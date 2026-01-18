"""
Utilidades comunes para el proyecto AgenteVentas
"""

from .google_auth import (
    obtener_credenciales,
    crear_cliente_gspread,
    abrir_spreadsheet_por_url,
    obtener_hoja,
    GOOGLE_SHEETS_SCOPES,
    DEFAULT_CREDENTIALS_FILE
)

from .phone_formatter import (
    normalizar_numero,
    formatear_numero_legible,
    validar_numero_mexicano,
    extraer_lada
)

__all__ = [
    # Google Auth
    'obtener_credenciales',
    'crear_cliente_gspread',
    'abrir_spreadsheet_por_url',
    'obtener_hoja',
    'GOOGLE_SHEETS_SCOPES',
    'DEFAULT_CREDENTIALS_FILE',
    # Phone Formatter
    'normalizar_numero',
    'formatear_numero_legible',
    'validar_numero_mexicano',
    'extraer_lada',
]
