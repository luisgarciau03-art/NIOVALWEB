<<<<<<< HEAD
import dropbox
import os

# Token de acceso de Dropbox (se recomienda usar variable de entorno en producción)
DROPBOX_TOKEN = os.getenv('DROPBOX_TOKEN', 'sl.u.AGNEt4G4m38HBIG7pzvXkk_0g0_Biv4Yts26pjmPF-QLSYLzF-Q1_pdOIY5i_4O2z-aydejMaY1qoFDicw5uxUDS7isA3W-pFyEY113ZKaZECAv53VWK2RJ8ohKCQnyDT2cGwhaQnHxfpOjD-eSM7ru2WOBObn61ZmKxoBDxkPvJK6DEU9wsrOWHYBHMcM69mQxzw7lC9s2hQqJGdh6nGYvw5w_yYl8PAgJHpBWVhQZsfI6mj1R6mSCOtlYCpWj6aeaqxSTXHEvu_m4ewsVb6EFNQtp52cisWbBjKcF5cl32oL7_VddsOHtP3PSF_bt3F8w5JPZ-CoKAbrk45LIWv8BqXdveYqh3w6Y_rMtr_y8bmJ_s942TtM0cSn1ePxLJjyJvWbwIj90gBVQ22bJp4guH-_tBpCVIiD-Iv4Rj4NlNk_WIkBcJ-ixPK1LPHdiz_fFT0P6eqBZzOw_lxdp7bdA87eJv8w4MYP0hPadpLF1cyUEtye4zc50zfBIsykfVPxizb09p97xp1w_bdRLeJ1LjBTAWns7ub-d6NMa7vep2mkuHLkHdR9f_95QEqncnxvEMEoIa_eNwbnNr0jJQhkm2OWgdLKlVlLuQ47YkFwB5W1f-4r0wVQwpoUBA6ZSMOq-JluPQS_JBNGEouAH9JWN78L543VXoGRiOJ3oavJPvrYrzH_2dvpdxF-rg6-ScM92qiQrUjycneRt0uZDrYkXzZJ2Jce8ND0QN33dARTRKMJOKyRM2wxEI-n_z-_SR106Az2pWQ8wiMJhrSAfEeSfcqY9RGtXAXIbgWU66h72ChkGmSZ395HqwZmkl2feHY7ZFnAQdRN-cYjLmliErF7hKlU1BjMVzP7RvQVeJVV77AORkrH8bPSBD-aUFkgTdtx8TwUlgHOWyEzPnG7CQYp-a7OYfYRlAVA7n07KofRyFWoIb15uBw0vT5cWfr4AVjLqmRRw4vyv1Uf7HbyCiTOKnxFhlgRCVmwDtNqUkZpgeiZdBGapLKGnK77fHMgUG2F5ZfcAT1n_JsKqo8R3OSODpUgNwW6qRDIQe61BvQGgM3gvqvhF1LLu-PkcSL8UA7ed_x6IWks3ryvlIuRJLmSsI1rfwpvyCPLUeD_whLJNFmHZe47j3sUZCwDe6Nx4cmVg9XVb5n-ObOKsWpdnAYpdG2rkRRLLB9vkiCmz0doBs8CpwPWZgs5qWZe7RerIkmxvime29HIj_FKnDJqCV53qJPEEOma7uJXpGEzDoCmSZUWY0BfiZ3Yhk-DawWj5JybENzBDpWN-xcgKxGx-h9sqWj97Ra7qqhfPAmsLj8nZmAsbn91MNPvK5Kgb_Nmuc_8KQK7KtpmFCoAojoIGYxhdMVw7xxW3nda08OpLuEVRrHaZ9kjKS-0sFyF74-uI1ga6ENRjozaavH3LAoVhVzQfuM54PGIP_PtOJonFbEC7Khg')

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
DROPBOX_TOKEN = os.getenv('DROPBOX_TOKEN', 'sl.u.AGNEt4G4m38HBIG7pzvXkk_0g0_Biv4Yts26pjmPF-QLSYLzF-Q1_pdOIY5i_4O2z-aydejMaY1qoFDicw5uxUDS7isA3W-pFyEY113ZKaZECAv53VWK2RJ8ohKCQnyDT2cGwhaQnHxfpOjD-eSM7ru2WOBObn61ZmKxoBDxkPvJK6DEU9wsrOWHYBHMcM69mQxzw7lC9s2hQqJGdh6nGYvw5w_yYl8PAgJHpBWVhQZsfI6mj1R6mSCOtlYCpWj6aeaqxSTXHEvu_m4ewsVb6EFNQtp52cisWbBjKcF5cl32oL7_VddsOHtP3PSF_bt3F8w5JPZ-CoKAbrk45LIWv8BqXdveYqh3w6Y_rMtr_y8bmJ_s942TtM0cSn1ePxLJjyJvWbwIj90gBVQ22bJp4guH-_tBpCVIiD-Iv4Rj4NlNk_WIkBcJ-ixPK1LPHdiz_fFT0P6eqBZzOw_lxdp7bdA87eJv8w4MYP0hPadpLF1cyUEtye4zc50zfBIsykfVPxizb09p97xp1w_bdRLeJ1LjBTAWns7ub-d6NMa7vep2mkuHLkHdR9f_95QEqncnxvEMEoIa_eNwbnNr0jJQhkm2OWgdLKlVlLuQ47YkFwB5W1f-4r0wVQwpoUBA6ZSMOq-JluPQS_JBNGEouAH9JWN78L543VXoGRiOJ3oavJPvrYrzH_2dvpdxF-rg6-ScM92qiQrUjycneRt0uZDrYkXzZJ2Jce8ND0QN33dARTRKMJOKyRM2wxEI-n_z-_SR106Az2pWQ8wiMJhrSAfEeSfcqY9RGtXAXIbgWU66h72ChkGmSZ395HqwZmkl2feHY7ZFnAQdRN-cYjLmliErF7hKlU1BjMVzP7RvQVeJVV77AORkrH8bPSBD-aUFkgTdtx8TwUlgHOWyEzPnG7CQYp-a7OYfYRlAVA7n07KofRyFWoIb15uBw0vT5cWfr4AVjLqmRRw4vyv1Uf7HbyCiTOKnxFhlgRCVmwDtNqUkZpgeiZdBGapLKGnK77fHMgUG2F5ZfcAT1n_JsKqo8R3OSODpUgNwW6qRDIQe61BvQGgM3gvqvhF1LLu-PkcSL8UA7ed_x6IWks3ryvlIuRJLmSsI1rfwpvyCPLUeD_whLJNFmHZe47j3sUZCwDe6Nx4cmVg9XVb5n-ObOKsWpdnAYpdG2rkRRLLB9vkiCmz0doBs8CpwPWZgs5qWZe7RerIkmxvime29HIj_FKnDJqCV53qJPEEOma7uJXpGEzDoCmSZUWY0BfiZ3Yhk-DawWj5JybENzBDpWN-xcgKxGx-h9sqWj97Ra7qqhfPAmsLj8nZmAsbn91MNPvK5Kgb_Nmuc_8KQK7KtpmFCoAojoIGYxhdMVw7xxW3nda08OpLuEVRrHaZ9kjKS-0sFyF74-uI1ga6ENRjozaavH3LAoVhVzQfuM54PGIP_PtOJonFbEC7Khg')

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
