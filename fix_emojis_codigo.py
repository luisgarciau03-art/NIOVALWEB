"""
Script para eliminar emojis de prints en agente_ventas.py
Esto soluciona errores UnicodeEncodeError en Windows
"""

import re

def eliminar_emojis_prints():
    """Elimina emojis de prints en agente_ventas.py"""

    with open('agente_ventas.py', 'r', encoding='utf-8') as f:
        contenido = f.read()

    # Patrón para encontrar emojis comunes
    emojis = {
        '🔍': '[DEBUG]',
        '⏸️': '[PAUSE]',
        '🔁': '[REPEAT]',
        '🔧': '[FIX]',
        '⚠️': '[WARN]',
        '✅': '[OK]',
        '❌': '[ERROR]',
        '📱': '[PHONE]',
        '📧': '[EMAIL]',
        '🚀': '[ROCKET]',
        '🔧': '[WRENCH]',
    }

    # Reemplazar cada emoji
    for emoji, reemplazo in emojis.items():
        contenido = contenido.replace(emoji, reemplazo)

    # Guardar
    with open('agente_ventas.py', 'w', encoding='utf-8') as f:
        f.write(contenido)

    print("Emojis eliminados de agente_ventas.py")
    print(f"Total reemplazos: {sum(contenido.count(r) for r in emojis.values())}")

if __name__ == "__main__":
    eliminar_emojis_prints()
