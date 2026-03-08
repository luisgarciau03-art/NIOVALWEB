"""
BRUCE TEMPLATES ENGINE (BTE)
=============================
Motor de respuestas basado en templates que reemplaza GPT libre.

Arquitectura:
  FSM clasifica intent -> BTE selecciona template -> Variables inyectadas -> Respuesta

GPT solo se usa como fallback clasificador (JSON mode) para el ~6% de casos
que el FSM no puede manejar. Incluso entonces, GPT NO genera texto libre,
solo elige una accion del catalogo.

Basado en analisis de 1,941 conversaciones y 5,083 turnos de Bruce.
"""

import re
import random
import json
import os
from typing import Optional, Dict, List, Tuple

# ============================================================
# CATALOGO DE ACCIONES Y TEMPLATES
# 42 acciones (32 originales + 3 de logs + 7 nuevas de contexto)
# Cada accion tiene 3+ variantes para evitar repeticion
# ============================================================

BTE_CATALOG = {

    # ================================================================
    # FASE 1: APERTURA (35.4% de todos los turnos)
    # ================================================================

    "PRESENTACION_Y_PEDIR_ENCARGADO": {
        "fase": "APERTURA",
        "templates": [
            "Buen dia. Le llamo de parte de NIOVAL, manejamos productos de ferreteria. Se encuentra el encargado de compras?",
            "Buenas tardes. Soy Bruce de NIOVAL, distribuidores de productos ferreteros. Podria comunicarme con el encargado de compras?",
            "Hola, que tal. Llamo de la marca NIOVAL. Somos distribuidores de productos de ferreteria. Estara el encargado o encargada de compras?",
        ],
        "variables": [],
    },

    "PRESENTACION_NIOVAL": {
        "fase": "APERTURA",
        "templates": [
            "Mi nombre es Bruce, le llamo de la marca NIOVAL. Somos distribuidores de productos ferreteros.",
            "Soy Bruce de NIOVAL. Somos una empresa de Guadalajara que distribuye productos de ferreteria.",
            "Le llamo de parte de NIOVAL. Manejamos productos de ferreteria como cintas, griferia, herramientas y mas.",
        ],
        "variables": [],
    },

    "SALUDO_SIMPLE": {
        "fase": "APERTURA",
        "templates": [
            "Hola, buen dia.",
            "Buenas tardes.",
            "Hola, que tal.",
        ],
        "variables": [],
    },

    "SALUDO_Y_PEDIR_ENCARGADO": {
        "fase": "APERTURA",
        "templates": [
            "Hola, buen dia. Le llamo de parte de NIOVAL para ofrecerle informacion de nuestros productos ferreteros. Se encuentra el encargado de compras?",
            "Buenas tardes. Soy Bruce de NIOVAL. Me podria comunicar con el encargado o encargada de compras?",
            "Hola, que tal. Llamo de NIOVAL, productos de ferreteria. Estara disponible el encargado de compras?",
        ],
        "variables": [],
    },

    # ================================================================
    # FASE 2: BUSCAR ENCARGADO (16.7%)
    # ================================================================

    "PREGUNTAR_POR_ENCARGADO": {
        "fase": "BUSCAR_ENCARGADO",
        "templates": [
            "Se encontrara el encargado o encargada de compras?",
            "Podria comunicarme con la persona encargada de las compras?",
            "Estara disponible el encargado de compras?",
        ],
        "variables": [],
    },

    "ESPERANDO_TRANSFERENCIA": {
        "fase": "BUSCAR_ENCARGADO",
        "templates": [
            "Claro, espero.",
            "Si, aqui estoy, esperando.",
            "Perfecto, aqui espero.",
        ],
        "variables": [],
    },

    "PEDIR_COMUNICAR_ENCARGADO": {
        "fase": "BUSCAR_ENCARGADO",
        "templates": [
            "Me lo podria comunicar por favor?",
            "Seria posible que me lo comunicara?",
            "Me podria pasar con el, por favor?",
        ],
        "variables": [],
    },

    # ================================================================
    # FASE 3: PITCH / OFERTA (14.8%)
    # ================================================================

    "PITCH_PRODUCTOS": {
        "fase": "PITCH",
        "templates": [
            "Somos de Guadalajara y manejamos mas de 15 categorias: cintas tapagoteras, griferia, herramientas, candados y mas. Le gustaria recibir nuestro catalogo?",
            "Manejamos productos de ferreteria como cintas, griferia, herramientas y accesorios. Tenemos un catalogo digital que le puedo enviar sin compromiso.",
            "NIOVAL distribuye productos ferreteros: cintas tapagoteras, griferia, herramientas, candados y mas. Le interesaria ver nuestro catalogo?",
        ],
        "variables": [],
    },

    "PITCH_ENCARGADO_CORTO": {
        "fase": "PITCH",
        "templates": [
            "Le llamo para compartirle nuestro catalogo de productos ferreteros. Le gustaria recibirlo por WhatsApp o correo?",
            "Tenemos un catalogo digital con mas de 15 categorias de productos. Se lo puedo enviar por WhatsApp?",
            "Me gustaria enviarle nuestro catalogo de productos. Tiene un WhatsApp donde se lo pueda mandar?",
        ],
        "variables": [],
    },

    "PREGUNTAR_SI_QUIERE_CATALOGO": {
        "fase": "PITCH",
        "templates": [
            "Le gustaria que le enviara nuestro catalogo por WhatsApp o correo?",
            "Tenemos un catalogo digital sin compromiso. Se lo puedo enviar?",
            "Le interesaria recibir nuestro catalogo de productos?",
        ],
        "variables": [],
    },

    "OFRECER_ENVIAR_CATALOGO": {
        "fase": "PITCH",
        "templates": [
            "Me gustaria enviarle nuestro catalogo digital completo con precios. Tiene un WhatsApp donde se lo pueda mandar?",
            "Puedo enviarle el catalogo sin compromiso para que lo revise con calma. Por WhatsApp o correo?",
            "Le puedo compartir nuestro catalogo con toda la informacion. A donde se lo envio?",
        ],
        "variables": [],
    },

    "MENCIONAR_CATALOGO": {
        "fase": "PITCH",
        "templates": [
            "Le enviare el catalogo en las proximas horas. Muchas gracias por su tiempo.",
            "Le llega el catalogo por {canal}. Cualquier duda, con gusto le atiendo.",
            "Perfecto, le envio el catalogo. Ahi viene toda la informacion de precios y productos.",
        ],
        "variables": ["canal"],
    },

    "MENCIONAR_PRODUCTOS": {
        "fase": "PITCH",
        "templates": [
            "Manejamos cintas tapagoteras, griferia, herramientas, candados y mas de 15 categorias de productos ferreteros.",
            "Distribuimos productos de ferreteria: cintas, griferia, herramientas y accesorios. Todo viene en nuestro catalogo.",
            "Tenemos una linea completa de productos ferreteros. Le puedo enviar el catalogo para que vea todo lo que manejamos.",
        ],
        "variables": [],
    },

    # ================================================================
    # FASE 4: CAPTURAR CONTACTO (10.6%)
    # ================================================================

    "PEDIR_WHATSAPP": {
        "fase": "CAPTURA",
        "templates": [
            "Me podria compartir su numero de WhatsApp para enviarle el catalogo?",
            "Cual es su WhatsApp para mandarle la informacion?",
            "Tiene un WhatsApp donde le pueda enviar el catalogo?",
        ],
        "variables": [],
    },

    "PEDIR_CORREO": {
        "fase": "CAPTURA",
        "templates": [
            "Me podria compartir un correo electronico para enviarle la informacion?",
            "Cual es su correo para mandarle el catalogo?",
            "Tiene un correo donde le pueda enviar el catalogo?",
        ],
        "variables": [],
    },

    "PEDIR_NUMERO": {
        "fase": "CAPTURA",
        "templates": [
            "Si, por favor, digame el numero.",
            "Claro, estoy listo para anotarlo. Digame.",
            "Adelante, digame el numero por favor.",
        ],
        "variables": [],
    },

    "PEDIR_NUMERO_COMPLETO": {
        "fase": "CAPTURA",
        "templates": [
            "Disculpe, solo escuche {digitos} digitos. Me puede repetir el numero completo?",
            "Parece que faltan algunos digitos. Me lo podria repetir completo?",
            "Necesito el numero completo de 10 digitos. Me lo puede dar otra vez?",
        ],
        "variables": ["digitos"],
    },

    "CONFIRMAR_ENVIO_WHATSAPP": {
        "fase": "CAPTURA",
        "templates": [
            "Perfecto, le envio el catalogo a este numero de WhatsApp.",
            "Entendido, le mando el catalogo por WhatsApp.",
            "Listo, le llega el catalogo a su WhatsApp.",
        ],
        "variables": [],
    },

    "CONFIRMAR_ENVIO_CORREO": {
        "fase": "CAPTURA",
        "templates": [
            "Perfecto, le envio el catalogo a ese correo.",
            "Entendido, le mando la informacion por correo electronico.",
            "Listo, le llega el catalogo a su correo.",
        ],
        "variables": [],
    },

    "CONFIRMAR_NUMERO_ANOTADO": {
        "fase": "CAPTURA",
        "templates": [
            "Perfecto, ya lo tengo anotado. Muchas gracias.",
            "Listo, ya quedo registrado el numero.",
            "Anotado. Muchas gracias por el dato.",
        ],
        "variables": [],
    },

    "DAR_NUMERO_BRUCE": {
        "fase": "CAPTURA",
        "templates": [
            "Nuestro numero es 6 6 2 4 1 5 1 9 9 7. La marca es NIOVAL, se escribe N I O V A L.",
            "Le dejo nuestro telefono: 6 6 2 4 1 5 1 9 9 7. Y el correo es ventas arroba nioval punto com.",
            "El numero es 6 6 2 4 1 5 1 9 9 7, y la marca es NIOVAL: N I O V A L.",
        ],
        "variables": [],
    },

    # Aliases de logs: MENCIONAR_NUMERO (71x) = DAR_NUMERO_BRUCE
    # MENCIONAR_WHATSAPP (33x) y MENCIONAR_CORREO (19x) = MENCIONAR_CONTACTO_BRUCE

    # ================================================================
    # FASE 5: CONFIRMAR / CERRAR (4.5%)
    # ================================================================

    "CONFIRMAR_DATO": {
        "fase": "CIERRE",
        "templates": [
            "Perfecto, muchas gracias.",
            "Excelente, quedo registrado.",
            "Muy bien, ya lo tengo anotado.",
        ],
        "variables": [],
    },

    "CONFIRMAR_Y_AGRADECER": {
        "fase": "CIERRE",
        "templates": [
            "Perfecto, muchas gracias por su tiempo. Que tenga buen dia.",
            "Excelente, le agradezco mucho. Que tenga excelente dia.",
            "Muy bien, muchas gracias. Cualquier cosa, aqui estamos.",
        ],
        "variables": [],
    },

    "DESPEDIDA": {
        "fase": "CIERRE",
        "templates": [
            "Muchas gracias por su tiempo. Que tenga excelente dia.",
            "Le agradezco mucho la atencion. Que tenga buen dia.",
            "Gracias por atenderme. Que le vaya muy bien.",
        ],
        "variables": [],
    },

    "DESPEDIDA_PUERTA_ABIERTA": {
        "fase": "CIERRE",
        "templates": [
            "Entendido, no se preocupe. Si en algun momento le interesa, con gusto le atendemos. Que tenga buen dia.",
            "No hay problema. Quedo a sus ordenes por si mas adelante requiere algo. Buen dia.",
            "Comprendo. Si en el futuro necesita informacion, aqui estamos. Que tenga excelente dia.",
        ],
        "variables": [],
    },

    # ================================================================
    # FASE 6: MANEJO DE SITUACIONES (11.0%)
    # ================================================================

    "CONFIRMAR_ESCUCHA": {
        "fase": "SITUACIONAL",
        "templates": [
            "Si, le escucho. Digame.",
            "Si, aqui estoy. Adelante.",
            "Le escucho perfectamente, digame.",
        ],
        "variables": [],
    },

    "MANEJAR_TIMEOUT": {
        "fase": "SITUACIONAL",
        "templates": [
            "Me escucha? Parece que hay un poco de interferencia.",
            "Disculpe, sigue ahi? No alcanzo a escucharlo.",
            "Me escucha? Parece que se corto un momento.",
        ],
        "variables": [],
    },

    "MANEJAR_CONFUSION": {
        "fase": "SITUACIONAL",
        "templates": [
            "Disculpe, le explico brevemente. Soy Bruce de NIOVAL, distribuidores de productos ferreteros. Le llamo para ofrecerle nuestro catalogo con precios de fabrica.",
            "Perdon por la confusion. Le llamo de NIOVAL para ofrecerle productos ferreteros a precios competitivos.",
            "Le aclaro, soy Bruce de la marca NIOVAL. Manejamos productos de ferreteria y le llamaba para ver si le interesa recibir nuestro catalogo.",
        ],
        "variables": [],
    },

    "OFRECER_CALLBACK": {
        "fase": "SITUACIONAL",
        "templates": [
            "Entiendo. A que hora le puedo llamar para encontrar al encargado?",
            "No hay problema. Cuando seria buen momento para volver a llamar?",
            "Comprendo. Me puede indicar un horario para volver a intentarlo?",
        ],
        "variables": [],
    },

    "PREGUNTAR_HORARIO_CALLBACK": {
        "fase": "SITUACIONAL",
        "templates": [
            "A que hora me recomienda llamar para encontrarlo?",
            "Cual seria un buen horario para volver a comunicarme?",
            "A que hora estara disponible?",
        ],
        "variables": [],
    },

    "ACKNOWLEDGMENT": {
        "fase": "SITUACIONAL",
        "templates": [
            "Entendido, digame.",
            "Claro, comprendo. Digame.",
            "De acuerdo, adelante.",
            "Muy bien, le escucho.",
        ],
        "variables": [],
    },

    "ACEPTAR_RECHAZO": {
        "fase": "SITUACIONAL",
        "templates": [
            "Entendido, disculpe la molestia. Que tenga buen dia.",
            "Comprendo, no hay problema. Que tenga excelente dia.",
            "Entiendo, gracias por su tiempo. Que le vaya bien.",
        ],
        "variables": [],
    },

    "RECONOCER_OCUPADO": {
        "fase": "SITUACIONAL",
        "templates": [
            "Entiendo que esta ocupado. Me permite enviarle la informacion por WhatsApp para que la revise con calma?",
            "Comprendo, no le quito mas tiempo. Le puedo mandar el catalogo por WhatsApp o correo?",
            "No se preocupe. Le parece si le envio la informacion para que la vea cuando pueda?",
        ],
        "variables": [],
    },

    # ================================================================
    # FASE 7: RESPONDER PREGUNTAS (1.2%)
    # ================================================================

    "RESPONDER_UBICACION": {
        "fase": "PREGUNTAS",
        "templates": [
            "Somos de Guadalajara, Jalisco. Distribuimos a toda la republica.",
            "Estamos en Guadalajara, Jalisco. Hacemos envios a todo el pais.",
            "Nuestra empresa esta en Guadalajara. Manejamos envios a toda la republica.",
        ],
        "variables": [],
    },

    "RESPONDER_QUIEN_ES_NIOVAL": {
        "fase": "PREGUNTAS",
        "templates": [
            "NIOVAL es una empresa de Guadalajara que distribuye productos de ferreteria: cintas, griferia, herramientas y mas.",
            "Somos NIOVAL, distribuidores de productos ferreteros. Manejamos mas de 15 categorias de productos.",
            "NIOVAL es una marca de productos de ferreteria. Distribuimos cintas tapagoteras, griferia, herramientas y accesorios.",
        ],
        "variables": [],
    },

    "MENCIONAR_CONTACTO_BRUCE": {
        "fase": "PREGUNTAS",
        "templates": [
            "Nuestro WhatsApp es 6 6 2 4 1 5 1 9 9 7 y el correo es ventas arroba nioval punto com.",
            "Me puede contactar al 6 6 2 4 1 5 1 9 9 7 o al correo ventas arroba nioval punto com.",
            "Le dejo nuestro contacto: WhatsApp 6 6 2 4 1 5 1 9 9 7, correo ventas arroba nioval punto com.",
        ],
        "variables": [],
    },

    "RESPONDER_PRECIOS": {
        "fase": "PREGUNTAS",
        "templates": [
            "Los precios dependen del volumen y los productos. En el catalogo vienen todos los precios. Se lo envio?",
            "Manejamos diferentes precios segun el producto. Le puedo enviar el catalogo con precios para que los revise.",
            "Los precios varian segun el producto y la cantidad. Le envio el catalogo para que los vea?",
        ],
        "variables": [],
    },

    "RESPONDER_ENVIOS": {
        "fase": "PREGUNTAS",
        "templates": [
            "Si, hacemos envios a toda la republica. El catalogo incluye informacion de envios.",
            "Manejamos envios a todo el pais. En el catalogo viene esa informacion.",
            "Claro, distribuimos a toda la republica. Le envio el catalogo con los detalles?",
        ],
        "variables": [],
    },

    "RESPONDER_PREGUNTA_GENERICA": {
        "fase": "PREGUNTAS",
        "templates": [
            "Esa informacion viene en nuestro catalogo. Se lo puedo enviar por WhatsApp o correo?",
            "Con gusto. Toda esa informacion la puede encontrar en nuestro catalogo digital. Se lo envio?",
            "Claro. Le puedo mandar el catalogo con toda la informacion detallada. Tiene WhatsApp?",
        ],
        "variables": [],
    },
}

