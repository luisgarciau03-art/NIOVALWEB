#!/usr/bin/env python3
"""
Test FIX 256: No activar "Claro, espero" cuando cliente dice "no se encuentra el encargado ahorita"
"""
import sys
import re

# Fix encoding for Windows console
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')


def test_filtro_5_fix_256(ultimo_cliente):
    """Simula FILTRO 5 con FIX 256 aplicado"""

    # FIX 249/256: Detectar negaciones/rechazos que invalidan "ahorita"
    patrones_negacion = [
        r'cerrado', r'no\s+est[aá]', r'no\s+se\s+encuentra',
        r'no\s+hay', r'no\s+tenemos', r'no\s+puede',
        r'ocupado', r'no\s+disponible',
        # FIX 256: Patrones específicos para encargado
        r'(?:encargado|jefe|gerente).*(?:no\s+est[aá]|sali[oó]|se\s+fue)',
        r'(?:no\s+est[aá]|sali[oó]|se\s+fue).*(?:encargado|jefe|gerente)',
        r'ya\s+sali[oó]', r'se\s+fue', r'est[aá]\s+fuera'
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

    # FIX 249/256: Solo detectar "ahorita" si NO hay negación
    # FIX 256: Corregir bug - usar regex en lugar de 'in'
    if re.search(r'\bahorita\b', ultimo_cliente) and not tiene_negacion:
        patrones_espera.append(r'\bahorita\b')
        ahorita_agregado = True
    else:
        ahorita_agregado = False

    cliente_pide_espera = any(re.search(p, ultimo_cliente) for p in patrones_espera)

    print(f"\n📊 Cliente: '{ultimo_cliente[:80]}'")
    print(f"   tiene_negacion: {tiene_negacion}")
    print(f"   ahorita_agregado: {ahorita_agregado}")
    print(f"   cliente_pide_espera: {cliente_pide_espera}")

    # FIX 249: NO activar filtro si hay negación explícita
    if cliente_pide_espera and not tiene_negacion:
        print(f"   ⏳ FILTRO ACTIVADO")
        return True
    else:
        print(f"   ✅ FILTRO NO ACTIVADO")
        return False


if __name__ == "__main__":
    print("="*70)
    print("TEST FIX 256: 'no se encuentra el encargado ahorita'")
    print("="*70)

    # Caso 1: Del log real (DEBE RECHAZARSE)
    print("\n🧪 CASO 1: 'no se encuentra el encargado ahorita'")
    resultado1 = test_filtro_5_fix_256("pues, sí, no, no se encuentra el encargado ahorita,")
    assert resultado1 == False, "❌ FALLO: NO debería activar 'Claro, espero'"
    print("✅ CORRECTO")

    # Caso 2: "ahorita lo busco" (DEBE ACEPTARSE)
    print("\n🧪 CASO 2: 'ahorita lo busco'")
    resultado2 = test_filtro_5_fix_256("ahorita lo busco")
    assert resultado2 == True, "❌ FALLO: SÍ debería activar 'Claro, espero'"
    print("✅ CORRECTO")

    # Caso 3: "ya salió el encargado ahorita" (DEBE RECHAZARSE)
    print("\n🧪 CASO 3: 'ya salió el encargado ahorita'")
    resultado3 = test_filtro_5_fix_256("ya salió el encargado ahorita")
    assert resultado3 == False, "❌ FALLO: NO debería activar"
    print("✅ CORRECTO")

    # Caso 4: "el encargado se fue ahorita" (DEBE RECHAZARSE)
    print("\n🧪 CASO 4: 'el encargado se fue ahorita'")
    resultado4 = test_filtro_5_fix_256("el encargado se fue ahorita")
    assert resultado4 == False, "❌ FALLO: NO debería activar"
    print("✅ CORRECTO")

    # Caso 5: "ahorita tenemos cerrado" (DEBE RECHAZARSE)
    print("\n🧪 CASO 5: 'ahorita tenemos cerrado'")
    resultado5 = test_filtro_5_fix_256("ahorita tenemos cerrado")
    assert resultado5 == False, "❌ FALLO: NO debería activar"
    print("✅ CORRECTO")

    # Caso 6: "permítame un momento" (DEBE ACEPTARSE)
    print("\n🧪 CASO 6: 'permítame un momento'")
    resultado6 = test_filtro_5_fix_256("permítame un momento")
    assert resultado6 == True, "❌ FALLO: SÍ debería activar"
    print("✅ CORRECTO")

    # Caso 7: "no está disponible ahorita" (DEBE RECHAZARSE)
    print("\n🧪 CASO 7: 'no está disponible ahorita'")
    resultado7 = test_filtro_5_fix_256("no está disponible ahorita")
    assert resultado7 == False, "❌ FALLO: NO debería activar"
    print("✅ CORRECTO")

    print("\n" + "="*70)
    print("✅ TODOS LOS TESTS PASARON")
    print("="*70)
