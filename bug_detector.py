"""
FIX 632/637: Bug Detector - Deteccion automatica de bugs y errores en llamadas.

Modulo independiente que rastrea eventos por llamada y detecta 17+ tipos de problemas:

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
12. CLIENTE_HABLA_ULTIMO: Cliente hablo al final pero Bruce nunca respondio (FIX 642A)

EVALUACION GPT (FIX 637 - GPT-4o-mini post-llamada):
12. GPT_EVAL_*: Problemas detectados por GPT al evaluar la conversacion completa

Cada funcion publica esta envuelta en try/except - CERO impacto en path critico.
"""

import os
import re
import sys
import time
import atexit
import signal
import threading
import requests
from datetime import datetime
from collections import defaultdict


# ============================================================
# CONFIGURACION
# ============================================================

# FIX 751: Telegram tokens movidos a variables de entorno (antes hardcoded)
TELEGRAM_BOTS = [
    {
        "token": os.getenv("TELEGRAM_BOT1_TOKEN", ""),
        "chat_id": os.getenv("TELEGRAM_BOT1_CHAT_ID", ""),
    },
    {
        "token": os.getenv("TELEGRAM_BOT2_TOKEN", ""),
        "chat_id": os.getenv("TELEGRAM_BOT2_CHAT_ID", ""),
    },
]

# Deploy version - se actualiza automaticamente via set_deploy_version()
_DEPLOY_VERSION = "sin-deploy-info"


def set_deploy_version(version: str):
    """Permite a servidor_llamadas.py configurar la version del deploy actual."""
    global _DEPLOY_VERSION
    _DEPLOY_VERSION = version

# Severidades
CRITICO = "CRITICO"
ALTO = "ALTO"
MEDIO = "MEDIO"
INFO = "INFO"

# Retener bugs recientes (max)
MAX_BUGS_HISTORY = 200

# GPT evaluation: minimo de turnos para justificar el costo
# FIX 642B: Bajado de 3 a 2 (BRUCE2070 tenia 2 turnos y GPT eval no corrio)
# FIX 692B: Subido de 2 a 3 (BRUCE2214: 2 turnos/43s genera FP 66% del tiempo)
# FIX 713A: Threshold dinámico - llamadas cortas (25-45s, 2 turnos) usan prompt enfocado
GPT_EVAL_MIN_TURNOS = 2           # FIX 713A: Bajado de 3 a 2 (llamadas cortas usan prompt enfocado)
GPT_EVAL_MIN_TURNOS_COMPLETO = 3  # FIX 713A: GPT eval completo requiere 3+ turnos
# FIX 692B: Duración mínima para GPT eval (llamadas ultra-cortas = FP)
# FIX 713A: Bajado de 45 a 25 (BRUCE2263: 41s/2 turnos tenía bugs reales no detectados)
# FIX 717: Bajado de 25 a 20 (BRUCE2284: 24s tenía bugs claros no detectados por 1s)
GPT_EVAL_MIN_DURACION_S = 20
GPT_EVAL_DURACION_CORTA_S = 45    # FIX 713A: < 45s = llamada corta → prompt enfocado

