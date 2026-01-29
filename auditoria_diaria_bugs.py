# -*- coding: utf-8 -*-
"""
AUDITORIA DIARIA DE BUGS - FASE DE IMPLEMENTACION
Script para detectar bugs y problemas sin corregir en logs de Railway

Caracteristicas:
- Lee logs desde carpeta local (no descarga de Railway)
- Guarda historial de archivos ya analizados (evita duplicados)
- Detecta patrones de bugs conocidos (FIX 508-511 y anteriores)
- Genera reporte con bugs sin corregir
- Identifica nuevos patrones de error

Uso:
    python auditoria_diaria_bugs.py
    python auditoria_diaria_bugs.py --forzar  # Re-analiza todos los archivos
    python auditoria_diaria_bugs.py --archivo logs.123.log  # Analiza archivo especifico

Autor: Sistema Bruce W - Auditoria Automatizada
Fecha: 2026-01-28
"""

import os
import re
import json
import hashlib
from datetime import datetime
from collections import defaultdict, Counter
from typing import Dict, List, Tuple, Optional
import argparse

# Configuracion
CARPETA_LOGS = r"C:\Users\PC 1\AgenteVentas\LOGS"
HISTORIAL_FILE = r"C:\Users\PC 1\AgenteVentas\historial_auditoria_bugs.json"
REPORTE_DIR = r"C:\Users\PC 1\AgenteVentas\reportes_auditoria"


