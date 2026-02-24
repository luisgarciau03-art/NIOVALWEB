"""
Orquestador del ciclo de auditoria por lotes para Bruce W.

Workflow:
  1. Descargar datos de produccion (bugs, patterns, logs)
  2. Identificar logs nuevos (no procesados previamente)
  3. Parsear logs -> extraer conversaciones y bugs
  4. Ejecutar suite de regresion
  5. Generar reporte Excel con resultados del lote
  6. Mostrar resumen con proximos pasos

El historial evita procesar el mismo log dos veces.
Cada ejecucion = 1 lote en el Excel.

Uso:
  python scripts/batch_audit.py                          # Auditoria completa (manual)
  python scripts/batch_audit.py --monitor                # Auto-monitor (default 25 llamadas)
  python scripts/batch_audit.py --monitor --batch-size 10 # Auto cada 10 llamadas
  python scripts/batch_audit.py --monitor --batch-size 5  # Auto cada 5 llamadas
  python scripts/batch_audit.py --monitor --reset         # Reiniciar conteo desde cero
  python scripts/batch_audit.py --skip-download          # Usar datos locales
  python scripts/batch_audit.py --skip-regression        # Sin tests de regresion
  python scripts/batch_audit.py --only-report            # Solo regenerar Excel
  python scripts/batch_audit.py --status                 # Ver estado actual
"""

import os
import sys
import re
import json
import time
import subprocess
import requests
from datetime import datetime

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS_DIR = os.path.join(PROJECT_DIR, 'scripts')
LOGS_DIR = os.path.join(PROJECT_DIR, 'LOGS')
AUDIT_DATA_DIR = os.path.join(PROJECT_DIR, 'audit_data')
TESTS_DIR = os.path.join(PROJECT_DIR, 'tests')
TEST_DATA_DIR = os.path.join(TESTS_DIR, 'test_data')
MONITOR_STATE_PATH = os.path.join(AUDIT_DATA_DIR, 'monitor_state.json')
SERVER_URL = "https://nioval-webhook-server-production.up.railway.app"

sys.path.insert(0, PROJECT_DIR)
sys.path.insert(0, SCRIPTS_DIR)


def _ensure_dirs():
    for d in [AUDIT_DATA_DIR, LOGS_DIR, TEST_DATA_DIR]:
        os.makedirs(d, exist_ok=True)


def _run(cmd, description, timeout=300):
    """Ejecuta comando y retorna (success, output)."""
    print(f"  > {description}...", end=' ', flush=True)
    try:
        result = subprocess.run(
            cmd, cwd=PROJECT_DIR, capture_output=True, text=True,
            timeout=timeout, encoding='utf-8', errors='replace',
        )
        output = (result.stdout or '') + (result.stderr or '')
        ok = result.returncode == 0
        print("OK" if ok else f"WARN (exit {result.returncode})")
        return ok, output
    except subprocess.TimeoutExpired:
        print(f"TIMEOUT ({timeout}s)")
        return False, f"Timeout {timeout}s"
    except Exception as e:
        print(f"ERROR: {e}")
        return False, str(e)


# ============================================================
# PASO 1: Descargar datos de producción
# ============================================================

def step_download_production_data():
    """Descarga datos de todos los endpoints de producción."""
    print("\n[1/5] DESCARGANDO DATOS DE PRODUCCIÓN\n")

    from production_data_fetcher import fetch_all, get_production_summary, download_new_logs

    # Descargar endpoints
    results = fetch_all()
    summary = get_production_summary(results)

    # Descargar logs nuevos
    print("\n  Descargando logs nuevos de Railway...")
    new_logs = download_new_logs()
    summary['new_logs_downloaded'] = new_logs

    return summary


# ============================================================
# PASO 2: Identificar logs no procesados
# ============================================================

def step_identify_new_logs():
    """Identifica logs que no han sido procesados en auditorías previas."""
    print("\n[2/5] IDENTIFICANDO LOGS NUEVOS\n")

    from batch_report_excel import load_batch_history

    history = load_batch_history()
    processed = set(history.get('logs_processed', {}).keys())

    all_logs = []
    if os.path.isdir(LOGS_DIR):
        all_logs = sorted([f for f in os.listdir(LOGS_DIR) if f.endswith('.txt')])

    new_logs = [f for f in all_logs if f not in processed]

    print(f"  Total logs en disco: {len(all_logs)}")
    print(f"  Ya procesados: {len(processed)}")
    print(f"  Nuevos por procesar: {len(new_logs)}")

    if new_logs:
        print(f"  Archivos nuevos:")
        for f in new_logs[:15]:
            filepath = os.path.join(LOGS_DIR, f)
            size = os.path.getsize(filepath) if os.path.exists(filepath) else 0
            print(f"    {f} ({size:,} bytes)")
        if len(new_logs) > 15:
            print(f"    ... y {len(new_logs)-15} más")

    return new_logs


