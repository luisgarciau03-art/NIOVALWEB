"""
FIX 200: Sistema de Monitoreo Automático de Créditos ElevenLabs

Este módulo:
1. Verifica créditos periódicamente
2. Genera alertas automáticas cuando están bajos
3. Registra el consumo en tiempo real
4. Previene llamadas cuando no hay créditos suficientes

Integración con servidor_llamadas.py
"""

import os
import time
import threading
from datetime import datetime
from dotenv import load_dotenv
from elevenlabs.client import ElevenLabs

load_dotenv()


class MonitorCreditosElevenLabs:
    """
    Monitor de créditos ElevenLabs con alertas automáticas
    """

    def __init__(self):
        self.api_key = os.getenv("ELEVENLABS_API_KEY")
        self.client = None
        self.ultimo_check = None
        self.caracteres_restantes = None
        self.caracteres_limite = None
        self.alertas_enviadas = {
            "critico": False,
            "bajo": False,
            "medio": False
        }

        # Thresholds
        self.CRITICO = 10000    # Menos de 10k caracteres (~30 llamadas)
        self.BAJO = 50000       # Menos de 50k caracteres (~160 llamadas)
        self.MEDIO = 100000     # Menos de 100k caracteres (~330 llamadas)

        # Intervalo de verificación (segundos)
        self.INTERVALO_CHECK = 300  # Cada 5 minutos

        # Inicializar cliente
        if self.api_key:
            try:
                self.client = ElevenLabs(api_key=self.api_key)
                print("✅ Monitor de créditos ElevenLabs inicializado")
            except Exception as e:
                print(f"⚠️ Error inicializando monitor de créditos: {e}")

    def verificar_creditos_ahora(self):
        """
        Verifica créditos inmediatamente y retorna estado
        """
        if not self.client:
            return None

        try:
            subscription = self.client.user.get_subscription()

            if hasattr(subscription, 'character_count'):
                self.caracteres_restantes = subscription.character_limit - subscription.character_count
                self.caracteres_limite = subscription.character_limit
                self.ultimo_check = datetime.now()

                # Calcular llamadas restantes (promedio 300 caracteres por llamada)
                llamadas_restantes = self.caracteres_restantes // 300

                # Generar alertas según nivel
                if self.caracteres_restantes < self.CRITICO:
                    if not self.alertas_enviadas["critico"]:
                        print("\n" + "="*60)
                        print("🚨🚨🚨 ALERTA CRÍTICA - CRÉDITOS ELEVENLABS 🚨🚨🚨")
                        print("="*60)
                        print(f"⚠️  Caracteres restantes: {self.caracteres_restantes:,}")
                        print(f"⚠️  Llamadas restantes: ~{llamadas_restantes}")
                        print(f"⚠️  ACCIÓN REQUERIDA: RECARGAR INMEDIATAMENTE")
                        print("="*60 + "\n")
                        self.alertas_enviadas["critico"] = True

                elif self.caracteres_restantes < self.BAJO:
                    if not self.alertas_enviadas["bajo"]:
                        print("\n" + "="*60)
                        print("⚠️  ALERTA - CRÉDITOS BAJOS ELEVENLABS")
                        print("="*60)
                        print(f"📊 Caracteres restantes: {self.caracteres_restantes:,}")
                        print(f"📞 Llamadas restantes: ~{llamadas_restantes}")
                        print(f"📢 ACCIÓN SUGERIDA: Considerar recarga pronto")
                        print("="*60 + "\n")
                        self.alertas_enviadas["bajo"] = True

                elif self.caracteres_restantes < self.MEDIO:
                    if not self.alertas_enviadas["medio"]:
                        print(f"📊 Créditos ElevenLabs: {self.caracteres_restantes:,} caracteres (~{llamadas_restantes} llamadas)")
                        self.alertas_enviadas["medio"] = True

                # Reset alertas si los créditos suben (recarga)
                if self.caracteres_restantes > self.MEDIO:
                    self.alertas_enviadas = {
                        "critico": False,
                        "bajo": False,
                        "medio": False
                    }

                return {
                    "caracteres_restantes": self.caracteres_restantes,
                    "caracteres_limite": self.caracteres_limite,
                    "llamadas_restantes": llamadas_restantes,
                    "estado": self._calcular_estado(),
                    "ultimo_check": self.ultimo_check
                }

        except Exception as e:
            print(f"⚠️ Error verificando créditos: {e}")
            return None

    def _calcular_estado(self):
        """
        Calcula el estado actual según créditos restantes
        """
        if self.caracteres_restantes < self.CRITICO:
            return "CRITICO"
        elif self.caracteres_restantes < self.BAJO:
            return "BAJO"
        elif self.caracteres_restantes < self.MEDIO:
            return "MEDIO"
        else:
            return "OPTIMO"

    def tiene_creditos_suficientes(self, palabras_estimadas=50):
        """
        Verifica si hay créditos suficientes para una llamada

        Args:
            palabras_estimadas: Número estimado de palabras para la llamada

        Returns:
            bool: True si hay créditos suficientes
        """
        if not self.caracteres_restantes:
            # Si no hemos verificado aún, hacer check ahora
            self.verificar_creditos_ahora()

        if not self.caracteres_restantes:
            # Si aún no hay datos, asumir que sí hay (fail-open)
            return True

        # Estimación: ~6 caracteres por palabra (promedio español)
        caracteres_necesarios = palabras_estimadas * 6

        return self.caracteres_restantes >= caracteres_necesarios

    def iniciar_monitoreo_automatico(self):
        """
        Inicia un thread que verifica créditos periódicamente
        """
        def monitor_loop():
            print(f"🔄 Monitor de créditos iniciado (cada {self.INTERVALO_CHECK}s)")

            while True:
                try:
                    self.verificar_creditos_ahora()
                    time.sleep(self.INTERVALO_CHECK)
                except Exception as e:
                    print(f"⚠️ Error en monitor loop: {e}")
                    time.sleep(60)  # Reintentar en 1 minuto si hay error

        # Verificar créditos inmediatamente al iniciar
        self.verificar_creditos_ahora()

        # Iniciar thread de monitoreo
        monitor_thread = threading.Thread(target=monitor_loop, daemon=True)
        monitor_thread.start()

    def obtener_reporte(self):
        """
        Genera un reporte del estado actual
        """
        if not self.caracteres_restantes:
            return "⚠️ No hay datos de créditos disponibles"

        llamadas_restantes = self.caracteres_restantes // 300
        estado = self._calcular_estado()

        emoji_estado = {
            "OPTIMO": "✅",
            "MEDIO": "📊",
            "BAJO": "⚠️",
            "CRITICO": "🚨"
        }.get(estado, "❓")

        reporte = f"""
{emoji_estado} ESTADO ELEVENLABS: {estado}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 Caracteres restantes: {self.caracteres_restantes:,} / {self.caracteres_limite:,}
📞 Llamadas restantes: ~{llamadas_restantes}
🕐 Último check: {self.ultimo_check.strftime('%Y-%m-%d %H:%M:%S') if self.ultimo_check else 'N/A'}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
        return reporte.strip()


# Instancia global para usar en servidor_llamadas.py
_monitor_global = None


def obtener_monitor():
    """
    Obtiene la instancia global del monitor (singleton)
    """
    global _monitor_global
    if _monitor_global is None:
        _monitor_global = MonitorCreditosElevenLabs()
    return _monitor_global


def iniciar_monitoreo():
    """
    Inicia el monitoreo automático de créditos
    """
    monitor = obtener_monitor()
    monitor.iniciar_monitoreo_automatico()
    return monitor


# Script standalone para testing
if __name__ == "__main__":
    print("\n" + "="*60)
    print("🚀 FIX 200: MONITOR DE CRÉDITOS ELEVENLABS")
    print("="*60 + "\n")

    monitor = MonitorCreditosElevenLabs()

    # Verificar créditos
    resultado = monitor.verificar_creditos_ahora()

    if resultado:
        print("\n" + monitor.obtener_reporte())

        # Test de verificación
        print("\n🧪 TESTS DE VERIFICACIÓN:")
        print(f"  ✓ ¿Créditos suficientes para llamada de 50 palabras? {monitor.tiene_creditos_suficientes(50)}")
        print(f"  ✓ ¿Créditos suficientes para llamada de 200 palabras? {monitor.tiene_creditos_suficientes(200)}")

        print("\n✅ Monitor funcionando correctamente")
        print("   Para integrar con el servidor, importar: from monitor_creditos_elevenlabs import iniciar_monitoreo")

    else:
        print("\n❌ No se pudo verificar créditos")
        print("   Verificar API key y conexión")
