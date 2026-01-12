# -*- coding: utf-8 -*-
"""
Sistema de Llamadas Masivas en Producción (Railway)
Lee contactos de Google Sheets y hace llamadas reales vía Twilio/Railway
"""

import os
import sys
import requests
import time
from dotenv import load_dotenv
from nioval_sheets_adapter import NiovalSheetsAdapter
from twilio.rest import Client

# Configurar encoding UTF-8 para Windows
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

load_dotenv()

# URL del servidor en Railway
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "https://nioval-webhook-server-production.up.railway.app")

# Credenciales Twilio
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")


class SistemaLlamadasMasivas:
    """Sistema para hacer llamadas masivas en producción"""

    def __init__(self):
        """Inicializa conexión con Google Sheets y Twilio"""
        print("\n🚀 Inicializando Sistema de Llamadas Masivas...")
        self.sheets_adapter = NiovalSheetsAdapter()

        # FIX 178: Inicializar cliente Twilio para verificar estado de llamadas
        if TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN:
            self.twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
            print("✅ Cliente Twilio inicializado")
        else:
            self.twilio_client = None
            print("⚠️  Cliente Twilio no disponible (credenciales faltantes)")

        print("✅ Conectado a Google Sheets\n")

    def ejecutar_llamadas(self, cantidad: int = 10, delay_entre_llamadas: int = 10, pedir_confirmacion: bool = True):
        """
        FIX 88: Ejecuta llamadas CONSECUTIVAS (una tras otra, esperando a que termine cada una)

        Args:
            cantidad: Número de llamadas a realizar
            delay_entre_llamadas: Segundos de espera DESPUÉS de que termine una llamada (default: 10)
            pedir_confirmacion: Si False, omite mensaje de confirmación (default: True)
        """
        print("\n" + "=" * 60)
        print(f"📞 INICIANDO LLAMADAS MASIVAS EN PRODUCCIÓN")
        print("=" * 60 + "\n")

        # Obtener contactos pendientes (sin valor en columna F)
        print("📋 Obteniendo contactos pendientes de Google Sheets...")
        contactos = self.sheets_adapter.obtener_contactos_pendientes(limite=cantidad)

        if not contactos:
            print("ℹ️  No hay contactos pendientes")
            return

        print(f"✅ Encontrados {len(contactos)} contactos pendientes\n")

        # Mostrar primeros contactos
        print("📝 Primeros 3 contactos:")
        for c in contactos[:3]:
            print(f"   Fila {c['fila']}: {c['nombre_negocio']} - {c['telefono']}")

        print(f"\n📞 Se realizarán {len(contactos)} llamadas")
        print(f"⏱️  Delay entre llamadas: {delay_entre_llamadas} segundos\n")

        # Confirmar (opcional)
        if pedir_confirmacion:
            confirmar = input("⚠️  ¿Deseas continuar? (s/n): ").strip().lower()
            if confirmar != 's':
                print("❌ Cancelado")
                return

        # Ejecutar llamadas
        resultados = {
            'exitosas': 0,
            'fallidas': 0,
            'total': len(contactos)
        }

        for i, contacto in enumerate(contactos, 1):
            print("\n" + "=" * 60)
            print(f"📞 LLAMADA {i}/{len(contactos)}")
            print("=" * 60 + "\n")

            fila = contacto['fila']
            nombre = contacto['nombre_negocio']
            telefono = contacto['telefono']

            print(f"📞 Fila {fila}: {nombre}")
            print(f"   Teléfono: {telefono}")

            # FIX 88: Hacer llamada vía Railway y obtener Call SID
            call_sid = self._iniciar_llamada_railway(contacto)

            if call_sid:
                resultados['exitosas'] += 1
                print("✅ Llamada iniciada correctamente")

                # FIX 178: ESPERAR A QUE LA LLAMADA TERMINE VERIFICANDO ESTADO REAL
                duracion = self._esperar_fin_llamada(call_sid)
                if duracion is not None:
                    print(f"✅ Llamada completada (duración: {duracion}s)")
                else:
                    print("⚠️  No se pudo verificar finalización de llamada")
            else:
                resultados['fallidas'] += 1
                print("❌ Error al iniciar llamada")

            # FIX 88: Esperar delay DESPUÉS de que termine la llamada (excepto en la última)
            if i < len(contactos):
                print(f"\n⏱️  Esperando {delay_entre_llamadas}s antes de la siguiente llamada...")
                time.sleep(delay_entre_llamadas)

        # Resumen final
        print("\n" + "=" * 60)
        print("📊 RESUMEN DE LLAMADAS")
        print("=" * 60)
        print(f"Total: {resultados['total']}")
        print(f"✅ Exitosas: {resultados['exitosas']}")
        print(f"❌ Fallidas: {resultados['fallidas']}")
        print(f"📈 Tasa de éxito: {round(resultados['exitosas']/resultados['total']*100, 1)}%")
        print("=" * 60 + "\n")

    def _iniciar_llamada_railway(self, contacto: dict) -> str:
        """
        FIX 88: Inicia una llamada a través de Railway

        Args:
            contacto: Diccionario completo con toda la información del contacto

        Returns:
            Call SID si se inició correctamente, None si hubo error
        """
        try:
            url = f"{WEBHOOK_URL}/iniciar-llamada"

            # Cargar referencia de columna U (si existe)
            fila = contacto['fila']
            referencia = self.sheets_adapter.obtener_referencia(fila)
            if referencia:
                contacto['referencia'] = referencia
                print(f"👥 Referencia encontrada: {referencia[:50]}...")

            # Enviar contacto completo con TODA la información
            payload = {
                "telefono": contacto['telefono'],
                "nombre_negocio": contacto['nombre_negocio'],
                "contacto_info": contacto,  # Enviar TODO el diccionario
                # FIX 179: Deshabilitar reintentos automáticos para evitar empalmes
                "deshabilitar_reintentos": True
            }

            print(f"🌐 Enviando solicitud a Railway: {url}")

            response = requests.post(url, json=payload, timeout=10)

            if response.status_code == 200:
                data = response.json()
                call_sid = data.get('call_sid', None)
                print(f"📞 Call SID: {call_sid}")
                return call_sid  # FIX 88: Retornar Call SID
            else:
                print(f"❌ Error HTTP {response.status_code}: {response.text}")
                return None

        except Exception as e:
            print(f"❌ Error al iniciar llamada: {e}")
            return None

    def _esperar_fin_llamada(self, call_sid: str, max_tiempo_espera: int = 180) -> int:
        """
        FIX 178: Verifica el estado REAL de la llamada en Twilio hasta que termine

        Args:
            call_sid: ID de la llamada de Twilio
            max_tiempo_espera: Tiempo máximo a esperar (default: 180s = 3 minutos)

        Returns:
            Duración de la llamada en segundos, o None si hubo error

        Estados de llamada en Twilio:
        - queued: En cola
        - ringing: Timbrando
        - in-progress: En progreso (conversación activa)
        - completed: Completada
        - busy: Ocupado
        - failed: Falló
        - no-answer: No respondió
        - canceled: Cancelada
        """
        if not call_sid or not self.twilio_client:
            print("⚠️  No se puede verificar estado (Call SID o cliente Twilio faltante)")
            # Fallback: esperar tiempo fijo
            time.sleep(45)
            return None

        print(f"🔍 Verificando estado de llamada {call_sid}...")

        inicio = time.time()
        tiempo_transcurrido = 0
        ultimo_estado = None

        # Estados que indican que la llamada terminó
        estados_finales = ["completed", "busy", "failed", "no-answer", "canceled"]

        while tiempo_transcurrido < max_tiempo_espera:
            try:
                # Consultar estado actual de la llamada
                call = self.twilio_client.calls(call_sid).fetch()
                estado_actual = call.status
                duracion = call.duration  # Duración en segundos (None si aún no termina)

                # Mostrar cambio de estado
                if estado_actual != ultimo_estado:
                    print(f"   📞 Estado: {estado_actual}")
                    ultimo_estado = estado_actual

                # Verificar si la llamada terminó
                if estado_actual in estados_finales:
                    duracion_total = int(duracion) if duracion else 0
                    print(f"   ✅ Llamada finalizada: {estado_actual} (duración: {duracion_total}s)")
                    return duracion_total

                # Esperar 3 segundos antes de volver a consultar
                time.sleep(3)
                tiempo_transcurrido = int(time.time() - inicio)

            except Exception as e:
                print(f"   ⚠️  Error consultando estado: {e}")
                # Esperar y reintentar
                time.sleep(5)
                tiempo_transcurrido = int(time.time() - inicio)

        # Si llegamos aquí, se agotó el tiempo máximo
        print(f"   ⚠️  Timeout alcanzado ({max_tiempo_espera}s) - continuando de todas formas")
        return None

    def ver_estadisticas(self):
        """Muestra estadísticas de contactos"""
        print("\n" + "=" * 60)
        print("📊 ESTADÍSTICAS DE CONTACTOS")
        print("=" * 60 + "\n")

        stats = self.sheets_adapter.obtener_estadisticas()

        print(f"Total contactos: {stats.get('total_contactos', 0)}")
        print(f"Con número: {stats.get('con_numero', 0)}")
        print(f"Llamados: {stats.get('llamados', 0)}")
        print(f"Pendientes: {stats.get('pendientes', 0)}")
        print(f"Progreso: {stats.get('porcentaje_completado', 0)}%")
        print("\n" + "=" * 60 + "\n")


