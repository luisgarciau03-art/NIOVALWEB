#!/usr/bin/env python3
"""
Auto-descarga INTELIGENTE de logs de Railway
=============================================
- Detecta nuevos DEPLOYS automáticamente
- Descarga cuando hay 5000+ líneas nuevas
- Corre como servicio en segundo plano
- Se inicia automáticamente con Windows (opcional)

Uso:
    python auto_descarga_logs_smart.py              # Iniciar monitoreo
    python auto_descarga_logs_smart.py --instalar   # Instalar en inicio de Windows
"""

import subprocess
import os
import time
import json
import re
from datetime import datetime
import glob
import sys
import requests

# Configuración
LOGS_DIR = r"C:\Users\PC 1\AgenteVentas\LOGS"

# Configuración de Telegram para notificaciones
TELEGRAM_BOTS = [
    {
        "token": "8537624347:AAHDIe60mb2TkdDk4vqlcS2tpakTB_5D4qE",
        "chat_id": "7314842427",
        "nombre": "Bot 1"
    },
    {
        "token": "8524460310:AAFAwph27rSagooKTNSGXauBycpDpCjhKjI",
        "chat_id": "5838212022",
        "nombre": "Bot 2"
    }
]


def notificar_telegram(mensaje: str):
    """Envía notificación a Telegram"""
    for bot in TELEGRAM_BOTS:
        try:
            url = f"https://api.telegram.org/bot{bot['token']}/sendMessage"
            data = {
                "chat_id": bot['chat_id'],
                "text": mensaje,
                "parse_mode": "HTML"
            }
            requests.post(url, data=data, timeout=10)
        except:
            pass
RAILWAY_PATH = r"C:\Users\PC 1\AppData\Roaming\npm\railway.cmd"
WORKING_DIR = r"C:\Users\PC 1\AgenteVentas"
STATE_FILE = os.path.join(LOGS_DIR, "monitor_state.json")

# Railway Health Endpoint para detectar deploys
RAILWAY_HEALTH_URL = "https://nioval-webhook-server-production.up.railway.app/info-cache"

# Parámetros de monitoreo
LINEAS_POR_DESCARGA = 5000
CHECK_INTERVAL_SECONDS = 60  # Revisar cada 60 segundos
MIN_NUEVAS_LINEAS_PARA_DESCARGAR = 500  # Mínimo de líneas nuevas para descargar

def log(msg):
    """Log con timestamp"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {msg}")

def crear_directorio():
    if not os.path.exists(LOGS_DIR):
        os.makedirs(LOGS_DIR)
        log(f"Directorio creado: {LOGS_DIR}")

def cargar_estado():
    """Carga el estado anterior del monitor"""
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            pass
    return {
        "ultimo_bruce_id": 0,
        "ultimo_estado_servidor": {},
        "ultima_descarga": None,
        "total_descargas": 0
    }

def guardar_estado(estado):
    """Guarda el estado del monitor"""
    try:
        with open(STATE_FILE, 'w', encoding='utf-8') as f:
            json.dump(estado, f, indent=2)
    except Exception as e:
        log(f"[WARN] No se pudo guardar estado: {e}")

def obtener_ultimo_bruce_id():
    """Obtiene el último BRUCE ID de los logs actuales"""
    try:
        resultado = subprocess.run(
            [RAILWAY_PATH, "logs", "-n", "100"],
            capture_output=True,
            timeout=30,
            cwd=WORKING_DIR,
            shell=True
        )
        logs = resultado.stdout.decode('utf-8', errors='replace')
        bruce_ids = re.findall(r'BRUCE(\d+)', logs)
        if bruce_ids:
            return max(int(x) for x in bruce_ids)
    except Exception as e:
        log(f"[ERROR] Obteniendo ultimo BRUCE ID: {e}")
    return 0

def obtener_estado_servidor():
    """
    Obtiene estado del servidor Railway via health endpoint.
    Detecta deploys cuando el servidor se reinicia (frases_registradas vuelve a 0 o cambia drásticamente)
    """
    try:
        response = requests.get(RAILWAY_HEALTH_URL, timeout=10)
        if response.status_code == 200:
            data = response.json()
            return {
                "online": True,
                "audios": data.get("audios_en_cache", 0),
                "frases": data.get("frases_registradas", 0),
                "timestamp": datetime.now().isoformat()
            }
    except requests.exceptions.ConnectionError:
        return {"online": False, "audios": 0, "frases": 0, "timestamp": datetime.now().isoformat()}
    except Exception as e:
        log(f"[WARN] Error consultando servidor: {e}")
        return {"online": False, "audios": 0, "frases": 0, "timestamp": datetime.now().isoformat()}


def detectar_nuevo_deploy(estado_anterior: dict, estado_actual: dict) -> bool:
    """
    Detecta si hubo un nuevo deploy comparando estados del servidor.
    Un deploy se detecta cuando:
    1. El servidor estaba offline y ahora está online
    2. El contador de frases bajó significativamente (reinicio de memoria)
    """
    if not estado_anterior or not estado_actual:
        return False

    # Servidor volvió después de estar offline
    if not estado_anterior.get("online") and estado_actual.get("online"):
        log("[DEPLOY] Servidor volvió online después de estar caído")
        return True

    # Frases bajaron significativamente (indica reinicio)
    frases_antes = estado_anterior.get("frases", 0)
    frases_ahora = estado_actual.get("frases", 0)

    if frases_antes > 100 and frases_ahora < frases_antes * 0.5:
        log(f"[DEPLOY] Frases bajaron de {frases_antes} a {frases_ahora} (reinicio detectado)")
        return True

    return False

def obtener_siguiente_nombre():
    """Genera nombre de archivo: DD_MMPT#"""
    crear_directorio()
    hoy = datetime.now()
    prefijo = hoy.strftime("%d_%m")

    patron = os.path.join(LOGS_DIR, f"{prefijo}PT*.txt")
    archivos = glob.glob(patron)

    if not archivos:
        return f"{prefijo}PT1.txt", 1

    numeros = []
    for archivo in archivos:
        match = re.search(rf'{prefijo}PT(\d+)', os.path.basename(archivo))
        if match:
            numeros.append(int(match.group(1)))

    siguiente = max(numeros) + 1 if numeros else 1
    return f"{prefijo}PT{siguiente}.txt", siguiente

