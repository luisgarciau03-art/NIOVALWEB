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
    # FIX 912: Pitch corto con beneficios, NO lista de categorias (anti FLUJO_ROBOTICO)
    # FIX 924: Enfoque en valor, no en enumerar productos
    "pitch_inicial": [
        "Le comento, me comunico de la marca NIOVAL. Somos distribuidores de productos "
        "ferreteros con precios muy competitivos y entrega directa. "
        "¿Se encontrara el encargado o encargada de compras?",
        "Le llamo de NIOVAL, somos distribuidores de productos ferreteros de "
        "Guadalajara. Manejamos una linea muy completa a buenos precios. "
        "¿Se encontrara el encargado de compras?",
        "Buenos dias, le hablo de NIOVAL. Somos proveedores de productos ferreteros "
        "con precios de fabrica. ¿Podria hablar con el encargado de compras?",
    ],
    # FIX 846: Cambiado "Me comunico de la marca NIOVAL" → "Le llamo de parte de NIOVAL"
    # para evitar que _PITCH_NIOVAL matchee 2 veces (pitch_inicial + pitch_persona_nueva)
    # y cause PITCH_REPETIDO en bug_detector
    "pitch_persona_nueva": [
        "Hola, buen dia. Le llamo de parte de NIOVAL para ofrecerle informacion de "
        "nuestros productos de ferreteria. "
        "¿Se encontrara el encargado o encargada de compras?",
    ],
    # FIX 912: Pitch encargado corto con beneficios (anti FLUJO_ROBOTICO)
    "pitch_encargado": [
        "Excelente. Le comento, somos NIOVAL, distribuidores de productos ferreteros "
        "con precios de fabrica y entrega directa. "
        "¿Le gustaria recibir nuestro catalogo con lista de precios?",
        "Perfecto. Mire, somos NIOVAL de Guadalajara, manejamos una linea muy "
        "completa de productos ferreteros a muy buenos precios. "
        "¿Le interesaria que le envie nuestra lista de precios?",
        "Que bien. Somos distribuidores NIOVAL con precios muy competitivos. "
        "¿Le gustaria conocer nuestro catalogo?",
    ],
    # FIX 875: Versión corta para cuando el pitch ya fue dado (evita INFO_NO_SOLICITADA)
    # Auditoría 25/02: "Excelente. Le comento, somos NIOVAL..." 9x cuando pitch_inicial ya sonó
    "pitch_encargado_corto": [
        "Excelente. ¿Le gustaria recibir nuestro catalogo de productos por WhatsApp o correo electronico?",
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

    # === FIX 894: Templates para IDENTITY_QUESTION y WHAT_OFFER ===
    # Evitan que GPT genere respuestas genéricas cuando cliente pregunta quién es Bruce
    # FIX 912: Pitch corto con beneficios (anti FLUJO_ROBOTICO)
    "pitch_completo_894": [
        "Le comento, somos NIOVAL, distribuidores de productos ferreteros con "
        "precios de fabrica y entrega directa. "
        "¿Le gustaria que le envie nuestra lista de precios?",
    ],
    "pitch_y_encargado_894": [
        "Le comento, somos distribuidores de productos ferreteros con mas de "
        "quince mil productos. Con gusto le puedo enviar nuestro catalogo. "
        "¿Se encontrara el encargado o encargada de compras?",
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
    # FIX 911: Variantes empáticas para rechazos de canal
    "pedir_alternativa_correo": [
        "Entiendo, no se preocupe. ¿Me podria dar un correo electronico entonces?",
        "Claro, sin problema. ¿Habra un correo electronico donde le pueda enviar la informacion?",
    ],
    "pedir_alternativa_telefono": [
        "Entiendo, no hay problema. ¿Me podria dar un telefono fijo o directo entonces?",
        "Claro. ¿Tendra un numero de telefono donde le pueda contactar?",
    ],
    "pedir_alternativa_whatsapp": [
        "Entiendo. ¿Tendra un WhatsApp donde le pueda enviar la informacion?",
        "Claro. ¿Habra un numero de WhatsApp para enviarle los detalles?",
    ],
    # FIX 841: Removida mención de "catálogo" para evitar CATALOGO_REPETIDO
    # FIX 911: Variantes empáticas con reflejo del cliente
    "pedir_contacto_alternativo": [
        "Entiendo que no se encuentra. ¿Me podria proporcionar un WhatsApp o correo "
        "del encargado?",
        "No se preocupe, entiendo que no esta disponible. ¿Habra algun WhatsApp o "
        "correo donde pueda enviarle la informacion?",
        "Claro, no hay problema. ¿Me podria facilitar algun medio de contacto "
        "del encargado para hacerle llegar nuestra informacion?",
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
    # FIX 914: Cierre con recapitulación de siguiente paso
    "confirmar_telefono": [
        "Perfecto, ya tengo el numero registrado. Le envio el catalogo con "
        "lista de precios en las proximas dos horas. Si tiene alguna duda, "
        "con gusto me puede contactar. Muchas gracias por su tiempo.",
        "Excelente, ya quedo anotado. En breve le envio toda la informacion "
        "de nuestros productos. Muchas gracias, que tenga excelente dia.",
    ],
    "confirmar_correo": [
        "Perfecto, ya tengo el correo registrado. Le envio el catalogo con "
        "lista de precios en las proximas dos horas. Si tiene alguna duda, "
        "con gusto me puede contactar. Muchas gracias por su tiempo.",
        "Excelente, ya quedo anotado el correo. En breve le envio toda la "
        "informacion. Muchas gracias, que tenga excelente dia.",
    ],
    "confirmar_dato_generico": [
        "Perfecto, ya lo tengo anotado. Le envio el catalogo en las proximas "
        "dos horas. Si tiene alguna pregunta, estamos para servirle. "
        "Muchas gracias por su tiempo.",
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
    # FIX 911/914: Variantes de despedida con empatía
    "despedida_cortes": [
        "Muchas gracias por su tiempo. Que tenga excelente dia. Hasta pronto.",
        "Le agradezco mucho su atencion. Que tenga muy buen dia.",
        "Muchas gracias, fue un gusto. Que le vaya muy bien.",
    ],
    "despedida_no_interesa": [
        "Entendido, no se preocupe. Le dejo nuestro numero por si mas adelante "
        "le interesa. Que tenga buen dia.",
        "Claro, lo entiendo perfectamente. Si en algun momento necesita productos "
        "ferreteros, con gusto le atendemos. Que tenga buen dia.",
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
    # FIX 914: Removido filler "Perfecto, muchas gracias" (RESPUESTA_FILLER_INCOHERENTE)
    "pedir_whatsapp_o_correo": [
        "Con gusto le envio la informacion. ¿Me podria proporcionar un numero de "
        "WhatsApp o correo electronico?",
        "Para hacerle llegar nuestro catalogo, ¿me podria dar un WhatsApp "
        "o correo electronico?",
    ],
    # FIX 884: BRUCE2516 - Template breve para FIX 878 pivot (2do intento de identidad)
    # FIX 885: Remover "catalogo" para evitar CATALOGO_REPETIDO (BRUCE2551/1975)
    # Palabras distintas a pedir_whatsapp_o_correo para evitar PREGUNTA_REPETIDA.
    "pedir_whatsapp_o_correo_breve": [
        "¿Me puede facilitar su WhatsApp o un correo electrónico?",
    ],
    # FIX 885B: BRUCE2551/1975 - 3er+ intento de identidad → pedir numero directo
    # Distinto a breve para evitar PREGUNTA_REPETIDA entre identity #2 y #3
    "pedir_numero_directo_885": [
        "¿Me puede dar un número de celular para enviarle la información?",
    ],
    # FIX 891: BRUCE1975 - FIX 791 UNKNOWN en encargado_ausente con identity_repetidas >= 2
    # Distinto a pedir_numero_directo_885 para evitar PREGUNTA_REPETIDA (4o template diferente)
    "pedir_telefono_directo_891": [
        "¿Podría facilitarme un teléfono fijo o celular para contactarle?",
    ],
    # FIX 892A: BRUCE1975 - 2da entrada a ENCARGADO_AUSENTE (post-transfer) usa template distinto
    # pedir_contacto_alternativo ya sonó en PITCH→ENCARGADO_AUSENTE; evitar PREGUNTA_REPETIDA
    "pedir_dato_contacto_892": [
        "Entiendo. ¿Podría darme algún dato de contacto del encargado, como WhatsApp o correo?",
    ],
    "pitch_catalogo_whatsapp": [
        "Con mucho gusto. Manejamos una amplia linea de productos ferreteros de la "
        "marca NIOVAL. ¿Le puedo enviar nuestro catalogo por WhatsApp?",
    ],
    "preguntar_horario_encargado": [
        "Entiendo, no se preocupe. ¿Hay algun horario en el que pueda encontrar "
        "al encargado de compras?",
    ],
    "despedida_agradecimiento": [
        "Claro que si. Le agradezco mucho su tiempo. Que tenga excelente dia.",
    ],

    # FIX 920: Templates empáticos para frustración detectada
    "despedida_ocupado_920": [
        "Entiendo perfectamente que esta ocupado. Le pido una disculpa por la "
        "interrupcion. Si gusta, le puedo marcar en otro momento. Que tenga buen dia.",
        "Disculpe la molestia, entiendo que no es buen momento. "
        "¿Le marco mas tarde o prefiere que le envie la informacion por otro medio?",
    ],
    "despedida_ya_llamaron_920": [
        "Le ofrezco una disculpa por las molestias. Tomo nota para no volver a "
        "interrumpirle. Que tenga excelente dia.",
        "Disculpe la insistencia, no era nuestra intencion molestar. "
        "Que tenga muy buen dia.",
    ],

    # FIX 918: Template para confusion del cliente (SENTIMIENTO_NEGATIVO)
    "aclarar_confusion": [
        "Disculpe, le explico brevemente. Somos NIOVAL, distribuidores de productos "
        "ferreteros. Le llamamos para ofrecerle nuestro catalogo con precios de fabrica.",
        "Perdon por la confusion. Mi nombre es Bruce, le llamo de NIOVAL para "
        "ofrecerle productos ferreteros a precios competitivos.",
    ],

    # FIX 920: Templates para explorar antes de despedida (OPORTUNIDAD_PERDIDA)
    "explorar_antes_despedida": [
        "Entiendo. ¿Habra algun horario mejor para llamarle?",
        "Claro, no hay problema. ¿Le podria dejar mi numero por si mas adelante le interesa?",
    ],

    # FIX 921: Template para rechazo ambiguo (MANEJO_OBJECIONES)
    "aclarar_rechazo_ambiguo": [
        "Disculpe, ¿se refiere a que no esta el encargado o prefiere que no le llamemos?",
        "Entiendo. ¿No se encuentra el encargado o no le interesa la informacion?",
    ],

    # FIX 922: Template pre-despedida para captura minima (CAPTURA_DATOS)
    "captura_minima_pre_despedida": [
        "Entendido. Antes de colgar, ¿me podria dar su nombre para la proxima ocasion?",
        "Claro. ¿A que hora seria mejor momento para llamar?",
    ],

    # FIX 921: Template de catálogo sin compromiso mejorado
    "ofrecer_catalogo_sin_compromiso": [
        "Claro, le comento. Somos distribuidores de NIOVAL. "
        "¿Le interesa recibir nuestro catalogo sin compromiso?",
        "Mire, sin compromiso le puedo enviar nuestra lista de precios "
        "para que la revise con calma. ¿Le interesaria?",
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

    # FIX 913: Mejor manejo de objeciones con técnicas de reencuadre
    # FIX 911: Instrucciones de empatía específicas
    # FIX 915: Instrucciones de escucha activa
    "manejar_objecion": {
        "system": (
            "Eres Bruce, vendedor de NIOVAL (productos ferreteros). "
            "El cliente expreso una objecion o duda.\n"
            "REGLAS DE EMPATIA (FIX 911):\n"
            "1. PRIMERO reconoce lo que el cliente dijo usando SUS palabras\n"
            "2. Muestra comprension genuina ('entiendo su situacion', 'tiene razon')\n"
            "3. Si esta ocupado: ofrece llamar en otro momento\n"
            "4. Si no le interesa: respeta sin insistir, ofrece dejar numero\n"
            "5. Si tiene dudas: ofrece catalogo sin compromiso\n"
            "REGLAS DE ESCUCHA ACTIVA (FIX 915):\n"
            "- Menciona algo ESPECIFICO que el cliente dijo (no respuestas genericas)\n"
            "- Si el cliente pregunto algo, responde ESO primero\n"
            "Maximo 2 oraciones. Mexicano coloquial. NO insistas si rechazo firme."
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

    # FIX 908/911/912/914/915/916: Mejorado con todas las reglas de auditoria
    "conversacion_libre": {
        "system": (
            "Eres Bruce, vendedor de NIOVAL (productos ferreteros). "
            "La conversacion esta en una situacion no estandar.\n"
            "REGLAS ABSOLUTAS:\n"
            "1. Si cliente ya dijo un dato (nombre, telefono, correo, WhatsApp) "
            "en CUALQUIER turno anterior, NUNCA pedir ese dato de nuevo\n"
            "2. Si cliente rechazo un canal ('no tengo WhatsApp', 'no tengo correo'), "
            "NO pedir ese canal. Ofrecer alternativa distinta\n"
            "3. Si encargado no esta, pedir contacto alternativo\n"
            "4. Maximo 2 oraciones, mexicano coloquial\n"
            "5. NO repetir frases que Bruce ya dijo en turnos anteriores\n"
            "6. ESCUCHA ACTIVA: menciona algo ESPECIFICO que el cliente dijo\n"
            "7. EMPATIA: si el cliente suena frustrado, ocupado o confundido, "
            "reconocelo PRIMERO antes de continuar\n"
            "8. NO uses fillers vacios como 'Perfecto, muchas gracias' o 'Claro, digame' "
            "cuando no hay nada que agradecer. Responde al contenido del cliente\n"
            "9. Si el cliente ofrece hacer algo (pasar numero, dejar recado, enviar correo), "
            "ACEPTA y agradece, no ignores su oferta\n"
            "10. Si el cliente pregunto algo, responde ESO primero, no cambies de tema\n"
            "11. NO pidas datos si aun no explicaste que es NIOVAL ni que ofreces\n"
            "12. Si el cliente parece confundido, explica brevemente quien eres y por que llamas\n"
            "13. Si el cliente dijo 'no' de forma ambigua, pregunta a que se refiere\n"
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
