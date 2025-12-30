<<<<<<< HEAD
import dropbox
import os

# Token de acceso de Dropbox (se recomienda usar variable de entorno en producción)
DROPBOX_TOKEN = os.getenv('DROPBOX_TOKEN', 'sl.u.AGMPg9iEcdt4xv7BaMEnpZ-88kLdl7AWV9z2O0Z1RsGGENR7ebQbU1RgAHfI-E7IFP7P3Ftp5Si0MXnlynHUb57Vn3drKAqI0IpJ4DaAOB2JLKm9G6qzHS7qoBqf3a89q4vbqzqpThVZEjNjiE4LAK2Cb0hsWAJrFqbxXz9bTK72jj4eWVeUm51jB98gZNEYITp1euGMS_yRNXkeipTfHk1Af-vNnyLXzlzUjD71p22P9Fa4WzhIRgZFEHbCYqtBr931d5j99v3xkxySLGmcmi30jmljhfC8aDf20eE6isRKypf7mOW8BtMzyOCErSQwxhcG9hqBKs1mPSVCtSjGNcBesHrxz5Nho-pGipshI59fQlOJchrCtdVLbLY5MpSH-OoxnaC1GX1t9oqSNl0xDoYOf3ePMSbdScGVEKAt1qFg9ozFoSn0hWYExAwo4tXkJDCgzFW_c0BEZmfpLXd2gtcfujJNwj_6ODpZyWuiubprS_jgtGIt02h3LYDqY23cWECCVIOgZuirCpvucki-7SFmiCbO7AS3kctWUa0CTTT1GXt9BJBWUDsR7sS4kIwC_SdVCC-GGvo16S95mRPXG_GjshsWU_S8HBf6obkQMWdWPrQHyyrJkBq9c9PXBguzL7A1MpijOrsiTpBRliKfcFVjR9J71kEb2TtSDkJ6eLOG14NmHfJxt8A4URJGSdD9tZED8y6E-HHlaKG0mVCQgXjfDQiJhTfDujBwapbX3eTdvV6f_8jmXTLC9z8cEHAolp6EShmcMUDnoiYqFifZdZc_Kzq1GfQcdMNIVl4cIH6Jk03ZOMZWio2dMLogW6Ordgu2C35fLOjG62PDLmsF9gzLblonsWjCvP66o4jdQSolQdtahqSJJ6YAZC5dQEq3NSUgY3ST0fQ8B6stb2iqIuxRe1EcO8X3kau8wRUDeZa9KWhHOuKcUm2HzMyVl5ivWP6tiHvIIHwqxYeUu1JqQ7faUQQmZTsqb-msygAWmAAA4gBLof_T2XJeJdPLo6TqcGhKVrG15xfGnF0sO82aYaMnce_c63HYqtn3orrU3tdmwuaZZgNd1kaIOIvDb6sqdQ34sDUtbTbsgOkOZFKzAMBFT9F_7Q0yoTT5-XTzDiHrCyhZV8HJYD3-PQ3DECAIQZe4SPh59ahXpQi3UuZxzCVEjnVtuB7koXFuCSSjY7a3R_TJC4OdlCVB0PJOZ7G52ukI_kG-88Ni3HENE-xdTrbFgEGhVErFsOgjiE1Zu0MXwl-qFylOrPrH_FrWL_SNWjYbMlwNBco8iLuuzfGt9PLfvfSnRDTBhHCPra0xItGZztJY0hU6hqnwwJC6xal3FntN10u8A7n8pcGhB2bLN8dCfFIyZJhdZPyOFKJrzxRji0kKk0guxFVmAwiWnk-GKqvX7mLXLPod2LhnrPL1r5F0m7wpBH4GQIaEy6SfSRS7mg')

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
DROPBOX_TOKEN = os.getenv('DROPBOX_TOKEN', 'sl.u.AGMPg9iEcdt4xv7BaMEnpZ-88kLdl7AWV9z2O0Z1RsGGENR7ebQbU1RgAHfI-E7IFP7P3Ftp5Si0MXnlynHUb57Vn3drKAqI0IpJ4DaAOB2JLKm9G6qzHS7qoBqf3a89q4vbqzqpThVZEjNjiE4LAK2Cb0hsWAJrFqbxXz9bTK72jj4eWVeUm51jB98gZNEYITp1euGMS_yRNXkeipTfHk1Af-vNnyLXzlzUjD71p22P9Fa4WzhIRgZFEHbCYqtBr931d5j99v3xkxySLGmcmi30jmljhfC8aDf20eE6isRKypf7mOW8BtMzyOCErSQwxhcG9hqBKs1mPSVCtSjGNcBesHrxz5Nho-pGipshI59fQlOJchrCtdVLbLY5MpSH-OoxnaC1GX1t9oqSNl0xDoYOf3ePMSbdScGVEKAt1qFg9ozFoSn0hWYExAwo4tXkJDCgzFW_c0BEZmfpLXd2gtcfujJNwj_6ODpZyWuiubprS_jgtGIt02h3LYDqY23cWECCVIOgZuirCpvucki-7SFmiCbO7AS3kctWUa0CTTT1GXt9BJBWUDsR7sS4kIwC_SdVCC-GGvo16S95mRPXG_GjshsWU_S8HBf6obkQMWdWPrQHyyrJkBq9c9PXBguzL7A1MpijOrsiTpBRliKfcFVjR9J71kEb2TtSDkJ6eLOG14NmHfJxt8A4URJGSdD9tZED8y6E-HHlaKG0mVCQgXjfDQiJhTfDujBwapbX3eTdvV6f_8jmXTLC9z8cEHAolp6EShmcMUDnoiYqFifZdZc_Kzq1GfQcdMNIVl4cIH6Jk03ZOMZWio2dMLogW6Ordgu2C35fLOjG62PDLmsF9gzLblonsWjCvP66o4jdQSolQdtahqSJJ6YAZC5dQEq3NSUgY3ST0fQ8B6stb2iqIuxRe1EcO8X3kau8wRUDeZa9KWhHOuKcUm2HzMyVl5ivWP6tiHvIIHwqxYeUu1JqQ7faUQQmZTsqb-msygAWmAAA4gBLof_T2XJeJdPLo6TqcGhKVrG15xfGnF0sO82aYaMnce_c63HYqtn3orrU3tdmwuaZZgNd1kaIOIvDb6sqdQ34sDUtbTbsgOkOZFKzAMBFT9F_7Q0yoTT5-XTzDiHrCyhZV8HJYD3-PQ3DECAIQZe4SPh59ahXpQi3UuZxzCVEjnVtuB7koXFuCSSjY7a3R_TJC4OdlCVB0PJOZ7G52ukI_kG-88Ni3HENE-xdTrbFgEGhVErFsOgjiE1Zu0MXwl-qFylOrPrH_FrWL_SNWjYbMlwNBco8iLuuzfGt9PLfvfSnRDTBhHCPra0xItGZztJY0hU6hqnwwJC6xal3FntN10u8A7n8pcGhB2bLN8dCfFIyZJhdZPyOFKJrzxRji0kKk0guxFVmAwiWnk-GKqvX7mLXLPod2LhnrPL1r5F0m7wpBH4GQIaEy6SfSRS7mg')

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
