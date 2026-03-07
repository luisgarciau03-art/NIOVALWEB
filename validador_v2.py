#!/usr/bin/env python3
"""
Validador V2 - Comparativa fine-tuning v1 vs v2 para Bruce W.

Fases:
  1. Correr 67 escenarios de simulador_e2e.py contra modelo activo
  2. Correr 150 escenarios out-of-sample nuevos contra modelo activo
  3. Analizar bugs con BugDetector (rule-based)
  4. Generar reporte comparativo vs baseline (audit pre-finetune)

Uso:
    python validador_v2.py                  # Todo (fases 1+2)
    python validador_v2.py --fase 1         # Solo simulador_e2e (67 escenarios)
    python validador_v2.py --fase 2         # Solo 150 nuevos out-of-sample
    python validador_v2.py --verbose        # Ver respuestas de Bruce
    python validador_v2.py --reporte        # Solo mostrar ultimo reporte JSON
"""

import os
import sys
import json
import time
import argparse
from collections import Counter

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
from bug_detector import CallEventTracker, BugDetector

# ============================================================
# Baseline de referencia (auditoria pre-finetune, 150 sinteticos)
# ============================================================
BASELINE = {
    "descripcion": "Auditoria Claude Sonnet pre-finetune (sinteticos v1, 150 convs)",
    "total_convs": 150,
    "bugs_reales": 16,      # bugs genuinos detectados en auditoria cualitativa
    "fps": 9,               # false positives en bug_detector v1
    "tasa_bugs": 16 / 150,  # 10.7%
    "bugs_por_tipo": {
        "NO_DA_DATOS_RECADO": 3,
        "CONFIRMACION_FALSA": 5,
        "LOOP": 4,
        "GPT_LOGICA_ROTA": 4,
    },
}

# ============================================================
# 150 escenarios out-of-sample (NO usados en entrenamiento)
# Organizados en 15 grupos de 10 variaciones cada uno
# ============================================================
ESCENARIOS_OOS = []

def _make(gid, vid, nombre, contacto, turnos, bugs_criticos=None):
    ESCENARIOS_OOS.append({
        "id": f"OOS-{gid:02d}-{vid:02d}",
        "nombre": nombre,
        "contacto": contacto,
        "turnos": turnos,
        "bugs_criticos": bugs_criticos or [],
    })

# --- Grupo 1: Happy path completo (WhatsApp) ---
negocios_g1 = [
    ("Ferreteria Omega", "3312340001", "Guadalajara"),
    ("Tlapaleria Don Goyo", "5512340002", "CDMX"),
    ("Herramientas Plus", "8112340003", "Monterrey"),
    ("Materiales El Grullo", "3312340004", "Guadalajara"),
    ("Suministros GEST", "5512340005", "CDMX"),
    ("Ferreteria La Tuerca", "3312340006", "Guadalajara"),
    ("Distribuidora HDL", "6641234007", "Tijuana"),
    ("Abarrotes Roma", "9512340008", "Oaxaca"),
    ("Herramientas Pronto", "4441234009", "Aguascalientes"),
    ("El Tornillo Magico", "3312340010", "Guadalajara"),
]
for i, (neg, tel, ciudad) in enumerate(negocios_g1, 1):
    frases = [
        ["Bueno", "Si yo soy el encargado", "Si manda el catalogo por WhatsApp", f"Es el {tel}", "Muchas gracias"],
        ["Buen dia", "Si, soy yo", "Por WhatsApp esta bien", f"Anota el {tel}", "Ok perfecto"],
        ["Digame", "Si yo mero", "Orale, por WhatsApp", f"El numero es {tel}", "Listo"],
        ["Hola", "Si, con el encargado habla", "Al WhatsApp si", f"Son el {tel}", "Gracias"],
        ["Buenos dias", "Si, yo soy el dueno", "Al WhatsApp mandalo", f"Es {tel}", "Bien, gracias"],
        ["Bueno, buenos dias", "Si aqui el encargado", "Si al WhatsApp perfecto", f"El {tel}", "Que este bien"],
        ["Diga", "Si yo soy", "Claro por WhatsApp", f"El numero {tel}", "De acuerdo gracias"],
        ["Bueno", "Si, conmigo hablas", "Al WhatsApp mandalo", f"{tel}", "Listo, gracias"],
        ["Alo", "Si, soy yo el encargado de compras", "Por WhatsApp si", f"El {tel} es", "Perfecto, gracias"],
        ["Bueno si", "Si aqui encargado", "Si manda por WhatsApp", f"El numero es {tel}", "Ok, bye"],
    ]
    _make(1, i, f"Happy path WhatsApp - {neg}", {"nombre_negocio": neg, "telefono": tel, "ciudad": ciudad}, [{"cliente": t, "check_not": []} for t in frases[i-1]])

# --- Grupo 2: WhatsApp rechazado -> correo aceptado ---
negocios_g2 = [
    ("Plasticos del Sur", "3312341001", "Guadalajara"),
    ("Materiales Norte", "8112341002", "Monterrey"),
    ("Ferreteria Juarez", "5512341003", "CDMX"),
    ("Taller Industrial", "3312341004", "Guadalajara"),
    ("Dist. El Progreso", "7712341005", "Sonora"),
    ("Construcciones RM", "3312341006", "Guadalajara"),
    ("Ferreteria Santos", "4812341007", "Veracruz"),
    ("El Clavo Dorado", "3312341008", "Guadalajara"),
    ("Herramientas Valle", "5512341009", "CDMX"),
    ("Materiales Cielos", "3312341010", "Guadalajara"),
]
correos = [
    "plasticos@gmail.com", "materiales@hotmail.com", "ferreteria@yahoo.com",
    "taller@gmail.com", "progreso@hotmail.com", "construcciones@gmail.com",
    "santos@outlook.com", "clavo@gmail.com", "herramientas@yahoo.com", "cielos@gmail.com",
]
for i, ((neg, tel, ciudad), correo) in enumerate(zip(negocios_g2, correos), 1):
    turnos = [
        {"cliente": "Bueno", "check_not": []},
        {"cliente": "Si yo soy el encargado", "check_not": []},
        {"cliente": "No tengo WhatsApp", "check_not": ["whatsapp", "WhatsApp"]},
        {"cliente": f"Si, al correo. Es {correo}", "check_not": []},
        {"cliente": "Muy bien, gracias", "check_not": ["whatsapp", "WhatsApp"]},
    ]
    _make(2, i, f"WA rechazado -> correo - {neg}", {"nombre_negocio": neg, "telefono": tel, "ciudad": ciudad}, turnos, ["DATO_NEGADO_REINSISTIDO"])

