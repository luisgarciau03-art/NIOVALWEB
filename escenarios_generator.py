"""
Generador de 1000 escenarios OOS para testing de Bruce W.
Genera escenarios diversos programaticamente con variaciones realistas.
Grupos de 15 escenarios cada uno (~67 grupos).
"""
import random
import json

random.seed(42)  # Reproducible

# ── Datos base para variaciones ──────────────────────────────────────────

GIROS = [
    "Ferreteria", "Tlapaleria", "Papeleria", "Abarroteria", "Carniceria",
    "Panaderia", "Tortilleria", "Farmacia", "Veterinaria", "Refaccionaria",
    "Muebleria", "Vidriera", "Pinturas", "Plomeria", "Electrica",
    "Zapateria", "Tienda de Ropa", "Merceria", "Cerrajeria", "Herreria",
    "Dulceria", "Jugueteria", "Floreria", "Cremeria", "Polleria",
    "Marisqueria", "Cocina Economica", "Restaurante", "Cafeteria", "Lavanderia",
    "Estetica", "Optica", "Dentista", "Consultorio", "Laboratorio",
    "Imprenta", "Copias", "Celulares", "Computadoras", "Electronica",
]

NOMBRES_NEGOCIO = [
    "El Martillo", "La Tuerca", "Don Pepe", "El Tornillo", "La Paloma",
    "San Juan", "El Sol", "La Estrella", "El Aguila", "La Corona",
    "El Diamante", "La Perla", "El Roble", "La Fuente", "El Pino",
    "Santa Maria", "San Jose", "El Faro", "La Cascada", "El Puente",
    "Don Carlos", "La Victoria", "El Progreso", "La Union", "El Triunfo",
    "La Esperanza", "El Porvenir", "La Fortuna", "El Dorado", "La Bonita",
    "Don Luis", "El Central", "La Nueva", "El Popular", "La Moderna",
    "San Miguel", "El Rayo", "La Loma", "El Cerro", "La Colina",
    "Don Roberto", "El Norte", "La Sur", "El Este", "La Oeste",
    "San Pedro", "El Grande", "La Chica", "El Viejo", "La Joven",
]

CIUDADES = [
    "Guadalajara", "CDMX", "Monterrey", "Puebla", "Queretaro",
    "Leon", "Toluca", "Merida", "Chihuahua", "Tijuana",
    "Cancun", "Aguascalientes", "Morelia", "Hermosillo", "Saltillo",
    "Culiacan", "Durango", "Tampico", "Veracruz", "Oaxaca",
]

SALUDOS_CLIENTE = [
    "Bueno", "Diga", "Si, digame", "Alo", "Bueno, quien habla",
    "Si", "Mande", "Que paso", "A ver", "Bueno bueno",
    "Hola", "Si, bueno", "Digame", "Que se le ofrece", "Si diga",
    "Buenas tardes", "Buenos dias", "Buenas", "Que tal", "Que onda",
    "Si quien habla", "A sus ordenes", "En que le puedo ayudar",
    "Tienda {giro}, buenas tardes", "Si bueno, {giro} {nombre}",
]

CONFIRMACIONES_ENCARGADO = [
    "Si, yo soy el encargado", "Si yo mero", "Si, soy el dueno",
    "Si, yo soy", "Servidor", "Un servidor", "Si, con el habla",
    "Yo soy el encargado de compras", "Si, yo me encargo de eso",
    "Soy el responsable", "Yo veo eso de las compras",
    "Si, digame", "Si yo soy, que necesita", "Aqui el mero mero",
    "Si, el dueno soy yo", "Yo soy el que compra", "Si claro, yo soy",
    "Pues si, yo soy", "Aja, yo soy el encargado", "Si, yo manejo eso",
]

ACEPTA_WHATSAPP = [
    "Si, por WhatsApp esta bien", "Mandelo por WhatsApp",
    "Si al WhatsApp", "Por favor al WhatsApp", "Si, por wats",
    "Al WhatsApp por favor", "Si claro, por WhatsApp",
    "Si mandamelo al wats", "Orale, por WhatsApp", "Dale, al WhatsApp",
    "Si esta bien, mandalo al wats", "Al WhatsApp esta perfecto",
    "Si, mandelo al WhatsApp por favor", "Claro, por WhatsApp",
    "Si si, al wats porfa",
]

ACEPTA_CORREO = [
    "Al correo esta bien", "Si, por correo", "Mandelo al email",
    "Por correo electronico", "Si, al correo por favor",
    "Al email", "Mejor al correo", "Si mandelo al mail",
    "Prefiero por correo", "Al correo electronico por favor",
]

RECHAZA_WHATSAPP = [
    "No tengo WhatsApp", "No uso WhatsApp", "No manejo eso del WhatsApp",
    "Ese telefono no tiene WhatsApp", "Aqui no tenemos WhatsApp",
    "No no, WhatsApp no", "No le se al WhatsApp",
    "Pues no tengo wats", "No se usar el WhatsApp",
    "No usamos WhatsApp aqui", "No tenemos wats",
    "El telefono de la tienda no tiene WhatsApp",
]

RECHAZA_CORREO = [
    "Tampoco tengo correo", "No tengo email", "No uso correo",
    "Correo tampoco", "No no, correo no", "No manejo correo",
    "No tenemos correo electronico", "Eso del correo no",
]

RECHAZA_TODO = [
    "No me interesa gracias", "No gracias", "Estamos bien asi",
    "Ya tenemos proveedor", "No necesitamos nada", "No gracias, no me interesa",
    "Ahorita no", "No, no nos interesa", "Gracias pero no",
    "Estamos surtidos", "Ya tenemos quien nos surta", "No ocupamos nada",
    "La verdad ahorita no", "No estamos interesados", "Mejor no",
]

ENCARGADO_AUSENTE = [
    "No esta, salio a comer", "No se encuentra", "Salio",
    "No esta el encargado", "Anda fuera", "No vino hoy",
    "Esta en una junta", "Salio a hacer un mandado", "No ha llegado",
    "Viene hasta la tarde", "Hoy no vino", "Esta de vacaciones",
    "Fue al banco", "Salio a desayunar", "Anda en la calle",
    "No esta disponible", "Esta ocupado con un cliente", "No lo encuentro",
]

DESPEDIDAS_CLIENTE = [
    "Muchas gracias", "Gracias, bye", "Ok gracias", "Sale, gracias",
    "Perfecto gracias", "Muy bien gracias", "Orale gracias",
    "Esta bien, gracias", "Ok bye", "Gracias que tenga buen dia",
    "Listo gracias", "Si, gracias por la info",
]

EMAILS = [
    "ferreteria{n}@gmail.com", "tienda{n}@hotmail.com", "compras{n}@yahoo.com",
    "negocio{n}@outlook.com", "ventas{n}@gmail.com", "contacto{n}@live.com",
    "admin{n}@prodigy.net.mx", "info{n}@gmail.com", "pedidos{n}@hotmail.com",
    "gerencia{n}@yahoo.com.mx", "elnegocio{n}@gmail.com", "la.tienda{n}@hotmail.com",
]

NUMEROS_TELEFONO_FORMATS = [
    "33 {a} {b}", "33{a}{b}", "Es el 33 {a} {b}",
    "Mi numero es 33 {a} {b}", "El {a} {b} de Guadalajara",
    "55 {a} {b}", "81 {a} {b}", "22 {a} {b}",
    "{a} {b} {c} {d}", "Es el treinta y tres {a} {b}",
]

# ── Preguntas del cliente por categoria ──────────────────────────────────

PREGUNTAS_PRODUCTO = [
    "Y que tipo de productos manejan?", "Que es lo que venden exactamente?",
    "Que marcas tienen?", "Manejan herramienta electrica?",
    "Tienen tornilleria?", "Que lineas manejan?", "Son mayoristas?",
    "A que precio manejan?", "Tienen catalogo en linea?",
    "Manejan productos de plomeria?", "Que tan buenos son sus productos?",
    "Son productos nacionales o importados?", "Tienen garantia?",
    "Cual es su producto estrella?", "Manejan material electrico?",
]

PREGUNTAS_EMPRESA = [
    "De donde son ustedes?", "Donde estan ubicados?",
    "Desde cuando estan en el mercado?", "Cuantos anos tienen?",
    "Son de aqui de la ciudad?", "Tienen sucursal aqui?",
    "Son distribuidores directos?", "Son fabricantes o distribuidores?",
    "Tienen bodega aqui?", "Como los puedo visitar?",
]

PREGUNTAS_ENVIO = [
    "Hacen envios?", "Cual es el minimo de pedido?",
    "Cuanto tarda en llegar?", "Cobran envio?", "Entregan a domicilio?",
    "Mandan por paqueteria?", "Tienen envio gratis?",
    "Desde donde mandan?", "Llega en cuanto tiempo?",
    "Puedo pasar a recoger?",
]

PREGUNTAS_PRECIO = [
    "A que precios manejan?", "Tienen precios de mayoreo?",
    "Dan descuento por volumen?", "Cuanto cuesta el catalogo?",
    "Son precios con IVA?", "Facturan?", "Dan credito?",
    "A 30 dias facturan?", "Cual es su precio mas bajo?",
    "Manejan precio especial para distribuidores?",
]

