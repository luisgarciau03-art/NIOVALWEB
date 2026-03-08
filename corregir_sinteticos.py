"""
Corrige los 16 bugs reales detectados en sinteticos_auditoria_50.jsonl
por la auditoria Claude Sonnet.
Genera sinteticos_v2_corregidos.jsonl para segunda ronda fine-tuning.
"""
import json

# Correcciones por numero de conversacion (1-indexed)
# Formato: {conv_num: [(role_a_buscar, texto_a_buscar_substr, nuevo_contenido), ...]}
CORRECCIONES = {

    # DESPEDIDA_PREMATURA: encargado pregunta "¿qué traes?" y Bruce se despide
    10: [
        ("assistant", "Le agradezco mucho su atencion. Que tenga muy buen dia.",
         "En NIOVAL distribuimos herramientas, cintas tapagoteras, grifería, candados e impermeabilizantes. ¿Le envío el catálogo con lista de precios por WhatsApp o correo?"),
        ("assistant", "Perfecto, le envio el catalogo en las proximas 2 horas. Le agradezco mucho su tiempo. Que tenga excelente",
         "Con gusto. Nuestro WhatsApp de NIOVAL es 662 415 1997. ¿Le envío el catálogo ahí o prefiere darnos su número directamente?"),
    ],

    # NO_DA_DATOS_RECADO: recepcionista pide datos de Bruce, Bruce se despide
    13: [
        ("assistant", "Muchas gracias, fue un gusto. Que le vaya muy bien.",
         "Claro, con mucho gusto. Mi nombre es Bruce, de NIOVAL. Nuestro WhatsApp es 662 415 1997 y nuestro correo es ventas@nioval.com. ¿Me podría dejar un WhatsApp o correo donde contactar al encargado cuando regrese?"),
    ],

    17: [
        ("assistant", "Muchas gracias, fue un gusto. Que le vaya muy bien.",
         "Claro, disculpe la confusión. Mi nombre es Bruce, de NIOVAL. Nuestro número es 662 415 1997. ¿Podría dejarme un contacto del encargado para enviarle el catálogo?"),
    ],

    # CONFUSION_FLUJO: cliente dio su WhatsApp pero Bruce responde "Perfecto, ya tengo su numero" confuso
    23: [
        ("assistant", "Perfecto, ya tengo su numero. Le envio el catalogo con lista de precios en las proximas horas. Si ti",
         "Perfecto, ya tengo anotado el WhatsApp 55 8743 2891. Le envío el catálogo de NIOVAL en breve. Muchas gracias, que tenga buen día."),
        ("assistant", "Claro, digame.",
         "Soy Bruce, de NIOVAL. Le puedo dar nuestro WhatsApp: 662 415 1997. ¿O prefiere darnos el suyo para enviarle el catálogo directamente?"),
    ],

    # PITCH_AUSENTE: Bruce pide WhatsApp sin presentarse
    24: [
        ("assistant", "Para hacerle llegar nuestro catalogo, ¿me podria dar un WhatsApp o correo electronico?",
         "Le llamo de NIOVAL, somos distribuidores de productos ferreteros: herramientas, cintas tapagoteras, grifería y más. ¿Le gustaría recibir nuestro catálogo por WhatsApp o correo?"),
    ],

    # NO_DA_DATOS_RECADO
    37: [
        ("assistant", "Muchas gracias, fue un gusto. Que le vaya muy bien.",
         "Con gusto. Mi nombre es Bruce, de NIOVAL. Nuestro WhatsApp es 662 415 1997. ¿Podría dejarme un contacto del encargado para enviarle el catálogo cuando regrese?"),
    ],

    # DESPEDIDA_PREMATURA: encargado pregunta "¿qué trae?" y Bruce se despide
    39: [
        ("assistant", "Muchas gracias, fue un gusto. Que le vaya muy bien.",
         "En NIOVAL distribuimos herramientas, cintas tapagoteras, grifería, candados e impermeabilizantes. ¿Le envío el catálogo con lista de precios por WhatsApp o correo?"),
    ],

    # IGNORA_PREGUNTA: captura correo pero ignora pregunta "¿cuál es tu nombre y de dónde llamabas?"
    40: [
        ("assistant", "Perfecto, ya tengo el correo. Le envio el catalogo con lista de precios en las proximas horas. Si ti",
         "Perfecto, ya tengo el correo. Soy Bruce, de NIOVAL, distribuidores de productos ferreteros de Guadalajara. Le envío el catálogo en las próximas horas. Muchas gracias."),
    ],

    # IGNORA_PREGUNTA: captura correo pero ignora pregunta "¿cuál es su nombre y número?"
    41: [
        ("assistant", "Excelente, quedo registrado el correo. En breve le envio toda la informacion con precios. Muchas gra",
         "Excelente. Mi nombre es Bruce, de NIOVAL. Quedo registrado el correo. En breve le enviamos toda la información con precios. Muchas gracias."),
    ],

    # DATOS_NIOVAL_INAPROPIADO: cliente pide WhatsApp de NIOVAL y Bruce se despide sin darlo
    42: [
        ("assistant", "Muchas gracias, fue un gusto. Que le vaya muy bien.",
         "Claro, nuestro WhatsApp de NIOVAL es 662 415 1997. Ahí le enviamos el catálogo completo con lista de precios. ¿Le parece bien?"),
    ],

    # CONFIRMACION_FALSA + OFERTA_POST_DESPEDIDA: conv 43 tiene despedida intermedia + catálogo falso
    43: [
        # Corregir la despedida intermedia: cuando C dice "usted es quien debe dar datos", B debe darlos
        ("assistant", "Le agradezco mucho su atencion. Que tenga muy buen dia.",
         "Claro, mi nombre es Bruce, de NIOVAL. Nuestro WhatsApp es 662 415 1997. ¿Le paso esos datos al encargado?"),
        # Corregir el último turn falso
        ("assistant", "Perfecto, le envio el catalogo en las proximas 2 horas. Le agradezco mucho su tiempo. Que tenga exce",
         "Muchas gracias. Ya dejé los datos de NIOVAL. Que tenga muy buen día."),
    ],

    # NO_DA_DATOS_RECADO
    44: [
        ("assistant", "Muchas gracias por su tiempo. Que tenga excelente dia. Hasta pronto.",
         "Con gusto. Mi nombre es Bruce, de NIOVAL. Nuestro WhatsApp es 662 415 1997 y nuestro correo ventas@nioval.com. ¿Me podría dejar un WhatsApp o correo del encargado para enviarle el catálogo?"),
    ],

    # CONFIRMACION_FALSA: "ya lo tengo anotado. Le envío el catálogo" pero no hay dato de CLIENTE capturado
    46: [
        ("assistant", "Muy bien, ya lo tengo anotado. Le envio el catalogo en un momento. Si necesita algo mas, con gusto l",
         "Muchas gracias. Ya le dejé los datos de NIOVAL. ¿Podría también darme el WhatsApp o correo del encargado para enviarle el catálogo directamente cuando regrese?"),
    ],

    # IGNORA_PREGUNTA: WhatsApp capturado pero Bruce ignora pregunta de productos
    49: [
        ("assistant", "Muy bien, ya lo tengo anotado. Le envio el catalogo en un momento. Si necesita algo mas, con gusto l",
         "Perfecto, ya tengo su WhatsApp. En NIOVAL manejamos herramientas, cintas tapagoteras, grifería, candados e impermeabilizantes. Le envío el catálogo completo ahí en breve. Muchas gracias."),
    ],

    # PITCH_REPETIDO: Bruce repite el pitch completo después de que encargado ya se identificó
    77: [
        ("assistant", "Me comunico de la marca NIOVAL para ofrecer información de nuestros productos de ferretería. ¿Le gus",
         "¡Perfecto! Le envío nuestro catálogo con lista de precios. ¿Por WhatsApp o correo electrónico?"),
    ],

    # NO_DA_DATOS_RECADO
    78: [
        ("assistant", "Muchas gracias por su tiempo. Que tenga excelente dia. Hasta pronto.",
         "Claro, con gusto. Mi nombre es Bruce, de NIOVAL. Nuestro número es 662 415 1997. ¿Me podría dar el WhatsApp o correo del encargado para enviarle el catálogo cuando regrese?"),
    ],

    # NO_DA_DATOS_RECADO: recepcionista pide datos de Bruce repetidamente, Bruce nunca los da
    5: [
        ("assistant", "Le agradezco mucho su atencion. Que tenga muy buen dia.",
         "Claro. Mi nombre es Bruce, de NIOVAL. Nuestro WhatsApp es 662 415 1997 y nuestro correo ventas@nioval.com. Ahí puede dejarnos mensaje para el encargado. Muchas gracias."),
    ],

    # OFERTA_POST_DESPEDIDA + NO_DA_DATOS_RECADO: conv 43 aún tiene despedida a media conversación
    # Corregir el turn de despedida en medio (no el final que ya fue corregido antes)
    # Después de que C dice "usted es quien debe dar los datos", B debe dar su info, no despedirse
    # Nota: la corrección anterior cambió el último turn; aquí corregimos el turn intermedio
    70: [
        ("assistant", "Muchas gracias por su tiempo. Que tenga excelente dia. Hasta pronto.",
         "Con gusto. Mi nombre es Bruce, de NIOVAL. Nuestro WhatsApp es 662 415 1997 y correo ventas@nioval.com. ¿Podría anotar esos datos para el encargado? Muchas gracias."),
    ],
}


