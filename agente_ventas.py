"""
Sistema de Agente de Ventas con GPT-4o + ElevenLabs
Empresa: NIOVAL
"""

import os
import json
import time
from datetime import datetime
from enum import Enum
from openai import OpenAI
from elevenlabs import ElevenLabs, VoiceSettings
import pandas as pd
from dotenv import load_dotenv
from detector_ivr import DetectorIVR  # FIX 202: Detector de IVR/contestadoras automáticas

# FIX 769: Variantes formales de acknowledgment con rotación
# FIX 803: "continúe" → "prosiga" (TTS pronunciaba como portugués "continue")
_ACK_VARIANTS_769 = [
    "Sí, adelante.",
    "Claro, prosiga.",
    "Sí, lo escucho.",
    "Entendido, prosiga.",
    "Perfecto, adelante.",
]
_ACK_DIGAME_769 = [
    "Claro, dígame.",
    "Sí, adelante, dígame.",
    "Perfecto, dígame.",
    "Entendido, dígame.",
]
_ack_counter_769 = 0


def _get_ack_769(digame=False):
    """FIX 769: Retorna acknowledgment formal con rotación."""
    global _ack_counter_769
    variants = _ACK_DIGAME_769 if digame else _ACK_VARIANTS_769
    result = variants[_ack_counter_769 % len(variants)]
    _ack_counter_769 += 1
    return result


# FIX 519: Sistema de auto-aprendizaje de patrones
try:
    from cache_patrones_aprendidos import obtener_cache_patrones, inicializar_cache_patrones
    CACHE_PATRONES_DISPONIBLE = True
except ImportError:
    CACHE_PATRONES_DISPONIBLE = False
    print("   [WARN] FIX 519: cache_patrones_aprendidos no disponible")

# FIX 699: Memory Layer - Capa de memoria conversacional
try:
    from memory_layer import ConversationMemory
    MEMORY_LAYER_DISPONIBLE = True
except ImportError:
    MEMORY_LAYER_DISPONIBLE = False
    print("   [WARN] FIX 699: memory_layer no disponible")

# FIX 700: Speech Processor - Máquina de estados para speech
try:
    from speech_processor import SpeechStateMachine, SpeechState, SpeechAction
    SPEECH_PROCESSOR_DISPONIBLE = True
except ImportError:
    SPEECH_PROCESSOR_DISPONIBLE = False
    print("   [WARN] FIX 700: speech_processor no disponible")

# FIX 701: Intent Classifier - Clasificador centralizado de intenciones
try:
    from intent_classifier import IntentClassifier, IntentCategory
    INTENT_CLASSIFIER_DISPONIBLE = True
except ImportError:
    INTENT_CLASSIFIER_DISPONIBLE = False
    print("   [WARN] FIX 701: intent_classifier no disponible")


# [EMOJI]
# FIX 482 (AUDITORIA W04): SISTEMA DE MÉTRICAS E INSTRUMENTACIÓN
# [EMOJI]

class MetricsLogger:
    """
    FIX 482 (AUDITORIA W04): Logger de métricas completas para análisis de rendimiento.

    Problema detectado en auditoría:
    - NO hay visibilidad de latencias en producción
    - NO sabemos dónde están los cuellos de botella
    - NO podemos medir mejoras (FIX 475 redujo timeouts, ¿cuánto mejoró realmente?)

    Métricas tracked:
    - Timing: transcripción, GPT, generación audio, total por turno
    - Calidad: transcripciones incorrectas, preguntas respondidas vs ignoradas
    - Conversación: interrupciones, repeticiones, recuperaciones de error
    """

    def __init__(self):
        self.metricas = {
            # Métricas de timing (en segundos)
            "tiempos_transcripcion": [],
            "tiempos_gpt": [],
            "tiempos_audio": [],
            "tiempos_total_turno": [],

            # Métricas de calidad
            "preguntas_directas_respondidas": 0,
            "preguntas_directas_total": 0,
            "transcripciones_incorrectas": 0,
            "transcripciones_total": 0,

            # Métricas de interacción
            "interrupciones_detectadas": 0,
            "repeticiones_cliente": 0,
            "recuperaciones_error": 0,
            "respuestas_vacias_bloqueadas": 0,

            # Metadata
            "call_sid": None,
            "inicio_llamada": None,
            "fin_llamada": None,
        }

    def log_tiempo_transcripcion(self, segundos: float):
        """Registra tiempo de transcripción (Deepgram)"""
        self.metricas["tiempos_transcripcion"].append(segundos)

    def log_tiempo_gpt(self, segundos: float):
        """Registra tiempo de procesamiento GPT"""
        self.metricas["tiempos_gpt"].append(segundos)

    def log_tiempo_audio(self, segundos: float):
        """Registra tiempo de generación de audio (ElevenLabs)"""
        self.metricas["tiempos_audio"].append(segundos)

    def log_tiempo_total_turno(self, segundos: float):
        """Registra tiempo total de un turno conversacional"""
        self.metricas["tiempos_total_turno"].append(segundos)

    def log_pregunta_directa(self, respondida: bool):
        """Registra si Bruce respondió o ignoró pregunta directa"""
        self.metricas["preguntas_directas_total"] += 1
        if respondida:
            self.metricas["preguntas_directas_respondidas"] += 1

    def log_transcripcion(self, correcta: bool):
        """Registra si transcripción Deepgram fue correcta o tuvo errores"""
        self.metricas["transcripciones_total"] += 1
        if not correcta:
            self.metricas["transcripciones_incorrectas"] += 1

    def log_interrupcion_detectada(self):
        """Registra que se detectó y evitó una interrupción (FIX 477)"""
        self.metricas["interrupciones_detectadas"] += 1

    def log_repeticion_cliente(self):
        """Registra que cliente repitió pregunta (FIX 480)"""
        self.metricas["repeticiones_cliente"] += 1

    def log_recuperacion_error(self):
        """Registra que Bruce se recuperó de un error (FIX 481)"""
        self.metricas["recuperaciones_error"] += 1

    def log_respuesta_vacia_bloqueada(self):
        """Registra que se bloqueó respuesta vacía (FIX 479)"""
        self.metricas["respuestas_vacias_bloqueadas"] += 1

    def log_filtro_post_gpt(self, fix_id: str, tipo: str):
        """Registra que un filtro post-GPT fue aplicado (FIX 693/697/699)"""
        if "filtros_post_gpt" not in self.metricas:
            self.metricas["filtros_post_gpt"] = []
        self.metricas["filtros_post_gpt"].append({"fix": fix_id, "tipo": tipo})

    def get_promedios(self) -> dict:
        """Calcula promedios de todas las métricas de timing"""
        def avg(lista):
            return sum(lista) / len(lista) if lista else 0

        return {
            "tiempo_transcripcion_avg": avg(self.metricas["tiempos_transcripcion"]),
            "tiempo_gpt_avg": avg(self.metricas["tiempos_gpt"]),
            "tiempo_audio_avg": avg(self.metricas["tiempos_audio"]),
            "tiempo_total_turno_avg": avg(self.metricas["tiempos_total_turno"]),
            "tasa_preguntas_respondidas": (
                self.metricas["preguntas_directas_respondidas"] / self.metricas["preguntas_directas_total"]
                if self.metricas["preguntas_directas_total"] > 0 else 0
            ),
            "tasa_transcripciones_correctas": (
                (self.metricas["transcripciones_total"] - self.metricas["transcripciones_incorrectas"]) /
                self.metricas["transcripciones_total"]
                if self.metricas["transcripciones_total"] > 0 else 0
            ),
        }

    def generar_reporte(self) -> str:
        """
        Genera reporte legible de métricas para logs.

        Returns:
            String con reporte formateado
        """
        promedios = self.get_promedios()

        reporte = "\n" + "="*60 + "\n"
        reporte += "MÉTRICAS DE LLAMADA (FIX 482)\n"
        reporte += "="*60 + "\n"

        # Timing
        reporte += "\nTIMING PROMEDIO:\n"
        reporte += f"  Transcripción (Deepgram): {promedios['tiempo_transcripcion_avg']:.2f}s\n"
        reporte += f"  Procesamiento (GPT-4o):   {promedios['tiempo_gpt_avg']:.2f}s\n"
        reporte += f"  Audio (ElevenLabs):       {promedios['tiempo_audio_avg']:.2f}s\n"
        reporte += f"  Total por turno:          {promedios['tiempo_total_turno_avg']:.2f}s\n"

        # Calidad
        reporte += "\nCALIDAD:\n"
        reporte += f"  Preguntas respondidas:    {self.metricas['preguntas_directas_respondidas']}/{self.metricas['preguntas_directas_total']} "
        reporte += f"({promedios['tasa_preguntas_respondidas']*100:.1f}%)\n"
        reporte += f"  Transcripciones correctas: {self.metricas['transcripciones_total'] - self.metricas['transcripciones_incorrectas']}/{self.metricas['transcripciones_total']} "
        reporte += f"({promedios['tasa_transcripciones_correctas']*100:.1f}%)\n"

        # Interacciones
        reporte += "\nINTERACCIONES:\n"
        reporte += f"  Interrupciones evitadas:  {self.metricas['interrupciones_detectadas']}\n"
        reporte += f"  Repeticiones cliente:     {self.metricas['repeticiones_cliente']}\n"
        reporte += f"  Recuperaciones de error:  {self.metricas['recuperaciones_error']}\n"
        reporte += f"  Respuestas vacías bloqueadas: {self.metricas['respuestas_vacias_bloqueadas']}\n"

        reporte += "="*60 + "\n"

        return reporte

    def exportar_json(self) -> dict:
        """Exporta métricas en formato JSON para análisis"""
        return {
            **self.metricas,
            "promedios": self.get_promedios(),
        }


# FIX 339: Sistema de Estados de Conversación
# Esto ayuda a Bruce a saber en qué punto de la conversación está
# y evitar respuestas incoherentes o loops
class EstadoConversacion(Enum):
    INICIO = "inicio"                          # Llamada recién iniciada
    ESPERANDO_SALUDO = "esperando_saludo"      # Bruce saludó, espera respuesta
    PRESENTACION = "presentacion"              # Bruce se presentó
    BUSCANDO_ENCARGADO = "buscando_encargado"  # Preguntó por encargado
    ENCARGADO_NO_ESTA = "encargado_no_esta"    # Cliente dijo que no está - pedir contacto
    PIDIENDO_WHATSAPP = "pidiendo_whatsapp"    # Pidió WhatsApp
    PIDIENDO_CORREO = "pidiendo_correo"        # Pidió correo
    DICTANDO_NUMERO = "dictando_numero"        # Cliente está dictando número - NO INTERRUMPIR
    DICTANDO_CORREO = "dictando_correo"        # Cliente está dictando correo - NO INTERRUMPIR
    ESPERANDO_TRANSFERENCIA = "esperando"      # Cliente dijo "espere/permítame"
    CONTACTO_CAPTURADO = "contacto_capturado"  # Ya tenemos WhatsApp o correo
    DESPEDIDA = "despedida"                    # Conversación terminando
    CONVERSACION_NORMAL = "conversacion_normal"  # FIX 488: Estado normal de conversación
    # FIX 520 BRUCE1652: Flujo para ofrecer contacto de Bruce cuando cliente no puede dar info
    OFRECIENDO_CONTACTO_BRUCE = "ofreciendo_contacto_bruce"  # Bruce ofreció dejar su número
    ESPERANDO_DONDE_ANOTAR = "esperando_donde_anotar"        # Bruce preguntó si tiene dónde anotar

# FIX 552: Máquina de Estados para Flujo de Email/Correo
# PROBLEMA BRUCE1889: FIX 496/491 se dispara incorrectamente durante dictado
# SOLUCIÓN: Rastrear estado explícito del flujo de correo
class EstadoEmail(Enum):
    INICIAL = "inicial"            # Sin interacción sobre email
    OFRECIDO = "ofrecido"          # Cliente ofreció dar email
    ESPERANDO = "esperando"        # Cliente pidió esperar antes de dictar
    DICTANDO = "dictando"          # Cliente está DICTANDO email - NO INTERRUMPIR
    CAPTURADO = "capturado"        # Email ya fue capturado - NO volver a pedir

# Cargar variables de entorno desde .env
load_dotenv()

# Configuración
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY", "tu-api-key-aqui")
ELEVENLABS_VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID", "pNInz6obpgDQGcFmaJgB")

# Determinar si usar GitHub Models o OpenAI directo
USE_GITHUB_MODELS = os.getenv("USE_GITHUB_MODELS", "true").lower() == "true"

# Inicializar clientes
if USE_GITHUB_MODELS:
    print("[MODO] GitHub Models (Gratis - Para pruebas)")
    openai_client = OpenAI(
        base_url="https://models.inference.ai.azure.com",
        api_key=GITHUB_TOKEN
    )
else:
    print("[MODO] OpenAI Directo (Produccion)")
    openai_client = OpenAI(api_key=OPENAI_API_KEY)

elevenlabs_client = ElevenLabs(api_key=ELEVENLABS_API_KEY)

# FIX 819: LLM Client Adapter (soporte OpenAI + Anthropic)
from llm_client import llm_client

# Sistema de Prompt para Bruce
# Cargado desde archivo externo para mejor mantenibilidad
from prompts import obtener_system_prompt
SYSTEM_PROMPT = obtener_system_prompt()

def convertir_numeros_escritos_a_digitos(texto: str) -> str:
    """
    Convierte números escritos en palabras a dígitos

    Ejemplos:
        "seis seis veintitrés 53 41 8" → "66 23 53 41 8"
        "tres tres uno dos" → "33 12"
        "sesenta y seis" → "66"
        "treinta y uno" → "31"
        "100 veintiuno" → "121" (FIX 331)
        "cien veintiuno" → "121" (FIX 331)
    """
    import re

    texto_convertido = texto.lower()

    # FIX 331: Convertir "100 veintiuno" → "121", "100 veintidos" → "122", etc.
    # Esto es común en México cuando dicen números de 3 dígitos como "cien veintiuno"
    # El patrón es: 100/cien/ciento + número del 1-99
    patrones_cien = {
        # 100 + veintiX = 12X
        '100 veintiuno': '121', '100 veintidos': '122', '100 veintidós': '122',
        '100 veintitrés': '123', '100 veintitres': '123', '100 veinticuatro': '124',
        '100 veinticinco': '125', '100 veintiséis': '126', '100 veintiseis': '126',
        '100 veintisiete': '127', '100 veintiocho': '128', '100 veintinueve': '129',
        # cien + veintiX = 12X
        'cien veintiuno': '121', 'cien veintidos': '122', 'cien veintidós': '122',
        'cien veintitrés': '123', 'cien veintitres': '123', 'cien veinticuatro': '124',
        'cien veinticinco': '125', 'cien veintiséis': '126', 'cien veintiseis': '126',
        'cien veintisiete': '127', 'cien veintiocho': '128', 'cien veintinueve': '129',
        # ciento + veintiX = 12X
        'ciento veintiuno': '121', 'ciento veintidos': '122', 'ciento veintidós': '122',
        'ciento veintitrés': '123', 'ciento veintitres': '123', 'ciento veinticuatro': '124',
        'ciento veinticinco': '125', 'ciento veintiséis': '126', 'ciento veintiseis': '126',
        'ciento veintisiete': '127', 'ciento veintiocho': '128', 'ciento veintinueve': '129',
        # 100/cien + diez a diecinueve = 11X
        '100 diez': '110', '100 once': '111', '100 doce': '112', '100 trece': '113',
        '100 catorce': '114', '100 quince': '115', '100 dieciséis': '116', '100 dieciseis': '116',
        '100 diecisiete': '117', '100 dieciocho': '118', '100 diecinueve': '119',
        'cien diez': '110', 'cien once': '111', 'cien doce': '112', 'cien trece': '113',
        'cien catorce': '114', 'cien quince': '115', 'cien dieciséis': '116', 'cien dieciseis': '116',
        'cien diecisiete': '117', 'cien dieciocho': '118', 'cien diecinueve': '119',
        # 100/cien + treinta a noventa = 13X-19X
        '100 treinta': '130', '100 cuarenta': '140', '100 cincuenta': '150',
        '100 sesenta': '160', '100 setenta': '170', '100 ochenta': '180', '100 noventa': '190',
        'cien treinta': '130', 'cien cuarenta': '140', 'cien cincuenta': '150',
        'cien sesenta': '160', 'cien setenta': '170', 'cien ochenta': '180', 'cien noventa': '190',
        # 100/cien + unidades simples = 10X
        '100 uno': '101', '100 dos': '102', '100 tres': '103', '100 cuatro': '104',
        '100 cinco': '105', '100 seis': '106', '100 siete': '107', '100 ocho': '108', '100 nueve': '109',
        'cien uno': '101', 'cien dos': '102', 'cien tres': '103', 'cien cuatro': '104',
        'cien cinco': '105', 'cien seis': '106', 'cien siete': '107', 'cien ocho': '108', 'cien nueve': '109',
        # Variantes sin espacio (a veces Deepgram las transcribe así)
        '100veintiuno': '121', '100veintidos': '122', '100veintitres': '123',
        '100veinticuatro': '124', '100veinticinco': '125', '100veintiseis': '126',
        '100veintisiete': '127', '100veintiocho': '128', '100veintinueve': '129',
        # ciento + treinta y uno, etc. = 13X
        'ciento treinta y uno': '131', 'ciento treinta y dos': '132', 'ciento treinta y tres': '133',
        'ciento treinta y cuatro': '134', 'ciento treinta y cinco': '135', 'ciento treinta y seis': '136',
        'ciento treinta y siete': '137', 'ciento treinta y ocho': '138', 'ciento treinta y nueve': '139',
        'ciento cuarenta y uno': '141', 'ciento cuarenta y dos': '142', 'ciento cuarenta y tres': '143',
        'ciento cincuenta y uno': '151', 'ciento cincuenta y dos': '152', 'ciento cincuenta y tres': '153',
    }

    for patron, digitos in patrones_cien.items():
        texto_convertido = texto_convertido.replace(patron, digitos)

    # FIX 331: También convertir "cien" suelto a "100" si no se convirtió antes
    # Esto es para casos como "9 6 1 cien 21" donde "cien" queda suelto
    texto_convertido = texto_convertido.replace(' cien ', ' 100 ')
    texto_convertido = texto_convertido.replace(' ciento ', ' 100 ')

    # FIX 276: Primero convertir números compuestos "treinta y uno" → "31"
    # Patrón: decena + "y" + unidad
    compuestos = {
        'treinta y uno': '31', 'treinta y dos': '32', 'treinta y tres': '33',
        'treinta y cuatro': '34', 'treinta y cinco': '35', 'treinta y seis': '36',
        'treinta y siete': '37', 'treinta y ocho': '38', 'treinta y nueve': '39',
        'cuarenta y uno': '41', 'cuarenta y dos': '42', 'cuarenta y tres': '43',
        'cuarenta y cuatro': '44', 'cuarenta y cinco': '45', 'cuarenta y seis': '46',
        'cuarenta y siete': '47', 'cuarenta y ocho': '48', 'cuarenta y nueve': '49',
        'cincuenta y uno': '51', 'cincuenta y dos': '52', 'cincuenta y tres': '53',
        'cincuenta y cuatro': '54', 'cincuenta y cinco': '55', 'cincuenta y seis': '56',
        'cincuenta y siete': '57', 'cincuenta y ocho': '58', 'cincuenta y nueve': '59',
        'sesenta y uno': '61', 'sesenta y dos': '62', 'sesenta y tres': '63',
        'sesenta y cuatro': '64', 'sesenta y cinco': '65', 'sesenta y seis': '66',
        'sesenta y siete': '67', 'sesenta y ocho': '68', 'sesenta y nueve': '69',
        'setenta y uno': '71', 'setenta y dos': '72', 'setenta y tres': '73',
        'setenta y cuatro': '74', 'setenta y cinco': '75', 'setenta y seis': '76',
        'setenta y siete': '77', 'setenta y ocho': '78', 'setenta y nueve': '79',
        'ochenta y uno': '81', 'ochenta y dos': '82', 'ochenta y tres': '83',
        'ochenta y cuatro': '84', 'ochenta y cinco': '85', 'ochenta y seis': '86',
        'ochenta y siete': '87', 'ochenta y ocho': '88', 'ochenta y nueve': '89',
        'noventa y uno': '91', 'noventa y dos': '92', 'noventa y tres': '93',
        'noventa y cuatro': '94', 'noventa y cinco': '95', 'noventa y seis': '96',
        'noventa y siete': '97', 'noventa y ocho': '98', 'noventa y nueve': '99',
    }

    for compuesto, digito in compuestos.items():
        texto_convertido = texto_convertido.replace(compuesto, digito)

    # Mapeo de palabras a dígitos
    numeros_palabras = {
        # Números del 0-9
        'cero': '0', 'uno': '1', 'dos': '2', 'tres': '3', 'cuatro': '4',
        'cinco': '5', 'seis': '6', 'siete': '7', 'ocho': '8', 'nueve': '9',

        # Números 10-19
        'diez': '10', 'once': '11', 'doce': '12', 'trece': '13', 'catorce': '14',
        'quince': '15', 'dieciséis': '16', 'dieciseis': '16', 'diecisiete': '17',
        'dieciocho': '18', 'diecinueve': '19',

        # Decenas 20-90
        'veinte': '20', 'veintiuno': '21', 'veintidos': '22', 'veintidós': '22',
        'veintitrés': '23', 'veintitres': '23', 'veinticuatro': '24', 'veinticinco': '25',
        'veintiséis': '26', 'veintiseis': '26', 'veintisiete': '27', 'veintiocho': '28',
        'veintinueve': '29',
        'treinta': '30', 'cuarenta': '40', 'cincuenta': '50',
        'sesenta': '60', 'setenta': '70', 'ochenta': '80', 'noventa': '90'
    }

    # FIX 794: Reemplazar palabras más largas PRIMERO para evitar
    # que "ocho" dentro de "dieciocho" se reemplace antes → "dieci8"
    for palabra, digito in sorted(numeros_palabras.items(), key=lambda x: len(x[0]), reverse=True):
        texto_convertido = texto_convertido.replace(palabra, digito)

    return texto_convertido


def detectar_numeros_en_grupos(texto: str) -> bool:
    """
    Detecta si el cliente está dando números en pares o grupos de 2-3 dígitos
    en lugar de dígito por dígito.

    Ejemplos que detecta:
        "66 23 53 41 85" → True (pares)
        "662 353 418" → True (grupos de 3)
        "veintitres cincuenta y tres" → True (números de 2 dígitos)
        "seis seis dos tres cinco tres" → False (dígito por dígito)

    Returns:
        True si detecta números en grupos/pares
    """
    import re

    texto_lower = texto.lower()

    # Detectar números de 2 dígitos escritos juntos: "23", "53", "41", etc.
    # Patrón: al menos 3 grupos de 2 dígitos seguidos
    if len(re.findall(r'\b\d{2}\b', texto)) >= 3:
        return True

    # Detectar números de 3 dígitos: "662", "353", "418"
    if len(re.findall(r'\b\d{3}\b', texto)) >= 2:
        return True

    # Detectar palabras de números compuestos (10-99)
    palabras_compuestas = [
        'diez', 'once', 'doce', 'trece', 'catorce', 'quince',
        'dieciséis', 'dieciseis', 'diecisiete', 'dieciocho', 'diecinueve',
        'veinte', 'veintiuno', 'veintidos', 'veintidós', 'veintitrés', 'veintitres',
        'veinticuatro', 'veinticinco', 'veintiséis', 'veintiseis', 'veintisiete',
        'veintiocho', 'veintinueve', 'treinta', 'cuarenta', 'cincuenta',
        'sesenta', 'setenta', 'ochenta', 'noventa'
    ]

    # Si hay 3 o más palabras compuestas, probablemente está en grupos
    contador = sum(1 for palabra in palabras_compuestas if palabra in texto_lower)
    if contador >= 3:
        return True

    return False


class AgenteVentas:
    """Agente de ventas con GPT-4o y ElevenLabs + Integración Google Sheets"""

    def __init__(self, contacto_info: dict = None, sheets_manager=None, resultados_manager=None, whatsapp_validator=None):
        """
        Inicializa el agente de ventas

        Args:
            contacto_info: Información del contacto a llamar (desde Google Sheets)
            sheets_manager: Instancia de NiovalSheetsAdapter (para leer contactos)
            resultados_manager: Instancia de ResultadosSheetsAdapter (para guardar resultados)
            whatsapp_validator: Instancia de WhatsAppValidator
        """
        self.conversation_history = []
        self.contacto_info = contacto_info or {}
        self.sheets_manager = sheets_manager
        self.resultados_manager = resultados_manager
        self.whatsapp_validator = whatsapp_validator
        self.respuestas_vacias_consecutivas = 0  # Contador para detectar cuelgue
        self.acaba_de_responder_desesperado = False  # FIX 143: Flag para no pedir repetición después de confirmar presencia
        self.esperando_transferencia = False  # FIX 170: Flag cuando cliente va a pasar al encargado
        self.segunda_parte_saludo_dicha = False  # FIX 201: Flag para evitar repetir segunda parte del saludo
        self.detector_ivr = DetectorIVR()  # FIX 202: Detector de sistemas IVR/contestadoras automáticas
        self.timeouts_deepgram = 0  # FIX 408: Contador de timeouts de Deepgram (máximo 2 pedidos de repetición)
        self.gpt_timeouts_consecutivos = 0  # FIX 682: Contador de GPT timeouts consecutivos

        # FIX 481 (AUDITORIA W04): Sistema de recuperación de errores
        self.intentos_recuperacion = 0  # Contador de intentos de recuperación (max 3)
        self.ultimo_error_detectado = None  # Tipo de error que se está recuperando

        # FIX 482 (AUDITORIA W04): Sistema de métricas e instrumentación
        self.metrics = MetricsLogger()

        # FIX 522 BRUCE1659: Flag para evitar repetir oferta de catálogo
        self.catalogo_prometido = False  # True cuando Bruce ya dijo "le envío el catálogo"
        self.numero_parcial_recibido = None  # Guardar número parcial para pedir completo

        # FIX 526 BRUCE1677: Flag para cuando Bruce pregunta por hora de callback
        self.esperando_hora_callback = False  # True cuando Bruce preguntó "¿A qué hora...?"

        # FIX 535: Flag para prevenir pérdida de contexto después de silencios
        # Una vez que Bruce avanza de INICIO, NUNCA volver a responder "Hola, buen día"
        self.conversacion_iniciada = False  # True una vez que Bruce ha dicho algo más que saludo

        # FIX 339: Estado de conversación para evitar respuestas incoherentes
        self.estado_conversacion = EstadoConversacion.INICIO
        self.estado_anterior = None  # Para tracking de transiciones

        # FIX 552: Estado de flujo de email/correo (previene repeticiones durante dictado)
        self.estado_email = EstadoEmail.INICIAL
        # FIX 561: Counter anti-repetición REGRESO_DE_ESPERA
        self.regreso_espera_count = 0
        # FIX 565: Tracking silencio de Bruce
        self.bruce_silence_start = None
        self.bruce_silence_fallback_count = 0  # FIX 565: Limitar fallbacks a 2 máximo
        # FIX 559: Flag encargado ya confirmado (previene re-disparo del pitch)
        self.encargado_confirmado = False
        # FIX 571: Flag dictado de dígitos activo
        self.digitos_acumulados_flag = False

        # FIX 778: Exponer openai_client como atributo de instancia para GPT_NARROW
        self.openai_client = openai_client

        # FSM Engine - Motor determinista (shadow mode por defecto)
        self.fsm = None
        try:
            from fsm_engine import FSMEngine, FSM_ENABLED
            if FSM_ENABLED != "false":
                self.fsm = FSMEngine()
                print(f"  [FSM] Inicializado en modo: {FSM_ENABLED}")
        except ImportError:
            pass  # FSM no disponible, usar lógica existente

        # FIX 762+765+766: Diccionario para conversión de números verbales a dígitos
        self._nums_to_digit_762 = {
            'cero': '0', 'uno': '1', 'una': '1', 'dos': '2', 'tres': '3',
            'cuatro': '4', 'cinco': '5', 'seis': '6', 'siete': '7',
            'ocho': '8', 'nueve': '9', 'diez': '10',
        }

        # Datos del lead que se van capturando durante la llamada
        self.lead_data = {
            "contacto_id": (contacto_info.get('fila') or contacto_info.get('ID')) if contacto_info else None,
            "nombre_contacto": "",
            "nombre_negocio": contacto_info.get('nombre_negocio', contacto_info.get('Nombre Negocio', '')) if contacto_info else "",
            "telefono": contacto_info.get('telefono', contacto_info.get('Teléfono', '')) if contacto_info else "",
            "email": "",
            "whatsapp": "",
            "whatsapp_valido": False,
            "ciudad": contacto_info.get('ciudad', contacto_info.get('Ciudad', '')) if contacto_info else "",
            "categorias_interes": "",
            "productos_interes": "",
            "nivel_interes": "bajo",
            "temperatura": "frío",
            "objeciones": [],
            "notas": "",
            "fecha_inicio": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "duracion_segundos": 0,
            "interesado": False,
            "estado_llamada": "Respondio",  # Respondio/Buzon/Telefono Incorrecto/Colgo/No Respondio

            # Formulario de 7 preguntas (captura automática durante conversación)
            "pregunta_0": "Respondio",  # Estado de llamada (automático)
            "pregunta_1": "",  # Necesidades (opciones múltiples separadas por coma)
            "pregunta_2": "",  # Toma decisiones (Sí/No)
            "pregunta_3": "",  # Pedido inicial (Crear Pedido/No)
            "pregunta_4": "",  # Pedido muestra (Sí/No)
            "pregunta_5": "",  # Compromiso fecha (Sí/No/Tal vez)
            "pregunta_6": "",  # Método pago TDC (Sí/No/Tal vez)
            "pregunta_7": "",  # Conclusión (Pedido/Revisara/Correo/etc.) - Automático
            "resultado": "",  # APROBADO/NEGADO

            # Análisis post-llamada (Columna V y W)
            "nivel_interes_clasificado": "",  # Alto/Medio/Bajo - Columna V
            "opinion_bruce": "",  # Autoevaluación de Bruce - Columna W
            "estado_animo_cliente": "",  # Positivo/Neutral/Negativo (interno)
        }

        # Metadatos de la llamada
        self.call_sid = None
        self.fecha_reprogramacion = None
        self.hora_preferida = None
        self.motivo_no_contacto = None

        # Contador para alternar frases de relleno (hace la conversación más natural)
        self.indice_frase_relleno = 0

        # FIX 699: Memory Layer - Capa de memoria conversacional
        try:
            if MEMORY_LAYER_DISPONIBLE:
                self.memory = ConversationMemory()
            else:
                self.memory = None
        except Exception as e_mem:
            print(f"   [WARN] FIX 699: Error inicializando Memory Layer: {e_mem}")
            self.memory = None

        # FIX 700: Speech Processor - Máquina de estados para speech
        try:
            if SPEECH_PROCESSOR_DISPONIBLE:
                self.speech = SpeechStateMachine()
            else:
                self.speech = None
        except Exception as e_sp:
            print(f"   [WARN] FIX 700: Error inicializando Speech Processor: {e_sp}")
            self.speech = None

        # FIX 701: Intent Classifier - Clasificador centralizado de intenciones
        try:
            if INTENT_CLASSIFIER_DISPONIBLE:
                self.classifier = IntentClassifier()
            else:
                self.classifier = None
        except Exception as e_ic:
            print(f"   [WARN] FIX 701: Error inicializando Intent Classifier: {e_ic}")
            self.classifier = None

    # [EMOJI]
    # FIX 491: SISTEMA DE CONTEXTO DINÁMICO
    # [EMOJI]

    def _detectar_fase_actual(self):
        """
        Detecta en qué fase de conversación está Bruce.

        FIX 491: Sistema de detección de fases para contexto dinámico.

        Returns:
            str: "APERTURA", "CALIFICACION", "CAPTURA", o "CIERRE"
        """
        mensajes_count = len(self.conversation_history)

        # Fase 1: APERTURA (primeros 2 mensajes)
        if mensajes_count <= 2:
            return "APERTURA"

        # Detectar si ya confirmó ser encargado
        es_encargado = False
        for msg in self.conversation_history:
            if msg['role'] == 'user':
                content_lower = msg['content'].lower()
                # Patrones de confirmación
                if any(frase in content_lower for frase in [
                    'soy yo', 'yo soy', 'sí soy', 'si soy', 'con él', 'con el', 'el mismo',
                    'servidor', 'a sus órdenes', 'a sus ordenes', 'yo me encargo',
                    'soy el encargado', 'soy la encargada', 'soy el dueño', 'soy la dueña',
                    'él habla', 'el habla', 'aquí él', 'aqui el', 'yo hablo'
                ]):
                    es_encargado = True
                    break

        # Fase 2: CALIFICACION (no sabemos si es encargado)
        if not es_encargado:
            return "CALIFICACION"

        # Fase 3: CAPTURA (es encargado pero falta contacto)
        # FIX 507b: Usar lead_data.get() para evitar AttributeError
        tiene_contacto = bool(self.lead_data.get("whatsapp") or self.lead_data.get("email"))
        if es_encargado and not tiene_contacto:
            return "CAPTURA"

        # Fase 4: CIERRE (ya tiene contacto o rechazó)
        return "CIERRE"

    def _obtener_objetivo_fase(self, fase):
        """Retorna objetivo de la fase actual"""
        objetivos = {
            "APERTURA": "Saludar, presentarte como Bruce de NIOVAL, y preguntar por el encargado de compras",
            "CALIFICACION": "Confirmar si hablas con el encargado de compras o conseguir su contacto/horario",
            "CAPTURA": "Obtener WhatsApp (PRIORIDAD) o correo electrónico del encargado",
            "CIERRE": "Confirmar envío de catálogo en las próximas 2 horas y despedirte profesionalmente"
        }
        return objetivos.get(fase, "Continuar conversación")

    def _obtener_siguiente_accion(self, fase):
        """Retorna siguiente acción recomendada según fase"""
        acciones = {
            "APERTURA": "Preguntar: '¿Se encuentra el encargado de compras?'",
            "CALIFICACION": "Si es encargado → Pedir WhatsApp. Si no está → Pedir horario o transferencia",
            "CAPTURA": "Preguntar: '¿Su WhatsApp para enviar el catálogo?' (o correo si no tiene WhatsApp)",
            "CIERRE": "Confirmar: 'Le envío catálogo en las próximas 2 horas. Muchas gracias por su tiempo.'"
        }
        return acciones.get(fase, "Adaptarse al contexto del cliente")

    def _obtener_reglas_criticas_fase(self, fase):
        """Retorna recordatorio compacto de reglas para esta fase"""
        reglas = {
            "APERTURA": "Saludo variado → Presentación NIOVAL → Preguntar encargado (máx 20 palabras)",
            "CALIFICACION": "Si confirma ser encargado → CAPTURA | Si no está → horario/transferencia (máx 20 palabras)",
            "CAPTURA": "WhatsApp PRIMERO → Correo solo si no tiene | NO repetir número en voz | NO preguntar nombre (máx 20 palabras)",
            "CIERRE": "'En 2 horas' (NUNCA 'ahorita') → Agradecer → Si se despide, despedirse SIN más preguntas"
        }
        return reglas.get(fase, "")

    def _detectar_objeciones_activas(self):
        """
        Detecta objeciones mencionadas recientemente.

        Returns:
            list: Lista de objeciones detectadas
        """
        if len(self.conversation_history) < 2:
            return []

        # Analizar últimos 6 mensajes (3 turnos)
        ultimos_mensajes = self.conversation_history[-6:]
        contexto = " ".join([m['content'] for m in ultimos_mensajes]).lower()

        objeciones = []

        # Objeción: PRECIO
        if any(palabra in contexto for palabra in [
            'cuánto cuesta', 'cuanto cuesta', 'qué precio', 'que precio',
            'dame precio', 'cuánto sale', 'cuanto sale', 'muy caro', 'costoso',
            'pedido mínimo', 'pedido minimo', 'cuánto tengo', 'cuanto tengo'
        ]):
            objeciones.append("PRECIO")

        # Objeción: OCUPADO
        if any(palabra in contexto for palabra in [
            'estoy ocupado', 'estoy ocupada', 'tengo prisa', 'rápido por favor',
            'rapido por favor', 'estoy atendiendo', 'no tengo tiempo'
        ]):
            objeciones.append("OCUPADO")

        # Objeción: YA TIENE PROVEEDOR
        if any(palabra in contexto for palabra in [
            'ya tenemos proveedor', 'ya tengo proveedor', 'ya trabajo con',
            'ya compro con', 'estoy contento con', 'no necesito otro'
        ]):
            objeciones.append("PROVEEDOR")

        # Objeción: NO CONFÍA
        if any(palabra in contexto for palabra in [
            'no me da confianza', 'no da confianza', 'cómo sé que', 'como se que',
            'miedo de fraude', 'miedo a fraude', 'pago y no llega', 'son de confianza'
        ]):
            objeciones.append("CONFIANZA")

        return objeciones

    def _generar_recordatorio_objeciones(self, objeciones):
        """Genera recordatorio compacto para objeciones detectadas"""
        if not objeciones:
            return ""

        texto = "\n[WARN] OBJECIONES DETECTADAS: " + ", ".join(objeciones) + "\n"

        recordatorios = {
            "PRECIO": "→ NO inventar precios | Redirigir a catálogo | Si 'caro' → promoción $1,500",
            "OCUPADO": "→ Respuestas 3-5 palabras | Directo al punto | Sin explicaciones",
            "PROVEEDOR": "→ Posicionar como PLAN B | 'para cuando no tenga stock'",
            "CONFIANZA": "→ Ofrecer pedido prueba $1,500 | Pago contra entrega | Número verificable"
        }

        for objecion in objeciones:
            texto += recordatorios.get(objecion, "") + "\n"

        return texto

    def _generar_contexto_dinamico(self):
        """
        Genera contexto dinámico que se AGREGA al prompt original.

        FIX 491: NO reemplaza nada del prompt original (mantiene variaciones léxicas).
        Solo añade resumen de conversación actual + recordatorios focalizados.

        Returns:
            str: Contexto dinámico (100-150 líneas)
        """
        fase = self._detectar_fase_actual()
        objeciones = self._detectar_objeciones_activas()

        # Formatear datos capturados
        # FIX 507: BRUCE1492 - Usar lead_data.get() para evitar AttributeError
        nombre_enc = self.lead_data.get("nombre_encargado", "") or "NO CAPTURADO"
        whatsapp = self.lead_data.get("whatsapp", "") or "NO CAPTURADO"
        correo = self.lead_data.get("email", "") or "NO CAPTURADO"

        # Construir contexto compacto
        contexto = f"""

[EMOJI]
[EMOJI] CONTEXTO DINÁMICO - LLAMADA ACTUAL (FIX 491)
[EMOJI]

NEGOCIO: {self.lead_data.get("nombre_negocio", "N/A")} | CIUDAD: {self.lead_data.get("ciudad", "N/A")} | TEL: {self.lead_data.get("telefono", "N/A")}

DATOS CAPTURADOS:
• Nombre: {nombre_enc} | WhatsApp: {whatsapp} | Correo: {correo}

[EMOJI] CRÍTICO: NO REPETIR PREGUNTAS POR DATOS YA CAPTURADOS
Si un dato tiene valor (no dice "NO CAPTURADO"), YA LO TIENES. No preguntar de nuevo.

[EMOJI]
[EMOJI] FASE: {fase} | OBJETIVO: {self._obtener_objetivo_fase(fase)}
[EMOJI]

SIGUIENTE ACCIÓN: {self._obtener_siguiente_accion(fase)}

REGLAS CLAVE FASE: {self._obtener_reglas_criticas_fase(fase)}
{self._generar_recordatorio_objeciones(objeciones)}
[EMOJI]
FIN CONTEXTO DINÁMICO - Reglas completas ya proporcionadas arriba
[EMOJI]
"""

        return contexto

    def _actualizar_estado_conversacion(self, mensaje_cliente: str, respuesta_bruce: str = None) -> bool:
        """
        FIX 339: Actualiza el estado de la conversación basándose en el mensaje del cliente
        y opcionalmente en la respuesta de Bruce.

        Returns:
            bool: True si debe continuar procesando, False si debe detener (ej: problema de audio)

        Esto permite que los filtros sepan en qué contexto están y eviten respuestas incoherentes.
        """
        import re

        mensaje_lower = mensaje_cliente.lower()
        self.estado_anterior = self.estado_conversacion

        # Detectar si cliente está dictando número (contiene 3+ dígitos)
        digitos_encontrados = re.findall(r'\d', mensaje_lower)
        if len(digitos_encontrados) >= 3:
            # Si estábamos pidiendo WhatsApp o hay números, está dictando
            if self.estado_conversacion in [EstadoConversacion.PIDIENDO_WHATSAPP, EstadoConversacion.PIDIENDO_CORREO]:
                self.estado_conversacion = EstadoConversacion.DICTANDO_NUMERO
                print(f"[EMOJI] FIX 339: Estado → DICTANDO_NUMERO (cliente dictando: {len(digitos_encontrados)} dígitos)")
                # FIX 435: Retornar True (no None) - estado válido donde Bruce espera dictado completo
                return True

        # Detectar si cliente está dictando correo (contiene @ o "arroba")
        if '@' in mensaje_lower or 'arroba' in mensaje_lower or 'punto com' in mensaje_lower:
            self.estado_conversacion = EstadoConversacion.DICTANDO_CORREO
            print(f"[EMOJI] FIX 339: Estado → DICTANDO_CORREO")
            # FIX 435: Retornar True (no None) - estado válido donde Bruce espera dictado completo
            return True

        # FIX 389/396/399: Detectar persona nueva después de transferencia
        # Si estábamos esperando transferencia Y cliente dice "bueno"/"dígame"/etc. → Persona nueva
        if self.estado_conversacion == EstadoConversacion.ESPERANDO_TRANSFERENCIA:
            # FIX 399: Si cliente hace PREGUNTA DIRECTA, salir de ESPERANDO_TRANSFERENCIA
            # Caso BRUCE1131: "¿De dónde dice que habla?" = Cliente preguntando, NO transferencia
            preguntas_directas_salir = [
                '¿de dónde', '¿de donde', 'de dónde', 'de donde',
                '¿quién habla', '¿quien habla', 'quién habla', 'quien habla',
                '¿quién es', '¿quien es', 'quién es', 'quien es',
                '¿qué empresa', '¿que empresa', 'qué empresa', 'que empresa',
                '¿cómo dijo', '¿como dijo', 'cómo dijo', 'como dijo',
                '¿me repite', 'me repite', '¿puede repetir', 'puede repetir',
                '¿qué dice', '¿que dice', 'qué dice', 'que dice'
            ]

            es_pregunta_directa = any(preg in mensaje_lower for preg in preguntas_directas_salir)

            if es_pregunta_directa:
                # Salir de ESPERANDO_TRANSFERENCIA - cliente pregunta directamente a Bruce
                print(f"[EMOJI] FIX 399: Cliente hace PREGUNTA DIRECTA - Saliendo de ESPERANDO_TRANSFERENCIA")
                print(f"   Mensaje: '{mensaje_cliente}' - GPT responderá")
                self.estado_conversacion = EstadoConversacion.BUSCANDO_ENCARGADO
                # NO retornar aquí - dejar que GPT responda la pregunta
            else:
                saludos_persona_nueva = ['bueno', 'hola', 'sí', 'si', 'dígame', 'digame',
                                         'mande', 'a ver', 'qué pasó', 'que paso', 'alo', 'aló']

                # Verificar si es un saludo simple (persona nueva contestando)
                mensaje_stripped = mensaje_lower.strip().strip('?').strip('¿')
                es_saludo_nuevo = any(mensaje_stripped == s or mensaje_stripped.startswith(s + ' ') for s in saludos_persona_nueva)

                if es_saludo_nuevo:
                    # FIX 396: Persona nueva detectada - RE-PRESENTARSE INMEDIATAMENTE
                    # NO dejar que GPT maneje, porque malinterpreta "¿Bueno?" como confirmación
                    self.estado_conversacion = EstadoConversacion.BUSCANDO_ENCARGADO
                    print(f"[EMOJI] FIX 389/396: Persona nueva después de transferencia - RE-PRESENTANDO")
                    print(f"   Cliente dijo: '{mensaje_cliente}' - Bruce se presenta nuevamente")
                    # Retornar presentación inmediata
                    return "Me comunico de la marca NIOVAL para ofrecer información de nuestros productos de ferretería. ¿Se encontrará el encargado o encargada de compras?"

        # FIX 394/395/446: Detectar "¿En qué le puedo apoyar?" como ENCARGADO DISPONIBLE
        # Cliente pregunta "¿En qué le apoyo?" = ES EL ENCARGADO y está disponible
        # NO debe preguntar por el encargado, debe ofrecer catálogo DIRECTAMENTE
        # FIX 446: Lista ampliada con más variantes
        patrones_encargado_disponible = [
            # Ofreciendo ayuda
            '¿en qué le puedo apoyar', '¿en que le puedo apoyar',
            '¿en qué le apoyo', '¿en que le apoyo',
            '¿en qué puedo ayudar', '¿en que puedo ayudar',
            '¿en qué puedo servirle', '¿en que puedo servirle',
            'en qué le puedo apoyar', 'en que le puedo apoyar',
            'en qué le apoyo', 'en que le apoyo',
            '¿qué necesita', '¿que necesita',
            '¿para qué llama', '¿para que llama',
            '¿qué ocupa', '¿que ocupa',
            # FIX 446: Más variantes de ofrecimiento
            '¿qué se le ofrece', '¿que se le ofrece',
            '¿qué desea', '¿que desea', '¿qué busca', '¿que busca',
            'para servirle', 'a sus órdenes', 'a sus ordenes',
            'a la orden', 'dígame', 'digame', 'mande usted',
            'servidor', 'servidora', 'presente',
            # FIX 395: Agregar "con él/ella habla" (caso BRUCE1122)
            'con ella habla', 'con él habla', 'con el habla',
            'sí, con ella', 'si, con ella', 'sí, con él', 'si, con él',
            'sí con ella', 'si con ella', 'sí con él', 'si con él',
            'ella habla', 'él habla', 'el habla',
            # Confirmando que es el encargado
            'yo soy', 'soy yo', 'soy la encargada', 'soy el encargado',
            # FIX 446: Más variantes de "soy yo"
            'yo mero', 'aquí mero', 'aqí mero', 'acá mero',
            'sí soy', 'si soy', 'sí soy yo', 'si soy yo',
            'yo soy la dueña', 'yo soy el dueño', 'soy el dueño', 'soy la dueña',
            'yo soy quien', 'yo me encargo', 'yo hago las compras',
            'conmigo', 'con un servidor', 'con una servidora',
            # FIX 446: Confirmando que SÍ está el encargado
            'sí está', 'si esta', 'sí se encuentra', 'si se encuentra',
            'aquí está', 'aqui esta', 'aquí se encuentra', 'aqui se encuentra',
            'sí lo tenemos', 'si lo tenemos', 'sí la tenemos', 'si la tenemos',
            'ya llegó', 'ya llego', 'acaba de llegar', 'ya está aquí', 'ya esta aqui'
        ]
        if any(p in mensaje_lower for p in patrones_encargado_disponible):
            print(f"[EMOJI] FIX 394/395: Cliente ES el encargado - ENCARGADO DISPONIBLE")
            print(f"   Detectado: '{mensaje_cliente}' - Ofreciendo catálogo DIRECTAMENTE")
            # Responder directamente sin preguntar por encargado
            return "Me comunico de la marca NIOVAL para ofrecer información de nuestros productos de ferretería. ¿Le gustaría recibir nuestro catálogo por WhatsApp o correo electrónico?"

        # FIX 405/413: PRIMERO detectar si es RECHAZO antes de detectar transferencia
        # Caso BRUCE1146: "No, ahorita no, muchas gracias" = RECHAZO, NO transferencia
        # FIX 413: Caso BRUCE1206: "No, no nos interesa ahorita, gracias" = RECHAZO, NO transferencia
        patrones_rechazo = [
            'no, ahorita no', 'no ahorita no',
            'no, gracias', 'no gracias',
            'no me interesa', 'no necesito',
            # FIX 413: Agregar variantes "nos/les/le interesa" (caso BRUCE1206)
            'no nos interesa', 'no les interesa', 'no le interesa',
            'no, no necesito', 'no no necesito',
            'estoy ocupado', 'estamos ocupados',
            'no tengo tiempo', 'no tiene tiempo',
            'no moleste', 'no llame más', 'no llame mas',
            'quite mi número', 'quite mi numero',
            'no vuelva a llamar', 'no vuelvan a llamar'
        ]

        # FIX 560: "Muchas gracias" = rechazo cortés SOLO si Bruce ya presentó (4+ mensajes)
        if len(self.conversation_history) >= 4:
            patrones_rechazo.extend([
                'muchas gracias', 'muchas gracias que tenga buen día',
                'muchas gracias que tenga buen dia',
                'gracias que tenga buen día', 'gracias que tenga buen dia',
                'gracias hasta luego', 'gracias, hasta luego',
                'no pues gracias', 'no, pues gracias',
            ])

        es_rechazo = any(rechazo in mensaje_lower for rechazo in patrones_rechazo)

        if es_rechazo:
            print(f"[EMOJI] FIX 405: Cliente RECHAZÓ (no es transferencia)")
            print(f"   Mensaje: '{mensaje_cliente}'")
            print(f"   Detectado patrón de rechazo - GPT manejará despedida")
            # NO activar ESPERANDO_TRANSFERENCIA - dejar que GPT maneje el rechazo
            # GPT debería despedirse cortésmente
        else:
            # Detectar si cliente pide esperar (SOLO si NO es rechazo)
            patrones_espera = ['permítame', 'permitame', 'permiso', 'con permiso',  # FIX 576
                              'espere', 'espéreme', 'espereme',
                              'un momento', 'un segundito', 'ahorita', 'tantito']
            if any(p in mensaje_lower for p in patrones_espera):
                # FIX 411: Verificar que NO sea solicitud de llamar después
                # Caso BRUCE1198: "Si gusta marcar en 5 minutos" = LLAMAR DESPUÉS, no transferencia
                solicita_llamar_despues = [
                    'marcar en', 'llamar en',  # "Si gusta marcar en 5 minutos"
                    'marcar más tarde', 'llamar más tarde', 'marcar mas tarde', 'llamar mas tarde',
                    'marcar después', 'llamar después', 'marcar despues', 'llamar despues',
                    'marcar luego', 'llamar luego',
                    'en 5 minutos', 'en un rato', 'en unos minutos',
                    'más tarde', 'más tardecito', 'al rato', 'mas tarde', 'mas tardecito',
                ]

                es_solicitud_llamar_despues = any(patron in mensaje_lower for patron in solicita_llamar_despues)

                if es_solicitud_llamar_despues:
                    # FIX 416: NO hacer return - permitir que se detecte ENCARGADO_NO_ESTA
                    # Caso BRUCE1215: "No, no está ahorita. Si quiere más tarde"
                    # Debe detectar AMBOS: 1) Llamar después 2) Encargado no está
                    print(f"[EMOJI] FIX 411/416: Cliente pide LLAMAR DESPUÉS (no transferencia)")
                    print(f"   Mensaje: '{mensaje_cliente}' - Continuando para detectar otros estados")
                    # NO activar ESPERANDO_TRANSFERENCIA - pero NO hacer return aún
                    # Continuar para detectar ENCARGADO_NO_ESTA u otros estados

                else:
                    # FIX 411: Verificar que NO sea solicitud de número de Bruce
                    # Caso BRUCE1198: "O si gusta dejarme algún número" = PIDE NÚMERO, no transferencia
                    pide_numero_bruce = [
                        'déjame un número', 'dejame un numero',
                        'déjame algún número', 'dejame algun numero',
                        'dame un número', 'dame un numero',
                        'tu número', 'su número', 'tu numero', 'su numero',
                        'tu teléfono', 'su teléfono', 'tu telefono', 'su telefono',
                        'tu whatsapp', 'su whatsapp',
                        'dejarme número', 'dejarme numero',
                        'dejarme algún', 'dejarme algun',
                    ]

                    cliente_pide_numero = any(patron in mensaje_lower for patron in pide_numero_bruce)

                    if cliente_pide_numero:
                        print(f"[EMOJI] FIX 411: Cliente PIDE NÚMERO de Bruce")
                        print(f"   Mensaje: '{mensaje_cliente}' - GPT debe dar WhatsApp")
                        # NO activar ESPERANDO_TRANSFERENCIA
                        return  # Dejar que GPT maneje

                    # FIX 411: Expandir preguntas directas (incluir NOMBRE)
                    # Caso BRUCE1199: "Permítame. ¿Cuál es tu nombre?" = PREGUNTA POR NOMBRE, no transferencia
                    preguntas_directas = [
                        '¿de dónde', '¿de donde', 'de dónde', 'de donde',
                        '¿quién habla', '¿quien habla', 'quién habla', 'quien habla',
                        '¿quién es', '¿quien es', 'quién es', 'quien es',
                        '¿qué empresa', '¿que empresa', 'qué empresa', 'que empresa',
                        '¿cómo dijo', '¿como dijo', 'cómo dijo', 'como dijo',
                        '¿me repite', 'me repite', '¿puede repetir', 'puede repetir',
                        '¿qué dice', '¿que dice', 'qué dice', 'que dice',
                        # FIX 411: Preguntas por NOMBRE (caso BRUCE1199)
                        '¿cuál es tu nombre', '¿cual es tu nombre', 'cuál es tu nombre', 'cual es tu nombre',
                        '¿cómo te llamas', '¿como te llamas', 'cómo te llamas', 'como te llamas',
                        '¿cuánto es tu nombre', '¿cuanto es tu nombre',  # Deepgram transcribe "cuál" como "cuánto"
                        '¿tu nombre', 'tu nombre',
                        '¿su nombre', 'su nombre',
                        '¿cómo se llama', '¿como se llama', 'cómo se llama', 'como se llama',
                        '¿cuál es su nombre', '¿cual es su nombre', 'cuál es su nombre', 'cual es su nombre',
                    ]

                    es_pregunta_directa = any(preg in mensaje_lower for preg in preguntas_directas)

                    if es_pregunta_directa:
                        print(f"[EMOJI] FIX 411: 'Permítame' detectado pero es PREGUNTA DIRECTA - NO es transferencia")
                        print(f"   Mensaje: '{mensaje_cliente}' - GPT debe responder la pregunta")
                        # NO activar ESPERANDO_TRANSFERENCIA
                        return  # Dejar que GPT maneje

                    # Verificar que NO sea negación ("no está ahorita") ni ocupado ("ahorita está ocupado")
                    # FIX 417: Agregar "ocupado" a las exclusiones (casos BRUCE1216, BRUCE1219)
                    if not any(neg in mensaje_lower for neg in ['no está', 'no esta', 'no se encuentra', 'ocupado', 'busy']):
                        self.estado_conversacion = EstadoConversacion.ESPERANDO_TRANSFERENCIA
                        print(f"[EMOJI] FIX 339/399/405/411/417: Estado → ESPERANDO_TRANSFERENCIA")
                        # FIX 435: Retornar True (no None) para que generar_respuesta() NO malinterprete como FIX 428
                        # Caso BRUCE1304: "ahorita le paso" → establecía ESPERANDO_TRANSFERENCIA
                        # pero return sin valor retornaba None → generar_respuesta() lo interpretaba como FIX 428 y colgaba
                        return True

        # Detectar si encargado no está
        # FIX 417: Agregar "ocupado" y "busy" (casos BRUCE1216, BRUCE1219)
        # FIX 425: Agregar variantes de errores de transcripción (caso BRUCE1251)
        patrones_no_esta = ['no está', 'no esta', 'no se encuentra',
                           # FIX 425: Error de transcripción común: "encuentre" en vez de "encuentra"
                           'no se encuentre',
                           'salió', 'salio',
                           'no hay', 'no lo encuentro', 'no los encuentro', 'no tiene horario',
                           # FIX 417: "Ocupado" = No disponible = Equivalente a "no está"
                           'está ocupado', 'esta ocupado', 'ocupado',
                           'está busy', 'esta busy', 'busy',
                           # FIX 425: Frases que indican "no está" (caso BRUCE1251: "anda en la comida")
                           'anda en la comida', 'anda comiendo', 'salió a comer', 'salio a comer',
                           'fue a comer', 'están comiendo', 'estan comiendo',
                           # FIX 471: BRUCE1415 - "No tengo" = No hay encargado
                           'no tengo', 'no tenemos', 'no contamos con', 'aquí no hay',
                           # FIX 642D: BRUCE2070 - "marcar más tarde" = encargado no disponible
                           'marcar más tarde', 'marcar mas tarde', 'llamar más tarde', 'llamar mas tarde',
                           'marque más tarde', 'marque mas tarde', 'llame más tarde', 'llame mas tarde',
                           'marcar después', 'marcar despues', 'llamar después', 'llamar despues']
        if any(p in mensaje_lower for p in patrones_no_esta):
            # FIX 747: BRUCE2386 - Check if client is ALSO dictating numbers
            # "Es que no estan ahorita. Es cuarenta y cuatro cuarenta"
            # First clause = encargado absent, second clause = phone number being dictated
            # If concurrent dictation detected, flag it for post-filter override
            _nums_747 = ['cero','uno','dos','tres','cuatro','cinco','seis','siete',
                'ocho','nueve','diez','once','doce','trece','catorce','quince',
                'veinte','treinta','cuarenta','cincuenta','sesenta','setenta','ochenta','noventa']
            _msg_norm_747 = mensaje_lower.replace('á','a').replace('é','e').replace('í','i').replace('ó','o').replace('ú','u')
            _nums_verbales_747 = sum(1 for p in _msg_norm_747.split() if p in _nums_747)
            import re as _re_747
            _digitos_747 = len(_re_747.findall(r'\d', mensaje_lower))
            if _nums_verbales_747 >= 2 or _digitos_747 >= 3:
                self.estado_conversacion = EstadoConversacion.ENCARGADO_NO_ESTA
                self._datos_parciales_en_no_esta_747 = True
                print(f"[OK] FIX 747: BRUCE2386 - ENCARGADO_NO_ESTA + dictado concurrente ({_nums_verbales_747} nums verbales, {_digitos_747} digitos)")
                return True
            self.estado_conversacion = EstadoConversacion.ENCARGADO_NO_ESTA
            print(f"[EMOJI] FIX 339/417/425: Estado → ENCARGADO_NO_ESTA")
            return True

        # FIX 427/446: Detectar cuando cliente dice "soy yo" (él ES el encargado)
        # Casos: BRUCE1290, BRUCE1293
        # Cliente dice "Soy yo" o "Yo soy el encargado" indicando que él es quien toma decisiones
        # FIX 446: Lista ampliada con más variantes
        patrones_soy_yo = [
            # Básicos
            'soy yo', 'yo soy', 'sí soy yo', 'si soy yo', 'sí soy', 'si soy',
            # Encargado/encargada
            'yo soy el encargado', 'soy el encargado', 'yo soy la encargada', 'soy la encargada',
            # Dueño/dueña
            'yo soy el dueño', 'soy el dueño', 'yo soy la dueña', 'soy la dueña',
            # Mexicanismos
            'yo mero', 'aquí mero', 'acá mero', 'mero mero',
            # Variantes de "conmigo"
            'conmigo', 'con un servidor', 'con una servidora',
            'a sus órdenes', 'a sus ordenes', 'para servirle',
            # Variantes de rol
            'yo me encargo', 'yo hago las compras', 'yo veo eso',
            'yo manejo', 'yo decido', 'yo atiendo', 'yo recibo',
            # Variantes "con él/ella habla"
            'con ella habla', 'con él habla', 'con el habla',
            'ella habla', 'él habla', 'el habla',
            # Respuestas afirmativas a "¿usted es el encargado?"
            'sí, yo soy', 'si, yo soy', 'sí yo soy', 'si yo soy',
            'sí, con él', 'si, con él', 'sí, con ella', 'si, con ella'
        ]
        if any(p in mensaje_lower for p in patrones_soy_yo):
            self.estado_conversacion = EstadoConversacion.ENCARGADO_PRESENTE
            print(f"[EMOJI] FIX 427: Cliente ES el encargado → Estado = ENCARGADO_PRESENTE")
            return True

        # FIX 428: Detectar problemas de comunicación (cliente no puede escuchar bien)
        # Caso: BRUCE1289, BRUCE1297 - Cliente dijo "¿bueno? ¿bueno?" repetidamente
        # Cliente repite frases indicando que no puede escuchar a Bruce
        # Patrones: "¿bueno?" múltiple, saludos repetidos, etc.
        palabras_problema_audio = mensaje_lower.split()

        # Contar repeticiones de "bueno"
        # FIX 433: CRÍTICO - Umbral aumentado de 2 a 5+ para evitar falsos positivos
        # Casos BRUCE1311, 1306, 1301: Bruce colgaba cuando cliente decía "¿bueno?" 2-3 veces
        # Mayoría de clientes SÍ estaban escuchando - solo es forma de contestar/hablar
        contador_bueno = mensaje_lower.count('¿bueno?') + mensaje_lower.count('bueno?') + mensaje_lower.count('¿bueno')
        if contador_bueno >= 5:
            print(f"[EMOJI] FIX 428/433: Cliente dice '¿bueno?' {contador_bueno} veces → Problema de audio REAL detectado")
            print(f"   → NO procesar con GPT - retornar False para que sistema de respuestas vacías maneje")
            # Retornar False para que generar_respuesta() retorne None
            # El sistema de respuestas vacías se encargará de colgar si continúa
            return False

        # FIX 433: DESHABILITADO - Detectar saludos repetidos causaba falsos positivos
        # Saludar 2 veces es normal, no indica problema de audio
        # saludos_simples = ['buen día', 'buen dia', 'buenas', 'buenos días', 'buenos dias']
        # frases_encontradas = [s for s in saludos_simples if mensaje_lower.count(s) >= 2]
        # if frases_encontradas:
        #     print(f"[EMOJI] FIX 428: Cliente repite saludo '{frases_encontradas[0]}' → Posible problema de audio")
        #     print(f"   → NO procesar con GPT - retornar False")
        #     return False

        # Detectar si ya capturamos contacto
        if self.lead_data.get("whatsapp") or self.lead_data.get("email"):
            self.estado_conversacion = EstadoConversacion.CONTACTO_CAPTURADO
            print(f"[EMOJI] FIX 339: Estado → CONTACTO_CAPTURADO")
            return True

        # Si la respuesta de Bruce pregunta por WhatsApp/correo
        if respuesta_bruce:
            respuesta_lower = respuesta_bruce.lower()
            if 'whatsapp' in respuesta_lower and '?' in respuesta_lower:
                self.estado_conversacion = EstadoConversacion.PIDIENDO_WHATSAPP
                print(f"[EMOJI] FIX 339: Estado → PIDIENDO_WHATSAPP")
            elif 'correo' in respuesta_lower and '?' in respuesta_lower:
                self.estado_conversacion = EstadoConversacion.PIDIENDO_CORREO
                print(f"[EMOJI] FIX 339: Estado → PIDIENDO_CORREO")
            elif 'encargado' in respuesta_lower and '?' in respuesta_lower:
                self.estado_conversacion = EstadoConversacion.BUSCANDO_ENCARGADO
                print(f"[EMOJI] FIX 339: Estado → BUSCANDO_ENCARGADO")

        # Continuar procesando normalmente
        return True

    def _cliente_esta_dictando(self) -> bool:
        """
        FIX 339: Verifica si el cliente está en proceso de dictar número o correo.
        Útil para saber si debemos esperar más tiempo antes de responder.
        """
        return self.estado_conversacion in [
            EstadoConversacion.DICTANDO_NUMERO,
            EstadoConversacion.DICTANDO_CORREO
        ]

    def _cliente_esta_dando_informacion(self, texto_cliente: str) -> bool:
        """
        FIX 477 (AUDITORIA W04): Detecta si cliente está ACTIVAMENTE dando información.
        Previene interrupciones cuando cliente dice números/correos parciales.

        Problema observado en BRUCE1406:
        - Cliente: "9 51. 9 51," (empezando a dar número)
        - Bruce interrumpe: "¿Me puede dar el número del encargado?" [ERROR]

        Returns:
            True si cliente está dando información AHORA, False si no
        """
        import re
        texto_lower = texto_cliente.lower().strip()

        # FIX 571: Si dígitos están siendo acumulados (FIX 502 en servidor), forzar silencio
        if getattr(self, 'digitos_acumulados_flag', False):
            print(f"   [DEBUG] FIX 571: Dígitos acumulándose (FIX 502) - forzar silencio")
            return True

        # FIX 553: BRUCE1893 - NO pausar si hay pregunta directa o negocio no apto
        # Problema: Cliente dijo "sí, aquí es un taller mecánico. ¿Qué quiere?" y Bruce NO respondió
        # FIX 477 pausó porque detectó que terminaba con "o", pero había pregunta directa después

        # VERIFICAR 1: ¿Hay pregunta directa en el texto?
        preguntas_directas = ["¿qué quiere?", "¿qué se le ofrece?", "¿de qué se trata?", "¿qué necesita?"]
        tiene_pregunta_directa = any(pregunta in texto_lower for pregunta in preguntas_directas)
        if tiene_pregunta_directa:
            print(f"   [DEBUG] FIX 553: Pregunta directa detectada - NO pausar")
            return False  # NO pausar, responder la pregunta

        # VERIFICAR 2: ¿Es negocio no apto para ferreterías?
        negocios_no_aptos = [
            "taller mecánico", "taller automotriz", "taller de autos",
            "hospital", "clínica", "consultorio",
            "escuela", "primaria", "secundaria", "preparatoria",
            "restaurante", "café", "cafetería"
        ]
        es_negocio_no_apto = any(negocio in texto_lower for negocio in negocios_no_aptos)
        if es_negocio_no_apto:
            print(f"   [DEBUG] FIX 553: Negocio no apto detectado - NO pausar")
            return False  # NO pausar, Bruce debe responder/despedirse

        # FIX 526 BRUCE1677: Si Bruce preguntó por HORA, los números son hora, no teléfono
        if self.esperando_hora_callback:
            print(f"   [DEBUG] FIX 526: esperando_hora_callback=True - NO interpretar números como teléfono")
            return False  # No está dictando teléfono, está dando hora

        # 1. NÚMEROS PARCIALES (típicamente WhatsApp/teléfono)
        # Patrones: "9 51", "662 415", "tres tres dos"
        digitos = re.findall(r'\d', texto_cliente)
        if len(digitos) >= 2 and len(digitos) < 10:
            # FIX 758: BRUCE2431 - Excluir dígitos en contexto temporal
            # "Llega como en 30 minutos" → "30" es tiempo, NOT teléfono
            # Solo si pocos dígitos (<=3) Y hay palabra de tiempo adyacente
            _time_match_758 = re.search(r'\b\d{1,3}\s*(minuto|hora|dia|día|semana|rato|segundo|mes)', texto_lower)
            if _time_match_758 and len(digitos) <= 3:
                print(f"   [DEBUG] FIX 758: Dígitos en contexto temporal ('{_time_match_758.group()}') - NO es teléfono")
                return False
            # Tiene 2-9 dígitos (incompleto para número mexicano de 10)
            # Probablemente está dictando número
            print(f"   [DEBUG] FIX 477: DETECTADO número parcial ({len(digitos)} dígitos) - Cliente probablemente sigue dictando")
            return True

        # 2. DELETREO DE CORREO (palabras clave)
        palabras_deletreo_correo = [
            "arroba", "@", "punto com", "punto mx", "punto net",
            "gmail", "hotmail", "outlook", "yahoo"
        ]
        # FIX 527: BRUCE1776 - Deletreo fonético más específico
        # Problema: "a de" coincidía con "segurA DE 9" en frases de horario
        # Solución: Buscar patrón " X de " donde X es una letra sola
        import re
        deletreo_fonetico = re.search(r'\b[a-z] de [a-z]', texto_lower)  # "a de avión", "m de mamá"

        if any(p in texto_lower for p in palabras_deletreo_correo) or deletreo_fonetico:
            print(f"   [DEBUG] FIX 477: DETECTADO deletreo de correo - Cliente probablemente sigue dictando")
            return True

        # 3. FRASE TERMINA CON CONECTOR/PAUSA (sugiere continuación)
        # FIX 592 BRUCE1988: NO pausar por coma si es confirmación/saludo corto
        # Problema: "Sí, señor," → FIX 477 pausaba por la coma → Bruce mudo 15 seg
        confirmaciones_cortas_592 = [
            'si', 'sí', 'no', 'bueno', 'claro', 'ok', 'aja', 'ajá', 'mhm',
            'si señor', 'sí señor', 'si senor', 'sí senor',
            'no señor', 'no senor', 'si claro', 'sí claro',
            'bueno si', 'bueno sí', 'si digame', 'sí dígame',
            'si mande', 'sí mande', 'mande', 'digame', 'dígame',
            'si bueno', 'sí bueno', 'buenos dias', 'buenos días',
            'buenas tardes', 'buenas noches', 'si gracias', 'sí gracias'
        ]
        # FIX 754: BRUCE2321 - "No, joven," es rechazo cortés, NO continuación
        # Problema: "No, joven," termina en coma → FIX 477 trata como dato parcial → "Ajá, sí."
        # Pero "No, [término cortés]" es rechazo COMPLETO en español mexicano
        _rechazo_cortes_754 = [
            'no joven', 'no muchacho', 'no señor', 'no senor',
            'no señorita', 'no senorita', 'no mijo', 'no amigo',
            'no gracias joven', 'no gracias muchacho', 'no gracias señor',
        ]
        _tl_754 = re.sub(r'[,.\s]+$', '', texto_lower).replace(',', ' ').strip()
        _tl_754 = re.sub(r'\s+', ' ', _tl_754)
        if any(r in _tl_754 for r in _rechazo_cortes_754):
            print(f"   [DEBUG] FIX 754: '{_tl_754}' es rechazo cortés - NO pausar por coma")
            return False
        texto_limpio_592 = re.sub(r'[,.\s]+$', '', texto_lower).strip()
        es_confirmacion_corta = texto_limpio_592 in confirmaciones_cortas_592

        palabras_continuacion = [
            ",", "y", "entonces", "este", "o sea", "pues", "bueno",
            "es decir", "o", "pero", "como", "porque"
        ]
        for palabra in palabras_continuacion:
            if texto_cliente.strip().endswith(palabra):
                if palabra == "," and es_confirmacion_corta:
                    print(f"   [DEBUG] FIX 592: Frase '{texto_limpio_592}' termina con coma pero es CONFIRMACION CORTA - NO pausar")
                    return False
                # FIX 592: Para conectores (no coma), también verificar si es frase corta sin datos
                if es_confirmacion_corta:
                    print(f"   [DEBUG] FIX 592: Frase '{texto_limpio_592}' termina con '{palabra}' pero es confirmacion - NO pausar")
                    return False
                print(f"   [DEBUG] FIX 477: DETECTADO frase termina con '{palabra}' - Cliente probablemente continúa")
                return True

        # 4. NO está dando información
        return False

    def _cliente_repite_pregunta(self, texto_cliente: str) -> tuple:
        """
        FIX 480 (AUDITORIA W04): Detecta si cliente está repitiendo la MISMA pregunta.

        Problema observado en BRUCE1405:
        - Cliente preguntó 3 veces "¿De dónde habla?"
        - Bruce respondió diferente cada vez
        - NO detectó frustración del cliente

        Returns:
            (True/False, pregunta_repetida, veces_repetida)
        """
        from difflib import SequenceMatcher

        texto_lower = texto_cliente.lower().strip()

        # FIX 583: Whitelist de frases conversacionales que naturalmente se repiten
        # Estas NO son repeticiones problemáticas - son reconocimientos normales
        frases_whitelist_583 = {
            'si', 'sí', 'no', 'bueno', 'ok', 'aja', 'ajá', 'mhm',
            'si claro', 'sí claro', 'si por favor', 'sí por favor',
            'claro', 'claro que si', 'claro que sí', 'por supuesto',
            'buenos dias', 'buenos días', 'buenas tardes', 'buenas noches',
            'digame', 'dígame', 'mande', 'mande usted',
            'si digame', 'sí dígame', 'bueno si', 'bueno sí',
            'buenos dias digame', 'buenos días dígame',
            'si buenos dias', 'sí buenos días',
            'si buenas tardes', 'sí buenas tardes',
            'ah ok', 'ah bueno', 'ah ya', 'ya', 'ya veo',
            'esta bien', 'está bien', 'sale', 'va', 'orale', 'órale',
            'eso si', 'eso sí', 'asi es', 'así es', 'correcto',
            'con permiso', 'permiso', 'un momento', 'momentito',
        }
        # Normalizar: quitar signos de puntuación para comparar
        import re as re_583
        texto_normalizado_583 = re_583.sub(r'[¿?¡!.,;:\-]', '', texto_lower).strip()
        if texto_normalizado_583 in frases_whitelist_583:
            print(f"   FIX 583: Frase conversacional común '{texto_normalizado_583}' - NO es repetición")
            return (False, "", 0)

        # FIX 583: Frases de 3 palabras o menos son demasiado cortas para ser repeticiones
        palabras_583 = texto_normalizado_583.split()
        if len(palabras_583) <= 3:
            print(f"   FIX 583: Frase corta ({len(palabras_583)} palabras) - ignorando detección de repetición")
            return (False, "", 0)

        # Obtener últimos 3-4 mensajes del cliente
        mensajes_cliente = [
            msg['content'].lower().strip() for msg in self.conversation_history[-10:]
            if msg['role'] == 'user'
        ]

        if len(mensajes_cliente) < 2:
            return (False, "", 0)

        # Verificar si el mensaje actual es SIMILAR a alguno anterior
        mensaje_actual = mensajes_cliente[-1] if mensajes_cliente else texto_lower

        # Contador de repeticiones
        veces_repetida = 0
        pregunta_repetida = ""

        for msg_previo in mensajes_cliente[-4:-1]:  # Revisar últimos 3 mensajes anteriores
            # Calcular similitud (SequenceMatcher)
            similitud = SequenceMatcher(None, mensaje_actual, msg_previo).ratio()

            # Si similitud > 70%, considerar como repetición
            if similitud > 0.7:
                veces_repetida += 1
                pregunta_repetida = msg_previo
                self.metrics.log_repeticion_cliente()  # FIX 482: Métrica
                print(f"\n[REPEAT] FIX 480: REPETICIÓN DETECTADA (similitud: {similitud*100:.1f}%)")
                print(f"   Cliente repitió: '{msg_previo}'")
                print(f"   Veces repetida: {veces_repetida}")

        if veces_repetida >= 1:
            return (True, pregunta_repetida, veces_repetida + 1)  # +1 por mensaje actual

        return (False, "", 0)

    def _generar_respuesta_para_repeticion(self, pregunta_repetida: str, veces: int) -> str:
        """
        FIX 480 (AUDITORIA W04): Genera respuesta CLARA cuando cliente repite pregunta.

        Estrategia:
        - 1ra repetición: Responder MÁS CORTO y MÁS CLARO
        - 2da repetición: Ofrecer alternativa

        Args:
            pregunta_repetida: La pregunta que el cliente está repitiendo
            veces: Número de veces que la repitió

        Returns:
            Respuesta adaptada
        """
        pregunta_lower = pregunta_repetida.lower()

        # ================================================================
        # FIX 493: PROTECCIÓN ANTI-LOOP GLOBAL
        # Si Bruce ya preguntó por encargado 2+ veces en toda la conversación,
        # NO volver a preguntar aunque sea primera repetición de esta pregunta
        # ================================================================
        ultimas_bruce_rep = [
            msg['content'].lower() for msg in self.conversation_history[-6:]
            if msg['role'] == 'assistant'
        ]
        patrones_encargado_rep = [
            'se encontrará el encargado', 'se encontrara el encargado',
            'está el encargado', 'esta el encargado',
            'se encuentra el encargado', 'encargado de compras',
            'me comunica con el encargado'
        ]
        veces_pregunto_global = sum(
            1 for msg in ultimas_bruce_rep
            if any(p in msg for p in patrones_encargado_rep)
        )
        # Si ya preguntamos 2+ veces globalmente, tratar como 3+ repeticiones
        if veces_pregunto_global >= 2:
            veces = 3  # Forzar respuesta alternativa (sin preguntar por encargado)

        # Identificar tipo de pregunta
        if any(p in pregunta_lower for p in ["de dónde", "de donde", "ubicación", "dónde están"]):
            if veces == 2:
                return "Guadalajara, Jalisco. Hacemos envíos a toda la república. ¿Me comunica con el encargado?"
            else:  # 3+ veces
                return "Estamos en Guadalajara. ¿Prefiere que le llame en otro momento más conveniente?"

        elif any(p in pregunta_lower for p in ["quién habla", "quien habla", "quién llama"]):
            if veces == 2:
                return "Bruce de NIOVAL, productos ferreteros. ¿Está el encargado de compras?"
            else:
                return "Me llamo Bruce, de NIOVAL. ¿Le envío el catálogo por WhatsApp?"

        elif any(p in pregunta_lower for p in ["qué vende", "que vende", "qué productos"]):
            if veces == 2:
                return "Productos de ferretería: cintas, grifería, herramientas. ¿Está el encargado?"
            else:
                return "Ferretería. ¿Le envío el catálogo por WhatsApp para que vea todo?"

        elif any(p in pregunta_lower for p in ["qué marcas", "que marcas"]):
            if veces == 2:
                return "Marca NIOVAL. Es nuestra marca propia. ¿Está el encargado de compras?"
            else:
                return "NIOVAL. ¿Le gustaría recibir el catálogo por WhatsApp?"

        # FIX 626C: BRUCE2060 - Si cliente repite OFERTA de contacto, ACEPTAR
        # Problema: Cliente decía "te paso su teléfono" 3 veces y Bruce respondía
        # "Disculpe, no escuché bien" en loop porque FIX 480 detectaba repetición
        # pero no reconocía que era una OFERTA de datos que debía aceptar
        patrones_ofrece_626c = ['te paso', 'le paso', 'te doy', 'le doy', 'puedo pasar', 'puedo dar']
        patrones_dato_626c = ['teléfono', 'telefono', 'número', 'numero', 'cel', 'whatsapp', 'correo']
        if any(p in pregunta_lower for p in patrones_ofrece_626c) and any(t in pregunta_lower for t in patrones_dato_626c):
            print(f"   FIX 626C: Cliente repite OFERTA de contacto → aceptar número")
            return "Sí, por favor, dígame el número."

        # Respuesta genérica si no se identificó la pregunta
        if veces == 2:
            return "Disculpe, no escuché bien. ¿Me puede repetir su pregunta?"
        else:
            # FIX 684: Eliminada mención "problemas de conexión" (CTN-002)
            return "Disculpe, no le estoy escuchando bien. ¿Prefiere que le llame en otro momento?"

    def _detectar_error_necesita_recuperacion(self, texto_cliente: str) -> tuple:
        """
        FIX 481 (AUDITORIA W04): Detecta si Bruce cometió un error que necesita recuperación.

        Problema observado en auditoría:
        - Cuando Bruce comete un error (no responde pregunta, alucina datos), NO HAY LÓGICA DE RECUPERACIÓN
        - Cliente repite pregunta frustrado y Bruce responde diferente cada vez
        - Esto destruye confianza y lleva a cuelgues

        Casos de error detectables:
        1. Cliente repite pregunta (ya detectado por FIX 480)
        2. Cliente dice "No entendí" / "¿Cómo?" / "No le escucho bien"
        3. Cliente dice "Eso no es lo que pregunté"
        4. Cliente muestra frustración: "Ya le dije", "Le dije que..."

        Returns:
            (necesita_recuperacion: bool, tipo_error: str, contexto: str)
        """
        from difflib import SequenceMatcher

        texto_lower = texto_cliente.lower().strip()

        # FIX 618B: BRUCE2033 - Separar PEDIR_REPETIR de CONFUSION
        # PEDIR_REPETIR: Cliente NO ESCUCHÓ a Bruce (audio) → repetir literalmente
        # CONFUSION: Cliente no ENTENDIÓ a Bruce (concepto) → re-explicar
        # Problema: Antes ambos generaban "me expliqué mal..." → loop porque cliente
        #   quería que REPITIERA, no que explicara diferente
        indicadores_pedir_repetir = [
            'no escuché bien', 'no escuche bien', 'no te escuché',
            'no te escuche', 'no le escuché', 'no le escuche',
            'no escuché', 'no escuche',
            'me puedes repetir', 'me puede repetir', 'puedes repetir',
            'puede repetir', 'repite por favor', 'repíteme', 'repiteme',
            'no alcancé a escuchar', 'no alcance a escuchar',
            'no oí bien', 'no oi bien', 'no oí', 'no oi',
            'no te oigo', 'no le oigo', 'no se oye',
            'repítelo', 'repitelo', 'me lo repites', 'me lo puede repetir',
            'otra vez por favor', 'una vez más', 'una vez mas',
        ]

        if any(ind in texto_lower for ind in indicadores_pedir_repetir):
            print(f"\n FIX 618B: PEDIR_REPETIR - Cliente no escuchó a Bruce")
            print(f"   Cliente dijo: '{texto_cliente}'")
            return (True, "PEDIR_REPETIR", texto_cliente)

        # TIPO 1: Indicadores directos de confusión (conceptual)
        indicadores_confusion = [
            'no entendí', 'no entendi', '¿cómo?', '¿como?', 'como dice',
            'no le escucho', 'no escucho bien', 'no se le escucha',
            'no entiendo', '¿qué dice?', '¿que dice?', 'qué dice',
            'no le entiendo', 'no te entiendo', 'perdón', 'perdon',
            'no me quedó claro', 'no me quedo claro',
        ]

        if any(ind in texto_lower for ind in indicadores_confusion):
            print(f"\n[WRENCH] FIX 481: CONFUSIÓN DETECTADA - Cliente no entendió respuesta")
            print(f"   Cliente dijo: '{texto_cliente}'")
            return (True, "CONFUSION", texto_cliente)

        # TIPO 2: Indicadores de frustración (ya le dije antes)
        indicadores_frustracion = [
            'ya le dije', 'ya te dije', 'ya le comenté', 'ya te comente',
            'ya se lo dije', 'ya te lo dije', 'pero ya le',
            'eso no es lo que', 'no es lo que pregunté', 'no es lo que pregunte',
            'eso no fue lo que', 'no le pregunté eso', 'no le pregunte eso'
        ]

        if any(ind in texto_lower for ind in indicadores_frustracion):
            print(f"\n[WRENCH] FIX 481: FRUSTRACIÓN DETECTADA - Cliente repitiendo información")
            print(f"   Cliente dijo: '{texto_cliente}'")
            return (True, "FRUSTRACION", texto_cliente)

        # FIX 509: TIPO 2b: Cliente dice que NO tiene el dato/contacto
        # BRUCE1528: Cliente dijo "Le dije que no lo tengo" → Bruce pidió WhatsApp del encargado (ERROR)
        # FIX 509b: BRUCE1533/1534 - "no tengo WhatsApp" (sin "el") / "teléfono es directo"
        # Esto debe detectarse ANTES de CORRECCION porque "le dije" activa CORRECCION incorrectamente
        indicadores_no_tiene_dato = [
            'no lo tengo', 'no tengo el', 'no tengo su',
            'no cuento con', 'no me sé', 'no me se',
            'no sé cuál es', 'no se cual es', 'no sé su', 'no se su',
            'no tengo ese dato', 'no tengo esa información', 'no tengo esa informacion',
            'no tengo el número', 'no tengo el numero',
            'no tengo el whatsapp', 'no tengo el correo',
            'no sé el número', 'no se el numero',
            'no sé el whatsapp', 'no se el whatsapp',
            'no le sé', 'no le se', 'no me lo sé', 'no me lo se',
            'no cuento con ese', 'no cuento con esa',
            'no manejo esa información', 'no manejo esa informacion',
            'desconozco', 'no lo conozco', 'no la conozco',
            # FIX 509b: BRUCE1533/1534 - Variantes adicionales
            'no tengo whatsapp',  # Sin "el" - caso BRUCE1533
            'no manejo whatsapp', 'no uso whatsapp',
            'teléfono es directo', 'telefono es directo',
            'teléfono directo', 'telefono directo',
            'es telmex', 'línea directa', 'linea directa',
            'es línea fija', 'es linea fija', 'teléfono fijo', 'telefono fijo',
            'no tenemos whatsapp', 'no manejamos whatsapp',
            'aquí no hay whatsapp', 'aqui no hay whatsapp',
            'este número no tiene', 'este numero no tiene'
        ]

        if any(ind in texto_lower for ind in indicadores_no_tiene_dato):
            print(f"\n[WRENCH] FIX 509: CLIENTE NO TIENE DATO - Cliente indica que no tiene el contacto")
            print(f"   Cliente dijo: '{texto_cliente}'")
            return (True, "NO_TIENE_DATO", texto_cliente)

        # TIPO 3: Cliente corrige a Bruce
        # FIX 616A: BRUCE2031 - Hacer patrones más específicos
        # PROBLEMA: 'no es' es substring de 'no escuché', 'no estoy', 'no espera', etc.
        # SOLUCION: Usar 'no es ' (con espacio) o patrones más largos
        indicadores_correccion = [
            'no, es', 'no es lo que', 'no es eso', 'no es así', 'no es asi',
            'no, le dije', 'le dije', 'dije que',
            'pero le dije', 'le comenté que', 'le comente que',
            'no, eso no', 'eso no es'
        ]

        if any(ind in texto_lower for ind in indicadores_correccion):
            print(f"\n[WRENCH] FIX 481: CORRECCIÓN DETECTADA - Cliente corrigiendo a Bruce")
            print(f"   Cliente dijo: '{texto_cliente}'")
            return (True, "CORRECCION", texto_cliente)

        # TIPO 4: Cliente repite pregunta (usar FIX 480)
        es_repeticion, pregunta_repetida, veces = self._cliente_repite_pregunta(texto_cliente)
        if es_repeticion and veces >= 2:
            print(f"\n[WRENCH] FIX 481: PREGUNTA REPETIDA - Cliente preguntó {veces} veces sin respuesta clara")
            return (True, "PREGUNTA_REPETIDA", pregunta_repetida)

        return (False, "", "")

    def _generar_respuesta_recuperacion_error(self, tipo_error: str, contexto: str) -> str:
        """
        FIX 481 (AUDITORIA W04): Genera respuesta de recuperación cuando Bruce cometió error.

        Estrategia de recuperación:
        1. Reconocer error: "Disculpe, me expliqué mal..."
        2. Dar respuesta CLARA y DIRECTA
        3. Si ya se intentó 3 veces, ofrecer alternativa (llamar después, enviar catálogo)

        Args:
            tipo_error: Tipo de error ("CONFUSION", "FRUSTRACION", "CORRECCION", "PREGUNTA_REPETIDA")
            contexto: Contexto del error (texto del cliente)

        Returns:
            Respuesta de recuperación
        """
        self.intentos_recuperacion += 1
        contexto_lower = contexto.lower()

        # Si ya intentamos recuperar 3 veces → Ofrecer escalación/alternativa
        if self.intentos_recuperacion >= 3:
            print(f"\n[WARN] FIX 481: 3 INTENTOS DE RECUPERACIÓN FALLIDOS - Ofreciendo alternativa")
            return (
                # FIX 684: Eliminada mención "problemas de comunicación" (CTN-002)
                "Disculpe, no le estoy escuchando bien. "
                "¿Prefiere que le envíe el catálogo por WhatsApp y el encargado lo revisa con calma? "
                "O si gusta puedo llamar en otro momento más conveniente."
            )

        # RECUPERACIÓN SEGÚN TIPO DE ERROR

        # FIX 618B: PEDIR_REPETIR → Repetir LITERALMENTE el último mensaje de Bruce
        if tipo_error == "PEDIR_REPETIR":
            print(f"   FIX 618B: Cliente pide repetir - buscando último mensaje de Bruce")
            ultimos_bruce_rep = [
                msg['content'] for msg in self.conversation_history
                if msg['role'] == 'assistant'
            ]
            if ultimos_bruce_rep:
                ultimo_msg = ultimos_bruce_rep[-1]
                print(f"   FIX 618B: Repitiendo: '{ultimo_msg[:60]}...'")
                return ultimo_msg
            # Si no hay mensaje previo, hacer presentación
            return "Me comunico de la marca NIOVAL, vendemos productos para ferreterías. ¿Se encontrará el encargado de compras?"

        if tipo_error == "CONFUSION":
            # Cliente no entendió → Repetir MÁS CLARO y MÁS CORTO
            print(f"   [WRENCH] FIX 481: Generando respuesta de recuperación (CONFUSIÓN - Intento {self.intentos_recuperacion}/3)")

            # Detectar qué fue lo último que Bruce dijo para clarificar
            ultimos_bruce = [
                msg['content'].lower() for msg in self.conversation_history[-6:]
                if msg['role'] == 'assistant'
            ]

            # ================================================================
            # FIX 493: PROTECCIÓN ANTI-LOOP EN RECUPERACIÓN
            # Si ya preguntamos por encargado 2+ veces, NO volver a preguntar
            # ================================================================
            patrones_encargado_rec = [
                'se encontrará el encargado', 'se encontrara el encargado',
                'está el encargado', 'esta el encargado',
                'se encuentra el encargado', 'encargado de compras',
                'me comunica con el encargado'
            ]
            veces_pregunto_encargado_rec = sum(
                1 for msg in ultimos_bruce
                if any(p in msg for p in patrones_encargado_rec)
            )
            ya_pregunto_suficiente_rec = veces_pregunto_encargado_rec >= 1  # FIX 692A: alineado con bug detector

            if ultimos_bruce:
                ultimo_bruce = ultimos_bruce[-1]

                # Si Bruce habló de NIOVAL → Clarificar empresa
                if 'nioval' in ultimo_bruce or 'marca' in ultimo_bruce:
                    if ya_pregunto_suficiente_rec:
                        return "Disculpe, me expliqué mal. Hablo de NIOVAL, vendemos productos de ferretería. ¿Le envío el catálogo por WhatsApp?"
                    return "Disculpe, me expliqué mal. Hablo de NIOVAL, vendemos productos de ferretería. ¿Está el encargado de compras?"

                # Si Bruce habló de productos → Clarificar productos
                if 'producto' in ultimo_bruce or 'ferretería' in ultimo_bruce or 'grifería' in ultimo_bruce:
                    if ya_pregunto_suficiente_rec:
                        return "Perdón, me explico mejor: vendemos productos para ferreterías como cintas, grifería, herramientas. ¿Le envío el catálogo?"
                    return "Perdón, me explico mejor: vendemos productos para ferreterías como cintas, grifería, herramientas. ¿Me comunica con el encargado?"

                # Si Bruce pidió contacto → Clarificar por qué
                if 'whatsapp' in ultimo_bruce or 'correo' in ultimo_bruce:
                    return "Disculpe. Le pido el WhatsApp para enviarle nuestro catálogo de productos. Es sin compromiso."

            # Recuperación genérica
            if ya_pregunto_suficiente_rec:
                return "Disculpe, me expliqué mal. Hablo de NIOVAL, vendemos productos para ferreterías. ¿Le envío el catálogo por WhatsApp?"
            return "Disculpe, me expliqué mal. Hablo de NIOVAL, vendemos productos para ferreterías. ¿Se encontrará el encargado de compras?"

        elif tipo_error == "FRUSTRACION":
            # Cliente frustrado porque ya dio info → Disculparse y continuar
            print(f"   [WRENCH] FIX 481: Generando respuesta de recuperación (FRUSTRACIÓN - Intento {self.intentos_recuperacion}/3)")

            return (
                "Tiene razón, disculpe. "
                "¿Me puede confirmar el WhatsApp donde le envío el catálogo?"
            )

        elif tipo_error == "NO_TIENE_DATO":
            # FIX 509: BRUCE1528 - Cliente dice que NO tiene el contacto del encargado
            # En este caso, ofrecemos el WhatsApp de NIOVAL para que el encargado les contacte
            print(f"   [WRENCH] FIX 509: Generando respuesta de recuperación (NO TIENE DATO - Intento {self.intentos_recuperacion}/3)")

            return (
                "Entiendo perfectamente, no se preocupe. "
                "Si gusta le puedo dejar nuestro WhatsApp 6 6 2, 4 1 5, 1 9 9 7 "
                "para cuando el encargado pueda comunicarse con nosotros."
            )

        elif tipo_error == "CORRECCION":
            # Cliente corrigió a Bruce → Agradecer corrección y proceder
            print(f"   [WRENCH] FIX 481: Generando respuesta de recuperación (CORRECCIÓN - Intento {self.intentos_recuperacion}/3)")

            return (
                "Disculpe, tiene razón. "
                "¿Me confirma el WhatsApp del encargado para enviarle el catálogo?"
            )

        elif tipo_error == "PREGUNTA_REPETIDA":
            # Cliente repitió pregunta → Usar FIX 480
            print(f"   [WRENCH] FIX 481: Usando FIX 480 para respuesta de repetición")
            _, _, veces = self._cliente_repite_pregunta(contexto)
            return self._generar_respuesta_para_repeticion(contexto, veces)

        # Fallback genérico
        return "Disculpe, ¿me podría repetir? No escuché bien."

    def _obtener_frase_relleno(self, delay_segundos: float = 3.0) -> str:
        """
        FIX 163: Obtiene una frase de relleno natural para ganar tiempo cuando GPT tarda.
        Alterna entre diferentes frases para que suene natural y no repetitivo.

        Args:
            delay_segundos: Tiempo que tardó GPT en responder

        Returns:
            Frase de relleno en español mexicano (varía según delay)
        """
        # FIX 163: Frases para delays 3-5 segundos (cortas)
        frases_cortas = [
            "Ajá, déjeme ver...",
            "Mmm, perfecto...",
            "Entiendo, sí...",
            "Ajá, mire...",
            "Mmm, está claro...",
            "Perfecto, permítame...",
            "Ajá, exacto...",
            "Entendido, pues...",
            "Mmm, muy bien...",
            "Ajá, claro...",
        ]

        # FIX 163: Frases para delays 5-8 segundos (medias - más elaboradas)
        frases_medias = [
            "Déjeme ver eso con calma...",
            "Un momento, lo reviso...",
            "Permítame verificar...",
            "Déjeme consultarlo...",
            "Un segundito, lo verifico...",
            "Déjeme checar eso...",
            "Ajá, déjeme revisar bien...",
            "Mmm, permítame confirmarlo...",
        ]

        # FIX 163: Frases para delays >8 segundos (largas - más justificación)
        frases_largas = [
            "Déjeme revisar bien toda la información...",
            "Un momento por favor, verifico los detalles...",
            "Permítame consultar esto con cuidado...",
            "Déjeme ver todos los detalles...",
            "Un segundito, reviso toda la información...",
            "Mmm, déjeme verificar todo bien...",
        ]

        # FIX 163: Seleccionar lista según delay
        if delay_segundos > 8.0:
            frases_relleno = frases_largas
        elif delay_segundos > 5.0:
            frases_relleno = frases_medias
        else:
            frases_relleno = frases_cortas

        # Obtener frase actual y avanzar el índice
        frase = frases_relleno[self.indice_frase_relleno % len(frases_relleno)]
        self.indice_frase_relleno += 1

        return frase

    def _analizar_sentimiento(self, mensaje_cliente: str) -> dict:
        """
        FIX 386: Analiza el sentimiento/emoción del mensaje del cliente en tiempo real.

        Args:
            mensaje_cliente: Último mensaje del cliente

        Returns:
            dict con: {
                'sentimiento': 'muy_positivo'|'positivo'|'neutral'|'negativo'|'muy_negativo',
                'score': float (-1.0 a 1.0),
                'emocion_detectada': 'entusiasmo'|'interes'|'neutral'|'molestia'|'enojo',
                'debe_colgar': bool
            }
        """
        import re

        mensaje_lower = mensaje_cliente.lower()
        score = 0.0
        emocion = 'neutral'

        # ============================================================
        # PATRONES MUY NEGATIVOS (score: -0.8 a -1.0) → COLGAR
        # ============================================================
        patrones_muy_negativos = [
            # Enojo explícito
            r'ya\s+te\s+dije\s+que\s+no', r'¡no!', r'no\s+me\s+interesa',
            r'déjame\s+en\s+paz', r'dejame\s+en\s+paz', r'no\s+molestes',
            r'quita', r'lárgate', r'largate', r'cuelga',
            # Insultos
            r'idiota', r'estúpido', r'estupido', r'pendejo',
            # Frustración extrema
            r'¿qué\s+no\s+entiendes\?', r'¿que\s+no\s+entiendes\?',
            r'ya\s+basta', r'no\s+insistas',
        ]

        for patron in patrones_muy_negativos:
            if re.search(patron, mensaje_lower):
                score = -1.0
                emocion = 'enojo'
                break

        # ============================================================
        # PATRONES NEGATIVOS (score: -0.4 a -0.7)
        # ============================================================
        if score == 0.0:
            patrones_negativos = [
                # Rechazo educado
                r'no\s+gracias', r'no\s+me\s+interesa', r'no\s+necesito',
                r'no\s+estoy\s+interesado', r'no\s+nos\s+interesa',
                # Prisa/ocupado
                r'estoy\s+ocupado', r'no\s+tengo\s+tiempo', r'tengo\s+prisa',
                r'rápido', r'rapido', r'luego\s+te\s+llamo',
                # Ya tienen proveedor
                r'ya\s+tenemos', r'ya\s+trabajamos\s+con',
                r'solo\s+trabajamos\s+con', r'proveedor\s+fijo',
            ]

            for patron in patrones_negativos:
                if re.search(patron, mensaje_lower):
                    score = -0.6
                    emocion = 'molestia'
                    break

        # ============================================================
        # PATRONES POSITIVOS (score: 0.4 a 0.7)
        # ============================================================
        if score == 0.0:
            patrones_positivos = [
                # Interés activo
                r'me\s+interesa', r'suena\s+bien', r'perfecto',
                r'claro', r'sí', r'si\s+por\s+favor',
                # Pide información
                r'¿qué\s+productos', r'¿que\s+productos',
                r'mándame', r'mandame', r'envíame', r'enviame',
                r'pásame', r'pasame',
                # Acepta catálogo
                r'adelante', r'sí\s+mándalo', r'si\s+mandalo',
            ]

            for patron in patrones_positivos:
                if re.search(patron, mensaje_lower):
                    score = 0.6
                    emocion = 'interes'
                    break

        # ============================================================
        # PATRONES MUY POSITIVOS (score: 0.8 a 1.0)
        # ============================================================
        if score == 0.0:
            patrones_muy_positivos = [
                # Entusiasmo
                r'¡perfecto!', r'excelente', r'¡sí!',
                r'me\s+urge', r'necesito', r'cuando\s+antes',
                # Múltiples confirmaciones
                r'sí,?\s+sí', r'si,?\s+si', r'claro,?\s+claro',
                # Pide acción inmediata
                r'mándamelo\s+ya', r'mandamelo\s+ya',
                r'ahora\s+mismo', r'lo\s+antes\s+posible',
            ]

            for patron in patrones_muy_positivos:
                if re.search(patron, mensaje_lower):
                    score = 0.9
                    emocion = 'entusiasmo'
                    break

        # ============================================================
        # CLASIFICACIÓN FINAL
        # ============================================================
        if score >= 0.8:
            sentimiento = 'muy_positivo'
        elif score >= 0.4:
            sentimiento = 'positivo'
        elif score >= -0.3:
            sentimiento = 'neutral'
        elif score >= -0.7:
            sentimiento = 'negativo'
        else:
            sentimiento = 'muy_negativo'

        # Debe colgar si sentimiento muy negativo
        debe_colgar = score <= -0.8

        return {
            'sentimiento': sentimiento,
            'score': score,
            'emocion_detectada': emocion,
            'debe_colgar': debe_colgar
        }

    def _validar_sentido_comun(self, respuesta: str, contexto_cliente: str) -> tuple:
        """
        FIX 384: Validador de sentido común que verifica la lógica de la respuesta.

        Args:
            respuesta: Respuesta generada por GPT
            contexto_cliente: Últimos mensajes del cliente (concatenados)

        Returns:
            (es_valida: bool, razon_invalida: str)
        """
        import re

        respuesta_lower = respuesta.lower()
        contexto_lower = contexto_cliente.lower()

        # Pre-calcular detecciones comunes
        tiene_digitos = len(re.findall(r'\d', contexto_lower)) >= 8
        tiene_arroba = '@' in contexto_lower or 'arroba' in contexto_lower
        dice_este_numero = any(frase in contexto_lower for frase in [
            'este número', 'este numero', 'ese número', 'ese numero',
            'este mismo', 'sería este', 'seria este', 'es este'
        ])

        # ============================================================
        # REGLA 1: No pedir dato que cliente acaba de dar
        # ============================================================
        if 'cuál es su' in respuesta_lower or 'cual es su' in respuesta_lower or 'me confirma su' in respuesta_lower:
            if (tiene_digitos or dice_este_numero) and ('whatsapp' in respuesta_lower or 'número' in respuesta_lower or 'numero' in respuesta_lower):
                return False, "Cliente acaba de dar número"

            if tiene_arroba and ('correo' in respuesta_lower or 'email' in respuesta_lower):
                return False, "Cliente acaba de dar correo"

        # ============================================================
        # REGLA 2: No insistir con encargado si cliente dijo que no está
        # FIX 392: Mejorar detección de "salieron a comer / regresan en X tiempo"
        # FIX 393: Mejorar detección de "No, no se encuentra" y variantes
        # FIX 397: Detectar "No." simple como respuesta negativa (caso BRUCE1125)
        # FIX 409: Detectar "ahorita no" (caso timeout Deepgram + "no está")
        # ============================================================
        cliente_dice_no_esta = any(frase in contexto_lower for frase in [
            'no está', 'no esta', 'no se encuentra', 'no lo encuentro',
            'salió', 'salio', 'no viene', 'está fuera', 'esta fuera',
            # FIX 392: Agregar patrones de "salieron a comer / regresan"
            'salieron a comer', 'salió a comer', 'salio a comer',
            'fue a comer', 'fueron a comer',
            'regresan', 'regresa', 'vuelve', 'vuelven',
            'en media hora', 'en una hora', 'en un rato', 'más tarde', 'mas tarde',
            'ahorita no está', 'ahorita no esta',
            # FIX 409: Agregar "ahorita no" + variantes más flexibles
            'ahorita no', 'no está ahorita', 'no esta ahorita',
            'no ahorita', 'ahorita ya no',
            # FIX 393: Agregar variantes de rechazo directo (caso BRUCE1099)
            'no, no se encuentra', 'no, no está', 'no, no esta',
            'no se encuentra, no', 'no, gracias', 'no gracias',
            # FIX 438: Caso BRUCE1321 - "todavía no llega" indica que encargado regresará
            'todavía no llega', 'todavia no llega', 'aún no llega', 'aun no llega',
            'no ha llegado', 'todavía no viene', 'todavia no viene'
        ])

        bruce_insiste_encargado = any(frase in respuesta_lower for frase in [
            'me comunica con', 'me puede comunicar', 'me podría comunicar',
            'número del encargado', 'numero del encargado',
            'número directo del encargado', 'numero directo del encargado',
            'pasar con el encargado',
            # FIX 393: Detectar si Bruce PREGUNTA por el encargado (caso BRUCE1099)
            '¿se encontrará el encargado', '¿se encontrara el encargado',
            'se encontrará el encargado', 'se encontrara el encargado'
        ])

        # FIX 397: Detectar "No." simple cuando Bruce preguntó por encargado
        # Verificar últimos 2 mensajes de Bruce para ver si preguntó por encargado
        ultimos_bruce = [
            msg['content'].lower() for msg in self.conversation_history[-4:]
            if msg['role'] == 'assistant'
        ]
        bruce_pregunto_encargado_reciente = any(
            '¿se encontrará el encargado' in msg or '¿se encontrara el encargado' in msg or
            '¿usted es el encargado' in msg
            for msg in ultimos_bruce[-2:]  # Últimos 2 mensajes de Bruce
        )

        # FIX 397: Si cliente dice solo "No" o "No." y Bruce preguntó por encargado → Negación
        ultimos_cliente = [
            msg['content'].lower().strip() for msg in self.conversation_history[-3:]
            if msg['role'] == 'user'
        ]
        cliente_dice_no_simple = False
        if ultimos_cliente and bruce_pregunto_encargado_reciente:
            ultimo_msg = ultimos_cliente[-1].strip('.').strip()
            # Detectar "No" solo, sin otras palabras (excepto puntuación)
            if ultimo_msg in ['no', 'nope', 'nel', 'no.', 'no,']:
                cliente_dice_no_simple = True
                print(f"\n[DEBUG] FIX 397: Cliente dijo 'No' simple después de pregunta por encargado")
                print(f"   Último mensaje cliente: '{ultimos_cliente[-1]}'")
                print(f"   Bruce preguntó por encargado: {bruce_pregunto_encargado_reciente}")

        # FIX 392: También detectar si Bruce hace pregunta genérica sin ofrecer alternativa
        bruce_pregunta_generica = any(frase in respuesta_lower for frase in [
            '¿le envío el catálogo completo?', '¿le envio el catalogo completo?'
        ]) and not any(alt in respuesta_lower for alt in [
            'mientras tanto', 'cuando regrese', 'vuelva a llamar'
        ])

        # FIX 397: Activar REGLA 2 si cliente dijo "No está" O "No" simple
        if (cliente_dice_no_esta or cliente_dice_no_simple) and (bruce_insiste_encargado or bruce_pregunta_generica):
            if cliente_dice_no_simple:
                return False, "Cliente dijo 'No' - encargado NO disponible"
            else:
                return False, "Cliente dijo que encargado NO está / salió a comer"

        # ============================================================
        # REGLA 3: No decir "ya lo tengo" sin tener datos reales
        # FIX 397: Mejorar detección de datos reales vs frases ambiguas
        # ============================================================
        bruce_dice_ya_tengo = any(frase in respuesta_lower for frase in [
            'ya lo tengo', 'ya lo tengo registrado', 'ya lo tengo anotado',
            'le llegará', 'le llegara'
        ])

        if bruce_dice_ya_tengo:
            tiene_whatsapp = bool(self.lead_data.get("whatsapp"))
            tiene_email = bool(self.lead_data.get("email"))

            # FIX 397: Verificar más estrictamente si cliente dio dato
            # Frases ambiguas que NO son datos: "pásele este", "un segundo", etc.
            frases_ambiguas = [
                'pásele', 'pasele', 'un segundo', 'un momento', 'espere',
                'bueno', 'así es', 'ok', 'claro', 'sí', 'si'
            ]
            ultimos_msg_cliente = ' '.join([
                msg['content'].lower() for msg in self.conversation_history[-3:]
                if msg['role'] == 'user'
            ])
            es_frase_ambigua = any(f in ultimos_msg_cliente for f in frases_ambiguas)

            # Verificar si cliente realmente dio dato en contexto reciente
            tiene_dato_en_contexto = (
                (tiene_digitos and len(re.findall(r'\d', contexto_lower)) >= 10 and not es_frase_ambigua) or
                tiene_arroba or
                dice_este_numero
            )

            if not tiene_whatsapp and not tiene_email and not tiene_dato_en_contexto:
                print(f"\n[EMOJI] FIX 397: REGLA 3 ACTIVADA - Bruce dice 'ya lo tengo' sin datos")
                print(f"   Últimos mensajes cliente: '{ultimos_msg_cliente[:100]}...'")
                print(f"   Tiene WhatsApp guardado: {tiene_whatsapp}")
                print(f"   Tiene Email guardado: {tiene_email}")
                print(f"   Dígitos detectados: {tiene_digitos}")
                print(f"   Es frase ambigua: {es_frase_ambigua}")
                return False, "Dice 'ya lo tengo' sin datos capturados"

        # ============================================================
        # REGLA 4: Responder preguntas del cliente primero
        # ============================================================
        # ¿Cliente hizo una pregunta?
        ultimo_mensaje_cliente = contexto_lower.split()[-50:] if contexto_lower else []
        ultimo_mensaje_str = ' '.join(ultimo_mensaje_cliente)

        # FIX 423: Excluir saludos comunes que usan '?' pero NO son preguntas reales
        # Caso BRUCE1244: Cliente dijo "¿Bueno?" (saludo), Bruce ofreció productos (incorrecto)
        # FIX 436: Caso BRUCE1322 - Cliente dijo "Hola, buenos días. ¿Bueno?"
        #          FIX 423 fallaba porque solo detectaba si mensaje era EXACTAMENTE "¿bueno?"
        #          Ahora detectamos si el mensaje CONTIENE saludos típicos con interrogación
        saludos_con_interrogacion = [
            '¿bueno?', '¿bueno', 'bueno?',
            '¿dígame?', '¿digame?', 'dígame?', 'digame?',
            '¿mande?', 'mande?',
            '¿sí?', '¿si?', 'sí?', 'si?',
            '¿aló?', '¿alo?', 'aló?', 'alo?'
        ]

        # FIX 436: Detectar si el mensaje es un patrón de saludo (con o sin pregunta)
        # Patrones de saludo que NO son preguntas reales:
        # - "Hola, buenos días. ¿Bueno?"
        # - "¿Bueno? ¿Bueno?"
        # - "Hola. ¿Bueno?"
        patrones_saludo = [
            'hola', 'buenos días', 'buenos dias', 'buenas tardes', 'buenas noches',
            'buen día', 'buen dia', 'qué tal', 'que tal'
        ]

        # FIX 436: Múltiples condiciones para detectar saludo (no pregunta real)
        # 1. El mensaje es SOLO un saludo con interrogación
        es_solo_saludo_exacto = any(saludo == ultimo_mensaje_str.strip() for saludo in saludos_con_interrogacion)

        # 2. El mensaje CONTIENE un saludo con interrogación (como "Hola. ¿Bueno?")
        contiene_saludo_interrogacion = any(saludo in ultimo_mensaje_str for saludo in saludos_con_interrogacion)

        # 3. El mensaje es solo saludos típicos (hola, buenos días, etc.)
        es_saludo_tipico = any(patron in ultimo_mensaje_str for patron in patrones_saludo)

        # FIX 436: Si el mensaje contiene saludos Y tiene "?" del tipo saludo → NO es pregunta real
        # Caso BRUCE1322: "hola, buenos días. ¿bueno?" → es_saludo = True
        es_solo_saludo = (
            es_solo_saludo_exacto or
            (contiene_saludo_interrogacion and es_saludo_tipico) or
            (contiene_saludo_interrogacion and not any(q in ultimo_mensaje_str for q in [
                '¿qué', '¿que', '¿cuál', '¿cual', '¿cómo', '¿como',
                '¿cuánto', '¿cuanto', '¿dónde', '¿donde', '¿quién', '¿quien'
            ]))
        )

        cliente_pregunto = not es_solo_saludo and ('?' in ultimo_mensaje_str or any(q in ultimo_mensaje_str for q in [
            '¿qué', '¿que', '¿cuál', '¿cual', '¿cómo', '¿como',
            'qué tipo', 'que tipo', 'qué productos', 'que productos',
            'qué manejan', 'que manejan', 'qué venden', 'que venden'
        ]))

        # ¿Bruce respondió la pregunta?
        # FIX 439: Caso BRUCE1317 - Agregar palabras de identificación de empresa
        # Cliente preguntó "¿De dónde habla?" y Bruce dijo "Me comunico de la marca NIOVAL..."
        # FIX 384 NO reconocía esto como respuesta válida → cambiaba a info de productos
        bruce_responde = any(palabra in respuesta_lower for palabra in [
            'manejamos', 'tenemos', 'vendemos', 'sí', 'si',
            'grifería', 'griferia', 'cintas', 'herramientas',
            'claro', 'productos de ferretería', 'productos de ferreteria',
            # FIX 439: Agregar palabras de identificación/introducción
            'nioval', 'marca nioval', 'me comunico de', 'la marca',
            'soy de', 'hablo de', 'llamamos de', 'llamo de'
        ])

        if cliente_pregunto and not bruce_responde:
            # Cliente preguntó pero Bruce no respondió
            return False, "Cliente preguntó algo y Bruce no respondió"

        # ============================================================
        # REGLA 5: Detectar solicitud de reprogramación
        # FIX 392: Agregar "si gusta marcar más tarde" (caso BRUCE1094)
        # ============================================================
        cliente_pide_reprogramar = any(frase in contexto_lower for frase in [
            'marcar en otro momento', 'marca en otro momento',
            'llame en otro momento', 'llamar más tarde',
            'si gustas marca', 'si gusta marcar',
            # FIX 392: Agregar variantes de "si gusta marcar más tarde"
            'si gusta marcar más tarde', 'si gusta marcar mas tarde',
            'si gustas marcar más tarde', 'si gustas marcar mas tarde',
            'marque más tarde', 'marque mas tarde',
            # FIX 695: BRUCE2232 - "si gustas hablar luego" callback
            'si gusta hablar', 'si gustas hablar', 'hablar luego',
            'hablar más tarde', 'hablar mas tarde', 'hablar después', 'hablar despues'
        ])

        bruce_pide_whatsapp = any(frase in respuesta_lower for frase in [
            'cuál es su whatsapp', 'cual es su whatsapp',
            'me confirma su whatsapp', 'su número de whatsapp'
        ])

        if cliente_pide_reprogramar and bruce_pide_whatsapp:
            return False, "Cliente pidió reprogramar pero Bruce pide WhatsApp"

        # ============================================================
        # REGLA 6: No interrumpir cuando cliente está buscando encargado
        # ============================================================
        cliente_esta_buscando = any(frase in contexto_lower for frase in [
            'no me cuelgue', 'no cuelgue', 'dame un momento',
            'espera un momento', 'déjame ver', 'dejame ver',
            'hágame el lugar', 'hagame el lugar'
        ])

        # Si ya dijo "Claro, espero" y cliente sigue buscando, NO decir más
        ultimos_bruce = [
            msg['content'].lower() for msg in self.conversation_history[-3:]
            if msg['role'] == 'assistant'
        ]
        bruce_ya_dijo_espero = any('claro, espero' in msg or 'claro espero' in msg for msg in ultimos_bruce)

        if cliente_esta_buscando and bruce_ya_dijo_espero and respuesta.strip():
            # Cliente está buscando Y Bruce ya dijo que espera → NO decir nada más
            return False, "Cliente está buscando encargado - esperar en silencio"

        # Si todas las validaciones pasan
        return True, ""

    def _filtrar_respuesta_post_gpt(self, respuesta: str, skip_fix_384: bool = False) -> str:
        """
        FIX 226: Filtro POST-GPT para forzar reglas que GPT no sigue consistentemente.

        Problemas que resuelve:
        1. Bruce repite el correo del cliente (riesgo de errores)
        2. Bruce pregunta WhatsApp después de ya tener el correo
        3. Bruce dice cosas sin sentido o números aleatorios

        Args:
            respuesta: Respuesta generada por GPT
            skip_fix_384: Si True, NO ejecutar FIX 384 (usado por FIX 391/392)

        Returns:
            Respuesta filtrada/corregida
        """
        import re

        # FIX 479 (AUDITORIA W04): VALIDACIÓN DE RESPUESTAS VACÍAS
        # Problema observado en BRUCE1404: Bruce respondió con string vacío
        # Cliente esperó 49s y recibió respuesta vacía → colgó frustrado
        if not respuesta or len(respuesta.strip()) == 0:
            print(f"\n[WARN] FIX 479: RESPUESTA VACÍA DETECTADA - Usando respuesta de fallback")
            self.metrics.log_respuesta_vacia_bloqueada()  # FIX 482: Métrica
            return "Disculpe, ¿me podría repetir? No escuché bien."

        # FIX 479: Si respuesta es muy corta (<5 caracteres), probablemente error
        if len(respuesta.strip()) < 5:
            print(f"\n[WARN] FIX 479: RESPUESTA MUY CORTA detectada ('{respuesta}') - Usando fallback")
            self.metrics.log_respuesta_vacia_bloqueada()  # FIX 482: Métrica
            return "Permítame un momento, por favor."

        respuesta_lower = respuesta.lower()
        respuesta_original = respuesta
        filtro_aplicado = False

        # ============================================================
        # FIX 810B: BRUCE2528 - GPT genera filler como respuesta cuando cliente dio info sustantiva
        # "No se encuentra" → Bruce: "Sí, adelante" (INCORRECTO - debería procesar info)
        # "seis seis veintitrés..." → Bruce: "Sí, adelante" (INCORRECTO - debería confirmar dato)
        # Detecta fillers GPT y reemplaza con respuesta contextual
        # ============================================================
        _fillers_gpt_810 = [
            'sí, adelante', 'si, adelante', 'claro, continue', 'claro, continúe',
            'adelante, le escucho', 'sí, por favor', 'si, por favor',
            'sí, dígame', 'si, digame', 'entendido, continue', 'entendido, continúe',
            'perfecto, adelante', 'sí, lo escucho', 'si, lo escucho',
            'adelante', 'continúe', 'continue', 'le escucho',
        ]
        _resp_strip_810 = respuesta_lower.strip().rstrip('.')
        _es_filler_810 = _resp_strip_810 in _fillers_gpt_810

        if _es_filler_810:
            # Obtener último mensaje del cliente
            _ult_cliente_810 = ""
            for msg in reversed(self.conversation_history):
                if msg['role'] == 'user':
                    _ult_cliente_810 = msg.get('content', '').lower()
                    break

            # Solo override si cliente dio info sustantiva (>15 chars, no solo "bueno")
            if len(_ult_cliente_810) > 15:
                _sa_810 = lambda t: t.replace('á','a').replace('é','e').replace('í','i').replace('ó','o').replace('ú','u')
                _uc_810 = _sa_810(_ult_cliente_810)

                # Caso 1: Cliente dijo que encargado no está
                if any(p in _uc_810 for p in ['no esta', 'no se encuentra', 'no se encue', 'salio', 'no puede', 'esta enfermo', 'no vino']):
                    respuesta = "Entiendo que no se encuentra. ¿Me podría proporcionar un WhatsApp o correo para enviarle el catálogo al encargado?"
                    print(f"[OK] FIX 810B: Filler GPT '{_resp_strip_810}' → override (encargado no está)")
                    filtro_aplicado = True
                # Caso 2: Cliente dictó número/dato
                elif any(p in _uc_810 for p in ['seis', 'siete', 'ocho', 'nueve', 'arroba', '@', 'gmail']):
                    _nums_810 = ['cero','uno','dos','tres','cuatro','cinco','seis','siete','ocho','nueve',
                                 'diez','veinte','treinta','cuarenta','cincuenta']
                    if sum(1 for n in _nums_810 if n in _uc_810) >= 3 or re.search(r'\d{3,}', _uc_810):
                        respuesta = "Perfecto, ya lo tengo registrado. Muchas gracias."
                        print(f"[OK] FIX 810B: Filler GPT '{_resp_strip_810}' → override (dato dictado)")
                        filtro_aplicado = True
                # Caso 3: Cliente explicó algo sustantivo
                elif any(p in _uc_810 for p in ['no tengo', 'no lo tengo', 'no hay', 'no vendemos', 'no es', 'aqui no']):
                    respuesta = "Entiendo, muchas gracias por la información. ¿Habría otra persona con quien pudiera comunicarme?"
                    print(f"[OK] FIX 810B: Filler GPT '{_resp_strip_810}' → override (cliente explicó)")
                    filtro_aplicado = True

                if filtro_aplicado:
                    respuesta_lower = respuesta.lower()

        # ============================================================
        # FIX 816: OFERTA_POST_DESPEDIDA prevention
        # Bug detector marca cuando Bruce ofrece catálogo/pitch DESPUÉS de haberse despedido
        # 95 instancias en audit masivo - sin prevención previa
        # Detectar si último mensaje de Bruce fue despedida → bloquear cualquier oferta nueva
        # ============================================================
        if not filtro_aplicado and len(self.conversation_history) >= 2:
            _ultimo_bruce_816 = ''
            for _m816 in reversed(self.conversation_history):
                if _m816['role'] == 'assistant':
                    _ultimo_bruce_816 = _m816['content'].lower()
                    break
            # Patrones de despedida EXPLÍCITA (no ambiguos con saludos)
            # "buen día" solo = ambiguo (puede ser saludo), REQUIERE contexto de despedida
            _despedida_816 = any(p in _ultimo_bruce_816 for p in [
                'que tenga buen dia', 'que tenga buen día', 'que tenga excelente dia',
                'que tenga excelente día', 'gracias por su tiempo', 'hasta luego',
                'que le vaya bien', 'que este bien', 'que esté bien',
                'fue un placer',
            ])
            # Excluir saludos: "Hola, buen día" NO es despedida
            if _despedida_816 and 'hola' in _ultimo_bruce_816[:15]:
                _despedida_816 = False
            if _despedida_816:
                _oferta_816 = any(p in respuesta_lower for p in [
                    'catálogo', 'catalogo', 'le envío', 'le envio',
                    'nioval', 'productos', 'información', 'informacion',
                    'whatsapp', 'correo', 'le mando',
                ])
                if _oferta_816:
                    print(f"\n[FIX 816] OFERTA_POST_DESPEDIDA: Bruce ya se despidió pero GPT ofrece algo nuevo")
                    print(f"  Despedida previa: '{_ultimo_bruce_816[:60]}'")
                    print(f"  Oferta bloqueada: '{respuesta[:60]}'")
                    respuesta = "Que tenga excelente día, hasta luego."
                    respuesta_lower = respuesta.lower()
                    filtro_aplicado = True

        # ============================================================
        # FIX 615B: BRUCE2030 - NO repetir números de teléfono en voz
        # GPT a veces repite el número completo (ej: "+526623531804")
        # El TTS lo lee con acento extranjero y suena mal
        # SOLUCIÓN: Eliminar números de teléfono de la respuesta
        # ============================================================
        patron_tel_615 = r'\+?\d{2}[\s-]?\d{10}|\+?\d{12,13}|\b\d{10}\b'
        numeros_encontrados = re.findall(patron_tel_615, respuesta)
        if numeros_encontrados:
            print(f"[OK] FIX 615B: BRUCE2030 - Eliminando {len(numeros_encontrados)} número(s) de teléfono de respuesta")
            for num in numeros_encontrados:
                print(f"   Eliminando: '{num}'")
                respuesta = respuesta.replace(num, '')
            # Limpiar frases que quedan rotas tras eliminar el número
            respuesta = re.sub(r'(?:tengo\s+)?(?:su|el|al)\s+número\s*\.?\s*', '', respuesta, flags=re.IGNORECASE)
            respuesta = re.sub(r'por\s+[Ww]hats[Aa]pp\s+al\s*\.?\s*', 'por WhatsApp. ', respuesta)
            respuesta = re.sub(r'[Ss]í,?\s*\.?\s*(?=Perfecto)', '', respuesta)
            # Limpiar espacios dobles y puntuación extra
            respuesta = re.sub(r'\s{2,}', ' ', respuesta).strip()
            respuesta = re.sub(r'\.\s*\.', '.', respuesta)
            respuesta = re.sub(r',\s*\.', '.', respuesta)
            respuesta = re.sub(r'^\s*[,.]?\s*', '', respuesta)
            if respuesta:
                respuesta_lower = respuesta.lower()
                print(f"   Respuesta limpia: '{respuesta[:100]}'")

        # ============================================================
        # FIX 650: BRUCE2112, BRUCE2106, BRUCE2100, BRUCE2094 - GPT_FUERA_DE_TEMA
        # Bruce pregunta por encargado SIN dar pitch de productos primero
        # Debe dar información de productos ANTES de pedir encargado en turno 1
        # FIX 660: BRUCE2143 - Bruce pide contacto DIRECTO sin pitch ni encargado
        # ============================================================
        mensajes_bruce_650 = [msg for msg in self.conversation_history if msg['role'] == 'assistant']
        turno_bruce_650 = len(mensajes_bruce_650)

        if turno_bruce_650 == 1:  # Primer turno de Bruce (después del saludo automático)
            tiene_encargado = any(p in respuesta_lower for p in ["encargado", "encargada", "compras"])
            pide_contacto = any(p in respuesta_lower for p in ["whatsapp", "correo", "teléfono", "telefono", "número", "numero", "contacto"])
            # FIX 746: BRUCE2317 - Pitch real = identificación empresa + productos (no solo mención incidental)
            _tiene_identidad_746 = any(p in respuesta_lower for p in ["nioval", "marca", "distribuidor"])
            _tiene_productos_746 = any(p in respuesta_lower for p in ["productos", "ferreteros", "ferreteria", "herramientas"])
            tiene_pitch = _tiene_identidad_746 and _tiene_productos_746

            # FIX 660: Bloquear si pide contacto SIN pitch (peor que pedir encargado sin pitch)
            if pide_contacto and not tiene_pitch:
                # Reemplazar completamente con pitch + pregunta por encargado
                respuesta = "Me comunico de NIOVAL, somos distribuidores de productos ferreteros. ¿Se encontrará el encargado o encargada de compras?"
                print(f"   FIX 660: Reemplazado petición directa de contacto con pitch + encargado (turno 1)")
                filtro_aplicado = True
            # FIX 650 original: Agregar pitch si pregunta por encargado sin pitch
            elif tiene_encargado and not tiene_pitch:
                pitch_minimo = "Le comento, me comunico de NIOVAL, somos distribuidores de productos ferreteros. "
                respuesta = pitch_minimo + respuesta
                print(f"   FIX 650: Agregado pitch mínimo en turno 1 antes de preguntar por encargado")
                filtro_aplicado = True

        # ============================================================
        # FIX 653: BRUCE2093 - GPT_RESPUESTA_INCORRECTA
        # "nioval" debe ser siempre "NIOVAL" (mayúsculas - es nombre de marca)
        # ============================================================
        if "nioval" in respuesta_lower:
            # Reemplazar todas las variantes por NIOVAL mayúsculas
            respuesta = re.sub(r'\bnioval\b', 'NIOVAL', respuesta, flags=re.IGNORECASE)
            print(f"   FIX 653: Normalizado 'nioval' -> 'NIOVAL'")
            # FIX 813: NO poner filtro_aplicado - es cosmético, no sustantivo
            respuesta_lower = respuesta.lower()

        # ============================================================
        # FIX 667A: BRUCE2171 - GPT_LOGICA_ROTA (Cliente negó tener dato específico)
        # "solo tengo teléfono fijo y correo" → Bruce pide WhatsApp (INCORRECTO)
        # FIX 646A regla #2 en system prompt NO funciona → mover a POST-FILTER
        # ============================================================
        ultimo_cliente_667 = self.conversation_history[-1]['content'].lower() if self.conversation_history else ""

        # Detectar negaciones de datos específicos
        negaciones_dato_667 = [
            r'solo\s+(?:tengo|tiene|cuento|cuenta)\s+(telefono|correo|email|celular|numero)',
            r'(?:solo|unicamente|nada\s+mas)\s+(telefono|correo|email|celular)',
            r'no\s+(?:tengo|tiene|cuento|cuenta|manejo)\s+(whatsapp|telefono|correo|email)',
            r'(?:tengo|tiene)\s+solo\s+(el\s+)?(telefono|correo|email)',
            r'(?:sin|no\s+hay)\s+(whatsapp|telefono|correo)'
        ]

        dato_negado_667 = None
        for patron in negaciones_dato_667:
            match = re.search(patron, ultimo_cliente_667)
            if match:
                # Capturar qué dato fue negado
                dato_negado_667 = match.group(1) if match.lastindex >= 1 else match.group(0)
                break

        if dato_negado_667:
            # Detectar si Bruce pide el dato que cliente negó tener
            # Normalizar dato negado
            dato_map = {
                'whatsapp': ['whatsapp', 'whats'],
                'telefono': ['telefono', 'teléfono', 'número', 'numero', 'celular'],
                'correo': ['correo', 'email', 'e-mail', 'correo electronico']
            }

            dato_negado_norm = dato_negado_667
            for key, variants in dato_map.items():
                if any(v in dato_negado_667 for v in variants):
                    dato_negado_norm = key
                    break

            # Verificar si respuesta pide ese dato
            pide_dato_negado = False
            if dato_negado_norm == 'whatsapp' and 'whatsapp' in respuesta_lower:
                pide_dato_negado = True
            elif dato_negado_norm == 'telefono' and any(w in respuesta_lower for w in ['telefono', 'teléfono', 'número', 'numero', 'celular']):
                pide_dato_negado = True
            elif dato_negado_norm == 'correo' and any(w in respuesta_lower for w in ['correo', 'email']):
                pide_dato_negado = True

            if pide_dato_negado:
                # OVERRIDE: Pedir el dato alternativo que cliente SÍ tiene
                alternativas_667 = {
                    'whatsapp': 'Perfecto. ¿Me podría proporcionar entonces el teléfono fijo o el correo electrónico?',
                    'telefono': 'Entiendo. ¿Me podría proporcionar entonces el correo electrónico o WhatsApp?',
                    'correo': 'De acuerdo. ¿Me podría proporcionar entonces el teléfono o WhatsApp?'
                }
                respuesta_original_667 = respuesta
                respuesta = alternativas_667.get(dato_negado_norm, respuesta)
                print(f"[OK] FIX 667A: BRUCE2171 - Cliente negó tener {dato_negado_norm.upper()}, override respuesta GPT")
                print(f"   Respuesta original: '{respuesta_original_667[:80]}'")
                print(f"   Respuesta corregida: '{respuesta[:80]}'")
                filtro_aplicado = True

        # ============================================================
        # FIX 667B: BRUCE2173 - GPT_LOGICA_ROTA (Bruce ignora información clave)
        # "esa no es la sucursal correcta" → Bruce pide datos de esa sucursal (INCORRECTO)
        # FIX 646A regla #3 en system prompt NO funciona → mover a POST-FILTER
        # ============================================================
        # Detectar cuando cliente indica que algo es INCORRECTO/EQUIVOCADO
        indicadores_error_667b = [
            r'(?:esa|esta)\s+no\s+(?:es|sera)\s+(?:la|esa)\s+(sucursal|ubicacion|direccion|lugar)',
            r'no\s+(?:es|corresponde)\s+(?:aqui|aca|esta|la\s+correcta)',
            r'se\s+equivoc[oó]',
            r'(?:numero|telefono|dato)\s+(?:incorrecto|equivocado)',
            r'no\s+(?:es|sera)\s+(?:el|la)\s+correcto'
        ]

        cliente_indico_error_667b = False
        for patron in indicadores_error_667b:
            if re.search(patron, ultimo_cliente_667):
                cliente_indico_error_667b = True
                break

        if cliente_indico_error_667b:
            # Si Bruce sigue pidiendo datos relacionados → OVERRIDE
            pide_datos_sucursal = any(w in respuesta_lower for w in [
                'telefono de', 'número de', 'datos de', 'contacto de',
                'esa sucursal', 'esta sucursal', 'la sucursal'
            ])

            if pide_datos_sucursal:
                respuesta_original_667b = respuesta
                respuesta = "Entiendo, disculpe. ¿Me podría indicar entonces cuál es la sucursal o ubicación correcta?"
                print(f"[OK] FIX 667B: BRUCE2173 - Cliente indicó error en ubicación, override respuesta GPT")
                print(f"   Respuesta original: '{respuesta_original_667b[:80]}'")
                print(f"   Respuesta corregida: '{respuesta[:80]}'")
                filtro_aplicado = True

        # ============================================================
        # FIX 732: BRUCE2294 - GPT_LOGICA_ROTA (Cliente dio dato EN ESTE TURNO pero GPT pide el mismo)
        # "El correo es juan arroba gmail punto com" → Bruce pide correo (INCORRECTO)
        # FIX 646A regla #2 verifica turnos ANTERIORES pero NO el turno ACTUAL
        # ============================================================
        if not filtro_aplicado and ultimo_cliente_667:
            # Normalizar acentos para matching robusto (FIX 631 compat)
            _sa_732 = lambda t: t.replace('á','a').replace('é','e').replace('í','i').replace('ó','o').replace('ú','u').replace('ü','u').replace('ñ','n')
            resp_norm_732 = _sa_732(respuesta_lower)

            # Detectar datos en el turno actual del cliente
            tiene_email_732 = any(ind in ultimo_cliente_667 for ind in ['arroba', '@', 'gmail', 'hotmail', 'outlook', 'yahoo', 'punto com'])
            digitos_732 = re.findall(r'\d', ultimo_cliente_667)
            tiene_telefono_732 = len(digitos_732) >= 7
            # FIX 809: BRUCE2519 - También detectar números dictados en PALABRAS
            # "seis seis veintitrés cincuenta y tres dieciocho cero cuatro" = teléfono
            if not tiene_telefono_732:
                _nums_palabras_809 = [
                    'cero', 'uno', 'dos', 'tres', 'cuatro', 'cinco', 'seis', 'siete', 'ocho', 'nueve',
                    'diez', 'once', 'doce', 'trece', 'catorce', 'quince',
                    'dieciseis', 'diecisiete', 'dieciocho', 'diecinueve',
                    'veinte', 'veintiuno', 'veintidos', 'veintitres', 'veinticuatro', 'veinticinco',
                    'treinta', 'cuarenta', 'cincuenta', 'sesenta', 'setenta', 'ochenta', 'noventa'
                ]
                _conteo_809 = sum(1 for p in _nums_palabras_809 if p in ultimo_cliente_667)
                if _conteo_809 >= 4:
                    tiene_telefono_732 = True
                    print(f"[OK] FIX 809: Detectados {_conteo_809} números en PALABRAS → teléfono")
            tiene_whatsapp_732 = any(ind in ultimo_cliente_667 for ind in ['mi whatsapp', 'el whatsapp es', 'whatsapp es el', 'por whatsapp es'])

            dato_actual_732 = None
            if tiene_email_732:
                dato_actual_732 = 'correo'
            elif tiene_whatsapp_732:
                dato_actual_732 = 'whatsapp'
            elif tiene_telefono_732:
                dato_actual_732 = 'telefono'

            # FIX 743: BRUCE2296 - "Te puedo proporcionar correo" = OFERTA futura, NO dato ya dado
            # Distinguir "puedo dar/proporcionar/pasar" (intención) vs dato real (arroba, dígitos)
            if dato_actual_732:
                _ofertas_743 = ['puedo proporcionar', 'puedo dar', 'puedo pasar',
                    'quieres que te', 'quiere que le', 'te paso un', 'le paso un',
                    'te doy un', 'le doy un', 'si quieres te', 'si gusta le']
                es_oferta_743 = any(p in ultimo_cliente_667 for p in _ofertas_743)
                if es_oferta_743:
                    print(f"[INFO] FIX 743: '{ultimo_cliente_667[:60]}' es OFERTA, no dato real → skip FIX 732")
                    dato_actual_732 = None

            if dato_actual_732:
                # Verificar si Bruce pide el MISMO tipo de dato que cliente acaba de dar
                pide_mismo_732 = False
                if dato_actual_732 == 'correo' and any(w in resp_norm_732 for w in ['correo', 'email', 'e-mail']):
                    # Verificar que Bruce PIDE (no confirma)
                    pide_mismo_732 = any(w in resp_norm_732 for w in ['me podria dar', 'podria darme', 'proporcion', 'cual es su correo', 'cual es el correo'])
                elif dato_actual_732 == 'whatsapp' and 'whatsapp' in resp_norm_732:
                    pide_mismo_732 = any(w in resp_norm_732 for w in ['me podria dar', 'podria darme', 'proporcion', 'cual es su whatsapp'])
                elif dato_actual_732 == 'telefono' and any(w in resp_norm_732 for w in ['telefono', 'numero', 'celular']):
                    pide_mismo_732 = any(w in resp_norm_732 for w in ['me podria dar', 'podria darme', 'proporcion', 'cual es su', 'digitos', 'restantes'])

                if pide_mismo_732:
                    confirmaciones_732 = {
                        'correo': 'Perfecto, ya lo tengo anotado. Muchas gracias.',
                        'whatsapp': 'Perfecto, ya lo tengo registrado. Le envío el catálogo en un momento.',
                        'telefono': 'Perfecto, ya lo tengo anotado. Muchas gracias por el dato.',
                    }
                    respuesta_original_732 = respuesta
                    respuesta = confirmaciones_732.get(dato_actual_732, 'Perfecto, ya lo tengo anotado.')
                    print(f"[OK] FIX 732: BRUCE2294 - Cliente dio {dato_actual_732.upper()} en ESTE turno, GPT pidio de nuevo → override")
                    print(f"   Respuesta original: '{respuesta_original_732[:80]}'")
                    print(f"   Respuesta corregida: '{respuesta[:80]}'")
                    filtro_aplicado = True

        # ============================================================
        # FIX 668: BRUCE2163 - GPT_LOGICA_ROTA (Encargado no disponible, pide contacto)
        # "encargada disponible mañana" → Bruce pide WhatsApp (INCORRECTO - debe preguntar hora)
        # FIX 646A regla #1 en system prompt NO funciona → reforzar con POST-FILTER
        # ============================================================
        # Detectar "mañana" sin hora específica
        indicadores_manana_668 = [
            r'\bma[ñn]ana\b',
            r'despues de las',
            r'en\s+(?:la|por\s+la)\s+(?:tarde|ma[ñn]ana)',
            r'regresa\s+(?:ma[ñn]ana|despues|mas\s+tarde)',
            r'(?:hasta|a\s+partir\s+de)\s+ma[ñn]ana',
            r'(?:vuelve|llega)\s+ma[ñn]ana'
        ]

        cliente_dijo_manana_668 = False
        for patron in indicadores_manana_668:
            if re.search(patron, ultimo_cliente_667):
                cliente_dijo_manana_668 = True
                break

        # Verificar que NO mencionó hora específica (FIX 665 ya cubre ese caso)
        # FIX 751: Requiere al menos :MM o am/pm/periodo del día (antes matcheaba cualquier número suelto)
        patron_hora_668 = r'\b\d{1,2}(?::\d{2}|\s*(?:am|pm|de la ma[ñn]ana|de la tarde|de la noche))\b'
        tiene_hora_668 = re.search(patron_hora_668, ultimo_cliente_667)
        horas_palabras_668 = ['ocho', 'nueve', 'diez', 'once', 'doce', 'una', 'dos', 'tres', 'cuatro', 'cinco', 'seis', 'siete']
        menciona_hora_palabra_668 = any(f" {hora} " in f" {ultimo_cliente_667} " for hora in horas_palabras_668)

        if cliente_dijo_manana_668 and not tiene_hora_668 and not menciona_hora_palabra_668:
            # Si Bruce pide contacto (WhatsApp/correo/teléfono) → OVERRIDE preguntar hora
            pide_contacto_668 = any(w in respuesta_lower for w in [
                'whatsapp', 'correo', 'email', 'telefono', 'teléfono', 'número', 'numero',
                'contacto', 'celular', 'me podria proporcionar', 'me podria dar'
            ])

            if pide_contacto_668:
                respuesta_original_668 = respuesta
                respuesta = "Perfecto. ¿A qué hora mañana la puedo encontrar disponible?"
                print(f"[OK] FIX 668: BRUCE2163 - Encargado disponible mañana sin hora, override para preguntar hora")
                print(f"   Respuesta original: '{respuesta_original_668[:80]}'")
                print(f"   Respuesta corregida: '{respuesta[:80]}'")
                filtro_aplicado = True

        # ============================================================
        # FIX 733: BRUCE2287 - Anti-interrupción durante dictado parcial
        # Bruce pidió WhatsApp/teléfono/correo → cliente da datos parciales → GPT cambia de tema
        # Debe esperar con acknowledgment en vez de interrumpir
        # ============================================================
        if not filtro_aplicado and len(self.conversation_history) >= 2:
            # Normalizar acentos para matching robusto (FIX 631 compat)
            _sa_733 = lambda t: t.replace('á','a').replace('é','e').replace('í','i').replace('ó','o').replace('ú','u').replace('ü','u').replace('ñ','n')

            # Obtener último mensaje de Bruce (penúltimo en history)
            ultimo_bruce_733 = ''
            for msg in reversed(self.conversation_history):
                if msg.get('role') == 'assistant':
                    ultimo_bruce_733 = _sa_733(msg.get('content', '').lower())
                    break

            resp_norm_733 = _sa_733(respuesta_lower)

            # ¿Bruce pidió dato de contacto?
            bruce_pidio_dato_733 = any(w in ultimo_bruce_733 for w in [
                'whatsapp', 'correo', 'email', 'numero', 'telefono',
                'me podria dar', 'me podria proporcionar', 'podria darme',
                'cual es su', 'digame el', 'paseme el'
            ])

            if bruce_pidio_dato_733:
                # ¿Cliente está dando datos parciales? (2+ dígitos o email parcial)
                digitos_733 = re.findall(r'\d', ultimo_cliente_667)
                tiene_email_733 = any(ind in ultimo_cliente_667 for ind in ['arroba', '@', 'gmail', 'hotmail', 'punto com'])
                # FIX 739: BRUCE2308 - También detectar números en PALABRAS ("ochenta y siete")
                _nums_739 = ['cero','uno','dos','tres','cuatro','cinco','seis','siete',
                    'ocho','nueve','diez','once','doce','trece','catorce','quince',
                    'veinte','treinta','cuarenta','cincuenta','sesenta','setenta','ochenta','noventa']
                _uc_739 = ultimo_cliente_667.replace(',', ' ').replace('.', ' ')
                _uc_739 = _uc_739.replace('á','a').replace('é','e').replace('í','i').replace('ó','o').replace('ú','u')
                _nums_verbales_739 = sum(1 for p in _uc_739.split() if p in _nums_739)
                tiene_digitos_733 = len(digitos_733) >= 2 or _nums_verbales_739 >= 2

                if tiene_digitos_733 or tiene_email_733:
                    # ¿GPT respondió con algo que NO es acknowledgment?
                    es_acknowledgment_733 = any(w in resp_norm_733 for w in [
                        'aja', 'perfecto', 'ya lo tengo', 'anotado', 'registrado',
                        'continue', 'prosiga', 'adelante', 'digame', 'lo tengo', 'tome nota'
                    ])
                    # ¿GPT cambió de tema? (pitch, catálogo, despedida, pregunta diferente)
                    cambio_tema_733 = any(w in resp_norm_733 for w in [
                        'catalogo', 'productos', 'ferretero', 'nioval', 'encargado',
                        'buen dia', 'gracias por su tiempo', 'que tenga',
                        'le comento', 'le ofrecemos'
                    ])

                    if not es_acknowledgment_733 and cambio_tema_733:
                        respuesta_original_733 = respuesta
                        respuesta = _get_ack_769() + " Continúe por favor."
                        self.estado_conversacion = EstadoConversacion.DICTANDO_NUMERO if tiene_digitos_733 else EstadoConversacion.DICTANDO_CORREO
                        print(f"[OK] FIX 733: BRUCE2287 - Cliente dictando dato parcial, GPT cambió de tema → override")
                        print(f"   Bruce pidió dato → cliente dio {len(digitos_733)} dígitos")
                        print(f"   Respuesta original: '{respuesta_original_733[:80]}'")
                        print(f"   Respuesta corregida: '{respuesta[:80]}'")
                        filtro_aplicado = True

        # ============================================================
        # FIX 747: BRUCE2386 - ENCARGADO_NO_ESTA + dictado concurrente
        # Cliente dijo "Es que no estan ahorita. Es cuarenta y cuatro cuarenta"
        # Pattern detector set ENCARGADO_NO_ESTA but client was ALSO dictating numbers
        # Override response to acknowledge the data being dictated
        # ============================================================
        if not filtro_aplicado and getattr(self, '_datos_parciales_en_no_esta_747', False):
            # Client said encargado isn't there AND dictated numbers in same sentence
            # Acknowledge the number instead of asking for contact again
            respuesta_original_747 = respuesta
            respuesta = f"Entendido, no se encuentra. {_get_ack_769(digame=True)} el número por favor."
            self.estado_conversacion = EstadoConversacion.DICTANDO_NUMERO
            print(f"\n[OK] FIX 747: BRUCE2386 - ENCARGADO_NO_ESTA + dictado concurrente → override")
            print(f"   Respuesta original: '{respuesta_original_747[:80]}'")
            print(f"   Respuesta corregida: '{respuesta[:80]}'")
            filtro_aplicado = True
            self._datos_parciales_en_no_esta_747 = False  # Reset flag

        # ============================================================
        # FIX 736: BRUCE2302 - Cliente anuncia dato ("El WhatsApp", "El correo es")
        # pero GPT cambia tema (callback, despedida, encargado) → override con acknowledgment
        # Distinto de FIX 733: aquí el cliente ANUNCIA que va a dictar, no ha dado datos aún
        # ============================================================
        if not filtro_aplicado and ultimo_cliente_667:
            _sa_736 = lambda t: t.replace('á','a').replace('é','e').replace('í','i').replace('ó','o').replace('ú','u').replace('ü','u').replace('ñ','n')
            resp_norm_736 = _sa_736(respuesta_lower)

            # Cliente anuncia que va a dar dato de contacto
            anuncio_dato_736 = re.search(
                r'((?:este\s+)?si[.,]?\s+(?:el|mi)\s+whatsapp|'
                r'el whatsapp\b|mi whatsapp\b|'
                r'el correo\s+(?:es|seria)|mi correo\s+(?:es|seria)|'
                r'el numero\s+(?:es|seria)|mi numero\s+(?:es|seria)|'
                r'(?:si\s+)?(?:te|le)\s+(?:doy|paso)\s+(?:el|mi|un)\s+(?:whatsapp|correo|numero|telefono))',
                ultimo_cliente_667, re.IGNORECASE
            )

            if anuncio_dato_736:
                # GPT NO debe cambiar de tema (callback, despedida, hora)
                cambio_tema_736 = any(w in resp_norm_736 for w in [
                    'a que hora', 'me recomienda llamar', 'me comunico despues',
                    'gracias por su tiempo', 'que tenga', 'buen dia',
                    'encargado', 'catalogo', 'productos ferreteros',
                    'le comento', 'le ofrecemos'
                ])
                # Verificar que GPT no es SOLO acknowledgment (sin cambio de tema)
                es_ack_736 = any(w in resp_norm_736 for w in [
                    'aja', 'perfecto', 'digame', 'adelante', 'continue', 'prosiga',
                    'si, digame', 'claro', 'anotado'
                ])
                es_ack_corto_736 = es_ack_736 and len(respuesta.strip()) < 35

                if cambio_tema_736 and not es_ack_corto_736:
                    respuesta_original_736 = respuesta
                    respuesta = _get_ack_769(digame=True)
                    print(f"[OK] FIX 736: BRUCE2302 - Cliente anuncia dato, GPT cambió de tema → override")
                    print(f"   Cliente dijo: '{ultimo_cliente_667[:60]}'")
                    print(f"   Respuesta original: '{respuesta_original_736[:80]}'")
                    print(f"   Respuesta corregida: '{respuesta[:80]}'")
                    filtro_aplicado = True

        # ============================================================
        # FIX 737: BRUCE2306 - Cliente dictó email/teléfono pero GPT pide otro canal
        # Backup de FIX 733: verifica últimos 2 mensajes del cliente (no solo 1)
        # ============================================================
        if not filtro_aplicado and ultimo_cliente_667:
            _datos_recientes_737 = []
            _count_737 = 0
            for msg in reversed(self.conversation_history):
                if msg.get('role') == 'user' and _count_737 < 2:
                    _datos_recientes_737.append(msg['content'].lower())
                    _count_737 += 1
                elif _count_737 >= 2:
                    break
            _texto_reciente_737 = ' '.join(_datos_recientes_737)

            tiene_email_737 = any(ind in _texto_reciente_737 for ind in [
                'arroba', '@', 'gmail', 'hotmail', 'yahoo', 'outlook',
                'punto com', 'punto mx', '.com', '.mx', '.net'
            ])
            _digitos_737 = re.findall(r'\d', _texto_reciente_737)
            tiene_tel_737 = len(_digitos_737) >= 4

            if tiene_email_737 or tiene_tel_737:
                _sa_737 = lambda t: t.replace('á','a').replace('é','e').replace('í','i').replace('ó','o').replace('ú','u').replace('ü','u').replace('ñ','n')
                _rn_737 = _sa_737(respuesta_lower)
                pide_otro_737 = any(w in _rn_737 for w in [
                    'me podria proporcionar', 'me puede dar', 'me podria dar',
                    'me permite', 'tiene whatsapp', 'whatsapp del', 'correo del',
                    'numero de whatsapp', 'numero de telefono',
                    'proporcionar el whatsapp', 'proporcionar un whatsapp',
                    'proporcionar el correo', 'proporcionar un numero'
                ])
                ya_confirma_737 = any(w in _rn_737 for w in [
                    'anotado', 'registrado', 'ya lo tengo', 'perfecto',
                    'le envio', 'lo tengo', 'recibido'
                ])
                if pide_otro_737 and not ya_confirma_737:
                    respuesta_original_737 = respuesta
                    if tiene_email_737:
                        respuesta = "Perfecto, ya lo tengo anotado. Le envío la información al correo indicado."
                    else:
                        respuesta = "Perfecto, ya lo tengo anotado. Le envío el catálogo."
                    print(f"[OK] FIX 737: BRUCE2306 - Cliente dictó datos pero GPT pidió otro canal → override")
                    print(f"   Datos detectados: email={tiene_email_737}, tel={tiene_tel_737} ({len(_digitos_737)} dígitos)")
                    print(f"   Respuesta original: '{respuesta_original_737[:80]}'")
                    print(f"   Respuesta corregida: '{respuesta[:80]}'")
                    respuesta_lower = respuesta.lower()  # FIX 813: Actualizar respuesta_lower para evitar checks stale
                    filtro_aplicado = True

        # ============================================================
        # FIX 751: BRUCE2404 - Cliente OFRECE canal de contacto pero GPT pide otro
        # Diferente de FIX 737: FIX 737 detecta datos YA DICTADOS, FIX 751 detecta
        # OFERTAS de canal ("te podría pasar un correo", "por correo mejor")
        # Si cliente ofrece correo pero GPT pide WhatsApp → aceptar canal ofrecido
        # ============================================================
        if not filtro_aplicado and ultimo_cliente_667:
            _sa_751 = lambda t: t.replace('á','a').replace('é','e').replace('í','i').replace('ó','o').replace('ú','u').replace('ü','u').replace('ñ','n')
            _cl_751 = _sa_751(ultimo_cliente_667)
            # Detectar oferta de canal específico por el cliente
            _ofrece_correo_751 = any(p in _cl_751 for p in [
                'te paso un correo', 'le paso un correo', 'si te doy un correo',
                'te podria pasar un correo', 'le podria pasar un correo',
                'te puedo pasar un correo', 'le puedo dar un correo',
                'por correo mejor', 'mejor por correo', 'correo electronico',
                'te paso el correo', 'le paso el correo', 'te doy el correo',
                'le doy el correo', 'si te paso correo', 'te mando un correo',
                'le mando un correo', 'si quieres te paso un correo',
                'te puedo proporcionar un correo', 'le puedo proporcionar un correo'
            ])
            _ofrece_whatsapp_751 = any(p in _cl_751 for p in [
                'te paso un whatsapp', 'le paso un whatsapp', 'te doy mi whatsapp',
                'por whatsapp mejor', 'mejor por whatsapp',
                'te paso el whatsapp', 'le paso el whatsapp'
            ])
            _ofrece_telefono_751 = any(p in _cl_751 for p in [
                'te paso un telefono', 'le paso un telefono', 'te doy el telefono',
                'te paso el numero', 'le paso el numero', 'te doy un numero',
                'le doy un numero', 'te puedo dar un numero', 'le puedo dar un numero'
            ])
            _canal_ofrecido_751 = None
            if _ofrece_correo_751:
                _canal_ofrecido_751 = 'correo'
            elif _ofrece_whatsapp_751:
                _canal_ofrecido_751 = 'whatsapp'
            elif _ofrece_telefono_751:
                _canal_ofrecido_751 = 'telefono'

            if _canal_ofrecido_751:
                _rn_751 = _sa_751(respuesta_lower)
                # GPT pide un canal DIFERENTE al ofrecido
                _pide_otro_751 = False
                if _canal_ofrecido_751 == 'correo' and any(w in _rn_751 for w in [
                    'whatsapp', 'numero de whatsapp', 'proporcionar el whatsapp',
                    'numero de telefono', 'proporcionar un numero'
                ]):
                    _pide_otro_751 = True
                elif _canal_ofrecido_751 == 'whatsapp' and any(w in _rn_751 for w in [
                    'correo', 'email', 'proporcionar un correo',
                    'proporcionar el correo'
                ]):
                    _pide_otro_751 = True
                elif _canal_ofrecido_751 == 'telefono' and any(w in _rn_751 for w in [
                    'whatsapp', 'correo', 'email'
                ]):
                    _pide_otro_751 = True

                # También detectar si GPT ignora la oferta completamente
                _ignora_oferta_751 = any(w in _rn_751 for w in [
                    'me puede repetir', 'no escuche', 'me podria repetir',
                    'me decia', 'disculpe'
                ])

                if _pide_otro_751 or _ignora_oferta_751:
                    respuesta_original_751 = respuesta
                    if _canal_ofrecido_751 == 'correo':
                        respuesta = "Claro que sí, dígame el correo por favor."
                    elif _canal_ofrecido_751 == 'whatsapp':
                        respuesta = "Claro que sí, dígame el número de WhatsApp por favor."
                    else:
                        respuesta = "Claro que sí, dígame el número por favor."
                    respuesta_lower = respuesta.lower()
                    print(f"[OK] FIX 751: Cliente ofreció {_canal_ofrecido_751} pero GPT pidió otro canal → override")
                    print(f"   Cliente: '{ultimo_cliente_667[:80]}'")
                    print(f"   Respuesta original: '{respuesta_original_751[:80]}'")
                    print(f"   Respuesta corregida: '{respuesta[:80]}'")
                    respuesta_lower = respuesta.lower()  # FIX 813: Actualizar respuesta_lower
                    filtro_aplicado = True

        # ============================================================
        # FIX 752: BRUCE2407/2409/2410 - Callback sin contacto → despedida prematura
        # Bruce acepta callback pero se despide SIN pedir datos de contacto
        # Si callback detectado + no hay contacto capturado + Bruce se despide → override
        # ============================================================
        if not filtro_aplicado and self.conversation_history:
            _sa_752 = lambda t: t.replace('á','a').replace('é','e').replace('í','i').replace('ó','o').replace('ú','u').replace('ü','u').replace('ñ','n')
            _rn_752 = _sa_752(respuesta_lower)
            # Detectar si Bruce se está despidiendo
            _despedida_bruce_752 = any(p in _rn_752 for p in [
                'que tenga excelente dia', 'que tenga buen dia', 'hasta luego',
                'hasta pronto', 'le agradezco', 'muchas gracias por su tiempo',
                'me comunico despues', 'entonces me comunico', 'le marco despues',
                'le llamo despues', 'le marco mas tarde', 'le llamo mas tarde'
            ])
            if _despedida_bruce_752:
                # Verificar si hay contacto capturado
                _tiene_contacto_752 = bool(
                    getattr(self, 'lead_data', {}).get('telefono') or
                    getattr(self, 'lead_data', {}).get('whatsapp') or
                    getattr(self, 'lead_data', {}).get('email') or
                    getattr(self, 'lead_data', {}).get('correo')
                )
                # Verificar si hay callback mencionado en conversación
                _callback_752 = False
                _hora_callback_752 = ''
                for msg in self.conversation_history[-6:]:
                    _mc_752 = _sa_752(msg.get('content', '').lower())
                    if any(p in _mc_752 for p in [
                        'manana', 'mas tarde', 'otro dia', 'la proxima',
                        'despues de', 'en la tarde', 'en la manana',
                        'marcar despues', 'llamar despues', 'regresa',
                        'vuelve', 'no esta', 'no se encuentra', 'salio',
                        'marcar mas tarde', 'llamar mas tarde'
                    ]):
                        _callback_752 = True
                        # Buscar hora mencionada
                        import re as _re_752
                        _hora_match_752 = _re_752.search(r'(\d{1,2}(?::\d{2})?\s*(?:am|pm|de la manana|de la tarde)?)', _mc_752)
                        if _hora_match_752:
                            _hora_callback_752 = _hora_match_752.group(1)
                        if 'manana' in _mc_752 and not _hora_callback_752:
                            _hora_callback_752 = 'mañana'
                        break

                if _callback_752 and not _tiene_contacto_752:
                    respuesta_original_752 = respuesta
                    if _hora_callback_752:
                        respuesta = f"Con gusto le marco {_hora_callback_752}. ¿Me podría dejar un número directo donde pueda comunicarme?"
                    else:
                        respuesta = "Con gusto. ¿Me podría dejar un número directo donde pueda comunicarme?"
                    respuesta_lower = respuesta.lower()
                    print(f"[OK] FIX 752: Callback sin contacto → despedida prematura → override pedir contacto")
                    print(f"   Callback detectado: hora='{_hora_callback_752}'")
                    print(f"   Contacto capturado: {_tiene_contacto_752}")
                    print(f"   Respuesta original: '{respuesta_original_752[:80]}'")
                    print(f"   Respuesta corregida: '{respuesta[:80]}'")
                    respuesta_lower = respuesta.lower()  # FIX 813: Actualizar respuesta_lower
                    filtro_aplicado = True

        # ============================================================
        # FIX 690C: BRUCE2202 - Cliente listo para dictar ("tienes donde anotar")
        # Si GPT responde con "me puede repetir" o genérico, override con "Sí, dígame"
        # ============================================================
        if not filtro_aplicado and self.conversation_history:
            ultimo_cliente_690 = self.conversation_history[-1].get('content', '').lower() if self.conversation_history[-1].get('role') == 'user' else ''
            keywords_dictar_690 = ['anotar', 'apuntar', 'donde escribir', 'con que escribir',
                                   'tienes lapiz', 'tiene lapiz', 'tienes papel', 'tiene papel',
                                   'tienes pluma', 'tiene pluma']
            cliente_listo_690 = any(k in ultimo_cliente_690 for k in keywords_dictar_690)

            if cliente_listo_690:
                # FIX 707B: BRUCE2253 - Override también si GPT pide WhatsApp/correo/contacto
                # cuando cliente OFRECE dictar. No solo respuestas genéricas.
                respuesta_generica_690 = any(p in respuesta_lower for p in [
                    'me puede repetir', 'me podria repetir', 'no escuche', 'no le escuche',
                    'disculpe', 'me decia'
                ])
                respuesta_pide_contacto_707 = any(p in respuesta_lower for p in [
                    'whatsapp', 'correo', 'email', 'me da su', 'me podria dar',
                    'me proporciona', 'numero del encargado', 'numero directo',
                    'catalogo', 'me comunico despues', 'entonces me comunico'
                ])
                if respuesta_generica_690 or respuesta_pide_contacto_707:
                    respuesta_original_690 = respuesta
                    respuesta = "Sí, claro, dígame el número por favor."
                    respuesta_lower = respuesta.lower()
                    print(f"[OK] FIX 690C/707B: Cliente listo para dictar → override")
                    print(f"   Cliente dijo: '{ultimo_cliente_690[:60]}'")
                    print(f"   Respuesta original: '{respuesta_original_690[:60]}'")
                    print(f"   Respuesta corregida: '{respuesta}'")
                    filtro_aplicado = True

        # ============================================================
        # FIX 493: PARCHE GLOBAL ANTI-LOOP - PRIORIDAD MÁXIMA
        # Problema BRUCE1471: Bruce preguntaba por encargado 5+ veces en loop
        # Solución: Contar preguntas y BLOQUEAR repeticiones
        # ============================================================
        ultimas_bruce_antiloop = [
            msg['content'].lower() for msg in self.conversation_history[-10:]
            if msg['role'] == 'assistant'
        ]

        # Contar veces que preguntó por encargado
        # FIX 493: Lista COMPLETA de todas las variantes encontradas en el código
        preguntas_encargado = [
            # Variantes principales
            'se encontrará el encargado', 'se encontrara el encargado',
            'está el encargado', 'esta el encargado',
            'se encuentra el encargado', 'encargado de compras',
            'me comunica con el encargado', 'comunica con el encargado',
            # Variantes adicionales encontradas en auditoría
            'mensaje al encargado', 'dejar un mensaje al encargado',
            'hablar con el encargado', 'contactar al encargado',
            'encargado o encargada', 'encontrará el encargado'
        ]
        veces_pregunto_encargado = sum(
            1 for msg in ultimas_bruce_antiloop
            if any(p in msg for p in preguntas_encargado)
        )

        # FIX 494: INCOHERENCIA - Si cliente YA CONFIRMÓ que él es el encargado
        # Bruce NO debe preguntar por encargado NUNCA MÁS (ni siquiera 1 vez)
        encargado_ya_confirmado = getattr(self, 'encargado_confirmado', False)

        # Si la respuesta actual pregunta por encargado
        pregunta_por_encargado = any(p in respuesta_lower for p in preguntas_encargado)

        # FIX 810A: BRUCE2528 - State-based check: si estado = ENCARGADO_NO_ESTA, NUNCA re-preguntar
        # El counter de FIX 493 puede fallar si historial es largo; el estado es definitivo
        _estado_str_810 = str(getattr(self, 'estado_conversacion', ''))
        if pregunta_por_encargado and 'ENCARGADO_NO_ESTA' in _estado_str_810:
            print(f"\n[WARN] FIX 810A: Estado={_estado_str_810} → BLOQUEAR pregunta por encargado")
            print(f"   Respuesta bloqueada: '{respuesta[:60]}...'")
            respuesta = "Entiendo. ¿Me podría proporcionar el WhatsApp del encargado para enviarle el catálogo?"
            print(f"   Respuesta corregida: '{respuesta}'")
            return respuesta

        # FIX 494: INCOHERENCIA CRÍTICA - Cliente YA ES el encargado
        # Si encargado_ya_confirmado = True, BLOQUEAR INMEDIATAMENTE cualquier pregunta por encargado
        if pregunta_por_encargado and encargado_ya_confirmado:
            print(f"\n[WARN] FIX 494 INCOHERENCIA: Bruce iba a preguntar por encargado pero CLIENTE YA ES EL ENCARGADO")
            print(f"   Respuesta bloqueada: '{respuesta[:60]}...'")
            # Ofrecer catálogo directamente ya que estamos hablando con el encargado
            respuesta = "¿Le gustaría recibir nuestro catálogo de productos por WhatsApp?"
            print(f"   Respuesta corregida: '{respuesta}'")
            return respuesta

        # FIX 493+692A: Si ya preguntamos 1+ veces, bloquear 2da pregunta
        # FIX 692A: Alineado con bug detector (marca PREGUNTA_REPETIDA con 2 total)
        if pregunta_por_encargado and veces_pregunto_encargado >= 1:
            print(f"\n[WARN] FIX 493+692A ANTI-LOOP: Bruce iba a preguntar por encargado ({veces_pregunto_encargado+1}a vez)")
            print(f"   Respuesta bloqueada: '{respuesta[:60]}...'")

            # Verificar si cliente dio horario en el contexto
            ultimo_cliente = ""
            for msg in reversed(self.conversation_history):
                if msg['role'] == 'user':
                    ultimo_cliente = msg['content'].lower()
                    break

            import re
            patron_horario = r'(?:llega|viene|regresa).*?(?:a las|las)\s*(\d{1,2})'
            match_horario = re.search(patron_horario, ultimo_cliente)

            if match_horario:
                hora = match_horario.group(1)
                respuesta = f"Perfecto, le llamo a las {hora} entonces. Muchas gracias por su tiempo."
                print(f"   Respuesta anti-loop: '{respuesta}' (con horario)")
            elif 'no está' in ultimo_cliente or 'no esta' in ultimo_cliente:
                respuesta = "Entiendo. ¿Me podría proporcionar el WhatsApp del encargado para enviarle el catálogo?"
                print(f"   Respuesta anti-loop: '{respuesta}' (pedir WhatsApp)")
            else:
                respuesta = "¿Me puede proporcionar un WhatsApp donde le envíe información?"
                print(f"   Respuesta anti-loop: '{respuesta}' (genérico)")

            return respuesta

        # ============================================================
        # FIX 813: Si un filtro previo (737/751/752/810B) ya corrigió la respuesta,
        # NO aplicar anti-loop (catálogo/whatsapp/correo) - evitar sobreescribir correcciones
        if filtro_aplicado:
            print(f"[INFO] FIX 813: filtro_aplicado=True, saltando checks anti-loop (493B/671/672)")
            return respuesta

        # ============================================================
        # FIX 493B: BRUCE2118, BRUCE2128 - CATALOGO_REPETIDO
        # Bruce ofrece catálogo 2+ veces en la misma conversación → loop
        # Solución: Contar menciones de catálogo y BLOQUEAR si >=2
        # FIX 659: Debugging mejorado + detección más robusta
        # ============================================================
        patrones_catalogo_493b = [
            'catálogo', 'catalogo', 'le envío el catálogo', 'le envio el catalogo',
            'le mando el catálogo', 'le mando el catalogo', 'enviarle el catálogo',
            'enviarle el catalogo', 'le gustaría recibir', 'le gustaria recibir',
            'enviarle información', 'enviarle informacion', 'enviarle el catálogo',
            'para enviarle el catálogo', 'para enviarle el catalogo'
        ]

        # FIX 659: Contar ofertas en historial completo (no solo últimos 10)
        mensajes_bruce = [
            msg['content'].lower() for msg in self.conversation_history
            if msg['role'] == 'assistant'
        ]

        veces_ofrecio_catalogo = 0
        for msg in mensajes_bruce:
            if any(p in msg for p in patrones_catalogo_493b):
                veces_ofrecio_catalogo += 1
                print(f"[DEBUG FIX 659] Catálogo encontrado en: {msg[:80]}...")

        print(f"[DEBUG FIX 659] Total mensajes Bruce: {len(mensajes_bruce)}")
        print(f"[DEBUG FIX 659] Veces ofreció catálogo: {veces_ofrecio_catalogo}")

        # Si la respuesta actual ofrece catálogo
        ofrece_catalogo_493b = any(p in respuesta_lower for p in patrones_catalogo_493b)
        print(f"[DEBUG FIX 659] Respuesta actual ofrece catálogo: {ofrece_catalogo_493b}")

        # FIX 671: BRUCE2157, 2143, 2142, 2135, 2128, 2118 - Ajustar threshold para alinearse con bug detector
        # Bug detector marca CATALOGO_REPETIDO si ofreció 2+ veces
        # FIX 659 original bloqueaba en 3ra oferta (>=2 previos) → MISMATCH
        # FIX 671: Bloquear en 2da oferta (>=1 previo + 1 actual = 2 total)
        if ofrece_catalogo_493b and veces_ofrecio_catalogo >= 1:
            # FIX 705: BRUCE2214 - NO bloquear si cliente muestra interés/pregunta aclaración
            # Cliente preguntó "Como es? WhatsApp?" = INTERESADO, no repetición no solicitada
            ultimo_cliente_705 = ""
            for msg in reversed(self.conversation_history):
                if msg['role'] == 'user':
                    ultimo_cliente_705 = msg.get('content', '').lower()
                    break
            patrones_interes_705 = [
                'como es', 'como seria', 'como funciona', 'como le hago',
                'whatsapp', 'por whatsapp', 'al whatsapp',
                'por correo', 'al correo', 'me interesa',
                'si me interesa', 'si quiero', 'mandame', 'mandeme',
                'enviame', 'enviemelo', 'si por favor', 'si claro',
                'como es el catalogo', 'donde lo veo', 'como lo recibo',
                'a donde me lo manda', 'digame', 'platiqueme',
                # FIX 707A: BRUCE2253 - Cliente ofrece dictar dato
                'anotar', 'apuntar', 'donde anotar', 'donde apuntar',
                'te doy', 'le doy', 'te paso su', 'le paso su',
                'te lo paso', 'se lo paso', 'te lo doy', 'se lo doy',
                # FIX 773: BRUCE2436 - Preguntas sobre la empresa = interés
                'donde estan', 'donde están', 'de donde son', 'de dónde son',
                'que productos', 'qué productos', 'que marcas', 'qué marcas',
                'que manejan', 'qué manejan', 'que venden', 'qué venden',
                'tienen envios', 'hacen envios', 'hacen envíos',
                'te paso su correo', 'le paso su correo', 'te paso el correo',
            ]
            cliente_interesado_705 = any(p in ultimo_cliente_705 for p in patrones_interes_705)
            # FIX 812: BRUCE2516,2518,2523,2525 - Narrowar FIX 705: patrones genéricos
            # ("dígame", "sí claro") NO son interés real en catálogo si son respuesta corta
            if cliente_interesado_705 and len(ultimo_cliente_705) < 25:
                _genericos_812 = ['digame', 'si claro', 'si por favor', 'platiqueme', 'como es']
                _solo_generico_812 = any(p in ultimo_cliente_705 for p in _genericos_812)
                _tiene_catalogo_812 = 'catalogo' in ultimo_cliente_705 or 'catálogo' in ultimo_cliente_705
                if _solo_generico_812 and not _tiene_catalogo_812:
                    # Respuesta genérica corta sin mención de catálogo = NO interés real
                    cliente_interesado_705 = False
                    print(f"[INFO] FIX 812: Respuesta genérica corta '{ultimo_cliente_705[:40]}' → NO suspender anti-loop")
            if cliente_interesado_705:
                print(f"\n[INFO] FIX 705: Anti-loop SUSPENDIDO - cliente muestra interés")
                print(f"   Último cliente: '{ultimo_cliente_705[:80]}'")
                print(f"   Dejando pasar respuesta de catálogo (cliente lo pidió/preguntó)")
            else:
                # FIX 742: BRUCE2287+BRUCE2296 - NO bloquear si cliente dictando datos o ofreciendo contacto
                # BRUCE2287: Cliente dictó "ochenta y siete trece" → FIX 671 reemplazó con despedida
                # BRUCE2296: Cliente dijo "Te puedo proporcionar correo" → FIX 671 reemplazó con despedida
                _uc_742 = ultimo_cliente_705.replace('á','a').replace('é','e').replace('í','i').replace('ó','o').replace('ú','u')
                _digitos_742 = re.findall(r'\d', ultimo_cliente_705)
                _nums_742 = ['cero','uno','dos','tres','cuatro','cinco','seis','siete',
                    'ocho','nueve','diez','once','doce','trece','catorce','quince',
                    'veinte','treinta','cuarenta','cincuenta','sesenta','setenta','ochenta','noventa']
                _nums_verbales_742 = sum(1 for p in _uc_742.split() if p in _nums_742)
                cliente_dictando_742 = len(_digitos_742) >= 3 or _nums_verbales_742 >= 2

                cliente_ofrece_742 = any(p in ultimo_cliente_705 for p in [
                    'te puedo proporcionar', 'le puedo proporcionar',
                    'te puedo dar', 'le puedo dar', 'te puedo pasar', 'le puedo pasar',
                    'te doy el correo', 'te doy un correo', 'le doy el correo',
                    'te paso el correo', 'le paso el correo', 'te paso un correo',
                    'proporcionar correo', 'proporcionar el correo',
                    'arroba', '@', 'gmail', 'hotmail', 'punto com', 'punto mx',
                ])

                if cliente_dictando_742 or cliente_ofrece_742:
                    print(f"\n[INFO] FIX 742: Anti-loop SUSPENDIDO - cliente dictando/ofreciendo datos")
                    print(f"   Último cliente: '{ultimo_cliente_705[:80]}'")
                    print(f"   Dictando: {cliente_dictando_742}, Ofrece: {cliente_ofrece_742}")
                else:
                    print(f"\n[WARN] FIX 671 ANTI-LOOP: Bruce iba a ofrecer catálogo ({veces_ofrecio_catalogo+1}a vez)")
                    print(f"   Respuesta bloqueada: '{respuesta[:60]}...'")
                    # Respuesta alternativa: agradecer y cerrar
                    respuesta = "Perfecto, entonces me comunico después. Muchas gracias por su tiempo, que tenga excelente día."
                    print(f"   Respuesta anti-loop: '{respuesta}'")
                    return respuesta

        # FIX 494: INCOHERENCIA - Si ya tenemos WhatsApp capturado, NO pedir de nuevo
        whatsapp_ya_capturado = bool(self.lead_data.get("whatsapp"))

        # Contar veces que preguntó por WhatsApp
        preguntas_whatsapp = [
            'cuál es su whatsapp', 'cual es su whatsapp',
            'me proporciona su whatsapp', 'me da su whatsapp',
            'me confirma su whatsapp', 'confirma su whatsapp',
            'su número de whatsapp', 'su numero de whatsapp'
        ]
        veces_pregunto_whatsapp = sum(
            1 for msg in ultimas_bruce_antiloop
            if any(p in msg for p in preguntas_whatsapp)
        )

        # Detectar si Bruce va a pedir WhatsApp
        pregunta_whatsapp = any(p in respuesta_lower for p in preguntas_whatsapp)

        # FIX 494: Si YA tenemos WhatsApp, no pedir de nuevo (INCOHERENCIA CRÍTICA)
        if pregunta_whatsapp and whatsapp_ya_capturado:
            print(f"\n[WARN] FIX 494 INCOHERENCIA: Bruce iba a pedir WhatsApp pero YA LO TIENE: {self.lead_data.get('whatsapp')}")
            print(f"   Respuesta bloqueada: '{respuesta[:60]}...'")
            respuesta = "Perfecto, le envío el catálogo en un momento. ¿Hay algo más en lo que le pueda ayudar?"
            print(f"   Respuesta corregida: '{respuesta}'")
            return respuesta

        # FIX 672+813: Alinear threshold con bug detector
        # Bug detector marca PREGUNTA_REPETIDA si preguntó 2+ veces (count >= 2)
        # FIX 672 original: >= 2 previos (bloqueaba 3ra) → MISMATCH con detector que marca 2da
        # FIX 813: >= 1 previo (bloquea 2da pregunta, alineado con detector)
        if pregunta_whatsapp and veces_pregunto_whatsapp >= 1:
            print(f"\n[WARN] FIX 672 ANTI-LOOP: Bruce iba a pedir WhatsApp ({veces_pregunto_whatsapp+1}a vez)")
            print(f"   Respuesta bloqueada: '{respuesta[:60]}...'")
            respuesta = "Entiendo. ¿Prefiere que le envíe la información por correo electrónico?"
            print(f"   Respuesta anti-loop: '{respuesta}'")
            return respuesta

        # FIX 494: INCOHERENCIA - Si ya tenemos CORREO capturado, NO pedir de nuevo
        email_ya_capturado = bool(self.lead_data.get("email"))

        preguntas_correo = [
            'cuál es su correo', 'cual es su correo',
            'me proporciona su correo', 'me da su correo',
            'su correo electrónico', 'correo electrónico'
        ]
        pregunta_correo = any(p in respuesta_lower for p in preguntas_correo)

        if pregunta_correo and email_ya_capturado:
            print(f"\n[WARN] FIX 494 INCOHERENCIA: Bruce iba a pedir correo pero YA LO TIENE: {self.lead_data.get('email')}")
            print(f"   Respuesta bloqueada: '{respuesta[:60]}...'")
            respuesta = "Perfecto, le envío el catálogo en un momento. ¿Hay algo más en lo que le pueda ayudar?"
            print(f"   Respuesta corregida: '{respuesta}'")
            return respuesta

        # FIX 493: Detectar loop de preguntas de CATÁLOGO
        preguntas_catalogo = [
            'le envío el catálogo', 'le envio el catalogo',
            'enviarle el catálogo', 'enviarle el catalogo',
            'recibir el catálogo', 'recibir el catalogo',
            'recibir nuestro catálogo', 'recibir nuestro catalogo',
            'le gustaría recibir', 'le gustaria recibir'
        ]
        veces_pregunto_catalogo = sum(
            1 for msg in ultimas_bruce_antiloop
            if any(p in msg for p in preguntas_catalogo)
        )

        pregunta_catalogo = any(p in respuesta_lower for p in preguntas_catalogo)
        # FIX 672+813: Alinear threshold con bug detector (mismo que WhatsApp)
        # FIX 813: >= 1 previo (bloquea 2da pregunta, alineado con detector)
        if pregunta_catalogo and veces_pregunto_catalogo >= 1:
            print(f"\n[WARN] FIX 672 ANTI-LOOP: Bruce iba a ofrecer catálogo ({veces_pregunto_catalogo+1}a vez)")
            print(f"   Respuesta bloqueada: '{respuesta[:60]}...'")
            # Cliente ya rechazó 2 veces - despedirse profesionalmente
            respuesta = "Entiendo perfectamente. Le agradezco su tiempo. Que tenga excelente día."
            print(f"   Respuesta anti-loop: '{respuesta}' (despedida después de 2 rechazos)")
            return respuesta

        # FIX 493: Detectar loop de "¿Me puede repetir?"
        preguntas_repetir = [
            'me puede repetir', 'me podría repetir', 'me podria repetir',
            'no escuché bien', 'no escuche bien', 'disculpe no escuché'
        ]
        veces_pidio_repetir = sum(
            1 for msg in ultimas_bruce_antiloop
            if any(p in msg for p in preguntas_repetir)
        )

        pregunta_repetir = any(p in respuesta_lower for p in preguntas_repetir)
        # FIX 774: BRUCE2438 - Threshold >= 1 (bloquea 2da repetición, alineado con bug detector)
        # Bug detector marca PREGUNTA_REPETIDA con 2 ocurrencias, FIX 493 bloqueaba 3ra → MISMATCH
        if pregunta_repetir and veces_pidio_repetir >= 1:
            print(f"\n[WARN] FIX 774 ANTI-LOOP: Bruce iba a pedir repetición ({veces_pidio_repetir+1}a vez)")
            print(f"   Respuesta bloqueada: '{respuesta[:60]}...'")
            # FIX 774: En vez de pedir repetir de nuevo, usar fallback contextual
            # Ofrecer enviar catálogo para no perder la oportunidad
            respuesta = "¿Le gustaría que le envíe nuestro catálogo por WhatsApp para que lo revise con calma?"
            print(f"   Respuesta anti-loop: '{respuesta}' (FIX 774 - oferta catálogo)")
            return respuesta

        # FIX 517 BRUCE1733: Anti-loop para "¿Me permite dejarle el número?"
        # Problema: Bruce repitió esta frase 4 veces sin dar el número
        preguntas_dejar_numero = [
            'me permite dejarle', 'me permite darle',
            'le puedo dejar mi número', 'le puedo dar mi número',
            'dejarle el número', 'dejarle mi número',
            'para que el encargado nos contacte'
        ]
        veces_ofrecio_dejar_numero = sum(
            1 for msg in ultimas_bruce_antiloop
            if any(p in msg for p in preguntas_dejar_numero)
        )
        ofrece_dejar_numero = any(p in respuesta_lower for p in preguntas_dejar_numero)

        # Si ya ofreció 2+ veces dejar número, DAR EL NÚMERO directamente
        if ofrece_dejar_numero and veces_ofrecio_dejar_numero >= 2:
            print(f"\n[WARN] FIX 517 ANTI-LOOP: Bruce iba a ofrecer dejar número ({veces_ofrecio_dejar_numero+1}a vez)")
            print(f"   Respuesta bloqueada: '{respuesta[:60]}...'")
            # DAR EL NÚMERO DIRECTAMENTE
            respuesta = "Nuestro WhatsApp es 6 6 2, 4 1 5, 1 9 9 7 y nuestro correo es ventas arroba nioval punto com. Con gusto le atendemos."
            print(f"   Respuesta anti-loop: '{respuesta}' (dar número directo)")
            return respuesta

        # FIX 338: Definir contexto_cliente GLOBAL para todos los filtros
        # Incluir últimos 6 mensajes del cliente para mejor detección
        ultimos_mensajes_cliente_global = [
            msg['content'].lower() for msg in self.conversation_history[-12:]
            if msg['role'] == 'user'
        ]
        contexto_cliente = ' '.join(ultimos_mensajes_cliente_global[-6:]) if ultimos_mensajes_cliente_global else ""

        # ============================================================
        # FIX 481 (AUDITORIA W04): RECUPERACIÓN DE ERRORES
        # PRIORIDAD ULTRA-ALTA - Detectar si Bruce necesita corregir error
        # ============================================================
        # Obtener último mensaje del cliente
        ultimo_mensaje_cliente = ""
        if self.conversation_history:
            for msg in reversed(self.conversation_history):
                if msg['role'] == 'user':
                    ultimo_mensaje_cliente = msg['content']
                    break

        if ultimo_mensaje_cliente:
            necesita_recuperacion, tipo_error, contexto_error = self._detectar_error_necesita_recuperacion(ultimo_mensaje_cliente)

            if necesita_recuperacion:
                # FIX 626A: BRUCE2060 - Si PREGUNTA_REPETIDA pero GPT ya tiene respuesta CORRECTA,
                # NO sobreescribir. En BRUCE2060, GPT generó "Sí, dígame el número" (perfecto!)
                # pero FIX 481 lo reemplazó con "Disculpe, no escuché bien" → loop infinito.
                # Solución: verificar si GPT ya acepta/responde correctamente la repetición.
                respuesta_lower_481 = respuesta.lower()
                if tipo_error == "PREGUNTA_REPETIDA":
                    # Palabras que indican que GPT YA respondió correctamente al cliente
                    gpt_ya_responde_bien = any(kw in respuesta_lower_481 for kw in [
                        'dígame el número', 'digame el numero', 'dígame su número', 'digame su numero',
                        'dígame el teléfono', 'digame el telefono',
                        'por favor, dígame', 'por favor, digame',
                        'sí, por favor', 'si, por favor', 'sí por favor', 'si por favor',
                        'adelante, dígame', 'adelante, digame',
                        'claro, dígame', 'claro, digame',
                        'anote', 'tome nota', 'dígame', 'digame',
                    ])
                    if gpt_ya_responde_bien:
                        print(f"\n[OK] FIX 626A: GPT ya tiene respuesta CORRECTA para repetición")
                        print(f"   Tipo: {tipo_error}")
                        print(f"   GPT: '{respuesta[:80]}'")
                        print(f"   → Usando GPT en vez de recuperación genérica")
                        # Resetear intentos porque GPT respondió bien
                        self.intentos_recuperacion = 0
                        # No retornar aquí, dejar que pase al resto del post-filter
                    else:
                        # GPT no tiene buena respuesta → usar recuperación normal
                        respuesta_recuperacion = self._generar_respuesta_recuperacion_error(tipo_error, contexto_error)
                        self.metrics.log_recuperacion_error()  # FIX 482: Métrica
                        print(f"\n[WRENCH] FIX 481: RECUPERACIÓN DE ERROR ACTIVADA")
                        print(f"   Tipo error: {tipo_error}")
                        print(f"   Respuesta original GPT: '{respuesta[:80]}'")
                        print(f"   Respuesta recuperación: '{respuesta_recuperacion[:80]}'")
                        return respuesta_recuperacion
                else:
                    # Para otros tipos de error (CONFUSION, FRUSTRACION, etc.) → recuperación normal
                    respuesta_recuperacion = self._generar_respuesta_recuperacion_error(tipo_error, contexto_error)
                    self.metrics.log_recuperacion_error()  # FIX 482: Métrica
                    print(f"\n[WRENCH] FIX 481: RECUPERACIÓN DE ERROR ACTIVADA")
                    print(f"   Tipo error: {tipo_error}")
                    print(f"   Respuesta original GPT: '{respuesta[:80]}'")
                    print(f"   Respuesta recuperación: '{respuesta_recuperacion[:80]}'")
                    return respuesta_recuperacion
            else:
                # No hay error → Resetear contador de recuperación
                if self.intentos_recuperacion > 0:
                    print(f"\n[OK] FIX 481: Conversación recuperada - Reseteando contador (era {self.intentos_recuperacion})")
                    self.intentos_recuperacion = 0
                    self.ultimo_error_detectado = None

        # ============================================================
        # FIX 398/400: REGLAS CRÍTICAS - SIEMPRE ACTIVAS (NO SKIPPEABLE)
        # Estas reglas se ejecutan ANTES de cualquier skip
        # ============================================================

        # REGLA CRÍTICA 2: Si cliente pregunta "¿De dónde habla?" o "¿Qué necesita?", responder ANTES de ofrecer catálogo
        # FIX 400: Caso BRUCE1136 - Cliente preguntó "¿De dónde me habla?" y Bruce no respondió
        # FIX 405: Caso BRUCE1146 - Cliente preguntó "¿Qué necesita?" y Bruce dijo "¿Me escucha?"
        # FIX 412: Caso BRUCE1203 - Cliente preguntó "¿En qué le puedo ayudar?" al inicio, Bruce se presentó, luego cliente dijo "No, no se encuentra" y Bruce volvió a presentarse innecesariamente
        if not filtro_aplicado:
            cliente_pregunta_de_donde = any(patron in contexto_cliente.lower() for patron in [
                '¿de dónde', '¿de donde', 'de dónde', 'de donde',
                '¿de qué empresa', '¿de que empresa', 'de qué empresa', 'de que empresa',
                '¿qué empresa', '¿que empresa', 'qué empresa', 'que empresa',
                '¿cómo dijo', '¿como dijo', 'cómo dijo', 'como dijo',
                '¿quién habla', '¿quien habla', 'quién habla', 'quien habla',
                '¿me repite', 'me repite', '¿puede repetir', 'puede repetir',
                # FIX 405: Agregar "¿Qué necesita?" (caso BRUCE1146)
                '¿qué necesita', '¿que necesita', 'qué necesita', 'que necesita',
                '¿en qué le puedo ayudar', '¿en que le puedo ayudar',
                '¿qué se le ofrece', '¿que se le ofrece',
                '¿para qué llama', '¿para que llama',
                # FIX 479: BRUCE1445 - "de donde llamas dices" (sin signos de interrogación)
                'de donde llamas', 'de dónde llamas', 'de donde habla', 'de dónde habla',
                'de donde me llama', 'de dónde me llama', 'de donde dices', 'de dónde dices',
                'de que marca', 'de qué marca', 'que marca es', 'qué marca es',
                'como se llama la marca', 'cómo se llama la marca',
                'como dijo que se llama', 'cómo dijo que se llama'
            ])

            # Verificar si Bruce NO mencionó la empresa en su respuesta ACTUAL
            bruce_menciona_nioval_en_respuesta_actual = any(palabra in respuesta.lower() for palabra in [
                'nioval', 'marca nioval', 'la marca', 'me comunico de'
            ])

            # FIX 412: Verificar si Bruce YA se presentó en mensajes ANTERIORES
            # Caso BRUCE1203: Cliente preguntó "¿En qué le puedo ayudar?" al inicio, Bruce se presentó,
            # luego cliente dijo "No, no se encuentra" y Bruce NO debe volver a presentarse
            ultimos_mensajes_bruce_temp_fix412 = [
                msg['content'].lower() for msg in self.conversation_history[-10:]
                if msg['role'] == 'assistant'
            ]
            bruce_ya_se_presento = any(
                any(palabra in msg for palabra in ['nioval', 'marca nioval', 'me comunico de'])
                for msg in ultimos_mensajes_bruce_temp_fix412
            )

            # FIX 412: SOLO activar si cliente preguntó Y Bruce NO mencionó NIOVAL (ni ahora NI antes)
            if cliente_pregunta_de_donde and not bruce_menciona_nioval_en_respuesta_actual and not bruce_ya_se_presento:
                print(f"\n[EMOJI] FIX 400/405/412: REGLA CRÍTICA 2 - Cliente preguntó sobre empresa, Bruce NO se ha presentado")
                print(f"   Cliente dijo: '{contexto_cliente[:100]}'")
                print(f"   Bruce iba a decir: '{respuesta[:80]}'")
                respuesta = "Me comunico de la marca NIOVAL para ofrecer información de nuestros productos de ferretería. ¿Se encontrará el encargado o encargada de compras?"
                filtro_aplicado = True
            elif cliente_pregunta_de_donde and bruce_ya_se_presento:
                # FIX 412: Bruce YA se presentó antes - NO sobrescribir
                print(f"\n[EMOJI]  FIX 412: Cliente preguntó pero Bruce YA se presentó antes - NO sobrescribiendo")
                print(f"   Respuesta actual: '{respuesta[:80]}'")
                # NO activar filtro - dejar que la respuesta actual fluya

        # REGLA CRÍTICA 1: NUNCA decir "ya lo tengo" sin datos reales
        # FIX 402: Expandir patrones para capturar TODAS las variantes
        if not filtro_aplicado:
            bruce_dice_ya_tengo = any(frase in respuesta_lower for frase in [
                'ya lo tengo', 'ya lo tengo registrado', 'ya lo tengo anotado',
                'ya tengo registrado', 'ya tengo anotado',
                'le llegará', 'le llegara',
                'le envío el catálogo en las próximas horas',
                'le enviará el catálogo', 'le enviara el catalogo',
                'en las próximas horas', 'en las proximas horas',
                'perfecto, ya lo', 'perfecto ya lo'  # FIX 402: Detectar inicio de frase
            ])

            if bruce_dice_ya_tengo:
                tiene_whatsapp = bool(self.lead_data.get("whatsapp"))
                tiene_email = bool(self.lead_data.get("email"))

                # FIX 398: Verificar MUY estrictamente si cliente dio dato
                frases_ambiguas = [
                    'pásele', 'pasele', 'un segundo', 'un momento', 'espere',
                    'bueno', 'así es', 'ok', 'claro', 'sí', 'si', 'eso es'
                ]
                ultimos_msg_cliente = ' '.join([
                    msg['content'].lower() for msg in self.conversation_history[-3:]
                    if msg['role'] == 'user'
                ])

                # Verificar si hay arroba o dígitos suficientes
                tiene_arroba = '@' in ultimos_msg_cliente
                digitos = re.findall(r'\d', ultimos_msg_cliente)
                tiene_digitos_suficientes = len(digitos) >= 10

                # Verificar que NO sea frase ambigua
                es_frase_ambigua = any(f in ultimos_msg_cliente for f in frases_ambiguas)

                # FIX 398: Solo considerar dato válido si:
                # 1. Tiene datos guardados O
                # 2. Tiene arroba O
                # 3. Tiene 10+ dígitos Y NO es frase ambigua
                tiene_dato_real = (
                    tiene_whatsapp or
                    tiene_email or
                    tiene_arroba or
                    (tiene_digitos_suficientes and not es_frase_ambigua)
                )

                if not tiene_dato_real:
                    print(f"\n[EMOJI] FIX 398: REGLA CRÍTICA 1 - Bloqueó 'ya lo tengo' sin datos")
                    print(f"   WhatsApp guardado: {tiene_whatsapp}")
                    print(f"   Email guardado: {tiene_email}")
                    print(f"   Últimos mensajes: '{ultimos_msg_cliente[:100]}'")
                    print(f"   Tiene arroba: {tiene_arroba}")
                    print(f"   Dígitos: {len(digitos)}")
                    print(f"   Es frase ambigua: {es_frase_ambigua}")

                    respuesta = "Claro, con gusto. ¿Me confirma su número de WhatsApp o correo electrónico para enviarle el catálogo?"
                    filtro_aplicado = True

        # ============================================================
        # FILTRO -1 (FIX 384): VALIDADOR DE SENTIDO COMÚN
        # Se ejecuta DESPUÉS de REGLAS CRÍTICAS
        # ============================================================
        if not filtro_aplicado:
            # FIX 389: NO activar FIX 384 si es persona nueva después de transferencia
            # Dejar que FILTRO 5B (FIX 289) maneje la re-presentación
            ultimos_mensajes_bruce_temp = [
                msg['content'].lower() for msg in self.conversation_history[-4:]
                if msg['role'] == 'assistant'
            ]
            bruce_dijo_espero_temp = any('claro, espero' in msg or 'espero' in msg for msg in ultimos_mensajes_bruce_temp)

            if bruce_dijo_espero_temp and self.estado_conversacion == EstadoConversacion.BUSCANDO_ENCARGADO:
                # Persona nueva después de espera - SKIP FIX 384, dejar que FILTRO 5B maneje
                print(f"\n[EMOJI]  FIX 389: Saltando FIX 384 - Persona nueva después de transferencia")
                print(f"   Dejando que FILTRO 5B (FIX 289) maneje la re-presentación")
            elif skip_fix_384:
                # FIX 392/398: Cliente confirmó - NO ejecutar FIX 384 OPCIONAL
                # PERO: REGLAS CRÍTICAS ya se ejecutaron arriba
                print(f"\n[EMOJI]  FIX 392/398: Saltando FIX 384 OPCIONAL - Cliente confirmó")
                print(f"   (REGLAS CRÍTICAS ya verificadas)")
                print(f"   Cliente dijo: '{contexto_cliente[-60:] if len(contexto_cliente) > 60 else contexto_cliente}'")
                print(f"   GPT generó: '{respuesta[:80]}...'")
            else:
                # FIX 391: NO activar FIX 384 si GPT está pidiendo WhatsApp/correo correctamente
                # Detectar si GPT está pidiendo dato de contacto
                gpt_pide_contacto = any(frase in respuesta.lower() for frase in [
                    'cuál es su whatsapp', 'cual es su whatsapp',
                    'cuál es su número', 'cual es su numero',
                    'me confirma su whatsapp', 'me confirma su número',
                    'me puede proporcionar su correo', 'me proporciona su correo',
                    'me confirma su correo', 'cuál es su correo', 'cual es su correo',
                    'me podría proporcionar', 'dígame su correo', 'digame su correo'
                ])

                # FIX 418: NO aplicar FIX 384 si estamos en estado crítico (ENCARGADO_NO_ESTA)
                # Caso BRUCE1220: Cliente dijo "no hay", estado = ENCARGADO_NO_ESTA
                # FIX 384 sobrescribió con "Claro. Manejamos productos..." (incorrecto)
                estado_critico = self.estado_conversacion in [
                    EstadoConversacion.ENCARGADO_NO_ESTA,
                    EstadoConversacion.ENCARGADO_NO_ESTA
                ]

                # FIX 629C: BRUCE2063 - Si mensaje ACTUAL es despedida, NO aplicar FIX 384
                # Problema: FIX 384 usa contexto_cliente (todos los mensajes) y detecta "no está"
                # de turnos anteriores, pero el ACTUAL es "Hasta luego" → override con "¿catálogo?"
                ultimo_msg_actual_629 = ""
                for msg in reversed(self.conversation_history):
                    if msg['role'] == 'user':
                        ultimo_msg_actual_629 = msg['content'].lower().strip()
                        break
                frases_despedida_629c = ['hasta luego', 'adiós', 'adios', 'bye', 'nos vemos',
                                         'buenas noches', 'que tenga buen', 'que le vaya bien']
                msg_actual_es_despedida = any(f in ultimo_msg_actual_629 for f in frases_despedida_629c)

                if msg_actual_es_despedida:
                    print(f"\n   FIX 629C: Saltando FIX 384 - Mensaje ACTUAL es DESPEDIDA")
                    print(f"   Cliente dijo: '{ultimo_msg_actual_629[:50]}'")
                    print(f"   FIX 384 habría corregido basado en contexto viejo")
                elif estado_critico:
                    print(f"\n[EMOJI]  FIX 418: Saltando FIX 384 - Estado crítico: {self.estado_conversacion.value}")
                    print(f"   GPT debe manejar con contexto de estado")
                    print(f"   Cliente dijo: '{contexto_cliente[-80:] if len(contexto_cliente) > 80 else contexto_cliente}'")
                # Si GPT está pidiendo contacto, NO aplicar FIX 384
                elif gpt_pide_contacto:
                    print(f"\n[EMOJI]  FIX 391: Saltando FIX 384 - GPT está pidiendo WhatsApp/correo correctamente")
                    print(f"   GPT generó: '{respuesta[:80]}...'")
                else:
                    # FIX 384 normal
                    es_valida, razon = self._validar_sentido_comun(respuesta, contexto_cliente)

                    if not es_valida:
                        print(f"\n[EMOJI] FIX 384: VALIDADOR DE SENTIDO COMÚN ACTIVADO")
                        print(f"   Razón: {razon}")
                        print(f"   Cliente dijo: '{contexto_cliente[:100]}...'")
                        print(f"   Bruce iba a decir: '{respuesta[:80]}...'")

                        # Generar respuesta con sentido común basada en la razón
                        if "Cliente acaba de dar número" in razon:
                            respuesta = "Perfecto, muchas gracias. Le envío el catálogo en las próximas horas."
                        elif "Cliente acaba de dar correo" in razon:
                            respuesta = "Perfecto, muchas gracias. Le envío el catálogo por correo."
                        elif "Cliente dijo que encargado NO está" in razon or "salió a comer" in razon:
                            # FIX 392/393/400: Ofrecer alternativas (enviar catálogo o reprogramar)
                            # FIX 393: NO usar "Perfecto" cuando cliente rechaza
                            # FIX 400: Si cliente preguntó "¿De dónde habla?" + "no se encuentra", responder ambas
                            # FIX 513 BRUCE1580: Incluir "¿de qué empresa?" y "¿de qué marca?"
                            if any(patron in contexto_cliente.lower() for patron in [
                                '¿de dónde', 'de dónde', '¿de donde', 'de donde',
                                '¿de qué empresa', 'de qué empresa', '¿de que empresa', 'de que empresa',
                                '¿de qué marca', 'de qué marca', '¿de que marca', 'de que marca',
                                '¿qué empresa', 'qué empresa', '¿que empresa', 'que empresa'
                            ]):
                                respuesta = "Me comunico de la marca NIOVAL para ofrecer información de productos de ferretería. Entiendo que el encargado no se encuentra. ¿Le gustaría que le envíe el catálogo por WhatsApp para que lo revise cuando regrese?"
                            else:
                                respuesta = "Entiendo. ¿Le gustaría que le envíe el catálogo por WhatsApp para que lo revise el encargado cuando regrese?"
                        elif "Dice 'ya lo tengo' sin datos capturados" in razon:
                            respuesta = "Claro, con gusto. ¿Me confirma su número de WhatsApp para enviarle el catálogo?"
                        elif "Cliente preguntó algo y Bruce no respondió" in razon:
                            # Intentar responder la pregunta del cliente
                            if 'qué productos' in contexto_cliente or 'que productos' in contexto_cliente:
                                respuesta = "Manejamos grifería, cintas, herramientas y más productos de ferretería. ¿Le envío el catálogo completo por WhatsApp?"
                            else:
                                respuesta = "Claro. Manejamos productos de ferretería: grifería, cintas, herramientas. ¿Le envío el catálogo completo?"
                        elif "Cliente pidió reprogramar" in razon:
                            respuesta = "Perfecto. ¿A qué hora sería mejor que llame de nuevo?"
                        elif "Cliente está buscando encargado" in razon:
                            # NO decir nada - esperar
                            respuesta = ""  # Silencio
                        else:
                            # Error genérico - solicitar dato faltante
                            respuesta = "Perfecto. ¿Me confirma su número de WhatsApp para enviarle el catálogo?"

                        filtro_aplicado = True
                        print(f"   Respuesta corregida: '{respuesta}'")

        # ============================================================
        # FILTRO 0 (FIX 298/301): CRÍTICO - Evitar despedida/asunciones prematuras
        # Si estamos muy temprano en la conversación (< 4 mensajes) y Bruce
        # intenta despedirse O asume cosas que el cliente NO dijo, BLOQUEAR
        # ============================================================
        num_mensajes_total = len(self.conversation_history)
        num_mensajes_bruce = len([m for m in self.conversation_history if m['role'] == 'assistant'])

        # Detectar si Bruce intenta despedirse
        frases_despedida = [
            'que tenga excelente día', 'que tenga excelente dia', 'que tenga buen día', 'que tenga buen dia',
            'le marco entonces', 'muchas gracias por su tiempo', 'gracias por la información',
            'hasta luego', 'hasta pronto', 'que le vaya bien', 'buen día', 'buenas tardes',
            'me despido', 'fue un gusto'
        ]

        # FIX 301: También detectar cuando Bruce ASUME que cliente está ocupado/no interesado
        frases_asuncion_prematura = [
            'entiendo que está ocupado', 'entiendo que esta ocupado',
            'entiendo que no le interesa', 'entiendo que no tiene tiempo',
            'veo que está ocupado', 'veo que esta ocupado',
            'comprendo que está ocupado', 'comprendo que esta ocupado'
        ]

        bruce_intenta_despedirse = any(frase in respuesta_lower for frase in frases_despedida)
        bruce_asume_cosas = any(frase in respuesta_lower for frase in frases_asuncion_prematura)

        # Si es muy temprano (< 4 mensajes de Bruce) y NO tenemos contacto capturado
        # FIX 307: Usar lead_data en lugar de atributos inexistentes
        tiene_contacto = bool(self.lead_data.get("whatsapp")) or bool(self.lead_data.get("email"))

        if (bruce_intenta_despedirse or bruce_asume_cosas) and num_mensajes_bruce < 4 and not tiene_contacto:
            # FIX 419: NO aplicar FIX 298/301 si estamos en estado crítico (ENCARGADO_NO_ESTA)
            # Caso BRUCE1235: Cliente dijo "ahorita no se encuentra" → Estado = ENCARGADO_NO_ESTA
            # GPT generó: "Entiendo que está ocupado. ¿Le gustaría que le envíe el catá..."
            # FIX 298/301 sobrescribió con pregunta del encargado (INCORRECTO)
            # GPT debe manejar con contexto de estado, FIX 298/301 NO debe sobrescribir
            estado_critico_298 = self.estado_conversacion in [
                EstadoConversacion.ENCARGADO_NO_ESTA,
            ]

            if estado_critico_298:
                print(f"\n[EMOJI]  FIX 419: Saltando FIX 298/301 - Estado crítico: {self.estado_conversacion.value}")
                print(f"   GPT debe manejar con contexto de estado")
                print(f"   Bruce iba a decir: '{respuesta[:60]}...'")
                # NO sobrescribir - dejar respuesta de GPT
            else:
                # Verificar último mensaje del cliente para ver si es rechazo real
                ultimos_cliente = [m['content'].lower() for m in self.conversation_history[-2:] if m['role'] == 'user']
                ultimo_cliente = ultimos_cliente[-1] if ultimos_cliente else ""

                # Patrones de rechazo REAL (el cliente NO quiere hablar)
                rechazo_real = any(frase in ultimo_cliente for frase in [
                    'no gracias', 'no me interesa', 'no necesito', 'estoy ocupado', 'no tengo tiempo',
                    'no moleste', 'no llame', 'quite mi número', 'no vuelva a llamar', 'cuelgo'
                ])

                # FIX 301: "Gracias" solo NO es rechazo - es cortesía
                es_solo_gracias = ultimo_cliente.strip() in ['gracias', 'gracias.', 'muchas gracias', 'ok gracias']

                # FIX 325/390/392: Detectar si cliente PIDE información por correo/WhatsApp
                # O si ofrece DEJAR RECADO (oportunidad de capturar contacto)
                cliente_pide_info_contacto = any(frase in ultimo_cliente for frase in [
                    'por correo', 'por whatsapp', 'por wasa', 'enviar la información',
                    'enviar la informacion', 'mandar la información', 'mandar la informacion',
                    'me puedes enviar', 'me puede enviar', 'envíame', 'enviame',
                    'mándame', 'mandame', 'enviarme', 'mandarme',
                    # FIX 390: Agregar patrones faltantes (caso BRUCE1083)
                    'al correo', 'mándanos al correo', 'mandanos al correo',
                    'envíalo al correo', 'envialo al correo', 'mándalo al correo', 'mandalo al correo',
                    'mándanos la', 'mandanos la', 'nos puede mandar', 'nos puede enviar',
                    'envíanos', 'envianos', 'mándanos', 'mandanos',
                    # FIX 392: Agregar "dejar recado" (caso BRUCE1096)
                    'dejar recado', 'dejar mensaje', 'dejarle recado', 'dejarle mensaje',
                    'guste dejar recado', 'gusta dejar recado', 'quiere dejar recado',
                    'quieren dejar recado', 'quiere dejarle'
                ])

                if not rechazo_real or es_solo_gracias:
                    tipo_problema = "asume cosas" if bruce_asume_cosas else "despedida prematura"
                    print(f"\n[EMOJI] FIX 298/301: CRÍTICO - Bruce {tipo_problema}")
                    print(f"   Mensajes de Bruce: {num_mensajes_bruce} (< 4)")
                    print(f"   Tiene contacto: {tiene_contacto}")
                    print(f"   Último cliente: '{ultimo_cliente[:50]}'")
                    print(f"   Bruce iba a decir: '{respuesta[:60]}...'")

                    # FIX 325/390: Si cliente pidió info por correo/WhatsApp, pedir el dato
                    if cliente_pide_info_contacto:
                        # FIX 390: Detectar CORREO con patrones expandidos
                        if any(p in ultimo_cliente for p in ['por correo', 'al correo', 'correo electrónico', 'correo electronico']):
                            respuesta = "Claro, con gusto. ¿Me puede proporcionar su correo electrónico para enviarle el catálogo?"
                            print(f"   FIX 325/390: Cliente pidió por CORREO - pidiendo email")
                        else:
                            respuesta = "Claro, con gusto. ¿Me confirma su número de WhatsApp para enviarle el catálogo?"
                            print(f"   FIX 325/390: Cliente pidió por WHATSAPP - pidiendo número")
                    else:
                        # FIX 459: BRUCE1381 - Verificar si Bruce YA preguntó por el encargado
                        # Si ya preguntó, NO volver a preguntar (evita doble pregunta)
                        historial_bruce_459 = ' '.join([
                            msg['content'].lower() for msg in self.conversation_history[-4:]
                            if msg['role'] == 'assistant'
                        ])
                        bruce_ya_pregunto_encargado = any(frase in historial_bruce_459 for frase in [
                            'encargado de compras', 'encargada de compras',
                            '¿se encontrará el encargado', '¿se encuentra el encargado',
                            'se encontrara el encargado', 'se encuentra el encargado'
                        ])

                        if bruce_ya_pregunto_encargado:
                            # FIX 459: Ya preguntó por encargado - usar respuesta contextual
                            print(f"   [OK] FIX 459: Bruce YA preguntó por encargado - NO volver a preguntar")
                            # Verificar si cliente indicó que no está el encargado
                            encargado_no_esta = any(frase in ultimo_cliente for frase in [
                                'no está', 'no esta', 'no se encuentra', 'salió', 'salio',
                                'por el momento no', 'ahorita no', 'no hay'
                            ])
                            if encargado_no_esta:
                                respuesta = "Entiendo. ¿A qué hora puedo llamar para contactarlo?"
                                print(f"   FIX 459: Encargado no está - preguntando horario")
                            else:
                                # Cliente dio respuesta parcial/confusa - usar respuesta de GPT
                                print(f"   FIX 459: Usando respuesta original de GPT")
                                filtro_aplicado = False  # Dejar respuesta de GPT
                        else:
                            # Continuar la conversación normalmente
                            respuesta = "Claro. ¿Se encontrará el encargado o encargada de compras para brindarle información de nuestros productos?"
                    if filtro_aplicado != False:  # FIX 459: Solo marcar si no se desactivó
                        filtro_aplicado = True
                    print(f"   Respuesta corregida: \"{respuesta}\"")

        # ============================================================
        # FILTRO 1 (FIX 226/251): Si ya tenemos correo, NO repetirlo ni pedir WhatsApp
        # ============================================================
        email_capturado = self.lead_data.get("email", "")
        if email_capturado:
            # FIX 251: Patrones expandidos para detectar repetición de correo
            patrones_repetir_correo = [
                r'confirmar.*correo',
                r'confirmar.*email',
                r'confirmar.*es\s+\w+.*@',
                r'enviar[ée].*al?\s+correo',
                r'enviar[ée].*por\s+correo',  # FIX 251: "enviaré por correo"
                r'enviar[ée].*a\s+\w+.*@',
                r'catálogo.*a\s+\w+.*@',
                r'catálogo.*al?\s+correo',
                r'catálogo.*por\s+correo',  # FIX 251: "catálogo por correo"
                r'correo.*a\s+\w+\s*@',  # FIX 251: "correo a usuario@..."
                r'por\s+correo\s+a\s+',  # FIX 251: "por correo a [email]"
                r'@.*punto\s*com',
                r'@.*gmail',
                r'@.*hotmail',
                r'@.*yahoo',
                r'@.*outlook',
                r'arroba',
                r'puedo\s+confirmar',
                r'le\s+confirmo\s+que',
                r'es\s+correcto.*correo',
            ]

            for patron in patrones_repetir_correo:
                if re.search(patron, respuesta_lower):
                    print(f"\n[EMOJI] FIX 226/251: FILTRO ACTIVADO - Bruce intentó repetir correo")
                    print(f"   Respuesta original: \"{respuesta[:80]}...\"")
                    respuesta = "Perfecto, ya lo tengo registrado. Le llegará el catálogo en las próximas horas. Muchas gracias por su tiempo, que tenga excelente día."
                    filtro_aplicado = True
                    print(f"   Respuesta corregida: \"{respuesta}\"")
                    break

            # FIX 252: Bloquear si Bruce menciona el email capturado literalmente
            if not filtro_aplicado and email_capturado:
                # Normalizar email para búsqueda (quitar espacios, hacer lowercase)
                email_normalizado = email_capturado.lower().replace(" ", "")

                # Buscar partes del email en la respuesta
                # Ejemplo: "facturacion@gmail.com" → buscar "facturacion", "gmail"
                partes_email = email_normalizado.split("@")
                if len(partes_email) == 2:
                    usuario = partes_email[0]  # "facturacion"
                    dominio = partes_email[1].split(".")[0]  # "gmail"

                    # Si Bruce menciona el nombre de usuario del email (>4 chars)
                    if len(usuario) > 4 and usuario in respuesta_lower.replace(" ", ""):
                        print(f"\n[EMOJI] FIX 252: FILTRO ACTIVADO - Bruce mencionó email capturado ('{usuario}')")
                        print(f"   Email capturado: {email_capturado}")
                        print(f"   Respuesta original: \"{respuesta[:80]}...\"")
                        respuesta = "Perfecto, ya lo tengo registrado. Le llegará el catálogo en las próximas horas. Muchas gracias por su tiempo, que tenga excelente día."
                        filtro_aplicado = True
                        print(f"   Respuesta corregida: \"{respuesta}\"")

            # Patrones que indican que Bruce pide WhatsApp cuando ya tiene correo
            if not filtro_aplicado:
                patrones_pedir_whatsapp = [
                    r'whatsapp',
                    r'wats',
                    r'número.*celular',
                    r'celular.*número',
                    r'enviar.*por.*mensaje',
                    r'mensaje.*texto',
                    r'también.*por',
                    r'además.*por',
                ]

                for patron in patrones_pedir_whatsapp:
                    if re.search(patron, respuesta_lower):
                        print(f"\n[EMOJI] FIX 226: FILTRO ACTIVADO - Bruce pidió WhatsApp pero ya tiene correo")
                        print(f"   Respuesta original: \"{respuesta[:80]}...\"")
                        respuesta = "Perfecto, ya lo tengo registrado. Le llegará el catálogo en las próximas horas. Muchas gracias por su tiempo, que tenga excelente día."
                        filtro_aplicado = True
                        print(f"   Respuesta corregida: \"{respuesta}\"")
                        break

        # ============================================================
        # FILTRO 1B (FIX 516 BRUCE1619 + FIX 510 BRUCE1724): No preguntar WhatsApp si cliente dijo que NO tiene
        # ============================================================
        if not filtro_aplicado and self.lead_data.get("sin_whatsapp"):
            # Si cliente ya dijo "no tenemos WhatsApp" y Bruce vuelve a preguntar → corregir
            patrones_preguntar_whatsapp = [
                r'whatsapp', r'watsapp', r'wats', r'wasa',
                r'su\s+número.*enviar', r'número.*catálogo',
                r'confirma.*número', r'me\s+da.*número'
            ]
            for patron in patrones_preguntar_whatsapp:
                if re.search(patron, respuesta_lower):
                    print(f"\n[PHONE] FIX 516/510: FILTRO ACTIVADO - Bruce preguntó WhatsApp pero cliente dijo que NO tiene")
                    print(f"   Respuesta original: \"{respuesta[:80]}...\"")
                    # FIX 510 BRUCE1724: Si cliente indicó que es teléfono fijo, pedir teléfono no correo
                    if self.lead_data.get("es_telefono_fijo"):
                        respuesta = "Disculpe, ¿me podría repetir el número de teléfono?"
                        print(f"   FIX 510: Cliente indicó teléfono fijo, pidiendo teléfono")
                    else:
                        respuesta = "Entendido. ¿Me puede dar un correo electrónico para enviarle la información?"
                    filtro_aplicado = True
                    print(f"   Respuesta corregida: \"{respuesta}\"")
                    break

        # ============================================================
        # FILTRO 2: Detectar números aleatorios/sin sentido
        # ============================================================
        if not filtro_aplicado:
            # Detectar si Bruce menciona un número de teléfono que no corresponde al cliente
            numeros_en_respuesta = re.findall(r'\b\d{7,12}\b', respuesta)
            if numeros_en_respuesta:
                # Verificar si el número es del cliente actual
                numero_cliente = self.lead_data.get('telefono', '') or ''
                numero_cliente_limpio = re.sub(r'\D', '', numero_cliente)

                for num in numeros_en_respuesta:
                    if num not in numero_cliente_limpio and numero_cliente_limpio not in num:
                        print(f"\n[EMOJI] FIX 226: FILTRO ACTIVADO - Bruce mencionó número aleatorio: {num}")
                        print(f"   Respuesta original: \"{respuesta[:80]}...\"")
                        # Remover el número de la respuesta
                        respuesta = re.sub(r'\b\d{7,12}\b', '', respuesta)
                        respuesta = re.sub(r'\s+', ' ', respuesta).strip()
                        filtro_aplicado = True
                        print(f"   Respuesta corregida: \"{respuesta}\"")

        # ============================================================
        # FILTRO 3: Respuestas muy largas o sin sentido
        # ============================================================
        if not filtro_aplicado:
            # Si la respuesta es muy larga (>200 chars) y tiene patrón de repetición
            if len(respuesta) > 200:
                palabras = respuesta.split()
                # Contar palabras repetidas
                from collections import Counter
                conteo = Counter(palabras)
                palabras_repetidas = sum(1 for c in conteo.values() if c > 3)

                if palabras_repetidas > 5:
                    print(f"\n[EMOJI] FIX 226: FILTRO ACTIVADO - Respuesta con repeticiones excesivas")
                    print(f"   Respuesta original: \"{respuesta[:80]}...\"")
                    respuesta = "Entiendo. ¿Le gustaría que le envíe el catálogo por correo electrónico?"
                    filtro_aplicado = True
                    print(f"   Respuesta corregida: \"{respuesta}\"")

        # ============================================================
        # FILTRO 4 (FIX 234/297): Cliente dice "¿Bueno?" - pero NO repetir "¿me escucha?"
        # FIX 297: Evitar bucle donde Bruce pregunta "¿me escucha?" múltiples veces
        # ============================================================
        if not filtro_aplicado:
            ultimos_mensajes_cliente = [
                msg['content'].lower() for msg in self.conversation_history[-3:]
                if msg['role'] == 'user'
            ]

            # FIX 297: Verificar si Bruce YA preguntó "¿me escucha?" antes
            mensajes_bruce_recientes = [
                msg['content'].lower() for msg in self.conversation_history[-6:]
                if msg['role'] == 'assistant'
            ]
            bruce_ya_pregunto_escucha = any(
                'me escucha' in msg or 'me escuchas' in msg or 'me oye' in msg
                for msg in mensajes_bruce_recientes
            )

            if ultimos_mensajes_cliente:
                ultimo_cliente = ultimos_mensajes_cliente[-1]

                # Detectar si el cliente solo dice "bueno" repetido (no escuchó)
                patron_bueno_repetido = r'^[\s\?\¿]*bueno[\s\?\¿]*(?:bueno[\s\?\¿]*)*$'
                solo_dice_bueno = bool(re.match(patron_bueno_repetido, ultimo_cliente.strip()))

                # También detectar variaciones
                patrones_no_escucho = [
                    r'^\s*\¿?\s*bueno\s*\??\s*$',  # Solo "¿Bueno?"
                    r'bueno.*bueno.*bueno',  # "¿Bueno? ¿Bueno? ¿Bueno?"
                    r'^\s*\¿?\s*hola\s*\??\s*$',  # Solo "¿Hola?"
                    r'^\s*\¿?\s*s[ií]\s*\??\s*$',  # Solo "¿Sí?"
                    r'^\s*\¿?\s*alo\s*\??\s*$',  # Solo "¿Aló?"
                    r'^\s*\¿?\s*diga\s*\??\s*$',  # Solo "¿Diga?"
                ]

                cliente_no_escucho = solo_dice_bueno or any(re.search(p, ultimo_cliente) for p in patrones_no_escucho)

                # FIX 297/351: Si Bruce YA preguntó "¿me escucha?" o ya se presentó, NO repetir
                # En su lugar, continuar con la presentación diferente
                bruce_ya_se_presento = any(
                    'soy bruce de la marca' in msg or 'usted es el encargado' in msg
                    for msg in mensajes_bruce_recientes
                )

                if cliente_no_escucho:
                    if bruce_ya_pregunto_escucha or bruce_ya_se_presento:
                        # Ya preguntamos o ya nos presentamos, usar frase DIFERENTE
                        print(f"\n[EMOJI] FIX 297/351: Cliente sigue diciendo '{ultimo_cliente}' pero Bruce YA se presentó")
                        print(f"   Usando frase diferente para evitar repetición")
                        # FIX 351: Alternar entre diferentes frases
                        if 'se encontrará el encargado' in ' '.join(mensajes_bruce_recientes):
                            respuesta = "Sí, aquí sigo. ¿Me puede escuchar bien?"
                        else:
                            respuesta = "Le llamo de la marca NIOVAL, productos de ferretería. ¿Se encontrará el encargado de compras?"
                        filtro_aplicado = True
                        print(f"   Respuesta corregida: \"{respuesta}\"")
                    elif 'nioval' in respuesta_lower:
                        # Primera vez: confirmar presencia
                        print(f"\n[EMOJI] FIX 234: FILTRO ACTIVADO - Cliente no escuchó, dice '{ultimo_cliente}'")
                        print(f"   Bruce iba a repetir presentación")
                        respuesta = "Sí, ¿me escucha? Le llamo de la marca NIOVAL."
                        filtro_aplicado = True
                        print(f"   Respuesta corregida: \"{respuesta}\"")

        # ============================================================
        # FILTRO 5 (FIX 235/237/249/337): Cliente dice "permítame/espere" - protocolo espera
        # FIX 337: Revisar últimos 4 mensajes para mejor detección
        # ============================================================
        if not filtro_aplicado:
            ultimos_mensajes_cliente = [
                msg['content'].lower() for msg in self.conversation_history[-4:]
                if msg['role'] == 'user'
            ]

            if ultimos_mensajes_cliente:
                # FIX 337: Revisar todos los mensajes recientes, no solo el último
                ultimo_cliente = ultimos_mensajes_cliente[-1]
                contexto_espera = ' '.join(ultimos_mensajes_cliente[-2:]) if len(ultimos_mensajes_cliente) >= 2 else ultimo_cliente

                # FIX 249/256/261/318/357: Detectar negaciones/rechazos que invalidan "ahorita"
                # Si cliente dice "ahorita tenemos cerrado", NO es espera
                # FIX 318: "No, no está ahorita" - el encargado NO está
                # FIX 357: "ahorita no nos interesa" - es rechazo, NO espera
                patrones_negacion = [
                    r'cerrado', r'no\s+est[aá]', r'no\s+se\s+encuentra',
                    r'no\s+hay', r'no\s+tenemos', r'no\s+puede',
                    r'ocupado', r'no\s+disponible',
                    # FIX 357: "ahorita no nos interesa", "no me interesa"
                    r'no\s+(?:me|nos|le)?\s*interesa',  # "no nos interesa"
                    r'ahorita\s+no\s+(?:me|nos|le)?\s*interesa',  # "ahorita no nos interesa"
                    r'no\s+(?:estoy|estamos)\s+interesad[oa]',  # "no estamos interesados"
                    r'no\s+(?:necesito|necesitamos)',  # "no necesitamos"
                    r'no\s+(?:gracias|thank)',  # "no gracias"
                    # FIX 358: "no te encuentro ahorita" = encargado NO está
                    r'no\s+(?:te|lo|la|le)\s+encuentr[oa]',  # "no te encuentro"
                    r'no\s+(?:te|lo|la|le)\s+encuentr[oa]\s+ahorita',  # "no te encuentro ahorita"
                    r'no,?\s*no,?\s*ahorita\s+no',  # "No, no, ahorita no"
                    # FIX 318: Patrones más específicos para "no está ahorita"
                    r'no,?\s*no\s+est[aá]',  # "No, no está ahorita"
                    r'no\s+est[aá]\s+ahorita',  # "no está ahorita"
                    r'ahorita\s+no\s+est[aá]',  # "ahorita no está"
                    # FIX 256: Patrones específicos para encargado
                    r'(?:encargado|jefe|gerente).*(?:no\s+est[aá]|sali[oó]|se\s+fue)',
                    r'(?:no\s+est[aá]|sali[oó]|se\s+fue).*(?:encargado|jefe|gerente)',
                    r'ya\s+sali[oó]', r'se\s+fue', r'est[aá]\s+fuera',
                    # FIX 261: Patrones de horario de llegada (implica que ahora NO está)
                    # FIX 429: Agregar "encuentra" y "está" para casos como "se encuentra hasta las 5"
                    r'(?:entra|llega|viene|encuentra|est[aá])\s+(?:a\s+las?|hasta\s+las?)\s*\d',
                    r'(?:entra|llega|viene|encuentra|est[aá])\s+(?:en\s+la\s+)?(?:tarde|mañana|noche)',
                    r'hasta\s+las?\s*\d',  # "hasta las 9"
                    r'(?:después|despues)\s+de\s+las?\s*\d',  # "después de las 9"
                    r'(?:m[aá]s\s+)?tarde',  # "más tarde"
                    r'(?:en\s+)?(?:un\s+)?rato',  # "en un rato"
                    r'(?:no\s+)?(?:tod[ao])?v[ií]a\s+no',  # "todavía no"
                    # FIX 614: BRUCE2029 - Detectar "NO + verbo modal + esperar"
                    # Caso: "No necesitaría esperar que vuelva" → NO es solicitud de espera
                    r'no\s+(?:necesit|pod|deber|quier|puedes?|puede)[a-záéíóúüñ]*\s+esperar',  # "no necesitaría esperar"
                    r'no\s+(?:necesit|pod|deber|quier)[a-záéíóúüñ]*\s+que\s+.*esperar',  # "no necesitaría que esperar"
                ]

                tiene_negacion = any(re.search(p, ultimo_cliente) for p in patrones_negacion)

                # FIX 237: Patrones más completos que indican que cliente pide esperar
                patrones_espera = [
                    r'perm[ií]t[ae]me', r'perm[ií]tame',
                    r'me\s+permite', r'me\s+permites',
                    r'esp[eé]r[ae]me', r'espera',
                    r'un\s+momento', r'un\s+segundito', r'un\s+segundo',
                    r'dame\s+chance', r'd[ée]jame',
                    r'aguanta', r'tantito',
                ]

                # FIX 249/256: Solo detectar "ahorita" si NO hay negación
                # FIX 256: Corregir bug - usar regex en lugar de 'in'
                if re.search(r'\bahorita\b', ultimo_cliente) and not tiene_negacion:
                    patrones_espera.append(r'\bahorita\b')

                # FIX 337: Buscar en último mensaje Y en contexto reciente
                cliente_pide_espera = any(re.search(p, ultimo_cliente) for p in patrones_espera)
                cliente_pide_espera_contexto = any(re.search(p, contexto_espera) for p in patrones_espera)

                # FIX 249/389: NO activar filtro si hay negación O si es persona nueva
                # FIX 389: Si estado es BUSCANDO_ENCARGADO (persona nueva), NO activar espera
                es_persona_nueva_estado = (self.estado_conversacion == EstadoConversacion.BUSCANDO_ENCARGADO)

                # FIX 614: BRUCE2029 - NO activar si cliente hace PREGUNTA
                # Caso: "¿Necesitas esperar que vuelva?" → NO es solicitud de espera
                es_pregunta = '¿' in ultimo_cliente or ultimo_cliente.strip().endswith('?')

                # FIX 614: BRUCE2029 - NO activar si Bruce ya dijo "Claro, espero" (anti-loop)
                # Caso: Bruce dijo "Claro, espero" dos veces seguidas
                ultimos_bruce_614 = [
                    msg['content'].lower() for msg in self.conversation_history[-4:]
                    if msg['role'] == 'assistant'
                ]
                bruce_ya_dijo_espero_614 = any('claro, espero' in msg or 'claro espero' in msg for msg in ultimos_bruce_614[-2:])

                if (cliente_pide_espera or cliente_pide_espera_contexto) and not tiene_negacion and not es_persona_nueva_estado and not es_pregunta and not bruce_ya_dijo_espero_614:
                    print(f"\n[EMOJI] FIX 235/237/249/337: FILTRO ACTIVADO - Cliente pide esperar: '{ultimo_cliente}'")
                    respuesta = "Claro, espero."
                    filtro_aplicado = True
                    print(f"   Respuesta: \"{respuesta}\"")
                elif cliente_pide_espera and tiene_negacion:
                    print(f"\n[EMOJI] FIX 249: NO activar espera - Cliente dice 'ahorita' pero con negación: '{ultimo_cliente}'")
                elif cliente_pide_espera and es_pregunta:
                    print(f"\n[EMOJI] FIX 614.1: NO activar espera - Cliente hace PREGUNTA: '{ultimo_cliente}'")
                elif cliente_pide_espera and bruce_ya_dijo_espero_614:
                    print(f"\n[EMOJI] FIX 614.2: NO activar espera - Bruce YA dijo 'Claro, espero' - evitar loop")

        # ============================================================
        # FILTRO 5B (FIX 287/289): Persona nueva después de transferencia
        # Si Bruce estaba esperando y llega persona nueva preguntando
        # "¿Con quién hablo?" o "¿Bueno?", Bruce debe RE-PRESENTARSE
        # ============================================================
        if not filtro_aplicado:
            ultimos_mensajes_bruce = [
                msg['content'].lower() for msg in self.conversation_history[-4:]
                if msg['role'] == 'assistant'
            ]
            ultimos_mensajes_cliente = [
                msg['content'].lower() for msg in self.conversation_history[-2:]
                if msg['role'] == 'user'
            ]

            # Detectar si Bruce estaba esperando (transferencia de llamada)
            bruce_dijo_espero = any(
                frase in msg for msg in ultimos_mensajes_bruce
                for frase in ['claro, espero', 'claro, aquí espero', 'espero', 'claro que sí, espero', 'perfecto, espero']
            )

            if bruce_dijo_espero and len(ultimos_mensajes_cliente) > 0:
                ultimo_cliente = ultimos_mensajes_cliente[-1]

                # FIX 289: Detectar si es PERSONA NUEVA (encargado transferido)
                # Indicadores: pregunta quién habla, dice bueno/hola como si fuera nuevo
                es_persona_nueva = any(
                    frase in ultimo_cliente
                    for frase in ['con quién hablo', 'con quien hablo', 'quién habla', 'quien habla',
                                  'de dónde', 'de donde', 'de parte de quién', 'de parte de quien',
                                  'soy el encargado', 'soy la encargada', 'aquí estoy', 'aqui estoy']
                )

                # FIX 344: También puede ser persona nueva si dice "dígame", "sí dígame", "bueno", etc.
                # Esto indica que el encargado ya fue transferido y espera que Bruce hable
                saludos_persona_nueva = [
                    'bueno', '¿bueno?', 'hola', '¿hola?', 'sí', 'si',
                    'dígame', 'digame', 'sí dígame', 'si digame', 'sí, dígame', 'si, digame',
                    'mande', 'a ver', 'a ver dígame', 'qué pasó', 'que paso',
                    'sí bueno', 'si bueno', 'alo', 'aló'
                ]
                es_saludo_nuevo = any(ultimo_cliente.strip() == s or ultimo_cliente.strip().startswith(s + '.') for s in saludos_persona_nueva)

                if es_persona_nueva or (es_saludo_nuevo and bruce_dijo_espero):
                    print(f"\n[EMOJI] FIX 289: PERSONA NUEVA detectada después de transferencia")
                    print(f"   Cliente dice: '{ultimo_cliente}'")
                    print(f"   Bruce iba a decir: '{respuesta[:60]}...'")
                    # Re-presentarse brevemente
                    respuesta = "Sí, buen día. Soy Bruce de la marca NIOVAL, productos de ferretería. ¿Usted es el encargado de compras?"
                    filtro_aplicado = True
                    print(f"   Respuesta corregida: \"{respuesta}\"")

        # ============================================================
        # FILTRO 5C (FIX 291/369): Cliente menciona sucursal/matriz/mostrador
        # Si GPT quiere despedirse O ofrecer catálogo pero cliente mencionó
        # sucursal/matriz/mostrador, Bruce debe pedir número de matriz/oficinas
        # FIX 369: Agregar "puro mostrador" como indicador de no hay encargado
        # ============================================================
        if not filtro_aplicado:
            ultimos_mensajes_cliente = [
                msg['content'].lower() for msg in self.conversation_history[-3:]
                if msg['role'] == 'user'
            ]

            if ultimos_mensajes_cliente:
                # Concatenar últimos mensajes para buscar contexto completo
                contexto_cliente = ' '.join(ultimos_mensajes_cliente)

                # Detectar si cliente menciona sucursal/matriz/oficinas
                # FIX 369/373: Agregar patrones de "solo mostrador" / "puro distribución"
                menciona_redireccion = any(
                    frase in contexto_cliente
                    for frase in ['sucursal', 'matriz', 'oficinas', 'corporativo', 'área de compras',
                                  'no es de compras', 'no compramos aquí', 'no compramos aqui',
                                  'ir a la', 'tendré que', 'tendre que', 'tendría que', 'tendria que',
                                  # FIX 369: Patrones de "solo mostrador"
                                  'puro mostrador', 'solo mostrador', 'somos mostrador',
                                  'empleado de mostrador', 'empleados de mostrador',
                                  'puro empleo de mostrador', 'somos puro empleo',
                                  'no tenemos encargado', 'no hay encargado',
                                  'aquí no hay', 'aqui no hay', 'no manejamos compras',
                                  'no hacemos compras', 'no compramos nosotros',
                                  # FIX 373: Patrones de "solo distribución"
                                  'no nos dedicamos a las compras', 'no nos dedicamos a compras',
                                  'somos distribución', 'somos distribucion', 'solo distribución',
                                  'solo distribucion', 'nada más distribución', 'nada mas distribucion',
                                  'únicamente distribución', 'unicamente distribucion',
                                  'pura distribución', 'pura distribucion']
                )

                # Detectar si GPT quiere despedirse/colgar O ignorar y ofrecer catálogo
                bruce_quiere_despedirse = any(
                    frase in respuesta_lower
                    for frase in ['error con el número', 'error con el numero', 'número equivocado', 'numero equivocado',
                                  'disculpe las molestias', 'buen día', 'buen dia', 'hasta luego',
                                  'gracias por su tiempo', 'que tenga']
                )

                # FIX 369: También activar si Bruce ofrece catálogo ignorando que no hay encargado
                bruce_ofrece_catalogo_ignorando = any(
                    frase in respuesta_lower
                    for frase in ['le gustaría recibir', 'le gustaria recibir',
                                  'catálogo por whatsapp', 'catalogo por whatsapp',
                                  'whatsapp o correo']
                )

                # FIX 373: También activar si Bruce dice "Claro, espero" ignorando que no manejan compras
                bruce_dice_espero_ignorando = 'claro, espero' in respuesta_lower or 'claro espero' in respuesta_lower

                if menciona_redireccion and (bruce_quiere_despedirse or bruce_ofrece_catalogo_ignorando or bruce_dice_espero_ignorando):
                    print(f"\n[EMOJI] FIX 291/369/373: FILTRO ACTIVADO - Cliente mencionó sucursal/matriz/mostrador/distribución")
                    print(f"   Contexto: '{contexto_cliente[:80]}...'")
                    print(f"   Bruce iba a decir: '{respuesta[:60]}...'")
                    respuesta = "Entiendo. ¿Me podría proporcionar el número de las oficinas o del área de compras para contactarlos?"
                    filtro_aplicado = True
                    print(f"   Respuesta corregida: \"{respuesta}\"")

        # ============================================================
        # FILTRO 5D (FIX 379): Cliente dice que ELLOS no manejan productos de ferretería
        # Bruce NO debe decir "no manejamos" (invirtiendo el sujeto)
        # ============================================================
        if not filtro_aplicado:
            ultimos_mensajes_cliente = [
                msg['content'].lower() for msg in self.conversation_history[-3:]
                if msg['role'] == 'user'
            ]

            if ultimos_mensajes_cliente:
                contexto_cliente = ' '.join(ultimos_mensajes_cliente)

                # FIX 379: Detectar cuando CLIENTE dice que ELLOS no manejan productos
                cliente_dice_no_manejan = any(frase in contexto_cliente for frase in [
                    'no lo manejamos', 'no los manejamos', 'no manejamos',
                    'no la manejamos', 'no las manejamos',
                    'no trabajamos', 'no vendemos', 'no tenemos',
                    'tipo de producto no', 'ese producto no',
                    'esos productos no', 'ese tipo de'
                ])

                # Detectar si Bruce invierte el sujeto diciendo "no manejamos"
                bruce_invierte_sujeto = any(frase in respuesta_lower for frase in [
                    'actualmente no manejamos', 'no manejamos ese',
                    'no manejamos ese tipo', 'no manejamos tubería',
                    'no manejamos eso'
                ])

                if cliente_dice_no_manejan and bruce_invierte_sujeto:
                    print(f"\n[EMOJI] FIX 379: FILTRO ACTIVADO - Bruce invierte sujeto ('no manejamos' → 'ustedes no manejan')")
                    print(f"   Cliente dijo: '{contexto_cliente[:80]}...'")
                    print(f"   Bruce iba a decir: '{respuesta[:60]}...'")
                    respuesta = "Entiendo que ustedes no manejan ese tipo de producto actualmente. Aún así, le puedo enviar nuestro catálogo completo de ferretería por WhatsApp por si en el futuro les interesa. ¿Le parece?"
                    filtro_aplicado = True
                    print(f"   Respuesta corregida: '{respuesta}'")

        # ============================================================
        # FILTRO 6 (FIX 231): Detectar cuando cliente quiere dar correo
        # ============================================================
        if not filtro_aplicado:
            # Ver último mensaje del cliente
            ultimos_mensajes_cliente = [
                msg['content'].lower() for msg in self.conversation_history[-3:]
                if msg['role'] == 'user'
            ]

            if ultimos_mensajes_cliente:
                ultimo_cliente = ultimos_mensajes_cliente[-1]

                # Patrones que indican que el cliente quiere dar su correo
                # FIX 343: Agregar "te comparto un correo" y variantes
                patrones_dar_correo = [
                    r'correo\s+electr[oó]nico',
                    r'por\s+correo',
                    r'mi\s+correo',
                    r'el\s+correo',
                    r'te\s+(doy|paso)\s+(el\s+)?correo',
                    r'le\s+(doy|paso)\s+(el\s+)?correo',
                    r'te\s+comparto\s+(un\s+)?correo',  # FIX 343: "te comparto un correo"
                    r'le\s+comparto\s+(un\s+)?correo',  # FIX 343: "le comparto un correo"
                    r'comparto\s+(un\s+)?correo',       # FIX 343: "comparto un correo"
                    r'env[ií](a|e)\s+(tu|su)\s+informaci[oó]n',  # FIX 343: "envíe su información"
                    r'para\s+que\s+env[ií](a|e)s?\s+(tu|su)',    # FIX 343: "para que envíes tu info"
                    r'anota\s+(el\s+)?correo',
                    r'apunta\s+(el\s+)?correo',
                    r'email',
                    r'mail',
                    r'@',  # Si menciona arroba
                    r'arroba',  # FIX 280: Detectar "arroba" como palabra
                    r'punto\s*com',  # FIX 280: Detectar "punto com"
                    r'gmail',
                    r'hotmail',
                    r'outlook',
                    r'yahoo',
                ]

                cliente_quiere_dar_correo = any(re.search(p, ultimo_cliente) for p in patrones_dar_correo)

                # Verificar que Bruce no está pidiendo el correo apropiadamente
                bruce_pide_correo = any(word in respuesta_lower for word in [
                    'cuál es', 'cual es', 'dígame', 'digame', 'adelante', 'escucho',
                    'anoto', 'me dice', 'por favor', 'correo'
                ])

                if cliente_quiere_dar_correo and not bruce_pide_correo:
                    print(f"\n[EMAIL] FIX 231: FILTRO ACTIVADO - Cliente quiere dar correo")
                    print(f"   Cliente dijo: \"{ultimo_cliente[:60]}...\"")
                    print(f"   Bruce iba a decir: \"{respuesta[:60]}...\"")
                    respuesta = "Claro, dígame su correo electrónico por favor."
                    filtro_aplicado = True
                    print(f"   Respuesta corregida: \"{respuesta}\"")

        # ============================================================
        # FILTRO 6B (FIX 254/255): Cliente dice "no se encuentra" pero Bruce insiste
        # ============================================================
        if not filtro_aplicado:
            ultimos_mensajes_cliente = [
                msg['content'].lower() for msg in self.conversation_history[-4:]
                if msg['role'] == 'user'
            ]

            if ultimos_mensajes_cliente:
                ultimo_cliente = ultimos_mensajes_cliente[-1]

                # Detectar si cliente dice que encargado NO está disponible
                # FIX 372: Agregar "viene hasta el [día]" como NO disponible
                patrones_no_disponible = [
                    r'no\s+se\s+encuentra',
                    r'no\s+est[aá]',
                    r'no\s+est[aá]\s+(?:disponible|aqu[ií]|en\s+este\s+momento)',
                    r'no\s+(?:lo|la)\s+tengo',
                    r'ya\s+sali[oó]',
                    r'(?:est[aá]|se\s+fue)\s+(?:fuera|afuera)',
                    r'(?:sali[oó]|se\s+fue)',
                    r'llamar\s+(?:m[aá]s\s+)?tarde',  # FIX 255: "llamar más tarde"
                    r'llame\s+(?:m[aá]s\s+)?tarde',   # FIX 255: "llame más tarde"
                    r'marcar\s+(?:m[aá]s\s+)?tarde',   # FIX 642D: BRUCE2070 "marcar más tarde"
                    r'marque\s+(?:m[aá]s\s+)?tarde',   # FIX 642D: "marque más tarde"
                    # FIX 372: "viene hasta el viernes/lunes/martes/etc"
                    r'viene\s+hasta\s+(?:el\s+)?(?:lunes|martes|mi[eé]rcoles|jueves|viernes|s[aá]bado|domingo)',
                    r'llega\s+hasta\s+(?:el\s+)?(?:lunes|martes|mi[eé]rcoles|jueves|viernes|s[aá]bado|domingo)',
                    r'regresa\s+hasta\s+(?:el\s+)?(?:lunes|martes|mi[eé]rcoles|jueves|viernes|s[aá]bado|domingo)',
                    r'entra\s+hasta\s+(?:el\s+)?(?:lunes|martes|mi[eé]rcoles|jueves|viernes|s[aá]bado|domingo)',
                    r'viene\s+el\s+(?:lunes|martes|mi[eé]rcoles|jueves|viernes|s[aá]bado|domingo)',
                    r'llega\s+el\s+(?:lunes|martes|mi[eé]rcoles|jueves|viernes|s[aá]bado|domingo)',
                ]

                cliente_dice_no_disponible = any(re.search(p, ultimo_cliente) for p in patrones_no_disponible)

                # FIX 376: Detectar cuando cliente pregunta sobre productos DESPUÉS de decir "no está"
                # Ejemplo: "No. ¿Qué cree? Que no está. Pero. ¿Qué tipo de productos son los que maneja?"
                cliente_pregunta_productos = any(palabra in ultimo_cliente for palabra in [
                    'qué tipo de productos', 'que tipo de productos',
                    'qué productos', 'que productos',
                    'qué manejan', 'que manejan',
                    'qué venden', 'que venden',
                    'de qué se trata', 'de que se trata',
                    'qué es lo que', 'que es lo que'
                ])

                # FIX 255: Ampliar detección - Bruce pide transferencia O pregunta por mejor momento
                bruce_insiste_contacto = any(kw in respuesta_lower for kw in [
                    'me lo podría comunicar',
                    'me lo puede comunicar',
                    'me podría comunicar',
                    'me puede pasar',
                    'me lo pasa',
                    'me comunica con',
                    'transferir',
                    'comunicar con',
                    # FIX 255: Nuevos patrones
                    'mejor momento para llamar',
                    'cuándo puedo llamar',
                    'a qué hora',
                    'qué hora puedo',
                    'cuándo lo encuentro',
                    'cuándo está disponible',
                    # FIX 376: Pedir número directo del encargado
                    'número directo del encargado',
                    'numero directo del encargado',
                    'número del encargado',
                    'numero del encargado'
                ])

                # FIX 372: También detectar si Bruce dice "está ocupado" cuando NO está disponible
                bruce_dice_ocupado = any(frase in respuesta_lower for frase in [
                    'entiendo que está ocupado', 'entiendo que esta ocupado',
                    'veo que está ocupado', 'veo que esta ocupado',
                    'si está ocupado', 'si esta ocupado'
                ])

                # FIX 376: Si cliente dice "no está" PERO pregunta sobre productos
                # Bruce debe responder la pregunta primero
                if cliente_dice_no_disponible and cliente_pregunta_productos:
                    print(f"\n[EMOJI] FIX 376: FILTRO ACTIVADO - Cliente dice 'no está' pero pregunta sobre productos")
                    print(f"   Cliente dijo: \"{ultimo_cliente[:80]}...\"")
                    print(f"   Bruce iba a decir: \"{respuesta[:60]}...\"")
                    respuesta = "Claro, manejamos grifería, cintas, herramientas y más productos de ferretería. ¿Le gustaría que le envíe el catálogo por WhatsApp para que el encargado lo revise?"
                    filtro_aplicado = True
                    print(f"   Respuesta corregida: \"{respuesta}\"")
                elif cliente_dice_no_disponible and (bruce_insiste_contacto or bruce_dice_ocupado):
                    # FIX 629B: BRUCE2063 - No sobreescribir si cliente OFRECE contacto
                    # "No está disponible, pero te puedo pasar su número" → GPT dijo "si me puede pasar"
                    # FIX 254 veía "no disponible" + "me puede pasar" → override con "¿catálogo?"
                    # Pero GPT estaba ACEPTANDO la oferta del cliente (correcto!)
                    cliente_ofrece_dato_629 = any(p in ultimo_cliente for p in [
                        'te puedo pasar', 'le puedo pasar', 'te paso su', 'le paso su',
                        'te doy su', 'le doy su', 'quieres que te pase', 'quiere que le pase',
                        'te puedo dar', 'le puedo dar', 'te paso el', 'le paso el',
                        'te doy el', 'le doy el', 'puedo pasar su', 'puedo dar su',
                    ])
                    if cliente_ofrece_dato_629:
                        print(f"\n   FIX 629B: Cliente OFRECE contacto - NO aplicar FIX 254/255")
                        print(f"   Cliente dijo: \"{ultimo_cliente[:80]}...\"")
                        print(f"   GPT respondió correctamente: \"{respuesta[:60]}...\"")
                    else:
                        print(f"\n[EMOJI] FIX 254/255/372/376: FILTRO ACTIVADO - Cliente dijo NO DISPONIBLE pero Bruce insiste/malinterpreta")
                        print(f"   Cliente dijo: \"{ultimo_cliente[:80]}...\"")
                        print(f"   Bruce iba a decir: \"{respuesta[:60]}...\"")
                        respuesta = "Entiendo. ¿Le gustaría que le envíe nuestro catálogo por WhatsApp o correo electrónico?"
                        filtro_aplicado = True
                        print(f"   Respuesta corregida: \"{respuesta}\"")

        # ============================================================
        # FILTRO 13 (FIX 257): Cliente dice que ÉL ES el encargado
        # ============================================================
        if not filtro_aplicado:
            ultimos_mensajes = [
                msg for msg in self.conversation_history[-4:]
            ]

            if len(ultimos_mensajes) >= 2:
                # Último mensaje del cliente
                ultimo_cliente = next((msg['content'].lower() for msg in reversed(ultimos_mensajes) if msg['role'] == 'user'), '')
                # Último mensaje de Bruce
                ultimo_bruce = next((msg['content'].lower() for msg in reversed(ultimos_mensajes) if msg['role'] == 'assistant'), '')

                # Detectar si Bruce preguntó por el encargado
                bruce_pregunto_encargado = any(kw in ultimo_bruce for kw in [
                    'encargado de compras',
                    'encargado',
                    'jefe de compras',
                    'gerente de compras',
                    'responsable de compras'
                ])

                # Detectar si cliente dice que ÉL ES el encargado
                patrones_yo_soy_encargado = [
                    r'yo\s+soy\s+(?:el\s+)?(?:encargado|jefe|gerente|responsable)',
                    r'soy\s+yo(?:\s+el)?(?:\s+encargado)?',
                    r'le\s+habla\s+(?:el\s+)?(?:encargado|jefe)',
                    r'habla\s+con\s+(?:el\s+)?(?:encargado|jefe)',
                ]

                cliente_es_encargado = any(re.search(p, ultimo_cliente) for p in patrones_yo_soy_encargado)

                # FIX 262: Detectar "Dígame" como señal de disposición a escuchar
                # Si cliente dice "Dígame", "Mande", etc. después de que Bruce preguntó por encargado
                patrones_digame = [
                    r'^d[ií]game\b', r'^mande\b', r'^s[ií],?\s*d[ií]game',
                    r'^a\s+sus\s+[oó]rdenes', r'^para\s+servirle',
                    r'^en\s+qu[eé]\s+le\s+(?:ayudo|puedo\s+ayudar)',
                ]
                cliente_dice_digame = any(re.search(p, ultimo_cliente.strip()) for p in patrones_digame)

                # Si Bruce preguntó por encargado Y cliente dice que ÉL ES
                if bruce_pregunto_encargado and cliente_es_encargado:
                    # Verificar que la respuesta de Bruce NO esté preguntando de nuevo por el encargado
                    bruce_vuelve_preguntar = any(kw in respuesta_lower for kw in [
                        'me podría comunicar',
                        'me puede comunicar',
                        'encargado de compras'
                    ])

                    if bruce_vuelve_preguntar or 'entendido' in respuesta_lower:
                        print(f"\n[EMOJI] FIX 257: FILTRO ACTIVADO - Cliente ES el encargado")
                        print(f"   Bruce preguntó: \"{ultimo_bruce[:60]}...\"")
                        print(f"   Cliente dijo: \"{ultimo_cliente[:60]}...\"")
                        print(f"   Bruce iba a decir: \"{respuesta[:60]}...\"")
                        respuesta = "Perfecto, mucho gusto. ¿Le gustaría recibir nuestro catálogo por WhatsApp o correo electrónico?"
                        filtro_aplicado = True
                        print(f"   Respuesta corregida: \"{respuesta}\"")

                # FIX 262: Si Bruce preguntó por encargado Y cliente dice "Dígame/Mande"
                # Esto indica que están listos para escuchar (probablemente ES el encargado)
                elif bruce_pregunto_encargado and cliente_dice_digame:
                    bruce_vuelve_preguntar = any(kw in respuesta_lower for kw in [
                        'me podría comunicar',
                        'me puede comunicar',
                        'encargado de compras'
                    ])

                    if bruce_vuelve_preguntar:
                        print(f"\n[EMOJI] FIX 262: FILTRO ACTIVADO - Cliente dice 'Dígame' (está listo)")
                        print(f"   Bruce preguntó: \"{ultimo_bruce[:60]}...\"")
                        print(f"   Cliente dijo: \"{ultimo_cliente[:60]}...\"")
                        print(f"   Bruce iba a decir: \"{respuesta[:60]}...\"")
                        respuesta = "Sí, buen día. Soy Bruce de la marca NIOVAL, productos de ferretería. ¿Usted es el encargado de compras?"
                        filtro_aplicado = True
                        print(f"   Respuesta corregida: \"{respuesta}\"")

        # ============================================================
        # FILTRO 15 (FIX 263): Evitar volver a preguntar por encargado cuando ya avanzamos
        # FIX 447: Caso BRUCE1340 - NO activar si cliente solo ha dicho saludos
        # ============================================================
        if not filtro_aplicado:
            # FIX 447: Solo contar como "avanzada" si el CLIENTE mencionó WhatsApp/correo/catálogo
            # No contar menciones de Bruce (él siempre los ofrece en su presentación)
            ultimos_mensajes_cliente_completos = [
                msg['content'].lower() for msg in self.conversation_history[-8:]
                if msg['role'] == 'user'
            ]

            # FIX 447: Detectar si cliente SOLO ha dicho saludos (no ha dado información real)
            saludos_comunes = ['buen día', 'buen dia', 'buenos días', 'buenos dias',
                              'buenas tardes', 'buenas noches', 'buenas', 'hola',
                              'dígame', 'digame', 'mande', 'sí', 'si', 'bueno', 'aló', 'alo']
            cliente_solo_saludo = all(
                any(saludo in msg for saludo in saludos_comunes) and len(msg) < 30
                for msg in ultimos_mensajes_cliente_completos
            ) if ultimos_mensajes_cliente_completos else True

            # Detectar si ya se habló del catálogo/WhatsApp/correo POR EL CLIENTE (no Bruce)
            conversacion_avanzada = any(
                any(kw in msg for kw in ['whatsapp', 'catálogo', 'catalogo', 'correo', 'email'])
                for msg in ultimos_mensajes_cliente_completos
            )

            # Detectar si Bruce está volviendo a preguntar por el encargado
            bruce_pregunta_encargado = any(kw in respuesta_lower for kw in [
                'se encontrará el encargado',
                'se encontrara el encargado',
                '¿se encuentra el encargado',
                'se encuentra el encargado',
                'me podría comunicar con el encargado',
                'me puede comunicar con el encargado',
            ])

            # FIX 431: NO activar este filtro si el cliente hizo una pregunta directa
            # Caso BRUCE1311: Cliente preguntó "¿De qué marca?" y Bruce iba a responder
            # pero FIX 263 cambió la respuesta a "Perfecto. ¿Hay algo más...?" (incorrecto)
            ultimos_mensajes_cliente = [
                msg['content'].lower() for msg in self.conversation_history[-3:]
                if msg['role'] == 'user'
            ]
            cliente_hizo_pregunta = False
            if ultimos_mensajes_cliente:
                ultimo_cliente = ultimos_mensajes_cliente[-1]
                # Detectar preguntas directas del cliente
                patrones_pregunta = ['¿', '?', 'qué', 'que', 'cuál', 'cual', 'cómo', 'como',
                                   'dónde', 'donde', 'cuándo', 'cuando', 'por qué', 'porque']
                cliente_hizo_pregunta = any(p in ultimo_cliente for p in patrones_pregunta)

            # FIX 447: NO activar si cliente solo ha dicho saludos
            if cliente_solo_saludo:
                print(f"\n[EMOJI]  FIX 447: Cliente solo ha dicho saludos - NO aplicar FIX 263")

            if conversacion_avanzada and bruce_pregunta_encargado and not cliente_hizo_pregunta and not cliente_solo_saludo:
                print(f"\n[EMOJI] FIX 263: FILTRO ACTIVADO - Bruce pregunta por encargado cuando ya avanzamos")
                print(f"   Bruce iba a decir: \"{respuesta[:80]}...\"")
                # Ofrecer continuar o despedirse
                respuesta = "Perfecto. ¿Hay algo más en lo que le pueda ayudar?"
                filtro_aplicado = True
                print(f"   Respuesta corregida: \"{respuesta}\"")
            elif conversacion_avanzada and bruce_pregunta_encargado and cliente_hizo_pregunta:
                print(f"\n[EMOJI]  FIX 431: Cliente hizo pregunta directa → NO aplicar FIX 263")
                print(f"   Cliente preguntó: '{ultimos_mensajes_cliente[-1][:50]}...'")
                print(f"   Bruce debe responder la pregunta, no cambiar tema")

        # ============================================================
        # FILTRO 7 (FIX 228/236/240): Evitar repetir el saludo/presentación
        # FIX 240: Patrones más específicos para evitar falsos positivos
        # ============================================================
        if not filtro_aplicado:
            # Patrones que indican que Bruce está repitiendo el SALUDO INICIAL completo
            # FIX 240: Removido "encargado" porque preguntar por el encargado es válido
            patrones_saludo_repetido = [
                r'me\s+comunico\s+de\s+(la\s+)?marca\s+nioval',
                r'quería\s+brindar\s+informaci[oó]n\s+sobre',  # FIX 240: Más específico
                r'productos\s+de\s+ferreter[ií]a.*se\s+encontrar',  # FIX 240: Combo específico
            ]

            # Verificar si ya dijimos algo similar antes
            ultimos_mensajes_bruce = [
                msg['content'].lower() for msg in self.conversation_history[-6:]
                if msg['role'] == 'assistant'
            ]

            for patron in patrones_saludo_repetido:
                if re.search(patron, respuesta_lower):
                    # FIX 236: Buscar en TODOS los mensajes anteriores, no solo los últimos
                    ya_dicho = any(re.search(patron, msg) for msg in ultimos_mensajes_bruce)
                    if ya_dicho:
                        # FIX 466: BRUCE1405 - NO filtrar si cliente pregunta DE DÓNDE LLAMAN
                        # Cuando cliente pregunta "¿de dónde me habla?", la presentación ES la respuesta correcta
                        ultimo_cliente_para_466 = ""
                        for msg in reversed(self.conversation_history):
                            if msg['role'] == 'user':
                                ultimo_cliente_para_466 = msg['content'].lower()
                                break

                        cliente_pregunta_origen = any(frase in ultimo_cliente_para_466 for frase in [
                            'de dónde', 'de donde', 'quién habla', 'quien habla',
                            'quién llama', 'quien llama', 'quién es', 'quien es',
                            'de qué empresa', 'de que empresa', 'de qué compañía', 'de que compania',
                            'de parte de quién', 'de parte de quien', 'con quién hablo', 'con quien hablo'
                        ])

                        if cliente_pregunta_origen:
                            print(f"\n[OK] FIX 466: Cliente pregunta DE DÓNDE LLAMAN - presentación ES la respuesta correcta")
                            print(f"   Cliente dijo: '{ultimo_cliente_para_466[:60]}...'")
                            print(f"   NO se cambiará la respuesta de GPT")
                            break  # Salir del for sin aplicar filtro

                        print(f"\n[EMOJI] FIX 228/236/240: FILTRO ACTIVADO - Bruce intentó repetir saludo/presentación")
                        print(f"   Patrón detectado: '{patron}'")
                        print(f"   Respuesta original: \"{respuesta[:80]}...\"")

                        # FIX 281: Verificar contexto del último mensaje del cliente
                        # Si el cliente dio información útil (día, hora, nombre, etc.), no usar "¿Me escucha?"
                        ultimo_cliente_msg = ""
                        for msg in reversed(self.conversation_history):
                            if msg['role'] == 'user':
                                ultimo_cliente_msg = msg['content'].lower()
                                break

                        # FIX 334: Detectar si cliente SOLO está saludando u ofreciendo ayuda
                        # Estos NO deben activar despedida
                        # FIX 450: Caso BRUCE1343 - Agregar "bueno", "sí", "aló" como saludos
                        es_solo_saludo = any(frase in ultimo_cliente_msg for frase in [
                            "buen día", "buen dia", "buenos días", "buenos dias",
                            "buenas tardes", "buenas noches", "dígame", "digame",
                            "mande", "sí dígame", "si digame", "qué se le ofrece",
                            "que se le ofrece", "en qué le puedo", "en que le puedo",
                            "cómo le ayudo", "como le ayudo", "le puedo ayudar",
                            # FIX 450: Variantes de contestar teléfono
                            "bueno", "sí", "si", "aló", "alo", "hola"
                        ])

                        # Detectar si cliente dio información de tiempo/día (pero NO saludos)
                        menciona_tiempo = False
                        if not es_solo_saludo:
                            menciona_tiempo = any(palabra in ultimo_cliente_msg for palabra in [
                                "lunes", "martes", "miércoles", "miercoles", "jueves", "viernes",
                                "sábado", "sabado", "domingo", "mañana", "tarde", "noche",
                                "semana", "hora", "hoy", "ayer"
                            ])
                            # FIX 334: Excluir "día/dia" si es parte de un saludo
                            if not menciona_tiempo:
                                if ("día" in ultimo_cliente_msg or "dia" in ultimo_cliente_msg):
                                    # Solo contar como tiempo si NO es parte de "buen día" o similar
                                    if not any(saludo in ultimo_cliente_msg for saludo in ["buen día", "buen dia", "buenos día", "buenos dia"]):
                                        menciona_tiempo = True

                        # Detectar si cliente dio respuesta negativa (no está, salió, etc.)
                        # FIX 446: Ampliada lista de detección de "encargado no está"
                        respuesta_negativa = any(palabra in ultimo_cliente_msg for palabra in [
                            # Básicas
                            "no está", "no esta", "salió", "salio", "no se encuentra",
                            "no hay", "no viene", "estaba", "cerrado",
                            # Variantes de ausencia
                            "no lo tenemos", "no la tenemos", "se fue", "ya se fue",
                            "está fuera", "esta fuera", "está ocupado", "esta ocupado",
                            "no lo encuentro", "no la encuentro", "no lo veo", "no la veo",
                            # Variantes temporales
                            "no está ahorita", "no esta ahorita", "ahorita no está", "ahorita no esta",
                            "por el momento no", "en este momento no", "ahora no",
                            "todavía no llega", "todavia no llega", "aún no llega", "aun no llega",
                            "no ha llegado", "todavía no viene", "todavia no viene",
                            # Variantes de horario/día
                            "no viene hoy", "no trabaja hoy", "hoy no viene", "hoy no está",
                            "viene hasta", "llega hasta", "regresa hasta",
                            # Ofreciendo alternativas
                            "gusta dejar", "dejar mensaje", "dejar recado", "dejar un recado",
                            "quiere dejar", "le dejo el mensaje", "yo le paso el recado"
                        ])

                        # FIX 443: Caso BRUCE1334 - Detectar si cliente OFRECE dar datos
                        # Esto tiene prioridad sobre respuesta_negativa porque el cliente quiere colaborar
                        # FIX 448: Caso BRUCE1342 - Agregar más variantes de ofrecimiento
                        frases_ofrecimiento_datos = [
                            'le puedo dar', 'te puedo dar', 'le doy', 'te doy',
                            'anota', 'apunta', 'mi correo', 'el correo', 'mi email',
                            'le paso', 'te paso', 'mi whatsapp', 'mi número', 'mi numero',
                            'manda al correo', 'mandar al correo', 'enviar al correo',
                            'ahí me manda', 'ahí le mando', 'le envío', 'me envía',
                            'para que me mande', 'para que le mande',
                            # FIX 443b: Agregar más frases para WhatsApp (BRUCE1337)
                            'manda por whatsapp', 'mandar por whatsapp', 'enviar por whatsapp',
                            'por whatsapp', 'al whatsapp', 'a su whatsapp', 'a tu whatsapp',
                            'le mando por', 'te mando por', 'se lo mando',
                            # FIX 443c: Agregar más frases para correo
                            'manda por correo', 'mandar por correo', 'enviar por correo',
                            'por correo', 'a su correo', 'a tu correo', 'al mail',
                            'manda al mail', 'enviar al mail', 'por mail', 'mi mail',
                            'el mail es', 'el correo es', 'su correo es',
                            # FIX 448: Caso BRUCE1342 - Variantes adicionales
                            'le doy mi correo', 'le doy el correo', 'le doy un correo',
                            'le envío su correo', 'le envio su correo', 'le envío el correo',
                            'ahí le puedo enviar', 'ahi le puedo enviar',
                            'le puedo enviar', 'puedo enviar información', 'puedo enviar informacion',
                            'doy mi número', 'doy mi numero', 'doy el número', 'doy el numero',
                            'tome nota', 'toma nota', 'le doy el dato', 'le doy los datos'
                        ]
                        cliente_ofreciendo_datos = any(frase in ultimo_cliente_msg for frase in frases_ofrecimiento_datos)

                        if cliente_ofreciendo_datos:
                            # FIX 443: Cliente ofrece dar correo/whatsapp/teléfono - aceptar y pedir el dato
                            if 'correo' in ultimo_cliente_msg or 'email' in ultimo_cliente_msg:
                                respuesta = "Claro, con gusto le envío la información. ¿Cuál es su correo electrónico?"
                                print(f"   [EMOJI] FIX 443: Cliente OFRECE CORREO - aceptando oferta")
                            elif 'whatsapp' in ultimo_cliente_msg:
                                respuesta = "Perfecto, ¿me puede confirmar su número de WhatsApp?"
                                print(f"   [EMOJI] FIX 443: Cliente OFRECE WHATSAPP - aceptando oferta")
                            else:
                                respuesta = "Claro, con gusto. ¿Me puede proporcionar el dato?"
                                print(f"   [EMOJI] FIX 443: Cliente OFRECE DATO - aceptando oferta")
                            filtro_aplicado = True
                            print(f"   Respuesta corregida: \"{respuesta}\"")
                            break
                        elif es_solo_saludo:
                            # FIX 334: Cliente solo saluda u ofrece ayuda - continuar con presentación
                            # FIX 440: Caso BRUCE1326 - Verificar si Bruce YA preguntó por encargado
                            # Si ya preguntó, NO volver a preguntar (evitar repetición)
                            bruce_ya_pregunto_encargado = any(
                                'encontrar' in msg and 'encargado' in msg
                                for msg in ultimos_mensajes_bruce
                            )

                            if bruce_ya_pregunto_encargado:
                                # FIX 440/445: Caso BRUCE1326/1338 - Bruce ya preguntó
                                # FIX 445: NO usar "¿Me escucha?" - el cliente SÍ escucha, solo hay latencia de Deepgram
                                respuesta = "Sí, le llamo de la marca NIOVAL. ¿Se encuentra el encargado de compras?"
                                print(f"   FIX 440/445: Bruce ya preguntó por encargado - reformulando sin '¿Me escucha?'")
                            else:
                                respuesta = "Qué tal, le llamo de la marca NIOVAL para brindar información de nuestros productos ferreteros. ¿Se encontrará el encargado de compras?"
                                print(f"   FIX 334: Cliente solo saludó/ofreció ayuda - continuando presentación")
                        elif menciona_tiempo:
                            respuesta = "Perfecto, muchas gracias por la información. Le marco entonces. Que tenga excelente día."
                            print(f"   FIX 281: Cliente mencionó tiempo/día - usando despedida apropiada")
                        elif respuesta_negativa:
                            # FIX 817: Ofrecer WhatsApp/correo además de callback
                            respuesta = "Entiendo. ¿Me podría dejar un WhatsApp o correo para enviarle la información al encargado?"
                            print(f"   FIX 281+817: Cliente indicó ausencia - ofreciendo WhatsApp/correo")
                        else:
                            # FIX 445: NO usar "¿Me escucha?" genérico - el cliente SÍ escucha
                            respuesta = "Sí, dígame."

                        filtro_aplicado = True
                        print(f"   Respuesta corregida: \"{respuesta}\"")
                        break

        # ============================================================
        # FILTRO 16 (FIX 263B/285): Evitar repetir la misma pregunta exacta
        # ============================================================
        if not filtro_aplicado:
            # Patrones de preguntas que NO deben repetirse
            preguntas_unicas = [
                r'(?:le\s+)?gustar[ií]a\s+recibir\s+(?:nuestro\s+)?cat[aá]logo',
                r'por\s+whatsapp\s+o\s+correo',
                r'¿cu[aá]l\s+es\s+su\s+n[uú]mero',
                r'¿me\s+(?:puede|podr[ií]a)\s+dar\s+su\s+n[uú]mero',
            ]

            ultimos_mensajes_bruce = [
                msg['content'].lower() for msg in self.conversation_history[-6:]
                if msg['role'] == 'assistant'
            ]

            # FIX 285: Detectar si cliente está deletreando correo (aunque no diga "arroba" aún)
            # Cuando Bruce pidió correo y cliente responde con palabras sueltas, está deletreando
            ultimos_mensajes_cliente = [
                msg['content'].lower() for msg in self.conversation_history[-4:]
                if msg['role'] == 'user'
            ]
            bruce_pidio_correo = any(
                palabra in msg for msg in ultimos_mensajes_bruce
                for palabra in ['correo', 'email', 'deletrear', 'electrónico']
            )
            cliente_dando_info = len(ultimos_mensajes_cliente) > 0 and any(
                # Patrones de deletreo parcial de correo
                palabra in ultimos_mensajes_cliente[-1]
                for palabra in ['gmail', 'hotmail', 'yahoo', 'outlook', 'arroba', 'punto com', '@']
            )

            for patron in preguntas_unicas:
                if re.search(patron, respuesta_lower):
                    # Verificar si ya preguntamos esto antes
                    ya_preguntado = any(re.search(patron, msg) for msg in ultimos_mensajes_bruce)
                    if ya_preguntado:
                        print(f"\n[EMOJI] FIX 263B/280: FILTRO ACTIVADO - Bruce repitiendo pregunta")
                        print(f"   Patrón repetido: '{patron}'")
                        print(f"   Bruce iba a decir: \"{respuesta[:80]}...\"")
                        # FIX 280/285: Reformular mejor según contexto
                        # FIX 444: Caso BRUCE1337 - NO usar "Adelante con el dato" si cliente pregunta o quiere dejar mensaje
                        ultimo_cliente_lower = ultimos_mensajes_cliente[-1] if ultimos_mensajes_cliente else ""
                        cliente_hace_pregunta = '?' in ultimo_cliente_lower or '¿' in ultimo_cliente_lower
                        cliente_quiere_dejar_mensaje = any(frase in ultimo_cliente_lower for frase in [
                            'deje un mensaje', 'dejar mensaje', 'dejo un mensaje', 'dejo mensaje',
                            'deme el mensaje', 'dame el mensaje', 'le dejo el mensaje',
                            'quiere dejar', 'quieres dejar', 'le puede dejar',
                            'mande un mensaje', 'mandar mensaje', 'enviar mensaje',
                            'qué le digo', 'que le digo'
                        ])

                        if cliente_quiere_dejar_mensaje:
                            # FIX 444: Cliente quiere dejar mensaje - dar contacto
                            respuesta = "Claro, puede enviar la información al WhatsApp 6 6 2, 4 1 5, 1 9 9 7 o al correo ventas arroba nioval punto com."
                            print(f"   [EMOJI] FIX 444: Cliente quiere dejar MENSAJE - dando contacto")
                        elif cliente_hace_pregunta and not cliente_dando_info:
                            # FIX 464: BRUCE1390 - Detectar si cliente pregunta QUÉ VENDE
                            # Caso: "¿Qué mercancía vende?" → Bruce respondió "Sí, dígame" (INCORRECTO)
                            # GPT había generado: "Manejamos productos de ferretería..." (CORRECTO)
                            cliente_pregunta_que_vende = any(frase in ultimo_cliente_lower for frase in [
                                'qué vende', 'que vende', 'qué mercancía', 'que mercancia',
                                'qué productos', 'que productos', 'qué manejan', 'que manejan',
                                'qué es lo que vende', 'que es lo que vende',
                                'a qué se dedica', 'a que se dedica',
                                'de qué se trata', 'de que se trata',
                                'qué ofrece', 'que ofrece'
                            ])

                            # FIX 508: BRUCE1525 - Cliente pide repetir la marca
                            # Caso: "Repites tu marca, por favor?" → Bruce respondió "Sí, dígame" (INCORRECTO)
                            cliente_pide_repetir_marca = any(frase in ultimo_cliente_lower for frase in [
                                'repite tu marca', 'repites tu marca', 'me repites tu marca',
                                'repíteme la marca', 'repiteme la marca',
                                'cuál es tu marca', 'cual es tu marca',
                                'cuál marca es', 'cual marca es',
                                'cómo se llama la marca', 'como se llama la marca',
                                'qué marca es', 'que marca es', 'qué marca dices', 'que marca dices',
                                'dime la marca', 'me dices la marca',
                                'no escuché la marca', 'no escuche la marca',
                                'perdón la marca', 'perdon la marca',
                                'repíteme', 'repiteme', 'me repite', 'repite por favor'
                            ])

                            if cliente_pregunta_que_vende:
                                # FIX 464: NO cambiar la respuesta de GPT - dejar que explique los productos
                                print(f"   [OK] FIX 464: Cliente pregunta QUÉ VENDE - dejando respuesta de GPT")
                                # No cambiar respuesta, dejar que GPT explique los productos
                                filtro_aplicado = False  # Cancelar el filtro
                                break  # Salir del loop de patrones
                            elif cliente_pide_repetir_marca:
                                # FIX 508: Cliente pide que repita la marca - responder con NIOVAL
                                print(f"   [OK] FIX 508: Cliente pide repetir MARCA - respondiendo con NIOVAL")
                                respuesta = "Manejamos la marca NIOVAL, que es nuestra marca propia de productos de ferretería."
                                filtro_aplicado = True
                                print(f"   Respuesta corregida: \"{respuesta}\"")
                                break
                            else:
                                # FIX 444 original: Cliente está preguntando algo genérico
                                respuesta = "Sí, dígame."
                                print(f"   [EMOJI] FIX 444: Cliente hace PREGUNTA - no decir 'adelante con el dato'")
                        elif bruce_pidio_correo or cliente_dando_info:
                            # FIX 430: Verificar si REALMENTE tenemos contacto capturado
                            # Caso BRUCE1313: Bruce dijo "ya lo tengo registrado" pero cliente solo dijo nombre
                            tiene_whatsapp = bool(self.lead_data.get("whatsapp"))
                            tiene_email = bool(self.lead_data.get("email"))

                            if tiene_whatsapp or tiene_email:
                                # Cliente está en medio de dar el correo y SÍ lo capturamos
                                respuesta = "Perfecto, ya lo tengo registrado. Le llegará el catálogo en las próximas horas."
                            else:
                                # Cliente NO dio contacto completo, NO decir "ya lo tengo registrado"
                                print(f"   [WARN] FIX 430: NO tengo contacto capturado - NO decir 'ya lo tengo'")
                                respuesta = "Sí, lo escucho. Adelante con el dato."
                        elif 'whatsapp' in patron or 'catálogo' in patron or 'correo' in patron:
                            respuesta = "Sí, lo escucho. Adelante con el dato."
                        else:
                            respuesta = "Sí, dígame."
                        filtro_aplicado = True
                        print(f"   Respuesta corregida: \"{respuesta}\"")
                        break

        # ============================================================
        # FILTRO 8 (FIX 227): Detectar horarios y responder apropiadamente
        # ============================================================
        if not filtro_aplicado:
            # Ver si el último mensaje del cliente mencionó horarios
            ultimos_mensajes_cliente = [
                msg['content'].lower() for msg in self.conversation_history[-4:]
                if msg['role'] == 'user'
            ]

            if ultimos_mensajes_cliente:
                ultimo_cliente = ultimos_mensajes_cliente[-1]

                # Patrones de horario/disponibilidad (FIX 230/320/346: agregados más patrones)
                patrones_horario = [
                    r'después\s+de\s+mediodía',
                    r'en\s+la\s+tarde',
                    r'más\s+tarde',
                    r'sería\s+más\s+tarde',  # FIX 230
                    r'seria\s+mas\s+tarde',  # FIX 230 (sin acentos)
                    r'después\s+de\s+las?\s+\d',
                    r'a\s+las?\s+\d',
                    r'lo\s+puedes?\s+encontrar',
                    r'lo\s+encuentras?',
                    r'está\s+después',
                    r'viene\s+después',
                    r'llega\s+a\s+las',
                    r'regresa\s+a\s+las',
                    r'no\s+está.*pero',
                    r'no\s+se\s+encuentra.*tarde',  # FIX 230
                    r'no\s+se\s+encuentra.*después',  # FIX 230
                    r'llame\s+(más\s+)?tarde',  # FIX 230
                    r'marque\s+(más\s+)?tarde',  # FIX 230
                    # FIX 320: "en una hora más", "en un rato", "como en una hora"
                    r'en\s+una?\s+hora',  # "en una hora", "en 1 hora"
                    r'una\s+hora\s+m[aá]s',  # "una hora más"
                    r'como\s+en\s+una?\s+hora',  # "como en una hora"
                    r'en\s+un\s+rato',  # "en un rato"
                    r'en\s+unos?\s+\d+\s*(?:minutos?|mins?)',  # "en 30 minutos"
                    r'por\s+el\s+momento\s+no',  # "por el momento no" (implica que llegará)
                    # FIX 487: BRUCE1468 - "dentro de una hora", "regresa en una hora"
                    r'dentro\s+de.*hora',  # "dentro de una hora", "dentro de 1 hora"
                    r'regresa.*hora',  # "regresa en una hora", "regresa como en una hora"
                    r'vuelve.*hora',  # "vuelve en una hora"
                    r'llega.*hora',  # "llega en una hora"
                    r'viene.*hora',  # "viene en una hora"
                    r'se\s+vend[ií]a.*hora',  # "se vendría en una hora" (caso BRUCE1468)
                    r'estar[aá].*hora',  # "estará en una hora"
                    r'regresa.*\d+\s*hora',  # "regresa en 1 hora", "regresa 1 hora"
                    # FIX 346: "de 9 a 2", "de 8 a 3", "horario de X a Y"
                    r'de\s+\d+\s+a\s+\d+',  # "de 9 a 2", "de 8 a 5"
                    r'horario\s+de',  # "horario de..."
                    r'en\s+el\s+horario',  # "en el horario de..."
                    r'se\s+encuentra\s+en\s+el\s+horario',  # "se encuentra en el horario"
                ]

                cliente_dio_horario = any(re.search(p, ultimo_cliente) for p in patrones_horario)

                # Si cliente dio horario pero Bruce no responde sobre eso
                # FIX 320: Cuando cliente indica horario de llegada, pedir número directo
                if cliente_dio_horario:
                    # FIX 346: Si respuesta está vacía, también hay que corregir
                    respuesta_vacia = len(respuesta.strip()) == 0

                    # Verificar si la respuesta de Bruce menciona el horario o reprogramación
                    menciona_horario = any(word in respuesta_lower for word in [
                        'mediodía', 'tarde', 'hora', 'llamar', 'comunic', 'anotado', 'perfecto',
                        'número', 'numero', 'directo'
                    ])

                    if not menciona_horario or respuesta_vacia:
                        print(f"\n[EMOJI] FIX 227/320: FILTRO ACTIVADO - Cliente dio horario pero Bruce no respondió")
                        print(f"   Cliente dijo: \"{ultimo_cliente[:60]}...\"")
                        print(f"   Bruce iba a decir: \"{respuesta[:60]}...\"")
                        # FIX 320: Pedir número directo del encargado
                        respuesta = "Perfecto. ¿Me podría proporcionar el número directo del encargado para contactarlo en ese horario?"
                        filtro_aplicado = True
                        print(f"   Respuesta corregida: \"{respuesta}\"")

        # ============================================================
        # FILTRO 9 (FIX 241): Cliente menciona sucursal o ofrece teléfono de referencia
        # ============================================================
        if not filtro_aplicado:
            ultimos_mensajes_cliente = [
                msg['content'].lower() for msg in self.conversation_history[-3:]
                if msg['role'] == 'user'
            ]

            if ultimos_mensajes_cliente:
                ultimo_cliente = ultimos_mensajes_cliente[-1]

                # Patrones que indican que el cliente menciona sucursal o va a pasar teléfono
                patrones_referencia_telefono = [
                    r'(?:sucursal|otra\s+tienda|otra\s+sede)',  # Es sucursal
                    r'(?:te\s+paso|le\s+paso|ah[ií]\s+te\s+paso)\s+(?:un\s+)?tel[eé]fono',  # Te paso un teléfono
                    r'(?:llam[ae]|marca|habla)\s+a\s+(?:este|otro|al)\s+n[uú]mero',  # Llama a este número
                    r'(?:te\s+doy|le\s+doy)\s+(?:un|el|otro)\s+tel[eé]fono',  # Te doy un teléfono
                    r'(?:anota|apunta)\s+(?:el|este)\s+(?:n[uú]mero|tel[eé]fono)',  # Anota este número
                ]

                cliente_ofrece_telefono = any(re.search(p, ultimo_cliente) for p in patrones_referencia_telefono)

                # Verificar que Bruce NO está pidiendo el número apropiadamente
                bruce_pide_numero = any(word in respuesta_lower for word in [
                    'cuál es', 'cual es', 'dígame', 'digame', 'adelante', 'anoto',
                    'me dice', 'número', 'numero', 'teléfono', 'telefono', 'listo'
                ])

                if cliente_ofrece_telefono and not bruce_pide_numero:
                    print(f"\n[EMOJI] FIX 241: FILTRO ACTIVADO - Cliente ofrece teléfono/sucursal")
                    print(f"   Cliente dijo: \"{ultimo_cliente[:80]}...\"")
                    print(f"   Bruce iba a decir: \"{respuesta[:60]}...\"")
                    respuesta = "Perfecto, dígame el número y lo anoto para llamar."
                    filtro_aplicado = True
                    print(f"   Respuesta corregida: \"{respuesta}\"")

        # ============================================================
        # FILTRO 10 (FIX 242): Cliente pregunta "¿de qué estado eres/son?"
        # ============================================================
        if not filtro_aplicado:
            ultimos_mensajes_cliente = [
                msg['content'].lower() for msg in self.conversation_history[-3:]
                if msg['role'] == 'user'
            ]

            if ultimos_mensajes_cliente:
                ultimo_cliente = ultimos_mensajes_cliente[-1]

                # Patrones que indican que el cliente pregunta por la ubicación/estado
                patrones_ubicacion = [
                    r'(?:qu[eé]\s+)?estado',  # "de qué estado" o "estado"
                    r'd[oó]nde\s+(?:est[aá][ns]?|son|eres)',  # "de dónde son/están/eres"
                    r'(?:de\s+)?d[oó]nde\s+(?:me\s+)?(?:llam|habl)',  # "de dónde me llaman"
                    r'ubicaci[oó]n',  # "ubicación"
                    r'(?:de\s+)?qu[eé]\s+(?:parte|ciudad|lugar)',  # "de qué parte/ciudad"
                    # FIX 302: Agregar "en qué ciudad están"
                    r'(?:en\s+)?qu[eé]\s+ciudad',  # "en qué ciudad", "qué ciudad"
                ]

                cliente_pregunta_ubicacion = any(re.search(p, ultimo_cliente) for p in patrones_ubicacion)

                # Verificar que Bruce NO está respondiendo sobre ubicación
                bruce_responde_ubicacion = any(word in respuesta_lower for word in [
                    'guadalajara', 'jalisco', 'ubicado', 'ubicados', 'estamos en', 'somos de'
                ])

                if cliente_pregunta_ubicacion and not bruce_responde_ubicacion:
                    print(f"\n[EMOJI] FIX 242: FILTRO ACTIVADO - Cliente pregunta ubicación")
                    print(f"   Cliente dijo: \"{ultimo_cliente[:80]}...\"")
                    print(f"   Bruce iba a decir: \"{respuesta[:60]}...\"")

                    # FIX 303: Verificar si ya se ofreció catálogo (indica que encargado ya confirmado)
                    historial_bruce = ' '.join([
                        msg['content'].lower() for msg in self.conversation_history
                        if msg['role'] == 'assistant'
                    ])
                    ya_ofrecio_catalogo = any(frase in historial_bruce for frase in [
                        'catálogo por whatsapp', 'catalogo por whatsapp',
                        'cuál es su número', 'cual es su numero',
                        'enviarle el catálogo', 'enviarle el catalogo'
                    ])

                    if ya_ofrecio_catalogo:
                        # Ya está en proceso de captura de contacto, no preguntar por encargado
                        respuesta = "Estamos ubicados en Guadalajara, Jalisco, pero hacemos envíos a toda la República Mexicana."
                        print(f"   FIX 303: Ya ofreció catálogo, respuesta sin preguntar por encargado")
                    else:
                        respuesta = "Estamos ubicados en Guadalajara, Jalisco, pero hacemos envíos a toda la República. ¿Se encuentra el encargado de compras?"

                    filtro_aplicado = True
                    print(f"   Respuesta corregida: \"{respuesta}\"")

        # ============================================================
        # FILTRO 11 (FIX 243/308): Cliente pregunta "¿Con quién hablo?" / "¿De parte de quién?"
        # FIX 308: NO preguntar nombre del cliente, solo presentarse
        # ============================================================
        if not filtro_aplicado:
            ultimos_mensajes_cliente = [
                msg['content'].lower() for msg in self.conversation_history[-3:]
                if msg['role'] == 'user'
            ]

            if ultimos_mensajes_cliente:
                ultimo_cliente = ultimos_mensajes_cliente[-1]

                # Patrones que indican que el cliente pregunta quién habla / de parte de quién
                # FIX 410: Arreglar patrón que detecta "quiere" como "quién"
                patrones_quien_habla = [
                    r'\bqui[eé]n\s+(?:tengo\s+el\s+gusto|hablo|me\s+habla|est[aá]s?|eres)',  # "quién hablo", "quién eres" (word boundary)
                    r'\bcon\s+qui[eé]n\s+(?:hablo|tengo)',  # "con quién hablo"
                    r'(?:cu[aá]l\s+es\s+)?(?:tu|su)\s+nombre',  # "cuál es tu nombre", "tu nombre"
                    r'c[oó]mo\s+(?:te\s+llamas?|se\s+llama)',  # "cómo te llamas", "cómo se llama"
                    r'\ba\s+qui[eé]n\s+(?:hablo|tengo)',  # "a quién hablo"
                    # FIX 308: Agregar "¿de parte de quién?"
                    r'(?:de\s+)?parte\s+de\s+qui[eé]n',  # "de parte de quién", "parte de quién"
                    r'de\s+qu[eé]\s+(?:empresa|marca|compa[ñn][ií]a)',  # "de qué empresa"
                    r'qu[eé]\s+(?:empresa|marca)\s+(?:es|son)',  # "qué empresa es"
                ]

                cliente_pregunta_quien = any(re.search(p, ultimo_cliente) for p in patrones_quien_habla)

                # Verificar que Bruce NO se está presentando correctamente
                bruce_se_presenta = any(word in respuesta_lower for word in [
                    'soy bruce', 'me llamo bruce', 'mi nombre es bruce', 'habla bruce',
                    'bruce de nioval', 'nioval', 'productos de ferretería', 'productos ferreteros'
                ])

                # FIX 308: Detectar si Bruce pregunta el nombre cuando NO debería
                bruce_pregunta_nombre = any(frase in respuesta_lower for frase in [
                    'con quién tengo el gusto', 'con quien tengo el gusto',
                    'cómo se llama', 'como se llama', 'su nombre'
                ])

                if cliente_pregunta_quien and (not bruce_se_presenta or bruce_pregunta_nombre):
                    print(f"\n[EMOJI] FIX 243/308: FILTRO ACTIVADO - Cliente pregunta quién habla")
                    print(f"   Cliente dijo: \"{ultimo_cliente[:80]}...\"")
                    print(f"   Bruce iba a decir: \"{respuesta[:60]}...\"")
                    # FIX 308: Solo presentarse, NO preguntar nombre del cliente
                    respuesta = "Me comunico de parte de la marca NIOVAL, nosotros distribuimos productos de ferretería. ¿Se encontrará el encargado de compras?"
                    filtro_aplicado = True
                    print(f"   Respuesta corregida: \"{respuesta}\"")

        # ============================================================
        # FILTRO 12 (FIX 245/246): Validar número telefónico incompleto
        # ============================================================
        if not filtro_aplicado:
            # FIX 246: Revisar más mensajes atrás (últimos 6 en lugar de 4)
            # para detectar si Bruce pidió número aunque haya habido interrupciones
            ultimos_mensajes = [
                msg for msg in self.conversation_history[-6:]
                if msg['role'] in ['user', 'assistant']
            ]

            if len(ultimos_mensajes) >= 2:
                # Revisar si Bruce pidió un número de teléfono/WhatsApp/referencia
                # FIX 246: Revisar TODOS los mensajes de Bruce, no solo el último
                mensajes_bruce = [msg['content'].lower() for msg in ultimos_mensajes if msg['role'] == 'assistant']
                ultimo_cliente = ""

                for msg in reversed(ultimos_mensajes):
                    if msg['role'] == 'user' and not ultimo_cliente:
                        ultimo_cliente = msg['content'].lower()
                        break

                # Detectar si Bruce pidió número EN CUALQUIERA de sus últimos mensajes
                # FIX 476: BRUCE1438 - Ser más estricto: solo si Bruce pidió EXPLÍCITAMENTE WhatsApp/teléfono
                # Problema: Bruce decía "solo escuché 4 dígitos" cuando cliente no estaba dando contacto
                bruce_pidio_numero_contacto = any(
                    any(kw in msg_bruce for kw in [
                        'whatsapp', 'celular', 'teléfono para contactar', 'telefono para contactar',
                        'número de whatsapp', 'numero de whatsapp', 'número de celular', 'numero de celular',
                        'su whatsapp', 'tu whatsapp', 'me da su whatsapp', 'me da tu whatsapp',
                        'proporcionar el número', 'proporcionar su número', 'proporcionar tu número',
                        'dar el número', 'dar su número', 'dar tu número',
                        'enviarle el catálogo', 'enviarle nuestro', 'enviar el catálogo'
                    ])
                    for msg_bruce in mensajes_bruce
                )

                # FIX 476: También verificar que cliente está DANDO número (no solo mencionando dígitos)
                # FIX 483: BRUCE1458 - Agregar patrones para "Es 6 6 9 2" (es + dígitos)
                cliente_dando_numero = any(patron in ultimo_cliente for patron in [
                    'es el', 'es mi', 'mi número', 'mi numero', 'mi cel', 'mi whatsapp',
                    'el número es', 'el numero es', 'anota', 'anote', 'apunte', 'apunta',
                    'te paso', 'le paso', 'te doy', 'le doy', 'ahí va', 'ahi va',
                    'mira es', 'tome nota', 'seria el'
                ])

                # FIX 483: BRUCE1458 - Detectar cuando cliente dice "es" seguido de dígitos
                # Ejemplo: "Es 6 6 9 2" → cliente dictando número
                if not cliente_dando_numero and ultimo_cliente.strip().startswith('es '):
                    # Verificar que después de "es " hay dígitos
                    resto = ultimo_cliente.strip()[3:]  # Después de "es "
                    if re.search(r'\d', resto):
                        cliente_dando_numero = True
                        print(f"[EMOJI] FIX 483: Detectado 'es' + dígitos: '{ultimo_cliente[:40]}'")

                # FIX 483: También detectar si el mensaje es PRINCIPALMENTE dígitos y Bruce pidió número
                if not cliente_dando_numero and bruce_pidio_numero_contacto:
                    digitos_en_mensaje = len(re.findall(r'\d', ultimo_cliente))
                    palabras_en_mensaje = len(ultimo_cliente.split())
                    # Si más del 50% del mensaje son dígitos (o grupos de dígitos)
                    if digitos_en_mensaje >= 3 and palabras_en_mensaje <= 5:
                        cliente_dando_numero = True
                        print(f"[EMOJI] FIX 483: Mensaje con dígitos después de pedir número: '{ultimo_cliente[:40]}'")

                # FIX 476B: BRUCE1438 - Excluir cuando cliente menciona HORAS o DÍAS (no es teléfono)
                # Cliente dijo "Hasta el lunes a las 10 y media, 11" = callback, NO número de teléfono
                cliente_menciona_hora_o_dia = any(patron in ultimo_cliente for patron in [
                    # Horas
                    'a las', 'las diez', 'las once', 'las doce', 'las nueve', 'las ocho',
                    'y media', 'y cuarto', 'en punto', 'de la mañana', 'de la tarde',
                    # Días
                    'el lunes', 'el martes', 'el miércoles', 'el miercoles', 'el jueves', 'el viernes',
                    'hasta el', 'hasta mañana', 'hasta manana', 'la próxima', 'la proxima',
                    # Otros indicadores de tiempo
                    'más tarde', 'mas tarde', 'al rato', 'en un rato', 'después de', 'despues de'
                ])

                # Si menciona hora o día, NO tratar como número de teléfono
                if cliente_menciona_hora_o_dia:
                    cliente_dando_numero = False
                    print(f"\n[EMOJI] FIX 476B: Cliente menciona HORA/DÍA, NO número de teléfono")
                    print(f"   Mensaje: '{ultimo_cliente[:80]}'")

                # Condición más estricta: Bruce pidió contacto Y cliente está dando número Y NO menciona hora/día
                bruce_pidio_numero = bruce_pidio_numero_contacto and cliente_dando_numero and not cliente_menciona_hora_o_dia

                if bruce_pidio_numero and ultimo_cliente:
                    # FIX 276: Primero convertir números escritos a dígitos
                    # Ej: "catorce" -> "14", "sesenta y uno" -> "61"
                    ultimo_cliente_convertido = convertir_numeros_escritos_a_digitos(ultimo_cliente)

                    # Extraer dígitos del mensaje del cliente (después de conversión)
                    digitos = re.findall(r'\d', ultimo_cliente_convertido)
                    num_digitos = len(digitos)

                    print(f"\n[EMOJI] FIX 245 DEBUG: Cliente dio número con {num_digitos} dígitos")
                    print(f"   Dígitos extraídos: {''.join(digitos)}")
                    print(f"   Mensaje completo: \"{ultimo_cliente[:80]}...\"")

                    # FIX 623B: Reconstruir número con dígitos preservados del turno anterior
                    digitos_previos_623b = getattr(self, 'digitos_preservados_previos', '')
                    if digitos_previos_623b and num_digitos >= 7:
                        numero_actual_623b = ''.join(digitos)
                        if numero_actual_623b.startswith(digitos_previos_623b):
                            print(f"   FIX 623B (post-filter): Número actual YA incluye previos → usar actual")
                        else:
                            digitos_necesarios_623b = 10 - len(digitos_previos_623b)
                            if 0 < digitos_necesarios_623b < num_digitos:
                                candidato_623b = digitos_previos_623b + numero_actual_623b[:digitos_necesarios_623b]
                                print(f"   FIX 623B (post-filter): Reconstruido: {digitos_previos_623b}+{numero_actual_623b[:digitos_necesarios_623b]}={candidato_623b}")
                                digitos = list(candidato_623b)
                                num_digitos = len(digitos)
                        self.digitos_preservados_previos = ''

                    # Números telefónicos en México tienen 10 dígitos
                    # Números con lada internacional (52) tienen 12 dígitos
                    numero_completo = num_digitos == 10 or num_digitos == 12

                    # Verificar que Bruce NO está pidiendo repetición/verificación del número
                    bruce_pide_repeticion = any(word in respuesta_lower for word in [
                        'repetir', 'repita', 'de nuevo', 'otra vez', 'completo',
                        'no escuché bien', 'no escuche bien', 'puede repetir'
                    ])

                    bruce_verifica_numero = any(word in respuesta_lower for word in [
                        'correcto', '¿correcto?', 'es el', 'confirmo', 'confirmar',
                        'anotado como', 'entendido', 'anoto como'
                    ])

                    # FIX 434: NO interrumpir si cliente está DICTANDO el número
                    # Caso BRUCE1308: Cliente dice "Es el 3 40." → Bruce interrumpe "solo escuché 3 dígitos"
                    # Cliente continúa "342, 109, 76," → Bruce interrumpe OTRA VEZ "solo escuché 8 dígitos"
                    # Resultado: Cliente confundido, 27 dígitos acumulados
                    cliente_esta_dictando = False

                    # Detectar patrones de dictado:
                    # 1. Números en grupos pequeños separados por espacios/pausas: "3 40", "342 109 76"
                    # 2. Números separados por comas: "3, 4, 2", "342, 109"
                    # 3. Mensaje corto con pocos dígitos (indica que viene más)
                    # 4. Palabras como "es el", "son", "empieza" (inicio de dictado)

                    patrones_dictado = [
                        r'\d+\s+\d+',  # Números separados por espacios: "3 40", "342 109"
                        r'\d+,\s*\d+',  # Números separados por comas: "3, 4, 2"
                        r'\d+\.\s*\d+',  # Números separados por puntos: "3. 40"
                    ]

                    palabras_inicio_dictado = [
                        'es el', 'son el', 'empieza', 'inicia', 'comienza',
                        'son los', 'es los', 'primero'
                    ]

                    # Verificar patrones de dictado en el mensaje
                    tiene_patron_dictado = any(re.search(patron, ultimo_cliente) for patron in patrones_dictado)
                    tiene_palabra_inicio = any(palabra in ultimo_cliente for palabra in palabras_inicio_dictado)

                    # Si tiene pocos dígitos (3-8) Y (tiene patrón de dictado O palabra de inicio) = está dictando
                    # FIX 468: BRUCE1406 - También detectar si termina en coma (cliente sigue dictando)
                    termina_en_coma = ultimo_cliente.strip().endswith(',')

                    if 3 <= num_digitos <= 8 and (tiene_patron_dictado or tiene_palabra_inicio or termina_en_coma):
                        cliente_esta_dictando = True
                        print(f"\n[PAUSE]  FIX 434/468: Cliente está DICTANDO número ({num_digitos} dígitos)")
                        print(f"   Patrón detectado: {ultimo_cliente[:80]}")
                        print(f"   Termina en coma: {termina_en_coma}")
                        print(f"   → NO interrumpir - esperar a que termine de dictar")

                        # FIX 468: BRUCE1406 - Establecer estado y NO generar respuesta
                        # Esto evita que otros filtros sobrescriban con preguntas
                        self.estado_conversacion = EstadoConversacion.DICTANDO_NUMERO
                        # Respuesta corta de confirmación para que cliente sepa que escuchamos
                        respuesta = "Ajá..."
                        filtro_aplicado = True
                        print(f"   [OK] FIX 468: Estado → DICTANDO_NUMERO, respuesta mínima para no interrumpir")

                    # FIX 245: Validar número incompleto (SOLO si NO está dictando)
                    if not numero_completo and num_digitos > 0 and not bruce_pide_repeticion and not cliente_esta_dictando:
                        print(f"\n[EMOJI] FIX 245/246: FILTRO ACTIVADO - Número incompleto ({num_digitos} dígitos)")
                        print(f"   Bruce iba a decir: \"{respuesta[:60]}...\"")

                        if num_digitos < 10:
                            respuesta = f"Disculpe, solo escuché {num_digitos} dígitos. ¿Me puede repetir el número completo? Son 10 dígitos."
                        else:  # num_digitos entre 11 y 11 (no es 10 ni 12)
                            respuesta = "Disculpe, me puede repetir el número completo? Creo que faltó un dígito."

                        filtro_aplicado = True
                        print(f"   Respuesta corregida: \"{respuesta}\"")

                    # FIX 247: Verificar número completo (repetirlo para confirmar)
                    elif numero_completo and num_digitos > 0 and not bruce_verifica_numero and not bruce_pide_repeticion:
                        print(f"\n[OK] FIX 247: FILTRO ACTIVADO - Verificar número completo ({num_digitos} dígitos)")
                        print(f"   Bruce iba a decir: \"{respuesta[:60]}...\"")

                        # Formatear número con guiones para legibilidad
                        numero_str = ''.join(digitos)
                        if num_digitos == 10:
                            # Formato: 3-3-2-2 (ej: 333-123-45-67)
                            numero_formateado = f"{numero_str[0:3]}-{numero_str[3:6]}-{numero_str[6:8]}-{numero_str[8:10]}"
                        elif num_digitos == 12:
                            # Formato internacional: 52-3-3-2-2
                            numero_formateado = f"{numero_str[0:2]}-{numero_str[2:5]}-{numero_str[5:8]}-{numero_str[8:10]}-{numero_str[10:12]}"
                        else:
                            numero_formateado = '-'.join([numero_str[i:i+2] for i in range(0, len(numero_str), 2)])

                        # FIX 618: NO repetir número en voz (FIX 615B + user request)
                        respuesta = "Perfecto, ya lo tengo anotado. Le envío el catálogo en las próximas horas. Muchas gracias."
                        filtro_aplicado = True
                        print(f"   Respuesta corregida: \"{respuesta}\"")

        # ============================================================
        # FILTRO 14 (FIX 258/259/266): Cliente dice "ahí le paso el número" o "lo puede enviar, le digo a dónde"
        # ============================================================
        if not filtro_aplicado:
            ultimos_mensajes_cliente = [
                msg['content'].lower() for msg in self.conversation_history[-3:]
                if msg['role'] == 'user'
            ]

            if ultimos_mensajes_cliente:
                ultimo_cliente = ultimos_mensajes_cliente[-1]

                # Detectar si cliente ofreció dar el número o dirección de envío
                patrones_ofrecimiento_numero = [
                    r'(?:ahí|ah[ií])\s+(?:le|te)\s+(?:paso|doy|mando)\s+(?:el|mi)\s+n[uú]mero',
                    r'(?:le|te)\s+(?:paso|doy|mando)\s+(?:el|mi)\s+(?:n[uú]mero|whatsapp)',
                    r'(?:dime|d[ií]game)\s+(?:d[oó]nde|a\s+d[oó]nde)\s+(?:te\s+lo|se\s+lo)\s+(?:paso|mando|env[ií]o)',
                    r'(?:apunta|anota)\s+(?:el|mi)\s+n[uú]mero',
                    # FIX 266: "Lo puede enviar, le digo a dónde" = cliente dará dirección/número
                    r'(?:lo|la)\s+puede\s+enviar.*(?:le\s+)?digo\s+(?:a\s+)?d[oó]nde',
                    r'(?:env[ií]e|mande).*(?:le\s+)?digo\s+(?:a\s+)?d[oó]nde',
                    r'(?:ah[ií]|ahi)\s+le\s+digo',  # "ahí le digo" (el número/correo)
                    r'(?:se\s+lo|te\s+lo)\s+(?:paso|doy|mando)',  # "se lo paso" (el número)
                    r'le\s+digo\s+(?:a\s+)?d[oó]nde',  # "le digo a dónde" (enviar)
                    r'(?:d[ií]game|dime)\s+(?:d[oó]nde|a\s+d[oó]nde)\s+(?:lo\s+)?(?:mando|env[ií]o)',
                ]

                cliente_ofrecio_numero = any(re.search(p, ultimo_cliente) for p in patrones_ofrecimiento_numero)

                # Verificar si Bruce NO está pidiendo el número en su respuesta
                bruce_pide_numero = any(kw in respuesta_lower for kw in [
                    'dígame', 'digame', 'dime', 'cuál es', 'cual es',
                    'número', 'numero', 'whatsapp', 'escuchando'
                ])

                if cliente_ofrecio_numero and not bruce_pide_numero:
                    print(f"\n[PHONE] FIX 258/259/266: FILTRO ACTIVADO - Cliente ofreció número/dirección pero Bruce NO lo pidió")
                    print(f"   Cliente dijo: \"{ultimo_cliente[:80]}...\"")
                    print(f"   Bruce iba a decir: \"{respuesta[:60]}...\"")
                    respuesta = "Perfecto, dígame su número por favor."
                    filtro_aplicado = True
                    print(f"   Respuesta corregida: \"{respuesta}\"")

        # ============================================================
        # FIX 462: BRUCE1396 - Capturar número cuando cliente CONFIRMA
        # Escenario: Bruce dijo "lo tengo anotado como 221-442-61-55, ¿es correcto?"
        #            Cliente dijo "Es correcto"
        #            Pero el número NO se guardó → FIX 295/300 pidió el número de nuevo
        # Solución: Detectar confirmación y extraer número del historial de Bruce
        # ============================================================
        if not filtro_aplicado and not self.lead_data.get("whatsapp"):
            # Obtener último mensaje del cliente
            ultimos_msg_cliente_fix462 = [
                msg['content'].lower() for msg in self.conversation_history[-3:]
                if msg['role'] == 'user'
            ]
            ultimo_cliente = ultimos_msg_cliente_fix462[-1] if ultimos_msg_cliente_fix462 else ""

            # Detectar si cliente está CONFIRMANDO un número
            cliente_confirma_numero = any(frase in ultimo_cliente for frase in [
                'es correcto', 'correcto', 'sí es', 'si es', 'así es', 'eso es',
                'exacto', 'ese es', 'ese mero', 'ándale', 'andale', 'ajá', 'aja',
                'afirmativo', 'está bien', 'esta bien', 'ok', 'okey'
            ])

            if cliente_confirma_numero:
                # Buscar en el historial el último mensaje de Bruce con un número
                for msg in reversed(self.conversation_history[-6:]):
                    if msg['role'] == 'assistant':
                        # Buscar patrones de confirmación de número
                        # "lo tengo anotado como 221-442-61-55" o "221 442 61 55"
                        patron_numero_en_mensaje = re.search(
                            r'(?:anotado como|tengo como|registrado como|es el|número es)?\s*(\d[\d\s\-\.]+\d)',
                            msg['content'], re.IGNORECASE
                        )
                        if patron_numero_en_mensaje:
                            numero_en_historial = patron_numero_en_mensaje.group(1)
                            # Limpiar: solo dígitos
                            digitos = re.sub(r'[^\d]', '', numero_en_historial)

                            if len(digitos) >= 9 and len(digitos) <= 12:
                                # Normalizar a 10 dígitos (quitar 52 si lo tiene)
                                if len(digitos) == 12 and digitos.startswith('52'):
                                    digitos = digitos[2:]

                                numero_whatsapp = f"+52{digitos}" if len(digitos) == 10 else f"+52{digitos}"
                                self.lead_data["whatsapp"] = numero_whatsapp
                                self.lead_data["whatsapp_valido"] = True

                                print(f"\n[OK] FIX 462: Cliente CONFIRMÓ número del historial")
                                print(f"   Bruce dijo: '{msg['content'][:60]}...'")
                                print(f"   Cliente confirmó: '{ultimo_cliente[:40]}'")
                                print(f"   Número extraído: {numero_en_historial} → {numero_whatsapp}")
                                print(f"   [EMOJI] WhatsApp guardado: {numero_whatsapp}")
                                break

        # ============================================================
        # FILTRO 16 (FIX 295/300): Bruce dice "ya lo tengo" pero NO ha capturado contacto
        # FIX 300: Simplificado - si NO tiene contacto capturado, NO puede decir "ya lo tengo"
        # ============================================================
        if not filtro_aplicado:
            # Verificar si Bruce dice "ya lo tengo" o "registrado"
            bruce_dice_ya_tiene = any(frase in respuesta_lower for frase in [
                'ya lo tengo', 'ya lo tengo registrado', 'ya lo tengo anotado',
                'le llegará el catálogo', 'le enviaré el catálogo'
            ])

            if bruce_dice_ya_tiene:
                # FIX 307: Verificar si realmente tenemos un contacto capturado (usar lead_data)
                tiene_whatsapp = bool(self.lead_data.get("whatsapp"))
                tiene_email = bool(self.lead_data.get("email"))

                # FIX 300: SIMPLIFICADO - Si NO tiene contacto, NO puede decir "ya lo tengo"
                # No importa si Bruce pidió el contacto antes - si NO lo tiene, NO lo tiene
                if not tiene_whatsapp and not tiene_email:
                    print(f"\n[EMOJI] FIX 295/300: FILTRO ACTIVADO - Bruce dice 'ya lo tengo' pero NO tiene contacto")
                    print(f"   WhatsApp capturado: {self.lead_data.get('whatsapp')}")
                    print(f"   Email capturado: {self.lead_data.get('email')}")
                    print(f"   Bruce iba a decir: \"{respuesta[:60]}...\"")
                    # Corregir: pedir el contacto en lugar de decir que ya lo tiene
                    respuesta = "Disculpe, ¿me podría proporcionar su número de WhatsApp o correo electrónico para enviarle el catálogo?"
                    filtro_aplicado = True
                    print(f"   Respuesta corregida: \"{respuesta}\"")

        # ============================================================
        # FILTRO 16B (FIX 310): Cliente SOLICITA envío por WhatsApp, Bruce debe pedir número
        # "Si gusta enviarnos la información por WhatsApp"
        # ============================================================
        if not filtro_aplicado:
            ultimos_mensajes_cliente = [
                msg['content'].lower() for msg in self.conversation_history[-3:]
                if msg['role'] == 'user'
            ]

            if ultimos_mensajes_cliente:
                contexto_cliente = ' '.join(ultimos_mensajes_cliente)

                # Detectar cuando cliente SOLICITA que le envíen por WhatsApp
                cliente_solicita_whatsapp = any(frase in contexto_cliente for frase in [
                    'enviarnos la información por whatsapp', 'enviarme la información por whatsapp',
                    'enviarnos la informacion por whatsapp', 'enviarme la informacion por whatsapp',
                    'envíalo por whatsapp', 'envialo por whatsapp', 'mándalo por whatsapp', 'mandalo por whatsapp',
                    'por whatsapp mejor', 'mejor por whatsapp', 'prefiero por whatsapp',
                    'si gusta enviarnos', 'si gusta enviarme', 'si quiere enviarnos', 'si quiere enviarme',
                    'puede enviarme', 'puede enviarnos', 'nos puede enviar', 'me puede enviar',
                    'envíenos', 'envienos', 'envíeme', 'envieme', 'la información por whatsapp',
                    'información por whatsapp', 'informacion por whatsapp'
                ])

                # Bruce NO pide número (responde otra cosa)
                bruce_pide_numero = any(frase in respuesta_lower for frase in [
                    'número de whatsapp', 'numero de whatsapp', 'cuál es su número', 'cual es su numero',
                    'me puede proporcionar', 'proporcionar el número', 'proporcionar el numero',
                    'dígame el número', 'digame el numero', 'su número', 'su numero'
                ])

                tiene_whatsapp = bool(self.lead_data.get("whatsapp"))

                if cliente_solicita_whatsapp and not bruce_pide_numero and not tiene_whatsapp:
                    print(f"\n[PHONE] FIX 310: FILTRO ACTIVADO - Cliente SOLICITA WhatsApp pero Bruce NO pidió número")
                    print(f"   Cliente dijo: \"{contexto_cliente[:80]}...\"")
                    print(f"   Bruce iba a decir: \"{respuesta[:60]}...\"")
                    respuesta = "Claro que sí. ¿Me puede proporcionar el número de WhatsApp para enviarle la información?"
                    filtro_aplicado = True
                    print(f"   Respuesta corregida: \"{respuesta}\"")

        # ============================================================
        # FILTRO 17 (FIX 306): Cliente OFRECE proporcionar contacto
        # "No está, pero si gusta le proporciono su número/correo"
        # ============================================================
        if not filtro_aplicado:
            ultimos_mensajes_cliente = [
                msg['content'].lower() for msg in self.conversation_history[-3:]
                if msg['role'] == 'user'
            ]

            if ultimos_mensajes_cliente:
                contexto_cliente = ' '.join(ultimos_mensajes_cliente)

                # Detectar cuando cliente OFRECE dar información
                # FIX 432: Agregar patrones para detectar "¿no le han pasado?", "te lo paso", etc.
                cliente_ofrece_info = any(frase in contexto_cliente for frase in [
                    'si gusta le proporciono', 'si gusta le doy', 'le proporciono',
                    'le puedo proporcionar', 'le doy el número', 'le doy el numero',
                    'le paso el número', 'le paso el numero', 'le puedo dar',
                    'puedo darle', 'se lo proporciono', 'se lo doy',
                    'si quiere le doy', 'si quiere le paso',
                    # FIX 432: Caso BRUCE1313 - "¿No le han pasado algún"
                    'le han pasado', 'le pasaron', 'te lo paso', 'se lo paso',
                    'no le han pasado', '¿no le han pasado', 'le puedo pasar'
                ])

                # Verificar que Bruce NO está aceptando la oferta correctamente
                bruce_acepta_oferta = any(frase in respuesta_lower for frase in [
                    'sí, por favor', 'si, por favor', 'se lo agradezco',
                    'perfecto', 'claro', 'adelante', 'dígame', 'digame'
                ])

                # Bruce dice algo incoherente como "espero" o "entiendo"
                bruce_respuesta_incoherente = any(frase in respuesta_lower for frase in [
                    'claro, espero', 'espero', 'entiendo que', 'comprendo'
                ]) and not bruce_acepta_oferta

                if cliente_ofrece_info and bruce_respuesta_incoherente:
                    print(f"\n[EMOJI] FIX 306: FILTRO ACTIVADO - Cliente OFRECE proporcionar contacto")
                    print(f"   Cliente dijo: \"{contexto_cliente[:80]}...\"")
                    print(f"   Bruce iba a decir: \"{respuesta[:60]}...\"")
                    respuesta = "Sí, por favor, se lo agradezco mucho."
                    filtro_aplicado = True
                    print(f"   Respuesta corregida: \"{respuesta}\"")

        # ============================================================
        # FILTRO 18 (FIX 309/309b): Cliente indica que es SUCURSAL/PUNTO DE VENTA
        # "Es un punto de venta, aquí no hay oficinas de compras"
        # Bruce debe pedir número de la matriz, NO despedirse NI seguir insistiendo
        # ============================================================
        if not filtro_aplicado:
            import re
            # Patrones que indican sucursal/punto de venta (no manejan compras ahí)
            patrones_sucursal = [
                r'punto\s+de\s+venta',
                r'aqu[ií]\s+no\s+(?:hay|es|tenemos|se\s+encargan)',
                r'no\s+(?:nos\s+)?encargamos?\s+de\s+compra',
                r'no\s+es\s+(?:una?\s+)?oficina',
                r'no\s+hay\s+oficinas?\s+de\s+compras?',
                r'no\s+(?:se\s+)?hace[mn]?\s+compras?\s+aqu[ií]',
                r'(?:es|somos)\s+(?:una?\s+)?sucursal',
                r'las?\s+compras?\s+(?:son|es|están?)\s+en\s+(?:la\s+)?(?:matriz|oficinas?|corporativo)',
                r'(?:aqu[ií]\s+)?no\s+(?:tenemos|hay)\s+quien\s+(?:compre|se\s+encargue)',
                r'no\s+es\s+(?:el\s+)?[aá]rea\s+de\s+compras',
                # FIX 309b: BRUCE737 - más patrones
                r'no\s+hay\s+(?:departamento|compras)',
                r'no\s+(?:tenemos|existe)\s+departamento',
                r'aqu[ií]\s+no\s+hay\s+(?:departamento|compras)',
                # FIX 317: Compras en otra ciudad (BRUCE759)
                r'(?:eso\s+)?est[aá]\s+all[aá]',
                r'es\s+all[aá]',
                r'all[aá]\s+(?:en\s+la\s+)?ciudad',
                r'en\s+(?:otra\s+)?ciudad\s+de',
                r'en\s+(?:cdmx|m[eé]xico|guadalajara|monterrey)',
                r'all[aá]\s+con\s+ellos',
                # FIX 354: BRUCE965 - "no vemos aquí nada", "es directo a la casa"
                r'no\s+vemos?\s+(?:aqu[ií]\s+)?(?:nada|eso)',
                r'(?:es|va)\s+directo\s+(?:a|hacia)\s+(?:la\s+)?casa',
                r'directamente\s+(?:a|hacia)\s+(?:la\s+)?casa',
                r'no\s+(?:lo\s+)?recibimos',
                r'(?:nosotros\s+)?no\s+(?:lo\s+)?vemos',
                r'no\s+(?:nos\s+)?(?:corresponde|toca)',
                r'eso\s+(?:es|va)\s+(?:con|para)\s+(?:la\s+)?(?:oficina|casa|matriz)',
                r'no\s+(?:nos\s+)?encargamos\s+de\s+eso',
                r'(?:aqu[ií]\s+)?no\s+(?:manejamos|vemos)\s+(?:nada\s+de\s+)?(?:eso|compras?|costos?)',
            ]

            cliente_es_sucursal = any(re.search(patron, contexto_cliente, re.IGNORECASE) for patron in patrones_sucursal)

            # Bruce se despide incorrectamente cuando debería pedir número de matriz
            bruce_se_despide = any(frase in respuesta_lower for frase in [
                'disculpe las molestias', 'error con el número', 'que tenga buen día',
                'que tenga excelente día', 'gracias por su tiempo', 'hasta luego',
                'buen día', 'buena tarde', 'disculpe la molestia'
            ])

            # FIX 309b/317/354: Bruce sigue insistiendo con catálogo/whatsapp sin pedir número matriz
            bruce_sigue_insistiendo = any(frase in respuesta_lower for frase in [
                'catálogo digital', 'catalogo digital', 'lista de precios',
                'enviarle nuestro catálogo', 'enviarle nuestro catalogo',
                'compartir nuestro catálogo', 'compartir nuestro catalogo',
                'hay alguien con quien', 'ofrecer a sus clientes',
                'cuál es su número de whatsapp', 'cual es su numero de whatsapp',
                'correo electrónico donde', 'correo electronico donde',
                # FIX 317: Bruce pregunta cuándo llamar en lugar de pedir número
                'momento más conveniente', 'momento mas conveniente',
                'cuándo sería adecuado', 'cuando seria adecuado',
                'llame en otro momento', 'llamar en otro momento',
                # FIX 354: Bruce sigue ofreciendo catálogo cuando cliente dice que no manejan compras
                'le gustaría recibir', 'le gustaria recibir',
                'le gustaría que le envíe', 'le gustaria que le envie',
                'catálogo completo', 'catalogo completo',
                'por whatsapp o correo', 'por correo o whatsapp',
                'hay algo de interés', 'hay algo de interes',
                'hablar con alguien más', 'hablar con alguien mas'
            ])

            # Verificar que Bruce NO está pidiendo número de matriz
            bruce_pide_matriz = any(frase in respuesta_lower for frase in [
                'número de la matriz', 'numero de la matriz', 'número de matriz', 'numero de matriz',
                'área de compras', 'area de compras', 'número del área', 'numero del area',
                'número de las oficinas', 'numero de las oficinas', 'oficinas centrales'
            ])

            if cliente_es_sucursal and (bruce_se_despide or bruce_sigue_insistiendo) and not bruce_pide_matriz:
                print(f"\n[EMOJI] FIX 309/309b: FILTRO ACTIVADO - Cliente indica que es SUCURSAL/PUNTO DE VENTA")
                print(f"   Cliente dijo: \"{contexto_cliente[:100]}...\"")
                print(f"   Bruce iba a decir: \"{respuesta[:80]}...\"")
                print(f"   Bruce se despide: {bruce_se_despide}, Bruce sigue insistiendo: {bruce_sigue_insistiendo}")
                respuesta = "Entiendo, las compras se manejan en la matriz. ¿Me podría proporcionar el número de la matriz o del área de compras?"
                filtro_aplicado = True
                print(f"   Respuesta corregida: \"{respuesta}\"")

        # ============================================================
        # FILTRO 19 (FIX 311): Cliente dice "no" después de pedir número encargado
        # Flujo: encargado no está → pedir su número → cliente dice no → ofrecer catálogo
        # ============================================================
        if not filtro_aplicado:
            # Verificar historial: Bruce pidió número del encargado?
            historial_bruce = ' '.join([
                msg['content'].lower() for msg in self.conversation_history[-4:]
                if msg['role'] == 'assistant'
            ])

            bruce_pidio_numero_encargado = any(frase in historial_bruce for frase in [
                'número directo del encargado', 'numero directo del encargado',
                'número del encargado', 'numero del encargado',
                'proporcionarme el número', 'proporcionarme el numero',
                'proporcionar el número', 'proporcionar el numero'
            ])

            # Cliente dice "no" o similar
            cliente_niega = any(frase in contexto_cliente for frase in [
                'no tengo', 'no lo tengo', 'no sé', 'no se', 'no puedo',
                'no te puedo', 'no le puedo', 'no cuento con',
                # FIX 590 BRUCE1977: Variantes plurales
                'no podemos', 'no lo podemos', 'no le podemos', 'no los podemos',
                'no se lo puedo', 'no se lo podemos'
            ]) or (contexto_cliente.strip() in ['no', 'no.', 'nel', 'nop', 'nope'])

            if bruce_pidio_numero_encargado and cliente_niega:
                print(f"\n[EMOJI] FIX 311: FILTRO ACTIVADO - Cliente niega número del encargado, ofrecer catálogo")
                print(f"   Bruce pidió número del encargado y cliente dijo: \"{contexto_cliente[:50]}\"")
                respuesta = "Entiendo, no hay problema. ¿Le gustaría que le envíe nuestro catálogo por WhatsApp o correo para que lo revise el encargado cuando regrese?"
                filtro_aplicado = True
                print(f"   Respuesta corregida: \"{respuesta}\"")

        # ============================================================
        # FILTRO 19B (FIX 311b): Cliente dice "no se encuentra" y Bruce ofrece catálogo
        # SIN haber pedido primero el número del encargado
        # ============================================================
        if not filtro_aplicado:
            # Detectar si cliente indica que encargado no está
            # FIX 318: Agregar variantes con "ahorita"
            # FIX 438: Caso BRUCE1321 - Agregar "todavía no llega" y variantes
            cliente_dice_no_esta = any(frase in contexto_cliente for frase in [
                'no se encuentra', 'no está', 'no esta', 'salió', 'salio',
                'no lo tenemos', 'gusta dejar', 'dejar mensaje', 'dejar recado',
                'no está ahorita', 'no esta ahorita', 'ahorita no está', 'ahorita no esta',
                # FIX 438: "todavía no llega" indica encargado regresará
                'todavía no llega', 'todavia no llega', 'aún no llega', 'aun no llega',
                'no ha llegado', 'todavía no viene', 'todavia no viene'
            ])

            # Bruce ofrece catálogo directamente sin pedir número del encargado
            bruce_ofrece_catalogo = any(frase in respuesta_lower for frase in [
                'catálogo por whatsapp', 'catalogo por whatsapp',
                'catálogo por correo', 'catalogo por correo',
                'le gustaría recibir', 'le gustaria recibir',
                'envíe nuestro catálogo', 'envie nuestro catalogo',
                'enviarle el catálogo', 'enviarle el catalogo'
            ])

            # Verificar que Bruce NO pidió número del encargado antes
            historial_bruce = ' '.join([
                msg['content'].lower() for msg in self.conversation_history[-4:]
                if msg['role'] == 'assistant'
            ])

            bruce_ya_pidio_numero = any(frase in historial_bruce for frase in [
                'número directo del encargado', 'numero directo del encargado',
                'número del encargado', 'numero del encargado'
            ])

            # FIX 457: BRUCE1370 - NO pedir número si cliente OFRECE dar un correo/número/whatsapp
            # Cliente dijo: "No se encuentra. Si quiere le doy un correo electrónico."
            # Bruce NO debe pedir número, debe ACEPTAR el correo que el cliente ofrece
            cliente_ofrece_dato = any(frase in contexto_cliente for frase in [
                'le doy un correo', 'le doy el correo', 'le paso el correo',
                'le doy un numero', 'le doy el numero', 'le paso el numero',
                'le doy un número', 'le doy el número', 'le paso el número',
                'le doy mi correo', 'le doy mi numero', 'le doy mi número',
                'le paso un correo', 'le paso un numero', 'le paso un número',
                'si quiere le doy', 'si gusta le doy', 'si desea le doy',
                'le puedo dar un correo', 'le puedo dar el correo',
                'le puedo dar un numero', 'le puedo dar el numero',
                'anote el correo', 'anote mi correo', 'apunte el correo',
                'tome nota', 'le comparto',
                # FIX 625B: BRUCE2058 - "te puedo pasar mi teléfono" = ofrece SU dato
                'puedo pasar mi teléfono', 'puedo pasar mi telefono',
                'puedo pasar el teléfono', 'puedo pasar el telefono',
                'puedo pasar mi número', 'puedo pasar mi numero',
                'puedo dar mi teléfono', 'puedo dar mi telefono',
                'puedo dar mi número', 'puedo dar mi numero',
                'te doy mi teléfono', 'le doy mi teléfono',
                'te doy mi telefono', 'le doy mi telefono',
                'te paso mi teléfono', 'le paso mi teléfono',
                'te paso mi telefono', 'le paso mi telefono',
                'yo te puedo apoyar', 'yo le puedo apoyar',
                'dime yo te puedo', 'dime yo te ayudo',
                # FIX 626B: BRUCE2060 - "te paso su teléfono" = ofrece dato del ENCARGADO
                'te paso su teléfono', 'le paso su teléfono',
                'te paso su telefono', 'le paso su telefono',
                'te paso su número', 'le paso su número',
                'te paso su numero', 'le paso su numero',
                'te doy su teléfono', 'le doy su teléfono',
                'te doy su telefono', 'le doy su telefono',
                'te doy su número', 'le doy su número',
                'te doy su numero', 'le doy su numero',
                'te paso el teléfono', 'le paso el teléfono',
                'te paso el telefono', 'le paso el telefono',
                'te paso el número', 'le paso el número',
                'te paso el numero', 'le paso el numero',
                'te doy el teléfono', 'le doy el teléfono',
                'te doy el telefono', 'le doy el telefono',
                'te doy el número', 'le doy el número',
                'te doy el numero', 'le doy el numero',
            ])

            if cliente_ofrece_dato:
                print(f"\n[OK] FIX 457: Cliente OFRECE dato - NO aplicar FIX 311b")
                print(f"   Cliente dijo: \"{contexto_cliente[:60]}...\"")
                print(f"   Bruce usará respuesta de GPT que acepta el dato")
            elif cliente_dice_no_esta and bruce_ofrece_catalogo and not bruce_ya_pidio_numero:
                # FIX 605 BRUCE2021: NO pedir número si cliente ya dijo que NO PUEDE dar contacto
                cliente_rechazo_contacto_605 = any(p in contexto_cliente for p in [
                    'no puedo mandarle', 'no puedo dar', 'no puedo enviar',
                    'no le puedo dar', 'no le puedo mandar', 'no le puedo pasar',
                    'no puedo proporcion', 'no me permiten', 'no nos permiten',
                    'no puedo compartir', 'no, no, no puedo', 'no no puedo'
                ])
                if cliente_rechazo_contacto_605:
                    print(f"\n[OK] FIX 605: Cliente RECHAZÓ dar contacto - Ofrecer contacto de Bruce en vez de pedir número")
                    respuesta = "Entiendo, no se preocupe. ¿Me permite dejarle mi número para que el encargado nos contacte cuando tenga oportunidad?"
                    filtro_aplicado = True
                else:
                    print(f"\n[EMOJI] FIX 311b: FILTRO ACTIVADO - Encargado no está, pedir número ANTES de catálogo")
                    print(f"   Cliente dijo: \"{contexto_cliente[:60]}...\"")
                    print(f"   Bruce iba a ofrecer catálogo: \"{respuesta[:60]}...\"")
                    respuesta = "Entiendo. ¿Me podría proporcionar el número directo del encargado para contactarlo?"
                    filtro_aplicado = True
                    print(f"   Respuesta corregida: \"{respuesta}\"")

        # ============================================================
        # FILTRO 19B2 (FIX 474): BRUCE1433 - Cliente quiere que Bruce vuelva cuando llegue el dueño
        # Problema: Cliente dijo "mejor cuando venga el dueño, al rato llega"
        # Bruce ofreció catálogo en lugar de preguntar a qué hora volver a llamar
        # ============================================================
        if not filtro_aplicado:
            # Patrones que indican "vuelva a llamar cuando llegue el dueño/encargado"
            cliente_quiere_volver_llamar = any(frase in contexto_cliente for frase in [
                # Variantes de "cuando venga/llegue el dueño/encargado"
                'cuando venga el dueño', 'cuando venga el dueno', 'cuando venga el encargado',
                'cuando llegue el dueño', 'cuando llegue el dueno', 'cuando llegue el encargado',
                'mejor cuando venga', 'mejor cuando llegue', 'mejor cuando esté', 'mejor cuando este',
                # "Al rato llega" = el dueño/encargado llegará pronto
                'al rato llega', 'ahorita llega', 'ahorita viene', 'al rato viene',
                'más tarde llega', 'mas tarde llega', 'más tarde viene', 'mas tarde viene',
                'en un rato llega', 'en un rato viene', 'ya mero llega', 'ya mero viene',
                'ahorita no está pero', 'ahorita no esta pero', 'no está pero al rato', 'no esta pero al rato',
                # Variantes directas de "vuelva a llamar"
                'vuelva cuando', 'vuelva a llamar cuando', 'llame cuando', 'marque cuando'
            ])

            # Bruce ofrece catálogo cuando debería preguntar hora para volver a llamar
            bruce_ofrece_catalogo = any(frase in respuesta_lower for frase in [
                'catálogo por whatsapp', 'catalogo por whatsapp',
                'catálogo por correo', 'catalogo por correo',
                'le gustaría que le envíe', 'le gustaria que le envie',
                'envíe nuestro catálogo', 'envie nuestro catalogo',
                'envíe el catálogo', 'envie el catalogo',
                'whatsapp o correo', 'correo o whatsapp'
            ])

            if cliente_quiere_volver_llamar and bruce_ofrece_catalogo:
                print(f"\n[EMOJI] FIX 474: FILTRO ACTIVADO - Cliente quiere que Bruce vuelva cuando llegue el dueño")
                print(f"   Caso BRUCE1433: Cliente dijo 'mejor cuando venga el dueño, al rato llega'")
                print(f"   Cliente dijo: \"{contexto_cliente[:80]}...\"")
                print(f"   Bruce iba a ofrecer catálogo: \"{respuesta[:60]}...\"")
                respuesta = "Claro, con gusto. ¿A qué hora me recomienda llamar para encontrarlo?"
                filtro_aplicado = True
                print(f"   Respuesta corregida: \"{respuesta}\"")

        # ============================================================
        # FILTRO 19B3 (FIX 478): BRUCE1444 - Cliente pide que Bruce marque en un día específico
        # Problema: Cliente dijo "marque el lunes" pero Bruce no entendió
        # ============================================================
        if not filtro_aplicado:
            # Patrones de días de la semana y momentos
            dias_semana = ['lunes', 'martes', 'miércoles', 'miercoles', 'jueves', 'viernes', 'sábado', 'sabado', 'domingo']
            momentos = ['mañana', 'manana', 'pasado mañana', 'pasado manana', 'la próxima semana', 'la proxima semana', 'otro día', 'otro dia']

            # Detectar si cliente pide callback en día específico
            cliente_pide_dia = any(frase in contexto_cliente for frase in [
                # Marque/llame + día
                'marque el', 'márqueme el', 'marqueme el', 'llámeme el', 'llameme el',
                'llame el', 'hable el', 'hábleme el', 'hableme el',
                # FIX 480: BRUCE1446 - "Si gusta marcar el día lunes"
                'si gusta marcar', 'si gustas marcar', 'marcar el día', 'marcar el dia',
                'si gusta marcar el', 'si gustas marcar el', 'si gusta llamar', 'si gustas llamar',
                # FIX 695: "hablar" variantes
                'si gusta hablar', 'si gustas hablar', 'hablar luego', 'hablar más tarde',
                # FIX 480: "Se presenta hasta el lunes" = encargado estará el lunes
                'se presenta hasta', 'se presenta el', 'estará hasta el', 'estara hasta el',
                'está hasta el', 'esta hasta el', 'viene hasta el', 'llega hasta el',
                # Mejor + día
                'mejor el', 'mejor hasta el', 'hasta el',
                # Mañana/después
                'mañana', 'manana', 'pasado mañana', 'pasado manana',
                'la próxima semana', 'la proxima semana', 'el próximo', 'el proximo',
                # Indirectas
                'regrese', 'regresa', 'vuelva', 'vuelve'
            ])

            # Verificar que menciona un día de la semana o momento
            menciona_dia = any(dia in contexto_cliente for dia in dias_semana + momentos)

            # Bruce no entendió y ofrece catálogo o sigue la conversación normal
            bruce_no_entendio = not any(frase in respuesta_lower for frase in [
                'el lunes', 'el martes', 'el miércoles', 'el miercoles', 'el jueves', 'el viernes',
                'mañana', 'manana', 'próxima semana', 'proxima semana',
                'ese día', 'ese dia', 'a esa hora', 'en ese momento',
                'le marco', 'le llamo', 'le hablo', 'me comunico'
            ])

            if cliente_pide_dia and menciona_dia and bruce_no_entendio:
                # Extraer el día mencionado
                dia_mencionado = None
                for dia in dias_semana:
                    if dia in contexto_cliente:
                        dia_mencionado = dia.capitalize()
                        break
                for momento in momentos:
                    if momento in contexto_cliente:
                        dia_mencionado = momento
                        break

                print(f"\n[EMOJI] FIX 478: FILTRO ACTIVADO - Cliente pide callback en día específico")
                print(f"   Caso BRUCE1444: Cliente dijo 'marque el lunes'")
                print(f"   Cliente dijo: \"{contexto_cliente[:80]}...\"")
                print(f"   Día detectado: {dia_mencionado}")
                print(f"   Bruce iba a decir: \"{respuesta[:60]}...\"")

                # FIX 665: BRUCE2161 - Detectar si cliente YA mencionó la hora en el mismo mensaje
                # Problema: Cliente dijo "mañana a las 9:00 de la mañana" pero Bruce preguntó "¿A qué hora?"
                patron_hora = r'\b(\d{1,2}):?(\d{2})?\s*(am|pm|de la mañana|de la manana|de la tarde|de la noche)?\b'
                hora_match = re.search(patron_hora, contexto_cliente)

                # También detectar horas escritas en palabras: "nueve", "diez", "once"
                horas_palabras = ['ocho', 'nueve', 'diez', 'once', 'doce', 'una', 'dos', 'tres', 'cuatro', 'cinco', 'seis', 'siete']
                menciona_hora_palabra = any(f" {hora} " in f" {contexto_cliente} " for hora in horas_palabras)

                if hora_match or menciona_hora_palabra:
                    hora_mencionada = hora_match.group(0) if hora_match else "la hora que mencionó"
                    print(f"    [FIX 665] Cliente YA mencionó hora: {hora_mencionada}")
                    print(f"    NO preguntar '¿A qué hora?' - Cliente ya dio la hora")

                    # Responder sin preguntar la hora
                    if dia_mencionado:
                        respuesta = f"Perfecto, le marco el {dia_mencionado} a esa hora. Muchas gracias."
                    else:
                        respuesta = "Perfecto, le marco a esa hora. Muchas gracias."
                else:
                    # Cliente NO mencionó hora → preguntar
                    if dia_mencionado:
                        respuesta = f"Perfecto, le marco el {dia_mencionado}. ¿A qué hora le queda mejor?"
                    else:
                        respuesta = "Claro, ¿qué día y a qué hora le queda mejor para llamarle?"

                filtro_aplicado = True
                print(f"   Respuesta corregida: \"{respuesta}\"")

        # ============================================================
        # FILTRO 19C (FIX 437): Bruce YA pidió número de encargado, cliente confirma
        # pero Bruce ofrece catálogo en lugar de esperar el número
        # Caso BRUCE1322: Bruce preguntó número, cliente dijo "Por favor,", Bruce ofreció catálogo
        # ============================================================
        if not filtro_aplicado:
            historial_bruce = ' '.join([
                msg['content'].lower() for msg in self.conversation_history[-4:]
                if msg['role'] == 'assistant'
            ])

            bruce_ya_pidio_numero = any(frase in historial_bruce for frase in [
                'número directo del encargado', 'numero directo del encargado',
                'número del encargado', 'numero del encargado',
                '¿me podría proporcionar el número', '¿me podria proporcionar el numero'
            ])

            # Cliente dice frases de confirmación/espera que indican que va a dar el número
            cliente_confirma_o_espera = any(frase in contexto_cliente for frase in [
                'por favor', 'porfavor', 'sí', 'si', 'claro', 'adelante', 'dale',
                'un momento', 'un segundo', 'espere', 'espéreme', 'espereme',
                'ahí le paso', 'ahi le paso', 'déjeme', 'dejeme',
                'ok', 'va', 'sale', 'perfecto', 'listo'
            ])

            # Bruce ofrece catálogo cuando debería estar esperando el número
            bruce_ofrece_catalogo = any(frase in respuesta_lower for frase in [
                'catálogo por whatsapp', 'catalogo por whatsapp',
                'catálogo por correo', 'catalogo por correo',
                'le gustaría recibir', 'le gustaria recibir',
                'envíe nuestro catálogo', 'envie nuestro catalogo',
                'whatsapp o correo', 'correo o whatsapp'
            ])

            if bruce_ya_pidio_numero and cliente_confirma_o_espera and bruce_ofrece_catalogo:
                print(f"\n[EMOJI] FIX 437: FILTRO ACTIVADO - Bruce YA pidió número, cliente confirmó, NO ofrecer catálogo")
                print(f"   Caso: BRUCE1322 - Cliente dijo 'Por favor,' y Bruce ofreció catálogo")
                print(f"   Historial Bruce: pidió número del encargado")
                print(f"   Cliente dijo: \"{contexto_cliente[:60]}...\"")
                print(f"   Bruce iba a ofrecer: \"{respuesta[:60]}...\"")
                respuesta = "Perfecto. Adelante, lo escucho."
                filtro_aplicado = True
                print(f"   Respuesta corregida: \"{respuesta}\"")

        # ============================================================
        # FILTRO 20 (FIX 315/329): Cliente YA indicó preferencia (correo/whatsapp)
        # Bruce pregunta por el otro en lugar de pedir el que cliente dijo
        # FIX 329: También detectar cuando Bruce pregunta "WhatsApp o correo" cuando
        # cliente YA especificó su preferencia
        # ============================================================
        if not filtro_aplicado:
            # Detectar si cliente ya dijo su preferencia
            # FIX 446: Listas ampliadas para detección de preferencia de contacto
            cliente_prefiere_correo = any(frase in contexto_cliente for frase in [
                # Básicos
                'por correo', 'correo electrónico', 'correo electronico',
                'el correo', 'mi correo', 'email', 'mejor correo',
                # FIX 446: Variantes adicionales
                'al correo', 'a mi correo', 'a su correo',
                'mándalo al correo', 'mandalo al correo', 'envíalo al correo', 'envialo al correo',
                'mándamelo al correo', 'mandamelo al correo',
                'mande al correo', 'envíe al correo', 'envie al correo',
                'por mail', 'al mail', 'mi mail', 'el mail',
                'prefiero correo', 'mejor por correo', 'por correo mejor',
                'mándelo por correo', 'mandelo por correo', 'envíelo por correo', 'envielo por correo',
                'le doy el correo', 'le paso el correo', 'te doy el correo',
                'anota el correo', 'apunta el correo',
                # FIX 485: BRUCE1464 - Detectar preguntas confirmando correo: "¿Es por correo?"
                '¿es por correo?', 'es por correo?', '¿por correo?', 'por correo?',
                '¿correo?', 'correo?', '¿es correo?', 'es correo?',
                '¿está bien por correo?', 'esta bien por correo?',
                '¿puede ser por correo?', 'puede ser por correo?',
                'correo está bien', 'correo esta bien', 'por correo está bien', 'por correo esta bien'
            ])

            cliente_prefiere_whatsapp = any(frase in contexto_cliente for frase in [
                # Básicos
                'por whatsapp', 'por wasa', 'whatsapp', 'wasa',
                'mi whats', 'mejor whatsapp', 'mejor whats',
                'mandar por whatsapp', 'enviar por whatsapp',  # FIX 329
                'me podrás mandar', 'me podras mandar',  # FIX 329: "¿No me podrás mandar por WhatsApp?"
                # FIX 446: Variantes adicionales
                'al whatsapp', 'a mi whatsapp', 'a su whatsapp',
                'mándalo al whatsapp', 'mandalo al whatsapp', 'envíalo al whatsapp', 'envialo al whatsapp',
                'mándamelo al whatsapp', 'mandamelo al whatsapp',
                'mande al whatsapp', 'envíe al whatsapp', 'envie al whatsapp',
                'por whats', 'al whats', 'mi whats', 'el whats',
                'prefiero whatsapp', 'mejor por whatsapp', 'por whatsapp mejor',
                'mándelo por whatsapp', 'mandelo por whatsapp', 'envíelo por whatsapp', 'envielo por whatsapp',
                'le doy el whatsapp', 'le paso el whatsapp', 'te doy el whatsapp',
                'anota el whatsapp', 'apunta el whatsapp',
                'manda al wasa', 'envía al wasa', 'envia al wasa',
                'por wasap', 'al wasap', 'por guasa', 'al guasa',
                # FIX 485: BRUCE1464 - Detectar preguntas confirmando WhatsApp: "¿Es por WhatsApp?"
                '¿es por whatsapp?', 'es por whatsapp?', '¿por whatsapp?', 'por whatsapp?',
                '¿whatsapp?', 'whatsapp?', '¿es whatsapp?', 'es whatsapp?',
                '¿está bien por whatsapp?', 'esta bien por whatsapp?',
                '¿puede ser por whatsapp?', 'puede ser por whatsapp?',
                'whatsapp está bien', 'whatsapp esta bien', 'por whatsapp está bien', 'por whatsapp esta bien',
                '¿por wasa?', 'por wasa?', '¿wasa?', 'wasa?'
            ])

            # Bruce pregunta por el método equivocado
            bruce_pide_whatsapp = any(frase in respuesta_lower for frase in [
                'cuál es su whatsapp', 'cual es su whatsapp',
                'número de whatsapp', 'numero de whatsapp',
                'su whatsapp', 'tu whatsapp'
            ])

            bruce_pide_correo = any(frase in respuesta_lower for frase in [
                'cuál es su correo', 'cual es su correo',
                'su correo electrónico', 'su correo electronico',
                'dígame el correo', 'digame el correo'
            ])

            # FIX 329: Bruce pregunta por AMBAS opciones cuando cliente ya eligió una
            bruce_pregunta_ambas = any(frase in respuesta_lower for frase in [
                'whatsapp o correo', 'correo o whatsapp',
                'whatsapp o por correo', 'correo o por whatsapp',
                'le gustaría recibir', 'le gustaria recibir',
                'prefiere whatsapp', 'prefiere correo'
            ])

            if cliente_prefiere_correo and bruce_pide_whatsapp:
                print(f"\n[EMAIL] FIX 315: FILTRO ACTIVADO - Cliente prefiere CORREO pero Bruce pide WhatsApp")
                print(f"   Cliente dijo: \"{contexto_cliente[:60]}...\"")
                print(f"   Bruce iba a pedir WhatsApp: \"{respuesta[:60]}...\"")
                respuesta = "Perfecto, dígame el correo y lo anoto."
                filtro_aplicado = True
                print(f"   Respuesta corregida: \"{respuesta}\"")

            elif cliente_prefiere_whatsapp and bruce_pide_correo:
                print(f"\n[PHONE] FIX 315: FILTRO ACTIVADO - Cliente prefiere WHATSAPP pero Bruce pide correo")
                print(f"   Cliente dijo: \"{contexto_cliente[:60]}...\"")
                print(f"   Bruce iba a pedir correo: \"{respuesta[:60]}...\"")
                respuesta = "Perfecto. ¿Me confirma su número de WhatsApp para enviarle el catálogo?"
                filtro_aplicado = True
                print(f"   Respuesta corregida: \"{respuesta}\"")

            # FIX 329: Cliente ya dijo WhatsApp pero Bruce pregunta "WhatsApp o correo"
            elif cliente_prefiere_whatsapp and bruce_pregunta_ambas:
                print(f"\n[PHONE] FIX 329: FILTRO ACTIVADO - Cliente YA dijo WhatsApp pero Bruce pregunta ambas opciones")
                print(f"   Cliente dijo: \"{contexto_cliente[:60]}...\"")
                print(f"   Bruce iba a preguntar: \"{respuesta[:60]}...\"")
                respuesta = "Perfecto. ¿Me confirma su número de WhatsApp para enviarle el catálogo?"
                filtro_aplicado = True
                print(f"   Respuesta corregida: \"{respuesta}\"")

            # FIX 329: Cliente ya dijo correo pero Bruce pregunta "WhatsApp o correo"
            elif cliente_prefiere_correo and bruce_pregunta_ambas:
                print(f"\n[EMAIL] FIX 329: FILTRO ACTIVADO - Cliente YA dijo correo pero Bruce pregunta ambas opciones")
                print(f"   Cliente dijo: \"{contexto_cliente[:60]}...\"")
                print(f"   Bruce iba a preguntar: \"{respuesta[:60]}...\"")
                respuesta = "Perfecto, dígame el correo y lo anoto."
                filtro_aplicado = True
                print(f"   Respuesta corregida: \"{respuesta}\"")

        # ============================================================
        # FILTRO 20b (FIX 330/332): Cliente OFRECE número de oficinas/encargado
        # O indica que es SUCURSAL y debe llamar a oficinas
        # Bruce NO debe ignorar esto - debe pedir el número
        # FIX 332: Expandir detección para "sería número de oficina", "sería con oficina"
        # ============================================================
        if not filtro_aplicado:
            # Detectar si cliente ofrece dar un número o indica que es sucursal
            cliente_ofrece_numero = any(frase in contexto_cliente for frase in [
                'le doy el número', 'le doy el numero', 'te doy el número', 'te doy el numero',
                'le paso el número', 'le paso el numero', 'te paso el número', 'te paso el numero',
                'le doy el teléfono', 'le doy el telefono', 'anota el número', 'anota el numero',
                'apunta el número', 'apunta el numero', 'es el número', 'es el numero',
                'número de oficinas', 'numero de oficinas', 'número de la oficina', 'numero de la oficina',
                'número del encargado', 'numero del encargado', 'número directo', 'numero directo',
                'hablando a una sucursal', 'esto es sucursal', 'esta es sucursal',
                # FIX 332: Más variantes
                'sería número', 'seria numero', 'sería el número', 'seria el numero',
                'sería lo que es oficina', 'seria lo que es oficina',
                'sería con oficina', 'seria con oficina', 'sería con lo que es oficina',
                'no sería este número', 'no seria este numero', 'no sería con nosotros',
                'aquí en una sucursal', 'aqui en una sucursal', 'somos sucursal',
                'esto es una sucursal', 'estamos en sucursal', 'ahí lo comunican',
                'ahi lo comunican', 'lo comunican', 'lo transfieren'
            ])

            # Bruce ignora y dice algo irrelevante
            bruce_ignora_oferta = any(frase in respuesta_lower for frase in [
                'hay algo más', 'hay algo mas', 'algo más en lo que',
                'le gustaría recibir', 'le gustaria recibir',
                'whatsapp o correo', 'correo o whatsapp',
                'que tenga buen día', 'que tenga excelente día',
                'gracias por su tiempo', 'hasta luego',
                # FIX 332: También cuando Bruce pregunta por encargado ignorando que es sucursal
                'se encontrará el encargado', 'se encontrara el encargado',
                'encargado de compras', 'encargada de compras',
                # FIX 332: O cuando dice "ya lo tengo registrado" sin tener dato
                'ya lo tengo registrado', 'ya tengo registrado',
                # FIX 335: Bruce habla de ubicación cuando cliente ofrece número
                'estamos ubicados', 'ubicados en', 'hacemos envíos', 'hacemos envios',
                'toda la república', 'toda la republica'
            ])

            if cliente_ofrece_numero and bruce_ignora_oferta:
                print(f"\n[EMOJI] FIX 330/332/335: FILTRO ACTIVADO - Cliente ofrece número pero Bruce ignora")
                print(f"   Cliente dijo: \"{contexto_cliente[:80]}...\"")
                print(f"   Bruce iba a decir: \"{respuesta[:60]}...\"")

                # FIX 335: Detectar si es sucursal o si simplemente ofrecen número
                es_sucursal = any(frase in contexto_cliente for frase in [
                    'sucursal', 'oficinas', 'oficina', 'cedis', 'corporativo'
                ])

                if es_sucursal:
                    respuesta = "Entiendo, es una sucursal. ¿Me podría proporcionar el número de oficinas para comunicarme con el encargado?"
                else:
                    # Cliente simplemente ofrece dar un número
                    respuesta = "Perfecto, estoy listo para anotarlo."

                filtro_aplicado = True
                print(f"   Respuesta corregida: \"{respuesta}\"")

        # ============================================================
        # FILTRO 21 (FIX 316/323): Bruce se despide cuando cliente solo saluda
        # "Buen día" no es despedida, es saludo - no colgar!
        # FIX 323: Ser más agresivo - también cuando dice "gracias por la información"
        # pero el cliente NO dio ninguna información (solo saludos)
        # FIX 323b: También detectar "¿En qué le puedo ayudar?" - cliente OFRECE ayuda
        # ============================================================
        if not filtro_aplicado:
            # Saludos simples que NO son despedidas
            saludos_simples = [
                'buen día', 'buen dia', 'buenos días', 'buenos dias',
                'buenas tardes', 'buenas noches', 'buenas', 'hola',
                'qué tal', 'que tal', 'diga', 'dígame', 'digame'
            ]

            # FIX 323b: Frases donde cliente OFRECE ayuda (definitivamente NO es despedida)
            cliente_ofrece_ayuda = any(frase in contexto_cliente for frase in [
                'en qué le puedo', 'en que le puedo', 'en qué puedo', 'en que puedo',
                'le puedo ayudar', 'puedo ayudar', 'cómo le ayudo', 'como le ayudo',
                'qué se le ofrece', 'que se le ofrece', 'mande', 'dígame'
            ])

            # Verificar si cliente SOLO dijo un saludo (contexto corto)
            contexto_es_saludo = any(saludo in contexto_cliente for saludo in saludos_simples)
            contexto_es_corto = len(contexto_cliente.split()) <= 8  # FIX 323b: aumentar a 8 palabras

            # Bruce se despide incorrectamente
            bruce_se_despide = any(frase in respuesta_lower for frase in [
                'que tenga excelente día', 'que tenga excelente dia',
                'que tenga buen día', 'que tenga buen dia',
                'le marco entonces', 'gracias por la información',
                'gracias por la informacion', 'hasta luego',
                # FIX 323: Agregar más frases de despedida prematura
                'muchas gracias por la información', 'muchas gracias por la informacion',
                'perfecto, muchas gracias', 'gracias por su tiempo'
            ])

            # FIX 323: También verificar si en TODO el historial el cliente NO dio información real
            # Solo hay saludos repetidos
            historial_cliente = ' '.join([
                msg['content'].lower() for msg in self.conversation_history
                if msg['role'] == 'user'
            ])

            # FIX 531: BRUCE1806 - "ella habla", "él habla", "yo soy" indican que el cliente ES el encargado
            # NO deben clasificarse como "solo saludos", son información importante
            frases_cliente_es_encargado = [
                'ella habla', 'él habla', 'el habla', 'yo habla',  # Variantes de "él/ella habla"
                'yo soy', 'yo soy el', 'yo soy la', 'soy el encargado', 'soy la encargada',
                'soy yo', 'sería yo', 'seria yo', 'conmigo', 'es conmigo',
                'yo mero', 'yo mera', 'servidor', 'servidora', 'un servidor', 'una servidora'
            ]
            cliente_es_encargado = any(frase in historial_cliente for frase in frases_cliente_es_encargado)

            if cliente_es_encargado:
                print(f"    FIX 531: BRUCE1806 - Cliente indicó que ES el encargado - NO aplicar filtro de 'solo saludos'")

            # FIX 323b: Palabras neutrales que NO cuentan como "información"
            palabras_neutrales = saludos_simples + [
                'sí', 'si', 'alo', 'aló', 'bueno', 'en', 'qué', 'que', 'le', 'puedo',
                'ayudar', 'cómo', 'como', 'mande', 'diga', 'se', 'ofrece', 'a'
            ]
            # FIX 531: Si cliente ES encargado, NO clasificar como "solo saludos"
            cliente_solo_saluda = False if cliente_es_encargado else (all(
                any(saludo in palabra for saludo in palabras_neutrales)
                for palabra in historial_cliente.split()
            ) if historial_cliente else True)

            # FIX 323/323b: Si cliente saluda/ofrece ayuda Y Bruce intenta despedirse = ERROR
            if ((contexto_es_saludo or cliente_ofrece_ayuda) and contexto_es_corto and bruce_se_despide) or \
               (cliente_solo_saluda and bruce_se_despide and not tiene_contacto):
                print(f"\n[EMOJI] FIX 316/323: FILTRO ACTIVADO - Cliente SALUDA/OFRECE AYUDA pero Bruce se DESPIDE")
                print(f"   Cliente dijo: \"{contexto_cliente}\"")
                print(f"   Cliente ofrece ayuda: {cliente_ofrece_ayuda}")
                print(f"   Historial cliente (solo saludos): {cliente_solo_saluda}")
                print(f"   Bruce iba a despedirse: \"{respuesta[:60]}...\"")
                respuesta = "Me comunico de la marca NIOVAL para brindar información de nuestros productos ferreteros. ¿Se encontrará el encargado de compras?"
                filtro_aplicado = True
                print(f"   Respuesta corregida: \"{respuesta}\"")

        # ============================================================
        # FILTRO CONSOLIDADO: ENCARGADO NO ESTÁ (FIX 318/321/326/328/333/341)
        # Combina FILTRO 22 y FILTRO 23 en uno solo más completo
        # Maneja todas las variantes de "no está el encargado" y respuestas incorrectas
        # ============================================================
        if not filtro_aplicado:
            # FIX 341/348/349: Lista COMPLETA de patrones que indican que el encargado NO está
            patrones_no_esta = [
                'no está', 'no esta', 'no se encuentra', 'salió', 'salio',
                'no está ahorita', 'no esta ahorita', 'ahorita no está', 'ahorita no esta',
                'no, no está', 'no, no esta', 'no lo tenemos', 'se fue', 'no hay nadie',
                'ahorita no', 'ahorita no se', 'no los encuentro', 'no lo encuentro',
                'no la encuentro', 'no se sabe', 'no sabemos', 'no tienen horario',
                'no tiene horario', 'no sabría decirle', 'no sabria decirle',
                'está fuera', 'esta fuera', 'está ocupado', 'esta ocupado',
                'no viene hoy', 'no trabaja hoy', 'ya se fue',
                # FIX 348/349/360: "No" simple o "por el momento no" después de preguntar por encargado
                'por el momento no', 'por el momento no,', 'por el momento, no',
                'no, por el momento', 'no por el momento',
                'en este momento no', 'en este momento, no',
                'no, disculpe', 'no disculpe', 'no, lo siento',
                'no, ahorita no', 'ahorita no está disponible', 'ahorita no esta disponible',
                # FIX 360: Variantes con múltiples "no"
                'no, no, ahorita no', 'no no ahorita no', 'no, no ahorita',
                'no, no, no', 'no no no', 'no, no se encuentra', 'no no se encuentra',
                'no, no sé', 'no no se', 'no, no lo encuentro', 'no no lo encuentro',
                'no te encuentro', 'no lo encuentro ahorita', 'no te encuentro ahorita',
                # FIX 438: Caso BRUCE1321 - "todavía no llega" indica encargado regresará
                'todavía no llega', 'todavia no llega', 'aún no llega', 'aun no llega',
                'no ha llegado', 'todavía no viene', 'todavia no viene'
            ]
            cliente_dice_no_esta = any(frase in contexto_cliente for frase in patrones_no_esta)

            # Verificar que NO es una transferencia real (cliente pasando llamada)
            patrones_transferencia = [
                'te lo paso', 'se lo paso', 'ahorita te lo paso', 'te comunico',
                'espérame', 'esperame', 'un momento', 'permíteme', 'permiteme',
                'en un momento', 'ahora lo paso', 'ahora te lo paso'
            ]
            es_transferencia = any(frase in contexto_cliente for frase in patrones_transferencia)

            # FIX 326: Detectar si cliente sugiere llamar después
            patrones_llamar_despues = [
                'llamar más tarde', 'llamar mas tarde', 'llame más tarde', 'llame mas tarde',
                'guste llamar', 'quiere llamar', 'llamar después', 'llamar despues',
                'llamar en la tarde', 'llamar mañana', 'llamar manana',
                'marque más tarde', 'marque mas tarde', 'marque después', 'marque despues',
                'vuelva a llamar', 'intente más tarde', 'intente mas tarde'
            ]
            cliente_sugiere_despues = any(frase in contexto_cliente for frase in patrones_llamar_despues)

            # FIX 341: TODAS las respuestas incorrectas de Bruce cuando cliente dice "no está"
            respuestas_incorrectas_bruce = [
                # Bruce dice "espero" cuando no hay nadie que lo transfiera
                'claro, espero', 'claro espero', 'claro, aquí espero',
                'perfecto, espero', 'aquí espero',
                # Bruce repite la pregunta del encargado
                'se encontrará el encargado', 'se encontrara el encargado',
                'está el encargado', 'esta el encargado',
                'se encuentra el encargado', 'encargado de compras',
                'encargada de compras', 'claro. ¿se encontrará', 'claro. ¿se encontrara',
                # Bruce dice "hay algo más" en lugar de pedir contacto
                'hay algo más', 'hay algo mas', 'algo más en lo que',
                'algo mas en lo que', 'en qué puedo ayudar', 'en que puedo ayudar',
                'puedo ayudarle', 'le puedo ayudar'
            ]
            bruce_responde_mal = any(frase in respuesta_lower for frase in respuestas_incorrectas_bruce)

            # Solo activar si cliente dice "no está" Y Bruce responde mal Y NO es transferencia
            if cliente_dice_no_esta and bruce_responde_mal and not es_transferencia:
                print(f"\n[EMOJI] FIX 341 CONSOLIDADO: Cliente dice NO ESTÁ pero Bruce responde mal")
                print(f"   Cliente dijo: \"{contexto_cliente[:60]}...\"")
                print(f"   Bruce iba a decir: \"{respuesta[:60]}...\"")

                # Determinar respuesta apropiada según contexto
                if cliente_sugiere_despues:
                    respuesta = "Perfecto, le llamo más tarde entonces. ¿A qué hora sería mejor para encontrar al encargado?"
                    print(f"   → Cliente sugiere llamar después - preguntando horario")
                else:
                    respuesta = "Entiendo. ¿Me podría proporcionar el número directo del encargado para contactarlo?"
                    print(f"   → Pidiendo número directo del encargado")

                filtro_aplicado = True
                print(f"   Respuesta corregida: \"{respuesta}\"")

        # ============================================================
        # FILTRO 24 (FIX 322/327/342): Cliente pregunta "¿De dónde te comunicas?" o "¿Quién habla?"
        # Bruce debe responder con presentación INCLUYENDO SU NOMBRE
        # FIX 327: Agregar nombre "Bruce" cuando preguntan "quién habla"
        # FIX 342: Agregar más variantes de "de dónde" y detectar respuestas incoherentes
        # ============================================================
        if not filtro_aplicado:
            # FIX 342: Lista completa de preguntas sobre origen/identidad
            cliente_pregunta_origen = any(frase in contexto_cliente for frase in [
                'de dónde', 'de donde', 'de dónde te comunicas', 'de donde te comunicas',
                'de dónde llama', 'de donde llama', 'de dónde habla', 'de donde habla',
                'de dónde nos marca', 'de donde nos marca', 'de dónde me marca', 'de donde me marca',
                'de dónde nos llama', 'de donde nos llama', 'de dónde me llama', 'de donde me llama',
                'de qué empresa', 'de que empresa', 'de parte de quién', 'de parte de quien',
                'qué empresa', 'que empresa', 'cuál empresa', 'cual empresa',
                'qué marca', 'que marca', 'cuál marca', 'cual marca'
            ])

            # FIX 327/390: Detectar específicamente "¿Quién habla?" y variantes
            cliente_pregunta_quien = any(frase in contexto_cliente for frase in [
                'quién habla', 'quien habla', 'quién llama', 'quien llama',
                'quién es', 'quien es', 'con quién hablo', 'con quien hablo',
                # FIX 390: Agregar "con quién tengo el gusto" (caso BRUCE1083)
                'con quién tengo el gusto', 'con quien tengo el gusto',
                'quién tengo el gusto', 'quien tengo el gusto'
            ])

            # FIX 342: Bruce responde algo INCOHERENTE (no relacionado con la pregunta)
            bruce_responde_incoherente = any(frase in respuesta_lower for frase in [
                'hay algo más', 'hay algo mas', 'perfecto.', 'gracias por',
                'que tenga buen', 'que tenga excelente', 'hasta luego',
                'me escucha', '¿me escucha'
            ])

            # Bruce NO responde la pregunta (ofrece catálogo o algo irrelevante)
            bruce_no_responde_origen = not any(frase in respuesta_lower for frase in [
                'nioval', 'ferretería', 'ferreteria', 'productos ferreteros',
                'marca nioval', 'de la marca', 'guadalajara', 'jalisco'
            ])

            bruce_no_dice_nombre = 'bruce' not in respuesta_lower

            # FIX 342: Si cliente pregunta origen Y Bruce responde incoherente O no responde origen
            if cliente_pregunta_origen and (bruce_no_responde_origen or bruce_responde_incoherente):
                print(f"\n[EMOJI] FIX 322/342: FILTRO ACTIVADO - Cliente pregunta ORIGEN pero Bruce no responde")
                print(f"   Cliente preguntó: \"{contexto_cliente[:60]}...\"")
                print(f"   Bruce iba a decir: \"{respuesta[:60]}...\"")
                print(f"   No responde origen: {bruce_no_responde_origen}, Responde incoherente: {bruce_responde_incoherente}")
                respuesta = "Mi nombre es Bruce, me comunico de parte de la marca NIOVAL. Distribuimos productos de ferretería. ¿Se encontrará el encargado de compras?"
                filtro_aplicado = True
                print(f"   Respuesta corregida: \"{respuesta}\"")

            # FIX 327: Si preguntan específicamente "quién habla" y Bruce no dice su nombre
            elif cliente_pregunta_quien and (bruce_no_dice_nombre or bruce_responde_incoherente):
                print(f"\n[EMOJI] FIX 327/342: FILTRO ACTIVADO - Cliente pregunta QUIÉN HABLA pero Bruce no dice nombre")
                print(f"   Cliente preguntó: \"{contexto_cliente[:60]}...\"")
                print(f"   Bruce iba a decir: \"{respuesta[:60]}...\"")
                respuesta = "Mi nombre es Bruce, me comunico de parte de la marca NIOVAL para ofrecer información de nuestros productos ferreteros. ¿Se encontrará el encargado de compras?"
                filtro_aplicado = True
                print(f"   Respuesta corregida: \"{respuesta}\"")

        # ============================================================
        # FILTRO 25 (FIX 322): Bruce dice "ya lo tengo registrado" sin
        # haber pedido/recibido ningún dato - error grave
        # ============================================================
        if not filtro_aplicado:
            # Bruce dice que ya tiene registrado algo
            bruce_dice_registrado = any(frase in respuesta_lower for frase in [
                'ya lo tengo registrado', 'ya lo tengo anotado',
                'ya tengo registrado', 'ya tengo anotado',
                'le llegará el catálogo', 'le llegara el catalogo'
            ])

            # Verificar si realmente hay un correo/whatsapp capturado
            # FIX 639C: BRUCE2068 - Verificar lead_data ademas de atributos legacy
            # Problema: ultimo_correo_capturado NUNCA se setea, pero lead_data["email"] SI (por FIX 505)
            tiene_correo = (hasattr(self, 'ultimo_correo_capturado') and self.ultimo_correo_capturado) or bool(self.lead_data.get("email"))
            tiene_whatsapp = (hasattr(self, 'ultimo_whatsapp_capturado') and self.ultimo_whatsapp_capturado) or bool(self.lead_data.get("whatsapp"))

            # FIX 356: Buscar en historial si cliente REALMENTE dio algún dato de contacto
            # No basta con que haya dígitos - debe ser en contexto de dar número
            historial_cliente = ' '.join([
                msg['content'].lower() for msg in self.conversation_history
                if msg['role'] == 'user'
            ])
            cliente_dio_correo = '@' in historial_cliente or 'arroba' in historial_cliente

            # FIX 356: Verificar que cliente DIO número en contexto de WhatsApp/contacto
            # No solo contar dígitos - verificar que hubo intercambio de número
            ultimos_mensajes = [msg['content'].lower() for msg in self.conversation_history[-8:] if msg['role'] == 'user']
            contexto_numero = ' '.join(ultimos_mensajes)

            # Verificar si Bruce PIDIÓ número y cliente lo DIO
            mensajes_bruce = [msg['content'].lower() for msg in self.conversation_history[-8:] if msg['role'] == 'assistant']
            bruce_pidio_numero = any(frase in ' '.join(mensajes_bruce) for frase in [
                'número de whatsapp', 'numero de whatsapp', 'su whatsapp',
                'su número', 'su numero', 'cuál es el número', 'cual es el numero',
                'me proporciona', 'me puede dar'
            ])

            # Cliente dio número solo si: Bruce pidió Y cliente respondió con dígitos
            import re
            digitos_en_contexto = len(re.findall(r'\d', contexto_numero))
            cliente_dio_whatsapp = bruce_pidio_numero and digitos_en_contexto >= 8

            tiene_dato_real = tiene_correo or tiene_whatsapp or cliente_dio_correo or cliente_dio_whatsapp

            if bruce_dice_registrado and not tiene_dato_real:
                print(f"\n[EMOJI] FIX 322: FILTRO ACTIVADO - Bruce dice 'registrado' SIN tener dato")
                print(f"   Bruce iba a decir: \"{respuesta[:60]}...\"")
                print(f"   tiene_correo={tiene_correo}, tiene_whatsapp={tiene_whatsapp}")
                # Corregir a presentación
                respuesta = "Me comunico de parte de la marca NIOVAL, distribuimos productos de ferretería. ¿Se encontrará el encargado de compras?"
                filtro_aplicado = True
                print(f"   Respuesta corregida: \"{respuesta}\"")

        # ============================================================
        # FILTRO 26 (FIX 324): Cliente pide información por WhatsApp/correo
        # pero Bruce pregunta de nuevo por el encargado en lugar de pedir el dato
        # Ejemplo: "No está, pero podría mandarme la información por este [WhatsApp]"
        # ============================================================
        if not filtro_aplicado:
            # Detectar si cliente pide información
            cliente_pide_info = any(frase in contexto_cliente for frase in [
                'mandarme la información', 'mandarme la informacion',
                'enviarme la información', 'enviarme la informacion',
                'mándame la información', 'mandame la informacion',
                'me puede mandar', 'me puedes mandar',
                'envíame', 'enviame', 'mandarme la', 'enviarme el',
                'podría mandarme', 'podria mandarme',
                'me manda la información', 'me manda la informacion',
                'mándeme la', 'mandeme la', 'envíeme la', 'envieme la'
            ])

            # Detectar si cliente menciona WhatsApp o "por este número"
            cliente_menciona_medio = any(frase in contexto_cliente for frase in [
                'por whatsapp', 'por wasa', 'por este', 'por este número',
                'por este numero', 'a este número', 'a este numero',
                'este mismo', 'aquí mismo', 'aqui mismo', 'por correo'
            ])

            # Bruce pregunta por encargado en lugar de pedir el contacto
            bruce_pregunta_encargado = any(frase in respuesta_lower for frase in [
                'se encontrará el encargado', 'se encontrara el encargado',
                'está el encargado', 'esta el encargado',
                'se encuentra el encargado', 'encargado de compras',
                'encargada de compras'
            ])

            if (cliente_pide_info or cliente_menciona_medio) and bruce_pregunta_encargado:
                print(f"\n[PHONE] FIX 324: FILTRO ACTIVADO - Cliente PIDE INFO pero Bruce pregunta por encargado")
                print(f"   Cliente dijo: \"{contexto_cliente[:80]}...\"")
                print(f"   Bruce iba a preguntar por encargado: \"{respuesta[:60]}...\"")
                # Responder aceptando enviar la información
                respuesta = "Claro, con gusto. ¿Me confirma su número de WhatsApp para enviarle el catálogo?"
                filtro_aplicado = True
                print(f"   Respuesta corregida: \"{respuesta}\"")

        # ============================================================
        # FILTRO 27 (FIX 336): Cliente dice "a este número" o "sería este número"
        # Significa que debemos enviar al mismo número que estamos marcando
        # ============================================================
        if not filtro_aplicado:
            # FIX 347: Detectar si cliente indica usar el mismo número
            cliente_dice_este_numero = any(frase in contexto_cliente for frase in [
                'a este número nada más', 'a este numero nada mas',
                'sería a este número', 'seria a este numero',
                'sería este número', 'seria este numero',
                'a este número', 'a este numero',
                'por este número', 'por este numero',
                'este mismo número', 'este mismo numero',
                'al mismo número', 'al mismo numero',
                'a este nada más', 'a este nada mas',
                # FIX 347: Más variantes
                'a este número que marca', 'a este numero que marca',
                'al número que marca', 'al numero que marca',
                'este que marca', 'número que marca', 'numero que marca',
                'por este medio', 'a este medio',
                'mándamelo por este', 'mandamelo por este',
                'por aquí', 'por aqui', 'aquí mismo', 'aqui mismo',
                'a este whatsapp', 'por este whatsapp'
            ])

            # Bruce pide número O responde algo incoherente cuando ya le dijeron el número
            bruce_responde_mal = any(frase in respuesta_lower for frase in [
                'cuál es su número', 'cual es su numero',
                'me puede repetir', 'me puede proporcionar',
                'solo escuché', 'solo escuche',
                'dígitos', 'digitos',
                # FIX 347: Respuestas incoherentes (re-presentación)
                'me comunico de parte', 'mi nombre es bruce',
                'soy bruce de', 'le llamo de la marca',
                'se encontrará el encargado', 'se encontrara el encargado'
            ])

            if cliente_dice_este_numero and bruce_responde_mal:
                print(f"\n[EMOJI] FIX 336/347: FILTRO ACTIVADO - Cliente dice 'a este número' pero Bruce responde mal")
                print(f"   Cliente dijo: \"{contexto_cliente[:80]}...\"")
                print(f"   Bruce iba a decir: \"{respuesta[:60]}...\"")
                respuesta = "Perfecto, entonces le envío el catálogo a este mismo número por WhatsApp. Muchas gracias por su tiempo, que tenga excelente día."
                filtro_aplicado = True
                print(f"   Respuesta corregida: \"{respuesta}\"")

        # ============================================================
        # FILTRO 28 (FIX 345): Cliente ofrece correo pero Bruce responde incoherente
        # Ejemplo: "Te comparto un correo" → "Perfecto. ¿Hay algo más?"
        # Esto es INCORRECTO - Bruce debe pedir el correo
        # ============================================================
        if not filtro_aplicado:
            # FIX 359: Detectar si cliente ofrece dar correo (incluyendo preguntas)
            cliente_ofrece_correo = any(frase in contexto_cliente for frase in [
                'te comparto un correo', 'le comparto un correo',
                'te comparto el correo', 'le comparto el correo',
                'comparto un correo', 'comparto el correo',
                'te doy un correo', 'le doy un correo',
                'te doy el correo', 'le doy el correo',
                'te paso un correo', 'le paso un correo',
                'te paso el correo', 'le paso el correo',
                'si gusta para que envíe', 'si gustas para que envíe',
                'si gusta para que envie', 'si gustas para que envies',
                'para que envíe tu información', 'para que envíes tu información',
                'para que envie tu informacion', 'para que envies tu informacion',
                'para que nos envíe', 'para que nos envíes',
                'para que mande', 'para que mandes',
                # FIX 359: Cliente PREGUNTA si dar correo
                'doy un correo', 'doy el correo', 'doy correo',  # "¿te doy un correo?"
                'te digo a dónde', 'te digo a donde', 'le digo a dónde', 'le digo a donde',
                'whatsapp o correo', 'correo electrónico', 'correo electronico',
                'mandármela', 'mandarmela', 'mándamela', 'mandamela',
                'mándamelo', 'mandamelo', 'envíamelo', 'enviamelo'
            ])

            # Bruce responde algo incoherente en lugar de pedir el correo
            bruce_responde_incoherente = any(frase in respuesta_lower for frase in [
                'hay algo más', 'hay algo mas',
                'algo más en lo que', 'algo mas en lo que',
                'perfecto.', 'excelente.',
                'muchas gracias por su tiempo',
                'que tenga buen día', 'que tenga excelente día',
                'hasta luego',
                'ya tengo registrado', 'ya lo tengo registrado'
            ])

            if cliente_ofrece_correo and bruce_responde_incoherente:
                print(f"\n[EMAIL] FIX 345: FILTRO ACTIVADO - Cliente ofrece correo pero Bruce responde incoherente")
                print(f"   Cliente dijo: \"{contexto_cliente[:80]}...\"")
                print(f"   Bruce iba a decir: \"{respuesta[:60]}...\"")
                respuesta = "Claro, dígame su correo electrónico por favor."
                filtro_aplicado = True
                print(f"   Respuesta corregida: \"{respuesta}\"")

        # ============================================================
        # FILTRO 29 (FIX 353): Cliente pregunta sobre productos
        # Ejemplo: "¿De qué producto son?" → Bruce debe explicar qué vende
        # ============================================================
        if not filtro_aplicado:
            # Detectar si cliente pregunta sobre productos
            cliente_pregunta_productos = any(frase in contexto_cliente for frase in [
                'de qué producto', 'de que producto', 'qué producto', 'que producto',
                'de qué son', 'de que son', 'qué son', 'que son',
                'qué venden', 'que venden', 'qué manejan', 'que manejan',
                'qué productos', 'que productos', 'qué ofrecen', 'que ofrecen',
                'a qué se dedican', 'a que se dedican', 'de qué es', 'de que es',
                'qué es nioval', 'que es nioval', 'qué es eso', 'que es eso',
                'de qué marca', 'de que marca', 'qué marca', 'que marca',
                # FIX 361: "¿De qué marca está hablando?"
                'qué marca está hablando', 'que marca esta hablando',
                'de qué marca está', 'de que marca esta',
                'de qué marca me', 'de que marca me',
                'qué marca es', 'que marca es',
                'me dijiste', 'dijiste que', 'no escuché', 'no escuche',
                'repíteme', 'repiteme', 'qué era', 'que era'
            ])

            # FIX 361: Bruce no responde sobre productos (responde algo irrelevante)
            # O responde algo completamente incoherente como "¿me escucha?" o "¿hay algo más?"
            bruce_responde_incoherente = any(frase in respuesta_lower for frase in [
                'me escucha', 'me escuchas', 'hay algo más', 'hay algo mas',
                'algo más en lo que', 'algo mas en lo que', 'puedo ayudar',
                'ya lo tengo registrado', 'perfecto.', 'excelente.'
            ])
            bruce_no_responde_productos = bruce_responde_incoherente or not any(frase in respuesta_lower for frase in [
                'ferretería', 'ferreteria', 'herramienta', 'grifería', 'griferia',
                'candado', 'nioval', 'producto', 'catálogo', 'catalogo',
                'cinta', 'tapagoteras', 'distribuimos', 'manejamos'
            ])

            if cliente_pregunta_productos and bruce_no_responde_productos:
                print(f"\n[WRENCH] FIX 353: FILTRO ACTIVADO - Cliente pregunta productos pero Bruce no responde")
                print(f"   Cliente dijo: \"{contexto_cliente[:80]}...\"")
                print(f"   Bruce iba a decir: \"{respuesta[:60]}...\"")
                respuesta = "Claro, somos de la marca NIOVAL. Manejamos productos de ferretería como herramientas, grifería, candados, cinta tapagoteras y más. ¿Le gustaría recibir el catálogo?"
                filtro_aplicado = True
                print(f"   Respuesta corregida: \"{respuesta}\"")

        # ============================================================
        # FILTRO 30 (FIX 355): Cliente pide nombre y/o número de Bruce
        # Ejemplo: "¿Me puede dar su número telefónico para yo pasarle a Ricardo?"
        # Bruce debe dar su nombre y el teléfono de NIOVAL
        # ============================================================
        if not filtro_aplicado:
            # Detectar si cliente pide datos de contacto de Bruce
            cliente_pide_datos_bruce = any(frase in contexto_cliente for frase in [
                'deme su número', 'deme su numero', 'me da su número', 'me da su numero',
                'su número telefónico', 'su numero telefonico', 'su teléfono', 'su telefono',
                'número de usted', 'numero de usted', 'teléfono de usted', 'telefono de usted',
                'su nombre y su número', 'su nombre y su numero',
                'se identifique', 'identifíquese', 'identifiquese',
                'cómo se llama', 'como se llama', 'quién me habla', 'quien me habla',
                'para pasarle', 'para que se comunique', 'para comunicarle',
                'le paso su información', 'le paso su informacion',
                'nombre de usted', 'cuál es su nombre', 'cual es su nombre'
            ])

            # Bruce responde mal (placeholders, respuesta genérica, o no da el número)
            bruce_responde_mal_datos = any(frase in respuesta_lower for frase in [
                '[tu nombre]', '[tu número]', 'tu nombre', 'tu número',
                'le gustaría recibir', 'le gustaria recibir',
                'ya lo tengo registrado', 'catálogo', 'catalogo',
                'whatsapp o correo', 'correo electrónico'
            ]) or '662 415' not in respuesta

            # FIX 625A: BRUCE2059 - "te paso su teléfono" NO es pedir datos de Bruce
            # Es el cliente ofreciendo PASAR el teléfono del encargado
            cliente_ofrece_pasar_625a = any(p in contexto_cliente for p in [
                'te paso su', 'le paso su', 'paso su teléfono', 'paso su telefono',
                'paso su número', 'paso su numero', 'paso su cel',
                'te puedo pasar', 'le puedo pasar', 'puedo pasar su',
                'te doy su', 'le doy su', 'doy su teléfono', 'doy su telefono',
                'doy su número', 'doy su numero',
            ])
            if cliente_ofrece_pasar_625a:
                cliente_pide_datos_bruce = False
                print(f"\n[OK] FIX 625A: BRUCE2059 - Cliente OFRECE pasar teléfono del encargado, NO pide datos de Bruce")

            if cliente_pide_datos_bruce and bruce_responde_mal_datos:
                print(f"\n[EMOJI] FIX 355: FILTRO ACTIVADO - Cliente pide datos de Bruce")
                print(f"   Cliente dijo: \"{contexto_cliente[:80]}...\"")
                print(f"   Bruce iba a decir: \"{respuesta[:60]}...\"")
                respuesta = "Claro, mi nombre es Bruce de la marca NIOVAL. Nuestro teléfono es 662 415 1997, eso es: seis seis dos, cuatro uno cinco, uno nueve nueve siete. Con gusto puede pasarle mis datos al encargado."
                filtro_aplicado = True
                print(f"   Respuesta corregida: \"{respuesta}\"")

        # ============================================================
        # FILTRO 31 (FIX 362): Cliente dicta número de teléfono después de que
        # Bruce pidió el número del encargado - NO decir "Claro, espero"
        # Ejemplo: Bruce: "¿Me podría proporcionar el número del encargado?"
        #          Cliente: "4 4 2 2 15 23 0 1"
        #          Bruce: "Claro, espero" ← ERROR! Debe capturar el número
        # ============================================================
        if not filtro_aplicado:
            import re

            # Verificar si cliente está dando números (dígitos en el mensaje)
            digitos_en_cliente = len(re.findall(r'\d', contexto_cliente))

            # Patrones que indican que cliente está dictando un número de teléfono
            patron_dictando_numero = bool(re.search(r'\d\s*\d\s*\d', contexto_cliente))  # Al menos 3 dígitos

            # Bruce preguntó por número del encargado recientemente
            mensajes_bruce_recientes = [
                msg['content'].lower() for msg in self.conversation_history[-6:]
                if msg['role'] == 'assistant'
            ]
            bruce_pidio_numero_encargado = any(
                frase in ' '.join(mensajes_bruce_recientes)
                for frase in [
                    'número del encargado', 'numero del encargado',
                    'número directo', 'numero directo',
                    'contactarlo en ese horario', 'contactarla en ese horario',
                    'para llamarle', 'para contactarlo', 'para contactarla',
                    'me podría proporcionar el número', 'me podria proporcionar el numero'
                ]
            )

            # Bruce responde con "Claro, espero" u otra respuesta de espera
            bruce_dice_espero = any(frase in respuesta_lower for frase in [
                'claro, espero', 'claro espero', 'aquí espero', 'aqui espero',
                'perfecto, espero', 'perfecto espero'
            ])

            if digitos_en_cliente >= 6 and patron_dictando_numero and bruce_dice_espero:
                print(f"\n[EMOJI] FIX 362: FILTRO ACTIVADO - Cliente DICTA NÚMERO pero Bruce dice 'espero'")
                print(f"   Cliente dijo: \"{contexto_cliente[:80]}...\"")
                print(f"   Dígitos detectados: {digitos_en_cliente}")
                print(f"   Bruce iba a decir: \"{respuesta[:60]}...\"")
                # Agradecer y confirmar el número
                respuesta = "Perfecto, muchas gracias por el número. Le marco entonces en ese horario. Que tenga excelente día."
                filtro_aplicado = True
                print(f"   Respuesta corregida: \"{respuesta}\"")

        # ============================================================
        # FILTRO 32 (FIX 363): Reforzar detección de "ya lo tengo registrado"
        # Cuando Bruce NO tiene ningún dato pero dice que sí tiene
        # También detectar cuando cliente OFRECE dar correo/número
        # pero Bruce dice "ya lo tengo registrado" sin haberlo recibido
        # ============================================================
        if not filtro_aplicado:
            # Bruce dice que ya tiene registrado
            bruce_dice_registrado = any(frase in respuesta_lower for frase in [
                'ya lo tengo registrado', 'ya lo tengo anotado',
                'ya tengo registrado', 'ya tengo anotado',
                'le llegará el catálogo', 'le llegara el catalogo',
                'en las próximas horas', 'en las proximas horas'
            ])

            if bruce_dice_registrado:
                # Verificar si REALMENTE tenemos datos
                tiene_email_real = bool(self.lead_data.get("email"))
                tiene_whatsapp_real = bool(self.lead_data.get("whatsapp"))

                # Buscar en historial si cliente dio email con @
                historial_cliente = ' '.join([
                    msg['content'].lower() for msg in self.conversation_history
                    if msg['role'] == 'user'
                ])
                cliente_dio_email_real = '@' in historial_cliente or ('arroba' in historial_cliente and 'punto' in historial_cliente)

                # Buscar si cliente dio número de WhatsApp (10+ dígitos Y Bruce lo pidió)
                digitos_total = len(re.findall(r'\d', historial_cliente))
                mensajes_bruce_todos = [msg['content'].lower() for msg in self.conversation_history if msg['role'] == 'assistant']
                bruce_pidio_whatsapp = any('whatsapp' in msg or 'su número' in msg for msg in mensajes_bruce_todos)
                cliente_dio_whatsapp_real = bruce_pidio_whatsapp and digitos_total >= 10

                tiene_dato_confirmado = tiene_email_real or tiene_whatsapp_real or cliente_dio_email_real or cliente_dio_whatsapp_real

                # FIX 363/366: Detectar cuando cliente OFRECE dar dato pero aún no lo ha dado
                # FIX 366: Agregar "no sé si te pudiera dar un correo" y variantes
                cliente_ofrece_dar_dato = any(frase in contexto_cliente for frase in [
                    'si gusta mandárme', 'si gusta mandarme', 'si gusta mandarmelo',
                    'mándeme su', 'mandeme su', 'envíeme su', 'envieme su',
                    'yo le comparto', 'yo se lo comparto', 'yo le paso',
                    'mandármelo por correo', 'mandarmelo por correo',
                    'si gusta enviar', 'si desea enviar',
                    # FIX 366: Cliente ofrece dar correo
                    'te pudiera dar un correo', 'le pudiera dar un correo',
                    'te puedo dar un correo', 'le puedo dar un correo',
                    'darle un correo', 'darte un correo',
                    'si te doy un correo', 'si le doy un correo',
                    'te paso un correo', 'le paso un correo',
                    'te doy el correo', 'le doy el correo',
                    'si quiere le doy', 'si quieres te doy',
                    'no sé si te', 'no se si te', 'no sé si le', 'no se si le'
                ])

                # FIX 365/368: Detectar cuando cliente dice "sí" aceptando la oferta
                # pero Bruce dice "ya lo tengo" sin haber pedido el dato
                # FIX 368: Mejorar para detectar frases más largas como "Ajá. Sí, soy yo, dígame"
                ultimos_mensajes_cliente = [
                    msg['content'].lower().strip() for msg in self.conversation_history[-3:]
                    if msg['role'] == 'user'
                ]
                ultimo_cliente = ultimos_mensajes_cliente[-1] if ultimos_mensajes_cliente else ""

                # FIX 368: Patrones de aceptación - buscar DENTRO del mensaje, no solo al inicio
                patrones_acepta = [
                    'sí', 'si', 'claro', 'ok', 'órale', 'orale', 'ajá', 'aja',
                    'dígame', 'digame', 'adelante', 'mande'
                ]
                # FIX 370: Excluir "bueno" como patrón de aceptación si es solo "¿Bueno?" repetido
                # "¿Bueno? ¿Bueno?" indica que cliente NO escucha, NO es aceptación
                es_solo_bueno_repetido = bool(re.match(r'^[\s\?\¿bueno,\s]+$', ultimo_cliente.replace('?', '').replace('¿', '')))
                if not es_solo_bueno_repetido and 'bueno' in ultimo_cliente:
                    # Solo contar "bueno" si viene con algo más (ej: "sí bueno", "bueno, adelante")
                    if any(p in ultimo_cliente for p in ['sí bueno', 'si bueno', 'bueno adelante', 'bueno, sí']):
                        patrones_acepta.append('bueno')

                # Cliente acepta si contiene palabras de aceptación Y NO contiene email/número
                tiene_patron_acepta = any(p in ultimo_cliente for p in patrones_acepta)
                no_tiene_dato = '@' not in ultimo_cliente and 'arroba' not in ultimo_cliente
                pocos_digitos = len(re.findall(r'\d', ultimo_cliente)) < 7

                # FIX 370: Si cliente solo dice "¿Bueno?" NO es aceptación
                if es_solo_bueno_repetido:
                    tiene_patron_acepta = False

                # FIX 367: Detectar "soy yo" como indicador de que ES el encargado
                # pero aún así NO tiene dato de contacto
                cliente_dice_soy_yo = any(frase in ultimo_cliente for frase in [
                    'soy yo', 'yo soy', 'sí soy', 'si soy', 'aquí estoy', 'aqui estoy'
                ])

                cliente_solo_acepta = tiene_patron_acepta and no_tiene_dato and pocos_digitos

                # Verificar que Bruce acaba de preguntar por WhatsApp/correo
                ultimos_bruce = [
                    msg['content'].lower() for msg in self.conversation_history[-4:]
                    if msg['role'] == 'assistant'
                ]
                bruce_pregunto_medio = any(
                    'whatsapp o correo' in msg or 'correo electrónico' in msg or 'correo o whatsapp' in msg
                    for msg in ultimos_bruce
                )

                cliente_acepta_sin_dato = cliente_solo_acepta and bruce_pregunto_medio

                if not tiene_dato_confirmado or cliente_ofrece_dar_dato or cliente_acepta_sin_dato:
                    print(f"\n[EMOJI] FIX 363/365/366/367/368: FILTRO ACTIVADO - Bruce dice 'registrado' SIN DATO REAL")
                    print(f"   tiene_email_real={tiene_email_real}, tiene_whatsapp_real={tiene_whatsapp_real}")
                    print(f"   cliente_dio_email_real={cliente_dio_email_real}, cliente_dio_whatsapp_real={cliente_dio_whatsapp_real}")
                    print(f"   cliente_ofrece_dar_dato={cliente_ofrece_dar_dato}, cliente_acepta_sin_dato={cliente_acepta_sin_dato}")
                    print(f"   cliente_dice_soy_yo={cliente_dice_soy_yo}, ultimo_cliente='{ultimo_cliente[:50]}'")
                    print(f"   Bruce iba a decir: \"{respuesta[:60]}...\"")
                    # Pedir el dato correctamente
                    if 'correo' in contexto_cliente or 'email' in contexto_cliente:
                        respuesta = "Claro, con gusto. ¿Me puede proporcionar su correo electrónico?"
                    else:
                        respuesta = "Claro, con gusto. ¿Me confirma su número de WhatsApp para enviarle el catálogo?"
                    filtro_aplicado = True
                    print(f"   Respuesta corregida: \"{respuesta}\"")

        # ============================================================
        # FILTRO 32B (FIX 375): Cliente dice "mándenme la información a este número"
        # "Este número" = el número que Bruce marcó (está en self.lead_data["telefono"])
        # Bruce debe reconocer que YA TIENE el número
        # ============================================================
        if not filtro_aplicado:
            # Detectar "este número" como referencia al número actual
            patrones_este_numero = [
                r'este\s+n[uú]mero', r'ese\s+n[uú]mero',
                r'a\s+este\s+(?:n[uú]mero|whatsapp|tel[eé]fono)',
                r'este\s+(?:tel[eé]fono|whatsapp)',
                r'mand(?:ar|e|arlo).*este\s+n[uú]mero',
                r'env(?:iar|íe|iarlo).*este\s+n[uú]mero',
                r'(?:a|al)\s+este\s+(?:n[uú]mero|whatsapp)',
                r'aqu[ií]\s+(?:mismo|al\s+n[uú]mero)',
                r'mismo\s+n[uú]mero',
                # FIX 377: "es este mismo", "este mismo", "el mismo"
                r'es\s+este\s+mismo', r'este\s+mismo',
                r'el\s+mismo\s+(?:n[uú]mero)?', r'ese\s+mismo',
                r'este\s+(?:tel[eé]fono|n[uú]mero)?\s*mismo',
                r'es\s+el\s+mismo',
                # FIX 382: "sería este", "seria este" (condicional)
                r'ser[ií]a\s+este', r'ser[ií]a\s+el\s+mismo',
                r'ser[ií]a\s+ese', r'ser[ií]a\s+(?:este|ese)\s+n[uú]mero'
            ]

            cliente_dice_este_numero = any(re.search(p, contexto_cliente) for p in patrones_este_numero)

            # Detectar si Bruce está preguntando por WhatsApp/correo después de que cliente pidió info a "este número"
            # FIX 377: También detectar "ya lo tengo registrado" cuando NO debería
            bruce_pregunta_medio = any(frase in respuesta_lower for frase in [
                'whatsapp o correo', 'correo electrónico', 'correo o whatsapp',
                '¿le gustaría recibir', 'le gustaría recibir'
            ])

            # FIX 378: Detectar "ya lo tengo registrado" cuando cliente dijo "este mismo"
            bruce_dice_registrado_sin_confirmar = any(frase in respuesta_lower for frase in [
                'ya lo tengo registrado', 'ya lo tengo anotado',
                'le llegará el catálogo', 'le llegara el catalogo'
            ])

            if cliente_dice_este_numero and (bruce_pregunta_medio or bruce_dice_registrado_sin_confirmar):
                # Verificar si tenemos el número del cliente
                telefono_cliente = self.lead_data.get("telefono", "")
                if telefono_cliente:
                    print(f"\n[PHONE] FIX 375/377/378: FILTRO ACTIVADO - Cliente pide info a 'este número'")
                    print(f"   Cliente dijo: '{contexto_cliente[:80]}'")
                    print(f"   Número que Bruce marcó: {telefono_cliente}")
                    print(f"   Bruce iba a decir: '{respuesta[:60]}...'")

                    # FIX 378: GUARDAR el número como WhatsApp antes de confirmar
                    # Limpiar el número (quitar espacios, guiones, paréntesis)
                    telefono_limpio = re.sub(r'[^\d+]', '', telefono_cliente)

                    # Solo guardar si parece un número válido (10+ dígitos)
                    if len(re.findall(r'\d', telefono_limpio)) >= 10:
                        self.lead_data["whatsapp"] = telefono_limpio
                        print(f"   [OK] WhatsApp guardado: {telefono_limpio}")

                    # Confirmar que vamos a usar ese número como WhatsApp
                    ultimos_4_digitos = telefono_cliente[-4:]
                    respuesta = f"Perfecto, le envío el catálogo a este WhatsApp terminado en {ultimos_4_digitos}. Muchas gracias."
                    filtro_aplicado = True
                    print(f"   Respuesta corregida: '{respuesta}'")

        # ============================================================
        # FILTRO 32C (FIX 383): Cliente pide "marcar en otro momento" (reprogramar)
        # Bruce NO debe pedir WhatsApp, debe preguntar horario
        # ============================================================
        if not filtro_aplicado:
            ultimos_mensajes_cliente = [
                msg['content'].lower() for msg in self.conversation_history[-3:]
                if msg['role'] == 'user'
            ]

            if ultimos_mensajes_cliente:
                contexto_cliente = ' '.join(ultimos_mensajes_cliente)

                # Detectar solicitud de reprogramación
                cliente_pide_reprogramar = any(frase in contexto_cliente for frase in [
                    'marcar en otro momento', 'marca en otro momento',
                    'llame en otro momento', 'llama en otro momento',
                    'llamar en otro momento', 'llamar más tarde',
                    'marcar más tarde', 'marca más tarde',
                    'regrese más tarde', 'llame después',
                    'vuelva a llamar', 'vuelve a llamar',
                    'mejor en otro momento', 'en otro horario',
                    'si gustas marca', 'si gusta marcar',
                    'si gustas llama', 'si gusta llamar',
                    # FIX 695: "hablar" variantes
                    'si gustas habla', 'si gusta hablar', 'hablar luego'
                ])

                # Detectar si Bruce pide WhatsApp en lugar de horario
                bruce_pide_whatsapp = any(frase in respuesta_lower for frase in [
                    'cuál es su whatsapp', 'cual es su whatsapp',
                    'me confirma su whatsapp', 'me da su whatsapp',
                    'su número de whatsapp', 'me proporciona su whatsapp'
                ])

                if cliente_pide_reprogramar and bruce_pide_whatsapp:
                    print(f"\n[EMOJI] FIX 383: FILTRO ACTIVADO - Cliente pide reprogramar pero Bruce pide WhatsApp")
                    print(f"   Cliente dijo: '{contexto_cliente[:80]}...'")
                    print(f"   Bruce iba a decir: '{respuesta[:60]}...'")
                    respuesta = "Perfecto. ¿A qué hora sería mejor que llame de nuevo?"
                    filtro_aplicado = True
                    print(f"   Respuesta corregida: '{respuesta}'")

        # ============================================================
        # FILTRO 33 (FIX 364/367): Cliente dice "Ella habla" / "Él habla" / "Soy yo"
        # Esto indica que ESA persona ES la encargada/el encargado de compras
        # Bruce preguntó "¿Se encontrará el encargado?" y cliente dice "Ella habla"
        # = la persona en la línea ES la encargada
        # FIX 367: Agregar "soy yo, dígame" como indicador de encargado
        # FIX 508: BRUCE1525 - Solo aplicar si cliente indica en el ÚLTIMO mensaje, no todo el historial
        # ============================================================
        if not filtro_aplicado:
            # Detectar si cliente indica que es el/la encargado/a
            patrones_ella_el_habla = [
                r'ella\s+habla', r'él\s+habla', r'el\s+habla',
                r'yo\s+hablo', r'aquí\s+habla', r'aqui\s+habla',
                r'con\s+ella\s+(?:habla|está)', r'con\s+él\s+(?:habla|está)',
                r'soy\s+(?:yo|ella|él)', r'le\s+habla',
                r'hablas?\s+con\s+(?:ella|él|el)',
                r'es\s+una\s+servidora', r'servidor', r'servidora',
                # Patrones mexicanos comunes
                r'aquí\s+(?:andamos|estamos)', r'aqui\s+(?:andamos|estamos)',
                r'mero\s+(?:yo|ella|él)', r'precisamente\s+(?:yo|ella|él)',
                # FIX 367: "soy yo" con variantes
                r's[ií],?\s*soy\s+yo', r'soy\s+yo,?\s*d[ií]game',
                r'yo\s+soy,?\s*d[ií]game', r's[ií],?\s*adelante'
            ]

            # FIX 508: Obtener SOLO el último mensaje del cliente, no todo el historial
            # BRUCE1525: Cliente dijo "con ella habla" ANTES, luego preguntó "¿qué productos manejas?"
            # El filtro estaba usando contexto_cliente (historial completo) y detectaba el viejo mensaje
            ultimos_mensajes_cliente_fix508 = [
                msg['content'].lower() for msg in self.conversation_history[-2:]
                if msg['role'] == 'user'
            ]
            ultimo_mensaje_cliente_fix508 = ultimos_mensajes_cliente_fix508[-1] if ultimos_mensajes_cliente_fix508 else ""

            # Solo detectar si el cliente indica que es encargado en el ÚLTIMO mensaje
            cliente_indica_es_encargado = any(re.search(p, ultimo_mensaje_cliente_fix508) for p in patrones_ella_el_habla)

            # Bruce preguntó por encargado recientemente
            mensajes_bruce_recientes = [
                msg['content'].lower() for msg in self.conversation_history[-4:]
                if msg['role'] == 'assistant'
            ]
            bruce_pregunto_encargado = any(
                'encargado' in msg or 'encargada' in msg
                for msg in mensajes_bruce_recientes
            )

            # Bruce responde algo que ignora que el cliente dijo que ES el encargado
            bruce_ignora = any(frase in respuesta_lower for frase in [
                '¿se encontrará el encargado', 'se encontrara el encargado',
                'se encuentra el encargado', 'encargado de compras',
                'me escucha', 'me escuchas', 'estamos ubicados'
            ])

            if cliente_indica_es_encargado and (bruce_pregunto_encargado or bruce_ignora):
                print(f"\n[EMOJI]‍[EMOJI] FIX 364: FILTRO ACTIVADO - Cliente dice que ES el/la encargado/a")
                print(f"   Cliente dijo: \"{contexto_cliente[:80]}...\"")
                print(f"   Bruce iba a decir: \"{respuesta[:60]}...\"")
                # Continuar con la oferta del catálogo
                respuesta = "Perfecto, mucho gusto. ¿Le gustaría recibir nuestro catálogo de productos por WhatsApp o correo electrónico?"
                filtro_aplicado = True
                print(f"   Respuesta corregida: \"{respuesta}\"")

        # ============================================================
        # FILTRO FINAL (FIX 394): Eliminar "Perfecto" inapropiado
        # Bruce dice "Perfecto" cuando cliente hace pregunta o NO confirmó nada
        # ============================================================
        if not filtro_aplicado and respuesta.lower().startswith('perfecto'):
            # Obtener último mensaje del cliente
            ultimos_3_cliente = [
                msg['content'].lower() for msg in self.conversation_history[-3:]
                if msg['role'] == 'user'
            ]

            if ultimos_3_cliente:
                ultimo_msg_cliente = ultimos_3_cliente[-1]

                # Cliente hizo PREGUNTA (termina en ?)
                cliente_hizo_pregunta = '?' in ultimo_msg_cliente

                # Cliente NO confirmó nada
                cliente_no_confirmo = not any(conf in ultimo_msg_cliente for conf in [
                    'sí', 'si', 'claro', 'adelante', 'dale', 'ok', 'okay',
                    'bueno', 'sale', 'está bien', 'esta bien', 'por favor'
                ])

                # Cliente rechazó o dijo "No"
                cliente_rechazo = any(neg in ultimo_msg_cliente for neg in [
                    'no', 'no está', 'no esta', 'no se encuentra', 'no gracias'
                ])

                # Si cliente hizo pregunta O NO confirmó O rechazó → NO usar "Perfecto"
                if cliente_hizo_pregunta or cliente_no_confirmo or cliente_rechazo:
                    print(f"\n[EMOJI] FIX 394: 'Perfecto' inapropiado detectado")
                    print(f"   Cliente dijo: '{ultimo_msg_cliente[:60]}...'")
                    print(f"   Razón: {'Pregunta' if cliente_hizo_pregunta else 'No confirmó' if cliente_no_confirmo else 'Rechazo'}")

                    # Reemplazar "Perfecto" con "Claro" o eliminarlo
                    if respuesta.lower().startswith('perfecto.'):
                        respuesta = respuesta[9:].strip()  # Eliminar "Perfecto."
                        respuesta = respuesta[0].upper() + respuesta[1:] if respuesta else respuesta
                        print(f"   Respuesta corregida: '{respuesta[:60]}...'")
                        filtro_aplicado = True
                    elif respuesta.lower().startswith('perfecto,'):
                        respuesta = "Claro," + respuesta[9:]
                        print(f"   Respuesta corregida: '{respuesta[:60]}...'")
                        filtro_aplicado = True

        if filtro_aplicado:
            print(f"[OK] FIX 226-394: Filtro post-GPT aplicado exitosamente")

        # FIX 467: BRUCE1404 - Fallback cuando GPT devuelve respuesta vacía
        # Esto ocurre a veces con transcripciones duplicadas/erróneas que confunden a GPT
        if not respuesta or len(respuesta.strip()) == 0:
            print(f"\n[WARN] FIX 467: GPT devolvió respuesta VACÍA - generando fallback")
            print(f"   Estado actual: {self.estado_conversacion}")

            # Generar respuesta según el estado de la conversación
            if self.estado_conversacion == EstadoConversacion.ENCARGADO_NO_ESTA:
                respuesta = "Entiendo. ¿Me podría proporcionar un número de WhatsApp o correo para enviarle información?"
                print(f"   FIX 467: Estado ENCARGADO_NO_ESTA - pidiendo contacto")
            elif self.estado_conversacion == EstadoConversacion.PIDIENDO_WHATSAPP:
                respuesta = "¿Me puede repetir el número, por favor?"
                print(f"   FIX 467: Estado PIDIENDO_WHATSAPP - solicitando repetición")
            elif self.estado_conversacion == EstadoConversacion.ESPERANDO_TRANSFERENCIA:
                # FIX 574: NO repetir "Claro, espero." - ya se dijo en FIX 470
                # Devolver vacío para mantener silencio de espera (FIX 498 manejará)
                respuesta = ""
                print(f"   FIX 574: Estado ESPERANDO_TRANSFERENCIA - silencio (ya se dijo 'Claro, espero')")
            else:
                respuesta = "Sí, dígame."
                print(f"   FIX 467: Estado genérico - respuesta neutral")

            print(f"   Respuesta fallback: \"{respuesta}\"")

        # ================================================================
        # FIX 522 BRUCE1659: Detectar promesa de catálogo y evitar repetir
        # ================================================================
        respuesta_lower = respuesta.lower() if respuesta else ""

        # Detectar si Bruce promete enviar el catálogo
        if any(frase in respuesta_lower for frase in [
            'le envío el catálogo', 'le envio el catalogo',
            'envío el catálogo', 'envio el catalogo',
            'le mando el catálogo', 'le mando el catalogo'
        ]):
            if not self.catalogo_prometido:
                self.catalogo_prometido = True
                print(f"   FIX 522: Catálogo PROMETIDO - flag activado")

        # FIX 526 BRUCE1677: Detectar si Bruce pregunta por hora de callback
        # FIX 533 BRUCE1665: Expandir patrones - "hora me" además de "hora le"
        if any(frase in respuesta_lower for frase in [
            '¿a qué hora', '¿a que hora', 'qué hora sería', 'que hora seria',
            '¿qué hora le', '¿que hora le', 'a qué hora le', 'a que hora le',
            # FIX 533: Agregar variantes con "me" en lugar de "le"
            '¿qué hora me', '¿que hora me', 'a qué hora me', 'a que hora me',
            'qué hora puedo', 'que hora puedo', 'a qué hora puedo', 'a que hora puedo',
            # FIX 533: Más variantes de preguntas por horario
            '¿cuándo puedo', '¿cuando puedo', 'cuándo le', 'cuando le',
            'horario para', 'mejor hora', 'mejor horario',
            '¿a qué hora regresa', '¿a que hora regresa', '¿a qué hora llega', '¿a que hora llega'
        ]):
            self.esperando_hora_callback = True
            print(f"   FIX 526/533: Bruce pregunta por HORA - esperando_hora_callback=True")
        elif self.esperando_hora_callback:
            # Si Bruce dice algo diferente, resetear el flag
            self.esperando_hora_callback = False
            print(f"   FIX 526: Bruce no pregunta por hora - resetear flag")

        # Si ya se prometió el catálogo y Bruce vuelve a ofrecer, convertir en despedida
        if self.catalogo_prometido:
            # Detectar si está volviendo a ofrecer catálogo
            vuelve_a_ofrecer = any(frase in respuesta_lower for frase in [
                '¿le gustaría recibirlo', '¿le gustaria recibirlo',
                '¿le envío el catálogo', '¿le envio el catalogo',
                '¿por whatsapp o correo', '¿whatsapp o correo'
            ])
            if vuelve_a_ofrecer:
                print(f"   FIX 522: Ya se prometió catálogo - evitando repetir oferta")
                respuesta = "Perfecto, entonces le envío el catálogo. Muchas gracias por su tiempo, que tenga excelente día."

        # ============================================================
        # FIX 699: MEMORY LAYER VALIDATION
        # Validar respuesta GPT contra hechos conocidos de la conversación
        # Si contradice hechos → usar alternativa generada por Memory Layer
        # ============================================================
        try:
            if self.memory:
                ok_699, alternativa_699 = self.memory.validate_response(respuesta)
                if not ok_699 and alternativa_699:
                    print(f"\n[FIX 699] MEMORY LAYER: Respuesta contradice hechos conocidos")
                    print(f"  Respuesta original: '{respuesta[:60]}...'")
                    print(f"  Hechos: {self.memory.get_summary()}")
                    print(f"  Override: '{alternativa_699[:60]}...'")
                    respuesta = alternativa_699
                    self.metrics.log_filtro_post_gpt("FIX_699", "MEMORY_LAYER_OVERRIDE")
        except Exception as e_mem:
            print(f"   [WARN] FIX 699: Memory validate_response error: {e_mem}")

        # ============================================================
        # FIX 693: POST-FILTER PITCH REPETIDO SEMÁNTICO
        # BRUCE2234, BRUCE2238: GPT reformula pitch en otras palabras
        # FIX 679 (>=85% similar) no lo detecta si wording es diferente
        # Si "nioval" ya fue mencionado por Bruce Y respuesta actual
        # también tiene "nioval" + palabras de pitch → strip pitch, keep question
        # ============================================================
        palabras_pitch_693 = ['productos', 'ferretero', 'ferretería', 'ferreteria',
                              'catálogo', 'catalogo', 'distribuidor', 'marca nioval',
                              'línea', 'linea', 'brindar informacion', 'ofrecer informacion',
                              'brindar información', 'ofrecer información']
        ya_presento_693 = any('nioval' in m.get('content', '').lower()
                              for m in self.conversation_history if m.get('role') == 'assistant')
        # FIX 815: Expandir detección de pitch repetido
        # FIX 693 original: solo si 'nioval' en respuesta actual → pitch reformulado sin 'nioval' escapaba
        # FIX 815: También detectar si ya hizo pitch Y respuesta tiene 2+ palabras de pitch (sin necesitar 'nioval')
        _ya_hizo_pitch_815 = ya_presento_693 or any(
            sum(1 for p in palabras_pitch_693 if p in m.get('content', '').lower()) >= 2
            for m in self.conversation_history if m.get('role') == 'assistant'
        )
        _resp_tiene_nioval_815 = 'nioval' in respuesta.lower()
        # Palabras FUERTES de pitch (excluyendo catálogo/catalogo que es normal en ofertas)
        _palabras_pitch_fuerte_815 = ['distribuidor', 'marca nioval', 'brindar informacion',
                                       'brindar información', 'ofrecer informacion', 'ofrecer información',
                                       'línea', 'linea']
        _pitch_fuerte_815 = sum(1 for p in _palabras_pitch_fuerte_815 if p in respuesta.lower())
        _pitch_total_815 = sum(1 for p in palabras_pitch_693 if p in respuesta.lower())
        # Trigger: (ya presentó nioval + respuesta tiene nioval + pitch) → original FIX 693
        # OR (ya hizo pitch + respuesta tiene 3+ pitch keywords incluyendo al menos 1 fuerte)
        _trigger_815 = (ya_presento_693 and _resp_tiene_nioval_815 and _pitch_total_815 >= 1) or \
                        (_ya_hizo_pitch_815 and _pitch_total_815 >= 3 and _pitch_fuerte_815 >= 1 and len(respuesta) > 30)
        if _trigger_815:
                print(f"\n[FIX 693] PITCH REPETIDO SEMÁNTICO detectado (NIOVAL ya presentado)")
                print(f"  Respuesta: '{respuesta[:80]}...'")
                # Generar alternativa contextual sin repetir pitch
                if getattr(self, 'encargado_disponible', None) == False or (
                    any('no esta' in m.get('content', '').lower() or 'no está' in m.get('content', '').lower() or 'no se encuentra' in m.get('content', '').lower()
                        for m in self.conversation_history if m.get('role') == 'user')):
                    respuesta = "¿Me podría proporcionar un WhatsApp o correo para enviarle el catálogo?"
                elif getattr(self, 'encargado_confirmado', False):
                    respuesta = "¿Me podría proporcionar un WhatsApp o correo para enviarle el catálogo?"
                elif any('encargad' in m.get('content', '').lower()
                         for m in self.conversation_history if m.get('role') == 'assistant'):
                    respuesta = "¿Me podría proporcionar un WhatsApp o correo para enviarle la información?"
                else:
                    respuesta = "¿Se encontrará el encargado o encargada de compras?"
                print(f"  Override: '{respuesta}'")
                self.metrics.log_filtro_post_gpt("FIX_693", "PITCH_REPETIDO_SEMANTICO")

        # ============================================================
        # FIX 697: GPT CONTEXT TRACKING (BRUCE2252)
        # Detectar cuando cliente ya proporcionó información clave que GPT ignora
        # Caso 1: "mismo número" → NO pedir WhatsApp/número del encargado de nuevo
        # Caso 2: "no quiero dejar [dato]" → NO pedir ese dato
        # ============================================================
        ultimos_3_cliente = [m.get('content', '').lower() for m in self.conversation_history
                             if m.get('role') == 'user'][-3:]
        contexto_cliente_697 = ' '.join(ultimos_3_cliente)

        # FIX 697A: Cliente dijo "mismo número" → NO pedir WhatsApp/número encargado
        if any(frase in contexto_cliente_697 for frase in [
            'mismo numero', 'mismo número', 'este mismo', 'es el mismo',
            'ese mismo', 'es este', 'es ese'
        ]):
            pide_contacto_697a = any(frase in respuesta_lower for frase in [
                'whatsapp del encargado', 'whatsapp de la encargada',
                'numero del encargado', 'número del encargado',
                'numero de la encargada', 'número de la encargada',
                'numero directo', 'número directo', 'contacto del encargado'
            ])
            if pide_contacto_697a:
                print(f"\n[FIX 697A] Cliente dijo 'mismo número' - NO pedir contacto encargado")
                print(f"  Contexto: '{contexto_cliente_697[-80:]}'")
                print(f"  Respuesta original: '{respuesta[:60]}...'")
                # Override: ofrecer enviar catálogo al número actual
                respuesta = "Perfecto, entonces le envío el catálogo a este número. ¿Me podría confirmar el nombre del encargado?"
                print(f"  Override: '{respuesta}'")
                self.metrics.log_filtro_post_gpt("FIX_697A", "MISMO_NUMERO_IGNORADO")

        # FIX 697B: Cliente dijo "no quiero dejar [dato]" → NO pedir ese dato
        if any(frase in contexto_cliente_697 for frase in [
            'no quiero dejar', 'no te quiero dejar', 'no le quiero dejar',
            'no puedo dar', 'no puedo dejar', 'no puedo proporcionar'
        ]):
            pide_dato_697b = any(frase in respuesta_lower for frase in [
                'tiene donde anotar', 'tiene dónde anotar', 'anote', 'apunte',
                'me da su', 'me podría dar', 'me proporcion'
            ])
            if pide_dato_697b:
                print(f"\n[FIX 697B] Cliente rechazó dar dato - NO insistir")
                print(f"  Contexto: '{contexto_cliente_697[-80:]}'")
                print(f"  Respuesta original: '{respuesta[:60]}...'")
                # Override: cerrar conversación amablemente
                respuesta = "Entiendo, no se preocupe. Muchas gracias por su tiempo, que tenga excelente día."
                print(f"  Override: '{respuesta}'")
                self.metrics.log_filtro_post_gpt("FIX_697B", "RECHAZO_DATO_IGNORADO")

        # ============================================================
        # FIX 679 + FASE 1.3: CIRCUIT BREAKER ANTI-LOOP
        # Si Bruce ya dijo algo muy similar (>=85%), generar alternativa
        # FASE 1.3: Track count - 2da repetición = cierre cortés con catálogo
        # ============================================================
        import re as re_679
        import unicodedata as ud_679
        respuesta_norm_679 = ud_679.normalize('NFKD', respuesta.lower()).encode('ascii', 'ignore').decode('ascii')
        respuesta_norm_679 = re_679.sub(r'[^\w\s]', '', respuesta_norm_679).strip()
        # Solo verificar si respuesta tiene contenido sustancial (>25 chars normalizados)
        if len(respuesta_norm_679) > 25:
            respuestas_previas_679 = [m.get('content', '') for m in self.conversation_history if m.get('role') == 'assistant']
            _dup_count_751 = 0  # FASE 1.3: Contar cuántas veces ya se dijo algo similar
            for prev in respuestas_previas_679:
                prev_norm = ud_679.normalize('NFKD', prev.lower()).encode('ascii', 'ignore').decode('ascii')
                prev_norm = re_679.sub(r'[^\w\s]', '', prev_norm).strip()
                if len(prev_norm) > 25:
                    from difflib import SequenceMatcher as SM_679
                    ratio_679 = SM_679(None, respuesta_norm_679, prev_norm).ratio()
                    if ratio_679 >= 0.85:
                        _dup_count_751 += 1
            if _dup_count_751 >= 2:
                # FASE 1.3: 3ra repetición → cierre cortés definitivo
                print(f"\n[FASE 1.3] CIRCUIT BREAKER: Respuesta repetida {_dup_count_751 + 1}x")
                print(f"  Respuesta: '{respuesta[:60]}...'")
                respuesta = "Le envío la información por WhatsApp. Muchas gracias por su tiempo, que tenga excelente día."
                print(f"  Override CIERRE: '{respuesta}'")
            elif _dup_count_751 == 1:
                print(f"\n[FIX 679] DUPLICADO DETECTADO (2da vez)")
                print(f"  Actual: '{respuesta[:60]}...'")
                # Generar alternativa contextual
                if 'encargado' in respuesta.lower():
                    respuesta = "¿Me podría proporcionar un WhatsApp o correo para enviarle el catálogo?"
                elif 'nioval' in respuesta.lower():
                    respuesta = "¿Se encontrará el encargado o encargada de compras?"
                elif 'whatsapp' in respuesta.lower():
                    respuesta = "¿Prefiere que le envíe la información por correo electrónico?"
                elif 'catálogo' in respuesta.lower() or 'catalogo' in respuesta.lower():
                    respuesta = "Muchas gracias por su tiempo. Que tenga excelente día."
                else:
                    respuesta = "Disculpe, ¿me podría indicar cómo le puedo apoyar?"
                print(f"  Override: '{respuesta}'")

        # ============================================================
        # FIX 814: LOOP SHORT-STRING PROTECTION
        # FIX 679 solo protege strings >25 chars (similarity-based)
        # Frases cortas como "Claro, espero" (14 chars) escapan y se repiten 6x+
        # FIX 814: Exact match para strings 10-25 chars normalizados
        # ============================================================
        if 10 <= len(respuesta_norm_679) <= 25:
            _dup_short_814 = 0
            _previas_814 = [m.get('content', '') for m in self.conversation_history if m.get('role') == 'assistant']
            for prev in _previas_814:
                prev_norm_814 = ud_679.normalize('NFKD', prev.lower()).encode('ascii', 'ignore').decode('ascii')
                prev_norm_814 = re_679.sub(r'[^\w\s]', '', prev_norm_814).strip()
                if respuesta_norm_679 == prev_norm_814:
                    _dup_short_814 += 1
            if _dup_short_814 >= 2:
                print(f"\n[FIX 814] LOOP SHORT: Frase corta repetida {_dup_short_814 + 1}x: '{respuesta[:40]}'")
                respuesta = "Le envío la información por WhatsApp. Muchas gracias por su tiempo, que tenga excelente día."
                print(f"  Override CIERRE: '{respuesta}'")
            elif _dup_short_814 == 1:
                print(f"\n[FIX 814] LOOP SHORT: Frase corta repetida 2x: '{respuesta[:40]}'")
                if 'espero' in respuesta_norm_679 or 'momento' in respuesta_norm_679:
                    respuesta = "¿Me podría proporcionar un WhatsApp o correo para enviarle el catálogo mientras tanto?"
                elif 'encargado' in respuesta_norm_679:
                    respuesta = "¿Me podría dar un WhatsApp donde le envíe información?"
                else:
                    respuesta = "¿Me podría indicar cómo le puedo apoyar?"
                print(f"  Override: '{respuesta}'")

        # ============================================================
        # FIX 684: POST-FILTER ANTI-PROBLEMAS-TECNICOS (CTN-002)
        # Si GPT genera respuesta que menciona problemas técnicos/conexión,
        # reemplazar con versión sin excusa técnica
        # ============================================================
        respuesta_lower_684 = respuesta.lower()
        patrones_tecnicos_684 = [
            'problemas de conexión', 'problemas de conexion',
            'problema con la línea', 'problema con la linea',
            'problemas técnicos', 'problemas tecnicos',
            'hay interferencia', 'problemas de comunicación',
            'problemas de comunicacion', 'problemas de audio',
            'problemas con el audio', 'fallas técnicas',
            'fallas tecnicas', 'error técnico', 'error tecnico',
        ]
        if any(p in respuesta_lower_684 for p in patrones_tecnicos_684):
            print(f"\n[FIX 684] CTN-002: GPT mencionó problemas técnicos")
            print(f"  Bloqueado: '{respuesta[:80]}...'")
            # Reemplazar con versión sin excusa técnica
            if 'llamar' in respuesta_lower_684 or 'marco' in respuesta_lower_684 or 'llamo' in respuesta_lower_684:
                respuesta = "Disculpe, no le estoy escuchando bien. ¿Prefiere que le llame en otro momento?"
            elif 'whatsapp' in respuesta_lower_684 or 'catálogo' in respuesta_lower_684:
                respuesta = "¿Le puedo enviar el catálogo por WhatsApp para que lo revise con calma?"
            else:
                respuesta = "Disculpe, no le escuché bien. ¿Me puede repetir?"
            print(f"  Override FIX 684: '{respuesta}'")

        return respuesta

    def iniciar_conversacion(self):
        """Inicia la conversación con el mensaje de apertura"""

        # Agregar contexto de información previa del cliente
        contexto_previo = self._generar_contexto_cliente()
        if contexto_previo:
            self.conversation_history.append({
                "role": "system",
                "content": contexto_previo
            })

        # Detectar si el contexto indica que este número ES del encargado de compras
        es_encargado_confirmado = False
        if self.contacto_info:
            contexto_reprog = self.contacto_info.get('contexto_reprogramacion', '').lower()
            referencia = self.contacto_info.get('referencia', '').lower()

            # Buscar palabras clave que indiquen que este número es del encargado
            keywords_encargado = ['encargado', 'dio número', 'dio numero', 'contacto del encargado',
                                  'número del encargado', 'numero del encargado', 'referencia']

            if any(keyword in contexto_reprog for keyword in keywords_encargado):
                es_encargado_confirmado = True
            if any(keyword in referencia for keyword in keywords_encargado):
                es_encargado_confirmado = True

        # FIX 91/107/108/111/112: Saludo dividido en 2 partes para no saturar
        # Primera parte: Solo "Hola, buen dia" para captar atención y obtener saludo
        mensaje_inicial = "Hola, buen dia"

        self.conversation_history.append({
            "role": "assistant",
            "content": mensaje_inicial
        })

        return mensaje_inicial

    def _generar_contexto_cliente(self) -> str:
        """
        Genera un mensaje de contexto con información previa del cliente

        Returns:
            String con información del cliente que el agente ya conoce
        """
        if not self.contacto_info:
            return ""

        contexto_partes = ["[INFORMACIÓN PREVIA DEL CLIENTE - NO PREGUNTES ESTO]"]

        # Nombre del negocio (siempre lo tenemos - columna B)
        if self.contacto_info.get('nombre_negocio'):
            contexto_partes.append(f"- Nombre del negocio: {self.contacto_info['nombre_negocio']}")

        # Ubicación (columna C)
        if self.contacto_info.get('ciudad'):
            contexto_partes.append(f"- Ciudad: {self.contacto_info['ciudad']}")

        # Categoría (columna D)
        if self.contacto_info.get('categoria'):
            contexto_partes.append(f"- Tipo de negocio: {self.contacto_info['categoria']}")

        # Domicilio completo (columna H)
        if self.contacto_info.get('domicilio'):
            contexto_partes.append(f"- Dirección: {self.contacto_info['domicilio']}")

        # Horario (columna M)
        if self.contacto_info.get('horario'):
            contexto_partes.append(f"- Horario: {self.contacto_info['horario']}")

        # Info de Google Maps (columnas I, J, K)
        if self.contacto_info.get('puntuacion'):
            contexto_partes.append(f"- Puntuación Google Maps: {self.contacto_info['puntuacion']} estrellas")

        if self.contacto_info.get('resenas'):
            contexto_partes.append(f"- Número de reseñas: {self.contacto_info['resenas']}")

        if self.contacto_info.get('maps'):
            contexto_partes.append(f"- Nombre en Google Maps: {self.contacto_info['maps']}")

        # Estatus previo (columna N)
        if self.contacto_info.get('estatus'):
            contexto_partes.append(f"- Estatus previo: {self.contacto_info['estatus']}")

        # REFERENCIA - Si alguien lo refirió (columna U)
        if self.contacto_info.get('referencia'):
            contexto_partes.append(f"\n[EMOJI] IMPORTANTE - REFERENCIA:")
            contexto_partes.append(f"- {self.contacto_info['referencia']}")
            contexto_partes.append(f"- Usa esta información en tu SALUDO INICIAL para generar confianza")
            contexto_partes.append(f"- Ejemplo: 'Hola, mi nombre es Bruce W. Me pasó su contacto [NOMBRE DEL REFERIDOR] de [EMPRESA]. Él me comentó que usted...'")

        # CONTEXTO DE REPROGRAMACIÓN - Si hubo llamadas previas (columna W)
        if self.contacto_info.get('contexto_reprogramacion'):
            contexto_partes.append(f"\n[EMOJI] LLAMADA REPROGRAMADA:")
            contexto_partes.append(f"- {self.contacto_info['contexto_reprogramacion']}")
            contexto_partes.append(f"- Menciona que ya habían hablado antes y retomas la conversación")
            contexto_partes.append(f"- Ejemplo: 'Hola, qué tal. Como le había comentado la vez pasada, me comunico nuevamente...'")

            # Si el contexto indica que este número ES del encargado, agregar advertencia CRÍTICA
            contexto_lower = self.contacto_info['contexto_reprogramacion'].lower()
            if any(keyword in contexto_lower for keyword in ['encargado', 'dio número', 'dio numero', 'contacto del']):
                contexto_partes.append(f"\n[WARN] CRÍTICO: Este número FUE PROPORCIONADO como el del ENCARGADO DE COMPRAS")
                contexto_partes.append(f"- NO preguntes 'se encuentra el encargado' - YA ESTÁS HABLANDO CON ÉL")
                contexto_partes.append(f"- Saluda directamente y pide su nombre: '¿Con quién tengo el gusto?'")

        if len(contexto_partes) > 1:  # Más que solo el header
            contexto_partes.append("\n[EMOJI] Recuerda: NO preguntes nada de esta información, ya la tienes.")
            return "\n".join(contexto_partes)

        return ""

    # [EMOJI]
    # FIX 491: SISTEMA DE OPTIMIZACIÓN DE LATENCIA (Cache + Patrones + Tokens Dinámicos)
    # [EMOJI]

    def _detectar_patron_simple_optimizado(self, texto_cliente: str):
        """
        FIX 491: Detecta patrones simples que NO requieren GPT.
        Latencia: 0.05s (100x más rápido que GPT de 3.5s)

        Returns:
            dict con {tipo, respuesta, accion, dato} si detecta patrón, None si no
        """
        import re
        texto_lower = texto_cliente.lower().strip()
        # FIX 631: Normalizar acentos para matching robusto
        # STT (Deepgram fallback) puede enviar texto SIN acentos ("espereme" vs "espéreme")
        # Esto asegura que patrones matcheen independientemente de si STT acentúa o no
        # NOTA: ñ NO se toca - es letra fundamental del español, no acento
        texto_lower = texto_lower.replace('á','a').replace('é','e').replace('í','i').replace('ó','o').replace('ú','u').replace('ü','u')

        # FIX 701: Pre-clasificación con Intent Classifier (solo logging, no override)
        try:
            if self.classifier:
                intent_result_701 = self.classifier.classify(texto_lower)
                if intent_result_701:
                    print(f"   [INTENT] FIX 701: {intent_result_701.category.value} "
                          f"(conf={intent_result_701.confidence:.2f}, "
                          f"pattern='{intent_result_701.pattern}', "
                          f"method={intent_result_701.method})")
        except Exception as e_ic:
            print(f"   [WARN] FIX 701: Intent Classifier error: {e_ic}")

        # FIX 579: Connector check universal - si texto termina en conector, cliente no terminó
        # No hacer fast-match, dejar que GPT espere frase completa
        conectores_579 = [' y', ' o', ' pero', ' que', ' con', ' para', ' por', ' de',
            ' en', ' a', ' como', ' cuando', ',', '...', ' si', ' pues', ' no sé si',
            ' no se si', ' si es que', ' aunque']
        if any(texto_lower.endswith(c) for c in conectores_579):
            print(f"   FIX 579: Texto termina en conector ('{texto_lower[-10:]}') - dejando a GPT")
            return None

        # ================================================================
        # FIX 776: BRUCE2446 - Post-farewell: Si Bruce YA se despidió y cliente
        # dice "¿Aló?/¿Bueno?/Hello?" → repetir despedida breve, NO "me puede repetir"
        # ================================================================
        if len(self.conversation_history) >= 2:
            _ultimo_bruce_776 = ''
            for _m776 in reversed(self.conversation_history):
                if _m776['role'] == 'assistant':
                    _ultimo_bruce_776 = _m776['content'].lower()
                    break
            _bruce_ya_despidio_776 = any(p in _ultimo_bruce_776 for p in [
                'que tenga buen dia', 'que tenga excelente dia', 'que tenga buena tarde',
                'que tenga excelente tarde', 'gracias por su tiempo', 'hasta luego',
                'que le vaya bien', 'que este bien', 'disculpe la molestia',
                'buen dia', 'buena tarde', 'fue un placer'
            ])
            _cliente_post_farewell_776 = any(p in texto_lower for p in [
                'alo', 'bueno', 'hello', 'hola', 'oiga', 'si', 'ok'
            ]) and len(texto_lower) < 20
            if _bruce_ya_despidio_776 and _cliente_post_farewell_776:
                print(f"[OK] FIX 776: BRUCE2446 - Post-farewell '{texto_lower[:30]}' → despedida final")
                return {
                    "tipo": "POST_FAREWELL",
                    "respuesta": "Que tenga excelente día, hasta luego.",
                    "accion": "DESPEDIDA_FINAL"
                }

        # ================================================================
        # FIX 520 BRUCE1652: Flujo de ofrecer contacto de Bruce
        # Cuando cliente no puede dar info del encargado, Bruce ofrece su número
        # ================================================================

        # Fase 1: Bruce ofreció dejar su número, esperando respuesta del cliente
        if self.estado_conversacion == EstadoConversacion.OFRECIENDO_CONTACTO_BRUCE:
            # Detectar si cliente acepta recibir el contacto
            cliente_acepta = any(p in texto_lower for p in [
                'sí', 'si', 'claro', 'adelante', 'va', 'sale', 'ok', 'okay',
                'dígame', 'digame', 'dime', 'pásemelo', 'pasemelo', 'démelo', 'demelo',
                'anote', 'anota', 'deje', 'deja', 'por favor', 'perfecto',
                'cómo no', 'como no', 'órale', 'orale', 'ándale', 'andale',
                'está bien', 'esta bien', 'bueno', 'pues sí', 'pues si'
            ])

            # Detectar si cliente rechaza
            cliente_rechaza = any(p in texto_lower for p in [
                'no gracias', 'no, gracias', 'no hace falta', 'no es necesario',
                'no se preocupe', 'no te preocupes', 'así está bien', 'asi esta bien',
                'mejor no', 'no por ahora', 'ahorita no'
            ])

            if cliente_rechaza:
                print(f"   FIX 520: Cliente RECHAZA recibir contacto - despedirse amablemente")
                self.estado_conversacion = EstadoConversacion.DESPEDIDA
                return {
                    "tipo": "CLIENTE_RECHAZA_CONTACTO_BRUCE",
                    "respuesta": "Entendido, no se preocupe. Le vuelvo a llamar más tarde. Muchas gracias por su tiempo.",
                    "accion": "DESPEDIRSE"
                }
            elif cliente_acepta:
                print(f"   FIX 520: Cliente ACEPTA recibir contacto - preguntar si tiene dónde anotar")
                self.estado_conversacion = EstadoConversacion.ESPERANDO_DONDE_ANOTAR
                return {
                    "tipo": "CLIENTE_ACEPTA_CONTACTO_BRUCE",
                    "respuesta": "Perfecto. ¿Tiene dónde anotar?",
                    "accion": "PREGUNTAR_DONDE_ANOTAR"
                }
            else:
                # Respuesta ambigua - repetir ofrecimiento
                print(f"   FIX 520: Respuesta ambigua - clarificar ofrecimiento")
                return {
                    "tipo": "CLARIFICAR_OFRECIMIENTO",
                    "respuesta": "¿Me permite dejarle el número para que el encargado nos contacte?",
                    "accion": "REPETIR_OFRECIMIENTO"
                }

        # Fase 2: Bruce preguntó si tiene dónde anotar, esperando confirmación
        if self.estado_conversacion == EstadoConversacion.ESPERANDO_DONDE_ANOTAR:
            # Detectar si cliente tiene dónde anotar
            tiene_donde_anotar = any(p in texto_lower for p in [
                'sí', 'si', 'claro', 'adelante', 'dígame', 'digame', 'dime',
                'anoto', 'apunto', 'tengo', 'ya', 'listo', 'pásemelo', 'pasemelo',
                'démelo', 'demelo', 'dámelo', 'damelo', 'va', 'sale', 'ok',
                'ajá', 'aja', 'órale', 'orale', 'ándale', 'andale', 'espere', 'espera',
                'déjeme', 'dejeme', 'déjame', 'dejame', 'un momento', 'un segundo'
            ])

            # Detectar si no tiene dónde anotar
            no_tiene = any(p in texto_lower for p in [
                'no tengo', 'ahorita no', 'no traigo', 'no encuentro',
                'espéreme', 'espereme', 'deje busco', 'deja busco'
            ])

            if no_tiene:
                print(f"   FIX 520: Cliente NO tiene dónde anotar - esperar")
                return {
                    "tipo": "ESPERANDO_QUE_ANOTE",
                    "respuesta": "Claro, lo espero.",
                    "accion": "ESPERAR"
                }
            elif tiene_donde_anotar:
                print(f"   FIX 520: Cliente TIENE dónde anotar - dar número y marca")
                self.estado_conversacion = EstadoConversacion.CONTACTO_CAPTURADO
                return {
                    "tipo": "DAR_CONTACTO_BRUCE",
                    "respuesta": "El número es 6 6 2, 4 1 5, 1 9 9 7 y la marca es NIOVAL, se escribe N I O V A L. Quedamos atentos a su llamada.",
                    "accion": "CONTACTO_DADO"
                }
            else:
                # Asumir que sí tiene y dar el número
                print(f"   FIX 520: Respuesta ambigua - asumir que sí tiene y dar número")
                self.estado_conversacion = EstadoConversacion.CONTACTO_CAPTURADO
                return {
                    "tipo": "DAR_CONTACTO_BRUCE",
                    "respuesta": "El número es 6 6 2, 4 1 5, 1 9 9 7 y la marca es NIOVAL, se escribe N I O V A L. Quedamos atentos a su llamada.",
                    "accion": "CONTACTO_DADO"
                }

        # ================================================================
        # FIX 497: SISTEMA DE DETECCIÓN SEMÁNTICA ROBUSTO
        # PROBLEMA: Variaciones regionales de México no se detectaban
        # - Querétaro: "No está"
        # - CDMX: "Jefe, disculpe aún no llega"
        # - Norte: "El patrón no se encuentra"
        # - Bajío: "El mero mero salió"
        # SOLUCIÓN: Patrones expandidos + detección por palabras clave
        # ================================================================

        # --- SINÓNIMOS DE "ENCARGADO" POR REGIÓN ---
        sinonimos_encargado = [
            # Formales
            'encargado', 'encargada', 'responsable', 'gerente', 'gerenta',
            'administrador', 'administradora', 'director', 'directora',
            # Informales/Regionales
            'jefe', 'jefa', 'patrón', 'patron', 'patrona', 'dueño', 'dueña',
            'el mero mero', 'la mera mera', 'el que manda', 'la que manda',
            'el de compras', 'la de compras', 'quien compra', 'el que compra',
            'quien decide', 'el que decide', 'la que decide',
            # Títulos
            'licenciado', 'licenciada', 'ingeniero', 'ingeniera', 'contador', 'contadora'
        ]

        # --- PATRONES DE "NO ESTÁ" EXPANDIDOS ---
        # Incluye variaciones regionales de todo México
        patrones_no_esta = [
            # Básicos (Querétaro, Bajío)
            # FIX 525 BRUCE1670: Incluir "no se encuentre" (error común de transcripción)
            'no está', 'no esta', 'no se encuentra', 'no se encuentre', 'no anda',
            # Salió/Fue (General)
            'salió', 'salio', 'se fue', 'se salió', 'se salio', 'anda fuera',
            'fue a', 'anda en', 'está afuera', 'esta afuera',
            # Llegará después (CDMX, formal)
            'aún no llega', 'aun no llega', 'todavía no llega', 'todavia no llega',
            'no ha llegado', 'viene más tarde', 'viene mas tarde',
            'llega a las', 'llega más tarde', 'llega mas tarde', 'llega hasta',
            'viene a las', 'regresa a las', 'vuelve a las',
            'llega como a las', 'viene como a las', 'regresa como a las',
            # No disponible (General)
            'no hay nadie', 'no lo encuentro', 'no la encuentro',
            'está ocupado', 'esta ocupado', 'está ocupada', 'esta ocupada',
            'está en junta', 'esta en junta', 'anda en una junta',
            'no puede atender', 'no lo puedo comunicar', 'no la puedo comunicar',
            # Horario/Día (General)
            'hoy no viene', 'hoy no vino', 'viene mañana', 'viene el lunes',
            'no trabaja hoy', 'es su día de descanso', 'es su dia de descanso',
            'ya se fue', 'ya salió', 'ya salio',
            # Regional Norte (Monterrey, Chihuahua)
            'no anda aquí', 'no anda aqui', 'anda pa fuera',
            # Regional CDMX
            'disculpe', 'ahorita no', 'ahorita no está', 'ahorita no esta',
            'en este momento no', 'por el momento no',
            # Comida/Descanso
            'salió a comer', 'salio a comer', 'está comiendo', 'esta comiendo',
            'fue a comer', 'anda comiendo', 'salió a desayunar', 'salio a desayunar',
            # FIX 642D: BRUCE2070 - "marcar más tarde" = encargado no disponible (callback)
            'marcar más tarde', 'marcar mas tarde', 'llamar más tarde', 'llamar mas tarde',
            'marque más tarde', 'marque mas tarde', 'llame más tarde', 'llame mas tarde',
            'marcar después', 'marcar despues', 'llamar después', 'llamar despues',
        ]

        # FIX 710C: BRUCE2255 - "No hacemos compras" = RECHAZO DEFINITIVO (antes de ENCARGADO_NO_ESTA)
        # Cliente dice que el negocio NO compra → no tiene sentido pedir WhatsApp del encargado
        patrones_no_hacemos_compras_710 = [
            'no hacemos compra', 'no hacemos compras', 'no hacemos ningun tipo de compra',
            'no compramos', 'no compro nada', 'no compramos nada',
            'aqui no se compra', 'aqui no compramos', 'no hacemos pedidos',
            'no manejamos compras', 'no realizamos compras', 'no adquirimos',
            'no necesitamos proveedores', 'no necesitamos proveedor',
        ]
        if any(p in texto_lower for p in patrones_no_hacemos_compras_710):
            print(f"   FIX 710C: BRUCE2255 - Cliente dice NO HACEN COMPRAS: '{texto_cliente[:60]}'")
            return {
                "tipo": "NO_HACEMOS_COMPRAS",
                "respuesta": "Entendido, disculpe la molestia. Que tenga buen día.",
                "accion": "DESPEDIDA"
            }

        # FIX 744: BRUCE2366 - AREA_EQUIVOCADA inmediato
        # Cliente dice "no tengo negocio", "está equivocado", "número equivocado" etc.
        # Bruce debe disculparse y colgar INMEDIATAMENTE (no pedir WhatsApp)
        patrones_area_equivocada_744 = [
            'esta equivocado', 'estas equivocado', 'usted esta equivocado',
            'numero equivocado', 'se equivoco de numero', 'se equivoco de telefono',
            'marco equivocado', 'llamo equivocado', 'llamo al lugar equivocado',
            'no tengo negocio', 'no tenemos negocio', 'yo no tengo negocio',
            'no es negocio', 'aqui no hay negocio', 'no hay ningun negocio',
            'no es ferreteria', 'esto no es ferreteria', 'aqui no es ferreteria',
            'no vendemos ferreteria', 'no manejamos ferreteria', 'no manejo ferreteria',
            'no es mi area', 'no es el area', 'area equivocada', 'departamento equivocado',
            'no es aqui', 'aqui no es', 'no es conmigo', ' no soy yo', 'no, no soy yo',
            'no es mi departamento', 'no es de mi area',
        ]
        if any(p in texto_lower for p in patrones_area_equivocada_744):
            print(f"   FIX 744: BRUCE2366 - AREA_EQUIVOCADA detectada: '{texto_cliente[:60]}'")
            return {
                "tipo": "AREA_EQUIVOCADA",
                "respuesta": "Disculpe la molestia, que tenga buen día.",
                "accion": "DESPEDIDA"
            }

        # Detectar si cliente menciona que el encargado NO ESTÁ
        encargado_no_esta = any(p in texto_lower for p in patrones_no_esta)

        # También detectar si mencionan sinónimo + negación
        # Ej: "el jefe no está", "el patrón salió", "el dueño viene más tarde"
        if not encargado_no_esta:
            for sinonimo in sinonimos_encargado:
                if sinonimo in texto_lower:
                    # Verificar si hay negación o ausencia cerca
                    negaciones = ['no', 'salió', 'salio', 'fue', 'viene', 'llega', 'anda', 'todavía', 'todavia', 'aún', 'aun']
                    if any(neg in texto_lower for neg in negaciones):
                        encargado_no_esta = True
                        print(f"[OK] FIX 497: Detectado sinónimo '{sinonimo}' + ausencia")
                        break

        # FIX 621C: BRUCE2048 - Detectar "otra sucursal" / "no es aquí" / "la matriz"
        # Problema: Cliente dice "no es en esta sucursal, es en la otra" pero Bruce insiste por encargado
        # Solución: Detectar redirección a otra sucursal y pedir teléfono de esa sucursal
        # FIX 688: BRUCE2200 - "comunicarse directamente con Cuba" = redirección a sede/matriz
        patrones_otra_sucursal_621c = [
            'otra sucursal', 'la otra sucursal', 'en la otra',
            'no es en esta', 'no es esta sucursal', 'no es aquí', 'no es aqui',
            'es en otra', 'en otra parte', 'en otro lado', 'en otro local',
            'la matriz', 'en la matriz', 'la central', 'la principal',
            'nos mandan de', 'mandan desde', 'piden desde', 'compran desde',
            'aquí no hay encargado', 'aqui no hay encargado',
            'aquí no tenemos', 'aqui no tenemos',
            'aquí no se compra', 'aqui no se compra',
            'aquí no manejamos', 'aqui no manejamos',
            'no es esta tienda', 'no es aquí donde',
            # FIX 688: Patrones de redirección a sede/matriz/ciudad
            'comunicarse directamente', 'hablar directamente con',
            'llamar directamente', 'directamente con ellos',
            'directamente a la', 'la casa matriz', 'la sede',
            'las oficinas centrales', 'la oficina central',
            'corporativo', 'el corporativo',
        ]
        es_otra_sucursal_621c = any(p in texto_lower for p in patrones_otra_sucursal_621c)
        if es_otra_sucursal_621c:
            print(f"   FIX 621C: BRUCE2048 - Cliente indica OTRA SUCURSAL: '{texto_cliente[:60]}'")
            # Verificar si ya se pidió el teléfono de la otra sucursal
            ultimas_bruce_621c = [
                msg['content'].lower() for msg in self.conversation_history[-4:]
                if msg['role'] == 'assistant'
            ]
            ya_pidio_tel_sucursal = any(
                'teléfono de esa sucursal' in msg or 'telefono de esa sucursal' in msg
                or 'número de la otra' in msg or 'numero de la otra' in msg
                for msg in ultimas_bruce_621c
            )
            if ya_pidio_tel_sucursal:
                print(f"   FIX 621C: Ya pidió teléfono sucursal - ofrecer catálogo directo")
                return {
                    "tipo": "OTRA_SUCURSAL_INSISTENCIA",
                    "respuesta": "Entiendo, no se preocupe. ¿Me permite dejarle el número de NIOVAL para que le pasen la información al encargado? Es el 6 6 2, 4 1 5, 1 9 9 7.",
                    "accion": "OFRECER_CONTACTO"
                }
            return {
                "tipo": "OTRA_SUCURSAL",
                "respuesta": "Entiendo, es en otra sucursal. ¿Me podría dar el teléfono de esa sucursal para comunicarme directamente con ellos?",
                "accion": "PEDIR_TEL_SUCURSAL"
            }

        if encargado_no_esta:
            # Verificar si Bruce ya preguntó por encargado (evitar loop)
            ultimas_bruce = [
                msg['content'].lower() for msg in self.conversation_history[-6:]
                if msg['role'] == 'assistant'
            ]
            veces_pregunto = sum(
                1 for msg in ultimas_bruce
                if 'se encontrará el encargado' in msg or 'se encontrara el encargado' in msg
                   or 'encargado de compras' in msg
            )

            if veces_pregunto >= 1:  # Si ya preguntó al menos 1 vez
                print(f"[OK] FIX 493: Cliente dice encargado NO ESTÁ + Bruce ya preguntó {veces_pregunto} vez(ces)")

                # FIX 518 BRUCE1644: Verificar si Bruce ya pidió WhatsApp (evitar loop)
                bruce_ya_pidio_whatsapp = any(
                    'whatsapp del encargado' in msg or 'whatsapp del' in msg
                    for msg in ultimas_bruce
                )

                # FIX 518: Detectar si cliente dice que NO PUEDE dar info
                cliente_no_puede = any(p in texto_lower for p in [
                    'no puedo', 'no, no', 'no no', 'apenas', 'nada más', 'nada mas',
                    'solo mostrador', 'en el mostrador', 'no están', 'no estan'
                ])

                # FIX 555: BRUCE1895 - Mejorar detección de horarios específicos
                # PROBLEMA: "Después de las 5:00 de la tarde" era detectado como callback genérico
                # SOLUCIÓN: Detectar PRIMERO horarios específicos antes de callback genérico

                def _detectar_horario_especifico(texto: str) -> tuple:
                    """
                    FIX 555: Detecta horarios específicos en el texto
                    Returns: (tiene_horario: bool, hora_texto: str)
                    """
                    import re

                    # Patrón 1: "X:XX" formato (5:00, 17:30, etc.)
                    patron_numero = r'\b(\d{1,2}):(\d{2})\b'
                    match = re.search(patron_numero, texto)
                    if match:
                        return (True, f"{match.group(1)}:{match.group(2)}")

                    # Patrón 2: "a las X", "las X", "después de las X", "antes de las X"
                    patron_las = r'(?:a las|las|después de las|despues de las|antes de las)\s*(\d{1,2})'
                    match = re.search(patron_las, texto)
                    if match:
                        return (True, match.group(1))

                    # Patrón 3: "X de la mañana/tarde/noche", "X am/pm"
                    patron_periodo = r'(\d{1,2})\s*(?:de la|por la)?\s*(?:mañana|tarde|noche|am|pm|a\.?m\.?|p\.?m\.?)'
                    match = re.search(patron_periodo, texto)
                    if match:
                        return (True, match.group(1))

                    # Patrón 4: Día específico (implica horario concreto)
                    dias_semana = ['lunes', 'martes', 'miércoles', 'miercoles', 'jueves', 'viernes', 'sábado', 'sabado', 'domingo']
                    if any(dia in texto for dia in dias_semana):
                        return (True, "día específico")

                    return (False, "")

                tiene_horario_especifico, hora_texto = _detectar_horario_especifico(texto_lower)

                # FIX 518: Detectar "más tarde" / "después" SOLO si NO hay hora específica
                indica_callback_generico = any(p in texto_lower for p in [
                    'más tarde', 'mas tarde', 'después', 'despues',
                    'al rato', 'en un rato', 'luego', 'ahorita no'
                ]) and not tiene_horario_especifico  # FIX 555: Añadir verificación

                # FIX 625A: BRUCE2058 - Detectar "te puedo pasar mi teléfono" ANTES de horario
                # Problema: Cliente dice "No está, pero dime, te puedo pasar mi teléfono"
                # Bruce pedía número del ENCARGADO en vez de aceptar teléfono del CLIENTE
                palabras_ofrece_telefono_625 = [
                    'te puedo pasar mi teléfono', 'le puedo pasar mi teléfono',
                    'te puedo pasar mi telefono', 'le puedo pasar mi telefono',
                    'te puedo pasar el teléfono', 'le puedo pasar el teléfono',
                    'te puedo pasar el telefono', 'le puedo pasar el telefono',
                    'puedo pasar mi teléfono', 'puedo pasar mi telefono',
                    'puedo pasar mi número', 'puedo pasar mi numero',
                    'puedo pasar mi celular', 'puedo pasar mi cel',
                    'puedo dar mi teléfono', 'puedo dar mi telefono',
                    'puedo dar mi número', 'puedo dar mi numero',
                    'te doy mi teléfono', 'le doy mi teléfono',
                    'te doy mi telefono', 'le doy mi telefono',
                    'te paso mi teléfono', 'le paso mi teléfono',
                    'te paso mi telefono', 'le paso mi telefono',
                    'te doy mi cel', 'le doy mi cel',
                    'yo te apoyo', 'yo te puedo apoyar', 'yo le puedo apoyar',
                    'dime yo te puedo', 'dime yo te ayudo',
                ]
                if any(p in texto_lower for p in palabras_ofrece_telefono_625):
                    print(f"   FIX 625A: BRUCE2058 - Cliente ofrece SU teléfono/contacto directo")
                    print(f"     Texto: '{texto_lower[:80]}'")
                    self.estado_conversacion = EstadoConversacion.DICTANDO_NUMERO
                    return {
                        "tipo": "CLIENTE_OFRECE_SU_CONTACTO",
                        "respuesta": "Claro, dígame su número por favor.",
                        "accion": "CAPTURAR_TELEFONO_CLIENTE"
                    }

                # FIX 626B: BRUCE2060 - "te paso su teléfono" = OFRECE contacto del ENCARGADO
                # Similar a FIX 625A pero para "su" (encargado) en vez de "mi" (cliente)
                # Problema: Cliente decía "si quieres te paso su teléfono" y Bruce respondía
                # "Claro, espero" (transfer) o "Disculpe, no escuché bien" (loop)
                palabras_ofrece_tel_encargado_626 = [
                    'te paso su teléfono', 'le paso su teléfono',
                    'te paso su telefono', 'le paso su telefono',
                    'te paso su número', 'le paso su número',
                    'te paso su numero', 'le paso su numero',
                    'te paso su cel', 'le paso su cel',
                    'te doy su teléfono', 'le doy su teléfono',
                    'te doy su telefono', 'le doy su telefono',
                    'te doy su número', 'le doy su número',
                    'te doy su numero', 'le doy su numero',
                    'te doy su cel', 'le doy su cel',
                    'te paso el teléfono', 'le paso el teléfono',
                    'te paso el telefono', 'le paso el telefono',
                    'te paso el número', 'le paso el número',
                    'te paso el numero', 'le paso el numero',
                    'te doy el teléfono', 'le doy el teléfono',
                    'te doy el telefono', 'le doy el telefono',
                    'te doy el número', 'le doy el número',
                    'te doy el numero', 'le doy el numero',
                    '¿te paso su', '¿le paso su',
                ]
                if any(p in texto_lower for p in palabras_ofrece_tel_encargado_626):
                    print(f"   FIX 626B: BRUCE2060 - Cliente ofrece teléfono/número del ENCARGADO")
                    print(f"     Texto: '{texto_lower[:80]}'")
                    self.estado_conversacion = EstadoConversacion.DICTANDO_NUMERO
                    return {
                        "tipo": "OFRECE_CONTACTO_ENCARGADO",
                        "respuesta": "Sí, por favor, dígame el número.",
                        "accion": "CAPTURAR_TELEFONO_ENCARGADO"
                    }

                if tiene_horario_especifico:
                    # FIX 594 BRUCE1987: Si cliente OFRECE correo/whatsapp, priorizar captura
                    # Problema: "Llega hasta el lunes, te doy el correo mejor" → Bruce decía "le llamo entonces"
                    # El patrón ENCARGADO_NO_ESTA_CON_HORARIO ignoraba que el cliente OFRECÍA contacto
                    palabras_ofrece_contacto_594 = [
                        'te doy el correo', 'le doy el correo', 'doy el correo',
                        'te doy mi correo', 'le doy mi correo',
                        'te paso el correo', 'le paso el correo', 'paso el correo',
                        'te mando el correo', 'le mando el correo',
                        'anota el correo', 'anote el correo',
                        'te doy el mail', 'le doy el mail',
                        'te doy el email', 'le doy el email',
                        'te doy el whatsapp', 'le doy el whatsapp',
                        'te doy el número', 'le doy el número',
                        'te doy el numero', 'le doy el numero',
                        'te paso el número', 'le paso el número',
                        'te paso el numero', 'le paso el numero',
                        'mándalo por correo', 'mandalo por correo',
                        'mándalo por mail', 'mandalo por mail',
                        'mejor por correo', 'correo mejor',
                        'mejor el correo', 'mejor el mail'
                    ]
                    if any(p in texto_lower for p in palabras_ofrece_contacto_594):
                        print(f"   FIX 594: Cliente OFRECE contacto (correo/whatsapp) - PRIORIDAD sobre callback")
                        print(f"     Texto: '{texto_lower[:80]}'")
                        return {
                            "tipo": "CLIENTE_OFRECE_CONTACTO_DIRECTO",
                            "respuesta": "Perfecto, dígame el correo y lo anoto.",
                            "accion": "CAPTURAR_CORREO"
                        }
                    print(f"   FIX 555: Cliente dio horario ESPECÍFICO ({hora_texto}) - Confirmar callback")
                    return {
                        "tipo": "ENCARGADO_NO_ESTA_CON_HORARIO",
                        "respuesta": f"Perfecto, le llamo entonces. Muchas gracias por su tiempo.",
                        "accion": "AGENDAR_CALLBACK"
                    }
                # FIX 518: Si cliente indica callback genérico (sin hora específica), preguntar horario
                # FIX 575: Memoria de estado - no repetir misma pregunta
                elif indica_callback_generico:
                    ya_pregunto_horario = getattr(self, 'pregunto_horario_count', 0)
                    self.pregunto_horario_count = ya_pregunto_horario + 1
                    if ya_pregunto_horario == 0:
                        print(f"   FIX 518: Cliente indica callback genérico - Preguntar horario (1ra vez)")
                        return {
                            "tipo": "ENCARGADO_LLEGA_MAS_TARDE",
                            "respuesta": "Entendido. ¿A qué hora me recomienda llamar para encontrarlo?",
                            "accion": "PREGUNTAR_HORARIO"
                        }
                    else:
                        print(f"   FIX 575: Ya preguntó horario {ya_pregunto_horario}x - ofreciendo alternativa")
                        return {
                            "tipo": "ENCARGADO_LLEGA_MAS_TARDE_ALTERNATIVA",
                            "respuesta": "Entiendo que es difícil localizarlo. ¿Me podría proporcionar un número de WhatsApp o correo para enviarle la información?",
                            "accion": "OFRECER_ALTERNATIVA"
                        }
                # FIX 520 BRUCE1652: Si ya pidió WhatsApp y cliente no puede, OFRECER CONTACTO DE BRUCE
                elif bruce_ya_pidio_whatsapp and cliente_no_puede:
                    print(f"   FIX 520: Ya pidió WhatsApp + cliente no puede - Ofrecer contacto de Bruce")
                    self.estado_conversacion = EstadoConversacion.OFRECIENDO_CONTACTO_BRUCE
                    return {
                        "tipo": "OFRECER_CONTACTO_BRUCE",
                        "respuesta": "Entiendo, no se preocupe. ¿Me permite dejarle mi número para que el encargado nos contacte cuando tenga oportunidad?",
                        "accion": "OFRECER_CONTACTO"
                    }
                # FIX 518: Si ya pidió WhatsApp, NO volver a pedir - preguntar horario
                elif bruce_ya_pidio_whatsapp:
                    print(f"   FIX 518: Ya pidió WhatsApp - Preguntar horario en lugar de repetir")
                    return {
                        "tipo": "EVITAR_LOOP_WHATSAPP",
                        "respuesta": "Entendido. ¿A qué hora me recomienda llamar para hablar con el encargado?",
                        "accion": "PREGUNTAR_HORARIO"
                    }
                else:
                    print(f"   FIX 493: Cliente dice NO ESTÁ sin horario - Pedir WhatsApp")
                    return {
                        "tipo": "ENCARGADO_NO_ESTA_SIN_HORARIO",
                        "respuesta": "Entiendo. ¿Me podría proporcionar el WhatsApp del encargado para enviarle el catálogo?",
                        "accion": "PEDIR_WHATSAPP_ENCARGADO"
                    }

        # ================================================================
        # FIX 505: BRUCE1480/1481 - Detectar EMAIL COMPLETO DICTADO
        # DEBE IR ANTES de CLIENTE_ACEPTA_CORREO para tener prioridad
        # PROBLEMA: "El correo es Luis García arroba Gmail punto com" matcheaba
        # con "el correo" en CLIENTE_ACEPTA_CORREO y respondía "¿Cuál es su correo?"
        # SOLUCIÓN: Si tiene arroba + dominio + terminación = EMAIL COMPLETO
        # ================================================================
        dominios_email = ['gmail', 'hotmail', 'outlook', 'yahoo', 'live', 'icloud', 'prodigy', 'aol']
        terminaciones_email = ['punto com', 'punto mx', 'punto net', 'punto org', '.com', '.mx', '.net', '.org']

        tiene_arroba = 'arroba' in texto_lower or '@' in texto_lower
        tiene_dominio = any(dom in texto_lower for dom in dominios_email)
        tiene_terminacion = any(term in texto_lower for term in terminaciones_email)

        # Si tiene los 3 componentes = EMAIL COMPLETO DICTADO
        if tiene_arroba and tiene_dominio and tiene_terminacion:
            print(f"[OK] FIX 505: EMAIL COMPLETO DICTADO detectado: '{texto_cliente[:60]}'")
            print(f"   Arroba: {tiene_arroba}, Dominio: {tiene_dominio}, Terminación: {tiene_terminacion}")

            # Extraer y guardar el email
            import re

            # FIX 639B: BRUCE2068 - Preferir email LITERAL (con "@" real) sobre procesado
            # Problema: STT a veces incluye el email literal al final: "...Es Luis García U. De uva03@gmail.com."
            # Si procesamos "arroba" → "@" primero, la regex matchea el email GARBLED en lugar del correcto
            # Solución: Buscar email con "@" real en el texto ORIGINAL antes de procesar
            match_literal = re.search(r'[a-z0-9._-]+@[a-z0-9.-]+\.[a-z]{2,}', texto_lower)
            if match_literal:
                email_extraido = match_literal.group(0)
                print(f"   FIX 639B: Email LITERAL encontrado: {email_extraido}")
                self.lead_data["email"] = email_extraido
            else:
                # Fallback: Procesar texto (arroba → @, punto com → .com, etc.)
                texto_email = texto_lower

                # FIX 505: Eliminar ayudas mnemotécnicas primero
                # "u de uva" → "u", "b de burro" → "b", etc.
                texto_email = re.sub(r'\b([a-z])\s+de\s+\w+\b', r'\1', texto_email)

                # Eliminar palabras de contexto que no son parte del email
                palabras_eliminar = [
                    'es', 'el', 'la', 'mi', 'su', 'correo', 'email', 'mail',
                    'entonces', 'pues', 'bueno', 'ok', 'este', 'seria', 'sería',
                    'luis', 'garcía', 'garcia', 'juan', 'pedro', 'maria', 'maría',
                ]
                for palabra in palabras_eliminar:
                    texto_email = re.sub(rf'\b{palabra}\b', '', texto_email)

                # Convertir "arroba" → "@"
                texto_email = re.sub(r'\b(arroba|aroba)\b', '@', texto_email)
                # Convertir "punto com" → ".com"
                texto_email = re.sub(r'\bpunto\s*', '.', texto_email)
                # Quitar espacios
                texto_email = re.sub(r'\s+', '', texto_email)

                print(f"   Texto procesado: '{texto_email}'")

                # Buscar patrón de email
                match_email = re.search(r'[a-z0-9._-]+@[a-z0-9.-]+\.[a-z]{2,}', texto_email)
                if match_email:
                    email_extraido = match_email.group(0)
                    print(f"   Email extraído: {email_extraido}")
                    self.lead_data["email"] = email_extraido
                else:
                    print(f"   [WARN] No se pudo extraer email del texto procesado")

            return {
                "tipo": "CLIENTE_DICTA_EMAIL_COMPLETO",
                "respuesta": "Perfecto, ya lo tengo anotado. Le llegará el catálogo en las próximas horas. Muchas gracias por su tiempo.",
                "accion": "DESPEDIRSE"
            }

        # ================================================================
        # FIX 554: BRUCE1895 - Cliente OFRECE recibir información por canal específico
        # PROBLEMA: Cliente dijo "se lo agradecería enviándomelo a un correo" y Bruce NO detectó
        # SOLUCIÓN: Detectar ofertas de canal del cliente (no solo aceptaciones)
        # ================================================================
        patrones_ofrece_recibir_info = [
            # Ofertas con "gustar"
            'si gusta dejarme', 'si gusta enviarme', 'si gusta mandarme',
            'si gusta me lo envía', 'si gusta me lo envia', 'si gusta me lo manda',
            # Ofertas con "agradecería"
            'se lo agradecería enviándomelo', 'se lo agradeceria enviandomelo',
            'se lo agradecería enviandome', 'se lo agradeceria enviandome',
            'se lo agradecería mandándomelo', 'se lo agradeceria mandandome',
            'se lo agradecería si me lo envía', 'se lo agradeceria si me lo envia',
            # Ofertas con "puede"
            'puede enviarme', 'puede mandarme', 'puede dejarme',
            'pueden enviarme', 'pueden mandarme', 'pueden dejarme',
            'podría enviarme', 'podria enviarme', 'podría mandarme', 'podria mandarme', 'podría dejarme', 'podria dejarme',
            # Con canal específico
            'enviármelo a un correo', 'enviarmelo a un correo',
            'mandármelo a un correo', 'mandarmelo a un correo',
            'enviármelo por correo', 'enviarmelo por correo',
            'mandármelo por whatsapp', 'mandarmelo por whatsapp',
            # Solicitudes directas
            'dejar información', 'dejar informacion', 'dejarme información', 'dejarme informacion',
            'déjame información', 'dejame informacion',
            'enviar información', 'enviar informacion', 'enviarme información', 'enviarme informacion',
            'envíame información', 'enviame informacion',
            'mandar información', 'mandar informacion', 'mandarme información', 'mandarme informacion',
            'mándame información', 'mandame informacion'
        ]

        if any(p in texto_lower for p in patrones_ofrece_recibir_info):
            print(f"[OK] FIX 554: Cliente OFRECE recibir información: '{texto_cliente[:60]}'")
            # Detectar canal específico mencionado
            if 'correo' in texto_lower or 'mail' in texto_lower:
                print(f"   Canal detectado: CORREO")
                return {
                    "tipo": "CLIENTE_OFRECE_RECIBIR_CORREO",
                    "respuesta": "Perfecto, con gusto le envío el catálogo. ¿Me permite su correo electrónico?",
                    "accion": "PEDIR_CORREO"
                }
            elif 'whatsapp' in texto_lower:
                print(f"   Canal detectado: WHATSAPP")
                return {
                    "tipo": "CLIENTE_OFRECE_RECIBIR_WHATSAPP",
                    "respuesta": "Perfecto, con gusto le envío el catálogo. ¿Me confirma su número de WhatsApp?",
                    "accion": "PEDIR_WHATSAPP"
                }
            else:
                # Canal no especificado - ofrecer opciones
                print(f"   Canal NO especificado - ofrecer opciones")
                return {
                    "tipo": "CLIENTE_OFRECE_RECIBIR_INFO_GENERICO",
                    "respuesta": "Con gusto. ¿Prefiere que le envíe el catálogo por WhatsApp o correo electrónico?",
                    "accion": "OFRECER_CANALES"
                }

        # ================================================================
        # FIX 495/497: DETECCIÓN ROBUSTA - Cliente ACEPTA correo
        # AMPLIADO: Variaciones regionales + contextuales
        # ================================================================
        patrones_acepta_correo = [
            # Elección directa
            'por correo', 'al correo', 'el correo', 'a mi correo',
            'correo está bien', 'correo esta bien', 'correo por favor',
            'prefiero correo', 'mejor correo', 'mejor por correo',
            'sí correo', 'si correo', 'sí, correo', 'si, correo',
            # Acciones
            'mándame al correo', 'mandame al correo', 'mándalo al correo', 'mandalo al correo',
            'envíame al correo', 'enviame al correo', 'envíalo al correo', 'envialo al correo',
            'pásalo al correo', 'pasalo al correo', 'mándamelo al correo', 'mandamelo al correo',
            # Confirmaciones
            'el correo sí', 'el correo si', 'correo sí', 'correo si',
            'a correo', 'que sea correo', 'que sea por correo',
            # Regional
            'échalo al correo', 'echalo al correo', 'aviéntalo al correo', 'avientalo al correo',
            # Variaciones
            'mail', 'email', 'e-mail', 'al mail', 'por mail', 'al email'
        ]
        # Evitar falso positivo si cliente pregunta "¿Es por correo?" o menciona que ya tiene
        es_pregunta = '?' in texto_cliente or texto_lower.startswith('es ') or texto_lower.startswith('¿')
        tiene_correo = 'ya tiene' in texto_lower or 'ya tienen' in texto_lower
        if any(p in texto_lower for p in patrones_acepta_correo) and not es_pregunta and not tiene_correo:
            print(f"[OK] FIX 495: Cliente ACEPTA recibir por CORREO: '{texto_cliente[:50]}'")
            return {
                "tipo": "CLIENTE_ACEPTA_CORREO",
                "respuesta": "Perfecto. ¿Cuál es su correo electrónico?",
                "accion": "PEDIR_CORREO"
            }

        # FIX 495/497: DETECCIÓN ROBUSTA - Cliente ACEPTA WhatsApp
        patrones_acepta_whatsapp = [
            # Elección directa
            'por whatsapp', 'al whatsapp', 'el whatsapp', 'a mi whatsapp',
            'whatsapp está bien', 'whatsapp esta bien', 'whatsapp por favor',
            'prefiero whatsapp', 'mejor whatsapp', 'mejor por whatsapp',
            'sí whatsapp', 'si whatsapp', 'sí, whatsapp', 'si, whatsapp',
            # FIX 523: BRUCE1752 - Variantes con "vía" (ej: "por vía whatsapp estaría bien")
            'por vía whatsapp', 'por via whatsapp', 'vía whatsapp', 'via whatsapp',
            'whatsapp estaría bien', 'whatsapp estaria bien',
            'sí por whatsapp', 'si por whatsapp', 'sí, por whatsapp', 'si, por whatsapp',
            # Acciones
            'mándame al whatsapp', 'mandame al whatsapp', 'mándalo al whatsapp', 'mandalo al whatsapp',
            'envíame al whatsapp', 'enviame al whatsapp', 'envíalo al whatsapp', 'envialo al whatsapp',
            'pásalo al whatsapp', 'pasalo al whatsapp',
            # Confirmaciones
            'el whatsapp sí', 'el whatsapp si', 'whatsapp sí', 'whatsapp si',
            'a whatsapp', 'que sea whatsapp', 'que sea por whatsapp',
            # Regional/Coloquial
            'por wasa', 'por wats', 'por whats', 'al wasa', 'al wats',
            'por guasap', 'por wasap', 'al guasap', 'al wasap',
            'por wa', 'al wa', 'por el wa',
            # Este número
            'a este número', 'a este numero', 'este mismo número', 'este mismo numero',
            'sí, este', 'si, este', 'a éste', 'a este', 'aquí mismo', 'aqui mismo'
        ]
        if any(p in texto_lower for p in patrones_acepta_whatsapp) and not es_pregunta:
            print(f"[OK] FIX 495: Cliente ACEPTA recibir por WHATSAPP: '{texto_cliente[:50]}'")
            return {
                "tipo": "CLIENTE_ACEPTA_WHATSAPP",
                "respuesta": "Perfecto. ¿Me confirma su número de WhatsApp?",
                "accion": "PEDIR_WHATSAPP"
            }

        # ================================================================
        # FIX 496/497: DETECCIÓN ROBUSTA - Cliente OFRECE dar contacto
        # PROBLEMA: Cliente dijo "¿Te puedo pasar el correo?" y Bruce no entendió
        # AMPLIADO: Todas las formas de ofrecer información de contacto
        # ================================================================
        patrones_ofrece_correo = [
            # FIX 514 BRUCE1733: Agregar variantes con "un" en lugar de "el"
            # Caso: "si gusta, le puedo dar un correo" → Bruce no lo detectó
            'le puedo dar un correo', 'te puedo dar un correo',
            'puedo darle un correo', 'puedo darte un correo',
            'si gusta le puedo dar', 'si gusta te puedo dar',  # sin "correo" al final
            'gusta le doy', 'gusta te doy',  # variantes cortas
            # Preguntas de ofrecimiento
            'te puedo pasar el correo', 'le puedo pasar el correo',
            'te puedo dar el correo', 'le puedo dar el correo',
            'quiere el correo', 'quieres el correo', 'quiere que le dé el correo', 'quiere que le de el correo',
            'quiere que le pase el correo', 'gusta el correo',
            # Acciones directas
            'te paso el correo', 'le paso el correo', 'le doy el correo', 'te doy el correo',
            'te mando el correo', 'le mando el correo',
            'aquí está el correo', 'aqui esta el correo', 'este es el correo',
            # Instrucciones
            'anota el correo', 'anote el correo', 'apunta el correo', 'apunte el correo',
            'tome nota del correo', 'toma nota del correo', 'ahí le va el correo',
            # Disponibilidad
            'tengo el correo', 'aquí tengo el correo', 'aqui tengo el correo',
            'sí tengo correo', 'si tengo correo', 'el correo es',
            'puedo darle el correo', 'puedo darte el correo',
            # Regional
            'le aviento el correo', 'te aviento el correo',
            'ahí te va el correo', 'ahi te va el correo',
            # Dictando
            'es arroba', 'arroba gmail', 'arroba hotmail', 'arroba outlook', 'arroba yahoo'
        ]
        if any(p in texto_lower for p in patrones_ofrece_correo):
            # FIX 552: Verificar estado_email antes de activar FIX 496
            # PROBLEMA BRUCE1889: Repetía "dígame el correo" durante dictado
            if hasattr(self, 'estado_email'):
                if self.estado_email == EstadoEmail.DICTANDO:
                    print(f"⚠️ FIX 552: Cliente está DICTANDO email - NO interrumpir")
                    return None  # NO activar patrón
                elif self.estado_email == EstadoEmail.CAPTURADO:
                    print(f"⚠️ FIX 552: Email ya capturado - NO volver a pedir")
                    return None  # NO activar patrón

            print(f"[OK] FIX 496: Cliente OFRECE dar CORREO: '{texto_cliente[:50]}'")
            # FIX 552: Actualizar estado a OFRECIDO
            if hasattr(self, 'estado_email'):
                self.estado_email = EstadoEmail.OFRECIDO
            return {
                "tipo": "CLIENTE_OFRECE_CORREO",
                "respuesta": "Sí, por favor, dígame el correo.",
                "accion": "ACEPTAR_CORREO"
            }

        # FIX 496/497: DETECCIÓN ROBUSTA - Cliente OFRECE dar WhatsApp/Número
        patrones_ofrece_whatsapp = [
            # Preguntas de ofrecimiento - WhatsApp
            'te puedo pasar el whatsapp', 'le puedo pasar el whatsapp',
            'te puedo dar el whatsapp', 'le puedo dar el whatsapp',
            'quiere el whatsapp', 'quieres el whatsapp', 'quiere que le dé el whatsapp', 'quiere que le de el whatsapp',
            'quiere que le pase el whatsapp', 'gusta el whatsapp',
            # Acciones directas - WhatsApp
            'te paso el whatsapp', 'le paso el whatsapp', 'le doy el whatsapp', 'te doy el whatsapp',
            'te mando el whatsapp', 'le mando el whatsapp',
            'aquí está el whatsapp', 'aqui esta el whatsapp', 'este es el whatsapp',
            # Instrucciones - WhatsApp
            'anota el whatsapp', 'anote el whatsapp', 'apunta el whatsapp', 'apunte el whatsapp',
            'tome nota del whatsapp', 'toma nota del whatsapp',
            # Disponibilidad - WhatsApp
            'tengo el whatsapp', 'aquí tengo el whatsapp', 'aqui tengo el whatsapp',
            'sí tengo whatsapp', 'si tengo whatsapp', 'el whatsapp es',
            'puedo darle el whatsapp', 'puedo darte el whatsapp',
            # Preguntas de ofrecimiento - NÚMERO (genérico)
            'te puedo pasar el número', 'le puedo pasar el número',
            'te puedo pasar el numero', 'le puedo pasar el numero',
            'te puedo dar el número', 'le puedo dar el número',
            'te puedo dar el numero', 'le puedo dar el numero',
            'quiere el número', 'quieres el número', 'quiere el numero', 'quieres el numero',
            # Acciones directas - NÚMERO
            'te paso el número', 'le paso el número', 'te paso el numero', 'le paso el numero',
            'te doy el número', 'le doy el número', 'te doy el numero', 'le doy el numero',
            'aquí está el número', 'aqui esta el numero', 'este es el número', 'este es el numero',
            # Instrucciones - NÚMERO
            'anota el número', 'anote el número', 'anota el numero', 'anote el numero',
            'apunta el número', 'apunte el número', 'apunta el numero', 'apunte el numero',
            'tome nota', 'toma nota', 'ahí le va', 'ahi le va', 'ahí te va', 'ahi te va',
            # Disponibilidad - NÚMERO
            'tengo el número', 'aquí tengo el número', 'tengo el numero', 'aqui tengo el numero',
            'el número es', 'el numero es', 'mi número es', 'mi numero es',
            'puedo darle el número', 'puedo darte el número',
            # Regional - NÚMERO
            'le aviento el número', 'te aviento el número', 'le aviento el numero', 'te aviento el numero',
            # Dictando número
            'es el', 'el cel es', 'el celular es', 'el teléfono es', 'el telefono es',
            # Confirmación de que tienen
            'sí tengo', 'si tengo', 'claro que sí', 'claro que si', 'cómo no', 'como no'
        ]
        if any(p in texto_lower for p in patrones_ofrece_whatsapp):
            # FIX 513 BRUCE1728: Si cliente ya está DICTANDO dígitos, NO repetir "dígame el número"
            # Problema: Cliente dijo "Es el 99, 99" y Bruce repitió "dígame el número" 2 veces
            import re
            digitos_dictados = re.findall(r'\d', texto_cliente)
            if len(digitos_dictados) >= 2:
                print(f"[OK] FIX 513: Cliente DICTANDO número ({len(digitos_dictados)} dígitos) - esperando silencio")
                return {
                    "tipo": "CLIENTE_DICTANDO_NUMERO",
                    "respuesta": "",  # Silencio - esperar que termine de dictar
                    "accion": "ESPERAR_NUMERO"
                }

            # FIX 524: BRUCE1761 - Si cliente TAMBIÉN pregunta de dónde habla, responder PRIMERO
            # Problema: Cliente dijo "¿Cómo no? ¿De dónde dice que llama?" y Bruce ignoró la pregunta
            preguntas_empresa = [
                'de dónde habla', 'de donde habla', 'de dónde llama', 'de donde llama',
                'de dónde me habla', 'de donde me habla', 'de dónde me llama', 'de donde me llama',
                'quién habla', 'quien habla', 'quién llama', 'quien llama',
                'de parte de quién', 'de parte de quien', 'de qué empresa', 'de que empresa',
                'cuál empresa', 'cual empresa', 'qué empresa', 'que empresa'
            ]
            cliente_pregunta_empresa = any(p in texto_lower for p in preguntas_empresa)

            if cliente_pregunta_empresa:
                print(f"[OK] FIX 524: Cliente OFRECE WhatsApp + pregunta empresa - Respondiendo ambos")
                return {
                    "tipo": "CLIENTE_OFRECE_WHATSAPP_CON_PREGUNTA",
                    "respuesta": "Le llamo de NIOVAL, somos distribuidores de productos ferreteros. Sí, dígame su número por favor.",
                    "accion": "ACEPTAR_WHATSAPP_CON_RESPUESTA"
                }

            print(f"[OK] FIX 496: Cliente OFRECE dar WHATSAPP: '{texto_cliente[:50]}'")
            return {
                "tipo": "CLIENTE_OFRECE_WHATSAPP",
                "respuesta": "Sí, por favor, dígame el número.",
                "accion": "ACEPTAR_WHATSAPP"
            }

        # ================================================================
        # FIX 558: SOLICITUD CALLBACK - EVALUAR ANTES que CLIENTE_ES_ENCARGADO
        # (Movido aquí desde más abajo para evitar que "dígame" capture primero)
        # FIX 532 BRUCE1673: Solicitud de callback al mismo número
        # ================================================================
        if any(p in texto_lower for p in [
            "llamar a esta línea", "llamar a esta linea",
            "llamar a esta misma línea", "llamar a esta misma linea",
            "marcar a esta línea", "marcar a esta linea",
            "llame a esta línea", "llame a esta linea",
            "llamarnos a este número", "llamarnos a este numero",
            "llamen a este número", "llamen a este numero",
            "llámenos a este", "llamenos a este",
            "vuelva a llamar", "vuelvan a llamar",
            "regresa la llamada", "regresar la llamada",
            "me marca después", "me marca despues",
            "le marco después", "le marco despues",
            # FIX 558: Patrones adicionales de callback
            "me puede regresar la llamada", "puede regresar la llamada",
            "regrese la llamada", "regréseme la llamada",
            "llame en", "llámeme en", "llameme en",
            "marque en", "márqueme en", "marqueme en",
            "llame más tarde", "llame mas tarde",
            "llámeme más tarde", "llameme mas tarde",
            "puede llamar más tarde", "puede llamar mas tarde",
            "puede marcar más tarde", "puede marcar mas tarde"
        ]) and not any(neg in texto_lower for neg in ["no vuelva", "no llame", "no marque"]):
            print(f"[OK] FIX 532/558: SOLICITUD CALLBACK AL MISMO NÚMERO: '{texto_cliente[:50]}'")
            return {
                "tipo": "SOLICITUD_CALLBACK",
                "respuesta": "Perfecto, con gusto le vuelvo a llamar. ¿A qué hora le convendría más?",
                "accion": "CONFIRMAR_CALLBACK"
            }

        # ================================================================
        # FIX 497: DETECCIÓN ROBUSTA - Cliente ES el encargado
        # PROBLEMA: Bruce sigue preguntando por encargado cuando YA está hablando con él
        # AMPLIADO: Variaciones regionales de confirmación
        # ================================================================
        patrones_soy_encargado = [
            # Confirmaciones directas
            'yo soy', 'soy yo', 'yo mero', 'yo mera', 'el mero', 'la mera',
            'con él habla', 'con el habla', 'con ella habla',
            'a sus órdenes', 'a sus ordenes', 'para servirle',
            'aquí estoy', 'aqui estoy', 'presente', 'servidor', 'servidora',
            # Títulos + confirmación
            'soy el encargado', 'soy la encargada', 'soy el gerente', 'soy la gerente',
            'soy el dueño', 'soy la dueña', 'soy el jefe', 'soy la jefa',
            'soy el responsable', 'soy la responsable', 'soy quien compra',
            'soy el que compra', 'soy la que compra', 'soy quien decide',
            # Regional - confirmación informal
            'sí, yo', 'si, yo', 'yo, dígame', 'yo, digame', 'yo, ¿qué pasó', 'yo, que paso',
            'yo, ¿qué necesita', 'yo, que necesita', 'yo, ¿en qué le ayudo', 'yo, en que le ayudo',
            # FIX 557: Removidos 'mande', 'dígame', 'usted dirá' (son saludos genéricos, no confirmación de encargado)
            # Confirmación de que es él/ella
            'el mismo', 'la misma', 'yo mismo', 'yo misma',
            'conmigo', 'con un servidor', 'con una servidora',
            # Respuesta a "¿Es el encargado?"
            'sí lo soy', 'si lo soy', 'así es', 'asi es', 'efectivamente',
            'correcto', 'afirmativo', 'eso es', 'exacto', 'exactamente',
            # Regional CDMX
            'órale', 'orale', 'órale pues', 'orale pues', 'ándale', 'andale',
            # Regional Norte
            'simón', 'simon', 'nel que sí', 'nel que si'
        ]

        # Verificar si cliente dice que ES el encargado
        # FIX 559: No re-disparar si encargado ya fue confirmado (previene repetición del pitch)
        encargado_ya_confirmado = getattr(self, 'encargado_confirmado', False)
        if any(p in texto_lower for p in patrones_soy_encargado) and not encargado_ya_confirmado:
            # Marcar que el encargado está confirmado
            self.encargado_confirmado = True
            print(f"[OK] FIX 497: Cliente ES el encargado: '{texto_cliente[:50]}'")
            return {
                "tipo": "CLIENTE_ES_ENCARGADO",
                "respuesta": "Perfecto. Le llamo para ofrecerle nuestro catálogo de productos ferreteros NIOVAL. ¿Le gustaría recibirlo por WhatsApp o correo?",
                "accion": "OFRECER_CATALOGO"
            }

        # FIX 476 (AUDITORIA W04): PREGUNTAS DIRECTAS - PRIORIDAD MÁXIMA
        # Problema: Bruce responde "Sí, dígame" en lugar de responder pregunta directa
        # Ejemplo: Cliente: "¿De dónde habla?" → Bruce: "Sí, dígame" [ERROR]
        # Solución: Detectar y responder preguntas ANTES de cualquier otro procesamiento

        # Pregunta: ¿Dónde están ubicados? / ¿Ubicación? (pregunta geográfica específica)
        # NOTA FIX 521: "¿De dónde habla?" en México = "¿De qué empresa?" (NO es ubicación)
        if any(p in texto_lower for p in [
            "dónde están ubicados", "donde estan ubicados",
            "ubicados", "ubicación", "ubicacion",
            "de qué ciudad son", "de que ciudad son", "de qué estado", "de que estado",
            "en qué parte de", "en que parte de", "qué ciudad son", "que ciudad son"
        ]):
            # FIX 521 BRUCE1657: Si ya sabemos que el encargado NO está, NO preguntar por él
            if self.estado_conversacion == EstadoConversacion.ENCARGADO_NO_ESTA:
                print(f"   FIX 521: Pregunta ubicación + encargado NO está - Ofrecer WhatsApp")
                return {
                    "tipo": "PREGUNTA_UBICACION_SIN_ENCARGADO",
                    "respuesta": "Estamos ubicados en Guadalajara, Jalisco, pero hacemos envíos a toda la República Mexicana. ¿Me puede proporcionar el WhatsApp del encargado para enviarle el catálogo?",
                    "accion": "PEDIR_WHATSAPP"
                }
            return {
                "tipo": "PREGUNTA_UBICACION",
                "respuesta": "Estamos ubicados en Guadalajara, Jalisco, pero hacemos envíos a toda la República Mexicana. ¿Me comunica con el encargado de compras?",
                "accion": "RESPONDER_PREGUNTA"
            }

        # Pregunta: ¿De dónde habla? / ¿Quién habla? / ¿De parte de quién? / ¿De qué empresa?
        # FIX 521 BRUCE1657: "¿De dónde habla?" en México = "¿De qué empresa habla?" (NO ubicación)
        # FIX 513 BRUCE1580: Agregar "¿de qué empresa?" que no se detectaba
        if any(p in texto_lower for p in [
            # FIX 521: "De dónde habla/llama" = pregunta de EMPRESA, NO ubicación
            "de dónde habla", "de donde habla", "de dónde llama", "de donde llama",
            "de dónde me habla", "de donde me habla", "de dónde me llama", "de donde me llama",
            "de dónde es", "de donde es",  # "¿De dónde es la llamada?"
            # FIX 738: BRUCE2307 - "¿Dónde dice que llama?" sin prefijo "de"
            "donde dice que llama", "donde dice que habla",
            "de que parte llama", "de que parte habla",
            "donde llama usted", "donde llamas",
            # Variantes de quién habla
            "quién habla", "quien habla", "quién llama", "quien llama",
            "de parte de quién", "de parte de quien", "quién es", "quien es",
            "con quién hablo", "con quien hablo",
            # FIX 749A: BRUCE2388 - "¿Con quién tengo el gusto?"
            "con quién tengo el gusto", "con quien tengo el gusto",
            "con quién tengo gusto", "con quien tengo gusto",
            # FIX 513: BRUCE1580 - "¿De qué empresa dice que habla?"
            "de qué empresa", "de que empresa", "qué empresa", "que empresa",
            "de qué compañía", "de que compañia", "qué compañía", "que compañia",
            # FIX 694: BRUCE2238 - "¿Cuál es su nombre?" no se detectaba
            "cuál es su nombre", "cual es su nombre", "cómo se llama", "como se llama",
            "su nombre", "tu nombre", "nombre de usted"
        ]):
            # FIX 595 BRUCE1992: Distinguir "¿de dónde es?" (UBICACION) vs "¿quién habla?" (IDENTIDAD)
            # Problema: Cliente preguntó "De donde es?" queriendo saber la ciudad, no la empresa
            # Bruce respondió con identidad + repitió pregunta del encargado (incoherente)
            es_pregunta_ubicacion = any(p in texto_lower for p in [
                "de dónde es", "de donde es", "de dónde son", "de donde son",
                "dónde están", "donde estan", "dónde están ubicados", "donde estan ubicados",
                "de qué ciudad", "de que ciudad", "de qué estado", "de que estado"
            ])

            # FIX 521 BRUCE1657: Si ya sabemos que el encargado NO está, NO preguntar por él
            if self.estado_conversacion == EstadoConversacion.ENCARGADO_NO_ESTA:
                if es_pregunta_ubicacion:
                    print(f"   FIX 595: Pregunta UBICACION + encargado NO está - Responder ubicación + WhatsApp")
                    return {
                        "tipo": "PREGUNTA_UBICACION_SIN_ENCARGADO",
                        "respuesta": "Somos de Guadalajara, Jalisco. Distribuimos productos de ferretería de la marca NIOVAL. ¿Me puede proporcionar el WhatsApp del encargado para enviarle el catálogo?",
                        "accion": "PEDIR_WHATSAPP"
                    }
                print(f"   FIX 521: Pregunta identidad + encargado NO está - Ofrecer WhatsApp")
                return {
                    "tipo": "PREGUNTA_IDENTIDAD_SIN_ENCARGADO",
                    "respuesta": "Mi nombre es Bruce, me comunico de la marca NIOVAL. Somos distribuidores de productos ferreteros. ¿Me puede proporcionar el WhatsApp del encargado para enviarle el catálogo?",
                    "accion": "PEDIR_WHATSAPP"
                }
            if es_pregunta_ubicacion:
                print(f"   FIX 595: Pregunta de UBICACION detectada - Responder con ciudad")
                return {
                    "tipo": "PREGUNTA_UBICACION",
                    "respuesta": "Somos de Guadalajara, Jalisco. Distribuimos productos de ferretería de la marca NIOVAL. ¿Se encuentra el encargado de compras?",
                    "accion": "RESPONDER_PREGUNTA"
                }
            return {
                "tipo": "PREGUNTA_IDENTIDAD",
                "respuesta": "Mi nombre es Bruce, me comunico de la marca NIOVAL. Somos distribuidores de productos ferreteros. ¿Me comunica con el encargado de compras?",
                "accion": "RESPONDER_PREGUNTA"
            }

        # Pregunta: ¿Qué vende? / ¿Qué productos?
        if any(p in texto_lower for p in [
            "qué vende", "que vende", "qué ofrece", "que ofrece",
            "qué productos", "que productos", "qué maneja", "que maneja",
            "qué es lo que", "que es lo que", "de qué se trata", "de que se trata"
        ]):
            # FIX 521 BRUCE1657: Si ya sabemos que el encargado NO está, NO preguntar por él
            if self.estado_conversacion == EstadoConversacion.ENCARGADO_NO_ESTA:
                print(f"   FIX 521: Pregunta productos + encargado NO está - Ofrecer WhatsApp")
                return {
                    "tipo": "PREGUNTA_PRODUCTOS_SIN_ENCARGADO",
                    "respuesta": "Distribuimos productos de ferretería: cintas tapagoteras, grifería, herramientas, candados y más de 15 categorías. ¿Me puede proporcionar el WhatsApp del encargado para enviarle el catálogo?",
                    "accion": "PEDIR_WHATSAPP"
                }
            return {
                "tipo": "PREGUNTA_PRODUCTOS",
                "respuesta": "Distribuimos productos de ferretería: cintas tapagoteras, grifería, herramientas, candados y más de 15 categorías. ¿Se encuentra el encargado de compras?",
                "accion": "RESPONDER_PREGUNTA"
            }

        # Pregunta: ¿Qué marcas?
        if any(p in texto_lower for p in [
            "qué marcas", "que marcas", "cuáles marcas", "cuales marcas",
            "de qué marca", "de que marca", "cuál marca", "cual marca",
            "marcas maneja", "marcas tiene", "marca propia"
        ]):
            return {
                "tipo": "PREGUNTA_MARCAS",
                "respuesta": "Manejamos la marca NIOVAL, que es nuestra marca propia. Al ser marca propia ofrecemos mejores precios. ¿Se encuentra el encargado de compras para platicarle más a detalle?",
                "accion": "RESPONDER_PREGUNTA"
            }

        # Pregunta: ¿Cuánto cuesta? / ¿Qué precios?
        # FIX 530 BRUCE1671: Agregar "lista de precios" como pregunta de precios
        if any(p in texto_lower for p in [
            "cuánto cuesta", "cuanto cuesta", "cuánto vale", "cuanto vale",
            "qué precio", "que precio", "cuánto sale", "cuanto sale",
            "dame precios", "deme precios", "qué precios", "que precios",
            # FIX 530 BRUCE1671: Cliente preguntó "una lista de precios?" pero Bruce quedó en silencio
            "lista de precios", "lista precios", "una lista de precios"
        ]):
            return {
                "tipo": "PREGUNTA_PRECIOS",
                "respuesta": "Los precios varían según el producto. ¿Me proporciona su WhatsApp y le envío el catálogo completo con todos los precios?",
                "accion": "RESPONDER_PREGUNTA"
            }

        # ================================================================
        # FIX 513: NUEVOS PATRONES DETECTADOS EN AUDITORÍA
        # BRUCE1581, BRUCE1585, BRUCE1586, BRUCE1591, BRUCE1592
        # ================================================================

        # FIX 513 BRUCE1581: Tienda cerrada / Negocio cerrado
        # Caso: "Está marcando a la tienda cerrada" → Bruce no entendió
        if any(p in texto_lower for p in [
            "tienda cerrada", "está cerrada", "esta cerrada", "estamos cerrados",
            "ya cerramos", "ya cerró", "ya cerro", "negocio cerrado",
            "no estamos abiertos", "cerramos a las", "cerré", "cerre",
            "fuera de horario", "no hay horario", "hasta mañana", "hasta el lunes",
            "ya no atendemos", "ya nos fuimos", "ya se fueron"
        ]):
            # FIX 775: BRUCE2443 - Si cliente YA mencionó hora, NO preguntar "¿A qué hora?"
            # "viene hasta mañana a las diez" → FIX 513 matchea "hasta mañana" pero hora ya está
            _horas_palabras_775 = ['ocho', 'nueve', 'diez', 'once', 'doce', 'una', 'dos',
                                   'tres', 'cuatro', 'cinco', 'seis', 'siete']
            _tiene_hora_775 = (
                re.search(r'a las\s+\d{1,2}', texto_lower) or
                re.search(r'\b\d{1,2}\s*:\s*\d{2}', texto_lower) or
                re.search(r'\b\d{1,2}\s*(?:am|pm)\b', texto_lower) or
                any(f'a las {h}' in texto_lower for h in _horas_palabras_775) or
                any(f'las {h}' in texto_lower for h in _horas_palabras_775)
            )
            # FIX 775B: Si ya preguntamos hora y cliente repite → confirmar (anti-loop)
            _ya_pregunto_hora_775 = self.esperando_hora_callback
            if _tiene_hora_775 or _ya_pregunto_hora_775:
                if _ya_pregunto_hora_775:
                    self.esperando_hora_callback = False
                print(f"[OK] FIX 775: BRUCE2443 - TIENDA CERRADA + hora{'(ya preguntada)' if _ya_pregunto_hora_775 else ''} → confirmar")
                return {
                    "tipo": "TIENDA_CERRADA_CON_HORA",
                    "respuesta": "Perfecto, le llamo mañana a esa hora entonces. Muchas gracias por su tiempo.",
                    "accion": "CONFIRMAR_CALLBACK"
                }
            print(f"[OK] FIX 513: TIENDA CERRADA detectado: '{texto_cliente[:50]}'")
            self.esperando_hora_callback = True  # FIX 775: Marcar que preguntamos hora
            return {
                "tipo": "TIENDA_CERRADA",
                "respuesta": "Entiendo, disculpe la molestia. ¿A qué hora puedo llamar mañana para encontrarlos?",
                "accion": "PEDIR_HORARIO_CALLBACK"
            }

        # FIX 513 BRUCE1586 + FIX 516 BRUCE1619: No tienen WhatsApp
        # Caso: "No, no tenemos WhatsApp" → Bruce no entendió y volvió a preguntar (incorrecto)
        # FIX 516: Agregar más variantes y marcar que NO tiene WhatsApp
        if any(p in texto_lower for p in [
            "no tenemos whatsapp", "no tengo whatsapp", "no hay whatsapp",
            "no manejo whatsapp", "no manejamos whatsapp", "no uso whatsapp",
            "no usamos whatsapp", "no cuento con whatsapp", "sin whatsapp",
            "no tenemos wasa", "no tengo wasa", "no tenemos wats", "no tengo wats",
            # FIX 516: Más variantes detectadas en BRUCE1619
            "aquí no hay whatsapp", "aqui no hay whatsapp",
            "no lo tenemos", "no lo tengo",  # Contexto: después de preguntar WhatsApp
            "no contamos con whatsapp", "no contamos con wasa",
            "ese no lo tenemos", "ese no lo tengo",
            "whatsapp no", "wasa no", "wats no",
            "no, whatsapp no", "no, wasa no",
            "no tienen whatsapp", "no tiene whatsapp"
        ]):
            print(f"[OK] FIX 513/516: CLIENTE NO TIENE WHATSAPP: '{texto_cliente[:50]}'")
            # FIX 516: Marcar que cliente NO tiene WhatsApp para evitar volver a preguntar
            self.lead_data["sin_whatsapp"] = True
            return {
                "tipo": "CLIENTE_NO_TIENE_WHATSAPP",
                "respuesta": "Entendido. ¿Me puede dar un correo electrónico para enviarle la información?",
                "accion": "PEDIR_CORREO"
            }

        # FIX 509: BRUCE1724 - Detectar "número normal" / "es de teléfono" / "línea fija"
        # Caso: Cliente dijo "No, número normal, es de teléfono" después de dictar dígitos
        # Problema: Bruce no capturó el número porque esperaba "WhatsApp"
        # Solución: Detectar esta aclaración y pedir que confirme el número fijo
        if any(p in texto_lower for p in [
            "número normal", "numero normal", "es de teléfono", "es de telefono",
            "teléfono fijo", "telefono fijo", "línea fija", "linea fija",
            "es línea", "es linea", "teléfono normal", "telefono normal",
            "no es whatsapp", "no es wats", "es fijo", "número fijo", "numero fijo",
            "teléfono de la sucursal", "telefono de la sucursal", "teléfono de oficina",
            "telefono de oficina", "número de oficina", "numero de oficina"
        ]):
            print(f"[OK] FIX 509: BRUCE1724 - Cliente aclara que es TELÉFONO FIJO, no WhatsApp")
            print(f"   Texto: '{texto_cliente}'")
            self.lead_data["sin_whatsapp"] = True
            self.lead_data["es_telefono_fijo"] = True
            # Extraer dígitos del texto actual o del historial reciente
            import re
            digitos_texto = re.findall(r'\d', texto_cliente)
            if len(digitos_texto) >= 7:
                numero_extraido = ''.join(digitos_texto[-10:]) if len(digitos_texto) >= 10 else ''.join(digitos_texto)
                print(f"   Número extraído del texto: {numero_extraido}")
                return {
                    "tipo": "CONFIRMAR_TELEFONO_FIJO",
                    "respuesta": f"Perfecto, entonces le marco al {numero_extraido[-4:]}. ¿Es correcto?",
                    "accion": "CONFIRMAR_TELEFONO",
                    "telefono": numero_extraido
                }
            else:
                return {
                    "tipo": "PEDIR_TELEFONO_FIJO",
                    "respuesta": "Entendido. ¿Me podría repetir el número de teléfono fijo?",
                    "accion": "PEDIR_TELEFONO_FIJO"
                }

        # FIX 547: BRUCE1880/1882 - NO ofrecer contacto si cliente está DANDO número
        # Problema: Cliente dice "le mando el numero a ver... E56 40" pero FIX 513/520 interrumpe
        # Solución: Verificar flag esperando_dictado_numero antes de activar oferta
        cliente_dando_numero = hasattr(self, 'esperando_dictado_numero') and self.esperando_dictado_numero
        puede_ofrecer = not cliente_dando_numero

        # FIX 513 BRUCE1591 + FIX 520 BRUCE1652: No pueden dar contacto / No tiene permitido
        # Caso: "No tengo permitido daros ningún WhatsApp" → Ofrecer contacto de Bruce
        # MEJORADO FIX 520: En lugar de pedir horario, ofrecer dejar nuestro contacto
        # FIX 505 BRUCE1721: Agregar "no lo tenemos permitido" y variantes plurales
        # FIX 547: SOLO activar si puede_ofrecer == True
        # FIX 582: Solo ofrecer contacto de Bruce si ya hubo al menos 3 intercambios
        # (previene disparo en primer mensaje con input corrupto)
        historial_suficiente_582 = len(self.conversation_history) >= 4
        if puede_ofrecer and historial_suficiente_582 and any(p in texto_lower for p in [
            # Variantes de "no permitido" (singular y plural)
            "no tengo permitido", "no tenemos permitido", "no lo tenemos permitido",
            "no me permiten", "no nos permiten", "no puedo dar", "no puedo darte",
            "no puedo darle", "no le puedo dar", "no te puedo dar",
            "no está permitido", "no esta permitido", "no me dejan",
            "no estoy autorizado", "no estoy autorizada", "no tengo autorización",
            "no puedo pasar", "no le puedo pasar", "no te puedo pasar",
            # FIX 590 BRUCE1977: Variantes PLURALES "no podemos pasar/dar"
            "no podemos pasar", "no lo podemos pasar", "no los podemos pasar",
            "no le podemos pasar", "no te podemos pasar", "no se lo podemos pasar",
            "no podemos dar", "no lo podemos dar", "no le podemos dar",
            "no podemos proporcion", "no lo podemos proporcion",
            "prohibido dar", "no damos información", "no damos numeros",
            "política de la empresa", "politica de la empresa",
            # FIX 520: Variantes adicionales de "no puedo"
            "no puedo proporcionarle", "no puedo proporcionarte", "no le puedo proporcionar",
            "no te puedo proporcionar", "no cuento con esa información", "no cuento con esa informacion",
            "no tengo esa información", "no tengo esa informacion", "no manejo esa información",
            "no sé el número", "no se el numero", "no sé su número", "no se su numero",
            "no lo sé", "no lo se", "no sé", "no se", "desconozco",
            "no tengo acceso", "no tengo el dato", "no tengo ese dato",
            "no me lo sé", "no me lo se", "no me lo han dado", "no me lo dieron",
            "eso no me lo dan", "eso no lo sé", "eso no lo se",
            "no manejo números", "no manejo numeros", "no manejo esos datos",
            # FIX 520: Variantes de rechazo cortés
            "solamente ellos", "solo ellos", "nada más ellos", "nomas ellos",
            "ellos lo manejan", "él lo maneja", "ella lo maneja",
            "tendría que ser con él", "tendria que ser con el", "tendría que ser con ella",
            "eso lo ve el encargado", "eso lo ve la encargada", "eso lo maneja el jefe",
            "no soy quien para dar", "no me corresponde", "no es mi área",
            # FIX 520: Variantes de negación simple
            "no, no puedo", "no no puedo", "no, solamente", "no solamente",
            "apenas", "apenas y", "nada más", "nomas", "nomás",
            # FIX 605 BRUCE2021: "no puedo mandarle su celular" no matcheaba
            "no puedo mandarle", "no puedo enviarle", "no puedo mandarte",
            "no puedo enviarte", "no le puedo mandar", "no te puedo mandar",
            "no le puedo enviar", "no te puedo enviar",
            "no puedo compartir", "no le puedo compartir", "no te puedo compartir",
            "no, no, no puedo"
        ]):
            print(f"[OK] FIX 513/520: NO PUEDE DAR CONTACTO - Ofrecer contacto de Bruce: '{texto_cliente[:50]}'")
            self.estado_conversacion = EstadoConversacion.OFRECIENDO_CONTACTO_BRUCE
            return {
                "tipo": "OFRECER_CONTACTO_BRUCE",
                "respuesta": "Entiendo, no se preocupe. ¿Me permite dejarle mi número para que el encargado nos contacte cuando tenga oportunidad?",
                "accion": "OFRECER_CONTACTO"
            }

        # FIX 558: SOLICITUD_CALLBACK movido ANTES de CLIENTE_ES_ENCARGADO (ver arriba)

        # FIX 513 BRUCE1585 + FIX 528 BRUCE1704: Confirma mismo número / Este número
        # Caso: "Este número, ya te confirmo si sí" → Bruce no respondió
        # Caso BRUCE1704: "Es este número" → Cliente indica que su WhatsApp es el número actual
        if any(p in texto_lower for p in [
            "este número", "este numero", "a este mismo", "este mismo",
            "aquí mismo", "aqui mismo", "a éste", "en este",
            "al que estás llamando", "al que estas llamando",
            "al que me llamas", "al que me hablas",
            "ya te confirmo", "te confirmo", "le confirmo",
            "es el mismo", "el mismo número", "el mismo numero",
            # FIX 528 BRUCE1704: Patrones adicionales para "es este número"
            "es este", "es éste", "es ese", "sería este", "seria este",
            "el que aparece", "el que te aparece", "el que le aparece",
            "el que marca", "el que te marca", "el que le marca",
            "el de aquí", "el de aqui", "el que estás viendo", "el que estas viendo",
            "pues este", "pues éste", "sí, este", "si, este", "sí este", "si este",
            # FIX 563: Patrones "mándelo a este número/teléfono"
            "mándelo a este", "mandelo a este", "envíelo a este", "envielo a este",
            "mándelo aquí", "mandelo aqui", "envíelo aquí", "envielo aqui",
            "a este teléfono", "a este telefono", "a este celular",
            "mande la información aquí", "mande la informacion aqui",
            "envíe el catálogo aquí", "envie el catalogo aqui",
            "mande a este", "envíe a este", "envie a este",
            "mándalo a este", "mandalo a este", "sí, a este", "si, a este",
            # FIX 580: "Puede enviar la información a este número de WhatsApp"
            "enviar la información a este", "enviar la informacion a este",
            "enviar información a este", "enviar informacion a este",
            "puede enviar a este", "pueden enviar a este",
            "mandar la información a este", "mandar la informacion a este",
            "enviar por este", "mandar por este",
            "a este whatsapp", "a este número de whatsapp", "a este numero de whatsapp",
            "por este whatsapp", "por este número", "por este numero",
            "puede enviar su información", "pueden enviar su información",
            "puede enviar su informacion", "pueden enviar su informacion"
        ]) and not any(neg in texto_lower for neg in ["no es", "no tengo", "no tiene"]):
            print(f"[OK] FIX 513: CONFIRMA MISMO NÚMERO: '{texto_cliente[:50]}'")
            return {
                "tipo": "CONFIRMA_MISMO_NUMERO",
                "respuesta": "Perfecto, le envío el catálogo a este número entonces. Muchas gracias por su tiempo.",
                "accion": "CONFIRMAR_ENVIO"
            }

        # FIX 513 BRUCE1592 + FIX 515 BRUCE1613: Transferencia completada / Persona nueva
        # Caso BRUCE1592: Cliente dijo "Un momento", luego "¿Bueno?" al regresar
        # Caso BRUCE1613: Cliente transfirió y el encargado contestó - Bruce debe PRESENTARSE
        # Verificar si antes hubo una espera/transferencia
        ultimos_mensajes = [msg['content'].lower() for msg in self.conversation_history[-6:] if msg['role'] == 'user']
        hubo_espera = any(esp in ' '.join(ultimos_mensajes) for esp in [
            'un momento', 'espere', 'espérame', 'esperame', 'ahorita le paso',
            'le comunico', 'permítame', 'permitame', 'déjeme', 'dejeme',
            'le transfiero', 'lo comunico', 'la comunico', 'se lo paso', 'se la paso'
        ])

        # FIX 515: Patrones que indican que el ENCARGADO ya está en línea
        patrones_encargado_presente = [
            # Saludos que indican persona nueva
            "¿bueno?", "bueno?", "¿bueno", "bueno,", "bueno sí", "bueno si",
            "¿sí?", "si?", "¿hola?", "hola?", "hola,", "hola buenos",
            "¿me escucha", "me escucha", "¿sigue ahí", "sigue ahi", "¿está ahí", "esta ahi",
            # FIX 515: Patrones de encargado respondiendo directamente
            "sí dígame", "si digame", "dígame", "digame", "a sus órdenes", "a sus ordenes",
            "¿qué se le ofrece", "que se le ofrece", "¿en qué le ayudo", "en que le ayudo",
            "¿en qué le puedo ayudar", "en que le puedo ayudar",
            "¿quién habla?", "quien habla?", "¿de dónde llama", "de donde llama",
            "¿de parte de quién", "de parte de quien", "¿con quién hablo", "con quien hablo",
            "mande", "mándeme", "mandeme", "a ver", "sí, bueno", "si, bueno"
        ]

        if hubo_espera and any(p in texto_lower for p in patrones_encargado_presente):
            # FIX 515: Determinar si es el ENCARGADO o solo alguien regresando
            # Si preguntan "¿quién habla?" o "¿en qué le ayudo?" → ES el encargado, PRESENTARSE
            es_encargado_directo = any(p in texto_lower for p in [
                "dígame", "digame", "¿qué se le ofrece", "que se le ofrece",
                "¿en qué le ayudo", "en que le ayudo", "¿en qué le puedo",
                "a sus órdenes", "a sus ordenes", "mande"
            ])

            if es_encargado_directo:
                print(f"[OK] FIX 515: ENCARGADO PRESENTE después de transferencia: '{texto_cliente[:50]}'")
                return {
                    "tipo": "TRANSFERENCIA_COMPLETADA_ENCARGADO",
                    "respuesta": "Hola, me comunico de la marca NIOVAL para ofrecer información de nuestros productos de ferretería. ¿Le gustaría recibir nuestro catálogo por WhatsApp o correo?",
                    "accion": "PRESENTARSE_A_ENCARGADO"
                }
            else:
                # FIX 561: Anti-repetición - no dar misma respuesta más de 1 vez
                self.regreso_espera_count = getattr(self, 'regreso_espera_count', 0) + 1
                if self.regreso_espera_count <= 1:
                    print(f"[OK] FIX 513: REGRESO DESPUÉS DE ESPERA: '{texto_cliente[:50]}'")
                    return {
                        "tipo": "REGRESO_DE_ESPERA",
                        "respuesta": "Sí, aquí estoy. ¿Me comunica con el encargado de compras?",
                        "accion": "RETOMAR_CONVERSACION"
                    }
                else:
                    print(f"   FIX 561: REGRESO_DE_ESPERA ya dado {self.regreso_espera_count} veces - dejando a GPT")

        # FIX 514 BRUCE1595: Cliente pide LLAMAR DESPUÉS/MÁS TARDE
        # Caso: Cliente dice "llámeme más tarde" → Bruce ofreció catálogo (INCORRECTO)
        # Cuando cliente pide callback, NO ofrecer catálogo ni pedir contacto - solo pedir horario
        if any(p in texto_lower for p in [
            # Variantes de "llamar más tarde"
            "llame más tarde", "llame mas tarde", "llámeme más tarde", "llameme mas tarde",
            "llama más tarde", "llama mas tarde", "llámame más tarde", "llamame mas tarde",
            "llámenos más tarde", "llamenos mas tarde",
            # Variantes de "llamar después"
            "llame después", "llame despues", "llámeme después", "llameme despues",
            "llama después", "llama despues", "llámame después", "llamame despues",
            # Variantes de "marcar más tarde/después"
            "marque más tarde", "marque mas tarde", "márqueme más tarde", "marqueme mas tarde",
            "marca más tarde", "marca mas tarde", "márcame más tarde", "marcame mas tarde",
            "marque después", "marque despues", "márqueme después", "marqueme despues",
            # Variantes de "otro momento/día"
            "llame en otro momento", "llama en otro momento",
            "llámeme otro día", "llameme otro dia", "llama otro día", "llama otro dia",
            "marque otro día", "marque otro dia", "marca otro día", "marca otro dia",
            # Variantes cortas que indican callback
            "mejor más tarde", "mejor mas tarde", "mejor después", "mejor despues",
            "al rato", "en un rato me llama", "en un rato me llamas",
            "ahorita no puedo", "ahorita estoy ocupado", "ahorita estoy ocupada",
            "estoy ocupado", "estoy ocupada", "no puedo ahorita",
            "regrese la llamada", "vuelva a llamar", "vuelve a llamar",
            "intente más tarde", "intente mas tarde",
            # FIX 517 BRUCE1637: Variantes con "gusta" (forma cortés mexicana)
            "gusta llamar más tarde", "gusta llamar mas tarde",
            "gusta marcar más tarde", "gusta marcar mas tarde",
            "gusta llamar después", "gusta llamar despues",
            "si gusta llamar", "si gusta marcar",
            # FIX 695: "hablar" variantes
            "si gusta hablar", "si gustas hablar", "hablar luego", "hablar más tarde",
            "si gusta llámele", "si gusta llamele",
            "le gustaría llamar", "le gustaria llamar",
            # FIX 517: Cliente dice que ÉL volverá a llamar (implica callback)
            "vuelvo a llamar", "le vuelvo a llamar", "yo le llamo",
            "yo le marco", "le marco después", "le marco despues"
        ]):
            # Verificar que no sea "no me llame" o rechazo total
            if not any(neg in texto_lower for neg in ["no me llame", "no llames", "no vuelva", "deja de llamar"]):
                print(f"[OK] FIX 514: CLIENTE PIDE LLAMAR DESPUÉS: '{texto_cliente[:50]}'")
                return {
                    "tipo": "CLIENTE_PIDE_LLAMAR_DESPUES",
                    "respuesta": "Claro, sin problema. ¿A qué hora le vendría mejor que le llame?",
                    "accion": "AGENDAR_CALLBACK"
                }

        # FIX 621A: BRUCE2051 - Pre-check: Cliente OFRECE su correo/número (NO pide contacto NIOVAL)
        # Problema: "Le voy a dar un número de un correo" matcheaba "número de" en PIDE_CONTACTO_NIOVAL
        # porque los patrones genéricos como "número de", "un número" son ambiguos
        # Solución: Si cliente dice "le voy a dar/pasar", "yo le doy", etc. → es OFERTA del cliente
        indicadores_cliente_ofrece_621 = [
            'le voy a dar', 'te voy a dar', 'les voy a dar',
            'le voy a pasar', 'te voy a pasar', 'les voy a pasar',
            'le voy a mandar', 'te voy a mandar',
            'yo le doy', 'yo te doy', 'yo le paso', 'yo te paso',
            'le doy un', 'le doy el', 'le doy mi',
            'le paso un', 'le paso el', 'le paso mi',
            'le mando un', 'le mando el', 'le mando mi',
            'aquí le va', 'aqui le va', 'ahí le va', 'ahi le va',
            'tome nota', 'apunte', 'anote',
            # FIX 627: BRUCE2061 - "te paso su número" no estaba en la lista
            # Causaba que FIX 510 (PIDE_CONTACTO_NIOVAL) ganara por "su número"
            # y Bruce diera SU WhatsApp en vez de aceptar el número ofrecido
            'te paso su', 'le paso su', 'te doy su', 'le doy su',
            'te paso el', 'le paso el', 'te doy el', 'le doy el',
            'te puedo pasar', 'le puedo pasar', 'te puedo dar', 'le puedo dar',
            'quieres que te pase', 'quiere que le pase',
            'quieres que te dé', 'quiere que le dé',
            'quieres que te de', 'quiere que le de',
        ]
        contexto_contacto_621 = any(w in texto_lower for w in [
            'correo', 'email', 'mail', 'número', 'numero', 'teléfono', 'telefono', 'cel', 'whatsapp'
        ])
        if any(p in texto_lower for p in indicadores_cliente_ofrece_621) and contexto_contacto_621:
            print(f"   FIX 621A: BRUCE2051 - Cliente OFRECE su contacto: '{texto_cliente[:60]}'")
            if any(w in texto_lower for w in ['correo', 'email', 'mail']):
                self.estado_conversacion = EstadoConversacion.DICTANDO_CORREO
                return {
                    "tipo": "CLIENTE_OFRECE_CORREO",
                    "respuesta": "Sí, claro, dígame su correo por favor.",
                    "accion": "ESPERAR_CORREO"
                }
            else:
                self.estado_conversacion = EstadoConversacion.DICTANDO_NUMERO
                return {
                    "tipo": "CLIENTE_OFRECE_NUMERO",
                    "respuesta": "Sí, claro, dígame el número por favor.",
                    "accion": "ESPERAR_NUMERO"
                }

        # FIX 628: BRUCE2062 - Patrones auto-suficientes (no necesitan contact word)
        # Problema: "¿Quieres que te pase su" se truncó sin "teléfono" → no matcheó
        # porque contexto_contacto_621 requería "teléfono/número/correo" que fue cortado
        # Solución: Patrones que terminan en posesivo "su" ya implican oferta de contacto
        # "te paso su" / "quieres que te pase su" → solo puede ser teléfono/número/correo
        patrones_ofrece_autosuficientes_628 = [
            'quieres que te pase su', 'quiere que le pase su',
            'quieres que te dé su', 'quiere que le dé su',
            'quieres que te de su', 'quiere que le de su',
            'te paso su', 'le paso su', 'te doy su', 'le doy su',
            'te puedo pasar su', 'le puedo pasar su',
            'te puedo dar su', 'le puedo dar su',
        ]
        if any(p in texto_lower for p in patrones_ofrece_autosuficientes_628):
            print(f"   FIX 628: BRUCE2062 - Oferta contacto auto-suficiente (sin contact word): '{texto_cliente[:60]}'")
            self.estado_conversacion = EstadoConversacion.DICTANDO_NUMERO
            return {
                "tipo": "CLIENTE_OFRECE_NUMERO",
                "respuesta": "Sí, claro, dígame el número por favor.",
                "accion": "ESPERAR_NUMERO"
            }

        # FIX 510: BRUCE1540 - Cliente pide el contacto de NIOVAL
        # Caso: "Entonces, ¿Cómo se encuentra? Démelo." → Bruce NO dio el contacto
        # Cliente está pidiendo que Bruce le dé SU número de contacto
        # FIX 518b BRUCE1647: Agregar patrones tolerantes a transcripciones parciales
        # FIX 515 BRUCE1733: Agregar "¿Qué número es?" y variantes - cliente pregunta por el número
        if any(p in texto_lower for p in [
            # FIX 515 BRUCE1733: Cliente pregunta qué número es
            "qué número es", "que numero es", "qué número", "que numero",
            "cuál número", "cual numero", "qué números", "que numeros",
            "me da su número", "me das tu número", "me da tu número",
            "me das su número", "me das tu numero", "me da su numero",
            # Variantes con "perdón" / clarificación
            "qué número es, perdón", "que numero es perdon",
            "perdón qué número", "perdon que numero",
            "démelo", "damelo", "dámelo",  # "Démelo" - pidiendo el número
            "me lo da", "me lo das", "me lo puede dar",
            "pásame el número", "pasame el numero", "páseme el número", "paseme el numero",
            "dame tu número", "dame su número", "deme su número",
            "cuál es su número", "cual es su numero", "cuál es tu número", "cual es tu numero",
            "cuál es el whatsapp", "cual es el whatsapp",
            "cuál es el teléfono", "cual es el telefono",
            "me das el número", "me da el número",
            "su contacto", "tu contacto", "el contacto",
            "cómo los contacto", "como los contacto",
            "número para llamar", "numero para llamar",
            "a qué número", "a que numero",
            # FIX 518b: Patrones parciales para transcripciones incompletas de Deepgram
            # Ej: "si gusta mejor deme" = cliente pide el número de NIOVAL
            "mejor deme", "mejor déme", "mejor dame",
            "si gusta deme", "si gusta déme", "si gusta dame",
            "gusta deme", "gusta déme",  # transcripción parcial sin "si"
            "pero deme", "pero déme", "pero dame",
            "deme el", "déme el", "dame el",  # "déme el número"
            "deme su", "déme su", "dame su",  # "déme su número"
            "mejor el suyo", "deme el suyo", "el de ustedes",
            # FIX 518c: Más variantes para transcripciones parciales
            # Variantes con "pasa/pase/paso"
            "páselo", "paselo", "pásalo", "pasalo", "pásemelo", "pasemelo",
            "me lo pasa", "me lo pasas", "pásame", "pasame",
            # Variantes con "diga/dice/dime"
            "dígame el", "digame el", "dime el", "dígamelo", "digamelo", "dímelo", "dimelo",
            "me lo dice", "me lo dices", "a ver dime", "a ver dígame", "a ver digame",
            # Variantes con "anoto/apunto" (cliente va a anotar)
            "lo anoto", "anoto", "lo apunto", "apunto", "déjame anotar", "dejame anotar",
            "espere anoto", "espera anoto", "deje anoto", "deja anoto",
            # Variantes con "dicta/repite"
            "díctame", "dictame", "dícteme", "dicteme", "dicta el", "dicte el",
            "repítelo", "repitelo", "repítalo", "repitalo", "repítame", "repitame",
            # Variantes con interjecciones mexicanas
            "órale deme", "orale deme", "ándale deme", "andale deme",
            "va deme", "sale deme", "bueno deme", "bueno dame",
            "pues deme", "pues dame", "entonces deme", "entonces dame",
            "sí deme", "si deme", "ok deme", "okay deme",
            # Variantes preguntando por WhatsApp/teléfono de NIOVAL
            "tienes whatsapp", "tiene whatsapp", "tienen whatsapp",
            "tienes número", "tiene número", "tienen número",
            "cuál sería", "cual seria", "cuál es", "cual es",
            "y su número", "y tu número", "y el número", "y el whatsapp",
            # Variantes con "déjame/déjeme"
            "déjame el", "dejame el", "déjeme el", "dejeme el",
            "déjame su", "dejame su", "déjeme su", "dejeme su",
            # Variantes para cuando dicen "el tuyo/suyo"
            "el tuyo", "el suyo", "el de usted", "tu número", "su número",
            "me pasas el tuyo", "me pasa el suyo",
            # Variantes parciales comunes de Deepgram
            "número de", "el número", "un número", "algún número", "algun numero",
            "para contactar", "para llamar", "para comunicar",
            "cómo te llamo", "como te llamo", "cómo le llamo", "como le llamo",
            "a dónde llamo", "a donde llamo", "dónde les llamo", "donde les llamo",
            # FIX 740: BRUCE2311 - "Me pasas tus datos" = pide contacto de Bruce/Nioval
            "me pasas tus datos", "pasame tus datos", "me das tus datos",
            "dame tus datos", "tus datos por favor", "sus datos por favor",
            "me pasa sus datos", "me da sus datos", "paseme sus datos"
        ]):
            print(f"[OK] FIX 510: Cliente pide contacto de NIOVAL - dando WhatsApp")
            return {
                "tipo": "PIDE_CONTACTO_NIOVAL",
                "respuesta": "Claro, nuestro WhatsApp es 6 6 2, 4 1 5, 1 9 9 7 y nuestro correo es ventas arroba nioval punto com. Con gusto le atendemos.",
                "accion": "DAR_CONTACTO"
            }

        # 1. DESPEDIDAS (no necesita GPT)
        # FIX 629A: BRUCE2063 - "Hasta luego, oiga, Hasta luego indra." (38 chars) no matcheaba con < 30
        # Separar despedidas fuertes (toleran más texto) de débiles (necesitan contexto corto)
        despedidas_fuertes = ["adios", "hasta luego", "bye", "nos vemos"]
        # FIX 646B: BRUCE2080 - "Ya todo" es expresión mexicana = despedida/fin conversación
        # IMPORTANTE: Sin acentos porque FIX 631 normaliza texto_lower
        despedidas_debiles = ["gracias", "lo reviso", "lo checo", "ya todo", "ya esta todo", "ya es todo"]
        es_despedida_fuerte = any(d in texto_lower for d in despedidas_fuertes) and len(texto_lower.split()) <= 10
        es_despedida_debil = any(d in texto_lower for d in despedidas_debiles) and len(texto_lower) < 30
        # Si catálogo ya prometido, cualquier despedida es válida (tolerancia máxima)
        es_despedida_post_catalogo = self.catalogo_prometido and any(d in texto_lower for d in despedidas_fuertes + despedidas_debiles)
        if es_despedida_fuerte or es_despedida_debil or es_despedida_post_catalogo:
            return {
                "tipo": "DESPEDIDA_CLIENTE",
                "respuesta": "Muchas gracias por su tiempo. Que tenga excelente día.",
                "accion": "TERMINAR_LLAMADA"
            }

        # FIX 648: BRUCE2112, BRUCE2111 - CLIENTE_HABLA_ULTIMO
        # Cliente da cierre natural pero Bruce NO responde → ghostea al cliente
        # "No hay ahorita" / "Habla a otra sucursal" → Bruce debe cerrar apropiadamente
        # FIX 654: BRUCE2120 - Agregar patrones corteses mexicanos de rechazo
        patrones_cierre_natural = [
            "no hay ahorita", "no hay en esta hora", "no hay nadie",
            "tienes que hablar a", "tiene que llamar a", "contacta a",
            "habla a la sucursal", "marca a la sucursal", "llama a la sucursal",
            "no hay encargado", "no tenemos encargado",
            "solo soy yo", "yo nada mas", "yo solo", "estoy solo", "estoy sola",
            # FIX 654: Patrones corteses mexicanos (rechazo implícito)
            "no muchacho", "no muchachito", "no joven", "no jovencito",
            "no gracias joven", "no gracias muchacho", "no gracias muchachito"
        ]

        if any(p in texto_lower for p in patrones_cierre_natural):
            print(f"   FIX 648: Detectado cierre natural del cliente")
            if any(p in texto_lower for p in ["otra sucursal", "habla a", "tiene que llamar", "tienes que hablar"]):
                return {
                    "tipo": "DESPEDIDA_NATURAL_CLIENTE_DERIVACION",
                    "respuesta": "Perfecto, voy a contactar a esa sucursal entonces. Muchas gracias por su ayuda, que tenga excelente día.",
                    "accion": "TERMINAR_LLAMADA"
                }
            return {
                "tipo": "DESPEDIDA_NATURAL_CLIENTE_NO_DISPONIBLE",
                "respuesta": "Perfecto, entonces le marco más tarde cuando esté disponible. Muchas gracias, que tenga buen día.",
                "accion": "TERMINAR_LLAMADA"
            }

        # 2. CONFIRMACIONES SIMPLES (no necesita GPT)
        # FIX 522 BRUCE1659: Incluir "ándale" y variantes mexicanas
        if texto_lower in ["ok", "okay", "sale", "va", "sí", "si", "claro", "ajá", "aja",
                           "ándale", "andale", "órale", "orale", "ok ándale", "ok andale"]:
            # FIX 522: Si ya se prometió el catálogo, despedirse
            if self.catalogo_prometido:
                print(f"   FIX 522: Confirmación simple + catálogo ya prometido - Despedirse")
                return {
                    "tipo": "CONFIRMACION_CATALOGO_PROMETIDO",
                    "respuesta": "Perfecto, le envío el catálogo entonces. Muchas gracias por su tiempo, que tenga excelente día.",
                    "accion": "TERMINAR_LLAMADA"
                }
            return {
                "tipo": "CONFIRMACION_SIMPLE",
                "respuesta": "Perfecto, adelante por favor.",
                "accion": "ESPERAR_DATO"
            }

        # 3. SALUDOS INICIALES (no necesita GPT)
        # FIX 524 BRUCE1669: NO tratar como saludo si contiene números (cliente dictando + "¿Bueno?")
        saludos = ["hola", "bueno", "buenos días", "buenos dias", "buenas tardes", "diga", "sí dígame", "si digame"]
        tiene_digitos = bool(re.search(r'\d', texto_lower))

        # FIX 527 BRUCE1694: "¿Bueno?" sin números DESPUÉS de que Bruce ya habló = verificación de conexión
        # NO debe responder "Hola, buen día" sino "Sí, aquí estoy"
        # FIX 530: BRUCE1803 - Agregar variantes repetidas como "¿bueno, bueno?" o "bueno bueno"
        verificaciones_conexion_exactas = [
            "bueno", "¿bueno?", "bueno?", "hola", "¿hola?", "hola?", "oye", "¿oye?",
            # FIX 530: Variantes repetidas cuando cliente verifica que siguen en línea
            "bueno bueno", "¿bueno? ¿bueno?", "bueno, bueno", "¿bueno, bueno?",
            "hola hola", "¿hola? ¿hola?", "hola, hola"
        ]
        verificacion_conexion = texto_lower.strip().rstrip('.,;:!?¿¡') in verificaciones_conexion_exactas or \
                               texto_lower.strip() in verificaciones_conexion_exactas

        if verificacion_conexion and not tiene_digitos:
            if self.estado_conversacion != EstadoConversacion.INICIO:
                # FIX 604: Si es primer turno real (cliente dice "¿Bueno?" al inicio),
                # ir directo al pitch en vez de "¿Me decía?" pasivo
                mensajes_usuario_604 = [msg for msg in self.conversation_history if msg['role'] == 'user'
                                        and '[Timeout' not in msg.get('content', '')]
                es_inicio_604 = len(mensajes_usuario_604) <= 1

                if es_inicio_604:
                    # FIX 689: BRUCE2193 - No repetir pitch completo si ya se presentó
                    ya_presento_689 = any('nioval' in msg.get('content', '').lower()
                                          for msg in self.conversation_history if msg['role'] == 'assistant')
                    if ya_presento_689:
                        print(f"   FIX 689: '¿Bueno?' pero ya presentó NIOVAL → NO repetir pitch, usar FIX 621B")
                        # Fall through a FIX 621B (repetir pregunta) en vez de repetir pitch completo
                        pass
                    else:
                        print(f"   FIX 604: '¿Bueno?' en primer turno → pitch directo en vez de '¿Me decía?'")
                        return {
                            "tipo": "VERIFICACION_CONEXION_INICIO",
                            "respuesta": "Sí, le comento, me comunico de la marca NIOVAL, más que nada quería brindar información de nuestros productos ferreteros, ¿se encontrará el encargado o encargada de compras?",
                            "accion": "AVANZAR_A_PRESENTACION"
                        }

                # FIX 621B: BRUCE2049 - Si Bruce acabó de hacer una PREGUNTA y cliente dice "diga"/"bueno",
                # NO responder "¿Me decía?" sino REPETIR la pregunta de Bruce
                # Caso: Bruce: "¿Se encontrará el encargado?" → Cliente: "Diga." → Bruce: "¿Me decía?" (MAL)
                # Correcto: Bruce: "Le preguntaba, ¿se encontrará el encargado de compras?"
                ultimo_bruce_621b = None
                for msg in reversed(self.conversation_history):
                    if msg['role'] == 'assistant':
                        ultimo_bruce_621b = msg.get('content', '')
                        break
                if ultimo_bruce_621b and ultimo_bruce_621b.strip().endswith('?'):
                    # FIX 745: BRUCE2370 - Anti-recursive garble
                    # Si último msg de Bruce ya empieza con "Sí, le preguntaba", NO envolver de nuevo
                    # Causa recursión: "Sí, le preguntaba, ¿le preguntaba, ¿...?"
                    _ub_lower_745 = ultimo_bruce_621b.strip().lower()
                    if _ub_lower_745.startswith('sí, le preguntaba') or _ub_lower_745.startswith('si, le preguntaba'):
                        print(f"   FIX 745: BRUCE2370 - Anti-recursive: último Bruce ya era 'le preguntaba' → fallback limpio")
                        return {
                            "tipo": "VERIFICACION_CONEXION",
                            "respuesta": "Sí, aquí estoy. Dígame.",
                            "accion": "CONTINUAR_CONVERSACION"
                        }
                    # Extraer la última pregunta (después del último punto)
                    partes_621b = re.split(r'[.!]\s+', ultimo_bruce_621b)
                    ultima_pregunta_621b = partes_621b[-1].strip() if partes_621b else ultimo_bruce_621b.strip()
                    # FIX 624: BRUCE2045 - Si la extracción es muy larga, buscar último ¿
                    # Problema: Pitch "Me comunico..., ¿Se encontrará el encargado?" usa comas,
                    # no puntos, entonces split por [.!] NO separa → 157 chars > 120 → fallaba
                    if len(ultima_pregunta_621b) > 120:
                        idx_pregunta_624 = ultimo_bruce_621b.rfind('¿')
                        if idx_pregunta_624 >= 0:
                            ultima_pregunta_621b = ultimo_bruce_621b[idx_pregunta_624:].strip()
                            print(f"   FIX 624: Pregunta extraída con ¿: '{ultima_pregunta_621b[:80]}'")
                    # Asegurar que la pregunta no sea demasiado larga
                    if len(ultima_pregunta_621b) <= 120:
                        # Quitar ¿ inicial si existe para concatenar con "le preguntaba,"
                        pregunta_limpia_621b = ultima_pregunta_621b.lstrip('¿').strip()
                        pregunta_limpia_621b = pregunta_limpia_621b[0].lower() + pregunta_limpia_621b[1:] if pregunta_limpia_621b else pregunta_limpia_621b
                        respuesta_621b = f"Sí, le preguntaba, ¿{pregunta_limpia_621b}"
                        if not respuesta_621b.endswith('?'):
                            respuesta_621b += '?'
                        print(f"   FIX 621B: BRUCE2049 - Bruce hizo pregunta → repetir: '{respuesta_621b[:60]}'")
                        return {
                            "tipo": "VERIFICACION_CONEXION_REPETIR_PREGUNTA",
                            "respuesta": respuesta_621b,
                            "accion": "CONTINUAR_CONVERSACION"
                        }

                # Ya pasamos del inicio - cliente verifica que seguimos en línea
                print(f"   FIX 527: Cliente verifica conexión ('{texto_lower}') - NO es saludo inicial")
                return {
                    "tipo": "VERIFICACION_CONEXION",
                    "respuesta": "Sí, aquí estoy. ¿Me decía?",
                    "accion": "CONTINUAR_CONVERSACION"
                }

        # FIX 711A: BRUCE2255 - "Dígame" NO es "Diga". "diga" substring matchea "digame"
        # pero son cosas diferentes: "Diga" = "hello?" vs "Dígame" = "go ahead, tell me"
        # Si texto es "digame"/"digame." NO debe tratarse como saludo/verificación
        texto_stripped_711 = texto_lower.strip().rstrip('.,;:!?¿¡')
        es_digame_711 = texto_stripped_711 in ['digame', 'si digame', 'si, digame']
        if es_digame_711:
            # "Dígame" = cliente dice "adelante, cuénteme" → responder con pitch o continuar
            print(f"   FIX 711A: BRUCE2255 - 'Dígame' = go ahead (NO es 'Diga' verificación)")
            historial_avanzado_711 = len(self.conversation_history) >= 4
            if historial_avanzado_711:
                # Ya dio pitch → cliente dice "dígame" = escucha activa, continuar
                # NO repetir pregunta de encargado - dar info o preguntar por encargado naturalmente
                ya_pregunto_encargado_711 = any(
                    'encargado' in msg.get('content', '').lower()
                    for msg in self.conversation_history if msg['role'] == 'assistant'
                )
                if ya_pregunto_encargado_711:
                    print(f"   FIX 711A: Ya preguntó encargado + Dígame = cliente escucha → dar pitch corto")
                    return {
                        "tipo": "DIGAME_CONTINUAR",
                        "respuesta": "Sí, le comento, manejamos productos de ferretería de la marca NIOVAL: cintas tapagoteras, grifería, herramientas y más de 15 categorías. ¿Con quién podría platicar sobre las compras?",
                        "accion": "PITCH_CORTO"
                    }
                return {
                    "tipo": "DIGAME_ADELANTE",
                    "respuesta": "Sí, le comento, manejamos productos de ferretería de la marca NIOVAL. ¿Se encontrará el encargado o encargada de compras?",
                    "accion": "AVANZAR_CONVERSACION"
                }
            # Inicio de conversación → dar pitch
            return {
                "tipo": "DIGAME_INICIO",
                "respuesta": "Sí, le comento, me comunico de la marca NIOVAL, más que nada quería brindar información de nuestros productos ferreteros. ¿Se encontrará el encargado o encargada de compras?",
                "accion": "AVANZAR_A_PRESENTACION"
            }

        if any(s in texto_lower for s in saludos) and len(texto_lower) < 20 and not tiene_digitos:
            # FIX 535: SOLO responder "Hola, buen día" si NUNCA hemos avanzado de INICIO
            # Previene pérdida de contexto después de silencios (BRUCE1665)
            # FIX 535b: BRUCE1821 - También verificar tamaño del historial
            # Si conversation_history >= 4, significa que Bruce ya habló presentación
            # Cliente dijo "Diga." interrumpiendo = NO es saludo inicial, es verificación
            historial_avanzado = len(self.conversation_history) >= 4
            if historial_avanzado:
                print(f"   FIX 535b: BRUCE1821 - Historial tiene {len(self.conversation_history)} mensajes - NO es saludo inicial")
                # FIX 621B: BRUCE2049 - Si Bruce hizo pregunta, repetirla en vez de "¿Me decía?"
                ultimo_bruce_535b = None
                for msg in reversed(self.conversation_history):
                    if msg['role'] == 'assistant':
                        ultimo_bruce_535b = msg.get('content', '')
                        break
                if ultimo_bruce_535b and ultimo_bruce_535b.strip().endswith('?'):
                    # FIX 745: BRUCE2370 - Anti-recursive garble (copia 535b)
                    _ub_lower_745b = ultimo_bruce_535b.strip().lower()
                    if _ub_lower_745b.startswith('sí, le preguntaba') or _ub_lower_745b.startswith('si, le preguntaba'):
                        print(f"   FIX 745: Anti-recursive (535b): último Bruce ya era 'le preguntaba' → fallback limpio")
                        return {
                            "tipo": "VERIFICACION_CONEXION",
                            "respuesta": "Sí, aquí estoy. Dígame.",
                            "accion": "CONTINUAR_CONVERSACION"
                        }
                    partes_535b = re.split(r'[.!]\s+', ultimo_bruce_535b)
                    ultima_pregunta_535b = partes_535b[-1].strip() if partes_535b else ultimo_bruce_535b.strip()
                    # FIX 624: BRUCE2045 - Si es muy larga, buscar último ¿
                    if len(ultima_pregunta_535b) > 120:
                        idx_624 = ultimo_bruce_535b.rfind('¿')
                        if idx_624 >= 0:
                            ultima_pregunta_535b = ultimo_bruce_535b[idx_624:].strip()
                            print(f"   FIX 624: Pregunta extraída con ¿: '{ultima_pregunta_535b[:80]}'")
                    if len(ultima_pregunta_535b) <= 120:
                        pregunta_limpia_535b = ultima_pregunta_535b.lstrip('¿').strip()
                        pregunta_limpia_535b = pregunta_limpia_535b[0].lower() + pregunta_limpia_535b[1:] if pregunta_limpia_535b else pregunta_limpia_535b
                        respuesta_535b = f"Sí, le preguntaba, ¿{pregunta_limpia_535b}"
                        if not respuesta_535b.endswith('?'):
                            respuesta_535b += '?'
                        print(f"   FIX 621B: Bruce hizo pregunta → repetir: '{respuesta_535b[:60]}'")
                        return {
                            "tipo": "VERIFICACION_CONEXION_REPETIR_PREGUNTA",
                            "respuesta": respuesta_535b,
                            "accion": "CONTINUAR_CONVERSACION"
                        }
                return {
                    "tipo": "VERIFICACION_CONEXION",
                    "respuesta": "Sí, aquí estoy. ¿Me decía?",
                    "accion": "CONTINUAR_CONVERSACION"
                }
            if self.estado_conversacion == EstadoConversacion.INICIO and not self.conversacion_iniciada:
                # FIX 535: Marcar que la conversación ya inició
                self.conversacion_iniciada = True
                return {
                    "tipo": "SALUDO_INICIAL",
                    "respuesta": "Hola, buen día.",
                    "accion": "AVANZAR_A_PRESENTACION"
                }
            elif self.conversacion_iniciada:
                # FIX 535: Conversación ya iniciada - responder como verificación de conexión
                print(f"   FIX 535: Conversación ya iniciada - NO repetir saludo inicial")
                return {
                    "tipo": "VERIFICACION_CONEXION",
                    "respuesta": "Sí, aquí estoy. ¿Me decía?",
                    "accion": "CONTINUAR_CONVERSACION"
                }

        # FIX 524 BRUCE1669: Si tiene números + "¿Bueno?", cliente verifica conexión mientras dicta
        if tiene_digitos and ("bueno" in texto_lower or "¿bueno?" in texto_lower):
            digitos = re.findall(r'\d', texto_lower)
            num_digitos = len(digitos)
            print(f"   FIX 524: Cliente dictando número ({num_digitos} dígitos) + verificando conexión")

            if num_digitos < 10:
                # Número incompleto - pedir el resto
                return {
                    "tipo": "NUMERO_PARCIAL_CON_VERIFICACION",
                    "respuesta": f"Sí, aquí estoy. Llevo anotados {num_digitos} dígitos. ¿Me puede dar el número completo?",
                    "accion": "PEDIR_NUMERO_COMPLETO"
                }
            else:
                # Número completo - confirmar
                numero_str = ''.join(digitos[:10])
                numero_formateado = f"{numero_str[0:3]}-{numero_str[3:6]}-{numero_str[6:8]}-{numero_str[8:10]}"
                return {
                    "tipo": "NUMERO_COMPLETO_CON_VERIFICACION",
                    "respuesta": f"Sí, aquí estoy. Tengo anotado {numero_formateado}, ¿es correcto?",
                    "accion": "CONFIRMAR_NUMERO"
                }

        # FIX 526 BRUCE1677: Si esperamos hora y cliente da números, interpretar como hora
        # FIX 533 BRUCE1665: También manejar respuestas de horario SIN dígitos ("por la tarde", "en la mañana")
        if self.esperando_hora_callback:
            # Patrones de horario sin necesidad de dígitos explícitos
            patrones_horario_sin_digitos = [
                'por la tarde', 'en la tarde', 'la tarde', 'tarde',
                'por la mañana', 'en la mañana', 'la mañana', 'mañana', 'manana',
                'por la noche', 'en la noche', 'la noche', 'noche',
                'después de', 'despues de', 'como a las', 'como las',
                'a partir de', 'después del', 'despues del',
                'en un rato', 'más tarde', 'mas tarde', 'al rato',
                'después de comer', 'despues de comer', 'hora de comida',
                'medio día', 'medio dia', 'mediodía', 'mediodia',
                'sería por la', 'seria por la', 'sería en la', 'seria en la',
                # FIX 533: "como a las 5" tiene número pero el patrón clave es "como a las"
                'a las', 'las'
            ]

            tiene_patron_horario = any(p in texto_lower for p in patrones_horario_sin_digitos)

            if tiene_digitos or tiene_patron_horario:
                digitos = re.findall(r'\d', texto_lower)
                print(f"   FIX 526/533: esperando_hora_callback=True + horario detectado (dígitos={digitos}, patrón={tiene_patron_horario})")

                # Reset flag
                self.esperando_hora_callback = False

                # Detectar patrones comunes de hora para personalizar respuesta
                hora_texto = texto_lower
                if any(h in hora_texto for h in ['mañana', 'manana']):
                    return {
                        "tipo": "HORA_CALLBACK_CONFIRMADA",
                        "respuesta": "Perfecto, entonces le llamo por la mañana. Muchas gracias por su tiempo.",
                        "accion": "CONFIRMAR_CALLBACK"
                    }
                elif any(h in hora_texto for h in ['tarde']):
                    return {
                        "tipo": "HORA_CALLBACK_CONFIRMADA",
                        "respuesta": "Perfecto, entonces le llamo por la tarde. Muchas gracias por su tiempo.",
                        "accion": "CONFIRMAR_CALLBACK"
                    }
                elif any(h in hora_texto for h in ['noche']):
                    return {
                        "tipo": "HORA_CALLBACK_CONFIRMADA",
                        "respuesta": "Perfecto, entonces le llamo por la noche. Muchas gracias por su tiempo.",
                        "accion": "CONFIRMAR_CALLBACK"
                    }
                else:
                    # Respuesta genérica con la hora si se detectó
                    if digitos:
                        hora_num = ''.join(digitos[:2])  # Tomar primeros 2 dígitos como hora
                        return {
                            "tipo": "HORA_CALLBACK_CONFIRMADA",
                            "respuesta": f"Perfecto, entonces le llamo a las {hora_num}. Muchas gracias por su tiempo.",
                            "accion": "CONFIRMAR_CALLBACK"
                        }
                    else:
                        return {
                            "tipo": "HORA_CALLBACK_CONFIRMADA",
                            "respuesta": "Perfecto, le llamo más tarde entonces. Muchas gracias por su tiempo.",
                            "accion": "CONFIRMAR_CALLBACK"
                        }

        # 4. TRANSFERENCIAS (no necesita GPT)
        # FIX 562: Excluir "te/le paso el correo/número" - eso es DAR info, no transferir
        info_keywords_562 = ["correo", "email", "mail", "número", "numero", "teléfono", "telefono", "whatsapp", "catálogo", "catalogo"]
        es_dar_info_562 = any(k in texto_lower for k in info_keywords_562)
        transferencias = ["espere", "le paso", "ahorita le comunico", "permítame", "permitame"]
        if any(t in texto_lower for t in transferencias) and len(texto_lower) < 40 and not es_dar_info_562:
            return {
                "tipo": "TRANSFERENCIA",
                "respuesta": "Perfecto, muchas gracias por comunicarme.",
                "accion": "ESPERAR_TRANSFERENCIA"
            }

        # FIX 523 BRUCE1661: Cliente ofrece dar correo/número
        # Caso: "¿Tiene para anotar un correo?" = cliente quiere DAR su correo
        # FIX 690A: BRUCE2202 - "tienes con que anotar" / "tienes lapiz" / "tienes papel"
        if any(p in texto_lower for p in [
            "tiene para anotar", "tienes para anotar",
            "tiene donde anotar", "tienes donde anotar",
            "tiene dónde anotar", "tienes dónde anotar",
            "puede anotar", "puedes anotar",
            # FIX 690A: Variantes adicionales de "¿tienes donde anotar?"
            "tiene con que anotar", "tienes con que anotar",
            "tiene con qué anotar", "tienes con qué anotar",
            "tiene lapiz", "tienes lapiz", "tiene lápiz", "tienes lápiz",
            "tiene papel", "tienes papel", "tiene pluma", "tienes pluma",
            "tienes donde apuntar", "tiene donde apuntar",
            "tienes para apuntar", "tiene para apuntar",
            "puede apuntar", "puedes apuntar",
            "le doy un correo", "le doy mi correo", "le doy el correo",
            "le doy un número", "le doy mi número", "le doy el número",
            "le paso un correo", "le paso mi correo",
            "le paso un número", "le paso mi número",
            "anote un correo", "anota un correo", "anote el correo",
            "anote un número", "anota un número", "anote el número"
        ]):
            print(f"   FIX 523: Cliente OFRECE dar correo/número - aceptar")
            # Detectar si es correo o número
            if "correo" in texto_lower or "email" in texto_lower or "mail" in texto_lower:
                self.estado_conversacion = EstadoConversacion.DICTANDO_CORREO
                return {
                    "tipo": "CLIENTE_OFRECE_CORREO",
                    "respuesta": "Sí, claro, dígame su correo por favor.",
                    "accion": "ESPERAR_CORREO"
                }
            else:
                self.estado_conversacion = EstadoConversacion.DICTANDO_NUMERO
                return {
                    "tipo": "CLIENTE_OFRECE_NUMERO",
                    "respuesta": "Sí, claro, dígame el número por favor.",
                    "accion": "ESPERAR_NUMERO"
                }

        # 5. WHATSAPP DETECTADO (regex, no necesita GPT)
        # FIX 617D: Convertir números escritos a dígitos antes del regex
        # Problema análogo a FIX 617B: si STT transcribe "tres tres uno..." como palabras,
        # el regex \d{10} no matchea. Aplicar convertir_numeros_escritos_a_digitos primero.
        texto_numeros_617 = convertir_numeros_escritos_a_digitos(texto_cliente)
        whatsapp_regex = r'\b\d{10}\b|\b\d{3}[\s-]?\d{3}[\s-]?\d{4}\b'
        match_whatsapp = re.search(whatsapp_regex, texto_numeros_617)
        if not match_whatsapp:
            # También intentar con texto original (por si ya tiene dígitos)
            match_whatsapp = re.search(whatsapp_regex, texto_cliente)
        if match_whatsapp:
            numero = re.sub(r'[^\d]', '', match_whatsapp.group())[:10]
            return {
                "tipo": "WHATSAPP_DETECTADO",
                "respuesta": f"Perfecto, ya lo tengo. Le envío el catálogo en las próximas horas. Muchas gracias.",
                "accion": "GUARDAR_WHATSAPP",
                "dato": numero
            }

        # 6. CORREO DETECTADO (regex, no necesita GPT)
        # FIX 617B: BRUCE2032 - Convertir "arroba"→"@", "punto com"→".com" antes del regex
        # Problema: STT transcribe "arroba" como texto, no como "@" → regex no matchea
        texto_email_617 = texto_cliente
        texto_email_617 = re.sub(r'\b(arroba|aroba|a roba)\b', '@', texto_email_617, flags=re.IGNORECASE)
        texto_email_617 = re.sub(r'\bpunto\s*com\b', '.com', texto_email_617, flags=re.IGNORECASE)
        texto_email_617 = re.sub(r'\bpunto\s*mx\b', '.mx', texto_email_617, flags=re.IGNORECASE)
        texto_email_617 = re.sub(r'\bpunto\s*net\b', '.net', texto_email_617, flags=re.IGNORECASE)
        texto_email_617 = re.sub(r'\bpunto\s*org\b', '.org', texto_email_617, flags=re.IGNORECASE)
        # Eliminar espacios alrededor de @ y . en contexto email
        texto_email_617 = re.sub(r'\s*@\s*', '@', texto_email_617)
        # Eliminar espacios entre partes del email (ej: "luis garcia @ gmail .com" → "luisgarcia@gmail.com")
        # Solo si ya tiene @ (confirmamos que hay email)
        if '@' in texto_email_617:
            # Extraer la parte del texto que parece email (buscar palabras alrededor del @)
            match_zona_email = re.search(r'(\S+(?:\s+\S+){0,4})\s*@\s*(\S+(?:\s+\S+){0,2})', texto_email_617)
            if match_zona_email:
                pre_at = match_zona_email.group(1).replace(' ', '').lower()
                post_at = match_zona_email.group(2).replace(' ', '').lower()
                email_reconstruido = f"{pre_at}@{post_at}"
                # Limpiar puntos duplicados
                email_reconstruido = re.sub(r'\.+', '.', email_reconstruido)
                # Verificar que parece email válido
                email_regex_check = r'^[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}$'
                if re.match(email_regex_check, email_reconstruido):
                    print(f"   FIX 617B: Email reconstruido de dictado: '{email_reconstruido}'")
                    return {
                        "tipo": "CORREO_DETECTADO",
                        "respuesta": "Perfecto, ya lo tengo anotado. Le envío el catálogo en las próximas horas. Muchas gracias.",
                        "accion": "GUARDAR_CORREO",
                        "dato": email_reconstruido
                    }

        email_regex = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        match_email = re.search(email_regex, texto_cliente)
        if match_email:
            correo = match_email.group()
            return {
                "tipo": "CORREO_DETECTADO",
                "respuesta": "Perfecto, ya lo tengo anotado. Le envío el catálogo en las próximas horas. Muchas gracias.",
                "accion": "GUARDAR_CORREO",
                "dato": correo
            }

        # ================================================================
        # FIX 521: BRUCE1744 - Confirmación INSTANTÁNEA de números dictados
        # Problema: GPT tardó 10+ segundos cuando cliente dictó número
        # Solución: Si hay 7+ dígitos (número parcial/completo), confirmar SIN GPT
        # FIX 617D: Usar texto_numeros_617 (ya convertido arriba) para contar dígitos
        # ================================================================
        digitos_en_texto = re.findall(r'\d', texto_numeros_617)
        num_digitos = len(digitos_en_texto)

        if num_digitos >= 7:
            # Construir número para mostrar
            numero_capturado = ''.join(digitos_en_texto)
            print(f"[OK] FIX 521: NÚMERO DICTADO detectado ({num_digitos} dígitos): {numero_capturado}")

            # FIX 623B: BRUCE2041 - Reconstruir número con dígitos del turno anterior
            # Problema: Cliente dictó "6621" (turno anterior) + "201020 6620" (turno actual)
            # FIX 469 concatenó SOLO el turno actual → "2010206620" (INCORRECTO)
            # El número real era "6621201020" (6621 del turno anterior + 201020 continuación)
            # Solución: Si hay dígitos preservados, intentar reconstruir el número correcto
            digitos_previos_623 = getattr(self, 'digitos_preservados_previos', '')
            if digitos_previos_623 and num_digitos >= 10:
                print(f"   FIX 623B: Dígitos previos del turno anterior: '{digitos_previos_623}'")
                # Caso 1: El número actual EMPIEZA con los dígitos previos
                # → Cliente repitió desde el inicio → usar número actual (es completo)
                if numero_capturado.startswith(digitos_previos_623):
                    print(f"   FIX 623B: Número actual YA incluye dígitos previos (cliente repitió) → usar actual")
                    # Limpiar dígitos previos
                    self.digitos_preservados_previos = ''
                else:
                    # Caso 2: El número actual NO empieza con los dígitos previos
                    # → Cliente CONTINUÓ desde donde quedó + posiblemente repitió inicio
                    # Intentar: previos + primeros (10-len(previos)) dígitos del actual
                    digitos_necesarios = 10 - len(digitos_previos_623)
                    if 0 < digitos_necesarios < num_digitos:
                        candidato_623 = digitos_previos_623 + numero_capturado[:digitos_necesarios]
                        print(f"   FIX 623B: Número reconstruido: {digitos_previos_623} + {numero_capturado[:digitos_necesarios]} = {candidato_623}")
                        numero_capturado = candidato_623
                        print(f"   FIX 623B: Usando número reconstruido: {numero_capturado}")
                    else:
                        print(f"   FIX 623B: No se puede reconstruir (necesarios={digitos_necesarios}) → usar actual")
                    # Limpiar dígitos previos
                    self.digitos_preservados_previos = ''
            elif digitos_previos_623:
                # Hay dígitos previos pero no tenemos 10+ actuales - limpiar
                self.digitos_preservados_previos = ''

            if num_digitos >= 10:
                # Número completo (10+ dígitos) - confirmar
                numero_final = numero_capturado[:10]
                numero_formateado = f"{numero_final[0:3]} {numero_final[3:6]} {numero_final[6:8]} {numero_final[8:10]}"
                self.lead_data["whatsapp"] = numero_final
                self.estado_conversacion = EstadoConversacion.CONTACTO_CAPTURADO
                return {
                    "tipo": "NUMERO_COMPLETO_DICTADO",
                    "respuesta": "Perfecto, ya lo tengo anotado. Le envío el catálogo en las próximas horas. Muchas gracias por su tiempo.",
                    "accion": "GUARDAR_WHATSAPP",
                    "dato": numero_final
                }
            else:
                # Número parcial (7-9 dígitos) - pedir los que faltan
                digitos_faltantes = 10 - num_digitos
                return {
                    "tipo": "NUMERO_PARCIAL_DICTADO",
                    "respuesta": f"Perfecto, llevo anotados {num_digitos} dígitos. ¿Me puede dar los {digitos_faltantes} que faltan?",
                    "accion": "ESPERAR_NUMERO_COMPLETO"
                }

        # NO hay patrón simple → Necesita GPT
        return None

    def _obtener_respuesta_cache(self, texto_cliente: str):
        """
        FIX 491: Sistema de cache de respuestas frecuentes.
        Latencia: 0.3-0.6s (vs 3.5s de GPT) - Reducción de 83-91%

        Returns:
            str con respuesta cacheada si hay match, None si no
        """
        texto_lower = texto_cliente.lower().strip()

        # ================================================================
        # FIX 493: PROTECCIÓN ANTI-LOOP EN CACHE
        # Si Bruce ya preguntó por encargado 2+ veces, NO volver a preguntar
        # ================================================================
        ultimas_bruce_cache = [
            msg['content'].lower() for msg in self.conversation_history[-6:]
            if msg['role'] == 'assistant'
        ]
        patrones_encargado_cache = [
            'se encontrará el encargado', 'se encontrara el encargado',
            'está el encargado', 'esta el encargado',
            'se encuentra el encargado', 'encargado de compras'
        ]
        veces_pregunto_encargado_cache = sum(
            1 for msg in ultimas_bruce_cache
            if any(p in msg for p in patrones_encargado_cache)
        )
        ya_pregunto_suficiente = veces_pregunto_encargado_cache >= 1  # FIX 692A: alineado con bug detector

        # CACHE DE RESPUESTAS MÁS FRECUENTES (basado en análisis de logs)

        # Pregunta: ¿De dónde?
        if any(p in texto_lower for p in ["de dónde", "de donde", "dónde están", "donde estan", "ubicación", "de qué ciudad", "de que ciudad"]):
            if ya_pregunto_suficiente:
                return "Estamos en Guadalajara, pero hacemos envíos a toda la República. ¿Le envío el catálogo por WhatsApp?"
            return "Estamos en Guadalajara, pero hacemos envíos a toda la República. ¿Se encuentra el encargado?"

        # Pregunta: ¿Qué venden?
        if any(p in texto_lower for p in ["qué vende", "que vende", "qué productos", "que productos", "qué maneja", "que maneja"]):
            if ya_pregunto_suficiente:
                return "Productos ferreteros: cintas, grifería, herramientas. ¿Le envío el catálogo por WhatsApp?"
            return "Productos ferreteros: cintas, grifería, herramientas. ¿Está el encargado?"

        # Pregunta: ¿Qué marcas?
        if any(p in texto_lower for p in ["qué marcas", "que marcas", "de qué marca", "de que marca", "cuál marca", "cual marca"]):
            if ya_pregunto_suficiente:
                return "Manejamos NIOVAL, nuestra marca propia. Mejores precios al ser marca propia. ¿Le envío el catálogo?"
            return "Manejamos NIOVAL, nuestra marca propia. Mejores precios al ser marca propia. ¿Está el encargado?"

        # Objeción: No me interesa
        if any(p in texto_lower for p in ["no me interesa", "no necesitamos", "no gracias"]) and len(texto_lower) < 40:
            return "Entiendo. ¿Le envío el catálogo sin compromiso? Es solo para que lo tenga como referencia."

        # Objeción: Ya tenemos proveedor
        if any(p in texto_lower for p in ["ya tenemos", "ya trabajamos con", "tenemos proveedor"]):
            return "Perfecto. Muchos nos usan como segunda opción. ¿Le envío el catálogo como plan B?"

        # Cliente ocupado
        if any(p in texto_lower for p in ["estoy ocupado", "estoy ocupada", "no tengo tiempo"]) and len(texto_lower) < 40:
            return "Entiendo. ¿Le envío el catálogo por WhatsApp y lo revisa cuando tenga tiempo?"

        # NO hay match en cache → Usar GPT
        return None

    def _calcular_max_tokens_dinamico(self, contexto_actual: str):
        """
        FIX 491: Ajusta max_tokens según complejidad REAL de respuesta.
        No desperdiciar tokens (tiempo) en respuestas simples.

        Returns:
            int: Cantidad de tokens óptima (50-200)
        """
        contexto_lower = contexto_actual.lower().strip()

        # RESPUESTAS ULTRA-SIMPLES (confirmaciones, saludos): 50 tokens
        # Latencia: ~1.5s (vs 3.5s con 150 tokens)
        respuestas_simples = ["ok", "adelante", "perfecto", "claro", "entendido", "gracias", "excelente", "muy bien", "sale", "va"]
        if any(palabra in contexto_lower for palabra in respuestas_simples) and len(contexto_lower) < 20:
            return 50

        # RESPUESTAS CORTAS (preguntas directas): 100 tokens
        # Latencia: ~2.5s
        if len(contexto_lower) < 30:
            return 100

        # RESPUESTAS MEDIAS (default actual): 150 tokens
        # Latencia: ~3.5s
        # Para la mayoría de casos
        if len(contexto_lower) < 60:
            return 150

        # RESPUESTAS COMPLEJAS (objeciones elaboradas): 200 tokens
        # Latencia: ~4.5s (solo cuando realmente necesario)
        # Detectar objeciones complejas o preguntas largas
        return 200

    # ============================================================
    # FIX 762+765+766: Sync FSM state/data back to agent
    # Cuando FSM intercepta, procesar_respuesta() retorna temprano
    # saltándose pattern detector y data extraction. Este método
    # asegura que lead_data y flags se sincronizan correctamente.
    # ============================================================
    def _sync_fsm_to_agent(self, texto_cliente: str, fsm_response: str):
        """FIX 762: Sync FSM state/data back to agent after FSM intercepts."""
        if not hasattr(self, 'fsm') or not self.fsm:
            return

        try:
            import re  # FIX 770: Needed for regex in data extraction below
            from fsm_engine import FSMState
        except ImportError:
            return

        fsm_state = self.fsm.state
        fsm_ctx = self.fsm.context

        # --- 1. Extracción de teléfono cuando FSM llega a CONTACTO_CAPTURADO ---
        if fsm_state == FSMState.CONTACTO_CAPTURADO:
            # FIX 794: Usar convertir_numeros_escritos_a_digitos() para preservar orden
            # Bug anterior: re.findall(r'\d') extraía dígitos literales PRIMERO,
            # luego _nums_to_digit_762 APPENDED palabras → orden incorrecto
            # Ejemplo: "seis seis veintitrés... 23531804" → 2353180466 (MAL)
            # Ahora: convertir TODO a dígitos preservando orden → 6623531804 (BIEN)
            texto_convertido_794 = convertir_numeros_escritos_a_digitos(texto_cliente)
            digitos = re.findall(r'\d', texto_convertido_794)

            if len(digitos) >= 10:
                numero_final = ''.join(digitos[:10])
                if not self.lead_data.get("whatsapp"):
                    self.lead_data["whatsapp"] = numero_final
                    self.lead_data["whatsapp_valido"] = True
                    print(f"  [FSM FIX 762] WhatsApp synced: {numero_final}")

            # 1b. Extracción de email (literal @)
            email_match = re.search(r'[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}', texto_cliente)
            if email_match and not self.lead_data.get("email"):
                self.lead_data["email"] = email_match.group(0)
                print(f"  [FSM FIX 762] Email synced: {email_match.group(0)}")

            # 1c. Email dictado por voz ("arroba gmail punto com") - FIX 617B approach
            if not email_match and 'arroba' in texto_cliente.lower():
                tn_email = texto_cliente.lower().strip()
                tn_email = tn_email.replace(' arroba ', '@').replace(' punto com', '.com')
                tn_email = tn_email.replace(' punto mx', '.mx').replace(' punto net', '.net')
                tn_email = tn_email.replace(' punto org', '.org')
                email_match2 = re.search(r'[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}', tn_email)
                if email_match2 and not self.lead_data.get("email"):
                    self.lead_data["email"] = email_match2.group(0)
                    print(f"  [FSM FIX 762] Email (voice) synced: {email_match2.group(0)}")

        # --- 2. Sync catalogo_prometido ---
        if fsm_ctx.catalogo_prometido:
            self.catalogo_prometido = True

        # --- 3. Sync estado_conversacion ---
        _FSM_TO_ESTADO = {
            FSMState.BUSCANDO_ENCARGADO: EstadoConversacion.BUSCANDO_ENCARGADO,
            FSMState.ENCARGADO_AUSENTE: EstadoConversacion.ENCARGADO_NO_ESTA,
            FSMState.ENCARGADO_PRESENTE: EstadoConversacion.BUSCANDO_ENCARGADO,  # No hay equivalente exacto
            FSMState.CAPTURANDO_CONTACTO: EstadoConversacion.PIDIENDO_WHATSAPP,
            FSMState.CONTACTO_CAPTURADO: EstadoConversacion.CONTACTO_CAPTURADO,
            FSMState.DESPEDIDA: EstadoConversacion.DESPEDIDA,
            FSMState.DICTANDO_DATO: EstadoConversacion.DICTANDO_NUMERO,
            FSMState.ESPERANDO_TRANSFERENCIA: EstadoConversacion.ESPERANDO_TRANSFERENCIA,
            # Phase 4: 3 nuevos mappings
            FSMState.SALUDO: EstadoConversacion.ESPERANDO_SALUDO,
            FSMState.PITCH: EstadoConversacion.PRESENTACION,
            FSMState.OFRECIENDO_CONTACTO: EstadoConversacion.OFRECIENDO_CONTACTO_BRUCE,
        }
        new_estado = _FSM_TO_ESTADO.get(fsm_state)
        if new_estado:
            self.estado_conversacion = new_estado

        # --- FIX 766: Sync lead_data para callback ---
        if fsm_ctx.callback_pedido and fsm_ctx.callback_hora:
            if not self.lead_data.get("pregunta_4"):
                self.lead_data["pregunta_4"] = fsm_ctx.callback_hora

        # --- 4. Log sync ---
        print(f"  [FSM FIX 762] Sync: fsm={fsm_state.value} → estado={self.estado_conversacion.value}"
              f" | wapp={self.lead_data.get('whatsapp','')} email={self.lead_data.get('email','')}")

    def procesar_respuesta(self, respuesta_cliente: str) -> str:
        """
        Procesa la respuesta del cliente y genera una respuesta del agente

        Args:
            respuesta_cliente: Lo que dijo el cliente

        Returns:
            Respuesta del agente
        """
        # FIX 620A: Resetear flag de pausa intencional al inicio de cada turno
        self.pausa_intencional = False

        # Agregar respuesta del cliente al historial
        self.conversation_history.append({
            "role": "user",
            "content": respuesta_cliente
        })

        # ============================================================
        # FSM ENGINE - Motor determinista como primer respondedor
        # Modo shadow: loguea decisiones sin interceptar
        # Modo active: intercepta, GPT como fallback
        # ============================================================
        if hasattr(self, 'fsm') and self.fsm:
            try:
                fsm_result = self.fsm.process(respuesta_cliente, self)
                if fsm_result is not None:
                    # FIX 762: Sync FSM state/data back to agent before returning
                    self._sync_fsm_to_agent(respuesta_cliente, fsm_result)
                    self.conversation_history.append({
                        "role": "assistant",
                        "content": fsm_result
                    })
                    # FIX 755: turno_actual puede no existir si FSM intercepta temprano
                    self.turno_actual = getattr(self, 'turno_actual', 0) + 1
                    return fsm_result
            except Exception as e:
                print(f"  [FSM ERROR] {e} - fallthrough a logica existente")

        # ============================================================
        # FIX 759B: BRUCE2427 - Re-introducción post-transferencia
        # Después de "Claro, espero", si persona nueva dice saludo genérico
        # (hola, buen día, bueno), Bruce debe re-presentarse con pitch + encargado
        # FIX 749A ya cubre "quién habla" → solo cubrir saludos sin pregunta identidad
        # ============================================================
        if getattr(self, '_post_espera_reintroducir_759', False):
            self._post_espera_reintroducir_759 = False
            _t759 = respuesta_cliente.strip().lower()
            _t759 = _t759.replace('á','a').replace('é','e').replace('í','i').replace('ó','o').replace('ú','u')
            _t759 = _t759.replace('¿','').replace('?','').replace('¡','').replace('!','').replace('.','').replace(',','')
            _saludos_759 = ['hola', 'bueno', 'buen dia', 'buenas tardes', 'buenas noches', 'que tal', 'digame', 'diga', 'si digame', 'mande']
            _es_saludo_759 = any(s in _t759 for s in _saludos_759)
            # Excluir si ya es pregunta de identidad (FIX 749A lo maneja)
            _es_identidad_759 = any(q in _t759 for q in ['quien habla', 'quien llama', 'de donde', 'que empresa', 'de parte de'])
            if _es_saludo_759 and not _es_identidad_759:
                _reintro = "Buen día. Mi nombre es Bruce, le llamo de la marca NIOVAL, distribuidores de productos ferreteros. ¿Se encontrará el encargado o encargada de compras?"
                print(f"\n [FIX 759B] Post-transferencia: persona nueva saluda '{respuesta_cliente[:60]}' → re-introducción")
                self.conversation_history.append({"role": "assistant", "content": _reintro})
                self.turno_actual = getattr(self, 'turno_actual', 0) + 1
                return _reintro

        # ============================================================
        # FIX 708+709: PREGUNTAS OBVIAS - Respuestas instantáneas
        # 708: anotar/papel, escuchas/ahí, robot/grabación, listo
        # 709: quién habla, qué venden, cómo te llamas, eres Bruce
        # Intercepta ANTES de pattern detector y GPT = 0 latencia, 0 cascada
        # ============================================================
        texto_lower_708 = respuesta_cliente.strip().lower()
        texto_lower_708 = texto_lower_708.replace('á','a').replace('é','e').replace('í','i').replace('ó','o').replace('ú','u').replace('ü','u').replace('ñ','n')
        texto_lower_708 = texto_lower_708.replace('¿','').replace('?','').replace('¡','').replace('!','')

        # Diccionario: {patrones} → respuesta
        # Orden importa: se evalúa primero el match más específico
        preguntas_obvias_708 = [
            # --- Cliente ofrece dictar dato ---
            (['tienes donde anotar', 'tiene donde anotar', 'tienes para anotar',
              'tiene para anotar', 'tienes con que anotar', 'tiene con que anotar',
              'tienes lapiz', 'tiene lapiz', 'tienes papel', 'tiene papel',
              'tienes pluma', 'tiene pluma', 'tienes donde apuntar', 'tiene donde apuntar',
              'tienes donde escribir', 'tiene donde escribir'],
             "Si, claro, digame por favor."),

            # --- Verificación de conexión ---
            (['me escuchas', 'me escucha', 'me oyes', 'me oye',
              'sigues ahi', 'sigue ahi', 'estas ahi', 'esta ahi',
              'hay alguien', 'hay alguien ahi', 'se oye', 'se escucha'],
             "Si, le escucho perfectamente, digame."),

            # --- ¿Eres robot/grabación? ---
            (['eres robot', 'es un robot', 'eres una grabacion', 'es una grabacion',
              'eres una maquina', 'es una maquina', 'es automatico', 'eres automatico',
              'habla una maquina', 'habla un robot', 'eres inteligencia artificial',
              'es inteligencia artificial'],
             "No, soy Bruce, agente de ventas de NIOVAL. ¿En que le puedo ayudar?"),

            # --- ¿Estás listo/preparado? ---
            (['estas listo', 'esta listo', 'listo para anotar', 'ya estas',
              'ya esta listo', 'preparado'],
             "Si, estoy listo, digame por favor."),

            # --- FIX 709/749A: ¿Quién habla? / ¿De dónde llaman? ---
            # FIX 749A: BRUCE2388 - Response includes greeting prefix + encargado question
            # Bug detector marked SALUDO_FALTANTE because FIX 708 returned identification without "Buen día"
            (['quien habla', 'quien llama', 'quien me habla', 'quien me llama',
              'con quien hablo', 'con quien tengo el gusto', 'con quien tengo gusto',
              'de donde habla', 'de donde hablan', 'de donde llama', 'de donde llaman',
              'de donde me habla', 'de donde me llama', 'de donde me marcan',
              'de que empresa', 'de que compania', 'que empresa es',
              'de parte de quien', 'a nombre de quien'],
             "Buen día. Mi nombre es Bruce, le llamo de la marca NIOVAL. Somos distribuidores de productos ferreteros. ¿Se encontrará el encargado o encargada de compras?"),

            # --- FIX 709: ¿Qué venden/manejan? ---
            (['que venden', 'que vende', 'que ofrecen', 'que ofrece',
              'que manejan', 'que maneja', 'que productos', 'que tipo de productos',
              'que es lo que venden', 'a que se dedican', 'que es nioval',
              'de que se trata', 'que comercializan', 'que distribuyen'],
             "Distribuimos productos de ferreteria: cintas tapagoteras, griferia, herramientas, candados y mas de 15 categorias."),

            # --- FIX 709: ¿Cómo te llamas? / ¿Tu nombre? ---
            (['como te llamas', 'como se llama', 'cual es tu nombre', 'cual es su nombre',
              'tu nombre', 'su nombre cual es', 'me dice su nombre',
              'dime tu nombre', 'digame su nombre'],
             "Mi nombre es Bruce, de la marca NIOVAL."),

            # --- FIX 710A: BRUCE2255 - "No hacemos compras" = rechazo definitivo ---
            (['no hacemos compra', 'no hacemos compras', 'no hacemos ningun tipo de compra',
              'no compramos', 'no compramos nada', 'no compro nada',
              'aqui no se compra', 'aqui no compramos', 'no hacemos pedidos',
              'no manejamos compras', 'no realizamos compras',
              'no adquirimos', 'no necesitamos proveedores', 'no necesitamos proveedor',
              'ya tenemos todo cubierto', 'no nos interesa ningun producto',
              'no estamos interesados en comprar'],
             "Entendido, disculpe la molestia. Que tenga buen dia."),

            # --- FIX 709: Confirmación de nombre "¿Bruce?" ---
            (['eres bruce', 'es bruce', 'bruce verdad', 'bruce, verdad',
              'bruce cierto', 'bruce, cierto',
              'se llama bruce', 'te llamas bruce', 'usted es bruce'],
             "Si, soy Bruce de NIOVAL. ¿En que le puedo ayudar?"),
        ]

        for patrones_708, respuesta_708 in preguntas_obvias_708:
            if any(p in texto_lower_708 for p in patrones_708):
                print(f"\n[OK] FIX 708: PREGUNTA OBVIA detectada")
                print(f"   Cliente: '{respuesta_cliente[:60]}'")
                print(f"   Respuesta: '{respuesta_708}'")

                # Registrar en historial
                self.conversation_history.append({
                    "role": "assistant",
                    "content": respuesta_708
                })

                # Actualizar Memory Layer
                try:
                    if hasattr(self, 'memory') and self.memory:
                        self.memory.extract_facts(self.conversation_history)
                except Exception:
                    pass

                return respuesta_708

        # ============================================================
        # FIX 491: OPTIMIZACIÓN DE LATENCIA (Cache + Patrones + Reducción 66% delay)
        # Intentar respuesta INSTANTÁNEA antes de llamar a GPT (3.5s → 0.05-0.6s)
        # ============================================================

        # PASO 1: Detectar patrones simples (0.05s - 100x más rápido)
        patron_detectado = self._detectar_patron_simple_optimizado(respuesta_cliente)

        # FIX 633: Registrar match en pattern audit
        if patron_detectado:
            try:
                from pattern_audit import track_pattern_match
                track_pattern_match(patron_detectado.get('tipo', ''), respuesta_cliente[:80])
            except Exception:
                pass

        # FIX 570: Si texto termina en conector/coma, el cliente NO terminó de hablar
        # No usar fast-match, dejar que GPT procese con contexto completo
        if patron_detectado:
            conectores_finales_570 = [' y', ' o', ' pero', ' que', ' con', ' para', ' por', ' de',
                ' en', ' a', ' como', ' cuando', ',', '...', ' si', ' pues']
            texto_patron_lower = respuesta_cliente.strip().lower()
            texto_termina_conector = any(texto_patron_lower.endswith(c) for c in conectores_finales_570)
            if texto_termina_conector:
                print(f"   FIX 570: Patrón detectado ({patron_detectado['tipo']}) PERO texto termina en conector - dejando a GPT")
                print(f"   Texto: '{respuesta_cliente[-40:]}'")
                patron_detectado = None

        # FASE 1.3: CIRCUIT BREAKER - Si 3+ patrones invalidados consecutivamente, skip validators
        # Problema: Validators invalidan patrones correctos en cadena → siempre cae a GPT → GPT puede fallar
        # Solución: Si el agente acumula 3+ invalidaciones seguidas, confiar en pattern detector
        _skip_validators_751 = False
        if patron_detectado:
            _inv_count = getattr(self, '_patrones_invalidados_consecutivos', 0)
            if _inv_count >= 3:
                _skip_validators_751 = True
                print(f"\n FASE 1.3: CIRCUIT BREAKER ACTIVO - {_inv_count} patrones invalidados consecutivamente")
                print(f"   Confiando en pattern detector: '{patron_detectado.get('tipo', '')}'")
                self._patrones_invalidados_consecutivos = 0  # Reset después de bypass

        # FIX 598: VALIDADOR POST-PATRÓN - Detectar contradicciones antes de responder
        # Problema: El pattern detector responde en 0.05s pero a veces la respuesta
        # CONTRADICE lo que el cliente dijo (ej: cliente ofrece correo pero Bruce dice "le llamo")
        # Solución: Tabla de contradicciones patron→keywords. Si se detecta contradicción, GPT decide.
        if patron_detectado and not _skip_validators_751:
            tipo_patron = patron_detectado.get('tipo', '')
            texto_validacion = respuesta_cliente.strip().lower()
            # FIX 631: Normalizar acentos (consistente con texto_lower)
            texto_validacion = texto_validacion.replace('á','a').replace('é','e').replace('í','i').replace('ó','o').replace('ú','u').replace('ü','u')

            # Tabla de contradicciones: {tipo_patron: [keywords que invalidan el patrón]}
            contradicciones_598 = {
                # Si callback pero cliente ofrece contacto o ES el encargado → GPT
                "ENCARGADO_NO_ESTA_CON_HORARIO": [
                    'correo', 'mail', 'email', 'whatsapp', 'te doy', 'le doy',
                    'te paso', 'le paso', 'anota', 'anote', 'apunta', 'apunte',
                    'pero dígame', 'pero digame', 'en qué le ayudo', 'en que le ayudo',
                    'le puedo ayudar', 'te puedo ayudar', 'lo puedo ayudar',
                    'yo soy', 'soy yo', 'yo mero', 'conmigo', 'soy el encargado',
                    'soy la encargada', 'soy el dueño', 'soy la dueña'
                ],
                "ENCARGADO_LLEGA_MAS_TARDE": [
                    'correo', 'mail', 'email', 'whatsapp', 'te doy', 'le doy',
                    'te paso', 'le paso', 'pero dígame', 'pero digame',
                    'en qué le ayudo', 'en que le ayudo',
                    'yo soy', 'soy yo', 'yo mero', 'conmigo', 'soy el encargado',
                    'soy la encargada', 'soy el dueño', 'soy la dueña'
                ],
                # Si respuesta identidad pero cliente pregunta ubicación → GPT
                "PREGUNTA_IDENTIDAD": [
                    'dónde están', 'donde estan', 'qué ciudad', 'que ciudad',
                    'dónde se ubican', 'donde se ubican'
                ],
                # Si encargado no está pero cliente ofrece ayudar o ES el encargado → GPT
                "ENCARGADO_NO_ESTA_SIN_HORARIO": [
                    'pero dígame', 'pero digame', 'pero dime',
                    'en qué le ayudo', 'en que le ayudo', 'que se le ofrece',
                    'le puedo ayudar', 'lo puedo ayudar', 'puedo ayudarle',
                    'yo le ayudo', 'yo lo ayudo', 'yo le atiendo', 'yo lo atiendo',
                    'dígame a mí', 'digame a mi', 'dime a mí', 'dime a mi',
                    'yo soy', 'soy yo', 'yo mero', 'conmigo', 'soy el encargado',
                    'soy la encargada', 'soy el dueño', 'soy la dueña',
                    'correo', 'mail', 'email', 'whatsapp', 'te doy', 'le doy',
                    'te paso', 'le paso'
                ],
                # Si despedida pero cliente hace pregunta nueva → no despedirse
                "DESPEDIDA": [
                    '¿', 'que productos', 'qué productos', 'catálogo', 'catalogo',
                    'envíame', 'enviame', 'mándame', 'mandame'
                ],
                # FIX 686A: OFRECER_CONTACTO_BRUCE eliminado de contradicciones_598
                # Keywords como 'correo' invalidaban en contexto de negación ("no tengo correo")
                # El pattern detector solo dispara este patrón cuando cliente rechazó todo → correcto
                # FIX 599: SOLICITUD_CALLBACK contradice si cliente ofrece contacto directo
                "SOLICITUD_CALLBACK": [
                    'correo', 'mail', 'email', 'whatsapp', 'te doy', 'le doy',
                    'te paso', 'le paso', 'anota', 'anote', 'apunta', 'apunte',
                    'yo le ayudo', 'yo lo ayudo', 'yo le atiendo', 'yo lo atiendo',
                    'dígame a mí', 'digame a mi', 'conmigo', 'yo mero'
                ],
                # FIX 599: Si patrón pide transferir pero CLIENTE ES el encargado → GPT
                "TRANSFERENCIA": [
                    'yo soy', 'soy yo', 'yo mero', 'conmigo', 'aquí estoy', 'aqui estoy',
                    'yo le atiendo', 'yo lo atiendo', 'yo le ayudo', 'yo lo ayudo',
                    'soy el encargado', 'soy la encargada', 'soy el dueño',
                    'soy la dueña', 'soy el responsable', 'soy la responsable'
                ],
                # FIX 599: CONFIRMACION_SIMPLE contradice si después del "sí" hay contenido importante
                "CONFIRMACION_SIMPLE": [
                    'correo', 'mail', 'email', 'whatsapp', 'catálogo', 'catalogo',
                    'precio', 'precios', 'cotización', 'cotizacion',
                    'qué productos', 'que productos', 'qué manejan', 'que manejan',
                    'qué venden', 'que venden', 'qué marcas', 'que marcas',
                    'envíame', 'enviame', 'mándame', 'mandame',
                    'te doy', 'le doy', 'te paso', 'le paso'
                ],
            }

            keywords_contradiccion = contradicciones_598.get(tipo_patron, [])
            contradiccion_encontrada = None
            for kw in keywords_contradiccion:
                if kw in texto_validacion:
                    contradiccion_encontrada = kw
                    break

            # También verificar: si el texto tiene 2+ cláusulas y la segunda tiene "?" → GPT
            # Ej: "No se encuentra. ¿De dónde habla?" → la pregunta es más importante que el estado
            # FIX 635: Patrones de confirmación/dato inmunes a pregunta complementaria
            # Ej: "sí es el mismo, ¿me puedes mandar?" → la pregunta NO contradice CONFIRMA_MISMO_NUMERO
            # FASE 1.1: Set UNIVERSAL de inmunidad - reemplaza 4 listas separadas
            # Patrones en este set sobreviven TODOS los validadores (598, 600, 601, 602)
            _PATRONES_INMUNES_UNIVERSAL = {
                # Confirmaciones/aceptaciones
                'CONFIRMA_MISMO_NUMERO', 'CONFIRMACION_SIMPLE', 'CLIENTE_DICE_SI', 'CLIENTE_DICE_NO',
                'CLIENTE_ACEPTA_WHATSAPP', 'CLIENTE_ACEPTA_CORREO', 'CLIENTE_ACEPTA_CONTACTO_BRUCE',
                # Ofertas de datos del cliente
                'CLIENTE_OFRECE_WHATSAPP', 'CLIENTE_OFRECE_CORREO', 'CLIENTE_OFRECE_NUMERO',
                'CLIENTE_OFRECE_SU_CONTACTO', 'OFRECE_CONTACTO_ENCARGADO',
                # Dictado activo
                'CLIENTE_DICTANDO_NUMERO', 'NUMERO_PARCIAL_DICTADO', 'NUMERO_PARCIAL_CON_VERIFICACION',
                'NUMERO_COMPLETO_DICTADO', 'CORREO_DETECTADO', 'WHATSAPP_DETECTADO',
                'CLIENTE_DICTA_EMAIL_COMPLETO',
                # Despedidas/rechazos
                'DESPEDIDA', 'DESPEDIDA_CLIENTE', 'RECHAZO_DEFINITIVO', 'NO_INTERESA_FINAL',
                'DESPEDIDA_NATURAL_CLIENTE_DERIVACION', 'DESPEDIDA_NATURAL_CLIENTE_NO_DISPONIBLE',
                'NO_HACEMOS_COMPRAS', 'SALUDO',
                # Estado encargado
                'ENCARGADO_NO_ESTA_SIN_HORARIO', 'ENCARGADO_NO_ESTA_CON_HORARIO',
                'ENCARGADO_LLEGA_MAS_TARDE', 'ENCARGADO_LLEGA_MAS_TARDE_ALTERNATIVA',
                'CLIENTE_ES_ENCARGADO',
                # Sucursal/ubicacion
                'OTRA_SUCURSAL', 'OTRA_SUCURSAL_INSISTENCIA',
                # Contacto Bruce
                'OFRECER_CONTACTO_BRUCE', 'DAR_CONTACTO_BRUCE', 'PEDIR_TELEFONO_FIJO',
                'PIDE_CONTACTO_NIOVAL',
                # Anti-loop
                'EVITAR_LOOP_WHATSAPP',
                # Conversacionales
                'DIGAME_CONTINUAR', 'PREGUNTA_IDENTIDAD', 'PREGUNTA_MARCAS',
                'VERIFICACION_CONEXION', 'VERIFICACION_CONEXION_REPETIR_PREGUNTA',
                # Callback
                'SOLICITUD_CALLBACK',
                # FIX 744: Area equivocada (despedida inmediata, no invalidar)
                'AREA_EQUIVOCADA',
                # FIX 757: Patrones con 0% survival en pattern audit
                'ESPERANDO_QUE_ANOTE', 'TIENDA_CERRADA',
            }
            patrones_inmunes_pregunta_598 = _PATRONES_INMUNES_UNIVERSAL
            tiene_pregunta_segunda_clausula = False
            partes_texto = [p.strip() for p in texto_validacion.replace('.', '|').replace('?', '?|').split('|') if p.strip()]
            if len(partes_texto) >= 2 and tipo_patron not in patrones_inmunes_pregunta_598:
                for parte in partes_texto[1:]:
                    if '?' in parte or parte.startswith('qué') or parte.startswith('que') or parte.startswith('cómo') or parte.startswith('como') or parte.startswith('cuál') or parte.startswith('cual') or parte.startswith('dónde') or parte.startswith('donde') or parte.startswith('quién') or parte.startswith('quien'):
                        # FIX 707C: BRUCE2253 - "anotar/apuntar" = cliente OFRECE dato, NO contradicción
                        parte_lower = parte.lower()
                        if any(k in parte_lower for k in ['anotar', 'apuntar', 'donde escribir']):
                            print(f"   FIX 707C: Pregunta '{parte[:30]}' es oferta de dato, NO contradicción")
                            continue  # Skip this part, check next
                        tiene_pregunta_segunda_clausula = True
                        contradiccion_encontrada = f"pregunta en 2da cláusula: '{parte[:30]}'"
                        break

            if contradiccion_encontrada:
                print(f"   FIX 598: VALIDADOR POST-PATRÓN: Patrón '{tipo_patron}' CONTRADICHO por '{contradiccion_encontrada}'")
                print(f"   Texto cliente: '{texto_validacion[:80]}'")
                print(f"   Respuesta que SE EVITÓ: '{patron_detectado['respuesta'][:60]}...'")
                print(f"   → Derivando a GPT para respuesta contextual")
                # FIX 633: Registrar invalidación por FIX 598
                try:
                    from pattern_audit import track_pattern_invalidation
                    track_pattern_invalidation(tipo_patron, "598")
                except Exception:
                    pass
                patron_detectado = None  # Invalidar patrón, GPT decidirá
                # FASE 1.3: Incrementar counter de invalidaciones consecutivas
                self._patrones_invalidados_consecutivos = getattr(self, '_patrones_invalidados_consecutivos', 0) + 1

        # FIX 600: SPLITTER ADVERSATIVO - "pero/sin embargo/aunque" cambia intención
        # Problema: "No está pero yo le ayudo" → patrón matchea "no está" e ignora "yo le ayudo"
        # Solución: Si texto tiene conjunción adversativa y la parte después tiene contenido
        # sustancial (>=3 palabras), invalidar patrón porque la intención real está DESPUÉS del "pero"
        if patron_detectado and not _skip_validators_751:
            texto_600 = respuesta_cliente.strip().lower()
            # FIX 631: Normalizar acentos (consistente con texto_lower)
            texto_600 = texto_600.replace('á','a').replace('é','e').replace('í','i').replace('ó','o').replace('ú','u').replace('ü','u')
            conjunciones_adversativas = [' pero ', ' sin embargo ', ' aunque ', ' solo que ', ' nada mas que ', ' nomas que ',
                                        ' la verdad ', ' es que ', ' lo que pasa es que ', ' lo que pasa ', ' la neta ']
            # Patrones que SÍ sobreviven al "pero" (despedida, confirmaciones negativas)
            # FIX 621C: OTRA_SUCURSAL inmune (cliente dice "es que no es en esta sucursal" → "es que" no cambia intención)
            # FIX 621A: CLIENTE_OFRECE_CORREO/NUMERO inmune (cliente dice "pero le doy un correo" → oferta es válida)
            # FIX 626B: OFRECE_CONTACTO_ENCARGADO y CLIENTE_OFRECE_SU_CONTACTO inmunes
            # FIX 629A: Agregar DESPEDIDA_CLIENTE (tipo real retornado por pattern detector)
            # FIX 639A: BRUCE2068 - CLIENTE_DICTA_EMAIL_COMPLETO inmune (email dictado es naturalmente largo)
            # FIX 648: Agregar DESPEDIDA_NATURAL_CLIENTE_* (cierre natural del cliente)
            # FIX 661: Pattern audit - Agregar patrones con 0% survival
            # FIX 687A: Agregar CLIENTE_ACEPTA_CORREO, EVITAR_LOOP_WHATSAPP, PEDIR_TELEFONO_FIJO (0% survival)
            # FASE 1.1: Usar set universal (reemplaza lista individual)
            patrones_inmunes_pero = _PATRONES_INMUNES_UNIVERSAL
            tipo_600 = patron_detectado.get('tipo', '')

            if tipo_600 not in patrones_inmunes_pero:
                for conj in conjunciones_adversativas:
                    if conj in texto_600:
                        parte_despues = texto_600.split(conj, 1)[1].strip()
                        palabras_despues = [p for p in parte_despues.split() if len(p) > 2]
                        if len(palabras_despues) >= 2:
                            print(f"   FIX 600: SPLITTER ADVERSATIVO: Texto tiene '{conj.strip()}' + {len(palabras_despues)} palabras después")
                            print(f"   Antes: '{texto_600.split(conj, 1)[0].strip()[:40]}'")
                            print(f"   Después: '{parte_despues[:40]}'")
                            print(f"   Patrón '{tipo_600}' INVALIDADO → GPT decidirá con contexto completo")
                            # FIX 633: Registrar invalidación por FIX 600
                            try:
                                from pattern_audit import track_pattern_invalidation
                                track_pattern_invalidation(tipo_600, "600")
                            except Exception:
                                pass
                            patron_detectado = None
                            # FASE 1.3: Incrementar counter
                            self._patrones_invalidados_consecutivos = getattr(self, '_patrones_invalidados_consecutivos', 0) + 1
                        break

        # FIX 601: UMBRAL DE COMPLEJIDAD - Textos largos multi-cláusula → GPT
        # Problema: Textos de >12 palabras con múltiples oraciones son demasiado complejos
        # para pattern matching simple. Ej: "No está el jefe, salió a comer, pero si quiere
        # le paso al encargado del área de compras" → patrón ve "no está" e ignora todo lo demás
        # Solución: Si texto tiene >12 palabras Y >1 cláusula (separada por punto/coma/;) → GPT
        if patron_detectado and not _skip_validators_751:
            texto_601 = respuesta_cliente.strip()
            palabras_601 = texto_601.split()
            tipo_601 = patron_detectado.get('tipo', '')
            # Solo aplicar a textos largos, no a confirmaciones cortas
            # FIX 617A: BRUCE2032 - CORREO_DETECTADO y WHATSAPP_DETECTADO son inmunes
            # Problema: Cliente dicta email largo (>12 palabras + 3 cláusulas) → FIX 601 invalidaba
            # el patrón CORREO_DETECTADO → GPT devolvía vacío → FIX 577 respondía con pitch inicial
            # FIX 621C: OTRA_SUCURSAL inmune (texto largo con "es en la otra sucursal" no debe ir a GPT)
            # FIX 621A: CLIENTE_OFRECE_CORREO/NUMERO inmune (dictado largo no debe invalidar)
            # FIX 626B: OFRECE_CONTACTO_ENCARGADO y CLIENTE_OFRECE_SU_CONTACTO inmunes
            # FIX 629A: Agregar DESPEDIDA_CLIENTE (tipo real retornado por pattern detector)
            # FIX 634: CLIENTE_DICTANDO_NUMERO/NUMERO_PARCIAL inmunes (buzón de voz prepende texto largo)
            # FIX 639A: BRUCE2068 - CLIENTE_DICTA_EMAIL_COMPLETO inmune (dictado de email largo + multi-clausula)
            # FIX 646D: EVITAR_LOOP_WHATSAPP y CLIENTE_ACEPTA_CORREO inmunes (audit mostró 0% survival)
            # FIX 648: DESPEDIDA_NATURAL_CLIENTE_* inmunes (cierre natural del cliente)
            # FIX 661: Pattern audit - Agregar patrones con 0% survival
            # FIX 687B: Agregar PEDIR_TELEFONO_FIJO (0% survival - no estaba en ninguna lista)
            # FIX 710B: BRUCE2255 - ENCARGADO_NO_ESTA_* inmunes (cliente repite 3x genera >12 palabras)
            # FASE 1.1: Usar set universal (reemplaza lista individual)
            patrones_inmunes_601 = _PATRONES_INMUNES_UNIVERSAL
            # FASE 1.1: Threshold subido de 12/3 → 25/5 (solo invalida textos REALMENTE ambiguos)
            if len(palabras_601) > 25 and tipo_601 not in patrones_inmunes_601:
                # Contar cláusulas (separadores: . , ; ¿ ?)
                num_clausulas = 1
                for sep in ['. ', ', ', '; ', '¿', '?']:
                    num_clausulas += texto_601.count(sep)
                if num_clausulas >= 5:
                    print(f"   FIX 601: UMBRAL COMPLEJIDAD: {len(palabras_601)} palabras + {num_clausulas} cláusulas")
                    print(f"   Texto: '{texto_601[:60]}...'")
                    print(f"   Patrón '{tipo_601}' INVALIDADO → GPT maneja complejidad mejor")
                    # FIX 633: Registrar invalidación por FIX 601
                    try:
                        from pattern_audit import track_pattern_invalidation
                        track_pattern_invalidation(tipo_601, "601")
                    except Exception:
                        pass
                    patron_detectado = None
                    # FASE 1.3: Incrementar counter
                    self._patrones_invalidados_consecutivos = getattr(self, '_patrones_invalidados_consecutivos', 0) + 1

        # FIX 602: VALIDADOR DE CONTEXTO CONVERSACIONAL
        # Problema: El patrón detectado puede ser técnicamente correcto pero INCOHERENTE
        # con lo que Bruce preguntó. Ej: Bruce pidió correo → cliente dice "no" → patrón RECHAZO
        # pero lo correcto es que GPT pida alternativa (WhatsApp).
        # Solución: Extraer el tema de la última pregunta de Bruce y validar coherencia.
        if patron_detectado and len(self.conversation_history) >= 2 and not _skip_validators_751:
            tipo_602 = patron_detectado.get('tipo', '')
            # Obtener último mensaje de Bruce
            ultimo_bruce_602 = None
            for msg in reversed(self.conversation_history):
                if msg['role'] == 'assistant':
                    ultimo_bruce_602 = msg['content'].lower()
                    break

            if ultimo_bruce_602:
                # Detectar tema de la última pregunta de Bruce
                tema_bruce = None
                if any(kw in ultimo_bruce_602 for kw in ['correo', 'email', 'mail']):
                    tema_bruce = 'PIDIENDO_CORREO'
                elif any(kw in ultimo_bruce_602 for kw in ['whatsapp', 'número', 'numero', 'teléfono', 'telefono', 'celular']):
                    tema_bruce = 'PIDIENDO_TELEFONO'
                elif any(kw in ultimo_bruce_602 for kw in ['encargado', 'responsable', 'dueño', 'jefe', 'gerente']):
                    tema_bruce = 'PIDIENDO_ENCARGADO'
                elif any(kw in ultimo_bruce_602 for kw in ['catálogo', 'catalogo', 'productos', 'marcas', 'líneas', 'lineas']):
                    tema_bruce = 'OFRECIENDO_CATALOGO'
                elif any(kw in ultimo_bruce_602 for kw in ['horario', 'hora', 'cuándo', 'cuando', 'qué día', 'que dia']):
                    tema_bruce = 'PREGUNTANDO_HORARIO'

                # FIX 692C: Patrones que SIEMPRE sobreviven FIX 602 (0% survival fix)
                # Estos patrones son válidos en CUALQUIER contexto conversacional
                # FASE 1.1: Usar set universal (reemplaza lista individual)
                patrones_inmunes_602 = _PATRONES_INMUNES_UNIVERSAL

                if tipo_602 in patrones_inmunes_602:
                    print(f"   FIX 692C: Patrón '{tipo_602}' es INMUNE a FIX 602 (válido en cualquier contexto)")
                    # No invalidar, dejar que sobreviva
                else:
                    pass  # Continuar con check de incoherencias normal

                # Patrones INCOHERENTES según contexto de Bruce
                # Si Bruce pidió dato de contacto → respuestas de estado de encargado son incoherentes
                # FIX 686C: OFRECER_CONTACTO_BRUCE eliminado de incoherencias (0% survival)
                # Bruce ofrece su contacto como último recurso independiente del tema actual
                incoherencias_por_contexto = {
                    'PIDIENDO_CORREO': [
                        'ENCARGADO_NO_ESTA_CON_HORARIO', 'ENCARGADO_NO_ESTA_SIN_HORARIO',
                        'ENCARGADO_LLEGA_MAS_TARDE', 'SOLICITUD_CALLBACK',
                        'PREGUNTA_IDENTIDAD', 'PREGUNTA_UBICACION',
                        'TRANSFERENCIA'
                    ],
                    'PIDIENDO_TELEFONO': [
                        'ENCARGADO_NO_ESTA_CON_HORARIO', 'ENCARGADO_NO_ESTA_SIN_HORARIO',
                        'ENCARGADO_LLEGA_MAS_TARDE', 'SOLICITUD_CALLBACK',
                        'PREGUNTA_IDENTIDAD', 'PREGUNTA_UBICACION',
                        'TRANSFERENCIA'
                    ],
                    'PIDIENDO_ENCARGADO': [
                        'CONFIRMACION_SIMPLE', 'DESPEDIDA',
                    ],
                    'OFRECIENDO_CATALOGO': [
                        'ENCARGADO_NO_ESTA_CON_HORARIO', 'ENCARGADO_NO_ESTA_SIN_HORARIO',
                        'SOLICITUD_CALLBACK', 'TRANSFERENCIA'
                    ],
                    'PREGUNTANDO_HORARIO': [
                        'CONFIRMACION_SIMPLE',
                        'PREGUNTA_IDENTIDAD'
                    ],
                }

                if tema_bruce:
                    patrones_incoherentes = incoherencias_por_contexto.get(tema_bruce, [])
                    # FIX 692C: Skip invalidación si patrón es inmune a FIX 602
                    if tipo_602 in patrones_incoherentes and tipo_602 not in patrones_inmunes_602:
                        print(f"   FIX 602: VALIDADOR CONTEXTO: Bruce estaba en '{tema_bruce}'")
                        print(f"   Patrón '{tipo_602}' es INCOHERENTE con el contexto")
                        print(f"   Último Bruce: '{ultimo_bruce_602[:60]}'")
                        print(f"   → GPT dará respuesta contextual coherente")
                        # FIX 633: Registrar invalidación por FIX 602
                        try:
                            from pattern_audit import track_pattern_invalidation
                            track_pattern_invalidation(tipo_602, "602")
                        except Exception:
                            pass
                        patron_detectado = None
                        # FASE 1.3: Incrementar counter
                        self._patrones_invalidados_consecutivos = getattr(self, '_patrones_invalidados_consecutivos', 0) + 1

        if patron_detectado:
            # FASE 1.3: Patrón sobrevivió → reset counter
            self._patrones_invalidados_consecutivos = 0
            # FIX 633: Registrar que patrón sobrevivió todos los checks
            try:
                from pattern_audit import track_pattern_survived
                track_pattern_survived(patron_detectado.get('tipo', ''))
            except Exception:
                pass
            print(f"[EMOJI] FIX 491: PATRÓN DETECTADO ({patron_detectado['tipo']}) - Latencia ~0.05s vs 3.5s GPT (reducción 98%)")

            # FIX 482: Métrica - Si es pregunta directa, registrarla como respondida
            if patron_detectado.get('accion') == "RESPONDER_PREGUNTA":
                self.metrics.log_pregunta_directa(respondida=True)

            # Ejecutar acción si hay
            if patron_detectado['accion'] == "GUARDAR_WHATSAPP" and 'dato' in patron_detectado:
                self.lead_data["whatsapp"] = patron_detectado['dato']
                print(f"   [PHONE] WhatsApp guardado: {patron_detectado['dato']}")
            elif patron_detectado['accion'] == "GUARDAR_CORREO" and 'dato' in patron_detectado:
                self.lead_data["email"] = patron_detectado['dato']
                print(f"   [EMAIL] Correo guardado: {patron_detectado['dato']}")

            # FIX 620B: BRUCE2056 - Si patrón pregunta por HORA de callback, activar flag
            # Problema: esperando_hora_callback solo se activaba en _filtrar_respuesta_post_gpt (GPT),
            # pero patrones ENCARGADO_LLEGA_MAS_TARDE retornan sin pasar por GPT.
            # Sin el flag, FIX 526 no prevenía que FIX 477 pausara al recibir "12 de la tarde"
            tipo_patron_620 = patron_detectado.get('tipo', '')
            respuesta_lower_620 = patron_detectado['respuesta'].lower()
            if tipo_patron_620 in ('ENCARGADO_LLEGA_MAS_TARDE', 'ENCARGADO_LLEGA_MAS_TARDE_ALTERNATIVA',
                                   'ENCARGADO_NO_ESTA_CON_HORARIO', 'SOLICITUD_CALLBACK'):
                if any(f in respuesta_lower_620 for f in ['qué hora', 'que hora', 'cuándo', 'cuando',
                                                          'a qué hora', 'a que hora']):
                    self.esperando_hora_callback = True
                    print(f"   FIX 620B: esperando_hora_callback=True (patrón {tipo_patron_620} pregunta hora)")

            # Agregar respuesta al historial
            self.conversation_history.append({
                "role": "assistant",
                "content": patron_detectado['respuesta']
            })

            return patron_detectado['respuesta']

        # FASE 2.1: GPT-4o-mini intent classifier como fallback
        # Si patron_detectado fue invalidado o no hubo match, intentar clasificación rápida
        _gpt_intent_751 = None
        try:
            from gpt_intent_classifier import classify_intent, intent_to_pattern_type
            _ultimo_bruce_751 = ""
            for _m in reversed(self.conversation_history):
                if _m.get('role') == 'assistant':
                    _ultimo_bruce_751 = _m.get('content', '')[:100]
                    break
            _estado_751 = getattr(self, 'estado_conversacion', None)
            _estado_str_751 = _estado_751.value if _estado_751 and hasattr(_estado_751, 'value') else str(_estado_751)
            _gpt_intent_751 = classify_intent(
                respuesta_cliente, _ultimo_bruce_751, _estado_str_751,
                call_sid=self.lead_data.get('bruce_id', '')
            )
            if _gpt_intent_751 and _gpt_intent_751.get('confidence', 0) >= 0.85:
                _mapped_type = intent_to_pattern_type(_gpt_intent_751['intent'])
                if _mapped_type:
                    print(f"   FASE 2.1: GPT intent '{_gpt_intent_751['intent']}' → tipo patrón '{_mapped_type}'")
                    # Enriquecer el contexto para GPT principal (no override, solo hint)
                    self._gpt_intent_hint = _gpt_intent_751
        except ImportError:
            pass  # Module not available
        except Exception as e_gi:
            print(f"   [WARN] FASE 2.1: GPT intent classifier error: {e_gi}")

        # FIX 699: Memory Layer - Extraer hechos antes de procesar
        try:
            if self.memory:
                self.memory.extract_facts(self.conversation_history)
        except Exception as e_mem:
            print(f"   [WARN] FIX 699: Memory extract_facts error: {e_mem}")

        # FIX 700: Speech Processor - Analizar estado de speech
        try:
            if self.speech:
                estado_speech_700, accion_speech_700 = self.speech.process_input(respuesta_cliente)
                print(f"   [SPEECH] FIX 700: Estado={estado_speech_700.value}, Acción={accion_speech_700.value}")
                # Sincronizar flag esperando_hora_callback con speech processor
                if self.esperando_hora_callback:
                    self.speech.set_waiting_for_hour(True)
        except Exception as e_sp:
            print(f"   [WARN] FIX 700: Speech process_input error: {e_sp}")

        # FIX 477 (AUDITORIA W04): Verificar si cliente está dando información PARCIAL
        # NO interrumpir cuando está dictando número o correo
        # FIX 506b: BRUCE1489/1495/1503 - Retornar "" en lugar de None para evitar falso IVR
        # Problema: None era interpretado por FIX 304 como IVR y colgaba
        if self._cliente_esta_dando_informacion(respuesta_cliente):
            self.metrics.log_interrupcion_detectada()  # FIX 482: Métrica
            # FIX 696: BRUCE2244/2251 - Acknowledgment corto en vez de silencio
            # Problema: FIX 477/506b retornaban "" (vacío) → servidor no enviaba audio → cliente pensaba que se cayó la línea
            # Ejemplos: BRUCE2244 "¿Bueno?" verificando conexión, BRUCE2251 "¿Bueno?" tras dar callback
            # Solución: Retornar acknowledgment MUY corto (2 palabras) para señalar que Bruce está escuchando
            # sin interrumpir al cliente mientras continúa dictando
            self.pausa_intencional = True
            print(f"   [PAUSE]  FIX 477: Cliente dando información PARCIAL - NO interrumpir")
            print(f"   → FIX 696: Generando acknowledgment corto en vez de silencio")
            print(f"   FIX 620A: pausa_intencional=True (FIX 577 NO generará fallback)")

            # Agregar acknowledgment al historial
            acknowledgment = _get_ack_769()
            self.conversation_history.append({
                "role": "assistant",
                "content": acknowledgment
            })

            return acknowledgment  # FIX 696: Acknowledgment corto para señalar que Bruce escucha

        # PASO 2: Buscar en cache de respuestas frecuentes (0.3-0.6s - 83-91% más rápido)
        respuesta_cache = self._obtener_respuesta_cache(respuesta_cliente)
        if respuesta_cache:
            print(f"[EMOJI] FIX 491: CACHE HIT - Latencia ~0.4s vs 3.5s GPT (reducción 89%)")

            # Agregar respuesta al historial
            self.conversation_history.append({
                "role": "assistant",
                "content": respuesta_cache
            })

            return respuesta_cache

        # PASO 3: No hay match - continuar con GPT normal (3.5s)
        print(f"[EMOJI] FIX 491: No hay patrón/cache - Usando GPT (latencia ~3.5s)")

        # FIX 519: Marcar que esta transcripción no fue reconocida (se guardará después con la respuesta)
        self._transcripcion_pendiente_aprender = respuesta_cliente

        # ============================================================
        # FIX 389: INTEGRAR SISTEMA DE ESTADOS (FIX 339)
        # Actualizar estado de conversación ANTES de cualquier análisis
        # FIX 428: Retorna False si detecta problema de audio (no procesar)
        # ============================================================
        debe_continuar = self._actualizar_estado_conversacion(respuesta_cliente)
        # FIX 751: Si _actualizar_estado_conversacion retorna string, es respuesta directa (FIX 389/394/395)
        if isinstance(debe_continuar, str):
            print(f"   FIX 751: _actualizar_estado_conversacion retornó respuesta directa")
            return debe_continuar
        if not debe_continuar:
            # FIX 428 detectó problema de audio (¿bueno? repetido, etc.)
            # No generar respuesta - sistema de respuestas vacías manejará
            # FIX 506b: Retornar "" en lugar de None para evitar falso IVR
            print(f"   [EMOJI]  FIX 428: Problema de audio detectado → NO generar respuesta")
            print(f"   FIX 506b: Retornando '' (vacío) en lugar de None para evitar falso IVR")
            return ""  # FIX 506b: "" = pausar, None = IVR real

        # ============================================================
        # FIX 424: NO INTERRUMPIR cuando cliente está dictando correo/número
        # Caso BRUCE1250: Cliente dijo "compras arroba Gmail." (estaba dictando)
        # Bruce interrumpió antes de que dijera el dominio completo (.com, .mx, etc.)
        # ============================================================
        if self._cliente_esta_dictando():
            import re
            respuesta_lower = respuesta_cliente.lower()

            # Verificar si el dictado está COMPLETO
            dictado_completo = False

            if self.estado_conversacion == EstadoConversacion.DICTANDO_CORREO:
                # Correo completo si tiene dominio: ".com", ".mx", "punto com", etc.
                dominios_completos = [
                    '.com', '.mx', '.net', '.org', '.edu',
                    'punto com', 'punto mx', 'punto net', 'punto org',
                    'com.mx', 'punto com punto mx'
                ]
                dictado_completo = any(dominio in respuesta_lower for dominio in dominios_completos)

                print(f"\n[PAUSE]  FIX 424: Cliente dictando CORREO - Verificando si está completo")
                print(f"   Cliente dijo: \"{respuesta_cliente}\"")
                print(f"   Correo completo: {dictado_completo}")

            elif self.estado_conversacion == EstadoConversacion.DICTANDO_NUMERO:
                # Número completo si tiene 10+ dígitos
                digitos = re.findall(r'\d', respuesta_lower)
                dictado_completo = len(digitos) >= 10

                print(f"\n[PAUSE]  FIX 424: Cliente dictando NÚMERO - Verificando si está completo")
                print(f"   Cliente dijo: \"{respuesta_cliente}\"")
                print(f"   Dígitos detectados: {len(digitos)} - Completo: {dictado_completo}")

            if not dictado_completo:
                # Dictado INCOMPLETO - NO responder, esperar a que cliente termine
                # FIX 506b: Retornar "" en lugar de None para evitar falso IVR
                print(f"   → Dictado INCOMPLETO - Esperando más información")
                print(f"   FIX 506b: Retornando '' (vacío) en lugar de None para evitar falso IVR")
                return ""  # FIX 506b: "" = pausar, None = IVR real

        # ============================================================
        # FIX 426: NO PROCESAR transcripciones PARCIALES incompletas
        # Caso BRUCE1194: Cliente dijo "En este momento" (transcripción parcial de Deepgram)
        # Bruce procesó antes de recibir transcripción final: "En este momento no se encuentra"
        # ============================================================
        respuesta_lower = respuesta_cliente.lower().strip()

        # Frases de INICIO que típicamente CONTINÚAN
        # Caso BRUCE1194/1257/1262/1264/1267: "en este momento" → continúa con "no se encuentra"
        frases_inicio_incompletas = [
            'en este momento',
            'ahorita',
            'ahora',
            'ahora mismo',
            'por el momento',
            'por ahora',
            'en este rato'
        ]

        # Palabras de CONTINUACIÓN que indican que la frase está COMPLETA
        palabras_continuacion = [
            'no',      # "en este momento no se encuentra"
            'está',    # "ahorita está ocupado"
            'esta',    # "ahorita esta ocupado"
            'se',      # "en este momento se encuentra"
            'salió',   # "ahorita salió"
            'salio',   # "ahorita salio"
            'hay',     # "ahora no hay nadie"
            'puede',   # "ahorita no puede"
            'anda',    # "ahorita anda en la comida"
            # FIX 452: Caso BRUCE1349 - Agregar más palabras de continuación
            'estamos', # "ahorita estamos trabajando con un proveedor"
            'estoy',   # "por el momento estoy ocupado"
            'tenemos', # "ahorita tenemos otro proveedor"
            'tengo',   # "ahorita tengo ocupado"
            'trabajamos',  # "ahorita trabajamos con otro"
            'trabajando',  # "estamos trabajando"
            'proveedor',   # "ya tenemos proveedor"
            'gracias',     # "te agradezco" - frase completa de despedida
            'agradezco',   # "te agradezco mucho"
        ]

        # Verificar si cliente dijo SOLO una frase de inicio SIN continuación
        tiene_frase_inicio = any(frase in respuesta_lower for frase in frases_inicio_incompletas)
        # FIX 454: Caso BRUCE1353 - Limpiar puntuación de cada palabra antes de comparar
        # "No, no, en este momento" → ['no', 'no', 'en', 'este', 'momento'] (sin comas)
        palabras_limpias = [palabra.strip('.,;:!?¿¡') for palabra in respuesta_lower.split()]
        tiene_continuacion = any(palabra in palabras_limpias for palabra in palabras_continuacion)

        # Si tiene frase de inicio pero NO tiene continuación → transcripción PARCIAL
        # FIX 506b: Retornar "" en lugar de None para evitar falso IVR
        if tiene_frase_inicio and not tiene_continuacion:
            print(f"\n[PAUSE]  FIX 426: Transcripción PARCIAL detectada (frase de inicio sin continuación)")
            print(f"   Cliente dijo: \"{respuesta_cliente}\"")
            print(f"   Tiene frase de inicio: {tiene_frase_inicio}")
            print(f"   Tiene continuación: {tiene_continuacion}")
            print(f"   → Esperando transcripción COMPLETA")
            print(f"   FIX 506b: Retornando '' (vacío) en lugar de None para evitar falso IVR")
            return ""  # FIX 506b: "" = pausar, None = IVR real

        # FIX 389/415: Si cliente pidió esperar (transferencia) → Responder inmediatamente SIN llamar GPT
        # PERO: Si cambió a BUSCANDO_ENCARGADO (persona nueva), SÍ llamar GPT para re-presentarse
        # FIX 415: Prevenir loop "Claro, espero." - Solo decirlo UNA VEZ
        if self.estado_conversacion == EstadoConversacion.ESPERANDO_TRANSFERENCIA:
            # FIX 415: Verificar si Bruce YA dijo "Claro, espero." recientemente
            ultimos_bruce_temp_fix415 = [
                msg['content'].lower() for msg in self.conversation_history[-5:]
                if msg['role'] == 'assistant'
            ]
            bruce_ya_dijo_espero = any('claro, espero' in msg or 'claro espero' in msg
                                       for msg in ultimos_bruce_temp_fix415)

            if bruce_ya_dijo_espero:
                # FIX 482: BRUCE1457 - Detectar si cliente VOLVIÓ de la espera
                # Si dice "¿Bueno?", "Sí", "Ya", "Aquí estoy", etc. = VOLVIÓ y debemos continuar
                cliente_lower_482 = respuesta_cliente.strip().lower()
                cliente_volvio = any(frase in cliente_lower_482 for frase in [
                    '¿bueno?', 'bueno?', 'bueno', 'sí', 'si', 'ya', 'ya estoy',
                    'aquí estoy', 'aqui estoy', 'listo', 'diga', 'dígame', 'digame',
                    'mande', 'sí diga', 'si diga', 'ya regresé', 'ya regrese',
                    'continúe', 'continue', 'prosiga', 'siga', 'ahí está', 'ahi esta'
                ])

                # FIX 498: BRUCE1473 - Detectar si cliente OFRECE correo/WhatsApp durante espera
                # Si dice "te paso el correo", "quieres el correo", etc. → ACEPTAR la oferta
                patrones_ofrece_correo_espera = [
                    'te puedo pasar el correo', 'le puedo pasar el correo',
                    'te paso el correo', 'le paso el correo', 'te paso correo', 'le paso correo',
                    'te doy el correo', 'le doy el correo', 'te doy correo', 'le doy correo',
                    'quiere el correo', 'quieres el correo', 'quieres que te pase correo',
                    'quiere que le pase correo', 'por correo', 'al correo', 'el correo',
                    'te mando el correo', 'le mando el correo', 'mándalo al correo',
                    'anota el correo', 'anote el correo', 'apunta el correo'
                ]

                patrones_ofrece_whatsapp_espera = [
                    'te puedo pasar el whatsapp', 'le puedo pasar el whatsapp',
                    'te paso el whatsapp', 'le paso el whatsapp', 'te paso el número',
                    'le paso el número', 'te paso numero', 'le paso numero',
                    'te doy el whatsapp', 'le doy el whatsapp', 'te doy el número',
                    'le doy el número', 'quiere el whatsapp', 'quieres el whatsapp',
                    'quiere el número', 'quieres el número', 'anota el número',
                    'anote el número', 'toma nota', 'tome nota', 'ahí le va', 'ahí te va'
                ]

                # FIX 498: Detectar si cliente está verificando que Bruce sigue ahí
                patrones_verificando_presencia = [
                    'hola', '¿hola?', 'bueno', '¿bueno?', '¿sigues ahí?', 'sigues ahi',
                    '¿me escucha?', 'me escucha', '¿está ahí?', 'esta ahi', '¿oye?', 'oye'
                ]

                cliente_ofrece_correo = any(p in cliente_lower_482 for p in patrones_ofrece_correo_espera)
                cliente_ofrece_whatsapp = any(p in cliente_lower_482 for p in patrones_ofrece_whatsapp_espera)
                cliente_verificando = any(p in cliente_lower_482 for p in patrones_verificando_presencia)

                if cliente_ofrece_correo:
                    print(f"\n[OK] FIX 498: Cliente OFRECE CORREO durante espera - '{respuesta_cliente}'")
                    print(f"   Cambiando estado a CONVERSACION_NORMAL para aceptar oferta")
                    self.estado_conversacion = EstadoConversacion.CONVERSACION_NORMAL
                    # Responder aceptando la oferta
                    return "Sí, por favor, dígame el correo."

                if cliente_ofrece_whatsapp:
                    print(f"\n[OK] FIX 498: Cliente OFRECE WHATSAPP/NÚMERO durante espera - '{respuesta_cliente}'")
                    print(f"   Cambiando estado a CONVERSACION_NORMAL para aceptar oferta")
                    self.estado_conversacion = EstadoConversacion.CONVERSACION_NORMAL
                    # Responder aceptando la oferta
                    return "Sí, por favor, dígame el número."

                if cliente_verificando:
                    print(f"\n[OK] FIX 498: Cliente VERIFICANDO PRESENCIA durante espera - '{respuesta_cliente}'")
                    print(f"   Respondiendo para confirmar que seguimos en línea")
                    # Responder para confirmar presencia pero seguir esperando
                    return "Sí, aquí estoy. Le espero."

                # FIX 506 BRUCE1721: Detectar si cliente CLARIFICA que NO puede ayudar
                # Caso: Bruce dijo "Claro, espero." pero cliente dice "estoy en sucursal, no en oficinas"
                # Esto NO es transferencia - cliente está explicando que NO puede ayudar
                patrones_no_puede_ayudar = [
                    'sucursal', 'oficinas', 'área equivocada', 'area equivocada',
                    'departamento equivocado', 'no es mi área', 'no es mi area',
                    'no manejo eso', 'no me corresponde', 'no soy el encargado',
                    'no soy la encargada', 'no tengo autorización', 'no tengo autorizacion',
                    'no estoy autorizado', 'no estoy autorizada',
                    'no lo tenemos permitido', 'no tenemos permitido', 'no me permiten',
                    'no puedo dar', 'no le puedo dar', 'prohibido',
                    'no soy quien', 'no me dejan', 'no está permitido', 'no esta permitido'
                ]
                cliente_no_puede_ayudar = any(p in cliente_lower_482 for p in patrones_no_puede_ayudar)

                if cliente_no_puede_ayudar:
                    print(f"\n[OK] FIX 506: Cliente CLARIFICA que NO puede ayudar - '{respuesta_cliente}'")
                    print(f"   Saliendo de ESPERANDO_TRANSFERENCIA → Ofrecer contacto de Bruce")
                    self.estado_conversacion = EstadoConversacion.OFRECIENDO_CONTACTO_BRUCE
                    return "Entiendo, no se preocupe. ¿Me permite dejarle mi número para que el encargado nos contacte cuando tenga oportunidad?"

                if cliente_volvio:
                    print(f"\n[OK] FIX 482: Cliente VOLVIÓ de la espera - '{respuesta_cliente}'")
                    print(f"   Cambiando estado a CONVERSACION_NORMAL para continuar")
                    self.estado_conversacion = EstadoConversacion.CONVERSACION_NORMAL
                    # NO retornar None, continuar con procesamiento normal (GPT)
                else:
                    # FIX 415/498: Ya dijo "Claro, espero." → SILENCIARSE pero NO colgar
                    print(f"\n[WARN] FIX 415/498: Bruce YA dijo 'Claro, espero.' - Esperando en SILENCIO")
                    print(f"   Cliente dijo: \"{respuesta_cliente}\" - NO responder (esperar transferencia)")
                    # FIX 498: Retornar cadena vacía para silenciarse SIN colgar (None = IVR = colgar)
                    return ""

            # FIX 578: Re-verificar estado - FIX 482 pudo haberlo cambiado a CONVERSACION_NORMAL
            if self.estado_conversacion != EstadoConversacion.ESPERANDO_TRANSFERENCIA:
                print(f"   FIX 578: Estado cambió a {self.estado_conversacion} - NO decir 'Claro, espero'")
                # No hacer return - caer al procesamiento normal (GPT más abajo)
            else:
                # Primera vez diciendo "Claro, espero." en esta transferencia
                print(f"\n[EMOJI] FIX 389/415: Cliente pidiendo esperar/transferir - Estado: ESPERANDO_TRANSFERENCIA")
                print(f"   Cliente dijo: \"{respuesta_cliente}\"")
                print(f"   → Respondiendo 'Claro, espero.' SIN llamar GPT")

                respuesta_espera = "Claro, espero."

                self.conversation_history.append({
                    "role": "assistant",
                    "content": respuesta_espera
                })

                return respuesta_espera

        # ============================================================
        # FIX 386: ANÁLISIS DE SENTIMIENTO EN TIEMPO REAL
        # ============================================================
        sentimiento_data = self._analizar_sentimiento(respuesta_cliente)

        # Logging del sentimiento detectado
        if sentimiento_data['sentimiento'] != 'neutral':
            emoji_sentimiento = {
                'muy_positivo': '[EMOJI]',
                'positivo': '[EMOJI]',
                'neutral': '[EMOJI]',
                'negativo': '[EMOJI]',
                'muy_negativo': '[EMOJI]'
            }

            print(f"\n{emoji_sentimiento[sentimiento_data['sentimiento']]} FIX 386: Sentimiento detectado")
            print(f"   Emoción: {sentimiento_data['emocion_detectada'].upper()}")
            print(f"   Score: {sentimiento_data['score']:.2f}")
            print(f"   Clasificación: {sentimiento_data['sentimiento']}")

            if sentimiento_data['debe_colgar']:
                print(f"   [EMOJI] ACCIÓN: Cliente muy molesto/enojado → COLGAR INMEDIATAMENTE")

        # Si cliente está MUY molesto → Colgar con despedida educada
        if sentimiento_data['debe_colgar']:
            despedida_disculpa = "Disculpe las molestias. Le agradezco su tiempo. Que tenga excelente día."

            self.conversation_history.append({
                "role": "assistant",
                "content": despedida_disculpa
            })

            # Marcar como no interesado
            self.lead_data["interesado"] = False
            self.lead_data["resultado"] = "CLIENTE MOLESTO - Colgó"
            self.lead_data["estado_llamada"] = "Colgo"
            self.lead_data["estado_animo_cliente"] = "Muy Negativo - Enojado"

            print(f"\n[EMOJI] FIX 386: Terminando llamada por sentimiento muy negativo")
            return despedida_disculpa

        # ============================================================
        # FIX 202: DETECTAR IVR/CONTESTADORAS AUTOMÁTICAS
        # ============================================================
        # Verificar si es la primera o segunda respuesta del cliente
        num_respuestas_cliente = sum(1 for msg in self.conversation_history if msg['role'] == 'user')
        es_primera_respuesta = (num_respuestas_cliente == 1)

        # Analizar respuesta con detector de IVR
        resultado_ivr = self.detector_ivr.analizar_respuesta(
            respuesta_cliente,
            es_primera_respuesta=es_primera_respuesta
        )

        # Logging de detección
        if resultado_ivr["confianza"] >= 0.3:
            emoji = "[EMOJI]" if resultado_ivr["es_ivr"] else "[WARN]"
            print(f"\n{emoji} FIX 202: Análisis IVR")
            print(f"   Confianza: {resultado_ivr['confianza']:.0%}")
            print(f"   Acción: {resultado_ivr['accion'].upper()}")
            print(f"   Razón: {resultado_ivr['razon']}")
            if resultado_ivr['categorias']:
                print(f"   Categorías: {', '.join(resultado_ivr['categorias'])}")

        # Si se detectó IVR con alta confianza → Colgar inmediatamente
        if resultado_ivr["accion"] == "colgar":
            print(f"\n[EMOJI] FIX 202: IVR/CONTESTADORA DETECTADO [EMOJI]")
            print(f"   Confianza: {resultado_ivr['confianza']:.0%}")
            print(f"   Transcripción: \"{respuesta_cliente[:100]}...\"")
            print(f"   Categorías detectadas: {', '.join(resultado_ivr['categorias'])}")
            print(f"   → TERMINANDO LLAMADA AUTOMÁTICAMENTE")

            # Guardar en lead_data como IVR detectado
            self.lead_data["resultado_llamada"] = "IVR/Buzón detectado"
            self.lead_data["notas_adicionales"] = (
                f"Sistema automatizado detectado. "
                f"Confianza: {resultado_ivr['confianza']:.0%}. "
                f"Razón: {resultado_ivr['razon'][:100]}"
            )

            # NO generar respuesta de Bruce, terminar directamente
            return None  # None indica que la llamada debe terminar

        # FIX 196: Detectar objeciones cortas LEGÍTIMAS (NO son colgadas ni errores)
        # Cliente dice "pero", "espera", "no", etc. → quiere interrumpir/objetar
        respuesta_lower = respuesta_cliente.lower()
        respuesta_stripped = respuesta_cliente.strip()

        objeciones_cortas_legitimas = ["pero", "espera", "espere", "no", "qué", "que", "eh", "mande", "cómo", "como"]

        es_objecion_corta = respuesta_stripped.lower() in objeciones_cortas_legitimas

        if es_objecion_corta:
            # Cliente quiere interrumpir/objetar - NO es fin de llamada
            print(f"[EMOJI] FIX 196: Objeción corta detectada: '{respuesta_cliente}' - continuando conversación")

            # Agregar contexto para que GPT maneje la objeción apropiadamente
            self.conversation_history.append({
                "role": "system",
                "content": f"[SISTEMA] Cliente dijo '{respuesta_cliente}' (objeción/duda/interrupción). Responde apropiadamente: si es 'pero' pide que continúe ('¿Sí, dígame?'), si es 'espera' confirma que esperas, si es 'no' pregunta qué duda tiene, si es 'qué/mande/cómo' repite brevemente lo último que dijiste."
            })

            print(f"   [OK] FIX 196: Contexto agregado para GPT - manejará objeción corta")

        # FIX 128/129: DETECCIÓN AVANZADA DE INTERRUPCIONES Y TRANSCRIPCIONES ERRÓNEAS DE WHISPER

        # FIX 153: Detectar interrupciones cortas (cliente dice algo mientras Bruce habla)
        # MEJORADO: NO detectar como interrupción si cliente responde apropiadamente
        palabras_interrupcion = respuesta_stripped.split()

        # FIX 156: Palabras clave de respuestas válidas (MEJORADO - búsqueda parcial)
        # Si la respuesta CONTIENE estas palabras, NO es interrupción
        palabras_validas = [
            "hola", "bueno", "diga", "dígame", "digame", "adelante",
            "buenos días", "buenos dias", "buen día", "buen dia",
            "claro", "ok", "vale", "perfecto", "si", "sí", "no",
            "aló", "alo", "buenas", "qué onda", "que onda", "mande",
            "a sus órdenes", "ordenes", "qué necesita", "que necesita"
        ]

        # Verificar si la respuesta CONTIENE alguna palabra válida (no exacta)
        es_respuesta_valida = any(palabra in respuesta_lower for palabra in palabras_validas)

        # FIX 156: Solo es interrupción si:
        # 1. Es corta (<=3 palabras)
        # 2. NO contiene palabras válidas
        # 3. Conversación temprana (<=6 mensajes)
        es_interrupcion_corta = (
            len(palabras_interrupcion) <= 3 and
            not es_respuesta_valida and
            len(self.conversation_history) <= 6
        )

        # FIX 129: LISTA EXPANDIDA de transcripciones erróneas comunes de Whisper
        # Basado en análisis de logs reales
        transcripciones_erroneas = [
            # Errores críticos de sintaxis/gramática
            "que no me hablas", "no me hablas", "que me hablas",
            "la que no me hablas", "qué marca es la que no me hablas",
            "que marca es la que", "cual marca es la que",
            "de que marca", "qué marca",
            "y peso para servirle",  # Debería ser "A sus órdenes"
            "más que nada",  # Debería ser "más que nada"

            # Frases contradictorias o sin sentido
            "si no por correo no no agarro nada",
            "si no, por correo no, no agarro",
            "ahorita no muchachos no se encuentran",
            "no, que no te puedo no es por correo",
            "sí sí aquí estamos de este a ver",

            # Respuestas muy cortas sospechosas
            "oc",  # Debería ser "ok"
            "camarón",  # Sin contexto
            "moneda",  # Sin contexto

            # Fragmentaciones extrañas de emails
            "arroba punto com",  # Email incompleto
            "punto leos",  # Fragmento de email
            "compras a roberto",  # "arroba" transcrito como "a"
            "arroba el primerito",

            # Contextos incorrectos
            "el gerente de tienda de armas",  # En contexto ferretería
            "siri dime un trabalenguas",  # Cliente activó Siri

            # Sistemas IVR mal transcritos
            "matriz si conoce el número de extensión",
            "grabes un mensaje marque la tecla gato",
            "marque la tecla gato",

            # Nombres mal transcritos (patrones comunes)
            "o jedi",  # Debería ser "Yahir"
            "jail",  # Debería ser "Jair"
        ]

        # FIX 129: ENFOQUE 2 - Análisis de contexto y coherencia
        es_transcripcion_erronea = any(frase in respuesta_lower for frase in transcripciones_erroneas)

        # Validaciones adicionales de coherencia
        es_respuesta_muy_corta_sospechosa = (
            len(respuesta_stripped) <= 3 and
            respuesta_lower not in ["sí", "si", "no", "ok"] and
            len(self.conversation_history) > 3
        )

        # Detectar respuestas vacías o solo espacios
        es_respuesta_vacia = len(respuesta_stripped) == 0

        # FIX 138D: Detectar múltiples negaciones (signo de error de transcripción)
        # MEJORADO: Ignorar casos válidos como "Así no, no está" o "Ahorita no, no puedo"
        tiene_negaciones_multiples = False

        # Contar "no" repetido (más de 2 veces seguidas es sospechoso)
        if respuesta_lower.count("no no no") > 0:
            tiene_negaciones_multiples = True

        # "no no" sin contexto válido
        elif "no no" in respuesta_lower:
            # Verificar si NO es un caso válido como "así no, no está"
            # FIX 525 BRUCE1670: Agregar casos válidos para "no, no sé" y "no, no se encuentra"
            casos_validos = [
                "así no, no", "ahorita no, no", "ahora no, no",
                "todavía no, no", "pues no, no", "no sé, no",
                "creo que no, no", "por ahora no, no",
                # FIX 525: Casos donde cliente dice "no, no sé" o "no, no se encuentra"
                "no, no sé", "no, no se", "no no sé", "no no se",
                "no, no está", "no, no esta", "no no está", "no no esta",
                "no, no hay", "no no hay",
                "no, no lo", "no no lo",  # "no, no lo conozco"
                "no, no la", "no no la",  # "no, no la tengo"
                "no, no tengo", "no no tengo",
                "no, no puedo", "no no puedo"
            ]
            if not any(caso in respuesta_lower for caso in casos_validos):
                tiene_negaciones_multiples = True

        # Detectar fragmentos de email sin @ (error común de Whisper)
        tiene_fragmento_email_sin_arroba = (
            ("arroba" in respuesta_lower or "punto com" in respuesta_lower) and
            "@" not in respuesta_cliente and
            "." not in respuesta_cliente
        )

        # Combinar todas las detecciones
        es_transcripcion_erronea = (
            es_transcripcion_erronea or
            es_respuesta_muy_corta_sospechosa or
            tiene_negaciones_multiples or
            tiene_fragmento_email_sin_arroba
        )

        # Debug: Reportar qué tipo de error se detectó
        if es_transcripcion_erronea:
            razones = []
            if any(frase in respuesta_lower for frase in transcripciones_erroneas):
                razones.append("patrón conocido")
            if es_respuesta_muy_corta_sospechosa:
                razones.append("respuesta muy corta")
            if tiene_negaciones_multiples:
                razones.append("negaciones múltiples")
            if tiene_fragmento_email_sin_arroba:
                razones.append("fragmento email")
            print(f"[WARN] FIX 129: Posible error Whisper detectado: {', '.join(razones)}")

        # Si detectamos interrupción o transcripción errónea, agregar indicación para usar nexo
        if (es_interrupcion_corta or es_transcripcion_erronea) and len(self.conversation_history) >= 3:
            ultimo_mensaje_bruce = None
            for msg in reversed(self.conversation_history):
                if msg['role'] == 'assistant':
                    ultimo_mensaje_bruce = msg['content']
                    break

            # FIX 129/188/198: Mensajes específicos según SEVERIDAD del error detectado
            if es_transcripcion_erronea and not es_interrupcion_corta:
                # FIX 198: Clasificar severidad del error en 3 niveles

                # NIVEL 1: Errores CRÍTICOS (no se entiende NADA)
                errores_criticos = [
                    "que no me hablas", "no me hablas", "qué marca es la que no me hablas",
                    "y peso para servirle", "camarón", "moneda", "o jedi", "jail"
                ]
                es_error_critico = any(err in respuesta_lower for err in errores_criticos)

                # NIVEL 2: Error PARCIAL en dato solicitado (WhatsApp/Email)
                estaba_pidiendo_dato = any(kw in ultimo_mensaje_bruce.lower() for kw in
                                          ["whatsapp", "correo", "email", "teléfono", "telefono", "número", "numero"])

                # NIVEL 3: Error LEVE (respuesta con sentido pero palabras extrañas)
                # Este es el nivel por defecto si no es crítico ni dato solicitado

                if es_error_critico:
                    # NIVEL 1: ERROR CRÍTICO → Pedir repetir cortésmente
                    self.conversation_history.append({
                        "role": "system",
                        "content": f"""[SISTEMA - FIX 198 NIVEL 1] [EMOJI] ERROR CRÍTICO DE TRANSCRIPCIÓN

El cliente dijo algo pero la transcripción no tiene sentido: "{respuesta_cliente}"

[WARN] CONTEXTO:
Tu último mensaje: {ultimo_mensaje_bruce[:80] if ultimo_mensaje_bruce else 'N/A'}

[EMOJI] ACCIÓN REQUERIDA:
Pide cortésmente que repita: "Disculpe, no le escuché bien por la línea, ¿me lo podría repetir?"

[ERROR] NO menciones palabras de la transcripción errónea
[ERROR] NO repitas tu pregunta anterior textualmente (usa palabras diferentes)
[OK] SÍ usa frase genérica de "no escuché bien"
[OK] SÍ mantén tono profesional y cortés
"""
                    })
                    print(f"[EMOJI] FIX 198 NIVEL 1: Error crítico Whisper → pedir repetir")

                elif estaba_pidiendo_dato:
                    # NIVEL 2: ERROR PARCIAL EN DATO → Intentar interpretar PRIMERO
                    self.conversation_history.append({
                        "role": "system",
                        "content": f"""[SISTEMA - FIX 198 NIVEL 2] [WARN] ERROR PARCIAL EN DATO SOLICITADO

Estabas pidiendo: {ultimo_mensaje_bruce[:50]}...
Cliente respondió (con posibles errores): "{respuesta_cliente}"

[EMOJI] ESTRATEGIA DE 3 PASOS:

1. **PRIMERO: Intenta interpretar el dato**
   - Si parece WhatsApp (contiene números): Extrae los dígitos visibles
   - Si parece email (tiene palabras como gmail, hotmail, arroba): Intenta reconstruir
   - Ejemplo: "tres tres uno camarón cinco" → 331X5 (falta 1 dígito)

2. **SI lograste interpretar ≥70% del dato:**
   - Confirma lo que entendiste: "Perfecto, solo para confirmar, ¿es el [DATO QUE INTERPRETASTE]?"
   - Ejemplo: "Entonces el WhatsApp es 331-XXX-5678, ¿correcto?"
   - Ejemplo: "El correo es nombre@gmail.com, ¿correcto?"

3. **SI NO lograste interpretar ≥70%:**
   - Pide repetir MÁS DESPACIO: "Disculpe, no le escuché completo, ¿me lo podría repetir más despacio?"

[ERROR] NO digas "ya lo tengo" si NO lo tienes completo
[ERROR] NO repitas palabras erróneas al cliente
[OK] SÍ confirma el dato si lo interpretaste parcialmente
[OK] SÍ pide repetir SOLO si interpretación es <70%
[OK] SÍ mantén tono profesional (no hagas sentir mal al cliente)
"""
                    })
                    print(f"[WARN] FIX 198 NIVEL 2: Error parcial en dato → intentar interpretar")

                else:
                    # NIVEL 3: ERROR LEVE → Interpretar intención y continuar
                    self.conversation_history.append({
                        "role": "system",
                        "content": f"""[SISTEMA - FIX 198 NIVEL 3] ℹ[EMOJI] ERROR LEVE DE TRANSCRIPCIÓN

Cliente respondió (con errores leves): "{respuesta_cliente}"

[EMOJI] ESTRATEGIA:
1. Interpreta la INTENCIÓN general (positivo/negativo/pregunta/duda)
2. Continúa la conversación basándote en la intención
3. NO menciones las palabras erróneas
4. NO pidas repetir por errores leves

Ejemplo de interpretación:
- Transcripción: "oc, así a ver" → Intención: Confirmación positiva ("ok, sí, a ver")
- Transcripción: "pero no sé" → Intención: Duda/inseguridad
- Transcripción: "y eso que es" → Intención: Pregunta de aclaración

[ERROR] NO preguntes sobre palabras sin sentido
[ERROR] NO pidas repetir (es error leve, intención es clara)
[ERROR] NO hagas sentir al cliente que no lo entiendes
[OK] SÍ continúa la conversación fluidamente
[OK] SÍ responde basándote en la intención general
[OK] SÍ mantén naturalidad en la conversación
"""
                    })
                    print(f"[OK] FIX 198 NIVEL 3: Error leve → interpretar intención y continuar")

            elif es_interrupcion_corta and ultimo_mensaje_bruce and len(ultimo_mensaje_bruce) > 50:
                # FIX 182/184: Detectar si estamos ESPERANDO información del cliente O si está deletreando
                mensajes_recopilacion = [
                    "whatsapp", "correo", "email", "teléfono", "telefono", "número", "numero",
                    "nombre", "ciudad", "adelante", "proporcionar", "pasar"
                ]

                # FIX 184/187: Detectar si el cliente está DELETREANDO correo
                # Incluye: arroba, punto, guion bajo, deletreo fonético, Y formato "nombre@gmail.com"
                palabras_deletreo = ["arroba", "punto", "guion", "guión", "bajo", "@", "."]

                # FIX 187: Detectar deletreo fonético (a de amor, m de mama, f de foca)
                patron_deletreo_fonetico = any(
                    patron in respuesta_cliente.lower()
                    for patron in [" de ", "arroba", "punto", "guion", "guión", "bajo"]
                )

                # FIX 187: Detectar formato directo "nombredelnego cio@gmail.com"
                patron_email_directo = "@" in respuesta_cliente or "gmail" in respuesta_cliente.lower() or "hotmail" in respuesta_cliente.lower()

                cliente_deletreando = (
                    any(palabra in respuesta_cliente.lower() for palabra in palabras_deletreo) or
                    patron_deletreo_fonetico or
                    patron_email_directo
                )

                esta_recopilando_info = any(palabra in ultimo_mensaje_bruce.lower() for palabra in mensajes_recopilacion) or cliente_deletreando

                if esta_recopilando_info:
                    # Estamos recopilando información - el cliente está RESPONDIENDO o DELETREANDO
                    if cliente_deletreando:
                        # FIX 184: Cliente está DELETREANDO - NO interrumpir
                        self.conversation_history.append({
                            "role": "system",
                            "content": f"""[SISTEMA - FIX 184] [EMOJI] CLIENTE ESTÁ DELETREANDO CORREO - NO INTERRUMPIR

El cliente está DELETREANDO su correo electrónico: "{respuesta_cliente}"

[WARN] CRÍTICO:
- NO digas NADA mientras deletrea (NO "Sigo aquí", NO "Adelante")
- PERMANECE EN SILENCIO TOTAL
- ESPERA a que TERMINE de deletrear COMPLETAMENTE
- Solo DESPUÉS de que termine, di: "Perfecto, ya lo tengo anotado."

Si interrumpes, el cliente se FRUSTRA y CUELGA.

EJEMPLO:
Cliente: "super block arroba issa punto com"
Bruce: [SILENCIO - NO INTERRUMPIR]
(Sistema espera siguiente input del cliente o fin de deletreo)
"""
                        })
                        print(f"[EMOJI] FIX 184: Cliente DELETREANDO correo - NO INTERRUMPIR")
                    else:
                        # Cliente está respondiendo pregunta normal
                        self.conversation_history.append({
                            "role": "system",
                            "content": f"""[SISTEMA - FIX 182] [WARN] CLIENTE ESTÁ RESPONDIENDO TU PREGUNTA

Tu último mensaje fue: "{ultimo_mensaje_bruce[:100]}..."

El cliente está PROPORCIONANDO la información que pediste (WhatsApp, correo, nombre, etc.).

NO uses frases de nexo como "Perfecto me lo podrá comunicar"
SOLO di frases de CONTINUIDAD:
- "Sigo aquí"
- "Adelante por favor"
- "Lo estoy anotando"
- "Perfecto, continúe"

Ejemplo CORRECTO:
Bruce: "¿Cuál es su correo?"
Cliente: "Super block arroba"
Bruce: "Sigo aquí" (NO "Perfecto me lo podrá comunicar")
Cliente: "issa punto com"
Bruce: "Perfecto, ya lo tengo anotado."
"""
                        })
                        print(f"[EMOJI] FIX 182: Cliente respondiendo pregunta - usando continuidad simple")
                else:
                    # Interrupción corta durante PRESENTACIÓN
                    self.conversation_history.append({
                        "role": "system",
                        "content": f"""[SISTEMA - FIX 128/182] [WARN] INTERRUPCIÓN EN PRESENTACIÓN

Cliente interrumpió mientras hablabas. Tu último mensaje fue: "{ultimo_mensaje_bruce[:100]}..."

DEBES usar una frase de NEXO para retomar naturalmente:
- "Como le comentaba..."
- "Lo que le decía..."
- "Entonces, como le mencionaba..."
- "Perfecto, entonces..."

NO repitas el mensaje completo desde el inicio.

Ejemplo correcto:
"Perfecto, entonces como le comentaba, me comunico de NIOVAL sobre productos ferreteros..."
"""
                    })
                    print(f"[EMOJI] FIX 128/182: Interrupción en presentación - forzando uso de nexo")

        # FIX 75/81: DETECCIÓN TEMPRANA DE OBJECIONES - Terminar ANTES de llamar GPT
        # CRÍTICO: Detectar CUALQUIER mención de proveedor exclusivo/Truper y COLGAR

        # FIX 81: DEBUG - Imprimir SIEMPRE para verificar que este código se ejecuta
        print(f"[DEBUG] FIX 81 DEBUG: Verificando objeciones en: '{respuesta_cliente[:80]}'")

        # Patrones de objeción definitiva (cliente NO quiere seguir)
        # FIX 75/80/81: AMPLIADOS para detectar TODAS las variaciones de "solo Truper"
        objeciones_terminales = [
            # Truper específico - CUALQUIER mención
            "truper", "trúper", "tru per",
            "productos truper", "producto truper",
            "trabajamos truper", "manejamos truper",
            "solo truper", "solamente truper", "únicamente truper",
            # Solo/únicamente/solamente trabajamos/manejamos
            "únicamente trabajamos", "solamente trabajamos", "solo trabajamos",
            "únicamente manejamos", "solamente manejamos", "solo manejamos",
            "únicamente productos", "solamente productos", "solo productos",
            "trabajamos productos", "manejamos productos",  # FIX 80: Agregado
            # Proveedor exclusivo
            "proveedor principal", "principal proveedor",  # FIX 80: Agregado
            "proveedor fijo", "ya tenemos proveedor",
            "tenemos contrato con", "somos distribuidores de",
            "ya tenemos proveedor exclusivo", "contrato exclusivo",
            # No podemos
            "no podemos manejar otras", "no podemos manejar más",
            "no manejamos otras marcas", "no queremos otras marcas"
        ]

        for objecion in objeciones_terminales:
            if objecion in respuesta_lower:
                print(f"[EMOJI] FIX 75: OBJECIÓN TERMINAL DETECTADA - COLGANDO INMEDIATAMENTE")
                print(f"   Patrón detectado: '{objecion}'")
                print(f"   Respuesta cliente: '{respuesta_cliente[:100]}'")

                # FIX 75/79: Marcar como no interesado Y estado Colgo
                self.lead_data["interesado"] = False
                self.lead_data["resultado"] = "NO INTERESADO"
                self.lead_data["pregunta_7"] = "Cliente tiene proveedor exclusivo (Truper u otro)"
                self.lead_data["estado_llamada"] = "Colgo"  # FIX 75: Esto fuerza el hangup

                # FIX 79: Despedida más cálida y profesional que deja la puerta abierta
                # Evita tono seco y agresivo cuando cliente menciona proveedor exclusivo
                respuesta_despedida = "Perfecto, comprendo que ya trabajan con un proveedor fijo. Le agradezco mucho su tiempo y por la información. Si en el futuro necesitan comparar precios o buscan un proveedor adicional, con gusto pueden contactarnos. Que tenga excelente día."

                self.conversation_history.append({
                    "role": "assistant",
                    "content": respuesta_despedida
                })

                return respuesta_despedida

        # FIX 81: DEBUG - Si llegamos aquí, NO se detectó ninguna objeción
        print(f"[OK] FIX 81 DEBUG: NO se detectó objeción terminal. Continuando conversación normal.")

        # FIX 170/237: Detectar cuando cliente va a PASAR al encargado (AHORA)
        # Estas frases indican transferencia INMEDIATA, NO futura
        patrones_transferencia_inmediata = [
            # Transferencia directa
            "te puedo pasar", "te paso", "le paso", "se lo paso",
            "te lo paso", "ahorita te lo paso", "te comunico",
            "me lo comunica", "me lo pasa", "pásamelo",
            # FIX 811: BRUCE2522 - Variantes con "ahí" ("ahí le paso", "ahí se lo paso")
            "ahí le paso", "ahi le paso", "ahí se lo paso", "ahi se lo paso",
            "ahí te lo paso", "ahi te lo paso",
            # FIX 350: "déjeme lo transfiero" y variantes
            "déjeme lo transfiero", "dejeme lo transfiero",
            "déjeme la transfiero", "dejeme la transfiero",
            "lo transfiero", "la transfiero", "le transfiero",
            "te transfiero", "déjeme transferirlo", "dejeme transferirlo",
            # FIX 237/380: Solicitud de espera - agregados más patrones
            "dame un momento", "espera un momento", "espérame", "un segundito",
            "permíteme", "permiteme", "déjame ver", "dejame ver",
            "un momento",  # FIX 237: Solo "un momento" sin prefijo
            "un segundo",  # FIX 237
            "tantito",     # FIX 237: Mexicanismo
            "ahorita",     # FIX 237: Cuando dice solo "ahorita" (va a hacer algo)
            "me permite",  # FIX 237
            "me permites", # FIX 237
            # FIX 380: "No me cuelgue" indica que va a buscar al encargado
            "no me cuelgue", "no cuelgue", "no me cuelgues", "no cuelgues",
            "espérame tantito", "esperame tantito",
            # FIX 381: "Hágame el lugar" = modismo mexicano de "espéreme"
            "hágame el lugar", "hagame el lugar",
            "hágame favor", "hagame favor",
            "hágame un favor", "hagame un favor",
            # Confirmación de disponibilidad + acción
            "sí está aquí", "está aquí", "está disponible",
            "ya viene", "ahorita viene", "está por aquí"
        ]

        # FIX 216/318/374: Patrones que INVALIDAN la transferencia (negaciones)
        # Si el cliente dice "NO está disponible", NO es transferencia
        patrones_negacion = [
            "no está disponible", "no esta disponible",
            "no está aquí", "no esta aquí", "no esta aqui",
            "no se encuentra", "no lo encuentro", "no la encuentro",
            "no viene", "no va a venir", "no puede", "no hay nadie",
            # FIX 318/374: "no está ahorita" / "ahorita no" - el encargado NO está
            "no está ahorita", "no esta ahorita",
            "ahorita no está", "ahorita no esta",
            "ahorita no", "no ahorita",  # FIX 374: Cubrir "ahorita no no está"
            "no, no está", "no, no esta"
        ]

        # FIX 229: Patrones que indican que el cliente va a DAR INFORMACIÓN (NO transferencia)
        # "Le paso el correo" = cliente va a dar correo, NO pasar al encargado
        # FIX 622A: BRUCE2041 - "le paso un teléfono" = dar número, NO transferir
        patrones_dar_info = [
            "paso el correo", "paso mi correo", "paso un correo",
            "doy el correo", "doy mi correo", "le doy el correo",
            "paso el mail", "paso mi mail", "paso el email",
            "te paso el número", "le paso el número", "paso mi número",
            "te paso el whatsapp", "le paso el whatsapp", "paso mi whatsapp",
            "te lo paso por correo", "se lo paso por correo",
            "anota", "apunta", "toma nota",
            # FIX 622A: BRUCE2041 - "paso un teléfono/número" = OFRECE dato
            "paso un teléfono", "paso un telefono", "paso un número", "paso un numero",
            "paso el teléfono", "paso el telefono",
            "paso un cel", "paso un celular",
            "le paso un", "te paso un",  # "le paso un [teléfono/número/correo]"
        ]

        # FIX 229: Verificar si cliente va a dar información
        cliente_da_info = any(info in respuesta_lower for info in patrones_dar_info)

        # FIX 615: BRUCE2030 - "te lo paso" + número = NO es transferencia
        # Si el texto contiene "número", "teléfono", o dígitos, cliente está DANDO un número
        # NO activar modo transferencia aunque diga "te lo paso"
        import re as re_615
        cliente_dictando_numero_615 = any(p in respuesta_lower for p in [
            'número es', 'numero es', 'el número', 'el numero',
            'teléfono es', 'telefono es', 'mi teléfono', 'mi telefono',
            'mi número', 'mi numero', 'mi cel', 'mi celular',
        ])
        tiene_digitos_secuencia_615 = bool(re_615.search(r'\d{3,}', respuesta_lower))
        if cliente_dictando_numero_615 or tiene_digitos_secuencia_615:
            cliente_da_info = True  # Forzar como "dando información"
            print(f"[OK] FIX 615: BRUCE2030 - Cliente DICTANDO NÚMERO - NO es transferencia")
            print(f"   Detectado: numero={cliente_dictando_numero_615}, digitos={tiene_digitos_secuencia_615}")

        # FIX 216: Primero verificar si hay negación
        hay_negacion = any(neg in respuesta_lower for neg in patrones_negacion)

        if hay_negacion:
            print(f"[EMOJI] FIX 216: Detectada NEGACIÓN - NO es transferencia")
            print(f"   Respuesta cliente: '{respuesta_cliente[:100]}'")
            # NO retornar "Claro, espero" - continuar con flujo normal
        elif cliente_da_info:
            print(f"[EMAIL] FIX 229: Cliente va a DAR INFORMACIÓN - NO es transferencia")
            print(f"   Respuesta cliente: '{respuesta_cliente[:100]}'")
            # NO retornar "Claro, espero" - dejar que GPT pida el correo/dato
        else:
            # FIX 460: BRUCE1381 - Detectar si cliente dice LLAMAR DESPUÉS vs TRANSFERIR AHORA
            # Si cliente dice "puede marcar en otro momento", "llame después", etc.
            # NO es transferencia - es sugerencia de llamar en otro momento
            cliente_dice_llamar_despues = any(frase in respuesta_lower for frase in [
                'puede marcar', 'marque después', 'marque despues', 'llame después', 'llame despues',
                'llámenos después', 'llamenos despues', 'marcar en otro', 'llamar en otro',
                'vuelva a llamar', 'intente más tarde', 'intente mas tarde',
                'regrese la llamada', 'mejor llame', 'otro momento', 'otro dia', 'otro día',
                'más tarde', 'mas tarde', 'en la tarde', 'en la mañana', 'mañana',
                'el mostrador', 'nada más atendemos', 'nada mas atendemos', 'solo atendemos',
                'no se la maneja', 'no le puedo', 'no tengo esa información', 'no tengo esa informacion'
            ])

            # FIX 749B: BRUCE2388 - "Te comunico sobre" = "I inform you about", NOT transfer
            # "Te comunico sobre una línea directa de atención a clientes" matched "te comunico"
            # but client was explaining their business, NOT transferring the call
            _te_comunico_explicacion_749 = any(p in respuesta_lower for p in [
                'te comunico sobre', 'le comunico sobre', 'se comunica a',
                'te comunico que', 'le comunico que', 'comunico de que',
                'linea directa de atencion', 'línea directa de atención',
                'linea de atencion', 'línea de atención'
            ])

            if cliente_dice_llamar_despues:
                print(f"[EMOJI] FIX 460: Cliente sugiere LLAMAR DESPUÉS - NO es transferencia")
                print(f"   Respuesta cliente: '{respuesta_cliente[:100]}'")
                # NO activar transferencia - dejar que GPT maneje con despedida apropiada
            elif _te_comunico_explicacion_749:
                print(f"[OK] FIX 749B: BRUCE2388 - 'te comunico sobre/que' = explicación, NO transferencia")
                print(f"   Respuesta cliente: '{respuesta_cliente[:100]}'")
                # NO activar transferencia - dejar que GPT responda normalmente
            else:
                for patron in patrones_transferencia_inmediata:
                    if patron in respuesta_lower:
                        # FIX 622B: BRUCE2041 - Respetar anti-loop de FIX 508
                        # Si ya dijo "Claro, espero" en los últimos 30s, NO repetir
                        import time as time_622b
                        ultimo_claro_ts = getattr(self, 'ultimo_claro_espero_timestamp', 0)
                        tiempo_desde_622b = time_622b.time() - ultimo_claro_ts
                        if ultimo_claro_ts > 0 and tiempo_desde_622b < 30:
                            print(f"   FIX 622B: ANTI-LOOP en FIX 170 - Ya dijo 'Claro, espero' hace {tiempo_desde_622b:.1f}s")
                            print(f"   → NO repetir, dejar que GPT procese")
                            break  # Salir del loop de patrones, continuar con GPT

                        print(f"[EMOJI] FIX 170: Cliente va a PASAR al encargado AHORA")
                        print(f"   Patrón detectado: '{patron}'")
                        print(f"   Respuesta cliente: '{respuesta_cliente[:100]}'")

                        # Marcar flag de transferencia
                        self.esperando_transferencia = True

                        # Respuesta simple de espera
                        respuesta_espera = "Claro, espero."

                        # FIX 622B: Actualizar timestamp para anti-loop
                        self.ultimo_claro_espero_timestamp = time_622b.time()

                        self.conversation_history.append({
                            "role": "assistant",
                            "content": respuesta_espera
                        })

                        print(f"[OK] FIX 170: Bruce esperará (timeout extendido a 20s)")
                        return respuesta_espera

        # FIX 238/262: Detectar cuando encargado LLEGA después de esperar
        # Si estábamos esperando transferencia y cliente dice "¿Bueno?" = encargado llegó
        if self.esperando_transferencia:
            patrones_encargado_llego = [
                "bueno", "sí", "si", "diga", "hola", "alo", "aló",
                "qué pasó", "que paso", "mande", "a ver",
                # FIX 262: Agregar más patrones de "llegada"
                "dígame", "digame", "sí dígame", "si digame",
                "a sus órdenes", "a sus ordenes",
                "para servirle", "en qué le ayudo", "en que le ayudo",
                "sí bueno", "si bueno", "sí mande", "si mande"
            ]

            # Limpiar respuesta para comparar
            respuesta_limpia = respuesta_lower.strip().replace("¿", "").replace("?", "").strip()

            encargado_llego = any(patron == respuesta_limpia or patron in respuesta_limpia.split()
                                  for patron in patrones_encargado_llego)

            if encargado_llego:
                print(f"\n[EMOJI] FIX 238: ENCARGADO LLEGÓ después de esperar")
                print(f"   Cliente dijo: '{respuesta_cliente}'")
                print(f"   Bruce estaba esperando transferencia")

                # Reset flag de transferencia
                self.esperando_transferencia = False

                # Respuesta corta de presentación (ya nos presentamos antes)
                respuesta_encargado = "Sí, buen día. Soy Bruce de la marca NIOVAL, productos de ferretería. ¿Usted es el encargado de compras?"

                self.conversation_history.append({
                    "role": "assistant",
                    "content": respuesta_encargado
                })

                print(f"[OK] FIX 238: Bruce se presenta al encargado")
                return respuesta_encargado

        # Extraer información clave de la respuesta
        self._extraer_datos(respuesta_cliente)

        # Verificar si se detectó un estado especial (Buzon, Telefono Incorrecto, Colgo, No Respondio, No Contesta)
        # Si es así, generar respuesta de despedida automática
        if self.lead_data["estado_llamada"] in ["Buzon", "Telefono Incorrecto", "Colgo", "No Respondio", "No Contesta"]:
            # FIX 22A: Respuestas de despedida apropiadas según el estado
            # IMPORTANTE: Estados "Colgo", "No Respondio", "No Contesta" retornan cadena vacía
            # porque la llamada YA terminó y NO hay que decir nada más
            respuestas_despedida = {
                "Buzon": "Disculpe, parece que entró el buzón de voz. Le llamaré en otro momento. Que tenga buen día.",
                "Telefono Incorrecto": "Disculpe las molestias, parece que hay un error con el número. Que tenga buen día.",
                "Colgo": "",  # Llamada terminada - NO decir nada
                "No Respondio": "",  # No hubo respuesta - NO decir nada
                "No Contesta": ""  # Nadie contestó - NO decir nada
            }

            respuesta_agente = respuestas_despedida.get(self.lead_data["estado_llamada"], "Que tenga buen día.")

            # FIX 421: NO repetir despedida automática si ya se dijo (caso BRUCE1227)
            # Similar a FIX 415 para "Claro, espero."
            # Verificar últimos 3 mensajes de Bruce
            if respuesta_agente:
                ultimos_bruce_temp_fix421 = [
                    msg['content'].lower() for msg in self.conversation_history[-6:]
                    if msg['role'] == 'assistant'
                ]

                # Buscar frases clave de la despedida en historial
                frases_despedida_ya_dicha = [
                    'disculpe las molestias',
                    'error con el número',
                    'entró el buzón',
                    'le llamaré en otro momento'
                ]

                bruce_ya_se_despidio = any(
                    frase in msg for frase in frases_despedida_ya_dicha
                    for msg in ultimos_bruce_temp_fix421
                )

                if bruce_ya_se_despidio:
                    # FIX 421: Ya dijo despedida → NO repetir (silencio)
                    print(f"\n[EMOJI]  FIX 421: Bruce YA se despidió - NO repetir despedida")
                    print(f"   Cliente dijo: \"{respuesta_cliente[:50]}\" - NO responder")
                    # Retornar cadena vacía para terminar llamada sin repetir
                    return ""

            # Solo agregar al historial si hay respuesta (no vacía)
            if respuesta_agente:
                self.conversation_history.append({
                    "role": "assistant",
                    "content": respuesta_agente
                })

            return respuesta_agente

        # FIX 792: Safety net template ANTES de GPT full
        # Si FSM retornó None pero estado_conversacion es conocido → template
        _narrow_792 = self._try_narrow_prompt_792(respuesta_cliente)
        if _narrow_792:
            print(f"\n [FIX 792] Template fallback: estado={self.estado_conversacion.value} → '{_narrow_792[:60]}'")
            self.conversation_history.append({"role": "assistant", "content": _narrow_792})
            self.turno_actual = getattr(self, 'turno_actual', 0) + 1
            return _narrow_792

        # Generar respuesta con GPT-4o-mini (OPTIMIZADO para baja latencia)
        try:
            import time
            inicio_gpt = time.time()

            # FIX 68: CRÍTICO - Reparar construcción de historial
            # PROBLEMA: Se estaba duplicando system prompt y perdiendo historial

            # 1. Construir prompt dinámico PRIMERO (incluye memoria de conversación)
            prompt_optimizado = self._construir_prompt_dinamico()

            # 2. Filtrar SOLO mensajes user/assistant (NO system) del historial
            mensajes_conversacion = [msg for msg in self.conversation_history
                                    if msg['role'] in ['user', 'assistant']]

            # 3. Limitar a últimos 12 mensajes (6 turnos completos user+assistant)
            # AUMENTADO de 6 a 12 para mejor memoria
            MAX_MENSAJES_CONVERSACION = 12
            if len(mensajes_conversacion) > MAX_MENSAJES_CONVERSACION:
                mensajes_conversacion = mensajes_conversacion[-MAX_MENSAJES_CONVERSACION:]
                print(f"[WRENCH] FIX 68: Historial limitado a últimos {MAX_MENSAJES_CONVERSACION} mensajes")

            # 4. Debug: Imprimir últimos 2 mensajes para diagnóstico
            if len(mensajes_conversacion) >= 2:
                print(f"\n[EMOJI] FIX 68: Últimos 2 mensajes en historial:")
                for msg in mensajes_conversacion[-2:]:
                    preview = msg['content'][:60] + "..." if len(msg['content']) > 60 else msg['content']
                    print(f"   {msg['role'].upper()}: {preview}")

            # FIX 491: Calcular max_tokens dinámicamente según complejidad
            max_tokens_dinamico = self._calcular_max_tokens_dinamico(respuesta_cliente)
            print(f"[EMOJI]  FIX 491: max_tokens dinámico = {max_tokens_dinamico} (basado en complejidad)")

            # FIX 533: AUDITORIA 29/01 - Retry automático en APITimeoutError de OpenAI
            # Problema: 9 timeouts de OpenAI detectados sin retry
            # Solución: Intentar 2 veces con timeouts progresivamente más cortos
            response = None
            intentos_gpt = 0
            max_intentos_gpt = 2
            timeouts_gpt = [4.0, 2.0]  # FIX 533: Primer intento 4s, retry 2s
            max_tokens_retry = [max_tokens_dinamico, 50]  # FIX 533: Segundo intento con menos tokens

            while intentos_gpt < max_intentos_gpt:
                try:
                    timeout_actual = timeouts_gpt[intentos_gpt]
                    tokens_actual = max_tokens_retry[intentos_gpt]

                    if intentos_gpt > 0:
                        print(f"   FIX 533: Reintento #{intentos_gpt} con timeout={timeout_actual}s, tokens={tokens_actual}")

                    # FIX 646A: REGLAS ANTI-REPETICIÓN - Prevenir GPT_LOGICA_ROTA
                    # Análisis bugs 2026-02-11: 69% de bugs son GPT repitiendo preguntas ya respondidas
                    # FIX 647: BRUCE2098 - Cliente NO AUTORIZADO → no insistir
                    # FIX 649: BRUCE2106, BRUCE2104 - Formas indirectas de proporcionar datos
                    # FIX 818: Reglas anti-LOGICA_ROTA reforzadas (64% de bugs GPT)
                    reglas_anti_repeticion_646 = {
                        "role": "system",
                        "content": """[SISTEMA - FIX 646A/647] REGLAS CRITICAS ANTI-REPETICION (FIX 818) - LEE ANTES DE RESPONDER:

=== ERROR #1 (30% de bugs): NO REPITAS LA PREGUNTA DEL ENCARGADO ===
REVISA el historial. Si YA preguntaste por el encargado:
- Cliente dijo "no esta/salio/no se encuentra" -> encargado NO ESTÁ. Pide WhatsApp o correo. NO preguntes de nuevo.
- Cliente dijo "yo soy/soy el dueno/habla con el" -> Continua la venta con EL. NO pidas transferencia.
- Cliente dijo "si esta/si se encuentra" -> Pide que te transfieran. NO repitas la pregunta.
PROHIBIDO: Preguntar "se encontrara el encargado?" si ya lo preguntaste en CUALQUIER turno previo.

=== ERROR #2 (19% de bugs): NO PIDAS DATO QUE YA TE DIERON ===
REVISA el historial. Si el cliente YA dicto un numero, correo o dato:
- "Mi WhatsApp es 662..." -> dato YA está capturado. Confirma y despidete.
- "El correo es juan@..." -> dato YA está capturado. Confirma y despidete.
- "Llamame manana a las 9" -> YA DIO HORARIO. Confirma, no pidas otro dato.
- "Te paso el numero..." + dicto numeros -> ESTA DICTANDO. Espera, no interrumpas.
- Si proporcionó datos DIRECTA o INDIRECTAMENTE ("Llame al 555...", "Puede marcar al...", "Contacte al...") -> YA LO TIENES.
Si el cliente ya proporcionó un dato, NO lo pidas de nuevo.
PROHIBIDO: Pedir WhatsApp/correo/telefono si el cliente ya lo proporciono.

=== ERROR #3 (15% de bugs): IDENTIFICA CON QUIEN HABLAS ===
SENALES de que el cliente ES el encargado (NO pidas transferencia):
- "Yo soy el encargado/dueno/yo mero/habla con el"
- "Yo hago las compras/yo decido"
- "Tienes donde anotar?" / "Te paso mis datos" (= listo para comprar = decisor)
- Pregunta precios/productos (= tiene poder de decision)
PROHIBIDO: Pedir "me comunica con el encargado?" a alguien que YA SE IDENTIFICO como encargado.

=== REGLAS ADICIONALES (FIX 655/658/649) ===
4. Si cliente NO ESTÁ AUTORIZADO, NO PUEDE dar datos, o NO LE PERMITEN -> NO insistir.
   Ofrecer enviar catálogo al teléfono general o agendar callback.

5. FIX 655: Negación Explícita - Si el cliente EXPLÍCITAMENTE DIJO QUE NO LO TIENE:
   "No lo tengo", "No tengo ese dato", "No cuento con eso", "La verdad no lo tengo"
   FIX 658: Negación Explícita CORTA - "No", "No, gracias", "No, oiga", "No, joven",
   "No, muchacho", "No por ahorita", "No, está bien"
   -> NO insistir con el mismo dato.
   Alternar: si pidió WhatsApp, ofrecer correo general del negocio. Si no tiene correo, ofrecer callback.

6. "Dígame" como respuesta a tu saludo = "adelante". NO es confusión. Continúa con tu pitch.

7. Si encargado NO ESTÁ o NO PUEDE atender -> ofrecer contacto alternativo (WhatsApp/correo).
   NO simplemente decir "lo llamo después" sin capturar datos.

MAXIMA PRIORIDAD: Verifica el historial COMPLETO antes de generar tu respuesta."""
                    }

                    # Construir mensajes con reglas anti-repetición
                    mensajes_con_reglas = [
                        {"role": "system", "content": prompt_optimizado},
                        *mensajes_conversacion,
                        reglas_anti_repeticion_646
                    ]

                    # FIX 699: Inyectar hechos de Memory Layer en prompt GPT
                    try:
                        if self.memory:
                            contexto_memoria_699 = self.memory.get_gpt_context()
                            if contexto_memoria_699:
                                mensajes_con_reglas.insert(-1, {
                                    "role": "system",
                                    "content": contexto_memoria_699
                                })
                                print(f"   [MEMORY] FIX 699: Inyectado contexto memoria ({len(contexto_memoria_699)} chars)")
                    except Exception as e_mem:
                        print(f"   [WARN] FIX 699: Memory GPT context error: {e_mem}")

                    # FIX 819: Usar LLM Client Adapter (OpenAI o Anthropic)
                    respuesta_agente_819 = llm_client.chat_completion(
                        messages=mensajes_con_reglas,
                        openai_client=openai_client,
                        temperature=0.7,
                        max_tokens=tokens_actual,  # FIX 491/533: Dinámico, reducido en retry
                        timeout=timeout_actual,  # FIX 533: Timeout progresivo
                        presence_penalty=0.6,
                        frequency_penalty=1.5,  # FIX 74: Penalización MÁXIMA de repeticiones
                        top_p=0.9,  # FIX 55: Reducir diversidad
                    )
                    # Éxito - salir del loop
                    if intentos_gpt > 0:
                        print(f"   FIX 533: Reintento exitoso en intento #{intentos_gpt + 1}")
                    break

                except Exception as e_gpt:
                    error_tipo = type(e_gpt).__name__
                    intentos_gpt += 1

                    if 'Timeout' in error_tipo or 'timeout' in str(e_gpt).lower():
                        print(f"   FIX 533: APITimeoutError en intento {intentos_gpt}/{max_intentos_gpt}")
                        if intentos_gpt >= max_intentos_gpt:
                            print(f"   FIX 533: Agotados {max_intentos_gpt} intentos - usando fallback")
                            raise  # Re-lanzar para que el except global maneje
                        # Continuar al siguiente intento
                    else:
                        # Error no es timeout - re-lanzar inmediatamente
                        raise

            duracion_gpt = time.time() - inicio_gpt

            # FIX 163: Si GPT tardó más de 3 segundos, agregar frase de relleno ANTES de la respuesta
            frase_relleno = ""
            if duracion_gpt > 3.0:
                frase_relleno = self._obtener_frase_relleno(duracion_gpt)
                print(f"[EMOJI] FIX 163: GPT tardo {duracion_gpt:.1f}s - agregando frase de relleno: '{frase_relleno}'")

            respuesta_agente = respuesta_agente_819  # FIX 819: Resultado del adapter

            # FIX 519: Guardar transcripción + respuesta para aprendizaje automático
            if CACHE_PATRONES_DISPONIBLE and hasattr(self, '_transcripcion_pendiente_aprender') and self._transcripcion_pendiente_aprender:
                try:
                    cache = obtener_cache_patrones()
                    if cache:
                        cache.registrar_transcripcion_no_reconocida(
                            texto_cliente=self._transcripcion_pendiente_aprender,
                            respuesta_bruce=respuesta_agente,
                            bruce_id=getattr(self, 'bruce_id', None)
                        )
                except Exception as e:
                    print(f"   [WARN] FIX 519: Error guardando patrón: {e}")
                finally:
                    self._transcripcion_pendiente_aprender = None

            # ============================================================
            # FIX 385: Extraer Chain-of-Thought compacto (análisis interno)
            # ============================================================
            analisis_interno = ""
            # Buscar [A]...[/A] (formato compacto) o [ANÁLISIS]...[/ANÁLISIS] (legacy)
            if "[A]" in respuesta_agente and "[/A]" in respuesta_agente:
                # Extraer análisis compacto
                partes = respuesta_agente.split("[A]", 1)
                if len(partes) > 1:
                    analisis_y_respuesta = partes[1].split("[/A]", 1)
                    if len(analisis_y_respuesta) > 1:
                        analisis_interno = analisis_y_respuesta[0].strip()
                        respuesta_agente = analisis_y_respuesta[1].strip()

                        # Logging del análisis interno (compacto)
                        print(f"\n[EMOJI] FIX 385: Razonamiento compacto → {analisis_interno}")
                        print(f"   [OK] Respuesta: {respuesta_agente[:80]}...")
            elif "[ANÁLISIS]" in respuesta_agente and "[/ANÁLISIS]" in respuesta_agente:
                # Formato legacy (largo)
                partes = respuesta_agente.split("[ANÁLISIS]", 1)
                if len(partes) > 1:
                    analisis_y_respuesta = partes[1].split("[/ANÁLISIS]", 1)
                    if len(analisis_y_respuesta) > 1:
                        analisis_interno = analisis_y_respuesta[0].strip()
                        respuesta_agente = analisis_y_respuesta[1].strip()
                        print(f"\n[EMOJI] FIX 385: Razonamiento detallado detectado")
                        print(f"   [OK] Respuesta: {respuesta_agente[:80]}...")

            # Si hay frase de relleno, agregarla al inicio de la respuesta
            if frase_relleno:
                respuesta_agente = f"{frase_relleno} {respuesta_agente}"

            # ============================================================
            # FIX 391/392/398: DETECTAR CONFIRMACIÓN DEL CLIENTE PRIMERO
            # ============================================================
            # FIX 398: Detección de confirmación MÁS ESTRICTA
            skip_fix_384 = False

            ultimos_mensajes_cliente_pre = [
                msg['content'].lower() for msg in self.conversation_history[-4:]
                if msg['role'] == 'user'
            ]

            if ultimos_mensajes_cliente_pre:
                ultimo_cliente_pre = ultimos_mensajes_cliente_pre[-1]

                # FIX 398: SOLO confirmaciones CLARAS (con contexto adicional)
                confirmaciones_claras = [
                    'sí, adelante', 'si, adelante', 'claro, adelante',
                    'sí adelante', 'si adelante', 'claro adelante',
                    'ok, adelante', 'okay, adelante',
                    'sí, por favor', 'si, por favor', 'sí por favor', 'si por favor',
                    'claro, por favor', 'claro por favor',
                    'sí, mande', 'si, mande', 'sí mande', 'si mande',
                    'dale, sí', 'dale, si', 'dale si', 'dale sí',
                    'sí, sí', 'si, si', 'sí sí', 'si si',
                    'claro, claro', 'claro claro',
                    'está bien, adelante', 'esta bien, adelante',
                    'perfecto, adelante', 'sale, adelante'
                ]

                # FIX 398: Frases ambiguas que NO son confirmaciones
                frases_ambiguas_no_confirmacion = [
                    'bueno, pásele', 'bueno, pasele', 'bueno pasele',
                    'un segundo', 'un momento', 'espere', 'permítame', 'permitame',
                    'así es', 'asi es', 'eso es',
                    'ok.', 'bueno.', 'claro.', 'sí.', 'si.',  # Solo palabras (sin contexto)
                    'a ver', 'diga', 'dígame', 'digame'
                ]

                # Verificar si es confirmación CLARA
                cliente_confirmo_recientemente = any(
                    conf in ultimo_cliente_pre for conf in confirmaciones_claras
                )

                # Verificar si es frase ambigua (NO confirmar en estos casos)
                es_frase_ambigua = any(
                    amb in ultimo_cliente_pre for amb in frases_ambiguas_no_confirmacion
                )

                # FIX 398: Solo activar skip si confirmó Y NO es frase ambigua
                if cliente_confirmo_recientemente and not es_frase_ambigua:
                    skip_fix_384 = True
                    print(f"\n[EMOJI]  FIX 398: Cliente confirmó CLARAMENTE - skip_fix_384 = True")
                    print(f"   Confirmación detectada: '{ultimo_cliente_pre}'")
                elif es_frase_ambigua:
                    print(f"\n[EMOJI] FIX 398: Frase ambigua detectada - NO es confirmación")
                    print(f"   Frase: '{ultimo_cliente_pre}'")

            # ============================================================
            # FIX 226: FILTRO POST-GPT - Forzar reglas que GPT no sigue
            # ============================================================
            respuesta_agente = self._filtrar_respuesta_post_gpt(respuesta_agente, skip_fix_384)

            # ============================================================
            # FIX 204: DETECTAR Y PREVENIR REPETICIONES IDÉNTICAS
            # ============================================================
            # Verificar si Bruce está a punto de repetir el mismo mensaje
            ultimas_respuestas_bruce = [
                msg['content'] for msg in self.conversation_history[-6:]
                if msg['role'] == 'assistant'
            ]

            # Normalizar para comparación (sin puntuación ni mayúsculas)
            import re
            respuesta_normalizada = re.sub(r'[^\w\s]', '', respuesta_agente.lower()).strip()

            # FIX 391/392: Detectar si contexto cambió (cliente confirmó/respondió)
            # NO bloquear repetición si cliente dio respuesta nueva que requiere la misma acción
            ultimos_mensajes_cliente = [
                msg['content'].lower() for msg in self.conversation_history[-4:]
                if msg['role'] == 'user'
            ]

            cliente_confirmo_recientemente = False

            if ultimos_mensajes_cliente:
                ultimo_cliente = ultimos_mensajes_cliente[-1]
                # Cliente confirmó con "sí", "claro", "adelante", etc.
                confirmaciones = ['sí', 'si', 'claro', 'adelante', 'dale', 'ok', 'okay',
                                 'bueno', 'perfecto', 'sale', 'está bien', 'esta bien']
                cliente_confirmo_recientemente = any(c in ultimo_cliente for c in confirmaciones)

            # Verificar si esta respuesta ya se dijo en las últimas 3 respuestas
            repeticion_detectada = False
            for i, resp_previa in enumerate(ultimas_respuestas_bruce[-3:], 1):
                resp_previa_normalizada = re.sub(r'[^\w\s]', '', resp_previa.lower()).strip()

                # Si la respuesta es >80% similar (o idéntica)
                if respuesta_normalizada == resp_previa_normalizada:
                    # FIX 391/392: Si cliente confirmó recientemente, NO bloquear
                    # (puede ser respuesta útil en nuevo contexto)
                    if cliente_confirmo_recientemente:
                        print(f"\n[EMOJI]  FIX 391/392: Repetición detectada pero cliente confirmó - permitiendo respuesta")
                        print(f"   Cliente dijo: '{ultimo_cliente[:60]}...'")
                        print(f"   Respuesta: '{respuesta_agente[:60]}...'")
                        print(f"   FIX 392: skip_fix_384 activado - FIX 384 NO se ejecutará")
                        break

                    repeticion_detectada = True
                    print(f"\n[EMOJI] FIX 204/393: REPETICIÓN IDÉNTICA DETECTADA [EMOJI]")
                    print(f"   Bruce intentó repetir: \"{respuesta_agente[:60]}...\"")
                    print(f"   Ya se dijo hace {i} respuesta(s)")
                    print(f"   → Modificando respuesta para evitar repetición")
                    break

            # FIX 393/394: Detectar repetición de PREGUNTAS (caso BRUCE1099, BRUCE1105)
            # Bruce preguntó "¿Se encontrará el encargado?" múltiples veces seguidas
            # FIX 394: Ampliar a últimas 4 respuestas (BRUCE1105 repitió 4 veces)
            if not repeticion_detectada and '?' in respuesta_agente:
                # Extraer la pregunta principal
                pregunta_actual = respuesta_agente.split('?')[0].lower().strip()
                pregunta_normalizada = re.sub(r'[^\w\s]', '', pregunta_actual).strip()

                # FIX 394: Revisar últimas 4 respuestas en vez de 2
                for i, resp_previa in enumerate(ultimas_respuestas_bruce[-4:], 1):
                    if '?' in resp_previa:
                        pregunta_previa = resp_previa.split('?')[0].lower().strip()
                        pregunta_previa_norm = re.sub(r'[^\w\s]', '', pregunta_previa).strip()

                        # Si la pregunta es idéntica
                        if pregunta_normalizada == pregunta_previa_norm:
                            repeticion_detectada = True
                            print(f"\n[EMOJI] FIX 393/394: REPETICIÓN DE PREGUNTA DETECTADA [EMOJI]")
                            print(f"   Bruce intentó repetir PREGUNTA: \"{pregunta_actual[:60]}...?\"")
                            print(f"   Ya se preguntó hace {i} respuesta(s)")
                            print(f"   → Modificando respuesta para evitar repetición")
                            break

            if repeticion_detectada:
                # Modificar la respuesta para que GPT genere algo diferente
                self.conversation_history.append({
                    "role": "system",
                    "content": f"""[EMOJI] [SISTEMA - FIX 204/393] REPETICIÓN DETECTADA

Estabas a punto de decir EXACTAMENTE lo mismo que ya dijiste antes:
"{respuesta_agente[:100]}..."

[EMOJI] NO repitas esto. El cliente YA lo escuchó.

[OK] OPCIONES VÁLIDAS:
1. Si el cliente no respondió tu pregunta: Reformula de manera DIFERENTE
2. Si el cliente está ocupado/no interesado: Ofrece despedirte o llamar después
3. Si no te entiende: Usa palabras más simples
4. Si el cliente rechazó 2 veces: DESPÍDETE profesionalmente y cuelga

[EMOJI] EJEMPLO DE REFORMULACIÓN:
ORIGINAL: "¿Le gustaría que le envíe el catálogo por WhatsApp?"
REFORMULADO: "¿Tiene WhatsApp donde le pueda enviar información?"
REFORMULADO 2: "¿Prefiere que le llame en otro momento?"

[EMOJI] FIX 393: Si el cliente ya rechazó 2 veces, NO insistas:
CLIENTE: "No, gracias" (1ra vez) → "No" (2da vez)
BRUCE: "Entiendo. Le agradezco su tiempo. Buen día." [COLGAR]

Genera una respuesta COMPLETAMENTE DIFERENTE ahora."""
                })

                # Regenerar respuesta con contexto de no repetir
                # FIX 819: Usar modelo potente para retry (gpt-4o o claude-sonnet)
                print(f"[EMOJI] FIX 204: Regenerando respuesta sin repeticion...")
                try:
                    respuesta_agente = llm_client.chat_completion(
                        messages=self.conversation_history,
                        openai_client=openai_client,
                        model_override=llm_client.get_retry_model(),  # gpt-4o o claude-sonnet
                        temperature=0.9,  # Más creatividad para evitar repetición
                        max_tokens=80,
                        timeout=2.8,
                        presence_penalty=0.8,
                        frequency_penalty=2.0,
                        top_p=0.9,
                    )
                    print(f"[OK] FIX 204: Nueva respuesta generada: \"{respuesta_agente[:60]}...\"")

                except Exception as e:
                    print(f"[WARN] FIX 204: Error al regenerar, usando despedida genérica")
                    respuesta_agente = "Entiendo. ¿Prefiere que le llame en otro momento más conveniente?"

            # Agregar al historial
            self.conversation_history.append({
                "role": "assistant",
                "content": respuesta_agente
            })

            return respuesta_agente

        except Exception as e:
            # FIX 305/307/352: Logging detallado del error para diagnóstico
            import traceback
            error_tipo = type(e).__name__
            print(f"\n[EMOJI] FIX 305: EXCEPCIÓN EN GPT [EMOJI]")
            print(f"   Error: {error_tipo}: {e}")
            print(f"   Traceback completo:")
            traceback.print_exc()
            # FIX 307: Variable correcta es respuesta_cliente
            print(f"   Último mensaje del cliente: {respuesta_cliente[:100] if respuesta_cliente else 'VACÍO'}")
            print(f"   Historial tiene {len(self.conversation_history)} mensajes")

            # FIX 352: Respuestas de fallback según contexto del cliente
            respuesta_lower = respuesta_cliente.lower() if respuesta_cliente else ""

            # FIX 771: BRUCE2435 - Si Bruce YA DIO su contacto y cliente se despide → despedida
            # PROBLEMA: APITimeoutError cuando cliente dijo "Ok, gracias" → fallback genérico
            # repetía "¿Se encontrará el encargado?" causando loop de 5+ turnos
            _todos_bruce_771 = [m['content'].lower() for m in self.conversation_history if m['role'] == 'assistant']
            _bruce_dio_contacto_771 = any(
                any(w in msg for w in ['6 6 2', '662', '4 1 5', '415', '1 9 9 7', '1997',
                                        'ventas arroba nioval', 'ventas@nioval',
                                        'nuestro whatsapp es', 'nuestro correo es',
                                        'mi número es', 'mi numero es', 'nuestro número es'])
                for msg in _todos_bruce_771
            )
            _cliente_despide_771 = any(p in respuesta_lower for p in [
                'gracias', 'ok gracias', 'bien gracias', 'hasta luego', 'adios', 'adiós',
                'bye', 'bueno gracias', 'muchas gracias', 'muy amable',
                'esta bien', 'está bien', 'ya quedo', 'ya quedó', 'perfecto gracias'
            ])
            _cliente_pide_numero_771 = any(p in respuesta_lower for p in [
                'cual es tu numero', 'cuál es tu número', 'dame tu numero', 'dime tu numero',
                'dimelo', 'dímelo', 'si dime', 'sí dime', 'dame el numero', 'pásame tu'
            ])
            if _bruce_dio_contacto_771 and _cliente_despide_771:
                print(f"[OK] FIX 771: Bruce ya dio contacto + cliente se despide → despedida formal")
                return "Perfecto, muchas gracias por su tiempo. Que tenga excelente día."
            if _cliente_pide_numero_771 and not _bruce_dio_contacto_771:
                print(f"[OK] FIX 771: Cliente pide número de Bruce → darlo")
                return "Claro, nuestro WhatsApp es 6 6 2, 4 1 5, 1 9 9 7 y nuestro correo es ventas arroba nioval punto com."

            # FIX 422: Si Bruce pidió número del encargado y cliente aceptó, preguntar directamente
            # Caso BRUCE1244: Bruce pidió número, cliente dijo "Si gusta,", Bruce debió preguntar por número
            ultimos_bruce_422 = [
                msg['content'].lower() for msg in self.conversation_history[-3:]
                if msg['role'] == 'assistant'
            ]
            bruce_pidio_numero_encargado = any(
                frase in msg for frase in [
                    'número directo del encargado',
                    'numero directo del encargado',
                    'número del encargado',
                    'numero del encargado'
                ]
                for msg in ultimos_bruce_422
            )

            cliente_acepta = any(p in respuesta_lower for p in ['sí', 'si', 'claro', 'adelante', 'dígame', 'digame', 'gusta'])

            if bruce_pidio_numero_encargado and cliente_acepta:
                print(f"[OK] FIX 422: Bruce pidió número del encargado y cliente aceptó")
                print(f"   Cliente dijo: '{respuesta_cliente}' - Preguntando directamente por número")
                return "Perfecto. ¿Cuál es el número?"

            # Si cliente preguntó sobre productos
            if any(p in respuesta_lower for p in ['qué producto', 'que producto', 'de qué son', 'de que son',
                                                    'qué venden', 'que venden', 'qué manejan', 'que manejan']):
                return "Manejamos productos de ferretería de la marca NIOVAL. Tenemos herramientas, grifería, candados, y más. ¿Le gustaría recibir el catálogo?"

            # Si cliente dijo que sí o mostró interés (pero NO si Bruce pidió número)
            if cliente_acepta and not bruce_pidio_numero_encargado:
                return "¿Le gustaría recibir nuestro catálogo por WhatsApp o correo electrónico?"

            # Si cliente preguntó quién habla o de dónde llaman
            if any(p in respuesta_lower for p in ['quién habla', 'quien habla', 'de dónde', 'de donde',
                                                   'quién es', 'quien es', 'de parte']):
                return "Mi nombre es Bruce, me comunico de parte de la marca NIOVAL, productos de ferretería."

            # FIX 493: BRUCE1471 - Detectar si cliente dijo que encargado NO ESTÁ
            # PROBLEMA: Fallback genérico preguntaba por encargado cuando cliente ya dijo "no está"
            # RESULTADO: Loop infinito de 5+ repeticiones
            patrones_no_esta_fallback = [
                'no está', 'no esta', 'no se encuentra', 'salió', 'salio',
                'llega a las', 'llega más tarde', 'llega mas tarde',
                'no hay nadie', 'no hay encargado', 'no tenemos encargado',
                'ocupado', 'en una junta', 'no puede atender',
                # FIX 642C: BRUCE2070 - "marcar más tarde" es callback (encargado no está)
                'marcar más tarde', 'marcar mas tarde', 'llamar más tarde', 'llamar mas tarde',
                'marque más tarde', 'marque mas tarde', 'llame más tarde', 'llame mas tarde',
                'marcar después', 'marcar despues', 'llamar después', 'llamar despues',
            ]
            if any(p in respuesta_lower for p in patrones_no_esta_fallback):
                print(f"[OK] FIX 493: Fallback detecta ENCARGADO_NO_ESTA - NO preguntar de nuevo")
                # Detectar si cliente dio horario
                import re
                patron_horario = r'(?:llega|viene|regresa|está|esta).*?(?:a las|las|a la|la)\s*(\d{1,2})'
                match_horario = re.search(patron_horario, respuesta_lower)
                if match_horario:
                    hora = match_horario.group(1)
                    print(f"   FIX 493: Cliente dio horario ({hora} hrs) - Agendar callback")
                    return f"Perfecto, le llamo a las {hora} entonces. Muchas gracias."
                else:
                    # Sin horario - pedir WhatsApp del encargado
                    return "Entiendo. ¿Me podría proporcionar el WhatsApp del encargado para enviarle el catálogo?"

            # FIX 493: Verificar si ya preguntamos por encargado antes
            # ACTUALIZADO: Usar MISMOS patrones que el parche global anti-loop
            ultimas_bruce_493 = [
                msg['content'].lower() for msg in self.conversation_history[-6:]
                if msg['role'] == 'assistant'
            ]
            # Lista COMPLETA de patrones de encargado (sincronizada con parche global)
            patrones_encargado_493 = [
                'se encontrará el encargado', 'se encontrara el encargado',
                'está el encargado', 'esta el encargado',
                'se encuentra el encargado', 'encargado de compras',
                'me comunica con el encargado', 'comunica con el encargado',
                'mensaje al encargado', 'dejar un mensaje al encargado',
                'hablar con el encargado', 'contactar al encargado',
                'encargado o encargada', 'encontrará el encargado'
            ]
            veces_pregunto_encargado = sum(
                1 for msg in ultimas_bruce_493
                if any(p in msg for p in patrones_encargado_493)
            )
            if veces_pregunto_encargado >= 1:  # FIX 692A: alineado con bug detector
                print(f"[WARN] FIX 493+692A: Ya preguntamos por encargado {veces_pregunto_encargado} veces - EVITANDO LOOP")
                return "Entiendo. ¿Me puede proporcionar un WhatsApp para enviarle información?"

            # FIX 305: Fallback genérico (solo si no hay indicios de loop)
            return "Perfecto. ¿Se encontrará el encargado o encargada de compras?"
    
    def _extraer_datos(self, texto: str):
        """Extrae información clave del texto del cliente"""
        import re

        texto_lower = texto.lower()

        # FIX 72: Detectar estados de llamada sin respuesta - MÁS ESTRICTO
        # PROBLEMA: Detección muy sensible causaba falsos positivos
        # SOLUCIÓN: Requerir frases completas, no palabras sueltas
        frases_buzon = [
            "buzón de voz", "buzon de voz", "entró el buzón", "entro el buzon",
            "dejé el buzón", "deje el buzon", "cayó en buzón", "cayo en buzon",
            "contestadora automática", "mensaje automático", "deje su mensaje",
            "después del tono", "despues del tono"
        ]

        # Solo detectar si es una frase completa de buzón, no palabra suelta
        if any(frase in texto_lower for frase in frases_buzon):
            self.lead_data["estado_llamada"] = "Buzon"
            self.lead_data["pregunta_0"] = "Buzon"
            self.lead_data["pregunta_7"] = "BUZON"
            self.lead_data["resultado"] = "NEGADO"
            print(f"[EMOJI] FIX 72: Estado detectado: Buzón de voz - Frase: '{texto[:50]}'")
            return

        # FIX 24/420: Detección MÁS ESTRICTA de teléfono incorrecto
        # Frases completas que indican número equivocado
        # FIX 420: Removida "fuera de servicio" - es ambigua (caso BRUCE1227)
        # "fuera de servicio" puede referirse a: teléfono, negocio cerrado, o encargado no disponible
        frases_numero_incorrecto = [
            "numero incorrecto", "número incorrecto", "numero equivocado", "número equivocado",
            "no existe", "no es aqui", "no es aquí",
            "se equivocó de número", "se equivoco de numero", "marcó mal", "marco mal",
            "no trabajo aqui", "no trabajo aquí", "no es el negocio", "no es mi negocio",
            "equivocado de numero", "equivocado de número", "llamó mal", "llamo mal",
            "no hay negocio", "aqui no es", "aquí no es", "no es aca", "no es acá",
            "esto no es una ferretería", "esto no es ferretería", "no vendemos",
            "no es este el número", "no es este número", "llamó al número equivocado",
            "se equivocó de teléfono", "marcó equivocado",
            # FIX 420: Agregar patrones más específicos para teléfono fuera de servicio
            "el número está fuera de servicio", "el numero esta fuera de servicio",
            "teléfono fuera de servicio", "telefono fuera de servicio",
            "este número no existe", "este numero no existe"
        ]

        # NOTA: Eliminadas frases genéricas que causan falsos positivos:
        # - "no soy" (cliente puede decir "no soy el encargado de compras")
        # - "no somos" (cliente puede decir "no somos distribuidores")
        # - "no es este" (demasiado genérico)

        if (any(frase in texto_lower for frase in frases_numero_incorrecto) or
            (("telefono" in texto_lower or "teléfono" in texto_lower or "numero" in texto_lower or "número" in texto_lower) and
             ("incorrecto" in texto_lower or "equivocado" in texto_lower or "equivocada" in texto_lower))):
            self.lead_data["estado_llamada"] = "Telefono Incorrecto"
            self.lead_data["pregunta_0"] = "Telefono Incorrecto"
            self.lead_data["pregunta_7"] = "TELEFONO INCORRECTO"
            self.lead_data["resultado"] = "NEGADO"
            print(f"[EMOJI] Estado detectado: Teléfono Incorrecto - '{texto[:50]}...'")
            return

        # FIX 22B: Detección MÁS ESTRICTA de "colgó" - solo frases completas
        # NO detectar palabras sueltas que puedan confundirse
        frases_colgo_real = [
            "el cliente colgó", "cliente colgó", "ya colgó", "colgó la llamada",
            "se colgó", "colgaron", "me colgaron", "cortó la llamada"
        ]
        if any(frase in texto_lower for frase in frases_colgo_real):
            self.lead_data["estado_llamada"] = "Colgo"
            self.lead_data["pregunta_0"] = "Colgo"
            self.lead_data["pregunta_7"] = "Colgo"
            self.lead_data["resultado"] = "NEGADO"
            print(f"[EMOJI] Estado detectado: Cliente colgó - '{texto[:50]}...'")
            return

        if any(palabra in texto_lower for palabra in ["no contesta", "no responde", "sin respuesta"]):
            self.lead_data["estado_llamada"] = "No Contesta"
            self.lead_data["pregunta_0"] = "No Contesta"
            self.lead_data["pregunta_7"] = "Nulo"
            self.lead_data["resultado"] = "NEGADO"
            print(f"[EMOJI] Estado detectado: No contesta")
            return

        # ============================================================
        # FIX 18: DETECCIÓN CRÍTICA - "YO SOY EL ENCARGADO"
        # ============================================================
        # Detectar cuando el cliente confirma que ÉL/ELLA es el encargado
        frases_es_encargado = [
            "yo soy el encargado", "soy yo el encargado", "yo soy la encargada", "soy yo la encargada",
            "soy el encargado", "soy la encargada",
            "la encargada soy yo", "el encargado soy yo",
            "soy yo", "yo soy", "habla con él", "es conmigo",
            "el trato es conmigo", "hablo yo", "hable conmigo",
            "yo atiendo", "yo me encargo", "yo soy quien",
            "aquí yo", "yo le atiendo", "conmigo puede hablar",
            "yo lo puedo atender", "lo puedo atender", "puedo atenderlo",  # FIX 51
            "yo puedo atender", "yo te atiendo", "yo te puedo atender"  # FIX 51
        ]

        if any(frase in texto_lower for frase in frases_es_encargado):
            # Marcar que YA estamos hablando con el encargado
            if not hasattr(self, 'encargado_confirmado'):
                self.encargado_confirmado = True
                print(f"[EMOJI] CONFIRMADO: Cliente ES el encargado - '{texto[:50]}...'")

                # Agregar mensaje al sistema para que GPT NO vuelva a preguntar
                self.conversation_history.append({
                    "role": "system",
                    "content": """[WARN][WARN][WARN] CRÍTICO: El cliente acaba de confirmar que ÉL/ELLA ES el encargado de compras.

ACCIÓN INMEDIATA:
1. NO vuelvas a preguntar "¿Se encuentra el encargado?" NUNCA MÁS
2. NO preguntas por horario del encargado
3. NO pidas que te comuniquen con el encargado
4. Continúa la conversación DIRECTAMENTE con esta persona
5. [EMOJI] FIX 172: NO pidas el nombre (genera delays de audio)
6. Pregunta directamente: "¿Le gustaría recibir el catálogo por WhatsApp?"

YA ESTÁS HABLANDO CON EL ENCARGADO. NO LO VUELVAS A BUSCAR."""
                })

        # ============================================================
        # FIX 46: DETECCIÓN CRÍTICA - CLIENTE PREGUNTA POR MARCAS
        # ============================================================
        # Inyectar advertencia INMEDIATA cuando cliente pregunta qué marcas maneja NIOVAL
        frases_pregunta_marcas = [
            "qué marcas", "que marcas", "cuáles marcas", "cuales marcas",
            "qué marca", "que marca", "cuál marca", "cual marca",
            "de qué marca", "de que marca", "marcas manejan", "marca manejan",
            "marcas tienen", "marca tienen", "marcas trabajan", "marca trabajan",
            "marcas reconocidas", "marca reconocida", "qué distribuyen", "que distribuyen",
            "qué venden", "que venden", "productos de qué marca", "productos de que marca"
        ]

        if any(frase in texto_lower for frase in frases_pregunta_marcas):
            print(f"[EMOJI] FIX 46: Cliente pregunta por MARCAS - '{texto[:60]}...'")

            self.conversation_history.append({
                "role": "system",
                "content": """[EMOJI] ALERTA ULTRA-CRÍTICA: CLIENTE PREGUNTA POR MARCAS [EMOJI]

El cliente está preguntando QUÉ MARCAS maneja NIOVAL.

[WARN][WARN][WARN] PROHIBICIONES ABSOLUTAS - NUNCA NUNCA NUNCA DIGAS:
[ERROR] "Manejamos marcas reconocidas como Truper"
[ERROR] "Trabajamos con Truper"
[ERROR] "Distribuimos Truper"
[ERROR] "Contamos con Pochteca"
[ERROR] "Manejamos Pretul"
[ERROR] "Trabajamos con marcas como [CUALQUIER NOMBRE DE MARCA EXTERNA]"
[ERROR] "Tenemos Stanley, Dewalt, Urrea"
[ERROR] NO MENCIONES NOMBRES DE MARCAS EXTERNAS

[OK][OK][OK] RESPUESTAS OBLIGATORIAS - USA EXACTAMENTE:
[OK] "Manejamos la marca NIOVAL, que es nuestra marca propia"
[OK] "Trabajamos con nuestra propia línea de productos bajo la marca NIOVAL"
[OK] "Al ser marca propia, ofrecemos mejores precios que marcas comerciales"
[OK] "¿Le gustaría que le envíe el catálogo completo para que vea todos nuestros productos?"

NIOVAL ES UNA MARCA PROPIA - NO ES DISTRIBUIDOR DE OTRAS MARCAS.
TRUPER, POCHTECA, PRETUL = SON COMPETENCIA [ERROR][ERROR][ERROR]

IMPORTANTE:
- Si cliente pregunta: "¿Qué marcas?" → Responde: "Manejamos NIOVAL, nuestra marca propia"
- NO inventes nombres de marcas
- NO menciones competencia
- OFRECE enviar catálogo para que vea los productos"""
            })

        # ============================================================
        # FIX 33: DETECCIÓN DE FRUSTRACIÓN DEL CLIENTE
        # ============================================================
        # Detectar cuando el cliente dice "ya te lo dije", "ya te pasé", "eso ya te lo mencioné"
        frases_frustracion = [
            "ya te lo dije", "ya te dije", "ya te lo mencioné", "ya te lo mencione",
            "ya te pasé", "ya te pase", "ya te lo pasé", "ya te lo pase",
            "eso ya te lo dije", "eso ya te lo dije", "te lo acabo de decir",
            "ya te lo comenté", "ya te lo comente", "te lo acabo de dar",
            "ya te di", "ya te lo di", "acabas de preguntarme eso",
            "ya respondí eso", "ya respondi eso", "me estas repitiendo"
        ]

        if any(frase in texto_lower for frase in frases_frustracion):
            print(f"[EMOJI] FIX 33: Cliente muestra FRUSTRACIÓN - '{texto[:60]}...'")

            self.conversation_history.append({
                "role": "system",
                "content": """[WARN][WARN][WARN] [SISTEMA] ALERTA: EL CLIENTE ESTÁ FRUSTRADO

El cliente acaba de decir "ya te lo dije" o similar. Esto significa que:
1. YA dio esta información anteriormente en la conversación
2. Estás preguntando algo que YA preguntaste antes
3. El cliente se está molestando por repetir información

ACCIÓN INMEDIATA OBLIGATORIA:
1. REVISA el historial de conversación COMPLETO antes de responder
2. BUSCA la información que el cliente dice que ya dio
3. NO vuelvas a pedir esa información - confírma que ya la tienes
4. DISCULPATE por la confusión: "Disculpe, tiene razón. Ya me lo había mencionado."
5. AVANZA a la siguiente pregunta SIN volver a pedir información ya capturada

INFORMACIÓN YA CAPTURADA:
- Nombre: {nombre}
- WhatsApp: {whatsapp}
- Email: {email}
- Productos de interés: {productos}

[ERROR] NO vuelvas a preguntar por NADA de lo de arriba
[OK] AVANZA con la conversación usando la info que YA TIENES""".format(
                    nombre=self.lead_data.get('nombre_contacto', 'No capturado'),
                    whatsapp=self.lead_data.get('whatsapp', 'No capturado'),
                    email=self.lead_data.get('email', 'No capturado'),
                    productos=self.lead_data.get('productos_interes', 'No capturados')
                )
            })

        # ============================================================
        # FIX 31: DETECTAR SI YA SE PREGUNTÓ POR TAMAÑO/PROVEEDORES
        # ============================================================
        # Buscar en el historial si Bruce ya preguntó por tamaño de negocio o proveedores
        preguntas_tamano = [
            "qué tamaño de negocio", "que tamaño de negocio", "tamaño del negocio",
            "si es una ferretería local", "tienen varias sucursales",
            "son distribuidor mayorista", "qué tipo de negocio"
        ]

        preguntas_proveedores = [
            "trabajan con varios proveedores", "tienen uno principal",
            "proveedores actuales", "su proveedor principal"
        ]

        # Revisar mensajes del asistente en el historial
        mensajes_bruce = [msg['content'] for msg in self.conversation_history if msg['role'] == 'assistant']
        texto_completo_bruce = ' '.join(mensajes_bruce).lower()

        ya_pregunto_tamano = any(frase in texto_completo_bruce for frase in preguntas_tamano)
        ya_pregunto_proveedores = any(frase in texto_completo_bruce for frase in preguntas_proveedores)

        if ya_pregunto_tamano and not hasattr(self, 'flag_pregunta_tamano_advertida'):
            self.flag_pregunta_tamano_advertida = True
            print(f"[EMOJI] FIX 31: Ya preguntaste por TAMAÑO DE NEGOCIO - NO volver a preguntar")

            self.conversation_history.append({
                "role": "system",
                "content": """[WARN][WARN][WARN] [SISTEMA] YA PREGUNTASTE POR TAMAÑO DE NEGOCIO

Detecté que YA preguntaste sobre el tamaño del negocio anteriormente.

[ERROR] NO vuelvas a preguntar: "¿Qué tamaño de negocio tienen?"
[ERROR] NO vuelvas a preguntar: "¿Si es ferretería local o distribuidora?"
[OK] YA TIENES esta información en el contexto de la conversación
[OK] AVANZA a la siguiente pregunta o tema

Si el cliente no respondió claramente la primera vez, está bien. NO insistas."""
            })

        if ya_pregunto_proveedores and not hasattr(self, 'flag_pregunta_proveedores_advertida'):
            self.flag_pregunta_proveedores_advertida = True
            print(f"[EMOJI] FIX 31: Ya preguntaste por PROVEEDORES - NO volver a preguntar")

            self.conversation_history.append({
                "role": "system",
                "content": """[WARN][WARN][WARN] [SISTEMA] YA PREGUNTASTE POR PROVEEDORES

Detecté que YA preguntaste sobre los proveedores actuales.

[ERROR] NO vuelvas a preguntar: "¿Trabajan con varios proveedores?"
[ERROR] NO vuelvas a preguntar: "¿Tienen uno principal?"
[OK] YA TIENES esta información en el contexto de la conversación
[OK] AVANZA a la siguiente pregunta o tema

Si el cliente no respondió claramente la primera vez, está bien. NO insistas."""
            })

        # ============================================================
        # FIX 32 + FIX 198: DETECTAR SI CLIENTE YA DIO CORREO (VERIFICACIÓN CONTINUA)
        # ============================================================
        # FIX 198: SIEMPRE verificar si email ya existe (no usar flag de una sola vez)
        if self.lead_data.get("email"):
            # Verificar si este email YA estaba en el historial ANTES de esta respuesta
            email_actual = self.lead_data["email"]

            # Buscar en historial si ya se mencionó este email
            email_ya_mencionado = False
            num_mensaje_anterior = None

            for i, msg in enumerate(self.conversation_history[:-1]):  # Excluir mensaje actual
                if msg['role'] == 'user' and email_actual.lower() in msg['content'].lower():
                    email_ya_mencionado = True
                    num_mensaje_anterior = (i + 1) // 2  # Calcular número de mensaje
                    break

            if email_ya_mencionado:
                print(f"[WARN] FIX 198: Email '{email_actual}' YA fue mencionado en mensaje #{num_mensaje_anterior}")
                print(f"   Cliente está REPITIENDO el email (no es la primera vez)")

                self.conversation_history.append({
                    "role": "system",
                    "content": f"""[WARN][WARN][WARN] [SISTEMA] EMAIL DUPLICADO DETECTADO - FIX 198

El cliente acaba de mencionar el email: {email_actual}

[EMOJI] IMPORTANTE: Este email YA fue proporcionado anteriormente en mensaje #{num_mensaje_anterior}

[EMOJI] ACCIÓN REQUERIDA:
- [OK] Responde: "Perfecto, ya lo tengo anotado desde antes. Muchas gracias."
- [OK] NO pidas confirmación (ya lo tienes)
- [OK] NO digas "adelante con el correo" (ya te lo dieron)
- [OK] DESPIDE INMEDIATAMENTE

[ERROR] NUNCA pidas el email de nuevo
[ERROR] NUNCA digas "perfecto, adelante" (ya está adelante)
[ERROR] NUNCA actúes como si fuera la primera vez

El cliente ya te dio este dato antes. Reconócelo y termina la llamada."""
                })
                print(f"   [OK] FIX 198: Contexto agregado para GPT - manejar email duplicado")
            else:
                # Primera vez que se menciona este email
                print(f"[OK] FIX 198: Email '{email_actual}' es NUEVO - primera mención")

                self.conversation_history.append({
                    "role": "system",
                    "content": f"""[OK] [SISTEMA] NUEVO EMAIL CAPTURADO

Email capturado: {email_actual}

[ERROR] NO vuelvas a pedir el correo electrónico
[ERROR] NO digas "¿Me podría dar su correo?"
[ERROR] NO digas "¿Tiene correo electrónico?"
[OK] YA LO TIENES: {email_actual}
[OK] AVANZA con la conversación

Responde: "Perfecto, ya lo tengo anotado. Le llegará el catálogo en las próximas horas."

DESPIDE INMEDIATAMENTE y COLGAR."""
                })

        # ============================================================
        # FIX 16 + FIX 172: DETECCIÓN - NUNCA PEDIR NOMBRE (genera delays de audio)
        # ============================================================
        # FIX 172: Detectar si Bruce está preguntando por el nombre (NUNCA debe hacerlo)
        frases_pide_nombre = [
            "¿con quién tengo el gusto?", "con quien tengo el gusto",
            "¿me podría decir su nombre?", "me podria decir su nombre",
            "¿cuál es su nombre?", "cual es su nombre",
            "¿cómo se llama?", "como se llama"
        ]

        if any(frase in texto_lower for frase in frases_pide_nombre):
            print(f"[WARN][WARN][WARN] FIX 172 VIOLADO: Bruce pidió nombre (genera delays de audio)")
            self.conversation_history.append({
                "role": "system",
                "content": """[WARN][WARN][WARN] ERROR CRÍTICO - FIX 172 VIOLADO:

Acabas de preguntar el nombre del cliente. Esto está PROHIBIDO porque:
1. Genera delays de 1-4 segundos en la generación de audio con ElevenLabs
2. NO es necesario para enviar el catálogo
3. Genera fricción con el cliente

ACCIÓN INMEDIATA:
- NO vuelvas a preguntar el nombre NUNCA MÁS
- Pregunta directamente: "¿Le gustaría recibir el catálogo por WhatsApp o correo electrónico?"
- NUNCA uses el nombre del cliente en tus respuestas (genera delays)"""
                })

        # ============================================================
        # FIX 127: DETECCIÓN CRÍTICA - "NO, POR WHATSAPP" / "MÁNDAMELO POR WHATSAPP"
        # ============================================================
        # Detectar cuando cliente RECHAZA correo y pide WhatsApp repetidamente

        # FIX 127: Primero verificar si cliente dice que NO tiene/quiere WhatsApp
        frases_rechaza_whatsapp = [
            "no tengo whatsapp", "no manejo whatsapp", "no uso whatsapp",
            "no agarro whatsapp", "no, por whatsapp no", "whatsapp no",
            "no me funciona whatsapp", "no puedo whatsapp"
        ]

        cliente_rechaza_whatsapp = any(frase in texto_lower for frase in frases_rechaza_whatsapp)

        frases_pide_whatsapp = [
            "mándamelo por whatsapp", "envialo por whatsapp",
            "mejor whatsapp", "prefiero whatsapp", "whatsapp mejor",
            "tengo whatsapp", "mejor el whatsapp", "dame tu whatsapp",
            "si whatsapp", "sí whatsapp", "por whatsapp si", "por whatsapp sí"
        ]

        if not cliente_rechaza_whatsapp and any(frase in texto_lower for frase in frases_pide_whatsapp):
            if not hasattr(self, 'cliente_confirmo_whatsapp'):
                self.cliente_confirmo_whatsapp = True
                print(f"[OK] CRÍTICO: Cliente CONFIRMÓ que quiere WhatsApp (NO correo)")

                self.conversation_history.append({
                    "role": "system",
                    "content": """[WARN][WARN][WARN] CRÍTICO - CLIENTE RECHAZÓ CORREO Y PIDIÓ WHATSAPP

El cliente acaba de decir que NO quiere correo, quiere WHATSAPP.

ACCIÓN INMEDIATA:
1. NO vuelvas a pedir correo electrónico
2. Pide su número de WhatsApp AHORA MISMO
3. Di: "Perfecto, le enviaré el catálogo por WhatsApp. ¿Me podría proporcionar su número de teléfono para enviárselo?"

IMPORTANTE:
- WhatsApp es PRIORITARIO sobre correo
- Si ya pediste correo antes, cambia inmediatamente a WhatsApp
- NUNCA insistas en correo si el cliente pidió WhatsApp"""
                })

        # ============================================================
        # FIX 34: DETECCIÓN CRÍTICA EXPANDIDA - OBJECIÓN TRUPER (NO APTO)
        # ============================================================
        # Detectar cuando cliente SOLO maneja Truper (marca exclusiva)
        # Truper NO permite que sus socios distribuyan otras marcas
        frases_solo_truper = [
            "solo truper", "solamente truper", "únicamente truper",
            "solo manejamos truper", "solamente manejamos truper", "únicamente manejamos truper",  # FIX 42
            "solo podemos truper", "solo podemos comprar truper",
            "somos truper", "solo trabajamos con truper",
            "nada más truper", "nomás truper", "solo compramos truper",
            "trabajamos para truper", "somos distribuidores de truper",
            "distribuidor de truper", "distribuidores truper",
            "únicamente trabajamos para truper", "solamente trabajamos para truper",
            "todo lo que es truper", "manejamos truper", "trabajamos truper",
            "no podemos manejar alguna otra", "no podemos manejar otra marca",  # FIX 42
            "no puedo manejar otra", "no podemos trabajar con otra",  # FIX 42
            "no podemos trabajar con algunas otras", "no podemos trabajar con otras marcas",  # FIX 44
        ]

        # FIX 36: Detección ULTRA-AGRESIVA - "trabajamos con truper" SIN necesidad de "solo"
        frases_trabajamos_truper = [
            "trabajamos con truper", "trabajo con truper", "trabajamos truper",
            "trabajamos directamente con truper", "compramos truper",
            "compramos con truper", "trabajamos con trooper",  # Variación Trooper
            "únicamente trabajamos con truper"
        ]

        # Detección combinada: menciona truper + frases de exclusividad
        mencion_truper = "truper" in texto_lower or "trooper" in texto_lower
        frases_exclusividad = [
            "solo podemos", "únicamente podemos", "solamente podemos",
            "solo manejamos", "únicamente manejamos", "solamente manejamos",
            "solo trabajamos", "únicamente trabajamos", "trabajamos con"
        ]
        tiene_frase_exclusividad = any(frase in texto_lower for frase in frases_exclusividad)

        # FIX 39: EXCLUSIÓN - NO activar si cliente menciona OTRAS marcas además de Truper
        # Si dice "Truper y Urrea" o "Truper como otras marcas" → NO es exclusivo
        marcas_competencia = [
            'urrea', 'pretul', 'stanley', 'dewalt', 'surtek', 'evans', 'foset',
            'milwaukee', 'makita', 'bosch', 'hermex', 'toolcraft'
        ]

        # Palabras que indican MÚLTIPLES marcas (no exclusividad)
        palabras_multiples_marcas = [
            'diferentes marcas', 'varias marcas', 'otras marcas', 'distintas marcas',
            'y', 'como', 'también', 'además', 'junto con', 'entre ellas'
        ]

        menciona_otras_marcas = any(marca in texto_lower for marca in marcas_competencia)
        indica_multiples = any(palabra in texto_lower for palabra in palabras_multiples_marcas)

        # DETECCIÓN FINAL: 3 formas de detectar TRUPER exclusivo
        # PERO si menciona otras marcas O indica múltiples → NO es exclusivo
        es_truper_exclusivo = (
            (any(frase in texto_lower for frase in frases_solo_truper) or  # Forma 1: Listas directas
             any(frase in texto_lower for frase in frases_trabajamos_truper) or  # Forma 2: "trabajamos con truper"
             (mencion_truper and tiene_frase_exclusividad))  # Forma 3: Combinación
            and not (menciona_otras_marcas or indica_multiples)  # FIX 39: EXCLUSIÓN crítica
        )

        if es_truper_exclusivo:
            # Marcar como NO APTO y preparar despedida
            self.lead_data["estado_llamada"] = "Colgo"
            self.lead_data["pregunta_0"] = "Colgo"
            self.lead_data["pregunta_7"] = "NO APTO - SOLO TRUPER"
            self.lead_data["resultado"] = "NEGADO"
            self.lead_data["nivel_interes_clasificado"] = "NO APTO"
            print(f"[EMOJI] OBJECIÓN TRUPER detectada - Marcando como NO APTO")

            # FIX 34: Agregar respuesta de despedida INMEDIATA al historial
            # para que GPT NO genere más preguntas
            respuesta_truper = "Entiendo perfectamente. Truper es una excelente marca. Le agradezco mucho su tiempo y le deseo mucho éxito en su negocio. Que tenga un excelente día."

            self.conversation_history.append({
                "role": "assistant",
                "content": respuesta_truper
            })

            print(f"[EMOJI] FIX 34: Protocolo TRUPER activado - respuesta de despedida agregada al historial")
            print(f"[EMOJI] Retornando despedida inmediata: '{respuesta_truper}'")

            # Retornar la despedida INMEDIATAMENTE sin procesar con GPT
            return respuesta_truper  # FIX 34: CRITICAL - Retornar despedida sin llamar a GPT

        # Detectar interés
        palabras_interes = ["sí", "si", "me interesa", "claro", "adelante", "ok", "envíe", "mándame"]
        palabras_rechazo = ["no", "no gracias", "no me interesa", "ocupado", "no tengo tiempo"]

        if any(palabra in texto_lower for palabra in palabras_interes):
            self.lead_data["interesado"] = True
            self.lead_data["nivel_interes"] = "medio"

        elif any(palabra in texto_lower for palabra in palabras_rechazo):
            self.lead_data["interesado"] = False

        # ============================================================
        # PASO 1: DETECTAR REFERENCIAS PRIMERO (antes de WhatsApp)
        # ============================================================
        # Detectar referencias (cuando el cliente pasa contacto de otra persona)
        # IMPORTANTE: Ordenar patrones de MÁS ESPECÍFICO a MENOS ESPECÍFICO
        # para evitar falsos positivos
        patrones_referencia = [
            # Patrones CON nombre específico (grupo de captura)
            r'(?:te paso|paso|pasa)\s+(?:el )?contacto\s+(?:de|del)\s+([A-ZÁÉÍÓÚÑ][a-záéíóúñ]{2,}(?:\s+[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)?)',
            r'(?:contacta|habla con|llama a|comunicate con)\s+([A-ZÁÉÍÓÚÑ][a-záéíóúñ]{2,}(?:\s+[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)?)',
            r'(?:mi compañero|mi socio|mi jefe|el encargado|el dueño|el gerente)\s+(?:se llama\s+)?([A-ZÁÉÍÓÚÑ][a-záéíóúñ]{2,}(?:\s+[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)?)',

            # Patrones SIN nombre - Ofrecimientos de pasar contacto
            # NOTA: Ordenar de más específico a menos específico
            # IMPORTANTE: Usar [oó] para aceptar "paso" y "pasó" (con/sin acento)
            # IMPORTANTE: "el|su" es opcional para permitir "te pasó contacto" (sin "su/el")
            r'(?:te lo pas[oó]|se lo pas[oó]|te lo doy)',  # "sí, te lo paso" o "te lo pasó"
            r'(?:quiere|quieres?)\s+(?:el |su |tu )?(?:contacto|n[uú]mero)',  # "quiere su contacto"
            r'(?:te puedo pasar|puedo pasar|puedo dar|te puedo dar)\s+(?:el |su )?\s*(?:contacto|n[uú]mero)',  # "te puedo pasar su contacto" o "puedo pasar contacto"
            r'(?:le doy|te doy)\s+(?:el |su )?\s*(?:contacto|n[uú]mero)',  # "te doy su número" o "te doy contacto"
            r'(?:te pas[oó]|le pas[oó])\s+(?:el |su )?\s*(?:contacto|n[uú]mero)',  # "te paso/pasó su número" o "te pasó contacto"

            # FIX 241: Patrones adicionales para detectar ofrecimiento de teléfono
            r'(?:te pas[oó]|le pas[oó]|ah[ií] te paso)\s+(?:un |el )?tel[eé]fono',  # "ahí te paso un teléfono"
            r'(?:te doy|le doy)\s+(?:un |el |otro )?tel[eé]fono',  # "te doy un teléfono"
            r'(?:llam[ae]|marca|habla)\s+(?:a |al )?(?:este |otro |al )?(?:n[uú]mero|tel[eé]fono)',  # "llama a este número"
            r'(?:sucursal|otra tienda|otra sede)',  # "es una sucursal" - cliente sugiere llamar a otro lado
        ]

        for patron in patrones_referencia:
            match = re.search(patron, texto, re.IGNORECASE)
            if match:
                # Si el patrón captura un nombre (grupo 1)
                if match.lastindex and match.lastindex >= 1:
                    nombre_referido = match.group(1).strip()

                    # FIX 40: Filtrar palabras no válidas como nombres (productos, marcas, despedidas, pronombres)
                    palabras_invalidas = [
                        'número', 'telefono', 'contacto', 'whatsapp', 'correo', 'email', 'dato', 'información',
                        'gracias', 'hasta', 'luego', 'adiós', 'bye', 'bueno', 'favor', 'tiempo', 'momento',
                        'nosotros', 'ustedes', 'ellos', 'ellas', 'él', 'ella', 'yo', 'tú', 'usted',  # FIX 38: Pronombres
                        'herrajes', 'herraje', 'tornillos', 'tornillo', 'tuercas', 'tuerca', 'clavos', 'clavo',
                        'candados', 'candado', 'llaves', 'llave', 'cerraduras', 'cerradura', 'bisagras', 'bisagra',
                        'chapas', 'chapa',  # FIX 40: Producto específico (cerraduras)
                        'cinta', 'cintas', 'grifo', 'grifos', 'grifería', 'griferías', 'tubos', 'tubo',
                        'manguera', 'mangueras', 'cable', 'cables', 'alambre', 'alambres',
                        'truper', 'pretul', 'stanley', 'dewalt', 'urrea', 'surtek', 'evans', 'foset',
                        'nioval', 'toolcraft', 'milwaukee', 'makita', 'bosch',
                        'productos', 'producto', 'artículos', 'artículo', 'cosas', 'cosa', 'eso', 'nada'
                    ]
                    if nombre_referido.lower() not in palabras_invalidas and len(nombre_referido) > 2:
                        # Guardar en lead_data para procesarlo después
                        if "referencia_nombre" not in self.lead_data:
                            self.lead_data["referencia_nombre"] = nombre_referido
                            self.lead_data["referencia_telefono"] = ""  # Se capturará después si lo mencionan
                            self.lead_data["referencia_contexto"] = texto[:150]  # Contexto completo
                            print(f"[EMOJI] Referencia detectada: {nombre_referido}")
                            print(f"   Contexto: {texto[:100]}...")
                        break
                else:
                    # Si no hay nombre pero mencionan "te puedo pasar su contacto"
                    if "referencia_nombre" not in self.lead_data:
                        self.lead_data["referencia_nombre"] = ""  # Sin nombre todavía
                        self.lead_data["referencia_telefono"] = ""  # Se capturará después
                        self.lead_data["referencia_contexto"] = texto[:150]  # Contexto completo
                        print(f"[EMOJI] Referencia detectada (sin nombre aún)")
                        print(f"   Contexto: {texto[:100]}...")
                    break

        # Si tenemos una referencia pendiente, capturar nombre o número
        if "referencia_nombre" in self.lead_data:
            # 1. Si ya tenemos nombre (o referencia sin nombre) pero falta número, buscar número
            # IMPORTANTE: Checar si la key existe en el dict, porque puede ser "" (string vacío)
            if "referencia_nombre" in self.lead_data and not self.lead_data.get("referencia_telefono"):
                # PASO 1: Convertir números escritos a dígitos
                # "seis seis veintitrés 53 41 8" → "6 6 23 53 41 8"
                texto_convertido = convertir_numeros_escritos_a_digitos(texto)

                # PASO 2: Extraer TODOS los dígitos (quitar espacios, guiones, etc.)
                numero = re.sub(r'[^\d]', '', texto_convertido)

                print(f"[DEBUG] Scanner de dígitos: encontrados {len(numero)} dígitos en '{texto[:50]}...'")

                # IMPORTANTE: Ignorar secuencias muy cortas (1-5 dígitos) para evitar interrumpir
                # cuando el cliente está en medio de dictar el número
                if len(numero) >= 1 and len(numero) <= 5:
                    print(f"[EMOJI] Ignorando fragmento corto: {numero} ({len(numero)} dígitos) - cliente aún dictando, no interrumpir")
                    # NO agregamos mensajes al sistema, dejamos que el cliente continúe

                # Si encontramos 6+ dígitos, procesamos (ya está cerca del número completo)
                elif len(numero) >= 6:
                    # Validar que tenga exactamente 10 dígitos
                    if len(numero) == 10:
                        numero_completo = f"+52{numero}"
                        self.lead_data["referencia_telefono"] = numero_completo
                        print(f"[EMOJI] Número de referencia detectado: {numero_completo}")
                        print(f"   Asociado a: {self.lead_data.get('referencia_nombre', 'Encargado')}")

                        # Formatear número para repetir al cliente (ej: 66 23 53 41 85)
                        numero_formateado = ' '.join([numero[i:i+2] for i in range(0, len(numero), 2)])
                        self.conversation_history.append({
                            "role": "system",
                            "content": f"""[SISTEMA] [OK] Número completo capturado: {numero_formateado}

[EMOJI] FIX 175 - INSTRUCCIONES CRÍTICAS PARA REPETIR NÚMERO:
1. DEBES repetir el número EXACTAMENTE como lo capturaste: {numero_formateado}
2. NO conviertas a palabras como "ochenta y siete" - USA SOLO DÍGITOS
3. Di EXACTAMENTE: "Perfecto, el número es {numero_formateado}, ¿es correcto?"
4. NUNCA digas un número diferente - causa confusión y pérdida del cliente
5. Ejemplo CORRECTO: "el número es 87 18 97 02 31"
6. Ejemplo INCORRECTO: "el número es ochenta y siete dieciocho noventa y dos treinta y uno"

REPITE TEXTUALMENTE: {numero_formateado}"""
                        })
                    else:
                        # Número incorrecto (6-9 dígitos o 11+ dígitos)
                        if len(numero) < 10:
                            # Número incompleto: Verificar si está en pares/grupos para pedir dígito por dígito
                            if detectar_numeros_en_grupos(texto):
                                print(f"[WARN] Número incompleto Y detectado en pares/grupos: {numero} ({len(numero)} dígitos)")
                                self.conversation_history.append({
                                    "role": "system",
                                    "content": "[SISTEMA] El cliente está proporcionando el número en PARES o GRUPOS (ej: '66 23 53' o 'veintitres cincuenta'). Esto puede causar errores en la captura. Debes pedirle de manera amable que repita el número DÍGITO POR DÍGITO para mayor claridad. Ejemplo: 'Para asegurarme de anotarlo correctamente, ¿podría repetirme el número dígito por dígito? Por ejemplo: seis, seis, dos, tres, cinco, tres...'"
                                })
                            else:
                                print(f"[WARN] Número incompleto de referencia detectado: {numero} ({len(numero)} dígitos)")
                                numero_formateado = ' '.join([numero[i:i+2] for i in range(0, len(numero), 2)])
                                self.conversation_history.append({
                                    "role": "system",
                                    "content": f"[SISTEMA] El número del contacto está incompleto: {numero_formateado} ({len(numero)} dígitos). Los números en México deben tener EXACTAMENTE 10 dígitos. Debes pedirle que confirme el número completo de 10 dígitos de manera natural."
                                })
                        else:
                            print(f"[WARN] Número con dígitos de más de referencia detectado: {numero} ({len(numero)} dígitos)")
                            numero_formateado = ' '.join([numero[i:i+2] for i in range(0, len(numero), 2)])
                            self.conversation_history.append({
                                "role": "system",
                                "content": f"[SISTEMA] El número del contacto tiene dígitos de más: {numero_formateado} ({len(numero)} dígitos, pero deberían ser 10). Probablemente hubo un error en la captura. Debes pedirle que repita el número DÍGITO POR DÍGITO de manera clara y natural. Ejemplo: 'Disculpe, parece que capté algunos dígitos de más. ¿Podría repetirme el número dígito por dígito para asegurarme de anotarlo correctamente? Por ejemplo: seis, seis, dos, tres...'"
                            })

            # 2. Si NO tenemos nombre pero sí número, buscar nombre con patrones simples
            elif not self.lead_data.get("referencia_nombre") and self.lead_data.get("referencia_telefono"):
                # Patrones para capturar nombres: "se llama Juan", "es Pedro", "su nombre es María"
                patrones_nombre = [
                    r'(?:se llama|llama)\s+([A-ZÁÉÍÓÚÑ][a-záéíóúñ]{2,}(?:\s+[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)?)',
                    r'(?:es|nombre es)\s+([A-ZÁÉÍÓÚÑ][a-záéíóúñ]{2,}(?:\s+[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)?)',
                    r'^(?:sí|si),?\s+([A-ZÁÉÍÓÚÑ][a-záéíóúñ]{2,}(?:\s+[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)?)',
                ]

                for patron in patrones_nombre:
                    match = re.search(patron, texto, re.IGNORECASE)
                    if match:
                        nombre = match.group(1).strip()
                        # FIX 40: Lista expandida - NO capturar productos, marcas ni pronombres como nombres
                        palabras_invalidas = [
                            'número', 'telefono', 'contacto', 'whatsapp', 'correo', 'email', 'dato', 'información', 'ese', 'este',
                            'nosotros', 'ustedes', 'ellos', 'ellas', 'él', 'ella', 'yo', 'tú', 'usted',  # FIX 38: Pronombres
                            'herrajes', 'herraje', 'tornillos', 'tornillo', 'tuercas', 'tuerca', 'clavos', 'clavo',
                            'candados', 'candado', 'llaves', 'llave', 'cerraduras', 'cerradura', 'bisagras', 'bisagra',
                            'chapas', 'chapa',  # FIX 40: Producto específico (cerraduras)
                            'cinta', 'cintas', 'grifo', 'grifos', 'grifería', 'griferías', 'tubos', 'tubo',
                            'manguera', 'mangueras', 'cable', 'cables', 'alambre', 'alambres',
                            'truper', 'pretul', 'stanley', 'dewalt', 'urrea', 'surtek', 'evans', 'foset',
                            'nioval', 'toolcraft', 'milwaukee', 'makita', 'bosch',
                            'productos', 'producto', 'artículos', 'artículo', 'cosas', 'cosa', 'eso', 'nada'
                        ]
                        if nombre.lower() not in palabras_invalidas and len(nombre) > 2:
                            self.lead_data["referencia_nombre"] = nombre
                            print(f"[EMOJI] Nombre de referencia detectado: {nombre}")
                            print(f"   Asociado al número: {self.lead_data.get('referencia_telefono')}")
                            break

            # 3. Si NO tenemos nombre ni número, buscar número
            elif not self.lead_data.get("referencia_telefono"):
                # PASO 1: Convertir números escritos a dígitos
                texto_convertido = convertir_numeros_escritos_a_digitos(texto)

                # PASO 2: Extraer TODOS los dígitos
                numero = re.sub(r'[^\d]', '', texto_convertido)

                print(f"[DEBUG] Scanner de dígitos (sin nombre): encontrados {len(numero)} dígitos en '{texto[:50]}...'")

                # IMPORTANTE: Ignorar secuencias muy cortas (1-5 dígitos) para evitar interrumpir
                # cuando el cliente está en medio de dictar el número
                if len(numero) >= 1 and len(numero) <= 5:
                    print(f"[EMOJI] Ignorando fragmento corto: {numero} ({len(numero)} dígitos) - cliente aún dictando, no interrumpir")
                    # NO agregamos mensajes al sistema, dejamos que el cliente continúe

                # Si encontramos 6+ dígitos, procesamos (ya está cerca del número completo)
                elif len(numero) >= 6:
                    # Validar que tenga exactamente 10 dígitos
                    if len(numero) == 10:
                        numero_completo = f"+52{numero}"
                        self.lead_data["referencia_telefono"] = numero_completo
                        print(f"[EMOJI] Número de referencia detectado: {numero_completo}")
                        print(f"   Asociado a: {self.lead_data.get('referencia_nombre', 'Encargado')}")

                        # Formatear número para repetir al cliente (ej: 66 23 53 41 85)
                        numero_formateado = ' '.join([numero[i:i+2] for i in range(0, len(numero), 2)])
                        self.conversation_history.append({
                            "role": "system",
                            "content": f"""[SISTEMA] [OK] Número completo capturado: {numero_formateado}

[EMOJI] FIX 175 - INSTRUCCIONES CRÍTICAS PARA REPETIR NÚMERO:
1. DEBES repetir el número EXACTAMENTE como lo capturaste: {numero_formateado}
2. NO conviertas a palabras como "ochenta y siete" - USA SOLO DÍGITOS
3. Di EXACTAMENTE: "Perfecto, el número es {numero_formateado}, ¿es correcto?"
4. NUNCA digas un número diferente - causa confusión y pérdida del cliente
5. Ejemplo CORRECTO: "el número es 87 18 97 02 31"
6. Ejemplo INCORRECTO: "el número es ochenta y siete dieciocho noventa y dos treinta y uno"

REPITE TEXTUALMENTE: {numero_formateado}"""
                        })
                    else:
                        # Número incorrecto (6-9 dígitos o 11+ dígitos)
                        if len(numero) < 10:
                            # Número incompleto: Verificar si está en pares/grupos para pedir dígito por dígito
                            if detectar_numeros_en_grupos(texto):
                                print(f"[WARN] Número incompleto Y detectado en pares/grupos: {numero} ({len(numero)} dígitos)")
                                self.conversation_history.append({
                                    "role": "system",
                                    "content": "[SISTEMA] El cliente está proporcionando el número en PARES o GRUPOS (ej: '66 23 53' o 'veintitres cincuenta'). Esto puede causar errores en la captura. Debes pedirle de manera amable que repita el número DÍGITO POR DÍGITO para mayor claridad. Ejemplo: 'Para asegurarme de anotarlo correctamente, ¿podría repetirme el número dígito por dígito? Por ejemplo: seis, seis, dos, tres, cinco, tres...'"
                                })
                            else:
                                print(f"[WARN] Número incompleto de referencia detectado: {numero} ({len(numero)} dígitos)")
                                numero_formateado = ' '.join([numero[i:i+2] for i in range(0, len(numero), 2)])
                                self.conversation_history.append({
                                    "role": "system",
                                    "content": f"[SISTEMA] El número del contacto está incompleto: {numero_formateado} ({len(numero)} dígitos). Los números en México deben tener EXACTAMENTE 10 dígitos. Debes pedirle que confirme el número completo de 10 dígitos de manera natural."
                                })
                        else:
                            print(f"[WARN] Número con dígitos de más de referencia detectado: {numero} ({len(numero)} dígitos)")
                            numero_formateado = ' '.join([numero[i:i+2] for i in range(0, len(numero), 2)])
                            self.conversation_history.append({
                                "role": "system",
                                "content": f"[SISTEMA] El número del contacto tiene dígitos de más: {numero_formateado} ({len(numero)} dígitos, pero deberían ser 10). Probablemente hubo un error en la captura. Debes pedirle que repita el número DÍGITO POR DÍGITO de manera clara y natural. Ejemplo: 'Disculpe, parece que capté algunos dígitos de más. ¿Podría repetirme el número dígito por dígito para asegurarme de anotarlo correctamente? Por ejemplo: seis, seis, dos, tres...'"
                            })

        # ============================================================
        # FIX 17: DETECCIÓN - "YA TE LO DI/PASÉ EL NÚMERO"
        # ============================================================
        # Detectar cuando cliente dice que YA dio el WhatsApp anteriormente
        frases_ya_dio_numero = [
            "ya te lo di", "ya te lo dije", "ya te lo pasé", "ya te lo había dado",
            "ya te lo había pasado", "ya te lo mencioné", "ya te lo comenté",
            "ya lo tienes", "ya te lo envié", "ya está", "ya se lo di",
            "sí ya le dije", "ya le había pasado"
        ]

        if any(frase in texto_lower for frase in frases_ya_dio_numero):
            print(f"[WARN] Cliente dice que YA dio el número antes")
            self.conversation_history.append({
                "role": "system",
                "content": """[WARN] CRÍTICO: El cliente dice que YA te dio el número de WhatsApp anteriormente.

ACCIÓN INMEDIATA:
1. Revisa el historial de la conversación
2. Busca el número que te dio (probablemente esté en uno de los mensajes anteriores)
3. Si lo encuentras, confírmalo: "Tiene razón, discúlpeme. El número que tengo es [NÚMERO]. ¿Es correcto?"
4. Si NO lo encuentras, pide disculpas y solicítalo una última vez: "Tiene razón, discúlpeme. Para asegurarme de tenerlo bien, ¿me lo podría repetir una última vez?"

NO sigas pidiendo el número sin revisar el historial primero."""
            })

        # ============================================================
        # PASO 2: DETECTAR WHATSAPP (solo si NO hay referencia pendiente)
        # ============================================================
        # Detectar WhatsApp en el texto
        # Patrones: 3312345678, 33-1234-5678, +523312345678, 66 23 53 41 85, etc.
        patrones_tel = [
            r'\+?52\s?(\d{2})\s?(\d{2})\s?(\d{2})\s?(\d{2})\s?(\d{2})',  # +52 66 23 53 41 85 (10 dígitos espacio cada 2)
            r'(\d{2})\s(\d{2})\s(\d{2})\s(\d{2})\s(\d{2})',              # 66 23 53 41 85 (10 dígitos espacio cada 2)
            r'(\d{2})\s(\d{2})\s(\d{2})\s(\d{2})',                       # 33 12 12 83 (8 dígitos espacio cada 2) - FIX 12
            r'(\d{2})\s(\d{2})\s(\d{2})\s(\d{2})\s(\d{1})',              # 66 23 53 41 8 (9 dígitos espacio cada 2)
            r'\+?52\s?(\d{2})\s?(\d{4})\s?(\d{4})',                      # +52 33 1234 5678
            r'(\d{2})\s?(\d{4})\s?(\d{4})',                              # 33 1234 5678
            r'(\d{4,10})'                                                 # 4-10 dígitos sin espacios (capturar incluso muy cortos para alertar)
        ]

        # IMPORTANTE: Si ya detectamos una referencia pendiente, NO capturar números como WhatsApp
        # Los números deben guardarse como referencia_telefono
        tiene_referencia_pendiente = ("referencia_nombre" in self.lead_data and
                                      not self.lead_data.get("referencia_telefono"))

        if not tiene_referencia_pendiente:
            # Solo buscar WhatsApp si NO hay referencia pendiente
            for patron in patrones_tel:
                match = re.search(patron, texto)
                if match:
                    numero = ''.join(match.groups())

                    # Validar longitud del número (solo 10 dígitos)
                    if len(numero) != 10:
                        # Número incorrecto - pedir número de 10 dígitos
                        if len(numero) < 10:
                            # Casos especiales según longitud
                            if len(numero) <= 7:
                                # MUY CORTO (4-7 dígitos) - probablemente cliente interrumpido o número parcial
                                print(f"[EMOJI] Número MUY CORTO detectado: {numero} ({len(numero)} dígitos)")
                                self.conversation_history.append({
                                    "role": "system",
                                    "content": f"""[SISTEMA] [WARN] NÚMERO MUY INCOMPLETO: Solo captaste {len(numero)} dígitos ({numero}).

Los números de WhatsApp en México SIEMPRE tienen 10 dígitos.

ACCIÓN REQUERIDA:
1. NO guardes este número incompleto
2. Pide el número completo de forma clara y natural
3. Ejemplo: "Disculpe, solo alcancé a captar {numero}. ¿Me podría dar el número completo de 10 dígitos? Por ejemplo: tres, tres, uno, cero, dos, tres..."

IMPORTANTE: Espera a que el cliente dé los 10 dígitos completos antes de continuar."""
                                })
                            else:
                                # 8-9 dígitos - casi completo
                                print(f"[WARN] Número incompleto detectado: {numero} ({len(numero)} dígitos)")
                                numero_formateado = ' '.join([numero[i:i+2] for i in range(0, len(numero), 2)])
                                self.conversation_history.append({
                                    "role": "system",
                                    "content": f"[SISTEMA] El número de WhatsApp está incompleto: {numero_formateado} ({len(numero)} dígitos). Los números en México deben tener EXACTAMENTE 10 dígitos. Debes pedirle que confirme el número completo de 10 dígitos. Ejemplo: 'El número que tengo es {numero_formateado}, pero me parece que falta un dígito. ¿Me lo podría confirmar completo?'"
                                })
                        else:
                            print(f"[WARN] Número con dígitos de más detectado: {numero} ({len(numero)} dígitos)")
                            numero_formateado = ' '.join([numero[i:i+2] for i in range(0, len(numero), 2)])
                            self.conversation_history.append({
                                "role": "system",
                                "content": f"[SISTEMA] El número de WhatsApp tiene dígitos de más: {numero_formateado} ({len(numero)} dígitos, pero deberían ser 10). Probablemente hubo un error en la captura. Debes pedirle que repita el número DÍGITO POR DÍGITO de manera clara y natural. Ejemplo: 'Disculpe, parece que capté algunos dígitos de más. ¿Podría repetirme su WhatsApp dígito por dígito? Por ejemplo: seis, seis, dos, tres...'"
                            })
                        break

                    else:  # len(numero) == 10
                        numero_completo = f"+52{numero}"
                        print(f"[PHONE] WhatsApp detectado (10 dígitos): {numero_completo}")

                        # Validación simple: solo verificar formato y cantidad de dígitos
                        # Asumimos que todos los números móviles mexicanos de 10 dígitos tienen WhatsApp
                        self.lead_data["whatsapp"] = numero_completo
                        self.lead_data["whatsapp_valido"] = True
                        print(f"   [OK] Formato válido (10 dígitos)")
                        print(f"   [EMOJI] WhatsApp guardado: {numero_completo}")
                        print(f"   [EMOJI] FIX 168: WhatsApp guardado - PRÓXIMA respuesta incluirá ANTI-CORREO + DESPEDIDA")
                        print(f"   [EMOJI] FIX 168: FLAG whatsapp_valido=True → GPT NO debe pedir correo ni WhatsApp")

                        # FIX 168: Mejorado de FIX 167
                        # Ya NO usamos mensaje [SISTEMA] (se filtra en línea 2040)
                        # Ahora la instrucción se agrega directamente en el SYSTEM PROMPT dinámico
                        # Ver línea 3770+ en _construir_prompt_dinamico()

                    break
        else:
            print(f"[EMOJI] Referencia pendiente detectada - números se guardarán como referencia_telefono")

        # ============================================================
        # DETECCIÓN DE EMAIL (con validación y confirmación)
        # ============================================================
        # FIX 45: CONVERTIR EMAILS DELETREADOS A FORMATO CORRECTO
        # Cliente dice: "yahir sam rodriguez arroba gmail punto com"
        # Twilio transcribe: "yahir sam rodriguez arroba gmail punto com" (palabras separadas)
        # Necesitamos convertir a: "yahirsamrodriguez@gmail.com"

        texto_email_procesado = texto.lower()

        # FIX 221: CORREGIR TRANSCRIPCIONES INCORRECTAS DE DELETREO
        # Whisper/Deepgram a veces transcriben mal las ayudas mnemotécnicas:
        # - "U de Uva" → "udv" o "u de uva" o "uva"
        # - "B de Burro" → "bdb" o "b de burro"
        # Solución: Detectar patrones y extraer solo la letra inicial

        # Patrones comunes de ayudas mnemotécnicas mal transcritas
        ayudas_mnemotecnicas = {
            # "X de [Palabra]" - la primera letra es la correcta
            r'\bu\s*de\s*uva\b': 'u',
            r'\bb\s*de\s*burro\b': 'b',
            r'\bv\s*de\s*vaca\b': 'v',
            r'\bs\s*de\s*sol\b': 's',
            r'\bc\s*de\s*casa\b': 'c',
            r'\bd\s*de\s*dado\b': 'd',
            r'\be\s*de\s*elefante\b': 'e',
            r'\bf\s*de\s*foco\b': 'f',
            r'\bg\s*de\s*gato\b': 'g',
            r'\bh\s*de\s*hotel\b': 'h',
            r'\bi\s*de\s*iglesia\b': 'i',
            r'\bj\s*de\s*jarra\b': 'j',
            r'\bk\s*de\s*kilo\b': 'k',
            r'\bl\s*de\s*luna\b': 'l',
            r'\bm\s*de\s*mama\b': 'm', r'\bm\s*de\s*mamá\b': 'm',
            r'\bn\s*de\s*naranja\b': 'n',
            r'\bo\s*de\s*oso\b': 'o',
            r'\bp\s*de\s*papa\b': 'p', r'\bp\s*de\s*papá\b': 'p',
            r'\bq\s*de\s*queso\b': 'q',
            r'\br\s*de\s*rosa\b': 'r',
            r'\bt\s*de\s*toro\b': 't',
            r'\bw\s*de\s*washington\b': 'w',
            r'\bx\s*de\s*xilofono\b': 'x',
            r'\by\s*de\s*yoyo\b': 'y',
            r'\bz\s*de\s*zapato\b': 'z',
            # Transcripciones pegadas (Whisper junta las letras)
            r'\budv\b': 'u',  # "U de Uva" transcrito como "udv"
            r'\bbdb\b': 'b',  # "B de Burro" transcrito como "bdb"
            r'\bvdv\b': 'v',  # "V de Vaca" transcrito como "vdv"
            r'\bsds\b': 's',  # "S de Sol" transcrito como "sds"
            r'\bcdc\b': 'c',  # "C de Casa" transcrito como "cdc"
            r'\bgdg\b': 'g',  # "G de Gato" transcrito como "gdg"
            r'\bmdm\b': 'm',  # "M de Mamá" transcrito como "mdm"
        }

        for patron, reemplazo in ayudas_mnemotecnicas.items():
            if re.search(patron, texto_email_procesado, re.IGNORECASE):
                texto_original = texto_email_procesado
                texto_email_procesado = re.sub(patron, reemplazo, texto_email_procesado, flags=re.IGNORECASE)
                print(f"[WRENCH] FIX 221: Corregida ayuda mnemotécnica: '{texto_original}' → '{texto_email_procesado}'")

        # FIX 48: ELIMINAR AYUDAS MNEMOTÉCNICAS antes de procesar
        # Cliente dice: "Z a m de mamá r o D r y G de gato"
        # Cliente dice: "Z a de Armando m de mamá r de Rogelio o de Óscar"
        # Necesitamos eliminar: nombres propios, frases descriptivas, TODO excepto letras/números

        if 'arroba' in texto_email_procesado or any(dom in texto_email_procesado for dom in ['gmail', 'hotmail', 'outlook', 'yahoo', 'live', 'icloud']):
            # FIX 48B/192: ESTRATEGIA AGRESIVA - Eliminar TODAS las ayudas mnemotécnicas
            # Patrón: "X de [Palabra]" donde X es una letra y [Palabra] es la ayuda

            # Lista de palabras a eliminar (nombres propios y palabras comunes usadas como ayudas)
            palabras_ayuda = [
                # Preposiciones/conectores
                'de', 'del', 'con', 'como', 'para', 'por', 'sin', 'bajo', 'el', 'la', 'los', 'las', 'es', 'son',
                # FIX 371: Agregar "y" que aparece entre palabras del email
                'y', 'e', 'o', 'u', 'a',
                # FIX 160: Contextuales de correo
                'correo', 'email', 'mail', 'electrónico', 'electronico',
                # Nombres comunes en alfabeto radiofónico informal
                'mama', 'mamá', 'papa', 'papá', 'gato', 'casa', 'perro', 'vaca', 'burro',
                'rosa', 'ana', 'oscar', 'óscar', 'carlos', 'daniel', 'elena', 'fernando',
                'rogelio', 'armando', 'ricardo', 'sandra', 'teresa', 'ursula', 'vicente',
                'william', 'xavier', 'yolanda', 'zorro', 'antonio', 'beatriz',
                # FIX 160/192: Nombres propios comunes en correos y ayudas
                'luis', 'garcía', 'garcia', 'uva', 'juan', 'jose', 'josé', 'maría', 'maria', 'pedro',
                'miguel', 'angel', 'ángel', 'lopez', 'lópez', 'martinez', 'martínez', 'rodriguez', 'rodríguez',
                'gonzalez', 'gonzález', 'hernández', 'hernandez', 'ramirez', 'ramírez',
                'beto', 'memo', 'pepe', 'paco', 'pancho', 'lupe', 'chuy', 'toño', 'tono',
                'bruce', 'wayne', 'clark', 'peter', 'tony', 'steve', 'diana', 'bruce',
                # Palabras descriptivas comunes
                'latina', 'latino', 'grande', 'chico', 'ring', 'heredado', 'vedado',
                'acento', 'tilde', 'mayúscula', 'mayuscula', 'minúscula', 'minuscula',
                # Números escritos (a veces se mezclan)
                'uno', 'dos', 'tres', 'cuatro', 'cinco', 'seis', 'siete', 'ocho', 'nueve', 'cero',
                'diez', 'veinte', 'treinta', 'cuarenta', 'cincuenta', 'sesenta', 'setenta', 'ochenta', 'noventa'
            ]

            # FIX 192: PASO 1 - Eliminar patrón "X de [Palabra]" (ayudas mnemotécnicas explícitas)
            # Ejemplo: "b de Beto" → "b", "m de mamá" → "m"
            texto_original_debug = texto_email_procesado
            patron_letra_de_ayuda = r'\b([a-z0-9])\s+de\s+\w+\b'
            texto_email_procesado = re.sub(patron_letra_de_ayuda, r'\1', texto_email_procesado, flags=re.IGNORECASE)

            # FIX 192: PASO 2 - Eliminar lista de palabras de ayuda comunes
            patron_palabras_ayuda = r'\b(' + '|'.join(palabras_ayuda) + r')\b'
            texto_email_procesado = re.sub(patron_palabras_ayuda, '', texto_email_procesado, flags=re.IGNORECASE)

            # Limpiar espacios múltiples que quedan después de eliminar ayudas
            texto_email_procesado = re.sub(r'\s+', ' ', texto_email_procesado).strip()

            print(f"[WRENCH] FIX 48B/192 - Ayudas mnemotécnicas eliminadas (AGRESIVO)")
            print(f"   Original: '{texto[:100]}...'")
            print(f"   Paso 1 (X de Palabra): '{texto_original_debug[:100]}...'")
            print(f"   Paso 2 (sin ayudas): '{texto_email_procesado[:100]}...'")

        # FIX 371: PRIMERO convertir "arroba" a "@" para detectar el límite del email
        texto_email_procesado = re.sub(r'\b(arroba|aroba|a roba)\b', '@', texto_email_procesado)

        # FIX 371: Eliminar puntos/comas que están ANTES del @ (errores de transcripción)
        # Ejemplo: "Tesoro. Arroba" → "Tesoro Arroba" → "Tesoro @"
        # Buscar: [palabra].  @ (punto antes del @) y eliminarlo
        texto_email_procesado = re.sub(r'\.\s*@', ' @', texto_email_procesado)
        texto_email_procesado = re.sub(r',\s*@', ' @', texto_email_procesado)

        # "punto" → "."
        # IMPORTANTE: Solo reemplazar "punto" cuando está en contexto de email (cerca de @, gmail, com, etc.)
        # NO reemplazar en contextos como "punto de venta"
        if '@' in texto_email_procesado or any(dom in texto_email_procesado for dom in ['gmail', 'hotmail', 'outlook', 'yahoo', 'live', 'icloud']):
            texto_email_procesado = re.sub(r'\bpunto\b', '.', texto_email_procesado)

        # "guión" → "-"
        texto_email_procesado = re.sub(r'\b(guion|guión)\b', '-', texto_email_procesado)

        # "guión bajo" / "underscore" → "_"
        texto_email_procesado = re.sub(r'\b(guion bajo|guión bajo|underscore|bajo)\b', '_', texto_email_procesado)

        # Paso 2: Detectar y reconstruir email deletreado
        # Patrón 1: [palabras/letras] @ [palabras/letras] . [dominio]
        # Ejemplo: "yahir sam rodriguez @ gmail . com"
        patron_email_deletreado = r'([a-z0-9._-]+(?:\s+[a-z0-9._-]+)*)\s*@\s*([a-z0-9.-]+(?:\s+[a-z0-9.-]+)*)\s*\.\s*([a-z]{2,})'
        match_deletreado = re.search(patron_email_deletreado, texto_email_procesado)

        # FIX 117: Patrón 2: Solo dominio sin arroba (ej: "coprofesa punto net")
        # Cliente a veces solo dice el dominio asumiendo que ya dijo el usuario antes
        patron_solo_dominio = r'\b([a-z0-9._-]+(?:\s+[a-z0-9._-]+)*)\s*\.\s*(net|com|org|mx|edu|gob)\b'
        match_solo_dominio = None
        if not match_deletreado:
            match_solo_dominio = re.search(patron_solo_dominio, texto_email_procesado)

        if match_deletreado:
            # Reconstruir email eliminando espacios
            nombre_local = match_deletreado.group(1).replace(' ', '')  # "yahir sam rodriguez" → "yahirsamrodriguez"
            dominio = match_deletreado.group(2).replace(' ', '')        # "gmail" → "gmail"
            extension = match_deletreado.group(3).replace(' ', '')      # "com" → "com"

            email_reconstruido = f"{nombre_local}@{dominio}.{extension}"

            print(f"[WRENCH] FIX 45 - Email deletreado detectado y reconstruido:")
            print(f"   Original: '{texto[:80]}...'")
            print(f"   Procesado: '{texto_email_procesado[:80]}...'")
            print(f"   Email reconstruido: '{email_reconstruido}'")

            # Usar el email reconstruido directamente
            email_detectado = email_reconstruido
            self.lead_data["email"] = email_detectado
            print(f"[EMAIL] Email detectado (deletreado): {email_detectado}")

            # FIX 98/118: DESPEDIRSE INMEDIATAMENTE después de capturar email
            self.conversation_history.append({
                "role": "system",
                "content": f"""[SISTEMA] [OK] Email capturado (deletreado): {email_detectado}

[WARN][WARN][WARN] FIX 98/118: DESPEDIDA INMEDIATA - CLIENTE OCUPADO [WARN][WARN][WARN]

El cliente está OCUPADO en mostrador. Ya tienes el EMAIL.

DEBES DESPEDIRTE AHORA:
"Perfecto, ya lo tengo anotado. Le llegará el catálogo en las próximas horas. Muchas gracias por su tiempo. Que tenga un excelente día."

[EMOJI] FIX 118: NO REPITAS EL CORREO
[ERROR] NUNCA digas el correo de vuelta (riesgo de deletrearlo mal)
[ERROR] Solo di: "ya lo tengo anotado" o "perfecto, anotado"
[ERROR] NO hagas más preguntas
[ERROR] NO pidas confirmación del correo (ya lo tienes)
[EMOJI] FIX 166: NO PIDAS MÁS DATOS[ERROR] NO pidas WhatsApp (el email es suficiente)[ERROR] NO pidas número telefónico
[ERROR] NO preguntes sobre productos, proveedores, etc.
[OK] DESPEDIRSE INMEDIATAMENTE y COLGAR

IMPORTANTE:
- El cliente está OCUPADO - termina la llamada YA
- Ya tienes nombre + email = SUFICIENTE
- Despedida corta y profesional
- NO repetir el correo evita errores de transcripción"""
            })

        # FIX 117: Manejar cuando solo se dice dominio (ej: "coprofesa punto net")
        elif match_solo_dominio:
            dominio_completo = match_solo_dominio.group(1).replace(' ', '') + '.' + match_solo_dominio.group(2)
            print(f"[WRENCH] FIX 117 - Dominio parcial detectado: {dominio_completo}")
            print(f"   Original: '{texto[:80]}...'")

            # Pedir el usuario del email
            self.conversation_history.append({
                "role": "system",
                "content": f"""[SISTEMA] [WARN] Email incompleto detectado: {dominio_completo}

El cliente proporcionó solo el DOMINIO ({dominio_completo}) pero falta el USUARIO antes del @.

ACCIÓN REQUERIDA:
Di EXACTAMENTE: "Perfecto, tengo {dominio_completo}. ¿Cuál es la primera parte del correo, antes del arroba?"

Ejemplo esperado del cliente: "sandra" o "info" o "ventas"
Entonces formarás el email completo: [usuario]@{dominio_completo}"""
            })

        # Patrón estricto para emails válidos (detectar emails que ya vienen formateados)
        # Solo procesar si NO se detectó email deletreado anteriormente
        if not match_deletreado and not match_solo_dominio:
            patron_email = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
            match_email = re.search(patron_email, texto)

            if match_email:
                email_detectado = match_email.group(0)
                self.lead_data["email"] = email_detectado
                print(f"[EMAIL] Email detectado: {email_detectado}")

                # FIX 98: DESPEDIRSE INMEDIATAMENTE después de capturar email
                self.conversation_history.append({
                    "role": "system",
                    "content": f"""[SISTEMA] [OK] Email capturado: {email_detectado}

[WARN][WARN][WARN] FIX 98: DESPEDIDA INMEDIATA - CLIENTE OCUPADO [WARN][WARN][WARN]

El cliente está OCUPADO en mostrador. Ya tienes el EMAIL.

DEBES DESPEDIRTE AHORA:
"Perfecto, ya lo tengo anotado. Le llegará el catálogo en las próximas horas. Muchas gracias por su tiempo. Que tenga un excelente día."

[ERROR] NO hagas más preguntas
[ERROR] NO pidas confirmación del correo (ya lo tienes)
[ERROR] NO preguntes sobre productos, proveedores, etc.
[OK] DESPEDIRSE INMEDIATAMENTE y COLGAR

IMPORTANTE:
- El cliente está OCUPADO - termina la llamada YA
- Ya tienes nombre + email = SUFICIENTE
- Despedida corta y profesional"""
                })
            else:
                # Detectar posibles emails incompletos o malformados
                # Buscar palabras que sugieren que el cliente está dando un email
                palabras_email = ["arroba", "@", "gmail", "hotmail", "outlook", "yahoo", "correo", "email"]

                if any(palabra in texto_lower for palabra in palabras_email):
                    # FIX 49: Contador de intentos fallidos de captura de email
                    if not hasattr(self, 'email_intentos_fallidos'):
                        self.email_intentos_fallidos = 0

                    self.email_intentos_fallidos += 1
                    print(f"[WARN] Posible email incompleto o malformado detectado (Intento {self.email_intentos_fallidos}): '{texto[:100]}...'")

                    # Si ya fallamos 2+ veces, ofrecer alternativa de WhatsApp
                    if self.email_intentos_fallidos >= 2:
                        print(f"[EMOJI] FIX 49: Email falló {self.email_intentos_fallidos} veces - ofrecer alternativa WhatsApp")
                        self.conversation_history.append({
                            "role": "system",
                            "content": """[SISTEMA] [EMOJI] PROBLEMA PERSISTENTE CON EMAIL (2+ intentos fallidos)

El cliente ha intentado deletrear el email 2 o más veces pero sigue sin capturarse correctamente.
La captura de emails por voz es POCO CONFIABLE cuando hay ayudas mnemotécnicas.

[WARN][WARN][WARN] ACCIÓN OBLIGATORIA - OFRECER ALTERNATIVA:

Di EXACTAMENTE:
"Disculpe, veo que hay dificultades con la captura del correo por teléfono. Para asegurarme de tenerlo correcto, tengo dos opciones:

1. Le puedo enviar el catálogo por WhatsApp a su número [NÚMERO SI LO TIENES], y desde ahí usted me puede escribir su correo para tenerlo bien anotado.

2. O si prefiere, me lo puede escribir por WhatsApp y yo se lo confirmo.

¿Qué opción prefiere?"

IMPORTANTE:
- NO vuelvas a pedir que deletree el email por voz
- La solución es usar WhatsApp/mensaje de texto
- Así evitamos más errores de transcripción"""
                        })
                    else:
                        # Primer intento fallido - pedir una vez más
                        self.conversation_history.append({
                            "role": "system",
                            "content": """[SISTEMA] [WARN] POSIBLE EMAIL INCOMPLETO - EL CLIENTE ESTÁ DELETREANDO

Detecté que el cliente está proporcionando un email letra por letra, pero aún NO está completo.

[EMOJI] FIX 191: PROHIBIDO DECIR "PERFECTO, YA LO TENGO ANOTADO"
El cliente AÚN está hablando. NO lo interrumpas con despedidas.

ACCIÓN REQUERIDA:
1. Pide al cliente que CONTINÚE con el resto del correo
2. Di algo como: "Perfecto, excelente. Por favor, adelante con el correo."
3. O: "Entiendo, ¿me podría proporcionar el correo electrónico para enviar la información?"

[ERROR] NO HACER:
- NO digas "ya lo tengo anotado" (NO lo tienes completo)
- NO te despidas (el cliente sigue hablando)
- NO inventes el correo

[OK] HACER:
- Escucha pacientemente cada letra
- Deja que el cliente termine de deletrear
- Solo cuando tengas el correo COMPLETO (ej: juan@gmail.com), ahí sí confirma"""
                        })

        # Detectar productos de interés
        productos_keywords = {
            'cinta': 'Cinta tapagoteras',
            'grifería': 'Grifería',
            'grifo': 'Grifería',
            'herramienta': 'Herramientas',
            'candado': 'Candados y seguridad',
            'llave': 'Cerraduras',
            'tornillo': 'Tornillería'
        }

        for keyword, producto in productos_keywords.items():
            if keyword in texto_lower:
                if self.lead_data["productos_interes"]:
                    self.lead_data["productos_interes"] += f", {producto}"
                else:
                    self.lead_data["productos_interes"] = producto

        # Detectar objeciones
        objeciones_keywords = [
            "caro", "precio alto", "ya tengo proveedor", "no me interesa",
            "no tengo tiempo", "no da confianza", "no conocemos", "lejos"
        ]

        for objecion in objeciones_keywords:
            if objecion in texto_lower:
                if objecion not in self.lead_data["objeciones"]:
                    self.lead_data["objeciones"].append(objecion)

        # Detectar reprogramación
        if any(palabra in texto_lower for palabra in ["llama después", "llámame", "después", "más tarde", "reprograma", "otro día", "mañana"]):
            self.lead_data["estado_llamada"] = "reprogramar"
            print(f"[EMOJI] Reprogramación detectada en texto: {texto[:50]}...")

        # Agregar a notas
        if self.lead_data["notas"]:
            self.lead_data["notas"] += f" | {texto[:100]}"
        else:
            self.lead_data["notas"] = texto[:100]

        # ============================================================
        # CORRECCIÓN DE NOMBRE (Género y Correcciones del Cliente)
        # ============================================================
        # FIX 47: Detectar si el cliente está corrigiendo su nombre
        # Patrones mejorados para capturar el nombre CORRECTO, no el incorrecto

        # PATRÓN 1 (FIX 47): "no me llamo [NOMBRE_MAL] me llamo [NOMBRE_BUENO]"
        # Ejemplo: "yo no me llamo Jason me llamo Yahir"
        patron_correccion_completa = r'no\s+me\s+llamo\s+[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+\s+(?:me llamo|soy)\s+([A-ZÁÉÍÓÚÑ][a-záéíóúñ]{2,})'
        match_completo = re.search(patron_correccion_completa, texto, re.IGNORECASE)

        if match_completo:
            nombre_corregido = match_completo.group(1).strip()
            print(f"[WRENCH] FIX 47 - Corrección detectada: 'no me llamo X me llamo {nombre_corregido}'")
        else:
            # PATRONES ORIGINALES (para otros casos)
            patrones_correccion_nombre = [
                # "es Yahir, no..." → captura Yahir
                r'es\s+([A-ZÁÉÍÓÚÑ][a-záéíóúñ]{2,}),?\s+no\s+',
                # "Yahir, no..." → captura Yahir (al inicio)
                r'^([A-ZÁÉÍÓÚÑ][a-záéíóúñ]{2,}),?\s+no\s+',
            ]

            nombre_corregido = None
            for patron in patrones_correccion_nombre:
                match = re.search(patron, texto, re.IGNORECASE)
                if match:
                    nombre_corregido = match.group(1).strip()
                    break

        # Solo procesar si se detectó corrección
        if match_completo or nombre_corregido:
            # FIX 40: Verificar que sea un nombre válido (NO productos, marcas ni pronombres)
            palabras_invalidas = [
                'número', 'telefono', 'contacto', 'whatsapp', 'correo', 'email', 'verdad', 'cierto',
                # FIX 38: Pronombres
                'nosotros', 'ustedes', 'ellos', 'ellas', 'él', 'ella', 'yo', 'tú', 'usted',
                # Productos de ferretería
                'herrajes', 'herraje', 'tornillos', 'tornillo', 'tuercas', 'tuerca', 'clavos', 'clavo',
                'candados', 'candado', 'llaves', 'llave', 'cerraduras', 'cerradura', 'bisagras', 'bisagra',
                'chapas', 'chapa',  # FIX 40: Producto específico (cerraduras)
                'cinta', 'cintas', 'grifo', 'grifos', 'grifería', 'griferías', 'tubos', 'tubo',
                'manguera', 'mangueras', 'cable', 'cables', 'alambre', 'alambres',
                # Marcas comunes
                'truper', 'pretul', 'stanley', 'dewalt', 'urrea', 'surtek', 'evans', 'foset',
                'nioval', 'toolcraft', 'milwaukee', 'makita', 'bosch',
                # Palabras genéricas
                'productos', 'producto', 'artículos', 'artículo', 'cosas', 'cosa', 'eso', 'nada'
            ]
            if nombre_corregido and nombre_corregido.lower() not in palabras_invalidas and len(nombre_corregido) > 2:
                # Actualizar nombre en lead_data
                nombre_anterior = self.lead_data.get("nombre_contacto", "")
                self.lead_data["nombre_contacto"] = nombre_corregido
                print(f"[EMOJI] Nombre CORREGIDO por cliente: '{nombre_anterior}' → '{nombre_corregido}'")

                # FIX 47: Enviar instrucción ULTRA-CLARA a GPT para usar el nombre correcto
                self.conversation_history.append({
                    "role": "system",
                    "content": f"""[EMOJI] CORRECCIÓN CRÍTICA DE NOMBRE [EMOJI]

El cliente acaba de corregir su nombre:
[ERROR] Nombre INCORRECTO que usaste antes: "{nombre_anterior}"
[OK] Nombre CORRECTO: "{nombre_corregido}"

ACCIÓN INMEDIATA OBLIGATORIA:
1. PIDE DISCULPAS por el error: "Disculpe, {nombre_corregido}, tiene razón."
2. De ahora en adelante, SIEMPRE usa "{nombre_corregido}" (NO "{nombre_anterior}")
3. En la despedida, usa "{nombre_corregido}" (NO "{nombre_anterior}")
4. NO cambies ni el género ni la ortografía de "{nombre_corregido}"

Ejemplo de disculpa:
"Disculpe, {nombre_corregido}, tiene toda la razón. Permítame continuar..."

IMPORTANTE: El nombre correcto es "{nombre_corregido}", NO "{nombre_anterior}"."""
                })

        # Capturar respuestas del formulario de 7 preguntas
        self._capturar_respuestas_formulario(texto, texto_lower)

    def _validar_whatsapp(self, numero: str) -> bool:
        """
        Valida si un número tiene WhatsApp activo

        Returns:
            bool: True si tiene WhatsApp, False si no
        """
        if not self.whatsapp_validator:
            # Sin validador, asumimos válido
            self.lead_data["whatsapp_valido"] = True
            return True

        try:
            resultado = self.whatsapp_validator.validar(numero)
            tiene_whatsapp = resultado.get('tiene_whatsapp', False)

            self.lead_data["whatsapp_valido"] = tiene_whatsapp

            if tiene_whatsapp:
                print(f"[OK] WhatsApp válido: {numero}")
                return True
            else:
                print(f"[WARN] WhatsApp NO válido: {numero}")
                # Limpiar el WhatsApp del lead_data ya que no es válido
                self.lead_data["whatsapp"] = ""
                self.lead_data["whatsapp_valido"] = False
                return False

        except Exception as e:
            print(f"[ERROR] Error al validar WhatsApp: {e}")
            return False

    def _capturar_respuestas_formulario(self, texto: str, texto_lower: str):
        """
        Captura respuestas del formulario de 7 preguntas de forma automática
        durante la conversación natural

        Las preguntas se hacen de forma SUTIL e INDIRECTA, no como cuestionario.
        Este método analiza las respuestas del cliente y las categoriza.
        """

        # PREGUNTA 1: Necesidades del Cliente (Opciones múltiples)
        # Opciones: Entregas Rápidas, Líneas de Crédito, Contra Entrega, Envío Gratis, Precio Preferente, Evaluar Calidad
        necesidades_detectadas = []

        if any(palabra in texto_lower for palabra in ["entrega", "entregar", "rápid", "rapido", "pronto", "envío rápido", "tiempo", "tiempos", "urgente", "inmediato"]):
            if "Entregas Rápidas" not in self.lead_data["pregunta_1"]:
                necesidades_detectadas.append("Entregas Rápidas")

        if any(palabra in texto_lower for palabra in ["crédito", "credito", "financiamiento", "a crédito", "plazo"]):
            if "Líneas de Crédito" not in self.lead_data["pregunta_1"]:
                necesidades_detectadas.append("Líneas de Crédito")

        if any(palabra in texto_lower for palabra in ["contra entrega", "cod", "pago al recibir", "pago contra entrega"]):
            if "Contra Entrega" not in self.lead_data["pregunta_1"]:
                necesidades_detectadas.append("Contra Entrega")

        if any(palabra in texto_lower for palabra in ["envío gratis", "envio gratis", "sin costo de envío", "envío sin costo"]):
            if "Envío Gratis" not in self.lead_data["pregunta_1"]:
                necesidades_detectadas.append("Envío Gratis")

        if any(palabra in texto_lower for palabra in ["precio", "costo", "económico", "barato", "buen precio", "precio preferente"]):
            if "Precio Preferente" not in self.lead_data["pregunta_1"]:
                necesidades_detectadas.append("Precio Preferente")

        if any(palabra in texto_lower for palabra in ["calidad", "probar", "muestra", "evaluar", "ver cómo", "verificar calidad"]):
            if "Evaluar Calidad" not in self.lead_data["pregunta_1"]:
                necesidades_detectadas.append("Evaluar Calidad")

        # Agregar necesidades detectadas
        if necesidades_detectadas:
            if self.lead_data["pregunta_1"]:
                existentes = [n.strip() for n in self.lead_data["pregunta_1"].split(",")]
                for necesidad in necesidades_detectadas:
                    if necesidad not in existentes:
                        existentes.append(necesidad)
                self.lead_data["pregunta_1"] = ", ".join(existentes)
            else:
                self.lead_data["pregunta_1"] = ", ".join(necesidades_detectadas)

        # PREGUNTA 2: Toma de Decisiones (Sí/No)
        if not self.lead_data["pregunta_2"]:
            # Detección explícita
            if any(palabra in texto_lower for palabra in ["soy el dueño", "soy dueño", "yo autorizo", "yo decido", "yo soy quien", "sí, yo"]):
                self.lead_data["pregunta_2"] = "Sí"
                print(f"[EMOJI] Pregunta 2 detectada: Sí (toma decisiones)")
            elif any(palabra in texto_lower for palabra in ["tengo que consultar", "no soy el dueño", "no puedo decidir", "habla con", "consultar con"]):
                self.lead_data["pregunta_2"] = "No"
                print(f"[EMOJI] Pregunta 2 detectada: No (no toma decisiones)")
            # Inferencia: Si dice que es encargado de compras o gerente
            elif any(palabra in texto_lower for palabra in ["encargado de compras", "yo soy el encargado", "gerente", "administrador", "yo manejo"]):
                self.lead_data["pregunta_2"] = "Sí (Bruce)"
                print(f"[EMOJI] Pregunta 2 inferida: Sí (Bruce) - es encargado/gerente")

        # PREGUNTA 3: Pedido Inicial (Crear Pedido Inicial/No)
        if not self.lead_data["pregunta_3"]:
            if any(palabra in texto_lower for palabra in ["arma el pedido", "sí, armalo", "dale, arma", "prepara el pedido", "hazme el pedido"]):
                self.lead_data["pregunta_3"] = "Crear Pedido Inicial Sugerido"
                print(f"[EMOJI] Pregunta 3 detectada: Crear Pedido Inicial Sugerido")
            elif any(palabra in texto_lower for palabra in ["no quiero pedido", "no hagas pedido", "todavía no", "aún no", "primero quiero ver"]):
                self.lead_data["pregunta_3"] = "No"
                print(f"[EMOJI] Pregunta 3 detectada: No")

        # PREGUNTA 4: Pedido de Muestra (Sí/No)
        if not self.lead_data["pregunta_4"]:
            # Detectar aceptación de pedido de muestra de $1,500
            if any(palabra in texto_lower for palabra in ["sí, la muestra", "acepto la muestra", "dale con la muestra", "sí, el pedido de muestra", "está bien $1,500", "está bien 1500"]):
                self.lead_data["pregunta_4"] = "Sí"
                print(f"[EMOJI] Pregunta 4 detectada: Sí (acepta muestra)")
            elif any(palabra in texto_lower for palabra in ["no, la muestra", "no quiero muestra", "no, gracias", "no me interesa la muestra"]):
                self.lead_data["pregunta_4"] = "No"
                print(f"[EMOJI] Pregunta 4 detectada: No (rechaza muestra)")

        # PREGUNTA 5: Compromiso de Fecha (Sí/No/Tal vez)
        if not self.lead_data["pregunta_5"]:
            if any(palabra in texto_lower for palabra in ["sí, esta semana", "esta semana sí", "dale, esta semana", "arrancamos esta semana"]):
                self.lead_data["pregunta_5"] = "Sí"
                print(f"[EMOJI] Pregunta 5 detectada: Sí (esta semana)")
            elif any(palabra in texto_lower for palabra in ["no, esta semana no", "la próxima", "el próximo mes", "todavía no puedo"]):
                self.lead_data["pregunta_5"] = "No"
                print(f"[EMOJI] Pregunta 5 detectada: No")
            elif any(palabra in texto_lower for palabra in ["tal vez", "talvez", "lo veo", "no sé", "lo pensare", "a ver"]):
                self.lead_data["pregunta_5"] = "Tal vez"
                print(f"[EMOJI] Pregunta 5 detectada: Tal vez")

        # PREGUNTA 6: Método de Pago TDC (Sí/No/Tal vez)
        if not self.lead_data["pregunta_6"]:
            if any(palabra in texto_lower for palabra in ["sí, con tarjeta", "acepto tarjeta", "con tdc", "sí, cierro", "dale, cierro"]):
                self.lead_data["pregunta_6"] = "Sí"
                print(f"[EMOJI] Pregunta 6 detectada: Sí (acepta TDC)")
            elif any(palabra in texto_lower for palabra in ["no con tarjeta", "no quiero tarjeta", "prefiero efectivo", "solo efectivo"]):
                self.lead_data["pregunta_6"] = "No"
                print(f"[EMOJI] Pregunta 6 detectada: No")
            elif any(palabra in texto_lower for palabra in ["tal vez", "lo veo", "veo lo de la tarjeta"]):
                self.lead_data["pregunta_6"] = "Tal vez"
                print(f"[EMOJI] Pregunta 6 detectada: Tal vez")

        # PREGUNTA 7: Conclusión (se determina automáticamente al final de la llamada)
        # No se captura aquí, se determina en el método _determinar_conclusion()

    def _inferir_respuestas_faltantes(self):
        """
        Infiere respuestas faltantes basándose en el contexto de la conversación
        Marca las inferencias con "(Bruce)" para indicar que fueron deducidas
        """
        notas_lower = self.lead_data["notas"].lower()

        # PREGUNTA 2: Si no respondió pero capturamos WhatsApp, probablemente toma decisiones
        if not self.lead_data["pregunta_2"] and self.lead_data["whatsapp"]:
            self.lead_data["pregunta_2"] = "Sí (Bruce)"
            print(f"[EMOJI] Pregunta 2 inferida: Sí (Bruce) - dio WhatsApp, probablemente toma decisiones")

        # PREGUNTA 3: Si dijo que no quiere pedido o solo quiere catálogo
        if not self.lead_data["pregunta_3"]:
            if self.lead_data["whatsapp"] and any(palabra in notas_lower for palabra in ["catálogo", "catalogo", "lo reviso", "envía", "manda"]):
                self.lead_data["pregunta_3"] = "No (Bruce)"
                print(f"[EMOJI] Pregunta 3 inferida: No (Bruce) - solo quiere catálogo")
            elif not self.lead_data["whatsapp"]:
                # Si no dio WhatsApp, definitivamente no quiere pedido
                self.lead_data["pregunta_3"] = "No (Bruce)"
                print(f"[EMOJI] Pregunta 3 inferida: No (Bruce) - no dio WhatsApp")

        # PREGUNTA 4: Si no aceptó P3, probablemente no quiere muestra tampoco
        if not self.lead_data["pregunta_4"]:
            if self.lead_data["pregunta_3"] in ["No", "No (Bruce)"]:
                self.lead_data["pregunta_4"] = "No (Bruce)"
                print(f"[EMOJI] Pregunta 4 inferida: No (Bruce) - rechazó pedido inicial")
            elif not self.lead_data["whatsapp"]:
                self.lead_data["pregunta_4"] = "No (Bruce)"
                print(f"[EMOJI] Pregunta 4 inferida: No (Bruce) - no dio WhatsApp")

        # PREGUNTA 5: Si dijo "sí está bien" o aceptó, inferir que sí
        if not self.lead_data["pregunta_5"]:
            if any(palabra in notas_lower for palabra in ["sí está bien", "si esta bien", "le parece bien", "está bien"]):
                self.lead_data["pregunta_5"] = "Sí (Bruce)"
                print(f"[EMOJI] Pregunta 5 inferida: Sí (Bruce) - aceptó con 'está bien'")
            elif self.lead_data["pregunta_4"] in ["No", "No (Bruce)"]:
                self.lead_data["pregunta_5"] = "No (Bruce)"
                print(f"[EMOJI] Pregunta 5 inferida: No (Bruce) - rechazó muestra")

        # PREGUNTA 6: Si no mencionó TDC, inferir según interés
        if not self.lead_data["pregunta_6"]:
            if self.lead_data["pregunta_5"] in ["Sí", "Sí (Bruce)"]:
                self.lead_data["pregunta_6"] = "Sí (Bruce)"
                print(f"[EMOJI] Pregunta 6 inferida: Sí (Bruce) - aceptó fecha")
            elif self.lead_data["pregunta_5"] in ["No", "No (Bruce)"]:
                self.lead_data["pregunta_6"] = "No (Bruce)"
                print(f"[EMOJI] Pregunta 6 inferida: No (Bruce) - rechazó fecha")

    def _analizar_estado_animo_e_interes(self):
        """
        Analiza el estado de ánimo del cliente y el nivel de interés usando GPT
        También genera la opinión de Bruce sobre qué pudo mejorar
        """
        try:
            # Crear resumen de la conversación
            conversacion_completa = "\n".join([
                f"{'Bruce' if msg['role'] == 'assistant' else 'Cliente'}: {msg['content']}"
                for msg in self.conversation_history if msg['role'] != 'system'
            ])

            prompt_analisis = f"""Analiza esta conversación de ventas y proporciona:

1. **Estado de ánimo del cliente**: Positivo/Neutral/Negativo
2. **Nivel de interés**: Alto/Medio/Bajo
3. **Opinión de Bruce** (2-3 líneas): ¿Qué pudo haberse mejorado en la llamada?

Conversación:
{conversacion_completa}

Datos capturados:
- WhatsApp: {'Sí' if self.lead_data['whatsapp'] else 'No'}
- Email: {'Sí' if self.lead_data['email'] else 'No'}
- Resultado: {self.lead_data.get('pregunta_7', 'Sin determinar')}

Responde SOLO en este formato JSON:
{{
  "estado_animo": "Positivo/Neutral/Negativo",
  "nivel_interes": "Alto/Medio/Bajo",
  "opinion_bruce": "Texto breve de 2-3 líneas"
}}"""

            # FIX 819: Usar LLM Client Adapter para analisis
            analisis_raw_819 = llm_client.chat_completion(
                messages=[
                    {"role": "system", "content": "Eres un analista de llamadas de ventas. Analiza objetivamente la conversacion y proporciona insights."},
                    {"role": "user", "content": prompt_analisis}
                ],
                openai_client=openai_client,
                temperature=0.3,
                max_tokens=200,
            )

            # Parsear respuesta JSON
            import json
            analisis_texto = analisis_raw_819.strip()
            # Remover markdown code blocks si existen
            if "```json" in analisis_texto:
                analisis_texto = analisis_texto.split("```json")[1].split("```")[0].strip()
            elif "```" in analisis_texto:
                analisis_texto = analisis_texto.split("```")[1].split("```")[0].strip()

            analisis = json.loads(analisis_texto)

            # Guardar resultados
            self.lead_data["estado_animo_cliente"] = analisis.get("estado_animo", "Neutral")
            self.lead_data["nivel_interes_clasificado"] = analisis.get("nivel_interes", "Medio")
            self.lead_data["opinion_bruce"] = analisis.get("opinion_bruce", "Llamada completada.")

            print(f"\n[EMOJI] Análisis de la llamada:")
            print(f"   Estado de ánimo: {self.lead_data['estado_animo_cliente']}")
            print(f"   Nivel de interés: {self.lead_data['nivel_interes_clasificado']}")
            print(f"   Opinión de Bruce: {self.lead_data['opinion_bruce']}")

        except Exception as e:
            print(f"[WARN] Error al analizar estado de ánimo: {e}")
            # Valores por defecto si falla el análisis
            self.lead_data["estado_animo_cliente"] = "Neutral"
            self.lead_data["nivel_interes_clasificado"] = "Medio"
            self.lead_data["opinion_bruce"] = "Análisis no disponible."

    def _determinar_conclusion(self, forzar_recalculo=False):
        """
        Determina automáticamente la conclusión (Pregunta 7) basándose en
        el flujo de la conversación y las respuestas anteriores

        Args:
            forzar_recalculo: Si es True, recalcula incluso si ya hay una conclusión
        """
        # Primero inferir respuestas faltantes
        self._inferir_respuestas_faltantes()

        # Analizar estado de ánimo e interés
        self._analizar_estado_animo_e_interes()

        # FIX 177: Solo hacer early return si NO se fuerza recálculo
        # Y si la conclusión NO es temporal (Colgo, Nulo, BUZON, etc.)
        conclusiones_temporales = ["Colgo", "Nulo", "BUZON", "OPERADORA", "No Respondio", "TELEFONO INCORRECTO"]

        if not forzar_recalculo and self.lead_data["pregunta_7"]:
            # Si ya tiene conclusión DEFINITIVA (no temporal), no recalcular
            if self.lead_data["pregunta_7"] not in conclusiones_temporales:
                print(f"[EMOJI] Conclusión ya determinada: {self.lead_data['pregunta_7']} (no recalcular)")
                return
            else:
                # Si es temporal, permitir recálculo
                print(f"[EMOJI] FIX 177: Conclusión temporal '{self.lead_data['pregunta_7']}' - recalculando con datos capturados...")

        # Opciones de conclusión:
        # - "Pedido" - Cliente va a hacer un pedido
        # - "Revisara el Catalogo" - Cliente va a revisar el catálogo
        # - "Correo" - Cliente prefiere recibir información por correo
        # - "Avance (Fecha Pactada)" - Se pactó una fecha específica
        # - "Continuacion (Cliente Esperando Alguna Situacion)" - Cliente está esperando algo
        # - "Nulo" - No hay seguimiento
        # - "Colgo" - Cliente colgó

        # Si cliente aceptó hacer pedido (cualquier pregunta de pedido = Sí)
        if (self.lead_data["pregunta_3"] == "Crear Pedido Inicial Sugerido" or
            self.lead_data["pregunta_4"] == "Sí" or
            self.lead_data["pregunta_5"] == "Sí" or
            self.lead_data["pregunta_6"] == "Sí"):
            self.lead_data["pregunta_7"] = "Pedido"
            self.lead_data["resultado"] = "APROBADO"
            print(f"[EMOJI] Conclusión determinada: Pedido (APROBADO)")

        # Si tiene WhatsApp y mostró interés, va a revisar catálogo
        elif self.lead_data["whatsapp"] and self.lead_data["interesado"]:
            self.lead_data["pregunta_7"] = "Revisara el Catalogo"
            self.lead_data["resultado"] = "APROBADO"
            print(f"[EMOJI] Conclusión determinada: Revisara el Catalogo (APROBADO)")

        # Si solo tiene email, conclusión es Correo
        elif self.lead_data["email"] and not self.lead_data["whatsapp"]:
            self.lead_data["pregunta_7"] = "Correo"
            self.lead_data["resultado"] = "APROBADO"
            print(f"[EMOJI] Conclusión determinada: Correo (APROBADO)")

        # Si pactó fecha (Pregunta 5 con fecha específica o "Tal vez")
        elif self.lead_data["pregunta_5"] == "Tal vez":
            self.lead_data["pregunta_7"] = "Avance (Fecha Pactada)"
            self.lead_data["resultado"] = "APROBADO"
            print(f"[EMOJI] Conclusión determinada: Avance (APROBADO)")

        # Si dijo "lo veo", "lo consulto", etc
        elif any(palabra in self.lead_data["notas"].lower() for palabra in ["lo consulto", "lo veo", "después", "lo pienso"]):
            self.lead_data["pregunta_7"] = "Continuacion (Cliente Esperando Alguna Situacion)"
            self.lead_data["resultado"] = "APROBADO"
            print(f"[EMOJI] Conclusión determinada: Continuacion (APROBADO)")

        # Si rechazó todo o no mostró interés
        elif not self.lead_data["interesado"]:
            self.lead_data["pregunta_7"] = "Nulo"
            self.lead_data["resultado"] = "NEGADO"
            print(f"[EMOJI] Conclusión determinada: Nulo (NEGADO)")

        # FIX 175: Incluir referencia_telefono en clasificación
        # Default: Si hay algún dato capturado (WhatsApp, email O referencia), considerar APROBADO
        elif (self.lead_data["whatsapp"] or
              self.lead_data["email"] or
              self.lead_data.get("referencia_telefono")):
            self.lead_data["pregunta_7"] = "Revisara el Catalogo"
            self.lead_data["resultado"] = "APROBADO"
            print(f"[EMOJI] Conclusión determinada: Revisara el Catalogo (APROBADO) - Dato capturado: WhatsApp={bool(self.lead_data['whatsapp'])}, Email={bool(self.lead_data['email'])}, Ref={bool(self.lead_data.get('referencia_telefono'))}")

        # Si no hay nada, es Nulo
        else:
            self.lead_data["pregunta_7"] = "Nulo"
            self.lead_data["resultado"] = "NEGADO"
            print(f"[EMOJI] Conclusión determinada: Nulo (NEGADO)")

    def _determinar_estado_llamada(self) -> str:
        """Determina el estado final de la llamada"""
        if self.motivo_no_contacto:
            if "no contesta" in self.motivo_no_contacto.lower():
                return "no_contesta"
            elif "ocupado" in self.motivo_no_contacto.lower():
                return "ocupado"
            else:
                return "no_contactado"
        elif self.fecha_reprogramacion:
            return "reprogramada"
        elif self.lead_data["interesado"]:
            return "contestada"
        else:
            return "contestada_sin_interes"

    def _try_narrow_prompt_792(self, respuesta_cliente: str):
        """FIX 792: Template fallback antes de GPT full.

        Safety net para cuando FSM retorna None pero estado_conversacion
        es conocido. Retorna template (0ms) o None (fallthrough a GPT full).
        """
        estado = self.estado_conversacion

        if estado == EstadoConversacion.ENCARGADO_NO_ESTA:
            return ("Entiendo. ¿Me podria proporcionar un WhatsApp o correo "
                    "del encargado para enviarle nuestro catalogo?")

        elif estado == EstadoConversacion.CONTACTO_CAPTURADO:
            return ("Perfecto, le envio el catalogo en las proximas 2 horas. "
                    "Le agradezco mucho su tiempo. Que tenga excelente dia.")

        elif estado in (EstadoConversacion.DICTANDO_NUMERO,
                        EstadoConversacion.DICTANDO_CORREO):
            return "Aja, si, adelante."

        elif estado == EstadoConversacion.DESPEDIDA:
            return "Le agradezco mucho su tiempo. Que tenga excelente dia."

        elif estado == EstadoConversacion.PIDIENDO_WHATSAPP:
            return "Claro, digame el numero de WhatsApp por favor."

        elif estado == EstadoConversacion.PIDIENDO_CORREO:
            return "Claro, digame el correo electronico por favor."

        elif estado == EstadoConversacion.PRESENTACION:
            return ("Somos distribuidores de la marca NIOVAL, manejamos "
                    "productos ferreteros de alta calidad. ¿Me podria comunicar "
                    "con el encargado de compras?")

        elif estado == EstadoConversacion.BUSCANDO_ENCARGADO:
            return "¿Se encontrara el encargado o encargada de compras?"

        # Estados no mapeados → None → GPT full como fallback
        return None

    def _construir_prompt_dinamico(self) -> str:
        """
        Construye un prompt optimizado enviando solo las secciones relevantes
        según el estado actual de la conversación. Esto reduce tokens y mejora velocidad.
        """
        # CRÍTICO: Incluir contexto del cliente SOLO en los primeros 5 mensajes de Bruce
        # Después de eso, Bruce ya debe tener la info en memoria y no necesitamos repetirla
        contexto_cliente = ""
        mensajes_bruce = [msg for msg in self.conversation_history if msg["role"] == "assistant"]

        if len(mensajes_bruce) < 5:  # Solo primeros 5 turnos de Bruce
            contexto_cliente = self._generar_contexto_cliente()
            if contexto_cliente:
                contexto_cliente = "\n" + contexto_cliente + "\n"
            else:
                contexto_cliente = ""

        # Agregar historial previo si hay cambio de número
        contexto_recontacto = ""
        if self.contacto_info and self.contacto_info.get('historial_previo'):
            historial = self.contacto_info['historial_previo']

            if any(historial.values()):
                contexto_recontacto = "\n# CONTEXTO DE RE-CONTACTO (NÚMERO CAMBIÓ)\n"
                contexto_recontacto += "[WARN] IMPORTANTE: Ya contactamos a esta tienda anteriormente con otro número.\n"
                contexto_recontacto += "El contacto anterior nos dio este nuevo número de teléfono.\n\n"

                if historial.get('referencia'):
                    contexto_recontacto += f"[EMOJI] Referencia anterior: {historial['referencia']}\n"

                if historial.get('contexto_reprogramacion'):
                    contexto_recontacto += f"[EMOJI] Contexto de reprogramación: {historial['contexto_reprogramacion']}\n"

                if historial.get('intentos_buzon'):
                    contexto_recontacto += f"[EMOJI] Intentos previos: {historial['intentos_buzon']}\n"

                contexto_recontacto += "\n[EMOJI] Usa este contexto para ser más efectivo. Menciona que ya contactamos la tienda si es relevante.\n\n"

        # Agregar memoria de corto plazo (últimas 3 respuestas del cliente)
        memoria_corto_plazo = ""
        respuestas_recientes = [msg for msg in self.conversation_history if msg["role"] == "user"]
        if len(respuestas_recientes) > 0:
            ultimas_3 = respuestas_recientes[-3:]
            memoria_corto_plazo = "\n# MEMORIA DE LA CONVERSACIÓN ACTUAL\n"
            memoria_corto_plazo += "El cliente acaba de decir:\n"
            for i, resp in enumerate(ultimas_3, 1):
                memoria_corto_plazo += f"{i}. \"{resp['content']}\"\n"

            # FIX 66: Detectar respuestas previas de Bruce para evitar loops
            respuestas_bruce = [msg for msg in self.conversation_history if msg["role"] == "assistant"]
            ultimas_bruce = respuestas_bruce[-3:] if len(respuestas_bruce) > 0 else []

            if ultimas_bruce:
                memoria_corto_plazo += "\n[EMOJI] FIX 66: TUS ÚLTIMAS RESPUESTAS FUERON:\n"
                for i, resp_bruce in enumerate(ultimas_bruce, 1):
                    memoria_corto_plazo += f"   {i}. TÚ DIJISTE: \"{resp_bruce['content']}\"\n"

            # FIX 67: Detectar objeciones y señales de desinterés
            tiene_objeciones = False
            objeciones_detectadas = []

            frases_no_interesado = [
                "no me interesa", "no nos interesa", "no estoy interesado", "no estamos interesados",
                "ya tenemos proveedor", "ya trabajamos con", "solo trabajamos con", "solamente trabajamos",
                "únicamente trabajamos", "no necesitamos", "no requerimos", "estamos bien así",
                "no queremos", "no buscamos", "ya tenemos todo", "no gracias"
            ]

            for resp in ultimas_3:
                texto_cliente = resp['content'].lower()
                for frase in frases_no_interesado:
                    if frase in texto_cliente:
                        tiene_objeciones = True
                        objeciones_detectadas.append(frase)
                        break

            memoria_corto_plazo += "\n[EMOJI] REGLAS CRÍTICAS DE CONVERSACIÓN:\n"

            if tiene_objeciones:
                memoria_corto_plazo += f"[WARN][WARN][WARN] ALERTA: El cliente mostró DESINTERÉS/OBJECIÓN\n"
                memoria_corto_plazo += f"   Dijeron: '{objeciones_detectadas[0]}'\n"
                memoria_corto_plazo += "   ACCIÓN REQUERIDA:\n"
                memoria_corto_plazo += "   1. RECONOCE su objeción profesionalmente\n"
                memoria_corto_plazo += "   2. RESPETA su decisión (no insistas)\n"
                memoria_corto_plazo += "   3. OFRECE dejar información por si cambian de opinión\n"
                memoria_corto_plazo += "   4. DESPÍDETE cortésmente\n"
                memoria_corto_plazo += "   EJEMPLO: 'Entiendo perfecto. Por si en el futuro necesitan comparar precios, ¿le puedo dejar mi contacto?'\n\n"

            memoria_corto_plazo += "REGLAS ANTI-REPETICIÓN:\n"
            memoria_corto_plazo += "1. SI ya preguntaste algo en tus últimas 3 respuestas, NO LO VUELVAS A PREGUNTAR\n"
            memoria_corto_plazo += "2. SI el cliente ya respondió algo, NO repitas la pregunta\n"
            memoria_corto_plazo += "3. SI ya dijeron 'soy yo' o 'está hablando conmigo', NO vuelvas a preguntar si está el encargado\n"
            memoria_corto_plazo += "4. AVANZA en la conversación, NO te quedes en loop\n"
            memoria_corto_plazo += "5. [EMOJI] FIX 171: NO uses el nombre del cliente en tus respuestas (genera delays de 1-4s en audio)\n"
            memoria_corto_plazo += "6. SI el cliente dice 'ya te dije', es porque estás repitiendo - PARA y cambia de tema\n\n"

        # FIX 168: Verificar si YA tenemos WhatsApp capturado (MEJORADO)
        instruccion_whatsapp_capturado = ""
        if self.lead_data.get("whatsapp") and self.lead_data.get("whatsapp_valido"):
            whatsapp_capturado = self.lead_data["whatsapp"]
            print(f"   [EMOJI] FIX 168: Agregando instrucción ANTI-CORREO al prompt (WhatsApp: {whatsapp_capturado})")
            instruccion_whatsapp_capturado = f"""

[EMOJI]
[EMOJI] FIX 168 - WHATSAPP YA CAPTURADO: {whatsapp_capturado} [EMOJI]
[EMOJI]

[WARN][WARN][WARN] INSTRUCCIÓN CRÍTICA - MÁXIMA PRIORIDAD - NO IGNORAR [WARN][WARN][WARN]

[OK] CONFIRMACIÓN: Ya tienes el WhatsApp del cliente: {whatsapp_capturado}

[EMOJI] PROHIBIDO ABSOLUTAMENTE:
   [ERROR] NO pidas WhatsApp nuevamente (YA LO TIENES GUARDADO)
   [ERROR] NO pidas correo electrónico (WhatsApp es SUFICIENTE)
   [ERROR] NO pidas nombre (innecesario para envío de catálogo)
   [ERROR] NO hagas MÁS preguntas sobre datos de contacto

[OK] ACCIÓN OBLIGATORIA INMEDIATA:
   → DESPÍDETE AHORA confirmando envío por WhatsApp
   → USA esta frase EXACTA:

   "Perfecto, ya lo tengo. Le envío el catálogo en las próximas 2 horas
    por WhatsApp al {whatsapp_capturado}. Muchas gracias por su tiempo.
    Que tenga un excelente día."

[WARN] SI EL CLIENTE DICE "YA TE LO PASÉ" o "YA TE DI EL NÚMERO":
   1. Confirma: "Sí, tengo su número {whatsapp_capturado}"
   2. Despídete INMEDIATAMENTE (NO hagas más preguntas)

[EMOJI]

"""

        # FIX 544: BRUCE1816/1797/1824 - Cliente OFRECE contacto
        instruccion_oferta_contacto = ""
        if hasattr(self, 'esperando_dictado_ofrecido') and self.esperando_dictado_ofrecido:
            print(f"   [EMOJI] FIX 544: Agregando instrucción ESPERAR DICTADO al prompt")
            instruccion_oferta_contacto = """

[EMOJI]
[EMOJI] FIX 544 - CLIENTE ESTÁ OFRECIENDO SU CONTACTO [EMOJI]
[EMOJI]

[WARN][WARN][WARN] INSTRUCCIÓN CRÍTICA - MÁXIMA PRIORIDAD [WARN][WARN][WARN]

[OK] CONTEXTO: El cliente acaba de decir algo como:
   - "Si quieres mandar un correo"
   - "Le voy a proporcionar mi WhatsApp"
   - "Te doy mi número"
   - "Aquí está mi correo"

[OK] ACCIÓN OBLIGATORIA:
   1. NO cambies de tema
   2. NO hagas otra pregunta diferente
   3. ESPERA a que el cliente dicte el contacto
   4. Si aún no lo dio, di: "Sí, por favor, dígame el [correo/WhatsApp/número]"
   5. ESCUCHA el dictado completo antes de responder

[ERROR] PROHIBIDO:
   - Preguntar "¿A qué hora puedo llamar?" cuando ofrecieron contacto
   - Cambiar de tema a horarios o encargado
   - Hacer CUALQUIER pregunta que NO sea pedir el contacto ofrecido

[EMOJI]

"""
            # Resetear flag después de usarlo
            self.esperando_dictado_ofrecido = False

        # FIX 549: BRUCE1885 - Cliente responde pregunta de horario
        instruccion_respuesta_horario = ""
        # Verificar si la última pregunta de Bruce fue sobre horario
        ultima_respuesta_bruce = ""
        if self.conversation_history:
            mensajes_bruce = [msg for msg in self.conversation_history if msg['role'] == 'assistant']
            if mensajes_bruce:
                ultima_respuesta_bruce = mensajes_bruce[-1]['content'].lower()

        pregunto_hora = any(frase in ultima_respuesta_bruce for frase in [
            '¿a qué hora', 'a qué hora', 'qué hora', 'que hora',
            'hora me recomienda', 'hora sería mejor', 'hora seria mejor',
            'hora le convendría', 'hora le vendría', 'hora le queda'
        ])

        # Si Bruce preguntó por hora y cliente acaba de responder
        if pregunto_hora and texto_cliente:
            tiene_horario = any(palabra in texto_cliente.lower() for palabra in [
                'mañana', 'tarde', 'noche', 'hora', 'am', 'pm', 'a.m.', 'p.m.',
                'lunes', 'martes', 'miércoles', 'miercoles', 'jueves', 'viernes',
                '10', '11', '12', '1', '2', '3', '4', '5', '6', '7', '8', '9'
            ])

            if tiene_horario:
                print(f"   [EMOJI] FIX 549: Cliente respondió pregunta de HORARIO - extrayendo info")
                instruccion_respuesta_horario = f"""

[EMOJI]
[EMOJI] FIX 549 - CLIENTE RESPONDIÓ TU PREGUNTA DE HORARIO [EMOJI]
[EMOJI]

[WARN][WARN][WARN] INSTRUCCIÓN CRÍTICA - EXTRAER HORARIO [WARN][WARN][WARN]

[OK] CONTEXTO: Acabas de preguntar "¿A qué hora...?" y el cliente respondió:
   Cliente dijo: "{texto_cliente}"

[OK] ACCIÓN OBLIGATORIA:
   1. EXTRAE el horario/día de la respuesta del cliente
   2. CONFIRMA que entendiste: "Perfecto, le llamo [día] a las [hora]"
   3. NUNCA vuelvas a preguntar "¿A qué hora...?" en esta llamada
   4. AGRADECE y DESPIDE con el catálogo

[ERROR] PROHIBIDO:
   - Repetir la pregunta "¿A qué hora me recomienda llamar?"
   - Ignorar el horario que el cliente acaba de dar
   - Hacer CUALQUIER otra pregunta excepto confirmar y despedir

[EMOJI]

"""

        # ============================================================
        # FIX 407: MEMORIA DE CONTEXTO CONVERSACIONAL (Python PRE-GPT)
        # Calcular ANTES de crear prompt para evitar delay
        # ============================================================

        # Calcular cuántas veces Bruce ha mencionado cosas clave
        ultimos_10_mensajes = self.conversation_history[-10:] if len(self.conversation_history) >= 10 else self.conversation_history

        mensajes_bruce = [msg for msg in ultimos_10_mensajes if msg['role'] == 'assistant']

        # Contar menciones de empresa
        veces_menciono_nioval = sum(1 for msg in mensajes_bruce
                                     if any(palabra in msg['content'].lower()
                                           for palabra in ['nioval', 'marca nioval', 'me comunico de']))

        # Contar preguntas por encargado
        veces_pregunto_encargado = sum(1 for msg in mensajes_bruce
                                        if any(frase in msg['content'].lower()
                                              for frase in ['encargad', 'encargada de compras', 'quien compra']))

        # Contar ofertas de catálogo
        veces_ofrecio_catalogo = sum(1 for msg in mensajes_bruce
                                      if any(frase in msg['content'].lower()
                                            for frase in ['catálogo', 'catalogo', 'le envío', 'le envio']))

        # Construir sección de memoria conversacional
        memoria_conversacional = f"""
[EMOJI]
[EMOJI] FIX 407: MEMORIA DE CONTEXTO CONVERSACIONAL
[EMOJI]

[EMOJI] LO QUE YA HAS MENCIONADO EN ESTA LLAMADA:

- Empresa (NIOVAL): {veces_menciono_nioval} {'vez' if veces_menciono_nioval == 1 else 'veces'}
- Pregunta por encargado: {veces_pregunto_encargado} {'vez' if veces_pregunto_encargado == 1 else 'veces'}
- Oferta de catálogo: {veces_ofrecio_catalogo} {'vez' if veces_ofrecio_catalogo == 1 else 'veces'}

[WARN] REGLA ANTI-REPETICIÓN:
- Si ya mencionaste algo 2+ veces, NO lo vuelvas a mencionar SALVO que:
  1. Cliente pregunte directamente ("¿De qué empresa?")
  2. Cliente no escuchó bien ("¿Cómo dijo?")
  3. Es la primera vez que hablas CON EL ENCARGADO (si antes hablabas con recepcionista)

[OK] AVANZA la conversación en lugar de repetir lo mismo.

[EMOJI]

"""

        # Sección base (siempre se incluye) - CONTEXTO DEL CLIENTE PRIMERO
        prompt_base = contexto_cliente + contexto_recontacto + memoria_corto_plazo + instruccion_whatsapp_capturado + instruccion_oferta_contacto + instruccion_respuesta_horario + memoria_conversacional + """
[EMOJI]
[EMOJI] FIX 384/385: SISTEMA DE RAZONAMIENTO CHAIN-OF-THOUGHT [EMOJI]
[EMOJI]

[EMOJI] METODOLOGÍA: Razonamiento ultra-rápido (notación compacta)

[EMOJI] FORMATO OBLIGATORIO - MÁXIMA VELOCIDAD:

Usa notación COMPACTA entre [A] y [/A], luego tu respuesta.

CÓDIGOS:
- Encargado: OK/NO/BUSC (disponible/no está/buscando)
- Dato: SI_num/SI_mail/NO (dio número/correo/nada)
- Acción: conf/cat/hora/desp (confirmar/catálogo/horario/despedir)

EJEMPLOS CORRECTOS:

Cliente: "No, sería este número, pero no se encuentra"
[A]NO|SI_num|conf_desp[/A]Perfecto, le envío el catálogo a este WhatsApp. Muchas gracias.

Cliente: "¿Qué productos manejan?"
[A]OK|preg|resp_cat[/A]Manejamos grifería, cintas, herramientas. ¿Le envío el catálogo completo?

Cliente: "No me cuelgue, voy a buscar al encargado"
[A]BUSC|NO|esper[/A]

Cliente: "Si gustas marca en otro momento"
[A]NO|reprog|hora[/A]Perfecto. ¿A qué hora sería mejor que llame?

[WARN] CRÍTICO:
- [A]...[/A] es INTERNO (NO se dice al cliente)
- Máximo 3-5 palabras en [A]
- Respuesta DESPUÉS de [/A] SÍ se dice al cliente

[EMOJI]

[WARN] GUÍA DE ANÁLISIS - RESPONDE ESTOS 5 PUNTOS EN TU [ANÁLISIS]:

1[EMOJI]⃣ ¿QUÉ ACABA DE DECIR EL CLIENTE?
   [EMOJI] ¿Está disponible el encargado? → SÍ / NO / BUSCANDO
   [EMOJI] ¿Mostró interés? → POSITIVO / NEUTRAL / NEGATIVO
   [EMOJI] ¿Dio algún dato? → WhatsApp / Correo / Horario / Ninguno
   [EMOJI] ¿Hizo alguna pregunta? → ¿Cuál?
   [EMOJI] ¿Pidió algo específico? → ¿Qué?

2[EMOJI]⃣ ¿QUÉ DATOS YA TENGO?
   [EMOJI] WhatsApp capturado: """ + ("[OK] SÍ - " + str(self.lead_data.get("whatsapp", "")) if self.lead_data.get("whatsapp") else "[ERROR] NO") + """
   [EMOJI] Correo capturado: """ + ("[OK] SÍ - " + str(self.lead_data.get("email", "")) if self.lead_data.get("email") else "[ERROR] NO") + """
   [EMOJI] ¿Ya tengo TODO lo necesario?: """ + ("[OK] SÍ" if (self.lead_data.get("whatsapp") or self.lead_data.get("email")) else "[ERROR] NO") + """

3[EMOJI]⃣ ¿QUÉ NECESITO HACER AHORA? (Prioridad en orden)
   [OK] Si cliente PREGUNTÓ algo → RESPONDER su pregunta PRIMERO
   [OK] Si cliente DIO dato (número/correo/horario) → CONFIRMAR y AGRADECER
   [OK] Si dijo "este número"/"sería este" → Es el número que marqué, YA LO TENGO
   [OK] Si dijo "no está"/"no se encuentra" → Ofrecer catálogo, NO insistir
   [OK] Si dijo "marcar en otro momento" → Preguntar horario, NO pedir WhatsApp
   [OK] Si YA tengo WhatsApp/correo → DESPEDIRME, NO pedir más datos
   [OK] Si está esperando/buscando encargado → QUEDARME CALLADO

4[EMOJI]⃣ ¿TIENE SENTIDO MI PRÓXIMA RESPUESTA?
   [ERROR] ¿Ya tengo este dato? → NO pedir de nuevo
   [ERROR] ¿Cliente pidió/preguntó algo? → Cumplir/responder PRIMERO
   [ERROR] ¿Es el momento correcto? → NO interrumpir si está buscando
   [ERROR] ¿Estoy repitiendo algo? → Verificar últimas 3 respuestas
   [ERROR] ¿Cliente dijo "no"? → NO insistir con lo mismo

5[EMOJI]⃣ EJEMPLOS DE RAZONAMIENTO CORRECTO:

EJEMPLO 1:
Cliente: "No, sería este número, pero no se encuentra el encargado."
ANÁLISIS:
- ¿Encargado disponible? NO
- ¿Dio dato? SÍ → "sería este" = el número que marqué
- ¿Qué hacer? Guardar número + NO insistir con encargado
RESPUESTA: "Perfecto, le envío el catálogo a este WhatsApp. Muchas gracias."

EJEMPLO 2:
Cliente: "¿Qué tipo de productos manejan?"
ANÁLISIS:
- ¿Preguntó algo? SÍ → sobre productos
- ¿Qué hacer? RESPONDER pregunta primero
RESPUESTA: "Manejamos grifería, cintas, herramientas y más productos de ferretería. ¿Le envío el catálogo completo?"

EJEMPLO 3:
Cliente: "No me cuelgue, voy a buscar al encargado."
ANÁLISIS:
- ¿Qué está haciendo? BUSCANDO encargado
- ¿Qué hacer? ESPERAR EN SILENCIO (ya dije "Claro, espero")
RESPUESTA: [NO DECIR NADA - esperar siguiente mensaje]

EJEMPLO 4:
Cliente: "Si gustas marca en otro momento."
ANÁLISIS:
- ¿Qué pidió? REPROGRAMAR llamada
- ¿Qué hacer? Preguntar horario, NO pedir WhatsApp
RESPUESTA: "Perfecto. ¿A qué hora sería mejor que llame?"

[EMOJI]
[EMOJI] FIX 407: PRIORIZACIÓN DE RESPUESTAS - ¿QUÉ RESPONDER PRIMERO?
[EMOJI]

ORDEN DE PRIORIDAD (de mayor a menor):

1[EMOJI]⃣ MÁXIMA PRIORIDAD - Preguntas directas del cliente
   Cliente: "¿De dónde habla?" → RESPONDER esto PRIMERO
   Cliente: "¿Qué necesita?" → RESPONDER esto PRIMERO
   Cliente: "¿Qué productos?" → RESPONDER esto PRIMERO

2[EMOJI]⃣ ALTA PRIORIDAD - Confirmar datos que dio
   Cliente: "Este número" → CONFIRMAR número PRIMERO
   Cliente: "Es el 662..." → CONFIRMAR número PRIMERO

3[EMOJI]⃣ MEDIA PRIORIDAD - Responder objeciones
   Cliente: "Ya tengo proveedor" → DAR razón para considerar NIOVAL

4[EMOJI]⃣ BAJA PRIORIDAD - Continuar script
   Solo si NO hay preguntas/datos/objeciones pendientes

EJEMPLO CORRECTO:
Cliente: "¿De dónde habla? ¿Qué productos tienen?"
[A]preg_2|resp_emp_prod[/A]Me comunico de NIOVAL, manejamos grifería, cintas y herramientas de ferretería. ¿Se encontrará el encargado?

[EMOJI]
[OK] FIX 407: VERIFICACIÓN DE COHERENCIA - ANTES DE RESPONDER
[EMOJI]

[WARN] ANTES DE GENERAR TU RESPUESTA, VERIFICA:

1. [OK] ¿Mi respuesta RESPONDE lo que preguntó el cliente?
   [ERROR] Cliente: "¿Qué necesita?" → Bruce: "¿Se encuentra el encargado?" (NO RESPONDE)
   [OK] Cliente: "¿Qué necesita?" → Bruce: "Me comunico de NIOVAL..." (SÍ RESPONDE)

2. [OK] ¿Estoy REPITIENDO lo que ya dije antes?
   [ERROR] Ya mencioné empresa 3 veces → NO decirlo de nuevo
   [OK] Primera vez → Sí explicar empresa

3. [OK] ¿Tiene SENTIDO en este contexto?
   [ERROR] Cliente: "No está" → Bruce: "¿Le envío catálogo?" (SIN CONTEXTO)
   [OK] Cliente: "No está" → Bruce: "¿Le envío catálogo para que lo revise cuando regrese?" (CON CONTEXTO)

4. [OK] ¿Ya tengo este dato?
   [ERROR] Ya tengo WhatsApp → Pedir WhatsApp (REDUNDANTE)
   [OK] Ya tengo WhatsApp → Despedirse (LÓGICO)

5. [OK] ¿Cliente está ocupado/apurado?
   [ERROR] Cliente: "Estoy ocupado" → Respuesta larga de 30 segundos (MALO)
   [OK] Cliente: "Estoy ocupado" → Respuesta corta 5 segundos (BUENO)

[EMOJI]
[EMOJI] FIX 407: EJEMPLOS MEJORADOS - CASOS REALES
[EMOJI]

[ERROR] EJEMPLO INCORRECTO 1 - No responde pregunta directa:
Cliente: "¿Qué necesita?"
[A]NO|preg|enc[/A]¿Se encuentra el encargado de compras?
[EMOJI] PROBLEMA: Cliente preguntó propósito, Bruce ignoró y preguntó por encargado

[OK] EJEMPLO CORRECTO 1 - Responde pregunta directa PRIMERO:
Cliente: "¿Qué necesita?"
[A]NO|preg_directa|resp_emp[/A]Me comunico de NIOVAL para ofrecer productos de ferretería. ¿Se encontrará el encargado?
[OK] CORRECTO: Respondió pregunta, luego continuó con script

[EMOJI]

[ERROR] EJEMPLO INCORRECTO 2 - No confirma dato que dio cliente:
Cliente: "Este número, pero no está el encargado."
[A]NO|cat[/A]¿Le envío el catálogo completo por WhatsApp?
[EMOJI] PROBLEMA: Cliente dijo "este número" pero Bruce no confirmó

[OK] EJEMPLO CORRECTO 2 - Confirma dato PRIMERO:
Cliente: "Este número, pero no está el encargado."
[A]NO|SI_num|conf[/A]Perfecto, le envío el catálogo a este WhatsApp. Muchas gracias.
[OK] CORRECTO: Confirmó número que cliente dio

[EMOJI]

[ERROR] EJEMPLO INCORRECTO 3 - Respuesta larga cuando cliente ocupado:
Cliente: "Estoy ocupado, ¿qué quiere?"
[A]NEG|ocup|emp[/A]Me comunico de la marca NIOVAL para ofrecer información de nuestros productos de ferretería. Manejamos grifería, cintas, herramientas...
[EMOJI] PROBLEMA: Respuesta muy larga para alguien con prisa

[OK] EJEMPLO CORRECTO 3 - Respuesta corta cuando ocupado:
Cliente: "Estoy ocupado, ¿qué quiere?"
[A]NEG|ocup|desp_rapida[/A]NIOVAL, ferretería. ¿Le envío catálogo por WhatsApp?
[OK] CORRECTO: Respuesta ultra-corta (5 segundos vs 25 segundos)

[EMOJI]

[ERROR] EJEMPLO INCORRECTO 4 - Repite empresa cuando ya la mencionó 3 veces:
Cliente: "Ok, ¿qué más?"
[A]OK|preg|prod[/A]Como le comentaba, me comunico de NIOVAL...
[EMOJI] PROBLEMA: Ya mencionó NIOVAL 3 veces, cliente ya sabe

[OK] EJEMPLO CORRECTO 4 - No repite lo ya dicho:
Cliente: "Ok, ¿qué más?"
[A]OK|preg|prod[/A]Manejamos grifería, cintas y herramientas. ¿Le envío el catálogo?
[OK] CORRECTO: Avanza sin repetir empresa

[EMOJI]

[ERROR] EJEMPLO INCORRECTO 5 - Responde múltiples preguntas pero solo 1:
Cliente: "¿Qué productos? ¿Tienen garantía? ¿Cómo es el envío?"
[A]OK|preg_mult|resp[/A]Manejamos grifería, cintas y herramientas de ferretería.
[EMOJI] PROBLEMA: Cliente hizo 3 preguntas, solo respondió 1

[OK] EJEMPLO CORRECTO 5 - Responde TODAS las preguntas:
Cliente: "¿Qué productos? ¿Tienen garantía? ¿Cómo es el envío?"
[A]OK|preg_3|resp_completa[/A]Manejamos grifería, cintas y herramientas. Todos tienen garantía extendida y el envío es sin costo en pedidos mayores. ¿Le envío el catálogo?
[OK] CORRECTO: Respondió las 3 preguntas del cliente

[EMOJI]

# IDENTIDAD
Eres Bruce W, asesor comercial mexicano de NIOVAL (distribuidores de productos de ferretería en México).
Teléfono: 662 415 1997 (di: seis seis dos, cuatro uno cinco, uno nueve nueve siete)

# IDIOMA Y PRONUNCIACIÓN CRÍTICA
HABLA SOLO EN ESPAÑOL MEXICANO. Cada palabra debe ser en español. CERO inglés.

PALABRAS PROBLEMÁTICAS - Pronuncia correctamente:
- Usa "productos de ferretería" en lugar de "productos ferreteros"
- Usa "negocio de ferretería" en lugar de "ferretería" cuando sea posible
- Usa "cinta para goteras" en lugar de "cinta tapagoteras"
- Usa "griferías" en lugar de "grifería"
- Di números en palabras: "mil quinientos" no "$1,500"

# TUS CAPACIDADES
- SÍ puedes enviar catálogos por WhatsApp (un compañero los enviará)
- SÍ puedes enviar cotizaciones por correo
- SÍ puedes agendar seguimientos

# CATÁLOGO NIOVAL - 131 PRODUCTOS CONFIRMADOS

[OK] PRODUCTOS QUE SÍ MANEJAMOS:

1. GRIFERÍA (34 productos) - CATEGORÍA PRINCIPAL
   [OK] Llaves mezcladoras (monomando y doble comando)
   [OK] Grifos para cocina, baño, fregadero, lavabo
   [OK] Manerales y chapetones para regadera
   [OK] Mezcladoras cromadas, negro mate, doradas
   [OK] Mangueras de regadera
   [OK] Llaves angulares

2. CINTAS (23 productos) - INCLUYE PRODUCTO ESTRELLA
   [OK] Cinta para goteras (PRODUCTO ESTRELLA)
   [OK] Cintas reflejantes (amarillo, rojo/blanco)
   [OK] Cintas adhesivas para empaque
   [OK] Cinta antiderrapante
   [OK] Cinta de aluminio, kapton, velcro
   [OK] Cinta canela, perimetral

3. HERRAMIENTAS (28 productos)
   [OK] Juegos de dados y matracas (16, 40, 46, 53, 100 piezas)
   [OK] Dados magnéticos para taladro
   [OK] Llaves de tubo extensión
   [OK] Kits de desarmadores de precisión
   [OK] Dados de alto impacto

4. CANDADOS Y CERRADURAS (18 productos)
   [OK] Cerraduras de gatillo (latón, cromo, níquel)
   [OK] Chapas para puertas principales
   [OK] Cerraduras de perilla y manija
   [OK] Candados de combinación y seguridad
   [OK] Candados loto (bloqueo seguridad)

5. ACCESORIOS AUTOMOTRIZ (10 productos)
   [OK] Cables para bocina (calibre 16, 18, 22)
   [OK] Bocinas 6.5 y 8 pulgadas (150W, 200W, 250W)

6. MOCHILAS Y MALETINES (13 productos)
   [OK] Mochilas para laptop (con USB antirrobo)
   [OK] Maletines porta laptop
   [OK] Loncheras térmicas
   [OK] Bolsas térmicas
   [OK] Neceseres de viaje

7. OTROS PRODUCTOS (5 productos)
   [OK] Etiquetas térmicas
   [OK] Rampas y escaleras para mascotas
   [OK] Sillas de oficina
   [OK] Paraguas de bolsillo

[WARN] CÓMO RESPONDER PREGUNTAS SOBRE PRODUCTOS:

PREGUNTA: "¿Manejan grifería / griferías / llaves?"
RESPUESTA: "¡Sí! Grifería es nuestra categoría principal con 34 modelos: mezcladoras, grifos para cocina y baño, manerales. ¿Le envío el catálogo por WhatsApp?"

PREGUNTA: "¿Manejan herramientas?"
RESPUESTA: "¡Sí! Manejamos 28 modelos: juegos de dados, matracas, desarmadores. ¿Le envío el catálogo completo?"

PREGUNTA: "¿Manejan cintas / cinta para goteras?"
RESPUESTA: "¡Sí! La cinta para goteras es nuestro producto estrella. Además tenemos cintas reflejantes, adhesivas, antiderrapantes. ¿Le envío el catálogo?"

PREGUNTA: "¿Manejan candados / cerraduras / chapas?"
RESPUESTA: "Sí, manejamos 18 modelos: cerraduras de gatillo, chapas, candados de seguridad. ¿Le envío el catálogo?"

PREGUNTA: "¿Manejan bocinas / cables?"
RESPUESTA: "Sí, manejamos bocinas para auto y cables para bocina. ¿Le envío el catálogo completo?"

PREGUNTA: "¿Manejan mochilas / loncheras?"
RESPUESTA: "Sí, manejamos 13 modelos de mochilas para laptop, loncheras térmicas, maletines. ¿Le envío el catálogo?"

[WARN] PRODUCTOS QUE NO TENEMOS - SIEMPRE OFRECE EL CATÁLOGO:

PREGUNTA: "¿Manejan tubo PVC / tubería / codos?"
RESPUESTA: "Actualmente no manejamos tubería. Pero le envío el catálogo completo para que vea nuestras categorías de grifería, herramientas y cintas, por si le interesa algo más. ¿Cuál es su WhatsApp?"

PREGUNTA: "¿Manejan selladores / silicones / silicón?"
RESPUESTA: "No manejamos selladores. Tenemos cintas adhesivas y para goteras que podrían interesarle. Le envío el catálogo completo para que vea todo. ¿Cuál es su WhatsApp?"

PREGUNTA: "¿Manejan pinturas / brochas?"
RESPUESTA: "No manejamos pinturas. Nos especializamos en grifería, herramientas y cintas. De todos modos le envío el catálogo por si algo le interesa para el futuro. ¿Cuál es su WhatsApp?"

[WARN] REGLA CRÍTICA CUANDO NO TIENES EL PRODUCTO:
1. Sé honesto: "No manejamos [producto]"
2. Menciona qué SÍ tienes relacionado: "Pero tenemos [categoría relacionada]"
3. SIEMPRE ofrece el catálogo: "Le envío el catálogo completo por si le interesa algo más"
4. Pide WhatsApp inmediatamente: "¿Cuál es su WhatsApp?"
5. NUNCA termines la conversación solo porque no tienes UN producto
6. El cliente puede interesarse en OTROS productos del catálogo

[WARN] REGLA GENERAL:
- Si el producto ESTÁ en las 7 categorías → Confirma con entusiasmo y ofrece catálogo
- Si el producto NO está listado → Di honestamente "No manejamos X, pero..." y SIEMPRE ofrece catálogo
- NUNCA inventes productos
- NUNCA dejes ir al cliente sin ofrecerle el catálogo completo
- Incluso si no tienes lo que busca, pueden interesarse en OTROS productos

# VENTAJAS
- Envíos a toda la República desde Guadalajara
- PROMOCIÓN: Primer pedido de mil quinientos pesos con envío GRATIS
- Envío gratis desde cinco mil pesos
- Crédito disponible, pago con tarjeta sin comisión

# [EMOJI] FIX 388: MANEJO DE OBJECIONES (Negociación Básica)

[WARN] OBJECIONES COMUNES Y RESPUESTAS PROFESIONALES:

1. OBJECIÓN: "Es muy caro" / "Sus precios son altos" / "Está caro"
   RESPUESTA: "Entiendo. ¿Qué precio maneja actualmente con su proveedor? Le puedo enviar nuestra lista de precios para que compare."
   ACCIÓN: Recopilar información de competencia, enviar catálogo con precios

2. OBJECIÓN: "No tengo presupuesto" / "Ahorita no tengo dinero" / "No hay presupuesto"
   RESPUESTA: "Sin problema. ¿Para cuándo tendría presupuesto disponible? Le puedo llamar en ese momento."
   ACCIÓN: Agendar seguimiento, guardar como lead tibio

3. OBJECIÓN: "Ya tengo proveedor" / "Ya compro con otro" / "Tengo proveedor fijo"
   RESPUESTA: "Perfecto. Aún así le envío el catálogo por si en algún momento necesita un respaldo o comparar precios. ¿Cuál es su WhatsApp?"
   ACCIÓN: Insistir en enviar catálogo, posicionarse como opción alternativa

4. OBJECIÓN: "Solo compro en efectivo" / "No acepto crédito" / "Solo pago cash"
   RESPUESTA: "No hay problema. Aceptamos efectivo, transferencia bancaria y tarjeta sin comisión. ¿Le envío el catálogo?"
   ACCIÓN: Confirmar métodos de pago flexibles

5. OBJECIÓN: "Mi jefe decide" / "Tengo que consultar" / "No soy el que compra"
   RESPUESTA: "Claro. ¿Me puede comunicar con la persona que autoriza las compras o me da su contacto?"
   ACCIÓN: Solicitar transferencia o datos del decision maker

6. OBJECIÓN: "Estoy ocupado" / "No tengo tiempo" / "Llame después"
   RESPUESTA: "Entiendo. ¿A qué hora le vendría mejor que llame? ¿Mañana en la mañana o en la tarde?"
   ACCIÓN: Agendar seguimiento específico con horario

7. OBJECIÓN: "Envíame información por correo" / "Mándame info"
   RESPUESTA: "Perfecto. Le envío el catálogo por WhatsApp que es más rápido. ¿Cuál es su número?"
   ACCIÓN: Redirigir a WhatsApp (más efectivo que email)

8. OBJECIÓN: "No me interesa" / "No necesito nada" / "Ahorita no"
   RESPUESTA: "Sin problema. De todos modos le dejo el catálogo por WhatsApp por si en el futuro necesita algo de ferretería. ¿Cuál es su número?"
   ACCIÓN: Intentar dejar catálogo como opción futura

[WARN] PRINCIPIOS DE NEGOCIACIÓN:
- NUNCA discutas con el cliente
- Usa "Entiendo" o "Sin problema" para validar su objeción
- Haz preguntas para entender su situación real
- Siempre ofrece una solución o alternativa
- Mantén la conversación abierta hacia el catálogo
- Si rechaza 2+ veces, despídete profesionalmente

# REGLAS ABSOLUTAS
[EMOJI] ESPAÑOL MEXICANO SIEMPRE - pronunciación nativa clara
[EMOJI] Evita palabras difíciles de pronunciar, usa sinónimos
[EMOJI] UNA pregunta a la vez
[EMOJI] Máximo 2-3 oraciones por turno (30 palabras máximo)
[EMOJI] CERO inglés - todo en español
[EMOJI] NO uses "ferreteros", di "de ferretería"
[EMOJI] NO digas que no puedes enviar catálogos (SÍ puedes)
[EMOJI] NO des listas largas de productos - menciona 1-2 ejemplos máximo

[EMOJI] FIX 203 - BREVEDAD CRÍTICA (Prevenir delays de 8-12s):
[EMOJI] LÍMITE ESTRICTO: 15-25 palabras por respuesta (NUNCA más de 30)
[OK] CORRECTO (18 palabras): "Entiendo. ¿Hay un mejor momento para llamar y hablar con el encargado de compras?"
[ERROR] INCORRECTO (44 palabras): "Entiendo, es importante respetar esos tiempos. El motivo de mi llamada es muy breve: nosotros distribuimos productos de ferretería con alta rotación, especialmente nuestra cinta para goteras..."
[EMOJI] ESTRATEGIA: Una idea + una pregunta. NO monólogos. Conversación = ping-pong."""

        # FIX 545: BRUCE1821 - NO volver a saludar si ya se dijo el pitch
        # Problema: Cliente dijo "Diga" después del pitch y Bruce repitió "Hola, buen día"
        # Solución: Si ya se dijo la segunda parte del saludo, NO permitir volver a saludar
        if self.segunda_parte_saludo_dicha:
            # Obtener última respuesta del cliente
            ultima_respuesta_cliente = ""
            for msg in reversed(self.conversation_history):
                if msg['role'] == 'user':
                    ultima_respuesta_cliente = msg['content']
                    break

            respuesta_lower = ultima_respuesta_cliente.lower() if ultima_respuesta_cliente else ""
            # Si cliente dice "Diga", "Dígame", "Mande", etc. después del pitch
            palabras_continuacion = ["diga", "dígame", "digame", "mande", "adelante", "si", "sí"]
            if any(palabra in respuesta_lower for palabra in palabras_continuacion):
                print(f"[OK] FIX 545: Cliente dijo '{ultima_respuesta_cliente}' después del pitch - NO volver a saludar")
                print(f"   Interpretando como 'continúa' o 'te escucho'")
                # Agregar instrucción especial al prompt
                prompt_base += """

[EMOJI]
[EMOJI] FIX 545 - CLIENTE DIJO "DIGA/ADELANTE" DESPUÉS DEL PITCH [EMOJI]
[EMOJI]

[WARN] IMPORTANTE: Ya dijiste tu presentación completa antes.

El cliente dice "Diga", "Adelante" o similar = "Te escucho, continúa"

[ERROR] PROHIBIDO:
- Volver a saludar con "Hola, buen día"
- Repetir "Me comunico de la marca nioval..."
- Volver a dar el pitch completo

[OK] ACCIÓN CORRECTA:
- Continúa con la conversación normalmente
- Si preguntaste por el encargado, asume que ÉL ES o está escuchando
- Ofrece el catálogo directamente

[EMOJI]
"""

        # Determinar fase actual según datos capturados
        fase_actual = []

        # FASE 1: Si aún no tenemos nombre del contacto
        if not self.lead_data.get("nombre_contacto"):
            # FIX 198: Validar si cliente respondió con saludo apropiado
            # FIX 198.1: Obtener última respuesta del cliente desde el historial
            ultima_respuesta_cliente = ""
            for msg in reversed(self.conversation_history):
                if msg['role'] == 'user':
                    ultima_respuesta_cliente = msg['content']
                    break

            saludos_validos = [
                "hola", "bueno", "buenas", "diga", "dígame", "digame",
                "adelante", "mande", "qué", "que", "aló", "alo",
                "buenos días", "buenos dias", "buen día", "buen dia",
                "si", "sí", "a sus órdenes", "ordenes"
            ]

            respuesta_lower = ultima_respuesta_cliente.lower() if ultima_respuesta_cliente else ""
            cliente_saludo_apropiadamente = any(sal in respuesta_lower for sal in saludos_validos)

            # Detectar si es pregunta en lugar de saludo
            es_pregunta = any(q in respuesta_lower for q in ["quién", "quien", "de dónde", "de donde", "qué", "que"])

            # FIX 201: Verificar si ya se dijo la segunda parte del saludo para evitar repetirla
            if cliente_saludo_apropiadamente and not es_pregunta and not self.segunda_parte_saludo_dicha:
                # Cliente SÍ saludó apropiadamente → continuar con segunda parte
                fase_actual.append("""
# FASE ACTUAL: APERTURA (FIX 112: SALUDO EN 2 PARTES)

[EMOJI] IMPORTANTE: El saludo inicial fue solo "Hola, buen dia"

[OK] FIX 198: El cliente respondió apropiadamente al saludo.

Ahora di la segunda parte:
"Me comunico de la marca nioval, más que nada quería brindar informacion de nuestros productos ferreteros, ¿Se encontrara el encargado o encargada de compras?"

NO continúes hasta confirmar que hablas con el encargado.

Si responden con preguntas ("¿Quién habla?", "¿De dónde?"):
"Me comunico de la marca nioval, más que nada quería brindar informacion de nuestros productos ferreteros, ¿Se encontrara el encargado o encargada de compras?"
Si dicen "Sí" / "Sí está" (indicando que el encargado SÍ está disponible): "Perfecto, ¿me lo podría comunicar por favor?"
Si dicen "Yo soy" / "Soy yo" / "Habla con él": "Perfecto. ¿Le gustaría recibir el catálogo por WhatsApp o correo electrónico?"
Si dicen NO / "No está" / "No se encuentra": "Entendido. ¿Me podría proporcionar un número de WhatsApp o correo para enviar información?"

[WARN][WARN][WARN] FIX 99/101: SI OFRECEN CORREO, ACEPTARLO Y DESPEDIRSE INMEDIATAMENTE
Si el cliente ofrece dar el CORREO del encargado:
- "Puedo darle su correo" / "Le paso su email" / "Mejor le doy el correo"

RESPONDE: "Perfecto, excelente. Por favor, adelante con el correo."
[ESPERA EL CORREO]

FIX 101: Después de recibir correo - DESPEDIDA INMEDIATA (SIN PEDIR NOMBRE):
"Perfecto, ya lo tengo anotado. Le llegará el catálogo en las próximas horas. Muchas gracias por su tiempo. Que tenga un excelente día."
[TERMINA LLAMADA - NO PIDAS NOMBRE]

[ERROR] NO preguntes el nombre (abruma al cliente que no es de compras)
[ERROR] NO insistas en número si ofrecen correo
[OK] El correo es SUFICIENTE - Despedida inmediata
[OK] Cliente se siente ayudado, NO comprometido

[WARN] IMPORTANTE - Detectar cuando YA te transfirieron:
Si después de pedir la transferencia, alguien dice "Hola" / "Bueno" / "Quién habla?" / "Dígame":
- Esta es LA PERSONA TRANSFERIDA (el encargado), NO una nueva llamada
- NO vuelvas a pedir que te comuniquen con el encargado
- [EMOJI] FIX 172: NO pidas el nombre
- Responde: "¿Bueno? Muy buen día. Me comunico de la marca nioval para ofrecerle nuestro catálogo. ¿Le gustaría recibirlo por WhatsApp?"

IMPORTANTE - Si el cliente ofrece dar el número:
- Si dicen "Te paso su contacto" / "Le doy el número": Di solo "Perfecto, estoy listo." y ESPERA el número SIN volver a pedirlo.
- Si preguntan "¿Tienes donde anotar?": Di solo "Sí, adelante por favor." y ESPERA el número SIN volver a pedirlo.
- NUNCA repitas la solicitud del número si el cliente ya ofreció darlo.

[WARN] FLUJO OBLIGATORIO SI DAN NÚMERO DE CONTACTO DE REFERENCIA:
[Si dan número de teléfono del encargado]
[WARN][WARN][WARN] FIX 98: FLUJO ULTRA-RÁPIDO - CLIENTE OCUPADO [WARN][WARN][WARN]

PASO 1: "Perfecto, muchas gracias. ¿Me podría decir su nombre para poder mencionarle que usted me facilitó su contacto?"
[Esperar nombre]

PASO 2 (SIMPLIFICADO): "Gracias [NOMBRE]. Perfecto, le enviaré el catálogo completo por correo electrónico para que el encargado lo revise con calma. ¿Me confirma el correo?"
[Esperar correo]

PASO 3 (DESPEDIDA INMEDIATA): "Perfecto, ya lo tengo anotado. Le llegará en las próximas horas. Muchas gracias por su tiempo, [NOMBRE]. Que tenga un excelente día."
[FIN DE LLAMADA]

[ERROR] NUNCA hagas 3-4 preguntas largas (productos, proveedores, necesidades, horarios)
[ERROR] NUNCA preguntes "¿Qué tipo de productos manejan? ¿Son ferretería local o mayorista?"
[ERROR] La persona está OCUPADA en mostrador - ir DIRECTO al correo
[OK] Solo: Nombre → Correo → Despedida (máximo 3 intercambios)
""")
                # FIX 201: Marcar que se dijo la segunda parte del saludo
                self.segunda_parte_saludo_dicha = True
                # FIX 535: Marcar conversación iniciada para prevenir pérdida de contexto
                self.conversacion_iniciada = True
                print(f"[OK] FIX 201/535: Se activó la segunda parte del saludo. conversacion_iniciada=True")

            elif self.segunda_parte_saludo_dicha:
                # FIX 201: Cliente dijo "Dígame" u otro saludo DESPUÉS de que ya se dijo la segunda parte
                # NO repetir la introducción, continuar con la conversación
                fase_actual.append(f"""
# FASE ACTUAL: CONTINUACIÓN DESPUÉS DEL SALUDO - FIX 201

[EMOJI] IMPORTANTE: Ya dijiste la presentación completa anteriormente.

Cliente dijo: "{ultima_respuesta_cliente}"

[EMOJI] ANÁLISIS:
El cliente está diciendo "{ultima_respuesta_cliente}" como una forma de decir "continúa" o "te escucho".

[OK] NO repitas tu presentación
[OK] NO vuelvas a decir "Me comunico de la marca nioval..."
[OK] YA lo dijiste antes

[EMOJI] ACCIÓN CORRECTA:
Si preguntaste por el encargado de compras y el cliente dice "Dígame":
→ Interpreta esto como que ÉL ES el encargado o está escuchando
→ Continúa con: "Perfecto. ¿Le gustaría recibir nuestro catálogo por WhatsApp o correo electrónico?"

Si no has preguntado por el encargado aún:
→ Pregunta directamente: "¿Se encuentra el encargado o encargada de compras?"
""")
                print(f"[OK] FIX 201: Cliente dijo '{ultima_respuesta_cliente}' después de la segunda parte. NO se repetirá la introducción.")

            else:
                # FIX 198: Cliente NO respondió con saludo estándar
                fase_actual.append(f"""
# FASE ACTUAL: APERTURA - FIX 198: MANEJO DE RESPUESTA NO ESTÁNDAR

[EMOJI] El cliente NO respondió con un saludo estándar.

Cliente dijo: "{ultima_respuesta_cliente}"

[EMOJI] ANÁLISIS Y ACCIÓN:

Si parece una PREGUNTA ("¿Quién habla?", "¿De dónde?", "¿Qué desea?"):
→ Responde la pregunta Y LUEGO di tu presentación completa:
   "Me comunico de la marca nioval, más que nada quería brindar informacion de nuestros productos ferreteros, ¿Se encontrara el encargado o encargada de compras?"

Si parece CONFUSIÓN o NO ENTENDIÓ (respuesta sin sentido, silencio, ruido):
→ Repite tu saludo de forma más clara y completa:
   "¿Bueno? Buenos días. Me comunico de la marca nioval, más que nada quería brindar informacion de nuestros productos ferreteros, ¿Se encontrara el encargado o encargada de compras?"

Si parece RECHAZO ("Ocupado", "No me interesa", "No tengo tiempo"):
→ Respeta su tiempo y ofrece alternativa rápida:
   "Entiendo que está ocupado. ¿Le gustaría que le envíe el catálogo por WhatsApp o correo para revisarlo cuando tenga tiempo?"

[OK] SIEMPRE termina preguntando por el encargado de compras
[OK] NO insistas si muestran rechazo claro
[OK] Mantén tono profesional y respetuoso
""")

        # FASE 2: Si ya tenemos nombre pero aún no presentamos valor
        elif not self.lead_data.get("productos_interes") and len(self.conversation_history) < 8:
            fase_actual.append(f"""
# FASE ACTUAL: PRESENTACIÓN Y CALIFICACIÓN
Ya hablas con: {self.lead_data.get("nombre_contacto", "el encargado")}

Di: "El motivo de mi llamada es muy breve: nosotros distribuimos productos de ferretería con alta rotación, especialmente nuestra cinta para goteras que muchos negocios de ferretería tienen como producto estrella, además de griferías, herramientas y más de quince categorías. ¿Usted maneja este tipo de productos actualmente en su negocio?"

IMPORTANTE - PREGUNTAS A CAPTURAR (durante conversación natural):
P1: ¿Persona con quien hablaste es encargado de compras? (Sí/No/Tal vez)
P2: ¿La persona toma decisiones de compra? (Sí/No/Tal vez)
P3: ¿Acepta pedido inicial sugerido? (Crear Pedido Inicial Sugerido/No)
P4: Si dijo NO a P3, ¿acepta pedido de muestra de mil quinientos pesos? (Sí/No)
P5: Si aceptó P3 o P4, ¿procesar esta semana? (Sí/No/Tal vez)
P6: Si aceptó P5, ¿pago con tarjeta crédito? (Sí/No/Tal vez)
P7: Resultado final (capturado automáticamente al terminar)

Mantén conversación natural mientras capturas esta info.
""")

        # FASE 3: Si hay interés pero no tenemos WhatsApp
        elif not self.lead_data.get("whatsapp"):
            fase_actual.append(f"""
# FASE ACTUAL: CAPTURA DE WHATSAPP
Ya tienes: Nombre={self.lead_data.get("nombre_contacto", "N/A")}

[WARN][WARN][WARN] CRÍTICO - VERIFICAR HISTORIAL ANTES DE PEDIR CORREO [WARN][WARN][WARN]
ANTES DE PEDIR CORREO ELECTRÓNICO, REVISA CUIDADOSAMENTE EL HISTORIAL DE LA CONVERSACIÓN:
- Si el cliente YA mencionó su WhatsApp anteriormente (ej: "3331234567"), NO pidas correo
- Si el cliente dice "ya te lo pasé" o "ya te lo di", es porque SÍ te dio el WhatsApp antes
- NUNCA pidas correo si ya tienes WhatsApp en el historial

PRIORIDAD ABSOLUTA DE CONTACTO:
1. WhatsApp (PRIMERA OPCIÓN - siempre pedir primero)
2. Correo (SOLO si confirmó que NO tiene WhatsApp o no puede dar WhatsApp)

Si cliente dice "ya te lo pasé/di el WhatsApp":
- Pide disculpas: "Tiene razón, discúlpeme. Deje verifico el número que me pasó..."
- Revisa el historial y confirma el número que dio
- NO pidas el correo

CRÍTICO: Tú SÍ puedes enviar el catálogo por WhatsApp. Un compañero del equipo lo enviará.

Di: "Me gustaría enviarle nuestro catálogo digital completo con lista de precios para que lo revise con calma. Le puedo compartir todo por WhatsApp que es más rápido y visual. ¿Cuál es su número de WhatsApp?"

IMPORTANTE - Respuestas comunes del cliente:
- Si dicen "Te paso el contacto" / "Te lo doy": Di solo "Perfecto, estoy listo para anotarlo." y ESPERA el número SIN volver a pedirlo.
- Si preguntan "¿Tienes donde anotar?": Di solo "Sí, adelante por favor." y ESPERA el número SIN volver a pedirlo.
- Si dan el número directamente: Di "Perfecto, ya lo tengo anotado. ¿Es de 10 dígitos?" (NO repitas el número en voz).
- Si no tienen WhatsApp: "Entiendo. ¿Tiene correo electrónico donde enviarle el catálogo?"

NUNCA repitas la solicitud del número si el cliente ya ofreció darlo o está a punto de darlo.
NUNCA digas que no puedes enviar el catálogo. SIEMPRE puedes enviarlo.

[WARN][WARN][WARN] TIMING DE ENVÍO DEL CATÁLOGO - CRÍTICO:
[ERROR] NUNCA NUNCA NUNCA digas: "en un momento", "ahorita", "al instante", "inmediatamente", "ya se lo envío"
[OK] SIEMPRE SIEMPRE SIEMPRE di: "en el transcurso del día" o "en las próximas 2 horas"
Razón: Un compañero del equipo lo envía, NO es automático.

Ejemplos CORRECTOS cuando confirmas WhatsApp:
- "Perfecto, en las próximas 2 horas le llega el catálogo por WhatsApp"
- "Excelente, le envío el catálogo en el transcurso del día"

Ejemplos INCORRECTOS (NUNCA uses):
- "En un momento le enviaré..." [ERROR]
- "Ahorita le envío..." [ERROR]
- "Se lo envío al instante..." [ERROR]
""")

        # FASE 4: Si ya tenemos WhatsApp, proceder al cierre
        elif self.lead_data.get("whatsapp"):
            nombre = self.lead_data.get("nombre_contacto", "")
            fase_actual.append(f"""
# FASE ACTUAL: CIERRE
Ya tienes: Nombre={nombre}, WhatsApp={self.lead_data.get("whatsapp")}

Di: "Excelente{f', {nombre}' if nombre else ''}. En las próximas 2 horas le llega el catálogo completo por WhatsApp. Le voy a marcar algunos productos que creo pueden interesarle según lo que me comentó. También le incluyo información sobre nuestra promoción de primer pedido de $1,500 pesos con envío gratis. Un compañero del equipo le dará seguimiento en los próximos días. ¿Le parece bien?"

Despedida: "Muchas gracias por su tiempo{f', señor/señora {nombre}' if nombre else ''}. Que tenga excelente tarde. Hasta pronto."
""")

        # ============================================================
        # FIX 491: FASE 1 - Sistema de Contexto Dinámico
        # Generar contexto dinámico que se AGREGA al prompt original
        # ============================================================
        contexto_dinamico = self._generar_contexto_dinamico()

        # Combinar prompt base + fase actual + contexto dinámico
        return prompt_base + "\n".join(fase_actual) + contexto_dinamico

    def _guardar_backup_excel(self):
        """Guarda un respaldo en Excel local"""
        try:
            import os
            archivo_excel = "leads_nioval_backup.xlsx"
            ruta_completa = os.path.abspath(archivo_excel)

            print(f"[EMOJI] Intentando guardar backup en: {ruta_completa}")

            # Intentar cargar archivo existente
            try:
                df = pd.read_excel(archivo_excel)
                print(f"[EMOJI] Archivo existente cargado con {len(df)} filas")
            except FileNotFoundError:
                df = pd.DataFrame()
                print(f"[EMOJI] Creando nuevo archivo Excel")

            # Convertir objeciones a string
            lead_data_excel = self.lead_data.copy()
            lead_data_excel["objeciones"] = ", ".join(lead_data_excel["objeciones"])

            # Agregar nuevo lead
            nuevo_lead = pd.DataFrame([lead_data_excel])
            df = pd.concat([df, nuevo_lead], ignore_index=True)

            # Guardar
            df.to_excel(archivo_excel, index=False)
            print(f"[OK] Backup guardado en {ruta_completa} ({len(df)} filas totales)")

        except Exception as e:
            import traceback
            print(f"[WARN] No se pudo guardar backup en Excel: {e}")
            print(f"[WARN] Traceback: {traceback.format_exc()}")

    def autoevaluar_llamada(self):
        """
        Bruce se autoevalúa y asigna una calificación del 1-10 según el resultado de la llamada

        Parámetros de calificación:

        10 - EXCELENTE: Lead caliente confirmado con WhatsApp validado, interesado, respondió todas las preguntas
        9  - MUY BUENO: Lead caliente con WhatsApp, interesado pero faltó alguna información menor
        8  - BUENO: Lead tibio con WhatsApp capturado, mostró algo de interés
        7  - ACEPTABLE: Contacto correcto (dueño/encargado), conversación completa pero sin mucho interés
        6  - REGULAR: Contacto correcto, conversación cortada o cliente neutral
        5  - SUFICIENTE: Número incorrecto pero se obtuvo referencia con número nuevo
        4  - BAJO: No es el contacto correcto, no dio referencia
        3  - DEFICIENTE: Cliente molesto/cortó rápido, no se pudo rescatar nada
        2  - MUY DEFICIENTE: Buzón de voz
        1  - PÉSIMO: Número equivocado/no existe

        Returns:
            int: Calificación de 1-10
        """
        try:
            # Extraer datos clave
            resultado = self.lead_data.get("resultado", "")
            estado_llamada = self.lead_data.get("pregunta_0", "")
            nivel_interes = self.lead_data.get("nivel_interes_clasificado", "")
            whatsapp = self.lead_data.get("whatsapp", "")
            referencia = self.lead_data.get("referencia_telefono", "")
            estado_animo = self.lead_data.get("estado_animo_cliente", "")

            # CASO 10: Lead perfecto
            if (resultado == "ACEPTADO" and
                whatsapp and
                nivel_interes in ["CALIENTE", "Caliente"] and
                self.lead_data.get("pregunta_7") == "SI"):
                return 10

            # CASO 9: Lead muy bueno
            if (resultado == "ACEPTADO" and
                whatsapp and
                nivel_interes in ["CALIENTE", "Caliente", "TIBIO", "Tibio"]):
                return 9

            # CASO 8: Lead bueno
            if (resultado == "ACEPTADO" and whatsapp):
                return 8

            # CASO 7: Conversación completa, contacto correcto
            if (estado_llamada in ["Dueño", "Encargado Compras"] and
                resultado in ["PENDIENTE", "ACEPTADO"]):
                return 7

            # CASO 6: Conversación cortada pero contacto correcto
            if estado_llamada in ["Dueño", "Encargado Compras"]:
                return 6

            # CASO 5: Número incorrecto pero con referencia
            if (estado_llamada in ["Número Incorrecto", "Numero Incorrecto"] and
                referencia):
                return 5

            # CASO 4: Número incorrecto sin referencia
            if estado_llamada in ["Número Incorrecto", "Numero Incorrecto"]:
                return 4

            # CASO 3: Cliente molesto
            if estado_animo in ["Molesto", "Enojado"] or resultado == "NEGADO":
                return 3

            # CASO 2: Buzón de voz
            if estado_llamada == "Buzon":
                return 2

            # CASO 1: Número equivocado/no existe
            if estado_llamada in ["No Contesta", "Numero Equivocado"]:
                return 1

            # Default: 5 (suficiente)
            return 5

        except Exception as e:
            print(f"[WARN] Error en autoevaluación: {e}")
            return 5  # Calificación neutra si hay error

    def guardar_llamada_y_lead(self):
        """
        Guarda la llamada en Google Sheets usando ResultadosSheetsAdapter
        (Llamado desde servidor_llamadas.py al finalizar llamada)
        """
        if not self.resultados_manager:
            print("[WARN] ResultadosSheetsAdapter no disponible - no se puede guardar")
            return

        try:
            print("[EMOJI] Guardando resultados en 'Bruce FORMS'...")

            # Calcular duración de la llamada ANTES de guardar
            if self.lead_data.get("fecha_inicio"):
                try:
                    inicio = datetime.strptime(self.lead_data["fecha_inicio"], "%Y-%m-%d %H:%M:%S")
                    duracion = (datetime.now() - inicio).total_seconds()
                    self.lead_data["duracion_segundos"] = int(duracion)
                    print(f"[EMOJI] Duración de la llamada: {self.lead_data['duracion_segundos']} segundos")
                except Exception as e:
                    print(f"[WARN] Error calculando duración: {e}")
                    self.lead_data["duracion_segundos"] = 0
            else:
                print(f"[WARN] No hay fecha_inicio - duración = 0")
                self.lead_data["duracion_segundos"] = 0

            # FIX 482 (AUDITORIA W04): Imprimir reporte de métricas
            print(self.metrics.generar_reporte())

            # Determinar conclusión antes de guardar
            self._determinar_conclusion()

            # Autoevaluar llamada (Bruce se califica del 1-10)
            calificacion_bruce = self.autoevaluar_llamada()
            print(f"[EMOJI] Bruce se autoevaluó: {calificacion_bruce}/10")

            # Guardar en "Bruce FORMS"
            resultado_guardado = self.resultados_manager.guardar_resultado_llamada({
                'nombre_negocio': self.lead_data["nombre_negocio"],
                'telefono': self.lead_data["telefono"],
                'ciudad': self.lead_data["ciudad"],
                'estado_llamada': self.lead_data["pregunta_0"],
                'pregunta_1': self.lead_data["pregunta_1"],
                'pregunta_2': self.lead_data["pregunta_2"],
                'pregunta_3': self.lead_data["pregunta_3"],
                'pregunta_4': self.lead_data["pregunta_4"],
                'pregunta_5': self.lead_data["pregunta_5"],
                'pregunta_6': self.lead_data["pregunta_6"],
                'pregunta_7': self.lead_data["pregunta_7"],
                'resultado': self.lead_data["resultado"],
                'duracion': self.lead_data["duracion_segundos"],
                'nivel_interes_clasificado': self.lead_data["nivel_interes_clasificado"],
                'estado_animo_cliente': self.lead_data["estado_animo_cliente"],
                'opinion_bruce': self.lead_data["opinion_bruce"],
                'calificacion': calificacion_bruce,  # Calificación de Bruce (1-10)
                'bruce_id': getattr(self, 'bruce_id', None)  # ID BRUCE (BRUCE01, BRUCE02, etc.)
            })

            if resultado_guardado:
                print(f"[OK] Resultados guardados en 'Bruce FORMS'")
            else:
                print(f"[ERROR] Error al guardar resultados")

            print("\n" + "=" * 60)
            print("[EMOJI] ACTUALIZACIONES EN LISTA DE CONTACTOS")
            print("=" * 60)

            # Actualizar WhatsApp y Email en LISTA DE CONTACTOS si están disponibles
            if self.sheets_manager and self.contacto_info:
                fila = self.contacto_info.get('fila') or self.contacto_info.get('ID')
                print(f"\n[EMOJI] Verificando actualización en LISTA DE CONTACTOS...")
                print(f"   Fila: {fila}")
                print(f"   WhatsApp capturado: {self.lead_data['whatsapp']}")
                print(f"   Referencia capturada: {self.lead_data.get('referencia_telefono', '')}")
                print(f"   Email capturado: {self.lead_data['email']}")

                # Determinar qué número actualizar en columna E
                numero_para_columna_e = None

                # Prioridad 1: WhatsApp directo del contacto
                if self.lead_data["whatsapp"]:
                    numero_para_columna_e = self.lead_data["whatsapp"]
                    tipo_numero = "WhatsApp directo"
                # Prioridad 2: Número de referencia (encargado/contacto)
                elif self.lead_data.get("referencia_telefono"):
                    numero_para_columna_e = self.lead_data["referencia_telefono"]
                    tipo_numero = "Número de referencia"

                # Actualizar columna E si tenemos algún número
                if numero_para_columna_e and fila:
                    print(f"   [EMOJI] Actualizando columna E:E fila {fila} con {tipo_numero}...")
                    self.sheets_manager.actualizar_numero_con_whatsapp(
                        fila=fila,
                        whatsapp=numero_para_columna_e
                    )
                    print(f"[OK] Columna E actualizada con {tipo_numero}: {numero_para_columna_e}")
                elif not numero_para_columna_e:
                    print(f"[WARN] No se capturó WhatsApp ni referencia - no se actualiza columna E")
                elif not fila:
                    print(f"[WARN] No se tiene fila del contacto - no se puede actualizar")

                if self.lead_data["email"] and fila:
                    self.sheets_manager.registrar_email_capturado(
                        fila=fila,
                        email=self.lead_data["email"]
                    )
                    print(f"[OK] Email actualizado en LISTA DE CONTACTOS")

                # Guardar referencia si se detectó una (solo necesitamos el teléfono)
                if "referencia_nombre" in self.lead_data and self.lead_data.get("referencia_telefono"):
                    print(f"\n[EMOJI] Procesando referencia...")
                    print(f"   Nombre del referido: {self.lead_data['referencia_nombre']}")
                    print(f"   Teléfono del referido: {self.lead_data['referencia_telefono']}")

                    # Buscar el número del referido en LISTA DE CONTACTOS
                    telefono_referido = self.lead_data["referencia_telefono"]

                    # Buscar en todos los contactos
                    contactos = self.sheets_manager.obtener_contactos_pendientes(limite=10000)
                    fila_referido = None

                    for contacto in contactos:
                        # IMPORTANTE: Excluir la fila actual para evitar referencia circular
                        if contacto['telefono'] == telefono_referido and contacto['fila'] != fila:
                            fila_referido = contacto['fila']
                            print(f"   [OK] Referido encontrado en fila {contacto['fila']}: {contacto.get('nombre_negocio', 'Sin nombre')}")
                            break

                    if fila_referido:
                        # 1. Guardar referencia en columna U del contacto referido (nueva fila)
                        nombre_referidor = self.contacto_info.get('nombre_negocio', 'Cliente')
                        telefono_referidor = self.contacto_info.get('telefono', '')
                        contexto = self.lead_data.get('referencia_contexto', '')

                        # Pasar también el número que se está guardando para detectar cambios futuros
                        self.sheets_manager.guardar_referencia(
                            fila_destino=fila_referido,
                            nombre_referidor=nombre_referidor,
                            telefono_referidor=telefono_referidor,
                            contexto=contexto,
                            numero_llamado=telefono_referido  # Número del nuevo contacto
                        )
                        print(f"[OK] Referencia guardada en fila {fila_referido} (columna U)")

                        # 2. Guardar contexto en columna W de la fila ACTUAL indicando que dio una referencia
                        nombre_ref = self.lead_data.get('referencia_nombre', 'Encargado')
                        if not nombre_ref:
                            nombre_ref = "Encargado"

                        contexto_actual = f"Dio referencia: {nombre_ref} ({telefono_referido}) - {contexto[:50]}"
                        self.sheets_manager.guardar_contexto_reprogramacion(
                            fila=fila,
                            fecha="Referencia dada",
                            motivo=f"Pasó contacto de {nombre_ref}",
                            notas=contexto_actual
                        )
                        print(f"[OK] Contexto de referencia guardado en fila {fila} (columna W)")

                        # 3. INICIAR LLAMADA AUTOMÁTICA AL REFERIDO
                        print(f"\n[EMOJI] Iniciando llamada automática al referido...")
                        try:
                            import requests
                            import os

                            # URL del servidor de llamadas (puede estar en variable de entorno)
                            servidor_url = os.getenv("SERVIDOR_LLAMADAS_URL", "https://nioval-webhook-server-production.up.railway.app")
                            endpoint = f"{servidor_url}/iniciar-llamada"

                            # Preparar datos de la llamada
                            payload = {
                                "telefono": telefono_referido,
                                "fila": fila_referido
                            }

                            print(f"   [EMOJI] Enviando solicitud a {endpoint}")
                            print(f"   [PHONE] Teléfono: {telefono_referido}")
                            print(f"   [EMOJI] Fila: {fila_referido}")

                            # Hacer la solicitud POST (con timeout para no bloquear)
                            response = requests.post(
                                endpoint,
                                json=payload,
                                timeout=5
                            )

                            if response.status_code == 200:
                                data = response.json()
                                call_sid = data.get("call_sid", "Unknown")
                                print(f"   [OK] Llamada iniciada exitosamente!")
                                print(f"   [EMOJI] Call SID: {call_sid}")
                            else:
                                print(f"   [WARN] Error al iniciar llamada: {response.status_code}")
                                print(f"   Respuesta: {response.text}")

                        except requests.exceptions.Timeout:
                            print(f"   [WARN] Timeout al iniciar llamada - la llamada puede haberse iniciado de todas formas")
                        except Exception as e:
                            print(f"   [ERROR] Error al iniciar llamada automática: {e}")
                            print(f"   La llamada deberá iniciarse manualmente")

                    else:
                        print(f"[WARN] No se encontró el número {telefono_referido} en LISTA DE CONTACTOS")
                        print(f"   La referencia NO se guardó - agregar el contacto manualmente")

                        # Guardar en columna W que dio una referencia pero no está en la lista
                        nombre_ref = self.lead_data.get('referencia_nombre', 'Encargado')
                        if not nombre_ref:
                            nombre_ref = "Encargado"

                        self.sheets_manager.guardar_contexto_reprogramacion(
                            fila=fila,
                            fecha="Referencia no encontrada",
                            motivo=f"Dio número {telefono_referido} ({nombre_ref}) - NO ESTÁ EN LISTA",
                            notas="Agregar contacto manualmente a LISTA DE CONTACTOS"
                        )
                        print(f"[OK] Contexto de referencia guardado en fila {fila} (columna W)")

                # Guardar contexto de reprogramación si el cliente pidió ser llamado después
                if self.lead_data.get("estado_llamada") == "reprogramar" and fila:
                    print(f"\n[EMOJI] Guardando contexto de reprogramación...")

                    # Extraer fecha y motivo si están disponibles
                    fecha_reprogramacion = self.fecha_reprogramacion or "Próximos días"
                    motivo = f"Cliente solicitó ser llamado después. {self.lead_data['notas'][:100]}"

                    self.sheets_manager.guardar_contexto_reprogramacion(
                        fila=fila,
                        fecha=fecha_reprogramacion,
                        motivo=motivo,
                        notas=f"Interés: {self.lead_data['nivel_interes']} | WhatsApp: {self.lead_data['whatsapp'] or 'No capturado'}"
                    )
                    print(f"[OK] Contexto de reprogramación guardado en columna W")

                    # Limpiar columna F para que vuelva a aparecer como pendiente
                    self.sheets_manager.marcar_estado_final(fila, "")
                    print(f"[OK] Columna F limpiada - contacto volverá a aparecer como pendiente")
            else:
                print("[WARN] No hay sheets_manager o contacto_info - omitiendo actualizaciones")
                print(f"   sheets_manager: {'[EMOJI]' if self.sheets_manager else '[EMOJI]'}")
                print(f"   contacto_info: {'[EMOJI]' if self.contacto_info else '[EMOJI]'}")

            print("\n" + "=" * 60)
            print("[OK] GUARDADO COMPLETO - Todos los datos procesados")
            print("=" * 60 + "\n")

        except Exception as e:
            print(f"[ERROR] Error al guardar llamada: {e}")
            import traceback
            traceback.print_exc()

    def obtener_resumen(self) -> dict:
        """Retorna un resumen de la conversación y datos recopilados"""

        # Determinar conclusión automáticamente antes de retornar
        self._determinar_conclusion()

        return {
            "lead_data": self.lead_data,
            "num_mensajes": len(self.conversation_history),
            "duracion_estimada": len(self.conversation_history) * 15  # segundos
        }


def demo_interactiva():
    """Demo interactiva por consola"""
    print("=" * 60)
    print("[EMOJI] AGENTE DE VENTAS NIOVAL - Bruce W")
    print("=" * 60)
    print()
    
    agente = AgenteVentas()
    
    # Mensaje inicial
    mensaje_inicial = agente.iniciar_conversacion()
    print(f"[EMOJI] Bruce W: {mensaje_inicial}")
    print()
    
    # Frases de despedida del cliente (mejoradas para México)
    despedidas_cliente = [
        "lo reviso", "lo revisare", "lo revisaré", "lo checo", "lo checamos",
        "adiós", "adios", "hasta luego", "nos vemos", "bye", "chao",
        "luego hablamos", "después platicamos", "luego te marco",
        "ya te contacto", "ya te contactamos", "te marco después",
        "te llamamos después", "te llamo después",
        "ok gracias adiós", "gracias adiós", "gracias hasta luego",
        "está bien gracias", "esta bien gracias", "sale pues"
    ]

    # Bucle conversacional
    while True:
        respuesta_cliente = input("[EMOJI] Cliente: ").strip()
        
        if not respuesta_cliente:
            continue
        
        if respuesta_cliente.lower() in ["salir", "exit", "terminar"]:
            print("\n[EMOJI] Guardando información del lead...")
            agente.guardar_llamada_y_lead()
            print("\n" + "=" * 60)
            print("RESUMEN DE LA CONVERSACIÓN:")
            print(json.dumps(agente.obtener_resumen(), indent=2, ensure_ascii=False))
            print("=" * 60)
            break
        
        # Procesar y responder
        respuesta_agente = agente.procesar_respuesta(respuesta_cliente)
        print(f"\n[EMOJI] Bruce W: {respuesta_agente}\n")

        # Detectar estados de llamada sin respuesta (terminar automáticamente)
        if agente.lead_data["estado_llamada"] in ["Buzon", "Telefono Incorrecto", "Colgo", "No Respondio", "No Contesta"]:
            print(f"[EMOJI] Estado detectado: {agente.lead_data['estado_llamada']}. Finalizando llamada automáticamente...")
            print("[EMOJI] Guardando información del lead...\n")
            agente.guardar_llamada_y_lead()
            print("\n" + "=" * 60)
            print("RESUMEN DE LA CONVERSACIÓN:")
            print(json.dumps(agente.obtener_resumen(), indent=2, ensure_ascii=False))
            print("=" * 60)
            break

        # Detectar si el cliente se está despidiendo (solo después del turno 2+)
        num_turnos = len(agente.conversation_history) // 2

        # Palabras que indican inicio de llamada (NO despedida)
        saludos_inicio = ["bueno", "buenas", "diga", "hola", "¿quién habla?", "quien habla"]
        es_inicio = num_turnos <= 2 and any(saludo in respuesta_cliente.lower() for saludo in saludos_inicio)

        # Detectar despedida REAL (solo después de 2+ turnos y sin palabras de inicio)
        cliente_se_despide = (
            num_turnos > 2 and
            not es_inicio and
            any(frase in respuesta_cliente.lower() for frase in despedidas_cliente)
        )

        # Si el cliente se despidió, Bruce responde y termina
        if cliente_se_despide:
            print("\n[EMOJI] Bruce W detectó despedida. Finalizando llamada...")
            print("[EMOJI] Guardando información del lead...\n")
            agente.guardar_llamada_y_lead()
            print("\n" + "=" * 60)
            print("RESUMEN DE LA CONVERSACIÓN:")
            print(json.dumps(agente.obtener_resumen(), indent=2, ensure_ascii=False))
            print("=" * 60)
            break


def procesar_contactos_automaticamente():
    """
    Procesa contactos desde Google Sheets automáticamente
    """
    try:
        # Importar adaptadores
        from nioval_sheets_adapter import NiovalSheetsAdapter
        from resultados_sheets_adapter import ResultadosSheetsAdapter

        print("\n" + "=" * 60)
        print("[ROCKET] SISTEMA AUTOMÁTICO DE LLAMADAS - NIOVAL")
        print("=" * 60)

        # Inicializar adaptadores
        print("\n[EMOJI] Conectando con Google Sheets...")
        nioval_adapter = NiovalSheetsAdapter()
        resultados_adapter = ResultadosSheetsAdapter()

        # Contador de contactos procesados
        contactos_procesados = 0
        max_contactos = 100  # Límite de contactos a procesar en esta sesión

        # Procesar contactos continuamente (recargar lista después de cada uno)
        while contactos_procesados < max_contactos:
            # Recargar contactos pendientes (siempre obtiene el primero disponible)
            print("[EMOJI] Leyendo contactos pendientes...")
            contactos = nioval_adapter.obtener_contactos_pendientes(limite=1)  # Solo obtener el primero

            if not contactos:
                print(f"\n[OK] No hay más contactos pendientes")
                break

            contacto = contactos[0]  # Tomar el primer contacto
            contactos_procesados += 1

            print("\n" + "=" * 60)
            print(f"[EMOJI] CONTACTO #{contactos_procesados}")
            print(f"   Negocio: {contacto.get('nombre_negocio', 'Sin nombre')}")
            print(f"   Teléfono: {contacto.get('telefono', 'Sin teléfono')}")
            print(f"   Ciudad: {contacto.get('ciudad', 'Sin ciudad')}")
            print("=" * 60 + "\n")

            # Crear agente para este contacto
            agente = AgenteVentas(contacto_info=contacto)

            # Iniciar conversación
            mensaje_inicial = agente.iniciar_conversacion()
            print(f"[EMOJI] Bruce W: {mensaje_inicial}\n")

            # Bucle conversacional
            despedidas_cliente = [
                "lo reviso", "lo revisare", "lo revisaré", "lo checo", "lo checamos",
                "adiós", "adios", "hasta luego", "nos vemos", "bye", "chao",
                "luego hablamos", "después platicamos", "luego te marco",
                "ya te contacto", "ya te contactamos", "te marco después",
                "te llamamos después", "te llamo después",
                "ok gracias adiós", "gracias adiós", "gracias hasta luego",
                "está bien gracias", "esta bien gracias", "sale pues"
            ]

            while True:
                respuesta_cliente = input("[EMOJI] Cliente: ").strip()

                if not respuesta_cliente:
                    continue

                if respuesta_cliente.lower() in ["salir", "exit", "terminar"]:
                    print("\n[EMOJI] Finalizando conversación...")
                    break

                # Procesar y responder
                respuesta_agente = agente.procesar_respuesta(respuesta_cliente)
                print(f"\n[EMOJI] Bruce W: {respuesta_agente}\n")

                # Detectar estados de llamada sin respuesta (terminar automáticamente)
                if agente.lead_data["estado_llamada"] in ["Buzon", "Telefono Incorrecto", "Colgo", "No Respondio", "No Contesta"]:
                    print(f"[EMOJI] Estado detectado: {agente.lead_data['estado_llamada']}. Finalizando llamada automáticamente...")
                    break

                # Detectar despedida
                num_turnos = len(agente.conversation_history) // 2
                saludos_inicio = ["bueno", "buenas", "diga", "hola", "¿quién habla?", "quien habla"]
                es_inicio = num_turnos <= 2 and any(saludo in respuesta_cliente.lower() for saludo in saludos_inicio)

                cliente_se_despide = (
                    num_turnos > 2 and
                    not es_inicio and
                    any(frase in respuesta_cliente.lower() for frase in despedidas_cliente)
                )

                if cliente_se_despide:
                    print("\n[EMOJI] Bruce W detectó despedida. Finalizando conversación...")
                    break

            # Calcular duración de llamada
            if agente.lead_data["fecha_inicio"]:
                from datetime import datetime
                inicio = datetime.strptime(agente.lead_data["fecha_inicio"], "%Y-%m-%d %H:%M:%S")
                duracion = (datetime.now() - inicio).total_seconds()
                agente.lead_data["duracion_segundos"] = int(duracion)

            # Realizar análisis y determinar conclusión ANTES de guardar
            print("\n[EMOJI] Analizando llamada...")
            agente._determinar_conclusion()

            # Guardar resultados en Google Sheets
            print("\n[EMOJI] Guardando resultados en Google Sheets...")

            try:
                # 1. Guardar en "Bruce FORMS" (7 preguntas + análisis)
                resultado_guardado = resultados_adapter.guardar_resultado_llamada({
                    'nombre_negocio': agente.lead_data["nombre_negocio"],
                    'telefono': agente.lead_data["telefono"],
                    'ciudad': agente.lead_data["ciudad"],
                    'estado_llamada': agente.lead_data["pregunta_0"],
                    'pregunta_1': agente.lead_data["pregunta_1"],
                    'pregunta_2': agente.lead_data["pregunta_2"],
                    'pregunta_3': agente.lead_data["pregunta_3"],
                    'pregunta_4': agente.lead_data["pregunta_4"],
                    'pregunta_5': agente.lead_data["pregunta_5"],
                    'pregunta_6': agente.lead_data["pregunta_6"],
                    'pregunta_7': agente.lead_data["pregunta_7"],
                    'resultado': agente.lead_data["resultado"],
                    'duracion': agente.lead_data["duracion_segundos"],
                    'nivel_interes_clasificado': agente.lead_data["nivel_interes_clasificado"],
                    'estado_animo_cliente': agente.lead_data["estado_animo_cliente"],
                    'opinion_bruce': agente.lead_data["opinion_bruce"]
                })
                if resultado_guardado:
                    print(f"   [OK] Formulario guardado correctamente")

                # 2. Actualizar contacto en "LISTA DE CONTACTOS"
                if agente.lead_data["whatsapp"]:
                    nioval_adapter.actualizar_numero_con_whatsapp(
                        fila=contacto['fila'],
                        whatsapp=agente.lead_data["whatsapp"]
                    )
                    print(f"   [OK] WhatsApp actualizado en LISTA DE CONTACTOS (celda E)")

                if agente.lead_data["email"]:
                    nioval_adapter.registrar_email_capturado(
                        fila=contacto['fila'],
                        email=agente.lead_data["email"]
                    )
                    print(f"   [OK] Email actualizado en LISTA DE CONTACTOS (celda T)")

                # 3. Manejo especial de BUZÓN (4 reintentos: 2 por día x 2 días)
                if agente.lead_data["estado_llamada"] == "Buzon":
                    # Marcar intento de buzón y obtener contador
                    intentos = nioval_adapter.marcar_intento_buzon(contacto['fila'])

                    if intentos <= 3:
                        # Intentos 1, 2, 3 - mover al final para reintentar
                        print(f"   [EMOJI] Intento #{intentos} de buzón detectado")
                        print(f"   ↩[EMOJI]  Moviendo contacto al final de la lista para reintentar...")
                        nioval_adapter.mover_fila_al_final(contacto['fila'])

                        if intentos == 1:
                            print(f"   [OK] Contacto reagendado para intento #2 (mismo día)")
                        elif intentos == 2:
                            print(f"   [OK] Contacto reagendado para intento #3 (siguiente ronda)")
                        elif intentos == 3:
                            print(f"   [OK] Contacto reagendado para intento #4 (último intento)")

                    elif intentos >= 4:
                        # Cuarto intento de buzón - clasificar como TELEFONO INCORRECTO
                        print(f"   [EMOJI] Cuarto intento de buzón detectado")
                        print(f"   [ERROR] Número no válido después de 4 intentos (2 días)")
                        print(f"   [EMOJI] Clasificando como TELEFONO INCORRECTO")
                        nioval_adapter.marcar_estado_final(contacto['fila'], "TELEFONO INCORRECTO")
                        print(f"   [EMOJI] Moviendo contacto al final de la lista (números no válidos)")
                        nioval_adapter.mover_fila_al_final(contacto['fila'])
                        print(f"   [OK] Contacto archivado al final con estado: TELEFONO INCORRECTO")
                else:
                    # Para otros estados (Respondio, Telefono Incorrecto, Colgo, No Contesta)
                    # Marcar el estado final en columna F
                    estado_final = agente.lead_data["estado_llamada"]
                    nioval_adapter.marcar_estado_final(contacto['fila'], estado_final)
                    print(f"   [OK] Estado final marcado: {estado_final}")

                # 4. Mostrar resumen
                print("\n" + "=" * 60)
                print("[EMOJI] RESUMEN DE LA CONVERSACIÓN:")
                print(f"[EMOJI] Conclusión: {agente.lead_data['pregunta_7']} ({agente.lead_data['resultado']})")
                print(json.dumps(agente.obtener_resumen(), indent=2, ensure_ascii=False))
                print("=" * 60)

            except Exception as e:
                print(f"   [ERROR] Error al guardar en Sheets: {e}")

            # Continuar automáticamente con el siguiente contacto (sin preguntar)
            print(f"\n[EMOJI] Continuando automáticamente con el siguiente contacto...\n")

        # Fin del bucle while
        print("\n" + "=" * 60)
        print("[OK] PROCESO COMPLETADO")
        print(f"   Total procesados: {contactos_procesados}")
        print("=" * 60 + "\n")

    except Exception as e:
        print(f"\n[ERROR] Error en el proceso automático: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    print("\n[WARN]  NOTA: Asegúrate de configurar las API keys en variables de entorno:")
    print("   - OPENAI_API_KEY")
    print("   - ELEVENLABS_API_KEY")
    print("   - ELEVENLABS_VOICE_ID\n")

    # Mostrar opciones
    print("=" * 60)
    print("MODO DE EJECUCIÓN")
    print("=" * 60)
    print("1. Demo interactiva (sin Google Sheets)")
    print("2. Procesar contactos desde Google Sheets (AUTOMÁTICO)")
    print("=" * 60)

    modo = input("\nSelecciona modo (1 o 2): ").strip()

    if modo == "2":
        procesar_contactos_automaticamente()
    else:
        demo_interactiva()