CLIENTE_YA_TIENE_PROVEEDOR = [
    "Ya tenemos proveedor para eso", "Ya nos surte alguien",
    "Pues ya tenemos quien nos venda eso", "Ya trabajamos con otra marca",
    "Ya tenemos a nuestro distribuidor", "Estamos contentos con nuestro proveedor",
    "Ya tenemos compromiso con otro", "Pues si pero ya tenemos quien nos surta",
    "Ya estamos trabajando con Truper", "Ya nos mandan de otra fabrica",
]

CLIENTE_PIDE_DESCUENTO = [
    "Que descuento me dan?", "Si compro bastante que precio me hacen?",
    "Me pueden dar mejor precio?", "Tienen alguna promocion?",
    "Si soy cliente frecuente hay descuento?", "A cuanto me lo dejan?",
    "Cuanto es lo menos?", "Me pueden hacer un descuento?",
    "Si compro por mayoreo que precio?", "Hay precio especial?",
]

CLIENTE_COMPARA = [
    "Es que en Truper me lo dan mas barato", "Y por que son mejores que los demas?",
    "Pero en la competencia dan credito", "Es que yo compro en la central de abastos",
    "Pues Home Depot tiene buenos precios", "Y que ventaja tienen sobre Pretul?",
    "Pero yo ya tengo buen precio con mi proveedor actual",
    "Me conviene mas comprar en la central", "Es que mi proveedor me fia",
    "Y por que deberia cambiar de proveedor?",
]

MULTIPLES_PERSONAS = [
    "Espere le paso al dueno", "Dejeme preguntarle a mi jefe",
    "Ahorita le comunico", "Permitame tantito, le paso la llamada",
    "Pasemela al encargado", "Un momento, le transfiero",
    "Le voy a pasar a mi companero que ve eso", "Espere, quien es?",
    "Dejeme consultarlo con mi socio", "Ahorita le hablo al patron",
]

DATOS_PROACTIVOS = [
    "Mire mi WhatsApp es 33 1234 5678, mandeme info",
    "Mi correo es tienda@gmail.com si quiere mande ahi",
    "Apunte, el numero es 33 9876 5432",
    "Le doy mi cel para que me mande el catalogo: 55 1234 5678",
    "Anote mi email: compras@outlook.com",
    "Mi wats es el mismo numero que le marco",
    "El WhatsApp de la tienda es 33 4567 8901",
    "Si quiere le doy mi correo: negocio@hotmail.com",
    "Tome nota del celular del encargado: 81 2345 6789",
    "Le doy el numero de la tienda: 33 5678 1234",
]

CAMBIO_OPINION = [
    "Sabe que, mejor si mandelo por WhatsApp",
    "No espere, mejor al correo",
    "Pensandolo bien si me interesa",
    "Bueno ya que, si mandeme el catalogo",
    "Sabe que, mejor no. Ya no me interesa",
    "Espere, mejor mandelo al otro numero",
    "No ya mejor dejelo asi", "Ah bueno, entonces si mande al correo",
    "Sabe que, si al WhatsApp pero a otro numero",
    "Mejor el catalogo mandelo al email",
]

PIDE_HABLAR_JEFE = [
    "Puedo hablar con su supervisor?", "Quien es su jefe?",
    "Paseme con su encargado", "Quiero hablar con alguien mas",
    "Puede comunicarme con su gerente?", "No quiero hablar con usted, paseme a otro",
    "Hay alguien mas con quien pueda hablar?", "Quiero quejarme con su supervisor",
    "Quien lo manda a usted?", "Quiero hablar con un humano de verdad",
]

YA_LLAMARON = [
    "Ya me hablaron de ahi", "Ya llamaron la semana pasada",
    "Otra vez? Ya me llamaron antes", "Si ya me marcaron hace rato",
    "Ya me habian llamado de NIOVAL", "Es la tercera vez que llaman",
    "Ya conozco, ya me habian llamado", "Si ya me hablo un companero suyo",
    "Ya nos contactaron y dijimos que no", "Ya tengo su catalogo, ya me lo mandaron",
]

DA_NOMBRE_ENCARGADO = [
    "El encargado se llama Don Pedro", "Hable con el senor Martinez",
    "Tiene que hablar con Juan", "El que ve eso es el ingeniero Lopez",
    "Pregunte por la licenciada Garcia", "Busque al contador Ramirez",
    "El encargado es Don Roberto pero no esta", "Hable con Dona Maria ella ve las compras",
    "Pregunte por el senor Hernandez", "El dueno es Don Jose pero no ha llegado",
]

NO_DA_DATOS = [
    "Si pero no le voy a dar mi numero", "No le doy mis datos",
    "Para que quieren mi informacion?", "No, datos personales no doy por telefono",
    "Y para que ocupan mi correo?", "No se, no me gusta dar mis datos asi",
    "Uy no, eso de dar el celular no me late", "Pues mandelo aqui al telefono de la tienda",
    "No no, mi numero personal no", "Y no me lo pueden mandar de otra forma?",
]

MONOSILABICO = [
    "Si", "No", "Aja", "Mmm", "Ok", "Sale", "Va", "Orale",
    "Bueno", "Pues si", "Puede ser", "Quien sabe", "A lo mejor",
    "Ah", "Ey", "Nel", "Simon", "Nop", "Sep", "Ya",
]

SPANGLISH = [
    "Let me check con el manager", "No tengo el email, sorry",
    "Send it to my WhatsApp please", "Ok, let me give you my number",
    "We already have a supplier, pero thanks", "Hold on, let me ask",
    "The boss is not here right now", "Can you call back later?",
    "Ok whatever, mandelo", "Si, it's fine, al WhatsApp",
]

SIN_AUTORIDAD = [
    "Yo nomas soy empleado, no puedo decidir eso",
    "Tendria que hablar con el dueno", "Yo no veo eso de las compras",
    "No soy el encargado, soy el que atiende", "Yo nomas estoy cuidando",
    "El patron es el que decide eso", "Yo soy el chalancito nomas",
    "No me dejan a mi decidir esas cosas", "Soy el ayudante nomas",
    "Yo nomas contesto el telefono",
]

HORAS_CALLBACK = [
    "como a las 3", "despues de las 2", "en la tarde", "manana en la manana",
    "como a las 10", "despues de comer", "como en una hora",
    "ya como a las 5", "manana temprano", "el lunes",
    "como a las 12", "en un ratito", "ya mas tarde",
]


def _gen_telefono():
    """Genera telefono mexicano aleatorio."""
    lada = random.choice(["33", "55", "81", "22", "44", "47", "66", "61", "99", "22"])
    return f"{lada}{random.randint(10000000, 99999999)}"


def _gen_contacto(idx):
    """Genera contacto unico."""
    giro = random.choice(GIROS)
    nombre = random.choice(NOMBRES_NEGOCIO)
    ciudad = random.choice(CIUDADES)
    return {
        "nombre_negocio": f"{giro} {nombre}",
        "telefono": _gen_telefono(),
        "ciudad": ciudad,
    }


def _gen_email(idx):
    """Genera email dictado."""
    tpl = random.choice(EMAILS)
    email = tpl.format(n=idx)
    # A veces dictar con "arroba" en vez de @
    if random.random() < 0.5:
        email_dictado = email.replace("@", " arroba ").replace(".", " punto ")
        return email, f"Es {email_dictado}"
    return email, f"Si, el correo es {email}"


def _gen_numero_dictado():
    """Genera numero dictado de forma variada."""
    a = f"{random.randint(1000, 9999)}"
    b = f"{random.randint(1000, 9999)}"
    c = a[:2]
    d = a[2:]
    fmt = random.choice(NUMEROS_TELEFONO_FORMATS)
    return fmt.format(a=a, b=b, c=c, d=d)


# ── Generadores por grupo ───────────────────────────────────────────────

def gen_g18_confuso(gid, start_vid, count=15):
    """Cliente confuso / no entiende el producto."""
    scenarios = []
    for i in range(count):
        vid = start_vid + i
        contacto = _gen_contacto(vid)
        pregunta = random.choice(PREGUNTAS_PRODUCTO)
        pregunta2 = random.choice(PREGUNTAS_EMPRESA)
        saludo = random.choice(SALUDOS_CLIENTE).format(giro=contacto["nombre_negocio"].split()[0], nombre=contacto["nombre_negocio"])
        turnos = [
            {"cliente": saludo, "check_not": []},
            {"cliente": random.choice(CONFIRMACIONES_ENCARGADO), "check_not": []},
            {"cliente": pregunta, "check_not": []},
            {"cliente": pregunta2, "check_not": []},
            {"cliente": random.choice(ACEPTA_WHATSAPP), "check_not": []},
            {"cliente": _gen_numero_dictado(), "check_not": []},
        ]
        scenarios.append({
            "id": f"OOS-{gid:02d}-{vid:02d}",
            "nombre": f"G{gid}: Cliente confuso pregunta producto+empresa #{i+1}",
            "contacto": contacto,
            "turnos": turnos,
            "bugs_criticos": [],
        })
    return scenarios


