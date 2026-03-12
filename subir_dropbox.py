import dropbox
import os

# Configuracion Dropbox con refresh token (auto-renovacion, nunca expira)
DROPBOX_APP_KEY = os.getenv('DROPBOX_APP_KEY', '')
DROPBOX_APP_SECRET = os.getenv('DROPBOX_APP_SECRET', '')
DROPBOX_REFRESH_TOKEN = os.getenv('DROPBOX_REFRESH_TOKEN', '')
# Fallback: token de acceso directo (short-lived, expira en ~4h)
DROPBOX_TOKEN = os.getenv('DROPBOX_TOKEN', '')


def _get_dropbox_client():
    """Crea cliente Dropbox con refresh token (preferido) o access token (fallback)."""
    if DROPBOX_REFRESH_TOKEN and DROPBOX_APP_KEY and DROPBOX_APP_SECRET:
        print("[DROPBOX] Usando refresh token (auto-renovacion)")
        return dropbox.Dropbox(
            app_key=DROPBOX_APP_KEY,
            app_secret=DROPBOX_APP_SECRET,
            oauth2_refresh_token=DROPBOX_REFRESH_TOKEN
        )
    if DROPBOX_TOKEN:
        print("[DROPBOX] Usando access token directo (short-lived)")
        return dropbox.Dropbox(DROPBOX_TOKEN)
    return None


def subir_pdf_a_dropbox(ruta_local, nombre_destino):
    """
    Sube un archivo PDF a la raiz de tu Dropbox.
    :param ruta_local: Ruta local del archivo PDF.
    :param nombre_destino: Nombre con el que se guardara en Dropbox (ej: 'archivo.pdf').
    :return: URL compartida del archivo subido o None si falla.
    """
    dbx = _get_dropbox_client()
    if not dbx:
        print("[WARN] Dropbox no configurado. Configura DROPBOX_REFRESH_TOKEN + APP_KEY + APP_SECRET.")
        return None
    with open(ruta_local, 'rb') as f:
        data = f.read()
    try:
        # Subir archivo a la raiz
        dbx.files_upload(data, f'/{nombre_destino}', mode=dropbox.files.WriteMode.overwrite)
        # Crear enlace compartido (o reutilizar existente)
        try:
            shared_link_metadata = dbx.sharing_create_shared_link_with_settings(f'/{nombre_destino}')
        except dropbox.exceptions.ApiError as e:
            if hasattr(e.error, 'is_shared_link_already_exists') and e.error.is_shared_link_already_exists():
                links = dbx.sharing_list_shared_links(path=f'/{nombre_destino}', direct_only=True).links
                if links:
                    return links[0].url
            raise
        return shared_link_metadata.url
    except Exception as e:
        print(f"Error subiendo a Dropbox: {e}")
        return None
