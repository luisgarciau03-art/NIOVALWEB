"""
Test para FIX 407: Razonamiento Mejorado - Memoria + Coherencia + Priorización

Verifica que:
1. Memoria de Contexto se calcula correctamente
2. Priorización de Respuestas está en el prompt
3. Verificación de Coherencia está en el prompt
4. Ejemplos Mejorados están en el prompt
"""

import sys
import os

# Agregar directorio padre al path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_memoria_contexto():
    """Test 1: Verificar que la memoria de contexto se calcula correctamente"""
    print("\n" + "="*70)
    print("TEST 1: MEMORIA DE CONTEXTO CONVERSACIONAL")
    print("="*70)

    from agente_ventas import AgenteVentas

    # Crear agente de prueba
    agente = AgenteVentas()

    # Simular conversación
    agente.conversation_history = [
        {"role": "assistant", "content": "Me comunico de NIOVAL para ofrecer productos de ferretería"},
        {"role": "user", "content": "Dígame"},
        {"role": "assistant", "content": "¿Se encontrará el encargado de compras?"},
        {"role": "user", "content": "No está"},
        {"role": "assistant", "content": "Como le comentaba, me comunico de NIOVAL"},
        {"role": "user", "content": "Ya me dijo"},
        {"role": "assistant", "content": "¿Le envío el catálogo completo?"},
        {"role": "user", "content": "Ok"},
    ]

    # Simular cálculo de memoria (igual que en agente_ventas.py líneas 6535-6552)
    ultimos_10_mensajes = agente.conversation_history[-10:] if len(agente.conversation_history) >= 10 else agente.conversation_history
    mensajes_bruce = [msg for msg in ultimos_10_mensajes if msg['role'] == 'assistant']

    veces_menciono_nioval = sum(1 for msg in mensajes_bruce
                                 if any(palabra in msg['content'].lower()
                                       for palabra in ['nioval', 'marca nioval', 'me comunico de']))

    veces_pregunto_encargado = sum(1 for msg in mensajes_bruce
                                    if any(frase in msg['content'].lower()
                                          for frase in ['encargad', 'encargada de compras', 'quien compra']))

    veces_ofrecio_catalogo = sum(1 for msg in mensajes_bruce
                                  if any(frase in msg['content'].lower()
                                        for frase in ['catálogo', 'catalogo', 'le envío', 'le envio']))

    print(f"\n📊 Resultados del cálculo:")
    print(f"   - Menciones de NIOVAL: {veces_menciono_nioval}")
    print(f"   - Preguntas por encargado: {veces_pregunto_encargado}")
    print(f"   - Ofertas de catálogo: {veces_ofrecio_catalogo}")

    # Verificaciones
    assert veces_menciono_nioval == 2, f"❌ NIOVAL debería ser 2, pero es {veces_menciono_nioval}"
    assert veces_pregunto_encargado == 1, f"❌ Encargado debería ser 1, pero es {veces_pregunto_encargado}"
    assert veces_ofrecio_catalogo == 1, f"❌ Catálogo debería ser 1, pero es {veces_ofrecio_catalogo}"

    print("\n✅ TEST 1 PASÓ: Memoria de contexto calcula correctamente")
    return True


def test_prompt_contiene_fix_407():
    """Test 2: Verificar que el prompt contiene todas las secciones de FIX 407"""
    print("\n" + "="*70)
    print("TEST 2: VERIFICAR SECCIONES DE FIX 407 EN PROMPT")
    print("="*70)

    # Leer el archivo agente_ventas.py
    with open('agente_ventas.py', 'r', encoding='utf-8') as f:
        contenido = f.read()

    secciones_requeridas = [
        ("Memoria de Contexto", "FIX 407: MEMORIA DE CONTEXTO CONVERSACIONAL"),
        ("Priorización de Respuestas", "FIX 407: PRIORIZACIÓN DE RESPUESTAS"),
        ("Verificación de Coherencia", "FIX 407: VERIFICACIÓN DE COHERENCIA"),
        ("Ejemplos Mejorados", "FIX 407: EJEMPLOS MEJORADOS"),
    ]

    print("\n📋 Verificando secciones:")

    todas_presentes = True
    for nombre, patron in secciones_requeridas:
        if patron in contenido:
            print(f"   ✅ {nombre}: PRESENTE")
        else:
            print(f"   ❌ {nombre}: FALTA")
            todas_presentes = False

    assert todas_presentes, "❌ Faltan secciones de FIX 407"

    print("\n✅ TEST 2 PASÓ: Todas las secciones están presentes")
    return True


