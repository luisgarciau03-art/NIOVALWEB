import dropbox
import os

# Token de acceso de Dropbox (se recomienda usar variable de entorno en producción)
DROPBOX_TOKEN = os.getenv('DROPBOX_TOKEN', 'sl.u.AGJpekINlMpj1pKA6YtmqdUhjKUDawoFEvMROzyzmgHBzWlpMMJy7ICCwV1C1lgXl9pyTuVW--m44cq7XrU2hjIlzk0RoW5QwHioStJGznWMirfmRKZmMPgTCTgVApf_Xri-aHHEmu7VpOIPtAIUlhTR5mOECiBcExb_R9DiYdvQd2XbP3KGsFiDZiKLOksa7qXc5fwStvjXevGhSxKTWCRkuavtKW1eL_H8UcQpw4415UstDdNu-lzpDQeGvsNBd5obRIQbYZzOA8_Ry7vU-IwD3T_6bNx654yobeapOR6T_2kdlTV08h45rQ9rh6mcFyKi7USmnHP4eEf4bmMBis8VMVpdDf4zzZHKaxaom0Xcmj-duwsH7ktvF6EaNyIPRdFFFFYSOMO0jpVGQrxibhtf4QLfv1PHTWwyWCbzIvWMxTUE4HyWcpfYvxegrx7-TmsyrVk5WkBwgigWY2VcsHTSNdFzaBXtLwnhiSQB7bpjotUwx1Gx9Of9xxeXcOFtvRx09MZKdwazqIogeoFWEtDPXJnh4fhQ-uByT6NOY7Z7Ww3w1ol6G-E7WaKviI5omvl7gnMaqoN7zVCT5Wl5bUMsIa9gEj6tN_Kgs0dKiW8SA6RROpmAeXVQFNX6gXE8IdgXS_D5sB_Yeh9YAqsjT_4G2ozMHECbOTZMAe25Xlm6M0LLu97kMviV5z6zijWkI6Ad9TMpi9pQ6YP1DomMCXjCgwTNSBmV_gnfBVNw3dGEFaCCTb37osirBKk8MC4RNkrwcNWsFa4Ko4gWYhhDR1ORB5An68XR8ZBuQddFLWcaNwVrGovmm53nCa2GGY8aH_dkL9iU7tCvZKZ2m9bbeauHA8-dtY9aFJm69p_dZHAP973nj-SGIgrBQIfNiTFBcQvq5r9Sm6UXG2kbxuDInLdXpzSROGFW1Wxkq1YBFEWMnwp_2zqSUXntwnI_KRcAKyH2UGg_1YbbxXuU6HdIgoL5QZ47anyt8l75Pm1EY1tuKIt3m6QoXtgb0RTJz7r22Y5jxd8eABG_sXCAk0_5rC3lbWqBAy47iLQU1v6j4ROgzzJa2scRAAXRCrjr2R7Q6VY7mUyctoW0SL0MRWtSSVTVBAAdVHWiFyK8nwvtX95gndjqdHhYsw0AZYPwG0GtWTbdiM9W9kBvWJvKWwXOpy2hXJn_PKLZXO0YJrBxGkmZ7qE0NcQACLRhKqvh47-C5Hb4mEN1dYYpyP6HsJAaKRqvG9LNe6O1K0Mg-UetjSPUgYmxUOMTjfSCda-ZDPxc38QeC6nnN3HpDtksUa--RJN7r80eRhUeR_VtBoR0llAFugwUdidv31leuhrSzHOcFJxxMNXKdprJ5TaXaK2wNm5DITtzwtOgRw4RL8NYY9krnNCtk2oq0QHCCCr6tNdSaWHxd2Xxifs-gKQzVa1K2w2DGXQG5w8KHJuFpS7kHg0KdA')

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
