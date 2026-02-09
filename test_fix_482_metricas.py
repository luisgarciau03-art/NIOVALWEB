"""
TEST FIX 482: Validar sistema de métricas e instrumentación

OBJETIVO:
- Verificar que MetricsLogger registra todas las métricas
- Validar cálculo de promedios
- Verificar generación de reportes
"""

import sys
import os

# Agregar path para importar AgenteVentas
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from agente_ventas import MetricsLogger

def test_metricas_timing():
    """Validar registro de métricas de timing"""

    print("\n" + "="*60)
    print("TEST FIX 482: METRICAS DE TIMING")
    print("="*60)

    metrics = MetricsLogger()

    # Simular registro de tiempos
    print("\nRegistrando tiempos simulados...")
    metrics.log_tiempo_transcripcion(0.35)
    metrics.log_tiempo_transcripcion(0.42)
    metrics.log_tiempo_transcripcion(0.28)

    metrics.log_tiempo_gpt(2.10)
    metrics.log_tiempo_gpt(1.85)
    metrics.log_tiempo_gpt(2.30)

    metrics.log_tiempo_audio(0.80)
    metrics.log_tiempo_audio(0.75)

    metrics.log_tiempo_total_turno(3.25)
    metrics.log_tiempo_total_turno(3.02)

    # Calcular promedios
    promedios = metrics.get_promedios()

    print("\nPromedios calculados:")
    print(f"  Transcripcion: {promedios['tiempo_transcripcion_avg']:.2f}s")
    print(f"  GPT: {promedios['tiempo_gpt_avg']:.2f}s")
    print(f"  Audio: {promedios['tiempo_audio_avg']:.2f}s")
    print(f"  Total turno: {promedios['tiempo_total_turno_avg']:.2f}s")

    # Validaciones
    tests_passed = 0
    tests_total = 4

    # TEST 1: Promedio transcripción ~0.35s
    if 0.25 <= promedios['tiempo_transcripcion_avg'] <= 0.45:
        print("  PASS: Promedio transcripcion correcto")
        tests_passed += 1
    else:
        print(f"  FAIL: Promedio transcripcion fuera de rango")

    # TEST 2: Promedio GPT ~2.08s
    if 1.8 <= promedios['tiempo_gpt_avg'] <= 2.4:
        print("  PASS: Promedio GPT correcto")
        tests_passed += 1
    else:
        print(f"  FAIL: Promedio GPT fuera de rango")

    # TEST 3: Promedio audio ~0.77s
    if 0.7 <= promedios['tiempo_audio_avg'] <= 0.85:
        print("  PASS: Promedio audio correcto")
        tests_passed += 1
    else:
        print(f"  FAIL: Promedio audio fuera de rango")

    # TEST 4: Promedio total ~3.13s
    if 2.8 <= promedios['tiempo_total_turno_avg'] <= 3.5:
        print("  PASS: Promedio total turno correcto")
        tests_passed += 1
    else:
        print(f"  FAIL: Promedio total turno fuera de rango")

    print(f"\nRESULTADO: {tests_passed}/{tests_total} tests pasados")
    return tests_passed == tests_total


def test_metricas_calidad():
    """Validar registro de métricas de calidad"""

    print("\n" + "="*60)
    print("TEST FIX 482: METRICAS DE CALIDAD")
    print("="*60)

    metrics = MetricsLogger()

    # Simular preguntas directas
    print("\nRegistrando preguntas directas...")
    metrics.log_pregunta_directa(respondida=True)
    metrics.log_pregunta_directa(respondida=True)
    metrics.log_pregunta_directa(respondida=True)
    metrics.log_pregunta_directa(respondida=False)

    # Simular transcripciones
    print("Registrando transcripciones...")
    metrics.log_transcripcion(correcta=True)
    metrics.log_transcripcion(correcta=True)
    metrics.log_transcripcion(correcta=True)
    metrics.log_transcripcion(correcta=True)
    metrics.log_transcripcion(correcta=False)

    # Calcular tasas
    promedios = metrics.get_promedios()

    print("\nTasas calculadas:")
    print(f"  Preguntas respondidas: {promedios['tasa_preguntas_respondidas']*100:.1f}%")
    print(f"  Transcripciones correctas: {promedios['tasa_transcripciones_correctas']*100:.1f}%")

    # Validaciones
    tests_passed = 0
    tests_total = 2

    # TEST 1: 3/4 preguntas respondidas = 75%
    if abs(promedios['tasa_preguntas_respondidas'] - 0.75) < 0.01:
        print("  PASS: Tasa preguntas respondidas correcta (75%)")
        tests_passed += 1
    else:
        print(f"  FAIL: Tasa incorrecta (esperado: 0.75, obtenido: {promedios['tasa_preguntas_respondidas']})")

    # TEST 2: 4/5 transcripciones correctas = 80%
    if abs(promedios['tasa_transcripciones_correctas'] - 0.80) < 0.01:
        print("  PASS: Tasa transcripciones correctas correcta (80%)")
        tests_passed += 1
    else:
        print(f"  FAIL: Tasa incorrecta (esperado: 0.80, obtenido: {promedios['tasa_transcripciones_correctas']})")

    print(f"\nRESULTADO: {tests_passed}/{tests_total} tests pasados")
    return tests_passed == tests_total


