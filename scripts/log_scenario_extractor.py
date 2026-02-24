"""
Log Scenario Extractor: Parsea logs de producción y genera bases de datos
para testing automatizado.

Extiende scripts/log_parser.py con extracción de:
- Bugs detectados por BugDetector ([BUG_DETECTOR], [ALTO], [MEDIO])
- Transiciones FSM ([FSM PHASE2], [FSM SHADOW])
- Calificación Bruce, conclusión, duración
- Tags automáticos (happy_path, bug_detected, rechazo, etc.)

Uso:
    python scripts/log_scenario_extractor.py                    # Genera scenario_db.json
    python scripts/log_scenario_extractor.py --bug-catalog      # Genera bug_regression_catalog.json
    python scripts/log_scenario_extractor.py --stats             # Solo estadísticas
"""

import os
import re
import json
import glob
import argparse
from collections import defaultdict
from datetime import datetime

# Directorio del proyecto
PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOGS_DIR = os.path.join(PROJECT_DIR, 'LOGS')
OUTPUT_DIR = os.path.join(PROJECT_DIR, 'tests', 'test_data')


# ============================================================
# REGEX PATTERNS
# ============================================================

RE_BRUCE_ID_INIT = re.compile(r'ID BRUCE generado:\s*(BRUCE\d+)')
RE_CLIENTE = re.compile(
    r'\[CLIENTE\]\s*(BRUCE\d+)\s*-\s*CLIENTE DIJO:\s*"(.*)"'
)
RE_BRUCE = re.compile(
    r'\[BRUCE\]\s*(BRUCE\d+)\s*DICE:\s*"(.*)"'
)
RE_FSM_TRANSITION = re.compile(
    r'\[FSM (?:SHADOW|PHASE\d+)\] state=(\w+) intent=(\w+) → next=(\w+)'
)
RE_BUG_DETECTOR = re.compile(
    r'\[BUG_DETECTOR\]\s*(BRUCE\d+):\s*(\d+)\s*bug'
)
RE_BUG_LINE = re.compile(
    r'\[(?:ALTO|MEDIO|CRITICO)\]\s*(\w+):\s*(.*)'
)
RE_GPT_BUG = re.compile(
    r'\[GPT (?:ALTO|MEDIO)\]\s*(GPT_\w+):\s*(.*)'
)
RE_CALIFICACION = re.compile(r'Calificaci[oó]n Bruce:\s*(\d+)/10')
RE_CONCLUSION = re.compile(r'Conclusi[oó]n determinada:\s*(.+)')
RE_DURACION = re.compile(r'Duraci[oó]n de la llamada:\s*(\d+)\s*(?:s|segundos)')
RE_NEGOCIO = re.compile(r'Negocio:\s*(.+?)(?:\s*$)')
RE_LLAMADA_TERMINADA = re.compile(r'LLAMADA TERMINADA|DESPEDIDA FINAL|STATUS CALLBACK')