# --- Grupo 3: WhatsApp rechazado -> telefono aceptado ---
negocios_g3 = [
    ("Ferreteria El Rayo", "3312342001", "Guadalajara"),
    ("Tornillos Express", "5512342002", "CDMX"),
    ("Dist. Herramientas", "8112342003", "Monterrey"),
    ("El Fierro Solido", "3312342004", "Guadalajara"),
    ("Materiales El Sol", "6641342005", "Tijuana"),
    ("Tlapaleria Juarez", "3312342006", "Guadalajara"),
    ("Suministros Centro", "5512342007", "CDMX"),
    ("El Tornillo Azul", "3312342008", "Guadalajara"),
    ("Herramientas Roma", "4441342009", "Aguascalientes"),
    ("Materiales Omega", "3312342010", "Guadalajara"),
]
for i, (neg, tel, ciudad) in enumerate(negocios_g3, 1):
    turnos = [
        {"cliente": "Bueno", "check_not": []},
        {"cliente": "Si yo soy", "check_not": []},
        {"cliente": "No uso WhatsApp", "check_not": ["whatsapp", "WhatsApp"]},
        {"cliente": "Tampoco tengo correo electronico", "check_not": ["whatsapp", "WhatsApp", "correo"]},
        {"cliente": f"Solo tengo este telefono, el {tel}", "check_not": []},
    ]
    _make(3, i, f"WA+correo rechazados -> tel - {neg}", {"nombre_negocio": neg, "telefono": tel, "ciudad": ciudad}, turnos, ["DATO_NEGADO_REINSISTIDO", "LOOP"])

# --- Grupo 4: Happy path correo (no WhatsApp preference) ---
correos_g4 = [
    "ventas@ferreteriasol.com", "compras@materialesrey.mx", "info@tornillosnorte.com",
    "almacen@distribuidoramex.com", "gerencia@ferreteriaplus.mx", "admin@herramientasgdl.com",
    "contacto@tiendaindustrial.mx", "ventas@sumindustrial.com", "compras@ferremundo.mx",
    "info@materialesintegral.com",
]
negocios_g4 = [
    ("Ferreteria Sol", "3312343001", "Guadalajara"),
    ("Materiales Rey", "5512343002", "CDMX"),
    ("Tornillos Norte", "8112343003", "Monterrey"),
    ("Distribuidora Mex", "3312343004", "Guadalajara"),
    ("Ferreteria Plus", "4412343005", "Queretaro"),
    ("Herramientas GDL", "3312343006", "Guadalajara"),
    ("Tienda Industrial", "5512343007", "CDMX"),
    ("Sum. Industrial", "3312343008", "Guadalajara"),
    ("Ferremundo", "7712343009", "Sonora"),
    ("Materiales Integral", "3312343010", "Guadalajara"),
]
for i, ((neg, tel, ciudad), correo) in enumerate(zip(negocios_g4, correos_g4), 1):
    turnos = [
        {"cliente": "Bueno", "check_not": []},
        {"cliente": "Si soy yo el encargado", "check_not": []},
        {"cliente": f"Mandalo al correo, es {correo}", "check_not": []},
        {"cliente": "Si eso es todo, gracias", "check_not": []},
    ]
    _make(4, i, f"Happy path correo - {neg}", {"nombre_negocio": neg, "telefono": tel, "ciudad": ciudad}, turnos)

# --- Grupo 5: Encargado ausente - diferentes excusas ---
excusas = [
    "No esta, salio a comer",
    "Esta en junta ahorita",
    "Salio al banco, regresa en una hora",
    "No vino hoy, viene manana",
    "Esta atendiendo un cliente",
    "Esta en el almacen, no puede hablar",
    "Esta de viaje hasta el lunes",
    "Acaba de salir a hacer una entrega",
    "Esta con el contador ahorita",
    "Esta en la sucursal, no esta aqui",
]
negocios_g5 = [
    ("Ferreteria Padilla", "3312344001", "Guadalajara"),
    ("El Clavo Seguro", "5512344002", "CDMX"),
    ("Materiales Noreste", "8112344003", "Monterrey"),
    ("Dist. El Porvenir", "3312344004", "Guadalajara"),
    ("Tornillos La Paz", "4412344005", "Queretaro"),
    ("El Fierro Rapido", "3312344006", "Guadalajara"),
    ("Herramientas GTO", "4112344007", "Guanajuato"),
    ("Sum. El Aguila", "3312344008", "Guadalajara"),
    ("Tlapaleria Roma", "5512344009", "CDMX"),
    ("Ferreteria Azteca", "3312344010", "Guadalajara"),
]
for i, ((neg, tel, ciudad), excusa) in enumerate(zip(negocios_g5, excusas), 1):
    turnos = [
        {"cliente": "Bueno", "check_not": []},
        {"cliente": excusa, "check_not": []},
        {"cliente": "Si, digale que llamaron de Nioval", "check_not": []},
    ]
    _make(5, i, f"Encargado ausente - {neg}", {"nombre_negocio": neg, "telefono": tel, "ciudad": ciudad}, turnos)

# --- Grupo 6: Rechazo rapido / no interes ---
rechazos = [
    "No gracias, no nos interesa",
    "No, no necesitamos nada",
    "Ya tenemos proveedor, gracias",
    "No tengo tiempo ahorita",
    "No me interesa, gracias",
    "Estamos bien con lo que tenemos",
    "No por favor, no necesitamos",
    "Ahorita no, quiza otro dia",
    "No, muchas gracias",
    "No, por favor, adios",
]
negocios_g6 = [
    ("Ferreteria Luna", "3312345001", "Guadalajara"),
    ("Dist. El Taller", "5512345002", "CDMX"),
    ("Materiales Poniente", "8112345003", "Monterrey"),
    ("El Tornillo Rojo", "3312345004", "Guadalajara"),
    ("Herramientas Reyes", "4412345005", "Queretaro"),
    ("Ferreteria Centro", "3312345006", "Guadalajara"),
    ("Tlapaleria Norte", "5512345007", "CDMX"),
    ("El Fierro Blanco", "3312345008", "Guadalajara"),
    ("Sum. Industrial MX", "6641345009", "Tijuana"),
    ("Materiales El Arco", "3312345010", "Guadalajara"),
]
for i, ((neg, tel, ciudad), rechazo) in enumerate(zip(negocios_g6, rechazos), 1):
    turnos = [
        {"cliente": "Bueno", "check_not": []},
        {"cliente": rechazo, "check_not": []},
    ]
    _make(6, i, f"Rechazo rapido - {neg}", {"nombre_negocio": neg, "telefono": tel, "ciudad": ciudad}, turnos)

