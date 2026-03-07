#!/usr/bin/env python3
"""
Banco de Regresion - Convierte bugs reales de produccion en escenarios de prueba.

Cada bug real que ocurre una vez queda registrado permanentemente.
El pre_deploy_check.py verifica que esos bugs nunca vuelvan a aparecer.

Uso:
    python banco_regresion.py --construir          # Construir banco desde logs historicos
    python banco_regresion.py --agregar BRUCE2665  # Agregar llamada especifica al banco
    python banco_regresion.py --listar             # Ver todos los patrones en el banco
    python banco_regresion.py --stats              # Estadisticas del banco
    python banco_regresion.py --construir --min-bugs 1  # Solo llamadas con bugs
"""

import os
import sys
import re
import json
import glob
import argparse
from collections import Counter

if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

LOGS_DIR  = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'LOGS')
BANCO_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'banco_regresion.json')

# ============================================================
# Parser (reutilizado)
# ============================================================
RE_BRUCE_ID_INIT = re.compile(r'ID BRUCE generado:\s*(BRUCE\d+)')
RE_CLIENTE  = re.compile(r'\[CLIENTE\]\s*(BRUCE\d+)\s*-\s*CLIENTE DIJO:\s*"(.*)"')
RE_BRUCE    = re.compile(r'\[BRUCE\]\s*(BRUCE\d+)\s*DICE:\s*"(.*)"')
RE_BUG_DET  = re.compile(r'\[BUG_DETECTOR\]\s*(BRUCE\d+):\s*(\d+)\s*bug')
RE_BUG_LINE = re.compile(r'\[(ALTO|MEDIO|CRITICO)\]\s*(\w+):\s*(.*)')
RE_GPT_BUG  = re.compile(r'\[GPT (ALTO|MEDIO)\]\s*(GPT_\w+):\s*(.*)')
RE_NEGOCIO  = re.compile(r'Negocio:\s*(.+?)(?:\s*\(|$)')
RE_TELEFONO = re.compile(r'Tel:\s*(\+?\d[\d\s]*)')


