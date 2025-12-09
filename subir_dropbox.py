import dropbox
import os

# Token de acceso de Dropbox (se recomienda usar variable de entorno en producción)
DROPBOX_TOKEN = os.getenv('DROPBOX_TOKEN', 'sl.u.AGIJxNYAt_KiVWhMxqnAp1hahjEDbqJCY7Tk2D15KWy8e4lVwE14KoMsVeIdMEP6EMQsmEajmh4Moc56pOqljuhmzs60DI1gsVYpmyZPfRpfCgzIwncxbel13Bxq2CJmA5pgWq7rHDrmM-bLDk_L-3W-pzYyZ15ZxiBASAFL38cYxg1c7h1JCjNH76rAYPAvVavz5R6Xe4tF0IHYbeF4pV3qlb2c0CdAJP_0X2RI3uQNIcavWCj1gnkLScwIWThSiIG2p1nOvW7Tn2Vs5IHVLP9XXnaJjR3B3BIOjsOgDyi2hW5PJdI5Nc5W9R_jAWNm4XamoK-gjRd13b-cSBxqmSPKA2J1Tuq-5kleyorr33VwBLf-bxjMqLNIT72hdRqdjTcjn1dBMaWE1-SHuHCU6HulErB5Jid-mx_2jF6aEwjwPVljYviweYJpN23T8gI-yxkGj6LC8_M8uZE5sUYe_i-B_YX--wPBmN1f8EQTXRzWWPC2Okrk-YsBpFayG85WkDDxuOnA7hS_HbEdtGzxKgo5yA1iccjv8iQWwQxKrTH6MsNLQETEkcT5hq46NRhbFpUTuXJ-ujWzFMqNphk_Cor17p_XsNeJZ7vgXA5dPZG_oLyHA1B8rbhdYJlA_Ib7bcA67dadaq-sjIWjW488ZDuEpb76wUtiHBfxXAlg5DxgaXknsHItcSn_yVXJQUAKE6jL-CKiAVBAvJuGoEMbDF5SoD5-i_7yquOycHz3886HDe4V8A9-IMgdENDnVPrSsVUdkqaBbNSYoMJjIO1fHDyFiSp580QiMm4KVO4IlOXDDJWaRcQ9OQiHVxs5iwhJmcp657_4rmEdCX8ENcp063yKjRPYO4s8SWjwQkhfrMEhcOsV53I0DMgg2OzDMTIPs8Aun_xdE8aj14PIyy_KCVHjjNTScXOfHfDQyYI9Dj9B-aYrTSHhTcR6XwUbeI0RsEoVuZB9yegKfD7llBZbVNZqmKK1_kHF_K4F87FtcIohuDO9DtkeZ_ubn5GMHFz9SDcjShgRFfsSOYjOiGGDEJyXtBrFMIFnqceLgNkXIZpQ_nT_PEHO7Lihx4z6JnCqyiY978Oxb1Vy6Z0FSgT8lPOh9CD-7wtW-M41QFm6U70MHLpuiDgTST-tihEXgEQkaMgffc8Rv9SIAD850F2rxDpWmB6JW6esiYZj3rfKc0CJdicAFMlxhGC8y4pnpYgJv76MkZi8PyvlPUkAHUuPS8RLXzuJlUuKQKCLDUanj9amS0Z3l-n38B6WDd7XF6uiwuQd6SjUwW46ko0Nq1UJy_FNMTTJsd6mmpFOXM9HQ0Gvc9udJ44O_h6KDAktMLnaJnpVnD1Ufn4Uh058vo_MBAVDE7etszNEz6tDY98F7l-unRMqTHbkXmSa6gSwgsMYDkcQScGcJabr_LE3gnzV-YHvZSEdKtA15eDpbHi39u4U9Q')

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
