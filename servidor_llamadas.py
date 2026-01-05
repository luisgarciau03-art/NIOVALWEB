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
from dotenv import load_dotenv
from agente_ventas import AgenteVentas
from elevenlabs import ElevenLabs

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

twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
elevenlabs_client = ElevenLabs(api_key=ELEVENLABS_API_KEY)

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
        "timeout": "¿Sigue ahí?",
        "error": "Lo siento, hubo un error. Le llamaremos más tarde.",
        "pensando": "Mmm, déjeme pensarlo un momento...",  # Audio de relleno mientras GPT procesa

        # Saludo inicial (se usa en TODAS las llamadas) - CON PRONUNCIACIÓN CORRECTA
        "saludo_inicial": "Hola, muy buenas tardes. Mi nombre es Bruce W, le llamo de NIOVAL, somos distribuidores especializados en productos ferre-teros. ¿Me comunico con el encargado de compras o con el dueño del negocio?",

        # Despedidas comunes
        "despedida_1": "Muchas gracias por su tiempo. Que tenga excelente tarde. Hasta pronto.",
        "despedida_2": "Perfecto. En las próximas dos horas le llega el catálogo completo por WhatsApp. Muchas gracias por su tiempo. Que tenga excelente tarde.",
    }

    print("🔧 Pre-generando caché de audios con Multilingual v2...")
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

        # Generar audio
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
        return audio_id

    except Exception as e:
        print(f"❌ Error generando audio: {e}")
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

        # Crear llamada con Twilio (con grabación y detección de buzón automática)
        call = twilio_client.calls.create(
            to=telefono_destino,
            from_=TWILIO_PHONE_NUMBER,
            url=request.url_root + "webhook-voz",
            method="POST",
            record=True,  # Grabar llamada automáticamente
            machine_detection="DetectMessageEnd",  # Detectar buzón de voz automáticamente
            machine_detection_timeout=5,  # Timeout de 5 segundos para detectar
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

    # Generar audio con ElevenLabs - usar CACHÉ si es el saludo estándar
    audio_id = f"inicial_{call_sid}"

    # Detectar si es el saludo estándar para usar caché (0s delay, Multilingual v2)
    usa_cache_saludo = "Hola, muy buenas tardes. Mi nombre es Bruce W" in mensaje_inicial
    if usa_cache_saludo:
        generar_audio_elevenlabs(mensaje_inicial, audio_id, usar_cache_key="saludo_inicial")
    else:
        generar_audio_elevenlabs(mensaje_inicial, audio_id)

    # Registrar mensaje inicial de Bruce en LOGS
    if logs_manager and bruce_id:
        nombre_tienda = contacto_info.get('nombre_negocio', '') if contacto_info else ''
        logs_manager.registrar_mensaje_bruce(
            bruce_id,
            mensaje_inicial,
            desde_cache=usa_cache_saludo,
            cache_key="saludo_inicial" if usa_cache_saludo else None,
            nombre_tienda=nombre_tienda
        )

    # Crear respuesta TwiML
    response = VoiceResponse()

    # PAUSA DE 1 SEGUNDO - Dar tiempo al cliente de decir "Hola" primero
    response.pause(length=1)

    # Reproducir audio de ElevenLabs
    audio_url = request.url_root + f"audio/{audio_id}"
    response.play(audio_url)

    # Recopilar respuesta del cliente
    gather = Gather(
        input="speech",
        language="es-MX",
        timeout=5,  # Tiempo de espera antes de timeout
        speech_timeout=1,  # OPTIMIZADO: 1s después de que cliente deja de hablar (antes 3s)
        action="/procesar-respuesta",
        method="POST"
    )
    response.append(gather)

    # Si no hay respuesta (fallback a TTS de Twilio)
    response.say("No escuché su respuesta. Le llamaremos más tarde.", language="es-MX")
    response.hangup()

    return Response(str(response), mimetype="text/xml")


@app.route("/procesar-respuesta", methods=["GET", "POST"])
def procesar_respuesta():
    """
    Procesa la respuesta del cliente y continúa la conversación
    """
    # Twilio puede enviar GET o POST
    if request.method == "GET":
        call_sid = request.args.get("CallSid")
        speech_result = request.args.get("SpeechResult", "")
        call_status = request.args.get("CallStatus", "")
        answered_by = request.args.get("AnsweredBy", "")

        # DEBUG: Log todos los parámetros de Twilio
        print(f"\n🔍 DEBUG - Parámetros Twilio (GET):")
        print(f"   CallSid: {call_sid}")
        print(f"   CallStatus: {call_status}")
        print(f"   AnsweredBy: {answered_by}")
        print(f"   SpeechResult: '{speech_result}'")
        if request.args.get("Digits"):
            print(f"   Digits: {request.args.get('Digits')}")
    else:
        call_sid = request.form.get("CallSid")
        speech_result = request.form.get("SpeechResult", "")
        call_status = request.form.get("CallStatus", "")
        answered_by = request.form.get("AnsweredBy", "")

        # DEBUG: Log todos los parámetros de Twilio
        print(f"\n🔍 DEBUG - Parámetros Twilio (POST):")
        print(f"   CallSid: {call_sid}")
        print(f"   CallStatus: {call_status}")
        print(f"   AnsweredBy: {answered_by}")
        print(f"   SpeechResult: '{speech_result}'")
        if request.form.get("Digits"):
            print(f"   Digits: {request.form.get('Digits')}")

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

    # Detectar respuestas vacías consecutivas (cliente ya no está en línea)
    if not speech_result or speech_result.strip() == "":
        agente.respuestas_vacias_consecutivas += 1
        print(f"⚠️ Respuesta vacía #{agente.respuestas_vacias_consecutivas}")

        # Si hay 3 respuestas vacías consecutivas, cliente probablemente colgó
        if agente.respuestas_vacias_consecutivas >= 3:
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

    # Procesar respuesta con GPT-4o
    import time
    import threading
    inicio = time.time()

    # Variable para almacenar la respuesta cuando termine GPT
    respuesta_container = {"respuesta": None, "completado": False}

    def procesar_gpt():
        respuesta_container["respuesta"] = agente.procesar_respuesta(speech_result)
        respuesta_container["completado"] = True

    # Iniciar procesamiento de GPT en thread separado
    gpt_thread = threading.Thread(target=procesar_gpt)
    gpt_thread.start()

    # Crear respuesta TwiML inicial
    response = VoiceResponse()

    # OPTIMIZACIÓN: Timeout más corto para respuestas más rápidas
    # Esperar máximo 5 segundos por GPT (suficiente para respuestas normales)
    gpt_thread.join(timeout=5.0)

    if not respuesta_container["completado"]:
        # GPT tardó más de 5 segundos - timeout
        print(f"❌ GPT timeout después de 5s")
        response.say("Lo siento, estoy teniendo problemas técnicos. Le llamaré más tarde.", language="es-MX")
        response.hangup()
        return Response(str(response), mimetype="text/xml")

    respuesta_agente = respuesta_container["respuesta"]
    tiempo_gpt = time.time() - inicio
    print(f"⏱️ GPT tardó: {tiempo_gpt:.2f}s")
    print(f"🤖 BRUCE DICE: \"{respuesta_agente}\"")

    # Generar audio con ElevenLabs - detectar si puede usar caché
    audio_id = f"respuesta_{call_sid}_{len(audio_files)}"
    inicio_audio = time.time()

    # Detectar despedidas comunes para usar caché (0s delay, Multilingual v2)
    cache_key = None
    if "Muchas gracias por su tiempo. Que tenga excelente tarde. Hasta pronto" in respuesta_agente:
        cache_key = "despedida_1"
    elif "En las próximas dos horas le llega el catálogo" in respuesta_agente and "Muchas gracias por su tiempo" in respuesta_agente:
        cache_key = "despedida_2"

    generar_audio_elevenlabs(respuesta_agente, audio_id, usar_cache_key=cache_key)
    tiempo_audio = time.time() - inicio_audio
    print(f"⏱️ Audio tardó: {tiempo_audio:.2f}s")
    print(f"⏱️ TOTAL delay: {(time.time() - inicio):.2f}s")

    # Registrar mensaje de Bruce en LOGS (con info de cache)
    if logs_manager and agente.bruce_id:
        # Determinar si vino del caché
        desde_cache = (tiempo_audio < 0.1)  # Si tardó menos de 0.1s, vino del caché
        nombre_tienda = agente.lead_data.get('nombre_negocio', '')
        logs_manager.registrar_mensaje_bruce(
            agente.bruce_id,
            respuesta_agente,
            desde_cache=desde_cache,
            cache_key=cache_key,
            tiempo_generacion=tiempo_audio if not desde_cache else None,
            nombre_tienda=nombre_tienda
        )

    # Reproducir audio de ElevenLabs (response ya fue creado arriba)
    audio_url = request.url_root + f"audio/{audio_id}"
    response.play(audio_url)

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

        # IMPORTANTE: Esperar respuesta del cliente por educación antes de colgar
        print(f"⏳ Esperando despedida del cliente por cortesía...")

        # Crear Gather para escuchar despedida del cliente
        gather_despedida = Gather(
            input="speech",
            language="es-MX",
            timeout=3,  # Esperar hasta 3 segundos
            speech_timeout=2,  # 2 segundos después de que termine de hablar
            action="/despedida-final",
            method="POST"
        )
        response.append(gather_despedida)

        # Si no responde en 3 segundos, terminar igual
        response.hangup()

        return str(response)

    # Si NO es despedida, continuar conversación normal
    gather = Gather(
        input="speech",
        language="es-MX",
        timeout=5,  # Tiempo de espera antes de timeout
        speech_timeout=1,  # OPTIMIZADO: 1s después de que cliente deja de hablar (antes 3s)
        action="/procesar-respuesta",
        method="POST"
    )
    response.append(gather)

    # Fallback si no hay respuesta - usar CACHÉ (0s delay, acento perfecto)
    audio_id_timeout = f"timeout_{call_sid}_{len(audio_files)}"
    generar_audio_elevenlabs("¿Sigue ahí?", audio_id_timeout, usar_cache_key="timeout")
    audio_url_timeout = request.url_root + f"audio/{audio_id_timeout}"
    response.play(audio_url_timeout)
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

                # 1. Manejo de BUZÓN - Marcar intentos y reintentar
                if agente.lead_data.get("estado_llamada") == "Buzon" and fila:
                    print(f"\n📞 Llamada cayó en buzón - manejando reintento...")
                    intentos = sheets_manager.marcar_intento_buzon(fila)

                    if intentos == 1:
                        # PRIMER intento de buzón - REINTENTO INMEDIATO
                        print(f"📞 Primer intento de buzón - iniciando reintento inmediato...")
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

            if not texto or not key:
                continue

            # Verificar si ya existe en caché
            if key in audio_cache:
                print(f"⏭️ Omitido: {key} (ya está en caché)")
                continue

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


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("🚀 SERVIDOR DE LLAMADAS NIOVAL")
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
