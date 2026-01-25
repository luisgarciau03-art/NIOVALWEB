# -*- coding: utf-8 -*-
"""
Script de prueba rápida con tu número
Ejecuta: python test_mi_numero.py
"""
import requests
import sys

# Configurar encoding para Windows
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

# ========================================
# CONFIGURA TU NÚMERO AQUÍ
# ========================================
MI_NUMERO = "+526623531804"  # Número configurado
NOMBRE_NEGOCIO = "Prueba Bruce"

# ========================================

RAILWAY_URL = "https://nioval-webhook-server-production.up.railway.app"

print("\n" + "=" * 70)
print("PRUEBA DE BRUCE W - LLAMADA DE PRUEBA")
print("=" * 70 + "\n")
print(f"Llamando a: {MI_NUMERO}")
print(f"Negocio: {NOMBRE_NEGOCIO}")
print()

if MI_NUMERO == "+52XXXXXXXXXX":
    print("  ERROR: Debes cambiar MI_NUMERO en el archivo test_mi_numero.py")
    print("   Edita la línea 10 con tu número real")
    print()
    exit(1)

data = {
    "telefono": MI_NUMERO,
    "nombre_negocio": NOMBRE_NEGOCIO
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
        print(f"\nBruce te esta llamando...")
        print(f"\nPrueba decir:")
        print("   - De donde habla?")
        print("   - Que marcas maneja?")
        print("   - Mi nombre es [tu nombre]")
        print("\nMonitorea en:")
        print("   - Railway Logs: https://railway.app")
        print("   - Twilio: https://console.twilio.com/us1/monitor/logs/calls")
        print("   - Cache Stats: https://nioval-webhook-server-production.up.railway.app/stats")
        print()
    else:
        print("=" * 70)
        print("ERROR EN LA LLAMADA")
        print("=" * 70)
        print(f"\n{response.text}\n")

except Exception as e:
    print(f"ERROR: {e}")

print("=" * 70 + "\n")
