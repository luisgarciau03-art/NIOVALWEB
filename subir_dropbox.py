<<<<<<< HEAD
import dropbox
import os

# Token de acceso de Dropbox (se recomienda usar variable de entorno en producción)
DROPBOX_TOKEN = os.getenv('DROPBOX_TOKEN', 'sl.u.AGO7dvrwXeIcuDTs4elzNx-ZI8XsgHlir6qYA3-pKtIb5yIm0WuSm0qZM9NbO86v51xvKm4pL7Z7cdzNpbW3kmcpAPdQOJXC26_ePuvCJyRbxKQKm4JlhOq0HpwHzOVVehWOfpsEYrpUAgoCoVsZrLZwsPsQ4e70kWvWeDC3aNkjPaRMJczCFKEk5IakHjKK8kZvLWX0yjjzH4q8S4FSGO7K8zBrcf_n357sOEM9R0E0LU63B6mX-Bj6tH_CnE10sPWfozeMiXZ0oIl1VEuB4CBGWrDB6Hit0hOgJdLCLAIF2THgWJd7khLESzbCnbBqnJAI8VxlkO87185KlwLUhUGy-VTlq2yW_viCDosgdn3vnBub19DUrVlNtxI7nj_facaJtMXy2H6E6TrPZRqbXZpIPpaQknUoQdAvXgQoyqMv8GV0ZrfB7QncMJ8CE2ZrK8NN6i5z4Rs_VgFAnmadEAOmcVKnYYCLBp6ClIDEuOplwm12U3L27TlWn69NCaTGN__1XjvaTp-83CA95L7UmqMdZyp0vOdkLNhLoXiqhnp-ywNwFCodI_nm78jEX5qnBlmQGm6pvp0TBLp3_GX7dEZ0feBbGhTkXNR_ZGF1edd_2NxD-U1FOE85VChp_9GxSgfleE-6dydLXYAgQN7qWumR3uBuSRzxbLOCK6oieMaS6cRghcURl-bZds-zBP0hDTs6rziEPa2Q0eUo5PZIlifKCp2GbvDG6I5KEUbKJP4ic_NeK8szn_VyLKYHVp_nrKIKYMx7Gz951DsZR53DxeLLBF7DBhy39OUMwSIEv47KBVQmfKY3c6SwgGhuBoQDQVHHk3cUicEk_h4V1mKq5EFQ4IyjNVe5WS7W3qsnEAh_8QU5YAXAc-FdeTBvDWhOLwAE7GkMtVKgEU6M8FsuxyrODuWDpZlMhUcod5Ao5EbbjkcgT9Ajo13jg22mldNywTdpAaWARfGILySGB2u9UT2d8f23Ew1XydQn7dlKo3ZvictioD49kpEREBy9e0bHyz1WyH9Xf7uc3mpe6OhSQHZ3Od6fG8GHd0E7zpcghGu2rL2xN5vTi0nXlAwqWBUVHgzhl5z6CzQ0GtRyo9_2oRxgc-nnbwKXtGhDnuehE6MjAFeWlmBHD1U7SNpXh8Le0wp_vcPwzMEaSfv5WQdZ9JgewHi_3gQKpxGsJMLUaLgVaR62ELu8vY44MzfalflvFIHukpgQwh-vN1mlfNkahWuMgGhQW-vrn0fUidzmVJMM2QT4mXjuvyyE1l8yr09UxJxVh5-rI_31QtPGNnqFjjTONUlgNhFXGAUYJDdjDBscckMHGZMIKhHDRveUver8ihNp-SwJ5OWdozTYr8nkeZJWPIgeK3BcySWlEtaZY-DsELkbRfdA-BbaMWzJJA6rLlgCYUevKVOPkX7gPK4UzMDXVmnOqjUQ41Tpbvf5uFXK5g')

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
DROPBOX_TOKEN = os.getenv('DROPBOX_TOKEN', 'sl.u.AGO7dvrwXeIcuDTs4elzNx-ZI8XsgHlir6qYA3-pKtIb5yIm0WuSm0qZM9NbO86v51xvKm4pL7Z7cdzNpbW3kmcpAPdQOJXC26_ePuvCJyRbxKQKm4JlhOq0HpwHzOVVehWOfpsEYrpUAgoCoVsZrLZwsPsQ4e70kWvWeDC3aNkjPaRMJczCFKEk5IakHjKK8kZvLWX0yjjzH4q8S4FSGO7K8zBrcf_n357sOEM9R0E0LU63B6mX-Bj6tH_CnE10sPWfozeMiXZ0oIl1VEuB4CBGWrDB6Hit0hOgJdLCLAIF2THgWJd7khLESzbCnbBqnJAI8VxlkO87185KlwLUhUGy-VTlq2yW_viCDosgdn3vnBub19DUrVlNtxI7nj_facaJtMXy2H6E6TrPZRqbXZpIPpaQknUoQdAvXgQoyqMv8GV0ZrfB7QncMJ8CE2ZrK8NN6i5z4Rs_VgFAnmadEAOmcVKnYYCLBp6ClIDEuOplwm12U3L27TlWn69NCaTGN__1XjvaTp-83CA95L7UmqMdZyp0vOdkLNhLoXiqhnp-ywNwFCodI_nm78jEX5qnBlmQGm6pvp0TBLp3_GX7dEZ0feBbGhTkXNR_ZGF1edd_2NxD-U1FOE85VChp_9GxSgfleE-6dydLXYAgQN7qWumR3uBuSRzxbLOCK6oieMaS6cRghcURl-bZds-zBP0hDTs6rziEPa2Q0eUo5PZIlifKCp2GbvDG6I5KEUbKJP4ic_NeK8szn_VyLKYHVp_nrKIKYMx7Gz951DsZR53DxeLLBF7DBhy39OUMwSIEv47KBVQmfKY3c6SwgGhuBoQDQVHHk3cUicEk_h4V1mKq5EFQ4IyjNVe5WS7W3qsnEAh_8QU5YAXAc-FdeTBvDWhOLwAE7GkMtVKgEU6M8FsuxyrODuWDpZlMhUcod5Ao5EbbjkcgT9Ajo13jg22mldNywTdpAaWARfGILySGB2u9UT2d8f23Ew1XydQn7dlKo3ZvictioD49kpEREBy9e0bHyz1WyH9Xf7uc3mpe6OhSQHZ3Od6fG8GHd0E7zpcghGu2rL2xN5vTi0nXlAwqWBUVHgzhl5z6CzQ0GtRyo9_2oRxgc-nnbwKXtGhDnuehE6MjAFeWlmBHD1U7SNpXh8Le0wp_vcPwzMEaSfv5WQdZ9JgewHi_3gQKpxGsJMLUaLgVaR62ELu8vY44MzfalflvFIHukpgQwh-vN1mlfNkahWuMgGhQW-vrn0fUidzmVJMM2QT4mXjuvyyE1l8yr09UxJxVh5-rI_31QtPGNnqFjjTONUlgNhFXGAUYJDdjDBscckMHGZMIKhHDRveUver8ihNp-SwJ5OWdozTYr8nkeZJWPIgeK3BcySWlEtaZY-DsELkbRfdA-BbaMWzJJA6rLlgCYUevKVOPkX7gPK4UzMDXVmnOqjUQ41Tpbvf5uFXK5g')

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
