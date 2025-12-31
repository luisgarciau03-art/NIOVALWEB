<<<<<<< HEAD
import dropbox
import os

# Token de acceso de Dropbox (se recomienda usar variable de entorno en producción)
DROPBOX_TOKEN = os.getenv('DROPBOX_TOKEN', 'sl.u.AGNf4e3nQL6bFqDSK3tqwBQoA5S-8r8CaHtWWUWrL1Y5GSmidRlVu5vK9nG3C9Q6G7KYlv45-KClOfruu4esj92L0HB_1RYWTz1LWQZoQtJ3GgDSXx8DaCZ3_Jh4-cpVrFfbId9mOgjbTG566X0D8fyFx7OOpUn_BuZPNu9r6s0Edit4p1fmMCez3Ges5EM60NmAtwP6UjGmEHfEMGv63Iv2VkMtAAvPwvL4_m771qNj36tO57DXicAooWfMIHlo6cu33nRbBO05zp6PeHIY12ShYtku6s29rtOSQXB5yfFuhH2s_JDjWaintoeLAhqkK-3ufjKuZjTKjTzKFPXTCPZU-FDQPvqnIT0bxZcCtDctelwvVdcs7ZC6bkdTw1TLwI6th4sNfG4mE9KytDA5_kQQMQwaQXBv9AKKpslbW2xdNiB7Jyo3zS6npA9d_i8iMshwJL8O9Nx2LEq1hCPawarrUGJpwuMVvp4SUVZXKwupzX6mww57WGR2Qycf7vDkwtBmyzeXxA1d7ZGJmamdA4Y50nI6cg-ctGgkOIH7D26RKIlLbf_DnREGc874QWoARipe-bBGM6iyEWvLD8ld_J-wdYmQQl3mrJ1eTG9E8Gf8AGvr5Bgq_-Ww_STMiSSD81kab1CO9lSyJXPCzHA_mZnnpPpOFcsyCWiM3WiOkVhOfOr46ITKuEJSe5nhGYiD5126BmS-zz10HtEf2JhciX_HFNeyXU7LGPFrhNZlVu1105SxdcLrzGDClpbcfhhbZmkQfvMnYpsA03VrlD_-IHW4mU5Hd0spd8hWxgoq3OY-FAXEGrziRGTLD0cIXr_a0inQW7kgAys1bOH6EB59m6yFU1LyUcUfp_Lp_wHceCtLmLQdGD-j9a6Fmge9oZszpvrhmZJtKCBYiYjyn8BXQW06H9Qm6huZ6Vmf2zDRO02yrTT2E37RS1b65qTaIpt9jAAE6l9GY9cTt8sxUsCZq8bXz_ilOXw_7sj6MegitJV7S4tK8GPheaYb74D3demhZM6xaJQeoIka5k9_BEJVCLBgh8MwxGAc9C-Tfs8RJaO6ZSNEcYLmNfxxCqj1Qt0H44JjEDq1E2BNS_tDXlNxaOIUaZcj1qq3LITxJXwARg4JyBiD_eb6-pbye5lY4nGxh9Txe-cSQQbfsIBMMP9GB82jq2f1HrH5ybrbk3ezotEEYVuww0JuXmU_u-K5zLnyFu-yx4i6L1pVjSQtuk_eRgwkqMEiilcj4I-vN5whXtV0fGow0FywWAWKiRWPllR9hB5yt7vFPFdv26jeBVTcH0a3phy5vErGcn6EGtjAYMj9Itazj1qfj3atyXdYnUk4gtCkf6gnKDA7mMl_ZFw3oIGct-MErTC81yqVp9kCGlZCDXQ7KbbkMo7xQycun7dldouTzrqYFGxLlZiYzSyLwfCxcKuP7htr9JGitnK454i_yg+')

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
DROPBOX_TOKEN = os.getenv('DROPBOX_TOKEN', 'sl.u.AGNf4e3nQL6bFqDSK3tqwBQoA5S-8r8CaHtWWUWrL1Y5GSmidRlVu5vK9nG3C9Q6G7KYlv45-KClOfruu4esj92L0HB_1RYWTz1LWQZoQtJ3GgDSXx8DaCZ3_Jh4-cpVrFfbId9mOgjbTG566X0D8fyFx7OOpUn_BuZPNu9r6s0Edit4p1fmMCez3Ges5EM60NmAtwP6UjGmEHfEMGv63Iv2VkMtAAvPwvL4_m771qNj36tO57DXicAooWfMIHlo6cu33nRbBO05zp6PeHIY12ShYtku6s29rtOSQXB5yfFuhH2s_JDjWaintoeLAhqkK-3ufjKuZjTKjTzKFPXTCPZU-FDQPvqnIT0bxZcCtDctelwvVdcs7ZC6bkdTw1TLwI6th4sNfG4mE9KytDA5_kQQMQwaQXBv9AKKpslbW2xdNiB7Jyo3zS6npA9d_i8iMshwJL8O9Nx2LEq1hCPawarrUGJpwuMVvp4SUVZXKwupzX6mww57WGR2Qycf7vDkwtBmyzeXxA1d7ZGJmamdA4Y50nI6cg-ctGgkOIH7D26RKIlLbf_DnREGc874QWoARipe-bBGM6iyEWvLD8ld_J-wdYmQQl3mrJ1eTG9E8Gf8AGvr5Bgq_-Ww_STMiSSD81kab1CO9lSyJXPCzHA_mZnnpPpOFcsyCWiM3WiOkVhOfOr46ITKuEJSe5nhGYiD5126BmS-zz10HtEf2JhciX_HFNeyXU7LGPFrhNZlVu1105SxdcLrzGDClpbcfhhbZmkQfvMnYpsA03VrlD_-IHW4mU5Hd0spd8hWxgoq3OY-FAXEGrziRGTLD0cIXr_a0inQW7kgAys1bOH6EB59m6yFU1LyUcUfp_Lp_wHceCtLmLQdGD-j9a6Fmge9oZszpvrhmZJtKCBYiYjyn8BXQW06H9Qm6huZ6Vmf2zDRO02yrTT2E37RS1b65qTaIpt9jAAE6l9GY9cTt8sxUsCZq8bXz_ilOXw_7sj6MegitJV7S4tK8GPheaYb74D3demhZM6xaJQeoIka5k9_BEJVCLBgh8MwxGAc9C-Tfs8RJaO6ZSNEcYLmNfxxCqj1Qt0H44JjEDq1E2BNS_tDXlNxaOIUaZcj1qq3LITxJXwARg4JyBiD_eb6-pbye5lY4nGxh9Txe-cSQQbfsIBMMP9GB82jq2f1HrH5ybrbk3ezotEEYVuww0JuXmU_u-K5zLnyFu-yx4i6L1pVjSQtuk_eRgwkqMEiilcj4I-vN5whXtV0fGow0FywWAWKiRWPllR9hB5yt7vFPFdv26jeBVTcH0a3phy5vErGcn6EGtjAYMj9Itazj1qfj3atyXdYnUk4gtCkf6gnKDA7mMl_ZFw3oIGct-MErTC81yqVp9kCGlZCDXQ7KbbkMo7xQycun7dldouTzrqYFGxLlZiYzSyLwfCxcKuP7htr9JGitnK454i_yg+')

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
