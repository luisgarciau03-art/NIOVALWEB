#!/usr/bin/env python3
"""
Auditoria Profunda - Pipeline unificado de deteccion de bugs en produccion.

Descarga logs reales -> Parsea conversaciones -> Replay por FSM actual ->
GPT eval -> Analisis cruzado -> Reporte priorizado con FIX sugeridos.

Uso:
    python auditoria_profunda.py                         # Descarga + auditoria completa
    python auditoria_profunda.py --sin-descargar         # Solo auditar logs existentes
    python auditoria_profunda.py --gpt-eval              # Incluir GPT eval (costo ~$0.03/llamada)
    python auditoria_profunda.py --ultimas 50            # Solo ultimas N llamadas
    python auditoria_profunda.py --solo-reporte          # Solo reporte de ultima auditoria
    python auditoria_profunda.py --bruce BRUCE2600       # Auditar llamada especifica
    python auditoria_profunda.py --verbose               # Mostrar detalle de cada llamada
    python auditoria_profunda.py --exportar              # Generar reporte HTML
"""

import os
import sys
import re
import time
import json
import argparse
import glob
import requests
from datetime import datetime
from collections import Counter, defaultdict

# Windows encoding fix
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

from agente_ventas import AgenteVentas
from bug_detector import CallEventTracker, BugDetector

# ============================================================
# CONFIGURACION
# ============================================================

LOGS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'LOGS')
AUDIT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'audit_data')
SERVER_URL = "https://nioval-webhook-server-production.up.railway.app"
LAST_AUDIT_FILE = os.path.join(AUDIT_DIR, 'ultima_auditoria.json')

# Regex para parsear logs (mismos que simulador_log_replay.py)
RE_BRUCE_ID_INIT = re.compile(r'ID BRUCE generado:\s*(BRUCE\d+)')
RE_CLIENTE = re.compile(r'\[CLIENTE\]\s*(BRUCE\d+)\s*-\s*CLIENTE DIJO:\s*"(.*)"')
RE_BRUCE = re.compile(r'\[BRUCE\]\s*(BRUCE\d+)\s*DICE:\s*"(.*)"')
RE_BUG_DETECTOR = re.compile(r'\[BUG_DETECTOR\]\s*(BRUCE\d+):\s*(\d+)\s*bug')
RE_BUG_LINE = re.compile(r'\[(ALTO|MEDIO|CRITICO)\]\s*(\w+):\s*(.*)')
RE_GPT_BUG = re.compile(r'\[GPT (ALTO|MEDIO)\]\s*(GPT_\w+):\s*(.*)')
RE_NEGOCIO = re.compile(r'Negocio:\s*(.+?)(?:\s*\(|$)')
RE_TELEFONO = re.compile(r'Tel:\s*(\+?\d[\d\s]*)')
RE_DURACION = re.compile(r'Duraci[oó]n:\s*(\d+)s')
RE_ESTADO_FINAL = re.compile(r'Estado:\s*(\w+)')
RE_WHATSAPP = re.compile(r'WhatsApp:\s*(\d+)')
RE_EMAIL = re.compile(r'Email:\s*([\w\.\-]+@[\w\.\-]+)')

# Frases de despedida (para cortar replay)
FAREWELL_PHRASES = [
    'muchas gracias por su tiempo', 'que tenga excelente dia',
    'que tenga buen dia', 'hasta pronto', 'hasta luego',
]


# ============================================================
# 1. DESCARGA DE LOGS
# ============================================================

def descargar_logs_frescos():
    """Descarga logs recientes del servidor de produccion."""
    print("\n[1/5] DESCARGANDO LOGS DE PRODUCCION...")
    os.makedirs(LOGS_DIR, exist_ok=True)

    try:
        url = f"{SERVER_URL}/logs/download?lineas=5000&formato=json"
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        logs_list = data.get("logs", [])
        if not logs_list:
            print("  [WARN] Endpoint devolvio 0 logs")
            return None

        # Guardar con nombre unico
        hoy = datetime.now()
        prefijo = hoy.strftime("%d_%m")
        patron = os.path.join(LOGS_DIR, f"{prefijo}PT*.txt")
        existentes = glob.glob(patron)
        nums = []
        for a in existentes:
            m = re.search(rf'{prefijo}PT(\d+)', os.path.basename(a))
            if m:
                nums.append(int(m.group(1)))
        siguiente = (max(nums) + 1) if nums else 1
        nombre = f"{prefijo}PT{siguiente}.txt"
        filepath = os.path.join(LOGS_DIR, nombre)

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write("\n".join(logs_list))

        n_bruce = sum(1 for l in logs_list if 'ID BRUCE generado' in l)
        print(f"  [OK] {len(logs_list)} lineas -> {nombre} (~{n_bruce} llamadas)")
        return filepath

    except Exception as e:
        print(f"  [ERROR] Descarga fallida: {e}")
        return None


# ============================================================
# 2. PARSER DE LOGS
# ============================================================

def parse_log_file(filepath):
    """Parsea un archivo de log y extrae conversaciones completas."""
    conversations = {}
    current_bruce_id = None
    last_bug_bruce_id = None

    try:
        with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
            lines = f.readlines()
    except Exception as e:
        print(f"  Error leyendo {filepath}: {e}")
        return conversations

    for line in lines:
        line = line.rstrip('\n')

        m = RE_BRUCE_ID_INIT.search(line)
        if m:
            current_bruce_id = m.group(1)
            if current_bruce_id not in conversations:
                conversations[current_bruce_id] = {
                    'turns': [], 'bugs_original': [],
                    'negocio': None, 'telefono': None,
                    'duracion': None, 'estado_final': None,
                    'whatsapp': None, 'email': None,
                    'source_file': os.path.basename(filepath),
                }

        if 'DEBUG 3:' in line and 'Datos extra' in line:
            m_tel = RE_TELEFONO.search(line)
            m_neg = RE_NEGOCIO.search(line)
            if current_bruce_id and current_bruce_id in conversations:
                if m_tel:
                    conversations[current_bruce_id]['telefono'] = m_tel.group(1).replace(' ', '')
                if m_neg:
                    conversations[current_bruce_id]['negocio'] = m_neg.group(1).strip()

        m = RE_CLIENTE.search(line)
        if m:
            bruce_id, texto = m.group(1), m.group(2)
            if bruce_id in conversations and texto.strip():
                turns = conversations[bruce_id]['turns']
                if not turns or turns[-1].get('text') != texto or turns[-1].get('role') != 'cliente':
                    conversations[bruce_id]['turns'].append({'role': 'cliente', 'text': texto.strip()})

        m = RE_BRUCE.search(line)
        if m:
            bruce_id, texto = m.group(1), m.group(2)
            if bruce_id in conversations and texto.strip():
                turns = conversations[bruce_id]['turns']
                if not turns or turns[-1].get('text') != texto or turns[-1].get('role') != 'bruce':
                    conversations[bruce_id]['turns'].append({'role': 'bruce', 'text': texto.strip()})

        m = RE_BUG_DETECTOR.search(line)
        if m:
            last_bug_bruce_id = m.group(1)

        m = RE_BUG_LINE.search(line)
        if m and last_bug_bruce_id and last_bug_bruce_id in conversations:
            conversations[last_bug_bruce_id]['bugs_original'].append({
                'tipo': m.group(2), 'severidad': m.group(1),
                'detalle': m.group(3).strip(), 'source': 'rule',
            })

        m = RE_GPT_BUG.search(line)
        if m and last_bug_bruce_id and last_bug_bruce_id in conversations:
            conversations[last_bug_bruce_id]['bugs_original'].append({
                'tipo': m.group(2), 'severidad': m.group(1),
                'detalle': m.group(3).strip(), 'source': 'gpt_eval',
            })

        m = RE_DURACION.search(line)
        if m and current_bruce_id and current_bruce_id in conversations:
            conversations[current_bruce_id]['duracion'] = int(m.group(1))

        # Estado final y datos capturados
        if current_bruce_id and current_bruce_id in conversations:
            m = RE_ESTADO_FINAL.search(line)
            if m and 'Estado:' in line:
                conversations[current_bruce_id]['estado_final'] = m.group(1)
            m = RE_WHATSAPP.search(line)
            if m and 'WhatsApp:' in line:
                conversations[current_bruce_id]['whatsapp'] = m.group(1)
            m = RE_EMAIL.search(line)
            if m and 'Email:' in line:
                conversations[current_bruce_id]['email'] = m.group(1)

    return conversations


