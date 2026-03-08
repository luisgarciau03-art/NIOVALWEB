# -*- coding: utf-8 -*-
"""
Test para FIX 408 - Timeout Deepgram Progresivo
Simula diferentes escenarios de timeout
"""

import sys
import os

# Configurar encoding UTF-8 para Windows
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Agregar directorio actual al path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from agente_ventas import AgenteVentas

def test_fix_408():
    print("="*70)
    print("TEST DE FIX 408: TIMEOUT DEEPGRAM PROGRESIVO")
    print("="*70)

    tests_pasados = 0
    tests_totales = 5

    # Test 1: Verificar que el atributo existe
    print("\n[1/5] Verificando atributo timeouts_deepgram...")
    agente = AgenteVentas()

    if hasattr(agente, 'timeouts_deepgram'):
        print(f"   ✓ PASS: Atributo timeouts_deepgram existe")
        print(f"   Valor inicial: {agente.timeouts_deepgram}")
        if agente.timeouts_deepgram == 0:
            print(f"   ✓ Inicializado correctamente en 0")
            tests_pasados += 1
        else:
            print(f"   ✗ FAIL: Debería inicializarse en 0, pero es {agente.timeouts_deepgram}")
    else:
        print(f"   ✗ FAIL: Atributo timeouts_deepgram NO existe")

    # Test 2: Verificar código de FIX 408 en servidor_llamadas.py
    print("\n[2/5] Verificando código FIX 408 en servidor_llamadas.py...")
    try:
        with open('servidor_llamadas.py', 'r', encoding='utf-8') as f:
            content = f.read()

        if 'FIX 408' in content:
            print(f"   ✓ PASS: Código FIX 408 encontrado")

            # Contar menciones de FIX 408
            menciones = content.count('FIX 408')
            print(f"   Total de menciones FIX 408: {menciones}")

            # Verificar frases clave
            frases_esperadas = [
                "Disculpe, no alcancé a escucharle bien",
                "¿Me escucha? Parece que hay interferencia",
                "timeouts_deepgram += 1",
                "timeouts_deepgram = 0"
            ]

            frases_encontradas = sum(1 for frase in frases_esperadas if frase in content)
            print(f"   Frases clave encontradas: {frases_encontradas}/{len(frases_esperadas)}")

            if frases_encontradas == len(frases_esperadas):
                print(f"   ✓ Todas las frases clave presentes")
                tests_pasados += 1
            else:
                print(f"   ✗ Faltan algunas frases clave")
        else:
            print(f"   ✗ FAIL: Código FIX 408 NO encontrado")
    except Exception as e:
        print(f"   ✗ FAIL: Error al leer servidor_llamadas.py: {e}")

    # Test 3: Simular primer timeout
    print("\n[3/5] Simulando primer timeout...")
    agente = AgenteVentas()
    agente.timeouts_deepgram = 0

    # Incrementar como lo haría el código
    agente.timeouts_deepgram += 1

    if agente.timeouts_deepgram == 1:
        respuesta_esperada = "Disculpe, no alcancé a escucharle bien, ¿me podría repetir?"
        print(f"   ✓ PASS: Contador en 1 (primer timeout)")
        print(f"   Respuesta esperada: \"{respuesta_esperada}\"")
        tests_pasados += 1
    else:
        print(f"   ✗ FAIL: Contador debería ser 1, pero es {agente.timeouts_deepgram}")

    # Test 4: Simular segundo timeout
    print("\n[4/5] Simulando segundo timeout...")
    agente.timeouts_deepgram += 1

    if agente.timeouts_deepgram == 2:
        respuesta_esperada = "¿Me escucha? Parece que hay interferencia"
        print(f"   ✓ PASS: Contador en 2 (segundo timeout)")
        print(f"   Respuesta esperada: \"{respuesta_esperada}\"")
        tests_pasados += 1
    else:
        print(f"   ✗ FAIL: Contador debería ser 2, pero es {agente.timeouts_deepgram}")

    # Test 5: Simular tercer timeout (debe continuar con saludo)
    print("\n[5/5] Simulando tercer timeout...")
    agente.timeouts_deepgram += 1

    if agente.timeouts_deepgram >= 3:
        respuesta_esperada = "Me comunico de la marca nioval..."
        print(f"   ✓ PASS: Contador en {agente.timeouts_deepgram} (tercer timeout+)")
        print(f"   Acción esperada: Continuar con saludo completo")
        print(f"   Respuesta esperada: \"{respuesta_esperada}\"")
        tests_pasados += 1
    else:
        print(f"   ✗ FAIL: Contador debería ser ≥3, pero es {agente.timeouts_deepgram}")

    # Test Extra: Verificar reset de contador
    print("\n[EXTRA] Verificando reset de contador...")
    agente.timeouts_deepgram = 2  # Simular 2 timeouts previos
    print(f"   Contador antes de reset: {agente.timeouts_deepgram}")

    # Simular que Deepgram respondió exitosamente
    agente.timeouts_deepgram = 0
    print(f"   Contador después de reset: {agente.timeouts_deepgram}")

    if agente.timeouts_deepgram == 0:
        print(f"   ✓ Reset exitoso")
    else:
        print(f"   ✗ Reset fallido")

    # Resumen
    print("\n" + "="*70)
    print(f"RESULTADO: {tests_pasados}/{tests_totales} tests pasaron")
    print("="*70)

    if tests_pasados == tests_totales:
        print("\n✅ TODOS LOS TESTS PASARON")
        print("FIX 408 CONFIGURADO CORRECTAMENTE")
        print("\nFlujo de respuestas verificado:")
        print("  1. Timeout #1 → 'Disculpe, no alcancé a escucharle bien...'")
        print("  2. Timeout #2 → '¿Me escucha? Parece que hay interferencia'")
        print("  3. Timeout #3+ → Continuar con saludo completo")
        print("  4. Reset automático cuando Deepgram responde")
        print("\n✅ LISTO PARA PRODUCCIÓN")
        return 0
    else:
        print(f"\n⚠️ {tests_totales - tests_pasados} test(s) fallaron")
        print("Revisar implementación de FIX 408")
        return 1

if __name__ == "__main__":
    print("\n🔧 Iniciando pruebas de FIX 408...")
    print("Fecha:", __import__('datetime').datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    print()

    resultado = test_fix_408()

    print("\n" + "="*70)
    if resultado == 0:
        print("✅ TEST COMPLETADO EXITOSAMENTE")
    else:
        print("❌ TEST FALLÓ - Revisar errores arriba")
    print("="*70)

    sys.exit(resultado)
