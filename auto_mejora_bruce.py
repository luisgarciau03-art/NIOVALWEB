"""
FIX 387: Meta-Aprendizaje Automático para Bruce W
Sistema de Auto-Mejora Continua que analiza el desempeño semanal,
identifica patrones de éxito/fracaso, y optimiza el SYSTEM_PROMPT automáticamente

Características FIX 387:
- Análisis de objeciones frecuentes no manejadas
- Detección de frases más efectivas en llamadas exitosas
- Identificación de problemas recurrentes
- Recomendaciones basadas en tasa de éxito (>80% = óptimo)
- Auto-actualización de prompt si efectividad > 80%
"""

import os
import json
import re
from datetime import datetime, timedelta
from collections import Counter, defaultdict
from typing import Dict, List, Tuple
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
    FIX 387: Sistema de meta-aprendizaje automático
    Analiza las llamadas de la última semana y genera recomendaciones
    basadas en patrones de éxito/fracaso para optimizar el SYSTEM_PROMPT
    """

    def __init__(self):
        self.resultados_adapter = ResultadosSheetsAdapter()
        self.archivo_prompt = "agente_ventas.py"
        self.archivo_historial = "historial_mejoras_bruce.json"

        # FIX 387: Umbrales de meta-aprendizaje
        self.umbral_auto_update = 0.80  # 80% tasa de éxito para auto-update
        self.min_llamadas_confiable = 20  # Mínimo de llamadas para análisis confiable

        # FIX 387: Contadores de patrones
        self.objeciones_frecuentes = Counter()
        self.frases_efectivas = Counter()
        self.problemas_detectados = []

    def analizar_semana(self):
        """
        FIX 387: Analiza todas las llamadas de la última semana con meta-aprendizaje
        Incluye análisis de objeciones, frases efectivas y problemas recurrentes
        """
        print("\n" + "=" * 60)
        print("🧠 FIX 387: META-APRENDIZAJE AUTOMÁTICO - BRUCE W")
        print("=" * 60)

        try:
            # Obtener estadísticas de la última semana
            stats = self._obtener_estadisticas_semana()

            if not stats:
                print("❌ No hay datos suficientes para analizar")
                return None

            # FIX 387: Verificar mínimo de llamadas para análisis confiable
            if stats['total_llamadas'] < self.min_llamadas_confiable:
                print(f"\n⚠️  Solo {stats['total_llamadas']} llamadas analizadas.")
                print(f"   Mínimo recomendado: {self.min_llamadas_confiable} para análisis confiable")
                print("   Continuando con análisis limitado...\n")

            print(f"\n📊 Datos de la última semana:")
            print(f"   Total de llamadas: {stats['total_llamadas']}")
            print(f"   Tasa de conversión: {stats['tasa_conversion']:.1f}%")
            print(f"   WhatsApps capturados: {stats['whatsapps_capturados']}")
            print(f"   Nivel de interés promedio: {stats['interes_promedio']}")
            print(f"   Estado de ánimo predominante: {stats['animo_predominante']}")

            # FIX 387: Obtener todas las filas para análisis avanzado
            todas_filas = self.resultados_adapter.hoja_resultados.get_all_values()

            # FIX 387: Analizar objeciones frecuentes
            self._analizar_objeciones_frecuentes(todas_filas)

            # FIX 387: Analizar frases efectivas
            self._analizar_frases_efectivas(todas_filas)

            # FIX 387: Detectar problemas recurrentes
            self._detectar_problemas_recurrentes(stats)

            # FIX 387: Agregar datos de meta-aprendizaje a stats
            stats['objeciones_top'] = self.objeciones_frecuentes.most_common(5)
            stats['frases_efectivas_top'] = self.frases_efectivas.most_common(5)
            stats['problemas_detectados'] = self.problemas_detectados

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

                # FIX 387: Verificar si se requiere auto-actualización
                print("\n" + "=" * 60)
                if stats['tasa_conversion'] >= self.umbral_auto_update * 100:
                    print(f"✅ FIX 387: TASA DE ÉXITO ≥ {self.umbral_auto_update*100:.0f}%")
                    print("   Sistema funcionando ÓPTIMAMENTE - No se requieren cambios automáticos")
                else:
                    print(f"⚠️  FIX 387: TASA DE ÉXITO < {self.umbral_auto_update*100:.0f}%")
                    print("   Revisar recomendaciones manualmente y actualizar prompt")
                print("=" * 60)

                return {
                    'stats': stats,
                    'analisis': analisis_gpt,
                    'fecha': datetime.now().strftime("%Y-%m-%d"),
                    'auto_update': stats['tasa_conversion'] >= self.umbral_auto_update * 100
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

    def _analizar_objeciones_frecuentes(self, todas_filas):
        """
        FIX 387: Analiza objeciones frecuentes en llamadas fallidas
        Busca patrones comunes en la columna de notas/transcripción
        """
        print("\n🔍 FIX 387: Analizando objeciones frecuentes...")

        patrones_objecion = {
            'ya_tengo_proveedor': r'ya\s+tengo\s+proveedor|tengo\s+proveedor\s+fijo',
            'es_muy_caro': r'es\s+muy\s+caro|está\s+caro|sus\s+precios\s+son\s+altos',
            'no_tengo_presupuesto': r'no\s+tengo\s+presupuesto|ahorita\s+no\s+tengo\s+dinero',
            'no_me_interesa': r'no\s+me\s+interesa|no\s+necesito\s+nada',
            'estoy_ocupado': r'estoy\s+ocupado|no\s+tengo\s+tiempo',
            'mi_jefe_decide': r'mi\s+jefe\s+decide|tengo\s+que\s+consultar',
            'solo_efectivo': r'solo\s+(?:compro|pago)\s+en\s+efectivo'
        }

        # Iterar filas para encontrar objeciones
        for fila in todas_filas[1:]:  # Saltar header
            if len(fila) < 19:
                continue

            # Columna S: Resultado
            resultado = fila[18] if len(fila) > 18 else ""

            # Solo analizar llamadas NO aprobadas
            if resultado == "APROBADO":
                continue

            # Columna T: Notas/Observaciones (si existe)
            notas = fila[19] if len(fila) > 19 else ""

            # Buscar objeciones
            for tipo_objecion, patron in patrones_objecion.items():
                if re.search(patron, notas, re.IGNORECASE):
                    self.objeciones_frecuentes[tipo_objecion] += 1

        if self.objeciones_frecuentes:
            print("   Top 5 objeciones:")
            for objecion, count in self.objeciones_frecuentes.most_common(5):
                print(f"   • {objecion.replace('_', ' ').title()}: {count}x")

    def _analizar_frases_efectivas(self, todas_filas):
        """
        FIX 387: Identifica frases/patrones en llamadas exitosas
        """
        print("\n💡 FIX 387: Identificando frases efectivas...")

        # Patrones de frases que Bruce usa frecuentemente
        patrones_frases = {
            'oferta_catalogo': r'le\s+envío\s+el\s+catálogo',
            'pregunta_whatsapp': r'cuál\s+es\s+su\s+whatsapp',
            'mencion_promocion': r'primer\s+pedido.*envío\s+gratis|envío\s+gratis',
            'pregunta_encargado': r'(?:puedo|me\s+comunica).*encargado\s+de\s+compras',
            'mencion_griferia': r'grifería|griferías|llaves',
            'mencion_cintas': r'cinta\s+para\s+goteras|cintas'
        }

        # Analizar solo llamadas APROBADAS
        for fila in todas_filas[1:]:
            if len(fila) < 19:
                continue

            resultado = fila[18] if len(fila) > 18 else ""

            # Solo llamadas exitosas
            if resultado != "APROBADO":
                continue

            notas = fila[19] if len(fila) > 19 else ""

            # Buscar frases efectivas
            for tipo_frase, patron in patrones_frases.items():
                if re.search(patron, notas, re.IGNORECASE):
                    self.frases_efectivas[tipo_frase] += 1

        if self.frases_efectivas:
            print("   Top 5 frases efectivas:")
            for frase, count in self.frases_efectivas.most_common(5):
                print(f"   • {frase.replace('_', ' ').title()}: {count}x")

    def _detectar_problemas_recurrentes(self, stats):
        """
        FIX 387: Detecta problemas recurrentes basados en métricas
        """
        print("\n⚠️  FIX 387: Detectando problemas recurrentes...")

        # Problema 1: Tasa de conversión muy baja
        if stats['tasa_conversion'] < 20:
            self.problemas_detectados.append(
                f"Tasa de conversión muy baja ({stats['tasa_conversion']:.1f}%). "
                "Revisar script de apertura y manejo de objeciones."
            )

        # Problema 2: Objeción "ya tengo proveedor" muy frecuente
        if self.objeciones_frecuentes.get('ya_tengo_proveedor', 0) > stats['total_llamadas'] * 0.3:
            self.problemas_detectados.append(
                "Objeción 'ya tengo proveedor' muy frecuente (30%+). "
                "Mejorar diferenciación de valor en FIX 388 (Negociación)."
            )

        # Problema 3: Estado de ánimo predominantemente negativo
        if stats['animo_predominante'] in ['Molesto', 'Enojado', 'Muy Negativo']:
            self.problemas_detectados.append(
                f"Estado de ánimo predominante: {stats['animo_predominante']}. "
                "Revisar tono y empatía en respuestas. Considerar FIX 386 (Sentimiento)."
            )

        # Problema 4: Nivel de interés bajo
        if stats['interes_promedio'] == 'Bajo':
            self.problemas_detectados.append(
                "Nivel de interés promedio bajo. "
                "Enfatizar beneficios concretos (envío gratis, promoción) más temprano."
            )

        # Problema 5: Muchas llamadas pero pocas conversiones (ratio 10:1 o peor)
        if stats['total_llamadas'] >= 100 and stats['tasa_conversion'] < 10:
            self.problemas_detectados.append(
                f"{stats['total_llamadas']} llamadas con solo {stats['tasa_conversion']:.1f}% conversión. "
                "Problema de calidad de leads o script inefectivo. Revisar targeting."
            )

        if self.problemas_detectados:
            for i, problema in enumerate(self.problemas_detectados, 1):
                print(f"   {i}. {problema}")
        else:
            print("   ✅ No se detectaron problemas críticos")

    def _analizar_con_gpt(self, stats):
        """
        FIX 387: Usa GPT-4o-mini para analizar estadísticas con meta-aprendizaje
        Incluye objeciones frecuentes, frases efectivas y problemas detectados
        """
        try:
            # FIX 387: Construir sección de objeciones
            objeciones_texto = "Sin datos suficientes"
            if stats.get('objeciones_top'):
                objeciones_texto = "\n".join([
                    f"  • {obj.replace('_', ' ').title()}: {count}x"
                    for obj, count in stats['objeciones_top']
                ])

            # FIX 387: Construir sección de frases efectivas
            frases_texto = "Sin datos suficientes"
            if stats.get('frases_efectivas_top'):
                frases_texto = "\n".join([
                    f"  • {frase.replace('_', ' ').title()}: {count}x"
                    for frase, count in stats['frases_efectivas_top']
                ])

            # FIX 387: Construir sección de problemas
            problemas_texto = "✅ No se detectaron problemas críticos"
            if stats.get('problemas_detectados'):
                problemas_texto = "\n".join([
                    f"  {i}. {problema}"
                    for i, problema in enumerate(stats['problemas_detectados'], 1)
                ])

            prompt = f"""Eres un experto en optimización de scripts de ventas telefónicas. Analiza estas métricas de Bruce W (agente de ventas de NIOVAL) con FIX 387: META-APRENDIZAJE AUTOMÁTICO y genera cambios ESPECÍFICOS Y TEXTUALES para el SYSTEM_PROMPT.

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

🔍 FIX 387: OBJECIONES MÁS FRECUENTES (en llamadas fallidas):
{objeciones_texto}

💡 FIX 387: FRASES MÁS EFECTIVAS (en llamadas exitosas):
{frases_texto}

⚠️ FIX 387: PROBLEMAS RECURRENTES DETECTADOS:
{problemas_texto}

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
