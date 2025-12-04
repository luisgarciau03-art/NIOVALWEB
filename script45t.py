"""
INSTRUCCIONES PARA RESOLVER CONFLICTOS DE GIT:

1. Busca las marcas de conflicto en este archivo:
    <<<<<<< HEAD
    (tu versión local)
    =======
    (versión remota)
    >>>>>>> main

2. Elige y edita el contenido correcto, eliminando las marcas <<<<<<<, =======, >>>>>>>.
3. Guarda el archivo.
4. En la terminal ejecuta:
    git add script45t.py
    git commit -m "Resuelve conflicto en script45t.py"
    git push
"""

import google.auth
import google_auth_oauthlib
# --- TEST DE SELENIUM Y LOGGING AL INICIO ---
import os
import time
import re
from time import sleep
from datetime import datetime
from typing import Optional

import subprocess
print("Chromium path:", subprocess.getoutput('which chromium'))
print("Chromium version:", subprocess.getoutput('chromium --version'))
print("Chromedriver path:", subprocess.getoutput('which chromedriver'))
print("Chromedriver version:", subprocess.getoutput('chromedriver --version'))
try:
    import google_auth_oauthlib
    import google.auth
    print("google-auth-oauthlib version:", google_auth_oauthlib.__version__)
    print("google-auth version:", google.auth.__version__)
except Exception as e:
    print("Error mostrando versión de google-auth-oauthlib/google-auth:", e)
try:
    import google_auth_oauthlib
    import google_auth
    print("google-auth-oauthlib version:", google_auth_oauthlib.__version__)
    print("google-auth version:", google_auth.__version__)
except Exception as e:
    print("Error mostrando versión de google-auth-oauthlib/google-auth:", e)
try:
    out = subprocess.getoutput('/usr/bin/chromium --headless --no-sandbox --disable-gpu --disable-dev-shm-usage --disable-software-rasterizer --window-size=1920,1080 --version')
    print("Chromium manual launch output:", out)
except Exception as e:
    print("Chromium manual launch error:", e)

# Test Selenium Chromium siempre al importar
def test_selenium_chromium():
    from selenium import webdriver
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.chrome.options import Options
    import os

    chromedriver_path = os.environ.get('CHROMEDRIVER_PATH', '/usr/bin/chromedriver')
    chrome_bin = os.environ.get('CHROME_BIN', '/usr/bin/chromium')
    opts = Options()
    opts.add_argument('--headless')
    opts.add_argument('--no-sandbox')
    opts.add_argument('--disable-dev-shm-usage')
    opts.add_argument('--disable-gpu')
    opts.add_argument('--disable-software-rasterizer')
    opts.add_argument('--window-size=1920,1080')
    opts.binary_location = chrome_bin

    try:
        driver = webdriver.Chrome(service=Service(chromedriver_path), options=opts)
        driver.get("chrome://version")
        print("Selenium Chromium test: OK")
        driver.quit()
    except Exception as e:
        print("Selenium Chromium test: ERROR", e)

test_selenium_chromium()

print("CHROME_BIN exists:", os.path.isfile(os.environ.get('CHROME_BIN', '/usr/bin/chromium')))
print("CHROMEDRIVER_PATH exists:", os.path.isfile(os.environ.get('CHROMEDRIVER_PATH', '/usr/bin/chromedriver')))
print("CHROME_BIN is executable:", os.access(os.environ.get('CHROME_BIN', '/usr/bin/chromium'), os.X_OK))
print("CHROMEDRIVER_PATH is executable:", os.access(os.environ.get('CHROMEDRIVER_PATH', '/usr/bin/chromedriver'), os.X_OK))

import gspread
from oauth2client.service_account import ServiceAccountCredentials
import requests
# ...existing code...

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import WebDriverException, TimeoutException

from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

SPREADSHEET_ID_COT = "1oS6a6LCRJNGombl-nHo58uDORdKrNqhvq4FJEzi_1-Q"
SPREADSHEET_ID_VENTAS = "1Dlpm6swrNSPnt9L5tQhoi2OMln0bb8bqqgeLACNos98"
SHEET_NAME_VENTAS = "Ventas"
CONTACTOS_SHEET_ID = "1oEtAiYaYVdOnEum3tbp_BminBUdj06JzXqJhaOVQFlk"
CONTACTOS_SHEET_TAB = "BD CONTACTOS"
MENSAJES_SHEET_NAME = "Mensajes"
GID_COT = "1320728772"
LOCAL_BASE_DIR = r'C:\Users\PC 1\Cotizaciones'
SUBDIR_NOVIEMBRE = "Noviembre"

CLIENT_SECRET_FILE = "webniovalpdfs.json"
TOKEN_FILE = "token2.json"
PDF_RANGE = "A1:I44"
DRIVE_FOLDER_ID = "1ppeYE8f_uWkXITmwkC2_U7ozvoYxLh28"

NEW_SPREADSHEET_ID = "1oS6a6LCRJNGombl-nHo58uDORdKrNqhvq4FJEzi_1-Q"
BD_SHEET_NAME = "BD"
SCOPES = [
    'https://www.googleapis.com/auth/drive.file',
    'https://www.googleapis.com/auth/spreadsheets'
]

CHROME_BINARY = 'C:/Program Files/Google/Chrome/Application/chrome.exe'
CHROME_PROFILE_PATH = "C:/Users/PC 1/ChromeSeleniumProfile"
CHROME_PROFILE_DIR = "Default"
T_CHAT_LOAD = 30
WAIT_TIMEOUT = 90
T_SHORT = 1

DOC_EXTS = ['.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx', '.zip']

TELEGRAM_TOKEN = "8467383503:AAFIJUXpPDKBc-zwDiIjjj_6pvely6O45gs"
TELEGRAM_CHAT_ID = "5838212022"

def avisar_telegram(mensaje):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    try:
        response = requests.post(url, data={
            "chat_id": TELEGRAM_CHAT_ID,
            "text": mensaje
        })
        if response.status_code == 200:
            print("Aviso enviado a Telegram.")
        else:
            print("Error enviando aviso a Telegram:", response.text)
    except Exception as e:
        print("Excepción al avisar por Telegram:", e)

