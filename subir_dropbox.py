<<<<<<< HEAD
import dropbox
import os

# Token de acceso de Dropbox (se recomienda usar variable de entorno en producción)
DROPBOX_TOKEN = os.getenv('DROPBOX_TOKEN', 'sl.u.AGN2Zgp27xyFRT14Y-6QRubJxXoY3N02iAPZi-Tn2uVbndeOQnyjxxfIGAP-bsToXx5t-0JXSqDGPKqpk_Mu6H3TqFrzw8gvN1APNnZ3iCFxeRmHz8s9iPquKelXLkuo4Og6CPZP82bAJ-x2xPmMB0JZok0iGuILwV4mfYTAnVOCHNTApbhDmYuSO2PB6Psnnxz5DwO1ORbvjVdq9dR02NyFNP8vDhbxv0vmT_x4yr9UlAtLeio-uiQ2N-75yQrGEkL4Wl8BvKY8VqlVMgTTFVAa93kxBNfL1KubgCFMhJUoeIEaeVZGCzkpCb47oqAwAl0Stf7ENvbu1xuTobv59i4xbzo-BjrsuzNBwlKUBKBNFfwwGNRjVk31bvEgoNXN3S6jgiV3zmntOqEMHZ56g48-x1wZwuVYfPO_l8uydkoU83rqVey3Bhyc8OzXl3tgG4FIF5wWU8lYeoaNsGOpZQFBc3dj_9dqf8OY8_WhZFuijdP0xZZxB0s9E3SJei45rC_xoFe35vB1G-X4HbqkotLkSWIQf8_OBx3e0YznSjrflHNzJ5qIqM9P_-3Tui15KJnUPbtU4L1gXM2rWwKKisQWn8WFKineAglfIrYG-A-_y7B-gOSuhgPaRpavp69h5ARzygfkcNel98vGFQ_qzCio1NNU_Ld_LFAh9mY9NQhzG7e0JWVagG1D1U7KXUbeOWV5B8Kb3q4LU4Jm9AlTKuI6XGqeN40CE12hvQcIIabVrEatzroEaGTwq2lZSW3dfEr-AA_E9cIXy89h4x5bd2nUeb91Q8MPOvRy4Jh5m1o_DiKo6MpgA9eFLsqpAmoRNrEseRNfmf189qdcYyLpJLbGK1Nh-vp0ptbM1xFP5-KRpSvoXvoUEAuIpyF5ngVXYB-7bzviQeaCZbQgKnIYK3gSGzSJ2N0r3yET0ILDlcaCipJnrh3EgGYy1Ayq35IgniFhUbG8LLND_68QaFdWgYHx4doVSV_D60gBznD6Md5WOFosOnXiySDgOurryAazY07L7MNdsPMfSS8nrIHxxZEsptXV19mB1QpnNJYH0Yc1VZEafx_VwzGNBkZPpb77ZS42TNB73ml_M3MMmluyla9RVqUBLUawbsFD1uAZ6HJ4y_dgqutAHxvEYoeF4ldzvk7Jb24Sl58kdE3bOzFO8aCHxaw2MDK5qnmQ_cT3fGMLzING0EfOYj1BKu_u-xShtcT_JsYvKpipboEwQpj3PH28qOg9EPbH5o9dAIKDx6BK9PeHiLebd33ca3IwuJ_7OmDxwK1gk-aSOp5dy2oLOYI_wjhtqQLDdRwZbXFfJs9wK5PXk91tOrEjrxm3xw3nsdpMgaPPI7ZuGLNM-FTHefKIhBwctiUfV3mBR_SF0u_6L-d0LuZwE7_ZKJT6LDtayFcD_iHZnX0uONa0PGww4RzeBJgMHa9idrCbrEgRj7dPVQ')

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
DROPBOX_TOKEN = os.getenv('DROPBOX_TOKEN', 'sl.u.AGN2Zgp27xyFRT14Y-6QRubJxXoY3N02iAPZi-Tn2uVbndeOQnyjxxfIGAP-bsToXx5t-0JXSqDGPKqpk_Mu6H3TqFrzw8gvN1APNnZ3iCFxeRmHz8s9iPquKelXLkuo4Og6CPZP82bAJ-x2xPmMB0JZok0iGuILwV4mfYTAnVOCHNTApbhDmYuSO2PB6Psnnxz5DwO1ORbvjVdq9dR02NyFNP8vDhbxv0vmT_x4yr9UlAtLeio-uiQ2N-75yQrGEkL4Wl8BvKY8VqlVMgTTFVAa93kxBNfL1KubgCFMhJUoeIEaeVZGCzkpCb47oqAwAl0Stf7ENvbu1xuTobv59i4xbzo-BjrsuzNBwlKUBKBNFfwwGNRjVk31bvEgoNXN3S6jgiV3zmntOqEMHZ56g48-x1wZwuVYfPO_l8uydkoU83rqVey3Bhyc8OzXl3tgG4FIF5wWU8lYeoaNsGOpZQFBc3dj_9dqf8OY8_WhZFuijdP0xZZxB0s9E3SJei45rC_xoFe35vB1G-X4HbqkotLkSWIQf8_OBx3e0YznSjrflHNzJ5qIqM9P_-3Tui15KJnUPbtU4L1gXM2rWwKKisQWn8WFKineAglfIrYG-A-_y7B-gOSuhgPaRpavp69h5ARzygfkcNel98vGFQ_qzCio1NNU_Ld_LFAh9mY9NQhzG7e0JWVagG1D1U7KXUbeOWV5B8Kb3q4LU4Jm9AlTKuI6XGqeN40CE12hvQcIIabVrEatzroEaGTwq2lZSW3dfEr-AA_E9cIXy89h4x5bd2nUeb91Q8MPOvRy4Jh5m1o_DiKo6MpgA9eFLsqpAmoRNrEseRNfmf189qdcYyLpJLbGK1Nh-vp0ptbM1xFP5-KRpSvoXvoUEAuIpyF5ngVXYB-7bzviQeaCZbQgKnIYK3gSGzSJ2N0r3yET0ILDlcaCipJnrh3EgGYy1Ayq35IgniFhUbG8LLND_68QaFdWgYHx4doVSV_D60gBznD6Md5WOFosOnXiySDgOurryAazY07L7MNdsPMfSS8nrIHxxZEsptXV19mB1QpnNJYH0Yc1VZEafx_VwzGNBkZPpb77ZS42TNB73ml_M3MMmluyla9RVqUBLUawbsFD1uAZ6HJ4y_dgqutAHxvEYoeF4ldzvk7Jb24Sl58kdE3bOzFO8aCHxaw2MDK5qnmQ_cT3fGMLzING0EfOYj1BKu_u-xShtcT_JsYvKpipboEwQpj3PH28qOg9EPbH5o9dAIKDx6BK9PeHiLebd33ca3IwuJ_7OmDxwK1gk-aSOp5dy2oLOYI_wjhtqQLDdRwZbXFfJs9wK5PXk91tOrEjrxm3xw3nsdpMgaPPI7ZuGLNM-FTHefKIhBwctiUfV3mBR_SF0u_6L-d0LuZwE7_ZKJT6LDtayFcD_iHZnX0uONa0PGww4RzeBJgMHa9idrCbrEgRj7dPVQ')

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
