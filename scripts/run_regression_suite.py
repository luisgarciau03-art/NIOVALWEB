"""
Orquestador: Suite de Regresión Automatizada para Bruce W.

Ejecuta el pipeline completo:
  1. Parse logs → scenario_db.json
  2. Generar bug_regression_catalog.json
  3. Generar mutation_scenarios.json
  4. Ejecutar tests (pytest)
  5. Generar reporte

Uso:
  python scripts/run_regression_suite.py              # Full pipeline
  python scripts/run_regression_suite.py --skip-parse # Usar datos cacheados
  python scripts/run_regression_suite.py --quick      # Solo regresión (sin mutaciones)
"""

import os
import sys
import time
import json
import subprocess
import argparse
from datetime import datetime

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS_DIR = os.path.join(PROJECT_DIR, 'scripts')
TESTS_DIR = os.path.join(PROJECT_DIR, 'tests')
TEST_DATA_DIR = os.path.join(TESTS_DIR, 'test_data')
LOGS_DIR = os.path.join(PROJECT_DIR, 'LOGS')

sys.path.insert(0, PROJECT_DIR)


def _run_python(script_args, description, timeout=300):
    """Ejecuta un script Python y retorna (success, output)."""
    cmd = [sys.executable] + script_args
    print(f"  Ejecutando: {' '.join(script_args[-2:])}")
    try:
        result = subprocess.run(
            cmd,
            cwd=PROJECT_DIR,
            capture_output=True,
            text=True,
            timeout=timeout,
            encoding='utf-8',
            errors='replace',
        )
        output = result.stdout + result.stderr
        success = result.returncode == 0
        if not success:
            print(f"  ADVERTENCIA: {description} retornó código {result.returncode}")
        return success, output
    except subprocess.TimeoutExpired:
        print(f"  TIMEOUT: {description} excedió {timeout}s")
        return False, f"Timeout después de {timeout}s"
    except Exception as e:
        print(f"  ERROR: {description}: {e}")
        return False, str(e)


def _run_pytest(test_args, description, timeout=600):
    """Ejecuta pytest y retorna (passed, failed, errors, output)."""
    cmd = [sys.executable, '-m', 'pytest'] + test_args + [
        '-v', '--tb=short', '--no-header', '-q'
    ]
    print(f"  Ejecutando: pytest {' '.join(test_args)}")
    try:
        result = subprocess.run(
            cmd,
            cwd=PROJECT_DIR,
            capture_output=True,
            text=True,
            timeout=timeout,
            encoding='utf-8',
            errors='replace',
        )
        output = result.stdout + result.stderr

        # Parsear resultados
        passed = failed = errors = 0
        for line in output.split('\n'):
            line = line.strip()
            if 'passed' in line or 'failed' in line or 'error' in line:
                import re
                m_p = re.search(r'(\d+) passed', line)
                m_f = re.search(r'(\d+) failed', line)
                m_e = re.search(r'(\d+) error', line)
                if m_p:
                    passed = int(m_p.group(1))
                if m_f:
                    failed = int(m_f.group(1))
                if m_e:
                    errors = int(m_e.group(1))

        return passed, failed, errors, output
    except subprocess.TimeoutExpired:
        print(f"  TIMEOUT: {description}")
        return 0, 0, 1, "Timeout"
    except Exception as e:
        print(f"  ERROR: {description}: {e}")
        return 0, 0, 1, str(e)


