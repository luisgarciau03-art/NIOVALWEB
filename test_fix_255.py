#!/usr/bin/env python3
"""
Test para reproducir el problema del FILTRO 5 con "ahorita no se encuentra"
"""
import sys
import re

# Fix encoding for Windows console
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

def test_filtro_5(ultimo_cliente):
    """Simula exactamente la lógica del FILTRO 5"""

    # FIX 249: Detectar negaciones/rechazos que invalidan "ahorita"
    patrones_negacion = [
        r'cerrado', r'no\s+est[aá]', r'no\s+se\s+encuentra',
        r'no\s+hay', r'no\s+tenemos', r'no\s+puede',
        r'ocupado', r'no\s+disponible'
    ]

    tiene_negacion = any(re.search(p, ultimo_cliente) for p in patrones_negacion)

    # FIX 237: Patrones más completos que indican que cliente pide esperar
    patrones_espera = [
        r'perm[ií]t[ae]me', r'perm[ií]tame',
        r'me\s+permite', r'me\s+permites',
        r'esp[eé]r[ae]me', r'espera',
        r'un\s+momento', r'un\s+segundito', r'un\s+segundo',
        r'dame\s+chance', r'd[ée]jame',
        r'aguanta', r'tantito',
    ]

    # FIX 249: Solo detectar "ahorita" si NO hay negación
    # ¡ESTE ES EL BUG! Usa 'in' en lugar de regex
    if r'\bahorita\b' in ultimo_cliente and not tiene_negacion:
        patrones_espera.append(r'\bahorita\b')
        print(f"   ✅ 'ahorita' agregado a patrones_espera")
    else:
        print(f"   ❌ 'ahorita' NO agregado (negacion={tiene_negacion})")

    cliente_pide_espera = any(re.search(p, ultimo_cliente) for p in patrones_espera)

    print(f"\n📊 RESUMEN:")
    print(f"   tiene_negacion: {tiene_negacion}")
    print(f"   patrones_espera: {patrones_espera}")
    print(f"   cliente_pide_espera: {cliente_pide_espera}")

    # FIX 249: NO activar filtro si hay negación explícita
    if cliente_pide_espera and not tiene_negacion:
        print(f"\n⏳ FILTRO ACTIVADO - Cliente pide esperar")
        return True
    elif cliente_pide_espera and tiene_negacion:
        print(f"\n🚫 NO activar espera - Cliente dice 'ahorita' pero con negación")
        return False
    else:
        print(f"\n✅ NO activar espera - No se detectó petición de espera")
        return False


if __name__ == "__main__":
    # Caso del log real
    texto = "ahorita no se encuentra, si gusta, llamar más tarde."
    print(f"🧪 TEST: '{texto}'")
    resultado = test_filtro_5(texto)
    print(f"\n{'='*60}")
    print(f"RESULTADO: {'FILTRO ACTIVADO ❌' if resultado else 'FILTRO NO ACTIVADO ✅'}")
