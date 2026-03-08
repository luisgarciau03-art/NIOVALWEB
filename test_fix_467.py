# -*- coding: utf-8 -*-
"""
Test para FIX 467: Fallback cuando GPT devuelve respuesta vacia

Problema: BRUCE1404 - Cliente dijo "Por el momento se encuentra ocupado"
          (transcripcion duplicada por error de Deepgram)
          GPT devolvio respuesta vacia y Bruce colgo

Solucion: Detectar respuesta vacia y generar fallback segun estado
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from enum import Enum


class EstadoConversacion(Enum):
    INICIAL = "inicial"
    ESPERANDO_SALUDO = "esperando_saludo"
    PRESENTACION = "presentacion"
    BUSCANDO_ENCARGADO = "buscando_encargado"
    ENCARGADO_NO_ESTA = "encargado_no_esta"
    PIDIENDO_WHATSAPP = "pidiendo_whatsapp"
    PIDIENDO_CORREO = "pidiendo_correo"
    ESPERANDO_TRANSFERENCIA = "esperando_transferencia"
    DICTANDO_NUMERO = "dictando_numero"


def generar_fallback_respuesta_vacia(estado: EstadoConversacion) -> str:
    """Simula la logica de FIX 467 para generar fallback"""
    if estado == EstadoConversacion.ENCARGADO_NO_ESTA:
        return "Entiendo. ¿Me podría proporcionar un número de WhatsApp o correo para enviarle información?"
    elif estado == EstadoConversacion.PIDIENDO_WHATSAPP:
        return "¿Me puede repetir el número, por favor?"
    elif estado == EstadoConversacion.ESPERANDO_TRANSFERENCIA:
        return "Claro, espero."
    else:
        return "Sí, dígame."


def test_caso_bruce1404():
    """
    FIX 467: Simular caso BRUCE1404 - Respuesta vacia con encargado ocupado
    """
    print("\n" + "="*60)
    print("TEST: Caso BRUCE1404 - Respuesta vacia con encargado ocupado")
    print("="*60)

    respuesta_gpt = ""  # GPT devolvio vacio
    estado = EstadoConversacion.ENCARGADO_NO_ESTA

    print(f"  Respuesta GPT: '{respuesta_gpt}' (vacia)")
    print(f"  Estado: {estado.value}")

    # Simular deteccion y fallback
    if not respuesta_gpt or len(respuesta_gpt.strip()) == 0:
        respuesta_final = generar_fallback_respuesta_vacia(estado)
        print(f"  Fallback generado: '{respuesta_final}'")

        if "WhatsApp" in respuesta_final or "correo" in respuesta_final:
            print(f"\n[OK] FIX 467 generaria respuesta pidiendo contacto")
            return True
        else:
            print(f"\n[FAIL] Fallback incorrecto para ENCARGADO_NO_ESTA")
            return False
    else:
        print(f"\n[FAIL] No detecto respuesta vacia")
        return False


def test_fallbacks_por_estado():
    """
    FIX 467: Verificar fallback correcto para cada estado
    """
    print("\n" + "="*60)
    print("TEST: Fallback correcto para cada estado")
    print("="*60)

    casos = [
        (EstadoConversacion.ENCARGADO_NO_ESTA, "WhatsApp"),  # Debe pedir contacto
        (EstadoConversacion.PIDIENDO_WHATSAPP, "repetir"),   # Debe pedir repeticion
        (EstadoConversacion.ESPERANDO_TRANSFERENCIA, "espero"),  # Debe decir que espera
        (EstadoConversacion.INICIAL, "dígame"),  # Respuesta neutra
    ]

    errores = []

    for estado, palabra_esperada in casos:
        fallback = generar_fallback_respuesta_vacia(estado)

        if palabra_esperada.lower() in fallback.lower():
            print(f"  [OK] {estado.value} -> '{fallback[:50]}...'")
        else:
            print(f"  [FAIL] {estado.value} -> '{fallback}' (esperaba '{palabra_esperada}')")
            errores.append(estado.value)

    if errores:
        print(f"\n[FAIL] {len(errores)} estados con fallback incorrecto")
        return False

    print(f"\n[OK] Todos los fallbacks son correctos")
    return True


def test_respuesta_no_vacia():
    """
    FIX 467: NO aplicar fallback si hay respuesta valida
    """
    print("\n" + "="*60)
    print("TEST: NO aplicar fallback si hay respuesta valida")
    print("="*60)

    respuestas_validas = [
        "Entiendo, ¿a qué hora puedo llamar?",
        "Perfecto, le envío el catálogo.",
        "Sí",
        "Claro",
    ]

    errores = []

    for respuesta in respuestas_validas:
        necesita_fallback = not respuesta or len(respuesta.strip()) == 0

        if not necesita_fallback:
            print(f"  [OK] '{respuesta[:40]}...' -> NO necesita fallback")
        else:
            print(f"  [FAIL] '{respuesta}' -> detectada como vacia incorrectamente")
            errores.append(respuesta)

    if errores:
        print(f"\n[FAIL] {len(errores)} respuestas validas detectadas como vacias")
        return False

    print(f"\n[OK] Respuestas validas NO activan fallback")
    return True


def test_respuestas_vacias():
    """
    FIX 467: Detectar diferentes formas de respuestas vacias
    """
    print("\n" + "="*60)
    print("TEST: Detectar diferentes formas de respuestas vacias")
    print("="*60)

    respuestas_vacias = [
        "",
        "   ",
        "\n",
        "\t",
        None,
    ]

    errores = []

    for respuesta in respuestas_vacias:
        necesita_fallback = not respuesta or len(str(respuesta).strip()) == 0 if respuesta is not None else True

        if necesita_fallback:
            repr_respuesta = repr(respuesta) if respuesta else "None"
            print(f"  [OK] {repr_respuesta} -> detectada como vacia")
        else:
            print(f"  [FAIL] '{respuesta}' -> NO detectada como vacia")
            errores.append(respuesta)

    if errores:
        print(f"\n[FAIL] {len(errores)} respuestas vacias NO detectadas")
        return False

    print(f"\n[OK] Todas las respuestas vacias detectadas")
    return True


if __name__ == "__main__":
    print("="*60)
    print("TESTS FIX 467: Fallback cuando GPT devuelve respuesta vacia")
    print("="*60)

    resultados = []

    resultados.append(("Caso BRUCE1404", test_caso_bruce1404()))
    resultados.append(("Fallbacks por estado", test_fallbacks_por_estado()))
    resultados.append(("Respuestas NO vacias", test_respuesta_no_vacia()))
    resultados.append(("Respuestas vacias", test_respuestas_vacias()))

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
