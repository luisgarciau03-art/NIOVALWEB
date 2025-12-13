<<<<<<< HEAD
import dropbox
import os

# Token de acceso de Dropbox (se recomienda usar variable de entorno en producción)
DROPBOX_TOKEN = os.getenv('DROPBOX_TOKEN', 'sl.u.AGL-GAs5SLV8ENXHXfAukUbYTbFwG0_Qn-b47ucYyzZsLLOZVumgc-RYX0s9zX4l0ugdDg130N0Tg4nlpjm0tAnQbVLqEOQt5hnMbqb6O1ureIxtBn911Pr3JGMuVI_GFmHdYY_R6sYOCinfJaErDM4vm0jNCrysOyXt7epZCTdAlVp3V9_aXAFg5yT52hIU4RQZP9GO1Z-3XEo5t7pW_zcw5gBMtnrG1zQU9z8HRubRl7M9yi103JGjtqruLR2a1MTrELeRV_famG5D4ys7QwrDsvHlUIbwWJICP-pHJU2XPLbXUR4kiFxFoLLGAuUmtztfgOqZfI9rWn5XmFhet9mD3-PEqJzJsrjrx5LsfSE2-sBphK2bQ83fIuYN7q_qk0yr1-ZMfC5v6pnOLwKRdrqFZLaEP8Mb4_OJyYC_gzFL2Go34qTRQWi9Fpxog1BQaB3V5A-wda_WZ4hKFHKF9pybuY-qmkQBIyrBaF61kLK-T3aKIBoIgUPhiPvvQRVS6auF7GZQ9FAZiNuq8JP1P482ol6Qy9mSOOxlnBqw8QqseuOLbRku4_-zg_w5NS2bvOLzDL7iVpZvRVUzRfCfapQ5GAz9_ie5Ne5OqQmbHtvJc-BjzWKdt1t5tUEWMSFQfj4ees24s5VBHURs21j9jxZxPb9PtwUWVn6cTX_YPz8cp4TynQszRNkQAIB2qvlotURmV2sEPa-3oCih8or1buEzMV3TMYjy4e4rtWM1bbPFRZID0-AdTUqa8PTJ41fyjpnblf5-1TYdASTbeP21v-GuxoTwOEi2wphQ33WyW_ZiEEdTf-mwfh9GSN9NVtL3qFWFkJXZSY70iSmbr6h_JxFfjWIRqMrsbkDhxMSIN98hlbrMSuhe0VduN_WlJoYG_HVymRUOonlfiLHc-vrcO-TwulZl4kfb7_HvprtM950CT6XdeXOd4IaDoCYy9IQgRD0-cfU9Br4xNq0REDwksJ75gHfiafeB1sLMIGffTVYqGBse4DYqbRK3a3u2GTFmo5sDqM2xR1iVeLc_3MS1EXYaCqSrgfBWdYBoofK_H-q6A_dsXAe0gJCWVrkwgLjTDh1lpDad8ZmaHNiE9qeENjuZP9Xw-A8AuDFhFTyz26OEoSO9aNJPA-KPTmaQMVpf5dsqaOT7YqXnsCV_1oxVlVM2UUcohqsQISR7WQt5Y-kA7spAjPMqe4tF8KEYX0v_FgsRT4YsujOkqtlkukCF9CQxcFsA-aof3YvUd4aZXJV50JDoHKKkc0ABxaSsPitMMRHS5dkpCglJ2zzettRXAqYDeRc94Rq1hjdedol3GFh2xWN5bKpKKEtv5fHKdfoBB_enb80f1Wr7JGiN0DMivXcTo67PqIvywQ2ukX2vxI5-ytcNKWCug8HozGXxMrnHKTPhyu3j-btXZeZ0SBXbwGatRSDFnzgpmm-od_MgXGASwg')

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
DROPBOX_TOKEN = os.getenv('DROPBOX_TOKEN', 'sl.u.AGL-GAs5SLV8ENXHXfAukUbYTbFwG0_Qn-b47ucYyzZsLLOZVumgc-RYX0s9zX4l0ugdDg130N0Tg4nlpjm0tAnQbVLqEOQt5hnMbqb6O1ureIxtBn911Pr3JGMuVI_GFmHdYY_R6sYOCinfJaErDM4vm0jNCrysOyXt7epZCTdAlVp3V9_aXAFg5yT52hIU4RQZP9GO1Z-3XEo5t7pW_zcw5gBMtnrG1zQU9z8HRubRl7M9yi103JGjtqruLR2a1MTrELeRV_famG5D4ys7QwrDsvHlUIbwWJICP-pHJU2XPLbXUR4kiFxFoLLGAuUmtztfgOqZfI9rWn5XmFhet9mD3-PEqJzJsrjrx5LsfSE2-sBphK2bQ83fIuYN7q_qk0yr1-ZMfC5v6pnOLwKRdrqFZLaEP8Mb4_OJyYC_gzFL2Go34qTRQWi9Fpxog1BQaB3V5A-wda_WZ4hKFHKF9pybuY-qmkQBIyrBaF61kLK-T3aKIBoIgUPhiPvvQRVS6auF7GZQ9FAZiNuq8JP1P482ol6Qy9mSOOxlnBqw8QqseuOLbRku4_-zg_w5NS2bvOLzDL7iVpZvRVUzRfCfapQ5GAz9_ie5Ne5OqQmbHtvJc-BjzWKdt1t5tUEWMSFQfj4ees24s5VBHURs21j9jxZxPb9PtwUWVn6cTX_YPz8cp4TynQszRNkQAIB2qvlotURmV2sEPa-3oCih8or1buEzMV3TMYjy4e4rtWM1bbPFRZID0-AdTUqa8PTJ41fyjpnblf5-1TYdASTbeP21v-GuxoTwOEi2wphQ33WyW_ZiEEdTf-mwfh9GSN9NVtL3qFWFkJXZSY70iSmbr6h_JxFfjWIRqMrsbkDhxMSIN98hlbrMSuhe0VduN_WlJoYG_HVymRUOonlfiLHc-vrcO-TwulZl4kfb7_HvprtM950CT6XdeXOd4IaDoCYy9IQgRD0-cfU9Br4xNq0REDwksJ75gHfiafeB1sLMIGffTVYqGBse4DYqbRK3a3u2GTFmo5sDqM2xR1iVeLc_3MS1EXYaCqSrgfBWdYBoofK_H-q6A_dsXAe0gJCWVrkwgLjTDh1lpDad8ZmaHNiE9qeENjuZP9Xw-A8AuDFhFTyz26OEoSO9aNJPA-KPTmaQMVpf5dsqaOT7YqXnsCV_1oxVlVM2UUcohqsQISR7WQt5Y-kA7spAjPMqe4tF8KEYX0v_FgsRT4YsujOkqtlkukCF9CQxcFsA-aof3YvUd4aZXJV50JDoHKKkc0ABxaSsPitMMRHS5dkpCglJ2zzettRXAqYDeRc94Rq1hjdedol3GFh2xWN5bKpKKEtv5fHKdfoBB_enb80f1Wr7JGiN0DMivXcTo67PqIvywQ2ukX2vxI5-ytcNKWCug8HozGXxMrnHKTPhyu3j-btXZeZ0SBXbwGatRSDFnzgpmm-od_MgXGASwg')

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
