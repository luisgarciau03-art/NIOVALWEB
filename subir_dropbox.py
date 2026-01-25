<<<<<<< HEAD
import dropbox
import os

# Token de acceso de Dropbox (se recomienda usar variable de entorno en producción)
DROPBOX_TOKEN = os.getenv('DROPBOX_TOKEN', 'sl.u.AGT8P0Q4HLt5rLfsFxcMrWD4Wd1qjQZ1nJppetokuqIn8Re2JhElJkJkyQArymKp6vASCdpU0hpW41spotW__Cx67IJ6wySSESyT1jhmEoW_xYzxvwDEE-WdeXsV6oJm9vzReHsFe_XceDNEx2oD0oG2pvzgZtdLO_3gCvz7YXmh1jEhQ8V5WTokWz8EUl_Y4LmPbmjn1hswB0Tj39eJJ1Ff_pL0WsvtY3d5VuXW68olB29KZl4iUwCL96fjlDYAPMxIdybCsBuXJzHafI5Ft5sDfj29kEV4JqeVLZkKPVqTO29aAYvxPOz7AlU_qB5xqu3vqnyd_UKobEPBQFFMkwj4-k6nscGP1cwQ1rHumT5VCmmaQAFJ3et0Sbe9Ui0QV9n7tHnC6GlmEu7V-M0oP58E2FiQZank29evwG014HaYXgTZK4GP9u1XD973E_3Q118b8Nr3UWX9KKWuzzL8XlbjigreogKJbaRVx_CpgcALAIwfJVj-JfXp4TYOMZQlDzCgtSotjwIPPLEavgfsHdfh8wHH9x0s4mJCrT_cUU1whHfCHol1LTfhqoh4Z6NX5sqUVVgjNd5uG1N3dHnaOH_V2nfwPr2m_z6UR-ku7VjX_IfLvKeYpGe-UmVn0o8DY40ZY6XEQV_iZdszvyxfJg1NzdSHS3Aug7g2UCHLsbSN_lSO6f8YVTO0emyOvJmgjEEDnSVdB2sekyll4ckxXdYiWRVgbEg6-RNUWIsOr9Nkq0BYkKZL_mIxz6VD9mEBsG8-FOlAtnOuPIyFVpEV1XcmtBsRBnXVruRvoVT8Jt7XGzfUg0Jiw-Pa1krSHnQ9TA4NVShU_Q8fHeKXZQkMU449OLEuP-i8qiAoGvzeaAjBoAcwKxPiuL4cECOeoZFzTegmkdFWFd4ZlaxrObPcV3bn--cbsa_-v6VnHGJOzBYVVk8qSmayVT7dnmiLe2dg4j4EaG0fmCkHn_vF1Zr2KOBfzqj5zjSxgEfYBgG3LgxECydKnkEr4Hf8q_dsTjOgU-rDLKSzA_NgDwPTM5nPD-t1L1VtReyHBZvKK_UbzJOQ5pl3qSulARk6Tw4-WMAOOIbK1vzNMsTd8p_uKTKBa3VhjykVd4WHdkgDZiUD5xjyfCiAyE040K26m7h9Xzsk7nkhvlNet6CjQ6tDwkv3ES5p0deT5MLwFY__wh-W9akbateeuVfPK8OcKU4UkF6OVn24b54aEPOqAJbR9pwA9TFvRYOpjqR4_HKyVjGxtLD6VCqhm1EDymrgW6XW8I9RAii7OHEeT1MkT9ACFwTB-4u2xzu5e44AdXtHAlL29xr2jtxaf7VmS2p2gkgJl1NyMIAILWQ6ZUiCFYixQEOjwzS3-YNtnLWyWN3cpG2MM6UAUIAldhWP66TmXQ4cb1xqFQK-pY3BpMrUEbKmEQR0HcEn1csM9LaI8MR8xzTgl-FzPw')

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
DROPBOX_TOKEN = os.getenv('DROPBOX_TOKEN', 'sl.u.AGT8P0Q4HLt5rLfsFxcMrWD4Wd1qjQZ1nJppetokuqIn8Re2JhElJkJkyQArymKp6vASCdpU0hpW41spotW__Cx67IJ6wySSESyT1jhmEoW_xYzxvwDEE-WdeXsV6oJm9vzReHsFe_XceDNEx2oD0oG2pvzgZtdLO_3gCvz7YXmh1jEhQ8V5WTokWz8EUl_Y4LmPbmjn1hswB0Tj39eJJ1Ff_pL0WsvtY3d5VuXW68olB29KZl4iUwCL96fjlDYAPMxIdybCsBuXJzHafI5Ft5sDfj29kEV4JqeVLZkKPVqTO29aAYvxPOz7AlU_qB5xqu3vqnyd_UKobEPBQFFMkwj4-k6nscGP1cwQ1rHumT5VCmmaQAFJ3et0Sbe9Ui0QV9n7tHnC6GlmEu7V-M0oP58E2FiQZank29evwG014HaYXgTZK4GP9u1XD973E_3Q118b8Nr3UWX9KKWuzzL8XlbjigreogKJbaRVx_CpgcALAIwfJVj-JfXp4TYOMZQlDzCgtSotjwIPPLEavgfsHdfh8wHH9x0s4mJCrT_cUU1whHfCHol1LTfhqoh4Z6NX5sqUVVgjNd5uG1N3dHnaOH_V2nfwPr2m_z6UR-ku7VjX_IfLvKeYpGe-UmVn0o8DY40ZY6XEQV_iZdszvyxfJg1NzdSHS3Aug7g2UCHLsbSN_lSO6f8YVTO0emyOvJmgjEEDnSVdB2sekyll4ckxXdYiWRVgbEg6-RNUWIsOr9Nkq0BYkKZL_mIxz6VD9mEBsG8-FOlAtnOuPIyFVpEV1XcmtBsRBnXVruRvoVT8Jt7XGzfUg0Jiw-Pa1krSHnQ9TA4NVShU_Q8fHeKXZQkMU449OLEuP-i8qiAoGvzeaAjBoAcwKxPiuL4cECOeoZFzTegmkdFWFd4ZlaxrObPcV3bn--cbsa_-v6VnHGJOzBYVVk8qSmayVT7dnmiLe2dg4j4EaG0fmCkHn_vF1Zr2KOBfzqj5zjSxgEfYBgG3LgxECydKnkEr4Hf8q_dsTjOgU-rDLKSzA_NgDwPTM5nPD-t1L1VtReyHBZvKK_UbzJOQ5pl3qSulARk6Tw4-WMAOOIbK1vzNMsTd8p_uKTKBa3VhjykVd4WHdkgDZiUD5xjyfCiAyE040K26m7h9Xzsk7nkhvlNet6CjQ6tDwkv3ES5p0deT5MLwFY__wh-W9akbateeuVfPK8OcKU4UkF6OVn24b54aEPOqAJbR9pwA9TFvRYOpjqR4_HKyVjGxtLD6VCqhm1EDymrgW6XW8I9RAii7OHEeT1MkT9ACFwTB-4u2xzu5e44AdXtHAlL29xr2jtxaf7VmS2p2gkgJl1NyMIAILWQ6ZUiCFYixQEOjwzS3-YNtnLWyWN3cpG2MM6UAUIAldhWP66TmXQ4cb1xqFQK-pY3BpMrUEbKmEQR0HcEn1csM9LaI8MR8xzTgl-FzPw')

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