def gen_g19_ya_tiene_proveedor(gid, start_vid, count=15):
    """Cliente ya tiene proveedor similar."""
    scenarios = []
    for i in range(count):
        vid = start_vid + i
        contacto = _gen_contacto(vid)
        saludo = random.choice(SALUDOS_CLIENTE).format(giro=contacto["nombre_negocio"].split()[0], nombre=contacto["nombre_negocio"])
        proveedor_msg = random.choice(CLIENTE_YA_TIENE_PROVEEDOR)
        # 50% acepta de todos modos, 50% rechaza
        if random.random() < 0.5:
            turnos = [
                {"cliente": saludo, "check_not": []},
                {"cliente": random.choice(CONFIRMACIONES_ENCARGADO), "check_not": []},
                {"cliente": proveedor_msg, "check_not": []},
                {"cliente": "Bueno, mandeme el catalogo a ver que tal", "check_not": []},
                {"cliente": random.choice(ACEPTA_WHATSAPP), "check_not": []},
                {"cliente": _gen_numero_dictado(), "check_not": []},
            ]
        else:
            turnos = [
                {"cliente": saludo, "check_not": []},
                {"cliente": random.choice(CONFIRMACIONES_ENCARGADO), "check_not": []},
                {"cliente": proveedor_msg, "check_not": []},
                {"cliente": random.choice(RECHAZA_TODO), "check_not": []},
            ]
        scenarios.append({
            "id": f"OOS-{gid:02d}-{vid:02d}",
            "nombre": f"G{gid}: Ya tiene proveedor #{i+1}",
            "contacto": contacto,
            "turnos": turnos,
            "bugs_criticos": [],
        })
    return scenarios


def gen_g20_pide_descuento(gid, start_vid, count=15):
    """Cliente pide descuentos/promociones."""
    scenarios = []
    for i in range(count):
        vid = start_vid + i
        contacto = _gen_contacto(vid)
        saludo = random.choice(SALUDOS_CLIENTE).format(giro=contacto["nombre_negocio"].split()[0], nombre=contacto["nombre_negocio"])
        descuento = random.choice(CLIENTE_PIDE_DESCUENTO)
        turnos = [
            {"cliente": saludo, "check_not": []},
            {"cliente": random.choice(CONFIRMACIONES_ENCARGADO), "check_not": []},
            {"cliente": descuento, "check_not": []},
            {"cliente": "Bueno si, mandeme el catalogo con precios", "check_not": []},
            {"cliente": random.choice(ACEPTA_WHATSAPP + ACEPTA_CORREO), "check_not": []},
            {"cliente": _gen_numero_dictado(), "check_not": []},
        ]
        scenarios.append({
            "id": f"OOS-{gid:02d}-{vid:02d}",
            "nombre": f"G{gid}: Pide descuento #{i+1}",
            "contacto": contacto,
            "turnos": turnos,
            "bugs_criticos": [],
        })
    return scenarios


def gen_g21_compara_competencia(gid, start_vid, count=15):
    """Cliente compara con competencia."""
    scenarios = []
    for i in range(count):
        vid = start_vid + i
        contacto = _gen_contacto(vid)
        saludo = random.choice(SALUDOS_CLIENTE).format(giro=contacto["nombre_negocio"].split()[0], nombre=contacto["nombre_negocio"])
        compara = random.choice(CLIENTE_COMPARA)
        turnos = [
            {"cliente": saludo, "check_not": []},
            {"cliente": random.choice(CONFIRMACIONES_ENCARGADO), "check_not": []},
            {"cliente": compara, "check_not": []},
            {"cliente": "Pues si, a ver mandeme el catalogo para comparar", "check_not": []},
            {"cliente": random.choice(ACEPTA_WHATSAPP), "check_not": []},
            {"cliente": _gen_numero_dictado(), "check_not": []},
        ]
        scenarios.append({
            "id": f"OOS-{gid:02d}-{vid:02d}",
            "nombre": f"G{gid}: Compara competencia #{i+1}",
            "contacto": contacto,
            "turnos": turnos,
            "bugs_criticos": [],
        })
    return scenarios


def gen_g22_multiples_personas(gid, start_vid, count=15):
    """Multiples personas en la llamada."""
    scenarios = []
    for i in range(count):
        vid = start_vid + i
        contacto = _gen_contacto(vid)
        saludo = random.choice(SALUDOS_CLIENTE).format(giro=contacto["nombre_negocio"].split()[0], nombre=contacto["nombre_negocio"])
        pasa_llamada = random.choice(MULTIPLES_PERSONAS)
        turnos = [
            {"cliente": saludo, "check_not": []},
            {"cliente": pasa_llamada, "check_not": []},
            # Segunda persona contesta
            {"cliente": "Si, bueno, digame", "check_not": []},
            {"cliente": random.choice(CONFIRMACIONES_ENCARGADO), "check_not": []},
            {"cliente": random.choice(ACEPTA_WHATSAPP + ACEPTA_CORREO), "check_not": []},
            {"cliente": _gen_numero_dictado(), "check_not": []},
        ]
        scenarios.append({
            "id": f"OOS-{gid:02d}-{vid:02d}",
            "nombre": f"G{gid}: Multiples personas #{i+1}",
            "contacto": contacto,
            "turnos": turnos,
            "bugs_criticos": [],
        })
    return scenarios


def gen_g23_datos_proactivos(gid, start_vid, count=15):
    """Cliente da datos proactivamente sin que Bruce pregunte."""
    scenarios = []
    for i in range(count):
        vid = start_vid + i
        contacto = _gen_contacto(vid)
        saludo = random.choice(SALUDOS_CLIENTE).format(giro=contacto["nombre_negocio"].split()[0], nombre=contacto["nombre_negocio"])
        dato = random.choice(DATOS_PROACTIVOS)
        turnos = [
            {"cliente": saludo, "check_not": []},
            {"cliente": random.choice(CONFIRMACIONES_ENCARGADO), "check_not": []},
            {"cliente": dato, "check_not": []},
            {"cliente": random.choice(DESPEDIDAS_CLIENTE), "check_not": []},
        ]
        scenarios.append({
            "id": f"OOS-{gid:02d}-{vid:02d}",
            "nombre": f"G{gid}: Datos proactivos #{i+1}",
            "contacto": contacto,
            "turnos": turnos,
            "bugs_criticos": [],
        })
    return scenarios


def gen_g24_cambia_opinion(gid, start_vid, count=15):
    """Cliente cambia de opinion mid-call."""
    scenarios = []
    for i in range(count):
        vid = start_vid + i
        contacto = _gen_contacto(vid)
        saludo = random.choice(SALUDOS_CLIENTE).format(giro=contacto["nombre_negocio"].split()[0], nombre=contacto["nombre_negocio"])
        cambio = random.choice(CAMBIO_OPINION)
        turnos = [
            {"cliente": saludo, "check_not": []},
            {"cliente": random.choice(CONFIRMACIONES_ENCARGADO), "check_not": []},
            {"cliente": random.choice(RECHAZA_TODO), "check_not": []},
            {"cliente": cambio, "check_not": []},
            {"cliente": _gen_numero_dictado(), "check_not": []},
        ]
        scenarios.append({
            "id": f"OOS-{gid:02d}-{vid:02d}",
            "nombre": f"G{gid}: Cambia de opinion #{i+1}",
            "contacto": contacto,
            "turnos": turnos,
            "bugs_criticos": [],
        })
    return scenarios


def gen_g25_garantias(gid, start_vid, count=15):
    """Cliente pregunta garantias/devoluciones."""
    preguntas = [
        "Tienen garantia en sus productos?", "Y si no me gustan los devuelvo?",
        "Que pasa si llegan danados?", "Hacen cambios?",
        "Cuanto tiempo de garantia dan?", "Si no me sirve me devuelven mi dinero?",
        "Responden por la calidad?", "Y si sale defectuoso?",
        "Tienen politica de devolucion?", "Garantizan la calidad?",
        "Si no es lo que esperaba puedo regresar el pedido?",
        "Manejan algun seguro en el envio?", "Que pasa si no me llega?",
        "Y si llega incompleto?", "Me dan factura con garantia?",
    ]
    scenarios = []
    for i in range(count):
        vid = start_vid + i
        contacto = _gen_contacto(vid)
        saludo = random.choice(SALUDOS_CLIENTE).format(giro=contacto["nombre_negocio"].split()[0], nombre=contacto["nombre_negocio"])
        pregunta = preguntas[i % len(preguntas)]
        turnos = [
            {"cliente": saludo, "check_not": []},
            {"cliente": random.choice(CONFIRMACIONES_ENCARGADO), "check_not": []},
            {"cliente": pregunta, "check_not": []},
            {"cliente": "Ah ok, pues si mandeme el catalogo", "check_not": []},
            {"cliente": random.choice(ACEPTA_WHATSAPP), "check_not": []},
            {"cliente": _gen_numero_dictado(), "check_not": []},
        ]
        scenarios.append({
            "id": f"OOS-{gid:02d}-{vid:02d}",
            "nombre": f"G{gid}: Pregunta garantias #{i+1}",
            "contacto": contacto,
            "turnos": turnos,
            "bugs_criticos": [],
        })
    return scenarios


