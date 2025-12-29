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
from dotenv import load_dotenv
from agente_ventas import AgenteVentas
from elevenlabs import ElevenLabs

load_dotenv()

app = Flask(__name__)

# Inicializar Google Sheets Managers (solo una vez al arrancar)
sheets_manager = None
resultados_manager = None
try:
    from nioval_sheets_adapter import NiovalSheetsAdapter
    from resultados_sheets_adapter import ResultadosSheetsAdapter

    sheets_manager = NiovalSheetsAdapter()  # Para leer contactos
    resultados_manager = ResultadosSheetsAdapter()  # Para guardar resultados
    print("✅ Google Sheets Managers inicializados")
except Exception as e:
    print(f"⚠️  Google Sheets no disponible: {e}")
    print("⚠️  Las llamadas se guardarán solo en backup local")

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
FRECUENCIA_MIN_CACHE = 3  # Auto-generar caché después de N usos
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


def registrar_frase_usada(texto):
    """
    Registra una frase usada y auto-genera caché si alcanza frecuencia mínima
    """
    # Normalizar texto (quitar espacios extras, lowercase para comparación)
    texto_norm = " ".join(texto.split()).strip()

    # Generar key único basado en primeras palabras
    palabras = texto_norm.split()[:8]  # Primeras 8 palabras
    frase_key = "_".join(palabras).lower()

    # Incrementar contador
    if frase_key not in frase_stats:
        frase_stats[frase_key] = {"texto": texto, "count": 0}

    frase_stats[frase_key]["count"] += 1
    count = frase_stats[frase_key]["count"]

    # Auto-generar caché si alcanza frecuencia mínima
    if count == FRECUENCIA_MIN_CACHE and frase_key not in audio_cache:
        print(f"\n🔥 Frase frecuente detectada ({count} usos): {texto[:50]}...")
        print(f"   Generando caché automático con Multilingual v2...")

        try:
            # Generar audio con Multilingual v2 (mejor calidad)
            audio_generator = elevenlabs_client.text_to_speech.convert(
                voice_id=ELEVENLABS_VOICE_ID,
                text=texto,
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
            guardar_cache_en_disco(frase_key, texto, temp_file.name)

            print(f"   ✅ Caché auto-generado: {frase_key}")

        except Exception as e:
            print(f"   ❌ Error generando caché automático: {e}")


def pre_generar_audios_cache():
    """Pre-genera frases comunes con Multilingual v2 para acento perfecto"""
    frases_comunes = {
        # Frases de sistema
        "timeout": "¿Sigue ahí?",
        "error": "Lo siento, hubo un error. Le llamaremos más tarde.",

        # Saludo inicial (se usa en TODAS las llamadas)
        "saludo_inicial": "Hola, muy buenas tardes. Mi nombre es Bruce W, le llamo de NIOVAL, somos distribuidores especializados en productos de ferretería. ¿Me comunico con el encargado de compras o con el dueño del negocio?",

        # Despedidas comunes
        "despedida_1": "Muchas gracias por su tiempo. Que tenga excelente tarde. Hasta pronto.",
        "despedida_2": "Perfecto. En las próximas dos horas le llega el catálogo completo por WhatsApp. Muchas gracias por su tiempo. Que tenga excelente tarde.",
    }

    print("🔧 Pre-generando caché de audios con Multilingual v2...")
    for key, texto in frases_comunes.items():
        try:
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


def generar_audio_elevenlabs(texto, audio_id, usar_cache_key=None):
    """
    Genera audio con ElevenLabs usando estrategia híbrida AUTO-ADAPTATIVA:
    - Caché manual: Usa audio pre-generado (0s delay)
    - Caché auto: Busca en caché auto-generado de frases frecuentes
    - Frases largas: Multilingual v2 (mejor acento, ~5s delay)
    - Frases cortas: Turbo v2 (velocidad, ~2s delay)
    """
    try:
        import time
        inicio = time.time()

        # PASO 1: Si hay cache key manual, usar audio pre-generado
        if usar_cache_key and usar_cache_key in audio_cache:
            audio_files[audio_id] = audio_cache[usar_cache_key]
            print(f"📦 Caché manual: {usar_cache_key} (0s delay)")
            return audio_id

        # PASO 2: Buscar en caché auto-generado
        palabras_inicio = " ".join(texto.split()[:8]).lower()
        frase_key = "_".join(palabras_inicio.split())

        if frase_key in audio_cache:
            audio_files[audio_id] = audio_cache[frase_key]
            print(f"📦 Caché AUTO: {frase_key[:40]}... (0s delay)")
            return audio_id

        # PASO 3: Registrar frase para estadísticas (auto-genera caché si es frecuente)
        registrar_frase_usada(texto)

        # Aplicar correcciones fonéticas
        texto_corregido = corregir_pronunciacion(texto)

        # ESTRATEGIA HÍBRIDA: Elegir modelo según longitud
        palabras = len(texto_corregido.split())

        if palabras > 25:
            # Frases largas: Usar Multilingual v2 (mejor acento)
            modelo = "eleven_multilingual_v2"
            optimize_latency = None
            print(f"🎙️ Usando Multilingual v2 ({palabras} palabras)")
        else:
            # Frases cortas: Usar Turbo v2 (velocidad)
            modelo = "eleven_turbo_v2"
            optimize_latency = 4
            print(f"⚡ Usando Turbo v2 ({palabras} palabras)")

        # Generar audio
        audio_generator = elevenlabs_client.text_to_speech.convert(
            voice_id=ELEVENLABS_VOICE_ID,
            text=texto_corregido,
            model_id=modelo,
            optimize_streaming_latency=optimize_latency,
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

    # Esperar hasta 3 segundos si el audio aún no está listo
    max_wait = 3
    waited = 0
    while audio_id not in audio_files and waited < max_wait:
        time.sleep(0.1)
        waited += 0.1

    if audio_id in audio_files:
        return send_file(audio_files[audio_id], mimetype='audio/mpeg')
    return "Audio not found", 404


@app.route("/iniciar-llamada", methods=["POST"])
def iniciar_llamada():
    """
    Endpoint para iniciar una llamada saliente
    
    Body JSON:
    {
        "telefono": "+52XXXXXXXXXX",
        "nombre_negocio": "Ferretería ejemplo"
    }
    """
    data = request.json
    telefono_destino = data.get("telefono")
    nombre_negocio = data.get("nombre_negocio", "cliente")
    
    if not telefono_destino:
        return {"error": "Teléfono requerido"}, 400
    
    try:
        # Crear llamada con Twilio (con grabación automática habilitada)
        call = twilio_client.calls.create(
            to=telefono_destino,
            from_=TWILIO_PHONE_NUMBER,
            url=request.url_root + "webhook-voz",
            method="POST",
            record=True  # Grabar llamada automáticamente
        )

        # Guardar info del contacto para usar en el webhook
        contactos_llamadas[call.sid] = {
            "telefono": telefono_destino,
            "nombre_negocio": nombre_negocio
        }

        return {
            "success": True,
            "call_sid": call.sid,
            "status": call.status
        }

    except Exception as e:
        return {"error": str(e)}, 500


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

    # Crear nueva conversación con Google Sheets habilitado
    agente = AgenteVentas(
        contacto_info=contacto_info,
        sheets_manager=sheets_manager,
        resultados_manager=resultados_manager
    )
    agente.call_sid = call_sid  # Guardar el Call SID de Twilio
    conversaciones_activas[call_sid] = agente

    # Mensaje inicial
    mensaje_inicial = agente.iniciar_conversacion()

    # Generar audio con ElevenLabs - usar CACHÉ si es el saludo estándar
    audio_id = f"inicial_{call_sid}"

    # Detectar si es el saludo estándar para usar caché (0s delay, Multilingual v2)
    if "Hola, muy buenas tardes. Mi nombre es Bruce W" in mensaje_inicial:
        generar_audio_elevenlabs(mensaje_inicial, audio_id, usar_cache_key="saludo_inicial")
    else:
        generar_audio_elevenlabs(mensaje_inicial, audio_id)

    # Crear respuesta TwiML
    response = VoiceResponse()

    # Reproducir audio de ElevenLabs
    audio_url = request.url_root + f"audio/{audio_id}"
    response.play(audio_url)

    # Recopilar respuesta del cliente
    gather = Gather(
        input="speech",
        language="es-MX",
        timeout=5,  # Tiempo de espera antes de timeout
        speech_timeout=3,  # Tiempo después de que cliente deja de hablar
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
    else:
        call_sid = request.form.get("CallSid")
        speech_result = request.form.get("SpeechResult", "")

    # Obtener agente de esta conversación
    agente = conversaciones_activas.get(call_sid)

    if not agente:
        response = VoiceResponse()
        response.say("Error en la conversación.", language="es-MX")
        response.hangup()
        return Response(str(response), mimetype="text/xml")

    # Procesar respuesta con GPT-4o
    import time
    inicio = time.time()
    respuesta_agente = agente.procesar_respuesta(speech_result)
    tiempo_gpt = time.time() - inicio
    print(f"⏱️ GPT tardó: {tiempo_gpt:.2f}s")

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

    # Crear respuesta TwiML
    response = VoiceResponse()

    # Reproducir audio de ElevenLabs
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
        # Terminar llamada
        response.hangup()

        # Guardar lead y llamada en Google Sheets
        print(f"💾 Guardando llamada {call_sid} en Google Sheets...")
        try:
            agente.guardar_llamada_y_lead()
            print(f"✅ Llamada {call_sid} guardada correctamente")
        except Exception as e:
            print(f"❌ Error guardando llamada {call_sid}: {e}")

        # Limpiar memoria
        del conversaciones_activas[call_sid]
        if call_sid in contactos_llamadas:
            del contactos_llamadas[call_sid]
    else:
        # Continuar conversación
        gather = Gather(
            input="speech",
            language="es-MX",
            timeout=5,  # Tiempo de espera antes de timeout
            speech_timeout=3,  # Tiempo después de que cliente deja de hablar
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

        return {
            "audios_en_cache": len(audio_cache),
            "archivos_en_disco": len(archivos_disco),
            "tamano_mb": round(tamano_total / (1024 * 1024), 2),
            "directorio": CACHE_DIR,
            "voice_id_actual": ELEVENLABS_VOICE_ID,
            "archivos": archivos_disco[:10],  # Primeros 10 archivos
            "frecuencia_min": FRECUENCIA_MIN_CACHE,
            "frases_registradas": len(frase_stats)
        }

    except Exception as e:
        return {"error": str(e)}, 500


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("🚀 SERVIDOR DE LLAMADAS NIOVAL")
    print("=" * 60)
    print("\n📞 Endpoints disponibles:")
    print("  POST /iniciar-llamada      - Inicia una llamada individual")
    print("  POST /llamadas-masivas     - Inicia múltiples llamadas")
    print("  GET  /status/<call_sid>    - Estado de una llamada")
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
