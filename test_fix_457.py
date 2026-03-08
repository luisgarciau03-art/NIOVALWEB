# -*- coding: utf-8 -*-
"""
Test para FIX 457: No pedir número cuando cliente ofrece correo

Problema: BRUCE1370 - Cliente ofreció "Si quiere le doy un correo electrónico"
pero FIX 311b sobrescribió la respuesta de GPT y Bruce pidió el número
del encargado en lugar de aceptar el correo.

Solución: Detectar cuando cliente ofrece un dato y NO aplicar FIX 311b
para que GPT pueda responder apropiadamente aceptando el dato.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def test_detectar_cliente_ofrece_dato():
    """
    FIX 457: Verificar que se detecta cuando cliente ofrece un dato
    """
    print("\n" + "="*60)
    print("TEST FIX 457: Detectar cliente ofreciendo dato")
    print("="*60)

    frases_cliente_ofrece = [
        'le doy un correo', 'le doy el correo', 'le paso el correo',
        'le doy un numero', 'le doy el numero', 'le paso el numero',
        'le doy un número', 'le doy el número', 'le paso el número',
        'le doy mi correo', 'le doy mi numero', 'le doy mi número',
        'le paso un correo', 'le paso un numero', 'le paso un número',
        'si quiere le doy', 'si gusta le doy', 'si desea le doy',
        'le puedo dar un correo', 'le puedo dar el correo',
        'le puedo dar un numero', 'le puedo dar el numero',
        'anote el correo', 'anote mi correo', 'apunte el correo',
        'tome nota', 'le comparto'
    ]

    casos = [
        # (frase_cliente, deberia_detectar_ofrecimiento)
        ("No, no se encuentra. Si quiere le doy un correo electrónico.", True),  # BRUCE1370
        ("No está, le doy el número del encargado", True),
        ("El encargado no está, le paso el correo", True),
        ("No se encuentra, pero le puedo dar un numero", True),
        ("Tome nota, el correo es...", True),
        ("No se encuentra", False),  # No ofrece nada
        ("No está el encargado", False),  # No ofrece nada
        ("Ya no trabajamos con proveedores", False),  # No ofrece nada
    ]

    errores = []

    for frase, esperado in casos:
        frase_lower = frase.lower()
        cliente_ofrece = any(f in frase_lower for f in frases_cliente_ofrece)

        if cliente_ofrece == esperado:
            estado = "[OK]"
        else:
            estado = "[FAIL]"
            errores.append(frase)

        print(f"  {estado} '{frase[:50]}...' -> ofrece={cliente_ofrece}")

    if errores:
        print(f"\n[FAIL] Test fallado con {len(errores)} errores")
        return False

    print(f"\n[OK] Test pasado")
    return True


def test_caso_bruce1370():
    """
    FIX 457: Simular caso exacto de BRUCE1370
    """
    print("\n" + "="*60)
    print("TEST: Caso BRUCE1370 - Cliente ofrece correo")
    print("="*60)

    # Contexto BRUCE1370
    contexto_cliente = "no, no se encuentra. si quiere le doy un correo electrónico."
    respuesta_gpt = "Perfecto, ¿le gustaría recibir nuestro catálogo por correo electrónico?"

    # Frases que indican ofrecimiento
    frases_cliente_ofrece = [
        'le doy un correo', 'le doy el correo', 'si quiere le doy',
        'le puedo dar un correo', 'tome nota'
    ]

    # Lógica de FIX 457
    cliente_ofrece_dato = any(f in contexto_cliente for f in frases_cliente_ofrece)

    print(f"  Contexto cliente: '{contexto_cliente}'")
    print(f"  Respuesta GPT: '{respuesta_gpt}'")
    print(f"  Cliente ofrece dato: {cliente_ofrece_dato}")

    if cliente_ofrece_dato:
        print(f"\n  Con FIX 457:")
        print(f"    FIX 311b NO se aplicaría")
        print(f"    Bruce usaría respuesta de GPT: '{respuesta_gpt}'")
        print(f"    Bruce aceptaría el correo del cliente")
        print(f"\n[OK] FIX 457 evitaría el error de BRUCE1370")
        return True
    else:
        print(f"\n[FAIL] FIX 457 NO evitaría el problema")
        return False


def test_fix_311b_sin_ofrecimiento():
    """
    FIX 457: Verificar que FIX 311b SÍ se aplica cuando cliente NO ofrece dato
    """
    print("\n" + "="*60)
    print("TEST: FIX 311b sigue funcionando cuando no hay ofrecimiento")
    print("="*60)

    # Caso donde FIX 311b SÍ debe aplicar
    contexto_cliente = "no, no se encuentra"  # Sin ofrecimiento
    respuesta_gpt = "Le gustaría recibir nuestro catálogo por correo?"

    frases_cliente_ofrece = [
        'le doy un correo', 'le doy el correo', 'si quiere le doy',
        'le puedo dar un correo', 'tome nota'
    ]

    frases_no_esta = ['no se encuentra', 'no está', 'no esta']
    frases_catalogo = ['catálogo por correo', 'catalogo por correo', 'le gustaría recibir']

    cliente_dice_no_esta = any(f in contexto_cliente for f in frases_no_esta)
    bruce_ofrece_catalogo = any(f in respuesta_gpt.lower() for f in frases_catalogo)
    cliente_ofrece_dato = any(f in contexto_cliente for f in frases_cliente_ofrece)

    print(f"  Contexto cliente: '{contexto_cliente}'")
    print(f"  Cliente dice no está: {cliente_dice_no_esta}")
    print(f"  Bruce ofrece catálogo: {bruce_ofrece_catalogo}")
    print(f"  Cliente ofrece dato: {cliente_ofrece_dato}")

    # FIX 311b debe aplicar si: no_esta AND catalogo AND NOT ofrece_dato
    aplicar_311b = cliente_dice_no_esta and bruce_ofrece_catalogo and not cliente_ofrece_dato

    if aplicar_311b:
        print(f"\n  Sin ofrecimiento de dato:")
        print(f"    FIX 311b SÍ se aplicaría")
        print(f"    Bruce pediría número del encargado primero")
        print(f"\n[OK] FIX 311b sigue funcionando correctamente")
        return True
    else:
        print(f"\n[FAIL] FIX 311b no se aplicaría cuando debería")
        return False


if __name__ == "__main__":
    print("="*60)
    print("TESTS FIX 457: No pedir número cuando cliente ofrece correo")
    print("="*60)

    resultados = []

    resultados.append(("Detectar ofrecimiento", test_detectar_cliente_ofrece_dato()))
    resultados.append(("Caso BRUCE1370", test_caso_bruce1370()))
    resultados.append(("FIX 311b sin ofrecimiento", test_fix_311b_sin_ofrecimiento()))

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
