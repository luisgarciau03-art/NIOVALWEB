#!/usr/bin/env python3
"""
Test completo para FIX 255: Bruce insiste cuando cliente dice "no se encuentra"
"""
import sys
import re

# Fix encoding for Windows console
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')


def test_filtro_6b(cliente_msg, bruce_respuesta):
    """Simula el FILTRO 6B ampliado con FIX 255"""

    ultimo_cliente = cliente_msg.lower()
    respuesta_lower = bruce_respuesta.lower()

    # Detectar si cliente dice que encargado NO está disponible
    patrones_no_disponible = [
        r'no\s+se\s+encuentra',
        r'no\s+est[aá]',
        r'no\s+est[aá]\s+(?:disponible|aqu[ií]|en\s+este\s+momento)',
        r'no\s+(?:lo|la)\s+tengo',
        r'ya\s+sali[oó]',
        r'(?:est[aá]|se\s+fue)\s+(?:fuera|afuera)',
        r'(?:sali[oó]|se\s+fue)',
        r'llamar\s+(?:m[aá]s\s+)?tarde',  # FIX 255
        r'llame\s+(?:m[aá]s\s+)?tarde',   # FIX 255
    ]

    cliente_dice_no_disponible = any(re.search(p, ultimo_cliente) for p in patrones_no_disponible)

    # FIX 255: Ampliar detección - Bruce pide transferencia O pregunta por mejor momento
    bruce_insiste_contacto = any(kw in respuesta_lower for kw in [
        'me lo podría comunicar',
        'me lo puede comunicar',
        'me podría comunicar',
        'me puede pasar',
        'me lo pasa',
        'me comunica con',
        'transferir',
        'comunicar con',
        # FIX 255: Nuevos patrones
        'mejor momento para llamar',
        'cuándo puedo llamar',
        'a qué hora',
        'qué hora puedo',
        'cuándo lo encuentro',
        'cuándo está disponible',
    ])

    print(f"\n📊 ANÁLISIS:")
    print(f"   Cliente: '{cliente_msg[:80]}'")
    print(f"   Bruce iba a decir: '{bruce_respuesta[:80]}'")
    print(f"   cliente_dice_no_disponible: {cliente_dice_no_disponible}")
    print(f"   bruce_insiste_contacto: {bruce_insiste_contacto}")

    if cliente_dice_no_disponible and bruce_insiste_contacto:
        print(f"\n🚫 FILTRO ACTIVADO - Bruce debería ofrecer catálogo")
        return True
    else:
        print(f"\n✅ NO ACTIVAR FILTRO")
        return False


if __name__ == "__main__":
    print("=" * 70)
    print("TEST FIX 255: Cliente dice 'no se encuentra' pero Bruce insiste")
    print("=" * 70)

    # Caso 1: Del log real - "no se encuentra" + "mejor momento"
    print("\n\n🧪 CASO 1: Cliente dice 'no se encuentra' y Bruce pregunta por mejor momento")
    resultado1 = test_filtro_6b(
        "¿No se encuentra? No se encuentra.",
        "Entiendo. ¿Hay un mejor momento para llamar y hablar con el encargado de compras?"
    )
    assert resultado1 == True, "❌ FALLO: Debería activar el filtro"
    print("✅ CORRECTO: Filtro activado")

    # Caso 2: "llamar más tarde" + "mejor momento"
    print("\n\n🧪 CASO 2: Cliente dice 'llamar más tarde' y Bruce pregunta por horario")
    resultado2 = test_filtro_6b(
        "Ahorita no se encuentra, si gusta, llamar más tarde.",
        "¿A qué hora puedo llamar?"
    )
    assert resultado2 == True, "❌ FALLO: Debería activar el filtro"
    print("✅ CORRECTO: Filtro activado")

    # Caso 3: "no está" + "transferencia"
    print("\n\n🧪 CASO 3: Cliente dice 'no está' y Bruce pide transferencia")
    resultado3 = test_filtro_6b(
        "Ahorita no está disponible.",
        "¿Me lo podría comunicar por favor?"
    )
    assert resultado3 == True, "❌ FALLO: Debería activar el filtro"
    print("✅ CORRECTO: Filtro activado")

    # Caso 4: "no se encuentra" pero Bruce ofrece catálogo (NO activar)
    print("\n\n🧪 CASO 4: Cliente dice 'no se encuentra' y Bruce ofrece catálogo (NO ACTIVAR)")
    resultado4 = test_filtro_6b(
        "No se encuentra.",
        "Entiendo. ¿Le gustaría que le envíe nuestro catálogo por WhatsApp o correo electrónico?"
    )
    assert resultado4 == False, "❌ FALLO: NO debería activar el filtro"
    print("✅ CORRECTO: Filtro NO activado")

    # Caso 5: Cliente NO dice "no disponible" (NO activar)
    print("\n\n🧪 CASO 5: Cliente NO menciona disponibilidad (NO ACTIVAR)")
    resultado5 = test_filtro_6b(
        "Sí, dígame.",
        "¿Me podría comunicar con el encargado de compras?"
    )
    assert resultado5 == False, "❌ FALLO: NO debería activar el filtro"
    print("✅ CORRECTO: Filtro NO activado")

    print("\n\n" + "=" * 70)
    print("✅ TODOS LOS TESTS PASARON")
    print("=" * 70)
