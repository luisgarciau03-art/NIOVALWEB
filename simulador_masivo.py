#!/usr/bin/env python3
"""
Simulador Masivo de Conversaciones - Bruce W.

Genera y ejecuta 130 escenarios realistas basados en patrones de bugs de produccion.
Pipeline completa: FSM -> Patterns -> GPT (real) -> Post-filters -> Bug Detector.
Auditores triples: Rule-based + GPT eval + Claude Sonnet (modo profundo).

Sin Twilio, sin ElevenLabs, sin Azure Speech. Solo texto.

Uso:
    python simulador_masivo.py                          # Todos (60+ escenarios)
    python simulador_masivo.py --verbose                # Con respuestas completas
    python simulador_masivo.py --category logica_rota   # Solo una categoria
    python simulador_masivo.py --claude                 # + Claude Sonnet auditor
    python simulador_masivo.py --list                   # Listar escenarios
    python simulador_masivo.py --scenario 15            # Solo escenario N
    python simulador_masivo.py --quick                  # Solo 20 escenarios criticos
    python simulador_masivo.py --report bugs_report.json  # Guardar reporte JSON
"""

import os
import sys
import time
import json
import argparse
import threading
from collections import Counter, defaultdict
from datetime import datetime

# FIX: Windows cp1252 no soporta caracteres Unicode
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

from agente_ventas import AgenteVentas
from bug_detector import CallEventTracker, BugDetector, _evaluar_con_gpt


# ============================================================
# ESCENARIOS MASIVOS - Basados en bugs reales de produccion
# ============================================================
# Cada escenario tiene:
#   - id, nombre, categoria (tipo de bug que testea)
#   - contacto: info del negocio simulado
#   - turnos: lista de mensajes del cliente
#   - check_not: palabras que Bruce NO debe decir en ese turno
#   - check_bruce: palabras que Bruce SI debe decir (opcional)
#   - bugs_criticos: tipos de bug que si aparecen = FAIL
#   - critico: True si es de los 20 escenarios --quick

