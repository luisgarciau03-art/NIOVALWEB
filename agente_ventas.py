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
    print("🔧 Modo: GitHub Models (Gratis - Para pruebas)")
    openai_client = OpenAI(
        base_url="https://models.inference.ai.azure.com",
        api_key=GITHUB_TOKEN
    )
else:
    print("🚀 Modo: OpenAI Directo (Producción)")
    openai_client = OpenAI(api_key=OPENAI_API_KEY)

elevenlabs_client = ElevenLabs(api_key=ELEVENLABS_API_KEY)

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

    # Reemplazar cada palabra por su dígito
    for palabra, digito in numeros_palabras.items():
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

        # FIX 339: Estado de conversación para evitar respuestas incoherentes
        self.estado_conversacion = EstadoConversacion.INICIO
        self.estado_anterior = None  # Para tracking de transiciones

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

    def _actualizar_estado_conversacion(self, mensaje_cliente: str, respuesta_bruce: str = None):
        """
        FIX 339: Actualiza el estado de la conversación basándose en el mensaje del cliente
        y opcionalmente en la respuesta de Bruce.

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
                print(f"📊 FIX 339: Estado → DICTANDO_NUMERO (cliente dictando: {len(digitos_encontrados)} dígitos)")
                return

        # Detectar si cliente está dictando correo (contiene @ o "arroba")
        if '@' in mensaje_lower or 'arroba' in mensaje_lower or 'punto com' in mensaje_lower:
            self.estado_conversacion = EstadoConversacion.DICTANDO_CORREO
            print(f"📊 FIX 339: Estado → DICTANDO_CORREO")
            return

        # Detectar si cliente pide esperar
        patrones_espera = ['permítame', 'permitame', 'espere', 'espéreme', 'espereme',
                          'un momento', 'un segundito', 'ahorita', 'tantito']
        if any(p in mensaje_lower for p in patrones_espera):
            # Verificar que NO sea negación ("no está ahorita")
            if not any(neg in mensaje_lower for neg in ['no está', 'no esta', 'no se encuentra']):
                self.estado_conversacion = EstadoConversacion.ESPERANDO_TRANSFERENCIA
                print(f"📊 FIX 339: Estado → ESPERANDO_TRANSFERENCIA")
                return

        # Detectar si encargado no está
        patrones_no_esta = ['no está', 'no esta', 'no se encuentra', 'salió', 'salio',
                           'no hay', 'no lo encuentro', 'no los encuentro', 'no tiene horario']
        if any(p in mensaje_lower for p in patrones_no_esta):
            self.estado_conversacion = EstadoConversacion.ENCARGADO_NO_ESTA
            print(f"📊 FIX 339: Estado → ENCARGADO_NO_ESTA")
            return

        # Detectar si ya capturamos contacto
        if self.lead_data.get("whatsapp") or self.lead_data.get("email"):
            self.estado_conversacion = EstadoConversacion.CONTACTO_CAPTURADO
            print(f"📊 FIX 339: Estado → CONTACTO_CAPTURADO")
            return

        # Si la respuesta de Bruce pregunta por WhatsApp/correo
        if respuesta_bruce:
            respuesta_lower = respuesta_bruce.lower()
            if 'whatsapp' in respuesta_lower and '?' in respuesta_lower:
                self.estado_conversacion = EstadoConversacion.PIDIENDO_WHATSAPP
                print(f"📊 FIX 339: Estado → PIDIENDO_WHATSAPP")
            elif 'correo' in respuesta_lower and '?' in respuesta_lower:
                self.estado_conversacion = EstadoConversacion.PIDIENDO_CORREO
                print(f"📊 FIX 339: Estado → PIDIENDO_CORREO")
            elif 'encargado' in respuesta_lower and '?' in respuesta_lower:
                self.estado_conversacion = EstadoConversacion.BUSCANDO_ENCARGADO
                print(f"📊 FIX 339: Estado → BUSCANDO_ENCARGADO")

    def _cliente_esta_dictando(self) -> bool:
        """
        FIX 339: Verifica si el cliente está en proceso de dictar número o correo.
        Útil para saber si debemos esperar más tiempo antes de responder.
        """
        return self.estado_conversacion in [
            EstadoConversacion.DICTANDO_NUMERO,
            EstadoConversacion.DICTANDO_CORREO
        ]

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

    def _filtrar_respuesta_post_gpt(self, respuesta: str) -> str:
        """
        FIX 226: Filtro POST-GPT para forzar reglas que GPT no sigue consistentemente.

        Problemas que resuelve:
        1. Bruce repite el correo del cliente (riesgo de errores)
        2. Bruce pregunta WhatsApp después de ya tener el correo
        3. Bruce dice cosas sin sentido o números aleatorios

        Args:
            respuesta: Respuesta generada por GPT

        Returns:
            Respuesta filtrada/corregida
        """
        import re

        respuesta_lower = respuesta.lower()
        respuesta_original = respuesta
        filtro_aplicado = False

        # FIX 338: Definir contexto_cliente GLOBAL para todos los filtros
        # Incluir últimos 6 mensajes del cliente para mejor detección
        ultimos_mensajes_cliente_global = [
            msg['content'].lower() for msg in self.conversation_history[-12:]
            if msg['role'] == 'user'
        ]
        contexto_cliente = ' '.join(ultimos_mensajes_cliente_global[-6:]) if ultimos_mensajes_cliente_global else ""

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

            # FIX 325: Detectar si cliente PIDE información por correo/WhatsApp
            # En ese caso, NO preguntar por encargado - pedir el dato de contacto
            cliente_pide_info_contacto = any(frase in ultimo_cliente for frase in [
                'por correo', 'por whatsapp', 'por wasa', 'enviar la información',
                'enviar la informacion', 'mandar la información', 'mandar la informacion',
                'me puedes enviar', 'me puede enviar', 'envíame', 'enviame',
                'mándame', 'mandame', 'enviarme', 'mandarme'
            ])

            if not rechazo_real or es_solo_gracias:
                tipo_problema = "asume cosas" if bruce_asume_cosas else "despedida prematura"
                print(f"\n🚨 FIX 298/301: CRÍTICO - Bruce {tipo_problema}")
                print(f"   Mensajes de Bruce: {num_mensajes_bruce} (< 4)")
                print(f"   Tiene contacto: {tiene_contacto}")
                print(f"   Último cliente: '{ultimo_cliente[:50]}'")
                print(f"   Bruce iba a decir: '{respuesta[:60]}...'")

                # FIX 325: Si cliente pidió info por correo/WhatsApp, pedir el dato
                if cliente_pide_info_contacto:
                    if 'por correo' in ultimo_cliente:
                        respuesta = "Claro, con gusto. ¿Me puede proporcionar su correo electrónico para enviarle el catálogo?"
                        print(f"   FIX 325: Cliente pidió por CORREO - pidiendo email")
                    else:
                        respuesta = "Claro, con gusto. ¿Me confirma su número de WhatsApp para enviarle el catálogo?"
                        print(f"   FIX 325: Cliente pidió por WHATSAPP - pidiendo número")
                else:
                    # Continuar la conversación normalmente
                    respuesta = "Claro. ¿Se encontrará el encargado o encargada de compras para brindarle información de nuestros productos?"
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
                    print(f"\n🚨 FIX 226/251: FILTRO ACTIVADO - Bruce intentó repetir correo")
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
                        print(f"\n🚨 FIX 252: FILTRO ACTIVADO - Bruce mencionó email capturado ('{usuario}')")
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
                        print(f"\n🚨 FIX 226: FILTRO ACTIVADO - Bruce pidió WhatsApp pero ya tiene correo")
                        print(f"   Respuesta original: \"{respuesta[:80]}...\"")
                        respuesta = "Perfecto, ya lo tengo registrado. Le llegará el catálogo en las próximas horas. Muchas gracias por su tiempo, que tenga excelente día."
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
                        print(f"\n🚨 FIX 226: FILTRO ACTIVADO - Bruce mencionó número aleatorio: {num}")
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
                    print(f"\n🚨 FIX 226: FILTRO ACTIVADO - Respuesta con repeticiones excesivas")
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

                # FIX 297: Si Bruce YA preguntó "¿me escucha?", NO volver a preguntar
                # En su lugar, continuar con la presentación
                if cliente_no_escucho:
                    if bruce_ya_pregunto_escucha:
                        # Ya preguntamos si escucha, ahora continuar con presentación
                        print(f"\n📞 FIX 297: Cliente sigue diciendo '{ultimo_cliente}' pero Bruce YA preguntó si escucha")
                        print(f"   Continuando con presentación normal en lugar de repetir '¿me escucha?'")
                        respuesta = "Le llamo de la marca NIOVAL, productos de ferretería. ¿Se encontrará el encargado de compras?"
                        filtro_aplicado = True
                        print(f"   Respuesta corregida: \"{respuesta}\"")
                    elif 'nioval' in respuesta_lower:
                        # Primera vez: confirmar presencia
                        print(f"\n📞 FIX 234: FILTRO ACTIVADO - Cliente no escuchó, dice '{ultimo_cliente}'")
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

                # FIX 249/256/261/318: Detectar negaciones/rechazos que invalidan "ahorita"
                # Si cliente dice "ahorita tenemos cerrado", NO es espera
                # FIX 318: "No, no está ahorita" - el encargado NO está
                patrones_negacion = [
                    r'cerrado', r'no\s+est[aá]', r'no\s+se\s+encuentra',
                    r'no\s+hay', r'no\s+tenemos', r'no\s+puede',
                    r'ocupado', r'no\s+disponible',
                    # FIX 318: Patrones más específicos para "no está ahorita"
                    r'no,?\s*no\s+est[aá]',  # "No, no está ahorita"
                    r'no\s+est[aá]\s+ahorita',  # "no está ahorita"
                    r'ahorita\s+no\s+est[aá]',  # "ahorita no está"
                    # FIX 256: Patrones específicos para encargado
                    r'(?:encargado|jefe|gerente).*(?:no\s+est[aá]|sali[oó]|se\s+fue)',
                    r'(?:no\s+est[aá]|sali[oó]|se\s+fue).*(?:encargado|jefe|gerente)',
                    r'ya\s+sali[oó]', r'se\s+fue', r'est[aá]\s+fuera',
                    # FIX 261: Patrones de horario de llegada (implica que ahora NO está)
                    r'(?:entra|llega|viene)\s+(?:a\s+las?|hasta\s+las?)\s*\d',
                    r'(?:entra|llega|viene)\s+(?:en\s+la\s+)?(?:tarde|mañana|noche)',
                    r'hasta\s+las?\s*\d',  # "hasta las 9"
                    r'(?:después|despues)\s+de\s+las?\s*\d',  # "después de las 9"
                    r'(?:m[aá]s\s+)?tarde',  # "más tarde"
                    r'(?:en\s+)?(?:un\s+)?rato',  # "en un rato"
                    r'(?:no\s+)?(?:tod[ao])?v[ií]a\s+no',  # "todavía no"
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

                # FIX 249: NO activar filtro si hay negación explícita
                if (cliente_pide_espera or cliente_pide_espera_contexto) and not tiene_negacion:
                    print(f"\n⏳ FIX 235/237/249/337: FILTRO ACTIVADO - Cliente pide esperar: '{ultimo_cliente}'")
                    respuesta = "Claro, espero."
                    filtro_aplicado = True
                    print(f"   Respuesta: \"{respuesta}\"")
                elif cliente_pide_espera and tiene_negacion:
                    print(f"\n🚫 FIX 249: NO activar espera - Cliente dice 'ahorita' pero con negación: '{ultimo_cliente}'")

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
                    print(f"\n👋 FIX 289: PERSONA NUEVA detectada después de transferencia")
                    print(f"   Cliente dice: '{ultimo_cliente}'")
                    print(f"   Bruce iba a decir: '{respuesta[:60]}...'")
                    # Re-presentarse brevemente
                    respuesta = "Sí, buen día. Soy Bruce de la marca NIOVAL, productos de ferretería. ¿Usted es el encargado de compras?"
                    filtro_aplicado = True
                    print(f"   Respuesta corregida: \"{respuesta}\"")

        # ============================================================
        # FILTRO 5C (FIX 291): Cliente menciona sucursal/matriz
        # Si GPT quiere despedirse pero cliente mencionó sucursal/matriz,
        # Bruce debe pedir el número de la matriz en lugar de colgar
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
                menciona_redireccion = any(
                    frase in contexto_cliente
                    for frase in ['sucursal', 'matriz', 'oficinas', 'corporativo', 'área de compras',
                                  'no es de compras', 'no compramos aquí', 'no compramos aqui',
                                  'ir a la', 'tendré que', 'tendre que', 'tendría que', 'tendria que']
                )

                # Detectar si GPT quiere despedirse/colgar por "número equivocado"
                bruce_quiere_despedirse = any(
                    frase in respuesta_lower
                    for frase in ['error con el número', 'error con el numero', 'número equivocado', 'numero equivocado',
                                  'disculpe las molestias', 'buen día', 'buen dia', 'hasta luego',
                                  'gracias por su tiempo', 'que tenga']
                )

                if menciona_redireccion and bruce_quiere_despedirse:
                    print(f"\n🏢 FIX 291: FILTRO ACTIVADO - Cliente mencionó sucursal/matriz")
                    print(f"   Contexto: '{contexto_cliente[:80]}...'")
                    print(f"   Bruce iba a despedirse: '{respuesta[:60]}...'")
                    respuesta = "Entiendo, las compras se manejan en la matriz. ¿Me podría proporcionar el número de la matriz o del área de compras?"
                    filtro_aplicado = True
                    print(f"   Respuesta corregida: \"{respuesta}\"")

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
                    print(f"\n📧 FIX 231: FILTRO ACTIVADO - Cliente quiere dar correo")
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
                ]

                cliente_dice_no_disponible = any(re.search(p, ultimo_cliente) for p in patrones_no_disponible)

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
                ])

                if cliente_dice_no_disponible and bruce_insiste_contacto:
                    print(f"\n🚫 FIX 254/255: FILTRO ACTIVADO - Cliente dijo NO DISPONIBLE pero Bruce insiste")
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
                        print(f"\n🎯 FIX 257: FILTRO ACTIVADO - Cliente ES el encargado")
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
                        print(f"\n🎯 FIX 262: FILTRO ACTIVADO - Cliente dice 'Dígame' (está listo)")
                        print(f"   Bruce preguntó: \"{ultimo_bruce[:60]}...\"")
                        print(f"   Cliente dijo: \"{ultimo_cliente[:60]}...\"")
                        print(f"   Bruce iba a decir: \"{respuesta[:60]}...\"")
                        respuesta = "Sí, buen día. Soy Bruce de la marca NIOVAL, productos de ferretería. ¿Usted es el encargado de compras?"
                        filtro_aplicado = True
                        print(f"   Respuesta corregida: \"{respuesta}\"")

        # ============================================================
        # FILTRO 15 (FIX 263): Evitar volver a preguntar por encargado cuando ya avanzamos
        # ============================================================
        if not filtro_aplicado:
            # Verificar si ya hablamos del catálogo/WhatsApp/correo (significa que ya pasamos esa etapa)
            ultimos_mensajes = [
                msg['content'].lower() for msg in self.conversation_history[-8:]
            ]

            # Detectar si ya se habló del catálogo/WhatsApp/correo
            conversacion_avanzada = any(
                any(kw in msg for kw in ['whatsapp', 'catálogo', 'catalogo', 'correo', 'email'])
                for msg in ultimos_mensajes
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

            if conversacion_avanzada and bruce_pregunta_encargado:
                print(f"\n🚫 FIX 263: FILTRO ACTIVADO - Bruce pregunta por encargado cuando ya avanzamos")
                print(f"   Bruce iba a decir: \"{respuesta[:80]}...\"")
                # Ofrecer continuar o despedirse
                respuesta = "Perfecto. ¿Hay algo más en lo que le pueda ayudar?"
                filtro_aplicado = True
                print(f"   Respuesta corregida: \"{respuesta}\"")

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
                        print(f"\n🚨 FIX 228/236/240: FILTRO ACTIVADO - Bruce intentó repetir saludo/presentación")
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
                        es_solo_saludo = any(frase in ultimo_cliente_msg for frase in [
                            "buen día", "buen dia", "buenos días", "buenos dias",
                            "buenas tardes", "buenas noches", "dígame", "digame",
                            "mande", "sí dígame", "si digame", "qué se le ofrece",
                            "que se le ofrece", "en qué le puedo", "en que le puedo",
                            "cómo le ayudo", "como le ayudo", "le puedo ayudar"
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
                        respuesta_negativa = any(palabra in ultimo_cliente_msg for palabra in [
                            "no está", "no esta", "salió", "salio", "no se encuentra",
                            "no hay", "no viene", "estaba", "cerrado"
                        ])

                        if es_solo_saludo:
                            # FIX 334: Cliente solo saluda u ofrece ayuda - continuar con presentación
                            respuesta = "Qué tal, le llamo de la marca NIOVAL para brindar información de nuestros productos ferreteros. ¿Se encontrará el encargado de compras?"
                            print(f"   FIX 334: Cliente solo saludó/ofreció ayuda - continuando presentación")
                        elif menciona_tiempo:
                            respuesta = "Perfecto, muchas gracias por la información. Le marco entonces. Que tenga excelente día."
                            print(f"   FIX 281: Cliente mencionó tiempo/día - usando despedida apropiada")
                        elif respuesta_negativa:
                            respuesta = "Entiendo. ¿A qué hora puedo llamar para contactarlo?"
                            print(f"   FIX 281: Cliente indicó ausencia - preguntando horario")
                        else:
                            respuesta = "¿Me escucha?"

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
                        print(f"\n🚫 FIX 263B/280: FILTRO ACTIVADO - Bruce repitiendo pregunta")
                        print(f"   Patrón repetido: '{patron}'")
                        print(f"   Bruce iba a decir: \"{respuesta[:80]}...\"")
                        # FIX 280/285: Reformular mejor según contexto
                        if bruce_pidio_correo or cliente_dando_info:
                            # Cliente está en medio de dar el correo
                            respuesta = "Perfecto, ya lo tengo registrado. Le llegará el catálogo en las próximas horas."
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
                        print(f"\n🚨 FIX 227/320: FILTRO ACTIVADO - Cliente dio horario pero Bruce no respondió")
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
                    print(f"\n📞 FIX 241: FILTRO ACTIVADO - Cliente ofrece teléfono/sucursal")
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
                    print(f"\n📍 FIX 242: FILTRO ACTIVADO - Cliente pregunta ubicación")
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
                patrones_quien_habla = [
                    r'(?:con\s+)?qui[eé]n\s+(?:tengo\s+el\s+gusto|hablo|me\s+habla|est[aá]s?)',  # "con quién hablo", "quién eres"
                    r'(?:cu[aá]l\s+es\s+)?(?:tu|su)\s+nombre',  # "cuál es tu nombre", "tu nombre"
                    r'c[oó]mo\s+(?:te\s+llamas?|se\s+llama)',  # "cómo te llamas", "cómo se llama"
                    r'(?:qui[eé]n\s+)?eres\s+(?:t[uú])?',  # "quién eres tú", "eres tú"
                    r'a\s+qui[eé]n\s+(?:hablo|tengo)',  # "a quién hablo"
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
                    print(f"\n👤 FIX 243/308: FILTRO ACTIVADO - Cliente pregunta quién habla")
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
                bruce_pidio_numero = any(
                    any(kw in msg_bruce for kw in [
                        'número', 'numero', 'teléfono', 'telefono', 'whatsapp',
                        'celular', 'dígame el número', 'digame el numero',
                        'cuál es el número', 'cual es el numero',
                        'me puede dar', 'me da el', 'cuál es su'
                    ])
                    for msg_bruce in mensajes_bruce
                )

                if bruce_pidio_numero and ultimo_cliente:
                    # FIX 276: Primero convertir números escritos a dígitos
                    # Ej: "catorce" -> "14", "sesenta y uno" -> "61"
                    ultimo_cliente_convertido = convertir_numeros_escritos_a_digitos(ultimo_cliente)

                    # Extraer dígitos del mensaje del cliente (después de conversión)
                    digitos = re.findall(r'\d', ultimo_cliente_convertido)
                    num_digitos = len(digitos)

                    print(f"\n🔢 FIX 245 DEBUG: Cliente dio número con {num_digitos} dígitos")
                    print(f"   Dígitos extraídos: {''.join(digitos)}")
                    print(f"   Mensaje completo: \"{ultimo_cliente[:80]}...\"")

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

                    # FIX 245: Validar número incompleto
                    if not numero_completo and num_digitos > 0 and not bruce_pide_repeticion:
                        print(f"\n📞 FIX 245/246: FILTRO ACTIVADO - Número incompleto ({num_digitos} dígitos)")
                        print(f"   Bruce iba a decir: \"{respuesta[:60]}...\"")

                        if num_digitos < 10:
                            respuesta = f"Disculpe, solo escuché {num_digitos} dígitos. ¿Me puede repetir el número completo? Son 10 dígitos."
                        else:  # num_digitos entre 11 y 11 (no es 10 ni 12)
                            respuesta = "Disculpe, me puede repetir el número completo? Creo que faltó un dígito."

                        filtro_aplicado = True
                        print(f"   Respuesta corregida: \"{respuesta}\"")

                    # FIX 247: Verificar número completo (repetirlo para confirmar)
                    elif numero_completo and num_digitos > 0 and not bruce_verifica_numero and not bruce_pide_repeticion:
                        print(f"\n✅ FIX 247: FILTRO ACTIVADO - Verificar número completo ({num_digitos} dígitos)")
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

                        respuesta = f"Perfecto, lo tengo anotado como {numero_formateado}, ¿es correcto?"
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
                    print(f"\n📱 FIX 258/259/266: FILTRO ACTIVADO - Cliente ofreció número/dirección pero Bruce NO lo pidió")
                    print(f"   Cliente dijo: \"{ultimo_cliente[:80]}...\"")
                    print(f"   Bruce iba a decir: \"{respuesta[:60]}...\"")
                    respuesta = "Perfecto, dígame su número por favor."
                    filtro_aplicado = True
                    print(f"   Respuesta corregida: \"{respuesta}\"")

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
                    print(f"\n🚫 FIX 295/300: FILTRO ACTIVADO - Bruce dice 'ya lo tengo' pero NO tiene contacto")
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
                    print(f"\n📱 FIX 310: FILTRO ACTIVADO - Cliente SOLICITA WhatsApp pero Bruce NO pidió número")
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
                cliente_ofrece_info = any(frase in contexto_cliente for frase in [
                    'si gusta le proporciono', 'si gusta le doy', 'le proporciono',
                    'le puedo proporcionar', 'le doy el número', 'le doy el numero',
                    'le paso el número', 'le paso el numero', 'le puedo dar',
                    'puedo darle', 'se lo proporciono', 'se lo doy',
                    'si quiere le doy', 'si quiere le paso'
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
                    print(f"\n📞 FIX 306: FILTRO ACTIVADO - Cliente OFRECE proporcionar contacto")
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
            ]

            cliente_es_sucursal = any(re.search(patron, contexto_cliente, re.IGNORECASE) for patron in patrones_sucursal)

            # Bruce se despide incorrectamente cuando debería pedir número de matriz
            bruce_se_despide = any(frase in respuesta_lower for frase in [
                'disculpe las molestias', 'error con el número', 'que tenga buen día',
                'que tenga excelente día', 'gracias por su tiempo', 'hasta luego',
                'buen día', 'buena tarde', 'disculpe la molestia'
            ])

            # FIX 309b/317: Bruce sigue insistiendo con catálogo/whatsapp sin pedir número matriz
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
                'llame en otro momento', 'llamar en otro momento'
            ])

            # Verificar que Bruce NO está pidiendo número de matriz
            bruce_pide_matriz = any(frase in respuesta_lower for frase in [
                'número de la matriz', 'numero de la matriz', 'número de matriz', 'numero de matriz',
                'área de compras', 'area de compras', 'número del área', 'numero del area',
                'número de las oficinas', 'numero de las oficinas', 'oficinas centrales'
            ])

            if cliente_es_sucursal and (bruce_se_despide or bruce_sigue_insistiendo) and not bruce_pide_matriz:
                print(f"\n🏢 FIX 309/309b: FILTRO ACTIVADO - Cliente indica que es SUCURSAL/PUNTO DE VENTA")
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
                'no te puedo', 'no le puedo', 'no cuento con'
            ]) or (contexto_cliente.strip() in ['no', 'no.', 'nel', 'nop', 'nope'])

            if bruce_pidio_numero_encargado and cliente_niega:
                print(f"\n📞 FIX 311: FILTRO ACTIVADO - Cliente niega número del encargado, ofrecer catálogo")
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
            cliente_dice_no_esta = any(frase in contexto_cliente for frase in [
                'no se encuentra', 'no está', 'no esta', 'salió', 'salio',
                'no lo tenemos', 'gusta dejar', 'dejar mensaje', 'dejar recado',
                'no está ahorita', 'no esta ahorita', 'ahorita no está', 'ahorita no esta'
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

            if cliente_dice_no_esta and bruce_ofrece_catalogo and not bruce_ya_pidio_numero:
                print(f"\n📞 FIX 311b: FILTRO ACTIVADO - Encargado no está, pedir número ANTES de catálogo")
                print(f"   Cliente dijo: \"{contexto_cliente[:60]}...\"")
                print(f"   Bruce iba a ofrecer catálogo: \"{respuesta[:60]}...\"")
                respuesta = "Entiendo. ¿Me podría proporcionar el número directo del encargado para contactarlo?"
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
            cliente_prefiere_correo = any(frase in contexto_cliente for frase in [
                'por correo', 'correo electrónico', 'correo electronico',
                'el correo', 'mi correo', 'email', 'mejor correo'
            ])

            cliente_prefiere_whatsapp = any(frase in contexto_cliente for frase in [
                'por whatsapp', 'por wasa', 'whatsapp', 'wasa',
                'mi whats', 'mejor whatsapp', 'mejor whats',
                'mandar por whatsapp', 'enviar por whatsapp',  # FIX 329
                'me podrás mandar', 'me podras mandar'  # FIX 329: "¿No me podrás mandar por WhatsApp?"
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
                print(f"\n📧 FIX 315: FILTRO ACTIVADO - Cliente prefiere CORREO pero Bruce pide WhatsApp")
                print(f"   Cliente dijo: \"{contexto_cliente[:60]}...\"")
                print(f"   Bruce iba a pedir WhatsApp: \"{respuesta[:60]}...\"")
                respuesta = "Perfecto, dígame el correo y lo anoto."
                filtro_aplicado = True
                print(f"   Respuesta corregida: \"{respuesta}\"")

            elif cliente_prefiere_whatsapp and bruce_pide_correo:
                print(f"\n📱 FIX 315: FILTRO ACTIVADO - Cliente prefiere WHATSAPP pero Bruce pide correo")
                print(f"   Cliente dijo: \"{contexto_cliente[:60]}...\"")
                print(f"   Bruce iba a pedir correo: \"{respuesta[:60]}...\"")
                respuesta = "Perfecto. ¿Me confirma su número de WhatsApp para enviarle el catálogo?"
                filtro_aplicado = True
                print(f"   Respuesta corregida: \"{respuesta}\"")

            # FIX 329: Cliente ya dijo WhatsApp pero Bruce pregunta "WhatsApp o correo"
            elif cliente_prefiere_whatsapp and bruce_pregunta_ambas:
                print(f"\n📱 FIX 329: FILTRO ACTIVADO - Cliente YA dijo WhatsApp pero Bruce pregunta ambas opciones")
                print(f"   Cliente dijo: \"{contexto_cliente[:60]}...\"")
                print(f"   Bruce iba a preguntar: \"{respuesta[:60]}...\"")
                respuesta = "Perfecto. ¿Me confirma su número de WhatsApp para enviarle el catálogo?"
                filtro_aplicado = True
                print(f"   Respuesta corregida: \"{respuesta}\"")

            # FIX 329: Cliente ya dijo correo pero Bruce pregunta "WhatsApp o correo"
            elif cliente_prefiere_correo and bruce_pregunta_ambas:
                print(f"\n📧 FIX 329: FILTRO ACTIVADO - Cliente YA dijo correo pero Bruce pregunta ambas opciones")
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
                print(f"\n📞 FIX 330/332/335: FILTRO ACTIVADO - Cliente ofrece número pero Bruce ignora")
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

            # FIX 323b: Palabras neutrales que NO cuentan como "información"
            palabras_neutrales = saludos_simples + [
                'sí', 'si', 'alo', 'aló', 'bueno', 'en', 'qué', 'que', 'le', 'puedo',
                'ayudar', 'cómo', 'como', 'mande', 'diga', 'se', 'ofrece', 'a'
            ]
            cliente_solo_saluda = all(
                any(saludo in palabra for saludo in palabras_neutrales)
                for palabra in historial_cliente.split()
            ) if historial_cliente else True

            # FIX 323/323b: Si cliente saluda/ofrece ayuda Y Bruce intenta despedirse = ERROR
            if ((contexto_es_saludo or cliente_ofrece_ayuda) and contexto_es_corto and bruce_se_despide) or \
               (cliente_solo_saluda and bruce_se_despide and not tiene_contacto):
                print(f"\n🚨 FIX 316/323: FILTRO ACTIVADO - Cliente SALUDA/OFRECE AYUDA pero Bruce se DESPIDE")
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
            # FIX 341: Lista COMPLETA de patrones que indican que el encargado NO está
            patrones_no_esta = [
                'no está', 'no esta', 'no se encuentra', 'salió', 'salio',
                'no está ahorita', 'no esta ahorita', 'ahorita no está', 'ahorita no esta',
                'no, no está', 'no, no esta', 'no lo tenemos', 'se fue', 'no hay nadie',
                'ahorita no', 'ahorita no se', 'no los encuentro', 'no lo encuentro',
                'no la encuentro', 'no se sabe', 'no sabemos', 'no tienen horario',
                'no tiene horario', 'no sabría decirle', 'no sabria decirle',
                'está fuera', 'esta fuera', 'está ocupado', 'esta ocupado',
                'no viene hoy', 'no trabaja hoy', 'ya se fue'
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
                print(f"\n📞 FIX 341 CONSOLIDADO: Cliente dice NO ESTÁ pero Bruce responde mal")
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

            # FIX 327: Detectar específicamente "¿Quién habla?"
            cliente_pregunta_quien = any(frase in contexto_cliente for frase in [
                'quién habla', 'quien habla', 'quién llama', 'quien llama',
                'quién es', 'quien es', 'con quién hablo', 'con quien hablo'
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
                print(f"\n📞 FIX 322/342: FILTRO ACTIVADO - Cliente pregunta ORIGEN pero Bruce no responde")
                print(f"   Cliente preguntó: \"{contexto_cliente[:60]}...\"")
                print(f"   Bruce iba a decir: \"{respuesta[:60]}...\"")
                print(f"   No responde origen: {bruce_no_responde_origen}, Responde incoherente: {bruce_responde_incoherente}")
                respuesta = "Mi nombre es Bruce, me comunico de parte de la marca NIOVAL. Distribuimos productos de ferretería. ¿Se encontrará el encargado de compras?"
                filtro_aplicado = True
                print(f"   Respuesta corregida: \"{respuesta}\"")

            # FIX 327: Si preguntan específicamente "quién habla" y Bruce no dice su nombre
            elif cliente_pregunta_quien and (bruce_no_dice_nombre or bruce_responde_incoherente):
                print(f"\n📞 FIX 327/342: FILTRO ACTIVADO - Cliente pregunta QUIÉN HABLA pero Bruce no dice nombre")
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
            tiene_correo = hasattr(self, 'ultimo_correo_capturado') and self.ultimo_correo_capturado
            tiene_whatsapp = hasattr(self, 'ultimo_whatsapp_capturado') and self.ultimo_whatsapp_capturado

            # Buscar en historial si cliente dio algún dato
            historial_cliente = ' '.join([
                msg['content'].lower() for msg in self.conversation_history
                if msg['role'] == 'user'
            ])
            cliente_dio_correo = '@' in historial_cliente or 'arroba' in historial_cliente
            cliente_dio_whatsapp = any(c.isdigit() for c in historial_cliente) and len([c for c in historial_cliente if c.isdigit()]) >= 10

            tiene_dato_real = tiene_correo or tiene_whatsapp or cliente_dio_correo or cliente_dio_whatsapp

            if bruce_dice_registrado and not tiene_dato_real:
                print(f"\n🚨 FIX 322: FILTRO ACTIVADO - Bruce dice 'registrado' SIN tener dato")
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
                print(f"\n📱 FIX 324: FILTRO ACTIVADO - Cliente PIDE INFO pero Bruce pregunta por encargado")
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
            # Detectar si cliente indica usar el mismo número
            cliente_dice_este_numero = any(frase in contexto_cliente for frase in [
                'a este número nada más', 'a este numero nada mas',
                'sería a este número', 'seria a este numero',
                'sería este número', 'seria este numero',
                'a este número', 'a este numero',
                'por este número', 'por este numero',
                'este mismo número', 'este mismo numero',
                'al mismo número', 'al mismo numero',
                'a este nada más', 'a este nada mas'
            ])

            # Bruce pide número cuando ya le dijeron que use el mismo
            bruce_pide_numero = any(frase in respuesta_lower for frase in [
                'cuál es su número', 'cual es su numero',
                'me puede repetir', 'me puede proporcionar',
                'solo escuché', 'solo escuche',
                'dígitos', 'digitos'
            ])

            if cliente_dice_este_numero and bruce_pide_numero:
                print(f"\n📞 FIX 336: FILTRO ACTIVADO - Cliente dice 'a este número' pero Bruce pide número")
                print(f"   Cliente dijo: \"{contexto_cliente[:80]}...\"")
                print(f"   Bruce iba a pedir: \"{respuesta[:60]}...\"")
                respuesta = "Perfecto, entonces le envío el catálogo a este mismo número por WhatsApp. Muchas gracias por su tiempo, que tenga excelente día."
                filtro_aplicado = True
                print(f"   Respuesta corregida: \"{respuesta}\"")

        # ============================================================
        # FILTRO 28 (FIX 345): Cliente ofrece correo pero Bruce responde incoherente
        # Ejemplo: "Te comparto un correo" → "Perfecto. ¿Hay algo más?"
        # Esto es INCORRECTO - Bruce debe pedir el correo
        # ============================================================
        if not filtro_aplicado:
            # Detectar si cliente ofrece dar correo
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
                'para que mande', 'para que mandes'
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
                print(f"\n📧 FIX 345: FILTRO ACTIVADO - Cliente ofrece correo pero Bruce responde incoherente")
                print(f"   Cliente dijo: \"{contexto_cliente[:80]}...\"")
                print(f"   Bruce iba a decir: \"{respuesta[:60]}...\"")
                respuesta = "Claro, dígame su correo electrónico por favor."
                filtro_aplicado = True
                print(f"   Respuesta corregida: \"{respuesta}\"")

        if filtro_aplicado:
            print(f"✅ FIX 226-341: Filtro post-GPT aplicado exitosamente")

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
            contexto_partes.append(f"\n🔥 IMPORTANTE - REFERENCIA:")
            contexto_partes.append(f"- {self.contacto_info['referencia']}")
            contexto_partes.append(f"- Usa esta información en tu SALUDO INICIAL para generar confianza")
            contexto_partes.append(f"- Ejemplo: 'Hola, mi nombre es Bruce W. Me pasó su contacto [NOMBRE DEL REFERIDOR] de [EMPRESA]. Él me comentó que usted...'")

        # CONTEXTO DE REPROGRAMACIÓN - Si hubo llamadas previas (columna W)
        if self.contacto_info.get('contexto_reprogramacion'):
            contexto_partes.append(f"\n📞 LLAMADA REPROGRAMADA:")
            contexto_partes.append(f"- {self.contacto_info['contexto_reprogramacion']}")
            contexto_partes.append(f"- Menciona que ya habían hablado antes y retomas la conversación")
            contexto_partes.append(f"- Ejemplo: 'Hola, qué tal. Como le había comentado la vez pasada, me comunico nuevamente...'")

            # Si el contexto indica que este número ES del encargado, agregar advertencia CRÍTICA
            contexto_lower = self.contacto_info['contexto_reprogramacion'].lower()
            if any(keyword in contexto_lower for keyword in ['encargado', 'dio número', 'dio numero', 'contacto del']):
                contexto_partes.append(f"\n⚠️ CRÍTICO: Este número FUE PROPORCIONADO como el del ENCARGADO DE COMPRAS")
                contexto_partes.append(f"- NO preguntes 'se encuentra el encargado' - YA ESTÁS HABLANDO CON ÉL")
                contexto_partes.append(f"- Saluda directamente y pide su nombre: '¿Con quién tengo el gusto?'")

        if len(contexto_partes) > 1:  # Más que solo el header
            contexto_partes.append("\n🔒 Recuerda: NO preguntes nada de esta información, ya la tienes.")
            return "\n".join(contexto_partes)

        return ""
    
    def procesar_respuesta(self, respuesta_cliente: str) -> str:
        """
        Procesa la respuesta del cliente y genera una respuesta del agente

        Args:
            respuesta_cliente: Lo que dijo el cliente

        Returns:
            Respuesta del agente
        """
        # Agregar respuesta del cliente al historial
        self.conversation_history.append({
            "role": "user",
            "content": respuesta_cliente
        })

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
            emoji = "🚨" if resultado_ivr["es_ivr"] else "⚠️"
            print(f"\n{emoji} FIX 202: Análisis IVR")
            print(f"   Confianza: {resultado_ivr['confianza']:.0%}")
            print(f"   Acción: {resultado_ivr['accion'].upper()}")
            print(f"   Razón: {resultado_ivr['razon']}")
            if resultado_ivr['categorias']:
                print(f"   Categorías: {', '.join(resultado_ivr['categorias'])}")

        # Si se detectó IVR con alta confianza → Colgar inmediatamente
        if resultado_ivr["accion"] == "colgar":
            print(f"\n🚨🚨🚨 FIX 202: IVR/CONTESTADORA DETECTADO 🚨🚨🚨")
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
            print(f"🚨 FIX 196: Objeción corta detectada: '{respuesta_cliente}' - continuando conversación")

            # Agregar contexto para que GPT maneje la objeción apropiadamente
            self.conversation_history.append({
                "role": "system",
                "content": f"[SISTEMA] Cliente dijo '{respuesta_cliente}' (objeción/duda/interrupción). Responde apropiadamente: si es 'pero' pide que continúe ('¿Sí, dígame?'), si es 'espera' confirma que esperas, si es 'no' pregunta qué duda tiene, si es 'qué/mande/cómo' repite brevemente lo último que dijiste."
            })

            print(f"   ✅ FIX 196: Contexto agregado para GPT - manejará objeción corta")

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
            casos_validos = [
                "así no, no", "ahorita no, no", "ahora no, no",
                "todavía no, no", "pues no, no", "no sé, no",
                "creo que no, no", "por ahora no, no"
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
            print(f"⚠️ FIX 129: Posible error Whisper detectado: {', '.join(razones)}")

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
                        "content": f"""[SISTEMA - FIX 198 NIVEL 1] 🚨 ERROR CRÍTICO DE TRANSCRIPCIÓN

