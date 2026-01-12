<<<<<<< HEAD
import dropbox
import os

# Token de acceso de Dropbox (se recomienda usar variable de entorno en producción)
DROPBOX_TOKEN = os.getenv('DROPBOX_TOKEN', 'sl.u.AGO77pnHditqGbnX9m0GRV-WeMNII_ctLspYmu-oSgYx1CU_MZfcWoNy10q1BZg2q4Ee3yo-H5bIOduVppIcfAWmF_pEguUrMF2tvilvZ2YtEIrSSHrfFaitMBVtLGhmCmwfVAv1cB1Icf0_EsT-E1XHyvDJWpTMusbawgnHPspah8MYaE78ugY3WsC7VbOwEDDPcTB9I7Uw4fppPHB0uI-YCv2lstqzcxeQPrC5rncZYnVnCPtCjDh2vinnrm0v5oEXOtTX1ApYZTYUm0L2FZN7y7iO3Lk3bVXpWxZTt0jpdD1man1U2XYMX12Z6JSeZ_TWeczJf_g58kA0AV78fm3qsizT5NRN_qcr-4heAp5-G6HK472t5NdVNLZfFJmlHX60JH3PkVC-rm4Qib3mgODMRNSnsCXPMe7AFalb9tGbrRp1MN9tdySr2CeIUoZsC5rsbNclSfVBgpwS1JzlOAg2J3iIctKPkfvbWs7nY_R0k1pBv6bBskwNGenmffrySC28--uqX1Ze54-6BpJxB5fr9enaRdz0ciPZ048wosAILsuhtd8V3UmTVytecis7OO5mfGXxQ572aPA2JfOnG7QwLbinPRD-krK6EXyrSvvdJGUG0f9xzDH8lKSV9OGI-qrQNclQTKfrsJOaUrjNvm2koxmSMQWKMPReYyyGS7WdkyaRG0CvowlruxGFq2m_hWFNzO8pE7mrtApFHmYK6mmsaBPo_kDTki5mjuCI7qxI8KLLLNi4z3cn7BccJkpXKjg35-ofAW3pphVSj0YEx7riAmkt0IiSae8xGmT5lNXt5cweQluFlU8hZm-SfX2hZYPgTfrnNuxjfJqCCKWlK9rSCXytd423PcUs2F5Htowes-GogpxdTl0Ix9gl1QvrI6SMiDJL0MKah3Fw5e-kUJAU14BFO356RCtZrTA4yE62xYClugJzI1DslhRJ0UtvIHnkqWFOVP9OboYYAIexVAwYiHT1P0JDXR_twAaTdBFQjpR53wJqoLc1L_Xr-J5RD8tJNj51V1iTb0KJxqjfVPnmKUPgQ6oFIQ5d7SG5ucGer2Ea1NsLOgZ3VoxwM5exwYweXf7GmUd9ku_3donyS8XnK4PHIXyO2Fq2pwKC3yLgKAVsVnBH_O0itATxmf7HFeQpXW_Mnn67C7VIDOvncmyf6MsvEOnCsnpa8y2craXq5j-eycYh32YiilcMFAm9e3PqBGaR9wDWXVbLE4ShADXGYlifJOjev7JVgM4QFn_Jg7VaVtoWOVK7_zVaKsaj0Zn7COXQtCSsTXQfM8udsV9Jsi4S60VkGK3vW0OeBbCvnQ0OYqSoVlYZZEGY8LwBvWjaJpg2HxZ0-VZspJn1zmscSpE93-UWGfoXH-hyxv7JJ1aGv14zrG_lCxnXGmnbXbd664xfv-zuzgk2YuUJ6uaaQwHrTmt-Y6U4HcZhKgw0WQ')

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
DROPBOX_TOKEN = os.getenv('DROPBOX_TOKEN', 'sl.u.AGO77pnHditqGbnX9m0GRV-WeMNII_ctLspYmu-oSgYx1CU_MZfcWoNy10q1BZg2q4Ee3yo-H5bIOduVppIcfAWmF_pEguUrMF2tvilvZ2YtEIrSSHrfFaitMBVtLGhmCmwfVAv1cB1Icf0_EsT-E1XHyvDJWpTMusbawgnHPspah8MYaE78ugY3WsC7VbOwEDDPcTB9I7Uw4fppPHB0uI-YCv2lstqzcxeQPrC5rncZYnVnCPtCjDh2vinnrm0v5oEXOtTX1ApYZTYUm0L2FZN7y7iO3Lk3bVXpWxZTt0jpdD1man1U2XYMX12Z6JSeZ_TWeczJf_g58kA0AV78fm3qsizT5NRN_qcr-4heAp5-G6HK472t5NdVNLZfFJmlHX60JH3PkVC-rm4Qib3mgODMRNSnsCXPMe7AFalb9tGbrRp1MN9tdySr2CeIUoZsC5rsbNclSfVBgpwS1JzlOAg2J3iIctKPkfvbWs7nY_R0k1pBv6bBskwNGenmffrySC28--uqX1Ze54-6BpJxB5fr9enaRdz0ciPZ048wosAILsuhtd8V3UmTVytecis7OO5mfGXxQ572aPA2JfOnG7QwLbinPRD-krK6EXyrSvvdJGUG0f9xzDH8lKSV9OGI-qrQNclQTKfrsJOaUrjNvm2koxmSMQWKMPReYyyGS7WdkyaRG0CvowlruxGFq2m_hWFNzO8pE7mrtApFHmYK6mmsaBPo_kDTki5mjuCI7qxI8KLLLNi4z3cn7BccJkpXKjg35-ofAW3pphVSj0YEx7riAmkt0IiSae8xGmT5lNXt5cweQluFlU8hZm-SfX2hZYPgTfrnNuxjfJqCCKWlK9rSCXytd423PcUs2F5Htowes-GogpxdTl0Ix9gl1QvrI6SMiDJL0MKah3Fw5e-kUJAU14BFO356RCtZrTA4yE62xYClugJzI1DslhRJ0UtvIHnkqWFOVP9OboYYAIexVAwYiHT1P0JDXR_twAaTdBFQjpR53wJqoLc1L_Xr-J5RD8tJNj51V1iTb0KJxqjfVPnmKUPgQ6oFIQ5d7SG5ucGer2Ea1NsLOgZ3VoxwM5exwYweXf7GmUd9ku_3donyS8XnK4PHIXyO2Fq2pwKC3yLgKAVsVnBH_O0itATxmf7HFeQpXW_Mnn67C7VIDOvncmyf6MsvEOnCsnpa8y2craXq5j-eycYh32YiilcMFAm9e3PqBGaR9wDWXVbLE4ShADXGYlifJOjev7JVgM4QFn_Jg7VaVtoWOVK7_zVaKsaj0Zn7COXQtCSsTXQfM8udsV9Jsi4S60VkGK3vW0OeBbCvnQ0OYqSoVlYZZEGY8LwBvWjaJpg2HxZ0-VZspJn1zmscSpE93-UWGfoXH-hyxv7JJ1aGv14zrG_lCxnXGmnbXbd664xfv-zuzgk2YuUJ6uaaQwHrTmt-Y6U4HcZhKgw0WQ')

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
