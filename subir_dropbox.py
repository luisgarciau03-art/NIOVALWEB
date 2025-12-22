<<<<<<< HEAD
import dropbox
import os

# Token de acceso de Dropbox (se recomienda usar variable de entorno en producción)
DROPBOX_TOKEN = os.getenv('DROPBOX_TOKEN', 'sl.u.AGOhz6ccovQDu8yJs7gZ4hC0cGkZyIc7dlFNYxqjumRbWRoXDpwAm3aMvCfXtWJIrjU_dVLnUBD_ZzRJZZH_34qnR7uFyg7c2vatzC2p0zOlwta9QZmzxnyMJ6vZ1m8r1T581Nv9ZicbEj2SF0m3m0yjzTye001iKt0tFbnVwgCv7iqLBIeYqS73RBeniSg8RAzCiq_k4hvaSGTdYeyPrLZ7Dn1NyuAEUhYYCvN3yqy40WuPmKtg3HKmDXaHslD_g-2UwZCE7nEwAStM0zDHYumRkg8xd4BdyeMoa0uMRMAReZLYtrDMQ_L2pJ8ZVIeziJoL1SSkcsXybYIwI4Zq_kTSCKp-zUT_sWnwMCxBbM0foHlUMYgfFnXMta-rbHRvdRFTa7u8Qud1vDZW9z1CTnhA1DotNttxIyqH_PnPxZFj4VXB6fQkOCyal7KxS_vKhBKVpkLhtTVieDhG-7Q72j0UZ7LpL20fkpHm_3GHadS0hFmpPB3VvQ3WFlp7WZFWjsXf_azJqth0OBnha6JeOWUiWGv2vwkjpdOPBG7icn0rVxb0PC8i7P8DVlj66_ppyEfKJjs9RRCAFqcUb056seQvl3mX8P3vXC8GLFf_ahvLaFrjTH5oSVhq--QSFaqimxKjKOaOmBvsfP-5g5t4AT504BWws_AunTNRNTxcYwXcNbuTG03rxFFeLjul13ModDUmt9oQ_JLP_FKGYFcZk8kmM7zGbzyw5l5IIjKfXQZwqIdcHg2fT9v9SvTr4MBNauZ3y8fOFEwplHMcAvvNUhz61TGvo0olrPpRzx7rlZK4YvhfKvi_BBSH4QYLdvLczfL6j5-74BSB0X9FKmuuiqYfZs6TPUOe7WR5_gcTL0LoU3OGFFfRaZBXarldqVGAHE9g8pd3n71POJAEyVAQm4_5KONoY6bO58D1NxvckvCbBIsSNqEmqSTz62ZyuQfpse_dBHGQ0BqgoQpuwa3NuBEbvHpYyQMtiEd14JnFV5HZnGTacT52-b9G2KMyEZCaVgErWY-NWF8kkm1ADUIFoE5fn5dkhfemnDNtLFH8N2YtVp3wuH3auOnQ0QcZ8BbVacaza_XHFkViYJtkwsfxlgrT7pKeVhFZsNOo5qM8cxuzsA7saVyiA34mqEblh65OQJ5del1njHZgyvAX2ThHMzzVRL42gh2CmYrp3KylNP4ZuLRLiJd-Zrhwlb4wEt9VFy0q5rU1_1iHbMFpyCl29np1HYfM-7bVRzxkqHW_3UVuP1UNptIVkW4x2qA4S4R4a6wKgak4avg-OmRk7qeZlAAIGIHaIQzSFytdrf3mdpBFuXT9SXDiuB_JjMogYaL0SgNfSKdo346Bd5gzt7Of0TtNZQRjAPERjO2feebk_evMIs4IC9ctztuSfmG2pmJeeY5bkIki_N2hMDreuDGvF4ZyHjtSao1Cv5TGhgq2OI6UUg')

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
DROPBOX_TOKEN = os.getenv('DROPBOX_TOKEN', 'sl.u.AGOhz6ccovQDu8yJs7gZ4hC0cGkZyIc7dlFNYxqjumRbWRoXDpwAm3aMvCfXtWJIrjU_dVLnUBD_ZzRJZZH_34qnR7uFyg7c2vatzC2p0zOlwta9QZmzxnyMJ6vZ1m8r1T581Nv9ZicbEj2SF0m3m0yjzTye001iKt0tFbnVwgCv7iqLBIeYqS73RBeniSg8RAzCiq_k4hvaSGTdYeyPrLZ7Dn1NyuAEUhYYCvN3yqy40WuPmKtg3HKmDXaHslD_g-2UwZCE7nEwAStM0zDHYumRkg8xd4BdyeMoa0uMRMAReZLYtrDMQ_L2pJ8ZVIeziJoL1SSkcsXybYIwI4Zq_kTSCKp-zUT_sWnwMCxBbM0foHlUMYgfFnXMta-rbHRvdRFTa7u8Qud1vDZW9z1CTnhA1DotNttxIyqH_PnPxZFj4VXB6fQkOCyal7KxS_vKhBKVpkLhtTVieDhG-7Q72j0UZ7LpL20fkpHm_3GHadS0hFmpPB3VvQ3WFlp7WZFWjsXf_azJqth0OBnha6JeOWUiWGv2vwkjpdOPBG7icn0rVxb0PC8i7P8DVlj66_ppyEfKJjs9RRCAFqcUb056seQvl3mX8P3vXC8GLFf_ahvLaFrjTH5oSVhq--QSFaqimxKjKOaOmBvsfP-5g5t4AT504BWws_AunTNRNTxcYwXcNbuTG03rxFFeLjul13ModDUmt9oQ_JLP_FKGYFcZk8kmM7zGbzyw5l5IIjKfXQZwqIdcHg2fT9v9SvTr4MBNauZ3y8fOFEwplHMcAvvNUhz61TGvo0olrPpRzx7rlZK4YvhfKvi_BBSH4QYLdvLczfL6j5-74BSB0X9FKmuuiqYfZs6TPUOe7WR5_gcTL0LoU3OGFFfRaZBXarldqVGAHE9g8pd3n71POJAEyVAQm4_5KONoY6bO58D1NxvckvCbBIsSNqEmqSTz62ZyuQfpse_dBHGQ0BqgoQpuwa3NuBEbvHpYyQMtiEd14JnFV5HZnGTacT52-b9G2KMyEZCaVgErWY-NWF8kkm1ADUIFoE5fn5dkhfemnDNtLFH8N2YtVp3wuH3auOnQ0QcZ8BbVacaza_XHFkViYJtkwsfxlgrT7pKeVhFZsNOo5qM8cxuzsA7saVyiA34mqEblh65OQJ5del1njHZgyvAX2ThHMzzVRL42gh2CmYrp3KylNP4ZuLRLiJd-Zrhwlb4wEt9VFy0q5rU1_1iHbMFpyCl29np1HYfM-7bVRzxkqHW_3UVuP1UNptIVkW4x2qA4S4R4a6wKgak4avg-OmRk7qeZlAAIGIHaIQzSFytdrf3mdpBFuXT9SXDiuB_JjMogYaL0SgNfSKdo346Bd5gzt7Of0TtNZQRjAPERjO2feebk_evMIs4IC9ctztuSfmG2pmJeeY5bkIki_N2hMDreuDGvF4ZyHjtSao1Cv5TGhgq2OI6UUg')

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
