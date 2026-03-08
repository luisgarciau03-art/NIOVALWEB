"""
Sistema Automatizado de Llamadas Masivas - NIOVAL
Gestiona llamadas automáticas, reprogramación y seguimiento
"""

import time
import schedule
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import json
from agente_ventas import AgenteVentas
from google_sheets_manager import GoogleSheetsManager
from whatsapp_validator import WhatsAppValidator, WhatsAppValidatorCache
from twilio.rest import Client
import os
from dotenv import load_dotenv

load_dotenv()


class SistemaAutomatizado:
    """
    Sistema principal para gestionar llamadas automáticas a contactos
    """

    def __init__(self):
        """Inicializa el sistema completo"""
        print("\n" + "=" * 60)
        print(" INICIANDO SISTEMA AUTOMATIZADO - NIOVAL")
        print("=" * 60 + "\n")

        # Inicializar componentes
        self.sheets_manager = self._inicializar_sheets()
        self.whatsapp_validator = self._inicializar_whatsapp_validator()
        self.twilio_client = self._inicializar_twilio()

        # Configuración
        self.llamadas_por_dia = int(os.getenv("LLAMADAS_POR_DIA", "100"))
        self.delay_entre_llamadas = int(os.getenv("DELAY_LLAMADAS_SEG", "60"))
        self.horario_inicio = os.getenv("HORARIO_INICIO", "09:00")
        self.horario_fin = os.getenv("HORARIO_FIN", "17:00")

        print(f" Sistema inicializado")
        print(f" Configuración:")
        print(f"   - Llamadas por día: {self.llamadas_por_dia}")
        print(f"   - Delay entre llamadas: {self.delay_entre_llamadas}s")
        print(f"   - Horario: {self.horario_inicio} - {self.horario_fin}")

    def _inicializar_sheets(self) -> GoogleSheetsManager:
        """Inicializa el gestor de Google Sheets"""
        try:
            credentials_file = os.getenv("GOOGLE_CREDENTIALS_FILE", "credentials.json")
            spreadsheet_name = os.getenv("SPREADSHEET_NAME", "NIOVAL - Sistema de Llamadas")

            manager = GoogleSheetsManager(
                credentials_file=credentials_file,
                spreadsheet_name=spreadsheet_name
            )

            print(f" Google Sheets conectado")
            print(f"   URL: {manager.spreadsheet.url}")
            return manager

        except Exception as e:
            print(f" Error al inicializar Google Sheets: {e}")
            print("   El sistema funcionará sin Google Sheets (solo respaldo Excel)")
            return None

    def _inicializar_whatsapp_validator(self) -> WhatsAppValidatorCache:
        """Inicializa el validador de WhatsApp con cache"""
        try:
            method = os.getenv("WHATSAPP_VALIDATOR_METHOD", "formato")
            validator = WhatsAppValidator(method=method)
            validator_cache = WhatsAppValidatorCache(validator)

            print(f" Validador de WhatsApp: {method}")
            return validator_cache

        except Exception as e:
            print(f" Error al inicializar validador: {e}")
            return None

    def _inicializar_twilio(self) -> Optional[Client]:
        """Inicializa el cliente de Twilio"""
        try:
            account_sid = os.getenv("TWILIO_ACCOUNT_SID")
            auth_token = os.getenv("TWILIO_AUTH_TOKEN")

            if not account_sid or not auth_token:
                print(" Credenciales de Twilio no configuradas")
                return None

            client = Client(account_sid, auth_token)
            print(" Twilio conectado")
            return client

        except Exception as e:
            print(f" Error al inicializar Twilio: {e}")
            return None

    # ==================== GESTIÓN DE LLAMADAS ====================

    def ejecutar_llamadas_diarias(self):
        """Ejecuta el proceso de llamadas del día"""
        print("\n" + "=" * 60)
        print(f" INICIANDO LLAMADAS DEL DÍA - {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        print("=" * 60 + "\n")

        # Obtener contactos pendientes
        contactos = self._obtener_contactos_para_llamar()

        if not contactos:
            print("ℹ No hay contactos pendientes para llamar")
            return

        print(f" Contactos a llamar: {len(contactos)}")

        # Verificar si estamos en horario laboral
        if not self._en_horario_laboral():
            print(f" Fuera de horario laboral ({self.horario_inicio}-{self.horario_fin})")
            return

        # Ejecutar llamadas con delay
        resultados = {
            'exitosas': 0,
            'fallidas': 0,
            'reprogramadas': 0
        }

        for idx, contacto in enumerate(contactos, 1):
            print(f"\n--- Llamada {idx}/{len(contactos)} ---")

            try:
                resultado = self.realizar_llamada(contacto)

                if resultado['exito']:
                    resultados['exitosas'] += 1
                elif resultado.get('reprogramada'):
                    resultados['reprogramadas'] += 1
                else:
                    resultados['fallidas'] += 1

                # Delay entre llamadas
                if idx < len(contactos):
                    print(f" Esperando {self.delay_entre_llamadas}s antes de la siguiente llamada...")
                    time.sleep(self.delay_entre_llamadas)

            except Exception as e:
                print(f" Error en llamada: {e}")
                resultados['fallidas'] += 1

        # Mostrar resumen
        print("\n" + "=" * 60)
        print(" RESUMEN DEL DÍA")
        print("=" * 60)
        print(f" Exitosas: {resultados['exitosas']}")
        print(f" Reprogramadas: {resultados['reprogramadas']}")
        print(f" Fallidas: {resultados['fallidas']}")
        print("=" * 60 + "\n")

        # Actualizar KPIs
        if self.sheets_manager:
            self.sheets_manager.actualizar_kpis_diarios()

    def _obtener_contactos_para_llamar(self) -> List[Dict]:
        """Obtiene la lista de contactos pendientes y reprogramados"""
        contactos = []

        if self.sheets_manager:
            # Obtener contactos pendientes
            pendientes = self.sheets_manager.obtener_contactos_pendientes(
                limite=self.llamadas_por_dia
            )
            contactos.extend(pendientes)

            # Agregar llamadas reprogramadas para hoy
            reprogramadas = self.sheets_manager.obtener_llamadas_reprogramadas_hoy()

            for rep in reprogramadas:
                # Buscar el contacto en la hoja
                contacto = {
                    'Nombre Negocio': rep.get('Nombre Negocio'),
                    'Teléfono': rep.get('Teléfono'),
                    'Reprogramada': True,
                    'Hora Preferida': rep.get('Hora Preferida')
                }
                contactos.append(contacto)

        return contactos[:self.llamadas_por_dia]

    def realizar_llamada(self, contacto: Dict) -> Dict:
        """
        Realiza una llamada a un contacto

        Args:
            contacto: Datos del contacto desde Google Sheets

        Returns:
            Dict con resultado de la llamada
        """
        nombre = contacto.get('Nombre Negocio', 'Cliente')
        telefono = contacto.get('Teléfono')

        print(f" Llamando a {nombre} ({telefono})...")

        # Crear agente para este contacto
        agente = AgenteVentas(
            contacto_info=contacto,
            sheets_manager=self.sheets_manager,
            whatsapp_validator=self.whatsapp_validator
        )

        try:
            if self.twilio_client:
                # Realizar llamada real con Twilio
                resultado = self._llamada_twilio(telefono, agente)
            else:
                # Simulación de llamada (para testing sin Twilio)
                resultado = self._llamada_simulada(agente)

            return resultado

        except Exception as e:
            print(f" Error al llamar: {e}")
            return {
                'exito': False,
                'error': str(e)
            }

    def _llamada_twilio(self, telefono: str, agente: AgenteVentas) -> Dict:
        """Realiza llamada real con Twilio"""
        try:
            twilio_number = os.getenv("TWILIO_PHONE_NUMBER")
            webhook_url = os.getenv("WEBHOOK_URL", "http://localhost:5000/webhook-voz")

            # Iniciar llamada
            call = self.twilio_client.calls.create(
                to=telefono,
                from_=twilio_number,
                url=webhook_url,
                method="POST",
                status_callback=webhook_url + "/status",
                status_callback_method="POST"
            )

            agente.call_sid = call.sid

            print(f" Llamada iniciada - SID: {call.sid}")

            # Esperar resultado (en producción esto sería asíncrono)
            time.sleep(5)  # Simular espera de conexión

            # Obtener estado
            call_status = self.twilio_client.calls(call.sid).fetch()

            resultado = {
                'exito': call_status.status in ['in-progress', 'ringing', 'completed'],
                'estado': call_status.status,
                'call_sid': call.sid
            }

            # Manejar diferentes estados
            if call_status.status == 'no-answer':
                agente.motivo_no_contacto = "No contesta"
                agente.guardar_llamada_y_lead()
                resultado['reprogramada'] = True

            elif call_status.status == 'busy':
                agente.motivo_no_contacto = "Ocupado"
                agente.guardar_llamada_y_lead()
                resultado['reprogramada'] = True

            return resultado

        except Exception as e:
            print(f" Error en llamada Twilio: {e}")
            return {
                'exito': False,
                'error': str(e)
            }

    def _llamada_simulada(self, agente: AgenteVentas) -> Dict:
        """Simulación de llamada para testing"""
        print(" MODO SIMULACIÓN (sin Twilio)")

        # Simular conversación básica
        mensaje_inicial = agente.iniciar_conversacion()
        print(f"Bruce: {mensaje_inicial}")

        # Simular respuesta del cliente
        import random
        respuestas_simuladas = [
            "Sí, soy el encargado",
            "No me interesa",
            "Mándame información por WhatsApp al 3312345678",
            "Llámame después a las 3pm",
            "No contesta"  # Simular no respuesta
        ]

        respuesta_cliente = random.choice(respuestas_simuladas)
        print(f"Cliente (simulado): {respuesta_cliente}")

        # Procesar respuesta
        if "no contesta" in respuesta_cliente.lower():
            agente.motivo_no_contacto = "No contesta"
            agente.guardar_llamada_y_lead()
            return {
                'exito': False,
                'reprogramada': True,
                'motivo': 'No contesta'
            }

        else:
            respuesta_agente = agente.procesar_respuesta(respuesta_cliente)
            print(f"Bruce: {respuesta_agente}")

            # Guardar
            agente.guardar_llamada_y_lead()

            return {
                'exito': True,
                'simulada': True
            }

    def _en_horario_laboral(self) -> bool:
        """Verifica si está en horario laboral"""
        ahora = datetime.now()
        hora_actual = ahora.strftime('%H:%M')

        return self.horario_inicio <= hora_actual <= self.horario_fin

    # ==================== REPROGRAMACIÓN ====================

    def reprogramar_llamada(self, contacto: Dict, fecha: str, hora: str, motivo: str):
        """
        Reprograma una llamada

        Args:
            contacto: Datos del contacto
            fecha: Fecha de reprogramación (YYYY-MM-DD)
            hora: Hora preferida (HH:MM)
            motivo: Motivo de la reprogramación
        """
        print(f" Reprogramando llamada para {contacto.get('Nombre Negocio')}")
        print(f"   Fecha: {fecha} {hora}")
        print(f"   Motivo: {motivo}")

        if self.sheets_manager:
            # La reprogramación se maneja automáticamente en registrar_llamada
            # cuando se pasa fecha_reprogramacion
            pass

    # ==================== PROGRAMACIÓN DE TAREAS ====================

    def programar_llamadas_automaticas(self):
        """Programa las llamadas automáticas diarias"""
        print("\n" + "=" * 60)
        print(" CONFIGURANDO LLAMADAS AUTOMÁTICAS")
        print("=" * 60 + "\n")

        # Programar llamadas diarias a la hora configurada
        schedule.every().day.at(self.horario_inicio).do(self.ejecutar_llamadas_diarias)

        # Programar actualización de KPIs cada hora
        schedule.every().hour.do(self._actualizar_kpis)

        # Programar revisión de reprogramadas cada 4 horas
        schedule.every(4).hours.do(self._revisar_reprogramadas)

        print(f" Llamadas programadas para las {self.horario_inicio}")
        print(f" KPIs se actualizarán cada hora")
        print(f" Revisión de reprogramadas cada 4 horas")

    def _actualizar_kpis(self):
        """Actualiza KPIs periódicamente"""
        if self.sheets_manager:
            self.sheets_manager.actualizar_kpis_diarios()
            print(" KPIs actualizados")

    def _revisar_reprogramadas(self):
        """Revisa y procesa llamadas reprogramadas"""
        if self.sheets_manager:
            reprogramadas = self.sheets_manager.obtener_llamadas_reprogramadas_hoy()
            print(f" Reprogramadas para hoy: {len(reprogramadas)}")

    def iniciar_modo_continuo(self):
        """Inicia el sistema en modo continuo (24/7)"""
        print("\n" + "=" * 60)
        print(" MODO CONTINUO ACTIVADO")
        print("=" * 60 + "\n")
        print("El sistema correrá indefinidamente...")
        print("Presiona Ctrl+C para detener\n")

        try:
            while True:
                schedule.run_pending()
                time.sleep(60)  # Revisar cada minuto
        except KeyboardInterrupt:
            print("\n\n Sistema detenido por el usuario")

    # ==================== REPORTES ====================

    def generar_reporte_diario(self):
        """Genera reporte del día"""
        if not self.sheets_manager:
            print(" No hay conexión a Google Sheets para generar reporte")
            return

        print("\n" + "=" * 60)
        print(f" REPORTE DEL DÍA - {datetime.now().strftime('%Y-%m-%d')}")
        print("=" * 60 + "\n")

        kpis = self.sheets_manager.obtener_kpis_ultimos_dias(dias=1)

        if kpis:
            kpi_hoy = kpis[0]
            print(f" Llamadas realizadas: {kpi_hoy.get('Llamadas Realizadas', 0)}")
            print(f" Contestadas: {kpi_hoy.get('Llamadas Contestadas', 0)}")
            print(f" No contestadas: {kpi_hoy.get('Llamadas No Contestadas', 0)}")
            print(f" WhatsApps capturados: {kpi_hoy.get('WhatsApps Capturados', 0)}")
            print(f" Emails capturados: {kpi_hoy.get('Emails Capturados', 0)}")
            print(f" Leads generados: {kpi_hoy.get('Leads Generados', 0)}")
            print(f" Tasa de contacto: {kpi_hoy.get('Tasa Contacto (%)', 0)}%")
            print(f" Tasa de conversión: {kpi_hoy.get('Tasa Conversión (%)', 0)}%")
        else:
            print("ℹ No hay datos para hoy aún")

        print("\n" + "=" * 60)


# Función principal
def main():
    """Función principal del sistema"""
    print("""
    
      SISTEMA AUTOMATIZADO DE LLAMADAS - NIOVAL           
      Bruce W - Agente de Ventas Inteligente              
    
    """)

    # Inicializar sistema
    sistema = SistemaAutomatizado()

    # Menú de opciones
    print("\n OPCIONES DISPONIBLES:")
    print("1. Ejecutar llamadas ahora (manual)")
    print("2. Programar llamadas automáticas (modo continuo)")
    print("3. Generar reporte del día")
    print("4. Ver resumen general")
    print("5. Ejecutar 1 llamada de prueba")
    print("0. Salir")

    opcion = input("\nSelecciona una opción: ").strip()

    if opcion == "1":
        sistema.ejecutar_llamadas_diarias()

    elif opcion == "2":
        sistema.programar_llamadas_automaticas()
        sistema.iniciar_modo_continuo()

    elif opcion == "3":
        sistema.generar_reporte_diario()

    elif opcion == "4":
        if sistema.sheets_manager:
            resumen = sistema.sheets_manager.obtener_resumen_general()
            print("\n RESUMEN GENERAL:")
            print(json.dumps(resumen, indent=2, ensure_ascii=False))

    elif opcion == "5":
        print("\n Ejecutando llamada de prueba...")
        contactos = sistema._obtener_contactos_para_llamar()
        if contactos:
            sistema.realizar_llamada(contactos[0])
        else:
            print(" No hay contactos disponibles")

    else:
        print(" Hasta pronto!")


if __name__ == "__main__":
    main()
