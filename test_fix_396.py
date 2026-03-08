"""
FIX 396: Test de re-presentación inmediata después de transferencia
Simula el caso BRUCE1124 donde Bruce NO se presentó después de "¿Bueno?"
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


def test_caso_bruce1124():
    """
    Simula el caso real BRUCE1124:

    1. Cliente: "Déjame checo a ver si está" → Bruce espera
    2. Cliente: "Claro, espero."
    3. Cliente: "¿Bueno?" (PERSONA NUEVA después de transferencia)
    4. Bruce debió RE-PRESENTARSE pero respondió "Perfecto, ya lo tengo registrado" ❌

    Con FIX 396:
    - Detecta "¿Bueno?" después de transferencia
    - Bruce se RE-PRESENTA inmediatamente
    - NO deja que GPT malinterprete "¿Bueno?" como confirmación
    """

    print("\n" + "=" * 80)
    print("🧪 TEST FIX 396: Re-presentación después de transferencia (Caso BRUCE1124)")
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
    print("\n👤 Cliente: Bueno,")
    respuesta = agente.procesar_respuesta("Bueno,")
    print(f"Bruce: {respuesta}")

    # ============================================================
    # TEST 1: Cliente pide esperar para transferencia
    # ============================================================
    print("\n" + "=" * 80)
    print("TEST 1: Cliente dice 'Déjame checo' - Bruce debe ESPERAR")
    print("=" * 80)

    mensaje1 = "Este, déjame checo a ver si está"
    print(f"\n👤 Cliente: {mensaje1}")

    respuesta1 = agente.procesar_respuesta(mensaje1)
    print(f"\n🤖 Bruce: {respuesta1}")

    # Verificar que Bruce dijo "Claro, espero."
    if respuesta1 and 'espero' in respuesta1.lower():
        print("   ✅ CORRECTO - Bruce respondió 'Claro, espero.'")
        print(f"   ✅ Estado: {agente.estado_conversacion}")
    else:
        print(f"   ❌ ERROR - Bruce NO esperó correctamente")
        print(f"   ❌ Respuesta: '{respuesta1}'")

    # Verificar estado ESPERANDO_TRANSFERENCIA
    if agente.estado_conversacion == EstadoConversacion.ESPERANDO_TRANSFERENCIA:
        print("   ✅ Estado correcto: ESPERANDO_TRANSFERENCIA")
    else:
        print(f"   ❌ Estado incorrecto: {agente.estado_conversacion}")

    # ============================================================
    # TEST 2: Persona nueva dice "¿Bueno?" - Bruce debe RE-PRESENTARSE
    # ============================================================
    print("\n" + "=" * 80)
    print("TEST 2: Persona nueva dice '¿Bueno?' - Bruce debe RE-PRESENTARSE")
    print("=" * 80)

    mensaje2 = "¿Bueno?"
    print(f"\n👤 Cliente (PERSONA NUEVA): {mensaje2}")

    respuesta2 = agente.procesar_respuesta(mensaje2)
    print(f"\n🤖 Bruce: {respuesta2}")

    # Verificar que Bruce se presentó
    bruce_se_presento = any(palabra in respuesta2.lower() for palabra in [
        'nioval', 'ferretería', 'ferreteria', 'productos', 'me comunico', 'soy bruce'
    ])

    bruce_pregunta_encargado = '¿se encontrará el encargado' in respuesta2.lower() or \
                               '¿se encontrara el encargado' in respuesta2.lower() or \
                               '¿usted es el encargado' in respuesta2.lower()

    # Verificar que NO dijo "Perfecto, ya lo tengo registrado"
    bruce_malinterpreto = 'perfecto' in respuesta2.lower() and \
                          ('ya lo tengo' in respuesta2.lower() or \
                           'le llegará' in respuesta2.lower() or \
                           'le llegara' in respuesta2.lower())

    if bruce_se_presento and not bruce_malinterpreto:
        print("   ✅ CORRECTO - Bruce se RE-PRESENTÓ correctamente")
        print("   ✅ Bruce NO malinterpretó '¿Bueno?' como confirmación")
        print("   ✅ FIX 396 funcionó")
    elif bruce_malinterpreto:
        print(f"   ❌ ERROR - Bruce malinterpretó '¿Bueno?' como confirmación")
        print(f"   ❌ Bruce dijo: '{respuesta2}'")
        print(f"   ❌ FIX 396 NO funcionó")
    else:
        print(f"   ⚠️  Bruce respondió: '{respuesta2}'")

    # Verificar estado BUSCANDO_ENCARGADO
    if agente.estado_conversacion == EstadoConversacion.BUSCANDO_ENCARGADO:
        print("   ✅ Estado correcto: BUSCANDO_ENCARGADO")
    else:
        print(f"   ❌ Estado incorrecto: {agente.estado_conversacion}")

    # ============================================================
    # TEST 3: Verificar otros saludos de persona nueva
    # ============================================================
    print("\n" + "=" * 80)
    print("TEST 3: Verificar otros saludos de persona nueva")
    print("=" * 80)

    saludos_test = [
        "Hola",
        "Dígame",
        "Mande",
        "¿Qué pasó?",
        "Aló"
    ]

    saludos_correctos = 0
    for saludo_test in saludos_test:
        # Resetear agente para cada prueba
        agente_test = AgenteVentas(
            contacto_info={'nombre_negocio': 'Ferretería Test', 'telefono': '+525511112222'},
            whatsapp_validator=None
        )
        agente_test.iniciar_conversacion()
        agente_test.procesar_respuesta("Bueno")

        # Simular transferencia
        agente_test.procesar_respuesta("Déjame checo")

        print(f"\n   Probando: '{saludo_test}'")
        respuesta_test = agente_test.procesar_respuesta(saludo_test)

        se_presento = 'nioval' in respuesta_test.lower() or \
                     'ferretería' in respuesta_test.lower() or \
                     'ferreteria' in respuesta_test.lower()

        no_malinterpreto = not ('perfecto' in respuesta_test.lower() and \
                               'ya lo tengo' in respuesta_test.lower())

        if se_presento and no_malinterpreto:
            print(f"      ✅ DETECTADO y RE-PRESENTADO correctamente")
            saludos_correctos += 1
        else:
            print(f"      ❌ NO detectado - Respuesta: '{respuesta_test[:80]}...'")

    print(f"\n   📊 Saludos detectados correctamente: {saludos_correctos}/{len(saludos_test)}")

    if saludos_correctos >= len(saludos_test) * 0.8:  # 80% o más
        print(f"   ✅ FIX 396 funcionó - Mayoría de saludos detectados")
    else:
        print(f"   ❌ FIX 396 necesita mejoras - Solo {saludos_correctos}/{len(saludos_test)} funcionaron")

    print("\n" + "=" * 80)
    print("🏁 FIN DEL TEST")
    print("=" * 80)

    print("\n📊 RESUMEN:")
    print("   • TEST 1: Bruce detecta 'Déjame checo' y espera")
    print("   • TEST 2: Bruce detecta '¿Bueno?' después de transferencia y se re-presenta")
    print("   • TEST 3: Bruce detecta otros saludos (Hola, Dígame, Mande, etc.)")
    print("\n✅ FIX 396: RE-PRESENTACIÓN INMEDIATA después de transferencia")
    print("   • Evita malinterpretación de '¿Bueno?' como confirmación")
    print("   • Bruce se presenta nuevamente con persona nueva")


if __name__ == "__main__":
    test_caso_bruce1124()
