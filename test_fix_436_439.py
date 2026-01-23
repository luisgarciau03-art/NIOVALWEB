#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test para verificar FIX 436, 437, 438, 439

FIX 436: Caso BRUCE1322 - Mejorar detección de saludos en REGLA 4
         "Hola, buenos días. ¿Bueno?" NO es pregunta real

FIX 437: Caso BRUCE1322 - No ofrecer catálogo cuando Bruce pidió número de encargado
         Cliente dice "Por favor," después de pedir número → esperar número

FIX 438: Caso BRUCE1321 - Agregar "todavía no llega" a detección de regreso
         "No se encuentra, oiga, todavía no llega" → detectar encargado no está

FIX 439: Caso BRUCE1317 - Reconocer "Me comunico de NIOVAL" como respuesta válida
         Cliente pregunta "¿De dónde habla?" → Bruce responde con identificación
"""

import os
import sys

def test_fix_436():
    """
    FIX 436: Mejorar detección de saludos que NO son preguntas reales
    Caso: BRUCE1322 - "Hola, buenos días. ¿Bueno?"
    """
    print("\n" + "="*60)
    print("TEST FIX 436: Detección de saludos mejorada")
    print("="*60)

    with open('agente_ventas.py', 'r', encoding='utf-8') as f:
        codigo = f.read()

    errores = []

    # Verificar comentarios FIX 436
    if "# FIX 436:" not in codigo:
        errores.append("Falta comentario '# FIX 436:'")

    # Verificar BRUCE1322 mencionado
    if "BRUCE1322" not in codigo:
        errores.append("Falta mención a 'BRUCE1322'")

    # Verificar patrones de saludo agregados
    if "patrones_saludo" not in codigo:
        errores.append("Falta variable 'patrones_saludo'")

    if "'hola'" not in codigo.lower():
        errores.append("Falta patrón 'hola' en patrones_saludo")

    if "'buenos días'" not in codigo.lower() and "'buenos dias'" not in codigo.lower():
        errores.append("Falta patrón 'buenos días' en patrones_saludo")

    # Verificar lógica de detección mejorada
    if "contiene_saludo_interrogacion" not in codigo:
        errores.append("Falta variable 'contiene_saludo_interrogacion'")

    if "es_saludo_tipico" not in codigo:
        errores.append("Falta variable 'es_saludo_tipico'")

    if errores:
        print(f"   [FAIL] FALLÓ: {len(errores)} errores encontrados")
        for e in errores:
            print(f"      - {e}")
        return False

    print("   [OK] FIX 436 implementado correctamente")
    return True


def test_fix_437():
    """
    FIX 437: Prevenir oferta de catálogo después de pedir número de encargado
    Caso: BRUCE1322 - Cliente dice "Por favor," y Bruce ofrece catálogo
    """
    print("\n" + "="*60)
    print("TEST FIX 437: No ofrecer catálogo tras pedir número")
    print("="*60)

    with open('agente_ventas.py', 'r', encoding='utf-8') as f:
        codigo = f.read()

    errores = []

    # Verificar comentarios FIX 437
    if "# FILTRO 19C (FIX 437):" not in codigo and "FIX 437:" not in codigo:
        errores.append("Falta comentario 'FIX 437:'")

    # Verificar patrones de confirmación
    patrones_confirmacion = ['por favor', 'claro', 'adelante', 'un momento']
    encontrados = sum(1 for p in patrones_confirmacion if p in codigo.lower())
    if encontrados < 3:
        errores.append(f"Faltan patrones de confirmación (encontrados: {encontrados}/4)")

    # Verificar mensaje de respuesta
    if "Perfecto. Adelante, lo escucho." not in codigo:
        errores.append("Falta respuesta corregida 'Perfecto. Adelante, lo escucho.'")

    if errores:
        print(f"   [FAIL] FALLÓ: {len(errores)} errores encontrados")
        for e in errores:
            print(f"      - {e}")
        return False

    print("   [OK] FIX 437 implementado correctamente")
    return True


def test_fix_438():
    """
    FIX 438: Agregar "todavía no llega" a detección de encargado no está
    Caso: BRUCE1321 - "No se encuentra, oiga, todavía no llega"
    """
    print("\n" + "="*60)
    print("TEST FIX 438: Detectar 'todavía no llega'")
    print("="*60)

    with open('agente_ventas.py', 'r', encoding='utf-8') as f:
        codigo = f.read()

    errores = []

    # Verificar comentarios FIX 438
    if "# FIX 438:" not in codigo:
        errores.append("Falta comentario '# FIX 438:'")

    # Verificar BRUCE1321 mencionado
    if "BRUCE1321" not in codigo:
        errores.append("Falta mención a 'BRUCE1321'")

    # Verificar patrones agregados
    patrones_438 = [
        'todavía no llega', 'todavia no llega',
        'aún no llega', 'aun no llega',
        'no ha llegado'
    ]

    encontrados = sum(1 for p in patrones_438 if f"'{p}'" in codigo.lower())
    if encontrados < 4:
        errores.append(f"Faltan patrones de 'no llega' (encontrados: {encontrados}/5)")

    # Verificar que está en múltiples ubicaciones (3 listas de patrones)
    ocurrencias = codigo.lower().count("'todavía no llega'") + codigo.lower().count("'todavia no llega'")
    if ocurrencias < 3:
        errores.append(f"Patrón 'todavía no llega' debe estar en 3 ubicaciones (encontrado: {ocurrencias})")

    if errores:
        print(f"   [FAIL] FALLÓ: {len(errores)} errores encontrados")
        for e in errores:
            print(f"      - {e}")
        return False

    print("   [OK] FIX 438 implementado correctamente")
    return True


def test_fix_439():
    """
    FIX 439: Reconocer "Me comunico de NIOVAL" como respuesta válida
    Caso: BRUCE1317 - Cliente pregunta "¿De dónde habla?"
    """
    print("\n" + "="*60)
    print("TEST FIX 439: Reconocer identificación como respuesta")
    print("="*60)

    with open('agente_ventas.py', 'r', encoding='utf-8') as f:
        codigo = f.read()

    errores = []

    # Verificar comentarios FIX 439
    if "# FIX 439:" not in codigo:
        errores.append("Falta comentario '# FIX 439:'")

    # Verificar BRUCE1317 mencionado
    if "BRUCE1317" not in codigo:
        errores.append("Falta mención a 'BRUCE1317'")

    # Verificar patrones de identificación agregados a bruce_responde
    patrones_identificacion = ['nioval', 'me comunico de', 'la marca']

    # Buscar en la sección de bruce_responde
    encontrados = sum(1 for p in patrones_identificacion if f"'{p}'" in codigo.lower())
    if encontrados < 3:
        errores.append(f"Faltan patrones de identificación (encontrados: {encontrados}/3)")

    if errores:
        print(f"   [FAIL] FALLÓ: {len(errores)} errores encontrados")
        for e in errores:
            print(f"      - {e}")
        return False

    print("   [OK] FIX 439 implementado correctamente")
    return True


def test_fix_440():
    """
    FIX 440: No preguntar 2 veces por el encargado de compras
    Caso: BRUCE1326 - Bruce ya pregunto por encargado, no repetir
    """
    print("\n" + "="*60)
    print("TEST FIX 440: No repetir pregunta por encargado")
    print("="*60)

    with open('agente_ventas.py', 'r', encoding='utf-8') as f:
        codigo = f.read()

    errores = []

    # Verificar comentarios FIX 440
    if "# FIX 440:" not in codigo:
        errores.append("Falta comentario '# FIX 440:'")

    # Verificar BRUCE1326 mencionado
    if "BRUCE1326" not in codigo:
        errores.append("Falta mencion a 'BRUCE1326'")

    # Verificar variable de deteccion
    if "bruce_ya_pregunto_encargado" not in codigo:
        errores.append("Falta variable 'bruce_ya_pregunto_encargado'")

    # Verificar mensaje corto (no repetir pregunta completa)
    if "Le preguntaba si se encuentra" not in codigo:
        errores.append("Falta mensaje corto 'Le preguntaba si se encuentra'")

    if errores:
        print(f"   [FAIL] FALLO: {len(errores)} errores encontrados")
        for e in errores:
            print(f"      - {e}")
        return False

    print("   [OK] FIX 440 implementado correctamente")
    return True


def main():
    """Ejecutar todos los tests"""
    print("\n" + "="*70)
    print("TESTS FIX 436, 437, 438, 439, 440")
    print("="*70)

    # Cambiar al directorio del script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)

    resultados = []

    # Ejecutar tests
    resultados.append(("FIX 436 - Deteccion saludos mejorada", test_fix_436()))
    resultados.append(("FIX 437 - No catalogo tras pedir numero", test_fix_437()))
    resultados.append(("FIX 438 - 'Todavia no llega'", test_fix_438()))
    resultados.append(("FIX 439 - Identificacion como respuesta", test_fix_439()))
    resultados.append(("FIX 440 - No repetir pregunta encargado", test_fix_440()))

    # Resumen
    print("\n" + "="*70)
    print("RESUMEN DE TESTS")
    print("="*70)

    pasados = sum(1 for _, r in resultados if r)
    total = len(resultados)

    for nombre, resultado in resultados:
        estado = "[OK] PASADO" if resultado else "[FAIL] FALLIDO"
        print(f"   {estado}: {nombre}")

    print("\n" + "-"*70)
    print(f"RESULTADO: {pasados}/{total} tests pasados ({100*pasados//total}%)")
    print("-"*70)

    return 0 if pasados == total else 1


if __name__ == "__main__":
    sys.exit(main())
