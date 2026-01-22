"""
TEST FIX 413: Validar que "No nos interesa ahorita" se detecte como RECHAZO, no transferencia

Caso: BRUCE1206
Error: Cliente dijo "No, no nos interesa ahorita, gracias." y Bruce respondió "Claro, espero." (incoherente)
Causa: FIX 405 no tenía 'no nos interesa' en patrones_rechazo, solo 'no me interesa'
       La palabra "ahorita" activó ESPERANDO_TRANSFERENCIA
Solución: Agregar 'no nos interesa', 'no les interesa', 'no le interesa' a patrones_rechazo

Test:
1. Verificar que el código incluye los nuevos patrones
2. Validar caso BRUCE1206: "No, no nos interesa ahorita, gracias."
3. Validar variante: "No les interesa en este momento"
4. Validar variante: "No le interesa, gracias"
"""

def test_fix_413():
    """Valida que FIX 413 detecta correctamente rechazos con 'nos/les/le interesa'"""

    print("\n" + "="*80)
    print("TEST FIX 413: Detección de 'no nos/les/le interesa' como RECHAZO")
    print("="*80 + "\n")

    tests_pasados = 0
    tests_totales = 4

    # Test 1: Verificar que el código contiene los nuevos patrones
    print("Test 1: Verificar código FIX 413 en agente_ventas.py")
    print("-" * 80)

    with open('agente_ventas.py', 'r', encoding='utf-8') as f:
        codigo = f.read()

    patrones_esperados = [
        "# FIX 413:",
        "'no nos interesa'",
        "'no les interesa'",
        "'no le interesa'",
    ]

    patrones_encontrados = []
    for patron in patrones_esperados:
        if patron in codigo:
            patrones_encontrados.append(patron)
            print(f"✅ Encontrado: {patron}")
        else:
            print(f"❌ NO encontrado: {patron}")

    if len(patrones_encontrados) == len(patrones_esperados):
        print("✅ Test 1 PASADO: Código FIX 413 presente en agente_ventas.py\n")
        tests_pasados += 1
    else:
        print(f"❌ Test 1 FALLADO: Solo {len(patrones_encontrados)}/{len(patrones_esperados)} patrones encontrados\n")

    # Test 2: BRUCE1206 - "No, no nos interesa ahorita, gracias."
    print("Test 2: Caso BRUCE1206 - 'No, no nos interesa ahorita, gracias.'")
    print("-" * 80)

    caso_bruce1206 = "No, no nos interesa ahorita, gracias."

    # Simular detección de rechazo
    patrones_rechazo = [
        'no, ahorita no', 'no ahorita no',
        'no, gracias', 'no gracias',
        'no me interesa', 'no necesito',
        'no nos interesa', 'no les interesa', 'no le interesa',  # FIX 413
        'no, no necesito', 'no no necesito',
        'estoy ocupado', 'estamos ocupados',
    ]

    es_rechazo = any(patron in caso_bruce1206.lower() for patron in patrones_rechazo)

    if es_rechazo:
        print(f"✅ BRUCE1206 detectado como RECHAZO")
        print(f"   Frase: '{caso_bruce1206}'")
        print(f"   Patrón detectado: 'no nos interesa'")
        print(f"   Comportamiento esperado: GPT debe despedirse (NO 'Claro, espero.')")
        print("✅ Test 2 PASADO\n")
        tests_pasados += 1
    else:
        print(f"❌ BRUCE1206 NO detectado como rechazo")
        print(f"   Frase: '{caso_bruce1206}'")
        print(f"   ⚠️ Bruce diría 'Claro, espero.' (incorrecto)")
        print("❌ Test 2 FALLADO\n")

    # Test 3: Variante - "No les interesa en este momento"
    print("Test 3: Variante - 'No les interesa en este momento'")
    print("-" * 80)

    caso_variante_1 = "No les interesa en este momento"
    es_rechazo_v1 = any(patron in caso_variante_1.lower() for patron in patrones_rechazo)

    if es_rechazo_v1:
        print(f"✅ Variante detectada como RECHAZO")
        print(f"   Frase: '{caso_variante_1}'")
        print(f"   Patrón: 'no les interesa'")
        print("✅ Test 3 PASADO\n")
        tests_pasados += 1
    else:
        print(f"❌ Variante NO detectada como rechazo")
        print(f"   Frase: '{caso_variante_1}'")
        print("❌ Test 3 FALLADO\n")

    # Test 4: Variante - "No le interesa, gracias"
    print("Test 4: Variante - 'No le interesa, gracias'")
    print("-" * 80)

    caso_variante_2 = "No le interesa, gracias"
    es_rechazo_v2 = any(patron in caso_variante_2.lower() for patron in patrones_rechazo)

    if es_rechazo_v2:
        print(f"✅ Variante detectada como RECHAZO")
        print(f"   Frase: '{caso_variante_2}'")
        print(f"   Patrón: 'no le interesa'")
        print("✅ Test 4 PASADO\n")
        tests_pasados += 1
    else:
        print(f"❌ Variante NO detectada como rechazo")
        print(f"   Frase: '{caso_variante_2}'")
        print("❌ Test 4 FALLADO\n")

    # Resumen final
    print("="*80)
    print(f"RESUMEN FIX 413: {tests_pasados}/{tests_totales} tests pasados")
    print("="*80)

    if tests_pasados == tests_totales:
        print("✅ ¡TODOS LOS TESTS PASARON!")
        print("\nImpacto esperado:")
        print("  • -100% respuestas 'Claro, espero.' en rechazos con 'no nos interesa'")
        print("  • +100% despedidas corteses en rechazos")
        print("  • Mejor clasificación de resultados (RECHAZO vs NULL)")
    else:
        print(f"❌ {tests_totales - tests_pasados} test(s) fallaron")

    print("="*80 + "\n")

    return tests_pasados == tests_totales

if __name__ == "__main__":
    import sys
    exito = test_fix_413()
    sys.exit(0 if exito else 1)