# --- Grupo 7: Confirmaciones variadas (orale, dale, perfecto, etc.) ---
confirmaciones = [
    ["Bueno", "Orale si, yo soy", "Orale, al WhatsApp", "3312346001"],
    ["Hola", "Dale, soy yo", "Dale manda por WhatsApp", "5512346002"],
    ["Bueno", "Claro, soy el encargado", "Perfecto, al WhatsApp", "8112346003"],
    ["Buenos dias", "Correcto, con el encargado", "Correcto, al WhatsApp", "3312346004"],
    ["Diga", "Exacto, yo soy", "Exacto, por WhatsApp", "4412346005"],
    ["Bueno", "Eso es, yo mero", "Si si, al WhatsApp", "3312346006"],
    ["Alo", "Andale, yo soy el dueno", "Andale, manda por WhatsApp", "5512346007"],
    ["Bueno", "Con mucho gusto, soy el encargado", "Con gusto, al WhatsApp", "3312346008"],
    ["Si diga", "Afirmativo, yo soy", "Afirmativo, al WhatsApp", "6641346009"],
    ["Bueno", "Simón, yo soy el encargado", "Simón, por WhatsApp", "3312346010"],
]
negocios_g7 = [f"Ferreteria Conf {i}" for i in range(1, 11)]
ciudades_g7 = ["Guadalajara", "CDMX", "Monterrey", "Guadalajara", "Queretaro",
               "Guadalajara", "CDMX", "Guadalajara", "Tijuana", "Guadalajara"]
for i, (conf, ciudad) in enumerate(zip(confirmaciones, ciudades_g7), 1):
    neg = f"Ferreteria Conf {i}"
    tel = conf[3]
    turnos = [
        {"cliente": conf[0], "check_not": []},
        {"cliente": conf[1], "check_not": []},
        {"cliente": conf[2], "check_not": []},
        {"cliente": tel, "check_not": []},
        {"cliente": "Gracias, hasta luego", "check_not": []},
    ]
    _make(7, i, f"Confirmacion variada '{conf[1][:10]}' - {neg}", {"nombre_negocio": neg, "telefono": tel, "ciudad": ciudad}, turnos)

# --- Grupo 8: IVR / Conmutador -> encargado ---
negocios_g8 = [
    ("Grupo Industrial BH", "5512347001", "CDMX"),
    ("Corp. Materiales SA", "8112347002", "Monterrey"),
    ("Ferr. Corporativa GDL", "3312347003", "Guadalajara"),
    ("Dist. Nacional SA", "4412347004", "Queretaro"),
    ("Sum. Industriales MX", "5512347005", "CDMX"),
    ("Conglomerate Ferre SA", "3312347006", "Guadalajara"),
    ("Metalurgica del Norte", "8112347007", "Monterrey"),
    ("Grupo Suministros MX", "5512347008", "CDMX"),
    ("Corp. Herramientas SA", "3312347009", "Guadalajara"),
    ("Industrial Omega SA", "6641347010", "Tijuana"),
]
saludos_ivr = [
    ["Bienvenido a Grupo Industrial, en que le puedo ayudar", "Le comunico con el encargado", "Si, buenos dias, soy el encargado de compras", "Al WhatsApp si, el 5512347001"],
    ["Grupo Materiales buenos dias", "Un momento le comunico", "Buenas, si yo soy el encargado", "Por WhatsApp, el 8112347002"],
    ["Ferreteria Corporativa, digame", "Ahorita le comunico", "Si, soy yo el gerente de compras", "Al WhatsApp, es el 3312347003"],
    ["Distribuidora Nacional, buenas tardes", "En seguida le paso", "Buenos dias, aqui el encargado", "Al WhatsApp, 4412347004"],
    ["Suministros MX, como le ayudo", "Permita un momento", "Si, yo soy el responsable de compras", "Por WhatsApp, 5512347005"],
    ["Conglomerate, buenas tardes", "Con gusto, le comunico", "Si, aqui el encargado", "Al WhatsApp si, el 3312347006"],
    ["Metalurgica Norte, buenas", "Ahorita le paso", "Con el encargado habla, si", "Al WhatsApp, 8112347007"],
    ["Grupo Suministros, digame", "Un momento por favor", "Si, aqui el jefe de compras", "Por WhatsApp si, 5512347008"],
    ["Corp. Herramientas, buenas tardes", "Le comunico de inmediato", "Si, con el encargado", "Al WhatsApp, 3312347009"],
    ["Industrial Omega, buenas", "Ahorita le paso con el responsable", "Si, yo soy el encargado", "Por WhatsApp, 6641347010"],
]
for i, ((neg, tel, ciudad), turnos_raw) in enumerate(zip(negocios_g8, saludos_ivr), 1):
    turnos = [{"cliente": t, "check_not": []} for t in turnos_raw]
    _make(8, i, f"IVR -> encargado - {neg}", {"nombre_negocio": neg, "telefono": tel, "ciudad": ciudad}, turnos)

# --- Grupo 9: Preguntas sobre el catalogo / precio ---
preguntas = [
    "Que tipo de productos mandan",
    "Y cuanto cuesta el catalogo",
    "Tienen descuentos por volumen",
    "Son distribuidores o fabricantes",
    "De donde son ustedes",
    "Cuantos productos tienen",
    "Manejan herramienta de marca",
    "Tienen tornilleria en general",
    "Cuanto tiempo tardan en entregar",
    "Trabajan con credito",
]
negocios_g9 = [
    (f"Ferreteria Pregunta {i}", f"331234800{i}", "Guadalajara") for i in range(1, 11)
]
for i, ((neg, tel, ciudad), pregunta) in enumerate(zip(negocios_g9, preguntas), 1):
    turnos = [
        {"cliente": "Bueno", "check_not": []},
        {"cliente": "Si soy yo el encargado", "check_not": []},
        {"cliente": pregunta, "check_not": []},
        {"cliente": "Ah ok, si manda el catalogo al WhatsApp", "check_not": []},
        {"cliente": tel, "check_not": []},
    ]
    _make(9, i, f"Pregunta catalogo '{pregunta[:20]}' - {neg}", {"nombre_negocio": neg, "telefono": tel, "ciudad": ciudad}, turnos)

# --- Grupo 10: Numero dictado en partes / lento ---
negocios_g10 = [
    (f"Materiales Lento {i}", f"331234900{i}", "Guadalajara") for i in range(1, 11)
]
numeros_partes = [
    ["33", "12", "34", "90", "01"],
    ["El numero es 33", "12", "34 90", "02"],
    ["Espere... es el 33 12", "34 90 03"],
    ["Anote: treinta y tres", "doce", "treinta y cuatro noventa cuatro"],
    ["33-12-34-90-05"],
    ["El WhatsApp es: 33 12 34 90 06"],
    ["Disculpe... es el 3312349007"],
    ["Un momento... 33 12 34 90 08"],
    ["Si, el numero es 33 12", "espere", "34 90 09"],
    ["El tres tres, uno dos, tres cuatro, nueve, cero diez"],
]
for i, ((neg, tel, ciudad), partes) in enumerate(zip(negocios_g10, numeros_partes), 1):
    turnos_pre = [
        {"cliente": "Bueno", "check_not": []},
        {"cliente": "Si, yo soy el encargado", "check_not": []},
        {"cliente": "Si, al WhatsApp", "check_not": []},
    ]
    turnos_num = [{"cliente": p, "check_not": []} for p in partes]
    _make(10, i, f"Numero en partes - {neg}", {"nombre_negocio": neg, "telefono": tel, "ciudad": ciudad}, turnos_pre + turnos_num)

