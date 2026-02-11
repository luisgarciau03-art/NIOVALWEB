"""
FIX 632/637: Bug Detector - Deteccion automatica de bugs y errores en llamadas.

Modulo independiente que rastrea eventos por llamada y detecta 11 tipos de problemas:

BUGS TECNICOS (FIX 632):
1. BRUCE_MUDO: TwiML enviado pero audio nunca fetcheado por Twilio
2. LOOP: Bruce repite la misma respuesta 3+ veces
3. SILENCIO_PROLONGADO: Cliente dice "Bueno?" 2+ veces (Bruce no responde)
4. PATRON_INVALIDADO_FRECUENTE: 3+ patrones invalidados en 1 llamada
5. RESPUESTA_VACIA: GPT retorno vacio 2+ veces en 1 llamada

ERRORES DE CONTENIDO (FIX 637 - rule-based):
6. PREGUNTA_REPETIDA: Bruce hizo la misma pregunta 2+ veces
7. DATO_IGNORADO: Cliente dio telefono/email pero Bruce pidio de nuevo
8. OFERTA_POST_DESPEDIDA: Bruce ofrecio catalogo despues de despedirse
9. PITCH_REPETIDO: Bruce repitio el pitch de presentacion 2+ veces
10. CATALOGO_REPETIDO: Bruce ofrecio catalogo 2+ veces
11. DATO_SIN_RESPUESTA: Cliente dio dato (email/tel) pero Bruce no respondio (FIX 639D)

EVALUACION GPT (FIX 637 - GPT-4o-mini post-llamada):
12. GPT_EVAL_*: Problemas detectados por GPT al evaluar la conversacion completa

Cada funcion publica esta envuelta en try/except - CERO impacto en path critico.
"""

import os
import re
import time
import threading
import requests
from datetime import datetime
from collections import defaultdict


# ============================================================
# CONFIGURACION
# ============================================================

# Telegram bots (mismos del deploy notification)
TELEGRAM_BOTS = [
    {
        "token": "8537624347:AAHDIe60mb2TkdDk4vqlcS2tpakTB_5D4qE",
        "chat_id": "7314842427",
    },
    {
        "token": "8524460310:AAFAwph27rSagooKTNSGXauBycpDpCjhKjI",
        "chat_id": "5838212022",
    },
]

# Severidades
CRITICO = "CRITICO"
ALTO = "ALTO"
MEDIO = "MEDIO"
INFO = "INFO"

# Retener bugs recientes (max)
MAX_BUGS_HISTORY = 200

# GPT evaluation: minimo de turnos para justificar el costo
GPT_EVAL_MIN_TURNOS = 3

# FIX 640: Persistencia en disco (sobrevive deploys Railway)
_CACHE_DIR = os.getenv("CACHE_DIR", "audio_cache")
_BUGS_FILE = os.path.join(_CACHE_DIR, "recent_bugs.json")
_BUGS_SAVE_INTERVAL = 30  # Segundos minimo entre guardados
_bugs_last_save = 0


# ============================================================
# TRACKER POR LLAMADA
# ============================================================

class CallEventTracker:
    """Registra eventos estructurados para una llamada individual."""

    def __init__(self, call_sid: str, bruce_id: str, telefono: str = ""):
        self.call_sid = call_sid
        self.bruce_id = bruce_id
        self.telefono = telefono
        self.created_at = time.time()
        self.events = []
        # Contadores rapidos
        self.twiml_count = 0
        self.audio_fetch_count = 0
        self.respuestas_bruce = []
        self.textos_cliente = []
        self.conversacion = []  # FIX 637: Lista ordenada [("bruce", txt), ("cliente", txt)]
        self.patrones_invalidados = 0
        self.respuestas_vacias = 0
        self.cliente_dijo_bueno = 0

    def emit(self, event_type: str, data: dict = None):
        """Registra un evento. Siempre seguro (no lanza excepciones)."""
        try:
            self.events.append({
                "type": event_type,
                "time": time.time(),
                "data": data or {}
            })
            # Actualizar contadores
            if event_type == "TWIML_ENVIADO":
                self.twiml_count += 1
            elif event_type == "AUDIO_FETCH":
                self.audio_fetch_count += 1
            elif event_type == "BRUCE_RESPONDE":
                texto = (data or {}).get("texto", "")
                self.respuestas_bruce.append(texto)
                self.conversacion.append(("bruce", texto))
            elif event_type == "CLIENTE_DICE":
                texto = (data or {}).get("texto", "")
                self.textos_cliente.append(texto)
                self.conversacion.append(("cliente", texto))
                # Detectar "bueno?" del cliente (silencio prolongado)
                texto_lower = texto.lower().strip()
                if texto_lower in ("bueno", "bueno?", "hola", "hola?", "alo", "alo?"):
                    self.cliente_dijo_bueno += 1
            elif event_type == "PATRON_INVALIDADO":
                self.patrones_invalidados += 1
            elif event_type == "RESPUESTA_VACIA":
                self.respuestas_vacias += 1
        except Exception:
            pass  # Nunca fallar