def get_mes_actual():
    meses = [
        "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
        "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"
    ]
    return meses[datetime.now().month-1]

def crear_ruta_mes(base_dir, subdir=None):
    mes = get_mes_actual()
    ruta = os.path.join(base_dir, subdir if subdir else mes)
    if not os.path.exists(ruta):
        os.makedirs(ruta)
    return ruta

def clean_filename(filename):
    filename = filename.replace("  ", " ")
    return "".join([c for c in filename if c.isalnum() or c in " .-_"]).rstrip()

def authenticate():
    # Si estamos en Render, usar solo Service Account
    if os.environ.get('RENDER', None) == 'true' or os.environ.get('RENDER', None) == 'True':
        import json
        from google.oauth2.service_account import Credentials as ServiceAccountCreds
        secret_path = '/etc/secrets/GOOGLE_SERVICE_ACCOUNT_JSON'  # Usar el nombre exacto del archivo en Render
        if not os.path.exists(secret_path):
            raise Exception(f"No se encontró el archivo de Service Account en {secret_path}. Verifica el nombre en Secret Files de Render.")
        with open(secret_path, 'r') as f:
            info = json.load(f)
        creds = ServiceAccountCreds.from_service_account_info(info, scopes=SCOPES)
        return creds
    # Local: usar OAuth si no existe token
    creds = None
    if os.path.exists(TOKEN_FILE):
        from google.oauth2.credentials import Credentials
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
    if not creds or not creds.valid:
        from google_auth_oauthlib.flow import InstalledAppFlow
        flow = InstalledAppFlow.from_client_secrets_file(
            CLIENT_SECRET_FILE,
            SCOPES
        )
        creds = flow.run_local_server(
            port=8765,
            authorization_prompt_message=None,
            success_message=None,
            open_browser=True,
            access_type='offline',
            prompt='consent'
        )
        with open(TOKEN_FILE, 'w') as token:
            token.write(creds.to_json())
    return creds

def actualizar_num_factura(sheet):
    num_factura_actual = sheet.acell('G10').value
    match = re.match(r"(\d+)(.*)", num_factura_actual)
    if match:
        numero = int(match.group(1))
        sufijo = match.group(2)
        nuevo_num_factura = str(numero + 1) + sufijo
        sheet.update_acell('G10', nuevo_num_factura)
        print(f"Número de factura actualizado a {nuevo_num_factura}.")
        avisar_telegram(f"Número de factura actualizado a {nuevo_num_factura}.")
        return nuevo_num_factura
    else:
        print("El formato actual de G10 no permite sumar +1.")
        avisar_telegram("El formato actual de G10 no permite sumar +1.")
        return num_factura_actual

