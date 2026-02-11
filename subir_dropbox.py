<<<<<<< HEAD
import dropbox
import os

# Token de acceso de Dropbox (se recomienda usar variable de entorno en producción)
DROPBOX_TOKEN = os.getenv('DROPBOX_TOKEN', 'sl.u.AGSFrLuxgMcJsCdGM_rPI6yL3pfJfsznvPJcghL8jy0LRH5rLDViWkVLZUOtOeo9OCotguEWI2VsDlNXa4Tzu9ibzH4hlM-oZikFPK8c8pLFF2NtmExo9FvT3oYHe4WG8R8W47qqpqHW2GOwCle-CjhllLKLY7UR_qXrTBpeEKCf8kaZy7JJ0Qvx3Cn0POk71dlPcBXm6QDS6PrzmD01V1QLSS4FR5LqPDH07wb-cgDJleozDciolrnAg6pIpYe5KLvtk86mZIBuJgfvHwQ9pYARDNqWjodJ49OAMVL90Vdp_hA-XV8jykTJ5y28rH5bOiBY5o7WflQHq5CxPNVfesa19yBrtAc0IqfLEb2TuyoElhiMlrlnu5llvNBKVe5xx7CoU9Rp4PO-X3AwPPLTG384eTzXRFzqNwARTcMZjy4WM9TAytGTlyHWOUcCuL2NPj_yy1VUUwdMRenN_3I9Ei9BVXZpbRxnJIzk3J0yRFNixqNT0paz1eUOwbp5pEs93FITLCplQ5FSLm0xDhdC1W-2FGaVAA55Y8rshwJa3P0ee6at9UpyUDga1aRnbfUcrLkvULVy0VvcV0t_ljgZutlORuBMgyK5IUW6NPV2jOZo67zHV9j_pBQ5h8f_ftRhe-tZWreSUYwlTPI2KBhumPactx4YkNpPfutU92k6Oz2g3vOcG2gQpcQEz9ABnF13OCtNYGFSxGQbxLAcqPO_jYvC-KMjFu2sO4dX9bv-LaedMa-0aBUxAVOOnx9tma45WzbaKlKSqqonIs4ogSAc2TyViwT5YIXHYLyGopikRrmK9CY-Kk2oyvt-MQ0HbIpS8t4ehpCUyYXXur4mkioruJf_qQTRcHS0N_yaEgCH-U8j4LwDycJ0P5-u-AtOFI5NQZB0bNInlDVdwONvsiRCMHvWHrpeq4P7BqqoBwBDCesusY4hp9OeYUfh4gein7-ysbzysKGvtRaviD66ybsPGZVKmqE6laZtatBijjtIiIb_FqUTT5YwctHaZJpO3ezFEL21ZryrQioDOIQwZ36Aak2McMbQaLodWDpfO6AiBg8ltN9E-8_2qqMrdXvqEyfza0YDuE_LgIVVXeE7PW6y10qGkV-LvRELhREwpj8jiZyuQAaaliDjCbKDzE9LwX6TGjUD1Byu44KytN5TuLohDdcKspTCvzEy2FI6Lq53FzPAjfVQtE5ZYZaegSTmuZdFBi3evmVE3mUY5oWoRDjqGwZA3M92dv1bXh5t1h84caJykj068GP4N_z08r2wwOnbMJi0SlA29q_MpMqb9EQCfvEYc-t1J6Ba7ovAFN9J42z2BCewccDOOOqTQ0smO_lzR1GLwnO7WTdVn0U72tafM7WbJnuaxGmTzJokaYiTdnAlRAZ5zxgJ8aSRh-WvPVBG2CcfgVSFGb8pfP_qFFSazv2UsQTciQzoZkZIit2TzdKpzQ')

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
DROPBOX_TOKEN = os.getenv('DROPBOX_TOKEN', 'sl.u.AGSFrLuxgMcJsCdGM_rPI6yL3pfJfsznvPJcghL8jy0LRH5rLDViWkVLZUOtOeo9OCotguEWI2VsDlNXa4Tzu9ibzH4hlM-oZikFPK8c8pLFF2NtmExo9FvT3oYHe4WG8R8W47qqpqHW2GOwCle-CjhllLKLY7UR_qXrTBpeEKCf8kaZy7JJ0Qvx3Cn0POk71dlPcBXm6QDS6PrzmD01V1QLSS4FR5LqPDH07wb-cgDJleozDciolrnAg6pIpYe5KLvtk86mZIBuJgfvHwQ9pYARDNqWjodJ49OAMVL90Vdp_hA-XV8jykTJ5y28rH5bOiBY5o7WflQHq5CxPNVfesa19yBrtAc0IqfLEb2TuyoElhiMlrlnu5llvNBKVe5xx7CoU9Rp4PO-X3AwPPLTG384eTzXRFzqNwARTcMZjy4WM9TAytGTlyHWOUcCuL2NPj_yy1VUUwdMRenN_3I9Ei9BVXZpbRxnJIzk3J0yRFNixqNT0paz1eUOwbp5pEs93FITLCplQ5FSLm0xDhdC1W-2FGaVAA55Y8rshwJa3P0ee6at9UpyUDga1aRnbfUcrLkvULVy0VvcV0t_ljgZutlORuBMgyK5IUW6NPV2jOZo67zHV9j_pBQ5h8f_ftRhe-tZWreSUYwlTPI2KBhumPactx4YkNpPfutU92k6Oz2g3vOcG2gQpcQEz9ABnF13OCtNYGFSxGQbxLAcqPO_jYvC-KMjFu2sO4dX9bv-LaedMa-0aBUxAVOOnx9tma45WzbaKlKSqqonIs4ogSAc2TyViwT5YIXHYLyGopikRrmK9CY-Kk2oyvt-MQ0HbIpS8t4ehpCUyYXXur4mkioruJf_qQTRcHS0N_yaEgCH-U8j4LwDycJ0P5-u-AtOFI5NQZB0bNInlDVdwONvsiRCMHvWHrpeq4P7BqqoBwBDCesusY4hp9OeYUfh4gein7-ysbzysKGvtRaviD66ybsPGZVKmqE6laZtatBijjtIiIb_FqUTT5YwctHaZJpO3ezFEL21ZryrQioDOIQwZ36Aak2McMbQaLodWDpfO6AiBg8ltN9E-8_2qqMrdXvqEyfza0YDuE_LgIVVXeE7PW6y10qGkV-LvRELhREwpj8jiZyuQAaaliDjCbKDzE9LwX6TGjUD1Byu44KytN5TuLohDdcKspTCvzEy2FI6Lq53FzPAjfVQtE5ZYZaegSTmuZdFBi3evmVE3mUY5oWoRDjqGwZA3M92dv1bXh5t1h84caJykj068GP4N_z08r2wwOnbMJi0SlA29q_MpMqb9EQCfvEYc-t1J6Ba7ovAFN9J42z2BCewccDOOOqTQ0smO_lzR1GLwnO7WTdVn0U72tafM7WbJnuaxGmTzJokaYiTdnAlRAZ5zxgJ8aSRh-WvPVBG2CcfgVSFGb8pfP_qFFSazv2UsQTciQzoZkZIit2TzdKpzQ')

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
