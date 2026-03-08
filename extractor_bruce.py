# -*- coding: utf-8 -*-
"""
Extrae logs de casos BRUCE específicos
"""
import re
import sys

print("\n" + "="*60)
print("  EXTRACTOR DE LOGS BRUCE")
print("="*60 + "\n")

# Leer archivo completo
try:
    with open('logs_railway_completo.txt', 'r', encoding='utf-8', errors='ignore') as f:
        lines = f.readlines()
    
    print(f" Archivo leído: {len(lines)} líneas\n")
except FileNotFoundError:
    print(" Error: No se encontró logs_railway_completo.txt")
    print("\nEjecuta primero: railway logs --lines 30000 > logs_railway_completo.txt")
    sys.exit(1)

# IDs a buscar
bruce_ids = ['BRUCE1288', 'BRUCE1289', 'BRUCE1290', 'BRUCE1291']

print("Buscando casos BRUCE...\n")

for bruce_id in bruce_ids:
    # Buscar el ID
    found_lines = []
    found_index = -1
    
    for i, line in enumerate(lines):
        if bruce_id in line:
            found_index = i
            break
    
    if found_index >= 0:
        # Extraer contexto: 100 líneas antes, 500 después
        start = max(0, found_index - 100)
        end = min(len(lines), found_index + 500)
        found_lines = lines[start:end]
        
        # Guardar
        filename = f'logs_{bruce_id.lower()}.txt'
        with open(filename, 'w', encoding='utf-8') as f:
            f.writelines(found_lines)
        
        print(f" {bruce_id}: {len(found_lines)} líneas → {filename}")
    else:
        print(f" {bruce_id}: No encontrado")

print("\n" + "="*60)
print("  COMPLETADO")
print("="*60 + "\n")