def parse_all_logs(ultimas_n=None, bruce_id=None):
    """Parsea todos los logs disponibles."""
    log_files = sorted(glob.glob(os.path.join(LOGS_DIR, '*.txt')))
    log_files = [f for f in log_files if re.match(r'\d{2}_\d{2}PT\d+\.txt', os.path.basename(f))]

    if not log_files:
        print("  [WARN] No hay archivos de log en LOGS/")
        return {}

    # Usar los mas recientes primero
    log_files = sorted(log_files, reverse=True)

    all_convs = {}
    for lf in log_files:
        convs = parse_log_file(lf)
        all_convs.update(convs)

    # Filtrar por bruce_id
    if bruce_id:
        if bruce_id in all_convs:
            all_convs = {bruce_id: all_convs[bruce_id]}
        else:
            print(f"  [WARN] {bruce_id} no encontrado en logs")
            return {}

    # Filtrar solo las que tienen conversacion real
    all_convs = {k: v for k, v in all_convs.items()
                 if len([t for t in v['turns'] if t['role'] == 'cliente']) >= 1}

    # Ordenar por BRUCE ID (numerico descendente)
    sorted_keys = sorted(all_convs.keys(),
                         key=lambda x: int(re.search(r'\d+', x).group()),
                         reverse=True)

    if ultimas_n:
        sorted_keys = sorted_keys[:ultimas_n]

    return {k: all_convs[k] for k in sorted_keys}


# ============================================================
# 3. REPLAY + DETECCION DE BUGS
# ============================================================

def replay_llamada(bruce_id, conv_data, verbose=False, gpt_eval=False):
    """Reproduce una llamada real por la pipeline actual y detecta bugs."""
    negocio = conv_data.get('negocio') or 'Desconocido'
    telefono = conv_data.get('telefono') or '0000000000'
    client_messages = [t['text'] for t in conv_data['turns'] if t['role'] == 'cliente']

    if not client_messages:
        return None

    # Crear agente
    agente = AgenteVentas(
        contacto_info={'nombre_negocio': negocio, 'telefono': telefono, 'ciudad': ''},
        sheets_manager=None, resultados_manager=None, whatsapp_validator=None,
    )

    # Crear tracker
    tracker = CallEventTracker(
        call_sid=f"AUDIT_{bruce_id}",
        bruce_id=f"A_{bruce_id}",
        telefono=telefono,
    )

    # Saludo
    try:
        saludo = agente.iniciar_conversacion()
        tracker.emit("BRUCE_RESPONDE", {"texto": saludo})
        if verbose:
            print(f"      Bruce: {saludo}")
    except Exception:
        pass

    # Replay turnos
    respuestas = []
    call_ended = False
    fsm_states = []

    for i, msg in enumerate(client_messages):
        if call_ended:
            break

        tracker.emit("CLIENTE_DICE", {"texto": msg})
        if verbose:
            print(f"      Cliente [{i+1}]: {msg}")

        try:
            respuesta = agente.procesar_respuesta(msg) or ""
        except Exception as e:
            respuesta = f"[ERROR: {e}]"

        tracker.emit("BRUCE_RESPONDE", {"texto": respuesta})
        respuestas.append(respuesta)

        if verbose:
            print(f"      Bruce [{i+1}]: {respuesta}")

        # Capturar estado FSM si disponible
        if hasattr(agente, 'fsm_engine') and agente.fsm_engine:
            fsm_states.append(str(agente.fsm_engine.state))

        if any(fp in respuesta.lower() for fp in FAREWELL_PHRASES):
            call_ended = True

    # Detectar bugs
    bugs_replay = BugDetector.analyze(tracker)

    # GPT eval
    if gpt_eval and len(tracker.respuestas_bruce) >= 2:
        try:
            from bug_detector import _evaluar_con_gpt
            gpt_bugs = _evaluar_con_gpt(tracker)
            if gpt_bugs:
                bugs_replay.extend(gpt_bugs)
        except Exception:
            pass

    # Clasificar resultado
    wapp_capturado = any('whatsapp' in r.lower() and any(c.isdigit() for c in r) for r in respuestas)
    email_capturado = any('@' in r for r in respuestas)
    contacto_capturado = wapp_capturado or email_capturado or conv_data.get('whatsapp') or conv_data.get('email')
    despedida = any(any(fp in r.lower() for fp in FAREWELL_PHRASES) for r in respuestas)

    # Determinar estado de la llamada
    if contacto_capturado and despedida:
        estado = 'EXITOSA'
    elif despedida and not contacto_capturado:
        estado = 'RECHAZO'
    elif call_ended:
        estado = 'COMPLETADA'
    else:
        estado = 'INCOMPLETA'

    return {
        'bruce_id': bruce_id,
        'negocio': negocio,
        'telefono': telefono,
        'n_turnos_cliente': len(client_messages),
        'n_respuestas': len(respuestas),
        'bugs_original': conv_data.get('bugs_original', []),
        'bugs_replay': bugs_replay,
        'estado': estado,
        'contacto': bool(contacto_capturado),
        'fsm_states': fsm_states,
        'respuestas': respuestas,
        'mensajes_cliente': client_messages,
        'source_file': conv_data.get('source_file', '?'),
    }


# ============================================================
# 3B. EVALUADOR AGRESIVO Claude Sonnet (Opcion A+B+C combinadas)
# ============================================================

