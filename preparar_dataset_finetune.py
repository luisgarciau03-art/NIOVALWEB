#!/usr/bin/env python3
"""
FASE 1 - Preparacion de Dataset para Fine-tuning Bruce.

Extrae conversaciones "doradas" de los logs de Railway y las convierte
al formato JSONL requerido por la API de fine-tuning de OpenAI.

Uso:
    python preparar_dataset_finetune.py              # Procesar todos los logs
    python preparar_dataset_finetune.py --stats      # Solo estadisticas
    python preparar_dataset_finetune.py --preview 5  # Ver 5 ejemplos
    python preparar_dataset_finetune.py --output mi_dataset  # Nombre personalizado
"""

import os
import sys
import re
import json
import glob
import random
import argparse
from collections import defaultdict, Counter

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

LOGS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'LOGS')

# ============================================================
# System Prompt CORTO para fine-tuning (~200 tokens)
# El modelo aprende el resto de los ejemplos
# ============================================================

SYSTEM_PROMPT_FINETUNE = """Eres Bruce, agente de ventas telefónicas de NIOVAL, marca distribuidora de productos ferreteros en México (cintas tapagoteras, grifería, herramientas, candados, impermeabilizantes).

OBJETIVO: Capturar WhatsApp o correo del encargado de compras para enviar catálogo con lista de precios.

REGLAS ESENCIALES:
- Siempre habla de USTED, nunca de tú
- Nunca uses "jefe", "patrón", "chamba", "chido" - usa lenguaje profesional
- Si el encargado no está: pide WhatsApp o correo para dejarle información
- Si ya te dieron un dato (WhatsApp, correo, nombre): NO lo pidas de nuevo, confirma y despídete
- Si el cliente rechaza: respeta su decisión, despídete cordialmente sin insistir
- Si hay transferencia: espera en silencio a que conteste la nueva persona
- Responde preguntas directas del cliente antes de continuar con tu objetivo
- Máximo 2 oraciones por respuesta, sé conciso""".strip()

# ============================================================
# Regex (igual que simulador_log_replay.py)
# ============================================================

RE_BRUCE_ID_INIT = re.compile(r'ID BRUCE generado:\s*(BRUCE\d+)')
RE_CLIENTE = re.compile(r'\[CLIENTE\]\s*(BRUCE\d+)\s*-\s*CLIENTE DIJO:\s*"(.*)"')
RE_BRUCE = re.compile(r'\[BRUCE\]\s*(BRUCE\d+)\s*DICE:\s*"(.*)"')
RE_BUG_DETECTOR = re.compile(r'\[BUG_DETECTOR\]\s*(BRUCE\d+):\s*(\d+)\s*bug')
RE_BUG_LINE = re.compile(r'\[(ALTO|MEDIO|CRITICO)\]\s*(\w+):\s*(.*)')
RE_GPT_BUG = re.compile(r'\[GPT (ALTO|MEDIO)\]\s*(GPT_\w+):\s*(.*)')
RE_NEGOCIO = re.compile(r'Negocio:\s*(.+?)(?:\s*\(|$)')
RE_TELEFONO = re.compile(r'Tel:\s*(\+?\d[\d\s]*)')
RE_DURACION = re.compile(r'Duraci[oó]n:\s*(\d+)s')
RE_WHATSAPP_SYNCED = re.compile(r'WhatsApp synced:\s*(\d+)')
RE_EMAIL_SYNCED = re.compile(r'[Ee]mail synced:\s*(\S+@\S+)')

# Palabras informales que NO deben aparecer en respuestas de Bruce
INFORMAL_WORDS = ['jefe', 'patrón', 'patron', 'chamba', 'chido', 'neta', 'órale',
                  'orale', 'al cien', 'cuate', 'carnal', 'mano ', ' tú ', 'te digo',
                  'te mando', 'te envío', 'te llamo']

