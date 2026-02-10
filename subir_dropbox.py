<<<<<<< HEAD
import dropbox
import os

# Token de acceso de Dropbox (se recomienda usar variable de entorno en producción)
DROPBOX_TOKEN = os.getenv('DROPBOX_TOKEN', 'sl.u.AGRGx-gNaWxzJOxDIJ38LkCXUYI8eEsTRh3RwATUtylOUPADL5URlilpYZe2IjURVTfdukDdzfzED_GofhodogLunT_rJZxb-D4Ur9RUqEZs8bRTgsdkLpJhdLk2w-x-TpsG-ddenb6JyyH-pclbwmMSTB8Dy7rU0o9jtCOjSHANVC-HUApob2t3hiZvzPF16mCw48A-_w9hhWTZz2qsj5dUDKATjdQOqy4-3j3YUaACOy6bAT-VfWXDlqstrXqlAkST9AT5p6uf97gs6fMCgiIsieDKMohbKwGRNPOaiXzJCWbhmY8vNS0CoYB4jLqOxe5hlBpjxoYQ6XTRvKl0m9l4RpsaX3lXULeAhfi8doyK-lwi_5zunUjp68QXhItJvCCONelnlAlr8K1kzXttKO-ODEB_hygUp9zHTwlZulNGABtNzLA8A-cwQ11QBgm38bA8D16XOWAlywTmzLVGtgH6feWPdA3C1R-tG4Gqz001nSwV1KVlD-ygtyqFNWs8YCGfkkNjF8kSTMkc32pbbb74a-nyqHYT3_sAWoVe5klgfY_WOPh4zmaIIhDSshL5d1aUeb7Jc_hyG5ohT1_P8ABvIFYf9Cq61jcshA8pbqoWe2ZqKPJlJKokFKk_W2rMqmY83eupgBZBihALNNsnLPCT-6wgtzar7mkG0mXQ1X0w00FKqZOsxv0Yx0QTjPHAIAqLH5ao_eSGdOVUmp2QViiQiC9fS6q5JzC23kdFPT7q9clf5w_Q-Gg940LtbblnCMs3y-ADQko4giUtJaSpuUh2YGRr807amdY-0nL_Sf_sp51-_DoHmkmGvkUenklztLbZHrnPu_pG7BxzzzoyvMd72Uxc0-Hy9INcayFoTBz_FHJh-6HXpHymuGZFJ1vLro3mu__1PpDfQU4pO_Lj-8nISBXsnzTpeAnoFKMuX8DPviAB_gwiONsqT8pUdEiBKQW2LBAmEvHzZw9bZZnizSWHNHyefrhFOiINPEftYPktDxAYNlHHxg-4rWYU2q2SQpz0MFP0FHersmU1JshgZEKh3ZO6BaB6Ibmk1FGAd7HL4kRdDLMHD_6BrxZRuinp4Mb5qBEcuZARfeQjEcaZcHD2k2dmaSgMI2huCSYGi5WG0ImTz2EfBwQfWLXi42vdIbqjFTG4gaWYqqe7ysr3lCEk8gw3PdwA3fUG7nur6nm-Dei4SoPrVL0XRqutuzgNMl3RHjg45jAK-MImhnUR6jb6PUU8P5u8fAfyXDskusRMZkaJEF7Ex-BdofdoiH24goBgaXC9dWOzs1VhSqwbpXKlOVNG1atb87nbarTQNIbncuEWQdMbhJIHzV15hbZRNoztCsucdEjKjpOOqUpEgs3YCrhUj92ZvehAoV2Qd_MZBqNj40JZSTwhaDNUoSpLBSPgBEhSwbZClZ7VB3wVYU7UahA-Z69S1DW8D10uK_uFzw')

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
DROPBOX_TOKEN = os.getenv('DROPBOX_TOKEN', 'sl.u.AGRGx-gNaWxzJOxDIJ38LkCXUYI8eEsTRh3RwATUtylOUPADL5URlilpYZe2IjURVTfdukDdzfzED_GofhodogLunT_rJZxb-D4Ur9RUqEZs8bRTgsdkLpJhdLk2w-x-TpsG-ddenb6JyyH-pclbwmMSTB8Dy7rU0o9jtCOjSHANVC-HUApob2t3hiZvzPF16mCw48A-_w9hhWTZz2qsj5dUDKATjdQOqy4-3j3YUaACOy6bAT-VfWXDlqstrXqlAkST9AT5p6uf97gs6fMCgiIsieDKMohbKwGRNPOaiXzJCWbhmY8vNS0CoYB4jLqOxe5hlBpjxoYQ6XTRvKl0m9l4RpsaX3lXULeAhfi8doyK-lwi_5zunUjp68QXhItJvCCONelnlAlr8K1kzXttKO-ODEB_hygUp9zHTwlZulNGABtNzLA8A-cwQ11QBgm38bA8D16XOWAlywTmzLVGtgH6feWPdA3C1R-tG4Gqz001nSwV1KVlD-ygtyqFNWs8YCGfkkNjF8kSTMkc32pbbb74a-nyqHYT3_sAWoVe5klgfY_WOPh4zmaIIhDSshL5d1aUeb7Jc_hyG5ohT1_P8ABvIFYf9Cq61jcshA8pbqoWe2ZqKPJlJKokFKk_W2rMqmY83eupgBZBihALNNsnLPCT-6wgtzar7mkG0mXQ1X0w00FKqZOsxv0Yx0QTjPHAIAqLH5ao_eSGdOVUmp2QViiQiC9fS6q5JzC23kdFPT7q9clf5w_Q-Gg940LtbblnCMs3y-ADQko4giUtJaSpuUh2YGRr807amdY-0nL_Sf_sp51-_DoHmkmGvkUenklztLbZHrnPu_pG7BxzzzoyvMd72Uxc0-Hy9INcayFoTBz_FHJh-6HXpHymuGZFJ1vLro3mu__1PpDfQU4pO_Lj-8nISBXsnzTpeAnoFKMuX8DPviAB_gwiONsqT8pUdEiBKQW2LBAmEvHzZw9bZZnizSWHNHyefrhFOiINPEftYPktDxAYNlHHxg-4rWYU2q2SQpz0MFP0FHersmU1JshgZEKh3ZO6BaB6Ibmk1FGAd7HL4kRdDLMHD_6BrxZRuinp4Mb5qBEcuZARfeQjEcaZcHD2k2dmaSgMI2huCSYGi5WG0ImTz2EfBwQfWLXi42vdIbqjFTG4gaWYqqe7ysr3lCEk8gw3PdwA3fUG7nur6nm-Dei4SoPrVL0XRqutuzgNMl3RHjg45jAK-MImhnUR6jb6PUU8P5u8fAfyXDskusRMZkaJEF7Ex-BdofdoiH24goBgaXC9dWOzs1VhSqwbpXKlOVNG1atb87nbarTQNIbncuEWQdMbhJIHzV15hbZRNoztCsucdEjKjpOOqUpEgs3YCrhUj92ZvehAoV2Qd_MZBqNj40JZSTwhaDNUoSpLBSPgBEhSwbZClZ7VB3wVYU7UahA-Z69S1DW8D10uK_uFzw')

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
