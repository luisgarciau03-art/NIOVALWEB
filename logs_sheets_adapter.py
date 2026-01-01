"""
Adaptador para registrar logs de conversación en Google Sheets
Registra cada turno de conversación (BRUCE/CLIENTE) en la hoja LOGS
"""

import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
from typing import Optional


class LogsSheetsAdapter:
    """Adaptador para escribir logs de conversación en Google Sheets"""

    def __init__(self):
        """Inicializa la conexión con la hoja LOGS"""

        # Spreadsheet ID de LOGS (Llamadas Nioval)
        self.spreadsheet_id = "1U_z1KNqCxSRZVi7wvO2FQH4zIdS_wxuafxj6YHdHEqg"
        self.hoja_nombre = "LOGS"

        # Definir alcances
        self.scopes = [
            'https://www.googleapis.com/auth/spreadsheets',
            'https://www.googleapis.com/auth/drive'
        ]

        # Conectar
        self.client = self._autenticar()
        self.spreadsheet = self._abrir_spreadsheet()
        self.hoja_logs = self._obtener_hoja_logs()

        print(f"✅ Conectado a hoja LOGS para registro de conversaciones")

    def _autenticar(self):
        """Autentica con Google usando las credenciales (local o Railway/Render)"""
        try:
            import json
            import os

            # Intentar obtener credenciales desde variable de entorno (Railway/Render)
            credentials_json = os.getenv('GOOGLE_APPLICATION_CREDENTIALS_JSON')

            if credentials_json:
                # Estamos en producción, usar credenciales desde env
                print("🌐 Usando credenciales desde variable de entorno para LOGS")
                credentials_dict = json.loads(credentials_json)
                creds = Credentials.from_service_account_info(
                    credentials_dict,
                    scopes=self.scopes
                )
            else:
                # Desarrollo local
                print("💻 Usando credenciales locales para LOGS")
                creds = Credentials.from_service_account_file(
                    "bubbly-subject-412101-c969f4a975c5.json",
                    scopes=self.scopes
                )

            return gspread.authorize(creds)

        except Exception as e:
            print(f"❌ Error autenticando con Google Sheets (LOGS): {e}")
            raise

    def _abrir_spreadsheet(self):
        """Abre el spreadsheet de LOGS"""
        try:
            spreadsheet = self.client.open_by_key(self.spreadsheet_id)
            print(f"✅ Spreadsheet LOGS abierto: {spreadsheet.title}")
            return spreadsheet
        except Exception as e:
            print(f"❌ Error abriendo spreadsheet LOGS: {e}")
            raise

    def _obtener_hoja_logs(self):
        """Obtiene la hoja LOGS del spreadsheet"""
        try:
            hoja = self.spreadsheet.worksheet(self.hoja_nombre)
            print(f"✅ Hoja encontrada: {self.hoja_nombre}")
            return hoja
        except gspread.WorksheetNotFound:
            print(f"❌ No se encontró la hoja '{self.hoja_nombre}'")
            raise

    def registrar_mensaje(
        self,
        call_sid: str,
        quien: str,  # "BRUCE" o "CLIENTE"
        mensaje: str,
        audio_info: str = "N/A"  # Info sobre cache/generado
    ):
        """
        Registra un mensaje en la hoja LOGS

        Args:
            call_sid: ID de la llamada de Twilio
            quien: "BRUCE" o "CLIENTE"
            mensaje: Texto del mensaje
            audio_info: Información sobre el audio (cache/generado/N/A)
        """
        try:
            # Formato de fecha: YYYY-MM-DD HH:MM:SS
            fecha_hora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            # Preparar fila para insertar
            # Columnas: Fecha | ID | CLIENTE/BRUCE | MENSAJE | Audio/Cache
            fila = [
                fecha_hora,
                call_sid,
                quien,
                mensaje,
                audio_info
            ]

            # Agregar al final de la hoja
            self.hoja_logs.append_row(fila, value_input_option='USER_ENTERED')

            print(f"📝 LOG registrado: {quien[:6]}... | {mensaje[:50]}...")

        except Exception as e:
            # No fallar la llamada si falla el log
            print(f"⚠️ Error registrando en LOGS (no crítico): {e}")

    def registrar_mensaje_bruce(
        self,
        call_sid: str,
        mensaje: str,
        desde_cache: bool = False,
        cache_key: Optional[str] = None,
        tiempo_generacion: Optional[float] = None
    ):
        """
        Registra un mensaje de BRUCE con información de audio

        Args:
            call_sid: ID de la llamada
            mensaje: Texto que dijo Bruce
            desde_cache: Si el audio vino del cache
            cache_key: Nombre de la key del cache (si aplica)
            tiempo_generacion: Tiempo que tardó en generar (si se generó)
        """
        # Construir info de audio
        if desde_cache:
            if cache_key:
                audio_info = f"Cache ({cache_key[:30]}...)"
            else:
                audio_info = "Cache"
        elif tiempo_generacion is not None:
            audio_info = f"Generado ({tiempo_generacion:.2f}s)"
        else:
            audio_info = "Generado"

        self.registrar_mensaje(call_sid, "BRUCE", mensaje, audio_info)

    def registrar_mensaje_cliente(
        self,
        call_sid: str,
        mensaje: str
    ):
        """
        Registra un mensaje del CLIENTE

        Args:
            call_sid: ID de la llamada
            mensaje: Texto que dijo el cliente
        """
        self.registrar_mensaje(call_sid, "CLIENTE", mensaje, "N/A")

    def registrar_evento(
        self,
        call_sid: str,
        evento: str
    ):
        """
        Registra un evento del sistema (inicio de llamada, despedida detectada, etc.)

        Args:
            call_sid: ID de la llamada
            evento: Descripción del evento
        """
        self.registrar_mensaje(call_sid, "SISTEMA", evento, "N/A")
