# -*- coding: utf-8 -*-
"""
Script para descargar y analizar logs de Railway automáticamente
Detecta errores, warnings y problemas críticos del sistema BruceW
"""
import subprocess
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime
import os

class AnalizadorLogsRailway:
    def __init__(self, carpeta_logs="C:\\Users\\PC 1\\AgenteVentas\\LOGS"):
        self.errores = []
        self.warnings = []
        self.llamadas = []
        self.problemas_criticos = defaultdict(list)
        self.carpeta_logs = carpeta_logs

        # Crear carpeta si no existe
        os.makedirs(self.carpeta_logs, exist_ok=True)

    def descargar_logs(self, limite_lineas=1000):
        """Descarga logs de Railway usando railway CLI"""
        print("\n" + "="*70)
        print("📥 DESCARGANDO LOGS DE RAILWAY")
        print("="*70 + "\n")

        try:
            # Verificar si railway CLI está instalado
            check = subprocess.run(
                ["railway", "--version"],
                capture_output=True,
                text=True
            )

            if check.returncode != 0:
                print("❌ Railway CLI no está instalado")
                print("\n📝 Para instalar:")
                print("   npm i -g @railway/cli")
                print("   railway login")
                print("\n")
                return None

            print(f"✅ Railway CLI detectado: {check.stdout.strip()}")
            print(f"📊 Descargando últimas {limite_lineas} líneas de logs...\n")

            # Descargar logs
            result = subprocess.run(
                ["railway", "logs", "--limit", str(limite_lineas)],
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='ignore'
            )

            if result.returncode != 0:
                print(f"❌ Error al descargar logs: {result.stderr}")
                return None

            logs = result.stdout

            # Guardar en archivo en la carpeta LOGS
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"logs_railway_{timestamp}.txt"
            filepath = os.path.join(self.carpeta_logs, filename)

            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(logs)

            print(f"✅ Logs descargados: {filepath}")
            print(f"📏 Tamaño: {len(logs)} caracteres\n")

            return logs

        except FileNotFoundError:
            print("❌ Railway CLI no encontrado")
            print("\n📝 OPCIÓN 1 - Instalación Railway CLI:")
            print("   1. Instalar: npm i -g @railway/cli")
            print("   2. Login: railway login")
            print("   3. Link proyecto: railway link")
            print("\n📝 OPCIÓN 2 - Descarga Manual (Más Fácil):")
            print("   1. Ejecuta: python descargar_logs_web.py")
            print("   2. O ejecuta: descargar_logs_manual.bat")
            print("   3. Sigue las instrucciones en pantalla")
            print("\n")
            return None
        except Exception as e:
            print(f"❌ Error: {e}")
            return None

    def analizar_errores(self, logs):
        """Analiza errores en los logs"""
        print("\n" + "="*70)
        print("🔍 ANALIZANDO ERRORES")
        print("="*70 + "\n")

        lineas = logs.split('\n')

        # Patrones de errores
        patrones_error = [
            (r'❌.*', 'Error general'),
            (r'ERROR:', 'Error Python'),
            (r'Traceback', 'Excepción Python'),
            (r'ApiError', 'Error API ElevenLabs'),
            (r'TwilioException', 'Error Twilio'),
            (r'quota_exceeded', 'Cuota excedida ElevenLabs'),
            (r'status_callback_error', 'Error callback Twilio'),
            (r'No se pudo generar', 'Error generación audio'),
        ]

        for i, linea in enumerate(lineas):
            for patron, tipo in patrones_error:
                if re.search(patron, linea, re.IGNORECASE):
                    self.errores.append({
                        'tipo': tipo,
                        'linea': i + 1,
                        'texto': linea.strip()
                    })

        # Agrupar por tipo
        errores_por_tipo = Counter([e['tipo'] for e in self.errores])

        if not errores_por_tipo:
            print("✅ No se detectaron errores\n")
            return

        print(f"Total de errores detectados: {len(self.errores)}\n")

        for tipo, count in errores_por_tipo.most_common():
            print(f"  • {tipo}: {count} ocurrencias")

        print("\n")

    def analizar_warnings(self, logs):
        """Analiza warnings y advertencias"""
        print("="*70)
        print("⚠️  ANALIZANDO WARNINGS")
        print("="*70 + "\n")

        lineas = logs.split('\n')

        patrones_warning = [
            (r'⚠️.*', 'Warning general'),
            (r'WARNING:', 'Warning Python'),
            (r'FIX \d+A:', 'Fix con reintentos'),
            (r'Reintentando', 'Reintento'),
            (r'timeout', 'Timeout'),
            (r'credits remaining', 'Créditos bajos'),
        ]

        for i, linea in enumerate(lineas):
            for patron, tipo in patrones_warning:
                if re.search(patron, linea, re.IGNORECASE):
                    self.warnings.append({
                        'tipo': tipo,
                        'linea': i + 1,
                        'texto': linea.strip()
                    })

        warnings_por_tipo = Counter([w['tipo'] for w in self.warnings])

        if not warnings_por_tipo:
            print("✅ No se detectaron warnings\n")
            return

        print(f"Total de warnings: {len(self.warnings)}\n")

        for tipo, count in warnings_por_tipo.most_common():
            print(f"  • {tipo}: {count} ocurrencias")

        print("\n")

    def analizar_llamadas(self, logs):
        """Analiza llamadas realizadas"""
        print("="*70)
        print("📞 ANALIZANDO LLAMADAS")
        print("="*70 + "\n")

        lineas = logs.split('\n')

        # Detectar inicio de llamadas
        patron_bruce = r'BRUCE(\d+)'

        llamadas_detectadas = set()

        for linea in lineas:
            match = re.search(patron_bruce, linea)
            if match:
                bruce_id = match.group(1)
                llamadas_detectadas.add(bruce_id)

        print(f"Total de llamadas detectadas: {len(llamadas_detectadas)}\n")

        if llamadas_detectadas:
            print("IDs de llamadas:")
            for bruce_id in sorted(llamadas_detectadas, key=int):
                print(f"  • BRUCE{bruce_id}")

        print("\n")

        return llamadas_detectadas

    def detectar_problemas_criticos(self, logs):
        """Detecta problemas críticos específicos"""
        print("="*70)
        print("🚨 PROBLEMAS CRÍTICOS DETECTADOS")
        print("="*70 + "\n")

        lineas = logs.split('\n')

        problemas = {
            'cuota_excedida': r'quota_exceeded|credits remaining.*while.*required',
            'ivr_detectado': r'IVR/CONTESTADORA DETECTADO',
            'repeticion': r'REPETICIÓN DETECTADA',
            'timeout_audio': r'timeout.*audio|Timeout waiting',
            'error_twilio': r'TwilioException|status_callback_error',
            'error_gpt': r'Error en GPT|OpenAI.*error',
            'llamada_fallida': r'resultado_llamada.*No contestó|Ocupado|Rechazado',
        }

        for nombre, patron in problemas.items():
            matches = []
            for i, linea in enumerate(lineas):
                if re.search(patron, linea, re.IGNORECASE):
                    matches.append({
                        'linea': i + 1,
                        'texto': linea.strip()
                    })

            if matches:
                self.problemas_criticos[nombre] = matches

        if not self.problemas_criticos:
            print("✅ No se detectaron problemas críticos\n")
            return

        for problema, ocurrencias in self.problemas_criticos.items():
            print(f"\n🔥 {problema.upper().replace('_', ' ')}: {len(ocurrencias)} ocurrencias")

            # Mostrar primeras 3 ocurrencias
            for occ in ocurrencias[:3]:
                print(f"   Línea {occ['linea']}: {occ['texto'][:100]}...")

            if len(ocurrencias) > 3:
                print(f"   ... y {len(ocurrencias) - 3} más")

        print("\n")

    def analizar_creditos(self, logs):
        """Analiza consumo de créditos de ElevenLabs"""
        print("="*70)
        print("💰 ANÁLISIS DE CRÉDITOS ELEVENLABS")
        print("="*70 + "\n")

        # Buscar menciones de créditos
        patron_creditos = r'(\d+)\s+credits?\s+(remaining|required)'

        creditos_mencionados = []

        for linea in logs.split('\n'):
            match = re.search(patron_creditos, linea, re.IGNORECASE)
            if match:
                cantidad = int(match.group(1))
                tipo = match.group(2)
                creditos_mencionados.append({
                    'cantidad': cantidad,
                    'tipo': tipo,
                    'linea': linea.strip()
                })

        if not creditos_mencionados:
            print("ℹ️  No se encontró información de créditos en los logs\n")
            return

        # Encontrar último valor de créditos restantes
        creditos_remaining = [c for c in creditos_mencionados if c['tipo'].lower() == 'remaining']

        if creditos_remaining:
            ultimo = creditos_remaining[-1]
            print(f"💵 Créditos restantes (último valor): {ultimo['cantidad']:,}")

            if ultimo['cantidad'] < 1000:
                print("   🚨 CRÍTICO: Créditos muy bajos!")
            elif ultimo['cantidad'] < 5000:
                print("   ⚠️  ADVERTENCIA: Créditos bajos")
            else:
                print("   ✅ Nivel aceptable")

        # Analizar créditos requeridos
        creditos_required = [c for c in creditos_mencionados if c['tipo'].lower() == 'required']

        if creditos_required:
            promedio_requerido = sum(c['cantidad'] for c in creditos_required) / len(creditos_required)
            print(f"\n📊 Promedio de créditos por generación: {promedio_requerido:.0f}")
            print(f"   Generaciones estimadas con créditos actuales: {ultimo['cantidad'] // promedio_requerido:.0f}")

        print("\n")

    def generar_reporte(self):
        """Genera reporte resumen"""
        print("="*70)
        print("📋 RESUMEN EJECUTIVO")
        print("="*70 + "\n")

        # Estado general
        total_issues = len(self.errores) + len(self.warnings)

        if total_issues == 0:
            print("✅ SISTEMA SALUDABLE - No se detectaron problemas")
        elif len(self.errores) == 0:
            print(f"⚠️  ATENCIÓN REQUERIDA - {len(self.warnings)} warnings detectados")
        else:
            print(f"🚨 ACCIÓN REQUERIDA - {len(self.errores)} errores y {len(self.warnings)} warnings")

        print("\n")

        # Top 5 errores más frecuentes
        if self.errores:
            print("🔥 Top 5 Errores Más Frecuentes:")
            errores_por_tipo = Counter([e['tipo'] for e in self.errores])
            for tipo, count in errores_por_tipo.most_common(5):
                print(f"   {count}x {tipo}")
            print("\n")

        # Problemas críticos
        if self.problemas_criticos:
            print("🚨 Problemas Críticos Activos:")
            for problema, ocurrencias in self.problemas_criticos.items():
                print(f"   • {problema.replace('_', ' ').title()}: {len(ocurrencias)} ocurrencias")
            print("\n")

        # Recomendaciones
        print("💡 RECOMENDACIONES:")

        if 'cuota_excedida' in self.problemas_criticos:
            print("   1. ⚠️  URGENTE: Recargar créditos de ElevenLabs")

        if 'timeout_audio' in self.problemas_criticos:
            print("   2. ⚠️  Revisar FIX 203: Reducir tamaño de mensajes")

        if 'repeticion' in self.problemas_criticos:
            print("   3. ✅ FIX 204 está detectando repeticiones correctamente")

        if 'ivr_detectado' in self.problemas_criticos:
            print("   4. ✅ FIX 202 está detectando IVRs correctamente")

        if not self.problemas_criticos:
            print("   ✅ Sistema funcionando correctamente")

        print("\n")