def extraer_datos_cotizacion():
    try:
        import traceback
        print("[LOG] extraer_datos_cotizacion: INICIO")
        # Definir valores por defecto para evitar NameError
        # Obtener nombre del cliente y número de factura actualizado
        creds = authenticate()
        gc = gspread.authorize(creds)
        sheet = gc.open_by_key(SPREADSHEET_ID_COT).worksheet("Factura")
        nombre_cliente = sheet.acell('D10').value
        print(f"[DEBUG] Valor original de D10 (nombre_cliente): '{nombre_cliente}'")
        if not nombre_cliente or not nombre_cliente.strip():
            avisar_telegram("⚠️ D10 vacío en Factura. Usando 'cliente' como nombre.")
            nombre_cliente = "cliente"
        else:
            nombre_cliente = nombre_cliente.strip()
        print(f"[DEBUG] Nombre cliente final usado: '{nombre_cliente}'")
        esquema = sheet.acell('D12').value or ''
        print(f"[DEBUG] Valor original de D12 (esquema): '{esquema}'")
        esquema = esquema.strip()
        print(f"[DEBUG] Esquema detectado D12: '{esquema}'")
        monto = sheet.acell('H43').value or ''
        print(f"[DEBUG] Valor original de H43 (monto): '{monto}'")
        monto = monto.strip()
        print(f"[DEBUG] Monto detectado H43: '{monto}'")
        num_factura_actual = sheet.acell('G10').value or "1"
        print(f"[DEBUG] Valor original de G10 (num_factura_actual): '{num_factura_actual}'")
        match = re.match(r"(\d+)(.*)", num_factura_actual)
        if match:
            numero = int(match.group(1)) + 1
            sufijo = match.group(2)
            num_factura = f"{numero}{sufijo}"
            # Actualizar G10 con el nuevo número de factura
            try:
                sheet.update_acell('G10', num_factura)
                print(f"[DEBUG] G10 actualizado a: {num_factura}")
                avisar_telegram(f"G10 actualizado a: {num_factura}")
            except Exception as e:
                print(f"[ERROR] No se pudo actualizar G10: {e}")
                avisar_telegram(f"❌ Error actualizando G10: {e}")
        else:
            num_factura = num_factura_actual
        pdf_filename = f"{nombre_cliente} - {num_factura}.pdf"
        # Guardar en /tmp/ si estamos en Render, en cwd si es local
        if os.environ.get('RENDER', None) == 'true' or os.environ.get('RENDER', None) == 'True':
            pdf_path = f"/tmp/{pdf_filename}"
        else:
            pdf_path = os.path.join(os.getcwd(), pdf_filename)
        # Usar la función global authenticate()
        # Construir la URL correctamente
        pdf_url = (
            f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID_COT}/export?"
            f"format=pdf"
            f"&portrait=true"
            f"&fitw=true"
            f"&sheetnames=false"
            f"&printtitle=false"
            f"&pagenumbers=false"
            f"&gridlines=false"
            f"&fzr=true"
            f"&range={PDF_RANGE}"
            f"&gid={GID_COT}"
        )
        print("[LOG] extraer_datos_cotizacion: Descargando PDF solo del rango", PDF_RANGE)
        response = requests.get(pdf_url)
        if response.ok:
            print("[LOG] extraer_datos_cotizacion: PDF descargado correctamente por requests.")
            # Guardar PDF temporalmente solo para subirlo a Drive, luego eliminarlo
            with open(pdf_path, "wb") as f:
                f.write(response.content)
            # Validar que el PDF se haya guardado correctamente
            if not os.path.exists(pdf_path) or os.path.getsize(pdf_path) == 0:
                print(f"[ERROR] El PDF no se generó correctamente: {pdf_path}")
                avisar_telegram(f"❌ El PDF no se generó correctamente: {pdf_path}")
                drive_url = None
            else:
                # Subir PDF a Dropbox siempre
                from subir_dropbox import subir_pdf_a_dropbox
                dropbox_url = subir_pdf_a_dropbox(pdf_path, pdf_filename)
                if not dropbox_url:
                    print(f"[ERROR] No se obtuvo URL de Dropbox tras subir el PDF: {pdf_path}")
                    avisar_telegram(f"❌ No se obtuvo URL de Dropbox tras subir el PDF: {pdf_path}")
                else:
                    print(f"[LOG] PDF subido a Dropbox: {dropbox_url}")
            # Eliminar el PDF local después de subirlo
            try:
                os.remove(pdf_path)
            except Exception:
                pass
            avisar_telegram(f"✅ PDF cargado a Dropbox: {dropbox_url}")
            print("[LOG] extraer_datos_cotizacion: FIN flujo requests.")
            return pdf_path, pdf_filename, dropbox_url, nombre_cliente, esquema, monto, num_factura
        else:
            print("[LOG] extraer_datos_cotizacion: Error descargando PDF por requests. Intentando Selenium...")
            avisar_telegram("❌ Error descargando PDF de cotización, intentando con Selenium autenticado...")
            try:
                from selenium import webdriver
                from selenium.webdriver.chrome.service import Service
                from selenium.webdriver.chrome.options import Options
                from webdriver_manager.chrome import ChromeDriverManager
                opts = Options()
                # opts.add_argument('--headless')  # Eliminado para abrir ventana
                opts.add_argument('--no-sandbox')
                opts.add_argument('--disable-dev-shm-usage')
                print("[LOG] extraer_datos_cotizacion: Iniciando Selenium WebDriver...")
                driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=opts)
                print("[LOG] extraer_datos_cotizacion: Selenium WebDriver iniciado.")
                driver.get(pdf_url)
                print("[LOG] extraer_datos_cotizacion: Navegando a PDF URL con Selenium.")
                sleep(5)
                with open(pdf_path, "wb") as f:
                    f.write(driver.page_source.encode())
                print(f"[LOG] extraer_datos_cotizacion: PDF guardado con Selenium como: {pdf_path}")
                driver.quit()
                avisar_telegram(f"✅ PDF descargado con Selenium: {pdf_path}")
                drive_url = export_pdf_drive(pdf_path)
                avisar_telegram(f"✅ PDF cargado a Drive: {drive_url}")
                print("[LOG] extraer_datos_cotizacion: FIN flujo Selenium.")
                return pdf_path, pdf_filename, drive_url, nombre_cliente, num_factura
            except Exception as e:
                print(f"[ERROR] extraer_datos_cotizacion: Error en Selenium al descargar PDF: {e}")
                print(traceback.format_exc())
                avisar_telegram(f"❌ Error en Selenium al descargar PDF: {e}")
                return None, None, None, nombre_cliente, esquema, monto, num_factura
        print("[LOG] extraer_datos_cotizacion: FIN")
    except Exception as e:
        import traceback
        print(f"[ERROR] extraer_datos_cotizacion: Error general: {e}")
        print(traceback.format_exc())
        avisar_telegram(f"❌ Error en export_pdf_rango: {e}")
        return None, None, None, nombre_cliente, esquema, monto, num_factura

def export_pdf_drive(pdf_path):
    """
    Sube el PDF a Drive en la carpeta compartida y retorna el enlace público.
    """
    try:
        print(f'[DEBUG] Subiendo archivo a Drive: {pdf_path}')
        if not os.path.exists(pdf_path) or os.path.getsize(pdf_path) == 0:
            print(f"[ERROR] El archivo PDF no existe o está vacío: {pdf_path}")
            avisar_telegram(f"❌ El archivo PDF no existe o está vacío: {pdf_path}")
            return None
        # Usar la misma autenticación que para la hoja BD
        creds = authenticate()
        service = build('drive', 'v3', credentials=creds)
        file_metadata = {
            'name': os.path.basename(pdf_path),
            'mimeType': 'application/pdf',
            'parents': [DRIVE_FOLDER_ID]  # Carpeta de Drive
        }
        media = MediaFileUpload(pdf_path, mimetype='application/pdf', resumable=True)
        file = service.files().create(body=file_metadata, media_body=media, fields='id').execute()
        print(f"[DEBUG] Archivo creado en Drive con id: {file['id']}")
        # Haz público el archivo
        service.permissions().create(
            fileId=file['id'],
            body={'type': 'anyone', 'role': 'reader'}
        ).execute()
        drive_url = f"https://drive.google.com/file/d/{file['id']}/view?usp=sharing"
        print(f"[DEBUG] Archivo subido a Google Drive: {drive_url}")
        avisar_telegram(f"✅ Archivo PDF subido a Drive: {drive_url}")
        return drive_url
    except Exception as e:
        avisar_telegram(f"❌ Error subiendo PDF a Drive: {e}")
        print("Error en export_pdf_drive:", e)
        return None

