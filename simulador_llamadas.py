#!/usr/bin/env python3
"""
Simulador de Llamadas Bruce W
==============================
Testea flujos de conversacion sin Twilio/ElevenLabs/Azure.

Modos:
  - Sin OPENAI_API_KEY: Solo FSM + templates (rapido, gratis)
  - Con OPENAI_API_KEY: FSM + GPT real (~$0.01 por escenario)

Uso:
  python simulador_llamadas.py                  # Todos los escenarios
  python simulador_llamadas.py --verbose        # Detalle completo
  python simulador_llamadas.py --escenario 3    # Solo escenario #3
  python simulador_llamadas.py --list           # Listar escenarios
"""

import os
import sys
import io
import time
import argparse
from datetime import datetime

# Fix Windows console encoding (FSM logs use → character)
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Setup path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Env vars dummy si no existen (evitar crash al importar)
for _k in ['ELEVENLABS_API_KEY', 'TWILIO_ACCOUNT_SID', 'TWILIO_AUTH_TOKEN',
           'TWILIO_PHONE_NUMBER']:
    os.environ.setdefault(_k, 'SIM_DUMMY')

from agente_ventas import AgenteVentas, EstadoConversacion
from bug_detector import BugDetector, CallEventTracker, _evaluar_con_gpt

# ============================================================
# ESCENARIOS DE PRUEBA
# ============================================================

