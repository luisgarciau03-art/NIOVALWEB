"""
Clase base para adaptadores de Google Sheets
Elimina duplicación de código de autenticación y operaciones comunes
"""

import gspread
from typing import Dict, List, Optional, Any
from datetime import datetime

# Importar utilidades centralizadas
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from utils.google_auth import (
    crear_cliente_gspread,
    abrir_spreadsheet_por_url,
    abrir_spreadsheet_por_id,
    obtener_hoja,
    DEFAULT_CREDENTIALS_FILE
)


class BaseGoogleSheetsAdapter:
    """
    Clase base abstracta para adaptadores de Google Sheets.
    Proporciona funcionalidad común de autenticación y operaciones básicas.
    """

    def __init__(
        self,
        spreadsheet_url: str = None,
        hoja_nombre: str = None,
        credentials_file: str = None,
        spreadsheet_id: str = None
    ):
        """
        Inicializa la conexión con Google Sheets.

        Args:
            spreadsheet_url: URL del spreadsheet (usar esto O spreadsheet_id)
            hoja_nombre: Nombre de la hoja principal
            credentials_file: Ruta al archivo de credenciales (opcional)
            spreadsheet_id: ID del spreadsheet (alternativa a URL)
        """
        self.credentials_file = credentials_file or DEFAULT_CREDENTIALS_FILE
        self.spreadsheet_url = spreadsheet_url
        self.spreadsheet_id = spreadsheet_id
        self.hoja_nombre = hoja_nombre

        # Conectar
        self.client = self._autenticar()
        self.spreadsheet = self._abrir_spreadsheet()
        self.hoja = self._obtener_hoja()

    def _autenticar(self) -> gspread.Client:
        """Autentica con Google usando las credenciales centralizadas"""
        try:
            client = crear_cliente_gspread(self.credentials_file)
            print(f"   Autenticado correctamente con Google Sheets")
            return client
        except Exception as e:
            print(f"   Error al autenticar: {e}")
            raise

    def _abrir_spreadsheet(self) -> gspread.Spreadsheet:
        """Abre el spreadsheet por URL o ID"""
        try:
            if self.spreadsheet_url:
                spreadsheet = abrir_spreadsheet_por_url(self.client, self.spreadsheet_url)
            elif self.spreadsheet_id:
                spreadsheet = abrir_spreadsheet_por_id(self.client, self.spreadsheet_id)
            else:
                raise ValueError("Debe proporcionar spreadsheet_url o spreadsheet_id")
            print(f"   Spreadsheet abierto: {spreadsheet.title}")
            return spreadsheet
        except Exception as e:
            print(f"   Error al abrir spreadsheet: {e}")
            raise

    def _obtener_hoja(self) -> gspread.Worksheet:
        """Obtiene la hoja principal"""
        try:
            hoja = obtener_hoja(self.spreadsheet, self.hoja_nombre)
            print(f"   Hoja encontrada: {self.hoja_nombre}")
            return hoja
        except Exception as e:
            print(f"   Error al obtener hoja: {e}")
            raise

    # === Operaciones comunes ===

    def obtener_todos_los_valores(self) -> List[List[str]]:
        """Obtiene todos los valores de la hoja"""
        return self.hoja.get_all_values()

    def obtener_fila(self, numero_fila: int) -> List[str]:
        """Obtiene los valores de una fila específica"""
        return self.hoja.row_values(numero_fila)

    def obtener_celda(self, fila: int, columna: int) -> str:
        """Obtiene el valor de una celda específica"""
        return self.hoja.cell(fila, columna).value or ""

    def actualizar_celda(self, fila: int, columna: int, valor: Any) -> None:
        """Actualiza el valor de una celda"""
        self.hoja.update_cell(fila, columna, valor)

    def actualizar_batch(self, actualizaciones: List[Dict]) -> None:
        """
        Actualiza múltiples celdas en una sola operación.

        Args:
            actualizaciones: Lista de dicts con 'range' y 'values'
                Ejemplo: [{'range': 'A1', 'values': [['valor']]}]
        """
        self.hoja.batch_update(actualizaciones)

    def agregar_fila(self, valores: List[Any]) -> None:
        """Agrega una fila al final de la hoja"""
        self.hoja.append_row(valores)

    def eliminar_fila(self, numero_fila: int) -> None:
        """Elimina una fila específica"""
        self.hoja.delete_rows(numero_fila)

    def contar_filas_con_datos(self) -> int:
        """
        Cuenta las filas que tienen datos en la columna A.

        Returns:
            Número de filas con datos (excluyendo encabezado)
        """
        todas_filas = self.hoja.get_all_values()
        filas_con_datos = 0

        for fila in todas_filas:
            if len(fila) > 0 and fila[0]:
                filas_con_datos += 1
            else:
                break

        return filas_con_datos

    def obtener_siguiente_fila_vacia(self) -> int:
        """
        Obtiene el número de la siguiente fila vacía.

        Returns:
            Número de fila donde insertar siguiente registro
        """
        return self.contar_filas_con_datos() + 1

    def obtener_timestamp(self) -> str:
        """Obtiene timestamp formateado para registro"""
        return datetime.now().strftime("%d/%m/%Y %H:%M:%S")

    def obtener_fecha(self) -> str:
        """Obtiene fecha formateada"""
        return datetime.now().strftime("%Y-%m-%d")

    def obtener_hora(self) -> str:
        """Obtiene hora formateada"""
        return datetime.now().strftime("%H:%M")