# --- UTILIDAD PARA FLASK: SUBIDA PDF A DRIVE VIA OAUTH ---
def upload_pdf_to_drive_oauth(pdf_path, pdf_filename, drive_folder_id=None, client_secret_file=None, token_file=None):
    """
    Sube un PDF a Google Drive usando OAuth y retorna el enlace público.
    Parámetros:
        pdf_path: Ruta local del PDF
        pdf_filename: Nombre del archivo PDF
        drive_folder_id: ID de la carpeta destino en Drive
        client_secret_file: Ruta al client_secret.json
        token_file: Ruta al token.json
    """
    import os
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.oauth2.credentials import Credentials

    SCOPES = ['https://www.googleapis.com/auth/drive.file']
    drive_folder_id = drive_folder_id or '1ppeYE8f_uWkXITmwkC2_U7ozvoYxLh28'
    client_secret_file = client_secret_file or 'webniovalpdfs.json'
    token_file = token_file or 'token2.json'

    try:
        print(f"[LOG] Iniciando subida de PDF a Drive via OAuth: {pdf_path}, nombre: {pdf_filename}")
        creds = None
        # Si estamos en Render, usar Service Account siempre
        if os.environ.get('RENDER', None) == 'true' or os.environ.get('RENDER', None) == 'True':
            import json
            from google.oauth2.service_account import Credentials as ServiceAccountCreds
            secret_path = '/etc/secrets/GOOGLE_SERVICE_ACCOUNT_JSON'
            if not os.path.exists(secret_path):
                raise Exception(f"No se encontró el archivo de Service Account en {secret_path}. Verifica el nombre en Secret Files de Render.")
            with open(secret_path, 'r') as f:
                info = json.load(f)
            creds = ServiceAccountCreds.from_service_account_info(info, scopes=SCOPES)
        else:
            if os.path.exists(token_file):
                print(f"[LOG] Usando token existente: {token_file}")
                creds = Credentials.from_authorized_user_file(token_file, SCOPES)
            if not creds or not creds.valid:
                print(f"[LOG] Token inválido o no existe, iniciando flujo OAuth...")
                flow = InstalledAppFlow.from_client_secrets_file(client_secret_file, SCOPES)
                creds = flow.run_local_server(port=8765)
                with open(token_file, 'w') as token:
                    token.write(creds.to_json())
        print("[LOG] Autenticación completada.")
        service = build('drive', 'v3', credentials=creds)
        print("[LOG] Servicio Google Drive inicializado.")
        file_metadata = {
            'name': pdf_filename,
            'mimeType': 'application/pdf',
            'parents': [drive_folder_id]
        }
        print(f"[LOG] Metadata del archivo: {file_metadata}")
        media = MediaFileUpload(pdf_path, mimetype='application/pdf', resumable=True)
        print(f"[LOG] MediaFileUpload creado para: {pdf_path}")
        file = service.files().create(body=file_metadata, media_body=media, fields='id').execute()
        print(f"[LOG] Archivo creado en Drive con id: {file['id']}")
        service.permissions().create(fileId=file['id'], body={'type': 'anyone', 'role': 'reader'}).execute()
        print(f"[LOG] Permisos públicos asignados al archivo: {file['id']}")
        drive_url = f"https://drive.google.com/file/d/{file['id']}/view?usp=sharing"
        print(f"[LOG] URL final de Drive: {drive_url}")
        return drive_url
    except Exception as e:
        import traceback
        print(f"[ERROR] Error subiendo PDF a Drive: {e}")
        print(traceback.format_exc())
        avisar_telegram(f"❌ Error subiendo PDF a Drive: {e}")
        return None

def insertar_fila_ventas(link_pdf, nombre_cliente, total_factura, num_factura, esquema, mes_actual):
    try:
        creds = authenticate()
        gc = gspread.authorize(creds)
        sheet = gc.open_by_key(SPREADSHEET_ID_VENTAS).worksheet(SHEET_NAME_VENTAS)
        print(f"[DEBUG] Antes de insertar fila vacía en Ventas...")
        sheet.insert_row([''] * 15, 2)
        print(f"[DEBUG] Fila vacía insertada en posición 2.")
        fecha_hoy = datetime.now().strftime("%d/%m/%Y")
        # Limpiar fecha
        if isinstance(fecha_hoy, str):
            fecha_hoy = fecha_hoy.strip().lstrip("'").rstrip("'")
        # Limpiar monto total
        if isinstance(total_factura, str):
            total_factura = total_factura.strip().lstrip("'").rstrip("'")
        # Limpiar número de factura
        if isinstance(num_factura, str):
            num_factura = num_factura.strip().lstrip("'").rstrip("'")
        # Forzar que todos los valores sean cadenas y nunca None
        def safe_str(val):
            return str(val) if val is not None else ''
        fila = [
            safe_str(fecha_hoy),          # A2: Fecha
            safe_str(nombre_cliente),     # B2: Nombre
            '',                           # C2: VACÍO
            '',                           # D2: VACÍO
            safe_str(esquema),            # E2: Esquema
            'WEB',                        # F2: WEB (cotización vía web)
            safe_str(mes_actual),         # G2: Mes
            safe_str(total_factura),      # H2: Monto total
            '',                           # I2: VACÍO
            safe_str(num_factura),        # J2: Número Factura
            safe_str(link_pdf),           # K2: URL PDF
            '',                           # L2: PAGO
            '',                           # M2: Dias
            '',                           # N2: VACÍO
            ''                            # O2: VACÍO
        ]
        print(f"[DEBUG] Datos de la fila a actualizar en A2:O2: {fila}")
        # Actualizar la fila en el rango A2:O2
        try:
            print("[DEBUG] Intentando actualizar la fila en Ventas...")
            result = sheet.update([fila], 'A2:O2')
            print(f"[DEBUG] Resultado de sheet.update: {result}")
            avisar_telegram(f"📅 Fecha actual '{fecha_hoy}' actualizada en A2 de la hoja Ventas.")
            print(f"Fila insertada y B2 actualizado en hoja Ventas. Cliente='{nombre_cliente}'")
            avisar_telegram(f"➡️ Fila Ventas actualizada para cliente {nombre_cliente}.")
            return result
        except Exception as e:
            print(f"[ERROR] No se pudo actualizar la fila en Ventas: {e}")
            avisar_telegram(f"❌ Error actualizando fila Ventas: {e}")
            raise
    except Exception as e:
        print(f"[ERROR] Error al insertar fila de ventas: {e}")
        avisar_telegram(f"❌ Error al insertar fila de ventas: {e}")
        raise

