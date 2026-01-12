import requests
import base64

# Credenciales
account_sid = "ACddf2b7fafcc4714be7cc3437b905c9dc"
auth_token = "d43c85011fd8d331207d881461d32480"

# Crear autenticación básica
auth = base64.b64encode(f"{account_sid}:{auth_token}".encode()).decode()

# Intentar obtener información de la cuenta
url = f"https://api.twilio.com/2010-04-01/Accounts/{account_sid}.json"
headers = {
    "Authorization": f"Basic {auth}"
}

print("🔍 Verificando credenciales de Twilio...")
print(f"   Account SID: {account_sid}")
print(f"   Auth Token: {auth_token[:8]}...{auth_token[-8:]}")
print()

try:
    response = requests.get(url, headers=headers, timeout=10)
    print(f"📡 Respuesta HTTP: {response.status_code}")
    print()
    
    if response.status_code == 200:
        data = response.json()
        print("✅ CREDENCIALES VÁLIDAS")
        print(f"   Account SID: {data.get('sid')}")
        print(f"   Friendly Name: {data.get('friendly_name')}")
        print(f"   Status: {data.get('status')}")
        print(f"   Type: {data.get('type')}")
    elif response.status_code == 401:
        print("❌ ERROR 401: CREDENCIALES INVÁLIDAS")
        print()
        print("Posibles causas:")
        print("1. El Account SID es incorrecto")
        print("2. El Auth Token es incorrecto o expiró")
        print("3. El Auth Token fue regenerado en Twilio Console")
        print()
        print("Solución:")
        print("1. Ve a https://console.twilio.com")
        print("2. Copia el Account SID exacto")
        print("3. Copia el Auth Token exacto (o genera uno nuevo)")
        print("4. Actualiza las variables en Railway")
    else:
        print(f"❌ ERROR INESPERADO: {response.status_code}")
        print(f"   Respuesta: {response.text[:500]}")
        
except Exception as e:
    print(f"❌ ERROR DE CONEXIÓN: {type(e).__name__}")
    print(f"   Mensaje: {str(e)}")