# --- Grupo 11: Encargado pide mas tiempo / callbacks ---
negocios_g11 = [
    (f"Ferreteria Callback {i}", f"331235000{i}", "Guadalajara") for i in range(1, 11)
]
callbacks = [
    ["Bueno", "Si soy yo pero estoy ocupado ahorita", "Mejor llamame en una hora"],
    ["Bueno", "El encargado soy yo pero tengo un cliente", "Mejor a las 3 de la tarde"],
    ["Buen dia", "Si, soy el dueno pero estoy muy ocupado", "Marca al rato por favor"],
    ["Bueno", "Ahorita no puedo atenderte bien", "Llama pasado manana"],
    ["Hola", "Si soy yo pero en este momento no puedo", "Mandame un mensaje mejor"],
    ["Bueno", "Si pero ahora no tengo tiempo", "Vuelveme a llamar manana"],
    ["Diga", "Si soy el encargado pero estoy entreganado", "Llamame en la tarde"],
    ["Bueno", "Si pero tengo una junta ahorita", "Llama en una hora por favor"],
    ["Si digame", "Soy yo pero estoy con un cliente importante", "Mejor llama despues"],
    ["Bueno si", "Si soy el encargado pero ocupado", "Llama manana a primera hora"],
]
for i, ((neg, tel, ciudad), cb) in enumerate(zip(negocios_g11, callbacks), 1):
    turnos = [{"cliente": t, "check_not": []} for t in cb]
    _make(11, i, f"Callback / ocupado - {neg}", {"nombre_negocio": neg, "telefono": tel, "ciudad": ciudad}, turnos)

# --- Grupo 12: Pide recado para el encargado ausente ---
negocios_g12 = [
    (f"Ferreteria Recado {i}", f"331235100{i}", "Guadalajara") for i in range(1, 11)
]
recados = [
    ["Bueno", "No esta el encargado", "Si, le doy el recado", "El encargado es el senor Juan"],
    ["Hola", "El jefe no esta", "Si deje el recado", "Se llama el licenciado Pedro Ramirez"],
    ["Bueno", "No esta don Miguel", "Si puedo darle razon", "Deje su numero y el le llama"],
    ["Bueno", "No esta la encargada", "Si, con gusto le doy el recado", "Es la senora Lupita"],
    ["Digame", "El jefe salio", "Si le aviso", "Digame de que empresa llama"],
    ["Bueno", "El encargado esta en el almacen", "Ahorita le digo", "Como se llama usted"],
    ["Hola", "No esta el dueno", "Si le dejo el mensaje", "Me dice su numero"],
    ["Bueno", "Esta ocupado el senor", "Le digo que llamo", "De Nioval verdad"],
    ["Diga", "No viene el encargado hoy", "Si le aviso manana", "Cual es su numero"],
    ["Bueno si", "No esta don Carlos", "Si le doy el recado", "Que empresa es"],
]
for i, ((neg, tel, ciudad), rec) in enumerate(zip(negocios_g12, recados), 1):
    turnos = [{"cliente": t, "check_not": []} for t in rec]
    _make(12, i, f"Recado para encargado - {neg}", {"nombre_negocio": neg, "telefono": tel, "ciudad": ciudad}, turnos, ["NO_DA_DATOS_RECADO"])

# --- Grupo 13: Numero invalido / reintento ---
negocios_g13 = [
    (f"Ferreteria Numero {i}", f"331235200{i}", "Guadalajara") for i in range(1, 11)
]
nums_invalidos = [
    ["Bueno", "Si soy yo", "Si al WhatsApp", "Es el 123", "Perdon, el completo es 3312352001"],
    ["Hola", "Si encargado", "Al WhatsApp", "El 33", "Ah perdon, 3312352002"],
    ["Bueno", "Si yo mero", "Por WhatsApp", "Disculpe me equivoque, es 3312352003", "Si eso"],
    ["Buen dia", "Si, soy yo", "Al WhatsApp", "El numero... espere", "Es el 3312352004"],
    ["Bueno", "Si encargado", "Por WhatsApp si", "Ay perdon, me confundi", "Es 3312352005"],
    ["Hola", "Si soy yo", "Al WhatsApp", "Hmm no el correcto es 3312352006"],
    ["Digame", "Si yo", "WhatsApp", "El 55... no espere, 3312352007"],
    ["Bueno", "Si mero", "WhatsApp ok", "Este numero... 3312352008", "Si ese"],
    ["Hola si", "Aqui el encargado", "WhatsApp perfecto", "Anoteme el 3312352009"],
    ["Buen dia", "Si, conmigo", "Al WhatsApp esta bien", "El numero es 3312352010"],
]
for i, ((neg, tel, ciudad), num_seq) in enumerate(zip(negocios_g13, nums_invalidos), 1):
    turnos = [{"cliente": t, "check_not": []} for t in num_seq]
    _make(13, i, f"Numero invalido/reintento - {neg}", {"nombre_negocio": neg, "telefono": tel, "ciudad": ciudad}, turnos)

# --- Grupo 14: Preguntas de ubicacion / informacion Nioval ---
negocios_g14 = [
    (f"Ferreteria Ubic {i}", f"331235300{i}", "Guadalajara") for i in range(1, 11)
]
pregs_ubic = [
    ["Bueno", "Si soy yo", "Y de donde me estan llamando", "Ok, manden catalogo al WhatsApp", "3312353001"],
    ["Hola", "Si, encargado", "Que empresa es", "Ah ok, manden al WhatsApp", "3312353002"],
    ["Bueno", "Si, yo mero", "Ustedes de donde son", "Ah Guadalajara, ok mandan al WhatsApp", "3312353003"],
    ["Buen dia", "Si, soy yo", "Como se llama la empresa", "Nioval, ok manden al WhatsApp", "3312353004"],
    ["Bueno", "Si encargado", "Que venden exactamente", "Ah herreria, si manden al WhatsApp", "3312353005"],
    ["Hola", "Si, yo", "Tienen sucursal aqui en mi ciudad", "Ah solo Guadalajara, ok manden al WhatsApp", "3312353006"],
    ["Bueno", "Aqui encargado", "Tiempo de entrega", "Ah ok, si manden al WhatsApp", "3312353007"],
    ["Digame", "Si yo soy", "Son distribuidores", "Ah ok, manden al WhatsApp", "3312353008"],
    ["Bueno si", "Yo mero", "Ya les compre antes", "Ah si bueno, manden al WhatsApp", "3312353009"],
    ["Hola buen dia", "Si, encargado", "De que ciudad me llaman", "Guadalajara ok, WhatsApp si", "3312353010"],
]
for i, ((neg, tel, ciudad), seq) in enumerate(zip(negocios_g14, pregs_ubic), 1):
    turnos = [{"cliente": t, "check_not": []} for t in seq]
    _make(14, i, f"Pregunta ubicacion/empresa - {neg}", {"nombre_negocio": neg, "telefono": tel, "ciudad": ciudad}, turnos)