_EVAL_AGRESIVO_PROMPT = """Eres un AUDITOR IMPLACABLE de calidad para llamadas de ventas telefónicas. Tu estándar de referencia es un VENDEDOR ESTRELLA humano con 15 años de experiencia en ventas B2B en México. CUALQUIER desviación de ese estándar es un problema.

Bruce es un agente AI que vende productos ferreteros de la marca NIOVAL por teléfono. Tu trabajo es encontrar CADA falla, por mínima que sea. Sé brutalmente honesto.

ESCALA DE CALIFICACIÓN (MUY ESTRICTA):
- 10: PERFECTO. Imposible mejorar. Un vendedor estrella no lo haría mejor.
- 8-9: MUY BUENO. Solo detalles menores, flujo natural y efectivo.
- 6-7: ACEPTABLE. Funciona pero tiene áreas claras de mejora.
- 4-5: DEFICIENTE. Errores notables que afectan la conversión.
- 2-3: MALO. El cliente percibe que algo está mal.
- 1: DESASTROSO. Pierde completamente al cliente.

EVALÚA en 8 DIMENSIONES:

1. NATURALIDAD (1-10): ¿Bruce suena como humano mexicano profesional o como robot?
   - Penaliza: frases idénticas entre turnos, muletillas repetidas, transiciones robóticas
   - Penaliza DURO: usar exactamente la misma estructura de frase 2+ veces
   - Un vendedor real NUNCA diría la misma frase igual dos veces

2. EFECTIVIDAD_VENTAS (1-10): ¿Bruce avanza la venta de forma estratégica?
   - Penaliza: no adaptar el pitch al tipo de negocio del cliente
   - Penaliza: no hacer preguntas para descubrir necesidades antes de ofrecer
   - Un vendedor estrella PRIMERO entiende qué necesita el cliente, LUEGO ofrece

3. MANEJO_OBJECIONES (1-10): ¿Cómo maneja rechazos, dudas o resistencia?
   - Penaliza: aceptar "no" sin intentar al menos una alternativa
   - Penaliza: insistir mecánicamente con la misma frase
   - Un vendedor estrella reencuadra objeciones como oportunidades

4. CAPTURA_DATOS (1-10): ¿Es eficiente pidiendo WhatsApp/correo/teléfono?
   - Penaliza DURO: pedir WhatsApp cuando ya le dijeron que no tiene
   - Penaliza: pedir datos sin haber generado interés primero
   - Penaliza: no confirmar el dato capturado repitiéndolo

5. CIERRE (1-10): ¿Termina la llamada de forma profesional y efectiva?
   - Penaliza: despedida genérica sin recapitular lo acordado
   - Penaliza: no confirmar acción siguiente ("le mando el catálogo ahorita")
   - Un vendedor estrella SIEMPRE confirma el siguiente paso concreto

6. ESCUCHA_ACTIVA (1-10): ¿Bruce demuestra que ESCUCHÓ lo que dijo el cliente?
   - Penaliza DURO: ignorar información que el cliente ya dio
   - Penaliza: no referenciar nada de lo que dijo el cliente en su respuesta
   - Penaliza: responder con template genérico cuando el cliente dio info específica
   - Un vendedor estrella SIEMPRE refleja lo que escuchó: "Ah, entonces ustedes manejan X..."

7. ADAPTABILIDAD (1-10): ¿Bruce se adapta al estilo/ritmo del cliente?
   - Penaliza: dar respuestas largas a un cliente que habla corto/seco
   - Penaliza: ser formal cuando el cliente es informal (o viceversa)
   - Penaliza: seguir script rígido cuando el cliente cambió de tema
   - Un vendedor estrella IGUALA el estilo del cliente

8. FLUIDEZ_CONVERSACIONAL (1-10): ¿La conversación fluye naturalmente o se siente forzada?
   - Penaliza: cambios bruscos de tema
   - Penaliza: preguntas que no conectan con lo anterior
   - Penaliza: silencios implícitos por respuestas cortas del cliente que Bruce ignora
   - Un vendedor estrella hace que cada turno fluya del anterior

DETECTA estos problemas ESPECÍFICOS (SÉ AGRESIVO, busca TODO):

A) RESPUESTA_SUBOPTIMA: Bruce respondió algo "correcto" pero había una respuesta MEJOR.
   Ejemplo: Cliente pregunta "¿qué manejan?" y Bruce da pitch genérico en vez de preguntar qué busca.
   Para cada caso, indica QUÉ DIJO Bruce y QUÉ DEBIÓ DECIR (la respuesta ideal del vendedor estrella).

B) SENTIMIENTO_NEGATIVO: El cliente se frustró, confundió o molestó durante la llamada.
   Señales: tono brusco, repetir "bueno? bueno?", respuestas cada vez más cortas, sarcasmo, colgar rápido.
   Indica el turno donde cambió el sentimiento y por qué.

C) OPORTUNIDAD_PERDIDA: El cliente mostró interés (aunque tibio) pero Bruce no lo capitalizó.
   Ejemplo: Cliente dice "ah, ¿ferretería?" (curiosidad) pero Bruce sigue con script rígido.
   BUSCA señales sutiles: preguntas del cliente, comentarios sobre su negocio, menciones de proveedores actuales.

D) FLUJO_ROBOTICO: Bruce siguió un patrón predecible (saludo→pitch→WhatsApp) sin adaptarse.
   Penaliza cuando la conversación se siente como llenar un formulario en vez de una charla de ventas.
   Un vendedor estrella NUNCA suena como si estuviera leyendo un checklist.

E) TIMING_INCORRECTO: Bruce dijo algo correcto pero en el MOMENTO equivocado.
   Ejemplo: pedir WhatsApp antes de haber generado interés, o dar el pitch cuando el cliente preguntó otra cosa.

F) FALTA_EMPATIA: Bruce no reconoció una emoción o situación del cliente.
   Ejemplo: cliente dice "estoy muy ocupado" y Bruce sigue con el pitch en vez de decir "entiendo, ¿le marco en otro momento?"

G) REDUNDANCIA: Bruce repitió información, conceptos o frases que ya dijo antes.
   Incluso si las palabras son diferentes, si el CONCEPTO es el mismo, es redundancia.

H) RESPUESTA_IDEAL: Para CADA turno de Bruce, evalúa si fue la respuesta ÓPTIMA. Si no:
   - Indica qué dijo Bruce
   - Indica qué diría el vendedor estrella
   - Esto aplica INCLUSO si Bruce "no falló" — siempre hay una respuesta mejor

TAMBIÉN detecta estos bugs TÉCNICOS conocidos del sistema (si aplican):
- PREGUNTA_REPETIDA: Bruce repite la MISMA pregunta 2+ veces
- PITCH_REPETIDO: Bruce repite el pitch/oferta de productos 2+ veces
- CATALOGO_REPETIDO: Bruce ofrece catálogo 2+ veces cuando ya lo ofreció
- LOOP: Bruce entra en un ciclo de 3+ turnos repitiendo el mismo patrón
- DATO_IGNORADO: El cliente dio un dato (nombre, WhatsApp, etc.) pero Bruce lo ignoró
- DESPEDIDA_PREMATURA: Bruce se despidió cuando el cliente aún estaba hablando/interesado
- RESPUESTA_FILLER_INCOHERENTE: Bruce respondió con algo sin sentido o desconectado
- INTERRUPCION_CONVERSACIONAL: Bruce cortó al cliente a mitad de explicación
- AREA_EQUIVOCADA: Bruce habló de productos/temas que no corresponden a NIOVAL
- TRANSFER_IGNORADA: El cliente pidió hablar con alguien más y Bruce lo ignoró

Para estos, usa el nombre del bug directamente como "tipo" (sin prefijo AUDIT_).

CONVERSACION:
{conversacion}

CONTEXTO:
- Resultado de la llamada: {estado}
- Contacto capturado: {contacto}

Responde SOLO en JSON:
{{
  "scores": {{
    "naturalidad": N,
    "efectividad_ventas": N,
    "manejo_objeciones": N,
    "captura_datos": N,
    "cierre": N,
    "escucha_activa": N,
    "adaptabilidad": N,
    "fluidez_conversacional": N
  }},
  "score_total": N,
  "problemas": [
    {{"tipo": "RESPUESTA_SUBOPTIMA|SENTIMIENTO_NEGATIVO|OPORTUNIDAD_PERDIDA|FLUJO_ROBOTICO|TIMING_INCORRECTO|FALTA_EMPATIA|REDUNDANCIA|RESPUESTA_IDEAL", "turno": N, "severidad": "CRITICO|ALTO|MEDIO", "detalle": "...", "que_dijo_bruce": "...", "que_debio_decir": "lo que diria el vendedor estrella"}}
  ],
  "patron_repetitivo": "si Bruce usa la misma estructura/frase en multiples turnos, describelo aqui",
  "sentimiento_cliente_progresion": "como evoluciono la actitud del cliente turno a turno (positivo/neutro/negativo)",
  "resumen": "2-3 frases evaluando la llamada con honestidad brutal"
}}

REGLAS ULTRA-ESTRICTAS:
- score_total = promedio de las 8 dimensiones
- BUSCA PROBLEMAS ACTIVAMENTE. Si no encuentras al menos 2, estás siendo demasiado suave
- Un score de 5 significa "mediocre". Un 7 es "aceptable". Solo un 9+ es "bueno"
- Severidad CRITICO: afecta directamente la conversión (pierde la venta o irrita al cliente)
- Severidad ALTO: el cliente lo nota y afecta su percepción de profesionalismo
- Severidad MEDIO: mejorable, un vendedor estrella no lo haría así
- Si la llamada fue REALMENTE buena (score >= 9), problemas puede tener solo MEDIOs
- Si el cliente colgó rápido (1-2 turnos), ANALIZA POR QUÉ colgó — ¿Bruce pudo evitarlo?
- Máximo 10 problemas por llamada
- Para RESPUESTA_IDEAL, evalúa CADA turno de Bruce sin excepción
- NO seas condescendiente. Imagina que tu BONO depende de encontrar TODOS los problemas
- Si Bruce suena como script/robot en CUALQUIER turno, es FLUJO_ROBOTICO
- Si Bruce no menciona NADA de lo que dijo el cliente, es FALTA de ESCUCHA_ACTIVA
- Compara CADA respuesta de Bruce con lo que diría un vendedor humano con 15 años de experiencia
- Responde SOLO el JSON, sin texto antes ni después"""