def gen_g26_frases_cortadas(gid, start_vid, count=15):
    """Frases cortadas / respuestas incompletas."""
    frases = [
        "Si este... como le digo... pues si", "Ah pues... dejeme ver... si",
        "Es que mire... bueno si", "Como le explico... ya tenemos...",
        "Pues la verdad... no se... dejeme pensar",
        "Aja... si... este...", "Mmm... pues... a ver...",
        "Si pero... es que... bueno mandelo", "No pues... este... si esta bien",
        "Ah caray... dejeme... si por WhatsApp", "Si es que... ando ocupado pero si",
        "Pues mire... la cosa es que... si mandelo",
        "Oiga... es que... bueno al WhatsApp", "A ver... como era... si el numero es",
        "Mmm dejeme buscar... si aqui esta mi celular",
    ]
    scenarios = []
    for i in range(count):
        vid = start_vid + i
        contacto = _gen_contacto(vid)
        saludo = random.choice(SALUDOS_CLIENTE).format(giro=contacto["nombre_negocio"].split()[0], nombre=contacto["nombre_negocio"])
        frase = frases[i % len(frases)]
        turnos = [
            {"cliente": saludo, "check_not": []},
            {"cliente": random.choice(CONFIRMACIONES_ENCARGADO), "check_not": []},
            {"cliente": frase, "check_not": []},
            {"cliente": random.choice(ACEPTA_WHATSAPP), "check_not": []},
            {"cliente": _gen_numero_dictado(), "check_not": []},
        ]
        scenarios.append({
            "id": f"OOS-{gid:02d}-{vid:02d}",
            "nombre": f"G{gid}: Frases cortadas #{i+1}",
            "contacto": contacto,
            "turnos": turnos,
            "bugs_criticos": [],
        })
    return scenarios


def gen_g27_emails_raros(gid, start_vid, count=15):
    """Emails con dominios raros/dictado dificil."""
    emails_dificiles = [
        ("juan.perez_2024@prodigy.net.mx", "juan punto perez guion bajo 2024 arroba prodigy punto net punto mx"),
        ("compras-tienda@empresas.com.mx", "compras guion tienda arroba empresas punto com punto mx"),
        ("el.negocio.123@yahoo.com.mx", "el punto negocio punto 123 arroba yahoo punto com punto mx"),
        ("info+ventas@gmail.com", "info mas ventas arroba gmail punto com"),
        ("admin_2024@outlook.es", "admin guion bajo 2024 arroba outlook punto es"),
        ("la.ferreteria@live.com.mx", "la punto ferreteria arroba live punto com punto mx"),
        ("contacto.directo@icloud.com", "contacto punto directo arroba icloud punto com"),
        ("tienda-nueva-2025@hotmail.com", "tienda guion nueva guion 2025 arroba hotmail punto com"),
        ("gerente.compras@empresa.mx", "gerente punto compras arroba empresa punto mx"),
        ("pedidos_express@yahoo.es", "pedidos guion bajo express arroba yahoo punto es"),
        ("don.pedro.martinez@gmail.com", "don punto pedro punto martinez arroba gmail punto com"),
        ("ferreteria.el.clavo@outlook.com", "ferreteria punto el punto clavo arroba outlook punto com"),
        ("ventas2024@prodigy.net.mx", "ventas 2024 arroba prodigy punto net punto mx"),
        ("la_tlapaleria@hotmail.es", "la guion bajo tlapaleria arroba hotmail punto es"),
        ("compras.mayoreo@gmail.com", "compras punto mayoreo arroba gmail punto com"),
    ]
    scenarios = []
    for i in range(count):
        vid = start_vid + i
        contacto = _gen_contacto(vid)
        saludo = random.choice(SALUDOS_CLIENTE).format(giro=contacto["nombre_negocio"].split()[0], nombre=contacto["nombre_negocio"])
        email_real, email_dictado = emails_dificiles[i % len(emails_dificiles)]
        turnos = [
            {"cliente": saludo, "check_not": []},
            {"cliente": random.choice(CONFIRMACIONES_ENCARGADO), "check_not": []},
            {"cliente": "No tengo WhatsApp", "check_not": ["whatsapp", "WhatsApp"]},
            {"cliente": f"Si, el correo es {email_dictado}", "check_not": []},
            {"cliente": random.choice(DESPEDIDAS_CLIENTE), "check_not": ["whatsapp", "WhatsApp"]},
        ]
        scenarios.append({
            "id": f"OOS-{gid:02d}-{vid:02d}",
            "nombre": f"G{gid}: Email dificil #{i+1}",
            "contacto": contacto,
            "turnos": turnos,
            "bugs_criticos": ["DATO_NEGADO_REINSISTIDO"],
        })
    return scenarios


def gen_g28_pide_hablar_jefe(gid, start_vid, count=15):
    """Cliente pide hablar con jefe de Bruce."""
    scenarios = []
    for i in range(count):
        vid = start_vid + i
        contacto = _gen_contacto(vid)
        saludo = random.choice(SALUDOS_CLIENTE).format(giro=contacto["nombre_negocio"].split()[0], nombre=contacto["nombre_negocio"])
        pide_jefe = random.choice(PIDE_HABLAR_JEFE)
        turnos = [
            {"cliente": saludo, "check_not": []},
            {"cliente": pide_jefe, "check_not": []},
            {"cliente": "Bueno pues mandeme el catalogo entonces", "check_not": []},
            {"cliente": random.choice(ACEPTA_WHATSAPP), "check_not": []},
            {"cliente": _gen_numero_dictado(), "check_not": []},
        ]
        scenarios.append({
            "id": f"OOS-{gid:02d}-{vid:02d}",
            "nombre": f"G{gid}: Pide hablar con jefe #{i+1}",
            "contacto": contacto,
            "turnos": turnos,
            "bugs_criticos": [],
        })
    return scenarios


def gen_g29_ya_llamaron(gid, start_vid, count=15):
    """Cliente dice que ya llamaron antes."""
    scenarios = []
    for i in range(count):
        vid = start_vid + i
        contacto = _gen_contacto(vid)
        saludo = random.choice(SALUDOS_CLIENTE).format(giro=contacto["nombre_negocio"].split()[0], nombre=contacto["nombre_negocio"])
        ya_llamaron = random.choice(YA_LLAMARON)
        # 50% acepta, 50% rechaza
        if random.random() < 0.5:
            turnos = [
                {"cliente": saludo, "check_not": []},
                {"cliente": ya_llamaron, "check_not": []},
                {"cliente": "Bueno pues si, esta vez si mandeme el catalogo", "check_not": []},
                {"cliente": random.choice(ACEPTA_WHATSAPP), "check_not": []},
                {"cliente": _gen_numero_dictado(), "check_not": []},
            ]
        else:
            turnos = [
                {"cliente": saludo, "check_not": []},
                {"cliente": ya_llamaron, "check_not": []},
                {"cliente": "No, ya les dije que no me interesa", "check_not": []},
            ]
        scenarios.append({
            "id": f"OOS-{gid:02d}-{vid:02d}",
            "nombre": f"G{gid}: Ya llamaron antes #{i+1}",
            "contacto": contacto,
            "turnos": turnos,
            "bugs_criticos": [],
        })
    return scenarios


def gen_g30_nombre_encargado(gid, start_vid, count=15):
    """Da nombre del encargado pero no esta."""
    scenarios = []
    for i in range(count):
        vid = start_vid + i
        contacto = _gen_contacto(vid)
        saludo = random.choice(SALUDOS_CLIENTE).format(giro=contacto["nombre_negocio"].split()[0], nombre=contacto["nombre_negocio"])
        nombre_enc = random.choice(DA_NOMBRE_ENCARGADO)
        hora = random.choice(HORAS_CALLBACK)
        turnos = [
            {"cliente": saludo, "check_not": []},
            {"cliente": nombre_enc, "check_not": []},
            {"cliente": f"Llame {hora}", "check_not": []},
            {"cliente": random.choice(DESPEDIDAS_CLIENTE), "check_not": []},
        ]
        scenarios.append({
            "id": f"OOS-{gid:02d}-{vid:02d}",
            "nombre": f"G{gid}: Nombre encargado ausente #{i+1}",
            "contacto": contacto,
            "turnos": turnos,
            "bugs_criticos": [],
        })
    return scenarios


def gen_g31_no_da_datos(gid, start_vid, count=15):
    """Quiere catalogo pero no quiere dar datos."""
    scenarios = []
    for i in range(count):
        vid = start_vid + i
        contacto = _gen_contacto(vid)
        saludo = random.choice(SALUDOS_CLIENTE).format(giro=contacto["nombre_negocio"].split()[0], nombre=contacto["nombre_negocio"])
        no_dato = random.choice(NO_DA_DATOS)
        turnos = [
            {"cliente": saludo, "check_not": []},
            {"cliente": random.choice(CONFIRMACIONES_ENCARGADO), "check_not": []},
            {"cliente": "Si me interesa el catalogo", "check_not": []},
            {"cliente": no_dato, "check_not": []},
            # Al final cede
            {"cliente": "Bueno ya, tome nota: " + _gen_numero_dictado(), "check_not": []},
        ]
        scenarios.append({
            "id": f"OOS-{gid:02d}-{vid:02d}",
            "nombre": f"G{gid}: No da datos #{i+1}",
            "contacto": contacto,
            "turnos": turnos,
            "bugs_criticos": [],
        })
    return scenarios