# ============================================================
# Parser de logs
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
        return conversations

    for line in lines:
        line = line.rstrip('\n')

        m = RE_BRUCE_ID_INIT.search(line)
        if m:
            current_bruce_id = m.group(1)
            if current_bruce_id not in conversations:
                conversations[current_bruce_id] = {
                    'turns': [],
                    'bugs': [],
                    'negocio': None,
                    'whatsapp_capturado': None,
                    'email_capturado': None,
                    'duracion': None,
                    'source_file': os.path.basename(filepath),
                }

        # Datos de negocio
        if 'DEBUG 3:' in line and 'Datos extra' in line:
            m_neg = RE_NEGOCIO.search(line)
            if current_bruce_id and current_bruce_id in conversations and m_neg:
                conversations[current_bruce_id]['negocio'] = m_neg.group(1).strip()

        # WhatsApp capturado
        m = RE_WHATSAPP_SYNCED.search(line)
        if m and current_bruce_id and current_bruce_id in conversations:
            conversations[current_bruce_id]['whatsapp_capturado'] = m.group(1)

        # Email capturado
        m = RE_EMAIL_SYNCED.search(line)
        if m and current_bruce_id and current_bruce_id in conversations:
            conversations[current_bruce_id]['email_capturado'] = m.group(1)

        # Cliente dice
        m = RE_CLIENTE.search(line)
        if m:
            bruce_id, texto = m.group(1), m.group(2)
            if bruce_id in conversations and texto.strip():
                turns = conversations[bruce_id]['turns']
                if not turns or turns[-1].get('text') != texto or turns[-1].get('role') != 'cliente':
                    conversations[bruce_id]['turns'].append({'role': 'cliente', 'text': texto.strip()})

        # Bruce dice
        m = RE_BRUCE.search(line)
        if m:
            bruce_id, texto = m.group(1), m.group(2)
            if bruce_id in conversations and texto.strip():
                turns = conversations[bruce_id]['turns']
                if not turns or turns[-1].get('text') != texto or turns[-1].get('role') != 'bruce':
                    conversations[bruce_id]['turns'].append({'role': 'bruce', 'text': texto.strip()})

        # Bug Detector header
        m = RE_BUG_DETECTOR.search(line)
        if m:
            last_bug_bruce_id = m.group(1)

        # Bug rule-based
        m = RE_BUG_LINE.search(line)
        if m and last_bug_bruce_id and last_bug_bruce_id in conversations:
            conversations[last_bug_bruce_id]['bugs'].append({
                'tipo': m.group(2), 'severidad': m.group(1), 'source': 'rule'
            })

        # Bug GPT eval
        m = RE_GPT_BUG.search(line)
        if m and last_bug_bruce_id and last_bug_bruce_id in conversations:
            conversations[last_bug_bruce_id]['bugs'].append({
                'tipo': m.group(2), 'severidad': m.group(1), 'source': 'gpt'
            })

        # Duracion
        m = RE_DURACION.search(line)
        if m and current_bruce_id and current_bruce_id in conversations:
            conversations[current_bruce_id]['duracion'] = int(m.group(1))

    return conversations


def parse_all_logs():
    """Parsea todos los archivos de log en LOGS/."""
    log_files = sorted(glob.glob(os.path.join(LOGS_DIR, '*.txt')))
    log_files = [f for f in log_files if re.match(r'\d{2}_\d{2}PT\d+\.txt', os.path.basename(f))]

    if not log_files:
        print(f"  [!] No se encontraron logs en {LOGS_DIR}")
        print(f"      Descarga los logs primero con: python auto_descarga_logs.py")
        return {}

    all_convs = {}
    print(f"  Parseando {len(log_files)} archivos de log...")
    for lf in log_files:
        convs = parse_log_file(lf)
        all_convs.update(convs)

    return all_convs


# ============================================================
# Filtros de calidad (llamadas "doradas")
# ============================================================

