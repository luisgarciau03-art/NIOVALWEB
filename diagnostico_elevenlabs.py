"""
Script de diagnostico para verificar estado de ElevenLabs
"""
import os
import sys
from dotenv import load_dotenv

# Forzar UTF-8 para evitar problemas de encoding
sys.stdout.reconfigure(encoding='utf-8')

# Cargar variables de entorno
load_dotenv()

ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
ELEVENLABS_VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID")

print("=" * 60)
print("DIAGNOSTICO DE ELEVENLABS")
print("=" * 60)

# 1. Verificar API Key
if ELEVENLABS_API_KEY:
    print(f"[OK] ELEVENLABS_API_KEY: Configurada ({ELEVENLABS_API_KEY[:10]}...)")
else:
    print("[ERROR] ELEVENLABS_API_KEY: NO CONFIGURADA")

# 2. Verificar Voice ID
if ELEVENLABS_VOICE_ID:
    print(f"[OK] ELEVENLABS_VOICE_ID: {ELEVENLABS_VOICE_ID}")
else:
    print("[ERROR] ELEVENLABS_VOICE_ID: NO CONFIGURADA")

# 3. Intentar importar cliente de ElevenLabs
try:
    from elevenlabs import ElevenLabs
    print("[OK] Libreria elevenlabs importada correctamente")

    # 4. Crear cliente
    try:
        client = ElevenLabs(api_key=ELEVENLABS_API_KEY)
        print("[OK] Cliente ElevenLabs creado")

        # 5. Verificar cuota disponible
        try:
            # Intentar obtener info de la cuenta
            print("\n[INFO] Verificando cuota de API...")

            # Hacer una peticion de prueba pequeña
            audio_generator = client.text_to_speech.convert(
                voice_id=ELEVENLABS_VOICE_ID,
                text="Prueba",
                model_id="eleven_multilingual_v2",
                output_format="mp3_44100_128"
            )

            # Consumir el generador
            audio_bytes = b""
            for chunk in audio_generator:
                audio_bytes += chunk

            print(f"[OK] Prueba exitosa - Audio generado ({len(audio_bytes)} bytes)")

        except Exception as e:
            print(f"[ERROR] Error al generar audio de prueba: {e}")
            print(f"   Tipo de error: {type(e).__name__}")

            # Verificar si es error de cuota
            error_str = str(e).lower()
            if "quota" in error_str or "limit" in error_str or "credit" in error_str:
                print("   [ALERTA] POSIBLE PROBLEMA: Sin cuota/creditos en ElevenLabs")
            elif "unauthorized" in error_str or "api key" in error_str:
                print("   [ALERTA] POSIBLE PROBLEMA: API Key invalida")
            elif "voice" in error_str or "not found" in error_str:
                print("   [ALERTA] POSIBLE PROBLEMA: Voice ID invalido")

    except Exception as e:
        print(f"[ERROR] Error al crear cliente ElevenLabs: {e}")

except ImportError as e:
    print(f"[ERROR] Error al importar elevenlabs: {e}")

print("\n" + "=" * 60)
print("RECOMENDACIONES:")
print("=" * 60)

if not ELEVENLABS_API_KEY:
    print("1. Configura ELEVENLABS_API_KEY en el archivo .env")

if not ELEVENLABS_VOICE_ID:
    print("2. Configura ELEVENLABS_VOICE_ID en el archivo .env")

print("\nPara verificar tu cuota de ElevenLabs:")
print("👉 https://elevenlabs.io/app/subscription")
print("\n" + "=" * 60)