# FIX 640: Persistencia en disco (sobrevive deploys Railway)
# FIX 691: Robustez - save inmediato, atexit handler, fsync
# FIX 748: Railway Volume - usar PERSISTENT_DIR para sobrevivir deploys
_CACHE_DIR = os.getenv("CACHE_DIR", "audio_cache")
_PERSISTENT_DIR = os.getenv("PERSISTENT_DIR", _CACHE_DIR)
_BUGS_FILE = os.path.join(_PERSISTENT_DIR, "recent_bugs.json")
_BUGS_SAVE_INTERVAL = 5  # FIX 691: Reducido de 30s a 5s para minimizar perdida
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
        self.filler_162a_count = 0  # FIX 715: Contador de veces que se usó audio filler por fallo TTS

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
            elif event_type == "FILLER_162A":
                self.filler_162a_count += 1  # FIX 715: TTS falló, se usó audio filler
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

            # FIX 715: RESPUESTA_FILLER_INCOHERENTE - TTS falló y se usó "dejeme_ver" como filler
            if tracker.filler_162a_count >= 1:
                bugs.append({
                    "tipo": "RESPUESTA_FILLER_INCOHERENTE",
                    "severidad": ALTO,
                    "detalle": f"ElevenLabs TTS fallo {tracker.filler_162a_count}x -> audio 'dejeme_ver' usado como filler (cliente escucho respuesta incoherente)",
                    "categoria": "tecnico"
                })

            # =============================================
            # ERRORES DE CONTENIDO (FIX 637)
            # =============================================
            content_bugs = ContentAnalyzer.analyze(tracker)
            bugs.extend(content_bugs)

            # FIX 716: AREA_EQUIVOCADA / NO_MANEJA_FERRETERIA
            area_bugs = ContentAnalyzer._check_area_equivocada(tracker.conversacion)
            bugs.extend(area_bugs)

            # FIX 718: DICTADO_INTERRUMPIDO - cliente dictando dato y Bruce se despide
            dictado_bugs = ContentAnalyzer._check_dictado_interrumpido(tracker.conversacion)
            bugs.extend(dictado_bugs)

            # FIX 721: TRANSFER_IGNORADA - cliente pide esperar/transferir y Bruce sigue vendiendo
            transfer_bugs = ContentAnalyzer._check_transfer_ignorada(tracker.conversacion)
            bugs.extend(transfer_bugs)

            # FIX 723: DEGRADACION_TTS - fillers TTS consecutivos
            degradacion_bugs = ContentAnalyzer._check_degradacion_servicio(tracker)
            bugs.extend(degradacion_bugs)

            # FIX 724: PREFERENCIA_IGNORADA - cliente prefiere un canal y Bruce pide otro
            preferencia_bugs = ContentAnalyzer._check_preferencia_ignorada(tracker.conversacion)
            bugs.extend(preferencia_bugs)

            # FIX 725: DATO_NEGADO_REINSISTIDO - cliente niega dato y Bruce lo pide después
            negado_bugs = ContentAnalyzer._check_dato_negado_reinsistido(tracker.conversacion)
            bugs.extend(negado_bugs)

            # FIX 726: RESPUESTA_FILLER_GPT - GPT genera fillers como respuesta
            filler_gpt_bugs = ContentAnalyzer._check_respuesta_filler_gpt(tracker.respuestas_bruce, tracker.conversacion)
            bugs.extend(filler_gpt_bugs)

            # FIX 727: INTERRUPCION_CONVERSACIONAL - Bruce corta al cliente mientras explica
            interrupcion_bugs = ContentAnalyzer._check_interrupcion_conversacional(tracker.conversacion)
            bugs.extend(interrupcion_bugs)

            # FIX 793B: PREGUNTA_IGNORADA - Cliente pregunta y Bruce solo da acknowledgment
            pregunta_bugs = ContentAnalyzer._check_pregunta_ignorada(tracker.conversacion)
            bugs.extend(pregunta_bugs)

            # FIX 728: DESPEDIDA_PREMATURA - Bruce se despide sin capturar contacto
            despedida_bugs = ContentAnalyzer._check_despedida_prematura(tracker.conversacion, tracker.respuestas_bruce)
            bugs.extend(despedida_bugs)

            # FIX 729: CONTEXTO_IGNORADO - Cliente es decisor pero Bruce lo ignora
            contexto_bugs = ContentAnalyzer._check_contexto_ignorado(tracker.conversacion)
            bugs.extend(contexto_bugs)

            # FIX 730: SALUDO_FALTANTE - Bruce no saludó en primer turno
            saludo_bugs = ContentAnalyzer._check_saludo_faltante(tracker.respuestas_bruce)
            bugs.extend(saludo_bugs)

            # FIX 639D: DATO_SIN_RESPUESTA - check independiente (no requiere 2+ respuestas)
            dato_bugs = ContentAnalyzer._check_dato_sin_respuesta(tracker.conversacion)
            bugs.extend(dato_bugs)

            # FIX 642A: CLIENTE_HABLA_ULTIMO - cliente hablo al final y Bruce nunca respondio
            # Solo si DATO_SIN_RESPUESTA no lo cubrio ya (evitar doble reporte)
            if not dato_bugs:
                ultimo_bugs = ContentAnalyzer._check_cliente_habla_ultimo(tracker.conversacion)
                bugs.extend(ultimo_bugs)

            # =============================================
            # FIX 735: FILTRO IVR/CONMUTADOR
            # Si la "conversación" es con un IVR/PBX automatizado,
            # los bugs de contenido son falsos positivos
            # =============================================
            if bugs and tracker.conversacion:
                _IVR_PATTERNS_735 = re.compile(
                    r'(extensi[oó]n|m[aá]rquelo ahora|seleccione una|'
                    r'opciones?\s*\.?\s*(?:uno|dos|tres|cuatro)|'
                    r'espere en la l[ií]nea|para ser atendido|'
                    r'marque\s+(?:el|uno|dos|tres)|'
                    r'bienvenido\s+a\s+(?:la\s+)?l[ií]nea|'
                    r'horario de atenci[oó]n|'
                    r'presione\s+(?:uno|dos|tres|\d)|'
                    r'teclee\s+(?:el|su)|'
                    r'si desea\s+(?:hablar|comunicarse))',
                    re.IGNORECASE
                )
                texto_cliente_735 = ' '.join(t for who, t in tracker.conversacion if who == 'cliente')
                if _IVR_PATTERNS_735.search(texto_cliente_735):
                    # IVR detectado: filtrar bugs de contenido que son falsos positivos
                    tipos_fp_ivr = {
                        'GPT_CONTEXTO_IGNORADO', 'GPT_OPORTUNIDAD_PERDIDA',
                        'INTERRUPCION_CONVERSACIONAL', 'DESPEDIDA_PREMATURA',
                        'CONTEXTO_IGNORADO', 'DATO_IGNORADO',
                    }
                    bugs_originales = len(bugs)
                    bugs = [b for b in bugs if b.get('tipo') not in tipos_fp_ivr]
                    if len(bugs) < bugs_originales:
                        print(f"[FIX 735] IVR/conmutador detectado: {bugs_originales - len(bugs)} falsos positivos filtrados")

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

    # =========================================================
    # FIX 716: AREA_EQUIVOCADA / NO_MANEJA_FERRETERIA
    # =========================================================
    # FIX 716+720: Patrones de área equivocada / no aplica
    _AREA_EQUIVOCADA_PATTERNS = [
        'no manejo ferreteria', 'no manejamos ferreteria',
        'no manejo nada de ferreteria', 'no manejamos nada de ferreteria',
        'esto no es ferreteria', 'esto no es una ferreteria',
        'aqui no es ferreteria', 'no somos ferreteria',
        'no vendemos ferreteria', 'no es ferreteria',
        'no tenemos ferreteria', 'no trabajamos ferreteria',
        'area equivocada', 'departamento equivocado',
        'numero equivocado', 'se equivoco de numero',
        'corporativo', 'oficinas corporativas',
        'no es mi area', 'no me corresponde',
        'no es el area', 'llamo al lugar equivocado',
        'no hacemos eso', 'no manejamos eso',
        'no vendemos eso', 'no trabajamos con eso',
        'no es aqui', 'aqui no es',
        # FIX 720: Variantes adicionales
        'no es conmigo', 'no soy yo',
        'no es mi departamento', 'no es de mi area',
        'se equivoco', 'esta equivocado',
        'no hacemos compras', 'no compramos',
        'no hacemos ningun tipo de compra',
    ]

    # FIX 716+720: Respuestas de Bruce que indican que NO entendió el rechazo
    _BRUCE_NO_ENTENDIO_RECHAZO = re.compile(
        r'(whatsapp|correo|cat[aá]logo|encargad[oa]|informaci[oó]n|producto|me comunico|me permite|'
        r'le env[ií]o|le puedo|me podr[ií]a|aja.*si|mmm|entiendo.*me|'
        r'le ofrecemos|nuestro cat[aá]logo|le comento|le comparto|'
        r'le interesar[ií]a|le gustar[ií]a|qu[eé] le parece)',
        re.IGNORECASE
    )

    @staticmethod
    def _check_area_equivocada(conv: list) -> list:
        """FIX 716: Detecta si cliente dice que no es ferretería/área equivocada
        y Bruce no se despide apropiadamente."""
        bugs = []
        try:
            if len(conv) < 2:
                return bugs

            for i, (role, texto) in enumerate(conv):
                if role != "cliente" or not texto.strip():
                    continue

                texto_l = texto.lower()
                # Normalizar acentos
                texto_norm = texto_l.replace('á', 'a').replace('é', 'e').replace('í', 'i').replace('ó', 'o').replace('ú', 'u')

                cliente_dice_no_aplica = any(p in texto_norm for p in ContentAnalyzer._AREA_EQUIVOCADA_PATTERNS)

                if not cliente_dice_no_aplica:
                    continue

                # Verificar si Bruce respondió DESPUÉS con algo que ignora el rechazo
                for j in range(i + 1, len(conv)):
                    r2, t2 = conv[j]
                    if r2 == "bruce" and t2.strip():
                        # ¿Bruce ignoró el rechazo y siguió vendiendo?
                        if ContentAnalyzer._BRUCE_NO_ENTENDIO_RECHAZO.search(t2):
                            bugs.append({
                                "tipo": "AREA_EQUIVOCADA",
                                "severidad": ALTO,
                                "detalle": f"Cliente dijo '{texto[:60]}' pero Bruce ignoró y respondió: '{t2[:60]}'",
                                "categoria": "contenido"
                            })
                        break  # Solo revisar la siguiente respuesta de Bruce
        except Exception:
            pass
        return bugs

    # =========================================================
    # FIX 718: DICTADO_INTERRUMPIDO
    # =========================================================
    # FIX 718+720: Patrones de dictado (email, teléfono, WhatsApp, nombre, dirección)
    # FIX 842: \b en nombres de letras (ele/eme/ene/ese/erre) para evitar falsos positivos
    # en palabras comunes: "tenemos" contiene "ene", "presente" contiene "ese", etc.
    # FIX 847: \d{2,} → \d{3,} para evitar falso positivo con horas "4:00", "3:00"
    # (el "00" de la hora matcheaba como inicio de dictado de número)
    # FIX 847B+: También detectar múltiples grupos de 2+ dígitos separados por espacios/guiones
    # (teléfonos mexicanos tipo "33 12 34 56 78") que no tienen 3+ dígitos consecutivos
    _DICTADO_PATTERNS = re.compile(
        r'(arroba|@|guion bajo|guion medio|punto com|punto net|punto mx|'
        r'hotmail|gmail|yahoo|outlook|prodigy|'
        r'a de|b de|c de|d de|e de|f de|g de|'
        r'\bele\b|\beme\b|\bene\b|\bese\b|\berre\b|'
        r'doble (u|v|uve)|'
        r'mi whatsapp es|mi n[uú]mero es|mi celular es|mi tel[eé]fono es|'
        r'mi correo es|mi email es|mi nombre es|me llamo|'
        r'la direcci[oó]n es|estamos en|la calle es|'
        r'\d{3,}|(?:\d{2,}[\s\-]+){2,}\d{2,})',
        re.IGNORECASE
    )

    _BRUCE_DESPEDIDA = re.compile(
        r'(me comunico despu[eé]s|muchas gracias por su tiempo|que tenga|buen d[ií]a|'
        r'excelente d[ií]a|hasta luego|nos comunicamos|le marco)',
        re.IGNORECASE
    )

    # FIX 718+720: Confirmaciones de Bruce que indican que SÍ procesó el dato
    _BRUCE_CONFIRMA_DATO = re.compile(
        r'(perfecto.*lo tengo|lo anot[eé]|le env[ií]o el cat[aá]logo|'
        r'perfecto.*env[ií]o|perfecto.*catalogo|listo.*anot|'
        r'anotado|recibido|entendido.*env|ya lo tengo|'
        r'registrado|tom[eé] nota|correcto.*lo tengo|'
        r'excelente.*dato|muy bien.*anot|perfecto.*dato|'
        r'le mando|se lo env[ií]o)',
        re.IGNORECASE
    )

    @staticmethod
    def _check_dictado_interrumpido(conv: list) -> list:
        """FIX 718: Detecta si cliente estaba dictando datos y Bruce se despidió/cambió tema."""
        bugs = []
        try:
            if len(conv) < 3:
                return bugs

            for i, (role, texto) in enumerate(conv):
                if role != "cliente" or not texto.strip():
                    continue

                # ¿El cliente estaba dictando?
                if not ContentAnalyzer._DICTADO_PATTERNS.search(texto):
                    continue

                # Buscar la siguiente respuesta de Bruce
                for j in range(i + 1, len(conv)):
                    r2, t2 = conv[j]
                    if r2 == "bruce" and t2.strip():
                        # ¿Bruce se despidió en vez de confirmar el dato?
                        if ContentAnalyzer._BRUCE_DESPEDIDA.search(t2):
                            # FIX 718: Excluir si Bruce CONFIRMÓ el dato antes de despedirse
                            if ContentAnalyzer._BRUCE_CONFIRMA_DATO.search(t2):
                                break  # Bruce procesó el dato, no es interrupción
                            bugs.append({
                                "tipo": "DICTADO_INTERRUMPIDO",
                                "severidad": CRITICO,
                                "detalle": f"Cliente dictaba dato ('{texto[:50]}') pero Bruce se despidió: '{t2[:60]}'",
                                "categoria": "contenido"
                            })
                        break
        except Exception:
            pass
        return bugs

    # =========================================================
    # FIX 721: TRANSFER_IGNORADA - Cliente pide esperar/transferir
    # =========================================================
    _TRANSFER_PATTERNS = re.compile(
        r'(esp[eé]r[ea]me|le paso|le comunico|se lo paso|ahorita.+viene|'
        r'd[eé]jeme.+(?:pasar|comunicar)|un momento.+(?:le paso|se lo paso)|'
        r'le transfiero|ahorita le paso|d[eé]jeme ver si est[aá]|'
        r'voy a ver si est[aá]|ahorita viene|ya viene|espere un momento)',
        re.IGNORECASE
    )

    # Respuestas de Bruce que son correctas ante transfer (esperar)
    _BRUCE_ESPERA_CORRECTO = re.compile(
        r'(claro.+esper|por supuesto.+esper|s[ií].+esper|'
        r'con gusto.+esper|adelante|claro que s[ií]|'
        r'perfecto.+esper|s[ií].*no hay problema)',
        re.IGNORECASE
    )

    @staticmethod
    def _check_transfer_ignorada(conv: list) -> list:
        """FIX 721: Detecta si cliente pide esperar/transferir y Bruce sigue vendiendo."""
        bugs = []
        try:
            if len(conv) < 2:
                return bugs

            for i, (role, texto) in enumerate(conv):
                if role != "cliente" or not texto.strip():
                    continue

                if not ContentAnalyzer._TRANSFER_PATTERNS.search(texto):
                    continue

                # Buscar siguiente respuesta de Bruce
                for j in range(i + 1, len(conv)):
                    r2, t2 = conv[j]
                    if r2 == "bruce" and t2.strip():
                        # ¿Bruce respondió correctamente (esperando)?
                        if ContentAnalyzer._BRUCE_ESPERA_CORRECTO.search(t2):
                            break  # Comportamiento correcto
                        # ¿Bruce siguió vendiendo/hablando?
                        if ContentAnalyzer._BRUCE_NO_ENTENDIO_RECHAZO.search(t2):
                            bugs.append({
                                "tipo": "TRANSFER_IGNORADA",
                                "severidad": ALTO,
                                "detalle": f"Cliente pidió transferir ('{texto[:50]}') pero Bruce siguió: '{t2[:60]}'",
                                "categoria": "contenido"
                            })
                        break
        except Exception:
            pass
        return bugs

    # =========================================================
    # FIX 723: DEGRADACION_TTS - Fillers consecutivos
    # =========================================================
    @staticmethod
    def _check_degradacion_servicio(tracker) -> list:
        """FIX 723: Detecta degradación de servicio por fillers TTS consecutivos."""
        bugs = []
        try:
            if tracker.filler_162a_count >= 2:
                bugs.append({
                    "tipo": "DEGRADACION_TTS",
                    "severidad": CRITICO,
                    "detalle": f"ElevenLabs TTS fallo {tracker.filler_162a_count}x consecutivas -> degradacion de servicio",
                    "categoria": "tecnico"
                })
        except Exception:
            pass
        return bugs

    # =========================================================
    # FIX 724: PREFERENCIA_IGNORADA
    # =========================================================
    _PREFERENCIA_PATTERNS = re.compile(
        r'(mejor por (?:correo|whatsapp|tel[eé]fono|email)|'
        r'prefiero (?:correo|whatsapp|que me llamen|email|tel[eé]fono)|'
        r'por (?:correo|whatsapp) mejor|'
        r'mand[ea]me(?:lo)? por (?:correo|whatsapp|email)|'
        r'env[ií]ame(?:lo)? por (?:correo|whatsapp|email)|'
        r'mejor.+(?:correo|whatsapp|email)|'
        r'(?:d[ea]me|dame).+(?:correo|whatsapp|email))',
        re.IGNORECASE
    )

    # Mapeo de canales para detectar insistencia en canal diferente
    _CANAL_CORREO = re.compile(r'(correo|email|e-mail)', re.IGNORECASE)
    _CANAL_WHATSAPP = re.compile(r'(whatsapp|wats|what)', re.IGNORECASE)
    _CANAL_TELEFONO = re.compile(r'(tel[eé]fono|celular|llamar|llam[ea]me)', re.IGNORECASE)

    @staticmethod
    def _check_preferencia_ignorada(conv: list) -> list:
        """FIX 724: Detecta si cliente indica canal preferido y Bruce pide otro."""
        bugs = []
        try:
            if len(conv) < 3:
                return bugs

            for i, (role, texto) in enumerate(conv):
                if role != "cliente" or not texto.strip():
                    continue

                if not ContentAnalyzer._PREFERENCIA_PATTERNS.search(texto):
                    continue

                # Detectar canal preferido del cliente
                canal_preferido = None
                if ContentAnalyzer._CANAL_CORREO.search(texto):
                    canal_preferido = "correo"
                elif ContentAnalyzer._CANAL_WHATSAPP.search(texto):
                    canal_preferido = "whatsapp"
                elif ContentAnalyzer._CANAL_TELEFONO.search(texto):
                    canal_preferido = "telefono"

                if not canal_preferido:
                    continue

                # Buscar siguiente respuesta de Bruce
                for j in range(i + 1, len(conv)):
                    r2, t2 = conv[j]
                    if r2 == "bruce" and t2.strip():
                        t2_lower = t2.lower()
                        # ¿Bruce pidió un canal diferente?
                        bruce_pide_otro = False
                        if canal_preferido == "correo" and ContentAnalyzer._CANAL_WHATSAPP.search(t2):
                            bruce_pide_otro = True
                        elif canal_preferido == "whatsapp" and 'correo' in t2_lower and 'whatsapp' not in t2_lower:
                            bruce_pide_otro = True
                        elif canal_preferido == "telefono" and (ContentAnalyzer._CANAL_WHATSAPP.search(t2) or ContentAnalyzer._CANAL_CORREO.search(t2)):
                            bruce_pide_otro = True

                        if bruce_pide_otro:
                            bugs.append({
                                "tipo": "PREFERENCIA_IGNORADA",
                                "severidad": MEDIO,
                                "detalle": f"Cliente prefiere {canal_preferido} ('{texto[:50]}') pero Bruce pidió otro canal: '{t2[:60]}'",
                                "categoria": "contenido"
                            })
                        break
        except Exception:
            pass
        return bugs

    # =========================================================
    # FIX 725: DATO_NEGADO_REINSISTIDO
    # =========================================================
    _NEGACION_DATO_PATTERNS = re.compile(
        r'(no tengo (?:whatsapp|correo|celular|email)|'
        r'solo tengo (?:fijo|tel[eé]fono de casa|de casa)|'
        r'no uso (?:whatsapp|correo|email|celular)|'
        r'no manejo (?:whatsapp|correo|redes|email|celular)|'
        r'no cuento con (?:whatsapp|correo|email|celular))',
        re.IGNORECASE
    )

    @staticmethod
    def _check_dato_negado_reinsistido(conv: list) -> list:
        """FIX 725: Detecta si cliente niega tener un dato y Bruce lo pide después."""
        bugs = []
        try:
            if len(conv) < 3:
                return bugs

            # Recolectar negaciones del cliente
            datos_negados = set()
            negacion_indices = {}

            for i, (role, texto) in enumerate(conv):
                if role != "cliente" or not texto.strip():
                    continue

                match = ContentAnalyzer._NEGACION_DATO_PATTERNS.search(texto)
                if not match:
                    continue

                texto_l = texto.lower()
                if 'whatsapp' in texto_l or 'wats' in texto_l:
                    datos_negados.add('whatsapp')
                    negacion_indices['whatsapp'] = i
                if 'correo' in texto_l or 'email' in texto_l:
                    datos_negados.add('correo')
                    negacion_indices['correo'] = i
                if 'celular' in texto_l:
                    datos_negados.add('celular')
                    negacion_indices['celular'] = i

            if not datos_negados:
                return bugs

            # Buscar si Bruce pide un dato negado después de la negación
            for i, (role, texto) in enumerate(conv):
                if role != "bruce" or not texto.strip():
                    continue

                texto_l = texto.lower()
                for dato in datos_negados:
                    idx_negacion = negacion_indices.get(dato, -1)
                    if i <= idx_negacion:
                        continue  # Bruce preguntó ANTES de la negación, OK

                    # ¿Bruce pide ese dato después de la negación?
                    pide = False
                    if dato == 'whatsapp' and ('whatsapp' in texto_l or 'wats' in texto_l):
                        pide = True
                    elif dato == 'correo' and ('correo' in texto_l or 'email' in texto_l):
                        pide = True
                    elif dato == 'celular' and 'celular' in texto_l:
                        pide = True

                    if pide:
                        bugs.append({
                            "tipo": "DATO_NEGADO_REINSISTIDO",
                            "severidad": ALTO,
                            "detalle": f"Cliente dijo no tener {dato} pero Bruce lo pidió después: '{texto[:60]}'",
                            "categoria": "contenido"
                        })
                        datos_negados.discard(dato)  # No reportar doble
                        break

        except Exception:
            pass
        return bugs

    # =========================================================
    # FIX 726: RESPUESTA_FILLER_GPT - GPT genera fillers en vez de respuesta real
    # =========================================================
    # Diferente de FIX 715 (fallo TTS → audio hardcodeado "dejeme_ver")
    # Aquí GPT MISMO genera frases vacías como respuesta
    _FILLER_GPT_PATTERNS = re.compile(
        r'^[\s.,!?]*('
        r'd[eé]jeme ver|d[eé]jame ver|d[eé]jeme checar|d[eé]jame checar|'
        r'd[eé]jeme revisar|d[eé]jame revisar|d[eé]jame validarlo|d[eé]jeme validar|'
        r'mm+\s*(entiendo|aja|ok|si|ya)|'
        r'mm+h*|'
        r'aja\s*si|aj[aá]|'
        r'entiendo\s*entiendo|'
        r'ok\s*ok|'
        r'si\s*si\s*si'
        r')[\s.,!?]*$',
        re.IGNORECASE
    )

    # Fillers que son bug SOLO si son la respuesta completa (no seguidos de acción)
    _FILLER_GPT_PARCIAL = re.compile(
        r'^[\s.,!?]*(entiendo|aja|mm+h?|ok|s[ií])[\s.,!?]*$',
        re.IGNORECASE
    )

    @staticmethod
    def _check_respuesta_filler_gpt(respuestas_bruce: list, conv: list) -> list:
        """FIX 726: Detecta cuando GPT genera fillers como respuesta real."""
        bugs = []
        try:
            if len(respuestas_bruce) < 2:
                return bugs

            filler_count = 0
            filler_ejemplos = []

            for i, resp in enumerate(respuestas_bruce):
                resp_stripped = resp.strip()
                if not resp_stripped:
                    continue

                # Match completo: respuesta ES un filler puro
                if ContentAnalyzer._FILLER_GPT_PATTERNS.search(resp_stripped):
                    filler_count += 1
                    if len(filler_ejemplos) < 3:
                        filler_ejemplos.append(resp_stripped[:40])
                # Match parcial: respuesta muy corta y genérica (< 15 chars)
                elif len(resp_stripped) < 15 and ContentAnalyzer._FILLER_GPT_PARCIAL.search(resp_stripped):
                    filler_count += 1
                    if len(filler_ejemplos) < 3:
                        filler_ejemplos.append(resp_stripped[:40])

            # 2+ fillers GPT en una llamada = patrón problemático
            if filler_count >= 2:
                bugs.append({
                    "tipo": "RESPUESTA_FILLER_GPT",
                    "severidad": ALTO if filler_count < 4 else CRITICO,
                    "detalle": f"GPT generó {filler_count}x respuestas filler: {', '.join(filler_ejemplos)}",
                    "categoria": "contenido"
                })

        except Exception:
            pass
        return bugs

    # =========================================================
    # FIX 727: INTERRUPCION_CONVERSACIONAL
    # =========================================================
    # Patrones que indican que el cliente está explicando algo
    _CLIENTE_EXPLICANDO = re.compile(
        r'(no.{0,5}est[aá]|no se encuentra|est[aá] ocupad|sali[oó]|'
        r'mire.{0,15}que|lo que pasa|es que|le explico|'
        r'ahorita.{0,10}est[aá]|viene.{0,10}(?:rato|tarde|mañana)|'
        r'tendr[ií]a.{0,10}(?:marcar|llamar|hablar)|'
        r'no.{0,5}hacemos|no.{0,5}manejamos|no.{0,5}vendemos|'
        r'nosotros.{0,10}(?:somos|no|aqui)|'
        r'(?:la |mi |nuestra )(?:tienda|empresa|negocio).{0,15}(?:es|se dedica|vende))',
        re.IGNORECASE
    )

    @staticmethod
    def _check_interrupcion_conversacional(conv: list) -> list:
        """FIX 727: Detecta si Bruce interrumpe al cliente mientras explica algo."""
        bugs = []
        try:
            if len(conv) < 3:
                return bugs

            for i, (role, texto) in enumerate(conv):
                if role != "cliente" or not texto.strip():
                    continue

                # ¿El cliente está explicando algo?
                if not ContentAnalyzer._CLIENTE_EXPLICANDO.search(texto):
                    continue

                # ¿El texto del cliente parece incompleto? (sin cierre natural)
                texto_stripped = texto.strip()
                termina_completo = texto_stripped.endswith(('.', '?', '!', 'adiós', 'bye', 'gracias'))

                if termina_completo:
                    continue  # Cliente terminó su idea, no es interrupción

                # Buscar siguiente respuesta de Bruce
                for j in range(i + 1, len(conv)):
                    r2, t2 = conv[j]
                    if r2 == "bruce" and t2.strip():
                        # ¿Bruce respondió con algo que ignora lo que el cliente decía?
                        t2_lower = t2.lower()
                        texto_lower_727 = texto.lower()

                        # FIX 772: BRUCE2435/2436 - Si cliente dijo "no está" y Bruce pide
                        # cualquier dato de contacto, es flujo CORRECTO (no interrupción)
                        # "No, no está" → "¿WhatsApp o correo del encargado?" = respuesta apropiada
                        # FIX 843: Expandido - ya no requiere 'encargado' en texto de Bruce
                        _cliente_dijo_no_esta_772 = any(p in texto_lower_727 for p in [
                            'no esta', 'no está', 'no se encuentra', 'no hay',
                            'no esta disponible', 'no está disponible',
                        ])
                        _bruce_pide_contacto_843 = (
                            'whatsapp' in t2_lower or
                            'correo' in t2_lower or
                            'numero' in t2_lower or
                            'número' in t2_lower or
                            'telefono' in t2_lower or
                            'teléfono' in t2_lower or
                            'entiendo' in t2_lower[:20]  # "Entiendo. ¿Me podría..." = acknowledges
                        )
                        if _cliente_dijo_no_esta_772 and _bruce_pide_contacto_843:
                            print(f"  [FIX 843/772] SKIP interrupcion: 'no está' + pedir contacto = flujo correcto")
                            break  # Not a bug

                        # FIX 843: Excepción callback - Si Bruce confirma hora de callback, es respuesta correcta
                        _bruce_confirma_callback_843 = (
                            any(p in t2_lower for p in ['le marco', 'le llamo', 'vuelvo a llamar']) and
                            any(p in t2_lower for p in ['las ', 'hora', 'mañana', 'manana', 'tarde', 'rato'])
                        )
                        if _bruce_confirma_callback_843:
                            print(f"  [FIX 843] SKIP interrupcion: Bruce confirma callback = flujo correcto")
                            break  # Not a bug

                        bruce_ignora = (
                            ContentAnalyzer._PITCH_NIOVAL.search(t2) or
                            ContentAnalyzer._OFERTA_CATALOGO.search(t2) or
                            ('whatsapp' in t2_lower and 'encargado' not in texto_lower_727) or
                            ContentAnalyzer._BRUCE_DESPEDIDA.search(t2)
                        )

                        if bruce_ignora:
                            bugs.append({
                                "tipo": "INTERRUPCION_CONVERSACIONAL",
                                "severidad": ALTO,
                                "detalle": f"Cliente explicaba ('{texto[:50]}') pero Bruce interrumpió: '{t2[:60]}'",
                                "categoria": "contenido"
                            })
                        break
        except Exception:
            pass
        return bugs

    # =========================================================
    # FIX 728: DESPEDIDA_PREMATURA
    # =========================================================
    _CONTACTO_CAPTURADO = re.compile(
        r'(lo anot[eé]|anotado|perfecto.*(?:env[ií]o|mando|tengo)|'
        r'le env[ií]o|se lo env[ií]o|registrado|'
        r'ya.{0,5}tengo.{0,10}(?:dato|n[uú]mero|correo|whatsapp)|'
        r'tom[eé] nota)',
        re.IGNORECASE
    )

    _CLIENTE_INTERESADO = re.compile(
        r'((?<!no )(?<!no me )me interesa|s[ií].{0,10}(?:mand[ea]|env[ií]a)|'
        r'env[ií]ame|m[aá]ndame|'
        r'claro.{0,5}(?:s[ií]|que s[ií])|'
        r'tienes? donde anotar|'
        r'(?:d[ea]me|dame).{0,10}(?:informaci[oó]n|cat[aá]logo))',
        re.IGNORECASE
    )

    @staticmethod
    def _check_despedida_prematura(conv: list, respuestas_bruce: list) -> list:
        """FIX 728: Detecta si Bruce se despide sin haber capturado contacto."""
        bugs = []
        try:
            if len(conv) < 3 or len(respuestas_bruce) < 2:
                return bugs

            # ¿Bruce capturó algún contacto?
            contacto_capturado = any(
                ContentAnalyzer._CONTACTO_CAPTURADO.search(r)
                for r in respuestas_bruce
            )
            if contacto_capturado:
                return bugs  # Tiene contacto, despedida es OK

            # ¿Cliente mostró interés?
            cliente_interesado = any(
                ContentAnalyzer._CLIENTE_INTERESADO.search(t)
                for role, t in conv if role == "cliente"
            )
            if not cliente_interesado:
                return bugs  # Cliente no mostró interés, despedida es normal

            # ¿Bruce se despidió?
            ultima_bruce = ""
            for i in range(len(conv) - 1, -1, -1):
                if conv[i][0] == "bruce":
                    ultima_bruce = conv[i][1]
                    break

            if not ultima_bruce:
                return bugs

            if ContentAnalyzer._DESPEDIDA_BRUCE.search(ultima_bruce):
                bugs.append({
                    "tipo": "DESPEDIDA_PREMATURA",
                    "severidad": ALTO,
                    "detalle": f"Cliente mostró interés pero Bruce se despidió sin capturar contacto: '{ultima_bruce[:60]}'",
                    "categoria": "contenido"
                })

        except Exception:
            pass
        return bugs

    # =========================================================
    # FIX 729: CONTEXTO_IGNORADO (rule-based)
    # =========================================================
    _CLIENTE_ES_DECISOR = re.compile(
        r'(yo soy (?:el|la) (?:encargad[oa]|due[ñn]o|jefe|gerente|administrador|propietari[oa])|'
        r'yo (?:hago|me encargo de?) las compras|'
        r'yo (?:veo|manejo) (?:lo de |las )?compras|'
        r'conmigo es|a m[ií] me (?:puede|podr[ií]a)|'
        r'yo mero|yo soy (?:quien|el que)|'
        r'tienes? donde anotar)',
        re.IGNORECASE
    )

    _BRUCE_IGNORA_DECISOR = re.compile(
        r'(cuando (?:regrese|llegue|venga|est[eé]) (?:el|la) (?:encargad|due[ñn]|jef)|'
        r'le dejo (?:recado|mensaje|el recado)|'
        r'podr[ií]a (?:dejarle|pasarle) (?:el recado|recado)|'
        r'si gusta le dejo|'
        r'le (?:podr[ií]a|puedo) dejar (?:recado|el mensaje))',
        re.IGNORECASE
    )

    @staticmethod
    def _check_contexto_ignorado(conv: list) -> list:
        """FIX 729: Detecta si cliente dice que ES el decisor y Bruce lo trata como empleado."""
        bugs = []
        try:
            if len(conv) < 2:
                return bugs

            for i, (role, texto) in enumerate(conv):
                if role != "cliente" or not texto.strip():
                    continue

                if not ContentAnalyzer._CLIENTE_ES_DECISOR.search(texto):
                    continue

                # Buscar siguiente respuesta de Bruce
                for j in range(i + 1, len(conv)):
                    r2, t2 = conv[j]
                    if r2 == "bruce" and t2.strip():
                        if ContentAnalyzer._BRUCE_IGNORA_DECISOR.search(t2):
                            bugs.append({
                                "tipo": "CONTEXTO_IGNORADO",
                                "severidad": CRITICO,
                                "detalle": f"Cliente dijo ser decisor ('{texto[:50]}') pero Bruce lo ignoró: '{t2[:60]}'",
                                "categoria": "contenido"
                            })
                        break
        except Exception:
            pass
        return bugs

    # =========================================================
    # FIX 730: SALUDO_FALTANTE
    # =========================================================
    _SALUDO_BRUCE = re.compile(
        r'(buenos? (?:d[ií]as?|tardes?|noches?)|buen d[ií]a|'
        r'hola.{0,10}(?:buenos?|buen)|'
        r'me comunico de)',
        re.IGNORECASE
    )

    @staticmethod
    def _check_saludo_faltante(respuestas_bruce: list) -> list:
        """FIX 730: Detecta si Bruce no saludó en su primer turno."""
        bugs = []
        try:
            if not respuestas_bruce:
                return bugs

            primera = respuestas_bruce[0].strip()
            if not primera:
                return bugs

            if not ContentAnalyzer._SALUDO_BRUCE.search(primera):
                bugs.append({
                    "tipo": "SALUDO_FALTANTE",
                    "severidad": MEDIO,
                    "detalle": f"Bruce no saludó en primer turno: '{primera[:60]}'",
                    "categoria": "contenido"
                })

        except Exception:
            pass
        return bugs

    # Palabras que indican que el CLIENTE termino la llamada (no es bug de Bruce)
    _DESPEDIDA_CLIENTE = re.compile(
        r'\b(adi[oó]s|bye|hasta luego|nos vemos|que le vaya bien|gracias.{0,10}buen d[ií]a)\b',
        re.IGNORECASE
    )

    @staticmethod
    def _check_cliente_habla_ultimo(conv: list) -> list:
        """FIX 642A: Detecta si el cliente fue el ultimo en hablar y Bruce nunca respondio.

        Caso BRUCE2070: Cliente dijo 'Tendrias que marcar mas tarde, digame' y Bruce
        quedo en silencio hasta que la llamada termino.

        Excluye: despedidas del cliente (el colgo voluntariamente), mensajes vacios.
        """
        bugs = []
        try:
            if len(conv) < 2:
                return bugs

            # Buscar el ultimo mensaje real (no vacio) de la conversacion
            ultimo_idx = len(conv) - 1
            while ultimo_idx >= 0:
                role, texto = conv[ultimo_idx]
                if texto.strip():
                    break
                ultimo_idx -= 1

            if ultimo_idx < 0:
                return bugs

            role, texto = conv[ultimo_idx]

            # Solo nos interesa si el ultimo mensaje real es del cliente
            if role != "cliente":
                return bugs

            # Excluir si el cliente se despidio (el termino la llamada, no es bug)
            if ContentAnalyzer._DESPEDIDA_CLIENTE.search(texto):
                return bugs

            # FIX 643B: BRUCE2071 - Excluir si Bruce dijo "problemas técnicos" antes
            # (GPT timeout - error esperado, no bug de lógica)
            bruce_dijo_error_tecnico = any(
                r == "bruce" and ("problemas técnicos" in t.lower() or "problemas tecnicos" in t.lower())
                for r, t in conv
            )
            if bruce_dijo_error_tecnico:
                return bugs

            # Verificar que Bruce respondio al menos 1 vez antes (sino es BRUCE_MUDO)
            bruce_respondio_alguna_vez = any(r == "bruce" and t.strip() for r, t in conv)
            if not bruce_respondio_alguna_vez:
                return bugs

            bugs.append({
                "tipo": "CLIENTE_HABLA_ULTIMO",
                "severidad": ALTO,
                "detalle": f"Cliente hablo al final pero Bruce NUNCA respondio: '{texto[:60]}'",
                "categoria": "contenido"
            })

        except Exception:
            pass
        return bugs

    # =========================================================
    # FIX 793B: PREGUNTA_IGNORADA
    # =========================================================
    # Preguntas directas del cliente que requieren respuesta real
    _PREGUNTA_DIRECTA_CLIENTE = re.compile(
        r'((?:¿|¡)?(?:qui[eé]n|de d[oó]nde|de qu[eé]|qu[eé]|a qui[eé]n)'
        r'.{0,30}(?:habla|llama|busca|empresa|marca|vende|ofrece|es usted)\??)',
        re.IGNORECASE
    )

    # Acknowledgments puros de Bruce (modo dictado, sin responder la pregunta)
    _BRUCE_ACK_PURO_793 = re.compile(
        r'^[\s.,!?¡¿]*(claro[,.]?\s*(?:continue|adelante|s[ií])|'
        r's[ií][,.]?\s*(?:adelante|continue|lo escucho)|'
        r'perfecto[,.]?\s*(?:adelante|continue)|'
        r'entendido[,.]?\s*(?:continue|adelante)|'
        r'adelante|continue|lo escucho|aja(?:[,.]?\s*s[ií])?)[\s.,!?]*$',
        re.IGNORECASE
    )

    @staticmethod
    def _check_pregunta_ignorada(conv: list) -> list:
        """FIX 793B: Detecta cuando cliente pregunta directamente y Bruce
        responde con solo acknowledgment sin contestar la pregunta."""
        bugs = []
        try:
            if len(conv) < 4:
                return bugs

            ignoradas = 0
            ejemplos = []

            for i, (role, texto) in enumerate(conv):
                if role != "cliente" or not texto.strip():
                    continue

                # ¿El cliente hizo una pregunta directa?
                if not ContentAnalyzer._PREGUNTA_DIRECTA_CLIENTE.search(texto):
                    continue

                # Buscar siguiente respuesta de Bruce
                for j in range(i + 1, len(conv)):
                    r2, t2 = conv[j]
                    if r2 == "bruce" and t2.strip():
                        # ¿Bruce respondió con solo acknowledgment?
                        if ContentAnalyzer._BRUCE_ACK_PURO_793.search(t2.strip()):
                            ignoradas += 1
                            if len(ejemplos) < 2:
                                ejemplos.append(f"'{texto[:40]}' -> '{t2[:40]}'")
                        break

            if ignoradas >= 1:
                bugs.append({
                    "tipo": "PREGUNTA_IGNORADA",
                    "severidad": ALTO if ignoradas >= 2 else MEDIO,
                    "detalle": f"Cliente pregunto {ignoradas}x pero Bruce solo dio acknowledgment: {'; '.join(ejemplos)}",
                    "categoria": "contenido"
                })

        except Exception:
            pass
        return bugs