def parse_file_extended(filepath):
    """Parsea un archivo de log con datos extendidos.

    Returns:
        dict: {bruce_id: {turns, bugs, fsm_transitions, calificacion, ...}}
    """
    conversations = {}
    current_bruce_id = None
    # Track which bruce_id the bug lines belong to
    last_bug_bruce_id = None

    try:
        with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
            lines = f.readlines()
    except Exception as e:
        print(f"  Error leyendo {filepath}: {e}")
        return conversations

    for line in lines:
        line = line.rstrip('\n')

        # --- BRUCE ID generado ---
        m = RE_BRUCE_ID_INIT.search(line)
        if m:
            current_bruce_id = m.group(1)
            if current_bruce_id not in conversations:
                conversations[current_bruce_id] = {
                    'turns': [],
                    'bugs': [],
                    'fsm_transitions': [],
                    'patterns_detected': [],
                    'calificacion': None,
                    'conclusion': None,
                    'duracion': None,
                    'negocio': None,
                    'source_file': os.path.basename(filepath),
                }

        # --- Cliente dice ---
        m = RE_CLIENTE.search(line)
        if m:
            bruce_id, texto = m.group(1), m.group(2)
            if bruce_id in conversations and texto.strip():
                turns = conversations[bruce_id]['turns']
                if not turns or turns[-1].get('text') != texto or turns[-1].get('role') != 'client':
                    conversations[bruce_id]['turns'].append({
                        'role': 'client',
                        'text': texto,
                    })

        # --- Bruce dice ---
        m = RE_BRUCE.search(line)
        if m:
            bruce_id, texto = m.group(1), m.group(2)
            if bruce_id in conversations and texto.strip():
                turns = conversations[bruce_id]['turns']
                if not turns or turns[-1].get('text') != texto or turns[-1].get('role') != 'bruce':
                    conversations[bruce_id]['turns'].append({
                        'role': 'bruce',
                        'text': texto,
                    })

        # --- FSM Transitions ---
        m = RE_FSM_TRANSITION.search(line)
        if m and current_bruce_id and current_bruce_id in conversations:
            conversations[current_bruce_id]['fsm_transitions'].append({
                'from': m.group(1),
                'intent': m.group(2),
                'to': m.group(3),
            })

        # --- Bug Detector header ---
        m = RE_BUG_DETECTOR.search(line)
        if m:
            last_bug_bruce_id = m.group(1)

        # --- Bug line (rule-based) ---
        m = RE_BUG_LINE.search(line)
        if m and last_bug_bruce_id and last_bug_bruce_id in conversations:
            bug_type, detail = m.group(1), m.group(2).strip()
            conversations[last_bug_bruce_id]['bugs'].append({
                'tipo': bug_type,
                'detalle': detail,
                'source': 'rule',
            })

        # --- GPT eval bug ---
        m = RE_GPT_BUG.search(line)
        if m and last_bug_bruce_id and last_bug_bruce_id in conversations:
            bug_type, detail = m.group(1), m.group(2).strip()
            conversations[last_bug_bruce_id]['bugs'].append({
                'tipo': bug_type,
                'detalle': detail,
                'source': 'gpt_eval',
            })

        # --- Pattern detected ---
        m_pat = re.search(r'PATR[OÓ]N DETECTADO\s*\((\w+)\)', line)
        if m_pat and current_bruce_id and current_bruce_id in conversations:
            conversations[current_bruce_id]['patterns_detected'].append(m_pat.group(1))

        # --- Calificación ---
        m = RE_CALIFICACION.search(line)
        if m and current_bruce_id and current_bruce_id in conversations:
            conversations[current_bruce_id]['calificacion'] = int(m.group(1))

        # --- Conclusión ---
        m = RE_CONCLUSION.search(line)
        if m and current_bruce_id and current_bruce_id in conversations:
            conversations[current_bruce_id]['conclusion'] = m.group(1).strip()

        # --- Duración ---
        m = RE_DURACION.search(line)
        if m and current_bruce_id and current_bruce_id in conversations:
            conversations[current_bruce_id]['duracion'] = int(m.group(1))

        # --- Negocio ---
        m = RE_NEGOCIO.search(line)
        if m and current_bruce_id and current_bruce_id in conversations:
            if not conversations[current_bruce_id]['negocio']:
                conversations[current_bruce_id]['negocio'] = m.group(1).strip()

        # --- Llamada terminada ---
        if RE_LLAMADA_TERMINADA.search(line):
            current_bruce_id = None
            last_bug_bruce_id = None

    return conversations


def parse_all_logs(logs_dir=LOGS_DIR):
    """Parsea todos los archivos .txt en LOGS/."""
    all_conversations = {}

    log_files = sorted(glob.glob(os.path.join(logs_dir, '*.txt')))
    # Filtrar archivos no-log
    log_files = [f for f in log_files if re.match(r'\d{2}_\d{2}PT\d+\.txt', os.path.basename(f))]

    print(f"Parseando {len(log_files)} archivos de log...")

    for filepath in log_files:
        convs = parse_file_extended(filepath)
        for bruce_id, data in convs.items():
            if bruce_id in all_conversations:
                # Mantener versión con más turnos
                if len(data['turns']) > len(all_conversations[bruce_id]['turns']):
                    all_conversations[bruce_id] = data
            else:
                all_conversations[bruce_id] = data

    print(f"Total: {len(all_conversations)} conversaciones extraídas")
    return all_conversations


