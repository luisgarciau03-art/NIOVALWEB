<<<<<<< HEAD
import dropbox
import os

# Token de acceso de Dropbox (se recomienda usar variable de entorno en producción)
DROPBOX_TOKEN = os.getenv('DROPBOX_TOKEN', 'sl.u.AGPNPtxIgi-Mgon0k2SII4n9r_B_ExcHwU66Kc_Oue8fHUM5q0MluBGSmmHsi2meGAU8c9qh8ZWGV-MGFlQ8VvCy5sDEr1lAzep5Hu7fJZ3idrxRBzufJaSeFLd2MMtjII8CagGFroZjCQ2uvMlcaE5nMaGLe9I6Jm-J1iYMYiVGwagpqeAI_f2ProE9D9Qr1v5PHOX4vORThXdtOssF55HkqsCc7tAjnRgVD1xxiGua7fftNPTcOgcrVq0jmETh17Bs4ZA8TzA3xuidPZAzWVfdPHnbL4X2OaXnHGyGNM4Kr9Y99xoYysNxnAz_tEq5vjJhxsD7hFnUUR6j6MaRzNfblnW6-PUeiwKRgQnZp_RyKfbXGbd3MDaydn5FaxQ6F2iN10EMtvNwQLX6q3j_U32a__IDyj0AKXHFxLSvHW9_b4PvxQhiC93Oe6t28e82dQZ2cXzTxitEOJ_V0nszMAU12A468Psu3lK2Mj3FhlKZbV8jUXKzWTRpXOVTrVCNRgt8Ix-nK_K75fceGov-27Gqeg9aVnhJ1As_jzZVyfTbp2zQmubM8O76MvqAESOsvCQFf-Xp55cIEd3Yc7K4cNWkFsDk1GAeXLA0p0sDXTG70k3Cao_AkllTtJBe1oaYIzv_WsiMaSl1mSGdap-SWzMbC2WIUDyqG6YI7uMpEl5OxByTB6tv0H7sSVv3MQZOQn58WL_ZZ5LdlUH0DYrnszREOFIEsd4RIz8xuEE6sjo_8hB38nCY4-Sv6j1TNETmf5zvD_H_GxTCTpZaUvqODmg0qO1X_XA8rqHMWNJscfj2H5vdn-1z0tfq3cBgxwYs5snlyzlIdgJnsNcf4xfSKJXGi304lS8bIL3MboNQy2dtDgk6P7EOT60zwt62C6Wk07BnAq0IiZEcLLJFijQyaJrSsIs8MrQK8tUer_TPlJVtrxi1qphVDD9ThfpvFo91Bx75Oihn5A5aeDWwUTqrBiGkiYoobSQgDsgP0l6pDbGXuzq2ncVCBJIJ_SWHVnka-r4qzumbLBry_3OOMn-Gj3bnS5OeWhC7xXQyB5Zm4sryEUposYKIOJBAdOK8eTLItUO0MXJc2zu5_PFywfhHQmKdgcz0543Klw8D0W6t_WBhKpVmE9WM0q79fRhxq-nRCyDd8vFSh1wiq1zSTcJkzjFpy_pi4LHxTqigZmE01D-CdOKVyNta6s3wY7AmBBqRAe70Hd3MkF30CGTbhw0kKWYzKnSwhUsECs38OV484Ns3oVkO9L-z88NTrA6vGjXDoD1Im1JjQ9eIuX4Fy_ZP2qkxp2UhIOLwtZSOCU0S25u387CDfTisaAibroCIQbQ7qaxFR3WPYX2VSq14Nl4TKOerom-j8Ukh3ywcDkl8zYDB4fnfW3FyzOGGW5faWhqPw7_uBM8tWFDXgZ1nNuZSvktLiX_M3sdS8C02ymId0H1E-w')

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
DROPBOX_TOKEN = os.getenv('DROPBOX_TOKEN', 'sl.u.AGPNPtxIgi-Mgon0k2SII4n9r_B_ExcHwU66Kc_Oue8fHUM5q0MluBGSmmHsi2meGAU8c9qh8ZWGV-MGFlQ8VvCy5sDEr1lAzep5Hu7fJZ3idrxRBzufJaSeFLd2MMtjII8CagGFroZjCQ2uvMlcaE5nMaGLe9I6Jm-J1iYMYiVGwagpqeAI_f2ProE9D9Qr1v5PHOX4vORThXdtOssF55HkqsCc7tAjnRgVD1xxiGua7fftNPTcOgcrVq0jmETh17Bs4ZA8TzA3xuidPZAzWVfdPHnbL4X2OaXnHGyGNM4Kr9Y99xoYysNxnAz_tEq5vjJhxsD7hFnUUR6j6MaRzNfblnW6-PUeiwKRgQnZp_RyKfbXGbd3MDaydn5FaxQ6F2iN10EMtvNwQLX6q3j_U32a__IDyj0AKXHFxLSvHW9_b4PvxQhiC93Oe6t28e82dQZ2cXzTxitEOJ_V0nszMAU12A468Psu3lK2Mj3FhlKZbV8jUXKzWTRpXOVTrVCNRgt8Ix-nK_K75fceGov-27Gqeg9aVnhJ1As_jzZVyfTbp2zQmubM8O76MvqAESOsvCQFf-Xp55cIEd3Yc7K4cNWkFsDk1GAeXLA0p0sDXTG70k3Cao_AkllTtJBe1oaYIzv_WsiMaSl1mSGdap-SWzMbC2WIUDyqG6YI7uMpEl5OxByTB6tv0H7sSVv3MQZOQn58WL_ZZ5LdlUH0DYrnszREOFIEsd4RIz8xuEE6sjo_8hB38nCY4-Sv6j1TNETmf5zvD_H_GxTCTpZaUvqODmg0qO1X_XA8rqHMWNJscfj2H5vdn-1z0tfq3cBgxwYs5snlyzlIdgJnsNcf4xfSKJXGi304lS8bIL3MboNQy2dtDgk6P7EOT60zwt62C6Wk07BnAq0IiZEcLLJFijQyaJrSsIs8MrQK8tUer_TPlJVtrxi1qphVDD9ThfpvFo91Bx75Oihn5A5aeDWwUTqrBiGkiYoobSQgDsgP0l6pDbGXuzq2ncVCBJIJ_SWHVnka-r4qzumbLBry_3OOMn-Gj3bnS5OeWhC7xXQyB5Zm4sryEUposYKIOJBAdOK8eTLItUO0MXJc2zu5_PFywfhHQmKdgcz0543Klw8D0W6t_WBhKpVmE9WM0q79fRhxq-nRCyDd8vFSh1wiq1zSTcJkzjFpy_pi4LHxTqigZmE01D-CdOKVyNta6s3wY7AmBBqRAe70Hd3MkF30CGTbhw0kKWYzKnSwhUsECs38OV484Ns3oVkO9L-z88NTrA6vGjXDoD1Im1JjQ9eIuX4Fy_ZP2qkxp2UhIOLwtZSOCU0S25u387CDfTisaAibroCIQbQ7qaxFR3WPYX2VSq14Nl4TKOerom-j8Ukh3ywcDkl8zYDB4fnfW3FyzOGGW5faWhqPw7_uBM8tWFDXgZ1nNuZSvktLiX_M3sdS8C02ymId0H1E-w')

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