# ============================================================
# ACCIONES VALIDAS PARA GPT FALLBACK
# ============================================================
ACCIONES_VALIDAS = list(BTE_CATALOG.keys())


# ============================================================
# BTE ENGINE - Motor principal
# ============================================================

class BTEEngine:
    """Motor de templates que reemplaza GPT libre."""

    def __init__(self):
        self._historial_templates = []  # Ultimos templates usados (anti-repeticion)
        self._contador_por_accion = {}  # accion -> indice de variante (rotacion)

    def decidir_accion(self, fsm_intent, fsm_state, lead_data, conversation_history,
                       texto_cliente="", turno=0) -> Optional[str]:
        """
        Decide que accion tomar basado en FSM intent/state y contexto.
        Retorna nombre de accion del catalogo o None si necesita GPT fallback.

        Prioridad: Intent fuerte > State+texto > Text patterns > Default
        """
        intent = str(fsm_intent).split('.')[-1] if fsm_intent else ""
        state = str(fsm_state).split('.')[-1] if fsm_state else ""
        t = texto_cliente.lower().strip() if texto_cliente else ""
        t_norm = t.replace('á', 'a').replace('é', 'e').replace('í', 'i').replace('ó', 'o').replace('ú', 'u')
        history = conversation_history or []
        data = lead_data or {}

        # =============================================================
        # PRIORIDAD 1: Intent fuerte (FSM ya clasifico)
        # =============================================================

        # Saludo / Inicio
        if intent in ('GREETING', 'SALUDO'):
            if not self._ya_se_presento(history):
                return "PRESENTACION_Y_PEDIR_ENCARGADO"
            return "CONFIRMAR_ESCUCHA"

        # Saludo simple (IVR/conmutador)
        if intent in ('SALUDO_SIMPLE', 'IVR'):
            return "SALUDO_SIMPLE"

        # Transferencia
        if intent == 'TRANSFER':
            return "ESPERANDO_TRANSFERENCIA"

        # No interes / Rechazo duro
        if intent in ('NO_INTEREST', 'REJECT', 'RECHAZO'):
            return "DESPEDIDA_PUERTA_ABIERTA"

        # Otra sucursal / numero equivocado
        if intent in ('ANOTHER_BRANCH', 'WRONG_NUMBER'):
            return "ACEPTAR_RECHAZO"

        # Rechazo de canal (no tengo WhatsApp, etc)
        if intent in ('REJECT_DATA', 'REJECT_CHANNEL'):
            return self._accion_post_rechazo_dato(data)

        # Cliente es encargado / muestra interes
        if intent in ('INTEREST', 'ENCARGADO_PRESENTE', 'IDENTITY'):
            if self._ya_hizo_pitch(history):
                if self._ya_pidio_contacto(history, data):
                    return "CONFIRMAR_Y_AGRADECER"
                return "PEDIR_WHATSAPP"
            return "PITCH_ENCARGADO_CORTO"

        # Encargado no esta
        if intent in ('NOT_AVAILABLE', 'ENCARGADO_AUSENTE'):
            return "OFRECER_CALLBACK"

        # Callback
        if intent == 'CALLBACK':
            if self._tiene_hora_callback(texto_cliente):
                return "CONFIRMAR_Y_AGRADECER"
            return "PREGUNTAR_HORARIO_CALLBACK"

        # Confirmacion del cliente
        if intent in ('CONFIRMATION', 'CONFIRM', 'YES'):
            return self._accion_post_confirmacion(history, data, state)

        # Cliente ofrece/dicta dato
        if intent in ('OFFER_DATA', 'DICTA_NUMERO', 'DICTA_EMAIL'):
            # Si ya hay dato completo capturado -> confirmar anotado
            if data.get('whatsapp') or data.get('correo') or data.get('telefono_contacto'):
                return "CONFIRMAR_NUMERO_ANOTADO"
            # Si hay digitos parciales -> pedir numero completo
            if data.get('digitos_parciales'):
                return "PEDIR_NUMERO_COMPLETO"
            return "CONFIRMAR_DATO"

        # Verificacion de conexion
        if intent in ('VERIFICATION', 'CHECK'):
            return "CONFIRMAR_ESCUCHA"

        # Pregunta del cliente
        if intent in ('QUESTION', 'PREGUNTA'):
            return self._responder_pregunta(texto_cliente)

        # Cliente ocupado
        if intent in ('BUSY', 'OCCUPIED'):
            return "RECONOCER_OCUPADO"

        # Continuacion generica (aja, ok, si)
        if intent in ('CONTINUATION', 'FILLER'):
            return self._accion_continuacion(history, state, data)

        # Confusion / No entendio
        if intent in ('UNCLEAR', 'CONFUSION', 'CORRECTION'):
            return "MANEJAR_CONFUSION"

        # Timeout / silencio
        if intent in ('TIMEOUT', 'SILENCE', 'NO_AUDIO'):
            return "MANEJAR_TIMEOUT"

        # =============================================================
        # PRIORIDAD 2: State + texto (FSM no resolvio intent)
        # =============================================================

        if state in ('saludo',):
            if not self._ya_se_presento(history):
                return "PRESENTACION_Y_PEDIR_ENCARGADO"
            return "SALUDO_Y_PEDIR_ENCARGADO"

        if state in ('pitch', 'encargado_presente'):
            return self._accion_en_pitch(t_norm, history, data)

        if state in ('buscando_encargado', 'esperando_transferencia'):
            return self._accion_buscando_encargado(t_norm, history)

        if state in ('capturando_contacto', 'dictando_dato'):
            return self._accion_capturando_contacto(t_norm, history, data)

        if state in ('encargado_ausente',):
            return self._accion_encargado_ausente(t_norm, history, data)

        if state in ('ofreciendo_contacto',):
            return "DAR_NUMERO_BRUCE"

        if state in ('despedida', 'contacto_capturado'):
            return "DESPEDIDA"

        # =============================================================
        # PRIORIDAD 3: Patrones de texto (sin intent ni state)
        # =============================================================

        # Cliente pregunta identidad de Bruce
        if any(w in t_norm for w in ['de parte de quien', 'quien habla', 'quien es usted', 'de donde me llama']):
            if not self._ya_se_presento(history):
                return "PRESENTACION_NIOVAL"
            return "RESPONDER_UBICACION"

        # Problemas de conexion
        if any(w in t_norm for w in ['no le escucho', 'no se oye', 'se corto', 'no escucho nada']):
            return "MANEJAR_TIMEOUT"

        # Cliente ocupado
        if any(w in t_norm for w in ['estoy ocupado', 'no tengo tiempo', 'ahorita no puedo', 'estamos ocupados']):
            return "RECONOCER_OCUPADO"

        # Cliente pide contacto de Bruce
        if any(w in t_norm for w in ['dame tu numero', 'pasa tu numero', 'cual es tu numero',
                                      'cual es el contacto', 'como te contacto', 'tus datos',
                                      'pasame tus datos', 'dame tus datos']):
            return "MENCIONAR_CONTACTO_BRUCE"

        # Preguntas frecuentes
        if any(w in t_norm for w in ['de donde', 'donde estan', 'de que ciudad']):
            return "RESPONDER_UBICACION"
        if any(w in t_norm for w in ['que es nioval', 'que venden', 'que manejan', 'que productos']):
            return "RESPONDER_QUIEN_ES_NIOVAL"
        if any(w in t_norm for w in ['precio', 'cuanto cuesta', 'cuanto sale']):
            return "RESPONDER_PRECIOS"
        if any(w in t_norm for w in ['envian', 'envios', 'mandan']):
            return "RESPONDER_ENVIOS"

        # Respuestas cortas (bueno, digame, mande)
        if any(w in t_norm for w in ['bueno', 'digame', 'diga', 'mande', 'si digame']):
            if not self._ya_se_presento(history):
                return "PRESENTACION_Y_PEDIR_ENCARGADO"
            return "CONFIRMAR_ESCUCHA"

        # Turno 1 sin info -> presentarse
        if turno <= 1 and not intent and not state and not self._ya_se_presento(history):
            return "PRESENTACION_Y_PEDIR_ENCARGADO"

        # No se pudo resolver -> GPT fallback
        return None

    def generar_respuesta(self, accion: str, contexto: dict = None) -> str:
        """
        Genera texto de respuesta usando el template de la accion.
        Inyecta variables del contexto.
        """
        if accion not in BTE_CATALOG:
            return None

        template_info = BTE_CATALOG[accion]
        templates = template_info["templates"]

        # Rotacion ciclica de variantes (anti-repeticion)
        idx = self._contador_por_accion.get(accion, 0)
        template = templates[idx % len(templates)]
        self._contador_por_accion[accion] = idx + 1

        # Anti-repeticion: si este template exacto fue usado recientemente, rotar
        if template in self._historial_templates[-5:]:
            idx += 1
            template = templates[idx % len(templates)]
            self._contador_por_accion[accion] = idx + 1

        # Inyectar variables
        if contexto and template_info.get("variables"):
            for var in template_info["variables"]:
                if var in contexto:
                    template = template.replace(f"{{{var}}}", str(contexto[var]))

        # Registrar en historial
        self._historial_templates.append(template)
        if len(self._historial_templates) > 20:
            self._historial_templates = self._historial_templates[-20:]

        return template

    def process(self, texto_cliente: str, fsm_intent=None, fsm_state=None,
                lead_data: dict = None, conversation_history: list = None,
                turno: int = 0) -> Optional[str]:
        """
        Punto de entrada principal.
        Intenta resolver con template. Retorna None si necesita GPT.
        """
        lead_data = lead_data or {}
        conversation_history = conversation_history or []

        accion = self.decidir_accion(
            fsm_intent=fsm_intent,
            fsm_state=fsm_state,
            lead_data=lead_data,
            conversation_history=conversation_history,
            texto_cliente=texto_cliente,
            turno=turno,
        )

        if accion is None:
            return None

        contexto = {
            "canal": lead_data.get("canal_preferido", "WhatsApp"),
            "digitos": lead_data.get("digitos_capturados", "algunos"),
            "nombre_cliente": lead_data.get("nombre_contacto", ""),
            "nombre_negocio": lead_data.get("nombre_negocio", ""),
        }

        respuesta = self.generar_respuesta(accion, contexto)

        if respuesta:
            print(f"  [BTE] Accion: {accion} -> '{respuesta[:60]}...'")

        return respuesta

    # ============================================================
    # HELPERS INTERNOS
    # ============================================================

    def _ya_se_presento(self, history: list) -> bool:
        """Verifica si Bruce ya se presento en la conversacion."""
        for msg in history:
            if msg.get('role') == 'assistant':
                t = msg['content'].lower()
                if any(w in t for w in ['nioval', 'bruce', 'productos ferreteros', 'ferreteria']):
                    return True
        return False

    def _ya_hizo_pitch(self, history: list) -> bool:
        """Verifica si Bruce ya hizo el pitch de productos."""
        for msg in history:
            if msg.get('role') == 'assistant':
                t = msg['content'].lower()
                if any(w in t for w in ['catalogo', 'catálogo', 'productos', 'ferreteria', 'ferretería']):
                    return True
        return False

    def _ya_pidio_contacto(self, history: list, lead_data: dict) -> bool:
        """Verifica si ya se pidio WhatsApp/correo."""
        if lead_data.get('whatsapp') or lead_data.get('correo') or lead_data.get('telefono_contacto'):
            return True
        for msg in history:
            if msg.get('role') == 'assistant':
                t = msg['content'].lower()
                if any(w in t for w in ['whatsapp', 'correo', 'numero']):
                    return True
        return False

    def _tiene_hora_callback(self, texto: str) -> bool:
        """Verifica si el texto incluye una hora para callback."""
        t = texto.lower()
        return bool(re.search(r'\b(las|a las|de las)\s+\w+\b|\b\d{1,2}\s*(am|pm|de la|hrs)\b|\bmanana\b|\blunes\b|\bmartes\b', t))

    def _accion_post_confirmacion(self, history: list, lead_data: dict, state: str = "") -> str:
        """Decide que hacer despues de que el cliente confirma."""
        # Si ya tiene WhatsApp capturado -> confirmar envio por WhatsApp
        if lead_data.get('whatsapp'):
            return "CONFIRMAR_ENVIO_WHATSAPP"
        # Si ya tiene correo capturado -> confirmar envio por correo
        if lead_data.get('correo'):
            return "CONFIRMAR_ENVIO_CORREO"
        # Si ya se ofrecio catalogo pero no se pidio contacto -> pedir WhatsApp
        if self._ya_hizo_pitch(history):
            return "PEDIR_WHATSAPP"
        # No pitch aun -> pitch
        return "PITCH_ENCARGADO_CORTO"

    def _accion_post_rechazo_dato(self, lead_data: dict) -> str:
        """Decide que hacer cuando el cliente rechaza un canal."""
        sin_wapp = lead_data.get('sin_whatsapp', False)
        sin_correo = lead_data.get('sin_correo', False)
        sin_tel = lead_data.get('sin_telefono', False)
        if sin_wapp and sin_correo:
            if sin_tel:
                return "DAR_NUMERO_BRUCE"
            return "DAR_NUMERO_BRUCE"  # Ofrecer numero de Bruce como ultima opcion
        if sin_wapp:
            return "PEDIR_CORREO"
        return "PEDIR_CORREO"

    def _responder_pregunta(self, texto: str) -> str:
        """Mapea pregunta del cliente a accion."""
        t = texto.lower().replace('á', 'a').replace('é', 'e').replace('í', 'i').replace('ó', 'o').replace('ú', 'u')
        if any(w in t for w in ['donde estan', 'de donde', 'que ciudad', 'ubicacion']):
            return "RESPONDER_UBICACION"
        if any(w in t for w in ['que es nioval', 'que venden', 'que manejan', 'que productos']):
            return "RESPONDER_QUIEN_ES_NIOVAL"
        if any(w in t for w in ['precio', 'cuanto cuesta', 'cuanto sale', 'cuanto cobran']):
            return "RESPONDER_PRECIOS"
        if any(w in t for w in ['envio', 'mandan', 'envian', 'a todo el pais']):
            return "RESPONDER_ENVIOS"
        if any(w in t for w in ['tu numero', 'tus datos', 'tu contacto', 'como te contacto']):
            return "MENCIONAR_CONTACTO_BRUCE"
        return "RESPONDER_PREGUNTA_GENERICA"

    def _accion_continuacion(self, history: list, state: str, lead_data: dict) -> str:
        """Cuando el cliente dice algo generico (aja, ok, si) sin intent claro."""
        if state in ('pitch', 'encargado_presente'):
            if self._ya_hizo_pitch(history):
                return "OFRECER_ENVIAR_CATALOGO"
            return "PREGUNTAR_SI_QUIERE_CATALOGO"
        if state in ('capturando_contacto', 'dictando_dato'):
            return "PEDIR_NUMERO"
        if state in ('ofreciendo_contacto',):
            return "DAR_NUMERO_BRUCE"
        if state in ('contacto_capturado',):
            return "MENCIONAR_CATALOGO"
        return "ACKNOWLEDGMENT"

    def _accion_en_pitch(self, t_norm: str, history: list, lead_data: dict) -> str:
        """Acciones cuando estamos en estado de pitch."""
        # Cliente es el encargado
        if any(w in t_norm for w in ['yo soy', 'soy yo', 'soy el encargado', 'conmigo', 'yo mero', 'soy el dueno']):
            if self._ya_hizo_pitch(history):
                return "OFRECER_ENVIAR_CATALOGO"
            return "PITCH_ENCARGADO_CORTO"
        # Cliente acepta/confirma
        if any(w in t_norm for w in ['si', 'claro', 'orale', 'dale', 'va', 'por supuesto', 'andale']):
            if self._ya_hizo_pitch(history):
                return "OFRECER_ENVIAR_CATALOGO"
            return "PREGUNTAR_SI_QUIERE_CATALOGO"
        # Cliente pregunta por productos
        if any(w in t_norm for w in ['que productos', 'que manejan', 'que venden', 'que tienen']):
            return "PITCH_PRODUCTOS"
        # No interes
        if any(w in t_norm for w in ['no me interesa', 'no gracias', 'no necesito']):
            return "DESPEDIDA_PUERTA_ABIERTA"
        # Ocupado
        if any(w in t_norm for w in ['estoy ocupado', 'no tengo tiempo', 'ahorita no']):
            return "RECONOCER_OCUPADO"
        # Default en pitch: mencionar productos
        return "MENCIONAR_PRODUCTOS"

    def _accion_buscando_encargado(self, t_norm: str, history: list) -> str:
        """Acciones cuando buscamos al encargado."""
        if any(w in t_norm for w in ['no esta', 'salio', 'no se encuentra', 'no vino', 'no viene']):
            return "OFRECER_CALLBACK"
        if any(w in t_norm for w in ['yo soy', 'soy yo', 'yo mero', 'conmigo', 'soy el encargado', 'soy el dueno']):
            return "PITCH_ENCARGADO_CORTO"
        if any(w in t_norm for w in ['un momento', 'ahorita', 'espere', 'le paso', 'se lo paso', 'se lo comunico']):
            return "ESPERANDO_TRANSFERENCIA"
        # Cliente dice "si" o "bueno" -> pedir que nos comuniquen
        if any(w in t_norm for w in ['si', 'bueno', 'digame', 'aja']):
            return "PEDIR_COMUNICAR_ENCARGADO"
        return "PREGUNTAR_POR_ENCARGADO"

    def _accion_capturando_contacto(self, t_norm: str, history: list, lead_data: dict) -> str:
        """Acciones cuando estamos capturando datos de contacto."""
        if any(w in t_norm for w in ['no tengo whatsapp', 'no tengo wats', 'no manejo whatsapp']):
            return "PEDIR_CORREO"
        if any(w in t_norm for w in ['no tengo correo', 'no manejo correo']):
            return "DAR_NUMERO_BRUCE"
        # Cliente confirma con dato ya capturado
        if lead_data.get('whatsapp') and any(w in t_norm for w in ['si', 'claro', 'correcto', 'esta bien']):
            return "CONFIRMAR_ENVIO_WHATSAPP"
        if lead_data.get('correo') and any(w in t_norm for w in ['si', 'claro', 'correcto', 'esta bien']):
            return "CONFIRMAR_ENVIO_CORREO"
        # Cliente dice "si" -> listo para dar numero
        if any(w in t_norm for w in ['si', 'claro', 'dale', 'orale', 'va', 'por supuesto', 'anote', 'apunte']):
            return "PEDIR_NUMERO"
        return "PEDIR_WHATSAPP"

    def _accion_encargado_ausente(self, t_norm: str, history: list, lead_data: dict) -> str:
        """Acciones cuando el encargado no esta."""
        if self._tiene_hora_callback(t_norm):
            return "CONFIRMAR_Y_AGRADECER"
        if any(w in t_norm for w in ['llame', 'marque', 'regrese', 'mas tarde', 'despues']):
            return "PREGUNTAR_HORARIO_CALLBACK"
        return "OFRECER_CALLBACK"

    # ============================================================
    # GPT FALLBACK CLASIFICADOR (JSON mode)
    # Para el ~6% de casos que BTE no puede resolver
    # ============================================================

    def gpt_fallback_clasificar(self, texto_cliente: str, conversation_history: list,
                                 lead_data: dict, openai_client=None) -> Optional[str]:
        """
        Usa GPT en JSON mode para clasificar la accion.
        GPT NO genera texto, solo elige de ACCIONES_VALIDAS.
        Retorna nombre de accion o None si falla.
        """
        if not openai_client:
            return None

        # Construir contexto compacto
        ultimos_turnos = conversation_history[-6:] if conversation_history else []
        historial_str = "\n".join(
            f"{'BRUCE' if m['role']=='assistant' else 'CLIENTE'}: {m['content'][:100]}"
            for m in ultimos_turnos
        )

        datos_capturados = []
        if lead_data.get('whatsapp'): datos_capturados.append(f"WhatsApp: {lead_data['whatsapp']}")
        if lead_data.get('correo'): datos_capturados.append(f"Correo: {lead_data['correo']}")
        if lead_data.get('sin_whatsapp'): datos_capturados.append("Cliente NO tiene WhatsApp")
        if lead_data.get('sin_correo'): datos_capturados.append("Cliente NO tiene correo")

        prompt = f"""Eres un clasificador de acciones para Bruce, agente de ventas de NIOVAL (productos ferreteros).

HISTORIAL RECIENTE:
{historial_str}

CLIENTE DICE AHORA: "{texto_cliente}"

DATOS CAPTURADOS: {', '.join(datos_capturados) if datos_capturados else 'Ninguno'}

ACCIONES DISPONIBLES:
{json.dumps(ACCIONES_VALIDAS, indent=2)}

Responde SOLO con JSON: {{"accion": "NOMBRE_ACCION"}}
Elige la accion mas apropiada. Si ninguna aplica exactamente, elige la mas cercana."""

        try:
            response = openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "system", "content": prompt}],
                response_format={"type": "json_object"},
                temperature=0.1,
                max_tokens=50,
                timeout=3,
            )
            result = json.loads(response.choices[0].message.content)
            accion = result.get("accion", "")
            if accion in ACCIONES_VALIDAS:
                print(f"  [BTE-GPT] Fallback clasifico: {accion}")
                return accion
            else:
                print(f"  [BTE-GPT] Accion invalida: {accion}")
                return None
        except Exception as e:
            print(f"  [BTE-GPT] Error fallback: {e}")
            return None


# Instancia global
bte_engine = BTEEngine()