ESCENARIOS = [
    # ================================================================
    # CATEGORIA: GPT_LOGICA_ROTA (pregunta repetida, dato ya dado)
    # Frases reales de produccion: BRUCE2655, BRUCE2640, BRUCE2639, BRUCE2633
    # STT artifacts incluidos donde aplica
    # ================================================================
    {
        "id": 1, "nombre": "Repite pregunta encargado despues de confirmacion clara",
        "categoria": "logica_rota", "critico": True,
        "contacto": {"nombre_negocio": "Ferreteria El Tornillo de Oro", "telefono": "3336381234", "ciudad": "Guadalajara"},
        "turnos": [
            {"cliente": "Bueno?", "check_not": []},
            {"cliente": "Si, yo soy el encargado de compras, digame", "check_not": []},
            {"cliente": "Aja, si, lo escucho", "check_not": ["encargado", "se encontrara"]},
            {"cliente": "Orale pues mandeme el catalogo por WhatsApp", "check_not": ["encargado"]},
            {"cliente": "Es el treinta y tres, treinta y seis, treinta y ocho, doce, treinta y cuatro", "check_not": []},
        ],
        "bugs_criticos": ["GPT_LOGICA_ROTA", "PREGUNTA_REPETIDA"],
    },
    {
        "id": 2, "nombre": "Pide WhatsApp cuando cliente ya esta dictando numero",
        "categoria": "logica_rota", "critico": True,
        "contacto": {"nombre_negocio": "Tornillos y Tuercas del Bajio", "telefono": "4771234502", "ciudad": "Leon"},
        "turnos": [
            {"cliente": "Bueno? Buenas tardes", "check_not": []},
            {"cliente": "Si, yo mero, soy el de compras", "check_not": []},
            {"cliente": "Si, al WhatsApp esta bien", "check_not": []},
            # STT artifact: numero parcial como lo dicta gente real
            {"cliente": "Cuatro siete siete", "check_not": []},
            {"cliente": "Uno dos tres cuatro cinco cero dos", "check_not": ["whatsapp"]},
        ],
        "bugs_criticos": ["GPT_LOGICA_ROTA", "LOOP"],
    },
    {
        "id": 3, "nombre": "Confirma ser encargado 2 veces, Bruce pregunta de nuevo",
        "categoria": "logica_rota", "critico": True,
        "contacto": {"nombre_negocio": "Materiales para Construccion San Jose", "telefono": "5556781003", "ciudad": "CDMX"},
        "turnos": [
            {"cliente": "Bueno?", "check_not": []},
            # STT: eco tipico de Azure - frase repetida
            {"cliente": "Si, si soy el encargado. Si, si soy el encargado de compras.", "check_not": []},
            {"cliente": "Aja, digame pues", "check_not": ["encargado", "se encontrara"]},
            {"cliente": "Mande, que ocupan?", "check_not": ["encargado"]},
        ],
        "bugs_criticos": ["GPT_LOGICA_ROTA", "PREGUNTA_REPETIDA", "LOOP"],
    },
    {
        "id": 4, "nombre": "Contacto dado en mismo turno que confirmacion",
        "categoria": "logica_rota", "critico": True,
        "contacto": {"nombre_negocio": "Ferreteria La Union de Monterrey", "telefono": "8119876504", "ciudad": "Monterrey"},
        "turnos": [
            {"cliente": "Bueno", "check_not": []},
            # Cliente da todo junto - muy comun en produccion
            {"cliente": "Si, yo soy el encargado, oiga mire mandeme el catalogo al WhatsApp al ochenta y uno diecinueve ochenta y siete sesenta y cinco cero cuatro", "check_not": ["proporcionar"]},
            {"cliente": "Si, asi es, correcto", "check_not": ["encargado"]},
        ],
        "bugs_criticos": ["DATO_NEGADO_REINSISTIDO", "PREGUNTA_REPETIDA"],
    },
    {
        "id": 5, "nombre": "Dice 'a sus ordenes' y Bruce re-pregunta encargado",
        "categoria": "logica_rota", "critico": False,
        "contacto": {"nombre_negocio": "Tlapaleria El Sol de Mexico", "telefono": "3339015005", "ciudad": "Guadalajara"},
        "turnos": [
            {"cliente": "Hola, buen dia", "check_not": []},
            {"cliente": "Si, a sus ordenes, yo soy el encargado", "check_not": []},
            {"cliente": "Si, lo escucho, digame", "check_not": ["encargado"]},
            {"cliente": "Ah orale, pues mande por WhatsApp", "check_not": ["encargado"]},
            {"cliente": "Treinta y tres, treinta y nueve, cero uno, cincuenta, cero cinco", "check_not": []},
        ],
        "bugs_criticos": ["GPT_LOGICA_ROTA", "PREGUNTA_REPETIDA"],
    },
    {
        "id": 6, "nombre": "Da correo deletreado, Bruce vuelve a pedir",
        "categoria": "logica_rota", "critico": True,
        "contacto": {"nombre_negocio": "Industrial del Norte SA de CV", "telefono": "8187651006", "ciudad": "Monterrey"},
        "turnos": [
            {"cliente": "Bueno?", "check_not": []},
            {"cliente": "Si, soy el encargado de compras", "check_not": []},
            {"cliente": "Fijese que no manejo WhatsApp", "check_not": []},
            # Email dictado como en produccion real
            {"cliente": "Es compras, c de casa, o, m de mama, p de Pedro, r de Ramon, a, s, arroba industrial punto com punto eme equis", "check_not": []},
            {"cliente": "Correcto, asi es", "check_not": ["correo", "email"]},
        ],
        "bugs_criticos": ["GPT_LOGICA_ROTA", "DATO_NEGADO_REINSISTIDO"],
    },
    {
        "id": 7, "nombre": "Numero en 2 partes con pausa - STT lo corta",
        "categoria": "logica_rota", "critico": False,
        "contacto": {"nombre_negocio": "Cerrajeria y Chapas Express", "telefono": "3312347007", "ciudad": "Guadalajara"},
        "turnos": [
            {"cliente": "Bueno, buenas tardes", "check_not": []},
            {"cliente": "Si soy yo, el mero mero", "check_not": []},
            {"cliente": "Orale, al WhatsApp", "check_not": []},
            # STT corta el numero en 2 transcripciones
            {"cliente": "Treinta y tres, doce", "check_not": []},
            {"cliente": "Treinta y cuatro, setenta, cero siete", "check_not": []},
        ],
        "bugs_criticos": ["GPT_LOGICA_ROTA", "LOOP"],
    },

    # ================================================================
    # CATEGORIA: GPT_CONTEXTO_IGNORADO (ignora contexto del cliente)
    # Frases reales: BRUCE2658, BRUCE2650, BRUCE2643, BRUCE2619, BRUCE2618
    # ================================================================
    {
        "id": 8, "nombre": "Cliente se identifica como encargado al contestar",
        "categoria": "contexto_ignorado", "critico": True,
        "contacto": {"nombre_negocio": "Pinturas y Solventes del Valle", "telefono": "3338901008", "ciudad": "Guadalajara"},
        "turnos": [
            # Real: muchos contestan con cargo incluido
            {"cliente": "Bueno, buen dia, habla el encargado de compras, en que le puedo ayudar?", "check_not": ["encargado", "se encontrara"]},
            {"cliente": "Aja, si digame pues, que me ofrece", "check_not": ["encargado"]},
            {"cliente": "Orale pues mande el catalogo por WhatsApp", "check_not": []},
            {"cliente": "Treinta y tres, treinta y ocho, noventa, diez, cero ocho", "check_not": []},
        ],
        "bugs_criticos": ["GPT_CONTEXTO_IGNORADO", "PREGUNTA_REPETIDA"],
    },
    {
        "id": 9, "nombre": "Cliente participando activo, Bruce asume ausencia",
        "categoria": "contexto_ignorado", "critico": True,
        "contacto": {"nombre_negocio": "Electricos y Plomeria del Centro", "telefono": "3312901009", "ciudad": "Guadalajara"},
        "turnos": [
            {"cliente": "Bueno?", "check_not": []},
            {"cliente": "Si, a sus ordenes, que se le ofrece?", "check_not": []},
            {"cliente": "A ver pues, expliqueme bien que es lo que venden ustedes", "check_not": ["ausente", "no esta", "cuando regresa"]},
            {"cliente": "Ah mire, si me interesa, suena bien", "check_not": []},
            {"cliente": "Si, mandeme la informacion por WhatsApp al treinta y tres doce noventa diez cero nueve", "check_not": []},
        ],
        "bugs_criticos": ["GPT_CONTEXTO_IGNORADO"],
    },
    {
        "id": 10, "nombre": "Dueno contesta - no dice 'encargado' sino 'yo soy el dueno'",
        "categoria": "contexto_ignorado", "critico": False,
        "contacto": {"nombre_negocio": "Ferreteria Don Pedro y Hermanos", "telefono": "4421901010", "ciudad": "Queretaro"},
        "turnos": [
            {"cliente": "Bueno?", "check_not": []},
            {"cliente": "Pues si, yo soy el dueno del changarro, digame", "check_not": ["encargado"]},
            {"cliente": "Aha, a ver pues", "check_not": ["encargado"]},
            {"cliente": "Orale, mandeme por WhatsApp pues", "check_not": []},
            {"cliente": "Cuarenta y cuatro veintiuno noventa diez diez", "check_not": []},
        ],
        "bugs_criticos": ["GPT_CONTEXTO_IGNORADO", "PREGUNTA_REPETIDA"],
    },
    {
        "id": 11, "nombre": "Empleado ofrece pasar recado al patron",
        "categoria": "contexto_ignorado", "critico": False,
        "contacto": {"nombre_negocio": "Herramientas del Bajio SA", "telefono": "4771234511", "ciudad": "Leon"},
        "turnos": [
            {"cliente": "Bueno, buenas tardes", "check_not": []},
            {"cliente": "No, fijese que el patron no esta, pero si gusta yo le paso el recado", "check_not": []},
            {"cliente": "Si, digame que le anoto", "check_not": []},
            {"cliente": "Ah orale, le doy el WhatsApp del jefe, es el cuarenta y siete setenta y uno veintitrece cuarenta y cinco once", "check_not": []},
        ],
        "bugs_criticos": ["GPT_CONTEXTO_IGNORADO"],
    },
    {
        "id": 12, "nombre": "Conmutador transfiere a compras - Bruce repite pitch",
        "categoria": "contexto_ignorado", "critico": True,
        "contacto": {"nombre_negocio": "Grupo Ferretero Nacional SA de CV", "telefono": "5556123012", "ciudad": "CDMX"},
        "turnos": [
            {"cliente": "Grupo Ferretero Nacional, buenas tardes, en que le puedo ayudar", "check_not": []},
            {"cliente": "Le comunico al area de compras, permitame tantito", "check_not": []},
            # Despues de transferencia, Bruce debe dar pitch fresco
            {"cliente": "Si, bueno, soy el encargado de compras, digame", "check_not": ["encargado", "se encontrara"]},
            {"cliente": "A ver, que manejan ustedes", "check_not": ["encargado"]},
            {"cliente": "Mandeme el catalogo al correo compras arroba grupoferretero punto com punto eme equis", "check_not": []},
        ],
        "bugs_criticos": ["GPT_CONTEXTO_IGNORADO", "PITCH_REPETIDO"],
    },

    # ================================================================
    # CATEGORIA: GPT_OPORTUNIDAD_PERDIDA (cliente interesado, Bruce no capitaliza)
    # Frases reales: BRUCE2649, BRUCE2643, BRUCE2650
    # ================================================================
    {
        "id": 13, "nombre": "Cliente pregunta activamente por productos especificos",
        "categoria": "oportunidad_perdida", "critico": True,
        "contacto": {"nombre_negocio": "Ferreteria La Paloma de Occidente", "telefono": "3336501013", "ciudad": "Guadalajara"},
        "turnos": [
            {"cliente": "Bueno?", "check_not": []},
            {"cliente": "Si, soy el encargado de compras, oiga me interesa saber que productos manejan ustedes", "check_not": []},
            {"cliente": "Tienen tornilleria industrial? Tornillo grado ocho y asi?", "check_not": []},
            {"cliente": "Orale si, mandeme el catalogo pues", "check_not": []},
            {"cliente": "Al WhatsApp, treinta y tres, treinta y seis, cincuenta, diez, trece", "check_not": []},
        ],
        "bugs_criticos": ["GPT_OPORTUNIDAD_PERDIDA"],
    },
    {
        "id": 14, "nombre": "Cliente da numero espontaneo sin que Bruce pida",
        "categoria": "oportunidad_perdida", "critico": True,
        "contacto": {"nombre_negocio": "Tlapaleria Los Pinos de Jalisco", "telefono": "3336141014", "ciudad": "Guadalajara"},
        "turnos": [
            {"cliente": "Bueno, buen dia", "check_not": []},
            # Muy comun: cliente ya sabe el rollo y da el dato de una vez
            {"cliente": "Si soy el encargado, mire ya me habian hablado de ustedes, nomás mandeme el catalogo al treinta y tres treinta y seis catorce diez catorce por WhatsApp", "check_not": []},
            {"cliente": "Si, ese mero, por WhatsApp", "check_not": []},
        ],
        "bugs_criticos": ["GPT_OPORTUNIDAD_PERDIDA", "GPT_LOGICA_ROTA"],
    },
    {
        "id": 15, "nombre": "Pregunta a como dan y si hay descuento por mayoreo",
        "categoria": "oportunidad_perdida", "critico": False,
        "contacto": {"nombre_negocio": "Herramientas y Mas de Monterrey", "telefono": "8143215015", "ciudad": "Monterrey"},
        "turnos": [
            {"cliente": "Buen dia", "check_not": []},
            {"cliente": "Si, a sus ordenes", "check_not": []},
            {"cliente": "Y a como dan? Cuanto sale la tornilleria?", "check_not": []},
            {"cliente": "Mmm, y manejan algun descuento por mayoreo? Nosotros compramos bastante", "check_not": []},
            {"cliente": "Orale pues mandeme el catalogo con la lista de precios ahi", "check_not": []},
            {"cliente": "Al ochenta y uno cuarenta y tres veintiuno cincuenta quince por WhatsApp", "check_not": []},
        ],
        "bugs_criticos": ["GPT_OPORTUNIDAD_PERDIDA"],
    },
    {
        "id": 16, "nombre": "Cliente recurrente - ya les habia comprado antes",
        "categoria": "oportunidad_perdida", "critico": False,
        "contacto": {"nombre_negocio": "Materiales para Construccion Puebla", "telefono": "2221234516", "ciudad": "Puebla"},
        "turnos": [
            {"cliente": "Bueno?", "check_not": []},
            {"cliente": "Si soy yo, oiga fijese que ya les habiamos comprado antes, ahi tengo unas facturas de ustedes", "check_not": []},
            {"cliente": "Si, quiero volver a hacer un pedido, ocupo mas material", "check_not": []},
            {"cliente": "Mandeme el catalogo actualizado al WhatsApp pues", "check_not": []},
            {"cliente": "Veintidos veintiuno veintitrés cuarenta y cinco dieciseis", "check_not": []},
        ],
        "bugs_criticos": ["GPT_OPORTUNIDAD_PERDIDA"],
    },

    # ================================================================
    # CATEGORIA: GPT_RESPUESTA_INCOHERENTE (respuesta generica/desconectada)
    # Frases reales: BRUCE2658, BRUCE2640, BRUCE2635, BRUCE2633
    # ================================================================
    {
        "id": 17, "nombre": "Encargado ausente, Bruce responde generico 'Entendido'",
        "categoria": "respuesta_incoherente", "critico": True,
        "contacto": {"nombre_negocio": "Ferreteria Azteca de Guadalajara", "telefono": "3336501017", "ciudad": "Guadalajara"},
        "turnos": [
            {"cliente": "Bueno?", "check_not": []},
            {"cliente": "No, fijese que no esta, ando fueras, salio a comer hace rato", "check_not": []},
            {"cliente": "Pues no se a que hora regresa, la verdad", "check_not": []},
        ],
        "bugs_criticos": ["GPT_RESPUESTA_INCOHERENTE", "LOOP"],
    },
    {
        "id": 18, "nombre": "No es ferreteria - giro equivocado, Bruce sigue ofreciendo",
        "categoria": "respuesta_incoherente", "critico": True,
        "contacto": {"nombre_negocio": "Consultorio Dental Garcia", "telefono": "3336181018", "ciudad": "Guadalajara"},
        "turnos": [
            {"cliente": "Bueno?", "check_not": []},
            # Real: gente confundida porque no es el giro correcto
            {"cliente": "No oiga, aqui no es ninguna ferreteria, esto es un consultorio dental, se equivoco de numero", "check_not": ["catalogo", "producto", "ferreteria", "herramienta"]},
        ],
        "bugs_criticos": ["GPT_RESPUESTA_INCOHERENTE", "GPT_LOGICA_ROTA"],
    },
    {
        "id": 19, "nombre": "Da correo sin que pidan pero Bruce no procesa",
        "categoria": "respuesta_incoherente", "critico": False,
        "contacto": {"nombre_negocio": "Industrial del Pacifico SA", "telefono": "3221234519", "ciudad": "Puerto Vallarta"},
        "turnos": [
            {"cliente": "Buenas tardes", "check_not": []},
            {"cliente": "Si, soy el encargado", "check_not": []},
            # Real: da correo junto con rechazo de WhatsApp
            {"cliente": "No tengo WhatsApp oiga, pero mi correo es ventas arroba industrialpacifico punto com", "check_not": ["whatsapp"]},
            {"cliente": "Si, asi es, ventas arroba industrial pacifico punto com", "check_not": []},
        ],
        "bugs_criticos": ["GPT_RESPUESTA_INCOHERENTE", "DATO_SIN_RESPUESTA"],
    },
    {
        "id": 20, "nombre": "Cliente explica su giro especifico, Bruce ignora contexto",
        "categoria": "respuesta_incoherente", "critico": False,
        "contacto": {"nombre_negocio": "Plomeria y Electricidad del Sur", "telefono": "3339015020", "ciudad": "Guadalajara"},
        "turnos": [
            {"cliente": "Buen dia", "check_not": []},
            {"cliente": "Pues si, yo soy el encargado, nosotros somos plomeros mire, manejamos puro material de plomeria y tuberia", "check_not": []},
            {"cliente": "Eso mero, lo que ocupamos es herramienta para plomeria, llaves, tubos, conexiones", "check_not": []},
            {"cliente": "Pues mandeme el catalogo al treinta y tres treinta y nueve cero uno cincuenta veinte", "check_not": []},
        ],
        "bugs_criticos": ["GPT_RESPUESTA_INCOHERENTE"],
    },

    # ================================================================
    # CATEGORIA: GPT_RESPUESTA_INCORRECTA (info falsa, genero, ubicacion)
    # Frases reales: BRUCE2635, BRUCE2634, BRUCE2627
    # ================================================================
    {
        "id": 21, "nombre": "Verificar genero correcto (Bruce es hombre)",
        "categoria": "respuesta_incorrecta", "critico": True,
        "contacto": {"nombre_negocio": "Ferreteria El Clavo Dorado", "telefono": "3336501021", "ciudad": "Guadalajara"},
        "turnos": [
            {"cliente": "Bueno, buenas tardes", "check_not": ["senorita", "senora"]},
            {"cliente": "Si, soy el encargado de compras", "check_not": ["senorita", "senora"]},
            {"cliente": "Orale, mande por WhatsApp el catalogo", "check_not": []},
            {"cliente": "Treinta y tres treinta y seis cincuenta diez veintiuno", "check_not": []},
        ],
        "bugs_criticos": ["GPT_RESPUESTA_INCORRECTA"],
    },
    {
        "id": 22, "nombre": "Pregunta de ubicacion - Bruce responde Guadalajara correctamente",
        "categoria": "respuesta_incorrecta", "critico": True,
        "contacto": {"nombre_negocio": "Ferreteria del Norte Monterrey", "telefono": "8119876022", "ciudad": "Monterrey"},
        "turnos": [
            {"cliente": "Bueno?", "check_not": []},
            {"cliente": "Si soy, oiga de donde me hablan?", "check_not": []},
            {"cliente": "Y donde estan ubicados ustedes?", "check_not": []},
            {"cliente": "Ah orale, mande el catalogo al WhatsApp ochenta y uno diecinueve ochenta y siete sesenta veintidos", "check_not": []},
        ],
        "bugs_criticos": ["GPT_RESPUESTA_INCORRECTA"],
    },
    {
        "id": 23, "nombre": "Email deletreado con mnemotecnicos - no confundir",
        "categoria": "respuesta_incorrecta", "critico": False,
        "contacto": {"nombre_negocio": "Tornillos Premium de Mexico", "telefono": "3336501023", "ciudad": "Guadalajara"},
        "turnos": [
            {"cliente": "Bueno", "check_not": []},
            {"cliente": "Si soy el de compras", "check_not": []},
            {"cliente": "Fijese que no tengo WhatsApp", "check_not": []},
            # Real: deletreo con mnemotecnicos como en produccion
            {"cliente": "El correo es pe de Pedro, ere de Ramon, e de elefante, eme de mama, i latina, u de uva, eme de mama, arroba gmail punto com", "check_not": []},
        ],
        "bugs_criticos": ["GPT_RESPUESTA_INCORRECTA"],
    },

    # ================================================================
    # CATEGORIA: SALUDO_FALTANTE (Bruce no saluda en primer turno)
    # Frases reales: BRUCE2643, BRUCE2626, BRUCE2631
    # ================================================================
    {
        "id": 24, "nombre": "Saludo basico - cliente contesta 'Bueno?'",
        "categoria": "saludo_faltante", "critico": True,
        "contacto": {"nombre_negocio": "Ferreteria El Martillo de Plata", "telefono": "3336501024", "ciudad": "Guadalajara"},
        "turnos": [
            {"cliente": "Bueno?", "check_not": []},
            {"cliente": "Si, digame", "check_not": []},
            {"cliente": "No gracias, ahorita no me interesa", "check_not": []},
        ],
        "bugs_criticos": ["SALUDO_FALTANTE"],
    },
    {
        "id": 25, "nombre": "Saludo post-conmutador - IVR contesta primero",
        "categoria": "saludo_faltante", "critico": False,
        "contacto": {"nombre_negocio": "Corporativo Industrial Mexicano", "telefono": "5556123025", "ciudad": "CDMX"},
        "turnos": [
            {"cliente": "Corporativo Industrial, buenas tardes, en que le puedo ayudar", "check_not": []},
            {"cliente": "Permitame tantito, le comunico al area de compras", "check_not": []},
            {"cliente": "Si bueno, soy el encargado de compras", "check_not": []},
            {"cliente": "Si, al WhatsApp cincuenta y cinco cincuenta y seis doce treinta veinticinco", "check_not": []},
        ],
        "bugs_criticos": ["SALUDO_FALTANTE"],
    },

    # ================================================================
    # CATEGORIA: TONO_INADECUADO (insistente despues de rechazo)
    # Frases reales: BRUCE2621, BRUCE2611
    # ================================================================
    {
        "id": 26, "nombre": "Rechazo cortante - Bruce no debe insistir",
        "categoria": "tono_inadecuado", "critico": True,
        "contacto": {"nombre_negocio": "Ferreteria El Rechazo Firme", "telefono": "3336501026", "ciudad": "Guadalajara"},
        "turnos": [
            {"cliente": "Bueno?", "check_not": []},
            {"cliente": "No gracias senor, no nos interesa, ya tenemos quien nos surte, gracias", "check_not": []},
        ],
        "bugs_criticos": ["GPT_TONO_INADECUADO", "LOOP"],
    },
    {
        "id": 27, "nombre": "Cliente harto por llamadas frecuentes",
        "categoria": "tono_inadecuado", "critico": True,
        "contacto": {"nombre_negocio": "Tlapaleria Los Hartos", "telefono": "3336501027", "ciudad": "Guadalajara"},
        "turnos": [
            {"cliente": "Bueno", "check_not": []},
            # Real: queja agresiva de produccion
            {"cliente": "Oiga ya dejenos de estar llamando, a cada rato nos marcan, ya nos tienen hartos con sus llamadas, ya por favor", "check_not": ["catalogo", "producto", "whatsapp"]},
        ],
        "bugs_criticos": ["GPT_TONO_INADECUADO", "LOOP", "PREGUNTA_REPETIDA"],
    },
    {
        "id": 28, "nombre": "Tono profesional - sin modismos vulgares",
        "categoria": "tono_inadecuado", "critico": False,
        "contacto": {"nombre_negocio": "Electricos Profesionales CDMX", "telefono": "5556123028", "ciudad": "CDMX"},
        "turnos": [
            {"cliente": "Buen dia", "check_not": []},
            {"cliente": "Si soy yo, a sus ordenes", "check_not": ["bronca", "chido", "neta", "wey"]},
            {"cliente": "Orale pues mandeme al WhatsApp", "check_not": ["bronca", "chido", "neta", "wey"]},
            {"cliente": "Cincuenta y cinco, cincuenta y seis, doce, treinta, veintiocho", "check_not": []},
        ],
        "bugs_criticos": ["GPT_TONO_INADECUADO"],
    },

    # ================================================================
    # CATEGORIA: CLIENTE_HABLA_ULTIMO (Bruce no responde al final)
    # Frases reales: BRUCE2621, BRUCE2610
    # ================================================================
    {
        "id": 29, "nombre": "Cliente agradece al final - Bruce debe despedirse",
        "categoria": "cliente_habla_ultimo", "critico": True,
        "contacto": {"nombre_negocio": "Ferreteria Agradecida", "telefono": "3336501029", "ciudad": "Guadalajara"},
        "turnos": [
            {"cliente": "Bueno?", "check_not": []},
            {"cliente": "Si soy el encargado", "check_not": []},
            {"cliente": "Si, al WhatsApp", "check_not": []},
            {"cliente": "Treinta y tres treinta y seis cincuenta diez veintinueve", "check_not": []},
            # Real: cliente siempre dice gracias al final
            {"cliente": "Ah bueno, pues muchas gracias, ahi lo checamos", "check_not": []},
        ],
        "bugs_criticos": ["CLIENTE_HABLA_ULTIMO"],
    },
    {
        "id": 30, "nombre": "Pregunta final del cliente sin respuesta",
        "categoria": "cliente_habla_ultimo", "critico": False,
        "contacto": {"nombre_negocio": "Materiales La Ultima Pregunta", "telefono": "3336501030", "ciudad": "Guadalajara"},
        "turnos": [
            {"cliente": "Bueno?", "check_not": []},
            {"cliente": "Si, soy yo, el de compras", "check_not": []},
            {"cliente": "Mandeme por WhatsApp al treinta y tres treinta y seis cincuenta diez treinta", "check_not": []},
            {"cliente": "Oiga y cada cuando manejan ustedes promociones?", "check_not": []},
        ],
        "bugs_criticos": ["CLIENTE_HABLA_ULTIMO"],
    },

    # ================================================================
    # CATEGORIA: DATO_SIN_RESPUESTA (dato dado pero Bruce no confirma)
    # Frases reales: BRUCE2608
    # ================================================================
    {
        "id": 31, "nombre": "Email dado claro - Bruce debe confirmar",
        "categoria": "dato_sin_respuesta", "critico": True,
        "contacto": {"nombre_negocio": "Industrial Proveetiza SA", "telefono": "3336501031", "ciudad": "Guadalajara"},
        "turnos": [
            {"cliente": "Bueno?", "check_not": []},
            {"cliente": "Si, soy el encargado de compras", "check_not": []},
            {"cliente": "Fijese que no manejo WhatsApp", "check_not": []},
            # STT real: correo con arroba/punto
            {"cliente": "Mandeme al correo proveetiza arroba gmail punto com", "check_not": []},
        ],
        "bugs_criticos": ["DATO_SIN_RESPUESTA"],
    },
    {
        "id": 32, "nombre": "Numero dado completo - Bruce no debe re-pedir",
        "categoria": "dato_sin_respuesta", "critico": True,
        "contacto": {"nombre_negocio": "Herramientas y Tornillos Contacto", "telefono": "3336501032", "ciudad": "Guadalajara"},
        "turnos": [
            {"cliente": "Buen dia", "check_not": []},
            {"cliente": "Si soy yo, el mero encargado de compras", "check_not": []},
            {"cliente": "Orale pues, mandeme al WhatsApp", "check_not": []},
            {"cliente": "Es el treinta y tres, treinta y seis, cincuenta, diez, treinta y dos", "check_not": []},
            {"cliente": "Si, correcto, ese mero", "check_not": ["numero", "telefono", "whatsapp"]},
        ],
        "bugs_criticos": ["DATO_SIN_RESPUESTA", "PREGUNTA_REPETIDA"],
    },

    # ================================================================
    # CATEGORIA: CANAL_RECHAZADO (WhatsApp/correo negado, Bruce re-pide)
    # ================================================================
    {
        "id": 33, "nombre": "WhatsApp rechazado -> correo rechazado -> telefono fijo",
        "categoria": "canal_rechazado", "critico": True,
        "contacto": {"nombre_negocio": "Tlapaleria Don Chucho", "telefono": "3336501033", "ciudad": "Guadalajara"},
        "turnos": [
            {"cliente": "Bueno?", "check_not": []},
            {"cliente": "Si, yo soy el encargado de compras, a sus ordenes", "check_not": []},
            {"cliente": "Fijese que no tengo WhatsApp, no lo manejo", "check_not": []},
            {"cliente": "No, tampoco tengo correo electronico, nada de eso", "check_not": ["whatsapp"]},
            {"cliente": "Pues el telefono fijo es este mismo, treinta y tres treinta y seis cincuenta diez treinta y tres", "check_not": ["whatsapp", "correo"]},
        ],
        "bugs_criticos": ["DATO_NEGADO_REINSISTIDO", "LOOP"],
    },
    {
        "id": 34, "nombre": "Solo WhatsApp rechazado -> ofrecer correo",
        "categoria": "canal_rechazado", "critico": True,
        "contacto": {"nombre_negocio": "Ferreteria Sin WA", "telefono": "3312345034", "ciudad": "Guadalajara"},
        "turnos": [
            {"cliente": "Bueno, buen dia", "check_not": []},
            {"cliente": "Si, yo mero soy el encargado", "check_not": []},
            {"cliente": "No manejo WhatsApp", "check_not": []},
            {"cliente": "Si, el correo es ferreteria34@gmail.com", "check_not": ["whatsapp"]},
            {"cliente": "Si, correcto, gracias", "check_not": ["whatsapp"]},
        ],
        "bugs_criticos": ["DATO_NEGADO_REINSISTIDO"],
    },
    {
        "id": 35, "nombre": "Todos canales rechazados -> ofrecer numero Bruce",
        "categoria": "canal_rechazado", "critico": False,
        "contacto": {"nombre_negocio": "Ferreteria Antigua", "telefono": "3312345035", "ciudad": "Guadalajara"},
        "turnos": [
            {"cliente": "Bueno", "check_not": []},
            {"cliente": "Si soy el encargado pero no manejo WhatsApp", "check_not": []},
            {"cliente": "No, tampoco tengo correo", "check_not": ["whatsapp"]},
            {"cliente": "No, solo el telefono fijo del negocio", "check_not": ["whatsapp", "correo"]},
        ],
        "bugs_criticos": ["DATO_NEGADO_REINSISTIDO", "LOOP"],
    },

    # ================================================================
    # CATEGORIA: CALLBACK (cliente pide que llamen despues)
    # ================================================================
    {
        "id": 36, "nombre": "Callback con hora especifica: a las 4",
        "categoria": "callback", "critico": True,
        "contacto": {"nombre_negocio": "Ferreteria Ocupada", "telefono": "3312345036", "ciudad": "Guadalajara"},
        "turnos": [
            {"cliente": "Bueno?", "check_not": []},
            {"cliente": "Oiga fijese que ahorita ando bien ocupado, puede marcarme despues de las cuatro de la tarde?", "check_not": []},
        ],
        "bugs_criticos": ["LOOP", "PREGUNTA_REPETIDA"],
    },
    {
        "id": 37, "nombre": "Callback relativo: en una hora",
        "categoria": "callback", "critico": True,
        "contacto": {"nombre_negocio": "Materiales Ocupados", "telefono": "3312345037", "ciudad": "Guadalajara"},
        "turnos": [
            {"cliente": "Bueno, buen dia", "check_not": []},
            {"cliente": "Si mire, ahorita no puedo atenderle, marqueme en una hora por favor", "check_not": []},
        ],
        "bugs_criticos": ["LOOP", "GPT_LOGICA_ROTA"],
    },
    {
        "id": 38, "nombre": "Callback: encargado viene mas tarde sin hora",
        "categoria": "callback", "critico": False,
        "contacto": {"nombre_negocio": "Tlapaleria Esperame", "telefono": "3312345038", "ciudad": "Guadalajara"},
        "turnos": [
            {"cliente": "Bueno", "check_not": []},
            {"cliente": "No, no esta el encargado, viene mas tardecito", "check_not": []},
            {"cliente": "Pues no se, la verdad no se a que hora llega", "check_not": []},
        ],
        "bugs_criticos": ["LOOP"],
    },
    {
        "id": 39, "nombre": "Callback despues de pitch: 'marqueme por ahi de las 6'",
        "categoria": "callback", "critico": False,
        "contacto": {"nombre_negocio": "Ferreteria Las Seis", "telefono": "3312345039", "ciudad": "Guadalajara"},
        "turnos": [
            {"cliente": "Bueno", "check_not": []},
            {"cliente": "Si soy yo", "check_not": []},
            {"cliente": "Mire ahorita estoy atendiendo a un cliente, si gusta hablar por ahi de las seis de la tarde", "check_not": []},
        ],
        "bugs_criticos": ["LOOP", "PREGUNTA_REPETIDA"],
    },

    # ================================================================
    # CATEGORIA: RECHAZO (no interes, ya tiene proveedor, etc.)
    # ================================================================
    {
        "id": 40, "nombre": "Rechazo inmediato: no me interesa",
        "categoria": "rechazo", "critico": True,
        "contacto": {"nombre_negocio": "Ferreteria Rechazo", "telefono": "3312345040", "ciudad": "Guadalajara"},
        "turnos": [
            {"cliente": "Bueno", "check_not": []},
            {"cliente": "No gracias senor, no me interesa, gracias", "check_not": []},
        ],
        "bugs_criticos": ["LOOP", "PREGUNTA_REPETIDA"],
    },
    {
        "id": 41, "nombre": "Ya tengo proveedor, estamos surtidos",
        "categoria": "rechazo", "critico": True,
        "contacto": {"nombre_negocio": "Tornillos Surtidos", "telefono": "3312345041", "ciudad": "Guadalajara"},
        "turnos": [
            {"cliente": "Bueno", "check_not": []},
            {"cliente": "Si, soy el encargado", "check_not": []},
            {"cliente": "No gracias, ya tenemos quien nos surte, ya estamos bien surtidos, gracias de todas formas", "check_not": []},
        ],
        "bugs_criticos": ["LOOP", "PREGUNTA_REPETIDA"],
    },
    {
        "id": 42, "nombre": "No es ferreteria / giro equivocado",
        "categoria": "rechazo", "critico": True,
        "contacto": {"nombre_negocio": "Restaurante La Cocina", "telefono": "3312345042", "ciudad": "Guadalajara"},
        "turnos": [
            {"cliente": "Bueno", "check_not": []},
            {"cliente": "No oiga, aqui es un restaurante, no es ninguna ferreteria, se equivoco", "check_not": ["catalogo", "producto"]},
        ],
        "bugs_criticos": ["GPT_LOGICA_ROTA", "LOOP"],
    },
    {
        "id": 43, "nombre": "No hacemos compras / area equivocada",
        "categoria": "rechazo", "critico": False,
        "contacto": {"nombre_negocio": "Distribuidora Sin Compras", "telefono": "5512345043", "ciudad": "CDMX"},
        "turnos": [
            {"cliente": "Bueno", "check_not": []},
            {"cliente": "No mire, aqui no hacemos ningun tipo de compra, nosotros nomas vendemos, no compramos", "check_not": ["catalogo"]},
        ],
        "bugs_criticos": ["GPT_LOGICA_ROTA", "LOOP"],
    },
    {
        "id": 44, "nombre": "Numero equivocado",
        "categoria": "rechazo", "critico": False,
        "contacto": {"nombre_negocio": "Electrica Fantasma", "telefono": "3312345044", "ciudad": "Guadalajara"},
        "turnos": [
            {"cliente": "Bueno", "check_not": []},
            {"cliente": "No senor, se equivoco de numero, aqui es una casa particular, no es ningun negocio", "check_not": ["catalogo", "whatsapp"]},
        ],
        "bugs_criticos": ["LOOP", "PREGUNTA_REPETIDA"],
    },

    # ================================================================
    # CATEGORIA: TRANSFERENCIA (le paso, un momento, le comunico)
    # ================================================================
    {
        "id": 45, "nombre": "Transfer simple: un momento le paso",
        "categoria": "transferencia", "critico": True,
        "contacto": {"nombre_negocio": "Ferreteria Transfer", "telefono": "3312345045", "ciudad": "Guadalajara"},
        "turnos": [
            {"cliente": "Bueno, buen dia", "check_not": []},
            {"cliente": "Un momentito, le paso al encargado de compras", "check_not": []},
            {"cliente": "Si bueno, soy el encargado, digame que se le ofrece", "check_not": []},
            {"cliente": "Orale, si mandeme por WhatsApp, treinta y tres doce treinta y cuatro cincuenta cuarenta y cinco", "check_not": []},
        ],
        "bugs_criticos": ["PITCH_REPETIDO", "PREGUNTA_REPETIDA"],
    },
    {
        "id": 46, "nombre": "Transfer: 'permitame' en medio de dictado",
        "categoria": "transferencia", "critico": False,
        "contacto": {"nombre_negocio": "Industrial Transfer", "telefono": "3312345046", "ciudad": "Guadalajara"},
        "turnos": [
            {"cliente": "Bueno", "check_not": []},
            {"cliente": "Si soy yo", "check_not": []},
            {"cliente": "Al WhatsApp", "check_not": []},
            {"cliente": "33 12", "check_not": []},
            {"cliente": "Permitame un momento", "check_not": []},
            {"cliente": "34 50 46", "check_not": []},
        ],
        "bugs_criticos": ["LOOP"],
    },
    {
        "id": 47, "nombre": "Transfer a area de compras desde conmutador",
        "categoria": "transferencia", "critico": False,
        "contacto": {"nombre_negocio": "Grupo Corporativo MX", "telefono": "5512345047", "ciudad": "CDMX"},
        "turnos": [
            {"cliente": "Grupo Corporativo, buen dia, en que le puedo ayudar", "check_not": []},
            {"cliente": "Le comunico al area de compras, un momento", "check_not": []},
            {"cliente": "Hola si, soy el encargado de compras", "check_not": []},
            {"cliente": "Si me interesa, mandeme catalogo", "check_not": []},
            {"cliente": "Al correo compras@grupocorp.mx", "check_not": []},
        ],
        "bugs_criticos": ["PITCH_REPETIDO"],
    },

    # ================================================================
    # CATEGORIA: FLUJO_COMPLETO (flujos exitosos de referencia)
    # ================================================================
    {
        "id": 48, "nombre": "Flujo perfecto: saludo -> encargado -> WhatsApp -> numero",
        "categoria": "flujo_completo", "critico": True,
        "contacto": {"nombre_negocio": "Ferreteria Exitosa", "telefono": "3312345048", "ciudad": "Guadalajara"},
        "turnos": [
            {"cliente": "Buen dia", "check_not": []},
            {"cliente": "Si, yo soy el encargado", "check_not": []},
            {"cliente": "Claro, al WhatsApp", "check_not": []},
            {"cliente": "Es el 33 12 34 50 48", "check_not": []},
            {"cliente": "Si, esta bien, gracias", "check_not": []},
        ],
        "bugs_criticos": [],
    },
    {
        "id": 49, "nombre": "Flujo largo con preguntas: 8+ turnos sin bugs",
        "categoria": "flujo_completo", "critico": False,
        "contacto": {"nombre_negocio": "Mega Ferreteria Plus", "telefono": "3312345049", "ciudad": "Guadalajara"},
        "turnos": [
            {"cliente": "Bueno, buen dia", "check_not": []},
            {"cliente": "Si, soy yo el encargado", "check_not": []},
            {"cliente": "Que tipo de productos manejan?", "check_not": []},
            {"cliente": "Y a que precios?", "check_not": []},
            {"cliente": "Manejan marca Truper?", "check_not": []},
            {"cliente": "Tienen descuento por mayoreo?", "check_not": []},
            {"cliente": "Ok, mandeme el catalogo por WhatsApp", "check_not": []},
            {"cliente": "33 12 34 50 49", "check_not": []},
            {"cliente": "Si, correcto, muchas gracias", "check_not": []},
        ],
        "bugs_criticos": [],
    },
    {
        "id": 50, "nombre": "Flujo por correo: WhatsApp rechazado, correo exitoso",
        "categoria": "flujo_completo", "critico": False,
        "contacto": {"nombre_negocio": "Distribuidora por Email", "telefono": "3312345050", "ciudad": "Guadalajara"},
        "turnos": [
            {"cliente": "Bueno", "check_not": []},
            {"cliente": "Si, soy el encargado", "check_not": []},
            {"cliente": "No manejo WhatsApp", "check_not": []},
            {"cliente": "Si, mi correo es distribuidora50@gmail.com", "check_not": ["whatsapp"]},
            {"cliente": "Si, correcto, gracias", "check_not": ["whatsapp"]},
        ],
        "bugs_criticos": [],
    },

    # ================================================================
    # CATEGORIA: STT_GARBLED (texto distorsionado por STT)
    # ================================================================
    {
        "id": 51, "nombre": "STT: Texto duplicado en frase",
        "categoria": "stt_garbled", "critico": False,
        "contacto": {"nombre_negocio": "Ferreteria STT1", "telefono": "3312345051", "ciudad": "Guadalajara"},
        "turnos": [
            {"cliente": "Hola buen dia. Que dice? Hola buen dia.", "check_not": []},
            {"cliente": "Si soy el encargado. Si soy el encargado de compras.", "check_not": []},
            {"cliente": "Al WhatsApp por favor. Al WhatsApp.", "check_not": []},
            {"cliente": "Es el 33 12 34 50 51", "check_not": []},
        ],
        "bugs_criticos": ["LOOP", "PREGUNTA_REPETIDA"],
    },
    {
        "id": 52, "nombre": "STT: Palabras ilegibles mezcladas con intento",
        "categoria": "stt_garbled", "critico": False,
        "contacto": {"nombre_negocio": "Tlapaleria STT2", "telefono": "3312345052", "ciudad": "Guadalajara"},
        "turnos": [
            {"cliente": "Bueno si digame", "check_not": []},
            {"cliente": "Estan en sobra de comida, estan en sobra de comida, marque mas tarde", "check_not": []},
        ],
        "bugs_criticos": ["LOOP", "GPT_LOGICA_ROTA"],
    },

    # ================================================================
    # CATEGORIA: ENCARGADO_AUSENTE (variaciones)
    # ================================================================
    {
        "id": 53, "nombre": "Encargado salio, empleado no sabe hora",
        "categoria": "encargado_ausente", "critico": True,
        "contacto": {"nombre_negocio": "Ferreteria Ausente", "telefono": "3312345053", "ciudad": "Guadalajara"},
        "turnos": [
            {"cliente": "Bueno", "check_not": []},
            {"cliente": "No, fijese que no esta, anda fueras, salio a comer hace rato", "check_not": []},
            {"cliente": "Pues no sabria decirle a que hora llega, la verdad", "check_not": []},
        ],
        "bugs_criticos": ["LOOP"],
    },
    {
        "id": 54, "nombre": "Encargado de vacaciones",
        "categoria": "encargado_ausente", "critico": False,
        "contacto": {"nombre_negocio": "Materiales Vacaciones", "telefono": "3312345054", "ciudad": "Guadalajara"},
        "turnos": [
            {"cliente": "Bueno, buen dia", "check_not": []},
            {"cliente": "No, el patron esta de vacaciones, regresa hasta la proxima semana, si gusta marcar el lunes", "check_not": []},
        ],
        "bugs_criticos": ["LOOP"],
    },
    {
        "id": 55, "nombre": "Encargado enfermo",
        "categoria": "encargado_ausente", "critico": False,
        "contacto": {"nombre_negocio": "Herramientas Enfermo", "telefono": "3312345055", "ciudad": "Guadalajara"},
        "turnos": [
            {"cliente": "Bueno", "check_not": []},
            {"cliente": "No, se reporto enfermo hoy, no viene", "check_not": []},
            {"cliente": "No, no se cuando regresa la verdad, a ver si manana ya viene", "check_not": []},
        ],
        "bugs_criticos": ["LOOP"],
    },

    # ================================================================
    # CATEGORIA: CONFIRMACIONES_AMBIGUAS (orale, mhm, aha, etc.)
    # ================================================================
    {
        "id": 56, "nombre": "'Orale' como confirmacion",
        "categoria": "confirmaciones", "critico": False,
        "contacto": {"nombre_negocio": "Ferreteria Orale", "telefono": "3312345056", "ciudad": "Guadalajara"},
        "turnos": [
            {"cliente": "Bueno", "check_not": []},
            {"cliente": "Orale", "check_not": []},
            {"cliente": "Si soy yo", "check_not": []},
            {"cliente": "Orale, pues mandame el catalogo por WhatsApp", "check_not": []},
            {"cliente": "33 12 34 50 56", "check_not": []},
        ],
        "bugs_criticos": ["LOOP"],
    },
    {
        "id": 57, "nombre": "'Mhm' y 'aha' como confirmaciones",
        "categoria": "confirmaciones", "critico": False,
        "contacto": {"nombre_negocio": "Tlapaleria Mhm", "telefono": "3312345057", "ciudad": "Guadalajara"},
        "turnos": [
            {"cliente": "Bueno", "check_not": []},
            {"cliente": "Aha", "check_not": []},
            {"cliente": "Mhm, si soy yo", "check_not": []},
            {"cliente": "Aha, al WhatsApp", "check_not": []},
            {"cliente": "33 12 34 50 57", "check_not": []},
        ],
        "bugs_criticos": ["LOOP"],
    },

    # ================================================================
    # CATEGORIA: WHAT_OFFER (que venden, que ofrecen)
    # ================================================================
    {
        "id": 58, "nombre": "Pregunta repetida: que venden (2 veces)",
        "categoria": "what_offer", "critico": True,
        "contacto": {"nombre_negocio": "Ferreteria Curiosa", "telefono": "3312345058", "ciudad": "Guadalajara"},
        "turnos": [
            {"cliente": "Bueno", "check_not": []},
            {"cliente": "Si soy yo, y que es lo que venden?", "check_not": []},
            {"cliente": "Si pero que tipo de herramientas exactamente?", "check_not": []},
            {"cliente": "Ok, mandeme por WhatsApp el catalogo 33 12 34 50 58", "check_not": []},
        ],
        "bugs_criticos": ["LOOP", "PREGUNTA_REPETIDA"],
    },
    {
        "id": 59, "nombre": "Pregunta ubicacion + que ofrecen",
        "categoria": "what_offer", "critico": False,
        "contacto": {"nombre_negocio": "Ferreteria Ubicacion", "telefono": "3312345059", "ciudad": "Guadalajara"},
        "turnos": [
            {"cliente": "Bueno, buen dia", "check_not": []},
            {"cliente": "Si, soy el encargado, de donde hablan?", "check_not": []},
            {"cliente": "Y donde estan ubicados?", "check_not": []},
            {"cliente": "Ok, mandeme catalogo al WhatsApp 33 12 34 50 59", "check_not": []},
        ],
        "bugs_criticos": ["LOOP"],
    },

    # ================================================================
    # CATEGORIA: CONTACTO_INVERTIDO (cliente pide numero de Bruce)
    # ================================================================
    {
        "id": 60, "nombre": "Cliente pide numero de Bruce para contactar",
        "categoria": "contacto_invertido", "critico": True,
        "contacto": {"nombre_negocio": "Ferreteria Dame Tu Numero", "telefono": "3312345060", "ciudad": "Guadalajara"},
        "turnos": [
            {"cliente": "Bueno", "check_not": []},
            {"cliente": "Si soy el encargado, mire mejor deme su numero de telefono y yo le marco cuando tenga tiempo", "check_not": []},
        ],
        "bugs_criticos": ["LOOP", "PREGUNTA_REPETIDA"],
    },
    {
        "id": 61, "nombre": "Cliente pide que Bruce mande WhatsApp primero",
        "categoria": "contacto_invertido", "critico": False,
        "contacto": {"nombre_negocio": "Tlapaleria Mandame WA", "telefono": "3312345061", "ciudad": "Guadalajara"},
        "turnos": [
            {"cliente": "Bueno, buen dia", "check_not": []},
            {"cliente": "Si, soy el encargado, oiga mejor mandeme usted un WhatsApp para yo tener su numero guardado", "check_not": []},
        ],
        "bugs_criticos": ["LOOP"],
    },

    # ================================================================
    # CATEGORIA: BUZON_VOZ / IVR
    # ================================================================
    {
        "id": 62, "nombre": "Buzon de voz: 'la persona con la que intentas comunicarte'",
        "categoria": "buzon_ivr", "critico": False,
        "contacto": {"nombre_negocio": "Negocio Buzon", "telefono": "3312345062", "ciudad": "Guadalajara"},
        "turnos": [
            {"cliente": "La persona con la que intentas comunicarte no esta disponible en este momento, por favor deja tu mensaje despues del tono", "check_not": []},
        ],
        "bugs_criticos": ["LOOP", "PREGUNTA_REPETIDA"],
    },
    {
        "id": 63, "nombre": "IVR: menu automatico con opciones",
        "categoria": "buzon_ivr", "critico": False,
        "contacto": {"nombre_negocio": "Corporativo IVR", "telefono": "5512345063", "ciudad": "CDMX"},
        "turnos": [
            {"cliente": "Bienvenido a Corporativo, marque uno para ventas, dos para compras, tres para otro departamento", "check_not": []},
        ],
        "bugs_criticos": ["LOOP"],
    },

    # ================================================================
    # CATEGORIA: QUEJA (reclamo sobre producto/servicio)
    # ================================================================
    {
        "id": 64, "nombre": "Queja sobre llamadas frecuentes",
        "categoria": "queja", "critico": True,
        "contacto": {"nombre_negocio": "Ferreteria Quejona", "telefono": "3312345064", "ciudad": "Guadalajara"},
        "turnos": [
            {"cliente": "Bueno", "check_not": []},
            {"cliente": "Oiga ya dejen de estar marcando, a cada rato nos estan llamando, ya por favor, ya no queremos que nos llamen", "check_not": ["catalogo", "producto", "whatsapp"]},
        ],
        "bugs_criticos": ["LOOP", "GPT_TONO_INADECUADO"],
    },
    {
        "id": 65, "nombre": "Tercera persona: 'ya le dijeron que no'",
        "categoria": "queja", "critico": False,
        "contacto": {"nombre_negocio": "Materiales Ya Dijeron", "telefono": "3312345065", "ciudad": "Guadalajara"},
        "turnos": [
            {"cliente": "Bueno", "check_not": []},
            {"cliente": "Mire, el patron dice que ya le dijeron que no, que ya no le esten llamando por favor", "check_not": ["catalogo", "whatsapp"]},
        ],
        "bugs_criticos": ["LOOP", "GPT_TONO_INADECUADO"],
    },
    # ================================================================
    # ESCENARIOS 66-130: Variaciones ampliadas (FIX 906)
    # ================================================================
    # --- LOGICA_ROTA variaciones ---
    {
        "id": 66, "nombre": "Pide correo 2 veces seguidas sin escuchar respuesta",
        "categoria": "logica_rota", "critico": True,
        "contacto": {"nombre_negocio": "Cerrajeria El Llavero", "telefono": "8112340066", "ciudad": "Monterrey"},
        "turnos": [
            {"cliente": "Bueno?", "check_not": []},
            {"cliente": "Si yo mero, mande la info a mi correo", "check_not": []},
            {"cliente": "Es cerrajeria punto llavero arroba gmail punto com", "check_not": []},
            {"cliente": "Si ese mero", "check_not": ["correo", "email"]},
        ],
        "bugs_criticos": ["GPT_LOGICA_ROTA"],
    },
    {
        "id": 67, "nombre": "Pregunta encargado cuando dueno ya se identifico",
        "categoria": "logica_rota", "critico": True,
        "contacto": {"nombre_negocio": "Pinturas El Arcoiris", "telefono": "6141230067", "ciudad": "Chihuahua"},
        "turnos": [
            {"cliente": "Bueno, aqui Pinturas El Arcoiris", "check_not": []},
            {"cliente": "Yo soy el mero mero, el dueno pues", "check_not": []},
            {"cliente": "Orale suena interesante, mandeme la info", "check_not": ["encargado"]},
        ],
        "bugs_criticos": ["GPT_LOGICA_ROTA"],
    },
    {
        "id": 68, "nombre": "Da WhatsApp y Bruce pide otra vez el mismo",
        "categoria": "logica_rota", "critico": True,
        "contacto": {"nombre_negocio": "Materiales La Fortaleza", "telefono": "2221230068", "ciudad": "Puebla"},
        "turnos": [
            {"cliente": "Si bueno?", "check_not": []},
            {"cliente": "Si soy yo, al WhatsApp porfa", "check_not": []},
            {"cliente": "Dos dos veintitres cuarenta y cinco sesenta y siete", "check_not": []},
            {"cliente": "Si es correcto", "check_not": ["proporcionar"]},
        ],
        "bugs_criticos": ["DATO_NEGADO_REINSISTIDO", "PREGUNTA_REPETIDA"],
    },
    {
        "id": 69, "nombre": "Cliente confirma todo y Bruce sigue preguntando",
        "categoria": "logica_rota", "critico": False,
        "contacto": {"nombre_negocio": "Herramientas Don Pepe", "telefono": "4421230069", "ciudad": "Queretaro"},
        "turnos": [
            {"cliente": "Bueno?", "check_not": []},
            {"cliente": "Si soy el encargado", "check_not": []},
            {"cliente": "Si claro, al whats", "check_not": []},
            {"cliente": "Cuatro cuarenta y dos doce treinta sesenta y nueve", "check_not": []},
            {"cliente": "Si esta correcto gracias", "check_not": ["encargado"]},
        ],
        "bugs_criticos": ["GPT_LOGICA_ROTA"],
    },
    {
        "id": 70, "nombre": "Bruce repite pitch despues de que cliente acepto",
        "categoria": "logica_rota", "critico": True,
        "contacto": {"nombre_negocio": "Soluciones Electricas MX", "telefono": "5541230070", "ciudad": "CDMX"},
        "turnos": [
            {"cliente": "Bueno", "check_not": []},
            {"cliente": "Si soy", "check_not": []},
            {"cliente": "Va, mandelo al WhatsApp", "check_not": []},
            {"cliente": "Cinco cincuenta y cuatro doce treinta setenta", "check_not": ["herramienta"]},
        ],
        "bugs_criticos": ["GPT_LOGICA_ROTA"],
    },
    # --- CONTEXTO_IGNORADO variaciones ---
    {
        "id": 71, "nombre": "Cliente dice que vende abarrotes, no ferreteria",
        "categoria": "contexto_ignorado", "critico": True,
        "contacto": {"nombre_negocio": "Abarrotes La Esquina", "telefono": "3336500071", "ciudad": "Guadalajara"},
        "turnos": [
            {"cliente": "Bueno?", "check_not": []},
            {"cliente": "Si soy, pero fijese que nosotros vendemos puras cosas de abarrotes, nada de ferreteria", "check_not": []},
        ],
        "bugs_criticos": ["GPT_CONTEXTO_IGNORADO"],
    },
    {
        "id": 72, "nombre": "Cliente explica que ya cerro el negocio",
        "categoria": "contexto_ignorado", "critico": True,
        "contacto": {"nombre_negocio": "Ferreteria Cerrada", "telefono": "3336500072", "ciudad": "Guadalajara"},
        "turnos": [
            {"cliente": "Bueno", "check_not": []},
            {"cliente": "Fijese que ya cerramos el negocio hace como dos meses, ya no vendemos nada de eso", "check_not": ["catalogo", "whatsapp", "encargado"]},
        ],
        "bugs_criticos": ["GPT_CONTEXTO_IGNORADO"],
    },
    {
        "id": 73, "nombre": "Cliente dice que esta en horario de comida",
        "categoria": "contexto_ignorado", "critico": False,
        "contacto": {"nombre_negocio": "Tornillos Express", "telefono": "8112340073", "ciudad": "Monterrey"},
        "turnos": [
            {"cliente": "Bueno?", "check_not": []},
            {"cliente": "Oiga ahorita estamos en hora de comida, no hay nadie aqui, estoy solo en la tienda", "check_not": []},
        ],
        "bugs_criticos": ["GPT_CONTEXTO_IGNORADO"],
    },
    {
        "id": 74, "nombre": "Cliente explica que solo vende al menudeo",
        "categoria": "contexto_ignorado", "critico": False,
        "contacto": {"nombre_negocio": "Mini Ferreteria Lupita", "telefono": "3336500074", "ciudad": "Guadalajara"},
        "turnos": [
            {"cliente": "Si bueno", "check_not": []},
            {"cliente": "Si soy la encargada, pero nosotros somos muy chiquitos, solo vendemos al menudeo, no compramos por mayoreo", "check_not": []},
        ],
        "bugs_criticos": ["GPT_CONTEXTO_IGNORADO"],
    },
    {
        "id": 75, "nombre": "Cliente dice que ya tiene el catalogo de Nioval",
        "categoria": "contexto_ignorado", "critico": True,
        "contacto": {"nombre_negocio": "Ferreteria Ya Tengo", "telefono": "3336500075", "ciudad": "Guadalajara"},
        "turnos": [
            {"cliente": "Bueno?", "check_not": []},
            {"cliente": "Si soy, ah si ya me mandaron el catalogo la vez pasada, ya lo tengo", "check_not": []},
            {"cliente": "Si ya lo vi, luego les marco si necesito algo va?", "check_not": ["catalogo", "enviar"]},
        ],
        "bugs_criticos": ["GPT_CONTEXTO_IGNORADO"],
    },
    # --- OPORTUNIDAD_PERDIDA variaciones ---
    {
        "id": 76, "nombre": "Cliente pregunta por precios de brocas especificas",
        "categoria": "oportunidad_perdida", "critico": True,
        "contacto": {"nombre_negocio": "Brocas y Mas Industrial", "telefono": "8112340076", "ciudad": "Monterrey"},
        "turnos": [
            {"cliente": "Bueno?", "check_not": []},
            {"cliente": "Si soy, oiga manejan brocas de carburo de tungsteno para concreto?", "check_not": []},
        ],
        "bugs_criticos": ["GPT_OPORTUNIDAD_PERDIDA"],
    },
    {
        "id": 77, "nombre": "Cliente menciona que quiere comprar en volumen",
        "categoria": "oportunidad_perdida", "critico": True,
        "contacto": {"nombre_negocio": "Construcciones Garza SA", "telefono": "8112340077", "ciudad": "Monterrey"},
        "turnos": [
            {"cliente": "Bueno, Construcciones Garza", "check_not": []},
            {"cliente": "Si soy el de compras, fijese que necesitamos surtir como 500 piezas de tornilleria variada, es para una obra grande", "check_not": []},
        ],
        "bugs_criticos": ["GPT_OPORTUNIDAD_PERDIDA"],
    },
    {
        "id": 78, "nombre": "Cliente pregunta si dan credito a 30 dias",
        "categoria": "oportunidad_perdida", "critico": False,
        "contacto": {"nombre_negocio": "Materiales del Bajio", "telefono": "4771230078", "ciudad": "Leon"},
        "turnos": [
            {"cliente": "Si bueno?", "check_not": []},
            {"cliente": "Si soy, oiga manejan credito? necesitamos como a 30 dias", "check_not": []},
        ],
        "bugs_criticos": ["GPT_OPORTUNIDAD_PERDIDA"],
    },
    {
        "id": 79, "nombre": "Cliente pide descuento directo",
        "categoria": "oportunidad_perdida", "critico": False,
        "contacto": {"nombre_negocio": "Tlapaleria Descuento", "telefono": "3336500079", "ciudad": "Guadalajara"},
        "turnos": [
            {"cliente": "Bueno?", "check_not": []},
            {"cliente": "Si soy, oye y si pido harto me hacen descuento?", "check_not": []},
        ],
        "bugs_criticos": ["GPT_OPORTUNIDAD_PERDIDA"],
    },
    # --- RESPUESTA_INCOHERENTE variaciones ---
    {
        "id": 80, "nombre": "Respuesta generica a pregunta especifica de envio",
        "categoria": "respuesta_incoherente", "critico": True,
        "contacto": {"nombre_negocio": "Ferreteria La Lejana", "telefono": "9511230080", "ciudad": "Oaxaca"},
        "turnos": [
            {"cliente": "Bueno?", "check_not": []},
            {"cliente": "Si soy, oiga hacen envios hasta aca a Oaxaca?", "check_not": []},
        ],
        "bugs_criticos": ["GPT_RESPUESTA_INCOHERENTE"],
    },
    {
        "id": 81, "nombre": "Cliente pregunta garantia y Bruce ignora",
        "categoria": "respuesta_incoherente", "critico": False,
        "contacto": {"nombre_negocio": "Herramientas Confianza", "telefono": "3336500081", "ciudad": "Guadalajara"},
        "turnos": [
            {"cliente": "Si bueno", "check_not": []},
            {"cliente": "Si soy, oiga sus productos traen garantia? es que hemos tenido problemas con otros proveedores", "check_not": []},
        ],
        "bugs_criticos": ["GPT_RESPUESTA_INCOHERENTE"],
    },
    {
        "id": 82, "nombre": "Bruce responde a silencio STT con texto generico",
        "categoria": "respuesta_incoherente", "critico": False,
        "contacto": {"nombre_negocio": "Materiales Silencio", "telefono": "3336500082", "ciudad": "Guadalajara"},
        "turnos": [
            {"cliente": "Bueno?", "check_not": []},
            {"cliente": "...", "check_not": []},
            {"cliente": "Ah si bueno, soy el encargado, me quede pensando", "check_not": []},
        ],
        "bugs_criticos": ["GPT_RESPUESTA_INCOHERENTE"],
    },
    # --- RESPUESTA_INCORRECTA variaciones ---
    {
        "id": 83, "nombre": "Bruce confunde nombre del negocio del cliente",
        "categoria": "respuesta_incorrecta", "critico": True,
        "contacto": {"nombre_negocio": "Ferreteria Los Hermanos Lopez", "telefono": "3336500083", "ciudad": "Guadalajara"},
        "turnos": [
            {"cliente": "Bueno, Ferreteria Los Hermanos Lopez", "check_not": []},
            {"cliente": "Si soy el encargado", "check_not": ["martinez", "garcia", "perez"]},
        ],
        "bugs_criticos": ["GPT_RESPUESTA_INCORRECTA"],
    },
    {
        "id": 84, "nombre": "Cliente pregunta tiempo de entrega",
        "categoria": "respuesta_incorrecta", "critico": False,
        "contacto": {"nombre_negocio": "Materiales Rapidos", "telefono": "6641230084", "ciudad": "Tijuana"},
        "turnos": [
            {"cliente": "Bueno?", "check_not": []},
            {"cliente": "Si soy, oiga en cuanto tiempo llega un pedido aca a Tijuana?", "check_not": []},
        ],
        "bugs_criticos": ["GPT_RESPUESTA_INCORRECTA"],
    },
    # --- SALUDO variaciones ---
    {
        "id": 85, "nombre": "Saludo despues de silencio largo - STT tarda",
        "categoria": "saludo_faltante", "critico": True,
        "contacto": {"nombre_negocio": "Tlapaleria Silenciosa", "telefono": "3336500085", "ciudad": "Guadalajara"},
        "turnos": [
            {"cliente": "Alo? bueno? si?", "check_not": []},
            {"cliente": "Si si aqui estoy, es que no se oia", "check_not": []},
        ],
        "bugs_criticos": ["SALUDO_FALTANTE"],
    },
    {
        "id": 86, "nombre": "Saludo regional: 'Mande?' como primera respuesta",
        "categoria": "saludo_faltante", "critico": False,
        "contacto": {"nombre_negocio": "Ferreteria Mande", "telefono": "2291230086", "ciudad": "Veracruz"},
        "turnos": [
            {"cliente": "Mande?", "check_not": []},
            {"cliente": "Si bueno, aqui la ferreteria", "check_not": []},
        ],
        "bugs_criticos": ["SALUDO_FALTANTE"],
    },
    # --- TONO variaciones ---
    {
        "id": 87, "nombre": "Cliente molesto por demora - Bruce debe ser empatico",
        "categoria": "tono_inadecuado", "critico": True,
        "contacto": {"nombre_negocio": "Herramientas Molesto", "telefono": "3336500087", "ciudad": "Guadalajara"},
        "turnos": [
            {"cliente": "Bueno?", "check_not": []},
            {"cliente": "Oiga es que ya me habian dicho que me iban a mandar el catalogo y nunca me llego, llevan como 2 semanas", "check_not": []},
        ],
        "bugs_criticos": ["GPT_TONO_INADECUADO"],
    },
    {
        "id": 88, "nombre": "Cliente anciano habla lento - Bruce no debe apurar",
        "categoria": "tono_inadecuado", "critico": False,
        "contacto": {"nombre_negocio": "Tlapaleria Don Beto", "telefono": "3336500088", "ciudad": "Guadalajara"},
        "turnos": [
            {"cliente": "Bueno... si... bueno...?", "check_not": []},
            {"cliente": "Ay si mijo... pues... a ver... si soy... el que atiende pues... yo y mi esposa...", "check_not": []},
            {"cliente": "Uy pues... dejame pensar... a ver... si mande el catalogo... al... whats... app...", "check_not": []},
        ],
        "bugs_criticos": ["GPT_TONO_INADECUADO"],
    },
    # --- CANAL_RECHAZADO variaciones ---
    {
        "id": 89, "nombre": "WhatsApp rechazado con excusa: 'no tengo datos'",
        "categoria": "canal_rechazado", "critico": True,
        "contacto": {"nombre_negocio": "Ferreteria Sin Datos", "telefono": "3336500089", "ciudad": "Guadalajara"},
        "turnos": [
            {"cliente": "Bueno", "check_not": []},
            {"cliente": "Si soy yo", "check_not": []},
            {"cliente": "Fijese que no tengo datos en el celular, no me llegan los whats", "check_not": []},
            {"cliente": "Si mejor al correo", "check_not": ["whatsapp", "whats"]},
        ],
        "bugs_criticos": ["DATO_NEGADO_REINSISTIDO"],
    },
    {
        "id": 90, "nombre": "Correo rechazado: 'no reviso correos'",
        "categoria": "canal_rechazado", "critico": True,
        "contacto": {"nombre_negocio": "Materiales Sin Correo", "telefono": "3336500090", "ciudad": "Guadalajara"},
        "turnos": [
            {"cliente": "Si bueno", "check_not": []},
            {"cliente": "Si soy", "check_not": []},
            {"cliente": "No pues el whats no, no lo uso", "check_not": []},
            {"cliente": "Pues correo tampoco, nunca los reviso la verdad, mejor deme su numero y yo les marco", "check_not": ["correo", "email"]},
        ],
        "bugs_criticos": ["DATO_NEGADO_REINSISTIDO"],
    },
    {
        "id": 91, "nombre": "WhatsApp rechazado indirecto: 'el patron no usa eso'",
        "categoria": "canal_rechazado", "critico": True,
        "contacto": {"nombre_negocio": "Tlapaleria Don Chucho", "telefono": "6621230091", "ciudad": "Hermosillo"},
        "turnos": [
            {"cliente": "Bueno?", "check_not": []},
            {"cliente": "Si yo soy", "check_not": []},
            {"cliente": "No pues el patron no usa eso del whatsapp, es de la vieja escuela jaja", "check_not": []},
            {"cliente": "Si tiene correo, anote", "check_not": ["whatsapp"]},
        ],
        "bugs_criticos": ["DATO_NEGADO_REINSISTIDO"],
    },
    # --- CALLBACK variaciones ---
    {
        "id": 92, "nombre": "Callback: 'el encargado llega a las 2'",
        "categoria": "callback", "critico": True,
        "contacto": {"nombre_negocio": "Materiales Horario", "telefono": "3336500092", "ciudad": "Guadalajara"},
        "turnos": [
            {"cliente": "Bueno?", "check_not": []},
            {"cliente": "El encargado no esta, llega como a las dos de la tarde", "check_not": ["catalogo"]},
        ],
        "bugs_criticos": ["GPT_CONTEXTO_IGNORADO"],
    },
    {
        "id": 93, "nombre": "Callback: 'marqueme el lunes'",
        "categoria": "callback", "critico": False,
        "contacto": {"nombre_negocio": "Ferreteria Lunes", "telefono": "3336500093", "ciudad": "Guadalajara"},
        "turnos": [
            {"cliente": "Bueno", "check_not": []},
            {"cliente": "Si soy pero ahorita ando en chinga, marqueme el lunes mejor", "check_not": ["catalogo"]},
        ],
        "bugs_criticos": ["GPT_CONTEXTO_IGNORADO"],
    },
    {
        "id": 94, "nombre": "Callback con dia especifico: 'el miercoles por la manana'",
        "categoria": "callback", "critico": False,
        "contacto": {"nombre_negocio": "Tornillos Agenda", "telefono": "8112340094", "ciudad": "Monterrey"},
        "turnos": [
            {"cliente": "Bueno?", "check_not": []},
            {"cliente": "Si soy, pero ahorita no le puedo atender, marqueme el miercoles en la manana", "check_not": []},
        ],
        "bugs_criticos": ["GPT_CONTEXTO_IGNORADO"],
    },
    # --- RECHAZO variaciones ---
    {
        "id": 95, "nombre": "Rechazo educado: 'gracias pero no necesitamos'",
        "categoria": "rechazo", "critico": True,
        "contacto": {"nombre_negocio": "Ferreteria Amable", "telefono": "3336500095", "ciudad": "Guadalajara"},
        "turnos": [
            {"cliente": "Bueno?", "check_not": []},
            {"cliente": "Si soy, fijese que ahorita estamos bien surtidos, muchas gracias pero no necesitamos nada, gracias", "check_not": ["catalogo", "whatsapp"]},
        ],
        "bugs_criticos": ["GPT_TONO_INADECUADO", "LOOP"],
    },
    {
        "id": 96, "nombre": "Rechazo por competencia: 'ya trabajamos con Truper directo'",
        "categoria": "rechazo", "critico": False,
        "contacto": {"nombre_negocio": "Herramientas Truper Fan", "telefono": "3336500096", "ciudad": "Guadalajara"},
        "turnos": [
            {"cliente": "Bueno", "check_not": []},
            {"cliente": "Si soy, pero nosotros ya trabajamos directo con Truper, nos dan mejor precio", "check_not": []},
        ],
        "bugs_criticos": ["GPT_CONTEXTO_IGNORADO"],
    },
    {
        "id": 97, "nombre": "Rechazo con enojo: 'ya dije que no!'",
        "categoria": "rechazo", "critico": True,
        "contacto": {"nombre_negocio": "Tlapaleria Ya Dije", "telefono": "3336500097", "ciudad": "Guadalajara"},
        "turnos": [
            {"cliente": "Bueno?", "check_not": []},
            {"cliente": "Ya les dije que no! que no me interesa! ya van como 3 veces que llaman!", "check_not": ["catalogo", "whatsapp", "producto"]},
        ],
        "bugs_criticos": ["GPT_TONO_INADECUADO", "LOOP"],
    },
    {
        "id": 98, "nombre": "Rechazo 3ra persona: 'dice mi jefe que no'",
        "categoria": "rechazo", "critico": False,
        "contacto": {"nombre_negocio": "Materiales El Jefe Dice", "telefono": "3336500098", "ciudad": "Guadalajara"},
        "turnos": [
            {"cliente": "Bueno", "check_not": []},
            {"cliente": "Dice mi jefe que no le interesa, que ya tiene sus proveedores y que ya no le marquen", "check_not": ["catalogo", "whatsapp"]},
        ],
        "bugs_criticos": ["GPT_TONO_INADECUADO"],
    },
    # --- TRANSFERENCIA variaciones ---
    {
        "id": 99, "nombre": "Transfer: 'ahorita se lo paso, espere tantito'",
        "categoria": "transferencia", "critico": True,
        "contacto": {"nombre_negocio": "Ferreteria Tantito", "telefono": "3336500099", "ciudad": "Guadalajara"},
        "turnos": [
            {"cliente": "Bueno?", "check_not": []},
            {"cliente": "Ahorita se lo paso, espereme tantito", "check_not": []},
            {"cliente": "Si bueno, aqui el encargado", "check_not": []},
        ],
        "bugs_criticos": ["PREGUNTA_REPETIDA"],
    },
    {
        "id": 100, "nombre": "Transfer: 'deje le digo que le conteste'",
        "categoria": "transferencia", "critico": False,
        "contacto": {"nombre_negocio": "Materiales Deje Le Digo", "telefono": "3336500100", "ciudad": "Guadalajara"},
        "turnos": [
            {"cliente": "Bueno", "check_not": []},
            {"cliente": "Deje le digo al encargado que le conteste, no se retire", "check_not": []},
            {"cliente": "Si bueno, ya estoy aqui, que paso", "check_not": []},
        ],
        "bugs_criticos": ["PREGUNTA_REPETIDA"],
    },
    {
        "id": 101, "nombre": "Transfer 3ra persona: 'te lo comunican'",
        "categoria": "transferencia", "critico": False,
        "contacto": {"nombre_negocio": "Tlapaleria Comunican", "telefono": "3336500101", "ciudad": "Guadalajara"},
        "turnos": [
            {"cliente": "Bueno?", "check_not": []},
            {"cliente": "Si ahorita te lo comunican, no cuelgues", "check_not": []},
            {"cliente": "Si diga, soy el encargado de compras", "check_not": []},
        ],
        "bugs_criticos": ["PREGUNTA_REPETIDA"],
    },
    # --- FLUJO_COMPLETO variaciones ---
    {
        "id": 102, "nombre": "Flujo exitoso con correo - Monterrey",
        "categoria": "flujo_completo", "critico": True,
        "contacto": {"nombre_negocio": "Ferreteria Regia", "telefono": "8112340102", "ciudad": "Monterrey"},
        "turnos": [
            {"cliente": "Bueno?", "check_not": []},
            {"cliente": "Si soy yo", "check_not": []},
            {"cliente": "Mandelo por correo mejor", "check_not": []},
            {"cliente": "Es ferreteria punto regia arroba hotmail punto com", "check_not": []},
            {"cliente": "Si correcto, gracias", "check_not": []},
        ],
        "bugs_criticos": [],
    },
    {
        "id": 103, "nombre": "Flujo con muchas preguntas del cliente - interesado",
        "categoria": "flujo_completo", "critico": True,
        "contacto": {"nombre_negocio": "Materiales Preguntones", "telefono": "3336500103", "ciudad": "Guadalajara"},
        "turnos": [
            {"cliente": "Bueno, materiales preguntones", "check_not": []},
            {"cliente": "Si soy el encargado, que ofrecen?", "check_not": []},
            {"cliente": "Y que marcas manejan?", "check_not": []},
            {"cliente": "Orale, y hacen envios?", "check_not": []},
            {"cliente": "Va pues, mandelo al whats", "check_not": []},
            {"cliente": "Tres tres treinta y seis cincuenta cero cero uno cero tres", "check_not": []},
        ],
        "bugs_criticos": [],
    },
    {
        "id": 104, "nombre": "Flujo con transfer exitoso luego WhatsApp",
        "categoria": "flujo_completo", "critico": False,
        "contacto": {"nombre_negocio": "Ferreteria Transfer OK", "telefono": "3336500104", "ciudad": "Guadalajara"},
        "turnos": [
            {"cliente": "Bueno?", "check_not": []},
            {"cliente": "Un momento le paso al encargado", "check_not": []},
            {"cliente": "Si bueno, soy el encargado de compras", "check_not": []},
            {"cliente": "Si va, mandelo al WhatsApp", "check_not": []},
            {"cliente": "Es el tres tres treinta y seis cincuenta cero uno cero cuatro", "check_not": []},
        ],
        "bugs_criticos": [],
    },
    {
        "id": 105, "nombre": "Flujo rapido: cliente ya conoce Nioval",
        "categoria": "flujo_completo", "critico": False,
        "contacto": {"nombre_negocio": "Materiales Ya Conozco", "telefono": "3336500105", "ciudad": "Guadalajara"},
        "turnos": [
            {"cliente": "Bueno?", "check_not": []},
            {"cliente": "Ah si, Nioval, si ya se quienes son, mandeme el catalogo actualizado", "check_not": []},
            {"cliente": "Al WhatsApp, es el tres tres doce treinta y cuatro cero cinco", "check_not": []},
            {"cliente": "Si correcto, gracias", "check_not": []},
        ],
        "bugs_criticos": [],
    },
    # --- STT_GARBLED variaciones ---
    {
        "id": 106, "nombre": "STT: Eco duplicado largo",
        "categoria": "stt_garbled", "critico": True,
        "contacto": {"nombre_negocio": "Ferreteria Eco", "telefono": "3336500106", "ciudad": "Guadalajara"},
        "turnos": [
            {"cliente": "Bueno bueno si bueno?", "check_not": []},
            {"cliente": "Si soy si soy el encargado el encargado", "check_not": []},
            {"cliente": "Al whats whats al whatsapp", "check_not": []},
        ],
        "bugs_criticos": ["GPT_RESPUESTA_INCOHERENTE"],
    },
    {
        "id": 107, "nombre": "STT: Deepgram mishear numeros",
        "categoria": "stt_garbled", "critico": True,
        "contacto": {"nombre_negocio": "Tornillos Mishear", "telefono": "3336500107", "ciudad": "Guadalajara"},
        "turnos": [
            {"cliente": "Bueno", "check_not": []},
            {"cliente": "Si soy yo", "check_not": []},
            {"cliente": "Al whats", "check_not": []},
            {"cliente": "Es el tres tres veintiseis ahi va veintiseis cuarenta y sinco... cuarenta y cinco pues sesenta y siete", "check_not": []},
        ],
        "bugs_criticos": ["GPT_RESPUESTA_INCOHERENTE"],
    },
    {
        "id": 108, "nombre": "STT: Ruido de fondo con palabras sueltas",
        "categoria": "stt_garbled", "critico": False,
        "contacto": {"nombre_negocio": "Ferreteria Ruidosa", "telefono": "3336500108", "ciudad": "Guadalajara"},
        "turnos": [
            {"cliente": "B... bue... bueno?", "check_not": []},
            {"cliente": "Si... [ruido]... yo soy... [inaudible]... el que atiende", "check_not": []},
        ],
        "bugs_criticos": ["GPT_RESPUESTA_INCOHERENTE"],
    },
    {
        "id": 109, "nombre": "STT: Azure duplica frase completa",
        "categoria": "stt_garbled", "critico": False,
        "contacto": {"nombre_negocio": "Materiales Duplicado", "telefono": "3336500109", "ciudad": "Guadalajara"},
        "turnos": [
            {"cliente": "Bueno si bueno?", "check_not": []},
            {"cliente": "Si soy el encargado si soy el encargado de la tienda", "check_not": []},
            {"cliente": "Si mandelo por WhatsApp mandelo por WhatsApp", "check_not": []},
        ],
        "bugs_criticos": ["GPT_RESPUESTA_INCOHERENTE"],
    },
    # --- ENCARGADO_AUSENTE variaciones ---
    {
        "id": 110, "nombre": "Encargado en reunion",
        "categoria": "encargado_ausente", "critico": True,
        "contacto": {"nombre_negocio": "Ferreteria Reunion", "telefono": "3336500110", "ciudad": "Guadalajara"},
        "turnos": [
            {"cliente": "Bueno?", "check_not": []},
            {"cliente": "El encargado esta en una reunion, no creo que salga pronto", "check_not": ["catalogo"]},
        ],
        "bugs_criticos": ["GPT_CONTEXTO_IGNORADO"],
    },
    {
        "id": 111, "nombre": "Encargado murio - caso delicado",
        "categoria": "encargado_ausente", "critico": True,
        "contacto": {"nombre_negocio": "Materiales Delicado", "telefono": "3336500111", "ciudad": "Guadalajara"},
        "turnos": [
            {"cliente": "Bueno", "check_not": []},
            {"cliente": "Mire el dueno fallecio hace poco, estamos viendo que hacemos con el negocio", "check_not": ["catalogo", "whatsapp", "encargado"]},
        ],
        "bugs_criticos": ["GPT_TONO_INADECUADO"],
    },
    {
        "id": 112, "nombre": "Encargado fue al banco, regresa en rato",
        "categoria": "encargado_ausente", "critico": False,
        "contacto": {"nombre_negocio": "Tlapaleria Al Banco", "telefono": "3336500112", "ciudad": "Guadalajara"},
        "turnos": [
            {"cliente": "Bueno?", "check_not": []},
            {"cliente": "El patron fue al banco, quien sabe a que hora regrese", "check_not": []},
        ],
        "bugs_criticos": ["GPT_CONTEXTO_IGNORADO"],
    },
    {
        "id": 113, "nombre": "Nadie atiende compras aqui - empleado nuevo",
        "categoria": "encargado_ausente", "critico": False,
        "contacto": {"nombre_negocio": "Ferreteria Nuevo", "telefono": "3336500113", "ciudad": "Guadalajara"},
        "turnos": [
            {"cliente": "Bueno", "check_not": []},
            {"cliente": "Yo apenas entre a trabajar aqui, no se quien ve lo de las compras, el patron no esta", "check_not": []},
        ],
        "bugs_criticos": ["GPT_CONTEXTO_IGNORADO"],
    },
    # --- CONFIRMACIONES variaciones ---
    {
        "id": 114, "nombre": "'Simon' como confirmacion",
        "categoria": "confirmaciones", "critico": True,
        "contacto": {"nombre_negocio": "Ferreteria Simon", "telefono": "3336500114", "ciudad": "Guadalajara"},
        "turnos": [
            {"cliente": "Bueno?", "check_not": []},
            {"cliente": "Simon, yo soy", "check_not": []},
            {"cliente": "Simon, al whats", "check_not": []},
            {"cliente": "Tres tres doce treinta y cuatro cero cero uno catorce", "check_not": []},
        ],
        "bugs_criticos": [],
    },
    {
        "id": 115, "nombre": "'Sale' y 'va' como confirmaciones",
        "categoria": "confirmaciones", "critico": False,
        "contacto": {"nombre_negocio": "Materiales Sale Va", "telefono": "3336500115", "ciudad": "Guadalajara"},
        "turnos": [
            {"cliente": "Bueno", "check_not": []},
            {"cliente": "Sale, si soy", "check_not": []},
            {"cliente": "Va pues, por el whats", "check_not": []},
            {"cliente": "Tres tres treinta y seis cincuenta cero cero once quince", "check_not": []},
        ],
        "bugs_criticos": [],
    },
    {
        "id": 116, "nombre": "'Andale' y 'ajale' como confirmaciones",
        "categoria": "confirmaciones", "critico": False,
        "contacto": {"nombre_negocio": "Tlapaleria Andale", "telefono": "3336500116", "ciudad": "Guadalajara"},
        "turnos": [
            {"cliente": "Bueno?", "check_not": []},
            {"cliente": "Andale si, yo soy el dueno", "check_not": []},
            {"cliente": "Ajale, mandelo al whats", "check_not": []},
        ],
        "bugs_criticos": [],
    },
    # --- WHAT_OFFER variaciones ---
    {
        "id": 117, "nombre": "Pregunta 'que marcas manejan' despues de pitch",
        "categoria": "what_offer", "critico": True,
        "contacto": {"nombre_negocio": "Ferreteria Marcas", "telefono": "3336500117", "ciudad": "Guadalajara"},
        "turnos": [
            {"cliente": "Bueno?", "check_not": []},
            {"cliente": "Si soy", "check_not": []},
            {"cliente": "Y que marcas manejan?", "check_not": []},
        ],
        "bugs_criticos": ["GPT_OPORTUNIDAD_PERDIDA"],
    },
    {
        "id": 118, "nombre": "Pregunta 'tienen herramienta electrica?'",
        "categoria": "what_offer", "critico": False,
        "contacto": {"nombre_negocio": "Materiales Electricos", "telefono": "3336500118", "ciudad": "Guadalajara"},
        "turnos": [
            {"cliente": "Bueno", "check_not": []},
            {"cliente": "Si soy yo", "check_not": []},
            {"cliente": "Y tienen herramienta electrica? rotomartillos, esmeriles, esas cosas?", "check_not": []},
        ],
        "bugs_criticos": ["GPT_OPORTUNIDAD_PERDIDA"],
    },
    {
        "id": 119, "nombre": "'A como dan los flexometros?' - precio directo",
        "categoria": "what_offer", "critico": False,
        "contacto": {"nombre_negocio": "Tlapaleria Flexometros", "telefono": "3336500119", "ciudad": "Guadalajara"},
        "turnos": [
            {"cliente": "Bueno?", "check_not": []},
            {"cliente": "Si soy, a como dan los flexometros de 8 metros?", "check_not": []},
        ],
        "bugs_criticos": ["GPT_OPORTUNIDAD_PERDIDA"],
    },
    # --- CONTACTO_INVERTIDO variaciones ---
    {
        "id": 120, "nombre": "Cliente pide pagina web de Nioval",
        "categoria": "contacto_invertido", "critico": False,
        "contacto": {"nombre_negocio": "Ferreteria Web", "telefono": "3336500120", "ciudad": "Guadalajara"},
        "turnos": [
            {"cliente": "Bueno?", "check_not": []},
            {"cliente": "Si soy, tienen pagina de internet donde pueda ver los productos?", "check_not": []},
        ],
        "bugs_criticos": ["GPT_OPORTUNIDAD_PERDIDA"],
    },
    {
        "id": 121, "nombre": "Cliente pide WhatsApp de Bruce para el guardar",
        "categoria": "contacto_invertido", "critico": True,
        "contacto": {"nombre_negocio": "Materiales Guarda Contacto", "telefono": "3336500121", "ciudad": "Guadalajara"},
        "turnos": [
            {"cliente": "Bueno", "check_not": []},
            {"cliente": "Si soy, oiga mejor dame tu numero de WhatsApp y yo te mando mensaje cuando necesite", "check_not": []},
        ],
        "bugs_criticos": ["GPT_OPORTUNIDAD_PERDIDA"],
    },
    # --- BUZON/IVR variaciones ---
    {
        "id": 122, "nombre": "Buzon: 'el numero que usted marco no existe'",
        "categoria": "buzon_ivr", "critico": True,
        "contacto": {"nombre_negocio": "Numero Inexistente", "telefono": "3336500122", "ciudad": "Guadalajara"},
        "turnos": [
            {"cliente": "El numero que usted marco no existe o ha sido cancelado", "check_not": ["catalogo", "encargado"]},
        ],
        "bugs_criticos": ["GPT_RESPUESTA_INCOHERENTE"],
    },
    {
        "id": 123, "nombre": "IVR: 'para ventas marque 1, para soporte marque 2'",
        "categoria": "buzon_ivr", "critico": False,
        "contacto": {"nombre_negocio": "Empresa IVR Menu", "telefono": "3336500123", "ciudad": "Guadalajara"},
        "turnos": [
            {"cliente": "Bienvenido a empresa, para ventas marque uno, para soporte marque dos, para directorio marque tres", "check_not": ["catalogo", "encargado"]},
        ],
        "bugs_criticos": ["GPT_RESPUESTA_INCOHERENTE"],
    },
    {
        "id": 124, "nombre": "Buzon: 'deje su mensaje despues del tono'",
        "categoria": "buzon_ivr", "critico": False,
        "contacto": {"nombre_negocio": "Ferreteria Buzon Tono", "telefono": "3336500124", "ciudad": "Guadalajara"},
        "turnos": [
            {"cliente": "La persona que llama no esta disponible, por favor deje su mensaje despues del tono", "check_not": ["catalogo", "encargado"]},
        ],
        "bugs_criticos": ["GPT_RESPUESTA_INCOHERENTE"],
    },
    # --- QUEJA variaciones ---
    {
        "id": 125, "nombre": "Queja suave: 'oiga ya habian llamado ayer'",
        "categoria": "queja", "critico": True,
        "contacto": {"nombre_negocio": "Ferreteria Ya Llamaron", "telefono": "3336500125", "ciudad": "Guadalajara"},
        "turnos": [
            {"cliente": "Bueno?", "check_not": []},
            {"cliente": "Oiga ya me habian llamado ayer para lo mismo, no le digo que no nos interesa", "check_not": ["catalogo", "whatsapp"]},
        ],
        "bugs_criticos": ["GPT_TONO_INADECUADO"],
    },
    {
        "id": 126, "nombre": "Queja agresiva: 'estan molestando, voy a reportar'",
        "categoria": "queja", "critico": True,
        "contacto": {"nombre_negocio": "Materiales Reportar", "telefono": "3336500126", "ciudad": "Guadalajara"},
        "turnos": [
            {"cliente": "Bueno", "check_not": []},
            {"cliente": "Oiga ya estan molestando, si siguen llamando los voy a reportar con Profeco, ya basta", "check_not": ["catalogo", "whatsapp", "producto"]},
        ],
        "bugs_criticos": ["GPT_TONO_INADECUADO", "LOOP"],
    },
    {
        "id": 127, "nombre": "Queja 3ra persona: 'la senora dice que ya no llamen'",
        "categoria": "queja", "critico": False,
        "contacto": {"nombre_negocio": "Tlapaleria Senora Dice", "telefono": "3336500127", "ciudad": "Guadalajara"},
        "turnos": [
            {"cliente": "Bueno?", "check_not": []},
            {"cliente": "Mire, la senora dice que ya no le llamen, que ya tiene sus proveedores y que ya no la molesten", "check_not": ["catalogo", "whatsapp"]},
        ],
        "bugs_criticos": ["GPT_TONO_INADECUADO"],
    },
    # --- DATO_SIN_RESPUESTA variaciones ---
    {
        "id": 128, "nombre": "Cliente da nombre completo sin que pidan",
        "categoria": "dato_sin_respuesta", "critico": True,
        "contacto": {"nombre_negocio": "Herramientas Nombre", "telefono": "3336500128", "ciudad": "Guadalajara"},
        "turnos": [
            {"cliente": "Bueno?", "check_not": []},
            {"cliente": "Si soy, me llamo Roberto Martinez para que lo apunte", "check_not": []},
            {"cliente": "Si al WhatsApp, tres tres doce treinta y cuatro cero uno veintiocho", "check_not": []},
        ],
        "bugs_criticos": ["DATO_SIN_RESPUESTA"],
    },
    # --- CLIENTE_HABLA_ULTIMO variaciones ---
    {
        "id": 129, "nombre": "Cliente dice 'sale bye' y Bruce no cierra",
        "categoria": "cliente_habla_ultimo", "critico": True,
        "contacto": {"nombre_negocio": "Ferreteria Bye", "telefono": "3336500129", "ciudad": "Guadalajara"},
        "turnos": [
            {"cliente": "Bueno?", "check_not": []},
            {"cliente": "Si soy", "check_not": []},
            {"cliente": "Va al whats", "check_not": []},
            {"cliente": "Tres tres doce treinta cuarenta cero uno veintinueve", "check_not": []},
            {"cliente": "Sale, bye!", "check_not": []},
        ],
        "bugs_criticos": ["CLIENTE_HABLA_ULTIMO"],
    },
    {
        "id": 130, "nombre": "Cliente cuelga con 'gracias, hasta luego'",
        "categoria": "cliente_habla_ultimo", "critico": False,
        "contacto": {"nombre_negocio": "Materiales Hasta Luego", "telefono": "3336500130", "ciudad": "Guadalajara"},
        "turnos": [
            {"cliente": "Bueno", "check_not": []},
            {"cliente": "Si soy yo", "check_not": []},
            {"cliente": "Al correo mejor", "check_not": []},
            {"cliente": "materiales punto hastaluego arroba gmail punto com", "check_not": []},
            {"cliente": "Gracias, hasta luego!", "check_not": []},
        ],
        "bugs_criticos": ["CLIENTE_HABLA_ULTIMO"],
    },
]


