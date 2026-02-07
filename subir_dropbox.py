<<<<<<< HEAD
import dropbox
import os

# Token de acceso de Dropbox (se recomienda usar variable de entorno en producción)
DROPBOX_TOKEN = os.getenv('DROPBOX_TOKEN', 'sl.u.AGQnXSUkZDyqap2jtT3-Hnia3v4EIM3xsc7tRjYqSMe5wtDPw6J4c1GFbOAs687xjYpYtL7BZgzwN-hfZQSCoaZhg5S1Yj3AC03Jn7qPa-KRkYy9JOa8LAz5npbcev-nHHV4r042PCKAgFKWrolUZzDwdNKd1x-aGrGbjx-t_1JVRmkqEpH49ga4hyp0_r78601A9bevBupbFeTjFoEk47MlEdY3tKGPxy0Ev2LV0nJUOQKx3kTOwmsJx1lNMbAIk-D-k0aTPdH51268m5vIzWyQHVf7Ro6mAgIPPRcWTqebM1f0i-m7hH4lB9yDGqiK2XUMFEoyha22KeHinxDbEi0Cvu46bQ4UZD_X7Qo0q_jbU83jMXxD9lE021ucoDSZhGiqQaq89w1zQfA9pT4jxNhG8K95merJx-EVKQmwJlOU-ACD-W3k4D-VzjNyEcrEAiACBxWaXvZV1ES6GfLKDRpSRoX47uqVj7kf9RPpWywRtiEYQM2Y3-cp9uXg2YeHsFCQhJaLM3H0n85FPXRQzLgoYHpY9LEKfiL3Pii6j_uPFIiDdibcgX-D3hspOTUApQWIADZJSuBd0MnAiLG_8Khpo0WbY3KhkfX7tQ7XCFux03IEX9Nm93nwfNqXN7lpPFGYHy7xDv-zV-qtQZS457l3VqJH-e4cGQUE0ePa0_cDnkJezDLFNUGIQlurDjTDz2jZitVxblrUqKr_4SonjsFIXmeLtwjn4DBitAe2A8kxAVUthZ3IjFnhoa6O6insltmO98X9m211qcN5aWHI9M11zefaCGoTdK-pwGbjLTIiYIm42MQNIbk2yqa1-OZYvN6NVMoAnRfV4TGaa8wVKcyxhyoRzdDEHoJh9BaKeEuwY3SInw5FagIOozRuaXgQNPAszXoRe4OamN06TmA3o1S9TiVNtvcNq4QvPssusqHV9I5gmlA7-qam5zuYg96gau_HirTXZNl0KlAFhIpdtXLV3nfT1WWe8fJGPrcUzB9Ya1qVVAk0nA9frAOuN-WerFIXL0Ie_Cog02r9A3dsJD4e06wxDoKdZzGaC10Gduz4XmorG6YULnckTb8Mfwlum_BVAqQXfNsmmGBUeao8PQZxVlU4c96t5TB9zI87ZKFvfsfg2KVokmPbFUvxiNtu9m8n6gy0k75kdN4V6HVvbxqOa6DBhT0UPShBqzMhE4O_ky-o0LkBiOcN39zDAMDvrlXZvC2VG0HNfhUa25-sQPAS0Y5hvA4ZYN_S5D0WxYKd-zbdmzkEm00SYPhW4nD8IMQujEAMUoBwncDiPvLzsZlbZrsC1MPcd6hUa8rTBMeJc8MBFMHaQBz2RyIKy-sIPrNWoerGudhYHjMxoaboh3-otXNX8pCuwqtBC7B9XflMwkiv6Upf_kKdCMZy2B9ja4zS8lf_frCVKhuU_FhijI7Ha9HVF46vaxPQlQjtyFKGBg')

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
DROPBOX_TOKEN = os.getenv('DROPBOX_TOKEN', 'sl.u.AGQnXSUkZDyqap2jtT3-Hnia3v4EIM3xsc7tRjYqSMe5wtDPw6J4c1GFbOAs687xjYpYtL7BZgzwN-hfZQSCoaZhg5S1Yj3AC03Jn7qPa-KRkYy9JOa8LAz5npbcev-nHHV4r042PCKAgFKWrolUZzDwdNKd1x-aGrGbjx-t_1JVRmkqEpH49ga4hyp0_r78601A9bevBupbFeTjFoEk47MlEdY3tKGPxy0Ev2LV0nJUOQKx3kTOwmsJx1lNMbAIk-D-k0aTPdH51268m5vIzWyQHVf7Ro6mAgIPPRcWTqebM1f0i-m7hH4lB9yDGqiK2XUMFEoyha22KeHinxDbEi0Cvu46bQ4UZD_X7Qo0q_jbU83jMXxD9lE021ucoDSZhGiqQaq89w1zQfA9pT4jxNhG8K95merJx-EVKQmwJlOU-ACD-W3k4D-VzjNyEcrEAiACBxWaXvZV1ES6GfLKDRpSRoX47uqVj7kf9RPpWywRtiEYQM2Y3-cp9uXg2YeHsFCQhJaLM3H0n85FPXRQzLgoYHpY9LEKfiL3Pii6j_uPFIiDdibcgX-D3hspOTUApQWIADZJSuBd0MnAiLG_8Khpo0WbY3KhkfX7tQ7XCFux03IEX9Nm93nwfNqXN7lpPFGYHy7xDv-zV-qtQZS457l3VqJH-e4cGQUE0ePa0_cDnkJezDLFNUGIQlurDjTDz2jZitVxblrUqKr_4SonjsFIXmeLtwjn4DBitAe2A8kxAVUthZ3IjFnhoa6O6insltmO98X9m211qcN5aWHI9M11zefaCGoTdK-pwGbjLTIiYIm42MQNIbk2yqa1-OZYvN6NVMoAnRfV4TGaa8wVKcyxhyoRzdDEHoJh9BaKeEuwY3SInw5FagIOozRuaXgQNPAszXoRe4OamN06TmA3o1S9TiVNtvcNq4QvPssusqHV9I5gmlA7-qam5zuYg96gau_HirTXZNl0KlAFhIpdtXLV3nfT1WWe8fJGPrcUzB9Ya1qVVAk0nA9frAOuN-WerFIXL0Ie_Cog02r9A3dsJD4e06wxDoKdZzGaC10Gduz4XmorG6YULnckTb8Mfwlum_BVAqQXfNsmmGBUeao8PQZxVlU4c96t5TB9zI87ZKFvfsfg2KVokmPbFUvxiNtu9m8n6gy0k75kdN4V6HVvbxqOa6DBhT0UPShBqzMhE4O_ky-o0LkBiOcN39zDAMDvrlXZvC2VG0HNfhUa25-sQPAS0Y5hvA4ZYN_S5D0WxYKd-zbdmzkEm00SYPhW4nD8IMQujEAMUoBwncDiPvLzsZlbZrsC1MPcd6hUa8rTBMeJc8MBFMHaQBz2RyIKy-sIPrNWoerGudhYHjMxoaboh3-otXNX8pCuwqtBC7B9XflMwkiv6Upf_kKdCMZy2B9ja4zS8lf_frCVKhuU_FhijI7Ha9HVF46vaxPQlQjtyFKGBg')

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