def buscar_telefono(nombre_cliente: str, sheet_contactos) -> Optional[str]:
    try:
        tel_rows = sheet_contactos.get_all_values()
        print(f"Buscando el teléfono para: '{nombre_cliente.strip()}'")
        for idx, tel_row in enumerate(tel_rows[1:], start=2):
            tienda_tel = tel_row[0].strip().lower() if len(tel_row) > 0 else ""
            telefono = tel_row[18].strip() if len(tel_row) > 18 else ""
            print(f"Fila {idx}: tienda='{tienda_tel}', telefono='{telefono}'")
            if tienda_tel == nombre_cliente.strip().lower():
                if telefono and not telefono.startswith('+'):
                    telefono = '+' + telefono
                print(f">> Match! {tienda_tel} == {nombre_cliente.strip().lower()} → {telefono}")
                return telefono
        avisar_telegram(f"❌ No se encontró teléfono para cliente: {nombre_cliente}")
        return None
    except Exception as e:
        avisar_telegram(f"❌ Error buscando teléfono: {e}")
        return None

def obtener_numero_mensaje(sheet_ventas, sheet_contactos, sheet_mensajes):
    try:
        fila2 = sheet_ventas.row_values(2)
        nombre_cliente = fila2[1].strip()  # B2 (no A2)
        print('Nombre cliente detectado B2:', nombre_cliente)
        telefono = buscar_telefono(nombre_cliente, sheet_contactos)
        mensajes_list = sheet_mensajes.col_values(3)[2:]
        if not mensajes_list:
            mensajes_list = ["Estimado cliente, adjunto su cotización"]
        print(f"Mensajes detectados desde hoja Mensajes C3:C: {mensajes_list}")

        if not telefono:
            print(f"No se encontró teléfono para '{nombre_cliente}', favor de ingresar manualmente:")
            avisar_telegram(f"❌ Por favor ingresa manualmente el teléfono para {nombre_cliente}.")
            telefono = input("Introduce el teléfono con +52...: ").strip()
        return telefono, mensajes_list
    except Exception as e:
        avisar_telegram(f"❌ Error en obtención de teléfono/mensajes: {e}")
        raise

def crear_opciones(user_data_dir=CHROME_PROFILE_PATH, profile_dir=CHROME_PROFILE_DIR) -> Options:
    opts = Options()
    print("[LOG] crear_opciones: RENDER=", os.environ.get('RENDER', None))
    if os.environ.get('RENDER', None) == 'true' or os.environ.get('RENDER', None) == 'True':
        # Configuración headless para Render
        opts.add_argument('--headless')
        opts.add_argument('--no-sandbox')
        opts.add_argument('--disable-dev-shm-usage')
        opts.add_argument('--disable-gpu')
        opts.add_argument('--disable-extensions')
        opts.add_argument('--window-size=1920,1080')
        opts.add_argument('--disable-software-rasterizer')
        opts.add_experimental_option("excludeSwitches", ["enable-automation"])
        opts.add_experimental_option('useAutomationExtension', False)
        opts.binary_location = os.environ.get('CHROME_BIN', '/usr/bin/chromium')
        print(f"[LOG] crear_opciones: binary_location={opts.binary_location}")
    else:
        # Configuración local (PC)
        opts.add_argument(f"--user-data-dir={user_data_dir}")
        opts.add_argument(f"--profile-directory={profile_dir}")
        if CHROME_BINARY and os.path.isfile(CHROME_BINARY):
            opts.binary_location = CHROME_BINARY
        opts.add_argument('--no-sandbox')
        opts.add_argument('--disable-dev-shm-usage')
        opts.add_argument('--disable-gpu')
        opts.add_argument('--disable-extensions')
        opts.add_experimental_option("excludeSwitches", ["enable-automation"])
        opts.add_experimental_option('useAutomationExtension', False)
        print(f"[LOG] crear_opciones: binary_location={getattr(opts, 'binary_location', None)}")
    print("[LOG] crear_opciones: args=", opts.arguments)
    return opts


def iniciar_driver(user_data_dir=CHROME_PROFILE_PATH, profile_dir=CHROME_PROFILE_DIR) -> webdriver.Chrome:
    print("[LOG] iniciar_driver: RENDER=", os.environ.get('RENDER', None))
    if os.environ.get('RENDER', None) == 'true' or os.environ.get('RENDER', None) == 'True':
        chromedriver_path = os.environ.get('CHROMEDRIVER_PATH', '/usr/bin/chromedriver')
        print(f"[LOG] iniciar_driver: chromedriver_path={chromedriver_path}")
        svc = Service(chromedriver_path)
        opts = crear_opciones()
        try:
            driver = webdriver.Chrome(service=svc, options=opts)
            print("[LOG] iniciar_driver: Selenium Chrome iniciado correctamente.")
            return driver
        except Exception as e:
            print(f"[ERROR] iniciar_driver: Selenium no pudo iniciar Chrome. Error: {e}")
            raise
    else:
        # Local: usa webdriver_manager y perfil de usuario
        print("[LOG] iniciar_driver: modo local")
        svc = Service(ChromeDriverManager().install())
        opts = crear_opciones(user_data_dir, profile_dir)
        try:
            driver = webdriver.Chrome(service=svc, options=opts)
            print("[LOG] iniciar_driver: Selenium Chrome iniciado correctamente (local).")
            return driver
        except Exception as e:
            print(f"[ERROR] iniciar_driver: Selenium no pudo iniciar Chrome (local). Error: {e}")
            raise

