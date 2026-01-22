"""
FIX 404: Análisis Masivo de Manejo del Encargado de Compras

Analiza logs de múltiples llamadas para detectar:
1. Cliente dice "no está" / "no se encuentra" → Bruce NO debería ofrecer catálogo inmediatamente
2. Cliente dice "habla con él/ella" → Bruce debería entender que YA habla con encargado
3. Cliente pregunta "¿de dónde habla?" → Bruce DEBE responder empresa antes de seguir
4. Cliente dice "no" simple → Bruce debe entender contexto (encargado no disponible)

Fecha: 2026-01-21
"""

import re
import json
from datetime import datetime
from collections import defaultdict


class AnalizadorEncargado:
    """Analiza logs para detectar errores en manejo de encargado de compras"""

    def __init__(self):
        # Patrones problemáticos a detectar
        self.patrones_cliente_dice_no_esta = [
            r'no\s+est[aá]',
            r'no\s+se\s+encuentra',
            r'no\s+se\s+encuentra\s+ahorita',
            r'sali[oó]\s+a\s+comer',
            r'no\s+est[aá]\s+ahorita',
            r'no\s+est[aá]\s+en\s+este\s+momento',
            r'est[aá]\s+ocupad[oa]',
            r'no\s+puede\s+atender'
        ]

        self.patrones_cliente_dice_habla_con_encargado = [
            r'con\s+[eé]l\s+habl[oa]',
            r'con\s+ella\s+habl[oa]',
            r'yo\s+soy\s+el\s+encargado',
            r'yo\s+soy\s+la\s+encargada',
            r's[ií],\s+yo\s+soy',
            r's[ií],\s+dime',
            r's[ií],\s+d[ií]game',
            r'yo\s+le\s+atiendo',
            r'yo\s+me\s+encargo'
        ]

        self.patrones_cliente_pregunta_de_donde = [
            r'¿de\s+d[oó]nde\s+habl',
            r'¿de\s+d[oó]nde\s+me\s+habl',
            r'de\s+d[oó]nde\s+dic',
            r'¿qu[eé]\s+empresa',
            r'¿qui[eé]n\s+habl',
            r'¿c[oó]mo\s+dijo',
            r'¿me\s+repite'
        ]

        self.patrones_cliente_dice_no_simple = [
            r'^no\.?$',
            r'^nope\.?$',
            r'^nel\.?$',
            r'^no,?\s+gracias\.?$'
        ]

        # Respuestas incorrectas de Bruce
        self.patrones_bruce_ofrece_catalogo = [
            r'le\s+env[ií]o\s+el\s+cat[aá]logo',
            r'le\s+mando\s+el\s+cat[aá]logo',
            r'le\s+comparto\s+el\s+cat[aá]logo',
            r'¿le\s+gustar[ií]a\s+que\s+le\s+env[ií]',
            r'¿le\s+parece\s+bien\s+que\s+le\s+env[ií]',
            r'le\s+llegar[aá]\s+el\s+cat[aá]logo'
        ]

        self.patrones_bruce_no_menciona_empresa = [
            # Bruce NO mencionó NIOVAL/empresa en su respuesta
            r'^(?!.*nioval)(?!.*marca)(?!.*me\s+comunico\s+de).*$'
        ]

        self.patrones_bruce_insiste_encargado = [
            r'¿se\s+encontrar[aá]\s+el\s+encargado',
            r'¿me\s+comunica\s+con\s+el\s+encargado',
            r'¿puede\s+pasar\s+con\s+el\s+encargado'
        ]

        # Estadísticas
        self.errores_detectados = []
        self.llamadas_analizadas = 0
        self.llamadas_con_errores = 0

    def extraer_conversacion(self, log_text):
        """
        Extrae turnos de conversación del log

        Returns:
            List[dict]: [{"timestamp": "...", "speaker": "Bruce/Cliente", "text": "..."}]
        """
        turnos = []

        # Patrón para detectar mensajes de Bruce y Cliente
        # Formato: [HH:MM:SS] Bruce: "texto" o [HH:MM:SS] Cliente: "texto"
        patron_turno = r'\[(\d{2}:\d{2}:\d{2})\]\s+(Bruce|Cliente):\s+"?([^"\n]+)"?'

        matches = re.finditer(patron_turno, log_text, re.IGNORECASE | re.MULTILINE)

        for match in matches:
            timestamp, speaker, text = match.groups()
            turnos.append({
                "timestamp": timestamp,
                "speaker": speaker.capitalize(),
                "text": text.strip()
            })

        return turnos

    def detectar_errores_en_conversacion(self, turnos, bruce_id=""):
        """
        Analiza una conversación completa buscando errores

        Returns:
            List[dict]: Errores detectados
        """
        errores = []

        for i, turno in enumerate(turnos):
            if turno["speaker"] == "Cliente":
                cliente_msg = turno["text"].lower()

                # Obtener respuesta de Bruce (siguiente turno)
                bruce_msg = ""
                bruce_timestamp = ""
                if i + 1 < len(turnos) and turnos[i + 1]["speaker"] == "Bruce":
                    bruce_msg = turnos[i + 1]["text"].lower()
                    bruce_timestamp = turnos[i + 1]["timestamp"]

                # ERROR 1: Cliente dice "no está" → Bruce ofrece catálogo inmediatamente
                if any(re.search(patron, cliente_msg) for patron in self.patrones_cliente_dice_no_esta):
                    if bruce_msg and any(re.search(patron, bruce_msg) for patron in self.patrones_bruce_ofrece_catalogo):
                        errores.append({
                            "tipo": "OFRECE_CATALOGO_CUANDO_NO_ESTA",
                            "timestamp": turno["timestamp"],
                            "cliente_dijo": turno["text"],
                            "bruce_respondio": turnos[i + 1]["text"] if i + 1 < len(turnos) else "",
                            "bruce_id": bruce_id,
                            "severidad": "ALTA",
                            "descripcion": "Cliente dijo que encargado NO está, pero Bruce ofreció catálogo sin alternativa"
                        })

                # ERROR 2: Cliente pregunta "¿de dónde habla?" → Bruce NO menciona empresa
                if any(re.search(patron, cliente_msg) for patron in self.patrones_cliente_pregunta_de_donde):
                    if bruce_msg:
                        menciona_empresa = any(palabra in bruce_msg for palabra in ['nioval', 'marca', 'me comunico de'])
                        if not menciona_empresa:
                            errores.append({
                                "tipo": "NO_RESPONDE_DE_DONDE_HABLA",
                                "timestamp": turno["timestamp"],
                                "cliente_dijo": turno["text"],
                                "bruce_respondio": turnos[i + 1]["text"] if i + 1 < len(turnos) else "",
                                "bruce_id": bruce_id,
                                "severidad": "ALTA",
                                "descripcion": "Cliente preguntó de dónde habla pero Bruce NO mencionó NIOVAL"
                            })

                # ERROR 3: Cliente dice "con él/ella habla" → Bruce sigue preguntando por encargado
                if any(re.search(patron, cliente_msg) for patron in self.patrones_cliente_dice_habla_con_encargado):
                    if bruce_msg and any(re.search(patron, bruce_msg) for patron in self.patrones_bruce_insiste_encargado):
                        errores.append({
                            "tipo": "INSISTE_ENCARGADO_CUANDO_YA_HABLA_CON_EL",
                            "timestamp": turno["timestamp"],
                            "cliente_dijo": turno["text"],
                            "bruce_respondio": turnos[i + 1]["text"] if i + 1 < len(turnos) else "",
                            "bruce_id": bruce_id,
                            "severidad": "ALTA",
                            "descripcion": "Cliente dijo que YA habla con encargado pero Bruce siguió preguntando"
                        })

                # ERROR 4: Cliente dice "No" simple después de pregunta por encargado → Bruce insiste
                if any(re.search(patron, cliente_msg) for patron in self.patrones_cliente_dice_no_simple):
                    # Verificar si Bruce preguntó por encargado en los últimos 2 turnos
                    pregunto_encargado = False
                    if i >= 2:
                        for j in range(max(0, i - 2), i):
                            if turnos[j]["speaker"] == "Bruce":
                                if any(re.search(patron, turnos[j]["text"].lower()) for patron in self.patrones_bruce_insiste_encargado):
                                    pregunto_encargado = True
                                    break

                    if pregunto_encargado:
                        if bruce_msg and any(re.search(patron, bruce_msg) for patron in self.patrones_bruce_insiste_encargado):
                            errores.append({
                                "tipo": "INSISTE_DESPUES_DE_NO_SIMPLE",
                                "timestamp": turno["timestamp"],
                                "cliente_dijo": turno["text"],
                                "bruce_respondio": turnos[i + 1]["text"] if i + 1 < len(turnos) else "",
                                "bruce_id": bruce_id,
                                "severidad": "MEDIA",
                                "descripcion": "Cliente dijo 'No' simple pero Bruce insistió en preguntar por encargado"
                            })

        return errores

    def analizar_archivo_log(self, ruta_archivo):
        """
        Analiza un archivo de log completo que puede contener múltiples llamadas

        Args:
            ruta_archivo: Path al archivo .log o .txt

        Returns:
            dict: Resumen del análisis
        """
        print(f"\n📂 Analizando archivo: {ruta_archivo}")

        with open(ruta_archivo, 'r', encoding='utf-8') as f:
            contenido = f.read()

        # Detectar separaciones de llamadas (BRUCE ID)
        # Formato: "BRUCE1134", "BRUCE1135", etc.
        patron_bruce_id = r'(BRUCE\d+)'
        llamadas_separadas = re.split(patron_bruce_id, contenido)

        # Si no hay separación por BRUCE ID, analizar como una sola llamada
        if len(llamadas_separadas) <= 1:
            turnos = self.extraer_conversacion(contenido)
            errores = self.detectar_errores_en_conversacion(turnos, "UNKNOWN")
            self.errores_detectados.extend(errores)
            self.llamadas_analizadas = 1
            if errores:
                self.llamadas_con_errores = 1
        else:
            # Analizar cada llamada por separado
            for i in range(1, len(llamadas_separadas), 2):
                bruce_id = llamadas_separadas[i]
                log_llamada = llamadas_separadas[i + 1] if i + 1 < len(llamadas_separadas) else ""

                if log_llamada.strip():
                    print(f"\n  🔍 Analizando {bruce_id}...")
                    turnos = self.extraer_conversacion(log_llamada)

                    if turnos:
                        self.llamadas_analizadas += 1
                        errores = self.detectar_errores_en_conversacion(turnos, bruce_id)

                        if errores:
                            self.llamadas_con_errores += 1
                            self.errores_detectados.extend(errores)
                            print(f"    ❌ {len(errores)} errores detectados")
                        else:
                            print(f"    ✅ Sin errores")

        return self.generar_resumen()

    def generar_resumen(self):
        """Genera resumen del análisis"""
        resumen = {
            "llamadas_analizadas": self.llamadas_analizadas,
            "llamadas_con_errores": self.llamadas_con_errores,
            "llamadas_sin_errores": self.llamadas_analizadas - self.llamadas_con_errores,
            "total_errores": len(self.errores_detectados),
            "errores_por_tipo": defaultdict(int),
            "errores_por_severidad": defaultdict(int),
            "errores_detallados": self.errores_detectados
        }

        # Contar por tipo y severidad
        for error in self.errores_detectados:
            resumen["errores_por_tipo"][error["tipo"]] += 1
            resumen["errores_por_severidad"][error["severidad"]] += 1

        return resumen

    def imprimir_resumen(self, resumen):
        """Imprime resumen en consola de forma legible"""
        print("\n" + "=" * 100)
        print("📊 RESUMEN DEL ANÁLISIS MASIVO - MANEJO DE ENCARGADO DE COMPRAS")
        print("=" * 100)

        print(f"\n📞 Llamadas analizadas: {resumen['llamadas_analizadas']}")
        print(f"   ✅ Sin errores: {resumen['llamadas_sin_errores']} ({resumen['llamadas_sin_errores']/resumen['llamadas_analizadas']*100:.1f}%)")
        print(f"   ❌ Con errores: {resumen['llamadas_con_errores']} ({resumen['llamadas_con_errores']/resumen['llamadas_analizadas']*100:.1f}%)")

        print(f"\n🚨 Total de errores detectados: {resumen['total_errores']}")

        print("\n📋 Errores por severidad:")
        for severidad, cantidad in sorted(resumen['errores_por_severidad'].items(), reverse=True):
            print(f"   {severidad}: {cantidad}")

        print("\n📋 Errores por tipo:")
        for tipo, cantidad in sorted(resumen['errores_por_tipo'].items(), key=lambda x: x[1], reverse=True):
            tipo_legible = tipo.replace("_", " ").title()
            print(f"   {tipo_legible}: {cantidad}")

        # Detallar errores
        if resumen['errores_detallados']:
            print("\n" + "=" * 100)
            print("🔍 ERRORES DETALLADOS")
            print("=" * 100)

            for i, error in enumerate(resumen['errores_detallados'], 1):
                print(f"\n❌ ERROR {i}/{len(resumen['errores_detallados'])} - {error['tipo']}")
                print(f"   BRUCE ID: {error['bruce_id']}")
                print(f"   Timestamp: {error['timestamp']}")
                print(f"   Severidad: {error['severidad']}")
                print(f"   Descripción: {error['descripcion']}")
                print(f"   Cliente dijo: \"{error['cliente_dijo']}\"")
                print(f"   Bruce respondió: \"{error['bruce_respondio']}\"")

        print("\n" + "=" * 100)

    def guardar_resultados_json(self, resumen, ruta_salida="analisis_encargado_resultados.json"):
        """Guarda resultados en JSON para análisis posterior"""
        with open(ruta_salida, 'w', encoding='utf-8') as f:
            json.dump(resumen, f, ensure_ascii=False, indent=2)

        print(f"\n💾 Resultados guardados en: {ruta_salida}")


