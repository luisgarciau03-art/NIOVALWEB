"""
FIX 393: Test de mejoras en FIX 384 y FIX 204 para detección de rechazos
Simula el caso BRUCE1099 donde Bruce repitió pregunta 2 veces sin detectar rechazo
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


def test_caso_bruce1099():
    """
    Simula el caso real BRUCE1099:

    1. Cliente: "¿Bueno?" → Bruce ofrece catálogo
    2. Cliente: "No, no se encuentra." → Bruce pregunta por encargado ❌
    3. Cliente: "No, gracias." → Bruce repite pregunta por encargado ❌ REPETICIÓN
    4. Cliente: "No." → Bruce debió despedirse

    Con FIX 393:
    - FIX 384 detecta "No, no se encuentra" y NO pregunta por encargado
    - FIX 204 detecta repetición de PREGUNTA (no solo afirmaciones)
    - Bruce NO usa "Perfecto" cuando cliente rechaza
    """

    print("\n" + "=" * 80)
    print("🧪 TEST FIX 393: Detección de rechazos y repetición de preguntas (Caso BRUCE1099)")
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
    print("\n👤 Cliente: Ahora sí, pues buenas tardes. ¿Bueno?")
    respuesta = agente.procesar_respuesta("Ahora sí, pues buenas tardes. ¿Bueno?")
    print(f"Bruce: {respuesta}")

    # ============================================================
    # TEST 1: Cliente dice "No, no se encuentra"
    # ============================================================
    print("\n" + "=" * 80)
    print("TEST 1: Cliente dice 'No, no se encuentra' - Bruce NO debe preguntar por encargado")
    print("=" * 80)

    mensaje1 = "No, no se encuentra."
    print(f"\n👤 Cliente: {mensaje1}")

    respuesta1 = agente.procesar_respuesta(mensaje1)
    print(f"\n🤖 Bruce: {respuesta1}")

    # Verificar que Bruce NO preguntó por el encargado otra vez
    bruce_pregunta_encargado = any(frase in respuesta1.lower() for frase in [
        '¿se encontrará el encargado', '¿se encontrara el encargado',
        'se encontrará el encargado', 'se encontrara el encargado'
    ])

    bruce_ofrece_alternativa = any(frase in respuesta1.lower() for frase in [
        'whatsapp', 'correo', 'catálogo', 'catalogo', 'cuando regrese', 'más tarde'
    ])

    if not bruce_pregunta_encargado and bruce_ofrece_alternativa:
        print("   ✅ CORRECTO - Bruce NO preguntó por encargado otra vez")
        print("   ✅ Bruce ofreció alternativa (WhatsApp/correo)")
        print("   ✅ FIX 393 funcionó - REGLA 2 mejorada")
    elif bruce_pregunta_encargado:
        print(f"   ❌ ERROR - Bruce preguntó por encargado DESPUÉS de que cliente dijo 'No se encuentra'")
        print(f"   ❌ FIX 393 NO funcionó correctamente")
    else:
        print(f"   ⚠️  Bruce respondió: '{respuesta1}'")

    # ============================================================
    # TEST 2: Cliente dice "No, gracias" - Verificar repetición de preguntas
    # ============================================================
    print("\n" + "=" * 80)
    print("TEST 2: Cliente dice 'No, gracias' - Bruce NO debe repetir pregunta idéntica")
    print("=" * 80)

    mensaje2 = "No, gracias."
    print(f"\n👤 Cliente: {mensaje2}")

    respuesta2 = agente.procesar_respuesta(mensaje2)
    print(f"\n🤖 Bruce: {respuesta2}")

    # Verificar que Bruce NO repitió la misma pregunta
    bruce_repite_pregunta = False
    if '?' in respuesta1 and '?' in respuesta2:
        pregunta1 = respuesta1.split('?')[0].lower().strip()
        pregunta2 = respuesta2.split('?')[0].lower().strip()

        # Normalizar
        import re
        pregunta1_norm = re.sub(r'[^\w\s]', '', pregunta1).strip()
        pregunta2_norm = re.sub(r'[^\w\s]', '', pregunta2).strip()

        bruce_repite_pregunta = (pregunta1_norm == pregunta2_norm)

    if not bruce_repite_pregunta:
        print("   ✅ CORRECTO - Bruce NO repitió la pregunta idéntica")
        print("   ✅ FIX 393 funcionó - Detección de repetición de preguntas mejorada")
    else:
        print(f"   ❌ ERROR - Bruce repitió EXACTAMENTE la misma pregunta")
        print(f"   ❌ Pregunta 1: '{pregunta1}'")
        print(f"   ❌ Pregunta 2: '{pregunta2}'")

    # ============================================================
    # TEST 3: Verificar que Bruce NO usa "Perfecto" cuando cliente rechaza
    # ============================================================
    print("\n" + "=" * 80)
    print("TEST 3: Verificar que Bruce NO usa 'Perfecto' cuando cliente rechaza")
    print("=" * 80)

    bruce_usa_perfecto_incorrecto = False
    if 'perfecto' in respuesta1.lower() or 'perfecto' in respuesta2.lower():
        # Verificar si cliente dijo algo negativo
        cliente_rechazo = any(neg in mensaje1.lower() + mensaje2.lower() for neg in [
            'no', 'no se encuentra', 'no gracias', 'no está'
        ])
        if cliente_rechazo:
            bruce_usa_perfecto_incorrecto = True

    if not bruce_usa_perfecto_incorrecto:
        print("   ✅ CORRECTO - Bruce NO usó 'Perfecto' inapropiadamente")
        print("   ✅ FIX 393 funcionó - Respuestas más coherentes")
    else:
        print(f"   ❌ ERROR - Bruce usó 'Perfecto' cuando cliente rechazó")
        print(f"   ❌ Esto suena incoherente y robótico")

    print("\n" + "=" * 80)
    print("🏁 FIN DEL TEST")
    print("=" * 80)

    print("\n📊 RESUMEN:")
    print("   • TEST 1: FIX 393 mejora REGLA 2 para detectar 'No, no se encuentra'")
    print("   • TEST 2: FIX 393 detecta repetición de PREGUNTAS (no solo afirmaciones)")
    print("   • TEST 3: FIX 393 elimina 'Perfecto' inapropiado cuando cliente rechaza")


if __name__ == "__main__":
    test_caso_bruce1099()
