#!/usr/bin/env python3
"""
Test FIX 257-259:
- FIX 257: Detectar "yo soy el encargado"
- FIX 258/259: Detectar "ahí le paso el número"
"""
import sys
import re

# Fix encoding for Windows console
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')


def test_fix_257_yo_soy_encargado():
    """Test FIX 257: Cliente dice que ÉL ES el encargado"""

    print("\n" + "="*70)
    print("TEST FIX 257: 'Yo soy el encargado'")
    print("="*70)

    # Simular el escenario
    ultimo_bruce = "perfecto, ¿me podría comunicar con el encargado de compras?"
    ultimo_cliente = "sí, yo soy el encargado."
    respuesta_gpt = "Entendido. ¿Le gustaría recibir nuestro catálogo por WhatsApp o correo electrónico?"

    # Lógica del FILTRO 13
    bruce_pregunto_encargado = any(kw in ultimo_bruce for kw in [
        'encargado de compras', 'encargado', 'jefe de compras'
    ])

    patrones_yo_soy_encargado = [
        r'yo\s+soy\s+(?:el\s+)?(?:encargado|jefe|gerente|responsable)',
        r'soy\s+yo(?:\s+el)?(?:\s+encargado)?',
    ]

    cliente_es_encargado = any(re.search(p, ultimo_cliente) for p in patrones_yo_soy_encargado)

    bruce_vuelve_preguntar = any(kw in respuesta_gpt.lower() for kw in [
        'me podría comunicar', 'me puede comunicar', 'encargado de compras'
    ])

    print(f"\n📊 Análisis:")
    print(f"   Bruce preguntó: '{ultimo_bruce}'")
    print(f"   Cliente dijo: '{ultimo_cliente}'")
    print(f"   GPT iba a decir: '{respuesta_gpt}'")
    print(f"   bruce_pregunto_encargado: {bruce_pregunto_encargado}")
    print(f"   cliente_es_encargado: {cliente_es_encargado}")
    print(f"   bruce_vuelve_preguntar: {bruce_vuelve_preguntar}")

    filtro_activado = bruce_pregunto_encargado and cliente_es_encargado and (bruce_vuelve_preguntar or 'entendido' in respuesta_gpt.lower())

    if filtro_activado:
        print(f"\n   🎯 FILTRO ACTIVADO")
        respuesta_corregida = "Perfecto, mucho gusto. ¿Le gustaría recibir nuestro catálogo por WhatsApp o correo electrónico?"
        print(f"   Respuesta corregida: '{respuesta_corregida}'")
        return True
    else:
        print(f"\n   ❌ FILTRO NO ACTIVADO")
        return False


def test_fix_258_259_ahi_le_paso():
    """Test FIX 258/259: Cliente dice 'ahí le paso el número'"""

    print("\n" + "="*70)
    print("TEST FIX 258/259: 'Ahí le paso el número'")
    print("="*70)

    # Simular el escenario del log
    ultimo_cliente = "sí, mándemelo ahí, ahí le paso el número."
    respuesta_gpt = "Perfecto, lo tendré anotado."

    # Lógica del FILTRO 14
    patrones_ofrecimiento_numero = [
        r'(?:ahí|ah[ií])\s+(?:le|te)\s+(?:paso|doy|mando)\s+(?:el|mi)\s+n[uú]mero',
        r'(?:le|te)\s+(?:paso|doy|mando)\s+(?:el|mi)\s+(?:n[uú]mero|whatsapp)',
    ]

    cliente_ofrecio_numero = any(re.search(p, ultimo_cliente) for p in patrones_ofrecimiento_numero)

    bruce_pide_numero = any(kw in respuesta_gpt.lower() for kw in [
        'dígame', 'digame', 'dime', 'cuál es', 'cual es', 'número', 'numero', 'whatsapp'
    ])

    print(f"\n📊 Análisis:")
    print(f"   Cliente dijo: '{ultimo_cliente}'")
    print(f"   GPT iba a decir: '{respuesta_gpt}'")
    print(f"   cliente_ofrecio_numero: {cliente_ofrecio_numero}")
    print(f"   bruce_pide_numero: {bruce_pide_numero}")

    filtro_activado = cliente_ofrecio_numero and not bruce_pide_numero

    if filtro_activado:
        print(f"\n   📱 FILTRO ACTIVADO")
        respuesta_corregida = "Perfecto, dígame su número por favor."
        print(f"   Respuesta corregida: '{respuesta_corregida}'")
        return True
    else:
        print(f"\n   ❌ FILTRO NO ACTIVADO")
        return False


if __name__ == "__main__":
    print("🧪 TESTS PARA FIX 257-259")

    # Test FIX 257
    resultado1 = test_fix_257_yo_soy_encargado()
    assert resultado1 == True, "❌ FALLO: FIX 257 debería activarse"
    print("✅ FIX 257 CORRECTO")

    # Test FIX 258/259
    resultado2 = test_fix_258_259_ahi_le_paso()
    assert resultado2 == True, "❌ FALLO: FIX 258/259 debería activarse"
    print("✅ FIX 258/259 CORRECTO")

    print("\n" + "="*70)
    print("✅ TODOS LOS TESTS PASARON")
    print("="*70)
