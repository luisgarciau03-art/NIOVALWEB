#!/usr/bin/env python3
"""
Test FIX 472: BRUCE1419 - No esperar continuacion cuando cliente responde "No" a pregunta de encargado

Problema: Cliente dijo "No." en respuesta a "Se encontrara el encargado?"
pero Bruce trato como frase incompleta y espero 1.5s, causando delay de 5+ segundos.
El cliente pregunto "Bueno?" impaciente y colgo.

Solucion: Detectar que si Bruce pregunto por encargado y cliente responde solo "No",
es una respuesta COMPLETA y no hay que esperar continuacion.
"""

def test_fix_472():
    """Simular la deteccion de 'No' como respuesta completa a pregunta de encargado"""

    # Patrones que indican que Bruce pregunto por encargado
    patrones_pregunta_encargado = [
        'encargado', 'encargada', 'quien ve las compras', 'quien maneja las compras',
        'responsable de compras', 'se encontrara', 'se encuentra'
    ]

    test_cases = [
        {
            "nombre": "BRUCE1419 - No a pregunta de encargado",
            "ultimo_bruce": "Me comunico de la marca nioval, mas que nada queria brindar informacion de nuestros productos ferreteros. Se encontrara el encargado o encargada de compras?",
            "cliente_dijo": "No.",
            "debe_responder_inmediato": True
        },
        {
            "nombre": "No gracias a pregunta de encargado",
            "ultimo_bruce": "Se encuentra el encargado de compras?",
            "cliente_dijo": "No, gracias.",
            "debe_responder_inmediato": True
        },
        {
            "nombre": "No no a pregunta de encargado",
            "ultimo_bruce": "Se encuentra la encargada?",
            "cliente_dijo": "No, no.",
            "debe_responder_inmediato": True
        },
        {
            "nombre": "No a saludo (NO aplica FIX 472)",
            "ultimo_bruce": "Hola, buen dia. Le llamo de nioval.",
            "cliente_dijo": "No.",
            "debe_responder_inmediato": False
        },
        {
            "nombre": "Si tenemos (NO aplica FIX 472)",
            "ultimo_bruce": "Se encuentra el encargado de compras?",
            "cliente_dijo": "Si, un momento.",
            "debe_responder_inmediato": False  # FIX 472 no aplica, pero otros FIX si
        },
        {
            "nombre": "No tengo encargado (FIX 471 aplica, no 472)",
            "ultimo_bruce": "Se encuentra el encargado de compras?",
            "cliente_dijo": "No tengo encargado.",
            "debe_responder_inmediato": True  # FIX 471 aplica aqui
        }
    ]

    resultados = []

    for caso in test_cases:
        ultimo_bruce = caso["ultimo_bruce"].lower()
        cliente_dijo = caso["cliente_dijo"]
        frase_limpia = cliente_dijo.strip().lower()

        # Logica FIX 472
        import re
        bruce_pregunto_encargado = any(p in ultimo_bruce for p in patrones_pregunta_encargado)
        frase_sin_puntuacion = re.sub(r'[.,;:!?]', '', frase_limpia).strip()
        cliente_dijo_solo_no = frase_sin_puntuacion in ['no', 'no gracias', 'no no']

        fix_472_aplica = bruce_pregunto_encargado and cliente_dijo_solo_no

        # Logica FIX 471 (para casos de "no tengo", etc.)
        respuestas_no_hay_encargado = [
            'no tengo', 'no tenemos', 'no hay', 'aqui no hay',
            'no contamos', 'no esta', 'no se encuentra'
        ]
        fix_471_aplica = any(resp in frase_limpia for resp in respuestas_no_hay_encargado)

        respuesta_inmediata = fix_472_aplica or fix_471_aplica

        exito = respuesta_inmediata == caso["debe_responder_inmediato"]

        resultados.append({
            "nombre": caso["nombre"],
            "exito": exito,
            "fix_472": fix_472_aplica,
            "fix_471": fix_471_aplica,
            "respuesta_inmediata": respuesta_inmediata,
            "esperado": caso["debe_responder_inmediato"]
        })

        status = "[OK]" if exito else "[FAIL]"
        print(f"{status} {caso['nombre']}")
        print(f"   Cliente: '{caso['cliente_dijo']}'")
        print(f"   Bruce pregunto encargado: {bruce_pregunto_encargado}")
        print(f"   FIX 472 aplica: {fix_472_aplica}, FIX 471 aplica: {fix_471_aplica}")
        print(f"   Respuesta inmediata: {respuesta_inmediata}, Esperado: {caso['debe_responder_inmediato']}")
        print()

    # Resumen
    exitosos = sum(1 for r in resultados if r["exito"])
    total = len(resultados)
    print(f"\n{'='*50}")
    print(f"Resultados: {exitosos}/{total} tests pasaron")

    return exitosos == total


if __name__ == "__main__":
    print("=" * 50)
    print("TEST FIX 472: 'No' como respuesta a pregunta de encargado")
    print("=" * 50)
    print()

    exito = test_fix_472()

    if exito:
        print("\n[OK] Todos los tests pasaron")
    else:
        print("\n[FAIL] Algunos tests fallaron")

    exit(0 if exito else 1)
