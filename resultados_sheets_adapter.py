"""
Adaptador para el Spreadsheet de RESULTADOS
Guarda las respuestas del formulario de 7 preguntas en "Respuestas de formulario 1"
"""

import gspread
from google.oauth2.service_account import Credentials
from typing import Dict, Optional
from datetime import datetime


class ResultadosSheetsAdapter:
    """Adaptador para guardar resultados de llamadas en Google Sheets"""

    def __init__(self):
        """Inicializa la conexión con el spreadsheet de resultados"""

        # Credenciales y configuración
        self.credentials_file = "C:\\Users\\PC 1\\bubbly-subject-412101-c969f4a975c5.json"
        self.spreadsheet_url = "https://docs.google.com/spreadsheets/d/1U_z1KNqCxSRZVi7wvO2FQH4zIdS_wxuafxj6YHdHEqg/edit"
        self.hoja_nombre = "Respuestas de formulario 1"

        # Definir alcances
        self.scopes = [
            'https://www.googleapis.com/auth/spreadsheets',
            'https://www.googleapis.com/auth/drive'
        ]

        # Conectar
        self.client = self._autenticar()
        self.spreadsheet = self._abrir_spreadsheet()
        self.hoja_resultados = self._obtener_hoja_resultados()

        print(f"✅ Conectado a spreadsheet de resultados: {self.hoja_nombre}")

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
            print("✅ Autenticado correctamente (spreadsheet resultados)")
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
            print(f"✅ Spreadsheet de resultados abierto: {spreadsheet.title}")
            return spreadsheet
        except Exception as e:
            print(f"❌ Error al abrir spreadsheet de resultados: {e}")
            raise

    def _obtener_hoja_resultados(self):
        """Obtiene la hoja de resultados"""
        try:
            hoja = self.spreadsheet.worksheet(self.hoja_nombre)
            print(f"✅ Hoja de resultados encontrada: {self.hoja_nombre}")
            return hoja
        except Exception as e:
            print(f"❌ Error: No se encontró la hoja '{self.hoja_nombre}'")
            print(f"   Hojas disponibles: {[ws.title for ws in self.spreadsheet.worksheets()]}")
            raise

    def guardar_resultado_llamada(self, datos: Dict) -> bool:
        """
        Guarda el resultado de una llamada en el spreadsheet

        Estructura de columnas según llenar_formularios.py:
        - Columna A: Marca temporal (fecha/hora)
        - Columna B: TIENDA (nombre del negocio)
        - Columna C: Respuesta Pregunta 1 (opciones múltiples)
        - Columna D: Respuesta Pregunta 2 (Sí/No)
        - Columna E: Respuesta Pregunta 3 (Crear Pedido Inicial/No)
        - Columna F: (vacía - no se usa)
        - Columna G: Respuesta Pregunta 4 (Sí/No - Pedido Muestra)
        - Columna H: Respuesta Pregunta 5 (Sí/No/Tal vez - Fecha)
        - Columna I: Respuesta Pregunta 6 (Sí/No/Tal vez - TDC)
        - Columna J: Respuesta Pregunta 7 o Prioridad (Pedido/Revisara/Correo/etc.)
        - Columna S: Resultado (APROBADO/NEGADO)
        - Columna T: Estado de llamada (Respondio/Buzon/Telefono Incorrecto)

        Args:
            datos: Diccionario con los datos de la llamada

        Returns:
            bool: True si se guardó correctamente
        """
        try:
            # Obtener última fila CON DATOS (no todas las filas vacías)
            todas_filas = self.hoja_resultados.get_all_values()

            # Contar solo filas que tienen datos en columna A (timestamp)
            filas_con_datos = 0
            for fila in todas_filas:
                if len(fila) > 0 and fila[0]:  # Si columna A tiene valor
                    filas_con_datos += 1
                else:
                    break  # Dejar de contar cuando encontramos fila vacía

            ultima_fila = filas_con_datos + 1

            print(f"\n📝 Guardando resultado en fila {ultima_fila}...")

            # Preparar datos
            fecha_hora = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
            tienda = datos.get('nombre_negocio', datos.get('TIENDA', ''))

            # Respuestas de las 7 preguntas
            respuesta_pregunta0 = datos.get('estado_llamada', 'Respondio')  # Respondio/Buzon/Telefono Incorrecto
            respuesta_pregunta1 = datos.get('pregunta_1', '')  # Opciones múltiples separadas por coma
            respuesta_pregunta2 = datos.get('pregunta_2', '')  # Sí/No
            respuesta_pregunta3 = datos.get('pregunta_3', '')  # Crear Pedido Inicial/No
            respuesta_pregunta4 = datos.get('pregunta_4', '')  # Sí/No
            respuesta_pregunta5 = datos.get('pregunta_5', '')  # Sí/No/Tal vez
            respuesta_pregunta6 = datos.get('pregunta_6', '')  # Sí/No/Tal vez
            respuesta_pregunta7 = datos.get('pregunta_7', '')  # Pedido/Revisara/Correo/etc.

            # Resultado y estado
            resultado = datos.get('resultado', 'APROBADO')
            tiempo_total = datos.get('duracion', '')

            # Lista de actualizaciones en batch
            actualizaciones = [
                {'range': f'A{ultima_fila}', 'values': [[fecha_hora]]},
                {'range': f'B{ultima_fila}', 'values': [[tienda]]},
            ]

            # Agregar respuestas solo si existen
            if respuesta_pregunta1:
                actualizaciones.append({'range': f'C{ultima_fila}', 'values': [[respuesta_pregunta1]]})
                print(f"  → Pregunta 1: {respuesta_pregunta1}")

            if respuesta_pregunta2:
                actualizaciones.append({'range': f'D{ultima_fila}', 'values': [[respuesta_pregunta2]]})
                print(f"  → Pregunta 2: {respuesta_pregunta2}")

            if respuesta_pregunta3:
                actualizaciones.append({'range': f'E{ultima_fila}', 'values': [[respuesta_pregunta3]]})
                print(f"  → Pregunta 3: {respuesta_pregunta3}")

            if respuesta_pregunta4:
                actualizaciones.append({'range': f'G{ultima_fila}', 'values': [[respuesta_pregunta4]]})
                print(f"  → Pregunta 4: {respuesta_pregunta4}")

            if respuesta_pregunta5:
                actualizaciones.append({'range': f'H{ultima_fila}', 'values': [[respuesta_pregunta5]]})
                print(f"  → Pregunta 5: {respuesta_pregunta5}")

            if respuesta_pregunta6:
                actualizaciones.append({'range': f'I{ultima_fila}', 'values': [[respuesta_pregunta6]]})
                print(f"  → Pregunta 6: {respuesta_pregunta6}")

            # Columna J: Prioridad según lógica de llenar_formularios.py
            # Prioridad: Colgo > Buzon/Telefono Incorrecto/No Contesta > No apto > Respuesta 7
            if respuesta_pregunta7 == 'Colgo':
                actualizaciones.append({'range': f'J{ultima_fila}', 'values': [["Colgo"]]})
                print(f"  → Columna J: Colgo")
            elif respuesta_pregunta0 == 'Buzon':
                actualizaciones.append({'range': f'J{ultima_fila}', 'values': [["BUZON"]]})
                print(f"  → Columna J: BUZON")
            elif respuesta_pregunta0 == 'Telefono Incorrecto':
                actualizaciones.append({'range': f'J{ultima_fila}', 'values': [["TELEFONO INCORRECTO"]]})
                print(f"  → Columna J: TELEFONO INCORRECTO")
            elif respuesta_pregunta0 == 'No Contesta':
                actualizaciones.append({'range': f'J{ultima_fila}', 'values': [["NO CONTESTA"]]})
                print(f"  → Columna J: NO CONTESTA")
            elif resultado == 'NEGADO':
                actualizaciones.append({'range': f'J{ultima_fila}', 'values': [["No apto"]]})
                print(f"  → Columna J: No apto")
            elif respuesta_pregunta7:
                actualizaciones.append({'range': f'J{ultima_fila}', 'values': [[respuesta_pregunta7]]})
                print(f"  → Columna J: {respuesta_pregunta7}")

            # Columna S: Resultado
            actualizaciones.append({'range': f'S{ultima_fila}', 'values': [[resultado]]})
            print(f"  → Resultado: {resultado}")

            # Columna T: Estado de llamada
            if respuesta_pregunta0:
                actualizaciones.append({'range': f'T{ultima_fila}', 'values': [[respuesta_pregunta0]]})
                print(f"  → Estado: {respuesta_pregunta0}")

            # Columna U: Duración de la llamada (tiempo total)
            if tiempo_total:
                actualizaciones.append({'range': f'U{ultima_fila}', 'values': [[tiempo_total]]})
                print(f"  → Duración: {tiempo_total}")

            # Columna V: Nivel de interés clasificado (Alto/Medio/Bajo)
            nivel_interes = datos.get('nivel_interes_clasificado', 'Medio')
            if nivel_interes:
                actualizaciones.append({'range': f'V{ultima_fila}', 'values': [[nivel_interes]]})
                print(f"  → Nivel de interés: {nivel_interes}")

            # Columna W: Estado de ánimo del cliente (Positivo/Neutral/Negativo)
            estado_animo = datos.get('estado_animo_cliente', 'Neutral')
            if estado_animo:
                actualizaciones.append({'range': f'W{ultima_fila}', 'values': [[estado_animo]]})
                print(f"  → Estado de ánimo: {estado_animo}")

            # Columna X: Opinión de Bruce (autoevaluación)
            opinion_bruce = datos.get('opinion_bruce', '')
            if opinion_bruce:
                actualizaciones.append({'range': f'X{ultima_fila}', 'values': [[opinion_bruce]]})
                print(f"  → Opinión Bruce: {opinion_bruce[:50]}...")

            # Columna Y: Calificación de Bruce (1-10)
            calificacion = datos.get('calificacion', '')
            if calificacion:
                actualizaciones.append({'range': f'Y{ultima_fila}', 'values': [[calificacion]]})
                print(f"  → Calificación Bruce: {calificacion}/10")

            # Columna Z: ID BRUCE (BRUCE01, BRUCE02, etc.)
            bruce_id = datos.get('bruce_id', '')
            if bruce_id:
                actualizaciones.append({'range': f'Z{ultima_fila}', 'values': [[bruce_id]]})
                print(f"  → ID BRUCE: {bruce_id}")

            # Ejecutar todas las actualizaciones en batch
            self.hoja_resultados.batch_update(actualizaciones)

            print(f"✅ Resultado guardado exitosamente en fila {ultima_fila}")
            return True

        except Exception as e:
            print(f"❌ Error al guardar resultado: {e}")
            import traceback
            traceback.print_exc()
            return False

    def obtener_estadisticas(self) -> Dict:
        """Obtiene estadísticas del spreadsheet de resultados"""
        try:
            datos = self.hoja_resultados.get_all_values()

            total_resultados = len(datos) - 1  # Menos header
            aprobados = 0
            negados = 0

            # Contar en columna S
            for fila in datos[1:]:
                if len(fila) > 18:  # Columna S es índice 18
                    resultado = fila[18]
                    if resultado == 'APROBADO':
                        aprobados += 1
                    elif resultado == 'NEGADO':
                        negados += 1

            return {
                'total_resultados': total_resultados,
                'aprobados': aprobados,
                'negados': negados,
                'tasa_aprobacion': round((aprobados / total_resultados * 100) if total_resultados > 0 else 0, 2)
            }

        except Exception as e:
            print(f"❌ Error al obtener estadísticas: {e}")
            return {}