def gen_g32_horarios_envios(gid, start_vid, count=15):
    """Pregunta horarios/envios/cobertura."""
    scenarios = []
    for i in range(count):
        vid = start_vid + i
        contacto = _gen_contacto(vid)
        saludo = random.choice(SALUDOS_CLIENTE).format(giro=contacto["nombre_negocio"].split()[0], nombre=contacto["nombre_negocio"])
        pregunta = random.choice(PREGUNTAS_ENVIO)
        turnos = [
            {"cliente": saludo, "check_not": []},
            {"cliente": random.choice(CONFIRMACIONES_ENCARGADO), "check_not": []},
            {"cliente": pregunta, "check_not": []},
            {"cliente": "Ah ok, pues mandeme el catalogo para ver", "check_not": []},
            {"cliente": random.choice(ACEPTA_WHATSAPP + ACEPTA_CORREO), "check_not": []},
            {"cliente": _gen_numero_dictado(), "check_not": []},
        ]
        scenarios.append({
            "id": f"OOS-{gid:02d}-{vid:02d}",
            "nombre": f"G{gid}: Pregunta envios #{i+1}",
            "contacto": contacto,
            "turnos": turnos,
            "bugs_criticos": [],
        })
    return scenarios


def gen_g33_monosilabico(gid, start_vid, count=15):
    """Respuestas monosilabicas."""
    scenarios = []
    for i in range(count):
        vid = start_vid + i
        contacto = _gen_contacto(vid)
        turnos = [
            {"cliente": random.choice(["Si", "Bueno", "Aja", "Mande"]), "check_not": []},
            {"cliente": random.choice(["Si", "Aja", "Mmm"]), "check_not": []},
            {"cliente": random.choice(["Si", "Ok", "Va"]), "check_not": []},
            {"cliente": random.choice(["Aja", "Si", "Sale"]), "check_not": []},
            {"cliente": _gen_numero_dictado(), "check_not": []},
        ]
        scenarios.append({
            "id": f"OOS-{gid:02d}-{vid:02d}",
            "nombre": f"G{gid}: Monosilabico #{i+1}",
            "contacto": contacto,
            "turnos": turnos,
            "bugs_criticos": [],
        })
    return scenarios


def gen_g34_interrumpe_cambia_tema(gid, start_vid, count=15):
    """Cliente interrumpe y cambia de tema."""
    interrupciones = [
        "Espere tantito... ya, digame", "Oiga y aparte de eso, venden pinturas?",
        "Perdon estaba con un cliente, que decia?", "Ah si si, y tienen envio gratis?",
        "Mire ahorita ando ocupado pero si me interesa", "Dejeme tantito que llego un cliente",
        "Si pero primero digame cuanto cuesta", "Oiga y por cierto de donde habla?",
        "Espere... ok ya, continue", "Ah y tambien manejan material electrico?",
        "No espere, antes de eso, facturan?", "Si pero oiga, dan credito?",
        "Un momento... listo, que decia?", "Oiga pero primero, son de confianza?",
        "Si si pero cuanto es el pedido minimo?",
    ]
    scenarios = []
    for i in range(count):
        vid = start_vid + i
        contacto = _gen_contacto(vid)
        saludo = random.choice(SALUDOS_CLIENTE).format(giro=contacto["nombre_negocio"].split()[0], nombre=contacto["nombre_negocio"])
        interrupcion = interrupciones[i % len(interrupciones)]
        turnos = [
            {"cliente": saludo, "check_not": []},
            {"cliente": random.choice(CONFIRMACIONES_ENCARGADO), "check_not": []},
            {"cliente": interrupcion, "check_not": []},
            {"cliente": "Bueno si, mandeme la info", "check_not": []},
            {"cliente": random.choice(ACEPTA_WHATSAPP), "check_not": []},
            {"cliente": _gen_numero_dictado(), "check_not": []},
        ]
        scenarios.append({
            "id": f"OOS-{gid:02d}-{vid:02d}",
            "nombre": f"G{gid}: Interrumpe/cambia tema #{i+1}",
            "contacto": contacto,
            "turnos": turnos,
            "bugs_criticos": [],
        })
    return scenarios


def gen_g35_spanglish(gid, start_vid, count=15):
    """Spanglish / anglicismos."""
    scenarios = []
    for i in range(count):
        vid = start_vid + i
        contacto = _gen_contacto(vid)
        saludo = random.choice(SALUDOS_CLIENTE).format(giro=contacto["nombre_negocio"].split()[0], nombre=contacto["nombre_negocio"])
        spanglish = random.choice(SPANGLISH)
        turnos = [
            {"cliente": saludo, "check_not": []},
            {"cliente": spanglish, "check_not": []},
            {"cliente": "Ok fine, send it por WhatsApp", "check_not": []},
            {"cliente": _gen_numero_dictado(), "check_not": []},
        ]
        scenarios.append({
            "id": f"OOS-{gid:02d}-{vid:02d}",
            "nombre": f"G{gid}: Spanglish #{i+1}",
            "contacto": contacto,
            "turnos": turnos,
            "bugs_criticos": [],
        })
    return scenarios


def gen_g36_sin_autoridad(gid, start_vid, count=15):
    """Empleado sin autoridad de compra."""
    scenarios = []
    for i in range(count):
        vid = start_vid + i
        contacto = _gen_contacto(vid)
        saludo = random.choice(SALUDOS_CLIENTE).format(giro=contacto["nombre_negocio"].split()[0], nombre=contacto["nombre_negocio"])
        sin_aut = random.choice(SIN_AUTORIDAD)
        hora = random.choice(HORAS_CALLBACK)
        turnos = [
            {"cliente": saludo, "check_not": []},
            {"cliente": sin_aut, "check_not": []},
            {"cliente": f"El dueno viene {hora}", "check_not": []},
            {"cliente": random.choice(DESPEDIDAS_CLIENTE), "check_not": []},
        ]
        scenarios.append({
            "id": f"OOS-{gid:02d}-{vid:02d}",
            "nombre": f"G{gid}: Sin autoridad #{i+1}",
            "contacto": contacto,
            "turnos": turnos,
            "bugs_criticos": [],
        })
    return scenarios


def gen_g37_multiflow(gid, start_vid, count=15):
    """Flujos complejos multi-giro."""
    scenarios = []
    for i in range(count):
        vid = start_vid + i
        contacto = _gen_contacto(vid)
        saludo = random.choice(SALUDOS_CLIENTE).format(giro=contacto["nombre_negocio"].split()[0], nombre=contacto["nombre_negocio"])
        # Escenarios que combinan multiples situaciones
        variant = i % 5
        if variant == 0:
            # Rechaza WA, pregunta producto, acepta correo
            turnos = [
                {"cliente": saludo, "check_not": []},
                {"cliente": random.choice(CONFIRMACIONES_ENCARGADO), "check_not": []},
                {"cliente": random.choice(PREGUNTAS_PRODUCTO), "check_not": []},
                {"cliente": random.choice(RECHAZA_WHATSAPP), "check_not": ["whatsapp", "WhatsApp"]},
                {"cliente": random.choice(PREGUNTAS_PRECIO), "check_not": ["whatsapp", "WhatsApp"]},
                {"cliente": f"El correo es negocio{vid}@gmail.com", "check_not": ["whatsapp", "WhatsApp"]},
            ]
        elif variant == 1:
            # Pasa llamada + proveedor existente + acepta
            turnos = [
                {"cliente": saludo, "check_not": []},
                {"cliente": random.choice(MULTIPLES_PERSONAS), "check_not": []},
                {"cliente": "Si bueno, digame", "check_not": []},
                {"cliente": random.choice(CLIENTE_YA_TIENE_PROVEEDOR), "check_not": []},
                {"cliente": "Pues a ver, mandeme catalogo al wats", "check_not": []},
                {"cliente": _gen_numero_dictado(), "check_not": []},
            ]
        elif variant == 2:
            # Encargado ausente + da nombre + hora callback
            turnos = [
                {"cliente": saludo, "check_not": []},
                {"cliente": random.choice(ENCARGADO_AUSENTE), "check_not": []},
                {"cliente": random.choice(DA_NOMBRE_ENCARGADO), "check_not": []},
                {"cliente": f"Marcale {random.choice(HORAS_CALLBACK)}", "check_not": []},
            ]
        elif variant == 3:
            # Pregunta garantia + descuento + acepta
            turnos = [
                {"cliente": saludo, "check_not": []},
                {"cliente": random.choice(CONFIRMACIONES_ENCARGADO), "check_not": []},
                {"cliente": "Tienen garantia en sus productos?", "check_not": []},
                {"cliente": random.choice(CLIENTE_PIDE_DESCUENTO), "check_not": []},
                {"cliente": "Bueno si, al WhatsApp", "check_not": []},
                {"cliente": _gen_numero_dictado(), "check_not": []},
            ]
        else:
            # Monosilabico + interrumpe + da datos rapido
            turnos = [
                {"cliente": "Aja", "check_not": []},
                {"cliente": "Si", "check_not": []},
                {"cliente": "Oiga espere... ya, si mandelo", "check_not": []},
                {"cliente": "Al wats, " + _gen_numero_dictado(), "check_not": []},
            ]
        scenarios.append({
            "id": f"OOS-{gid:02d}-{vid:02d}",
            "nombre": f"G{gid}: Multi-flow #{i+1}",
            "contacto": contacto,
            "turnos": turnos,
            "bugs_criticos": [],
        })
    return scenarios


# ── Grupos extra para llegar a 1000 ─────────────────────────────────────

