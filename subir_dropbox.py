<<<<<<< HEAD
import dropbox
import os

# Token de acceso de Dropbox (se recomienda usar variable de entorno en producción)
DROPBOX_TOKEN = os.getenv('DROPBOX_TOKEN', 'sl.u.AGKFsIvS7KT3UcSxkYghnnQDdd7h3up86fSAsKakk4DwPQFpN3j0FYkRAUNyXIbEka4tXZYkfWpl6RryUYFsmQot-D_G27bZLpQkrKGso1kZ_kPoNBXzLxE41LHRdekJmZC-LAFD_fE9gBdeTeZWdJ6z1LoZ5vLwX3Fekw41b_21ZhPiBg1TtwzOGuTyRVIOiXynpS0-OhJe61YA5-EL8ZHDhd75Hc_k6gO-PgX7iTk6EmoRl6841IsJjBMAtRiwpWJGx8CEESnPW1mDM6OevXzK5A0E6N7UV8JD2yM8ymF-luI86TXpbmJb0ahnvfguR58H8OcyReXwdF6O9zDgFc4UWQKUs6Hm2oI0PRr3IH5WYgq8EDOIfH8CWWEgJGjBPM_DTgtMxOjL4BltdamxZSfbRQUaSkvX8O031U3rMkmnjBjbjSVoUQyWM9Frw8gPMKJqbXf3U2e_24TDMczG-DRbUNStsWdxVTaD1EgMECoZk99Ag28-boblFvCCJ3mFVtRw4AgBbDJGbzcWHfhuM1WtPo3wZzrzh9tjn24xcYtnBExrt95_OIv5YdkgnqVpV4eqacF5J5hgC7H4oRfi_oxBnpgIL_8J5uUwBDSKWFx2GIO3bXKjJamF9Xz8YD6E7m8aF5CZZqluTqCyfuRpJDnRspylsFI0crHp-UsjIx6ONDVbAj1f8jaZDpO3CSsZnFzmi4oeQA1LHAjHauy24zrUzS944pmJgtTtfn_eXIrOtRQcsf3I9fqJI1F1E6WdYbXmikyPnzTqQb8ErkDKv8lycy90dLuHxYNmzJ4MIKhiyeJCO3yQpuKoyOxyXY1X9tbPKOBIzH4kqwa8WqUCpRy3DMNfzVkLZkKRqVupPxtUM45XpIV0kg_tDtcmU_f6rIo-fU5BUwna5Exjm-JmoRqep9RvcrEun_Q8gqOFgKTptqqoD18ls145oj-NippQ3tVpgOEc4fgBb-jbDETYNz9mnYAHWzP0NXdD_UnU1kBkMTYzNKKP0zKn61MFcSJyGDf6-Obj842dLHMHuKMW0uWr6MSWimmA9cQU_t-pSwzoLPy2nyz2K3trT1RKTMeNNztzWo-GB4DCSNnk7bholIVSWUvUC1y3qAhIfb11sXBDRrxqUvumh9ozc4Xqz3E5gm4xxIdl6BFIllddeMAnIO_sA6mGG2oxq0tKKAp0PGnvLNk6Amh_GZbkjPQo1Gr2iNGTUGpxNjfMktoe7_wfHmE-_hIT9uymXLv29R5HrW9EZ0kx6yPkKUkLyBjLA2xGQjjN0StoyIr7ad0Osj7uXa2Qcd-zydlL1suDEFGVhKX39wPCh1ql83wimfFutMbytW3rig2ZggS8v49ZC1pad0j_qckFsNjGyPkKIdFkRFK5ZqAUYmZM0DuAIGRXuWY2ZR7QR2FHn1vgjfrWaIahMImrYHpcwZ3iPqZ4cXdnIimAKA')

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
DROPBOX_TOKEN = os.getenv('DROPBOX_TOKEN', 'sl.u.AGKFsIvS7KT3UcSxkYghnnQDdd7h3up86fSAsKakk4DwPQFpN3j0FYkRAUNyXIbEka4tXZYkfWpl6RryUYFsmQot-D_G27bZLpQkrKGso1kZ_kPoNBXzLxE41LHRdekJmZC-LAFD_fE9gBdeTeZWdJ6z1LoZ5vLwX3Fekw41b_21ZhPiBg1TtwzOGuTyRVIOiXynpS0-OhJe61YA5-EL8ZHDhd75Hc_k6gO-PgX7iTk6EmoRl6841IsJjBMAtRiwpWJGx8CEESnPW1mDM6OevXzK5A0E6N7UV8JD2yM8ymF-luI86TXpbmJb0ahnvfguR58H8OcyReXwdF6O9zDgFc4UWQKUs6Hm2oI0PRr3IH5WYgq8EDOIfH8CWWEgJGjBPM_DTgtMxOjL4BltdamxZSfbRQUaSkvX8O031U3rMkmnjBjbjSVoUQyWM9Frw8gPMKJqbXf3U2e_24TDMczG-DRbUNStsWdxVTaD1EgMECoZk99Ag28-boblFvCCJ3mFVtRw4AgBbDJGbzcWHfhuM1WtPo3wZzrzh9tjn24xcYtnBExrt95_OIv5YdkgnqVpV4eqacF5J5hgC7H4oRfi_oxBnpgIL_8J5uUwBDSKWFx2GIO3bXKjJamF9Xz8YD6E7m8aF5CZZqluTqCyfuRpJDnRspylsFI0crHp-UsjIx6ONDVbAj1f8jaZDpO3CSsZnFzmi4oeQA1LHAjHauy24zrUzS944pmJgtTtfn_eXIrOtRQcsf3I9fqJI1F1E6WdYbXmikyPnzTqQb8ErkDKv8lycy90dLuHxYNmzJ4MIKhiyeJCO3yQpuKoyOxyXY1X9tbPKOBIzH4kqwa8WqUCpRy3DMNfzVkLZkKRqVupPxtUM45XpIV0kg_tDtcmU_f6rIo-fU5BUwna5Exjm-JmoRqep9RvcrEun_Q8gqOFgKTptqqoD18ls145oj-NippQ3tVpgOEc4fgBb-jbDETYNz9mnYAHWzP0NXdD_UnU1kBkMTYzNKKP0zKn61MFcSJyGDf6-Obj842dLHMHuKMW0uWr6MSWimmA9cQU_t-pSwzoLPy2nyz2K3trT1RKTMeNNztzWo-GB4DCSNnk7bholIVSWUvUC1y3qAhIfb11sXBDRrxqUvumh9ozc4Xqz3E5gm4xxIdl6BFIllddeMAnIO_sA6mGG2oxq0tKKAp0PGnvLNk6Amh_GZbkjPQo1Gr2iNGTUGpxNjfMktoe7_wfHmE-_hIT9uymXLv29R5HrW9EZ0kx6yPkKUkLyBjLA2xGQjjN0StoyIr7ad0Osj7uXa2Qcd-zydlL1suDEFGVhKX39wPCh1ql83wimfFutMbytW3rig2ZggS8v49ZC1pad0j_qckFsNjGyPkKIdFkRFK5ZqAUYmZM0DuAIGRXuWY2ZR7QR2FHn1vgjfrWaIahMImrYHpcwZ3iPqZ4cXdnIimAKA')

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