# ============================================================
# PASO 3: Parsear logs y extraer bugs
# ============================================================

def _fetch_bugs_from_server(bruce_ids):
    """Consulta /bugs endpoint para obtener bugs de BRUCE IDs especificos.

    Esta es la fuente MAS CONFIABLE de bugs (base de datos del servidor).
    """
    bugs_by_bruce = {}
    try:
        resp = requests.get(f"{SERVER_URL}/bugs", timeout=15)
        resp.raise_for_status()
        text = resp.text

        # Parsear HTML del endpoint /bugs
        # Formato: BRUCE#### ... tipo ... severidad ... detalle
        for bid in bruce_ids:
            bid_str = bid if bid.startswith('BRUCE') else f'BRUCE{bid}'
            # Buscar bloques de este BRUCE ID
            pattern = re.compile(
                rf'{re.escape(bid_str)}\s+.*?'
                rf'(GPT_\w+|\w+)\s+'
                rf'(CRITICO|ALTO|MEDIO|BAJO)\s+'
                rf'\[turno \d+\]\s*(.*?)(?=\d+t\s*/|\Z)',
                re.DOTALL
            )
            for m in pattern.finditer(text):
                if bid_str not in bugs_by_bruce:
                    bugs_by_bruce[bid_str] = []
                bugs_by_bruce[bid_str].append({
                    'tipo': m.group(1).strip(),
                    'severidad': m.group(2).strip(),
                    'detalle': re.sub(r'\s+', ' ', m.group(3)).strip()[:200],
                    'source': 'server_bugs',
                })
    except Exception:
        pass

    # Fallback: parsear con regex mas simple si el formato es diferente
    if not bugs_by_bruce:
        try:
            text_clean = re.sub(r'<[^>]+>', ' ', text)
            text_clean = re.sub(r'\s+', ' ', text_clean)
            for bid in bruce_ids:
                bid_str = bid if bid.startswith('BRUCE') else f'BRUCE{bid}'
                # Buscar: BRUCE#### ... TIPO SEVERIDAD [turno N] detalle
                chunks = text_clean.split(bid_str)
                for i, chunk in enumerate(chunks[1:], 1):
                    # Extraer tipo y severidad del chunk
                    m = re.search(
                        r'(GPT_\w+|\w+)\s+(CRITICO|ALTO|MEDIO|BAJO)\s+(.+?)(?=BRUCE\d{4}|\Z)',
                        chunk[:500]
                    )
                    if m:
                        if bid_str not in bugs_by_bruce:
                            bugs_by_bruce[bid_str] = []
                        bugs_by_bruce[bid_str].append({
                            'tipo': m.group(1).strip(),
                            'severidad': m.group(2).strip(),
                            'detalle': m.group(3).strip()[:200],
                            'source': 'server_bugs',
                        })
        except Exception:
            pass

    return bugs_by_bruce