def detect_invalid_popup(driver) -> bool:
    """
    Detecta el modal de error de WhatsApp Web si el número es inválido,
    tolerando recarga/refresco del DOM.
    """
    try:
        xp_exact = '//div[normalize-space(text())="El número de teléfono compartido a través de la dirección URL no es válido."]'
        if driver.find_elements(By.XPATH, xp_exact):
            print('[DEBUG] Detectado modal exacto WhatsApp')
            return True
        xp_contains = '//div[contains(translate(text(),"ÁÉÍÓÚáéíóúABCDEFGHIJKLMNOPQRSTUVWXYZ","áéíóúabcdefghijklmnopqrstuvwxyz"), "el número de teléfono compartido a través de la dirección url no es válido")]'
        if driver.find_elements(By.XPATH, xp_contains):
            print('[DEBUG] Detectado modal contains WhatsApp')
            return True
        for div in driver.find_elements(By.XPATH, '//div'):
            try:
                txt = div.text.strip().lower()
                if "número de teléfono" in txt and "no es válido" in txt:
                    print('[DEBUG] Detectado modal WhatsApp por div:', txt)
                    return True
            except Exception as e:
                print('[DEBUG] Ignorado div por error:', e)
                continue
        xp_ok = '//span[normalize-space(text())="OK" or normalize-space(text())="Ok" or normalize-space(text())="ok"]'
        if driver.find_elements(By.XPATH, xp_ok):
            src = (driver.page_source or "").lower()
            if "el número de teléfono compartido a través de la dirección url no es válido" in src \
               or ("número de teléfono" in src and "no es válido" in src):
                print('[DEBUG] Detectado modal OK WhatsApp + mensaje en page_source')
                return True
        src = (driver.page_source or "").lower()
        if "el número de teléfono compartido a través de la dirección url no es válido" in src:
            print('[DEBUG] Detectado [page_source]')
            return True
        if "número de teléfono" in src and "no es válido" in src:
            print('[DEBUG] Detectado [page_source] fragmento')
            return True
    except Exception as e:
        print("Error grave en detect_invalid_popup:", e)
    return False

def abrir_chat(driver: webdriver.Chrome, telefono: str, max_wait_override: Optional[int] = None) -> str:
    url = f"https://web.whatsapp.com/send?phone={telefono.replace('+','')}&text="
    driver.get(url)
    print(f"Abriendo chat {telefono} ...")
    avisar_telegram(f"Abriendo chat para {telefono} en WhatsApp ...")
    chat_xpath = '//div[@contenteditable="true"]'
    max_wait = max_wait_override if max_wait_override is not None else WAIT_TIMEOUT
    t0 = time.time()
    while time.time() - t0 < max_wait:
        sleep(1)
        if detect_invalid_popup(driver):
            avisar_telegram(f"❌ *ERROR WHATSAPP*\n*Número inválido detectado.*\nTeléfono: `{telefono}`\nURL: {url}")
            return 'invalido'
        chat_boxes = driver.find_elements(By.XPATH, chat_xpath)
        for el in chat_boxes:
            try:
                if el.is_displayed():
                    sleep(0.5)
                    avisar_telegram(f"✅ Chat abierto correctamente para: {telefono}")
                    return 'ok'
            except Exception:
                continue
    print("No se pudo cargar el chat (timeout).")
    avisar_telegram(f"❌ *ERROR WHATSAPP*\n*URL no carga o timeout.*\nTeléfono: `{telefono}`\nURL: {url}")
    return 'fail'

def find_message_box(driver, timeout=30):
    xpath = '//div[@contenteditable="true" and (@data-tab="10" or contains(@aria-placeholder,"Escribe"))]'
    try:
        elems = WebDriverWait(driver, timeout).until(EC.presence_of_all_elements_located((By.XPATH, xpath)))
        for e in elems:
            if e.is_displayed():
                return e
    except Exception:
        pass
    try:
        elems = driver.find_elements(By.XPATH, '//div[@contenteditable="true"]')
        for e in elems:
            if e.is_displayed():
                return e
    except Exception:
        pass
    return None

def focus_and_place_caret_at_end(driver, el):
    driver.execute_script("arguments[0].scrollIntoView({block:'center'});", el)
    try:
        el.click()
    except Exception:
        driver.execute_script("arguments[0].click();", el)
    sleep(0.08)
    js = """
    const el = arguments[0];
    el.focus();
    const range = document.createRange();
    range.selectNodeContents(el);
    range.collapse(false);
    const sel = window.getSelection();
    sel.removeAllRanges();
    sel.addRange(range);
    """
    driver.execute_script(js, el)
    sleep(0.08)
    return True

def enviar_mensaje(driver, mensaje):
    try:
        msg_box = find_message_box(driver, timeout=30)
        if not msg_box:
            print("No se encontró el área de mensaje.")
            avisar_telegram("❌ No se encontró el área de mensaje en WhatsApp Web. Intenta manualmente.")
            return
        focus_and_place_caret_at_end(driver, msg_box)
        try:
            msg_box.send_keys(mensaje)
            sleep(0.2)
            msg_box.send_keys(Keys.ENTER)
            print("Mensaje enviado (send_keys).")
            avisar_telegram(f"Mensaje enviado: {mensaje[:60]}...")
            sleep(T_SHORT)
            return
        except WebDriverException:
            try:
                import pyperclip
            except Exception:
                pyperclip = None
            if pyperclip:
                try:
                    pyperclip.copy(mensaje)
                    focus_and_place_caret_at_end(driver, msg_box)
                    ActionChains(driver).key_down(Keys.CONTROL).send_keys('v').key_up(Keys.CONTROL).perform()
                    sleep(0.15)
                    ActionChains(driver).send_keys(Keys.ENTER).perform()
                    print("Mensaje enviado (clipboard).")
                    avisar_telegram(f"Mensaje enviado por clipboard: {mensaje[:60]}...")
                    sleep(T_SHORT)
                    return
                except Exception:
                    pass
        safe = mensaje.replace("\\", "\\\\").replace("'", "\\'").replace("\n", "\\n")
        js = "arguments[0].focus(); arguments[0].innerText = arguments[1]; arguments[0].dispatchEvent(new InputEvent('input',{bubbles:true}));"
        driver.execute_script(js, msg_box, safe)
        sleep(0.13)
        msg_box.send_keys(Keys.ENTER)
        print("Mensaje enviado (JS injection).")
        avisar_telegram(f"Mensaje enviado por JS injection: {mensaje[:60]}...")
        sleep(T_SHORT)
    except Exception as e:
        avisar_telegram(f"❌ Error al enviar mensaje WhatsApp: {e}")

