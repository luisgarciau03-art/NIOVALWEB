"""Extract procesar_respuesta body from servidor_llamadas.py to server/handlers/conversation_handler.py"""
import re

with open('servidor_llamadas.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

print(f"Starting with {len(lines)} lines")

# procesar_respuesta: line 1664 (def) to 4832 (last line before blank + next route)
# The route decorator is at 1663, def at 1664, docstring 1665-1669, body 1670-4832

# Extract the function body (lines 1670-4832, 1-indexed)
body_lines = lines[1669:4832]  # 0-indexed: 1669 to 4831

# Dedent from 4 spaces (module-level function body) to 4 spaces (new function body)
# Actually, the body is already at 4-space indent since it's a module-level function
# We keep the same indentation
transformed = []
for line in body_lines:
    transformed.append(line)

print(f"Extracted {len(transformed)} lines for handler body")

# Find all global variables referenced in the function
# Look for lines with 'global' keyword
globals_used = set()
for line in body_lines:
    m = re.match(r'\s+global (.+)', line)
    if m:
        for var in m.group(1).split(','):
            globals_used.add(var.strip())

print(f"Global variables used: {globals_used}")

# Build the handler module
# Instead of passing all globals, we'll import them from servidor_llamadas
# This works because the handler is imported lazily at call time
header = '''"""
Server handler: Main conversation processing logic
Extracted from servidor_llamadas.procesar_respuesta()
This is the core call flow handler (3,170+ lines)
"""
from flask import request, Response


def handle_procesar_respuesta(app_context):
    """
    Core conversation processing logic.
    Receives app_context dict with all necessary globals and utilities.
    Returns: Flask Response (TwiML XML)
    """
    # Unpack context - all module-level globals from servidor_llamadas
    import servidor_llamadas as srv

'''

# The body references many module-level variables directly.
# We need to add a block at the top that imports them from servidor_llamadas.
# Let's scan for all module-level names used.

# Actually, the simplest approach is to keep the function IN servidor_llamadas.py
# but move only the INNER logic to the handler module.
# The outer function (the route) stays and calls the handler.

# NEW APPROACH: Create the handler as a function that takes the parsed request
# params and returns the TwiML response string. The route stays as a thin wrapper.

header = '''"""
Server handler: Main conversation processing logic
Extracted from servidor_llamadas.procesar_respuesta()
This is the core call flow handler (3,170+ lines)
"""
from flask import Response


def handle_procesar_respuesta(call_sid, speech_result, recording_url, call_status, answered_by, request_params, srv):
    """
    Core conversation processing logic.

    Args:
        call_sid: Twilio CallSid
        speech_result: Twilio SpeechResult
        recording_url: Twilio RecordingUrl
        call_status: Twilio CallStatus
        answered_by: Twilio AnsweredBy
        request_params: dict of all request parameters
        srv: servidor_llamadas module (for accessing globals)

    Returns: Flask Response (TwiML XML)
    """
'''

# For the body, we need to:
# 1. Replace references to module-level globals with srv.X
# 2. Replace function calls to module-level functions with srv.X()

# This is too risky for an automated replacement. Let's use a different approach:
# Just move the ENTIRE function (with its imports from the module) as-is.

# SIMPLEST SAFE APPROACH:
# Move the function body to a new file, but have it import from servidor_llamadas
# at the top level. This works because by the time the handler is imported
# (lazily during a request), servidor_llamadas is already fully loaded.

header = '''"""
Server handler: Main conversation processing logic
Extracted from servidor_llamadas.procesar_respuesta()
This is the core call flow handler (3,170+ lines)
"""
from flask import request, Response


def handle_procesar_respuesta():
    """
    Core conversation processing logic for /procesar-respuesta endpoint.

    All globals are accessed via lazy import of servidor_llamadas module.

    Returns: Flask Response (TwiML XML)
    """
    # Lazy import to avoid circular imports at module load time
    import servidor_llamadas as srv

    # Re-bind all module-level names used in this function
    conversaciones_activas = srv.conversaciones_activas
    conversaciones_activas_lock = srv.conversaciones_activas_lock
    audio_files = srv.audio_files
    contactos_llamadas = srv.contactos_llamadas
    cliente_hablando_activo = srv.cliente_hablando_activo
    respuesta_precargada = srv.respuesta_precargada
    audio_cache = srv.audio_cache
    cache_metadata = srv.cache_metadata
    frase_stats = srv.frase_stats
    respuestas_cache = srv.respuestas_cache
    cache_respuestas_stats = srv.cache_respuestas_stats
    preguntas_frecuentes = srv.preguntas_frecuentes
    deepgram_transcripciones = srv.deepgram_transcripciones
    deepgram_transcripciones_lock = srv.deepgram_transcripciones_lock
    deepgram_ultima_final = srv.deepgram_ultima_final
    deepgram_ultima_final_lock = srv.deepgram_ultima_final_lock
    elevenlabs_transcripciones = srv.elevenlabs_transcripciones
    elevenlabs_transcripciones_lock = srv.elevenlabs_transcripciones_lock
    elevenlabs_ultima_final = srv.elevenlabs_ultima_final
    callsid_to_bruceid = srv.callsid_to_bruceid
    bruce_audio_enviado_timestamp = srv.bruce_audio_enviado_timestamp

    # Re-bind utility functions
    generar_audio_elevenlabs = srv.generar_audio_elevenlabs
    transcribir_con_whisper = srv.transcribir_con_whisper
    corregir_pronunciacion = srv.corregir_pronunciacion
    guardar_cache_en_disco = srv.guardar_cache_en_disco
    normalizar_frase_con_nombres = srv.normalizar_frase_con_nombres
    registrar_frase_usada = srv.registrar_frase_usada
    registrar_pregunta_respuesta = srv.registrar_pregunta_respuesta
    log_evento = srv.log_evento
    post_procesar_transcripcion_email = srv.post_procesar_transcripcion_email
    es_texto_valido_espanol = srv.es_texto_valido_espanol
    limpiar_recursos_llamada = srv.limpiar_recursos_llamada
    concatenar_audios_mp3 = srv.concatenar_audios_mp3
    generar_audio_con_nombre = srv.generar_audio_con_nombre
    generar_audio_async = srv.generar_audio_async
    registrar_llamada = srv.registrar_llamada

    # Re-bind config values
    ELEVENLABS_API_KEY = srv.ELEVENLABS_API_KEY if hasattr(srv, 'ELEVENLABS_API_KEY') else None
    twilio_client = srv.twilio_client if hasattr(srv, 'twilio_client') else None

'''

# Now add the function body with the original indentation
with open('server/handlers/conversation_handler.py', 'w', encoding='utf-8') as f:
    f.write(header)
    f.writelines(transformed)

line_count = sum(1 for _ in open('server/handlers/conversation_handler.py', 'r', encoding='utf-8'))
print(f"Created server/handlers/conversation_handler.py ({line_count} lines)")

# Now replace the function in servidor_llamadas.py
# Replace lines 1663-4833 (route decorator + function) with a thin wrapper
wrapper = '''@app.route("/procesar-respuesta", methods=["GET", "POST"])
def procesar_respuesta():
    """FIX 60/214: Procesa respuesta del cliente - delegado a server/handlers/conversation_handler.py"""
    from server.handlers.conversation_handler import handle_procesar_respuesta
    return handle_procesar_respuesta()


'''

# Replace lines 1663-4834 (0-indexed: 1662-4833)
new_lines = lines[:1662] + [wrapper] + lines[4834:]

with open('servidor_llamadas.py', 'w', encoding='utf-8') as f:
    f.writelines(new_lines)

new_count = sum(1 for _ in open('servidor_llamadas.py', 'r', encoding='utf-8'))
print(f"servidor_llamadas.py: 9344 -> {new_count} lines")
