# -*- coding: utf-8 -*-
"""
Script para pre-generar cachés de las frases más comunes de Bruce
Ejecutar DESPUÉS de recargar créditos de ElevenLabs
"""
import os
import sys
from dotenv import load_dotenv
from elevenlabs import ElevenLabs
import time

# Cargar variables de entorno
load_dotenv()

ELEVENLABS_API_KEY = os.getenv('ELEVENLABS_API_KEY')
ELEVENLABS_VOICE_ID = "pNInz6obpgDQGcFmaJgB"  # Voz de Bruce
CACHE_DIR = "audio_cache"

# Crear directorio si no existe
os.makedirs(CACHE_DIR, exist_ok=True)

# Cliente ElevenLabs
client = ElevenLabs(api_key=ELEVENLABS_API_KEY)

# ============================================================
# FRASES MÁS COMUNES (del análisis de logs)
# ============================================================

FRASES_CRITICAS = {
    # Saludos y presentación
    "presentacion_completa": "Me comunico de la marca nioval, especializada en productos de ferretería como griferías, herramientas y cintas. ¿Puedo ayudarle con algo específico o enviarle el catálogo?",

    "presentacion_corta": "Me comunico de la marca nioval, especializada en productos de ferretería. ¿Se encuentra el encargado de compras?",

    # Respuestas cuando cliente está ocupado
    "ocupado_whatsapp": "Entiendo que está ocupado. ¿Le gustaría que le envíe el catálogo por WhatsApp para revisarlo cuando tenga tiempo?",

    "ocupado_llamar_despues": "Entiendo. ¿Hay un mejor momento para llamar y hablar con el encargado de compras?",

    # Preguntas comunes
    "pregunta_encargado": "¿Se encuentra el encargado o encargada de compras?",

    "pregunta_whatsapp": "¿Le gustaría recibir nuestro catálogo por WhatsApp?",

    "pregunta_catalogo": "¿Puedo enviarle el catálogo completo para que vea todos nuestros productos?",

    # Transiciones y nexos
    "perfecto_adelante": "Perfecto, adelante",

    "si_digame": "Sí, dígame",

    "claro_escucho": "Claro, escucho",

    "entiendo": "Entiendo",

    # Despedidas
    "despedida_completa": "Perfecto, ya lo tengo anotado. Le llegará el catálogo en las próximas horas. Muchas gracias por su tiempo. Que tenga un excelente día.",

    "despedida_corta": "Muchas gracias por su tiempo. Que tenga un excelente día.",

    # Audios de relleno (críticos)
    "dejeme_ver": "Déjeme ver",

    "un_momento": "Un momento por favor",

    "pensando_1": "Mmm",
    "pensando_2": "Déjeme revisar",
    "pensando_3": "Sí, claro",
    "pensando_4": "Perfecto",
    "pensando_5": "Entiendo"
}

def generar_cache_key(texto):
    """Genera key de caché (primeras 8 palabras)"""
    palabras = texto.lower().split()[:8]
    return "_".join(palabras)

def generar_audio(texto, cache_key):
    """Genera audio con ElevenLabs y guarda en caché"""
    try:
        print(f"\n📝 Generando: {cache_key}")
        print(f"   Texto: {texto[:60]}...")

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

        print(f"   ✅ Guardado: {filename}")
        return True

    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False

def main():
    print("\n" + "="*70)
    print("GENERADOR DE CACHÉS - FRASES MÁS COMUNES")
    print("="*70 + "\n")

    print(f"📋 Total frases a generar: {len(FRASES_CRITICAS)}")
    print(f"📂 Directorio: {CACHE_DIR}")
    print(f"🎤 Voz: {ELEVENLABS_VOICE_ID} (Bruce)")
    print()

    # Verificar créditos antes de empezar
    try:
        subscription = client.user.get_subscription()
        if hasattr(subscription, 'character_count'):
            caracteres_restantes = subscription.character_limit - subscription.character_count
            llamadas_estimadas = caracteres_restantes // 300

            print(f"💰 Créditos disponibles: {caracteres_restantes:,} caracteres")
            print(f"📊 Llamadas estimadas: ~{llamadas_estimadas}")

            # Calcular créditos necesarios
            total_caracteres = sum(len(texto) for texto in FRASES_CRITICAS.values())
            print(f"📝 Créditos necesarios: ~{total_caracteres * 7:,} caracteres")
            print()

            if caracteres_restantes < total_caracteres * 7:
                print("⚠️  ADVERTENCIA: Créditos insuficientes para generar todos los cachés")
                print("   Se generarán tantos como sea posible")
                print()
    except Exception as e:
        print(f"⚠️ No se pudo verificar créditos ElevenLabs: {e}")

    respuesta = input("¿Continuar? (s/n): ")
    if respuesta.lower() != 's':
        print("Cancelado.")
        return

    print("\n" + "="*70)
    print("GENERANDO CACHÉS...")
    print("="*70)

    exitosos = 0
    fallidos = 0

    for nombre, texto in FRASES_CRITICAS.items():
        cache_key = generar_cache_key(texto)

        # Verificar si ya existe
        filepath = os.path.join(CACHE_DIR, f"{cache_key}.mp3")
        if os.path.exists(filepath):
            print(f"\n⏭️  Saltando: {nombre} (ya existe)")
            exitosos += 1
            continue

        # Generar
        if generar_audio(texto, cache_key):
            exitosos += 1
        else:
            fallidos += 1

        # Pequeña pausa entre requests
        time.sleep(0.5)

    print("\n" + "="*70)
    print("RESUMEN")
    print("="*70)
    print(f"\n✅ Exitosos: {exitosos}/{len(FRASES_CRITICAS)}")
    print(f"❌ Fallidos: {fallidos}/{len(FRASES_CRITICAS)}")
    print()

    if exitosos > 0:
        print("🎉 Cachés generados exitosamente")
        print("📌 Estos audios ahora se reproducirán instantáneamente (0s delay)")
        print()
        print("Próximo paso: Subir audio_cache/ a Railway")
        print("  1. Comprimir: tar -czf audio_cache.tar.gz audio_cache/")
        print("  2. Subir al volumen persistente de Railway")
        print()

if __name__ == "__main__":
    main()