# ============================================================
# DETECTOR DE BUGS TECNICOS (FIX 632)
# ============================================================

class BugDetector:
    """Analiza un CallEventTracker al terminar la llamada."""

    @staticmethod
    def analyze(tracker: CallEventTracker) -> list:
        """
        Retorna lista de bugs detectados (tecnicos + contenido).
        Cada bug: {"tipo": str, "severidad": str, "detalle": str, "categoria": str}
        """
        bugs = []
        try:
            # =============================================
            # BUGS TECNICOS (FIX 632)
            # =============================================

            # 1. BRUCE_MUDO: TwiML enviado pero audio no fetcheado
            if tracker.twiml_count > 0 and tracker.audio_fetch_count == 0:
                bugs.append({
                    "tipo": "BRUCE_MUDO",
                    "severidad": CRITICO,
                    "detalle": f"TwiML enviado {tracker.twiml_count}x pero audio fetcheado 0x",
                    "categoria": "tecnico"
                })

            # 2. LOOP: Misma respuesta de Bruce 3+ veces
            if len(tracker.respuestas_bruce) >= 3:
                from collections import Counter
                conteo = Counter(tracker.respuestas_bruce)
                for resp, count in conteo.most_common(3):
                    if count >= 3 and len(resp) > 10:
                        bugs.append({
                            "tipo": "LOOP",
                            "severidad": ALTO,
                            "detalle": f"Respuesta repetida {count}x: '{resp[:60]}...'",
                            "categoria": "tecnico"
                        })
                        break

            # 3. SILENCIO_PROLONGADO: Cliente dice "Bueno?" 2+ veces
            if tracker.cliente_dijo_bueno >= 2:
                bugs.append({
                    "tipo": "SILENCIO_PROLONGADO",
                    "severidad": ALTO,
                    "detalle": f"Cliente dijo 'Bueno?'/'Hola?' {tracker.cliente_dijo_bueno}x (Bruce no responde)",
                    "categoria": "tecnico"
                })

            # 4. PATRON_INVALIDADO_FRECUENTE: 3+ invalidaciones
            if tracker.patrones_invalidados >= 3:
                bugs.append({
                    "tipo": "PATRON_INVALIDADO_FRECUENTE",
                    "severidad": MEDIO,
                    "detalle": f"{tracker.patrones_invalidados} patrones invalidados en 1 llamada",
                    "categoria": "tecnico"
                })

            # 5. RESPUESTA_VACIA: GPT vacio 2+ veces
            if tracker.respuestas_vacias >= 2:
                bugs.append({
                    "tipo": "RESPUESTA_VACIA",
                    "severidad": ALTO,
                    "detalle": f"GPT retorno vacio {tracker.respuestas_vacias}x en esta llamada",
                    "categoria": "tecnico"
                })

            # =============================================
            # ERRORES DE CONTENIDO (FIX 637)
            # =============================================
            content_bugs = ContentAnalyzer.analyze(tracker)
            bugs.extend(content_bugs)

            # FIX 639D: DATO_SIN_RESPUESTA - check independiente (no requiere 2+ respuestas)
            dato_bugs = ContentAnalyzer._check_dato_sin_respuesta(tracker.conversacion)
            bugs.extend(dato_bugs)

        except Exception:
            pass  # Nunca fallar

        return bugs


# ============================================================
# ANALIZADOR DE CONTENIDO (FIX 637 - rule-based)
# ============================================================

