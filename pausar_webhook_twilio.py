# -*- coding: utf-8 -*-
"""
Script para pausar/despausar el webhook de Twilio
"""
import os
import sys
from dotenv import load_dotenv
from twilio.rest import Client

# Configurar encoding para Windows
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')

load_dotenv()

account_sid = os.getenv('TWILIO_ACCOUNT_SID')
auth_token = os.getenv('TWILIO_AUTH_TOKEN')
phone_number = os.getenv('TWILIO_PHONE_NUMBER')

client = Client(account_sid, auth_token)

print("\n" + "=" * 70)
print("PAUSAR/REANUDAR WEBHOOK DE TWILIO")
print("=" * 70 + "\n")

numbers = client.incoming_phone_numbers.list(phone_number=phone_number, limit=1)
if not numbers:
    print("Error: Numero no encontrado")
    exit(1)

number = numbers[0]
print(f"Numero: {number.phone_number}")
print(f"Webhook actual: {number.voice_url or 'NINGUNO'}\n")

print("Opciones:")
print("1. PAUSAR (eliminar webhook)")
print("2. REANUDAR (restaurar webhook)")
opcion = input("\nSelecciona (1/2): ").strip()

if opcion == "1":
    # Pausar - eliminar webhook
    number.update(voice_url="")
    print("\nWebhook PAUSADO")
    print("Las llamadas no seran procesadas por Bruce")
elif opcion == "2":
    # Reanudar - restaurar webhook
    webhook_url = os.getenv('WEBHOOK_URL')
    number.update(
        voice_url=f"{webhook_url}/webhook-voz",
        voice_method="POST"
    )
    print("\nWebhook REANUDADO")
    print(f"URL: {webhook_url}/webhook-voz")
else:
    print("\nOpcion invalida")

print("\n" + "=" * 70 + "\n")