# ============================================================
# EVALUACION GPT POST-LLAMADA (FIX 637)
# ============================================================

def _es_comportamiento_correcto(conversacion: list) -> bool:
    """
    FIX 664B: Pre-filtro que detecta casos donde el comportamiento de Bruce es CORRECTO
    y NO debe ser evaluado como bug.

    Retorna True si el comportamiento es intencionalmente correcto.
    """
    if len(conversacion) < 2:
        return False

    try:
        # Extraer último mensaje del cliente
        ultimo_cliente = ""
        for i in range(len(conversacion) - 1, -1, -1):
            if conversacion[i][0] == "cliente":
                ultimo_cliente = conversacion[i][1].lower()
                break

        # Extraer último mensaje de Bruce
        ultimo_bruce = ""
        for i in range(len(conversacion) - 1, -1, -1):
            if conversacion[i][0] == "bruce":
                ultimo_bruce = conversacion[i][1].lower()
                break

        if not ultimo_cliente or not ultimo_bruce:
            return False

        # CASO 1: Cliente dice "¿Bueno?" → Repetir pregunta es CORRECTO
        # FIX 751: Normalizar acentos para compatibilidad con FIX 631 (texto puede venir sin acentos)
        verificaciones_conexion = ['¿bueno?', '¿bueno', 'bueno?', '¿qué?', '¿que?', '¿cómo?', '¿como?', '¿mande?', '¿me escucha?']
        ultimo_cliente_norm = ultimo_cliente.replace('á','a').replace('é','e').replace('í','i').replace('ó','o').replace('ú','u')
        if any(verif in ultimo_cliente for verif in verificaciones_conexion) or any(verif in ultimo_cliente_norm for verif in verificaciones_conexion):
            # Verificar que Bruce repitió pregunta del turno anterior
            if len(conversacion) >= 3:
                for i in range(len(conversacion) - 2, -1, -1):
                    if conversacion[i][0] == "bruce":
                        pregunta_anterior = conversacion[i][1]
                        # Si la pregunta anterior tiene '?' y está en el mensaje actual
                        if '?' in pregunta_anterior:
                            # Buscar palabras clave de la pregunta anterior en mensaje actual
                            palabras_clave = [p for p in pregunta_anterior.split() if len(p) > 4][:3]
                            if any(palabra in ultimo_bruce for palabra in palabras_clave):
                                print(f"[FIX 664B] COMPORTAMIENTO CORRECTO: Cliente verifico conexion ('{ultimo_cliente[:30]}...') -> Bruce repitio pregunta")
                                return True
                        break

        # CASO 2: Cliente no respondió pregunta de Bruce → Repetir es CORRECTO
        # FIX 722: Restringido - NO skip si cliente mencionó rol/cargo (gerente, corporativo, dueño, jefe)
        if len(conversacion) >= 3:
            # FIX 722: Palabras que indican que cliente es decisor (NO skipear GPT eval)
            roles_decisor = ['gerente', 'corporativo', 'dueño', 'dueno', 'jefe', 'encargado',
                           'director', 'administrador', 'propietario', 'yo hago las compras',
                           'yo me encargo', 'yo soy el que']
            cliente_es_decisor = any(rol in ultimo_cliente for rol in roles_decisor)

            if not cliente_es_decisor:
                for i in range(len(conversacion) - 3, -1, -1):
                    if conversacion[i][0] == "bruce":
                        pregunta_bruce = conversacion[i][1].lower()
                        if '?' in pregunta_bruce:
                            # Verificar si cliente respondió sobre el mismo tema
                            if 'encargado' in pregunta_bruce and 'encargado' not in ultimo_cliente:
                                if 'whatsapp' not in ultimo_cliente and 'telefono' not in ultimo_cliente:
                                    print(f"[FIX 664B] ✅ COMPORTAMIENTO CORRECTO: Cliente no respondió pregunta sobre tema específico")
                                    return True
                        break

        # CASO 3: Bruce hablando con IVR (mensajes repetitivos del "cliente")
        mensajes_ivr = ['para ventas marque', 'marque uno', 'le agradecemos su preferencia',
                       'no puede ser atendida', 'deje un mensaje', 'lo siento no lo entiendo']
        if any(msg in ultimo_cliente for msg in mensajes_ivr):
            print(f"[FIX 664B] COMPORTAMIENTO CORRECTO: Cliente es un IVR automatizado")
            return True

        # FIX 793A: CASO 4 ELIMINADO - Antes skipeaba GPT eval en llamadas "exitosas"
        # (muchas gracias, le envio, etc.). Problema: BRUCE2512 tenía respuesta incoherente
        # en Turn 2 pero como capturó contacto, GPT eval se saltó y nunca detectó el bug.
        # Ahora GPT eval siempre corre para detectar bugs en cualquier turno.

        # FASE 2.2: CASO 5: Modismos mexicanos - "dígame/qué necesita" NO es pregunta
        _modismos_go_ahead = ['digame', 'si digame', 'que necesita', 'que se le ofrece',
                              'que le ofrecemos', 'que ocupa', 'en que le ayudo', 'en que le puedo ayudar']
        if any(m in ultimo_cliente.replace('á','a').replace('é','e').replace('í','i').replace('ó','o').replace('ú','u')
               for m in _modismos_go_ahead):
            print(f"[FASE 2.2] COMPORTAMIENTO CORRECTO: Cliente dijo modismo 'go ahead' ('{ultimo_cliente[:30]}')")
            return True

        # FASE 2.2: CASO 6: Llamada < 2 turnos de Bruce → no hay suficiente contexto
        _turnos_bruce = sum(1 for c in conversacion if c[0] == 'bruce')
        if _turnos_bruce < 2:
            print(f"[FASE 2.2] SKIP: Solo {_turnos_bruce} turno(s) de Bruce, insuficiente contexto")
            return True

    except Exception as e:
        print(f"[FIX 664B] Error en pre-filtro: {e}")

    return False