def step_parse_logs(log_files):
    """Parsea logs nuevos, extrae conversaciones y bugs.

    Usa DOS fuentes de bugs:
    1. Parseo de archivos de log (lineas [BUG_DETECTOR], [ALTO], [GPT ALTO])
    2. Consulta directa al endpoint /bugs del servidor (fuente principal)

    Returns:
        dict con metricas del parseo
    """
    print("\n[3/5] PARSEANDO LOGS Y EXTRAYENDO BUGS\n")

    if not log_files:
        print("  No hay logs nuevos para parsear")
        return {
            'total_conversations': 0,
            'total_bugs': 0,
            'bruce_ids': [],
            'bugs_detalle': [],
            'bugs_por_tipo': {},
            'calificaciones': [],
        }

    # Usar log_scenario_extractor para parsear (genera scenario_db.json)
    extractor_path = os.path.join(SCRIPTS_DIR, 'log_scenario_extractor.py')
    if os.path.exists(extractor_path):
        ok, output = _run(
            [sys.executable, extractor_path],
            "Ejecutando log_scenario_extractor",
            timeout=120,
        )

    # Parsear logs directamente para metricas del lote
    metrics = {
        'total_conversations': 0,
        'total_bugs': 0,
        'bruce_ids': [],
        'bugs_detalle': [],
        'bugs_por_tipo': {},
        'calificaciones': [],
        'total_llamadas': 0,
    }

    # Regex patterns
    RE_BRUCE_CONV = re.compile(r'\[(?:CLIENTE|BRUCE)\]\s*(BRUCE\d+)')
    RE_BUG_HEADER = re.compile(r'\[BUG_DETECTOR\]\s*(BRUCE\d+):\s*(\d+)\s*bug')
    RE_BUG_RULE = re.compile(r'\[(CRITICO|ALTO|MEDIO|BAJO)\]\s*(\w+):\s*(.*)')
    RE_BUG_GPT = re.compile(r'\[GPT\s+(CRITICO|ALTO|MEDIO|BAJO)\]\s*(GPT_\w+):\s*(.*)')
    RE_CALIFICACION = re.compile(r'Calificaci[oó]n Bruce:\s*(\d+)/10')

    all_bruce_ids = set()
    last_bug_bruce_id = None
    seen_bugs = set()  # Deduplicar bugs

    for log_file in log_files:
        filepath = os.path.join(LOGS_DIR, log_file)
        if not os.path.exists(filepath):
            continue

        try:
            with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read()
        except Exception as e:
            print(f"  [!] Error leyendo {log_file}: {e}")
            continue

        # Limpiar HTML residual
        content = re.sub(r'<[^>]+>', '\n', content)

        # Extraer BRUCE IDs de conversaciones (solo CLIENTE/BRUCE dice)
        for m in RE_BRUCE_CONV.finditer(content):
            all_bruce_ids.add(m.group(1))

        # Parsear linea por linea para asociacion correcta de bugs
        for line in content.split('\n'):
            line = line.strip()
            if not line:
                continue

            # Bug detector header: establece BRUCE ID para bugs siguientes
            m = RE_BUG_HEADER.search(line)
            if m:
                last_bug_bruce_id = m.group(1)
                continue

            # Bug rule-based: [ALTO] TIPO: detalle
            m = RE_BUG_RULE.search(line)
            if m and last_bug_bruce_id:
                sev, tipo, detalle = m.group(1), m.group(2), m.group(3).strip()
                bug_key = f"{last_bug_bruce_id}_{tipo}_{detalle[:50]}"
                if bug_key not in seen_bugs:
                    seen_bugs.add(bug_key)
                    metrics['bugs_detalle'].append({
                        'bruce_id': last_bug_bruce_id,
                        'tipo': tipo,
                        'severidad': sev,
                        'detalle': detalle[:200],
                        'source': 'log_rule',
                    })
                    metrics['bugs_por_tipo'][tipo] = metrics['bugs_por_tipo'].get(tipo, 0) + 1
                    metrics['total_bugs'] += 1
                continue

            # Bug GPT eval: [GPT ALTO] GPT_TIPO: detalle
            m = RE_BUG_GPT.search(line)
            if m and last_bug_bruce_id:
                sev, tipo, detalle = m.group(1), m.group(2), m.group(3).strip()
                bug_key = f"{last_bug_bruce_id}_{tipo}_{detalle[:50]}"
                if bug_key not in seen_bugs:
                    seen_bugs.add(bug_key)
                    metrics['bugs_detalle'].append({
                        'bruce_id': last_bug_bruce_id,
                        'tipo': tipo,
                        'severidad': sev,
                        'detalle': detalle[:200],
                        'source': 'log_gpt',
                    })
                    metrics['bugs_por_tipo'][tipo] = metrics['bugs_por_tipo'].get(tipo, 0) + 1
                    metrics['total_bugs'] += 1
                continue

            # Calificacion
            m = RE_CALIFICACION.search(line)
            if m:
                metrics['calificaciones'].append(int(m.group(1)))

    bugs_from_logs = metrics['total_bugs']

    # === FUENTE 2: Consultar /bugs endpoint del servidor ===
    print(f"  > Consultando /bugs endpoint...")
    server_bugs = _fetch_bugs_from_server(all_bruce_ids)
    bugs_added_from_server = 0
    for bid, bugs in server_bugs.items():
        for bug in bugs:
            bug_key = f"{bid}_{bug['tipo']}_{bug['detalle'][:50]}"
            if bug_key not in seen_bugs:
                seen_bugs.add(bug_key)
                metrics['bugs_detalle'].append({
                    'bruce_id': bid,
                    'tipo': bug['tipo'],
                    'severidad': bug['severidad'],
                    'detalle': bug['detalle'],
                    'source': 'server_bugs',
                })
                metrics['bugs_por_tipo'][bug['tipo']] = metrics['bugs_por_tipo'].get(bug['tipo'], 0) + 1
                metrics['total_bugs'] += 1
                bugs_added_from_server += 1

    metrics['bruce_ids'] = sorted(all_bruce_ids)
    metrics['total_llamadas'] = len(all_bruce_ids)
    metrics['total_conversations'] = len(all_bruce_ids)

    print(f"  Conversaciones encontradas: {metrics['total_conversations']}")
    print(f"  BRUCE IDs: {len(metrics['bruce_ids'])}")
    print(f"  Bugs de logs: {bugs_from_logs}")
    if bugs_added_from_server:
        print(f"  Bugs de /bugs endpoint: +{bugs_added_from_server}")
    print(f"  Bugs TOTAL: {metrics['total_bugs']}")
    if metrics['bugs_por_tipo']:
        print(f"  Por tipo:")
        for tipo, count in sorted(metrics['bugs_por_tipo'].items(), key=lambda x: -x[1])[:10]:
            print(f"    {tipo}: {count}")
    if metrics['calificaciones']:
        avg = sum(metrics['calificaciones']) / len(metrics['calificaciones'])
        print(f"  Calificacion promedio: {avg:.1f}/10")
        metrics['calificacion_promedio'] = round(avg, 1)
    else:
        metrics['calificacion_promedio'] = 0

    return metrics