class ContentAnalyzer:
    """Detecta errores de contenido en la conversacion (rule-based, sin GPT)."""

    # Palabras clave para detectar preguntas por datos de contacto
    _PIDE_NUMERO = re.compile(
        r'(cu[aá]l es (su|el|tu) (n[uú]mero|tel[eé]fono|celular|whatsapp))|'
        r'(me (puede|podr[ií]a) (dar|proporcionar|compartir) (su|el|un) (n[uú]mero|tel[eé]fono|whatsapp))|'
        r'(d[ií]game (su|el) (n[uú]mero|tel[eé]fono))',
        re.IGNORECASE
    )
    _PIDE_CORREO = re.compile(
        r'(cu[aá]l es (su|el|tu) (correo|email|e-mail))|'
        r'(me (puede|podr[ií]a) (dar|proporcionar|compartir) (su|el|un) (correo|email))|'
        r'(d[ií]game (su|el) (correo|email))',
        re.IGNORECASE
    )
    # Detectar que cliente dio datos
    _CLIENTE_DIO_NUMERO = re.compile(r'\d{7,10}', re.IGNORECASE)
    _CLIENTE_DIO_EMAIL = re.compile(
        r'(arroba|@|correo\s+es|mi\s+correo|email\s+es)',
        re.IGNORECASE
    )
    # Despedida
    _DESPEDIDA_BRUCE = re.compile(
        r'(gracias por su tiempo|que tenga (buen|excelente) d[ií]a|hasta luego|'
        r'fue un (gusto|placer)|le (deseo|agradezco)|buen d[ií]a.*gracias)',
        re.IGNORECASE
    )
    # Oferta catalogo/info
    _OFERTA_CATALOGO = re.compile(
        r'(env[ií](o|ar)(le)? (el|nuestro|un) cat[aá]logo|'
        r'le (mando|env[ií]o|comparto) (el|nuestro|un) cat[aá]logo|'
        r'quiere (recibir|ver|que le env[ií]e) (el|nuestro|un) cat[aá]logo)',
        re.IGNORECASE
    )
    # Pitch nioval
    _PITCH_NIOVAL = re.compile(
        r'(me comunico de (la marca )?nioval|'
        r'trabajamos productos ferreteros|'
        r'somos (la marca|una marca|distribuidores) nioval)',
        re.IGNORECASE
    )
    # Preguntas de Bruce (terminan en ?)
    _PREGUNTA = re.compile(r'\?')

    @staticmethod
    def analyze(tracker: CallEventTracker) -> list:
        """Analiza contenido de la conversacion buscando errores."""
        bugs = []
        try:
            respuestas = tracker.respuestas_bruce
            textos_cli = tracker.textos_cliente
            conv = tracker.conversacion

            # Minimo de turnos para analizar contenido
            if len(respuestas) < 2:
                return bugs

            # --- 6. PREGUNTA_REPETIDA ---
            bugs.extend(ContentAnalyzer._check_pregunta_repetida(respuestas))

            # --- 7. DATO_IGNORADO ---
            bugs.extend(ContentAnalyzer._check_dato_ignorado(conv))

            # --- 8. OFERTA_POST_DESPEDIDA ---
            bugs.extend(ContentAnalyzer._check_oferta_post_despedida(respuestas))

            # --- 9. PITCH_REPETIDO ---
            bugs.extend(ContentAnalyzer._check_pitch_repetido(respuestas))

            # --- 10. CATALOGO_REPETIDO ---
            bugs.extend(ContentAnalyzer._check_catalogo_repetido(respuestas))

            # Note: DATO_SIN_RESPUESTA (FIX 639D) se ejecuta desde BugDetector.analyze()
            # porque no requiere el minimo de 2 respuestas Bruce

        except Exception:
            pass  # Nunca fallar
        return bugs

    @staticmethod
    def _check_pregunta_repetida(respuestas: list) -> list:
        """Detecta si Bruce hizo la misma pregunta 2+ veces."""
        bugs = []
        try:
            preguntas = []
            for r in respuestas:
                if '?' in r and len(r) > 15:
                    # Extraer la parte de la pregunta (despues del ultimo '.')
                    partes = r.split('.')
                    for p in partes:
                        if '?' in p:
                            preguntas.append(p.strip().lower())

            # Buscar preguntas similares (>70% overlap)
            seen = {}
            for preg in preguntas:
                # Normalizar: quitar signos y palabras cortas
                palabras = set(re.findall(r'[a-záéíóúüñ]{4,}', preg))
                matched = False
                for key, (ref_palabras, count) in list(seen.items()):
                    if len(palabras) > 0 and len(ref_palabras) > 0:
                        overlap = len(palabras & ref_palabras) / max(len(palabras), len(ref_palabras))
                        if overlap >= 0.6:
                            seen[key] = (ref_palabras | palabras, count + 1)
                            matched = True
                            break
                if not matched and len(palabras) >= 2:
                    seen[preg] = (palabras, 1)

            for preg, (_, count) in seen.items():
                if count >= 2:
                    bugs.append({
                        "tipo": "PREGUNTA_REPETIDA",
                        "severidad": MEDIO,
                        "detalle": f"Pregunta repetida {count}x: '{preg[:60]}'",
                        "categoria": "contenido"
                    })
                    break  # Solo reportar la primera

        except Exception:
            pass
        return bugs

    @staticmethod
    def _check_dato_ignorado(conv: list) -> list:
        """Detecta si cliente dio telefono/email pero Bruce pidio de nuevo."""
        bugs = []
        try:
            cliente_dio_numero = False
            cliente_dio_email = False

            for role, texto in conv:
                if role == "cliente":
                    if ContentAnalyzer._CLIENTE_DIO_NUMERO.search(texto):
                        cliente_dio_numero = True
                    if ContentAnalyzer._CLIENTE_DIO_EMAIL.search(texto):
                        cliente_dio_email = True
                elif role == "bruce":
                    # Si cliente ya dio numero y Bruce pide numero
                    if cliente_dio_numero and ContentAnalyzer._PIDE_NUMERO.search(texto):
                        bugs.append({
                            "tipo": "DATO_IGNORADO",
                            "severidad": ALTO,
                            "detalle": f"Cliente ya dio numero pero Bruce pidio de nuevo: '{texto[:60]}'",
                            "categoria": "contenido"
                        })
                        break
                    # Si cliente ya dio email y Bruce pide email
                    if cliente_dio_email and ContentAnalyzer._PIDE_CORREO.search(texto):
                        bugs.append({
                            "tipo": "DATO_IGNORADO",
                            "severidad": ALTO,
                            "detalle": f"Cliente ya dio correo pero Bruce pidio de nuevo: '{texto[:60]}'",
                            "categoria": "contenido"
                        })
                        break

        except Exception:
            pass
        return bugs

    @staticmethod
    def _check_oferta_post_despedida(respuestas: list) -> list:
        """Detecta si Bruce ofrecio catalogo/info despues de despedirse."""
        bugs = []
        try:
            bruce_ya_se_despidio = False
            for r in respuestas:
                if ContentAnalyzer._DESPEDIDA_BRUCE.search(r):
                    bruce_ya_se_despidio = True
                elif bruce_ya_se_despidio:
                    # Cualquier respuesta sustancial despues de despedida
                    if ContentAnalyzer._OFERTA_CATALOGO.search(r) or ContentAnalyzer._PITCH_NIOVAL.search(r):
                        bugs.append({
                            "tipo": "OFERTA_POST_DESPEDIDA",
                            "severidad": MEDIO,
                            "detalle": f"Bruce se despidio pero luego ofrecio: '{r[:60]}'",
                            "categoria": "contenido"
                        })
                        break
        except Exception:
            pass
        return bugs

    @staticmethod
    def _check_pitch_repetido(respuestas: list) -> list:
        """Detecta si Bruce repitio el pitch de nioval 2+ veces."""
        bugs = []
        try:
            count = sum(1 for r in respuestas if ContentAnalyzer._PITCH_NIOVAL.search(r))
            if count >= 2:
                bugs.append({
                    "tipo": "PITCH_REPETIDO",
                    "severidad": MEDIO,
                    "detalle": f"Pitch de nioval repetido {count}x en la misma llamada",
                    "categoria": "contenido"
                })
        except Exception:
            pass
        return bugs

    @staticmethod
    def _check_catalogo_repetido(respuestas: list) -> list:
        """Detecta si Bruce ofrecio catalogo 2+ veces."""
        bugs = []
        try:
            count = sum(1 for r in respuestas if ContentAnalyzer._OFERTA_CATALOGO.search(r))
            if count >= 2:
                bugs.append({
                    "tipo": "CATALOGO_REPETIDO",
                    "severidad": MEDIO,
                    "detalle": f"Oferta de catalogo repetida {count}x en la misma llamada",
                    "categoria": "contenido"
                })
        except Exception:
            pass
        return bugs

    @staticmethod
    def _check_dato_sin_respuesta(conv: list) -> list:
        """FIX 639D: Detecta si cliente dio dato importante (email/telefono) pero Bruce no respondio.

        Caso BRUCE2068: Cliente dicto email completo, Bruce nunca respondio.
        Deteccion: Cliente dice algo con email/telefono, y la conversacion termina
        sin que Bruce confirme haberlo recibido.
        """
        bugs = []
        try:
            if len(conv) < 2:
                return bugs

            # Buscar el ultimo mensaje del cliente que contiene datos
            ultimo_dato_cliente_idx = -1
            tipo_dato = None
            for i, (role, texto) in enumerate(conv):
                if role == "cliente" and texto.strip():
                    texto_l = texto.lower()
                    if ContentAnalyzer._CLIENTE_DIO_EMAIL.search(texto) or '@' in texto:
                        ultimo_dato_cliente_idx = i
                        tipo_dato = "email"
                    elif ContentAnalyzer._CLIENTE_DIO_NUMERO.search(texto):
                        ultimo_dato_cliente_idx = i
                        tipo_dato = "telefono"

            if ultimo_dato_cliente_idx < 0:
                return bugs

            # Verificar si Bruce respondio DESPUES de ese dato
            bruce_respondio_despues = False
            for i in range(ultimo_dato_cliente_idx + 1, len(conv)):
                role, texto = conv[i]
                if role == "bruce" and texto.strip():
                    bruce_respondio_despues = True
                    break

            if not bruce_respondio_despues:
                texto_dato = conv[ultimo_dato_cliente_idx][1]
                bugs.append({
                    "tipo": "DATO_SIN_RESPUESTA",
                    "severidad": CRITICO,
                    "detalle": f"Cliente dio {tipo_dato} pero Bruce NUNCA respondio: '{texto_dato[:60]}'",
                    "categoria": "contenido"
                })

        except Exception:
            pass
        return bugs


