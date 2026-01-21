"""
FIX 389: Test de detección PRE-GPT de transferencias
Simula el caso BRUCE1078 donde cliente dice "permítame" múltiples veces
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


def test_caso_bruce1078():
    """
    Simula el caso real BRUCE1078:

    [20:29:56] Cliente: "Permítame un momento, déjeme ver si no ha salido a comer. Permítame,"
    [20:29:56] Bruce: "Claro, espero." ✅

    [20:29:59] Cliente: "Sí, sí. Sí, permítame, Sí, permítame, déjeme verificar si todavía se encuentra."
    [20:29:59] Bruce: DEBIÓ DECIR "Claro, espero." ❌ (pero dijo "Sí, buen día. Soy Bruce...")
    """

    print("\n" + "=" * 80)
    print("🧪 TEST FIX 389: Detección PRE-GPT de transferencias (Caso BRUCE1078)")
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
    print("\n👤 Cliente: Buenas")
    respuesta = agente.procesar_respuesta("Buenas")
    print(f"Bruce: {respuesta}")

    # ============================================================
    # PRIMER "PERMÍTAME" - Cliente pide esperar
    # ============================================================
    print("\n" + "=" * 80)
    print("TEST 1: Cliente dice 'Permítame un momento...'")
    print("=" * 80)

    mensaje1 = "Permítame un momento, déjeme ver si no ha salido a comer. Permítame,"
    print(f"\n👤 Cliente: {mensaje1}")

    # Verificar estado ANTES
    print(f"   Estado ANTES: {agente.estado_conversacion}")

    respuesta1 = agente.procesar_respuesta(mensaje1)

    # Verificar estado DESPUÉS
    print(f"   Estado DESPUÉS: {agente.estado_conversacion}")
    print(f"🤖 Bruce: {respuesta1}")

    # Verificar resultado
    if respuesta1 == "Claro, espero.":
        print("   ✅ CORRECTO - Bruce respondió 'Claro, espero.' inmediatamente")
    else:
        print(f"   ❌ ERROR - Bruce debió decir 'Claro, espero.' pero dijo '{respuesta1}'")

    # ============================================================
    # SEGUNDO "PERMÍTAME" - Cliente REPITE permítame
    # ============================================================
    print("\n" + "=" * 80)
    print("TEST 2: Cliente REPITE 'Sí, permítame...' (caso crítico)")
    print("=" * 80)

    mensaje2 = "Sí, sí. Sí, permítame, Sí, permítame, déjeme verificar si todavía se encuentra."
    print(f"\n👤 Cliente: {mensaje2}")

    # Verificar estado ANTES
    print(f"   Estado ANTES: {agente.estado_conversacion}")

    respuesta2 = agente.procesar_respuesta(mensaje2)

    # Verificar estado DESPUÉS
    print(f"   Estado DESPUÉS: {agente.estado_conversacion}")
    print(f"🤖 Bruce: {respuesta2}")

    # Verificar resultado
    if respuesta2 == "Claro, espero.":
        print("   ✅ CORRECTO - Bruce volvió a responder 'Claro, espero.' SIN llamar GPT")
        print("   ✅ FIX 389 funciona correctamente - NO se re-presenta cuando cliente está transfiriendo")
    else:
        print(f"   ❌ ERROR - Bruce NO debió re-presentarse")
        print(f"   ❌ Esperado: 'Claro, espero.'")
        print(f"   ❌ Obtenido: '{respuesta2}'")

    # ============================================================
    # TERCER MENSAJE - Cliente transfiere al encargado (persona nueva)
    # ============================================================
    print("\n" + "=" * 80)
    print("TEST 3: Persona nueva contesta (transferencia exitosa)")
    print("=" * 80)

    mensaje3 = "¿Bueno?"
    print(f"\n👤 Cliente (NUEVA PERSONA): {mensaje3}")

    # Verificar estado ANTES
    print(f"   Estado ANTES: {agente.estado_conversacion}")

    respuesta3 = agente.procesar_respuesta(mensaje3)

    # Verificar estado DESPUÉS
    print(f"   Estado DESPUÉS: {agente.estado_conversacion}")
    print(f"🤖 Bruce: {respuesta3}")

    # Verificar que ahora SÍ se presenta (porque es persona nueva)
    if "bruce" in respuesta3.lower() and "nioval" in respuesta3.lower():
        print("   ✅ CORRECTO - Bruce se RE-PRESENTA porque detectó persona nueva")
    else:
        print(f"   ⚠️  Bruce debió re-presentarse con NIOVAL")

    print("\n" + "=" * 80)
    print("🏁 FIN DEL TEST")
    print("=" * 80)


if __name__ == "__main__":
    test_caso_bruce1078()
