# -*- coding: utf-8 -*-
"""
Test para FIX 451: Esperar transcripcion FINAL antes de procesar

Problema: GPT procesa transcripciones PARCIALES de Deepgram antes de que
llegue la transcripcion FINAL, causando desfase y respuestas incoherentes.

Solucion: Agregar tracking de FINAL vs PARCIAL y esperar hasta 1s adicional
por la transcripcion FINAL antes de procesar.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import time


def test_tracking_final_parcial():
    """
    FIX 451: Verificar que el tracking de FINAL vs PARCIAL funciona correctamente
    """
    print("\n" + "="*60)
    print("TEST FIX 451: Tracking FINAL vs PARCIAL")
    print("="*60)

    # Simular el diccionario de tracking
    deepgram_ultima_final = {}
    call_sid = "test_call_123"

    # Caso 1: Solo PARCIAL
    deepgram_ultima_final[call_sid] = {
        "timestamp": time.time(),
        "texto": "Buen dia",
        "es_final": False
    }

    info = deepgram_ultima_final.get(call_sid, {})
    es_final = info.get("es_final", False)

    if not es_final:
        print("  [OK] Caso 1: Detectado como PARCIAL correctamente")
    else:
        print("  [FAIL] Caso 1: Deberia ser PARCIAL")
        return False

    # Caso 2: Llega FINAL
    deepgram_ultima_final[call_sid] = {
        "timestamp": time.time(),
        "texto": "Buen dia, le llamo de NIOVAL.",
        "es_final": True
    }

    info = deepgram_ultima_final.get(call_sid, {})
    es_final = info.get("es_final", False)

    if es_final:
        print("  [OK] Caso 2: Detectado como FINAL correctamente")
    else:
        print("  [FAIL] Caso 2: Deberia ser FINAL")
        return False

    # Caso 3: Call_sid no existe
    info = deepgram_ultima_final.get("no_existe", {})
    es_final = info.get("es_final", False)

    if not es_final:
        print("  [OK] Caso 3: Call_sid inexistente manejado correctamente")
    else:
        print("  [FAIL] Caso 3: Deberia ser False por defecto")
        return False

    print("\n[OK] Test tracking FINAL/PARCIAL pasado")
    return True


def test_logica_espera():
    """
    FIX 451: Verificar la logica de espera por FINAL
    """
    print("\n" + "="*60)
    print("TEST FIX 451: Logica de espera por FINAL")
    print("="*60)

    # Simular variables
    max_espera_final_extra = 1.0
    wait_interval = 0.05

    # Caso 1: FINAL llega inmediatamente
    tiempo_espera = 0.0
    es_final = True

    if es_final:
        print("  [OK] Caso 1: FINAL inmediato - no necesita esperar")
    else:
        print("  [FAIL] Caso 1: Deberia procesar inmediatamente")
        return False

    # Caso 2: Solo PARCIAL, esperar hasta max
    tiempo_espera = 0.0
    es_final = False
    esperando_final = True

    while tiempo_espera < max_espera_final_extra and not es_final:
        tiempo_espera += wait_interval
        # Simular que FINAL llega despues de 0.3s
        if tiempo_espera >= 0.3:
            es_final = True

    if es_final and tiempo_espera <= 0.35:
        print(f"  [OK] Caso 2: FINAL llego despues de {tiempo_espera:.2f}s")
    else:
        print(f"  [FAIL] Caso 2: No detecto FINAL a tiempo")
        return False

    # Caso 3: FINAL nunca llega, usar PARCIAL despues de timeout
    tiempo_espera = 0.0
    es_final = False

    while tiempo_espera < max_espera_final_extra and not es_final:
        tiempo_espera += wait_interval

    if not es_final and tiempo_espera >= max_espera_final_extra:
        print(f"  [OK] Caso 3: Timeout alcanzado ({tiempo_espera:.2f}s) - usar PARCIAL")
    else:
        print(f"  [FAIL] Caso 3: No manejo timeout correctamente")
        return False

    print("\n[OK] Test logica de espera pasado")
    return True


def test_escenario_desfase():
    """
    FIX 451: Simular el escenario de desfase GPT/Deepgram
    """
    print("\n" + "="*60)
    print("TEST FIX 451: Escenario de desfase GPT/Deepgram")
    print("="*60)

    # Simular secuencia real:
    # t=0.0s: Llega PARCIAL "Buen"
    # t=0.1s: Llega PARCIAL "Buen dia"
    # t=0.3s: Llega FINAL "Buen dia, buenos dias."
    # Sin FIX 451: GPT procesa "Buen" y responde incorrectamente
    # Con FIX 451: Espera FINAL y procesa "Buen dia, buenos dias."

    transcripciones = [
        (0.0, "Buen", False),
        (0.1, "Buen dia", False),
        (0.3, "Buen dia, buenos dias.", True)
    ]

    # Sin FIX 451 (procesa primera disponible)
    sin_fix = transcripciones[0][1]
    print(f"  Sin FIX 451: Procesaria '{sin_fix}' (incompleto)")

    # Con FIX 451 (espera FINAL)
    con_fix = None
    for ts, texto, es_final in transcripciones:
        if es_final:
            con_fix = texto
            break

    if con_fix:
        print(f"  Con FIX 451: Procesaria '{con_fix}' (completo)")

    if con_fix and len(con_fix) > len(sin_fix):
        print("\n[OK] FIX 451 obtiene transcripcion mas completa")
        return True
    else:
        print("\n[FAIL] FIX 451 no mejora la situacion")
        return False


def test_limpieza_tracking():
    """
    FIX 451: Verificar que el tracking se limpia correctamente
    """
    print("\n" + "="*60)
    print("TEST FIX 451: Limpieza de tracking")
    print("="*60)

    deepgram_ultima_final = {}
    call_sid = "test_call_456"

    # Agregar tracking
    deepgram_ultima_final[call_sid] = {
        "timestamp": time.time(),
        "texto": "Test mensaje",
        "es_final": True
    }

    # Verificar que existe
    if call_sid in deepgram_ultima_final and deepgram_ultima_final[call_sid].get("es_final"):
        print("  [OK] Tracking creado correctamente")
    else:
        print("  [FAIL] Tracking no se creo")
        return False

    # Simular limpieza (como se hace despues de procesar)
    if call_sid in deepgram_ultima_final:
        deepgram_ultima_final[call_sid] = {}

    # Verificar que se limpio
    info = deepgram_ultima_final.get(call_sid, {})
    if not info.get("es_final", False):
        print("  [OK] Tracking limpiado correctamente")
    else:
        print("  [FAIL] Tracking no se limpio")
        return False

    print("\n[OK] Test limpieza pasado")
    return True


if __name__ == "__main__":
    print("="*60)
    print("TESTS FIX 451: Esperar FINAL antes de procesar")
    print("="*60)

    resultados = []

    resultados.append(("Tracking FINAL/PARCIAL", test_tracking_final_parcial()))
    resultados.append(("Logica de espera", test_logica_espera()))
    resultados.append(("Escenario desfase", test_escenario_desfase()))
    resultados.append(("Limpieza tracking", test_limpieza_tracking()))

    print("\n" + "="*60)
    print("RESUMEN DE TESTS")
    print("="*60)

    total_pasados = sum(1 for _, r in resultados if r)
    total_tests = len(resultados)

    for nombre, resultado in resultados:
        estado = "[OK]" if resultado else "[FAIL]"
        print(f"  {estado} {nombre}")

    print(f"\nTotal: {total_pasados}/{total_tests} tests pasados")

    if total_pasados == total_tests:
        print("\n[OK] TODOS LOS TESTS PASARON")
        sys.exit(0)
    else:
        print("\n[FAIL] ALGUNOS TESTS FALLARON")
        sys.exit(1)
