"""
Adaptador específico para el Spreadsheet de NIOVAL
Conecta con la hoja "Bruce" existente
"""

import gspread
from google.oauth2.service_account import Credentials
import re
from typing import List, Dict, Optional
from datetime import datetime


class NiovalSheetsAdapter:
    """Adaptador para trabajar con el spreadsheet existente de NIOVAL"""

    def __init__(self):
        """Inicializa la conexión con el spreadsheet de NIOVAL"""

        # Credenciales y configuración
        self.credentials_file = "C:\\Users\\PC 1\\bubbly-subject-412101-c969f4a975c5.json"
        self.spreadsheet_url = "https://docs.google.com/spreadsheets/d/1wgEentS16hJrcf6YdEnSpEBcp4SCBJ9TkOCZY439jV4/edit"
        self.hoja_nombre = "Bruce"

        # Definir alcances
        self.scopes = [
            'https://www.googleapis.com/auth/spreadsheets',
            'https://www.googleapis.com/auth/drive'
        ]

        # Conectar
        self.client = self._autenticar()
        self.spreadsheet = self._abrir_spreadsheet()
        self.hoja_contactos = self._obtener_hoja_contactos()

        print(f"✅ Conectado a: {self.hoja_nombre}")

    def _autenticar(self):
        """Autentica con Google usando las credenciales (local o Render)"""
        try:
            import json
            import os

            # Intentar obtener credenciales desde variable de entorno (Render)
            credentials_json = os.getenv('GOOGLE_APPLICATION_CREDENTIALS_JSON')

            if credentials_json:
                # Estamos en Render/producción, usar credenciales desde env
                print("🌐 Usando credenciales desde variable de entorno (Render)")
                credentials_dict = json.loads(credentials_json)
                creds = Credentials.from_service_account_info(
                    credentials_dict,
                    scopes=self.scopes
                )
            else:
                # Estamos en local, usar archivo
                print("💻 Usando credenciales desde archivo local")
                creds = Credentials.from_service_account_file(
                    self.credentials_file,
                    scopes=self.scopes
                )

            client = gspread.authorize(creds)
            print("✅ Autenticado correctamente con Google Sheets")
            return client
        except Exception as e:
            print(f"❌ Error al autenticar: {e}")
            if not os.getenv('GOOGLE_APPLICATION_CREDENTIALS_JSON'):
                print(f"   Verifica que el archivo existe: {self.credentials_file}")
            else:
                print(f"   Verifica que la variable GOOGLE_APPLICATION_CREDENTIALS_JSON sea válida")
            raise

    def _abrir_spreadsheet(self):
        """Abre el spreadsheet por URL"""
        try:
            spreadsheet = self.client.open_by_url(self.spreadsheet_url)
            print(f"✅ Spreadsheet abierto: {spreadsheet.title}")
            return spreadsheet
        except Exception as e:
            print(f"❌ Error al abrir spreadsheet: {e}")
            print(f"   Verifica que el Service Account tiene acceso al spreadsheet")
            raise

    def _obtener_hoja_contactos(self):
        """Obtiene la hoja de contactos"""
        try:
            hoja = self.spreadsheet.worksheet(self.hoja_nombre)
            print(f"✅ Hoja encontrada: {self.hoja_nombre}")
            return hoja
        except Exception as e:
            print(f"❌ Error: No se encontró la hoja '{self.hoja_nombre}'")
            print(f"   Hojas disponibles: {[ws.title for ws in self.spreadsheet.worksheets()]}")
            raise

    def normalizar_numero(self, numero: str) -> Optional[str]:
        """
        Normaliza diferentes formatos de números mexicanos al formato estándar

        Ejemplos de entrada:
        - "662 101 2000" → "+526621012000"
        - "323 112 7516" → "+523231127516"
        - "81 1481 9779" → "+528114819779"
        - "662-101-2000" → "+526621012000"
        - "6621012000" → "+526621012000"

        Returns:
            Número en formato +52XXXXXXXXXX o None si es inválido
        """
        if not numero:
            return None

        # Limpiar el número: eliminar espacios, guiones, paréntesis
        numero_limpio = re.sub(r'[^\d+]', '', str(numero))

        # Si ya tiene +52, verificar longitud
        if numero_limpio.startswith('+52'):
            numero_limpio = numero_limpio[3:]  # Quitar +52
        elif numero_limpio.startswith('52'):
            numero_limpio = numero_limpio[2:]  # Quitar 52

        # Ahora numero_limpio debe tener 10 dígitos (número mexicano)
        if len(numero_limpio) == 10 and numero_limpio.isdigit():
            return f"+52{numero_limpio}"

        # Si tiene 11 dígitos y empieza con 1 (formato internacional alternativo)
        elif len(numero_limpio) == 11 and numero_limpio.startswith('1'):
            return f"+52{numero_limpio[1:]}"

        else:
            print(f"⚠️ Número inválido (no tiene 10 dígitos): {numero} → {numero_limpio}")
            return None

    def obtener_contactos_pendientes(self, limite: int = 100) -> List[Dict]:
        """
        Obtiene contactos pendientes de llamar

        Criterios:
        - Columna E tiene número de teléfono
        - Columna F está vacía (no se ha llamado)

        Args:
            limite: Número máximo de contactos a retornar

        Returns:
            Lista de diccionarios con datos de contactos
        """
        print(f"\n📋 Obteniendo contactos pendientes...")

        try:
            # Obtener todos los valores de la hoja
            datos = self.hoja_contactos.get_all_values()

            if not datos:
                print("⚠️ La hoja está vacía")
                return []

            # La primera fila son encabezados (asumiendo)
            # encabezados = datos[0]

            contactos_pendientes = []

            # Iterar desde la fila 2 (índice 1)
            for idx, fila in enumerate(datos[1:], start=2):  # start=2 porque es fila 2 en Sheets

                # Verificar que la fila tenga suficientes columnas
                if len(fila) < 6:  # Necesitamos al menos hasta columna F (índice 5)
                    continue

                # Columna E (índice 4) = Número de teléfono
                numero_raw = fila[4] if len(fila) > 4 else ""

                # Columna F (índice 5) = Estado de llamada
                estado_llamada = fila[5] if len(fila) > 5 else ""

                # Solo procesar si:
                # 1. Tiene número en columna E
                # 2. Columna F está vacía
                if numero_raw and not estado_llamada:

                    # Normalizar número
                    numero_normalizado = self.normalizar_numero(numero_raw)

                    if numero_normalizado:
                        # Obtener TODOS los datos de la fila (según estructura del spreadsheet)
                        contacto = {
                            # Datos básicos
                            'fila': idx,
                            'numero_raw': numero_raw,
                            'telefono': numero_normalizado,

                            # Columnas del spreadsheet (basado en la captura compartida)
                            'numero_fila': fila[0] if len(fila) > 0 else "",  # A: W
                            'nombre_negocio': fila[1] if len(fila) > 1 else f"Cliente {idx}",  # B: TIENDA
                            'ciudad': fila[2] if len(fila) > 2 else "",  # C: CIUDAD
                            'categoria': fila[3] if len(fila) > 3 else "Ferretería",  # D: CATEGORIA
                            # E: CONTACTO (ya lo tenemos como telefono)
                            # F: RESPUESTA (estado_llamada - usada para filtrar)
                            'porcentajes': fila[6] if len(fila) > 6 else "",  # G: PORCENTAJES
                            'domicilio': fila[7] if len(fila) > 7 else "",  # H: Domicilio
                            'puntuacion': fila[8] if len(fila) > 8 else "",  # I: Puntuacion
                            'resenas': fila[9] if len(fila) > 9 else "",  # J: Reseñas
                            'maps': fila[10] if len(fila) > 10 else "",  # K: Maps
                            'link': fila[11] if len(fila) > 11 else "",  # L: Link
                            'horario': fila[12] if len(fila) > 12 else "",  # M: Horario
                            'estatus': fila[13] if len(fila) > 13 else "",  # N: Estatus
                            'latitud': fila[14] if len(fila) > 14 else "",  # O: Latitud
                            'longitud': fila[15] if len(fila) > 15 else "",  # P: Longitud
                            'medida': fila[16] if len(fila) > 16 else "",  # Q: Medida
                            'esquema': fila[17] if len(fila) > 17 else "",  # R: Esquema
                            'fecha': fila[18] if len(fila) > 18 else "",  # S: Fecha
                            # T: Email (se escribe aquí cuando se captura)

                            # Flag para indicar que tiene datos previos
                            'tiene_datos_previos': True,
                        }

                        contactos_pendientes.append(contacto)

                        # Limitar resultados
                        if len(contactos_pendientes) >= limite:
                            break

            print(f"✅ Encontrados {len(contactos_pendientes)} contactos pendientes")

            # Mostrar primeros 3 como muestra
            if contactos_pendientes:
                print("\n📝 Primeros 3 contactos:")
                for c in contactos_pendientes[:3]:
                    print(f"   Fila {c['fila']}: {c['nombre_negocio']} - {c['telefono']}")

            return contactos_pendientes

        except Exception as e:
            print(f"❌ Error al obtener contactos: {e}")
            return []

    # NOTA: La columna F NO se debe llenar desde este sistema
    # Solo se verifica que esté vacía para determinar si el contacto debe ser llamado
    # La información de llamadas se guarda en otro spreadsheet

    def actualizar_numero_con_whatsapp(self, fila: int, whatsapp: str):
        """
        Reemplaza el número en columna E con el WhatsApp validado
        Formato: 662 108 5297 (10 dígitos con espacios cada 3)

        Args:
            fila: Número de fila
            whatsapp: Número de WhatsApp validado (formato +52XXXXXXXXXX)
        """
        try:
            # Extraer solo los 10 dígitos (quitar +52)
            if whatsapp.startswith('+52'):
                numero_limpio = whatsapp[3:]  # Quitar +52
            elif whatsapp.startswith('52'):
                numero_limpio = whatsapp[2:]  # Quitar 52
            else:
                numero_limpio = whatsapp

            # Formatear: 662 108 5297 (3 dígitos, espacio, 3 dígitos, espacio, 4 dígitos)
            if len(numero_limpio) == 10:
                numero_formateado = f"{numero_limpio[:3]} {numero_limpio[3:6]} {numero_limpio[6:]}"
            else:
                # Si no tiene 10 dígitos, usar tal cual
                numero_formateado = numero_limpio

            # Reemplazar en columna E (índice 5)
            self.hoja_contactos.update_cell(fila, 5, numero_formateado)
            print(f"✅ Número actualizado en fila {fila} (columna E): {numero_formateado}")
        except Exception as e:
            print(f"❌ Error al actualizar número: {e}")

    def registrar_email_capturado(self, fila: int, email: str):
        """
        Registra el email capturado en columna T

        Args:
            fila: Número de fila
            email: Email capturado
        """
        try:
            # Columna T (índice 20)
            self.hoja_contactos.update_cell(fila, 20, email)
            print(f"✅ Email registrado en fila {fila} (columna T): {email}")
        except Exception as e:
            print(f"❌ Error al registrar email: {e}")

    def obtener_contador_intentos_buzon(self, fila: int) -> int:
        """
        Obtiene el número de intentos de buzón registrados para esta fila

        Args:
            fila: Número de fila

        Returns:
            Número de intentos (0, 1, o 2)
        """
        try:
            # Columna U (índice 21) guarda el contador de intentos de buzón
            valor = self.hoja_contactos.cell(fila, 21).value

            if valor and valor.isdigit():
                return int(valor)
            return 0
        except Exception as e:
            print(f"⚠️ Error al obtener contador de intentos: {e}")
            return 0

    def marcar_intento_buzon(self, fila: int) -> int:
        """
        Marca un intento de buzón y retorna el número de intentos total

        Args:
            fila: Número de fila

        Returns:
            Número de intentos después de incrementar (1 o 2)
        """
        try:
            # Obtener contador actual
            intentos_actuales = self.obtener_contador_intentos_buzon(fila)
            nuevos_intentos = intentos_actuales + 1

            # Actualizar contador en columna U (índice 21)
            self.hoja_contactos.update_cell(fila, 21, str(nuevos_intentos))

            print(f"📞 Intento de buzón #{nuevos_intentos} registrado para fila {fila}")
            return nuevos_intentos

        except Exception as e:
            print(f"❌ Error al marcar intento de buzón: {e}")
            return 0

    def mover_fila_al_final(self, fila: int):
        """
        Mueve una fila al final de la hoja (para reintentar después)

        Args:
            fila: Número de fila a mover
        """
        try:
            print(f"📋 Moviendo fila {fila} al final de la lista...")

            # Obtener los datos de la fila
            datos_fila = self.hoja_contactos.row_values(fila)

            if not datos_fila:
                print(f"⚠️ La fila {fila} está vacía, no se puede mover")
                return

            # Limpiar columna F (estado) para que vuelva a aparecer como pendiente
            datos_fila[5] = ""  # Columna F (índice 5)

            # Obtener la última fila con datos
            todas_filas = self.hoja_contactos.get_all_values()
            ultima_fila_con_datos = len(todas_filas)
            nueva_fila = ultima_fila_con_datos + 1

            # Agregar la fila al final
            self.hoja_contactos.append_row(datos_fila)

            # Eliminar la fila original
            self.hoja_contactos.delete_rows(fila)

            print(f"✅ Fila movida de {fila} → {nueva_fila} (al final)")

        except Exception as e:
            print(f"❌ Error al mover fila: {e}")
            import traceback
            traceback.print_exc()

    def marcar_estado_final(self, fila: int, estado: str):
        """
        Marca el estado final de la llamada en columna F

        Args:
            fila: Número de fila
            estado: Estado a marcar (ej: "BUZON", "Respondio", "Telefono Incorrecto")
        """
        try:
            # Columna F (índice 6)
            self.hoja_contactos.update_cell(fila, 6, estado)
            print(f"✅ Estado marcado en fila {fila} (columna F): {estado}")
        except Exception as e:
            print(f"❌ Error al marcar estado: {e}")

    def obtener_estadisticas(self) -> Dict:
        """Obtiene estadísticas generales de la hoja"""
        try:
            datos = self.hoja_contactos.get_all_values()

            total_contactos = len(datos) - 1  # Menos header
            contactos_con_numero = 0
            contactos_llamados = 0
            contactos_pendientes = 0

            for fila in datos[1:]:
                if len(fila) > 4 and fila[4]:  # Tiene número
                    contactos_con_numero += 1

                    if len(fila) > 5 and fila[5]:  # Columna F tiene valor
                        contactos_llamados += 1
                    else:
                        contactos_pendientes += 1

            return {
                'total_contactos': total_contactos,
                'con_numero': contactos_con_numero,
                'llamados': contactos_llamados,
                'pendientes': contactos_pendientes,
                'porcentaje_completado': round((contactos_llamados / contactos_con_numero * 100) if contactos_con_numero > 0 else 0, 2)
            }

        except Exception as e:
            print(f"❌ Error al obtener estadísticas: {e}")
            return {}


