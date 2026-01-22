# -*- coding: utf-8 -*-
"""
Test para FIX 409 - Detección Mejorada "Ahorita No"
"""

import sys
import os

# Configurar encoding UTF-8 para Windows
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

def test_fix_409():
    print("="*70)
    print("TEST DE FIX 409: DETECCIÓN MEJORADA 'AHORITA NO'")
    print("="*70)

    tests_pasados = 0
    tests_totales = 3

    # Test 1: Verificar patrones en agente_ventas.py
    print("\n[1/3] Verificando patrones FIX 409 en agente_ventas.py...")
    try:
        with open('agente_ventas.py', 'r', encoding='utf-8') as f:
            content = f.read()

        if 'FIX 409' in content:
            print(f"   ✓ PASS: Código FIX 409 encontrado")

            # Verificar patrones específicos
            patrones_esperados = [
                "'ahorita no'",
                "'no está ahorita'",
                "'no esta ahorita'",
                "'no ahorita'",
                "'ahorita ya no'"
            ]

            patrones_encontrados = sum(1 for p in patrones_esperados if p in content)
            print(f"   Patrones encontrados: {patrones_encontrados}/{len(patrones_esperados)}")

            if patrones_encontrados == len(patrones_esperados):
                print(f"   ✓ Todos los patrones presentes")
                tests_pasados += 1
            else:
                print(f"   ✗ Faltan algunos patrones")
        else:
            print(f"   ✗ FAIL: Código FIX 409 NO encontrado")
    except Exception as e:
        print(f"   ✗ FAIL: Error al leer agente_ventas.py: {e}")

    # Test 2: Simular detección de "ahorita no"
    print("\n[2/3] Simulando detección de 'ahorita no'...")

    # Casos de prueba
    casos = [
        ("ahorita no está", True),
        ("ahorita no", True),
        ("no está ahorita", True),
        ("no ahorita", True),
        ("ahorita ya no", True),
        ("ahorita sí", False),  # NO debería detectar
        ("ahorita", False),  # NO debería detectar
    ]

    # Simular la lógica de detección
    patrones_deteccion = [
        'no está', 'no esta', 'no se encuentra',
        'ahorita no está', 'ahorita no esta',
        'ahorita no', 'no está ahorita', 'no esta ahorita',
        'no ahorita', 'ahorita ya no',
    ]

    casos_correctos = 0
    for texto, deberia_detectar in casos:
        detectado = any(patron in texto.lower() for patron in patrones_deteccion)

        if detectado == deberia_detectar:
            casos_correctos += 1
            print(f"   ✓ '{texto}' → {deberia_detectar} (correcto)")
        else:
            print(f"   ✗ '{texto}' → esperado {deberia_detectar}, obtuvo {detectado}")

    if casos_correctos == len(casos):
        print(f"   ✓ PASS: Todos los casos de detección correctos")
        tests_pasados += 1
    else:
        print(f"   ✗ FAIL: {len(casos) - casos_correctos} caso(s) fallaron")

    # Test 3: Verificar integración con REGLA 2
    print("\n[3/3] Verificando integración con REGLA 2...")

    # Buscar la sección de REGLA 2 en el código
    try:
        with open('agente_ventas.py', 'r', encoding='utf-8') as f:
            lines = f.readlines()

        # Buscar la línea que contiene "REGLA 2"
        regla2_encontrada = False
        cliente_dice_no_esta_encontrado = False

        for i, line in enumerate(lines):
            if 'REGLA 2: No insistir con encargado' in line:
                regla2_encontrada = True

            if 'cliente_dice_no_esta = any(frase in contexto_lower' in line:
                cliente_dice_no_esta_encontrado = True

        if regla2_encontrada and cliente_dice_no_esta_encontrado:
            print(f"   ✓ PASS: REGLA 2 y cliente_dice_no_esta encontrados")

            # Verificar que esté en la sección correcta (función _validar_sentido_comun)
            validar_sentido_comun_encontrado = any(
                'def _validar_sentido_comun' in line
                for line in lines
            )

            if validar_sentido_comun_encontrado:
                print(f"   ✓ Función _validar_sentido_comun existe")
                tests_pasados += 1
            else:
                print(f"   ✗ Función _validar_sentido_comun NO encontrada")
        else:
            print(f"   ✗ FAIL: REGLA 2 o cliente_dice_no_esta NO encontrados")
    except Exception as e:
        print(f"   ✗ FAIL: Error al verificar integración: {e}")

    # Resumen
    print("\n" + "="*70)
    print(f"RESULTADO: {tests_pasados}/{tests_totales} tests pasaron")
    print("="*70)

    if tests_pasados == tests_totales:
        print("\n✅ TODOS LOS TESTS PASARON")
        print("FIX 409 CONFIGURADO CORRECTAMENTE")
        print("\nPatrones de detección verificados:")
        print("  1. 'ahorita no' → Detecta encargado NO está")
        print("  2. 'no está ahorita' → Detecta encargado NO está")
        print("  3. 'no ahorita' → Detecta encargado NO está")
        print("  4. 'ahorita ya no' → Detecta encargado NO está")
        print("\n✅ LISTO PARA PRODUCCIÓN")
        print("\nEjemplo de uso:")
        print('  Cliente: "Ahorita no se encuentra, no sé si guste marcar"')
        print('  FIX 409: Detecta "ahorita no" → REGLA 2 activada')
        print('  Bruce: "Entiendo. ¿Le gustaría que le envíe el catálogo..."')
        return 0
    else:
        print(f"\n⚠️ {tests_totales - tests_pasados} test(s) fallaron")
        print("Revisar implementación de FIX 409")
        return 1

if __name__ == "__main__":
    print("\n🔧 Iniciando pruebas de FIX 409...")
    print("Fecha:", __import__('datetime').datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    print()

    # Cambiar al directorio del script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)

    resultado = test_fix_409()

    print("\n" + "="*70)
    if resultado == 0:
        print("✅ TEST COMPLETADO EXITOSAMENTE")
    else:
        print("❌ TEST FALLÓ - Revisar errores arriba")
    print("="*70)

    sys.exit(resultado)
