# -*- coding: utf-8 -*-
"""
Script para forzar pre-generación de audios en Railway
Esto generará todos los audios de respuestas cacheadas con ElevenLabs
"""
import requests
import sys

if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

RAILWAY_URL = "https://nioval-webhook-server-production.up.railway.app"

print("\n" + "=" * 70)
print("GENERADOR DE CACHE DE AUDIOS - BRUCE W")
print("=" * 70 + "\n")

print("Este script forzara la pre-generacion de audios para todas las")
print("respuestas cacheadas. Esto puede tomar 1-2 minutos.")
print()

input("Presiona ENTER para continuar...")

print("\nEnviando request a Railway...")

# FIX 93: Pre-generar los 2 saludos iniciales nuevos
frases_a_generar = [
    {
        "key": "saludo_inicial",
        "texto": "Hola, que tal, buen dia, me comunico de la marca nioval, queria brindar informacion de nuestros productos ferreteros, ¿Se encuentra el encargado o encargada de compras?"
    },
    {
        "key": "saludo_inicial_encargado",
        "texto": "Hola, que tal, buen dia, me comunico de la marca nioval, queria brindar informacion de nuestros productos ferreteros, ¿Con quién tengo el gusto?"
    }
]

print(f"\n📋 Frases a generar: {len(frases_a_generar)}")
for i, frase in enumerate(frases_a_generar, 1):
    print(f"   {i}. {frase['key']}: {frase['texto'][:60]}...")

try:
    # El endpoint /generate-cache pre-genera los audios especificados
    response = requests.post(
        f"{RAILWAY_URL}/generate-cache",
        json={"frases": frases_a_generar},
        timeout=120  # 2 minutos timeout (puede tardar generando audios)
    )

    print(f"Status Code: {response.status_code}\n")

    if response.status_code == 200:
        result = response.json()
        print("=" * 70)
        print("AUDIOS PRE-GENERADOS EXITOSAMENTE")
        print("=" * 70)
        print(f"\n{result.get('message', 'OK')}")
        print(f"\nAudios generados: {result.get('audios_generados', 'N/A')}")
        print()
        print("Ahora las respuestas cacheadas seran INSTANTANEAS (<0.1s)")
        print()
    else:
        print("=" * 70)
        print("ERROR")
        print("=" * 70)
        print(f"\n{response.text}\n")

except requests.Timeout:
    print("\nTIMEOUT: La generacion de audios tardo mas de 2 minutos.")
    print("Esto es normal si hay muchos audios por generar.")
    print("Espera 5 minutos y prueba hacer una llamada de nuevo.")
except Exception as e:
    print(f"\nERROR: {e}")

print("=" * 70 + "\n")
