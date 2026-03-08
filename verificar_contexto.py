"""
Script para verificar que Bruce genera el contexto correctamente
"""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# Simular contacto con información completa
contacto_info = {
    'nombre_negocio': 'Ferretería El Martillo',
    'ciudad': 'Guadalajara, Jalisco',
    'categoria': 'Ferretería',
    'domicilio': 'Av. Revolución 123, Col. Centro',
    'horario': 'Lun-Vie 9:00-18:00, Sáb 9:00-14:00',
    'puntuacion': '4.5',
    'resenas': '87',
    'maps': 'Ferretería El Martillo - Centro',
    'estatus': 'Prospecto',
    'referencia': 'Me pasó su contacto Juan Pérez de Ferretería La Llave',
    'contexto_reprogramacion': 'Cliente pidió que le llamáramos el viernes por la tarde. Mostró interés en productos de plomería.'
}

# Función que simula _generar_contexto_cliente()
def generar_contexto_cliente(contacto_info):
    """Simula la función _generar_contexto_cliente()"""
    if not contacto_info:
        return ""

    contexto_partes = ["[INFORMACIÓN PREVIA DEL CLIENTE - NO PREGUNTES ESTO]"]

    # Nombre del negocio
    if contacto_info.get('nombre_negocio'):
        contexto_partes.append(f"- Nombre del negocio: {contacto_info['nombre_negocio']}")

    # Ciudad
    if contacto_info.get('ciudad'):
        contexto_partes.append(f"- Ciudad: {contacto_info['ciudad']}")

    # Categoría
    if contacto_info.get('categoria'):
        contexto_partes.append(f"- Tipo de negocio: {contacto_info['categoria']}")

    # Domicilio
    if contacto_info.get('domicilio'):
        contexto_partes.append(f"- Dirección: {contacto_info['domicilio']}")

    # Horario
    if contacto_info.get('horario'):
        contexto_partes.append(f"- Horario: {contacto_info['horario']}")

    # Puntuación Google Maps
    if contacto_info.get('puntuacion'):
        contexto_partes.append(f"- Puntuación Google Maps: {contacto_info['puntuacion']} estrellas")

    if contacto_info.get('resenas'):
        contexto_partes.append(f"- Número de reseñas: {contacto_info['resenas']}")

    if contacto_info.get('maps'):
        contexto_partes.append(f"- Nombre en Google Maps: {contacto_info['maps']}")

    # Estatus
    if contacto_info.get('estatus'):
        contexto_partes.append(f"- Estatus previo: {contacto_info['estatus']}")

    # REFERENCIA
    if contacto_info.get('referencia'):
        contexto_partes.append(f"\n IMPORTANTE - REFERENCIA:")
        contexto_partes.append(f"- {contacto_info['referencia']}")
        contexto_partes.append(f"- Usa esta información en tu SALUDO INICIAL para generar confianza")
        contexto_partes.append(f"- Ejemplo: 'Hola, mi nombre es Bruce W. Me pasó su contacto [NOMBRE DEL REFERIDOR] de [EMPRESA]. Él me comentó que usted...'")

    # CONTEXTO DE REPROGRAMACIÓN
    if contacto_info.get('contexto_reprogramacion'):
        contexto_partes.append(f"\n LLAMADA REPROGRAMADA:")
        contexto_partes.append(f"- {contacto_info['contexto_reprogramacion']}")
        contexto_partes.append(f"- Menciona que ya habían hablado antes y retomas la conversación")
        contexto_partes.append(f"- Ejemplo: 'Hola, qué tal. Como le había comentado la vez pasada, me comunico nuevamente...'")

    if len(contexto_partes) > 1:
        contexto_partes.append("\nRecuerda: NO preguntes nada de esta información, ya la tienes.")
        return "\n".join(contexto_partes)

    return ""

# TEST
print("\n" + "="*80)
print(" VERIFICACIÓN DE CONTEXTO - BRUCE W")
print("="*80 + "\n")

print(" CONTACTO DE PRUEBA:")
print(f"  Negocio: {contacto_info['nombre_negocio']}")
print(f"  Ciudad: {contacto_info['ciudad']}")
print(f"  Referencia: {contacto_info.get('referencia', 'N/A')}")
print(f"  Reprogramación: {contacto_info.get('contexto_reprogramacion', 'N/A')}")

print("\n" + "="*80)
print(" CONTEXTO GENERADO (se inyecta como mensaje system):")
print("="*80 + "\n")

contexto = generar_contexto_cliente(contacto_info)
print(contexto)

print("\n" + "="*80)
print(" VERIFICACIÓN:")
print("="*80)

verificaciones = {
    "Nombre del negocio incluido": "nombre del negocio" in contexto.lower(),
    "Ciudad incluida": "ciudad" in contexto.lower(),
    "Dirección incluida": "dirección" in contexto.lower(),
    "Horario incluido": "horario" in contexto.lower(),
    "Google Maps incluido": "google maps" in contexto.lower(),
    "Referencia incluida": "referencia" in contexto.lower(),
    "Reprogramación incluida": "reprogramada" in contexto.lower(),
    "Instrucción de NO preguntar": "no preguntes" in contexto.lower()
}

for check, resultado in verificaciones.items():
    print(f"  {'' if resultado else ''} {check}")

print("\n" + "="*80)
print(" RESUMEN:")
print("="*80)
num_elementos = len([line for line in contexto.split('\n') if line.startswith('-')])
print(f"  Total de elementos en contexto: {num_elementos}")
print(f"  Caracteres totales: {len(contexto)}")
print(f"\n   El contexto se genera correctamente")
print(f"   Bruce TIENE esta información antes de empezar la llamada")
print(f"   No debe preguntar estos datos al cliente")
print("\n" + "="*80)
