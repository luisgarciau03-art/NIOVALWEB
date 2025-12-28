# -*- coding: utf-8 -*-
"""
Script de prueba para hacer una llamada desde Railway (produccion)
"""
import requests
import sys

# Configurar encoding para Windows
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')

# URL de tu servidor en Railway
RAILWAY_URL = "https://nioval-webhook-server-production.up.railway.app"

print("\n" + "=" * 70)
print("PRUEBA DE LLAMADA EN PRODUCCION (RAILWAY)")
print("=" * 70 + "\n")

# Solicitar datos de la llamada
print("Ingresa los datos para la llamada de prueba:\n")
telefono = input("Telefono destino (ej: +523312345678): ").strip()
nombre = input("Nombre del negocio (ej: Ferreteria Lopez): ").strip() or "cliente"

print(f"\n{'='*70}")
print("INICIANDO LLAMADA...")
print(f"{'='*70}\n")
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
    # Hacer request al servidor de Railway
    print("Enviando request a Railway...")
    response = requests.post(
        f"{RAILWAY_URL}/iniciar-llamada",
        json=data,
        timeout=30
    )

    print(f"Status Code: {response.status_code}\n")

    if response.status_code == 200:
        result = response.json()
        print("="*70)
        print("LLAMADA INICIADA EXITOSAMENTE")
        print("="*70)
        print(f"\nCall SID: {result.get('call_id', 'N/A')}")
        print(f"Status: {result.get('status', 'N/A')}")
        print(f"\nLa llamada se esta realizando...")
        print("\nVerifica:")
        print("1. Que el telefono destino este recibiendo la llamada")
        print("2. Los logs en Railway: https://railway.app (seccion Deployments)")
        print("3. Los logs en Twilio: https://console.twilio.com/us1/monitor/logs/calls")
        print()
    else:
        print("="*70)
        print("ERROR AL INICIAR LLAMADA")
        print("="*70)
        print(f"\nRespuesta del servidor:")
        print(response.text)
        print()

except requests.exceptions.Timeout:
    print("ERROR: Timeout al conectar con Railway")
    print("Verifica que el servidor este corriendo")
except requests.exceptions.ConnectionError:
    print("ERROR: No se pudo conectar con Railway")
    print(f"URL: {RAILWAY_URL}")
    print("Verifica que el deployment este activo")
except Exception as e:
    print(f"ERROR: {e}")

print("="*70 + "\n")
