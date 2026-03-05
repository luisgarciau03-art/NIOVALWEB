#!/usr/bin/env python3
"""
Simulador Log Replay - Replay de llamadas reales desde logs de produccion.

Extrae conversaciones reales de los logs de Railway y las reproduce
a traves de la pipeline actual (FSM + Patterns + GPT + Post-filters),
comparando los bugs originales vs los bugs del replay.

Uso:
    python simulador_log_replay.py --latest 5             # Ultimas 5 llamadas con bugs
    python simulador_log_replay.py --bruce BRUCE2549      # Replay de llamada especifica
    python simulador_log_replay.py --file 25_02PT15.txt   # Todas las llamadas de un log
    python simulador_log_replay.py --latest 10 --verbose  # Con respuestas completas
    python simulador_log_replay.py --latest 10 --bugs-only  # Solo llamadas con bugs
    python simulador_log_replay.py --list                 # Listar llamadas disponibles
"""

import os
import sys
import re
import time
import argparse
import glob
from collections import Counter, defaultdict

# FIX: Windows cp1252 no soporta caracteres Unicode como ->
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Asegurar path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Cargar .env antes de imports
from dotenv import load_dotenv
load_dotenv()

from agente_ventas import AgenteVentas
from bug_detector import CallEventTracker, BugDetector

# Directorio de logs
LOGS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'LOGS')


# ============================================================
# Parser de logs (basado en log_scenario_extractor.py)
# ============================================================

RE_BRUCE_ID_INIT = re.compile(r'ID BRUCE generado:\s*(BRUCE\d+)')
RE_CLIENTE = re.compile(
    r'\[CLIENTE\]\s*(BRUCE\d+)\s*-\s*CLIENTE DIJO:\s*"(.*)"'
)
RE_BRUCE = re.compile(
    r'\[BRUCE\]\s*(BRUCE\d+)\s*DICE:\s*"(.*)"'
)
RE_BUG_DETECTOR = re.compile(
    r'\[BUG_DETECTOR\]\s*(BRUCE\d+):\s*(\d+)\s*bug'
)
RE_BUG_LINE = re.compile(
    r'\[(ALTO|MEDIO|CRITICO)\]\s*(\w+):\s*(.*)'
)
RE_GPT_BUG = re.compile(
    r'\[GPT (ALTO|MEDIO)\]\s*(GPT_\w+):\s*(.*)'
)
RE_NEGOCIO = re.compile(r'Negocio:\s*(.+?)(?:\s*\(|$)')
RE_TELEFONO = re.compile(r'Tel:\s*(\+?\d[\d\s]*)')
RE_DURACION_STATUS = re.compile(r'Duraci[oó]n:\s*(\d+)s')


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

        # --- BRUCE ID generado ---
        m = RE_BRUCE_ID_INIT.search(line)
        if m:
            current_bruce_id = m.group(1)
            if current_bruce_id not in conversations:
                conversations[current_bruce_id] = {
                    'turns': [],
                    'bugs_original': [],
                    'negocio': None,
                    'telefono': None,
                    'duracion': None,
                    'source_file': os.path.basename(filepath),
                }

        # --- DEBUG 3: Datos extraidos (telefono + negocio) ---
        if 'DEBUG 3:' in line and 'Datos extra' in line:
            m_tel = RE_TELEFONO.search(line)
            m_neg = RE_NEGOCIO.search(line)
            if current_bruce_id and current_bruce_id in conversations:
                if m_tel:
                    conversations[current_bruce_id]['telefono'] = m_tel.group(1).replace(' ', '')
                if m_neg:
                    conversations[current_bruce_id]['negocio'] = m_neg.group(1).strip()

        # --- Cliente dice ---
        m = RE_CLIENTE.search(line)
        if m:
            bruce_id, texto = m.group(1), m.group(2)
            if bruce_id in conversations and texto.strip():
                turns = conversations[bruce_id]['turns']
                # Evitar duplicados consecutivos
                if not turns or turns[-1].get('text') != texto or turns[-1].get('role') != 'cliente':
                    conversations[bruce_id]['turns'].append({
                        'role': 'cliente',
                        'text': texto.strip(),
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
                        'text': texto.strip(),
                    })

        # --- Bug Detector header ---
        m = RE_BUG_DETECTOR.search(line)
        if m:
            last_bug_bruce_id = m.group(1)

        # --- Bug line (rule-based) ---
        m = RE_BUG_LINE.search(line)
        if m and last_bug_bruce_id and last_bug_bruce_id in conversations:
            severidad, bug_type, detail = m.group(1), m.group(2), m.group(3).strip()
            conversations[last_bug_bruce_id]['bugs_original'].append({
                'tipo': bug_type,
                'severidad': severidad,
                'detalle': detail,
                'source': 'rule',
            })

        # --- GPT eval bug ---
        m = RE_GPT_BUG.search(line)
        if m and last_bug_bruce_id and last_bug_bruce_id in conversations:
            severidad, bug_type, detail = m.group(1), m.group(2), m.group(3).strip()
            conversations[last_bug_bruce_id]['bugs_original'].append({
                'tipo': bug_type,
                'severidad': severidad,
                'detalle': detail,
                'source': 'gpt_eval',
            })

        # --- Duracion (STATUS CALLBACK) ---
        m = RE_DURACION_STATUS.search(line)
        if m and current_bruce_id and current_bruce_id in conversations:
            conversations[current_bruce_id]['duracion'] = int(m.group(1))

    return conversations


