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

# Inicializar Google Sheets Manager (solo una vez al arrancar)
sheets_manager = None
try:
    from nioval_sheets_adapter import NiovalSheetsAdapter
    sheets_manager = NiovalSheetsAdapter()
    print("✅ Google Sheets Manager inicializado")
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


def generar_audio_elevenlabs(texto, audio_id):
    """Genera audio con ElevenLabs y lo guarda temporalmente (OPTIMIZADO para baja latencia)"""
    try:
        # Usar modelo TURBO para respuesta más rápida con idioma español forzado
        audio_generator = elevenlabs_client.text_to_speech.convert(
            voice_id=ELEVENLABS_VOICE_ID,
            text=texto,
            model_id="eleven_turbo_v2",  # Modelo más rápido
            optimize_streaming_latency=4,  # Máxima prioridad a latencia baja
            output_format="mp3_44100_128",  # Formato optimizado
            language_code="es"  # FORZAR español mexicano
        )

        # Guardar en archivo temporal
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.mp3')
        for chunk in audio_generator:
            temp_file.write(chunk)
        temp_file.close()

        # Guardar ruta del archivo
        audio_files[audio_id] = temp_file.name
        return audio_id

    except Exception as e:
        print(f"Error generando audio ElevenLabs: {e}")
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
        # Crear llamada con Twilio
        call = twilio_client.calls.create(
            to=telefono_destino,
            from_=TWILIO_PHONE_NUMBER,
            url=request.url_root + "webhook-voz",
            method="POST"
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
        sheets_manager=sheets_manager
    )
    agente.call_sid = call_sid  # Guardar el Call SID de Twilio
    conversaciones_activas[call_sid] = agente

    # Mensaje inicial
    mensaje_inicial = agente.iniciar_conversacion()

    # Generar audio con ElevenLabs
    audio_id = f"inicial_{call_sid}"
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
    respuesta_agente = agente.procesar_respuesta(speech_result)

    # Generar audio con ElevenLabs
    audio_id = f"respuesta_{call_sid}_{len(audio_files)}"
    generar_audio_elevenlabs(respuesta_agente, audio_id)

    # Crear respuesta TwiML
    response = VoiceResponse()

    # Reproducir audio de ElevenLabs
    audio_url = request.url_root + f"audio/{audio_id}"
    response.play(audio_url)

    # Verificar si debe terminar
    if any(palabra in respuesta_agente.lower() for palabra in ["gracias por su tiempo", "hasta luego", "que tenga buen día"]):
        # Terminar llamada
        response.hangup()

        # Guardar lead y llamada en Google Sheets
        agente.guardar_llamada_y_lead()

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

        # Fallback si no hay respuesta
        response.say("¿Sigue ahí?", language="es-MX")
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
                method="POST"
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

    # Puerto dinámico para Render (usa PORT de env o 5000 por defecto)
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
