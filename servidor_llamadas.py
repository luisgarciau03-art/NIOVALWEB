"""
Servidor Flask para manejar llamadas telefónicas con Twilio
Integración: Twilio → GPT-4o → ElevenLabs → Cliente
"""

from flask import Flask, request, Response, send_file
from twilio.twiml.voice_response import VoiceResponse, Gather, Play
from twilio.rest import Client
import os
import tempfile
import threading
import json
import random
import traceback  # FIX 102: Para logging de errores detallados
from dotenv import load_dotenv
from agente_ventas import AgenteVentas
from elevenlabs import ElevenLabs
from openai import OpenAI  # FIX 60: Para Whisper API
import requests  # FIX 60: Para descargar grabaciones de Twilio

load_dotenv()

app = Flask(__name__)

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
    print("✅ Google Sheets Managers inicializados")
except Exception as e:
    print(f"⚠️  Google Sheets no disponible: {e}")
    print("⚠️  Las llamadas se guardarán solo en backup local")

# Inicializar WhatsApp Validator
try:
    from whatsapp_validator import WhatsAppValidator
    whatsapp_validator = WhatsAppValidator()
    print("✅ WhatsApp Validator inicializado")
except Exception as e:
    print(f"⚠️  WhatsApp Validator no disponible: {e}")
    print("⚠️  No se validarán números de WhatsApp")

# Configuración Twilio
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_PHONE_NUMBER = os.getenv("TWILIO_PHONE_NUMBER")

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

# Caché de audios pre-generados con Multilingual v2 (mejor calidad)
audio_cache = {}

# Sistema de caché auto-adaptativo
frase_stats = {}  # Contador de frecuencia de frases

# Directorio de caché - detecta automáticamente si estamos en Railway
# Railway monta el Volume en /app/audio_cache por defecto
# En local usa ./audio_cache
CACHE_DIR = os.getenv("CACHE_DIR", "audio_cache")  # Configurable por variable de entorno
FRECUENCIA_MIN_CACHE = 2  # Auto-generar caché después de N usos (reducido de 3 a 2)
cache_metadata = {}  # Metadata: frase → archivo MP3

