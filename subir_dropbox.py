<<<<<<< HEAD
import dropbox
import os

# Token de acceso de Dropbox (se recomienda usar variable de entorno en producción)
DROPBOX_TOKEN = os.getenv('DROPBOX_TOKEN', 'sl.u.AGJsip9dpyUMQzPt2MKz_EeClbkD1mbdOuQASbf6eiGLHCFtsoNOrUaYnZ0gjwwUL1QtBg-u2WRniCF_y6gD5kLb987GAyihFHZ_I3H_XdGOGaKguChPku1PKsuXQfPEsorK4xtjmP5ayjKD66mMXXx340IJ1DxrOiP6wFFHgeM3El4ZJILhRsSorLIoGI7PDi-BJQYPIao0-5Uk7ausy-VO6GZ43gMptl5CCvrnWeMOp_0zzao0tmxW7Lyrrgv8FLMKKjZodsJUg4Kq1Efqe4ENerMttTbbuMIjql7Xp1cH0k430u4WCUpD1Lw5-8Nxtkc5GsENTI5MUxqw87p3pauAjcNDVnVqhRnq_7NnPHSPu25rhtg2ZZCq4B3_vMtcY_VeTngTI8XUHL0xvvq_1R04AhL-MnPaiEloepeNjcMioCuCfGhsTLQbPA2qIR_cQD4mKtqg6sKTEyWtibfpYj2ogQGQzHlo9XTvjMA12OEUFmIVox8SQQS4ogNBRHHRyqFECF-i19XVEtSmjuj7kPMu7KAez2RGXAogMR0uzheOmcxUgN7aVbzMJr6R8z4q3yOvlT5zyaBNPJEXiRt2dPpylP7kgX8yxXNO-XK-8hITuWJM4Q2VPV4Yzn9nXRhS3OKFQ-9-MPIjdoaMecr38PuIj58osjE6mz6H8WN5bzEJ20iyAcB4ztICoBa5otZwcp-HuAh68hMOC0b9Y2LBJhuX0QMhsS3Q1fV4RGuddYMRj4BtToDU3cmw0ZT-dNhZfcWYkUJUKLE6NPeHE7LaNiEmjLaJ164ennO4R1A5yGMtxoXlkXNNP4yqOIfdP43kwCuCJMw_NZhH2O5susCXsCD0mn96q4WvcWBE1idSeWwhXDqXssVXGdma6xJceNQOQgRq56vQV6XMpy5xaxw1f6PwptBcBZJU62w447u6YtDWRsLIHOKwnzPkc3P-9UkacicZrWnVymdLAIDbYEeJxjXS7Gki075WICXzT_EM3dMSlLuqy_Hqe8UA8mYDkevPsb761FuiLXpwBAoqCCd3BWCvKHsCFRKQxObZ56x9NQzSHzJjRbKSfEKVfOmMVrkLClfjjSY6cSBS-3uNPxoVHD0ZtzqYctsVNqMwUo2Wg16UMjgWDiPBbGBkxubL_KUOkfVVMy2SYwU2FQqat8E6SY4e240N3WlVHu-NyitQHv6Sy4w1n7xQWpbdhmoNInLXI3DCie3yYRZcW5CO-GshYJrSsvJTxBC2_IKq0HaO2FezxZaUjjLOACj8Ba5TeJVN-ETFLcypOWgMwNkoJCbt90zT_TB4S1gHcl1HUzApsStCXm6mUhBW50dCoVnNon2bkQoGm2lEHTlV1lihnVW3DoU4R0hlyYTtMVeuc51oa71Lv1lxS8vWegV1BZsy0SsuqwZkb7EQdRqPdz6c4RmJ0VP77wr8_wkFikecZo4pfMGYtw')

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
DROPBOX_TOKEN = os.getenv('DROPBOX_TOKEN', 'sl.u.AGJsip9dpyUMQzPt2MKz_EeClbkD1mbdOuQASbf6eiGLHCFtsoNOrUaYnZ0gjwwUL1QtBg-u2WRniCF_y6gD5kLb987GAyihFHZ_I3H_XdGOGaKguChPku1PKsuXQfPEsorK4xtjmP5ayjKD66mMXXx340IJ1DxrOiP6wFFHgeM3El4ZJILhRsSorLIoGI7PDi-BJQYPIao0-5Uk7ausy-VO6GZ43gMptl5CCvrnWeMOp_0zzao0tmxW7Lyrrgv8FLMKKjZodsJUg4Kq1Efqe4ENerMttTbbuMIjql7Xp1cH0k430u4WCUpD1Lw5-8Nxtkc5GsENTI5MUxqw87p3pauAjcNDVnVqhRnq_7NnPHSPu25rhtg2ZZCq4B3_vMtcY_VeTngTI8XUHL0xvvq_1R04AhL-MnPaiEloepeNjcMioCuCfGhsTLQbPA2qIR_cQD4mKtqg6sKTEyWtibfpYj2ogQGQzHlo9XTvjMA12OEUFmIVox8SQQS4ogNBRHHRyqFECF-i19XVEtSmjuj7kPMu7KAez2RGXAogMR0uzheOmcxUgN7aVbzMJr6R8z4q3yOvlT5zyaBNPJEXiRt2dPpylP7kgX8yxXNO-XK-8hITuWJM4Q2VPV4Yzn9nXRhS3OKFQ-9-MPIjdoaMecr38PuIj58osjE6mz6H8WN5bzEJ20iyAcB4ztICoBa5otZwcp-HuAh68hMOC0b9Y2LBJhuX0QMhsS3Q1fV4RGuddYMRj4BtToDU3cmw0ZT-dNhZfcWYkUJUKLE6NPeHE7LaNiEmjLaJ164ennO4R1A5yGMtxoXlkXNNP4yqOIfdP43kwCuCJMw_NZhH2O5susCXsCD0mn96q4WvcWBE1idSeWwhXDqXssVXGdma6xJceNQOQgRq56vQV6XMpy5xaxw1f6PwptBcBZJU62w447u6YtDWRsLIHOKwnzPkc3P-9UkacicZrWnVymdLAIDbYEeJxjXS7Gki075WICXzT_EM3dMSlLuqy_Hqe8UA8mYDkevPsb761FuiLXpwBAoqCCd3BWCvKHsCFRKQxObZ56x9NQzSHzJjRbKSfEKVfOmMVrkLClfjjSY6cSBS-3uNPxoVHD0ZtzqYctsVNqMwUo2Wg16UMjgWDiPBbGBkxubL_KUOkfVVMy2SYwU2FQqat8E6SY4e240N3WlVHu-NyitQHv6Sy4w1n7xQWpbdhmoNInLXI3DCie3yYRZcW5CO-GshYJrSsvJTxBC2_IKq0HaO2FezxZaUjjLOACj8Ba5TeJVN-ETFLcypOWgMwNkoJCbt90zT_TB4S1gHcl1HUzApsStCXm6mUhBW50dCoVnNon2bkQoGm2lEHTlV1lihnVW3DoU4R0hlyYTtMVeuc51oa71Lv1lxS8vWegV1BZsy0SsuqwZkb7EQdRqPdz6c4RmJ0VP77wr8_wkFikecZo4pfMGYtw')

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
