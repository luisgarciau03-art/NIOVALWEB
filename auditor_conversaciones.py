# -*- coding: utf-8 -*-
"""
Auditor de Conversaciones - Análisis completo de TODOS los logs de Bruce W
Categorías:
  TEC = Bug Técnico (STT timeout, audio, conexión, GPT timeout)
  CTN = Error de Contenido (pitch repetido, fuera de tema, info incorrecta)
  AI  = Evaluación GPT (lógica rota, oportunidades perdidas, preguntas repetidas)
  FLU = Flujo Conversacional (silencio excesivo, cliente habló último, IVR no detectado)
  CAL = Calidad de Llamada (llamada muy corta, sin datos capturados, cliente confundido)
"""

import os
import re
import sys
import json
import glob
from collections import defaultdict, Counter
from datetime import datetime
from difflib import SequenceMatcher

# Encoding UTF-8 para Windows
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

LOGS_DIR = os.path.join(os.path.dirname(__file__), "LOGS")


# ============================================================
# PASO 1: PARSER - Extraer conversaciones de los logs
# ============================================================

def parsear_logs():
    """Parsea TODOS los archivos de log y extrae conversaciones completas."""
    conversaciones = {}  # bruce_id -> {mensajes, metadata, diagnosticos}

    # Regex patterns
    re_cliente = re.compile(
        r'\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\] \[CLIENTE\] (BRUCE\d+) - CLIENTE DIJO: "([^"]*)"'
    )
    re_bruce = re.compile(
        r'\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\] \[BRUCE\] (BRUCE\d+) DICE: "([^"]*)"'
    )
    re_terminada = re.compile(
        r'\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\] \[LLAMADA\] LLAMADA TERMINADA - Estado: (\w[\w-]*), Duración: (\d+)s'
    )
    re_bruce_id = re.compile(r'ID BRUCE(?:\s+generado)?:\s*(BRUCE\d+)')
    re_gpt_timeout = re.compile(r'(?:APITimeoutError|GPT timeout|FIX 533.*timeout)', re.IGNORECASE)
    re_stt_timeout = re.compile(r'(?:Timeouts? Deepgram|ESPERANDO EN SILENCIO|Respuestas? vacías? consecutivas)', re.IGNORECASE)
    re_bug_detector = re.compile(r'\[BUG_DETECTOR\] (BRUCE\d+): (\d+) bug')
    re_vacio = re.compile(r'CLIENTE DIJO: ""')
    re_fix_applied = re.compile(r'FIX (\d+)[A-Z]?:')

    # Obtener todos los archivos de log ordenados
    log_files = sorted(glob.glob(os.path.join(LOGS_DIR, "*.txt")))
    print(f"Encontrados {len(log_files)} archivos de log")

    for log_file in log_files:
        try:
            with open(log_file, 'r', encoding='utf-8', errors='replace') as f:
                contenido = f.read()
        except Exception as e:
            print(f"  Error leyendo {log_file}: {e}")
            continue

        lineas = contenido.split('\n')

        for linea in lineas:
            # Detectar IDs de BRUCE
            match_id = re_bruce_id.search(linea)
            if match_id:
                bid = match_id.group(1)
                if bid not in conversaciones:
                    conversaciones[bid] = {
                        'mensajes': [],
                        'duracion': 0,
                        'estado_final': '',
                        'bugs_detectados': 0,
                        'gpt_timeouts': 0,
                        'stt_timeouts': 0,
                        'respuestas_vacias': 0,
                        'fixes_activados': set(),
                        'archivo': os.path.basename(log_file),
                    }

            # Mensajes del cliente
            match_cliente = re_cliente.search(linea)
            if match_cliente:
                ts, bid, texto = match_cliente.groups()
                if bid in conversaciones:
                    conversaciones[bid]['mensajes'].append({
                        'timestamp': ts,
                        'rol': 'cliente',
                        'texto': texto
                    })

            # Mensajes de Bruce
            match_bruce = re_bruce.search(linea)
            if match_bruce:
                ts, bid, texto = match_bruce.groups()
                if bid in conversaciones:
                    conversaciones[bid]['mensajes'].append({
                        'timestamp': ts,
                        'rol': 'bruce',
                        'texto': texto
                    })

            # Llamada terminada
            match_term = re_terminada.search(linea)
            if match_term:
                ts, estado, duracion = match_term.groups()
                # Buscar el BRUCE ID más reciente que no tenga duración
                for bid in reversed(list(conversaciones.keys())):
                    if conversaciones[bid]['duracion'] == 0:
                        conversaciones[bid]['duracion'] = int(duracion)
                        conversaciones[bid]['estado_final'] = estado
                        break

            # Bug detector
            match_bug = re_bug_detector.search(linea)
            if match_bug:
                bid, count = match_bug.groups()
                if bid in conversaciones:
                    conversaciones[bid]['bugs_detectados'] = int(count)

            # GPT timeouts
            if re_gpt_timeout.search(linea):
                for bid in reversed(list(conversaciones.keys())):
                    if conversaciones[bid]['mensajes']:
                        conversaciones[bid]['gpt_timeouts'] += 1
                        break

            # STT timeouts
            if re_stt_timeout.search(linea):
                for bid in reversed(list(conversaciones.keys())):
                    if conversaciones[bid]['mensajes']:
                        conversaciones[bid]['stt_timeouts'] += 1
                        break

            # Respuestas vacías del cliente
            if re_vacio.search(linea):
                match_vacio_bid = re.search(r'(BRUCE\d+)', linea)
                if match_vacio_bid:
                    bid = match_vacio_bid.group(1)
                    if bid in conversaciones:
                        conversaciones[bid]['respuestas_vacias'] += 1

            # FIX activados
            for fix_match in re_fix_applied.finditer(linea):
                fix_num = fix_match.group(1)
                match_fix_bid = re.search(r'(BRUCE\d+)', linea)
                if match_fix_bid:
                    bid = match_fix_bid.group(1)
                    if bid in conversaciones:
                        conversaciones[bid]['fixes_activados'].add(int(fix_num))

    # Convertir sets a listas para serialización
    for bid in conversaciones:
        conversaciones[bid]['fixes_activados'] = sorted(list(conversaciones[bid]['fixes_activados']))

    print(f"Total conversaciones extraídas: {len(conversaciones)}")
    return conversaciones