ESCENARIOS = [
    # ----------------------------------------------------------
    # 1. Flujo exitoso completo
    # ----------------------------------------------------------
    {
        "nombre": "Flujo exitoso completo",
        "descripcion": "Saludo -> encargado si -> WhatsApp -> captura -> despedida",
        "contacto": {"nombre_negocio": "Ferreteria Test", "ciudad": "Guadalajara"},
        "turnos": [
            {
                "cliente": "Bueno, buen dia",
                "check_bruce": ["nioval"],
            },
            {
                "cliente": "Si, yo soy el encargado de compras",
                "check_bruce": None,
            },
            {
                "cliente": "Si, me interesa el catalogo por WhatsApp",
                "check_bruce": None,
            },
            {
                "cliente": "Mi WhatsApp es 33 12 34 56 78",
                "check_bruce": None,
            },
        ],
        "bugs_esperados": [],
        "bugs_no_esperados": ["PREGUNTA_IGNORADA"],
    },

    # ----------------------------------------------------------
    # 2. Encargado no esta
    # ----------------------------------------------------------
    {
        "nombre": "Encargado no esta",
        "descripcion": "Saludo -> no esta -> pedir WhatsApp/correo -> captura",
        "contacto": {"nombre_negocio": "Ferreteria Prueba", "ciudad": "Monterrey"},
        "turnos": [
            {
                "cliente": "Bueno",
                "check_bruce": None,
            },
            {
                "cliente": "No, no esta el encargado",
                "check_bruce": None,
            },
            {
                "cliente": "Si, le doy un WhatsApp",
                "check_bruce": None,
            },
            {
                "cliente": "Es 81 23 45 67 89",
                "check_bruce": None,
            },
        ],
        "bugs_esperados": [],
    },

    # ----------------------------------------------------------
    # 3. Pregunta ignorada (FIX 793B)
    # ----------------------------------------------------------
    {
        "nombre": "Pregunta ignorada (FIX 793B)",
        "descripcion": "Cliente pregunta 'quien habla' y Bruce da solo ack",
        "contacto": {"nombre_negocio": "Ferreteria XYZ"},
        "simular_bug": True,
        "turnos_raw": [
            ("bruce", "Me comunico de la marca NIOVAL, manejamos productos ferreteros."),
            ("cliente", "Aja si"),
            ("bruce", "Claro, digame el numero."),
            ("cliente", "Quien habla?"),
            ("bruce", "Si, adelante."),
            ("cliente", "Quien habla?"),
            ("bruce", "Claro, continue."),
        ],
        "bugs_esperados": ["PREGUNTA_IGNORADA"],
    },

    # ----------------------------------------------------------
    # 4. Rechazo inmediato
    # ----------------------------------------------------------
    {
        "nombre": "Rechazo inmediato",
        "descripcion": "Cliente dice 'no me interesa' rapido -> despedida limpia",
        "contacto": {"nombre_negocio": "Tienda ABC"},
        "turnos": [
            {
                "cliente": "Bueno",
                "check_bruce": None,
            },
            {
                "cliente": "No, no me interesa, gracias",
                "check_bruce": None,
            },
        ],
        "bugs_esperados": [],
    },

    # ----------------------------------------------------------
    # 5. Dictado WhatsApp con numero
    # ----------------------------------------------------------
    {
        "nombre": "Dictado WhatsApp",
        "descripcion": "Encargado presente -> ofrece WhatsApp -> dicta numero",
        "contacto": {"nombre_negocio": "Ferreteria Delta"},
        "turnos": [
            {
                "cliente": "Si, buen dia, digame",
                "check_bruce": None,
            },
            {
                "cliente": "Si, yo me encargo de las compras",
                "check_bruce": None,
            },
            {
                "cliente": "Si, le doy mi WhatsApp",
                "check_bruce": None,
            },
            {
                "cliente": "Es el 55 98 76 54 32",
                "check_bruce": None,
            },
        ],
        "bugs_esperados": [],
    },

    # ----------------------------------------------------------
    # 6. Dictado correo electronico
    # ----------------------------------------------------------
    {
        "nombre": "Dictado correo electronico",
        "descripcion": "Encargado da correo en vez de WhatsApp",
        "contacto": {"nombre_negocio": "Herrajes del Norte"},
        "turnos": [
            {
                "cliente": "Bueno, si digame",
                "check_bruce": None,
            },
            {
                "cliente": "Si, yo soy el encargado",
                "check_bruce": None,
            },
            {
                "cliente": "Mejor le doy mi correo",
                "check_bruce": None,
            },
            {
                "cliente": "Es juan arroba gmail punto com",
                "check_bruce": None,
            },
        ],
        "bugs_esperados": [],
    },

    # ----------------------------------------------------------
    # 7. Encargado llega luego (callback)
    # ----------------------------------------------------------
    {
        "nombre": "Callback - encargado llega luego",
        "descripcion": "Encargado no esta -> viene manana -> programar callback",
        "contacto": {"nombre_negocio": "Ferreteria Omega"},
        "turnos": [
            {
                "cliente": "Bueno",
                "check_bruce": None,
            },
            {
                "cliente": "No, ahorita no esta, viene manana",
                "check_bruce": None,
            },
            {
                "cliente": "Por la manana, como a las 9",
                "check_bruce": None,
            },
        ],
        "bugs_esperados": [],
    },

    # ----------------------------------------------------------
    # 8. Pitch repetido (bug detector)
    # ----------------------------------------------------------
    {
        "nombre": "Pitch repetido (deteccion bug)",
        "descripcion": "Bruce repite pitch de NIOVAL 2x -> bug PITCH_REPETIDO",
        "contacto": {"nombre_negocio": "Ferreteria Bug"},
        "simular_bug": True,
        "turnos_raw": [
            ("bruce", "Hola, buen dia. Me comunico de la marca NIOVAL, manejamos productos ferreteros de alta calidad."),
            ("cliente", "Aja, si"),
            ("bruce", "Me comunico de la marca NIOVAL, trabajamos productos ferreteros. Se encontrara el encargado de compras?"),
            ("cliente", "No, no esta"),
            ("bruce", "Entiendo. Me podria dar un WhatsApp?"),
        ],
        "bugs_esperados": ["PITCH_REPETIDO"],
    },

    # ----------------------------------------------------------
    # 9. PREGUNTA_REPETIDA (LIVE) - Bruce NO repite pregunta encargado
    # ----------------------------------------------------------
    {
        "nombre": "No repite pregunta encargado",
        "descripcion": "Bruce pregunta por encargado 1 vez, cliente dice si -> no repite",
        "contacto": {"nombre_negocio": "Ferreteria Uno"},
        "turnos": [
            {
                "cliente": "Bueno, digame",
                "check_bruce": None,
            },
            {
                "cliente": "Si, yo soy el encargado de compras",
                "check_bruce": None,
            },
            {
                "cliente": "Si, mandeme el catalogo",
                "check_bruce": None,
            },
        ],
        "bugs_esperados": [],
        "bugs_no_esperados": ["PREGUNTA_REPETIDA"],
    },

    # ----------------------------------------------------------
    # 10. PREGUNTA_REPETIDA (RAW) - Deteccion bug repeticion
    # ----------------------------------------------------------
    {
        "nombre": "Deteccion pregunta repetida (BugDetector)",
        "descripcion": "Bruce pregunta 'encargado' 3x -> bug PREGUNTA_REPETIDA",
        "contacto": {"nombre_negocio": "Ferreteria RepBug"},
        "simular_bug": True,
        "turnos_raw": [
            ("bruce", "Hola, buen dia. Me comunico de NIOVAL."),
            ("cliente", "Bueno"),
            ("bruce", "Se encontrara el encargado de compras?"),
            ("cliente", "Ahorita no se"),
            ("bruce", "Se encontrara el encargado o encargada de compras?"),
            ("cliente", "Ya le dije que no se"),
            ("bruce", "Me podria comunicar con el encargado de compras?"),
        ],
        "bugs_esperados": ["PREGUNTA_REPETIDA"],
    },

    # ----------------------------------------------------------
    # 11. CLIENTE_HABLA_ULTIMO (RAW) - Cliente habla y Bruce no responde
    # ----------------------------------------------------------
    {
        "nombre": "Deteccion cliente habla ultimo (BugDetector)",
        "descripcion": "Cliente dice algo al final pero Bruce nunca responde",
        "contacto": {"nombre_negocio": "Tienda Silencio"},
        "simular_bug": True,
        "turnos_raw": [
            ("bruce", "Hola, buen dia. Le llamo de NIOVAL."),
            ("cliente", "Si, digame"),
            ("bruce", "Manejamos productos ferreteros. Se encuentra el encargado?"),
            ("cliente", "Mire, le voy a dar un correo y me puede enviar la informacion ahi"),
        ],
        "bugs_esperados": ["CLIENTE_HABLA_ULTIMO"],
    },

    # ----------------------------------------------------------
    # 12. CLIENTE_HABLA_ULTIMO (LIVE) - Bruce SI responde al final
    # ----------------------------------------------------------
    {
        "nombre": "Bruce responde cuando cliente ofrece dato",
        "descripcion": "Cliente ofrece correo al final -> Bruce debe responder",
        "contacto": {"nombre_negocio": "Ferreteria Respuesta"},
        "turnos": [
            {
                "cliente": "Bueno, buen dia",
                "check_bruce": None,
            },
            {
                "cliente": "Si, yo soy el encargado",
                "check_bruce": None,
            },
            {
                "cliente": "Le doy mi correo para que me mande info",
                "check_bruce": None,
            },
        ],
        "bugs_esperados": [],
        "bugs_no_esperados": ["CLIENTE_HABLA_ULTIMO"],
    },

    # ----------------------------------------------------------
    # 13. GPT_LOGICA_ROTA (RAW) - Bruce pide dato ya proporcionado
    # ----------------------------------------------------------
    {
        "nombre": "Deteccion logica rota (BugDetector)",
        "descripcion": "Bruce pide horario que cliente ya dio -> GPT_LOGICA_ROTA",
        "contacto": {"nombre_negocio": "Ferreteria Logica"},
        "simular_bug": True,
        "turnos_raw": [
            ("bruce", "Hola, buen dia. Le llamo de NIOVAL."),
            ("cliente", "Si, digame"),
            ("bruce", "Manejamos productos ferreteros. Se encuentra el encargado?"),
            ("cliente", "No, no esta. Viene a las 3 de la tarde"),
            ("bruce", "Entiendo. A que hora me recomienda llamar para encontrar al encargado?"),
            ("cliente", "Ya le dije, a las 3"),
            ("bruce", "A que hora me recomienda llamar para encontrar al encargado?"),
        ],
        "bugs_esperados": ["PREGUNTA_REPETIDA"],
    },

    # ----------------------------------------------------------
    # 14. SALUDO_FALTANTE (RAW) - Bruce no saluda en primer turno
    # ----------------------------------------------------------
    {
        "nombre": "Deteccion saludo faltante (BugDetector)",
        "descripcion": "Bruce inicia sin 'hola/buen dia' -> SALUDO_FALTANTE",
        "contacto": {"nombre_negocio": "Tienda SinSaludo"},
        "simular_bug": True,
        "turnos_raw": [
            ("bruce", "Mi nombre es Bruce, le llamo de NIOVAL. Somos distribuidores de productos ferreteros."),
            ("cliente", "Si, digame"),
            ("bruce", "Se encontrara el encargado de compras?"),
        ],
        "bugs_esperados": ["SALUDO_FALTANTE"],
    },

    # ----------------------------------------------------------
    # 15. SALUDO_FALTANTE (LIVE) - Bruce SI saluda
    # ----------------------------------------------------------
    {
        "nombre": "Bruce saluda correctamente",
        "descripcion": "Primer turno de Bruce incluye saludo",
        "contacto": {"nombre_negocio": "Ferreteria Saludo"},
        "turnos": [
            {
                "cliente": "Bueno",
                "check_bruce": None,
            },
        ],
        "bugs_esperados": [],
        "bugs_no_esperados": ["SALUDO_FALTANTE"],
    },

    # ----------------------------------------------------------
    # 16. CATALOGO_REPETIDO (RAW) - Bruce ofrece catalogo 2x
    # ----------------------------------------------------------
    {
        "nombre": "Deteccion catalogo repetido (BugDetector)",
        "descripcion": "Bruce ofrece catalogo 2 veces -> CATALOGO_REPETIDO",
        "contacto": {"nombre_negocio": "Ferreteria CatRep"},
        "simular_bug": True,
        "turnos_raw": [
            ("bruce", "Hola, buen dia. Le llamo de NIOVAL."),
            ("cliente", "Si, digame"),
            ("bruce", "Manejamos productos ferreteros. Le podemos enviar un catalogo por WhatsApp."),
            ("cliente", "Ah ok"),
            ("bruce", "Le puedo enviar nuestro catalogo de productos por WhatsApp si gusta."),
            ("cliente", "Si"),
            ("bruce", "Digame su numero"),
        ],
        "bugs_esperados": ["CATALOGO_REPETIDO"],
    },

    # ----------------------------------------------------------
    # 17. INTERRUPCION_CONVERSACIONAL (RAW) - Bruce corta al cliente
    # ----------------------------------------------------------
    {
        "nombre": "Deteccion interrupcion conversacional (BugDetector)",
        "descripcion": "Bruce interrumpe mientras cliente explica situacion",
        "contacto": {"nombre_negocio": "Ferreteria Corta"},
        "simular_bug": True,
        "turnos_raw": [
            ("bruce", "Hola, buen dia. Le llamo de NIOVAL."),
            ("cliente", "Mire, es que nosotros no vendemos eso"),
            ("bruce", "Me comunico de Nioval, trabajamos productos ferreteros de calidad"),
        ],
        "bugs_esperados": ["INTERRUPCION_CONVERSACIONAL"],
    },

    # ----------------------------------------------------------
    # 18. BRUCE_MUDO (RAW) - TwiML enviado pero audio nunca fetcheado
    # ----------------------------------------------------------
    {
        "nombre": "Deteccion Bruce mudo (BugDetector)",
        "descripcion": "TwiML enviado pero audio no fetcheado -> BRUCE_MUDO",
        "contacto": {"nombre_negocio": "Ferreteria Muda"},
        "simular_bug": True,
        "tracker_attrs": {"twiml_count": 3, "audio_fetch_count": 0},
        "turnos_raw": [
            ("bruce", "Hola, buen dia. Le llamo de NIOVAL."),
            ("cliente", "Bueno"),
            ("bruce", ""),
            ("cliente", "Bueno? Me escucha?"),
        ],
        "bugs_esperados": ["BRUCE_MUDO"],
    },

    # ----------------------------------------------------------
    # 19. RESPUESTA_FILLER_INCOHERENTE (RAW) - TTS fallo, filler de respaldo
    # ----------------------------------------------------------
    {
        "nombre": "Deteccion filler incoherente (BugDetector)",
        "descripcion": "ElevenLabs TTS fallo -> filler dejeme_ver usado",
        "contacto": {"nombre_negocio": "Ferreteria Filler"},
        "simular_bug": True,
        "tracker_attrs": {"filler_162a_count": 2},
        "turnos_raw": [
            ("bruce", "Hola, buen dia. Le llamo de NIOVAL."),
            ("cliente", "Que tipo de productos manejan?"),
            ("bruce", "Dejeme ver"),
            ("cliente", "Bueno?"),
            ("bruce", "Mmm"),
        ],
        "bugs_esperados": ["RESPUESTA_FILLER_INCOHERENTE"],
    },

    # ----------------------------------------------------------
    # 20. DICTADO_INTERRUMPIDO (RAW) - Bruce se despide durante dictado
    # ----------------------------------------------------------
    {
        "nombre": "Deteccion dictado interrumpido (BugDetector)",
        "descripcion": "Cliente dicta numero y Bruce se despide sin confirmar",
        "contacto": {"nombre_negocio": "Ferreteria Dictado"},
        "simular_bug": True,
        "turnos_raw": [
            ("bruce", "Me podria dar su numero de WhatsApp?"),
            ("cliente", "Si claro, mi whatsapp es 33 12 34"),
            ("bruce", "Muchas gracias por su tiempo, que tenga buen dia"),
        ],
        "bugs_esperados": ["DICTADO_INTERRUMPIDO"],
    },

    # ----------------------------------------------------------
    # 21. LOOP (RAW) - Bruce repite misma respuesta
    # ----------------------------------------------------------
    {
        "nombre": "Deteccion loop (BugDetector)",
        "descripcion": "Bruce da misma respuesta 3 veces -> LOOP",
        "contacto": {"nombre_negocio": "Ferreteria Loop"},
        "simular_bug": True,
        "turnos_raw": [
            ("bruce", "Hola, buen dia. Le llamo de NIOVAL."),
            ("cliente", "Bueno"),
            ("bruce", "Se encontrara el encargado de compras?"),
            ("cliente", "No"),
            ("bruce", "Se encontrara el encargado de compras?"),
            ("cliente", "Que no"),
            ("bruce", "Se encontrara el encargado de compras?"),
        ],
        "bugs_esperados": ["LOOP"],
    },

    # ----------------------------------------------------------
    # 22. LOOP (LIVE) - Bruce NO entra en loop
    # ----------------------------------------------------------
    {
        "nombre": "Bruce no entra en loop con rechazo",
        "descripcion": "Cliente rechaza varias veces -> Bruce no repite",
        "contacto": {"nombre_negocio": "Ferreteria NoLoop"},
        "turnos": [
            {
                "cliente": "Bueno",
                "check_bruce": None,
            },
            {
                "cliente": "No me interesa",
                "check_bruce": None,
            },
        ],
        "bugs_esperados": [],
        "bugs_no_esperados": ["LOOP"],
    },

    # ----------------------------------------------------------
    # 23. DATO_IGNORADO (RAW) - Bruce pide dato que cliente ya dio
    # ----------------------------------------------------------
    {
        "nombre": "Deteccion dato ignorado (BugDetector)",
        "descripcion": "Cliente da numero pero Bruce pide de nuevo",
        "contacto": {"nombre_negocio": "Ferreteria Dato"},
        "simular_bug": True,
        "turnos_raw": [
            ("bruce", "Me podria dar su numero de WhatsApp?"),
            ("cliente", "Si, es 3312345678"),
            ("bruce", "Cual es su numero de WhatsApp?"),
        ],
        "bugs_esperados": ["DATO_IGNORADO"],
    },

    # ----------------------------------------------------------
    # 24. DESPEDIDA_PREMATURA (RAW) - Bruce se despide sin capturar contacto
    # ----------------------------------------------------------
    {
        "nombre": "Deteccion despedida prematura (BugDetector)",
        "descripcion": "Cliente interesado, Bruce se despide sin capturar contacto",
        "contacto": {"nombre_negocio": "Ferreteria Prematura"},
        "simular_bug": True,
        "turnos_raw": [
            ("bruce", "Hola, buen dia. Me comunico de la marca Nioval."),
            ("cliente", "Si, me interesa el catalogo"),
            ("bruce", "Gracias por su tiempo, que tenga buen dia"),
        ],
        "bugs_esperados": ["DESPEDIDA_PREMATURA"],
    },

    # ----------------------------------------------------------
    # 25. AREA_EQUIVOCADA (RAW) - Cliente dice no es ferreteria
    # ----------------------------------------------------------
    {
        "nombre": "Deteccion area equivocada (BugDetector)",
        "descripcion": "Cliente dice no es ferreteria, Bruce sigue vendiendo",
        "contacto": {"nombre_negocio": "Ferreteria Equivocada"},
        "simular_bug": True,
        "turnos_raw": [
            ("bruce", "Hola, buen dia. Me comunico de la marca Nioval."),
            ("cliente", "Aqui no vendemos ferreteria, se equivoco"),
            ("bruce", "Le puedo enviar nuestro catalogo por WhatsApp?"),
        ],
        "bugs_esperados": ["AREA_EQUIVOCADA"],
    },

    # ----------------------------------------------------------
    # 26. TRANSFER_IGNORADA (RAW) - Cliente pide esperar, Bruce sigue
    # ----------------------------------------------------------
    {
        "nombre": "Deteccion transfer ignorada (BugDetector)",
        "descripcion": "Cliente pide esperar para transferir y Bruce sigue vendiendo",
        "contacto": {"nombre_negocio": "Ferreteria Transfer"},
        "simular_bug": True,
        "turnos_raw": [
            ("bruce", "Hola, buen dia. Me comunico de la marca Nioval."),
            ("cliente", "Espereme un momento, le paso al encargado"),
            ("bruce", "Le puedo enviar nuestro catalogo por WhatsApp?"),
        ],
        "bugs_esperados": ["TRANSFER_IGNORADA"],
    },

    # ----------------------------------------------------------
    # 27. PITCH_REPETIDO (RAW) - Bruce repite pitch 2+ veces
    # ----------------------------------------------------------
    {
        "nombre": "Deteccion pitch repetido (BugDetector)",
        "descripcion": "Bruce repite el pitch de Nioval 2+ veces",
        "contacto": {"nombre_negocio": "Ferreteria Pitch"},
        "simular_bug": True,
        "turnos_raw": [
            ("bruce", "Hola, me comunico de la marca Nioval."),
            ("cliente", "Bueno, digame"),
            ("bruce", "Somos una marca Nioval de productos ferreteros"),
            ("cliente", "Ajam"),
            ("bruce", "Me comunico de la marca Nioval para ofrecerle"),
        ],
        "bugs_esperados": ["PITCH_REPETIDO"],
    },

    # ----------------------------------------------------------
    # 28. DATO_IGNORADO (LIVE) - Bruce NO re-pide dato ya dado
    # ----------------------------------------------------------
    {
        "nombre": "Bruce no ignora datos del cliente",
        "descripcion": "Cliente da WhatsApp -> Bruce confirma, no re-pide",
        "contacto": {"nombre_negocio": "Ferreteria Dato OK", "ciudad": "Guadalajara"},
        "turnos": [
            {
                "cliente": "Bueno, buen dia",
                "check_bruce": None,
            },
            {
                "cliente": "Si, yo soy el encargado de compras",
                "check_bruce": None,
            },
            {
                "cliente": "Mi WhatsApp es 33 14 25 36 47",
                "check_bruce": None,
            },
        ],
        "bugs_esperados": [],
        "bugs_no_esperados": ["DATO_IGNORADO"],
    },

    # ----------------------------------------------------------
    # 29. AREA_EQUIVOCADA (LIVE) - Bruce se despide si no es ferreteria
    # ----------------------------------------------------------
    {
        "nombre": "Bruce maneja area equivocada correctamente",
        "descripcion": "Cliente dice no es ferreteria -> Bruce se despide",
        "contacto": {"nombre_negocio": "Tortilleria Test", "ciudad": "Monterrey"},
        "turnos": [
            {
                "cliente": "Bueno",
                "check_bruce": None,
            },
            {
                "cliente": "No, esto no es ferreteria, somos tortilleria",
                "check_bruce": None,
            },
        ],
        "bugs_esperados": [],
        "bugs_no_esperados": ["AREA_EQUIVOCADA"],
    },

    # ----------------------------------------------------------
    # 30. TRANSFER_IGNORADA (LIVE) - Bruce espera la transferencia
    # ----------------------------------------------------------
    {
        "nombre": "Bruce espera transferencia correctamente",
        "descripcion": "Cliente dice espereme le paso -> Bruce espera",
        "contacto": {"nombre_negocio": "Ferreteria Espera", "ciudad": "Guadalajara"},
        "turnos": [
            {
                "cliente": "Bueno",
                "check_bruce": None,
            },
            {
                "cliente": "Espereme un momento, le paso al encargado",
                "check_bruce": None,
            },
        ],
        "bugs_esperados": [],
        "bugs_no_esperados": ["TRANSFER_IGNORADA"],
    },

    # ----------------------------------------------------------
    # 31. DESPEDIDA_PREMATURA (LIVE) - Bruce captura contacto antes de despedir
    # ----------------------------------------------------------
    {
        "nombre": "Bruce no se despide prematuramente",
        "descripcion": "Cliente interesado -> Bruce pide WhatsApp antes de despedir",
        "contacto": {"nombre_negocio": "Ferreteria Despedida OK", "ciudad": "Guadalajara"},
        "turnos": [
            {
                "cliente": "Bueno, buen dia",
                "check_bruce": None,
            },
            {
                "cliente": "Si, yo soy el encargado. Me interesa el catalogo",
                "check_bruce": None,
            },
            {
                "cliente": "Si, mi WhatsApp es 33 98 76 54 32",
                "check_bruce": None,
            },
        ],
        "bugs_esperados": [],
        "bugs_no_esperados": ["DESPEDIDA_PREMATURA"],
    },

    # ----------------------------------------------------------
    # 32. Calidad general (LIVE) - Bruce responde coherentemente
    # ----------------------------------------------------------
    {
        "nombre": "Bruce responde coherente ante preguntas",
        "descripcion": "Cliente pregunta sobre productos -> Bruce responde con info",
        "contacto": {"nombre_negocio": "Ferreteria Coherente", "ciudad": "Guadalajara"},
        "turnos": [
            {
                "cliente": "Bueno",
                "check_bruce": None,
            },
            {
                "cliente": "Si soy el encargado, que tipo de productos manejan?",
                "check_bruce": None,
            },
        ],
        "bugs_esperados": [],
        "bugs_no_esperados": ["INTERRUPCION_CONVERSACIONAL", "LOOP"],
    },

    # ==========================================================
    # GPT EVAL ESCENARIOS (requieren --gpt-eval + OPENAI_API_KEY)
    # ==========================================================

    # ----------------------------------------------------------
    # 33. GPT_LOGICA_ROTA (RAW) - Bruce pide dato ya dado
    # ----------------------------------------------------------
    {
        "nombre": "GPT detecta logica rota (dato ya dado)",
        "descripcion": "Cliente da WhatsApp, Bruce lo pide de nuevo",
        "contacto": {"nombre_negocio": "Ferreteria GPT1"},
        "simular_bug": True,

        "turnos_raw": [
            ("bruce", "Hola, me comunico de la marca Nioval para ofrecerle productos ferreteros."),
            ("cliente", "Si, que tienen?"),
            ("bruce", "Tenemos productos de alta calidad. Me podria dar su WhatsApp para enviarle el catalogo?"),
            ("cliente", "Si claro, mi WhatsApp es 33 14 25 36 47"),
            ("bruce", "Me podria dar su numero de WhatsApp para enviarle el catalogo?"),
        ],
        "bugs_esperados_any": ["GPT_LOGICA_ROTA", "GPT_RESPUESTA_INCOHERENTE"],
    },

    # ----------------------------------------------------------
    # 34. GPT_CONTEXTO_IGNORADO (RAW) - Trata encargado como empleado
    # ----------------------------------------------------------
    {
        "nombre": "GPT detecta contexto ignorado (encargado)",
        "descripcion": "Cliente es el encargado pero Bruce lo trata como empleado",
        "contacto": {"nombre_negocio": "Ferreteria GPT2"},
        "simular_bug": True,

        "turnos_raw": [
            ("bruce", "Hola, me comunico de la marca Nioval. Se encontrara el encargado de compras?"),
            ("cliente", "Yo soy el encargado de compras, yo mero"),
            ("bruce", "Ah muy bien. Y cuando regresa el encargado de compras?"),
            ("cliente", "Le digo que yo soy el encargado"),
            ("bruce", "Entendido, le paso el recado al encargado cuando este. Gracias."),
        ],
        "bugs_esperados_any": ["GPT_CONTEXTO_IGNORADO", "GPT_LOGICA_ROTA", "GPT_RESPUESTA_INCOHERENTE"],
    },

    # ----------------------------------------------------------
    # 35. GPT_OPORTUNIDAD_PERDIDA (RAW) - Cliente interesado, Bruce no pide contacto
    # ----------------------------------------------------------
    {
        "nombre": "GPT detecta oportunidad perdida",
        "descripcion": "Cliente dice me interesa, Bruce se despide sin pedir contacto",
        "contacto": {"nombre_negocio": "Ferreteria GPT3"},
        "simular_bug": True,

        "turnos_raw": [
            ("bruce", "Hola, me comunico de la marca Nioval para ofrecerle productos ferreteros."),
            ("cliente", "Ah si, que tienen?"),
            ("bruce", "Tenemos productos ferreteros de alta calidad para ferreterias como la suya."),
            ("cliente", "Me interesa mucho, mandame la informacion por favor"),
            ("bruce", "Gracias por su tiempo, que tenga un excelente dia. Hasta luego."),
        ],
        "bugs_esperados_any": ["GPT_OPORTUNIDAD_PERDIDA", "GPT_LOGICA_ROTA"],
    },

    # ----------------------------------------------------------
    # 36. GPT_RESPUESTA_INCOHERENTE (RAW) - Bruce solo dice "entiendo"
    # ----------------------------------------------------------
    {
        "nombre": "GPT detecta respuesta incoherente",
        "descripcion": "Cliente da info, Bruce responde 'entiendo' sin procesar",
        "contacto": {"nombre_negocio": "Ferreteria GPT4"},
        "simular_bug": True,

        "turnos_raw": [
            ("bruce", "Hola, me comunico de la marca Nioval para ofrecerle productos ferreteros."),
            ("cliente", "Si, nosotros compramos llaves, candados y herramientas. Que precios manejan?"),
            ("bruce", "Entiendo. Mmm."),
            ("cliente", "Pero necesito saber los precios para hacer un pedido grande"),
            ("bruce", "Aja, si. Entiendo, entiendo."),
        ],
        "bugs_esperados_any": ["GPT_RESPUESTA_INCOHERENTE", "GPT_OPORTUNIDAD_PERDIDA"],
    },

    # ----------------------------------------------------------
    # 37. GPT_FUERA_DE_TEMA (RAW) - Bruce habla de algo no relacionado
    # ----------------------------------------------------------
    {
        "nombre": "GPT detecta fuera de tema",
        "descripcion": "Bruce habla de seguros de vida en vez de ferreteria",
        "contacto": {"nombre_negocio": "Ferreteria GPT5"},
        "simular_bug": True,

        "turnos_raw": [
            ("bruce", "Hola, me comunico de la marca Nioval para ofrecerle productos ferreteros."),
            ("cliente", "Si, que productos tienen"),
            ("bruce", "Queria preguntarle si le gustaria comprar un seguro de vida para proteger a su familia."),
            ("cliente", "Pero usted no me hablaba de ferreteria?"),
            ("bruce", "Tambien tenemos seguros de gastos medicos muy completos para su empresa."),
        ],
        "bugs_esperados_any": ["GPT_FUERA_DE_TEMA", "GPT_RESPUESTA_INCORRECTA"],
    },

    # ----------------------------------------------------------
    # 38. GPT_LOGICA_ROTA (LIVE) - Bruce NO pide dato ya dado
    # ----------------------------------------------------------
    {
        "nombre": "Bruce no pide dato ya dado (GPT eval)",
        "descripcion": "Cliente da WhatsApp -> Bruce confirma, no re-pide",
        "contacto": {"nombre_negocio": "Ferreteria GPT6", "ciudad": "Guadalajara"},

        "turnos": [
            {"cliente": "Bueno, buen dia", "check_bruce": None},
            {"cliente": "Si, yo soy el encargado de compras", "check_bruce": None},
            {"cliente": "Si, mi WhatsApp es 33 14 25 36 47", "check_bruce": None},
        ],
        "bugs_esperados": [],
        "bugs_no_esperados": ["DATO_IGNORADO"],
    },

    # ----------------------------------------------------------
    # 39. GPT_CONTEXTO_IGNORADO (LIVE) - Bruce reconoce al encargado
    # ----------------------------------------------------------
    {
        "nombre": "Bruce reconoce al encargado (GPT eval)",
        "descripcion": "Cliente es encargado -> Bruce le ofrece catalogo directamente",
        "contacto": {"nombre_negocio": "Ferreteria GPT7", "ciudad": "Monterrey"},

        "turnos": [
            {"cliente": "Bueno", "check_bruce": None},
            {"cliente": "Yo soy el encargado de compras, que me ofrece?", "check_bruce": None},
        ],
        "bugs_esperados": [],
        "bugs_no_esperados": ["AREA_EQUIVOCADA"],
    },

    # ----------------------------------------------------------
    # 40. GPT_OPORTUNIDAD_PERDIDA (LIVE) - Bruce captura datos
    # ----------------------------------------------------------
    {
        "nombre": "Bruce captura datos cuando cliente esta interesado (GPT eval)",
        "descripcion": "Cliente interesado -> Bruce pide WhatsApp",
        "contacto": {"nombre_negocio": "Ferreteria GPT8", "ciudad": "Guadalajara"},

        "turnos": [
            {"cliente": "Bueno, buen dia", "check_bruce": None},
            {"cliente": "Si soy el encargado, me interesa el catalogo", "check_bruce": None},
            {"cliente": "Si, mi WhatsApp es 33 98 76 54 32", "check_bruce": None},
        ],
        "bugs_esperados": [],
        "bugs_no_esperados": ["DESPEDIDA_PREMATURA"],
    },

    # ----------------------------------------------------------
    # 41. GPT_RESPUESTA_INCOHERENTE (LIVE) - Bruce responde coherente
    # ----------------------------------------------------------
    {
        "nombre": "Bruce responde coherente a preguntas (GPT eval)",
        "descripcion": "Cliente pregunta sobre productos -> Bruce responde con info real",
        "contacto": {"nombre_negocio": "Ferreteria GPT9", "ciudad": "Guadalajara"},

        "turnos": [
            {"cliente": "Bueno", "check_bruce": None},
            {"cliente": "Si soy el encargado, que tipo de productos manejan?", "check_bruce": None},
        ],
        "bugs_esperados": [],
        "bugs_no_esperados": ["INTERRUPCION_CONVERSACIONAL"],
    },

    # ----------------------------------------------------------
    # 42. GPT_FUERA_DE_TEMA (LIVE) - Bruce se mantiene en tema
    # ----------------------------------------------------------
    {
        "nombre": "Bruce se mantiene en tema ferretero (GPT eval)",
        "descripcion": "Conversacion normal -> Bruce habla solo de ferreteria/NIOVAL",
        "contacto": {"nombre_negocio": "Ferreteria GPT10", "ciudad": "Guadalajara"},

        "turnos": [
            {"cliente": "Bueno, buen dia", "check_bruce": None},
            {"cliente": "Si, yo soy el encargado. Que marcas manejan?", "check_bruce": None},
        ],
        "bugs_esperados": [],
        "bugs_no_esperados": ["LOOP"],
    },

    # ============================================================
    # ESCENARIOS 43-82: BASADOS EN LOGS REALES (2 por bug)
    # ============================================================

    # ----------------------------------------------------------
    # 43. PREGUNTA_REPETIDA (BRUCE2143) - WhatsApp pedido 2x
    # ----------------------------------------------------------
    {
        "nombre": "BRUCE2143: WhatsApp pedido 2x tras rechazo",
        "descripcion": "Bruce pide WhatsApp despues de que cliente dice no tengo",
        "simular_bug": True,
        "turnos_raw": [
            ("bruce", "Hola, buen dia. Me comunico de la marca Nioval para ofrecerle productos ferreteros."),
            ("cliente", "Si, digame"),
            ("bruce", "Manejamos productos ferreteros de alta calidad. Me podria dar su numero de WhatsApp para enviarle el catalogo?"),
            ("cliente", "No tengo WhatsApp ahorita"),
            ("bruce", "Entiendo. Me podria dar su numero de WhatsApp para enviarle informacion?"),
        ],
        "bugs_esperados": ["PREGUNTA_REPETIDA"],
    },

    # ----------------------------------------------------------
    # 44. PREGUNTA_REPETIDA (BRUCE2111) - Dejar numero pedido 2x
    # ----------------------------------------------------------
    {
        "nombre": "BRUCE2111: Pide dejar numero 2x tras confirmacion",
        "descripcion": "Bruce repite pregunta de dejar numero despues de que cliente dijo si",
        "simular_bug": True,
        "turnos_raw": [
            ("bruce", "Hola, buen dia. Me comunico de la marca Nioval."),
            ("cliente", "Bueno"),
            ("bruce", "Me permite dejarle mi numero para que el encargado nos contacte cuando llegue?"),
            ("cliente", "Si, claro"),
            ("bruce", "Me permite dejarle mi numero para que el encargado nos contacte?"),
        ],
        "bugs_esperados": ["PREGUNTA_REPETIDA"],
    },

    # ----------------------------------------------------------
    # 45. CLIENTE_HABLA_ULTIMO (BRUCE2111) - Sucursal Sahuayo
    # ----------------------------------------------------------
    {
        "nombre": "BRUCE2111: Cliente redirige a sucursal sin respuesta",
        "descripcion": "Cliente dice hablar a otra sucursal y Bruce no responde",
        "simular_bug": True,
        "turnos_raw": [
            ("bruce", "Hola, buen dia. Me comunico de la marca Nioval."),
            ("cliente", "Si"),
            ("bruce", "Se encontrara el encargado o encargada de compras?"),
            ("cliente", "No muchacha, tienes que hablar a la sucursal de Sahuayo"),
        ],
        "bugs_esperados": ["CLIENTE_HABLA_ULTIMO"],
    },

    # ----------------------------------------------------------
    # 46. CLIENTE_HABLA_ULTIMO (BRUCE2112) - No hay ahorita
    # ----------------------------------------------------------
    {
        "nombre": "BRUCE2112: Cliente dice no hay nadie sin respuesta",
        "descripcion": "Cliente dice que no hay nadie y Bruce no responde",
        "simular_bug": True,
        "turnos_raw": [
            ("bruce", "Hola, buen dia. Me comunico de la marca Nioval."),
            ("cliente", "Si, digame"),
            ("bruce", "Se encontrara el encargado o encargada de compras?"),
            ("cliente", "No, no hay ahorita, en esta hora no hay"),
        ],
        "bugs_esperados": ["CLIENTE_HABLA_ULTIMO"],
    },

    # ----------------------------------------------------------
    # 47. SALUDO_FALTANTE (BRUCE2317) - Abre pidiendo WhatsApp
    # ----------------------------------------------------------
    {
        "nombre": "BRUCE2317: Abre pidiendo WhatsApp sin saludo",
        "descripcion": "Bruce abre la conversacion pidiendo WhatsApp sin saludar primero",
        "simular_bug": True,
        "turnos_raw": [
            ("bruce", "Me podria dar su WhatsApp para enviarle el catalogo de nuestros productos?"),
            ("cliente", "Que? Quien habla?"),
            ("bruce", "Le llamo de la marca Nioval, somos distribuidores de productos ferreteros."),
        ],
        "bugs_esperados": ["SALUDO_FALTANTE"],
    },

    # ----------------------------------------------------------
    # 48. SALUDO_FALTANTE (BRUCE2350) - Abre con pregunta encargado
    # ----------------------------------------------------------
    {
        "nombre": "BRUCE2350: Abre preguntando encargado sin saludo",
        "descripcion": "Bruce pregunta por encargado sin saludar primero",
        "simular_bug": True,
        "turnos_raw": [
            ("bruce", "Se encontrara el encargado o encargada de compras para hablarle sobre productos ferreteros?"),
            ("cliente", "Quien habla?"),
            ("bruce", "Le llamo de la marca Nioval."),
        ],
        "bugs_esperados": ["SALUDO_FALTANTE"],
    },

    # ----------------------------------------------------------
    # 49. PITCH_REPETIDO (BRUCE2118) - Pitch 2x misma llamada
    # ----------------------------------------------------------
    {
        "nombre": "BRUCE2118: Pitch Nioval repetido 2x",
        "descripcion": "Bruce repite el pitch de Nioval despues de que cliente pregunta",
        "simular_bug": True,
        "turnos_raw": [
            ("bruce", "Hola, buen dia. Me comunico de la marca Nioval, trabajamos productos ferreteros."),
            ("cliente", "Ah si? Ustedes venden herramientas?"),
            ("bruce", "Si, me comunico de la marca Nioval, trabajamos productos ferreteros para su negocio."),
            ("cliente", "Ok, y que tienen?"),
        ],
        "bugs_esperados": ["PITCH_REPETIDO"],
    },

    # ----------------------------------------------------------
    # 50. PITCH_REPETIDO (BRUCE2106) - Pitch repetido tras IVR
    # ----------------------------------------------------------
    {
        "nombre": "BRUCE2106: Pitch repetido tras respuesta IVR",
        "descripcion": "Bruce repite pitch exacto despues de IVR",
        "simular_bug": True,
        "turnos_raw": [
            ("bruce", "Hola, buen dia. Me comunico de la marca Nioval, trabajamos productos ferreteros. Se encuentra el encargado de compras?"),
            ("cliente", "Para ventas marque uno, administracion dos"),
            ("bruce", "Me comunico de la marca Nioval, trabajamos productos ferreteros. Se encuentra el encargado de compras?"),
        ],
        "bugs_esperados": ["PITCH_REPETIDO"],
    },

    # ----------------------------------------------------------
    # 51. CATALOGO_REPETIDO (BRUCE2118) - Catalogo ofrecido 2x
    # ----------------------------------------------------------
    {
        "nombre": "BRUCE2118: Catalogo ofrecido 2x en misma llamada",
        "descripcion": "Bruce ofrece enviar catalogo dos veces",
        "simular_bug": True,
        "turnos_raw": [
            ("bruce", "Hola, buen dia. Me comunico de la marca Nioval."),
            ("cliente", "Si, digame"),
            ("bruce", "Le puedo enviar nuestro catalogo de productos por WhatsApp si gusta."),
            ("cliente", "Mmm, no se si me interese"),
            ("bruce", "Le envio el catalogo para que lo revise con calma, sin compromiso."),
        ],
        "bugs_esperados": ["CATALOGO_REPETIDO"],
    },

    # ----------------------------------------------------------
    # 52. CATALOGO_REPETIDO - Variante con "mando" y "envio"
    # ----------------------------------------------------------
    {
        "nombre": "Catalogo repetido: mando + envio variante",
        "descripcion": "Bruce ofrece catalogo con diferentes palabras pero mismo intent",
        "simular_bug": True,
        "turnos_raw": [
            ("bruce", "Hola, buen dia. Me comunico de la marca Nioval."),
            ("cliente", "Si, que necesita?"),
            ("bruce", "Le mando nuestro catalogo de productos ferreteros por WhatsApp?"),
            ("cliente", "No se, dejeme ver"),
            ("bruce", "Le envio nuestro catalogo sin compromiso para que lo revise?"),
        ],
        "bugs_esperados": ["CATALOGO_REPETIDO"],
    },

    # ----------------------------------------------------------
    # 53. INTERRUPCION_CONVERSACIONAL (BRUCE2446) - No es ferreteria
    # ----------------------------------------------------------
    {
        "nombre": "BRUCE2446: Cliente dice no es ferreteria, Bruce sigue",
        "descripcion": "Cliente explica que no es ferreteria pero Bruce interrumpe con pitch",
        "simular_bug": True,
        "turnos_raw": [
            ("bruce", "Hola, buen dia. Me comunico de la marca Nioval."),
            ("cliente", "Es que no es aqui en ferreteria, no hacemos eso"),
            ("bruce", "Me comunico de Nioval, trabajamos productos ferreteros de calidad."),
        ],
        "bugs_esperados": ["INTERRUPCION_CONVERSACIONAL"],
    },

    # ----------------------------------------------------------
    # 54. INTERRUPCION_CONVERSACIONAL - Cliente explica su ramo
    # ----------------------------------------------------------
    {
        "nombre": "Cliente explica su ramo, Bruce interrumpe con pitch",
        "descripcion": "Cliente dice que estan enfocados en otro ramo y Bruce interrumpe",
        "simular_bug": True,
        "turnos_raw": [
            ("bruce", "Hola, buen dia. Me comunico de la marca Nioval."),
            ("cliente", "Mire, le explico, nosotros estamos enfocados en otro ramo"),
            ("bruce", "Me comunico de Nioval, trabajamos productos ferreteros para su negocio."),
        ],
        "bugs_esperados": ["INTERRUPCION_CONVERSACIONAL"],
    },

    # ----------------------------------------------------------
    # 55. BRUCE_MUDO (BRUCE2133) - TwiML sin audio
    # ----------------------------------------------------------
    {
        "nombre": "BRUCE2133: TwiML enviado pero audio nunca fetched",
        "descripcion": "Bruce genera TwiML pero el audio nunca se reproduce",
        "simular_bug": True,
        "tracker_attrs": {"twiml_count": 2, "audio_fetch_count": 0},
        "turnos_raw": [
            ("bruce", "Hola, buen dia. Me comunico de la marca Nioval."),
            ("cliente", "Bueno?"),
            ("bruce", ""),
            ("cliente", "Bueno? Me escucha? Hay alguien ahi?"),
        ],
        "bugs_esperados": ["BRUCE_MUDO"],
    },

    # ----------------------------------------------------------
    # 56. BRUCE_MUDO - Respuesta vacia tras pregunta
    # ----------------------------------------------------------
    {
        "nombre": "Bruce mudo: respuesta vacia tras pregunta cliente",
        "descripcion": "Cliente pregunta y Bruce no responde",
        "simular_bug": True,
        "tracker_attrs": {"twiml_count": 3, "audio_fetch_count": 0},
        "turnos_raw": [
            ("bruce", "Hola, buen dia. Me comunico de la marca Nioval."),
            ("cliente", "Si, que productos manejan?"),
            ("bruce", ""),
            ("cliente", "Oiga? Hay alguien?"),
        ],
        "bugs_esperados": ["BRUCE_MUDO"],
    },

    # ----------------------------------------------------------
    # 57. RESPUESTA_FILLER_INCOHERENTE (BRUCE2446) - TTS falla
    # ----------------------------------------------------------
    {
        "nombre": "BRUCE2446: TTS falla y envia filler incoherente",
        "descripcion": "ElevenLabs TTS falla y Bruce responde con filler dejeme ver",
        "simular_bug": True,
        "tracker_attrs": {"filler_162a_count": 2},
        "turnos_raw": [
            ("bruce", "Hola, buen dia. Me comunico de la marca Nioval."),
            ("cliente", "Si, que tipo de productos manejan?"),
            ("bruce", "Dejeme ver"),
            ("cliente", "Bueno?"),
            ("bruce", "Mmm"),
        ],
        "bugs_esperados": ["RESPUESTA_FILLER_INCOHERENTE"],
    },

    # ----------------------------------------------------------
    # 58. RESPUESTA_FILLER_INCOHERENTE - Fillers consecutivos
    # ----------------------------------------------------------
    {
        "nombre": "Fillers consecutivos: dejeme ver + mmm + ajasi",
        "descripcion": "Bruce responde solo con fillers sin contenido real",
        "simular_bug": True,
        "tracker_attrs": {"filler_162a_count": 3},
        "turnos_raw": [
            ("bruce", "Hola, buen dia. Me comunico de la marca Nioval."),
            ("cliente", "Si, cuanto cuesta el catalogo?"),
            ("bruce", "Dejeme ver"),
            ("cliente", "Ya tiene el precio?"),
            ("bruce", "Mmm dejeme ver"),
        ],
        "bugs_esperados": ["RESPUESTA_FILLER_INCOHERENTE"],
    },

    # ----------------------------------------------------------
    # 59. DICTADO_INTERRUMPIDO (BRUCE2446) - Despedida durante dictado
    # ----------------------------------------------------------
    {
        "nombre": "BRUCE2446: Bruce se despide mientras cliente dicta",
        "descripcion": "Cliente dictando dato y Bruce se despide abruptamente",
        "simular_bug": True,
        "turnos_raw": [
            ("bruce", "Me podria dar su correo electronico?"),
            ("cliente", "Si, mi correo es ferreteria arroba hotmail punto"),
            ("bruce", "Muchas gracias por su tiempo, que tenga buen dia."),
        ],
        "bugs_esperados": ["DICTADO_INTERRUMPIDO"],
    },

    # ----------------------------------------------------------
    # 60. DICTADO_INTERRUMPIDO - Numero parcial cortado
    # ----------------------------------------------------------
    {
        "nombre": "Dictado interrumpido: numero parcial cortado",
        "descripcion": "Cliente da numero parcial y Bruce cambia tema",
        "simular_bug": True,
        "turnos_raw": [
            ("bruce", "Digame su numero de WhatsApp por favor."),
            ("cliente", "Si claro, mi whatsapp es 33 14 25"),
            ("bruce", "Muchas gracias por su tiempo, que tenga buen dia."),
        ],
        "bugs_esperados": ["DICTADO_INTERRUMPIDO"],
    },

    # ----------------------------------------------------------
    # 61. LOOP (BRUCE1889) - Digame el correo 3x
    # ----------------------------------------------------------
    {
        "nombre": "BRUCE1889: Pide correo 4 veces en loop",
        "descripcion": "Bruce repite si por favor digame el correo multiples veces",
        "simular_bug": True,
        "turnos_raw": [
            ("bruce", "Hola, buen dia. Me comunico de la marca Nioval."),
            ("cliente", "Muy bien, yo te doy el correo"),
            ("bruce", "Si, por favor, digame el correo."),
            ("cliente", "Espereme tantito"),
            ("bruce", "Si, por favor, digame el correo."),
            ("cliente", "Si mire es Martin Compras"),
            ("bruce", "Si, por favor, digame el correo."),
        ],
        "bugs_esperados": ["LOOP"],
    },

    # ----------------------------------------------------------
    # 62. LOOP - Encargado preguntado 3x
    # ----------------------------------------------------------
    {
        "nombre": "Loop: pregunta por encargado 3 veces",
        "descripcion": "Bruce pregunta se encontrara el encargado 3 veces seguidas",
        "simular_bug": True,
        "turnos_raw": [
            ("bruce", "Hola, buen dia. Me comunico de la marca Nioval."),
            ("cliente", "Si"),
            ("bruce", "Se encontrara el encargado de compras?"),
            ("cliente", "No se"),
            ("bruce", "Se encontrara el encargado de compras?"),
            ("cliente", "Le digo que no se"),
            ("bruce", "Se encontrara el encargado de compras?"),
        ],
        "bugs_esperados": ["LOOP"],
    },

    # ----------------------------------------------------------
    # 63. DATO_IGNORADO (BRUCE2087) - Email dictado e ignorado
    # ----------------------------------------------------------
    {
        "nombre": "BRUCE2087: Email completo dictado pero Bruce re-pregunta",
        "descripcion": "Cliente dicta correo completo y Bruce lo pide de nuevo",
        "simular_bug": True,
        "turnos_raw": [
            ("bruce", "Hola, buen dia. Me comunico de la marca Nioval."),
            ("cliente", "Si, le doy el correo, es ferreterialafuente arroba hotmail punto com"),
            ("bruce", "Me podria dar su correo electronico para enviarle informacion?"),
        ],
        "bugs_esperados": ["DATO_IGNORADO"],
    },

    # ----------------------------------------------------------
    # 64. DATO_IGNORADO - WhatsApp dado e ignorado
    # ----------------------------------------------------------
    {
        "nombre": "Dato ignorado: WhatsApp dado y Bruce lo pide otra vez",
        "descripcion": "Cliente da WhatsApp y Bruce pide el numero de nuevo",
        "simular_bug": True,
        "turnos_raw": [
            ("bruce", "Hola, buen dia. Me comunico de la marca Nioval."),
            ("cliente", "Si, mi numero es 3312456789"),
            ("bruce", "Me podria dar su numero de WhatsApp para enviarle el catalogo?"),
        ],
        "bugs_esperados": ["DATO_IGNORADO"],
    },

    # ----------------------------------------------------------
    # 65. AREA_EQUIVOCADA (BRUCE1893) - Taller mecanico
    # ----------------------------------------------------------
    {
        "nombre": "BRUCE1893: Cliente dice es taller mecanico",
        "descripcion": "Cliente indica que es taller mecanico y Bruce sigue vendiendo ferreteria",
        "simular_bug": True,
        "turnos_raw": [
            ("bruce", "Hola, buen dia. Me comunico de la marca Nioval, trabajamos productos ferreteros."),
            ("cliente", "Lo que pasa es que aqui no es ferreteria, es un taller mecanico"),
            ("bruce", "Entiendo, le puedo enviar nuestro catalogo de productos ferreteros?"),
        ],
        "bugs_esperados": ["AREA_EQUIVOCADA"],
    },

    # ----------------------------------------------------------
    # 66. AREA_EQUIVOCADA - No vendemos ferreteria
    # ----------------------------------------------------------
    {
        "nombre": "Area equivocada: no vendemos ferreteria",
        "descripcion": "Cliente dice que no vende ferreteria y Bruce insiste",
        "simular_bug": True,
        "turnos_raw": [
            ("bruce", "Hola, buen dia. Me comunico de la marca Nioval."),
            ("cliente", "Mire, nosotros no vendemos ferreteria, somos una papeleria"),
            ("bruce", "Le puedo enviar nuestro catalogo de productos para que lo revise?"),
        ],
        "bugs_esperados": ["AREA_EQUIVOCADA"],
    },

    # ----------------------------------------------------------
    # 67. DESPEDIDA_PREMATURA (BRUCE2080) - Sin datos capturados
    # ----------------------------------------------------------
    {
        "nombre": "BRUCE2080: Despedida sin capturar ningun dato",
        "descripcion": "Bruce se despide cuando cliente mostro interes sin capturar contacto",
        "simular_bug": True,
        "turnos_raw": [
            ("bruce", "Hola, buen dia. Me comunico de la marca Nioval."),
            ("cliente", "Si, me interesa, mandame informacion"),
            ("bruce", "Con gusto. Que tipo de productos le interesan?"),
            ("cliente", "Herramientas en general"),
            ("bruce", "Muchas gracias por su tiempo, que tenga buen dia."),
        ],
        "bugs_esperados": ["DESPEDIDA_PREMATURA"],
    },

    # ----------------------------------------------------------
    # 68. DESPEDIDA_PREMATURA (BRUCE2446) - Se despide sin info
    # ----------------------------------------------------------
    {
        "nombre": "BRUCE2446: Se despide cuando cliente quiere dar dato",
        "descripcion": "Cliente dice enviame info y Bruce se despide sin capturar",
        "simular_bug": True,
        "turnos_raw": [
            ("bruce", "Hola, buen dia. Me comunico de la marca Nioval."),
            ("cliente", "Si claro, enviame el catalogo"),
            ("bruce", "Perfecto. Que productos le interesan mas?"),
            ("cliente", "Herramientas y cerraduras"),
            ("bruce", "Hasta luego, que tenga buen dia."),
        ],
        "bugs_esperados": ["DESPEDIDA_PREMATURA"],
    },

    # ----------------------------------------------------------
    # 69. TRANSFER_IGNORADA - Espereme le paso al encargado
    # ----------------------------------------------------------
    {
        "nombre": "Transfer ignorada: espereme le paso al encargado",
        "descripcion": "Cliente pide esperar para transferir y Bruce sigue con pitch",
        "simular_bug": True,
        "turnos_raw": [
            ("bruce", "Hola, buen dia. Me comunico de la marca Nioval."),
            ("cliente", "Si, espereme, le paso al encargado"),
            ("bruce", "Le puedo enviar nuestro catalogo de productos ferreteros por WhatsApp?"),
        ],
        "bugs_esperados": ["TRANSFER_IGNORADA"],
    },

    # ----------------------------------------------------------
    # 70. TRANSFER_IGNORADA - Permitame un momento
    # ----------------------------------------------------------
    {
        "nombre": "Transfer ignorada: permitame un momento le comunico",
        "descripcion": "Cliente dice permitame y Bruce hace pitch en vez de esperar",
        "simular_bug": True,
        "turnos_raw": [
            ("bruce", "Hola, buen dia. Me comunico de la marca Nioval. Se encontrara el encargado?"),
            ("cliente", "Si, dejeme comunicarlo, un momento por favor"),
            ("bruce", "Le comento, somos distribuidores de productos ferreteros de alta calidad."),
        ],
        "bugs_esperados": ["TRANSFER_IGNORADA"],
    },

    # ----------------------------------------------------------
    # 71. DEGRADACION_TTS (BRUCE1895) - Fillers multiples
    # ----------------------------------------------------------
    {
        "nombre": "BRUCE1895: Degradacion TTS con fillers multiples",
        "descripcion": "TTS falla y genera multiples fillers consecutivos",
        "simular_bug": True,
        "tracker_attrs": {"filler_162a_count": 3},
        "turnos_raw": [
            ("bruce", "Hola, buen dia. Me comunico de la marca Nioval."),
            ("cliente", "Si, que productos tienen?"),
            ("bruce", "Mmm"),
            ("cliente", "Bueno?"),
            ("bruce", "Dejeme ver"),
            ("cliente", "Oiga?"),
            ("bruce", "Mmm dejeme ver"),
        ],
        "bugs_esperados": ["DEGRADACION_TTS"],
    },

    # ----------------------------------------------------------
    # 72. DEGRADACION_TTS - Doble filler mmm
    # ----------------------------------------------------------
    {
        "nombre": "Degradacion TTS: doble filler sin respuesta real",
        "descripcion": "Bruce responde con fillers sin dar respuesta real",
        "simular_bug": True,
        "tracker_attrs": {"filler_162a_count": 2},
        "turnos_raw": [
            ("bruce", "Hola, buen dia. Me comunico de la marca Nioval."),
            ("cliente", "Cuanto cuesta el envio?"),
            ("bruce", "Mmm"),
            ("cliente", "Me escucha?"),
            ("bruce", "Mmm dejeme ver"),
        ],
        "bugs_esperados": ["DEGRADACION_TTS"],
    },

    # ----------------------------------------------------------
    # 73. GPT_LOGICA_ROTA (BRUCE2505) - Pide WhatsApp ya sabiendo
    # ----------------------------------------------------------
    {
        "nombre": "BRUCE2505: Pide WhatsApp cuando ya sabe que encargado no esta",
        "descripcion": "Cliente dice que encargado no se encuentra, Bruce pide WhatsApp como si no supiera",
        "simular_bug": True,
        "turnos_raw": [
            ("bruce", "Hola, buen dia. Me comunico de la marca Nioval. Se encontrara el encargado de compras?"),
            ("cliente", "No, no se encuentra"),
            ("bruce", "Entiendo que no se encuentra. Me podria proporcionar un WhatsApp para enviarle el catalogo al encargado?"),
            ("cliente", "Ya le dije que no esta el encargado, no insista"),
            ("bruce", "Me podria proporcionar un WhatsApp o correo para enviarle el catalogo al encargado?"),
        ],
        "bugs_esperados_any": ["GPT_LOGICA_ROTA", "GPT_RESPUESTA_INCOHERENTE"],
    },

    # ----------------------------------------------------------
    # 74. GPT_LOGICA_ROTA (BRUCE2106) - Repite pregunta tras IVR
    # ----------------------------------------------------------
    {
        "nombre": "BRUCE2106: Repite pregunta identica tras IVR",
        "descripcion": "IVR da opciones y Bruce repite la misma pregunta sin procesar",
        "simular_bug": True,
        "turnos_raw": [
            ("bruce", "Hola, buen dia. Me comunico de la marca Nioval. Se encuentra el encargado de compras?"),
            ("cliente", "Para ventas marque uno, administracion dos"),
            ("bruce", "Se encuentra el encargado de compras?"),
            ("cliente", "Le digo que es un conmutador, no hay encargado aqui"),
            ("bruce", "Disculpe, no escuche bien. Me puede repetir su pregunta?"),
        ],
        "bugs_esperados_any": ["GPT_LOGICA_ROTA", "GPT_FUERA_DE_TEMA", "GPT_RESPUESTA_INCOHERENTE"],
    },

    # ----------------------------------------------------------
    # 75. GPT_CONTEXTO_IGNORADO (BRUCE2508) - Area de ventas
    # ----------------------------------------------------------
    {
        "nombre": "BRUCE2508: Ignora que cliente es de area de ventas",
        "descripcion": "Cliente dice esta es area de ventas y Bruce sigue buscando encargado compras",
        "simular_bug": True,
        "turnos_raw": [
            ("bruce", "Hola, buen dia. Me comunico de la marca Nioval. Se encontrara el encargado de compras?"),
            ("cliente", "No, disculpe, esta es area de ventas"),
            ("bruce", "Entiendo. Tendras algun contacto para poder hablar con el encargado de compras?"),
            ("cliente", "Le digo que aqui no hay encargado de compras, esta es area de ventas"),
            ("bruce", "Me podria comunicar con alguien del area de compras?"),
        ],
        "bugs_esperados_any": ["GPT_CONTEXTO_IGNORADO", "GPT_LOGICA_ROTA", "GPT_FUERA_DE_TEMA"],
    },

    # ----------------------------------------------------------
    # 76. GPT_CONTEXTO_IGNORADO - Yo soy el dueno
    # ----------------------------------------------------------
    {
        "nombre": "Contexto ignorado: cliente es el dueno y Bruce busca encargado",
        "descripcion": "Cliente dice yo soy el dueno y Bruce pide hablar con encargado",
        "simular_bug": True,
        "turnos_raw": [
            ("bruce", "Hola, buen dia. Me comunico de la marca Nioval. Se encontrara el encargado de compras?"),
            ("cliente", "Yo soy el dueno de la ferreteria"),
            ("bruce", "Entiendo. Y cuando regresa el encargado de compras?"),
            ("cliente", "Le digo que yo soy el dueno, yo mero"),
            ("bruce", "Ah perfecto. Y a que hora puedo encontrar al encargado de compras?"),
        ],
        "bugs_esperados_any": ["GPT_CONTEXTO_IGNORADO", "GPT_LOGICA_ROTA"],
    },

    # ----------------------------------------------------------
    # 77. GPT_OPORTUNIDAD_PERDIDA (BRUCE2508) - Web ofrecida
    # ----------------------------------------------------------
    {
        "nombre": "BRUCE2508: Cliente ofrece pagina web y Bruce ignora",
        "descripcion": "Cliente da pagina web como contacto alternativo pero Bruce no capitaliza",
        "simular_bug": True,
        "turnos_raw": [
            ("bruce", "Hola, buen dia. Me comunico de la marca Nioval. Se encontrara el encargado de compras?"),
            ("cliente", "No esta. Pero en la pagina de internet esta disponible, gota punto com punto mx"),
            ("bruce", "Entiendo. Me podria dar un numero de WhatsApp?"),
            ("cliente", "Le digo que en la pagina esta toda la informacion"),
            ("bruce", "Me podria dar su numero de WhatsApp para enviarle el catalogo?"),
        ],
        "bugs_esperados_any": ["GPT_OPORTUNIDAD_PERDIDA", "GPT_LOGICA_ROTA", "GPT_FUERA_DE_TEMA"],
    },

    # ----------------------------------------------------------
    # 78. GPT_OPORTUNIDAD_PERDIDA (BRUCE2507) - Callback ignorado
    # ----------------------------------------------------------
    {
        "nombre": "BRUCE2507: Cliente dice en 20 min llega, Bruce pide WhatsApp",
        "descripcion": "Cliente ofrece horario de callback pero Bruce ignora y pide WhatsApp",
        "simular_bug": True,
        "turnos_raw": [
            ("bruce", "Hola, buen dia. Me comunico de la marca Nioval. Se encontrara el encargado de compras?"),
            ("cliente", "No se encuentra, como en veinte minutos llega"),
            ("bruce", "Entiendo que no se encuentra. Me podria proporcionar un WhatsApp o correo?"),
            ("cliente", "Le digo que en veinte minutos llega, llamele otra vez"),
            ("bruce", "Me podria dar su numero de WhatsApp para enviarle informacion?"),
        ],
        "bugs_esperados_any": ["GPT_OPORTUNIDAD_PERDIDA", "GPT_LOGICA_ROTA"],
    },

    # ----------------------------------------------------------
    # 79. GPT_RESPUESTA_INCOHERENTE (BRUCE2505) - Adelante x3
    # ----------------------------------------------------------
    {
        "nombre": "BRUCE2505: Responde si adelante sin procesar info",
        "descripcion": "Bruce responde genericamente adelante/continue sin procesar lo que dice el cliente",
        "simular_bug": True,
        "turnos_raw": [
            ("bruce", "Hola, buen dia. Me comunico de la marca Nioval."),
            ("cliente", "Buenas tardes"),
            ("bruce", "Se encontrara el encargado de compras?"),
            ("cliente", "A quien busca?"),
            ("bruce", "Si, adelante."),
            ("cliente", "Le pregunte a quien busca, al encargado o a quien"),
            ("bruce", "Claro, continue."),
        ],
        "bugs_esperados_any": ["GPT_RESPUESTA_INCOHERENTE", "GPT_LOGICA_ROTA", "GPT_FUERA_DE_TEMA"],
    },

    # ----------------------------------------------------------
    # 80. GPT_RESPUESTA_INCOHERENTE (BRUCE2446) - Entiendo sin procesar
    # ----------------------------------------------------------
    {
        "nombre": "BRUCE2446: Entiendo sin procesar que no es ferreteria",
        "descripcion": "Cliente dice que no es ferreteria y Bruce dice entiendo sin reaccionar",
        "simular_bug": True,
        "turnos_raw": [
            ("bruce", "Hola, buen dia. Me comunico de la marca Nioval, trabajamos productos ferreteros."),
            ("cliente", "Es que no es aqui ferreteria, no hacemos eso"),
            ("bruce", "Entiendo. Me permite dejarle mi numero para que el encargado nos contacte?"),
            ("cliente", "Le digo que no es ferreteria, aqui no hay encargado de eso"),
            ("bruce", "Ajá, si. Y me podria dar un WhatsApp del encargado?"),
        ],
        "bugs_esperados_any": ["GPT_RESPUESTA_INCOHERENTE", "GPT_CONTEXTO_IGNORADO", "GPT_LOGICA_ROTA", "GPT_FUERA_DE_TEMA"],
    },

    # ----------------------------------------------------------
    # 81. GPT_FUERA_DE_TEMA (BRUCE2100) - Rechazo pero ofrece catalogo
    # ----------------------------------------------------------
    {
        "nombre": "BRUCE2100: Cliente rechaza pero Bruce ofrece catalogo",
        "descripcion": "Cliente dice voy a comprar aqui y Bruce sigue ofreciendo catalogo",
        "simular_bug": True,
        "turnos_raw": [
            ("bruce", "Hola, buen dia. Me comunico de la marca Nioval, trabajamos productos ferreteros."),
            ("cliente", "No, no se preocupe, voy a comprar eso aqui, no"),
            ("bruce", "Entiendo. Si le interesa, le puedo enviar nuestro catalogo por WhatsApp."),
            ("cliente", "No gracias, ya le dije que no"),
            ("bruce", "Le envio el catalogo sin compromiso para que lo revise con calma?"),
        ],
        "bugs_esperados_any": ["GPT_FUERA_DE_TEMA", "GPT_LOGICA_ROTA", "GPT_OPORTUNIDAD_PERDIDA", "GPT_TONO_INADECUADO"],
    },

    # ----------------------------------------------------------
    # 82. GPT_FUERA_DE_TEMA (BRUCE2446) - No es ferreteria pero insiste
    # ----------------------------------------------------------
    {
        "nombre": "BRUCE2446: Insiste dejar numero en negocio no ferretero",
        "descripcion": "Cliente dice que no es ferreteria y Bruce insiste en dejar numero",
        "simular_bug": True,
        "turnos_raw": [
            ("bruce", "Hola, buen dia. Me comunico de la marca Nioval, trabajamos productos ferreteros."),
            ("cliente", "Mire, aqui no es ferreteria, somos una farmacia"),
            ("bruce", "Entiendo. Me permite dejarle mi numero para que el encargado nos contacte?"),
            ("cliente", "Le digo que somos farmacia, no tenemos encargado de ferreteria"),
            ("bruce", "Le envio nuestro catalogo de productos ferreteros por WhatsApp?"),
        ],
        "bugs_esperados_any": ["GPT_FUERA_DE_TEMA", "GPT_CONTEXTO_IGNORADO", "GPT_LOGICA_ROTA"],
    },
]


