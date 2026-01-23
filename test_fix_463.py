# -*- coding: utf-8 -*-
"""
Test para FIX 463: No detectar buzon si cliente ofrece WhatsApp

Problema: BRUCE1388 - Cliente dijo "si gusta dejar un mensaje a WhatsApp"
          FIX 105 detecto "dejar un mensaje" como buzon
          Pero era una persona real ofreciendo medio de contacto

Solucion: Verificar si el mensaje contiene WhatsApp/contacto antes de marcar como buzon
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def es_buzon_con_fix_463(speech_result: str) -> bool:
    """Simula la logica de deteccion de buzon con FIX 463"""
    keywords_buzon = [
        "buzon de voz", "deje su mensaje", "deja tu mensaje",
        "dejar un mensaje", "dejar mensaje", "despues del tono",
        "no puede atender", "no disponible en este momento"
    ]

    speech_lower = speech_result.lower() if speech_result else ""
    es_buzon = any(keyword in speech_lower for keyword in keywords_buzon)

    # FIX 463: NO detectar buzon si cliente OFRECE WhatsApp/contacto
    if es_buzon:
        cliente_ofrece_contacto = any(palabra in speech_lower for palabra in [
            'whatsapp', 'le compartimos', 'le comparto', 'le paso',
            'este numero', 'a este mismo', 'mi numero'
        ])
        if cliente_ofrece_contacto:
            es_buzon = False

    return es_buzon


def test_caso_bruce1388():
    """
    FIX 463: Simular caso BRUCE1388 - Falso positivo de buzon
    """
    print("\n" + "="*60)
    print("TEST: Caso BRUCE1388 - Falso positivo de buzon")
    print("="*60)

    mensaje = "Este, si gusta dejar un mensaje a WhatsApp y le compartimos los numeros."

    print(f"  Mensaje: '{mensaje}'")

    es_buzon = es_buzon_con_fix_463(mensaje)

    print(f"  Es buzon: {es_buzon}")

    if not es_buzon:
        print(f"\n[OK] FIX 463 NO detecta como buzon (correcto)")
        return True
    else:
        print(f"\n[FAIL] FIX 463 detecta como buzon (incorrecto)")
        return False


def test_buzon_real():
    """
    FIX 463: Verificar que buzon real SI se detecta
    """
    print("\n" + "="*60)
    print("TEST: Buzon real SI se detecta")
    print("="*60)

    casos_buzon_real = [
        "Por favor deje su mensaje despues del tono",
        "El buzon de voz esta lleno",
        "No puede atender su llamada, deje un mensaje",
        "Deja tu mensaje despues del tono",
    ]

    errores = []

    for mensaje in casos_buzon_real:
        es_buzon = es_buzon_con_fix_463(mensaje)

        if es_buzon:
            print(f"  [OK] '{mensaje[:50]}...' -> buzon=True")
        else:
            print(f"  [FAIL] '{mensaje[:50]}...' -> buzon=False")
            errores.append(mensaje)

    if errores:
        print(f"\n[FAIL] {len(errores)} buzones reales NO detectados")
        return False

    print(f"\n[OK] Todos los buzones reales detectados")
    return True


def test_no_buzon_con_whatsapp():
    """
    FIX 463: Mensajes con WhatsApp NO son buzon
    """
    print("\n" + "="*60)
    print("TEST: Mensajes con WhatsApp NO son buzon")
    print("="*60)

    casos_no_buzon = [
        "Si gusta dejar un mensaje a WhatsApp",
        "Puede dejar mensaje por WhatsApp",
        "Le compartimos el numero por WhatsApp",
        "A este numero le puede dejar un mensaje",
        "Le paso mi numero para que deje mensaje",
    ]

    errores = []

    for mensaje in casos_no_buzon:
        es_buzon = es_buzon_con_fix_463(mensaje)

        if not es_buzon:
            print(f"  [OK] '{mensaje[:50]}...' -> buzon=False")
        else:
            print(f"  [FAIL] '{mensaje[:50]}...' -> buzon=True")
            errores.append(mensaje)

    if errores:
        print(f"\n[FAIL] {len(errores)} mensajes detectados como buzon incorrectamente")
        return False

    print(f"\n[OK] Todos los mensajes con WhatsApp NO son buzon")
    return True


if __name__ == "__main__":
    print("="*60)
    print("TESTS FIX 463: No detectar buzon si cliente ofrece WhatsApp")
    print("="*60)

    resultados = []

    resultados.append(("Caso BRUCE1388", test_caso_bruce1388()))
    resultados.append(("Buzon real SI se detecta", test_buzon_real()))
    resultados.append(("Mensajes con WhatsApp NO son buzon", test_no_buzon_con_whatsapp()))

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