El cliente dijo algo pero la transcripción no tiene sentido: "{respuesta_cliente}"

⚠️ CONTEXTO:
Tu último mensaje: {ultimo_mensaje_bruce[:80] if ultimo_mensaje_bruce else 'N/A'}

🎯 ACCIÓN REQUERIDA:
Pide cortésmente que repita: "Disculpe, no le escuché bien por la línea, ¿me lo podría repetir?"

❌ NO menciones palabras de la transcripción errónea
❌ NO repitas tu pregunta anterior textualmente (usa palabras diferentes)
✅ SÍ usa frase genérica de "no escuché bien"
✅ SÍ mantén tono profesional y cortés
"""
                    })
                    print(f"🚨 FIX 198 NIVEL 1: Error crítico Whisper → pedir repetir")

                elif estaba_pidiendo_dato:
                    # NIVEL 2: ERROR PARCIAL EN DATO → Intentar interpretar PRIMERO
                    self.conversation_history.append({
                        "role": "system",
                        "content": f"""[SISTEMA - FIX 198 NIVEL 2] ⚠️ ERROR PARCIAL EN DATO SOLICITADO

Estabas pidiendo: {ultimo_mensaje_bruce[:50]}...
Cliente respondió (con posibles errores): "{respuesta_cliente}"

