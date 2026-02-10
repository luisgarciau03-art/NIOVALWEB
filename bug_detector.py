"""
FIX 632: Bug Detector - Deteccion automatica de bugs en llamadas.

Modulo independiente que rastrea eventos por llamada y detecta 5 tipos de bugs:
1. BRUCE_MUDO: TwiML enviado pero audio nunca fetcheado por Twilio
2. LOOP: Bruce repite la misma respuesta 3+ veces
3. SILENCIO_PROLONGADO: Cliente dice "Bueno?" 2+ veces (Bruce no responde)
4. PATRON_INVALIDADO_FRECUENTE: 3+ patrones invalidados en 1 llamada
5. RESPUESTA_VACIA: GPT retorno vacio 2+ veces en 1 llamada

Cada funcion publica esta envuelta en try/except - CERO impacto en path critico.
"""

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

# Retener bugs recientes (max)
MAX_BUGS_HISTORY = 200


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
            elif event_type == "CLIENTE_DICE":
                texto = (data or {}).get("texto", "")
                self.textos_cliente.append(texto)
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
# DETECTOR DE BUGS
# ============================================================

class BugDetector:
    """Analiza un CallEventTracker al terminar la llamada."""

    @staticmethod
    def analyze(tracker: CallEventTracker) -> list:
        """
        Retorna lista de bugs detectados.
        Cada bug: {"tipo": str, "severidad": str, "detalle": str}
        """
        bugs = []
        try:
            # 1. BRUCE_MUDO: TwiML enviado pero audio no fetcheado
            if tracker.twiml_count > 0 and tracker.audio_fetch_count == 0:
                bugs.append({
                    "tipo": "BRUCE_MUDO",
                    "severidad": CRITICO,
                    "detalle": f"TwiML enviado {tracker.twiml_count}x pero audio fetcheado 0x"
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
                            "detalle": f"Respuesta repetida {count}x: '{resp[:60]}...'"
                        })
                        break

            # 3. SILENCIO_PROLONGADO: Cliente dice "Bueno?" 2+ veces
            if tracker.cliente_dijo_bueno >= 2:
                bugs.append({
                    "tipo": "SILENCIO_PROLONGADO",
                    "severidad": ALTO,
                    "detalle": f"Cliente dijo 'Bueno?'/'Hola?' {tracker.cliente_dijo_bueno}x (Bruce no responde)"
                })

            # 4. PATRON_INVALIDADO_FRECUENTE: 3+ invalidaciones
            if tracker.patrones_invalidados >= 3:
                bugs.append({
                    "tipo": "PATRON_INVALIDADO_FRECUENTE",
                    "severidad": MEDIO,
                    "detalle": f"{tracker.patrones_invalidados} patrones invalidados en 1 llamada"
                })

            # 5. RESPUESTA_VACIA: GPT vacio 2+ veces
            if tracker.respuestas_vacias >= 2:
                bugs.append({
                    "tipo": "RESPUESTA_VACIA",
                    "severidad": ALTO,
                    "detalle": f"GPT retorno vacio {tracker.respuestas_vacias}x en esta llamada"
                })

        except Exception:
            pass  # Nunca fallar

        return bugs


# ============================================================
# ESTADO GLOBAL (thread-safe)
# ============================================================

_lock = threading.Lock()
_active_trackers = {}     # call_sid -> CallEventTracker
_recent_bugs = []         # Lista de bugs recientes


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

        bugs = BugDetector.analyze(tracker)
        if bugs:
            # Guardar en historial
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
            with _lock:
                _recent_bugs.append(bug_entry)
                # Limpiar si excede limite
                while len(_recent_bugs) > MAX_BUGS_HISTORY:
                    _recent_bugs.pop(0)

            # Enviar alerta Telegram en background
            threading.Thread(
                target=_enviar_alerta_telegram,
                args=(bug_entry,),
                daemon=True
            ).start()

            print(f"[BUG_DETECTOR] {tracker.bruce_id}: {len(bugs)} bug(s) detectado(s)")
            for bug in bugs:
                print(f"  [{bug['severidad']}] {bug['tipo']}: {bug['detalle']}")

    except Exception as e:
        print(f"[BUG_DETECTOR] Error en analyze_and_cleanup: {e}")


def get_recent_bugs(limit: int = 50) -> list:
    """Retorna bugs recientes (mas reciente primero)."""
    try:
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
        bugs_importantes = [b for b in bugs if b["severidad"] in (CRITICO, ALTO)]
        if not bugs_importantes:
            return

        # Construir mensaje
        lineas = [f"<b>BUG DETECTADO en {bruce_id}</b>"]
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
    bugs = get_recent_bugs(50)

    rows = []
    for entry in bugs:
        bruce_id = entry.get("bruce_id", "???")
        telefono = entry.get("telefono", "")
        timestamp = entry.get("timestamp", "")
        stats = entry.get("stats", {})

        for bug in entry.get("bugs", []):
            severidad = bug["severidad"]
            if severidad == CRITICO:
                color = "#ff4444"
            elif severidad == ALTO:
                color = "#ffaa00"
            else:
                color = "#44aaff"

            rows.append(f"""
            <tr>
                <td>{timestamp}</td>
                <td><b>{bruce_id}</b></td>
                <td>{telefono}</td>
                <td style="color:{color};font-weight:bold">{bug['tipo']}</td>
                <td style="color:{color}">{severidad}</td>
                <td>{bug['detalle']}</td>
                <td>{stats.get('turnos', '?')}t / {stats.get('duracion_s', '?')}s</td>
            </tr>""")

    if not rows:
        tabla = "<p>Sin bugs detectados. Las alertas aparecen cuando se detectan anomalias en llamadas.</p>"
    else:
        tabla = f"""
        <table border="1" cellpadding="6" cellspacing="0" style="border-collapse:collapse;width:100%;font-size:14px">
            <tr style="background:#333;color:white">
                <th>Hora</th><th>BRUCE ID</th><th>Telefono</th>
                <th>Bug</th><th>Severidad</th><th>Detalle</th><th>Stats</th>
            </tr>
            {''.join(rows)}
        </table>"""

    # Contar por tipo
    conteo = defaultdict(int)
    for entry in bugs:
        for bug in entry.get("bugs", []):
            conteo[bug["tipo"]] += 1

    resumen = " | ".join(f"{tipo}: {cnt}" for tipo, cnt in sorted(conteo.items())) or "Ninguno"

    return f"""<!DOCTYPE html>
<html><head>
<meta charset="utf-8">
<title>Bruce W - Bug Detector</title>
<style>
    body {{ font-family: monospace; margin: 20px; background: #1a1a1a; color: #eee; }}
    h1 {{ color: #ff6644; }}
    table {{ background: #222; }}
    tr:nth-child(even) {{ background: #2a2a2a; }}
    th {{ text-align: left; }}
    a {{ color: #44aaff; }}
    .resumen {{ background: #333; padding: 10px; border-radius: 5px; margin: 10px 0; }}
</style>
</head><body>
<h1>Bug Detector - Bruce W</h1>
<p><a href="/historial-llamadas">Historial</a> | <a href="/bugs">Bugs</a></p>
<div class="resumen">
    <b>Resumen:</b> {resumen}<br>
    <b>Total entradas:</b> {len(bugs)}
</div>
{tabla}
<p style="color:#666;margin-top:20px">
    Tipos: BRUCE_MUDO (audio no llega) | LOOP (respuesta repetida) |
    SILENCIO_PROLONGADO (cliente espera) | PATRON_INVALIDADO_FRECUENTE |
    RESPUESTA_VACIA (GPT falla)
</p>
</body></html>"""