# --- Grupo 15: Flujos mixtos / edge cases ---
edge_cases = [
    # 1: Encargado contesta confundido
    ("Ferreteria Edge 1", "3312354001", "Guadalajara", [
        "Bueno", "No entiendo de que me habla", "Ah, catalogo de ferreterias", "Si mande al WhatsApp", "3312354001"
    ]),
    # 2: Pide tiempo para pensar
    ("Ferreteria Edge 2", "3312354002", "Guadalajara", [
        "Bueno", "Si soy yo", "Dejame pensar... si mandelo por WhatsApp", "3312354002"
    ]),
    # 3: Encargado y dueno son la misma persona
    ("Ferreteria Edge 3", "3312354003", "Guadalajara", [
        "Bueno", "Si soy yo, soy el dueno y encargado", "Si al WhatsApp", "3312354003"
    ]),
    # 4: Numero de correo dictado lento
    ("Ferreteria Edge 4", "3312354004", "Guadalajara", [
        "Bueno", "Si, encargado", "Al correo mejor", "Es ferreteria", "punto edge4", "arroba gmail", "punto com"
    ]),
    # 5: Dice que ya recibio el catalogo antes
    ("Ferreteria Edge 5", "3312354005", "Guadalajara", [
        "Bueno", "Si soy yo el encargado", "Ya me mandaron el catalogo antes", "Ah si, pero actualizalo, manda al WhatsApp", "3312354005"
    ]),
    # 6: No sabe si es el encargado correcto
    ("Ferreteria Edge 6", "3312354006", "Guadalajara", [
        "Bueno", "Pues yo soy el que esta aqui pero no se si soy el encargado", "Si yo decido las compras", "Si al WhatsApp", "3312354006"
    ]),
    # 7: Pregunta si es gratis
    ("Ferreteria Edge 7", "3312354007", "Guadalajara", [
        "Bueno", "Si, soy yo", "Es gratis el catalogo", "Ah si gratis, entonces si manda al WhatsApp", "3312354007"
    ]),
    # 8: Quiere catalogo fisico
    ("Ferreteria Edge 8", "3312354008", "Guadalajara", [
        "Bueno", "Si, encargado", "Prefiero catalogo en papel", "Ah, digital si, manda al WhatsApp", "3312354008"
    ]),
    # 9: Empieza rechazando, luego acepta
    ("Ferreteria Edge 9", "3312354009", "Guadalajara", [
        "Bueno", "No me interesa", "Bueno a ver de que se trata", "Ah ferreterias, si manda al WhatsApp", "3312354009"
    ]),
    # 10: Pide hablar con supervisor de Nioval
    ("Ferreteria Edge 10", "3312354010", "Guadalajara", [
        "Bueno", "Si, encargado", "Me puede comunicar con su supervisor", "Ok, manda el catalogo al WhatsApp entonces", "3312354010"
    ]),
]
for i, (neg, tel, ciudad, seq) in enumerate(edge_cases, 1):
    turnos = [{"cliente": t, "check_not": []} for t in seq]
    _make(15, i, f"Edge case {i} - {neg}", {"nombre_negocio": neg, "telefono": tel, "ciudad": ciudad}, turnos)


# --- Grupo 16: FIX 938 - Validacion de nuevos fixes ---
# Escenarios diseñados para confirmar que FIX 938 A-I funcionan correctamente

# FIX 938-A: "estamos bien" → NO_INTEREST → despedida (no pide datos)
_make(16, 1, "FIX938-A: estamos_bien_no_interest",
    {"nombre_negocio": "Ferreteria Test A", "telefono": "3312160001", "ciudad": "Guadalajara"},
    [
        {"cliente": "Bueno", "check_not": []},
        {"cliente": "Si, soy el encargado", "check_not": []},
        {"cliente": "Estamos bien con lo que tenemos, gracias", "check_not": ["WhatsApp", "correo", "numero"]},
    ],
    bugs_criticos=["DATO_NEGADO_REINSISTIDO"],
)

# FIX 938-A2: "no muchas gracias" → NO_INTEREST → despedida (no pide datos)
_make(16, 2, "FIX938-A2: no_muchas_gracias_no_interest",
    {"nombre_negocio": "Ferreteria Test A2", "telefono": "3312160002", "ciudad": "Guadalajara"},
    [
        {"cliente": "Bueno", "check_not": []},
        {"cliente": "Soy yo", "check_not": []},
        {"cliente": "No, muchas gracias, no nos hace falta", "check_not": ["WhatsApp", "correo"]},
    ],
    bugs_criticos=["DATO_NEGADO_REINSISTIDO"],
)

# FIX 938-B: "marca al rato" en estado CAPTURANDO_CONTACTO → CALLBACK (no continuar pidiendo datos)
_make(16, 3, "FIX938-B: marca_al_rato_en_capturando",
    {"nombre_negocio": "Ferreteria Test B", "telefono": "3312160003", "ciudad": "Guadalajara"},
    [
        {"cliente": "Bueno", "check_not": []},
        {"cliente": "Si, yo soy el encargado", "check_not": []},
        {"cliente": "Claro, al WhatsApp", "check_not": []},
        {"cliente": "Marca al rato, ahorita estoy ocupado", "check_not": ["WhatsApp", "digame"]},
    ],
    bugs_criticos=["DATO_NEGADO_REINSISTIDO", "LOOP"],
)

# FIX 938-C: encargado presente pide callback → template "directo" (no menciona "encontrar al encargado")
_make(16, 4, "FIX938-C: callback_encargado_presente_template_directo",
    {"nombre_negocio": "Ferreteria Test C", "telefono": "3312160004", "ciudad": "Guadalajara"},
    [
        {"cliente": "Bueno, soy el encargado", "check_not": []},
        {"cliente": "Si, digame", "check_not": []},
        {"cliente": "Llame mas tarde, ahorita no puedo", "check_not": ["encontrar al encargado"]},
    ],
    bugs_criticos=["GPT_LOGICA_ROTA"],
)

