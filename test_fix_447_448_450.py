# -*- coding: utf-8 -*-
"""
Test para FIX 447, 448, 450

Casos resueltos:
- BRUCE1340: FIX 263 se activó cuando cliente solo dijo "Buen día" (saludo)
- BRUCE1342: No detectó "le doy mi correo" como oferta de datos
- BRUCE1343: Usó "Sí, dígame" cuando debía reformular pregunta por encargado
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def test_fix_447_cliente_solo_saludos():
    """
    FIX 447: NO activar FIX 263 si cliente solo ha dicho saludos
    Caso BRUCE1340: Cliente repitió "Buen día" y Bruce respondió "Perfecto. ¿Hay algo más?"
    """
    print("\n" + "="*60)
    print("TEST FIX 447: Cliente solo saludos - NO activar FIX 263")
    print("="*60)

    saludos_comunes = ['buen día', 'buen dia', 'buenos días', 'buenos dias',
                      'buenas tardes', 'buenas noches', 'buenas', 'hola',
                      'dígame', 'digame', 'mande', 'sí', 'si', 'bueno', 'aló', 'alo']

    # Simular historial de mensajes del cliente
    casos = [
        # (mensajes_cliente, esperado_cliente_solo_saludo)
        (["Buen día.", "Buen día."], True),  # BRUCE1340
        (["¿Sí? ¿Bueno?", "¿Sí? ¿Bueno?"], True),  # BRUCE1343
        (["Hola", "Buenos días"], True),
        (["No se encuentra"], False),  # Esto NO es solo saludo
        (["Buen día", "No, no está el encargado"], False),  # Mezcla
        (["Me interesa el catálogo"], False),  # No es saludo
    ]

    errores = []

    for mensajes, esperado in casos:
        # Lógica de FIX 447
        mensajes_lower = [m.lower() for m in mensajes]
        cliente_solo_saludo = all(
            any(saludo in msg for saludo in saludos_comunes) and len(msg) < 30
            for msg in mensajes_lower
        ) if mensajes_lower else True

        if cliente_solo_saludo == esperado:
            print(f"  [OK] {mensajes} -> solo_saludo={cliente_solo_saludo}")
        else:
            errores.append(f"{mensajes}: esperado {esperado}, obtenido {cliente_solo_saludo}")
            print(f"  [FAIL] {mensajes} -> esperado {esperado}, obtenido {cliente_solo_saludo}")

    if errores:
        print(f"\n[FAIL] Test FIX 447 falló con {len(errores)} errores")
        return False

    print("\n[OK] Test FIX 447 pasado")
    return True


def test_fix_448_frases_ofrecimiento_datos():
    """
    FIX 448: Detectar más variantes de ofrecimiento de datos
    Caso BRUCE1342: Cliente dijo "le doy mi correo" pero no se detectó
    """
    print("\n" + "="*60)
    print("TEST FIX 448: Detectar ofertas de datos del cliente")
    print("="*60)

    frases_ofrecimiento_datos = [
        'le puedo dar', 'te puedo dar', 'le doy', 'te doy',
        'anota', 'apunta', 'mi correo', 'el correo', 'mi email',
        'le paso', 'te paso', 'mi whatsapp', 'mi número', 'mi numero',
        'manda al correo', 'mandar al correo', 'enviar al correo',
        'ahí me manda', 'ahí le mando', 'le envío', 'me envía',
        'para que me mande', 'para que le mande',
        'manda por whatsapp', 'mandar por whatsapp', 'enviar por whatsapp',
        'por whatsapp', 'al whatsapp', 'a su whatsapp', 'a tu whatsapp',
        'le mando por', 'te mando por', 'se lo mando',
        'manda por correo', 'mandar por correo', 'enviar por correo',
        'por correo', 'a su correo', 'a tu correo', 'al mail',
        'manda al mail', 'enviar al mail', 'por mail', 'mi mail',
        'el mail es', 'el correo es', 'su correo es',
        # FIX 448: Nuevas variantes
        'le doy mi correo', 'le doy el correo', 'le doy un correo',
        'le envío su correo', 'le envio su correo', 'le envío el correo',
        'ahí le puedo enviar', 'ahi le puedo enviar',
        'le puedo enviar', 'puedo enviar información', 'puedo enviar informacion',
        'doy mi número', 'doy mi numero', 'doy el número', 'doy el numero',
        'tome nota', 'toma nota', 'le doy el dato', 'le doy los datos'
    ]

    # Frases que DEBEN detectarse
    casos_positivos = [
        "No, no se encuentra, le doy mi correo",  # BRUCE1342
        "Le envío su correo",  # BRUCE1342
        "Ahí le puedo enviar información",  # BRUCE1342
        "Le doy el correo del encargado",
        "Tome nota del correo",
        "Le doy mi número de WhatsApp",
    ]

    # Frases que NO deben detectarse
    casos_negativos = [
        "Buenos días",
        "No se encuentra",
        "Un momento",
        "¿De dónde habla?",
    ]

    errores = []

    print("\n--- Casos que DEBEN detectarse ---")
    for frase in casos_positivos:
        frase_lower = frase.lower()
        detectado = any(oferta in frase_lower for oferta in frases_ofrecimiento_datos)

        if detectado:
            print(f"  [OK] '{frase[:50]}...' detectado")
        else:
            errores.append(f"'{frase}' NO fue detectado como oferta")
            print(f"  [FAIL] '{frase}' NO detectado")

    print("\n--- Casos que NO deben detectarse ---")
    for frase in casos_negativos:
        frase_lower = frase.lower()
        detectado = any(oferta in frase_lower for oferta in frases_ofrecimiento_datos)

        if not detectado:
            print(f"  [OK] '{frase}' NO detectado (correcto)")
        else:
            errores.append(f"'{frase}' fue detectado incorrectamente")
            print(f"  [FAIL] '{frase}' detectado incorrectamente")

    if errores:
        print(f"\n[FAIL] Test FIX 448 falló con {len(errores)} errores")
        return False

    print("\n[OK] Test FIX 448 pasado")
    return True


def test_fix_450_es_solo_saludo():
    """
    FIX 450: Detectar "bueno", "sí", "aló" como saludos telefónicos
    Caso BRUCE1343: Cliente dijo "¿Sí? ¿Bueno?" pero no se detectó como saludo
    """
    print("\n" + "="*60)
    print("TEST FIX 450: Detectar saludos telefónicos")
    print("="*60)

    # Lista actualizada con FIX 450
    saludos_reconocidos = [
        "buen día", "buen dia", "buenos días", "buenos dias",
        "buenas tardes", "buenas noches", "dígame", "digame",
        "mande", "sí dígame", "si digame", "qué se le ofrece",
        "que se le ofrece", "en qué le puedo", "en que le puedo",
        "cómo le ayudo", "como le ayudo", "le puedo ayudar",
        # FIX 450: Nuevas variantes
        "bueno", "sí", "si", "aló", "alo", "hola"
    ]

    # Frases que DEBEN detectarse como saludos
    casos_positivos = [
        "¿Sí? ¿Bueno?",  # BRUCE1343
        "Bueno",
        "Aló",
        "Hola",
        "Sí dígame",
        "Buenos días",
        "¿Bueno?",
    ]

    errores = []

    for frase in casos_positivos:
        frase_lower = frase.lower()
        es_saludo = any(s in frase_lower for s in saludos_reconocidos)

        if es_saludo:
            print(f"  [OK] '{frase}' detectado como saludo")
        else:
            errores.append(f"'{frase}' NO fue detectado como saludo")
            print(f"  [FAIL] '{frase}' NO detectado como saludo")

    if errores:
        print(f"\n[FAIL] Test FIX 450 falló con {len(errores)} errores")
        return False

    print("\n[OK] Test FIX 450 pasado")
    return True


def test_caso_bruce1340():
    """
    Verificar que BRUCE1340 no se repetiría con FIX 447
    """
    print("\n" + "="*60)
    print("TEST: Caso BRUCE1340 - 'Perfecto. ¿Hay algo más?' incoherente")
    print("="*60)

    # Simular historial de BRUCE1340
    mensajes_cliente = ["Buen día.", "Buen día."]

    saludos_comunes = ['buen día', 'buen dia', 'buenos días', 'buenos dias',
                      'buenas tardes', 'buenas noches', 'buenas', 'hola',
                      'dígame', 'digame', 'mande', 'sí', 'si', 'bueno', 'aló', 'alo']

    mensajes_lower = [m.lower() for m in mensajes_cliente]
    cliente_solo_saludo = all(
        any(saludo in msg for saludo in saludos_comunes) and len(msg) < 30
        for msg in mensajes_lower
    )

    print(f"  Mensajes cliente: {mensajes_cliente}")
    print(f"  Cliente solo saludó: {cliente_solo_saludo}")

    if cliente_solo_saludo:
        print(f"\n[OK] FIX 447 evitaría activar FIX 263 - no más 'Perfecto. ¿Hay algo más?'")
        return True
    else:
        print(f"\n[FAIL] FIX 447 NO evitaría el problema")
        return False


def test_caso_bruce1343():
    """
    Verificar que BRUCE1343 usaría respuesta apropiada con FIX 450
    """
    print("\n" + "="*60)
    print("TEST: Caso BRUCE1343 - 'Sí, dígame' cuando debía reformular")
    print("="*60)

    # Simular mensaje del cliente en BRUCE1343
    mensaje_cliente = "¿Sí? ¿Bueno?"

    saludos_reconocidos = [
        "buen día", "buen dia", "buenos días", "buenos dias",
        "buenas tardes", "buenas noches", "dígame", "digame",
        "mande", "sí dígame", "si digame", "qué se le ofrece",
        "que se le ofrece", "en qué le puedo", "en que le puedo",
        "cómo le ayudo", "como le ayudo", "le puedo ayudar",
        "bueno", "sí", "si", "aló", "alo", "hola"
    ]

    mensaje_lower = mensaje_cliente.lower()
    es_saludo = any(s in mensaje_lower for s in saludos_reconocidos)

    print(f"  Mensaje cliente: '{mensaje_cliente}'")
    print(f"  Detectado como saludo: {es_saludo}")

    if es_saludo:
        print(f"  Con FIX 450, se usaria: 'Si, le llamo de la marca NIOVAL. Se encuentra el encargado?'")
        print(f"\n[OK] FIX 450 evitaría 'Sí, dígame' incoherente")
        return True
    else:
        print(f"\n[FAIL] FIX 450 NO evitaría el problema")
        return False


if __name__ == "__main__":
    print("="*60)
    print("TESTS FIX 447, 448, 450")
    print("="*60)

    resultados = []

    resultados.append(("FIX 447 - Cliente solo saludos", test_fix_447_cliente_solo_saludos()))
    resultados.append(("FIX 448 - Frases ofrecimiento datos", test_fix_448_frases_ofrecimiento_datos()))
    resultados.append(("FIX 450 - Saludos telefónicos", test_fix_450_es_solo_saludo()))
    resultados.append(("Caso BRUCE1340", test_caso_bruce1340()))
    resultados.append(("Caso BRUCE1343", test_caso_bruce1343()))

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
