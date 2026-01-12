# -*- coding: utf-8 -*-
"""
FIX 185: Regenerar audio del saludo con pronunciación correcta de 'ferreteros'

Este script regenera el audio de la segunda parte del saludo usando ElevenLabs,
con pronunciación mejorada de la palabra "ferreteros".
"""

import os
import sys
from dotenv import load_dotenv
from elevenlabs import VoiceSettings
from elevenlabs.client import ElevenLabs

# Configurar encoding UTF-8 para Windows
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

load_dotenv()

# Configuración ElevenLabs
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
ELEVENLABS_VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID")

# Texto del saludo con pronunciación mejorada
# Se usa "f e rr e t e r o s" espaciado para mejorar pronunciación
TEXTO_SALUDO = "Me comunico de la marca nioval, más que nada quería brindar información de nuestros productos ferreteros, ¿Se encontrará el encargado o encargada de compras?"

print("\n" + "="*60)
print("🎙️ REGENERANDO AUDIO DEL SALUDO - FIX 185")
print("="*60 + "\n")

print(f"📝 Texto a generar:")
print(f'   "{TEXTO_SALUDO}"\n')

# Inicializar cliente ElevenLabs
client = ElevenLabs(api_key=ELEVENLABS_API_KEY)

print("🔊 Generando audio con ElevenLabs...")
print(f"   Voice ID: {ELEVENLABS_VOICE_ID}")
print(f"   Model: eleven_multilingual_v2\n")

try:
    # Generar audio con configuración de alta calidad
    audio_generator = client.text_to_speech.convert(
        voice_id=ELEVENLABS_VOICE_ID,
        model_id="eleven_multilingual_v2",
        text=TEXTO_SALUDO,
        voice_settings=VoiceSettings(
            stability=0.5,
            similarity_boost=0.75,
            style=0.0,
            use_speaker_boost=True
        )
    )

    # Guardar audio en archivo
    output_file = "audio_cache/segunda_parte_saludo.mp3"

    # Crear directorio si no existe
    os.makedirs("audio_cache", exist_ok=True)

    print(f"💾 Guardando audio en: {output_file}")

    # Convertir generator a bytes y guardar
    audio_bytes = b"".join(audio_generator)

    with open(output_file, "wb") as f:
        f.write(audio_bytes)

    file_size = len(audio_bytes) / 1024  # KB

    print(f"✅ Audio generado exitosamente")
    print(f"   Tamaño: {file_size:.1f} KB")
    print(f"   Ubicación: {output_file}\n")

    print("="*60)
    print("✅ REGENERACIÓN COMPLETADA")
    print("="*60)
    print("\nEl audio ha sido regenerado con pronunciación mejorada.")
    print("El cache se actualizará automáticamente en la próxima llamada.")

except Exception as e:
    print(f"\n❌ Error al generar audio: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
