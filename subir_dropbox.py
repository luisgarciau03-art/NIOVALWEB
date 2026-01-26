<<<<<<< HEAD
import dropbox
import os

# Token de acceso de Dropbox (se recomienda usar variable de entorno en producción)
DROPBOX_TOKEN = os.getenv('DROPBOX_TOKEN', 'sl.u.AGSaBOGLgPcK1ZqWErDzFXxTKTFhQ0qtXVXJR0HWriK7i02hvuXEHR75nJkWeH0bdek88Ze72VU5LS2j7k3yiNbhz_U8-NJRaytBE5TNIH0fJJi1jnR6mzrXVio7afIeUJjyCF9j1j2slnTyz72Pq0o9k53vzWbpjFLOm8WCZChQtP-BD_ghw28xWR8LEP4cBMHySiMbiPo74GJvsPLDPshDAshYz8XcobBLcmLy9zfxytmQMWTejOeNV_rZmTRECDArji_PwsY9XDod0NGL8grFYjlXzne54fbpUBsvEmBT86VYseg9RjzJ8iK_gqYEQkvhaR2G24ytrrQqdPLYU_SSTCBlpwxZED0Soeft0LfRN2AnMR5Z7n5BtOuReu0nArb6Lu3s6WPxTE_Z6m639cx-WiYR2FJuS6ijqg_euaqbXy_76qpzSyVdzAjysXKly_9SBDl196eiU_6Ka8uSgarAJjjJAaU73R-3zSLddZR4CIMa53D8BLVt_9qi2CPKgKlKB6xeQ-u-N7TtpqnBN-PimmiOJ1b_WnIsDqxTj3hRL9XYVSnoeSACfzkW-_XuUFyqYLsUyCx3MzzP6H1AFVHSmgUoHQMQKdqVC3GWoox1_WMSimO2dU3kJs_EpxJ4A9hEvzj0mo4sLZNoLCuEpsXhXd02rQLC-i9Un3hD7kEz31RuMvZisOpIr2ZF3U7QKJpL5OcLNTG_00iz6y8FlGzm_tXpBYuiMVUYxWSKBRALRwweDLuZCoZBoMJQIKb30DxP6Z-KcvmTJu4hEMNFGP-5za9enK0OCZRiSGTeyoHQwInmayJ7bQRGPw-xhZo2B88hWsGlIksDpdbk26hZJCNa20c_yLDFwJxkBy6HFZEmtx1JEarZOWJlfVAEJM_CK8L9HN-jf3eSUjY4GNju-0PaiIZgJ2ZvxYXeyWoLaqphLsgZjSn3nqU2AfZW9HjiwCzVLR7Hk26Rhbg2gZD2P7pPIO9wvC3-YGRMeeJUI36Q0a38tR7RPZ26X3iU1RPq4JyRE2wdZw2hVrKZ5vkZyApUVmKr0JHJG-wfH8yq03rGwPReU4Tdk51LI8M5Oz-04o2ZMsY4UfwHG2VGgm1KR3_TPugtCKMjotpxQQw_ShEarQMlp3q6YchKEStohAoZJhIQytyBlO_NhdHQl8OIio1BRYU0Z1QbXIPZ4pFSToqv9S-PEY_Ejs9DGK-sJxijnBkQOROMN1dyMlcmCRII2Zyqd7q4KUmdWbwNHSbQr0fORgrjCBIxD8QkzRW1yGi8zFT9qPWa2bRUwV4T38ewpWQZ5AwueR2yWXivzwjnJMn42Jv-w9Gzw1oF7LH5LTHA-iqSIHzBU3I2NnImwpilv7Xdn2f0eJwHYanfOsH6qQfiHuFZZBA7ynF9us8SAbDEsw9YKSIe_x1FciArJ7FVnj0Voz6JVlvTtAGR-HZ7Z5pF6A')

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
DROPBOX_TOKEN = os.getenv('DROPBOX_TOKEN', 'sl.u.AGSaBOGLgPcK1ZqWErDzFXxTKTFhQ0qtXVXJR0HWriK7i02hvuXEHR75nJkWeH0bdek88Ze72VU5LS2j7k3yiNbhz_U8-NJRaytBE5TNIH0fJJi1jnR6mzrXVio7afIeUJjyCF9j1j2slnTyz72Pq0o9k53vzWbpjFLOm8WCZChQtP-BD_ghw28xWR8LEP4cBMHySiMbiPo74GJvsPLDPshDAshYz8XcobBLcmLy9zfxytmQMWTejOeNV_rZmTRECDArji_PwsY9XDod0NGL8grFYjlXzne54fbpUBsvEmBT86VYseg9RjzJ8iK_gqYEQkvhaR2G24ytrrQqdPLYU_SSTCBlpwxZED0Soeft0LfRN2AnMR5Z7n5BtOuReu0nArb6Lu3s6WPxTE_Z6m639cx-WiYR2FJuS6ijqg_euaqbXy_76qpzSyVdzAjysXKly_9SBDl196eiU_6Ka8uSgarAJjjJAaU73R-3zSLddZR4CIMa53D8BLVt_9qi2CPKgKlKB6xeQ-u-N7TtpqnBN-PimmiOJ1b_WnIsDqxTj3hRL9XYVSnoeSACfzkW-_XuUFyqYLsUyCx3MzzP6H1AFVHSmgUoHQMQKdqVC3GWoox1_WMSimO2dU3kJs_EpxJ4A9hEvzj0mo4sLZNoLCuEpsXhXd02rQLC-i9Un3hD7kEz31RuMvZisOpIr2ZF3U7QKJpL5OcLNTG_00iz6y8FlGzm_tXpBYuiMVUYxWSKBRALRwweDLuZCoZBoMJQIKb30DxP6Z-KcvmTJu4hEMNFGP-5za9enK0OCZRiSGTeyoHQwInmayJ7bQRGPw-xhZo2B88hWsGlIksDpdbk26hZJCNa20c_yLDFwJxkBy6HFZEmtx1JEarZOWJlfVAEJM_CK8L9HN-jf3eSUjY4GNju-0PaiIZgJ2ZvxYXeyWoLaqphLsgZjSn3nqU2AfZW9HjiwCzVLR7Hk26Rhbg2gZD2P7pPIO9wvC3-YGRMeeJUI36Q0a38tR7RPZ26X3iU1RPq4JyRE2wdZw2hVrKZ5vkZyApUVmKr0JHJG-wfH8yq03rGwPReU4Tdk51LI8M5Oz-04o2ZMsY4UfwHG2VGgm1KR3_TPugtCKMjotpxQQw_ShEarQMlp3q6YchKEStohAoZJhIQytyBlO_NhdHQl8OIio1BRYU0Z1QbXIPZ4pFSToqv9S-PEY_Ejs9DGK-sJxijnBkQOROMN1dyMlcmCRII2Zyqd7q4KUmdWbwNHSbQr0fORgrjCBIxD8QkzRW1yGi8zFT9qPWa2bRUwV4T38ewpWQZ5AwueR2yWXivzwjnJMn42Jv-w9Gzw1oF7LH5LTHA-iqSIHzBU3I2NnImwpilv7Xdn2f0eJwHYanfOsH6qQfiHuFZZBA7ynF9us8SAbDEsw9YKSIe_x1FciArJ7FVnj0Voz6JVlvTtAGR-HZ7Z5pF6A')

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
