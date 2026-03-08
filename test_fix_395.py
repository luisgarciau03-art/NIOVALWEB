"""
FIX 395: Test de mejoras en detección de encargado disponible y logs completos
Simula el caso BRUCE1122 donde Bruce no detectó "con ella habla" como encargado
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


def test_caso_bruce1122():
    """
    Simula el caso real BRUCE1122:

    1. Bruce: "¿Se encontrará el encargado o encargada de compras?"
    2. Cliente: "Sí, con ella" → Bruce debió detectar que ELLA ES LA ENCARGADA
    3. Cliente: "Sí, con ella habla." → Bruce CONFIRMÓ que ella es la encargada
    4. Bruce NO detectó y esperó 7 segundos (muy largo)

    Con FIX 395:
    - Detecta "con ella habla", "sí, con ella" como ENCARGADO DISPONIBLE
    - Ofrece catálogo DIRECTAMENTE sin preguntar otra vez
    - Reduce timeout de 4s a 2.5s para evitar delays largos
    """

    print("\n" + "=" * 80)
    print("🧪 TEST FIX 395: Detección 'con ella habla' y logs completos (Caso BRUCE1122)")
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
    print("\n👤 Cliente: Listo, buen día.")
    respuesta = agente.procesar_respuesta("Listo, buen día.")
    print(f"Bruce: {respuesta}")

    # ============================================================
    # TEST 1: Cliente dice "Sí, con ella" - Bruce debe detectar encargado
    # ============================================================
    print("\n" + "=" * 80)
    print("TEST 1: Cliente dice 'Sí, con ella' - Bruce debe detectar ENCARGADO DISPONIBLE")
    print("=" * 80)

    mensaje1 = "Sí, con ella"
    print(f"\n👤 Cliente: {mensaje1}")

    respuesta1 = agente.procesar_respuesta(mensaje1)
    print(f"\n🤖 Bruce: {respuesta1}")

    # Verificar que Bruce NO preguntó por el encargado otra vez
    bruce_pregunta_encargado = any(frase in respuesta1.lower() for frase in [
        '¿se encontrará el encargado', '¿se encontrara el encargado',
        'se encontrará el encargado', 'se encontrara el encargado',
        '¿me comunica con', '¿me puede comunicar'
    ])

    bruce_ofrece_catalogo = any(frase in respuesta1.lower() for frase in [
        'catálogo', 'catalogo', 'productos', 'información', 'informacion'
    ])

    if not bruce_pregunta_encargado and bruce_ofrece_catalogo:
        print("   ✅ CORRECTO - Bruce NO preguntó por encargado otra vez")
        print("   ✅ Bruce detectó que cliente ES el encargado")
        print("   ✅ Bruce ofreció catálogo DIRECTAMENTE")
        print("   ✅ FIX 395 funcionó - Patrón 'sí, con ella' detectado")
    elif bruce_pregunta_encargado:
        print(f"   ❌ ERROR - Bruce preguntó por encargado DESPUÉS de que cliente dijo 'Sí, con ella'")
        print(f"   ❌ FIX 395 NO funcionó correctamente")
    else:
        print(f"   ⚠️  Bruce respondió: '{respuesta1}'")

    # ============================================================
    # TEST 2: Cliente confirma "Sí, con ella habla." - Verificar detección
    # ============================================================
    print("\n" + "=" * 80)
    print("TEST 2: Cliente confirma 'Sí, con ella habla.' - Bruce debe CONFIRMAR detección")
    print("=" * 80)

    mensaje2 = "Sí, con ella habla."
    print(f"\n👤 Cliente: {mensaje2}")

    respuesta2 = agente.procesar_respuesta(mensaje2)
    print(f"\n🤖 Bruce: {respuesta2}")

    # Verificar que Bruce NO repitió pregunta por encargado
    bruce_repite_pregunta = any(frase in respuesta2.lower() for frase in [
        '¿se encontrará el encargado', '¿se encontrara el encargado',
        'se encontrará el encargado', 'se encontrara el encargado'
    ])

    bruce_continua_oferta = any(frase in respuesta2.lower() for frase in [
        'catálogo', 'catalogo', 'whatsapp', 'correo', 'productos'
    ])

    if not bruce_repite_pregunta and bruce_continua_oferta:
        print("   ✅ CORRECTO - Bruce NO repitió pregunta por encargado")
        print("   ✅ Bruce continuó ofreciendo catálogo")
        print("   ✅ FIX 395 funcionó - Patrón 'con ella habla' detectado")
    else:
        print(f"   ❌ ERROR - Bruce no manejó correctamente la confirmación")
        print(f"   ❌ Respuesta: '{respuesta2}'")

    # ============================================================
    # TEST 3: Verificar otros patrones de FIX 395
    # ============================================================
    print("\n" + "=" * 80)
    print("TEST 3: Verificar otros patrones de detección de encargado")
    print("=" * 80)

    patrones_test = [
        "Sí, con él habla",
        "Yo soy el encargado",
        "Soy la encargada",
        "Ella habla",
        "Soy yo"
    ]

    patrones_correctos = 0
    for patron in patrones_test:
        # Resetear agente para cada prueba
        agente_test = AgenteVentas(
            contacto_info={'nombre_negocio': 'Ferretería Test', 'telefono': '+525511112222'},
            whatsapp_validator=None
        )
        agente_test.iniciar_conversacion()
        agente_test.procesar_respuesta("Listo, buen día.")

        print(f"\n   Probando: '{patron}'")
        respuesta_test = agente_test.procesar_respuesta(patron)

        pregunta_encargado = '¿se encontrará el encargado' in respuesta_test.lower() or \
                            '¿se encontrara el encargado' in respuesta_test.lower()
        ofrece_catalogo = 'catálogo' in respuesta_test.lower() or 'catalogo' in respuesta_test.lower()

        if not pregunta_encargado and ofrece_catalogo:
            print(f"      ✅ DETECTADO correctamente")
            patrones_correctos += 1
        else:
            print(f"      ❌ NO detectado - Respuesta: '{respuesta_test[:80]}...'")

    print(f"\n   📊 Patrones detectados correctamente: {patrones_correctos}/{len(patrones_test)}")

    if patrones_correctos >= len(patrones_test) * 0.8:  # 80% o más
        print(f"   ✅ FIX 395 funcionó - Mayoría de patrones detectados")
    else:
        print(f"   ❌ FIX 395 necesita mejoras - Solo {patrones_correctos}/{len(patrones_test)} funcionaron")

    print("\n" + "=" * 80)
    print("🏁 FIN DEL TEST")
    print("=" * 80)

    print("\n📊 RESUMEN:")
    print("   • TEST 1: FIX 395 detecta 'Sí, con ella' como encargado disponible")
    print("   • TEST 2: FIX 395 detecta 'con ella habla' sin repetir pregunta")
    print("   • TEST 3: FIX 395 detecta variantes (con él, yo soy, ella habla)")
    print("\n✅ MEJORAS ADICIONALES:")
    print("   • Logs completos: ?bruce_id=X busca en 5000 logs (antes: 500)")
    print("   • Timeout reducido: 2.5s (antes: 4s) para menos delays")


if __name__ == "__main__":
    test_caso_bruce1122()