def _extraer_metadata_conversacion(tracker: CallEventTracker) -> dict:
    """
    FIX 664C: Extrae metadata contextual de la llamada para enriquecer GPT evaluation.

    Retorna dict con:
    - patrones_activados: Lista de patrones/fixes que se activaron intencionalmente
    - fixes_aplicados: Lista de correcciones automáticas aplicadas
    - contexto_adicional: Información relevante para la evaluación
    """
    metadata = {
        'patrones_activados': [],
        'fixes_aplicados': [],
        'contexto_adicional': []
    }

    try:
        # Buscar menciones de FIX patterns en los logs de conversación
        conversacion_texto = " ".join([texto for _, texto in tracker.conversacion])

        # Detectar patrones comunes que son comportamiento correcto
        if '¿bueno?' in conversacion_texto.lower():
            metadata['patrones_activados'].append('FIX 621B: VERIFICACION_CONEXION_REPETIR_PREGUNTA')

        if 'te paso su' in conversacion_texto.lower() or 'le paso un' in conversacion_texto.lower():
            metadata['patrones_activados'].append('FIX 626: CLIENTE_OFRECE_CONTACTO')

        # Detectar si fue una llamada muy corta (cliente colgó rápido)
        if len(tracker.respuestas_bruce) <= 2:
            metadata['contexto_adicional'].append('Llamada muy corta - cliente colgó rápido')

        # Detectar si cliente era un IVR
        mensajes_ivr = ['para ventas marque', 'marque uno', 'le agradecemos']
        if any(msg in conversacion_texto.lower() for msg in mensajes_ivr):
            metadata['contexto_adicional'].append('Cliente es sistema IVR automatizado')

    except Exception as e:
        print(f"[FIX 664C] Error extrayendo metadata: {e}")

    return metadata


