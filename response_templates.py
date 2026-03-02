"""
response_templates.py - Banco de templates y narrow prompts para FSM Bruce W.

41 templates en español mexicano natural + 6 narrow prompts GPT.
Los templates cubren ~90% de los turnos conversacionales.
FIX 791: +6 templates stateful para UNKNOWN (reemplazan GPT_NARROW conversacion_libre).
GPT narrow solo se usa para preguntas de producto y situaciones complejas.
"""

# ============================================================
# TEMPLATES DE RESPUESTA (español mexicano natural)
# ============================================================
# Cada key mapea a una lista de variantes (se usa la primera por defecto).
# Las variantes adicionales son para futura rotación/personalización.

TEMPLATES = {
    # === PITCH / PRESENTACIÓN ===
    "pitch_inicial": [
        "Le comento, me comunico de la marca NIOVAL. Somos distribuidores de productos "
        "ferreteros. Manejamos mas de quince categorias: cintas tapagoteras, griferia, "
        "herramientas, candados y mucho mas. "
        "¿Se encontrara el encargado o encargada de compras?",
    ],
    # FIX 846: Cambiado "Me comunico de la marca NIOVAL" → "Le llamo de parte de NIOVAL"
    # para evitar que _PITCH_NIOVAL matchee 2 veces (pitch_inicial + pitch_persona_nueva)
    # y cause PITCH_REPETIDO en bug_detector
    "pitch_persona_nueva": [
        "Hola, buen dia. Le llamo de parte de NIOVAL para ofrecerle informacion de "
        "nuestros productos de ferreteria. "
        "¿Se encontrara el encargado o encargada de compras?",
    ],
    "pitch_encargado": [
        "Excelente. Le comento, somos NIOVAL, distribuidores de productos ferreteros. "
        "Manejamos cintas tapagoteras, griferia, herramientas, candados y mas de "
        "quince categorias. "
        "¿Le gustaria recibir nuestro catalogo por WhatsApp o correo electronico?",
    ],

    # === IDENTIFICACIÓN ===
    "identificacion_nioval": [
        "Mi nombre es Bruce, le llamo de la marca NIOVAL. Somos distribuidores "
        "de productos ferreteros de Guadalajara, Jalisco.",
    ],
    "identificacion_pitch": [
        "Mi nombre es Bruce, le llamo de NIOVAL. Somos distribuidores de productos "
        "ferreteros. Manejamos mas de quince categorias. "
        "¿Se encontrara el encargado de compras?",
    ],

    # === ENCARGADO ===
    "preguntar_encargado": [
        "¿Se encontrara el encargado o encargada de compras?",
    ],

    # === SOLICITAR CONTACTO ===
    # FIX 847: Removida mención de "catálogo" en pedir_whatsapp/pedir_correo
    # para evitar CATALOGO_REPETIDO (combined con confirmar_telefono ya suman 2 matches)
    "pedir_whatsapp": [
        "¿Me podria proporcionar un numero de WhatsApp?",
    ],
    "pedir_correo": [
        "¿Me podria dar un correo electronico?",
    ],
    "pedir_telefono": [
        "¿Me podria dar un telefono fijo o directo del encargado?",
    ],
    "pedir_alternativa_correo": [
        "Entiendo. ¿Me podria proporcionar un correo electronico entonces?",
    ],
    "pedir_alternativa_telefono": [
        "Entiendo. ¿Me podria dar un telefono fijo o directo entonces?",
    ],
    "pedir_alternativa_whatsapp": [
        "Entiendo. ¿Tendra un WhatsApp donde le pueda enviar la informacion?",
    ],
    # FIX 841: Removida mención de "catálogo" para evitar CATALOGO_REPETIDO
    # (confirmar_telefono/correo ya incluye la promesa del catálogo)
    "pedir_contacto_alternativo": [
        "Entiendo que no se encuentra. ¿Me podria proporcionar un WhatsApp o correo "
        "del encargado?",
    ],
    "digame_numero": [
        "Claro, digame por favor.",
        "Si, digame el numero.",
        "Adelante, le escucho.",
    ],

    # === DICTADO / ACKNOWLEDGMENT ===
    # FIX 769: Variantes formales con rotación (evitar repetición)
    # FIX 803: "continue" → "prosiga" (TTS pronunciaba como portugués)
    "aja_si": [
        "Si, adelante.",
        "Claro, prosiga.",
        "Si, lo escucho.",
        "Entendido, prosiga.",
        "Perfecto, adelante.",
    ],
    "aja_digame": [
        "Claro, digame.",
        "Si, adelante, digame.",
        "Perfecto, digame.",
        "Entendido, digame.",
    ],

    # === CONFIRMACIÓN DE DATO CAPTURADO ===
    "confirmar_telefono": [
        "Perfecto, ya tengo el numero registrado. Le envio el catalogo en las "
        "proximas dos horas. Muchas gracias por su tiempo.",
    ],
    "confirmar_correo": [
        "Perfecto, ya tengo el correo registrado. Le envio el catalogo en las "
        "proximas dos horas. Muchas gracias por su tiempo.",
    ],
    "confirmar_dato_generico": [
        "Perfecto, ya lo tengo anotado. Le envio el catalogo en las proximas "
        "dos horas. Muchas gracias por su tiempo.",
    ],

    # === OFRECER CONTACTO DE BRUCE ===
    "ofrecer_contacto_bruce": [
        "¿Le puedo dejar mi numero para que el encargado nos contacte cuando guste?",
    ],
    "tiene_donde_anotar": [
        "Perfecto. ¿Tiene donde anotar?",
    ],
    "dictar_numero_bruce": [
        "Nuestro numero es 662 353 1804. Le repito, 662 353 1804. "
        "Somos NIOVAL, distribuidores de productos ferreteros.",
    ],

    # === TRANSFER / ESPERA ===
    "claro_espero": [
        "Claro, espero.",
    ],

    # === CALLBACK ===
    "preguntar_hora_callback": [
        "¿A que hora me recomienda llamar para encontrar al encargado?",
    ],
    "confirmar_callback": [
        "Perfecto, le marco {hora}. Muchas gracias por su tiempo, que tenga "
        "excelente dia.",
    ],
    "confirmar_callback_generico": [
        "Perfecto, le vuelvo a llamar mas tarde. Muchas gracias por su tiempo, "
        "que tenga excelente dia.",
    ],

    # === DESPEDIDAS ===
    "despedida_cortes": [
        "Muchas gracias por su tiempo. Que tenga excelente dia. Hasta pronto.",
    ],
    "despedida_no_interesa": [
        "Entendido, no se preocupe. Le dejo nuestro numero por si mas adelante "
        "le interesa. Que tenga buen dia.",
    ],
    "despedida_otra_sucursal": [
        "Entiendo, disculpe la molestia. ¿Me podria indicar el telefono de la "
        "sucursal correcta?",
    ],
    "despedida_cerrado": [
        "Entiendo, disculpe la molestia. Que tenga buen dia.",
    ],
    # FIX 744: Area equivocada / no tengo negocio
    "despedida_area_equivocada": [
        "Disculpe la molestia, que tenga buen dia.",
    ],
    "despedida_sin_contacto": [
        "Entendido, no se preocupe. Le vuelvo a llamar mas tarde. "
        "Muchas gracias por su tiempo.",
    ],
    "despedida_catalogo_prometido": [
        "Perfecto. En las proximas dos horas le llega el catalogo. "
        "Muchas gracias por su tiempo. Que tenga excelente dia.",
    ],
    "despedida_no_compras": [
        "Entendido, disculpe la molestia. Que tenga buen dia.",
    ],

    # === PREGUNTAS OBVIAS ===
    "respuesta_robot": [
        "No, soy Bruce, agente de ventas de NIOVAL. ¿En que le puedo ayudar?",
    ],
    "respuesta_escuchas": [
        "Si, le escucho perfectamente, digame.",
    ],
    "respuesta_listo_anotar": [
        "Si, claro, digame por favor.",
    ],

    # === RECONEXIÓN / VERIFICACIÓN ===
    "verificacion_aqui_estoy": [
        "Si, aqui estoy. Digame.",
    ],
    "no_escuche_repetir": [
        "Disculpe, no alcance a captar. ¿Me puede repetir?",
    ],

    # === FIX 791: Templates stateful para UNKNOWN (reemplazan GPT_NARROW) ===
    "repitch_encargado": [
        "Claro, le comento. Somos distribuidores de la marca NIOVAL, manejamos "
        "productos ferreteros de alta calidad. "
        "¿Me podria comunicar con el encargado de compras?",
    ],
    "pedir_whatsapp_o_correo": [
        "Perfecto, muchas gracias. ¿Me podria proporcionar un numero de WhatsApp "
        "o correo electronico para enviarle la informacion?",
    ],
    "pitch_catalogo_whatsapp": [
        "Con mucho gusto. Manejamos una amplia linea de productos ferreteros de la "
        "marca NIOVAL. ¿Le puedo enviar nuestro catalogo por WhatsApp?",
    ],
    "preguntar_horario_encargado": [
        "Entiendo, no se preocupe. ¿Hay algun horario en el que pueda encontrar "
        "al encargado de compras?",
    ],
    "ofrecer_catalogo_sin_compromiso": [
        "Claro, le comento. Somos distribuidores de NIOVAL. "
        "¿Le interesa recibir nuestro catalogo sin compromiso?",
    ],
    "despedida_agradecimiento": [
        "Claro que si. Le agradezco mucho su tiempo. Que tenga excelente dia.",
    ],
}