# ============================================================
# PASO 2: AUDITOR - Evaluar cada conversación
# ============================================================

def auditar_conversacion(bruce_id, conv):
    """Audita una conversación y retorna lista de bugs encontrados."""
    bugs = []
    mensajes = conv['mensajes']

    if not mensajes:
        return bugs

    # Extraer textos por rol
    msgs_bruce = [m for m in mensajes if m['rol'] == 'bruce']
    msgs_cliente = [m for m in mensajes if m['rol'] == 'cliente']
    textos_bruce = [m['texto'].lower() for m in msgs_bruce]
    textos_cliente = [m['texto'].lower() for m in msgs_cliente]

    # ========== TEC: Bugs Técnicos ==========

    # TEC-001: GPT Timeout
    if conv['gpt_timeouts'] > 0:
        bugs.append({
            'categoria': 'TEC',
            'codigo': 'TEC-001',
            'nombre': 'GPT_TIMEOUT',
            'severidad': 'HIGH' if conv['gpt_timeouts'] >= 2 else 'MEDIUM',
            'descripcion': f"GPT timeout detectado {conv['gpt_timeouts']}x durante la llamada"
        })

    # TEC-002: STT Timeout / Transcripciones vacías
    if conv['stt_timeouts'] >= 3:
        bugs.append({
            'categoria': 'TEC',
            'codigo': 'TEC-002',
            'nombre': 'STT_TIMEOUT_EXCESIVO',
            'severidad': 'HIGH',
            'descripcion': f"STT timeout {conv['stt_timeouts']}x - posible problema de audio/conexión"
        })

    # TEC-003: Respuestas vacías del cliente (STT no transcribió)
    if conv['respuestas_vacias'] >= 3:
        bugs.append({
            'categoria': 'TEC',
            'codigo': 'TEC-003',
            'nombre': 'TRANSCRIPCION_VACIA_EXCESIVA',
            'severidad': 'MEDIUM',
            'descripcion': f"Cliente tuvo {conv['respuestas_vacias']} respuestas vacías (STT no transcribió)"
        })

    # TEC-004: Llamada muy corta (posible error de conexión)
    if conv['duracion'] > 0 and conv['duracion'] < 10 and len(mensajes) <= 2:
        bugs.append({
            'categoria': 'TEC',
            'codigo': 'TEC-004',
            'nombre': 'LLAMADA_ULTRA_CORTA',
            'severidad': 'LOW',
            'descripcion': f"Llamada de {conv['duracion']}s con solo {len(mensajes)} mensajes"
        })

    # ========== CTN: Errores de Contenido ==========

    # CTN-001: Pitch NIOVAL repetido (mejorado: solo cuenta pitch COMPLETO de Bruce)
    # Un pitch completo requiere "nioval" + al menos 1 palabra clave de venta
    palabras_pitch = ['catálogo', 'catalogo', 'productos', 'distribuidor', 'marca', 'línea', 'linea']
    menciones_pitch_completo = 0
    for t in textos_bruce:
        if 'nioval' in t and any(p in t for p in palabras_pitch):
            menciones_pitch_completo += 1
    if menciones_pitch_completo >= 2:
        bugs.append({
            'categoria': 'CTN',
            'codigo': 'CTN-001',
            'nombre': 'PITCH_REPETIDO',
            'severidad': 'MEDIUM',
            'descripcion': f"Bruce repitió pitch completo NIOVAL {menciones_pitch_completo} veces"
        })

    # CTN-002: Bruce habla de problemas de conexión
    patrones_conexion = ['problemas de conexión', 'problemas de conexion', 'problema con la línea',
                         'problema con la linea', 'no se escucha', 'hay interferencia',
                         'problemas técnicos', 'problemas tecnicos']
    for i, texto in enumerate(textos_bruce):
        if any(p in texto for p in patrones_conexion):
            bugs.append({
                'categoria': 'CTN',
                'codigo': 'CTN-002',
                'nombre': 'HABLA_PROBLEMAS_CONEXION',
                'severidad': 'MEDIUM',
                'descripcion': f"Bruce mencionó problemas de conexión: '{msgs_bruce[i]['texto'][:80]}'"
            })
            break

    # CTN-003: Bruce pide "su número" sin contexto
    for i, texto in enumerate(textos_bruce):
        patrones_numero_sin_contexto = [
            'dígame su número', 'digame su numero', 'me da su número', 'me da su numero',
            'cuál es su número', 'cual es su numero', 'páseme su número', 'paseme su numero'
        ]
        if any(p in texto for p in patrones_numero_sin_contexto):
            # Verificar si NO especificó para qué (whatsapp, catálogo, encargado)
            if 'whatsapp' not in texto and 'catálogo' not in texto and 'catalogo' not in texto and 'encargado' not in texto:
                bugs.append({
                    'categoria': 'CTN',
                    'codigo': 'CTN-003',
                    'nombre': 'NUMERO_SIN_CONTEXTO',
                    'severidad': 'HIGH',
                    'descripcion': f"Bruce pidió número sin especificar para qué: '{msgs_bruce[i]['texto'][:80]}'"
                })
                break

    # CTN-004: Bruce inventó marcas (no NIOVAL)
    marcas_inventadas = ['truper', 'pretul', 'pochteca', 'urrea', 'stanley', 'dewalt']
    for i, texto in enumerate(textos_bruce):
        for marca in marcas_inventadas:
            if marca in texto:
                bugs.append({
                    'categoria': 'CTN',
                    'codigo': 'CTN-004',
                    'nombre': 'MARCA_INVENTADA',
                    'severidad': 'CRITICAL',
                    'descripcion': f"Bruce mencionó marca no autorizada '{marca}': '{msgs_bruce[i]['texto'][:80]}'"
                })
                break

    # ========== AI: Evaluación GPT ==========

    # AI-001: Pregunta por encargado repetida
    preguntas_encargado = sum(1 for t in textos_bruce if 'encargado' in t and ('?' in t or 'encontrar' in t or 'se encuentra' in t))
    if preguntas_encargado >= 2:
        bugs.append({
            'categoria': 'AI',
            'codigo': 'AI-001',
            'nombre': 'PREGUNTA_ENCARGADO_REPETIDA',
            'severidad': 'MEDIUM',
            'descripcion': f"Bruce preguntó por el encargado {preguntas_encargado} veces"
        })

    # AI-002: Pide WhatsApp después de que cliente dijo que no tiene
    cliente_sin_whatsapp = any('no tengo whatsapp' in t or 'no es whatsapp' in t or
                               'teléfono fijo' in t or 'telefono fijo' in t or
                               'es fijo' in t for t in textos_cliente)
    if cliente_sin_whatsapp:
        # Verificar si Bruce pidió WhatsApp DESPUÉS
        idx_no_whatsapp = None
        for i, m in enumerate(mensajes):
            if m['rol'] == 'cliente' and ('no tengo whatsapp' in m['texto'].lower() or
                                          'teléfono fijo' in m['texto'].lower() or
                                          'telefono fijo' in m['texto'].lower()):
                idx_no_whatsapp = i
                break
        if idx_no_whatsapp is not None:
            for m in mensajes[idx_no_whatsapp + 1:]:
                if m['rol'] == 'bruce' and 'whatsapp' in m['texto'].lower():
                    bugs.append({
                        'categoria': 'AI',
                        'codigo': 'AI-002',
                        'nombre': 'INSISTE_WHATSAPP_POST_RECHAZO',
                        'severidad': 'HIGH',
                        'descripcion': "Bruce pidió WhatsApp después de que cliente dijo que no tiene"
                    })
                    break

    # AI-003: Bruce colgó sin ofrecer alternativa
    if conv['estado_final'] == 'completed' and len(msgs_bruce) >= 2:
        ultimo_bruce = textos_bruce[-1] if textos_bruce else ""
        # Si Bruce se despidió sin haber capturado datos y sin ofrecer alternativa
        patrones_despedida_prematura = ['me comunico después', 'me comunico despues',
                                        'le marco después', 'le marco despues',
                                        'gracias por su tiempo']
        if any(p in ultimo_bruce for p in patrones_despedida_prematura):
            # Verificar si capturó algún dato
            capturo_dato = any('anotado' in t or 'registrado' in t or 'perfecto' in t
                              for t in textos_bruce)
            if not capturo_dato:
                bugs.append({
                    'categoria': 'AI',
                    'codigo': 'AI-003',
                    'nombre': 'DESPEDIDA_SIN_ALTERNATIVA',
                    'severidad': 'HIGH',
                    'descripcion': f"Bruce se despidió sin capturar datos ni ofrecer alternativa"
                })

    # AI-004: Bruce repite la misma respuesta (mejorado: similarity ratio >= 0.85)
    respuesta_repetida_encontrada = False
    for i in range(len(textos_bruce)):
        if respuesta_repetida_encontrada:
            break
        for j in range(i + 1, len(textos_bruce)):
            ti, tj = textos_bruce[i], textos_bruce[j]
            # Solo comparar respuestas con contenido sustancial (>30 chars)
            if len(ti) > 30 and len(tj) > 30:
                ratio = SequenceMatcher(None, ti, tj).ratio()
                if ratio >= 0.85:
                    bugs.append({
                        'categoria': 'AI',
                        'codigo': 'AI-004',
                        'nombre': 'RESPUESTA_REPETIDA_EXACTA',
                        'severidad': 'MEDIUM',
                        'descripcion': f"Bruce repitió respuesta ({ratio:.0%} similar): '{msgs_bruce[i]['texto'][:60]}...'"
                    })
                    respuesta_repetida_encontrada = True
                    break

    # AI-005: Cliente ofreció dato pero Bruce no lo capturó (mejorado: verificar confirmación)
    patrones_oferta_cliente = ['te paso', 'le paso', 'te doy', 'le doy', 'aquí está',
                                'aqui esta', 'el correo es', 'el número es', 'el numero es',
                                'anota', 'apunta']
    patrones_confirmacion_bruce = ['perfecto', 'ya lo tengo', 'anoto', 'anotado', 'registrado',
                                    'excelente', 'gracias por', 'le envío', 'le envio',
                                    'le mando', 'catálogo', 'catalogo', 'correcto']
    for i, m in enumerate(mensajes):
        if m['rol'] == 'cliente' and any(p in m['texto'].lower() for p in patrones_oferta_cliente):
            # Verificar si Bruce respondió apropiadamente en los SIGUIENTES 2 mensajes
            bruce_confirmo = False
            for m2 in mensajes[i + 1:i + 4]:  # Revisar hasta 3 msgs después
                if m2['rol'] == 'bruce':
                    texto_bruce = m2['texto'].lower()
                    if any(p in texto_bruce for p in patrones_confirmacion_bruce):
                        bruce_confirmo = True
                        break
            if not bruce_confirmo:
                # Solo marcar si Bruce IGNORÓ (pidió encargado o se despidió)
                siguiente_bruce = None
                for m2 in mensajes[i + 1:]:
                    if m2['rol'] == 'bruce':
                        siguiente_bruce = m2['texto'].lower()
                        break
                if siguiente_bruce and ('encargado' in siguiente_bruce or 'me comunico' in siguiente_bruce):
                    bugs.append({
                        'categoria': 'AI',
                        'codigo': 'AI-005',
                        'nombre': 'OFERTA_DATO_IGNORADA',
                        'severidad': 'HIGH',
                        'descripcion': f"Cliente ofreció dato '{m['texto'][:60]}' pero Bruce no lo capturó"
                    })
                    break

    # ========== FLU: Flujo Conversacional ==========

    # FLU-001: Cliente habló último (mejorado: excluir despedidas naturales)
    if mensajes and mensajes[-1]['rol'] == 'cliente' and mensajes[-1]['texto'].strip():
        ultimo_cliente = mensajes[-1]['texto'].strip()
        ultimo_lower = ultimo_cliente.lower()
        # Excluir si es una despedida natural del cliente (no es un bug)
        despedidas_naturales = ['gracias', 'hasta luego', 'bye', 'adiós', 'adios',
                                'está bien', 'esta bien', 'ok', 'bueno', 'sale',
                                'va', 'órale', 'orale', 'ándale', 'andale',
                                'que le vaya bien', 'igualmente', 'cuídese', 'cuidese']
        es_despedida = any(d in ultimo_lower for d in despedidas_naturales)
        if len(ultimo_cliente) > 3 and not es_despedida:
            bugs.append({
                'categoria': 'FLU',
                'codigo': 'FLU-001',
                'nombre': 'CLIENTE_HABLO_ULTIMO',
                'severidad': 'HIGH',
                'descripcion': f"Cliente habló último sin respuesta de Bruce: '{ultimo_cliente[:60]}'"
            })

    # FLU-002: Silencio excesivo (cliente habla 3+ veces sin respuesta de Bruce)
    silencios_consecutivos = 0
    max_silencios = 0
    for m in mensajes:
        if m['rol'] == 'cliente' and m['texto'].strip():
            silencios_consecutivos += 1
        elif m['rol'] == 'bruce':
            max_silencios = max(max_silencios, silencios_consecutivos)
            silencios_consecutivos = 0
    max_silencios = max(max_silencios, silencios_consecutivos)

    if max_silencios >= 3:
        bugs.append({
            'categoria': 'FLU',
            'codigo': 'FLU-002',
            'nombre': 'SILENCIO_EXCESIVO',
            'severidad': 'CRITICAL' if max_silencios >= 5 else 'HIGH',
            'descripcion': f"Cliente habló {max_silencios} veces consecutivas sin respuesta de Bruce"
        })

    # FLU-003: IVR no detectado (mejorado: solo primeros 3 msgs + Bruce respondió DESPUÉS)
    patrones_ivr = ['marque uno', 'marqué uno', 'marque 1', 'para ventas',
                     'para administración', 'para administracion', 'bienvenidos a',
                     'le agradecemos su preferencia', 'vuelva a intentarlo',
                     'oprima', 'presione', 'extensión', 'extension',
                     'su llamada es importante', 'por favor espere',
                     'correo de voz', 'deje su mensaje']
    # Solo revisar primeros 4 mensajes (IVR aparece al inicio de la llamada)
    primeros_msgs = mensajes[:4]
    for idx_m, m in enumerate(primeros_msgs):
        if m['rol'] == 'cliente':
            texto_lower = m['texto'].lower()
            if any(p in texto_lower for p in patrones_ivr):
                # Verificar si Bruce respondió DESPUÉS con contenido conversacional (no solo saludo)
                bruce_despues_ivr = [mb for mb in mensajes[idx_m + 1:]
                                     if mb['rol'] == 'bruce' and len(mb['texto']) > 20]
                if len(bruce_despues_ivr) >= 2:
                    bugs.append({
                        'categoria': 'FLU',
                        'codigo': 'FLU-003',
                        'nombre': 'IVR_NO_DETECTADO',
                        'severidad': 'MEDIUM',
                        'descripcion': f"IVR no detectado: '{m['texto'][:60]}'"
                    })
                    break

    # ========== CAL: Calidad de Llamada ==========

    # Keywords expandidos de confirmación de captura (usado por CAL-001 y CAL-002)
    confirmaciones_captura = ['anotado', 'registrado', 'perfecto, ya', 'excelente',
                               'le envío', 'le envio', 'le mando', 'catálogo a su',
                               'catalogo a su', 'le marco', 'agendo', 'ya lo tengo',
                               'ya tengo su', 'correcto, entonces', 'a su whatsapp',
                               'a su correo', 'le llamo']

    # CAL-001: Llamada sin datos capturados (mejorado: más keywords + check datos reales)
    total_turnos = len(mensajes)
    if total_turnos >= 6:  # Al menos 3 intercambios
        capturo_algo = any(any(kw in t for kw in confirmaciones_captura) for t in textos_bruce)
        # También verificar si hay datos reales mencionados por Bruce (WhatsApp/email/teléfono)
        datos_reales = any('@' in t or 'whatsapp' in t and ('33' in t or '55' in t or '66' in t)
                          for t in textos_bruce)
        # Verificar si cliente rechazó todo (no es bug de Bruce)
        cliente_rechazo = any('no me interesa' in t or 'no nos interesa' in t or
                              'no gracias' in t or 'ya tenemos proveedor' in t
                              for t in textos_cliente)
        if not capturo_algo and not datos_reales and not cliente_rechazo and conv['estado_final'] == 'completed':
            bugs.append({
                'categoria': 'CAL',
                'codigo': 'CAL-001',
                'nombre': 'SIN_DATOS_CAPTURADOS',
                'severidad': 'MEDIUM',
                'descripcion': f"Llamada de {total_turnos} mensajes sin capturar datos de contacto"
            })

    # CAL-002: Cliente mostró interés pero Bruce no cerró (mejorado: keywords expandidos)
    patrones_interes = ['me interesa', 'mándame', 'mandame', 'envíame', 'enviame',
                         'sí, claro', 'si, claro', 'claro que sí', 'claro que si',
                         'pásame', 'pasame', 'mándalo', 'mandalo', 'envíalo', 'envialo']
    cliente_interesado = any(any(p in t for p in patrones_interes) for t in textos_cliente)
    if cliente_interesado and total_turnos >= 4:
        capturo_dato = any(any(kw in t for kw in confirmaciones_captura) for t in textos_bruce)
        if not capturo_dato:
            bugs.append({
                'categoria': 'CAL',
                'codigo': 'CAL-002',
                'nombre': 'INTERES_NO_CERRADO',
                'severidad': 'HIGH',
                'descripcion': "Cliente mostró interés pero no se capturaron datos"
            })

    return bugs


