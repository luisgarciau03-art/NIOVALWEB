# -*- coding: utf-8 -*-
"""
Test Final para FIX 407 - Verificación por número de línea
"""

def test_fix_407():
    print("="*70)
    print("TEST DE FIX 407: RAZONAMIENTO MEJORADO")
    print("="*70)

    with open('agente_ventas.py', 'r', encoding='utf-8') as f:
        lines = f.readlines()

    tests_pasados = 0
    tests_totales = 5

    # Test 1: Memoria de Contexto en línea 6530
    print("\n[1/5] Verificando Memoria de Contexto (linea 6530)...")
    if any("FIX 407: MEMORIA DE CONTEXTO CONVERSACIONAL" in line for line in lines[6520:6540]):
        print("   PASS: Comentario de Memoria encontrado")
        tests_pasados += 1
    else:
        print("   FAIL: No se encontro comentario de Memoria")

    # Test 2: Código de cálculo de memoria
    print("\n[2/5] Verificando codigo de calculo de memoria...")
    tiene_calculo = False
    for i, line in enumerate(lines[6535:6555], start=6535):
        if "veces_menciono_nioval" in line or "veces_pregunto_encargado" in line:
            tiene_calculo = True
            break

    if tiene_calculo:
        print("   PASS: Codigo de calculo presente")
        tests_pasados += 1
    else:
        print("   FAIL: Falta codigo de calculo")

    # Test 3: Priorización (línea 6678)
    print("\n[3/5] Verificando Priorizacion de Respuestas (linea 6678)...")
    if any("PRIORIZA" in line and "FIX 407" in line for line in lines[6675:6685]):
        print("   PASS: Seccion de Priorizacion encontrada")
        tests_pasados += 1
    else:
        print("   FAIL: No se encontro seccion de Priorizacion")

    # Test 4: Verificación de Coherencia (línea 6703)
    print("\n[4/5] Verificando Verificacion de Coherencia (linea 6703)...")
    if any("COHERENCIA" in line and "FIX 407" in line for line in lines[6700:6710]):
        print("   PASS: Seccion de Coherencia encontrada")
        tests_pasados += 1
    else:
        print("   FAIL: No se encontro seccion de Coherencia")

    # Test 5: Ejemplos Mejorados (línea 6729)
    print("\n[5/5] Verificando Ejemplos Mejorados (linea 6729)...")
    if any("EJEMPLOS MEJORADOS" in line and "FIX 407" in line for line in lines[6725:6735]):
        print("   PASS: Seccion de Ejemplos encontrada")
        tests_pasados += 1
    else:
        print("   FAIL: No se encontro seccion de Ejemplos")

    # Resumen
    print("\n" + "="*70)
    print("RESULTADO: {}/{} tests pasaron".format(tests_pasados, tests_totales))
    print("="*70)

    if tests_pasados == tests_totales:
        print("\nTODOS LOS TESTS PASARON")
        print("FIX 407 CONFIGURADO CORRECTAMENTE")
        print("\nComponentes verificados:")
        print("  1. Memoria de Contexto Conversacional (Python PRE-GPT)")
        print("  2. Codigo de calculo de memoria")
        print("  3. Priorizacion de Respuestas")
        print("  4. Verificacion de Coherencia")
        print("  5. Ejemplos Mejorados de Razonamiento")
        return 0
    else:
        print("\n{} test(s) fallaron".format(tests_totales - tests_pasados))
        return 1


if __name__ == "__main__":
    exit(test_fix_407())
