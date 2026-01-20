<<<<<<< HEAD
import dropbox
import os

# Token de acceso de Dropbox (se recomienda usar variable de entorno en producción)
DROPBOX_TOKEN = os.getenv('DROPBOX_TOKEN', 'sl.u.AGPr5MBDESHSLfnYC-Lk6b5pjrSlFoT9t-SmJ8_OtBvA694u0iy4Cst6UrsG7qLSJKicaVZmf0CQEnoDrACqx2ZLtrzoxT-5q0PLKEpaY_5SSRLT-yxTZ7ZKpYPBENFJ7UaKU203IjkFNB5f1LvaDMOKQjC1MOrbpIReI5ce76QkltZCsWMTvQ1VF0O4pn3N84jQ-My0s-DUKZHqW2trsyeBU-pVxJaxBz4f1ZhieDaypTuyNfoMjB4CAxvyBItZYr3MlImORKcPtHZ10Gg2ZIW-DsoUepTvnViY_fp4W-SJuEqnLu5SrhC8ZyhdpJdrvFc9PfmeQAxhEQcZjwcyqPTQ5O1c2teaeRK_QIs17PUFsM2sFxxZRGbdf9NiWQ3iopmSty9SDrQ5DJJbfYyYePZ97NvaCNWW8rXQeQiYMdFo7lbHeKHM0ceS4CmIA1fFsysKdhqt3npT6taWdtcG3bXe2wUt3L0rq5Ldxa6-aMUVuxS4ivge5aYgjSq8tEEdZWJmHYLGoBJFV4XNdw8ZwA5P6SzN8lJG364_vBoTKidL5aW1X5aJhlfcV1if7bswQ_d_-eI0-H0zcjRqgkP9JNiGyfcruCyGstixOgAQeUmUhZyrUPquUUehXYJS3Sp1nTI9-4U4w3TpKkkILWQU5HGmeyDJucxPny8Davt3Ak3ntEWGUDjWyZFUQGtq_o7eXApUFKPv9nseWcK8XGG5dGPfVPii7GtrrlSJhbnuHBGCzKqa-psJNeyKBa9XYu23Wpn5EqzI5iEGLrcQEXSXvYhdEk6c4by4e-9TK_mSgUYAsy0KXnIqrrj0kIFVdIgA5E4JZI2CSj6WT59XEJZM9KOoPPcSWOYfL94Nh-kxX0PCdQQf63KlPzV0QoHoEp7PopIMes3z5Y3upDdyGgdJFqph3GLvWeKomyXqLLyC2_8RGN__Epyy1dXY6RBmGVib7C4CZ0vXYwJNdAaGuu9EdAl-4mysQRw0YGLUCDkRFOOFAlFK3jDa7c2GMtKpT02AIyVldISt0k1p-d8qJIF298ShwpfBpaPHNhFiltT3QjZy4YzHhOk3uSTwhff0dysWftKOcsOYX8aL811GcQz0H25ufi2NjEFcUeYwUoJgY793J9VtkOEErTEgacAQ9wKqaRQvSefCRnbPY3b1XuhUrsRTnBhl5iwuN0RrPBL61BYI5RnnWNSeKVGgxWBDIfNi6SMf8FAJRAHde2DCm7nVJ2f0yrGyuLSBwW7LbSdxDmHgllQkih-K-tPICRYiNBPns6BZpgGOgFdjhUw3FQTwCejnJKNtd-vcePlkUuQKlBfTyVylk_Gm1NQTCkxnfsiBt8aHrvzAmoccEG61IrWeuowstvmhkor_9J847FhWnu4n19HQCSwQ6NV10hxPJBfp0QGTb5ar7HXEJKqwhzacBaOyYw7PwaHSxO4_2f0BV8C6ZQ')

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
DROPBOX_TOKEN = os.getenv('DROPBOX_TOKEN', 'sl.u.AGPr5MBDESHSLfnYC-Lk6b5pjrSlFoT9t-SmJ8_OtBvA694u0iy4Cst6UrsG7qLSJKicaVZmf0CQEnoDrACqx2ZLtrzoxT-5q0PLKEpaY_5SSRLT-yxTZ7ZKpYPBENFJ7UaKU203IjkFNB5f1LvaDMOKQjC1MOrbpIReI5ce76QkltZCsWMTvQ1VF0O4pn3N84jQ-My0s-DUKZHqW2trsyeBU-pVxJaxBz4f1ZhieDaypTuyNfoMjB4CAxvyBItZYr3MlImORKcPtHZ10Gg2ZIW-DsoUepTvnViY_fp4W-SJuEqnLu5SrhC8ZyhdpJdrvFc9PfmeQAxhEQcZjwcyqPTQ5O1c2teaeRK_QIs17PUFsM2sFxxZRGbdf9NiWQ3iopmSty9SDrQ5DJJbfYyYePZ97NvaCNWW8rXQeQiYMdFo7lbHeKHM0ceS4CmIA1fFsysKdhqt3npT6taWdtcG3bXe2wUt3L0rq5Ldxa6-aMUVuxS4ivge5aYgjSq8tEEdZWJmHYLGoBJFV4XNdw8ZwA5P6SzN8lJG364_vBoTKidL5aW1X5aJhlfcV1if7bswQ_d_-eI0-H0zcjRqgkP9JNiGyfcruCyGstixOgAQeUmUhZyrUPquUUehXYJS3Sp1nTI9-4U4w3TpKkkILWQU5HGmeyDJucxPny8Davt3Ak3ntEWGUDjWyZFUQGtq_o7eXApUFKPv9nseWcK8XGG5dGPfVPii7GtrrlSJhbnuHBGCzKqa-psJNeyKBa9XYu23Wpn5EqzI5iEGLrcQEXSXvYhdEk6c4by4e-9TK_mSgUYAsy0KXnIqrrj0kIFVdIgA5E4JZI2CSj6WT59XEJZM9KOoPPcSWOYfL94Nh-kxX0PCdQQf63KlPzV0QoHoEp7PopIMes3z5Y3upDdyGgdJFqph3GLvWeKomyXqLLyC2_8RGN__Epyy1dXY6RBmGVib7C4CZ0vXYwJNdAaGuu9EdAl-4mysQRw0YGLUCDkRFOOFAlFK3jDa7c2GMtKpT02AIyVldISt0k1p-d8qJIF298ShwpfBpaPHNhFiltT3QjZy4YzHhOk3uSTwhff0dysWftKOcsOYX8aL811GcQz0H25ufi2NjEFcUeYwUoJgY793J9VtkOEErTEgacAQ9wKqaRQvSefCRnbPY3b1XuhUrsRTnBhl5iwuN0RrPBL61BYI5RnnWNSeKVGgxWBDIfNi6SMf8FAJRAHde2DCm7nVJ2f0yrGyuLSBwW7LbSdxDmHgllQkih-K-tPICRYiNBPns6BZpgGOgFdjhUw3FQTwCejnJKNtd-vcePlkUuQKlBfTyVylk_Gm1NQTCkxnfsiBt8aHrvzAmoccEG61IrWeuowstvmhkor_9J847FhWnu4n19HQCSwQ6NV10hxPJBfp0QGTb5ar7HXEJKqwhzacBaOyYw7PwaHSxO4_2f0BV8C6ZQ')

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
