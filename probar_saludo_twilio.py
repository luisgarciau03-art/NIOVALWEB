# -*- coding: utf-8 -*-
"""
Genera audio del saludo de Bruce usando Twilio TTS (el que usa en producción)
"""
from twilio.rest import Client
import os
from dotenv import load_dotenv

load_dotenv()

# Configuración Twilio
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")

client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

# Mensaje de Bruce (el saludo actual)
mensaje_saludo = """Hola, muy buenas tardes. Mi nombre es Bruce W, le llamo de NIOVAL,
somos distribuidores especializados en productos ferreteros.
¿Me comunico con el encargado de compras o con el dueño del negocio?"""

print("\n" + "="*70)
print("GENERAR AUDIO DEL SALUDO DE BRUCE (TWILIO TTS)")
print("="*70 + "\n")

print(f"Mensaje:\n{mensaje_saludo}\n")
print("Generando audio con voz Polly.Mia (español mexicano)...\n")

try:
    # Generar audio usando Twilio TTS
    # Nota: Esto genera una URL temporal del audio, NO descarga archivo
    recording = client.api.accounts(TWILIO_ACCOUNT_SID).recordings.create(
        recording_status_callback='https://example.com',  # No se usa
        tts_text=mensaje_saludo,
        tts_voice='Polly.Mia',  # Voz que usa Bruce
        tts_language='es-MX'
    )

    print(f" Audio generado!")
    print(f"URL del audio: {recording.url}")
    print(f"\nPuedes escucharlo en tu navegador copiando la URL de arriba")

except Exception as e:
    print(f" Error: {e}")
    print("\nAlternativa: Usa el script de llamada de prueba")
    print("python llamar_produccion.py +52[TU_NUMERO] \"Prueba\"")

print("\n" + "="*70 + "\n")
