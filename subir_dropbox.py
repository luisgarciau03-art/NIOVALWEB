<<<<<<< HEAD
import dropbox
import os

# Token de acceso de Dropbox (se recomienda usar variable de entorno en producción)
DROPBOX_TOKEN = os.getenv('DROPBOX_TOKEN', 'sl.u.AGJJ1xU5Xr2VRsXVEZ-SyzXuYfD_UiG6NhSiYXmNMlfNi_HYlTPCsIrSmALx3_HVacHFrsGqZE5Cdy-ZMq3iLbfoP1LZX7YRl3kGGCi-f9GAfMpYQjpMJ3s-6CrdyAGxCYFG8VTC11c2oxhu1SgwWBmUH2DNBtA4HL-40s3bVRYR_aurlbOWFdGUF3bsKEU6AFFcAAIaH_XTQxKC1EY-I33sPMnuG3C5L1zZvaY9Eoe_J1wQRPsu-OZciDYjE1xNbEaNPK5X23fdPBwDK56_Ryu6Gr4K8RHOn0vzhtaACniZ1Od_mW3e1FXfCftqe8kKbTBfvkMjXrYMghmJZiFjkL4lPujdx4dSB717LDJhFCSIKPDMchogNhfRpmCiPv6tPCnWIXy6ta7oHLXPodPjsOlxMSDg0gdgwZMFdHb5v4yVcwGGCHSkCnebPe_4tE7s3XhqGMmR0dlNAEQXDo9JVPBlIcEEGlc_HcwGG77oTET49y_Ms9t0iSBKPGEb6FHNbAFk3vjD7l-GDeR5B18nX53xA18__IY_HSvWimKf-SuUmkLjEHCJj3HNHZwgvZ1KfOE_IwDo8F3WkO0VoRbvHJBlx2ixL4c2ZzGlHIh6EqHIC9U8Hk2fQsvvwoe7CtM3JyowYZypKtQichJzlu0sUSl6dTidBCZcuU1PmDYQH85Gd-a0AXhMNPuUJan10s97AVwkkkh-uF28CoArIofpTMffwLtxR6btRcZJ8TiLeOM3QEPCnIHLAdQr5cE0froY-mXUfZGXBB1Imeax1Tq6eSviHbXTa_f-V_r4h46QzS7axM2XUyRkqqCCexu_Q_MvYdmrW_OYy1kuCiZkqNFl_D5NxJafkhtSxIWTMGH8YucloOVfZ_1AR7HfYJOO07h11QBwuS7LjS12HW_7kJFW7h9CrNPMR06zuLzPff_iZp7Kh3kquXIaXnWU0NOVjQ_iptjwzQtOzQvBtNTdEO5QVX8FmuePg6I-r98Im1DuZhOFEYWgUvlEYBPVqDHEEuy18tDAe9I-sNC4dygs15OsoADmm2P_Rn6gMrKYr8LohSPinwv-4kJfBNMdmbOtyISCBU9j-6kmQ6V-c3VKuiLRQExx9K8j7A1io8sB4KBpc5_u_gsVGa5GqHEGis5OsBTpfmTwBSjiS4pL4CsDcR_4BVuSqQnVw4cNK2YGUbrijNF6iLbw4qHTt8yuGxdq7NibE06vHAbtFvE5eeAaoC2qXELcg6rC6p3sGxT0TWNJkrMTXPqf52ioJCkNFj8oVf_Di2UGFBweu2OgRukIYD-g0i2WSF8_zEGqt4793VuhOLOR83p8xDsPdYof4jlZ8651AFpH1yHcKUCsHfw4p0ECpYd6STx9ni5SFNo_zxfefQOYqNLLgeEL9rz7ahz_dVK9V50Wu8QMDMqsiS2C886bCEx3piImAldPCbFFTwDysKXTKw')

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
DROPBOX_TOKEN = os.getenv('DROPBOX_TOKEN', 'sl.u.AGJJ1xU5Xr2VRsXVEZ-SyzXuYfD_UiG6NhSiYXmNMlfNi_HYlTPCsIrSmALx3_HVacHFrsGqZE5Cdy-ZMq3iLbfoP1LZX7YRl3kGGCi-f9GAfMpYQjpMJ3s-6CrdyAGxCYFG8VTC11c2oxhu1SgwWBmUH2DNBtA4HL-40s3bVRYR_aurlbOWFdGUF3bsKEU6AFFcAAIaH_XTQxKC1EY-I33sPMnuG3C5L1zZvaY9Eoe_J1wQRPsu-OZciDYjE1xNbEaNPK5X23fdPBwDK56_Ryu6Gr4K8RHOn0vzhtaACniZ1Od_mW3e1FXfCftqe8kKbTBfvkMjXrYMghmJZiFjkL4lPujdx4dSB717LDJhFCSIKPDMchogNhfRpmCiPv6tPCnWIXy6ta7oHLXPodPjsOlxMSDg0gdgwZMFdHb5v4yVcwGGCHSkCnebPe_4tE7s3XhqGMmR0dlNAEQXDo9JVPBlIcEEGlc_HcwGG77oTET49y_Ms9t0iSBKPGEb6FHNbAFk3vjD7l-GDeR5B18nX53xA18__IY_HSvWimKf-SuUmkLjEHCJj3HNHZwgvZ1KfOE_IwDo8F3WkO0VoRbvHJBlx2ixL4c2ZzGlHIh6EqHIC9U8Hk2fQsvvwoe7CtM3JyowYZypKtQichJzlu0sUSl6dTidBCZcuU1PmDYQH85Gd-a0AXhMNPuUJan10s97AVwkkkh-uF28CoArIofpTMffwLtxR6btRcZJ8TiLeOM3QEPCnIHLAdQr5cE0froY-mXUfZGXBB1Imeax1Tq6eSviHbXTa_f-V_r4h46QzS7axM2XUyRkqqCCexu_Q_MvYdmrW_OYy1kuCiZkqNFl_D5NxJafkhtSxIWTMGH8YucloOVfZ_1AR7HfYJOO07h11QBwuS7LjS12HW_7kJFW7h9CrNPMR06zuLzPff_iZp7Kh3kquXIaXnWU0NOVjQ_iptjwzQtOzQvBtNTdEO5QVX8FmuePg6I-r98Im1DuZhOFEYWgUvlEYBPVqDHEEuy18tDAe9I-sNC4dygs15OsoADmm2P_Rn6gMrKYr8LohSPinwv-4kJfBNMdmbOtyISCBU9j-6kmQ6V-c3VKuiLRQExx9K8j7A1io8sB4KBpc5_u_gsVGa5GqHEGis5OsBTpfmTwBSjiS4pL4CsDcR_4BVuSqQnVw4cNK2YGUbrijNF6iLbw4qHTt8yuGxdq7NibE06vHAbtFvE5eeAaoC2qXELcg6rC6p3sGxT0TWNJkrMTXPqf52ioJCkNFj8oVf_Di2UGFBweu2OgRukIYD-g0i2WSF8_zEGqt4793VuhOLOR83p8xDsPdYof4jlZ8651AFpH1yHcKUCsHfw4p0ECpYd6STx9ni5SFNo_zxfefQOYqNLLgeEL9rz7ahz_dVK9V50Wu8QMDMqsiS2C886bCEx3piImAldPCbFFTwDysKXTKw')

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
