# -*- coding: utf-8 -*-
"""
Test para FIX 464: No decir "Si digame" cuando cliente pregunta que vende

Problema: BRUCE1390 - Cliente pregunto "Que mercancia vende?"
          GPT respondio correctamente: "Manejamos productos de ferreteria..."
          Pero FIX 444 cambio la respuesta a "Si, digame"

Solucion: Detectar preguntas sobre productos y NO cambiar la respuesta de GPT
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def debe_dejar_respuesta_gpt(ultimo_cliente: str) -> bool:
    """Simula la logica de FIX 464"""
    ultimo_cliente_lower = ultimo_cliente.lower()

    # FIX 464: Detectar si cliente pregunta QUE VENDE
    cliente_pregunta_que_vende = any(frase in ultimo_cliente_lower for frase in [
        'que vende', 'que mercancia', 'que productos', 'que manejan',
        'que es lo que vende', 'a que se dedica', 'de que se trata', 'que ofrece'
    ])

    return cliente_pregunta_que_vende


def test_caso_bruce1390():
    """
    FIX 464: Simular caso BRUCE1390 - Pregunta sobre productos
    """
    print("\n" + "="*60)
    print("TEST: Caso BRUCE1390 - Pregunta sobre productos")
    print("="*60)

    mensaje = "Es en 3 pesos. Que mercancia vende, disculpa?"

    print(f"  Cliente dijo: '{mensaje}'")

    dejar_gpt = debe_dejar_respuesta_gpt(mensaje)

    print(f"  Dejar respuesta de GPT: {dejar_gpt}")

    if dejar_gpt:
        print(f"\n[OK] FIX 464 dejaria respuesta de GPT (Manejamos productos...)")
        return True
    else:
        print(f"\n[FAIL] FIX 464 cambiaria a 'Si, digame' (incorrecto)")
        return False


def test_preguntas_sobre_productos():
    """
    FIX 464: Varias preguntas sobre productos
    """
    print("\n" + "="*60)
    print("TEST: Varias preguntas sobre productos")
    print("="*60)

    casos_pregunta_productos = [
        "Que vende?",
        "Que mercancia manejan?",
        "Que productos tienen?",
        "Que es lo que vende nioval?",
        "A que se dedican?",
        "De que se trata su empresa?",
        "Que es lo que ofrecen?",
    ]

    errores = []

    for pregunta in casos_pregunta_productos:
        dejar_gpt = debe_dejar_respuesta_gpt(pregunta)

        if dejar_gpt:
            print(f"  [OK] '{pregunta}' -> dejar GPT")
        else:
            print(f"  [FAIL] '{pregunta}' -> NO dejar GPT")
            errores.append(pregunta)

    if errores:
        print(f"\n[FAIL] {len(errores)} preguntas NO detectadas")
        return False

    print(f"\n[OK] Todas las preguntas de productos detectadas")
    return True


def test_preguntas_genericas():
    """
    FIX 464: Preguntas genericas SI deben cambiar a 'Si digame'
    """
    print("\n" + "="*60)
    print("TEST: Preguntas genericas SI deben cambiar")
    print("="*60)

    casos_pregunta_generica = [
        "Digame?",
        "Que paso?",
        "Bueno?",
        "Si?",
        "Es para la ferreteria?",
    ]

    todos_no_productos = True

    for pregunta in casos_pregunta_generica:
        dejar_gpt = debe_dejar_respuesta_gpt(pregunta)

        if not dejar_gpt:
            print(f"  [OK] '{pregunta}' -> cambiar a 'Si, digame'")
        else:
            print(f"  [FAIL] '{pregunta}' -> detectado como pregunta de productos")
            todos_no_productos = False

    if todos_no_productos:
        print(f"\n[OK] Preguntas genericas cambian correctamente")
        return True
    else:
        print(f"\n[FAIL] Algunas preguntas genericas no cambian")
        return False


if __name__ == "__main__":
    print("="*60)
    print("TESTS FIX 464: No decir 'Si digame' para preguntas de productos")
    print("="*60)

    resultados = []

    resultados.append(("Caso BRUCE1390", test_caso_bruce1390()))
    resultados.append(("Preguntas sobre productos", test_preguntas_sobre_productos()))
    resultados.append(("Preguntas genericas", test_preguntas_genericas()))

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
