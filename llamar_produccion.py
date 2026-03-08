# -*- coding: utf-8 -*-
"""
Script para hacer llamadas desde Railway (produccion)
Uso: py llamar_produccion.py +523312345678 "Ferreteria Lopez"
"""
import requests
import sys

# Configurar encoding para Windows
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')

# URL de Railway
RAILWAY_URL = "https://nioval-webhook-server-production.up.railway.app"

# Verificar argumentos
if len(sys.argv) < 2:
    print("\nUso: py llamar_produccion.py <telefono> [nombre_negocio]")
    print("\nEjemplo: py llamar_produccion.py +523312345678 \"Ferreteria Lopez\"")
    print()
    sys.exit(1)

telefono = sys.argv[1]
nombre = sys.argv[2] if len(sys.argv) > 2 else "cliente"

print("\n" + "=" * 70)
print("LLAMADA EN PRODUCCION (RAILWAY)")
print("=" * 70 + "\n")
print(f"Destino: {telefono}")
print(f"Nombre: {nombre}")
print(f"Servidor: {RAILWAY_URL}")
print()

# Preparar datos
data = {
    "telefono": telefono,
    "nombre_negocio": nombre
}

try:
    print("Enviando request a Railway...")
    response = requests.post(
        f"{RAILWAY_URL}/iniciar-llamada",
        json=data,
        timeout=30
    )

    print(f"Status Code: {response.status_code}\n")

    if response.status_code == 200:
        result = response.json()
        print("=" * 70)
        print("LLAMADA INICIADA EXITOSAMENTE")
        print("=" * 70)
        print(f"\nCall SID: {result.get('call_id', 'N/A')}")
        print(f"Status: {result.get('status', 'N/A')}")
        print(f"\nLa llamada se esta realizando...")
        print("\nMonitorea en:")
        print("- Railway: https://railway.app")
        print("- Twilio: https://console.twilio.com/us1/monitor/logs/calls")
        print()
    else:
        print("=" * 70)
        print("ERROR")
        print("=" * 70)
        print(f"\n{response.text}\n")

except Exception as e:
    print(f"ERROR: {e}")

print("=" * 70 + "\n")