def gen_g_precio_facturacion(gid, start_vid, count=15):
    """Preguntas de precio y facturacion."""
    scenarios = []
    for i in range(count):
        vid = start_vid + i
        contacto = _gen_contacto(vid)
        saludo = random.choice(SALUDOS_CLIENTE).format(giro=contacto["nombre_negocio"].split()[0], nombre=contacto["nombre_negocio"])
        pregunta = random.choice(PREGUNTAS_PRECIO)
        turnos = [
            {"cliente": saludo, "check_not": []},
            {"cliente": random.choice(CONFIRMACIONES_ENCARGADO), "check_not": []},
            {"cliente": pregunta, "check_not": []},
            {"cliente": "Bueno mandeme la info", "check_not": []},
            {"cliente": random.choice(ACEPTA_WHATSAPP + ACEPTA_CORREO), "check_not": []},
            {"cliente": _gen_numero_dictado(), "check_not": []},
        ]
        scenarios.append({
            "id": f"OOS-{gid:02d}-{vid:02d}",
            "nombre": f"G{gid}: Precio/facturacion #{i+1}",
            "contacto": contacto,
            "turnos": turnos,
            "bugs_criticos": [],
        })
    return scenarios


def gen_g_rechazo_variado(gid, start_vid, count=15):
    """Rechazos con diferentes tonos y razones."""
    rechazos_variados = [
        "No gracias, no me interesa para nada",
        "Mire joven, no me haga perder el tiempo",
        "Ya no me llamen por favor", "Estoy en lista de no llamar",
        "No compro nada por telefono", "Esto es spam verdad?",
        "No tengo tiempo para esto", "Estoy muy ocupado, colguele",
        "No necesitamos nada de eso aqui", "Ya nos surtimos la semana pasada",
        "Estamos en quiebra, no compramos nada", "Ya vamos a cerrar el negocio",
        "No me interesa, ya no insista", "Eso no lo vendemos nosotros",
        "Llame a otro lado por favor",
    ]
    scenarios = []
    for i in range(count):
        vid = start_vid + i
        contacto = _gen_contacto(vid)
        saludo = random.choice(SALUDOS_CLIENTE).format(giro=contacto["nombre_negocio"].split()[0], nombre=contacto["nombre_negocio"])
        rechazo = rechazos_variados[i % len(rechazos_variados)]
        turnos = [
            {"cliente": saludo, "check_not": []},
            {"cliente": rechazo, "check_not": []},
        ]
        scenarios.append({
            "id": f"OOS-{gid:02d}-{vid:02d}",
            "nombre": f"G{gid}: Rechazo variado #{i+1}",
            "contacto": contacto,
            "turnos": turnos,
            "bugs_criticos": [],
        })
    return scenarios


def gen_g_callback_detallado(gid, start_vid, count=15):
    """Callback con detalles especificos."""
    scenarios = []
    for i in range(count):
        vid = start_vid + i
        contacto = _gen_contacto(vid)
        saludo = random.choice(SALUDOS_CLIENTE).format(giro=contacto["nombre_negocio"].split()[0], nombre=contacto["nombre_negocio"])
        ausente = random.choice(ENCARGADO_AUSENTE)
        hora = random.choice(HORAS_CALLBACK)
        turnos = [
            {"cliente": saludo, "check_not": []},
            {"cliente": ausente, "check_not": []},
            {"cliente": f"Marque {hora}, a esa hora ya esta", "check_not": []},
            {"cliente": random.choice(DESPEDIDAS_CLIENTE), "check_not": []},
        ]
        scenarios.append({
            "id": f"OOS-{gid:02d}-{vid:02d}",
            "nombre": f"G{gid}: Callback detallado #{i+1}",
            "contacto": contacto,
            "turnos": turnos,
            "bugs_criticos": [],
        })
    return scenarios


def gen_g_numero_incorrecto(gid, start_vid, count=15):
    """Numero equivocado / no es el negocio."""
    frases_equivocado = [
        "Aqui no es ninguna ferreteria", "Se equivoco de numero",
        "No, aqui es una casa particular", "Este no es el numero que busca",
        "No conozco ese negocio", "Aqui no es eso",
        "No, este es un numero personal", "Se equivoco joven",
        "Aqui no vendemos nada de eso", "No existe ese negocio aqui",
        "No, esta mal el numero", "Aqui es una oficina, no una tienda",
        "No se a quien le marca pero aqui no es", "Tiene el numero equivocado",
        "No, aqui es otra cosa",
    ]
    scenarios = []
    for i in range(count):
        vid = start_vid + i
        contacto = _gen_contacto(vid)
        saludo = random.choice(SALUDOS_CLIENTE).format(giro=contacto["nombre_negocio"].split()[0], nombre=contacto["nombre_negocio"])
        equivocado = frases_equivocado[i % len(frases_equivocado)]
        turnos = [
            {"cliente": saludo, "check_not": []},
            {"cliente": equivocado, "check_not": []},
        ]
        scenarios.append({
            "id": f"OOS-{gid:02d}-{vid:02d}",
            "nombre": f"G{gid}: Numero equivocado #{i+1}",
            "contacto": contacto,
            "turnos": turnos,
            "bugs_criticos": ["LOOP"],
        })
    return scenarios


def gen_g_wa_y_correo_rechazados(gid, start_vid, count=15):
    """WA y correo rechazados, solo telefono."""
    scenarios = []
    for i in range(count):
        vid = start_vid + i
        contacto = _gen_contacto(vid)
        saludo = random.choice(SALUDOS_CLIENTE).format(giro=contacto["nombre_negocio"].split()[0], nombre=contacto["nombre_negocio"])
        turnos = [
            {"cliente": saludo, "check_not": []},
            {"cliente": random.choice(CONFIRMACIONES_ENCARGADO), "check_not": []},
            {"cliente": random.choice(RECHAZA_WHATSAPP), "check_not": ["whatsapp", "WhatsApp"]},
            {"cliente": random.choice(RECHAZA_CORREO), "check_not": ["whatsapp", "WhatsApp", "correo", "email"]},
            {"cliente": "Pues llameme y ya, " + _gen_numero_dictado(), "check_not": []},
        ]
        scenarios.append({
            "id": f"OOS-{gid:02d}-{vid:02d}",
            "nombre": f"G{gid}: WA+correo rechazados #{i+1}",
            "contacto": contacto,
            "turnos": turnos,
            "bugs_criticos": ["DATO_NEGADO_REINSISTIDO"],
        })
    return scenarios


def gen_g_happy_path_variado(gid, start_vid, count=15):
    """Happy paths con variaciones de giro y tono."""
    scenarios = []
    for i in range(count):
        vid = start_vid + i
        contacto = _gen_contacto(vid)
        saludo = random.choice(SALUDOS_CLIENTE).format(giro=contacto["nombre_negocio"].split()[0], nombre=contacto["nombre_negocio"])
        turnos = [
            {"cliente": saludo, "check_not": []},
            {"cliente": random.choice(CONFIRMACIONES_ENCARGADO), "check_not": []},
            {"cliente": random.choice(ACEPTA_WHATSAPP), "check_not": []},
            {"cliente": _gen_numero_dictado(), "check_not": []},
            {"cliente": random.choice(DESPEDIDAS_CLIENTE), "check_not": []},
        ]
        scenarios.append({
            "id": f"OOS-{gid:02d}-{vid:02d}",
            "nombre": f"G{gid}: Happy path variado #{i+1}",
            "contacto": contacto,
            "turnos": turnos,
            "bugs_criticos": [],
        })
    return scenarios


def gen_g_acepta_correo_directo(gid, start_vid, count=15):
    """Happy path correo directo."""
    scenarios = []
    for i in range(count):
        vid = start_vid + i
        contacto = _gen_contacto(vid)
        saludo = random.choice(SALUDOS_CLIENTE).format(giro=contacto["nombre_negocio"].split()[0], nombre=contacto["nombre_negocio"])
        email, dictado = _gen_email(vid)
        turnos = [
            {"cliente": saludo, "check_not": []},
            {"cliente": random.choice(CONFIRMACIONES_ENCARGADO), "check_not": []},
            {"cliente": random.choice(ACEPTA_CORREO), "check_not": []},
            {"cliente": dictado, "check_not": []},
            {"cliente": random.choice(DESPEDIDAS_CLIENTE), "check_not": []},
        ]
        scenarios.append({
            "id": f"OOS-{gid:02d}-{vid:02d}",
            "nombre": f"G{gid}: Correo directo #{i+1}",
            "contacto": contacto,
            "turnos": turnos,
            "bugs_criticos": [],
        })
    return scenarios


def gen_g_responde_agresivo(gid, start_vid, count=15):
    """Cliente responde de forma agresiva/molesta."""
    agresivos = [
        "Ya dejen de molestar!", "Otra vez con sus llamadas?",
        "No me vuelvan a llamar!", "Estoy harto de que llamen",
        "Quiten mi numero de su lista!", "Esto es acoso telefonico",
        "Le voy a colgar si sigue insistiendo", "No me interesa y no insista",
        "Dejen de fregar!", "Que parte de NO no entienden?",
        "Me tienen cansado con sus llamadas", "Ya les dije que no mil veces",
        "Si vuelven a llamar los denuncio", "Metanse su catalogo por donde les quepa",
        "No me importa su producto, dejen de llamar",
    ]
    scenarios = []
    for i in range(count):
        vid = start_vid + i
        contacto = _gen_contacto(vid)
        saludo = random.choice(SALUDOS_CLIENTE).format(giro=contacto["nombre_negocio"].split()[0], nombre=contacto["nombre_negocio"])
        agresivo = agresivos[i % len(agresivos)]
        turnos = [
            {"cliente": saludo, "check_not": []},
            {"cliente": agresivo, "check_not": []},
        ]
        scenarios.append({
            "id": f"OOS-{gid:02d}-{vid:02d}",
            "nombre": f"G{gid}: Cliente agresivo #{i+1}",
            "contacto": contacto,
            "turnos": turnos,
            "bugs_criticos": [],
        })
    return scenarios


