# -*- coding: utf-8 -*-
"""
Script para descargar grabaciones de llamadas desde Twilio
"""
import os
import sys
import requests
from dotenv import load_dotenv
from twilio.rest import Client
from datetime import datetime, timedelta

# Configurar encoding para Windows
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')

load_dotenv()

# Configuración
account_sid = os.getenv('TWILIO_ACCOUNT_SID')
auth_token = os.getenv('TWILIO_AUTH_TOKEN')
client = Client(account_sid, auth_token)

print("\n" + "=" * 70)
print("DESCARGAR GRABACIONES DE LLAMADAS DE BRUCE")
print("=" * 70 + "\n")

# Obtener llamadas de los últimos 7 días
fecha_inicio = datetime.now() - timedelta(days=7)
print(f"Buscando llamadas desde: {fecha_inicio.strftime('%Y-%m-%d')}\n")

calls = client.calls.list(
    start_time_after=fecha_inicio,
    limit=50
)

if not calls:
    print("No se encontraron llamadas recientes")
    sys.exit(0)

print(f"Encontradas {len(calls)} llamadas\n")
print("=" * 70)

# Crear directorio para grabaciones
os.makedirs("grabaciones", exist_ok=True)

# Procesar cada llamada
for idx, call in enumerate(calls, 1):
    call_sid = call.sid
    fecha = call.start_time.strftime('%Y-%m-%d %H:%M:%S') if call.start_time else 'N/A'
    duracion = f"{call.duration}s" if call.duration else 'N/A'
    destino = call.to

    print(f"\n[{idx}/{len(calls)}] Llamada {call_sid}")
    print(f"    Fecha: {fecha}")
    print(f"    Destino: {destino}")
    print(f"    Duración: {duracion}")

    # Buscar grabaciones para esta llamada
    recordings = client.recordings.list(call_sid=call_sid)

    if recordings:
        for rec_idx, recording in enumerate(recordings):
            # URL de descarga
            recording_url = f"https://api.twilio.com{recording.uri.replace('.json', '.mp3')}"

            # Nombre del archivo
            filename = f"grabaciones/{call_sid}_{rec_idx}.mp3"

            print(f"    📥 Descargando grabación {rec_idx + 1}...")

            try:
                # Descargar con autenticación
                response = requests.get(
                    recording_url,
                    auth=(account_sid, auth_token),
                    stream=True
                )

                if response.status_code == 200:
                    with open(filename, 'wb') as f:
                        for chunk in response.iter_content(chunk_size=8192):
                            f.write(chunk)
                    print(f"    ✅ Guardada en: {filename}")
                else:
                    print(f"    ❌ Error descargando: {response.status_code}")

            except Exception as e:
                print(f"    ❌ Error: {e}")
    else:
        print(f"    ⚠️  No hay grabaciones para esta llamada")

print("\n" + "=" * 70)
print("DESCARGA COMPLETADA")
print("=" * 70)
print(f"\nLas grabaciones se guardaron en: {os.path.abspath('grabaciones')}")
print("\nTambién puedes escucharlas en:")
print("https://console.twilio.com/us1/monitor/logs/calls")
print("\n" + "=" * 70 + "\n")
