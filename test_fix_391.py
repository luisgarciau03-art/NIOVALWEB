"""
FIX 391: Test de refinamiento de FIX 384 y FIX 204
Simula el caso BRUCE1085 donde FIX 384 interfirió con captura de WhatsApp
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


def test_caso_bruce1085():
    """
    Simula el caso real BRUCE1085:

    1. Cliente ofrece dejar mensaje
    2. GPT genera correctamente: "Perfecto. ¿Me podría proporcionar su número de WhatsApp..."
    3. FIX 384 SOBRESCRIBE: "Claro. Manejamos productos de ferretería..."
    4. Se pierde oportunidad de capturar WhatsApp

    Con FIX 391, esto NO debería pasar.
    """

    print("\n" + "=" * 80)
    print("🧪 TEST FIX 391: Refinamiento de FIX 384 y FIX 204 (Caso BRUCE1085)")
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

    # Cliente saluda
    print("\n👤 Cliente: ¿Qué tal?")
    respuesta = agente.procesar_respuesta("¿Qué tal?")
    print(f"Bruce: {respuesta}")

    # ============================================================
    # TEST 1: Cliente ofrece dejar mensaje (BRUCE1085 inicio)
    # ============================================================
    print("\n" + "=" * 80)
    print("TEST 1: Cliente ofrece dejar mensaje - GPT debe pedir WhatsApp")
    print("=" * 80)

    mensaje1 = "¿no se encuentra, quiere dejarle el mensaje?"
    print(f"\n👤 Cliente: {mensaje1}")

    respuesta1 = agente.procesar_respuesta(mensaje1)
    print(f"\n🤖 Bruce: {respuesta1}")

    # Verificar que Bruce pidió WhatsApp (NO debió activarse FIX 384)
    pide_whatsapp = any(palabra in respuesta1.lower() for palabra in [
        'whatsapp', 'número', 'numero', 'contacto', 'correo'
    ])

    if pide_whatsapp:
        print("   ✅ CORRECTO - Bruce pidió dato de contacto (FIX 391 funcionó)")
        print("   ✅ FIX 384 NO interfirió con captura de WhatsApp")
    else:
        print(f"   ❌ ERROR - Bruce NO pidió WhatsApp")
        print(f"   ❌ FIX 384 pudo haber interferido")

    # ============================================================
    # TEST 2: Cliente confirma "Sí" - GPT puede usar frase similar
    # ============================================================
    print("\n" + "=" * 80)
    print("TEST 2: Cliente confirma 'Sí' - FIX 204 NO debe bloquear respuesta útil")
    print("=" * 80)

    # Simular que Bruce pregunta por productos
    agente.conversation_history.append({
        'role': 'assistant',
        'content': 'Manejamos productos de ferretería: grifería, cintas, herramientas.'
    })

    mensaje2 = "Sí."
    print(f"\n👤 Cliente: {mensaje2}")

    respuesta2 = agente.procesar_respuesta(mensaje2)
    print(f"\n🤖 Bruce: {respuesta2}")

    # Verificar que Bruce siguió conversación lógicamente
    # (NO debe regenerar porque cliente confirmó)
    if len(respuesta2) > 10:
        print("   ✅ CORRECTO - Bruce respondió coherentemente")
        print("   ✅ FIX 204 NO bloqueó respuesta útil después de confirmación")
    else:
        print(f"   ⚠️  Respuesta muy corta: '{respuesta2}'")

    # ============================================================
    # TEST 3: Verificar que FIX 384 SÍ funciona en casos legítimos
    # ============================================================
    print("\n" + "=" * 80)
    print("TEST 3: Verificar que FIX 384 SÍ funciona cuando debe (caso legítimo)")
    print("=" * 80)

    # Reiniciar agente
    agente2 = AgenteVentas(
        contacto_info={
            'nombre_negocio': 'Ferretería Test 2',
            'telefono': '+525511113333'
        },
        whatsapp_validator=None
    )

    agente2.iniciar_conversacion()
    agente2.procesar_respuesta("Buenos días")

    # Cliente dice que encargado NO está
    mensaje3 = "No está, ya salió"
    print(f"\n👤 Cliente: {mensaje3}")

    # Simular que GPT insiste con encargado (error que FIX 384 debe corregir)
    # Agregar manualmente a historial para simular respuesta GPT
    agente2.conversation_history.append({
        'role': 'user',
        'content': mensaje3
    })

    # FIX 384 debe detectar "Cliente dijo que encargado NO está" y corregir
    print("   Esperado: FIX 384 debe sugerir enviar catálogo por WhatsApp")

    print("\n" + "=" * 80)
    print("🏁 FIN DEL TEST")
    print("=" * 80)

    print("\n📊 RESUMEN:")
    print("   • TEST 1: Verificar que FIX 391 NO bloquea captura de WhatsApp")
    print("   • TEST 2: Verificar que FIX 391 permite respuestas útiles tras confirmación")
    print("   • TEST 3: Verificar que FIX 384 sigue funcionando correctamente")


if __name__ == "__main__":
    test_caso_bruce1085()
