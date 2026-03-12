"""
Bruce v2.5 — Servidor Realtime API (Hibrido FSM + STT)

Arquitectura:
  Twilio WS audio -> OpenAI Realtime (SOLO STT, auto-response suprimido)
    -> transcription event
    -> AgenteVentas.procesar_respuesta(texto) [via asyncio.to_thread]
    -> Audio cache ulaw (si template) | ElevenLabs WS TTS (si dinamico)
    -> Twilio WS audio out

Reemplaza: servidor_llamadas.py (Flask, 9344 lineas, TwiML <Play>/<Record>)
Elimina: Azure Speech STT, Deepgram STT
Mantiene: FSM engine (1195+ fixes), audio cache, ElevenLabs TTS, Google Sheets
"""

import os
import sys
import json
import asyncio
import logging
import base64
import time
import io
import re
import subprocess
from datetime import datetime
from pathlib import Path
from collections import defaultdict, deque

import websockets
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.responses import HTMLResponse, JSONResponse, Response
from twilio.rest import Client as TwilioClient
from twilio.twiml.voice_response import VoiceResponse, Connect
from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger("bruce_v2")

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_PHONE_NUMBER = os.getenv("TWILIO_PHONE_NUMBER")
OPENAI_API_KEY_STT = os.getenv("OPENAI_API_KEY_STT", OPENAI_API_KEY)

# OpenAI Realtime API URL (STT only)
OPENAI_REALTIME_URL = "wss://api.openai.com/v1/realtime?model=gpt-4o-realtime-preview"

# ---------------------------------------------------------------------------
# Multi-voice system
# ---------------------------------------------------------------------------
VOCES_DISPONIBLES = {
    "bruce_w": {
        "voice_id": "7uSWXMmzGnsyxZwYFfmK",
        "nombre": "Bruce W - Masculina Original",
        "cache_dir": "audio_cache",
    },
    "diana_sanchez": {
        "voice_id": "FIhWHKTvfI9sX1beLEJ8",
        "nombre": "Diana Sanchez - Femenina",
        "cache_dir": "audio_cache_diana_sanchez",
    },
    "mauricio": {
        "voice_id": "94zOad0g7T7K4oa7zhDq",
        "nombre": "Mauricio - Masculina",
        "cache_dir": "audio_cache_mauricio",
    },
}

_voz_env = os.getenv("VOZ_ACTIVA", "bruce_w")
VOZ_ACTIVA = _voz_env if _voz_env in VOCES_DISPONIBLES else "bruce_w"
ELEVENLABS_VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID") or VOCES_DISPONIBLES[VOZ_ACTIVA]["voice_id"]
CACHE_DIR = os.getenv("CACHE_DIR", VOCES_DISPONIBLES[VOZ_ACTIVA]["cache_dir"])

log.info(f"VOZ ACTIVA: {VOZ_ACTIVA} ({VOCES_DISPONIBLES[VOZ_ACTIVA]['nombre']})")
log.info(f"VOICE ID: {ELEVENLABS_VOICE_ID}")
log.info(f"CACHE DIR: {CACHE_DIR}")

# ElevenLabs WS URL (ulaw output for Twilio)
ELEVENLABS_WS_URL = (
    f"wss://api.elevenlabs.io/v1/text-to-speech/{ELEVENLABS_VOICE_ID}/stream-input"
    f"?model_id=eleven_multilingual_v2"
    f"&output_format=ulaw_8000"
)

# ElevenLabs BOS (Beginning of Stream) config
ELEVENLABS_BOS = {
    "text": " ",
    "voice_settings": {
        "stability": 0.35,
        "similarity_boost": 0.80,
        "style": 0.40,
        "use_speaker_boost": True,
    },
    "generation_config": {
        "chunk_length_schedule": [120, 160, 250, 290],
    },
}

