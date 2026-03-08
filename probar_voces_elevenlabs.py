# -*- coding: utf-8 -*-
"""
Script para probar diferentes voces de ElevenLabs y compararlas
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

print("\n" + "=" * 70)
print("PROBAR VOCES DE ELEVENLABS - COMPARACIÓN")
print("=" * 70 + "\n")

# Texto de prueba con palabras problemáticas
texto_prueba = """Hola, muy buenas tardes. Mi nombre es Bruce W, le llamo de NIOVAL,
somos distribuidores especializados en productos de ferretería.
Tenemos cinta para goteras, griferías completas y herramientas.
El primer pedido de mil quinientos pesos incluye envío gratis."""

print("Texto de prueba:")
print("-" * 70)
print(texto_prueba)
print("-" * 70 + "\n")

# Voces mexicanas a probar
voces_probar = [
    {
        "nombre": "Enrique Mondragón",
        "id": "iDEmt5MnqUotdwCIVplo",
        "descripcion": "es-MX, middle-aged, elegant"
    },
    {
        "nombre": "Mateo Aragon",
        "id": "vPrtQbTwtAoP87VnQmID",
        "descripcion": "Mexican accent, young, warm"
    }
]

client = ElevenLabs(api_key=ELEVENLABS_API_KEY)

# Probar con diferentes modelos
modelos = [
    {
        "nombre": "Turbo v2 (actual)",
        "id": "eleven_turbo_v2",
        "descripcion": "Más rápido, puede sacrificar calidad"
    },
    {
        "nombre": "Multilingual v2",
        "id": "eleven_multilingual_v2",
        "descripcion": "Mejor calidad, más lento, soporta español nativo"
    }
]

os.makedirs("pruebas_voces", exist_ok=True)

for voz in voces_probar:
    print(f"\n{'='*70}")
    print(f"VOZ: {voz['nombre']}")
    print(f"Descripción: {voz['descripcion']}")
    print(f"{'='*70}\n")

    for modelo in modelos:
        print(f"  Probando con modelo: {modelo['nombre']}...")
        print(f"  ({modelo['descripcion']})")

        try:
            # Generar audio
            audio_generator = client.text_to_speech.convert(
                voice_id=voz["id"],
                text=texto_prueba,
                model_id=modelo["id"],
                output_format="mp3_44100_128"
            )

            # Guardar archivo
            filename = f"pruebas_voces/{voz['nombre'].replace(' ', '_')}_{modelo['nombre'].replace(' ', '_')}.mp3"

            with open(filename, 'wb') as f:
                for chunk in audio_generator:
                    f.write(chunk)

            print(f"   Guardado: {filename}")

        except Exception as e:
            print(f"   Error: {e}")

        print()

print("\n" + "=" * 70)
print("PRUEBAS COMPLETADAS")
print("=" * 70)
print(f"\nArchivos guardados en: {os.path.abspath('pruebas_voces')}")
print("\nESCUCHA LOS ARCHIVOS Y COMPARA:")
print("1. ¿Cuál suena más nativo mexicano?")
print("2. ¿Cuál pronuncia mejor 'ferretería' y 'griferías'?")
print("3. ¿Turbo v2 o Multilingual v2 suena mejor?")
print("\nSi Multilingual v2 suena mejor, cambiaremos el modelo en producción.")
print("=" * 70 + "\n")
