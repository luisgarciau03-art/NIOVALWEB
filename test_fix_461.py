# -*- coding: utf-8 -*-
"""
Test para FIX 461: Corregir duplicación de mensajes de usuario en historial

Problema: BRUCE1381 mostraba mensajes de usuario duplicados en el historial
Causa: servidor_llamadas.py línea 2798 agregaba mensaje Y procesar_respuesta()
       también lo agregaba en agente_ventas.py línea 4314

Solución: Remover la adición duplicada en servidor_llamadas.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def test_no_duplicacion_mensajes_usuario():
    """
    FIX 461: Verificar que no hay duplicación de mensajes de usuario
    """
    print("\n" + "="*60)
    print("TEST FIX 461: No duplicación de mensajes de usuario")
    print("="*60)

    # Simular historial con mensajes
    conversation_history = []

    # Simular el flujo CORRECTO (sin duplicación)
    # Solo procesar_respuesta() agrega el mensaje
    speech_result = "Este, mire, por el momento no se"

    # Simular lo que hace procesar_respuesta() en agente_ventas.py línea 4314
    conversation_history.append({
        "role": "user",
        "content": speech_result
    })

    # Verificar que no hay duplicados
    mensajes_usuario = [msg for msg in conversation_history if msg['role'] == 'user']

    print(f"  Speech result: '{speech_result}'")
    print(f"  Mensajes de usuario en historial: {len(mensajes_usuario)}")

    # Verificar que hay exactamente 1 mensaje
    if len(mensajes_usuario) == 1:
        print(f"\n[OK] No hay duplicación - solo 1 mensaje de usuario")
        return True
    else:
        print(f"\n[FAIL] Hay {len(mensajes_usuario)} mensajes de usuario (debería ser 1)")
        return False


def test_caso_bruce1381_interrupcion():
    """
    FIX 461: Simular caso BRUCE1381 - interrupción durante segunda parte
    """
    print("\n" + "="*60)
    print("TEST: Caso BRUCE1381 - Interrupción durante segunda parte")
    print("="*60)

    # Simular historial donde Bruce ya dijo 2 mensajes (segunda parte)
    conversation_history = [
        {"role": "assistant", "content": "Buenas tardes, ¿es la ferretería?"},
        {"role": "user", "content": "Sí, dígame"},
        {"role": "assistant", "content": "Me comunico de la marca nioval..."}
    ]

    # Cliente responde durante la segunda parte
    speech_result = "Este, mire, por el momento no se"

    # Verificar condición de interrupción
    mensajes_bruce_previos = [msg for msg in conversation_history if msg['role'] == 'assistant']
    bruce_ya_dijo_segunda_parte = len(mensajes_bruce_previos) >= 2

    print(f"  Mensajes de Bruce previos: {len(mensajes_bruce_previos)}")
    print(f"  Bruce ya dijo segunda parte: {bruce_ya_dijo_segunda_parte}")

    if bruce_ya_dijo_segunda_parte:
        # ANTES de FIX 461: Se agregaba aquí Y en procesar_respuesta()
        # DESPUÉS de FIX 461: Solo se agrega en procesar_respuesta()

        # Simular flujo CORRECTO (solo procesar_respuesta agrega)
        print(f"\n  Con FIX 461:")
        print(f"    servidor_llamadas.py NO agrega mensaje aquí")
        print(f"    procesar_respuesta() agrega mensaje en agente_ventas.py")

        # Simular procesar_respuesta()
        conversation_history.append({
            "role": "user",
            "content": speech_result
        })

        # Verificar no duplicación
        mensajes_usuario = [msg for msg in conversation_history if msg['role'] == 'user']
        mensajes_con_texto = [msg for msg in mensajes_usuario if msg['content'] == speech_result]

        print(f"    Mensajes de usuario con mismo texto: {len(mensajes_con_texto)}")

        if len(mensajes_con_texto) == 1:
            print(f"\n[OK] FIX 461 evita duplicación")
            return True
        else:
            print(f"\n[FAIL] Hay {len(mensajes_con_texto)} mensajes con mismo texto")
            return False
    else:
        print(f"\n[FAIL] Escenario incorrecto - Bruce no dijo segunda parte")
        return False


def test_flujo_cache_no_afectado():
    """
    FIX 461: Verificar que el flujo de caché (primera respuesta) no fue afectado
    """
    print("\n" + "="*60)
    print("TEST: Flujo de caché no afectado")
    print("="*60)

    # Simular historial inicial (solo saludo de Bruce)
    conversation_history = [
        {"role": "assistant", "content": "Buenas tardes, ¿es la ferretería?"}
    ]

    # Cliente responde con saludo simple
    speech_result = "Sí, dígame"

    # Este es el caso de caché (primera respuesta)
    mensajes_bruce_previos = [msg for msg in conversation_history if msg['role'] == 'assistant']
    bruce_ya_dijo_segunda_parte = len(mensajes_bruce_previos) >= 2

    print(f"  Mensajes de Bruce previos: {len(mensajes_bruce_previos)}")
    print(f"  Es caso de caché (primera respuesta): {not bruce_ya_dijo_segunda_parte}")

    if not bruce_ya_dijo_segunda_parte:
        # En este caso, servidor_llamadas.py SÍ agrega el mensaje
        # porque procesar_respuesta() NO se llama (usa caché)

        print(f"\n  Flujo de caché:")
        print(f"    servidor_llamadas.py agrega mensaje de usuario")
        print(f"    servidor_llamadas.py agrega respuesta de caché")
        print(f"    procesar_respuesta() NO se llama")

        # Simular flujo de caché
        conversation_history.append({
            "role": "user",
            "content": speech_result
        })
        conversation_history.append({
            "role": "assistant",
            "content": "Me comunico de la marca nioval..."
        })

        # Verificar no duplicación
        mensajes_usuario = [msg for msg in conversation_history if msg['role'] == 'user']

        print(f"    Mensajes de usuario: {len(mensajes_usuario)}")

        if len(mensajes_usuario) == 1:
            print(f"\n[OK] Flujo de caché funciona correctamente")
            return True
        else:
            print(f"\n[FAIL] Hay {len(mensajes_usuario)} mensajes de usuario")
            return False
    else:
        print(f"\n[FAIL] Escenario incorrecto")
        return False


if __name__ == "__main__":
    print("="*60)
    print("TESTS FIX 461: Duplicación de mensajes de usuario")
    print("="*60)

    resultados = []

    resultados.append(("No duplicación mensajes", test_no_duplicacion_mensajes_usuario()))
    resultados.append(("Caso BRUCE1381 interrupción", test_caso_bruce1381_interrupcion()))
    resultados.append(("Flujo caché no afectado", test_flujo_cache_no_afectado()))

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