# ============================================================
# EVALUACION GPT POST-LLAMADA (FIX 637)
# ============================================================

_GPT_EVAL_PROMPT = """Eres un auditor de calidad para llamadas de ventas de Bruce, agente AI de la marca NIOVAL (productos ferreteros).

Analiza esta conversacion telefonica y detecta SOLO errores claros. NO reportes cosas normales o menores.

FLUJO NORMAL DE BRUCE (esto NO son errores):
- Bruce se presenta, menciona NIOVAL y pregunta por el encargado de compras
- Si el encargado no esta, Bruce pide WhatsApp del encargado para enviar catalogo
- Si el cliente ofrece CORREO en vez de WhatsApp, Bruce acepta el correo. Esto es CORRECTO, no es "logica rota"
- Si el cliente dice "digame", "si digame", "que necesita" = esta diciendo "adelante, lo escucho", NO es una pregunta
- Bruce confirma los datos recibidos y se despide
- Si Bruce obtiene un contacto (email, WhatsApp, telefono), la llamada fue EXITOSA

Tipos de errores a buscar:
1. RESPUESTA_INCORRECTA: Bruce dio informacion FALSA sobre NIOVAL o sus productos
2. FUERA_DE_TEMA: Bruce hablo de algo completamente ajeno a NIOVAL/ferreteria
3. TONO_INADECUADO: Bruce fue grosero, impaciente o poco profesional
4. LOGICA_ROTA: Bruce pidio un dato que el cliente YA le habia dado EN LA MISMA LLAMADA
5. OPORTUNIDAD_PERDIDA: Cliente dijo explicitamente "si me interesa" o "enviame info" y Bruce NO le pidio contacto

CONVERSACION:
{conversacion}

Responde SOLO en este formato JSON (array vacio si no hay errores):
[
  {{"tipo": "TIPO_ERROR", "severidad": "ALTO|MEDIO", "turno": N, "detalle": "descripcion breve"}}
]

IMPORTANTE:
- Solo reporta errores CLAROS y EVIDENTES, no interpretaciones subjetivas
- Si la llamada fue corta (cliente colgo rapido), NO reportes nada
- Si Bruce se despidio correctamente tras rechazo, NO es error
- Si el cliente ofrecio correo en vez de WhatsApp y Bruce acepto, NO es error
- Si Bruce obtuvo datos de contacto y se despidio, la llamada fue exitosa - NO busques errores menores
- Adaptarse al medio de contacto que el cliente prefiera (correo vs WhatsApp vs telefono) es CORRECTO
- Maximo 3 errores por llamada
- Responde SOLO el JSON, sin texto adicional"""


