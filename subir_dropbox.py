<<<<<<< HEAD
import dropbox
import os

# Token de acceso de Dropbox (se recomienda usar variable de entorno en producción)
DROPBOX_TOKEN = os.getenv('DROPBOX_TOKEN', 'sl.u.AGI0Feq-cipWmLqSP55Qj3PdE7EGQnrkMS0f2YMR-r3PDRwSoNyM6f-gq0iT9Z76oZhMloe-tUQRIk8e0mpEG_NIHrrrXi914MULeeUls39CQRWNFHQWQgYSOfY1eWgw4aEE1S3mhHyuvoYRxfXPK5LM6FsNhnyZqdRHpnyOMhr_z35xTWuO0t0H14PkG9cmiSZf-L7lhuq8tK4QBk8SaS60Bagx377iN_0KknzFpvgJsvlSPemWaOKCOp5vpEbO_VY9kNpQIfcwUVs_I2S2MSsUp-5JfN23DizZNTdIo2mZhxZMsZ0josL3zbsE5IOTEIo50wyAM8HMvyBTYV79P-0CWT8l-cfVSvCMnrsth9uSCJ4l8jFZRnGhexY7dKDysVwlD4i5QvbFAh-jsqjw0As6xRKHKqEFIhSd0x0C9uF-CLH48tbr9NFD2Z4mF_bvddhuuFey1gX_5mUkihsAYGFxYiD-1UAHVixiNkS9IPmYF69023SQIEK2lbpJSP9UkFHsyQxfrOzLt0eqj4UzZ27EYtauJi24L6EgocmQ0tv1LoH8Kpf-wH6Fhh3hdOyxpI7aTs8Ycu5M6i5U6Rcasp7gJkexcXPgJusbvZVUIkzM4lIc7CTSBDd4XHnuDk0AFQw6vcv5UguqeBlqYqkQRu7M2yg66_4ixbp1ItEWP2WixyzDVuQ7pASa8aHgjYMP8_daL81omUhJc3v1oTwfkx9COSMZsS_TpGTP_7M8NEokcUo7L1X5vzJ_723Z_b1Dj5xgnEULCLR0GjilXLoj5V6I7O6MtcHqctEvCKMg4U6K3Vm47W5Gr4zin1qp1PL9VXtY5Nz_CzBQqEGUJfwVmbR9hyi4s-WkWNKG9BEXHa5_TQxiWHXFghKERMQMuLuHXtfLcblhhG8ve-4FsPlmSq1MSbGVqBjqXXXRywXdY5rApTyGvegxKAsbc7-c3k5FVDScxk6BZj8o8NLdVd-vS0MfQSpVbfp9RcYSmjY_T-8ExmcmMaJDmBE6YGiJLEdg3HKQVXppZITqVJ3rXwc1gLWc1LMtz-lhO2ZY4abIkwN_3knlM4JW_Y89Yextd')

def subir_pdf_a_dropbox(ruta_local, nombre_destino):
    """
    Sube un archivo PDF a la raíz de tu Dropbox.
    :param ruta_local: Ruta local del archivo PDF.
    :param nombre_destino: Nombre con el que se guardará en Dropbox (ej: 'archivo.pdf').
    :return: URL compartida del archivo subido o None si falla.
    """
    dbx = dropbox.Dropbox(DROPBOX_TOKEN)
    with open(ruta_local, 'rb') as f:
        data = f.read()
    try:
        # Subir archivo a la raíz
        dbx.files_upload(data, f'/{nombre_destino}', mode=dropbox.files.WriteMode.overwrite)
        # Crear enlace compartido
        shared_link_metadata = dbx.sharing_create_shared_link_with_settings(f'/{nombre_destino}')
        return shared_link_metadata.url
    except Exception as e:
        print(f"Error subiendo a Dropbox: {e}")
        return None

# Ejemplo de uso:
# url = subir_pdf_a_dropbox('/ruta/local/archivo.pdf', 'archivo.pdf')
# print('URL compartida:', url)
=======
import dropbox
import os

