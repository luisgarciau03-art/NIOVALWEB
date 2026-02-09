#!/usr/bin/env python3
"""
Auto-descarga de logs de Railway
================================
Descarga automáticamente los logs cada X minutos para no perder historial.
Guarda en C:\\Users\\PC 1\\AgenteVentas\\LOGS con formato DD_MMPT#

Uso:
    python auto_descarga_logs.py                    # Descarga cada 30 min (default)
    python auto_descarga_logs.py --intervalo 15    # Descarga cada 15 min
    python auto_descarga_logs.py --una-vez         # Solo descarga una vez y sale
    python auto_descarga_logs.py --buscar 1704     # Buscar BRUCE1704 en historial
"""

import subprocess
import os
import time
import argparse
from datetime import datetime
import re
import json
import glob

# Configuración
LOGS_DIR = r"C:\Users\PC 1\AgenteVentas\LOGS"
MAX_LOGS_POR_DESCARGA = 5000
INTERVALO_MINUTOS_DEFAULT = 30
RAILWAY_PATH = r"C:\Users\PC 1\AppData\Roaming\npm\railway.cmd"

def crear_directorio_logs():
    """Crea el directorio para guardar logs si no existe"""
    if not os.path.exists(LOGS_DIR):
        os.makedirs(LOGS_DIR)
        print(f"[OK] Directorio '{LOGS_DIR}' creado")
    return LOGS_DIR

def obtener_siguiente_nombre():
    """
    Genera el siguiente nombre de archivo con formato DD_MMPT#
    Ejemplo: 28_01PT1, 28_01PT2, 28_01PT3...
    """
    crear_directorio_logs()

    hoy = datetime.now()
    prefijo = hoy.strftime("%d_%m")  # Formato: 28_01

    # Buscar archivos existentes con el mismo prefijo de fecha
    patron = os.path.join(LOGS_DIR, f"{prefijo}PT*.txt")
    archivos_existentes = glob.glob(patron)

    if not archivos_existentes:
        siguiente_num = 1
    else:
        # Extraer números de los archivos existentes
        numeros = []
        for archivo in archivos_existentes:
            nombre = os.path.basename(archivo)
            match = re.search(rf'{prefijo}PT(\d+)', nombre)
            if match:
                numeros.append(int(match.group(1)))

        siguiente_num = max(numeros) + 1 if numeros else 1

    nombre = f"{prefijo}PT{siguiente_num}.txt"
    return nombre, siguiente_num

def descargar_logs(num_lineas=5000):
    """Descarga logs de Railway y los guarda con formato DD_MMPT#"""
    fecha_legible = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    nombre_archivo, num_parte = obtener_siguiente_nombre()

    print(f"\n{'='*60}")
    print(f"[{fecha_legible}] Descargando {num_lineas} lineas de logs...")
    print(f"Archivo: {nombre_archivo}")
    print(f"{'='*60}")

    try:
        # Ejecutar railway logs con encoding UTF-8
        resultado = subprocess.run(
            [RAILWAY_PATH, "logs", "-n", str(num_lineas)],
            capture_output=True,
            timeout=180,
            cwd=r"C:\Users\PC 1\AgenteVentas",
            shell=True
        )

        # Decodificar con UTF-8, ignorando errores
        try:
            logs = resultado.stdout.decode('utf-8', errors='replace')
        except:
            logs = resultado.stdout.decode('latin-1', errors='replace')

        if resultado.returncode != 0:
            stderr = resultado.stderr.decode('utf-8', errors='replace') if resultado.stderr else ""
            print(f"[ERROR] Railway CLI fallo: {stderr}")
            return None

        if not logs or len(logs) < 100:
            print(f"[WARN] Logs vacios o muy cortos ({len(logs) if logs else 0} chars)")
            return None

        # Guardar archivo
        archivo_completo = os.path.join(LOGS_DIR, nombre_archivo)

        with open(archivo_completo, 'w', encoding='utf-8') as f:
            f.write(f"# Logs Railway - Parte {num_parte}\n")
            f.write(f"# Fecha descarga: {fecha_legible}\n")
            f.write(f"# Lineas: {num_lineas}\n")
            f.write(f"# {'='*50}\n\n")
            f.write(logs)

        # Extraer BRUCE IDs para resumen
        bruce_ids = set(re.findall(r'BRUCE(\d+)', logs))
        bruce_ids_sorted = sorted([int(x) for x in bruce_ids])

        lineas = len(logs.split('\n'))
        tamano_kb = len(logs) / 1024

        print(f"\n[OK] Guardado: {archivo_completo}")
        print(f"    Lineas: {lineas}")
        print(f"    Tamano: {tamano_kb:.1f} KB")

        if bruce_ids_sorted:
            print(f"    BRUCE IDs: {bruce_ids_sorted[0]} - {bruce_ids_sorted[-1]} ({len(bruce_ids_sorted)} llamadas)")

        # Guardar índice
        actualizar_indice(nombre_archivo, archivo_completo, lineas, bruce_ids_sorted)

        return archivo_completo

    except subprocess.TimeoutExpired:
        print("[ERROR] Timeout descargando logs (>180s)")
        return None
    except FileNotFoundError:
        print(f"[ERROR] Railway CLI no encontrado en: {RAILWAY_PATH}")
        print("Verifica que Railway CLI este instalado")
        return None
    except Exception as e:
        print(f"[ERROR] {type(e).__name__}: {e}")
        return None

