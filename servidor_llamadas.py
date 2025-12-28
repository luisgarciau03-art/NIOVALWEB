"""
Servidor Flask para manejar llamadas telefónicas con Twilio
Integración: Twilio → GPT-4o → ElevenLabs → Cliente
"""

from flask import Flask, request, Response
from twilio.twiml.voice_response import VoiceResponse, Gather
from twilio.rest import Client
import os
from dotenv import load_dotenv
from agente_ventas import AgenteVentas

load_dotenv()

app = Flask(__name__)

# Configuración Twilio
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_PHONE_NUMBER = os.getenv("TWILIO_PHONE_NUMBER")

twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

# Almacenar conversaciones activas (en producción usar Redis/DB)
conversaciones_activas = {}


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
    
    # Crear nueva conversación
    agente = AgenteVentas()
    conversaciones_activas[call_sid] = agente
    
    # Mensaje inicial
    mensaje_inicial = agente.iniciar_conversacion()
    
    # Crear respuesta TwiML
    response = VoiceResponse()
    
    # Decir el mensaje inicial
    response.say(
        mensaje_inicial,
        voice="Polly.Miguel",  # Voz en español
        language="es-MX"
    )
    
    # Recopilar respuesta del cliente
    gather = Gather(
        input="speech",
        language="es-MX",
        timeout=5,
        speech_timeout="auto",
        action="/procesar-respuesta",
        method="POST"
    )
    response.append(gather)
    
    # Si no hay respuesta
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
    
    # Crear respuesta TwiML
    response = VoiceResponse()
    
    # Verificar si debe terminar
    if any(palabra in respuesta_agente.lower() for palabra in ["gracias por su tiempo", "hasta luego", "que tenga buen día"]):
        # Terminar llamada
        response.say(respuesta_agente, voice="Polly.Miguel", language="es-MX")
        response.hangup()
        
        # Guardar lead
        agente.guardar_lead()
        del conversaciones_activas[call_sid]
    else:
        # Continuar conversación
        response.say(respuesta_agente, voice="Polly.Miguel", language="es-MX")
        
        gather = Gather(
            input="speech",
            language="es-MX",
            timeout=5,
            speech_timeout="auto",
            action="/procesar-respuesta",
            method="POST"
        )
        response.append(gather)
        
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
