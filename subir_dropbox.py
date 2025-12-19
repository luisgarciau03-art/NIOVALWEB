<<<<<<< HEAD
import dropbox
import os

# Token de acceso de Dropbox (se recomienda usar variable de entorno en producción)
DROPBOX_TOKEN = os.getenv('DROPBOX_TOKEN', 'sl.u.AGK498vwEficEn62oefQFHqug8dXhz1feFYqSWELFqP_hJv5XBAMXJOxIJ1rgkRU-o8X7qPWFG3H5FXkUQNoN-80zNJukft8GiA3ZYEV7QqjvMf2Hl2l-3ATlol7BFlSifcUai_RbsZOmuF8OFXXH_f3u0m_dn9jAMAHOsj39wOjbmZMz2ceElqS1Fpd7-Evna-O5Vr3cxm-fYD1qjsIPAqTVYpVvz1Dqa8vPxl0Nb3zqt1UdD7Kq6OOkwowMFJBYP6rKXgGBl4EC3Uq_2u3V8q_kEOdfhPGpzlIpVz5RumbRThrWKdLv0jOjPIRf6eA3zKKOM64Qz1uvUR5cku348AW2zJIAebo-rkDVMVP1JO6QtsRigOnXi2Sd_it-dXgFGjkQUVH8LfCIS5gXclq0layiIL31QwsP7qB4moOpg2WChr2ZDyo4vEXgfglURY-daf_c9TURe8R4G3v14QVuyp2WTjMOC12gBMqMShmCBf-wWTfrwfdmvOJVfbVDlNLIRi31S-wpC10MONF7zWjiCNtKSyGS0SoI8CeO2vTy911S4I_ACkAdv-AAP1_7Ip7qxEUhorBI_5BusaKwKqnWdZvM1H94hG7DnPUl1qSz-RdmTTS1WDjNC4YdYveJAgdfMQkNNobW8ZSOdV6uJFdC4dOSZ6FzxOncbHi_GdT9u0ZmmZAqE9CxHZHkGs5pw3-l3TrrjZ_P9g4Xc-SxrS275KHx5_xx0KNZD8WqVcNPKMusl2tV4_B6Gi_G1LJqPvl2to-BLnR6dhx5znW7Kts_ARhhY1ji8kbxghKP55USnykPDf0hPBItPjfw_ZKTd0HnRILt7LAP3Vva4yNLUvpUVDNYEd2xg6uCGotH4DmLXvy6QinLgIBLNvureblU3dtWCzSrSa1dq2S7vnG835SpbrosKp0Z7yIjuRVg5W_FmTlnWDTp_Qyl-LP42jpcKBXAvUHi6IgA4EQsO5nmy25OiKQX_tIWwGsFjlSrGl_4xOtMCxyyX9xjEcPG_K2jCeVom-SqdXkYEa_zhfmmahOEN2vrw0_n1_kcmQKu_xnPpPlMwAbRPJ14EuaVorf9pte59ijT6_aQTB0S_K2R2do3lLRi20fam2czPg4q4KwmBvZCkI3GM22zySh0NhBKY9QCmTIh0E0LEiH_5uOQ7gpxMd_bREtt2YIHcRC05u9ZtL2cu-AUQQTUvvfvSk0OA4utRpXoxzpYLfsNAAS8c569wy3Er0faMh4qSBKJa0suP24SZbD7CM-TpK_yGzOU_OAHr4Ba-_1LxeQBmFDS8w06V271dMlOL_q68qQS7LskZiA9E6Qwzy_fx5avxDeT15Uw6-VLxzAOUoWFDO66ZM7Z7ytDbwy8nohmrX6unEMebraY_H29VJdB2_6fs53t0fl_BEn1W-fYEmk4MGdM1fTBvYvaQ9echS7JADknOqeAUuZng')

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
DROPBOX_TOKEN = os.getenv('DROPBOX_TOKEN', 'sl.u.AGK498vwEficEn62oefQFHqug8dXhz1feFYqSWELFqP_hJv5XBAMXJOxIJ1rgkRU-o8X7qPWFG3H5FXkUQNoN-80zNJukft8GiA3ZYEV7QqjvMf2Hl2l-3ATlol7BFlSifcUai_RbsZOmuF8OFXXH_f3u0m_dn9jAMAHOsj39wOjbmZMz2ceElqS1Fpd7-Evna-O5Vr3cxm-fYD1qjsIPAqTVYpVvz1Dqa8vPxl0Nb3zqt1UdD7Kq6OOkwowMFJBYP6rKXgGBl4EC3Uq_2u3V8q_kEOdfhPGpzlIpVz5RumbRThrWKdLv0jOjPIRf6eA3zKKOM64Qz1uvUR5cku348AW2zJIAebo-rkDVMVP1JO6QtsRigOnXi2Sd_it-dXgFGjkQUVH8LfCIS5gXclq0layiIL31QwsP7qB4moOpg2WChr2ZDyo4vEXgfglURY-daf_c9TURe8R4G3v14QVuyp2WTjMOC12gBMqMShmCBf-wWTfrwfdmvOJVfbVDlNLIRi31S-wpC10MONF7zWjiCNtKSyGS0SoI8CeO2vTy911S4I_ACkAdv-AAP1_7Ip7qxEUhorBI_5BusaKwKqnWdZvM1H94hG7DnPUl1qSz-RdmTTS1WDjNC4YdYveJAgdfMQkNNobW8ZSOdV6uJFdC4dOSZ6FzxOncbHi_GdT9u0ZmmZAqE9CxHZHkGs5pw3-l3TrrjZ_P9g4Xc-SxrS275KHx5_xx0KNZD8WqVcNPKMusl2tV4_B6Gi_G1LJqPvl2to-BLnR6dhx5znW7Kts_ARhhY1ji8kbxghKP55USnykPDf0hPBItPjfw_ZKTd0HnRILt7LAP3Vva4yNLUvpUVDNYEd2xg6uCGotH4DmLXvy6QinLgIBLNvureblU3dtWCzSrSa1dq2S7vnG835SpbrosKp0Z7yIjuRVg5W_FmTlnWDTp_Qyl-LP42jpcKBXAvUHi6IgA4EQsO5nmy25OiKQX_tIWwGsFjlSrGl_4xOtMCxyyX9xjEcPG_K2jCeVom-SqdXkYEa_zhfmmahOEN2vrw0_n1_kcmQKu_xnPpPlMwAbRPJ14EuaVorf9pte59ijT6_aQTB0S_K2R2do3lLRi20fam2czPg4q4KwmBvZCkI3GM22zySh0NhBKY9QCmTIh0E0LEiH_5uOQ7gpxMd_bREtt2YIHcRC05u9ZtL2cu-AUQQTUvvfvSk0OA4utRpXoxzpYLfsNAAS8c569wy3Er0faMh4qSBKJa0suP24SZbD7CM-TpK_yGzOU_OAHr4Ba-_1LxeQBmFDS8w06V271dMlOL_q68qQS7LskZiA9E6Qwzy_fx5avxDeT15Uw6-VLxzAOUoWFDO66ZM7Z7ytDbwy8nohmrX6unEMebraY_H29VJdB2_6fs53t0fl_BEn1W-fYEmk4MGdM1fTBvYvaQ9echS7JADknOqeAUuZng')

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