def main():
    """Menú principal"""
    try:
        sistema = SistemaLlamadasMasivas()

        while True:
            print("\n" + "=" * 60)
            print("📞 SISTEMA DE LLAMADAS MASIVAS - PRODUCCIÓN")
            print("=" * 60 + "\n")

            print("1. Ver estadísticas")
            print("2. Ejecutar 1 llamada (prueba)")
            print("3. Ejecutar 2 llamadas (delay: 30s)")
            print("4. Ejecutar 5 llamadas (delay: 30s)")
            print("5. Ejecutar 10 llamadas (delay: 30s)")
            print("6. Ejecutar 50 llamadas (delay: 30s)")
            print("7. Ejecutar cantidad personalizada")
            print("0. Salir")

            opcion = input("\nSelecciona una opción: ").strip()

            if opcion == "1":
                sistema.ver_estadisticas()

            elif opcion == "2":
                sistema.ejecutar_llamadas(cantidad=1, delay_entre_llamadas=30, pedir_confirmacion=False)

            elif opcion == "3":
                sistema.ejecutar_llamadas(cantidad=2, delay_entre_llamadas=30)

            elif opcion == "4":
                sistema.ejecutar_llamadas(cantidad=5, delay_entre_llamadas=30)

            elif opcion == "5":
                sistema.ejecutar_llamadas(cantidad=10, delay_entre_llamadas=30)

            elif opcion == "6":
                confirmar = input("⚠️  ¿Ejecutar 50 llamadas? (s/n): ").strip().lower()
                if confirmar == 's':
                    sistema.ejecutar_llamadas(cantidad=50, delay_entre_llamadas=30)

            elif opcion == "7":
                try:
                    cantidad = int(input("¿Cuántas llamadas? "))
                    delay = int(input("¿Delay entre llamadas (segundos)? [default: 30]: ") or "30")
                    sistema.ejecutar_llamadas(cantidad=cantidad, delay_entre_llamadas=delay)
                except ValueError:
                    print("❌ Valores inválidos")

            elif opcion == "0":
                print("\n👋 Hasta pronto!")
                break

            else:
                print("❌ Opción inválida")

    except KeyboardInterrupt:
        print("\n\n⚠️  Programa interrumpido por el usuario")
    except Exception as e:
        print(f"\n❌ Error fatal: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
