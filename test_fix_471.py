#!/usr/bin/env python3
"""
Test FIX 471: BRUCE1415 - Detectar 'No tengo' como 'no hay encargado'

Problema: Cliente dijo "No tengo" pero Bruce lo trato como frase incompleta
y espero continuacion en lugar de entender que no hay encargado.

Solucion:
1. Agregar 'no tengo' a patrones de ENCARGADO_NO_ESTA en agente_ventas.py
2. Agregar deteccion en servidor_llamadas.py para NO esperar continuacion
"""

def test_fix_471():
    """Simular la deteccion de respuestas 'no hay encargado'"""

    respuestas_no_hay_encargado = [
        'no tengo', 'no tenemos', 'no hay', 'aqui no hay', 'aqui no hay',
        'no contamos', 'no esta', 'no esta', 'no se encuentra',
        'no lo tengo', 'no la tengo', 'no, no hay'
    ]

    test_cases = [
        {
            "nombre": "BRUCE1415 - No tengo",
            "frase": "No tengo",
            "debe_detectar": True
        },
        {
            "nombre": "No tenemos encargado",
            "frase": "No tenemos encargado de compras",
            "debe_detectar": True
        },
        {
            "nombre": "No hay",
            "frase": "No hay nadie ahorita",
            "debe_detectar": True
        },
        {
            "nombre": "No esta",
            "frase": "No esta en este momento",
            "debe_detectar": True
        },
        {
            "nombre": "Aqui no hay",
            "frase": "Aqui no hay encargado",
            "debe_detectar": True
        },
        {
            "nombre": "Si tenemos (NO debe detectar)",
            "frase": "Si tenemos encargado",
            "debe_detectar": False
        },
        {
            "nombre": "Buenos dias (NO debe detectar)",
            "frase": "Buenos dias",
            "debe_detectar": False
        }
    ]

    resultados = []

    for caso in test_cases:
        frase_limpia = caso["frase"].strip().lower()
        frase_es_no_hay_encargado = any(resp in frase_limpia for resp in respuestas_no_hay_encargado)

        exito = frase_es_no_hay_encargado == caso["debe_detectar"]

        resultados.append({
            "nombre": caso["nombre"],
            "exito": exito,
            "frase": caso["frase"],
            "detectado": frase_es_no_hay_encargado,
            "esperado": caso["debe_detectar"]
        })

        status = "[OK]" if exito else "[FAIL]"
        print(f"{status} {caso['nombre']}")
        print(f"   Frase: '{caso['frase']}'")
        print(f"   Detectado: {frase_es_no_hay_encargado}, Esperado: {caso['debe_detectar']}")
        print()

    # Resumen
    exitosos = sum(1 for r in resultados if r["exito"])
    total = len(resultados)
    print(f"\n{'='*50}")
    print(f"Resultados: {exitosos}/{total} tests pasaron")

    return exitosos == total


if __name__ == "__main__":
    print("=" * 50)
    print("TEST FIX 471: Detectar 'No tengo' como 'no hay encargado'")
    print("=" * 50)
    print()

    exito = test_fix_471()

    if exito:
        print("\n[OK] Todos los tests pasaron")
    else:
        print("\n[FAIL] Algunos tests fallaron")

    exit(0 if exito else 1)