# Testing y ejemplos de uso
if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("📊 NIOVAL SHEETS ADAPTER - TESTING")
    print("=" * 60 + "\n")

    try:
        # Inicializar adapter
        adapter = NiovalSheetsAdapter()

        print("\n--- ESTADÍSTICAS GENERALES ---")
        stats = adapter.obtener_estadisticas()
        print(f"Total contactos: {stats.get('total_contactos', 0)}")
        print(f"Con número: {stats.get('con_numero', 0)}")
        print(f"Llamados: {stats.get('llamados', 0)}")
        print(f"Pendientes: {stats.get('pendientes', 0)}")
        print(f"Progreso: {stats.get('porcentaje_completado', 0)}%")

        print("\n--- OBTENIENDO CONTACTOS PENDIENTES ---")
        contactos = adapter.obtener_contactos_pendientes(limite=5)

        if contactos:
            print(f"\n✅ {len(contactos)} contactos pendientes obtenidos")

            # Mostrar detalles
            for c in contactos:
                print(f"\nContacto Fila {c['fila']}:")
                print(f"  Negocio: {c['nombre_negocio']}")
                print(f"  Teléfono original: {c['numero_raw']}")
                print(f"  Teléfono normalizado: {c['telefono']}")
                print(f"  Ciudad: {c['ciudad']}")

        else:
            print("ℹ️ No hay contactos pendientes")

        # Test de normalización
        print("\n--- TEST DE NORMALIZACIÓN DE NÚMEROS ---")
        numeros_test = [
            "662 101 2000",
            "323 112 7516",
            "81 1481 9779",
            "662-101-2000",
            "6621012000",
            "+526621012000",
            "52 662 101 2000"
        ]

        for num in numeros_test:
            normalizado = adapter.normalizar_numero(num)
            print(f"{num:20} → {normalizado}")

    except Exception as e:
        print(f"\n❌ Error en testing: {e}")
        print("\n💡 Verifica:")
        print("   1. Que el archivo bubbly-subject-412101-c969f4a975c5.json existe")
        print("   2. Que el Service Account tiene acceso al spreadsheet")
        print("   3. Que la hoja 'Bruce' existe")

    print("\n" + "=" * 60)
