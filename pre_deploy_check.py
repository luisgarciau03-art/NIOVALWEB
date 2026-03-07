#!/usr/bin/env python3
"""
Pre-Deploy Check - Validacion zero-llamadas antes de cada deploy.

Corre 3 niveles de validacion en orden de velocidad:
  1. Replay de logs recientes (conversaciones reales, sin llamadas)
  2. Escenarios OOS validador_v2 (texto puro)
  3. Banco de regresion (bugs reales que nunca deben repetirse)

Uso:
    python pre_deploy_check.py              # Validacion completa
    python pre_deploy_check.py --rapido     # Solo replay reciente (< 3 min)
    python pre_deploy_check.py --replay-n 100  # Replay de ultimas N llamadas
    python pre_deploy_check.py --sin-oos    # Skip validador_v2 fase 2

Salida:
    Exit 0  = OK, listo para deploy
    Exit 1  = Regresiones detectadas, NO deployar
"""

import os
import sys
import re
import time
import argparse
import glob
from collections import Counter, defaultdict

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

LOGS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'LOGS')
BANCO_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'banco_regresion.json')

# ============================================================
# Colores
# ============================================================
class C:
    OK    = '\033[92m'
    FAIL  = '\033[91m'
    WARN  = '\033[93m'
    BOLD  = '\033[1m'
    CYAN  = '\033[96m'
    RESET = '\033[0m'

def ok(msg):   print(f"{C.OK}  [OK]{C.RESET}  {msg}")
def fail(msg): print(f"{C.FAIL}  [FAIL]{C.RESET} {msg}")
def warn(msg): print(f"{C.WARN}  [WARN]{C.RESET} {msg}")
def info(msg): print(f"{C.CYAN}  ---{C.RESET}  {msg}")

# ============================================================
# Parser de logs (reutilizado de simulador_log_replay.py)
# ============================================================
RE_BRUCE_ID_INIT = re.compile(r'ID BRUCE generado:\s*(BRUCE\d+)')
RE_CLIENTE = re.compile(r'\[CLIENTE\]\s*(BRUCE\d+)\s*-\s*CLIENTE DIJO:\s*"(.*)"')
RE_BRUCE   = re.compile(r'\[BRUCE\]\s*(BRUCE\d+)\s*DICE:\s*"(.*)"')
RE_BUG_DETECTOR = re.compile(r'\[BUG_DETECTOR\]\s*(BRUCE\d+):\s*(\d+)\s*bug')
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
                    'turns': [], 'bugs_original': [],
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
        m = RE_BUG_DETECTOR.search(line)
        if m:
            last_bug_bruce_id = m.group(1)
        m = RE_BUG_LINE.search(line)
        if m and last_bug_bruce_id and last_bug_bruce_id in conversations:
            conversations[last_bug_bruce_id]['bugs_original'].append({
                'tipo': m.group(2), 'severidad': m.group(1), 'detalle': m.group(3).strip()
            })
        m = RE_GPT_BUG.search(line)
        if m and last_bug_bruce_id and last_bug_bruce_id in conversations:
            conversations[last_bug_bruce_id]['bugs_original'].append({
                'tipo': m.group(2), 'severidad': m.group(1), 'detalle': m.group(3).strip()
            })
    return conversations


def cargar_logs_recientes(n_archivos=30):
    """Carga los N archivos de log mas recientes."""
    log_files = sorted(
        glob.glob(os.path.join(LOGS_DIR, '*.txt')),
        key=os.path.getmtime,
        reverse=True
    )
    log_files = [f for f in log_files
                 if re.match(r'\d{2}_\d{2}PT\d+\.txt', os.path.basename(f))]
    log_files = log_files[:n_archivos]

    all_convs = {}
    for lf in log_files:
        convs = parse_log_file(lf)
        all_convs.update(convs)
    return all_convs


