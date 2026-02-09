"""
Test Simple para FIX 407 - Sin importar agente_ventas.py
Verifica que todas las secciones de FIX 407 están presentes en el código
"""

import re

def test_fix_407():
    print("="*70)
    print("TEST DE FIX 407: RAZONAMIENTO MEJORADO")
    print("="*70)

    # Leer el archivo
    with open('agente_ventas.py', 'r', encoding='utf-8') as f:
        contenido = f.read()

    print("\n[1/5] Verificando Memoria de Contexto...")
    tests_pasados = 0
    tests_totales = 5

    # Test 1: Memoria de Contexto
    if all(patron in contenido for patron in [
        "FIX 407: MEMORIA DE CONTEXTO CONVERSACIONAL",
        "veces_menciono_nioval",
        "veces_pregunto_encargado",
        "veces_ofrecio_catalogo",
        "ultimos_10_mensajes",
        "REGLA ANTI-REPETICION"
    ]):
        print("   PASS: Memoria de Contexto implementada correctamente")
        tests_pasados += 1
    else:
        print("   FAIL: Falta código de Memoria de Contexto")

    # Test 2: Integración en prompt_base
    print("\n[2/5] Verificando integración en prompt_base...")
    if "memoria_conversacional" in contenido and \
       "prompt_base = contexto_cliente + contexto_recontacto + memoria_corto_plazo + instruccion_whatsapp_capturado + memoria_conversacional" in contenido:
        print("   PASS: memoria_conversacional integrada en prompt_base")
        tests_pasados += 1
    else:
        print("   FAIL: memoria_conversacional NO está integrada")

    # Test 3: Priorización de Respuestas
    print("\n[3/5] Verificando Priorización de Respuestas...")
    if all(patron in contenido for patron in [
        "FIX 407: PRIORIZACION DE RESPUESTAS",
        "MAXIMA PRIORIDAD - Preguntas directas del cliente",
        "ALTA PRIORIDAD - Confirmar datos que dio",
        "MEDIA PRIORIDAD - Responder objeciones",
        "BAJA PRIORIDAD - Continuar script"
    ]):
        print("   PASS: Priorización de Respuestas implementada")
        tests_pasados += 1
    else:
        print("   FAIL: Falta Priorización de Respuestas")

    # Test 4: Verificación de Coherencia
    print("\n[4/5] Verificando Verificación de Coherencia...")
    if all(patron in contenido for patron in [
        "FIX 407: VERIFICACION DE COHERENCIA",
        "Mi respuesta RESPONDE lo que pregunto el cliente",
        "Estoy REPITIENDO lo que ya dije antes",
        "Tiene SENTIDO en este contexto",
        "Ya tengo este dato",
        "Cliente esta ocupado/apurado"
    ]):
        print("   PASS: Verificación de Coherencia implementada")
        tests_pasados += 1
    else:
        print("   FAIL: Falta Verificación de Coherencia")

    # Test 5: Ejemplos Mejorados
    print("\n[5/5] Verificando Ejemplos Mejorados...")
    ejemplos_encontrados = 0
    ejemplos_requeridos = [
        "No responde pregunta directa",
        "No confirma dato que dio cliente",
        "Respuesta larga cuando cliente ocupado",
        "Repite empresa cuando ya la menciono",
        "Responde multiples preguntas pero solo 1"
    ]

    for ejemplo in ejemplos_requeridos:
        if ejemplo in contenido:
            ejemplos_encontrados += 1

    if ejemplos_encontrados >= 5:
        print(f"   PASS: {ejemplos_encontrados}/5 ejemplos mejorados presentes")
        tests_pasados += 1
    else:
        print(f"   FAIL: Solo {ejemplos_encontrados}/5 ejemplos presentes")

    # Resumen
    print("\n" + "="*70)
    print(f"RESULTADO: {tests_pasados}/{tests_totales} tests pasaron")
    print("="*70)

    if tests_pasados == tests_totales:
        print("\nTODOS LOS TESTS PASARON")
        print("FIX 407 CONFIGURADO CORRECTAMENTE")
        return 0
    else:
        print(f"\n{tests_totales - tests_pasados} test(s) fallaron")
        print("Revisar implementacion de FIX 407")
        return 1


if __name__ == "__main__":
    exit(test_fix_407())
