#!/usr/bin/env python3
"""
Test FIX 474: BRUCE1433 - Detectar 'volver cuando llegue el dueño'

Problema: Cliente dijo "mejor cuando venga el dueño, al rato llega"
pero Bruce ofreció catálogo en lugar de preguntar a qué hora volver a llamar.

Solución: Detectar patrones que indican que el cliente quiere que Bruce
vuelva a llamar cuando llegue el dueño/encargado, y responder preguntando
a qué hora volver a llamar.
"""

def test_fix_474():
    """Simular la detección de 'volver cuando llegue el dueño'"""

    # Patrones que indican "vuelva a llamar cuando llegue el dueño/encargado"
    patrones_volver_llamar = [
        # Variantes de "cuando venga/llegue el dueño/encargado"
        'cuando venga el dueño', 'cuando venga el dueno', 'cuando venga el encargado',
        'cuando llegue el dueño', 'cuando llegue el dueno', 'cuando llegue el encargado',
        'mejor cuando venga', 'mejor cuando llegue', 'mejor cuando esté', 'mejor cuando este',
        # "Al rato llega" = el dueño/encargado llegará pronto
        'al rato llega', 'ahorita llega', 'ahorita viene', 'al rato viene',
        'más tarde llega', 'mas tarde llega', 'más tarde viene', 'mas tarde viene',
        'en un rato llega', 'en un rato viene', 'ya mero llega', 'ya mero viene',
        'ahorita no está pero', 'ahorita no esta pero', 'no está pero al rato', 'no esta pero al rato',
        # Variantes directas de "vuelva a llamar"
        'vuelva cuando', 'vuelva a llamar cuando', 'llame cuando', 'marque cuando'
    ]

    test_cases = [
        {
            "nombre": "BRUCE1433 - Mejor cuando venga el dueño, al rato llega",
            "frase": "Pues ahí mejor cuando venga el dueño, oiga, al rato llega.",
            "debe_detectar": True
        },
        {
            "nombre": "Cuando llegue el encargado",
            "frase": "No, mejor cuando llegue el encargado.",
            "debe_detectar": True
        },
        {
            "nombre": "Al rato llega el jefe",
            "frase": "Al rato llega el jefe, si gusta.",
            "debe_detectar": True
        },
        {
            "nombre": "Ahorita llega",
            "frase": "Ahorita llega, espérese tantito.",
            "debe_detectar": True
        },
        {
            "nombre": "Más tarde viene",
            "frase": "Más tarde viene el dueño.",
            "debe_detectar": True
        },
        {
            "nombre": "Vuelva a llamar cuando esté",
            "frase": "Vuelva a llamar cuando esté el encargado.",
            "debe_detectar": True
        },
        {
            "nombre": "En un rato llega",
            "frase": "En un rato llega, si gusta marcar después.",
            "debe_detectar": True
        },
        {
            "nombre": "No está (NO debe detectar - es diferente)",
            "frase": "No está el encargado.",
            "debe_detectar": False
        },
        {
            "nombre": "Buenos días (NO debe detectar)",
            "frase": "Buenos días, a sus órdenes.",
            "debe_detectar": False
        },
        {
            "nombre": "Sí me interesa (NO debe detectar)",
            "frase": "Sí me interesa, mándeme el catálogo.",
            "debe_detectar": False
        },
        {
            "nombre": "Ya mero llega",
            "frase": "Ya mero llega el patrón.",
            "debe_detectar": True
        },
        {
            "nombre": "Ahorita no está pero al rato",
            "frase": "Ahorita no está pero al rato llega.",
            "debe_detectar": True
        }
    ]

    resultados = []

    for caso in test_cases:
        frase_limpia = caso["frase"].strip().lower()
        cliente_quiere_volver = any(patron in frase_limpia for patron in patrones_volver_llamar)

        exito = cliente_quiere_volver == caso["debe_detectar"]

        resultados.append({
            "nombre": caso["nombre"],
            "exito": exito,
            "frase": caso["frase"],
            "detectado": cliente_quiere_volver,
            "esperado": caso["debe_detectar"]
        })

        status = "[OK]" if exito else "[FAIL]"
        print(f"{status} {caso['nombre']}")
        print(f"   Frase: '{caso['frase']}'")
        print(f"   Detectado: {cliente_quiere_volver}, Esperado: {caso['debe_detectar']}")
        print()

    # Resumen
    exitosos = sum(1 for r in resultados if r["exito"])
    total = len(resultados)
    print(f"\n{'='*50}")
    print(f"Resultados: {exitosos}/{total} tests pasaron")

    return exitosos == total


if __name__ == "__main__":
    print("=" * 50)
    print("TEST FIX 474: Detectar 'volver cuando llegue el dueño'")
    print("=" * 50)
    print()

    exito = test_fix_474()

    if exito:
        print("\n[OK] Todos los tests pasaron")
    else:
        print("\n[FAIL] Algunos tests fallaron")

    exit(0 if exito else 1)
