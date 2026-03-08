# -*- coding: utf-8 -*-
"""
Sistema automatico que lee de Google Sheets y llama via Railway
"""
import sys
import time
import requests
from datetime import datetime
from nioval_sheets_adapter import NiovalSheetsAdapter

# Configurar encoding para Windows
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')

# URL del servidor en Railway
RAILWAY_URL = "https://nioval-webhook-server-production.up.railway.app"

def main():
    # Verificar si se paso -y como argumento
    auto_confirm = '-y' in sys.argv or '--yes' in sys.argv

    print("\n" + "=" * 70)
    print("SISTEMA AUTOMATICO DE LLAMADAS (RAILWAY + GOOGLE SHEETS)")
    print("=" * 70 + "\n")

    # Conectar con Google Sheets
    print("Conectando con Google Sheets...")
    try:
        sheets = NiovalSheetsAdapter()
        print("Conexion exitosa\n")
    except Exception as e:
        print(f"ERROR al conectar con Google Sheets: {e}")
        return

    # Obtener contactos pendientes
    print("Obteniendo contactos pendientes...")
    contactos = sheets.obtener_contactos_pendientes(limite=5)

    if not contactos:
        print("\nNo hay contactos pendientes para llamar")
        print("\nVerifica que en Google Sheets haya contactos con:")
        print("- Columna E (TELEFONO) con numero valido")
        print("- Columna F (RESULTADO) vacia (sin marcar)")
        return

    print(f"\nEncontrados {len(contactos)} contactos pendientes\n")

    # Mostrar contactos
    print("=" * 70)
    print("CONTACTOS A LLAMAR:")
    print("=" * 70)
    for idx, c in enumerate(contactos, 1):
        print(f"{idx}. {c.get('nombre_negocio', 'SIN NOMBRE')} - {c.get('telefono', 'SIN TEL')}")
    print()

    # Confirmar
    if not auto_confirm:
        respuesta = input("Iniciar llamadas automaticas? (s/n): ").strip().lower()
        if respuesta != 's':
            print("\nCancelado por el usuario")
            return
    else:
        print("Modo automatico (-y): Iniciando sin confirmacion...\n")

    print("\n" + "=" * 70)
    print("INICIANDO LLAMADAS...")
    print("=" * 70 + "\n")

    # Estadisticas
    exitosas = 0
    errores = 0

    # Procesar cada contacto
    for idx, contacto in enumerate(contactos, 1):
        nombre = contacto.get('nombre_negocio', 'cliente')
        telefono = contacto.get('telefono', '')

        print(f"\n[{idx}/{len(contactos)}] {nombre} - {telefono}")

        if not telefono:
            print("  SALTADO: Sin telefono")
            errores += 1
            continue

        # Preparar datos para Railway
        data = {
            "telefono": telefono,
            "nombre_negocio": nombre
        }

        try:
            # Llamar al endpoint de Railway
            print(f"  Enviando request a Railway...")
            response = requests.post(
                f"{RAILWAY_URL}/iniciar-llamada",
                json=data,
                timeout=30
            )

            if response.status_code == 200:
                result = response.json()
                call_id = result.get('call_id', 'N/A')
                print(f"  EXITOSA - Call SID: {call_id}")
                exitosas += 1
            else:
                print(f"  ERROR - Status {response.status_code}")
                print(f"  {response.text}")
                errores += 1

        except Exception as e:
            print(f"  ERROR: {e}")
            errores += 1

        # Delay entre llamadas (excepto en la ultima)
        if idx < len(contactos):
            print("  Esperando 10 segundos antes de la siguiente llamada...")
            time.sleep(10)

    # Resumen final
    print("\n" + "=" * 70)
    print("RESUMEN DE LLAMADAS")
    print("=" * 70)
    print(f"\nTotal contactos: {len(contactos)}")
    print(f"Exitosas: {exitosas}")
    print(f"Errores: {errores}")
    print()
    print("Verifica los resultados en:")
    print("- Railway logs: https://railway.app")
    print("- Twilio logs: https://console.twilio.com/us1/monitor/logs/calls")
    print("- Google Sheets: Los resultados se guardaran automaticamente")
    print("\n" + "=" * 70 + "\n")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nInterrumpido por el usuario")
    except Exception as e:
        print(f"\nERROR FATAL: {e}")