_GPT_EVAL_PROMPT = """Eres un auditor de calidad para llamadas de ventas de Bruce, agente AI de la marca NIOVAL (productos ferreteros).

Analiza esta conversacion telefonica y detecta SOLO errores claros. NO reportes cosas normales o menores.

MODISMOS MEXICANOS (NO son bugs, son expresiones normales):
- "Si, bueno?" / "Bueno?" = verificacion de conexion telefonica (NO interes)
- "No, joven" / "No, muchacho" / "No, mijo" = rechazo cortes (NO agresion ni queja)
- "Oiga" / "Mire" / "Fijese" = llamar la atencion (NO queja ni reclamo)
- "Ahi le encargo" / "Sale pues" = despedida informal mexicana
- "Que cree" / "Fijese que" = introduccion a informacion (NO pregunta retórica)
- "Mande" / "Mande?" = "no escuche, repita por favor" (NO es un comando)
- "Andale" / "Sale" / "Orale" = confirmacion informal
- "Digame" / "Si digame" / "Que necesita" = "adelante, lo escucho" (NO es pregunta)
- "Tienes donde anotar?" = persona lista para dar datos (ES decisor/encargado)

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
   FIX 750: "Si, bueno?", "Bueno?", "Si, bueno." son VERIFICACION DE CONEXION (= "Sigues ahi?"), NO interes. Ignorar como senal de interes.
6. CONTEXTO_IGNORADO: Bruce trato al interlocutor como empleado/recepcionista cuando ERA el encargado/dueño.
   Senales de que el interlocutor ES el encargado/decisor:
   - "Yo soy el encargado/dueno", "Yo hago las compras", "Tienes donde anotar?" (= listo para dar datos, es decisor)
   - "Que me ofreces?" / "Que venden?" (= interesado como comprador)
   - Ofrece directamente un dato de contacto personal
   Si Bruce responde con "le dejo recado al encargado" o "cuando regrese el encargado" a alguien que ES el encargado, es error GRAVE.
7. RESPUESTA_INCOHERENTE: Bruce dio respuesta generica ("entiendo", "mmm") sin procesar la informacion del cliente.
   Ejemplo: Cliente dice algo especifico -> Bruce solo dice "Entiendo" y cambia de tema sin abordar lo dicho.
   NO es error si "entiendo" va seguido de una accion relevante ("Entiendo. Me podria dar su WhatsApp?")

FIX 664A - REGLAS CRITICAS PARA DETECTAR LOGICA_ROTA (reduce falsos positivos):

1. Bruce repitió pregunta SIN que cliente diera nueva información
   EXCEPCIONES (NO ES BUG, es comportamiento CORRECTO):
   - Si cliente dijo "¿Bueno?" "¿Qué?" "¿Cómo?" "¿Mande?" → Verificación de conexión → Repetir es CORRECTO
   - Si cliente no respondió la pregunta anterior (cambió de tema) → Repetir es CORRECTO
   - Si hubo ruido o cliente pidió que repita → Repetir es CORRECTO

2. Bruce pidió dato que cliente YA proporcionó
   IMPORTANTE: Verificar que el dato esté en el mensaje INMEDIATO anterior (turno previo)
   NO contar si el dato está en turnos anteriores pero NO en contexto reciente (>2 turnos atrás)

3. Bruce ignoró información clave del cliente
   Ejemplo REAL: Cliente mencionó hora "9:00 AM" pero Bruce preguntó "¿A qué hora?"
   Debe estar en el MISMO turno o turno inmediato anterior

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
- Responde SOLO el JSON, sin texto adicional

FIX 646E - CONTEO DE TURNOS:
- Al indicar "turno N", cuenta SOLO los mensajes de Bruce (BRUCE: ...), NO los del cliente
- Turno 1 de Bruce = primer mensaje que dice "BRUCE: ..."
- Turno 2 de Bruce = segundo mensaje que dice "BRUCE: ..."
- NO cuentes mensajes del CLIENTE como turnos de Bruce
- Verifica que el mensaje en el turno reportado fue dicho por Bruce, NO por el cliente"""


