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
    # FIX 1110: Variante para 2da pregunta de identidad (anti-PREGUNTA_REPETIDA)
    # OOS-12-13: "¿Cómo se llama?" → identificacion_nioval, "¿De qué empresa?" → MISMA respuesta
    "identificacion_nioval_variante": [
        "Somos NIOVAL, empresa de Guadalajara dedicada a la distribucion de "
        "productos ferreteros. Manejamos mas de quince categorias con entrega directa.",
    ],
    "identificacion_pitch": [
        "Mi nombre es Bruce, le llamo de NIOVAL. Somos distribuidores de productos "
        "ferreteros. Manejamos mas de quince categorias. "
        "¿Se encontrara el encargado de compras?",
    ],
    # FIX 1068: Identificacion breve post-despedida (sin reiniciar pitch completo)
    # Cuando en DESPEDIDA el cliente pregunta empresa/numero, solo identificarse y despedirse
    "identificacion_breve_1068": [
        "Le llamo de NIOVAL, distribuidores de ferreteria. Que tenga excelente dia.",
    ],
    # FIX 1082: Despedida breve cuando intermediario da info post-relay en estado DESPEDIDA
    # "Se llama el señor Juan" / "Es la señora Lupita" → acknowled without re-opening sale
    "despedida_reconfirmacion_1082": [
        "Muchas gracias por la informacion. Que tenga excelente dia.",
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
    # FIX 938-F+1113: Aceptar oferta de recado + preguntar hora callback (NO re-pedir WhatsApp)
    # FIX 1113: Re-pedir WhatsApp causaba PREGUNTA_REPETIDA (OOS-12-03)
    "aceptar_recado_pedir_wa": [
        "Muchas gracias, le agradezco mucho. ¿A que hora me recomienda volver a llamar?",
        "Con mucho gusto, se lo agradezco. ¿Cuando estaria disponible el encargado?",
    ],
    "digame_numero": [
        "Claro, digame por favor.",
        "Si, digame el numero.",
        "Adelante, le escucho.",
    ],

    # === DICTADO / ACKNOWLEDGMENT ===
    # FIX 769: Variantes formales con rotación (evitar repetición)
    # FIX 803: "continue" → "prosiga" (TTS pronunciaba como portugués)
    # FIX 906E: Variantes mas naturales (audit Claude: "suena robotico")
    "aja_si": [
        "Si, adelante.",
        "Claro, prosiga.",
        "Si, lo escucho.",
        "Entendido, prosiga.",
        "Perfecto, adelante.",
        "Aja, digame.",
        "Si, le escucho.",
    ],
    "aja_digame": [
        "Claro, digame.",
        "Si, adelante, digame.",
        "Perfecto, digame.",
        "Entendido, digame.",
        "Aja, digame por favor.",
    ],

    # === CONFIRMACIÓN DE DATO CAPTURADO ===
    # FIX 914: Cierre con recapitulación de siguiente paso
    # FIX 906E: Incluir confirmacion del dato recibido + que se envia + cuando + contacto retorno
    "confirmar_telefono": [
        "Perfecto, ya tengo su numero. Le envio el catalogo con "
        "lista de precios en las proximas horas. Si tiene alguna duda, "
        "me puede escribir a ese mismo numero. Muchas gracias por su tiempo, que tenga excelente dia.",
        "Excelente, quedo registrado. En breve le envio toda la informacion "
        "de nuestros productos con precios. Muchas gracias, que tenga excelente dia.",
        "Muy bien, ya lo tengo anotado. Le envio el catalogo en un momento. "
        "Si necesita algo mas, con gusto le atendemos. Que tenga buen dia.",
    ],
    # FIX 1126: Phone-only confirmation (WA+correo rechazados) — sin "escribir"
    # OOS-03 (10 convs): "me puede escribir" es incoherente para teléfono fijo
    "confirmar_telefono_fijo_1126": [
        # FIX 1159: Cierre cálido completo (OOS-03: 10 REGULAR por despedida truncada)
        "Perfecto, ya tengo su numero. Le envio el catalogo con lista de precios "
        "en las proximas horas. Si tiene alguna duda, nos puede llamar. "
        "Muchas gracias por su tiempo, que tenga excelente dia.",
        "Excelente, quedo registrado. En breve le envio toda la informacion "
        "de nuestros productos con precios. Muchas gracias, que tenga excelente dia.",
    ],
    "confirmar_correo": [
        "Perfecto, ya tengo el correo. Le envio el catalogo con "
        "lista de precios en las proximas horas. Si tiene alguna duda, "
        "me puede escribir. Muchas gracias por su tiempo, que tenga excelente dia.",
        "Excelente, quedo registrado el correo. En breve le envio toda la "
        "informacion con precios. Muchas gracias, que tenga excelente dia.",
    ],
    "confirmar_dato_generico": [
        "Perfecto, ya lo tengo anotado. Le envio el catalogo con lista "
        "de precios en las proximas horas. Si tiene alguna pregunta, "
        "estamos para servirle. Muchas gracias por su tiempo.",
    ],

    # === OFRECER CONTACTO DE BRUCE ===
    # FIX 1094: Más empático y natural (antes muy directo/mecánico)
    # FIX 1122: Mala experiencia previa → respuesta empática (GPT no era empático)
    # OOS-15-14: "ya compré de NIOVAL y no fue bien" → GPT decía "catálogo"
    "empatia_mala_experiencia_1122": [
        "Lamento mucho escuchar eso. Le ofrezco una disculpa de parte de NIOVAL. "
        "Nos gustaria tener la oportunidad de mejorar su experiencia. "
        "¿Me permite enviarle nuestro catalogo actualizado para que vea las novedades?",
    ],

    # FIX 1121: Certificaciones → respuesta honesta (no GPT que hallucina)
    # OOS-16-16: "Solo trabajamos con proveedores certificados" → GPT decía "tenemos documentos en orden"
    "respuesta_certificaciones_1121": [
        "Somos empresa formal con RFC y facturacion electronica. Sobre certificaciones adicionales, "
        "no cuento con esa informacion en este momento, pero con gusto le conecto con mi equipo "
        "para resolverle esa duda. ¿Le gustaria que le enviemos la informacion?",
    ],

    # FIX 1127: Phase 1 intercepts para preguntas frecuentes (GPT evasivo)
    # OOS-14-14: devoluciones → GPT redirects a catálogo
    "respuesta_devoluciones_1127": [
        "Si, aceptamos devoluciones por producto en mal estado. Le detallo las condiciones "
        "junto con el catalogo. ¿Se lo envio?",
    ],
    # OOS-14-20: RFC/facturación → GPT redirects a catálogo
    "respuesta_rfc_1127": [
        "Si, somos empresa formal con RFC y emitimos facturas electronicas. "
        "Con gusto le enviamos la informacion. ¿Tiene WhatsApp o correo?",
    ],
    # OOS-14-18: catálogo físico/digital → GPT circular
    "respuesta_catalogo_digital_1127": [
        "Manejamos catalogo digital que le enviamos directamente. Es mas practico "
        "y siempre esta actualizado. ¿Se lo mando por WhatsApp o correo?",
    ],
    # OOS-14-09/15-05: "ya les compré antes" → reconocer cliente existente
    "reconocer_cliente_existente_1127": [
        "Que bien, gracias por su confianza. Tenemos novedades en el catalogo desde entonces. "
        "¿Le gustaria que le envie la informacion actualizada?",
    ],
    # OOS-14-19: "qué productos manejan" → enumerar líneas
    "respuesta_lineas_producto_1127": [
        "Somos distribuidores ferreteros: manejamos herramienta, tornilleria, plomeria, "
        "griferia, silicones, candados, adhesivos, cerraduras, electricidad y mas de 500 articulos. "
        "¿Le envio el catalogo con precios?",
    ],

    # FIX 1129: Correo exchange — cliente ofrece dar correo del encargado
    # OOS-12-16: "Dígame su correo para darle el del encargado"
    "capturar_correo_encargado_1129": [
        "No manejo correo de contacto, pero con gusto me puede dictar el correo del encargado "
        "y le mandamos la informacion directamente.",
    ],

    # FIX 1131: "yo no decido" → preguntar si el decisor está
    # OOS-16-13: "Yo no decido eso, el dueño es el que compra"
    "preguntar_decisor_1131": [
        "Entiendo. ¿Se encontrara el encargado de compras para platicarle brevemente?",
    ],

    # FIX 1137: Encargado ocupado (presente pero busy) → no decir "no se encuentra"
    # OOS-05-05/06: "Está atendiendo un cliente" / "Está en el almacén"
    "encargado_ocupado_1137": [
        "Entiendo que esta ocupado. ¿Me podria proporcionar un WhatsApp o correo del encargado?",
    ],

    # FIX 1138: Callback cuando el PROPIO encargado está ocupado
    # OOS-11-03: "Soy el dueño pero estoy muy ocupado" → "para encontrar al encargado" es incorrecto
    "callback_encargado_ocupado_1138": [
        "Entiendo, no se preocupe. ¿A que hora le puedo volver a marcar?",
        "Sin problema. ¿Cuando le quedaria bien que le marque?",
    ],

    # FIX 1139: "¿Es gratis el catálogo?" → respuesta directa
    # OOS-15-07: GPT responde "Esa info viene en el catálogo" (circular)
    "catalogo_gratis_1139": [
        "Si, el catalogo es totalmente gratis y sin compromiso. ¿Se lo envio por WhatsApp o correo?",
    ],

    # FIX 1140: "No me gustan las llamadas de ventas" → empatía + oferta rápida
    # OOS-15-11: Bruce ignora y pide WA directamente
    "empatia_no_gustan_llamadas_1140": [
        "Lo entiendo perfectamente, sere muy breve. Solo le queria ofrecer nuestro catalogo "
        "de productos ferreteros sin compromiso. ¿Le puedo enviar la informacion por WhatsApp o correo?",
    ],

    # FIX 1142: Tiempo de entrega → respuesta directa
    # OOS-14-17: GPT dice "esa info en el catálogo" (evasivo)
    # FIX 1158: Redirect más directo a WA/correo (OOS-09-09: cliente salva la situación)
    "respuesta_tiempo_entrega_1142": [
        "Generalmente de 2 a 5 dias habiles dependiendo de su ubicacion. "
        "¿Le envio el catalogo con precios por WhatsApp o correo?",
    ],

    # FIX 1142B: Precio de producto → respuesta directa
    # OOS-14-11: GPT con error gramatical "le la envío"
    "respuesta_precio_producto_1142": [
        "Manejamos precios de mayoreo muy competitivos. Con gusto le envio la lista "
        "de precios para que pueda revisar. ¿Se la mando por WhatsApp o correo?",
    ],

    # FIX 1144: "Quizás en unos meses" → deferred callback con seguimiento
    # OOS-16-18: Bruce se despide sin confirmar callback futuro
    "despedida_callback_diferido_1144": [
        "Entendido, no hay problema. Nos ponemos en contacto mas adelante entonces. "
        "Le dejo nuestro numero por si antes necesita algo. Que tenga buen dia.",
    ],

    # FIX 1133: "este mismo número" → confirmar
    # OOS-13-13: "este mismo número que marcó usted"
    "confirmar_mismo_numero_1133": [
        "Perfecto, le envio la informacion a este mismo numero entonces. Muchas gracias por su tiempo, que tenga buen dia.",
    ],

    # FIX 1148: "De dónde son" → respuesta de ubicación sin re-introducción
    # OOS-09-05: Bruce re-dice "Mi nombre es Bruce" (redundante)
    "respuesta_ubicacion_1148": [
        "Somos de Guadalajara, Jalisco. Distribuidores de productos ferreteros con entrega a toda la republica.",
    ],

    # FIX 1149: "¿Es grabación/robot?" → respuesta explícita
    # OOS-15-12/15-17: Bruce evade con identidad corporativa
    "respuesta_agente_real_1149": [
        "Soy Bruce, agente de ventas de NIOVAL. Con gusto le atiendo. "
        "¿Le gustaria recibir nuestro catalogo de productos?",
    ],

    # FIX 1150: "¿Cómo consiguió este número?" → explicar prospección
    # OOS-16-14: Bruce da identidad pero no responde la pregunta
    "respuesta_origen_numero_1150": [
        "Estamos contactando negocios del giro ferretero para ofrecer nuestros productos. "
        "¿Le gustaria recibir nuestro catalogo con lista de precios?",
    ],

    # FIX 1156: "no sé si soy el encargado" → preguntar si decide compras
    # OOS-15-06: Bruce dice "Excelente" ante incertidumbre de rol
    "preguntar_si_decide_1156": [
        "No se preocupe. ¿Usted es quien decide las compras de productos o quien los recibe?",
    ],

    # FIX 1160: Primer recado → agradecer + intentar captura una vez más
    # OOS-05 (6 REGULAR): Bruce aceptaba sin segundo intento
    "recado_repedir_dato_1160": [
        "Se lo agradezco mucho. ¿De casualidad tendra un WhatsApp o correo del encargado "
        "para enviarle la informacion directamente?",
    ],

    # FIX 1134: "ya les compré" como encargado_presente → reconocer + ofrecer
    # FIX 1132: FIX 1111 name post-recado → acknowledge name in despedida
    "despedida_con_nombre_1132": [
        "Perfecto, muchas gracias. Quedamos al pendiente con el encargado. Que tenga buen dia.",
    ],

    # FIX 1116: Cliente pide correo de NIOVAL → no manejamos correo, ofrecer teléfono
    # OOS-12-16: "Dígame su correo para darle el del encargado" → Bruce no tiene email público
    "ofrecer_telefono_sin_correo_1116": [
        "Por el momento no manejamos correo de contacto, pero con gusto le dejo nuestro numero telefonico para que nos llame cuando guste. ¿Tiene donde anotar?",
        "No tenemos correo de contacto disponible, pero le puedo dejar nuestro numero directo. ¿Le anoto?",
    ],
    "ofrecer_contacto_bruce": [
        "Con gusto le dejo el numero de NIOVAL para que nos contacte cuando le convenga. ¿Le anoto?",
        "¿Le puedo dejar mi numero directo para que el encargado nos llame cuando guste?",
        "Con mucho gusto le dejo los datos de contacto de NIOVAL. ¿Tiene donde anotar?",
    ],
    "tiene_donde_anotar": [
        "Perfecto. ¿Tiene donde anotar?",
    ],
    "dictar_numero_bruce": [
        "Nuestro numero es 662 353 1804. Le repito, 662 353 1804. "
        "Somos NIOVAL, distribuidores de productos ferreteros.",
    ],

    # FIX 1095+1107: Recado verbal → reconocer + preguntar hora callback (NO re-pedir WhatsApp)
    # FIX 1107: Re-pedir WhatsApp causaba PREGUNTA_REPETIDA en 22/230 convs (OOS-05, OOS-12)
    "recado_y_pedir_contacto_1095": [
        "Con mucho gusto le dejamos el recado. ¿A que hora me recomienda volver a llamar?",
        "Claro, le dejamos el mensaje. ¿Cuando estaria disponible el encargado para llamarle?",
        "Perfecto, le dejamos el recado. ¿A que hora puedo volver a marcar?",
    ],

    # FIX 1125: Recado simple → aceptar y despedir (no preguntar callback)
    # OOS-05-07/08/09/10: "dígale que llamaron de Nioval" → goodbye, no callback
    "recado_aceptado_despedida_1125": [
        "Con mucho gusto le dejamos el recado. Muchas gracias por su tiempo, que tenga buen dia.",
        "Perfecto, le dejamos el mensaje. Muchas gracias, que tenga excelente dia.",
        "Claro, le dejamos el recado. Muchas gracias por su atencion, hasta pronto.",
    ],

    # === TRANSFER / ESPERA ===
    "claro_espero": [
        "Claro, espero.",
    ],

    # === CALLBACK ===
    "preguntar_hora_callback": [
        "¿A que hora me recomienda llamar para encontrar al encargado?",
    ],
    # FIX 938-E: OOS audit V2 - Template para callback cuando encargado ya esta presente
    "preguntar_hora_callback_directo": [
        "¿A que hora seria buen momento para marcarle?",
        "¿Cuando le puedo marcar para hablar con mas calma?",
        "Claro, con gusto. ¿A que hora le queda mejor?",
    ],
    "confirmar_callback": [
        "Perfecto, le marco {hora}. Muchas gracias por su tiempo, que tenga "
        "excelente dia.",
    ],
    "confirmar_callback_generico": [
        "Perfecto, le vuelvo a llamar mas tarde. Muchas gracias por su tiempo, "
        "que tenga excelente dia.",
    ],
    # FIX 1162: Sin presupuesto → callback el próximo mes
    "callback_sin_presupuesto_1162": [
        "Entiendo perfectamente, no se preocupe. Le parece si le marco el proximo mes "
        "para ver si ya cuentan con presupuesto? Asi le envio el catalogo con lista de precios. "
        "Que tenga excelente dia.",
        "Claro, lo entiendo. Si gusta le llamo el proximo mes cuando cuenten con presupuesto, "
        "y con gusto le comparto nuestro catalogo. Muchas gracias por su tiempo, buen dia.",
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

    # FIX 950: Template para rechazo hostil / solicitud LFPDPPP de eliminar datos
    # NO ofrecer retomar contacto. NO mencionar WhatsApp/correo. Cierre definitivo.
    "despedida_hostil_950": [
        "Disculpe la molestia, no era mi intencion incomodar. Que tenga buen dia.",
        "Le ofrezco una disculpa. No le volveremos a marcar. Que tenga excelente dia.",
    ],

    # FIX 1124: Confirmación de preferencia de número ("use el personal")
    # Cliente dio 2 números y aclara cuál usar — confirmar y despedir
    "confirmar_preferencia_numero_1124": [
        "Perfecto, le envio el catalogo al {numero}. Muchas gracias por su tiempo. Que tenga excelente dia.",
        "Entendido, usamos el {numero}. Le mandamos el catalogo por ahi. Que tenga buen dia.",
        "Listo, le enviamos todo al {numero}. Muchas gracias. Hasta pronto.",
    ],

    # FIX 952: Confirmación de corrección de número/dato post-captura
    # Usar {numero} como placeholder — se reemplaza en fsm_engine.py
    "confirmar_correccion_952": [
        "Perfecto, ya actualice el numero al {numero}. Le enviamos el catalogo a ese numero. Muchas gracias.",
        "Listo, quedo registrado el {numero}. Le mandamos el catalogo por ahi. Que tenga buen dia.",
        "Anotado, el numero correcto es el {numero}. Le enviamos el catalogo a ese. Gracias por avisar.",
    ],

    # FIX 906: Template empatico para situaciones sensibles (fallecimiento, cierre)
    "despedida_sensible_906": [
        "Lamento mucho escuchar eso. Le ofrezco mis condolencias. "
        "Disculpe la molestia, que tenga buen dia.",
        "Lo siento mucho, de verdad. Disculpe la llamada, no era mi intencion "
        "molestar en este momento. Que tenga buen dia.",
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
    # FIX 938-D: OOS audit V2 - Templates menos invasivos (no pedir nombre después de pitch)
    "captura_minima_pre_despedida": [
        "¿A que hora seria buen momento para llamarle otro dia?",
        "Claro, no hay problema. Le dejo nuestro numero por si mas adelante le interesa.",
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
            "Eres Bruce, ejecutivo de ventas de NIOVAL (distribuidora ferretera, Guadalajara). "
            "El cliente hizo una pregunta. OBLIGATORIO: responde la pregunta PRIMERO con info "
            "concreta. Luego SOLO di 'Le envio el catalogo con precios' (SIN mencionar WhatsApp "
            "ni correo — eso ya se maneja por separado). "
            "NUNCA respondas solo pidiendo datos de contacto sin responder la pregunta. "
            "Catalogo: cintas tapagoteras, griferia, herramientas, candados, silicones, "
            "adhesivos, cerraduras, tornilleria, plomeria, electricidad y mas de 500 productos. "
            "RESPUESTAS CANONICAS:\n"
            "- Precio/costo/cuanto cuesta: 'Manejamos precios de mayoreo muy competitivos. "
            "Con gusto le envio la lista de precios.'\n"
            "- Tornilleria/producto especifico: 'Si, manejamos tornilleria completa y mas. "
            "Le envio el catalogo para que vea todos los productos.'\n"
            "- Que venden/que manejan: 'Somos distribuidores ferreteros: herramienta, "
            "tornilleria, plomeria, griferia, silicones, candados y mas de 500 articulos.'\n"
            "- Descuentos: 'Si, manejamos descuentos por volumen, se los detallo en la lista.'\n"
            "- Credito: 'Manejamos credito con clientes frecuentes.'\n"
            "- Ubicacion/envios: 'Estamos en Guadalajara, hacemos envios a toda la Republica.'\n"
            "- Tiempo entrega: '2 a 5 dias habiles segun su ubicacion.'\n"
            "- Son distribuidores/que tipo de empresa: 'Si, somos distribuidores de productos "
            "ferreteros. Manejamos mas de 15 categorias con entrega directa.'\n"
            "- Competidor/mejores que otro: 'Nuestros precios de mayoreo y envio directo son "
            "muy competitivos. Le envio el catalogo para que compare.'\n"
            "- Supervisor: 'Soy el ejecutivo de ventas de NIOVAL, con gusto le ayudo. "
            "Le envio el catalogo.'\n"
            "- Devoluciones: 'Si, aceptamos devoluciones por producto en mal estado. "
            "Le detallo las condiciones en el catalogo.'\n"
            "- Facturacion/RFC: 'Si, somos empresa formal con RFC, emitimos facturas electronicas. "
            "Con gusto le enviamos la informacion fiscal.'\n"
            "- Certificaciones/proveedores certificados: 'Somos empresa formal con RFC y facturacion "
            "electronica. No cuento con informacion sobre certificaciones adicionales en este momento, "
            "pero con gusto le conecto con mi equipo para resolverle esa duda.'\n"
            "- Catalogo fisico/digital: 'Manejamos catalogo digital que le enviamos directamente. "
            "Es mas practico y siempre actualizado.'\n"
            "- Grabacion/robot/IA: 'No, soy Bruce, ejecutivo de ventas real de NIOVAL. "
            "Hablo directamente con usted.'\n"
            "- Empresa equivocada (Herrajes del Norte, etc.): 'No, somos NIOVAL, "
            "distribuidores ferreteros de Guadalajara. Quiza nos confunde con otra empresa.'\n"
            "FORMATO: 1-2 oraciones maximas. SIEMPRE 'usted'/'le'. Mexicano profesional. "
            "NUNCA menciones WhatsApp, correo, email, numero de telefono ni pidas datos de contacto. "  # FIX 1093
            "NUNCA preguntes 'me puede dar su numero' ni similares. Solo responde la pregunta."
        ),
        "max_tokens": 100,
        "temperature": 0.4,
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
            "REGLAS:\n"
            "1. Confirma el dato recibido (menciona el numero/correo que te dieron)\n"
            "2. Di QUE le vas a enviar ('el catalogo con lista de precios')\n"
            "3. Di CUANDO ('en las proximas horas')\n"
            "4. Ofrece contacto de retorno ('si tiene dudas, me puede escribir')\n"
            "5. SIEMPRE usa 'usted' (le envio, su numero), NUNCA 'tu'\n"
            "2-3 oraciones, mexicano coloquial pero profesional."
        ),
        "max_tokens": 80,
        "temperature": 0.3,
    },

    # FIX 908/911/912/914/915/916/906F: Mejorado con todas las reglas de auditoria
    "conversacion_libre": {
        "system": (
            "Eres Bruce, vendedor de NIOVAL (productos ferreteros de Guadalajara). "
            "La conversacion esta en una situacion no estandar.\n"
            "REGLAS ABSOLUTAS:\n"
            "1. Si cliente ya dijo un dato (nombre, telefono, correo, WhatsApp) "
            "en CUALQUIER turno anterior, NUNCA pedir ese dato de nuevo\n"
            "2. Si cliente rechazo un canal ('no tengo WhatsApp', 'no tengo correo'), "
            "NO pedir ese canal. Ofrecer alternativa distinta\n"
            "3. Si encargado no esta, pedir contacto alternativo\n"
            "4. Maximo 2 oraciones, mexicano coloquial pero profesional\n"
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
            "14. SIEMPRE usa 'usted' (le envio, su numero). NUNCA tutees al cliente\n"
            "15. Al confirmar un dato, REPITE el numero/correo que te dieron\n"
            "16. Al despedirte, di QUE envias, CUANDO, y ofrece contacto de retorno\n"
            "17. 'Claro, digame' es SOLO para cuando el cliente va a dictar un numero "
            "o correo. NUNCA uses 'Claro, digame' como respuesta a una pregunta ni a "
            "una afirmacion\n"
            "18. Si el cliente dice 'marca al rato', 'llama despues' o similar, "
            "responde 'Perfecto, le marco mas tarde' o similar — NO digas 'Claro, digame'\n"
            "19. Si el cliente ofrece dejar un recado, acepta con gratitud y pide "
            "el WhatsApp o correo del encargado con palabras DISTINTAS a las ya usadas\n"
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

    # FIX 1049: Acknowledge client's post-capture instruction (e.g. "use el personal")
    # Called when CONTACTO_CAPTURADO + CONFIRMATION — client may be specifying which number to use
    "reconocer_y_despedir": {
        "system": (
            "Eres Bruce, ejecutivo de ventas de NIOVAL. "
            "El cliente acaba de dar una instruccion adicional sobre el contacto que proporcionó. "
            "Acusa recibo brevemente ('De acuerdo', 'Anotado', 'Perfecto') y despidete. "
            "OBLIGATORIO: 1 sola oración corta. Incluye 'que tenga buen dia' o 'hasta luego'. "
            "NUNCA pidas más datos. Mexicano profesional. Solo 'usted'/'le'."
        ),
        "max_tokens": 50,
        "temperature": 0.3,
    },
}
