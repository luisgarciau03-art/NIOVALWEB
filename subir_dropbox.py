<<<<<<< HEAD
import dropbox
import os

# Token de acceso de Dropbox (se recomienda usar variable de entorno en producción)
DROPBOX_TOKEN = os.getenv('DROPBOX_TOKEN', 'sl.u.AGTtFQnOaQlO_DVPu8rTbSS0G3e8w-HiNgXocpJfZ0DmSjYDfDOEn1tdvDYzFzkoGZDTw762NtBGv3M3vP9YilYe09Vkc2b66aNSXRnYIBY4VDeHzxncTc5d7AB97YVqWa_g9Ok-sMsTFjw9tp3pQ2KCW42OTzrzs2aoc8c487maXEJXrGip0sLVs4QIh8rStGVozGmmort6KE-NSabnvyjj8fcdchjQi2S0vEYaMg31QCJHy5AwW0EiP8EZs3nWxqwh8XY9OWhcwd5ARzMwhTkKv0bRFEWE8LJ555VY9xlPVZVY2XQo_BhEARhIQ5IixA4nPq2p6T-Au65eZvBz_MHZk0l3VMV-Ne4A8DK6MKboiPmdW4foWXYDb_VidSAhwPJ8NzvU3DokLioZ_GHW2IiTRlpzNod2g_k8XvuH4k58vgZv304RuD1bbOnwYT2IcW9tavNHR3034GyO8zigqM64wNGR2OsiaTzP5l_huIdUi0fTVvgQoba3wgixHnUiBvL4N9x6Xf76199mGcu3AG1ldqNhY7YDYdYBCMFjphK3jnIPsseVh0pX3UDpVZPJz8j8ISV9lfpv2Dki3HqCU1oUmux95CKl9cI2dC-MZs6YS-KMZfG-p9cJKOcvL02fVg23Yrx1n0zqdCrAgvZNH8IMrdJ3OLEEZ_ofubT7wSNzC6rLznxHw-_cSmcqihfsrVhgQplKMQcfHIdK4gM11FBffKRdTLSp2yik6CxTkPIyzG3IJAq1sDzsLDJWwKJR32ASFRaYZGCFiuFQs5qtIaSUZxjO04vOCvXZfub5M5NnwjQpbdedR-QCoBjhEzmfxX7NIV2yU-XhH1zY4tvWUYXc9tBSBOl00ZvfwxeJf-rRSMBca-buHYVkKYSnzrLsN32yKvl2_GfnOwoW5oQaGMUno9WtUfEx7oVPetbXmSLWgFRwojJ6EXpieUdYTGT0V8qfVexpjs4ncGWgD-hWyOZlYSIaRInBu42O4N5FkuYgGaRP02UasigZo7U0ddZASV4fxGlCLL-Q8zFWCv9urFKu8j67_g91uDIHv2FDLxGRxvkZQqEPxmHSqv_jEw1HddC0zTdClbcpdkFzTdeYBF-ZIk5-itdj8tq_x-uER3yFutiZdCfXa_gbpJ68J3ytuB7_ZY2828fkmOjQvoU1Z9enzNrvxdWlODD9tnE_73LTR6L3YbuuqDccvqiVWbbG-5ccktT9j0l3gNTB63avFqN3OTvJWtLccAx3OmKpHnzP_g6WAxH5fN2xnS0fJmclv7-CDxZBZggvDOiwOvq-WYPUlv-4pT4lcPXzU5kluPXR-5H6D5AGJhfcHOTavia4Qb8AzaaoPDfQUzUblaqZrzr7vLMn1jOg5gh9tJf6xP6ngMGh2PclFj8JU2Bo_9--02jyVDGi9R2prpj5O43V5aJ0ZTPWhAjKnzy5iQW8xh7NVg')

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
DROPBOX_TOKEN = os.getenv('DROPBOX_TOKEN', 'sl.u.AGTtFQnOaQlO_DVPu8rTbSS0G3e8w-HiNgXocpJfZ0DmSjYDfDOEn1tdvDYzFzkoGZDTw762NtBGv3M3vP9YilYe09Vkc2b66aNSXRnYIBY4VDeHzxncTc5d7AB97YVqWa_g9Ok-sMsTFjw9tp3pQ2KCW42OTzrzs2aoc8c487maXEJXrGip0sLVs4QIh8rStGVozGmmort6KE-NSabnvyjj8fcdchjQi2S0vEYaMg31QCJHy5AwW0EiP8EZs3nWxqwh8XY9OWhcwd5ARzMwhTkKv0bRFEWE8LJ555VY9xlPVZVY2XQo_BhEARhIQ5IixA4nPq2p6T-Au65eZvBz_MHZk0l3VMV-Ne4A8DK6MKboiPmdW4foWXYDb_VidSAhwPJ8NzvU3DokLioZ_GHW2IiTRlpzNod2g_k8XvuH4k58vgZv304RuD1bbOnwYT2IcW9tavNHR3034GyO8zigqM64wNGR2OsiaTzP5l_huIdUi0fTVvgQoba3wgixHnUiBvL4N9x6Xf76199mGcu3AG1ldqNhY7YDYdYBCMFjphK3jnIPsseVh0pX3UDpVZPJz8j8ISV9lfpv2Dki3HqCU1oUmux95CKl9cI2dC-MZs6YS-KMZfG-p9cJKOcvL02fVg23Yrx1n0zqdCrAgvZNH8IMrdJ3OLEEZ_ofubT7wSNzC6rLznxHw-_cSmcqihfsrVhgQplKMQcfHIdK4gM11FBffKRdTLSp2yik6CxTkPIyzG3IJAq1sDzsLDJWwKJR32ASFRaYZGCFiuFQs5qtIaSUZxjO04vOCvXZfub5M5NnwjQpbdedR-QCoBjhEzmfxX7NIV2yU-XhH1zY4tvWUYXc9tBSBOl00ZvfwxeJf-rRSMBca-buHYVkKYSnzrLsN32yKvl2_GfnOwoW5oQaGMUno9WtUfEx7oVPetbXmSLWgFRwojJ6EXpieUdYTGT0V8qfVexpjs4ncGWgD-hWyOZlYSIaRInBu42O4N5FkuYgGaRP02UasigZo7U0ddZASV4fxGlCLL-Q8zFWCv9urFKu8j67_g91uDIHv2FDLxGRxvkZQqEPxmHSqv_jEw1HddC0zTdClbcpdkFzTdeYBF-ZIk5-itdj8tq_x-uER3yFutiZdCfXa_gbpJ68J3ytuB7_ZY2828fkmOjQvoU1Z9enzNrvxdWlODD9tnE_73LTR6L3YbuuqDccvqiVWbbG-5ccktT9j0l3gNTB63avFqN3OTvJWtLccAx3OmKpHnzP_g6WAxH5fN2xnS0fJmclv7-CDxZBZggvDOiwOvq-WYPUlv-4pT4lcPXzU5kluPXR-5H6D5AGJhfcHOTavia4Qb8AzaaoPDfQUzUblaqZrzr7vLMn1jOg5gh9tJf6xP6ngMGh2PclFj8JU2Bo_9--02jyVDGi9R2prpj5O43V5aJ0ZTPWhAjKnzy5iQW8xh7NVg')

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