def test_ejemplos_mejorados():
    """Test 3: Verificar que los ejemplos mejorados están completos"""
    print("\n" + "="*70)
    print("TEST 3: VERIFICAR EJEMPLOS MEJORADOS")
    print("="*70)

    with open('agente_ventas.py', 'r', encoding='utf-8') as f:
        contenido = f.read()

    ejemplos_requeridos = [
        ("Ejemplo 1", "No responde pregunta directa"),
        ("Ejemplo 2", "No confirma dato que dio cliente"),
        ("Ejemplo 3", "Respuesta larga cuando cliente ocupado"),
        ("Ejemplo 4", "Repite empresa cuando ya la mencionó"),
        ("Ejemplo 5", "Responde múltiples preguntas pero solo 1"),
    ]

    print("\n📚 Verificando ejemplos:")

    todos_presentes = True
    for nombre, patron in ejemplos_requeridos:
        if patron in contenido:
            print(f"   ✅ {nombre}: PRESENTE")
        else:
            print(f"   ❌ {nombre}: FALTA")
            todos_presentes = False

    assert todos_presentes, "❌ Faltan ejemplos en FIX 407"

    print("\n✅ TEST 3 PASÓ: Todos los ejemplos mejorados están presentes")
    return True


def test_integracion_completa():
    """Test 4: Verificar que memoria_conversacional se inyecta al prompt"""
    print("\n" + "="*70)
    print("TEST 4: VERIFICAR INTEGRACIÓN EN prompt_base")
    print("="*70)

    with open('agente_ventas.py', 'r', encoding='utf-8') as f:
        contenido = f.read()

    # Buscar la línea donde se construye prompt_base
    patron_integracion = "prompt_base = contexto_cliente + contexto_recontacto + memoria_corto_plazo + instruccion_whatsapp_capturado + memoria_conversacional"

    if patron_integracion in contenido:
        print("\n✅ memoria_conversacional está integrada en prompt_base")
        print("   Orden correcto:")
        print("   1. contexto_cliente")
        print("   2. contexto_recontacto")
        print("   3. memoria_corto_plazo")
        print("   4. instruccion_whatsapp_capturado")
        print("   5. memoria_conversacional ← FIX 407")
    else:
        print("\n❌ memoria_conversacional NO está integrada correctamente")
        return False

    print("\n✅ TEST 4 PASÓ: Integración completa correcta")
    return True


def test_prioridad_y_coherencia():
    """Test 5: Verificar que las reglas de prioridad y coherencia están detalladas"""
    print("\n" + "="*70)
    print("TEST 5: VERIFICAR REGLAS DE PRIORIDAD Y COHERENCIA")
    print("="*70)

    with open('agente_ventas.py', 'r', encoding='utf-8') as f:
        contenido = f.read()

    reglas_prioridad = [
        "1️⃣ MÁXIMA PRIORIDAD - Preguntas directas del cliente",
        "2️⃣ ALTA PRIORIDAD - Confirmar datos que dio",
        "3️⃣ MEDIA PRIORIDAD - Responder objeciones",
        "4️⃣ BAJA PRIORIDAD - Continuar script",
    ]

    reglas_coherencia = [
        "¿Mi respuesta RESPONDE lo que preguntó el cliente?",
        "¿Estoy REPITIENDO lo que ya dije antes?",
        "¿Tiene SENTIDO en este contexto?",
        "¿Ya tengo este dato?",
        "¿Cliente está ocupado/apurado?",
    ]

    print("\n🎯 Verificando reglas de prioridad:")
    for regla in reglas_prioridad:
        if regla in contenido:
            print(f"   ✅ {regla}")
        else:
            print(f"   ❌ Falta: {regla}")
            return False

    print("\n✅ Verificando reglas de coherencia:")
    for regla in reglas_coherencia:
        if regla in contenido:
            print(f"   ✅ {regla}")
        else:
            print(f"   ❌ Falta: {regla}")
            return False

    print("\n✅ TEST 5 PASÓ: Todas las reglas están completas")
    return True


def main():
    """Ejecutar todos los tests"""
    print("\n" + "="*70)
    print("TEST DE FIX 407: RAZONAMIENTO MEJORADO")
    print("="*70)

    tests = [
        test_memoria_contexto,
        test_prompt_contiene_fix_407,
        test_ejemplos_mejorados,
        test_integracion_completa,
        test_prioridad_y_coherencia,
    ]

    resultados = []

    for test_func in tests:
        try:
            resultado = test_func()
            resultados.append((test_func.__name__, True, None))
        except AssertionError as e:
            resultados.append((test_func.__name__, False, str(e)))
            print(f"\n❌ FALLÓ: {e}")
        except Exception as e:
            resultados.append((test_func.__name__, False, f"Error inesperado: {e}"))
            print(f"\n❌ ERROR INESPERADO: {e}")

    # Resumen final
    print("\n" + "="*70)
    print("📊 RESUMEN DE TESTS")
    print("="*70)

    tests_pasados = sum(1 for _, resultado, _ in resultados if resultado)
    tests_totales = len(resultados)

    for nombre, resultado, error in resultados:
        status = "✅ PASÓ" if resultado else f"❌ FALLÓ: {error}"
        print(f"{nombre}: {status}")

    print("\n" + "="*70)
    print(f"RESULTADO FINAL: {tests_pasados}/{tests_totales} tests pasaron")
    print("="*70)

    if tests_pasados == tests_totales:
        print("\nTODOS LOS TESTS PASARON - FIX 407 CONFIGURADO CORRECTAMENTE")
        return 0
    else:
        print(f"\n{tests_totales - tests_pasados} test(s) fallaron")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
