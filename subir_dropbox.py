<<<<<<< HEAD
import dropbox
import os

# Token de acceso de Dropbox (se recomienda usar variable de entorno en producción)
DROPBOX_TOKEN = os.getenv('DROPBOX_TOKEN', 'sl.u.AGOdNR2rXWqX1q3WoeygAe2JvKFFneHeQwWO7Qpqty-AGHJaM79JFcez2nCFjy6oAWyPYaVzgw9a7fIzw2wTamVv9QGxyGVUpYB0BqCxpnTRmaxqxElAeWQGK-zl_a0WHkUTAUpTnSlPZ1Ks6F74peYOgBGKZnze_unk5S4IbfGXOhFPOlD9hwW1bTStjUjpX_54d9cp7yMlLZZr6hFCt2IqDFZMd5btn76BXexEXmmXctTLLg-pQzcZ4Gy77MU1UuDfH1CnT5zHknQ04hTwqkhzQvQGLnGJHpKpsUstO1nGOvC_esF8fzKJR9OEGl1iCJ6R7LIgIBEs9x155mjarmg54vrg6kmrHZ9lCU-qfuGCLa4VltD4GGV7hGCbUZyx-x2ZJblWJJfFs-rGRKWo6W4QkUO21_bzg_OX3bTXaRYtkXN7a4ZW7YHIW7wlI_PiaETt2lY-FUEzspxdn1XqpGNxJ9CYTjKGvqorN5a5MPR_XtJoLhHOiRn_LDFv0w3CDAQ2mEpYJ0RcQWLZhnxgsRGYR4tj0nhValCnyXYB9PbsntpQFsMAZZ2GSAi5-euA9kf6R5_BNoWmeWuvDQvxWt6mYG26rWXSdbDeJmXP-H_i2SSgYJQ4ytEXXhBxQFLMaLPZnJ5PjBSDY5MIj7EunWw3KxYHaCdc4qaVmPR3kM19uj4LFUB7wV0xfICwkesev9s95GxL8bdMF14HY6b6GsxUJRcR6JztOw_bDveDGp6zMPHv8muLvMQ3omxiaEI4GoSQj2ZZadQbtqB55q3mwKlbU_HWWueDPSpnJzIul7s1oDV2bgG53-Jq1FP-pfO-uyvi9DIN3Q4gvf6b4fmOpwyKENzwHVqmFk69SkZP6FdjHJSro0i831P2q6YblRC8rlOAcz-Hd0nUmMpOOom9m7qcX9NZ56dbcLS8pHNpms-yA3DPl8CSK5dsjxNsjx3WxeCbnefrVPyrxGDZYS_RdCRmA5964OgUmj6j6T55vpIdYGPH846jCSUqS7n7qChbexbNjxP84GjBiiPOOXmARIpXT1QmHV5Yxokte9L5hGIfJVt5AYG5nMducP7cZVmgLt_LEGJm-_N8nChk6tX8MrYODYJNJiB5z7Q8Rb1aAL6PeuQ6bZdcgtzBdSCkX3hFzMn-gQHYQcP3Af3g6oK3f7Ooikw6RysHTp7LkvG4sgmQZ4U384qyy69hMyspDWc57pkOKQZgN3Ay-DpZBezYuTh5LS3khMDMnRIjGZHeW28x658FDz7oNTqUfCLSdtNH7q2oLJ9gNF-zfgK5hYFxQYnzlavYXrp7DE1lGSCtzsX0ANbzo3OrwYYSR_-mZwseqao9e9Y4NVWZxnCl-gAPk3RI4K0u8SyTbkHf7bABITelX697h397sho91Zg8f-jquGJUk93UtTfpe6PLiJegkl7KY9z3ePN4C0I9UAabqv4jzA')

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
DROPBOX_TOKEN = os.getenv('DROPBOX_TOKEN', 'sl.u.AGOdNR2rXWqX1q3WoeygAe2JvKFFneHeQwWO7Qpqty-AGHJaM79JFcez2nCFjy6oAWyPYaVzgw9a7fIzw2wTamVv9QGxyGVUpYB0BqCxpnTRmaxqxElAeWQGK-zl_a0WHkUTAUpTnSlPZ1Ks6F74peYOgBGKZnze_unk5S4IbfGXOhFPOlD9hwW1bTStjUjpX_54d9cp7yMlLZZr6hFCt2IqDFZMd5btn76BXexEXmmXctTLLg-pQzcZ4Gy77MU1UuDfH1CnT5zHknQ04hTwqkhzQvQGLnGJHpKpsUstO1nGOvC_esF8fzKJR9OEGl1iCJ6R7LIgIBEs9x155mjarmg54vrg6kmrHZ9lCU-qfuGCLa4VltD4GGV7hGCbUZyx-x2ZJblWJJfFs-rGRKWo6W4QkUO21_bzg_OX3bTXaRYtkXN7a4ZW7YHIW7wlI_PiaETt2lY-FUEzspxdn1XqpGNxJ9CYTjKGvqorN5a5MPR_XtJoLhHOiRn_LDFv0w3CDAQ2mEpYJ0RcQWLZhnxgsRGYR4tj0nhValCnyXYB9PbsntpQFsMAZZ2GSAi5-euA9kf6R5_BNoWmeWuvDQvxWt6mYG26rWXSdbDeJmXP-H_i2SSgYJQ4ytEXXhBxQFLMaLPZnJ5PjBSDY5MIj7EunWw3KxYHaCdc4qaVmPR3kM19uj4LFUB7wV0xfICwkesev9s95GxL8bdMF14HY6b6GsxUJRcR6JztOw_bDveDGp6zMPHv8muLvMQ3omxiaEI4GoSQj2ZZadQbtqB55q3mwKlbU_HWWueDPSpnJzIul7s1oDV2bgG53-Jq1FP-pfO-uyvi9DIN3Q4gvf6b4fmOpwyKENzwHVqmFk69SkZP6FdjHJSro0i831P2q6YblRC8rlOAcz-Hd0nUmMpOOom9m7qcX9NZ56dbcLS8pHNpms-yA3DPl8CSK5dsjxNsjx3WxeCbnefrVPyrxGDZYS_RdCRmA5964OgUmj6j6T55vpIdYGPH846jCSUqS7n7qChbexbNjxP84GjBiiPOOXmARIpXT1QmHV5Yxokte9L5hGIfJVt5AYG5nMducP7cZVmgLt_LEGJm-_N8nChk6tX8MrYODYJNJiB5z7Q8Rb1aAL6PeuQ6bZdcgtzBdSCkX3hFzMn-gQHYQcP3Af3g6oK3f7Ooikw6RysHTp7LkvG4sgmQZ4U384qyy69hMyspDWc57pkOKQZgN3Ay-DpZBezYuTh5LS3khMDMnRIjGZHeW28x658FDz7oNTqUfCLSdtNH7q2oLJ9gNF-zfgK5hYFxQYnzlavYXrp7DE1lGSCtzsX0ANbzo3OrwYYSR_-mZwseqao9e9Y4NVWZxnCl-gAPk3RI4K0u8SyTbkHf7bABITelX697h397sho91Zg8f-jquGJUk93UtTfpe6PLiJegkl7KY9z3ePN4C0I9UAabqv4jzA')

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
