"""
Extractor de acciones de conversacion desde logs Railway.
Analiza 362+ archivos de logs para identificar TODAS las acciones posibles
que Bruce necesita realizar en una llamada.

Proyecto: BRUCE TEMPLATES ENGINE
"""

import os
import re
import json
from collections import Counter, defaultdict

LOGS_DIR = r"C:\Users\PC 1\AgenteVentas\LOGS"

# Patrones para extraer turnos de conversacion
RE_BRUCE_DICE = re.compile(
    r'\[BRUCE\]\s*(BRUCE\d+)\s*DICE:\s*"([^"]+)"'
)
RE_CLIENTE_DICE = re.compile(
    r'\[(?:SPEECH|TRANSCRIPCION|STT)\].*?(?:FINAL|texto)[:\s]*"?([^"]+)"?',
    re.IGNORECASE
)
RE_CLIENTE_FINAL = re.compile(
    r'(?:Texto final|FINAL|speech_final|Transcripcion final)[:\s]*"?([^"\n]+)"?',
    re.IGNORECASE
)
RE_PROCESANDO = re.compile(
    r'Procesando (?:respuesta|transcripci).*?[:\s]*"?([^"\n]+)"?',
    re.IGNORECASE
)
RE_FSM_INTENT = re.compile(
    r'FSM.*?intent[:\s]*(\w+)',
    re.IGNORECASE
)
RE_FSM_STATE = re.compile(
    r'FSM.*?(?:estado|state)[:\s]*(\w+)',
    re.IGNORECASE
)
RE_FSM_ROUTE = re.compile(
    r'FSM.*?ruta[:\s]*(\w+)',
    re.IGNORECASE
)
RE_GPT_RESPUESTA = re.compile(
    r'(?:GPT|OpenAI|gpt).*?(?:respuesta|response)[:\s]*"?([^"\n]{10,})"?',
    re.IGNORECASE
)
RE_TEMPLATE = re.compile(
    r'(?:template|plantilla|ruta)[:\s]*(\w+)',
    re.IGNORECASE
)
RE_LLAMADA_INICIO = re.compile(
    r'LLAMADA INICIADA.*?\+\d+.*?\(([^)]+)\)'
)
RE_LLAMADA_FIN = re.compile(
    r'(?:LLAMADA FINALIZADA|RESULTADO FINAL|Colgo|hangup)',
    re.IGNORECASE
)
RE_CACHE_HIT = re.compile(
    r'(?:cache|cach[eé])[:\s]*(hit|miss|desde cach)',
    re.IGNORECASE
)
RE_POST_FILTER = re.compile(
    r'(?:FIX \d+|post.?filter|override|intercept)',
    re.IGNORECASE
)

# Patrones para lo que DICE el cliente (mas granular)
RE_TEXTO_CLIENTE = re.compile(
    r'(?:'
    r'Texto (?:final|completo|acumulado)[:\s]*"([^"]+)"'
    r'|FINAL[:\s]*"([^"]+)"'
    r'|speech_final[:\s]*"([^"]+)"'
    r'|Procesando respuesta para[:\s]*"([^"]+)"'
    r'|texto_para_procesar[:\s]*"([^"]+)"'
    r'|FIX \d+:.*?texto[:\s]*"([^"]+)"'
    r')',
    re.IGNORECASE
)


