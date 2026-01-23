<<<<<<< HEAD
import dropbox
import os

# Token de acceso de Dropbox (se recomienda usar variable de entorno en producción)
DROPBOX_TOKEN = os.getenv('DROPBOX_TOKEN', 'sl.u.AGQ94HjUP1-FD2bqpy4_gD0HkMU3m8utKa1UPeAY4nV-qTjiawnKOl-P5MVbVPbzUFaLyHg7zt9AGJh3aoRQUt_mTqDlyJLMG7MzQEx1N9hgRVTpCuzd36hZbsVTIUoZcJk3yKVW8Nmz7hsPNKoakvEjEJZTNG0qc1NCpTv7Jjt5bx-rQlzwycj7kBfjvriG0GbJu_mJykBqLryUwELFM0ZSTRhnnYG-hJ3iyJt2avbM_R7eFDIgivPbbInU77NyRstJL8BrXmE4wHxaz8z_9TTLPIGzFUF0uv--_YDj-T2C5KwrY3qqfaOq_3IIw8IAHqRMiv8zJ2vmYAnnuxY66yvtm8KOml5aCPqetT1VTYw6ewPw3PXFYmacAhoOKxgcjyx3DgWcH0U-K-TFZsqjot1bxcalJCw1SX9bqgHnsS-ICm50i8rnrqmzTFPOFrVjfiXOwG6FVr4CcC67HV91I_Z_TDsZdKAFxLDHts4R-ZRuEd9DgUxg4iXLtVg6mEXFqy-BaKfaTsJwpILhSiQEYGg9qSLR34HvVuXM62zZCmlX-zotf-IG_Hc2l1ovQ2AgqLOdyykDX2-ZdRDIYyhY-dphfDCi0OXG8gSv4ftsVemIBI3fhvTSEG3snFPzg4gS2RnT6ptOiULRykcw5-_u5-QLf-lGFMwV4sc3pGzZdt2bZi7SJnPAjcWbYg4_dZcShVMKCS6CEu0LhbouW-RUuRrPoCdN6n1lIa4AKRUihk6wBX5zExrzxMQMfyRuhbVoc0hl5Qr3xJVjqOFS1V0R-rO97WpCfNvZFc2NdM-Z-lFdZ_DNE3I8ukimWpsb5E7n5i_aiIXEFCywxfpnav5tSeK76BZDFVRiVQnvVjP3mfivHlxaiOi11BKpdB2n1O4RAGEMTH9WpMaRPivF1kebbiEvDk2n8Wit4fiyODsXUTV4AhxQmejTRXzgJpnL5BEEFFx3QUpJe_B-Akicsznmpn-wI22MdRSHZHhf8jc87NsfEpbl6FiBo4AbxA-3BEwljY3bAJdGfu46c9Pp-5PBB74gr4fz0zU_ESsoeqK8hEti70EARGqyNqaHfIUiDJATAaGPJgLFOE65jo6n56InTlRRWWhIFG39qCZt469VmbtX7YTMAJ5_x4ZFQG_xe6ygikWBbfaraxop151N02zAqU-7TaBUg48GnhvKVtKfWZW99zys3dHN0ZPPl3ZFQnrs9KhK7-fp4roGXD3PGMASbN8COZR1t4OxE4ENzb7YpVE8_saAkeS72cBE7KFn6YStULzfHmD8I2VXGnMezI5iL0_FEZSROmgovVXXImO9F4O6Z9WMxdISKDLZqGrTnxTUSn-BcWHPXGk0ekCx4SB3vtLhBSeIyOxwnFxDylwyYWhl4sFYHRE71QkIRgkEFw0Q3wcHyPJvaBZFb--XA22p4zBrZ4rq0jaT3Gh1CGnkLObt8Q')

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
DROPBOX_TOKEN = os.getenv('DROPBOX_TOKEN', 'sl.u.AGQ94HjUP1-FD2bqpy4_gD0HkMU3m8utKa1UPeAY4nV-qTjiawnKOl-P5MVbVPbzUFaLyHg7zt9AGJh3aoRQUt_mTqDlyJLMG7MzQEx1N9hgRVTpCuzd36hZbsVTIUoZcJk3yKVW8Nmz7hsPNKoakvEjEJZTNG0qc1NCpTv7Jjt5bx-rQlzwycj7kBfjvriG0GbJu_mJykBqLryUwELFM0ZSTRhnnYG-hJ3iyJt2avbM_R7eFDIgivPbbInU77NyRstJL8BrXmE4wHxaz8z_9TTLPIGzFUF0uv--_YDj-T2C5KwrY3qqfaOq_3IIw8IAHqRMiv8zJ2vmYAnnuxY66yvtm8KOml5aCPqetT1VTYw6ewPw3PXFYmacAhoOKxgcjyx3DgWcH0U-K-TFZsqjot1bxcalJCw1SX9bqgHnsS-ICm50i8rnrqmzTFPOFrVjfiXOwG6FVr4CcC67HV91I_Z_TDsZdKAFxLDHts4R-ZRuEd9DgUxg4iXLtVg6mEXFqy-BaKfaTsJwpILhSiQEYGg9qSLR34HvVuXM62zZCmlX-zotf-IG_Hc2l1ovQ2AgqLOdyykDX2-ZdRDIYyhY-dphfDCi0OXG8gSv4ftsVemIBI3fhvTSEG3snFPzg4gS2RnT6ptOiULRykcw5-_u5-QLf-lGFMwV4sc3pGzZdt2bZi7SJnPAjcWbYg4_dZcShVMKCS6CEu0LhbouW-RUuRrPoCdN6n1lIa4AKRUihk6wBX5zExrzxMQMfyRuhbVoc0hl5Qr3xJVjqOFS1V0R-rO97WpCfNvZFc2NdM-Z-lFdZ_DNE3I8ukimWpsb5E7n5i_aiIXEFCywxfpnav5tSeK76BZDFVRiVQnvVjP3mfivHlxaiOi11BKpdB2n1O4RAGEMTH9WpMaRPivF1kebbiEvDk2n8Wit4fiyODsXUTV4AhxQmejTRXzgJpnL5BEEFFx3QUpJe_B-Akicsznmpn-wI22MdRSHZHhf8jc87NsfEpbl6FiBo4AbxA-3BEwljY3bAJdGfu46c9Pp-5PBB74gr4fz0zU_ESsoeqK8hEti70EARGqyNqaHfIUiDJATAaGPJgLFOE65jo6n56InTlRRWWhIFG39qCZt469VmbtX7YTMAJ5_x4ZFQG_xe6ygikWBbfaraxop151N02zAqU-7TaBUg48GnhvKVtKfWZW99zys3dHN0ZPPl3ZFQnrs9KhK7-fp4roGXD3PGMASbN8COZR1t4OxE4ENzb7YpVE8_saAkeS72cBE7KFn6YStULzfHmD8I2VXGnMezI5iL0_FEZSROmgovVXXImO9F4O6Z9WMxdISKDLZqGrTnxTUSn-BcWHPXGk0ekCx4SB3vtLhBSeIyOxwnFxDylwyYWhl4sFYHRE71QkIRgkEFw0Q3wcHyPJvaBZFb--XA22p4zBrZ4rq0jaT3Gh1CGnkLObt8Q')

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