def _evaluar_con_gpt(tracker: CallEventTracker) -> list:
    """Evalua la conversacion con GPT-4o-mini. Retorna lista de bugs."""
    bugs = []
    try:
        # Solo evaluar si hay suficientes turnos
        if len(tracker.respuestas_bruce) < GPT_EVAL_MIN_TURNOS:
            return bugs

        # Construir texto de conversacion
        lineas = []
        for i, (role, texto) in enumerate(tracker.conversacion):
            if role == "bruce":
                lineas.append(f"BRUCE: {texto}")
            else:
                lineas.append(f"CLIENTE: {texto}")

        if not lineas:
            return bugs

        conversacion_texto = "\n".join(lineas)

        # Lazy import de openai
        import openai
        api_key = os.environ.get("OPENAI_API_KEY", "")
        if not api_key:
            return bugs

        client = openai.OpenAI(api_key=api_key)

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": _GPT_EVAL_PROMPT.format(conversacion=conversacion_texto)}
            ],
            temperature=0.1,
            max_tokens=500,
            timeout=15
        )

        resultado = response.choices[0].message.content.strip()

        # Parsear JSON
        import json
        # Limpiar posible markdown
        if resultado.startswith("```"):
            resultado = resultado.split("```")[1]
            if resultado.startswith("json"):
                resultado = resultado[4:]

        errores = json.loads(resultado)

        if not isinstance(errores, list):
            return bugs

        for error in errores[:3]:  # Maximo 3
            tipo = error.get("tipo", "DESCONOCIDO")
            severidad = error.get("severidad", MEDIO)
            if severidad not in (CRITICO, ALTO, MEDIO):
                severidad = MEDIO
            detalle = error.get("detalle", "")
            turno = error.get("turno", "?")

            bugs.append({
                "tipo": f"GPT_{tipo}",
                "severidad": severidad,
                "detalle": f"[turno {turno}] {detalle}",
                "categoria": "gpt_eval"
            })

    except Exception as e:
        print(f"[BUG_DETECTOR] GPT eval error: {e}")

    return bugs