🎯 ESTRATEGIA DE 3 PASOS:

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

❌ NO digas "ya lo tengo" si NO lo tienes completo
❌ NO repitas palabras erróneas al cliente
✅ SÍ confirma el dato si lo interpretaste parcialmente
✅ SÍ pide repetir SOLO si interpretación es <70%
✅ SÍ mantén tono profesional (no hagas sentir mal al cliente)
"""
                    })
                    print(f"⚠️ FIX 198 NIVEL 2: Error parcial en dato → intentar interpretar")

                else:
                    # NIVEL 3: ERROR LEVE → Interpretar intención y continuar
                    self.conversation_history.append({
                        "role": "system",
                        "content": f"""[SISTEMA - FIX 198 NIVEL 3] ℹ️ ERROR LEVE DE TRANSCRIPCIÓN

Cliente respondió (con errores leves): "{respuesta_cliente}"

🎯 ESTRATEGIA:
1. Interpreta la INTENCIÓN general (positivo/negativo/pregunta/duda)
2. Continúa la conversación basándote en la intención
3. NO menciones las palabras erróneas
4. NO pidas repetir por errores leves

Ejemplo de interpretación:
- Transcripción: "oc, así a ver" → Intención: Confirmación positiva ("ok, sí, a ver")
- Transcripción: "pero no sé" → Intención: Duda/inseguridad
- Transcripción: "y eso que es" → Intención: Pregunta de aclaración

❌ NO preguntes sobre palabras sin sentido
❌ NO pidas repetir (es error leve, intención es clara)
❌ NO hagas sentir al cliente que no lo entiendes
✅ SÍ continúa la conversación fluidamente
✅ SÍ responde basándote en la intención general
✅ SÍ mantén naturalidad en la conversación
"""
                    })
                    print(f"✅ FIX 198 NIVEL 3: Error leve → interpretar intención y continuar")

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
                            "content": f"""[SISTEMA - FIX 184] 🚨 CLIENTE ESTÁ DELETREANDO CORREO - NO INTERRUMPIR

El cliente está DELETREANDO su correo electrónico: "{respuesta_cliente}"

