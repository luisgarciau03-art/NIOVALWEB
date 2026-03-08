"""
FIX 394: Test de detección mejorada de repeticiones y "Perfecto" inapropiado
Simula el caso BRUCE1105 donde Bruce repitió 4 veces la misma pregunta
"""

import sys
import os
import io

# Fix encoding issues en Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Agregar ruta del proyecto
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from agente_ventas import AgenteVentas, EstadoConversacion


def test_caso_bruce1105():
    """
    Simula el caso real BRUCE1105:

    1. Cliente: "¿En qué le puedo apoyar?" → Bruce debió presentarse
    2. Cliente: "¿En qué le puedo apoyar?" (OTRA VEZ) → Bruce repitió ❌
    3. Cliente: "No, está marcando a mostrador. ¿En qué le apoyo?" → Bruce repitió ❌
    4. Cliente: "No, le digo que en qué le apoyo." → Bruce repitió ❌
    5. Bruce repitió "Perfecto. ¿Se encontrará el encargado?" 4 VECES

    Con FIX 394:
    - Detecta "¿En qué le puedo apoyar?" y se presenta inmediatamente
    - Detecta repeticiones en últimas 4 respuestas
    - Elimina "Perfecto" cuando cliente hace pregunta
    """

    print("\n" + "=" * 80)
    print("🧪 TEST FIX 394: Repeticiones múltiples y 'Perfecto' inapropiado (Caso BRUCE1105)")
    print("=" * 80)

    # Crear agente sin dependencias externas
    agente = AgenteVentas(
        contacto_info={
            'nombre_negocio': 'Ferretería Test',
            'telefono': '+525511112222'
        },
        whatsapp_validator=None
    )

    # Iniciar conversación
    print("\n📞 INICIANDO CONVERSACIÓN")
    saludo = agente.iniciar_conversacion()
    print(f"Bruce: {saludo}")

    # ============================================================
    # TEST 1: Cliente dice "¿En qué le puedo apoyar?"
    # ============================================================
    print("\n" + "=" * 80)
    print("TEST 1: Cliente dice '¿En qué le puedo apoyar?' - Bruce debe presentarse INMEDIATAMENTE")
    print("=" * 80)

    mensaje1 = "Buen día. ¿En qué le puedo apoyar?"
    print(f"\n👤 Cliente: {mensaje1}")

    respuesta1 = agente.procesar_respuesta(mensaje1)
    print(f"\n🤖 Bruce: {respuesta1}")

    # Verificar que Bruce se presentó
    bruce_se_presento = any(palabra in respuesta1.lower() for palabra in [
        'nioval', 'ferretería', 'ferreteria', 'productos', 'me comunico'
    ])

    bruce_pregunta_encargado = '¿se encontrará el encargado' in respuesta1.lower() or '¿se encontrara el encargado' in respuesta1.lower()

    if bruce_se_presento and bruce_pregunta_encargado:
        print("   ✅ CORRECTO - Bruce se presentó inmediatamente")
        print("   ✅ FIX 394 funcionó - Detectó '¿En qué le puedo apoyar?'")
    else:
        print(f"   ❌ ERROR - Bruce NO se presentó correctamente")
        print(f"   ❌ Respuesta: '{respuesta1}'")

    # ============================================================
    # TEST 2: Cliente repite pregunta - Verificar que NO repite respuesta
    # ============================================================
    print("\n" + "=" * 80)
    print("TEST 2: Cliente repite pregunta - Bruce NO debe repetir exactamente lo mismo")
    print("=" * 80)

    mensaje2 = "¿En qué le puedo apoyar?"
    print(f"\n👤 Cliente: {mensaje2}")

    respuesta2 = agente.procesar_respuesta(mensaje2)
    print(f"\n🤖 Bruce: {respuesta2}")

    # Verificar que Bruce NO repitió exactamente lo mismo
    import re
    resp1_norm = re.sub(r'[^\w\s]', '', respuesta1.lower()).strip()
    resp2_norm = re.sub(r'[^\w\s]', '', respuesta2.lower()).strip()

    if resp1_norm != resp2_norm:
        print("   ✅ CORRECTO - Bruce NO repitió la respuesta idéntica")
        print("   ✅ FIX 394 funcionó - Detectó repetición y regeneró")
    else:
        print(f"   ❌ ERROR - Bruce repitió EXACTAMENTE la misma respuesta")

    # ============================================================
    # TEST 3: Verificar que "Perfecto" NO se usa cuando cliente pregunta
    # ============================================================
    print("\n" + "=" * 80)
    print("TEST 3: Verificar que Bruce NO usa 'Perfecto' cuando cliente hace pregunta")
    print("=" * 80)

    bruce_uso_perfecto_mal = False
    for i, respuesta in enumerate([respuesta1, respuesta2], 1):
        if respuesta.lower().startswith('perfecto'):
            print(f"   ⚠️  Respuesta {i} empezó con 'Perfecto': '{respuesta[:60]}...'")
            # Verificar si cliente hizo pregunta
            mensaje = mensaje1 if i == 1 else mensaje2
            if '?' in mensaje:
                bruce_uso_perfecto_mal = True
                print(f"   ❌ ERROR - Cliente hizo pregunta pero Bruce dijo 'Perfecto'")

    if not bruce_uso_perfecto_mal:
        print("   ✅ CORRECTO - Bruce NO usó 'Perfecto' inapropiadamente")
        print("   ✅ FIX 394 funcionó - Filtro de 'Perfecto' activado")
    else:
        print(f"   ❌ ERROR - Bruce usó 'Perfecto' cuando cliente hizo pregunta")

    # ============================================================
    # TEST 4: Simular 3 repeticiones más para verificar detección en últimas 4
    # ============================================================
    print("\n" + "=" * 80)
    print("TEST 4: Verificar detección de repeticiones en últimas 4 respuestas")
    print("=" * 80)

    # Simular que Bruce va a responder lo mismo 3 veces más
    # Esto debería ser bloqueado por FIX 394
    contador_repeticiones = 0
    ultimas_4_respuestas = []

    for i in range(4):
        msg_test = f"¿Bueno? (mensaje {i+1})"
        print(f"\n👤 Cliente: {msg_test}")

        resp_test = agente.procesar_respuesta(msg_test)
        print(f"🤖 Bruce: {resp_test[:60]}...")

        # Normalizar y agregar a lista
        resp_norm = re.sub(r'[^\w\s]', '', resp_test.lower()).strip()
        ultimas_4_respuestas.append(resp_norm)

        # Verificar si es repetición
        if ultimas_4_respuestas.count(resp_norm) > 1:
            contador_repeticiones += 1

    print(f"\n📊 Repeticiones detectadas en 4 intentos: {contador_repeticiones}")

    if contador_repeticiones <= 1:
        print("   ✅ CORRECTO - FIX 394 detectó y bloqueó repeticiones")
        print("   ✅ Máximo 1 repetición permitida en 4 respuestas")
    else:
        print(f"   ❌ ERROR - Se permitieron {contador_repeticiones} repeticiones")
        print(f"   ❌ FIX 394 NO funcionó correctamente")

    print("\n" + "=" * 80)
    print("🏁 FIN DEL TEST")
    print("=" * 80)

    print("\n📊 RESUMEN:")
    print("   • TEST 1: FIX 394 detecta '¿En qué le puedo apoyar?' y se presenta")
    print("   • TEST 2: FIX 394 NO permite repetir respuesta idéntica")
    print("   • TEST 3: FIX 394 elimina 'Perfecto' cuando cliente hace pregunta")
    print("   • TEST 4: FIX 394 detecta repeticiones en últimas 4 respuestas")


if __name__ == "__main__":
    test_caso_bruce1105()
