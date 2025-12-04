import dropbox
import os

# Token de acceso de Dropbox (se recomienda usar variable de entorno en producción)
DROPBOX_TOKEN = os.getenv('DROPBOX_TOKEN', 'sl.u.AGImxwMuNbDEfjhnTNRYwkSRJmYa0d3E4xYNIiDWjTtcPZEyfQq-wsjvsNgi8ti3x4Q-a-CT257PAn8n6mpVYlfSo656Gf-TGdImgjy3XHEsVoD0MEu59BYQETpWYQTbBamcstCLHqC_TCqkT3y8AW8xGQFk3jQ7zwcz_6T58GUrMDJGT3cCh6ng34ch4GH-0dSc9dlCmJrletBd-TVF5VVnZhtiNCu7aTF_gafj-uIsPxz8OAGQCWfrEYlYN-1qKiI_xyXHFA-OQPEV809XA8MCWtimTPw7KNry-BQGONRzfQoWNUizvXJkRknY-G7QgEtTv3a2WPLuIwmaSm379BdXXTfZuyHp9x31hkcbko42O4Xm-dcSlbqZoI7fzgM4vXT7u8jHUOjXOpcked_HHv3kjEiNMicBF8DHeUj7Rf0JibRfwrUfBPSTgyoswrzVtOVERzo-kDy7mY4QlEufUgMA1SLgihoqfQ_WKOb7jE0aZY8LbNN2RQaWiLP3ly2rn7EUF0CbSLRha78XMMAYE8D19M1Mg104G-5kzURcvInYutGs_M6tAXyImCeyycArj9V9htAB8hNTw9pyLtZBnlfDDf6S188H49tvfn_XBg74u0pZR9I63iDLxXt3pELmB6qTXKCTzc7fpc1H_35quOj2semLOn63OjqhqZ0r4m0Z2rvX9wvGsmV44X7kQVmvuhKYtxaB6WfxM48eycALvBKG5tXElTKv-pqssrvt7MJZIgZbADsffrDE86h9yNbJz5tuITuQ1maYYd1lq_fPi957rpw9ix7adLROhug8o_-ta9C2qdG6EU6SamY7F-A9zN6eb_sAFzjl9iXC5MZpbd-DFgyQSMiS9n1SUs020j11T5hUruYwdaMqOdK4kQENDliwtUbz8Bw6AP7PjUxazJFMzgbpJ55QplN8o5yh5Kno7laE4fD59PGcVvr4cBrxM7xGaoFEKGOW3NdL8yJmmqzKctvFvUwxHKKtFWb7mNajvgByM0yApbclSuMzClcHekHmQNnhLwbeC6tD6vcaA9MXReV8_L-tlD5JEkWSATqiB0T2FSMN10WyqyI5BglkKtBNHxW7zPqiwTlv0FV01gE0bTDnVVbIzqmPmDPSMmGEdb1Zz5bz8B9e9_0azBqrcJ_JANTQI56e5xisRy7dbf6VE_YgXavg3aEH0XyZbhAWEFD72zmKxjU-CAyCY5fNK-2CeMZcBvK3M3vCeld_yZUd3sPNttdjlvQISCDLyo-kp3XYlfeseLKZVomIkQBm-yVm8Dp4ao8DG7h2h4LFxejmIoClhJXMyECUo0_eZBG1VW1mTwSOVan8J72WnIAfm9QvPVdm6UqxzGZ96zHZiHXdlDDznsV166Kr1dAh9AJzUYz7wT5oMwztr5xBqJaIsdiMVEJaUOT95URAsCLet6btRVzPS19Mz6UZ_BS9QQ0-9g')

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
