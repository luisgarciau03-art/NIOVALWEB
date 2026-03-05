#!/usr/bin/env python3
"""
Simulador End-to-End de llamadas Bruce W.

Simula llamadas completas texto-a-texto pasando por toda la pipeline real:
FSM -> Patterns -> GPT (real) -> Post-filters -> Bug Detector

Sin Twilio, sin ElevenLabs, sin Azure Speech. Solo texto.

Uso:
    python simulador_e2e.py                    # Todos los escenarios
    python simulador_e2e.py --verbose          # Con respuestas completas
    python simulador_e2e.py --scenario 1       # Solo escenario 1
    python simulador_e2e.py --list             # Listar escenarios
"""

import os
import sys
import time
import argparse

# FIX: Windows cp1252 no soporta caracteres Unicode como →
# Reconfigurar stdout/stderr para UTF-8 con fallback a reemplazo
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Asegurar path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Cargar .env antes de imports
from dotenv import load_dotenv
load_dotenv()

from agente_ventas import AgenteVentas
from bug_detector import CallEventTracker, BugDetector, _evaluar_con_gpt


# ============================================================
# Escenarios de test
# ============================================================
ESCENARIOS = [
    {
        "id": 1,
        "nombre": "Canal rechazado: WhatsApp -> correo -> telefono",
        "fix_target": "FIX 834+835",
        "contacto": {"nombre_negocio": "Ferreteria El Clavo", "telefono": "3312345678", "ciudad": "Guadalajara"},
        "turnos": [
            {"cliente": "Bueno, buen dia",
             "check_not": []},
            {"cliente": "Si, yo soy el encargado de compras",
             "check_not": []},
            {"cliente": "No tengo WhatsApp",
             "check_not": ["whatsapp", "WhatsApp"]},
            {"cliente": "Tampoco tengo correo",
             "check_not": ["whatsapp", "WhatsApp", "correo", "email"]},
            {"cliente": "El telefono es 33 12 34 56 78",
             "check_not": []},
        ],
        "bugs_criticos": ["DATO_NEGADO_REINSISTIDO", "LOOP"],
    },
    {
        "id": 2,
        "nombre": "Dato ya capturado: WhatsApp dado, no re-pedir",
        "fix_target": "FIX 836",
        "contacto": {"nombre_negocio": "Tornillos Express", "telefono": "5587654321", "ciudad": "CDMX"},
        "turnos": [
            {"cliente": "Bueno",
             "check_not": []},
            {"cliente": "Si, yo mero, soy el encargado",
             "check_not": []},
            {"cliente": "Si, por WhatsApp esta bien",
             "check_not": []},
            {"cliente": "Es el 55 87 65 43 21",
             "check_not": []},
            {"cliente": "Ok, gracias",
             "check_not": ["whatsapp", "WhatsApp"]},
        ],
        "bugs_criticos": ["GPT_LOGICA_ROTA"],
    },
    {
        "id": 3,
        "nombre": "Confirmaciones variadas: orale, perfecto, correcto",
        "fix_target": "FIX 837",
        "contacto": {"nombre_negocio": "Herramientas del Norte", "telefono": "8112345678", "ciudad": "Monterrey"},
        "turnos": [
            {"cliente": "Bueno, buen dia",
             "check_not": []},
            {"cliente": "Orale",
             "check_not": []},
            {"cliente": "Si, soy yo el encargado",
             "check_not": []},
            {"cliente": "Perfecto, mandalo por WhatsApp",
             "check_not": []},
            {"cliente": "33 45 67 89 01",
             "check_not": []},
        ],
        "bugs_criticos": [],
    },
    {
        "id": 4,
        "nombre": "Flujo exitoso completo (referencia limpia)",
        "fix_target": "Baseline",
        "contacto": {"nombre_negocio": "Ferreteria La Llave", "telefono": "5512345678", "ciudad": "CDMX"},
        "turnos": [
            {"cliente": "Buen dia",
             "check_not": []},
            {"cliente": "Si, yo soy",
             "check_not": []},
            {"cliente": "Claro, al WhatsApp",
             "check_not": []},
            {"cliente": "Es el 55 12 34 56 78",
             "check_not": []},
            {"cliente": "Si, esta bien, gracias",
             "check_not": []},
        ],
        "bugs_criticos": [],
    },
    {
        "id": 5,
        "nombre": "Rechazo total: todos canales -> ofrecer contacto Bruce",
        "fix_target": "FIX 834+835",
        "contacto": {"nombre_negocio": "Cerrajeria Segura", "telefono": "3398765432", "ciudad": "Guadalajara"},
        "turnos": [
            {"cliente": "Bueno",
             "check_not": []},
            {"cliente": "No esta el encargado, salio a comer",
             "check_not": []},
            {"cliente": "No tengo WhatsApp del encargado",
             "check_not": ["whatsapp", "WhatsApp"]},
            {"cliente": "Tampoco tengo correo de el",
             "check_not": ["whatsapp", "WhatsApp", "correo", "email"]},
            {"cliente": "No, solo telefono fijo aqui en el negocio",
             "check_not": []},
        ],
        "bugs_criticos": ["LOOP", "DATO_NEGADO_REINSISTIDO"],
    },
    {
        "id": 6,
        "nombre": "No interes rapido: rechazo en pitch",
        "fix_target": "Baseline",
        "contacto": {"nombre_negocio": "Taller Mecanico Perez", "telefono": "2212345678", "ciudad": "Puebla"},
        "turnos": [
            {"cliente": "Bueno",
             "check_not": []},
            {"cliente": "No gracias, no nos interesa",
             "check_not": []},
        ],
        "bugs_criticos": [],
    },
    {
        "id": 7,
        "nombre": "Encargado ausente con callback",
        "fix_target": "Baseline",
        "contacto": {"nombre_negocio": "Ferreteria El Martillo", "telefono": "4412345678", "ciudad": "Queretaro"},
        "turnos": [
            {"cliente": "Bueno, buen dia",
             "check_not": []},
            {"cliente": "No, no esta, viene mas tarde como a las 4",
             "check_not": []},
            {"cliente": "Si, a las 4 de la tarde",
             "check_not": []},
        ],
        "bugs_criticos": [],
    },
    {
        "id": 8,
        "nombre": "FIX 873: WhatsApp rechazado - no re-pedir",
        "fix_target": "FIX 873",
        "contacto": {"nombre_negocio": "Tlapaleria La Paloma", "telefono": "3312345679", "ciudad": "Guadalajara"},
        "turnos": [
            {"cliente": "Bueno",
             "check_not": []},
            {"cliente": "Si, yo soy el encargado",
             "check_not": []},
            {"cliente": "No tengo whatsapp",
             "check_not": []},
            {"cliente": "Si, el correo es ferreteria@gmail.com",
             "check_not": []},
            {"cliente": "Orale, gracias",
             "check_not": ["whatsapp", "WhatsApp"]},  # No re-pedir WhatsApp al final
        ],
        "bugs_criticos": ["DATO_NEGADO_REINSISTIDO"],
    },
    {
        "id": 9,
        "nombre": "FIX 870/874: No repetir Entiendo/Perfecto consecutivos",
        "fix_target": "FIX 870/874",
        "contacto": {"nombre_negocio": "Ferreteria Central", "telefono": "3398765433", "ciudad": "Guadalajara"},
        "turnos": [
            {"cliente": "Bueno",
             "check_not": []},
            {"cliente": "Si, soy yo",
             "check_not": []},
            {"cliente": "Aha",
             "check_not": []},
            {"cliente": "Mhm",
             "check_not": []},
            {"cliente": "Si, mandame por WhatsApp",
             "check_not": []},
            {"cliente": "33 98 76 54 33",
             "check_not": []},
        ],
        "bugs_criticos": ["LOOP"],
    },
    {
        "id": 10,
        "nombre": "Flujo IVR / conmutador (no confundir con cliente)",
        "fix_target": "FIX 735",
        "contacto": {"nombre_negocio": "Grupo Industrial SA", "telefono": "5512345670", "ciudad": "CDMX"},
        "turnos": [
            {"cliente": "Grupo Industrial, buenos dias, en que le puedo ayudar",
             "check_not": []},
            {"cliente": "Le comunico",
             "check_not": []},
            {"cliente": "Buenos dias, si, soy yo el encargado",
             "check_not": []},
            {"cliente": "Por WhatsApp esta bien, el numero es 55 12 34 56 70",
             "check_not": []},
        ],
        "bugs_criticos": [],
    },
    {
        "id": 11,
        "nombre": "FIX 871: Pregunta ubicacion repetida -> pivot a catalogo",
        "fix_target": "FIX 871",
        "contacto": {"nombre_negocio": "Ferreteria Norte", "telefono": "8112345670", "ciudad": "Monterrey"},
        "turnos": [
            {"cliente": "Buen dia",
             "check_not": []},
            {"cliente": "Si, soy yo",
             "check_not": []},
            {"cliente": "De donde hablan ustedes",
             "check_not": []},
            {"cliente": "Ah, y donde estan ubicados exactamente",
             "check_not": []},
            {"cliente": "Ok, manden por WhatsApp el catalogo",
             "check_not": []},
            {"cliente": "33 98 76 54 33",
             "check_not": []},
        ],
        "bugs_criticos": [],
    },
    # ---- Escenarios 12-25: Cobertura ampliada ----
    {
        "id": 12,
        "nombre": "Numero equivocado: cliente dice no es aqui",
        "fix_target": "FIX 869E",
        "contacto": {"nombre_negocio": "Electronica Lopez", "telefono": "3312349999", "ciudad": "Guadalajara"},
        "turnos": [
            {"cliente": "Bueno",
             "check_not": []},
            {"cliente": "No, aqui no es ninguna ferreteria, esta equivocado",
             "check_not": []},
        ],
        "bugs_criticos": ["LOOP", "PREGUNTA_REPETIDA"],
    },
    {
        "id": 13,
        "nombre": "Pregunta por precios antes de dar contacto",
        "fix_target": "Baseline",
        "contacto": {"nombre_negocio": "Ferreteria San Juan", "telefono": "4421234567", "ciudad": "Queretaro"},
        "turnos": [
            {"cliente": "Bueno, buen dia",
             "check_not": []},
            {"cliente": "Si, yo soy el encargado",
             "check_not": []},
            {"cliente": "Y cuanto cuesta su producto? Cuales son los precios?",
             "check_not": []},
            {"cliente": "Ah ok, mandame el catalogo por WhatsApp",
             "check_not": []},
            {"cliente": "44 21 23 45 67",
             "check_not": []},
        ],
        "bugs_criticos": [],
    },
    {
        "id": 14,
        "nombre": "Ya tengo proveedor: rechazo por competencia",
        "fix_target": "FIX 844/850",
        "contacto": {"nombre_negocio": "Tornillos y Mas", "telefono": "8187654321", "ciudad": "Monterrey"},
        "turnos": [
            {"cliente": "Bueno",
             "check_not": []},
            {"cliente": "Si, soy el encargado",
             "check_not": []},
            {"cliente": "No gracias, ya tengo proveedor, ya estamos surtidos",
             "check_not": []},
        ],
        "bugs_criticos": ["PREGUNTA_REPETIDA", "LOOP"],
    },
    {
        "id": 15,
        "nombre": "Transferencia a encargado: un momento, le paso",
        "fix_target": "FIX 860",
        "contacto": {"nombre_negocio": "Materiales El Sol", "telefono": "2221234567", "ciudad": "Puebla"},
        "turnos": [
            {"cliente": "Bueno, buen dia",
             "check_not": []},
            {"cliente": "Si, un momento, le paso al encargado",
             "check_not": []},
            {"cliente": "Bueno, si, soy el encargado de compras",
             "check_not": []},
            {"cliente": "Si, mandame tu catalogo por WhatsApp",
             "check_not": []},
            {"cliente": "22 21 23 45 67",
             "check_not": []},
        ],
        "bugs_criticos": ["PITCH_REPETIDO", "LOOP"],
    },
    {
        "id": 16,
        "nombre": "Dictado de correo electronico completo",
        "fix_target": "FIX 718/733",
        "contacto": {"nombre_negocio": "Ferreteria El Clavo Dorado", "telefono": "3312340001", "ciudad": "Guadalajara"},
        "turnos": [
            {"cliente": "Bueno",
             "check_not": []},
            {"cliente": "Si, yo soy el encargado",
             "check_not": []},
            {"cliente": "No tengo WhatsApp",
             "check_not": ["whatsapp", "WhatsApp"]},
            {"cliente": "ferreteria arroba gmail punto com",
             "check_not": []},
            {"cliente": "Si, correcto, gracias",
             "check_not": []},
        ],
        "bugs_criticos": ["DATO_NEGADO_REINSISTIDO"],
    },
    {
        "id": 17,
        "nombre": "Cliente ocupado, pide que llamen despues",
        "fix_target": "FIX 849",
        "contacto": {"nombre_negocio": "Pinturas del Valle", "telefono": "6621234567", "ciudad": "Hermosillo"},
        "turnos": [
            {"cliente": "Bueno",
             "check_not": []},
            {"cliente": "Estoy ocupado ahorita, puede llamar mas tarde?",
             "check_not": []},
            {"cliente": "Como a las 3 de la tarde",
             "check_not": []},
        ],
        "bugs_criticos": ["LOOP"],
    },
    {
        "id": 18,
        "nombre": "Otra sucursal: redirige a otra ubicacion",
        "fix_target": "FIX 866A",
        "contacto": {"nombre_negocio": "Cadena Ferretera Nacional", "telefono": "5598765432", "ciudad": "CDMX"},
        "turnos": [
            {"cliente": "Bueno, buen dia",
             "check_not": []},
            {"cliente": "Aqui no manejamos eso, tiene que hablar a la sucursal de Monterrey",
             "check_not": []},
        ],
        "bugs_criticos": ["PREGUNTA_REPETIDA", "LOOP"],
    },
    {
        "id": 19,
        "nombre": "Dictado numero parcial: 3 digitos, pausa, completa",
        "fix_target": "FIX 714/847B",
        "contacto": {"nombre_negocio": "Ferreteria Los Pinos", "telefono": "3312340002", "ciudad": "Guadalajara"},
        "turnos": [
            {"cliente": "Bueno",
             "check_not": []},
            {"cliente": "Si, soy el de compras",
             "check_not": []},
            {"cliente": "Si, al WhatsApp",
             "check_not": []},
            {"cliente": "33 12",
             "check_not": []},
            {"cliente": "34 56 78",
             "check_not": []},
        ],
        "bugs_criticos": ["DICTADO_INTERRUMPIDO"],
    },
    {
        "id": 20,
        "nombre": "Cliente pregunta quien llama (identity question)",
        "fix_target": "FIX 738/878",
        "contacto": {"nombre_negocio": "Comercial Azteca", "telefono": "5512340003", "ciudad": "CDMX"},
        "turnos": [
            {"cliente": "Bueno",
             "check_not": []},
            {"cliente": "De donde me habla? Quien es usted?",
             "check_not": []},
            {"cliente": "Ah ok, y que venden?",
             "check_not": []},
            {"cliente": "Si, mandeme el catalogo al WhatsApp",
             "check_not": []},
            {"cliente": "55 12 34 00 03",
             "check_not": []},
        ],
        "bugs_criticos": ["PREGUNTA_REPETIDA"],
    },
    {
        "id": 21,
        "nombre": "Encargado llega mas tarde sin hora especifica",
        "fix_target": "FIX 869A",
        "contacto": {"nombre_negocio": "Herramientas del Bajio", "telefono": "4771234567", "ciudad": "Leon"},
        "turnos": [
            {"cliente": "Bueno, buen dia",
             "check_not": []},
            {"cliente": "No, no esta. No se a que hora viene",
             "check_not": []},
            {"cliente": "No se, la verdad no tengo idea",
             "check_not": []},
        ],
        "bugs_criticos": ["LOOP"],
    },
    {
        "id": 22,
        "nombre": "Cliente acepta catalogo por correo (no WhatsApp)",
        "fix_target": "FIX 873",
        "contacto": {"nombre_negocio": "Industrial del Pacifico", "telefono": "3221234567", "ciudad": "Puerto Vallarta"},
        "turnos": [
            {"cliente": "Bueno",
             "check_not": []},
            {"cliente": "Si, yo soy el encargado de compras",
             "check_not": []},
            {"cliente": "No manejo WhatsApp",
             "check_not": ["whatsapp", "WhatsApp"]},
            {"cliente": "Es compras arroba industrial punto com",
             "check_not": ["whatsapp", "WhatsApp"]},
            {"cliente": "Si, esta bien, gracias",
             "check_not": ["whatsapp", "WhatsApp"]},
        ],
        "bugs_criticos": ["DATO_NEGADO_REINSISTIDO"],
    },
    {
        "id": 23,
        "nombre": "Quejas sobre llamada: ya no queremos que llamen",
        "fix_target": "FIX 869B",
        "contacto": {"nombre_negocio": "Electricos del Centro", "telefono": "3312340004", "ciudad": "Guadalajara"},
        "turnos": [
            {"cliente": "Bueno",
             "check_not": []},
            {"cliente": "Ya nos han hablado muchas veces, ya no queremos que llamen",
             "check_not": []},
        ],
        "bugs_criticos": ["LOOP", "PREGUNTA_REPETIDA"],
    },
    {
        "id": 24,
        "nombre": "Flujo largo: pitch, preguntas, objeciones, cierre",
        "fix_target": "Baseline completo",
        "contacto": {"nombre_negocio": "Mega Ferreteria", "telefono": "3312340005", "ciudad": "Guadalajara"},
        "turnos": [
            {"cliente": "Bueno, buen dia",
             "check_not": []},
            {"cliente": "Si, soy yo el encargado",
             "check_not": []},
            {"cliente": "Y que tipo de productos manejan exactamente?",
             "check_not": []},
            {"cliente": "Y a que precios?",
             "check_not": []},
            {"cliente": "Mmm, dejame pensarlo",
             "check_not": []},
            {"cliente": "Bueno, si, mandame el catalogo por WhatsApp",
             "check_not": []},
            {"cliente": "Es el 33 12 34 00 05",
             "check_not": []},
            {"cliente": "Si, correcto, gracias",
             "check_not": []},
        ],
        "bugs_criticos": ["LOOP", "PREGUNTA_REPETIDA", "PITCH_REPETIDO"],
    },
    {
        "id": 25,
        "nombre": "FIX 880: Eco de audio - no capturar numero propio Bruce",
        "fix_target": "FIX 880",
        "contacto": {"nombre_negocio": "Tlapaleria La Estrella", "telefono": "3312340006", "ciudad": "Guadalajara"},
        "turnos": [
            {"cliente": "Bueno",
             "check_not": []},
            {"cliente": "Si, yo soy",
             "check_not": []},
            {"cliente": "Al WhatsApp",
             "check_not": []},
            {"cliente": "66 23 53 18 04",
             "check_not": []},
            {"cliente": "No, ese no es, el mio es 33 12 34 00 06",
             "check_not": []},
        ],
        "bugs_criticos": ["LOOP"],
    },
    # ============================================================
    # ESCENARIOS 26-30: STT GARBLED (texto distorsionado/duplicado)
    # Simulan lo que Azure/Deepgram realmente produce en produccion
    # ============================================================
    {
        "id": 26,
        "nombre": "STT Garbled: Texto duplicado - frases repetidas",
        "fix_target": "FIX 885",
        "contacto": {"nombre_negocio": "Ferreteria Test STT", "telefono": "3312340007", "ciudad": "Guadalajara"},
        "turnos": [
            {"cliente": "Hola, buen dia. Que dice? Buenos dias. Si, con Hola, buen dia. Que dice? Buenos dias.",
             "check_not": []},
            {"cliente": "Si, si soy el encargado. Si, si soy el encargado de compras.",
             "check_not": []},
            {"cliente": "Si, mandalo por WhatsApp. Si, mandalo por WhatsApp por favor.",
             "check_not": []},
            {"cliente": "Es el 33 12 34 56 78",
             "check_not": []},
        ],
        "bugs_criticos": ["LOOP", "PREGUNTA_REPETIDA"],
    },
    {
        "id": 27,
        "nombre": "STT Garbled: Encargado ausente con palabras distorsionadas",
        "fix_target": "FIX 886",
        "contacto": {"nombre_negocio": "Tlapaleria STT Test", "telefono": "3312340008", "ciudad": "Guadalajara"},
        "turnos": [
            {"cliente": "Bueno, si digame",
             "check_not": []},
            {"cliente": "Estan en sobra de comida, estan en sobra de comida, si gustas marcar mas",
             "check_not": ["whatsapp", "WhatsApp"]},
            # Turno 3: garbled pero con "en 1 hora" → callback detectado por FIX 882
            {"cliente": "En una hora regresa el encargado",
             "check_not": []},
        ],
        "bugs_criticos": ["LOOP", "GPT_LOGICA_ROTA"],
    },
    {
        "id": 28,
        "nombre": "STT Garbled: De parte de quien con eco",
        "fix_target": "FIX 883+886",
        "contacto": {"nombre_negocio": "Materiales STT", "telefono": "3312340009", "ciudad": "Guadalajara"},
        "turnos": [
            {"cliente": "Buenas tardes, digame.",
             "check_not": []},
            {"cliente": "Aja. De parte de quien, disculpe? De parte de quien me habla?",
             "check_not": []},
            # Manager absent → Bruce asks for alt contact (correct behavior)
            {"cliente": "No, no esta. No, no esta el encargado.",
             "check_not": []},
        ],
        "bugs_criticos": ["LOOP", "PREGUNTA_REPETIDA"],
    },
    {
        "id": 29,
        "nombre": "STT Garbled: Digame + fijese que no (negacion mezclada)",
        "fix_target": "FIX 884B",
        "contacto": {"nombre_negocio": "Herramientas STT", "telefono": "3312340010", "ciudad": "Guadalajara"},
        "turnos": [
            {"cliente": "Si, digame",
             "check_not": []},
            {"cliente": "Digame. Fijese que no. No tenemos negocio de ese tipo.",
             "check_not": ["whatsapp", "WhatsApp"]},
        ],
        "bugs_criticos": ["GPT_LOGICA_ROTA"],
    },
    {
        "id": 30,
        "nombre": "STT Garbled: Numero con concatenacion de parciales",
        "fix_target": "FIX 885",
        "contacto": {"nombre_negocio": "Electrica STT", "telefono": "3312340011", "ciudad": "Guadalajara"},
        "turnos": [
            {"cliente": "Bueno",
             "check_not": []},
            {"cliente": "Si, yo mero soy. Si, yo mero.",
             "check_not": []},
            {"cliente": "Si claro, al WhatsApp",
             "check_not": []},
            {"cliente": "Permiteme un segundo. Es el seis catorce dos ochenta y seis. Permitame un segundo. Es el seis catorce dos ochenta y seis veintiuno.",
             "check_not": []},
        ],
        "bugs_criticos": ["LOOP", "DICTADO_INTERRUMPIDO"],
    },
]