# ============================================================
# Propuesta 1: Replay de logs reales
# ============================================================
def run_replay(n_llamadas=200, verbose=False):
    """Replay de las ultimas N llamadas reales contra el codigo actual."""
    print(f"\n{C.BOLD}{'='*60}{C.RESET}")
    print(f"{C.BOLD}  NIVEL 1: Replay de logs reales (ultimas ~{n_llamadas} llamadas){C.RESET}")
    print(f"{C.BOLD}{'='*60}{C.RESET}")

    from agente_ventas import AgenteVentas
    from bug_detector import CallEventTracker, BugDetector

    # Determinar cuantos archivos necesitamos (aprox 50-100 llamadas por archivo)
    n_archivos = max(5, n_llamadas // 60)
    info(f"Cargando {n_archivos} archivos de log recientes...")
    all_convs = cargar_logs_recientes(n_archivos)

    # Filtrar: solo conversaciones con 2+ turnos de cliente
    convs_validas = {
        bid: c for bid, c in all_convs.items()
        if len([t for t in c['turns'] if t['role'] == 'cliente']) >= 2
    }

    # Tomar las ultimas N
    sorted_bids = sorted(convs_validas.keys(),
                         key=lambda b: int(b.replace('BRUCE', '')),
                         reverse=True)[:n_llamadas]

    info(f"Llamadas validas para replay: {len(sorted_bids)}")

    _farewell = ['muchas gracias por su tiempo', 'que tenga excelente dia',
                 'que tenga buen dia', 'hasta pronto', 'hasta luego']

    regresiones = []
    limpias = 0
    t_total = time.time()

    for i, bid in enumerate(sorted_bids, 1):
        conv = convs_validas[bid]
        negocio = conv.get('negocio') or 'Desconocido'
        telefono = conv.get('telefono') or '0000000000'
        bugs_orig = conv.get('bugs_original', [])
        client_msgs = [t['text'] for t in conv['turns'] if t['role'] == 'cliente']

        agente = AgenteVentas(
            contacto_info={'nombre_negocio': negocio, 'telefono': telefono, 'ciudad': ''},
            sheets_manager=None, resultados_manager=None, whatsapp_validator=None,
        )
        tracker = CallEventTracker(
            call_sid=f"PDC_{bid}", bruce_id=f"PDC_{bid}", telefono=telefono,
        )
        tracker.simulador_texto = True

        try:
            saludo = agente.iniciar_conversacion()
            tracker.emit("BRUCE_RESPONDE", {"texto": saludo})
        except Exception:
            pass

        call_ended = False
        for msg in client_msgs:
            if call_ended:
                break
            tracker.emit("CLIENTE_DICE", {"texto": msg})
            try:
                resp = agente.procesar_respuesta(msg) or ""
            except Exception as e:
                resp = f"[ERROR: {e}]"
            tracker.emit("BRUCE_RESPONDE", {"texto": resp})
            if any(fp in resp.lower() for fp in _farewell):
                call_ended = True

        bugs_replay = BugDetector.analyze(tracker)
        tipos_orig   = set(b['tipo'] for b in bugs_orig)
        tipos_replay = set(b['tipo'] for b in bugs_replay)
        new_bugs = tipos_replay - tipos_orig  # Regresiones: bugs nuevos no existentes antes

        if new_bugs:
            regresiones.append({
                'bruce_id': bid,
                'negocio': negocio,
                'bugs_nuevos': list(new_bugs),
                'bugs_orig': list(tipos_orig),
            })
            if verbose:
                fail(f"{bid} - {negocio[:40]} | REGRESION: {new_bugs}")
        else:
            limpias += 1
            if verbose and i % 20 == 0:
                info(f"  {i}/{len(sorted_bids)} procesadas...")

    elapsed = time.time() - t_total
    print(f"\n  Llamadas replay: {len(sorted_bids)}")
    print(f"  Limpias:         {limpias}")
    print(f"  Regresiones:     {len(regresiones)}")
    print(f"  Tiempo:          {elapsed:.0f}s")

    if regresiones:
        fail(f"REGRESIONES DETECTADAS en {len(regresiones)} llamadas:")
        for r in regresiones[:10]:
            print(f"    {r['bruce_id']} | {r['negocio'][:40]} | {r['bugs_nuevos']}")
        return False
    else:
        ok(f"Replay limpio: {limpias} llamadas sin regresiones ({elapsed:.0f}s)")
        return True


# ============================================================
# Propuesta 1b: OOS validador_v2
# ============================================================
def run_oos():
    """Corre validador_v2 fase 2 (157 escenarios OOS)."""
    print(f"\n{C.BOLD}{'='*60}{C.RESET}")
    print(f"{C.BOLD}  NIVEL 2: Escenarios OOS (validador_v2 fase 2){C.RESET}")
    print(f"{C.BOLD}{'='*60}{C.RESET}")
    import subprocess
    t0 = time.time()
    result = subprocess.run(
        [sys.executable, 'validador_v2.py', '--fase', '2'],
        capture_output=True, text=True, encoding='utf-8', errors='replace',
        cwd=os.path.dirname(os.path.abspath(__file__))
    )
    elapsed = time.time() - t0
    output = result.stdout + result.stderr

    # Extraer resultado
    bugs_line = [l for l in output.split('\n') if 'Convs con bug:' in l]
    if bugs_line:
        print(f"  {bugs_line[0].strip()}")

    veredicto_line = [l for l in output.split('\n') if 'Veredicto' in l]
    if veredicto_line:
        print(f"  {veredicto_line[0].strip()}")

    if '0.0%' in output or '(0/' in output.split('Convs con bug:')[-1][:20]:
        ok(f"OOS limpio: 0 bugs en escenarios ({elapsed:.0f}s)")
        return True
    else:
        fail(f"OOS: bugs detectados en escenarios ({elapsed:.0f}s)")
        # Mostrar cuales
        for l in output.split('\n'):
            if 'Bug ' in l and ':' in l:
                print(f"    {l.strip()}")
        return False


# ============================================================
# Propuesta 3: Banco de regresion
# ============================================================
def run_banco():
    """Corre el banco de patrones reales (bugs que nunca deben repetirse)."""
    if not os.path.exists(BANCO_PATH):
        warn("Banco de regresion no encontrado. Ejecuta: python banco_regresion.py --construir")
        return True  # No falla si no existe aun

    print(f"\n{C.BOLD}{'='*60}{C.RESET}")
    print(f"{C.BOLD}  NIVEL 3: Banco de regresion (bugs reales historicos){C.RESET}")
    print(f"{C.BOLD}{'='*60}{C.RESET}")

    import json
    from agente_ventas import AgenteVentas
    from bug_detector import CallEventTracker, BugDetector

    with open(BANCO_PATH, 'r', encoding='utf-8') as f:
        banco = json.load(f)

    escenarios = banco.get('escenarios', [])
    info(f"Escenarios en banco: {len(escenarios)}")

    _farewell = ['muchas gracias por su tiempo', 'que tenga excelente dia',
                 'que tenga buen dia', 'hasta pronto', 'hasta luego']

    regresiones = []
    limpias = 0

    for esc in escenarios:
        bid = esc['bruce_id']
        negocio = esc.get('negocio') or 'Desconocido'
        bug_esperado = esc.get('bug_tipo')
        client_msgs = esc.get('client_turns', [])

        if not client_msgs:
            continue

        agente = AgenteVentas(
            contacto_info={'nombre_negocio': negocio, 'telefono': '0000000000', 'ciudad': ''},
            sheets_manager=None, resultados_manager=None, whatsapp_validator=None,
        )
        tracker = CallEventTracker(
            call_sid=f"BANCO_{bid}", bruce_id=f"BANCO_{bid}", telefono='0000000000',
        )
        tracker.simulador_texto = True

        try:
            saludo = agente.iniciar_conversacion()
            tracker.emit("BRUCE_RESPONDE", {"texto": saludo})
        except Exception:
            pass

        call_ended = False
        for msg in client_msgs:
            if call_ended:
                break
            tracker.emit("CLIENTE_DICE", {"texto": msg})
            try:
                resp = agente.procesar_respuesta(msg) or ""
            except Exception as e:
                resp = f"[ERROR: {e}]"
            tracker.emit("BRUCE_RESPONDE", {"texto": resp})
            if any(fp in resp.lower() for fp in _farewell):
                call_ended = True

        bugs_replay = BugDetector.analyze(tracker)
        tipos_replay = set(b['tipo'] for b in bugs_replay)

        if bug_esperado and bug_esperado in tipos_replay:
            regresiones.append({
                'bruce_id': bid,
                'bug_regresion': bug_esperado,
                'negocio': negocio,
            })
            fail(f"REGRESION: {bid} | {bug_esperado} volvio a aparecer | {negocio[:40]}")
        else:
            limpias += 1

    if regresiones:
        fail(f"Banco: {len(regresiones)} regresiones de bugs reales")
        return False
    else:
        ok(f"Banco limpio: {limpias} patrones reales sin regresion")
        return True


# ============================================================
# Main
# ============================================================
def main():
    parser = argparse.ArgumentParser(description='Pre-deploy check zero-llamadas')
    parser.add_argument('--rapido', action='store_true',
                        help='Solo replay reciente (nivel 1, ~3 min)')
    parser.add_argument('--sin-oos', action='store_true',
                        help='Skip validador_v2 OOS (nivel 2)')
    parser.add_argument('--replay-n', type=int, default=150,
                        help='Numero de llamadas historicas para replay (default: 150)')
    parser.add_argument('--verbose', action='store_true',
                        help='Mostrar detalle de cada llamada')
    args = parser.parse_args()

    print(f"\n{C.BOLD}{'='*60}")
    print(f"  PRE-DEPLOY CHECK - Zero llamadas reales")
    print(f"  Validacion: replay {args.replay_n} logs + OOS + banco regresion")
    print(f"{'='*60}{C.RESET}")

    t_inicio = time.time()
    resultados = {}

    # Nivel 1: Replay
    resultados['replay'] = run_replay(n_llamadas=args.replay_n, verbose=args.verbose)

    # Nivel 2: OOS (skip si --rapido o --sin-oos)
    if not args.rapido and not args.sin_oos:
        resultados['oos'] = run_oos()
    else:
        resultados['oos'] = True
        warn("OOS skipeado (--rapido o --sin-oos)")

    # Nivel 3: Banco de regresion
    if not args.rapido:
        resultados['banco'] = run_banco()
    else:
        resultados['banco'] = True

    # Resumen final
    elapsed_total = time.time() - t_inicio
    print(f"\n{C.BOLD}{'='*60}{C.RESET}")
    print(f"{C.BOLD}  RESUMEN PRE-DEPLOY{C.RESET}")
    print(f"  Tiempo total: {elapsed_total:.0f}s")
    print()

    todos_ok = all(resultados.values())

    nivel_nombres = {
        'replay': 'Replay logs reales',
        'oos':    'Escenarios OOS',
        'banco':  'Banco regresion',
    }
    for k, v in resultados.items():
        estado = f"{C.OK}PASS{C.RESET}" if v else f"{C.FAIL}FAIL{C.RESET}"
        print(f"  {estado}  {nivel_nombres[k]}")

    print()
    if todos_ok:
        print(f"{C.OK}{C.BOLD}  LISTO PARA DEPLOY{C.RESET}")
        sys.exit(0)
    else:
        print(f"{C.FAIL}{C.BOLD}  DEPLOY BLOQUEADO - Corregir regresiones primero{C.RESET}")
        sys.exit(1)


if __name__ == '__main__':
    main()