# ============================================================
# SIMULADOR
# ============================================================

class SimuladorLlamada:
    """Ejecuta escenarios de prueba contra AgenteVentas + BugDetector."""

    def __init__(self, verbose=False):
        self.verbose = verbose
        self.tiene_openai = bool(os.environ.get('OPENAI_API_KEY', ''))
        self.resultados = []

    def ejecutar_escenario(self, idx, escenario):
        """Ejecuta un escenario y retorna resultado."""
        nombre = escenario["nombre"]
        resultado = {
            "nombre": nombre,
            "idx": idx + 1,
            "turnos": [],
            "bugs_detectados": [],
            "bugs_esperados": escenario.get("bugs_esperados", []),
            "bugs_esperados_any": escenario.get("bugs_esperados_any", []),
            "bugs_no_esperados": escenario.get("bugs_no_esperados", []),
            "passed": False,
            "errores": [],
            "tiempo_ms": 0,
        }

        t0 = time.time()

        try:
            if escenario.get("simular_bug"):
                # Modo raw: conversacion pre-armada (para testear bug detector)
                self._ejecutar_raw(escenario, resultado)
            else:
                # Modo normal: usa AgenteVentas.procesar_respuesta()
                self._ejecutar_agente(escenario, resultado)
        except Exception as e:
            resultado["errores"].append(f"EXCEPCION: {e}")

        resultado["tiempo_ms"] = int((time.time() - t0) * 1000)

        # Evaluar pass/fail
        self._evaluar_resultado(resultado)
        self.resultados.append(resultado)
        return resultado

    def _ejecutar_agente(self, escenario, resultado):
        """Ejecuta escenario usando AgenteVentas real."""
        contacto = escenario.get("contacto", {})
        agente = AgenteVentas(contacto_info=contacto)
        saludo = agente.iniciar_conversacion()

        # Setup segunda parte saludo (simula lo que hace servidor)
        agente.conversacion_iniciada = True
        agente.segunda_parte_saludo_dicha = True

        # Agregar pitch al historial (simula turno 1 completo)
        pitch = agente._get_segunda_parte_saludo() if hasattr(agente, '_get_segunda_parte_saludo') else ""
        if pitch:
            agente.conversation_history.append({"role": "assistant", "content": pitch})
            saludo_completo = f"{saludo} {pitch}"
        else:
            saludo_completo = saludo

        resultado["turnos"].append({
            "role": "bruce",
            "texto": saludo_completo,
            "estado": str(agente.estado_conversacion.value),
        })

        for turno in escenario.get("turnos", []):
            cliente_dice = turno["cliente"]

            try:
                respuesta = agente.procesar_respuesta(cliente_dice)
            except Exception as e:
                respuesta = f"[ERROR: {e}]"
                resultado["errores"].append(f"procesar_respuesta error: {e}")

            resultado["turnos"].append({
                "role": "cliente",
                "texto": cliente_dice,
            })
            resultado["turnos"].append({
                "role": "bruce",
                "texto": respuesta or "[VACIO]",
                "estado": str(agente.estado_conversacion.value),
            })

            # Checks por turno
            if turno.get("check_bruce"):
                for keyword in turno["check_bruce"]:
                    if keyword.lower() not in (respuesta or "").lower():
                        resultado["errores"].append(
                            f"Check fallido: '{keyword}' no encontrado en respuesta Bruce"
                        )

        # Bug detection
        self._run_bug_detector(resultado)

    def _ejecutar_raw(self, escenario, resultado):
        """Ejecuta escenario con conversacion pre-armada (no usa AgenteVentas)."""
        for role, texto in escenario["turnos_raw"]:
            resultado["turnos"].append({
                "role": role,
                "texto": texto,
                "estado": "-",
            })

        # Bug detection (con tracker_attrs opcionales para metadata del servidor)
        self._run_bug_detector(resultado, tracker_attrs=escenario.get("tracker_attrs"))

    def _run_bug_detector(self, resultado, tracker_attrs=None):
        """Corre bug detector rule-based (y GPT eval si --gpt-eval) sobre la conversacion."""
        tracker = CallEventTracker(
            call_sid=f"SIM-{resultado['idx']:03d}",
            bruce_id=f"SIMTEST-{resultado['idx']:03d}",
            telefono="0000000000"
        )

        # Simular duracion de 60s para pasar threshold GPT eval (20s)
        tracker.created_at = time.time() - 60

        # Aplicar atributos de tracker opcionales (metadata servidor: twiml_count, etc.)
        if tracker_attrs:
            for attr, val in tracker_attrs.items():
                setattr(tracker, attr, val)

        for turno in resultado["turnos"]:
            role = turno["role"]
            texto = turno["texto"]
            if role == "bruce":
                tracker.conversacion.append(("bruce", texto))
                tracker.respuestas_bruce.append(texto)
            elif role == "cliente":
                tracker.conversacion.append(("cliente", texto))
                tracker.textos_cliente.append(texto)

        try:
            bugs = BugDetector.analyze(tracker)

            # GPT eval: evaluar conversacion con GPT-4o-mini
            try:
                gpt_bugs = _evaluar_con_gpt(tracker)
                bugs.extend(gpt_bugs)
            except Exception as e:
                resultado["errores"].append(f"GPT eval error: {e}")

            resultado["bugs_detectados"] = bugs
        except Exception as e:
            resultado["errores"].append(f"Bug detector error: {e}")

    def _evaluar_resultado(self, resultado):
        """Evalua si el escenario paso o fallo."""
        tipos_detectados = {b["tipo"] for b in resultado["bugs_detectados"]}
        passed = True

        # Verificar bugs esperados esten presentes (todos deben existir)
        for esperado in resultado["bugs_esperados"]:
            if esperado not in tipos_detectados:
                resultado["errores"].append(
                    f"Bug esperado '{esperado}' NO detectado"
                )
                passed = False

        # Verificar bugs esperados ANY (al menos uno debe existir)
        bugs_any = resultado.get("bugs_esperados_any", [])
        if bugs_any:
            if not any(b in tipos_detectados for b in bugs_any):
                resultado["errores"].append(
                    f"Ninguno de {bugs_any} detectado (encontrados: {list(tipos_detectados)})"
                )
                passed = False

        # Verificar bugs no esperados NO esten presentes
        for no_esperado in resultado.get("bugs_no_esperados", []):
            if no_esperado in tipos_detectados:
                resultado["errores"].append(
                    f"Bug inesperado '{no_esperado}' detectado"
                )
                passed = False

        # Si hay errores de ejecucion, falla
        if resultado["errores"]:
            passed = False

        resultado["passed"] = passed