class AuditoriaDiariaBugs:
    """Sistema de auditoria diaria para deteccion de bugs en fase de implementacion"""

    def __init__(self, carpeta_logs: str = CARPETA_LOGS):
        self.carpeta_logs = carpeta_logs
        self.historial = self._cargar_historial()
        self.bugs_detectados = []
        self.llamadas_analizadas = {}
        self.estadisticas = defaultdict(int)

        # Crear carpeta de reportes si no existe
        os.makedirs(REPORTE_DIR, exist_ok=True)

        # Patrones de bugs conocidos
        self._inicializar_patrones()

    def _inicializar_patrones(self):
        """Define patrones de bugs conocidos para deteccion"""

        # FIX 508: "Si, digame" incorrecto cuando cliente pregunta productos
        self.patron_fix508 = {
            'nombre': 'FIX_508_SI_DIGAME_INCORRECTO',
            'descripcion': 'Bruce dice "Si, digame" cuando cliente pregunta por productos/marca',
            'patron_cliente': [
                r'qu[eé]\s+productos?\s+maneja',
                r'qu[eé]\s+tipo\s+de\s+productos',
                r'qu[eé]\s+vende',
                r'repite\s+tu\s+marca',
                r'repites\s+tu\s+marca',
                r'cu[aá]l\s+es\s+tu\s+marca'
            ],
            'patron_error_bruce': r's[ií],?\s*d[ií]game'
        }

        # FIX 509b: No entender "no tengo WhatsApp"
        self.patron_fix509b = {
            'nombre': 'FIX_509B_NO_TENGO_WHATSAPP',
            'descripcion': 'Bruce no entiende cuando cliente dice que no tiene WhatsApp',
            'patron_cliente': [
                r'no\s+tengo\s+whatsapp',
                r'no\s+manejo\s+whatsapp',
                r'tel[eé]fono\s+(es\s+)?directo',
                r'es\s+telmex',
                r'l[ií]nea\s+(fija|directa)',
                r'no\s+tenemos\s+whatsapp'
            ],
            'patron_error_bruce': r'(whatsapp|me\s+puede\s+dar|me\s+comparte)'
        }

        # FIX 510: Cliente pide contacto de NIOVAL y no se lo dan
        self.patron_fix510 = {
            'nombre': 'FIX_510_PIDE_CONTACTO_NIOVAL',
            'descripcion': 'Cliente pide contacto de NIOVAL y Bruce no lo proporciona',
            'patron_cliente': [
                r'd[eé]melo',
                r'd[aá]melo',
                r'me\s+lo\s+da',
                r'me\s+lo\s+das',
                r'p[aá]same\s+el\s+n[uú]mero',
                r'cu[aá]l\s+es\s+su\s+whatsapp',
                r'tienen\s+whatsapp'
            ],
            'patron_ok_bruce': r'(332\s*1\s*0\s*1\s*4\s*4\s*8\s*6|ventas\s*arroba\s*nioval)'
        }

        # FIX 511: Timeouts de Deepgram
        self.patron_fix511 = {
            'nombre': 'FIX_511_TIMEOUT_DEEPGRAM',
            'descripcion': 'Timeout de Deepgram causando delays largos',
            'patron_log': [
                r'FIX\s+401.*Deepgram\s+no\s+respondi[oó]',
                r'Deepgram\s+no\s+respondi[oó]\s+en\s+\d+',
                r'timeout.*deepgram',
                r'FIX\s+511.*PARCIAL.*fallback'
            ]
        }

        # Repeticiones incorrectas
        self.patron_repeticiones = {
            'nombre': 'REPETICION_DETECTADA',
            'descripcion': 'Bruce repite la misma respuesta multiples veces',
            'patron_log': r'REPETICI[OÓ]N\s+DETECTADA|repitiendo\s+respuesta'
        }

        # IVR no detectado o falso positivo
        self.patron_ivr = {
            'nombre': 'IVR_PROBLEMA',
            'descripcion': 'IVR no detectado correctamente o falso positivo',
            'patron_log': [
                r'FALSO\s+POSITIVO\s+IVR',
                r'IVR.*no\s+detectado',
                r'contestadora.*persona\s+real'
            ]
        }

        # Encargado no disponible mal manejado
        self.patron_encargado = {
            'nombre': 'ENCARGADO_MAL_MANEJADO',
            'descripcion': 'Bruce no maneja bien cuando encargado no esta',
            'patron_cliente': [
                r'no\s+est[aá]',
                r'no\s+se\s+encuentra',
                r'sali[oó]\s+a\s+comer',
                r'est[aá]\s+ocupad[oa]'
            ],
            'patron_error_bruce': r'cat[aá]logo|productos|promoci[oó]n'
        }

        # Interrupciones mal manejadas
        self.patron_interrupciones = {
            'nombre': 'INTERRUPCION_MAL_MANEJADA',
            'descripcion': 'Bruce no maneja bien las interrupciones del cliente',
            'patron_log': r'Cliente\s+interrumpi[oó]|interrupci[oó]n\s+detectada'
        }

        # Error de API ElevenLabs
        self.patron_elevenlabs = {
            'nombre': 'ERROR_ELEVENLABS',
            'descripcion': 'Error en API de ElevenLabs (cuota, timeout, etc)',
            'patron_log': [
                r'quota_exceeded',
                r'ElevenLabs.*error',
                r'ApiError.*eleven',
                r'credits\s+remaining.*required'
            ]
        }

        # Error Twilio (solo errores reales, no logs HTTP normales)
        self.patron_twilio = {
            'nombre': 'ERROR_TWILIO',
            'descripcion': 'Error en Twilio (callback, conexion, etc)',
            'patron_log': [
                r'TwilioException',
                r'status_callback_error',
                r'Twilio.*error.*(?!200)',  # Excluir codigo 200
                r'Twilio.*failed',
                r'Error.*llamada.*Twilio'
            ]
        }

        # Patron para detectar IVR/Contestadora
        self.patron_ivr_detectado = {
            'nombre': 'IVR_DETECTADO',
            'descripcion': 'Llamada detectada como IVR/Contestadora',
            'patron_log': r'IVR/CONTESTADORA\s+DETECTADO|resultado.*IVR|contestadora\s+detectada'
        }

        # Patron para cliente frustrado/enojado
        self.patron_cliente_frustrado = {
            'nombre': 'CLIENTE_FRUSTRADO',
            'descripcion': 'Cliente muestra frustracion o enojo',
            'palabras_clave': [
                'no me interesa', 'ya te dije', 'deja de llamar', 'no llames',
                'molestando', 'que molesto', 'que fastidio', 'colgar',
                'no entiendes', 'ya entendiste', 'sordo', 'idiota',
                'estupido', 'maquina', 'robot', 'grabacion'
            ]
        }

        # Patron para llamada abandonada (cliente cuelga rapido)
        self.patron_llamada_abandonada = {
            'nombre': 'LLAMADA_ABANDONADA',
            'descripcion': 'Cliente colgo en menos de 30 segundos',
            'patron_log': r'duracion.*menos.*30|llamada.*corta|colgaron.*rapido'
        }

        # Metricas adicionales para analisis
        self.metricas_llamada = {
            'latencias': [],       # Tiempos de respuesta de Bruce
            'duraciones': [],      # Duracion de llamadas
            'ivr_count': 0,        # Contador de IVR
            'humanos_count': 0,    # Contador de humanos
            'abandonadas': 0,      # Llamadas abandonadas
            'frustrados': 0        # Clientes frustrados
        }

    def _cargar_historial(self) -> Dict:
        """Carga historial de archivos ya analizados"""
        if os.path.exists(HISTORIAL_FILE):
            try:
                with open(HISTORIAL_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"  Error cargando historial: {e}")
        return {'archivos_analizados': {}, 'ultima_auditoria': None}

    def _guardar_historial(self):
        """Guarda historial de archivos analizados"""
        self.historial['ultima_auditoria'] = datetime.now().isoformat()
        try:
            with open(HISTORIAL_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.historial, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"  Error guardando historial: {e}")

    def _calcular_hash(self, filepath: str) -> str:
        """Calcula hash MD5 de un archivo para detectar cambios"""
        hasher = hashlib.md5()
        with open(filepath, 'rb') as f:
            # Solo leer primeros 10KB para rapidez
            hasher.update(f.read(10240))
        return hasher.hexdigest()

    def _archivo_ya_analizado(self, filepath: str) -> bool:
        """Verifica si un archivo ya fue analizado (mismo hash)"""
        nombre = os.path.basename(filepath)
        hash_actual = self._calcular_hash(filepath)

        if nombre in self.historial['archivos_analizados']:
            return self.historial['archivos_analizados'][nombre]['hash'] == hash_actual
        return False

    def _marcar_analizado(self, filepath: str, bugs_encontrados: int):
        """Marca archivo como analizado en historial"""
        nombre = os.path.basename(filepath)
        self.historial['archivos_analizados'][nombre] = {
            'hash': self._calcular_hash(filepath),
            'fecha_analisis': datetime.now().isoformat(),
            'bugs_encontrados': bugs_encontrados
        }

    def obtener_archivos_logs(self) -> List[str]:
        """Obtiene lista de archivos de logs a analizar"""
        archivos = []

        if not os.path.exists(self.carpeta_logs):
            print(f"  Carpeta no existe: {self.carpeta_logs}")
            return archivos

        for nombre in os.listdir(self.carpeta_logs):
            # Aceptar ambos formatos: logs.*.log y *.txt (DD_MM_*.txt)
            es_log = nombre.startswith('logs.') and nombre.endswith('.log')
            es_txt = nombre.endswith('.txt') and not nombre.startswith('indice')
            if es_log or es_txt:
                filepath = os.path.join(self.carpeta_logs, nombre)
                archivos.append(filepath)

        # Ordenar por fecha de modificacion (mas recientes primero)
        archivos.sort(key=lambda x: os.path.getmtime(x), reverse=True)

        return archivos

    def extraer_conversaciones(self, contenido: str) -> Dict[str, List[Dict]]:
        """Extrae conversaciones individuales de los logs"""
        conversaciones = defaultdict(list)

        # Patron para extraer BRUCE ID y mensajes
        patron_bruce_dice = r'\[BRUCE\]\s+BRUCE(\d+)\s+DICE:\s*"([^"]+)"'
        patron_cliente_dijo = r'\[CLIENTE\]\s+BRUCE(\d+)\s+CLIENTE\s+DIJO:\s*"([^"]+)"'

        for match in re.finditer(patron_bruce_dice, contenido):
            bruce_id = f"BRUCE{match.group(1)}"
            texto = match.group(2)
            conversaciones[bruce_id].append({
                'quien': 'BRUCE',
                'texto': texto
            })

        for match in re.finditer(patron_cliente_dijo, contenido):
            bruce_id = f"BRUCE{match.group(1)}"
            texto = match.group(2)
            conversaciones[bruce_id].append({
                'quien': 'CLIENTE',
                'texto': texto
            })

        return conversaciones

    def detectar_bug_patron(self, conversacion: List[Dict], bruce_id: str,
                           patron_config: Dict) -> Optional[Dict]:
        """Detecta si hay un bug basado en patron cliente + respuesta Bruce"""

        for i, msg in enumerate(conversacion):
            if msg['quien'] != 'CLIENTE':
                continue

            texto_cliente = msg['texto'].lower()

            # Verificar si cliente dice algo que dispara el patron
            patron_encontrado = False
            for patron in patron_config.get('patron_cliente', []):
                if re.search(patron, texto_cliente, re.IGNORECASE):
                    patron_encontrado = True
                    break

            if not patron_encontrado:
                continue

            # Buscar respuesta de Bruce en los siguientes mensajes
            for j in range(i + 1, min(i + 3, len(conversacion))):
                if conversacion[j]['quien'] != 'BRUCE':
                    continue

                texto_bruce = conversacion[j]['texto'].lower()

                # Si hay patron_ok_bruce, verificar que NO este presente (seria bug)
                if 'patron_ok_bruce' in patron_config:
                    if not re.search(patron_config['patron_ok_bruce'], texto_bruce, re.IGNORECASE):
                        return {
                            'tipo': patron_config['nombre'],
                            'descripcion': patron_config['descripcion'],
                            'bruce_id': bruce_id,
                            'cliente_dijo': msg['texto'],
                            'bruce_respondio': conversacion[j]['texto'],
                            'esperado': 'Respuesta con contacto de NIOVAL'
                        }

                # Si hay patron_error_bruce, verificar que SI este presente (seria bug)
                elif 'patron_error_bruce' in patron_config:
                    if re.search(patron_config['patron_error_bruce'], texto_bruce, re.IGNORECASE):
                        return {
                            'tipo': patron_config['nombre'],
                            'descripcion': patron_config['descripcion'],
                            'bruce_id': bruce_id,
                            'cliente_dijo': msg['texto'],
                            'bruce_respondio': conversacion[j]['texto'],
                            'esperado': 'Respuesta contextual, no generica'
                        }

                break  # Solo verificar primera respuesta de Bruce

        return None

    def _buscar_bruce_id_cercano(self, lineas: List[str], indice: int, bruce_ids: set) -> str:
        """Busca el BRUCE ID mas cercano en las lineas anteriores"""
        # Buscar en las 20 lineas anteriores
        for offset in range(20):
            idx = indice - offset
            if idx < 0:
                break
            for bid in bruce_ids:
                if f'BRUCE{bid}' in lineas[idx]:
                    return f'BRUCE{bid}'
        return 'DESCONOCIDO'

    def detectar_bugs_log(self, contenido: str, filepath: str) -> List[Dict]:
        """Detecta bugs en logs basado en patrones de texto"""
        bugs = []
        lineas = contenido.split('\n')

        # Extraer BRUCE IDs del log
        bruce_ids = set(re.findall(r'BRUCE(\d+)', contenido))

        # Contador para evitar duplicados consecutivos
        ultimo_bug_tipo = None
        ultimo_bug_linea = -10

        for i, linea in enumerate(lineas):
            # FIX 511: Timeouts de Deepgram
            for patron in self.patron_fix511['patron_log']:
                if re.search(patron, linea, re.IGNORECASE):
                    # Evitar duplicados consecutivos (mismo tipo en menos de 5 lineas)
                    if ultimo_bug_tipo == 'FIX_511_TIMEOUT_DEEPGRAM' and (i - ultimo_bug_linea) < 5:
                        continue

                    # Buscar BRUCE ID en lineas cercanas
                    bruce_id = self._buscar_bruce_id_cercano(lineas, i, bruce_ids)

                    bugs.append({
                        'tipo': self.patron_fix511['nombre'],
                        'descripcion': self.patron_fix511['descripcion'],
                        'bruce_id': bruce_id,
                        'linea': i + 1,
                        'contexto': linea.strip()[:200],
                        'archivo': os.path.basename(filepath)
                    })
                    ultimo_bug_tipo = 'FIX_511_TIMEOUT_DEEPGRAM'
                    ultimo_bug_linea = i
                    break

            # Repeticiones
            if re.search(self.patron_repeticiones['patron_log'], linea, re.IGNORECASE):
                bruce_id = None
                for bid in bruce_ids:
                    if f'BRUCE{bid}' in linea:
                        bruce_id = f'BRUCE{bid}'
                        break

                bugs.append({
                    'tipo': self.patron_repeticiones['nombre'],
                    'descripcion': self.patron_repeticiones['descripcion'],
                    'bruce_id': bruce_id or 'DESCONOCIDO',
                    'linea': i + 1,
                    'contexto': linea.strip()[:200],
                    'archivo': os.path.basename(filepath)
                })

            # Errores ElevenLabs
            for patron in self.patron_elevenlabs['patron_log']:
                if re.search(patron, linea, re.IGNORECASE):
                    bugs.append({
                        'tipo': self.patron_elevenlabs['nombre'],
                        'descripcion': self.patron_elevenlabs['descripcion'],
                        'bruce_id': 'SISTEMA',
                        'linea': i + 1,
                        'contexto': linea.strip()[:200],
                        'archivo': os.path.basename(filepath)
                    })
                    break

            # Errores Twilio (excluir logs HTTP normales con codigo 200/301/302)
            if '" 200 -' not in linea and '" 301 -' not in linea and '" 302 -' not in linea:
                for patron in self.patron_twilio['patron_log']:
                    if re.search(patron, linea, re.IGNORECASE):
                        bugs.append({
                            'tipo': self.patron_twilio['nombre'],
                            'descripcion': self.patron_twilio['descripcion'],
                            'bruce_id': 'SISTEMA',
                            'linea': i + 1,
                            'contexto': linea.strip()[:200],
                            'archivo': os.path.basename(filepath)
                        })
                        break

        return bugs

    def analizar_metricas_avanzadas(self, contenido: str, filepath: str) -> Dict:
        """Analiza metricas avanzadas: latencia, duracion, IVR, frustrados"""
        metricas = {
            'latencias': [],
            'duraciones': [],
            'ivr_count': 0,
            'humanos_count': 0,
            'abandonadas': 0,
            'frustrados': 0,
            'llamadas_analizadas': set()
        }

        lineas = contenido.split('\n')

        for linea in lineas:
            # Extraer latencias de respuesta (tiempo de generacion de audio)
            # Patron: "Audio en X.XXs" o "Primer chunk en X.XXs"
            match_latencia = re.search(r'(?:Audio en|Primer chunk en)\s+([\d.]+)s', linea)
            if match_latencia:
                latencia = float(match_latencia.group(1))
                metricas['latencias'].append(latencia)

            # Detectar IVR/Contestadora
            if re.search(self.patron_ivr_detectado['patron_log'], linea, re.IGNORECASE):
                metricas['ivr_count'] += 1

            # Detectar llamadas con humanos (resultado APROBADO o NEGADO indica humano)
            if re.search(r'resultado.*(?:APROBADO|NEGADO|aprobado|negado)', linea, re.IGNORECASE):
                metricas['humanos_count'] += 1

            # Detectar duracion de llamada
            match_duracion = re.search(r'duracion[_\s]?(?:llamada)?[:\s]*([\d.]+)', linea, re.IGNORECASE)
            if match_duracion:
                duracion = float(match_duracion.group(1))
                metricas['duraciones'].append(duracion)
                # Llamada abandonada si < 30 segundos
                if duracion < 30:
                    metricas['abandonadas'] += 1

            # Detectar cliente frustrado por palabras clave
            linea_lower = linea.lower()
            for palabra in self.patron_cliente_frustrado['palabras_clave']:
                if palabra in linea_lower and 'CLIENTE DIJO' in linea:
                    metricas['frustrados'] += 1
                    break

        return metricas

    def analizar_archivo(self, filepath: str) -> Tuple[List[Dict], Dict]:
        """Analiza un archivo de logs y detecta bugs + metricas avanzadas"""
        bugs = []
        metricas = {}

        try:
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                contenido = f.read()
        except Exception as e:
            print(f"    Error leyendo {filepath}: {e}")
            return bugs, metricas

        # 1. Detectar bugs en logs (timeouts, errores, etc)
        bugs_log = self.detectar_bugs_log(contenido, filepath)
        bugs.extend(bugs_log)

        # 2. Extraer conversaciones y analizar patrones
        conversaciones = self.extraer_conversaciones(contenido)

        for bruce_id, conv in conversaciones.items():
            # FIX 508: "Si, digame" incorrecto
            bug = self.detectar_bug_patron(conv, bruce_id, self.patron_fix508)
            if bug:
                bug['archivo'] = os.path.basename(filepath)
                bugs.append(bug)

            # FIX 509b: No tengo WhatsApp
            bug = self.detectar_bug_patron(conv, bruce_id, self.patron_fix509b)
            if bug:
                bug['archivo'] = os.path.basename(filepath)
                bugs.append(bug)

            # FIX 510: Cliente pide contacto
            bug = self.detectar_bug_patron(conv, bruce_id, self.patron_fix510)
            if bug:
                bug['archivo'] = os.path.basename(filepath)
                bugs.append(bug)

            # Encargado mal manejado
            bug = self.detectar_bug_patron(conv, bruce_id, self.patron_encargado)
            if bug:
                bug['archivo'] = os.path.basename(filepath)
                bugs.append(bug)

        # 3. Analizar metricas avanzadas
        metricas = self.analizar_metricas_avanzadas(contenido, filepath)

        return bugs, metricas

    def ejecutar_auditoria(self, forzar: bool = False, archivo_especifico: str = None) -> Dict:
        """Ejecuta la auditoria completa"""
        print("\n" + "=" * 80)
        print(" AUDITORIA DIARIA DE BUGS - FASE DE IMPLEMENTACION")
        print(f" Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 80)

        # Obtener archivos a analizar
        if archivo_especifico:
            if os.path.exists(archivo_especifico):
                archivos = [archivo_especifico]
            else:
                filepath = os.path.join(self.carpeta_logs, archivo_especifico)
                if os.path.exists(filepath):
                    archivos = [filepath]
                else:
                    print(f"\n  Archivo no encontrado: {archivo_especifico}")
                    return {}
        else:
            archivos = self.obtener_archivos_logs()

        print(f"\n  Carpeta de logs: {self.carpeta_logs}")
        print(f"  Archivos encontrados: {len(archivos)}")

        if self.historial.get('ultima_auditoria'):
            print(f"  Ultima auditoria: {self.historial['ultima_auditoria']}")

        # Filtrar archivos ya analizados
        archivos_nuevos = []
        archivos_omitidos = 0

        for filepath in archivos:
            if forzar or not self._archivo_ya_analizado(filepath):
                archivos_nuevos.append(filepath)
            else:
                archivos_omitidos += 1

        print(f"\n  Archivos nuevos/modificados: {len(archivos_nuevos)}")
        print(f"  Archivos ya analizados (omitidos): {archivos_omitidos}")

        if not archivos_nuevos:
            print("\n  No hay archivos nuevos para analizar")
            return {'archivos_analizados': 0, 'bugs_detectados': 0}

        # Analizar archivos
        print("\n" + "-" * 80)
        print(" ANALIZANDO ARCHIVOS")
        print("-" * 80)

        todos_bugs = []
        todas_metricas = {
            'latencias': [],
            'duraciones': [],
            'ivr_count': 0,
            'humanos_count': 0,
            'abandonadas': 0,
            'frustrados': 0
        }

        for i, filepath in enumerate(archivos_nuevos, 1):
            nombre = os.path.basename(filepath)
            print(f"\n  [{i}/{len(archivos_nuevos)}] {nombre}")

            bugs, metricas = self.analizar_archivo(filepath)
            todos_bugs.extend(bugs)

            # Acumular metricas
            todas_metricas['latencias'].extend(metricas.get('latencias', []))
            todas_metricas['duraciones'].extend(metricas.get('duraciones', []))
            todas_metricas['ivr_count'] += metricas.get('ivr_count', 0)
            todas_metricas['humanos_count'] += metricas.get('humanos_count', 0)
            todas_metricas['abandonadas'] += metricas.get('abandonadas', 0)
            todas_metricas['frustrados'] += metricas.get('frustrados', 0)

            self._marcar_analizado(filepath, len(bugs))

            if bugs:
                print(f"      Bugs detectados: {len(bugs)}")
                for bug in bugs[:3]:  # Mostrar primeros 3
                    print(f"        - {bug['tipo']}: {bug.get('bruce_id', 'N/A')}")
                if len(bugs) > 3:
                    print(f"        ... y {len(bugs) - 3} mas")
            else:
                print(f"      Sin bugs detectados")

        # Guardar historial
        self._guardar_historial()

        # Generar reporte
        self._generar_reporte(todos_bugs, archivos_nuevos, todas_metricas)

        return {
            'archivos_analizados': len(archivos_nuevos),
            'bugs_detectados': len(todos_bugs),
            'bugs': todos_bugs,
            'metricas': todas_metricas
        }

    def _generar_reporte(self, bugs: List[Dict], archivos: List[str], metricas: Dict = None):
        """Genera reporte de la auditoria"""
        print("\n" + "=" * 80)
        print(" RESUMEN DE AUDITORIA")
        print("=" * 80)

        print(f"\n  Total archivos analizados: {len(archivos)}")
        print(f"  Total bugs detectados: {len(bugs)}")

        # Mostrar metricas avanzadas
        if metricas:
            print("\n" + "-" * 60)
            print(" METRICAS AVANZADAS")
            print("-" * 60)

            # Latencia promedio
            if metricas.get('latencias'):
                latencia_prom = sum(metricas['latencias']) / len(metricas['latencias'])
                latencia_max = max(metricas['latencias'])
                latencia_min = min(metricas['latencias'])
                print(f"\n  LATENCIA DE RESPUESTA:")
                print(f"    Promedio: {latencia_prom:.2f}s")
                print(f"    Minima: {latencia_min:.2f}s")
                print(f"    Maxima: {latencia_max:.2f}s")
                if latencia_prom > 3.0:
                    print(f"    [ALERTA] Latencia alta (>3s)")

            # Duracion de llamadas
            if metricas.get('duraciones'):
                dur_prom = sum(metricas['duraciones']) / len(metricas['duraciones'])
                dur_max = max(metricas['duraciones'])
                dur_min = min(metricas['duraciones'])
                print(f"\n  DURACION DE LLAMADAS:")
                print(f"    Promedio: {dur_prom:.1f}s")
                print(f"    Minima: {dur_min:.1f}s")
                print(f"    Maxima: {dur_max:.1f}s")

            # IVR vs Humanos
            ivr = metricas.get('ivr_count', 0)
            humanos = metricas.get('humanos_count', 0)
            total_contactos = ivr + humanos
            if total_contactos > 0:
                tasa_ivr = (ivr / total_contactos * 100)
                print(f"\n  IVR vs HUMANOS:")
                print(f"    IVR/Contestadoras: {ivr} ({tasa_ivr:.1f}%)")
                print(f"    Humanos: {humanos} ({100-tasa_ivr:.1f}%)")
                if tasa_ivr > 30:
                    print(f"    [ALERTA] Tasa IVR alta (>30%)")

            # Llamadas abandonadas
            abandonadas = metricas.get('abandonadas', 0)
            if abandonadas > 0:
                print(f"\n  LLAMADAS ABANDONADAS (<30s): {abandonadas}")

            # Clientes frustrados
            frustrados = metricas.get('frustrados', 0)
            if frustrados > 0:
                print(f"\n  CLIENTES FRUSTRADOS/ENOJADOS: {frustrados}")
                print(f"    [ALERTA] Revisar conversaciones con clientes molestos")

        if not bugs:
            print("\n  No se detectaron bugs en esta auditoria")

        # Agrupar por tipo
        if bugs:
            bugs_por_tipo = Counter([b['tipo'] for b in bugs])

            print("\n  BUGS POR TIPO:")
            print("  " + "-" * 40)
            for tipo, count in bugs_por_tipo.most_common():
                print(f"    {tipo}: {count}")

            # Agrupar por BRUCE ID
            bugs_por_bruce = Counter([b.get('bruce_id', 'N/A') for b in bugs])

            print("\n  BUGS POR LLAMADA:")
            print("  " + "-" * 40)
            for bruce_id, count in bugs_por_bruce.most_common(10):
                print(f"    {bruce_id}: {count} bugs")
        else:
            bugs_por_tipo = {}
            bugs_por_bruce = {}

        # Guardar reporte en archivo
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        reporte_file = os.path.join(REPORTE_DIR, f"auditoria_{timestamp}.json")

        reporte = {
            'fecha': datetime.now().isoformat(),
            'archivos_analizados': len(archivos),
            'total_bugs': len(bugs),
            'bugs_por_tipo': dict(bugs_por_tipo),
            'bugs_por_bruce': dict(bugs_por_bruce),
            'metricas_avanzadas': metricas,
            'detalle_bugs': bugs
        }

        with open(reporte_file, 'w', encoding='utf-8') as f:
            json.dump(reporte, f, indent=2, ensure_ascii=False)

        print(f"\n  Reporte guardado: {reporte_file}")

        # Mostrar bugs criticos
        bugs_criticos = [b for b in bugs if b['tipo'] in [
            'ERROR_ELEVENLABS', 'ERROR_TWILIO', 'FIX_511_TIMEOUT_DEEPGRAM'
        ]]

        if bugs_criticos:
            print("\n" + "=" * 80)
            print(" BUGS CRITICOS (requieren atencion inmediata)")
            print("=" * 80)

            for bug in bugs_criticos[:5]:
                print(f"\n  Tipo: {bug['tipo']}")
                print(f"  BRUCE ID: {bug.get('bruce_id', 'N/A')}")
                print(f"  Archivo: {bug.get('archivo', 'N/A')}")
                if 'contexto' in bug:
                    print(f"  Contexto: {bug['contexto'][:100]}...")

        # Mostrar bugs de conversacion
        bugs_conversacion = [b for b in bugs if b['tipo'] in [
            'FIX_508_SI_DIGAME_INCORRECTO', 'FIX_509B_NO_TENGO_WHATSAPP',
            'FIX_510_PIDE_CONTACTO_NIOVAL', 'ENCARGADO_MAL_MANEJADO'
        ]]

        if bugs_conversacion:
            print("\n" + "=" * 80)
            print(" BUGS DE CONVERSACION (logica de respuestas)")
            print("=" * 80)

            for bug in bugs_conversacion[:5]:
                print(f"\n  Tipo: {bug['tipo']}")
                print(f"  BRUCE ID: {bug.get('bruce_id', 'N/A')}")
                if 'cliente_dijo' in bug:
                    print(f"  Cliente dijo: \"{bug['cliente_dijo'][:80]}...\"")
                if 'bruce_respondio' in bug:
                    print(f"  Bruce respondio: \"{bug['bruce_respondio'][:80]}...\"")
                if 'esperado' in bug:
                    print(f"  Esperado: {bug['esperado']}")


def main():
    parser = argparse.ArgumentParser(description='Auditoria diaria de bugs - Fase de implementacion')
    parser.add_argument('--forzar', action='store_true',
                       help='Re-analizar todos los archivos (ignorar historial)')
    parser.add_argument('--archivo', type=str,
                       help='Analizar archivo especifico')

    args = parser.parse_args()

    auditoria = AuditoriaDiariaBugs()
    resultado = auditoria.ejecutar_auditoria(
        forzar=args.forzar,
        archivo_especifico=args.archivo
    )

    print("\n" + "=" * 80)
    print(" AUDITORIA COMPLETADA")
    print("=" * 80)

    if resultado.get('bugs_detectados', 0) > 0:
        print(f"\n  Se detectaron {resultado['bugs_detectados']} bugs")
        print("  Revisar reporte para detalles")
        return 1  # Exit code indica bugs encontrados
    else:
        print("\n  No se detectaron bugs")
        return 0


if __name__ == '__main__':
    exit(main())