def parse_all_logs():
    """Parsea todos los archivos de log en LOGS/."""
    log_files = sorted(glob.glob(os.path.join(LOGS_DIR, '*.txt')))
    log_files = [f for f in log_files if re.match(r'\d{2}_\d{2}PT\d+\.txt', os.path.basename(f))]

    all_convs = {}
    for lf in log_files:
        convs = parse_log_file(lf)
        all_convs.update(convs)

    return all_convs


def get_client_messages(conversation):
    """Extrae solo los mensajes del cliente de una conversacion."""
    return [t['text'] for t in conversation['turns'] if t['role'] == 'cliente' and t['text']]


# ============================================================
# Simulador Log Replay
# ============================================================

class LogReplaySimulator:
    def __init__(self, verbose=False, gpt_eval=False):
        self.verbose = verbose
        self.gpt_eval = gpt_eval  # FIX 901: Ejecutar GPT eval como en produccion
        self.resultados = []

    def replay_call(self, bruce_id, conv_data, call_index=0, total_calls=0):
        """Reproduce una llamada real a traves de la pipeline actual."""
        negocio = conv_data.get('negocio') or 'Negocio Desconocido'
        telefono = conv_data.get('telefono') or '0000000000'
        bugs_original = conv_data.get('bugs_original', [])
        client_messages = get_client_messages(conv_data)

        if not client_messages:
            return None

        idx_str = f"[{call_index}/{total_calls}] " if total_calls else ""
        n_bugs_orig = len(bugs_original)
        bugs_orig_str = f" ({n_bugs_orig} bugs)" if n_bugs_orig else ""

        print(f"\n  {idx_str}{bruce_id} - {negocio}{bugs_orig_str}")
        print(f"    Turnos cliente: {len(client_messages)} | Archivo: {conv_data.get('source_file', '?')}")

        t0 = time.time()

        # 1. Crear agente real
        contacto_info = {
            'nombre_negocio': negocio,
            'telefono': telefono,
            'ciudad': '',
        }
        agente = AgenteVentas(
            contacto_info=contacto_info,
            sheets_manager=None,
            resultados_manager=None,
            whatsapp_validator=None,
        )

        # 2. Crear tracker
        tracker = CallEventTracker(
            call_sid=f"REPLAY_{bruce_id}",
            bruce_id=f"R_{bruce_id}",
            telefono=telefono,
        )

        # 3. Saludo inicial
        try:
            saludo = agente.iniciar_conversacion()
            tracker.emit("BRUCE_RESPONDE", {"texto": saludo})
            if self.verbose:
                print(f"    Bruce: {saludo}")
        except Exception as e:
            print(f"    [ERROR] iniciar_conversacion: {e}")

        # 4. Reproducir mensajes del cliente
        # FIX 840: Detectar farewell para detener replay (en produccion Twilio cuelga)
        _farewell_phrases = [
            'muchas gracias por su tiempo', 'que tenga excelente dia',
            'que tenga buen dia', 'hasta pronto', 'hasta luego',
        ]
        call_ended = False

        respuestas_replay = []
        for i, msg in enumerate(client_messages):
            if call_ended:
                if self.verbose:
                    print(f"    [FIX 840] Llamada terminada - ignorando turno {i+1}")
                break

            tracker.emit("CLIENTE_DICE", {"texto": msg})

            if self.verbose:
                print(f"    Cliente [{i+1}]: {msg}")

            try:
                respuesta = agente.procesar_respuesta(msg)
                if not respuesta:
                    respuesta = ""
            except Exception as e:
                respuesta = f"[ERROR: {e}]"
                if self.verbose:
                    print(f"    [ERROR] turno {i+1}: {e}")

            tracker.emit("BRUCE_RESPONDE", {"texto": respuesta})
            respuestas_replay.append(respuesta)

            if self.verbose:
                print(f"    Bruce [{i+1}]: {respuesta}")

            # FIX 840: Detectar si Bruce se despidio (en produccion aqui se cuelga)
            resp_lower = respuesta.lower()
            if any(fp in resp_lower for fp in _farewell_phrases):
                call_ended = True

        # 5. Detectar bugs del replay
        duracion = time.time() - t0
        bugs_replay = BugDetector.analyze(tracker)

        # FIX 901: GPT eval en replay (mismo detector que produccion)
        if self.gpt_eval and len(tracker.respuestas_bruce) >= 2:
            try:
                from bug_detector import _evaluar_con_gpt
                gpt_bugs = _evaluar_con_gpt(tracker)
                if gpt_bugs:
                    bugs_replay.extend(gpt_bugs)
                    print(f"    [GPT EVAL] {len(gpt_bugs)} bug(s) detectado(s) por GPT")
            except Exception as e:
                print(f"    [GPT EVAL] Error: {e}")

        # 6. Comparar: original vs replay
        tipos_orig = set(b['tipo'] for b in bugs_original)
        tipos_replay = set(b['tipo'] for b in bugs_replay)

        fixed = tipos_orig - tipos_replay  # Bugs que YA NO aparecen
        new_bugs = tipos_replay - tipos_orig  # Bugs NUEVOS
        persistent = tipos_orig & tipos_replay  # Bugs que persisten

        # 7. Mostrar resultado
        if bugs_original:
            orig_str = ", ".join(f"{b['tipo']}({b['severidad']})" for b in bugs_original)
            print(f"    ORIGINAL: {orig_str}")
        else:
            print(f"    ORIGINAL: sin bugs")

        if bugs_replay:
            replay_str = ", ".join(f"{b['tipo']}({b['severidad']})" for b in bugs_replay)
            print(f"    REPLAY:   {replay_str}")
        else:
            print(f"    REPLAY:   sin bugs")

        # Resumen diferencial
        if fixed:
            print(f"    [FIXED]   {', '.join(sorted(fixed))}")
        if new_bugs:
            print(f"    [NUEVO]   {', '.join(sorted(new_bugs))}")
        if persistent:
            print(f"    [PERSISTE] {', '.join(sorted(persistent))}")
        if not fixed and not new_bugs and not persistent:
            print(f"    [LIMPIO]  Sin bugs antes ni despues")

        status = "MEJORADO" if fixed and not new_bugs else "LIMPIO" if not bugs_replay else "PENDIENTE"
        print(f"    [{status}] ({duracion:.1f}s)")

        resultado = {
            'bruce_id': bruce_id,
            'negocio': negocio,
            'bugs_original': bugs_original,
            'bugs_replay': bugs_replay,
            'fixed': list(fixed),
            'new_bugs': list(new_bugs),
            'persistent': list(persistent),
            'duracion': duracion,
            'n_turnos': len(client_messages),
        }
        self.resultados.append(resultado)
        return resultado

    def run(self, conversations, bruce_ids=None, latest_n=None, bugs_only=False):
        """Ejecuta replay de multiples llamadas."""
        print("=" * 65)
        print("  LOG REPLAY - Reproduccion de llamadas reales")
        print("=" * 65)

        # Filtrar conversaciones validas (con al menos 2 turnos de cliente)
        valid = {bid: c for bid, c in conversations.items()
                 if len(get_client_messages(c)) >= 2}

        if bruce_ids:
            valid = {bid: c for bid, c in valid.items() if bid in bruce_ids}
        if bugs_only:
            valid = {bid: c for bid, c in valid.items() if c.get('bugs_original')}

        # Ordenar por BRUCE ID numerico (mas recientes primero)
        sorted_ids = sorted(valid.keys(),
                           key=lambda x: int(re.search(r'\d+', x).group()) if re.search(r'\d+', x) else 0,
                           reverse=True)

        if latest_n:
            sorted_ids = sorted_ids[:latest_n]

        if not sorted_ids:
            print("\n  No se encontraron llamadas para reproducir.")
            return False

        print(f"\n  Llamadas a reproducir: {len(sorted_ids)}")
        if bugs_only:
            print(f"  (filtro: solo con bugs)")

        total = len(sorted_ids)
        for i, bid in enumerate(sorted_ids, 1):
            self.replay_call(bid, valid[bid], call_index=i, total_calls=total)

        # ============================================================
        # Resumen final
        # ============================================================
        print("\n" + "=" * 65)
        print("  RESUMEN LOG REPLAY")
        print("=" * 65)

        total_replayed = len(self.resultados)
        total_orig_bugs = sum(len(r['bugs_original']) for r in self.resultados)
        total_replay_bugs = sum(len(r['bugs_replay']) for r in self.resultados)
        total_fixed = sum(len(r['fixed']) for r in self.resultados)
        total_new = sum(len(r['new_bugs']) for r in self.resultados)

        print(f"\n  Llamadas reproducidas: {total_replayed}")
        print(f"  Bugs originales:      {total_orig_bugs}")
        print(f"  Bugs en replay:       {total_replay_bugs}")

        if total_orig_bugs > 0:
            reduction = ((total_orig_bugs - total_replay_bugs) / total_orig_bugs) * 100
            print(f"  Reduccion:            {reduction:+.1f}%")

        if total_fixed:
            print(f"\n  BUGS CORREGIDOS ({total_fixed}):")
            fixed_counter = Counter()
            for r in self.resultados:
                for f in r['fixed']:
                    fixed_counter[f] += 1
            for tipo, count in fixed_counter.most_common():
                print(f"    {tipo}: {count}x")

        if total_new:
            print(f"\n  BUGS NUEVOS ({total_new}):")
            new_counter = Counter()
            for r in self.resultados:
                for n in r['new_bugs']:
                    new_counter[n] += 1
            for tipo, count in new_counter.most_common():
                print(f"    {tipo}: {count}x")

        persistent_counter = Counter()
        for r in self.resultados:
            for p in r['persistent']:
                persistent_counter[p] += 1
        if persistent_counter:
            print(f"\n  BUGS PERSISTENTES:")
            for tipo, count in persistent_counter.most_common():
                print(f"    {tipo}: {count}x")

        total_tiempo = sum(r['duracion'] for r in self.resultados)
        print(f"\n  Tiempo total: {total_tiempo:.1f}s")
        print(f"  Costo estimado: ~${total_replayed * 0.01:.2f} USD (GPT-4.1-mini)")

        return total_replay_bugs <= total_orig_bugs


