# -*- coding: utf-8 -*-
"""
Test para FIX 468: No interrumpir cuando cliente esta dictando numero

Problema: BRUCE1406 - Cliente dijo "9 51. 9 51," (dictando numero)
          Bruce lo interrumpio con "¿Me podria proporcionar el numero directo?"
          Cliente colgo frustrado

Solucion: Detectar dictado de numeros (pocos digitos + coma al final)
          y generar respuesta minima "Aja..." para no interrumpir
"""

import sys
import os
import re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def detectar_cliente_dictando(mensaje: str) -> tuple:
    """
    Simula la logica de FIX 434/468 para detectar si cliente esta dictando numero
    Retorna (esta_dictando, razon, num_digitos)
    """
    mensaje_lower = mensaje.lower().strip()

    # Extraer digitos
    digitos = re.findall(r'\d', mensaje)
    num_digitos = len(digitos)

    if num_digitos == 0:
        return (False, "sin digitos", 0)

    # Patrones de dictado
    patrones_dictado = [
        r'\d+\s+\d+',  # Numeros separados por espacios
        r'\d+,\s*\d+',  # Numeros separados por comas
        r'\d+\.\s*\d+',  # Numeros separados por puntos
    ]

    palabras_inicio_dictado = [
        'es el', 'son el', 'empieza', 'inicia', 'comienza',
        'son los', 'es los', 'primero'
    ]

    tiene_patron_dictado = any(re.search(patron, mensaje) for patron in patrones_dictado)
    tiene_palabra_inicio = any(palabra in mensaje_lower for palabra in palabras_inicio_dictado)
    termina_en_coma = mensaje.strip().endswith(',')

    # Cliente esta dictando si tiene pocos digitos Y algun indicador
    if 3 <= num_digitos <= 8 and (tiene_patron_dictado or tiene_palabra_inicio or termina_en_coma):
        razon = []
        if tiene_patron_dictado:
            razon.append("patron dictado")
        if tiene_palabra_inicio:
            razon.append("palabra inicio")
        if termina_en_coma:
            razon.append("termina en coma")
        return (True, ", ".join(razon), num_digitos)

    return (False, "numero normal", num_digitos)


def test_caso_bruce1406():
    """
    FIX 468: Simular caso BRUCE1406 - Cliente dictando numero
    """
    print("\n" + "="*60)
    print("TEST: Caso BRUCE1406 - Cliente dictando numero")
    print("="*60)

    mensaje = "9 51. 9 51,"

    print(f"  Cliente dijo: '{mensaje}'")

    esta_dictando, razon, num_digitos = detectar_cliente_dictando(mensaje)

    print(f"  Esta dictando: {esta_dictando}")
    print(f"  Razon: {razon}")
    print(f"  Digitos: {num_digitos}")

    if esta_dictando and "coma" in razon:
        print(f"\n[OK] FIX 468 detectaria dictado por coma al final")
        return True
    else:
        print(f"\n[FAIL] FIX 468 NO detectaria dictado")
        return False


def test_patrones_dictado():
    """
    FIX 468: Varios patrones de dictado de numeros
    """
    print("\n" + "="*60)
    print("TEST: Varios patrones de dictado")
    print("="*60)

    casos_dictado = [
        ("9 51. 9 51,", True),  # Termina en coma
        ("Es el 3 40", True),   # Palabra inicio + espacios
        ("342, 109, 76", True),  # Comas entre numeros
        ("Son los 951", True),   # Palabra inicio
        ("3 4 2", True),         # Numeros separados
        ("Empieza con 332", True),  # Palabra inicio (3 digitos minimo)
    ]

    errores = []

    for mensaje, esperado in casos_dictado:
        esta_dictando, razon, _ = detectar_cliente_dictando(mensaje)

        if esta_dictando == esperado:
            estado = "[OK]"
            print(f"  {estado} '{mensaje}' -> dictando ({razon})")
        else:
            estado = "[FAIL]"
            print(f"  {estado} '{mensaje}' -> NO detectado")
            errores.append(mensaje)

    if errores:
        print(f"\n[FAIL] {len(errores)} patrones NO detectados")
        return False

    print(f"\n[OK] Todos los patrones de dictado detectados")
    return True


def test_numeros_completos():
    """
    FIX 468: Numeros completos NO deben detectarse como dictando
    """
    print("\n" + "="*60)
    print("TEST: Numeros completos NO son dictando")
    print("="*60)

    casos_completos = [
        "9515123456",          # 10 digitos juntos
        "951 512 34 56",       # 10 digitos con espacios
        "Es el 9515123456",    # 10 digitos con palabra inicio
        "Mi numero es 5212345678901",  # 12 digitos internacional
    ]

    errores = []

    for mensaje in casos_completos:
        esta_dictando, razon, num_digitos = detectar_cliente_dictando(mensaje)

        # Numeros con 10+ digitos NO deben considerarse como "dictando"
        # (ya estan completos)
        if num_digitos >= 10 and not esta_dictando:
            print(f"  [OK] '{mensaje[:30]}...' ({num_digitos} digitos) -> NO dictando")
        elif num_digitos < 10:
            print(f"  [SKIP] '{mensaje}' tiene {num_digitos} digitos (incompleto)")
        else:
            print(f"  [FAIL] '{mensaje}' detectado como dictando incorrectamente")
            errores.append(mensaje)

    if errores:
        print(f"\n[FAIL] {len(errores)} numeros completos detectados como dictando")
        return False

    print(f"\n[OK] Numeros completos NO detectados como dictando")
    return True


def test_mensajes_sin_numeros():
    """
    FIX 468: Mensajes sin numeros NO activan FIX 468
    """
    print("\n" + "="*60)
    print("TEST: Mensajes sin numeros NO activan FIX 468")
    print("="*60)

    casos_sin_numeros = [
        "Si, adelante",
        "No me interesa",
        "El encargado no esta",
        "Mande, digame",
    ]

    errores = []

    for mensaje in casos_sin_numeros:
        esta_dictando, razon, num_digitos = detectar_cliente_dictando(mensaje)

        if not esta_dictando and num_digitos == 0:
            print(f"  [OK] '{mensaje}' -> sin digitos, no dictando")
        else:
            print(f"  [FAIL] '{mensaje}' -> detectado incorrectamente")
            errores.append(mensaje)

    if errores:
        print(f"\n[FAIL] {len(errores)} mensajes sin numeros detectados")
        return False

    print(f"\n[OK] Mensajes sin numeros ignorados correctamente")
    return True


if __name__ == "__main__":
    print("="*60)
    print("TESTS FIX 468: No interrumpir cuando cliente dicta numero")
    print("="*60)

    resultados = []

    resultados.append(("Caso BRUCE1406", test_caso_bruce1406()))
    resultados.append(("Patrones dictado", test_patrones_dictado()))
    resultados.append(("Numeros completos", test_numeros_completos()))
    resultados.append(("Sin numeros", test_mensajes_sin_numeros()))

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