def get_assistant_index(messages, substr):
    """Encuentra el índice del mensaje assistant que contiene substr."""
    for i, m in enumerate(messages):
        if m["role"] == "assistant" and substr in m["content"]:
            return i
    return -1


def corregir_conversacion(conv_data, correcciones):
    """Aplica correcciones a una conversación."""
    msgs = conv_data["messages"]
    for role, substr, nuevo in correcciones:
        idx = get_assistant_index(msgs, substr)
        if idx >= 0:
            print(f"  Corrigiendo turno {idx}: '{msgs[idx]['content'][:60]}...'")
            msgs[idx]["content"] = nuevo
        else:
            print(f"  AVISO: No encontrado '{substr[:50]}'")
    return conv_data


def main():
    input_file = "sinteticos_auditoria_50.jsonl"
    output_file = "sinteticos_v2_corregidos.jsonl"

    with open(input_file, "r", encoding="utf-8") as f:
        lines = f.readlines()

    print(f"Cargadas {len(lines)} conversaciones")
    print(f"Corrigiendo {len(CORRECCIONES)} conversaciones con bugs...\n")

    corrected = 0
    output_lines = []
    for i, line in enumerate(lines):
        line = line.strip()
        if not line:
            continue
        conv_num = i + 1  # 1-indexed
        conv_data = json.loads(line)

        if conv_num in CORRECCIONES:
            print(f"--- CONV {conv_num} ---")
            conv_data = corregir_conversacion(conv_data, CORRECCIONES[conv_num])
            corrected += 1

        output_lines.append(json.dumps(conv_data, ensure_ascii=False))

    with open(output_file, "w", encoding="utf-8") as f:
        f.write("\n".join(output_lines) + "\n")

    print(f"\nListo: {corrected} conversaciones corregidas")
    print(f"Output: {output_file} ({len(output_lines)} conversaciones)")


if __name__ == "__main__":
    main()
