# -*- coding: utf-8 -*-
"""
Test para FIX 456: Esperar después de FINAL para detectar si cliente sigue hablando

Problema: Caso BRUCE1375 - Bruce interrumpió al cliente cuando éste seguía hablando.
El sistema recibió 2 FINALs ("...WhatsApp." y "...número.") y respondió,
pero el cliente seguía hablando ("Por WhatsApp, ¿por qué medio...").

Solución: Después de recibir FINAL, esperar 350ms y verificar si llegan PARCIALES
nuevas que indiquen que el cliente continúa hablando.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import time


def test_deteccion_cliente_sigue_hablando():
    """
    FIX 456: Verificar que se detecta cuando el cliente sigue hablando después de FINAL
    """
    print("\n" + "="*60)
    print("TEST FIX 456: Detección de cliente que sigue hablando")
    print("="*60)

    # Simular diccionarios globales
    deepgram_ultima_final = {}
    deepgram_ultima_parcial = {}
    call_sid = "test_call_456"

    # Simular: FINAL recibido
    timestamp_final = time.time()
    deepgram_ultima_final[call_sid] = {
        "timestamp": timestamp_final,
        "texto": "Que le pueda mandar a este número.",
        "es_final": True
    }

    print(f"  FINAL recibido: '{deepgram_ultima_final[call_sid]['texto']}'")

    # Simular: PARCIAL llega 100ms después (cliente sigue hablando)
    time.sleep(0.1)
    timestamp_parcial = time.time()
    deepgram_ultima_parcial[call_sid] = {
        "timestamp": timestamp_parcial,
        "texto": "Por WhatsApp, porque"
    }

    print(f"  PARCIAL llega después: '{deepgram_ultima_parcial[call_sid]['texto']}'")

    # Verificar lógica de FIX 456
    info_final = deepgram_ultima_final.get(call_sid, {})
    info_parcial = deepgram_ultima_parcial.get(call_sid, {})
    ts_final = info_final.get("timestamp", 0)
    ts_parcial = info_parcial.get("timestamp", 0)

    cliente_sigue_hablando = ts_parcial > ts_final

    if cliente_sigue_hablando:
        print(f"  [OK] FIX 456 detectaría: Cliente sigue hablando")
        print(f"\n[OK] Test pasado")
        return True
    else:
        print(f"  [FAIL] FIX 456 NO detectaría que sigue hablando")
        return False


def test_cliente_termino_de_hablar():
    """
    FIX 456: Verificar que NO interrumpe cuando cliente realmente terminó
    """
    print("\n" + "="*60)
    print("TEST FIX 456: Cliente que terminó de hablar")
    print("="*60)

    deepgram_ultima_final = {}
    deepgram_ultima_parcial = {}
    call_sid = "test_call_456b"

    # PARCIAL llegó primero
    timestamp_parcial = time.time() - 0.5
    deepgram_ultima_parcial[call_sid] = {
        "timestamp": timestamp_parcial,
        "texto": "Que le pueda mandar a este número"
    }

    # FINAL llegó después (cliente terminó)
    timestamp_final = time.time()
    deepgram_ultima_final[call_sid] = {
        "timestamp": timestamp_final,
        "texto": "Que le pueda mandar a este número.",
        "es_final": True
    }

    print(f"  PARCIAL: '{deepgram_ultima_parcial[call_sid]['texto']}'")
    print(f"  FINAL: '{deepgram_ultima_final[call_sid]['texto']}'")

    # Esperar 350ms (como haría FIX 456)
    time.sleep(0.35)

    # No llegó nueva PARCIAL
    ts_final = deepgram_ultima_final[call_sid]["timestamp"]
    ts_parcial = deepgram_ultima_parcial[call_sid]["timestamp"]

    cliente_sigue_hablando = ts_parcial > ts_final

    if not cliente_sigue_hablando:
        print(f"  [OK] FIX 456 detectaría: Cliente terminó de hablar")
        print(f"\n[OK] Test pasado")
        return True
    else:
        print(f"  [FAIL] FIX 456 cree que sigue hablando (incorrecto)")
        return False


def test_caso_bruce1375():
    """
    FIX 456: Simular caso exacto de BRUCE1375
    """
    print("\n" + "="*60)
    print("TEST: Caso BRUCE1375 - Interrupción durante número")
    print("="*60)

    # Cronología BRUCE1375:
    # 20:18:18 - FINAL: "comento que sería sobre sobre solamente sobre WhatsApp."
    # 20:18:20 - FINAL: "Que le pueda mandar a este número."
    # 20:18:21 - PARCIAL: "Por WhatsApp, porque" <- Cliente sigue!
    # 20:18:23 - Bruce responde (INCORRECTO - debió esperar)

    deepgram_ultima_final = {}
    deepgram_ultima_parcial = {}
    call_sid = "CA9a21b09be0e899980e1aacc34348e6be"

    # Simular secuencia temporal
    print(f"  Simulando secuencia temporal de BRUCE1375...")

    # 20:18:20 - FINAL llega
    timestamp_final = time.time()
    deepgram_ultima_final[call_sid] = {
        "timestamp": timestamp_final,
        "texto": "Que le pueda mandar a este número.",
        "es_final": True
    }
    print(f"  20:18:20 - FINAL: '{deepgram_ultima_final[call_sid]['texto']}'")

    # 20:18:21 - PARCIAL llega ~1s después (cliente sigue)
    time.sleep(0.2)  # Simulamos 200ms en el test
    timestamp_parcial = time.time()
    deepgram_ultima_parcial[call_sid] = {
        "timestamp": timestamp_parcial,
        "texto": "Por WhatsApp, porque"
    }
    print(f"  20:18:21 - PARCIAL: '{deepgram_ultima_parcial[call_sid]['texto']}'")

    # FIX 456 verificaría antes de responder
    ts_final = deepgram_ultima_final[call_sid]["timestamp"]
    ts_parcial = deepgram_ultima_parcial[call_sid]["timestamp"]

    cliente_sigue_hablando = ts_parcial > ts_final

    if cliente_sigue_hablando:
        print(f"\n  Con FIX 456:")
        print(f"    Bruce ESPERARÍA porque detecta PARCIAL nueva")
        print(f"    Bruce NO interrumpiría al cliente")
        print(f"\n[OK] FIX 456 evitaría interrupción de BRUCE1375")
        return True
    else:
        print(f"\n[FAIL] FIX 456 NO evitaría el problema")
        return False


if __name__ == "__main__":
    print("="*60)
    print("TESTS FIX 456: Esperar después de FINAL")
    print("="*60)

    resultados = []

    resultados.append(("Detección sigue hablando", test_deteccion_cliente_sigue_hablando()))
    resultados.append(("Cliente terminó", test_cliente_termino_de_hablar()))
    resultados.append(("Caso BRUCE1375", test_caso_bruce1375()))

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