# ============================================================
# PASO 4: Ejecutar suite de regresión
# ============================================================

def step_run_regression():
    """Ejecuta la suite de regresión automatizada.

    Returns:
        dict con resultados
    """
    print("\n[4/5] EJECUTANDO SUITE DE REGRESIÓN\n")

    regression_script = os.path.join(SCRIPTS_DIR, 'run_regression_suite.py')
    if not os.path.exists(regression_script):
        print("  [!] run_regression_suite.py no encontrado, saltando")
        return {'pass_rate': 0, 'passed': 0, 'failed': 0, 'errors': 0}

    ok, output = _run(
        [sys.executable, regression_script, '--skip-parse', '--quick'],
        "Suite de regresión (--quick)",
        timeout=600,
    )

    # Parsear resultados
    results = {'pass_rate': 0, 'passed': 0, 'failed': 0, 'errors': 0, 'output': ''}

    m_total = re.search(r'TOTAL:\s*(\d+)/(\d+)\s*PASS\s*\((\d+\.?\d*)%\)', output)
    if m_total:
        results['passed'] = int(m_total.group(1))
        total = int(m_total.group(2))
        results['pass_rate'] = float(m_total.group(3))
        results['failed'] = total - results['passed']

    # Buscar reporte JSON
    report_path = os.path.join(TEST_DATA_DIR, 'regression_report.json')
    if os.path.exists(report_path):
        try:
            with open(report_path, 'r', encoding='utf-8') as f:
                report = json.load(f)
            results['passed'] = report.get('total_passed', results['passed'])
            results['failed'] = report.get('total_failed', results['failed'])
            results['errors'] = report.get('total_errors', 0)
            results['pass_rate'] = report.get('pass_rate', results['pass_rate'])
        except Exception:
            pass

    print(f"  Resultado: {results['passed']} PASS, {results['failed']} FAIL")
    print(f"  Pass rate: {results['pass_rate']:.1f}%")

    return results


# ============================================================
# PASO 5: Generar reporte
# ============================================================

def step_generate_report(log_files, parse_metrics, regression_results, prod_summary):
    """Genera reporte Excel y registra el lote.

    Returns:
        (batch_num, excel_path)
    """
    print("\n[5/5] GENERANDO REPORTE\n")

    from batch_report_excel import add_batch, generate_excel, load_batch_history

    # Calcular métricas de conversión desde production summary
    conversion_rate = 0
    # TODO: Extraer de historial-llamadas si disponible

    # Armar resultado del lote
    audit_result = {
        'total_llamadas': parse_metrics.get('total_llamadas', 0),
        'bruce_ids': parse_metrics.get('bruce_ids', []),
        'bugs_total': parse_metrics.get('total_bugs', 0),
        'bugs_criticos': sum(
            1 for b in parse_metrics.get('bugs_detalle', [])
            if b.get('severidad') == 'CRITICO'
        ),
        'bugs_por_tipo': parse_metrics.get('bugs_por_tipo', {}),
        'bugs_detalle': parse_metrics.get('bugs_detalle', []),
        'calificacion_promedio': parse_metrics.get('calificacion_promedio', 0),
        'conversion_rate': conversion_rate,
        'regression_pass_rate': regression_results.get('pass_rate', 0),
        'logs_procesados': log_files,
        'version_deploy': (prod_summary or {}).get('version', '')[:50] if prod_summary else '',
        'fix_aplicados': [],
        'notas': f"Auditoría automática {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        'endpoints_ok': sum(
            1 for v in (prod_summary or {}).get('endpoints_status', {}).values()
            if v == 'ok'
        ),
        'endpoints_total': len((prod_summary or {}).get('endpoints_status', {})),
    }

    # Agregar lote al historial
    batch_num = add_batch(audit_result)
    print(f"  Lote #{batch_num} registrado")

    # Generar Excel
    history = load_batch_history()
    excel_path = generate_excel(history)
    if excel_path:
        print(f"  Excel generado: {excel_path}")

    # Generar HTML (persistente - se actualiza cada auditoría)
    html_path = None
    try:
        from batch_report_html import generate_html
        html_path = generate_html(history)
        if html_path:
            print(f"  HTML generado: {html_path}")
    except Exception as e:
        print(f"  [!] Error generando HTML: {e}")

    return batch_num, excel_path


