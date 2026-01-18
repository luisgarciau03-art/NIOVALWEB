"""
Sistema de Auto-Mejora Continua para Bruce W
Analiza el desempeño semanal y optimiza el SYSTEM_PROMPT automáticamente
"""

import os
import json
from datetime import datetime, timedelta
from openai import OpenAI
from dotenv import load_dotenv
from resultados_sheets_adapter import ResultadosSheetsAdapter

# Cargar variables de entorno
load_dotenv()

# Inicializar cliente OpenAI
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
openai_client = OpenAI(api_key=OPENAI_API_KEY)


class AutoMejoraBruce:
    """
    Sistema de auto-mejora que analiza las llamadas de la última semana
    y genera recomendaciones para optimizar el SYSTEM_PROMPT
    """

    def __init__(self):
        self.resultados_adapter = ResultadosSheetsAdapter()
        self.archivo_prompt = "agente_ventas.py"
        self.archivo_historial = "historial_mejoras_bruce.json"

    def analizar_semana(self):
        """
        Analiza todas las llamadas de la última semana y genera insights
        """
        print("\n" + "=" * 60)
        print("🔍 ANÁLISIS SEMANAL DE DESEMPEÑO - BRUCE W")
        print("=" * 60)

        try:
            # Obtener estadísticas de la última semana
            stats = self._obtener_estadisticas_semana()

            if not stats:
                print("❌ No hay datos suficientes para analizar")
                return None

            print(f"\n📊 Datos de la última semana:")
            print(f"   Total de llamadas: {stats['total_llamadas']}")
            print(f"   Tasa de conversión: {stats['tasa_conversion']:.1f}%")
            print(f"   WhatsApps capturados: {stats['whatsapps_capturados']}")
            print(f"   Nivel de interés promedio: {stats['interes_promedio']}")
            print(f"   Estado de ánimo predominante: {stats['animo_predominante']}")

            # Analizar patrones con GPT
            print("\n🤖 Analizando patrones con GPT-4o-mini...")
            analisis_gpt = self._analizar_con_gpt(stats)

            if analisis_gpt:
                print("\n📋 RECOMENDACIONES GENERADAS:")
                print(f"\n{analisis_gpt['resumen']}")

                if analisis_gpt.get('mejoras_criticas'):
                    print("\n🔴 Mejoras Críticas:")
                    for mejora in analisis_gpt['mejoras_criticas']:
                        print(f"   • {mejora}")

                if analisis_gpt.get('mejoras_sugeridas'):
                    print("\n🟡 Mejoras Sugeridas:")
                    for mejora in analisis_gpt['mejoras_sugeridas']:
                        print(f"   • {mejora}")

                return {
                    'stats': stats,
                    'analisis': analisis_gpt,
                    'fecha': datetime.now().strftime("%Y-%m-%d")
                }

        except Exception as e:
            print(f"❌ Error al analizar semana: {e}")
            import traceback
            traceback.print_exc()
            return None

    def _obtener_estadisticas_semana(self):
        """
        Obtiene estadísticas de las llamadas de la última semana
        """
        try:
            # Leer todas las filas del spreadsheet
            todas_filas = self.resultados_adapter.hoja_resultados.get_all_values()

            if len(todas_filas) <= 1:  # Solo headers
                return None

            # Fecha de hace 7 días
            hace_7_dias = datetime.now() - timedelta(days=7)

            # Analizar datos
            total_llamadas = 0
            aprobados = 0
            whatsapps = 0
            niveles_interes = []
            estados_animo = []

            # Iterar desde la fila 2 (saltar header)
            for fila in todas_filas[1:]:
                if len(fila) < 2:
                    continue

                # Columna A: Timestamp
                timestamp_str = fila[0] if len(fila) > 0 else ""

                # Parsear fecha (formato: dd/mm/yyyy HH:MM:SS)
                try:
                    if timestamp_str:
                        timestamp = datetime.strptime(timestamp_str.split()[0], "%d/%m/%Y")

                        # Solo últimos 7 días
                        if timestamp < hace_7_dias:
                            continue
                except Exception:
                    continue  # Formato de fecha inválido, saltar fila

                total_llamadas += 1

                # Columna S: Resultado
                resultado = fila[18] if len(fila) > 18 else ""
                if resultado == "APROBADO":
                    aprobados += 1

                # Columna V: Nivel de interés
                nivel_interes = fila[21] if len(fila) > 21 else ""
                if nivel_interes:
                    niveles_interes.append(nivel_interes)

                # Columna W: Estado de ánimo
                estado_animo = fila[22] if len(fila) > 22 else ""
                if estado_animo:
                    estados_animo.append(estado_animo)

            # Calcular métricas
            tasa_conversion = (aprobados / total_llamadas * 100) if total_llamadas > 0 else 0

            # Nivel de interés promedio
            interes_valores = {'Alto': 3, 'Medio': 2, 'Bajo': 1}
            if niveles_interes:
                promedio_numerico = sum(interes_valores.get(n, 2) for n in niveles_interes) / len(niveles_interes)
                if promedio_numerico >= 2.5:
                    interes_promedio = "Alto"
                elif promedio_numerico >= 1.5:
                    interes_promedio = "Medio"
                else:
                    interes_promedio = "Bajo"
            else:
                interes_promedio = "Medio"

            # Estado de ánimo predominante
            if estados_animo:
                animo_predominante = max(set(estados_animo), key=estados_animo.count)
            else:
                animo_predominante = "Neutral"

            return {
                'total_llamadas': total_llamadas,
                'aprobados': aprobados,
                'tasa_conversion': tasa_conversion,
                'whatsapps_capturados': aprobados,  # Aproximado
                'interes_promedio': interes_promedio,
                'animo_predominante': animo_predominante,
                'niveles_interes': niveles_interes,
                'estados_animo': estados_animo
            }

        except Exception as e:
            print(f"❌ Error al obtener estadísticas: {e}")
            return None

    def _analizar_con_gpt(self, stats):
        """
        Usa GPT-4o-mini para analizar las estadísticas y generar recomendaciones
        """
        try:
            prompt = f"""Eres un experto en optimización de scripts de ventas telefónicas. Analiza estas métricas de Bruce W (agente de ventas de NIOVAL) y genera cambios ESPECÍFICOS Y TEXTUALES para el SYSTEM_PROMPT.

📊 MÉTRICAS DE LA SEMANA:
- Total de llamadas: {stats['total_llamadas']}
- Tasa de conversión: {stats['tasa_conversion']:.1f}%
- WhatsApps capturados: {stats['whatsapps_capturados']}
- Nivel de interés promedio: {stats['interes_promedio']}
- Estado de ánimo predominante: {stats['animo_predominante']}

Distribución de interés:
{self._generar_distribucion(stats['niveles_interes'])}

Distribución de ánimo:
{self._generar_distribucion(stats['estados_animo'])}

INSTRUCCIONES CRÍTICAS:
1. En "modificaciones_prompt", propón cambios TEXTUALES específicos que se puedan copiar/pegar directamente
2. Cada cambio debe incluir el texto EXACTO a agregar o reemplazar en el script
3. Enfócate en frases, preguntas o respuestas concretas que Bruce puede usar
4. NO uses generalidades como "mejorar el tono" - especifica QUÉ decir exactamente
5. Basa tus sugerencias en los datos: si la conversión es baja, propón mejores cierres; si el ánimo es negativo, propón lenguaje más empático

EJEMPLO DE CAMBIO BIEN HECHO:
❌ MAL: "Mejorar la apertura para generar más interés"
✅ BIEN: "Reemplazar 'Buenos días' por: 'Buenos días, ¿hablo con [Nombre]? Excelente, le llamo de NIOVAL porque veo que tiene una [ferretería/abarrotes] y queremos apoyarle con mejores precios en sus compras. ¿Tiene un minuto?'"

EJEMPLO DE MOTIVO BIEN HECHO:
❌ MAL: "Para mejorar conversión"
✅ BIEN: "Solo 12% de llamadas superaron la apertura - el cliente cuelga antes de entender el valor. Necesitamos captar atención en primeros 10 segundos."

Responde SOLO en formato JSON:
{{
  "resumen": "Análisis de 2-3 líneas enfocado en datos concretos",
  "mejoras_criticas": [
    "Mejora crítica 1 con datos específicos (ej: 'Solo 2 de 1147 llamadas convirtieron - 0.17%')",
    "Mejora crítica 2 con datos"
  ],
  "mejoras_sugeridas": [
    "Mejora sugerida 1 con datos",
    "Mejora sugerida 2 con datos"
  ],
  "modificaciones_prompt": [
    {{
      "seccion": "FASE 1: APERTURA",
      "cambio": "TEXTO EXACTO del nuevo script de apertura entre comillas. Ejemplo: 'Buenos días, ¿hablo con [Nombre]? Le llamo de NIOVAL, somos distribuidores mayoristas...'",
      "texto_original": "Si conoces el texto actual que se debe reemplazar, inclúyelo aquí (opcional)",
      "motivo": "Dato específico que justifica el cambio. Ejemplo: 'Solo 145 de 1147 llamadas (12.6%) superaron la apertura - los clientes cuelgan sin entender el valor'",
      "impacto": "Alto/Medio/Bajo"
    }},
    {{
      "seccion": "MANEJO DE OBJECIONES - Ya tengo proveedores",
      "cambio": "TEXTO EXACTO de la nueva respuesta. Ejemplo: 'Perfecto, eso habla bien de su negocio. La mayoría de nuestros clientes trabajan con 2-3 proveedores para comparar. ¿Qué es lo que más valora de sus proveedores actuales: precio, crédito o entrega rápida?'",
      "texto_original": "Si conoces la respuesta actual, inclúyela",
      "motivo": "Dato específico. Ejemplo: 'De 230 clientes que dijeron tener proveedores, solo 34 (14.8%) aceptaron continuar - la respuesta actual no genera curiosidad'",
      "impacto": "Alto/Medio/Bajo"
    }}
  ]
}}

RECUERDA: Cada "cambio" debe ser TEXTO LITERAL que se pueda usar directamente en las llamadas."""

            response = openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "Eres un experto en optimización de scripts de ventas. Eres directo, específico y enfocado en resultados medibles."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=1000
            )

            # Parsear JSON
            analisis_texto = response.choices[0].message.content.strip()
            if "```json" in analisis_texto:
                analisis_texto = analisis_texto.split("```json")[1].split("```")[0].strip()
            elif "```" in analisis_texto:
                analisis_texto = analisis_texto.split("```")[1].split("```")[0].strip()

            return json.loads(analisis_texto)

        except Exception as e:
            print(f"❌ Error al analizar con GPT: {e}")
            return None

    def _generar_distribucion(self, lista):
        """Genera un string con la distribución de una lista"""
        if not lista:
            return "Sin datos"

        from collections import Counter
        conteo = Counter(lista)
        return ", ".join([f"{key}: {value}" for key, value in conteo.items()])

    def guardar_historial(self, analisis):
        """
        Guarda el análisis en el historial para tracking
        """
        try:
            # Leer historial existente
            if os.path.exists(self.archivo_historial):
                with open(self.archivo_historial, 'r', encoding='utf-8') as f:
                    historial = json.load(f)
            else:
                historial = []

            # Agregar nuevo análisis
            historial.append(analisis)

            # Guardar
            with open(self.archivo_historial, 'w', encoding='utf-8') as f:
                json.dump(historial, f, indent=2, ensure_ascii=False)

            print(f"\n✅ Historial actualizado: {self.archivo_historial}")

        except Exception as e:
            print(f"❌ Error al guardar historial: {e}")

    def aplicar_mejoras(self, analisis, auto=False):
        """
        Aplica las mejoras sugeridas al SYSTEM_PROMPT

        Args:
            analisis: Resultado del análisis semanal
            auto: Si es True, aplica automáticamente sin confirmación
        """
        if not analisis or 'analisis' not in analisis:
            print("❌ No hay análisis para aplicar")
            return

        modificaciones = analisis['analisis'].get('modificaciones_prompt', [])

        if not modificaciones:
            print("ℹ️ No hay modificaciones sugeridas para el prompt")
            return

        print("\n" + "=" * 60)
        print("🔧 APLICACIÓN DE MEJORAS AL SYSTEM_PROMPT")
        print("=" * 60)

        print("\nModificaciones sugeridas:")
        for i, mod in enumerate(modificaciones, 1):
            print(f"\n{i}. Sección: {mod['seccion']}")
            print(f"   Cambio: {mod['cambio']}")

        if not auto:
            confirmar = input("\n¿Deseas aplicar estas mejoras? (s/n): ").strip().lower()
            if confirmar != 's':
                print("❌ Mejoras canceladas")
                return

        print("\n⚠️ NOTA: Las mejoras se guardan en el historial.")
        print("   Para aplicarlas manualmente, revisa el archivo:")
        print(f"   {self.archivo_historial}")
        print("\n   Y actualiza el SYSTEM_PROMPT en agente_ventas.py")

        # Guardar en historial
        self.guardar_historial(analisis)

        print("\n✅ Proceso completado")


def ejecutar_analisis_semanal():
    """
    Función principal para ejecutar el análisis semanal
    """
    auto_mejora = AutoMejoraBruce()

    # Analizar semana
    analisis = auto_mejora.analizar_semana()

    if analisis:
        # Guardar en historial
        auto_mejora.guardar_historial(analisis)

        # Preguntar si aplicar mejoras
        auto_mejora.aplicar_mejoras(analisis, auto=False)


if __name__ == "__main__":
    print("\n🤖 SISTEMA DE AUTO-MEJORA CONTINUA - BRUCE W")
    ejecutar_analisis_semanal()
