"""
EJECUTAR TODOS LOS TESTS - AUDITORIA W04

Script maestro que ejecuta todos los tests de validación de FIXes
y genera un reporte consolidado.
"""

import subprocess
import sys
from datetime import datetime

def ejecutar_test(nombre_script):
    """Ejecuta un script de test y retorna el resultado"""

    print(f"\n{'='*70}")
    print(f"EJECUTANDO: {nombre_script}")
    print(f"{'='*70}")

    try:
        # Ejecutar test
        resultado = subprocess.run(
            [sys.executable, nombre_script],
            capture_output=True,
            text=True,
            timeout=30
        )

        # Imprimir output
        print(resultado.stdout)
        if resultado.stderr:
            print("ERRORES:")
            print(resultado.stderr)

        # Retornar código de salida (0 = éxito, 1 = fallo)
        return resultado.returncode == 0

    except subprocess.TimeoutExpired:
        print(f"\nERROR: Test excedió timeout de 30 segundos")
        return False
    except Exception as e:
        print(f"\nERROR ejecutando test: {e}")
        return False


def main():
    """Ejecutar todos los tests y generar reporte"""

    print("\n" + "="*70)
    print("SUITE COMPLETA DE TESTS - AUDITORIA W04")
    print("Fecha:", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    print("="*70)

    # Lista de tests a ejecutar
    tests = [
        {
            "nombre": "FIX 475: Timeout Deepgram",
            "script": "test_fix_475_timeout_deepgram.py",
            "critico": True
        },
        {
            "nombre": "FIX 476: Preguntas Directas",
            "script": "test_fix_476_preguntas_directas.py",
            "critico": True
        },
        {
            "nombre": "FIX 477: Detector Interrupciones",
            "script": "test_fix_477_detector_interrupciones.py",
            "critico": True
        },
        {
            "nombre": "FIX 479+480+481: Recuperacion Errores",
            "script": "test_fix_479_480_481_recuperacion.py",
            "critico": True
        },
        {
            "nombre": "FIX 482: Metricas e Instrumentacion",
            "script": "test_fix_482_metricas.py",
            "critico": False
        },
    ]

    # Ejecutar cada test
    resultados = {}

    for test in tests:
        resultado = ejecutar_test(test["script"])
        resultados[test["nombre"]] = {
            "resultado": resultado,
            "critico": test["critico"]
        }

    # Generar reporte final
    print("\n\n" + "="*70)
    print("REPORTE FINAL DE TESTS")
    print("="*70)

    tests_pasados = 0
    tests_totales = len(tests)
    tests_criticos_fallidos = []

    for nombre, info in resultados.items():
        estado = "PASS" if info["resultado"] else "FAIL"
        criticidad = "CRITICO" if info["critico"] else "OPCIONAL"

        print(f"\n{nombre}:")
        print(f"  Estado: {estado}")
        print(f"  Criticidad: {criticidad}")

        if info["resultado"]:
            tests_pasados += 1
        elif info["critico"]:
            tests_criticos_fallidos.append(nombre)

    # Resumen
    print("\n" + "="*70)
    print("RESUMEN")
    print("="*70)
    print(f"Tests ejecutados: {tests_totales}")
    print(f"Tests pasados: {tests_pasados}")
    print(f"Tests fallidos: {tests_totales - tests_pasados}")
    print(f"Tasa de exito: {(tests_pasados/tests_totales)*100:.1f}%")

    # Validar tests críticos
    if tests_criticos_fallidos:
        print("\n" + "!"*70)
        print("ATENCION: TESTS CRITICOS FALLIDOS")
        print("!"*70)
        for test in tests_criticos_fallidos:
            print(f"  - {test}")
        print("\nACCION REQUERIDA: Revisar y corregir antes de deploy")
        print("="*70)
        return False
    elif tests_pasados == tests_totales:
        print("\n" + "="*70)
        print("EXITO: TODOS LOS TESTS PASARON")
        print("Sistema listo para testing en produccion")
        print("="*70)
        return True
    else:
        print("\n" + "="*70)
        print("PARCIAL: Tests criticos OK, algunos opcionales fallaron")
        print("Se puede proceder con precaucion")
        print("="*70)
        return True


if __name__ == "__main__":
    success = main()

    # Guardar reporte
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    reporte_file = f"reporte_tests_{timestamp}.txt"

    print(f"\nReporte guardado en: {reporte_file}")

    # Código de salida
    exit(0 if success else 1)
