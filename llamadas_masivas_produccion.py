"""
Sistema de Llamadas Masivas en Producción (Railway)
Lee contactos de Google Sheets y hace llamadas reales vía Twilio/Railway
"""

import os
import requests
import time
from dotenv import load_dotenv
from nioval_sheets_adapter import NiovalSheetsAdapter

load_dotenv()

# URL del servidor en Railway
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "https://nioval-webhook-server-production.up.railway.app")


class SistemaLlamadasMasivas:
    """Sistema para hacer llamadas masivas en producción"""

    def __init__(self):
        """Inicializa conexión con Google Sheets"""
        print("\n🚀 Inicializando Sistema de Llamadas Masivas...")
        self.sheets_adapter = NiovalSheetsAdapter()
        print("✅ Conectado a Google Sheets\n")

    def ejecutar_llamadas(self, cantidad: int = 10, delay_entre_llamadas: int = 30):
        """
        Ejecuta un lote de llamadas reales vía Railway

        Args:
            cantidad: Número de llamadas a realizar
            delay_entre_llamadas: Segundos de espera entre llamadas (default: 30)
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

        # Confirmar
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

            # Hacer llamada vía Railway
            exito = self._iniciar_llamada_railway(telefono, nombre, fila)

            if exito:
                resultados['exitosas'] += 1
                print("✅ Llamada iniciada correctamente")
                # NOTA: NO marcamos en columna F - los resultados se guardan en "HISTORIAL DE LLAMADAS"
            else:
                resultados['fallidas'] += 1
                print("❌ Error al iniciar llamada")

            # Esperar antes de la siguiente llamada (excepto en la última)
            if i < len(contactos):
                print(f"\n⏳ Esperando {delay_entre_llamadas}s antes de la siguiente llamada...")
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

    def _iniciar_llamada_railway(self, telefono: str, nombre_negocio: str, fila: int) -> bool:
        """
        Inicia una llamada a través de Railway

        Returns:
            True si se inició correctamente, False si hubo error
        """
        try:
            url = f"{WEBHOOK_URL}/iniciar-llamada"

            payload = {
                "telefono": telefono,
                "nombre_negocio": nombre_negocio,
                "contacto_info": {
                    "ID": fila,
                    "nombre_negocio": nombre_negocio,
                    "telefono": telefono
                }
            }

            print(f"🌐 Enviando solicitud a Railway: {url}")

            response = requests.post(url, json=payload, timeout=10)

            if response.status_code == 200:
                data = response.json()
                call_sid = data.get('call_sid', 'N/A')
                print(f"📞 Call SID: {call_sid}")
                return True
            else:
                print(f"❌ Error HTTP {response.status_code}: {response.text}")
                return False

        except Exception as e:
            print(f"❌ Error al iniciar llamada: {e}")
            return False

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
                sistema.ejecutar_llamadas(cantidad=1, delay_entre_llamadas=30)

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
