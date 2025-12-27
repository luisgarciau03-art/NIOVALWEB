<<<<<<< HEAD
import dropbox
import os

# Token de acceso de Dropbox (se recomienda usar variable de entorno en producción)
DROPBOX_TOKEN = os.getenv('DROPBOX_TOKEN', 'sl.u.AGMy4T_VQJBNA7oYkCpHeAxCqRguDxkmd6riNyogavTzp4FSLyMdF45plw1kO7_4zFPC_L8kCK4h_i42IQ20Ppa8rbi6Dhu--eyAnc6IC2mzWJQkZX3klCcUCPAWDcWLi_QaQ-Fq5iYRiRBDQgbU5T_MYSmzkDR4Z1QWSnieCS7wqOooAdd4PksluKhdDrEUtP6OEG2bb2KRE_08NWTEPVcjk1JMQ0ZpYCZYesdRrbS1WQFFdnuu7PX2gdYJ_EUftXqVGSPQHPxndPL6xnaVvY9fpr1V4Cf_80gETsMBwbDvZv6N7IbYfZrZtSP8itjqBAzOSR-iAWdWZFDC16WXUsBSFT3XZhLhX3rynhVI1ADPB8WLu_mPReCSozu6LyPHpXf-zY9pFS0O3nMo2u_s-sTRYaIAkOExBUu1DizaxPS1FOjrGrX0bfTFHTtwPrgQ19rg_Ri6yImwIxBpBMYm2rUMEJJ32Lm5WzZdwR7vEc8_w-s4pafB5WzPd0WPAppnYs5aGaqsHlS7STCT9S0uDmqDqI8t9QYZ32r5yeWfBtmlA5u-e8cxIpI42koIF7nbnZx_NAc7f_1gip2JoUZoQsO_TYINhTmQqdEDTPA7TfbBmwTT1Ruft0MS467vcb4inuFU9SQd2_LkpVOFaAve3dXnie6j-aI5q-sLy49TeBQqIaMNbSeUcx5Si3B-h-owWkr8gktBdpiA09U7hE4S7KmKvTYnIqzc8tMG7gtAVg4YamvuZLbS48nxLiaM135I3p_UFcQRiOaFos1n8uMDFkRuDtB9Ti6PcVLXeVL2GAm_0AGRf0ypNdb4NGzaoa8TLHV-AdZONVxtlvdhYcIGhLijYG_iKfmwwAZw-copL94Jhszew-rXh0N79wFCWp56HlIrOiCBoJ5BbjmhmjEYiOdRirgQDgSN5rvokTHpvh6usCEmOfoMV-D_J-E4WICEXENPemJ6yqZdCehYo8wu4DvqNwqqt2Fs14W7SeAhGg5ELQAgNTj1X-U7o-d5cY7k3NOHlhGc34oRHzjgkWfnb2YzyqdRMRbb5JsntLSwYrgn7GTiKfkP5YyXWEmWgQdpBvv0UrOXS0wLjFzk5NVEPoO0vo7B_-PCDSPgsLqAzUx0sdSADax3iuIl8q54LJzp3jcQXW8Uwrw3U_tEou3MyQp7OApQs9SyvKhYuyjGKk6cIkye2ZU7bX1-hZ9DsyW618WGnE4DXjDeTivVZnmUJgjN_qG3SGLqhXyMKRrAh8ddedRSqZYtgwp01HYInVG6IrHy62bLX7xiULJOqJu52elngeRHGNYdpQAaKCBJfTk6neaK_EAQ5Hh-pww19U_MEXQS2PXVYiGHQcDCPEty5626pPO5O-4DvW7psGcRRKRiLiJVxEiUHQnOuU4tcH0gUUrwqUwntW75jP0nkKaOiE7EfvEhs1umPV5v7NHlrSRVbg')

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
DROPBOX_TOKEN = os.getenv('DROPBOX_TOKEN', 'sl.u.AGMy4T_VQJBNA7oYkCpHeAxCqRguDxkmd6riNyogavTzp4FSLyMdF45plw1kO7_4zFPC_L8kCK4h_i42IQ20Ppa8rbi6Dhu--eyAnc6IC2mzWJQkZX3klCcUCPAWDcWLi_QaQ-Fq5iYRiRBDQgbU5T_MYSmzkDR4Z1QWSnieCS7wqOooAdd4PksluKhdDrEUtP6OEG2bb2KRE_08NWTEPVcjk1JMQ0ZpYCZYesdRrbS1WQFFdnuu7PX2gdYJ_EUftXqVGSPQHPxndPL6xnaVvY9fpr1V4Cf_80gETsMBwbDvZv6N7IbYfZrZtSP8itjqBAzOSR-iAWdWZFDC16WXUsBSFT3XZhLhX3rynhVI1ADPB8WLu_mPReCSozu6LyPHpXf-zY9pFS0O3nMo2u_s-sTRYaIAkOExBUu1DizaxPS1FOjrGrX0bfTFHTtwPrgQ19rg_Ri6yImwIxBpBMYm2rUMEJJ32Lm5WzZdwR7vEc8_w-s4pafB5WzPd0WPAppnYs5aGaqsHlS7STCT9S0uDmqDqI8t9QYZ32r5yeWfBtmlA5u-e8cxIpI42koIF7nbnZx_NAc7f_1gip2JoUZoQsO_TYINhTmQqdEDTPA7TfbBmwTT1Ruft0MS467vcb4inuFU9SQd2_LkpVOFaAve3dXnie6j-aI5q-sLy49TeBQqIaMNbSeUcx5Si3B-h-owWkr8gktBdpiA09U7hE4S7KmKvTYnIqzc8tMG7gtAVg4YamvuZLbS48nxLiaM135I3p_UFcQRiOaFos1n8uMDFkRuDtB9Ti6PcVLXeVL2GAm_0AGRf0ypNdb4NGzaoa8TLHV-AdZONVxtlvdhYcIGhLijYG_iKfmwwAZw-copL94Jhszew-rXh0N79wFCWp56HlIrOiCBoJ5BbjmhmjEYiOdRirgQDgSN5rvokTHpvh6usCEmOfoMV-D_J-E4WICEXENPemJ6yqZdCehYo8wu4DvqNwqqt2Fs14W7SeAhGg5ELQAgNTj1X-U7o-d5cY7k3NOHlhGc34oRHzjgkWfnb2YzyqdRMRbb5JsntLSwYrgn7GTiKfkP5YyXWEmWgQdpBvv0UrOXS0wLjFzk5NVEPoO0vo7B_-PCDSPgsLqAzUx0sdSADax3iuIl8q54LJzp3jcQXW8Uwrw3U_tEou3MyQp7OApQs9SyvKhYuyjGKk6cIkye2ZU7bX1-hZ9DsyW618WGnE4DXjDeTivVZnmUJgjN_qG3SGLqhXyMKRrAh8ddedRSqZYtgwp01HYInVG6IrHy62bLX7xiULJOqJu52elngeRHGNYdpQAaKCBJfTk6neaK_EAQ5Hh-pww19U_MEXQS2PXVYiGHQcDCPEty5626pPO5O-4DvW7psGcRRKRiLiJVxEiUHQnOuU4tcH0gUUrwqUwntW75jP0nkKaOiE7EfvEhs1umPV5v7NHlrSRVbg')

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
