# -*- coding: utf-8 -*-
"""
FIX 208: Descarga automática de logs desde el servidor Bruce W
No requiere Railway CLI ni configuración adicional
"""
import requests
import os
from datetime import datetime

# Configuración
URL_SERVIDOR = "https://nioval-webhook-server-production.up.railway.app"
CARPETA_LOGS = "C:\\Users\\PC 1\\AgenteVentas\\LOGS"


def descargar_logs(lineas=1000, filtro=None, bruce_id=None):
    """
    Descarga logs del servidor automáticamente

    Args:
        lineas: Número de líneas a descargar (max 5000)
        filtro: Filtrar por texto (ej: "error", "BRUCE")
        bruce_id: Filtrar por ID de Bruce específico

    Returns:
        str: Ruta del archivo guardado o None si falla
    """
    print("\n" + "="*70)
    print("📥 DESCARGA AUTOMÁTICA DE LOGS - BRUCE W")
    print("="*70 + "\n")

    # Crear carpeta si no existe
    os.makedirs(CARPETA_LOGS, exist_ok=True)

    # Construir URL con parámetros
    params = {"lineas": lineas}
    if filtro:
        params["filtro"] = filtro
    if bruce_id:
        params["bruce_id"] = bruce_id

    # Intentar API JSON (más info)
    url_api = f"{URL_SERVIDOR}/logs/api"

    print(f"   🌐 Conectando a: {url_api}")
    print(f"   📊 Solicitando: {lineas} líneas")
    if filtro:
        print(f"   🔍 Filtro: {filtro}")
    if bruce_id:
        print(f"   🆔 Bruce ID: {bruce_id}")

    try:
        response = requests.get(url_api, params=params, timeout=30)

        if response.status_code != 200:
            print(f"\n   ❌ Error del servidor: {response.status_code}")
            print(f"   {response.text[:200]}")
            return None

        data = response.json()

        if "error" in data:
            print(f"\n   ❌ Error: {data['error']}")
            return None

        logs = data.get("logs", [])
        total_en_buffer = data.get("total_en_buffer", 0)

        print(f"\n   ✅ Logs recibidos: {len(logs)}")
        print(f"   📊 Total en servidor: {total_en_buffer}")

        if not logs:
            print("\n   ⚠️ No hay logs disponibles")
            print("   💡 Esto puede significar que el servidor se reinició recientemente")
            print("      Los logs se acumulan mientras el servidor está activo")
            return None

        # Guardar en archivo
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        if bruce_id:
            filename = f"logs_BRUCE{bruce_id}_{timestamp}.txt"
        elif filtro:
            filename = f"logs_{filtro}_{timestamp}.txt"
        else:
            filename = f"logs_bruce_{timestamp}.txt"

        filepath = os.path.join(CARPETA_LOGS, filename)

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(f"# LOGS BRUCE W - Descargados: {timestamp}\n")
            f.write(f"# Total en servidor: {total_en_buffer}\n")
            f.write(f"# Logs descargados: {len(logs)}\n")
            if filtro:
                f.write(f"# Filtro aplicado: {filtro}\n")
            if bruce_id:
                f.write(f"# Bruce ID: {bruce_id}\n")
            f.write("="*70 + "\n\n")

            for log in logs:
                f.write(log + "\n")

        print(f"\n   💾 Guardado en: {filepath}")
        print(f"   📏 Tamaño: {os.path.getsize(filepath):,} bytes")

        return filepath

    except requests.exceptions.ConnectionError:
        print(f"\n   ❌ No se pudo conectar al servidor")
        print(f"   🔗 Verifica que el servidor esté activo en:")
        print(f"      {URL_SERVIDOR}")
        return None
    except requests.exceptions.Timeout:
        print(f"\n   ❌ Timeout - El servidor tardó demasiado")
        return None
    except Exception as e:
        print(f"\n   ❌ Error: {e}")
        return None


def analizar_logs(filepath):
    """Ejecuta el analizador de logs si existe"""
    if filepath and os.path.exists(filepath):
        print("\n" + "="*70)
        print("🔍 EJECUTANDO ANÁLISIS...")
        print("="*70)
        os.system(f'py analizar_logs_railway.py "{filepath}"')


def main():
    import sys

    # Parsear argumentos
    lineas = 1000
    filtro = None
    bruce_id = None
    analizar = True

    args = sys.argv[1:]
    i = 0
    while i < len(args):
        arg = args[i]

        if arg in ['-l', '--lineas'] and i + 1 < len(args):
            lineas = int(args[i + 1])
            i += 2
        elif arg in ['-f', '--filtro'] and i + 1 < len(args):
            filtro = args[i + 1]
            i += 2
        elif arg in ['-b', '--bruce'] and i + 1 < len(args):
            bruce_id = args[i + 1].replace("BRUCE", "")
            i += 2
        elif arg in ['--no-analizar']:
            analizar = False
            i += 1
        elif arg in ['-h', '--help']:
            print("""
📥 DESCARGA AUTOMÁTICA DE LOGS - BRUCE W

Uso:
    py descargar_logs_auto.py [opciones]

Opciones:
    -l, --lineas N      Número de líneas a descargar (default: 1000, max: 5000)
    -f, --filtro TEXTO  Filtrar logs que contengan TEXTO
    -b, --bruce ID      Filtrar por Bruce ID específico (ej: 460)
    --no-analizar       Solo descargar, no ejecutar análisis
    -h, --help          Mostrar esta ayuda

Ejemplos:
    py descargar_logs_auto.py                      # Descargar últimos 1000 logs
    py descargar_logs_auto.py -l 5000              # Descargar 5000 logs
    py descargar_logs_auto.py -f error             # Solo logs con "error"
    py descargar_logs_auto.py -b 460               # Solo logs de BRUCE460
    py descargar_logs_auto.py -f error --no-analizar  # Solo descargar

URLs del servidor:
    Ver logs en navegador: {URL_SERVIDOR}/logs/view
    Descargar directo:     {URL_SERVIDOR}/logs/download
    API JSON:              {URL_SERVIDOR}/logs/api
""".format(URL_SERVIDOR=URL_SERVIDOR))
            return
        else:
            i += 1

    # Descargar
    filepath = descargar_logs(lineas=lineas, filtro=filtro, bruce_id=bruce_id)

    # Analizar si se pidió
    if filepath and analizar:
        respuesta = input("\n¿Analizar logs ahora? (s/n) [s]: ").strip().lower()
        if respuesta in ['', 's', 'si', 'y', 'yes']:
            analizar_logs(filepath)

    print("\n" + "="*70)
    print("✅ Proceso completado")
    print("="*70 + "\n")


if __name__ == "__main__":
    main()
