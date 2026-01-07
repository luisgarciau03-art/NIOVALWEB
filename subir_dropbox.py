<<<<<<< HEAD
import dropbox
import os

# Token de acceso de Dropbox (se recomienda usar variable de entorno en producción)
DROPBOX_TOKEN = os.getenv('DROPBOX_TOKEN', 'sl.u.AGPK8HHQrpDu-yKerhOYz6ufdltprtSgd-REGDO_tfrvYcBWuFvnAEqBPgjfS1EegvEfsmQyR_Bu1PROCUHHewhfEUprLDoqFjezW-aRb7CvwVOWDK4OiqxNcSyFsFyVHDe3kSAQcCbeQwQlAy4I76SMrxyGz8YFpkX2WvXg1QKP7wQAQLyNQaEFOrIskO_NELfpcWCO5o3hOJS66620yRGcpvR5WHMPGEcRMSO8jeNANYfOZsaIFtLEzhs7uTGCZSfnACm68KGp-HDESIKEhX2xBV2e17XjbQFyUOBYmRPm8_QIfXsaQwJzfflngMeEmgV7KRmXaqzVxA_Itj4oW8KAXhIPX7mkDJX2klog9BUus-SK3VCgmJZ2KcvfY4jCPV-d8Gc_HKb63e6e6MA1H8Ibn762dcwN2j8i7wpcWfhNQaJt4316OZ8mnWmSEZI0i9sWK-QKXYrbW3euRS1A1v_pwE35APFV_jOVSJfEaC_fcix8NIuCjReUJw7_slfrtIVIkl4RlrcSMZDUoElIbiN7_WkaeaHF0C8E2z2rG8v7wIvlI_aXoSYxPTTWMyo6QIkhlAzLOKoYcJXnt-uC_N77BSqKXjEpLzPGLl62k52l0PFPyaJlsmI_mjbNGfpxdyF7Pa40fFXgAOxZ76TiWd8ZpDOeF-7IvP6UR9gchcF_Klpkvsyi3tZm7aytJ-Z8GiiCT9nmSNyqLm8Y7a8CPR1MPSxiXD_YzigQ_jlSdx2sYJ0kKO76LazyDsF8_Fd6zVT-EpRY3E1eu7OvNXUekXdDSq6uEBo8VFbC8MWEOKXHWXzwcYBHSP8KVePPreZEs_RZbjPaddg09nZSdHmMlzkeJbS-_TgrhPmjIyotDhxyDBdFqT9qNULHKb8gdaKLO_G6ObSL_z6yY7Jyy6g49rcPTEekVJFNFdzS5Jlknr5eUUxzQJm5rSZYbYwpgZ0REusTYUT9aUVoj_iOhQYuPBpcM745evsXc-O9PRz7CBUy_APsCtAKGO6xBylMqO7U3mndAuK3mNfpZGDw4oqkBmJFfUWL-q3fKwFOWRmn7UnX4fV1ZuG6G1WYruO88uchlL6XTCeLpo8RF4AnHVKUO5wAoY3r5Lqb9azrNmb4CTbSwaMhDEqJ9-4-EJ3xCHwP2s-UecruJ57qlFkuBhYAZnx2qsZzFOTsBGwbHV36_kGMEYBtz-oLhHPLpqsHrNtYsfVD0xOdpTj4DLr86rHlZd1L58vrGEAGEntBxTfL9tXgVdQln4As1GP2LDXFyMvnW5Ek4lC19MPKmVsnlh7mWL4Z7NXxPwIiXdgHKcFKi5fkf7PyOBIQYe6osj1_eOMvcfOI-1ThYmiZ0eyoM2QosJjxsvn2MURnjneJ2QNlUJckVF435S5zjCyIIt18Icl1rCubEriMbKW0oBR9uxenC40vmojqIQfvss9CRGFv5hhSrA')

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
DROPBOX_TOKEN = os.getenv('DROPBOX_TOKEN', 'sl.u.AGPK8HHQrpDu-yKerhOYz6ufdltprtSgd-REGDO_tfrvYcBWuFvnAEqBPgjfS1EegvEfsmQyR_Bu1PROCUHHewhfEUprLDoqFjezW-aRb7CvwVOWDK4OiqxNcSyFsFyVHDe3kSAQcCbeQwQlAy4I76SMrxyGz8YFpkX2WvXg1QKP7wQAQLyNQaEFOrIskO_NELfpcWCO5o3hOJS66620yRGcpvR5WHMPGEcRMSO8jeNANYfOZsaIFtLEzhs7uTGCZSfnACm68KGp-HDESIKEhX2xBV2e17XjbQFyUOBYmRPm8_QIfXsaQwJzfflngMeEmgV7KRmXaqzVxA_Itj4oW8KAXhIPX7mkDJX2klog9BUus-SK3VCgmJZ2KcvfY4jCPV-d8Gc_HKb63e6e6MA1H8Ibn762dcwN2j8i7wpcWfhNQaJt4316OZ8mnWmSEZI0i9sWK-QKXYrbW3euRS1A1v_pwE35APFV_jOVSJfEaC_fcix8NIuCjReUJw7_slfrtIVIkl4RlrcSMZDUoElIbiN7_WkaeaHF0C8E2z2rG8v7wIvlI_aXoSYxPTTWMyo6QIkhlAzLOKoYcJXnt-uC_N77BSqKXjEpLzPGLl62k52l0PFPyaJlsmI_mjbNGfpxdyF7Pa40fFXgAOxZ76TiWd8ZpDOeF-7IvP6UR9gchcF_Klpkvsyi3tZm7aytJ-Z8GiiCT9nmSNyqLm8Y7a8CPR1MPSxiXD_YzigQ_jlSdx2sYJ0kKO76LazyDsF8_Fd6zVT-EpRY3E1eu7OvNXUekXdDSq6uEBo8VFbC8MWEOKXHWXzwcYBHSP8KVePPreZEs_RZbjPaddg09nZSdHmMlzkeJbS-_TgrhPmjIyotDhxyDBdFqT9qNULHKb8gdaKLO_G6ObSL_z6yY7Jyy6g49rcPTEekVJFNFdzS5Jlknr5eUUxzQJm5rSZYbYwpgZ0REusTYUT9aUVoj_iOhQYuPBpcM745evsXc-O9PRz7CBUy_APsCtAKGO6xBylMqO7U3mndAuK3mNfpZGDw4oqkBmJFfUWL-q3fKwFOWRmn7UnX4fV1ZuG6G1WYruO88uchlL6XTCeLpo8RF4AnHVKUO5wAoY3r5Lqb9azrNmb4CTbSwaMhDEqJ9-4-EJ3xCHwP2s-UecruJ57qlFkuBhYAZnx2qsZzFOTsBGwbHV36_kGMEYBtz-oLhHPLpqsHrNtYsfVD0xOdpTj4DLr86rHlZd1L58vrGEAGEntBxTfL9tXgVdQln4As1GP2LDXFyMvnW5Ek4lC19MPKmVsnlh7mWL4Z7NXxPwIiXdgHKcFKi5fkf7PyOBIQYe6osj1_eOMvcfOI-1ThYmiZ0eyoM2QosJjxsvn2MURnjneJ2QNlUJckVF435S5zjCyIIt18Icl1rCubEriMbKW0oBR9uxenC40vmojqIQfvss9CRGFv5hhSrA')

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