# FIX 938-D: rechazo firme → FIX 922 NO debe disparar captura_minima_pre_despedida
_make(16, 5, "FIX938-D: rechazo_firme_no_captura_minima",
    {"nombre_negocio": "Ferreteria Test D", "telefono": "3312160005", "ciudad": "Guadalajara"},
    [
        {"cliente": "Bueno", "check_not": []},
        {"cliente": "Soy el encargado", "check_not": []},
        {"cliente": "No gracias, no nos interesa para nada", "check_not": ["nombre", "hora", "momento"]},
    ],
    bugs_criticos=["GPT_LOGICA_ROTA", "DATO_NEGADO_REINSISTIDO"],
)

# FIX 938-I: "yo le dejo el recado" → aceptar_recado_pedir_wa (no repetir pedir WA igual)
_make(16, 6, "FIX938-I: recado_oferta_detectado",
    {"nombre_negocio": "Ferreteria Test I", "telefono": "3312160006", "ciudad": "Guadalajara"},
    [
        {"cliente": "Bueno", "check_not": []},
        {"cliente": "No esta el encargado", "check_not": []},
        {"cliente": "Yo le dejo el recado", "check_not": []},
    ],
    bugs_criticos=["GPT_LOGICA_ROTA"],
)

# FIX 938 MEJ-02: "tienen descuentos" → QUESTION → respuesta informativa (no "Claro, digame")
_make(16, 7, "FIX938-MEJ02: tienen_descuentos_es_pregunta",
    {"nombre_negocio": "Ferreteria Test MEJ2", "telefono": "3312160007", "ciudad": "Guadalajara"},
    [
        {"cliente": "Bueno", "check_not": []},
        {"cliente": "Soy yo el encargado", "check_not": []},
        {"cliente": "Tienen descuentos por volumen", "check_not": ["digame", "Claro, digame"]},
    ],
    bugs_criticos=["GPT_LOGICA_ROTA"],
)

# ============================================================
# Runner de escenarios OOS
# ============================================================
class RunnerOOS:
    def __init__(self, verbose=False):
        self.verbose = verbose
        self.resultados = []

    def run_scenario(self, escenario):
        eid = escenario["id"]
        nombre = escenario["nombre"]

        agente = AgenteVentas(
            contacto_info=escenario["contacto"],
            sheets_manager=None,
            resultados_manager=None,
            whatsapp_validator=None,
        )
        tracker = CallEventTracker(
            call_sid=f"VAL_V2_{eid}",
            bruce_id=f"VAL{eid}",
            telefono=escenario["contacto"].get("telefono", ""),
        )
        tracker.simulador_texto = True

        t0 = time.time()

        try:
            saludo = agente.iniciar_conversacion()
            tracker.emit("BRUCE_RESPONDE", {"texto": saludo})
        except Exception as e:
            saludo = ""
            if self.verbose:
                print(f"    [ERROR saludo] {e}")

        for i, turno in enumerate(escenario["turnos"]):
            msg = turno["cliente"]
            tracker.emit("CLIENTE_DICE", {"texto": msg})

            try:
                respuesta = agente.procesar_respuesta(msg) or ""
            except Exception as e:
                respuesta = f"[ERROR: {e}]"

            tracker.emit("BRUCE_RESPONDE", {"texto": respuesta})

            if self.verbose:
                print(f"      C[{i+1}]: {msg}")
                print(f"      B[{i+1}]: {respuesta}")

        duracion = time.time() - t0
        bugs = BugDetector.analyze(tracker)

        # Armar transcripcion para auditoria Sonnet
        # tracker.conversacion = lista de tuplas ("bruce"|"cliente", texto)
        transcripcion = []
        for rol, texto in tracker.conversacion:
            label = "Bruce" if rol == "bruce" else "Cliente"
            transcripcion.append((label, texto))

        resultado = {
            "id": eid,
            "nombre": nombre,
            "bugs": bugs,
            "duracion": duracion,
            "transcripcion": transcripcion,
            "contacto": escenario["contacto"],
        }
        self.resultados.append(resultado)
        return resultado

    def run_all(self, verbose_progress=True):
        total = len(ESCENARIOS_OOS)
        bugs_total = []

        for idx, esc in enumerate(ESCENARIOS_OOS, 1):
            if verbose_progress and idx % 10 == 1:
                print(f"  Procesando escenarios {idx}-{min(idx+9, total)}/{total}...")

            resultado = self.run_scenario(esc)
            bugs_total.extend(resultado["bugs"])

            if self.verbose:
                bugs_str = ", ".join(b["tipo"] for b in resultado["bugs"]) or "ninguno"
                print(f"  [{resultado['id']}] {resultado['nombre'][:50]} | bugs: {bugs_str}")

        return self.resultados, bugs_total


# ============================================================
# Auditoría Claude Sonnet (Fase 3)
# ============================================================
_SONNET_SYSTEM = """Eres un auditor experto de agentes de ventas telefónicos.
Evalúas conversaciones de Bruce W, un agente AI que llama a ferreterías para ofrecer el catálogo de NIOVAL.

Criterios de evaluación:
1. CANAL_REINSISTIDO: Bruce pidió WhatsApp/correo después de que el cliente lo rechazó explícitamente
2. DATO_REPETIDO: Bruce pidió un dato que el cliente ya proporcionó
3. LOGICA_ROTA: Bruce dice algo ilógico (ej: confirmar envío de catálogo sin tener contacto)
4. PREGUNTA_REPETIDA: Bruce hace la misma pregunta 2+ veces consecutivas sin progreso
5. TONO_INCORRECTO: Bruce usa tuteo o tono inapropiado
6. DESPEDIDA_PREMATURA: Bruce se despide mientras el cliente aún está dando información
7. PITCH_FUERA_DE_CONTEXTO: Bruce repite el pitch completo cuando ya fue aceptado/rechazado
8. OPORTUNIDAD_PERDIDA: El cliente mostró interés claro y Bruce no lo aprovechó

Para cada conversación responde SOLO con JSON válido en este formato:
{
  "id": "<id del escenario>",
  "bugs": [
    {"tipo": "CANAL_REINSISTIDO", "turno": 3, "detalle": "Bruce pidio WhatsApp despues de rechazo explicito"},
    ...
  ],
  "calidad": "BUENA|REGULAR|MALA",
  "nota": "Breve comentario (max 100 chars)"
}
Si no hay bugs, "bugs" debe ser lista vacía [].
NO incluyas texto fuera del JSON."""

