"""
Script mejorado para eliminar TODOS los emojis de agente_ventas.py
"""

import re

def eliminar_todos_emojis():
    """Elimina todos los emojis usando regex comprehensivo"""

    with open('agente_ventas.py', 'r', encoding='utf-8') as f:
        contenido = f.read()

    contenido_original = contenido

    # Patrón regex para eliminar TODOS los emojis Unicode
    emoji_pattern = re.compile(
        "["
        "\U0001F600-\U0001F64F"  # emoticons
        "\U0001F300-\U0001F5FF"  # símbolos & pictogramas
        "\U0001F680-\U0001F6FF"  # transporte & símbolos de mapa
        "\U0001F1E0-\U0001F1FF"  # banderas (iOS)
        "\U00002702-\U000027B0"
        "\U000024C2-\U0001F251"
        "\U0001F900-\U0001F9FF"  # emojis suplementarios
        "\U0001FA70-\U0001FAFF"  # símbolos extendidos
        "\U00002300-\U000023FF"  # símbolos técnicos varios
        "\U0001F000-\U0001F02F"  # piezas de Mahjong
        "\U0001F0A0-\U0001F0FF"  # cartas de juego
        "]+",
        flags=re.UNICODE
    )

    # Reemplazar todos los emojis por texto plano
    contenido = emoji_pattern.sub('[EMOJI]', contenido)

    # Contar cuántos se reemplazaron
    emojis_eliminados = contenido.count('[EMOJI]')

    # Guardar
    with open('agente_ventas.py', 'w', encoding='utf-8') as f:
        f.write(contenido)

    print(f"Limpieza completa de emojis")
    print(f"Emojis eliminados: {emojis_eliminados}")
    print(f"Tamaño antes: {len(contenido_original)} bytes")
    print(f"Tamaño despues: {len(contenido)} bytes")

if __name__ == "__main__":
    eliminar_todos_emojis()