def auto_tag(conversation):
    """Clasifica conversación con tags automáticos."""
    tags = []
    turns = conversation.get('turns', [])
    bugs = conversation.get('bugs', [])
    conclusion = (conversation.get('conclusion') or '').lower()
    calificacion = conversation.get('calificacion')
    client_turns = [t for t in turns if t['role'] == 'client']

    # Bug detected
    if bugs:
        tags.append('bug_detected')
        for b in bugs:
            tags.append(f"bug_{b['tipo'].lower()}")

    # Resultado
    if 'negado' in conclusion:
        tags.append('rechazo')
    elif 'whatsapp' in conclusion or 'correo' in conclusion:
        tags.append('contacto_capturado')
        tags.append('happy_path')
    elif 'callback' in conclusion or 'luego' in conclusion:
        tags.append('callback')

    # Calificación
    if calificacion and calificacion >= 7:
        tags.append('alta_calificacion')
    elif calificacion and calificacion <= 3:
        tags.append('baja_calificacion')

    # Duración
    dur = conversation.get('duracion') or 0
    if dur < 20:
        tags.append('ultra_corta')
    elif dur > 120:
        tags.append('larga')

    # Turnos del cliente
    if len(client_turns) <= 1:
        tags.append('cliente_silencioso')
    elif len(client_turns) >= 8:
        tags.append('conversacion_extendida')

    # Patrones
    fsm = conversation.get('fsm_transitions', [])
    states_visited = set(t.get('to', '') for t in fsm)
    if 'encargado_ausente' in states_visited:
        tags.append('encargado_ausente')
    if 'contacto_capturado' in states_visited:
        tags.append('dato_capturado')
    if 'despedida' in states_visited:
        tags.append('despedida_alcanzada')

    return list(set(tags))


def generate_scenario_db(conversations):
    """Genera scenario_db.json completo."""
    # Stats
    bug_types = defaultdict(list)
    for bruce_id, conv in conversations.items():
        for bug in conv.get('bugs', []):
            bug_types[bug['tipo']].append(bruce_id)

    pattern_freq = defaultdict(int)
    for conv in conversations.values():
        for p in conv.get('patterns_detected', []):
            pattern_freq[p] += 1

    # Tag all conversations
    for bruce_id, conv in conversations.items():
        conv['tags'] = auto_tag(conv)

    # Filter valid conversations (at least 2 turns)
    valid = {k: v for k, v in conversations.items() if len(v.get('turns', [])) >= 2}

    db = {
        'metadata': {
            'generated_at': datetime.now().isoformat(),
            'total_conversations': len(conversations),
            'valid_conversations': len(valid),
            'total_with_bugs': sum(1 for c in conversations.values() if c.get('bugs')),
            'bug_type_frequency': {k: len(v) for k, v in sorted(
                bug_types.items(), key=lambda x: -len(x[1]))},
            'pattern_frequency': dict(sorted(
                pattern_freq.items(), key=lambda x: -x[1])[:30]),
        },
        'conversations': valid,
        'bug_catalog_index': {k: v for k, v in bug_types.items()},
    }

    return db