def actualizar_indice(nombre, archivo, lineas, bruce_ids):
    """Mantiene un índice de todos los archivos descargados"""
    indice_file = os.path.join(LOGS_DIR, "indice_logs.json")

    try:
        if os.path.exists(indice_file):
            with open(indice_file, 'r', encoding='utf-8') as f:
                indice = json.load(f)
        else:
            indice = {"descargas": []}

        entrada = {
            "nombre": nombre,
            "fecha": datetime.now().isoformat(),
            "archivo": archivo,
            "lineas": lineas,
            "bruce_ids_min": bruce_ids[0] if bruce_ids else None,
            "bruce_ids_max": bruce_ids[-1] if bruce_ids else None,
            "total_bruce_ids": len(bruce_ids)
        }

        indice["descargas"].append(entrada)
        indice["ultima_descarga"] = datetime.now().isoformat()
        indice["total_descargas"] = len(indice["descargas"])

        with open(indice_file, 'w', encoding='utf-8') as f:
            json.dump(indice, f, indent=2, ensure_ascii=False)

    except Exception as e:
        print(f"[WARN] No se pudo actualizar indice: {e}")

def buscar_bruce_en_historico(bruce_id):
    """Busca un BRUCE ID específico en todos los logs históricos"""
    crear_directorio_logs()

    print(f"\nBuscando BRUCE{bruce_id} en logs historicos...")

    archivos = sorted([f for f in os.listdir(LOGS_DIR) if f.endswith(".txt") and f != "indice_logs.json"])

    encontrado_en = []
    todas_lineas = []

    for archivo in archivos:
        ruta = os.path.join(LOGS_DIR, archivo)
        try:
            with open(ruta, 'r', encoding='utf-8') as f:
                contenido = f.read()
                if f"BRUCE{bruce_id}" in contenido:
                    encontrado_en.append(archivo)
                    # Extraer líneas relevantes
                    lineas = [l for l in contenido.split('\n') if f"BRUCE{bruce_id}" in l]
                    todas_lineas.extend(lineas)
                    print(f"  [OK] {archivo}: {len(lineas)} lineas")
        except Exception as e:
            print(f"  [WARN] Error leyendo {archivo}: {e}")

    if not encontrado_en:
        print(f"\n[WARN] BRUCE{bruce_id} NO encontrado en ningun archivo historico")
    else:
        print(f"\n[RESUMEN] BRUCE{bruce_id} encontrado en {len(encontrado_en)} archivo(s)")
        print(f"          Total lineas: {len(todas_lineas)}")

        # Mostrar conversación
        print(f"\n--- Conversacion BRUCE{bruce_id} ---")
        for linea in todas_lineas:
            if "CLIENTE DIJO" in linea or "DICE:" in linea:
                print(linea[-200:] if len(linea) > 200 else linea)

    return encontrado_en