# ============================================================
# ESTADO GLOBAL (thread-safe)
# ============================================================

_lock = threading.Lock()
_active_trackers = {}     # call_sid -> CallEventTracker
_recent_bugs = []         # Lista de bugs recientes
_bugs_loaded = False      # FIX 640: Flag para lazy-load


def _load_bugs():
    """FIX 640: Carga bugs desde disco al iniciar."""
    global _recent_bugs, _bugs_loaded
    try:
        if os.path.exists(_BUGS_FILE):
            import json
            with open(_BUGS_FILE, 'r', encoding='utf-8') as f:
                loaded = json.load(f)
            if isinstance(loaded, list):
                _recent_bugs = loaded[-MAX_BUGS_HISTORY:]
                print(f"[BUG_DETECTOR] Cargados {len(_recent_bugs)} bugs desde disco")
        _bugs_loaded = True
    except Exception as e:
        print(f"[BUG_DETECTOR] Error cargando bugs: {e}")
        _bugs_loaded = True


def _save_bugs():
    """FIX 640: Guarda bugs a disco. Maximo cada {_BUGS_SAVE_INTERVAL}s."""
    global _bugs_last_save
    try:
        now = time.time()
        if (now - _bugs_last_save) < _BUGS_SAVE_INTERVAL:
            return
        import json
        os.makedirs(os.path.dirname(_BUGS_FILE) or '.', exist_ok=True)
        with open(_BUGS_FILE, 'w', encoding='utf-8') as f:
            json.dump(_recent_bugs, f, ensure_ascii=False)
        _bugs_last_save = now
    except Exception:
        pass


def _ensure_bugs_loaded():
    """FIX 640: Lazy-load bugs desde disco."""
    if not _bugs_loaded:
        _load_bugs()


def get_or_create_tracker(call_sid: str, bruce_id: str, telefono: str = "") -> CallEventTracker:
    """Obtiene o crea un tracker para esta llamada."""
    try:
        with _lock:
            if call_sid not in _active_trackers:
                _active_trackers[call_sid] = CallEventTracker(call_sid, bruce_id, telefono)
            else:
                # Actualizar bruce_id si no estaba
                if bruce_id and not _active_trackers[call_sid].bruce_id:
                    _active_trackers[call_sid].bruce_id = bruce_id
            return _active_trackers[call_sid]
    except Exception:
        # Retornar tracker descartable si falla
        return CallEventTracker(call_sid, bruce_id, telefono)


def emit_event(call_sid: str, event_type: str, data: dict = None):
    """Emite un evento para una llamada. Seguro si no existe tracker."""
    try:
        with _lock:
            tracker = _active_trackers.get(call_sid)
        if tracker:
            tracker.emit(event_type, data)
    except Exception:
        pass


def analyze_and_cleanup(call_sid: str, telefono: str = ""):
    """Analiza bugs al terminar llamada y limpia el tracker."""
    try:
        with _lock:
            tracker = _active_trackers.pop(call_sid, None)

        if not tracker:
            return

        # Fase 1: Bugs tecnicos + contenido (instantaneo)
        bugs = BugDetector.analyze(tracker)

        # Guardar entry base (tecnicos + contenido)
        bug_entry = {
            "bruce_id": tracker.bruce_id,
            "telefono": telefono or tracker.telefono,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "bugs": bugs,
            "stats": {
                "turnos": len(tracker.respuestas_bruce),
                "twiml": tracker.twiml_count,
                "audio_fetch": tracker.audio_fetch_count,
                "duracion_s": int(time.time() - tracker.created_at)
            }
        }

        if bugs:
            _ensure_bugs_loaded()
            with _lock:
                _recent_bugs.append(bug_entry)
                while len(_recent_bugs) > MAX_BUGS_HISTORY:
                    _recent_bugs.pop(0)

            _save_bugs()  # FIX 640: Persistir a disco

            # Enviar alerta Telegram en background
            threading.Thread(
                target=_enviar_alerta_telegram,
                args=(bug_entry,),
                daemon=True
            ).start()

            print(f"[BUG_DETECTOR] {tracker.bruce_id}: {len(bugs)} bug(s) detectado(s)")
            for bug in bugs:
                print(f"  [{bug['severidad']}] {bug['tipo']}: {bug['detalle']}")

        # Fase 2: Evaluacion GPT en background (async, no bloquea)
        if len(tracker.respuestas_bruce) >= GPT_EVAL_MIN_TURNOS:
            threading.Thread(
                target=_gpt_eval_background,
                args=(tracker, bug_entry),
                daemon=True
            ).start()

    except Exception as e:
        print(f"[BUG_DETECTOR] Error en analyze_and_cleanup: {e}")