# ============================================================
# Categorias para --list y --category
# ============================================================
CATEGORIAS = {
    "logica_rota": "GPT_LOGICA_ROTA - Pregunta repetida, dato ya dado",
    "contexto_ignorado": "GPT_CONTEXTO_IGNORADO - Ignora contexto del cliente",
    "oportunidad_perdida": "GPT_OPORTUNIDAD_PERDIDA - Cliente interesado sin capitalizar",
    "respuesta_incoherente": "GPT_RESPUESTA_INCOHERENTE - Respuesta generica/desconectada",
    "respuesta_incorrecta": "GPT_RESPUESTA_INCORRECTA - Info falsa, nombres mal",
    "saludo_faltante": "SALUDO_FALTANTE - Sin saludo en primer turno",
    "tono_inadecuado": "GPT_TONO_INADECUADO - Tono informal/insistente",
    "cliente_habla_ultimo": "CLIENTE_HABLA_ULTIMO - Bruce no responde al final",
    "dato_sin_respuesta": "DATO_SIN_RESPUESTA - Cliente da dato, Bruce ignora",
    "canal_rechazado": "CANAL_RECHAZADO - WhatsApp/correo negado, re-pide",
    "callback": "CALLBACK - Cliente pide que llamen despues",
    "rechazo": "RECHAZO - No interes, proveedor, giro equivocado",
    "transferencia": "TRANSFERENCIA - Le paso, un momento, le comunico",
    "flujo_completo": "FLUJO_COMPLETO - Referencia exitosa sin bugs",
    "stt_garbled": "STT_GARBLED - Texto distorsionado por STT",
    "encargado_ausente": "ENCARGADO_AUSENTE - Variaciones de ausencia",
    "confirmaciones": "CONFIRMACIONES - Orale, mhm, aha, etc.",
    "what_offer": "WHAT_OFFER - Que venden, que ofrecen",
    "contacto_invertido": "CONTACTO_INVERTIDO - Cliente pide numero Bruce",
    "buzon_ivr": "BUZON/IVR - Buzon de voz, menu automatico",
    "queja": "QUEJA - Reclamos, quejas sobre llamadas",
}


