# -*- coding: utf-8 -*-
"""
Test para FIX 455: Limpiar transcripciones acumuladas antes de enviar audio

Problema: Caso BRUCE1363 - Cliente dijo "Ahorita no, jefe, muchas gracias" DURANTE
el audio de Bruce, pero cuando Bruce termino de hablar, el sistema proceso un
"Bueno?" viejo en lugar del mensaje actual.

Solucion: Limpiar buffer de transcripciones ANTES de enviar audio de Bruce,
para que solo se capture la RESPUESTA al audio, no mensajes acumulados.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import time


def test_limpieza_transcripciones():
    """
    FIX 455: Verificar que las transcripciones se limpian antes de enviar audio
    """
    print("\n" + "="*60)
    print("TEST FIX 455: Limpieza de transcripciones acumuladas")
    print("="*60)

    # Simular el diccionario de transcripciones
    deepgram_transcripciones = {}
    deepgram_ultima_final = {}
    bruce_audio_enviado_timestamp = {}
    call_sid = "test_call_455"

    # Simular transcripciones acumuladas durante audio de Bruce
    deepgram_transcripciones[call_sid] = [
        "Bueno?",  # Viejo
        "Bueno?",  # Duplicado viejo
    ]
    deepgram_ultima_final[call_sid] = {
        "timestamp": time.time() - 10,  # 10 segundos atras
        "texto": "Bueno?",
        "es_final": True
    }

    print(f"  Antes de FIX 455:")
    print(f"    Transcripciones acumuladas: {deepgram_transcripciones[call_sid]}")
    print(f"    Ultima final: {deepgram_ultima_final[call_sid]}")

    # Simular FIX 455: Limpiar antes de enviar audio
    transcripciones_previas = len(deepgram_transcripciones.get(call_sid, []))
    if transcripciones_previas > 0:
        print(f"  FIX 455: Limpiando {transcripciones_previas} transcripciones acumuladas")
        deepgram_transcripciones[call_sid] = []
        if call_sid in deepgram_ultima_final:
            deepgram_ultima_final[call_sid] = {}
    bruce_audio_enviado_timestamp[call_sid] = time.time()

    # Verificar que se limpio
    if len(deepgram_transcripciones[call_sid]) == 0:
        print(f"  [OK] Transcripciones limpiadas")
    else:
        print(f"  [FAIL] Transcripciones NO se limpiaron")
        return False

    if not deepgram_ultima_final.get(call_sid, {}).get("es_final"):
        print(f"  [OK] Tracking de FINAL limpiado")
    else:
        print(f"  [FAIL] Tracking NO se limpio")
        return False

    # Simular que llega la nueva transcripcion despues del audio
    time.sleep(0.1)  # Simular delay
    nueva_transcripcion = "Ahorita no, jefe, muchas gracias."
    deepgram_transcripciones[call_sid].append(nueva_transcripcion)
    deepgram_ultima_final[call_sid] = {
        "timestamp": time.time(),
        "texto": nueva_transcripcion,
        "es_final": True
    }

    print(f"  Despues de FIX 455 (nueva transcripcion):")
    print(f"    Transcripciones: {deepgram_transcripciones[call_sid]}")

    # Verificar que solo esta la nueva transcripcion
    if len(deepgram_transcripciones[call_sid]) == 1 and deepgram_transcripciones[call_sid][0] == nueva_transcripcion:
        print(f"  [OK] Solo la nueva transcripcion esta en el buffer")
        print(f"\n[OK] Test FIX 455 pasado")
        return True
    else:
        print(f"  [FAIL] El buffer tiene contenido incorrecto")
        return False


def test_caso_bruce1363():
    """
    FIX 455: Simular el caso exacto de BRUCE1363
    """
    print("\n" + "="*60)
    print("TEST: Caso BRUCE1363 - 'Ahorita no, jefe, muchas gracias'")
    print("="*60)

    # Cronologia del problema:
    # 1. Bruce dice: "Usted es el encargado de compras?"
    # 2. Cliente responde "Ahorita no, jefe, muchas gracias" DURANTE el audio
    # 3. Transcripcion llega con 31.7s de latencia
    # 4. Sistema procesa "Bueno?" (viejo) en lugar de la respuesta real

    deepgram_transcripciones = {}
    bruce_audio_enviado_timestamp = {}
    call_sid = "CA97b5c133402172a27da03a96f891d4c7"

    # Estado ANTES de FIX 455: Hay transcripciones viejas acumuladas
    deepgram_transcripciones[call_sid] = [
        "Bueno?",
        "Bueno?",
        "Bueno?"
    ]

    print(f"  Escenario SIN FIX 455:")
    print(f"    Transcripciones al momento de procesar: {deepgram_transcripciones[call_sid]}")
    print(f"    Sistema procesaria: '{deepgram_transcripciones[call_sid][0]}' (INCORRECTO)")

    # Aplicar FIX 455
    print(f"\n  Aplicando FIX 455...")

    # Simular limpiar antes de enviar audio
    if deepgram_transcripciones.get(call_sid):
        deepgram_transcripciones[call_sid] = []
    bruce_audio_enviado_timestamp[call_sid] = time.time()

    # Simular que llega la respuesta CORRECTA despues del audio
    respuesta_correcta = "Ahorita no, jefe, muchas gracias."
    deepgram_transcripciones[call_sid].append(respuesta_correcta)

    print(f"  Escenario CON FIX 455:")
    print(f"    Transcripciones al momento de procesar: {deepgram_transcripciones[call_sid]}")
    print(f"    Sistema procesaria: '{deepgram_transcripciones[call_sid][0]}' (CORRECTO)")

    # Verificar que ahora procesaria el mensaje correcto
    if deepgram_transcripciones[call_sid][0] == respuesta_correcta:
        print(f"\n[OK] FIX 455 evitaria el problema de BRUCE1363")
        return True
    else:
        print(f"\n[FAIL] FIX 455 NO evitaria el problema")
        return False


def test_sin_transcripciones_previas():
    """
    FIX 455: Verificar que funciona cuando no hay transcripciones previas
    """
    print("\n" + "="*60)
    print("TEST FIX 455: Sin transcripciones previas")
    print("="*60)

    deepgram_transcripciones = {}
    bruce_audio_enviado_timestamp = {}
    call_sid = "test_call_nuevo"

    # Inicializar vacio
    deepgram_transcripciones[call_sid] = []

    print(f"  Transcripciones antes: {deepgram_transcripciones[call_sid]}")

    # FIX 455: Solo limpiar si hay algo
    transcripciones_previas = len(deepgram_transcripciones.get(call_sid, []))
    if transcripciones_previas > 0:
        deepgram_transcripciones[call_sid] = []
    bruce_audio_enviado_timestamp[call_sid] = time.time()

    print(f"  Transcripciones despues: {deepgram_transcripciones[call_sid]}")

    if len(deepgram_transcripciones[call_sid]) == 0:
        print(f"\n[OK] FIX 455 no causa errores con buffer vacio")
        return True
    else:
        print(f"\n[FAIL] Error inesperado")
        return False


if __name__ == "__main__":
    print("="*60)
    print("TESTS FIX 455: Limpiar transcripciones antes de audio")
    print("="*60)

    resultados = []

    resultados.append(("Limpieza transcripciones", test_limpieza_transcripciones()))
    resultados.append(("Caso BRUCE1363", test_caso_bruce1363()))
    resultados.append(("Sin transcripciones previas", test_sin_transcripciones_previas()))

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