def main():
    parser = argparse.ArgumentParser(description='Bruce W - Suite de Regresión')
    parser.add_argument('--skip-parse', action='store_true',
                        help='Usar datos cacheados (no re-parsear logs)')
    parser.add_argument('--quick', action='store_true',
                        help='Solo regresión, sin mutaciones')
    parser.add_argument('--mutations', type=int, default=50,
                        help='Número de mutaciones a generar')
    args = parser.parse_args()

    start = time.time()

    print(f"\n{'='*60}")
    print(f"  BRUCE W - SUITE DE REGRESIÓN AUTOMATIZADA")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}\n")

    results = {}

    # ============================================================
    # PASO 1: Parse logs
    # ============================================================
    if not args.skip_parse:
        print("[1/5] Parseando archivos de logs...")
        ok, out = _run_python(
            [os.path.join(SCRIPTS_DIR, 'log_scenario_extractor.py')],
            "Log Scenario Extractor",
            timeout=120,
        )
        # Extraer stats del output
        import re
        m = re.search(r'(\d+) conversaciones', out)
        total_convs = int(m.group(1)) if m else '?'
        m_bugs = re.search(r'Con bugs detectados:\s*(\d+)', out)
        total_bugs = int(m_bugs.group(1)) if m_bugs else '?'
        print(f"  {total_convs} conversaciones extraídas, {total_bugs} con bugs\n")
        results['parse'] = {'ok': ok, 'conversations': total_convs, 'with_bugs': total_bugs}
    else:
        print("[1/5] Usando datos cacheados (--skip-parse)\n")
        results['parse'] = {'ok': True, 'cached': True}

    # ============================================================
    # PASO 2: Generar catálogo de regresión
    # ============================================================
    if not args.skip_parse:
        print("[2/5] Generando catálogo de regresión...")
        ok, out = _run_python(
            [os.path.join(SCRIPTS_DIR, 'log_scenario_extractor.py'), '--bug-catalog'],
            "Bug Catalog Generator",
            timeout=120,
        )
        import re
        m = re.search(r'(\d+) regression tests', out)
        total_regressions = int(m.group(1)) if m else '?'
        m_types = re.search(r'(\d+) tipos de bug', out)
        bug_types = int(m_types.group(1)) if m_types else '?'
        print(f"  {total_regressions} test cases, {bug_types} tipos de bug\n")
        results['catalog'] = {'ok': ok, 'regressions': total_regressions, 'bug_types': bug_types}
    else:
        print("[2/5] Usando catálogo cacheado\n")
        results['catalog'] = {'ok': True, 'cached': True}

    # ============================================================
    # PASO 3: Generar mutaciones
    # ============================================================
    if not args.quick:
        if not args.skip_parse:
            print("[3/5] Generando mutaciones...")
            ok, out = _run_python(
                [os.path.join(SCRIPTS_DIR, 'scenario_mutator.py'), '--count', str(args.mutations)],
                "Scenario Mutator",
                timeout=60,
            )
            import re
            m = re.search(r'Total: (\d+)', out)
            total_muts = int(m.group(1)) if m else '?'
            print(f"  {total_muts} escenarios mutados\n")
            results['mutations'] = {'ok': ok, 'total': total_muts}
        else:
            print("[3/5] Usando mutaciones cacheadas\n")
            results['mutations'] = {'ok': True, 'cached': True}
    else:
        print("[3/5] Saltando mutaciones (--quick)\n")
        results['mutations'] = {'ok': True, 'skipped': True}

    # ============================================================
    # PASO 4: Ejecutar tests
    # ============================================================
    print("[4/5] Ejecutando tests...\n")

    total_passed = 0
    total_failed = 0
    total_errors = 0
    failed_tests = []

    # 4a) Bug Regressions RAW
    print("  --- Bug Regressions RAW ---")
    p, f, e, out = _run_pytest(
        ['tests/test_bug_regression.py', '-k', 'RAW'],
        "Bug Regressions RAW",
        timeout=300,
    )
    total_passed += p
    total_failed += f
    total_errors += e
    print(f"  Resultado: {p} PASS, {f} FAIL, {e} ERROR\n")
    results['test_raw'] = {'passed': p, 'failed': f, 'errors': e}
    if f > 0 or e > 0:
        # Extraer nombres de tests fallidos
        for line in out.split('\n'):
            if 'FAILED' in line:
                failed_tests.append(line.strip())

    # 4b) Bug Regressions LIVE
    print("  --- Bug Regressions LIVE ---")
    p, f, e, out = _run_pytest(
        ['tests/test_bug_regression.py', '-k', 'LIVE'],
        "Bug Regressions LIVE",
        timeout=600,
    )
    total_passed += p
    total_failed += f
    total_errors += e
    print(f"  Resultado: {p} PASS, {f} FAIL, {e} ERROR\n")
    results['test_live'] = {'passed': p, 'failed': f, 'errors': e}
    if f > 0 or e > 0:
        for line in out.split('\n'):
            if 'FAILED' in line:
                failed_tests.append(line.strip())

    # 4c) No-Crash
    print("  --- No-Crash Regressions ---")
    p, f, e, out = _run_pytest(
        ['tests/test_bug_regression.py', '-k', 'NOCRASH'],
        "No-Crash Regressions",
        timeout=300,
    )
    total_passed += p
    total_failed += f
    total_errors += e
    print(f"  Resultado: {p} PASS, {f} FAIL, {e} ERROR\n")
    results['test_nocrash'] = {'passed': p, 'failed': f, 'errors': e}

    # 4d) Mutaciones (si no --quick)
    if not args.quick:
        print("  --- Mutations No-Crash ---")
        p, f, e, out = _run_pytest(
            ['tests/test_scenario_mutations.py', '-k', 'no_crash'],
            "Mutations No-Crash",
            timeout=600,
        )
        total_passed += p
        total_failed += f
        total_errors += e
        print(f"  Resultado: {p} PASS, {f} FAIL, {e} ERROR\n")
        results['test_mut_nocrash'] = {'passed': p, 'failed': f, 'errors': e}

        print("  --- Mutations No-Critical-Bugs ---")
        p, f, e, out = _run_pytest(
            ['tests/test_scenario_mutations.py', '-k', 'no_critical'],
            "Mutations No-Critical-Bugs",
            timeout=600,
        )
        total_passed += p
        total_failed += f
        total_errors += e
        print(f"  Resultado: {p} PASS, {f} FAIL, {e} ERROR\n")
        results['test_mut_criticos'] = {'passed': p, 'failed': f, 'errors': e}

    # ============================================================
    # PASO 5: Reporte
    # ============================================================
    elapsed = time.time() - start
    total_all = total_passed + total_failed + total_errors
    pct = (total_passed / total_all * 100) if total_all > 0 else 0

    print(f"\n{'='*60}")
    print(f"  [5/5] REPORTE FINAL")
    print(f"{'='*60}")
    print(f"  TOTAL: {total_passed}/{total_all} PASS ({pct:.1f}%)")
    print(f"  Tiempo: {elapsed:.1f}s")
    print()

    if failed_tests:
        print("  TESTS FALLIDOS:")
        for ft in failed_tests[:20]:
            print(f"    {ft}")
        print()

    # Resumen por categoría
    for cat, label in [
        ('test_raw', 'Bug Regressions RAW'),
        ('test_live', 'Bug Regressions LIVE'),
        ('test_nocrash', 'No-Crash Regressions'),
        ('test_mut_nocrash', 'Mutations No-Crash'),
        ('test_mut_criticos', 'Mutations No-Critical-Bugs'),
    ]:
        r = results.get(cat)
        if r:
            status = "PASS" if r['failed'] == 0 and r['errors'] == 0 else "FAIL"
            print(f"  {label:30s}: {r['passed']:3d}/{r['passed']+r['failed']+r['errors']:3d}  {status}")

    print(f"{'='*60}\n")

    # Guardar reporte
    report = {
        'timestamp': datetime.now().isoformat(),
        'elapsed_seconds': round(elapsed, 1),
        'total_passed': total_passed,
        'total_failed': total_failed,
        'total_errors': total_errors,
        'pass_rate': round(pct, 1),
        'details': results,
        'failed_tests': failed_tests,
    }
    report_path = os.path.join(TEST_DATA_DIR, 'regression_report.json')
    os.makedirs(TEST_DATA_DIR, exist_ok=True)
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"  Reporte guardado: {report_path}")

    # Exit code
    sys.exit(0 if total_failed == 0 and total_errors == 0 else 1)


if __name__ == '__main__':
    main()