# FIX 713B: Prompt ENFOCADO para llamadas cortas (25-45s, 2 turnos)
# Solo busca errores GRAVES de alta certeza - reduce FP en llamadas cortas
_GPT_EVAL_PROMPT_CORTA = """Eres un auditor de calidad para llamadas cortas de Bruce, agente AI de la marca NIOVAL (productos ferreteros).

Esta llamada fue MUY CORTA (el cliente colgó rápido). Solo reporta errores GRAVES y de ALTA CERTEZA.

ERRORES GRAVES a buscar (solo estos 4 tipos):

1. CONTEXTO_IGNORADO: Bruce trató al interlocutor como empleado/recepcionista cuando ERA el encargado/dueño.
   Señales de que el interlocutor ES el encargado/decisor:
   - "Yo soy el encargado/dueño"
   - "Yo hago/me encargo de las compras"
   - "Tienes donde anotar?" (= listo para dar sus datos, es decisor)
   - "Qué me ofreces?" / "Qué venden?" (= interesado como comprador)
   - Ofrece directamente un dato de contacto personal
   Si Bruce responde con "le dejo recado al encargado" o "cuando regrese el encargado" a alguien que ES el encargado, es error GRAVE.

2. RESPUESTA_INCOHERENTE: Bruce dio respuesta genérica ("entiendo", "mmm") sin procesar la información del cliente.
   Ejemplo: Cliente dice algo específico → Bruce solo dice "Entiendo" y cambia de tema sin abordar lo dicho.
   NO es error si "entiendo" va seguido de una acción relevante ("Entiendo. ¿Me podría dar su WhatsApp?").

3. LOGICA_ROTA: Bruce pidió dato que el cliente YA proporcionó en el turno anterior.

4. OPORTUNIDAD_PERDIDA: Cliente mostró interés claro o ofreció datos, y Bruce respondió con despedida o tema irrelevante.
   FIX 750: BRUCE2321 - "Sí, bueno?", "¿Bueno?", "Sí, bueno." son VERIFICACION DE CONEXION en México (= "¿Sigues ahí?").
   NO son expresiones de interés. Si cliente dijo "Sí, bueno?" y Bruce continuó con pregunta de contacto, eso es CORRECTO.
   "No, joven" seguido de "Sí, bueno?" = cliente verificó conexión tras pausa, NO mostró interés.

CONVERSACION:
{conversacion}

Responde SOLO en este formato JSON (array vacio si no hay errores):
[
  {{"tipo": "TIPO_ERROR", "severidad": "ALTO", "turno": N, "detalle": "descripcion breve"}}
]

REGLAS ESTRICTAS:
- SOLO reporta errores de los 4 tipos listados arriba
- Si tienes DUDA, NO reportes (mejor no reportar que falso positivo)
- Si Bruce se despidió tras rechazo del cliente, NO es error
- Si la llamada fue normal (pitch → encargado → catálogo → despedida), NO reportes nada
- Al indicar turno N, cuenta SOLO mensajes de BRUCE (no del cliente)
- Maximo 2 errores por llamada corta
- Responde SOLO el JSON, sin texto adicional"""


