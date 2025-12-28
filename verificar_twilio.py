"""
Script de verificación de configuración de Twilio
Verifica que todas las credenciales estén correctas antes de hacer llamadas
"""
import os
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

print("\n" + "=" * 70)
print("🔍 VERIFICACIÓN DE CONFIGURACIÓN TWILIO")
print("=" * 70 + "\n")

# 1. Verificar variables de entorno
print("📋 PASO 1: Verificando variables de entorno...\n")

account_sid = os.getenv('TWILIO_ACCOUNT_SID')
auth_token = os.getenv('TWILIO_AUTH_TOKEN')
phone_number = os.getenv('TWILIO_PHONE_NUMBER')
webhook_url = os.getenv('WEBHOOK_URL')

variables_ok = True

if account_sid:
    print(f"   ✅ TWILIO_ACCOUNT_SID: {account_sid[:8]}...{account_sid[-4:]}")
else:
    print(f"   ❌ TWILIO_ACCOUNT_SID: NO CONFIGURADO")
    variables_ok = False

if auth_token:
    print(f"   ✅ TWILIO_AUTH_TOKEN: {'*' * 8}...{auth_token[-4:]}")
else:
    print(f"   ❌ TWILIO_AUTH_TOKEN: NO CONFIGURADO")
    variables_ok = False

if phone_number:
    print(f"   ✅ TWILIO_PHONE_NUMBER: {phone_number}")
else:
    print(f"   ❌ TWILIO_PHONE_NUMBER: NO CONFIGURADO")
    variables_ok = False

if webhook_url:
    print(f"   ✅ WEBHOOK_URL: {webhook_url}")
else:
    print(f"   ⚠️  WEBHOOK_URL: NO CONFIGURADO (opcional para testing)")

print()

if not variables_ok:
    print("❌ FALTAN VARIABLES DE ENTORNO")
    print("\n📝 Agrega estas líneas al archivo .env:\n")
    print("TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx")
    print("TWILIO_AUTH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx")
    print("TWILIO_PHONE_NUMBER=+52XXXXXXXXXX")
    print("WEBHOOK_URL=https://tu-url-ngrok.ngrok-free.app")
    print("\n" + "=" * 70 + "\n")
    exit(1)

# 2. Probar conexión con Twilio
print("📞 PASO 2: Probando conexión con Twilio...\n")

try:
    from twilio.rest import Client

    client = Client(account_sid, auth_token)

    # Obtener información de la cuenta
    print("   🔄 Conectando con Twilio...")
    account = client.api.accounts(account_sid).fetch()

    print(f"   ✅ Conexión exitosa")
    print(f"   ✅ Account Name: {account.friendly_name}")
    print(f"   ✅ Account Status: {account.status}")

except ImportError:
    print("   ❌ ERROR: Biblioteca 'twilio' no instalada")
    print("\n   Instala con: pip install twilio")
    print("\n" + "=" * 70 + "\n")
    exit(1)

except Exception as e:
    print(f"   ❌ ERROR DE CONEXIÓN: {e}")
    print("\n   Verifica que tu ACCOUNT_SID y AUTH_TOKEN sean correctos")
    print("   Obtenlos desde: https://console.twilio.com/")
    print("\n" + "=" * 70 + "\n")
    exit(1)

print()

# 3. Verificar número de teléfono
print("📱 PASO 3: Verificando número de teléfono...\n")

try:
    # Buscar el número en la cuenta
    numbers = client.incoming_phone_numbers.list(phone_number=phone_number, limit=1)

    if numbers:
        number = numbers[0]
        print(f"   ✅ Número encontrado: {number.phone_number}")
        print(f"   ✅ Friendly Name: {number.friendly_name}")
        print(f"   ✅ Capabilities:")
        print(f"      - Voice: {'✅' if number.capabilities.get('voice') else '❌'}")
        print(f"      - SMS: {'✅' if number.capabilities.get('sms') else '❌'}")

        # Verificar webhook configurado
        if number.voice_url:
            print(f"\n   ✅ Voice Webhook configurado: {number.voice_url}")
            print(f"   ✅ Método: {number.voice_method}")
        else:
            print(f"\n   ⚠️  Voice Webhook NO configurado")
            print(f"      Configúralo en: https://console.twilio.com/us1/develop/phone-numbers/manage/incoming")

    else:
        print(f"   ❌ Número {phone_number} no encontrado en tu cuenta Twilio")
        print(f"\n   Verifica que:")
        print(f"   1. El número esté comprado en tu cuenta")
        print(f"   2. El formato sea correcto (ej: +523312345678)")
        print(f"\n   Compra un número en: https://console.twilio.com/us1/develop/phone-numbers/manage/search")
        print("\n" + "=" * 70 + "\n")
        exit(1)