def extraer_conversaciones(filepath):
    """Extrae conversaciones completas de un archivo de log."""
    conversaciones = []
    conversacion_actual = None

    try:
        with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
            lines = f.readlines()
    except Exception as e:
        print(f"Error leyendo {filepath}: {e}")
        return []

    for i, line in enumerate(lines):
        # Detectar inicio de llamada
        m = RE_LLAMADA_INICIO.search(line)
        if m:
            if conversacion_actual and conversacion_actual['turnos']:
                conversaciones.append(conversacion_actual)
            conversacion_actual = {
                'negocio': m.group(1),
                'archivo': os.path.basename(filepath),
                'turnos': [],
                'bruce_id': None,
                'intents': [],
                'states': [],
                'routes': [],
                'post_filters': [],
            }
            continue

        if not conversacion_actual:
            # Crear una conversacion por defecto si encontramos turnos sin inicio
            conversacion_actual = {
                'negocio': 'desconocido',
                'archivo': os.path.basename(filepath),
                'turnos': [],
                'bruce_id': None,
                'intents': [],
                'states': [],
                'routes': [],
                'post_filters': [],
            }

        # Detectar Bruce dice
        m = RE_BRUCE_DICE.search(line)
        if m:
            bruce_id = m.group(1)
            texto_bruce = m.group(2)
            conversacion_actual['bruce_id'] = bruce_id
            conversacion_actual['turnos'].append({
                'quien': 'BRUCE',
                'texto': texto_bruce,
                'linea': i + 1,
            })
            continue

        # Detectar texto del cliente
        for pattern in [RE_TEXTO_CLIENTE, RE_PROCESANDO]:
            m = pattern.search(line)
            if m:
                texto = next((g for g in m.groups() if g), None)
                if texto and len(texto.strip()) > 1:
                    conversacion_actual['turnos'].append({
                        'quien': 'CLIENTE',
                        'texto': texto.strip(),
                        'linea': i + 1,
                    })
                break

        # Detectar FSM intent
        m = RE_FSM_INTENT.search(line)
        if m:
            conversacion_actual['intents'].append(m.group(1))

        # Detectar FSM state
        m = RE_FSM_STATE.search(line)
        if m:
            conversacion_actual['states'].append(m.group(1))

        # Detectar FSM route
        m = RE_FSM_ROUTE.search(line)
        if m:
            conversacion_actual['routes'].append(m.group(1))

        # Detectar post-filters
        m = RE_POST_FILTER.search(line)
        if m:
            conversacion_actual['post_filters'].append(m.group(0))

        # Detectar fin de llamada
        if RE_LLAMADA_FIN.search(line):
            if conversacion_actual and conversacion_actual['turnos']:
                conversaciones.append(conversacion_actual)
                conversacion_actual = None

    # Ultima conversacion
    if conversacion_actual and conversacion_actual['turnos']:
        conversaciones.append(conversacion_actual)

    return conversaciones


