# -*- coding: utf-8 -*-
"""
Test para FIX 462: Capturar WhatsApp cuando cliente confirma número

Problema: BRUCE1396 - Bruce repitió número "221-442-61-55, ¿es correcto?"
          Cliente dijo "Es correcto" pero el número NO se guardó.
          Luego FIX 295/300 volvió a pedir el WhatsApp.

Solución: Detectar confirmación del cliente y extraer número del historial de Bruce.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import re


def extraer_numero_del_historial(mensaje_bruce: str) -> str:
    """Simula la lógica de FIX 462 para extraer número del mensaje de Bruce"""
    patron_numero_en_mensaje = re.search(
        r'(?:anotado como|tengo como|registrado como|es el|número es)?\s*(\d[\d\s\-\.]+\d)',
        mensaje_bruce, re.IGNORECASE
    )
    if patron_numero_en_mensaje:
        numero_en_historial = patron_numero_en_mensaje.group(1)
        digitos = re.sub(r'[^\d]', '', numero_en_historial)
        if len(digitos) >= 9 and len(digitos) <= 12:
            if len(digitos) == 12 and digitos.startswith('52'):
                digitos = digitos[2:]
            return f"+52{digitos}"
    return None


def test_caso_bruce1396():
    """
    FIX 462: Simular caso BRUCE1396 - Cliente confirma número
    """
    print("\n" + "="*60)
    print("TEST: Caso BRUCE1396 - Cliente confirma número")
    print("="*60)

    # Mensaje de Bruce que contiene el número
    mensaje_bruce = "Perfecto, lo tengo anotado como 221-442-61-55, ¿es correcto?"

    # Mensaje del cliente confirmando
    mensaje_cliente = "Es correcto."

    print(f"  Bruce dijo: '{mensaje_bruce}'")
    print(f"  Cliente dijo: '{mensaje_cliente}'")

    # Detectar confirmación
    frases_confirmacion = [
        'es correcto', 'correcto', 'sí es', 'si es', 'así es', 'eso es',
        'exacto', 'ese es', 'ese mero', 'ándale', 'andale', 'ajá', 'aja'
    ]
    cliente_confirma = any(frase in mensaje_cliente.lower() for frase in frases_confirmacion)

    print(f"  Cliente confirma: {cliente_confirma}")

    if cliente_confirma:
        numero_extraido = extraer_numero_del_historial(mensaje_bruce)
        print(f"  Número extraído: {numero_extraido}")

        if numero_extraido:
            print(f"\n[OK] FIX 462 capturaría el número: {numero_extraido}")
            return True
        else:
            print(f"\n[FAIL] FIX 462 NO extrajo el número")
            return False
    else:
        print(f"\n[FAIL] NO detectó confirmación del cliente")
        return False


def test_diferentes_formatos_numero():
    """
    FIX 462: Probar diferentes formatos de número en mensaje de Bruce
    """
    print("\n" + "="*60)
    print("TEST: Diferentes formatos de número")
    print("="*60)

    casos = [
        ("lo tengo anotado como 221-442-61-55", "+522214426155"),
        ("lo tengo como 33 12 34 56 78", "+523312345678"),
        ("el número es 3312345678", "+523312345678"),
        ("registrado como 33.1234.5678", "+523312345678"),
        ("es el 221 442 6155", "+522214426155"),
        ("Perfecto, 3321014486, ¿correcto?", "+523321014486"),
    ]

    errores = []

    for mensaje, esperado in casos:
        resultado = extraer_numero_del_historial(mensaje)

        if resultado == esperado:
            estado = "[OK]"
        else:
            estado = "[FAIL]"
            errores.append((mensaje, esperado, resultado))

        print(f"  {estado} '{mensaje[:40]}...' -> {resultado}")

    if errores:
        print(f"\n[FAIL] {len(errores)} casos fallaron")
        for msg, esperado, resultado in errores:
            print(f"   - '{msg[:30]}...': esperado {esperado}, obtuvo {resultado}")
        return False

    print(f"\n[OK] Todos los formatos detectados correctamente")
    return True


def test_no_falsos_positivos():
    """
    FIX 462: Verificar que NO hay falsos positivos
    """
    print("\n" + "="*60)
    print("TEST: No falsos positivos")
    print("="*60)

    # Mensajes que NO deben extraer números
    casos_negativos = [
        "Perfecto, le enviaré el catálogo",  # Sin número
        "¿Me puede dar su número de WhatsApp?",  # Pregunta, no confirmación
        "Gracias por su tiempo",  # Sin número
    ]

    falsos_positivos = []

    for mensaje in casos_negativos:
        resultado = extraer_numero_del_historial(mensaje)
        if resultado:
            falsos_positivos.append((mensaje, resultado))
            print(f"  [FAIL] Falso positivo: '{mensaje}' -> {resultado}")
        else:
            print(f"  [OK] No extrajo de: '{mensaje[:40]}...'")

    if falsos_positivos:
        print(f"\n[FAIL] {len(falsos_positivos)} falsos positivos")
        return False

    print(f"\n[OK] Sin falsos positivos")
    return True


def test_confirmaciones_cliente():
    """
    FIX 462: Probar diferentes formas de confirmación del cliente
    """
    print("\n" + "="*60)
    print("TEST: Diferentes confirmaciones del cliente")
    print("="*60)

    frases_confirmacion = [
        'es correcto', 'correcto', 'sí es', 'si es', 'así es', 'eso es',
        'exacto', 'ese es', 'ese mero', 'ándale', 'andale', 'ajá', 'aja',
        'afirmativo', 'está bien', 'esta bien', 'ok', 'okey'
    ]

    casos = [
        ("Es correcto.", True),
        ("Sí, correcto", True),
        ("Así es, ese es", True),
        ("Exacto", True),
        ("Ándale, así es", True),
        ("Ok", True),
        ("No, está mal", False),
        ("Espéreme un momento", False),
        ("El número es 3312345678", False),  # Está dando número, no confirmando
    ]

    errores = []

    for frase, esperado in casos:
        frase_lower = frase.lower()
        es_confirmacion = any(conf in frase_lower for conf in frases_confirmacion)

        if es_confirmacion == esperado:
            estado = "[OK]"
        else:
            estado = "[FAIL]"
            errores.append((frase, esperado, es_confirmacion))

        print(f"  {estado} '{frase}' -> confirmación={es_confirmacion}")

    if errores:
        print(f"\n[FAIL] {len(errores)} casos fallaron")
        return False

    print(f"\n[OK] Todas las confirmaciones detectadas correctamente")
    return True


if __name__ == "__main__":
    print("="*60)
    print("TESTS FIX 462: Capturar WhatsApp cuando cliente confirma")
    print("="*60)

    resultados = []

    resultados.append(("Caso BRUCE1396", test_caso_bruce1396()))
    resultados.append(("Diferentes formatos número", test_diferentes_formatos_numero()))
    resultados.append(("No falsos positivos", test_no_falsos_positivos()))
    resultados.append(("Confirmaciones cliente", test_confirmaciones_cliente()))

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
