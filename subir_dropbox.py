<<<<<<< HEAD
import dropbox
import os

# Token de acceso de Dropbox (se recomienda usar variable de entorno en producción)
DROPBOX_TOKEN = os.getenv('DROPBOX_TOKEN', 'sl.u.AGRokPYReLY9Ad9p6b1Sb6nNFjixnriuX1xPIVWKPrI_sn0TfbnVB-BUnfGeNF-Phb3jYt1jbyPr6_m__0qikpI1CHMiX2iMwMpp6v7VLIaSyqhSlFIqXaGul9cDprCGV7XnqXqfjl5oGWt0Klxd3VLAFdO6VIT-2o0MNhnJEIRE7GIv3tVj1vXZVxb3Y1Z5zDnYnh6xGsBa6sl3jkcEnOXQX6DQdwCL4fNwbeVVigxm-KnFI2Ibm3Q56WP-caBGDW_bsKh9CoEiy2rPT9TRYKcFdborehwX2zFRSQ3Z3q6YUTTV_U4635xbkDoU0K9bMAx77fZJdzuKNfv1_A_9_vJL1w2EiHLzrgzdfED-RTVcO77sQnCxjYBXxcRIChdaGMLA8WxXFcRu1DCaxIDzN66RUqHihWAl_flPXV50Mz58-S8i_ZJmSZPsJMh1DKWMJTog-cL1FhFV0yO6YiItaHb4GZfkAZiYYGz1aBXp67aS6WlTj-gIGRN7ouQ1_6d93hPfZZf6tvLBShYUyJ2M7ImdN9xFm6rOuDPa_KqBsDlZxDK9_UzQc-OmpNu3z1WqJvCK_i2II3sbLx9-t5HJyDclUM6ahb4FLKilLmwcauGWhqz3QZd0YLxwtLWsl4NfBPoBQjMcICebm-6jKsVNoCvZCVt97MqfsSRCVFgJBrqUyx5pv2z0d4aPdnSnPXXMtMu1EKG2seOPNQW6TPeE1S7zZ9OiDz8l0_uU7VHyGszPK9JtwU9WpImEvDV035ON2V63AQazXrvrVPe9ck7tQ5xPI0umS7BrZfvLM-pbQsDZAnjDueKdfX6RubFGWwRkjivK4LFJO73vxvlF1AblY6FLx79qu7HrfElZG5XHEKk09x9oFryEpqGLPl4IalXMAzhorg0vLUrdB5Hf9o8do5Q7Pui22kIc0NPUWAZWb33qfpvWOPDnOzJtZdadrWhBeIReJ3inJH-fLetbQfmG4RN-lLZWjfDrqHGZrb6v-G0OTrkor9-tKDztpJY5YOWp5soc3HOVPdmIt3YVhwoRBiqn84DyH02Oadm-7FESgivuUasJ9h2jkDjPjY7hazlzAn7x_c5RnZj5K9UYUAuQrbcLv9xg7uIi9_qD9YvcTwLRDsF8hLA3shpdKUWBKXx7IJ5gEMRHfpzfKkKxvlcKCH6eTyHbko4RYc2iqdDJSTY-ekyGUUefqoI7gqjVUWpmj3KgHaB68kWlVh8as1cYIIaDC5xd0NDs91JvkhmMOnB314gWW7k-ezKuLAMqwwBd28YmZP11n27f8Swkrt4cFe24nb2-wgV3aaa2Th9-YGaj7lhjoivG6vLP-j-pnlYVCNT7Jbtvpr_3f6RntkzGF55spLLZEIaq-r78y4SxZ5UVs9F1nno0sNJ_GJON5m5ErWqJcNqgtVCBcAjmtTWpvJ0vQmQGXBoPf0m54Ofu9655SA')

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
DROPBOX_TOKEN = os.getenv('DROPBOX_TOKEN', 'sl.u.AGRokPYReLY9Ad9p6b1Sb6nNFjixnriuX1xPIVWKPrI_sn0TfbnVB-BUnfGeNF-Phb3jYt1jbyPr6_m__0qikpI1CHMiX2iMwMpp6v7VLIaSyqhSlFIqXaGul9cDprCGV7XnqXqfjl5oGWt0Klxd3VLAFdO6VIT-2o0MNhnJEIRE7GIv3tVj1vXZVxb3Y1Z5zDnYnh6xGsBa6sl3jkcEnOXQX6DQdwCL4fNwbeVVigxm-KnFI2Ibm3Q56WP-caBGDW_bsKh9CoEiy2rPT9TRYKcFdborehwX2zFRSQ3Z3q6YUTTV_U4635xbkDoU0K9bMAx77fZJdzuKNfv1_A_9_vJL1w2EiHLzrgzdfED-RTVcO77sQnCxjYBXxcRIChdaGMLA8WxXFcRu1DCaxIDzN66RUqHihWAl_flPXV50Mz58-S8i_ZJmSZPsJMh1DKWMJTog-cL1FhFV0yO6YiItaHb4GZfkAZiYYGz1aBXp67aS6WlTj-gIGRN7ouQ1_6d93hPfZZf6tvLBShYUyJ2M7ImdN9xFm6rOuDPa_KqBsDlZxDK9_UzQc-OmpNu3z1WqJvCK_i2II3sbLx9-t5HJyDclUM6ahb4FLKilLmwcauGWhqz3QZd0YLxwtLWsl4NfBPoBQjMcICebm-6jKsVNoCvZCVt97MqfsSRCVFgJBrqUyx5pv2z0d4aPdnSnPXXMtMu1EKG2seOPNQW6TPeE1S7zZ9OiDz8l0_uU7VHyGszPK9JtwU9WpImEvDV035ON2V63AQazXrvrVPe9ck7tQ5xPI0umS7BrZfvLM-pbQsDZAnjDueKdfX6RubFGWwRkjivK4LFJO73vxvlF1AblY6FLx79qu7HrfElZG5XHEKk09x9oFryEpqGLPl4IalXMAzhorg0vLUrdB5Hf9o8do5Q7Pui22kIc0NPUWAZWb33qfpvWOPDnOzJtZdadrWhBeIReJ3inJH-fLetbQfmG4RN-lLZWjfDrqHGZrb6v-G0OTrkor9-tKDztpJY5YOWp5soc3HOVPdmIt3YVhwoRBiqn84DyH02Oadm-7FESgivuUasJ9h2jkDjPjY7hazlzAn7x_c5RnZj5K9UYUAuQrbcLv9xg7uIi9_qD9YvcTwLRDsF8hLA3shpdKUWBKXx7IJ5gEMRHfpzfKkKxvlcKCH6eTyHbko4RYc2iqdDJSTY-ekyGUUefqoI7gqjVUWpmj3KgHaB68kWlVh8as1cYIIaDC5xd0NDs91JvkhmMOnB314gWW7k-ezKuLAMqwwBd28YmZP11n27f8Swkrt4cFe24nb2-wgV3aaa2Th9-YGaj7lhjoivG6vLP-j-pnlYVCNT7Jbtvpr_3f6RntkzGF55spLLZEIaq-r78y4SxZ5UVs9F1nno0sNJ_GJON5m5ErWqJcNqgtVCBcAjmtTWpvJ0vQmQGXBoPf0m54Ofu9655SA')

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
