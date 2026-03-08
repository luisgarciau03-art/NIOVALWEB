# -*- coding: utf-8 -*-
"""
Script para generar cachés de las frases más usadas que NO tienen caché
Usa las estadísticas de /stats para identificar qué cachear
"""
import requests
import os
import sys
import time
from dotenv import load_dotenv
from elevenlabs import ElevenLabs

# Cargar variables de entorno
load_dotenv()

RAILWAY_URL = "https://nioval-webhook-server-production.up.railway.app"
ELEVENLABS_API_KEY = os.getenv('ELEVENLABS_API_KEY')
ELEVENLABS_VOICE_ID = "pNInz6obpgDQGcFmaJgB"  # Voz de Bruce
CACHE_DIR = "audio_cache"

# Crear directorio si no existe
os.makedirs(CACHE_DIR, exist_ok=True)

def obtener_stats():
    """Obtiene estadísticas del servidor Railway"""
    try:
        print(" Consultando estadísticas de Railway...")
        response = requests.get(f"{RAILWAY_URL}/stats", timeout=10)

        if response.status_code == 200:
            # El HTML contiene las estadísticas, parsear manualmente
            html = response.text
            print(" Estadísticas obtenidas")
            return html
        else:
            print(f" Error: {response.status_code}")
            return None
    except Exception as e:
        print(f" Error consultando stats: {e}")
        return None

def parsear_frases_sin_cache(html):
    """Parsea el HTML de /stats para extraer frases sin caché"""
    import re

    frases_sin_cache = []

    # Buscar tabla de frases más usadas
    # Patrón: frase con X usos que NO tiene  (significa no tiene caché)

    # Por ahora, vamos a usar las que sabemos del análisis manual
    # TODO: Mejorar parsing del HTML

    return [
        ("¿Le gustaría que le envíe el catálogo por WhatsApp?", 5),
        ("¿Le gustaría recibir el catálogo por WhatsApp o correo electrónico?", 5),
        ("Manejamos productos de ferretería como griferías, herramientas y cintas. ¿Usted maneja este tipo de productos actualmente en su negocio?", 4),
        ("Entendido. ¿Me podría proporcionar su número de WhatsApp?", 3),
        ("Me comunico de la marca nioval, especializada en productos de ferretería como griferías, herramientas y cintas. ¿Puedo ayudarle con algo específico o enviarle el catálogo?", 3),
        ("Parece que está ocupado. ¿Le gustaría que le envíe el catálogo por WhatsApp para revisarlo cuando tenga tiempo?", 3),
    ]

def generar_cache_key(texto):
    """Genera key de caché (primeras 8 palabras)"""
    palabras = texto.lower().split()[:8]
    key = "_".join(palabras)
    # Limpiar caracteres especiales
    key = key.replace('¿', '').replace('?', '').replace('¡', '').replace(',', '').replace('.', '')
    return key

def generar_audio(texto, cache_key):
    """Genera audio con ElevenLabs"""
    try:
        client = ElevenLabs(api_key=ELEVENLABS_API_KEY)

        print(f"\n Generando: {cache_key}")
        print(f"   Texto ({len(texto.split())} palabras): {texto[:80]}...")

        # Generar audio
        audio_generator = client.text_to_speech.convert(
            voice_id=ELEVENLABS_VOICE_ID,
            text=texto,
            model_id="eleven_multilingual_v2",
            output_format="mp3_44100_128"
        )

        # Guardar en archivo
        filename = f"{cache_key}.mp3"
        filepath = os.path.join(CACHE_DIR, filename)

        with open(filepath, 'wb') as f:
            for chunk in audio_generator:
                f.write(chunk)

        print(f"    Guardado: {filename}")
        return True

    except Exception as e:
        print(f"    Error: {e}")
        return False

def main():
    print("\n" + "="*70)
    print("GENERADOR DE CACHÉS DESDE ESTADÍSTICAS")
    print("="*70 + "\n")

    # Obtener estadísticas
    stats_html = obtener_stats()
    if not stats_html:
        print("\n No se pudieron obtener estadísticas")
        return

    # Parsear frases sin caché
    frases = parsear_frases_sin_cache(stats_html)

    if not frases:
        print("\n Todas las frases frecuentes ya tienen caché")
        return

    print(f"\n Frases sin caché a generar: {len(frases)}")
    print()

    for i, (texto, usos) in enumerate(frases, 1):
        palabras = len(texto.split())
        print(f"   {i}. [{usos} usos] ({palabras}p) {texto[:60]}...")

    print()

    # Verificar créditos
    try:
        client = ElevenLabs(api_key=ELEVENLABS_API_KEY)
        subscription = client.user.get_subscription()

        if hasattr(subscription, 'character_count'):
            caracteres_restantes = subscription.character_limit - subscription.character_count

            print(f" Créditos disponibles: {caracteres_restantes:,} caracteres")

            # Calcular necesarios
            total_caracteres = sum(len(texto) for texto, _ in frases)
            creditos_necesarios = total_caracteres * 7  # ~7 créditos por carácter

            print(f" Créditos necesarios: ~{creditos_necesarios:,} caracteres")
            print()

            if caracteres_restantes < creditos_necesarios:
                print("  ADVERTENCIA: Créditos insuficientes")
                print(f"   Necesitas: {creditos_necesarios:,}")
                print(f"   Tienes: {caracteres_restantes:,}")
                print(f"   Faltante: {creditos_necesarios - caracteres_restantes:,}")
                print()
    except Exception as e:
        print(f"  No se pudo verificar créditos: {e}")
        print()

    respuesta = input("¿Continuar? (s/n): ")
    if respuesta.lower() != 's':
        print("Cancelado.")
        return

    print("\n" + "="*70)
    print("GENERANDO CACHÉS...")
    print("="*70)

    exitosos = 0
    fallidos = 0

    for texto, usos in frases:
        cache_key = generar_cache_key(texto)

        # Verificar si ya existe
        filepath = os.path.join(CACHE_DIR, f"{cache_key}.mp3")
        if os.path.exists(filepath):
            print(f"\n  Saltando: {texto[:50]}... (ya existe)")
            exitosos += 1
            continue

        # Generar
        if generar_audio(texto, cache_key):
            exitosos += 1
        else:
            fallidos += 1

        # Pausa entre requests
        time.sleep(0.5)

    print("\n" + "="*70)
    print("RESUMEN")
    print("="*70)
    print(f"\n Exitosos: {exitosos}/{len(frases)}")
    print(f" Fallidos: {fallidos}/{len(frases)}")
    print()

    if exitosos > 0:
        print(" Cachés generados exitosamente")
        print()
        print(" Próximo paso: Subir a Railway")
        print("   Opción 1: Desplegar completo (automático con git push)")
        print("   Opción 2: Subir solo audio_cache/ al volumen persistente")
        print()
        print("   Los audios locales en audio_cache/ se deben subir a:")
        print("   Railway Volume: /app/audio_cache/")
        print()

if __name__ == "__main__":
    main()