# ============================================================
# Simulador
# ============================================================
class SimuladorE2E:
    def __init__(self, verbose=False, gpt_eval=False):
        self.verbose = verbose
        self.gpt_eval = gpt_eval
        self.resultados = []

    def run_scenario(self, escenario):
        """Ejecuta un escenario completo y retorna resultado."""
        eid = escenario["id"]
        nombre = escenario["nombre"]
        fix_target = escenario["fix_target"]

        print(f"\n  [{eid}/{len(ESCENARIOS)}] {nombre}")
        print(f"    Target: {fix_target}")

        t0 = time.time()

        # 1. Crear agente real
        agente = AgenteVentas(
            contacto_info=escenario["contacto"],
            sheets_manager=None,
            resultados_manager=None,
            whatsapp_validator=None,
        )

        # 2. Crear tracker para bug detection
        tracker = CallEventTracker(
            call_sid=f"SIM_E2E_{eid}",
            bruce_id=f"SIM{eid:04d}",
            telefono=escenario["contacto"].get("telefono", ""),
        )

        # 3. Saludo inicial de Bruce
        try:
            saludo = agente.iniciar_conversacion()
            tracker.emit("BRUCE_RESPONDE", {"texto": saludo})
            if self.verbose:
                print(f"    Bruce: {saludo}")
        except Exception as e:
            print(f"    [ERROR] iniciar_conversacion: {e}")
            saludo = ""

        # 4. Loop de turnos
        errores_check = []
        for i, turno in enumerate(escenario["turnos"]):
            cliente_msg = turno["cliente"]
            tracker.emit("CLIENTE_DICE", {"texto": cliente_msg})

            if self.verbose:
                print(f"    Cliente [{i+1}]: {cliente_msg}")

            try:
                respuesta = agente.procesar_respuesta(cliente_msg)
                if not respuesta:
                    respuesta = ""
            except Exception as e:
                respuesta = f"[ERROR: {e}]"
                print(f"    [ERROR] procesar_respuesta turno {i+1}: {e}")

            tracker.emit("BRUCE_RESPONDE", {"texto": respuesta})

            if self.verbose:
                print(f"    Bruce [{i+1}]: {respuesta}")

            # Validar check_not (palabras que NO deben aparecer en la respuesta)
            for palabra in turno.get("check_not", []):
                if palabra.lower() in respuesta.lower():
                    error_msg = f"Turno {i+1}: Bruce dijo '{palabra}' (NO deberia)"
                    errores_check.append(error_msg)
                    if self.verbose:
                        print(f"    ** CHECK FAIL: {error_msg}")

        # 5. Analizar bugs (rule-based siempre, GPT eval opcional)
        duracion = time.time() - t0
        bugs = BugDetector.analyze(tracker)

        # FIX 892: GPT eval opcional para detectar bugs semánticos
        gpt_eval_bugs = []
        if self.gpt_eval:
            # Forzar duración mínima para que GPT eval no se salte por "ultra-corta"
            tracker.created_at = time.time() - 60
            try:
                gpt_eval_bugs = _evaluar_con_gpt(tracker)
                bugs.extend(gpt_eval_bugs)
            except Exception as e:
                print(f"    [GPT EVAL ERROR] {e}")

        # 6. Filtrar bugs criticos que NO deberian aparecer
        bugs_criticos_encontrados = []
        for bug in bugs:
            if bug["tipo"] in escenario.get("bugs_criticos", []):
                bugs_criticos_encontrados.append(bug)

        # 7. Determinar PASS/FAIL
        passed = len(errores_check) == 0 and len(bugs_criticos_encontrados) == 0

        # 8. Mostrar resultado
        bugs_str = ", ".join(f"{b['tipo']}({b['severidad']})" for b in bugs) if bugs else "ninguno"
        status = "PASS" if passed else "FAIL"

        if not self.verbose:
            print(f"    Bugs: {bugs_str}")

        if errores_check:
            for err in errores_check:
                print(f"    ** {err}")

        if bugs_criticos_encontrados:
            for bc in bugs_criticos_encontrados:
                print(f"    ** BUG CRITICO: {bc['tipo']} - {bc['detalle'][:80]}")

        print(f"    [{status}] ({duracion:.1f}s)")

        resultado = {
            "id": eid,
            "nombre": nombre,
            "passed": passed,
            "bugs": bugs,
            "bugs_criticos": bugs_criticos_encontrados,
            "errores_check": errores_check,
            "duracion": duracion,
        }
        self.resultados.append(resultado)
        return resultado

    def run_all(self, scenario_id=None):
        """Ejecuta todos los escenarios (o uno especifico)."""
        print("=" * 60)
        print("  SIMULADOR E2E - Bruce W (GPT real, sin Twilio)")
        print("=" * 60)

        escenarios = ESCENARIOS
        if scenario_id:
            escenarios = [e for e in ESCENARIOS if e["id"] == scenario_id]
            if not escenarios:
                print(f"  Escenario {scenario_id} no encontrado")
                return

        for esc in escenarios:
            self.run_scenario(esc)

        # Resumen
        total = len(self.resultados)
        passed = sum(1 for r in self.resultados if r["passed"])
        failed = total - passed

        print("\n" + "=" * 60)
        print(f"  RESULTADO: {passed}/{total} PASS" + (f", {failed} FAIL" if failed else ""))
        print("=" * 60)

        # Bug summary
        all_bugs = []
        for r in self.resultados:
            all_bugs.extend(r["bugs"])

        if all_bugs:
            from collections import Counter
            bug_counts = Counter(b["tipo"] for b in all_bugs)
            print(f"\n  Bugs totales: {len(all_bugs)}")
            for tipo, count in bug_counts.most_common():
                print(f"    {tipo}: {count}")

        # GPT eval summary
        if self.gpt_eval:
            gpt_bugs = [b for r in self.resultados for b in r["bugs"] if b.get("categoria") == "gpt_eval"]
            if gpt_bugs:
                print(f"\n  GPT Eval bugs: {len(gpt_bugs)}")
                for b in gpt_bugs:
                    print(f"    [{b['severidad']}] {b['tipo']}: {b['detalle'][:80]}")
            else:
                print(f"\n  GPT Eval: 0 bugs detectados (OK)")

        # Costo estimado
        total_duracion = sum(r["duracion"] for r in self.resultados)
        print(f"\n  Tiempo total: {total_duracion:.1f}s")
        gpt_cost = len(escenarios) * 0.02 if self.gpt_eval else 0
        print(f"  Costo estimado: ~${len(escenarios) * 0.01 + gpt_cost:.2f} USD (GPT-4.1-mini)")

        return failed == 0


def main():
    parser = argparse.ArgumentParser(description="Simulador E2E Bruce W")
    parser.add_argument("--verbose", "-v", action="store_true", help="Mostrar respuestas completas")
    parser.add_argument("--scenario", "-s", type=int, help="Ejecutar solo escenario N")
    parser.add_argument("--list", "-l", action="store_true", help="Listar escenarios")
    parser.add_argument("--gpt-eval", action="store_true", help="Ejecutar GPT eval post-llamada (detecta bugs semanticos)")
    args = parser.parse_args()

    if args.list:
        print("Escenarios disponibles:")
        for e in ESCENARIOS:
            print(f"  [{e['id']}] {e['nombre']} ({e['fix_target']})")
        return

    sim = SimuladorE2E(verbose=args.verbose, gpt_eval=args.gpt_eval)
    success = sim.run_all(scenario_id=args.scenario)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