# ============================================================
# STATUS
# ============================================================

def show_status():
    """Muestra estado actual del sistema de auditoría."""
    print(f"\n{'='*60}")
    print(f"  ESTADO DEL SISTEMA DE AUDITORÍA")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}\n")

    # Logs
    all_logs = []
    if os.path.isdir(LOGS_DIR):
        all_logs = [f for f in os.listdir(LOGS_DIR) if f.endswith('.txt')]
    print(f"  Logs en disco: {len(all_logs)}")

    # Historial de lotes
    history_path = os.path.join(AUDIT_DATA_DIR, 'batch_history.json')
    if os.path.exists(history_path):
        with open(history_path, 'r', encoding='utf-8') as f:
            history = json.load(f)
        batches = history.get('batches', [])
        processed = history.get('logs_processed', {})
        unprocessed = [f for f in all_logs if f not in processed]

        print(f"  Lotes completados: {len(batches)}")
        print(f"  Logs procesados: {len(processed)}")
        print(f"  Logs pendientes: {len(unprocessed)}")

        if batches:
            last = batches[-1]
            print(f"\n  Último lote: #{last.get('lote')}")
            print(f"    Fecha: {last.get('timestamp', '')[:19]}")
            print(f"    Llamadas: {last.get('llamadas', 0)}")
            print(f"    Bugs: {last.get('bugs_total', 0)}")
            print(f"    Calificación: {last.get('calificacion_promedio', 0)}")
            print(f"    Regresión: {last.get('regression_pass_rate', 0):.1f}%")

        if len(batches) >= 2:
            print(f"\n  Tendencia (últimos 3 lotes):")
            for b in batches[-3:]:
                llamadas = max(b.get('llamadas', 1), 1)
                bug_rate = b.get('bugs_total', 0) / llamadas * 100
                print(f"    Lote #{b.get('lote')}: "
                      f"{b.get('bugs_total',0)} bugs ({bug_rate:.1f}%), "
                      f"cal={b.get('calificacion_promedio',0)}")
    else:
        print(f"  No hay historial de auditorías previas")
        print(f"  Logs pendientes: {len(all_logs)}")

    # Regression report
    report_path = os.path.join(TEST_DATA_DIR, 'regression_report.json')
    if os.path.exists(report_path):
        with open(report_path, 'r', encoding='utf-8') as f:
            report = json.load(f)
        print(f"\n  Última regresión:")
        print(f"    Fecha: {report.get('timestamp', '')[:19]}")
        print(f"    Pass rate: {report.get('pass_rate', 0)}%")
        print(f"    {report.get('total_passed',0)} PASS, {report.get('total_failed',0)} FAIL")

    # Excel
    excel_path = os.path.join(AUDIT_DATA_DIR, 'auditoria_bruce.xlsx')
    if os.path.exists(excel_path):
        size = os.path.getsize(excel_path)
        print(f"\n  Excel: {excel_path} ({size:,} bytes)")

    print(f"\n{'='*60}\n")


# ============================================================
# MONITOR: Auto-detecta llamadas nuevas y dispara auditoria
# ============================================================