# Token de acceso de Dropbox (se recomienda usar variable de entorno en producción)
DROPBOX_TOKEN = os.getenv('DROPBOX_TOKEN', 'sl.u.AGI0Feq-cipWmLqSP55Qj3PdE7EGQnrkMS0f2YMR-r3PDRwSoNyM6f-gq0iT9Z76oZhMloe-tUQRIk8e0mpEG_NIHrrrXi914MULeeUls39CQRWNFHQWQgYSOfY1eWgw4aEE1S3mhHyuvoYRxfXPK5LM6FsNhnyZqdRHpnyOMhr_z35xTWuO0t0H14PkG9cmiSZf-L7lhuq8tK4QBk8SaS60Bagx377iN_0KknzFpvgJsvlSPemWaOKCOp5vpEbO_VY9kNpQIfcwUVs_I2S2MSsUp-5JfN23DizZNTdIo2mZhxZMsZ0josL3zbsE5IOTEIo50wyAM8HMvyBTYV79P-0CWT8l-cfVSvCMnrsth9uSCJ4l8jFZRnGhexY7dKDysVwlD4i5QvbFAh-jsqjw0As6xRKHKqEFIhSd0x0C9uF-CLH48tbr9NFD2Z4mF_bvddhuuFey1gX_5mUkihsAYGFxYiD-1UAHVixiNkS9IPmYF69023SQIEK2lbpJSP9UkFHsyQxfrOzLt0eqj4UzZ27EYtauJi24L6EgocmQ0tv1LoH8Kpf-wH6Fhh3hdOyxpI7aTs8Ycu5M6i5U6Rcasp7gJkexcXPgJusbvZVUIkzM4lIc7CTSBDd4XHnuDk0AFQw6vcv5UguqeBlqYqkQRu7M2yg66_4ixbp1ItEWP2WixyzDVuQ7pASa8aHgjYMP8_daL81omUhJc3v1oTwfkx9COSMZsS_TpGTP_7M8NEokcUo7L1X5vzJ_723Z_b1Dj5xgnEULCLR0GjilXLoj5V6I7O6MtcHqctEvCKMg4U6K3Vm47W5Gr4zin1qp1PL9VXtY5Nz_CzBQqEGUJfwVmbR9hyi4s-WkWNKG9BEXHa5_TQxiWHXFghKERMQMuLuHXtfLcblhhG8ve-4FsPlmSq1MSbGVqBjqXXXRywXdY5rApTyGvegxKAsbc7-c3k5FVDScxk6BZj8o8NLdVd-vS0MfQSpVbfp9RcYSmjY_T-8ExmcmMaJDmBE6YGiJLEdg3HKQVXppZITqVJ3rXwc1gLWc1LMtz-lhO2ZY4abIkwN_3knlM4JW_Y89Yextd')

def subir_pdf_a_dropbox(ruta_local, nombre_destino):
    """
    Sube un archivo PDF a la raíz de tu Dropbox.
    :param ruta_local: Ruta local del archivo PDF.
    :param nombre_destino: Nombre con el que se guardará en Dropbox (ej: 'archivo.pdf').
    :return: URL compartida del archivo subido o None si falla.
    """
    dbx = dropbox.Dropbox(DROPBOX_TOKEN)
    with open(ruta_local, 'rb') as f:
        data = f.read()
    try:
        # Subir archivo a la raíz
        dbx.files_upload(data, f'/{nombre_destino}', mode=dropbox.files.WriteMode.overwrite)
        # Crear enlace compartido
        shared_link_metadata = dbx.sharing_create_shared_link_with_settings(f'/{nombre_destino}')
        return shared_link_metadata.url
    except Exception as e:
        print(f"Error subiendo a Dropbox: {e}")
        return None

# Ejemplo de uso:
# url = subir_pdf_a_dropbox('/ruta/local/archivo.pdf', 'archivo.pdf')
# print('URL compartida:', url)
>>>>>>> 360599aadaf675d7d6f069373b22ec6f1d454087