# ============================================================
# PASO 3: GENERAR REPORTE
# ============================================================

def generar_reporte(conversaciones, resultados):
    """Genera reporte completo de auditoría."""
    total_conversaciones = len(conversaciones)
    total_con_bugs = sum(1 for bugs in resultados.values() if bugs)
    total_bugs = sum(len(bugs) for bugs in resultados.values())

    # Contadores por categoría
    por_categoria = Counter()
    por_codigo = Counter()
    por_severidad = Counter()
    bugs_detalle = []

    for bruce_id, bugs in resultados.items():
        for bug in bugs:
            por_categoria[bug['categoria']] += 1
            por_codigo[bug['codigo']] += 1
            por_severidad[bug['severidad']] += 1
            bugs_detalle.append({
                'bruce_id': bruce_id,
                **bug
            })

    # Imprimir reporte
    print("\n" + "=" * 80)
    print("  AUDITORÍA COMPLETA DE CONVERSACIONES - BRUCE W")
    print("=" * 80)

    print(f"\n  RESUMEN GENERAL")
    print(f"  Total conversaciones analizadas: {total_conversaciones}")
    print(f"  Conversaciones con bugs: {total_con_bugs} ({round(total_con_bugs/total_conversaciones*100, 1) if total_conversaciones else 0}%)")
    print(f"  Total bugs detectados: {total_bugs}")
    print(f"  Promedio bugs/conversación: {round(total_bugs/total_conversaciones, 2) if total_conversaciones else 0}")

    print(f"\n  POR CATEGORÍA")
    print(f"  {'Categoría':<6} {'Nombre':<30} {'Bugs':>6} {'%':>8}")
    print(f"  {'-'*6} {'-'*30} {'-'*6} {'-'*8}")
    categorias_nombres = {
        'TEC': 'Bug Técnico',
        'CTN': 'Error de Contenido',
        'AI': 'Evaluación GPT',
        'FLU': 'Flujo Conversacional',
        'CAL': 'Calidad de Llamada'
    }
    for cat in ['TEC', 'CTN', 'AI', 'FLU', 'CAL']:
        count = por_categoria.get(cat, 0)
        pct = round(count / total_bugs * 100, 1) if total_bugs else 0
        print(f"  {cat:<6} {categorias_nombres.get(cat, cat):<30} {count:>6} {pct:>7.1f}%")

    print(f"\n  POR SEVERIDAD")
    for sev in ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW']:
        count = por_severidad.get(sev, 0)
        pct = round(count / total_bugs * 100, 1) if total_bugs else 0
        print(f"  {sev:<10} {count:>6} ({pct:.1f}%)")

    print(f"\n  TOP 15 BUGS MÁS FRECUENTES")
    print(f"  {'Código':<12} {'Nombre':<35} {'Count':>6}")
    print(f"  {'-'*12} {'-'*35} {'-'*6}")
    for codigo, count in por_codigo.most_common(15):
        # Buscar nombre del bug
        nombre = next((b['nombre'] for b in bugs_detalle if b['codigo'] == codigo), codigo)
        print(f"  {codigo:<12} {nombre:<35} {count:>6}")

    # Conversaciones con más bugs
    conv_por_bugs = sorted(
        [(bid, len(bugs)) for bid, bugs in resultados.items() if bugs],
        key=lambda x: x[1],
        reverse=True
    )
    print(f"\n  TOP 10 CONVERSACIONES CON MÁS BUGS")
    print(f"  {'BRUCE ID':<12} {'Bugs':>6} {'Duración':>10} {'Mensajes':>10}")
    print(f"  {'-'*12} {'-'*6} {'-'*10} {'-'*10}")
    for bid, bug_count in conv_por_bugs[:10]:
        dur = conversaciones[bid]['duracion']
        msgs = len(conversaciones[bid]['mensajes'])
        print(f"  {bid:<12} {bug_count:>6} {dur:>8}s {msgs:>10}")

    print("\n" + "=" * 80)

    return {
        'total_conversaciones': total_conversaciones,
        'total_con_bugs': total_con_bugs,
        'total_bugs': total_bugs,
        'por_categoria': dict(por_categoria),
        'por_codigo': dict(por_codigo),
        'por_severidad': dict(por_severidad),
        'top_bugs': por_codigo.most_common(20),
        'bugs_detalle': bugs_detalle
    }


