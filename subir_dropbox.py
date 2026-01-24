<<<<<<< HEAD
import dropbox
import os

# Token de acceso de Dropbox (se recomienda usar variable de entorno en producción)
DROPBOX_TOKEN = os.getenv('DROPBOX_TOKEN', 'sl.u.AGRC-J8ydRqjvsn_MlLg4eXcYOPj5oGRrT_kRfCCCi7aPp-i-sivgDiJrR-sXqPoFcWd-f296y77YWBU1hXnKCqf5nU3I_DF5W5Wes81AAIDRIS3OhSKA2AW-MVWT0lXrE-rrerT5xgEBdFFWXzcFIkanHfmqn6mLZvpaHoxd4Jbh-6nuf355KkQTu3A86smZn97Unhg1rDCFyidnG8lP9vhaySmIeW7VTuK2E7DoOOFiu5bIurQmCLC2WdVMtCjEj0ad4YZGnW46AuVpavIN4XeXP6sIKJzoBbcVdVf9vxzgr5FvjdYCRT6NfyPlSJa2N6ZfaxFQxgMVeO09tDWwzWZJRHLKqv02IKVGfx9vVmXOqswhdjxQIYOpSw3gG6s31f-ejNamEP7SUDU9ZIiASlY38VqU6Rb0XPLIT5f7eWAysJLsa8TNzkgsWq90xjcyf5cUWfmsOEEKaZ5trKMtUBggQ3IKRaF9E8293ezn5mVfCqUSWDcFFI__KZFy2OzRWo3VA-hNECQlsdJeCs9DTWmAeg41o5owJq0SVwN8Wlre0vb6dllKx_HA5pZQGXR8jrWDBNpHCmMKEFSJVgeMdbynUKwislLNN7fXFw9elbgOD2kEfxDJlv2gvsXvJc_h9lNV44EnVBeGAZLRnsZNi6-s0j7MayjQGXynW5DDg2PgeK_vrdrVzY1RVvyF272CnJ2-c-pByqotraa6_yhLympRxyduWgQAT_z5FcMKW7_icvSNe7YrTMb_vBJ7IxorGEmQ3j9NAlpYFpET8dFBMkCn0tLln7bPA9cEPbG2VsygiAVsgbx-A3PJnLSvbeilCkA3pjPA688heDQUtOC7QP0XKZyAnKT6CHRQuE0VHDhbaePjGW5XknoT7jifvIY3ROyYA-tIBTq8JslEm2cBRSUnev-vnNcFTptABB_Za8AW4FDn3A7uWG56P8RqqaRzjRLbIv7fjo9zcyo5AOwJN_WGkgVenDveJYVcrYKfYm2Sj1t7La6ZYzrXMoqc_4BOa8B0MsRv0TV9HTq0c1JXc1pNoICXVTImxTC6C9F8vEz5BEiO9jzGgPIeOjSuE0rdTEKtutHzVRXLHlS5IDCXGZvTjb8_b7yfg-8sCi00FU5Fw9sM6AEYlEN5A5Gw_8H-vMiHrnmVdjpwjR9_XENvQd0p5g1Z9MLTirQ0EcLbCeRQJs-PoIlRTzIdmJILNjUWw6kGybqPbvuSggk9GgnNEg8Cjron06mCzRCDEwuTRci1o-Qy4cg7cGjdWS3bXUC9Q_JACsQIFbefJ7IzGfIUOjeNgI-x_ltPZ4maij_UAVKQP-FNH1BZJI6SiaI3Y3P7gceDIABSrg_42poBUPTiHva5gQvAkPV1K06MNm5Z5GnvpUt9xZYwnZErK1gFdMy3hcY9rBz3pdjGbVukQvVxsMJcj6G0x2Z-mdQpNDRDIyxPQ')

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
DROPBOX_TOKEN = os.getenv('DROPBOX_TOKEN', 'sl.u.AGRC-J8ydRqjvsn_MlLg4eXcYOPj5oGRrT_kRfCCCi7aPp-i-sivgDiJrR-sXqPoFcWd-f296y77YWBU1hXnKCqf5nU3I_DF5W5Wes81AAIDRIS3OhSKA2AW-MVWT0lXrE-rrerT5xgEBdFFWXzcFIkanHfmqn6mLZvpaHoxd4Jbh-6nuf355KkQTu3A86smZn97Unhg1rDCFyidnG8lP9vhaySmIeW7VTuK2E7DoOOFiu5bIurQmCLC2WdVMtCjEj0ad4YZGnW46AuVpavIN4XeXP6sIKJzoBbcVdVf9vxzgr5FvjdYCRT6NfyPlSJa2N6ZfaxFQxgMVeO09tDWwzWZJRHLKqv02IKVGfx9vVmXOqswhdjxQIYOpSw3gG6s31f-ejNamEP7SUDU9ZIiASlY38VqU6Rb0XPLIT5f7eWAysJLsa8TNzkgsWq90xjcyf5cUWfmsOEEKaZ5trKMtUBggQ3IKRaF9E8293ezn5mVfCqUSWDcFFI__KZFy2OzRWo3VA-hNECQlsdJeCs9DTWmAeg41o5owJq0SVwN8Wlre0vb6dllKx_HA5pZQGXR8jrWDBNpHCmMKEFSJVgeMdbynUKwislLNN7fXFw9elbgOD2kEfxDJlv2gvsXvJc_h9lNV44EnVBeGAZLRnsZNi6-s0j7MayjQGXynW5DDg2PgeK_vrdrVzY1RVvyF272CnJ2-c-pByqotraa6_yhLympRxyduWgQAT_z5FcMKW7_icvSNe7YrTMb_vBJ7IxorGEmQ3j9NAlpYFpET8dFBMkCn0tLln7bPA9cEPbG2VsygiAVsgbx-A3PJnLSvbeilCkA3pjPA688heDQUtOC7QP0XKZyAnKT6CHRQuE0VHDhbaePjGW5XknoT7jifvIY3ROyYA-tIBTq8JslEm2cBRSUnev-vnNcFTptABB_Za8AW4FDn3A7uWG56P8RqqaRzjRLbIv7fjo9zcyo5AOwJN_WGkgVenDveJYVcrYKfYm2Sj1t7La6ZYzrXMoqc_4BOa8B0MsRv0TV9HTq0c1JXc1pNoICXVTImxTC6C9F8vEz5BEiO9jzGgPIeOjSuE0rdTEKtutHzVRXLHlS5IDCXGZvTjb8_b7yfg-8sCi00FU5Fw9sM6AEYlEN5A5Gw_8H-vMiHrnmVdjpwjR9_XENvQd0p5g1Z9MLTirQ0EcLbCeRQJs-PoIlRTzIdmJILNjUWw6kGybqPbvuSggk9GgnNEg8Cjron06mCzRCDEwuTRci1o-Qy4cg7cGjdWS3bXUC9Q_JACsQIFbefJ7IzGfIUOjeNgI-x_ltPZ4maij_UAVKQP-FNH1BZJI6SiaI3Y3P7gceDIABSrg_42poBUPTiHva5gQvAkPV1K06MNm5Z5GnvpUt9xZYwnZErK1gFdMy3hcY9rBz3pdjGbVukQvVxsMJcj6G0x2Z-mdQpNDRDIyxPQ')

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