def detectar_outcome(conv):
    """
    Detecta el outcome de la conversacion.
    Retorna: 'contacto_capturado' | 'rechazo_correcto' | 'encargado_ausente' |
             'transfer_correcto' | 'incompleto'
    """
    import re as _re
    _RE_EMAIL = _re.compile(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}')
    _RE_PHONE = _re.compile(r'\b\d[\d\s]{8,14}\d\b')

    # Contacto capturado directamente (Railway logs con tracking)
    if conv.get('whatsapp_capturado') or conv.get('email_capturado'):
        return 'contacto_capturado'

    # Analizar ultimas respuestas de Bruce
    bruce_turns = [t['text'].lower() for t in conv['turns'] if t['role'] == 'bruce']
    if not bruce_turns:
        return 'incompleto'

    ultima = bruce_turns[-1] if bruce_turns else ''
    bruce_text_completo = ' '.join(bruce_turns)

    # Buscar si cliente dio email/telefono y Bruce confirmo (sinteticos Claude)
    cliente_turns_raw = [t['text'] for t in conv['turns'] if t['role'] == 'cliente']
    cliente_text = ' '.join(cliente_turns_raw)
    if (_RE_EMAIL.search(cliente_text) or _RE_PHONE.search(cliente_text)):
        if any(p in bruce_text_completo for p in [
            'ya tengo', 'ya lo tengo', 'perfecto', 'le envio el catalogo',
            'le mando', 'registrado', 'anotado', 'muchas gracias',
            'le hare llegar', 'recibido'
        ]):
            return 'contacto_capturado'

    # Despedida correcta
    despedida = any(p in ultima for p in [
        'gracias por su tiempo', 'que tenga', 'buen dia', 'buenas tardes',
        'fue un gusto', 'hasta luego', 'muchas gracias', 'con gusto le llamamos',
        'le dejo mis datos', 'perfecto, ya tengo', 'le envio el catalogo',
        'hasta pronto', 'con mucho gusto'
    ])

    # Frases de rechazo bien manejado
    cliente_turns_lower = [t['text'].lower() for t in conv['turns'] if t['role'] == 'cliente']
    cliente_rechaza = any(any(p in ct for p in [
        'no me interesa', 'no gracias', 'ya tengo proveedor', 'estamos surtidos',
        'no necesito', 'no quiero', 'llamen mas tarde', 'vuelvan a llamar'
    ]) for ct in cliente_turns_lower)

    if cliente_rechaza and despedida:
        return 'rechazo_correcto'

    # Encargado ausente + Bruce pidio contacto alternativo
    encargado_ausente = any(any(p in ct for p in [
        'no esta', 'no se encuentra', 'salio', 'no hay encargado'
    ]) for ct in cliente_turns_lower)

    bruce_pidio_contacto = any(any(p in bt for p in [
        'whatsapp', 'correo', 'telefono', 'numero'
    ]) for bt in bruce_turns)

    if encargado_ausente and bruce_pidio_contacto and despedida:
        return 'encargado_ausente'

    # Transfer
    transfer_detectada = any(any(p in ct for p in [
        'le paso', 'le comunico', 'un momento'
    ]) for ct in cliente_turns_lower)

    if transfer_detectada and despedida:
        return 'transfer_correcto'

    return 'incompleto'


def tiene_lenguaje_informal(conv):
    """Verifica si Bruce uso lenguaje informal en alguna respuesta."""
    for t in conv['turns']:
        if t['role'] == 'bruce':
            texto = t['text'].lower()
            if any(w in texto for w in INFORMAL_WORDS):
                return True
    return False