def _gpt_eval_background(tracker: CallEventTracker, base_entry: dict):
    """Ejecuta evaluacion GPT en background y agrega resultados."""
    try:
        gpt_bugs = _evaluar_con_gpt(tracker)
        if not gpt_bugs:
            return

        # Crear nueva entry para bugs GPT
        gpt_entry = {
            "bruce_id": tracker.bruce_id,
            "telefono": base_entry.get("telefono", ""),
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "bugs": gpt_bugs,
            "stats": base_entry.get("stats", {})
        }

        with _lock:
            _recent_bugs.append(gpt_entry)
            while len(_recent_bugs) > MAX_BUGS_HISTORY:
                _recent_bugs.pop(0)

        _save_bugs()  # FIX 640: Persistir a disco

        # Enviar alerta Telegram
        _enviar_alerta_telegram(gpt_entry)

        print(f"[BUG_DETECTOR] {tracker.bruce_id}: GPT eval encontro {len(gpt_bugs)} error(es)")
        for bug in gpt_bugs:
            print(f"  [GPT {bug['severidad']}] {bug['tipo']}: {bug['detalle']}")

    except Exception as e:
        print(f"[BUG_DETECTOR] GPT eval background error: {e}")


def get_recent_bugs(limit: int = 50) -> list:
    """Retorna bugs recientes (mas reciente primero)."""
    try:
        _ensure_bugs_loaded()
        with _lock:
            return list(reversed(_recent_bugs[-limit:]))
    except Exception:
        return []


# ============================================================
# ALERTAS TELEGRAM
# ============================================================

def _enviar_alerta_telegram(bug_entry: dict):
    """Envia alerta a Telegram. Ejecutar en daemon thread."""
    try:
        bruce_id = bug_entry.get("bruce_id", "???")
        telefono = bug_entry.get("telefono", "")
        bugs = bug_entry.get("bugs", [])
        stats = bug_entry.get("stats", {})

        # Solo alertar bugs CRITICO o ALTO
        bugs_importantes = [b for b in bugs if b.get("severidad") in (CRITICO, ALTO)]
        if not bugs_importantes:
            return

        # Construir mensaje
        lineas = []

        # Diferenciar header por categoria
        categorias = set(b.get("categoria", "tecnico") for b in bugs_importantes)
        if "gpt_eval" in categorias:
            lineas.append(f"<b>ERROR DETECTADO (GPT) en {bruce_id}</b>")
        elif "contenido" in categorias:
            lineas.append(f"<b>ERROR CONTENIDO en {bruce_id}</b>")
        else:
            lineas.append(f"<b>BUG DETECTADO en {bruce_id}</b>")

        if telefono:
            lineas.append(f"Tel: {telefono}")
        lineas.append("")

        for bug in bugs_importantes:
            emoji = "!!!" if bug["severidad"] == CRITICO else "!!"
            lineas.append(f"{emoji} <b>{bug['tipo']}</b> ({bug['severidad']})")
            lineas.append(f"  {bug['detalle']}")
            lineas.append("")

        lineas.append(f"Turnos: {stats.get('turnos', '?')} | Duracion: {stats.get('duracion_s', '?')}s")
        lineas.append(f"Hora: {bug_entry.get('timestamp', '')}")

        mensaje = "\n".join(lineas)

        # Enviar a todos los bots
        for bot in TELEGRAM_BOTS:
            try:
                url = f"https://api.telegram.org/bot{bot['token']}/sendMessage"
                data = {
                    "chat_id": bot["chat_id"],
                    "text": mensaje,
                    "parse_mode": "HTML"
                }
                requests.post(url, data=data, timeout=10)
            except Exception:
                pass  # No fallar si un bot no responde

    except Exception:
        pass


# ============================================================
# DASHBOARD HTML
# ============================================================