def _auditoria_sonnet(resultados_oos, batch_size=10):
    """Evalúa conversaciones OOS con Claude Sonnet en batches."""
    try:
        import anthropic
    except ImportError:
        print("  [SONNET] anthropic no instalado. pip install anthropic")
        return []

    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        print("  [SONNET] ANTHROPIC_API_KEY no configurada")
        return []

    client = anthropic.Anthropic(api_key=api_key)
    todos_hallazgos = []

    # Filtrar resultados con transcripcion no vacía
    con_transcript = [r for r in resultados_oos if r.get("transcripcion")]
    total = len(con_transcript)
    print(f"  [SONNET] Auditando {total} conversaciones en batches de {batch_size}...")

    for batch_start in range(0, total, batch_size):
        batch = con_transcript[batch_start:batch_start + batch_size]
        batch_num = batch_start // batch_size + 1
        total_batches = (total + batch_size - 1) // batch_size
        print(f"  [SONNET] Batch {batch_num}/{total_batches} ({len(batch)} convs)...")

        # Construir prompt con todas las conversaciones del batch
        convs_text = ""
        for r in batch:
            convs_text += f"\n--- ESCENARIO {r['id']}: {r['nombre']} ---\n"
            for rol, texto in r["transcripcion"]:
                convs_text += f"{rol}: {texto}\n"
            convs_text += "\n"

        prompt = f"""Evalúa las siguientes {len(batch)} conversaciones de Bruce W.
Responde con un JSON array con un objeto por conversación:
[
  {{json conv 1}},
  {{json conv 2}},
  ...
]

CONVERSACIONES:
{convs_text}"""

        try:
            response = client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=2048,
                system=_SONNET_SYSTEM,
                messages=[{"role": "user", "content": prompt}],
            )
            raw = response.content[0].text.strip()

            # Limpiar si viene con markdown
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
            raw = raw.strip()

            hallazgos_batch = json.loads(raw)
            if isinstance(hallazgos_batch, dict):
                hallazgos_batch = [hallazgos_batch]
            todos_hallazgos.extend(hallazgos_batch)

        except Exception as e:
            err_str = str(e)
            print(f"  [SONNET] Error batch {batch_num}: {err_str[:120]}")
            for r in batch:
                todos_hallazgos.append({"id": r["id"], "bugs": [], "calidad": "ERROR", "nota": err_str[:80]})
            # Abortar si es error de creditos (no tiene sentido seguir)
            if "credit balance is too low" in err_str or "insufficient_quota" in err_str:
                print(f"  [SONNET] Creditos agotados - abortando auditoria. Agrega creditos en console.anthropic.com")
                # Completar entradas faltantes
                for r in con_transcript[batch_start + len(batch):]:
                    todos_hallazgos.append({"id": r["id"], "bugs": [], "calidad": "ERROR", "nota": "sin_creditos"})
                break

        time.sleep(0.5)  # Rate limiting

    return todos_hallazgos


def _imprimir_sonnet_resumen(hallazgos):
    """Imprime resumen de auditoría Sonnet."""
    if not hallazgos:
        return

    total = len(hallazgos)
    con_bug = [h for h in hallazgos if h.get("bugs")]
    tasa = len(con_bug) / total if total else 0

    bug_counts = Counter(
        b["tipo"]
        for h in hallazgos
        for b in h.get("bugs", [])
    )
    calidad_counts = Counter(h.get("calidad", "?") for h in hallazgos)

    print(f"\n  FASE 3 - Auditoria Sonnet ({total} conversaciones):")
    print(f"    Convs con bug: {len(con_bug)}/{total}  ({tasa*100:.1f}%)")
    if bug_counts:
        for tipo, cnt in bug_counts.most_common():
            print(f"    Bug {tipo}: {cnt}")
    else:
        print(f"    Bugs: ninguno")
    print(f"    Calidad: " + " | ".join(f"{k}={v}" for k, v in calidad_counts.most_common()))

    # Mostrar casos con bugs
    if con_bug:
        print(f"\n    Escenarios con bugs detectados por Sonnet:")
        for h in con_bug:
            for b in h["bugs"]:
                print(f"      [{h['id']}] {b['tipo']} (turno {b.get('turno','?')}): {b.get('detalle','')[:80]}")


