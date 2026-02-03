<<<<<<< HEAD
import dropbox
import os

# Token de acceso de Dropbox (se recomienda usar variable de entorno en producción)
DROPBOX_TOKEN = os.getenv('DROPBOX_TOKEN', 'sl.u.AGQBYZ4fAc7K0DsCIxAh5KMXwiXY99hm4o_jOSAIylKsGXEN-3poADHvFs2O9fnlIUAhDn6n0ioq0PFYc20Vu_F3ADz0ElbwqtN9DiXOCG1ySd4p_0JuM78jCLMrubnRQTN-fTQTfkW3Gic6buaTZM5JmKAeT42yrgpeajleC8D4CeT2TTfDAvwDpngUzHSQ2u55HUtb1l6n5sJTNO-PCTgAAevawqxeycOshy7AwVyj8OYCNH4cLVoXChC6T1J3JBNvNbnqSVu953kivQ2kCT_qzDWTWESs71webl8hCGDpL-09PjweP1RyG9Ltkv38QcGUicO-jNm3aHAvNiezdcfQzmg8AronSj0sJFaL8CIES7F3mOd7gLXAqpoYVw1WcIYq_byom2xTwe38QLOyFBEXPoBEkiX87PVaGsaI1agzCZN1nG9l7g_VTRqb3BMrqBVbuBYpeyb8s1c1VlCNTh4Jl99vBNAgPpUPsMxrIAfiD8zoob5Sl-p8ULmjyK_nb3XFwcpAq3CrDKj1WMREUTAOp5j33QC91DywNHz1xqNgPGcUXO-pvCeSwZRPgy17RmYqz2uRzFmcg7Zb6J6Id2nOJW6P2n7EMyatO_RZwWX9neDOGrvD_fhuCoLRdx8e7Gp2T1MUx7nbSVYWlQutZUM0zookzN9HwgfilJfXHH7oXOcR3mwu_g5cKmNtEZFdAtVMRQKvOHMEAea4w4jEWVpz-9KF8CFZvyD7d6ucT0EugjORylVAxy56TpiJdXkXYqEPHTwoyw61Wldp0uKYiC25nFdGRKq7MzoUJ9vME1t7j7hqKD9mQzkMQZKCn8MuqqLkSWxNvE7KG-Z4sFcAzqg25HuwSyhGX4uSoloJSOUzTMK7IKD0GfQn_L9I5RpZICPNzHBknfWZAj7Vp4IiDx-eXyuhFyktmEHVzPa0IqsZIkyp3mYz0JvatQ2xMc8EeaKU1j45G71JPr7SUT-PQugNbmDPJnCfMnGt8QceZgqhmsGfSU4k7bNTLmAV1Ct_PXZEWZ4x8AerGowqsrXXHxfgQf2qx0Bpx3AbdKoUYk_WtTdz0RaPUbzlwQlblLRJLhvyNdGoAgFmkTK1DKWje1lc8l3cPAG0LrpOwYcyAVlpBH9K3CZmNwrlTnkeyUfnMlG48orhVgw_ViIl33y0yHE52Q3W1kg-xEpIqa3-V8Zi1DM6amp2_cZepItv5ByrkgxYzPLTZJCsrKZum7VV-oLSaUfX2S6Xqnsi1dO35qhgKeSO2tLkOb4m1xFW1S7cZst1tocwPWq1Vb3FYd2yh9swqsvvWPUChC9Y4TZU7eZ8nolgtDtuPPhGChGtkE3A4BEl-M1q4DVRM-2OJsPt7GTdFITk1htDQdu9263ooY8w1fxB3fYQbZTXUqh0JUFqDp7Keup6-us2LSUEQ6RK6aAqCcBTddBpLYLXL6ihVfUfOw')

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
DROPBOX_TOKEN = os.getenv('DROPBOX_TOKEN', 'sl.u.AGQBYZ4fAc7K0DsCIxAh5KMXwiXY99hm4o_jOSAIylKsGXEN-3poADHvFs2O9fnlIUAhDn6n0ioq0PFYc20Vu_F3ADz0ElbwqtN9DiXOCG1ySd4p_0JuM78jCLMrubnRQTN-fTQTfkW3Gic6buaTZM5JmKAeT42yrgpeajleC8D4CeT2TTfDAvwDpngUzHSQ2u55HUtb1l6n5sJTNO-PCTgAAevawqxeycOshy7AwVyj8OYCNH4cLVoXChC6T1J3JBNvNbnqSVu953kivQ2kCT_qzDWTWESs71webl8hCGDpL-09PjweP1RyG9Ltkv38QcGUicO-jNm3aHAvNiezdcfQzmg8AronSj0sJFaL8CIES7F3mOd7gLXAqpoYVw1WcIYq_byom2xTwe38QLOyFBEXPoBEkiX87PVaGsaI1agzCZN1nG9l7g_VTRqb3BMrqBVbuBYpeyb8s1c1VlCNTh4Jl99vBNAgPpUPsMxrIAfiD8zoob5Sl-p8ULmjyK_nb3XFwcpAq3CrDKj1WMREUTAOp5j33QC91DywNHz1xqNgPGcUXO-pvCeSwZRPgy17RmYqz2uRzFmcg7Zb6J6Id2nOJW6P2n7EMyatO_RZwWX9neDOGrvD_fhuCoLRdx8e7Gp2T1MUx7nbSVYWlQutZUM0zookzN9HwgfilJfXHH7oXOcR3mwu_g5cKmNtEZFdAtVMRQKvOHMEAea4w4jEWVpz-9KF8CFZvyD7d6ucT0EugjORylVAxy56TpiJdXkXYqEPHTwoyw61Wldp0uKYiC25nFdGRKq7MzoUJ9vME1t7j7hqKD9mQzkMQZKCn8MuqqLkSWxNvE7KG-Z4sFcAzqg25HuwSyhGX4uSoloJSOUzTMK7IKD0GfQn_L9I5RpZICPNzHBknfWZAj7Vp4IiDx-eXyuhFyktmEHVzPa0IqsZIkyp3mYz0JvatQ2xMc8EeaKU1j45G71JPr7SUT-PQugNbmDPJnCfMnGt8QceZgqhmsGfSU4k7bNTLmAV1Ct_PXZEWZ4x8AerGowqsrXXHxfgQf2qx0Bpx3AbdKoUYk_WtTdz0RaPUbzlwQlblLRJLhvyNdGoAgFmkTK1DKWje1lc8l3cPAG0LrpOwYcyAVlpBH9K3CZmNwrlTnkeyUfnMlG48orhVgw_ViIl33y0yHE52Q3W1kg-xEpIqa3-V8Zi1DM6amp2_cZepItv5ByrkgxYzPLTZJCsrKZum7VV-oLSaUfX2S6Xqnsi1dO35qhgKeSO2tLkOb4m1xFW1S7cZst1tocwPWq1Vb3FYd2yh9swqsvvWPUChC9Y4TZU7eZ8nolgtDtuPPhGChGtkE3A4BEl-M1q4DVRM-2OJsPt7GTdFITk1htDQdu9263ooY8w1fxB3fYQbZTXUqh0JUFqDp7Keup6-us2LSUEQ6RK6aAqCcBTddBpLYLXL6ihVfUfOw')

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