def clasificar_accion_bruce(texto_bruce, texto_cliente_prev, contexto):
    """Clasifica que ACCION esta tomando Bruce basado en su respuesta."""
    t = texto_bruce.lower()

    # SALUDO
    if any(w in t for w in ['buen dia', 'buenas tardes', 'buenos dias', 'hola,']):
        if 'encargado' in t or 'compras' in t:
            return 'SALUDO_Y_PEDIR_ENCARGADO'
        if 'nioval' in t or 'bruce' in t:
            return 'SALUDO_CON_PRESENTACION'
        return 'SALUDO_SIMPLE'

    # IDENTIFICACION / PRESENTACION
    if any(w in t for w in ['mi nombre es bruce', 'me comunico de', 'le llamo de', 'soy bruce', 'de la marca nioval', 'de parte de nioval']):
        if 'encargado' in t or 'compras' in t:
            return 'PRESENTACION_Y_PEDIR_ENCARGADO'
        return 'PRESENTACION_NIOVAL'

    # PEDIR ENCARGADO
    if any(w in t for w in ['encargado', 'encargada', 'quien toma las decisiones', 'area de compras']):
        if 'comunicar' in t or 'pasar' in t:
            return 'PEDIR_COMUNICAR_ENCARGADO'
        return 'PREGUNTAR_POR_ENCARGADO'

    # PITCH / OFERTA
    if any(w in t for w in ['catalogo', 'catálogo']):
        if any(w in t for w in ['enviar', 'mandar', 'compartir']):
            return 'OFRECER_ENVIAR_CATALOGO'
        if any(w in t for w in ['recibir', 'le gustaria', 'le gustaría']):
            return 'PREGUNTAR_SI_QUIERE_CATALOGO'
        return 'MENCIONAR_CATALOGO'

    if any(w in t for w in ['productos', 'griferia', 'cinta', 'herramienta', 'limpieza', 'ferreteria', 'ferretería']):
        if 'manejamos' in t or 'ofrecemos' in t or 'especializamos' in t:
            return 'PITCH_PRODUCTOS'
        return 'MENCIONAR_PRODUCTOS'

    # PEDIR WHATSAPP
    if 'whatsapp' in t:
        if any(w in t for w in ['numero', 'número', 'cual es', 'cuál es', 'proporcionar', 'compartir']):
            return 'PEDIR_WHATSAPP'
        if any(w in t for w in ['enviar', 'mandar']):
            return 'CONFIRMAR_ENVIO_WHATSAPP'
        return 'MENCIONAR_WHATSAPP'

    # PEDIR CORREO
    if any(w in t for w in ['correo', 'email', 'e-mail']):
        if any(w in t for w in ['cual es', 'cuál es', 'proporcionar', 'compartir', 'digame', 'dígame']):
            return 'PEDIR_CORREO'
        if any(w in t for w in ['enviar', 'mandar']):
            return 'CONFIRMAR_ENVIO_CORREO'
        return 'MENCIONAR_CORREO'

    # PEDIR TELEFONO / NUMERO
    if any(w in t for w in ['numero', 'número', 'telefono', 'teléfono']):
        if 'mi numero' in t or 'mi número' in t or 'el numero es' in t:
            return 'DAR_NUMERO_BRUCE'
        if any(w in t for w in ['proporcionar', 'compartir', 'digame', 'dígame', 'repetir']):
            return 'PEDIR_NUMERO'
        if 'anotar' in t or 'anotado' in t or 'anote' in t:
            return 'CONFIRMAR_NUMERO_ANOTADO'
        if 'completo' in t or 'faltan' in t or 'digitos' in t or 'dígitos' in t:
            return 'PEDIR_NUMERO_COMPLETO'
        return 'MENCIONAR_NUMERO'

    # CONFIRMAR DATO
    if any(w in t for w in ['perfecto', 'excelente', 'muy bien', 'anotado', 'correcto']):
        if any(w in t for w in ['gracias', 'agradezco']):
            return 'CONFIRMAR_Y_AGRADECER'
        return 'CONFIRMAR_DATO'

    # DESPEDIDA
    if any(w in t for w in ['hasta luego', 'buen dia', 'buenas tardes', 'que tenga', 'que tengas', 'excelente dia', 'excelente día']):
        if 'gracias' in t:
            return 'DESPEDIDA_CON_AGRADECIMIENTO'
        return 'DESPEDIDA'

    if any(w in t for w in ['si necesita', 'si en algun momento', 'si en algún momento', 'si requiere']):
        return 'DESPEDIDA_PUERTA_ABIERTA'

    # CALLBACK / REPROGRAMAR
    if any(w in t for w in ['llamar', 'llamo', 'marcar', 'comunicar']):
        if any(w in t for w in ['otro momento', 'mas tarde', 'más tarde', 'manana', 'mañana', 'horario']):
            return 'OFRECER_CALLBACK'
        if 'cuando' in t or 'hora' in t:
            return 'PREGUNTAR_HORARIO_CALLBACK'

    # MANEJAR RECHAZO
    if any(w in t for w in ['entiendo', 'comprendo', 'respeto']):
        if any(w in t for w in ['no hay problema', 'gracias por su tiempo', 'gracias por tu tiempo']):
            return 'ACEPTAR_RECHAZO'
        if 'ocupado' in t:
            return 'RECONOCER_OCUPADO'
        return 'ACKNOWLEDGMENT'

    # ESCUCHAR / CONFIRMAR ESCUCHA
    if any(w in t for w in ['me escucha', 'escucha?', 'adelante', 'digame', 'dígame', 'si, digame']):
        return 'CONFIRMAR_ESCUCHA'

    # ESPERAR TRANSFERENCIA
    if any(w in t for w in ['aqui estoy', 'aquí estoy', 'esperando', 'espero', 'estoy listo']):
        return 'ESPERANDO_TRANSFERENCIA'

    # MANEJAR CONFUSION
    if any(w in t for w in ['confusion', 'confusión', 'malentendido', 'disculpe']):
        return 'MANEJAR_CONFUSION'

    # RESPONDER PREGUNTA
    if any(w in t for w in ['guadalajara', 'jalisco']):
        return 'RESPONDER_UBICACION'

    if 'nioval' in t and any(w in t for w in ['es una', 'somos', 'nos dedicamos']):
        return 'RESPONDER_QUIEN_ES_NIOVAL'

    # TIMEOUT / SIN RESPUESTA
    if any(w in t for w in ['no hay respuesta', 'interferencia', 'no escucho']):
        return 'MANEJAR_TIMEOUT'

    # DEFAULT
    return 'RESPUESTA_GPT_LIBRE'