# FIX 56: CACHÉ DE RESPUESTAS DE GPT (0s delay para preguntas comunes)
# Diccionario: patrón de pregunta → respuesta pre-definida
respuestas_cache = {
    # Preguntas sobre origen/ubicación
    "de_donde_habla": {
        "patrones": [
            "de dónde", "de donde", "dónde están", "donde están",
            "de qué ciudad", "de que ciudad", "ubicados", "ubicación",
            "de parte de", "de qué parte", "de que parte"
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
    "quien_habla": {
        "patrones": [
            "quién habla", "quien habla", "de parte de quién", "de parte de quien",
            "quién es", "quien es", "su nombre", "cómo se llama", "como se llama"
        ],
        "respuesta": "Mi nombre es Bruce W, soy asesor de ventas de NIOVAL. Quisiera brindar información al encargado de compras sobre nuestros productos ferreteros. ¿Me lo puede comunicar por favor?"
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


def cargar_cache_desde_disco():
    """Carga caché persistente desde disco al iniciar"""
    import os
    import json

    if not os.path.exists(CACHE_DIR):
        os.makedirs(CACHE_DIR)
        print("📁 Directorio de caché creado")
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
                print(f"  📦 Cargado desde disco: {key}")

        print(f"✅ {len(audio_cache)} audios cargados desde caché persistente\n")

    # Cargar estadísticas de frases
    stats_file = os.path.join(CACHE_DIR, "frase_stats.json")
    if os.path.exists(stats_file):
        with open(stats_file, 'r', encoding='utf-8') as f:
            global frase_stats
            frase_stats = json.load(f)
        print(f"📊 {len(frase_stats)} estadísticas de frases cargadas desde disco\n")

    # FIX 57: Cargar preguntas frecuentes y candidatos auto-cache
    preguntas_file = os.path.join(CACHE_DIR, "preguntas_frecuentes.json")
    if os.path.exists(preguntas_file):
        with open(preguntas_file, 'r', encoding='utf-8') as f:
            global preguntas_frecuentes
            preguntas_frecuentes = json.load(f)
        print(f"🔍 {len(preguntas_frecuentes)} preguntas frecuentes cargadas desde disco\n")

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
                        print(f"✅ FIX 64: respuestas_cache.json ya está actualizado ({len(seed_content)} categorías)\n")
            except:
                debe_actualizar = True

        if debe_actualizar:
            shutil.copy(repo_respuestas_file, respuestas_file)
            print(f"📋 FIX 64: Actualizado respuestas_cache.json desde seed_data/ a Volume\n")
    else:
        print(f"⚠️ FIX 64: No se encontró seed_data/respuestas_cache.json\n")

    if os.path.exists(respuestas_file):
        with open(respuestas_file, 'r', encoding='utf-8') as f:
            global respuestas_cache
            cache_personalizado = json.load(f)
            # Merge con las respuestas por defecto (prioridad a las personalizadas)
            respuestas_cache.update(cache_personalizado)
        print(f"💾 {len(cache_personalizado)} respuestas personalizadas cargadas desde disco")
        print(f"📊 TOTAL de categorías en caché: {len(respuestas_cache)}\n")


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

    print(f"💾 Caché guardado en disco: {key} → {filename}")


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
        print(f"\n🎯 FIX 57: Pregunta frecuente detectada ({UMBRAL_AUTO_CACHE} veces):")
        print(f"   Pregunta: '{pregunta[:60]}...'")
        print(f"   Respuesta más común: '{respuesta[:60]}...'")

        # Agregar a candidatos si no está ya
        if pregunta_normalizada not in candidatos_auto_cache:
            candidatos_auto_cache.append(pregunta_normalizada)
            print(f"   ✅ Agregado a candidatos de auto-caché")

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
        print(f"👤 Nombre detectado: '{nombre_detectado}' → Usando plantilla universal")
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
        print(f"\n🔥 Frase frecuente detectada ({count} usos): {texto_para_cache[:50]}...")
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

            print(f"   ✅ Caché auto-generado: {frase_key}")
            if nombre_detectado:
                print(f"   📝 Guardado como plantilla universal con (NAME)")

        except Exception as e:
            print(f"   ❌ Error generando caché automático: {e}")


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
    }

    # FIX 59: Agregar respuestas cacheadas de respuestas_cache para pre-generación
    # Esto hace que las respuestas comunes sean INSTANTÁNEAS (0s delay)
    print("🔧 Pre-generando caché de audios con Multilingual v2...")
    print(f"📋 Agregando {len(respuestas_cache)} respuestas cacheadas al pre-generado...")
    for categoria, datos in respuestas_cache.items():
        cache_key = f"respuesta_cache_{categoria}"
        frases_comunes[cache_key] = datos["respuesta"]

    for key, texto in frases_comunes.items():
        # IMPORTANTE: Solo generar si NO existe en cache (ahorra créditos)
        if key in audio_cache:
            print(f"  ⏭️ Omitido: {key} (ya existe en cache)")
            continue

        try:
            print(f"  🎙️ Generando: {key}...")
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
            print(f"  ✅ Cached: {key}")
        except Exception as e:
            print(f"  ❌ Error caching {key}: {e}")

    print(f"✅ Caché completo: {len(audio_cache)} audios pre-generados\n")


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
        print("⚠️ pydub no disponible, usando concatenación simple")
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

    print(f"🎭 Generando audio con nombre específico: '{nombre}'")

    # Reemplazar (NAME) con el nombre real
    texto_final = texto_plantilla.replace("(NAME)", nombre)

    # Generar audio completo
    print(f"   🎤 Generando: '{texto_final[:50]}...'")
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

    print(f"   ✅ Audio generado en {(time.time() - inicio):.2f}s")
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
            print(f"📦 Caché manual: {usar_cache_key} (0s delay)")
            return audio_id

        # PASO 2: Detectar si tiene nombre y buscar plantilla correspondiente
        texto_plantilla, nombre_detectado = normalizar_frase_con_nombres(texto)

        if nombre_detectado:
            # Buscar plantilla en caché
            palabras_plantilla = " ".join(texto_plantilla.split()[:8]).lower()
            frase_key_plantilla = "_".join(palabras_plantilla.split())

            if frase_key_plantilla in audio_cache:
                print(f"🎭 Usando plantilla universal + nombre '{nombre_detectado}'")
                audio_compuesto = generar_audio_con_nombre(
                    texto_plantilla,
                    nombre_detectado,
                    frase_key_plantilla
                )

                if audio_compuesto:
                    audio_files[audio_id] = audio_compuesto
                    print(f"✅ Audio compuesto listo (plantilla + nombre)")
                    return audio_id
                else:
                    print(f"⚠️ Error en audio compuesto, generando completo...")
            else:
                print(f"ℹ️ Plantilla no en caché, generando completo...")

        # PASO 3: Buscar en caché auto-generado (sin nombre)
        palabras_inicio = " ".join(texto.split()[:8]).lower()
        frase_key = "_".join(palabras_inicio.split())

        if frase_key in audio_cache:
            audio_files[audio_id] = audio_cache[frase_key]
            print(f"📦 Caché AUTO: {frase_key[:40]}... (0s delay)")
            return audio_id

        # PASO 4: Registrar frase para estadísticas (auto-genera caché si es frecuente)
        registrar_frase_usada(texto)

        # Aplicar correcciones fonéticas
        texto_corregido = corregir_pronunciacion(texto)

        # SIEMPRE usar Multilingual v2 (mejor acento mexicano)
        palabras = len(texto_corregido.split())
        modelo = "eleven_multilingual_v2"
        print(f"🎙️ Usando Multilingual v2 ({palabras} palabras)")

        # FIX 162A: Generar audio con retry automático
        max_intentos = 2
        intento = 1

        while intento <= max_intentos:
            try:
                print(f"🎵 FIX 162A: Generando audio (intento {intento}/{max_intentos})")

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
                        print(f"🎵 Primer chunk en {(time.time() - inicio):.2f}s")
                temp_file.close()

                # Guardar ruta del archivo
                audio_files[audio_id] = temp_file.name
                print(f"✅ Audio en {(time.time() - inicio):.2f}s ({chunk_count} chunks, {modelo})")

                if intento > 1:
                    print(f"✅ FIX 162A: Audio generado exitosamente en intento {intento}")

                return audio_id

            except Exception as e_retry:
                print(f"⚠️ FIX 162A: Error en intento {intento}/{max_intentos}: {type(e_retry).__name__}")

                if intento < max_intentos:
                    print(f"🔄 FIX 162A: Reintentando en 1 segundo...")
                    time.sleep(1)
                    intento += 1
                else:
                    # Último intento falló - lanzar excepción para que la maneje el except principal
                    raise e_retry

    except Exception as e:
        print(f"❌ FIX 162A: Error generando audio ElevenLabs después de {max_intentos} intentos: {e}")
        print(f"   Tipo de error: {type(e).__name__}")
        print(f"   Texto que causó error: {texto[:100]}...")
        print(f"   Traceback completo:")
        traceback.print_exc()
        print(f"🚨 FIX 162A: CRÍTICO - NO usar fallback Twilio (causa desconfianza)")
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


def transcribir_con_whisper(recording_url):
    """
    FIX 60: Transcribe audio usando Whisper API de OpenAI

    Args:
        recording_url: URL de la grabación de Twilio

    Returns:
        str: Texto transcrito o None si falla
    """
    import time
    inicio = time.time()

    try:
        print(f"🎙️ FIX 60: Descargando grabación de Twilio...")
        print(f"   URL: {recording_url}")

        # FIX 62: Descargar audio de Twilio con autenticación (timeout agresivo)
        response = requests.get(
            recording_url,
            auth=(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN),
            timeout=5  # FIX 62: Reducido de 10s a 5s
        )
        response.raise_for_status()

        tiempo_descarga = time.time() - inicio
        print(f"   ✅ Audio descargado en {tiempo_descarga:.3f}s ({len(response.content)} bytes)")

        # Guardar temporalmente para Whisper
        temp_audio = tempfile.NamedTemporaryFile(delete=False, suffix='.wav')
        temp_audio.write(response.content)
        temp_audio.close()

        print(f"🤖 FIX 60: Transcribiendo con Whisper API...")
        inicio_whisper = time.time()

        # Transcribir con Whisper
        with open(temp_audio.name, 'rb') as audio_file:
            transcription = openai_client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                language="es",  # Español (mejor precisión)
                response_format="text"
            )

        tiempo_whisper = time.time() - inicio_whisper
        tiempo_total = time.time() - inicio

        # Limpiar archivo temporal
        os.unlink(temp_audio.name)

        texto = transcription.strip() if isinstance(transcription, str) else transcription.text.strip()

        print(f"   ✅ Transcripción completada en {tiempo_whisper:.3f}s")
        print(f"   ⏱️  Tiempo total: {tiempo_total:.3f}s (descarga: {tiempo_descarga:.3f}s + whisper: {tiempo_whisper:.3f}s)")
        print(f"   📝 Texto: '{texto}'")

        return texto

    except Exception as e:
        tiempo_total = time.time() - inicio
        print(f"   ❌ Error en transcripción Whisper después de {tiempo_total:.3f}s: {e}")
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
        print(f"\n🔍 DEBUG 1: /iniciar-llamada - Request recibido")

        data = request.json
        print(f"🔍 DEBUG 2: JSON parseado correctamente")

        telefono_destino = data.get("telefono")
        nombre_negocio = data.get("nombre_negocio", "cliente")
        contacto_info = data.get("contacto_info", None)

        print(f"🔍 DEBUG 3: Datos extraídos - Tel: {telefono_destino}, Negocio: {nombre_negocio}")

        if not telefono_destino:
            print(f"❌ ERROR: Teléfono no proporcionado")
            return {"error": "Teléfono requerido"}, 400

        print(f"🔍 DEBUG 4: Iniciando llamada Twilio a {telefono_destino}")

        # FIX 85: DESHABILITAR machine_detection para reducir delay de 11s a 2-3s
        # PROBLEMA: DetectMessageEnd hace que Twilio ESPERE 5-10s antes de hablar
        # SOLUCIÓN: Deshabilitar y detectar buzón por transcripción (ya implementado en agente_ventas.py)
        call = twilio_client.calls.create(
            to=telefono_destino,
            from_=TWILIO_PHONE_NUMBER,
            url=request.url_root + "webhook-voz",
            method="POST",
            record=True,  # Grabar llamada automáticamente
            # machine_detection="DetectMessageEnd",  # FIX 85: DESHABILITADO (causaba delay de 11s)
            # machine_detection_timeout=5,  # FIX 85: DESHABILITADO
            status_callback=request.url_root + "status-callback",  # Webhook para estado de llamada
            status_callback_event=["completed"]  # Notificar cuando termine
        )

        print(f"🔍 DEBUG 5: Llamada Twilio creada - SID: {call.sid}")

        # Guardar info del contacto para usar en el webhook
        if contacto_info:
            # Si se envió contacto_info completo, usarlo
            contactos_llamadas[call.sid] = contacto_info
            print(f"📋 Contacto completo guardado para Call SID {call.sid[:10]}... (fila {contacto_info.get('fila', 'N/A')})")
        else:
            # Si no, guardar solo lo básico (compatibilidad con llamadas antiguas)
            contactos_llamadas[call.sid] = {
                "telefono": telefono_destino,
                "nombre_negocio": nombre_negocio
            }
            print(f"📋 Contacto básico guardado para Call SID {call.sid[:10]}...")

        print(f"🔍 DEBUG 6: Retornando respuesta exitosa")

        return {
            "success": True,
            "call_sid": call.sid,
            "status": call.status
        }

    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"\n❌ ERROR EN /iniciar-llamada:")
        print(f"❌ Tipo de error: {type(e).__name__}")
        print(f"❌ Mensaje: {str(e)}")
        print(f"❌ Stack trace completo:")
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
                print(f"\n🔄 NÚMERO CAMBIÓ - Cargando historial previo para contexto...")
                historial_previo = sheets_manager.obtener_historial_completo(fila)

                if any(historial_previo.values()):
                    print(f"📚 Historial cargado:")
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
        print(f"🆔 ID BRUCE generado: {bruce_id}")

    # Crear nueva conversación con Google Sheets y WhatsApp Validator
    agente = AgenteVentas(
        contacto_info=contacto_info,
        sheets_manager=sheets_manager,
        resultados_manager=resultados_manager,
        whatsapp_validator=whatsapp_validator
    )
    agente.call_sid = call_sid  # Guardar el Call SID de Twilio
    agente.bruce_id = bruce_id  # Guardar el ID BRUCE
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
        print(f"📦 FIX 114: Saludo corto 'Hola, buen dia' desde caché (0s delay, voz Bruce)")
    elif usa_cache_saludo_normal and "saludo_inicial" in audio_cache:
        # Usar audio pre-generado del caché - versión normal (0s delay, voz Bruce)
        audio_files[audio_id] = audio_cache["saludo_inicial"]
        print(f"📦 Saludo inicial (normal) desde caché (0s delay, voz Bruce)")
    elif usa_cache_saludo_encargado and "saludo_inicial_encargado" in audio_cache:
        # Usar audio pre-generado del caché - versión encargado (0s delay, voz Bruce)
        audio_files[audio_id] = audio_cache["saludo_inicial_encargado"]
        print(f"📦 Saludo inicial (encargado) desde caché (0s delay, voz Bruce)")
    else:
        # Fallback: generar con ElevenLabs si no hay caché
        print(f"⚠️ Generando saludo inicial con ElevenLabs (caché no disponible - tardará 2-4s)")
        generar_audio_elevenlabs(mensaje_inicial, audio_id)

    # FIX 96: Preparar grabación ANTES de reproducir audio (estar listo desde el primer sonido)
    # IMPORTANTE: El <Gather> debe envolver al <Play> para que Twilio esté escuchando
    # DESDE QUE EMPIEZA a reproducir el audio, no DESPUÉS de que termina
    #
    # FIX 60/61/62/63/86: Recopilar respuesta del cliente con WHISPER API (mejor precisión + más barato)
    # IMPORTANTE: input="speech" + recordingStatusCallback genera GRABACIÓN automáticamente
    # Twilio enviará RecordingUrl en el webhook para que Whisper lo transcriba
    # FIX 86/112/149: Timeouts MUY AGRESIVOS para detectar cliente desesperado RÁPIDO
    # Cliente desesperado habla 5-30s continuamente → Necesitamos cortar en primera pausa
    gather = Gather(
        input="speech",
        language="es-MX",
        timeout=2,  # FIX 145: 2s - Balance entre clientes normales (2-3s) y desesperados
        speech_timeout=0.5,  # FIX 149: 0.5s - ULTRA AGRESIVO para cortar cliente desesperado en primera pausa
        action="/procesar-respuesta",
        method="POST",
        action_on_empty_result=False,  # No procesar si no hay respuesta
        speech_model="experimental_conversations",  # FIX 61: CRÍTICO - Habilitar grabación para Whisper
        barge_in=True  # FIX 139: Permitir interrupciones en saludo para detectar clientes desesperados rápido
    )

    # FIX 96: ANIDAR <Play> dentro de <Gather> para que esté listo ANTES de hablar
    # Reproducir audio de ElevenLabs DENTRO del Gather
    audio_url = request.url_root + f"audio/{audio_id}"
    gather.play(audio_url)

    # Agregar el Gather a la respuesta
    response.append(gather)

    # FIX 110: Si no hay respuesta, redirigir a /procesar-respuesta con SpeechResult vacío
    # Esto permite que el FIX 92 maneje la respuesta vacía (pedir repetición)
    # en lugar de colgar directamente
    response.redirect(url="/procesar-respuesta?CallSid=" + call_sid + "&SpeechResult=", method="POST")

    return Response(str(response), mimetype="text/xml")


@app.route("/procesar-respuesta", methods=["GET", "POST"])
def procesar_respuesta():
    """
    FIX 60: Procesa la respuesta del cliente y continúa la conversación
    ACTUALIZADO: Usa Whisper API si está disponible (mejor precisión + más barato)
    """
    # Twilio puede enviar GET o POST
    if request.method == "GET":
        call_sid = request.args.get("CallSid")
        speech_result = request.args.get("SpeechResult", "")
        recording_url = request.args.get("RecordingUrl", "")  # FIX 60
        call_status = request.args.get("CallStatus", "")
        answered_by = request.args.get("AnsweredBy", "")

        # DEBUG: Log todos los parámetros de Twilio
        print(f"\n🔍 DEBUG - Parámetros Twilio (GET):")
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
        print(f"\n🔍 DEBUG - Parámetros Twilio (POST):")
        print(f"   CallSid: {call_sid}")
        print(f"   CallStatus: {call_status}")
        print(f"   AnsweredBy: {answered_by}")
        print(f"   SpeechResult: '{speech_result}'")
        print(f"   RecordingUrl: '{recording_url}'")  # FIX 60
        if request.form.get("Digits"):
            print(f"   Digits: {request.form.get('Digits')}")

    # FIX 60: PRIORIZAR WHISPER API si está disponible
    # Whisper tiene: mejor precisión (96-99% vs 85-90%) + más barato ($0.006/min vs $0.020/min)
    usar_whisper = False
    transcripcion_whisper = None

    if recording_url and OPENAI_API_KEY:
        print(f"\n🎯 FIX 60: RecordingUrl disponible - usando WHISPER API")
        transcripcion_whisper = transcribir_con_whisper(recording_url)

        if transcripcion_whisper:
            usar_whisper = True
            speech_original_twilio = speech_result  # Guardar transcripción de Twilio para comparación
            speech_result = transcripcion_whisper  # Usar Whisper como principal

            # Log de comparación (útil para validar mejora)
            if speech_original_twilio:
                print(f"\n📊 FIX 60: COMPARACIÓN DE TRANSCRIPCIONES:")
                print(f"   🔵 Twilio: '{speech_original_twilio}'")
                print(f"   🟢 Whisper: '{transcripcion_whisper}'")
                if speech_original_twilio.lower() != transcripcion_whisper.lower():
                    print(f"   ⚠️  DIFERENCIAS DETECTADAS - Whisper será más preciso")
            else:
                print(f"   ℹ️  Solo Whisper disponible (Twilio no transcribió)")
        else:
            print(f"   ⚠️  Whisper falló - fallback a transcripción de Twilio")
    elif not OPENAI_API_KEY:
        print(f"   ℹ️  OPENAI_API_KEY no configurada - usando Twilio Speech Recognition")

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

                print(f"🔧 FIX 30 - Corrección ortográfica:")
                print(f"   '{palabra_original} con {letra_correcta}' → '{palabra_corregida}'")

        # Log si hubo correcciones
        if speech_result != speech_original:
            print(f"🔧 FIX 28/30 - Transcripción corregida:")
            print(f"   Original: '{speech_original}'")
            print(f"   Corregida: '{speech_result}'")

    # Verificar si Twilio detectó buzón de voz (AnsweredBy=machine_start)
    if answered_by in ["machine_start", "machine_end_beep", "machine_end_silence", "machine_end_other"]:
        print(f"📞 Buzón de voz detectado automáticamente por Twilio: {answered_by}")
        print(f"💬 Marcando como BUZON")

        # Obtener agente si existe
        agente = conversaciones_activas.get(call_sid)
        if agente:
            # Marcar como "Buzon"
            agente.lead_data["estado_llamada"] = "Buzon"
            agente.lead_data["pregunta_0"] = "Buzon"
            agente.lead_data["pregunta_7"] = "BUZON"
            agente.lead_data["resultado"] = "NEGADO"
            print(f"📝 Estado actualizado: Buzón detectado automáticamente")

            # Guardar la llamada
            agente.guardar_llamada_y_lead()

        # Terminar con respuesta TwiML
        response = VoiceResponse()
        response.say("Disculpe, parece que entró el buzón de voz. Le llamaré en otro momento. Que tenga buen día.", language="es-MX")
        response.hangup()
        return Response(str(response), mimetype="text/xml")

    # FIX 105: Detectar buzón por contenido del SpeechResult (cuando Twilio no lo detecta por AMD)
    # Keywords comunes en mensajes de buzón de voz en México
    keywords_buzon = [
        "buzón de voz", "buzon de voz", "deje su mensaje", "deja tu mensaje",
        "dejar un mensaje", "dejar mensaje", "después del tono", "despues del tono",
        "no puede atender", "no disponible en este momento", "mailbox is full",
        "buzón está lleno", "buzon esta lleno", "no se puede dejar", "intente más tarde"
    ]

    speech_lower = speech_result.lower() if speech_result else ""
    es_buzon_por_contenido = any(keyword in speech_lower for keyword in keywords_buzon)

    if es_buzon_por_contenido:
        print(f"📞 FIX 105: Buzón detectado por contenido del SpeechResult")
        print(f"   Mensaje: '{speech_result[:100]}...'")
        print(f"💬 Marcando como BUZON")

        # Obtener agente si existe
        agente = conversaciones_activas.get(call_sid)
        if agente:
            # Marcar como "Buzon"
            agente.lead_data["estado_llamada"] = "Buzon"
            agente.lead_data["pregunta_0"] = "Buzon"
            agente.lead_data["pregunta_7"] = "BUZON"
            agente.lead_data["resultado"] = "NEGADO"
            print(f"📝 Estado actualizado: Buzón detectado por análisis de contenido")

            # Guardar la llamada
            agente.guardar_llamada_y_lead()

        # Terminar con respuesta TwiML
        response = VoiceResponse()
        response.say("Disculpe, parece que entró el buzón de voz. Le llamaré en otro momento. Que tenga buen día.", language="es-MX")
        response.hangup()
        return Response(str(response), mimetype="text/xml")

    # FIX 109: Detectar operadora/contestadora automática por contenido
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
        "gracias por llamar", "bienvenido a"
    ]

    speech_lower = speech_result.lower() if speech_result else ""
    es_operadora = any(keyword in speech_lower for keyword in keywords_operadora)

    if es_operadora:
        print(f"📞 FIX 109: Operadora/IVR detectada por contenido del SpeechResult")
        print(f"   Mensaje: '{speech_result[:100]}...'")
        print(f"💬 Marcando como OPERADORA")

        # Obtener agente si existe
        agente = conversaciones_activas.get(call_sid)
        if agente:
            # Marcar como "Operadora" (similar a Buzón)
            agente.lead_data["estado_llamada"] = "Operadora"
            agente.lead_data["pregunta_0"] = "Operadora"
            agente.lead_data["pregunta_7"] = "OPERADORA"
            agente.lead_data["resultado"] = "NEGADO"
            print(f"📝 Estado actualizado: Operadora/IVR detectada")

            # Guardar la llamada
            agente.guardar_llamada_y_lead()

        # Terminar con respuesta TwiML
        response = VoiceResponse()
        response.say("Disculpe, parece que entró la operadora automática. Le llamaré en otro momento. Que tenga buen día.", language="es-MX")
        response.hangup()
        return Response(str(response), mimetype="text/xml")

    # Verificar si la llamada ya terminó (cliente colgó)
    if call_status in ["completed", "busy", "no-answer", "canceled", "failed"]:
        print(f"📞 Llamada terminada - Estado: {call_status}")
        print(f"💬 Cliente colgó o llamada desconectada")

        # Obtener agente si existe
        agente = conversaciones_activas.get(call_sid)
        if agente:
            # Marcar como "Colgo" si no hay otro estado especial
            if agente.lead_data["estado_llamada"] == "Respondio":
                agente.lead_data["estado_llamada"] = "Colgo"
                agente.lead_data["pregunta_0"] = "Colgo"
                agente.lead_data["pregunta_7"] = "Colgo"
                agente.lead_data["resultado"] = "NEGADO"
                print(f"📝 Estado actualizado: Cliente colgó")

            # Guardar la llamada
            agente.guardar_llamada_y_lead()

        # Terminar con respuesta TwiML
        response = VoiceResponse()
        response.hangup()
        return Response(str(response), mimetype="text/xml")

    # Obtener agente de esta conversación
    agente = conversaciones_activas.get(call_sid)

    if not agente:
        response = VoiceResponse()
        response.say("Error en la conversación.", language="es-MX")
        response.hangup()
        return Response(str(response), mimetype="text/xml")

    # LOG: Mostrar lo que dijo el cliente
    print(f"\n💬 CLIENTE DIJO: \"{speech_result}\"")

    # Registrar mensaje del cliente en LOGS
    if logs_manager and speech_result and agente.bruce_id:
        nombre_tienda = agente.lead_data.get('nombre_negocio', '')
        logs_manager.registrar_mensaje_cliente(agente.bruce_id, speech_result, nombre_tienda)

    # FIX 92: Detectar respuestas vacías y pedir repetición antes de colgar
    if not speech_result or speech_result.strip() == "":
        agente.respuestas_vacias_consecutivas += 1
        print(f"⚠️ Respuesta vacía #{agente.respuestas_vacias_consecutivas}")

        # FIX 145: Si es el PRIMER mensaje y está vacío, NO pedir repetición
        # Cliente normal necesita 2-3s para procesar "Hola, buen dia"
        # Contar mensajes de usuario para detectar si es primera respuesta
        mensajes_usuario = [msg for msg in agente.conversation_history if msg['role'] == 'user']
        es_primer_mensaje = len(mensajes_usuario) == 0

        if es_primer_mensaje:
            print(f"🚨 FIX 145: Primer mensaje vacío - Cliente necesita más tiempo para procesar saludo")
            print(f"   NO pedir repetición, solo esperar más tiempo...")
            agente.respuestas_vacias_consecutivas = 0  # No contar como vacía

            # Esperar más tiempo sin pedir repetición
            response = VoiceResponse()
            gather = response.gather(
                input="speech",
                action="/procesar-respuesta",
                method="POST",
                language="es-MX",
                speechTimeout="auto",
                timeout=5  # Dar 5s adicionales para que cliente procese
            )
            print(f"✅ FIX 145: Esperando respuesta del primer mensaje sin pedir repetición")
            return Response(str(response), mimetype="text/xml")

        # FIX 143: Si acabamos de responder a cliente desesperado, NO pedir repetición
        # El cliente necesita tiempo para procesar la confirmación "Sí, estoy aquí"
        if agente.acaba_de_responder_desesperado:
            print(f"🚨 FIX 143: Cliente desesperado acaba de recibir confirmación - NO pedir repetición")
            print(f"   Esperando a que cliente procese y responda...")
            agente.acaba_de_responder_desesperado = False  # Resetear flag
            agente.respuestas_vacias_consecutivas = 0  # Resetear contador

            # Simplemente esperar más tiempo sin pedir repetición
            response = VoiceResponse()
            gather = response.gather(
                input="speech",
                action="/procesar-respuesta",
                method="POST",
                language="es-MX",
                speechTimeout="auto",
                timeout=8  # Dar 8s para que cliente procese
            )
            print(f"✅ FIX 143: Esperando respuesta sin pedir repetición")
            return Response(str(response), mimetype="text/xml")

        # Primera o segunda vez: Pedir amablemente que repitan
        if agente.respuestas_vacias_consecutivas <= 2:
            print(f"🎙️ Bruce pedirá que le repitan (intento #{agente.respuestas_vacias_consecutivas})")

            # Frases variadas para pedir repetición
            frases_repeticion = [
                "Disculpa, no te escuché bien, ¿me puedes repetir?",
                "Perdón, no logré escucharte, ¿me lo repites por favor?",
                "No alcancé a escucharte, ¿me lo dices de nuevo?"
            ]

            # Alternar entre las frases según el intento
            respuesta_agente = frases_repeticion[(agente.respuestas_vacias_consecutivas - 1) % len(frases_repeticion)]

            # FIX 152: LOG cuando se reproduce "Disculpa no te escuché bien"
            print(f"🚨 FIX 152: REPRODUCIENDO MENSAJE DE REPETICIÓN")
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
            print(f"✅ Bruce pidió que le repitan")

            # Esperar respuesta del cliente
            gather = response.gather(
                input="speech",
                action="/procesar-respuesta",
                method="POST",
                language="es-MX",
                speechTimeout="auto",
                timeout=10
            )

            print(f"✅ Bruce pidió que le repitan")
            return Response(str(response), mimetype="text/xml")

        # Tercera vez: Cliente probablemente colgó
        else:
            print(f"📞 Detectadas 3 respuestas vacías consecutivas")
            print(f"💬 Cliente probablemente colgó o no responde")

            # Marcar como "Colgo" o "No Contesta" según el caso
            if agente.lead_data["estado_llamada"] == "Respondio":
                # Si había respondido antes, probablemente colgó
                agente.lead_data["estado_llamada"] = "Colgo"
                agente.lead_data["pregunta_0"] = "Colgo"
                agente.lead_data["pregunta_7"] = "Colgo"
                agente.lead_data["resultado"] = "NEGADO"
                print(f"📝 Estado actualizado: Cliente colgó (3 silencios)")

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

    print(f"🔍 FIX 121 DEBUG: len(conversation_history)={len(agente.conversation_history)}, mensajes_usuario={len(mensajes_usuario)}, es_primera_respuesta={es_primera_respuesta}")

    # Saludos simples del cliente
    saludos_simples = [
        "hola", "bueno", "buenos días", "buenos dias", "buen día", "buen dia",
        "diga", "dígame", "digame", "sí", "si", "aló", "alo", "buenas",
        "qué onda", "que onda", "mande", "a sus órdenes", "a sus ordenes"
    ]

    # FIX 121: Si es saludo simple en primera respuesta, usar caché inmediato
    usa_segunda_parte_saludo = False
    if es_primera_respuesta and any(saludo in speech_lower for saludo in saludos_simples):
        # Verificar que la respuesta sea SOLO el saludo (no más de 5 palabras)
        palabras = speech_result.split()
        if len(palabras) <= 5:
            usa_segunda_parte_saludo = True
            print(f"🚀 FIX 121: Saludo simple detectado en primera respuesta: '{speech_result}'")
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
                print(f"🚨 FIX 70: Objeción detectada en historial - DESHABILITANDO CACHE")
                print(f"   Frase: '{frase_obj}'")
                break
        if tiene_objeciones_activas:
            break

    # FIX 71: DESHABILITAR CACHE COMPLETAMENTE hasta resolver loops
    # El cache estaba causando respuestas sin contexto que ignoraban objeciones
    print(f"🚨 FIX 71: CACHE DESHABILITADO TEMPORALMENTE - Usando solo GPT con contexto completo")
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
        print(f"🚀 FIX 121: INICIANDO respuesta desde caché de segunda parte...")

        # FIX 131: Verificar si Bruce YA dijo la segunda parte (cliente interrumpió)
        # Si hay 2+ mensajes de Bruce, significa que ya se dijo la segunda parte
        mensajes_bruce_previos = [msg for msg in agente.conversation_history if msg['role'] == 'assistant']
        bruce_ya_dijo_segunda_parte = len(mensajes_bruce_previos) >= 2

        if bruce_ya_dijo_segunda_parte:
            # Cliente interrumpió mientras Bruce hablaba el 2do mensaje
            # NO usar caché, usar GPT para responder con nexo
            print(f"⚠️ FIX 131: Cliente interrumpió en 2do mensaje - NO usar caché")
            print(f"   Cliente dijo: '{speech_result}' mientras Bruce hablaba segunda parte")
            print(f"   Usando GPT con instrucción de nexo en lugar de caché")

            # Deshabilitar caché para que use GPT normal con detección de interrupción
            usa_segunda_parte_saludo = False

            # Agregar mensaje del cliente al historial ANTES de GPT
            agente.conversation_history.append({
                "role": "user",
                "content": speech_result
            })

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
            print(f"✅ FIX 121: Respuesta instantánea desde caché completada en {tiempo_cache:.3f}s")

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
                print(f"🎯 FIX 97: Audio cacheado detectado: {cache_key_audio}")
                result = generar_audio_elevenlabs(respuesta_texto, audio_id_temp, usar_cache_key=cache_key_audio)
            else:
                # FIX 98: SIEMPRE usar voz de Bruce (ElevenLabs), sin importar longitud
                palabras = len(respuesta_texto.split())
                print(f"🎵 FIX 98: Generando audio con ElevenLabs VOZ BRUCE ({palabras} palabras)")
                result = generar_audio_elevenlabs(respuesta_texto, audio_id_temp)

            # FIX 102: Logging detallado del resultado
            print(f"🔍 FIX 102 DEBUG: result = {result}, type = {type(result)}")

            # Guardar resultado en contenedor
            if result is not None:
                audio_container["audio_id"] = audio_id_temp
                audio_container["usa_cache"] = usa_cache_audio
                audio_container["cache_key"] = cache_key_audio
                print(f"✅ FIX 102: Audio container guardado - audio_id={audio_id_temp}")
            else:
                audio_container["audio_id"] = None  # Usar Twilio TTS
                print(f"⚠️ FIX 102: generar_audio_elevenlabs() retornó None - usará Twilio TTS")

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

    # FIX 132: Detectar si cliente está desesperado (repite saludos múltiples veces)
    cliente_desesperado = False
    if len(speech_result.split()) >= 5:
        # Cliente dijo 5+ palabras
        speech_lower = speech_result.lower()
        # Buscar repeticiones de saludos/preguntas
        patrones_desesperacion = [
            "hola", "buenos días", "buen día", "me escuchas", "me escucha",
            "está ahí", "estas ahi", "hay alguien", "bueno", "aló"
        ]

        # Contar cuántos patrones aparecen
        count_patrones = sum(1 for patron in patrones_desesperacion if patron in speech_lower)

        # Si aparecen 2+ patrones diferentes, cliente está desesperado
        if count_patrones >= 2:
            cliente_desesperado = True
            agente.acaba_de_responder_desesperado = True  # FIX 143: Marcar para no pedir repetición después
            print(f"⚠️ FIX 132: Cliente desesperado detectado - '{speech_result}'")
            print(f"   Reduciendo timeout de espera a 0.5s para responder INMEDIATAMENTE")

    # FIX 58/97: Si la respuesta vino del caché, NO esperar ni reproducir "pensando"
    # El caché es instantáneo (0s), no necesita señal auditiva
    if not respuesta_container.get("desde_cache", False):
        # FIX 50/97/102: REDUCIR DELAY - Mientras GPT piensa, reproducir sonido de "pensando"
        # Esto mantiene al cliente en la línea y evita que piense que Bruce colgó

        # FIX 146: Reducir delay para cliente desesperado de 0.5s a 0s (meta: 3s total)
        # Si es saludo simple en primera respuesta, esperar solo 1s
        # Sino, esperar 3s normal (antes 5s)
        if cliente_desesperado:
            timeout_espera = 0  # FIX 146: Responder INMEDIATAMENTE (0s) - meta 3s total
        elif usa_segunda_parte_saludo or es_primera_respuesta:
            timeout_espera = 1.0  # Saludo simple - responder rápido
        else:
            timeout_espera = 3.0  # FIX 147: Normal 5s→3s - reducir delays generales

        print(f"⏱️ FIX 132: Esperando {timeout_espera}s antes de señal auditiva")
        gpt_thread.join(timeout=timeout_espera)

    if not respuesta_container["completado"] and not respuesta_container.get("desde_cache", False):
        # GPT+Audio aún procesando - dar señal auditiva

        # FIX 133: Si cliente está desesperado, responder INMEDIATAMENTE y esperar GPT
        if cliente_desesperado:
            print(f"🚨 FIX 133: Cliente desesperado - confirmando presencia INMEDIATAMENTE")

            # Esperar a que GPT termine (máximo 5s más)
            gpt_thread.join(timeout=5.0)

            if not respuesta_container["completado"]:
                # GPT aún no termina - dar confirmación y seguir esperando
                print(f"⏳ FIX 133 + FIX 162A: GPT aún procesando - usando audio de relleno")
                # FIX 162A: Usar audio de relleno en lugar de Twilio
                if "un_momento" in audio_cache:
                    audio_url = request.url_root + "audio_cache/un_momento"
                    response.play(audio_url)
                elif "pensando_1" in audio_cache:
                    audio_url = request.url_root + "audio_cache/pensando_1"
                    response.play(audio_url)

                # Esperar otros 5s (total 10.5s máximo)
                gpt_thread.join(timeout=5.0)

                if not respuesta_container["completado"]:
                    # GPT tardó más de 10.5s - timeout
                    print(f"❌ FIX 133: GPT timeout después de 10.5s")
                    response.say("Lo siento, estoy teniendo problemas técnicos. Le llamaré más tarde.", language="es-MX")
                    response.hangup()
                    return Response(str(response), mimetype="text/xml")

            # GPT terminó - continuar con respuesta normal
            print(f"✅ FIX 133: GPT completado - continuando con respuesta")
        else:
            print(f"⏳ GPT+Audio procesando - reproduciendo tono de pensando...")
            # FIX 54B: Usar frases variables pre-cacheadas con VOZ DE BRUCE
            # Seleccionar aleatoriamente una de las 8 frases de "pensando"
            pensando_keys = [f"pensando_{i}" for i in range(1, 9)]
            pensando_key = random.choice(pensando_keys)

            # Verificar si existe en caché
            if pensando_key in audio_cache:
                # Reproducir audio pre-generado con voz de Bruce (0s delay)
                audio_url = request.url_root + f"audio_cache/{pensando_key}"
                print(f"💭 Bruce dice (voz Bruce): '{pensando_key}' desde caché")
                response.play(audio_url)
            else:
                # FIX 162A: Si no está en caché, usar cualquier audio de relleno disponible
                print(f"⚠️ FIX 162A: '{pensando_key}' no en caché, buscando alternativa")
                if "dejeme_ver" in audio_cache:
                    response.play(request.url_root + "audio_cache/dejeme_ver")
                elif "un_momento" in audio_cache:
                    response.play(request.url_root + "audio_cache/un_momento")
                # Si no hay ninguno, continuar sin audio

        # FIX 102: Esperar otros 5 segundos (total 10s máximo)
        gpt_thread.join(timeout=5.0)

        if not respuesta_container["completado"]:
            # GPT tardó más de 10 segundos total - timeout real
            print(f"❌ GPT timeout después de 10s")
            response.say("Lo siento, estoy teniendo problemas técnicos. Le llamaré más tarde.", language="es-MX")
            response.hangup()
            return Response(str(response), mimetype="text/xml")

    respuesta_agente = respuesta_container["respuesta"]
    tiempo_gpt = time.time() - inicio
    print(f"⏱️ GPT tardó: {tiempo_gpt:.2f}s")
    print(f"🤖 BRUCE DICE: \"{respuesta_agente}\"")

    # FIX 75/76: VERIFICAR SI DEBE COLGAR INMEDIATAMENTE (objeción terminal detectada)
    if agente.lead_data["estado_llamada"] == "Colgo":
        print(f"🚨🚨🚨 FIX 75: Estado 'Colgo' detectado - Terminando llamada después de despedida")
        print(f"   Razón: {agente.lead_data.get('pregunta_7', 'Objeción terminal')}")

        # FIX 76: Generar audio con voz de Bruce (ElevenLabs) usando caché
        audio_id_despedida = f"respuesta_{call_sid}_objecion_final"
        cache_key_despedida = "despedida_objecion"  # Caché para "Entiendo perfectamente. Muchas gracias..."

        # Intentar usar caché, si no existe generar con ElevenLabs
        result_despedida = generar_audio_elevenlabs(respuesta_agente, audio_id_despedida, usar_cache_key=cache_key_despedida)

        if result_despedida is not None:
            # Audio generado con ElevenLabs (voz Bruce)
            audio_url_despedida = request.url_root + f"audio/{audio_id_despedida}"
            print(f"✅ FIX 76: Usando voz Bruce (ElevenLabs) para despedida de objeción")
            response.play(audio_url_despedida)
        else:
            # FIX 162A: ElevenLabs falló - usar despedida simple pre-cacheada
            print(f"🚨 FIX 162A: ElevenLabs FALLÓ en despedida - usando caché de despedida simple")
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
        print(f"📦 FIX 119: Audio de segunda_parte_saludo desde caché (0s delay, sin espera)")
    else:
        # FIX 102: Esperar a que el audio termine de generarse (máximo 3s adicionales)
        # Si GPT terminó pero audio aún está generándose, esperar a que complete
        if not audio_container.get("completado", False):
            print(f"⏳ FIX 102: Esperando que audio ElevenLabs termine de generarse...")
            import time
            max_wait = 3.0  # Esperar máximo 3 segundos adicionales por el audio
            waited = 0
            while not audio_container.get("completado", False) and waited < max_wait:
                time.sleep(0.1)
                waited += 0.1

            if audio_container.get("completado", False):
                print(f"✅ FIX 102: Audio completado después de {waited:.1f}s adicionales")
            else:
                print(f"⚠️ FIX 102: Audio NO completó después de {max_wait}s - usará Twilio TTS")

        # FIX 97: Usar audio ya generado en paralelo (o None si debe usar Twilio TTS)
        # El thread ya generó el audio mientras esperábamos, así que está listo AHORA
        audio_id = audio_container.get("audio_id")
        usa_cache = audio_container.get("usa_cache", False)
        cache_key = audio_container.get("cache_key")

    tiempo_total = time.time() - inicio
    print(f"⏱️ TOTAL delay (GPT + Audio en paralelo): {tiempo_total:.2f}s")

    if audio_id:
        if usa_cache:
            print(f"📦 FIX 97: Audio desde caché: {cache_key} (generado en paralelo)")
        else:
            print(f"🎵 FIX 97: Audio ElevenLabs (generado en paralelo)")
    else:
        print(f"⚡ FIX 97: Usar Twilio TTS (respuesta larga o error)")

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
        print(f"🔚 Detectada despedida en: {respuesta_agente[:50]}...")

        # FIX 158: Marcar que Bruce se despidió primero
        agente.bruce_se_despidio = True

        # IMPORTANTE: Esperar respuesta del cliente por educación antes de colgar
        print(f"⏳ Esperando despedida del cliente por cortesía...")

        # FIX 60/61: Crear Gather para escuchar despedida del cliente (con Whisper)
        gather_despedida = Gather(
            input="speech",
            language="es-MX",
            timeout=3,  # Esperar hasta 3 segundos
            speech_timeout=2,  # FIX 60: Ya optimizado (corto para despedidas)
            action="/despedida-final",
            method="POST",
            speech_model="experimental_conversations"  # FIX 61: RecordingUrl para Whisper
        )

        # FIX 96: Reproducir audio DENTRO del Gather para estar listo desde que empieza
        if audio_id is None:
            # FIX 162A: ElevenLabs falló - usar despedida simple pre-cacheada
            print(f"🚨 FIX 162A: ElevenLabs FALLÓ en despedida gather - usando caché de despedida")
            print(f"   Despedida que falló: {respuesta_agente[:100]}...")
            print(f"   Call SID: {call_sid}")
            # Usar despedida simple del caché
            if "despedida_simple" in audio_cache:
                gather_despedida.play(request.url_root + "audio_cache/despedida_simple")
            # Si no hay despedida, continuar sin audio (mejor que cambiar voz)
        else:
            # Caso: Respuesta corta o cacheada - usar audio de ElevenLabs
            audio_url = request.url_root + f"audio/{audio_id}"
            gather_despedida.play(audio_url)

        response.append(gather_despedida)

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

            # Indirectas de ocupado
            "está ocupado", "no puede en este momento", "no puede ahorita",
            "está en junta", "está en una junta", "no está disponible",
            "está con un cliente", "ahorita está ocupado"
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

    if cliente_pidio_momento:
        timeout_gather = 10  # FIX 131: 10s cuando cliente pide "un momento" o variantes (antes 8s)
        print(f"⏱️ FIX 131: Timeout={timeout_gather}s (cliente pidió esperar: '{ultimo_mensaje_cliente}')")
    elif cliente_dictando_correo:
        timeout_gather = 15  # FIX 155: 15s cuando cliente está DICTANDO correo (email completo puede tomar 10-15s)
        print(f"⏱️ FIX 155: Timeout={timeout_gather}s (cliente dictando correo - NO interrumpir)")
    elif cliente_desesperado:
        timeout_gather = 5  # FIX 135: 5s cuando cliente está desesperado (necesita procesar confirmación)
        print(f"⏱️ FIX 135: Timeout={timeout_gather}s (cliente desesperado - dio confirmación)")
    elif ultimo_mensaje_bruce and any(keyword in ultimo_mensaje_bruce for keyword in keywords_pide_correo):
        timeout_gather = 4  # FIX 127: 4s cuando pide correo (antes 2s, cliente necesita tiempo PARA PENSAR)
        print(f"⏱️ FIX 127: Timeout={timeout_gather}s (pedir correo/WhatsApp)")
    elif es_segundo_mensaje:
        timeout_gather = 3  # FIX 124: 3s para segundo mensaje (largo, cliente necesita procesar)
        print(f"⏱️ FIX 124: Timeout={timeout_gather}s (segundo mensaje inicial - 25 palabras)")
    else:
        timeout_gather = 4  # FIX 151: 4s conversación normal (antes 1s - causaba "Disculpa no te escuché bien" innecesario)
        print(f"⏱️ FIX 151: Timeout={timeout_gather}s (conversación normal - dar tiempo para procesar)")

    # FIX 125/154/156/157: Permitir interrupciones SOLO en saludo inicial
    # FIX 156: REDUCIDO de 2 a 1 - ciclo persiste con barge_in en mensaje #2
    # FIX 157: DESHABILITADO completamente - ni siquiera en mensaje #1
    # Problema original (FIX 125): Cliente dice "Sí dígame" mientras Bruce habla, no se detecta → silencio 14s
    # FIX 154: Reducido de 3 a 2 - no fue suficiente
    # FIX 156: Solo mensaje #1 - cliente desesperado detectado en saludo, después NO interrumpir
    # FIX 157: Ciclo PERSISTE incluso con mensaje #1 - respuestas válidas ("dígame", "hola") detectadas como interrupción
    #   SOLUCIÓN: barge_in=False SIEMPRE - cliente puede interrumpir presionando tecla, pero no por voz
    permitir_interrupcion = False  # FIX 157: Deshabilitado completamente - elimina ciclo de interrupciones

    gather = Gather(
        input="speech",
        language="es-MX",
        timeout=timeout_gather,  # FIX 116: Progresivo según num_mensajes
        speech_timeout="auto",  # FIX 112: 1s→auto - Twilio detecta fin automáticamente
        action="/procesar-respuesta",
        method="POST",
        speech_model="experimental_conversations",  # FIX 61: RecordingUrl para Whisper
        barge_in=permitir_interrupcion  # FIX 125: True para primeros 3 mensajes, False después
    )

    print(f"🎙️ FIX 157: barge_in={permitir_interrupcion} DESHABILITADO (mensaje #{num_mensajes_bruce} - elimina ciclo)")

    # FIX 141: Si cliente está desesperado, agregar confirmación DENTRO del Gather ANTES de respuesta
    if cliente_desesperado:
        print(f"🚨 FIX 141: Agregando confirmación DENTRO de Gather (se reproduce ANTES de respuesta)")

        # FIX 138A: Usar caché para respuesta instantánea (0s en lugar de 0.91s)
        audio_id_confirmacion = f"confirmacion_desesperado_{call_sid}"

        # Generar usando caché (0s delay)
        result_confirmacion = generar_audio_elevenlabs(
            "Sí, estoy aquí.",
            audio_id_confirmacion,
            usar_cache_key="confirmacion_presencia"  # FIX 138A: Caché pregenerado
        )

        if result_confirmacion:
            audio_url_confirmacion = request.url_root + f"audio/{audio_id_confirmacion}"
            print(f"✅ FIX 141: Confirmación generada - agregando DENTRO de Gather")
            # FIX 141: Agregar DENTRO del Gather para que se reproduzca en secuencia
            gather.play(audio_url_confirmacion)
        else:
            # FIX 162A: NO usar Twilio - usar audio de relleno
            print(f"⚠️ FIX 162A: Caché falló - usando audio de relleno")
            if "pensando_1" in audio_cache:
                gather.play(request.url_root + "audio_cache/pensando_1")
            # Si falla, continuar sin audio (mejor que cambiar de voz)

    # FIX 96/98: Reproducir audio SIEMPRE con voz de Bruce (ElevenLabs) DENTRO del Gather
    if audio_id is None:
        # FIX 162A: ElevenLabs falló - NO usar Twilio, usar audio de relleno
        print(f"🚨 FIX 162A: ElevenLabs FALLÓ después de retry - usando audio de relleno")
        print(f"   Respuesta que falló: {respuesta_agente[:100]}...")
        print(f"   Call SID: {call_sid}")

        # Usar audio de relleno en lugar de Twilio
        if "dejeme_ver" in audio_cache:
            print(f"🎵 FIX 162A: Usando audio de relleno 'dejeme_ver'")
            gather.play(request.url_root + "audio_cache/dejeme_ver")
        elif "un_momento" in audio_cache:
            print(f"🎵 FIX 162A: Usando audio de relleno 'un_momento'")
            gather.play(request.url_root + "audio_cache/un_momento")
        # Si no hay audios de relleno, continuar sin audio (mejor que voz Twilio)
    else:
        # Usar audio de ElevenLabs (voz Bruce) - SIEMPRE preferido
        audio_url = request.url_root + f"audio/{audio_id}"
        gather.play(audio_url)

    response.append(gather)

    # FIX 137: Eliminado "¿Sigue ahí?" - causaba confusión y bugs
    # Si cliente no responde, redirigir directamente a procesar-respuesta (timeout)
    response.redirect("/procesar-respuesta")

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

    print(f"\n👋 DESPEDIDA FINAL - Call SID: {call_sid}")
    if cliente_respuesta:
        print(f"💬 CLIENTE SE DESPIDE: \"{cliente_respuesta}\"")
    else:
        print(f"🔇 Cliente no respondió despedida (silencio)")

    # Obtener agente de la conversación activa
    agente = conversaciones_activas.get(call_sid)

    # ADDED - Registrar despedida del cliente en LOGS
    if logs_manager and cliente_respuesta and agente and agente.bruce_id:
        nombre_tienda = agente.lead_data.get('nombre_negocio', '')
        logs_manager.registrar_mensaje_cliente(agente.bruce_id, cliente_respuesta, nombre_tienda)

    # Guardar lead y llamada en Google Sheets
    if agente:
        print(f"💾 Guardando llamada {call_sid} en Google Sheets...")
        try:
            agente.guardar_llamada_y_lead()
            print(f"✅ Llamada {call_sid} guardada correctamente")

            # Manejo post-guardado: Buzón y Reprogramación
            if sheets_manager and agente.contacto_info:
                fila = agente.contacto_info.get('fila') or agente.contacto_info.get('ID')

                # 1. Manejo de BUZÓN/OPERADORA - Marcar intentos y reintentar
                # FIX 109: Incluir Operadora en sistema de reintentos
                estado = agente.lead_data.get("estado_llamada")
                if estado in ["Buzon", "Operadora"] and fila:
                    tipo_deteccion = "buzón" if estado == "Buzon" else "operadora"
                    print(f"\n📞 Llamada cayó en {tipo_deteccion} - manejando reintento...")
                    intentos = sheets_manager.marcar_intento_buzon(fila)

                    if intentos == 1:
                        # PRIMER intento de buzón/operadora - REINTENTO INMEDIATO
                        print(f"📞 Primer intento de {tipo_deteccion} - iniciando reintento inmediato...")
                        print(f"⏰ Esperando 30 segundos antes de reintentar...")

                        # Capturar url_root ANTES del thread (Flask context)
                        base_url = request.url_root.replace('http://', 'https://')

                        def hacer_reintento():
                            import time
                            import requests
                            time.sleep(30)  # Esperar 30 segundos

                            telefono_destino = agente.contacto_info.get('telefono')
                            nombre_negocio = agente.contacto_info.get('nombre_negocio', 'cliente')

                            print(f"📞 Iniciando segundo intento a {telefono_destino}...")

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
                                    print(f"✅ Segundo intento iniciado correctamente")
                                else:
                                    print(f"⚠️ Error en reintento: {response_call.status_code}")

                            except Exception as e:
                                print(f"❌ Error iniciando reintento: {e}")

                        # Ejecutar reintento en background
                        import threading
                        thread = threading.Thread(target=hacer_reintento)
                        thread.daemon = True
                        thread.start()

                    else:
                        print(f"📞 Intento de buzón #{intentos} - no se hará reintento automático")

                # 2. Manejo de REFERENCIAS - Llamar automáticamente al referido
                telefono_referencia = agente.lead_data.get("referencia_telefono")
                if telefono_referencia and fila:
                    print(f"\n👥 Procesando referencia...")
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
                        print(f"✅ Referencia guardada en fila {fila_referido} (columna U)")

                        # Guardar contexto de reprogramación en el contacto ACTUAL (quien dio la referencia)
                        contexto_reprog = f"Reprog: Referencia dada | Pasó contacto de {nombre_ref or 'encargado'} ({telefono_referencia})"
                        sheets_manager.guardar_contexto_reprogramacion(fila, contexto_reprog)
                        print(f"✅ Contexto de referencia guardado en fila {fila} (columna W)")

                        # Iniciar llamada automática al referido
                        print(f"\n📞 Iniciando llamada automática al referido...")
                        print(f"     🌐 Enviando solicitud a {base_url}iniciar-llamada")
                        print(f"     📱 Teléfono: {telefono_referencia}")
                        print(f"     📋 Fila: {fila_referido}")

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
                                print(f"     ✅ Llamada iniciada exitosamente!")
                                print(f"     📞 Call SID: {result.get('call_sid', 'N/A')}")
                            else:
                                print(f"     ⚠️ Error en llamada automática: {response_ref.status_code}")

                        except Exception as e:
                            print(f"     ❌ Error iniciando llamada automática: {e}")

                # 3. Marcar llamada en columna U (registro de contacto)
                # No bloquear llamadas futuras - columnas U/V/W son solo para contexto
                telefono_actual = agente.lead_data.get("telefono", "")
                if telefono_actual and fila:
                    telefono_llamado = agente.contacto_info.get('telefono', telefono_actual)

                    # Verificar si ya fue llamado antes (para el mensaje de log)
                    es_primera = not sheets_manager.verificar_contacto_ya_llamado(fila)

                    sheets_manager.marcar_primera_llamada(fila, numero_llamado=telefono_llamado)

                    if es_primera:
                        print(f"📝 Primera llamada registrada en columna U con número: {telefono_llamado}")
                    else:
                        print(f"📝 Llamada subsecuente registrada en columna U con número: {telefono_llamado}")

        except Exception as e:
            print(f"❌ Error guardando llamada {call_sid}: {e}")
            import traceback
            traceback.print_exc()

        # Limpiar memoria
        del conversaciones_activas[call_sid]
        if call_sid in contactos_llamadas:
            del contactos_llamadas[call_sid]

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
                method="POST",
                record=True  # Grabar llamada automáticamente
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

    print(f"\n📞 STATUS CALLBACK - Llamada {call_sid[:10]}...")
    print(f"   Estado: {call_status}")
    print(f"   Duración: {call_duration}s")
    if answered_by:
        print(f"   AnsweredBy: {answered_by}")

    # NUEVO: Manejo de buzón detectado por Twilio - REINTENTO INMEDIATO
    # Detectar buzón por AnsweredBy O por call_status="no-answer"
    es_buzon = (
        answered_by in ["machine_start", "machine_end_beep", "machine_end_silence", "machine_end_other"] or
        call_status == "no-answer"
    )

    if es_buzon:
        if answered_by:
            print(f"   📞 Buzón detectado por AnsweredBy: {answered_by}")
        else:
            print(f"   📞 Buzón detectado por CallStatus: {call_status} (no-answer)")

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
            print(f"   📞 Intento de buzón #{intentos} registrado")

            if intentos == 1:
                # PRIMER intento - REINTENTO INMEDIATO
                print(f"   🔄 Primer buzón - programando reintento inmediato...", flush=True)
                print(f"   ⏰ Esperando 30 segundos...", flush=True)
                print(f"   📋 Datos del reintento: tel={telefono}, fila={fila}, base_url={request.url_root}", flush=True)

                import time
                import threading

                # IMPORTANTE: Capturar url_root ANTES del thread (Flask context)
                # Forzar HTTPS para Railway (evita redirect 301/302 que causa 405)
                base_url = request.url_root.replace('http://', 'https://')

                def hacer_reintento():
                    import sys
                    print(f"\n🔄 Thread iniciado - esperando 30s...", flush=True)
                    time.sleep(30)
                    print(f"\n📞 Iniciando reintento inmediato a {telefono}...", flush=True)

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
                            print(f"   ✅ Reintento iniciado: {data.get('call_sid', 'Unknown')}", flush=True)
                        else:
                            print(f"   ⚠️ Error en reintento: {response_call.status_code}", flush=True)
                    except Exception as e:
                        print(f"   ❌ Error iniciando reintento: {e}", flush=True)

                # Ejecutar reintento en thread separado para no bloquear el callback
                print(f"   🧵 Creando thread para reintento...", flush=True)
                thread = threading.Thread(target=hacer_reintento)
                thread.daemon = True
                thread.start()
                print(f"   ✅ Thread iniciado correctamente (daemon={thread.daemon}, alive={thread.is_alive()})", flush=True)

            # FIX 89: GUARDAR en "Respuestas de formulario 1" cuando es buzón después del segundo intento
            elif intentos >= 2:
                print(f"   💾 Segundo intento de buzón - guardando en Respuestas de formulario 1...")

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
                        print(f"   ⚠️ Error creando agente temporal: {e}")

                # Guardar el buzón
                if agente:
                    agente.lead_data["estado_llamada"] = "Buzon"
                    agente.lead_data["pregunta_0"] = "Buzon"
                    agente.lead_data["pregunta_7"] = "BUZON"
                    agente.lead_data["resultado"] = "NEGADO"

                    try:
                        agente.guardar_llamada_y_lead()
                        print(f"   ✅ Buzón guardado en Respuestas de formulario 1")
                    except Exception as e:
                        print(f"   ⚠️ Error guardando buzón: {e}")
                else:
                    print(f"   ⚠️ No se pudo obtener agente para guardar buzón")

    # FIX 95: Manejo de llamadas FALLIDAS (failed, busy, canceled)
    if call_status in ["failed", "busy", "canceled"]:
        print(f"   ⚠️ Llamada fallida - Estado: {call_status}")

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

            print(f"   📋 Fila {fila}: {nombre_negocio} - {telefono}")
            if sip_code:
                print(f"   ⚠️ SIP Response Code: {sip_code}")

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

                # Guardar en "Respuestas de formulario 1"
                agente.guardar_llamada_y_lead()
                print(f"   ✅ Llamada fallida guardada: {estado}")

            except Exception as e:
                print(f"   ❌ Error guardando llamada fallida: {e}")
                import traceback
                traceback.print_exc()

    # Si la llamada terminó y el agente aún existe en memoria
    if call_status == "completed" and call_sid in conversaciones_activas:
        agente = conversaciones_activas[call_sid]

        # Verificar si fue buzón de voz
        if answered_by in ["machine_start", "machine_end_beep", "machine_end_silence", "machine_end_other"]:
            if agente.lead_data["estado_llamada"] == "Respondio":
                print(f"   📞 Buzón de voz - detectado por status callback")
                agente.lead_data["estado_llamada"] = "Buzon"
                agente.lead_data["pregunta_0"] = "Buzon"
                agente.lead_data["pregunta_7"] = "BUZON"
                agente.lead_data["resultado"] = "NEGADO"

                # Guardar la llamada
                try:
                    agente.guardar_llamada_y_lead()
                    print(f"   ✅ Buzón guardado desde status callback")
                except Exception as e:
                    print(f"   ⚠️ Error guardando buzón desde status callback: {e}")

        # Si no fue buzón, determinar si colgó o no respondió
        elif agente.lead_data["estado_llamada"] == "Respondio":
            # FIX 158: NO sobrescribir si Bruce YA se despidió primero
            # Verificar si Bruce terminó con despedida
            bruce_se_despidio = getattr(agente, 'bruce_se_despidio', False)

            if bruce_se_despidio:
                print(f"   ✅ FIX 158: Bruce se despidió primero - NO clasificar como 'Colgó'")
                print(f"   📞 Llamada terminó normalmente - cliente respondió y Bruce completó despedida")
                # NO cambiar estado - mantener "Respondio" y el resultado que Bruce determinó
            else:
                # Verificar si hubo intercambio de conversación
                # Si hay menos de 2 mensajes en el historial, el cliente nunca respondió
                num_mensajes = len(agente.conversation_history)

                if num_mensajes <= 1:
                    # Cliente nunca respondió al saludo inicial
                    print(f"   📞 Cliente no respondió - detectado por status callback (solo {num_mensajes} mensaje)")
                    agente.lead_data["estado_llamada"] = "No Respondio"
                    agente.lead_data["pregunta_0"] = "No Respondio"
                    agente.lead_data["pregunta_7"] = "No Respondio"
                    agente.lead_data["resultado"] = "NEGADO"
                else:
                    # Hubo conversación, entonces sí colgó
                    print(f"   💬 Cliente colgó - detectado por status callback ({num_mensajes} mensajes)")
                    agente.lead_data["estado_llamada"] = "Colgo"
                    agente.lead_data["pregunta_0"] = "Colgo"
                    agente.lead_data["pregunta_7"] = "Colgo"
                    agente.lead_data["resultado"] = "NEGADO"

            # Guardar la llamada
            try:
                agente.guardar_llamada_y_lead()
                print(f"   ✅ Llamada guardada desde status callback")
            except Exception as e:
                print(f"   ⚠️ Error guardando desde status callback: {e}")

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
                    print(f"⚠️  No se pudo eliminar {archivo}: {e}")

            print(f"🗑️  {archivos_eliminados} archivos eliminados del caché")

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
                    max-width: 1200px;
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
                    max-width: 600px;
                    word-wrap: break-word;
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
            <h1>🎤 Estadísticas de Caché - Bruce W</h1>

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
                    🎤 Generar Audios Seleccionados
                </button>
            </div>

            <h2>📊 Frases por Frecuencia de Uso</h2>
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
            estado = '<span class="cached">✅ En caché</span>' if en_cache else '<span class="not-cached">⏳ No cacheado</span>'

            # Limitar longitud de frase para visualización
            frase_display = texto if len(texto) <= 100 else texto[:100] + "..."

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
                    btn.textContent = '⏳ Generando ' + frases.length + ' audios...';

                    try {
                        const response = await fetch('/generate-cache', {
                            method: 'POST',
                            headers: {'Content-Type': 'application/json'},
                            body: JSON.stringify({frases: frases})
                        });

                        const result = await response.json();

                        if (result.success) {
                            alert('✅ ' + result.generated + ' audios generados correctamente!');
                            location.reload(); // Recargar para ver cambios
                        } else {
                            alert('❌ Error: ' + result.error);
                        }
                    } catch (error) {
                        alert('❌ Error al generar audios: ' + error.message);
                    }

                    btn.disabled = false;
                    btn.textContent = '🎤 Generar Audios Seleccionados';
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
                print(f"⏭️ Omitido: {key} (ya está en caché)")
                continue
            elif key in audio_cache and force:
                print(f"🔄 Regenerando: {key} (force=True)")

            try:
                print(f"\n🎤 Generando audio para: {texto[:50]}...")

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
                except:
                    pass

                generated_count += 1
                print(f"✅ Audio generado y cacheado: {key}")

            except Exception as e:
                error_msg = f"Error en '{texto[:30]}...': {str(e)}"
                errors.append(error_msg)
                print(f"❌ {error_msg}")

        # Respuesta
        result = {
            "success": True,
            "generated": generated_count,
            "total_requested": len(frases),
            "errors": errors if errors else None
        }

        print(f"\n✅ Generación completada: {generated_count}/{len(frases)} audios")
        return result

    except Exception as e:
        print(f"❌ Error en generate-cache: {e}")
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
            diagnostico["test_escritura"] = "✅ OK"
        except Exception as e:
            diagnostico["test_escritura"] = f"❌ FALLO: {str(e)}"

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
            <h1>🔍 Diagnóstico de Persistencia - Railway</h1>

            <div class="section">
                <h2>📁 Información del Directorio</h2>
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
                            {'✅ SÍ' if diagnostico['existe'] else '❌ NO'}
                        </td>
                    </tr>
                    <tr>
                        <td class="key">Es directorio:</td>
                        <td class="{'ok' if diagnostico['es_directorio'] else 'error'}">
                            {'✅ SÍ' if diagnostico['es_directorio'] else '❌ NO'}
                        </td>
                    </tr>
                </table>
            </div>

            <div class="section">
                <h2>🔐 Permisos</h2>
                <table>
                    <tr>
                        <td class="key">Lectura (R):</td>
                        <td class="{'ok' if diagnostico['readable'] else 'error'}">
                            {'✅ OK' if diagnostico['readable'] else '❌ FALLO'}
                        </td>
                    </tr>
                    <tr>
                        <td class="key">Escritura (W):</td>
                        <td class="{'ok' if diagnostico['writable'] else 'error'}">
                            {'✅ OK' if diagnostico['writable'] else '❌ FALLO'}
                        </td>
                    </tr>
                    <tr>
                        <td class="key">Ejecución (X):</td>
                        <td class="{'ok' if diagnostico['executable'] else 'error'}">
                            {'✅ OK' if diagnostico['executable'] else '❌ FALLO'}
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
                <h2>📊 Archivos en Disco</h2>
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
                            {'✅ Existe (' + str(diagnostico.get('metadata_tamano_kb', 0)) + ' KB)' if diagnostico['metadata_existe'] else '⚠️ No existe'}
                        </td>
                    </tr>
                    <tr>
                        <td class="key">frase_stats.json:</td>
                        <td class="{'ok' if diagnostico['stats_existe'] else 'warning'}">
                            {'✅ Existe (' + str(diagnostico.get('stats_tamano_kb', 0)) + ' KB)' if diagnostico['stats_existe'] else '⚠️ No existe'}
                        </td>
                    </tr>
                </table>
            </div>

            <div class="section">
                <h2>💾 Caché en Memoria</h2>
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
                <h2>🌍 Variables de Entorno</h2>
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
                <h2>📄 Últimos Archivos (Top 20)</h2>
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
                <h2>✅ Recomendaciones</h2>
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
                    print(f"\n🎯 FIX 65: Pre-generando audio para nueva categoría '{categoria}'...")
                    audio_id = f"cache_{categoria}"
                    generar_audio_elevenlabs(respuesta, audio_id, usar_cache_key=categoria)
                    print(f"   ✅ Audio pre-generado exitosamente")
                except Exception as e:
                    print(f"   ⚠️ Error pre-generando audio: {e}")
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
                <h1>🎯 Gestor de Caché de Respuestas</h1>
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
                    <h2>📋 Respuestas Cacheadas ({len(respuestas_cache)})</h2>
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
                                <button class="delete-btn" onclick="eliminarCategoria('{categoria}')">🗑️ Eliminar</button>
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
                    <h2>🤖 Candidatos de Auto-Caché (Preguntas Frecuentes)</h2>
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
                            <span class="category-name" style="color: #f39c12;">🔥 "{pregunta_orig[:50]}..."</span>
                            <div>
                                <span class="usage-badge" style="background: #f39c12;">{count} veces</span>
                                <button class="btn-add-cache" onclick="agregarAlCache('{pregunta_safe}', '{respuesta_safe}')" style="margin-left: 10px; background: #27ae60; color: white; border: none; padding: 8px 16px; border-radius: 6px; cursor: pointer; font-weight: bold;">
                                    ➕ Agregar al Caché
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
                    <h3 style="margin-top: 30px; color: #666;">📊 Preguntas Emergentes</h3>
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
                    <h2>➕ Agregar Nueva Respuesta</h2>
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

                        <button type="submit" class="btn-primary">💾 Guardar Respuesta</button>
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
                            alert('✅ ' + result.message);
                            location.reload();
                        } else {
                            alert('❌ Error: ' + result.error);
                        }
                    } catch (error) {
                        alert('❌ Error: ' + error.message);
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
                            alert('✅ Agregado al caché! El audio se pre-generará automáticamente.');
                            location.reload();
                        } else {
                            alert('❌ Error: ' + result.error);
                        }
                    } catch (error) {
                        alert('❌ Error: ' + error.message);
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
                            alert('✅ ' + result.message);
                            location.reload();
                        } else {
                            alert('❌ Error: ' + result.error);
                        }
                    } catch (error) {
                        alert('❌ Error: ' + error.message);
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


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("🚀 SERVIDOR DE LLAMADAS NIOVAL")
    print("=" * 60)
    print("\n🚀 SERVIDOR BRUCE W - VERSION FIX 81 (DEBUG ACTIVO)")
    print("=" * 60)
    print("\n📞 Endpoints disponibles:")
    print("  POST /iniciar-llamada            - Inicia una llamada individual")
    print("  POST /llamadas-masivas           - Inicia múltiples llamadas")
    print("  GET  /status/<call_sid>          - Estado de una llamada")
    print("  GET  /stats                      - Ver estadísticas de caché")
    print("  POST /generate-cache             - Generar audios manualmente")
    print("  GET  /diagnostico-persistencia   - Diagnosticar volumen persistente")
    print("\n🌐 URLs de acceso:")
    print("  📊 Estadísticas: https://nioval-webhook-server-production.up.railway.app/stats")
    print("  🔍 Diagnóstico Persistencia: https://nioval-webhook-server-production.up.railway.app/diagnostico-persistencia")
    print("\n✅ FIX 79: Despedida cálida activa (deja puerta abierta)")
    print("✅ FIX 81: Debug de detección de Truper activo")
    print("\n⚠️  Asegúrate de configurar Twilio en .env")
    print("=" * 60 + "\n")

    # PASO 1: Cargar caché persistente desde disco (audios auto-generados)
    print("🔄 Cargando caché desde disco...")
    cargar_cache_desde_disco()

    # PASO 2: Pre-generar caché manual de audios comunes con Multilingual v2
    pre_generar_audios_cache()

    print(f"\n📊 Estadísticas de caché:")
    print(f"   • Audios en caché: {len(audio_cache)}")
    print(f"   • Directorio: {CACHE_DIR}")
    print(f"   • Ruta absoluta: {os.path.abspath(CACHE_DIR)}")
    print(f"   • Auto-caché después de {FRECUENCIA_MIN_CACHE} usos\n")

    # Puerto dinámico para Render (usa PORT de env o 5000 por defecto)
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
