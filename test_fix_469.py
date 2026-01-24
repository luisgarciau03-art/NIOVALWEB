#!/usr/bin/env python3
"""
Test FIX 469: BRUCE1416 - Usar transcripciones acumuladas cuando timeout se agota

Problema: El loop de espera de Deepgram terminaba por timeout pero había
transcripciones FINAL acumuladas que se perdían.

Solución: Cuando el timeout se agota, verificar si hay transcripciones
acumuladas y usarlas en lugar de asumir que Deepgram no respondió.
"""

def test_fix_469():
    """Simular el comportamiento de FIX 469"""

    # Simular el escenario de BRUCE1416
    test_cases = [
        {
            "nombre": "BRUCE1416 - Dos transcripciones acumuladas",
            "transcripciones_acumuladas": ["Buen día.", "Sí. ¿Bueno?"],
            "esperado_contiene": "Buen día",
            "esperado_contiene_2": "Bueno"
        },
        {
            "nombre": "Una sola transcripción",
            "transcripciones_acumuladas": ["Hola, buenas tardes"],
            "esperado_contiene": "Hola, buenas tardes",
            "esperado_contiene_2": None
        },
        {
            "nombre": "Transcripciones duplicadas",
            "transcripciones_acumuladas": ["Buen día.", "Buen día", "¿Bueno?"],
            "esperado_contiene": "Buen día",
            "esperado_contiene_2": "Bueno"
        },
        {
            "nombre": "Sin transcripciones - debe fallar",
            "transcripciones_acumuladas": [],
            "esperado_contiene": None,
            "esperado_contiene_2": None
        }
    ]

    resultados = []

    for caso in test_cases:
        transcripciones_acumuladas = caso["transcripciones_acumuladas"]

        # Simular lógica de FIX 469
        usar_deepgram = False
        transcripcion_deepgram = None

        if transcripciones_acumuladas:
            if len(transcripciones_acumuladas) > 1:
                # Eliminar duplicados
                transcripciones_unicas = []
                for t in transcripciones_acumuladas:
                    t_normalizada = t.lower().strip().rstrip('.,;:!?')
                    es_duplicado = False
                    for existente in transcripciones_unicas:
                        existente_norm = existente.lower().strip().rstrip('.,;:!?')
                        if t_normalizada == existente_norm:
                            es_duplicado = True
                            break
                        if t_normalizada in existente_norm or existente_norm in t_normalizada:
                            if len(t) > len(existente):
                                transcripciones_unicas.remove(existente)
                                transcripciones_unicas.append(t)
                            es_duplicado = True
                            break
                    if not es_duplicado:
                        transcripciones_unicas.append(t)

                transcripcion_deepgram = " ".join(transcripciones_unicas)
            else:
                transcripcion_deepgram = transcripciones_acumuladas[0]

            usar_deepgram = True

        # Verificar resultado
        if caso["esperado_contiene"] is None:
            # Caso sin transcripciones
            exito = not usar_deepgram
        else:
            exito = (
                usar_deepgram and
                transcripcion_deepgram and
                caso["esperado_contiene"].lower() in transcripcion_deepgram.lower()
            )
            if caso["esperado_contiene_2"]:
                exito = exito and caso["esperado_contiene_2"].lower() in transcripcion_deepgram.lower()

        resultados.append({
            "nombre": caso["nombre"],
            "exito": exito,
            "resultado": transcripcion_deepgram,
            "usar_deepgram": usar_deepgram
        })

        status = "[OK]" if exito else "[FAIL]"
        print(f"{status} {caso['nombre']}")
        print(f"   Input: {transcripciones_acumuladas}")
        print(f"   Output: '{transcripcion_deepgram}'")
        print(f"   usar_deepgram: {usar_deepgram}")
        print()

    # Resumen
    exitosos = sum(1 for r in resultados if r["exito"])
    total = len(resultados)
    print(f"\n{'='*50}")
    print(f"Resultados: {exitosos}/{total} tests pasaron")

    return exitosos == total


if __name__ == "__main__":
    print("=" * 50)
    print("TEST FIX 469: Usar transcripciones acumuladas en timeout")
    print("=" * 50)
    print()

    exito = test_fix_469()

    if exito:
        print("\n[OK] Todos los tests pasaron")
    else:
        print("\n[FAIL] Algunos tests fallaron")

    exit(0 if exito else 1)
