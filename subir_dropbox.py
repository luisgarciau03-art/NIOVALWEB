<<<<<<< HEAD
import dropbox
import os

# Token de acceso de Dropbox (se recomienda usar variable de entorno en producción)
DROPBOX_TOKEN = os.getenv('DROPBOX_TOKEN', 'sl.u.AGTs9-p-E0eVlr1yd2LJTciSrqwk9JISVEgKA0Uul_7SYCI79uUEEeLCCBXwaxuPA5KT1fJ5xTHI4kvLjjIDdg9foYwa54ya1LM3U7d-3Z3IlIYWTSQJPJuJOxlRh-sac1g7-IIG_9a-6EMmVkirACGSxfJiqhP625RudYfrpNP0TmGj6AYFHYh_quY9gz7edhE10jHZy5nMePPA8SvK4Q32R8bc04NbDpnBDEA9AiSLDTdEYLnEhd7RpxmqmKXbEmr52LrwiCBpK3azbnEiL1lnQcZu4fn5G-3Zq_wSJMPS1619oBwzpKquxDt4iHgsa6vFh4Q13KB7SMYjcb7-_-Xmhm766JU1sZbfZqkbt1tIMNhdceLDz8JuwHI8hUkm3iD7y2kDOKXVBVy1NhP9aNZeKKixl4RpxKPDmB5c3N1CtXedzGNws6FAR-s2APHIOBKttyU_XitSsuGdqXMDcxnDHqJgmLrvNPHPwbPEWPnzL0S1jzRVK6-t1mPFETIEyk1Ixjs6-CtYniMNYGYJG9CYuPr87coePZkvgMw8gwefSOOg-pi1DZvGdefM5CYxaKVbYxovz0NjhZB4J2J-c_9n1g5qWR9pJ3XiMe0cMy4myDvMu6T-lEKLstVMnQozTQOZFFzX2nmw2EmrZvjBF7Ulr0cOGo1Jx-c0R07KY-y2R_bVHGB5WwecMLW716XiybsFj3HgKeNsXEpjbaq3y33Fk8dJdv0_4nlWpiZiFg-Z6tTyUl1dSvYwmv0O4hgUfzi0hukrEqSlCIR-d8DqwqkgI5FnsGybfawiMI0EiuhHw_AGY6xLrJnUA1uLtLNqPyncpwh9nJwyTxEPYjUQ2u-O4xC7MTjNbJAqYQfnI-XSL433W8XI15XwxhypLdPuIm5YZUnlDm-ZDcDNtvpbb_leKOyS7NiBm1WqmdEAhpyjBGbZ-ptizkInYEvUA57X-dOisxwtu4ZOLEQV6DosI89cJ2_TlbZnhaeiHifyIjITrp53y7yVWW23-KcOVQezTrgomqzK9MFrCLtYU0vuowMiZJk9dKMgonPoCpPEDl9BqIBfcid2Qj0kCg0U8NPtUVB1fWGRBv9XWZABYn8_N6Xgni9J0AercscxgEEDV6uP3RFBL_tMdXu1ySOoobgP765je3Tb9r7c94VEW0f-NdWrAqh_orW4B2bdMGo_T6fuC7PlaLWRTTqp8vTdA8_MxNpBPazdfqvhtHjemNGN2yMNjAjW5okAiVZQWXZTW9G6DGJpIW8jmP8mTGPM-hKrpmD7RRNhoBsgUvyeaeF2OcTgiL1icwAf1Q9FTUTos3NZgkuSNUw3osFu-o5U6asIVsci6saBw6M1zVvSyvD-KmRHoykVl5VKv-COThfGSWT5IOSLm2PxHnjt17GW9R3fR5mNEGwRpyvTU8tBfyIjfYZ4TeQw0Hfdhl-oQRNzBwhH9g')

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
DROPBOX_TOKEN = os.getenv('DROPBOX_TOKEN', 'sl.u.AGTs9-p-E0eVlr1yd2LJTciSrqwk9JISVEgKA0Uul_7SYCI79uUEEeLCCBXwaxuPA5KT1fJ5xTHI4kvLjjIDdg9foYwa54ya1LM3U7d-3Z3IlIYWTSQJPJuJOxlRh-sac1g7-IIG_9a-6EMmVkirACGSxfJiqhP625RudYfrpNP0TmGj6AYFHYh_quY9gz7edhE10jHZy5nMePPA8SvK4Q32R8bc04NbDpnBDEA9AiSLDTdEYLnEhd7RpxmqmKXbEmr52LrwiCBpK3azbnEiL1lnQcZu4fn5G-3Zq_wSJMPS1619oBwzpKquxDt4iHgsa6vFh4Q13KB7SMYjcb7-_-Xmhm766JU1sZbfZqkbt1tIMNhdceLDz8JuwHI8hUkm3iD7y2kDOKXVBVy1NhP9aNZeKKixl4RpxKPDmB5c3N1CtXedzGNws6FAR-s2APHIOBKttyU_XitSsuGdqXMDcxnDHqJgmLrvNPHPwbPEWPnzL0S1jzRVK6-t1mPFETIEyk1Ixjs6-CtYniMNYGYJG9CYuPr87coePZkvgMw8gwefSOOg-pi1DZvGdefM5CYxaKVbYxovz0NjhZB4J2J-c_9n1g5qWR9pJ3XiMe0cMy4myDvMu6T-lEKLstVMnQozTQOZFFzX2nmw2EmrZvjBF7Ulr0cOGo1Jx-c0R07KY-y2R_bVHGB5WwecMLW716XiybsFj3HgKeNsXEpjbaq3y33Fk8dJdv0_4nlWpiZiFg-Z6tTyUl1dSvYwmv0O4hgUfzi0hukrEqSlCIR-d8DqwqkgI5FnsGybfawiMI0EiuhHw_AGY6xLrJnUA1uLtLNqPyncpwh9nJwyTxEPYjUQ2u-O4xC7MTjNbJAqYQfnI-XSL433W8XI15XwxhypLdPuIm5YZUnlDm-ZDcDNtvpbb_leKOyS7NiBm1WqmdEAhpyjBGbZ-ptizkInYEvUA57X-dOisxwtu4ZOLEQV6DosI89cJ2_TlbZnhaeiHifyIjITrp53y7yVWW23-KcOVQezTrgomqzK9MFrCLtYU0vuowMiZJk9dKMgonPoCpPEDl9BqIBfcid2Qj0kCg0U8NPtUVB1fWGRBv9XWZABYn8_N6Xgni9J0AercscxgEEDV6uP3RFBL_tMdXu1ySOoobgP765je3Tb9r7c94VEW0f-NdWrAqh_orW4B2bdMGo_T6fuC7PlaLWRTTqp8vTdA8_MxNpBPazdfqvhtHjemNGN2yMNjAjW5okAiVZQWXZTW9G6DGJpIW8jmP8mTGPM-hKrpmD7RRNhoBsgUvyeaeF2OcTgiL1icwAf1Q9FTUTos3NZgkuSNUw3osFu-o5U6asIVsci6saBw6M1zVvSyvD-KmRHoykVl5VKv-COThfGSWT5IOSLm2PxHnjt17GW9R3fR5mNEGwRpyvTU8tBfyIjfYZ4TeQw0Hfdhl-oQRNzBwhH9g')

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