def gen_g_encargado_ocupado_largo(gid, start_vid, count=15):
    """Encargado ocupado con dialogo largo."""
    ocupado_frases = [
        "Esta atendiendo a un cliente ahorita", "Anda con un proveedor",
        "Esta en una llamada", "No puede atender, esta en almacen",
        "Esta contando mercancia", "Anda descargando un camion",
        "Esta en el banco, regresa en un rato", "Salio a hacer una entrega",
        "Anda en la sucursal", "Fue a hacer un cobro",
        "Esta haciendo inventario", "Anda en la bodega",
        "Tiene una cita con un cliente", "Esta en una reunion",
        "Anda resolviendo un problema urgente",
    ]
    scenarios = []
    for i in range(count):
        vid = start_vid + i
        contacto = _gen_contacto(vid)
        saludo = random.choice(SALUDOS_CLIENTE).format(giro=contacto["nombre_negocio"].split()[0], nombre=contacto["nombre_negocio"])
        ocupado = ocupado_frases[i % len(ocupado_frases)]
        hora = random.choice(HORAS_CALLBACK)
        turnos = [
            {"cliente": saludo, "check_not": []},
            {"cliente": ocupado, "check_not": []},
            {"cliente": "No se cuanto se tarde", "check_not": []},
            {"cliente": f"Pues {hora} mas o menos", "check_not": []},
            {"cliente": random.choice(DESPEDIDAS_CLIENTE), "check_not": []},
        ]
        scenarios.append({
            "id": f"OOS-{gid:02d}-{vid:02d}",
            "nombre": f"G{gid}: Encargado ocupado largo #{i+1}",
            "contacto": contacto,
            "turnos": turnos,
            "bugs_criticos": [],
        })
    return scenarios


def gen_g_pregunta_quien_habla(gid, start_vid, count=15):
    """Cliente pregunta reiteradamente quien habla."""
    preguntas_identidad = [
        "Quien habla?", "De donde me marcan?", "De parte de quien?",
        "Y usted quien es?", "Como dijo que se llama?",
        "Perdon, de que empresa dijo?", "No le entendi, de donde habla?",
        "Y como se llama usted?", "De que compania es?",
        "Como dijo? No le escuche bien", "Puede repetir su nombre?",
        "Y que empresa es?", "Disculpe, de donde dijo que habla?",
        "Perdon, como se llama la empresa?", "Y eso que es, NIOVAL?",
    ]
    scenarios = []
    for i in range(count):
        vid = start_vid + i
        contacto = _gen_contacto(vid)
        saludo = random.choice(SALUDOS_CLIENTE).format(giro=contacto["nombre_negocio"].split()[0], nombre=contacto["nombre_negocio"])
        preg1 = preguntas_identidad[i % len(preguntas_identidad)]
        preg2 = preguntas_identidad[(i + 5) % len(preguntas_identidad)]
        turnos = [
            {"cliente": saludo, "check_not": []},
            {"cliente": preg1, "check_not": []},
            {"cliente": preg2, "check_not": []},
            {"cliente": "Ah ok, si mandeme el catalogo", "check_not": []},
            {"cliente": random.choice(ACEPTA_WHATSAPP), "check_not": []},
            {"cliente": _gen_numero_dictado(), "check_not": []},
        ]
        scenarios.append({
            "id": f"OOS-{gid:02d}-{vid:02d}",
            "nombre": f"G{gid}: Pregunta quien habla #{i+1}",
            "contacto": contacto,
            "turnos": turnos,
            "bugs_criticos": [],
        })
    return scenarios


def gen_g_cliente_distraido(gid, start_vid, count=15):
    """Cliente distraido que habla con alguien mas."""
    distraido = [
        "Si espere... oye Juanito no toques eso!... ya digame",
        "Aja... no Maria ahorita no!... perdon que decia?",
        "Si... espere tantito... oye bajale a la musica!... ya",
        "Mande?... no hijo ahorita estoy ocupado!... disculpe",
        "Si si... oye cierra la puerta!... perdon que decia",
        "Ajam... espere que estan tocando... ya digame",
        "Si... no no ese producto va alla!... continue",
        "Perdon es que llego un cliente... que me decia?",
        "Si mande... oye pon esas cajas ahi!... ya digame",
        "Ajam... espere que se esta cayendo algo... ya listo",
        "Si este... ay se me cayo el telefono... ya estoy aqui",
        "Aha... perdon estaba checando algo... repita",
        "Si si... no hijo la tarea es tuya!... perdon digame",
        "Aja... oye ponle el precio a eso!... ya digame",
        "Si... espere un segundo... ya, continue",
    ]
    scenarios = []
    for i in range(count):
        vid = start_vid + i
        contacto = _gen_contacto(vid)
        saludo = random.choice(SALUDOS_CLIENTE).format(giro=contacto["nombre_negocio"].split()[0], nombre=contacto["nombre_negocio"])
        frase = distraido[i % len(distraido)]
        turnos = [
            {"cliente": saludo, "check_not": []},
            {"cliente": frase, "check_not": []},
            {"cliente": random.choice(CONFIRMACIONES_ENCARGADO), "check_not": []},
            {"cliente": random.choice(ACEPTA_WHATSAPP), "check_not": []},
            {"cliente": _gen_numero_dictado(), "check_not": []},
        ]
        scenarios.append({
            "id": f"OOS-{gid:02d}-{vid:02d}",
            "nombre": f"G{gid}: Cliente distraido #{i+1}",
            "contacto": contacto,
            "turnos": turnos,
            "bugs_criticos": [],
        })
    return scenarios


def gen_g_numero_partes_lento(gid, start_vid, count=15):
    """Numero dictado en multiples partes muy lento."""
    scenarios = []
    for i in range(count):
        vid = start_vid + i
        contacto = _gen_contacto(vid)
        saludo = random.choice(SALUDOS_CLIENTE).format(giro=contacto["nombre_negocio"].split()[0], nombre=contacto["nombre_negocio"])
        # Dictar en 3-4 partes
        lada = random.choice(["33", "55", "81", "22"])
        p1 = f"{random.randint(10, 99)}"
        p2 = f"{random.randint(10, 99)}"
        p3 = f"{random.randint(10, 99)}"
        p4 = f"{random.randint(10, 99)}"
        turnos = [
            {"cliente": saludo, "check_not": []},
            {"cliente": random.choice(CONFIRMACIONES_ENCARGADO), "check_not": []},
            {"cliente": random.choice(ACEPTA_WHATSAPP), "check_not": []},
            {"cliente": f"Es el {lada}...", "check_not": []},
            {"cliente": f"{p1} {p2}...", "check_not": []},
            {"cliente": f"{p3} {p4}", "check_not": []},
        ]
        scenarios.append({
            "id": f"OOS-{gid:02d}-{vid:02d}",
            "nombre": f"G{gid}: Numero en partes lento #{i+1}",
            "contacto": contacto,
            "turnos": turnos,
            "bugs_criticos": [],
        })
    return scenarios


def gen_g_corrige_numero(gid, start_vid, count=15):
    """Cliente corrige numero despues de dictarlo mal."""
    scenarios = []
    for i in range(count):
        vid = start_vid + i
        contacto = _gen_contacto(vid)
        saludo = random.choice(SALUDOS_CLIENTE).format(giro=contacto["nombre_negocio"].split()[0], nombre=contacto["nombre_negocio"])
        correcciones = [
            "No espere, me equivoque. Es el ",
            "Perdon, el numero correcto es ",
            "Ay no, ese no es. Es ",
            "No, esta mal. Anote bien: ",
            "Le di el equivocado, es el ",
        ]
        correccion = random.choice(correcciones) + _gen_numero_dictado()
        turnos = [
            {"cliente": saludo, "check_not": []},
            {"cliente": random.choice(CONFIRMACIONES_ENCARGADO), "check_not": []},
            {"cliente": random.choice(ACEPTA_WHATSAPP), "check_not": []},
            {"cliente": _gen_numero_dictado(), "check_not": []},
            {"cliente": correccion, "check_not": []},
        ]
        scenarios.append({
            "id": f"OOS-{gid:02d}-{vid:02d}",
            "nombre": f"G{gid}: Corrige numero #{i+1}",
            "contacto": contacto,
            "turnos": turnos,
            "bugs_criticos": [],
        })
    return scenarios