# ============================================================
# Auditor Claude (opcional)
# ============================================================
def _auditar_con_claude(tracker, turnos_texto):
    """Audita una conversacion con Claude Sonnet. Retorna lista de bugs."""
    try:
        import anthropic
    except ImportError:
        print("    [CLAUDE] anthropic no instalado, skip")
        return []

    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    if not api_key:
        print("    [CLAUDE] ANTHROPIC_API_KEY no configurada, skip")
        return []

    client = anthropic.Anthropic(api_key=api_key)

    prompt = f"""Eres un auditor de calidad PROFUNDO para llamadas de ventas de Bruce W (agente AI de NIOVAL).
Tu trabajo es encontrar TODOS los bugs, errores, y areas de mejora posibles.

CONTEXTO COMPLETO:
- Bruce es un agente AI que llama a ferreterias/tlapalerias en Mexico para ofrecer catalogo de herramientas NIOVAL
- Bruce esta ubicado en Guadalajara, Jalisco y hace envios a toda la Republica
- Su objetivo: presentarse, dar pitch, pedir contacto (WhatsApp/correo/telefono) para enviar catalogo
- Vende: herramientas manuales, electricas, tornilleria, abrasivos, equipo de seguridad industrial, etc.
- Clientes tipicos: ferreterias, tlapalerias, materiales de construccion en toda la Republica
- El tono debe ser profesional pero amigable, usar "usted" no "tu", ser empatico con quejas

CONVERSACION A AUDITAR:
{turnos_texto}

TIPOS DE BUG A DETECTAR (se exhaustivo):
1. GPT_LOGICA_ROTA: Bruce repite pregunta ya respondida, pide dato ya dado, logica circular
2. GPT_CONTEXTO_IGNORADO: Bruce ignora contexto clave (giro, situacion, estado emocional del cliente)
3. GPT_OPORTUNIDAD_PERDIDA: Cliente muestra interes/pregunta y Bruce no capitaliza o no responde adecuadamente
4. GPT_RESPUESTA_INCOHERENTE: Respuesta generica/desconectada que no atiende lo que dijo el cliente
5. GPT_RESPUESTA_INCORRECTA: Bruce da info falsa, inventa datos, confunde nombres
6. GPT_TONO_INADECUADO: Bruce insiste despues de rechazo, tono demasiado informal, no empatiza con quejas
7. SALUDO_FALTANTE: Bruce no saluda apropiadamente al inicio
8. PREGUNTA_REPETIDA: Bruce hace la misma pregunta 2+ veces
9. DATO_NEGADO_REINSISTIDO: Bruce pide canal (WhatsApp/correo) que el cliente ya rechazo
10. LOOP: Bruce entra en ciclo repitiendo la misma respuesta/accion
11. MEJORA_EMPATIA: Bruce podria ser mas empatico en su respuesta (cuando cliente expresa frustacion/problema)
12. MEJORA_NATURAL: La respuesta de Bruce suena robotica, scripted, o poco natural para el contexto mexicano
13. MEJORA_CIERRE: Bruce no cierra bien la conversacion, no confirma datos, o no se despide apropiadamente

CRITERIOS DE SEVERIDAD:
- CRITICO: Bug que romperia la conversacion o molestaria al cliente en produccion
- ALTO: Bug evidente que afecta la calidad de la interaccion
- MEDIO: Area de mejora que haria la conversacion mas fluida
- BAJO: Detalle menor o sugerencia de optimizacion

Responde SOLO en este formato JSON (un array):
[{{"tipo": "TIPO_BUG", "severidad": "CRITICO|ALTO|MEDIO|BAJO", "turno": N, "detalle": "Descripcion clara del problema y sugerencia de mejora"}}]

Si NO hay bugs ni mejoras, responde: []

IMPORTANTE: Se EXHAUSTIVO. Analiza turno por turno. Reporta tanto bugs evidentes como areas de mejora sutiles."""

    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2000,
            messages=[{"role": "user", "content": prompt}],
        )
        text = response.content[0].text.strip()

        # Parse JSON response
        if text.startswith("["):
            bugs = json.loads(text)
            return [
                {
                    "tipo": b.get("tipo", "CLAUDE_EVAL"),
                    "severidad": b.get("severidad", "ALTO"),
                    "detalle": f"[Claude] {b.get('detalle', '')}",
                    "categoria": "claude_eval",
                    "turno": b.get("turno", 0),
                }
                for b in bugs
            ]
        return []
    except Exception as e:
        print(f"    [CLAUDE ERROR] {e}")
        return []


