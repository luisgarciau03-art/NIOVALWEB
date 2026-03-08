"""
Auditoría masiva: escanear TODOS los logs en LOGS/ con bug_detector + GPT eval.
Detecta TODOS los tipos de bug: rule-based + GPT.
"""
import os
import sys
import re
import json
import time
from collections import Counter, defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from bug_detector import BugDetector, CallEventTracker, ContentAnalyzer, _evaluar_con_gpt


def parse_all_logs(logs_dir):
    """Parse ALL log files and extract conversations + metadata."""
    log_files = sorted([f for f in os.listdir(logs_dir)
                       if f.endswith('.txt') and re.match(r'\d{2}_\d{2}PT', f)])
    print(f"Archivos de log: {len(log_files)}")

    all_convs = {}

    for lf in log_files:
        filepath = os.path.join(logs_dir, lf)
        date_match = re.match(r'(\d{2}_\d{2})', lf)
        file_date = date_match.group(1) if date_match else 'unknown'

        try:
            with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read()
        except Exception:
            continue

        # Extract [BRUCE] BRUCEXXXX DICE: "text"
        bruce_pattern = re.compile(
            r'\[BRUCE\]\s+(BRUCE\d+)\s+DICE:\s*"(.+?)"', re.DOTALL
        )
        # Extract [CLIENTE] BRUCEXXXX - CLIENTE DIJO: "text"
        cliente_pattern = re.compile(
            r'\[CLIENTE\]\s+(BRUCE\d+)\s+-\s+CLIENTE DIJO:\s*"(.+?)"', re.DOTALL
        )

        # Find all matches with positions
        events = []
        for m in bruce_pattern.finditer(content):
            bruce_id = m.group(1)
            text = m.group(2).strip()
            if text:
                events.append((m.start(), bruce_id, 'bruce', text))

        for m in cliente_pattern.finditer(content):
            bruce_id = m.group(1)
            text = m.group(2).strip()
            if text and len(text) > 1:
                events.append((m.start(), bruce_id, 'cliente', text))

        events.sort(key=lambda x: x[0])

        for _, bruce_id, role, text in events:
            if bruce_id not in all_convs:
                all_convs[bruce_id] = {
                    'turns': [],
                    'source': lf,
                    'date': file_date,
                    'twiml_count': 0,
                    'filler_count': 0,
                }
            all_convs[bruce_id]['turns'].append((role, text))

        # Extract metadata per BRUCE ID
        # TwiML count
        for m in re.finditer(r'\[BRUCE\]\s+(BRUCE\d+)', content):
            bid = m.group(1)
            if bid in all_convs:
                all_convs[bid]['twiml_count'] += 1

        # Filler count (FILLER_162A or TTS fallo)
        for m in re.finditer(r'(BRUCE\d+).*(?:FILLER_162A|filler.*hardcoded|audio.*dejeme_ver)', content):
            bid = m.group(1)
            if bid in all_convs:
                all_convs[bid]['filler_count'] += 1

    return all_convs


def build_tracker(bruce_id, data):
    """Build a CallEventTracker with TUPLE format for conversacion."""
    tracker = CallEventTracker(
        call_sid=f"CA_audit_{bruce_id}",
        bruce_id=bruce_id,
        telefono=""
    )
    tracker.created_at = time.time() - 120  # Simulate 2min call

    # CRITICAL: conversacion must be list of tuples (role, text)
    # where role is "bruce" or "cliente"
    conv = []
    for role, text in data.get('turns', []):
        conv.append((role, text))
        if role == 'bruce':
            tracker.respuestas_bruce.append(text)
        else:
            tracker.textos_cliente.append(text)

    tracker.conversacion = conv
    tracker.turnos = len([t for t in data.get('turns', []) if t[0] == 'bruce'])

    # Set metadata
    tracker.twiml_count = data.get('twiml_count', 0)
    tracker.audio_fetch_count = tracker.twiml_count  # Assume all fetched (no BRUCE_MUDO)
    tracker.filler_162a_count = data.get('filler_count', 0)

    return tracker


