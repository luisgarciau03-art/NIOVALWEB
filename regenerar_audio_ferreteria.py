"""
FIX 276: Regenerar audio con pronunciación correcta de ferretería/grifería

Frase a regenerar:
"Manejamos una variedad de productos de ferretería, como griferías, cintas y herramientas."
"""

import os
import sys
import hashlib
from elevenlabs.client import ElevenLabs
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# Configuración
ELEVENLABS_API_KEY = os.getenv('ELEVENLABS_API_KEY')
ELEVENLABS_VOICE_ID = "pNInz6obpgDQGcFmaJgB"  # Adam (voz de Bruce)
AUDIO_CACHE_DIR = "audio_cache"

# Configurar encoding para Windows
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

elevenlabs_client = ElevenLabs(api_key=ELEVENLABS_API_KEY)


def corregir_pronunciacion(texto):
    """Aplica correcciones fonéticas para mejorar pronunciación"""
    correcciones = {
        # Palabras problemáticas con RR
        "ferreteros": "fe-rre-te-ros",
        "ferretería": "fe-rre-te-ría",
        "ferreterías": "fe-rre-te-rías",
        "tapagoteras": "ta-pa-go-te-ras",
        "grifería": "gri-fe-ría",
        "griferías": "gri-fe-rías",
        "herramientas": "he-rra-mien-tas",
    }

    texto_corregido = texto
    for original, reemplazo in correcciones.items():
        texto_corregido = texto_corregido.replace(original, reemplazo)

    return texto_corregido


def generar_audio_id(texto):
    """Genera ID único para el audio basado en el texto"""
    return hashlib.md5(texto.encode('utf-8')).hexdigest()[:12]


def main():
    print("=" * 80)
    print("FIX 276: REGENERAR AUDIO CON PRONUNCIACIÓN CORRECTA")
    print("=" * 80)
    print()

    if not ELEVENLABS_API_KEY:
        print(" ERROR: Variable ELEVENLABS_API_KEY no configurada")
        return

    # Frase a regenerar
    texto_original = "Manejamos una variedad de productos de ferretería, como griferías, cintas y herramientas."

    print(f" Texto original: {texto_original}")

    # Aplicar corrección de pronunciación
    texto_corregido = corregir_pronunciacion(texto_original)
    print(f" Texto corregido: {texto_corregido}")

    try:
        # Generar nuevo audio con ElevenLabs
        print(f"\n Generando nuevo audio con ElevenLabs...")
        audio_generator = elevenlabs_client.text_to_speech.convert(
            voice_id=ELEVENLABS_VOICE_ID,
            text=texto_corregido,
            model_id="eleven_multilingual_v2",
            output_format="mp3_44100_128"
        )

        # Guardar audio
        audio_id = generar_audio_id(texto_original)
        nombre_archivo = f"variedad_ferreteria_{audio_id}.mp3"
        ruta = os.path.join(AUDIO_CACHE_DIR, nombre_archivo)

        os.makedirs(AUDIO_CACHE_DIR, exist_ok=True)

        with open(ruta, 'wb') as f:
            for chunk in audio_generator:
                if chunk:
                    f.write(chunk)

        print(f"\n Audio regenerado exitosamente!")
        print(f" Archivo: {nombre_archivo}")
        print(f" Ruta: {ruta}")

        # Verificar tamaño
        tamano = os.path.getsize(ruta)
        print(f" Tamaño: {tamano / 1024:.1f} KB")

    except Exception as e:
        print(f" ERROR al regenerar audio: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
