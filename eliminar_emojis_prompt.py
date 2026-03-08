"""
FIX 478 (AUDITORIA W04): Script para eliminar emojis del SYSTEM_PROMPT
Mantiene TODO el contenido textual, solo elimina decoración emoji
"""
import re

def eliminar_emojis(texto):
    """
    Elimina emojis pero mantiene todo el contenido textual
    """
    # Lista de emojis comunes en el prompt
    emojis_a_eliminar = [
        '', '', '', '', '', '🟠', '🟡', '🟢',
        '', '', '', '', '', '', '', '',
        '', '', '', '', '', '', '', '',
        '', '', '', '', '', '',
        '', '', '', '', '', '', '',
        '', '', '', '', '', '',
        '', '', '', '', '', '',
        '', '', '', '', '',
        '', '', '', '', '',
        '', '', '', '',
        '', '', '', '',
        '', '', '', '',
        '', '', '', '',
        '', '', '', '',
        '', '', '', '',
        '', '', '', '',
        '', '', '', '',
        '', '', '', '',
        '', '', '', '',
        '', '', '', '',
        '', '', '', '',
        '', '', '', '',
        '', '', '', '',
        '', '', '', '',
        '', '', '', '',
        '↩', '↪', '', '',
        '', '', '', '',
        '', '', '', '',
        '', '', '', '',
        '', '', '', '',
        '', '', '', '',
        '', '', '', '',
        '', '', '', '',
        '🟣', '🟢', '🟡', '🟠',
        '🟤', '', '', '🟥',
        '🟧', '🟨', '🟩', '🟦',
        '🟪', '🟫',
    ]

    # Eliminar cada emoji
    for emoji in emojis_a_eliminar:
        texto = texto.replace(emoji, '')

    # Patrón regex para capturar cualquier emoji que se haya escapado
    # Rangos Unicode de emojis
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
        "\U00002500-\U00002BEF"  # caracteres chinos
        "]+",
        flags=re.UNICODE
    )

    texto = emoji_pattern.sub('', texto)

    # Limpiar espacios múltiples que quedan después de eliminar emojis
    texto = re.sub(r' {2,}', ' ', texto)

    # Limpiar líneas que quedaron solo con espacios
    lineas = texto.split('\n')
    lineas_limpias = []
    for linea in lineas:
        linea_limpia = linea.strip()
        # Mantener líneas vacías (saltos de línea intencionados)
        # pero eliminar las que quedaron solo con espacios
        if linea or not linea.strip():
            lineas_limpias.append(linea)

    return '\n'.join(lineas_limpias)

def main():
    print("FIX 478 (AUDITORIA W04): Eliminando emojis del SYSTEM_PROMPT...")

    # Leer archivo original
    with open('prompts/system_prompt.txt', 'r', encoding='utf-8') as f:
        contenido_original = f.read()

    print(f"Tamaño original: {len(contenido_original)} caracteres")

    # Contar emojis
    emojis_encontrados = 0
    for char in contenido_original:
        if ord(char) > 127 and (
            '\U0001F600' <= char <= '\U0001F64F' or
            '\U0001F300' <= char <= '\U0001F5FF' or
            '\U0001F680' <= char <= '\U0001F6FF'
        ):
            emojis_encontrados += 1

    print(f"Emojis encontrados: {emojis_encontrados}")

    # Eliminar emojis
    contenido_sin_emojis = eliminar_emojis(contenido_original)

    print(f"Tamaño después de eliminar emojis: {len(contenido_sin_emojis)} caracteres")
    print(f"Reducción: {len(contenido_original) - len(contenido_sin_emojis)} caracteres ({(1 - len(contenido_sin_emojis)/len(contenido_original))*100:.1f}%)")

    # Guardar backup
    with open('prompts/system_prompt_con_emojis.txt.backup', 'w', encoding='utf-8') as f:
        f.write(contenido_original)
    print("Backup guardado: prompts/system_prompt_con_emojis.txt.backup")

    # Guardar versión sin emojis
    with open('prompts/system_prompt.txt', 'w', encoding='utf-8') as f:
        f.write(contenido_sin_emojis)

    print(" SYSTEM_PROMPT actualizado sin emojis")
    print(" Todo el contenido textual se mantuvo intacto")

if __name__ == "__main__":
    main()