def _evaluar_con_gpt(tracker: CallEventTracker) -> list:
    """Evalua la conversacion con GPT-4o-mini. Retorna lista de bugs."""
    bugs = []
    try:
        # Solo evaluar si hay suficientes turnos
        if len(tracker.respuestas_bruce) < GPT_EVAL_MIN_TURNOS:
            return bugs

        # FIX 713A: Threshold dinámico - determinar tipo de evaluación
        duracion_llamada = int(time.time() - tracker.created_at)
        num_turnos = len(tracker.respuestas_bruce)

        # FIX 717: Ultra-corta (< 20s) → SKIP total (bajado de 25s)
        if duracion_llamada < GPT_EVAL_MIN_DURACION_S:
            print(f"[FIX 717] Llamada {tracker.bruce_id}: Solo {duracion_llamada}s, SKIP GPT eval (min {GPT_EVAL_MIN_DURACION_S}s)")
            return bugs

        # FIX 713A: Determinar si es llamada corta (25-45s o 2 turnos) vs normal (>45s y 3+ turnos)
        es_llamada_corta = (duracion_llamada < GPT_EVAL_DURACION_CORTA_S or num_turnos < GPT_EVAL_MIN_TURNOS_COMPLETO)

        if es_llamada_corta:
            print(f"[FIX 713A] Llamada {tracker.bruce_id}: {duracion_llamada}s/{num_turnos} turnos -> GPT eval ENFOCADO (llamada corta)")
        else:
            print(f"[FIX 713A] Llamada {tracker.bruce_id}: {duracion_llamada}s/{num_turnos} turnos -> GPT eval COMPLETO")

        # FIX 735: Pre-filtro IVR - NO evaluar conversaciones con conmutador automático
        _IVR_735 = re.compile(
            r'(extensi[oó]n|m[aá]rquelo ahora|seleccione una|presione\s+(?:uno|dos|tres|\d)|'
            r'espere en la l[ií]nea|para ser atendido)',
            re.IGNORECASE
        )
        texto_cliente_735 = ' '.join(t for who, t in tracker.conversacion if who == 'cliente')
        if _IVR_735.search(texto_cliente_735):
            print(f"[FIX 735] Llamada {tracker.bruce_id}: IVR/conmutador detectado, SKIP GPT eval")
            return bugs

        # FIX 664B: Pre-filtro - detectar comportamiento correcto ANTES de GPT
        if _es_comportamiento_correcto(tracker.conversacion):
            print(f"[FIX 664B] Llamada {tracker.bruce_id}: Comportamiento correcto detectado, SKIP GPT eval")
            return bugs

        # FIX 664C: Extraer metadata contextual
        metadata = _extraer_metadata_conversacion(tracker)

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

        # FIX 713A: Seleccionar prompt según tipo de llamada
        if es_llamada_corta:
            # Llamada corta → prompt enfocado (solo errores graves)
            prompt_base = _GPT_EVAL_PROMPT_CORTA
            max_errores = 2
        else:
            # Llamada normal → prompt completo con metadata
            prompt_base = _GPT_EVAL_PROMPT
            max_errores = 3

        # FIX 664C: Agregar metadata contextual al prompt (solo para eval completo)
        contexto_adicional = ""
        if not es_llamada_corta:
            if metadata['patrones_activados']:
                contexto_adicional += "\n\nPATRONES DETECTADOS (comportamientos intencionalmente correctos):\n"
                for patron in metadata['patrones_activados']:
                    contexto_adicional += f"- {patron}\n"

            if metadata['contexto_adicional']:
                contexto_adicional += "\n\nCONTEXTO ADICIONAL:\n"
                for ctx in metadata['contexto_adicional']:
                    contexto_adicional += f"- {ctx}\n"

        # Insertar metadata al inicio del prompt después del contexto
        prompt_con_metadata = prompt_base.replace(
            "CONVERSACION:",
            f"{contexto_adicional}\n\nCONVERSACION:"
        )

        # Lazy import de openai
        import openai
        api_key = os.environ.get("OPENAI_API_KEY", "")
        if not api_key:
            return bugs

        client = openai.OpenAI(api_key=api_key)

        # FIX 713A: Usar prompt según tipo de llamada
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": prompt_con_metadata.format(conversacion=conversacion_texto)}
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

        for error in errores[:max_errores]:  # FIX 713A: max_errores según tipo
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
    """FIX 640+691+748: Carga bugs desde disco al iniciar."""
    global _recent_bugs, _bugs_loaded
    try:
        print(f"[BUG_DETECTOR] FIX 748: PERSISTENT_DIR={os.path.abspath(_PERSISTENT_DIR)}")
        print(f"[BUG_DETECTOR] FIX 691: Buscando bugs en {os.path.abspath(_BUGS_FILE)}")
        if os.path.exists(_BUGS_FILE):
            import json
            with open(_BUGS_FILE, 'r', encoding='utf-8') as f:
                loaded = json.load(f)
            if isinstance(loaded, list):
                _recent_bugs = loaded[-MAX_BUGS_HISTORY:]
                print(f"[BUG_DETECTOR] Cargados {len(_recent_bugs)} bugs desde disco")
            else:
                print(f"[BUG_DETECTOR] Archivo bugs existe pero formato invalido: {type(loaded)}")
        else:
            print(f"[BUG_DETECTOR] No hay bugs previos en disco (archivo no existe)")
        _bugs_loaded = True
    except Exception as e:
        print(f"[BUG_DETECTOR] Error cargando bugs: {e}")
        _bugs_loaded = True


