"""
Extract large route handlers from servidor_llamadas.py to server/handlers/
Automatically finds route boundaries and extracts functions > MIN_LINES
"""
import re

MIN_LINES = 150  # Only extract handlers larger than this

with open('servidor_llamadas.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

print(f"servidor_llamadas.py: {len(lines)} lines")

# Find all @app.route and their function definitions
routes = []
i = 0
while i < len(lines):
    line = lines[i]
    if line.strip().startswith('@app.route('):
        route_line = i  # 0-indexed
        # Extract route path
        m = re.search(r'"([^"]+)"', line)
        route_path = m.group(1) if m else "unknown"
        # Find the def line (might be right after, or after multiple decorators)
        j = i + 1
        while j < len(lines) and not lines[j].strip().startswith('def '):
            j += 1
        if j < len(lines):
            def_line = j
            # Extract function name
            m2 = re.match(r'def (\w+)\(', lines[j].strip())
            func_name = m2.group(1) if m2 else "unknown"
            routes.append({
                'route_path': route_path,
                'func_name': func_name,
                'decorator_line': route_line,
                'def_line': def_line,
            })
        i = j + 1
    else:
        i += 1

# Find end of each route function (next @app.route, next top-level def, or sock/if __name__)
for idx, route in enumerate(routes):
    start = route['def_line']
    # Find the end: look for next line at indent 0 that's not a blank line
    end = start + 1
    while end < len(lines):
        line = lines[end]
        # End at next route decorator, top-level function, sock, or if __name__
        if (line.strip().startswith('@app.route(') or
            line.strip().startswith('@sock.route(') or
            (re.match(r'^def \w+', line) and not line.startswith(' ')) or
            line.strip().startswith('if __name__') or
            (re.match(r'^# ', line) and end > start + 5)):  # Section comment at column 0
            # Back up past blank lines
            while end > start and lines[end-1].strip() == '':
                end -= 1
            break
        end += 1
    route['end_line'] = end - 1  # last line of function (0-indexed, inclusive)
    route['num_lines'] = route['end_line'] - route['decorator_line'] + 1

# Print all routes
print(f"\nFound {len(routes)} routes:")
for r in routes:
    marker = " *** EXTRACT" if r['num_lines'] >= MIN_LINES else ""
    print(f"  Line {r['decorator_line']+1}: {r['route_path']} -> {r['func_name']}() ({r['num_lines']} lines){marker}")

# Filter large handlers
large_handlers = [r for r in routes if r['num_lines'] >= MIN_LINES]
print(f"\n{len(large_handlers)} handlers >= {MIN_LINES} lines to extract:")
for r in large_handlers:
    print(f"  {r['func_name']}: {r['num_lines']} lines")

# Skip procesar_respuesta (already extracted - it's now a thin wrapper)
large_handlers = [r for r in large_handlers if r['func_name'] != 'procesar_respuesta']

# Map function name to handler filename
name_to_file = {
    'despedida_final': 'despedida_handler',
    'status_callback': 'status_handler',
    'webhook_voz': 'webhook_handler',
    'ver_estadisticas': 'stats_handler',
    'ver_dashboard': 'logs_dashboard_handler',
    'reporte_cache_html': 'cache_report_handler',
    'cache_manager': 'cache_manager_handler',
    'historial_llamadas_dashboard': 'historial_handler',
    'diagnostico_persistencia': 'diagnostics_handler',
    'llamadas_masivas': 'bulk_calls_handler',
}

# For each large handler, determine which module-level names it references
# We'll use a comprehensive rebind set (same as conversation_handler.py)
COMMON_REBINDS_STATE = """    # Lazy import to avoid circular imports
    import servidor_llamadas as srv

    # Rebind module-level state used by this handler
    conversaciones_activas = srv.conversaciones_activas
    conversaciones_activas_lock = srv.conversaciones_activas_lock
    audio_files = srv.audio_files
    contactos_llamadas = srv.contactos_llamadas
    audio_cache = srv.audio_cache
    cache_metadata = srv.cache_metadata
    frase_stats = srv.frase_stats
    respuestas_cache = srv.respuestas_cache
    cache_respuestas_stats = srv.cache_respuestas_stats
    preguntas_frecuentes = srv.preguntas_frecuentes
    callsid_to_bruceid = srv.callsid_to_bruceid
    logs_manager = srv.logs_manager
"""

COMMON_REBINDS_FUNCS = """
    # Rebind utility functions
    generar_audio_elevenlabs = srv.generar_audio_elevenlabs
    log_evento = srv.log_evento
    limpiar_recursos_llamada = srv.limpiar_recursos_llamada
    registrar_llamada = srv.registrar_llamada
    corregir_pronunciacion = srv.corregir_pronunciacion
    guardar_cache_en_disco = srv.guardar_cache_en_disco
"""

# Extract each handler
extracted = []
for handler in large_handlers:
    fname = handler['func_name']
    handler_file = name_to_file.get(fname, fname + '_handler')
    handler_module = f'server/handlers/{handler_file}.py'

    # Get the function body (lines after def + docstring)
    def_idx = handler['def_line']
    end_idx = handler['end_line']

    # Find where docstring ends (look for closing """)
    body_start = def_idx + 1
    # Check if there's a docstring
    if '"""' in lines[body_start].strip() or "'''" in lines[body_start].strip():
        # Multi-line docstring - find closing
        closing = '"""' if '"""' in lines[body_start] else "'''"
        if lines[body_start].strip().count(closing) >= 2:
            # Single-line docstring
            body_start += 1
        else:
            body_start += 1
            while body_start <= end_idx and closing not in lines[body_start]:
                body_start += 1
            body_start += 1  # Skip the closing line

    # Extract body lines
    body_lines = lines[body_start:end_idx+1]

    # Find the original docstring
    docstring_lines = lines[def_idx+1:body_start]
    docstring = ''.join(docstring_lines).strip()

    # Determine which rebinds this handler actually needs
    body_text = ''.join(body_lines)

    # Build selective rebinds
    rebinds = []
    rebinds.append("    import servidor_llamadas as srv\n")

    # Check which state variables are used
    state_vars = [
        'conversaciones_activas', 'conversaciones_activas_lock', 'audio_files',
        'contactos_llamadas', 'audio_cache', 'cache_metadata', 'frase_stats',
        'respuestas_cache', 'cache_respuestas_stats', 'preguntas_frecuentes',
        'callsid_to_bruceid', 'logs_manager', 'cliente_hablando_activo',
        'respuesta_precargada', 'deepgram_transcripciones', 'deepgram_transcripciones_lock',
        'deepgram_ultima_final', 'deepgram_ultima_final_lock', 'deepgram_ultima_parcial',
        'elevenlabs_transcripciones', 'elevenlabs_transcripciones_lock',
        'elevenlabs_ultima_final', 'bruce_audio_enviado_timestamp',
        'calificaciones_llamadas', 'historial_llamadas',
    ]

    for var in state_vars:
        # Check if variable name appears as a word boundary in body
        if re.search(r'\b' + var + r'\b', body_text):
            rebinds.append(f"    {var} = srv.{var}\n")

    # Check utility functions
    util_funcs = [
        'generar_audio_elevenlabs', 'log_evento', 'limpiar_recursos_llamada',
        'registrar_llamada', 'corregir_pronunciacion', 'guardar_cache_en_disco',
        'normalizar_frase_con_nombres', 'registrar_frase_usada',
        'registrar_pregunta_respuesta', 'transcribir_con_whisper',
        'post_procesar_transcripcion_email', 'es_texto_valido_espanol',
        'concatenar_audios_mp3', 'generar_audio_con_nombre', 'generar_audio_async',
        'pre_generar_audios_cache', 'cargar_cache_desde_disco',
        'cargar_historial', 'guardar_historial', 'cargar_calificaciones',
        'guardar_calificaciones', 'cargar_logs', 'guardar_logs',
        'guardar_stats_en_disco',
    ]

    for func in util_funcs:
        if re.search(r'\b' + func + r'\b', body_text):
            rebinds.append(f"    {func} = srv.{func}\n")

    # Check config values
    config_vars = [
        'DEEPGRAM_AVAILABLE', 'USE_DEEPGRAM', 'ELEVENLABS_STT_AVAILABLE',
        'DEPLOY_ID', 'CACHE_DIR', 'twilio_client', 'elevenlabs_client',
        'FRECUENCIA_MIN_CACHE', 'UMBRAL_AUTO_CACHE',
    ]

    for var in config_vars:
        if re.search(r'\b' + var + r'\b', body_text):
            rebinds.append(f"    {var} = srv.{var}\n")

    # Handle global statements
    global_removed = 0
    cleaned_body = []
    for line in body_lines:
        if line.strip().startswith('global '):
            cleaned_body.append(line.replace('global ', '# global  # Removed: using srv. rebinding - '))
            global_removed += 1
        else:
            cleaned_body.append(line)

    # Build the handler file
    # Determine imports needed
    imports = ['import os\n']
    if 'request.' in body_text or 'request,' in body_text:
        imports.append('from flask import request, Response\n')
    elif 'Response(' in body_text:
        imports.append('from flask import Response\n')
    if 'VoiceResponse' in body_text:
        imports.append('from twilio.twiml.voice_response import VoiceResponse, Gather, Play\n')
    if 'send_file' in body_text:
        imports.append('from flask import send_file\n')

    new_func_name = f'handle_{fname}'

    header = f'"""\nServer handler: {handler["route_path"]}\nExtracted from servidor_llamadas.{fname}()\n"""\n'
    header += ''.join(imports)
    header += f'\n\ndef {new_func_name}():\n'
    header += f'    {docstring}\n' if docstring else ''
    header += ''.join(rebinds)
    header += '\n'

    # Write handler file
    with open(handler_module, 'w', encoding='utf-8') as f:
        f.write(header)
        f.writelines(cleaned_body)

    handler_lines = sum(1 for _ in open(handler_module, 'r', encoding='utf-8'))

    print(f"\n  Created {handler_module} ({handler_lines} lines)")
    print(f"    Function: {fname} -> {new_func_name}")
    print(f"    Rebinds: {len(rebinds)-1} variables/functions")
    if global_removed:
        print(f"    Removed {global_removed} global statement(s)")

    extracted.append({
        'handler': handler,
        'handler_file': handler_file,
        'new_func_name': new_func_name,
    })

# Now replace all extracted functions in servidor_llamadas.py with thin wrappers
# Work backwards (from end of file) to avoid line number shifts
extracted_sorted = sorted(extracted, key=lambda x: x['handler']['decorator_line'], reverse=True)

for ext in extracted_sorted:
    h = ext['handler']
    decorator_idx = h['decorator_line']
    end_idx = h['end_line']

    # Get the original decorator line(s)
    decorator = lines[decorator_idx].rstrip() + '\n'

    wrapper = f"""{decorator}def {h['func_name']}():
    \"\"\"Delegated to server/handlers/{ext['handler_file']}.py\"\"\"
    from server.handlers.{ext['handler_file']} import {ext['new_func_name']}
    return {ext['new_func_name']}()


"""

    # Replace lines decorator_idx through end_idx (inclusive) + trailing blank lines
    # Also include any blank lines after the function
    replace_end = end_idx + 1
    while replace_end < len(lines) and lines[replace_end].strip() == '':
        replace_end += 1

    lines = lines[:decorator_idx] + [wrapper] + lines[replace_end:]

# Write the modified servidor_llamadas.py
with open('servidor_llamadas.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)

new_count = sum(1 for _ in open('servidor_llamadas.py', 'r', encoding='utf-8'))
total_extracted = sum(ext['handler']['num_lines'] for ext in extracted)
print(f"\n=== SUMMARY ===")
print(f"Extracted {len(extracted)} handlers ({total_extracted} lines)")
print(f"servidor_llamadas.py: 6180 -> {new_count} lines")
