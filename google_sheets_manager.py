"""
Sistema de Gestión de Llamadas NIOVAL usando Google Sheets
Maneja: Contactos, Llamadas, Leads, KPIs
"""

import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import os
from dotenv import load_dotenv

load_dotenv()


class GoogleSheetsManager:
    """Gestor de Google Sheets para el sistema de llamadas NIOVAL"""

    def __init__(self, credentials_file: str = None, spreadsheet_name: str = "NIOVAL - Sistema de Llamadas"):
        """
        Inicializa el gestor de Google Sheets

        Args:
            credentials_file: Ruta al archivo JSON de credenciales de Google
            spreadsheet_name: Nombre del spreadsheet a usar/crear
        """
        self.credentials_file = credentials_file or os.getenv("GOOGLE_CREDENTIALS_FILE", "credentials.json")
        self.spreadsheet_name = spreadsheet_name

        # Definir alcances necesarios
        self.scopes = [
            'https://www.googleapis.com/auth/spreadsheets',
            'https://www.googleapis.com/auth/drive'
        ]

        # Autenticar e inicializar
        self.client = self._autenticar()
        self.spreadsheet = self._obtener_o_crear_spreadsheet()

        # Inicializar hojas
        self.inicializar_hojas()

    def _autenticar(self):
        """Autentica con Google usando las credenciales"""
        try:
            creds = Credentials.from_service_account_file(
                self.credentials_file,
                scopes=self.scopes
            )
            client = gspread.authorize(creds)
            print(" Autenticado correctamente con Google Sheets")
            return client
        except Exception as e:
            print(f" Error al autenticar: {e}")
            raise

    def _obtener_o_crear_spreadsheet(self):
        """Obtiene el spreadsheet o lo crea si no existe"""
        try:
            # Intentar abrir spreadsheet existente
            spreadsheet = self.client.open(self.spreadsheet_name)
            print(f" Spreadsheet encontrado: {self.spreadsheet_name}")
            return spreadsheet
        except gspread.SpreadsheetNotFound:
            # Crear nuevo spreadsheet
            spreadsheet = self.client.create(self.spreadsheet_name)
            print(f" Spreadsheet creado: {self.spreadsheet_name}")
            return spreadsheet

    def inicializar_hojas(self):
        """Crea las hojas necesarias con sus encabezados"""

        # Definición de hojas y sus encabezados
        hojas_config = {
            'Contactos': [
                'ID', 'Nombre Negocio', 'Teléfono', 'WhatsApp', 'WhatsApp Válido',
                'Email', 'Ciudad', 'Estado', 'Categoría', 'Prioridad',
                'Notas', 'Origen', 'Fecha Creación', 'Fecha Actualización',
                'Estado Contacto', 'Última Llamada'
            ],
            'Llamadas': [
                'ID Llamada', 'ID Contacto', 'Call SID', 'Fecha Llamada',
                'Duración (seg)', 'Estado', 'Resultado', 'Motivo No Contacto',
                'Fecha Reprogramación', 'Hora Preferida', 'Nombre Contacto',
                'WhatsApp Capturado', 'Email Capturado', 'Productos Interés',
                'Nivel Interés', 'Objeciones', 'Siguiente Acción', 'Notas Llamada'
            ],
            'Leads': [
                'ID Lead', 'ID Contacto', 'ID Llamada', 'Nombre Contacto',
                'Nombre Negocio', 'Teléfono', 'WhatsApp', 'Email', 'Ciudad',
                'Categoría Interés', 'Productos Interés', 'Nivel Interés',
                'Temperatura', 'Notas', 'Siguiente Paso', 'Fecha Seguimiento',
                'Estado Lead', 'Origen', 'Fecha Creación', 'Fecha Conversión',
                'Monto Estimado'
            ],
            'KPIs Diarios': [
                'Fecha', 'Llamadas Realizadas', 'Llamadas Contestadas',
                'Llamadas No Contestadas', 'Llamadas Ocupado', 'Llamadas Reprogramadas',
                'Duración Total (seg)', 'Duración Promedio (seg)',
                'WhatsApps Capturados', 'Emails Capturados',
                'Leads Generados', 'Leads Calientes', 'Leads Tibios', 'Leads Fríos',
                'Tasa Contacto (%)', 'Tasa Conversión (%)',
                'Hora Más Efectiva', 'Objeciones Principales'
            ],
            'Reprogramadas': [
                'ID Llamada', 'Nombre Negocio', 'Teléfono', 'Fecha Reprogramación',
                'Hora Preferida', 'Motivo', 'Intentos', 'Estado', 'Notas'
            ],
            'Dashboard': [
                'Métrica', 'Valor', 'Fecha Actualización'
            ]
        }

        for nombre_hoja, encabezados in hojas_config.items():
            try:
                # Intentar obtener la hoja
                hoja = self.spreadsheet.worksheet(nombre_hoja)
                print(f" Hoja '{nombre_hoja}' ya existe")
            except gspread.WorksheetNotFound:
                # Crear la hoja
                hoja = self.spreadsheet.add_worksheet(
                    title=nombre_hoja,
                    rows=1000,
                    cols=len(encabezados)
                )
                # Agregar encabezados
                hoja.append_row(encabezados)
                # Formatear encabezados (negrita y fondo)
                hoja.format('A1:Z1', {
                    'textFormat': {'bold': True},
                    'backgroundColor': {'red': 0.2, 'green': 0.6, 'blue': 0.9}
                })
                print(f" Hoja '{nombre_hoja}' creada con {len(encabezados)} columnas")

    # ==================== GESTIÓN DE CONTACTOS ====================

    def agregar_contacto(self, nombre_negocio: str, telefono: str, **kwargs) -> int:
        """
        Agrega un nuevo contacto a la hoja de Contactos

        Args:
            nombre_negocio: Nombre del negocio
            telefono: Teléfono en formato +52XXXXXXXXXX
            **kwargs: Campos adicionales

        Returns:
            ID del contacto (número de fila)
        """
        hoja = self.spreadsheet.worksheet('Contactos')

        # Verificar si ya existe
        try:
            cell = hoja.find(telefono, in_column=3)  # Columna de teléfono
            if cell:
                print(f" El teléfono {telefono} ya existe en fila {cell.row}")
                return cell.row
        except Exception:
            pass  # Teléfono no encontrado, continuar para agregar

        # Preparar datos
        fecha_actual = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        nueva_fila = [
            len(hoja.get_all_values()),  # ID (número de fila)
            nombre_negocio,
            telefono,
            kwargs.get('whatsapp', ''),
            kwargs.get('whatsapp_valido', 'No'),
            kwargs.get('email', ''),
            kwargs.get('ciudad', ''),
            kwargs.get('estado', ''),
            kwargs.get('categoria', 'Ferretería'),
            kwargs.get('prioridad', 3),
            kwargs.get('notas', ''),
            kwargs.get('origen', 'Manual'),
            fecha_actual,  # Fecha creación
            fecha_actual,  # Fecha actualización
            'Pendiente',  # Estado contacto
            ''  # Última llamada
        ]

        hoja.append_row(nueva_fila)
        fila_id = len(hoja.get_all_values())

        print(f" Contacto agregado: {nombre_negocio} - Fila {fila_id}")
        return fila_id

    def agregar_contactos_masivo(self, contactos: List[Dict]) -> Dict:
        """
        Agrega múltiples contactos desde una lista

        Args:
            contactos: Lista de diccionarios con datos

        Returns:
            Dict con estadísticas de la carga
        """
        resultados = {
            'agregados': 0,
            'duplicados': 0,
            'errores': 0,
            'filas': []
        }

        for contacto in contactos:
            try:
                nombre = contacto.get('nombre_negocio')
                telefono = contacto.get('telefono')

                if not nombre or not telefono:
                    resultados['errores'] += 1
                    continue

                fila = self.agregar_contacto(nombre, telefono, **contacto)

                if fila:
                    resultados['agregados'] += 1
                    resultados['filas'].append(fila)

            except Exception as e:
                print(f" Error al agregar contacto: {e}")
                resultados['errores'] += 1

        return resultados

    def obtener_contactos_pendientes(self, limite: int = 100) -> List[Dict]:
        """
        Obtiene contactos que no han sido llamados

        Args:
            limite: Número máximo de contactos

        Returns:
            Lista de contactos pendientes
        """
        hoja = self.spreadsheet.worksheet('Contactos')
        registros = hoja.get_all_records()

        # Filtrar pendientes (sin última llamada o estado pendiente)
        pendientes = [
            r for r in registros
            if r.get('Estado Contacto') == 'Pendiente' or not r.get('Última Llamada')
        ]

        # Ordenar por prioridad
        pendientes.sort(key=lambda x: x.get('Prioridad', 0), reverse=True)

        return pendientes[:limite]

    def actualizar_contacto(self, fila: int, **campos):
        """
        Actualiza campos de un contacto

        Args:
            fila: Número de fila del contacto
            **campos: Campos a actualizar
        """
        hoja = self.spreadsheet.worksheet('Contactos')

        # Mapeo de campos a columnas (basado en encabezados)
        columnas_map = {
            'whatsapp': 4,
            'whatsapp_valido': 5,
            'email': 6,
            'ultima_llamada': 16,
            'estado_contacto': 15
        }

        for campo, valor in campos.items():
            if campo in columnas_map:
                col = columnas_map[campo]
                hoja.update_cell(fila, col, valor)

        # Actualizar fecha de actualización
        hoja.update_cell(fila, 14, datetime.now().strftime('%Y-%m-%d %H:%M:%S'))

    def actualizar_numero_con_whatsapp(self, fila: int, whatsapp: str):
        """
        Actualiza el número de teléfono con el WhatsApp capturado
        Formato: 662 108 5297 (10 dígitos con espacios cada 3)

        Args:
            fila: Número de fila del contacto
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

            hoja = self.spreadsheet.worksheet('Contactos')
            # Actualizar en columna 4 (WhatsApp)
            hoja.update_cell(fila, 4, numero_formateado)
            # Actualizar fecha de actualización
            hoja.update_cell(fila, 14, datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
            print(f" WhatsApp actualizado en fila {fila}: {numero_formateado}")
        except Exception as e:
            print(f" Error al actualizar WhatsApp: {e}")

    def registrar_email_capturado(self, fila: int, email: str):
        """
        Registra el email capturado durante la llamada

        Args:
            fila: Número de fila del contacto
            email: Email capturado
        """
        try:
            hoja = self.spreadsheet.worksheet('Contactos')
            # Actualizar en columna 6 (Email)
            hoja.update_cell(fila, 6, email)
            # Actualizar fecha de actualización
            hoja.update_cell(fila, 14, datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
            print(f" Email actualizado en fila {fila}: {email}")
        except Exception as e:
            print(f" Error al actualizar email: {e}")

    # ==================== GESTIÓN DE LLAMADAS ====================

    def registrar_llamada(self, contacto_fila: int, contacto_nombre: str, telefono: str,
                         estado: str, **kwargs) -> int:
        """
        Registra una llamada realizada

        Args:
            contacto_fila: Fila del contacto en hoja Contactos
            contacto_nombre: Nombre del negocio
            telefono: Teléfono llamado
            estado: Estado (contestada, no_contesta, ocupado, reprogramada)
            **kwargs: Datos adicionales

        Returns:
            Número de fila de la llamada registrada
        """
        hoja = self.spreadsheet.worksheet('Llamadas')
        fecha_actual = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        nueva_llamada = [
            len(hoja.get_all_values()),  # ID Llamada
            contacto_fila,  # ID Contacto
            kwargs.get('call_sid', ''),
            fecha_actual,  # Fecha llamada
            kwargs.get('duracion_segundos', 0),
            estado,
            kwargs.get('resultado', ''),
            kwargs.get('motivo_no_contacto', ''),
            kwargs.get('fecha_reprogramacion', ''),
            kwargs.get('hora_preferida', ''),
            kwargs.get('nombre_contacto', ''),
            kwargs.get('whatsapp_capturado', ''),
            kwargs.get('email_capturado', ''),
            kwargs.get('productos_interes', ''),
            kwargs.get('nivel_interes', ''),
            kwargs.get('objeciones', ''),
            kwargs.get('siguiente_accion', ''),
            kwargs.get('notas', '')
        ]

        hoja.append_row(nueva_llamada)
        llamada_fila = len(hoja.get_all_values())

        # Actualizar contacto
        self.actualizar_contacto(
            contacto_fila,
            ultima_llamada=fecha_actual,
            estado_contacto=estado
        )

        # Si es reprogramada, agregar a hoja de reprogramadas
        if estado == 'reprogramada' and kwargs.get('fecha_reprogramacion'):
            self._agregar_reprogramada(
                llamada_fila,
                contacto_nombre,
                telefono,
                kwargs.get('fecha_reprogramacion'),
                kwargs.get('hora_preferida', ''),
                kwargs.get('motivo_no_contacto', '')
            )

        # Actualizar KPIs
        self.actualizar_kpis_diarios()

        print(f" Llamada registrada: {contacto_nombre} - Estado: {estado}")
        return llamada_fila

    def _agregar_reprogramada(self, llamada_id: int, nombre: str, telefono: str,
                             fecha_reprog: str, hora: str, motivo: str):
        """Agrega una llamada a la hoja de Reprogramadas"""
        hoja = self.spreadsheet.worksheet('Reprogramadas')

        nueva_reprogramada = [
            llamada_id,
            nombre,
            telefono,
            fecha_reprog,
            hora,
            motivo,
            1,  # Intentos
            'Pendiente',
            ''  # Notas
        ]

        hoja.append_row(nueva_reprogramada)

    def obtener_llamadas_reprogramadas_hoy(self) -> List[Dict]:
        """Obtiene llamadas reprogramadas para hoy"""
        hoja = self.spreadsheet.worksheet('Reprogramadas')
        registros = hoja.get_all_records()

        hoy = datetime.now().strftime('%Y-%m-%d')

        reprogramadas_hoy = [
            r for r in registros
            if r.get('Fecha Reprogramación', '').startswith(hoy)
            and r.get('Estado') == 'Pendiente'
        ]

        return reprogramadas_hoy

    # ==================== GESTIÓN DE LEADS ====================

    def crear_lead(self, contacto_fila: int, llamada_fila: int, **kwargs) -> int:
        """
        Crea un nuevo lead

        Args:
            contacto_fila: Fila del contacto
            llamada_fila: Fila de la llamada
            **kwargs: Datos del lead

        Returns:
            Fila del lead creado
        """
        hoja = self.spreadsheet.worksheet('Leads')
        fecha_actual = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        nuevo_lead = [
            len(hoja.get_all_values()),  # ID Lead
            contacto_fila,
            llamada_fila,
            kwargs.get('nombre_contacto', ''),
            kwargs.get('nombre_negocio', ''),
            kwargs.get('telefono', ''),
            kwargs.get('whatsapp', ''),
            kwargs.get('email', ''),
            kwargs.get('ciudad', ''),
            kwargs.get('categoria_interes', ''),
            kwargs.get('productos_interes', ''),
            kwargs.get('nivel_interes', 'Bajo'),
            kwargs.get('temperatura', 'Frío'),
            kwargs.get('notas', ''),
            kwargs.get('siguiente_paso', ''),
            kwargs.get('fecha_seguimiento', ''),
            'Nuevo',  # Estado lead
            'Llamada saliente',  # Origen
            fecha_actual,  # Fecha creación
            '',  # Fecha conversión
            kwargs.get('monto_estimado', '')
        ]

        hoja.append_row(nuevo_lead)
        lead_fila = len(hoja.get_all_values())

        # Actualizar KPIs
        self.actualizar_kpis_diarios()

        print(f" Lead creado: {kwargs.get('nombre_negocio', 'N/A')} - Fila {lead_fila}")
        return lead_fila

    def obtener_leads_pendientes(self) -> List[Dict]:
        """Obtiene leads que necesitan seguimiento"""
        hoja = self.spreadsheet.worksheet('Leads')
        registros = hoja.get_all_records()

        # Filtrar leads activos que necesitan seguimiento
        pendientes = [
            r for r in registros
            if r.get('Estado Lead') in ['Nuevo', 'Contactado', 'Seguimiento']
        ]

        return pendientes

    # ==================== KPIs Y MÉTRICAS ====================

    def actualizar_kpis_diarios(self):
        """Calcula y actualiza KPIs del día actual"""
        hoja_llamadas = self.spreadsheet.worksheet('Llamadas')
        hoja_leads = self.spreadsheet.worksheet('Leads')
        hoja_kpis = self.spreadsheet.worksheet('KPIs Diarios')

        fecha_hoy = datetime.now().strftime('%Y-%m-%d')

        # Obtener todas las llamadas del día
        llamadas = hoja_llamadas.get_all_records()
        llamadas_hoy = [l for l in llamadas if l.get('Fecha Llamada', '').startswith(fecha_hoy)]

        # Calcular métricas de llamadas
        total_llamadas = len(llamadas_hoy)
        contestadas = sum(1 for l in llamadas_hoy if l.get('Estado') == 'contestada')
        no_contestadas = sum(1 for l in llamadas_hoy if l.get('Estado') == 'no_contesta')
        ocupado = sum(1 for l in llamadas_hoy if l.get('Estado') == 'ocupado')
        reprogramadas = sum(1 for l in llamadas_hoy if l.get('Estado') == 'reprogramada')

        duracion_total = sum(l.get('Duración (seg)', 0) for l in llamadas_hoy)
        duracion_promedio = (duracion_total / contestadas) if contestadas > 0 else 0

        whatsapps = sum(1 for l in llamadas_hoy if l.get('WhatsApp Capturado'))
        emails = sum(1 for l in llamadas_hoy if l.get('Email Capturado'))

        # Obtener leads del día
        leads = hoja_leads.get_all_records()
        leads_hoy = [l for l in leads if l.get('Fecha Creación', '').startswith(fecha_hoy)]

        total_leads = len(leads_hoy)
        leads_calientes = sum(1 for l in leads_hoy if l.get('Temperatura') == 'Caliente')
        leads_tibios = sum(1 for l in leads_hoy if l.get('Temperatura') == 'Tibio')
        leads_frios = sum(1 for l in leads_hoy if l.get('Temperatura') == 'Frío')

        # Calcular tasas
        tasa_contacto = (contestadas / total_llamadas * 100) if total_llamadas > 0 else 0
        tasa_conversion = (total_leads / contestadas * 100) if contestadas > 0 else 0

        # Buscar si ya existe registro de hoy
        kpis_existentes = hoja_kpis.get_all_records()
        fila_hoy = None

        for idx, kpi in enumerate(kpis_existentes, start=2):  # Start=2 porque fila 1 son encabezados
            if kpi.get('Fecha') == fecha_hoy:
                fila_hoy = idx
                break

        nueva_fila_kpi = [
            fecha_hoy,
            total_llamadas,
            contestadas,
            no_contestadas,
            ocupado,
            reprogramadas,
            duracion_total,
            int(duracion_promedio),
            whatsapps,
            emails,
            total_leads,
            leads_calientes,
            leads_tibios,
            leads_frios,
            round(tasa_contacto, 2),
            round(tasa_conversion, 2),
            '',  # Hora más efectiva (calcular después)
            ''   # Objeciones principales (calcular después)
        ]

        if fila_hoy:
            # Actualizar fila existente
            for col_idx, valor in enumerate(nueva_fila_kpi, start=1):
                hoja_kpis.update_cell(fila_hoy, col_idx, valor)
        else:
            # Agregar nueva fila
            hoja_kpis.append_row(nueva_fila_kpi)

        # Actualizar dashboard
        self._actualizar_dashboard()

        print(f" KPIs actualizados para {fecha_hoy}")

    def _actualizar_dashboard(self):
        """Actualiza el dashboard con métricas generales"""
        hoja_dashboard = self.spreadsheet.worksheet('Dashboard')

        # Limpiar dashboard
        hoja_dashboard.clear()
        hoja_dashboard.append_row(['Métrica', 'Valor', 'Fecha Actualización'])

        # Calcular métricas generales
        hoja_contactos = self.spreadsheet.worksheet('Contactos')
        hoja_llamadas = self.spreadsheet.worksheet('Llamadas')
        hoja_leads = self.spreadsheet.worksheet('Leads')

        total_contactos = len(hoja_contactos.get_all_records())
        total_llamadas = len(hoja_llamadas.get_all_records())
        total_leads = len(hoja_leads.get_all_records())

        contactos_pendientes = len([c for c in hoja_contactos.get_all_records()
                                    if c.get('Estado Contacto') == 'Pendiente'])

        fecha_actual = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        metricas_dashboard = [
            ['Total Contactos', total_contactos, fecha_actual],
            ['Contactos Pendientes', contactos_pendientes, fecha_actual],
            ['Total Llamadas Realizadas', total_llamadas, fecha_actual],
            ['Total Leads Generados', total_leads, fecha_actual],
            ['Tasa Conversión Global (%)',
             round((total_leads / total_llamadas * 100) if total_llamadas > 0 else 0, 2),
             fecha_actual]
        ]

        for metrica in metricas_dashboard:
            hoja_dashboard.append_row(metrica)

    def obtener_kpis_ultimos_dias(self, dias: int = 7) -> List[Dict]:
        """Obtiene KPIs de los últimos N días"""
        hoja = self.spreadsheet.worksheet('KPIs Diarios')
        registros = hoja.get_all_records()

        # Filtrar últimos N días
        fecha_limite = (datetime.now() - timedelta(days=dias)).strftime('%Y-%m-%d')

        kpis_recientes = [
            r for r in registros
            if r.get('Fecha', '') >= fecha_limite
        ]

        return sorted(kpis_recientes, key=lambda x: x.get('Fecha', ''), reverse=True)

    def obtener_resumen_general(self) -> Dict:
        """Obtiene resumen general de todas las métricas"""
        hoja_dashboard = self.spreadsheet.worksheet('Dashboard')
        registros = hoja_dashboard.get_all_records()

        resumen = {}
        for registro in registros:
            metrica = registro.get('Métrica')
            valor = registro.get('Valor')
            if metrica:
                resumen[metrica] = valor

        return resumen


# Ejemplo de uso
if __name__ == "__main__":
    print("\n" + "=" * 60)
    print(" GOOGLE SHEETS MANAGER - NIOVAL")
    print("=" * 60 + "\n")

    # Inicializar manager
    try:
        manager = GoogleSheetsManager(
            credentials_file="C:\\Users\\PC 1\\credentials.json",
            spreadsheet_name="NIOVAL - Sistema Llamadas Test"
        )

        print("\n Sistema inicializado correctamente")
        print(f" Spreadsheet: {manager.spreadsheet.url}")

        # Agregar contacto de prueba
        print("\n--- Agregando contacto de prueba ---")
        manager.agregar_contacto(
            nombre_negocio="Ferretería Test",
            telefono="+525512345678",
            ciudad="CDMX",
            estado="Ciudad de México",
            prioridad=5
        )

        # Obtener resumen
        print("\n--- Resumen General ---")
        resumen = manager.obtener_resumen_general()
        for metrica, valor in resumen.items():
            print(f"{metrica}: {valor}")

    except Exception as e:
        print(f"\n Error: {e}")
        print("\nAsegúrate de tener el archivo credentials.json configurado")