def main():
    """Función principal"""
    import sys

    print("=" * 100)
    print("🔍 ANALIZADOR MASIVO DE MANEJO DE ENCARGADO DE COMPRAS - FIX 404")
    print("=" * 100)

    if len(sys.argv) < 2:
        print("\n❌ Error: Debes proporcionar la ruta al archivo de logs")
        print("\nUso:")
        print(f"   python {sys.argv[0]} <ruta_archivo_logs.txt>")
        print("\nEjemplo:")
        print(f"   python {sys.argv[0]} logs_completos.txt")
        print(f"   python {sys.argv[0]} C:\\Users\\PC 1\\Downloads\\logs_bruce.log")
        return

    ruta_archivo = sys.argv[1]

    # Crear analizador
    analizador = AnalizadorEncargado()

    # Analizar archivo
    try:
        resumen = analizador.analizar_archivo_log(ruta_archivo)

        # Imprimir resumen
        analizador.imprimir_resumen(resumen)

        # Guardar resultados
        analizador.guardar_resultados_json(resumen)

        # Conclusión
        print("\n✅ Análisis completado")

        if resumen['llamadas_con_errores'] > 0:
            tasa_error = resumen['llamadas_con_errores'] / resumen['llamadas_analizadas'] * 100
            print(f"\n⚠️  Tasa de error: {tasa_error:.1f}%")

            if tasa_error > 30:
                print("   🚨 CRÍTICO: Más del 30% de llamadas tienen errores")
            elif tasa_error > 15:
                print("   ⚠️  ALTO: Más del 15% de llamadas tienen errores")
            else:
                print("   ℹ️  Tasa de error aceptable pero mejorable")
        else:
            print("\n🎉 ¡Excelente! No se detectaron errores")

    except FileNotFoundError:
        print(f"\n❌ Error: No se encontró el archivo '{ruta_archivo}'")
    except Exception as e:
        print(f"\n❌ Error durante el análisis: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
