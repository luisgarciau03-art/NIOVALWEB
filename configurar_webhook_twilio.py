# -*- coding: utf-8 -*-
"""
Script para configurar el webhook de Twilio automaticamente
"""
import os
import sys
from dotenv import load_dotenv
from twilio.rest import Client

# Configurar encoding para Windows
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')

# Cargar variables de entorno
load_dotenv()

print("\n" + "=" * 70)
print("CONFIGURACION DE WEBHOOK EN TWILIO")
print("=" * 70 + "\n")

# Obtener credenciales
account_sid = os.getenv('TWILIO_ACCOUNT_SID')
auth_token = os.getenv('TWILIO_AUTH_TOKEN')
phone_number = os.getenv('TWILIO_PHONE_NUMBER')
webhook_url = os.getenv('WEBHOOK_URL')

if not all([account_sid, auth_token, phone_number, webhook_url]):
    print("ERROR: Faltan variables de entorno en .env")
    exit(1)

print(f"Numero: {phone_number}")
print(f"Webhook URL: {webhook_url}/webhook-voz")
print()

try:
    # Conectar con Twilio
    client = Client(account_sid, auth_token)

    # Buscar el número
    print("Buscando numero en Twilio...")
    numbers = client.incoming_phone_numbers.list(phone_number=phone_number, limit=1)

    if not numbers:
        print(f"ERROR: Numero {phone_number} no encontrado en tu cuenta")
        exit(1)

    number = numbers[0]
    print(f"Numero encontrado: {number.friendly_name}")
    print()

    # Configurar webhook
    print("Configurando webhook...")
    number.update(
        voice_url=f"{webhook_url}/webhook-voz",
        voice_method="POST"
    )

    print("Webhook configurado exitosamente!")
    print()
    print("CONFIGURACION APLICADA:")
    print(f"   Voice URL: {webhook_url}/webhook-voz")
    print(f"   Metodo: POST")
    print()
    print("=" * 70)
    print("WEBHOOK CONFIGURADO - LISTO PARA LLAMADAS")
    print("=" * 70)
    print()

except Exception as e:
    print(f"ERROR: {e}")
    exit(1)
