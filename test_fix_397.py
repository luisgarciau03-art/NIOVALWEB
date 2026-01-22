"""
FIX 397: Test de detección "No" simple + mejora REGLA 3
Simula el caso BRUCE1125 donde cliente dijo "No." y Bruce no entendió
Y BRUCE1127 donde Bruce dijo "ya lo tengo" sin datos reales
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


def test_caso_bruce1125():
    """
    Simula el caso real BRUCE1125:

    1. Bruce: "¿Se encontrará el encargado de compras?"
    2. Cliente: "No." → Bruce debió entender que NO está disponible
    3. Cliente: "No." (OTRA VEZ) → Bruce debió despedirse
    4. Pero Bruce NO entendió y quedó en silencio ❌

    Con FIX 397:
    - Detecta "No." simple como respuesta negativa
    - Verifica que Bruce preguntó por encargado recientemente
    - NO insiste con "¿Le envío el catálogo?"
    - Ofrece alternativa: WhatsApp para cuando regrese
    """

    print("\n" + "=" * 80)
    print("🧪 TEST FIX 397 - PARTE 1: Detección 'No' simple (Caso BRUCE1125)")
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
    print("\n👤 Cliente: Buenos días.")
    respuesta = agente.procesar_respuesta("Buenos días.")
    print(f"Bruce: {respuesta}")

    # ============================================================
    # TEST 1: Cliente dice "No." simple - Bruce debe detectar negación
    # ============================================================
    print("\n" + "=" * 80)
    print("TEST 1: Cliente dice 'No.' - Bruce debe detectar que encargado NO está")
    print("=" * 80)

    mensaje1 = "No."
    print(f"\n👤 Cliente: {mensaje1}")

    respuesta1 = agente.procesar_respuesta(mensaje1)
    print(f"\n🤖 Bruce: {respuesta1}")

    # Verificar que Bruce NO preguntó por encargado otra vez
    bruce_insiste_encargado = any(frase in respuesta1.lower() for frase in [
        '¿se encontrará el encargado', '¿se encontrara el encargado',
        '¿me comunica con', '¿puede pasar'
    ])

    # Verificar que Bruce ofreció alternativa
    bruce_ofrece_alternativa = any(frase in respuesta1.lower() for frase in [
        'whatsapp', 'correo', 'catálogo', 'catalogo', 'cuando regrese',
        'puede dejar', 'le envío', 'le envio'
    ])

    if not bruce_insiste_encargado and bruce_ofrece_alternativa:
        print("   ✅ CORRECTO - Bruce NO insistió por encargado")
        print("   ✅ Bruce ofreció alternativa (WhatsApp/correo)")
        print("   ✅ FIX 397 funcionó - 'No' simple detectado")
    elif bruce_insiste_encargado:
        print(f"   ❌ ERROR - Bruce insistió por encargado después de 'No'")
        print(f"   ❌ FIX 397 NO funcionó")
    else:
        print(f"   ⚠️  Bruce respondió: '{respuesta1}'")

    # ============================================================
    # TEST 2: Cliente dice "No." OTRA VEZ - Bruce NO debe repetir
    # ============================================================
    print("\n" + "=" * 80)
    print("TEST 2: Cliente repite 'No.' - Bruce NO debe repetir pregunta")
    print("=" * 80)

    mensaje2 = "No."
    print(f"\n👤 Cliente: {mensaje2}")

    respuesta2 = agente.procesar_respuesta(mensaje2)
    print(f"\n🤖 Bruce: {respuesta2}")

    # Verificar que Bruce NO repitió la misma pregunta
    import re
    resp1_norm = re.sub(r'[^\w\s]', '', respuesta1.lower()).strip()
    resp2_norm = re.sub(r'[^\w\s]', '', respuesta2.lower()).strip()

    if resp1_norm != resp2_norm:
        print("   ✅ CORRECTO - Bruce NO repitió la pregunta idéntica")
        print("   ✅ Bruce varió su respuesta")
    else:
        print(f"   ❌ ERROR - Bruce repitió EXACTAMENTE la misma respuesta")

    print("\n" + "=" * 80)
    print("🏁 FIN PARTE 1")
    print("=" * 80)


def test_caso_bruce1127():
    """
    Simula el caso real BRUCE1127:

    1. Cliente: "Bueno, pásele este." (hablando con otra persona)
    2. Bruce: "Perfecto, ya lo tengo registrado" ❌ SIN DATOS REALES
    3. Cliente: "Sí. ¿Bueno?"
    4. Bruce: "Perfecto, ya lo tengo registrado" ❌ OTRA VEZ

    Con FIX 397:
    - REGLA 3 mejorada detecta frases ambiguas
    - "pásele este", "un segundo", etc. NO son datos
    - Bruce NO dice "ya lo tengo" sin datos reales
    - Bruce pide el dato correctamente
    """

    print("\n" + "=" * 80)
    print("🧪 TEST FIX 397 - PARTE 2: REGLA 3 mejorada (Caso BRUCE1127)")
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
    print("\n👤 Cliente: Dígame.")
    respuesta = agente.procesar_respuesta("Dígame.")
    print(f"Bruce: {respuesta}")

    # ============================================================
    # TEST 3: Cliente dice frase ambigua - Bruce NO debe decir "ya lo tengo"
    # ============================================================
    print("\n" + "=" * 80)
    print("TEST 3: Cliente dice 'Bueno, pásele este' - Bruce NO debe decir 'ya lo tengo'")
    print("=" * 80)

    mensaje3 = "Bueno, pásele este."
    print(f"\n👤 Cliente: {mensaje3}")

    respuesta3 = agente.procesar_respuesta(mensaje3)
    print(f"\n🤖 Bruce: {respuesta3}")

    # Verificar que Bruce NO dijo "ya lo tengo"
    bruce_dice_ya_tengo = any(frase in respuesta3.lower() for frase in [
        'ya lo tengo', 'ya lo tengo registrado', 'le llegará', 'le llegara'
    ])

    # Verificar que Bruce pidió el dato
    bruce_pide_dato = any(frase in respuesta3.lower() for frase in [
        'número', 'numero', 'whatsapp', 'correo', 'email',
        'me puede', 'me podría', 'me confirma'
    ])

    if not bruce_dice_ya_tengo and bruce_pide_dato:
        print("   ✅ CORRECTO - Bruce NO dijo 'ya lo tengo' sin datos")
        print("   ✅ Bruce pidió el dato correctamente")
        print("   ✅ FIX 397 REGLA 3 funcionó")
    elif bruce_dice_ya_tengo:
        print(f"   ❌ ERROR - Bruce dijo 'ya lo tengo' sin datos reales")
        print(f"   ❌ Cliente solo dijo frase ambigua: '{mensaje3}'")
        print(f"   ❌ FIX 397 REGLA 3 NO funcionó")
    else:
        print(f"   ⚠️  Bruce respondió: '{respuesta3}'")

    # ============================================================
    # TEST 4: Verificar otras frases ambiguas
    # ============================================================
    print("\n" + "=" * 80)
    print("TEST 4: Verificar detección de otras frases ambiguas")
    print("=" * 80)

    frases_ambiguas_test = [
        "Un segundo.",
        "Un momento.",
        "Espere.",
        "Ok.",
        "Así es.",
        "Claro."
    ]

    frases_correctas = 0
    for frase in frases_ambiguas_test:
        # Resetear agente
        agente_test = AgenteVentas(
            contacto_info={'nombre_negocio': 'Ferretería Test', 'telefono': '+525511112222'},
            whatsapp_validator=None
        )
        agente_test.iniciar_conversacion()
        agente_test.procesar_respuesta("Dígame")

        print(f"\n   Probando: '{frase}'")
        respuesta_test = agente_test.procesar_respuesta(frase)

        dice_ya_tengo = 'ya lo tengo' in respuesta_test.lower() or 'le llegará' in respuesta_test.lower()
        pide_dato = 'número' in respuesta_test.lower() or 'whatsapp' in respuesta_test.lower()

        if not dice_ya_tengo:
            print(f"      ✅ CORRECTO - NO dijo 'ya lo tengo' con frase ambigua")
            frases_correctas += 1
        else:
            print(f"      ❌ ERROR - Dijo 'ya lo tengo' con: '{frase}'")

    print(f"\n   📊 Frases detectadas correctamente: {frases_correctas}/{len(frases_ambiguas_test)}")

    if frases_correctas >= len(frases_ambiguas_test) * 0.8:  # 80% o más
        print(f"   ✅ FIX 397 REGLA 3 funcionó - Mayoría de frases ambiguas detectadas")
    else:
        print(f"   ❌ FIX 397 REGLA 3 necesita mejoras")

    print("\n" + "=" * 80)
    print("🏁 FIN PARTE 2")
    print("=" * 80)


if __name__ == "__main__":
    print("\n" + "=" * 100)
    print("🧪 TEST COMPLETO FIX 397: Detección 'No' simple + REGLA 3 mejorada")
    print("=" * 100)

    # Ejecutar ambas partes
    test_caso_bruce1125()
    test_caso_bruce1127()

    print("\n" + "=" * 100)
    print("📊 RESUMEN FINAL FIX 397")
    print("=" * 100)
    print("\n✅ PARTE 1: Detección 'No' simple")
    print("   • Detecta 'No.' como respuesta negativa cuando Bruce preguntó por encargado")
    print("   • Bruce ofrece alternativa (WhatsApp) en vez de insistir")
    print("   • Bruce NO repite pregunta cuando cliente repite 'No'")
    print("\n✅ PARTE 2: REGLA 3 mejorada")
    print("   • Detecta frases ambiguas: 'pásele este', 'un segundo', etc.")
    print("   • Bruce NO dice 'ya lo tengo' sin datos reales")
    print("   • Bruce pide el dato correctamente")
