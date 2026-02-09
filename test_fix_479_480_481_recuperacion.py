"""
TEST FIX 479, 480, 481: Validar sistema de recuperación de errores

OBJETIVO:
- FIX 479: Validar que respuestas vacías se bloquean
- FIX 480: Validar detección de repeticiones del cliente
- FIX 481: Validar recuperación de errores
"""

import sys
import os

# Agregar path para importar AgenteVentas
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from agente_ventas import AgenteVentas

def test_validacion_respuestas_vacias():
    """FIX 479: Validar que respuestas vacías se bloquean"""

    print("\n" + "="*60)
    print("TEST FIX 479: VALIDACION DE RESPUESTAS VACIAS")
    print("="*60)

    agente = AgenteVentas()

    casos_prueba = [
        {
            "nombre": "Respuesta vacia (string vacio)",
            "entrada": "",
            "debe_bloquear": True
        },
        {
            "nombre": "Respuesta solo espacios",
            "entrada": "   ",
            "debe_bloquear": True
        },
        {
            "nombre": "Respuesta muy corta (2 chars)",
            "entrada": "Ok",
            "debe_bloquear": True
        },
        {
            "nombre": "Respuesta valida",
            "entrada": "Perfecto, entonces le envío el catálogo",
            "debe_bloquear": False
        },
    ]

    tests_passed = 0
    tests_total = len(casos_prueba)

    for i, caso in enumerate(casos_prueba, 1):
        print(f"\nTEST {i}: {caso['nombre']}")
        print(f"  Entrada: '{caso['entrada']}'")

        # Aplicar filtro
        resultado = agente._filtrar_respuesta_post_gpt(caso['entrada'])

        # Validar
        fue_bloqueada = resultado != caso['entrada'] and len(resultado) > 10

        if fue_bloqueada == caso['debe_bloquear']:
            print(f"  PASS: {'Bloqueada' if fue_bloqueada else 'No bloqueada'} correctamente")
            if fue_bloqueada:
                print(f"    Fallback: '{resultado[:60]}...'")
            tests_passed += 1
        else:
            print(f"  FAIL: Esperado bloqueo={caso['debe_bloquear']}, obtenido={fue_bloqueada}")

    print(f"\nRESULTADO FIX 479: {tests_passed}/{tests_total} tests pasados")
    return tests_passed == tests_total


def test_deteccion_repeticiones():
    """FIX 480: Validar detección de repeticiones del cliente"""

    print("\n" + "="*60)
    print("TEST FIX 480: DETECCION DE REPETICIONES")
    print("="*60)

    agente = AgenteVentas()

    # Simular conversación con repeticiones
    print("\nSimulando conversacion con cliente que repite pregunta:")

    # Mensaje 1: Cliente pregunta
    agente.conversation_history.append({
        "role": "user",
        "content": "¿De donde habla?"
    })
    agente.conversation_history.append({
        "role": "assistant",
        "content": "Me comunico de la marca NIOVAL"
    })

    # Mensaje 2: Cliente repite (primera vez)
    agente.conversation_history.append({
        "role": "user",
        "content": "¿De donde habla?"
    })

    es_repeticion, pregunta, veces = agente._cliente_repite_pregunta("¿De donde habla?")

    print(f"\n  Pregunta: '¿De donde habla?'")
    print(f"  Repeticion detectada: {es_repeticion}")
    print(f"  Veces repetida: {veces}")

    test1_pass = es_repeticion and veces == 2

    # Mensaje 3: Cliente repite (segunda vez)
    agente.conversation_history.append({
        "role": "assistant",
        "content": "Estamos en Guadalajara, Jalisco"
    })
    agente.conversation_history.append({
        "role": "user",
        "content": "¿De donde hablan?"
    })

    es_repeticion2, pregunta2, veces2 = agente._cliente_repite_pregunta("¿De donde hablan?")

    print(f"\n  Pregunta similar: '¿De donde hablan?'")
    print(f"  Repeticion detectada: {es_repeticion2}")
    print(f"  Veces repetida: {veces2}")

    test2_pass = es_repeticion2 and veces2 >= 2

    # Test respuesta adaptativa
    if es_repeticion2:
        respuesta = agente._generar_respuesta_para_repeticion(pregunta2, veces2)
        print(f"\n  Respuesta adaptativa generada:")
        print(f"    '{respuesta[:80]}...'")
        test3_pass = len(respuesta) > 0 and ("Guadalajara" in respuesta or "prefiere" in respuesta.lower())
    else:
        test3_pass = False

    tests_passed = sum([test1_pass, test2_pass, test3_pass])
    print(f"\nRESULTADO FIX 480: {tests_passed}/3 tests pasados")

    return tests_passed == 3


