import dropbox
import os

# Token de acceso de Dropbox (se recomienda usar variable de entorno en producción)
DROPBOX_TOKEN = os.getenv('DROPBOX_TOKEN', 'sl.u.AGI8CoIGcOrs7hXxzQeyyeyhH8nDDa4Q8ExXBzXg7t6dFqo25oXFpl--X_mGmQDNffiCJCE09ADjOWbVvDla7q4racaXMe5yZ9AvwfiO4lQp7zyzqu_SLrjJaofjBXeZuTxTQbSMD6j9gnHVCpqQE5fEz3jk-m-2YNunTgabUmKFPaES4Mvnv7Neb-SRSGnIgnyb0yu__YIDA7PyiXDJerPiMQ2iOMWdedhzsY_N0uzqnnIHT1lOJ6T1ttkfVHjU8xjfhcW-avbpSeeJSbu7nHpxmZrWXk8Wkk4_2F1keRRlV78_Z6GbaQPRATsc1OrBKuo2QmK4qC3vcUgA31KbTZ95UtBdeuYtIM77unHoaTJ707HsY9XYyj7rP8oie3UiXPps25_NBBg8LWpvAXbK_cxX4NnGBJbDNIxTeVSWWKKD-Kwf9R8L0GgNi_fy23D-aEtQ04ngjMj_6R0u0q9OMmjf5AUN6HfkRLZIxEs4PHhQtqfmrW9feoJWPUlo62nZqBcJFXOvSY3VetynQF_UUAVx46MLU_UyVuIVGkGYk8yT8V-nVEIcNaPjHBVUizxQAib9IvLf0CP-Ysr7VTQLCFaDTwsc27Bf99EFaxBPU4NwaPI1EF4FoNHeoiiu3nBnNL53Umvhk6UvPl4D5U5aoTDTfkjll2oqeumJY3y0kg4w7Rh1fx9cwUBiX22Jw-_L1cIpvRJWNIGTPMvMvL_aFiT6Pu20vxkR6u1OnNJNg6rFXGMG9HfSb1JISP_q_qcx7lvtZpTPmTfq_lnFKO1cgruW1GuheTsDDs1IUj6QxEncJuDJBiVtc4QksteXf_4xoP-iw8TVwU9NRISqHywigxdbyr4PoIbB38KPXTRpre4cI5vNjuBZSmSVE9AL4dkqT-IiwQ8MI9rXTgKSlROru-KP9fh0QMuL2-2FVl7QruDJEkQlVd-KEeGyluZedaGWsxgRsP_8Nci6F_cCUfoQMonrFMHwdR1V9q_cotwZRNysRHoo3sC-KhsokrsSO__BSMKZNK1p2_Z_olYAcCBsDsXk5WTljjeD1Vm9Y7sLjJ7yS8hvn3UxsLbbSugB_WA5nVx6q864TwJYVHbjhsN6lqmfgmo85IH7f6fZLW5jm2IDXo_BzC05g1E2iKmjEHDIgU5sSHsWlvQ2_JmOtEfLbV_Fxk4_bldfZ6AVfw1u2Azw63Buv1B4qjEydp3vkjfzybRERQHaxxr4GwEWM14IkZPiDRKQZq5lLKZl38qxwi42vsVaTN3IPN4gJEE7a4n16Oyhhw9Rhp11odyDYi-jgqHZkHt8rYDbfxkwooG-Kj3ibMD5tbQ3ieyu1Fbp4sDKP6EPw0fRVS_TjETpJGR2MddBQRK-9RmmXHqX5blftVfl8-txS078VJ9PjbAX4LZ3lAcfrdKwNVmVQJiDzlzU60c20w5lyFapdrExmpK40CV2fA')

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