def evaluar_agresivo(resultado, verbose=False):
    """Evaluacion agresiva Claude Sonnet 4.6 con scoring + comparativa + sentimiento."""
    try:
        import anthropic
        api_key = os.environ.get("ANTHROPIC_API_KEY", "")
        if not api_key:
            return None

        # Construir texto de conversacion
        lineas = []
        turns = list(zip(resultado['mensajes_cliente'], resultado['respuestas']))
        for i, (cliente, bruce) in enumerate(turns, 1):
            lineas.append(f"CLIENTE [{i}]: {cliente}")
            lineas.append(f"BRUCE [{i}]: {bruce}")
        # Si hay mas mensajes cliente que respuestas
        if len(resultado['mensajes_cliente']) > len(resultado['respuestas']):
            for j in range(len(resultado['respuestas']), len(resultado['mensajes_cliente'])):
                lineas.append(f"CLIENTE [{j+1}]: {resultado['mensajes_cliente'][j]}")

        if len(lineas) < 2:
            return None

        conversacion_texto = "\n".join(lineas)

        prompt_content = _EVAL_AGRESIVO_PROMPT.format(
            conversacion=conversacion_texto,
            estado=resultado['estado'],
            contacto='SI' if resultado['contacto'] else 'NO',
        )

        client = anthropic.Anthropic(api_key=api_key)
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=4096,
            temperature=0,
            messages=[{
                "role": "user",
                "content": prompt_content
            }],
        )

        texto = response.content[0].text.strip()
        # Extraer JSON de markdown code blocks si aplica
        if texto.startswith("```"):
            texto = texto.split("```")[1]
            if texto.startswith("json"):
                texto = texto[4:]
        # Buscar JSON en el texto si no empieza con {
        if not texto.strip().startswith("{"):
            import re as _re
            _json_match = _re.search(r'\{[\s\S]*\}', texto)
            if _json_match:
                texto = _json_match.group(0)

        eval_data = json.loads(texto)

        if verbose:
            scores = eval_data.get('scores', {})
            total = eval_data.get('score_total', 0)
            problemas = eval_data.get('problemas', [])
            print(f"      [CLAUDE ULTRA] Score: {total:.1f}/10")
            print(f"        Nat:{scores.get('naturalidad', '?')} "
                  f"Eff:{scores.get('efectividad_ventas', '?')} "
                  f"Obj:{scores.get('manejo_objeciones', '?')} "
                  f"Cap:{scores.get('captura_datos', '?')} "
                  f"Cie:{scores.get('cierre', '?')} "
                  f"Esc:{scores.get('escucha_activa', '?')} "
                  f"Ada:{scores.get('adaptabilidad', '?')} "
                  f"Flu:{scores.get('fluidez_conversacional', '?')}")
            if eval_data.get('patron_repetitivo'):
                print(f"        [PATRON] {eval_data['patron_repetitivo'][:100]}")
            if eval_data.get('sentimiento_cliente_progresion'):
                print(f"        [SENTIMIENTO] {eval_data['sentimiento_cliente_progresion'][:100]}")
            for p in problemas:
                sev_color = "!!!" if p.get('severidad') == 'CRITICO' else "!!" if p.get('severidad') == 'ALTO' else "!"
                print(f"      {sev_color} [{p.get('severidad', '?')}] {p.get('tipo', '?')}: {p.get('detalle', '')[:90]}")
                if p.get('que_debio_decir'):
                    print(f"          -> Vendedor estrella: \"{p['que_debio_decir'][:90]}\"")
                elif p.get('sugerencia'):
                    print(f"          -> Sugerencia: {p['sugerencia'][:90]}")

        return eval_data

    except Exception as e:
        if verbose:
            print(f"      [CLAUDE ERROR] {e}")
        return None