def tiene_pregunta_repetida(conv):
    """Detecta si Bruce hizo la misma pregunta 2 veces."""
    bruce_turns = [t['text'].lower() for t in conv['turns'] if t['role'] == 'bruce']
    preguntas = [t for t in bruce_turns if '?' in t]

    _KEY_PATTERNS = [
        r'encargado de compras',
        r'whatsapp',
        r'correo electr[oó]nico',
        r'su nombre',
        r'a qu[eé] hora',
    ]
    for pat in _KEY_PATTERNS:
        matches = [t for t in preguntas if re.search(pat, t)]
        if len(matches) >= 2:
            return True
    return False


def es_llamada_dorada(bruce_id, conv):
    """
    Evalua si una conversacion es "dorada" para fine-tuning.
    Retorna (es_dorada: bool, razon: str, outcome: str)
    """
    turns = conv.get('turns', [])
    cliente_turns = [t for t in turns if t['role'] == 'cliente']
    bruce_turns = [t for t in turns if t['role'] == 'bruce']

    # Filtro 1: Minimo de turnos
    if len(cliente_turns) < 2 or len(bruce_turns) < 2:
        return False, 'muy_corta', 'incompleto'

    # Filtro 2: Sin bugs detectados (rule-based - los GPT pueden ser FP)
    rule_bugs = [b for b in conv.get('bugs', []) if b['source'] == 'rule']
    if rule_bugs:
        tipos = [b['tipo'] for b in rule_bugs]
        return False, f'bugs_rule:{",".join(tipos)}', 'incompleto'

    # Filtro 3: Sin bugs ALTO de GPT eval
    gpt_alto_bugs = [b for b in conv.get('bugs', [])
                     if b['source'] == 'gpt' and b['severidad'] == 'ALTO']
    if gpt_alto_bugs:
        tipos = [b['tipo'] for b in gpt_alto_bugs]
        return False, f'bugs_gpt_alto:{",".join(tipos)}', 'incompleto'

    # Filtro 4: Sin lenguaje informal
    if tiene_lenguaje_informal(conv):
        return False, 'lenguaje_informal', 'incompleto'

    # Filtro 5: Sin pregunta repetida (doble check manual)
    if tiene_pregunta_repetida(conv):
        return False, 'pregunta_repetida', 'incompleto'

    # Filtro 6: Outcome claro
    outcome = detectar_outcome(conv)
    if outcome == 'incompleto':
        return False, 'sin_outcome_claro', 'incompleto'

    return True, 'OK', outcome


# ============================================================
# Formateador JSONL para OpenAI fine-tuning
# ============================================================

def conv_to_jsonl(conv, system_prompt):
    """
    Convierte una conversacion al formato JSONL de OpenAI fine-tuning.

    Formato multi-turn:
    {"messages": [
        {"role": "system", "content": "..."},
        {"role": "user", "content": "cliente msg 1"},
        {"role": "assistant", "content": "bruce msg 1"},
        {"role": "user", "content": "cliente msg 2"},
        {"role": "assistant", "content": "bruce msg 2"},
        ...
    ]}
    """
    messages = [{"role": "system", "content": system_prompt}]

    # Agregar saludo inicial de Bruce si el primer turno es de bruce
    turns = conv['turns']

    # Normalizar: conversacion debe comenzar con user (cliente)
    # Si Bruce saluda primero, lo ponemos como primer assistant message
    # precedido de un user message dummy de "inicio de llamada"
    if turns and turns[0]['role'] == 'bruce':
        messages.append({"role": "user", "content": "[llamada entrante]"})
        messages.append({"role": "assistant", "content": turns[0]['text']})
        turns = turns[1:]

    for t in turns:
        role = "user" if t['role'] == 'cliente' else "assistant"
        messages.append({"role": role, "content": t['text']})

    # Validar que termina con assistant (Bruce)
    if messages and messages[-1]['role'] != 'assistant':
        return None  # Descarta conversaciones que terminan con el cliente

    # Validar alternancia correcta (no dos user/assistant consecutivos del mismo tipo)
    for i in range(1, len(messages)):
        if messages[i]['role'] == messages[i-1]['role'] and messages[i]['role'] != 'system':
            return None

    return {"messages": messages}


