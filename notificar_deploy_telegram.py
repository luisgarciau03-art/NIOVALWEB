#!/usr/bin/env python3
"""
Script para notificar por Telegram cuando el deploy en Railway termine.
Uso: python notificar_deploy_telegram.py "Mensaje personalizado"
"""

import sys
import os
import requests

# Fix encoding for Windows console
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# Configuración de bots de Telegram
TELEGRAM_BOTS = [
    {
        "token": "8537624347:AAHDIe60mb2TkdDk4vqlcS2tpakTB_5D4qE",
        "chat_id": "7314842427",
        "nombre": "Bot 1"
    },
    {
        "token": "8524460310:AAFAwph27rSagooKTNSGXauBycpDpCjhKjI",
        "chat_id": "5838212022",
        "nombre": "Bot 2"
    }
]


def enviar_notificacion(mensaje: str):
    """Envía notificación a todos los bots configurados."""
    resultados = []

    for bot in TELEGRAM_BOTS:
        try:
            url = f"https://api.telegram.org/bot{bot['token']}/sendMessage"
            data = {
                "chat_id": bot['chat_id'],
                "text": mensaje,
                "parse_mode": "HTML"
            }

            response = requests.post(url, data=data, timeout=10)

            if response.status_code == 200:
                print(f" {bot['nombre']}: Notificación enviada exitosamente")
                resultados.append(True)
            else:
                print(f" {bot['nombre']}: Error {response.status_code} - {response.text}")
                resultados.append(False)

        except Exception as e:
            print(f" {bot['nombre']}: Excepción - {e}")
            resultados.append(False)

    return all(resultados)


def main():
    # Mensaje por defecto o personalizado
    if len(sys.argv) > 1:
        mensaje = " ".join(sys.argv[1:])
    else:
        mensaje = " <b>Deploy completado</b>\n\n Bruce Agent actualizado en Railway"

    print(f"\n Enviando notificación a Telegram...")
    print(f"   Mensaje: {mensaje[:100]}...")

    exito = enviar_notificacion(mensaje)

    if exito:
        print("\n Todas las notificaciones enviadas correctamente")
        return 0
    else:
        print("\n Algunas notificaciones fallaron")
        return 1


if __name__ == "__main__":
    sys.exit(main())
