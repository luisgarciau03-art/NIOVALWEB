"""
FIX 638: Runner de tests con notificacion Telegram.

Ejecuta pytest y envia alerta a Telegram si hay tests que fallan.
Puede correrse manualmente o en CI/CD.

Uso:
    python scripts/run_tests_notify.py
"""

import subprocess
import sys
import os
import requests
from datetime import datetime

# Telegram bots (mismos de bug_detector.py)
TELEGRAM_BOTS = [
    {
        "token": "8537624347:AAHDIe60mb2TkdDk4vqlcS2tpakTB_5D4qE",
        "chat_id": "7314842427",
    },
    {
        "token": "8524460310:AAFAwph27rSagooKTNSGXauBycpDpCjhKjI",
        "chat_id": "5838212022",
    },
]


def enviar_telegram(mensaje: str):
    """Envia mensaje a todos los bots de Telegram."""
    for bot in TELEGRAM_BOTS:
        try:
            url = f"https://api.telegram.org/bot{bot['token']}/sendMessage"
            requests.post(url, data={
                "chat_id": bot["chat_id"],
                "text": mensaje,
                "parse_mode": "HTML",
            }, timeout=10)
        except Exception:
            pass


def run_tests():
    """Ejecuta pytest y retorna (exit_code, stdout, stderr)."""
    project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    result = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/", "-v", "--tb=short"],
        capture_output=True,
        text=True,
        cwd=project_dir,
        timeout=120,
    )
    return result.returncode, result.stdout, result.stderr


def parse_results(stdout: str) -> dict:
    """Extrae estadisticas del output de pytest."""
    info = {"passed": 0, "failed": 0, "errors": 0, "total": 0, "failed_tests": []}

    for line in stdout.splitlines():
        # Linea final: "X passed, Y failed in Z.ZZs"
        if "passed" in line and ("failed" in line or "error" in line or "in " in line):
            import re
            m_passed = re.search(r'(\d+) passed', line)
            m_failed = re.search(r'(\d+) failed', line)
            m_errors = re.search(r'(\d+) error', line)
            if m_passed:
                info["passed"] = int(m_passed.group(1))
            if m_failed:
                info["failed"] = int(m_failed.group(1))
            if m_errors:
                info["errors"] = int(m_errors.group(1))
            info["total"] = info["passed"] + info["failed"] + info["errors"]

        # Tests que fallaron: "FAILED tests/test_xxx.py::TestClass::test_method"
        if line.startswith("FAILED "):
            test_name = line.replace("FAILED ", "").strip()
            # Acortar el path
            test_name = test_name.split("::")[-1] if "::" in test_name else test_name
            info["failed_tests"].append(test_name)

    return info


def main():
    print(f"[TEST RUNNER] Ejecutando tests... ({datetime.now().strftime('%H:%M:%S')})")

    try:
        exit_code, stdout, stderr = run_tests()
    except subprocess.TimeoutExpired:
        msg = "<b>TESTS TIMEOUT</b>\nLos tests tardaron mas de 120s y fueron cancelados."
        enviar_telegram(msg)
        print("[TEST RUNNER] TIMEOUT - tests cancelados")
        sys.exit(1)
    except Exception as e:
        msg = f"<b>TESTS ERROR</b>\nNo se pudieron ejecutar: {e}"
        enviar_telegram(msg)
        print(f"[TEST RUNNER] Error ejecutando tests: {e}")
        sys.exit(1)

    info = parse_results(stdout)

    if exit_code == 0:
        # Tests pasaron
        print(f"[TEST RUNNER] PASSED: {info['passed']}/{info['total']} tests")
        # No notificar si todo paso (evitar spam)
        # Solo imprimir en consola
    else:
        # Tests fallaron - notificar Telegram
        lineas = ["<b>TESTS FALLARON</b>"]
        lineas.append(f"Passed: {info['passed']} | Failed: {info['failed']} | Errors: {info['errors']}")
        lineas.append("")

        if info["failed_tests"]:
            lineas.append("<b>Tests fallidos:</b>")
            for t in info["failed_tests"][:10]:  # Max 10
                lineas.append(f"  - {t}")

        lineas.append("")
        lineas.append(f"Hora: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        # Agregar ultimas lineas del output para contexto
        error_lines = [l for l in stdout.splitlines() if "FAILED" in l or "ERROR" in l or "assert" in l.lower()]
        if error_lines:
            lineas.append("")
            lineas.append("<b>Detalle:</b>")
            for el in error_lines[:5]:
                lineas.append(f"<code>{el[:100]}</code>")

        mensaje = "\n".join(lineas)
        enviar_telegram(mensaje)

        print(f"[TEST RUNNER] FAILED: {info['failed']} tests fallaron")
        print(stdout[-500:] if len(stdout) > 500 else stdout)

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
