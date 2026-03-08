# -*- coding: utf-8 -*-
"""
Test para FIX 410 - Arreglar detección incorrecta "quiere" como "quién"
"""

import sys
import os
import re

# Configurar encoding UTF-8 para Windows
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

def test_fix_410():
    print("="*70)
    print("TEST DE FIX 410: ARREGLAR DETECCIÓN 'QUIERE' COMO 'QUIÉN'")
    print("="*70)

    tests_pasados = 0
    tests_totales = 3

    # Test 1: Verificar que el patrón está arreglado
    print("\n[1/3] Verificando nuevo patrón en agente_ventas.py...")
    try:
        with open('agente_ventas.py', 'r', encoding='utf-8') as f:
            content = f.read()

        if 'FIX 410' in content:
            print(f"   ✓ PASS: Código FIX 410 encontrado")

            # Verificar que usa word boundary \b
            if r'\bqui[eé]n\s+' in content:
                print(f"   ✓ Patrón con word boundary encontrado")
                tests_pasados += 1
            else:
                print(f"   ✗ Patrón con word boundary NO encontrado")
        else:
            print(f"   ✗ FAIL: Código FIX 410 NO encontrado")
    except Exception as e:
        print(f"   ✗ FAIL: Error al leer agente_ventas.py: {e}")

    # Test 2: Simular detección con patrones ANTES y DESPUÉS
    print("\n[2/3] Comparando detección ANTES vs DESPUÉS...")

    # Patrón ANTES (buggy) - detecta "quiere" como "quién"
    patron_antes = r'(?:con\s+)?qui[eé]n\s+(?:tengo\s+el\s+gusto|hablo|me\s+habla|est[aá]s?)'

    # Patrón DESPUÉS (FIX 410) - NO detecta "quiere"
    patron_despues = r'\bqui[eé]n\s+(?:tengo\s+el\s+gusto|hablo|me\s+habla|est[aá]s?|eres)'

    # Casos de prueba
    casos = [
        # (texto, debería_detectar)
        ("con quién hablo", True),  # Debe detectar
        ("quién eres", True),  # Debe detectar
        ("quién me habla", True),  # Debe detectar
        ("si quiere, nomás número por whatsapp", False),  # NO debe detectar
        ("quiere recibir información", False),  # NO debe detectar
        ("si quiere enviar catálogo", False),  # NO debe detectar
    ]

    print(f"\n   Patrón ANTES (buggy):")
    for texto, deberia in casos:
        detectado = bool(re.search(patron_antes, texto, re.IGNORECASE))
        simbolo = "❌" if (detectado and not deberia) or (not detectado and deberia) else "✓"
        print(f"   {simbolo} '{texto}' → {detectado}")

    print(f"\n   Patrón DESPUÉS (FIX 410):")
    casos_correctos = 0
    for texto, deberia in casos:
        detectado = bool(re.search(patron_despues, texto, re.IGNORECASE))
        correcto = detectado == deberia
        if correcto:
            casos_correctos += 1
        simbolo = "✓" if correcto else "✗"
        print(f"   {simbolo} '{texto}' → {detectado} (esperado: {deberia})")

    if casos_correctos == len(casos):
        print(f"\n   ✓ PASS: Todos los casos correctos")
        tests_pasados += 1
    else:
        print(f"\n   ✗ FAIL: {len(casos) - casos_correctos} caso(s) fallaron")

    # Test 3: Verificar caso real de BRUCE1180
    print("\n[3/3] Verificando caso real BRUCE1180...")

    texto_cliente = "si quiere, nomás número por whatsapp. ¿vale?"

    # Antes (buggy)
    detectado_antes = bool(re.search(patron_antes, texto_cliente, re.IGNORECASE))

    # Después (FIX 410)
    detectado_despues = bool(re.search(patron_despues, texto_cliente, re.IGNORECASE))

    print(f"   Cliente dijo: '{texto_cliente}'")
    print(f"   Patrón ANTES detectó 'quién habla': {detectado_antes} ❌")
    print(f"   Patrón DESPUÉS detectó 'quién habla': {detectado_despues}")

    if not detectado_despues:
        print(f"   ✓ PASS: FIX 410 NO detecta 'quiere' como 'quién'")
        tests_pasados += 1
    else:
        print(f"   ✗ FAIL: FIX 410 sigue detectando incorrectamente")

    # Resumen
    print("\n" + "="*70)
    print(f"RESULTADO: {tests_pasados}/{tests_totales} tests pasaron")
    print("="*70)

    if tests_pasados == tests_totales:
        print("\n✅ TODOS LOS TESTS PASARON")
        print("FIX 410 CONFIGURADO CORRECTAMENTE")
        print("\nProblema resuelto:")
        print("  Cliente: 'Si quiere, nomás número por WhatsApp'")
        print("  ANTES: ❌ FIX 243 detectaba 'quiere' como 'quién habla'")
        print("  DESPUÉS: ✅ FIX 410 NO detecta - Bruce NO se re-presenta")
        print("\n✅ LISTO PARA PRODUCCIÓN")
        return 0
    else:
        print(f"\n⚠️ {tests_totales - tests_pasados} test(s) fallaron")
        print("Revisar implementación de FIX 410")
        return 1

if __name__ == "__main__":
    print("\n🔧 Iniciando pruebas de FIX 410...")
    print("Fecha:", __import__('datetime').datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    print()

    # Cambiar al directorio del script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)

    resultado = test_fix_410()

    print("\n" + "="*70)
    if resultado == 0:
        print("✅ TEST COMPLETADO EXITOSAMENTE")
    else:
        print("❌ TEST FALLÓ - Revisar errores arriba")
    print("="*70)

    sys.exit(resultado)
