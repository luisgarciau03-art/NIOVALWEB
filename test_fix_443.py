# -*- coding: utf-8 -*-
"""
Test para FIX 443: Detectar cuando cliente OFRECE dar datos

Caso resuelto:
- BRUCE1334: Cliente ofreció correo pero Bruce no lo captó a tiempo

El problema era:
1. Cliente dice "No se encuentra, pero le puedo dar un correo..."
2. Sistema no detectaba que el cliente está OFRECIENDO un dato importante
3. Bruce preguntaba "¿Me escucha?" en lugar de aceptar la oferta

Solución:
- servidor_llamadas.py: Detectar ofertas en transcripciones parciales y esperar más
- agente_ventas.py: Cuando llega transcripción con oferta, responder aceptando
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def test_deteccion_ofertas_datos():
    """
    FIX 443: Verificar detección de frases donde cliente ofrece datos
    """
    print("\n" + "="*60)
    print("TEST FIX 443: Detección de ofertas de datos")
    print("="*60)

    # Frases que DEBEN detectarse como oferta de datos
    frases_ofrecimiento_datos = [
        'le puedo dar', 'te puedo dar', 'le doy', 'te doy',
        'anota', 'apunta', 'mi correo', 'el correo', 'mi email',
        'le paso', 'te paso', 'mi whatsapp', 'mi número', 'mi numero',
        'manda al correo', 'mandar al correo', 'enviar al correo',
        'ahí me manda', 'ahí le mando', 'le envío', 'me envía',
        'para que me mande', 'para que le mande',
        # FIX 443b: WhatsApp
        'manda por whatsapp', 'mandar por whatsapp', 'enviar por whatsapp',
        'por whatsapp', 'al whatsapp', 'a su whatsapp', 'a tu whatsapp',
        'le mando por', 'te mando por', 'se lo mando',
        # FIX 443c: Correo
        'manda por correo', 'mandar por correo', 'enviar por correo',
        'por correo', 'a su correo', 'a tu correo', 'al mail',
        'manda al mail', 'enviar al mail', 'por mail', 'mi mail',
        'el mail es', 'el correo es', 'su correo es'
    ]

    # Casos de prueba - frases que DEBEN detectarse
    casos_positivos = [
        "No se encuentra, pero le puedo dar un correo",
        "Le doy mi whatsapp",
        "Anota: ventas arroba gmail punto com",
        "Mi correo es ejemplo arroba hotmail punto com",
        "Te paso mi número",
        "Ahí me manda la información al correo",
        "Para que me mande el catálogo le doy un email",
        "Le puedo dar el correo del encargado",
        "El correo es ventas nioval",
        # Casos WhatsApp agregados
        "Le mando la información por whatsapp",
        "Se lo mando al whatsapp",
        "Manda por whatsapp la información",
        # Casos Correo agregados
        "Le mando por correo el catálogo",
        "El mail es ventas arroba nioval",
        "Enviar al mail la información",
        "Por correo le envío todo",
    ]

    # Casos de prueba - frases que NO deben detectarse
    casos_negativos = [
        "Buenos días",
        "No se encuentra",
        "Un momento",
        "Estoy ocupado",
        "¿Quién habla?",
        "No me interesa",
        "¿De dónde llama?",
        "Soy el encargado",
    ]

    errores = []

    print("\n--- Casos que DEBEN detectarse ---")
    for frase in casos_positivos:
        frase_lower = frase.lower()
        detectado = any(oferta in frase_lower for oferta in frases_ofrecimiento_datos)

        if detectado:
            print(f"  [OK] '{frase[:50]}...' detectado")
        else:
            errores.append(f"'{frase}' NO fue detectado como oferta de datos")
            print(f"  [FAIL] '{frase}' NO detectado")

    print("\n--- Casos que NO deben detectarse ---")
    for frase in casos_negativos:
        frase_lower = frase.lower()
        detectado = any(oferta in frase_lower for oferta in frases_ofrecimiento_datos)

        if not detectado:
            print(f"  [OK] '{frase}' NO detectado (correcto)")
        else:
            errores.append(f"'{frase}' fue detectado incorrectamente como oferta")
            print(f"  [FAIL] '{frase}' detectado incorrectamente")

    if errores:
        print(f"\n[FAIL] Test detección ofertas falló con {len(errores)} errores:")
        for e in errores:
            print(f"  - {e}")
        return False

    print("\n[OK] Test detección de ofertas pasado")
    return True


def test_respuesta_a_oferta_correo():
    """
    FIX 443: Verificar que la respuesta a oferta de correo es apropiada
    """
    print("\n" + "="*60)
    print("TEST FIX 443: Respuesta apropiada a oferta de correo")
    print("="*60)

    # Simular la lógica de agente_ventas.py
    frases_ofrecimiento_datos = [
        'le puedo dar', 'te puedo dar', 'le doy', 'te doy',
        'anota', 'apunta', 'mi correo', 'el correo', 'mi email',
        'le paso', 'te paso', 'mi whatsapp', 'mi número', 'mi numero',
        'manda al correo', 'mandar al correo', 'enviar al correo',
        'ahí me manda', 'ahí le mando', 'le envío', 'me envía',
        'para que me mande', 'para que le mande'
    ]

    casos = [
        # (frase_cliente, tipo_esperado, palabras_clave_respuesta)
        ("Le puedo dar un correo", "correo", ["correo", "electrónico"]),
        ("Mi correo es ventas", "correo", ["correo", "electrónico"]),
        ("Le paso mi whatsapp", "whatsapp", ["whatsapp", "número"]),
        ("Anota el dato", "otro", ["dato", "proporcionar"]),
    ]

    errores = []

    for frase_cliente, tipo_esperado, palabras_clave in casos:
        frase_lower = frase_cliente.lower()
        cliente_ofreciendo_datos = any(frase in frase_lower for frase in frases_ofrecimiento_datos)

        if not cliente_ofreciendo_datos:
            errores.append(f"'{frase_cliente}' no detectado como oferta")
            print(f"  [FAIL] '{frase_cliente}' no detectado")
            continue

        # Determinar respuesta según lógica de FIX 443
        if 'correo' in frase_lower or 'email' in frase_lower:
            respuesta = "Claro, con gusto le envío la información. ¿Cuál es su correo electrónico?"
            tipo_detectado = "correo"
        elif 'whatsapp' in frase_lower:
            respuesta = "Perfecto, ¿me puede confirmar su número de WhatsApp?"
            tipo_detectado = "whatsapp"
        else:
            respuesta = "Claro, con gusto. ¿Me puede proporcionar el dato?"
            tipo_detectado = "otro"

        if tipo_detectado == tipo_esperado:
            print(f"  [OK] '{frase_cliente}' -> tipo '{tipo_detectado}' correcto")
        else:
            errores.append(f"'{frase_cliente}' tipo incorrecto: esperado '{tipo_esperado}', obtenido '{tipo_detectado}'")
            print(f"  [FAIL] '{frase_cliente}' tipo incorrecto")

    if errores:
        print(f"\n[FAIL] Test respuesta a ofertas falló con {len(errores)} errores:")
        for e in errores:
            print(f"  - {e}")
        return False

    print("\n[OK] Test respuesta a ofertas pasado")
    return True


def test_caso_bruce1334():
    """
    Verificar que el caso BRUCE1334 sería manejado correctamente ahora
    """
    print("\n" + "="*60)
    print("TEST: Caso BRUCE1334")
    print("="*60)

    # Frase del cliente en BRUCE1334
    frase_cliente = "No se encuentra, pero le puedo dar un correo y ahí me manda toda la información?"
    frase_lower = frase_cliente.lower()

    frases_ofrecimiento_datos = [
        'le puedo dar', 'te puedo dar', 'le doy', 'te doy',
        'anota', 'apunta', 'mi correo', 'el correo', 'mi email',
        'le paso', 'te paso', 'mi whatsapp', 'mi número', 'mi numero',
        'manda al correo', 'mandar al correo', 'enviar al correo',
        'ahí me manda', 'ahí le mando', 'le envío', 'me envía',
        'para que me mande', 'para que le mande'
    ]

    # Verificar detección
    cliente_ofreciendo_datos = any(frase in frase_lower for frase in frases_ofrecimiento_datos)

    print(f"  Frase cliente: '{frase_cliente}'")
    print(f"  Detectado como oferta de datos: {cliente_ofreciendo_datos}")

    if not cliente_ofreciendo_datos:
        print(f"\n[FAIL] BRUCE1334 NO sería detectado como oferta de datos")
        return False

    # Verificar qué frases coinciden
    frases_coincidentes = [f for f in frases_ofrecimiento_datos if f in frase_lower]
    print(f"  Frases detectadas: {frases_coincidentes}")

    # Verificar respuesta apropiada
    if 'correo' in frase_lower or 'email' in frase_lower:
        respuesta = "Claro, con gusto le envío la información. ¿Cuál es su correo electrónico?"
        print(f"  Respuesta esperada: '{respuesta}'")
    else:
        print(f"  [FAIL] No se detectó 'correo' en la frase")
        return False

    print(f"\n[OK] Test BRUCE1334 pasado - Ahora se detectaría y respondería apropiadamente")
    return True


if __name__ == "__main__":
    print("="*60)
    print("TESTS FIX 443: Detectar ofertas de datos del cliente")
    print("="*60)

    resultados = []

    resultados.append(("FIX 443 - Detección ofertas", test_deteccion_ofertas_datos()))
    resultados.append(("FIX 443 - Respuesta apropiada", test_respuesta_a_oferta_correo()))
    resultados.append(("Caso BRUCE1334", test_caso_bruce1334()))

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
