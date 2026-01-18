"""
Adaptador para registrar logs de conversación en Google Sheets
Registra cada turno de conversación (BRUCE/CLIENTE) en la hoja LOGS

MIGRADO: Ahora hereda de BaseGoogleSheetsAdapter para eliminar código duplicado
"""

import gspread
from datetime import datetime
from typing import Optional

# Importar clase base
from adapters.google_sheets.base import BaseGoogleSheetsAdapter


class LogsSheetsAdapter(BaseGoogleSheetsAdapter):
    """Adaptador para escribir logs de conversación en Google Sheets"""

    # Configuración del spreadsheet (usa ID en lugar de URL)
    SPREADSHEET_ID = "1U_z1KNqCxSRZVi7wvO2FQH4zIdS_wxuafxj6YHdHEqg"
    HOJA_NOMBRE = "LOGS"

    def __init__(self):
        """Inicializa la conexión con la hoja LOGS"""
        # Llamar al constructor de la clase base (usando ID en lugar de URL)
        super().__init__(
            spreadsheet_id=self.SPREADSHEET_ID,
            hoja_nombre=self.HOJA_NOMBRE
        )
        # Alias para compatibilidad con código existente
        self.hoja_logs = self.hoja

        # Contador de IDs BRUCE (se incrementa por cada nueva conversación)
        self.contador_bruce = self._obtener_ultimo_id_bruce()

        print(f"✅ Conectado a hoja LOGS para registro de conversaciones")
        print(f"📊 Último ID BRUCE: BRUCE{self.contador_bruce:02d}")

    def _obtener_ultimo_id_bruce(self):
        """Obtiene el último ID BRUCE usado en la hoja"""
        try:
            # Leer columna B (IDs) desde fila 2 hasta el final
            ids = self.hoja_logs.col_values(2)

            # Buscar el ID BRUCE más alto
            max_id = 0
            for id_value in ids[1:]:  # Saltar encabezado
                if id_value.startswith("BRUCE"):
                    try:
                        numero = int(id_value.replace("BRUCE", ""))
                        if numero > max_id:
                            max_id = numero
                    except ValueError:
                        continue

            return max_id
        except Exception as e:
            print(f"⚠️ Error obteniendo último ID BRUCE: {e}")
            return 0

    def generar_nuevo_id_bruce(self):
        """
        Genera un nuevo ID BRUCE secuencial (BRUCE01, BRUCE02, etc.)
        RE-LEE el último ID desde la hoja cada vez para garantizar consecutividad
        incluso si el servidor se reinicia o hay llamadas concurrentes.
        """
        # Re-leer el último ID desde la hoja (no confiar solo en memoria)
        ultimo_id_en_hoja = self._obtener_ultimo_id_bruce()
        nuevo_id = ultimo_id_en_hoja + 1

        # Actualizar contador en memoria también
        self.contador_bruce = nuevo_id

        return f"BRUCE{nuevo_id:02d}"

    def registrar_mensaje(
        self,
        bruce_id: str,
        quien: str,  # "BRUCE" o "CLIENTE"
        mensaje: str,
        audio_info: str = "N/A",  # Info sobre cache/generado
        nombre_tienda: str = ""  # Nombre de la tienda
    ):
        """
        Registra un mensaje en la hoja LOGS (inserta al inicio, recorre lo anterior hacia abajo)

        Args:
            bruce_id: ID de la conversación (BRUCE01, BRUCE02, etc.)
            quien: "BRUCE" o "CLIENTE"
            mensaje: Texto del mensaje
            audio_info: Información sobre el audio (cache/generado/CLIENTE)
            nombre_tienda: Nombre de la tienda del cliente
        """
        try:
            # Formato de fecha: Solo fecha (YYYY-MM-DD)
            fecha = datetime.now().strftime("%Y-%m-%d")

            # Preparar fila para insertar
            # Columnas: Fecha | ID | CLIENTE/BRUCE | MENSAJE | Audio/Cache | Nombre de la tienda
            fila = [
                fecha,
                bruce_id,
                quien,
                mensaje,
                audio_info,
                nombre_tienda
            ]

            # INSERTAR en fila 2 (después de encabezados) para que lo nuevo quede arriba
            # Esto recorre automáticamente todo lo anterior hacia abajo
            try:
                self.hoja_logs.insert_row(fila, index=2, value_input_option='USER_ENTERED')
            except Exception as e:
                # Si falla insert_row (hoja vacía), usar append_row
                print(f"   ⚠️ insert_row falló, usando append_row: {e}")
                self.hoja_logs.append_row(fila, value_input_option='USER_ENTERED')

            print(f"📝 LOG registrado: {quien[:6]}... | {mensaje[:50]}...")

        except Exception as e:
            # No fallar la llamada si falla el log
            print(f"⚠️ Error registrando en LOGS (no crítico): {e}")

    def registrar_mensaje_bruce(
        self,
        bruce_id: str,
        mensaje: str,
        desde_cache: bool = False,
        cache_key: Optional[str] = None,
        tiempo_generacion: Optional[float] = None,
        nombre_tienda: str = ""
    ):
        """
        Registra un mensaje de BRUCE con información de audio

        Args:
            bruce_id: ID de la conversación (BRUCE01, BRUCE02, etc.)
            mensaje: Texto que dijo Bruce
            desde_cache: Si el audio vino del cache
            cache_key: Nombre de la key del cache (si aplica)
            tiempo_generacion: Tiempo que tardó en generar (si se generó)
            nombre_tienda: Nombre de la tienda
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

        self.registrar_mensaje(bruce_id, "BRUCE", mensaje, audio_info, nombre_tienda)

    def registrar_mensaje_cliente(
        self,
        bruce_id: str,
        mensaje: str,
        nombre_tienda: str = ""
    ):
        """
        Registra un mensaje del CLIENTE

        Args:
            bruce_id: ID de la conversación (BRUCE01, BRUCE02, etc.)
            mensaje: Texto que dijo el cliente
            nombre_tienda: Nombre de la tienda
        """
        self.registrar_mensaje(bruce_id, "CLIENTE", mensaje, "CLIENTE", nombre_tienda)

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