def list_available_calls(conversations, bugs_only=False):
    """Lista las llamadas disponibles."""
    valid = {bid: c for bid, c in conversations.items()
             if len(get_client_messages(c)) >= 2}
    if bugs_only:
        valid = {bid: c for bid, c in valid.items() if c.get('bugs_original')}

    sorted_ids = sorted(valid.keys(),
                       key=lambda x: int(re.search(r'\d+', x).group()) if re.search(r'\d+', x) else 0,
                       reverse=True)

    print(f"\nLlamadas disponibles: {len(sorted_ids)}" + (" (con bugs)" if bugs_only else ""))
    print("-" * 80)

    for bid in sorted_ids[:50]:  # Limitar a 50
        c = valid[bid]
        negocio = c.get('negocio') or '?'
        n_client = len(get_client_messages(c))
        n_bugs = len(c.get('bugs_original', []))
        bugs_str = ", ".join(b['tipo'] for b in c.get('bugs_original', []))[:60]
        src = c.get('source_file', '?')

        if n_bugs:
            print(f"  {bid} | {negocio[:30]:<30} | {n_client}t | {n_bugs} bugs: {bugs_str} | {src}")
        else:
            print(f"  {bid} | {negocio[:30]:<30} | {n_client}t | limpio | {src}")

    if len(sorted_ids) > 50:
        print(f"  ... y {len(sorted_ids) - 50} mas")


