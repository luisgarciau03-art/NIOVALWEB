"""
Detector automático de churn NIOVAL.
Señales detectadas:
  1. Cliente sin pedido en 45+ días (ciclo normal mensual)
  2. Último pedido 30%+ menor que promedio de los 3 anteriores
"""
import os
import json
import requests
from datetime import datetime, timedelta
from collections import defaultdict

import gspread
from google.oauth2.service_account import Credentials

SPREADSHEET_ID  = "1Dlpm6swrNSPnt9L5tQhoi2OMln0bb8bqqgeLACNos98"
SHEET_NAME      = "Ventas"
TELEGRAM_TOKEN  = os.environ.get("TELEGRAM_TOKEN",  "8456512277:AAGmEedqxsa5L6h88tPnLKoA9LuXtjFmexc")
TELEGRAM_CHAT   = os.environ.get("TELEGRAM_CHAT_ID", "5838212022")
DIAS_INACTIVO   = 45
CAIDA_UMBRAL    = 0.30   # 30% de caída vs promedio


def _sheets_client():
    b64 = os.environ.get("SHEETS_SERVICE_ACCOUNT_B64")
    if b64:
        import base64, tempfile
        decoded = base64.b64decode(b64)
        tmp = tempfile.NamedTemporaryFile(mode='wb', suffix='.json', delete=False)
        tmp.write(decoded); tmp.close()
        creds_path = tmp.name
    else:
        creds_path = "niovalclientes-a38cae49d183.json"
    scopes = ["https://www.googleapis.com/auth/spreadsheets.readonly"]
    creds = Credentials.from_service_account_file(creds_path, scopes=scopes)
    return gspread.authorize(creds)


def leer_pedidos():
    gc = _sheets_client()
    ws = gc.open_by_key(SPREADSHEET_ID).worksheet(SHEET_NAME)
    rows = ws.get_all_values()
    pedidos = []
    for row in rows[1:]:   # skip header
        if len(row) < 8:
            continue
        fecha_str = row[0].strip()
        nombre    = row[1].strip()
        monto_str = row[7].strip().replace(',', '').replace('$', '').replace(' ', '')
        if not fecha_str or not nombre or not monto_str:
            continue
        try:
            fecha = datetime.strptime(fecha_str, "%d/%m/%Y")
        except ValueError:
            continue
        try:
            monto = float(monto_str)
        except ValueError:
            continue
        pedidos.append({'nombre': nombre, 'fecha': fecha, 'monto': monto})
    return pedidos


def analizar_churn(pedidos):
    hoy = datetime.now()
    por_cliente = defaultdict(list)
    for p in pedidos:
        por_cliente[p['nombre']].append(p)

    alertas = []
    for nombre, historial in por_cliente.items():
        historial.sort(key=lambda x: x['fecha'])
        ultimo = historial[-1]
        dias_inactivo = (hoy - ultimo['fecha']).days

        # Señal 1: sin pedido en 45+ días
        if dias_inactivo >= DIAS_INACTIVO:
            alertas.append({
                'nombre': nombre,
                'señal': 1,
                'dias': dias_inactivo,
                'ultimo_pedido': ultimo['fecha'].strftime('%d/%m/%Y'),
                'ultimo_monto': ultimo['monto'],
                'mensaje': f"Sin pedido hace *{dias_inactivo} días* (último: {ultimo['fecha'].strftime('%d/%m/%Y')} · ${ultimo['monto']:,.0f})"
            })
            continue  # no duplicar con señal 2

        # Señal 2: caída de 30%+ vs promedio de 3 anteriores
        if len(historial) >= 4:
            prev_3 = [h['monto'] for h in historial[-4:-1]]
            promedio = sum(prev_3) / 3
            if promedio > 0 and ultimo['monto'] < promedio * (1 - CAIDA_UMBRAL):
                caida_pct = int((1 - ultimo['monto'] / promedio) * 100)
                alertas.append({
                    'nombre': nombre,
                    'señal': 2,
                    'dias': dias_inactivo,
                    'ultimo_pedido': ultimo['fecha'].strftime('%d/%m/%Y'),
                    'ultimo_monto': ultimo['monto'],
                    'promedio': promedio,
                    'caida_pct': caida_pct,
                    'mensaje': f"Último pedido *{caida_pct}% menor* que su promedio (${ultimo['monto']:,.0f} vs ${promedio:,.0f} promedio)"
                })

    return alertas


def enviar_alertas_telegram(alertas):
    if not alertas:
        texto = "✅ *Análisis de Churn NIOVAL*\n\nNo se detectaron clientes en riesgo hoy."
        requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
            json={"chat_id": TELEGRAM_CHAT, "text": texto, "parse_mode": "Markdown"},
            timeout=10
        )
        return

    iconos = {1: "🔴", 2: "🟡"}
    señales = {1: "Sin pedido 45+ días", 2: "Caída de pedido 30%+"}

    texto = f"⚠️ *Alerta Churn NIOVAL — {datetime.now().strftime('%d/%m/%Y')}*\n"
    texto += f"_{len(alertas)} cliente(s) en riesgo_\n\n"

    for a in alertas:
        icono = iconos.get(a['señal'], '🔴')
        señal = señales.get(a['señal'], '')
        wa_msg = (f"Hola {a['nombre'].split()[0]}, soy de NIOVAL. "
                  f"Vi que no hemos trabajado juntos en las %C3%BAltimas semanas. "
                  f"%C2%BFTodo bien por all%C3%A1%3F Tenemos novedades que te pueden interesar.")
        texto += (
            f"{icono} *{a['nombre']}*\n"
            f"   Señal: {señal}\n"
            f"   {a['mensaje']}\n"
            f"   [📲 Enviar reactivación por WhatsApp](https://api.whatsapp.com/send?phone=52XXXXXXXXXX&text={wa_msg})\n\n"
        )

    texto += "_Script de reactivación sugerido en el manual de churn._"

    requests.post(
        f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
        json={"chat_id": TELEGRAM_CHAT, "text": texto, "parse_mode": "Markdown",
              "disable_web_page_preview": True},
        timeout=10
    )


def run():
    print("[CHURN] Leyendo pedidos...")
    pedidos = leer_pedidos()
    print(f"[CHURN] {len(pedidos)} pedidos leídos de {len(set(p['nombre'] for p in pedidos))} clientes")
    alertas = analizar_churn(pedidos)
    print(f"[CHURN] {len(alertas)} alertas detectadas")
    enviar_alertas_telegram(alertas)
    print("[CHURN] Alertas enviadas a Telegram")
    return alertas


if __name__ == "__main__":
    run()
