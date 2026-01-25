"""
FIX 404 (VERSIÓN HÍBRIDA): Análisis de Manejo del Encargado
Correlaciona logs de Railway (cliente) + Google Sheets (resultados)

LIMITACIÓN: No tenemos respuestas de Bruce guardadas en logs.
SOLUCIÓN: Inferir errores basándose en:
  - Lo que dijo el cliente (logs)
  - El resultado final (Sheets: APROBADO/NEGADO)

Fecha: 2026-01-24
"""

import re
from collections import defaultdict
from datetime import datetime, timedelta
from resultados_sheets_adapter import ResultadosSheetsAdapter


class AnalizadorEncargadoHibrido:
    """
    Analiza errores en manejo de encargado correlacionando:
    - Transcripciones del cliente (logs Railway)
    - Resultados finales (Google Sheets)
    """

    def __init__(self):
        self.sheets_adapter = ResultadosSheetsAdapter()

        # Patrones problemáticos del cliente
        self.patrones_no_esta = [
            r'no\s+est[aá]',
            r'no\s+se\s+encuentra',
            r'sali[oó]\s+a\s+comer',
            r'est[aá]\s+ocupad[oa]',
            r'no\s+puede\s+atender'
        ]

        self.patrones_pregunta_empresa = [
            r'¿de\s+d[oó]nde\s+habl',
            r'¿qu[eé]\s+empresa',
            r'¿qui[eé]n\s+habl',
            r'de\s+d[oó]nde\s+me\s+habl'
        ]

        self.patrones_ya_soy_encargado = [
            r'con\s+[eé]l\s+habl',
            r'yo\s+soy\s+el\s+encargado',
            r's[ií],\s+yo\s+soy',
            r'yo\s+le\s+atiendo'
        ]

        # Estadísticas
        self.errores_detectados = []
        self.llamadas_analizadas = 0

    def extraer_transcripciones_cliente(self, log_text, bruce_id):
        """
        Extrae SOLO las transcripciones del cliente desde logs de Railway
        Formato: [YYYY-MM-DD HH:MM:SS] [CLIENTE] BRUCE1288 - CLIENTE DIJO: "texto"
        """
        transcripciones = []

        # Patrón para líneas del cliente
        patron_cliente = r'\[([^\]]+)\]\s+\[CLIENTE\]\s+(' + bruce_id + r')\s+-\s+CLIENTE DIJO:\s+"([^"]+)"'

        matches = re.finditer(patron_cliente, log_text, re.IGNORECASE)

        for match in matches:
            timestamp, bid, texto = match.groups()
            transcripciones.append({
                "timestamp": timestamp,
                "bruce_id": bid,
                "texto": texto.strip()
            })

        return transcripciones

    def obtener_resultado_sheets(self, bruce_id):
        """
        Busca el resultado en Google Sheets para un BRUCE_ID específico
        Columna Z (26): ID Llamada (formato BRUCE1288)
        Columna S (19): Resultado (APROBADO/NEGADO)
        """
        try:
            # Obtener todas las filas
            todas_filas = self.sheets_adapter.hoja_resultados.get_all_values()

            # Buscar fila con este BRUCE_ID
            for i, fila in enumerate(todas_filas[1:], 2):  # Saltar header
                if len(fila) < 26:
                    continue

                # Columna Z (índice 25): ID Llamada
                id_llamada = fila[25] if len(fila) > 25 else ""

                if id_llamada == bruce_id:
                    # Encontrado
                    resultado = fila[18] if len(fila) > 18 else ""  # Columna S
                    compatible = fila[18] if len(fila) > 18 else ""  # Columna S (Compatible)
                    tiempo = fila[20] if len(fila) > 20 else ""  # Columna U (Tiempo)
                    interes = fila[21] if len(fila) > 21 else ""  # Columna V (Interés)
                    animo = fila[22] if len(fila) > 22 else ""  # Columna W (Ánimo)

                    return {
                        'encontrado': True,
                        'fila': i,
                        'resultado': resultado,
                        'compatible': compatible,
                        'tiempo': tiempo,
                        'interes': interes,
                        'animo': animo
                    }

            return {'encontrado': False}

        except Exception as e:
            print(f"  Error al buscar {bruce_id} en Sheets: {e}")
            return {'encontrado': False}

    def analizar_llamada(self, bruce_id, transcripciones, resultado_sheets):
        """
        Analiza una llamada específica buscando errores en manejo de encargado

        Lógica de inferencia:
        1. Cliente dice "no está" + Resultado NEGADO = Probablemente Bruce insistió mal
        2. Cliente pregunta "¿de dónde habla?" + Resultado NEGADO = No mencionó empresa
        3. Cliente dice "yo soy el encargado" + Tiempo > 2min = No entendió rápido
        """
        errores = []

        # Concatenar todos los mensajes del cliente
        mensajes_cliente = " ".join([t['texto'] for t in transcripciones]).lower()

        # ERROR 1: Cliente dice "no está" pero resultado NEGADO
        if any(re.search(patron, mensajes_cliente) for patron in self.patrones_no_esta):
            if resultado_sheets.get('resultado') == 'NEGADO':
                errores.append({
                    'tipo': 'OFRECE_CATALOGO_CUANDO_NO_ESTA',
                    'bruce_id': bruce_id,
                    'severidad': 'ALTA',
                    'descripcion': 'Cliente dijo que encargado NO está -> Resultado NEGADO (probablemente Bruce no ofreció alternativa efectiva)',
                    'evidencia_cliente': [t['texto'] for t in transcripciones if any(re.search(p, t['texto'].lower()) for p in self.patrones_no_esta)],
                    'resultado_final': resultado_sheets.get('resultado')
                })

        # ERROR 2: Cliente pregunta "¿de dónde habla?" pero resultado NEGADO
        if any(re.search(patron, mensajes_cliente) for patron in self.patrones_pregunta_empresa):
            if resultado_sheets.get('resultado') == 'NEGADO':
                errores.append({
                    'tipo': 'NO_RESPONDE_DE_DONDE_HABLA',
                    'bruce_id': bruce_id,
                    'severidad': 'ALTA',
                    'descripcion': 'Cliente preguntó de dónde habla -> Resultado NEGADO (probablemente Bruce no mencionó NIOVAL claramente)',
                    'evidencia_cliente': [t['texto'] for t in transcripciones if any(re.search(p, t['texto'].lower()) for p in self.patrones_pregunta_empresa)],
                    'resultado_final': resultado_sheets.get('resultado')
                })

        # ERROR 3: Cliente dice "yo soy el encargado" pero tiempo > 2 min
        if any(re.search(patron, mensajes_cliente) for patron in self.patrones_ya_soy_encargado):
            tiempo_str = resultado_sheets.get('tiempo', '')
            try:
                # Formato esperado: "3:45" (minutos:segundos)
                if ':' in tiempo_str:
                    partes = tiempo_str.split(':')
                    minutos = int(partes[0])
                    if minutos > 2:
                        errores.append({
                            'tipo': 'INSISTE_ENCARGADO_CUANDO_YA_HABLA_CON_EL',
                            'bruce_id': bruce_id,
                            'severidad': 'MEDIA',
                            'descripcion': f'Cliente dijo que YA es encargado pero llamada duró {tiempo_str} (probablemente Bruce siguió preguntando)',
                            'evidencia_cliente': [t['texto'] for t in transcripciones if any(re.search(p, t['texto'].lower()) for p in self.patrones_ya_soy_encargado)],
                            'tiempo_llamada': tiempo_str
                        })
            except Exception:
                pass

        return errores

    def analizar_logs(self, ruta_log):
        """
        Analiza archivo de logs de Railway y correlaciona con Google Sheets
        """
        print(f"\n Analizando archivo: {ruta_log}")

        with open(ruta_log, 'r', encoding='utf-8') as f:
            contenido = f.read()

        # Separar por BRUCE ID
        patron_bruce_id = r'BRUCE\d+'
        bruce_ids_encontrados = list(set(re.findall(patron_bruce_id, contenido)))

        print(f" Encontrados {len(bruce_ids_encontrados)} BRUCE IDs únicos\n")

        for bruce_id in sorted(bruce_ids_encontrados):
            print(f"   Analizando {bruce_id}...", end="")

            # Extraer transcripciones del cliente
            transcripciones = self.extraer_transcripciones_cliente(contenido, bruce_id)

            if not transcripciones:
                print(" [Sin transcripciones]")
                continue

            # Obtener resultado de Sheets
            resultado_sheets = self.obtener_resultado_sheets(bruce_id)

            if not resultado_sheets['encontrado']:
                print(f" [No en Sheets]")
                continue

            self.llamadas_analizadas += 1

            # Analizar errores
            errores = self.analizar_llamada(bruce_id, transcripciones, resultado_sheets)

            if errores:
                self.errores_detectados.extend(errores)
                print(f" [{len(errores)} errores]")
            else:
                print(" [OK]")

        return self.generar_resumen()

    def generar_resumen(self):
        """Genera resumen del análisis"""
        resumen = {
            'llamadas_analizadas': self.llamadas_analizadas,
            'llamadas_con_errores': len(set(e['bruce_id'] for e in self.errores_detectados)),
            'llamadas_sin_errores': self.llamadas_analizadas - len(set(e['bruce_id'] for e in self.errores_detectados)),
            'total_errores': len(self.errores_detectados),
            'errores_por_tipo': defaultdict(int),
            'errores_por_severidad': defaultdict(int),
            'errores_detallados': self.errores_detectados
        }

        # Contar por tipo y severidad
        for error in self.errores_detectados:
            resumen['errores_por_tipo'][error['tipo']] += 1
            resumen['errores_por_severidad'][error['severidad']] += 1

        return resumen

    def imprimir_resumen(self, resumen):
        """Imprime resumen en consola"""
        print("\n" + "=" * 100)
        print(" RESUMEN - ANÁLISIS HÍBRIDO DE MANEJO DE ENCARGADO (FIX 404)")
        print("=" * 100)

        if resumen['llamadas_analizadas'] == 0:
            print("\n ADVERTENCIA: No se encontraron llamadas para analizar")
            print("   - Verifica que los BRUCE_IDs en logs coincidan con Sheets (columna Z)")
            return

        print(f"\n Llamadas analizadas: {resumen['llamadas_analizadas']}")
        print(f"    Sin errores: {resumen['llamadas_sin_errores']} ({resumen['llamadas_sin_errores']/resumen['llamadas_analizadas']*100:.1f}%)")
        print(f"    Con errores: {resumen['llamadas_con_errores']} ({resumen['llamadas_con_errores']/resumen['llamadas_analizadas']*100:.1f}%)")

        print(f"\n Total de errores detectados: {resumen['total_errores']}")

        if resumen['errores_por_severidad']:
            print("\n Errores por severidad:")
            for severidad, cantidad in sorted(resumen['errores_por_severidad'].items(), reverse=True):
                print(f"   {severidad}: {cantidad}")

        if resumen['errores_por_tipo']:
            print("\n Errores por tipo:")
            for tipo, cantidad in sorted(resumen['errores_por_tipo'].items(), key=lambda x: x[1], reverse=True):
                tipo_legible = tipo.replace("_", " ").title()
                print(f"   {tipo_legible}: {cantidad}")

        # Detallar errores
        if resumen['errores_detallados']:
            print("\n" + "=" * 100)
            print(" ERRORES DETALLADOS")
            print("=" * 100)

            for i, error in enumerate(resumen['errores_detallados'], 1):
                print(f"\n ERROR {i}/{len(resumen['errores_detallados'])} - {error['tipo']}")
                print(f"   BRUCE ID: {error['bruce_id']}")
                print(f"   Severidad: {error['severidad']}")
                print(f"   Descripción: {error['descripcion']}")
                print(f"   Evidencia (cliente dijo):")
                for evidencia in error.get('evidencia_cliente', []):
                    print(f"     - \"{evidencia}\"")
                if 'resultado_final' in error:
                    print(f"   Resultado final: {error['resultado_final']}")
                if 'tiempo_llamada' in error:
                    print(f"   Tiempo llamada: {error['tiempo_llamada']}")

        print("\n" + "=" * 100)

        # Conclusiones
        if resumen['llamadas_con_errores'] > 0:
            tasa_error = resumen['llamadas_con_errores'] / resumen['llamadas_analizadas'] * 100
            print(f"\n  Tasa de error: {tasa_error:.1f}%")

            if tasa_error > 30:
                print("    CRÍTICO: Más del 30% de llamadas tienen errores en manejo de encargado")
            elif tasa_error > 15:
                print("     ALTO: Más del 15% de llamadas tienen errores en manejo de encargado")
            else:
                print("   Tasa de error aceptable pero mejorable")
        else:
            print("\n ¡Excelente! No se detectaron errores en manejo de encargado")

        print("=" * 100)


def main():
    """Función principal"""
    import sys

    print("=" * 100)
    print(" ANALIZADOR HÍBRIDO - MANEJO DE ENCARGADO (FIX 404)")
    print(" Correlaciona: Logs Railway (cliente) + Google Sheets (resultados)")
    print("=" * 100)

    if len(sys.argv) < 2:
        print("\n Error: Debes proporcionar la ruta al archivo de logs")
        print("\nUso:")
        print(f"   python {sys.argv[0]} <ruta_archivo_logs.txt>")
        print("\nEjemplo:")
        print(f"   python {sys.argv[0]} logs_railway_completo.txt")
        return

    ruta_archivo = sys.argv[1]

    # Crear analizador
    analizador = AnalizadorEncargadoHibrido()

    # Analizar
    try:
        resumen = analizador.analizar_logs(ruta_archivo)

        # Imprimir resumen
        analizador.imprimir_resumen(resumen)

        print(f"\n Análisis completado - {resumen['llamadas_analizadas']} llamadas procesadas")

    except FileNotFoundError:
        print(f"\n Error: No se encontró el archivo '{ruta_archivo}'")
    except Exception as e:
        print(f"\n Error durante el análisis: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