def main():
    print("\n" + "="*70)
    print("🔍 ANALIZADOR AUTOMÁTICO DE LOGS - RAILWAY")
    print("   Sistema BruceW - Detección de Errores y Problemas")
    print("="*70)

    # Verificar argumentos
    if len(sys.argv) > 1:
        # Analizar archivo existente
        archivo = sys.argv[1]
        print(f"\n📂 Analizando archivo: {archivo}")

        if not os.path.exists(archivo):
            print(f"❌ Archivo no encontrado: {archivo}")
            return

        with open(archivo, 'r', encoding='utf-8', errors='ignore') as f:
            logs = f.read()
    else:
        # Descargar logs de Railway
        analizador = AnalizadorLogsRailway()
        logs = analizador.descargar_logs(limite_lineas=1000)

        if not logs:
            print("\n❌ No se pudieron descargar los logs")
            print("\n💡 SOLUCIONES:")
            print("\n   OPCIÓN 1 - Descarga Manual (Recomendado):")
            print("      python descargar_logs_web.py")
            print("      O doble clic en: descargar_logs_manual.bat")
            print("\n   OPCIÓN 2 - Instalar Railway CLI:")
            print("      npm i -g @railway/cli")
            print("\n   OPCIÓN 3 - Usar archivo existente:")
            print("      python analizar_logs_railway.py LOGS\\archivo.txt")
            print("\n")
            return

    # Análisis completo
    analizador = AnalizadorLogsRailway()

    analizador.analizar_llamadas(logs)
    analizador.analizar_errores(logs)
    analizador.analizar_warnings(logs)
    analizador.detectar_problemas_criticos(logs)
    analizador.analizar_creditos(logs)
    analizador.generar_reporte()

    print("="*70)
    print("✅ Análisis completado")
    print("="*70 + "\n")

if __name__ == "__main__":
    main()