# ============================================================
# 3C. INTEGRACION CON SISTEMA /BUGS DE PRODUCCION
# ============================================================

def reportar_bugs_a_sistema(resultado, eval_agresivo=None):
    """Reporta bugs al sistema de /bugs de produccion (recent_bugs.json)."""
    from bug_detector import _recent_bugs, _lock, _save_bugs, _ensure_bugs_loaded, _DEPLOY_VERSION

    bugs_a_reportar = []

    # 1. Bugs del replay (rule-based)
    for bug in resultado.get('bugs_replay', []):
        bugs_a_reportar.append(bug)

    # 2. Bugs del evaluador agresivo Claude Sonnet
    if eval_agresivo:
        for problema in eval_agresivo.get('problemas', []):
            # Reportar CRITICO y ALTO siempre, MEDIO si score total < 6
            score_total = eval_agresivo.get('score_total', 10)
            if problema.get('severidad') in ('CRITICO', 'ALTO') or (problema.get('severidad') == 'MEDIO' and score_total < 6):
                bugs_a_reportar.append({
                    'tipo': f"AUDIT_{problema.get('tipo', 'DESCONOCIDO')}",
                    'severidad': problema.get('severidad', 'MEDIO'),
                    'detalle': f"[turno {problema.get('turno', '?')}] {problema.get('detalle', '')}",
                    'categoria': 'auditoria_profunda',
                    'sugerencia': problema.get('que_debio_decir', problema.get('sugerencia', '')),
                    'que_dijo_bruce': problema.get('que_dijo_bruce', ''),
                })

        # 3. Score bajo global (< 6.0 con escala estricta) = bug de calidad
        score_total = eval_agresivo.get('score_total', 10)
        if score_total < 6.0:
            bugs_a_reportar.append({
                'tipo': 'AUDIT_CALIDAD_BAJA',
                'severidad': 'CRITICO' if score_total < 4.0 else 'ALTO',
                'detalle': f"Score calidad: {score_total:.1f}/10 - {eval_agresivo.get('resumen', '')}",
                'categoria': 'auditoria_profunda',
            })

        # 4. Patrón repetitivo detectado = bug
        if eval_agresivo.get('patron_repetitivo'):
            bugs_a_reportar.append({
                'tipo': 'AUDIT_PATRON_REPETITIVO',
                'severidad': 'ALTO',
                'detalle': eval_agresivo['patron_repetitivo'],
                'categoria': 'auditoria_profunda',
            })

        # 5. Dimensiones individuales < 4 = bugs específicos
        scores = eval_agresivo.get('scores', {})
        for dim, val in scores.items():
            if isinstance(val, (int, float)) and val < 4:
                bugs_a_reportar.append({
                    'tipo': f'AUDIT_DIM_{dim.upper()}_CRITICA',
                    'severidad': 'ALTO',
                    'detalle': f"Dimensión {dim} = {val}/10 (críticamente bajo)",
                    'categoria': 'auditoria_profunda',
                })

    if not bugs_a_reportar:
        return 0

    # Crear entry compatible con el dashboard /bugs
    bug_entry = {
        "bruce_id": resultado['bruce_id'],
        "telefono": resultado.get('telefono', ''),
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "deploy": f"AUDIT_{_DEPLOY_VERSION}",
        "bugs": bugs_a_reportar,
        "stats": {
            "turnos": resultado.get('n_turnos_cliente', 0),
            "duracion_s": 0,
            "source": "auditoria_profunda",
        }
    }

    # Agregar scores si hay evaluacion agresiva
    if eval_agresivo:
        bug_entry["scores"] = eval_agresivo.get('scores', {})
        bug_entry["score_total"] = eval_agresivo.get('score_total', 0)
        bug_entry["resumen"] = eval_agresivo.get('resumen', '')

    # Insertar en el sistema de bugs
    _ensure_bugs_loaded()
    with _lock:
        _recent_bugs.append(bug_entry)
        while len(_recent_bugs) > 200:
            _recent_bugs.pop(0)

    _save_bugs(force=True)
    return len(bugs_a_reportar)


# ============================================================
# 4. ANALISIS CRUZADO
# ============================================================

def analisis_cruzado(resultados):
    """Analisis de patrones entre todas las llamadas."""
    total = len(resultados)
    if total == 0:
        return {}

    # --- Metricas basicas ---
    exitosas = sum(1 for r in resultados if r['estado'] == 'EXITOSA')
    rechazos = sum(1 for r in resultados if r['estado'] == 'RECHAZO')
    con_bugs = sum(1 for r in resultados if r['bugs_replay'])
    con_bugs_orig = sum(1 for r in resultados if r['bugs_original'])

    # --- Bugs por tipo ---
    bug_counter = Counter()
    bug_severity = defaultdict(list)  # tipo -> [severidades]
    bug_examples = defaultdict(list)  # tipo -> [(bruce_id, detalle)]

    for r in resultados:
        for bug in r['bugs_replay']:
            tipo = bug['tipo']
            bug_counter[tipo] += 1
            bug_severity[tipo].append(bug.get('severidad', 'MEDIO'))
            if len(bug_examples[tipo]) < 3:
                bug_examples[tipo].append({
                    'bruce_id': r['bruce_id'],
                    'detalle': bug.get('detalle', ''),
                    'negocio': r['negocio'],
                })

    # --- Frases del cliente que causan bugs ---
    frases_problematicas = Counter()
    for r in resultados:
        if r['bugs_replay']:
            for msg in r['mensajes_cliente']:
                # Normalizar
                msg_norm = msg.lower().strip()
                if len(msg_norm) > 5:
                    frases_problematicas[msg_norm] += 1

    # --- Bugs originales vs replay ---
    bugs_originales_tipos = Counter()
    for r in resultados:
        for bug in r['bugs_original']:
            bugs_originales_tipos[bug['tipo']] += 1

    bugs_replay_tipos = Counter()
    for r in resultados:
        for bug in r['bugs_replay']:
            bugs_replay_tipos[bug['tipo']] += 1

    # --- Bugs que persisten vs arreglados ---
    bugs_arreglados = {}
    bugs_nuevos = {}
    for tipo in set(list(bugs_originales_tipos.keys()) + list(bugs_replay_tipos.keys())):
        orig = bugs_originales_tipos.get(tipo, 0)
        replay = bugs_replay_tipos.get(tipo, 0)
        if orig > 0 and replay == 0:
            bugs_arreglados[tipo] = orig
        elif orig == 0 and replay > 0:
            bugs_nuevos[tipo] = replay

    # --- Calcular score de prioridad: frecuencia x severidad ---
    SEV_WEIGHT = {'CRITICO': 10, 'ALTO': 5, 'MEDIO': 2, 'INFO': 1}
    bug_priority = {}
    for tipo, count in bug_counter.items():
        sevs = bug_severity[tipo]
        avg_sev = sum(SEV_WEIGHT.get(s, 2) for s in sevs) / len(sevs)
        bug_priority[tipo] = count * avg_sev

    # Top 10 bugs priorizados
    top_bugs = sorted(bug_priority.items(), key=lambda x: x[1], reverse=True)[:10]

    # --- Scores Claude Sonnet (si hay) ---
    scores_detail = defaultdict(list)
    for r in resultados:
        eval_data = r.get('eval_agresivo')
        if eval_data and eval_data.get('scores'):
            for dim, val in eval_data['scores'].items():
                scores_detail[dim].append(val)

    scores_promedio = {}
    for dim, vals in scores_detail.items():
        scores_promedio[dim] = sum(vals) / len(vals) if vals else 0

    # Llamadas con peor score
    peor_score = sorted(
        [r for r in resultados if r.get('eval_agresivo', {}).get('score_total')],
        key=lambda r: r['eval_agresivo']['score_total']
    )[:10]

    return {
        'total': total,
        'exitosas': exitosas,
        'rechazos': rechazos,
        'con_bugs_replay': con_bugs,
        'con_bugs_original': con_bugs_orig,
        'tasa_conversion': exitosas / total * 100 if total > 0 else 0,
        'tasa_bugs': con_bugs / total * 100 if total > 0 else 0,
        'bug_counter': dict(bug_counter),
        'bug_examples': dict(bug_examples),
        'bug_priority': dict(bug_priority),
        'top_bugs': top_bugs,
        'frases_problematicas': frases_problematicas.most_common(15),
        'bugs_arreglados': bugs_arreglados,
        'bugs_nuevos': bugs_nuevos,
        'scores_promedio': scores_promedio,
        'peor_score': peor_score,
    }