def _load_monitor_state():
    """Carga estado del monitor."""
    if os.path.exists(MONITOR_STATE_PATH):
        try:
            with open(MONITOR_STATE_PATH, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            pass
    return {'last_bruce_id_seen': 0, 'calls_since_last_audit': 0, 'last_check': None}


def _save_monitor_state(state):
    """Guarda estado del monitor."""
    os.makedirs(AUDIT_DATA_DIR, exist_ok=True)
    with open(MONITOR_STATE_PATH, 'w', encoding='utf-8') as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def _get_all_bruce_ids():
    """Consulta el servidor y retorna TODOS los BRUCE IDs encontrados (set).

    FIX 804: Retorna set completo en vez de solo el max, para conteo preciso.
    """
    all_ids = set()

    # Fuente 1: /historial-llamadas (mas confiable, tiene TODOS los registros)
    try:
        resp = requests.get(f"{SERVER_URL}/historial-llamadas", timeout=15)
        resp.raise_for_status()
        ids = {int(x) for x in re.findall(r'BRUCE(\d+)', resp.text)}
        all_ids.update(ids)
    except Exception:
        pass

    # Fuente 2: /logs/api (tiene llamadas en curso que aun no estan en historial)
    try:
        resp = requests.get(f"{SERVER_URL}/logs/api?limite=500&formato=json", timeout=15)
        resp.raise_for_status()
        data = resp.json()
        logs_list = data.get('logs', []) if isinstance(data, dict) else data if isinstance(data, list) else []
        for line in logs_list:
            for m in re.findall(r'BRUCE(\d+)', str(line)):
                all_ids.add(int(m))
    except Exception:
        pass

    return all_ids


def _get_latest_bruce_id():
    """Consulta el servidor para obtener el BRUCE ID mas reciente."""
    all_ids = _get_all_bruce_ids()
    return max(all_ids) if all_ids else 0


def _count_new_calls(state):
    """Cuenta cuantas llamadas nuevas hay desde la ultima auditoria.

    FIX 804: Cuenta IDs reales > last_seen en vez de resta simple max - last_seen.
    Esto corrige deteccion incorrecta cuando IDs no son secuenciales o el monitor
    se inicia despues de que algunas llamadas ya ocurrieron.
    """
    all_ids = _get_all_bruce_ids()

    if not all_ids:
        return 0, 0

    current_max = max(all_ids)
    last_seen = state.get('last_bruce_id_seen', 0)

    if last_seen <= 0:
        # Primera vez - no contar las existentes como nuevas
        return 0, current_max

    # FIX 804: Contar IDs REALES mayores a last_seen (no resta simple)
    new_ids = {bid for bid in all_ids if bid > last_seen}
    return len(new_ids), current_max


def run_monitor(batch_size=25, interval_minutes=3, skip_regression=False):
    """Monitorea el servidor y ejecuta auditoria al acumular batch_size llamadas.

    Args:
        batch_size: Llamadas necesarias para disparar auditoria (5, 10, 25, 50...)
        interval_minutes: Minutos entre cada chequeo
        skip_regression: Saltear suite de regresion (mas rapido)
    """
    _ensure_dirs()
    state = _load_monitor_state()

    # Inicializar si es primera vez
    if state.get('last_bruce_id_seen', 0) == 0:
        _, current_max = _count_new_calls(state)
        state['last_bruce_id_seen'] = current_max
        state['calls_since_last_audit'] = 0
        _save_monitor_state(state)
        print(f"  Monitor inicializado. BRUCE ID actual: BRUCE{current_max}")
        print(f"  Las llamadas a partir de ahora se contaran como nuevas.\n")
    else:
        # FIX 804: Startup catch-up - detectar llamadas que ocurrieron mientras el monitor
        # estaba apagado y sumarlas al acumulador
        catchup_count, current_max = _count_new_calls(state)
        if catchup_count > 0:
            state['calls_since_last_audit'] = state.get('calls_since_last_audit', 0) + catchup_count
            state['last_bruce_id_seen'] = current_max
            state['last_check'] = datetime.now().isoformat()
            _save_monitor_state(state)
            print(f"  FIX 804: {catchup_count} llamada(s) detectada(s) mientras monitor estaba apagado")
            print(f"  Acumuladas ahora: {state['calls_since_last_audit']}\n")

    print(f"\n{'='*60}")
    print(f"  BRUCE W - MONITOR AUTOMATICO")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}")
    print(f"  Batch size: {batch_size} llamadas")
    print(f"  Intervalo: cada {interval_minutes} min")
    print(f"  Ultimo BRUCE ID: BRUCE{state.get('last_bruce_id_seen', '?')}")
    print(f"  Acumuladas: {state.get('calls_since_last_audit', 0)}/{batch_size}")
    print(f"  Ctrl+C para detener")
    print(f"{'='*60}\n")

    audit_count = 0

    try:
        while True:
            now = datetime.now().strftime('%H:%M:%S')
            new_calls, current_max = _count_new_calls(state)

            if new_calls > 0:
                state['calls_since_last_audit'] = state.get('calls_since_last_audit', 0) + new_calls
                state['last_bruce_id_seen'] = current_max
                state['last_check'] = datetime.now().isoformat()
                _save_monitor_state(state)

            accumulated = state.get('calls_since_last_audit', 0)

            if new_calls > 0:
                print(f"  [{now}] +{new_calls} llamada(s) nueva(s) "
                      f"(BRUCE{current_max}) | "
                      f"Acumuladas: {accumulated}/{batch_size}")
            else:
                print(f"  [{now}] Sin llamadas nuevas | "
                      f"Acumuladas: {accumulated}/{batch_size}", end='\r')

            # Disparar auditoria si llegamos al batch_size
            if accumulated >= batch_size:
                audit_count += 1
                print(f"\n\n{'*'*60}")
                print(f"  BATCH COMPLETO! {accumulated} llamadas acumuladas")
                print(f"  Iniciando auditoria #{audit_count}...")
                print(f"{'*'*60}\n")

                # Descargar logs nuevos
                try:
                    from production_data_fetcher import download_new_logs
                    download_new_logs()
                except Exception as e:
                    print(f"  [!] Error descargando logs: {e}")

                # Ejecutar auditoria completa
                try:
                    # Paso 1: Datos de produccion
                    prod_summary = None
                    try:
                        prod_summary = step_download_production_data()
                    except Exception as e:
                        print(f"  [!] Error descargando datos: {e}")

                    # Paso 2: Logs nuevos
                    new_logs = step_identify_new_logs()

                    if new_logs:
                        # Paso 3: Parsear
                        parse_metrics = step_parse_logs(new_logs)

                        # Paso 4: Regresion
                        regression_results = {'pass_rate': 0, 'passed': 0, 'failed': 0}
                        if not skip_regression:
                            try:
                                regression_results = step_run_regression()
                            except Exception as e:
                                print(f"  [!] Error regresion: {e}")

                        # Paso 5: Reporte
                        batch_num, excel_path = step_generate_report(
                            new_logs, parse_metrics, regression_results, prod_summary
                        )

                        bugs = parse_metrics.get('total_bugs', 0)
                        cal = parse_metrics.get('calificacion_promedio', 0)
                        print(f"\n  LOTE #{batch_num} COMPLETADO")
                        print(f"  Bugs: {bugs} | Calif: {cal} | Regresion: {regression_results.get('pass_rate', 0):.0f}%")
                    else:
                        print(f"\n  Sin logs nuevos para procesar")

                except Exception as e:
                    print(f"\n  [!] Error en auditoria: {e}")

                # FIX 804: Reset completo post-lote
                # Re-baseline al BRUCE ID mas reciente para no re-contar llamadas del lote anterior
                _, fresh_max = _count_new_calls({'last_bruce_id_seen': 0})
                state['calls_since_last_audit'] = 0
                state['last_bruce_id_seen'] = fresh_max if fresh_max > 0 else state.get('last_bruce_id_seen', 0)
                state['last_check'] = datetime.now().isoformat()
                _save_monitor_state(state)
                print(f"\n  Reset automatico: contador=0, baseline=BRUCE{state['last_bruce_id_seen']}")
                print(f"  Esperando siguiente lote de {batch_size} llamadas...\n")

            # Esperar
            time.sleep(interval_minutes * 60)

    except KeyboardInterrupt:
        print(f"\n\n  Monitor detenido.")
        print(f"  Auditorias realizadas: {audit_count}")
        print(f"  Llamadas pendientes: {state.get('calls_since_last_audit', 0)}/{batch_size}")
        _save_monitor_state(state)