# ============================================================
# REPORTE
# ============================================================

def imprimir_reporte(resultados, verbose=False):
    """Imprime reporte formateado."""
    modo = "GPT REAL" if os.environ.get('OPENAI_API_KEY', '') else "TEMPLATE (sin OPENAI_API_KEY)"
    total = len(resultados)
    passed = sum(1 for r in resultados if r["passed"])
    failed = total - passed

    print()
    print("=" * 60)
    print("  SIMULADOR DE LLAMADAS BRUCE W")
    print(f"  Modo: {modo}")
    print(f"  Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    print()

    for r in resultados:
        idx = r["idx"]
        nombre = r["nombre"]
        tiempo = r["tiempo_ms"]

        status = "PASS" if r["passed"] else "FAIL"
        icon = "[OK]" if r["passed"] else "[FAIL]"

        print(f"  [{idx}/{total}] {nombre}")

        if verbose:
            # Mostrar cada turno
            turno_num = 0
            for t in r["turnos"]:
                if t["role"] == "cliente":
                    turno_num += 1
                    print(f"    T{turno_num} Cliente: \"{t['texto'][:80]}\"")
                elif t["role"] == "bruce":
                    estado = t.get("estado", "")
                    estado_str = f" [{estado}]" if estado and estado != "-" else ""
                    print(f"       Bruce:   \"{t['texto'][:80]}\"{estado_str}")
            print()

        # Bugs detectados
        bugs = r["bugs_detectados"]
        if bugs:
            tipos_str = ", ".join(f"{b['tipo']}({b['severidad']})" for b in bugs)
            print(f"    Bugs: {tipos_str}")

        # Errores
        for err in r["errores"]:
            print(f"    ERROR: {err}")

        print(f"    {icon} {status} ({tiempo}ms)")
        print()

    # Resumen
    print("=" * 60)
    if failed == 0:
        print(f"  RESULTADO: {passed}/{total} PASS")
    else:
        print(f"  RESULTADO: {passed}/{total} PASS, {failed} FAIL")
    print("=" * 60)
    print()


# ============================================================
# MAIN
# ============================================================

def main():
    parser = argparse.ArgumentParser(description="Simulador de llamadas Bruce W")
    parser.add_argument("--verbose", "-v", action="store_true", help="Mostrar detalle completo")
    parser.add_argument("--escenario", "-e", type=int, help="Ejecutar solo escenario N")
    parser.add_argument("--list", "-l", action="store_true", help="Listar escenarios disponibles")
    args = parser.parse_args()

    if args.list:
        print("\nEscenarios disponibles:")
        for i, e in enumerate(ESCENARIOS):
            bug_str = f" -> espera: {', '.join(e.get('bugs_esperados', []))}" if e.get('bugs_esperados') else ""
            print(f"  {i+1}. {e['nombre']}: {e['descripcion']}{bug_str}")
        print()
        return

    sim = SimuladorLlamada(verbose=args.verbose)

    if args.escenario:
        idx = args.escenario - 1
        if 0 <= idx < len(ESCENARIOS):
            sim.ejecutar_escenario(idx, ESCENARIOS[idx])
        else:
            print(f"Error: escenario {args.escenario} no existe (hay {len(ESCENARIOS)})")
            sys.exit(1)
    else:
        for i, escenario in enumerate(ESCENARIOS):
            sim.ejecutar_escenario(i, escenario)

    imprimir_reporte(sim.resultados, verbose=args.verbose)

    # Exit code
    failed = sum(1 for r in sim.resultados if not r["passed"])
    sys.exit(1 if failed > 0 else 0)


if __name__ == "__main__":
    main()