# Testing
if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("📊 RESULTADOS SHEETS ADAPTER - TESTING")
    print("=" * 60 + "\n")

    try:
        # Inicializar adapter
        adapter = ResultadosSheetsAdapter()

        print("\n--- ESTADÍSTICAS DEL SPREADSHEET DE RESULTADOS ---")
        stats = adapter.obtener_estadisticas()
        print(f"Total de resultados: {stats.get('total_resultados', 0)}")
        print(f"Aprobados: {stats.get('aprobados', 0)}")
        print(f"Negados: {stats.get('negados', 0)}")
        print(f"Tasa de aprobación: {stats.get('tasa_aprobacion', 0)}%")

        print("\n--- TEST DE GUARDADO (COMENTADO) ---")
        print("Para probar guardado, descomentar el código siguiente:")
        print("""
        # Datos de prueba
        datos_prueba = {
            'nombre_negocio': 'Ferretería TEST',
            'estado_llamada': 'Respondio',
            'pregunta_1': 'Entregas Rápidas, Precio Preferente',
            'pregunta_2': 'Sí',
            'pregunta_3': 'Crear Pedido Inicial Sugerido',
            'pregunta_4': 'Sí',
            'pregunta_5': 'Sí',
            'pregunta_6': 'Sí',
            'pregunta_7': 'Pedido',
            'resultado': 'APROBADO',
            'duracion': '5:30'
        }

        # Guardar
        exito = adapter.guardar_resultado_llamada(datos_prueba)
        print(f"\\nResultado del guardado: {'✅ Éxito' if exito else '❌ Error'}")
        """)

    except Exception as e:
        print(f"\n❌ Error en testing: {e}")
        import traceback
        traceback.print_exc()

    print("\n" + "=" * 60)