# ============================================================
# MAIN
# ============================================================

def main():
    import argparse
    parser = argparse.ArgumentParser(description='Bruce W - Auditoria por Lotes')
    parser.add_argument('--skip-download', action='store_true',
                        help='No descargar datos de produccion')
    parser.add_argument('--skip-regression', action='store_true',
                        help='No ejecutar suite de regresion')
    parser.add_argument('--only-report', action='store_true',
                        help='Solo regenerar Excel desde historial')
    parser.add_argument('--status', action='store_true',
                        help='Mostrar estado actual')
    parser.add_argument('--process-all', action='store_true',
                        help='Procesar TODOS los logs (incluso ya procesados)')
    parser.add_argument('--monitor', action='store_true',
                        help='Modo monitor: vigila servidor y dispara auditoria automaticamente')
    parser.add_argument('--batch-size', type=int, default=25,
                        help='Llamadas para disparar auditoria en modo monitor (default: 25)')
    parser.add_argument('--interval', type=int, default=3,
                        help='Minutos entre chequeos en modo monitor (default: 3)')
    parser.add_argument('--reset', action='store_true',
                        help='Reiniciar estado del monitor (contar desde cero)')
    args = parser.parse_args()

    _ensure_dirs()

    if args.monitor:
        # FIX 804: --reset reinicia el estado del monitor
        if args.reset:
            _save_monitor_state({'last_bruce_id_seen': 0, 'calls_since_last_audit': 0, 'last_check': None})
            print("  Monitor reseteado. Se re-inicializara con el BRUCE ID actual.\n")
        run_monitor(
            batch_size=args.batch_size,
            interval_minutes=args.interval,
            skip_regression=args.skip_regression,
        )
        return

    if args.status:
        show_status()
        return

    if args.only_report:
        from batch_report_excel import load_batch_history, generate_excel
        history = load_batch_history()
        path = generate_excel(history)
        if path:
            print(f"\nExcel regenerado: {path}")
        return

    start = time.time()
    print(f"\n{'='*60}")
    print(f"  BRUCE W - AUDITORÍA POR LOTES")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}")

    # PASO 1: Descargar datos
    prod_summary = None
    if not args.skip_download:
        try:
            prod_summary = step_download_production_data()
        except Exception as e:
            print(f"\n  [!] Error descargando datos: {e}")
            print(f"  Continuando con datos locales...")

    # PASO 2: Identificar logs nuevos
    if args.process_all:
        # Procesar todos los logs
        new_logs = sorted([f for f in os.listdir(LOGS_DIR) if f.endswith('.txt')]) if os.path.isdir(LOGS_DIR) else []
        print(f"\n[2/5] PROCESANDO TODOS LOS LOGS: {len(new_logs)}\n")
    else:
        new_logs = step_identify_new_logs()

    if not new_logs and not args.skip_download:
        print("\n  [!] No hay logs nuevos para procesar.")
        print("  Use --process-all para reprocesar todos, o descargue nuevos logs primero.")

        # Aún así generar reporte si hay historial
        from batch_report_excel import load_batch_history
        history = load_batch_history()
        if history.get('batches'):
            print("  Regenerando Excel con datos existentes...")
            from batch_report_excel import generate_excel
            path = generate_excel(history)
            if path:
                print(f"  Excel: {path}")
        return

    # PASO 3: Parsear logs
    parse_metrics = step_parse_logs(new_logs)

    # PASO 4: Regresión
    regression_results = {'pass_rate': 0, 'passed': 0, 'failed': 0}
    if not args.skip_regression:
        try:
            regression_results = step_run_regression()
        except Exception as e:
            print(f"\n  [!] Error en regresión: {e}")

    # PASO 5: Generar reporte
    batch_num, excel_path = step_generate_report(
        new_logs, parse_metrics, regression_results, prod_summary
    )

    # RESUMEN FINAL
    elapsed = time.time() - start
    print(f"\n{'='*60}")
    print(f"  RESUMEN - LOTE #{batch_num}")
    print(f"{'='*60}")
    print(f"  Tiempo: {elapsed:.1f}s")
    print(f"  Logs procesados: {len(new_logs)}")
    print(f"  Conversaciones: {parse_metrics.get('total_conversations', 0)}")
    print(f"  Bugs encontrados: {parse_metrics.get('total_bugs', 0)}")
    print(f"  Calificación promedio: {parse_metrics.get('calificacion_promedio', 0)}")
    print(f"  Regresión: {regression_results.get('pass_rate', 0):.1f}%")
    if excel_path:
        print(f"  Excel: {excel_path}")

    # Próximos pasos
    if parse_metrics.get('total_bugs', 0) > 0:
        print(f"\n  PRÓXIMOS PASOS:")
        print(f"  1. Revisar bugs en Excel o en /bugs")
        print(f"  2. Aplicar FIX para bugs encontrados")
        print(f"  3. Validar en simulador: python simulador_llamadas.py")
        print(f"  4. Deploy a Railway: git push")
        print(f"  5. Ejecutar siguiente lote de 25 llamadas")
        print(f"  6. Repetir: python scripts/batch_audit.py")
    else:
        print(f"\n  Sin bugs detectados. Proceder con siguiente lote.")

    print(f"\n{'='*60}\n")


if __name__ == '__main__':
    main()
