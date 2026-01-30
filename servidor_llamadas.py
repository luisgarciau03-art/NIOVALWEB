"""
Servidor Flask para manejar llamadas telefónicas con Twilio
Integración: Twilio → GPT-4o → ElevenLabs → Cliente
"""

from flask import Flask, request, Response, send_file
from twilio.twiml.voice_response import VoiceResponse, Gather, Play, Start, Stream
from twilio.rest import Client
import os
import tempfile
import threading
import json
import random
import base64
import asyncio
import traceback  # FIX 102: Para logging de errores detallados
from datetime import datetime  # FIX 272.10: Movido al inicio para DEPLOY_ID
from dotenv import load_dotenv
from agente_ventas import AgenteVentas
from elevenlabs import ElevenLabs
from openai import OpenAI  # FIX 60: Para Whisper API
import requests  # FIX 60: Para descargar grabaciones de Twilio
import re  # FIX 458: Para limpiar puntuación en detección de saludos

# FIX 212: Flask-Sock para WebSocket (Deepgram streaming)
try:
    from flask_sock import Sock
    FLASK_SOCK_AVAILABLE = True
except ImportError:
    FLASK_SOCK_AVAILABLE = False
    print(" FIX 212: flask-sock no instalado. WebSocket no disponible.")

load_dotenv()

app = Flask(__name__)

# FIX 212: Inicializar WebSocket para Deepgram streaming
sock = None
if FLASK_SOCK_AVAILABLE:
    sock = Sock(app)
    print(" FIX 212: Flask-Sock inicializado para WebSocket")

# FIX 212: Importar módulo de Deepgram
deepgram_transcriber = None
DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY")
USE_DEEPGRAM = os.getenv("USE_DEEPGRAM", "true").lower() == "true"

try:
    from deepgram_transcriber import (
        DeepgramTranscriber,
        crear_transcriber,
        obtener_transcriber,
        eliminar_transcriber,
        verificar_configuracion as verificar_deepgram
    )
    DEEPGRAM_AVAILABLE = verificar_deepgram() if DEEPGRAM_API_KEY else False
    if DEEPGRAM_AVAILABLE:
        print(" FIX 212: Deepgram configurado y listo")
    else:
        print(" FIX 212: Deepgram no configurado - usando Whisper como fallback")
except ImportError as e:
    DEEPGRAM_AVAILABLE = False
    print(f" FIX 212: Módulo deepgram_transcriber no disponible: {e}")

# Almacenamiento de transcripciones pendientes de Deepgram
deepgram_transcripciones = {}  # call_sid -> transcripción
# FIX 451: Tracking de transcripciones FINAL vs PARCIAL
deepgram_ultima_final = {}  # call_sid -> {"timestamp": float, "texto": str, "es_final": bool}
# FIX 455: Timestamp de cuando Bruce terminó de enviar audio
# Caso BRUCE1363: Cliente dijo "Ahorita no, jefe" DURANTE audio de Bruce, pero transcripción llegó tarde
# Solución: Limpiar transcripciones que llegaron ANTES de que Bruce terminara de hablar
bruce_audio_enviado_timestamp = {}  # call_sid -> timestamp cuando se envió el audio

# FIX 456: Tracking de transcripciones PARCIALES para detectar si cliente sigue hablando
# Caso BRUCE1375: Bruce interrumpió porque recibió FINAL pero cliente seguía hablando (PARCIAL nueva)
# Solución: Después de FINAL, esperar y verificar si llegan PARCIALES nuevas
deepgram_ultima_parcial = {}  # call_sid -> {"timestamp": float, "texto": str}

# FIX 490: Locks para prevenir race conditions en acceso concurrente a diccionarios compartidos
# Los threads de Deepgram, GPT, y cleanup acceden a estos diccionarios simultáneamente
deepgram_transcripciones_lock = threading.Lock()
deepgram_ultima_final_lock = threading.Lock()
conversaciones_activas_lock = threading.Lock()

# FIX 164: Sistema de logging condicional para reducir rate limit
DEBUG_MODE = os.getenv("DEBUG_MODE", "false").lower() == "true"

def debug_print(*args, **kwargs):
    """FIX 164: Print solo si DEBUG_MODE está activado"""
    if DEBUG_MODE:
        print(*args, **kwargs)

def info_print(*args, **kwargs):
    """FIX 164: Print para logs importantes (siempre se muestran)"""
    print(*args, **kwargs)

# Inicializar Google Sheets Managers y WhatsApp Validator (solo una vez al arrancar)
sheets_manager = None
resultados_manager = None
logs_manager = None
whatsapp_validator = None

try:
    from nioval_sheets_adapter import NiovalSheetsAdapter
    from resultados_sheets_adapter import ResultadosSheetsAdapter
    from logs_sheets_adapter import LogsSheetsAdapter

    sheets_manager = NiovalSheetsAdapter()  # Para leer contactos
    resultados_manager = ResultadosSheetsAdapter()  # Para guardar resultados
    logs_manager = LogsSheetsAdapter()  # Para registrar logs de conversación
    print(" Google Sheets Managers inicializados")
except Exception as e:
    print(f"  Google Sheets no disponible: {e}")
    print("  Las llamadas se guardarán solo en backup local")

# Inicializar WhatsApp Validator
try:
    from whatsapp_validator import WhatsAppValidator
    whatsapp_validator = WhatsAppValidator()
    print(" WhatsApp Validator inicializado")
except Exception as e:
    print(f"  WhatsApp Validator no disponible: {e}")
    print("  No se validarán números de WhatsApp")

# FIX 519: Inicializar Cache de Patrones Aprendidos
try:
    from cache_patrones_aprendidos import inicializar_cache_patrones
    cache_patrones = inicializar_cache_patrones()
    print(" FIX 519: Cache de Patrones Aprendidos inicializado")
except Exception as e:
    print(f"  FIX 519: Cache de Patrones no disponible: {e}")
    cache_patrones = None

# Configuración Twilio
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_PHONE_NUMBER = os.getenv("TWILIO_PHONE_NUMBER")

# FIX 173: Logging de diagnóstico de credenciales (sin exponer token completo)
print(" FIX 173: Verificando credenciales de Twilio...")
if TWILIO_ACCOUNT_SID:
    print(f"    TWILIO_ACCOUNT_SID encontrado: {TWILIO_ACCOUNT_SID[:10]}...{TWILIO_ACCOUNT_SID[-4:]}")
else:
    print("    TWILIO_ACCOUNT_SID NO ENCONTRADO")

if TWILIO_AUTH_TOKEN:
    print(f"    TWILIO_AUTH_TOKEN encontrado: {TWILIO_AUTH_TOKEN[:8]}...{TWILIO_AUTH_TOKEN[-4:]}")
else:
    print("    TWILIO_AUTH_TOKEN NO ENCONTRADO")

if TWILIO_PHONE_NUMBER:
    print(f"    TWILIO_PHONE_NUMBER: {TWILIO_PHONE_NUMBER}")
else:
    print("    TWILIO_PHONE_NUMBER NO ENCONTRADO")

# Configuración ElevenLabs
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
ELEVENLABS_VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID")

# FIX 60: Configuración OpenAI (para Whisper API)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
elevenlabs_client = ElevenLabs(api_key=ELEVENLABS_API_KEY)
openai_client = OpenAI(api_key=OPENAI_API_KEY)  # FIX 60: Cliente para Whisper

# Almacenar conversaciones activas (en producción usar Redis/DB)
conversaciones_activas = {}
# Almacenar archivos de audio temporales
audio_files = {}
# Mapear Call SID a información de contacto
contactos_llamadas = {}
# FIX 244: Tracking de habla activa para detectar interrupciones
cliente_hablando_activo = {}  # call_sid -> {"inicio": timestamp, "palabras_dichas": int}
# FIX 314: Tracking de respuestas pre-cargadas por detección de saludos en interim
respuesta_precargada = {}  # call_sid -> {"audio_listo": bool, "tipo": str}

# Caché de audios pre-generados con Multilingual v2 (mejor calidad)
audio_cache = {}

# Sistema de caché auto-adaptativo
frase_stats = {}  # Contador de frecuencia de frases

# Directorio de caché - detecta automáticamente si estamos en Railway
# Railway monta el Volume en /app/audio_cache por defecto
# En local usa ./audio_cache
CACHE_DIR = os.getenv("CACHE_DIR", "audio_cache")  # Configurable por variable de entorno
FRECUENCIA_MIN_CACHE = 1  # FIX 193: Auto-generar caché después de 1 uso (reducir latencia)

# FIX 272.10: Identificador único del deploy actual (fecha/hora de inicio del servidor)
DEPLOY_ID = datetime.now().strftime("%Y-%m-%d %H:%M")
# FIX 282: Nombre del deploy desde Railway (más legible)
# Railway provee: RAILWAY_DEPLOYMENT_ID (hash), RAILWAY_GIT_COMMIT_SHA, RAILWAY_GIT_COMMIT_MESSAGE
# Usamos: primeros 8 chars del commit message o del deployment ID como fallback
_commit_msg = os.getenv("RAILWAY_GIT_COMMIT_MESSAGE", "")
_deploy_id = os.getenv("RAILWAY_DEPLOYMENT_ID", "")
# Extraer nombre legible: "FIX 282: ..." -> "FIX 282"
if _commit_msg:
    # Tomar primeras palabras hasta ":" o máximo 15 chars
    DEPLOY_NAME = _commit_msg.split(":")[0][:15].strip() if ":" in _commit_msg else _commit_msg[:15].strip()
elif _deploy_id:
    DEPLOY_NAME = _deploy_id[:8]  # Primeros 8 caracteres del hash
else:
    DEPLOY_NAME = datetime.now().strftime("%m-%d %H:%M")
cache_metadata = {}  # Metadata: frase → archivo MP3

# FIX 56: CACHÉ DE RESPUESTAS DE GPT (0s delay para preguntas comunes)
# Diccionario: patrón de pregunta → respuesta pre-definida
respuestas_cache = {
    # Preguntas sobre origen/ubicación
    "de_donde_habla": {
        "patrones": [
            "de dónde", "de donde", "dónde están", "donde están",
            "de qué ciudad", "de que ciudad", "ubicados", "ubicación",
            "de parte de", "de qué parte", "de que parte",
            # FIX 302: Agregar variantes "en qué ciudad"
            "en qué ciudad", "en que ciudad", "qué ciudad están", "que ciudad estan"
        ],
        "respuesta": "Estamos ubicados en Guadalajara, Jalisco, pero hacemos envíos a toda la República Mexicana. ¿Se encuentra el encargado de compras?"
    },

    # Preguntas sobre qué vende
    "que_vende": {
        "patrones": [
            "qué vende", "que vende", "qué productos", "que productos",
            "qué maneja", "que maneja", "de qué se trata", "de que se trata",
            "qué ofrece", "que ofrece", "para qué llama", "para que llama"
        ],
        "respuesta": "Distribuimos productos de ferretería: cinta para goteras, griferías, herramientas, candados y más categorías. ¿Se encuentra el encargado de compras?"
    },

    # Preguntas sobre marcas
    "que_marcas": {
        "patrones": [
            "qué marcas", "que marcas", "cuáles marcas", "cuales marcas",
            "qué marca", "que marca", "de qué marca", "de que marca",
            "marcas manejan", "marcas tienen"
        ],
        "respuesta": "Manejamos la marca NIOVAL, que es nuestra marca propia. Al ser marca propia ofrecemos mejores precios. ¿Se encuentra el encargado de compras para platicarle más a detalle?"
    },

    # Quien habla / de parte de quien
    # FIX 308: Respuesta mejorada - NO preguntar nombre del cliente, solo presentarse
    "quien_habla": {
        "patrones": [
            "quién habla", "quien habla", "de parte de quién", "de parte de quien",
            "quién es", "quien es", "su nombre", "cómo se llama", "como se llama",
            # FIX 308: Más variantes de "¿de parte de quién?"
            "parte de quién", "parte de quien", "de qué empresa", "de que empresa",
            "qué empresa", "que empresa", "de dónde llama", "de donde llama"
        ],
        "respuesta": "Me comunico de parte de la marca NIOVAL, nosotros distribuimos productos de ferretería. ¿Se encontrará el encargado de compras?"
    },

    # FIX 194/274/275: Respuestas de presencia (cliente confundido/siente abandono)
    # FIX 274: Respuestas más cortas para no confundir
    # FIX 275: Agregar saludos para respuesta inmediata
    "saludo_inicial": {
        "patrones": ["buenos días", "buenos dias", "buen día", "buen dia", "buenas tardes", "buenas noches", "hola"],
        "respuesta": "Hola, buenos días. Me comunico de la marca NIOVAL para brindar información de nuestros productos ferreteros. ¿Se encontrará el encargado de compras?",
        "categoria": "saludo"
    },
    "presencia_aqui": {
        "patrones": ["oiga", "bueno"],
        "respuesta": "Sí, dígame.",
        "categoria": "presencia"
    },
    "presencia_escucho": {
        "patrones": ["me escucha", "me oye"],
        "respuesta": "Sí, lo escucho perfectamente.",
        "categoria": "presencia"
    },
    "presencia_ayudo": {
        "patrones": ["sigue ahí", "está ahí"],
        "respuesta": "Sí, aquí sigo.",
        "categoria": "presencia"
    },
    "presencia_digame": {
        "patrones": ["bruce"],
        "respuesta": "Sí, dígame.",
        "categoria": "presencia"
    },

    # FIX 209/294/296: Respuestas cuando cliente ES el encargado de compras
    "encargado_si": {
        "patrones": ["sí soy", "si soy", "con él", "con el", "el mismo", "soy yo", "a sus órdenes", "a sus ordenes",
                     # FIX 294: Más formas de confirmar que ES el encargado
                     "hablando con él", "hablando con el", "estás hablando con él", "estas hablando con el",
                     "está hablando con él", "esta hablando con el", "hablas con él", "hablas con el",
                     "yo soy", "yo mero", "servidor", "el que busca", "el que buscas",
                     "soy el encargado", "soy la encargada", "soy el dueño", "soy la dueña",
                     "soy el de compras", "soy la de compras", "yo me encargo", "yo hago las compras",
                     # FIX 296: "él habla" = "con él habla" = ES el encargado
                     "él habla", "el habla", "sí él habla", "si el habla", "con él habla", "con el habla",
                     "él le atiende", "el le atiende", "aquí él", "aqui el", "él mismo", "el mismo"],
        "respuesta": "Perfecto. ¿Le gustaría recibir nuestro catálogo por WhatsApp o correo electrónico?"
    },
    # FIX 283: Cuando cliente confirma enviar a este número (WhatsApp)
    "confirma_este_numero": {
        "patrones": ["a este número", "a este numero", "es a este número", "es a este numero",
                     "a este mismo", "este mismo número", "este mismo numero", "al mismo número", "al mismo numero",
                     "a este lo pueden enviar", "a este lo puedo enviar", "a este número lo pueden", "a este numero lo pueden"],
        "respuesta": "Perfecto, lo enviaré a este número. Le mandaré el catálogo en breve."
    },
    # FIX 277/310: Cuando están pasando la llamada al encargado (modo espera)
    "pasando_llamada": {
        "patrones": ["te lo comunico", "se lo comunico", "te lo paso", "se lo paso", "ahorita te lo paso",
                     "ahorita se lo paso", "espéreme", "espereme", "un momento", "un momentito",
                     "déjame ver", "dejame ver", "voy a ver", "le paso", "te paso", "espere",
                     "deme un segundo", "dame un segundo", "un segundo", "un segundito",
                     "permítame", "permíteme", "permitame", "permiteme", "tantito",
                     # FIX 290: Agregar variantes de "deme un minuto"
                     "deme un minuto", "dame un minuto", "un minuto", "un minutito",
                     "déme un minuto", "deme chance", "dame chance", "un ratito", "un rato",
                     # FIX 310: "me da unos minutos" / "me permite"
                     "me da unos minutos", "me permite", "me das unos minutos", "unos minutos",
                     "si me da", "si me das", "si me permite", "si me permites",
                     "dame unos minutos", "deme unos minutos", "unos minutitos"],
        "respuesta": "Claro, aquí espero.",
        "categoria": "espera"
    },
    # FIX 311: Cuando encargado no está, primero pedir su número directo
    "encargado_no": {
        "patrones": ["no está", "no esta", "salió", "salio", "no se encuentra", "no lo tenemos", "dejar recado", "dejar el recado", "gusta dejar", "dejarle recado", "dejar mensaje"],
        "respuesta": "Entiendo. ¿Me podría proporcionar el número directo del encargado para contactarlo?"
    },
    # FIX 278/312: Cuando sugieren llamar en otro momento
    "llamar_otro_momento": {
        "patrones": ["marcarle en otro momento", "llamar en otro momento", "marque después", "marque despues",
                     "llame después", "llame despues", "otro momento", "más tarde", "mas tarde",
                     "regrese más tarde", "regrese mas tarde", "vuelva a llamar", "llame más tarde", "llame mas tarde",
                     # FIX 312: "si gusta marcar posteriormente" y variantes
                     "marcar posteriormente", "marque posteriormente", "llame posteriormente",
                     "si gusta marcar", "si gusta llamar", "si gusta marcarle", "si gusta llamarle",
                     "puede marcar", "puede llamar", "podría marcar", "podria marcar",
                     "al rato", "ahorita no", "ahorita está ocupado", "ahorita esta ocupado"],
        "respuesta": "Claro, con gusto. ¿A qué hora me recomienda llamar para encontrarlo?"
    },
    # FIX 281: Cuando mencionan día específico (fin de semana, lunes, etc.)
    "llamar_dia_especifico": {
        "patrones": ["es sábado", "es sabado", "es domingo", "hoy es sábado", "hoy es sabado", "hoy es domingo",
                     "el lunes", "el martes", "el miércoles", "el miercoles", "el jueves", "el viernes",
                     "hasta el lunes", "hasta el martes", "hasta el miércoles", "hasta el miercoles",
                     "mañana lunes", "mañana martes", "pasado mañana", "la próxima semana", "la proxima semana",
                     "no abrimos", "estamos cerrados", "no trabajamos", "no hay nadie", "no viene"],
        "respuesta": "Perfecto, muchas gracias por la información. Le marco entonces. Que tenga excelente día."
    },
    # FIX 273: Cuando no pueden dar información (no es el encargado)
    "no_puede_decidir": {
        "patrones": ["no sabría decirle", "no sabria decirle", "no puedo ayudarle", "no le puedo ayudar", "no sé", "no se", "no estoy seguro", "tendría que preguntar", "tendria que preguntar"],
        "respuesta": "Entiendo perfectamente. ¿A qué hora puedo llamar para hablar con el encargado? O si prefiere, le dejo el catálogo por WhatsApp para que lo revise con calma."
    },
    "whatsapp_si": {
        "patrones": ["whatsapp", "wasa", "número es", "numero es", "mi cel", "mi teléfono", "mi telefono"],
        "respuesta": "Perfecto. ¿Me lo puede confirmar? Lo anoto."
    },
    "correo_si": {
        "patrones": ["por correo", "el correo", "un correo", "mi correo", "email", "mándalo", "mandalo", "envíalo", "envialo", "le paso",
                     "te doy un correo", "te voy a dar un correo", "le doy el correo", "le paso el correo",
                     "por correo electrónico", "correo electrónico"],
        "respuesta": "Perfecto, dígame el correo y lo anoto."
    },
    # FIX 306: Cliente ofrece proporcionar su contacto (no está el encargado pero ofrece dar info)
    "ofrece_proporcionar": {
        "patrones": ["si gusta le proporciono", "si gusta le doy", "le proporciono", "le puedo proporcionar",
                     "le doy el número", "le doy el numero", "le paso el número", "le paso el numero",
                     "le doy su número", "le doy su numero", "le paso su número", "le paso su numero",
                     "si quiere le doy", "si quiere le paso", "quiere que le dé", "quiere que le de",
                     "le puedo dar", "puedo darle", "se lo proporciono", "se lo doy"],
        "respuesta": "Sí, por favor, se lo agradezco mucho."
    },
    # FIX 310: Cliente SOLICITA recibir info por WhatsApp (Bruce debe pedir número)
    "cliente_pide_whatsapp": {
        "patrones": ["enviarnos la información por whatsapp", "enviarme la información por whatsapp",
                     "enviarnos la informacion por whatsapp", "enviarme la informacion por whatsapp",
                     "mándame la información por whatsapp", "mandame la informacion por whatsapp",
                     "mándeme la información por whatsapp", "mandeme la informacion por whatsapp",
                     "envíalo por whatsapp", "envialo por whatsapp", "mándalo por whatsapp", "mandalo por whatsapp",
                     "por whatsapp mejor", "mejor por whatsapp", "prefiero por whatsapp",
                     "si gusta enviarnos", "si gusta enviarme", "si quiere enviarnos", "si quiere enviarme",
                     "puede enviarme", "puede enviarnos", "nos puede enviar", "me puede enviar",
                     "envíenos", "envienos", "envíeme", "envieme"],
        "respuesta": "Claro que sí. ¿Me puede proporcionar el número de WhatsApp para enviarle la información?"
    },
    "no_interesa": {
        "patrones": ["no me interesa", "no gracias", "no necesito", "ya tenemos", "estamos bien"],
        "respuesta": "Entiendo perfectamente. Solo quisiera enviarle nuestro catálogo sin compromiso para que lo tenga como referencia. ¿Le parece bien por WhatsApp?"
    },
    "ocupado": {
        "patrones": ["estoy ocupado", "no tengo tiempo", "ahora no puedo", "llámame después", "llamame despues"],
        "respuesta": "Por supuesto, lo entiendo. ¿Prefiere que le llame mañana por la mañana? O si gusta, le envío el catálogo por WhatsApp y lo revisa cuando pueda."
    },
    # FIX 276: Detectar cuando no venden/manejan ferretería
    "no_vende_ferreteria": {
        "patrones": ["no vendo ferretería", "no vendo ferreteria", "no vendemos ferretería", "no vendemos ferreteria",
                     "no manejo ferretería", "no manejo ferreteria", "no manejamos ferretería", "no manejamos ferreteria",
                     "nada de ferretería", "nada de ferreteria", "no es ferretería", "no es ferreteria",
                     "no tenemos ferretería", "no tenemos ferreteria", "no me dedico a", "no nos dedicamos"],
        "respuesta": "Entiendo perfectamente, disculpe la molestia. Que tenga un excelente día, gracias por su tiempo."
    },
    # FIX 311: Número equivocado - despedirse inmediatamente
    "numero_equivocado": {
        "patrones": ["está equivocado", "esta equivocado", "equivocado de número", "equivocado de numero",
                     "número equivocado", "numero equivocado", "se equivocó", "se equivoco",
                     "no es aquí", "no es aqui", "aquí no es", "aqui no es",
                     "no existe", "ya no existe", "no vive aquí", "no vive aqui",
                     "no trabaja aquí", "no trabaja aqui", "no conozco", "no lo conozco"],
        "respuesta": "Disculpe la molestia, que tenga buen día."
    },
    # FIX 288/291/309: Cuando las compras se hacen en otro lugar (sucursal vs oficinas/matriz/punto de venta)
    "compras_en_oficinas": {
        "patrones": ["sucursal no", "sucursales no", "aquí no se compra", "aqui no se compra", "no compramos aquí", "no compramos aqui",
                     "compras en oficinas", "compras en corporativo", "compras en matriz", "área de compras",
                     "oficinas centrales", "corporativo", "es en matriz", "es en oficinas",
                     "no hacemos compras", "no se hacen compras", "no podemos comprar",
                     # FIX 291: Más variantes de sucursal/matriz
                     "es una sucursal", "somos sucursal", "esto es sucursal", "aquí es sucursal", "aqui es sucursal",
                     "ir a la matriz", "ir a matriz", "tendría que ir", "tendria que ir", "tendré que ir", "tendre que ir",
                     "a la matriz", "en la matriz", "llamar a matriz", "marcar a matriz",
                     "aquí no es de compras", "aqui no es de compras", "no es de compras",
                     "no se compra aquí", "no se compra aqui", "aquí no compramos", "aqui no compramos",
                     # FIX 309: Punto de venta (BRUCE731)
                     "punto de venta", "un punto de venta", "es punto de venta", "somos punto de venta",
                     "aquí no hay oficinas", "aqui no hay oficinas", "no hay oficinas de compras",
                     "no es una oficina", "no es oficina", "aquí no es oficina", "aqui no es oficina",
                     "no nos encargamos de comprar", "no se encargan de comprar", "no me encargo de comprar",
                     "aquí no tenemos quien", "aqui no tenemos quien", "no tenemos quien compre",
                     "no es el área de compras", "no es el area de compras", "no es de compras aquí", "no es de compras aqui",
                     # FIX 309b: BRUCE737 - más variantes de "no hay compras aquí"
                     "aquí no hay compras", "aqui no hay compras", "no hay compras", "no hay compras aquí", "no hay compras aqui",
                     "no hay departamento de compra", "no hay departamento de compras", "no tenemos departamento",
                     "aquí no hay departamento", "aqui no hay departamento", "no existe departamento",
                     # FIX 317: Compras en otra ciudad (BRUCE759)
                     "está allá", "esta alla", "eso está allá", "eso esta alla", "es allá", "es alla",
                     "allá en la ciudad", "alla en la ciudad", "en otra ciudad", "en la ciudad de",
                     "en cdmx", "en méxico", "en mexico", "en guadalajara", "en monterrey",
                     "allá con ellos", "alla con ellos", "con ellos allá", "con ellos alla"],
        "respuesta": "Entiendo, las compras se manejan en otra ubicación. ¿Me podría proporcionar el número del área de compras?"
    },
}

# Estadísticas de uso del caché de respuestas
cache_respuestas_stats = {
    "total_consultas": 0,
    "cache_hits": 0,
    "cache_misses": 0,
    "por_categoria": {}
}

# FIX 57: AUTO-APRENDIZAJE DE CACHÉ (detecta preguntas frecuentes)
# Diccionario: pregunta_normalizada → {count, respuestas, ultima_respuesta}
preguntas_frecuentes = {}
UMBRAL_AUTO_CACHE = 2  # Después de 2 veces, sugerir para caché (más agresivo)
candidatos_auto_cache = []  # Lista de preguntas que califican para caché automático


# FIX 489: Función para limpiar TODOS los recursos de una llamada terminada (prevenir memory leak)
def limpiar_recursos_llamada(call_sid):
    """
    Limpia todos los recursos asociados a una llamada terminada.

    FIX 489: Previene memory leak limpiando TODOS los diccionarios que usan call_sid como key.
    Antes solo se limpiaban 2 de 9 diccionarios, causando acumulación de memoria.

    Args:
        call_sid: ID de la llamada de Twilio
    """
    diccionarios_call_specific = [
        conversaciones_activas,      # Instancia del agente
        contactos_llamadas,          # Info del contacto
        deepgram_transcripciones,    # Transcripciones acumuladas
        deepgram_ultima_final,       # Última transcripción FINAL
        deepgram_ultima_parcial,     # Última transcripción PARCIAL
        cliente_hablando_activo,     # Tracking de interrupciones
        bruce_audio_enviado_timestamp,  # Timestamp del último audio
        respuesta_precargada,        # Respuestas pre-generadas
        callsid_to_bruceid          # Mapeo call_sid -> bruce_id
    ]

    # Limpiar cada diccionario
    recursos_limpiados = 0
    for diccionario in diccionarios_call_specific:
        if call_sid in diccionario:
            del diccionario[call_sid]
            recursos_limpiados += 1

    print(f" FIX 489: Limpiados {recursos_limpiados} recursos de llamada {call_sid}")


def cargar_cache_desde_disco():
    """Carga caché persistente desde disco al iniciar"""
    import os
    import json

    if not os.path.exists(CACHE_DIR):
        os.makedirs(CACHE_DIR)
        print(" Directorio de caché creado")
        return

    # Cargar metadata
    metadata_file = os.path.join(CACHE_DIR, "metadata.json")
    if os.path.exists(metadata_file):
        with open(metadata_file, 'r', encoding='utf-8') as f:
            global cache_metadata
            cache_metadata = json.load(f)

        # Cargar archivos de audio
        for key, filename in cache_metadata.items():
            filepath = os.path.join(CACHE_DIR, filename)
            if os.path.exists(filepath):
                audio_cache[key] = filepath
                print(f"   Cargado desde disco: {key}")

        print(f" {len(audio_cache)} audios cargados desde caché persistente\n")

    # Cargar estadísticas de frases
    stats_file = os.path.join(CACHE_DIR, "frase_stats.json")
    if os.path.exists(stats_file):
        with open(stats_file, 'r', encoding='utf-8') as f:
            global frase_stats
            frase_stats = json.load(f)
        print(f" {len(frase_stats)} estadísticas de frases cargadas desde disco\n")

    # FIX 57: Cargar preguntas frecuentes y candidatos auto-cache
    preguntas_file = os.path.join(CACHE_DIR, "preguntas_frecuentes.json")
    if os.path.exists(preguntas_file):
        with open(preguntas_file, 'r', encoding='utf-8') as f:
            global preguntas_frecuentes
            preguntas_frecuentes = json.load(f)
        print(f" {len(preguntas_frecuentes)} preguntas frecuentes cargadas desde disco\n")

    # FIX 57/59/64: Cargar respuestas cacheadas personalizadas
    respuestas_file = os.path.join(CACHE_DIR, "respuestas_cache.json")
    repo_respuestas_file = os.path.join(os.path.dirname(__file__), "seed_data", "respuestas_cache.json")

    # FIX 64: SIEMPRE actualizar desde seed_data/ si existe y es diferente
    # Esto permite actualizar patrones sin borrar el Volume
    import shutil
    if os.path.exists(repo_respuestas_file):
        # Comparar contenido para evitar copias innecesarias
        debe_actualizar = True
        if os.path.exists(respuestas_file):
            try:
                with open(repo_respuestas_file, 'r', encoding='utf-8') as f1:
                    seed_content = json.load(f1)
                with open(respuestas_file, 'r', encoding='utf-8') as f2:
                    volume_content = json.load(f2)

                # Comparar número de categorías y patrones
                if len(seed_content) == len(volume_content):
                    # Verificar si los patrones son iguales
                    if all(
                        key in volume_content and
                        volume_content[key].get('patrones') == seed_content[key].get('patrones')
                        for key in seed_content
                    ):
                        debe_actualizar = False
                        print(f" FIX 64: respuestas_cache.json ya está actualizado ({len(seed_content)} categorías)\n")
            except Exception as e:
                print(f" FIX 64: Error comparando cache, actualizando: {e}")
                debe_actualizar = True

        if debe_actualizar:
            shutil.copy(repo_respuestas_file, respuestas_file)
            print(f" FIX 64: Actualizado respuestas_cache.json desde seed_data/ a Volume\n")
    else:
        print(f" FIX 64: No se encontró seed_data/respuestas_cache.json\n")

    if os.path.exists(respuestas_file):
        with open(respuestas_file, 'r', encoding='utf-8') as f:
            global respuestas_cache
            cache_personalizado = json.load(f)
            # Merge con las respuestas por defecto (prioridad a las personalizadas)
            respuestas_cache.update(cache_personalizado)
        print(f" {len(cache_personalizado)} respuestas personalizadas cargadas desde disco")
        print(f" TOTAL de categorías en caché: {len(respuestas_cache)}\n")


def guardar_cache_en_disco(key, texto, audio_path):
    """Guarda un audio en el caché persistente"""
    import os
    import json
    import shutil

    # Crear directorio si no existe
    if not os.path.exists(CACHE_DIR):
        os.makedirs(CACHE_DIR)

    # Generar nombre de archivo único
    import hashlib
    hash_key = hashlib.md5(texto.encode()).hexdigest()[:12]
    filename = f"{key}_{hash_key}.mp3"
    filepath = os.path.join(CACHE_DIR, filename)

    # Copiar archivo de audio temporal al caché persistente
    shutil.copy2(audio_path, filepath)

    # Actualizar metadata
    cache_metadata[key] = filename

    # Guardar metadata
    metadata_file = os.path.join(CACHE_DIR, "metadata.json")
    with open(metadata_file, 'w', encoding='utf-8') as f:
        json.dump(cache_metadata, f, ensure_ascii=False, indent=2)

    print(f" Caché guardado en disco: {key} → {filename}")


def guardar_stats_en_disco():
    """Guarda las estadísticas de frases en disco para persistencia"""
    import os
    import json

    stats_file = os.path.join(CACHE_DIR, "frase_stats.json")
    with open(stats_file, 'w', encoding='utf-8') as f:
        json.dump(frase_stats, f, ensure_ascii=False, indent=2)


def registrar_pregunta_respuesta(pregunta, respuesta):
    """
    FIX 57: Registra pares pregunta-respuesta para detectar patrones frecuentes
    Si una pregunta se repite UMBRAL_AUTO_CACHE veces, se sugiere para caché automático
    """
    import os
    import json
    import re

    global preguntas_frecuentes, candidatos_auto_cache

    # Normalizar pregunta (minúsculas, sin puntuación excesiva)
    pregunta_normalizada = re.sub(r'[¿?¡!]+', '', pregunta.lower().strip())
    pregunta_normalizada = ' '.join(pregunta_normalizada.split())  # Normalizar espacios

    # Si la pregunta ya existe, incrementar contador
    if pregunta_normalizada in preguntas_frecuentes:
        preguntas_frecuentes[pregunta_normalizada]["count"] += 1
        preguntas_frecuentes[pregunta_normalizada]["respuestas"].append(respuesta)
        preguntas_frecuentes[pregunta_normalizada]["ultima_respuesta"] = respuesta
    else:
        # Primera vez que se ve esta pregunta
        preguntas_frecuentes[pregunta_normalizada] = {
            "count": 1,
            "pregunta_original": pregunta,
            "respuestas": [respuesta],
            "ultima_respuesta": respuesta
        }

    # Verificar si alcanzó el umbral para auto-caché
    if preguntas_frecuentes[pregunta_normalizada]["count"] == UMBRAL_AUTO_CACHE:
        # Calificar para caché automático
        print(f"\n FIX 57: Pregunta frecuente detectada ({UMBRAL_AUTO_CACHE} veces):")
        print(f"   Pregunta: '{pregunta[:60]}...'")
        print(f"   Respuesta más común: '{respuesta[:60]}...'")

        # Agregar a candidatos si no está ya
        if pregunta_normalizada not in candidatos_auto_cache:
            candidatos_auto_cache.append(pregunta_normalizada)
            print(f"    Agregado a candidatos de auto-caché")

    # Guardar en disco para persistencia
    preguntas_file = os.path.join(CACHE_DIR, "preguntas_frecuentes.json")
    with open(preguntas_file, 'w', encoding='utf-8') as f:
        json.dump(preguntas_frecuentes, f, ensure_ascii=False, indent=2)


def normalizar_frase_con_nombres(texto):
    """
    Detecta nombres propios en frases y los convierte en placeholders (NAME)
    para crear plantillas universales de audio

    Ejemplos:
    - "Entiendo, Rodrigo. ¿Me podrías..." → "Entiendo, (NAME). ¿Me podrías..."
    - "Mucho gusto, Juan." → "Mucho gusto, (NAME)."
    """
    import re

    # Patrones para detectar nombres después de palabras clave
    patrones_nombre = [
        r'\b(Mucho gusto|Perfecto|Entiendo|Claro|Gracias|Hola),\s+([A-ZÁÉÍÓÚÑ][a-záéíóúñ]{2,}(?:\s+[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)?)',  # "Mucho gusto, Juan"
        r'\b(señor|señora|don|doña)\s+([A-ZÁÉÍÓÚÑ][a-záéíóúñ]{2,}(?:\s+[A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)?)',  # "señor Juan"
    ]

    texto_normalizado = texto
    nombre_detectado = None

    for patron in patrones_nombre:
        match = re.search(patron, texto)
        if match:
            palabra_clave = match.group(1)
            nombre = match.group(2)

            # Filtrar palabras que no son nombres
            palabras_invalidas = ['verdad', 'favor', 'tiempo', 'momento', 'información', 'contacto', 'número']
            if nombre.lower() not in palabras_invalidas:
                # Reemplazar nombre con placeholder
                texto_normalizado = texto.replace(f"{palabra_clave}, {nombre}", f"{palabra_clave}, (NAME)")
                texto_normalizado = texto_normalizado.replace(f"{palabra_clave} {nombre}", f"{palabra_clave} (NAME)")
                nombre_detectado = nombre
                break

    return texto_normalizado, nombre_detectado


def registrar_frase_usada(texto):
    """
    Registra una frase usada y auto-genera caché si alcanza frecuencia mínima
    Detecta nombres y crea plantillas universales con (NAME)
    """
    # Normalizar texto (quitar espacios extras)
    texto_norm = " ".join(texto.split()).strip()

    # Detectar y normalizar nombres → plantilla universal
    texto_plantilla, nombre_detectado = normalizar_frase_con_nombres(texto_norm)

    # Si se detectó un nombre, usar la plantilla universal
    if nombre_detectado:
        print(f" Nombre detectado: '{nombre_detectado}' → Usando plantilla universal")
        texto_para_cache = texto_plantilla
    else:
        texto_para_cache = texto_norm

    # Generar key único basado en primeras palabras de la plantilla
    palabras = texto_para_cache.split()[:8]  # Primeras 8 palabras
    frase_key = "_".join(palabras).lower()

    # Incrementar contador
    if frase_key not in frase_stats:
        frase_stats[frase_key] = {
            "texto": texto_para_cache,  # Guardar plantilla universal
            "count": 0,
            "tiene_nombre": bool(nombre_detectado)
        }

    frase_stats[frase_key]["count"] += 1
    count = frase_stats[frase_key]["count"]

    # Guardar estadísticas en disco para persistencia
    guardar_stats_en_disco()

    # Auto-generar caché si alcanza frecuencia mínima
    if count == FRECUENCIA_MIN_CACHE and frase_key not in audio_cache:
        print(f"\n Frase frecuente detectada ({count} usos): {texto_para_cache[:50]}...")
        print(f"   Generando caché automático con Multilingual v2...")

        try:
            # Generar audio con Multilingual v2 usando la plantilla universal
            audio_generator = elevenlabs_client.text_to_speech.convert(
                voice_id=ELEVENLABS_VOICE_ID,
                text=texto_para_cache,  # Usar plantilla con (NAME) si tiene nombre
                model_id="eleven_multilingual_v2",
                output_format="mp3_44100_128"
            )

            # Guardar en archivo temporal
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.mp3')
            for chunk in audio_generator:
                temp_file.write(chunk)
            temp_file.close()

            # Agregar a caché en memoria
            audio_cache[frase_key] = temp_file.name

            # Guardar en disco para persistencia
            guardar_cache_en_disco(frase_key, texto_para_cache, temp_file.name)

            print(f"    Caché auto-generado: {frase_key}")
            if nombre_detectado:
                print(f"    Guardado como plantilla universal con (NAME)")

        except Exception as e:
            print(f"    Error generando caché automático: {e}")


def pre_generar_audios_cache():
    """Pre-genera frases comunes con Multilingual v2 para acento perfecto"""
    frases_comunes = {
        # Frases de sistema
        "error": "Lo siento, hubo un error. Le llamaremos más tarde.",
        "confirmacion_presencia": "Sí, estoy aquí.",  # FIX 138A: Respuesta instantánea para cliente desesperado

        # FIX 54B: Múltiples frases de "pensando" con voz de Bruce (variables)
        "pensando_1": "Déjeme ver...",
        "pensando_2": "Mmm, déjeme validarlo...",
        "pensando_3": "Un momento...",
        "pensando_4": "Déjeme revisar...",
        "pensando_5": "Mmm...",
        "pensando_6": "Déjeme checar...",
        "pensando_7": "Permítame un segundo...",
        "pensando_8": "Déjame verificar...",

        # FIX 93: Saludo inicial ACTUALIZADO (FIX 91) - más corto y natural
        # Versión 1: Cuando NO sabemos si es encargado (más común)
        "saludo_inicial": "Hola, que tal, buen dia, me comunico de la marca nioval, queria brindar informacion de nuestros productos ferreteros, ¿Se encuentra el encargado o encargada de compras?",

        # Versión 2: Cuando YA sabemos que es encargado (menos común)
        "saludo_inicial_encargado": "Hola, que tal, buen dia, me comunico de la marca nioval, queria brindar informacion de nuestros productos ferreteros, ¿Con quién tengo el gusto?",

        # Despedidas comunes
        "despedida_1": "Muchas gracias por su tiempo. Que tenga excelente tarde. Hasta pronto.",
        "despedida_2": "Perfecto. En las próximas dos horas le llega el catálogo completo por WhatsApp. Muchas gracias por su tiempo. Que tenga excelente tarde.",

        # FIX 76/79: Despedida específica para objeciones terminales (Truper/proveedor exclusivo)
        # FIX 79: Cambiada a despedida más cálida y profesional que deja la puerta abierta
        "despedida_objecion": "Perfecto, comprendo que ya trabajan con un proveedor fijo. Le agradezco mucho su tiempo y por la información. Si en el futuro necesitan comparar precios o buscan un proveedor adicional, con gusto pueden contactarnos. Que tenga excelente día.",

        # FIX 210: Segunda parte del saludo (cuando cliente responde "bueno", "sí", etc.)
        # Esta frase se usa cuando el cliente ya respondió al "Hola buen día"
        # Pre-generada para respuesta INSTANTÁNEA (0s delay)
        "segunda_parte_saludo": "Me comunico de la marca nioval, más que nada quería brindar informacion de nuestros productos ferreteros, ¿Se encontrara el encargado o encargada de compras?",
    }

    # FIX 59: Agregar respuestas cacheadas de respuestas_cache para pre-generación
    # Esto hace que las respuestas comunes sean INSTANTÁNEAS (0s delay)
    print(" Pre-generando caché de audios con Multilingual v2...")
    print(f" Agregando {len(respuestas_cache)} respuestas cacheadas al pre-generado...")
    for categoria, datos in respuestas_cache.items():
        cache_key = f"respuesta_cache_{categoria}"
        frases_comunes[cache_key] = datos["respuesta"]

    for key, texto in frases_comunes.items():
        # IMPORTANTE: Solo generar si NO existe en cache (ahorra créditos)
        if key in audio_cache:
            print(f"   Omitido: {key} (ya existe en cache)")
            continue

        try:
            print(f"   Generando: {key}...")
            # Usar Multilingual v2 para frases comunes (mejor acento)
            audio_generator = elevenlabs_client.text_to_speech.convert(
                voice_id=ELEVENLABS_VOICE_ID,
                text=texto,
                model_id="eleven_multilingual_v2",  # Mejor acento
                output_format="mp3_44100_128"
            )

            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.mp3')
            for chunk in audio_generator:
                temp_file.write(chunk)
            temp_file.close()

            audio_cache[key] = temp_file.name

            # Guardar en disco para persistencia
            guardar_cache_en_disco(key, texto, temp_file.name)
            print(f"   Cached: {key}")
        except Exception as e:
            print(f"   Error caching {key}: {e}")

    print(f" Caché completo: {len(audio_cache)} audios pre-generados\n")


def corregir_pronunciacion(texto):
    """Aplica correcciones fonéticas para mejorar pronunciación con Turbo v2"""
    # Reemplazos específicos para mejorar pronunciación
    correcciones = {
        # Palabras problemáticas con RR
        "ferreteros": "fe-rre-te-ros",
        "ferretería": "fe-rre-te-rí-a",
        "ferreterías": "fe-rre-te-rí-as",
        "tapagoteras": "ta-pa-go-te-ras",
        "grifería": "gri-fe-rí-a",
        "griferías": "gri-fe-rí-as",
        # Números
        "$1,500": "mil quinientos",
        "$5,000": "cinco mil",
        "15": "quince",
    }

    texto_corregido = texto
    for original, reemplazo in correcciones.items():
        texto_corregido = texto_corregido.replace(original, reemplazo)

    return texto_corregido


def concatenar_audios_mp3(audio_paths):
    """
    Concatena múltiples archivos MP3 en uno solo
    Usa pydub para concatenación sin problemas de compatibilidad
    """
    try:
        from pydub import AudioSegment

        combined = AudioSegment.empty()
        for path in audio_paths:
            audio = AudioSegment.from_mp3(path)
            combined += audio

        # Guardar en archivo temporal
        temp_output = tempfile.NamedTemporaryFile(delete=False, suffix='.mp3')
        combined.export(temp_output.name, format="mp3", bitrate="128k")
        temp_output.close()

        return temp_output.name

    except ImportError:
        # Si pydub no está disponible, usar concatenación simple de bytes
        print(" pydub no disponible, usando concatenación simple")
        temp_output = tempfile.NamedTemporaryFile(delete=False, suffix='.mp3')

        for path in audio_paths:
            with open(path, 'rb') as f:
                temp_output.write(f.read())

        temp_output.close()
        return temp_output.name


def generar_audio_con_nombre(texto_plantilla, nombre, frase_key_plantilla):
    """
    Genera audio compuesto usando plantilla universal

    Estrategia simplificada:
    1. La plantilla tiene (NAME) literal en el audio
    2. Generar el texto completo reemplazando (NAME) con el nombre real
    3. Generar solo ese audio (rápido porque es corto)

    Nota: Por ahora generamos el audio completo en vez de concatenar,
    pero aún aprovechamos la detección automática de nombres.
    """
    import time
    inicio = time.time()

    print(f" Generando audio con nombre específico: '{nombre}'")

    # Reemplazar (NAME) con el nombre real
    texto_final = texto_plantilla.replace("(NAME)", nombre)

    # Generar audio completo
    print(f"    Generando: '{texto_final[:50]}...'")
    audio_generator = elevenlabs_client.text_to_speech.convert(
        voice_id=ELEVENLABS_VOICE_ID,
        text=texto_final,
        model_id="eleven_multilingual_v2",
        output_format="mp3_44100_128"
    )

    # Guardar en archivo temporal
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.mp3')
    for chunk in audio_generator:
        temp_file.write(chunk)
    temp_file.close()

    print(f"    Audio generado en {(time.time() - inicio):.2f}s")
    return temp_file.name


def generar_audio_elevenlabs(texto, audio_id, usar_cache_key=None):
    """
    Genera audio con ElevenLabs usando SOLO Multilingual v2 (mejor calidad)
    - Caché manual: Usa audio pre-generado (0s delay)
    - Caché auto: Busca en caché auto-generado de frases frecuentes
    - Plantillas con nombres: Concatena plantilla + nombre específico
    - Genera nuevo: Multilingual v2 para mejor acento mexicano
    """
    try:
        import time
        inicio = time.time()

        # PASO 1: Si hay cache key manual, usar audio pre-generado
        if usar_cache_key and usar_cache_key in audio_cache:
            audio_files[audio_id] = audio_cache[usar_cache_key]
            print(f" Caché manual: {usar_cache_key} (0s delay)")
            return audio_id

        # PASO 2: Detectar si tiene nombre y buscar plantilla correspondiente
        texto_plantilla, nombre_detectado = normalizar_frase_con_nombres(texto)

        if nombre_detectado:
            # Buscar plantilla en caché
            palabras_plantilla = " ".join(texto_plantilla.split()[:8]).lower()
            frase_key_plantilla = "_".join(palabras_plantilla.split())

            if frase_key_plantilla in audio_cache:
                print(f" Usando plantilla universal + nombre '{nombre_detectado}'")
                audio_compuesto = generar_audio_con_nombre(
                    texto_plantilla,
                    nombre_detectado,
                    frase_key_plantilla
                )

                if audio_compuesto:
                    audio_files[audio_id] = audio_compuesto
                    print(f" Audio compuesto listo (plantilla + nombre)")
                    return audio_id
                else:
                    print(f" Error en audio compuesto, generando completo...")
            else:
                print(f"ℹ Plantilla no en caché, generando completo...")

        # PASO 3: Buscar en caché auto-generado (sin nombre)
        # FIX 191: NUNCA usar caché si el texto contiene despedidas de cierre
        # Esto previene que Bruce diga "ya lo tengo anotado" cuando el cliente SIGUE deletreando
        palabras_cierre = ["perfecto ya lo tengo anotado", "perfecto, ya lo tengo anotado",
                          "le llegará el catálogo", "muchas gracias por su tiempo"]

        texto_lower = texto.lower()
        es_despedida_cierre = any(palabra in texto_lower for palabra in palabras_cierre)

        if es_despedida_cierre:
            print(f" FIX 191: Bloqueando caché de despedida - cliente aún puede estar hablando")
            print(f"   Texto: '{texto[:60]}...'")
            # NO usar caché - dejar que GPT decida si es momento de despedirse
        else:
            palabras_inicio = " ".join(texto.split()[:8]).lower()
            frase_key = "_".join(palabras_inicio.split())

            if frase_key in audio_cache:
                audio_files[audio_id] = audio_cache[frase_key]
                print(f" Caché AUTO: {frase_key[:40]}... (0s delay)")
                return audio_id

        # PASO 4: Registrar frase para estadísticas (auto-genera caché si es frecuente)
        registrar_frase_usada(texto)

        # Aplicar correcciones fonéticas
        texto_corregido = corregir_pronunciacion(texto)

        # FIX 197: SIEMPRE usar Multilingual v2 (acento mexicano natural)
        # Turbo v2 es más rápido PERO pierde acento mexicano → suena extranjero
        # Prioridad: CALIDAD DE ACENTO > VELOCIDAD
        palabras = len(texto_corregido.split())
        modelo = "eleven_multilingual_v2"
        print(f" FIX 197: Usando Multilingual v2 ({palabras} palabras, acento mexicano)")

        # FIX 162A: Generar audio con retry automático
        max_intentos = 2
        intento = 1

        while intento <= max_intentos:
            try:
                print(f" FIX 162A: Generando audio (intento {intento}/{max_intentos})")

                audio_generator = elevenlabs_client.text_to_speech.convert(
                    voice_id=ELEVENLABS_VOICE_ID,
                    text=texto_corregido,
                    model_id=modelo,
                    output_format="mp3_44100_128"
                )

                # Guardar en archivo temporal con streaming
                temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.mp3')
                chunk_count = 0
                for chunk in audio_generator:
                    temp_file.write(chunk)
                    chunk_count += 1
                    if chunk_count == 1:
                        print(f" Primer chunk en {(time.time() - inicio):.2f}s")
                temp_file.close()

                # Guardar ruta del archivo
                audio_files[audio_id] = temp_file.name
                print(f" Audio en {(time.time() - inicio):.2f}s ({chunk_count} chunks, {modelo})")

                if intento > 1:
                    print(f" FIX 162A: Audio generado exitosamente en intento {intento}")

                return audio_id

            except Exception as e_retry:
                print(f" FIX 162A: Error en intento {intento}/{max_intentos}: {type(e_retry).__name__}")

                if intento < max_intentos:
                    print(f" FIX 162A: Reintentando en 1 segundo...")
                    time.sleep(1)
                    intento += 1
                else:
                    # Último intento falló - lanzar excepción para que la maneje el except principal
                    raise e_retry

    except Exception as e:
        print(f" FIX 162A: Error generando audio ElevenLabs después de {max_intentos} intentos: {e}")
        print(f"   Tipo de error: {type(e).__name__}")
        print(f"   Texto que causó error: {texto[:100]}...")
        print(f"   Traceback completo:")
        traceback.print_exc()
        print(f" FIX 162A: CRÍTICO - NO usar fallback Twilio (causa desconfianza)")
        # FIX 208: Registrar error en buffer
        log_evento(f"ERROR ELEVENLABS: {type(e).__name__} - {str(e)[:200]}", "ERROR")
        return None


def generar_audio_async(texto, audio_id):
    """Wrapper para generar audio en background thread"""
    thread = threading.Thread(target=generar_audio_elevenlabs, args=(texto, audio_id))
    thread.daemon = True
    thread.start()
    return audio_id


@app.route("/audio/<audio_id>")
def servir_audio(audio_id):
    """Sirve el archivo de audio generado (con espera inteligente)"""
    import time
    import io

    # Esperar hasta 3 segundos si el audio aún no está listo
    max_wait = 3
    waited = 0
    while audio_id not in audio_files and waited < max_wait:
        time.sleep(0.1)
        waited += 0.1

    if audio_id in audio_files:
        audio_data = audio_files[audio_id]

        # Si es bytes, envolver en BytesIO para send_file
        if isinstance(audio_data, bytes):
            return send_file(io.BytesIO(audio_data), mimetype='audio/mpeg')

        # Si es string (ruta), send_file lo maneja directamente
        return send_file(audio_data, mimetype='audio/mpeg')

    return "Audio not found", 404


@app.route("/audio_cache/<cache_key>")
def servir_audio_cache(cache_key):
    """Sirve archivos de audio pre-cacheados (0s delay)"""
    import io

    if cache_key in audio_cache:
        audio_data = audio_cache[cache_key]

        # Si es bytes, envolver en BytesIO
        if isinstance(audio_data, bytes):
            return send_file(io.BytesIO(audio_data), mimetype='audio/mpeg')

        # Si es string (ruta de archivo), send_file lo maneja
        return send_file(audio_data, mimetype='audio/mpeg')

    return "Audio cache not found", 404


def post_procesar_transcripcion_email(texto_transcrito):
    """
    FIX 198: Reconstruye emails a partir de transcripciones verbales
    Ejemplo: "juan punto garcia arroba gmail punto com" → "juan.garcia@gmail.com"
    """
    import re

    texto = texto_transcrito.lower()

    # Reemplazar palabras verbales por símbolos
    replacements = {
        " arroba ": "@",
        " punto com": ".com",
        " punto es": ".es",
        " punto mx": ".mx",
        " guión bajo ": "_",
        " guion bajo ": "_",
        " guión medio ": "-",
        " guion medio ": "-",
        " guión ": "-",
        " guion ": "-",
    }

    for palabra, simbolo in replacements.items():
        texto = texto.replace(palabra, simbolo)

    # Detectar proveedores comunes y reconstruir
    proveedores = ["gmail", "hotmail", "yahoo", "outlook", "live", "icloud"]

    for proveedor in proveedores:
        # Detectar patrones como "nombre gmail com" → "nombre@gmail.com"
        pattern = rf"(\S+)\s+{proveedor}\s+com"
        match = re.search(pattern, texto)
        if match:
            nombre = match.group(1)
            email_reconstruido = f"{nombre}@{proveedor}.com"
            texto = re.sub(pattern, email_reconstruido, texto)
            print(f"    FIX 198: Email reconstruido: {email_reconstruido}")

    # Reemplazar " punto " en contextos de email
    # Solo si ya detectamos @ (para no afectar conversación normal)
    if "@" in texto:
        texto = texto.replace(" punto ", ".")

    return texto


def transcribir_con_whisper(recording_url, whisper_prompt=None, post_procesar_email=False):
    """
    FIX 60: Transcribe audio usando Whisper API de OpenAI
    FIX 198: Agrega soporte para prompt contextual y post-procesamiento de emails

    Args:
        recording_url: URL de la grabación de Twilio
        whisper_prompt: Prompt contextual para mejorar transcripción (FIX 198)
        post_procesar_email: Si True, aplica post-procesamiento de emails (FIX 198)

    Returns:
        str: Texto transcrito o None si falla
    """
    import time
    inicio = time.time()

    try:
        print(f" FIX 60: Descargando grabación de Twilio...")
        print(f"   URL: {recording_url}")

        # FIX 62: Descargar audio de Twilio con autenticación (timeout agresivo)
        response = requests.get(
            recording_url,
            auth=(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN),
            timeout=5  # FIX 62: Reducido de 10s a 5s
        )
        response.raise_for_status()

        tiempo_descarga = time.time() - inicio
        audio_bytes = len(response.content)
        print(f"    Audio descargado en {tiempo_descarga:.3f}s ({audio_bytes} bytes)")

        # FIX 268: Validar tamaño mínimo de audio antes de enviar a Whisper
        # Whisper requiere mínimo 0.1 segundos de audio (~1600 bytes para WAV mono 8kHz)
        # Si el audio es muy pequeño, es silencio o ruido - no vale la pena transcribir
        AUDIO_MIN_BYTES = 2000  # ~0.125 segundos de audio
        if audio_bytes < AUDIO_MIN_BYTES:
            print(f"    FIX 268: Audio muy corto ({audio_bytes} bytes < {AUDIO_MIN_BYTES}) - probablemente silencio")
            print(f"   ℹ Saltando Whisper para evitar error 'audio_too_short'")
            return None

        # Guardar temporalmente para Whisper
        temp_audio = tempfile.NamedTemporaryFile(delete=False, suffix='.wav')
        temp_audio.write(response.content)
        temp_audio.close()

        print(f" FIX 60: Transcribiendo con Whisper API...")
        if whisper_prompt:
            print(f"    FIX 198: Usando prompt contextual")
        inicio_whisper = time.time()

        # FIX 198: Transcribir con Whisper con prompt contextual opcional
        with open(temp_audio.name, 'rb') as audio_file:
            if whisper_prompt:
                transcription = openai_client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    language="es",
                    prompt=whisper_prompt,  # FIX 198: Prompt para mejorar transcripción
                    response_format="text"
                )
            else:
                transcription = openai_client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    language="es",
                    response_format="text"
                )

        tiempo_whisper = time.time() - inicio_whisper
        tiempo_total = time.time() - inicio

        # Limpiar archivo temporal
        os.unlink(temp_audio.name)

        texto = transcription.strip() if isinstance(transcription, str) else transcription.text.strip()

        # FIX 198: Post-procesamiento de emails si está activado
        if post_procesar_email and texto:
            texto_original = texto
            texto = post_procesar_transcripcion_email(texto)

            if texto_original != texto:
                print(f"    FIX 198: Transcripción mejorada")
                print(f"      Antes: '{texto_original}'")
                print(f"      Después: '{texto}'")

        print(f"    Transcripción completada en {tiempo_whisper:.3f}s")
        print(f"     Tiempo total: {tiempo_total:.3f}s (descarga: {tiempo_descarga:.3f}s + whisper: {tiempo_whisper:.3f}s)")
        print(f"    Texto: '{texto}'")

        return texto

    except Exception as e:
        tiempo_total = time.time() - inicio
        print(f"    Error en transcripción Whisper después de {tiempo_total:.3f}s: {e}")
        return None


@app.route("/iniciar-llamada", methods=["POST"])
def iniciar_llamada():
    """
    Endpoint para iniciar una llamada saliente

    Body JSON:
    {
        "telefono": "+52XXXXXXXXXX",
        "nombre_negocio": "Ferretería ejemplo",
        "contacto_info": {...}  # Información completa del contacto (opcional)
    }
    """
    try:
        debug_print(f"\n DEBUG 1: /iniciar-llamada - Request recibido")

        data = request.json
        print(f" DEBUG 2: JSON parseado correctamente")

        telefono_destino = data.get("telefono")
        nombre_negocio = data.get("nombre_negocio", "cliente")
        contacto_info = data.get("contacto_info", None)
        # FIX 179: Flag para deshabilitar reintentos automáticos (usado por llamadas masivas)
        deshabilitar_reintentos = data.get("deshabilitar_reintentos", False)

        print(f" DEBUG 3: Datos extraídos - Tel: {telefono_destino}, Negocio: {nombre_negocio}")
        if deshabilitar_reintentos:
            print(f" FIX 179: Reintentos automáticos DESHABILITADOS para esta llamada")

        if not telefono_destino:
            print(f" ERROR: Teléfono no proporcionado")
            return {"error": "Teléfono requerido"}, 400

        print(f" DEBUG 4: Iniciando llamada Twilio a {telefono_destino}")

        # FIX 85: DESHABILITAR machine_detection para reducir delay de 11s a 2-3s
        # PROBLEMA: DetectMessageEnd hace que Twilio ESPERE 5-10s antes de hablar
        # SOLUCIÓN: Deshabilitar y detectar buzón por transcripción (ya implementado en agente_ventas.py)
        call = twilio_client.calls.create(
            to=telefono_destino,
            from_=TWILIO_PHONE_NUMBER,
            url=request.url_root + "webhook-voz",
            method="POST",
            # FIX 271: Removido record=True - ahora usamos <Start><Recording> en TwiML
            # que es asíncrono y no interfiere con los <Record> de transcripción
            # machine_detection="DetectMessageEnd",  # FIX 85: DESHABILITADO (causaba delay de 11s)
            # machine_detection_timeout=5,  # FIX 85: DESHABILITADO
            status_callback=request.url_root + "status-callback",  # Webhook para estado de llamada
            status_callback_event=["completed"]  # Notificar cuando termine
        )

        print(f" DEBUG 5: Llamada Twilio creada - SID: {call.sid}")
        # FIX 208/284: Registrar inicio de llamada (sin duplicar prefijo BRUCE)
        bruce_id_log = contacto_info.get("bruce_id", "N/A") if contacto_info else "N/A"
        log_evento(f"{bruce_id_log} - LLAMADA INICIADA a {telefono_destino} ({nombre_negocio})", "LLAMADA")

        # Guardar info del contacto para usar en el webhook
        if contacto_info:
            # Si se envió contacto_info completo, usarlo
            contactos_llamadas[call.sid] = contacto_info
            # FIX 179: Guardar flag de reintentos
            contactos_llamadas[call.sid]['deshabilitar_reintentos'] = deshabilitar_reintentos
            print(f" Contacto completo guardado para Call SID {call.sid[:10]}... (fila {contacto_info.get('fila', 'N/A')})")
        else:
            # Si no, guardar solo lo básico (compatibilidad con llamadas antiguas)
            contactos_llamadas[call.sid] = {
                "telefono": telefono_destino,
                "nombre_negocio": nombre_negocio,
                # FIX 179: Guardar flag de reintentos
                "deshabilitar_reintentos": deshabilitar_reintentos
            }
            print(f" Contacto básico guardado para Call SID {call.sid[:10]}...")

        print(f" DEBUG 6: Retornando respuesta exitosa")

        return {
            "success": True,
            "call_sid": call.sid,
            "status": call.status
        }

    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"\n ERROR EN /iniciar-llamada:")
        print(f" Tipo de error: {type(e).__name__}")
        print(f" Mensaje: {str(e)}")
        print(f" Stack trace completo:")
        print(error_trace)
        return {"error": str(e), "type": type(e).__name__, "traceback": error_trace}, 500


@app.route("/webhook-voz", methods=["GET", "POST"])
def webhook_voz():
    """
    Webhook que Twilio llama cuando se contesta la llamada
    """
    # Twilio puede enviar GET o POST
    if request.method == "GET":
        call_sid = request.args.get("CallSid")
    else:
        call_sid = request.form.get("CallSid")

    # Obtener info del contacto si existe
    contacto_info = contactos_llamadas.get(call_sid, {})

    # Verificar si hay cambio de número y cargar historial previo
    historial_previo = None
    if contacto_info and sheets_manager:
        fila = contacto_info.get('fila') or contacto_info.get('ID')
        if fila:
            # Verificar si el número cambió
            if sheets_manager.verificar_cambio_numero(fila):
                print(f"\n NÚMERO CAMBIÓ - Cargando historial previo para contexto...")
                historial_previo = sheets_manager.obtener_historial_completo(fila)

                if any(historial_previo.values()):
                    print(f" Historial cargado:")
                    if historial_previo['referencia']:
                        print(f"   - Referencia: {historial_previo['referencia'][:80]}...")
                    if historial_previo['intentos_buzon']:
                        print(f"   - Intentos buzón: {historial_previo['intentos_buzon']}")
                    if historial_previo['contexto_reprogramacion']:
                        print(f"   - Contexto: {historial_previo['contexto_reprogramacion'][:80]}...")

                # Agregar historial al contacto_info para que el agente lo use
                contacto_info['historial_previo'] = historial_previo

    # Generar ID BRUCE para esta conversación (si logs_manager está disponible)
    bruce_id = None
    if logs_manager:
        bruce_id = logs_manager.generar_nuevo_id_bruce()
        print(f" ID BRUCE generado: {bruce_id}")

    # Crear nueva conversación con Google Sheets y WhatsApp Validator
    agente = AgenteVentas(
        contacto_info=contacto_info,
        sheets_manager=sheets_manager,
        resultados_manager=resultados_manager,
        whatsapp_validator=whatsapp_validator
    )
    agente.call_sid = call_sid  # Guardar el Call SID de Twilio
    agente.bruce_id = bruce_id  # Guardar el ID BRUCE
    agente.lead_data["bruce_id"] = bruce_id  # FIX 272.3: Guardar también en lead_data
    conversaciones_activas[call_sid] = agente

    # Mensaje inicial
    mensaje_inicial = agente.iniciar_conversacion()

    # FIX 52: USAR TWILIO TTS para mensaje inicial (0s delay, instantáneo)
    # ElevenLabs puede tardar 2-4s en generar, causando que cliente cuelgue
    # Twilio TTS es instantáneo y suficiente para saludo inicial

    # Registrar mensaje inicial de Bruce en LOGS
    if logs_manager and bruce_id:
        nombre_tienda = contacto_info.get('nombre_negocio', '') if contacto_info else ''
        logs_manager.registrar_mensaje_bruce(
            bruce_id,
            mensaje_inicial,
            desde_cache=True,  # Twilio TTS es como caché (instantáneo)
            cache_key="twilio_tts_inicial",
            nombre_tienda=nombre_tienda
        )

    # Crear respuesta TwiML
    response = VoiceResponse()

    # PAUSA DE 1 SEGUNDO - Dar tiempo al cliente de decir "Hola" primero
    response.pause(length=1)

    # FIX 53: VOLVER A ELEVENLABS PRE-GRABADO (voz masculina de Bruce)
    # Problema FIX 52: Polly.Mia es FEMENINA (Bruce debe ser hombre)
    # Solución: Usar caché de ElevenLabs (pre-generado al inicio, 0s delay)

    audio_id = f"inicial_{call_sid}"

    # FIX 114: Detectar saludo corto del FIX 112 para usar caché
    # Después del FIX 112, el saludo inicial es solo "Hola, buen dia"
    usa_cache_saludo_corto = mensaje_inicial.strip().lower() == "hola, buen dia"

    # Mantener compatibilidad con versiones antiguas (por si acaso)
    usa_cache_saludo_normal = "me comunico de la marca nioval, queria brindar informacion de nuestros productos ferreteros, ¿Se encuentra el encargado" in mensaje_inicial
    usa_cache_saludo_encargado = "me comunico de la marca nioval, queria brindar informacion de nuestros productos ferreteros, ¿Con quién tengo el gusto" in mensaje_inicial

    if usa_cache_saludo_corto and "saludo_inicial" in audio_cache:
        # FIX 114: Usar audio pre-generado del saludo corto FIX 112 (0s delay, voz Bruce)
        audio_files[audio_id] = audio_cache["saludo_inicial"]
        print(f" FIX 114: Saludo corto 'Hola, buen dia' desde caché (0s delay, voz Bruce)")
    elif usa_cache_saludo_normal and "saludo_inicial" in audio_cache:
        # Usar audio pre-generado del caché - versión normal (0s delay, voz Bruce)
        audio_files[audio_id] = audio_cache["saludo_inicial"]
        print(f" Saludo inicial (normal) desde caché (0s delay, voz Bruce)")
    elif usa_cache_saludo_encargado and "saludo_inicial_encargado" in audio_cache:
        # Usar audio pre-generado del caché - versión encargado (0s delay, voz Bruce)
        audio_files[audio_id] = audio_cache["saludo_inicial_encargado"]
        print(f" Saludo inicial (encargado) desde caché (0s delay, voz Bruce)")
    else:
        # Fallback: generar con ElevenLabs si no hay caché
        print(f" Generando saludo inicial con ElevenLabs (caché no disponible - tardará 2-4s)")
        generar_audio_elevenlabs(mensaje_inicial, audio_id)

    # FIX 212: DEEPGRAM STREAMING - Transcripción en tiempo real
    # Iniciar MediaStream hacia nuestro servidor WebSocket para Deepgram
    if DEEPGRAM_AVAILABLE and USE_DEEPGRAM:
        print(f" FIX 212: Iniciando MediaStream para Deepgram")

        # Obtener URL base del servidor (para WebSocket)
        # En Railway: wss://nioval-webhook-server-production.up.railway.app/media-stream
        ws_url = os.getenv("WEBSOCKET_URL")
        if not ws_url:
            # Construir URL automáticamente
            base_url = request.url_root.replace("http://", "wss://").replace("https://", "wss://")
            ws_url = base_url.rstrip("/") + "/media-stream"

        # Agregar <Start><Stream> para enviar audio a Deepgram
        start = Start()
        stream = Stream(url=ws_url)
        stream.parameter(name="CallSid", value=call_sid)
        start.append(stream)
        response.append(start)

        print(f"   WebSocket URL: {ws_url}")

    # FIX 271: Grabar llamada COMPLETA con <Start><Recording> (asíncrono)
    # Esto NO interfiere con los <Record> que usamos para transcripción
    # La grabación continúa en background durante toda la llamada
    start_recording = Start()
    start_recording.recording(
        recording_status_callback=request.url_root + "grabacion-llamada-completa",
        recording_status_callback_method="POST",
        recording_status_callback_event="completed"
    )
    response.append(start_recording)
    print(f"    FIX 271: Grabación asíncrona de llamada completa iniciada")

    # FIX 214: ELIMINAR COSTOS DE TWILIO SPEECH RECOGNITION
    # Twilio cobra por usar input="speech" con language (Speech Recognition)
    # Ahora usamos SOLO Deepgram para transcripción (más barato y preciso)
    #
    # Arquitectura FIX 214:
    # 1. Reproducir audio con <Play>
    # 2. Usar <Record> para capturar respuesta del cliente (NO cobra speech)
    # 3. Deepgram transcribe en tiempo real vía MediaStream
    # 4. Record termina por silencio, callback a /procesar-respuesta

    # FIX 455: Limpiar transcripciones acumuladas antes de reproducir audio inicial
    import time as time_module  # FIX 455: Import local para evitar conflictos
    if call_sid in deepgram_transcripciones and deepgram_transcripciones[call_sid]:
        print(f" FIX 455: Limpiando {len(deepgram_transcripciones[call_sid])} transcripciones previas (audio inicial)")
        deepgram_transcripciones[call_sid] = []
        if call_sid in deepgram_ultima_final:
            deepgram_ultima_final[call_sid] = {}
    bruce_audio_enviado_timestamp[call_sid] = time_module.time()

    # Reproducir el audio primero
    audio_url = request.url_root + f"audio/{audio_id}"
    response.play(audio_url)

    # FIX 214: Usar Record en lugar de Gather para evitar cobros de Speech Recognition
    # Record solo cobra minutos de voz (mucho más barato que Speech Recognition)
    # Deepgram MediaStream ya está transcribiendo en paralelo
    from twilio.twiml.voice_response import Record

    # FIX 223: Reducir max_length para evitar delays de 20-40s
    # Problema: Cliente repite varias veces sin pausar → Record no termina
    # FIX 475: BRUCE1432 - Reducir timeout de 2s a 1s para el primer mensaje (saludo)
    # Saludos como "Buenos días" o "Bueno" son cortos, no necesitan 2s de silencio
    response.record(
        action="/procesar-respuesta",
        method="POST",
        max_length=1,  # FIX 223: Reducido de 30s a 10s máximo
        timeout=1,  # FIX 475: Reducido de 2s a 1s (saludos son cortos)
        play_beep=False,
        trim="trim-silence",
        recording_status_callback="/grabacion-status",
        recording_status_callback_method="POST"
    )

    print(f"    FIX 214: Usando Record + Deepgram (sin Speech Recognition de Twilio)")

    return Response(str(response), mimetype="text/xml")


@app.route("/grabacion-status", methods=["POST"])
def grabacion_status():
    """FIX 214: Callback para status de grabación (RecordVerb - fragmentos)"""
    recording_sid = request.form.get("RecordingSid", "")
    recording_status = request.form.get("RecordingStatus", "")
    recording_url = request.form.get("RecordingUrl", "")
    call_sid = request.form.get("CallSid", "")

    print(f" FIX 214: Grabación fragmento {recording_status} - CallSid: {call_sid}")
    if recording_url:
        print(f"   URL: {recording_url}")

    return Response("OK", mimetype="text/plain")


@app.route("/grabacion-llamada-completa", methods=["GET", "POST"])
def grabacion_llamada_completa():
    """
    FIX 267/269: Callback para grabación COMPLETA de la llamada (record=True en calls.create)
    Esta es la grabación de TODA la llamada, no los fragmentos de RecordVerb
    FIX 269: Aceptar GET y POST porque Twilio puede enviar cualquiera de los dos
    """
    # FIX 269: Obtener parámetros de GET o POST
    if request.method == "GET":
        recording_sid = request.args.get("RecordingSid", "")
        recording_status = request.args.get("RecordingStatus", "")
        recording_url = request.args.get("RecordingUrl", "")
        recording_duration = request.args.get("RecordingDuration", "0")
        call_sid = request.args.get("CallSid", "")
    else:
        recording_sid = request.form.get("RecordingSid", "")
        recording_status = request.form.get("RecordingStatus", "")
        recording_url = request.form.get("RecordingUrl", "")
        recording_duration = request.form.get("RecordingDuration", "0")
        call_sid = request.form.get("CallSid", "")

    print(f"\n FIX 267: GRABACIÓN COMPLETA DE LLAMADA")
    print(f"   CallSid: {call_sid}")
    print(f"   RecordingSid: {recording_sid}")
    print(f"   Status: {recording_status}")
    print(f"   Duración: {recording_duration} segundos")
    if recording_url:
        print(f"   URL: {recording_url}")
        # Guardar URL en el agente si está disponible
        agente = conversaciones_activas.get(call_sid)
        if agente:
            agente.lead_data["recording_url"] = recording_url
            agente.lead_data["recording_duration"] = recording_duration
            print(f"    URL guardada en lead_data del agente")
        else:
            print(f"    Agente no encontrado en conversaciones_activas (llamada ya terminó)")

        # FIX 272: Guardar URL asociada al bruce_id para el historial
        bruce_id = callsid_to_bruceid.get(call_sid)
        if bruce_id:
            grabaciones_por_bruce[bruce_id] = recording_url
            print(f"    FIX 272: Grabación asociada a {bruce_id}")

            # Actualizar historial existente
            for llamada in historial_llamadas:
                if llamada.get("bruce_id") == bruce_id:
                    llamada["detalles"]["recording_url"] = recording_url
                    print(f"    FIX 272: Historial actualizado con URL de grabación")
                    # FIX 272.2: Persistir cambio en disco
                    guardar_historial()
                    break

    return Response("OK", mimetype="text/plain")


@app.route("/procesar-respuesta", methods=["GET", "POST"])
def procesar_respuesta():
    """
    FIX 60/214: Procesa la respuesta del cliente y continúa la conversación
    ACTUALIZADO FIX 214: Ya no usa SpeechResult de Twilio (ahorra costos)
    Prioridad: Deepgram (tiempo real) > Whisper (RecordingUrl) > vacío
    """
    # Twilio puede enviar GET o POST
    if request.method == "GET":
        call_sid = request.args.get("CallSid")
        speech_result = request.args.get("SpeechResult", "")
        recording_url = request.args.get("RecordingUrl", "")  # FIX 60
        call_status = request.args.get("CallStatus", "")
        answered_by = request.args.get("AnsweredBy", "")

        # DEBUG: Log todos los parámetros de Twilio
        print(f"\n DEBUG - Parámetros Twilio (GET):")
        print(f"   CallSid: {call_sid}")
        print(f"   CallStatus: {call_status}")
        print(f"   AnsweredBy: {answered_by}")
        print(f"   SpeechResult: '{speech_result}'")
        print(f"   RecordingUrl: '{recording_url}'")  # FIX 60
        if request.args.get("Digits"):
            print(f"   Digits: {request.args.get('Digits')}")
    else:
        call_sid = request.form.get("CallSid")
        speech_result = request.form.get("SpeechResult", "")
        recording_url = request.form.get("RecordingUrl", "")  # FIX 60
        call_status = request.form.get("CallStatus", "")
        answered_by = request.form.get("AnsweredBy", "")

        # DEBUG: Log todos los parámetros de Twilio
        print(f"\n DEBUG - Parámetros Twilio (POST):")
        print(f"   CallSid: {call_sid}")
        print(f"   CallStatus: {call_status}")
        print(f"   AnsweredBy: {answered_by}")
        print(f"   SpeechResult: '{speech_result}'")
        print(f"   RecordingUrl: '{recording_url}'")  # FIX 60
        if request.form.get("Digits"):
            print(f"   Digits: {request.form.get('Digits')}")

    # FIX 212: PRIORIZAR DEEPGRAM si está disponible (tiempo real, 90%+ precisión)
    # Fallback: Whisper API (96-99% precisión, pero con delay)
    # Último recurso: Transcripción de Twilio
    usar_deepgram = False
    usar_whisper = False
    transcripcion_deepgram = None
    transcripcion_whisper = None

    # FIX 212/217/218/219/401: Verificar si hay transcripción de Deepgram disponible
    # FIX 401: Deepgram es el sistema PRINCIPAL - esperar suficiente tiempo
    # FIX 511: BRUCE1546 - Timeout escalonado para reducir delays de 42s
    #   - 3s: Si hay PARCIAL disponible, usarla (no esperar 5s por FINAL)
    #   - 5s: Timeout absoluto (fallback completo)
    # FIX 534: Timeout progresivo - reducir timeouts si ya hubo timeouts previos
    import time

    # FIX 534: Obtener contador de timeouts del agente para ajuste progresivo
    agente_temp = conversaciones_activas.get(call_sid)
    timeouts_previos = getattr(agente_temp, 'timeouts_deepgram', 0) if agente_temp else 0

    # FIX 534: Ajustar timeouts según historial
    if timeouts_previos >= 2:
        # Después de 2+ timeouts, ser muy agresivo
        max_wait_deepgram = 2.5  # FIX 534: Reducido de 5s a 2.5s
        max_wait_parcial_fallback = 1.5  # FIX 534: Reducido de 3s a 1.5s
        print(f"   FIX 534: Timeouts previos={timeouts_previos} - usando timeouts reducidos ({max_wait_deepgram}s/{max_wait_parcial_fallback}s)")
    elif timeouts_previos == 1:
        # Después de 1 timeout, ser moderadamente agresivo
        max_wait_deepgram = 3.5  # FIX 534: Reducido de 5s a 3.5s
        max_wait_parcial_fallback = 2.0  # FIX 534: Reducido de 3s a 2s
        print(f"   FIX 534: Timeouts previos={timeouts_previos} - usando timeouts moderados ({max_wait_deepgram}s/{max_wait_parcial_fallback}s)")
    else:
        # Sin timeouts previos, usar valores normales
        max_wait_deepgram = 5.0  # FIX 401: Timeout absoluto máximo
        max_wait_parcial_fallback = 3.0  # FIX 511: Usar PARCIAL después de 3s si no hay FINAL
    wait_interval = 0.05  # FIX 219: Revisar cada 50ms (más frecuente)
    tiempo_esperado = 0
    parcial_disponible_desde = None  # FIX 511: Cuándo detectamos primera PARCIAL

    if DEEPGRAM_AVAILABLE and USE_DEEPGRAM:
        # FIX 451: Variable para rastrear si esperamos FINAL
        esperando_final = True
        tiempo_espera_final_extra = 0.0
        # FIX 475 (AUDITORIA W04): Reducir timeout de 1.0s a 0.3s para TODAS las transcripciones
        # Latencias de 30-115s observadas causando pérdida de leads
        # Benchmark industria: <300ms, nuevo timeout: 300ms universal
        max_espera_final_extra = 0.3  # Máximo 0.3s adicional esperando FINAL después de PARCIAL

        # FIX 477: BRUCE1443 - Reducir espera para saludos cortos (reduce delay en 2do mensaje)
        # Si la PARCIAL es un saludo corto, no esperar 1s completo por FINAL
        saludos_cortos = [
            'bueno', 'sí', 'si', 'alo', 'aló', 'diga', 'digame', 'dígame',
            'buenos días', 'buenos dias', 'buenas tardes', 'buenas noches',
            'hola', 'mande', 'a sus órdenes', 'a sus ordenes', 'para servirle'
        ]

        while tiempo_esperado < max_wait_deepgram:
            # FIX 490: Proteger lectura concurrente de transcripciones con lock
            with deepgram_transcripciones_lock:
                if call_sid in deepgram_transcripciones:
                    transcripciones_dg = deepgram_transcripciones.get(call_sid, []).copy()  # Copiar para evitar modificación externa
                else:
                    transcripciones_dg = []

            # Obtener info de última FINAL (también protegida)
            with deepgram_ultima_final_lock:
                info_ultima = deepgram_ultima_final.get(call_sid, {})
                es_final = info_ultima.get("es_final", False)

            if transcripciones_dg:
                # FIX 511: Registrar cuándo detectamos primera PARCIAL
                if parcial_disponible_desde is None:
                    parcial_disponible_desde = time.time()

                # FIX 451: Verificar si la transcripción es FINAL
                if not es_final and esperando_final:
                    # FIX 477: Si la PARCIAL es saludo corto, reducir tiempo de espera
                    parcial_actual = transcripciones_dg[-1].strip().lower() if transcripciones_dg else ""
                    es_saludo_corto = any(parcial_actual == saludo or parcial_actual.startswith(saludo + '.') or parcial_actual.startswith(saludo + ',') for saludo in saludos_cortos)

                    # FIX 511: Si ya pasaron 3s desde que tenemos PARCIAL, usarla inmediatamente
                    # Esto reduce delays de 5s a 3s cuando Deepgram tarda en enviar FINAL
                    tiempo_con_parcial = time.time() - parcial_disponible_desde
                    if tiempo_con_parcial >= max_wait_parcial_fallback:
                        print(f"\n FIX 511: PARCIAL disponible por {tiempo_con_parcial:.1f}s sin FINAL - usando como fallback")
                        print(f"   PARCIAL: '{parcial_actual}'")
                        # Forzar uso de PARCIAL
                        esperando_final = False
                        tiempo_espera_final_extra = max_espera_final_extra + 1  # Saltar la espera

                    # FIX 475 (AUDITORIA W04): Timeout universal de 0.3s para todas las transcripciones
                    # No diferenciar entre saludos y otras frases - consistencia de latencia
                    max_espera_ajustada = max_espera_final_extra  # Ya es 0.3s universal

                    if es_saludo_corto and tiempo_espera_final_extra == 0:
                        print(f" FIX 477: Saludo corto detectado '{parcial_actual}' - reduciendo espera a 0.3s")

                    # Solo tenemos PARCIAL - esperar un poco más por FINAL
                    if tiempo_espera_final_extra < max_espera_ajustada:
                        tiempo_espera_final_extra += wait_interval
                        time.sleep(wait_interval)
                        tiempo_esperado += wait_interval
                        print(f" FIX 451: Solo PARCIAL disponible, esperando FINAL... ({tiempo_espera_final_extra:.2f}s/{max_espera_ajustada}s)")
                        continue
                    else:
                        # Ya esperamos suficiente, usar PARCIAL con advertencia
                        print(f" FIX 451: Usando transcripción PARCIAL después de esperar {max_espera_final_extra}s por FINAL")

                        # FIX 465: BRUCE1398 - Detectar si la frase está INCOMPLETA
                        # Si termina con coma o palabras conectoras, el cliente sigue hablando
                        ultima_parcial_texto = ""
                        if transcripciones_dg:
                            ultima_parcial_texto = transcripciones_dg[-1].strip().lower()

                        # Patrones que indican frase incompleta
                        frase_incompleta = False
                        if ultima_parcial_texto:
                            # Termina con coma = definitivamente incompleta
                            if ultima_parcial_texto.endswith(','):
                                frase_incompleta = True
                                print(f"    FIX 465: Frase termina en COMA - cliente sigue hablando")
                            # Termina con palabra conectora
                            elif any(ultima_parcial_texto.endswith(f' {palabra}') for palabra in [
                                'y', 'pero', 'o', 'que', 'porque', 'este', 'bueno', 'pues', 'entonces', 'como'
                            ]):
                                frase_incompleta = True
                                print(f"    FIX 465: Frase termina en CONECTOR - cliente sigue hablando")

                        # FIX 465: Si frase incompleta, esperar 0.5s más antes de continuar
                        if frase_incompleta:
                            max_espera_frase_incompleta = 0.5
                            tiempo_espera_incompleta = 0.0
                            while tiempo_espera_incompleta < max_espera_frase_incompleta:
                                time.sleep(0.05)
                                tiempo_espera_incompleta += 0.05
                                tiempo_esperado += 0.05

                                # FIX 490: Proteger acceso concurrente con lock
                                with deepgram_transcripciones_lock:
                                    trans_actuales = deepgram_transcripciones.get(call_sid, [])
                                if trans_actuales and len(trans_actuales[-1]) > len(ultima_parcial_texto):
                                    print(f"    FIX 465: Nueva transcripción más larga recibida")
                                    # Volver a esperar por FINAL
                                    esperando_final = True
                                    tiempo_espera_final_extra = 0.5  # Ya esperamos algo
                                    break

                                if esperando_final:
                                    continue  # Volver al loop principal

                            # Si no se activó esperando_final, continuar usando parcial
                            esperando_final = False
                elif es_final:
                    print(f" FIX 451: Transcripción FINAL recibida")

                    # FIX 525: BRUCE1766 - Si es respuesta de PRESENCIA corta, procesar INMEDIATAMENTE
                    # "Dígame", "Sí", "Bueno", etc. son respuestas completas que no necesitan esperar
                    final_texto = transcripciones_dg[-1].strip().lower() if transcripciones_dg else ""
                    final_sin_puntuacion = final_texto.rstrip('.,;:!?¿¡')
                    respuestas_presencia = [
                        'dígame', 'digame', 'diga', 'mande', 'sí', 'si', 'bueno', 'alo', 'aló',
                        'sí dígame', 'si digame', 'sí diga', 'si diga', 'adelante',
                        'a sus órdenes', 'a sus ordenes', 'para servirle', 'en qué le ayudo',
                        'en que le ayudo', 'qué se le ofrece', 'que se le ofrece'
                    ]
                    es_respuesta_presencia = final_sin_puntuacion in respuestas_presencia

                    if es_respuesta_presencia:
                        print(f" FIX 525: Respuesta de PRESENCIA '{final_texto}' - procesando INMEDIATO sin espera")
                        # Saltar la espera de 350ms y procesar directamente
                        esperando_final = False
                        # No hacer continue, dejar que fluya al código de procesamiento

                    # FIX 528: BRUCE1775 - Si cliente dictó número de WhatsApp COMPLETO (10 dígitos), procesar INMEDIATO
                    # Problema: Cliente dictó "72, 27 0 7 27 84." (10 dígitos) pero Bruce no respondió
                    import re
                    digitos_en_final = re.findall(r'\d', final_texto)
                    es_numero_completo = len(digitos_en_final) >= 10
                    if es_numero_completo:
                        print(f" FIX 528: Número COMPLETO detectado ({len(digitos_en_final)} dígitos) - procesando INMEDIATO")
                        esperando_final = False

                    # FIX 456: BRUCE1375 - Esperar para ver si cliente sigue hablando
                    # El cliente puede pausar brevemente pero continuar hablando
                    # FIX 525/528: Solo esperar si NO es respuesta especial
                    procesar_inmediato = es_respuesta_presencia or es_numero_completo
                    tiempo_espera_post_final = 0.0
                    max_espera_post_final = 0.35 if not procesar_inmediato else 0.0  # FIX 525/528: 0 para casos especiales
                    timestamp_final = info_ultima.get("timestamp", time.time())

                    while tiempo_espera_post_final < max_espera_post_final:
                        time.sleep(0.05)  # Esperar 50ms
                        tiempo_espera_post_final += 0.05
                        tiempo_esperado += 0.05

                        # Verificar si llegó una PARCIAL nueva después del FINAL
                        info_parcial = deepgram_ultima_parcial.get(call_sid, {})
                        timestamp_parcial = info_parcial.get("timestamp", 0)

                        # Si hay PARCIAL más reciente que el FINAL, cliente sigue hablando
                        if timestamp_parcial > timestamp_final:
                            print(f" FIX 456: PARCIAL nueva detectada - cliente sigue hablando: '{info_parcial.get('texto', '')}'")
                            print(f"   Esperando más transcripciones...")
                            # Reset espera - esperar por nueva FINAL
                            esperando_final = True
                            tiempo_espera_final_extra = 0.0
                            break

                    # FIX 456: Si detectamos que sigue hablando, volver al while principal
                    if esperando_final and tiempo_espera_final_extra == 0.0:
                        continue  # Volver a esperar por nueva FINAL

                    if tiempo_espera_post_final >= max_espera_post_final:
                        print(f" FIX 456: No hay PARCIALES nuevas después de {max_espera_post_final}s - cliente terminó de hablar")

                    # FIX 239/242/248: Manejo inteligente de múltiples transcripciones
                    if len(transcripciones_dg) > 1:
                        print(f" FIX 239/242/248: {len(transcripciones_dg)} transcripciones acumuladas")
                        for i, t in enumerate(transcripciones_dg):
                            print(f"   [{i}] '{t}'")

                        # FIX 248: Primero eliminar duplicados exactos o casi exactos
                        # (diferencia solo en puntuación o espacios)
                        transcripciones_unicas = []
                        for t in transcripciones_dg:
                            # Normalizar: quitar puntuación y espacios extras
                            t_normalizada = t.lower().strip().rstrip('.,;:!?')

                            # Verificar si ya existe una transcripción muy similar (>90% igual)
                            es_duplicado = False
                            for existente in transcripciones_unicas:
                                existente_norm = existente.lower().strip().rstrip('.,;:!?')

                                # Si son exactamente iguales (normalizadas)
                                if t_normalizada == existente_norm:
                                    es_duplicado = True
                                    break

                                # Si una contiene completamente a la otra
                                if t_normalizada in existente_norm or existente_norm in t_normalizada:
                                    # Quedarse con la más larga
                                    if len(t) > len(existente):
                                        transcripciones_unicas.remove(existente)
                                        transcripciones_unicas.append(t)
                                    es_duplicado = True
                                    break

                            if not es_duplicado:
                                transcripciones_unicas.append(t)

                        print(f"    FIX 248: Después de eliminar duplicados: {len(transcripciones_unicas)} transcripciones únicas")

                        # FIX 242: Buscar la transcripción más completa
                        if len(transcripciones_unicas) == 1:
                            transcripcion_deepgram = transcripciones_unicas[0]
                            print(f"    FIX 248: Una sola transcripción única: '{transcripcion_deepgram}'")
                        else:
                            # Concatenar las partes únicas (ya sin duplicados)
                            transcripcion_deepgram = " ".join(transcripciones_unicas)
                            print(f"    FIX 248: Concatenando {len(transcripciones_unicas)} partes únicas: '{transcripcion_deepgram}'")
                    else:
                        transcripcion_deepgram = transcripciones_dg[0]

                    usar_deepgram = True
                    speech_original_twilio = speech_result
                    speech_result = transcripcion_deepgram

                    print(f"\n FIX 212: USANDO TRANSCRIPCIÓN DEEPGRAM (esperó {tiempo_esperado:.1f}s)")
                    print(f"   🟢 Deepgram: '{transcripcion_deepgram}'")
                    if speech_original_twilio:
                        print(f"    Twilio: '{speech_original_twilio}'")

                    # FIX 408: Resetear contador de timeouts cuando Deepgram responde exitosamente
                    if call_sid in conversaciones_activas:
                        agente_temp = conversaciones_activas[call_sid]
                        if hasattr(agente_temp, 'timeouts_deepgram') and agente_temp.timeouts_deepgram > 0:
                            print(f"    FIX 408: Reseteando contador de timeouts (era {agente_temp.timeouts_deepgram})")
                            agente_temp.timeouts_deepgram = 0

                    deepgram_transcripciones[call_sid] = []
                    # FIX 451: Limpiar también el tracking de FINAL/PARCIAL
                    if call_sid in deepgram_ultima_final:
                        deepgram_ultima_final[call_sid] = {}
                    break
            time.sleep(wait_interval)
            tiempo_esperado += wait_interval

        # FIX 469: BRUCE1416 - Si el timeout se agotó pero HAY transcripciones, usarlas
        # El loop puede terminar por timeout mientras espera más transcripciones,
        # pero ya acumuló transcripciones FINAL válidas que no debemos perder
        if not usar_deepgram:
            transcripciones_acumuladas = deepgram_transcripciones.get(call_sid, [])
            if transcripciones_acumuladas:
                print(f"\n FIX 469: Timeout pero hay {len(transcripciones_acumuladas)} transcripciones acumuladas")
                for i, t in enumerate(transcripciones_acumuladas):
                    print(f"   [{i}] '{t}'")

                # Usar las transcripciones acumuladas
                if len(transcripciones_acumuladas) > 1:
                    # Eliminar duplicados y concatenar
                    transcripciones_unicas = []
                    for t in transcripciones_acumuladas:
                        t_normalizada = t.lower().strip().rstrip('.,;:!?')
                        es_duplicado = False
                        for existente in transcripciones_unicas:
                            existente_norm = existente.lower().strip().rstrip('.,;:!?')
                            if t_normalizada == existente_norm:
                                es_duplicado = True
                                break
                            if t_normalizada in existente_norm or existente_norm in t_normalizada:
                                if len(t) > len(existente):
                                    transcripciones_unicas.remove(existente)
                                    transcripciones_unicas.append(t)
                                es_duplicado = True
                                break
                        if not es_duplicado:
                            transcripciones_unicas.append(t)

                    transcripcion_deepgram = " ".join(transcripciones_unicas)
                    print(f"    FIX 469: Concatenando {len(transcripciones_unicas)} partes: '{transcripcion_deepgram}'")
                else:
                    transcripcion_deepgram = transcripciones_acumuladas[0]
                    print(f"    FIX 469: Usando transcripción única: '{transcripcion_deepgram}'")

                usar_deepgram = True
                speech_original_twilio = speech_result
                speech_result = transcripcion_deepgram

                # Limpiar para próximo ciclo
                deepgram_transcripciones[call_sid] = []
                if call_sid in deepgram_ultima_final:
                    deepgram_ultima_final[call_sid] = {}
            else:
                print(f" FIX 401: Deepgram no respondió en {max_wait_deepgram}s")
                print(f"    Whisper DESHABILITADO - esperando siguiente intento con Deepgram")

                # FIX 534: Incrementar contador de timeouts para ajuste progresivo
                if call_sid in conversaciones_activas:
                    agente_timeout = conversaciones_activas[call_sid]
                    if hasattr(agente_timeout, 'timeouts_deepgram'):
                        agente_timeout.timeouts_deepgram += 1
                        print(f"    FIX 534: Timeout Deepgram #{agente_timeout.timeouts_deepgram}")

    # FIX 401: WHISPER DESHABILITADO - Deepgram es el único sistema de transcripción
    # Whisper genera demasiadas transcripciones basura ("subtítulos de amara.org")
    if False and not usar_deepgram and recording_url and OPENAI_API_KEY:
        print(f"\n FIX 60: RecordingUrl disponible - usando WHISPER API")

        # FIX 198: Detectar contexto para mejorar transcripción de Whisper
        whisper_prompt = None
        post_procesar_email = False

        # Obtener el agente actual para revisar el contexto
        agente = conversaciones_activas.get(call_sid)
        if agente and agente.conversation_history:
            # Buscar el último mensaje de Bruce
            ultimo_msg_bruce = ""
            for msg in reversed(agente.conversation_history):
                if msg['role'] == 'assistant':
                    ultimo_msg_bruce = msg['content'].lower()
                    break

            # Detectar si estábamos pidiendo email
            estaba_pidiendo_email = any(kw in ultimo_msg_bruce for kw in ["correo", "email", "electrónico", "correo electrónico"])

            # Detectar si estábamos pidiendo WhatsApp
            estaba_pidiendo_whatsapp = any(kw in ultimo_msg_bruce for kw in ["whatsapp", "número", "telefono", "teléfono"])

            if estaba_pidiendo_email:
                # FIX 198: Prompt específico para emails
                whisper_prompt = "El cliente está deletreando su correo electrónico. Palabras clave: arroba, @, punto, com, gmail, hotmail, yahoo, guión bajo, guión medio."
                post_procesar_email = True
                print(f" FIX 198: Contexto EMAIL detectado - mejorando transcripción")

            elif estaba_pidiendo_whatsapp:
                # Prompt para números telefónicos
                whisper_prompt = "El cliente está dictando su número de WhatsApp o teléfono en español. Números del 0 al 9."
                print(f" FIX 198: Contexto WHATSAPP detectado - mejorando transcripción")

        transcripcion_whisper = transcribir_con_whisper(
            recording_url,
            whisper_prompt=whisper_prompt,
            post_procesar_email=post_procesar_email
        )

        if transcripcion_whisper:
            # FIX 233: Filtrar transcripciones basura de Whisper
            # Cuando hay silencio o ruido, Whisper inventa texto como subtítulos de películas
            transcripciones_basura = [
                "subtítulos realizados por la comunidad de amara.org",
                "subtítulos por la comunidad de amara.org",
                "subtitulos realizados por la comunidad",
                "gracias por ver el video",
                "suscríbete al canal",
                "like y suscríbete",
                "muchas gracias por ver",
                "nos vemos en el siguiente video",
                "hasta la próxima",
                "transcripción realizada por",
                "audio no disponible",
                "silencio",
                "...",
                "[música]",
                "[aplausos]",
                "[risas]",
            ]

            transcripcion_lower = transcripcion_whisper.lower().strip()
            es_basura = any(basura in transcripcion_lower for basura in transcripciones_basura)

            # También detectar si es muy corto y sin sentido
            if len(transcripcion_whisper.strip()) < 3:
                es_basura = True

            if es_basura:
                print(f"\n FIX 233: Transcripción BASURA detectada de Whisper: '{transcripcion_whisper}'")
                print(f"   Ignorando y esperando entrada válida del cliente...")
                # NO usar esta transcripción - retornar TwiML para seguir escuchando
                transcripcion_whisper = None
            else:
                usar_whisper = True
                speech_original_twilio = speech_result  # Guardar transcripción de Twilio para comparación
                speech_result = transcripcion_whisper  # Usar Whisper como principal

                # Log de comparación (útil para validar mejora)
                if speech_original_twilio:
                    print(f"\n FIX 60: COMPARACIÓN DE TRANSCRIPCIONES:")
                    print(f"    Twilio: '{speech_original_twilio}'")
                    print(f"   🟢 Whisper: '{transcripcion_whisper}'")
                    if speech_original_twilio.lower() != transcripcion_whisper.lower():
                        print(f"     DIFERENCIAS DETECTADAS - Whisper será más preciso")
                else:
                    print(f"   ℹ  Solo Whisper disponible (Twilio no transcribió)")
        else:
            print(f"     Whisper falló - fallback a transcripción de Twilio")
    elif not OPENAI_API_KEY:
        print(f"   ℹ  OPENAI_API_KEY no configurada - usando Twilio Speech Recognition")

    # FIX 28/94: Corrección de transcripciones comunes de Whisper/Twilio
    # Whisper confunde palabras que suenan similar pero tienen significados diferentes
    if speech_result:
        speech_original = speech_result  # Guardar original para debug

        # Mapa de correcciones: palabra_incorrecta → palabra_correcta
        # Solo aplicar en contexto de ferretería/hardware y llamadas comerciales
        TRANSCRIPTION_CORRECTIONS = {
            'chiapas': 'chapas',       # Estado mexicano → cerraduras/herrajes
            'Chiapas': 'chapas',
            'CHIAPAS': 'chapas',
            'trupper': 'truper',       # Marca incorrecta → marca correcta
            'Trupper': 'Truper',
            'TRUPPER': 'TRUPER',
            'tuvo': 'tubo',            # Verbo → tubo PVC
            'candado': 'candados',     # Singular → plural (más común en ventas)
            'cerradura': 'cerraduras',
            'bisagra': 'bisagras',
            'tornillo': 'tornillos',
            'clavo': 'clavos',
            # FIX 94: Correcciones de frases comunes mal transcritas
            'fuiste': 'gusta',         # "fuiste a dejar" → "gusta dejar"
            'Fuiste': 'Gusta',
        }

        # Aplicar correcciones palabra por palabra
        palabras = speech_result.split()
        palabras_corregidas = []

        for palabra in palabras:
            # Buscar si esta palabra necesita corrección
            palabra_corregida = TRANSCRIPTION_CORRECTIONS.get(palabra, palabra)
            palabras_corregidas.append(palabra_corregida)

        speech_result = ' '.join(palabras_corregidas)

        # FIX 30: Detectar instrucciones de ortografía ("con z", "con s", etc.)
        # Cliente dice: "YahirSam con z" → Debe entenderse como "YahirZam"
        import re

        # Patrón: [palabra] con [letra]
        patron_ortografia = r'(\w+)\s+con\s+([a-zA-Z])\b'
        matches_ortografia = list(re.finditer(patron_ortografia, speech_result, re.IGNORECASE))

        if matches_ortografia:
            for match in reversed(matches_ortografia):  # Iterar al revés para no afectar índices
                palabra_original = match.group(1)
                letra_correcta = match.group(2).lower()

                # Buscar la última consonante diferente a letra_correcta y reemplazarla
                # Ejemplo: "Sam con z" → buscar 'm' (última letra), no es 'z', entonces reemplazar
                palabra_corregida = palabra_original
                for i in range(len(palabra_original) - 1, -1, -1):
                    letra_actual = palabra_original[i].lower()
                    if letra_actual != letra_correcta and letra_actual.isalpha():
                        # Reemplazar esta letra por la letra correcta (mantener mayúscula si era mayúscula)
                        if palabra_original[i].isupper():
                            letra_reemplazo = letra_correcta.upper()
                        else:
                            letra_reemplazo = letra_correcta

                        palabra_corregida = palabra_original[:i] + letra_reemplazo + palabra_original[i+1:]
                        break

                # Reemplazar en el texto completo (eliminar " con [letra]")
                speech_result = speech_result[:match.start()] + palabra_corregida + speech_result[match.end():]

                print(f" FIX 30 - Corrección ortográfica:")
                print(f"   '{palabra_original} con {letra_correcta}' → '{palabra_corregida}'")

        # Log si hubo correcciones
        if speech_result != speech_original:
            print(f" FIX 28/30 - Transcripción corregida:")
            print(f"   Original: '{speech_original}'")
            print(f"   Corregida: '{speech_result}'")

    # Verificar si Twilio detectó buzón de voz (AnsweredBy=machine_start)
    if answered_by in ["machine_start", "machine_end_beep", "machine_end_silence", "machine_end_other"]:
        print(f" Buzón de voz detectado automáticamente por Twilio: {answered_by}")
        print(f" Marcando como BUZON")

        # Obtener agente si existe
        agente = conversaciones_activas.get(call_sid)
        if agente:
            # Marcar como "Buzon"
            agente.lead_data["estado_llamada"] = "Buzon"
            agente.lead_data["pregunta_0"] = "Buzon"
            agente.lead_data["pregunta_7"] = "BUZON"
            agente.lead_data["resultado"] = "NEGADO"
            print(f" Estado actualizado: Buzón detectado automáticamente")

            # Guardar la llamada
            agente.guardar_llamada_y_lead()

        # Terminar con respuesta TwiML
        response = VoiceResponse()
        response.say("Disculpe, parece que entró el buzón de voz. Le llamaré en otro momento. Que tenga buen día.", language="es-MX")
        response.hangup()
        return Response(str(response), mimetype="text/xml")

    # FIX 105: Detectar buzón por contenido del SpeechResult (cuando Twilio no lo detecta por AMD)
    # Keywords comunes en mensajes de buzón de voz en México
    # FIX 512: BRUCE1488/BRUCE1490 - Agregar "no está disponible" y "graba tu mensaje"
    keywords_buzon = [
        "buzón de voz", "buzon de voz", "deje su mensaje", "deja tu mensaje",
        "dejar un mensaje", "dejar mensaje", "después del tono", "despues del tono",
        "no puede atender", "no disponible en este momento", "mailbox is full",
        "buzón está lleno", "buzon esta lleno", "no se puede dejar", "intente más tarde",
        # FIX 512: Nuevos patrones de buzón detectados en auditoría
        "no está disponible", "no esta disponible", "graba tu mensaje", "graba un mensaje",
        "la persona con la que intentas comunicarte", "persona que intentas comunicarte"
    ]

    speech_lower = speech_result.lower() if speech_result else ""
    es_buzon_por_contenido = any(keyword in speech_lower for keyword in keywords_buzon)

    # FIX 463: BRUCE1388 - NO detectar buzón si cliente OFRECE WhatsApp/contacto
    # Caso: "si gusta dejar un mensaje a WhatsApp y le compartimos los números"
    # Esto NO es buzón - es una persona ofreciendo medio de contacto
    if es_buzon_por_contenido:
        cliente_ofrece_contacto = any(palabra in speech_lower for palabra in [
            'whatsapp', 'le compartimos', 'le comparto', 'le paso',
            'este número', 'este numero', 'a este mismo', 'mi número', 'mi numero'
        ])
        if cliente_ofrece_contacto:
            print(f" FIX 463: NO es buzón - cliente OFRECE contacto (WhatsApp/número)")
            print(f"   Mensaje: '{speech_result[:80]}...'")
            es_buzon_por_contenido = False

    if es_buzon_por_contenido:
        print(f" FIX 105: Buzón detectado por contenido del SpeechResult")
        print(f"   Mensaje: '{speech_result[:100]}...'")
        print(f" Marcando como BUZON")

        # Obtener agente si existe
        agente = conversaciones_activas.get(call_sid)
        if agente:
            # Marcar como "Buzon"
            agente.lead_data["estado_llamada"] = "Buzon"
            agente.lead_data["pregunta_0"] = "Buzon"
            agente.lead_data["pregunta_7"] = "BUZON"
            agente.lead_data["resultado"] = "NEGADO"
            print(f" Estado actualizado: Buzón detectado por análisis de contenido")

            # Guardar la llamada
            agente.guardar_llamada_y_lead()

        # Terminar con respuesta TwiML
        response = VoiceResponse()
        response.say("Disculpe, parece que entró el buzón de voz. Le llamaré en otro momento. Que tenga buen día.", language="es-MX")
        response.hangup()
        return Response(str(response), mimetype="text/xml")

    # FIX 109/209: Detectar operadora/contestadora automática por contenido
    # FIX 209: Mejorar detección de IVR con más patrones
    keywords_operadora = [
        "número que usted marcó", "numero que usted marco",
        "el número marcado", "el numero marcado",
        "comuníquese más tarde", "comuniquese mas tarde",
        "no se encuentra disponible en este momento",
        "marque la extensión", "marque la extension",
        "oprima", "presione", "pulse",  # IVR típico
        "para español", "para inglés",  # Menú de idiomas
        "si desea hablar", "si conoce la extensión",
        "todas nuestras líneas están ocupadas", "todas nuestras lineas",
        "su llamada es importante", "por favor espere",
        "gracias por llamar", "bienvenido a",
        # FIX 209: Nuevos patrones de IVR detectados en llamadas reales
        "marca 1", "marca 2", "marca 3", "marca 4", "marca 5",
        "marca uno", "marca dos", "marca tres",
        "marque 1", "marque 2", "marque 3",
        "marque uno", "marque dos", "marque tres",
        "signo de número", "signo de numero",
        "para escuchar el mensaje",
        "para continuar con la grabación", "para continuar con la grabacion",
        "para eliminar este mensaje",
        "para enviar el mensaje",
        "para volver a grabar",
        "espera instrucciones",
        "correo de voz",
        "atención al cliente", "atencion al cliente",
        "línea de atención", "linea de atencion"
    ]

    speech_lower = speech_result.lower() if speech_result else ""
    es_operadora = any(keyword in speech_lower for keyword in keywords_operadora)

    if es_operadora:
        print(f" FIX 109: Operadora/IVR detectada por contenido del SpeechResult")
        print(f"   Mensaje: '{speech_result[:100]}...'")
        print(f" Marcando como OPERADORA")

        # Obtener agente si existe
        agente = conversaciones_activas.get(call_sid)
        if agente:
            # Marcar como "Operadora" (similar a Buzón)
            agente.lead_data["estado_llamada"] = "Operadora"
            agente.lead_data["pregunta_0"] = "Operadora"
            agente.lead_data["pregunta_7"] = "OPERADORA"
            agente.lead_data["resultado"] = "NEGADO"
            print(f" Estado actualizado: Operadora/IVR detectada")

            # Guardar la llamada
            agente.guardar_llamada_y_lead()

        # Terminar con respuesta TwiML
        response = VoiceResponse()
        response.say("Disculpe, parece que entró la operadora automática. Le llamaré en otro momento. Que tenga buen día.", language="es-MX")
        response.hangup()
        return Response(str(response), mimetype="text/xml")

    # FIX 195: SOLO procesar si llamada está ACTIVA
    # "completed" significa que llamada YA terminó (no que cliente está colgando ahora)
    # Twilio puede enviar múltiples requests: primero "in-progress" luego "completed"
    estados_llamada_terminada = ["completed", "busy", "no-answer", "canceled", "failed"]

    if call_status in estados_llamada_terminada:
        print(f" Llamada YA terminada - Estado: {call_status}")

        # FIX 195: Verificar si hay SpeechResult para procesar
        if speech_result and speech_result.strip():
            print(f" FIX 195: Llamada terminada pero hay transcripción: '{speech_result}'")
            print(f"   Esto indica request duplicado de Twilio - transcripción ya procesada")
            # NO procesar de nuevo - ya se procesó en request "in-progress"
        else:
            print(f" Cliente colgó o llamada desconectada")

        # Obtener agente si existe
        agente = conversaciones_activas.get(call_sid)
        if agente:
            # FIX 176: NO sobrescribir si ya se capturó información valiosa
            # Verificar si se capturó WhatsApp, email o referencia ANTES de marcar como "Colgo"
            tiene_dato_capturado = (
                agente.lead_data.get("whatsapp") or
                agente.lead_data.get("email") or
                agente.lead_data.get("referencia_telefono")
            )

            # Solo marcar como "Colgo" si NO hay datos capturados
            if agente.lead_data["estado_llamada"] == "Respondio" and not tiene_dato_capturado:
                agente.lead_data["estado_llamada"] = "Colgo"
                agente.lead_data["pregunta_0"] = "Colgo"
                agente.lead_data["pregunta_7"] = "Colgo"
                agente.lead_data["resultado"] = "NEGADO"
                print(f" Estado actualizado: Cliente colgó (sin datos capturados)")
            elif tiene_dato_capturado:
                # FIX 176: Si hay datos capturados, determinar conclusión correcta
                print(f" FIX 176: Cliente colgó pero SÍ capturamos datos:")
                print(f"   WhatsApp: {bool(agente.lead_data.get('whatsapp'))}")
                print(f"   Email: {bool(agente.lead_data.get('email'))}")
                print(f"   Referencia: {bool(agente.lead_data.get('referencia_telefono'))}")
                # FIX 177: Forzar recálculo para sobrescribir "Colgo" temporal
                agente._determinar_conclusion(forzar_recalculo=True)
                print(f"   Conclusión final: {agente.lead_data.get('pregunta_7')} ({agente.lead_data.get('resultado')})")

            # Guardar la llamada
            agente.guardar_llamada_y_lead()

        # Terminar con respuesta TwiML
        response = VoiceResponse()
        response.hangup()
        return Response(str(response), mimetype="text/xml")

    # FIX 195: Verificar que CallStatus sea válido para procesar
    # Solo procesar si la llamada está ACTIVA (in-progress, ringing, answered)
    estados_validos = ["in-progress", "ringing", "answered", ""]  # "" = sin status (primera llamada)

    if call_status and call_status not in estados_validos:
        print(f" FIX 195: CallStatus inválido para procesar: '{call_status}' - ignorando")
        response = VoiceResponse()
        response.hangup()
        return Response(str(response), mimetype="text/xml")

    print(f" FIX 195: CallStatus válido ('{call_status}' o vacío) - procesando transcripción")

    # Obtener agente de esta conversación
    agente = conversaciones_activas.get(call_sid)

    if not agente:
        response = VoiceResponse()
        response.say("Error en la conversación.", language="es-MX")
        response.hangup()
        return Response(str(response), mimetype="text/xml")

    # LOG: Mostrar lo que dijo el cliente
    print(f"\n CLIENTE DIJO: \"{speech_result}\"")
    # FIX 208/284: Registrar en buffer de logs (sin duplicar prefijo BRUCE)
    bruce_id_cliente = agente.lead_data.get("bruce_id", "N/A") if agente else "N/A"
    log_evento(f"{bruce_id_cliente} - CLIENTE DIJO: \"{speech_result}\"", "CLIENTE")

    # ============================================================================
    # FIX 507 BRUCE1721: Detectar TRANSCRIPCIONES CORRUPTAS de Deepgram
    # Problema: Deepgram a veces devuelve transcripciones sin sentido
    # Ejemplo: "¿Un váter o nada más? Pero hazme ya para torta." (BRUCE1721)
    # Solución: Detectar palabras/frases que NO tienen sentido en contexto ferretero
    # ============================================================================
    if speech_result and speech_result.strip():
        speech_lower_507 = speech_result.lower().strip()

        # Palabras que NUNCA deberían aparecer en una llamada de ventas de ferretería
        # y que indican transcripción corrupta de Deepgram
        palabras_corruptas = [
            'váter', 'vater', 'torta', 'hazme ya', 'para torta',
            'pizza', 'hamburguesa', 'taco', 'burrito', 'sushi',
            'fútbol', 'futbol', 'partido', 'gol',
            'canción', 'cancion', 'bailar', 'música', 'musica',
            'película', 'pelicula', 'serie', 'netflix',
            'amor', 'te amo', 'te quiero', 'beso', 'abrazo',
            'sexo', 'porno', 'xxx',
            'matar', 'morir', 'sangre', 'violencia',
            'droga', 'marihuana', 'cocaína', 'cocaina'
        ]

        # Patrones de frases sin sentido (combinaciones que no tienen contexto)
        frases_sin_sentido = [
            'hazme ya para', 'nada más pero', 'o nada más pero',
            'váter o nada', 'vater o nada'
        ]

        tiene_palabra_corrupta = any(p in speech_lower_507 for p in palabras_corruptas)
        tiene_frase_sin_sentido = any(f in speech_lower_507 for f in frases_sin_sentido)

        if tiene_palabra_corrupta or tiene_frase_sin_sentido:
            print(f"\n[WARN] FIX 507: TRANSCRIPCIÓN CORRUPTA DETECTADA")
            print(f"   Transcripción: '{speech_result}'")
            print(f"   → Pidiendo repetición al cliente")

            # Incrementar contador de transcripciones corruptas
            if not hasattr(agente, 'transcripciones_corruptas'):
                agente.transcripciones_corruptas = 0
            agente.transcripciones_corruptas += 1

            # Si ya van 2+ corruptas seguidas, puede ser problema de audio real
            if agente.transcripciones_corruptas >= 2:
                print(f"   [WARN] {agente.transcripciones_corruptas} transcripciones corruptas seguidas")
                print(f"   → Posible problema de audio/conexión")

            # Pedir repetición
            response = VoiceResponse()
            mensajes_repetir = [
                "Disculpe, no le escuché bien. ¿Me puede repetir?",
                "Perdón, tuve problemas de audio. ¿Qué me decía?",
                "Lo siento, no logré entenderle. ¿Me lo repite por favor?"
            ]
            import random
            mensaje = random.choice(mensajes_repetir)

            audio_id = f"repetir_corrupta_{call_sid}"
            result = generar_audio_elevenlabs(mensaje, audio_id)

            if result:
                audio_url = request.url_root + f"audio/{audio_id}"
                response.play(audio_url)
            else:
                response.say(mensaje, voice="alice", language="es-MX")

            response.record(
                action="/procesar-respuesta",
                method="POST",
                max_length=30,
                timeout=5,
                play_beep=False,
                trim="trim-silence"
            )
            return Response(str(response), mimetype="text/xml")
        else:
            # Transcripción válida - resetear contador
            if hasattr(agente, 'transcripciones_corruptas'):
                agente.transcripciones_corruptas = 0

    # Registrar mensaje del cliente en LOGS
    if logs_manager and speech_result and agente.bruce_id:
        nombre_tienda = agente.lead_data.get('nombre_negocio', '')
        logs_manager.registrar_mensaje_cliente(agente.bruce_id, speech_result, nombre_tienda)

    # ============================================================================
    # FIX 244: Detectar si cliente está hablando pausadamente (frase incompleta)
    # ============================================================================
    if speech_result and speech_result.strip():
        import time

        # ============================================================================
        # FIX 265: Detectar deletreo de email ANTES de verificar historial de habla
        # Esto permite detectar "Es ventas 1 arroba provechisa punto com" incluso
        # si es la primera vez que el cliente habla (sin historial previo)
        # ============================================================================
        frase_lower = speech_result.lower()
        palabras_deletreo_email = ["arroba", "punto", "guion", "guión", "bajo", "@", "gmail", "hotmail", "yahoo", "outlook", ".com", ".mx", ".net"]
        esta_deletreando_email = any(palabra in frase_lower for palabra in palabras_deletreo_email)
        email_detectado_completo = False  # FIX 499: Bandera para email completo

        # FIX 265: Si está deletreando email, verificar si parece completo o incompleto
        if esta_deletreando_email:
            # Un email completo tiene: algo@algo.algo (arroba + punto + dominio)
            tiene_arroba = "arroba" in frase_lower or "@" in frase_lower
            tiene_punto = "punto" in frase_lower or "." in frase_lower
            tiene_dominio = any(dom in frase_lower for dom in ["com", "mx", "net", "org", "edu", "gmail", "hotmail", "yahoo", "outlook"])

            email_parece_completo = tiene_arroba and tiene_punto and tiene_dominio

            if not email_parece_completo:
                # Email incompleto - esperar más
                print(f"\n FIX 265: CLIENTE DELETREANDO EMAIL (incompleto)")
                print(f"   Transcripción parcial: '{speech_result}'")
                print(f"   tiene_arroba: {tiene_arroba}, tiene_punto: {tiene_punto}, tiene_dominio: {tiene_dominio}")

                # Almacenar transcripción parcial
                if not hasattr(agente, 'transcripcion_parcial_acumulada'):
                    agente.transcripcion_parcial_acumulada = []
                agente.transcripcion_parcial_acumulada.append(speech_result)

                # Generar TwiML para seguir escuchando con timeout largo
                response = VoiceResponse()
                response.record(
                    action="/procesar-respuesta",
                    method="POST",
                    max_length=1,
                    timeout=5,  # 5s de timeout para deletreo de email
                    play_beep=False,
                    trim="trim-silence"
                )

                print(f"    FIX 265: Esperando que termine el email con timeout de 5s...")
                return Response(str(response), mimetype="text/xml")
            else:
                print(f"    FIX 265: Email parece completo - procesar normalmente")
                # FIX 499: Marcar que el email está completo para NO esperar más
                email_detectado_completo = True

        # Verificar si el cliente tiene historial de habla activa
        if call_sid in cliente_hablando_activo:
            info_habla = cliente_hablando_activo[call_sid]
            tiempo_hablando = time.time() - info_habla["inicio"]
            palabras_nuevas = len(speech_result.split())

            # Detectar si la frase parece incompleta
            # Indicios: termina abruptamente, no tiene verbo final, es muy corta después de hablar
            frase_parece_incompleta = False

            # FIX 260: Pre-detectar si es una pregunta para evitar falsos positivos
            frase_limpia = speech_result.strip().lower()

            # FIX 520: BRUCE1739/BRUCE1743 - Detectar cuando cliente VUELVE después de "Claro, espero"
            # Problema: Bruce entró en modo ESPERANDO_TRANSFERENCIA pero cuando cliente volvió
            # diciendo "¿Bueno?", "¿Vuelvo?", "están hablando de una ferretería?", Bruce NO respondió
            # Solución: Si estamos en ESPERANDO_TRANSFERENCIA y cliente dice algo (no petición de espera),
            # SALIR del modo espera y procesar normalmente
            from agente_ventas import EstadoConversacion
            if agente.estado_conversacion == EstadoConversacion.ESPERANDO_TRANSFERENCIA:
                # Detectar si cliente "volvió" (está hablando con Bruce, no pidiendo más espera)
                frases_cliente_volvio = [
                    '¿bueno?', 'bueno', '¿vuelvo?', 'vuelvo',
                    '¿hola?', 'hola', '¿sí?', 'si', '¿diga?', 'diga',
                    'aquí estoy', 'ahi estoy', 'ya estoy', 'listo',
                    '¿qué', '¿que', 'qué marca', 'que marca', 'qué vende', 'que vende',
                    '¿quién habla', '¿quien habla', 'quién es', 'quien es',
                    '¿de dónde', '¿de donde', 'de parte de',
                    'están hablando', 'estan hablando', 'habla de', 'hablan de',
                    'ferretería', 'ferreteria', 'empresa', 'negocio',
                    'no está', 'no esta', 'no se encuentra', 'salió', 'salio',
                    'no tenemos', 'no manejamos', 'no nos interesa'
                ]

                # Si NO es petición de más espera → cliente volvió
                frases_mas_espera = ['un momento', 'momentito', 'espere', 'tantito', 'un segundo']
                es_mas_espera = any(f in frase_limpia for f in frases_mas_espera)
                cliente_volvio = any(f in frase_limpia for f in frases_cliente_volvio) or not es_mas_espera

                if cliente_volvio and len(frase_limpia) > 2:  # Al menos 3 caracteres
                    print(f"\n FIX 520: CLIENTE VOLVIÓ después de espera - '{speech_result}'")
                    print(f"   Estado anterior: ESPERANDO_TRANSFERENCIA")
                    print(f"   → Saliendo del modo espera, procesando normalmente")
                    agente.estado_conversacion = EstadoConversacion.CONVERSACION_NORMAL
                    agente.respuestas_vacias_consecutivas = 0
                    # Resetear silencios
                    if hasattr(agente, 'silencios_durante_dictado'):
                        agente.silencios_durante_dictado = 0

            # FIX 470: BRUCE1412 - Detectar frases de ESPERA ANTES de cualquier otra lógica
            # Si el cliente dice "Permítame un segundo", "Un momento", etc., debemos
            # establecer estado ESPERANDO_TRANSFERENCIA y NO tratarlo como frase incompleta
            frases_espera_cliente = [
                'permítame', 'permitame', 'permíteme', 'permiteme',
                'un momento', 'un momentito', 'un segundo', 'un segundito',
                'dame un momento', 'deme un momento', 'dame un segundo', 'deme un segundo',
                'espere', 'espéreme', 'espereme', 'espera', 'espérame', 'esperame',
                'déjeme', 'dejeme', 'déjame', 'dejame',
                'aguarde', 'aguárdeme', 'aguardeme', 'aguarda', 'aguárdame',
                'tantito', 'un tantito', 'ahí le', 'ahorita le', 'ahorita te',
                'voy a ver', 'déjeme ver', 'dejeme ver', 'déjame ver', 'dejame ver',
                'ahorita se lo paso', 'se lo paso', 'le paso', 'te paso', 'ahorita lo paso',
                'en un momento', 'un minuto', 'un minutito'
            ]
            cliente_pidio_espera = any(frase in frase_limpia for frase in frases_espera_cliente)

            # FIX 511: BRUCE1725 - Detectar PREGUNTAS en la misma frase ANTES de activar modo espera
            # Problema: Cliente dijo "Sí, un momentito. ¿Qué marca, me dijo?"
            # FIX 470 detectó "momentito" pero ignoró la pregunta "¿Qué marca?"
            # Solución: Si hay una PREGUNTA, NO activar modo espera - dejar que agente responda
            contiene_pregunta = False
            if cliente_pidio_espera:
                preguntas_prioritarias = [
                    '¿qué marca', '¿que marca', 'qué marca', 'que marca',
                    '¿de qué', '¿de que', 'de qué empresa', 'de que empresa',
                    '¿quién habla', '¿quien habla', 'quién habla', 'quien habla',
                    '¿de dónde', '¿de donde', 'de dónde habla', 'de donde habla',
                    '¿qué vende', '¿que vende', 'qué venden', 'que venden',
                    '¿de parte de', 'de parte de quién', 'de parte de quien',
                    '¿para qué', '¿para que', 'para qué es', 'para que es',
                    'me dijo', 'me dijiste', 'me decía', 'me decia'  # "¿Qué marca me dijo?"
                ]
                contiene_pregunta = any(preg in frase_limpia for preg in preguntas_prioritarias)

                if contiene_pregunta:
                    print(f"\n FIX 511: PREGUNTA detectada en frase con 'espera' - NO activar modo espera")
                    print(f"   Frase: '{speech_result}'")
                    print(f"   → Cliente hizo PREGUNTA, dejar que agente responda")
                    cliente_pidio_espera = False  # Desactivar modo espera

            # FIX 518: BRUCE1736 - Detectar "MARQUE A OTRO NÚMERO" vs transferencia
            # Problema: Cliente dijo "marcó este número, pero con terminación 00, ahí le comunican"
            # FIX 470 detectó "le comunican" como transferencia, pero cliente decía LLAME A OTRO NÚMERO
            # Solución: Si menciona "otro número", "terminación", "extensión" → NO es transferencia
            if cliente_pidio_espera:
                indicadores_otro_numero = [
                    'otro número', 'otro numero', 'a otro', 'al otro',
                    'con terminación', 'con terminacion', 'terminación 0', 'terminacion 0',
                    'extensión', 'extension', 'marque a', 'marcar a', 'marca a',
                    'ahí le comunican', 'ahi le comunican', 'ahí le contestan', 'ahi le contestan',
                    'en ese número', 'en ese numero', 'a ese número', 'a ese numero',
                    'ese es el número', 'ese es el numero', 'el número es', 'el numero es',
                    'pero con', 'pero al'  # "pero con terminación 00"
                ]
                indica_otro_numero = any(ind in frase_limpia for ind in indicadores_otro_numero)

                if indica_otro_numero:
                    print(f"\n FIX 518: BRUCE1736 - Cliente indica OTRO NÚMERO, no transferencia")
                    print(f"   Frase: '{speech_result}'")
                    print(f"   → NO activar modo espera, procesar como información de contacto")
                    cliente_pidio_espera = False

            # FIX 508: BRUCE1723 - Evitar LOOP de "Claro, espero"
            # Problema: Bruce dijo "Claro, espero" 3 veces seguidas en 16 segundos
            # Solución: Si ya dijo "Claro, espero" en los últimos 30 segundos, NO repetir
            if cliente_pidio_espera:
                import time
                if not hasattr(agente, 'ultimo_claro_espero_timestamp'):
                    agente.ultimo_claro_espero_timestamp = 0

                tiempo_actual = time.time()
                tiempo_desde_ultimo = tiempo_actual - agente.ultimo_claro_espero_timestamp

                if tiempo_desde_ultimo < 30:  # Menos de 30 segundos desde el último
                    print(f"\n FIX 508: ANTI-LOOP - Ya dijo 'Claro, espero' hace {tiempo_desde_ultimo:.1f}s")
                    print(f"   → NO repetir, dejar que agente procese la frase")
                    cliente_pidio_espera = False  # Desactivar modo espera
                else:
                    # Actualizar timestamp si vamos a decir "Claro, espero"
                    agente.ultimo_claro_espero_timestamp = tiempo_actual

            # FIX 512: BRUCE1724 - NO activar modo espera si cliente está dictando NÚMEROS
            # Problema: Cliente dijo "Es de la sucursal. Es 99, 99, 44, 60 32" y Bruce dijo "Claro, espero"
            # Solución: Si la frase contiene 4+ dígitos, cliente está dictando número, NO esperar
            if cliente_pidio_espera:
                import re
                digitos_en_frase = re.findall(r'\d', frase_limpia)
                if len(digitos_en_frase) >= 4:
                    print(f"\n FIX 512: BRUCE1724 - Cliente dictando NÚMERO ({len(digitos_en_frase)} dígitos)")
                    print(f"   Frase: '{speech_result}'")
                    print(f"   → NO activar modo espera, dejar que agente capture el número")
                    cliente_pidio_espera = False

            # FIX 501: BRUCE1721 - Validar contexto NEGATIVO antes de activar modo espera
            # Problema: Cliente dijo "permítame un momentito, pero no. No lo tenemos permitido."
            # El FIX 470 detectó "permítame" pero ignoró la negación posterior
            # Solución: Verificar que NO haya negaciones/rechazos en la misma frase
            contexto_negativo = False
            if cliente_pidio_espera:
                frases_negativas = [
                    'pero no', 'no puedo', 'no tenemos permitido', 'no lo tenemos',
                    'no está permitido', 'no me permiten', 'no nos permiten',
                    'no es posible', 'no se puede', 'imposible',
                    'sucursal', 'oficinas', 'área equivocada', 'departamento equivocado',
                    'no es mi área', 'no manejo eso', 'no me corresponde',
                    'no soy el encargado', 'no soy la encargada', 'no soy quien',
                    'no tengo autorización', 'no estoy autorizado', 'no estoy autorizada'
                ]
                contexto_negativo = any(neg in frase_limpia for neg in frases_negativas)

                if contexto_negativo:
                    print(f"\n FIX 501: CONTEXTO NEGATIVO detectado - NO activar modo espera")
                    print(f"   Frase: '{speech_result}'")
                    print(f"   → Cliente NO está transfiriendo, está rechazando/explicando")
                    cliente_pidio_espera = False  # Desactivar modo espera

            # FIX 519: SENTIDO COMÚN con GPT - Analizar frases LARGAS/AMBIGUAS
            # Problema: BRUCE1736 - "marcó este número, pero con terminación 00, ahí le comunican"
            # Los patrones rígidos no pueden cubrir todas las variantes del lenguaje humano
            # Solución: Usar GPT mini para analizar la INTENCIÓN de frases ambiguas (>40 chars)
            if cliente_pidio_espera and len(speech_result) > 40:
                print(f"\n FIX 519: Frase larga ({len(speech_result)} chars) - Analizando intención con GPT...")
                try:
                    from openai import OpenAI
                    gpt_client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

                    prompt_intencion = f"""Analiza esta frase de un cliente en una llamada telefónica y determina su INTENCIÓN:

Frase del cliente: "{speech_result}"

El agente (Bruce) está preguntando por el encargado de compras. Determina qué quiere decir el cliente:

A) TRANSFERENCIA - El cliente va a TRANSFERIR la llamada o pasar el teléfono a otra persona
B) OTRO_NUMERO - El cliente está dando información de OTRO NÚMERO donde llamar (extensión, terminación, otro teléfono)
C) PREGUNTA - El cliente está haciendo una PREGUNTA (¿qué marca?, ¿de dónde?, etc.)
D) RECHAZO - El cliente está RECHAZANDO o diciendo que no puede ayudar
E) OTRO - Ninguna de las anteriores

Responde SOLO con una letra: A, B, C, D o E"""

                    response_gpt = gpt_client.chat.completions.create(
                        model="gpt-4o-mini",
                        messages=[{"role": "user", "content": prompt_intencion}],
                        max_tokens=5,
                        temperature=0
                    )

                    intencion = response_gpt.choices[0].message.content.strip().upper()
                    print(f"   GPT analizó intención: {intencion}")

                    # Si NO es transferencia, desactivar modo espera
                    if intencion != "A":
                        print(f"   FIX 519: GPT determinó que NO es transferencia ({intencion})")
                        if intencion == "B":
                            print(f"   → Cliente da información de OTRO NÚMERO")
                        elif intencion == "C":
                            print(f"   → Cliente hace PREGUNTA")
                        elif intencion == "D":
                            print(f"   → Cliente RECHAZA/no puede ayudar")
                        else:
                            print(f"   → Otra intención")
                        cliente_pidio_espera = False
                    else:
                        print(f"   FIX 519: GPT confirmó que ES transferencia - activar modo espera")

                except Exception as e:
                    print(f"   FIX 519: Error en GPT ({e}) - usando lógica de patrones")
                    # Si GPT falla, continuar con la lógica de patrones existente

            if cliente_pidio_espera:
                print(f"\n FIX 470: CLIENTE PIDIÓ ESPERAR - '{speech_result}'")
                print(f"   Estableciendo estado ESPERANDO_TRANSFERENCIA")

                # Establecer estado de espera en el agente
                from agente_ventas import EstadoConversacion
                agente.estado_conversacion = EstadoConversacion.ESPERANDO_TRANSFERENCIA
                agente.respuestas_vacias_consecutivas = 0  # Resetear contador

                # Registrar en historial
                agente.conversation_history.append({
                    "role": "user",
                    "content": speech_result
                })
                agente.conversation_history.append({
                    "role": "assistant",
                    "content": "Claro, espero."
                })

                bruce_id = agente.lead_data.get("bruce_id", "N/A")
                log_evento(f"{bruce_id} - CLIENTE DIJO: \"{speech_result}\"", "CLIENTE")
                log_evento(f"{bruce_id} DICE: \"Claro, espero.\" (FIX 470: modo espera)", "BRUCE")

                # Generar audio de respuesta corta
                audio_id = f"espera_{call_sid}"
                result = generar_audio_elevenlabs("Claro, espero.", audio_id)

                response = VoiceResponse()
                if result:
                    audio_url = request.url_root + f"audio/{audio_id}"
                    response.play(audio_url)
                else:
                    response.say("Claro, espero.", voice="alice", language="es-MX")

                # FIX 470: Usar timeout LARGO para esperar transferencia (30 segundos)
                response.record(
                    action="/procesar-respuesta",
                    method="POST",
                    max_length=1,
                    timeout=30,  # 30 segundos de espera
                    play_beep=False,
                    trim="trim-silence"
                )

                print(f"    FIX 470: Esperando transferencia con timeout de 30s...")
                return Response(str(response), mimetype="text/xml")

            es_pregunta_rapida = (
                frase_limpia.startswith('¿') or
                frase_limpia.startswith('qué ') or frase_limpia.startswith('que ') or
                frase_limpia.startswith('quién ') or frase_limpia.startswith('quien ') or
                frase_limpia.startswith('cuál ') or frase_limpia.startswith('cual ') or
                frase_limpia.startswith('cómo ') or frase_limpia.startswith('como ')
            )

            # 1. Frase muy corta (<3 palabras) después de ya haber hablado (>3 palabras antes)
            # FIX 260: Pero NO si es una pregunta (preguntas cortas son válidas)
            if palabras_nuevas < 3 and info_habla["palabras_dichas"] > 3 and not es_pregunta_rapida:
                frase_parece_incompleta = True
                print(f"    FIX 244: Frase corta ({palabras_nuevas} palabras) después de hablar")

            # 2. Frase termina en preposición/artículo/verbo copulativo (indica continuación)
            # FIX 250: Agregar verbos copulativos y auxiliares que requieren complemento
            # FIX 281: Agregar verbos en pretérito que indican continuación
            palabras_continuacion = [
                # Preposiciones
                "a", "de", "en", "la", "el", "lo", "un", "una", "para", "por", "con",
                # Verbos copulativos que requieren complemento
                "está", "esta", "es", "son", "están", "estan", "era", "fueron",
                # FIX 281: Verbos en pretérito imperfecto (indican que falta el complemento)
                "estaba", "estaban", "tenía", "tenia", "había", "habia", "iba",
                # Verbos auxiliares
                "va", "voy", "vas", "van", "puede", "pueden",
                # Conjunciones
                "y", "o", "pero", "mas",
                # Negaciones que requieren verbo
                "no", "ni", "tampoco"
            ]
            ultima_palabra = speech_result.strip().split()[-1].lower().rstrip('.,;:!?')

            # FIX 260: Reutilizar detección de pregunta (ya calculada arriba)
            # Agregar más palabras interrogativas para mayor cobertura
            es_pregunta = es_pregunta_rapida or (
                frase_limpia.startswith('dónde ') or frase_limpia.startswith('donde ') or
                frase_limpia.startswith('cuándo ') or frase_limpia.startswith('cuando ') or
                frase_limpia.startswith('cuánto ') or frase_limpia.startswith('cuanto ') or
                frase_limpia.startswith('por qué ') or frase_limpia.startswith('por que ')
            )

            # FIX 260: Si es pregunta, NO marcar como incompleta aunque termine en "es"
            if ultima_palabra in palabras_continuacion and not es_pregunta:
                frase_parece_incompleta = True
                print(f"    FIX 244/250: Frase termina en '{ultima_palabra}' (continuación esperada)")
            elif ultima_palabra in palabras_continuacion and es_pregunta:
                print(f"    FIX 260: Frase termina en '{ultima_palabra}' pero ES PREGUNTA - responder inmediatamente")

            # 3. Si lleva menos de 2 segundos hablando y dijo más de 2 palabras
            # FIX 264: Pero NO si es una pregunta o termina en signo de interrogación
            termina_en_pregunta = speech_result.strip().endswith('?') or '¿' in speech_result
            if tiempo_hablando < 2.0 and palabras_nuevas >= 2 and not es_pregunta and not termina_en_pregunta:
                # Probablemente sigue hablando - el timeout de 2s lo interrumpió
                frase_parece_incompleta = True
                print(f"    FIX 244: Habló rápido ({tiempo_hablando:.1f}s) - probablemente sigue hablando")
            elif tiempo_hablando < 2.0 and (es_pregunta or termina_en_pregunta):
                print(f"    FIX 264: Habló rápido pero ES PREGUNTA - responder inmediatamente")

            # FIX 253: Detectar si cliente está deletreando email (arroba, punto, @)
            # FIX 499: PERO si FIX 265 ya determinó que el email está completo, NO marcar como incompleto
            palabras_deletreo_email = ["arroba", "punto", "guion", "guión", "bajo", "@", "gmail", "hotmail", "yahoo"]
            esta_deletreando_email = any(palabra in speech_result.lower() for palabra in palabras_deletreo_email)

            if esta_deletreando_email and not email_detectado_completo:
                frase_parece_incompleta = True
                print(f"    FIX 253: Cliente deletreando email (detectado: {[p for p in palabras_deletreo_email if p in speech_result.lower()]})")
            elif esta_deletreando_email and email_detectado_completo:
                print(f"    FIX 499: Email COMPLETO detectado - NO esperar más, procesar ahora")
                # FIX 504: BRUCE1479 - Forzar que NO espere cuando email ya está completo
                frase_parece_incompleta = False

            # FIX 286: Detectar si cliente está repitiendo lo mismo (indica que espera respuesta)
            if hasattr(agente, 'transcripcion_parcial_acumulada') and len(agente.transcripcion_parcial_acumulada) >= 2:
                ultimas_2 = [t.lower().strip() for t in agente.transcripcion_parcial_acumulada[-2:]]
                speech_lower_strip = speech_result.lower().strip()
                # Si las últimas 2 transcripciones son iguales a la actual, el cliente está repitiendo
                if ultimas_2[-1] == speech_lower_strip or (len(ultimas_2) >= 2 and ultimas_2[-1] == ultimas_2[-2] == speech_lower_strip):
                    print(f"\n FIX 286: CLIENTE REPITIENDO - probablemente terminó de deletrear")
                    print(f"   Repitiendo: '{speech_result}'")
                    print(f"   Historial: {agente.transcripcion_parcial_acumulada[-3:]}")
                    frase_parece_incompleta = False  # Forzar respuesta

            # FIX 441: Casos BRUCE1329-1332 - NO esperar para saludos simples
            # Los saludos son frases completas por sí mismas, no necesitan continuación
            saludos_simples = [
                'hola', 'buenas', 'buenos días', 'buenos dias', 'buen día', 'buen dia',
                'buenas tardes', 'buenas noches', 'qué tal', 'que tal',
                'bueno', 'aló', 'alo', 'diga', 'dígame', 'digame',
                'mande', 'sí', 'si', 'sí dígame', 'si digame',
                # FIX 458: BRUCE1377 - Agregar variantes con coma/puntuación
                'sí, dígame', 'si, digame', 'sí, diga', 'si, diga',
                'buen día, dígame', 'buen dia, digame',
                # FIX 529 BRUCE1686: Saludos combinados con "sí" al inicio
                # FIX 531 BRUCE1672: Agregar TODAS las variantes con/sin acentos
                'sí buenos días', 'si buenos dias', 'sí buenos dias', 'si buenos días',
                'sí buen día', 'si buen dia', 'sí buen dia', 'si buen día',
                'sí buenas tardes', 'si buenas tardes', 'sí buenas', 'si buenas',
                'sí hola', 'si hola', 'hola buenos días', 'hola buenos dias',
                'hola buen día', 'hola buen dia', 'hola buenas tardes',
                # FIX 531: Variantes adicionales detectadas
                'buenos días', 'buen dia', 'bueno buen día', 'bueno buen dia'
            ]
            # FIX 458: Limpiar TODA la puntuación (incluyendo comas internas) para comparar
            # FIX 531: También normalizar espacios múltiples que quedan después de eliminar puntuación
            frase_para_comparar = re.sub(r'[.,;:!?¿¡]', '', frase_limpia).strip()
            frase_para_comparar = re.sub(r'\s+', ' ', frase_para_comparar)  # FIX 531: Colapsar espacios múltiples
            # También crear lista de saludos sin puntuación para comparar
            saludos_sin_puntuacion = [re.sub(r'\s+', ' ', re.sub(r'[.,;:!?¿¡]', '', s)).strip() for s in saludos_simples]
            frase_es_saludo_simple = frase_para_comparar in saludos_sin_puntuacion or frase_limpia.strip('.,;:!?¿¡') in saludos_simples

            # FIX 453: Caso BRUCE1347 - NO tratar "Sí" como saludo si cliente estaba dando dato
            # Si hay transcripciones parciales previas que terminan en "es", "teléfono", etc.
            # el cliente probablemente está confirmando que va a dar el dato, NO saludando
            cliente_dando_dato_previo = False
            if hasattr(agente, 'transcripcion_parcial_acumulada') and agente.transcripcion_parcial_acumulada:
                ultima_parcial = agente.transcripcion_parcial_acumulada[-1].lower().strip()
                palabras_esperando_dato = ['es', 'teléfono', 'telefono', 'correo', 'email', 'número', 'numero', 'whatsapp']
                # Verificar si la última transcripción termina en palabra que espera dato
                for palabra in palabras_esperando_dato:
                    if ultima_parcial.endswith(palabra) or f'{palabra} es' in ultima_parcial or f'el {palabra}' in ultima_parcial:
                        cliente_dando_dato_previo = True
                        print(f"    FIX 453: Contexto previo indica dato pendiente ('{ultima_parcial}')")
                        break

            if frase_parece_incompleta and frase_es_saludo_simple and not cliente_dando_dato_previo:
                print(f"    FIX 441: '{speech_result}' es saludo simple - NO esperar continuación")
                frase_parece_incompleta = False  # Forzar respuesta inmediata
            elif frase_es_saludo_simple and cliente_dando_dato_previo:
                print(f"    FIX 453: '{speech_result}' parece saludo PERO cliente daba dato - ESPERAR")

            # FIX 473: BRUCE1425 - Detectar frases de CORTESIA como respuestas completas
            # En Mexico es comun responder "Buen dia, a sus ordenes" o "Para servirle"
            frases_cortesia = [
                'a sus órdenes', 'a sus ordenes', 'a tus órdenes', 'a tus ordenes',
                'para servirle', 'para servirte', 'en qué le puedo ayudar', 'en que le puedo ayudar',
                'en qué puedo servirle', 'en que puedo servirle', 'cómo le puedo ayudar',
                'como le puedo ayudar', 'a la orden', 'a sus órdenes señor', 'a sus ordenes señor',
                'con mucho gusto', 'a la brevedad'
            ]
            frase_es_cortesia = any(cortesia in frase_limpia for cortesia in frases_cortesia)

            if frase_parece_incompleta and frase_es_cortesia:
                print(f"    FIX 473: BRUCE1425 - '{speech_result}' es frase de CORTESIA - NO esperar")
                frase_parece_incompleta = False  # Forzar respuesta inmediata

            # FIX 529: BRUCE1802 - "sí dígame" y variantes con prefijos son respuestas de PRESENCIA
            # Cliente dice "este, sí, dígame" o "ajá, dígame" indicando que está listo para escuchar
            # El problema es que FIX 244 los marca como "incompletos" por hablar rápido
            respuestas_presencia_completas = [
                'dígame', 'digame', 'diga', 'mande',
                'sí dígame', 'si digame', 'sí, dígame', 'si, digame',
                'sí diga', 'si diga', 'sí, diga', 'si, diga',
                'adelante', 'a la orden'
            ]
            # Verificar si la frase CONTIENE (no solo termina) en respuesta de presencia
            es_presencia_con_prefijo = any(resp in frase_limpia for resp in respuestas_presencia_completas)

            if frase_parece_incompleta and es_presencia_con_prefijo:
                print(f"    FIX 529: BRUCE1802 - '{speech_result}' contiene respuesta de PRESENCIA - NO esperar")
                frase_parece_incompleta = False  # Forzar respuesta inmediata

            # FIX 471: BRUCE1415 - "No tengo" es respuesta completa, NO esperar continuación
            # El cliente está diciendo que no hay encargado de compras
            respuestas_no_hay_encargado = [
                'no tengo', 'no tenemos', 'no hay', 'aquí no hay', 'aqui no hay',
                'no contamos', 'no está', 'no esta', 'no se encuentra',
                'no lo tengo', 'no la tengo', 'no, no hay'
            ]
            frase_es_no_hay_encargado = any(resp in frase_limpia for resp in respuestas_no_hay_encargado)

            if frase_parece_incompleta and frase_es_no_hay_encargado:
                print(f"    FIX 471: '{speech_result}' indica NO HAY ENCARGADO - NO esperar continuación")
                frase_parece_incompleta = False  # Forzar respuesta inmediata

            # FIX 472: BRUCE1419 - Si cliente responde solo "No" a pregunta sobre encargado
            # "No" solo ES respuesta completa cuando Bruce acaba de preguntar por el encargado
            import re
            frase_sin_puntuacion = re.sub(r'[.,;:!?¿¡]', '', frase_limpia).strip()
            if frase_parece_incompleta and frase_sin_puntuacion in ['no', 'no gracias', 'no no']:
                # Verificar si Bruce acaba de preguntar por el encargado
                ultimo_mensaje_bruce = ""
                # FIX 484: BRUCE1459 - Corregir atributo (historial → conversation_history)
                if agente.conversation_history:
                    for msg in reversed(agente.conversation_history):
                        if msg.get('role') == 'assistant':
                            ultimo_mensaje_bruce = msg.get('content', '').lower()
                            break

                # Buscar si pregunto por encargado
                bruce_pregunto_encargado = any(p in ultimo_mensaje_bruce for p in [
                    'encargado', 'encargada', 'quien ve las compras', 'quien maneja las compras',
                    'responsable de compras', 'se encontrara', 'se encuentra'
                ])

                if bruce_pregunto_encargado:
                    print(f"    FIX 472: BRUCE1419 - Cliente dijo '{speech_result}' a pregunta de encargado")
                    print(f"   Ultimo de Bruce: '{ultimo_mensaje_bruce[:60]}...'")
                    print(f"   'No' es respuesta COMPLETA - NO esperar continuacion")
                    frase_parece_incompleta = False  # Forzar respuesta inmediata

            # FIX 500: BRUCE1476 - Separar OFERTAS de DICTADO
            # OFERTAS: Cliente PREGUNTA si quieres el correo → Responder inmediatamente
            # DICTADO: Cliente YA ESTÁ dando el correo → Esperar a que termine

            # Frases de OFERTA (pregunta si quieres el correo/whatsapp)
            frases_oferta_correo = [
                'te puedo pasar el correo', 'le puedo pasar el correo',
                'te paso el correo', 'le paso el correo', 'te paso correo', 'le paso correo',
                'quieres el correo', 'quiere el correo', 'quieres que te pase correo',
                'quiere que le pase correo', 'quieres que te pase el correo',
                'te puedo dar el correo', 'le puedo dar el correo', 'te puedo dar correo',
                'por correo', 'mejor por correo', 'mándamelo por correo', 'mandamelo por correo'
            ]
            frases_oferta_whatsapp = [
                'te puedo pasar el whatsapp', 'le puedo pasar el whatsapp',
                'te paso el whatsapp', 'le paso el whatsapp', 'te paso el número',
                'le paso el número', 'te paso numero', 'le paso numero',
                'quieres el whatsapp', 'quiere el whatsapp', 'quieres el número',
                'quiere el número', 'te puedo dar el número', 'le puedo dar el número',
                'por whatsapp', 'mejor por whatsapp', 'al whatsapp', 'a tu whatsapp',
                'te lo mando por whatsapp', 'se lo mando por whatsapp',
                # FIX 523: BRUCE1752 - Variantes de "por vía whatsapp" y aceptaciones directas
                'por vía whatsapp', 'por via whatsapp', 'vía whatsapp', 'via whatsapp',
                'whatsapp estaría bien', 'whatsapp estaria bien', 'whatsapp está bien', 'whatsapp esta bien',
                'sí por whatsapp', 'si por whatsapp', 'sí, por whatsapp', 'si, por whatsapp',
                'sí whatsapp', 'si whatsapp', 'whatsapp sí', 'whatsapp si',
                'prefiero whatsapp', 'mejor whatsapp', 'whatsapp mejor',
                'a mi whatsapp', 'a este whatsapp', 'a su whatsapp'
            ]

            cliente_ofrece_correo = any(frase in frase_limpia for frase in frases_oferta_correo)
            cliente_ofrece_whatsapp = any(frase in frase_limpia for frase in frases_oferta_whatsapp)

            # FIX 500: Si cliente OFRECE correo/WhatsApp → Responder inmediatamente
            if cliente_ofrece_correo or cliente_ofrece_whatsapp:
                tipo_oferta = "correo" if cliente_ofrece_correo else "WhatsApp"
                print(f"\n FIX 500: BRUCE1476 - Cliente OFRECE {tipo_oferta}")
                print(f"   Detectado: '{speech_result}'")
                print(f"   Respuesta INMEDIATA - NO esperar")

                # Generar respuesta directa
                if cliente_ofrece_correo:
                    respuesta_oferta = "Sí, por favor, dígame el correo."
                else:
                    respuesta_oferta = "Sí, por favor, dígame el número."

                # Log el evento
                bruce_id = agente.lead_data.get("bruce_id", "N/A")
                log_evento(f"{bruce_id} DICE: \"{respuesta_oferta}\" (FIX 500: respuesta a oferta)", "BRUCE")

                # FIX 500b: Generar audio con función global (corrige AttributeError)
                audio_id = f"oferta_{call_sid}_{int(time.time())}"
                result = generar_audio_elevenlabs(respuesta_oferta, audio_id)

                if result:
                    audio_url = request.url_root + f"audio/{audio_id}"
                    response = VoiceResponse()
                    response.play(audio_url)
                    # FIX 502: Corregir ruta - usar /procesar-respuesta con Record (como el resto del código)
                    response.record(
                        action="/procesar-respuesta",
                        method="POST",
                        max_length=30,
                        timeout=3,
                        play_beep=False,
                        trim="trim-silence"
                    )
                    return Response(str(response), mimetype="text/xml")

            # FIX 443: Caso BRUCE1334 - Detectar cuando cliente ESTÁ DICTANDO datos
            # Si el cliente YA ESTÁ dando el correo/email/número, ESPERAR a que termine
            # Frases que indican que YA está dando el dato (no solo ofreciendo)
            frases_dictando_datos = [
                'anota', 'apunta', 'ahí le va', 'ahí te va', 'toma nota', 'tome nota',
                'el correo es', 'mi correo es', 'el email es', 'mi email es',
                'el mail es', 'mi mail es', 'su correo es',
                'el número es', 'mi número es', 'el whatsapp es', 'mi whatsapp es',
                'arroba', 'punto com', 'punto mx', '@', 'gmail', 'hotmail', 'yahoo', 'outlook'
            ]
            cliente_dictando_datos = any(frase in frase_limpia for frase in frases_dictando_datos)

            # FIX 504: BRUCE1479 - Si ya hay email completo, NO sobrescribir con espera
            if cliente_dictando_datos and not email_detectado_completo:
                print(f"    FIX 443: CLIENTE DICTANDO DATOS - esperar a que termine")
                print(f"   Detectado: '{speech_result}'")
                frase_parece_incompleta = True  # Forzar espera para captar el dato completo
                esta_deletreando_email = True  # Usar timeout largo (2.5s) igual que con emails
            elif cliente_dictando_datos and email_detectado_completo:
                print(f"    FIX 504: Dictado detectado PERO email ya completo - procesar ahora")

            if frase_parece_incompleta:
                print(f"\n FIX 244: CLIENTE HABLANDO PAUSADAMENTE - esperando que termine")
                print(f"   Transcripción parcial: '{speech_result}'")
                print(f"   Tiempo hablando: {tiempo_hablando:.1f}s")
                print(f"   Palabras dichas: {palabras_nuevas} (historial: {info_habla['palabras_dichas']})")

                # Almacenar esta transcripción parcial en el agente
                if not hasattr(agente, 'transcripcion_parcial_acumulada'):
                    agente.transcripcion_parcial_acumulada = []
                agente.transcripcion_parcial_acumulada.append(speech_result)

                # FIX 286: Limitar a máximo 5 esperas para evitar loops infinitos
                if len(agente.transcripcion_parcial_acumulada) >= 5:
                    print(f"\n FIX 286: LÍMITE DE ESPERA ALCANZADO ({len(agente.transcripcion_parcial_acumulada)} parciales)")
                    print(f"   Forzando respuesta para evitar timeout infinito")
                    # NO retornar - dejar que procese con GPT
                else:
                    # Generar TwiML para seguir escuchando SIN interrumpir
                    response = VoiceResponse()

                    # FIX 244/395/442: Timeout dinámico basado en contenido
                    # - 2.5s para deletreo de email (necesita más tiempo)
                    # - 1.5s para otras frases (reducir delay percibido - casos BRUCE1329-1332)
                    timeout_espera = 2.5 if esta_deletreando_email else 1.5

                    response.record(
                        action="/procesar-respuesta",
                        method="POST",
                        max_length=1,
                        timeout=timeout_espera,
                        play_beep=False,
                        trim="trim-silence"
                    )

                    print(f"    FIX 244/395/442: Esperando continuación con timeout de {timeout_espera}s...")
                    return Response(str(response), mimetype="text/xml")

        # Si llegó aquí y hay transcripciones parciales acumuladas, concatenar
        if hasattr(agente, 'transcripcion_parcial_acumulada') and agente.transcripcion_parcial_acumulada:
            print(f"\n FIX 244: Concatenando transcripciones parciales")
            for i, parcial in enumerate(agente.transcripcion_parcial_acumulada):
                print(f"   [{i}] '{parcial}'")

            # Agregar la transcripción actual
            agente.transcripcion_parcial_acumulada.append(speech_result)

            # Concatenar todas las partes
            speech_result = " ".join(agente.transcripcion_parcial_acumulada)
            print(f"    FIX 244: Frase completa: '{speech_result}'")

            # Limpiar acumulador
            agente.transcripcion_parcial_acumulada = []

        # Resetear tracking de habla activa (cliente terminó de hablar)
        if call_sid in cliente_hablando_activo:
            del cliente_hablando_activo[call_sid]

    # FIX 92: Detectar respuestas vacías y pedir repetición antes de colgar
    if not speech_result or speech_result.strip() == "":
        # FIX 470: BRUCE1412 - Si estamos en modo ESPERANDO_TRANSFERENCIA, NO contar como vacía
        # El cliente pidió "Permítame un segundo" y está transfiriendo la llamada
        from agente_ventas import EstadoConversacion
        if agente.estado_conversacion == EstadoConversacion.ESPERANDO_TRANSFERENCIA:
            print(f" FIX 470: Respuesta vacía pero estamos en ESPERANDO_TRANSFERENCIA - seguir esperando")
            print(f"   Silencios ignorados, esperando que cliente vuelva...")

            # NO incrementar respuestas_vacias_consecutivas
            response = VoiceResponse()

            # Seguir esperando con timeout largo
            response.record(
                action="/procesar-respuesta",
                method="POST",
                max_length=1,
                timeout=30,  # 30 segundos más de espera
                play_beep=False,
                trim="trim-silence"
            )

            print(f"    FIX 470: Continuando espera con timeout de 30s...")
            return Response(str(response), mimetype="text/xml")

        agente.respuestas_vacias_consecutivas += 1
        print(f" Respuesta vacía #{agente.respuestas_vacias_consecutivas}")

        # FIX 145: Si es el PRIMER mensaje y está vacío, NO pedir repetición
        # Cliente normal necesita 2-3s para procesar "Hola, buen dia"
        # Contar mensajes de usuario para detectar si es primera respuesta
        mensajes_usuario = [msg for msg in agente.conversation_history if msg['role'] == 'user']
        es_primer_mensaje = len(mensajes_usuario) == 0

        if es_primer_mensaje:
            # FIX 408: Lógica progresiva de timeouts - NO asumir "bueno" inmediatamente
            # Cliente podría haber dicho "no está" y perdemos la conversación

            # Incrementar contador de timeouts
            agente.timeouts_deepgram += 1
            print(f" FIX 408: Primer mensaje vacío (timeout #{agente.timeouts_deepgram})")

            agente.respuestas_vacias_consecutivas = 0  # No contar como vacía
            response = VoiceResponse()
            bruce_id = agente.lead_data.get("bruce_id", "N/A")

            # LÓGICA PROGRESIVA: Máximo 2 pedidos de repetición
            if agente.timeouts_deepgram == 1:
                # PRIMER TIMEOUT: Pedir repetición natural
                respuesta_timeout = "Disculpe, no alcancé a escucharle bien, ¿me podría repetir?"
                print(f"    FIX 408: Primer timeout - pidiendo repetición natural")

                # Agregar al historial
                agente.conversation_history.append({
                    "role": "user",
                    "content": "[Timeout Deepgram - no se transcribió]"
                })
                agente.conversation_history.append({
                    "role": "assistant",
                    "content": respuesta_timeout
                })

                # Generar audio
                audio_id = f"timeout1_{call_sid}"
                result = generar_audio_elevenlabs(respuesta_timeout, audio_id)
                if result:
                    audio_url = request.url_root + f"audio/{audio_id}"
                    response.play(audio_url)
                else:
                    response.say(respuesta_timeout, voice="alice", language="es-MX")

                log_evento(f"{bruce_id} DICE: \"{respuesta_timeout}\" (FIX 408: timeout #1)", "BRUCE")

            elif agente.timeouts_deepgram == 2:
                # SEGUNDO TIMEOUT: Pedir repetición más directa
                respuesta_timeout = "¿Me escucha? Parece que hay interferencia"
                print(f"    FIX 408: Segundo timeout - pidiendo repetición directa")

                # Agregar al historial
                agente.conversation_history.append({
                    "role": "user",
                    "content": "[Timeout Deepgram #2 - no se transcribió]"
                })
                agente.conversation_history.append({
                    "role": "assistant",
                    "content": respuesta_timeout
                })

                # Generar audio
                audio_id = f"timeout2_{call_sid}"
                result = generar_audio_elevenlabs(respuesta_timeout, audio_id)
                if result:
                    audio_url = request.url_root + f"audio/{audio_id}"
                    response.play(audio_url)
                else:
                    response.say(respuesta_timeout, voice="alice", language="es-MX")

                log_evento(f"{bruce_id} DICE: \"{respuesta_timeout}\" (FIX 408: timeout #2)", "BRUCE")

            else:
                # TERCER TIMEOUT+: Asumir problema de audio y continuar (lógica original FIX 211)
                print(f"    FIX 408: Tercer timeout - asumiendo problema de audio, continuando con saludo")
                segunda_parte = "Me comunico de la marca nioval, más que nada quería brindar informacion de nuestros productos ferreteros, ¿Se encontrara el encargado o encargada de compras?"

                # Agregar al historial como si hubiera respondido
                agente.conversation_history.append({
                    "role": "user",
                    "content": "[Cliente respondió - problema de audio]"
                })
                agente.conversation_history.append({
                    "role": "assistant",
                    "content": segunda_parte
                })

                # FIX 455: Limpiar transcripciones antes de enviar segunda parte
                import time as time_mod  # FIX 455: Import local
                if call_sid in deepgram_transcripciones and deepgram_transcripciones[call_sid]:
                    print(f" FIX 455: Limpiando {len(deepgram_transcripciones[call_sid])} transcripciones (segunda parte)")
                    deepgram_transcripciones[call_sid] = []
                    if call_sid in deepgram_ultima_final:
                        deepgram_ultima_final[call_sid] = {}
                bruce_audio_enviado_timestamp[call_sid] = time_mod.time()

                # Usar audio pre-generado si existe
                if "segunda_parte_saludo" in audio_cache:
                    audio_id = f"segunda_parte_vacio_{call_sid}"
                    audio_files[audio_id] = audio_cache["segunda_parte_saludo"]
                    audio_url = request.url_root + f"audio/{audio_id}"
                    print(f" FIX 408: Usando audio pre-generado de segunda_parte_saludo")
                    response.play(audio_url)
                else:
                    # Generar audio si no está en caché
                    audio_id = f"segunda_parte_vacio_{call_sid}"
                    result = generar_audio_elevenlabs(segunda_parte, audio_id)
                    if result:
                        audio_url = request.url_root + f"audio/{audio_id}"
                        response.play(audio_url)
                    else:
                        response.say(segunda_parte, voice="alice", language="es-MX")

                log_evento(f"{bruce_id} DICE: \"{segunda_parte}\" (FIX 408: timeout #3+, continuando)", "BRUCE")

            # FIX 214/215: Record en lugar de Gather (elimina costos de Speech Recognition)
            response.record(
                action="/procesar-respuesta",
                method="POST",
                max_length=1,
                timeout=2,  # FIX 215: Reducido de 8s a 2s
                play_beep=False,
                trim="trim-silence"
            )

            print(f" FIX 408: Respuesta enviada según nivel de timeout")
            return Response(str(response), mimetype="text/xml")

        # FIX 143: Si acabamos de responder a cliente desesperado, NO pedir repetición
        # El cliente necesita tiempo para procesar la confirmación "Sí, estoy aquí"
        if agente.acaba_de_responder_desesperado:
            print(f" FIX 143: Cliente desesperado acaba de recibir confirmación - NO pedir repetición")
            print(f"   Esperando a que cliente procese y responda...")
            agente.acaba_de_responder_desesperado = False  # Resetear flag
            agente.respuestas_vacias_consecutivas = 0  # Resetear contador

            # FIX 214/215: Simplemente esperar sin pedir repetición (Record + Deepgram)
            response = VoiceResponse()
            response.record(
                action="/procesar-respuesta",
                method="POST",
                max_length=1,
                timeout=3,  # FIX 215: Reducido de 8s a 3s
                play_beep=False,
                trim="trim-silence"
            )
            print(f" FIX 143: Esperando respuesta sin pedir repetición (Record)")
            return Response(str(response), mimetype="text/xml")

        # FIX 170: Si cliente va a pasar al encargado, esperar MÁS tiempo
        # El cliente necesita 15-20s para localizar y pasar al encargado
        if agente.esperando_transferencia:
            print(f" FIX 170: Cliente va a pasar al encargado - Esperando transferencia...")
            print(f"   Timeout extendido a 20s para dar tiempo a la transferencia")
            agente.esperando_transferencia = False  # Resetear flag después de primer timeout
            agente.respuestas_vacias_consecutivas = 0  # Resetear contador

            # FIX 214: Esperar 20 segundos para que pase al encargado (Record + Deepgram)
            response = VoiceResponse()
            response.record(
                action="/procesar-respuesta",
                method="POST",
                max_length=1,
                timeout=20,  # 20s para transferencia
                play_beep=False,
                trim="trim-silence"
            )
            print(f" FIX 170: Esperando hasta 20s para que cliente pase al encargado (Record)")
            return Response(str(response), mimetype="text/xml")

        # Primera o segunda vez: Pedir amablemente que repitan
        if agente.respuestas_vacias_consecutivas <= 2:
            print(f" Bruce pedirá que le repitan (intento #{agente.respuestas_vacias_consecutivas})")

            # Frases variadas para pedir repetición
            frases_repeticion = [
                "Disculpa, no te escuché bien, ¿me puedes repetir?",
                "Perdón, no logré escucharte, ¿me lo repites por favor?",
                "No alcancé a escucharte, ¿me lo dices de nuevo?"
            ]

            # Alternar entre las frases según el intento
            respuesta_agente = frases_repeticion[(agente.respuestas_vacias_consecutivas - 1) % len(frases_repeticion)]

            # FIX 152: LOG cuando se reproduce "Disculpa no te escuché bien"
            print(f" FIX 152: REPRODUCIENDO MENSAJE DE REPETICIÓN")
            print(f"   Mensaje: '{respuesta_agente}'")
            print(f"   Razón: Timeout expiró sin respuesta del cliente")
            print(f"   Intento: #{agente.respuestas_vacias_consecutivas}")

            # Generar audio y responder
            response = VoiceResponse()
            audio_id = f"repeticion_{call_sid}_{agente.respuestas_vacias_consecutivas}"

            # Usar función global generar_audio_elevenlabs (no es método de agente)
            result = generar_audio_elevenlabs(respuesta_agente, audio_id)

            if result is not None:
                # Audio generado exitosamente
                audio_url = request.url_root + f"audio/{audio_id}"
                response.play(audio_url)
            else:
                # Fallback a Polly si ElevenLabs falla
                response.say(respuesta_agente, voice="Polly.Mia", language="es-MX")

            # FIX 152: LOG adicional después de generar
            print(f" Bruce pidió que le repitan")

            # FIX 214/215: Esperar respuesta del cliente (Record + Deepgram)
            response.record(
                action="/procesar-respuesta",
                method="POST",
                max_length=1,
                timeout=3,  # FIX 215: Reducido de 10s a 3s
                play_beep=False,
                trim="trim-silence"
            )

            print(f" Bruce pidió que le repitan (Record)")
            return Response(str(response), mimetype="text/xml")

        # Tercera vez: Cliente probablemente colgó
        else:
            print(f" Detectadas 3 respuestas vacías consecutivas")
            print(f" Cliente probablemente colgó o no responde")

            # FIX 176: Verificar si se capturaron datos antes de marcar como "Colgo"
            tiene_dato_capturado = (
                agente.lead_data.get("whatsapp") or
                agente.lead_data.get("email") or
                agente.lead_data.get("referencia_telefono")
            )

            # Marcar como "Colgo" o "No Contesta" según el caso
            if agente.lead_data["estado_llamada"] == "Respondio" and not tiene_dato_capturado:
                # Si había respondido antes, probablemente colgó
                agente.lead_data["estado_llamada"] = "Colgo"
                agente.lead_data["pregunta_0"] = "Colgo"
                agente.lead_data["pregunta_7"] = "Colgo"
                agente.lead_data["resultado"] = "NEGADO"
                print(f" Estado actualizado: Cliente colgó (3 silencios, sin datos)")
            elif tiene_dato_capturado:
                # FIX 176: Si hay datos, determinar conclusión correcta
                print(f" FIX 176: 3 silencios pero SÍ hay datos capturados")
                # FIX 177: Forzar recálculo para sobrescribir "Colgo" temporal
                agente._determinar_conclusion(forzar_recalculo=True)
                print(f"   Conclusión: {agente.lead_data.get('pregunta_7')}")

            # Guardar la llamada
            agente.guardar_llamada_y_lead()

            # Terminar llamada
            response = VoiceResponse()
            response.hangup()
            return Response(str(response), mimetype="text/xml")
    else:
        # Resetear contador si hubo respuesta
        agente.respuestas_vacias_consecutivas = 0

    # FIX 121: DETECCIÓN RÁPIDA DE SALUDOS PARA SEGUNDA PARTE (FIX 112)
    # Si el cliente responde con saludo simple después de "Hola, buen dia",
    # responder INMEDIATAMENTE con segunda parte desde caché (0s delay GPT)
    speech_lower = speech_result.lower().strip()

    # FIX 121: Detectar si esta es la primera respuesta del cliente contando solo mensajes USER
    mensajes_usuario = [msg for msg in agente.conversation_history if msg['role'] == 'user']
    es_primera_respuesta = len(mensajes_usuario) == 0

    print(f" FIX 121 DEBUG: len(conversation_history)={len(agente.conversation_history)}, mensajes_usuario={len(mensajes_usuario)}, es_primera_respuesta={es_primera_respuesta}")

    # FIX 210: Saludos simples del cliente - AMPLIADO
    # Cuando el cliente responde con cualquiera de estos al primer saludo,
    # Bruce debe responder INMEDIATAMENTE con la segunda parte del saludo
    saludos_simples = [
        # Saludos básicos
        "hola", "bueno", "buenos días", "buenos dias", "buen día", "buen dia",
        "buenas tardes", "buenas noches", "buenas",
        # Confirmaciones/Atención
        "diga", "dígame", "digame", "sí", "si", "aló", "alo",
        "qué onda", "que onda", "mande", "a sus órdenes", "a sus ordenes",
        # FIX 210: Nuevos saludos detectados en llamadas reales
        "qué tal", "que tal", "qué hubo", "que hubo", "quihúbole", "quiubole",
        "qué pasó", "que paso", "qué pasa", "que pasa",
        "adelante", "a ver", "sí diga", "si diga", "sí dígame", "si digame",
        "qué se le ofrece", "que se le ofrece", "en qué le ayudo", "en que le ayudo",
        "con quién hablo", "con quien hablo", "quién es", "quien es",
        # Saludos formales
        "muy buenas", "muy buenas tardes", "muy buenos días", "muy buenos dias",
        # Respuestas cortas de atención
        "aquí", "aqui", "presente", "escucho", "le escucho", "lo escucho",
        "dígame en qué le ayudo", "digame en que le ayudo"
    ]

    # FIX 121/314: Si es saludo simple en primera respuesta, usar caché inmediato
    usa_segunda_parte_saludo = False

    # FIX 314: Verificar si ya detectamos saludo en interim (pre-cargado)
    if call_sid in respuesta_precargada and respuesta_precargada[call_sid].get("tipo") == "segunda_parte_saludo":
        usa_segunda_parte_saludo = True
        print(f" FIX 314: Saludo YA detectado en INTERIM - usando respuesta pre-cargada")
        print(f"   Respuesta será instantánea (0s delay)")
    elif es_primera_respuesta and any(saludo in speech_lower for saludo in saludos_simples):
        # Verificar que la respuesta sea SOLO el saludo (no más de 5 palabras)
        palabras = speech_result.split()
        if len(palabras) <= 5:
            usa_segunda_parte_saludo = True
            print(f" FIX 121: Saludo simple detectado en primera respuesta: '{speech_result}'")
            print(f"   Usando CACHE de segunda_parte_saludo para respuesta instantánea (0s GPT)")

    # FIX 56/70: VERIFICAR CACHÉ DE RESPUESTAS ANTES DE LLAMAR GPT (0s delay)
    import time
    import threading
    inicio = time.time()

    # Variable para almacenar la respuesta cuando termine GPT
    respuesta_container = {"respuesta": None, "completado": False, "desde_cache": False, "categoria_cache": None}

    # Detectar si la pregunta está en el caché
    respuesta_desde_cache = None

    global cache_respuestas_stats
    cache_respuestas_stats["total_consultas"] += 1

    # FIX 70: Detectar objeciones en el historial reciente para DESHABILITAR CACHE
    tiene_objeciones_activas = False
    frases_objecion = [
        "ya tenemos proveedor", "solo trabajamos con", "solamente trabajamos",
        "únicamente trabajamos", "no nos interesa", "no queremos",
        "no podemos", "tenemos contrato", "somos distribuidores de"
    ]

    # Revisar las últimas 3 respuestas del cliente
    mensajes_cliente = [msg for msg in agente.conversation_history if msg['role'] == 'user']
    ultimas_respuestas = mensajes_cliente[-3:] if len(mensajes_cliente) >= 3 else mensajes_cliente

    for msg in ultimas_respuestas:
        texto = msg['content'].lower()
        for frase_obj in frases_objecion:
            if frase_obj in texto:
                tiene_objeciones_activas = True
                print(f" FIX 70: Objeción detectada en historial - DESHABILITANDO CACHE")
                print(f"   Frase: '{frase_obj}'")
                break
        if tiene_objeciones_activas:
            break

    # FIX 71: DESHABILITAR CACHE COMPLETAMENTE hasta resolver loops
    # El cache estaba causando respuestas sin contexto que ignoraban objeciones
    print(f" FIX 71: CACHE DESHABILITADO TEMPORALMENTE - Usando solo GPT con contexto completo")
    print(f"   Razón: Cache causaba loops y respuestas sin contexto")

    # TODO: Re-habilitar cache cuando se resuelvan los loops de repetición
    # El cache es beneficioso (0s delay) pero solo si respeta el contexto

    # COMENTADO TEMPORALMENTE:
    # if not tiene_objeciones_activas:
    #     for categoria, datos in respuestas_cache.items():
    #         for patron in datos["patrones"]:
    #             if patron in speech_lower:
    #                 respuesta_desde_cache = datos["respuesta"]
    #                 ...

    # FIX 115/121/131: Si detectamos saludo simple, usar caché directo sin GPT
    if usa_segunda_parte_saludo:
        timestamp_inicio_cache = time.time()
        print(f" FIX 121: INICIANDO respuesta desde caché de segunda parte...")

        # FIX 131: Verificar si Bruce YA dijo la segunda parte (cliente interrumpió)
        # Si hay 2+ mensajes de Bruce, significa que ya se dijo la segunda parte
        mensajes_bruce_previos = [msg for msg in agente.conversation_history if msg['role'] == 'assistant']
        bruce_ya_dijo_segunda_parte = len(mensajes_bruce_previos) >= 2

        if bruce_ya_dijo_segunda_parte:
            # Cliente interrumpió mientras Bruce hablaba el 2do mensaje
            # NO usar caché, usar GPT para responder con nexo
            print(f" FIX 131: Cliente interrumpió en 2do mensaje - NO usar caché")
            print(f"   Cliente dijo: '{speech_result}' mientras Bruce hablaba segunda parte")
            print(f"   Usando GPT con instrucción de nexo en lugar de caché")

            # Deshabilitar caché para que use GPT normal con detección de interrupción
            usa_segunda_parte_saludo = False

            # FIX 461: BRUCE1381 - NO agregar mensaje aquí
            # procesar_respuesta() ya lo agrega en agente_ventas.py línea 4314
            # Agregar aquí causaba DUPLICACIÓN del mensaje del usuario
            # REMOVIDO:
            # agente.conversation_history.append({
            #     "role": "user",
            #     "content": speech_result
            # })

            # No continuar con caché - dejar que GPT procese con detección de interrupción
        else:
            # Primera vez que cliente responde - usar caché normal
            # Texto de la segunda parte del saludo (pre-generado en cache)
            respuesta_desde_cache = "Me comunico de la marca nioval, más que nada quería brindar informacion de nuestros productos ferreteros, ¿Se encontrara el encargado o encargada de compras?"

            # Agregar la respuesta del cliente al historial
            agente.conversation_history.append({
                "role": "user",
                "content": speech_result
            })

            # Agregar la respuesta de Bruce al historial
            agente.conversation_history.append({
                "role": "assistant",
                "content": respuesta_desde_cache
            })

            # Marcar como respuesta desde caché SOLO si NO fue interrupción
            respuesta_container["respuesta"] = respuesta_desde_cache
            respuesta_container["completado"] = True
            respuesta_container["desde_cache"] = True
            respuesta_container["categoria_cache"] = "segunda_parte_saludo_fix115"

            cache_respuestas_stats["cache_hits"] += 1
            tiempo_cache = time.time() - timestamp_inicio_cache
            print(f" FIX 121: Respuesta instantánea desde caché completada en {tiempo_cache:.3f}s")

    # FIX 97: Preparar contenedor para audio generado en paralelo
    audio_container = {"audio_id": None, "completado": False, "usa_cache": False, "cache_key": None}

    # Solo llamar a GPT si NO hay respuesta en caché
    if not respuesta_desde_cache:
        cache_respuestas_stats["cache_misses"] += 1

        def procesar_gpt_y_audio():
            """FIX 97: Procesar GPT y cuando termine, iniciar audio INMEDIATAMENTE"""
            # 1. Procesar con GPT (3-5s)
            respuesta_container["respuesta"] = agente.procesar_respuesta(speech_result)
            respuesta_container["completado"] = True

            # 2. Apenas GPT termina, detectar si hay caché de audio disponible
            respuesta_texto = respuesta_container["respuesta"]

            # FIX 304: Si respuesta es None (IVR detectado), no procesar audio
            # FIX 506b: BRUCE1489/1495/1503 - Distinguir None (IVR) de "" (pausar)
            # None = IVR real detectado → salir sin audio
            # "" = FIX 477/428 indica pausar → también salir pero sin marcar IVR
            if respuesta_texto is None:
                print(f" FIX 304: respuesta_texto es None (IVR detectado) - saliendo del thread")
                audio_container["audio_id"] = None
                audio_container["completado"] = True
                return  # Salir del thread sin procesar audio

            # FIX 506b: Si respuesta es cadena vacía, pausar sin marcar IVR
            if respuesta_texto == "":
                print(f" FIX 506b: respuesta_texto es '' (pausar/esperar) - saliendo del thread SIN marcar IVR")
                audio_container["audio_id"] = "PAUSAR"  # Valor especial para indicar pausa
                audio_container["completado"] = True
                return  # Salir del thread sin procesar audio

            # Detectar frases comunes para caché de audio
            usa_cache_audio = False
            cache_key_audio = None

            if "Muchas gracias por su tiempo. Que tenga excelente tarde. Hasta pronto" in respuesta_texto:
                cache_key_audio = "despedida_1"
                usa_cache_audio = True
            elif "En las próximas dos horas le llega el catálogo" in respuesta_texto and "Muchas gracias por su tiempo" in respuesta_texto:
                cache_key_audio = "despedida_2"
                usa_cache_audio = True
            elif "Perfecto, ¿con quién tengo el gusto?" in respuesta_texto:
                cache_key_audio = "pregunta_nombre"
                usa_cache_audio = True
            elif "¿Se encuentra el encargado de compras?" in respuesta_texto:
                cache_key_audio = "pregunta_encargado"
                usa_cache_audio = True
            elif "Disculpe, no alcancé a captar" in respuesta_texto:
                cache_key_audio = "no_alcance_captar"
                usa_cache_audio = True

            # 3. Generar audio (si hay caché es instantáneo, si no 2-4s)
            audio_id_temp = f"respuesta_{call_sid}_{len(audio_files)}"

            if usa_cache_audio:
                print(f" FIX 97: Audio cacheado detectado: {cache_key_audio}")
                result = generar_audio_elevenlabs(respuesta_texto, audio_id_temp, usar_cache_key=cache_key_audio)
            else:
                # FIX 98: SIEMPRE usar voz de Bruce (ElevenLabs), sin importar longitud
                palabras = len(respuesta_texto.split())
                print(f" FIX 98: Generando audio con ElevenLabs VOZ BRUCE ({palabras} palabras)")
                result = generar_audio_elevenlabs(respuesta_texto, audio_id_temp)

            # FIX 102: Logging detallado del resultado
            print(f" FIX 102 DEBUG: result = {result}, type = {type(result)}")

            # Guardar resultado en contenedor
            if result is not None:
                audio_container["audio_id"] = audio_id_temp
                audio_container["usa_cache"] = usa_cache_audio
                audio_container["cache_key"] = cache_key_audio
                debug_print(f" FIX 102: Audio container guardado - audio_id={audio_id_temp}")
            else:
                audio_container["audio_id"] = None  # Usar Twilio TTS
                print(f" FIX 102: generar_audio_elevenlabs() retornó None - usará Twilio TTS")

            audio_container["completado"] = True

        # FIX 97: Iniciar procesamiento GPT + audio en thread separado
        gpt_thread = threading.Thread(target=procesar_gpt_y_audio)
        gpt_thread.start()
    else:
        # Crear thread dummy para mantener compatibilidad con código existente
        gpt_thread = threading.Thread(target=lambda: None)
        gpt_thread.start()

    # Crear respuesta TwiML inicial
    response = VoiceResponse()

    # FIX 132/319: Detectar si cliente está desesperado (repite saludos múltiples veces)
    # FIX 319: NO activar "cliente desesperado" en primera respuesta - es normal que repitan saludo
    cliente_desesperado = False
    if len(speech_result.split()) >= 5 and not es_primera_respuesta:
        # Cliente dijo 5+ palabras Y NO es primera respuesta
        speech_lower = speech_result.lower()
        # FIX 319: Solo patrones que indican VERDADERA desesperación (no saludos normales)
        # Los saludos repetidos al inicio son normales, no desesperación
        patrones_desesperacion = [
            "me escuchas", "me escucha", "me oyes", "me oye",
            "está ahí", "estas ahi", "estás ahí", "hay alguien",
            "hola hola", "bueno bueno", "aló aló"  # Repeticiones inmediatas sí son desesperación
        ]

        # Contar cuántos patrones aparecen
        count_patrones = sum(1 for patron in patrones_desesperacion if patron in speech_lower)

        # Si aparecen 1+ patrones de desesperación, cliente está desesperado
        if count_patrones >= 1:
            cliente_desesperado = True
            agente.acaba_de_responder_desesperado = True  # FIX 143: Marcar para no pedir repetición después
            print(f" FIX 132: Cliente desesperado detectado - '{speech_result}'")
            print(f"   Reduciendo timeout de espera a 0s para responder INMEDIATAMENTE")

    # FIX 58/97: Si la respuesta vino del caché, NO esperar ni reproducir "pensando"
    # El caché es instantáneo (0s), no necesita señal auditiva
    if not respuesta_container.get("desde_cache", False):
        # FIX 50/97/102: REDUCIR DELAY - Mientras GPT piensa, reproducir sonido de "pensando"
        # Esto mantiene al cliente en la línea y evita que piense que Bruce colgó

        # FIX 146: Reducir delay para cliente desesperado de 0.5s a 0s (meta: 3s total)
        # FIX 183: Reducir timeout de respuesta - cliente se pone agresivo con delays >3s
        # FIX 319: Reducir aún más el timeout para saludos - clientes cuelgan con delays >4s
        if cliente_desesperado:
            timeout_espera = 0  # FIX 146: Responder INMEDIATAMENTE (0s) - meta 3s total
        elif usa_segunda_parte_saludo:
            timeout_espera = 0  # FIX 319: Saludo con cache = 0s delay (ya tenemos el audio listo)
        elif es_primera_respuesta:
            timeout_espera = 0.3  # FIX 319: Primera respuesta sin cache = 0.3s (antes 0.8s)
        else:
            timeout_espera = 1.5  # FIX 319: Normal 2s→1.5s - clientes impacientes

        debug_print(f" FIX 183: Esperando {timeout_espera}s antes de señal auditiva (máx 2s)")
        gpt_thread.join(timeout=timeout_espera)

    if not respuesta_container["completado"] and not respuesta_container.get("desde_cache", False):
        # GPT+Audio aún procesando - dar señal auditiva

        # FIX 133: Si cliente está desesperado, responder INMEDIATAMENTE y esperar GPT
        # FIX 522: BRUCE1744/1745 - Reducir timeout de 10.5s a 5s total
        if cliente_desesperado:
            print(f" FIX 133: Cliente desesperado - confirmando presencia INMEDIATAMENTE")

            # FIX 522: Esperar a que GPT termine (máximo 2.5s más - reducido de 5s)
            gpt_thread.join(timeout=2.5)

            if not respuesta_container["completado"]:
                # GPT aún no termina - dar confirmación y seguir esperando
                print(f" FIX 133 + FIX 162A + FIX 522: GPT aún procesando - usando audio de relleno")
                # FIX 162A: Usar audio de relleno en lugar de Twilio
                if "un_momento" in audio_cache:
                    audio_url = request.url_root + "audio_cache/un_momento"
                    response.play(audio_url)
                elif "pensando_1" in audio_cache:
                    audio_url = request.url_root + "audio_cache/pensando_1"
                    response.play(audio_url)

                # FIX 522: Esperar otros 2.5s (total 5s máximo - reducido de 10.5s)
                gpt_thread.join(timeout=2.5)

                if not respuesta_container["completado"]:
                    # FIX 522: GPT tardó más de 5s - timeout (antes era 10.5s)
                    print(f" FIX 522: GPT timeout después de 5s (reducido de 10.5s)")
                    response.say("Lo siento, estoy teniendo problemas técnicos. Le llamaré más tarde.", language="es-MX")
                    response.hangup()
                    return Response(str(response), mimetype="text/xml")

            # GPT terminó - continuar con respuesta normal
            print(f" FIX 133: GPT completado - continuando con respuesta")
        else:
            print(f" GPT+Audio procesando - reproduciendo tono de pensando...")
            # FIX 54B: Usar frases variables pre-cacheadas con VOZ DE BRUCE
            # Seleccionar aleatoriamente una de las 8 frases de "pensando"
            # FIX 516 BRUCE1730: Import local para evitar UnboundLocalError
            import random as random_module
            pensando_keys = [f"pensando_{i}" for i in range(1, 9)]
            pensando_key = random_module.choice(pensando_keys)

            # Verificar si existe en caché
            if pensando_key in audio_cache:
                # Reproducir audio pre-generado con voz de Bruce (0s delay)
                audio_url = request.url_root + f"audio_cache/{pensando_key}"
                print(f" Bruce dice (voz Bruce): '{pensando_key}' desde caché")
                response.play(audio_url)
            else:
                # FIX 162A: Si no está en caché, usar cualquier audio de relleno disponible
                print(f" FIX 162A: '{pensando_key}' no en caché, buscando alternativa")
                if "dejeme_ver" in audio_cache:
                    response.play(request.url_root + "audio_cache/dejeme_ver")
                elif "un_momento" in audio_cache:
                    response.play(request.url_root + "audio_cache/un_momento")
                # Si no hay ninguno, continuar sin audio

        # FIX 102 + FIX 522: Esperar otros 3 segundos (total 5s máximo - reducido de 10s)
        # BRUCE1744/1745: Clientes cuelgan cuando GPT tarda >4-5 segundos
        gpt_thread.join(timeout=3.0)

        if not respuesta_container["completado"]:
            # FIX 522: GPT tardó más de 5 segundos total - timeout (antes 10s)
            print(f" FIX 522: GPT timeout después de 5s (reducido de 10s)")
            response.say("Lo siento, estoy teniendo problemas técnicos. Le llamaré más tarde.", language="es-MX")
            response.hangup()
            return Response(str(response), mimetype="text/xml")

    respuesta_agente = respuesta_container["respuesta"]
    tiempo_gpt = time.time() - inicio
    debug_print(f" GPT tardó: {tiempo_gpt:.2f}s")
    print(f" BRUCE DICE: \"{respuesta_agente}\"")

    # FIX 304: Si respuesta es None (IVR detectado), colgar la llamada
    if respuesta_agente is None:
        print(f" FIX 304: respuesta_agente es None (IVR/contestadora detectada) - COLGANDO")
        bruce_id = agente.lead_data.get("bruce_id", "N/A")
        log_evento(f"{bruce_id} - IVR/CONTESTADORA DETECTADA - COLGANDO", "BRUCE")
        agente.lead_data["estado_llamada"] = "IVR"
        agente.lead_data["pregunta_7"] = "IVR/Contestadora automática"
        agente.guardar_llamada_y_lead()
        # FIX 503: Despedirse educadamente antes de colgar (por si no es IVR)
        response.say("Disculpe, parece que entró la contestadora. Le llamaré en otro momento. Que tenga buen día.", language="es-MX")
        response.hangup()
        return Response(str(response), mimetype="text/xml")

    # FIX 498: BRUCE1473 - Si respuesta es cadena vacía = modo espera silencioso
    # NO colgar, solo esperar sin generar audio y seguir escuchando
    if respuesta_agente == "":
        bruce_id = agente.lead_data.get("bruce_id", "N/A")

        # FIX 502: BRUCE1716 - Contador de silencios durante dictado de número
        # Problema: Cliente dicta número en partes, Bruce entra en silencio pero NUNCA confirma
        # Solución: Después de 2 silencios, intentar confirmar el número acumulado
        import re
        from agente_ventas import convertir_numeros_escritos_a_digitos
        if not hasattr(agente, 'silencios_durante_dictado'):
            agente.silencios_durante_dictado = 0
        if not hasattr(agente, 'digitos_acumulados'):
            agente.digitos_acumulados = []

        # Acumular dígitos del speech_result actual (si hay)
        # Primero convertir palabras a dígitos (ej: "veintiuno" → "21")
        texto_convertido = convertir_numeros_escritos_a_digitos(speech_result) if speech_result else ""
        digitos_actuales = re.findall(r'\d', texto_convertido)
        if digitos_actuales:
            agente.digitos_acumulados.extend(digitos_actuales)
            print(f" FIX 502: Acumulando {len(digitos_actuales)} dígitos → Total: {len(agente.digitos_acumulados)}")
            print(f"   Texto original: '{speech_result}' → Convertido: '{texto_convertido}'")

        agente.silencios_durante_dictado += 1
        print(f" FIX 498/502: Respuesta vacía (silencio #{agente.silencios_durante_dictado}) - Continuando sin audio")
        log_evento(f"{bruce_id} - ESPERANDO EN SILENCIO (FIX 498)", "BRUCE")

        # FIX 502: Verificar si debemos confirmar el número acumulado
        total_digitos = len(agente.digitos_acumulados)

        # Si tenemos 10+ dígitos Y 2+ silencios → Confirmar número
        if total_digitos >= 10 and agente.silencios_durante_dictado >= 2:
            numero_completo = ''.join(agente.digitos_acumulados[-10:])  # Últimos 10 dígitos
            print(f"\n FIX 502: NÚMERO COMPLETO DETECTADO después de {agente.silencios_durante_dictado} silencios")
            print(f"   Número: {numero_completo}")

            # Guardar en lead_data
            agente.lead_data["whatsapp"] = numero_completo
            print(f"   WhatsApp guardado: {numero_completo}")

            # Generar confirmación
            respuesta_confirmacion = f"Perfecto, le envío el catálogo al {numero_completo[-4:]}. Muchas gracias por su tiempo, que tenga excelente día."
            audio_id = f"confirmacion_{call_sid}"
            result = generar_audio_elevenlabs(respuesta_confirmacion, audio_id)

            # Resetear contadores
            agente.silencios_durante_dictado = 0
            agente.digitos_acumulados = []

            if result:
                audio_url = request.url_root + f"audio/{audio_id}"
                response.play(audio_url)
            else:
                response.say(respuesta_confirmacion, voice="alice", language="es-MX")

            log_evento(f"{bruce_id} DICE: \"{respuesta_confirmacion}\" (FIX 502: confirmación automática)", "BRUCE")

            # Marcar como despedida y continuar
            agente.lead_data["estado_llamada"] = "Respondio"
            response.record(
                action="/procesar-respuesta",
                method="POST",
                max_length=10,
                timeout=3,
                play_beep=False,
                trim="trim-silence"
            )
            return Response(str(response), mimetype="text/xml")

        # FIX 502: Si llevamos 3+ silencios sin número completo → Pedir que repita
        if agente.silencios_durante_dictado >= 3 and total_digitos > 0 and total_digitos < 10:
            print(f"\n FIX 502: {agente.silencios_durante_dictado} silencios con número incompleto ({total_digitos} dígitos)")
            respuesta_repetir = "Disculpe, ¿me puede repetir el número completo? Creo que no lo escuché bien."
            audio_id = f"repetir_{call_sid}"
            result = generar_audio_elevenlabs(respuesta_repetir, audio_id)

            # Resetear contadores para nuevo intento
            agente.silencios_durante_dictado = 0
            agente.digitos_acumulados = []

            if result:
                audio_url = request.url_root + f"audio/{audio_id}"
                response.play(audio_url)
            else:
                response.say(respuesta_repetir, voice="alice", language="es-MX")

            log_evento(f"{bruce_id} DICE: \"{respuesta_repetir}\" (FIX 502: pedir repetición)", "BRUCE")

            response.record(
                action="/procesar-respuesta",
                method="POST",
                max_length=30,
                timeout=5,
                play_beep=False,
                trim="trim-silence"
            )
            return Response(str(response), mimetype="text/xml")

        # FIX 503: Corregir ruta - usar /procesar-respuesta con Record
        response.record(
            action="/procesar-respuesta",
            method="POST",
            max_length=30,
            timeout=3,
            play_beep=False,
            trim="trim-silence"
        )
        return Response(str(response), mimetype="text/xml")

    # FIX 502: Resetear contadores de silencio cuando Bruce da respuesta normal
    # Esto evita acumulación incorrecta entre diferentes contextos de dictado
    if hasattr(agente, 'silencios_durante_dictado'):
        agente.silencios_durante_dictado = 0
    if hasattr(agente, 'digitos_acumulados'):
        agente.digitos_acumulados = []

    # FIX 208/284: Registrar en buffer de logs (sin duplicar prefijo BRUCE)
    bruce_id = agente.lead_data.get("bruce_id", "N/A")
    log_evento(f"{bruce_id} DICE: \"{respuesta_agente}\"", "BRUCE")

    # FIX 75/76: VERIFICAR SI DEBE COLGAR INMEDIATAMENTE (objeción terminal detectada)
    if agente.lead_data["estado_llamada"] == "Colgo":
        print(f" FIX 75: Estado 'Colgo' detectado - Terminando llamada después de despedida")
        print(f"   Razón: {agente.lead_data.get('pregunta_7', 'Objeción terminal')}")

        # FIX 76: Generar audio con voz de Bruce (ElevenLabs) usando caché
        audio_id_despedida = f"respuesta_{call_sid}_objecion_final"
        cache_key_despedida = "despedida_objecion"  # Caché para "Entiendo perfectamente. Muchas gracias..."

        # Intentar usar caché, si no existe generar con ElevenLabs
        result_despedida = generar_audio_elevenlabs(respuesta_agente, audio_id_despedida, usar_cache_key=cache_key_despedida)

        if result_despedida is not None:
            # Audio generado con ElevenLabs (voz Bruce)
            audio_url_despedida = request.url_root + f"audio/{audio_id_despedida}"
            print(f" FIX 76: Usando voz Bruce (ElevenLabs) para despedida de objeción")
            response.play(audio_url_despedida)
        else:
            # FIX 162A: ElevenLabs falló - usar despedida simple pre-cacheada
            print(f" FIX 162A: ElevenLabs FALLÓ en despedida - usando caché de despedida simple")
            print(f"   Despedida que falló: {respuesta_agente[:100]}...")
            print(f"   Call SID: {call_sid}")
            # Usar despedida simple del caché
            if "despedida_simple" in audio_cache:
                response.play(request.url_root + "audio_cache/despedida_simple")
            # Si no hay despedida en caché, colgar sin audio (mejor que cambiar voz)

        # FIX 76: Agregar pausa de 1 segundo antes de colgar (evita sensación agresiva)
        response.pause(length=1)
        response.hangup()

        # Guardar lead INMEDIATAMENTE
        agente.guardar_llamada_y_lead()

        return Response(str(response), mimetype="text/xml")

    # FIX 57: Registrar pregunta-respuesta para auto-aprendizaje de caché
    # Solo registrar si NO vino del caché (las cacheadas ya están optimizadas)
    if not respuesta_container.get("desde_cache", False):
        registrar_pregunta_respuesta(speech_result, respuesta_agente)

    # FIX 119: Si usamos caché de segunda parte del saludo, usar audio pre-generado
    # VERIFICAR ESTO ANTES de esperar (0s delay total)
    if usa_segunda_parte_saludo and "segunda_parte_saludo" in audio_cache:
        # Usar audio pre-generado de la segunda parte (0s delay total)
        audio_id = f"segunda_parte_saludo_{call_sid}"
        audio_files[audio_id] = audio_cache["segunda_parte_saludo"]
        usa_cache = True
        cache_key = "segunda_parte_saludo"
        audio_container["audio_id"] = audio_id
        audio_container["usa_cache"] = True
        audio_container["cache_key"] = cache_key
        audio_container["completado"] = True
        print(f" FIX 119: Audio de segunda_parte_saludo desde caché (0s delay, sin espera)")
    else:
        # FIX 165: Timeout dinámico según longitud del mensaje
        # Mensajes largos necesitan más tiempo para generar audio
        if not audio_container.get("completado", False):
            import time

            # FIX 165 + FIX 203: Calcular timeout según palabras (ajustado para Multilingual v2)
            palabras = len(respuesta_agente.split())
            # FIX 203: Fórmula actualizada basada en benchmarks reales de Multilingual v2:
            # - 10 palabras: ~2s → timeout 5s (mínimo)
            # - 20 palabras: ~4s → timeout 6s
            # - 30 palabras: ~6s → timeout 8s
            # - 40 palabras: ~8s → timeout 10s
            # - 50 palabras: ~10s → timeout 12s
            # Fórmula: 0.2s por palabra + 2s buffer, mínimo 5s, máximo 15s
            timeout_calculado = (palabras * 0.2) + 2.0
            max_wait = max(5.0, min(timeout_calculado, 15.0))

            print(f" FIX 165 + FIX 203: Esperando audio ({palabras} palabras, timeout={max_wait:.1f}s)...")
            waited = 0
            while not audio_container.get("completado", False) and waited < max_wait:
                time.sleep(0.1)
                waited += 0.1

            if audio_container.get("completado", False):
                debug_print(f" FIX 165: Audio completado después de {waited:.1f}s")
            else:
                print(f" FIX 165: Audio NO completó después de {max_wait:.1f}s - usará audio de relleno")

        # FIX 97: Usar audio ya generado en paralelo (o None si debe usar Twilio TTS)
        # El thread ya generó el audio mientras esperábamos, así que está listo AHORA
        audio_id = audio_container.get("audio_id")
        usa_cache = audio_container.get("usa_cache", False)
        cache_key = audio_container.get("cache_key")

    tiempo_total = time.time() - inicio
    debug_print(f" TOTAL delay (GPT + Audio en paralelo): {tiempo_total:.2f}s")

    if audio_id:
        if usa_cache:
            print(f" FIX 97: Audio desde caché: {cache_key} (generado en paralelo)")
        else:
            print(f" FIX 97: Audio ElevenLabs (generado en paralelo)")
    else:
        print(f" FIX 97: Usar Twilio TTS (respuesta larga o error)")

    # Registrar mensaje de Bruce en LOGS (con info de cache)
    if logs_manager and agente.bruce_id:
        # FIX 97: Determinar si vino del caché basado en tiempo total
        desde_cache = usa_cache or (tiempo_total < 3.0)  # Caché si <3s total
        nombre_tienda = agente.lead_data.get('nombre_negocio', '')
        logs_manager.registrar_mensaje_bruce(
            agente.bruce_id,
            respuesta_agente,
            desde_cache=desde_cache,
            cache_key=cache_key,
            tiempo_generacion=tiempo_total if not desde_cache else None,
            nombre_tienda=nombre_tienda
        )

    # Verificar si debe terminar (solo si Bruce se despide explícitamente)
    # IMPORTANTE: Usar frases distintivas que solo aparecen en despedidas
    debe_terminar = False

    # Despedidas explícitas de Bruce (frases distintivas)
    despedidas_bruce = [
        "gracias por su tiempo",
        "hasta pronto",
        "hasta luego",
        "que tenga excelente",  # Captura: "que tenga excelente tarde/día"
        "que tengas excelente", # Captura: "que tengas excelente tarde/día"
        "que tenga un excelente",  # Captura: "que tenga un excelente día"
        "que tengas un excelente", # Captura: "que tengas un excelente día"
        "que le vaya bien"
    ]

    respuesta_lower = respuesta_agente.lower()
    debe_terminar = any(despedida in respuesta_lower for despedida in despedidas_bruce)

    if debe_terminar:
        print(f" Detectada despedida en: {respuesta_agente[:50]}...")

        # FIX 158: Marcar que Bruce se despidió primero
        agente.bruce_se_despidio = True

        # IMPORTANTE: Esperar respuesta del cliente por educación antes de colgar
        print(f" Esperando despedida del cliente por cortesía...")

        # FIX 214: Usar Record en lugar de Gather para despedida (ahorra costos Speech Recognition)
        # Reproducir audio primero
        if audio_id is None:
            # FIX 162A: ElevenLabs falló - usar despedida simple pre-cacheada
            print(f" FIX 162A: ElevenLabs FALLÓ en despedida - usando caché de despedida")
            print(f"   Despedida que falló: {respuesta_agente[:100]}...")
            print(f"   Call SID: {call_sid}")
            if "despedida_simple" in audio_cache:
                response.play(request.url_root + "audio_cache/despedida_simple")
        else:
            audio_url = request.url_root + f"audio/{audio_id}"
            response.play(audio_url)

        # FIX 214/215: Record corto para escuchar despedida del cliente
        response.record(
            action="/despedida-final",
            method="POST",
            max_length=5,  # Máximo 5 segundos para despedida
            timeout=2,  # FIX 215: Reducido de 3s a 2s
            play_beep=False,
            trim="trim-silence"
        )

        # Si no responde en 3 segundos, terminar igual
        response.hangup()

        return str(response)

    # FIX 96/112/116: Si NO es despedida, continuar conversación normal
    # IMPORTANTE: Preparar Gather PRIMERO, luego reproducir audio DENTRO del Gather
    # FIX 60/61/62/63/86/112: Usando Whisper API (mejor precisión + más barato)

    # FIX 124: Timeouts ajustados según tipo de mensaje y posición en conversación

    # Detectar si Bruce acaba de pedir correo
    keywords_pide_correo = [
        "correo", "email", "e-mail", "dirección electrónica",
        "deletrear", "letra por letra", "¿cuál es el correo",
        "proporcionar.*correo", "pasar.*correo"
    ]

    # FIX 292/293: Detectar si Bruce acaba de pedir número de WhatsApp/teléfono
    keywords_pide_numero = [
        "whatsapp", "número de whatsapp", "numero de whatsapp",
        "cuál es su número", "cual es su numero", "me puede dar su número", "me puede dar su numero",
        "proporcionarme su número", "proporcionarme su numero", "confirmar el número", "confirmar el numero",
        "repetir el número", "repetir el numero", "número completo", "numero completo"
    ]

    # Revisar último mensaje de Bruce
    ultimo_mensaje_bruce = None
    for msg in reversed(agente.conversation_history):
        if msg['role'] == 'assistant':
            ultimo_mensaje_bruce = msg['content'].lower()
            break

    # FIX 124: Detectar si es el segundo mensaje (después del saludo inicial)
    num_mensajes_bruce = len([msg for msg in agente.conversation_history if msg['role'] == 'assistant'])
    es_segundo_mensaje = num_mensajes_bruce == 2  # "Me comunico de la marca nioval..."

    # FIX 126: Detectar si cliente pidió "un momento" en su último mensaje
    ultimo_mensaje_cliente = None
    mensajes_cliente = [msg for msg in agente.conversation_history if msg['role'] == 'user']
    if mensajes_cliente:
        ultimo_mensaje_cliente = mensajes_cliente[-1]['content'].lower()

    cliente_pidio_momento = False
    if ultimo_mensaje_cliente:
        # FIX 130: Lista ampliada con todas las variantes de "esperar"
        frases_espera = [
            # "Un momento" y variantes
            "un momento", "un momentito", "un minuto", "un minutito", "un segundo", "un segundito",
            "dame un momento", "dame un minuto", "dame un segundo", "deme un momento", "deme un minuto", "deme un segundo",

            # "Espere/Espera" y variantes
            "espere", "espéreme", "espera", "espérame", "esperame",
            "aguarda", "aguarde", "aguárdame", "aguárdeme",

            # "Permítame/Déjame" y variantes
            "permítame", "permíteme", "permitame", "permiteme",
            "déjame", "déjeme", "dejame", "dejeme",

            # Cliente ocupado
            "ahorita le marco", "le marco", "le hablo", "ahorita le hablo",
            "en un momento", "en un rato", "más tarde", "después te llamo",
            "luego te marco", "luego le marco", "te llamo luego", "le llamo luego",

            # Indirectas de ocupado (cliente ocupado AHORA pero puede atender después)
            "está ocupado", "no puede en este momento", "no puede ahorita",
            "está en junta", "está en una junta",
            "está con un cliente", "ahorita está ocupado"
            # FIX 216: REMOVIDO "no está disponible" - eso es rechazo, no espera
        ]
        cliente_pidio_momento = any(frase in ultimo_mensaje_cliente for frase in frases_espera)

    # FIX 155: Detectar si cliente está DICTANDO correo (no solo pensando)
    cliente_dictando_correo = False
    if ultimo_mensaje_cliente:
        indicadores_dictado_correo = [
            "se lo paso", "le paso", "es ", "arroba", "@", "punto com", ".com",
            "gmail", "hotmail", "outlook", "yahoo", "guión", "-", "underscore", "_"
        ]
        cliente_dictando_correo = any(ind in ultimo_mensaje_cliente.lower() for ind in indicadores_dictado_correo)

    # FIX 293: Detectar si cliente está DICTANDO número de teléfono
    cliente_dictando_numero = False
    bruce_pidio_numero = False
    if ultimo_mensaje_bruce:
        bruce_pidio_numero = any(keyword in ultimo_mensaje_bruce for keyword in keywords_pide_numero)

    if ultimo_mensaje_cliente:
        # Detectar patrones de números dictados (dígitos, pares de números)
        import re
        texto_cliente = ultimo_mensaje_cliente.lower()
        # Buscar si hay dígitos o palabras numéricas
        tiene_digitos = bool(re.search(r'\d', texto_cliente))
        # FIX 340: Contar cuántos dígitos hay para saber si está dictando
        num_digitos = len(re.findall(r'\d', texto_cliente))
        tiene_numeros_palabra = any(num in texto_cliente for num in [
            'cero', 'uno', 'dos', 'tres', 'cuatro', 'cinco', 'seis', 'siete', 'ocho', 'nueve', 'diez',
            'once', 'doce', 'trece', 'catorce', 'quince', 'veinte', 'treinta', 'cuarenta', 'cincuenta',
            'sesenta', 'setenta', 'ochenta', 'noventa'
        ])

        # FIX 340: Detectar si cliente OFRECE dar número (aunque Bruce no haya pedido explícitamente)
        cliente_ofrece_numero = any(frase in texto_cliente for frase in [
            'le doy el número', 'le doy el numero', 'te doy el número', 'te doy el numero',
            'es el', 'sería', 'seria', 'anota', 'apunta', 'el número es', 'el numero es'
        ])

        # Si Bruce pidió número O cliente ofrece número Y hay dígitos/números, es dictado
        if (bruce_pidio_numero or cliente_ofrece_numero) and (tiene_digitos or tiene_numeros_palabra):
            cliente_dictando_numero = True
            debug_print(f" FIX 293/340: Cliente dictando número de teléfono ({num_digitos} dígitos detectados)")

        # FIX 340: Si hay 3+ dígitos en el mensaje, SIEMPRE considerar como dictado
        # Esto evita interrumpir cuando cliente está a mitad de dictar
        if num_digitos >= 3:
            cliente_dictando_numero = True
            debug_print(f" FIX 340: Forzando modo dictado - {num_digitos} dígitos detectados - NO INTERRUMPIR")

    # FIX 215: Reducir todos los timeouts para respuesta más rápida
    # Record timeout = silencio después de que cliente termina de hablar
    if cliente_pidio_momento:
        timeout_gather = 5  # FIX 215: Reducido de 10s a 5s
        debug_print(f" FIX 215: Timeout={timeout_gather}s (cliente pidió esperar)")
    elif cliente_dictando_correo:
        timeout_gather = 8  # FIX 215: Reducido de 15s a 8s (correo largo)
        debug_print(f" FIX 215: Timeout={timeout_gather}s (cliente dictando correo)")
    elif cliente_dictando_numero or bruce_pidio_numero:
        # FIX 293/340: Dar MÁS tiempo cuando cliente dicta número de teléfono (10 dígitos)
        # FIX 340: Aumentado de 6s a 8s para evitar interrupciones mientras dictan
        timeout_gather = 8  # 8 segundos para que diga los 10 dígitos sin prisa
        debug_print(f" FIX 293/340: Timeout={timeout_gather}s (cliente dictando número - NO INTERRUMPIR)")
    elif cliente_desesperado:
        timeout_gather = 2  # FIX 215: Reducido de 5s a 2s (respuesta rápida)
        debug_print(f" FIX 215: Timeout={timeout_gather}s (cliente desesperado)")
    elif ultimo_mensaje_bruce and any(keyword in ultimo_mensaje_bruce for keyword in keywords_pide_correo):
        timeout_gather = 3  # FIX 215: Reducido de 4s a 3s
        debug_print(f" FIX 215: Timeout={timeout_gather}s (pedir correo/WhatsApp)")
    elif es_segundo_mensaje:
        timeout_gather = 2  # FIX 215: Reducido de 3s a 2s
        debug_print(f" FIX 215: Timeout={timeout_gather}s (segundo mensaje)")
    else:
        timeout_gather = 2  # FIX 215: Reducido de 4s a 2s (conversación normal)
        debug_print(f" FIX 215: Timeout={timeout_gather}s (conversación normal)")

    # FIX 125/154/156/157/194: Manejo inteligente de interrupciones
    # FIX 157: barge_in=False para evitar ciclo de saludos
    # FIX 194: Habilitar barge_in progresivamente para detectar confusión del cliente
    # FIX 196: REDUCIR umbral de #8 a #5 - detectar objeciones ANTES de despedida
    #
    # Problema original (FIX 125): Cliente dice "Sí dígame" mientras Bruce habla, no se detecta → silencio 14s
    # Problema FIX 157: Cliente confundido dice "¿Hola?" y Bruce no responde → siente abandono
    # Problema FIX 196: Cliente dice "pero" en mensaje #6-7 y Bruce NO lo detecta (barge_in=False)
    # Solución FIX 196: barge_in=True desde mensaje #5 (permite detectar objeciones como "pero" ANTES de despedida)

    if num_mensajes_bruce <= 2:
        # Primeros 2 mensajes: NO permitir (evitar ciclo FIX 157)
        permitir_interrupcion = False
        debug_print(f" FIX 194: barge_in=False (saludo inicial, evitar ciclo)")
    elif num_mensajes_bruce >= 5:
        # FIX 196: Desde mensaje #5: Permitir para detectar objeciones Y confusión
        permitir_interrupcion = True
        debug_print(f" FIX 196: barge_in=True (mensaje #{num_mensajes_bruce}, detectar objeciones/confusión)")
    else:
        # Mensajes 3-4: NO permitir (conversación fluida temprana)
        permitir_interrupcion = False
        debug_print(f" FIX 194: barge_in=False (conversación fluida)")

    # FIX 214: Usar Record en lugar de Gather para ELIMINAR COSTOS de Twilio Speech Recognition
    # Deepgram transcribe en tiempo real vía MediaStream, Record solo captura audio
    print(f" FIX 214: Usando Record + Deepgram (mensaje #{num_mensajes_bruce})")

    # FIX 141: Si cliente está desesperado, reproducir confirmación ANTES de respuesta
    if cliente_desesperado:
        print(f" FIX 141: Agregando confirmación (cliente desesperado)")

        audio_id_confirmacion = f"confirmacion_desesperado_{call_sid}"
        result_confirmacion = generar_audio_elevenlabs(
            "Sí, estoy aquí.",
            audio_id_confirmacion,
            usar_cache_key="confirmacion_presencia"
        )

        if result_confirmacion:
            audio_url_confirmacion = request.url_root + f"audio/{audio_id_confirmacion}"
            print(f" FIX 141: Confirmación generada")
            response.play(audio_url_confirmacion)
        else:
            print(f" FIX 162A: Caché falló - usando audio de relleno")
            if "pensando_1" in audio_cache:
                response.play(request.url_root + "audio_cache/pensando_1")

    # FIX 455: Caso BRUCE1363 - Limpiar transcripciones acumuladas ANTES de reproducir audio
    # Problema: Cliente dice "Ahorita no, jefe" DURANTE audio de Bruce
    # Esa transcripción se acumula y cuando llega /procesar-respuesta después del audio,
    # el sistema procesa un "¿Bueno?" viejo en lugar del mensaje actual
    # Solución: Limpiar buffer ANTES de enviar audio para que solo capture la RESPUESTA al audio
    import time as time_455  # FIX 455: Import local seguro
    import re as re_481  # FIX 481: Para detectar dígitos
    transcripciones_previas = deepgram_transcripciones.get(call_sid, [])

    # FIX 481: BRUCE1446/BRUCE1458 - NO descartar transcripciones importantes
    # Verificar si alguna transcripción contiene información importante que NO debe descartarse
    transcripciones_importantes = []
    transcripciones_descartar = []

    dias_semana_481 = ['lunes', 'martes', 'miércoles', 'miercoles', 'jueves', 'viernes', 'sábado', 'sabado', 'domingo']
    patrones_dia_481 = ['marcar el', 'marque el', 'llame el', 'si gusta marcar', 'hasta el', 'se presenta']

    for trans in transcripciones_previas:
        trans_lower = trans.lower() if isinstance(trans, str) else str(trans).lower()

        # FIX 481: Preservar si menciona día de la semana con contexto de callback
        contiene_dia_callback = any(
            patron in trans_lower and any(dia in trans_lower for dia in dias_semana_481)
            for patron in patrones_dia_481
        )

        # FIX 481: Preservar si contiene dígitos que parecen número telefónico (3+ dígitos)
        # Excluir horas como "a las 2", "las 10"
        digitos = re_481.findall(r'\d', trans_lower)
        contiene_telefono = len(digitos) >= 3 and not any(h in trans_lower for h in ['a las', 'las dos', 'las tres', 'las diez', 'las once', 'las doce'])

        # FIX 486: BRUCE1466 - Preservar frases de "interrupción válida"
        # Cliente dice "déjeme validar", "un momento", "espere" mientras Bruce procesa
        frases_interrupcion_valida = [
            'déjeme', 'dejeme', 'déjame', 'dejame',
            'validar', 'valido', 'checo', 'verifico',
            'un momento', 'espera', 'espere', 'espérame', 'esperame',
            'permíteme', 'permiteme', 'permítame', 'permitame',
            'voy a', 'deja ver', 'déjame ver', 'dejame ver',
            'voy a preguntar', 'lo checo', 'lo verifico',
            'deja consulto', 'deja pregunto', 'consulto',
            'lo consulto', 'pregunto', 'lo pregunto',
            'a ver', 'mmmm', 'mmm', 'ehh', 'ehhh'
        ]
        contiene_interrupcion_valida = any(frase in trans_lower for frase in frases_interrupcion_valida)

        if contiene_dia_callback or contiene_telefono or contiene_interrupcion_valida:
            transcripciones_importantes.append(trans)
            if contiene_interrupcion_valida:
                print(f" FIX 486: Preservando INTERRUPCIÓN VÁLIDA: '{trans}'")
            else:
                print(f" FIX 481: Preservando transcripción importante: '{trans}'")
        else:
            transcripciones_descartar.append(trans)

    if transcripciones_descartar:
        print(f" FIX 455: Limpiando {len(transcripciones_descartar)} transcripciones acumuladas ANTES de enviar audio")
        print(f"   Contenido descartado: {transcripciones_descartar}")

    # Solo conservar las transcripciones importantes
    deepgram_transcripciones[call_sid] = transcripciones_importantes

    if transcripciones_importantes:
        print(f" FIX 481: Conservando {len(transcripciones_importantes)} transcripciones importantes")

    # Limpiar el tracking de FINAL/PARCIAL si no hay transcripciones importantes
    if not transcripciones_importantes and call_sid in deepgram_ultima_final:
        deepgram_ultima_final[call_sid] = {}

    # Guardar timestamp de cuando Bruce envía audio (para referencia en logs)
    bruce_audio_enviado_timestamp[call_sid] = time_455.time()

    # FIX 96/98: Reproducir audio SIEMPRE con voz de Bruce (ElevenLabs)
    if audio_id is None:
        print(f" FIX 162A: ElevenLabs FALLÓ - usando audio de relleno")
        print(f"   Respuesta que falló: {respuesta_agente[:100]}...")
        print(f"   Call SID: {call_sid}")

        if "dejeme_ver" in audio_cache:
            print(f" FIX 162A: Usando audio de relleno 'dejeme_ver'")
            response.play(request.url_root + "audio_cache/dejeme_ver")
        elif "un_momento" in audio_cache:
            print(f" FIX 162A: Usando audio de relleno 'un_momento'")
            response.play(request.url_root + "audio_cache/un_momento")
    else:
        audio_url = request.url_root + f"audio/{audio_id}"
        response.play(audio_url)

    # FIX 214/223: Record para capturar respuesta del cliente
    # FIX 223: max_length reducido para evitar delays
    response.record(
        action="/procesar-respuesta",
        method="POST",
        max_length=1,  # FIX 223: Reducido de 30s a 10s máximo
        timeout=timeout_gather,  # FIX 116: Timeout progresivo según num_mensajes
        play_beep=False,
        trim="trim-silence"
    )

    return Response(str(response), mimetype="text/xml")


@app.route("/despedida-final", methods=["GET", "POST"])
def despedida_final():
    """
    Endpoint para manejar la despedida del cliente después de que Bruce se despidió.
    Por cortesía, esperamos a que el cliente se despida antes de colgar.
    """
    # Obtener parámetros de Twilio
    if request.method == "GET":
        call_sid = request.args.get("CallSid")
        cliente_respuesta = request.args.get("SpeechResult", "")
    else:
        call_sid = request.form.get("CallSid")
        cliente_respuesta = request.form.get("SpeechResult", "")

    print(f"\n DESPEDIDA FINAL - Call SID: {call_sid}")
    if cliente_respuesta:
        print(f" CLIENTE SE DESPIDE: \"{cliente_respuesta}\"")
    else:
        print(f" Cliente no respondió despedida (silencio)")

    # Obtener agente de la conversación activa
    agente = conversaciones_activas.get(call_sid)

    # ADDED - Registrar despedida del cliente en LOGS
    if logs_manager and cliente_respuesta and agente and agente.bruce_id:
        nombre_tienda = agente.lead_data.get('nombre_negocio', '')
        logs_manager.registrar_mensaje_cliente(agente.bruce_id, cliente_respuesta, nombre_tienda)

    # Guardar lead y llamada en Google Sheets
    if agente:
        print(f" Guardando llamada {call_sid} en Google Sheets...")
        try:
            agente.guardar_llamada_y_lead()
            print(f" Llamada {call_sid} guardada correctamente")

            # Manejo post-guardado: Buzón y Reprogramación
            if sheets_manager and agente.contacto_info:
                fila = agente.contacto_info.get('fila') or agente.contacto_info.get('ID')

                # 1. Manejo de BUZÓN/OPERADORA - Marcar intentos y reintentar
                # FIX 109: Incluir Operadora en sistema de reintentos
                estado = agente.lead_data.get("estado_llamada")
                if estado in ["Buzon", "Operadora"] and fila:
                    tipo_deteccion = "buzón" if estado == "Buzon" else "operadora"
                    print(f"\n Llamada cayó en {tipo_deteccion} - manejando reintento...")
                    intentos = sheets_manager.marcar_intento_buzon(fila)

                    # FIX 179: Verificar si los reintentos están deshabilitados
                    deshabilitar_reintentos = agente.contacto_info.get('deshabilitar_reintentos', False)

                    if intentos == 1 and not deshabilitar_reintentos:
                        # PRIMER intento de buzón/operadora - REINTENTO INMEDIATO
                        print(f" Primer intento de {tipo_deteccion} - iniciando reintento inmediato...")
                        print(f" Esperando 30 segundos antes de reintentar...")

                        # Capturar url_root ANTES del thread (Flask context)
                        base_url = request.url_root.replace('http://', 'https://')

                        def hacer_reintento():
                            import time
                            import requests
                            time.sleep(30)  # Esperar 30 segundos

                            telefono_destino = agente.contacto_info.get('telefono')
                            nombre_negocio = agente.contacto_info.get('nombre_negocio', 'cliente')

                            print(f" Iniciando segundo intento a {telefono_destino}...")

                            try:
                                response_call = requests.post(
                                    f"{base_url}iniciar-llamada",
                                    json={
                                        "telefono": telefono_destino,
                                        "nombre_negocio": nombre_negocio,
                                        "contacto_info": agente.contacto_info
                                    },
                                    timeout=10
                                )

                                if response_call.status_code == 200:
                                    print(f" Segundo intento iniciado correctamente")
                                else:
                                    print(f" Error en reintento: {response_call.status_code}")

                            except Exception as e:
                                print(f" Error iniciando reintento: {e}")

                        # Ejecutar reintento en background
                        import threading
                        thread = threading.Thread(target=hacer_reintento)
                        thread.daemon = True
                        thread.start()

                    elif intentos == 1 and deshabilitar_reintentos:
                        # FIX 179: Reintentos deshabilitados (llamadas masivas)
                        print(f" FIX 179: Primer intento de {tipo_deteccion} pero reintentos DESHABILITADOS (llamadas masivas)")
                    else:
                        print(f" Intento de buzón #{intentos} - no se hará reintento automático")

                # 2. Manejo de REFERENCIAS - Llamar automáticamente al referido
                telefono_referencia = agente.lead_data.get("referencia_telefono")
                if telefono_referencia and fila:
                    print(f"\n Procesando referencia...")
                    nombre_ref = agente.lead_data.get("referencia_nombre", "")
                    print(f"     Nombre del referido: {nombre_ref}")
                    print(f"     Teléfono del referido: {telefono_referencia}")

                    # Buscar el contacto referido en la lista
                    contacto_referido = sheets_manager.buscar_contacto_referido(telefono_referencia)

                    if contacto_referido:
                        fila_referido = contacto_referido.get('fila')
                        nombre_negocio_ref = contacto_referido.get('nombre_negocio', nombre_ref)

                        # Guardar la referencia en columna U del contacto referido
                        nombre_negocio_origen = agente.contacto_info.get('nombre_negocio', 'Desconocido')
                        telefono_origen = agente.contacto_info.get('telefono', '')

                        contexto_referencia = f"Referencia de: {nombre_negocio_origen} ({telefono_origen})"
                        if nombre_ref:
                            contexto_referencia += f" - Contacto: {nombre_ref}"

                        # Obtener último mensaje del cliente para contexto
                        ultimo_mensaje_cliente = ""
                        for msg in reversed(agente.conversation_history):
                            if msg.get('role') == 'user':
                                ultimo_mensaje_cliente = msg.get('content', '')
                                break

                        if ultimo_mensaje_cliente:
                            contexto_referencia += f" - Comentó: {ultimo_mensaje_cliente[:100]}"

                        fecha_hora = agente.lead_data.get("fecha_inicio", "")
                        referencia_completa = f"NUM:{telefono_referencia}|Ref: {nombre_negocio_origen} ({telefono_origen}) - {fecha_hora[:10]} - {ultimo_mensaje_cliente[:50]}"

                        sheets_manager.guardar_referencia(fila_referido, referencia_completa)
                        print(f" Referencia guardada en fila {fila_referido} (columna U)")

                        # Guardar contexto de reprogramación en el contacto ACTUAL (quien dio la referencia)
                        contexto_reprog = f"Reprog: Referencia dada | Pasó contacto de {nombre_ref or 'encargado'} ({telefono_referencia})"
                        sheets_manager.guardar_contexto_reprogramacion(fila, contexto_reprog)
                        print(f" Contexto de referencia guardado en fila {fila} (columna W)")

                        # Iniciar llamada automática al referido
                        print(f"\n Iniciando llamada automática al referido...")
                        print(f"      Enviando solicitud a {base_url}iniciar-llamada")
                        print(f"      Teléfono: {telefono_referencia}")
                        print(f"      Fila: {fila_referido}")

                        try:
                            import requests
                            response_ref = requests.post(
                                f"{base_url}iniciar-llamada",
                                json={
                                    "telefono": telefono_referencia,
                                    "nombre_negocio": nombre_negocio_ref,
                                    "contacto_info": contacto_referido
                                },
                                timeout=10
                            )

                            if response_ref.status_code == 200:
                                result = response_ref.json()
                                print(f"      Llamada iniciada exitosamente!")
                                print(f"      Call SID: {result.get('call_sid', 'N/A')}")
                            else:
                                print(f"      Error en llamada automática: {response_ref.status_code}")

                        except Exception as e:
                            print(f"      Error iniciando llamada automática: {e}")

                # 3. Marcar llamada en columna U (registro de contacto)
                # No bloquear llamadas futuras - columnas U/V/W son solo para contexto
                telefono_actual = agente.lead_data.get("telefono", "")
                if telefono_actual and fila:
                    telefono_llamado = agente.contacto_info.get('telefono', telefono_actual)

                    # Verificar si ya fue llamado antes (para el mensaje de log)
                    es_primera = not sheets_manager.verificar_contacto_ya_llamado(fila)

                    sheets_manager.marcar_primera_llamada(fila, numero_llamado=telefono_llamado)

                    if es_primera:
                        print(f" Primera llamada registrada en columna U con número: {telefono_llamado}")
                    else:
                        print(f" Llamada subsecuente registrada en columna U con número: {telefono_llamado}")

        except Exception as e:
            print(f" Error guardando llamada {call_sid}: {e}")
            import traceback
            traceback.print_exc()

        # FIX 489: Limpiar TODOS los recursos (prevenir memory leak)
        limpiar_recursos_llamada(call_sid)

    # Crear respuesta TwiML para colgar
    response = VoiceResponse()
    response.hangup()

    return Response(str(response), mimetype="text/xml")


@app.route("/llamadas-masivas", methods=["POST"])
def llamadas_masivas():
    """
    Inicia llamadas masivas desde una lista
    
    Body JSON:
    {
        "lista_telefonos": [
            {"telefono": "+52XXXXXXXXXX", "nombre": "Ferretería 1"},
            {"telefono": "+52YYYYYYYYYY", "nombre": "Ferretería 2"}
        ],
        "delay_segundos": 30
    }
    """
    data = request.json
    lista = data.get("lista_telefonos", [])
    delay = data.get("delay_segundos", 30)
    
    resultados = []
    
    for contacto in lista:
        try:
            call = twilio_client.calls.create(
                to=contacto["telefono"],
                from_=TWILIO_PHONE_NUMBER,
                url=request.url_root + "webhook-voz",
                method="POST"
                # FIX 271: Removido record=True - ahora usamos <Start><Recording> en TwiML
            )

            resultados.append({
                "telefono": contacto["telefono"],
                "nombre": contacto.get("nombre"),
                "call_sid": call.sid,
                "status": "iniciada"
            })
            
            # Esperar entre llamadas
            import time
            time.sleep(delay)
            
        except Exception as e:
            resultados.append({
                "telefono": contacto["telefono"],
                "error": str(e),
                "status": "fallida"
            })
    
    return {"resultados": resultados}


@app.route("/status-callback", methods=["GET", "POST"])
def status_callback():
    """
    Webhook que Twilio llama cuando cambia el estado de una llamada
    Se usa para detectar cuando el cliente cuelga o entra buzón
    """
    # Twilio puede enviar GET o POST
    if request.method == "GET":
        call_sid = request.args.get("CallSid")
        call_status = request.args.get("CallStatus")
        call_duration = request.args.get("CallDuration")
        answered_by = request.args.get("AnsweredBy", "")
    else:
        call_sid = request.form.get("CallSid")
        call_status = request.form.get("CallStatus")
        call_duration = request.form.get("CallDuration")
        answered_by = request.form.get("AnsweredBy", "")

    print(f"\n STATUS CALLBACK - Llamada {call_sid[:10]}...")
    print(f"   Estado: {call_status}")
    print(f"   Duración: {call_duration}s")
    if answered_by:
        print(f"   AnsweredBy: {answered_by}")

    # FIX 208: Registrar fin de llamada
    log_evento(f"LLAMADA TERMINADA - Estado: {call_status}, Duración: {call_duration}s", "LLAMADA")

    # NUEVO: Manejo de buzón detectado por Twilio - REINTENTO INMEDIATO
    # Detectar buzón por AnsweredBy O por call_status="no-answer"
    es_buzon = (
        answered_by in ["machine_start", "machine_end_beep", "machine_end_silence", "machine_end_other"] or
        call_status == "no-answer"
    )

    if es_buzon:
        if answered_by:
            print(f"    Buzón detectado por AnsweredBy: {answered_by}")
        else:
            print(f"    Buzón detectado por CallStatus: {call_status} (no-answer)")

        # Obtener info del contacto (puede estar en conversaciones_activas o contactos_llamadas)
        contacto_info = None
        if call_sid in conversaciones_activas:
            contacto_info = conversaciones_activas[call_sid].contacto_info
        elif call_sid in contactos_llamadas:
            contacto_info = contactos_llamadas[call_sid]

        if contacto_info and sheets_manager:
            fila = contacto_info.get('fila') or contacto_info.get('ID')
            telefono = contacto_info.get('telefono')
            nombre_negocio = contacto_info.get('nombre_negocio', 'cliente')

            # Marcar intento de buzón
            intentos = sheets_manager.marcar_intento_buzon(fila)
            print(f"    Intento de buzón #{intentos} registrado")

            # FIX 179: Verificar si los reintentos están deshabilitados
            deshabilitar_reintentos = contacto_info.get('deshabilitar_reintentos', False)

            if intentos == 1 and not deshabilitar_reintentos:
                # PRIMER intento - REINTENTO INMEDIATO
                print(f"    Primer buzón - programando reintento inmediato...", flush=True)
                print(f"    Esperando 30 segundos...", flush=True)
                print(f"    Datos del reintento: tel={telefono}, fila={fila}, base_url={request.url_root}", flush=True)

                import time
                import threading

                # IMPORTANTE: Capturar url_root ANTES del thread (Flask context)
                # Forzar HTTPS para Railway (evita redirect 301/302 que causa 405)
                base_url = request.url_root.replace('http://', 'https://')

                def hacer_reintento():
                    import sys
                    print(f"\n Thread iniciado - esperando 30s...", flush=True)
                    time.sleep(30)
                    print(f"\n Iniciando reintento inmediato a {telefono}...", flush=True)

                    try:
                        import requests
                        response_call = requests.post(
                            f"{base_url}iniciar-llamada",
                            json={
                                "telefono": telefono,
                                "nombre_negocio": nombre_negocio,
                                "contacto_info": contacto_info
                            },
                            timeout=10
                        )

                        if response_call.status_code == 200:
                            data = response_call.json()
                            print(f"    Reintento iniciado: {data.get('call_sid', 'Unknown')}", flush=True)
                        else:
                            print(f"    Error en reintento: {response_call.status_code}", flush=True)
                    except Exception as e:
                        print(f"    Error iniciando reintento: {e}", flush=True)

                # Ejecutar reintento en thread separado para no bloquear el callback
                print(f"    Creando thread para reintento...", flush=True)
                thread = threading.Thread(target=hacer_reintento)
                thread.daemon = True
                thread.start()
                print(f"    Thread iniciado correctamente (daemon={thread.daemon}, alive={thread.is_alive()})", flush=True)

            elif intentos == 1 and deshabilitar_reintentos:
                # FIX 179: Reintentos deshabilitados (llamadas masivas)
                print(f"    FIX 179: Primer intento de buzón pero reintentos DESHABILITADOS (llamadas masivas)", flush=True)

            # FIX 89: GUARDAR en "Bruce FORMS" cuando es buzón después del segundo intento
            elif intentos >= 2:
                print(f"    Segundo intento de buzón - guardando en Bruce FORMS...")

                # Obtener o crear agente para guardar el buzón
                agente = None
                if call_sid in conversaciones_activas:
                    agente = conversaciones_activas[call_sid]
                elif call_sid in contactos_llamadas:
                    # Crear agente temporal para guardar
                    try:
                        from agente_ventas import AgenteVentas
                        agente = AgenteVentas(
                            contacto_info=contacto_info,
                            sheets_manager=sheets_manager,
                            resultados_manager=resultados_manager,
                            whatsapp_validator=whatsapp_validator
                        )
                        agente.call_sid = call_sid
                    except Exception as e:
                        print(f"    Error creando agente temporal: {e}")

                # Guardar el buzón
                if agente:
                    agente.lead_data["estado_llamada"] = "Buzon"
                    agente.lead_data["pregunta_0"] = "Buzon"
                    agente.lead_data["pregunta_7"] = "BUZON"
                    agente.lead_data["resultado"] = "NEGADO"

                    try:
                        agente.guardar_llamada_y_lead()
                        print(f"    Buzón guardado en Bruce FORMS")
                    except Exception as e:
                        print(f"    Error guardando buzón: {e}")
                else:
                    print(f"    No se pudo obtener agente para guardar buzón")

    # FIX 95: Manejo de llamadas FALLIDAS (failed, busy, canceled)
    if call_status in ["failed", "busy", "canceled"]:
        print(f"    Llamada fallida - Estado: {call_status}")

        # Obtener info del contacto
        contacto_info = None
        if call_sid in conversaciones_activas:
            contacto_info = conversaciones_activas[call_sid].contacto_info
        elif call_sid in contactos_llamadas:
            contacto_info = contactos_llamadas[call_sid]

        if contacto_info:
            fila = contacto_info.get('fila') or contacto_info.get('ID')
            telefono = contacto_info.get('telefono', 'desconocido')
            nombre_negocio = contacto_info.get('nombre_negocio', 'desconocido')

            # Obtener código de error de Twilio
            sip_code = request.args.get("SipResponseCode") if request.method == "GET" else request.form.get("SipResponseCode")

            print(f"    Fila {fila}: {nombre_negocio} - {telefono}")
            if sip_code:
                print(f"    SIP Response Code: {sip_code}")

            # Crear agente temporal para guardar el resultado
            try:
                from agente_ventas import AgenteVentas
                agente = AgenteVentas(
                    contacto_info=contacto_info,
                    sheets_manager=sheets_manager,
                    resultados_manager=resultados_manager,
                    whatsapp_validator=whatsapp_validator
                )
                agente.call_sid = call_sid

                # Determinar el estado según el tipo de fallo
                if call_status == "busy":
                    estado = "Ocupado"
                elif call_status == "failed":
                    if sip_code == "500":
                        estado = "Numero Invalido"
                    else:
                        estado = "Fallo Tecnico"
                else:  # canceled
                    estado = "Cancelado"

                agente.lead_data["estado_llamada"] = estado
                agente.lead_data["pregunta_0"] = estado
                agente.lead_data["pregunta_7"] = estado.upper()
                agente.lead_data["resultado"] = "NEGADO"

                # Guardar en "Bruce FORMS"
                agente.guardar_llamada_y_lead()
                print(f"    Llamada fallida guardada: {estado}")

            except Exception as e:
                print(f"    Error guardando llamada fallida: {e}")
                import traceback
                traceback.print_exc()

    # Si la llamada terminó y el agente aún existe en memoria
    if call_status == "completed" and call_sid in conversaciones_activas:
        agente = conversaciones_activas[call_sid]

        # Verificar si fue buzón de voz
        if answered_by in ["machine_start", "machine_end_beep", "machine_end_silence", "machine_end_other"]:
            if agente.lead_data["estado_llamada"] == "Respondio":
                print(f"    Buzón de voz - detectado por status callback")
                agente.lead_data["estado_llamada"] = "Buzon"
                agente.lead_data["pregunta_0"] = "Buzon"
                agente.lead_data["pregunta_7"] = "BUZON"
                agente.lead_data["resultado"] = "NEGADO"

                # Guardar la llamada
                try:
                    agente.guardar_llamada_y_lead()
                    print(f"    Buzón guardado desde status callback")
                except Exception as e:
                    print(f"    Error guardando buzón desde status callback: {e}")

        # Si no fue buzón, determinar si colgó o no respondió
        elif agente.lead_data["estado_llamada"] == "Respondio":
            # FIX 158: NO sobrescribir si Bruce YA se despidió primero
            # Verificar si Bruce terminó con despedida
            bruce_se_despidio = getattr(agente, 'bruce_se_despidio', False)

            if bruce_se_despidio:
                print(f"    FIX 158: Bruce se despidió primero - NO clasificar como 'Colgó'")
                print(f"    Llamada terminó normalmente - cliente respondió y Bruce completó despedida")
                # NO cambiar estado - mantener "Respondio" y el resultado que Bruce determinó
            else:
                # Verificar si hubo intercambio de conversación
                # Si hay menos de 2 mensajes en el historial, el cliente nunca respondió
                num_mensajes = len(agente.conversation_history)

                if num_mensajes <= 1:
                    # Cliente nunca respondió al saludo inicial
                    print(f"    Cliente no respondió - detectado por status callback (solo {num_mensajes} mensaje)")
                    agente.lead_data["estado_llamada"] = "No Respondio"
                    agente.lead_data["pregunta_0"] = "No Respondio"
                    agente.lead_data["pregunta_7"] = "No Respondio"
                    agente.lead_data["resultado"] = "NEGADO"
                else:
                    # FIX 176: Verificar si se capturaron datos antes de marcar como "Colgo"
                    tiene_dato_capturado = (
                        agente.lead_data.get("whatsapp") or
                        agente.lead_data.get("email") or
                        agente.lead_data.get("referencia_telefono")
                    )

                    # Hubo conversación, entonces sí colgó
                    print(f"    Cliente colgó - detectado por status callback ({num_mensajes} mensajes)")

                    if not tiene_dato_capturado:
                        # Sin datos capturados → Marcar como "Colgo"
                        agente.lead_data["estado_llamada"] = "Colgo"
                        agente.lead_data["pregunta_0"] = "Colgo"
                        agente.lead_data["pregunta_7"] = "Colgo"
                        agente.lead_data["resultado"] = "NEGADO"
                        print(f"    Clasificado como 'Colgó' (sin datos capturados)")
                    else:
                        # FIX 176: Con datos capturados → Determinar conclusión correcta
                        print(f"    FIX 176: Cliente colgó pero SÍ capturamos datos:")
                        print(f"      WhatsApp: {bool(agente.lead_data.get('whatsapp'))}")
                        print(f"      Email: {bool(agente.lead_data.get('email'))}")
                        print(f"      Referencia: {bool(agente.lead_data.get('referencia_telefono'))}")
                        # FIX 177: Forzar recálculo para sobrescribir "Colgo" temporal
                        agente._determinar_conclusion(forzar_recalculo=True)
                        print(f"      Conclusión: {agente.lead_data.get('pregunta_7')} ({agente.lead_data.get('resultado')})")

            # Guardar la llamada
            try:
                agente.guardar_llamada_y_lead()
                print(f"    Llamada guardada desde status callback")
            except Exception as e:
                print(f"    Error guardando desde status callback: {e}")

        # FIX 207/272: Registrar en historial para dashboard web
        try:
            registrar_llamada(
                bruce_id=agente.lead_data.get("bruce_id", "N/A"),
                telefono=agente.lead_data.get("telefono", "N/A"),
                negocio=agente.lead_data.get("nombre_negocio", "N/A"),
                resultado=agente.lead_data.get("pregunta_7", agente.lead_data.get("estado_llamada", "N/A")),
                duracion=int(call_duration) if call_duration else 0,
                detalles={
                    "estado": agente.lead_data.get("estado_llamada"),
                    "whatsapp": bool(agente.lead_data.get("whatsapp")),
                    "email": bool(agente.lead_data.get("email")),
                    "recording_url": agente.lead_data.get("recording_url", "")  # FIX 272: Link a grabación
                },
                call_sid=call_sid  # FIX 272: Para asociar grabación después
            )
            print(f"    FIX 207: Llamada registrada en dashboard")
        except Exception as e:
            print(f"    Error registrando en dashboard: {e}")

    return Response("OK", status=200)


@app.route("/status/<call_sid>", methods=["GET"])
def obtener_status(call_sid):
    """Obtiene el estado de una llamada"""
    try:
        call = twilio_client.calls(call_sid).fetch()
        return {
            "call_sid": call.sid,
            "status": call.status,
            "duration": call.duration,
            "from": call.from_,
            "to": call.to
        }
    except Exception as e:
        return {"error": str(e)}, 404


@app.route("/regenerar-cache", methods=["POST"])
def regenerar_cache():
    """Regenera el caché manual con la voz actual"""
    import os

    try:
        # Limpiar caché en memoria
        audio_cache.clear()
        cache_metadata.clear()

        # Eliminar SOLO archivos dentro del directorio (no el directorio mismo)
        # Esto es necesario porque Railway Volume monta el directorio
        if os.path.exists(CACHE_DIR):
            archivos_eliminados = 0
            for archivo in os.listdir(CACHE_DIR):
                filepath = os.path.join(CACHE_DIR, archivo)
                try:
                    if os.path.isfile(filepath):
                        os.remove(filepath)
                        archivos_eliminados += 1
                except Exception as e:
                    print(f"  No se pudo eliminar {archivo}: {e}")

            print(f"  {archivos_eliminados} archivos eliminados del caché")

        # Regenerar caché manual con la voz ACTUAL
        pre_generar_audios_cache()

        return {
            "success": True,
            "message": "Caché regenerado con la voz actual",
            "audios_en_cache": len(audio_cache),
            "voice_id": ELEVENLABS_VOICE_ID
        }

    except Exception as e:
        return {"error": str(e)}, 500


@app.route("/limpiar-audio", methods=["POST"])
def limpiar_audio_especifico():
    """
    FIX 276: Elimina audios del caché que contengan cierta palabra/frase
    Útil para regenerar audios con pronunciación incorrecta

    POST /limpiar-audio
    Body: {"palabra": "ferretería"} o {"frase": "variedad de productos"}
    """
    import os

    try:
        data = request.get_json() or {}
        palabra = data.get('palabra', '').lower()
        frase = data.get('frase', '').lower()

        if not palabra and not frase:
            return {"error": "Debe proporcionar 'palabra' o 'frase' en el body"}, 400

        buscar = frase if frase else palabra
        eliminados = []

        # Buscar en audio_cache (memoria)
        keys_a_eliminar = []
        for key in audio_cache.keys():
            if buscar in key.lower():
                keys_a_eliminar.append(key)

        for key in keys_a_eliminar:
            del audio_cache[key]
            eliminados.append(f"memoria:{key}")

        # Buscar en archivos del disco
        if os.path.exists(CACHE_DIR):
            for archivo in os.listdir(CACHE_DIR):
                if archivo.endswith('.mp3') and buscar.replace(' ', '_') in archivo.lower():
                    filepath = os.path.join(CACHE_DIR, archivo)
                    try:
                        os.remove(filepath)
                        eliminados.append(f"disco:{archivo}")
                    except Exception as e:
                        eliminados.append(f"error:{archivo}:{e}")

        # También buscar en metadata
        if buscar in str(cache_metadata).lower():
            keys_metadata = [k for k in cache_metadata.keys() if buscar in k.lower()]
            for k in keys_metadata:
                if k in cache_metadata:
                    del cache_metadata[k]
                    eliminados.append(f"metadata:{k}")

        return {
            "success": True,
            "busqueda": buscar,
            "eliminados": eliminados,
            "total": len(eliminados),
            "mensaje": f"Se eliminarán {len(eliminados)} audios. La próxima vez que se use esta frase, se regenerará con pronunciación corregida."
        }

    except Exception as e:
        return {"error": str(e)}, 500


@app.route("/listar-audios", methods=["GET"])
def listar_audios():
    """Lista todos los audios disponibles en el cache"""
    import os

    try:
        archivos = []
        if os.path.exists(CACHE_DIR):
            for archivo in os.listdir(CACHE_DIR):
                if archivo.endswith('.mp3'):
                    filepath = os.path.join(CACHE_DIR, archivo)
                    size = os.path.getsize(filepath)
                    archivos.append({
                        "nombre": archivo,
                        "tamaño_kb": round(size / 1024, 2),
                        "url_descarga": f"/descargar-audio/{archivo}"
                    })

        return {
            "total": len(archivos),
            "archivos": archivos,
            "directorio": os.path.abspath(CACHE_DIR)
        }

    except Exception as e:
        return {"error": str(e)}, 500


@app.route("/descargar-audio/<filename>", methods=["GET"])
def descargar_audio(filename):
    """Descarga un archivo de audio del cache"""
    import os
    from flask import send_file

    try:
        # Validar que el archivo existe y es MP3
        if not filename.endswith('.mp3'):
            return {"error": "Solo archivos MP3 permitidos"}, 400

        filepath = os.path.join(CACHE_DIR, filename)

        if not os.path.exists(filepath):
            return {"error": "Archivo no encontrado"}, 404

        return send_file(filepath, mimetype='audio/mpeg', as_attachment=True, download_name=filename)

    except Exception as e:
        return {"error": str(e)}, 500


@app.route("/info-cache", methods=["GET"])
def info_cache():
    """Obtiene información detallada del caché"""
    import os

    try:
        # Listar archivos en disco
        archivos_disco = []
        if os.path.exists(CACHE_DIR):
            archivos_disco = os.listdir(CACHE_DIR)

        # Calcular tamaño total
        tamano_total = 0
        if os.path.exists(CACHE_DIR):
            for archivo in archivos_disco:
                filepath = os.path.join(CACHE_DIR, archivo)
                if os.path.isfile(filepath):
                    tamano_total += os.path.getsize(filepath)

        # Obtener frases más usadas (top 10)
        frases_ordenadas = sorted(
            frase_stats.items(),
            key=lambda x: x[1]["count"],
            reverse=True
        )[:10]

        top_frases = [
            {
                "frase": v["texto"][:60] + "..." if len(v["texto"]) > 60 else v["texto"],
                "usos": v["count"],
                "en_cache": k in audio_cache
            }
            for k, v in frases_ordenadas
        ]

        return {
            "audios_en_cache": len(audio_cache),
            "archivos_en_disco": len(archivos_disco),
            "tamano_mb": round(tamano_total / (1024 * 1024), 2),
            "directorio": CACHE_DIR,
            "voice_id_actual": ELEVENLABS_VOICE_ID,
            "archivos": archivos_disco[:10],  # Primeros 10 archivos
            "frecuencia_min": FRECUENCIA_MIN_CACHE,
            "frases_registradas": len(frase_stats),
            "top_frases": top_frases
        }

    except Exception as e:
        return {"error": str(e)}, 500


@app.route("/frases-sin-audio", methods=["GET"])
def frases_sin_audio():
    """
    Endpoint para obtener todas las frases registradas que no tienen audio en cache
    Ordenadas por frecuencia de uso (las más usadas primero)
    """
    try:
        # Obtener todas las frases sin audio
        frases_pendientes = []
        for key, data in frase_stats.items():
            if key not in audio_cache:
                frases_pendientes.append({
                    "key": key,
                    "texto": data.get("texto", ""),
                    "usos": data.get("count", 0),
                    "tiene_nombre": data.get("tiene_nombre", False)
                })

        # Ordenar por usos (descendente)
        frases_pendientes.sort(key=lambda x: x["usos"], reverse=True)

        # Limitar a las primeras 100 para no saturar
        limit = request.args.get("limit", 100, type=int)
        frases_pendientes = frases_pendientes[:limit]

        return {
            "total_sin_audio": len([k for k in frase_stats if k not in audio_cache]),
            "total_con_audio": len(audio_cache),
            "total_registradas": len(frase_stats),
            "frases": frases_pendientes
        }
    except Exception as e:
        return {"error": str(e)}, 500


@app.route("/reporte-cache", methods=["GET"])
def reporte_cache_html():
    """
    Endpoint para ver reporte visual del caché en HTML
    Acceso: GET /reporte-cache
    """
    from datetime import datetime

    try:
        # Obtener datos del caché
        archivos_disco = []
        tamano_total = 0
        if os.path.exists(CACHE_DIR):
            archivos_disco = os.listdir(CACHE_DIR)
            for archivo in archivos_disco:
                filepath = os.path.join(CACHE_DIR, archivo)
                if os.path.isfile(filepath):
                    tamano_total += os.path.getsize(filepath)

        # Top frases
        frases_ordenadas = sorted(
            frase_stats.items(),
            key=lambda x: x[1]["count"],
            reverse=True
        )[:15]

        # Construir filas de tabla
        filas_top = ""
        for i, (k, v) in enumerate(frases_ordenadas, 1):
            texto = v["texto"][:60] + "..." if len(v["texto"]) > 60 else v["texto"]
            usos = v["count"]
            en_cache = k in audio_cache
            estado = '<span class="badge badge-success">En Cache</span>' if en_cache else '<span class="badge badge-warning">Pendiente</span>'
            filas_top += f'''
                <tr>
                    <td>{i}</td>
                    <td class="text-truncate">{texto}</td>
                    <td><span class="badge badge-info">{usos}x</span></td>
                    <td>{estado}</td>
                </tr>'''

        # Archivos recientes
        filas_archivos = ""
        for i, archivo in enumerate(archivos_disco[:10], 1):
            filas_archivos += f'''
                <tr>
                    <td>{i}</td>
                    <td class="text-truncate">{archivo}</td>
                </tr>'''

        fecha_hora = datetime.now().strftime('%d/%m/%Y %H:%M')
        tamano_mb = round(tamano_total / (1024 * 1024), 1)

        html = f'''<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Reporte Cache Bruce - {fecha_hora}</title>
    <style>
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            font-family: 'Segoe UI', Tahoma, sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            color: #eee;
            min-height: 100vh;
            padding: 20px;
        }}
        .container {{ max-width: 1200px; margin: 0 auto; }}
        h1 {{
            text-align: center;
            color: #00d4ff;
            margin-bottom: 30px;
            font-size: 2.5em;
            text-shadow: 0 0 20px rgba(0,212,255,0.5);
        }}
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}
        .stat-card {{
            background: rgba(255,255,255,0.1);
            border-radius: 15px;
            padding: 25px;
            text-align: center;
            border: 1px solid rgba(255,255,255,0.1);
            transition: transform 0.3s, box-shadow 0.3s;
        }}
        .stat-card:hover {{
            transform: translateY(-5px);
            box-shadow: 0 10px 30px rgba(0,212,255,0.3);
        }}
        .stat-number {{
            font-size: 3em;
            font-weight: bold;
            color: #00d4ff;
            text-shadow: 0 0 10px rgba(0,212,255,0.5);
        }}
        .stat-label {{
            color: #aaa;
            margin-top: 10px;
            font-size: 0.9em;
            text-transform: uppercase;
            letter-spacing: 1px;
        }}
        .section {{
            background: rgba(255,255,255,0.05);
            border-radius: 15px;
            padding: 25px;
            margin-bottom: 25px;
            border: 1px solid rgba(255,255,255,0.1);
        }}
        .section h2 {{
            color: #00d4ff;
            margin-bottom: 20px;
            padding-bottom: 10px;
            border-bottom: 2px solid rgba(0,212,255,0.3);
        }}
        table {{ width: 100%; border-collapse: collapse; }}
        th, td {{
            padding: 12px 15px;
            text-align: left;
            border-bottom: 1px solid rgba(255,255,255,0.1);
        }}
        th {{
            background: rgba(0,212,255,0.2);
            color: #00d4ff;
            font-weight: 600;
        }}
        tr:hover {{ background: rgba(255,255,255,0.05); }}
        .badge {{
            display: inline-block;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 0.8em;
            font-weight: bold;
        }}
        .badge-success {{ background: #00c853; color: #fff; }}
        .badge-warning {{ background: #ff9800; color: #000; }}
        .badge-info {{ background: #00d4ff; color: #000; }}
        .footer {{
            text-align: center;
            color: #666;
            margin-top: 30px;
            padding-top: 20px;
            border-top: 1px solid rgba(255,255,255,0.1);
        }}
        .text-truncate {{
            max-width: 400px;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>Reporte Cache Bruce</h1>

        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-number">{len(audio_cache)}</div>
                <div class="stat-label">Audios en Cache</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{len(frase_stats)}</div>
                <div class="stat-label">Frases Registradas</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{FRECUENCIA_MIN_CACHE}</div>
                <div class="stat-label">Umbral Minimo</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{tamano_mb}</div>
                <div class="stat-label">Tamano (MB)</div>
            </div>
        </div>

        <div class="section">
            <h2>Top Frases en Cache</h2>
            <table>
                <thead>
                    <tr>
                        <th>#</th>
                        <th>Frase</th>
                        <th>Usos</th>
                        <th>Estado</th>
                    </tr>
                </thead>
                <tbody>{filas_top}
                </tbody>
            </table>
        </div>

        <div class="section">
            <h2>Archivos de Audio Recientes</h2>
            <table>
                <thead>
                    <tr>
                        <th>#</th>
                        <th>Archivo</th>
                    </tr>
                </thead>
                <tbody>{filas_archivos}
                </tbody>
            </table>
        </div>

        <div class="footer">
            <p>Generado automaticamente - {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}</p>
            <p>Bruce W - Sistema de Llamadas Automatizadas</p>
        </div>
    </div>
</body>
</html>'''

        return html, 200, {'Content-Type': 'text/html; charset=utf-8'}

    except Exception as e:
        return f"<h1>Error: {str(e)}</h1>", 500


@app.route("/patrones-aprendidos", methods=["GET"])
def ver_patrones_aprendidos():
    """
    FIX 519: Endpoint para ver patrones aprendidos automáticamente
    Acceso: GET /patrones-aprendidos
    """
    try:
        from cache_patrones_aprendidos import obtener_cache_patrones

        cache = obtener_cache_patrones()
        if not cache:
            return "<h1>Cache de patrones no inicializado</h1>", 500

        stats = cache.obtener_estadisticas()
        sugerencias = cache.obtener_sugerencias()

        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>FIX 519 - Patrones Aprendidos</title>
            <meta charset="UTF-8">
            <style>
                body {{ font-family: Arial; max-width: 95%; margin: 0 auto; padding: 20px; background: #1a1a2e; color: #eee; }}
                h1 {{ color: #4CAF50; border-bottom: 2px solid #4CAF50; }}
                h2 {{ color: #00bcd4; }}
                .card {{ background: #16213e; padding: 15px; margin: 10px 0; border-radius: 8px; border-left: 4px solid #4CAF50; }}
                .sugerencia {{ background: #1a1a2e; border: 1px solid #4CAF50; padding: 15px; margin: 10px 0; border-radius: 8px; }}
                .count {{ color: #ff9800; font-weight: bold; }}
                .categoria {{ background: #4CAF50; color: white; padding: 2px 8px; border-radius: 4px; font-size: 12px; }}
                code {{ background: #0d1b2a; padding: 10px; display: block; border-radius: 4px; overflow-x: auto; color: #00ff88; }}
                .ejemplo {{ color: #aaa; font-style: italic; }}
                table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
                th, td {{ padding: 10px; text-align: left; border-bottom: 1px solid #333; }}
                th {{ background: #16213e; color: #4CAF50; }}
            </style>
        </head>
        <body>
            <h1>🧠 FIX 519: Patrones Aprendidos Automáticamente</h1>

            <div class="card">
                <h2>📊 Estadísticas</h2>
                <p>Total patrones guardados: <span class="count">{stats['total_patrones']}</span></p>
                <p>Sugerencias listas: <span class="count">{stats['total_sugerencias']}</span></p>
                <p>Última actualización: {stats['ultima_actualizacion'] or 'N/A'}</p>
            </div>

            <h2>🏆 Top 10 Patrones Más Frecuentes</h2>
            <table>
                <tr><th>Patrón</th><th>Ocurrencias</th></tr>
        """

        for patron, count in stats['top_10_frecuentes']:
            html += f"<tr><td>{patron[:60]}...</td><td class='count'>{count}</td></tr>"

        html += "</table>"

        html += "<h2>💡 Sugerencias para Agregar al Código</h2>"

        if sugerencias:
            for sug in sugerencias[:20]:
                ejemplos_html = "<br>".join([f"• {ej[:80]}" for ej in sug.get('ejemplos', [])])
                html += f"""
                <div class="sugerencia">
                    <p><strong>Patrón:</strong> "{sug['patron_clave']}"</p>
                    <p><span class="categoria">{sug['categoria']}</span> | <span class="count">{sug['count']} ocurrencias</span></p>
                    <p class="ejemplo"><strong>Ejemplos:</strong><br>{ejemplos_html}</p>
                    <code>{sug.get('codigo_sugerido', 'N/A')}</code>
                </div>
                """
        else:
            html += "<p>No hay sugerencias todavía. Se necesitan al menos 3 ocurrencias de un patrón.</p>"

        html += """
            <h2>📈 Por Categoría</h2>
            <table>
                <tr><th>Categoría</th><th>Cantidad</th></tr>
        """

        for cat, count in stats.get('por_categoria', {}).items():
            html += f"<tr><td>{cat}</td><td class='count'>{count}</td></tr>"

        html += """
            </table>
        </body>
        </html>
        """

        return html

    except Exception as e:
        return f"<h1>Error: {e}</h1>", 500


@app.route("/stats", methods=["GET"])
def ver_estadisticas():
    """
    Endpoint para ver estadísticas de frases y caché en tiempo real
    Acceso: GET http://localhost:5000/stats o https://tu-dominio.railway.app/stats
    """
    try:
        # Cargar estadísticas desde archivo
        stats_file = os.path.join(CACHE_DIR, "frase_stats.json")
        if os.path.exists(stats_file):
            with open(stats_file, 'r', encoding='utf-8') as f:
                stats = json.load(f)
        else:
            stats = {}

        # Ordenar por frecuencia (más usadas primero)
        # stats tiene formato: {"frase_key": {"texto": "...", "count": N}}
        sorted_stats = dict(sorted(stats.items(), key=lambda x: x[1].get("count", 0), reverse=True))

        # Estadísticas generales
        total_frases = len(sorted_stats)
        total_usos = sum(item.get("count", 0) for item in sorted_stats.values())
        frases_en_cache = len(audio_cache)

        # Construir respuesta HTML bonita
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Estadísticas Bruce W - Caché de Audio</title>
            <meta charset="UTF-8">
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    max-width: 95%;
                    margin: 0 auto;
                    padding: 20px;
                    background: #f5f5f5;
                }}
                h1 {{
                    color: #333;
                    border-bottom: 3px solid #4CAF50;
                    padding-bottom: 10px;
                }}
                .stats-summary {{
                    display: flex;
                    gap: 20px;
                    margin: 20px 0;
                }}
                .stat-card {{
                    background: white;
                    padding: 20px;
                    border-radius: 8px;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                    flex: 1;
                }}
                .stat-number {{
                    font-size: 2em;
                    font-weight: bold;
                    color: #4CAF50;
                }}
                .stat-label {{
                    color: #666;
                    margin-top: 5px;
                }}
                table {{
                    width: 100%;
                    background: white;
                    border-radius: 8px;
                    overflow: hidden;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                    border-collapse: collapse;
                }}
                th {{
                    background: #4CAF50;
                    color: white;
                    padding: 15px;
                    text-align: left;
                }}
                td {{
                    padding: 12px 15px;
                    border-bottom: 1px solid #ddd;
                }}
                tr:hover {{
                    background: #f9f9f9;
                }}
                .cached {{
                    color: #4CAF50;
                    font-weight: bold;
                }}
                .not-cached {{
                    color: #999;
                }}
                .frase-text {{
                    max-width: none;
                    word-wrap: break-word;
                    white-space: normal;
                    min-width: 400px;
                }}
                .download-section {{
                    background: white;
                    padding: 20px;
                    border-radius: 8px;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                    margin: 20px 0;
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                }}
                .download-btn {{
                    background: #4CAF50;
                    color: white;
                    padding: 12px 24px;
                    border: none;
                    border-radius: 6px;
                    cursor: pointer;
                    font-size: 16px;
                    font-weight: bold;
                }}
                .download-btn:hover {{
                    background: #45a049;
                }}
                .download-btn:disabled {{
                    background: #ccc;
                    cursor: not-allowed;
                }}
                .select-all-btn {{
                    background: #2196F3;
                    color: white;
                    padding: 8px 16px;
                    border: none;
                    border-radius: 4px;
                    cursor: pointer;
                    margin-left: 10px;
                }}
                .select-all-btn:hover {{
                    background: #0b7dda;
                }}
                input[type="checkbox"] {{
                    width: 18px;
                    height: 18px;
                    cursor: pointer;
                }}
            </style>
        </head>
        <body>
            <h1> Estadísticas de Caché - Bruce W</h1>

            <div class="stats-summary">
                <div class="stat-card">
                    <div class="stat-number">{total_frases}</div>
                    <div class="stat-label">Frases Únicas</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number">{total_usos}</div>
                    <div class="stat-label">Usos Totales</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number">{frases_en_cache}</div>
                    <div class="stat-label">Audios en Caché</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number">{FRECUENCIA_MIN_CACHE}</div>
                    <div class="stat-label">Umbral Auto-Caché</div>
                </div>
            </div>

            <div class="download-section">
                <div>
                    <span id="selected-count">0 frases seleccionadas</span>
                    <button class="select-all-btn" onclick="selectAll()">Seleccionar Todo</button>
                    <button class="select-all-btn" onclick="deselectAll()">Deseleccionar Todo</button>
                </div>
                <button class="download-btn" id="generate-btn" onclick="generateSelected()" disabled>
                     Generar Audios Seleccionados
                </button>
            </div>

            <h2> Frases por Frecuencia de Uso</h2>
            <table>
                <thead>
                    <tr>
                        <th><input type="checkbox" id="select-all-header" onclick="toggleAll()"></th>
                        <th>#</th>
                        <th>Frase</th>
                        <th>Usos</th>
                        <th>Estado</th>
                    </tr>
                </thead>
                <tbody>
        """

        # Agregar filas de la tabla
        for i, (frase_key, data) in enumerate(sorted_stats.items(), 1):
            # Extraer texto y contador
            texto = data.get("texto", frase_key)
            count = data.get("count", 0)

            # Verificar si está en caché
            frase_normalizada = frase_key
            en_cache = frase_normalizada in audio_cache
            estado = '<span class="cached"> En caché</span>' if en_cache else '<span class="not-cached"> No cacheado</span>'

            # Mostrar frase completa (sin limitar)
            frase_display = texto

            # Checkbox deshabilitado si ya está en caché
            checkbox_disabled = 'disabled' if en_cache else ''
            checkbox_html = f'<input type="checkbox" class="frase-checkbox" data-texto="{texto}" data-key="{frase_key}" {checkbox_disabled} onchange="updateSelectedCount()">'

            html += f"""
                    <tr>
                        <td>{checkbox_html}</td>
                        <td>{i}</td>
                        <td class="frase-text">{frase_display}</td>
                        <td><strong>{count}</strong></td>
                        <td>{estado}</td>
                    </tr>
            """

        html += """
                </tbody>
            </table>

            <p style="margin-top: 20px; color: #666; text-align: center;">
                Actualizado en tiempo real • Railway Volume Persistente
            </p>

            <script>
                function updateSelectedCount() {
                    const checkboxes = document.querySelectorAll('.frase-checkbox:checked');
                    const count = checkboxes.length;
                    document.getElementById('selected-count').textContent = count + ' frases seleccionadas';
                    document.getElementById('generate-btn').disabled = count === 0;
                }

                function selectAll() {
                    document.querySelectorAll('.frase-checkbox:not(:disabled)').forEach(cb => {
                        cb.checked = true;
                    });
                    updateSelectedCount();
                }

                function deselectAll() {
                    document.querySelectorAll('.frase-checkbox').forEach(cb => {
                        cb.checked = false;
                    });
                    updateSelectedCount();
                }

                function toggleAll() {
                    const headerCheckbox = document.getElementById('select-all-header');
                    document.querySelectorAll('.frase-checkbox:not(:disabled)').forEach(cb => {
                        cb.checked = headerCheckbox.checked;
                    });
                    updateSelectedCount();
                }

                async function generateSelected() {
                    const checkboxes = document.querySelectorAll('.frase-checkbox:checked');
                    const frases = Array.from(checkboxes).map(cb => ({
                        texto: cb.dataset.texto,
                        key: cb.dataset.key
                    }));

                    if (frases.length === 0) {
                        alert('Selecciona al menos una frase');
                        return;
                    }

                    const btn = document.getElementById('generate-btn');
                    btn.disabled = true;
                    btn.textContent = ' Generando ' + frases.length + ' audios...';

                    try {
                        const response = await fetch('/generate-cache', {
                            method: 'POST',
                            headers: {'Content-Type': 'application/json'},
                            body: JSON.stringify({frases: frases})
                        });

                        const result = await response.json();

                        if (result.success) {
                            alert(' ' + result.generated + ' audios generados correctamente!');
                            location.reload(); // Recargar para ver cambios
                        } else {
                            alert(' Error: ' + result.error);
                        }
                    } catch (error) {
                        alert(' Error al generar audios: ' + error.message);
                    }

                    btn.disabled = false;
                    btn.textContent = ' Generar Audios Seleccionados';
                }
            </script>
        </body>
        </html>
        """

        return html

    except Exception as e:
        return {
            "error": str(e),
            "message": "Error al cargar estadísticas"
        }, 500


@app.route("/generate-cache", methods=["POST"])
def generar_cache_manual():
    """
    Endpoint para generar audios de caché manualmente desde la interfaz /stats
    Recibe: {"frases": [{"texto": "...", "key": "..."}, ...]}
    """
    try:
        data = request.json
        frases = data.get("frases", [])

        if not frases:
            return {"success": False, "error": "No se proporcionaron frases"}, 400

        generated_count = 0
        errors = []

        for frase_data in frases:
            texto = frase_data.get("texto")
            key = frase_data.get("key")
            force = frase_data.get("force", False)  # FIX 93: Permitir forzar regeneración

            if not texto or not key:
                continue

            # Verificar si ya existe en caché (skip si no es forzado)
            if key in audio_cache and not force:
                print(f" Omitido: {key} (ya está en caché)")
                continue
            elif key in audio_cache and force:
                print(f" Regenerando: {key} (force=True)")

            try:
                print(f"\n Generando audio para: {texto[:50]}...")

                # Generar audio con ElevenLabs Multilingual v2
                audio_generator = elevenlabs_client.text_to_speech.convert(
                    voice_id=ELEVENLABS_VOICE_ID,
                    text=texto,
                    model_id="eleven_multilingual_v2",
                    output_format="mp3_44100_128"
                )

                # Guardar en memoria
                audio_bytes = b"".join(audio_generator)
                audio_cache[key] = audio_bytes

                # Crear archivo temporal para guardar en disco
                with tempfile.NamedTemporaryFile(mode='wb', suffix='.mp3', delete=False) as temp_file:
                    temp_file.write(audio_bytes)
                    temp_path = temp_file.name

                # Guardar en disco para persistencia
                guardar_cache_en_disco(key, texto, temp_path)

                # Limpiar archivo temporal
                try:
                    os.unlink(temp_path)
                except Exception as e:
                    print(f" No se pudo eliminar temp {temp_path}: {e}")

                generated_count += 1
                print(f" Audio generado y cacheado: {key}")

            except Exception as e:
                error_msg = f"Error en '{texto[:30]}...': {str(e)}"
                errors.append(error_msg)
                print(f" {error_msg}")

        # Respuesta
        result = {
            "success": True,
            "generated": generated_count,
            "total_requested": len(frases),
            "errors": errors if errors else None
        }

        print(f"\n Generación completada: {generated_count}/{len(frases)} audios")
        return result

    except Exception as e:
        print(f" Error en generate-cache: {e}")
        return {
            "success": False,
            "error": str(e)
        }, 500


@app.route("/version", methods=["GET"])
def check_version():
    """
    Endpoint para verificar qué versión del código está corriendo en Railway
    """
    # Verificar si agente_ventas.py tiene el código FIX 81
    import inspect
    from agente_ventas import AgenteVentas

    # Obtener el código fuente del método procesar_respuesta
    source_code = inspect.getsource(AgenteVentas.procesar_respuesta)

    # Verificar si tiene los FIX esperados
    tiene_fix_81 = "FIX 81 DEBUG" in source_code
    tiene_fix_79 = "Perfecto, comprendo que ya trabajan con un proveedor fijo" in source_code
    tiene_patron_truper = '"truper"' in source_code or "'truper'" in source_code

    return {
        "version": "FIX 86 - Timeouts aumentados para evitar hangup inmediato",
        "servidor_actualizado": True,
        "agente_ventas_fix_81": tiene_fix_81,
        "agente_ventas_fix_79": tiene_fix_79,
        "agente_ventas_patron_truper": tiene_patron_truper,
        "gather_timeout": "6s (antes 3s)",
        "gather_speech_timeout": "3s (antes 1s)",
        "despedida_calida": "Perfecto, comprendo que ya trabajan con un proveedor fijo...",
        "git_commit": "FIX_86",
        "mensaje": "Timeouts aumentados para dar más tiempo al cliente de responder"
    }


@app.route("/estado-llamada/<call_sid>", methods=["GET"])
def estado_llamada(call_sid):
    """
    FIX 88: Endpoint para consultar el estado actual de una llamada
    Permite al script de llamadas masivas esperar a que termine una llamada antes de iniciar la siguiente

    Retorna:
        - activa: True si la llamada sigue activa
        - estado: "completed", "in-progress", "no-encontrada"
        - duracion: segundos de duración (si está disponible)
    """
    try:
        # Verificar si la conversación sigue activa en memoria
        if call_sid in conversaciones_activas:
            agente = conversaciones_activas[call_sid]
            return {
                "call_sid": call_sid,
                "activa": True,
                "estado": "in-progress",
                "nombre_negocio": agente.lead_data.get("nombre_negocio", "N/A"),
                "mensaje": "Llamada en progreso"
            }

        # Llamada no está activa en memoria (terminó o nunca existió)
        # Consultar Twilio para ver el estado real
        if twilio_client:
            try:
                call = twilio_client.calls(call_sid).fetch()
                return {
                    "call_sid": call_sid,
                    "activa": False,
                    "estado": call.status,
                    "duracion": call.duration,
                    "mensaje": f"Llamada {call.status}"
                }
            except Exception as e:
                return {
                    "call_sid": call_sid,
                    "activa": False,
                    "estado": "no-encontrada",
                    "error": str(e),
                    "mensaje": "Llamada no encontrada en Twilio"
                }
        else:
            return {
                "call_sid": call_sid,
                "activa": False,
                "estado": "completed",
                "mensaje": "Llamada no activa (Twilio no disponible)"
            }

    except Exception as e:
        return {
            "error": str(e),
            "call_sid": call_sid,
            "activa": False,
            "estado": "error"
        }, 500


@app.route("/diagnostico-persistencia", methods=["GET"])
def diagnostico_persistencia():
    """
    Endpoint de diagnóstico para verificar el estado del volumen persistente en Railway
    Muestra información detallada sobre archivos, permisos y capacidad de escritura
    """
    import os
    import tempfile

    try:
        diagnostico = {
            "directorio_cache": CACHE_DIR,
            "ruta_absoluta": os.path.abspath(CACHE_DIR),
            "existe": os.path.exists(CACHE_DIR),
            "es_directorio": os.path.isdir(CACHE_DIR) if os.path.exists(CACHE_DIR) else False,
        }

        # Verificar permisos de lectura/escritura
        if os.path.exists(CACHE_DIR):
            diagnostico["readable"] = os.access(CACHE_DIR, os.R_OK)
            diagnostico["writable"] = os.access(CACHE_DIR, os.W_OK)
            diagnostico["executable"] = os.access(CACHE_DIR, os.X_OK)
        else:
            diagnostico["readable"] = False
            diagnostico["writable"] = False
            diagnostico["executable"] = False

        # Listar archivos en el directorio
        archivos_info = []
        if os.path.exists(CACHE_DIR):
            for archivo in os.listdir(CACHE_DIR):
                filepath = os.path.join(CACHE_DIR, archivo)
                if os.path.isfile(filepath):
                    archivos_info.append({
                        "nombre": archivo,
                        "tamano_kb": round(os.path.getsize(filepath) / 1024, 2),
                        "fecha_modificacion": os.path.getmtime(filepath)
                    })

        diagnostico["total_archivos"] = len(archivos_info)
        diagnostico["archivos"] = sorted(archivos_info, key=lambda x: x["fecha_modificacion"], reverse=True)[:20]  # Últimos 20

        # Calcular tamaño total
        tamano_total = sum(a["tamano_kb"] for a in archivos_info)
        diagnostico["tamano_total_mb"] = round(tamano_total / 1024, 2)

        # Verificar metadata.json
        metadata_file = os.path.join(CACHE_DIR, "metadata.json")
        diagnostico["metadata_existe"] = os.path.exists(metadata_file)
        if os.path.exists(metadata_file):
            diagnostico["metadata_tamano_kb"] = round(os.path.getsize(metadata_file) / 1024, 2)

        # Verificar frase_stats.json
        stats_file = os.path.join(CACHE_DIR, "frase_stats.json")
        diagnostico["stats_existe"] = os.path.exists(stats_file)
        if os.path.exists(stats_file):
            diagnostico["stats_tamano_kb"] = round(os.path.getsize(stats_file) / 1024, 2)

        # Test de escritura
        try:
            test_file = os.path.join(CACHE_DIR, ".test_write")
            with open(test_file, 'w') as f:
                f.write("test")
            os.remove(test_file)
            diagnostico["test_escritura"] = " OK"
        except Exception as e:
            diagnostico["test_escritura"] = f" FALLO: {str(e)}"

        # Variables de entorno relevantes
        diagnostico["env_vars"] = {
            "CACHE_DIR": os.getenv("CACHE_DIR", "No configurada (usando default)"),
            "RAILWAY_VOLUME_MOUNT_PATH": os.getenv("RAILWAY_VOLUME_MOUNT_PATH", "No configurada"),
        }

        # Estado de caché en memoria
        diagnostico["cache_memoria"] = {
            "audios_cargados": len(audio_cache),
            "frases_registradas": len(frase_stats),
        }

        # Generar HTML de diagnóstico
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Diagnóstico de Persistencia - Bruce W</title>
            <meta charset="UTF-8">
            <style>
                body {{
                    font-family: 'Courier New', monospace;
                    max-width: 1000px;
                    margin: 0 auto;
                    padding: 20px;
                    background: #1e1e1e;
                    color: #d4d4d4;
                }}
                h1 {{
                    color: #4ec9b0;
                    border-bottom: 2px solid #4ec9b0;
                    padding-bottom: 10px;
                }}
                h2 {{
                    color: #569cd6;
                    margin-top: 30px;
                }}
                .section {{
                    background: #252526;
                    padding: 15px;
                    border-radius: 5px;
                    margin: 15px 0;
                    border-left: 4px solid #4ec9b0;
                }}
                .ok {{
                    color: #4ec9b0;
                    font-weight: bold;
                }}
                .error {{
                    color: #f48771;
                    font-weight: bold;
                }}
                .warning {{
                    color: #dcdcaa;
                    font-weight: bold;
                }}
                table {{
                    width: 100%;
                    border-collapse: collapse;
                    margin: 10px 0;
                }}
                th, td {{
                    padding: 8px;
                    text-align: left;
                    border-bottom: 1px solid #3e3e42;
                }}
                th {{
                    background: #2d2d30;
                    color: #4ec9b0;
                }}
                .key {{
                    color: #9cdcfe;
                }}
                .value {{
                    color: #ce9178;
                }}
            </style>
        </head>
        <body>
            <h1> Diagnóstico de Persistencia - Railway</h1>

            <div class="section">
                <h2> Información del Directorio</h2>
                <table>
                    <tr>
                        <td class="key">Directorio configurado:</td>
                        <td class="value">{diagnostico['directorio_cache']}</td>
                    </tr>
                    <tr>
                        <td class="key">Ruta absoluta:</td>
                        <td class="value">{diagnostico['ruta_absoluta']}</td>
                    </tr>
                    <tr>
                        <td class="key">Existe:</td>
                        <td class="{'ok' if diagnostico['existe'] else 'error'}">
                            {' SÍ' if diagnostico['existe'] else ' NO'}
                        </td>
                    </tr>
                    <tr>
                        <td class="key">Es directorio:</td>
                        <td class="{'ok' if diagnostico['es_directorio'] else 'error'}">
                            {' SÍ' if diagnostico['es_directorio'] else ' NO'}
                        </td>
                    </tr>
                </table>
            </div>

            <div class="section">
                <h2> Permisos</h2>
                <table>
                    <tr>
                        <td class="key">Lectura (R):</td>
                        <td class="{'ok' if diagnostico['readable'] else 'error'}">
                            {' OK' if diagnostico['readable'] else ' FALLO'}
                        </td>
                    </tr>
                    <tr>
                        <td class="key">Escritura (W):</td>
                        <td class="{'ok' if diagnostico['writable'] else 'error'}">
                            {' OK' if diagnostico['writable'] else ' FALLO'}
                        </td>
                    </tr>
                    <tr>
                        <td class="key">Ejecución (X):</td>
                        <td class="{'ok' if diagnostico['executable'] else 'error'}">
                            {' OK' if diagnostico['executable'] else ' FALLO'}
                        </td>
                    </tr>
                    <tr>
                        <td class="key">Test de escritura:</td>
                        <td class="{'ok' if 'OK' in diagnostico['test_escritura'] else 'error'}">
                            {diagnostico['test_escritura']}
                        </td>
                    </tr>
                </table>
            </div>

            <div class="section">
                <h2> Archivos en Disco</h2>
                <table>
                    <tr>
                        <td class="key">Total archivos:</td>
                        <td class="value">{diagnostico['total_archivos']}</td>
                    </tr>
                    <tr>
                        <td class="key">Tamaño total:</td>
                        <td class="value">{diagnostico['tamano_total_mb']} MB</td>
                    </tr>
                    <tr>
                        <td class="key">metadata.json:</td>
                        <td class="{'ok' if diagnostico['metadata_existe'] else 'warning'}">
                            {' Existe (' + str(diagnostico.get('metadata_tamano_kb', 0)) + ' KB)' if diagnostico['metadata_existe'] else ' No existe'}
                        </td>
                    </tr>
                    <tr>
                        <td class="key">frase_stats.json:</td>
                        <td class="{'ok' if diagnostico['stats_existe'] else 'warning'}">
                            {' Existe (' + str(diagnostico.get('stats_tamano_kb', 0)) + ' KB)' if diagnostico['stats_existe'] else ' No existe'}
                        </td>
                    </tr>
                </table>
            </div>

            <div class="section">
                <h2> Caché en Memoria</h2>
                <table>
                    <tr>
                        <td class="key">Audios cargados:</td>
                        <td class="value">{diagnostico['cache_memoria']['audios_cargados']}</td>
                    </tr>
                    <tr>
                        <td class="key">Frases registradas:</td>
                        <td class="value">{diagnostico['cache_memoria']['frases_registradas']}</td>
                    </tr>
                </table>
            </div>

            <div class="section">
                <h2> Variables de Entorno</h2>
                <table>
                    <tr>
                        <td class="key">CACHE_DIR:</td>
                        <td class="value">{diagnostico['env_vars']['CACHE_DIR']}</td>
                    </tr>
                    <tr>
                        <td class="key">RAILWAY_VOLUME_MOUNT_PATH:</td>
                        <td class="value">{diagnostico['env_vars']['RAILWAY_VOLUME_MOUNT_PATH']}</td>
                    </tr>
                </table>
            </div>

            <div class="section">
                <h2> Últimos Archivos (Top 20)</h2>
                <table>
                    <tr>
                        <th>Archivo</th>
                        <th>Tamaño (KB)</th>
                    </tr>
        """

        for archivo in diagnostico['archivos'][:20]:
            html += f"""
                    <tr>
                        <td class="value">{archivo['nombre']}</td>
                        <td class="value">{archivo['tamano_kb']}</td>
                    </tr>
            """

        html += """
                </table>
            </div>

            <div class="section">
                <h2> Recomendaciones</h2>
                <ul>
                    <li>Si el directorio NO existe, verifica que el volumen esté montado en Railway</li>
                    <li>Si NO hay permisos de escritura, verifica la configuración del volumen</li>
                    <li>Si metadata.json NO existe, el caché no sobrevivirá a reinicios del contenedor</li>
                    <li>Verifica que RAILWAY_VOLUME_MOUNT_PATH apunte al directorio correcto</li>
                    <li>Idealmente, CACHE_DIR debe ser igual a RAILWAY_VOLUME_MOUNT_PATH</li>
                </ul>
            </div>
        </body>
        </html>
        """

        return html

    except Exception as e:
        return {
            "error": str(e),
            "message": "Error al realizar diagnóstico"
        }, 500


# ============================================================================
# FIX 207: DASHBOARD DE MONITOREO EN TIEMPO REAL
# ============================================================================

from collections import deque

# FIX 272.2: Archivo para persistir historial entre deploys
HISTORIAL_FILE = os.path.join(CACHE_DIR, "historial_llamadas.json")

def cargar_historial():
    """Carga el historial de llamadas desde archivo JSON"""
    try:
        if os.path.exists(HISTORIAL_FILE):
            with open(HISTORIAL_FILE, 'r', encoding='utf-8') as f:
                datos = json.load(f)
                return deque(datos, maxlen=500)  # Últimas 500 llamadas
    except Exception as e:
        print(f" FIX 272.2: Error cargando historial: {e}")
    return deque(maxlen=500)

def guardar_historial():
    """Guarda el historial en archivo JSON para persistir entre deploys"""
    try:
        os.makedirs(os.path.dirname(HISTORIAL_FILE), exist_ok=True)
        with open(HISTORIAL_FILE, 'w', encoding='utf-8') as f:
            json.dump(list(historial_llamadas), f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f" FIX 272.2: Error guardando historial: {e}")
        return False

# Cargar historial al iniciar
historial_llamadas = cargar_historial()
print(f" FIX 272.2: {len(historial_llamadas)} llamadas en historial cargadas")

# FIX 272: Mapeo CallSid -> bruce_id para asociar grabaciones
callsid_to_bruceid = {}  # call_sid -> bruce_id
grabaciones_por_bruce = {}  # bruce_id -> recording_url

def registrar_llamada(bruce_id, telefono, negocio, resultado, duracion=0, detalles=None, call_sid=None):
    """Registra una llamada en el historial para el dashboard"""
    # FIX 272: Guardar mapeo call_sid -> bruce_id
    if call_sid and bruce_id:
        callsid_to_bruceid[call_sid] = bruce_id

    historial_llamadas.append({
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "bruce_id": bruce_id,
        "telefono": telefono,
        "negocio": negocio,
        "resultado": resultado,
        "duracion": duracion,
        "detalles": detalles or {},
        "call_sid": call_sid,  # FIX 272: Guardar para asociar grabación después
        "deploy_id": DEPLOY_ID,  # FIX 272.10: Guardar deploy donde ocurrió la llamada
        "deploy_name": DEPLOY_NAME  # FIX 282: Nombre del deploy (más legible)
    })

    # FIX 272.2: Persistir historial en disco
    guardar_historial()


@app.route("/logs", methods=["GET"])
def ver_dashboard():
    """
    FIX 207: Dashboard de monitoreo en tiempo real
    Muestra: llamadas activas, historial reciente, estadísticas del sistema
    """
    try:
        formato = request.args.get('formato', 'html')

        # Obtener llamadas activas desde conversaciones_activas
        llamadas_activas_lista = []
        for call_sid, agente in conversaciones_activas.items():
            try:
                llamadas_activas_lista.append({
                    "call_sid": call_sid[:20] + "...",
                    "bruce_id": agente.lead_data.get("bruce_id", "N/A") if hasattr(agente, 'lead_data') else "N/A",
                    "telefono": agente.lead_data.get("telefono", "N/A") if hasattr(agente, 'lead_data') else "N/A",
                    "negocio": agente.lead_data.get("nombre_negocio", "N/A") if hasattr(agente, 'lead_data') else "N/A",
                    "inicio": "En curso"
                })
            except Exception as e:
                print(f" Error obteniendo info de llamada activa: {e}")

        # Obtener historial reciente
        historial = list(historial_llamadas)[-50:]  # Últimas 50
        historial = list(reversed(historial))  # Más recientes primero

        # Estadísticas
        total_llamadas = len(historial_llamadas)
        exitosas = sum(1 for l in historial_llamadas if "catálogo" in str(l.get("resultado", "")).lower() or "éxito" in str(l.get("resultado", "")).lower())
        ivr_detectados = sum(1 for l in historial_llamadas if "ivr" in str(l.get("resultado", "")).lower())
        no_contesto = sum(1 for l in historial_llamadas if "no contestó" in str(l.get("resultado", "")).lower())

        # Info del sistema
        info_sistema = {
            "audios_en_cache": len(audio_cache),
            "frases_registradas": len(frase_stats),
            "llamadas_activas": len(conversaciones_activas),
            "historial_total": total_llamadas
        }

        if formato == 'json':
            return {
                "llamadas_activas": llamadas_activas_lista,
                "historial": historial,
                "estadisticas": {
                    "total": total_llamadas,
                    "exitosas": exitosas,
                    "ivr": ivr_detectados,
                    "no_contesto": no_contesto
                },
                "sistema": info_sistema
            }

        # Generar HTML
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title> Dashboard Bruce W - Monitoreo</title>
            <meta charset="UTF-8">
            <meta http-equiv="refresh" content="15">
            <style>
                body {{
                    font-family: 'Segoe UI', Arial, sans-serif;
                    background: #1a1a2e;
                    color: #eee;
                    margin: 0;
                    padding: 20px;
                }}
                h1 {{
                    color: #4CAF50;
                    border-bottom: 2px solid #4CAF50;
                    padding-bottom: 10px;
                }}
                h2 {{
                    color: #2196F3;
                    margin-top: 30px;
                }}
                .stats {{
                    display: flex;
                    gap: 15px;
                    margin: 20px 0;
                    flex-wrap: wrap;
                }}
                .stat-box {{
                    padding: 15px 25px;
                    border-radius: 10px;
                    font-weight: bold;
                    min-width: 120px;
                    text-align: center;
                }}
                .stat-box .number {{
                    font-size: 2em;
                    display: block;
                }}
                .stat-box .label {{
                    font-size: 0.9em;
                    opacity: 0.8;
                }}
                .stat-activas {{ background: #2196F3; }}
                .stat-exitosas {{ background: #4CAF50; }}
                .stat-ivr {{ background: #ff9800; }}
                .stat-nocontesto {{ background: #9e9e9e; }}
                .stat-cache {{ background: #9c27b0; }}

                table {{
                    width: 100%;
                    border-collapse: collapse;
                    margin: 15px 0;
                    background: #16213e;
                    border-radius: 10px;
                    overflow: hidden;
                }}
                th {{
                    background: #0f3460;
                    padding: 12px;
                    text-align: left;
                }}
                td {{
                    padding: 10px 12px;
                    border-bottom: 1px solid #1a1a2e;
                }}
                tr:hover {{
                    background: #1f4287;
                }}
                .resultado-exito {{ color: #4CAF50; }}
                .resultado-ivr {{ color: #ff9800; }}
                .resultado-nocontesto {{ color: #9e9e9e; }}
                .resultado-error {{ color: #f44336; }}

                .refresh-indicator {{
                    position: fixed;
                    top: 20px;
                    right: 20px;
                    background: #16213e;
                    padding: 10px 15px;
                    border-radius: 8px;
                    font-size: 12px;
                }}
                .pulse {{
                    display: inline-block;
                    width: 10px;
                    height: 10px;
                    background: #4CAF50;
                    border-radius: 50%;
                    animation: pulse 2s infinite;
                    margin-right: 8px;
                }}
                @keyframes pulse {{
                    0% {{ opacity: 1; transform: scale(1); }}
                    50% {{ opacity: 0.5; transform: scale(1.2); }}
                    100% {{ opacity: 1; transform: scale(1); }}
                }}

                .empty-state {{
                    text-align: center;
                    padding: 30px;
                    color: #666;
                    background: #16213e;
                    border-radius: 10px;
                }}

                .nav-links {{
                    margin: 20px 0;
                    padding: 15px;
                    background: #16213e;
                    border-radius: 10px;
                }}
                .nav-links a {{
                    color: #4CAF50;
                    margin-right: 20px;
                    text-decoration: none;
                }}
                .nav-links a:hover {{
                    text-decoration: underline;
                }}
            </style>
        </head>
        <body>
            <div class="refresh-indicator">
                <span class="pulse"></span> Auto-refresh 15s
            </div>

            <h1> Dashboard de Monitoreo - Bruce W</h1>

            <div class="nav-links">
                 <a href="/historial-llamadas">Historial + Calificaciones</a>
                 <a href="/stats">Estadísticas de Caché</a>
                 <a href="/diagnostico-persistencia">Diagnóstico</a>
                 <a href="/logs" onclick="location.reload(); return false;">Refrescar</a>
            </div>

            <div class="stats">
                <div class="stat-box stat-activas">
                    <span class="number">{len(conversaciones_activas)}</span>
                    <span class="label">Llamadas Activas</span>
                </div>
                <div class="stat-box stat-exitosas">
                    <span class="number">{exitosas}</span>
                    <span class="label">Exitosas</span>
                </div>
                <div class="stat-box stat-ivr">
                    <span class="number">{ivr_detectados}</span>
                    <span class="label">IVR Detectados</span>
                </div>
                <div class="stat-box stat-nocontesto">
                    <span class="number">{no_contesto}</span>
                    <span class="label">No Contestó</span>
                </div>
                <div class="stat-box stat-cache">
                    <span class="number">{info_sistema['audios_en_cache']}</span>
                    <span class="label">Audios en Caché</span>
                </div>
            </div>

            <h2> Llamadas Activas ({len(llamadas_activas_lista)})</h2>
        """

        if llamadas_activas_lista:
            html += """
            <table>
                <tr>
                    <th>BRUCE ID</th>
                    <th>Teléfono</th>
                    <th>Negocio</th>
                    <th>Call SID</th>
                </tr>
            """
            for llamada in llamadas_activas_lista:
                html += f"""
                <tr>
                    <td><strong>{llamada['bruce_id']}</strong></td>
                    <td>{llamada['telefono']}</td>
                    <td>{llamada['negocio']}</td>
                    <td style="font-size: 11px; color: #888;">{llamada['call_sid']}</td>
                </tr>
                """
            html += "</table>"
        else:
            html += """
            <div class="empty-state">
                No hay llamadas activas en este momento.
            </div>
            """

        html += f"""
            <h2> Historial Reciente ({total_llamadas} total)</h2>
        """

        if historial:
            html += """
            <table>
                <tr>
                    <th>Hora</th>
                    <th>BRUCE ID</th>
                    <th>Teléfono</th>
                    <th>Negocio</th>
                    <th>Resultado</th>
                </tr>
            """
            for llamada in historial[:30]:
                resultado = llamada.get('resultado', 'N/A')
                clase_resultado = 'resultado-exito' if 'catálogo' in resultado.lower() else 'resultado-ivr' if 'ivr' in resultado.lower() else 'resultado-nocontesto' if 'no contestó' in resultado.lower() else ''
                html += f"""
                <tr>
                    <td style="font-size: 12px;">{llamada.get('timestamp', 'N/A')}</td>
                    <td><strong>{llamada.get('bruce_id', 'N/A')}</strong></td>
                    <td>{llamada.get('telefono', 'N/A')}</td>
                    <td>{llamada.get('negocio', 'N/A')[:30]}</td>
                    <td class="{clase_resultado}">{resultado[:40]}</td>
                </tr>
                """
            html += "</table>"
        else:
            html += """
            <div class="empty-state">
                <h3> No hay historial de llamadas aún</h3>
                <p>El historial aparecerá aquí cuando se realicen llamadas.</p>
                <p>Las estadísticas se acumulan mientras el servidor esté activo.</p>
            </div>
            """

        html += f"""
            <h2> Estado del Sistema</h2>
            <table>
                <tr><td>Audios en Caché</td><td><strong>{info_sistema['audios_en_cache']}</strong></td></tr>
                <tr><td>Frases Registradas</td><td><strong>{info_sistema['frases_registradas']}</strong></td></tr>
                <tr><td>Llamadas Activas</td><td><strong>{info_sistema['llamadas_activas']}</strong></td></tr>
                <tr><td>Total en Historial</td><td><strong>{info_sistema['historial_total']}</strong></td></tr>
            </table>

            <p style="text-align: center; color: #666; margin-top: 30px;">
                 El historial se guarda en memoria mientras el servidor esté activo.<br>
                Para ver logs completos de Railway, copia los logs desde el Dashboard de Railway.
            </p>
        </body>
        </html>
        """

        return html

    except Exception as e:
        return {
            "error": str(e),
            "message": "Error al cargar dashboard"
        }, 500


@app.route("/cache-manager", methods=["GET", "POST"])
def cache_manager():
    """
    FIX 56: Panel de administración del caché de respuestas de GPT
    GET: Muestra el panel con estadísticas y respuestas actuales
    POST: Permite agregar/editar/eliminar respuestas cacheadas
    """
    global respuestas_cache, cache_respuestas_stats

    if request.method == "POST":
        try:
            data = request.get_json()
            accion = data.get("accion")

            if accion == "agregar":
                categoria = data.get("categoria")
                patrones = data.get("patrones", [])  # Lista de strings
                respuesta = data.get("respuesta")

                if not categoria or not patrones or not respuesta:
                    return {"error": "Faltan campos requeridos"}, 400

                # Agregar nueva categoría al caché
                respuestas_cache[categoria] = {
                    "patrones": patrones,
                    "respuesta": respuesta
                }

                # Guardar en disco para persistencia
                cache_file = os.path.join(CACHE_DIR, "respuestas_cache.json")
                with open(cache_file, 'w', encoding='utf-8') as f:
                    json.dump(respuestas_cache, f, ensure_ascii=False, indent=2)

                # FIX 65: Pre-generar audio automáticamente para la nueva respuesta
                try:
                    print(f"\n FIX 65: Pre-generando audio para nueva categoría '{categoria}'...")
                    audio_id = f"cache_{categoria}"
                    generar_audio_elevenlabs(respuesta, audio_id, usar_cache_key=categoria)
                    print(f"    Audio pre-generado exitosamente")
                except Exception as e:
                    print(f"    Error pre-generando audio: {e}")
                    # No fallar si el audio falla, solo advertir

                return {"success": True, "message": f"Categoría '{categoria}' agregada y audio pre-generado"}

            elif accion == "eliminar":
                categoria = data.get("categoria")

                if categoria in respuestas_cache:
                    del respuestas_cache[categoria]

                    # Guardar en disco
                    cache_file = os.path.join(CACHE_DIR, "respuestas_cache.json")
                    with open(cache_file, 'w', encoding='utf-8') as f:
                        json.dump(respuestas_cache, f, ensure_ascii=False, indent=2)

                    return {"success": True, "message": f"Categoría '{categoria}' eliminada"}
                else:
                    return {"error": "Categoría no encontrada"}, 404

            else:
                return {"error": "Acción no válida"}, 400

        except Exception as e:
            return {"error": str(e)}, 500

    # GET: Mostrar panel HTML
    try:
        # Calcular tasa de aciertos del caché
        total = cache_respuestas_stats["total_consultas"]
        hits = cache_respuestas_stats["cache_hits"]
        misses = cache_respuestas_stats["cache_misses"]
        hit_rate = (hits / total * 100) if total > 0 else 0

        # Construir HTML del panel
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Bruce W - Gestor de Caché de Respuestas</title>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <style>
                body {{
                    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                    max-width: 1400px;
                    margin: 0 auto;
                    padding: 20px;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    min-height: 100vh;
                }}
                .container {{
                    background: white;
                    border-radius: 15px;
                    padding: 30px;
                    box-shadow: 0 10px 40px rgba(0,0,0,0.2);
                }}
                h1 {{
                    color: #667eea;
                    margin-bottom: 10px;
                    font-size: 2.5em;
                }}
                .subtitle {{
                    color: #666;
                    margin-bottom: 30px;
                }}
                .stats-grid {{
                    display: grid;
                    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                    gap: 20px;
                    margin-bottom: 40px;
                }}
                .stat-card {{
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    padding: 25px;
                    border-radius: 12px;
                    text-align: center;
                    box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4);
                }}
                .stat-number {{
                    font-size: 3em;
                    font-weight: bold;
                    margin-bottom: 10px;
                }}
                .stat-label {{
                    font-size: 1.1em;
                    opacity: 0.9;
                }}
                .category-list {{
                    margin-top: 30px;
                }}
                .category-item {{
                    background: #f8f9fa;
                    border-left: 4px solid #667eea;
                    padding: 20px;
                    margin-bottom: 15px;
                    border-radius: 8px;
                    transition: all 0.3s ease;
                }}
                .category-item:hover {{
                    transform: translateX(5px);
                    box-shadow: 0 4px 12px rgba(0,0,0,0.1);
                }}
                .category-header {{
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    margin-bottom: 15px;
                }}
                .category-name {{
                    font-size: 1.3em;
                    font-weight: bold;
                    color: #667eea;
                }}
                .delete-btn {{
                    background: #e74c3c;
                    color: white;
                    border: none;
                    padding: 8px 16px;
                    border-radius: 6px;
                    cursor: pointer;
                    font-size: 0.9em;
                    transition: background 0.3s;
                }}
                .delete-btn:hover {{
                    background: #c0392b;
                }}
                .patterns-list {{
                    background: white;
                    padding: 15px;
                    border-radius: 6px;
                    margin-bottom: 10px;
                }}
                .pattern-tag {{
                    display: inline-block;
                    background: #667eea;
                    color: white;
                    padding: 5px 12px;
                    border-radius: 20px;
                    margin: 5px;
                    font-size: 0.9em;
                }}
                .response-box {{
                    background: white;
                    padding: 15px;
                    border-radius: 6px;
                    border: 2px solid #e1e8ed;
                    font-style: italic;
                    color: #333;
                }}
                .usage-badge {{
                    background: #27ae60;
                    color: white;
                    padding: 5px 12px;
                    border-radius: 15px;
                    font-size: 0.85em;
                    font-weight: bold;
                }}
                .add-form {{
                    background: #f8f9fa;
                    padding: 25px;
                    border-radius: 12px;
                    margin-top: 40px;
                    border: 2px dashed #667eea;
                }}
                .form-group {{
                    margin-bottom: 20px;
                }}
                .form-label {{
                    display: block;
                    font-weight: bold;
                    color: #333;
                    margin-bottom: 8px;
                }}
                .form-input {{
                    width: 100%;
                    padding: 12px;
                    border: 2px solid #ddd;
                    border-radius: 6px;
                    font-size: 1em;
                    transition: border-color 0.3s;
                }}
                .form-input:focus {{
                    outline: none;
                    border-color: #667eea;
                }}
                .form-textarea {{
                    min-height: 100px;
                    resize: vertical;
                }}
                .btn-primary {{
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    border: none;
                    padding: 12px 30px;
                    border-radius: 8px;
                    font-size: 1.1em;
                    cursor: pointer;
                    transition: transform 0.2s;
                }}
                .btn-primary:hover {{
                    transform: translateY(-2px);
                    box-shadow: 0 6px 20px rgba(102, 126, 234, 0.4);
                }}
                .help-text {{
                    font-size: 0.9em;
                    color: #666;
                    margin-top: 5px;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1> Gestor de Caché de Respuestas</h1>
                <p class="subtitle">Administra respuestas pre-definidas para reducir latencia en preguntas comunes</p>

                <!-- Estadísticas -->
                <div class="stats-grid">
                    <div class="stat-card">
                        <div class="stat-number">{total}</div>
                        <div class="stat-label">Total Consultas</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-number">{hits}</div>
                        <div class="stat-label">Cache Hits</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-number">{misses}</div>
                        <div class="stat-label">Cache Misses</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-number">{hit_rate:.1f}%</div>
                        <div class="stat-label">Tasa de Aciertos</div>
                    </div>
                </div>

                <!-- Lista de categorías -->
                <div class="category-list">
                    <h2> Respuestas Cacheadas ({len(respuestas_cache)})</h2>
        """

        for categoria, datos in respuestas_cache.items():
            usos = cache_respuestas_stats["por_categoria"].get(categoria, 0)
            patrones_html = "".join([f'<span class="pattern-tag">{p}</span>' for p in datos["patrones"]])

            html += f"""
                    <div class="category-item">
                        <div class="category-header">
                            <span class="category-name">{categoria}</span>
                            <div>
                                <span class="usage-badge">{usos} usos</span>
                                <button class="delete-btn" onclick="eliminarCategoria('{categoria}')"> Eliminar</button>
                            </div>
                        </div>
                        <div class="patterns-list">
                            <strong>Patrones detectados:</strong><br>
                            {patrones_html}
                        </div>
                        <div class="response-box">
                            <strong>Respuesta:</strong><br>
                            "{datos['respuesta']}"
                        </div>
                    </div>
            """

        html += """
                </div>
        """

        # FIX 57: Mostrar candidatos de auto-caché (preguntas frecuentes)
        if candidatos_auto_cache or preguntas_frecuentes:
            html += """
                <!-- Candidatos de Auto-Caché -->
                <div class="category-list" style="margin-top: 40px;">
                    <h2> Candidatos de Auto-Caché (Preguntas Frecuentes)</h2>
                    <p style="color: #666; margin-bottom: 20px;">
                        Estas preguntas se han repetido {0} o más veces. Puedes agregarlas al caché para respuestas instantáneas.
                    </p>
            """.format(UMBRAL_AUTO_CACHE)

            # Mostrar candidatos que alcanzaron el umbral
            for pregunta_norm in candidatos_auto_cache:
                if pregunta_norm in preguntas_frecuentes:
                    datos = preguntas_frecuentes[pregunta_norm]
                    count = datos["count"]
                    pregunta_orig = datos["pregunta_original"]
                    ultima_resp = datos["ultima_respuesta"]

                    # Escapar comillas para JavaScript
                    pregunta_safe = pregunta_orig.replace('"', '\\"').replace("'", "\\'")
                    respuesta_safe = ultima_resp.replace('"', '\\"').replace("'", "\\'")

                    html += f"""
                    <div class="category-item" style="border-left-color: #f39c12;">
                        <div class="category-header">
                            <span class="category-name" style="color: #f39c12;"> "{pregunta_orig[:50]}..."</span>
                            <div>
                                <span class="usage-badge" style="background: #f39c12;">{count} veces</span>
                                <button class="btn-add-cache" onclick="agregarAlCache('{pregunta_safe}', '{respuesta_safe}')" style="margin-left: 10px; background: #27ae60; color: white; border: none; padding: 8px 16px; border-radius: 6px; cursor: pointer; font-weight: bold;">
                                     Agregar al Caché
                                </button>
                            </div>
                        </div>
                        <div class="response-box">
                            <strong>Última respuesta de Bruce:</strong><br>
                            "{ultima_resp}"
                        </div>
                        <div class="response-box" style="margin-top: 10px; background: #e8f5e9;">
                            <strong>Pregunta completa:</strong><br>
                            "{pregunta_orig}"
                        </div>
                    </div>
                    """

            # Mostrar top 5 preguntas que están cerca del umbral
            preguntas_cerca = [(k, v) for k, v in preguntas_frecuentes.items()
                             if v["count"] < UMBRAL_AUTO_CACHE and k not in candidatos_auto_cache]
            preguntas_cerca.sort(key=lambda x: x[1]["count"], reverse=True)

            if preguntas_cerca[:5]:
                html += """
                    <h3 style="margin-top: 30px; color: #666;"> Preguntas Emergentes</h3>
                """

                for pregunta_norm, datos in preguntas_cerca[:5]:
                    count = datos["count"]
                    pregunta_orig = datos["pregunta_original"]

                    html += f"""
                    <div style="background: #f8f9fa; padding: 15px; margin-bottom: 10px; border-radius: 8px; border-left: 3px solid #95a5a6;">
                        <strong>"{pregunta_orig[:60]}..."</strong>
                        <span style="background: #95a5a6; color: white; padding: 3px 10px; border-radius: 10px; margin-left: 10px; font-size: 0.85em;">
                            {count}/{UMBRAL_AUTO_CACHE}
                        </span>
                    </div>
                    """

            html += """
                </div>
            """

        html += """
                <!-- Formulario para agregar nueva categoría -->
                <div class="add-form">
                    <h2> Agregar Nueva Respuesta</h2>
                    <form id="addForm">
                        <div class="form-group">
                            <label class="form-label">Categoría (ID única)</label>
                            <input type="text" class="form-input" id="categoria" placeholder="ej: horario_atencion" required>
                            <p class="help-text">Identificador único sin espacios (usa guiones bajos)</p>
                        </div>

                        <div class="form-group">
                            <label class="form-label">Patrones (uno por línea)</label>
                            <textarea class="form-input form-textarea" id="patrones" placeholder="qué horario&#10;horario de atención&#10;a qué hora" required></textarea>
                            <p class="help-text">Frases que activan esta respuesta (una por línea, en minúsculas)</p>
                        </div>

                        <div class="form-group">
                            <label class="form-label">Respuesta de Bruce</label>
                            <textarea class="form-input form-textarea" id="respuesta" placeholder="Nuestro horario es de lunes a viernes de 8am a 5pm." required></textarea>
                            <p class="help-text">La respuesta exacta que Bruce dirá cuando detecte los patrones</p>
                        </div>

                        <button type="submit" class="btn-primary"> Guardar Respuesta</button>
                    </form>
                </div>
            </div>

            <script>
                // Agregar nueva categoría
                document.getElementById('addForm').addEventListener('submit', async (e) => {
                    e.preventDefault();

                    const categoria = document.getElementById('categoria').value.trim();
                    const patronesText = document.getElementById('patrones').value.trim();
                    const respuesta = document.getElementById('respuesta').value.trim();

                    // Convertir patrones de texto multilínea a array
                    const patrones = patronesText.split('\\n').map(p => p.trim()).filter(p => p.length > 0);

                    try {
                        const response = await fetch('/cache-manager', {
                            method: 'POST',
                            headers: {'Content-Type': 'application/json'},
                            body: JSON.stringify({
                                accion: 'agregar',
                                categoria: categoria,
                                patrones: patrones,
                                respuesta: respuesta
                            })
                        });

                        const result = await response.json();

                        if (response.ok) {
                            alert(' ' + result.message);
                            location.reload();
                        } else {
                            alert(' Error: ' + result.error);
                        }
                    } catch (error) {
                        alert(' Error: ' + error.message);
                    }
                });

                // FIX 65: Agregar candidato al caché con un click
                async function agregarAlCache(pregunta, respuesta) {
                    // Pre-llenar el formulario con los datos del candidato
                    const categoria = prompt('Ingresa un ID único para esta categoría (ej: horario_atencion):',
                        pregunta.toLowerCase()
                            .replace(/[¿?¡!]/g, '')
                            .replace(/\\s+/g, '_')
                            .substring(0, 30)
                    );

                    if (!categoria) return;

                    // Usar la pregunta como patrón principal
                    const patrones = [pregunta.toLowerCase().replace(/[¿?¡!]/g, '').trim()];

                    try {
                        const response = await fetch('/cache-manager', {
                            method: 'POST',
                            headers: {'Content-Type': 'application/json'},
                            body: JSON.stringify({
                                accion: 'agregar',
                                categoria: categoria,
                                patrones: patrones,
                                respuesta: respuesta
                            })
                        });

                        const result = await response.json();

                        if (response.ok) {
                            alert(' Agregado al caché! El audio se pre-generará automáticamente.');
                            location.reload();
                        } else {
                            alert(' Error: ' + result.error);
                        }
                    } catch (error) {
                        alert(' Error: ' + error.message);
                    }
                }

                // Eliminar categoría
                async function eliminarCategoria(categoria) {
                    if (!confirm(`¿Seguro que deseas eliminar la categoría "${categoria}"?`)) {
                        return;
                    }

                    try {
                        const response = await fetch('/cache-manager', {
                            method: 'POST',
                            headers: {'Content-Type': 'application/json'},
                            body: JSON.stringify({
                                accion: 'eliminar',
                                categoria: categoria
                            })
                        });

                        const result = await response.json();

                        if (response.ok) {
                            alert(' ' + result.message);
                            location.reload();
                        } else {
                            alert(' Error: ' + result.error);
                        }
                    } catch (error) {
                        alert(' Error: ' + error.message);
                    }
                }
            </script>
        </body>
        </html>
        """

        return html

    except Exception as e:
        return {
            "error": str(e),
            "message": "Error al cargar el gestor de caché"
        }, 500


# ============================================================================
# FIX 208: SISTEMA DE LOGS DESCARGABLES
# Guarda eventos importantes en memoria y permite descargarlos via HTTP
# NO intercepta stdout para evitar conflictos con Gunicorn
# ============================================================================

import threading

# Buffer circular para logs (últimas 50000 líneas)
# FIX 403: Aumentado de 5000 a 50000 para tener logs completos como Railway
log_buffer = deque(maxlen=50000)
log_lock = threading.Lock()

# FIX 272.9: Archivo para persistir logs entre deploys
LOGS_FILE = os.path.join(CACHE_DIR, "logs_llamadas.json")

def cargar_logs():
    """Carga los logs guardados desde archivo JSON"""
    try:
        if os.path.exists(LOGS_FILE):
            with open(LOGS_FILE, 'r', encoding='utf-8') as f:
                datos = json.load(f)
                return deque(datos, maxlen=5000)
    except Exception as e:
        print(f" FIX 272.9: Error cargando logs: {e}")
    return deque(maxlen=5000)

def guardar_logs():
    """Guarda los logs en archivo JSON para persistir entre deploys"""
    try:
        os.makedirs(os.path.dirname(LOGS_FILE), exist_ok=True)
        with open(LOGS_FILE, 'w', encoding='utf-8') as f:
            json.dump(list(log_buffer), f, ensure_ascii=False)
        return True
    except Exception as e:
        print(f" FIX 272.9: Error guardando logs: {e}")
        return False

# Cargar logs al iniciar
log_buffer = cargar_logs()
print(f" FIX 272.9: {len(log_buffer)} logs cargados")

# Contador para guardar logs cada N entradas
_log_counter = 0

def log_evento(mensaje, tipo="INFO"):
    """
    Registra un evento en el buffer de logs
    Usar esta función para eventos importantes que queremos rastrear

    Args:
        mensaje: El mensaje a registrar
        tipo: INFO, ERROR, WARNING, BRUCE, CLIENTE, etc.
    """
    global _log_counter
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{timestamp}] [{tipo}] {mensaje}"

    with log_lock:
        log_buffer.append(log_entry)
        _log_counter += 1

        # FIX 272.9: Guardar cada 10 logs para no escribir en cada entrada
        if _log_counter >= 10:
            guardar_logs()
            _log_counter = 0

    # También imprimir para logs de Railway
    print(log_entry)


# FIX 403: Interceptar TODOS los prints para capturarlos en log_buffer
class LogCapture:
    """Captura TODOS los outputs de print() y los agrega al buffer de logs"""
    def __init__(self, original_stdout):
        self.original_stdout = original_stdout
        self.buffer = ""

    def write(self, text):
        # Escribir a stdout original (Railway)
        self.original_stdout.write(text)
        self.original_stdout.flush()

        # Capturar en buffer
        if text and text.strip():  # Solo capturar si no es vacío
            with log_lock:
                # Agregar timestamp si no lo tiene
                if not text.startswith('['):
                    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    text = f"[{timestamp}] {text.strip()}"
                else:
                    text = text.strip()

                log_buffer.append(text)

    def flush(self):
        self.original_stdout.flush()

    def isatty(self):
        """Necesario para compatibilidad con Click/Flask"""
        return self.original_stdout.isatty()

    def __getattr__(self, name):
        """Delegar cualquier otro método/atributo al stdout original"""
        return getattr(self.original_stdout, name)

# FIX 403: Activar captura de logs
import sys
original_stdout = sys.stdout
sys.stdout = LogCapture(original_stdout)
print(" FIX 403: Captura de logs activada - TODOS los prints se guardarán en buffer")


# ============================================================================
# FIX 272: DASHBOARD DE HISTORIAL CON CALIFICACIONES Y SEMÁFOROS
# ============================================================================

# Archivo para persistir calificaciones entre deploys
CALIFICACIONES_FILE = os.path.join(CACHE_DIR, "calificaciones_llamadas.json")

def cargar_calificaciones():
    """Carga las calificaciones guardadas desde el archivo JSON"""
    try:
        if os.path.exists(CALIFICACIONES_FILE):
            with open(CALIFICACIONES_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        print(f" FIX 272: Error cargando calificaciones: {e}")
    return {}

def guardar_calificaciones(calificaciones):
    """Guarda las calificaciones en archivo JSON para persistir entre deploys"""
    try:
        os.makedirs(os.path.dirname(CALIFICACIONES_FILE), exist_ok=True)
        with open(CALIFICACIONES_FILE, 'w', encoding='utf-8') as f:
            json.dump(calificaciones, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f" FIX 272: Error guardando calificaciones: {e}")
        return False

# Cargar calificaciones al iniciar
calificaciones_llamadas = cargar_calificaciones()
print(f" FIX 272: {len(calificaciones_llamadas)} calificaciones cargadas")


@app.route("/historial-llamadas", methods=["GET"])
def historial_llamadas_dashboard():
    """
    FIX 272: Dashboard de historial de llamadas con:
    - Semáforos de calificación (Verde/Amarillo/Rojo)
    - Campo de notas para errores
    - Link directo a grabación de Twilio
    - Persistencia entre deploys
    """
    global calificaciones_llamadas

    # Recargar calificaciones por si cambiaron
    calificaciones_llamadas = cargar_calificaciones()

    # Obtener historial
    historial = list(historial_llamadas)
    historial = list(reversed(historial))  # Más recientes primero

    # Estadísticas de semáforos
    total = len(calificaciones_llamadas)
    verdes = sum(1 for c in calificaciones_llamadas.values() if c.get('semaforo') == 'verde')
    amarillos = sum(1 for c in calificaciones_llamadas.values() if c.get('semaforo') == 'amarillo')
    rojos = sum(1 for c in calificaciones_llamadas.values() if c.get('semaforo') == 'rojo')
    naranjas = sum(1 for c in calificaciones_llamadas.values() if c.get('semaforo') == 'naranja')  # FIX 282: Buzón
    azules = sum(1 for c in calificaciones_llamadas.values() if c.get('semaforo') == 'azul')  # FIX 282: Contestadora
    sin_calificar = len(historial) - total

    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title> Historial de Llamadas - Bruce W</title>
        <meta charset="UTF-8">
        <style>
            * { box-sizing: border-box; }
            body {
                font-family: 'Segoe UI', Arial, sans-serif;
                background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
                color: #eee;
                margin: 0;
                padding: 20px;
                min-height: 100vh;
            }
            h1 {
                color: #4CAF50;
                text-align: center;
                margin-bottom: 10px;
            }
            .subtitle {
                text-align: center;
                color: #888;
                margin-bottom: 30px;
            }

            /* Estadísticas de semáforos */
            .stats-semaforos {
                display: flex;
                justify-content: center;
                gap: 20px;
                margin-bottom: 30px;
                flex-wrap: wrap;
            }
            .stat-item {
                padding: 15px 30px;
                border-radius: 10px;
                text-align: center;
                min-width: 100px;
            }
            .stat-verde { background: rgba(76, 175, 80, 0.3); border: 2px solid #4CAF50; }
            .stat-amarillo { background: rgba(255, 193, 7, 0.3); border: 2px solid #FFC107; }
            .stat-rojo { background: rgba(244, 67, 54, 0.3); border: 2px solid #f44336; }
            .stat-naranja { background: rgba(255, 152, 0, 0.3); border: 2px solid #FF9800; }
            .stat-azul { background: rgba(33, 150, 243, 0.3); border: 2px solid #2196F3; }
            .stat-gris { background: rgba(158, 158, 158, 0.3); border: 2px solid #9e9e9e; }
            .stat-item .numero { font-size: 2em; font-weight: bold; display: block; }
            .stat-item .label { font-size: 0.85em; opacity: 0.8; }

            /* Tabla principal */
            .tabla-container {
                overflow-x: auto;
                background: #16213e;
                border-radius: 15px;
                padding: 20px;
                box-shadow: 0 4px 20px rgba(0,0,0,0.3);
            }
            table {
                width: 100%;
                border-collapse: collapse;
            }
            th {
                background: #0f3460;
                padding: 15px 10px;
                text-align: left;
                font-weight: 600;
                position: sticky;
                top: 0;
            }
            td {
                padding: 12px 10px;
                border-bottom: 1px solid #1a1a2e;
                vertical-align: middle;
            }
            tr:hover { background: rgba(33, 150, 243, 0.1); }

            /* Semáforos */
            .semaforo {
                display: flex;
                gap: 8px;
                align-items: center;
            }
            .semaforo-btn {
                width: 28px;
                height: 28px;
                border-radius: 50%;
                border: 2px solid transparent;
                cursor: pointer;
                transition: all 0.2s;
                opacity: 0.4;
            }
            .semaforo-btn:hover { opacity: 0.8; transform: scale(1.1); }
            .semaforo-btn.activo { opacity: 1; border-color: white; box-shadow: 0 0 10px currentColor; }
            .btn-verde { background: #4CAF50; }
            .btn-amarillo { background: #FFC107; }
            .btn-rojo { background: #f44336; }
            .btn-naranja { background: #FF9800; }
            .btn-azul { background: #2196F3; }

            /* Campo de notas */
            .notas-input {
                width: 100%;
                min-width: 150px;
                padding: 8px;
                border: 1px solid #333;
                border-radius: 5px;
                background: #1a1a2e;
                color: #eee;
                font-size: 12px;
                resize: vertical;
            }
            .notas-input:focus {
                outline: none;
                border-color: #4CAF50;
            }

            /* Link grabación */
            .link-grabacion {
                color: #2196F3;
                text-decoration: none;
                font-size: 12px;
            }
            .link-grabacion:hover { text-decoration: underline; }

            /* Resultado badges */
            .badge {
                padding: 4px 10px;
                border-radius: 12px;
                font-size: 11px;
                font-weight: 600;
            }
            .badge-exito { background: #4CAF50; color: white; }
            .badge-ivr { background: #ff9800; color: white; }
            .badge-nocontesto { background: #9e9e9e; color: white; }
            .badge-negado { background: #f44336; color: white; }

            /* Botón guardar flotante */
            .btn-guardar {
                position: fixed;
                bottom: 30px;
                right: 30px;
                padding: 15px 30px;
                background: #4CAF50;
                color: white;
                border: none;
                border-radius: 30px;
                cursor: pointer;
                font-size: 16px;
                box-shadow: 0 4px 15px rgba(76, 175, 80, 0.4);
                transition: all 0.3s;
                z-index: 1000;
            }
            .btn-guardar:hover { transform: scale(1.05); background: #45a049; }
            .btn-guardar:disabled { background: #666; cursor: not-allowed; }

            /* Mensaje de guardado */
            .mensaje-guardado {
                position: fixed;
                top: 20px;
                right: 20px;
                padding: 15px 25px;
                background: #4CAF50;
                color: white;
                border-radius: 10px;
                display: none;
                z-index: 1001;
                animation: slideIn 0.3s ease;
            }
            @keyframes slideIn {
                from { transform: translateX(100px); opacity: 0; }
                to { transform: translateX(0); opacity: 1; }
            }

            /* Responsive */
            @media (max-width: 768px) {
                .stats-semaforos { gap: 10px; }
                .stat-item { padding: 10px 20px; min-width: 70px; }
                th, td { padding: 8px 5px; font-size: 12px; }
            }

            .empty-state {
                text-align: center;
                padding: 50px;
                color: #666;
            }

            .nav-links {
                text-align: center;
                margin-bottom: 20px;
            }
            .nav-links a {
                color: #4CAF50;
                margin: 0 15px;
                text-decoration: none;
            }
            .nav-links a:hover { text-decoration: underline; }

            /* FIX 272.4: Checkbox Solucionado */
            .checkbox-solucionado {
                display: flex;
                align-items: center;
                justify-content: center;
                cursor: pointer;
            }
            .checkbox-solucionado input {
                width: 20px;
                height: 20px;
                cursor: pointer;
                accent-color: #4CAF50;
            }
            .fila-solucionada {
                background: rgba(76, 175, 80, 0.15) !important;
                opacity: 0.7;
            }
            .fila-solucionada td {
                text-decoration: line-through;
                color: #888;
            }
            .fila-solucionada .badge,
            .fila-solucionada .semaforo-btn,
            .fila-solucionada .notas-input,
            .fila-solucionada .link-grabacion {
                text-decoration: none;
            }

            /* Semáforo guardado */
            .semaforo-guardado {
                font-size: 24px;
                display: inline-block;
            }
        </style>
    </head>
    <body>
        <h1> Historial de Llamadas - Bruce W</h1>
        <p class="subtitle">Panel de calificación con semáforos y notas</p>

        <div class="nav-links">
            <a href="/logs"> Dashboard Principal</a>
            <a href="/stats"> Estadísticas</a>
            <a href="/historial-llamadas"> Refrescar</a>
        </div>

        <div class="stats-semaforos">
            <div class="stat-item stat-verde">
                <span class="numero">""" + str(verdes) + """</span>
                <span class="label">🟢 Bueno</span>
            </div>
            <div class="stat-item stat-amarillo">
                <span class="numero">""" + str(amarillos) + """</span>
                <span class="label">🟡 Medio</span>
            </div>
            <div class="stat-item stat-rojo">
                <span class="numero">""" + str(rojos) + """</span>
                <span class="label"> Malo</span>
            </div>
            <div class="stat-item stat-naranja">
                <span class="numero">""" + str(naranjas) + """</span>
                <span class="label">🟠 Buzón</span>
            </div>
            <div class="stat-item stat-azul">
                <span class="numero">""" + str(azules) + """</span>
                <span class="label"> Contestadora</span>
            </div>
            <div class="stat-item stat-gris">
                <span class="numero">""" + str(max(0, sin_calificar)) + """</span>
                <span class="label"> Sin calificar</span>
            </div>
        </div>

        <div class="mensaje-guardado" id="mensajeGuardado"> Calificaciones guardadas</div>

        <div class="tabla-container">
    """

    if historial:
        html += """
            <div class="filtros" style="margin-bottom: 15px; padding: 10px; background: #2a2a2a; border-radius: 8px;">
                <label style="color: #fff; margin-right: 10px;"> Filtrar por Estado:</label>
                <select id="filtroEstado" onchange="filtrarPorEstado()" style="padding: 8px; border-radius: 5px; background: #333; color: #fff; border: 1px solid #555;">
                    <option value="todos">Todos</option>
                    <option value="verde">🟢 Bueno</option>
                    <option value="amarillo">🟡 Medio</option>
                    <option value="rojo"> Malo</option>
                    <option value="naranja">🟠 Buzón</option>
                    <option value="azul"> Contestadora</option>
                    <option value="sin_calificar"> Sin calificar</option>
                </select>
            </div>
            <table>
                <tr>
                    <th>Fecha/Hora</th>
                    <th>BRUCE ID</th>
                    <th>Negocio</th>
                    <th>Teléfono</th>
                    <th>Resultado</th>
                    <th>Duración</th>
                    <th>Colgó</th>
                    <th>Grabación</th>
                    <th>Semáforo</th>
                    <th>Notas del Error</th>
                    <th>Solucionado</th>
                    <th>Estado</th>
                    <th>Deploy</th>
                </tr>
        """

        for llamada in historial[:100]:  # Últimas 100
            bruce_id = llamada.get('bruce_id', 'N/A')
            call_id = bruce_id  # Usar bruce_id como identificador único

            # Obtener calificación guardada
            calif = calificaciones_llamadas.get(call_id, {})
            semaforo_actual = calif.get('semaforo', '')
            notas_actual = calif.get('notas', '')
            solucionado_actual = calif.get('solucionado', False)  # FIX 272.4: Campo solucionado

            # Determinar badge de resultado
            resultado = llamada.get('resultado', 'N/A')
            resultado_lower = resultado.lower()
            if 'catálogo' in resultado_lower or 'éxito' in resultado_lower:
                badge_class = 'badge-exito'
            elif 'ivr' in resultado_lower:
                badge_class = 'badge-ivr'
            elif 'no contestó' in resultado_lower:
                badge_class = 'badge-nocontesto'
            elif 'negado' in resultado_lower or 'rechaz' in resultado_lower:
                badge_class = 'badge-negado'
            else:
                badge_class = ''

            # URL de grabación - buscar en detalles o en mapeo global
            detalles = llamada.get('detalles', {})
            recording_url = detalles.get('recording_url', '') or grabaciones_por_bruce.get(bruce_id, '')

            # FIX 272.6: Extraer Recording SID para link directo
            recording_sid = ""
            if recording_url and "/Recordings/" in recording_url:
                recording_sid = recording_url.split("/Recordings/")[-1].split(".")[0]

            # Link al proxy local que sirve el audio con autenticación
            link_grabacion = f"/escuchar-grabacion/{recording_sid}" if recording_sid else ""

            # FIX 272.8: Link a logs filtrados por bruce_id
            link_logs = f"/logs/api?bruce_id={bruce_id.replace('BRUCE', '')}" if bruce_id and bruce_id != 'N/A' else ""

            # FIX 282: Obtener nombre del deploy de la llamada
            deploy_name = llamada.get('deploy_name', '')
            deploy_llamada = llamada.get('deploy_id', '')
            # FIX 282: Prioridad: deploy_name > deploy_id > "Anterior"
            if deploy_name:
                deploy_display = deploy_name[:12]  # Máximo 12 caracteres
            elif deploy_llamada:
                deploy_display = deploy_llamada[-5:]  # Solo HH:MM como fallback
            else:
                deploy_display = "Anterior"
                deploy_llamada = "Pre-272.10"

            # Estado para el filtro
            estado_filtro = semaforo_actual if semaforo_actual else 'sin_calificar'

            # FIX 517: Determinar quién colgó (C=Cliente, B=Bruce, -=N/A)
            quien_colgo = "-"
            if 'colgo' in resultado_lower or 'colgó' in resultado_lower:
                quien_colgo = "C"  # Cliente colgó
            elif 'catálogo' in resultado_lower or 'éxito' in resultado_lower or 'despedida' in resultado_lower:
                quien_colgo = "B"  # Bruce terminó exitosamente
            elif 'nulo' in resultado_lower and llamada.get('duracion', 0) > 30:
                quien_colgo = "C"  # Llamada larga sin resultado = cliente colgó

            html += f"""
                <tr data-call-id="{call_id}" data-estado="{estado_filtro}" class="{'fila-solucionada' if solucionado_actual else ''}">
                    <td style="font-size: 11px; white-space: nowrap;">{llamada.get('timestamp', 'N/A')}</td>
                    <td><a href="{link_logs}" target="_blank" style="color: #4CAF50; text-decoration: none;" title="Ver logs de esta llamada"><strong>{bruce_id}</strong> </a></td>
                    <td title="{llamada.get('negocio', 'N/A')}">{llamada.get('negocio', 'N/A')[:25]}...</td>
                    <td style="font-size: 12px;">{llamada.get('telefono', 'N/A')}</td>
                    <td><span class="badge {badge_class}">{resultado[:20]}</span></td>
                    <td>{llamada.get('duracion', 0)}s</td>
                    <td style="text-align:center; font-weight:bold; color:{'#f44336' if quien_colgo == 'C' else '#4CAF50' if quien_colgo == 'B' else '#666'};">{quien_colgo}</td>
                    <td>
                        {'<audio controls preload="none" style="width:150px; height:32px;"><source src="' + link_grabacion + '" type="audio/mpeg">Tu navegador no soporta audio</audio>' if link_grabacion else '<span style="color:#666">-</span>'}
                    </td>
                    <td>
                        <div class="semaforo">
                            <button class="semaforo-btn btn-verde {'activo' if semaforo_actual == 'verde' else ''}"
                                    onclick="setSemaforo('{call_id}', 'verde', this)" title="Bueno">
                            </button>
                            <button class="semaforo-btn btn-amarillo {'activo' if semaforo_actual == 'amarillo' else ''}"
                                    onclick="setSemaforo('{call_id}', 'amarillo', this)" title="Medio">
                            </button>
                            <button class="semaforo-btn btn-rojo {'activo' if semaforo_actual == 'rojo' else ''}"
                                    onclick="setSemaforo('{call_id}', 'rojo', this)" title="Malo">
                            </button>
                            <button class="semaforo-btn btn-naranja {'activo' if semaforo_actual == 'naranja' else ''}"
                                    onclick="setSemaforo('{call_id}', 'naranja', this)" title="Buzón">
                            </button>
                            <button class="semaforo-btn btn-azul {'activo' if semaforo_actual == 'azul' else ''}"
                                    onclick="setSemaforo('{call_id}', 'azul', this)" title="Contestadora">
                            </button>
                        </div>
                    </td>
                    <td>
                        <textarea class="notas-input"
                                  placeholder="Anotar error..."
                                  onchange="setNotas('{call_id}', this.value)"
                                  rows="2">{notas_actual}</textarea>
                    </td>
                    <td style="text-align: center;">
                        <label class="checkbox-solucionado">
                            <input type="checkbox" {'checked' if solucionado_actual else ''}
                                   onchange="setSolucionado('{call_id}', this.checked)">
                            <span class="checkmark"></span>
                        </label>
                    </td>
                    <td style="text-align: center;">
                        <span class="semaforo-guardado" data-call-id="{call_id}">
                            {'🟢' if semaforo_actual == 'verde' else '🟡' if semaforo_actual == 'amarillo' else '' if semaforo_actual == 'rojo' else '🟠' if semaforo_actual == 'naranja' else '' if semaforo_actual == 'azul' else ''}
                        </span>
                    </td>
                    <td style="font-size: 10px; color: #888;" title="{deploy_llamada}">{deploy_display}</td>
                </tr>
            """

        html += "</table>"
    else:
        html += """
            <div class="empty-state">
                <h3> No hay historial de llamadas</h3>
                <p>El historial aparecerá aquí cuando se realicen llamadas.</p>
            </div>
        """

    html += """
        </div>

        <button class="btn-guardar" onclick="guardarTodo()"> Guardar Calificaciones</button>

        <script>
            // Almacenar cambios pendientes
            let cambiosPendientes = {};

            // FIX 272.10: Filtrar filas por estado del semáforo
            function filtrarPorEstado() {
                const filtro = document.getElementById('filtroEstado').value;
                const filas = document.querySelectorAll('table tr[data-call-id]');

                filas.forEach(fila => {
                    const estado = fila.getAttribute('data-estado') || 'sin_calificar';
                    if (filtro === 'todos' || estado === filtro) {
                        fila.style.display = '';
                    } else {
                        fila.style.display = 'none';
                    }
                });
            }

            function setSemaforo(callId, color, btn) {
                // Quitar activo de hermanos
                const fila = btn.closest('tr');
                fila.querySelectorAll('.semaforo-btn').forEach(b => b.classList.remove('activo'));
                btn.classList.add('activo');

                // Registrar cambio
                if (!cambiosPendientes[callId]) cambiosPendientes[callId] = {};
                cambiosPendientes[callId].semaforo = color;

                // Indicador visual de cambio pendiente
                const colores = { 'verde': '#4CAF50', 'amarillo': '#FFC107', 'rojo': '#f44336', 'naranja': '#FF9800', 'azul': '#2196F3' };
                btn.style.boxShadow = '0 0 15px ' + (colores[color] || '#999');

                // Actualizar el emoji del estado guardado
                const estadoSpan = fila.querySelector('.semaforo-guardado');
                if (estadoSpan) {
                    const emojis = { 'verde': '🟢', 'amarillo': '🟡', 'rojo': '', 'naranja': '🟠', 'azul': '' };
                    estadoSpan.textContent = emojis[color] || '';
                }

                // FIX 272.10: Actualizar data-estado para el filtro
                fila.setAttribute('data-estado', color);
            }

            function setNotas(callId, notas) {
                if (!cambiosPendientes[callId]) cambiosPendientes[callId] = {};
                cambiosPendientes[callId].notas = notas;
            }

            function setSolucionado(callId, checked) {
                if (!cambiosPendientes[callId]) cambiosPendientes[callId] = {};
                cambiosPendientes[callId].solucionado = checked;

                // Actualizar visualmente la fila
                const fila = document.querySelector(`tr[data-call-id="${callId}"]`);
                if (fila) {
                    if (checked) {
                        fila.classList.add('fila-solucionada');
                    } else {
                        fila.classList.remove('fila-solucionada');
                    }
                }
            }

            async function guardarTodo() {
                const btn = document.querySelector('.btn-guardar');
                btn.disabled = true;
                btn.textContent = ' Guardando...';

                try {
                    const response = await fetch('/historial-llamadas/guardar', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify(cambiosPendientes)
                    });

                    const data = await response.json();

                    if (data.success) {
                        // Mostrar mensaje de éxito
                        const msg = document.getElementById('mensajeGuardado');
                        msg.style.display = 'block';
                        setTimeout(() => { msg.style.display = 'none'; }, 3000);

                        // Limpiar cambios pendientes
                        cambiosPendientes = {};

                        // Recargar para actualizar estadísticas
                        setTimeout(() => location.reload(), 1000);
                    } else {
                        alert('Error al guardar: ' + data.error);
                    }
                } catch (e) {
                    alert('Error de conexión: ' + e.message);
                }

                btn.disabled = false;
                btn.textContent = ' Guardar Calificaciones';
            }
        </script>
    </body>
    </html>
    """

    return html


@app.route("/historial-llamadas/guardar", methods=["POST"])
def guardar_calificaciones_endpoint():
    """
    FIX 272: Endpoint para guardar calificaciones de llamadas
    Persiste en JSON para sobrevivir deploys
    """
    global calificaciones_llamadas

    try:
        datos = request.get_json()

        if not datos:
            return {"success": False, "error": "No hay datos"}, 400

        # Recargar calificaciones actuales
        calificaciones_llamadas = cargar_calificaciones()

        # Actualizar con nuevos datos
        for call_id, calif in datos.items():
            if call_id not in calificaciones_llamadas:
                calificaciones_llamadas[call_id] = {}

            if 'semaforo' in calif:
                calificaciones_llamadas[call_id]['semaforo'] = calif['semaforo']
            if 'notas' in calif:
                calificaciones_llamadas[call_id]['notas'] = calif['notas']
            if 'solucionado' in calif:  # FIX 272.4: Guardar campo solucionado
                calificaciones_llamadas[call_id]['solucionado'] = calif['solucionado']

            calificaciones_llamadas[call_id]['fecha_actualizacion'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Guardar en archivo
        if guardar_calificaciones(calificaciones_llamadas):
            print(f" FIX 272: {len(datos)} calificaciones guardadas")
            return {"success": True, "guardados": len(datos)}
        else:
            return {"success": False, "error": "Error al escribir archivo"}, 500

    except Exception as e:
        print(f" FIX 272: Error guardando calificaciones: {e}")
        return {"success": False, "error": str(e)}, 500


@app.route("/escuchar-grabacion/<recording_sid>", methods=["GET"])
def escuchar_grabacion(recording_sid):
    """
    FIX 272.6: Proxy para servir grabaciones de Twilio con autenticación
    Permite escuchar grabaciones directamente sin necesidad de login en Twilio
    """
    try:
        if not recording_sid or recording_sid == "undefined":
            return "Recording SID no válido", 400

        # Construir URL de Twilio con autenticación
        twilio_url = f"https://api.twilio.com/2010-04-01/Accounts/{TWILIO_ACCOUNT_SID}/Recordings/{recording_sid}.mp3"

        # Descargar audio con autenticación
        response = requests.get(
            twilio_url,
            auth=(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN),
            stream=True,
            timeout=30
        )

        if response.status_code == 200:
            # Servir el audio directamente
            return Response(
                response.content,
                mimetype='audio/mpeg',
                headers={
                    'Content-Disposition': f'inline; filename="{recording_sid}.mp3"'
                }
            )
        else:
            print(f" FIX 272.6: Error descargando grabación {recording_sid}: {response.status_code}")
            return f"Error al obtener grabación: {response.status_code}", response.status_code

    except Exception as e:
        print(f" FIX 272.6: Error en proxy de grabación: {e}")
        return f"Error: {str(e)}", 500


@app.route("/logs/download", methods=["GET"])
def descargar_logs():
    """
    FIX 208: Endpoint para descargar logs del servidor
    Permite descargar los últimos logs como archivo de texto

    Params:
        - lineas: número de líneas a descargar (default: 1000, max: 5000)
        - formato: 'txt' o 'json' (default: txt)
    """
    try:
        lineas = min(int(request.args.get('lineas', 1000)), 5000)
        formato = request.args.get('formato', 'txt')

        with log_lock:
            logs_list = list(log_buffer)[-lineas:]

        if formato == 'json':
            return {
                "total_logs": len(log_buffer),
                "logs_solicitados": lineas,
                "logs": logs_list
            }

        # Formato texto plano para descarga
        logs_texto = "\n".join(logs_list)

        # Crear respuesta con headers para descarga
        response = app.response_class(
            response=logs_texto,
            status=200,
            mimetype='text/plain'
        )

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        response.headers['Content-Disposition'] = f'attachment; filename=logs_bruce_{timestamp}.txt'

        return response

    except Exception as e:
        return {"error": str(e)}, 500


@app.route("/logs/view", methods=["GET"])
def ver_logs_texto():
    """
    FIX 208: Ver logs en texto plano en el navegador
    Útil para copiar/pegar o ver en tiempo real
    """
    try:
        lineas = min(int(request.args.get('lineas', 500)), 5000)
        filtro = request.args.get('filtro', '').lower()

        with log_lock:
            logs_list = list(log_buffer)[-lineas:]

        # Aplicar filtro si existe
        if filtro:
            logs_list = [l for l in logs_list if filtro in l.lower()]

        # HTML simple para visualizar
        logs_html = "<br>".join(logs_list[-500:])  # Limitar a 500 en HTML

        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title> Logs Bruce W</title>
            <meta charset="UTF-8">
            <meta http-equiv="refresh" content="10">
            <style>
                body {{
                    font-family: 'Consolas', 'Monaco', monospace;
                    background: #1e1e1e;
                    color: #d4d4d4;
                    padding: 20px;
                    font-size: 12px;
                    line-height: 1.4;
                }}
                h1 {{
                    color: #4EC9B0;
                    font-family: Arial, sans-serif;
                }}
                .controls {{
                    background: #2d2d2d;
                    padding: 15px;
                    border-radius: 8px;
                    margin-bottom: 20px;
                }}
                .controls a {{
                    color: #569cd6;
                    margin-right: 20px;
                }}
                input {{
                    background: #3c3c3c;
                    border: 1px solid #555;
                    color: white;
                    padding: 8px;
                    border-radius: 4px;
                    margin-left: 10px;
                }}
                .logs {{
                    background: #1e1e1e;
                    padding: 15px;
                    border-radius: 8px;
                    border: 1px solid #333;
                    white-space: pre-wrap;
                    word-wrap: break-word;
                    max-height: 80vh;
                    overflow-y: auto;
                }}
                .highlight-error {{ color: #f44747; }}
                .highlight-warning {{ color: #dcdcaa; }}
                .highlight-bruce {{ color: #4ec9b0; }}
                .highlight-cliente {{ color: #ce9178; }}
            </style>
        </head>
        <body>
            <h1> Logs en Tiempo Real - Bruce W</h1>

            <div class="controls">
                <strong>Descargar:</strong>
                <a href="/logs/download?lineas=1000"> Últimos 1000</a>
                <a href="/logs/download?lineas=5000"> Todos (5000)</a>
                <a href="/logs/download?formato=json&lineas=1000"> JSON</a>
                |
                <strong>Filtrar:</strong>
                <form style="display:inline" method="get">
                    <input type="text" name="filtro" placeholder="ej: BRUCE, error, cliente" value="{filtro}">
                    <input type="hidden" name="lineas" value="{lineas}">
                    <button type="submit">Filtrar</button>
                </form>
                |
                <a href="/logs/view?lineas=100">100 líneas</a>
                <a href="/logs/view?lineas=500">500 líneas</a>
                <a href="/logs/view?lineas=2000">2000 líneas</a>
            </div>

            <div class="logs">
                <strong> Total en buffer: {len(log_buffer)} | Mostrando: {len(logs_list)} líneas</strong>
                <br><br>
                {logs_html}
            </div>

            <script>
                // Scroll al final automáticamente
                var logsDiv = document.querySelector('.logs');
                logsDiv.scrollTop = logsDiv.scrollHeight;
            </script>
        </body>
        </html>
        """

        return html

    except Exception as e:
        return {"error": str(e)}, 500


@app.route("/logs/api", methods=["GET"])
def logs_api():
    """
    FIX 208/272.8/395: API para obtener logs - ahora soporta HTML y JSON
    """
    try:
        # FIX 395/403: Si se filtra por bruce_id, buscar en TODO el buffer (50000 logs)
        bruce_id = request.args.get('bruce_id', '')
        if bruce_id:
            lineas = 50000  # FIX 403: Buscar en todo el buffer para logs completos
        else:
            lineas = min(int(request.args.get('lineas', 500)), 50000)

        filtro = request.args.get('filtro', '').lower()
        formato = request.args.get('formato', 'html')  # FIX 272.8: Por defecto HTML

        with log_lock:
            logs_list = list(log_buffer)[-lineas:]

        # Filtrar por texto
        if filtro:
            logs_list = [l for l in logs_list if filtro in l.lower()]

        # Filtrar por BRUCE ID
        if bruce_id:
            logs_list = [l for l in logs_list if f"BRUCE{bruce_id}" in l or f"bruce{bruce_id}" in l.lower()]

        # FIX 272.8: Si formato es JSON, devolver JSON
        if formato == 'json':
            return {
                "success": True,
                "total_en_buffer": len(log_buffer),
                "logs_filtrados": len(logs_list),
                "filtro": filtro,
                "bruce_id": bruce_id,
                "logs": logs_list
            }

        # FIX 272.8: Por defecto devolver HTML bonito
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title> Logs BRUCE{bruce_id}</title>
            <meta charset="UTF-8">
            <style>
                body {{
                    font-family: 'Consolas', 'Monaco', monospace;
                    background: #1a1a2e;
                    color: #eee;
                    margin: 0;
                    padding: 20px;
                }}
                h1 {{ color: #4CAF50; }}
                .nav {{ margin-bottom: 20px; }}
                .nav a {{ color: #4CAF50; margin-right: 20px; text-decoration: none; }}
                .nav a:hover {{ text-decoration: underline; }}
                .stats {{ background: #16213e; padding: 15px; border-radius: 10px; margin-bottom: 20px; }}
                .log-container {{
                    background: #0d1117;
                    border-radius: 10px;
                    padding: 15px;
                    max-height: 70vh;
                    overflow-y: auto;
                }}
                .log-line {{
                    padding: 5px 10px;
                    border-bottom: 1px solid #21262d;
                    font-size: 12px;
                    line-height: 1.5;
                }}
                .log-line:hover {{ background: #21262d; }}
                .log-bruce {{ color: #58a6ff; }}
                .log-cliente {{ color: #f0883e; }}
                .log-llamada {{ color: #a371f7; }}
                .log-error {{ color: #f85149; }}
                .log-exito {{ color: #3fb950; }}
            </style>
        </head>
        <body>
            <h1> Logs de BRUCE{bruce_id}</h1>
            <div class="nav">
                <a href="/historial-llamadas">← Volver al Historial</a>
                <a href="/logs"> Dashboard</a>
                <a href="/logs/api?bruce_id={bruce_id}&formato=json" target="_blank"> JSON</a>
            </div>
            <div class="stats">
                <strong>Total logs encontrados:</strong> {len(logs_list)} |
                <strong>BRUCE ID:</strong> {bruce_id}
            </div>
            <div class="log-container">
        """

        for log in logs_list:
            # Colorear según tipo de log
            css_class = ""
            if "[BRUCE" in log or "BRUCE DICE" in log.upper():
                css_class = "log-bruce"
            elif "[CLIENTE" in log or "CLIENTE DIJO" in log.upper():
                css_class = "log-cliente"
            elif "[LLAMADA" in log:
                css_class = "log-llamada"
            elif "error" in log.lower() or "" in log:
                css_class = "log-error"
            elif "" in log or "éxito" in log.lower():
                css_class = "log-exito"

            # Escapar HTML
            log_escaped = log.replace("<", "&lt;").replace(">", "&gt;")
            html += f'<div class="log-line {css_class}">{log_escaped}</div>'

        html += """
            </div>
        </body>
        </html>
        """

        return html

    except Exception as e:
        return {"error": str(e)}, 500


# ============================================================================
# FIX 212: WEBSOCKET ENDPOINT PARA DEEPGRAM STREAMING
# ============================================================================

# FIX 314: Saludos simples para detección rápida en interim
SALUDOS_RAPIDOS = [
    "hola", "bueno", "buenos días", "buenos dias", "buen día", "buen dia",
    "buenas tardes", "buenas noches", "buenas", "diga", "dígame", "digame",
    "sí", "si", "aló", "alo", "qué tal", "que tal", "mande"
]

# Callback que se llama cuando Deepgram completa una transcripción
def on_deepgram_transcript(call_sid, texto, is_final):
    """
    FIX 218/314: Callback cuando Deepgram transcribe algo
    Ahora maneja tanto transcripciones finales como parciales
    FIX 314: Detecta saludos en interim para pre-cargar respuesta
    """
    if not texto or not texto.strip():
        return

    texto = texto.strip()
    texto_lower = texto.lower()

    if call_sid not in deepgram_transcripciones:
        deepgram_transcripciones[call_sid] = []

    # FIX 244: Tracking de habla activa
    import time
    if call_sid not in cliente_hablando_activo:
        cliente_hablando_activo[call_sid] = {
            "inicio": time.time(),
            "palabras_dichas": 0
        }

    # Contar palabras (aproximado)
    num_palabras = len(texto.split())
    if num_palabras > cliente_hablando_activo[call_sid]["palabras_dichas"]:
        cliente_hablando_activo[call_sid]["palabras_dichas"] = num_palabras

    # FIX 314: Detectar saludos en interim para pre-cargar audio
    # Solo si es primera respuesta (no hay transcripciones previas finales)
    if not is_final and call_sid not in respuesta_precargada:
        # Verificar si es un saludo simple
        es_saludo = any(saludo in texto_lower for saludo in SALUDOS_RAPIDOS)
        palabras = texto.split()
        es_corto = len(palabras) <= 4  # Máximo 4 palabras para ser saludo

        if es_saludo and es_corto:
            print(f" FIX 314: Saludo detectado en INTERIM: '{texto}' - Pre-cargando respuesta...")

            # Marcar que ya pre-cargamos para no repetir
            respuesta_precargada[call_sid] = {
                "audio_listo": True,
                "tipo": "segunda_parte_saludo",
                "timestamp": time.time()
            }

            # Verificar que el audio de segunda_parte_saludo esté en cache
            if "segunda_parte_saludo" in audio_cache:
                print(f" FIX 314: Audio segunda_parte_saludo YA está en cache - respuesta será instantánea")
            else:
                print(f" FIX 314: Audio segunda_parte_saludo NO está en cache - generando...")
                # El audio se generará cuando se procese la respuesta

    # FIX 490: Proteger acceso concurrente a transcripciones con lock
    with deepgram_transcripciones_lock:
        if is_final:
            # Transcripción final - agregar al array
            print(f" FIX 212: Transcripción FINAL Deepgram para {call_sid}: '{texto}'")
            deepgram_transcripciones[call_sid].append(texto)
            # FIX 451: Marcar que recibimos transcripción FINAL
            with deepgram_ultima_final_lock:
                if call_sid not in deepgram_ultima_final:
                    deepgram_ultima_final[call_sid] = {}
                deepgram_ultima_final[call_sid] = {
                    "timestamp": time.time(),
                    "texto": texto,
                    "es_final": True
                }
        else:
            # FIX 218: Transcripción parcial - reemplazar última entrada parcial
            # Esto permite que /procesar-respuesta tenga datos aunque no haya llegado el final
            print(f" FIX 212: [PARCIAL] '{texto}'")
            if deepgram_transcripciones[call_sid]:
                # Si la última entrada es más corta que la nueva, reemplazarla
                ultima = deepgram_transcripciones[call_sid][-1]
                if len(texto) > len(ultima):
                    deepgram_transcripciones[call_sid][-1] = texto
            else:
                deepgram_transcripciones[call_sid].append(texto)

            # FIX 456: Siempre registrar la última PARCIAL para detectar si cliente sigue hablando
            deepgram_ultima_parcial[call_sid] = {
            "timestamp": time.time(),
            "texto": texto
        }

        # FIX 451: Marcar que solo tenemos PARCIAL (aún no llegó FINAL)
        if call_sid not in deepgram_ultima_final:
            deepgram_ultima_final[call_sid] = {}
        # Solo actualizar si no hay FINAL reciente (menos de 0.5s)
        ultima_info = deepgram_ultima_final.get(call_sid, {})
        if not ultima_info.get("es_final") or (time.time() - ultima_info.get("timestamp", 0)) > 0.5:
            deepgram_ultima_final[call_sid] = {
                "timestamp": time.time(),
                "texto": texto,
                "es_final": False
            }


# WebSocket handler para recibir audio de Twilio
if FLASK_SOCK_AVAILABLE and sock:
    @sock.route('/media-stream')
    def media_stream(ws):
        """
        FIX 212: WebSocket endpoint para recibir MediaStream de Twilio
        y enviarlo a Deepgram para transcripción en tiempo real
        """
        print(f"\n FIX 212: Nueva conexión WebSocket /media-stream")

        call_sid = None
        transcriber = None
        stream_sid = None

        try:
            while True:
                # Recibir mensaje de Twilio
                message = ws.receive()
                if message is None:
                    break

                data = json.loads(message)
                event = data.get('event')

                if event == 'connected':
                    print(f"🟢 FIX 212: MediaStream conectado")

                elif event == 'start':
                    # Inicio del stream - obtener metadata
                    start_data = data.get('start', {})
                    stream_sid = start_data.get('streamSid')
                    call_sid = start_data.get('callSid')

                    print(f" FIX 212: MediaStream iniciado")
                    print(f"   StreamSid: {stream_sid}")
                    print(f"   CallSid: {call_sid}")

                    # Crear transcriber de Deepgram para esta llamada
                    if DEEPGRAM_AVAILABLE and USE_DEEPGRAM:
                        transcriber = crear_transcriber(call_sid, on_deepgram_transcript)
                        if transcriber:
                            # Conectar a Deepgram (sync wrapper para async)
                            loop = asyncio.new_event_loop()
                            asyncio.set_event_loop(loop)
                            connected = loop.run_until_complete(transcriber.connect())
                            if connected:
                                print(f" FIX 212: Deepgram conectado para {call_sid}")
                            else:
                                print(f" FIX 212: Error conectando Deepgram para {call_sid}")
                                transcriber = None

                elif event == 'media':
                    # Audio chunk recibido de Twilio
                    media_data = data.get('media', {})
                    payload = media_data.get('payload')  # Audio en base64

                    if payload and transcriber:
                        # FIX 536: Verificar conexión y reconectar si es necesario
                        if not transcriber.is_connected:
                            print(f" FIX 536: Deepgram desconectado - intentando reconectar")
                            try:
                                loop = asyncio.new_event_loop()
                                asyncio.set_event_loop(loop)
                                reconnected = loop.run_until_complete(transcriber.reconnect())
                                if not reconnected:
                                    print(f" FIX 536: Reconexión fallida - continuando sin Deepgram")
                            except Exception as recon_error:
                                print(f" FIX 536: Error en reconexión: {recon_error}")

                        # Enviar audio si está conectado
                        if transcriber.is_connected:
                            transcriber.send_audio_base64(payload)

                elif event == 'stop':
                    print(f" FIX 212: MediaStream detenido - CallSid: {call_sid}")
                    break

        except Exception as e:
            error_str = str(e)
            print(f" FIX 212: Error en WebSocket: {e}")

            # FIX 536: Detectar errores específicos de WebSocket
            if '1005' in error_str or '1011' in error_str or 'ConnectionClosed' in error_str:
                print(f" FIX 536: Error de conexión WebSocket detectado ({error_str[:50]})")
                # No hacer traceback para errores esperados de cierre de conexión
            else:
                traceback.print_exc()

        finally:
            # Limpiar recursos
            if transcriber:
                try:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    loop.run_until_complete(transcriber.close())
                except Exception as e:
                    print(f" Error cerrando transcriber: {e}")

                if call_sid:
                    eliminar_transcriber(call_sid)
                    # FIX 314: Limpiar respuesta pre-cargada
                    if call_sid in respuesta_precargada:
                        del respuesta_precargada[call_sid]

            print(f" FIX 212: WebSocket cerrado - CallSid: {call_sid}")


if __name__ == "__main__":
    # FIX 208: Registrar inicio del servidor
    log_evento("Servidor iniciando...", "SISTEMA")

    print("\n" + "=" * 60)
    print(" SERVIDOR DE LLAMADAS NIOVAL")
    print("=" * 60)
    print("\n SERVIDOR BRUCE W - VERSION FIX 81 (DEBUG ACTIVO)")
    print("=" * 60)
    print("\n Endpoints disponibles:")
    print("  POST /iniciar-llamada            - Inicia una llamada individual")
    print("  POST /llamadas-masivas           - Inicia múltiples llamadas")
    print("  GET  /status/<call_sid>          - Estado de una llamada")
    print("  GET  /stats                      - Ver estadísticas de caché")
    print("  POST /generate-cache             - Generar audios manualmente")
    print("  GET  /diagnostico-persistencia   - Diagnosticar volumen persistente")
    print("  WS   /media-stream               - FIX 212: WebSocket para Deepgram")
    print("\n URLs de acceso:")
    print("   Estadísticas: https://nioval-webhook-server-production.up.railway.app/stats")
    print("   Diagnóstico Persistencia: https://nioval-webhook-server-production.up.railway.app/diagnostico-persistencia")
    print("\n FIX 79: Despedida cálida activa (deja puerta abierta)")
    print(" FIX 81: Debug de detección de Truper activo")

    # FIX 212: Estado de Deepgram
    if DEEPGRAM_AVAILABLE and USE_DEEPGRAM:
        print(" FIX 212: Deepgram ACTIVO - Transcripción en tiempo real")
        print(f"   WebSocket: /media-stream")
    else:
        print(" FIX 212: Deepgram NO disponible - Usando Whisper como fallback")
        if not DEEPGRAM_API_KEY:
            print("   Falta: DEEPGRAM_API_KEY en variables de entorno")

    print("\n  Asegúrate de configurar Twilio en .env")
    print("=" * 60 + "\n")

    # PASO 1: Cargar caché persistente desde disco (audios auto-generados)
    print(" Cargando caché desde disco...")
    cargar_cache_desde_disco()

    # PASO 2: Pre-generar caché manual de audios comunes con Multilingual v2
    pre_generar_audios_cache()

    print(f"\n Estadísticas de caché:")
    print(f"   • Audios en caché: {len(audio_cache)}")
    print(f"   • Directorio: {CACHE_DIR}")
    print(f"   • Ruta absoluta: {os.path.abspath(CACHE_DIR)}")
    print(f"   • Auto-caché después de {FRECUENCIA_MIN_CACHE} usos\n")

    # FIX 270: Notificar a Telegram que el servidor está listo
    def notificar_telegram_deploy():
        """Envía notificación a Telegram cuando el servidor inicia"""
        import datetime
        TELEGRAM_BOTS = [
            {
                "token": "8537624347:AAHDIe60mb2TkdDk4vqlcS2tpakTB_5D4qE",
                "chat_id": "7314842427",
                "nombre": "Bot 1"
            },
            {
                "token": "8524460310:AAFAwph27rSagooKTNSGXauBycpDpCjhKjI",
                "chat_id": "5838212022",
                "nombre": "Bot 2"
            }
        ]

        fecha_hora = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        mensaje = f" <b>Deploy completado</b>\n\n Bruce Agent iniciado en Railway\n {fecha_hora}\n Audios en caché: {len(audio_cache)}"

        for bot in TELEGRAM_BOTS:
            try:
                url = f"https://api.telegram.org/bot{bot['token']}/sendMessage"
                data = {
                    "chat_id": bot['chat_id'],
                    "text": mensaje,
                    "parse_mode": "HTML"
                }
                response = requests.post(url, data=data, timeout=10)
                if response.status_code == 200:
                    print(f" FIX 270: Telegram {bot['nombre']} notificado")
                else:
                    print(f" FIX 270: Error Telegram {bot['nombre']}: {response.status_code}")
            except Exception as e:
                print(f" FIX 270: Error Telegram {bot['nombre']}: {e}")

    # Ejecutar notificación en background para no bloquear inicio
    import threading
    threading.Thread(target=notificar_telegram_deploy, daemon=True).start()

    # Puerto dinámico para Render (usa PORT de env o 5000 por defecto)
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