def mostrar_estadisticas():
    """Muestra estadísticas del historial de logs"""
    indice_file = os.path.join(LOGS_DIR, "indice_logs.json")

    if not os.path.exists(indice_file):
        print("[INFO] No hay indice de logs aun.")
        return

    with open(indice_file, 'r', encoding='utf-8') as f:
        indice = json.load(f)

    print(f"\n{'='*60}")
    print("ESTADISTICAS DE LOGS HISTORICOS")
    print(f"{'='*60}")
    print(f"Directorio: {LOGS_DIR}")
    print(f"Total descargas: {indice.get('total_descargas', 0)}")
    print(f"Ultima descarga: {indice.get('ultima_descarga', 'N/A')}")

    if indice.get('descargas'):
        todas_ids = []
        for d in indice['descargas']:
            if d.get('bruce_ids_min') and d.get('bruce_ids_max'):
                todas_ids.extend(range(d['bruce_ids_min'], d['bruce_ids_max'] + 1))

        if todas_ids:
            print(f"Rango BRUCE IDs: {min(todas_ids)} - {max(todas_ids)}")

    # Mostrar archivos
    print(f"\nArchivos guardados:")
    for d in indice['descargas'][-10:]:
        bruce_range = f"BRUCE{d.get('bruce_ids_min', '?')}-{d.get('bruce_ids_max', '?')}"
        print(f"  {d['nombre']}: {bruce_range} ({d['lineas']} lineas)")

def loop_automatico(intervalo_minutos):
    """Loop infinito que descarga logs cada X minutos"""
    print(f"\n{'='*60}")
    print(f"MODO AUTOMATICO - Descarga cada {intervalo_minutos} minutos")
    print(f"Directorio: {LOGS_DIR}")
    print(f"Presiona Ctrl+C para detener")
    print(f"{'='*60}")

    contador = 0

    while True:
        try:
            contador += 1
            print(f"\n[Descarga #{contador}]")
            descargar_logs(MAX_LOGS_POR_DESCARGA)

            # Mostrar próxima hora
            from datetime import timedelta
            proxima = datetime.now() + timedelta(minutes=intervalo_minutos)
            print(f"\nProxima descarga: {proxima.strftime('%H:%M:%S')} (en {intervalo_minutos} min)")
            time.sleep(intervalo_minutos * 60)

        except KeyboardInterrupt:
            print(f"\n\n[STOP] Detenido despues de {contador} descargas")
            mostrar_estadisticas()
            break

def main():
    parser = argparse.ArgumentParser(description="Auto-descarga de logs de Railway")
    parser.add_argument("--intervalo", "-i", type=int, default=INTERVALO_MINUTOS_DEFAULT,
                        help=f"Intervalo en minutos entre descargas (default: {INTERVALO_MINUTOS_DEFAULT})")
    parser.add_argument("--una-vez", "-1", action="store_true",
                        help="Solo descarga una vez y sale")
    parser.add_argument("--lineas", "-n", type=int, default=MAX_LOGS_POR_DESCARGA,
                        help=f"Numero de lineas a descargar (default: {MAX_LOGS_POR_DESCARGA})")
    parser.add_argument("--buscar", "-b", type=int,
                        help="Buscar un BRUCE ID especifico en el historial")
    parser.add_argument("--stats", "-s", action="store_true",
                        help="Mostrar estadisticas del historial")

    args = parser.parse_args()

    if args.stats:
        mostrar_estadisticas()
        return

    if args.buscar:
        buscar_bruce_en_historico(args.buscar)
        return

    if args.una_vez:
        descargar_logs(args.lineas)
        mostrar_estadisticas()
    else:
        loop_automatico(args.intervalo)

if __name__ == "__main__":
    main()