def analizar_todos_los_logs():
    """Analiza todos los archivos de logs."""
    archivos = [f for f in os.listdir(LOGS_DIR) if f.endswith('.txt')]
    print(f"Encontrados {len(archivos)} archivos de logs")

    todas_conversaciones = []
    acciones_counter = Counter()
    acciones_ejemplos = defaultdict(list)  # accion -> [(texto_bruce, texto_cliente_prev, bruce_id)]
    turnos_totales = 0

    for archivo in sorted(archivos):
        filepath = os.path.join(LOGS_DIR, archivo)
        conversaciones = extraer_conversaciones(filepath)
        todas_conversaciones.extend(conversaciones)

        for conv in conversaciones:
            texto_cliente_prev = ""
            for turno in conv['turnos']:
                if turno['quien'] == 'BRUCE':
                    accion = clasificar_accion_bruce(turno['texto'], texto_cliente_prev, conv)
                    acciones_counter[accion] += 1
                    turnos_totales += 1

                    # Guardar ejemplo (max 5 por accion)
                    if len(acciones_ejemplos[accion]) < 5:
                        acciones_ejemplos[accion].append({
                            'bruce': turno['texto'][:150],
                            'cliente_prev': texto_cliente_prev[:100],
                            'bruce_id': conv.get('bruce_id', '?'),
                        })
                else:
                    texto_cliente_prev = turno['texto']

    print(f"\nTotal conversaciones extraidas: {len(todas_conversaciones)}")
    print(f"Total turnos de Bruce analizados: {turnos_totales}")
    print(f"Total acciones unicas detectadas: {len(acciones_counter)}")

    # Ordenar por frecuencia
    print(f"\n{'='*80}")
    print(f"ACCIONES DETECTADAS (ordenadas por frecuencia)")
    print(f"{'='*80}")

    for accion, count in acciones_counter.most_common():
        pct = (count / turnos_totales * 100) if turnos_totales else 0
        print(f"\n{accion}: {count} veces ({pct:.1f}%)")
        for ej in acciones_ejemplos[accion][:2]:
            print(f"  Cliente: \"{ej['cliente_prev'][:80]}\"")
            print(f"  Bruce:   \"{ej['bruce'][:80]}\"")
            print(f"  ({ej['bruce_id']})")

    # Generar reporte JSON
    reporte = {
        'total_archivos': len(archivos),
        'total_conversaciones': len(todas_conversaciones),
        'total_turnos_bruce': turnos_totales,
        'total_acciones_unicas': len(acciones_counter),
        'acciones': [
            {
                'nombre': accion,
                'frecuencia': count,
                'porcentaje': round(count / turnos_totales * 100, 1) if turnos_totales else 0,
                'ejemplos': acciones_ejemplos[accion][:3],
            }
            for accion, count in acciones_counter.most_common()
        ]
    }

    output_path = os.path.join(os.path.dirname(LOGS_DIR), 'acciones_detectadas.json')
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(reporte, f, ensure_ascii=False, indent=2)
    print(f"\nReporte guardado en: {output_path}")

    return reporte


if __name__ == '__main__':
    analizar_todos_los_logs()