# ---------------------------------------------------------------------------
# Twilio client
# ---------------------------------------------------------------------------
twilio_client = None
if TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN:
    twilio_client = TwilioClient(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
    log.info("Twilio client inicializado")

# ---------------------------------------------------------------------------
# OpenAI client (for GPT fallback in FSM)
# ---------------------------------------------------------------------------
openai_client = None
try:
    from openai import OpenAI
    openai_client = OpenAI(api_key=OPENAI_API_KEY)
    log.info("OpenAI client inicializado (GPT fallback)")
except ImportError:
    log.warning("openai package no instalado")

# ---------------------------------------------------------------------------
# Google Sheets managers
# ---------------------------------------------------------------------------
sheets_manager = None
resultados_manager = None
logs_manager = None
whatsapp_validator = None

try:
    from nioval_sheets_adapter import NiovalSheetsAdapter
    from resultados_sheets_adapter import ResultadosSheetsAdapter
    from logs_sheets_adapter import LogsSheetsAdapter
    sheets_manager = NiovalSheetsAdapter()
    resultados_manager = ResultadosSheetsAdapter()
    logs_manager = LogsSheetsAdapter()
    log.info("Google Sheets Managers inicializados")
except Exception as e:
    log.warning(f"Google Sheets no disponible: {e}")

try:
    from whatsapp_validator import WhatsAppValidator
    whatsapp_validator = WhatsAppValidator()
    log.info("WhatsApp Validator inicializado")
except Exception as e:
    log.warning(f"WhatsApp Validator no disponible: {e}")

# ---------------------------------------------------------------------------
# Bug Detector
# ---------------------------------------------------------------------------
BUG_DETECTOR_AVAILABLE = False
try:
    from bug_detector import (
        get_or_create_tracker, emit_event, analyze_and_cleanup,
        generar_bugs_html, set_deploy_version,
    )
    BUG_DETECTOR_AVAILABLE = True
except ImportError:
    log.warning("Bug detector no disponible")

# ---------------------------------------------------------------------------
# Deploy info
# ---------------------------------------------------------------------------
DEPLOY_ID = datetime.now().strftime("%Y-%m-%d %H:%M")
_commit_msg = os.getenv("RAILWAY_GIT_COMMIT_MESSAGE", "")
_deploy_id = os.getenv("RAILWAY_DEPLOYMENT_ID", "")
if _commit_msg:
    DEPLOY_NAME = _commit_msg.split(":")[0][:15].strip() if ":" in _commit_msg else _commit_msg[:15].strip()
elif _deploy_id:
    DEPLOY_NAME = _deploy_id[:8]
else:
    DEPLOY_NAME = datetime.now().strftime("%m-%d %H:%M")

if BUG_DETECTOR_AVAILABLE:
    set_deploy_version(f"{DEPLOY_NAME} ({DEPLOY_ID})")
    log.info(f"[BUG_DETECTOR] Deploy version: {DEPLOY_NAME} ({DEPLOY_ID})")

# ---------------------------------------------------------------------------
# OpenAI Realtime session config (STT-only mode)
# ---------------------------------------------------------------------------
SESSION_CONFIG = {
    "type": "session.update",
    "session": {
        "instructions": "",  # Empty — we don't use Realtime's LLM
        "output_modalities": ["text"],
        "input_audio_format": "g711_ulaw",
        "input_audio_transcription": {
            "model": "gpt-4o-mini-transcription",
        },
        "turn_detection": {
            "type": "server_vad",
            "threshold": 0.5,
            "prefix_padding_ms": 300,
            "silence_duration_ms": 500,
        },
        "tools": [],
        "tool_choice": "none",
    },
}

# ---------------------------------------------------------------------------
# Audio cache (MP3 from disk -> base64 ulaw for Twilio WS)
# ---------------------------------------------------------------------------
audio_cache_mp3 = {}       # key -> filepath (MP3)
audio_cache_ulaw = {}      # key -> list of base64 ulaw chunks
cache_metadata = {}

def cargar_cache_desde_disco():
    """Load MP3 audio cache from disk at startup."""
    global cache_metadata

    if not os.path.exists(CACHE_DIR):
        os.makedirs(CACHE_DIR, exist_ok=True)
        log.info("Directorio de cache creado")
        return

    metadata_file = os.path.join(CACHE_DIR, "metadata.json")
    if os.path.exists(metadata_file):
        with open(metadata_file, "r", encoding="utf-8") as f:
            cache_metadata = json.load(f)

        for key, filename in cache_metadata.items():
            filepath = os.path.join(CACHE_DIR, filename)
            if os.path.exists(filepath):
                audio_cache_mp3[key] = filepath

        log.info(f"{len(audio_cache_mp3)} audios MP3 cargados desde metadata.json")

    # Recover orphan MP3 files
    archivos_en_metadata = set(cache_metadata.values())
    archivos_recuperados = 0
    for archivo in os.listdir(CACHE_DIR):
        if not archivo.endswith(".mp3"):
            continue
        if archivo in archivos_en_metadata:
            continue
        if len(archivo) > 17 and archivo[-17] == "_":
            key_recuperada = archivo[:-17]
        else:
            key_recuperada = archivo.rsplit(".", 1)[0]

        filepath = os.path.join(CACHE_DIR, archivo)
        if os.path.getsize(filepath) < 1024:
            continue
        if key_recuperada not in audio_cache_mp3:
            audio_cache_mp3[key_recuperada] = filepath
            cache_metadata[key_recuperada] = archivo
            archivos_recuperados += 1

    if archivos_recuperados > 0:
        with open(metadata_file, "w", encoding="utf-8") as f:
            json.dump(cache_metadata, f, ensure_ascii=False, indent=2)
        log.info(f"{archivos_recuperados} audios huerfanos recuperados")

    log.info(f"TOTAL audios en cache: {len(audio_cache_mp3)}")


def convertir_mp3_a_ulaw_chunks(filepath: str) -> list:
    """Convert MP3 file to list of base64-encoded ulaw_8000 chunks for Twilio WS.

    Uses ffmpeg if available, otherwise falls back to pydub.
    Each chunk is ~20ms of audio (~160 bytes) base64-encoded.
    """
    import subprocess
    import struct

    try:
        # Use ffmpeg to convert MP3 -> raw mulaw 8000Hz mono
        result = subprocess.run(
            [
                "ffmpeg", "-i", filepath,
                "-f", "mulaw", "-ar", "8000", "-ac", "1",
                "-loglevel", "error", "pipe:1",
            ],
            capture_output=True,
            timeout=10,
        )
        if result.returncode != 0:
            log.warning(f"ffmpeg error for {filepath}: {result.stderr.decode()}")
            return []

        raw_ulaw = result.stdout
    except FileNotFoundError:
        # ffmpeg not available, try pydub
        try:
            from pydub import AudioSegment
            audio = AudioSegment.from_mp3(filepath)
            audio = audio.set_frame_rate(8000).set_channels(1).set_sample_width(1)
            raw_ulaw = audio.raw_data
        except Exception as e:
            log.warning(f"Cannot convert {filepath}: {e}")
            return []
    except Exception as e:
        log.warning(f"Error converting {filepath}: {e}")
        return []

    # Split into ~20ms chunks (160 bytes at 8000Hz mulaw)
    chunk_size = 160
    chunks = []
    for i in range(0, len(raw_ulaw), chunk_size):
        chunk = raw_ulaw[i:i + chunk_size]
        chunks.append(base64.b64encode(chunk).decode("ascii"))

    return chunks


def precargar_cache_ulaw():
    """Pre-convert frequently used MP3 cache entries to ulaw chunks.

    Called at startup in a background thread.
    """
    converted = 0
    for key, filepath in audio_cache_mp3.items():
        if key in audio_cache_ulaw:
            continue
        chunks = convertir_mp3_a_ulaw_chunks(filepath)
        if chunks:
            audio_cache_ulaw[key] = chunks
            converted += 1

    log.info(f"Pre-converted {converted} audios to ulaw format")


def buscar_audio_cache(texto_respuesta: str):
    """Search for cached ulaw audio matching the response text.

    Returns list of base64 chunks if found, None otherwise.
    """
    # Normalize text for cache lookup
    key = texto_respuesta.strip().lower()
    # Remove punctuation for fuzzy matching
    key_clean = key.replace(".", "").replace(",", "").replace("?", "").replace("!", "").strip()

    # Direct match
    if key in audio_cache_ulaw:
        return audio_cache_ulaw[key]
    if key_clean in audio_cache_ulaw:
        return audio_cache_ulaw[key_clean]

    # Search in MP3 cache and convert on-the-fly
    if key in audio_cache_mp3:
        chunks = convertir_mp3_a_ulaw_chunks(audio_cache_mp3[key])
        if chunks:
            audio_cache_ulaw[key] = chunks
            return chunks
    if key_clean in audio_cache_mp3:
        chunks = convertir_mp3_a_ulaw_chunks(audio_cache_mp3[key_clean])
        if chunks:
            audio_cache_ulaw[key_clean] = chunks
            return chunks

    return None


# ---------------------------------------------------------------------------
# Per-call state
# ---------------------------------------------------------------------------
conversaciones_activas = {}   # call_sid -> AgenteVentas instance
contactos_llamadas = {}       # call_sid -> contacto_info
callsid_to_bruceid = {}       # call_sid -> bruce_id
grabaciones_por_bruce = {}    # bruce_id -> recording_url

# ---------------------------------------------------------------------------
# Historial persistence (survives deploys via JSON on disk)
# ---------------------------------------------------------------------------
HISTORIAL_FILE = os.path.join(CACHE_DIR, "historial_llamadas.json")
CALIFICACIONES_FILE = os.path.join(CACHE_DIR, "calificaciones_llamadas.json")


def cargar_historial():
    try:
        if os.path.exists(HISTORIAL_FILE):
            with open(HISTORIAL_FILE, "r", encoding="utf-8") as f:
                return deque(json.load(f), maxlen=500)
    except Exception as e:
        log.warning(f"Error cargando historial: {e}")
    return deque(maxlen=500)


def guardar_historial():
    try:
        os.makedirs(os.path.dirname(HISTORIAL_FILE) or ".", exist_ok=True)
        with open(HISTORIAL_FILE, "w", encoding="utf-8") as f:
            json.dump(list(historial_llamadas), f, ensure_ascii=False, indent=2)
    except Exception as e:
        log.warning(f"Error guardando historial: {e}")


def cargar_calificaciones():
    try:
        if os.path.exists(CALIFICACIONES_FILE):
            with open(CALIFICACIONES_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception as e:
        log.warning(f"Error cargando calificaciones: {e}")
    return {}


def guardar_calificaciones(calificaciones):
    try:
        os.makedirs(os.path.dirname(CALIFICACIONES_FILE) or ".", exist_ok=True)
        with open(CALIFICACIONES_FILE, "w", encoding="utf-8") as f:
            json.dump(calificaciones, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        log.warning(f"Error guardando calificaciones: {e}")
        return False


def registrar_llamada(bruce_id, telefono, negocio, resultado, duracion=0, detalles=None, call_sid=None):
    """Register a call in the persistent historial."""
    if call_sid and bruce_id:
        callsid_to_bruceid[call_sid] = bruce_id

    historial_llamadas.append({
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "bruce_id": bruce_id,
        "telefono": telefono,
        "negocio": negocio,
        "resultado": resultado,
        "duracion": duracion,
        "detalles": detalles or {},
        "call_sid": call_sid,
        "deploy_id": DEPLOY_ID,
        "deploy_name": DEPLOY_NAME,
    })
    guardar_historial()


historial_llamadas = cargar_historial()
calificaciones_llamadas = cargar_calificaciones()
log.info(f"{len(historial_llamadas)} llamadas en historial, {len(calificaciones_llamadas)} calificaciones")


# ---------------------------------------------------------------------------
# Segunda parte del saludo (cached response for simple greetings)
# ---------------------------------------------------------------------------
SALUDOS_SIMPLES = [
    "hola", "buenas", "buenas tardes", "buenos días", "buenos dias",
    "buen día", "buen dia", "bueno", "sí", "si", "dígame", "digame",
    "mande", "aló", "alo", "qué pasó", "que paso", "sí bueno", "si bueno",
    "qué se le ofrece", "que se le ofrece", "en qué le ayudo", "en que le ayudo",
    "con quién hablo", "con quien hablo", "quién es", "quien es",
    "muy buenas", "muy buenas tardes", "muy buenos días", "muy buenos dias",
    "aquí", "aqui", "presente", "escucho", "le escucho", "lo escucho",
]

SEGUNDA_PARTE_SALUDO = (
    "Me comunico de la marca nioval, mas que nada queria brindar informacion "
    "de nuestros productos ferreteros, Se encontrara el encargado o encargada de compras?"
)


def detectar_segunda_parte_saludo(agente, texto: str) -> str | None:
    """If this is the first client response and it's a simple greeting,
    return the cached segunda parte instead of calling GPT.

    Returns the response text or None if not applicable.
    """
    speech_lower = texto.lower().strip()
    palabras = texto.split()

    # Only for first response (1 assistant message = saludo)
    mensajes_bruce = [m for m in agente.conversation_history if m["role"] == "assistant"]
    if len(mensajes_bruce) != 1:
        return None

    # Must be short (<=5 words) and match a greeting
    if len(palabras) > 5:
        return None

    if not any(s in speech_lower for s in SALUDOS_SIMPLES):
        return None

    # Check if pitch was already given (edge case)
    ya_presento = any(
        "nioval" in m.get("content", "").lower()
        for m in agente.conversation_history if m["role"] == "assistant"
    )
    if ya_presento:
        ya_pregunto_encargado = any(
            "encargad" in m.get("content", "").lower()
            for m in agente.conversation_history if m["role"] == "assistant"
        )
        if ya_pregunto_encargado:
            respuesta = "Me escucha? Sigue en la linea?"
        else:
            respuesta = "Se encontrara el encargado o encargada de compras?"
    else:
        respuesta = SEGUNDA_PARTE_SALUDO

    # Add to conversation history
    agente.conversation_history.append({"role": "user", "content": texto})
    agente.conversation_history.append({"role": "assistant", "content": respuesta})

    # Advance FSM: SALUDO -> BUSCANDO_ENCARGADO
    if hasattr(agente, "fsm") and agente.fsm:
        from fsm_engine import FSMState
        agente.fsm.state = FSMState.BUSCANDO_ENCARGADO
        agente.fsm.context.pitch_dado = True
        log.info("FSM avanzado SALUDO->BUSCANDO_ENCARGADO (segunda_parte_saludo cache)")

    return respuesta


# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------
app = FastAPI(title="Bruce v2.5 — Realtime API + FSM")


@app.on_event("startup")
async def startup_event():
    """Load caches and initialize on startup."""
    log.info("=" * 60)
    log.info("Bruce v2.5 — Servidor Realtime API + FSM")
    log.info(f"Deploy: {DEPLOY_NAME} ({DEPLOY_ID})")
    log.info("=" * 60)

    # Load audio cache from disk
    cargar_cache_desde_disco()

    # Pre-convert to ulaw in background
    loop = asyncio.get_event_loop()
    loop.run_in_executor(None, precargar_cache_ulaw)


@app.get("/")
async def health():
    return {
        "status": "ok",
        "version": "bruce_v2.5_realtime_fsm",
        "deploy": DEPLOY_NAME,
        "calls_active": len(conversaciones_activas),
        "calls_total": len(historial_llamadas),
        "cache_mp3": len(audio_cache_mp3),
        "cache_ulaw": len(audio_cache_ulaw),
    }


# ---------------------------------------------------------------------------
# Twilio webhook — incoming call
# ---------------------------------------------------------------------------
@app.api_route("/incoming-call", methods=["GET", "POST"])
async def incoming_call(request: Request):
    """Return TwiML that connects a bidirectional Media Stream."""
    host = request.headers.get("host", request.url.hostname)
    protocol = "wss"

    # Extract caller info from Twilio params
    if request.method == "POST":
        form = await request.form()
        call_sid = form.get("CallSid", "")
        caller = form.get("From", "")
        called = form.get("To", "")
    else:
        call_sid = request.query_params.get("CallSid", "")
        caller = request.query_params.get("From", "")
        called = request.query_params.get("To", "")

    log.info(f"Incoming call: {call_sid} from={caller} to={called}")

    # Look up contact info from Google Sheets
    contacto_info = None
    if sheets_manager and caller:
        telefono_limpio = caller.replace("+52", "").replace("+", "")
        try:
            contacto_info = await asyncio.to_thread(
                sheets_manager.buscar_contacto, telefono_limpio
            )
        except Exception as e:
            log.warning(f"Error buscando contacto: {e}")

    # Store for later use
    if contacto_info:
        contactos_llamadas[call_sid] = contacto_info

    response = VoiceResponse()
    connect = Connect()
    connect.stream(url=f"{protocol}://{host}/media-stream")
    response.append(connect)

    return HTMLResponse(content=str(response), media_type="application/xml")


# ---------------------------------------------------------------------------
# Outbound call endpoint
# ---------------------------------------------------------------------------
@app.post("/iniciar-llamada")
async def iniciar_llamada(request: Request):
    """Start an outbound call to a given number."""
    body = await request.json()
    telefono = body.get("telefono", "")
    if not telefono:
        return JSONResponse({"error": "telefono requerido"}, status_code=400)

    if not telefono.startswith("+"):
        telefono = f"+52{telefono}"

    contacto_info = body.get("contacto_info")
    nombre_negocio = body.get("nombre_negocio", "")

    host = request.headers.get("host", request.url.hostname)
    protocol = "https"
    webhook_url = f"{protocol}://{host}/incoming-call"
    status_url = f"{protocol}://{host}/status-callback"

    try:
        call = twilio_client.calls.create(
            to=telefono,
            from_=TWILIO_PHONE_NUMBER,
            url=webhook_url,
            record=True,
            recording_status_callback=f"{protocol}://{host}/recording-status",
            status_callback=status_url,
            status_callback_event=["completed"],
        )

        # Store contacto_info for this call
        if contacto_info:
            contactos_llamadas[call.sid] = contacto_info
        elif nombre_negocio:
            contactos_llamadas[call.sid] = {"nombre_negocio": nombre_negocio, "telefono": telefono}

        log.info(f"Llamada iniciada: {call.sid} -> {telefono}")
        return JSONResponse({"call_sid": call.sid, "status": "initiated", "telefono": telefono})
    except Exception as e:
        log.error(f"Error al iniciar llamada: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


# ---------------------------------------------------------------------------
# Status callback (call completed/failed)
# ---------------------------------------------------------------------------
@app.api_route("/status-callback", methods=["GET", "POST"])
async def status_callback(request: Request):
    """Handle call status changes from Twilio."""
    if request.method == "POST":
        form = await request.form()
        call_sid = form.get("CallSid")
        call_status = form.get("CallStatus")
        call_duration = form.get("CallDuration")
        answered_by = form.get("AnsweredBy", "")
    else:
        call_sid = request.query_params.get("CallSid")
        call_status = request.query_params.get("CallStatus")
        call_duration = request.query_params.get("CallDuration")
        answered_by = request.query_params.get("AnsweredBy", "")

    log.info(f"STATUS CALLBACK - {call_sid}: {call_status}, duration={call_duration}s")

    # Finalize call if agente exists
    agente = conversaciones_activas.get(call_sid)
    if agente and call_status == "completed":
        try:
            await asyncio.to_thread(_finalizar_llamada_sync, call_sid, agente)
        except Exception as e:
            log.error(f"Error finalizando llamada: {e}")

    # Cleanup
    conversaciones_activas.pop(call_sid, None)
    contactos_llamadas.pop(call_sid, None)

    return HTMLResponse("OK")


def _finalizar_llamada_sync(call_sid: str, agente):
    """Save call results to Google Sheets (sync, runs in thread).

    Note: historial registration is done separately via registrar_llamada()
    in the websocket cleanup — this function only handles Sheets + bug detector.
    """
    try:
        # Build result summary
        resultado = agente.obtener_resultado() if hasattr(agente, "obtener_resultado") else {}

        # Save to Google Sheets
        if resultados_manager and resultado:
            try:
                resultados_manager.guardar_resultado(resultado)
            except Exception as e:
                log.error(f"Error guardando resultado en Sheets: {e}")

        # Bug detector analysis
        if BUG_DETECTOR_AVAILABLE:
            try:
                analyze_and_cleanup(call_sid)
            except Exception:
                pass

    except Exception as e:
        log.error(f"Error en _finalizar_llamada_sync: {e}")


# ---------------------------------------------------------------------------
# Hangup helper
# ---------------------------------------------------------------------------
async def hangup_call(call_sid: str):
    """Hang up the Twilio call."""
    if not call_sid or not twilio_client:
        return
    try:
        await asyncio.to_thread(
            twilio_client.calls(call_sid).update,
            status="completed",
        )
        log.info(f"Llamada {call_sid} colgada")
    except Exception as e:
        log.error(f"Error colgando llamada: {e}")


# ---------------------------------------------------------------------------
# Create AgenteVentas for a call
# ---------------------------------------------------------------------------
def _crear_agente(call_sid: str, contacto_info: dict = None):
    """Create AgenteVentas instance (sync, runs in thread)."""
    from agente_ventas import AgenteVentas

    agente = AgenteVentas(
        contacto_info=contacto_info,
        sheets_manager=sheets_manager,
        resultados_manager=resultados_manager,
        whatsapp_validator=whatsapp_validator,
    )
    agente.call_sid = call_sid
    agente.voice_id = ELEVENLABS_VOICE_ID
    agente.voice_cache_dir = CACHE_DIR

    # Generate BRUCE ID
    if logs_manager:
        bruce_id = logs_manager.generar_nuevo_id_bruce()
        agente.bruce_id = bruce_id
        agente.lead_data["bruce_id"] = bruce_id
    else:
        agente.bruce_id = None

    return agente


# ---------------------------------------------------------------------------
# Send ulaw audio chunks to Twilio WS
# ---------------------------------------------------------------------------
async def send_ulaw_to_twilio(websocket: WebSocket, stream_sid: str, chunks: list):
    """Send pre-encoded ulaw chunks directly to Twilio Media Stream."""
    for chunk in chunks:
        try:
            await websocket.send_json({
                "event": "media",
                "streamSid": stream_sid,
                "media": {"payload": chunk},
            })
        except Exception:
            break
    # Small delay to let Twilio buffer
    await asyncio.sleep(0.05)


# ---------------------------------------------------------------------------
# Send text to ElevenLabs WS TTS and stream audio to Twilio
# ---------------------------------------------------------------------------
async def send_tts_to_twilio(
    texto: str,
    elevenlabs_ws,
    twilio_ws: WebSocket,
    stream_sid: str,
    state: dict,
):
    """Stream text through ElevenLabs TTS and forward ulaw audio to Twilio.

    Returns True if audio was sent successfully.
    """
    if not texto or not texto.strip():
        return False

    try:
        # Send text to ElevenLabs
        await elevenlabs_ws.send(json.dumps({
            "text": texto + " ",
            "try_trigger_generation": True,
        }))

        # Flush to trigger generation
        await elevenlabs_ws.send(json.dumps({
            "text": "",
            "flush": True,
        }))

        return True
    except Exception as e:
        log.error(f"Error sending TTS: {e}")
        return False


# ---------------------------------------------------------------------------
# Main WebSocket handler — Twilio <-> OpenAI Realtime <-> FSM <-> ElevenLabs
# ---------------------------------------------------------------------------
@app.websocket("/media-stream")
async def media_stream(websocket: WebSocket):
    await websocket.accept()
    log.info("Twilio WebSocket conectado")

    # Per-call state
    state = {
        "stream_sid": None,
        "call_sid": None,
        "should_hangup": False,
        "agente": None,
        "saludo_enviado": False,
        "transcripcion": [],
        "turnos_bruce": 0,
        "turnos_cliente": 0,
        "ultimo_texto_cliente": "",
        "tts_playing": False,
        "call_start_time": None,
        "silence_timeouts": 0,
        "last_activity": None,
    }

    openai_ws = None
    elevenlabs_ws = None

    try:
        # Connect to OpenAI Realtime API (STT only)
        openai_ws = await websockets.connect(
            OPENAI_REALTIME_URL,
            additional_headers={
                "Authorization": f"Bearer {OPENAI_API_KEY_STT or OPENAI_API_KEY}",
                "OpenAI-Beta": "realtime=v1",
            },
        )
        log.info("OpenAI Realtime conectado (STT-only mode)")

        # Send session config (no LLM, STT only)
        await openai_ws.send(json.dumps(SESSION_CONFIG))

        # Connect to ElevenLabs TTS WebSocket
        elevenlabs_ws = await websockets.connect(
            ELEVENLABS_WS_URL,
            additional_headers={"xi-api-key": ELEVENLABS_API_KEY},
        )
        log.info("ElevenLabs TTS conectado")

        # Send BOS
        await elevenlabs_ws.send(json.dumps(ELEVENLABS_BOS))

        # ---------------------------------------------------------------
        # Task 1: Twilio -> OpenAI (forward caller audio)
        # ---------------------------------------------------------------
        async def twilio_to_openai():
            try:
                while True:
                    message = await websocket.receive_text()
                    data = json.loads(message)

                    if data["event"] == "start":
                        state["stream_sid"] = data["start"]["streamSid"]
                        state["call_sid"] = data["start"].get("callSid")
                        log.info(f"Stream started: {state['stream_sid']} call={state['call_sid']}")

                        state["call_start_time"] = time.time()
                        state["last_activity"] = time.time()

                        # Create AgenteVentas instance
                        contacto_info = contactos_llamadas.get(state["call_sid"])
                        agente = await asyncio.to_thread(
                            _crear_agente, state["call_sid"], contacto_info
                        )
                        state["agente"] = agente
                        conversaciones_activas[state["call_sid"]] = agente

                        # Map call_sid -> bruce_id for recording association
                        if agente.bruce_id:
                            callsid_to_bruceid[state["call_sid"]] = agente.bruce_id

                        # Register in bug detector
                        if BUG_DETECTOR_AVAILABLE and agente.bruce_id:
                            try:
                                telefono_bd = (contacto_info or {}).get("telefono", "")
                                get_or_create_tracker(
                                    state["call_sid"], agente.bruce_id, telefono_bd
                                )
                            except Exception:
                                pass

                        # Send initial greeting
                        saludo = await asyncio.to_thread(agente.iniciar_conversacion)
                        log.info(f"Bruce (saludo): {saludo}")
                        state["transcripcion"].append({"rol": "Bruce", "texto": saludo})

                        # Log saludo
                        if logs_manager and agente.bruce_id:
                            nombre_tienda = (contacto_info or {}).get("nombre_negocio", "")
                            try:
                                await asyncio.to_thread(
                                    logs_manager.registrar_mensaje_bruce,
                                    agente.bruce_id, saludo, True, "saludo_inicial", nombre_tienda,
                                )
                            except Exception:
                                pass

                        # Send saludo audio
                        cached_saludo = buscar_audio_cache(saludo)
                        if cached_saludo:
                            await send_ulaw_to_twilio(websocket, state["stream_sid"], cached_saludo)
                            log.info(f"Saludo enviado desde cache ({len(cached_saludo)} chunks)")
                        else:
                            await send_tts_to_twilio(
                                saludo, elevenlabs_ws, websocket, state["stream_sid"], state
                            )
                            log.info("Saludo enviado via ElevenLabs TTS")

                        state["saludo_enviado"] = True

                    elif data["event"] == "media":
                        # Forward mulaw audio to OpenAI for transcription
                        if openai_ws and openai_ws.open:
                            await openai_ws.send(json.dumps({
                                "type": "input_audio_buffer.append",
                                "audio": data["media"]["payload"],
                            }))

                    elif data["event"] == "stop":
                        log.info("Twilio stream stopped")
                        break

            except WebSocketDisconnect:
                log.info("Twilio WebSocket desconectado")

        # ---------------------------------------------------------------
        # Task 2: OpenAI events -> FSM -> TTS
        # ---------------------------------------------------------------
        async def openai_events_handler():
            nonlocal elevenlabs_ws

            try:
                async for message in openai_ws:
                    event = json.loads(message)
                    event_type = event.get("type", "")

                    # === SUPPRESS auto-response from OpenAI LLM ===
                    if event_type == "response.created":
                        # Cancel any LLM response — we only want STT
                        try:
                            await openai_ws.send(json.dumps({"type": "response.cancel"}))
                        except Exception:
                            pass
                        continue

                    # === User speech transcription completed ===
                    elif event_type == "conversation.item.input_audio_transcription.completed":
                        transcript = event.get("transcript", "").strip()
                        if not transcript:
                            continue

                        state["last_activity"] = time.time()
                        state["silence_timeouts"] = 0
                        state["turnos_cliente"] += 1
                        log.info(f"Cliente: {transcript}")
                        state["transcripcion"].append({"rol": "Cliente", "texto": transcript})
                        state["ultimo_texto_cliente"] = transcript

                        agente = state["agente"]
                        if not agente:
                            continue

                        # Log client message
                        if logs_manager and agente.bruce_id:
                            nombre_tienda = ""
                            if agente.contacto_info:
                                nombre_tienda = agente.contacto_info.get("nombre_negocio", "")
                            try:
                                await asyncio.to_thread(
                                    logs_manager.registrar_mensaje_cliente,
                                    agente.bruce_id, transcript, nombre_tienda,
                                )
                            except Exception:
                                pass

                        # Bug detector event
                        if BUG_DETECTOR_AVAILABLE:
                            try:
                                emit_event(state["call_sid"], "cliente", transcript)
                            except Exception:
                                pass

                        # === IVR/Voicemail detection ===
                        transcript_lower = transcript.lower()
                        _ivr_patterns = [
                            "deje su mensaje", "despues del tono", "después del tono",
                            "marque la extension", "el numero que usted marco",
                            "el número que usted marcó", "no esta disponible",
                            "no está disponible", "fuera de servicio",
                            "leave a message", "after the tone", "press",
                            "para espanol oprima", "para español oprima",
                        ]
                        if any(p in transcript_lower for p in _ivr_patterns):
                            log.info(f"IVR/Buzon detectado: '{transcript[:60]}'")
                            state["should_hangup"] = True
                            # Register as IVR result
                            if agente.bruce_id:
                                registrar_llamada(
                                    agente.bruce_id,
                                    (agente.contacto_info or {}).get("telefono", ""),
                                    (agente.contacto_info or {}).get("nombre_negocio", ""),
                                    "IVR/Buzon detectado",
                                    call_sid=state["call_sid"],
                                )
                            await hangup_call(state["call_sid"])
                            continue

                        # === Segunda parte del saludo (cache, no GPT) ===
                        segunda_parte = detectar_segunda_parte_saludo(agente, transcript)
                        if segunda_parte:
                            respuesta = segunda_parte
                            log.info(f"Bruce (segunda_parte_saludo cache): {respuesta}")
                        else:
                            # === CORE: Route through FSM ===
                            try:
                                respuesta = await asyncio.to_thread(
                                    agente.procesar_respuesta, transcript
                                )
                            except Exception as e:
                                log.error(f"Error en procesar_respuesta: {e}")
                                respuesta = None

                        if not respuesta or respuesta.strip() == "":
                            continue

                        log.info(f"Bruce: {respuesta}")
                        state["transcripcion"].append({"rol": "Bruce", "texto": respuesta})
                        state["turnos_bruce"] += 1
                        state["last_activity"] = time.time()

                        # Log Bruce response
                        desde_cache = segunda_parte is not None
                        if logs_manager and agente.bruce_id:
                            nombre_tienda = ""
                            if agente.contacto_info:
                                nombre_tienda = agente.contacto_info.get("nombre_negocio", "")
                            try:
                                await asyncio.to_thread(
                                    logs_manager.registrar_mensaje_bruce,
                                    agente.bruce_id, respuesta, desde_cache,
                                    "segunda_parte_cache" if desde_cache else "fsm",
                                    nombre_tienda,
                                )
                            except Exception:
                                pass

                        # Bug detector event
                        if BUG_DETECTOR_AVAILABLE:
                            try:
                                emit_event(state["call_sid"], "bruce", respuesta)
                            except Exception:
                                pass

                        # === Send audio response ===
                        cached = buscar_audio_cache(respuesta)
                        if cached:
                            await send_ulaw_to_twilio(
                                websocket, state["stream_sid"], cached
                            )
                            log.info(f"Audio cache hit ({len(cached)} chunks)")
                        else:
                            await send_tts_to_twilio(
                                respuesta, elevenlabs_ws, websocket,
                                state["stream_sid"], state,
                            )
                            log.info("Audio via ElevenLabs TTS")

                        # Check if FSM says to hang up (DESPEDIDA state)
                        fsm = getattr(agente, "fsm", None)
                        if fsm and hasattr(fsm, "state"):
                            from fsm_engine import FSMState
                            if fsm.state == FSMState.DESPEDIDA:
                                state["should_hangup"] = True
                                log.info("FSM en DESPEDIDA — programando hangup")

                    # === User started speaking (interruption) ===
                    elif event_type == "input_audio_buffer.speech_started":
                        log.info("Interrupcion detectada — limpiando audio")
                        # Clear Twilio playback
                        if state["stream_sid"]:
                            try:
                                await websocket.send_json({
                                    "event": "clear",
                                    "streamSid": state["stream_sid"],
                                })
                            except Exception:
                                pass

                        # Reset ElevenLabs connection for next utterance
                        try:
                            await elevenlabs_ws.close()
                        except Exception:
                            pass
                        try:
                            elevenlabs_ws = await websockets.connect(
                                ELEVENLABS_WS_URL,
                                additional_headers={"xi-api-key": ELEVENLABS_API_KEY},
                            )
                            await elevenlabs_ws.send(json.dumps(ELEVENLABS_BOS))
                        except Exception as e:
                            log.error(f"Error reconnecting ElevenLabs: {e}")

                    # === Session events ===
                    elif event_type == "session.created":
                        log.info("OpenAI session created")

                    elif event_type == "session.updated":
                        log.info("OpenAI session updated (STT-only mode)")

                    elif event_type == "error":
                        log.error(f"OpenAI error: {event}")

            except websockets.exceptions.ConnectionClosed:
                log.info("OpenAI WebSocket cerrado")

        # ---------------------------------------------------------------
        # Task 3: ElevenLabs -> Twilio (TTS audio -> caller)
        # ---------------------------------------------------------------
        async def elevenlabs_to_twilio():
            nonlocal elevenlabs_ws

            while True:
                try:
                    async for message in elevenlabs_ws:
                        data = json.loads(message)

                        if data.get("audio"):
                            # Send ulaw audio to Twilio
                            if state["stream_sid"]:
                                await websocket.send_json({
                                    "event": "media",
                                    "streamSid": state["stream_sid"],
                                    "media": {"payload": data["audio"]},
                                })

                        elif data.get("isFinal"):
                            # TTS segment complete
                            if state["should_hangup"]:
                                log.info("Colgando llamada despues de despedida...")
                                await asyncio.sleep(0.8)
                                await hangup_call(state["call_sid"])
                                return

                except websockets.exceptions.ConnectionClosed:
                    # ElevenLabs reconnected after interruption
                    await asyncio.sleep(0.1)
                    continue

        # ---------------------------------------------------------------
        # ElevenLabs keepalive (prevent 20s timeout)
        # ---------------------------------------------------------------
        async def elevenlabs_keepalive():
            while True:
                await asyncio.sleep(15)
                try:
                    if elevenlabs_ws and elevenlabs_ws.open:
                        await elevenlabs_ws.send(json.dumps({
                            "text": " ",
                            "try_trigger_generation": False,
                        }))
                except Exception:
                    pass

        # ---------------------------------------------------------------
        # Silence timeout monitor
        # ---------------------------------------------------------------
        async def silence_monitor():
            """Detect prolonged silence and send prompts or hang up."""
            while True:
                await asyncio.sleep(5)
                if state["should_hangup"]:
                    break

                agente = state["agente"]
                if not agente or not state["saludo_enviado"]:
                    continue

                last = state.get("last_activity") or state.get("call_start_time")
                if not last:
                    continue

                elapsed = time.time() - last

                # After 15s of silence, send a prompt
                if elapsed > 15 and state["silence_timeouts"] == 0:
                    state["silence_timeouts"] = 1
                    prompt = "Me escucha? Sigue en la linea?"
                    log.info(f"Silence timeout 1 ({elapsed:.0f}s) — sending prompt")
                    state["transcripcion"].append({"rol": "Bruce", "texto": prompt})

                    cached = buscar_audio_cache(prompt)
                    if cached:
                        await send_ulaw_to_twilio(websocket, state["stream_sid"], cached)
                    else:
                        await send_tts_to_twilio(
                            prompt, elevenlabs_ws, websocket, state["stream_sid"], state
                        )

                # After 30s total silence, hang up
                elif elapsed > 30 and state["silence_timeouts"] >= 1:
                    log.info(f"Silence timeout final ({elapsed:.0f}s) — hanging up")
                    state["should_hangup"] = True
                    await hangup_call(state["call_sid"])
                    break

        # Run all tasks concurrently
        await asyncio.gather(
            twilio_to_openai(),
            openai_events_handler(),
            elevenlabs_to_twilio(),
            elevenlabs_keepalive(),
            silence_monitor(),
        )

    except Exception as e:
        log.error(f"Error en media_stream: {e}", exc_info=True)

    finally:
        # Cleanup WebSocket connections
        for ws in [openai_ws, elevenlabs_ws]:
            if ws:
                try:
                    await ws.close()
                except Exception:
                    pass

        turnos = len(state.get("transcripcion", []))
        duracion = int(time.time() - state["call_start_time"]) if state.get("call_start_time") else 0
        log.info(f"Llamada finalizada. {turnos} turnos, {duracion}s")

        # Final save
        agente = state.get("agente")
        call_sid = state.get("call_sid")
        if call_sid and agente:
            try:
                # Register in historial
                resultado_texto = "Nulo"
                if hasattr(agente, "fsm") and agente.fsm:
                    from fsm_engine import FSMState
                    st = agente.fsm.state
                    if st == FSMState.DESPEDIDA:
                        resultado_texto = "Despedida"
                    elif st == FSMState.CONTACTO_CAPTURADO:
                        resultado_texto = "Catalogo prometido - Exito"
                    elif st == FSMState.CAPTURANDO_CONTACTO:
                        resultado_texto = "Capturando contacto (colgo)"
                    else:
                        resultado_texto = f"Estado: {st.name}" if hasattr(st, "name") else str(st)

                contacto_info = agente.contacto_info or {}
                registrar_llamada(
                    bruce_id=getattr(agente, "bruce_id", None),
                    telefono=contacto_info.get("telefono", ""),
                    negocio=contacto_info.get("nombre_negocio", ""),
                    resultado=resultado_texto,
                    duracion=duracion,
                    detalles={"turnos": turnos, "transcripcion": state.get("transcripcion", [])},
                    call_sid=call_sid,
                )

                await asyncio.to_thread(
                    _finalizar_llamada_sync, call_sid, agente
                )
            except Exception as e:
                log.error(f"Error en finalizacion: {e}")

            conversaciones_activas.pop(call_sid, None)
            contactos_llamadas.pop(call_sid, None)


# ---------------------------------------------------------------------------
# Dashboard: Historial de Llamadas (full port from servidor_llamadas.py)
# ---------------------------------------------------------------------------
@app.get("/historial-llamadas")
async def historial_llamadas_page():
    """Full dashboard with semaforos, notes, recordings, filters."""
    global calificaciones_llamadas
    calificaciones_llamadas = cargar_calificaciones()

    historial = list(reversed(list(historial_llamadas)))

    # Stats
    total = len(calificaciones_llamadas)
    verdes = sum(1 for c in calificaciones_llamadas.values() if c.get("semaforo") == "verde")
    amarillos = sum(1 for c in calificaciones_llamadas.values() if c.get("semaforo") == "amarillo")
    rojos = sum(1 for c in calificaciones_llamadas.values() if c.get("semaforo") == "rojo")
    naranjas = sum(1 for c in calificaciones_llamadas.values() if c.get("semaforo") == "naranja")
    azules = sum(1 for c in calificaciones_llamadas.values() if c.get("semaforo") == "azul")
    sin_calificar = max(0, len(historial) - total)

    rows_html = ""
    for llamada in historial[:100]:
        bruce_id = llamada.get("bruce_id", "N/A")
        call_id = bruce_id
        calif = calificaciones_llamadas.get(call_id, {})
        semaforo_actual = calif.get("semaforo", "")
        notas_actual = calif.get("notas", "").replace('"', "&quot;")
        solucionado = calif.get("solucionado", False)
        resultado = llamada.get("resultado", "N/A")
        resultado_lower = resultado.lower()

        if "catalogo" in resultado_lower or "exito" in resultado_lower:
            badge_class = "badge-exito"
        elif "ivr" in resultado_lower:
            badge_class = "badge-ivr"
        elif "colgo" in resultado_lower or "colgó" in resultado_lower:
            badge_class = "badge-nocontesto"
        elif "negado" in resultado_lower or "rechaz" in resultado_lower:
            badge_class = "badge-negado"
        else:
            badge_class = ""

        recording_url = grabaciones_por_bruce.get(bruce_id, "")
        recording_sid = ""
        if recording_url and "/Recordings/" in recording_url:
            recording_sid = recording_url.split("/Recordings/")[-1].split(".")[0]
        link_grabacion = f"/escuchar-grabacion/{recording_sid}" if recording_sid else ""

        estado_filtro = semaforo_actual if semaforo_actual else "sin_calificar"
        deploy_display = llamada.get("deploy_name", llamada.get("deploy_id", "?"))[:12]

        quien_colgo = "-"
        if "colgo" in resultado_lower or "colgó" in resultado_lower:
            quien_colgo = "C"
        elif "catalogo" in resultado_lower or "exito" in resultado_lower or "despedida" in resultado_lower:
            quien_colgo = "B"

        audio_html = (
            f'<audio controls preload="none" style="width:150px;height:32px;">'
            f'<source src="{link_grabacion}" type="audio/mpeg"></audio>'
            if link_grabacion else '<span style="color:#666">-</span>'
        )

        def _btn(color, label):
            activo = "activo" if semaforo_actual == color else ""
            return (
                f'<button class="semaforo-btn btn-{color} {activo}" '
                f'onclick="setSemaforo(\'{call_id}\',\'{color}\',this)" title="{label}"></button>'
            )

        semaforo_emojis = {"verde": "&#x1F7E2;", "amarillo": "&#x1F7E1;", "rojo": "&#x1F534;", "naranja": "&#x1F7E0;", "azul": "&#x1F535;"}
        estado_emoji = semaforo_emojis.get(semaforo_actual, "")

        fila_class = "fila-solucionada" if solucionado else ""
        checked = "checked" if solucionado else ""

        rows_html += f'''<tr data-call-id="{call_id}" data-estado="{estado_filtro}" class="{fila_class}">
<td style="font-size:11px;white-space:nowrap">{llamada.get("timestamp","N/A")}</td>
<td><strong>{bruce_id}</strong></td>
<td title="{llamada.get("negocio","N/A")}">{str(llamada.get("negocio","N/A"))[:25]}</td>
<td style="font-size:12px">{llamada.get("telefono","N/A")}</td>
<td><span class="badge {badge_class}">{resultado[:20]}</span></td>
<td>{llamada.get("duracion",0)}s</td>
<td style="text-align:center;font-weight:bold">{quien_colgo}</td>
<td>{audio_html}</td>
<td><div class="semaforo">{_btn("verde","Bueno")}{_btn("amarillo","Medio")}{_btn("rojo","Malo")}{_btn("naranja","Buzon")}{_btn("azul","Contestadora")}</div></td>
<td><textarea class="notas-input" placeholder="Anotar error..." onchange="setNotas(\'{call_id}\',this.value)" rows="2">{notas_actual}</textarea></td>
<td style="text-align:center"><label class="checkbox-solucionado"><input type="checkbox" {checked} onchange="setSolucionado(\'{call_id}\',this.checked)"></label></td>
<td><span class="semaforo-guardado">{estado_emoji}</span></td>
<td style="font-size:10px;color:#888">{deploy_display}</td>
</tr>'''

    html = f"""<!DOCTYPE html><html><head><title>Bruce v2.5 Historial</title><meta charset="UTF-8">
<style>
*{{box-sizing:border-box}}
body{{font-family:'Segoe UI',Arial,sans-serif;background:linear-gradient(135deg,#1a1a2e 0%,#16213e 100%);color:#eee;margin:0;padding:20px;min-height:100vh}}
h1{{color:#4CAF50;text-align:center;margin-bottom:10px}}
.subtitle{{text-align:center;color:#888;margin-bottom:30px}}
.stats-semaforos{{display:flex;justify-content:center;gap:20px;margin-bottom:30px;flex-wrap:wrap}}
.stat-item{{padding:15px 30px;border-radius:10px;text-align:center;min-width:100px}}
.stat-verde{{background:rgba(76,175,80,.3);border:2px solid #4CAF50}}
.stat-amarillo{{background:rgba(255,193,7,.3);border:2px solid #FFC107}}
.stat-rojo{{background:rgba(244,67,54,.3);border:2px solid #f44336}}
.stat-naranja{{background:rgba(255,152,0,.3);border:2px solid #FF9800}}
.stat-azul{{background:rgba(33,150,243,.3);border:2px solid #2196F3}}
.stat-gris{{background:rgba(158,158,158,.3);border:2px solid #9e9e9e}}
.stat-item .numero{{font-size:2em;font-weight:bold;display:block}}
.stat-item .label{{font-size:.85em;opacity:.8}}
.tabla-container{{overflow-x:auto;background:#16213e;border-radius:15px;padding:20px;box-shadow:0 4px 20px rgba(0,0,0,.3)}}
table{{width:100%;border-collapse:collapse}}
th{{background:#0f3460;padding:15px 10px;text-align:left;font-weight:600;position:sticky;top:0}}
td{{padding:12px 10px;border-bottom:1px solid #1a1a2e;vertical-align:middle}}
tr:hover{{background:rgba(33,150,243,.1)}}
.semaforo{{display:flex;gap:8px;align-items:center}}
.semaforo-btn{{width:28px;height:28px;border-radius:50%;border:2px solid transparent;cursor:pointer;transition:all .2s;opacity:.4}}
.semaforo-btn:hover{{opacity:.8;transform:scale(1.1)}}
.semaforo-btn.activo{{opacity:1;border-color:white;box-shadow:0 0 10px currentColor}}
.btn-verde{{background:#4CAF50}}.btn-amarillo{{background:#FFC107}}.btn-rojo{{background:#f44336}}.btn-naranja{{background:#FF9800}}.btn-azul{{background:#2196F3}}
.notas-input{{width:100%;min-width:150px;padding:8px;border:1px solid #333;border-radius:5px;background:#1a1a2e;color:#eee;font-size:12px;resize:vertical}}
.notas-input:focus{{outline:none;border-color:#4CAF50}}
.badge{{padding:4px 10px;border-radius:12px;font-size:11px;font-weight:600}}
.badge-exito{{background:#4CAF50;color:white}}.badge-ivr{{background:#ff9800;color:white}}.badge-nocontesto{{background:#9e9e9e;color:white}}.badge-negado{{background:#f44336;color:white}}
.btn-guardar{{position:fixed;bottom:30px;right:30px;padding:15px 30px;background:#4CAF50;color:white;border:none;border-radius:30px;cursor:pointer;font-size:16px;box-shadow:0 4px 15px rgba(76,175,80,.4);z-index:1000}}
.btn-guardar:hover{{transform:scale(1.05);background:#45a049}}
.mensaje-guardado{{position:fixed;top:20px;right:20px;padding:15px 25px;background:#4CAF50;color:white;border-radius:10px;display:none;z-index:1001}}
.nav-links{{text-align:center;margin-bottom:20px}}
.nav-links a{{color:#4CAF50;margin:0 15px;text-decoration:none}}
.fila-solucionada{{background:rgba(76,175,80,.15)!important;opacity:.7}}
.fila-solucionada td{{text-decoration:line-through;color:#888}}
.fila-solucionada .badge,.fila-solucionada .semaforo-btn,.fila-solucionada .notas-input{{text-decoration:none}}
.checkbox-solucionado{{cursor:pointer}}.checkbox-solucionado input{{width:20px;height:20px;cursor:pointer;accent-color:#4CAF50}}
</style></head><body>
<h1>Historial de Llamadas - Bruce v2.5</h1>
<p class="subtitle">Deploy: {DEPLOY_NAME} ({DEPLOY_ID}) | Activas: {len(conversaciones_activas)}</p>
<div class="nav-links"><a href="/">Health</a><a href="/bugs">Bugs</a><a href="/historial-llamadas">Refrescar</a></div>
<div class="stats-semaforos">
<div class="stat-item stat-verde"><span class="numero">{verdes}</span><span class="label">Bueno</span></div>
<div class="stat-item stat-amarillo"><span class="numero">{amarillos}</span><span class="label">Medio</span></div>
<div class="stat-item stat-rojo"><span class="numero">{rojos}</span><span class="label">Malo</span></div>
<div class="stat-item stat-naranja"><span class="numero">{naranjas}</span><span class="label">Buzon</span></div>
<div class="stat-item stat-azul"><span class="numero">{azules}</span><span class="label">Contestadora</span></div>
<div class="stat-item stat-gris"><span class="numero">{sin_calificar}</span><span class="label">Sin calificar</span></div>
</div>
<div class="mensaje-guardado" id="mensajeGuardado">Calificaciones guardadas</div>
<div class="tabla-container">
<div style="margin-bottom:15px;padding:10px;background:#2a2a2a;border-radius:8px">
<label style="color:#fff;margin-right:10px">Filtrar:</label>
<select id="filtroEstado" onchange="filtrarPorEstado()" style="padding:8px;border-radius:5px;background:#333;color:#fff;border:1px solid #555">
<option value="todos">Todos</option><option value="verde">Bueno</option><option value="amarillo">Medio</option>
<option value="rojo">Malo</option><option value="naranja">Buzon</option><option value="azul">Contestadora</option>
<option value="sin_calificar">Sin calificar</option></select></div>
<table><tr><th>Fecha/Hora</th><th>BRUCE ID</th><th>Negocio</th><th>Telefono</th><th>Resultado</th><th>Duracion</th><th>Colgo</th><th>Grabacion</th><th>Semaforo</th><th>Notas</th><th>OK</th><th>Estado</th><th>Deploy</th></tr>
{rows_html}
</table></div>
<button class="btn-guardar" onclick="guardarTodo()">Guardar Calificaciones</button>
<script>
let cambiosPendientes={{}};
function filtrarPorEstado(){{const f=document.getElementById('filtroEstado').value;document.querySelectorAll('table tr[data-call-id]').forEach(r=>{{r.style.display=(f==='todos'||r.dataset.estado===f)?'':'none'}})}}
function setSemaforo(id,color,btn){{const fila=btn.closest('tr');fila.querySelectorAll('.semaforo-btn').forEach(b=>b.classList.remove('activo'));btn.classList.add('activo');if(!cambiosPendientes[id])cambiosPendientes[id]={{}};cambiosPendientes[id].semaforo=color;fila.dataset.estado=color}}
function setNotas(id,n){{if(!cambiosPendientes[id])cambiosPendientes[id]={{}};cambiosPendientes[id].notas=n}}
function setSolucionado(id,c){{if(!cambiosPendientes[id])cambiosPendientes[id]={{}};cambiosPendientes[id].solucionado=c;const f=document.querySelector(`tr[data-call-id="${{id}}"]`);if(f)f.classList.toggle('fila-solucionada',c)}}
async function guardarTodo(){{const btn=document.querySelector('.btn-guardar');btn.disabled=true;btn.textContent='Guardando...';try{{const r=await fetch('/historial-llamadas/guardar',{{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify(cambiosPendientes)}});const d=await r.json();if(d.success){{document.getElementById('mensajeGuardado').style.display='block';setTimeout(()=>location.reload(),1000);cambiosPendientes={{}}}}else alert('Error: '+d.error)}}catch(e){{alert('Error: '+e.message)}}btn.disabled=false;btn.textContent='Guardar Calificaciones'}}
</script></body></html>"""
    return HTMLResponse(html)


@app.post("/historial-llamadas/guardar")
async def guardar_calificaciones_endpoint(request: Request):
    """Save semaforo ratings to persistent JSON."""
    global calificaciones_llamadas
    try:
        datos = await request.json()
        if not datos:
            return JSONResponse({"success": False, "error": "No hay datos"}, status_code=400)

        calificaciones_llamadas = cargar_calificaciones()
        for call_id, calif in datos.items():
            if call_id not in calificaciones_llamadas:
                calificaciones_llamadas[call_id] = {}
            if "semaforo" in calif:
                calificaciones_llamadas[call_id]["semaforo"] = calif["semaforo"]
            if "notas" in calif:
                calificaciones_llamadas[call_id]["notas"] = calif["notas"]
            if "solucionado" in calif:
                calificaciones_llamadas[call_id]["solucionado"] = calif["solucionado"]
            calificaciones_llamadas[call_id]["fecha_actualizacion"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        if guardar_calificaciones(calificaciones_llamadas):
            return JSONResponse({"success": True, "guardados": len(datos)})
        return JSONResponse({"success": False, "error": "Error escribiendo archivo"}, status_code=500)
    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)


# ---------------------------------------------------------------------------
# Recording proxy (serve Twilio recordings with auth)
# ---------------------------------------------------------------------------
@app.get("/escuchar-grabacion/{recording_sid}")
async def escuchar_grabacion(recording_sid: str):
    """Proxy to serve Twilio recordings with authentication."""
    import httpx
    if not recording_sid or recording_sid == "undefined":
        return HTMLResponse("Recording SID no valido", status_code=400)

    twilio_url = f"https://api.twilio.com/2010-04-01/Accounts/{TWILIO_ACCOUNT_SID}/Recordings/{recording_sid}.mp3"
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                twilio_url,
                auth=(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN),
                timeout=30,
            )
        if resp.status_code == 200:
            return Response(
                content=resp.content,
                media_type="audio/mpeg",
                headers={"Content-Disposition": f'inline; filename="{recording_sid}.mp3"'},
            )
        return HTMLResponse(f"Error: {resp.status_code}", status_code=resp.status_code)
    except Exception as e:
        return HTMLResponse(f"Error: {e}", status_code=500)


# ---------------------------------------------------------------------------
# Dashboard: Bugs
# ---------------------------------------------------------------------------
@app.get("/bugs")
async def bugs_page():
    """Bug detector dashboard."""
    if BUG_DETECTOR_AVAILABLE:
        try:
            html = await asyncio.to_thread(generar_bugs_html)
            return HTMLResponse(html)
        except Exception as e:
            return HTMLResponse(f"<p>Error generando bugs: {e}</p>")
    return HTMLResponse("<p>Bug detector no disponible</p>")


# ---------------------------------------------------------------------------
# Recording callback — associate recording URL with bruce_id
# ---------------------------------------------------------------------------
@app.post("/recording-status")
async def recording_status(request: Request):
    form = await request.form()
    call_sid = form.get("CallSid", "")
    recording_url = form.get("RecordingUrl", "")
    recording_sid = form.get("RecordingSid", "")

    log.info(f"Recording: {recording_sid} status={form.get('RecordingStatus')} call={call_sid}")

    # Associate recording with bruce_id
    bruce_id = callsid_to_bruceid.get(call_sid)
    if bruce_id and recording_url:
        grabaciones_por_bruce[bruce_id] = recording_url
        # Update historial
        for llamada in historial_llamadas:
            if llamada.get("bruce_id") == bruce_id:
                if "detalles" not in llamada:
                    llamada["detalles"] = {}
                llamada["detalles"]["recording_url"] = recording_url
                break
        guardar_historial()

    return HTMLResponse("OK")


# ---------------------------------------------------------------------------
# API endpoints
# ---------------------------------------------------------------------------
@app.get("/api/calls")
async def api_calls():
    """API: list active calls."""
    calls = []
    for sid, agente in conversaciones_activas.items():
        calls.append({
            "call_sid": sid,
            "bruce_id": getattr(agente, "bruce_id", None),
            "turnos": len(getattr(agente, "conversation_history", [])),
        })
    return JSONResponse({"active_calls": calls, "count": len(calls)})


@app.get("/api/historial")
async def api_historial():
    """API: call history."""
    return JSONResponse({"historial": list(historial_llamadas)[-50:], "total": len(historial_llamadas)})


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", 8080))
    log.info(f"Starting Bruce v2.5 on port {port}")
    uvicorn.run(app, host="0.0.0.0", port=port)