# ============================================================
# Simulador Masivo
# ============================================================
class SimuladorMasivo:
    def __init__(self, verbose=False, gpt_eval=True, claude_eval=False):
        self.verbose = verbose
        self.gpt_eval = gpt_eval
        self.claude_eval = claude_eval
        self.resultados = []

    def run_scenario(self, escenario, idx=0, total=0):
        """Ejecuta un escenario y retorna resultado con bugs detectados."""
        eid = escenario["id"]
        nombre = escenario["nombre"]
        categoria = escenario["categoria"]

        idx_str = f"[{idx}/{total}] " if total else ""
        print(f"\n  {idx_str}#{eid} {nombre}")
        print(f"    Cat: {categoria} | Turnos: {len(escenario['turnos'])}")

        t0 = time.time()

        # 1. Crear agente real (sin sheets/twilio/elevenlabs)
        agente = AgenteVentas(
            contacto_info=escenario["contacto"],
            sheets_manager=None,
            resultados_manager=None,
            whatsapp_validator=None,
        )

        # 2. Tracker para bug detection
        tracker = CallEventTracker(
            call_sid=f"MASIVO_{eid}",
            bruce_id=f"M{eid:04d}",
            telefono=escenario["contacto"].get("telefono", ""),
        )
        tracker.simulador_texto = True  # FIX 910C: Skip INTERRUPCION in text sim

        # 3. Saludo inicial
        turnos_texto = []
        try:
            saludo = agente.iniciar_conversacion()
            tracker.emit("BRUCE_RESPONDE", {"texto": saludo})
            turnos_texto.append(f"Bruce: {saludo}")
            if self.verbose:
                print(f"    Bruce: {saludo}")
        except Exception as e:
            print(f"    [ERROR] iniciar_conversacion: {e}")
            saludo = ""

        # 4. Loop de turnos
        errores_check = []
        _farewell_phrases = [
            'muchas gracias por su tiempo', 'que tenga excelente dia',
            'que tenga buen dia', 'hasta pronto', 'hasta luego',
        ]
        call_ended = False

        for i, turno in enumerate(escenario["turnos"]):
            if call_ended:
                break

            cliente_msg = turno["cliente"]
            tracker.emit("CLIENTE_DICE", {"texto": cliente_msg})
            turnos_texto.append(f"Cliente [{i+1}]: {cliente_msg}")

            if self.verbose:
                print(f"    Cliente [{i+1}]: {cliente_msg}")

            try:
                respuesta = agente.procesar_respuesta(cliente_msg)
                if not respuesta:
                    respuesta = ""
            except Exception as e:
                respuesta = f"[ERROR: {e}]"
                print(f"    [ERROR] turno {i+1}: {e}")

            tracker.emit("BRUCE_RESPONDE", {"texto": respuesta})
            turnos_texto.append(f"Bruce [{i+1}]: {respuesta}")

            if self.verbose:
                print(f"    Bruce [{i+1}]: {respuesta}")

            # check_not validation
            for palabra in turno.get("check_not", []):
                if palabra.lower() in respuesta.lower():
                    error_msg = f"T{i+1}: Bruce dijo '{palabra}' (prohibido)"
                    errores_check.append(error_msg)
                    if self.verbose:
                        print(f"    ** CHECK FAIL: {error_msg}")

            # Detect farewell -> end call
            resp_lower = respuesta.lower()
            if any(fp in resp_lower for fp in _farewell_phrases):
                call_ended = True

        # 5. Bug detection: rule-based (siempre)
        duracion = time.time() - t0
        bugs = BugDetector.analyze(tracker)

        # 6. GPT eval (siempre por default)
        gpt_eval_bugs = []
        if self.gpt_eval:
            tracker.created_at = time.time() - 60  # Force min duration
            try:
                gpt_eval_bugs = _evaluar_con_gpt(tracker)
                if gpt_eval_bugs:
                    bugs.extend(gpt_eval_bugs)
            except Exception as e:
                print(f"    [GPT EVAL ERROR] {e}")

        # 7. Claude eval (opcional)
        claude_bugs = []
        if self.claude_eval:
            claude_bugs = _auditar_con_claude(tracker, "\n".join(turnos_texto))
            if claude_bugs:
                bugs.extend(claude_bugs)

        # 8. Check criticos -> PASS/FAIL
        bugs_criticos_encontrados = []
        for bug in bugs:
            if bug["tipo"] in escenario.get("bugs_criticos", []):
                bugs_criticos_encontrados.append(bug)

        passed = len(errores_check) == 0 and len(bugs_criticos_encontrados) == 0

        # 9. Output
        bugs_str = ", ".join(f"{b['tipo']}({b['severidad']})" for b in bugs) if bugs else "ninguno"
        status = "PASS" if passed else "FAIL"

        if not self.verbose:
            print(f"    Bugs: {bugs_str}")

        if errores_check:
            for err in errores_check:
                print(f"    ** {err}")
        if bugs_criticos_encontrados:
            for bc in bugs_criticos_encontrados:
                print(f"    ** CRITICO: {bc['tipo']} - {bc['detalle'][:80]}")

        # Color status
        print(f"    [{status}] ({duracion:.1f}s)")

        resultado = {
            "id": eid,
            "nombre": nombre,
            "categoria": categoria,
            "passed": passed,
            "bugs": bugs,
            "bugs_rule": [b for b in bugs if b.get("categoria") != "gpt_eval" and b.get("categoria") != "claude_eval"],
            "bugs_gpt": gpt_eval_bugs,
            "bugs_claude": claude_bugs,
            "bugs_criticos": bugs_criticos_encontrados,
            "errores_check": errores_check,
            "duracion": duracion,
            "turnos_texto": turnos_texto,
        }
        self.resultados.append(resultado)
        return resultado

    def run_all(self, scenario_id=None, category=None, quick=False):
        """Ejecuta escenarios filtrados."""
        print("=" * 70)
        print("  SIMULADOR MASIVO - Bruce W (65 escenarios, GPT real)")
        print("  Auditores: Rule-based" +
              (" + GPT eval" if self.gpt_eval else "") +
              (" + Claude Sonnet" if self.claude_eval else ""))
        print("=" * 70)

        escenarios = ESCENARIOS

        if scenario_id:
            escenarios = [e for e in escenarios if e["id"] == scenario_id]
        elif category:
            escenarios = [e for e in escenarios if e["categoria"] == category]
        elif quick:
            escenarios = [e for e in escenarios if e.get("critico", False)]

        if not escenarios:
            print("  No se encontraron escenarios con los filtros dados")
            return False

        print(f"  Escenarios a ejecutar: {len(escenarios)}")

        for i, esc in enumerate(escenarios, 1):
            self.run_scenario(esc, idx=i, total=len(escenarios))

        # ========== RESUMEN ==========
        self._print_summary()

        return all(r["passed"] for r in self.resultados)

    def _print_summary(self):
        """Imprime resumen completo."""
        total = len(self.resultados)
        passed = sum(1 for r in self.resultados if r["passed"])
        failed = total - passed

        print("\n" + "=" * 70)
        print(f"  RESULTADO FINAL: {passed}/{total} PASS" +
              (f", {failed} FAIL" if failed else " (100% limpio)"))
        print("=" * 70)

        # Failures detail
        if failed:
            print(f"\n  --- ESCENARIOS FALLIDOS ({failed}) ---")
            for r in self.resultados:
                if not r["passed"]:
                    bugs_str = ", ".join(f"{b['tipo']}" for b in r["bugs_criticos"])
                    checks_str = "; ".join(r["errores_check"][:3])
                    print(f"  #{r['id']} {r['nombre']}")
                    if bugs_str:
                        print(f"    Bugs criticos: {bugs_str}")
                    if checks_str:
                        print(f"    Check fails: {checks_str}")

        # Bug summary by type
        all_bugs = [b for r in self.resultados for b in r["bugs"]]
        if all_bugs:
            print(f"\n  --- BUGS TOTALES: {len(all_bugs)} ---")
            bug_counts = Counter(b["tipo"] for b in all_bugs)
            for tipo, count in bug_counts.most_common():
                print(f"    {tipo}: {count}")

        # Bug summary by category
        print(f"\n  --- BUGS POR CATEGORIA ---")
        cat_bugs = defaultdict(list)
        for r in self.resultados:
            for b in r["bugs"]:
                cat_bugs[r["categoria"]].append(b)
        for cat in sorted(cat_bugs.keys()):
            bugs = cat_bugs[cat]
            print(f"    {cat}: {len(bugs)} bugs")

        # GPT eval summary
        gpt_bugs = [b for r in self.resultados for b in r["bugs_gpt"]]
        if gpt_bugs:
            print(f"\n  --- GPT EVAL: {len(gpt_bugs)} bugs ---")
            for b in gpt_bugs[:10]:
                print(f"    [{b['severidad']}] {b['tipo']}: {b['detalle'][:70]}")

        # Claude summary
        if self.claude_eval:
            claude_bugs = [b for r in self.resultados for b in r["bugs_claude"]]
            print(f"\n  --- CLAUDE EVAL: {len(claude_bugs)} bugs ---")
            for b in claude_bugs[:10]:
                print(f"    [{b['severidad']}] {b['tipo']}: {b['detalle'][:70]}")

        # Cost estimate
        total_dur = sum(r["duracion"] for r in self.resultados)
        n = len(self.resultados)
        gpt_cost = n * 0.02 if self.gpt_eval else 0
        claude_cost = n * 0.05 if self.claude_eval else 0
        print(f"\n  Tiempo: {total_dur:.0f}s | Costo est: ~${n * 0.01 + gpt_cost + claude_cost:.2f} USD")

        # Pass rate
        pass_rate = (passed / total * 100) if total else 0
        print(f"  Tasa de exito: {pass_rate:.1f}%")

        if pass_rate >= 99:
            print("  TARGET 99% ALCANZADO!")
        elif pass_rate >= 90:
            print(f"  Faltan {failed} escenarios para 99%")

    def save_report(self, filepath):
        """Guarda reporte JSON con todos los resultados."""
        report = {
            "timestamp": datetime.now().isoformat(),
            "total_escenarios": len(self.resultados),
            "passed": sum(1 for r in self.resultados if r["passed"]),
            "failed": sum(1 for r in self.resultados if not r["passed"]),
            "pass_rate": sum(1 for r in self.resultados if r["passed"]) / max(len(self.resultados), 1) * 100,
            "auditores": {
                "rule_based": True,
                "gpt_eval": self.gpt_eval,
                "claude_eval": self.claude_eval,
            },
            "escenarios": [],
        }

        for r in self.resultados:
            report["escenarios"].append({
                "id": r["id"],
                "nombre": r["nombre"],
                "categoria": r["categoria"],
                "passed": r["passed"],
                "bugs": [{"tipo": b["tipo"], "severidad": b["severidad"], "detalle": b["detalle"]} for b in r["bugs"]],
                "errores_check": r["errores_check"],
                "duracion": round(r["duracion"], 2),
            })

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        print(f"\n  Reporte guardado: {filepath}")


