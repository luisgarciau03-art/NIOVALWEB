"""
Extract procesar_respuesta() from servidor_llamadas.py
to server/handlers/conversation_handler.py

Strategy:
- Copy the function body (lines 1670-4832) to new module
- Add lazy import of servidor_llamadas + rebind all module-level globals
- Replace original function with a 3-line wrapper
- Remove 'global cache_respuestas_stats' (dict mutation works via local ref)
"""

# Read the source
with open('servidor_llamadas.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

print(f"servidor_llamadas.py: {len(lines)} lines")

# Verify boundaries
assert 'def procesar_respuesta():' in lines[1663], f"Expected def at line 1664, got: {lines[1663]}"
assert '@app.route("/procesar-respuesta"' in lines[1662], f"Expected route at line 1663, got: {lines[1662]}"
assert 'return Response(str(response)' in lines[4831], f"Expected return at line 4832, got: {lines[4831]}"
assert '@app.route("/despedida-final"' in lines[4834], f"Expected next route at line 4835, got: {lines[4834]}"

# Extract function body (lines 1670-4832, 1-indexed -> 0-indexed: 1669-4831)
# These are the lines INSIDE the function (after docstring ends at line 1669)
body_lines = lines[1669:4832]  # 0-indexed slice
print(f"Extracted {len(body_lines)} lines of function body")

# Remove the 'global cache_respuestas_stats' line (line 3822, 0-indexed: 3821)
# Replace with a comment explaining why
cleaned_body = []
globals_removed = 0
for line in body_lines:
    if line.strip() == 'global cache_respuestas_stats':
        cleaned_body.append(line.replace('global cache_respuestas_stats',
                                         '# global cache_respuestas_stats  # Removed: dict mutation works via local ref from srv'))
        globals_removed += 1
    else:
        cleaned_body.append(line)

print(f"Removed {globals_removed} global statement(s)")

# Build the handler module
header = '''"""
Server handler: Main conversation processing logic
Extracted from servidor_llamadas.procesar_respuesta()
This is the core call flow handler (~3,160 lines)

All module-level globals are accessed via lazy import of servidor_llamadas.
Dict mutations work through local references (same underlying objects).
"""
from flask import request, Response
from twilio.twiml.voice_response import VoiceResponse, Gather, Play


def handle_procesar_respuesta():
    """
    FIX 60/214: Procesa la respuesta del cliente y continua la conversacion.
    Delegated from servidor_llamadas.procesar_respuesta()
    Returns: Flask Response (TwiML XML)
    """
    # Lazy import to avoid circular imports at module load time
    import servidor_llamadas as srv

    # Rebind module-level state (dicts/locks - local refs to same objects)
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

    # Rebind module-level utility functions
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

    # Rebind config values
    DEEPGRAM_AVAILABLE = srv.DEEPGRAM_AVAILABLE
    USE_DEEPGRAM = srv.USE_DEEPGRAM
    ELEVENLABS_STT_AVAILABLE = srv.ELEVENLABS_STT_AVAILABLE

    # --- Original function body starts below ---
'''

# Write the handler file
with open('server/handlers/conversation_handler.py', 'w', encoding='utf-8') as f:
    f.write(header)
    f.writelines(cleaned_body)

handler_lines = sum(1 for _ in open('server/handlers/conversation_handler.py', 'r', encoding='utf-8'))
print(f"Created server/handlers/conversation_handler.py ({handler_lines} lines)")

# Now replace procesar_respuesta in servidor_llamadas.py with thin wrapper
# Lines to replace: 1663-4833 (route decorator + function + trailing blank)
# 0-indexed: 1662-4832 (inclusive) -> slice [1662:4833]
wrapper = '''@app.route("/procesar-respuesta", methods=["GET", "POST"])
def procesar_respuesta():
    """FIX 60/214: Procesa respuesta del cliente - delegado a server/handlers/conversation_handler.py"""
    from server.handlers.conversation_handler import handle_procesar_respuesta
    return handle_procesar_respuesta()


'''

new_lines = lines[:1662] + [wrapper] + lines[4833:]

with open('servidor_llamadas.py', 'w', encoding='utf-8') as f:
    f.writelines(new_lines)

new_count = sum(1 for _ in open('servidor_llamadas.py', 'r', encoding='utf-8'))
print(f"servidor_llamadas.py: {len(lines)} -> {new_count} lines (removed {len(lines) - new_count})")
print(f"\nDone! Verify with: python -c \"import py_compile; py_compile.compile('servidor_llamadas.py'); py_compile.compile('server/handlers/conversation_handler.py'); print('OK')\"")
