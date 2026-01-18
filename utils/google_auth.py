"""
Utilidad centralizada para autenticación con Google APIs
Elimina duplicación de código en adapters
"""

import os
import json
import gspread
from google.oauth2.service_account import Credentials

# Scopes comunes para Google Sheets
GOOGLE_SHEETS_SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive'
]

# Ruta por defecto del archivo de credenciales local
DEFAULT_CREDENTIALS_FILE = "C:\\Users\\PC 1\\bubbly-subject-412101-c969f4a975c5.json"


def obtener_credenciales(credentials_file: str = None, scopes: list = None) -> Credentials:
    """
    Obtiene credenciales de Google desde variable de entorno o archivo local.

    Prioridad:
    1. Variable de entorno GOOGLE_APPLICATION_CREDENTIALS_JSON (Railway/Render)
    2. Archivo local de credenciales

    Args:
        credentials_file: Ruta al archivo de credenciales (opcional)
        scopes: Lista de scopes de Google API (opcional)

    Returns:
        Credentials: Objeto de credenciales de Google

    Raises:
        Exception: Si no se pueden obtener credenciales
    """
    if scopes is None:
        scopes = GOOGLE_SHEETS_SCOPES

    if credentials_file is None:
        credentials_file = DEFAULT_CREDENTIALS_FILE

    # Intentar obtener credenciales desde variable de entorno (Railway/Render)
    credentials_json = os.getenv('GOOGLE_APPLICATION_CREDENTIALS_JSON')

    if credentials_json:
        print("   Usando credenciales desde variable de entorno")
        credentials_dict = json.loads(credentials_json)
        creds = Credentials.from_service_account_info(
            credentials_dict,
            scopes=scopes
        )
    else:
        print("   Usando credenciales desde archivo local")
        creds = Credentials.from_service_account_file(
            credentials_file,
            scopes=scopes
        )

    return creds


def crear_cliente_gspread(credentials_file: str = None, scopes: list = None) -> gspread.Client:
    """
    Crea y retorna un cliente de gspread autenticado.

    Args:
        credentials_file: Ruta al archivo de credenciales (opcional)
        scopes: Lista de scopes de Google API (opcional)

    Returns:
        gspread.Client: Cliente autenticado de gspread
    """
    creds = obtener_credenciales(credentials_file, scopes)
    client = gspread.authorize(creds)
    return client


def abrir_spreadsheet_por_url(client: gspread.Client, url: str) -> gspread.Spreadsheet:
    """
    Abre un spreadsheet por URL.

    Args:
        client: Cliente de gspread autenticado
        url: URL del spreadsheet

    Returns:
        gspread.Spreadsheet: Spreadsheet abierto

    Raises:
        Exception: Si no se puede abrir el spreadsheet
    """
    try:
        spreadsheet = client.open_by_url(url)
        return spreadsheet
    except Exception as e:
        print(f"   Error al abrir spreadsheet: {e}")
        print(f"   Verifica que el Service Account tiene acceso al spreadsheet")
        raise


def abrir_spreadsheet_por_id(client: gspread.Client, spreadsheet_id: str) -> gspread.Spreadsheet:
    """
    Abre un spreadsheet por ID (key).

    Args:
        client: Cliente de gspread autenticado
        spreadsheet_id: ID del spreadsheet (key)

    Returns:
        gspread.Spreadsheet: Spreadsheet abierto

    Raises:
        Exception: Si no se puede abrir el spreadsheet
    """
    try:
        spreadsheet = client.open_by_key(spreadsheet_id)
        return spreadsheet
    except Exception as e:
        print(f"   Error al abrir spreadsheet: {e}")
        print(f"   Verifica que el Service Account tiene acceso al spreadsheet")
        raise


def obtener_hoja(spreadsheet: gspread.Spreadsheet, nombre_hoja: str) -> gspread.Worksheet:
    """
    Obtiene una hoja específica del spreadsheet.

    Args:
        spreadsheet: Spreadsheet abierto
        nombre_hoja: Nombre de la hoja a obtener

    Returns:
        gspread.Worksheet: Hoja obtenida

    Raises:
        Exception: Si no se encuentra la hoja
    """
    try:
        hoja = spreadsheet.worksheet(nombre_hoja)
        return hoja
    except Exception as e:
        hojas_disponibles = [ws.title for ws in spreadsheet.worksheets()]
        print(f"   Error: No se encontró la hoja '{nombre_hoja}'")
        print(f"   Hojas disponibles: {hojas_disponibles}")
        raise