def test_recuperacion_errores():
    """FIX 481: Validar recuperación de errores"""

    print("\n" + "="*60)
    print("TEST FIX 481: RECUPERACION DE ERRORES")
    print("="*60)

    agente = AgenteVentas()

    casos_prueba = [
        {
            "tipo": "CONFUSION",
            "entrada": "No entendi",
            "debe_detectar": True
        },
        {
            "tipo": "CONFUSION",
            "entrada": "¿Como dice?",
            "debe_detectar": True
        },
        {
            "tipo": "FRUSTRACION",
            "entrada": "Ya le dije que no esta",
            "debe_detectar": True
        },
        {
            "tipo": "CORRECCION",
            "entrada": "No, le dije que era otro numero",
            "debe_detectar": True
        },
        {
            "tipo": "NORMAL",
            "entrada": "Si, estoy interesado",
            "debe_detectar": False
        },
    ]

    tests_passed = 0
    tests_total = len(casos_prueba)

    for i, caso in enumerate(casos_prueba, 1):
        print(f"\nTEST {i}: {caso['tipo']}")
        print(f"  Entrada: '{caso['entrada']}'")

        necesita_recuperacion, tipo_error, contexto = agente._detectar_error_necesita_recuperacion(caso['entrada'])

        if necesita_recuperacion == caso['debe_detectar']:
            print(f"  PASS: {'Detectado' if necesita_recuperacion else 'No detectado'} correctamente")
            if necesita_recuperacion:
                print(f"    Tipo error: {tipo_error}")
                # Generar respuesta de recuperación
                respuesta = agente._generar_respuesta_recuperacion_error(tipo_error, contexto)
                print(f"    Respuesta recuperacion: '{respuesta[:60]}...'")
            tests_passed += 1
        else:
            print(f"  FAIL: Esperado deteccion={caso['debe_detectar']}, obtenido={necesita_recuperacion}")

    print(f"\nRESULTADO FIX 481: {tests_passed}/{tests_total} tests pasados")
    return tests_passed == tests_total


def main():
    """Ejecutar todos los tests de recuperación de errores"""

    print("\n" + "="*70)
    print("SUITE DE TESTS: FIX 479 + 480 + 481 (RECUPERACION DE ERRORES)")
    print("="*70)

    resultados = {
        "FIX 479 (Respuestas vacias)": test_validacion_respuestas_vacias(),
        "FIX 480 (Repeticiones)": test_deteccion_repeticiones(),
        "FIX 481 (Recuperacion errores)": test_recuperacion_errores(),
    }

    # Resumen final
    print("\n" + "="*70)
    print("RESUMEN FINAL")
    print("="*70)

    for nombre, resultado in resultados.items():
        estado = "PASS" if resultado else "FAIL"
        print(f"  {nombre}: {estado}")

    todos_pasaron = all(resultados.values())

    print("\n" + "="*70)
    if todos_pasaron:
        print("EXITO: Todos los tests de recuperacion pasaron")
    else:
        print("FALLO: Algunos tests fallaron")
    print("="*70)

    return todos_pasaron


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