def tipo_archivo(path):
    ext = os.path.splitext(path)[1].lower()
    if ext in DOC_EXTS:
        return "documento"
    return None

def click_attach_button(driver):
    try:
        attach_btn = WebDriverWait(driver, 20).until(
            EC.element_to_be_clickable((By.XPATH, '//span[@data-icon="plus-rounded"]'))
        )
        attach_btn.click()
        sleep(1)
        return True
    except Exception as e:
        print("No se pudo hacer click en el botón Adjuntar:", e)
        avisar_telegram("❌ No se pudo hacer click en el botón Adjuntar de WhatsApp Web.")
        return False

def click_documentos(driver):
    try:
        doc_btn = WebDriverWait(driver, 20).until(
            EC.element_to_be_clickable((By.XPATH, '//span[@data-icon="document-filled-refreshed"]'))
        )
        doc_btn.click()
        sleep(1)
        return True
    except Exception as e:
        print("No se encontró el botón Documentos:", e)
        avisar_telegram("❌ No se encontró el botón Documentos en WhatsApp Web.")
        return False

def find_file_input_by_position(driver, tipo="documento", timeout=20):
    end_time = time.time() + timeout
    while time.time() < end_time:
        inputs = driver.find_elements(By.XPATH, '//input[@type="file"]')
        if tipo == "documento" and len(inputs) >= 1:
            if inputs[0].is_enabled():
                return inputs[0]
        sleep(0.2)
    print(f"No se encontró input para cargar archivo: {tipo}")
    avisar_telegram(f"❌ No se encontró input para cargar archivo tipo {tipo} en WhatsApp Web.")
    return None

def enviar_archivo(driver, archivo_path):
    tipo = tipo_archivo(archivo_path)
    try:
        if tipo == "documento":
            if not click_attach_button(driver): return
            if not click_documentos(driver): return
            inp = find_file_input_by_position(driver, tipo="documento")
        else:
            print("Tipo de archivo no soportado:", archivo_path)
            avisar_telegram(f"❌ Tipo de archivo no soportado para enviar: {archivo_path}")
            return
        if not inp:
            print("No se encontró input para cargar archivo.")
            avisar_telegram(f"❌ No se encontró input para cargar archivo {archivo_path}.")
            return
        inp.send_keys(archivo_path)
        print("Archivo cargado:", archivo_path)
        avisar_telegram(f"PDF cargado para envío: {archivo_path}")
        sleep(3)
        actions = ActionChains(driver)
        actions.send_keys(Keys.ENTER)
        actions.perform()
        print("Simulación de tecla ENTER para enviar.")
        avisar_telegram(f"PDF enviado por WhatsApp: {archivo_path}")
        sleep(3)
    except Exception as e:
        avisar_telegram(f"❌ Error enviando archivo por WhatsApp: {e}")

def enviar_cotizacion_por_whatsapp(numero_destino, mensajes, archivo_pdf):
    driver = None
    try:
        driver = iniciar_driver(CHROME_PROFILE_PATH, CHROME_PROFILE_DIR)
        driver.get("https://web.whatsapp.com/")
        print("Abre WhatsApp Web y escanea el QR si corresponde (solo la primera vez).")
        avisar_telegram("Esperando escaneo QR de WhatsApp Web para continuar... Si ya está abierta la sesión, continúa sin escaneo.")
        sleep(T_CHAT_LOAD)
        chat_status = abrir_chat(driver, numero_destino, max_wait_override=WAIT_TIMEOUT)
        if chat_status != 'ok':
            print(f"No se pudo cargar el chat para el número: {numero_destino}")
            avisar_telegram(f"❌ No se pudo cargar el chat para el número: {numero_destino}. Flujo detenido.")
            driver.quit()
            return
        sleep(2)
        for mensaje in mensajes:
            enviar_mensaje(driver, mensaje)
            sleep(1)
        enviar_archivo(driver, archivo_pdf)
        print("Cotización enviada por WhatsApp.")
        avisar_telegram("✅ Cotización enviada con éxito por WhatsApp (mensajes + PDF).")
        sleep(8)
        driver.quit()
    except Exception as e:
        print("Error enviando por WhatsApp:", e)
        avisar_telegram(f"❌ Error al enviar cotización por WhatsApp: {e}")
        if driver:
            driver.quit()

def guardar_productos_en_bd(productos, nombre, esquema, metodo_pago):
    """
    Guarda los productos agregados en la hoja BD y actualiza G1, G2, G3 con los datos de usuario.
    productos: lista de dicts con keys: SKU, Nombre, Cantidad, Precio
    nombre: nombre del usuario
    esquema: esquema comercial
    metodo_pago: método de pago
    """
    creds = authenticate()
    gc = gspread.authorize(creds)
    sheet = gc.open_by_key(NEW_SPREADSHEET_ID).worksheet(BD_SHEET_NAME)
    # Actualiza G1, G2, G3
    sheet.update_acell('G1', nombre)
    sheet.update_acell('G2', esquema)
    sheet.update_acell('G3', metodo_pago)
    # Borra el contenido previo de A2:D1000 (excepto encabezados)
    try:
        sheet.batch_clear(['A2:D1000'])
    except Exception as e:
        print(f"Error al limpiar rango A2:D1000: {e}")
    filas = [[prod.get('SKU', ''), prod.get('Nombre', ''), prod.get('Cantidad', ''), prod.get('Precio', '')] for prod in productos]
    print(f"Filas a insertar en BD: {filas}")
    if filas and any(any(cell for cell in fila) for fila in filas):
        # Escribe directamente en el rango A2:D (no insert_rows)
        rango = f"A2:D{len(filas)+1}"
        sheet.update(rango, filas)
        print(f"Productos escritos en hoja BD en rango {rango}.")
        avisar_telegram(f"Productos escritos en hoja BD para {nombre} en rango {rango}.")
    else:
        print("No se recibieron productos para insertar en hoja BD.")
        avisar_telegram(f"No se recibieron productos para insertar en hoja BD para {nombre}.")