def main():
    logs_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'LOGS')
    if not os.path.exists(logs_dir):
        print(f"ERROR: {logs_dir} no existe")
        return

    # Check for OpenAI API key
    from dotenv import load_dotenv
    load_dotenv()
    tiene_openai = bool(os.environ.get('OPENAI_API_KEY', ''))
    print(f"GPT eval disponible: {tiene_openai}")

    # Parse all logs
    all_convs = parse_all_logs(logs_dir)
    print(f"Conversaciones totales: {len(all_convs)}")

    # Filter: at least 3 turns with both roles
    valid_convs = {}
    for bruce_id, data in all_convs.items():
        has_bruce = any(r == 'bruce' for r, _ in data['turns'])
        has_cliente = any(r == 'cliente' for r, _ in data['turns'])
        if has_bruce and has_cliente and len(data['turns']) >= 3:
            valid_convs[bruce_id] = data

    print(f"Conversaciones válidas (3+ turnos): {len(valid_convs)}")

    # Analyze
    detector = BugDetector()
    bug_counter = Counter()
    bug_examples = defaultdict(list)
    bug_severity = defaultdict(Counter)
    calls_with_bugs = 0
    calls_clean = 0
    bugs_by_date = defaultdict(lambda: Counter())
    calls_by_date = defaultdict(int)

    gpt_calls = 0
    gpt_errors = 0

    sorted_ids = sorted(valid_convs.keys(), key=lambda x: int(x.replace('BRUCE', '')))
    total_to_process = len(sorted_ids)

    for idx, bruce_id in enumerate(sorted_ids):
        data = valid_convs[bruce_id]
        tracker = build_tracker(bruce_id, data)
        date = data.get('date', 'unknown')
        calls_by_date[date] += 1

        # Progress every 50 calls
        if (idx + 1) % 50 == 0:
            print(f"  Procesando {idx+1}/{total_to_process}...")

        all_bugs = []

        # 1. Rule-based bugs (BugDetector + ContentAnalyzer)
        try:
            rule_bugs = detector.analyze(tracker)
            all_bugs.extend(rule_bugs)
        except Exception:
            pass

        # 2. GPT eval bugs (if API key available)
        if tiene_openai and len(tracker.respuestas_bruce) >= 2:
            try:
                gpt_bugs = _evaluar_con_gpt(tracker)
                all_bugs.extend(gpt_bugs)
                gpt_calls += 1
            except Exception as e:
                gpt_errors += 1

        if all_bugs:
            calls_with_bugs += 1
            for bug in all_bugs:
                bug_type = bug.get('tipo', bug.get('type', 'UNKNOWN'))
                severity = bug.get('severidad', bug.get('severity', 'MEDIO'))
                bug_counter[bug_type] += 1
                bug_severity[bug_type][severity] += 1

                detail = bug.get('detalle', bug.get('detail', ''))[:100]
                if len(bug_examples[bug_type]) < 5:
                    bug_examples[bug_type].append({
                        'bruce_id': bruce_id,
                        'detail': detail,
                        'date': date,
                        'turnos': len(data['turns'])
                    })

                bugs_by_date[date][bug_type] += 1
        else:
            calls_clean += 1

    total = calls_with_bugs + calls_clean
    total_bugs = sum(bug_counter.values())

    # Print report
    print("\n" + "=" * 70)
    print(f"  AUDITORÍA MASIVA COMPLETA")
    print(f"  Llamadas analizadas: {total}")
    print(f"  Con bugs: {calls_with_bugs} ({calls_with_bugs*100/max(total,1):.1f}%)")
    print(f"  Limpias:  {calls_clean} ({calls_clean*100/max(total,1):.1f}%)")
    print(f"  Total bugs: {total_bugs}")
    print(f"  Bugs/llamada: {total_bugs/max(total,1):.2f}")
    if tiene_openai:
        print(f"  GPT eval: {gpt_calls} llamadas, {gpt_errors} errores")
    print("=" * 70)

    print("\n--- TODOS LOS BUGS POR FRECUENCIA ---\n")
    print(f"  {'Tipo':<40s} {'Total':>5s}  {'ALTO':>4s}  {'MEDIO':>5s}  Ejemplos")
    print(f"  {'-'*40} {'-'*5}  {'-'*4}  {'-'*5}  {'-'*30}")
    for bug_type, count in bug_counter.most_common(30):
        alto = bug_severity[bug_type].get('ALTO', 0) + bug_severity[bug_type].get('CRITICO', 0)
        medio = bug_severity[bug_type].get('MEDIO', 0)
        examples = bug_examples[bug_type][:3]
        ex_str = ", ".join(e['bruce_id'] for e in examples)
        print(f"  {bug_type:<40s} {count:5d}  {alto:4d}  {medio:5d}  {ex_str}")

    print("\n--- TENDENCIA POR FECHA ---\n")
    print(f"  {'Fecha':<8s} {'Calls':>5s} {'Bugs':>5s} {'B/C':>5s}  Top bugs")
    print(f"  {'-'*8} {'-'*5} {'-'*5} {'-'*5}  {'-'*40}")
    for date in sorted(bugs_by_date.keys()):
        n_calls = calls_by_date[date]
        n_bugs = sum(bugs_by_date[date].values())
        bpc = n_bugs / max(n_calls, 1)
        top3 = bugs_by_date[date].most_common(3)
        top_str = ", ".join(f"{t}({c})" for t, c in top3)
        print(f"  {date:<8s} {n_calls:5d} {n_bugs:5d} {bpc:5.2f}  {top_str}")

    # Save JSON
    report = {
        'summary': {
            'calls_total': total,
            'calls_with_bugs': calls_with_bugs,
            'calls_clean': calls_clean,
            'total_bugs': total_bugs,
            'bugs_per_call': round(total_bugs / max(total, 1), 2),
            'gpt_eval_calls': gpt_calls,
            'gpt_eval_errors': gpt_errors,
        },
        'bug_counts': dict(bug_counter.most_common()),
        'bug_examples': {k: v for k, v in bug_examples.items()},
        'bugs_by_date': {k: dict(v) for k, v in bugs_by_date.items()},
        'calls_by_date': dict(calls_by_date),
    }

    report_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'audit_masivo_resultado.json')
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print(f"\nReporte JSON: {report_path}")


if __name__ == '__main__':
    main()
