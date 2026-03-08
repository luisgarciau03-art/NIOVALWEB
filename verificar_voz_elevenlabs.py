# -*- coding: utf-8 -*-
"""
Script para verificar la configuración de la voz de ElevenLabs
"""
import os
import sys
from dotenv import load_dotenv
from elevenlabs import ElevenLabs

# Configurar encoding para Windows
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')

load_dotenv()

ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
ELEVENLABS_VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID")

print("\n" + "=" * 70)
print("VERIFICAR VOZ DE ELEVENLABS")
print("=" * 70 + "\n")

if not ELEVENLABS_API_KEY or not ELEVENLABS_VOICE_ID:
    print(" ERROR: Faltan credenciales de ElevenLabs en .env")
    sys.exit(1)

print(f"Voice ID configurado: {ELEVENLABS_VOICE_ID}")
print()

try:
    client = ElevenLabs(api_key=ELEVENLABS_API_KEY)

    # Obtener información de la voz específica
    print("Consultando detalles de la voz...")
    voice = client.voices.get(voice_id=ELEVENLABS_VOICE_ID)

    print("\n" + "=" * 70)
    print("INFORMACIÓN DE LA VOZ")
    print("=" * 70 + "\n")

    print(f"Nombre: {voice.name}")
    print(f"Voice ID: {voice.voice_id}")
    print(f"Categoría: {voice.category}")

    if hasattr(voice, 'labels'):
        print(f"\nEtiquetas:")
        for key, value in voice.labels.items():
            print(f"  - {key}: {value}")

    if hasattr(voice, 'description'):
        print(f"\nDescripción: {voice.description}")

    print("\n" + "=" * 70)
    print("TODAS LAS VOCES DISPONIBLES")
    print("=" * 70 + "\n")

    # Listar todas las voces para comparar
    all_voices = client.voices.get_all()

    print(f"Total de voces: {len(all_voices.voices)}\n")

    # Buscar voces en español
    spanish_voices = []
    for v in all_voices.voices:
        labels = v.labels if hasattr(v, 'labels') else {}
        if labels and any('spanish' in str(val).lower() or 'español' in str(val).lower() or 'es' in str(val).lower() for val in labels.values()):
            spanish_voices.append(v)

    if spanish_voices:
        print("Voces en ESPAÑOL encontradas:\n")
        for v in spanish_voices:
            labels = v.labels if hasattr(v, 'labels') else {}
            accent = labels.get('accent', 'N/A') if labels else 'N/A'
            gender = labels.get('gender', 'N/A') if labels else 'N/A'
            age = labels.get('age', 'N/A') if labels else 'N/A'

            marcador = "  ← ACTUAL" if v.voice_id == ELEVENLABS_VOICE_ID else ""
            print(f"• {v.name}")
            print(f"  ID: {v.voice_id}{marcador}")
            print(f"  Acento: {accent} | Género: {gender} | Edad: {age}")
            print()
    else:
        print("No se encontraron voces específicamente marcadas como español")
        print("\nMostrando primeras 10 voces disponibles:\n")
        for v in all_voices.voices[:10]:
            labels = v.labels if hasattr(v, 'labels') else {}
            marcador = "  ← ACTUAL" if v.voice_id == ELEVENLABS_VOICE_ID else ""
            print(f"• {v.name} (ID: {v.voice_id}){marcador}")
            if labels:
                print(f"  Etiquetas: {labels}")
            print()

    print("=" * 70)
    print("\nPara cambiar la voz, actualiza ELEVENLABS_VOICE_ID en .env")
    print("=" * 70 + "\n")

except Exception as e:
    import traceback
    print(f"\n ERROR: {e}")
    print(f"\nTraceback:")
    print(traceback.format_exc())
    print("\nPosibles causas:")
    print("1. Voice ID inválido")
    print("2. API Key sin permisos")
    print("3. Voz no existe en tu cuenta")
