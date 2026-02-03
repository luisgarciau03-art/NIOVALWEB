<<<<<<< HEAD
import dropbox
import os

# Token de acceso de Dropbox (se recomienda usar variable de entorno en producción)
DROPBOX_TOKEN = os.getenv('DROPBOX_TOKEN', 'sl.u.AGQPOkJQnEmBP6eLKD8Po_74mhL6RjISZz3zCmk_bZrX0HTFzcCTrpi0i4sNPYPtzbMSx0z7Ho1xkhHtiNd9nMacsNxa_Rcsidos6k3pAKIEhVh2vej2aiWPC2WZQr2F-P6-Okp4i5YopiS1AgYn0RlcDZffsKadNCLQNivhPvf6D0yAzTnc07JMH8XFVmpe6is2OBvopHuXMIpZ49zUoYvSs283bywu1GpUblaUMlXBxZzqfMDpSNeXOGg5mBNlrFOL5t1-tajNI1JjNUDDwd-uckS6qJSRSYEwhClTk2Sy49QKJd0mLG3PECkE8DU55MT5WSJrYNfkEUKSm-kU1Dvor4yFiU1w0oN8k59zVcDibn6R1PWxcCIgz6BiYo-RM-gtmydPKIK5yqRL4gYhvqFpMC7H2n75m1bhLK1ctlcr6MBV8HRttzhKu5Uy5Oy01MMCYy1pNfSFhFvkK01zUQAlR-ZvCZ1po14_oMChNE1A26q8GJIp74MgTtmhlFu9Oxy0UFlxs3u60LUb3XQGThRHrXiws7g_nz0MiAWag44_rvRF3_6cRfxJIe0UlSdREtKOvsYt87TIj-nKl061LdTYPK9zakdXjpePjNmxHMBlSZqmFqQcj6ryAHkn8vbg8ZatTUI3Cllw_0fb80zOgeq0fuQMb0pWCWuUAqeq9NwILzPzLRZbaGODKKNxKePHFHiU2xiyipKTd7Dy2TJ7bBO7eQ_d1jINkF4i5sVqs-j_wuamuVs7xsh4k1Q4W4GmoYgHA1WpYMw8QM1jgoKUXLlmg4Q5-gYF4LGuKydFh6-kcc9_2v5bNq_-ERN0gTooJnsWD3jy2Imr1nUHFIMkzgrndoFd8Zmt6G16bmoKBILWOqQ0x3utwp1C0xts-8ikYwvd5-apx-rD_0DoeDEsV-rue2AFtEem_WZ_L39JiS-y5svakgxmNL3kMuUuIT2NBvmlbuwfXZvljkSGQQc0ojMVuThdiXeCcVlyFsC3A4_NSugBBDyydMV9oSWckFTNcJp8p2oDq9prBJAEMS1A1fnsiqaOVRQAOrV4S54d1dom-treSAOYrEMO2clYbuv8-vPFL4b7DcrgYBmJT7MZheaM_Ph6zIzSOdgQqIjcgFa09YnPAmGsJTh_TKF2uNP-ILfi9BimiNxYUIFyn3hQspEwKUD32o3nbjCMp0D2E5uZieRox3C3mnsO-ay96ZLM3eePPY01f3x3VvwcI1Roahsa__e3Efa1_oZwvFJtSRVjdqt0q3baNkI-4GgVN2o8G9i1vWbcfOCOn7BmKBztNxfd8yE5Hwiw5jZ1hkvSGt6WNwk0mQyG0nZORLFxTQV3suwNem-qOgxA-ZkKK4FdARyZ7tOKxpAbE0qCUthHEVpmxOoVJK9rTtovBI3vvJWhIv9Ec0-LnD1m-1EgFrLJkdxKGrjdbsvwjwNwZ9sDw4QNlQ')

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
DROPBOX_TOKEN = os.getenv('DROPBOX_TOKEN', 'sl.u.AGQPOkJQnEmBP6eLKD8Po_74mhL6RjISZz3zCmk_bZrX0HTFzcCTrpi0i4sNPYPtzbMSx0z7Ho1xkhHtiNd9nMacsNxa_Rcsidos6k3pAKIEhVh2vej2aiWPC2WZQr2F-P6-Okp4i5YopiS1AgYn0RlcDZffsKadNCLQNivhPvf6D0yAzTnc07JMH8XFVmpe6is2OBvopHuXMIpZ49zUoYvSs283bywu1GpUblaUMlXBxZzqfMDpSNeXOGg5mBNlrFOL5t1-tajNI1JjNUDDwd-uckS6qJSRSYEwhClTk2Sy49QKJd0mLG3PECkE8DU55MT5WSJrYNfkEUKSm-kU1Dvor4yFiU1w0oN8k59zVcDibn6R1PWxcCIgz6BiYo-RM-gtmydPKIK5yqRL4gYhvqFpMC7H2n75m1bhLK1ctlcr6MBV8HRttzhKu5Uy5Oy01MMCYy1pNfSFhFvkK01zUQAlR-ZvCZ1po14_oMChNE1A26q8GJIp74MgTtmhlFu9Oxy0UFlxs3u60LUb3XQGThRHrXiws7g_nz0MiAWag44_rvRF3_6cRfxJIe0UlSdREtKOvsYt87TIj-nKl061LdTYPK9zakdXjpePjNmxHMBlSZqmFqQcj6ryAHkn8vbg8ZatTUI3Cllw_0fb80zOgeq0fuQMb0pWCWuUAqeq9NwILzPzLRZbaGODKKNxKePHFHiU2xiyipKTd7Dy2TJ7bBO7eQ_d1jINkF4i5sVqs-j_wuamuVs7xsh4k1Q4W4GmoYgHA1WpYMw8QM1jgoKUXLlmg4Q5-gYF4LGuKydFh6-kcc9_2v5bNq_-ERN0gTooJnsWD3jy2Imr1nUHFIMkzgrndoFd8Zmt6G16bmoKBILWOqQ0x3utwp1C0xts-8ikYwvd5-apx-rD_0DoeDEsV-rue2AFtEem_WZ_L39JiS-y5svakgxmNL3kMuUuIT2NBvmlbuwfXZvljkSGQQc0ojMVuThdiXeCcVlyFsC3A4_NSugBBDyydMV9oSWckFTNcJp8p2oDq9prBJAEMS1A1fnsiqaOVRQAOrV4S54d1dom-treSAOYrEMO2clYbuv8-vPFL4b7DcrgYBmJT7MZheaM_Ph6zIzSOdgQqIjcgFa09YnPAmGsJTh_TKF2uNP-ILfi9BimiNxYUIFyn3hQspEwKUD32o3nbjCMp0D2E5uZieRox3C3mnsO-ay96ZLM3eePPY01f3x3VvwcI1Roahsa__e3Efa1_oZwvFJtSRVjdqt0q3baNkI-4GgVN2o8G9i1vWbcfOCOn7BmKBztNxfd8yE5Hwiw5jZ1hkvSGt6WNwk0mQyG0nZORLFxTQV3suwNem-qOgxA-ZkKK4FdARyZ7tOKxpAbE0qCUthHEVpmxOoVJK9rTtovBI3vvJWhIv9Ec0-LnD1m-1EgFrLJkdxKGrjdbsvwjwNwZ9sDw4QNlQ')

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
