"""
Log Parser: Extrae conversaciones de BRUCE#### desde archivos de log de Railway.

Parsea LOGS/*.txt y genera tests/test_data/conversations.json con:
- BRUCE ID
- Turnos de conversacion (cliente/bruce)
- Patrones detectados
- Patrones invalidados
- Resultado y duracion

Uso:
    python scripts/log_parser.py
    python scripts/log_parser.py --logs-dir LOGS --output tests/test_data/conversations.json
"""

import os
import re
import json
import glob
import argparse
from collections import defaultdict


def parse_log_file(filepath):
    """
    Parsea un archivo de log y extrae conversaciones BRUCE####.

    Returns dict: {bruce_id: {turns, patterns_detected, patterns_invalidated, ...}}
    """
    conversations = {}
    current_bruce_id = None

    try:
        with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
            lines = f.readlines()
    except Exception as e:
        print(f"  Error leyendo {filepath}: {e}")
        return conversations

    for line in lines:
        line = line.rstrip('\n')

        # Detectar BRUCE ID generado
        # Patron: "ID BRUCE generado: BRUCE2064"
        match_id = re.search(r'ID BRUCE generado:\s*(BRUCE\d+)', line)
        if match_id:
            current_bruce_id = match_id.group(1)
            if current_bruce_id not in conversations:
                conversations[current_bruce_id] = {
                    'turns': [],
                    'patterns_detected': [],
                    'patterns_invalidated': [],
                    'resultado': None,
                    'duracion': None,
                    'negocio': None,
                    'source_file': os.path.basename(filepath),
                }

        # Detectar negocio
        # Patron: "Datos extraidos - Tel: +52..., Negocio: Materiales y Ferreteria..."
        match_negocio = re.search(r'Negocio:\s*(.+?)(?:\s*$)', line)
        if match_negocio and current_bruce_id and current_bruce_id in conversations:
            conversations[current_bruce_id]['negocio'] = match_negocio.group(1).strip()

        # Detectar mensaje del cliente
        # Patron: "[timestamp] [CLIENTE] BRUCE2064 - CLIENTE DIJO: "texto""
        match_cliente = re.search(
            r'\[CLIENTE\]\s*(BRUCE\d+)\s*-\s*CLIENTE DIJO:\s*"(.*)"',
            line
        )
        if match_cliente:
            bruce_id = match_cliente.group(1)
            texto = match_cliente.group(2)
            if bruce_id in conversations and texto.strip():
                # Evitar duplicados consecutivos del mismo texto
                turns = conversations[bruce_id]['turns']
                if not turns or turns[-1].get('text') != texto or turns[-1].get('role') != 'client':
                    conversations[bruce_id]['turns'].append({
                        'role': 'client',
                        'text': texto
                    })

        # Detectar mensaje de Bruce
        # Patron: "[timestamp] [BRUCE] BRUCE2064 DICE: "texto""
        match_bruce = re.search(
            r'\[BRUCE\]\s*(BRUCE\d+)\s*DICE:\s*"(.*)"',
            line
        )
        if match_bruce:
            bruce_id = match_bruce.group(1)
            texto = match_bruce.group(2)
            if bruce_id in conversations and texto.strip():
                turns = conversations[bruce_id]['turns']
                if not turns or turns[-1].get('text') != texto or turns[-1].get('role') != 'bruce':
                    conversations[bruce_id]['turns'].append({
                        'role': 'bruce',
                        'text': texto
                    })

        # Detectar patron detectado
        # Patron: "FIX 491: PATRON DETECTADO (TIPO) - Latencia..."
        match_patron = re.search(
            r'PATR[OÓ]N DETECTADO\s*\((\w+)\)',
            line
        )
        if match_patron and current_bruce_id and current_bruce_id in conversations:
            tipo = match_patron.group(1)
            conversations[current_bruce_id]['patterns_detected'].append(tipo)

        # Detectar patron invalidado por FIX 600
        # Patron: "FIX 600 SPLITTER: ..." or "Patron 'X' INVALIDADO"
        match_inv_600 = re.search(
            r"FIX 600.*(?:INVALIDADO|invalidado|splitter)",
            line, re.IGNORECASE
        )
        if match_inv_600 and current_bruce_id and current_bruce_id in conversations:
            conversations[current_bruce_id]['patterns_invalidated'].append('FIX_600')

        # Detectar patron invalidado por FIX 601
        match_inv_601 = re.search(
            r"FIX 601.*(?:INVALIDADO|invalidado|complejidad)",
            line, re.IGNORECASE
        )
        if match_inv_601 and current_bruce_id and current_bruce_id in conversations:
            conversations[current_bruce_id]['patterns_invalidated'].append('FIX_601')

        # Detectar duracion
        # Patron: "Duracion: 37s" or "Duracion de la llamada: 36 segundos"
        match_dur = re.search(r'[Dd]uraci[oó]n.*?(\d+)\s*(?:s|segundos)', line)
        if match_dur and current_bruce_id and current_bruce_id in conversations:
            conversations[current_bruce_id]['duracion'] = int(match_dur.group(1))

        # Detectar resultado
        # Patron: "Conclusion determinada: Nulo (NEGADO)" or "Resultado: NEGADO"
        match_res = re.search(r'(?:Conclusi[oó]n determinada|Resultado):\s*(\w+)', line)
        if match_res and current_bruce_id and current_bruce_id in conversations:
            conversations[current_bruce_id]['resultado'] = match_res.group(1)

        # Detectar llamada terminada (reset current_bruce_id)
        if 'LLAMADA TERMINADA' in line:
            current_bruce_id = None

    return conversations