def gen_g_conversacion_larga(gid, start_vid, count=15):
    """Conversacion larga con muchos turnos."""
    scenarios = []
    for i in range(count):
        vid = start_vid + i
        contacto = _gen_contacto(vid)
        saludo = random.choice(SALUDOS_CLIENTE).format(giro=contacto["nombre_negocio"].split()[0], nombre=contacto["nombre_negocio"])
        turnos = [
            {"cliente": saludo, "check_not": []},
            {"cliente": random.choice(PREGUNTAS_EMPRESA), "check_not": []},
            {"cliente": random.choice(CONFIRMACIONES_ENCARGADO), "check_not": []},
            {"cliente": random.choice(PREGUNTAS_PRODUCTO), "check_not": []},
            {"cliente": random.choice(PREGUNTAS_PRECIO), "check_not": []},
            {"cliente": random.choice(PREGUNTAS_ENVIO), "check_not": []},
            {"cliente": random.choice(CLIENTE_PIDE_DESCUENTO), "check_not": []},
            {"cliente": "Bueno si convencido, mandeme el catalogo", "check_not": []},
            {"cliente": random.choice(ACEPTA_WHATSAPP), "check_not": []},
            {"cliente": _gen_numero_dictado(), "check_not": []},
            {"cliente": random.choice(DESPEDIDAS_CLIENTE), "check_not": []},
        ]
        scenarios.append({
            "id": f"OOS-{gid:02d}-{vid:02d}",
            "nombre": f"G{gid}: Conversacion larga #{i+1}",
            "contacto": contacto,
            "turnos": turnos,
            "bugs_criticos": [],
        })
    return scenarios


def gen_g_ivr_conmutador(gid, start_vid, count=15):
    """IVR o conmutador antes de llegar al humano."""
    ivr_saludos = [
        "Gracias por llamar a nuestra empresa, marque la extension o espere",
        "Bienvenido, para ventas marque 1, para compras marque 2",
        "Ferreteria central, en que departamento lo comunicamos?",
        "Buenos dias, lo transfiero en un momento",
        "Corporativo, con quien desea hablar?",
        "Un momento por favor, le transfiero la llamada",
        "Si, lo comunico con el area de compras",
        "Espere en linea por favor",
        "Enseguida le paso la llamada",
        "Le comunico, un segundo",
        "Si, aguarde un momento por favor",
        "Lo paso con el encargado, espere",
        "Marque la extension del area que necesita",
        "Conmutador, a donde lo comunico?",
        "Si, dejeme ver si esta disponible",
    ]
    scenarios = []
    for i in range(count):
        vid = start_vid + i
        contacto = _gen_contacto(vid)
        ivr = ivr_saludos[i % len(ivr_saludos)]
        turnos = [
            {"cliente": ivr, "check_not": []},
            {"cliente": "Si bueno, digame", "check_not": []},
            {"cliente": random.choice(CONFIRMACIONES_ENCARGADO), "check_not": []},
            {"cliente": random.choice(ACEPTA_WHATSAPP + ACEPTA_CORREO), "check_not": []},
            {"cliente": _gen_numero_dictado(), "check_not": []},
        ]
        scenarios.append({
            "id": f"OOS-{gid:02d}-{vid:02d}",
            "nombre": f"G{gid}: IVR/Conmutador #{i+1}",
            "contacto": contacto,
            "turnos": turnos,
            "bugs_criticos": [],
        })
    return scenarios


def gen_g_saludo_largo_contexto(gid, start_vid, count=15):
    """Cliente da mucho contexto en el saludo."""
    saludos_largos = [
        "Si bueno, mire nosotros somos una ferreteria chica aqui en el centro y pues tenemos de todo un poco",
        "Hola si, somos distribuidores de materiales de construccion desde hace 20 anos",
        "Si digame, aqui vendemos de todo, herramienta, tornilleria, plomeria, electrico",
        "Bueno si, mire somos una cadena de ferreterias con 5 sucursales",
        "Aja si, aqui es la bodega principal, tenemos otras dos tiendas",
        "Si bueno, somos el almacen central de un grupo de ferreterias",
        "Hola, mire yo soy el encargado de compras de esta zona, tenemos 3 tiendas",
        "Buenas, si nosotros estamos en el mercado de abastos, somos mayoristas",
        "Si bueno, aqui es una tlapaleria pero tambien vendemos material electrico",
        "Digame, nosotros somos una cooperativa de 10 ferreterias aqui en la zona",
        "Si, mire yo me encargo de surtir a varias tienditas de aqui de la colonia",
        "Bueno si, le comento que nosotros ya tenemos 15 anos en esto",
        "Hola, si mire nosotros somos distribuidores autorizados de Stanley",
        "Si bueno, aqui es una ferreteria industrial, manejamos cosas pesadas",
        "Digame, si nosotros somos proveedores de constructoras de la zona",
    ]
    scenarios = []
    for i in range(count):
        vid = start_vid + i
        contacto = _gen_contacto(vid)
        saludo_largo = saludos_largos[i % len(saludos_largos)]
        turnos = [
            {"cliente": saludo_largo, "check_not": []},
            {"cliente": "Si me interesa ver su catalogo", "check_not": []},
            {"cliente": random.choice(ACEPTA_WHATSAPP), "check_not": []},
            {"cliente": _gen_numero_dictado(), "check_not": []},
        ]
        scenarios.append({
            "id": f"OOS-{gid:02d}-{vid:02d}",
            "nombre": f"G{gid}: Saludo largo contexto #{i+1}",
            "contacto": contacto,
            "turnos": turnos,
            "bugs_criticos": [],
        })
    return scenarios


# ── Registrar todos los generadores ─────────────────────────────────────

GENERATORS = [
    (18, gen_g18_confuso),
    (19, gen_g19_ya_tiene_proveedor),
    (20, gen_g20_pide_descuento),
    (21, gen_g21_compara_competencia),
    (22, gen_g22_multiples_personas),
    (23, gen_g23_datos_proactivos),
    (24, gen_g24_cambia_opinion),
    (25, gen_g25_garantias),
    (26, gen_g26_frases_cortadas),
    (27, gen_g27_emails_raros),
    (28, gen_g28_pide_hablar_jefe),
    (29, gen_g29_ya_llamaron),
    (30, gen_g30_nombre_encargado),
    (31, gen_g31_no_da_datos),
    (32, gen_g32_horarios_envios),
    (33, gen_g33_monosilabico),
    (34, gen_g34_interrumpe_cambia_tema),
    (35, gen_g35_spanglish),
    (36, gen_g36_sin_autoridad),
    (37, gen_g37_multiflow),
    # Grupos extra para llegar a 1000
    (38, gen_g_precio_facturacion),
    (39, gen_g_rechazo_variado),
    (40, gen_g_callback_detallado),
    (41, gen_g_numero_incorrecto),
    (42, gen_g_wa_y_correo_rechazados),
    (43, gen_g_happy_path_variado),
    (44, gen_g_acepta_correo_directo),
    (45, gen_g_responde_agresivo),
    (46, gen_g_encargado_ocupado_largo),
    (47, gen_g_pregunta_quien_habla),
    (48, gen_g_cliente_distraido),
    (49, gen_g_numero_partes_lento),
    (50, gen_g_corrige_numero),
    (51, gen_g_conversacion_larga),
    (52, gen_g_ivr_conmutador),
    (53, gen_g_saludo_largo_contexto),
]

# Necesitamos ~67 grupos de 15 para 1000. Tenemos 36 generadores base.
# Los restantes 31 grupos se generan repitiendo generadores con seed diferente.

EXTRA_GENERATORS = [
    (54, gen_g18_confuso),
    (55, gen_g19_ya_tiene_proveedor),
    (56, gen_g20_pide_descuento),
    (57, gen_g21_compara_competencia),
    (58, gen_g22_multiples_personas),
    (59, gen_g23_datos_proactivos),
    (60, gen_g24_cambia_opinion),
    (61, gen_g25_garantias),
    (62, gen_g26_frases_cortadas),
    (63, gen_g27_emails_raros),
    (64, gen_g28_pide_hablar_jefe),
    (65, gen_g29_ya_llamaron),
    (66, gen_g30_nombre_encargado),
    (67, gen_g31_no_da_datos),
    (68, gen_g32_horarios_envios),
    (69, gen_g33_monosilabico),
    (70, gen_g34_interrumpe_cambia_tema),
    (71, gen_g35_spanglish),
    (72, gen_g36_sin_autoridad),
    (73, gen_g37_multiflow),
    (74, gen_g_precio_facturacion),
    (75, gen_g_rechazo_variado),
    (76, gen_g_callback_detallado),
    (77, gen_g_numero_incorrecto),
    (78, gen_g_wa_y_correo_rechazados),
    (79, gen_g_happy_path_variado),
    (80, gen_g_acepta_correo_directo),
    (81, gen_g_responde_agresivo),
    (82, gen_g_encargado_ocupado_largo),
    (83, gen_g_cliente_distraido),
    (84, gen_g_conversacion_larga),
]


def generate_all(target=1005):
    """Genera todos los escenarios. target ~1005 (67 grupos x 15)."""
    all_scenarios = []
    vid_counter = 1

    for gid, gen_func in GENERATORS:
        random.seed(42 + gid * 100)  # Seed unica por grupo
        scenarios = gen_func(gid, vid_counter, count=15)
        all_scenarios.extend(scenarios)
        vid_counter += 15

    for gid, gen_func in EXTRA_GENERATORS:
        random.seed(42 + gid * 100 + 5000)  # Seed diferente para variaciones
        scenarios = gen_func(gid, vid_counter, count=15)
        all_scenarios.extend(scenarios)
        vid_counter += 15

    return all_scenarios[:target]


if __name__ == "__main__":
    scenarios = generate_all()
    print(f"Escenarios generados: {len(scenarios)}")
    print(f"Grupos: {len(set(s['id'].split('-')[1] for s in scenarios))}")

    # Guardar a JSON para inspeccion
    with open("escenarios_1000.json", "w", encoding="utf-8") as f:
        json.dump(scenarios, f, ensure_ascii=False, indent=2)
    print("Guardado en escenarios_1000.json")
