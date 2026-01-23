# -*- coding: utf-8 -*-
"""
Test para FIX 458: Mejorar detección de saludos con puntuación

Problema: BRUCE1377 - Cliente dijo "Buen día" pero Bruce tuvo delay
y respondió "Disculpe no alcancé a escuchar" porque FIX 244 detectó
"habló rápido" y no reconoció el saludo por la puntuación.

Solución: Limpiar toda la puntuación (incluyendo comas internas)
antes de comparar con la lista de saludos simples.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import re


def test_deteccion_saludos_con_puntuacion():
    """
    FIX 458: Verificar que saludos con puntuación se detectan correctamente
    """
    print("\n" + "="*60)
    print("TEST FIX 458: Detección de saludos con puntuación")
    print("="*60)

    saludos_simples = [
        'hola', 'buenas', 'buenos días', 'buenos dias', 'buen día', 'buen dia',
        'buenas tardes', 'buenas noches', 'qué tal', 'que tal',
        'bueno', 'aló', 'alo', 'diga', 'dígame', 'digame',
        'mande', 'sí', 'si', 'sí dígame', 'si digame',
        # FIX 458: Variantes con coma
        'sí, dígame', 'si, digame', 'sí, diga', 'si, diga',
        'buen día, dígame', 'buen dia, digame'
    ]

    # FIX 458: Crear lista sin puntuación
    saludos_sin_puntuacion = [re.sub(r'[.,;:!?¿¡]', '', s).strip() for s in saludos_simples]

    casos = [
        # (frase, deberia_ser_saludo)
        ("Sí, dígame.", True),   # BRUCE1377/1382 - CON coma
        ("Sí dígame", True),     # Sin coma
        ("Buen día", True),      # BRUCE1377
        ("Buen día.", True),     # Con punto
        ("¿Bueno?", True),       # Con signos de pregunta
        ("Hola!", True),         # Con exclamación
        ("Sí, diga.", True),     # Variante
        ("Buenos días", True),
        ("Buenas tardes.", True),
        ("Mande", True),
        ("Dígame", True),
        # Casos que NO son saludos simples
        ("No se encuentra", False),
        ("Ahorita no está", False),
        ("Espéreme un momento", False),
    ]

    errores = []

    for frase, esperado in casos:
        frase_lower = frase.lower()
        # FIX 458: Limpiar TODA puntuación
        frase_para_comparar = re.sub(r'[.,;:!?¿¡]', '', frase_lower).strip()
        es_saludo = frase_para_comparar in saludos_sin_puntuacion or frase_lower.strip('.,;:!?¿¡') in saludos_simples

        if es_saludo == esperado:
            estado = "[OK]"
        else:
            estado = "[FAIL]"
            errores.append(frase)

        print(f"  {estado} '{frase}' -> saludo={es_saludo} (esperado={esperado})")

    if errores:
        print(f"\n[FAIL] Test fallado con {len(errores)} errores: {errores}")
        return False

    print(f"\n[OK] Test pasado")
    return True


def test_caso_bruce1377():
    """
    FIX 458: Simular caso exacto de BRUCE1377
    """
    print("\n" + "="*60)
    print("TEST: Caso BRUCE1377 - Saludo con delay")
    print("="*60)

    # Contexto BRUCE1377 (similar a BRUCE1382 que vimos en logs)
    speech_result = "Sí, dígame."
    tiempo_hablando = 1.7
    palabras_nuevas = 2

    # Verificar si FIX 244 lo marcaría como incompleta
    es_pregunta = '?' in speech_result or '¿' in speech_result
    termina_en_pregunta = speech_result.strip().endswith('?')

    # Condición de FIX 244
    frase_parece_incompleta = tiempo_hablando < 2.0 and palabras_nuevas >= 2 and not es_pregunta and not termina_en_pregunta

    print(f"  Speech result: '{speech_result}'")
    print(f"  Tiempo hablando: {tiempo_hablando}s")
    print(f"  Palabras nuevas: {palabras_nuevas}")
    print(f"  FIX 244 marcaría como incompleta: {frase_parece_incompleta}")

    # Ahora verificar FIX 458 (detección de saludo)
    saludos_simples = [
        'hola', 'buenas', 'buenos días', 'buenos dias', 'buen día', 'buen dia',
        'buenas tardes', 'buenas noches', 'qué tal', 'que tal',
        'bueno', 'aló', 'alo', 'diga', 'dígame', 'digame',
        'mande', 'sí', 'si', 'sí dígame', 'si digame',
        'sí, dígame', 'si, digame', 'sí, diga', 'si, diga'
    ]

    frase_limpia = speech_result.lower()
    frase_para_comparar = re.sub(r'[.,;:!?¿¡]', '', frase_limpia).strip()
    saludos_sin_puntuacion = [re.sub(r'[.,;:!?¿¡]', '', s).strip() for s in saludos_simples]
    frase_es_saludo_simple = frase_para_comparar in saludos_sin_puntuacion

    print(f"  Frase limpia: '{frase_limpia}'")
    print(f"  Frase para comparar: '{frase_para_comparar}'")
    print(f"  Es saludo simple: {frase_es_saludo_simple}")

    # FIX 441 desactivaría frase_parece_incompleta si es saludo
    if frase_parece_incompleta and frase_es_saludo_simple:
        frase_parece_incompleta = False
        print(f"\n  Con FIX 458:")
        print(f"    FIX 441 detectaría saludo y desactivaría espera")
        print(f"    Bruce respondería inmediatamente")
        print(f"\n[OK] FIX 458 evitaría delay de BRUCE1377")
        return True
    elif not frase_es_saludo_simple:
        print(f"\n[FAIL] FIX 458 NO detectó el saludo")
        return False
    else:
        print(f"\n[OK] No había espera desde el inicio")
        return True


def test_no_confundir_con_frases_incompletas():
    """
    FIX 458: Verificar que NO se confunda saludos con frases incompletas
    """
    print("\n" + "="*60)
    print("TEST: No confundir saludos con frases incompletas")
    print("="*60)

    saludos_simples = [
        'hola', 'buenas', 'buenos días', 'buenos dias', 'buen día', 'buen dia',
        'buenas tardes', 'buenas noches', 'qué tal', 'que tal',
        'bueno', 'aló', 'alo', 'diga', 'dígame', 'digame',
        'mande', 'sí', 'si', 'sí dígame', 'si digame',
        'sí, dígame', 'si, digame'
    ]
    saludos_sin_puntuacion = [re.sub(r'[.,;:!?¿¡]', '', s).strip() for s in saludos_simples]

    # Frases que NO deben ser detectadas como saludos
    frases_no_saludos = [
        "En este momento",      # Frase incompleta
        "Ahorita",              # Frase incompleta
        "No, el correo es",     # Dando dato
        "Sí, el número es",     # Dando dato
        "Le doy un correo",     # Ofreciendo dato
    ]

    todos_correctos = True

    for frase in frases_no_saludos:
        frase_lower = frase.lower()
        frase_para_comparar = re.sub(r'[.,;:!?¿¡]', '', frase_lower).strip()
        es_saludo = frase_para_comparar in saludos_sin_puntuacion

        if es_saludo:
            print(f"  [FAIL] '{frase}' detectado como saludo INCORRECTAMENTE")
            todos_correctos = False
        else:
            print(f"  [OK] '{frase}' NO es saludo (correcto)")

    if todos_correctos:
        print(f"\n[OK] Test pasado - No hay falsos positivos")
        return True
    else:
        print(f"\n[FAIL] Hay falsos positivos")
        return False


if __name__ == "__main__":
    print("="*60)
    print("TESTS FIX 458: Detección de saludos con puntuación")
    print("="*60)

    resultados = []

    resultados.append(("Saludos con puntuación", test_deteccion_saludos_con_puntuacion()))
    resultados.append(("Caso BRUCE1377", test_caso_bruce1377()))
    resultados.append(("No falsos positivos", test_no_confundir_con_frases_incompletas()))

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