except Exception as e:
    print(f"   ❌ ERROR: {e}")
    print("\n" + "=" * 70 + "\n")
    exit(1)

print()

# 4. Verificar saldo
print("💰 PASO 4: Verificando saldo de la cuenta...\n")

try:
    balance = client.balance.fetch()

    # Convertir balance a float
    saldo = float(balance.balance)

    print(f"   ✅ Saldo actual: ${saldo:.2f} {balance.currency}")

    if saldo < 5.0:
        print(f"   ⚠️  ADVERTENCIA: Saldo bajo")
        print(f"      Costo estimado por llamada: $0.10-0.25 USD")
        print(f"      Recarga en: https://console.twilio.com/billing")
    else:
        llamadas_estimadas = int(saldo / 0.20)
        print(f"   ✅ Suficiente para ~{llamadas_estimadas} llamadas (estimado)")

except Exception as e:
    print(f"   ⚠️  No se pudo obtener saldo: {e}")

print()

# 5. Verificar otras dependencias
print("📦 PASO 5: Verificando dependencias del sistema...\n")

dependencias = {
    'openai': 'OpenAI API',
    'elevenlabs': 'ElevenLabs TTS',
    'gspread': 'Google Sheets API',
    'google.oauth2': 'Google Auth',
}

dependencias_ok = True

for modulo, nombre in dependencias.items():
    try:
        __import__(modulo)
        print(f"   ✅ {nombre}: Instalado")
    except ImportError:
        print(f"   ❌ {nombre}: NO instalado")
        dependencias_ok = False

if not dependencias_ok:
    print("\n   Instala las dependencias faltantes con:")
    print("   pip install -r requirements.txt")

print()

# 6. Verificar webhook (si está configurado)
if webhook_url:
    print("🌐 PASO 6: Verificando webhook...\n")

    # Solo verificar formato
    if webhook_url.startswith('http://') or webhook_url.startswith('https://'):
        print(f"   ✅ URL válida: {webhook_url}")

        if 'ngrok' in webhook_url:
            print(f"   ⚠️  Usando ngrok (desarrollo)")
            print(f"      Asegúrate de que ngrok esté corriendo: ngrok http 5000")
        else:
            print(f"   ✅ URL de producción detectada")

        print(f"\n   📝 Configura esta URL en Twilio Console:")
        print(f"      1. Ve a: https://console.twilio.com/us1/develop/phone-numbers/manage/incoming")
        print(f"      2. Selecciona tu número: {phone_number}")
        print(f"      3. En 'A CALL COMES IN':")
        print(f"         - URL: {webhook_url}/webhook-voz")
        print(f"         - Método: HTTP POST")
    else:
        print(f"   ❌ URL inválida: {webhook_url}")
        print(f"      Debe empezar con http:// o https://")

    print()

# Resumen final
print("=" * 70)
print("📊 RESUMEN DE VERIFICACIÓN")
print("=" * 70 + "\n")

print("✅ Variables de entorno: OK")
print("✅ Conexión con Twilio: OK")
print("✅ Número de teléfono: OK")

if saldo >= 5.0:
    print("✅ Saldo suficiente: OK")
else:
    print("⚠️  Saldo bajo: Considera recargar")

if dependencias_ok:
    print("✅ Dependencias: OK")
else:
    print("⚠️  Dependencias: Faltan algunas")

if webhook_url:
    print("✅ Webhook configurado: OK")
else:
    print("⚠️  Webhook: No configurado (opcional)")

print("\n" + "=" * 70)
print("🎉 SISTEMA LISTO PARA HACER LLAMADAS CON TWILIO")
print("=" * 70 + "\n")

print("📝 SIGUIENTE PASO:")
print("   1. Asegúrate de que servidor_llamadas.py esté corriendo:")
print("      python servidor_llamadas.py")
print("\n   2. Si usas ngrok, asegúrate de que esté corriendo:")
print("      ngrok http 5000")
print("\n   3. Ejecuta el sistema de llamadas:")
print("      python sistema_llamadas_nioval.py")

print("\n" + "=" * 70 + "\n")