def parse_log_file(filepath):
    conversations = {}
    current_bruce_id = None
    last_bug_bruce_id = None
    try:
        with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
            lines = f.readlines()
    except Exception:
        return conversations

    for line in lines:
        line = line.rstrip('\n')
        m = RE_BRUCE_ID_INIT.search(line)
        if m:
            current_bruce_id = m.group(1)
            if current_bruce_id not in conversations:
                conversations[current_bruce_id] = {
                    'turns': [], 'bugs': [],
                    'negocio': None, 'telefono': None,
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
            bid, texto = m.group(1), m.group(2)
            if bid in conversations and texto.strip():
                t = conversations[bid]['turns']
                if not t or t[-1].get('text') != texto or t[-1].get('role') != 'cliente':
                    t.append({'role': 'cliente', 'text': texto.strip()})
        m = RE_BRUCE.search(line)
        if m:
            bid, texto = m.group(1), m.group(2)
            if bid in conversations and texto.strip():
                t = conversations[bid]['turns']
                if not t or t[-1].get('text') != texto or t[-1].get('role') != 'bruce':
                    t.append({'role': 'bruce', 'text': texto.strip()})
        m = RE_BUG_DET.search(line)
        if m:
            last_bug_bruce_id = m.group(1)
        m = RE_BUG_LINE.search(line)
        if m and last_bug_bruce_id and last_bug_bruce_id in conversations:
            conversations[last_bug_bruce_id]['bugs'].append({
                'tipo': m.group(2), 'severidad': m.group(1), 'detalle': m.group(3).strip()
            })
        m = RE_GPT_BUG.search(line)
        if m and last_bug_bruce_id and last_bug_bruce_id in conversations:
            conversations[last_bug_bruce_id]['bugs'].append({
                'tipo': m.group(2), 'severidad': m.group(1), 'detalle': m.group(3).strip()
            })
    return conversations


def parse_all_logs():
    log_files = sorted(glob.glob(os.path.join(LOGS_DIR, '*.txt')), key=os.path.getmtime)
    log_files = [f for f in log_files
                 if re.match(r'\d{2}_\d{2}PT\d+\.txt', os.path.basename(f))]
    all_convs = {}
    total = len(log_files)
    for i, lf in enumerate(log_files, 1):
        if i % 50 == 0:
            print(f"  Parseando archivo {i}/{total}...")
        convs = parse_log_file(lf)
        all_convs.update(convs)
    return all_convs


def conv_a_escenario(bruce_id, conv):
    """Convierte una conversacion parseada a escenario de banco."""
    client_turns = [t['text'] for t in conv['turns'] if t['role'] == 'cliente' and t['text']]
    bugs = conv.get('bugs', [])
    if not client_turns or not bugs:
        return None

    # Tomar el bug mas severo como el que queremos detectar
    severidad_orden = {'CRITICO': 3, 'ALTO': 2, 'MEDIO': 1}
    bugs_sorted = sorted(bugs, key=lambda b: severidad_orden.get(b['severidad'], 0), reverse=True)
    bug_principal = bugs_sorted[0]

    return {
        'bruce_id': bruce_id,
        'negocio': conv.get('negocio') or 'Desconocido',
        'source_file': conv.get('source_file', ''),
        'bug_tipo': bug_principal['tipo'],
        'bug_severidad': bug_principal['severidad'],
        'bug_detalle': bug_principal['detalle'],
        'todos_bugs': [b['tipo'] for b in bugs],
        'client_turns': client_turns,
        'n_turns': len(client_turns),
    }


def cargar_banco():
    if os.path.exists(BANCO_PATH):
        with open(BANCO_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {'version': 1, 'escenarios': [], 'bruce_ids': []}


def guardar_banco(banco):
    banco['total'] = len(banco['escenarios'])
    with open(BANCO_PATH, 'w', encoding='utf-8') as f:
        json.dump(banco, f, ensure_ascii=False, indent=2)
    print(f"  Banco guardado: {BANCO_PATH} ({banco['total']} escenarios)")


# ============================================================
# Comandos
# ============================================================

def cmd_construir(min_bugs=1, max_turns=15, solo_critico_alto=True):
    """Construir banco desde todos los logs historicos."""
    print("\n  Construyendo banco de regresion desde logs historicos...")
    print(f"  Directorio: {LOGS_DIR}")

    all_convs = parse_all_logs()
    print(f"  Total conversaciones parseadas: {len(all_convs)}")

    banco = cargar_banco()
    bids_existentes = set(banco.get('bruce_ids', []))

    nuevos = 0
    skipped_sin_bugs = 0
    skipped_existentes = 0
    skipped_sin_turns = 0

    for bruce_id, conv in all_convs.items():
        if bruce_id in bids_existentes:
            skipped_existentes += 1
            continue

        bugs = conv.get('bugs', [])
        client_turns = [t['text'] for t in conv['turns'] if t['role'] == 'cliente']

        if len(bugs) < min_bugs:
            skipped_sin_bugs += 1
            continue

        if len(client_turns) < 2 or len(client_turns) > max_turns:
            skipped_sin_turns += 1
            continue

        if solo_critico_alto:
            bugs_relevantes = [b for b in bugs if b['severidad'] in ('CRITICO', 'ALTO')]
            if not bugs_relevantes:
                skipped_sin_bugs += 1
                continue

        esc = conv_a_escenario(bruce_id, conv)
        if esc:
            banco['escenarios'].append(esc)
            banco.setdefault('bruce_ids', []).append(bruce_id)
            nuevos += 1

    print(f"\n  Resultado:")
    print(f"    Nuevos escenarios agregados: {nuevos}")
    print(f"    Ya existian en banco:        {skipped_existentes}")
    print(f"    Sin bugs (skipped):          {skipped_sin_bugs}")
    print(f"    Turns invalidos (skipped):   {skipped_sin_turns}")

    guardar_banco(banco)

    # Stats por tipo de bug
    bug_counter = Counter(esc['bug_tipo'] for esc in banco['escenarios'])
    print(f"\n  Top bugs en banco ({len(banco['escenarios'])} total):")
    for bug_tipo, cnt in bug_counter.most_common(10):
        print(f"    {bug_tipo:35s}: {cnt}")


def cmd_agregar(bruce_id):
    """Agregar una llamada especifica al banco."""
    print(f"\n  Buscando {bruce_id} en logs...")

    log_files = sorted(glob.glob(os.path.join(LOGS_DIR, '*.txt')), key=os.path.getmtime, reverse=True)
    log_files = [f for f in log_files
                 if re.match(r'\d{2}_\d{2}PT\d+\.txt', os.path.basename(f))]

    conv = None
    for lf in log_files:
        convs = parse_log_file(lf)
        if bruce_id in convs:
            conv = convs[bruce_id]
            print(f"  Encontrado en: {os.path.basename(lf)}")
            break

    if not conv:
        print(f"  ERROR: {bruce_id} no encontrado en logs")
        return

    banco = cargar_banco()
    if bruce_id in banco.get('bruce_ids', []):
        print(f"  {bruce_id} ya existe en el banco")
        return

    client_turns = [t['text'] for t in conv['turns'] if t['role'] == 'cliente']
    bugs = conv.get('bugs', [])
    print(f"  Turnos cliente: {len(client_turns)}")
    print(f"  Bugs detectados: {[b['tipo'] for b in bugs]}")

    if not client_turns:
        print(f"  ERROR: Sin turnos de cliente para agregar")
        return

    # Si no tiene bugs en logs, pedir tipo manualmente
    if not bugs:
        bug_tipo = input("  Bug tipo (ej. GPT_LOGICA_ROTA): ").strip() or 'UNKNOWN'
        bugs = [{'tipo': bug_tipo, 'severidad': 'ALTO', 'detalle': 'Agregado manualmente'}]
        conv['bugs'] = bugs

    esc = conv_a_escenario(bruce_id, conv)
    if esc:
        banco['escenarios'].append(esc)
        banco.setdefault('bruce_ids', []).append(bruce_id)
        guardar_banco(banco)
        print(f"  Agregado: {bruce_id} | {esc['bug_tipo']} | {len(client_turns)} turnos")
    else:
        print(f"  No se pudo convertir a escenario")


def cmd_listar():
    """Listar todos los escenarios en el banco."""
    banco = cargar_banco()
    escenarios = banco.get('escenarios', [])

    if not escenarios:
        print("  Banco vacio. Ejecuta: python banco_regresion.py --construir")
        return

    print(f"\n  Banco de regresion: {len(escenarios)} escenarios")
    print(f"  {'BRUCE ID':<12} {'BUG TIPO':<35} {'SEV':<8} {'TURNS':<6} {'NEGOCIO'}")
    print(f"  {'-'*90}")
    for esc in sorted(escenarios, key=lambda e: e['bruce_id']):
        print(f"  {esc['bruce_id']:<12} {esc['bug_tipo']:<35} "
              f"{esc['bug_severidad']:<8} {esc['n_turns']:<6} {esc['negocio'][:30]}")


def cmd_stats():
    """Estadisticas del banco."""
    banco = cargar_banco()
    escenarios = banco.get('escenarios', [])

    if not escenarios:
        print("  Banco vacio.")
        return

    print(f"\n  BANCO DE REGRESION - Estadisticas")
    print(f"  Total escenarios: {len(escenarios)}")

    bug_counter = Counter(esc['bug_tipo'] for esc in escenarios)
    sev_counter = Counter(esc['bug_severidad'] for esc in escenarios)

    print(f"\n  Por tipo de bug:")
    for bug_tipo, cnt in bug_counter.most_common():
        bar = '|' * min(cnt, 40)
        print(f"    {bug_tipo:<35} {cnt:3d} {bar}")

    print(f"\n  Por severidad:")
    for sev, cnt in sev_counter.most_common():
        print(f"    {sev:<10} {cnt}")

    turns_list = [esc['n_turns'] for esc in escenarios]
    print(f"\n  Turnos por escenario:")
    print(f"    Min: {min(turns_list)} | Max: {max(turns_list)} | Promedio: {sum(turns_list)/len(turns_list):.1f}")


# ============================================================
# Main
# ============================================================
def main():
    parser = argparse.ArgumentParser(description='Banco de regresion de bugs reales')
    parser.add_argument('--construir', action='store_true',
                        help='Construir banco desde logs historicos')
    parser.add_argument('--agregar', metavar='BRUCE_ID',
                        help='Agregar llamada especifica al banco')
    parser.add_argument('--listar', action='store_true',
                        help='Listar todos los escenarios')
    parser.add_argument('--stats', action='store_true',
                        help='Estadisticas del banco')
    parser.add_argument('--min-bugs', type=int, default=1,
                        help='Minimo de bugs para incluir en banco (default: 1)')
    parser.add_argument('--todos', action='store_true',
                        help='Incluir bugs MEDIO tambien (default: solo CRITICO/ALTO)')
    args = parser.parse_args()

    if args.construir:
        cmd_construir(
            min_bugs=args.min_bugs,
            solo_critico_alto=not args.todos,
        )
    elif args.agregar:
        cmd_agregar(args.agregar)
    elif args.listar:
        cmd_listar()
    elif args.stats:
        cmd_stats()
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