def generar_bugs_html() -> str:
    """Genera HTML para el endpoint /bugs."""
    bugs = get_recent_bugs(100)

    rows = []
    for entry in bugs:
        bruce_id = entry.get("bruce_id", "???")
        telefono = entry.get("telefono", "")
        timestamp = entry.get("timestamp", "")
        stats = entry.get("stats", {})

        for bug in entry.get("bugs", []):
            severidad = bug.get("severidad", MEDIO)
            categoria = bug.get("categoria", "tecnico")

            if severidad == CRITICO:
                color = "#ff4444"
            elif severidad == ALTO:
                color = "#ffaa00"
            elif categoria == "gpt_eval":
                color = "#cc66ff"
            else:
                color = "#44aaff"

            # Icono por categoria
            if categoria == "gpt_eval":
                cat_icon = "AI"
            elif categoria == "contenido":
                cat_icon = "CTN"
            else:
                cat_icon = "TEC"

            rows.append(f"""
            <tr>
                <td>{timestamp}</td>
                <td><b>{bruce_id}</b></td>
                <td>{telefono}</td>
                <td><span class="cat-{categoria}">{cat_icon}</span></td>
                <td style="color:{color};font-weight:bold">{bug['tipo']}</td>
                <td style="color:{color}">{severidad}</td>
                <td>{bug.get('detalle', '')}</td>
                <td>{stats.get('turnos', '?')}t / {stats.get('duracion_s', '?')}s</td>
            </tr>""")

    if not rows:
        tabla = "<p>Sin bugs/errores detectados. Las alertas aparecen cuando se detectan anomalias en llamadas.</p>"
    else:
        tabla = f"""
        <table border="1" cellpadding="6" cellspacing="0" style="border-collapse:collapse;width:100%;font-size:13px">
            <tr style="background:#333;color:white">
                <th>Hora</th><th>BRUCE ID</th><th>Tel</th><th>Cat</th>
                <th>Tipo</th><th>Sev</th><th>Detalle</th><th>Stats</th>
            </tr>
            {''.join(rows)}
        </table>"""

    # Contar por tipo y categoria
    conteo_tipo = defaultdict(int)
    conteo_cat = defaultdict(int)
    for entry in bugs:
        for bug in entry.get("bugs", []):
            conteo_tipo[bug.get("tipo", "?")] += 1
            conteo_cat[bug.get("categoria", "tecnico")] += 1

    resumen_tipo = " | ".join(f"{tipo}: {cnt}" for tipo, cnt in sorted(conteo_tipo.items())) or "Ninguno"
    resumen_cat = " | ".join(
        f"{'Tecnicos' if c == 'tecnico' else 'Contenido' if c == 'contenido' else 'GPT Eval'}: {n}"
        for c, n in sorted(conteo_cat.items())
    ) or "Ninguno"

    return f"""<!DOCTYPE html>
<html><head>
<meta charset="utf-8">
<title>Bruce W - Bug Detector + Quality Checker</title>
<style>
    body {{ font-family: monospace; margin: 20px; background: #1a1a1a; color: #eee; }}
    h1 {{ color: #ff6644; }}
    table {{ background: #222; }}
    tr:nth-child(even) {{ background: #2a2a2a; }}
    th {{ text-align: left; }}
    a {{ color: #44aaff; }}
    .resumen {{ background: #333; padding: 10px; border-radius: 5px; margin: 10px 0; }}
    .cat-tecnico {{ background: #335; padding: 2px 6px; border-radius: 3px; font-size: 11px; }}
    .cat-contenido {{ background: #533; padding: 2px 6px; border-radius: 3px; font-size: 11px; }}
    .cat-gpt_eval {{ background: #353; padding: 2px 6px; border-radius: 3px; font-size: 11px; color: #cc66ff; }}
    .legend {{ display: flex; gap: 20px; margin: 10px 0; }}
    .legend span {{ padding: 2px 8px; border-radius: 3px; font-size: 12px; }}
</style>
</head><body>
<h1>Bug Detector + Quality Checker - Bruce W</h1>
<p><a href="/historial-llamadas">Historial</a> | <a href="/bugs">Bugs</a> | <a href="/pattern-audit">Pattern Audit</a></p>

<div class="resumen">
    <b>Por categoria:</b> {resumen_cat}<br>
    <b>Por tipo:</b> {resumen_tipo}<br>
    <b>Total entradas:</b> {len(bugs)}
</div>

<div class="legend">
    <span class="cat-tecnico">TEC = Bug Tecnico</span>
    <span class="cat-contenido">CTN = Error de Contenido</span>
    <span class="cat-gpt_eval">AI = Evaluacion GPT</span>
</div>

{tabla}

<p style="color:#666;margin-top:20px">
    <b>Bugs Tecnicos (TEC):</b> BRUCE_MUDO | LOOP | SILENCIO_PROLONGADO | PATRON_INVALIDADO_FRECUENTE | RESPUESTA_VACIA<br>
    <b>Errores Contenido (CTN):</b> PREGUNTA_REPETIDA | DATO_IGNORADO | OFERTA_POST_DESPEDIDA | PITCH_REPETIDO | CATALOGO_REPETIDO<br>
    <b>GPT Eval (AI):</b> GPT_RESPUESTA_INCORRECTA | GPT_FUERA_DE_TEMA | GPT_TONO_INADECUADO | GPT_LOGICA_ROTA | GPT_OPORTUNIDAD_PERDIDA
</p>
</body></html>"""
