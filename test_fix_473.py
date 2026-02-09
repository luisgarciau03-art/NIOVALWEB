#!/usr/bin/env python3
"""
Test FIX 473: BRUCE1425 - Reconocer frases de cortesia como respuestas completas

Problema: Cliente dijo "Buen dia, a sus ordenes." pero Bruce trato como frase
incompleta y espero 1.5s por continuacion. El cliente colgo.

Solucion: Detectar frases de cortesia tipicas de Mexico como respuestas completas:
- "a sus ordenes"
- "para servirle"
- "en que le puedo ayudar"
"""

def test_fix_473():
    """Simular la deteccion de frases de cortesia"""

    frases_cortesia = [
        'a sus órdenes', 'a sus ordenes', 'a tus órdenes', 'a tus ordenes',
        'para servirle', 'para servirte', 'en qué le puedo ayudar', 'en que le puedo ayudar',
        'en qué puedo servirle', 'en que puedo servirle', 'cómo le puedo ayudar',
        'como le puedo ayudar', 'a la orden', 'a sus órdenes señor', 'a sus ordenes señor',
        'con mucho gusto', 'a la brevedad'
    ]

    test_cases = [
        {
            "nombre": "BRUCE1425 - Buen dia a sus ordenes",
            "frase": "Buen día, a sus órdenes.",
            "debe_detectar": True
        },
        {
            "nombre": "A sus ordenes simple",
            "frase": "A sus órdenes.",
            "debe_detectar": True
        },
        {
            "nombre": "Para servirle",
            "frase": "Buenas tardes, para servirle.",
            "debe_detectar": True
        },
        {
            "nombre": "En que le puedo ayudar",
            "frase": "¿En qué le puedo ayudar?",
            "debe_detectar": True
        },
        {
            "nombre": "A la orden",
            "frase": "Hola, a la orden.",
            "debe_detectar": True
        },
        {
            "nombre": "Buenos dias (NO es cortesia, es saludo)",
            "frase": "Buenos días.",
            "debe_detectar": False
        },
        {
            "nombre": "Hola (NO es cortesia)",
            "frase": "Hola",
            "debe_detectar": False
        },
        {
            "nombre": "Con mucho gusto",
            "frase": "Con mucho gusto, digame.",
            "debe_detectar": True
        }
    ]

    resultados = []

    for caso in test_cases:
        frase_limpia = caso["frase"].strip().lower()
        frase_es_cortesia = any(cortesia in frase_limpia for cortesia in frases_cortesia)

        exito = frase_es_cortesia == caso["debe_detectar"]

        resultados.append({
            "nombre": caso["nombre"],
            "exito": exito,
            "frase": caso["frase"],
            "detectado": frase_es_cortesia,
            "esperado": caso["debe_detectar"]
        })

        status = "[OK]" if exito else "[FAIL]"
        print(f"{status} {caso['nombre']}")
        print(f"   Frase: '{caso['frase']}'")
        print(f"   Detectado: {frase_es_cortesia}, Esperado: {caso['debe_detectar']}")
        print()

    # Resumen
    exitosos = sum(1 for r in resultados if r["exito"])
    total = len(resultados)
    print(f"\n{'='*50}")
    print(f"Resultados: {exitosos}/{total} tests pasaron")

    return exitosos == total


if __name__ == "__main__":
    print("=" * 50)
    print("TEST FIX 473: Detectar frases de cortesia")
    print("=" * 50)
    print()

    exito = test_fix_473()

    if exito:
        print("\n[OK] Todos los tests pasaron")
    else:
        print("\n[FAIL] Algunos tests fallaron")

    exit(0 if exito else 1)