def _save_bugs(force=False):
    """FIX 640+691: Guarda bugs a disco. force=True bypasses throttle (usado en shutdown)."""
    global _bugs_last_save
    try:
        now = time.time()
        if not force and (now - _bugs_last_save) < _BUGS_SAVE_INTERVAL:
            return
        import json
        os.makedirs(os.path.dirname(_BUGS_FILE) or '.', exist_ok=True)
        with open(_BUGS_FILE, 'w', encoding='utf-8') as f:
            json.dump(_recent_bugs, f, ensure_ascii=False)
            f.flush()
            os.fsync(f.fileno())  # FIX 691: Garantizar escritura a disco
        _bugs_last_save = now
    except Exception as e:
        print(f"[BUG_DETECTOR] Error guardando bugs a disco: {e}")


def _flush_bugs_on_exit():
    """FIX 691: Flush forzoso de bugs al cerrar proceso (deploy/SIGTERM)."""
    try:
        if _recent_bugs:
            _save_bugs(force=True)
            print(f"[BUG_DETECTOR] Flush de {len(_recent_bugs)} bugs a disco (shutdown)")
    except Exception as e:
        print(f"[BUG_DETECTOR] Error en flush de shutdown: {e}")


# FIX 691: Registrar handlers para persistir bugs en shutdown
atexit.register(_flush_bugs_on_exit)


def _sigterm_handler(signum, frame):
    """FIX 691: Handler SIGTERM - Railway envia SIGTERM antes de matar proceso."""
    print("[BUG_DETECTOR] SIGTERM recibido, guardando bugs...")
    _flush_bugs_on_exit()
    sys.exit(0)


try:
    signal.signal(signal.SIGTERM, _sigterm_handler)
except (OSError, ValueError):
    # signal.signal puede fallar si no estamos en main thread
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
            "deploy": _DEPLOY_VERSION,
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

            _save_bugs(force=True)  # FIX 691: Persistir inmediatamente cada bug nuevo

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
            "deploy": _DEPLOY_VERSION,
            "bugs": gpt_bugs,
            "stats": base_entry.get("stats", {})
        }

        with _lock:
            _recent_bugs.append(gpt_entry)
            while len(_recent_bugs) > MAX_BUGS_HISTORY:
                _recent_bugs.pop(0)

        _save_bugs(force=True)  # FIX 691: Persistir inmediatamente

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
        deploy = entry.get("deploy", "---")
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
                <td><span style="color:#888;font-size:11px">{deploy}</span></td>
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
                <th>Hora</th><th>BRUCE ID</th><th>Deploy</th><th>Tel</th><th>Cat</th>
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
<p style="color:#88ff88;font-size:14px">Deploy actual: <b>{_DEPLOY_VERSION}</b></p>
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