def main():
    try:
        errores = []
        urls_local = []
        urls_drive = []
        ahora = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        avisar_telegram(f"🔔 [{ahora}] Inicio de proceso de cotización automatizada...")

        # Llamar solo una vez a extraer_datos_cotizacion y usar los valores correctos
        pdf_path, pdf_filename, drive_url, nombre_cliente, esquema, monto, num_factura = extraer_datos_cotizacion()
        if pdf_path:
            urls_local.append(pdf_path)
        if drive_url:
            urls_drive.append(drive_url)

        if pdf_path is None:
            avisar_telegram("❌ Proceso abortado porque no se obtuvo el PDF de cotización.")
            errores.append("PDF local no obtenido.")
            print("No se pudo obtener el PDF. Flujo detenido.")
            return

        mes_actual = get_mes_actual()

        sheet_ventas = insertar_fila_ventas(drive_url or "", nombre_cliente, monto, num_factura, esquema, mes_actual)
        creds = authenticate()
        gc = gspread.authorize(creds)
        sheet_contactos = gc.open_by_key(CONTACTOS_SHEET_ID).worksheet(CONTACTOS_SHEET_TAB)
        sheet_mensajes = gc.open_by_key(CONTACTOS_SHEET_ID).worksheet(MENSAJES_SHEET_NAME)
        numero_destino, mensajes = obtener_numero_mensaje(sheet_ventas, sheet_contactos, sheet_mensajes)

        avisar_telegram(f"🔔 Enviando cotización a WhatsApp número: {numero_destino} ...")
        try:
            enviar_cotizacion_por_whatsapp(numero_destino, mensajes, pdf_path)
        except Exception as e:
            errores.append(f"Error enviando por WhatsApp ({numero_destino}): {e}")

        ahora_fin = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        resumen = f"🔔 [{ahora_fin}] Proceso FINALIZADO.\n\n"
        resumen += "*URLs PDF Local:*\n" + ("\n".join(urls_local) if urls_local else "No generado.") + "\n\n"
        resumen += "*URLs PDF Drive:*\n" + ("\n".join(urls_drive) if urls_drive else "No subido.") + "\n\n"
        if errores:
            resumen += "*ERRORES DETECTADOS:*\n" + "\n".join(errores)
        else:
            resumen += "No se detectaron errores en el proceso. ✅"
        avisar_telegram(resumen)
    except Exception as e_main:
        avisar_telegram(f"❌ Error general en el proceso principal: {e_main}")

def export_pdf_rango(nombre_cliente, num_factura):
    """
    Wrapper para exportar PDF de cotización y subirlo a Drive.
    Reutiliza la lógica existente de extraer_datos_cotizacion.
    """
    try:
        # extraer_datos_cotizacion returns 5 values, but we only need the first three
        result = extraer_datos_cotizacion()
        pdf_path, pdf_filename, drive_url = result[:3]
        return pdf_path, pdf_filename, drive_url
    except Exception as e:
        avisar_telegram(f"❌ Error en export_pdf_rango wrapper: {e}")
        return None, None, None

def test_selenium_chromium():
    from selenium import webdriver
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.chrome.options import Options
    import os

    chromedriver_path = os.environ.get('CHROMEDRIVER_PATH', '/usr/bin/chromedriver')
    chrome_bin = os.environ.get('CHROME_BIN', '/usr/bin/chromium')
    opts = Options()
    opts.add_argument('--headless')
    opts.add_argument('--no-sandbox')
    opts.add_argument('--disable-dev-shm-usage')
    opts.add_argument('--disable-gpu')
    opts.add_argument('--disable-software-rasterizer')
    opts.add_argument('--window-size=1920,1080')
    opts.binary_location = chrome_bin

    try:
        driver = webdriver.Chrome(service=Service(chromedriver_path), options=opts)
        driver.get("chrome://version")
        print("Selenium Chromium test: OK")
        driver.quit()
    except Exception as e:
        print("Selenium Chromium test: ERROR", e)

# Ejecutar test al inicio
if __name__ == "__main__":
    test_selenium_chromium()
    try:
        errores = []
        urls_local = []
        urls_drive = []
        ahora = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        avisar_telegram(f"🔔 [{ahora}] Inicio de proceso de cotización automatizada...")

        # Extraer todos los datos necesarios
        result = extraer_datos_cotizacion()
        pdf_path = result[0]
        pdf_filename = result[1]
        drive_url = result[2]
        nombre_cliente = result[3]
        esquema = result[4]
        monto = result[5]
        num_factura = result[6]
        mes_actual = get_mes_actual()

        if pdf_path:
            urls_local.append(pdf_path)
        if drive_url:
            urls_drive.append(drive_url)

        if pdf_path is None:
            avisar_telegram("❌ Proceso abortado porque no se obtuvo el PDF de cotización.")
            errores.append("PDF local no obtenido.")
            print("No se pudo obtener el PDF. Flujo detenido.")
        else:
            print("[DEBUG] Llamando a insertar_fila_ventas...")
            # link_pdf, nombre_cliente, total_factura, num_factura, esquema, mes_actual
            result_ventas = insertar_fila_ventas(drive_url or "", nombre_cliente, monto, num_factura, esquema, mes_actual)
            print(f"[DEBUG] Resultado de insertar_fila_ventas: {result_ventas}")

        ahora_fin = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        resumen = f"🔔 [{ahora_fin}] Proceso FINALIZADO.\n\n"
        resumen += "*URLs PDF Local:*\n" + ("\n".join(urls_local) if urls_local else "No generado.") + "\n\n"
        resumen += "*URLs PDF Drive:*\n" + ("\n".join(urls_drive) if urls_drive else "No subido.") + "\n\n"
        if errores:
            resumen += "*ERRORES DETECTADOS:*\n" + "\n".join(errores)
        else:
            resumen += "No se detectaron errores en el proceso. ✅"
        avisar_telegram(resumen)
    except Exception as e_main:
        avisar_telegram(f"❌ Error general en el proceso principal: {e_main}")


