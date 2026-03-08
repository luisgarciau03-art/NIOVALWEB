# -*- coding: utf-8 -*-
"""
Test para FIX 466: Permitir presentacion cuando cliente pregunta de donde llaman

Problema: BRUCE1405 - Cliente pregunto "¿De donde me habla?"
          GPT respondio correctamente: "Me comunico de la marca nioval..."
          Pero FIX 228/236/240 lo cambio a "Si, digame" porque detecto repeticion

Solucion: Detectar preguntas sobre ORIGEN de llamada y NO filtrar la presentacion
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def cliente_pregunta_origen(texto: str) -> bool:
    """Simula la logica de FIX 466 para detectar preguntas sobre origen"""
    texto_lower = texto.lower()

    frases_origen = [
        'de dónde', 'de donde', 'quién habla', 'quien habla',
        'quién llama', 'quien llama', 'quién es', 'quien es',
        'de qué empresa', 'de que empresa', 'de qué compañía', 'de que compania',
        'de parte de quién', 'de parte de quien', 'con quién hablo', 'con quien hablo'
    ]

    return any(frase in texto_lower for frase in frases_origen)


def test_caso_bruce1405():
    """
    FIX 466: Simular caso BRUCE1405 - Pregunta de donde llaman
    """
    print("\n" + "="*60)
    print("TEST: Caso BRUCE1405 - Pregunta de donde llaman")
    print("="*60)

    mensaje = "¿De dónde me habla la esposa?"

    print(f"  Cliente dijo: '{mensaje}'")

    pregunta_origen = cliente_pregunta_origen(mensaje)

    print(f"  Pregunta origen: {pregunta_origen}")

    if pregunta_origen:
        print(f"\n[OK] FIX 466 detectaria pregunta de origen - NO cambiaria respuesta")
        return True
    else:
        print(f"\n[FAIL] FIX 466 NO detectaria pregunta de origen")
        return False


def test_preguntas_origen():
    """
    FIX 466: Varias formas de preguntar de donde llaman
    """
    print("\n" + "="*60)
    print("TEST: Varias preguntas sobre origen de llamada")
    print("="*60)

    casos_origen = [
        "¿De dónde me habla?",
        "¿De donde llaman?",
        "¿Quién habla?",
        "¿Quien es?",
        "¿De qué empresa me llama?",
        "¿De parte de quien?",
        "¿Con quien hablo?",
        "Perdón, ¿de dónde me dijo que llamaba?",
        "¿De qué compañía es?",
    ]

    errores = []

    for pregunta in casos_origen:
        es_origen = cliente_pregunta_origen(pregunta)

        if es_origen:
            print(f"  [OK] '{pregunta}' -> pregunta origen")
        else:
            print(f"  [FAIL] '{pregunta}' -> NO detectada")
            errores.append(pregunta)

    if errores:
        print(f"\n[FAIL] {len(errores)} preguntas de origen NO detectadas")
        return False

    print(f"\n[OK] Todas las preguntas de origen detectadas")
    return True


def test_preguntas_no_origen():
    """
    FIX 466: Preguntas que NO son sobre el origen (deben seguir filtrando)
    """
    print("\n" + "="*60)
    print("TEST: Preguntas que NO son sobre origen")
    print("="*60)

    casos_no_origen = [
        "Buenas tardes",
        "Sí, dígame",
        "¿Qué productos venden?",
        "¿Cuánto cuesta?",
        "No me interesa, gracias",
        "¿Qué día pasa?",
        "El encargado no está",
    ]

    errores = []

    for pregunta in casos_no_origen:
        es_origen = cliente_pregunta_origen(pregunta)

        if not es_origen:
            print(f"  [OK] '{pregunta}' -> NO es pregunta origen")
        else:
            print(f"  [FAIL] '{pregunta}' -> detectada como origen (falso positivo)")
            errores.append(pregunta)

    if errores:
        print(f"\n[FAIL] {len(errores)} falsos positivos")
        return False

    print(f"\n[OK] Sin falsos positivos")
    return True


def test_simulacion_filtro():
    """
    FIX 466: Simular el comportamiento completo del filtro
    """
    print("\n" + "="*60)
    print("TEST: Simulacion del filtro completo")
    print("="*60)

    # Simular: Bruce ya dijo "Me comunico de la marca nioval..."
    # GPT responde de nuevo con presentacion
    # Verificar si el filtro se aplica o no segun pregunta del cliente

    casos = [
        # (pregunta_cliente, respuesta_gpt, debe_filtrar)
        ("¿De dónde me habla?", "Me comunico de la marca nioval...", False),  # NO filtrar
        ("Buenas tardes", "Me comunico de la marca nioval...", True),  # SI filtrar
        ("¿Quién llama?", "Me comunico de la marca nioval...", False),  # NO filtrar
        ("Sí dígame", "Me comunico de la marca nioval...", True),  # SI filtrar
    ]

    errores = []

    for pregunta, respuesta, debe_filtrar in casos:
        es_origen = cliente_pregunta_origen(pregunta)
        filtrar = not es_origen  # Si NO pregunta origen, se filtra

        if filtrar == debe_filtrar:
            accion = "filtrar" if filtrar else "NO filtrar"
            print(f"  [OK] '{pregunta[:30]}...' -> {accion}")
        else:
            accion_real = "filtrar" if filtrar else "NO filtrar"
            accion_esperada = "filtrar" if debe_filtrar else "NO filtrar"
            print(f"  [FAIL] '{pregunta}' -> {accion_real} (esperado: {accion_esperada})")
            errores.append(pregunta)

    if errores:
        print(f"\n[FAIL] {len(errores)} casos fallaron")
        return False

    print(f"\n[OK] Simulacion del filtro correcta")
    return True


if __name__ == "__main__":
    print("="*60)
    print("TESTS FIX 466: Permitir presentacion cuando preguntan origen")
    print("="*60)

    resultados = []

    resultados.append(("Caso BRUCE1405", test_caso_bruce1405()))
    resultados.append(("Preguntas sobre origen", test_preguntas_origen()))
    resultados.append(("Preguntas NO origen", test_preguntas_no_origen()))
    resultados.append(("Simulacion filtro", test_simulacion_filtro()))

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
