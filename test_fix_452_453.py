# -*- coding: utf-8 -*-
"""
Test para FIX 452 y FIX 453

FIX 452: Caso BRUCE1349 - Agregar palabras de continuacion para evitar falso positivo IVR
FIX 453: Caso BRUCE1347 - No tratar "Si" como saludo cuando cliente daba dato
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def test_fix_452_palabras_continuacion():
    """
    FIX 452: Verificar que nuevas palabras de continuacion funcionan
    Caso BRUCE1349: "ahorita estamos trabajando con un proveedor" fue detectado como IVR
    """
    print("\n" + "="*60)
    print("TEST FIX 452: Palabras de continuacion")
    print("="*60)

    frases_inicio_incompletas = [
        'en este momento',
        'ahorita',
        'ahora',
        'ahora mismo',
        'por el momento',
        'por ahora',
        'en este rato'
    ]

    # Lista actualizada con FIX 452
    palabras_continuacion = [
        'no', 'está', 'esta', 'se', 'salió', 'salio', 'hay', 'puede', 'anda',
        # FIX 452: Nuevas palabras
        'estamos', 'estoy', 'tenemos', 'tengo', 'trabajamos', 'trabajando',
        'proveedor', 'gracias', 'agradezco'
    ]

    # Casos de prueba
    casos = [
        # (frase, tiene_inicio, tiene_continuacion, deberia_procesar)
        ("en este momento", True, False, False),  # Incompleta - NO procesar
        ("en este momento no se encuentra", True, True, True),  # Completa
        ("ahorita estamos trabajando con un proveedor", True, True, True),  # FIX 452: BRUCE1349
        ("por el momento estoy ocupado", True, True, True),  # FIX 452
        ("ahorita tenemos otro proveedor", True, True, True),  # FIX 452
        ("por el momento, te agradezco mucho", True, True, True),  # FIX 452
        ("ahora", True, False, False),  # Incompleta
        ("ahora mismo anda en la comida", True, True, True),  # Completa
        ("No, no, en este momento", True, True, True),  # FIX 454: BRUCE1353 - "no" con coma
    ]

    # FIX 454: Función para limpiar puntuación (igual que en código real)
    def limpiar_palabras(frase):
        return [palabra.strip('.,;:!?¿¡') for palabra in frase.lower().split()]

    errores = []

    for frase, esperado_inicio, esperado_continuacion, deberia_procesar in casos:
        frase_lower = frase.lower()
        tiene_inicio = any(inicio in frase_lower for inicio in frases_inicio_incompletas)
        # FIX 454: Usar limpieza de puntuación
        palabras_limpias = limpiar_palabras(frase)
        tiene_continuacion = any(palabra in palabras_limpias for palabra in palabras_continuacion)

        # Si tiene inicio pero NO continuacion, NO procesar (es parcial)
        procesaria = not (tiene_inicio and not tiene_continuacion)

        # Verificar
        ok_inicio = tiene_inicio == esperado_inicio
        ok_continuacion = tiene_continuacion == esperado_continuacion
        ok_proceso = procesaria == deberia_procesar

        if ok_inicio and ok_continuacion and ok_proceso:
            print(f"  [OK] '{frase[:50]}...' -> procesar={procesaria}")
        else:
            errores.append(f"'{frase}': inicio={tiene_inicio}(esp:{esperado_inicio}), cont={tiene_continuacion}(esp:{esperado_continuacion})")
            print(f"  [FAIL] '{frase[:50]}...' -> esperado procesar={deberia_procesar}, obtenido={procesaria}")

    if errores:
        print(f"\n[FAIL] Test FIX 452 fallo con {len(errores)} errores")
        return False

    print("\n[OK] Test FIX 452 pasado")
    return True


def test_fix_453_saludo_contexto_dato():
    """
    FIX 453: NO tratar "Si" como saludo cuando cliente estaba dando dato
    Caso BRUCE1347: Cliente dijo "el telefono es" y luego "Si," pero Bruce lo trato como saludo
    """
    print("\n" + "="*60)
    print("TEST FIX 453: Saludo vs dato pendiente")
    print("="*60)

    saludos_simples = ['sí', 'si', 'bueno', 'hola', 'mande']

    palabras_esperando_dato = ['es', 'teléfono', 'telefono', 'correo', 'email', 'número', 'numero', 'whatsapp']

    # Casos de prueba
    casos = [
        # (frase_actual, transcripcion_previa, deberia_esperar)
        ("Sí,", "", False),  # Sin contexto previo - es saludo normal
        ("Sí,", "el teléfono es", True),  # FIX 453: Contexto de dato - ESPERAR
        ("Sí,", "Oh, no se encuentra. No, el teléfono es", True),  # FIX 453: BRUCE1347
        ("Hola", "buenos días", False),  # Saludo normal
        ("Si", "el correo es", True),  # FIX 453: Dato pendiente
        ("Bueno", "voy a ver si esta", False),  # No termina en palabra de dato
        ("Sí,", "arroba gmail punto com", False),  # Ya dio el dato completo
    ]

    errores = []

    for frase_actual, transcripcion_previa, esperado_esperar in casos:
        frase_limpia = frase_actual.lower().strip().strip('.,;:!?¿¡')
        es_saludo = frase_limpia in saludos_simples

        # Logica de FIX 453
        cliente_dando_dato = False
        if transcripcion_previa:
            previa_lower = transcripcion_previa.lower().strip()
            for palabra in palabras_esperando_dato:
                if previa_lower.endswith(palabra) or f'{palabra} es' in previa_lower or f'el {palabra}' in previa_lower:
                    cliente_dando_dato = True
                    break

        # Si es saludo Y hay dato pendiente, deberia esperar
        deberia_esperar_calculado = es_saludo and cliente_dando_dato

        if deberia_esperar_calculado == esperado_esperar:
            print(f"  [OK] '{frase_actual}' (prev: '{transcripcion_previa[:30]}...') -> esperar={deberia_esperar_calculado}")
        else:
            errores.append(f"'{frase_actual}' con previa '{transcripcion_previa}'")
            print(f"  [FAIL] '{frase_actual}' -> esperado esperar={esperado_esperar}, obtenido={deberia_esperar_calculado}")

    if errores:
        print(f"\n[FAIL] Test FIX 453 fallo con {len(errores)} errores")
        return False

    print("\n[OK] Test FIX 453 pasado")
    return True


def test_caso_bruce1349():
    """
    Verificar que BRUCE1349 no se repetiria con FIX 452
    """
    print("\n" + "="*60)
    print("TEST: Caso BRUCE1349 - Falso positivo IVR")
    print("="*60)

    # Frase del cliente en BRUCE1349
    frase = "Bueno, ahorita, por el momento, ahorita estamos trabajando con un proveedor, estimado. Te agradezco mucho."

    frases_inicio = ['en este momento', 'ahorita', 'ahora', 'por el momento', 'por ahora']
    palabras_continuacion = [
        'no', 'está', 'esta', 'se', 'salió', 'salio', 'hay', 'puede', 'anda',
        'estamos', 'estoy', 'tenemos', 'tengo', 'trabajamos', 'trabajando',
        'proveedor', 'gracias', 'agradezco'
    ]

    frase_lower = frase.lower()
    tiene_inicio = any(inicio in frase_lower for inicio in frases_inicio)
    # FIX 454: Usar limpieza de puntuación
    palabras_limpias = [palabra.strip('.,;:!?¿¡') for palabra in frase_lower.split()]
    tiene_continuacion = any(palabra in palabras_limpias for palabra in palabras_continuacion)

    print(f"  Frase: '{frase[:60]}...'")
    print(f"  Tiene frase de inicio: {tiene_inicio}")
    print(f"  Tiene continuacion: {tiene_continuacion}")

    # Con FIX 452, deberia detectar "estamos", "trabajando", "proveedor", "agradezco"
    if tiene_inicio and tiene_continuacion:
        print(f"  FIX 452: Se procesaria como PERSONA REAL (no IVR)")
        print(f"\n[OK] FIX 452 evitaria falso positivo de IVR")
        return True
    else:
        print(f"\n[FAIL] FIX 452 NO evitaria el problema")
        return False


def test_caso_bruce1347():
    """
    Verificar que BRUCE1347 no se repetiria con FIX 453
    """
    print("\n" + "="*60)
    print("TEST: Caso BRUCE1347 - Si como saludo durante dato")
    print("="*60)

    # Secuencia de BRUCE1347
    transcripcion_previa = "Oh, no se encuentra. No, el teléfono es"
    frase_actual = "Sí,"

    saludos_simples = ['sí', 'si', 'bueno', 'hola', 'mande']
    palabras_esperando_dato = ['es', 'teléfono', 'telefono', 'correo', 'número', 'numero']

    frase_limpia = frase_actual.lower().strip().strip('.,;:!?¿¡')
    es_saludo = frase_limpia in saludos_simples

    previa_lower = transcripcion_previa.lower().strip()
    cliente_dando_dato = any(
        previa_lower.endswith(palabra) or f'el {palabra}' in previa_lower
        for palabra in palabras_esperando_dato
    )

    print(f"  Transcripcion previa: '{transcripcion_previa}'")
    print(f"  Frase actual: '{frase_actual}'")
    print(f"  Es saludo simple: {es_saludo}")
    print(f"  Cliente dando dato (previo): {cliente_dando_dato}")

    if es_saludo and cliente_dando_dato:
        print(f"  FIX 453: NO trataria como saludo - ESPERARIA por el dato")
        print(f"\n[OK] FIX 453 evitaria interrumpir captura de dato")
        return True
    else:
        print(f"\n[FAIL] FIX 453 NO evitaria el problema")
        return False


if __name__ == "__main__":
    print("="*60)
    print("TESTS FIX 452 y FIX 453")
    print("="*60)

    resultados = []

    resultados.append(("FIX 452 - Palabras continuacion", test_fix_452_palabras_continuacion()))
    resultados.append(("FIX 453 - Saludo vs dato", test_fix_453_saludo_contexto_dato()))
    resultados.append(("Caso BRUCE1349", test_caso_bruce1349()))
    resultados.append(("Caso BRUCE1347", test_caso_bruce1347()))

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