# ============================================================
# Reporte comparativo
# ============================================================
def generar_reporte(resultados_sim, resultados_oos, sim_failed, sonnet_hallazgos=None):
    """Genera reporte JSON + resumen en consola."""

    # ---- Fase 1: Simulador E2E ----
    sim_total = len(resultados_sim)
    sim_pass = sum(1 for r in resultados_sim if r.get("passed", False))
    sim_bugs = [b for r in resultados_sim for b in r.get("bugs", [])]

    # ---- Fase 2: OOS ----
    oos_total = len(resultados_oos)
    oos_bugs = [b for r in resultados_oos for b in r.get("bugs", [])]
    oos_convs_con_bug = sum(1 for r in resultados_oos if r.get("bugs"))
    oos_tasa = oos_convs_con_bug / oos_total if oos_total else 0

    # ---- Comparativa con baseline ----
    mejora_abs = BASELINE["tasa_bugs"] - oos_tasa
    mejora_pct = (mejora_abs / BASELINE["tasa_bugs"] * 100) if BASELINE["tasa_bugs"] else 0

    bug_counts_oos = Counter(b["tipo"] for b in oos_bugs)
    bug_counts_sim = Counter(b["tipo"] for b in sim_bugs)

    reporte = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "modelo_activo": os.environ.get("LLM_MODEL", "gpt-4.1-mini"),
        "fase1_simulador_e2e": {
            "total_escenarios": sim_total,
            "pass": sim_pass,
            "fail": sim_total - sim_pass,
            "tasa_pass": sim_pass / sim_total if sim_total else 0,
            "bugs_totales": len(sim_bugs),
            "bugs_por_tipo": dict(bug_counts_sim),
        },
        "fase2_oos_150": {
            "total_convs": oos_total,
            "convs_con_bug": oos_convs_con_bug,
            "tasa_bugs": round(oos_tasa, 4),
            "bugs_totales": len(oos_bugs),
            "bugs_por_tipo": dict(bug_counts_oos),
            "escenarios_con_bug": [
                {"id": r["id"], "nombre": r["nombre"], "bugs": [{"tipo": b["tipo"], "detalle": b.get("detalle", "")[:120]} for b in r["bugs"]]}
                for r in resultados_oos if r.get("bugs")
            ],
        },
        "comparativa_baseline": {
            "baseline_descripcion": BASELINE["descripcion"],
            "baseline_tasa": BASELINE["tasa_bugs"],
            "baseline_bugs_reales": BASELINE["bugs_reales"],
            "v2_tasa": round(oos_tasa, 4),
            "mejora_absoluta": round(mejora_abs, 4),
            "mejora_pct": round(mejora_pct, 1),
            "veredicto": "MEJORA" if mejora_abs > 0 else ("IGUAL" if mejora_abs == 0 else "REGRESION"),
        },
    }

    # ---- Guardar JSON ----
    reporte_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "validador_v2_reporte.json")
    with open(reporte_path, "w", encoding="utf-8") as f:
        json.dump(reporte, f, ensure_ascii=False, indent=2)

    # ---- Imprimir resumen ----
    print("\n" + "=" * 65)
    print("  REPORTE COMPARATIVO - Finetune v2 vs Baseline")
    print("=" * 65)
    print(f"\n  Modelo activo: {reporte['modelo_activo']}")
    print(f"\n  FASE 1 - Simulador E2E ({sim_total} escenarios):")
    if sim_total:
        print(f"    PASS: {sim_pass}/{sim_total}  ({sim_pass/sim_total*100:.1f}%)")
    else:
        print(f"    (no ejecutada)")
    if bug_counts_sim:
        for tipo, cnt in bug_counts_sim.most_common():
            print(f"    Bug {tipo}: {cnt}")
    else:
        print(f"    Bugs: ninguno")

    print(f"\n  FASE 2 - Out-of-sample ({oos_total} escenarios nuevos):")
    print(f"    Convs con bug: {oos_convs_con_bug}/{oos_total}  ({oos_tasa*100:.1f}%)")
    if bug_counts_oos:
        for tipo, cnt in bug_counts_oos.most_common():
            print(f"    Bug {tipo}: {cnt}")
    else:
        print(f"    Bugs: ninguno")

    print(f"\n  COMPARATIVA vs Baseline:")
    print(f"    Baseline  : {BASELINE['tasa_bugs']*100:.1f}% ({BASELINE['bugs_reales']}/{BASELINE['total_convs']} convs)")
    print(f"    V2 (OOS)  : {oos_tasa*100:.1f}% ({oos_convs_con_bug}/{oos_total} convs)")
    print(f"    Mejora    : {mejora_abs*100:.1f}pp ({mejora_pct:.1f}%)")
    print(f"    Veredicto : {reporte['comparativa_baseline']['veredicto']}")
    # ---- Fase 3: Sonnet audit (opcional) ----
    if sonnet_hallazgos is not None:
        sonnet_con_bug = [h for h in sonnet_hallazgos if h.get("bugs")]
        sonnet_tasa = len(sonnet_con_bug) / len(sonnet_hallazgos) if sonnet_hallazgos else 0
        sonnet_bug_counts = Counter(
            b["tipo"] for h in sonnet_hallazgos for b in h.get("bugs", [])
        )
        reporte["fase3_sonnet_audit"] = {
            "total_auditadas": len(sonnet_hallazgos),
            "convs_con_bug": len(sonnet_con_bug),
            "tasa_bugs": round(sonnet_tasa, 4),
            "bugs_por_tipo": dict(sonnet_bug_counts),
            "escenarios_con_bug": [
                {"id": h["id"], "calidad": h.get("calidad"), "nota": h.get("nota", ""),
                 "bugs": h["bugs"]}
                for h in sonnet_con_bug
            ],
        }
        _imprimir_sonnet_resumen(sonnet_hallazgos)

        # Actualizar JSON
        with open(reporte_path, "w", encoding="utf-8") as f:
            json.dump(reporte, f, ensure_ascii=False, indent=2)

    print(f"\n  Reporte guardado: validador_v2_reporte.json")
    print("=" * 65)

    return reporte


# ============================================================
# Main
# ============================================================
def main():
    parser = argparse.ArgumentParser(description="Validador V2 - Comparativa finetune Bruce W")
    parser.add_argument("--fase", type=int, choices=[1, 2], help="Solo correr fase 1 o 2")
    parser.add_argument("--verbose", "-v", action="store_true", help="Mostrar respuestas de Bruce")
    parser.add_argument("--reporte", action="store_true", help="Solo mostrar ultimo reporte JSON")
    parser.add_argument("--sonnet", action="store_true", help="Auditoria cualitativa Claude Sonnet via API (Fase 3)")
    parser.add_argument("--exportar-transcripciones", action="store_true", help="Guardar transcripciones OOS a JSON para auditoria externa")
    args = parser.parse_args()

    if args.reporte:
        rpath = os.path.join(os.path.dirname(os.path.abspath(__file__)), "validador_v2_reporte.json")
        if os.path.exists(rpath):
            with open(rpath, encoding="utf-8") as f:
                print(json.dumps(json.load(f), ensure_ascii=False, indent=2))
        else:
            print("No hay reporte previo. Corre primero sin --reporte.")
        return

    print("=" * 65)
    print("  VALIDADOR V2 - Bruce W Finetune Comparison")
    print("=" * 65)

    resultados_sim = []
    resultados_oos = []
    sim_failed = 0

    # ---- Fase 1: Simulador E2E ----
    if args.fase in (None, 1):
        from simulador_e2e import SimuladorE2E, ESCENARIOS as SIM_ESCENARIOS
        print(f"\n  FASE 1: Simulador E2E ({len(SIM_ESCENARIOS)} escenarios)...")
        sim = SimuladorE2E(verbose=args.verbose, gpt_eval=False)
        sim.run_all()
        resultados_sim = sim.resultados
        sim_failed = sum(1 for r in resultados_sim if not r.get("passed", False))

    # ---- Fase 2: OOS 150 ----
    if args.fase in (None, 2):
        print(f"\n  FASE 2: Out-of-sample ({len(ESCENARIOS_OOS)} escenarios nuevos)...")
        runner = RunnerOOS(verbose=args.verbose)
        resultados_oos, _ = runner.run_all(verbose_progress=True)

    # ---- Exportar transcripciones (para auditoria en VSCode/Claude) ----
    if getattr(args, 'exportar_transcripciones', False) and resultados_oos:
        tpath = os.path.join(os.path.dirname(os.path.abspath(__file__)), "validador_v2_transcripciones.json")
        exportar = [
            {"id": r["id"], "nombre": r["nombre"],
             "transcripcion": [{"rol": rol, "texto": texto} for rol, texto in r.get("transcripcion", [])],
             "bugs_rule_based": [{"tipo": b["tipo"], "detalle": b.get("detalle","")} for b in r.get("bugs", [])]}
            for r in resultados_oos
        ]
        with open(tpath, "w", encoding="utf-8") as f:
            json.dump(exportar, f, ensure_ascii=False, indent=2)
        print(f"\n  Transcripciones guardadas: validador_v2_transcripciones.json ({len(exportar)} convs)")

    # ---- Fase 3: Sonnet audit (opcional) ----
    sonnet_hallazgos = None
    if args.sonnet and resultados_oos:
        print(f"\n  FASE 3: Auditoria Claude Sonnet...")
        sonnet_hallazgos = _auditoria_sonnet(resultados_oos)

    # ---- Reporte ----
    if resultados_sim or resultados_oos:
        generar_reporte(resultados_sim, resultados_oos, sim_failed, sonnet_hallazgos)

    # Codigo de salida: 0 si simulador paso todo
    sys.exit(0 if sim_failed == 0 else 1)


if __name__ == "__main__":
    main()
