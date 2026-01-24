#!/usr/bin/env python3
"""
Test FIX 470: BRUCE1412 - Detectar frases de espera y entrar en modo espera

Problema: Cliente dijo "Permitame un segundo" pero Bruce no lo detecto
y siguio pidiendo que le repitan hasta colgar automaticamente.

Solucion: Detectar frases de espera ANTES de la logica de frase incompleta,
establecer estado ESPERANDO_TRANSFERENCIA y usar timeout largo (30s).
"""

def test_fix_470():
    """Simular la deteccion de frases de espera"""

    frases_espera_cliente = [
        'permitame', 'permitame', 'permiteme', 'permiteme',
        'un momento', 'un momentito', 'un segundo', 'un segundito',
        'dame un momento', 'deme un momento', 'dame un segundo', 'deme un segundo',
        'espere', 'espereme', 'espereme', 'espera', 'esperame', 'esperame',
        'dejeme', 'dejeme', 'dejame', 'dejame',
        'aguarde', 'aguardeme', 'aguardeme', 'aguarda', 'aguardame',
        'tantito', 'un tantito', 'ahi le', 'ahorita le', 'ahorita te',
        'voy a ver', 'dejeme ver', 'dejeme ver', 'dejame ver', 'dejame ver',
        'ahorita se lo paso', 'se lo paso', 'le paso', 'te paso', 'ahorita lo paso',
        'en un momento', 'un minuto', 'un minutito'
    ]

    test_cases = [
        {
            "nombre": "BRUCE1412 - Permitame un segundo",
            "frase": "Permitame un segundo.",
            "debe_detectar": True
        },
        {
            "nombre": "Un momento por favor",
            "frase": "Un momento, por favor.",
            "debe_detectar": True
        },
        {
            "nombre": "Ahorita se lo paso",
            "frase": "Ahorita se lo paso.",
            "debe_detectar": True
        },
        {
            "nombre": "Espere tantito",
            "frase": "Espere tantito.",
            "debe_detectar": True
        },
        {
            "nombre": "Dejeme ver",
            "frase": "Dejeme ver si esta.",
            "debe_detectar": True
        },
        {
            "nombre": "Buenos dias (NO debe detectar)",
            "frase": "Buenos dias.",
            "debe_detectar": False
        },
        {
            "nombre": "No esta disponible (NO debe detectar)",
            "frase": "No esta disponible.",
            "debe_detectar": False
        },
        {
            "nombre": "Cual es su correo (NO debe detectar)",
            "frase": "Cual es su correo?",
            "debe_detectar": False
        }
    ]

    resultados = []

    for caso in test_cases:
        frase_limpia = caso["frase"].strip().lower()
        cliente_pidio_espera = any(frase in frase_limpia for frase in frases_espera_cliente)

        exito = cliente_pidio_espera == caso["debe_detectar"]

        resultados.append({
            "nombre": caso["nombre"],
            "exito": exito,
            "frase": caso["frase"],
            "detectado": cliente_pidio_espera,
            "esperado": caso["debe_detectar"]
        })

        status = "[OK]" if exito else "[FAIL]"
        print(f"{status} {caso['nombre']}")
        print(f"   Frase: '{caso['frase']}'")
        print(f"   Detectado: {cliente_pidio_espera}, Esperado: {caso['debe_detectar']}")
        print()

    # Resumen
    exitosos = sum(1 for r in resultados if r["exito"])
    total = len(resultados)
    print(f"\n{'='*50}")
    print(f"Resultados: {exitosos}/{total} tests pasaron")

    return exitosos == total


if __name__ == "__main__":
    print("=" * 50)
    print("TEST FIX 470: Detectar frases de espera")
    print("=" * 50)
    print()

    exito = test_fix_470()

    if exito:
        print("\n[OK] Todos los tests pasaron")
    else:
        print("\n[FAIL] Algunos tests fallaron")

    exit(0 if exito else 1)