# ============================================================
# NARROW PROMPTS GPT (single-purpose, max 2-3 líneas de sistema)
# ============================================================
# Estos reemplazan el system prompt masivo de 750+ reglas.
# Cada prompt tiene UN solo propósito y genera respuestas cortas.

NARROW_PROMPTS = {
    "responder_pregunta_producto": {
        "system": (
            "Eres Bruce, vendedor de NIOVAL (productos ferreteros de Guadalajara). "
            "El cliente hizo una pregunta sobre productos, precios o la empresa. "
            "Responde en 1-2 oraciones, mexicano coloquial. "
            "Productos: cintas tapagoteras, griferia, herramientas, candados, "
            "silicones, adhesivos, cerraduras, y mas de 15 categorias. "
            "REGLAS: NO preguntes nada, solo responde la pregunta. "
            "NO repitas informacion que ya dijiste. "
            "Si no sabes un precio exacto, di 'con gusto le envio la lista de precios'."
        ),
        "max_tokens": 80,
        "temperature": 0.5,
    },

    "generar_despedida": {
        "system": (
            "Eres Bruce, vendedor de NIOVAL. "
            "El cliente quiere terminar la llamada. Genera una despedida cortes "
            "en 1 oracion. Incluye 'que tenga buen dia' y 'hasta pronto'. "
            "Mexicano coloquial, profesional."
        ),
        "max_tokens": 40,
        "temperature": 0.3,
    },

    "manejar_objecion": {
        "system": (
            "Eres Bruce, vendedor de NIOVAL (productos ferreteros). "
            "El cliente expreso una objecion o duda. Responde con empatia "
            "en 1-2 oraciones. NO insistas si el rechazo es firme. "
            "Si hay duda, ofrece enviar catalogo sin compromiso. "
            "Mexicano coloquial."
        ),
        "max_tokens": 80,
        "temperature": 0.5,
    },

    "confirmar_dato_dictado": {
        "system": (
            "El cliente acaba de dictar un dato de contacto (telefono, email, nombre). "
            "Confirma el dato recibido y despidete prometiendo el catalogo. "
            "1-2 oraciones, mexicano coloquial."
        ),
        "max_tokens": 60,
        "temperature": 0.3,
    },

    "conversacion_libre": {
        "system": (
            "Eres Bruce, vendedor de NIOVAL (productos ferreteros: cintas, griferia, "
            "herramientas, candados). La conversacion esta en una situacion no estandar. "
            "REGLAS ABSOLUTAS:\n"
            "1. Si cliente ya dijo un dato (nombre, telefono, correo, WhatsApp) "
            "en CUALQUIER turno anterior, NUNCA pedir ese dato de nuevo\n"
            "2. Si cliente rechazo un canal ('no tengo WhatsApp', 'no tengo correo'), "
            "NO pedir ese canal. Ofrecer alternativa distinta\n"
            "3. Si encargado no esta, pedir contacto alternativo (WhatsApp, correo o telefono)\n"
            "4. Maximo 2 oraciones, mexicano coloquial\n"
            "5. NO repetir frases que Bruce ya dijo en turnos anteriores\n"
            "Estado actual: {state}\n"
            "Contexto: {context_summary}"
        ),
        "max_tokens": 100,
        "temperature": 0.5,
    },

    "personalizar_template": {
        "system": (
            "Tienes un template de respuesta y contexto de conversacion. "
            "Haz una variacion MINIMA del template para que suene natural "
            "en este contexto. NO cambies el significado ni la intencion. "
            "Solo ajusta 1-2 palabras si es necesario. "
            "Retorna SOLO la respuesta modificada, nada mas."
        ),
        "max_tokens": 80,
        "temperature": 0.3,
    },
}