def guardar_reporte_json(reporte, conversaciones, resultados):
    """Guarda reporte completo en JSON para análisis posterior."""
    output = {
        'timestamp': datetime.now().isoformat(),
        'resumen': {
            'total_conversaciones': reporte['total_conversaciones'],
            'total_con_bugs': reporte['total_con_bugs'],
            'total_bugs': reporte['total_bugs'],
            'por_categoria': reporte['por_categoria'],
            'por_severidad': reporte['por_severidad'],
            'top_bugs': reporte['top_bugs'],
        },
        'bugs_por_conversacion': {}
    }

    for bruce_id, bugs in resultados.items():
        if bugs:
            output['bugs_por_conversacion'][bruce_id] = {
                'duracion': conversaciones[bruce_id]['duracion'],
                'total_mensajes': len(conversaciones[bruce_id]['mensajes']),
                'bugs': bugs
            }

    ruta = os.path.join(os.path.dirname(__file__), 'auditoria_completa_resultado.json')
    with open(ruta, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"\n  Reporte JSON guardado en: {ruta}")
    return ruta


# ============================================================
# MAIN
# ============================================================

def main(min_bruce_id=None):
    """
    Auditor principal.
    Args:
        min_bruce_id: Si se especifica (ej: 2175), solo audita BRUCE >= ese número.
                      Útil para ver solo bugs recientes (post-fix).
    """
    filtro_txt = f" (BRUCE >= {min_bruce_id})" if min_bruce_id else ""
    print("\n" + "=" * 80)
    print(f"  AUDITOR DE CONVERSACIONES - BRUCE W{filtro_txt}")
    print("  Analizando TODOS los logs disponibles...")
    print("=" * 80)

    # Paso 1: Parsear logs
    print("\n[1/3] Parseando archivos de log...")
    conversaciones = parsear_logs()

    # Filtrar conversaciones con al menos 1 mensaje
    conversaciones_validas = {k: v for k, v in conversaciones.items() if v['mensajes']}
    print(f"  Conversaciones con mensajes: {len(conversaciones_validas)}")

    # Filtro opcional por BRUCE ID mínimo
    if min_bruce_id:
        conversaciones_validas = {
            k: v for k, v in conversaciones_validas.items()
            if int(re.search(r'\d+', k).group()) >= min_bruce_id
        }
        print(f"  Conversaciones post-BRUCE{min_bruce_id}: {len(conversaciones_validas)}")

    # Paso 2: Auditar cada conversación
    print("\n[2/3] Auditando conversaciones...")
    resultados = {}
    for bruce_id, conv in conversaciones_validas.items():
        bugs = auditar_conversacion(bruce_id, conv)
        resultados[bruce_id] = bugs

    # Paso 3: Generar reporte
    print("\n[3/3] Generando reporte...")
    reporte = generar_reporte(conversaciones_validas, resultados)

    # Guardar JSON
    guardar_reporte_json(reporte, conversaciones_validas, resultados)

    return reporte


if __name__ == "__main__":
    # Argumento opcional: python auditor_conversaciones.py 2175
    # Solo audita BRUCE >= 2175 (llamadas recientes post-fix)
    min_id = None
    if len(sys.argv) > 1:
        try:
            min_id = int(sys.argv[1])
        except ValueError:
            pass
    main(min_bruce_id=min_id)
