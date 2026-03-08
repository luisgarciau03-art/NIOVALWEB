"""
Sistema de Llamadas NIOVAL - Integrado con Spreadsheet Real
Usa la hoja "LISTA DE CONTACTOS" existente
"""

import time
from datetime import datetime
from typing import List, Dict
from nioval_sheets_adapter import NiovalSheetsAdapter
from resultados_sheets_adapter import ResultadosSheetsAdapter
from agente_ventas import AgenteVentas
from whatsapp_validator import WhatsAppValidator, WhatsAppValidatorCache
import os
from dotenv import load_dotenv

load_dotenv()


class SistemaLlamadasNioval:
    """Sistema principal de llamadas integrado con el spreadsheet real de NIOVAL"""

    def __init__(self):
        """Inicializa el sistema"""
        print("\n" + "=" * 60)
        print(" SISTEMA DE LLAMADAS NIOVAL")
        print("=" * 60 + "\n")

        # Inicializar componentes
        self.sheets_adapter = self._inicializar_sheets()
        self.resultados_adapter = self._inicializar_resultados()
        self.whatsapp_validator = self._inicializar_whatsapp()

        # Configuración
        self.delay_entre_llamadas = int(os.getenv("DELAY_LLAMADAS_SEG", "5"))  # 5 segundos para testing

        print(f"\n Sistema listo")
        print(f"  Delay entre llamadas: {self.delay_entre_llamadas}s")

    def _inicializar_sheets(self) -> NiovalSheetsAdapter:
        """Inicializa la conexión a Google Sheets"""
        try:
            adapter = NiovalSheetsAdapter()
            return adapter
        except Exception as e:
            print(f" Error al conectar con Google Sheets: {e}")
            raise

    def _inicializar_resultados(self) -> ResultadosSheetsAdapter:
        """Inicializa la conexión al spreadsheet de resultados"""
        try:
            adapter = ResultadosSheetsAdapter()
            return adapter
        except Exception as e:
            print(f" Error al conectar con spreadsheet de resultados: {e}")
            raise

    def _inicializar_whatsapp(self) -> WhatsAppValidatorCache:
        """Inicializa el validador de WhatsApp"""
        try:
            method = os.getenv("WHATSAPP_VALIDATOR_METHOD", "formato")
            validator = WhatsAppValidator(method=method)
            validator_cache = WhatsAppValidatorCache(validator)
            print(f" Validador de WhatsApp: {method}")
            return validator_cache
        except Exception as e:
            print(f" Error al inicializar validador: {e}")
            return None

    def ejecutar_llamadas(self, cantidad: int = 10):
        """
        Ejecuta un lote de llamadas

        Args:
            cantidad: Número de llamadas a realizar
        """
        print("\n" + "=" * 60)
        print(f" INICIANDO LLAMADAS - {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        print("=" * 60 + "\n")

        # Obtener contactos pendientes
        contactos = self.sheets_adapter.obtener_contactos_pendientes(limite=cantidad)

        if not contactos:
            print("ℹ No hay contactos pendientes")
            return

        print(f" Contactos a llamar: {len(contactos)}\n")

        # Estadísticas
        resultados = {
            'exitosas': 0,
            'con_whatsapp': 0,
            'con_email': 0,
            'sin_interes': 0,
            'errores': 0
        }

        # Ejecutar llamadas
        for idx, contacto in enumerate(contactos, 1):
            print(f"\n{'='*60}")
            print(f" LLAMADA {idx}/{len(contactos)}")
            print(f"{'='*60}")

            try:
                resultado = self.realizar_llamada(contacto)

                # Actualizar estadísticas
                if resultado.get('exito'):
                    resultados['exitosas'] += 1

                    if resultado.get('whatsapp_capturado'):
                        resultados['con_whatsapp'] += 1

                    if resultado.get('email_capturado'):
                        resultados['con_email'] += 1

                    if not resultado.get('interesado'):
                        resultados['sin_interes'] += 1
                else:
                    resultados['errores'] += 1

                # Delay entre llamadas
                if idx < len(contactos):
                    print(f"\n Esperando {self.delay_entre_llamadas}s...")
                    time.sleep(self.delay_entre_llamadas)

            except Exception as e:
                print(f" Error en llamada: {e}")
                resultados['errores'] += 1

        # Resumen final
        self._mostrar_resumen(resultados, len(contactos))

    def realizar_llamada(self, contacto: Dict) -> Dict:
        """
        Realiza una llamada a un contacto

        Args:
            contacto: Datos del contacto

        Returns:
            Dict con resultado
        """
        fila = contacto['fila']
        nombre = contacto['nombre_negocio']
        telefono = contacto['telefono']

        print(f"\n Fila {fila}: {nombre}")
        print(f"   Teléfono: {telefono}")

        # Crear agente para esta llamada
        agente = AgenteVentas(
            contacto_info=contacto,
            sheets_manager=None,  # No usamos el manager genérico
            whatsapp_validator=self.whatsapp_validator
        )

        try:
            # SIMULACIÓN DE LLAMADA (Modo testing sin Twilio)
            resultado = self._simular_llamada(agente, contacto)

            # NOTA: NO marcamos en columna F (eso se hace en otro spreadsheet)

            # Validar y actualizar WhatsApp si se capturó
            if resultado.get('whatsapp_capturado'):
                whatsapp_capturado = resultado['whatsapp_capturado']

                # Validar que el número tenga WhatsApp activo
                print(f"\n Validando WhatsApp: {whatsapp_capturado}")

                if self.whatsapp_validator:
                    validacion = self.whatsapp_validator.validar(whatsapp_capturado)

                    if validacion.get('tiene_whatsapp'):
                        # WhatsApp confirmado: actualizar columna E
                        print(f" WhatsApp validado correctamente")
                        self.sheets_adapter.actualizar_numero_con_whatsapp(
                            fila=fila,
                            whatsapp=whatsapp_capturado
                        )
                    else:
                        # No tiene WhatsApp: solo informar, no actualizar
                        print(f" El número no tiene WhatsApp activo (no se actualiza columna E)")
                        print(f"   Método: {validacion.get('metodo', 'N/A')}")
                else:
                    # Si no hay validador, asumir que es válido (modo formato)
                    print(f" Sin validador configurado, actualizando sin validación")
                    self.sheets_adapter.actualizar_numero_con_whatsapp(
                        fila=fila,
                        whatsapp=whatsapp_capturado
                    )

            # Registrar Email si se capturó
            if resultado.get('email_capturado'):
                self.sheets_adapter.registrar_email_capturado(
                    fila=fila,
                    email=resultado['email_capturado']
                )

            # Guardar resultado en el spreadsheet de resultados (Formulario de 7 preguntas)
            self._guardar_resultado_llamada(resultado, contacto)

            return resultado

        except Exception as e:
            print(f" Error: {e}")
            return {
                'exito': False,
                'error': str(e)
            }

    def _simular_llamada(self, agente: AgenteVentas, contacto: Dict) -> Dict:
        """
        Simula una llamada (para testing sin Twilio)

        Args:
            agente: Instancia de AgenteVentas
            contacto: Datos del contacto

        Returns:
            Dict con resultado de la simulación
        """
        print("\n MODO SIMULACIÓN")

        # Mensaje inicial
        mensaje_inicial = agente.iniciar_conversacion()
        print(f"\n Bruce: {mensaje_inicial}")

        # Simular respuestas del cliente
        import random

        respuestas_simuladas = [
            # Casos con interés
            {
                'texto': "Sí, soy el encargado",
                'seguimiento': [
                    "Me interesa ver el catálogo",
                    "Mi WhatsApp es 3312345678",
                    "Perfecto, espero el catálogo"
                ]
            },
            {
                'texto': "Sí, ¿qué productos manejan?",
                'seguimiento': [
                    "Mándame información al 6621234567",
                    "Bueno, espero tu mensaje"
                ]
            },
            # Casos sin interés
            {
                'texto': "No me interesa",
                'seguimiento': []
            },
            {
                'texto': "Ya tenemos proveedores",
                'seguimiento': []
            },
            # No contesta
            {
                'texto': "[SIN RESPUESTA]",
                'seguimiento': []
            }
        ]

        caso = random.choice(respuestas_simuladas)

        print(f" Cliente: {caso['texto']}")

        # Si no contesta
        if "[SIN RESPUESTA]" in caso['texto']:
            agente.motivo_no_contacto = "No contesta"
            return {
                'exito': False,
                'notas': 'No contesta',
                'interesado': False
            }

        # Procesar primera respuesta
        respuesta_agente = agente.procesar_respuesta(caso['texto'])
        print(f" Bruce: {respuesta_agente}")

        # Procesar respuestas de seguimiento
        for respuesta_cliente in caso['seguimiento']:
            print(f"\n Cliente: {respuesta_cliente}")

            respuesta_agente = agente.procesar_respuesta(respuesta_cliente)
            print(f" Bruce: {respuesta_agente}")

            # Pequeña pausa
            time.sleep(0.5)

        # Resultado final
        resultado = {
            'exito': True,
            'interesado': agente.lead_data.get('interesado', False),
            'whatsapp_capturado': agente.lead_data.get('whatsapp', ''),
            'email_capturado': agente.lead_data.get('email', ''),
            'notas': agente.lead_data.get('notas', '')[:100]  # Primeros 100 caracteres
        }

        # Mostrar resumen
        print(f"\n{''*60}")
        print(" RESUMEN DE LA LLAMADA:")
        print(f"   Interesado: {' Sí' if resultado['interesado'] else ' No'}")
        if resultado['whatsapp_capturado']:
            print(f"    WhatsApp: {resultado['whatsapp_capturado']}")
        if resultado['email_capturado']:
            print(f"    Email: {resultado['email_capturado']}")
        print(f"{''*60}")

        return resultado

    def _guardar_resultado_llamada(self, resultado: Dict, contacto: Dict):
        """
        Guarda el resultado de la llamada en el spreadsheet de resultados

        Args:
            resultado: Dict con el resultado de la llamada (lead_data)
            contacto: Dict con información del contacto
        """
        try:
            print(f"\n Guardando resultado en spreadsheet...")

            # Obtener lead_data del resultado
            lead_data = resultado.get('lead_data', {})

            # Preparar datos para el spreadsheet de resultados
            datos_guardado = {
                # Datos básicos
                'nombre_negocio': contacto.get('nombre_negocio', ''),

                # Estado de llamada (Pregunta 0)
                'estado_llamada': lead_data.get('pregunta_0', 'Respondio'),

                # Formulario de 7 preguntas
                'pregunta_1': lead_data.get('pregunta_1', ''),  # Necesidades (múltiple)
                'pregunta_2': lead_data.get('pregunta_2', ''),  # Toma decisiones (Sí/No)
                'pregunta_3': lead_data.get('pregunta_3', ''),  # Pedido inicial
                'pregunta_4': lead_data.get('pregunta_4', ''),  # Pedido muestra (Sí/No)
                'pregunta_5': lead_data.get('pregunta_5', ''),  # Fecha (Sí/No/Tal vez)
                'pregunta_6': lead_data.get('pregunta_6', ''),  # TDC (Sí/No/Tal vez)
                'pregunta_7': lead_data.get('pregunta_7', ''),  # Conclusión (automático)

                # Resultado
                'resultado': lead_data.get('resultado', ''),  # APROBADO/NEGADO

                # Duración estimada
                'duracion': resultado.get('duracion_estimada', ''),
            }

            # Guardar en spreadsheet de resultados
            exito = self.resultados_adapter.guardar_resultado_llamada(datos_guardado)

            if exito:
                print(f" Resultado guardado exitosamente")
            else:
                print(f" No se pudo guardar el resultado")

        except Exception as e:
            print(f" Error al guardar resultado: {e}")
            import traceback
            traceback.print_exc()

    def _mostrar_resumen(self, resultados: Dict, total: int):
        """Muestra resumen de las llamadas"""
        print("\n\n" + "=" * 60)
        print(" RESUMEN DE LLAMADAS")
        print("=" * 60)
        print(f" Total llamadas: {total}")
        print(f" Exitosas: {resultados['exitosas']}")
        print(f" WhatsApps capturados: {resultados['con_whatsapp']}")
        print(f" Emails capturados: {resultados['con_email']}")
        print(f" Con interés: {resultados['exitosas'] - resultados['sin_interes']}")
        print(f"  Sin interés: {resultados['sin_interes']}")
        print(f" Errores: {resultados['errores']}")

        if resultados['exitosas'] > 0:
            tasa_whatsapp = (resultados['con_whatsapp'] / resultados['exitosas']) * 100
            print(f"\n Tasa captura WhatsApp: {tasa_whatsapp:.1f}%")

        print("=" * 60 + "\n")

    def ver_estadisticas(self):
        """Muestra estadísticas generales del spreadsheet"""
        print("\n" + "=" * 60)
        print(" ESTADÍSTICAS GENERALES")
        print("=" * 60)

        stats = self.sheets_adapter.obtener_estadisticas()

        print(f"\n Total contactos: {stats.get('total_contactos', 0)}")
        print(f" Con número: {stats.get('con_numero', 0)}")
        print(f" Llamados: {stats.get('llamados', 0)}")
        print(f" Pendientes: {stats.get('pendientes', 0)}")
        print(f" Progreso: {stats.get('porcentaje_completado', 0)}%")

        print("\n" + "=" * 60)


def main():
    """Función principal"""
    print("""

  SISTEMA DE LLAMADAS NIOVAL                           
  Integrado con Google Sheets                          

    """)

    try:
        # Inicializar sistema
        sistema = SistemaLlamadasNioval()

        # Menú
        while True:
            print("\n OPCIONES:")
            print("1. Ver estadísticas generales")
            print("2. Ejecutar 5 llamadas de prueba")
            print("3. Ejecutar 10 llamadas")
            print("4. Ejecutar llamadas masivas (50)")
            print("0. Salir")

            opcion = input("\nSelecciona una opción: ").strip()

            if opcion == "1":
                sistema.ver_estadisticas()

            elif opcion == "2":
                sistema.ejecutar_llamadas(cantidad=5)

            elif opcion == "3":
                sistema.ejecutar_llamadas(cantidad=10)

            elif opcion == "4":
                confirmar = input("  ¿Ejecutar 50 llamadas? (s/n): ").strip().lower()
                if confirmar == 's':
                    sistema.ejecutar_llamadas(cantidad=50)

            elif opcion == "0":
                print("\n Hasta pronto!")
                break

            else:
                print(" Opción inválida")

    except Exception as e:
        print(f"\n Error fatal: {e}")
        print("\n Verifica:")
        print("   1. Archivo de credenciales: bubbly-subject-412101-c969f4a975c5.json")
        print("   2. Acceso al spreadsheet compartido")
        print("   3. Hoja 'LISTA DE CONTACTOS' existe")


if __name__ == "__main__":
    main()
