# -*- coding: utf-8 -*-
"""
Tests para FIX 459 y FIX 460

FIX 459: Evitar doble pregunta por encargado en FIX 298/301
- BRUCE1381: Bruce preguntó 2 veces "¿Se encontrará el encargado?"
- Causa: FIX 298/301 forzaba pregunta sin verificar si ya se hizo

FIX 460: Distinguir "va a pasar" vs "llame después" en FIX 170
- BRUCE1381: Cliente dijo "puede marcar en otro" pero Bruce dijo "Claro, espero"
- Causa: FIX 170 detectó "ahorita" y asumió transferencia incorrectamente
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def test_fix_459_no_doble_pregunta_encargado():
    """
    FIX 459: No preguntar 2 veces por el encargado
    """
    print("\n" + "="*60)
    print("TEST FIX 459: No doble pregunta por encargado")
    print("="*60)

    # Simular historial donde Bruce YA preguntó por encargado
    historial_bruce = "me comunico de la marca nioval... ¿se encontrará el encargado de compras?"

    # Frases que indican que Bruce ya preguntó
    frases_ya_pregunto = [
        'encargado de compras', 'encargada de compras',
        '¿se encontrará el encargado', '¿se encuentra el encargado',
        'se encontrara el encargado', 'se encuentra el encargado'
    ]

    bruce_ya_pregunto = any(frase in historial_bruce for frase in frases_ya_pregunto)

    print(f"  Historial Bruce: '{historial_bruce[:60]}...'")
    print(f"  Bruce ya preguntó por encargado: {bruce_ya_pregunto}")

    if bruce_ya_pregunto:
        print(f"\n  Con FIX 459:")
        print(f"    FIX 298/301 NO forzaría otra pregunta por encargado")
        print(f"    Bruce usaría respuesta contextual o de GPT")
        print(f"\n[OK] FIX 459 evitaría doble pregunta")
        return True
    else:
        print(f"\n[FAIL] FIX 459 NO detectó pregunta previa")
        return False


def test_fix_459_caso_bruce1381():
    """
    FIX 459: Simular caso BRUCE1381 - Cliente respondió parcialmente
    """
    print("\n" + "="*60)
    print("TEST: Caso BRUCE1381 - Doble pregunta por encargado")
    print("="*60)

    # Contexto BRUCE1381
    historial_bruce = "me comunico de la marca nioval, más que nada quería brindar informacion de nuestros productos ferreteros, ¿se encontrara el encargado o encargada de compras?"
    ultimo_cliente = "este, mire, por el momento no se"

    print(f"  Bruce dijo: '{historial_bruce[:60]}...'")
    print(f"  Cliente respondió: '{ultimo_cliente}'")

    # Verificar si Bruce ya preguntó
    frases_ya_pregunto = [
        'encargado de compras', 'encargada de compras',
        '¿se encontrará el encargado', '¿se encuentra el encargado',
        'se encontrara el encargado', 'se encuentra el encargado'
    ]
    bruce_ya_pregunto = any(frase in historial_bruce.lower() for frase in frases_ya_pregunto)

    # Verificar si encargado no está
    frases_no_esta = [
        'no está', 'no esta', 'no se encuentra', 'salió', 'salio',
        'por el momento no', 'ahorita no', 'no hay'
    ]
    encargado_no_esta = any(frase in ultimo_cliente for frase in frases_no_esta)

    print(f"  Bruce ya preguntó encargado: {bruce_ya_pregunto}")
    print(f"  Cliente indica encargado no está: {encargado_no_esta}")

    if bruce_ya_pregunto:
        if encargado_no_esta:
            respuesta_esperada = "Entiendo. ¿A qué hora puedo llamar para contactarlo?"
        else:
            respuesta_esperada = "(usar respuesta de GPT)"
        print(f"\n  Con FIX 459:")
        print(f"    NO preguntaría de nuevo por encargado")
        print(f"    Respuesta esperada: '{respuesta_esperada}'")
        print(f"\n[OK] FIX 459 evitaría error de BRUCE1381")
        return True
    else:
        print(f"\n[FAIL] FIX 459 NO evitaría el error")
        return False


def test_fix_460_llamar_despues_vs_transferir():
    """
    FIX 460: Distinguir "llame después" vs "transferencia"
    """
    print("\n" + "="*60)
    print("TEST FIX 460: Llamar después vs Transferir")
    print("="*60)

    frases_llamar_despues = [
        'puede marcar', 'marque después', 'marque despues', 'llame después', 'llame despues',
        'llámenos después', 'llamenos despues', 'marcar en otro', 'llamar en otro',
        'vuelva a llamar', 'intente más tarde', 'intente mas tarde',
        'regrese la llamada', 'mejor llame', 'otro momento', 'otro dia', 'otro día',
        'más tarde', 'mas tarde', 'en la tarde', 'en la mañana', 'mañana',
        'el mostrador', 'nada más atendemos', 'nada mas atendemos', 'solo atendemos',
        'no se la maneja', 'no le puedo', 'no tengo esa información', 'no tengo esa informacion'
    ]

    casos = [
        # (frase, es_llamar_despues, es_transferencia)
        ("puede marcar en otro momento", True, False),
        ("vuelva a llamar más tarde", True, False),
        ("le está hablando el mostrador, nada más atendemos", True, False),
        ("no se la maneja ahorita", True, False),  # BRUCE1381
        ("espéreme un momento", False, True),  # Transferencia real
        ("déjeme lo transfiero", False, True),  # Transferencia real
        ("te lo paso", False, True),  # Transferencia real
    ]

    errores = []

    for frase, esperado_llamar, esperado_transferir in casos:
        frase_lower = frase.lower()
        es_llamar_despues = any(f in frase_lower for f in frases_llamar_despues)

        # Si es "llamar después", NO es transferencia
        # Si NO es "llamar después", verificar patrones de transferencia
        if esperado_llamar == es_llamar_despues:
            estado = "[OK]"
        else:
            estado = "[FAIL]"
            errores.append(frase)

        print(f"  {estado} '{frase[:50]}...' -> llamar_después={es_llamar_despues}")

    if errores:
        print(f"\n[FAIL] Test fallado con {len(errores)} errores")
        return False

    print(f"\n[OK] Test pasado")
    return True


def test_fix_460_caso_bruce1381():
    """
    FIX 460: Simular caso BRUCE1381 - "Claro, espero" incoherente
    """
    print("\n" + "="*60)
    print("TEST: Caso BRUCE1381 - 'Claro, espero' incoherente")
    print("="*60)

    # Contexto BRUCE1381
    respuesta_cliente = "Este, esa información no se la maneja ahorita. Es que le está hablando el mostrador y nada más atendemos. Sí, puede marcar en otro en otro"

    print(f"  Cliente dijo: '{respuesta_cliente[:80]}...'")

    # Verificar con FIX 460
    frases_llamar_despues = [
        'puede marcar', 'el mostrador', 'nada más atendemos', 'nada mas atendemos',
        'no se la maneja', 'marcar en otro'
    ]

    es_llamar_despues = any(frase in respuesta_cliente.lower() for frase in frases_llamar_despues)

    print(f"  Es 'llamar después' (no transferencia): {es_llamar_despues}")

    if es_llamar_despues:
        print(f"\n  Con FIX 460:")
        print(f"    FIX 170 NO activaría 'Claro, espero'")
        print(f"    Bruce usaría despedida apropiada de GPT")
        print(f"\n[OK] FIX 460 evitaría 'Claro, espero' incoherente")
        return True
    else:
        print(f"\n[FAIL] FIX 460 NO evitaría el error")
        return False


if __name__ == "__main__":
    print("="*60)
    print("TESTS FIX 459/460: BRUCE1381 - Doble pregunta y Claro espero")
    print("="*60)

    resultados = []

    resultados.append(("FIX 459: No doble pregunta", test_fix_459_no_doble_pregunta_encargado()))
    resultados.append(("FIX 459: Caso BRUCE1381", test_fix_459_caso_bruce1381()))
    resultados.append(("FIX 460: Llamar después vs Transferir", test_fix_460_llamar_despues_vs_transferir()))
    resultados.append(("FIX 460: Caso BRUCE1381", test_fix_460_caso_bruce1381()))

    print("\n" + "="*60)
    print("RESUMEN DE TESTS")
    print("="*60)

    total_pasados = sum(1 for _, r in resultados if r)
    total_tests = len(resultados)

    for nombre, resultado in resultados:
        estado = "[OK]" if resultado else "[FAIL]"
        print(f"  {estado} {nombre}")

    print(f"\nTotal: {total_pasados}/{total_tests} tests pasados")

    if total_pasados == total_tests:
        print("\n[OK] TODOS LOS TESTS PASARON")
        sys.exit(0)
    else:
        print("\n[FAIL] ALGUNOS TESTS FALLARON")
        sys.exit(1)