# ============================================================
# Pipeline principal
# ============================================================

def generar_sinteticos():
    """
    Genera conversaciones sinteticas perfectas usando el simulador masivo.
    Retorna lista de ejemplos en formato JSONL-ready.
    """
    print("  Generando conversaciones sinteticas con simulador...")

    # Importar simulador
    try:
        from simulador_masivo import SCENARIOS, ejecutar_escenario
    except ImportError:
        print("  [!] No se pudo importar simulador_masivo")
        return []

    from agente_ventas import AgenteVentas
    from bug_detector import CallEventTracker

    ejemplos = []
    agente = AgenteVentas()

    import uuid
    for scenario in SCENARIOS:
        try:
            _sid = f"SIM_{uuid.uuid4().hex[:8]}"
            _bid = f"SIM_{scenario.get('id', uuid.uuid4().hex[:4])}"
            tracker = CallEventTracker(call_sid=_sid, bruce_id=_bid)
            tracker.simulador_texto = True

            client_msgs = scenario.get('messages', [])
            if len(client_msgs) < 2:
                continue

            turns = []

            # Saludo inicial
            saludo = agente.iniciar_conversacion()
            if saludo:
                turns.append({'role': 'bruce', 'text': saludo})

            for msg in client_msgs:
                turns.append({'role': 'cliente', 'text': msg})
                tracker.registrar_turno_cliente(msg)
                respuesta = agente.procesar_respuesta(msg, tracker)
                if respuesta:
                    turns.append({'role': 'bruce', 'text': respuesta})
                    tracker.registrar_respuesta_bruce(respuesta)

            # Verificar 0 bugs
            from bug_detector import BugDetector
            bugs = BugDetector.analyze(tracker)
            rule_bugs = [b for b in bugs if 'GPT' not in b.get('tipo', '')]
            if rule_bugs:
                continue

            if len(turns) < 4:
                continue

            conv_fake = {
                'turns': turns,
                'bugs': [],
                'whatsapp_capturado': None,
                'email_capturado': None,
            }

            outcome = detectar_outcome(conv_fake)

            ejemplo = conv_to_jsonl(conv_fake, SYSTEM_PROMPT_FINETUNE)
            if ejemplo:
                ejemplo['_meta'] = {
                    'bruce_id': f"SIM_{scenario.get('id', '?')}",
                    'outcome': outcome if outcome != 'incompleto' else scenario.get('category', 'sintetico'),
                    'negocio': scenario.get('description', 'Sintetico'),
                    'n_turns': len(turns),
                    'sintetico': True,
                }
                ejemplos.append(ejemplo)

        except Exception as e:
            continue

    print(f"  Sinteticos generados: {len(ejemplos)}")
    return ejemplos