def test_metricas_interacciones():
    """Validar registro de métricas de interacciones"""

    print("\n" + "="*60)
    print("TEST FIX 482: METRICAS DE INTERACCIONES")
    print("="*60)

    metrics = MetricsLogger()

    # Simular interacciones
    print("\nRegistrando interacciones...")
    metrics.log_interrupcion_detectada()
    metrics.log_interrupcion_detectada()
    metrics.log_interrupcion_detectada()

    metrics.log_repeticion_cliente()
    metrics.log_repeticion_cliente()

    metrics.log_recuperacion_error()

    metrics.log_respuesta_vacia_bloqueada()
    metrics.log_respuesta_vacia_bloqueada()

    print("\nContadores:")
    print(f"  Interrupciones evitadas: {metrics.metricas['interrupciones_detectadas']}")
    print(f"  Repeticiones cliente: {metrics.metricas['repeticiones_cliente']}")
    print(f"  Recuperaciones error: {metrics.metricas['recuperaciones_error']}")
    print(f"  Respuestas vacias bloqueadas: {metrics.metricas['respuestas_vacias_bloqueadas']}")

    # Validaciones
    tests_passed = 0
    tests_total = 4

    if metrics.metricas['interrupciones_detectadas'] == 3:
        print("  PASS: Contador interrupciones correcto")
        tests_passed += 1
    else:
        print("  FAIL: Contador interrupciones incorrecto")

    if metrics.metricas['repeticiones_cliente'] == 2:
        print("  PASS: Contador repeticiones correcto")
        tests_passed += 1
    else:
        print("  FAIL: Contador repeticiones incorrecto")

    if metrics.metricas['recuperaciones_error'] == 1:
        print("  PASS: Contador recuperaciones correcto")
        tests_passed += 1
    else:
        print("  FAIL: Contador recuperaciones incorrecto")

    if metrics.metricas['respuestas_vacias_bloqueadas'] == 2:
        print("  PASS: Contador respuestas vacias correcto")
        tests_passed += 1
    else:
        print("  FAIL: Contador respuestas vacias incorrecto")

    print(f"\nRESULTADO: {tests_passed}/{tests_total} tests pasados")
    return tests_passed == tests_total


def test_generacion_reporte():
    """Validar generación de reporte legible"""

    print("\n" + "="*60)
    print("TEST FIX 482: GENERACION DE REPORTE")
    print("="*60)

    metrics = MetricsLogger()

    # Registrar datos de ejemplo
    metrics.log_tiempo_transcripcion(0.35)
    metrics.log_tiempo_gpt(2.10)
    metrics.log_tiempo_audio(0.80)
    metrics.log_tiempo_total_turno(3.25)

    metrics.log_pregunta_directa(respondida=True)
    metrics.log_pregunta_directa(respondida=True)

    metrics.log_interrupcion_detectada()
    metrics.log_repeticion_cliente()

    # Generar reporte
    reporte = metrics.generar_reporte()

    print("\nReporte generado:")
    print(reporte)

    # Validaciones
    tests_passed = 0
    tests_total = 5

    if "METRICAS DE LLAMADA" in reporte:
        print("  PASS: Reporte contiene titulo")
        tests_passed += 1
    else:
        print("  FAIL: Falta titulo")

    if "TIMING PROMEDIO" in reporte:
        print("  PASS: Reporte contiene seccion timing")
        tests_passed += 1
    else:
        print("  FAIL: Falta seccion timing")

    if "CALIDAD" in reporte:
        print("  PASS: Reporte contiene seccion calidad")
        tests_passed += 1
    else:
        print("  FAIL: Falta seccion calidad")

    if "INTERACCIONES" in reporte:
        print("  PASS: Reporte contiene seccion interacciones")
        tests_passed += 1
    else:
        print("  FAIL: Falta seccion interacciones")

    if "0.35s" in reporte or "0.3" in reporte:
        print("  PASS: Reporte contiene valores numericos")
        tests_passed += 1
    else:
        print("  FAIL: Faltan valores numericos")

    print(f"\nRESULTADO: {tests_passed}/{tests_total} tests pasados")
    return tests_passed == tests_total


def main():
    """Ejecutar todos los tests de métricas"""

    print("\n" + "="*70)
    print("SUITE DE TESTS: FIX 482 (METRICAS E INSTRUMENTACION)")
    print("="*70)

    resultados = {
        "Metricas de Timing": test_metricas_timing(),
        "Metricas de Calidad": test_metricas_calidad(),
        "Metricas de Interacciones": test_metricas_interacciones(),
        "Generacion de Reporte": test_generacion_reporte(),
    }

    # Resumen final
    print("\n" + "="*70)
    print("RESUMEN FINAL")
    print("="*70)

    for nombre, resultado in resultados.items():
        estado = "PASS" if resultado else "FAIL"
        print(f"  {nombre}: {estado}")

    todos_pasaron = all(resultados.values())

    print("\n" + "="*70)
    if todos_pasaron:
        print("EXITO: Todos los tests de metricas pasaron")
    else:
        print("FALLO: Algunos tests fallaron")
    print("="*70)

    return todos_pasaron


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