def descargar_logs(razon="manual"):
    """Descarga logs y los guarda"""
    nombre, num_parte = obtener_siguiente_nombre()
    fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    log(f"Descargando {LINEAS_POR_DESCARGA} lineas... (razon: {razon})")

    try:
        resultado = subprocess.run(
            [RAILWAY_PATH, "logs", "-n", str(LINEAS_POR_DESCARGA)],
            capture_output=True,
            timeout=180,
            cwd=WORKING_DIR,
            shell=True
        )

        logs = resultado.stdout.decode('utf-8', errors='replace')

        if not logs or len(logs) < 100:
            log("[WARN] Logs vacios")
            return None

        archivo = os.path.join(LOGS_DIR, nombre)

        with open(archivo, 'w', encoding='utf-8') as f:
            f.write(f"# Logs Railway - Parte {num_parte}\n")
            f.write(f"# Fecha: {fecha}\n")
            f.write(f"# Razon: {razon}\n")
            f.write(f"# {'='*50}\n\n")
            f.write(logs)

        # Estadísticas
        bruce_ids = set(re.findall(r'BRUCE(\d+)', logs))
        bruce_sorted = sorted([int(x) for x in bruce_ids]) if bruce_ids else []
        lineas = len(logs.split('\n'))

        log(f"[OK] Guardado: {nombre}")
        log(f"    Lineas: {lineas}, BRUCE IDs: {bruce_sorted[0] if bruce_sorted else '?'}-{bruce_sorted[-1] if bruce_sorted else '?'}")

        # Notificar por Telegram
        mensaje = f"""<b>LOGS DESCARGADOS</b>

Archivo: {nombre}
Lineas: {lineas}
BRUCE IDs: {bruce_sorted[0] if bruce_sorted else '?'} - {bruce_sorted[-1] if bruce_sorted else '?'}
Razon: {razon}"""
        notificar_telegram(mensaje)

        return {
            "archivo": archivo,
            "nombre": nombre,
            "lineas": lineas,
            "bruce_min": bruce_sorted[0] if bruce_sorted else None,
            "bruce_max": bruce_sorted[-1] if bruce_sorted else None
        }

    except Exception as e:
        log(f"[ERROR] Descargando: {e}")
        return None

