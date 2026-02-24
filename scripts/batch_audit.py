"""
Orquestador del ciclo de auditoría por lotes para Bruce W.

Workflow:
  1. Descargar datos de producción (bugs, patterns, logs)
  2. Identificar logs nuevos (no procesados previamente)
  3. Parsear logs → extraer conversaciones y bugs
  4. Ejecutar suite de regresión
  5. Generar reporte Excel con resultados del lote
  6. Mostrar resumen con próximos pasos

El historial evita procesar el mismo log dos veces.
Cada ejecución = 1 lote en el Excel.

Uso:
  python scripts/batch_audit.py                    # Auditoría completa
  python scripts/batch_audit.py --skip-download    # Usar datos locales
  python scripts/batch_audit.py --skip-regression  # Sin tests de regresión
  python scripts/batch_audit.py --only-report      # Solo regenerar Excel
  python scripts/batch_audit.py --status           # Ver estado actual
"""

import os
import sys
import re
import json
import time
import subprocess
from datetime import datetime

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS_DIR = os.path.join(PROJECT_DIR, 'scripts')
LOGS_DIR = os.path.join(PROJECT_DIR, 'LOGS')
AUDIT_DATA_DIR = os.path.join(PROJECT_DIR, 'audit_data')
TESTS_DIR = os.path.join(PROJECT_DIR, 'tests')
TEST_DATA_DIR = os.path.join(TESTS_DIR, 'test_data')

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

def step_parse_logs(log_files):
    """Parsea logs nuevos, extrae conversaciones y bugs.

    Returns:
        dict con métricas del parseo
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

    # Usar log_scenario_extractor para parsear
    extractor_path = os.path.join(SCRIPTS_DIR, 'log_scenario_extractor.py')
    if os.path.exists(extractor_path):
        ok, output = _run(
            [sys.executable, extractor_path],
            "Ejecutando log_scenario_extractor",
            timeout=120,
        )

    # Parsear logs directamente para métricas del lote
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
    RE_BRUCE_ID = re.compile(r'BRUCE(\d+)')
    RE_BUG = re.compile(r'\[BUG_DETECTOR\]\s*(BRUCE\d+):\s*(\d+)\s*bug')
    RE_BUG_LINE = re.compile(r'\[(CRITICO|ALTO|MEDIO|BAJO)\]\s*(\w+):\s*(.*)')
    RE_CALIFICACION = re.compile(r'Calificaci[oó]n Bruce:\s*(\d+)/10')
    RE_CONCLUSION = re.compile(r'Conclusi[oó]n determinada:\s*(\w+)')
    RE_CLIENTE = re.compile(r'\[CLIENTE\]\s*(BRUCE\d+)')
    RE_BRUCE = re.compile(r'\[BRUCE\]\s*(BRUCE\d+)')

    all_bruce_ids = set()
    current_bruce_bugs = {}

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

        # Extraer BRUCE IDs
        for m in RE_BRUCE_ID.finditer(content):
            bid = f"BRUCE{m.group(1)}"
            all_bruce_ids.add(bid)

        # Extraer bugs
        for m in RE_BUG.finditer(content):
            bruce_id = m.group(1)
            n_bugs = int(m.group(2))
            current_bruce_bugs[bruce_id] = n_bugs

        # Extraer detalle de bugs
        for m in RE_BUG_LINE.finditer(content):
            sev = m.group(1)
            tipo = m.group(2)
            detalle = m.group(3).strip()

            # Asociar con el BRUCE ID más reciente
            recent_bruce = None
            for bid in reversed(list(current_bruce_bugs.keys())):
                recent_bruce = bid
                break

            metrics['bugs_detalle'].append({
                'bruce_id': recent_bruce or 'UNKNOWN',
                'tipo': tipo,
                'severidad': sev,
                'detalle': detalle[:200],
            })
            metrics['bugs_por_tipo'][tipo] = metrics['bugs_por_tipo'].get(tipo, 0) + 1
            metrics['total_bugs'] += 1

        # Extraer calificaciones
        for m in RE_CALIFICACION.finditer(content):
            cal = int(m.group(1))
            metrics['calificaciones'].append(cal)

    metrics['bruce_ids'] = sorted(all_bruce_ids)
    metrics['total_llamadas'] = len(all_bruce_ids)
    metrics['total_conversations'] = len(all_bruce_ids)

    print(f"  Conversaciones encontradas: {metrics['total_conversations']}")
    print(f"  BRUCE IDs: {len(metrics['bruce_ids'])}")
    print(f"  Bugs detectados: {metrics['total_bugs']}")
    if metrics['bugs_por_tipo']:
        print(f"  Por tipo:")
        for tipo, count in sorted(metrics['bugs_por_tipo'].items(), key=lambda x: -x[1])[:10]:
            print(f"    {tipo}: {count}")
    if metrics['calificaciones']:
        avg = sum(metrics['calificaciones']) / len(metrics['calificaciones'])
        print(f"  Calificación promedio: {avg:.1f}/10")
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
# MAIN
# ============================================================

def main():
    import argparse
    parser = argparse.ArgumentParser(description='Bruce W - Auditoría por Lotes')
    parser.add_argument('--skip-download', action='store_true',
                        help='No descargar datos de producción')
    parser.add_argument('--skip-regression', action='store_true',
                        help='No ejecutar suite de regresión')
    parser.add_argument('--only-report', action='store_true',
                        help='Solo regenerar Excel desde historial')
    parser.add_argument('--status', action='store_true',
                        help='Mostrar estado actual')
    parser.add_argument('--process-all', action='store_true',
                        help='Procesar TODOS los logs (incluso ya procesados)')
    args = parser.parse_args()

    _ensure_dirs()

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