# ============================================================
# Main
# ============================================================
def main():
    parser = argparse.ArgumentParser(description="Simulador Masivo Bruce W - 130 escenarios")
    parser.add_argument("--verbose", "-v", action="store_true", help="Respuestas completas")
    parser.add_argument("--scenario", "-s", type=int, help="Solo escenario N")
    parser.add_argument("--category", "-c", type=str, help="Solo categoria (ej: logica_rota)")
    parser.add_argument("--quick", "-q", action="store_true", help="Solo escenarios criticos")
    parser.add_argument("--list", "-l", action="store_true", help="Listar escenarios")
    parser.add_argument("--no-claude", action="store_true", help="Desactivar Claude Sonnet auditor (activo por default)")
    parser.add_argument("--no-gpt-eval", action="store_true", help="Desactivar GPT eval")
    parser.add_argument("--report", type=str, help="Guardar reporte JSON")

    args = parser.parse_args()

    if args.list:
        print(f"Escenarios disponibles: {len(ESCENARIOS)}\n")
        print("CATEGORIAS:")
        for cat, desc in sorted(CATEGORIAS.items()):
            n = sum(1 for e in ESCENARIOS if e["categoria"] == cat)
            print(f"  {cat} ({n}): {desc}")
        print(f"\nESCENARIOS:")
        for e in ESCENARIOS:
            critico = " *CRITICO*" if e.get("critico") else ""
            print(f"  [{e['id']:2d}] [{e['categoria']:20s}] {e['nombre']}{critico}")
        return

    sim = SimuladorMasivo(
        verbose=args.verbose,
        gpt_eval=not args.no_gpt_eval,
        claude_eval=not args.no_claude,
    )

    success = sim.run_all(
        scenario_id=args.scenario,
        category=args.category,
        quick=args.quick,
    )

    if args.report:
        sim.save_report(args.report)

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
