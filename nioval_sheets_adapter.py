"""
Adaptador específico para el Spreadsheet de NIOVAL
Conecta con la hoja "Bruce" (antes "LISTA DE CONTACTOS")
FIX 213: Renombrado de hoja 2026-01-14

MIGRADO: Ahora hereda de BaseGoogleSheetsAdapter para eliminar código duplicado
"""

import re
from typing import List, Dict, Optional
from datetime import datetime

# Importar clase base
from adapters.google_sheets.base import BaseGoogleSheetsAdapter


class NiovalSheetsAdapter(BaseGoogleSheetsAdapter):
    """Adaptador para trabajar con el spreadsheet existente de NIOVAL"""

    # Configuración del spreadsheet
    SPREADSHEET_URL = "https://docs.google.com/spreadsheets/d/1wgEentS16hJrcf6YdEnSpEBcp4SCBJ9TkOCZY439jV4/edit"
    # FIX 213: Cambio de nombre de hoja "LISTA DE CONTACTOS" -> "Bruce"
    HOJA_NOMBRE = "Bruce"

    def __init__(self):
        """Inicializa la conexión con el spreadsheet de NIOVAL"""
        # Llamar al constructor de la clase base
        super().__init__(
            spreadsheet_url=self.SPREADSHEET_URL,
            hoja_nombre=self.HOJA_NOMBRE
        )
        # Alias para compatibilidad con código existente
        self.hoja_contactos = self.hoja
        print(f"✅ Conectado a: {self.hoja_nombre}")

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

    def verificar_contacto_ya_llamado(self, fila: int) -> bool:
        """
        Verifica si un contacto ya fue llamado anteriormente
        Revisa si las columnas U (Referencia), V (Intentos buzón), W (Contexto) tienen contenido

        NOTA: Si el número en columna E cambió desde la última llamada, se considera NUEVO contacto

        Args:
            fila: Número de fila a verificar

        Returns:
            True si ya fue llamado (y número NO cambió), False si es primera vez o número cambió
        """
        try:
            # 1. Verificar si hay datos en U/V/W
            referencia = self.hoja_contactos.cell(fila, 21).value  # U
            intentos = self.hoja_contactos.cell(fila, 22).value    # V
            contexto = self.hoja_contactos.cell(fila, 23).value    # W

            tiene_historial = bool(
                (referencia and referencia.strip()) or
                (intentos and intentos.strip()) or
                (contexto and contexto.strip())
            )

            if not tiene_historial:
                # No hay historial, es primera vez
                return False

            # 2. Si tiene historial, verificar si el número cambió
            numero_cambio = self.verificar_cambio_numero(fila)

            if numero_cambio:
                print(f"🔄 Fila {fila}: Número cambió desde última llamada - permitir re-contacto")
                return False  # Permitir llamar aunque tenga historial

            # 3. Tiene historial y número NO cambió = ya fue llamado
            return True

        except Exception as e:
            print(f"⚠️ Error verificando si contacto fue llamado: {e}")
            return False  # En caso de error, asumir que no fue llamado

    def verificar_cambio_numero(self, fila: int) -> bool:
        """
        Verifica si el número en columna E cambió desde la última llamada

        Args:
            fila: Número de fila a verificar

        Returns:
            True si el número cambió, False si sigue igual o no hay registro previo
        """
        try:
            # Obtener número actual en columna E (índice 5)
            numero_actual = self.hoja_contactos.cell(fila, 5).value
            if not numero_actual:
                return False

            # Normalizar número actual
            numero_actual_normalizado = self.normalizar_numero(numero_actual)
            if not numero_actual_normalizado:
                return False

            # Obtener registro previo en columna U (formato: "NUM:6623534185|Primera llamada: 2025-01-15 10:30")
            registro_u = self.hoja_contactos.cell(fila, 21).value

            if not registro_u or not registro_u.strip():
                # No hay registro previo
                return False

            # Extraer número guardado del registro (formato: NUM:XXXXXXXXXX|...)
            if registro_u.startswith("NUM:"):
                numero_previo = registro_u.split("|")[0].replace("NUM:", "").strip()

                if numero_previo != numero_actual_normalizado:
                    print(f"   📞 Número anterior: {numero_previo}")
                    print(f"   📞 Número actual: {numero_actual_normalizado}")
                    return True

            return False

        except Exception as e:
            print(f"⚠️ Error verificando cambio de número: {e}")
            return False

    def marcar_primera_llamada(self, fila: int, numero_llamado: str = None):
        """
        Marca que se realizó la primera llamada a este contacto
        Guarda timestamp en columna U para indicar que ya fue contactado
        También guarda el número llamado para detectar cambios futuros

        Args:
            fila: Número de fila
            numero_llamado: Número de teléfono que se llamó (normalizado)
        """
        try:
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")

            # Si no se proporcionó número, obtenerlo de columna E
            if not numero_llamado:
                numero_raw = self.hoja_contactos.cell(fila, 5).value
                numero_llamado = self.normalizar_numero(numero_raw) if numero_raw else "DESCONOCIDO"

            # Formato: NUM:XXXXXXXXXX|Primera llamada: YYYY-MM-DD HH:MM
            marca = f"NUM:{numero_llamado}|Primera llamada: {timestamp}"

            # Guardar en columna U (índice 21)
            self.hoja_contactos.update_cell(fila, 21, marca)
            print(f"✅ Primera llamada marcada en fila {fila} (columna U) - Número: {numero_llamado}")

        except Exception as e:
            print(f"❌ Error al marcar primera llamada: {e}")

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
                            'referencia': fila[20] if len(fila) > 20 else "",  # U: Referencia (índice 20)
                            'contexto_reprogramacion': fila[22] if len(fila) > 22 else "",  # W: Contexto reprogramación (índice 22)

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
        FIX 113: Registra el email capturado en columna T
        (Eliminada columna AA que excedía los límites de la hoja)

        Args:
            fila: Número de fila
            email: Email capturado
        """
        try:
            # Columna T (índice 20) - email principal
            self.hoja_contactos.update_cell(fila, 20, email)
            print(f"✅ Email registrado en fila {fila} (columna T): {email}")
        except Exception as e:
            print(f"❌ Error al registrar email: {e}")

    def guardar_referencia(self, fila_destino: int, nombre_referidor: str, telefono_referidor: str = "", contexto: str = "", numero_llamado: str = None):
        """
        Guarda información de referencia en columna U del contacto destino
        IMPORTANTE: Preserva el número original para detectar cambios futuros

        Args:
            fila_destino: Fila del contacto que fue referido
            nombre_referidor: Nombre de quien refirió
            telefono_referidor: Teléfono de quien refirió (opcional)
            contexto: Contexto adicional (opcional)
            numero_llamado: Número que se llamó originalmente (para detectar cambios)
        """
        try:
            from datetime import datetime
            fecha = datetime.now().strftime("%Y-%m-%d")

            # Si no se proporcionó número, obtenerlo de columna E
            if not numero_llamado:
                numero_raw = self.hoja_contactos.cell(fila_destino, 5).value
                numero_llamado = self.normalizar_numero(numero_raw) if numero_raw else "DESCONOCIDO"

            # Formato: "NUM:XXXXXXXXXX|Ref: Juan (+523312345678) - 2025-12-28 - Encargado de compras"
            referencia = f"NUM:{numero_llamado}|Ref: {nombre_referidor}"
            if telefono_referidor:
                referencia += f" ({telefono_referidor})"
            referencia += f" - {fecha}"
            if contexto:
                referencia += f" - {contexto}"

            # Columna U (índice 21)
            self.hoja_contactos.update_cell(fila_destino, 21, referencia)
            print(f"✅ Referencia guardada en fila {fila_destino} (columna U): {referencia}")

        except Exception as e:
            print(f"❌ Error al guardar referencia: {e}")

    def obtener_referencia(self, fila: int) -> Optional[str]:
        """
        Obtiene la información de referencia de la columna U
        Elimina el prefijo NUM:XXXXXXXXXX| si existe

        Args:
            fila: Número de fila

        Returns:
            Texto de referencia o None si no existe
        """
        try:
            # Columna U (índice 21)
            valor = self.hoja_contactos.cell(fila, 21).value

            if valor and valor.strip():
                # Si tiene formato NUM:XXXXXXXXXX|..., extraer solo la parte después del pipe
                if "|" in valor:
                    return valor.split("|", 1)[1].strip()
                return valor.strip()
            return None

        except Exception as e:
            print(f"⚠️ Error al obtener referencia: {e}")
            return None

    def obtener_historial_completo(self, fila: int) -> Dict[str, str]:
        """
        Obtiene todo el historial de contacto previo (columnas U, V, W)
        Útil para cargar contexto cuando hay cambio de número

        Args:
            fila: Número de fila

        Returns:
            Dict con 'referencia', 'intentos_buzon', 'contexto_reprogramacion'
        """
        try:
            # Obtener valores de U, V, W
            referencia = self.hoja_contactos.cell(fila, 21).value  # U
            intentos = self.hoja_contactos.cell(fila, 22).value    # V
            contexto = self.hoja_contactos.cell(fila, 23).value    # W

            # Procesar referencia (quitar prefijo NUM:)
            referencia_limpia = None
            if referencia and referencia.strip():
                if "|" in referencia:
                    referencia_limpia = referencia.split("|", 1)[1].strip()
                else:
                    referencia_limpia = referencia.strip()

            return {
                'referencia': referencia_limpia,
                'intentos_buzon': intentos.strip() if intentos else None,
                'contexto_reprogramacion': contexto.strip() if contexto else None
            }

        except Exception as e:
            print(f"⚠️ Error al obtener historial completo: {e}")
            return {
                'referencia': None,
                'intentos_buzon': None,
                'contexto_reprogramacion': None
            }

    def obtener_contador_intentos_buzon(self, fila: int) -> int:
        """
        Obtiene el número de intentos de buzón registrados para esta fila

        Args:
            fila: Número de fila

        Returns:
            Número de intentos (0, 1, o 2)
        """
        try:
            # Columna V (índice 22) guarda el contador de intentos de buzón
            valor = self.hoja_contactos.cell(fila, 22).value

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

            # Actualizar contador en columna V (índice 22)
            self.hoja_contactos.update_cell(fila, 22, str(nuevos_intentos))

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

    def guardar_contexto_reprogramacion(self, fila: int, fecha: str, motivo: str, notas: str = ""):
        """
        Guarda contexto de reprogramación en columna W

        Args:
            fila: Número de fila
            fecha: Fecha de reprogramación
            motivo: Motivo de la reprogramación
            notas: Notas adicionales
        """
        try:
            from datetime import datetime
            fecha_actual = datetime.now().strftime("%Y-%m-%d %H:%M")

            contexto = f"Reprog: {fecha} | {motivo}"
            if notas:
                contexto += f" | {notas}"
            contexto += f" | Registrado: {fecha_actual}"

            # Columna W (índice 23)
            self.hoja_contactos.update_cell(fila, 23, contexto)
            print(f"✅ Contexto de reprogramación guardado en fila {fila} (columna W): {contexto[:50]}...")

        except Exception as e:
            print(f"❌ Error al guardar contexto de reprogramación: {e}")

    def obtener_contexto_reprogramacion(self, fila: int) -> Optional[str]:
        """
        Obtiene el contexto de reprogramación de la columna W

        Args:
            fila: Número de fila

        Returns:
            Texto de contexto o None si no existe
        """
        try:
            # Columna W (índice 23)
            valor = self.hoja_contactos.cell(fila, 23).value

            if valor and valor.strip():
                return valor.strip()
            return None

        except Exception as e:
            print(f"⚠️ Error al obtener contexto de reprogramación: {e}")
            return None

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