# ============================================================
# 5. REPORTE
# ============================================================

def generar_reporte(resultados, analisis, gpt_eval=False):
    """Genera reporte de auditoria en consola."""
    print("\n" + "=" * 70)
    print("  REPORTE DE AUDITORIA PROFUNDA")
    print(f"  Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"  GPT Eval: {'SI' if gpt_eval else 'NO (usar --gpt-eval para activar)'}")
    print("=" * 70)

    # --- Resumen ejecutivo ---
    print(f"\n  RESUMEN EJECUTIVO")
    print(f"  {'─' * 50}")
    print(f"  Llamadas analizadas:  {analisis['total']}")
    print(f"  Exitosas (contacto):  {analisis['exitosas']} ({analisis['tasa_conversion']:.1f}%)")
    print(f"  Rechazos:             {analisis['rechazos']}")
    print(f"  Con bugs (replay):    {analisis['con_bugs_replay']} ({analisis['tasa_bugs']:.1f}%)")
    print(f"  Con bugs (original):  {analisis['con_bugs_original']}")

    # --- Top bugs priorizados ---
    if analisis['top_bugs']:
        print(f"\n  TOP BUGS (frecuencia x severidad)")
        print(f"  {'─' * 50}")
        for i, (tipo, score) in enumerate(analisis['top_bugs'], 1):
            count = analisis['bug_counter'][tipo]
            pct = count / analisis['total'] * 100
            print(f"  {i:2d}. {tipo:<35s} {count:3d} llamadas ({pct:.1f}%)  score={score:.0f}")

            # Mostrar ejemplos
            examples = analisis['bug_examples'].get(tipo, [])
            for ex in examples[:2]:
                detalle = ex['detalle'][:80]
                print(f"      -> {ex['bruce_id']}: {detalle}")

    # --- Bugs arreglados ---
    if analisis['bugs_arreglados']:
        print(f"\n  BUGS ARREGLADOS (estaban en prod, ya no en replay)")
        print(f"  {'─' * 50}")
        for tipo, count in sorted(analisis['bugs_arreglados'].items(), key=lambda x: x[1], reverse=True):
            print(f"    [OK] {tipo}: {count} llamadas corregidas")

    # --- Bugs nuevos ---
    if analisis['bugs_nuevos']:
        print(f"\n  BUGS NUEVOS (no estaban en prod, aparecen en replay)")
        print(f"  {'─' * 50}")
        for tipo, count in sorted(analisis['bugs_nuevos'].items(), key=lambda x: x[1], reverse=True):
            print(f"    [!!] {tipo}: {count} llamadas afectadas")

    # --- Frases problematicas ---
    if analisis['frases_problematicas']:
        print(f"\n  FRASES DEL CLIENTE QUE GENERAN BUGS")
        print(f"  {'─' * 50}")
        for frase, count in analisis['frases_problematicas'][:10]:
            frase_short = frase[:60]
            print(f"    ({count}x) \"{frase_short}\"")

    # --- Scores Claude Sonnet ---
    if analisis.get('scores_promedio'):
        print(f"\n  SCORES DE CALIDAD Claude Sonnet ULTRA (promedio)")
        print(f"  {'─' * 50}")
        for dim, avg in sorted(analisis['scores_promedio'].items()):
            bar = '#' * int(avg) + '.' * (10 - int(avg))
            alerta = " <<<" if avg < 5 else ""
            print(f"    {dim:<30s} {avg:.1f}/10  [{bar}]{alerta}")

    if analisis.get('peor_score'):
        print(f"\n  LLAMADAS CON PEOR CALIDAD")
        print(f"  {'─' * 50}")
        for r in analisis['peor_score'][:5]:
            ev = r['eval_agresivo']
            score = ev['score_total']
            resumen = ev.get('resumen', '')[:60]
            print(f"    {r['bruce_id']:<12s} Score:{score:.1f}  {r['negocio'][:20]}")
            if resumen:
                print(f"      \"{resumen}\"")

    # --- Llamadas con mas bugs ---
    llamadas_con_bugs = sorted(
        [r for r in resultados if r['bugs_replay']],
        key=lambda r: len(r['bugs_replay']),
        reverse=True
    )[:10]

    if llamadas_con_bugs:
        print(f"\n  LLAMADAS CON MAS BUGS")
        print(f"  {'─' * 50}")
        for r in llamadas_con_bugs:
            bugs_str = ", ".join(b['tipo'] for b in r['bugs_replay'][:3])
            print(f"    {r['bruce_id']:<12s} {r['negocio'][:25]:<25s} {len(r['bugs_replay'])} bugs: {bugs_str}")

    print(f"\n{'=' * 70}\n")


def generar_reporte_html(resultados, analisis, gpt_eval=False):
    """Genera reporte HTML completo."""
    os.makedirs(AUDIT_DIR, exist_ok=True)
    fecha = datetime.now().strftime('%Y-%m-%d_%H%M')
    filepath = os.path.join(AUDIT_DIR, f'auditoria_{fecha}.html')

    # Construir HTML
    top_bugs_rows = ""
    for i, (tipo, score) in enumerate(analisis['top_bugs'], 1):
        count = analisis['bug_counter'][tipo]
        pct = count / analisis['total'] * 100
        examples_html = ""
        for ex in analisis['bug_examples'].get(tipo, [])[:3]:
            examples_html += f"<li><b>{ex['bruce_id']}</b>: {ex['detalle'][:100]}</li>"
        top_bugs_rows += f"""
        <tr>
            <td>{i}</td>
            <td><b>{tipo}</b></td>
            <td>{count} ({pct:.1f}%)</td>
            <td>{score:.0f}</td>
            <td><ul style="margin:0;padding-left:15px">{examples_html}</ul></td>
        </tr>"""

    llamadas_rows = ""
    for r in sorted(resultados, key=lambda x: len(x['bugs_replay']), reverse=True)[:30]:
        bugs_html = ", ".join(f"<span style='color:red'>{b['tipo']}</span>" for b in r['bugs_replay'][:3])
        if not bugs_html:
            bugs_html = "<span style='color:green'>Sin bugs</span>"
        estado_color = {'EXITOSA': 'green', 'RECHAZO': 'orange', 'COMPLETADA': 'blue', 'INCOMPLETA': 'gray'}
        color = estado_color.get(r['estado'], 'black')
        llamadas_rows += f"""
        <tr>
            <td>{r['bruce_id']}</td>
            <td>{r['negocio'][:30]}</td>
            <td>{r['n_turnos_cliente']}</td>
            <td style="color:{color}"><b>{r['estado']}</b></td>
            <td>{bugs_html}</td>
            <td>{r['source_file']}</td>
        </tr>"""

    frases_rows = ""
    for frase, count in analisis['frases_problematicas'][:15]:
        frases_rows += f"<tr><td>{count}</td><td>{frase[:80]}</td></tr>"

    html = f"""<!DOCTYPE html>
<html><head>
<meta charset="utf-8">
<title>Auditoria Profunda - {fecha}</title>
<style>
    body {{ font-family: 'Segoe UI', sans-serif; max-width: 1200px; margin: 0 auto; padding: 20px; background: #f5f5f5; }}
    h1 {{ color: #2c3e50; border-bottom: 3px solid #3498db; padding-bottom: 10px; }}
    h2 {{ color: #34495e; margin-top: 30px; }}
    .card {{ background: white; border-radius: 8px; padding: 20px; margin: 15px 0; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
    .stat {{ display: inline-block; text-align: center; padding: 15px 25px; margin: 5px; background: #ecf0f1; border-radius: 5px; }}
    .stat .num {{ font-size: 28px; font-weight: bold; color: #2c3e50; }}
    .stat .label {{ font-size: 12px; color: #7f8c8d; }}
    table {{ border-collapse: collapse; width: 100%; }}
    th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; font-size: 13px; }}
    th {{ background: #3498db; color: white; }}
    tr:nth-child(even) {{ background: #f9f9f9; }}
    .green {{ color: #27ae60; }} .red {{ color: #e74c3c; }} .orange {{ color: #f39c12; }}
</style></head><body>
<h1>Auditoria Profunda Bruce W</h1>
<p>Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M')} | GPT Eval: {'SI' if gpt_eval else 'NO'}</p>

<div class="card">
<h2>Resumen Ejecutivo</h2>
<div class="stat"><div class="num">{analisis['total']}</div><div class="label">Llamadas</div></div>
<div class="stat"><div class="num green">{analisis['exitosas']}</div><div class="label">Exitosas ({analisis['tasa_conversion']:.1f}%)</div></div>
<div class="stat"><div class="num orange">{analisis['rechazos']}</div><div class="label">Rechazos</div></div>
<div class="stat"><div class="num red">{analisis['con_bugs_replay']}</div><div class="label">Con Bugs ({analisis['tasa_bugs']:.1f}%)</div></div>
</div>

<div class="card">
<h2>Top Bugs Priorizados (frecuencia x severidad)</h2>
<table>
<tr><th>#</th><th>Bug</th><th>Frecuencia</th><th>Score</th><th>Ejemplos</th></tr>
{top_bugs_rows}
</table>
</div>

<div class="card">
<h2>Frases del Cliente que Generan Bugs</h2>
<table><tr><th>Veces</th><th>Frase</th></tr>
{frases_rows}
</table>
</div>

<div class="card">
<h2>Detalle por Llamada (top 30)</h2>
<table>
<tr><th>BRUCE ID</th><th>Negocio</th><th>Turnos</th><th>Estado</th><th>Bugs</th><th>Archivo</th></tr>
{llamadas_rows}
</table>
</div>

</body></html>"""

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(html)

    print(f"  [HTML] Reporte guardado: {filepath}")
    return filepath


def guardar_auditoria(resultados, analisis):
    """Guarda los resultados para comparacion futura."""
    os.makedirs(AUDIT_DIR, exist_ok=True)

    # Serializable
    data = {
        'fecha': datetime.now().isoformat(),
        'analisis': {
            'total': analisis['total'],
            'exitosas': analisis['exitosas'],
            'rechazos': analisis['rechazos'],
            'con_bugs_replay': analisis['con_bugs_replay'],
            'tasa_conversion': analisis['tasa_conversion'],
            'tasa_bugs': analisis['tasa_bugs'],
            'bug_counter': analisis['bug_counter'],
            'top_bugs': analisis['top_bugs'],
        },
        'llamadas_con_bugs': [
            {
                'bruce_id': r['bruce_id'],
                'negocio': r['negocio'],
                'bugs': [{'tipo': b['tipo'], 'severidad': b.get('severidad', 'MEDIO'),
                           'detalle': b.get('detalle', '')} for b in r['bugs_replay']],
            }
            for r in resultados if r['bugs_replay']
        ],
    }

    with open(LAST_AUDIT_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# ============================================================
# MAIN
# ============================================================

def main():
    parser = argparse.ArgumentParser(description='Auditoria Profunda - Pipeline unificado')
    parser.add_argument('--sin-descargar', action='store_true', help='No descargar logs nuevos')
    parser.add_argument('--gpt-eval', action='store_true', help='Incluir GPT eval mini (~$0.03/llamada)')
    parser.add_argument('--agresivo', action='store_true', help='Evaluador Claude Sonnet agresivo: scoring + comparativa + sentimiento (~$0.15/llamada)')
    parser.add_argument('--reportar-bugs', action='store_true', help='Reportar bugs al sistema /bugs de produccion')
    parser.add_argument('--ultimas', type=int, default=None, help='Solo ultimas N llamadas')
    parser.add_argument('--bruce', type=str, default=None, help='Auditar llamada especifica')
    parser.add_argument('--verbose', action='store_true', help='Mostrar detalle de cada llamada')
    parser.add_argument('--exportar', action='store_true', help='Generar reporte HTML')
    parser.add_argument('--solo-reporte', action='store_true', help='Solo mostrar ultimo reporte')
    args = parser.parse_args()

    # Solo mostrar ultimo reporte
    if args.solo_reporte:
        if os.path.exists(LAST_AUDIT_FILE):
            with open(LAST_AUDIT_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
            print(f"\n  Ultima auditoria: {data['fecha']}")
            print(f"  Llamadas: {data['analisis']['total']}")
            print(f"  Exitosas: {data['analisis']['exitosas']} ({data['analisis']['tasa_conversion']:.1f}%)")
            print(f"  Con bugs: {data['analisis']['con_bugs_replay']} ({data['analisis']['tasa_bugs']:.1f}%)")
            if data['analisis']['top_bugs']:
                print(f"\n  Top bugs:")
                for tipo, score in data['analisis']['top_bugs'][:5]:
                    count = data['analisis']['bug_counter'].get(tipo, 0)
                    print(f"    {tipo}: {count} llamadas (score={score:.0f})")
        else:
            print("  No hay auditoria previa. Ejecuta sin --solo-reporte primero.")
        return

    print("=" * 70)
    print("  AUDITORIA PROFUNDA - Pipeline Unificado")
    print("=" * 70)

    # 1. Descargar logs
    if not args.sin_descargar:
        nuevo_log = descargar_logs_frescos()

    # 2. Parsear logs
    print(f"\n[2/5] PARSEANDO LOGS...")
    conversaciones = parse_all_logs(ultimas_n=args.ultimas, bruce_id=args.bruce)
    print(f"  [OK] {len(conversaciones)} conversaciones encontradas")

    if not conversaciones:
        print("  [ERROR] No se encontraron conversaciones para auditar")
        return

    # 3. Replay + deteccion
    n_pasos = 7 if args.agresivo else 5
    print(f"\n[3/{n_pasos}] REPLAY + DETECCION DE BUGS...")
    if args.gpt_eval:
        costo_est = len(conversaciones) * 0.03
        print(f"  [GPT EVAL mini] Costo estimado: ~${costo_est:.2f} USD ({len(conversaciones)} llamadas)")
    if args.agresivo:
        costo_agr = len(conversaciones) * 0.15
        print(f"  [Claude Sonnet AGRESIVO] Costo estimado: ~${costo_agr:.2f} USD ({len(conversaciones)} llamadas)")

    resultados = []
    t0 = time.time()
    for i, (bruce_id, conv_data) in enumerate(conversaciones.items(), 1):
        client_msgs = [t['text'] for t in conv_data['turns'] if t['role'] == 'cliente']
        if not client_msgs:
            continue

        prefix = f"  [{i}/{len(conversaciones)}] {bruce_id}"
        negocio = (conv_data.get('negocio') or 'Desconocido')[:25]
        n_bugs_orig = len(conv_data.get('bugs_original', []))
        bugs_str = f" ({n_bugs_orig} bugs orig)" if n_bugs_orig else ""

        if args.verbose:
            print(f"\n{prefix} - {negocio}{bugs_str}")

        resultado = replay_llamada(bruce_id, conv_data,
                                   verbose=args.verbose, gpt_eval=args.gpt_eval)
        if resultado:
            n_replay = len(resultado['bugs_replay'])
            estado = resultado['estado']

            if not args.verbose:
                status = "OK" if n_replay == 0 else f"{n_replay} BUGS"
                sys.stdout.write(f"\r{prefix} - {negocio:<25s} [{estado}] {status}   ")
                sys.stdout.flush()

            resultados.append(resultado)

    elapsed = time.time() - t0
    print(f"\n  [OK] {len(resultados)} llamadas procesadas en {elapsed:.1f}s")

    # 3B. Evaluador agresivo Claude Sonnet (si --agresivo)
    if args.agresivo:
        print(f"\n[4/{n_pasos}] EVALUADOR AGRESIVO Claude Sonnet (scoring + comparativa + sentimiento)...")
        eval_count = 0
        eval_bugs_total = 0
        scores_all = []

        for i, resultado in enumerate(resultados, 1):
            # Solo evaluar llamadas con 2+ turnos
            if resultado['n_turnos_cliente'] < 2:
                continue

            if not args.verbose:
                sys.stdout.write(f"\r  [{i}/{len(resultados)}] {resultado['bruce_id']} - Evaluando Claude Sonnet...   ")
                sys.stdout.flush()

            eval_data = evaluar_agresivo(resultado, verbose=args.verbose)
            if eval_data:
                resultado['eval_agresivo'] = eval_data
                scores_all.append(eval_data.get('score_total', 0))
                eval_count += 1

                # Convertir problemas a bugs del replay
                for problema in eval_data.get('problemas', []):
                    resultado['bugs_replay'].append({
                        'tipo': f"AUDIT_{problema.get('tipo', 'DESCONOCIDO')}",
                        'severidad': problema.get('severidad', 'MEDIO'),
                        'detalle': f"[turno {problema.get('turno', '?')}] {problema.get('detalle', '')}",
                        'categoria': 'gpt4o_agresivo',
                    })
                    eval_bugs_total += 1

                # Reportar al sistema /bugs si se pide
                if args.reportar_bugs:
                    reportar_bugs_a_sistema(resultado, eval_data)

            # Rate limit Claude Sonnet
            time.sleep(0.3)

        avg_score = sum(scores_all) / len(scores_all) if scores_all else 0
        print(f"\n  [OK] {eval_count} llamadas evaluadas con Claude Sonnet")
        print(f"  [SCORE] Promedio calidad: {avg_score:.1f}/10")
        print(f"  [BUGS] {eval_bugs_total} problemas detectados por Claude Sonnet")

    # Reportar bugs rule-based al sistema /bugs (si --reportar-bugs y no --agresivo)
    if args.reportar_bugs and not args.agresivo:
        bugs_reportados = 0
        for resultado in resultados:
            if resultado['bugs_replay']:
                bugs_reportados += reportar_bugs_a_sistema(resultado)
        if bugs_reportados:
            print(f"  [/BUGS] {bugs_reportados} bugs reportados al sistema de produccion")

    # 4. Analisis cruzado
    print(f"\n[{5 if args.agresivo else 4}/{n_pasos}] ANALISIS CRUZADO...")
    analisis = analisis_cruzado(resultados)

    # 5. Reporte
    print(f"\n[{6 if args.agresivo else 5}/{n_pasos}] GENERANDO REPORTE...")
    generar_reporte(resultados, analisis, gpt_eval=args.gpt_eval)

    # Guardar para comparacion futura
    guardar_auditoria(resultados, analisis)

    # HTML si se pide
    if args.exportar:
        generar_reporte_html(resultados, analisis, gpt_eval=args.gpt_eval)


if __name__ == '__main__':
    main()
