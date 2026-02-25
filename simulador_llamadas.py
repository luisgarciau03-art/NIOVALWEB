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
from bug_detector import BugDetector, CallEventTracker

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
        """Corre bug detector rule-based sobre la conversacion."""
        tracker = CallEventTracker(
            call_sid=f"SIM-{resultado['idx']:03d}",
            bruce_id=f"SIMTEST-{resultado['idx']:03d}",
            telefono="0000000000"
        )

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
            resultado["bugs_detectados"] = bugs
        except Exception as e:
            resultado["errores"].append(f"Bug detector error: {e}")

    def _evaluar_resultado(self, resultado):
        """Evalua si el escenario paso o fallo."""
        tipos_detectados = {b["tipo"] for b in resultado["bugs_detectados"]}
        passed = True

        # Verificar bugs esperados esten presentes
        for esperado in resultado["bugs_esperados"]:
            if esperado not in tipos_detectados:
                resultado["errores"].append(
                    f"Bug esperado '{esperado}' NO detectado"
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
        status = "PASS" if r["passed"] else "FAIL"
        icon = "[OK]" if r["passed"] else "[FAIL]"
        tiempo = r["tiempo_ms"]

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
