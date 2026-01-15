<<<<<<< HEAD
import dropbox
import os

# Token de acceso de Dropbox (se recomienda usar variable de entorno en producción)
DROPBOX_TOKEN = os.getenv('DROPBOX_TOKEN', 'sl.u.AGNJTmV_aKBL9sKOmyP_aKynzty-pSDOYVEfFaJna4Td8LqCc_uVaIMxRePkMXWowMtAR7HW_MQFeU2lvcdbzoSki-qTLtJic9WXIyY1H9cmaTl9D5kp5D3X8Blsy-Dm16WLwjW3guTR7oPIB_6pjBLGHyXISFK54MUxDFRS1hEhstdXL84mDY9fFWLhjh67Q2iMVRCmLbp6l9Vd1UqwxPhKiIKmm8lZlP131W8E0DwyeRu5le_fhVLpmws9N6X2E1dqCso-d1T45Gl0bWTXvdelDPrLx-dx2vHaL8b-1wgD0bRHOIK8fSXxs_YR8G0AJfXg6PxL395yGXyMrfUEkMYdGi8x6OmzcV_0ACEck1sC7epifjJzV4YllbHmRebqISR-50liUUUZeGuZf3hH2W0UsL2poQE3SPZz6Coru8ui43AnqhqwJisfUM8QV4G1_WamNOnjNJdIIIf2w3qVJ1nwO0p_Dy3ZK1mc7TCcZFcfLXCvWFFrRItyQFB9JJEUSlvfSnSVQRUvAxd7Nhxm8pQCX1zsPd5tjFtJPCUxuLH5A1QevuDMPVOQa4uBH80BIiejXIePjw0TzKVDtVS5JzUgvhbmXRLRWR2MBWbXzthmmWDEi3s2H8HESZA9ZVK6-9kq_flF3Hnn7aLn5x_8xvbekTRiEa2ejrD4xAVBOGJ4podwNcp_YsAesI1GUCo_4AzbLqK1RwfxzakBVSTcNSt46Tr9Ij7MtGvvhqYg1m8IffzWet_PfplJ1dieibStI5ZD7xyCnIyfNbGA0pqc4uNZZFU-E5t6G_hHXJc57dDgIyLBiyGhGvgwhFgnd8deKWJdTvqWuHm2BLNn71brwTy0QUeMkdIPw4oPPP1P-2hCARzoB-K7Tak_7Ji-p7qdDH5DMSwenXOx0TG6dq0Xlzd6sMwxzAvtanPbE_6ceTcpO0424RuCh_J0QdcbfzDYBksUUH5yoGEl3Tf74buRPOLlwE5x4q0jKnvg1aIg4d56JMsnjZe4rEKKgf7CEsrsltr3UYBtprWX3ZqwvQTt6LaGW-tnuyxejqotpa8rmdMpN9oyJChM3R1CqGLNE8h3HnOtxYAX9BW7G61m7JnnRJOLwgydotjFFq6LXRn3a8q4Y7PByvfTAFln1yVP-LO69udvqhjyKOFEp7dF5ogx5YhsEil_vzQOQmF6Li3FovgA1sx6gORAmDMT7elcFqvP6LbuP0EtA59mCwpA6m3c8wtp2W9vI95jSDscwximA2LkM0hNsG_EWwSTD-j3qlEUo_K7NolpVxW4YRqSCzeCJ3bbGNV0lNbcfTzJYkRG2WfRX004G3mdf7MeZ_hg5KwsgW827YcpzLsnxx5qsDEK_Fe3HsYaiZcT7iamadjuQwu82xUZbWuvuxy3l2hLNRcYiMnhyPXr0hd6miLtBeX0yMfLkoz81xpUIbUnOC3Hqz-Ewwsl.u.AGNJTmV_aKBL9sKOmyP_aKynzty-pSDOYVEfFaJna4Td8LqCc_uVaIMxRePkMXWowMtAR7HW_MQFeU2lvcdbzoSki-qTLtJic9WXIyY1H9cmaTl9D5kp5D3X8Blsy-Dm16WLwjW3guTR7oPIB_6pjBLGHyXISFK54MUxDFRS1hEhstdXL84mDY9fFWLhjh67Q2iMVRCmLbp6l9Vd1UqwxPhKiIKmm8lZlP131W8E0DwyeRu5le_fhVLpmws9N6X2E1dqCso-d1T45Gl0bWTXvdelDPrLx-dx2vHaL8b-1wgD0bRHOIK8fSXxs_YR8G0AJfXg6PxL395yGXyMrfUEkMYdGi8x6OmzcV_0ACEck1sC7epifjJzV4YllbHmRebqISR-50liUUUZeGuZf3hH2W0UsL2poQE3SPZz6Coru8ui43AnqhqwJisfUM8QV4G1_WamNOnjNJdIIIf2w3qVJ1nwO0p_Dy3ZK1mc7TCcZFcfLXCvWFFrRItyQFB9JJEUSlvfSnSVQRUvAxd7Nhxm8pQCX1zsPd5tjFtJPCUxuLH5A1QevuDMPVOQa4uBH80BIiejXIePjw0TzKVDtVS5JzUgvhbmXRLRWR2MBWbXzthmmWDEi3s2H8HESZA9ZVK6-9kq_flF3Hnn7aLn5x_8xvbekTRiEa2ejrD4xAVBOGJ4podwNcp_YsAesI1GUCo_4AzbLqK1RwfxzakBVSTcNSt46Tr9Ij7MtGvvhqYg1m8IffzWet_PfplJ1dieibStI5ZD7xyCnIyfNbGA0pqc4uNZZFU-E5t6G_hHXJc57dDgIyLBiyGhGvgwhFgnd8deKWJdTvqWuHm2BLNn71brwTy0QUeMkdIPw4oPPP1P-2hCARzoB-K7Tak_7Ji-p7qdDH5DMSwenXOx0TG6dq0Xlzd6sMwxzAvtanPbE_6ceTcpO0424RuCh_J0QdcbfzDYBksUUH5yoGEl3Tf74buRPOLlwE5x4q0jKnvg1aIg4d56JMsnjZe4rEKKgf7CEsrsltr3UYBtprWX3ZqwvQTt6LaGW-tnuyxejqotpa8rmdMpN9oyJChM3R1CqGLNE8h3HnOtxYAX9BW7G61m7JnnRJOLwgydotjFFq6LXRn3a8q4Y7PByvfTAFln1yVP-LO69udvqhjyKOFEp7dF5ogx5YhsEil_vzQOQmF6Li3FovgA1sx6gORAmDMT7elcFqvP6LbuP0EtA59mCwpA6m3c8wtp2W9vI95jSDscwximA2LkM0hNsG_EWwSTD-j3qlEUo_K7NolpVxW4YRqSCzeCJ3bbGNV0lNbcfTzJYkRG2WfRX004G3mdf7MeZ_hg5KwsgW827YcpzLsnxx5qsDEK_Fe3HsYaiZcT7iamadjuQwu82xUZbWuvuxy3l2hLNRcYiMnhyPXr0hd6miLtBeX0yMfLkoz81xpUIbUnOC3Hqz-Eww')

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
DROPBOX_TOKEN = os.getenv('DROPBOX_TOKEN', 'sl.u.AGNJTmV_aKBL9sKOmyP_aKynzty-pSDOYVEfFaJna4Td8LqCc_uVaIMxRePkMXWowMtAR7HW_MQFeU2lvcdbzoSki-qTLtJic9WXIyY1H9cmaTl9D5kp5D3X8Blsy-Dm16WLwjW3guTR7oPIB_6pjBLGHyXISFK54MUxDFRS1hEhstdXL84mDY9fFWLhjh67Q2iMVRCmLbp6l9Vd1UqwxPhKiIKmm8lZlP131W8E0DwyeRu5le_fhVLpmws9N6X2E1dqCso-d1T45Gl0bWTXvdelDPrLx-dx2vHaL8b-1wgD0bRHOIK8fSXxs_YR8G0AJfXg6PxL395yGXyMrfUEkMYdGi8x6OmzcV_0ACEck1sC7epifjJzV4YllbHmRebqISR-50liUUUZeGuZf3hH2W0UsL2poQE3SPZz6Coru8ui43AnqhqwJisfUM8QV4G1_WamNOnjNJdIIIf2w3qVJ1nwO0p_Dy3ZK1mc7TCcZFcfLXCvWFFrRItyQFB9JJEUSlvfSnSVQRUvAxd7Nhxm8pQCX1zsPd5tjFtJPCUxuLH5A1QevuDMPVOQa4uBH80BIiejXIePjw0TzKVDtVS5JzUgvhbmXRLRWR2MBWbXzthmmWDEi3s2H8HESZA9ZVK6-9kq_flF3Hnn7aLn5x_8xvbekTRiEa2ejrD4xAVBOGJ4podwNcp_YsAesI1GUCo_4AzbLqK1RwfxzakBVSTcNSt46Tr9Ij7MtGvvhqYg1m8IffzWet_PfplJ1dieibStI5ZD7xyCnIyfNbGA0pqc4uNZZFU-E5t6G_hHXJc57dDgIyLBiyGhGvgwhFgnd8deKWJdTvqWuHm2BLNn71brwTy0QUeMkdIPw4oPPP1P-2hCARzoB-K7Tak_7Ji-p7qdDH5DMSwenXOx0TG6dq0Xlzd6sMwxzAvtanPbE_6ceTcpO0424RuCh_J0QdcbfzDYBksUUH5yoGEl3Tf74buRPOLlwE5x4q0jKnvg1aIg4d56JMsnjZe4rEKKgf7CEsrsltr3UYBtprWX3ZqwvQTt6LaGW-tnuyxejqotpa8rmdMpN9oyJChM3R1CqGLNE8h3HnOtxYAX9BW7G61m7JnnRJOLwgydotjFFq6LXRn3a8q4Y7PByvfTAFln1yVP-LO69udvqhjyKOFEp7dF5ogx5YhsEil_vzQOQmF6Li3FovgA1sx6gORAmDMT7elcFqvP6LbuP0EtA59mCwpA6m3c8wtp2W9vI95jSDscwximA2LkM0hNsG_EWwSTD-j3qlEUo_K7NolpVxW4YRqSCzeCJ3bbGNV0lNbcfTzJYkRG2WfRX004G3mdf7MeZ_hg5KwsgW827YcpzLsnxx5qsDEK_Fe3HsYaiZcT7iamadjuQwu82xUZbWuvuxy3l2hLNRcYiMnhyPXr0hd6miLtBeX0yMfLkoz81xpUIbUnOC3Hqz-Ewwsl.u.AGNJTmV_aKBL9sKOmyP_aKynzty-pSDOYVEfFaJna4Td8LqCc_uVaIMxRePkMXWowMtAR7HW_MQFeU2lvcdbzoSki-qTLtJic9WXIyY1H9cmaTl9D5kp5D3X8Blsy-Dm16WLwjW3guTR7oPIB_6pjBLGHyXISFK54MUxDFRS1hEhstdXL84mDY9fFWLhjh67Q2iMVRCmLbp6l9Vd1UqwxPhKiIKmm8lZlP131W8E0DwyeRu5le_fhVLpmws9N6X2E1dqCso-d1T45Gl0bWTXvdelDPrLx-dx2vHaL8b-1wgD0bRHOIK8fSXxs_YR8G0AJfXg6PxL395yGXyMrfUEkMYdGi8x6OmzcV_0ACEck1sC7epifjJzV4YllbHmRebqISR-50liUUUZeGuZf3hH2W0UsL2poQE3SPZz6Coru8ui43AnqhqwJisfUM8QV4G1_WamNOnjNJdIIIf2w3qVJ1nwO0p_Dy3ZK1mc7TCcZFcfLXCvWFFrRItyQFB9JJEUSlvfSnSVQRUvAxd7Nhxm8pQCX1zsPd5tjFtJPCUxuLH5A1QevuDMPVOQa4uBH80BIiejXIePjw0TzKVDtVS5JzUgvhbmXRLRWR2MBWbXzthmmWDEi3s2H8HESZA9ZVK6-9kq_flF3Hnn7aLn5x_8xvbekTRiEa2ejrD4xAVBOGJ4podwNcp_YsAesI1GUCo_4AzbLqK1RwfxzakBVSTcNSt46Tr9Ij7MtGvvhqYg1m8IffzWet_PfplJ1dieibStI5ZD7xyCnIyfNbGA0pqc4uNZZFU-E5t6G_hHXJc57dDgIyLBiyGhGvgwhFgnd8deKWJdTvqWuHm2BLNn71brwTy0QUeMkdIPw4oPPP1P-2hCARzoB-K7Tak_7Ji-p7qdDH5DMSwenXOx0TG6dq0Xlzd6sMwxzAvtanPbE_6ceTcpO0424RuCh_J0QdcbfzDYBksUUH5yoGEl3Tf74buRPOLlwE5x4q0jKnvg1aIg4d56JMsnjZe4rEKKgf7CEsrsltr3UYBtprWX3ZqwvQTt6LaGW-tnuyxejqotpa8rmdMpN9oyJChM3R1CqGLNE8h3HnOtxYAX9BW7G61m7JnnRJOLwgydotjFFq6LXRn3a8q4Y7PByvfTAFln1yVP-LO69udvqhjyKOFEp7dF5ogx5YhsEil_vzQOQmF6Li3FovgA1sx6gORAmDMT7elcFqvP6LbuP0EtA59mCwpA6m3c8wtp2W9vI95jSDscwximA2LkM0hNsG_EWwSTD-j3qlEUo_K7NolpVxW4YRqSCzeCJ3bbGNV0lNbcfTzJYkRG2WfRX004G3mdf7MeZ_hg5KwsgW827YcpzLsnxx5qsDEK_Fe3HsYaiZcT7iamadjuQwu82xUZbWuvuxy3l2hLNRcYiMnhyPXr0hd6miLtBeX0yMfLkoz81xpUIbUnOC3Hqz-Eww')

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
