<<<<<<< HEAD
import dropbox
import os

# Token de acceso de Dropbox (se recomienda usar variable de entorno en producción)
DROPBOX_TOKEN = os.getenv('DROPBOX_TOKEN', 'sl.u.AGP-RzwRkzj4QvsFffgn3FDYgB4aUEOjtb5b7g2_Qt_JAnsj6vKQT0EZRUvQD0OAjCuXZNqolgEkZG7wKfdibgfbls5dUyXpISOs1DLQBUd6kDsxsGeDBAt62a99vssZVfg8Zc7FuSKD3ZG9dmQPB_VmGEA1vQJgZEhz0lA2e58bYyXXVWUYKhsMr9xk1HId084DmU-cIBAeIyUpgx7F7CsIfCzIO6N8F2pr5kmQMqO-HDT2qzBkNlB1nLd1ThS_HmzlsQQA2Kx5M0o-gHLE4CDhWRC84Z9vWBiBKufNlDv9qUUQVoVEzXyt8DPq617zcs10J9KUUJQngjd3VQ7TriTlO2FOI9Qj_MPUxmNOePxkJNxRyVefme83CymWBEJ_6tUkkNkyGKaSSPNUU0dG9vpQZZNrhS0m2mb3kMDB0-QeqfHhdnv4Ak1_zLl9eg-69DDuBYrZvb7B-_aqT-F5ZSBkcqYWWf78sDGfBWmlx69hXObf0qk0J4qHozS3AIz-DHo4Y98nK8GI9KxJtZyBpv98dP-AB4igwmbe2OUTQeARs-MlieGi0twvle4TOdj2jIi7BKwUtflHyi-7nHf1A40eas0fhbvWFwbw8eOXZOlqrWGkPheWsL-x1LMZQafKEBHTd1-2VI3r--929qDeBgus8-O2TOsIfs39UKeusBpTLTErpCidw8aueNbz_zm6apj_x2poCZqc65MSJl7Okw2QAlRqs1Zyt6mccFpkH9Y8hADAiH78EdbIX_KtbfLR4sHZwQ8hZfEz0EVHgMtWtRkxponX86bASBZNkDEB9w4AhLjfBzJdtOocPVsicQoSqhDUSyM5qJxoSjOIrdIjsySTbDpqsvJCLZAcadm15UFpYtlVolPIUfXosWfGHHOWmrzxoWTXIiWUifJaaOhmYEdF6rGCEyOuoediAOi7tO71-TSZw38rxMPAw4lt3FubKiTCvxE0argA5FXyeM4Vrtz9KXNIkQwFnGN77cA5L12tWOV5NFKhu2FsIYPAWu6Iode64AinFuj0XK7lTudJgLG8FfppCEAwAeUfHP-qvhTMW-1JrI3UQN8fjXjpwUGc6zT6SyNhdqHdhgtCK3VQX00G6UQfNs3E_y7nYh0L6rjBc87WUtOgiiTuG3PMiTT5HX0YYqVLcxF0ko7aWzwKhdskAOWQBU_quim71LkDmz6YbZm_H3aqIYdcuz-Y3QKKG58k1ejTl_CK9n8XUX_xipoQ9YPRsbZXoTN9d_aDVNccTIXRVp4SrTrhek32OblRVCgmfIuiqggiQzPwCSQ_ABGrtBrj-LtzuTzLYHW9dQf9z3tkUT1L68RJNhjzVfbQf04IqwKoXn38nskPCU9uJoOcDumwijiDEmg7eYqc48hgikAG-eHTbuz_uBxQ6q2E62vsU-5WOiP014eD69_YrHfHo4HNLdCBxxXXDqw-7c-xxg')

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
DROPBOX_TOKEN = os.getenv('DROPBOX_TOKEN', 'sl.u.AGP-RzwRkzj4QvsFffgn3FDYgB4aUEOjtb5b7g2_Qt_JAnsj6vKQT0EZRUvQD0OAjCuXZNqolgEkZG7wKfdibgfbls5dUyXpISOs1DLQBUd6kDsxsGeDBAt62a99vssZVfg8Zc7FuSKD3ZG9dmQPB_VmGEA1vQJgZEhz0lA2e58bYyXXVWUYKhsMr9xk1HId084DmU-cIBAeIyUpgx7F7CsIfCzIO6N8F2pr5kmQMqO-HDT2qzBkNlB1nLd1ThS_HmzlsQQA2Kx5M0o-gHLE4CDhWRC84Z9vWBiBKufNlDv9qUUQVoVEzXyt8DPq617zcs10J9KUUJQngjd3VQ7TriTlO2FOI9Qj_MPUxmNOePxkJNxRyVefme83CymWBEJ_6tUkkNkyGKaSSPNUU0dG9vpQZZNrhS0m2mb3kMDB0-QeqfHhdnv4Ak1_zLl9eg-69DDuBYrZvb7B-_aqT-F5ZSBkcqYWWf78sDGfBWmlx69hXObf0qk0J4qHozS3AIz-DHo4Y98nK8GI9KxJtZyBpv98dP-AB4igwmbe2OUTQeARs-MlieGi0twvle4TOdj2jIi7BKwUtflHyi-7nHf1A40eas0fhbvWFwbw8eOXZOlqrWGkPheWsL-x1LMZQafKEBHTd1-2VI3r--929qDeBgus8-O2TOsIfs39UKeusBpTLTErpCidw8aueNbz_zm6apj_x2poCZqc65MSJl7Okw2QAlRqs1Zyt6mccFpkH9Y8hADAiH78EdbIX_KtbfLR4sHZwQ8hZfEz0EVHgMtWtRkxponX86bASBZNkDEB9w4AhLjfBzJdtOocPVsicQoSqhDUSyM5qJxoSjOIrdIjsySTbDpqsvJCLZAcadm15UFpYtlVolPIUfXosWfGHHOWmrzxoWTXIiWUifJaaOhmYEdF6rGCEyOuoediAOi7tO71-TSZw38rxMPAw4lt3FubKiTCvxE0argA5FXyeM4Vrtz9KXNIkQwFnGN77cA5L12tWOV5NFKhu2FsIYPAWu6Iode64AinFuj0XK7lTudJgLG8FfppCEAwAeUfHP-qvhTMW-1JrI3UQN8fjXjpwUGc6zT6SyNhdqHdhgtCK3VQX00G6UQfNs3E_y7nYh0L6rjBc87WUtOgiiTuG3PMiTT5HX0YYqVLcxF0ko7aWzwKhdskAOWQBU_quim71LkDmz6YbZm_H3aqIYdcuz-Y3QKKG58k1ejTl_CK9n8XUX_xipoQ9YPRsbZXoTN9d_aDVNccTIXRVp4SrTrhek32OblRVCgmfIuiqggiQzPwCSQ_ABGrtBrj-LtzuTzLYHW9dQf9z3tkUT1L68RJNhjzVfbQf04IqwKoXn38nskPCU9uJoOcDumwijiDEmg7eYqc48hgikAG-eHTbuz_uBxQ6q2E62vsU-5WOiP014eD69_YrHfHo4HNLdCBxxXXDqw-7c-xxg')

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
