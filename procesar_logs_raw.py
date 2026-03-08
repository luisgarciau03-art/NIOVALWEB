# -*- coding: utf-8 -*-
import json
import sys

if len(sys.argv) < 2:
    print("Uso: python procesar_logs_raw.py logs_bruce1288_raw.json")
    sys.exit(1)

filename = sys.argv[1]
bruce_id = filename.split('_')[1].upper()  # Extraer BRUCE ID

print(f"Procesando {filename} para {bruce_id}...")

with open(filename, 'r', encoding='utf-8') as f:
    content = f.read()

# Parsear cada línea como JSON
logs = []
for line in content.strip().split('\n'):
    if line.strip():
        try:
            entry = json.loads(line)
            logs.append(entry)
        except:
            pass

print(f" {len(logs)} entradas parseadas")

# Convertir a texto legible
output_file = f'logs_{bruce_id.lower()}.txt'
with open(output_file, 'w', encoding='utf-8') as f:
    for entry in logs:
        timestamp = entry.get('timestamp', '')
        message = entry.get('message', '')
        f.write(f"[{timestamp}] {message}\n")

print(f" Guardado en {output_file}")
