#!/usr/bin/env python3
"""
Debug FIX 256: Por qué se activó "Claro, espero" con "no se encuentra el encargado ahorita"
"""
import sys
import re

# Fix encoding for Windows console
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')


def test_filtro_5_exacto(ultimo_cliente):
    """Simula EXACTAMENTE la lógica del FILTRO 5 (líneas 1937-1970)"""

    print(f"\n{'='*70}")
    print(f"TEXTO DEL CLIENTE: '{ultimo_cliente}'")
    print(f"{'='*70}")

    # FIX 249: Detectar negaciones/rechazos que invalidan "ahorita"
    patrones_negacion = [
        r'cerrado', r'no\s+est[aá]', r'no\s+se\s+encuentra',
        r'no\s+hay', r'no\s+tenemos', r'no\s+puede',
        r'ocupado', r'no\s+disponible'
    ]

    tiene_negacion = any(re.search(p, ultimo_cliente) for p in patrones_negacion)
    print(f"\n1️⃣ Verificar negaciones:")
    for p in patrones_negacion:
        if re.search(p, ultimo_cliente):
            print(f"   ✅ Match: {p}")
    print(f"   → tiene_negacion = {tiene_negacion}")

    # FIX 237: Patrones más completos que indican que cliente pide esperar
    patrones_espera = [
        r'perm[ií]t[ae]me', r'perm[ií]tame',
        r'me\s+permite', r'me\s+permites',
        r'esp[eé]r[ae]me', r'espera',
        r'un\s+momento', r'un\s+segundito', r'un\s+segundo',
        r'dame\s+chance', r'd[ée]jame',
        r'aguanta', r'tantito',
    ]

    print(f"\n2️⃣ Patrones de espera iniciales:")
    print(f"   {patrones_espera}")

    # FIX 249: Solo detectar "ahorita" si NO hay negación
    # 🐛 BUG: Usa 'in' en lugar de regex
    print(f"\n3️⃣ Verificar 'ahorita':")
    metodo_incorrecto = r'\bahorita\b' in ultimo_cliente
    metodo_correcto = bool(re.search(r'\bahorita\b', ultimo_cliente))
    print(f"   Método incorrecto (in): {metodo_incorrecto}")
    print(f"   Método correcto (regex): {metodo_correcto}")
    print(f"   tiene_negacion: {tiene_negacion}")

    if r'\bahorita\b' in ultimo_cliente and not tiene_negacion:
        patrones_espera.append(r'\bahorita\b')
        print(f"   ✅ 'ahorita' agregado a patrones_espera")
    else:
        print(f"   ❌ 'ahorita' NO agregado")

    print(f"\n4️⃣ Verificar si cliente pide espera:")
    for p in patrones_espera:
        if re.search(p, ultimo_cliente):
            print(f"   ✅ Match: {p}")

    cliente_pide_espera = any(re.search(p, ultimo_cliente) for p in patrones_espera)
    print(f"   → cliente_pide_espera = {cliente_pide_espera}")

    # FIX 249: NO activar filtro si hay negación explícita
    print(f"\n5️⃣ Decisión final:")
    print(f"   cliente_pide_espera = {cliente_pide_espera}")
    print(f"   tiene_negacion = {tiene_negacion}")

    if cliente_pide_espera and not tiene_negacion:
        print(f"\n   ⏳ FILTRO ACTIVADO - Cliente pide esperar")
        print(f"   Respuesta: 'Claro, espero.'")
        return True
    elif cliente_pide_espera and tiene_negacion:
        print(f"\n   🚫 NO activar espera - Cliente dice 'ahorita' pero con negación")
        return False
    else:
        print(f"\n   ✅ NO activar espera - No se detectó petición de espera")
        return False


if __name__ == "__main__":
    # Caso del log real
    texto = "pues, sí, no, no se encuentra el encargado ahorita,"

    print("🔍 ANÁLISIS DEL BUG FIX 256")
    resultado = test_filtro_5_exacto(texto)

    print(f"\n{'='*70}")
    print(f"RESULTADO: {'FILTRO ACTIVADO ❌ (MAL)' if resultado else 'FILTRO NO ACTIVADO ✅ (BIEN)'}")
    print(f"{'='*70}")