def generar_dataset(output_prefix='bruce_finetune', preview_n=0, stats_only=False, incluir_sinteticos=True):
    """Pipeline completo de generacion de dataset."""

    print("=" * 65)
    print("  FASE 1 - Preparacion Dataset Fine-tuning Bruce")
    print("=" * 65)

    # Paso 1: Parsear logs
    print("\n[1/5] Parseando logs de Railway...")
    all_convs = parse_all_logs()

    if not all_convs:
        print("  [ERROR] No hay conversaciones. Descarga logs primero.")
        print("  Ejecuta: python auto_descarga_logs.py --horas 720")
        return

    print(f"  Conversaciones totales: {len(all_convs)}")

    # Paso 2: Filtrar llamadas doradas
    print("\n[2/5] Filtrando llamadas doradas...")
    doradas = {}
    rechazadas = Counter()
    outcomes = Counter()

    for bruce_id, conv in all_convs.items():
        es_dorada, razon, outcome = es_llamada_dorada(bruce_id, conv)
        if es_dorada:
            doradas[bruce_id] = conv
            doradas[bruce_id]['_outcome'] = outcome
            outcomes[outcome] += 1
        else:
            razon_base = razon.split(':')[0]
            rechazadas[razon_base] += 1

    print(f"  Doradas: {len(doradas)} / {len(all_convs)} ({100*len(doradas)/max(len(all_convs),1):.1f}%)")
    print(f"\n  Por outcome:")
    for outcome, count in outcomes.most_common():
        print(f"    {outcome}: {count}")
    print(f"\n  Rechazadas por:")
    for razon, count in rechazadas.most_common():
        print(f"    {razon}: {count}")

    if stats_only:
        return

    # Paso 3: Convertir reales a JSONL + agregar sinteticos
    print(f"\n[3/5] Convirtiendo conversaciones a formato OpenAI JSONL...")
    ejemplos_validos = []
    errores_formato = 0

    for bruce_id, conv in doradas.items():
        ejemplo = conv_to_jsonl(conv, SYSTEM_PROMPT_FINETUNE)
        if ejemplo:
            ejemplo['_meta'] = {
                'bruce_id': bruce_id,
                'outcome': conv.get('_outcome'),
                'negocio': conv.get('negocio'),
                'n_turns': len(conv['turns']),
                'sintetico': False,
            }
            ejemplos_validos.append(ejemplo)
        else:
            errores_formato += 1

    # Complementar con sinteticos
    if incluir_sinteticos:
        print(f"  Generando datos sinteticos del simulador para complementar...")
        sinteticos_sim = generar_sinteticos()
        ejemplos_validos.extend(sinteticos_sim)

        # Cargar sinteticos de Claude si existen
        claude_file = "bruce_sinteticos_claude.jsonl"
        sinteticos_claude = []
        if os.path.exists(claude_file):
            print(f"  Cargando sinteticos de Claude: {claude_file}")
            with open(claude_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            obj = json.loads(line)
                            obj['_meta'] = {'outcome': 'sintetico_claude', 'sintetico': True}
                            sinteticos_claude.append(obj)
                        except Exception:
                            pass
            ejemplos_validos.extend(sinteticos_claude)
            print(f"  Sinteticos Claude cargados: {len(sinteticos_claude)}")

        print(f"  Reales: {len(doradas)} | Sim: {len(sinteticos_sim)} | "
              f"Claude: {len(sinteticos_claude)} | Total: {len(ejemplos_validos)}")
    else:
        print(f"  Validos: {len(ejemplos_validos)} | Errores formato: {errores_formato}")

    if len(ejemplos_validos) < 10:
        print(f"\n  [!] Solo {len(ejemplos_validos)} ejemplos totales. Descarga mas logs.")
        print(f"      python auto_descarga_logs.py --horas 2160")
        return

    # Paso 4: Balancear por outcome y dividir train/validation
    print(f"\n[4/5] Balanceando dataset y dividiendo train/validation...")

    # Balancear: max 120 por outcome para evitar sesgo
    MAX_POR_OUTCOME = 120
    balanceados = []
    por_outcome = defaultdict(list)

    for ej in ejemplos_validos:
        outcome = ej.get('_meta', {}).get('outcome', 'unknown')
        por_outcome[outcome].append(ej)

    for outcome, lista in por_outcome.items():
        random.shuffle(lista)
        seleccionados = lista[:MAX_POR_OUTCOME]
        balanceados.extend(seleccionados)
        print(f"    {outcome}: {len(seleccionados)} (de {len(lista)} disponibles)")

    random.shuffle(balanceados)

    # Split 90/10 train/validation
    n_val = max(10, int(len(balanceados) * 0.10))
    n_train = len(balanceados) - n_val

    train_data = balanceados[:n_train]
    val_data = balanceados[n_val:]

    print(f"\n  Total: {len(balanceados)} | Train: {n_train} | Validation: {n_val}")

    # Preview
    if preview_n > 0:
        print(f"\n[PREVIEW] Primeros {preview_n} ejemplos:")
        for i, ej in enumerate(balanceados[:preview_n]):
            meta = ej.get('_meta', {})
            msgs = ej['messages']
            print(f"\n  --- Ejemplo {i+1} [{meta.get('outcome')}] {meta.get('bruce_id')} ---")
            for m in msgs[:6]:  # Primeros 3 pares
                role_label = "SYS" if m['role'] == 'system' else ("CLI" if m['role'] == 'user' else "BRUCE")
                content = m['content'][:80] + '...' if len(m['content']) > 80 else m['content']
                print(f"    [{role_label}] {content}")
            if len(msgs) > 6:
                print(f"    ... ({len(msgs)-6} mensajes mas)")

    # Paso 5: Guardar archivos
    print(f"\n[5/5] Guardando archivos JSONL...")

    def save_jsonl(data, path):
        """Guarda sin el campo _meta (no requerido por OpenAI)."""
        with open(path, 'w', encoding='utf-8') as f:
            for item in data:
                clean = {k: v for k, v in item.items() if k != '_meta'}
                f.write(json.dumps(clean, ensure_ascii=False) + '\n')

    train_path = f"{output_prefix}_train.jsonl"
    val_path = f"{output_prefix}_validation.jsonl"
    meta_path = f"{output_prefix}_meta.json"

    save_jsonl(train_data, train_path)
    save_jsonl(val_data, val_path)

    # Guardar metadata para referencia
    meta = {
        'total_conversaciones': len(all_convs),
        'doradas': len(doradas),
        'train': n_train,
        'validation': n_val,
        'outcomes': dict(outcomes),
        'system_prompt_tokens_aprox': len(SYSTEM_PROMPT_FINETUNE.split()),
        'system_prompt_preview': SYSTEM_PROMPT_FINETUNE[:200],
        'archivos': {
            'train': train_path,
            'validation': val_path,
        }
    }
    with open(meta_path, 'w', encoding='utf-8') as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    # Calcular tokens aproximados
    total_chars = sum(
        sum(len(m['content']) for m in ej['messages'])
        for ej in train_data
    )
    tokens_aprox = total_chars // 4  # ~4 chars/token

    print(f"\n  Archivos generados:")
    print(f"    {train_path}  ({n_train} ejemplos)")
    print(f"    {val_path} ({n_val} ejemplos)")
    print(f"    {meta_path}")
    print(f"\n  Tokens aprox. en training: ~{tokens_aprox:,}")
    print(f"  Costo estimado fine-tuning: ~${tokens_aprox * 0.000008:.2f} USD")
    print(f"  (gpt-4.1-mini: $8.00/1M tokens de entrenamiento)")

    print("\n" + "=" * 65)
    print("  FASE 1 COMPLETA")
    print("=" * 65)
    print(f"\n  Siguiente paso (Fase 2):")
    print(f"    python submit_finetune.py --train {train_path} --val {val_path}")

    return train_path, val_path


# ============================================================
# CLI
# ============================================================

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Preparar dataset para fine-tuning Bruce')
    parser.add_argument('--output', default='bruce_finetune', help='Prefijo para archivos de salida')
    parser.add_argument('--stats', action='store_true', help='Solo mostrar estadisticas sin generar archivos')
    parser.add_argument('--preview', type=int, default=0, metavar='N', help='Mostrar N ejemplos de preview')
    parser.add_argument('--seed', type=int, default=42, help='Semilla aleatoria para reproducibilidad')
    parser.add_argument('--no-sinteticos', action='store_true', help='No agregar datos sinteticos del simulador')
    args = parser.parse_args()

    random.seed(args.seed)

    generar_dataset(
        output_prefix=args.output,
        preview_n=args.preview,
        stats_only=args.stats,
        incluir_sinteticos=not args.no_sinteticos,
    )
