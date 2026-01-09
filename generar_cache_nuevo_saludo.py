# -*- coding: utf-8 -*-
"""
Script para pre-generar audio del nuevo saludo (FIX 108)
"""
import requests
import sys

if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

RAILWAY_URL = "https://nioval-webhook-server-production.up.railway.app"

print("\n" + "=" * 70)
print("GENERADOR DE CACHE - NUEVO SALUDO (FIX 108)")
print("=" * 70 + "\n")

# FIX 112: Saludo corto dividido en 2 partes (no saturar al cliente)
# Solo "Hola, buen dia" inicial - El resto después del saludo del cliente
frases_a_generar = [
    {
        "key": "saludo_inicial",
        "texto": "Hola, buen dia",
        "force": True  # Forzar regeneración
    }
]

print(f"📋 Frases a generar: {len(frases_a_generar)}\n")
for i, frase in enumerate(frases_a_generar, 1):
    print(f"   {i}. {frase['key']}")
    print(f"      → {frase['texto'][:70]}...")
    print()

try:
    response = requests.post(
        f"{RAILWAY_URL}/generate-cache",
        json={"frases": frases_a_generar},
        timeout=120
    )

    if response.status_code == 200:
        result = response.json()
        print("✅ Cache generado exitosamente\n")
        print(f"📊 Resultados:")
        print(f"   • Audios generados: {result.get('generados', 0)}")
        print(f"   • Ya existían: {result.get('existentes', 0)}")
        print(f"   • Errores: {result.get('errores', 0)}")

        if result.get('detalles'):
            print(f"\n📝 Detalles:")
            for detalle in result['detalles']:
                print(f"   • {detalle}")
    else:
        print(f"❌ Error: {response.status_code}")
        print(f"   Respuesta: {response.text}")

except requests.exceptions.Timeout:
    print("⏱️ Timeout - el servidor está procesando la solicitud")
    print("   Los audios se están generando en segundo plano")
    print("   Espera 1-2 minutos y verifica en Railway")

except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 70)