def main():
    parser = argparse.ArgumentParser(description="Log Replay Simulator - Bruce W")
    parser.add_argument("--verbose", "-v", action="store_true", help="Mostrar conversaciones completas")
    parser.add_argument("--bruce", "-b", nargs="+", help="BRUCE IDs especificos (ej: BRUCE2549 BRUCE2551)")
    parser.add_argument("--file", "-f", help="Archivo de log especifico (ej: 25_02PT15.txt)")
    parser.add_argument("--latest", "-n", type=int, help="Ultimas N llamadas")
    parser.add_argument("--bugs-only", action="store_true", help="Solo llamadas con bugs originales")
    parser.add_argument("--list", "-l", action="store_true", help="Listar llamadas disponibles")
    parser.add_argument("--gpt-eval", action="store_true", help="FIX 901: Ejecutar GPT eval (mismo que produccion)")
    args = parser.parse_args()

    # Parse logs
    print("Parseando logs...")
    if args.file:
        filepath = os.path.join(LOGS_DIR, args.file) if not os.path.isabs(args.file) else args.file
        if not os.path.exists(filepath):
            print(f"Error: {filepath} no existe")
            sys.exit(1)
        conversations = parse_log_file(filepath)
    else:
        conversations = parse_all_logs()

    print(f"Conversaciones encontradas: {len(conversations)}")

    # Listar
    if args.list:
        list_available_calls(conversations, bugs_only=args.bugs_only)
        return

    # Defaults: si no se especifica nada, replay ultimas 5 con bugs
    bruce_ids = args.bruce
    latest_n = args.latest
    bugs_only = args.bugs_only

    if not bruce_ids and not latest_n:
        latest_n = 5
        bugs_only = True
        print("(default: ultimas 5 llamadas con bugs)")

    sim = LogReplaySimulator(verbose=args.verbose, gpt_eval=getattr(args, "gpt_eval", False))
    success = sim.run(
        conversations,
        bruce_ids=bruce_ids,
        latest_n=latest_n,
        bugs_only=bugs_only,
    )
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
