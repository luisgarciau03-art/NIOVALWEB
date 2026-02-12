"""
Obtener refresh token de Dropbox para uso permanente en Railway.

Pasos:
1. Ve a https://www.dropbox.com/developers/apps
2. Crea una app (o usa la existente) con permisos: files.content.write, sharing.write
3. Copia el App Key y App Secret
4. Ejecuta este script y sigue las instrucciones
5. El refresh token NUNCA expira (a menos que lo revoques manualmente)

Una vez obtenido, configura en Railway:
  railway variables set DROPBOX_APP_KEY=<tu_app_key>
  railway variables set DROPBOX_APP_SECRET=<tu_app_secret>
  railway variables set DROPBOX_REFRESH_TOKEN=<el_refresh_token>
"""
import os
import requests

def obtener_refresh_token():
    print("=" * 60)
    print("  OBTENER REFRESH TOKEN DE DROPBOX")
    print("=" * 60)
    print()

    app_key = input("App Key de tu app Dropbox: ").strip()
    app_secret = input("App Secret de tu app Dropbox: ").strip()

    if not app_key or not app_secret:
        print("Error: App Key y App Secret son obligatorios.")
        return

    # Paso 1: Generar URL de autorizacion
    auth_url = (
        f"https://www.dropbox.com/oauth2/authorize"
        f"?client_id={app_key}"
        f"&response_type=code"
        f"&token_access_type=offline"
    )

    print()
    print("1. Abre esta URL en tu navegador:")
    print(f"   {auth_url}")
    print()
    print("2. Autoriza la app y copia el codigo que te da Dropbox")
    print()

    auth_code = input("Pega el codigo de autorizacion aqui: ").strip()

    if not auth_code:
        print("Error: Codigo de autorizacion vacio.")
        return

    # Paso 2: Intercambiar codigo por refresh token
    response = requests.post(
        "https://api.dropboxapi.com/oauth2/token",
        data={
            "code": auth_code,
            "grant_type": "authorization_code",
            "client_id": app_key,
            "client_secret": app_secret,
        }
    )

    if response.status_code != 200:
        print(f"Error: {response.status_code} - {response.text}")
        return

    data = response.json()
    refresh_token = data.get("refresh_token")
    access_token = data.get("access_token")

    if not refresh_token:
        print("Error: No se obtuvo refresh token. Verifica que token_access_type=offline.")
        print(f"Respuesta: {data}")
        return

    print()
    print("=" * 60)
    print("  REFRESH TOKEN OBTENIDO EXITOSAMENTE")
    print("=" * 60)
    print()
    print(f"DROPBOX_APP_KEY     = {app_key}")
    print(f"DROPBOX_APP_SECRET  = {app_secret}")
    print(f"DROPBOX_REFRESH_TOKEN = {refresh_token}")
    print()
    print("Para configurar en Railway, ejecuta estos 3 comandos:")
    print(f'  railway variables set DROPBOX_APP_KEY={app_key}')
    print(f'  railway variables set DROPBOX_APP_SECRET={app_secret}')
    print(f'  railway variables set DROPBOX_REFRESH_TOKEN={refresh_token}')
    print()
    print("El refresh token NUNCA expira. Ya no necesitas actualizar tokens diariamente.")


if __name__ == "__main__":
    obtener_refresh_token()