⚠️ CRÍTICO:
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
                        print(f"🔄 FIX 184: Cliente DELETREANDO correo - NO INTERRUMPIR")
                    else:
                        # Cliente está respondiendo pregunta normal
                        self.conversation_history.append({
                            "role": "system",
                            "content": f"""[SISTEMA - FIX 182] ⚠️ CLIENTE ESTÁ RESPONDIENDO TU PREGUNTA

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
                        print(f"🔄 FIX 182: Cliente respondiendo pregunta - usando continuidad simple")
                else:
                    # Interrupción corta durante PRESENTACIÓN
                    self.conversation_history.append({
                        "role": "system",
                        "content": f"""[SISTEMA - FIX 128/182] ⚠️ INTERRUPCIÓN EN PRESENTACIÓN

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
                    print(f"🔄 FIX 128/182: Interrupción en presentación - forzando uso de nexo")

        # FIX 75/81: DETECCIÓN TEMPRANA DE OBJECIONES - Terminar ANTES de llamar GPT
        # CRÍTICO: Detectar CUALQUIER mención de proveedor exclusivo/Truper y COLGAR

        # FIX 81: DEBUG - Imprimir SIEMPRE para verificar que este código se ejecuta
        print(f"🔍 FIX 81 DEBUG: Verificando objeciones en: '{respuesta_cliente[:80]}'")

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
                print(f"🚨🚨🚨 FIX 75: OBJECIÓN TERMINAL DETECTADA - COLGANDO INMEDIATAMENTE")
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
        print(f"✅ FIX 81 DEBUG: NO se detectó objeción terminal. Continuando conversación normal.")

        # FIX 170/237: Detectar cuando cliente va a PASAR al encargado (AHORA)
        # Estas frases indican transferencia INMEDIATA, NO futura
        patrones_transferencia_inmediata = [
            # Transferencia directa
            "te puedo pasar", "te paso", "le paso", "se lo paso",
            "te lo paso", "ahorita te lo paso", "te comunico",
            "me lo comunica", "me lo pasa", "pásamelo",
            # FIX 237: Solicitud de espera - agregados más patrones
            "dame un momento", "espera un momento", "espérame", "un segundito",
            "permíteme", "permiteme", "déjame ver", "dejame ver",
            "un momento",  # FIX 237: Solo "un momento" sin prefijo
            "un segundo",  # FIX 237
            "tantito",     # FIX 237: Mexicanismo
            "ahorita",     # FIX 237: Cuando dice solo "ahorita" (va a hacer algo)
            "me permite",  # FIX 237
            "me permites", # FIX 237
            # Confirmación de disponibilidad + acción
            "sí está aquí", "está aquí", "está disponible",
            "ya viene", "ahorita viene", "está por aquí"
        ]

        # FIX 216/318: Patrones que INVALIDAN la transferencia (negaciones)
        # Si el cliente dice "NO está disponible", NO es transferencia
        patrones_negacion = [
            "no está disponible", "no esta disponible",
            "no está aquí", "no esta aquí", "no esta aqui",
            "no se encuentra", "no lo encuentro", "no la encuentro",
            "no viene", "no va a venir", "no puede", "no hay nadie",
            # FIX 318: "no está ahorita" - el encargado NO está
            "no está ahorita", "no esta ahorita",
            "ahorita no está", "ahorita no esta",
            "no, no está", "no, no esta"
        ]

        # FIX 229: Patrones que indican que el cliente va a DAR INFORMACIÓN (NO transferencia)
        # "Le paso el correo" = cliente va a dar correo, NO pasar al encargado
        patrones_dar_info = [
            "paso el correo", "paso mi correo", "paso un correo",
            "doy el correo", "doy mi correo", "le doy el correo",
            "paso el mail", "paso mi mail", "paso el email",
            "te paso el número", "le paso el número", "paso mi número",
            "te paso el whatsapp", "le paso el whatsapp", "paso mi whatsapp",
            "te lo paso por correo", "se lo paso por correo",
            "anota", "apunta", "toma nota",
        ]

        # FIX 229: Verificar si cliente va a dar información
        cliente_da_info = any(info in respuesta_lower for info in patrones_dar_info)

        # FIX 216: Primero verificar si hay negación
        hay_negacion = any(neg in respuesta_lower for neg in patrones_negacion)

        if hay_negacion:
            print(f"🚫 FIX 216: Detectada NEGACIÓN - NO es transferencia")
            print(f"   Respuesta cliente: '{respuesta_cliente[:100]}'")
            # NO retornar "Claro, espero" - continuar con flujo normal
        elif cliente_da_info:
            print(f"📧 FIX 229: Cliente va a DAR INFORMACIÓN - NO es transferencia")
            print(f"   Respuesta cliente: '{respuesta_cliente[:100]}'")
            # NO retornar "Claro, espero" - dejar que GPT pida el correo/dato
        else:
            for patron in patrones_transferencia_inmediata:
                if patron in respuesta_lower:
                    print(f"📞 FIX 170: Cliente va a PASAR al encargado AHORA")
                    print(f"   Patrón detectado: '{patron}'")
                    print(f"   Respuesta cliente: '{respuesta_cliente[:100]}'")

                    # Marcar flag de transferencia
                    self.esperando_transferencia = True

                    # Respuesta simple de espera
                    respuesta_espera = "Claro, espero."

                    self.conversation_history.append({
                        "role": "assistant",
                        "content": respuesta_espera
                    })

                    print(f"✅ FIX 170: Bruce esperará (timeout extendido a 20s)")
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
                print(f"\n📞 FIX 238: ENCARGADO LLEGÓ después de esperar")
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

                print(f"✅ FIX 238: Bruce se presenta al encargado")
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

            # Solo agregar al historial si hay respuesta (no vacía)
            if respuesta_agente:
                self.conversation_history.append({
                    "role": "assistant",
                    "content": respuesta_agente
                })

            return respuesta_agente

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
                print(f"🔧 FIX 68: Historial limitado a últimos {MAX_MENSAJES_CONVERSACION} mensajes")

            # 4. Debug: Imprimir últimos 2 mensajes para diagnóstico
            if len(mensajes_conversacion) >= 2:
                print(f"\n📝 FIX 68: Últimos 2 mensajes en historial:")
                for msg in mensajes_conversacion[-2:]:
                    preview = msg['content'][:60] + "..." if len(msg['content']) > 60 else msg['content']
                    print(f"   {msg['role'].upper()}: {preview}")

            response = openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": prompt_optimizado},
                    *mensajes_conversacion
                ],
                temperature=0.7,
                max_tokens=80,  # FIX 197: CRÍTICO - Reducido de 100 a 80 (respuestas ULTRA-concisas, target <4seg total)
                presence_penalty=0.6,
                frequency_penalty=1.5,  # FIX 74: CRÍTICO - Aumentado de 1.2 a 1.5 (penalización MÁXIMA de repeticiones)
                timeout=2.8,  # FIX 197: CRÍTICO - Reducido de 3.5s a 2.8s (target 4-5s total con ElevenLabs)
                stream=False,
                top_p=0.9  # FIX 55: Reducir diversidad para respuestas más rápidas
            )

            duracion_gpt = time.time() - inicio_gpt

            # FIX 163: Si GPT tardó más de 3 segundos, agregar frase de relleno ANTES de la respuesta
            frase_relleno = ""
            if duracion_gpt > 3.0:
                frase_relleno = self._obtener_frase_relleno(duracion_gpt)
                print(f"⏱️ FIX 163: GPT tardó {duracion_gpt:.1f}s - agregando frase de relleno: '{frase_relleno}'")

            respuesta_agente = response.choices[0].message.content

            # Si hay frase de relleno, agregarla al inicio de la respuesta
            if frase_relleno:
                respuesta_agente = f"{frase_relleno} {respuesta_agente}"

            # ============================================================
            # FIX 226: FILTRO POST-GPT - Forzar reglas que GPT no sigue
            # ============================================================
            respuesta_agente = self._filtrar_respuesta_post_gpt(respuesta_agente)

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

            # Verificar si esta respuesta ya se dijo en las últimas 3 respuestas
            repeticion_detectada = False
            for i, resp_previa in enumerate(ultimas_respuestas_bruce[-3:], 1):
                resp_previa_normalizada = re.sub(r'[^\w\s]', '', resp_previa.lower()).strip()

                # Si la respuesta es >80% similar (o idéntica)
                if respuesta_normalizada == resp_previa_normalizada:
                    repeticion_detectada = True
                    print(f"\n🚨🚨🚨 FIX 204: REPETICIÓN IDÉNTICA DETECTADA 🚨🚨🚨")
                    print(f"   Bruce intentó repetir: \"{respuesta_agente[:60]}...\"")
                    print(f"   Ya se dijo hace {i} respuesta(s)")
                    print(f"   → Modificando respuesta para evitar repetición")
                    break

            if repeticion_detectada:
                # Modificar la respuesta para que GPT genere algo diferente
                self.conversation_history.append({
                    "role": "system",
                    "content": f"""🚨 [SISTEMA - FIX 204] REPETICIÓN DETECTADA

Estabas a punto de decir EXACTAMENTE lo mismo que ya dijiste antes:
"{respuesta_agente[:100]}..."

🛑 NO repitas esto. El cliente YA lo escuchó.

✅ OPCIONES VÁLIDAS:
1. Si el cliente no respondió tu pregunta: Reformula de manera DIFERENTE
2. Si el cliente está ocupado: Ofrece despedirte o llamar después
3. Si no te entiende: Usa palabras más simples

💡 EJEMPLO DE REFORMULACIÓN:
ORIGINAL: "¿Le gustaría que le envíe el catálogo por WhatsApp?"
REFORMULADO: "¿Tiene WhatsApp donde le pueda enviar información?"
REFORMULADO 2: "¿Prefiere que le llame en otro momento?"

Genera una respuesta COMPLETAMENTE DIFERENTE ahora."""
                })

                # Regenerar respuesta con contexto de no repetir
                print(f"🔄 FIX 204: Regenerando respuesta sin repetición...")
                try:
                    response_reintento = openai_client.chat.completions.create(
                        model="gpt-4o",
                        messages=self.conversation_history,
                        temperature=0.9,  # Más creatividad para evitar repetición
                        max_tokens=80,
                        presence_penalty=0.8,  # Penalizar tokens ya usados
                        frequency_penalty=2.0,  # MÁXIMA penalización de repeticiones
                        timeout=2.8,
                        stream=False,
                        top_p=0.9
                    )

                    respuesta_agente = response_reintento.choices[0].message.content
                    print(f"✅ FIX 204: Nueva respuesta generada: \"{respuesta_agente[:60]}...\"")

                except Exception as e:
                    print(f"⚠️ FIX 204: Error al regenerar, usando despedida genérica")
                    respuesta_agente = "Entiendo. ¿Prefiere que le llame en otro momento más conveniente?"

            # Agregar al historial
            self.conversation_history.append({
                "role": "assistant",
                "content": respuesta_agente
            })

            return respuesta_agente

        except Exception as e:
            # FIX 305/307: Logging detallado del error para diagnóstico
            import traceback
            print(f"\n🚨🚨🚨 FIX 305: EXCEPCIÓN EN GPT 🚨🚨🚨")
            print(f"   Error: {type(e).__name__}: {e}")
            print(f"   Traceback completo:")
            traceback.print_exc()
            # FIX 307: Variable correcta es respuesta_cliente
            print(f"   Último mensaje del cliente: {respuesta_cliente[:100] if respuesta_cliente else 'VACÍO'}")
            print(f"   Historial tiene {len(self.conversation_history)} mensajes")

            # FIX 305: En lugar de decir "problema técnico", dar una respuesta genérica pero útil
            # Esto evita que el cliente sienta que el sistema falló
            return "Perfecto. ¿Se encontrará el encargado o encargada de compras?"
    
    def texto_a_voz(self, texto: str, output_path: str = "respuesta.mp3"):
        """
        Convierte texto a voz usando ElevenLabs
        
        Args:
            texto: Texto a convertir
            output_path: Ruta donde guardar el audio
            
        Returns:
            Ruta del archivo de audio generado
        """
        try:
            # Genera el audio con ElevenLabs
            audio = elevenlabs_client.text_to_speech.convert(
                text=texto,
                voice_id=ELEVENLABS_VOICE_ID,
                model_id="eleven_multilingual_v2",
                voice_settings=VoiceSettings(
                    stability=0.50,
                    similarity_boost=0.80,
                    style=0.35
                )
            )
            
            # Guardar audio
            with open(output_path, "wb") as f:
                for chunk in audio:
                    f.write(chunk)
            
            return output_path
            
        except Exception as e:
            print(f"Error al generar voz: {e}")
            return None
    
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
            print(f"📝 FIX 72: Estado detectado: Buzón de voz - Frase: '{texto[:50]}'")
            return

        # FIX 24: Detección MÁS ESTRICTA de teléfono incorrecto
        # Frases completas que indican número equivocado
        frases_numero_incorrecto = [
            "numero incorrecto", "número incorrecto", "numero equivocado", "número equivocado",
            "no existe", "fuera de servicio", "no es aqui", "no es aquí",
            "se equivocó de número", "se equivoco de numero", "marcó mal", "marco mal",
            "no trabajo aqui", "no trabajo aquí", "no es el negocio", "no es mi negocio",
            "equivocado de numero", "equivocado de número", "llamó mal", "llamo mal",
            "no hay negocio", "aqui no es", "aquí no es", "no es aca", "no es acá",
            "esto no es una ferretería", "esto no es ferretería", "no vendemos",
            "no es este el número", "no es este número", "llamó al número equivocado",
            "se equivocó de teléfono", "marcó equivocado"
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
            print(f"📝 Estado detectado: Teléfono Incorrecto - '{texto[:50]}...'")
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
            print(f"📝 Estado detectado: Cliente colgó - '{texto[:50]}...'")
            return

        if any(palabra in texto_lower for palabra in ["no contesta", "no responde", "sin respuesta"]):
            self.lead_data["estado_llamada"] = "No Contesta"
            self.lead_data["pregunta_0"] = "No Contesta"
            self.lead_data["pregunta_7"] = "Nulo"
            self.lead_data["resultado"] = "NEGADO"
            print(f"📝 Estado detectado: No contesta")
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
                print(f"👤 CONFIRMADO: Cliente ES el encargado - '{texto[:50]}...'")

                # Agregar mensaje al sistema para que GPT NO vuelva a preguntar
                self.conversation_history.append({
                    "role": "system",
                    "content": """⚠️⚠️⚠️ CRÍTICO: El cliente acaba de confirmar que ÉL/ELLA ES el encargado de compras.

ACCIÓN INMEDIATA:
1. NO vuelvas a preguntar "¿Se encuentra el encargado?" NUNCA MÁS
2. NO preguntas por horario del encargado
3. NO pidas que te comuniquen con el encargado
4. Continúa la conversación DIRECTAMENTE con esta persona
5. 🚨 FIX 172: NO pidas el nombre (genera delays de audio)
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
            print(f"🚨 FIX 46: Cliente pregunta por MARCAS - '{texto[:60]}...'")

            self.conversation_history.append({
                "role": "system",
                "content": """🚨🚨🚨 ALERTA ULTRA-CRÍTICA: CLIENTE PREGUNTA POR MARCAS 🚨🚨🚨

El cliente está preguntando QUÉ MARCAS maneja NIOVAL.

⚠️⚠️⚠️ PROHIBICIONES ABSOLUTAS - NUNCA NUNCA NUNCA DIGAS:
❌ "Manejamos marcas reconocidas como Truper"
❌ "Trabajamos con Truper"
❌ "Distribuimos Truper"
❌ "Contamos con Pochteca"
❌ "Manejamos Pretul"
❌ "Trabajamos con marcas como [CUALQUIER NOMBRE DE MARCA EXTERNA]"
❌ "Tenemos Stanley, Dewalt, Urrea"
❌ NO MENCIONES NOMBRES DE MARCAS EXTERNAS

✅✅✅ RESPUESTAS OBLIGATORIAS - USA EXACTAMENTE:
✅ "Manejamos la marca NIOVAL, que es nuestra marca propia"
✅ "Trabajamos con nuestra propia línea de productos bajo la marca NIOVAL"
✅ "Al ser marca propia, ofrecemos mejores precios que marcas comerciales"
✅ "¿Le gustaría que le envíe el catálogo completo para que vea todos nuestros productos?"

NIOVAL ES UNA MARCA PROPIA - NO ES DISTRIBUIDOR DE OTRAS MARCAS.
TRUPER, POCHTECA, PRETUL = SON COMPETENCIA ❌❌❌

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
            print(f"😤 FIX 33: Cliente muestra FRUSTRACIÓN - '{texto[:60]}...'")

            self.conversation_history.append({
                "role": "system",
                "content": """⚠️⚠️⚠️ [SISTEMA] ALERTA: EL CLIENTE ESTÁ FRUSTRADO

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

❌ NO vuelvas a preguntar por NADA de lo de arriba
✅ AVANZA con la conversación usando la info que YA TIENES""".format(
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
            print(f"✋ FIX 31: Ya preguntaste por TAMAÑO DE NEGOCIO - NO volver a preguntar")

            self.conversation_history.append({
                "role": "system",
                "content": """⚠️⚠️⚠️ [SISTEMA] YA PREGUNTASTE POR TAMAÑO DE NEGOCIO

Detecté que YA preguntaste sobre el tamaño del negocio anteriormente.

❌ NO vuelvas a preguntar: "¿Qué tamaño de negocio tienen?"
❌ NO vuelvas a preguntar: "¿Si es ferretería local o distribuidora?"
✅ YA TIENES esta información en el contexto de la conversación
✅ AVANZA a la siguiente pregunta o tema

Si el cliente no respondió claramente la primera vez, está bien. NO insistas."""
            })

        if ya_pregunto_proveedores and not hasattr(self, 'flag_pregunta_proveedores_advertida'):
            self.flag_pregunta_proveedores_advertida = True
            print(f"✋ FIX 31: Ya preguntaste por PROVEEDORES - NO volver a preguntar")

            self.conversation_history.append({
                "role": "system",
                "content": """⚠️⚠️⚠️ [SISTEMA] YA PREGUNTASTE POR PROVEEDORES

Detecté que YA preguntaste sobre los proveedores actuales.

❌ NO vuelvas a preguntar: "¿Trabajan con varios proveedores?"
❌ NO vuelvas a preguntar: "¿Tienen uno principal?"
✅ YA TIENES esta información en el contexto de la conversación
✅ AVANZA a la siguiente pregunta o tema

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
                print(f"⚠️ FIX 198: Email '{email_actual}' YA fue mencionado en mensaje #{num_mensaje_anterior}")
                print(f"   Cliente está REPITIENDO el email (no es la primera vez)")

                self.conversation_history.append({
                    "role": "system",
                    "content": f"""⚠️⚠️⚠️ [SISTEMA] EMAIL DUPLICADO DETECTADO - FIX 198

El cliente acaba de mencionar el email: {email_actual}

🚨 IMPORTANTE: Este email YA fue proporcionado anteriormente en mensaje #{num_mensaje_anterior}

🎯 ACCIÓN REQUERIDA:
- ✅ Responde: "Perfecto, ya lo tengo anotado desde antes. Muchas gracias."
- ✅ NO pidas confirmación (ya lo tienes)
- ✅ NO digas "adelante con el correo" (ya te lo dieron)
- ✅ DESPIDE INMEDIATAMENTE

❌ NUNCA pidas el email de nuevo
❌ NUNCA digas "perfecto, adelante" (ya está adelante)
❌ NUNCA actúes como si fuera la primera vez

El cliente ya te dio este dato antes. Reconócelo y termina la llamada."""
                })
                print(f"   ✅ FIX 198: Contexto agregado para GPT - manejar email duplicado")
            else:
                # Primera vez que se menciona este email
                print(f"✅ FIX 198: Email '{email_actual}' es NUEVO - primera mención")

                self.conversation_history.append({
                    "role": "system",
                    "content": f"""✅ [SISTEMA] NUEVO EMAIL CAPTURADO

Email capturado: {email_actual}

❌ NO vuelvas a pedir el correo electrónico
❌ NO digas "¿Me podría dar su correo?"
❌ NO digas "¿Tiene correo electrónico?"
✅ YA LO TIENES: {email_actual}
✅ AVANZA con la conversación

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
            print(f"⚠️⚠️⚠️ FIX 172 VIOLADO: Bruce pidió nombre (genera delays de audio)")
            self.conversation_history.append({
                "role": "system",
                "content": """⚠️⚠️⚠️ ERROR CRÍTICO - FIX 172 VIOLADO:

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
                print(f"✅ CRÍTICO: Cliente CONFIRMÓ que quiere WhatsApp (NO correo)")

                self.conversation_history.append({
                    "role": "system",
                    "content": """⚠️⚠️⚠️ CRÍTICO - CLIENTE RECHAZÓ CORREO Y PIDIÓ WHATSAPP

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
            print(f"🚫 OBJECIÓN TRUPER detectada - Marcando como NO APTO")

            # FIX 34: Agregar respuesta de despedida INMEDIATA al historial
            # para que GPT NO genere más preguntas
            respuesta_truper = "Entiendo perfectamente. Truper es una excelente marca. Le agradezco mucho su tiempo y le deseo mucho éxito en su negocio. Que tenga un excelente día."

            self.conversation_history.append({
                "role": "assistant",
                "content": respuesta_truper
            })

            print(f"🚫 FIX 34: Protocolo TRUPER activado - respuesta de despedida agregada al historial")
            print(f"🚫 Retornando despedida inmediata: '{respuesta_truper}'")

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
                            print(f"👥 Referencia detectada: {nombre_referido}")
                            print(f"   Contexto: {texto[:100]}...")
                        break
                else:
                    # Si no hay nombre pero mencionan "te puedo pasar su contacto"
                    if "referencia_nombre" not in self.lead_data:
                        self.lead_data["referencia_nombre"] = ""  # Sin nombre todavía
                        self.lead_data["referencia_telefono"] = ""  # Se capturará después
                        self.lead_data["referencia_contexto"] = texto[:150]  # Contexto completo
                        print(f"👥 Referencia detectada (sin nombre aún)")
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

                print(f"🔍 Scanner de dígitos: encontrados {len(numero)} dígitos en '{texto[:50]}...'")

                # IMPORTANTE: Ignorar secuencias muy cortas (1-5 dígitos) para evitar interrumpir
                # cuando el cliente está en medio de dictar el número
                if len(numero) >= 1 and len(numero) <= 5:
                    print(f"🔇 Ignorando fragmento corto: {numero} ({len(numero)} dígitos) - cliente aún dictando, no interrumpir")
                    # NO agregamos mensajes al sistema, dejamos que el cliente continúe

                # Si encontramos 6+ dígitos, procesamos (ya está cerca del número completo)
                elif len(numero) >= 6:
                    # Validar que tenga exactamente 10 dígitos
                    if len(numero) == 10:
                        numero_completo = f"+52{numero}"
                        self.lead_data["referencia_telefono"] = numero_completo
                        print(f"📞 Número de referencia detectado: {numero_completo}")
                        print(f"   Asociado a: {self.lead_data.get('referencia_nombre', 'Encargado')}")

                        # Formatear número para repetir al cliente (ej: 66 23 53 41 85)
                        numero_formateado = ' '.join([numero[i:i+2] for i in range(0, len(numero), 2)])
                        self.conversation_history.append({
                            "role": "system",
                            "content": f"""[SISTEMA] ✅ Número completo capturado: {numero_formateado}

🚨 FIX 175 - INSTRUCCIONES CRÍTICAS PARA REPETIR NÚMERO:
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
                                print(f"⚠️ Número incompleto Y detectado en pares/grupos: {numero} ({len(numero)} dígitos)")
                                self.conversation_history.append({
                                    "role": "system",
                                    "content": "[SISTEMA] El cliente está proporcionando el número en PARES o GRUPOS (ej: '66 23 53' o 'veintitres cincuenta'). Esto puede causar errores en la captura. Debes pedirle de manera amable que repita el número DÍGITO POR DÍGITO para mayor claridad. Ejemplo: 'Para asegurarme de anotarlo correctamente, ¿podría repetirme el número dígito por dígito? Por ejemplo: seis, seis, dos, tres, cinco, tres...'"
                                })
                            else:
                                print(f"⚠️ Número incompleto de referencia detectado: {numero} ({len(numero)} dígitos)")
                                numero_formateado = ' '.join([numero[i:i+2] for i in range(0, len(numero), 2)])
                                self.conversation_history.append({
                                    "role": "system",
                                    "content": f"[SISTEMA] El número del contacto está incompleto: {numero_formateado} ({len(numero)} dígitos). Los números en México deben tener EXACTAMENTE 10 dígitos. Debes pedirle que confirme el número completo de 10 dígitos de manera natural."
                                })
                        else:
                            print(f"⚠️ Número con dígitos de más de referencia detectado: {numero} ({len(numero)} dígitos)")
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
                            print(f"👤 Nombre de referencia detectado: {nombre}")
                            print(f"   Asociado al número: {self.lead_data.get('referencia_telefono')}")
                            break

            # 3. Si NO tenemos nombre ni número, buscar número
            elif not self.lead_data.get("referencia_telefono"):
                # PASO 1: Convertir números escritos a dígitos
                texto_convertido = convertir_numeros_escritos_a_digitos(texto)

                # PASO 2: Extraer TODOS los dígitos
                numero = re.sub(r'[^\d]', '', texto_convertido)

                print(f"🔍 Scanner de dígitos (sin nombre): encontrados {len(numero)} dígitos en '{texto[:50]}...'")

                # IMPORTANTE: Ignorar secuencias muy cortas (1-5 dígitos) para evitar interrumpir
                # cuando el cliente está en medio de dictar el número
                if len(numero) >= 1 and len(numero) <= 5:
                    print(f"🔇 Ignorando fragmento corto: {numero} ({len(numero)} dígitos) - cliente aún dictando, no interrumpir")
                    # NO agregamos mensajes al sistema, dejamos que el cliente continúe

                # Si encontramos 6+ dígitos, procesamos (ya está cerca del número completo)
                elif len(numero) >= 6:
                    # Validar que tenga exactamente 10 dígitos
                    if len(numero) == 10:
                        numero_completo = f"+52{numero}"
                        self.lead_data["referencia_telefono"] = numero_completo
                        print(f"📞 Número de referencia detectado: {numero_completo}")
                        print(f"   Asociado a: {self.lead_data.get('referencia_nombre', 'Encargado')}")

                        # Formatear número para repetir al cliente (ej: 66 23 53 41 85)
                        numero_formateado = ' '.join([numero[i:i+2] for i in range(0, len(numero), 2)])
                        self.conversation_history.append({
                            "role": "system",
                            "content": f"""[SISTEMA] ✅ Número completo capturado: {numero_formateado}

🚨 FIX 175 - INSTRUCCIONES CRÍTICAS PARA REPETIR NÚMERO:
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
                                print(f"⚠️ Número incompleto Y detectado en pares/grupos: {numero} ({len(numero)} dígitos)")
                                self.conversation_history.append({
                                    "role": "system",
                                    "content": "[SISTEMA] El cliente está proporcionando el número en PARES o GRUPOS (ej: '66 23 53' o 'veintitres cincuenta'). Esto puede causar errores en la captura. Debes pedirle de manera amable que repita el número DÍGITO POR DÍGITO para mayor claridad. Ejemplo: 'Para asegurarme de anotarlo correctamente, ¿podría repetirme el número dígito por dígito? Por ejemplo: seis, seis, dos, tres, cinco, tres...'"
                                })
                            else:
                                print(f"⚠️ Número incompleto de referencia detectado: {numero} ({len(numero)} dígitos)")
                                numero_formateado = ' '.join([numero[i:i+2] for i in range(0, len(numero), 2)])
                                self.conversation_history.append({
                                    "role": "system",
                                    "content": f"[SISTEMA] El número del contacto está incompleto: {numero_formateado} ({len(numero)} dígitos). Los números en México deben tener EXACTAMENTE 10 dígitos. Debes pedirle que confirme el número completo de 10 dígitos de manera natural."
                                })
                        else:
                            print(f"⚠️ Número con dígitos de más de referencia detectado: {numero} ({len(numero)} dígitos)")
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
            print(f"⚠️ Cliente dice que YA dio el número antes")
            self.conversation_history.append({
                "role": "system",
                "content": """⚠️ CRÍTICO: El cliente dice que YA te dio el número de WhatsApp anteriormente.

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
                                print(f"🚨 Número MUY CORTO detectado: {numero} ({len(numero)} dígitos)")
                                self.conversation_history.append({
                                    "role": "system",
                                    "content": f"""[SISTEMA] ⚠️ NÚMERO MUY INCOMPLETO: Solo captaste {len(numero)} dígitos ({numero}).

Los números de WhatsApp en México SIEMPRE tienen 10 dígitos.

ACCIÓN REQUERIDA:
1. NO guardes este número incompleto
2. Pide el número completo de forma clara y natural
3. Ejemplo: "Disculpe, solo alcancé a captar {numero}. ¿Me podría dar el número completo de 10 dígitos? Por ejemplo: tres, tres, uno, cero, dos, tres..."

IMPORTANTE: Espera a que el cliente dé los 10 dígitos completos antes de continuar."""
                                })
                            else:
                                # 8-9 dígitos - casi completo
                                print(f"⚠️ Número incompleto detectado: {numero} ({len(numero)} dígitos)")
                                numero_formateado = ' '.join([numero[i:i+2] for i in range(0, len(numero), 2)])
                                self.conversation_history.append({
                                    "role": "system",
                                    "content": f"[SISTEMA] El número de WhatsApp está incompleto: {numero_formateado} ({len(numero)} dígitos). Los números en México deben tener EXACTAMENTE 10 dígitos. Debes pedirle que confirme el número completo de 10 dígitos. Ejemplo: 'El número que tengo es {numero_formateado}, pero me parece que falta un dígito. ¿Me lo podría confirmar completo?'"
                                })
                        else:
                            print(f"⚠️ Número con dígitos de más detectado: {numero} ({len(numero)} dígitos)")
                            numero_formateado = ' '.join([numero[i:i+2] for i in range(0, len(numero), 2)])
                            self.conversation_history.append({
                                "role": "system",
                                "content": f"[SISTEMA] El número de WhatsApp tiene dígitos de más: {numero_formateado} ({len(numero)} dígitos, pero deberían ser 10). Probablemente hubo un error en la captura. Debes pedirle que repita el número DÍGITO POR DÍGITO de manera clara y natural. Ejemplo: 'Disculpe, parece que capté algunos dígitos de más. ¿Podría repetirme su WhatsApp dígito por dígito? Por ejemplo: seis, seis, dos, tres...'"
                            })
                        break

                    else:  # len(numero) == 10
                        numero_completo = f"+52{numero}"
                        print(f"📱 WhatsApp detectado (10 dígitos): {numero_completo}")

                        # Validación simple: solo verificar formato y cantidad de dígitos
                        # Asumimos que todos los números móviles mexicanos de 10 dígitos tienen WhatsApp
                        self.lead_data["whatsapp"] = numero_completo
                        self.lead_data["whatsapp_valido"] = True
                        print(f"   ✅ Formato válido (10 dígitos)")
                        print(f"   💾 WhatsApp guardado: {numero_completo}")
                        print(f"   🎯 FIX 168: WhatsApp guardado - PRÓXIMA respuesta incluirá ANTI-CORREO + DESPEDIDA")
                        print(f"   🚨 FIX 168: FLAG whatsapp_valido=True → GPT NO debe pedir correo ni WhatsApp")

                        # FIX 168: Mejorado de FIX 167
                        # Ya NO usamos mensaje [SISTEMA] (se filtra en línea 2040)
                        # Ahora la instrucción se agrega directamente en el SYSTEM PROMPT dinámico
                        # Ver línea 3770+ en _construir_prompt_dinamico()

                    break
        else:
            print(f"🔄 Referencia pendiente detectada - números se guardarán como referencia_telefono")

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
                print(f"🔧 FIX 221: Corregida ayuda mnemotécnica: '{texto_original}' → '{texto_email_procesado}'")

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

            print(f"🔧 FIX 48B/192 - Ayudas mnemotécnicas eliminadas (AGRESIVO)")
            print(f"   Original: '{texto[:100]}...'")
            print(f"   Paso 1 (X de Palabra): '{texto_original_debug[:100]}...'")
            print(f"   Paso 2 (sin ayudas): '{texto_email_procesado[:100]}...'")

        # Paso 1: Reemplazar palabras clave por símbolos
        # "arroba" → "@"
        texto_email_procesado = re.sub(r'\b(arroba|aroba|a roba)\b', '@', texto_email_procesado)

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

            print(f"🔧 FIX 45 - Email deletreado detectado y reconstruido:")
            print(f"   Original: '{texto[:80]}...'")
            print(f"   Procesado: '{texto_email_procesado[:80]}...'")
            print(f"   Email reconstruido: '{email_reconstruido}'")

            # Usar el email reconstruido directamente
            email_detectado = email_reconstruido
            self.lead_data["email"] = email_detectado
            print(f"📧 Email detectado (deletreado): {email_detectado}")

            # FIX 98/118: DESPEDIRSE INMEDIATAMENTE después de capturar email
            self.conversation_history.append({
                "role": "system",
                "content": f"""[SISTEMA] ✅ Email capturado (deletreado): {email_detectado}

⚠️⚠️⚠️ FIX 98/118: DESPEDIDA INMEDIATA - CLIENTE OCUPADO ⚠️⚠️⚠️

El cliente está OCUPADO en mostrador. Ya tienes el EMAIL.

DEBES DESPEDIRTE AHORA:
"Perfecto, ya lo tengo anotado. Le llegará el catálogo en las próximas horas. Muchas gracias por su tiempo. Que tenga un excelente día."

🚨 FIX 118: NO REPITAS EL CORREO
❌ NUNCA digas el correo de vuelta (riesgo de deletrearlo mal)
❌ Solo di: "ya lo tengo anotado" o "perfecto, anotado"
❌ NO hagas más preguntas
❌ NO pidas confirmación del correo (ya lo tienes)
🚨 FIX 166: NO PIDAS MÁS DATOS❌ NO pidas WhatsApp (el email es suficiente)❌ NO pidas número telefónico
❌ NO preguntes sobre productos, proveedores, etc.
✅ DESPEDIRSE INMEDIATAMENTE y COLGAR

IMPORTANTE:
- El cliente está OCUPADO - termina la llamada YA
- Ya tienes nombre + email = SUFICIENTE
- Despedida corta y profesional
- NO repetir el correo evita errores de transcripción"""
            })

        # FIX 117: Manejar cuando solo se dice dominio (ej: "coprofesa punto net")
        elif match_solo_dominio:
            dominio_completo = match_solo_dominio.group(1).replace(' ', '') + '.' + match_solo_dominio.group(2)
            print(f"🔧 FIX 117 - Dominio parcial detectado: {dominio_completo}")
            print(f"   Original: '{texto[:80]}...'")

            # Pedir el usuario del email
            self.conversation_history.append({
                "role": "system",
                "content": f"""[SISTEMA] ⚠️ Email incompleto detectado: {dominio_completo}

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
                print(f"📧 Email detectado: {email_detectado}")

                # FIX 98: DESPEDIRSE INMEDIATAMENTE después de capturar email
                self.conversation_history.append({
                    "role": "system",
                    "content": f"""[SISTEMA] ✅ Email capturado: {email_detectado}

⚠️⚠️⚠️ FIX 98: DESPEDIDA INMEDIATA - CLIENTE OCUPADO ⚠️⚠️⚠️

El cliente está OCUPADO en mostrador. Ya tienes el EMAIL.

DEBES DESPEDIRTE AHORA:
"Perfecto, ya lo tengo anotado. Le llegará el catálogo en las próximas horas. Muchas gracias por su tiempo. Que tenga un excelente día."

❌ NO hagas más preguntas
❌ NO pidas confirmación del correo (ya lo tienes)
❌ NO preguntes sobre productos, proveedores, etc.
✅ DESPEDIRSE INMEDIATAMENTE y COLGAR

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
                    print(f"⚠️ Posible email incompleto o malformado detectado (Intento {self.email_intentos_fallidos}): '{texto[:100]}...'")

                    # Si ya fallamos 2+ veces, ofrecer alternativa de WhatsApp
                    if self.email_intentos_fallidos >= 2:
                        print(f"🚨 FIX 49: Email falló {self.email_intentos_fallidos} veces - ofrecer alternativa WhatsApp")
                        self.conversation_history.append({
                            "role": "system",
                            "content": """[SISTEMA] 🚨 PROBLEMA PERSISTENTE CON EMAIL (2+ intentos fallidos)

El cliente ha intentado deletrear el email 2 o más veces pero sigue sin capturarse correctamente.
La captura de emails por voz es POCO CONFIABLE cuando hay ayudas mnemotécnicas.

⚠️⚠️⚠️ ACCIÓN OBLIGATORIA - OFRECER ALTERNATIVA:

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
                            "content": """[SISTEMA] ⚠️ POSIBLE EMAIL INCOMPLETO - EL CLIENTE ESTÁ DELETREANDO

Detecté que el cliente está proporcionando un email letra por letra, pero aún NO está completo.

🚫🚫🚫 FIX 191: PROHIBIDO DECIR "PERFECTO, YA LO TENGO ANOTADO"
El cliente AÚN está hablando. NO lo interrumpas con despedidas.

ACCIÓN REQUERIDA:
1. Pide al cliente que CONTINÚE con el resto del correo
2. Di algo como: "Perfecto, excelente. Por favor, adelante con el correo."
3. O: "Entiendo, ¿me podría proporcionar el correo electrónico para enviar la información?"

❌ NO HACER:
- NO digas "ya lo tengo anotado" (NO lo tienes completo)
- NO te despidas (el cliente sigue hablando)
- NO inventes el correo

✅ HACER:
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
            print(f"📅 Reprogramación detectada en texto: {texto[:50]}...")

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
            print(f"🔧 FIX 47 - Corrección detectada: 'no me llamo X me llamo {nombre_corregido}'")
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
                print(f"✏️ Nombre CORREGIDO por cliente: '{nombre_anterior}' → '{nombre_corregido}'")

                # FIX 47: Enviar instrucción ULTRA-CLARA a GPT para usar el nombre correcto
                self.conversation_history.append({
                    "role": "system",
                    "content": f"""🚨🚨🚨 CORRECCIÓN CRÍTICA DE NOMBRE 🚨🚨🚨

El cliente acaba de corregir su nombre:
❌ Nombre INCORRECTO que usaste antes: "{nombre_anterior}"
✅ Nombre CORRECTO: "{nombre_corregido}"

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
                print(f"✅ WhatsApp válido: {numero}")
                return True
            else:
                print(f"⚠️ WhatsApp NO válido: {numero}")
                # Limpiar el WhatsApp del lead_data ya que no es válido
                self.lead_data["whatsapp"] = ""
                self.lead_data["whatsapp_valido"] = False
                return False

        except Exception as e:
            print(f"❌ Error al validar WhatsApp: {e}")
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
                print(f"📝 Pregunta 2 detectada: Sí (toma decisiones)")
            elif any(palabra in texto_lower for palabra in ["tengo que consultar", "no soy el dueño", "no puedo decidir", "habla con", "consultar con"]):
                self.lead_data["pregunta_2"] = "No"
                print(f"📝 Pregunta 2 detectada: No (no toma decisiones)")
            # Inferencia: Si dice que es encargado de compras o gerente
            elif any(palabra in texto_lower for palabra in ["encargado de compras", "yo soy el encargado", "gerente", "administrador", "yo manejo"]):
                self.lead_data["pregunta_2"] = "Sí (Bruce)"
                print(f"📝 Pregunta 2 inferida: Sí (Bruce) - es encargado/gerente")

        # PREGUNTA 3: Pedido Inicial (Crear Pedido Inicial/No)
        if not self.lead_data["pregunta_3"]:
            if any(palabra in texto_lower for palabra in ["arma el pedido", "sí, armalo", "dale, arma", "prepara el pedido", "hazme el pedido"]):
                self.lead_data["pregunta_3"] = "Crear Pedido Inicial Sugerido"
                print(f"📝 Pregunta 3 detectada: Crear Pedido Inicial Sugerido")
            elif any(palabra in texto_lower for palabra in ["no quiero pedido", "no hagas pedido", "todavía no", "aún no", "primero quiero ver"]):
                self.lead_data["pregunta_3"] = "No"
                print(f"📝 Pregunta 3 detectada: No")

        # PREGUNTA 4: Pedido de Muestra (Sí/No)
        if not self.lead_data["pregunta_4"]:
            # Detectar aceptación de pedido de muestra de $1,500
            if any(palabra in texto_lower for palabra in ["sí, la muestra", "acepto la muestra", "dale con la muestra", "sí, el pedido de muestra", "está bien $1,500", "está bien 1500"]):
                self.lead_data["pregunta_4"] = "Sí"
                print(f"📝 Pregunta 4 detectada: Sí (acepta muestra)")
            elif any(palabra in texto_lower for palabra in ["no, la muestra", "no quiero muestra", "no, gracias", "no me interesa la muestra"]):
                self.lead_data["pregunta_4"] = "No"
                print(f"📝 Pregunta 4 detectada: No (rechaza muestra)")

        # PREGUNTA 5: Compromiso de Fecha (Sí/No/Tal vez)
        if not self.lead_data["pregunta_5"]:
            if any(palabra in texto_lower for palabra in ["sí, esta semana", "esta semana sí", "dale, esta semana", "arrancamos esta semana"]):
                self.lead_data["pregunta_5"] = "Sí"
                print(f"📝 Pregunta 5 detectada: Sí (esta semana)")
            elif any(palabra in texto_lower for palabra in ["no, esta semana no", "la próxima", "el próximo mes", "todavía no puedo"]):
                self.lead_data["pregunta_5"] = "No"
                print(f"📝 Pregunta 5 detectada: No")
            elif any(palabra in texto_lower for palabra in ["tal vez", "talvez", "lo veo", "no sé", "lo pensare", "a ver"]):
                self.lead_data["pregunta_5"] = "Tal vez"
                print(f"📝 Pregunta 5 detectada: Tal vez")

        # PREGUNTA 6: Método de Pago TDC (Sí/No/Tal vez)
        if not self.lead_data["pregunta_6"]:
            if any(palabra in texto_lower for palabra in ["sí, con tarjeta", "acepto tarjeta", "con tdc", "sí, cierro", "dale, cierro"]):
                self.lead_data["pregunta_6"] = "Sí"
                print(f"📝 Pregunta 6 detectada: Sí (acepta TDC)")
            elif any(palabra in texto_lower for palabra in ["no con tarjeta", "no quiero tarjeta", "prefiero efectivo", "solo efectivo"]):
                self.lead_data["pregunta_6"] = "No"
                print(f"📝 Pregunta 6 detectada: No")
            elif any(palabra in texto_lower for palabra in ["tal vez", "lo veo", "veo lo de la tarjeta"]):
                self.lead_data["pregunta_6"] = "Tal vez"
                print(f"📝 Pregunta 6 detectada: Tal vez")

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
            print(f"📝 Pregunta 2 inferida: Sí (Bruce) - dio WhatsApp, probablemente toma decisiones")

        # PREGUNTA 3: Si dijo que no quiere pedido o solo quiere catálogo
        if not self.lead_data["pregunta_3"]:
            if self.lead_data["whatsapp"] and any(palabra in notas_lower for palabra in ["catálogo", "catalogo", "lo reviso", "envía", "manda"]):
                self.lead_data["pregunta_3"] = "No (Bruce)"
                print(f"📝 Pregunta 3 inferida: No (Bruce) - solo quiere catálogo")
            elif not self.lead_data["whatsapp"]:
                # Si no dio WhatsApp, definitivamente no quiere pedido
                self.lead_data["pregunta_3"] = "No (Bruce)"
                print(f"📝 Pregunta 3 inferida: No (Bruce) - no dio WhatsApp")

        # PREGUNTA 4: Si no aceptó P3, probablemente no quiere muestra tampoco
        if not self.lead_data["pregunta_4"]:
            if self.lead_data["pregunta_3"] in ["No", "No (Bruce)"]:
                self.lead_data["pregunta_4"] = "No (Bruce)"
                print(f"📝 Pregunta 4 inferida: No (Bruce) - rechazó pedido inicial")
            elif not self.lead_data["whatsapp"]:
                self.lead_data["pregunta_4"] = "No (Bruce)"
                print(f"📝 Pregunta 4 inferida: No (Bruce) - no dio WhatsApp")

        # PREGUNTA 5: Si dijo "sí está bien" o aceptó, inferir que sí
        if not self.lead_data["pregunta_5"]:
            if any(palabra in notas_lower for palabra in ["sí está bien", "si esta bien", "le parece bien", "está bien"]):
                self.lead_data["pregunta_5"] = "Sí (Bruce)"
                print(f"📝 Pregunta 5 inferida: Sí (Bruce) - aceptó con 'está bien'")
            elif self.lead_data["pregunta_4"] in ["No", "No (Bruce)"]:
                self.lead_data["pregunta_5"] = "No (Bruce)"
                print(f"📝 Pregunta 5 inferida: No (Bruce) - rechazó muestra")

        # PREGUNTA 6: Si no mencionó TDC, inferir según interés
        if not self.lead_data["pregunta_6"]:
            if self.lead_data["pregunta_5"] in ["Sí", "Sí (Bruce)"]:
                self.lead_data["pregunta_6"] = "Sí (Bruce)"
                print(f"📝 Pregunta 6 inferida: Sí (Bruce) - aceptó fecha")
            elif self.lead_data["pregunta_5"] in ["No", "No (Bruce)"]:
                self.lead_data["pregunta_6"] = "No (Bruce)"
                print(f"📝 Pregunta 6 inferida: No (Bruce) - rechazó fecha")

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

            # Llamar a GPT para analizar
            response = openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "Eres un analista de llamadas de ventas. Analiza objetivamente la conversación y proporciona insights."},
                    {"role": "user", "content": prompt_analisis}
                ],
                temperature=0.3,
                max_tokens=200
            )

            # Parsear respuesta JSON
            import json
            analisis_texto = response.choices[0].message.content.strip()
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

            print(f"\n📊 Análisis de la llamada:")
            print(f"   Estado de ánimo: {self.lead_data['estado_animo_cliente']}")
            print(f"   Nivel de interés: {self.lead_data['nivel_interes_clasificado']}")
            print(f"   Opinión de Bruce: {self.lead_data['opinion_bruce']}")

        except Exception as e:
            print(f"⚠️ Error al analizar estado de ánimo: {e}")
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
                print(f"📝 Conclusión ya determinada: {self.lead_data['pregunta_7']} (no recalcular)")
                return
            else:
                # Si es temporal, permitir recálculo
                print(f"📝 FIX 177: Conclusión temporal '{self.lead_data['pregunta_7']}' - recalculando con datos capturados...")

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
            print(f"📝 Conclusión determinada: Pedido (APROBADO)")

        # Si tiene WhatsApp y mostró interés, va a revisar catálogo
        elif self.lead_data["whatsapp"] and self.lead_data["interesado"]:
            self.lead_data["pregunta_7"] = "Revisara el Catalogo"
            self.lead_data["resultado"] = "APROBADO"
            print(f"📝 Conclusión determinada: Revisara el Catalogo (APROBADO)")

        # Si solo tiene email, conclusión es Correo
        elif self.lead_data["email"] and not self.lead_data["whatsapp"]:
            self.lead_data["pregunta_7"] = "Correo"
            self.lead_data["resultado"] = "APROBADO"
            print(f"📝 Conclusión determinada: Correo (APROBADO)")

        # Si pactó fecha (Pregunta 5 con fecha específica o "Tal vez")
        elif self.lead_data["pregunta_5"] == "Tal vez":
            self.lead_data["pregunta_7"] = "Avance (Fecha Pactada)"
            self.lead_data["resultado"] = "APROBADO"
            print(f"📝 Conclusión determinada: Avance (APROBADO)")

        # Si dijo "lo veo", "lo consulto", etc
        elif any(palabra in self.lead_data["notas"].lower() for palabra in ["lo consulto", "lo veo", "después", "lo pienso"]):
            self.lead_data["pregunta_7"] = "Continuacion (Cliente Esperando Alguna Situacion)"
            self.lead_data["resultado"] = "APROBADO"
            print(f"📝 Conclusión determinada: Continuacion (APROBADO)")

        # Si rechazó todo o no mostró interés
        elif not self.lead_data["interesado"]:
            self.lead_data["pregunta_7"] = "Nulo"
            self.lead_data["resultado"] = "NEGADO"
            print(f"📝 Conclusión determinada: Nulo (NEGADO)")

        # FIX 175: Incluir referencia_telefono en clasificación
        # Default: Si hay algún dato capturado (WhatsApp, email O referencia), considerar APROBADO
        elif (self.lead_data["whatsapp"] or
              self.lead_data["email"] or
              self.lead_data.get("referencia_telefono")):
            self.lead_data["pregunta_7"] = "Revisara el Catalogo"
            self.lead_data["resultado"] = "APROBADO"
            print(f"📝 Conclusión determinada: Revisara el Catalogo (APROBADO) - Dato capturado: WhatsApp={bool(self.lead_data['whatsapp'])}, Email={bool(self.lead_data['email'])}, Ref={bool(self.lead_data.get('referencia_telefono'))}")

        # Si no hay nada, es Nulo
        else:
            self.lead_data["pregunta_7"] = "Nulo"
            self.lead_data["resultado"] = "NEGADO"
            print(f"📝 Conclusión determinada: Nulo (NEGADO)")

    def guardar_llamada_y_lead(self):
        """
        Guarda la llamada y el lead en Google Sheets (si está configurado)
        También guarda en Excel como respaldo
        """
        try:
            print(f"📊 INICIANDO GUARDADO DE LLAMADA...")
            print(f"📊 - Call SID: {self.call_sid}")
            print(f"📊 - Sheets Manager: {'✅ Disponible' if self.sheets_manager else '❌ No disponible'}")
            print(f"📊 - Contacto Info: {'✅ Disponible' if self.contacto_info else '❌ No disponible'}")

            # Calcular duración de la llamada
            if self.lead_data["fecha_inicio"]:
                inicio = datetime.strptime(self.lead_data["fecha_inicio"], "%Y-%m-%d %H:%M:%S")
                duracion = (datetime.now() - inicio).total_seconds()
                self.lead_data["duracion_segundos"] = int(duracion)
                print(f"📊 - Duración: {self.lead_data['duracion_segundos']} segundos")

            # Determinar estado de la llamada
            estado_llamada = self._determinar_estado_llamada()
            print(f"📊 - Estado: {estado_llamada}")

            # NOTA: Google Sheets se guarda en el modo automático usando ResultadosSheetsAdapter
            # Ver líneas 2230+ para la lógica correcta de guardado

            # Guardar también en Excel como respaldo
            print(f"📊 Guardando backup en Excel...")
            self._guardar_backup_excel()

        except Exception as e:
            import traceback
            print(f"❌ Error al guardar llamada/lead: {e}")
            print(f"❌ Traceback completo:")
            print(traceback.format_exc())
            # Intentar guardar al menos en Excel
            try:
                self._guardar_backup_excel()
            except Exception as e2:
                print(f"❌ Error también en backup Excel: {e2}")

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
                contexto_recontacto += "⚠️ IMPORTANTE: Ya contactamos a esta tienda anteriormente con otro número.\n"
                contexto_recontacto += "El contacto anterior nos dio este nuevo número de teléfono.\n\n"

                if historial.get('referencia'):
                    contexto_recontacto += f"📋 Referencia anterior: {historial['referencia']}\n"

                if historial.get('contexto_reprogramacion'):
                    contexto_recontacto += f"📅 Contexto de reprogramación: {historial['contexto_reprogramacion']}\n"

                if historial.get('intentos_buzon'):
                    contexto_recontacto += f"📞 Intentos previos: {historial['intentos_buzon']}\n"

                contexto_recontacto += "\n💡 Usa este contexto para ser más efectivo. Menciona que ya contactamos la tienda si es relevante.\n\n"

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
                memoria_corto_plazo += "\n🚨 FIX 66: TUS ÚLTIMAS RESPUESTAS FUERON:\n"
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

            memoria_corto_plazo += "\n🚨🚨🚨 REGLAS CRÍTICAS DE CONVERSACIÓN:\n"

            if tiene_objeciones:
                memoria_corto_plazo += f"⚠️⚠️⚠️ ALERTA: El cliente mostró DESINTERÉS/OBJECIÓN\n"
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
            memoria_corto_plazo += "5. 🚨 FIX 171: NO uses el nombre del cliente en tus respuestas (genera delays de 1-4s en audio)\n"
            memoria_corto_plazo += "6. SI el cliente dice 'ya te dije', es porque estás repitiendo - PARA y cambia de tema\n\n"

        # FIX 168: Verificar si YA tenemos WhatsApp capturado (MEJORADO)
        instruccion_whatsapp_capturado = ""
        if self.lead_data.get("whatsapp") and self.lead_data.get("whatsapp_valido"):
            whatsapp_capturado = self.lead_data["whatsapp"]
            print(f"   ⚡ FIX 168: Agregando instrucción ANTI-CORREO al prompt (WhatsApp: {whatsapp_capturado})")
            instruccion_whatsapp_capturado = f"""

═══════════════════════════════════════════════════════════════
🚨🚨🚨 FIX 168 - WHATSAPP YA CAPTURADO: {whatsapp_capturado} 🚨🚨🚨
═══════════════════════════════════════════════════════════════

⚠️⚠️⚠️ INSTRUCCIÓN CRÍTICA - MÁXIMA PRIORIDAD - NO IGNORAR ⚠️⚠️⚠️

✅ CONFIRMACIÓN: Ya tienes el WhatsApp del cliente: {whatsapp_capturado}

🛑 PROHIBIDO ABSOLUTAMENTE:
   ❌ NO pidas WhatsApp nuevamente (YA LO TIENES GUARDADO)
   ❌ NO pidas correo electrónico (WhatsApp es SUFICIENTE)
   ❌ NO pidas nombre (innecesario para envío de catálogo)
   ❌ NO hagas MÁS preguntas sobre datos de contacto

✅ ACCIÓN OBLIGATORIA INMEDIATA:
   → DESPÍDETE AHORA confirmando envío por WhatsApp
   → USA esta frase EXACTA:

   "Perfecto, ya lo tengo. Le envío el catálogo en las próximas 2 horas
    por WhatsApp al {whatsapp_capturado}. Muchas gracias por su tiempo.
    Que tenga un excelente día."

⚠️ SI EL CLIENTE DICE "YA TE LO PASÉ" o "YA TE DI EL NÚMERO":
   1. Confirma: "Sí, tengo su número {whatsapp_capturado}"
   2. Despídete INMEDIATAMENTE (NO hagas más preguntas)

═══════════════════════════════════════════════════════════════

"""

        # Sección base (siempre se incluye) - CONTEXTO DEL CLIENTE PRIMERO
        prompt_base = contexto_cliente + contexto_recontacto + memoria_corto_plazo + instruccion_whatsapp_capturado + """# IDENTIDAD
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

✅ PRODUCTOS QUE SÍ MANEJAMOS:

1. GRIFERÍA (34 productos) - CATEGORÍA PRINCIPAL
   ✅ Llaves mezcladoras (monomando y doble comando)
   ✅ Grifos para cocina, baño, fregadero, lavabo
   ✅ Manerales y chapetones para regadera
   ✅ Mezcladoras cromadas, negro mate, doradas
   ✅ Mangueras de regadera
   ✅ Llaves angulares

2. CINTAS (23 productos) - INCLUYE PRODUCTO ESTRELLA
   ✅ Cinta para goteras (PRODUCTO ESTRELLA)
   ✅ Cintas reflejantes (amarillo, rojo/blanco)
   ✅ Cintas adhesivas para empaque
   ✅ Cinta antiderrapante
   ✅ Cinta de aluminio, kapton, velcro
   ✅ Cinta canela, perimetral

3. HERRAMIENTAS (28 productos)
   ✅ Juegos de dados y matracas (16, 40, 46, 53, 100 piezas)
   ✅ Dados magnéticos para taladro
   ✅ Llaves de tubo extensión
   ✅ Kits de desarmadores de precisión
   ✅ Dados de alto impacto

4. CANDADOS Y CERRADURAS (18 productos)
   ✅ Cerraduras de gatillo (latón, cromo, níquel)
   ✅ Chapas para puertas principales
   ✅ Cerraduras de perilla y manija
   ✅ Candados de combinación y seguridad
   ✅ Candados loto (bloqueo seguridad)

5. ACCESORIOS AUTOMOTRIZ (10 productos)
   ✅ Cables para bocina (calibre 16, 18, 22)
   ✅ Bocinas 6.5 y 8 pulgadas (150W, 200W, 250W)

6. MOCHILAS Y MALETINES (13 productos)
   ✅ Mochilas para laptop (con USB antirrobo)
   ✅ Maletines porta laptop
   ✅ Loncheras térmicas
   ✅ Bolsas térmicas
   ✅ Neceseres de viaje

7. OTROS PRODUCTOS (5 productos)
   ✅ Etiquetas térmicas
   ✅ Rampas y escaleras para mascotas
   ✅ Sillas de oficina
   ✅ Paraguas de bolsillo

⚠️ CÓMO RESPONDER PREGUNTAS SOBRE PRODUCTOS:

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

⚠️ PRODUCTOS QUE NO TENEMOS - SIEMPRE OFRECE EL CATÁLOGO:

PREGUNTA: "¿Manejan tubo PVC / tubería / codos?"
RESPUESTA: "Actualmente no manejamos tubería. Pero le envío el catálogo completo para que vea nuestras categorías de grifería, herramientas y cintas, por si le interesa algo más. ¿Cuál es su WhatsApp?"

PREGUNTA: "¿Manejan selladores / silicones / silicón?"
RESPUESTA: "No manejamos selladores. Tenemos cintas adhesivas y para goteras que podrían interesarle. Le envío el catálogo completo para que vea todo. ¿Cuál es su WhatsApp?"

PREGUNTA: "¿Manejan pinturas / brochas?"
RESPUESTA: "No manejamos pinturas. Nos especializamos en grifería, herramientas y cintas. De todos modos le envío el catálogo por si algo le interesa para el futuro. ¿Cuál es su WhatsApp?"

⚠️ REGLA CRÍTICA CUANDO NO TIENES EL PRODUCTO:
1. Sé honesto: "No manejamos [producto]"
2. Menciona qué SÍ tienes relacionado: "Pero tenemos [categoría relacionada]"
3. SIEMPRE ofrece el catálogo: "Le envío el catálogo completo por si le interesa algo más"
4. Pide WhatsApp inmediatamente: "¿Cuál es su WhatsApp?"
5. NUNCA termines la conversación solo porque no tienes UN producto
6. El cliente puede interesarse en OTROS productos del catálogo

⚠️ REGLA GENERAL:
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

# REGLAS ABSOLUTAS
✓ ESPAÑOL MEXICANO SIEMPRE - pronunciación nativa clara
✓ Evita palabras difíciles de pronunciar, usa sinónimos
✓ UNA pregunta a la vez
✓ Máximo 2-3 oraciones por turno (30 palabras máximo)
✗ CERO inglés - todo en español
✗ NO uses "ferreteros", di "de ferretería"
✗ NO digas que no puedes enviar catálogos (SÍ puedes)
✗ NO des listas largas de productos - menciona 1-2 ejemplos máximo

🔥 FIX 203 - BREVEDAD CRÍTICA (Prevenir delays de 8-12s):
⏱️ LÍMITE ESTRICTO: 15-25 palabras por respuesta (NUNCA más de 30)
✅ CORRECTO (18 palabras): "Entiendo. ¿Hay un mejor momento para llamar y hablar con el encargado de compras?"
❌ INCORRECTO (44 palabras): "Entiendo, es importante respetar esos tiempos. El motivo de mi llamada es muy breve: nosotros distribuimos productos de ferretería con alta rotación, especialmente nuestra cinta para goteras..."
💡 ESTRATEGIA: Una idea + una pregunta. NO monólogos. Conversación = ping-pong."""

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

🚨 IMPORTANTE: El saludo inicial fue solo "Hola, buen dia"

✅ FIX 198: El cliente respondió apropiadamente al saludo.

Ahora di la segunda parte:
"Me comunico de la marca nioval, más que nada quería brindar informacion de nuestros productos ferreteros, ¿Se encontrara el encargado o encargada de compras?"

NO continúes hasta confirmar que hablas con el encargado.

Si responden con preguntas ("¿Quién habla?", "¿De dónde?"):
"Me comunico de la marca nioval, más que nada quería brindar informacion de nuestros productos ferreteros, ¿Se encontrara el encargado o encargada de compras?"
Si dicen "Sí" / "Sí está" (indicando que el encargado SÍ está disponible): "Perfecto, ¿me lo podría comunicar por favor?"
Si dicen "Yo soy" / "Soy yo" / "Habla con él": "Perfecto. ¿Le gustaría recibir el catálogo por WhatsApp o correo electrónico?"
Si dicen NO / "No está" / "No se encuentra": "Entendido. ¿Me podría proporcionar un número de WhatsApp o correo para enviar información?"

⚠️⚠️⚠️ FIX 99/101: SI OFRECEN CORREO, ACEPTARLO Y DESPEDIRSE INMEDIATAMENTE
Si el cliente ofrece dar el CORREO del encargado:
- "Puedo darle su correo" / "Le paso su email" / "Mejor le doy el correo"

RESPONDE: "Perfecto, excelente. Por favor, adelante con el correo."
[ESPERA EL CORREO]

FIX 101: Después de recibir correo - DESPEDIDA INMEDIATA (SIN PEDIR NOMBRE):
"Perfecto, ya lo tengo anotado. Le llegará el catálogo en las próximas horas. Muchas gracias por su tiempo. Que tenga un excelente día."
[TERMINA LLAMADA - NO PIDAS NOMBRE]

❌ NO preguntes el nombre (abruma al cliente que no es de compras)
❌ NO insistas en número si ofrecen correo
✅ El correo es SUFICIENTE - Despedida inmediata
✅ Cliente se siente ayudado, NO comprometido

⚠️ IMPORTANTE - Detectar cuando YA te transfirieron:
Si después de pedir la transferencia, alguien dice "Hola" / "Bueno" / "Quién habla?" / "Dígame":
- Esta es LA PERSONA TRANSFERIDA (el encargado), NO una nueva llamada
- NO vuelvas a pedir que te comuniquen con el encargado
- 🚨 FIX 172: NO pidas el nombre
- Responde: "¿Bueno? Muy buen día. Me comunico de la marca nioval para ofrecerle nuestro catálogo. ¿Le gustaría recibirlo por WhatsApp?"

IMPORTANTE - Si el cliente ofrece dar el número:
- Si dicen "Te paso su contacto" / "Le doy el número": Di solo "Perfecto, estoy listo." y ESPERA el número SIN volver a pedirlo.
- Si preguntan "¿Tienes donde anotar?": Di solo "Sí, adelante por favor." y ESPERA el número SIN volver a pedirlo.
- NUNCA repitas la solicitud del número si el cliente ya ofreció darlo.

⚠️ FLUJO OBLIGATORIO SI DAN NÚMERO DE CONTACTO DE REFERENCIA:
[Si dan número de teléfono del encargado]
⚠️⚠️⚠️ FIX 98: FLUJO ULTRA-RÁPIDO - CLIENTE OCUPADO ⚠️⚠️⚠️

PASO 1: "Perfecto, muchas gracias. ¿Me podría decir su nombre para poder mencionarle que usted me facilitó su contacto?"
[Esperar nombre]

PASO 2 (SIMPLIFICADO): "Gracias [NOMBRE]. Perfecto, le enviaré el catálogo completo por correo electrónico para que el encargado lo revise con calma. ¿Me confirma el correo?"
[Esperar correo]

PASO 3 (DESPEDIDA INMEDIATA): "Perfecto, ya lo tengo anotado. Le llegará en las próximas horas. Muchas gracias por su tiempo, [NOMBRE]. Que tenga un excelente día."
[FIN DE LLAMADA]

❌ NUNCA hagas 3-4 preguntas largas (productos, proveedores, necesidades, horarios)
❌ NUNCA preguntes "¿Qué tipo de productos manejan? ¿Son ferretería local o mayorista?"
❌ La persona está OCUPADA en mostrador - ir DIRECTO al correo
✅ Solo: Nombre → Correo → Despedida (máximo 3 intercambios)
""")
                # FIX 201: Marcar que se dijo la segunda parte del saludo
                self.segunda_parte_saludo_dicha = True
                print(f"✅ FIX 201: Se activó la segunda parte del saludo. No se repetirá.")

            elif self.segunda_parte_saludo_dicha:
                # FIX 201: Cliente dijo "Dígame" u otro saludo DESPUÉS de que ya se dijo la segunda parte
                # NO repetir la introducción, continuar con la conversación
                fase_actual.append(f"""
# FASE ACTUAL: CONTINUACIÓN DESPUÉS DEL SALUDO - FIX 201

🚨 IMPORTANTE: Ya dijiste la presentación completa anteriormente.

Cliente dijo: "{ultima_respuesta_cliente}"

🎯 ANÁLISIS:
El cliente está diciendo "{ultima_respuesta_cliente}" como una forma de decir "continúa" o "te escucho".

✅ NO repitas tu presentación
✅ NO vuelvas a decir "Me comunico de la marca nioval..."
✅ YA lo dijiste antes

🎯 ACCIÓN CORRECTA:
Si preguntaste por el encargado de compras y el cliente dice "Dígame":
→ Interpreta esto como que ÉL ES el encargado o está escuchando
→ Continúa con: "Perfecto. ¿Le gustaría recibir nuestro catálogo por WhatsApp o correo electrónico?"

Si no has preguntado por el encargado aún:
→ Pregunta directamente: "¿Se encuentra el encargado o encargada de compras?"
""")
                print(f"✅ FIX 201: Cliente dijo '{ultima_respuesta_cliente}' después de la segunda parte. NO se repetirá la introducción.")

            else:
                # FIX 198: Cliente NO respondió con saludo estándar
                fase_actual.append(f"""
# FASE ACTUAL: APERTURA - FIX 198: MANEJO DE RESPUESTA NO ESTÁNDAR

🚨 El cliente NO respondió con un saludo estándar.

Cliente dijo: "{ultima_respuesta_cliente}"

🎯 ANÁLISIS Y ACCIÓN:

Si parece una PREGUNTA ("¿Quién habla?", "¿De dónde?", "¿Qué desea?"):
→ Responde la pregunta Y LUEGO di tu presentación completa:
   "Me comunico de la marca nioval, más que nada quería brindar informacion de nuestros productos ferreteros, ¿Se encontrara el encargado o encargada de compras?"

Si parece CONFUSIÓN o NO ENTENDIÓ (respuesta sin sentido, silencio, ruido):
→ Repite tu saludo de forma más clara y completa:
   "¿Bueno? Buenos días. Me comunico de la marca nioval, más que nada quería brindar informacion de nuestros productos ferreteros, ¿Se encontrara el encargado o encargada de compras?"

Si parece RECHAZO ("Ocupado", "No me interesa", "No tengo tiempo"):
→ Respeta su tiempo y ofrece alternativa rápida:
   "Entiendo que está ocupado. ¿Le gustaría que le envíe el catálogo por WhatsApp o correo para revisarlo cuando tenga tiempo?"

✅ SIEMPRE termina preguntando por el encargado de compras
✅ NO insistas si muestran rechazo claro
✅ Mantén tono profesional y respetuoso
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

⚠️⚠️⚠️ CRÍTICO - VERIFICAR HISTORIAL ANTES DE PEDIR CORREO ⚠️⚠️⚠️
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

⚠️⚠️⚠️ TIMING DE ENVÍO DEL CATÁLOGO - CRÍTICO:
❌ NUNCA NUNCA NUNCA digas: "en un momento", "ahorita", "al instante", "inmediatamente", "ya se lo envío"
✅ SIEMPRE SIEMPRE SIEMPRE di: "en el transcurso del día" o "en las próximas 2 horas"
Razón: Un compañero del equipo lo envía, NO es automático.

Ejemplos CORRECTOS cuando confirmas WhatsApp:
- "Perfecto, en las próximas 2 horas le llega el catálogo por WhatsApp"
- "Excelente, le envío el catálogo en el transcurso del día"

Ejemplos INCORRECTOS (NUNCA uses):
- "En un momento le enviaré..." ❌
- "Ahorita le envío..." ❌
- "Se lo envío al instante..." ❌
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

        # Combinar prompt base + fase actual
        return prompt_base + "\n".join(fase_actual)

    def _guardar_backup_excel(self):
        """Guarda un respaldo en Excel local"""
        try:
            import os
            archivo_excel = "leads_nioval_backup.xlsx"
            ruta_completa = os.path.abspath(archivo_excel)

            print(f"📁 Intentando guardar backup en: {ruta_completa}")

            # Intentar cargar archivo existente
            try:
                df = pd.read_excel(archivo_excel)
                print(f"📂 Archivo existente cargado con {len(df)} filas")
            except FileNotFoundError:
                df = pd.DataFrame()
                print(f"📄 Creando nuevo archivo Excel")

            # Convertir objeciones a string
            lead_data_excel = self.lead_data.copy()
            lead_data_excel["objeciones"] = ", ".join(lead_data_excel["objeciones"])

            # Agregar nuevo lead
            nuevo_lead = pd.DataFrame([lead_data_excel])
            df = pd.concat([df, nuevo_lead], ignore_index=True)

            # Guardar
            df.to_excel(archivo_excel, index=False)
            print(f"✅ Backup guardado en {ruta_completa} ({len(df)} filas totales)")

        except Exception as e:
            import traceback
            print(f"⚠️ No se pudo guardar backup en Excel: {e}")
            print(f"⚠️ Traceback: {traceback.format_exc()}")

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
            print(f"⚠️ Error en autoevaluación: {e}")
            return 5  # Calificación neutra si hay error

    def guardar_llamada_y_lead(self):
        """
        Guarda la llamada en Google Sheets usando ResultadosSheetsAdapter
        (Llamado desde servidor_llamadas.py al finalizar llamada)
        """
        if not self.resultados_manager:
            print("⚠️ ResultadosSheetsAdapter no disponible - no se puede guardar")
            return

        try:
            print("📊 Guardando resultados en 'Respuestas de formulario 1'...")

            # Calcular duración de la llamada ANTES de guardar
            if self.lead_data.get("fecha_inicio"):
                try:
                    inicio = datetime.strptime(self.lead_data["fecha_inicio"], "%Y-%m-%d %H:%M:%S")
                    duracion = (datetime.now() - inicio).total_seconds()
                    self.lead_data["duracion_segundos"] = int(duracion)
                    print(f"⏱️ Duración de la llamada: {self.lead_data['duracion_segundos']} segundos")
                except Exception as e:
                    print(f"⚠️ Error calculando duración: {e}")
                    self.lead_data["duracion_segundos"] = 0
            else:
                print(f"⚠️ No hay fecha_inicio - duración = 0")
                self.lead_data["duracion_segundos"] = 0

            # Determinar conclusión antes de guardar
            self._determinar_conclusion()

            # Autoevaluar llamada (Bruce se califica del 1-10)
            calificacion_bruce = self.autoevaluar_llamada()
            print(f"⭐ Bruce se autoevaluó: {calificacion_bruce}/10")

            # Guardar en "Respuestas de formulario 1"
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
                print(f"✅ Resultados guardados en 'Respuestas de formulario 1'")
            else:
                print(f"❌ Error al guardar resultados")

            print("\n" + "=" * 60)
            print("📋 ACTUALIZACIONES EN LISTA DE CONTACTOS")
            print("=" * 60)

            # Actualizar WhatsApp y Email en LISTA DE CONTACTOS si están disponibles
            if self.sheets_manager and self.contacto_info:
                fila = self.contacto_info.get('fila') or self.contacto_info.get('ID')
                print(f"\n📝 Verificando actualización en LISTA DE CONTACTOS...")
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
                    print(f"   ➡️ Actualizando columna E:E fila {fila} con {tipo_numero}...")
                    self.sheets_manager.actualizar_numero_con_whatsapp(
                        fila=fila,
                        whatsapp=numero_para_columna_e
                    )
                    print(f"✅ Columna E actualizada con {tipo_numero}: {numero_para_columna_e}")
                elif not numero_para_columna_e:
                    print(f"⚠️ No se capturó WhatsApp ni referencia - no se actualiza columna E")
                elif not fila:
                    print(f"⚠️ No se tiene fila del contacto - no se puede actualizar")

                if self.lead_data["email"] and fila:
                    self.sheets_manager.registrar_email_capturado(
                        fila=fila,
                        email=self.lead_data["email"]
                    )
                    print(f"✅ Email actualizado en LISTA DE CONTACTOS")

                # Guardar referencia si se detectó una (solo necesitamos el teléfono)
                if "referencia_nombre" in self.lead_data and self.lead_data.get("referencia_telefono"):
                    print(f"\n👥 Procesando referencia...")
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
                            print(f"   ✅ Referido encontrado en fila {contacto['fila']}: {contacto.get('nombre_negocio', 'Sin nombre')}")
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
                        print(f"✅ Referencia guardada en fila {fila_referido} (columna U)")

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
                        print(f"✅ Contexto de referencia guardado en fila {fila} (columna W)")

                        # 3. INICIAR LLAMADA AUTOMÁTICA AL REFERIDO
                        print(f"\n📞 Iniciando llamada automática al referido...")
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

                            print(f"   🌐 Enviando solicitud a {endpoint}")
                            print(f"   📱 Teléfono: {telefono_referido}")
                            print(f"   📋 Fila: {fila_referido}")

                            # Hacer la solicitud POST (con timeout para no bloquear)
                            response = requests.post(
                                endpoint,
                                json=payload,
                                timeout=5
                            )

                            if response.status_code == 200:
                                data = response.json()
                                call_sid = data.get("call_sid", "Unknown")
                                print(f"   ✅ Llamada iniciada exitosamente!")
                                print(f"   📞 Call SID: {call_sid}")
                            else:
                                print(f"   ⚠️ Error al iniciar llamada: {response.status_code}")
                                print(f"   Respuesta: {response.text}")

                        except requests.exceptions.Timeout:
                            print(f"   ⚠️ Timeout al iniciar llamada - la llamada puede haberse iniciado de todas formas")
                        except Exception as e:
                            print(f"   ❌ Error al iniciar llamada automática: {e}")
                            print(f"   La llamada deberá iniciarse manualmente")

                    else:
                        print(f"⚠️ No se encontró el número {telefono_referido} en LISTA DE CONTACTOS")
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
                        print(f"✅ Contexto de referencia guardado en fila {fila} (columna W)")

                # Guardar contexto de reprogramación si el cliente pidió ser llamado después
                if self.lead_data.get("estado_llamada") == "reprogramar" and fila:
                    print(f"\n📅 Guardando contexto de reprogramación...")

                    # Extraer fecha y motivo si están disponibles
                    fecha_reprogramacion = self.fecha_reprogramacion or "Próximos días"
                    motivo = f"Cliente solicitó ser llamado después. {self.lead_data['notas'][:100]}"

                    self.sheets_manager.guardar_contexto_reprogramacion(
                        fila=fila,
                        fecha=fecha_reprogramacion,
                        motivo=motivo,
                        notas=f"Interés: {self.lead_data['nivel_interes']} | WhatsApp: {self.lead_data['whatsapp'] or 'No capturado'}"
                    )
                    print(f"✅ Contexto de reprogramación guardado en columna W")

                    # Limpiar columna F para que vuelva a aparecer como pendiente
                    self.sheets_manager.marcar_estado_final(fila, "")
                    print(f"✅ Columna F limpiada - contacto volverá a aparecer como pendiente")
            else:
                print("⚠️ No hay sheets_manager o contacto_info - omitiendo actualizaciones")
                print(f"   sheets_manager: {'✓' if self.sheets_manager else '✗'}")
                print(f"   contacto_info: {'✓' if self.contacto_info else '✗'}")

            print("\n" + "=" * 60)
            print("✅ GUARDADO COMPLETO - Todos los datos procesados")
            print("=" * 60 + "\n")

        except Exception as e:
            print(f"❌ Error al guardar llamada: {e}")
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
    print("🤖 AGENTE DE VENTAS NIOVAL - Bruce W")
    print("=" * 60)
    print()
    
    agente = AgenteVentas()
    
    # Mensaje inicial
    mensaje_inicial = agente.iniciar_conversacion()
    print(f"🎙️ Bruce W: {mensaje_inicial}")
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
        respuesta_cliente = input("👤 Cliente: ").strip()
        
        if not respuesta_cliente:
            continue
        
        if respuesta_cliente.lower() in ["salir", "exit", "terminar"]:
            print("\n📊 Guardando información del lead...")
            agente.guardar_llamada_y_lead()
            print("\n" + "=" * 60)
            print("RESUMEN DE LA CONVERSACIÓN:")
            print(json.dumps(agente.obtener_resumen(), indent=2, ensure_ascii=False))
            print("=" * 60)
            break
        
        # Procesar y responder
        respuesta_agente = agente.procesar_respuesta(respuesta_cliente)
        print(f"\n🎙️ Bruce W: {respuesta_agente}\n")

        # Detectar estados de llamada sin respuesta (terminar automáticamente)
        if agente.lead_data["estado_llamada"] in ["Buzon", "Telefono Incorrecto", "Colgo", "No Respondio", "No Contesta"]:
            print(f"💼 Estado detectado: {agente.lead_data['estado_llamada']}. Finalizando llamada automáticamente...")
            print("📊 Guardando información del lead...\n")
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
            print("\n💼 Bruce W detectó despedida. Finalizando llamada...")
            print("📊 Guardando información del lead...\n")
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
        print("🚀 SISTEMA AUTOMÁTICO DE LLAMADAS - NIOVAL")
        print("=" * 60)

        # Inicializar adaptadores
        print("\n📊 Conectando con Google Sheets...")
        nioval_adapter = NiovalSheetsAdapter()
        resultados_adapter = ResultadosSheetsAdapter()

        # Contador de contactos procesados
        contactos_procesados = 0
        max_contactos = 100  # Límite de contactos a procesar en esta sesión

        # Procesar contactos continuamente (recargar lista después de cada uno)
        while contactos_procesados < max_contactos:
            # Recargar contactos pendientes (siempre obtiene el primero disponible)
            print("📋 Leyendo contactos pendientes...")
            contactos = nioval_adapter.obtener_contactos_pendientes(limite=1)  # Solo obtener el primero

            if not contactos:
                print(f"\n✅ No hay más contactos pendientes")
                break

            contacto = contactos[0]  # Tomar el primer contacto
            contactos_procesados += 1

            print("\n" + "=" * 60)
            print(f"📞 CONTACTO #{contactos_procesados}")
            print(f"   Negocio: {contacto.get('nombre_negocio', 'Sin nombre')}")
            print(f"   Teléfono: {contacto.get('telefono', 'Sin teléfono')}")
            print(f"   Ciudad: {contacto.get('ciudad', 'Sin ciudad')}")
            print("=" * 60 + "\n")

            # Crear agente para este contacto
            agente = AgenteVentas(contacto_info=contacto)

            # Iniciar conversación
            mensaje_inicial = agente.iniciar_conversacion()
            print(f"🎙️ Bruce W: {mensaje_inicial}\n")

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
                respuesta_cliente = input("👤 Cliente: ").strip()

                if not respuesta_cliente:
                    continue

                if respuesta_cliente.lower() in ["salir", "exit", "terminar"]:
                    print("\n📊 Finalizando conversación...")
                    break

                # Procesar y responder
                respuesta_agente = agente.procesar_respuesta(respuesta_cliente)
                print(f"\n🎙️ Bruce W: {respuesta_agente}\n")

                # Detectar estados de llamada sin respuesta (terminar automáticamente)
                if agente.lead_data["estado_llamada"] in ["Buzon", "Telefono Incorrecto", "Colgo", "No Respondio", "No Contesta"]:
                    print(f"💼 Estado detectado: {agente.lead_data['estado_llamada']}. Finalizando llamada automáticamente...")
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
                    print("\n💼 Bruce W detectó despedida. Finalizando conversación...")
                    break

            # Calcular duración de llamada
            if agente.lead_data["fecha_inicio"]:
                from datetime import datetime
                inicio = datetime.strptime(agente.lead_data["fecha_inicio"], "%Y-%m-%d %H:%M:%S")
                duracion = (datetime.now() - inicio).total_seconds()
                agente.lead_data["duracion_segundos"] = int(duracion)

            # Realizar análisis y determinar conclusión ANTES de guardar
            print("\n📊 Analizando llamada...")
            agente._determinar_conclusion()

            # Guardar resultados en Google Sheets
            print("\n📝 Guardando resultados en Google Sheets...")

            try:
                # 1. Guardar en "Respuestas de formulario 1" (7 preguntas + análisis)
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
                    print(f"   ✅ Formulario guardado correctamente")

                # 2. Actualizar contacto en "LISTA DE CONTACTOS"
                if agente.lead_data["whatsapp"]:
                    nioval_adapter.actualizar_numero_con_whatsapp(
                        fila=contacto['fila'],
                        whatsapp=agente.lead_data["whatsapp"]
                    )
                    print(f"   ✅ WhatsApp actualizado en LISTA DE CONTACTOS (celda E)")

                if agente.lead_data["email"]:
                    nioval_adapter.registrar_email_capturado(
                        fila=contacto['fila'],
                        email=agente.lead_data["email"]
                    )
                    print(f"   ✅ Email actualizado en LISTA DE CONTACTOS (celda T)")

                # 3. Manejo especial de BUZÓN (4 reintentos: 2 por día x 2 días)
                if agente.lead_data["estado_llamada"] == "Buzon":
                    # Marcar intento de buzón y obtener contador
                    intentos = nioval_adapter.marcar_intento_buzon(contacto['fila'])

                    if intentos <= 3:
                        # Intentos 1, 2, 3 - mover al final para reintentar
                        print(f"   📞 Intento #{intentos} de buzón detectado")
                        print(f"   ↩️  Moviendo contacto al final de la lista para reintentar...")
                        nioval_adapter.mover_fila_al_final(contacto['fila'])

                        if intentos == 1:
                            print(f"   ✅ Contacto reagendado para intento #2 (mismo día)")
                        elif intentos == 2:
                            print(f"   ✅ Contacto reagendado para intento #3 (siguiente ronda)")
                        elif intentos == 3:
                            print(f"   ✅ Contacto reagendado para intento #4 (último intento)")

                    elif intentos >= 4:
                        # Cuarto intento de buzón - clasificar como TELEFONO INCORRECTO
                        print(f"   📞 Cuarto intento de buzón detectado")
                        print(f"   ❌ Número no válido después de 4 intentos (2 días)")
                        print(f"   📋 Clasificando como TELEFONO INCORRECTO")
                        nioval_adapter.marcar_estado_final(contacto['fila'], "TELEFONO INCORRECTO")
                        print(f"   📋 Moviendo contacto al final de la lista (números no válidos)")
                        nioval_adapter.mover_fila_al_final(contacto['fila'])
                        print(f"   ✅ Contacto archivado al final con estado: TELEFONO INCORRECTO")
                else:
                    # Para otros estados (Respondio, Telefono Incorrecto, Colgo, No Contesta)
                    # Marcar el estado final en columna F
                    estado_final = agente.lead_data["estado_llamada"]
                    nioval_adapter.marcar_estado_final(contacto['fila'], estado_final)
                    print(f"   ✅ Estado final marcado: {estado_final}")

                # 4. Mostrar resumen
                print("\n" + "=" * 60)
                print("📊 RESUMEN DE LA CONVERSACIÓN:")
                print(f"📝 Conclusión: {agente.lead_data['pregunta_7']} ({agente.lead_data['resultado']})")
                print(json.dumps(agente.obtener_resumen(), indent=2, ensure_ascii=False))
                print("=" * 60)

            except Exception as e:
                print(f"   ❌ Error al guardar en Sheets: {e}")

            # Continuar automáticamente con el siguiente contacto (sin preguntar)
            print(f"\n⏩ Continuando automáticamente con el siguiente contacto...\n")

        # Fin del bucle while
        print("\n" + "=" * 60)
        print("✅ PROCESO COMPLETADO")
        print(f"   Total procesados: {contactos_procesados}")
        print("=" * 60 + "\n")

    except Exception as e:
        print(f"\n❌ Error en el proceso automático: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    print("\n⚠️  NOTA: Asegúrate de configurar las API keys en variables de entorno:")
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
