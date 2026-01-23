# -*- coding: utf-8 -*-
"""
Test para FIX 465: No interrumpir cuando frase termina en coma o conector

Problema: BRUCE1398 - Cliente dijo "Este, no, no está por el momento,"
          (con coma al final, iba a continuar diciendo "llega en media hora")
          Pero Bruce respondió antes de que terminara

Solución: Detectar frases que terminan en coma o palabras conectoras
          y esperar más tiempo antes de responder
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def detectar_frase_incompleta(texto: str) -> tuple:
    """
    Simula la lógica de FIX 465 para detectar frases incompletas
    Retorna (es_incompleta, razon)
    """
    texto_lower = texto.strip().lower()

    if not texto_lower:
        return (False, "vacio")

    # Termina con coma = definitivamente incompleta
    if texto_lower.endswith(','):
        return (True, "coma")

    # Termina con palabra conectora
    conectores = ['y', 'pero', 'o', 'que', 'porque', 'este', 'bueno', 'pues', 'entonces', 'como']
    for conector in conectores:
        if texto_lower.endswith(f' {conector}'):
            return (True, f"conector '{conector}'")

    return (False, "completa")


def test_caso_bruce1398():
    """
    FIX 465: Simular caso BRUCE1398 - Frase incompleta con coma
    """
    print("\n" + "="*60)
    print("TEST: Caso BRUCE1398 - Frase incompleta con coma")
    print("="*60)

    mensaje = "Este, no, no está por el momento,"

    print(f"  Transcripción: '{mensaje}'")

    incompleta, razon = detectar_frase_incompleta(mensaje)

    print(f"  Es incompleta: {incompleta}")
    print(f"  Razón: {razon}")

    if incompleta and razon == "coma":
        print(f"\n[OK] FIX 465 detectaría frase incompleta - esperaría más")
        return True
    else:
        print(f"\n[FAIL] FIX 465 NO detectaría frase incompleta")
        return False


def test_frases_incompletas():
    """
    FIX 465: Varias frases que deben detectarse como incompletas
    """
    print("\n" + "="*60)
    print("TEST: Frases que deben detectarse como incompletas")
    print("="*60)

    casos_incompletos = [
        ("No está por el momento,", "coma"),
        ("Sí, este", "conector"),
        ("Bueno, el encargado y", "conector"),
        ("Llega en una hora pero", "conector"),
        ("Sí, o sea que", "conector"),
        ("Es que bueno", "conector"),
        ("Mira, entonces", "conector"),
        ("Espérame porque", "conector"),
    ]

    errores = []

    for mensaje, tipo_esperado in casos_incompletos:
        incompleta, razon = detectar_frase_incompleta(mensaje)

        if incompleta:
            print(f"  [OK] '{mensaje}' -> incompleta ({razon})")
        else:
            print(f"  [FAIL] '{mensaje}' -> NO detectada como incompleta")
            errores.append(mensaje)

    if errores:
        print(f"\n[FAIL] {len(errores)} frases NO detectadas como incompletas")
        return False

    print(f"\n[OK] Todas las frases incompletas detectadas")
    return True


def test_frases_completas():
    """
    FIX 465: Frases completas NO deben esperar más
    """
    print("\n" + "="*60)
    print("TEST: Frases completas NO deben esperar más")
    print("="*60)

    casos_completos = [
        "No está por el momento.",
        "El encargado no se encuentra.",
        "Sí, dígame.",
        "Buenas tardes.",
        "No me interesa, gracias.",
        "Ya tenemos proveedor.",
        "Llámeme más tarde.",
    ]

    errores = []

    for mensaje in casos_completos:
        incompleta, razon = detectar_frase_incompleta(mensaje)

        if not incompleta:
            print(f"  [OK] '{mensaje}' -> completa")
        else:
            print(f"  [FAIL] '{mensaje}' -> detectada como incompleta ({razon})")
            errores.append(mensaje)

    if errores:
        print(f"\n[FAIL] {len(errores)} frases completas detectadas incorrectamente")
        return False

    print(f"\n[OK] Todas las frases completas identificadas correctamente")
    return True


def test_casos_edge():
    """
    FIX 465: Casos edge - frases que podrían confundir
    """
    print("\n" + "="*60)
    print("TEST: Casos edge")
    print("="*60)

    casos = [
        # (mensaje, esperado_incompleta)
        ("Bueno?", False),  # "bueno" al inicio con ? = pregunta completa
        ("No, bueno", True),  # termina en "bueno" = incompleta
        ("Dígame qué necesita", False),  # "que" en medio, no al final
        ("Sí pero", True),  # termina en "pero"
        ("No estoy interesado, pero", True),  # coma Y conector
    ]

    errores = []

    for mensaje, esperado in casos:
        incompleta, _ = detectar_frase_incompleta(mensaje)

        if incompleta == esperado:
            estado = "incompleta" if incompleta else "completa"
            print(f"  [OK] '{mensaje}' -> {estado}")
        else:
            estado_real = "incompleta" if incompleta else "completa"
            estado_esperado = "incompleta" if esperado else "completa"
            print(f"  [FAIL] '{mensaje}' -> {estado_real} (esperado: {estado_esperado})")
            errores.append(mensaje)

    if errores:
        print(f"\n[FAIL] {len(errores)} casos edge fallaron")
        return False

    print(f"\n[OK] Todos los casos edge pasaron")
    return True


if __name__ == "__main__":
    print("="*60)
    print("TESTS FIX 465: Detectar frases incompletas antes de responder")
    print("="*60)

    resultados = []

    resultados.append(("Caso BRUCE1398", test_caso_bruce1398()))
    resultados.append(("Frases incompletas", test_frases_incompletas()))
    resultados.append(("Frases completas", test_frases_completas()))
    resultados.append(("Casos edge", test_casos_edge()))

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