def parse_all_logs(logs_dir):
    """Parsea todos los archivos .txt en el directorio LOGS/."""
    all_conversations = {}

    log_files = sorted(glob.glob(os.path.join(logs_dir, '*.txt')))
    print(f"Encontrados {len(log_files)} archivos de log")

    for filepath in log_files:
        filename = os.path.basename(filepath)
        convs = parse_log_file(filepath)
        if convs:
            print(f"  {filename}: {len(convs)} conversaciones")
            for bruce_id, data in convs.items():
                # Si ya existe, mantener la version con mas turnos
                if bruce_id in all_conversations:
                    if len(data['turns']) > len(all_conversations[bruce_id]['turns']):
                        all_conversations[bruce_id] = data
                else:
                    all_conversations[bruce_id] = data

    return all_conversations


def filter_valid_conversations(conversations, min_turns=2):
    """Filtra conversaciones validas (con al menos min_turns turnos)."""
    valid = {}
    for bruce_id, data in conversations.items():
        if len(data['turns']) >= min_turns:
            valid[bruce_id] = data
    return valid


def generate_stats(conversations):
    """Genera estadisticas del dataset."""
    total = len(conversations)
    with_patterns = sum(1 for c in conversations.values() if c['patterns_detected'])
    with_invalidations = sum(1 for c in conversations.values() if c['patterns_invalidated'])
    avg_turns = sum(len(c['turns']) for c in conversations.values()) / max(total, 1)

    all_patterns = defaultdict(int)
    for c in conversations.values():
        for p in c['patterns_detected']:
            all_patterns[p] += 1

    return {
        'total_conversations': total,
        'with_patterns_detected': with_patterns,
        'with_invalidations': with_invalidations,
        'avg_turns': round(avg_turns, 1),
        'pattern_frequency': dict(sorted(all_patterns.items(), key=lambda x: -x[1])[:20]),
    }


def main():
    parser = argparse.ArgumentParser(description='Parse Bruce W log files into test data')
    parser.add_argument('--logs-dir', default=os.path.join(os.path.dirname(os.path.dirname(__file__)), 'LOGS'),
                       help='Directory with log .txt files')
    parser.add_argument('--output', default=os.path.join(os.path.dirname(os.path.dirname(__file__)),
                        'tests', 'test_data', 'conversations.json'),
                       help='Output JSON file path')
    parser.add_argument('--min-turns', type=int, default=2,
                       help='Minimum turns per conversation to include')
    args = parser.parse_args()

    print(f"Parseando logs desde: {args.logs_dir}")
    conversations = parse_all_logs(args.logs_dir)

    print(f"\nTotal conversaciones encontradas: {len(conversations)}")

    valid = filter_valid_conversations(conversations, args.min_turns)
    print(f"Conversaciones con >= {args.min_turns} turnos: {len(valid)}")

    stats = generate_stats(valid)
    print(f"\nEstadisticas:")
    print(f"  Turnos promedio: {stats['avg_turns']}")
    print(f"  Con patrones detectados: {stats['with_patterns_detected']}")
    print(f"  Con invalidaciones: {stats['with_invalidations']}")
    if stats['pattern_frequency']:
        print(f"  Top patrones:")
        for p, count in list(stats['pattern_frequency'].items())[:10]:
            print(f"    {p}: {count}")

    # Asegurar que el directorio de salida existe
    os.makedirs(os.path.dirname(args.output), exist_ok=True)

    output = {
        'metadata': {
            'total_log_files': len(glob.glob(os.path.join(args.logs_dir, '*.txt'))),
            'total_conversations': len(valid),
            'stats': stats,
        },
        'conversations': valid,
    }

    with open(args.output, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\nGuardado en: {args.output}")
    print(f"Tamano: {os.path.getsize(args.output) / 1024:.1f} KB")


if __name__ == '__main__':
    main()