def monitorear():
    """Loop principal de monitoreo"""
    log("="*60)
    log("MONITOR INTELIGENTE DE LOGS - INICIADO")
    log(f"Directorio: {LOGS_DIR}")
    log(f"Intervalo de chequeo: {CHECK_INTERVAL_SECONDS}s")
    log(f"Lineas por descarga: {LINEAS_POR_DESCARGA}")
    log("="*60)

    estado = cargar_estado()
    log(f"Estado anterior: ultimo BRUCE ID = {estado['ultimo_bruce_id']}")

    # Descarga inicial
    log("\n[INICIO] Descarga inicial...")
    resultado = descargar_logs("inicio_monitor")
    if resultado:
        estado['ultimo_bruce_id'] = resultado['bruce_max'] or estado['ultimo_bruce_id']
        estado['ultima_descarga'] = datetime.now().isoformat()
        estado['total_descargas'] = estado.get('total_descargas', 0) + 1
        guardar_estado(estado)

    # Obtener estado inicial del servidor
    estado_servidor = obtener_estado_servidor()
    estado['ultimo_estado_servidor'] = estado_servidor
    if estado_servidor.get("online"):
        log(f"Servidor online - Audios: {estado_servidor.get('audios')}, Frases: {estado_servidor.get('frases')}")
    else:
        log("Servidor offline al iniciar monitoreo")
    guardar_estado(estado)

    log(f"\nMonitoreando... (Ctrl+C para detener)\n")

    while True:
        try:
            time.sleep(CHECK_INTERVAL_SECONDS)

            # Verificar nuevo deploy via health endpoint
            estado_servidor_actual = obtener_estado_servidor()
            estado_servidor_anterior = estado.get('ultimo_estado_servidor', {})

            if detectar_nuevo_deploy(estado_servidor_anterior, estado_servidor_actual):
                log(f"\n[DEPLOY] Nuevo deploy detectado!")
                log(f"    Esperando 30s para que el servidor se estabilice...")
                time.sleep(30)

                resultado = descargar_logs("nuevo_deploy")
                if resultado:
                    estado['ultimo_bruce_id'] = resultado['bruce_max'] or estado['ultimo_bruce_id']
                    estado['ultima_descarga'] = datetime.now().isoformat()
                    estado['total_descargas'] += 1

                # Actualizar estado del servidor
                estado['ultimo_estado_servidor'] = obtener_estado_servidor()
                guardar_estado(estado)
                continue

            # Actualizar estado del servidor
            estado['ultimo_estado_servidor'] = estado_servidor_actual

            # Verificar nuevas llamadas (BRUCE IDs)
            bruce_actual = obtener_ultimo_bruce_id()
            if bruce_actual > 0:
                nuevos_bruce = bruce_actual - estado.get('ultimo_bruce_id', 0)

                if nuevos_bruce >= 5:  # Al menos 5 llamadas nuevas
                    log(f"\n[LLAMADAS] {nuevos_bruce} llamadas nuevas detectadas")
                    log(f"    BRUCE anterior: {estado.get('ultimo_bruce_id', 0)}")
                    log(f"    BRUCE actual: {bruce_actual}")

                    resultado = descargar_logs(f"{nuevos_bruce}_llamadas_nuevas")
                    if resultado:
                        estado['ultimo_bruce_id'] = resultado['bruce_max'] or bruce_actual
                        estado['ultima_descarga'] = datetime.now().isoformat()
                        estado['total_descargas'] += 1
                        guardar_estado(estado)

            # Mostrar heartbeat cada 5 minutos
            minutos = int(time.time() / 60)
            if minutos % 5 == 0:
                log(f"[HEARTBEAT] Monitoreando... (ultimo BRUCE: {estado.get('ultimo_bruce_id', 0)}, descargas: {estado.get('total_descargas', 0)})")
                time.sleep(60)  # Evitar múltiples heartbeats en el mismo minuto

        except KeyboardInterrupt:
            log("\n[STOP] Monitor detenido por usuario")
            guardar_estado(estado)
            break
        except Exception as e:
            log(f"[ERROR] {e}")
            time.sleep(10)

def instalar_inicio_windows():
    """Crea un acceso directo en el inicio de Windows"""
    import winreg

    script_path = os.path.abspath(__file__)
    python_path = sys.executable

    comando = f'"{python_path}" "{script_path}"'

    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0, winreg.KEY_SET_VALUE
        )
        winreg.SetValueEx(key, "RailwayLogsMonitor", 0, winreg.REG_SZ, comando)
        winreg.CloseKey(key)
        log("[OK] Instalado en inicio de Windows")
        log(f"    El monitor se iniciara automaticamente al encender la PC")
    except Exception as e:
        log(f"[ERROR] No se pudo instalar en inicio: {e}")

def desinstalar_inicio_windows():
    """Remueve el acceso directo del inicio de Windows"""
    import winreg

    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0, winreg.KEY_SET_VALUE
        )
        winreg.DeleteValue(key, "RailwayLogsMonitor")
        winreg.CloseKey(key)
        log("[OK] Removido del inicio de Windows")
    except FileNotFoundError:
        log("[INFO] No estaba instalado en inicio")
    except Exception as e:
        log(f"[ERROR] {e}")

def main():
    crear_directorio()

    if len(sys.argv) > 1:
        if sys.argv[1] == "--instalar":
            instalar_inicio_windows()
            return
        elif sys.argv[1] == "--desinstalar":
            desinstalar_inicio_windows()
            return
        elif sys.argv[1] == "--una-vez":
            descargar_logs("manual")
            return

    monitorear()

if __name__ == "__main__":
    main()
