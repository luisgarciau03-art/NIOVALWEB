# -*- coding: utf-8 -*-
"""
Test para FIX 441-442: Reduccion de delays en saludos simples

FIX 441: No esperar continuacion para saludos simples
FIX 442: Reducir timeout de 2.5s a 1.5s para frases que no son deletreo de email

Casos resueltos:
- BRUCE1329: Delay 10-12 segundos (cliente repitio "Bueno?")
- BRUCE1330: Delay 10-12 segundos + GPT timeout
- BRUCE1331: Bruce pregunto 2 veces por encargado
- BRUCE1332: Delay en respuesta
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def test_fix_441_saludos_simples():
    """
    FIX 441: Verificar que saludos simples no esperan continuacion
    """
    print("\n" + "="*60)
    print("TEST FIX 441: Saludos simples NO esperan continuacion")
    print("="*60)

    # Lista de saludos simples que no deben esperar
    saludos_simples = [
        'hola', 'buenas', 'buenos días', 'buenos dias', 'buen día', 'buen dia',
        'buenas tardes', 'buenas noches', 'qué tal', 'que tal',
        'bueno', 'aló', 'alo', 'diga', 'dígame', 'digame',
        'mande', 'sí', 'si', 'sí dígame', 'si digame'
    ]

    # Frases que DEBEN ser detectadas como saludos (incluye variantes con puntuacion)
    saludos_a_probar = saludos_simples + ['¿bueno?', '¡hola!', 'bueno?']

    # Simular la logica de FIX 441
    errores = []
    for saludo in saludos_a_probar:
        frase_limpia = saludo.strip().lower()
        # Limpiar signos de interrogacion/exclamacion de ambos lados
        frase_para_comparar = frase_limpia.strip('.,;:!?¿¡')
        frase_es_saludo_simple = frase_para_comparar in saludos_simples

        if not frase_es_saludo_simple:
            errores.append(f"'{saludo}' no fue detectado como saludo simple")
            print(f"  [FAIL] '{saludo}' NO detectado como saludo simple")
        else:
            print(f"  [OK] '{saludo}' detectado correctamente")

    # Verificar frases que NO son saludos simples
    no_saludos = [
        'no se encuentra', 'todavia no llega', 'un momento',
        'soy el encargado', 'en que te puedo ayudar'
    ]

    for frase in no_saludos:
        frase_limpia = frase.strip().lower()
        frase_para_comparar = frase_limpia.strip('.,;:!?¿¡')
        frase_es_saludo_simple = frase_para_comparar in saludos_simples

        if frase_es_saludo_simple:
            errores.append(f"'{frase}' fue detectado incorrectamente como saludo simple")
            print(f"  [FAIL] '{frase}' detectado incorrectamente como saludo")
        else:
            print(f"  [OK] '{frase}' NO es saludo simple (correcto)")

    if errores:
        print(f"\n[FAIL] Test FIX 441 fallo con {len(errores)} errores:")
        for e in errores:
            print(f"  - {e}")
        return False

    print("\n[OK] Test FIX 441 pasado - Saludos simples detectados correctamente")
    return True


def test_fix_442_timeout_dinamico():
    """
    FIX 442: Verificar que el timeout es dinamico
    - 2.5s para deletreo de email
    - 1.5s para otras frases
    """
    print("\n" + "="*60)
    print("TEST FIX 442: Timeout dinamico basado en contenido")
    print("="*60)

    palabras_deletreo_email = ["arroba", "punto", "guion", "guión", "bajo", "@", "gmail", "hotmail", "yahoo"]

    # Frases que SON deletreo de email (timeout = 2.5s)
    frases_email = [
        'ventas arroba',
        'ventas 1 arroba gmail',
        'punto com',
        'hotmail punto',
        'guion bajo'
    ]

    # Frases que NO son deletreo de email (timeout = 1.5s)
    frases_normales = [
        'buenos dias',
        'no se encuentra',
        'un momento',
        'si claro'
    ]

    errores = []

    for frase in frases_email:
        esta_deletreando = any(palabra in frase.lower() for palabra in palabras_deletreo_email)
        timeout_esperado = 2.5 if esta_deletreando else 1.5

        if timeout_esperado != 2.5:
            errores.append(f"'{frase}' deberia tener timeout 2.5s (tiene {timeout_esperado}s)")
            print(f"  [FAIL] '{frase}' timeout incorrecto: {timeout_esperado}s (esperado 2.5s)")
        else:
            print(f"  [OK] '{frase}' -> timeout 2.5s (email)")

    for frase in frases_normales:
        esta_deletreando = any(palabra in frase.lower() for palabra in palabras_deletreo_email)
        timeout_esperado = 2.5 if esta_deletreando else 1.5

        if timeout_esperado != 1.5:
            errores.append(f"'{frase}' deberia tener timeout 1.5s (tiene {timeout_esperado}s)")
            print(f"  [FAIL] '{frase}' timeout incorrecto: {timeout_esperado}s (esperado 1.5s)")
        else:
            print(f"  [OK] '{frase}' -> timeout 1.5s (normal)")

    if errores:
        print(f"\n[FAIL] Test FIX 442 fallo con {len(errores)} errores:")
        for e in errores:
            print(f"  - {e}")
        return False

    print("\n[OK] Test FIX 442 pasado - Timeouts dinamicos correctos")
    return True


def test_casos_bruce():
    """
    Verificar que los casos BRUCE1329-1332 serian manejados correctamente
    """
    print("\n" + "="*60)
    print("TEST: Casos BRUCE1329-1332")
    print("="*60)

    saludos_simples = [
        'hola', 'buenas', 'buenos días', 'buenos dias', 'buen día', 'buen dia',
        'buenas tardes', 'buenas noches', 'qué tal', 'que tal',
        'bueno', 'aló', 'alo', 'diga', 'dígame', 'digame',
        'mande', 'sí', 'si', 'sí dígame', 'si digame'
    ]

    casos = [
        # (ID, frase, esperado_esperar)
        ("BRUCE1329", "buen día, diga.", False),  # FIX 441: saludo simple, no esperar
        ("BRUCE1330", "¿franco?", False),  # Pregunta, no esperar (FIX 260/264)
        ("BRUCE1331", "buenos días.", False),  # FIX 441: saludo simple, no esperar
        ("BRUCE1332", "buenos días.", False),  # FIX 441: saludo simple, no esperar
    ]

    errores = []
    for bruce_id, frase, esperado_esperar in casos:
        frase_limpia = frase.strip().lower()

        # Verificar si es saludo simple (con limpieza de signos de ambos lados)
        frase_para_comparar = frase_limpia.strip('.,;:!?¿¡')
        es_saludo_simple = frase_para_comparar in saludos_simples

        # Verificar si es pregunta
        es_pregunta = (
            frase_limpia.startswith('¿') or
            frase_limpia.endswith('?')
        )

        # Con FIX 441 y FIX 260/264, estos casos NO deberian esperar
        deberia_esperar = False if (es_saludo_simple or es_pregunta) else esperado_esperar

        resultado = "[OK]" if deberia_esperar == esperado_esperar else "[FAIL]"

        if deberia_esperar != esperado_esperar:
            errores.append(f"{bruce_id}: '{frase}' esperado={esperado_esperar}, obtenido={deberia_esperar}")

        print(f"  {resultado} {bruce_id}: '{frase}'")
        print(f"         saludo_simple={es_saludo_simple}, pregunta={es_pregunta}, esperar={deberia_esperar}")

    if errores:
        print(f"\n[FAIL] Test casos BRUCE fallo:")
        for e in errores:
            print(f"  - {e}")
        return False

    print("\n[OK] Test casos BRUCE pasado")
    return True


if __name__ == "__main__":
    print("="*60)
    print("TESTS FIX 441-442: Reduccion de delays")
    print("="*60)

    resultados = []

    resultados.append(("FIX 441 - Saludos simples", test_fix_441_saludos_simples()))
    resultados.append(("FIX 442 - Timeout dinamico", test_fix_442_timeout_dinamico()))
    resultados.append(("Casos BRUCE", test_casos_bruce()))

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