def generate_bug_catalog(scenario_db):
    """Genera bug_regression_catalog.json para tests de regresión."""
    regressions = []
    conversations = scenario_db.get('conversations', {})
    bug_index = scenario_db.get('bug_catalog_index', {})

    for bug_type, bruce_ids in bug_index.items():
        # Seleccionar hasta 5 conversaciones representativas por tipo
        selected = []
        for bruce_id in bruce_ids[:5]:
            conv = conversations.get(bruce_id)
            if not conv or len(conv.get('turns', [])) < 2:
                continue

            # Solo incluir turnos de cliente y bruce (no metadata)
            conversation_turns = []
            for turn in conv['turns']:
                conversation_turns.append({
                    'role': turn['role'],
                    'text': turn['text'],
                })

            regression = {
                'bug_id': f"{bruce_id}_{bug_type}",
                'bruce_id': bruce_id,
                'bug_type': bug_type,
                'conversation': conversation_turns,
                'source_file': conv.get('source_file', ''),
                'duracion': conv.get('duracion'),
                'calificacion': conv.get('calificacion'),
                'tags': conv.get('tags', []),
                'expected_after_fix': {
                    'bug_detector_should_catch_raw': True,
                    'bug_should_be_absent': True,
                    'replay_should_not_crash': True,
                },
            }

            selected.append(regression)

        regressions.extend(selected)

    catalog = {
        'metadata': {
            'generated_at': datetime.now().isoformat(),
            'total_regressions': len(regressions),
            'bug_types_covered': len(bug_index),
            'bug_types': list(bug_index.keys()),
        },
        'regressions': regressions,
    }

    return catalog


def print_stats(scenario_db):
    """Imprime estadísticas del dataset."""
    meta = scenario_db['metadata']
    print(f"\n{'='*60}")
    print(f"  SCENARIO DB - ESTADÍSTICAS")
    print(f"{'='*60}")
    print(f"  Total conversaciones:   {meta['total_conversations']}")
    print(f"  Conversaciones válidas: {meta['valid_conversations']}")
    print(f"  Con bugs detectados:    {meta['total_with_bugs']}")
    print()

    if meta.get('bug_type_frequency'):
        print("  BUGS POR TIPO:")
        for bug_type, count in meta['bug_type_frequency'].items():
            print(f"    {bug_type}: {count}")
    print()

    if meta.get('pattern_frequency'):
        print("  TOP 10 PATRONES:")
        for pattern, count in list(meta['pattern_frequency'].items())[:10]:
            print(f"    {pattern}: {count}")
    print(f"{'='*60}\n")


def main():
    parser = argparse.ArgumentParser(description='Log Scenario Extractor')
    parser.add_argument('--logs-dir', default=LOGS_DIR, help='Directorio de logs')
    parser.add_argument('--output', default=os.path.join(OUTPUT_DIR, 'scenario_db.json'),
                        help='Archivo de salida')
    parser.add_argument('--bug-catalog', action='store_true',
                        help='Generar bug_regression_catalog.json')
    parser.add_argument('--stats', action='store_true',
                        help='Solo mostrar estadísticas')
    args = parser.parse_args()

    # Asegurar directorio de salida
    os.makedirs(os.path.dirname(args.output), exist_ok=True)

    # Parse logs
    conversations = parse_all_logs(args.logs_dir)
    scenario_db = generate_scenario_db(conversations)

    if args.stats:
        print_stats(scenario_db)
        return

    if args.bug_catalog:
        # Cargar scenario_db existente o usar el recién generado
        db_path = os.path.join(OUTPUT_DIR, 'scenario_db.json')
        if os.path.exists(db_path):
            with open(db_path, 'r', encoding='utf-8') as f:
                scenario_db = json.load(f)

        catalog = generate_bug_catalog(scenario_db)
        output_path = os.path.join(OUTPUT_DIR, 'bug_regression_catalog.json')
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(catalog, f, ensure_ascii=False, indent=2)
        print(f"\nBug catalog generado: {output_path}")
        print(f"  {catalog['metadata']['total_regressions']} regression tests")
        print(f"  {catalog['metadata']['bug_types_covered']} tipos de bug cubiertos")
        return

    # Guardar scenario_db
    with open(args.output, 'w', encoding='utf-8') as f:
        json.dump(scenario_db, f, ensure_ascii=False, indent=2)
    print(f"\nScenario DB generado: {args.output}")
    print_stats(scenario_db)


if __name__ == '__main__':
    main()
