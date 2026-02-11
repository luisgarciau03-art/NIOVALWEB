#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Analizar bugs específicos POST FIX 646/647
"""

import re
import sys

# Bugs críticos a analizar
BUGS_CRITICOS = {
    'BRUCE2106': 'GPT_LOGICA_ROTA - Pidió contacto cuando ya mencionado',
    'BRUCE2104': 'GPT_LOGICA_ROTA - Solicitó número previamente proporcionado',
    'BRUCE2112': 'CLIENTE_HABLA_ULTIMO - No respondió a cliente',
    'BRUCE2111': 'CLIENTE_HABLA_ULTIMO - No respondió a cliente'
}

def extraer_conversacion(archivo, bruce_id):
    """Extrae la conversación completa de un BRUCE ID"""
    with open(archivo, 'r', encoding='utf-8', errors='ignore') as f:
        contenido = f.read()

    # Buscar el ID en el archivo
    if bruce_id not in contenido:
        return None

    # Extraer sección desde inicio hasta el BRUCE ID + 500 líneas después
    lineas = contenido.split('\n')

    # Encontrar línea con BRUCE ID
    inicio_idx = None
    for i, linea in enumerate(lineas):
        if bruce_id in linea and 'ID BRUCE:' in linea:
            inicio_idx = i
            break

    if inicio_idx is None:
        return None

    # Buscar hacia atrás para encontrar inicio de la llamada
    # (buscar "Iniciando saludo" o "webhook-voz")
    buscar_desde = max(0, inicio_idx - 1000)

    for i in range(inicio_idx, buscar_desde, -1):
        if 'webhook-voz' in lineas[i] or 'Iniciando saludo' in lineas[i]:
            inicio_real = i
            break
    else:
        inicio_real = buscar_desde

    # Extraer desde inicio_real hasta inicio_idx + 100 líneas
    fin_idx = min(len(lineas), inicio_idx + 100)
    conversacion = '\n'.join(lineas[inicio_real:fin_idx])

    return conversacion

def analizar_bug(conversacion, bug_id, descripcion):
    """Analiza una conversación para encontrar el bug"""
    print(f"\n{'='*80}")
    print(f"BUG: {bug_id}")
    print(f"TIPO: {descripcion}")
    print(f"{'='*80}\n")

    # Extraer mensajes Bruce y Cliente
    mensajes_bruce = re.findall(r'BRUCE:(.*?)(?=CLIENTE:|$)', conversacion, re.DOTALL)
    mensajes_cliente = re.findall(r'CLIENTE:(.*?)(?=BRUCE:|$)', conversacion, re.DOTALL)

    print(f"Turnos Bruce: {len(mensajes_bruce)}")
    print(f"Turnos Cliente: {len(mensajes_cliente)}")
    print()

    # Mostrar conversación limpia
    print("CONVERSACIÓN:")
    print("-" * 80)

    # Reconstruir conversación en orden
    lineas = conversacion.split('\n')
    turno = 0
    for linea in lineas:
        if 'BRUCE:' in linea:
            turno += 1
            # Extraer solo el texto después de "BRUCE:"
            texto = linea.split('BRUCE:', 1)[1].strip()
            print(f"[Turno {turno}] BRUCE: {texto}")
        elif 'CLIENTE:' in linea:
            texto = linea.split('CLIENTE:', 1)[1].strip()
            print(f"           CLIENTE: {texto}")

    print("\n" + "="*80)

def main():
    archivos = [
        'C:\\Users\\PC 1\\AgenteVentas\\LOGS\\11_02PT11.txt',
        'C:\\Users\\PC 1\\AgenteVentas\\LOGS\\11_02PT12.txt'
    ]

    print("ANÁLISIS DE BUGS POST FIX 646/647")
    print("="*80)

    for bug_id, descripcion in BUGS_CRITICOS.items():
        conversacion_encontrada = None

        for archivo in archivos:
            try:
                conversacion = extraer_conversacion(archivo, bug_id)
                if conversacion:
                    conversacion_encontrada = conversacion
                    break
            except FileNotFoundError:
                continue

        if conversacion_encontrada:
            analizar_bug(conversacion_encontrada, bug_id, descripcion)
        else:
            print(f"\n⚠️ {bug_id} no encontrado en los logs")

if __name__ == '__main__':
    main()
