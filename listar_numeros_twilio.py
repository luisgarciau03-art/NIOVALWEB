# -*- coding: utf-8 -*-
"""
Script para listar todos los numeros en la cuenta de Twilio
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
print("LISTADO DE NUMEROS EN TWILIO")
print("=" * 70 + "\n")

# Obtener credenciales
account_sid = os.getenv('TWILIO_ACCOUNT_SID')
auth_token = os.getenv('TWILIO_AUTH_TOKEN')

if not all([account_sid, auth_token]):
    print("ERROR: Faltan credenciales de Twilio en .env")
    exit(1)

try:
    # Conectar con Twilio
    client = Client(account_sid, auth_token)

    # Listar todos los números
    print("Obteniendo numeros de tu cuenta...")
    numbers = client.incoming_phone_numbers.list()

    if not numbers:
        print("\nNo se encontraron numeros en tu cuenta")
        print("\nCompra un numero en:")
        print("https://console.twilio.com/us1/develop/phone-numbers/manage/search")
    else:
        print(f"\nEncontrados {len(numbers)} numero(s):\n")
        for idx, number in enumerate(numbers, 1):
            print(f"{idx}. Numero: {number.phone_number}")
            print(f"   Nombre: {number.friendly_name}")
            print(f"   SID: {number.sid}")
            print(f"   Voz: {'SI' if number.capabilities.get('voice') else 'NO'}")
            print(f"   SMS: {'SI' if number.capabilities.get('sms') else 'NO'}")
            if number.voice_url:
                print(f"   Webhook: {number.voice_url}")
            else:
                print(f"   Webhook: NO CONFIGURADO")
            print()

    print("=" * 70)

except Exception as e:
    print(f"ERROR: {e}")
    exit(1)
