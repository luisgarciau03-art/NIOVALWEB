<<<<<<< HEAD
import dropbox
import os

# Token de acceso de Dropbox (se recomienda usar variable de entorno en producción)
DROPBOX_TOKEN = os.getenv('DROPBOX_TOKEN', 'sl.u.AGN0wT76tX_5yfubolSLk8Yssh1yBr_hoWHd1bBlq6Utss8tRX3SsgfI9l6LbaG7aHGumJvyU8jGwLdvDYoNbeWzJm8Z9tga6tNoEZ_TlcQyG8vwEtlJ9Zf2Nr1XgHDyMP0JpkzK_iP6oZ5ArIVSFnJ24gyx6ooTPLeXLX0Cb8-uF_VTPbo4mCSd19evS9PY8e5bVVoRXpfeL7YGwik3CJ2u-F3SKafMQsIntgr2UdLKJtJZRtqihL10naLGmxccpQOzeWgPUfTTxViEV8_RXykBGWRsGecb8KGTAoTbUjhERQ4ly98PUTBRV0tUi_8nWFbbPWAMBKJ76yy7F4jNKjgHRxWeBTHNayMHt3eTYohV0JTpOwQHTu8yvQvEIi9WLowPusyxInkh_23KVQaUFP4MXe68w1B5IrsueUrJH1FdX5aNo1bC_3k2IPpsenQrxbrtb6fxjfGtQ8oIwCo8u8E-rh7SG2wDauOxSknBeFvx7hMAs_g1AIJ53XPQPNWs_pbsV3wq6IFBL25F9ugbttPLwsnAIrZibXFw6g3cwHPFoMoIyMbRQUFOwM-BByLeUJ5I0vllYp4SS_Q1NdozzmSW9nggoiPWGsPDYxhZewuEOTPb4hcn9weDO_AAQhoVQMUGEAh2b8pi7sM6gr68yuAqPpf1hClJ04SZnjHcjd78nwpUoXDMZFCo6MvynxEbAkjh8p00uq4TCS_qh5L9gBAKoF6SUmbcy3OYtjom_HkkJZ9uJc8VLPKOtuZKkuhJO51SQbbP1fhFATTXOveNA2eketb-c_UXvt0Vi1MnZxkP2pVXwynhWMccF1a-DLfR9xYNxFPlbGEU18fHp03scp8S12DlGaFDSVVS5r2hWLKLrXRjtGs_OhTY_ZXdjqop1_v31Z0mZ_khX7XMg6UIobB2BNmT1R6UX2EtwOTQSSFcZphV_75U0gp6d4D5fWTonJrkjh-nH3NaBRjH3ofGUV9zZFM7Mb885Sd-0vNyfJt2EtsjZRW_lbcn1ClzwNxewP6BYzClcVwYuWW7L0CyMU6d6zb1mCExMivJI-yeEX0kZ_H23WyURVWBB3GFCCdlssa2HSnZW0775jwekHWWQChWjv1sTIiFDk3Ecz7SNpxQDUD19K7ajLCVqsmequdowC_4aJsolIbN09GZmYTd2ypAOs0Q66cztElZK6jWvUsBpxI0NZq1y1l3KfhP6WE16-i4g4Q48oB3Pj7Hw190eIlW63iJfCZuUmTzVlDFibqxnwXpS6TjyYbXE6qOCkyAPFSTvrkQeSPvQiR43AdMvGOFMBqZ9Gn98RCoFPiIXrXxlHU1mIkBjNiq2R7MzfK3tM4oTi1hnXeAHOzjt3vsAPcnPZk24IqAlPwLEpyG4aqOjkWNrQRJqbHvsNezDp6rC_HNMA9wmaGxoZpl5isJDKqktRNfhSwQHEsPpEjnKEmsxA')

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
DROPBOX_TOKEN = os.getenv('DROPBOX_TOKEN', 'sl.u.AGN0wT76tX_5yfubolSLk8Yssh1yBr_hoWHd1bBlq6Utss8tRX3SsgfI9l6LbaG7aHGumJvyU8jGwLdvDYoNbeWzJm8Z9tga6tNoEZ_TlcQyG8vwEtlJ9Zf2Nr1XgHDyMP0JpkzK_iP6oZ5ArIVSFnJ24gyx6ooTPLeXLX0Cb8-uF_VTPbo4mCSd19evS9PY8e5bVVoRXpfeL7YGwik3CJ2u-F3SKafMQsIntgr2UdLKJtJZRtqihL10naLGmxccpQOzeWgPUfTTxViEV8_RXykBGWRsGecb8KGTAoTbUjhERQ4ly98PUTBRV0tUi_8nWFbbPWAMBKJ76yy7F4jNKjgHRxWeBTHNayMHt3eTYohV0JTpOwQHTu8yvQvEIi9WLowPusyxInkh_23KVQaUFP4MXe68w1B5IrsueUrJH1FdX5aNo1bC_3k2IPpsenQrxbrtb6fxjfGtQ8oIwCo8u8E-rh7SG2wDauOxSknBeFvx7hMAs_g1AIJ53XPQPNWs_pbsV3wq6IFBL25F9ugbttPLwsnAIrZibXFw6g3cwHPFoMoIyMbRQUFOwM-BByLeUJ5I0vllYp4SS_Q1NdozzmSW9nggoiPWGsPDYxhZewuEOTPb4hcn9weDO_AAQhoVQMUGEAh2b8pi7sM6gr68yuAqPpf1hClJ04SZnjHcjd78nwpUoXDMZFCo6MvynxEbAkjh8p00uq4TCS_qh5L9gBAKoF6SUmbcy3OYtjom_HkkJZ9uJc8VLPKOtuZKkuhJO51SQbbP1fhFATTXOveNA2eketb-c_UXvt0Vi1MnZxkP2pVXwynhWMccF1a-DLfR9xYNxFPlbGEU18fHp03scp8S12DlGaFDSVVS5r2hWLKLrXRjtGs_OhTY_ZXdjqop1_v31Z0mZ_khX7XMg6UIobB2BNmT1R6UX2EtwOTQSSFcZphV_75U0gp6d4D5fWTonJrkjh-nH3NaBRjH3ofGUV9zZFM7Mb885Sd-0vNyfJt2EtsjZRW_lbcn1ClzwNxewP6BYzClcVwYuWW7L0CyMU6d6zb1mCExMivJI-yeEX0kZ_H23WyURVWBB3GFCCdlssa2HSnZW0775jwekHWWQChWjv1sTIiFDk3Ecz7SNpxQDUD19K7ajLCVqsmequdowC_4aJsolIbN09GZmYTd2ypAOs0Q66cztElZK6jWvUsBpxI0NZq1y1l3KfhP6WE16-i4g4Q48oB3Pj7Hw190eIlW63iJfCZuUmTzVlDFibqxnwXpS6TjyYbXE6qOCkyAPFSTvrkQeSPvQiR43AdMvGOFMBqZ9Gn98RCoFPiIXrXxlHU1mIkBjNiq2R7MzfK3tM4oTi1hnXeAHOzjt3vsAPcnPZk24IqAlPwLEpyG4aqOjkWNrQRJqbHvsNezDp6rC_HNMA9wmaGxoZpl5isJDKqktRNfhSwQHEsPpEjnKEmsxA')

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
