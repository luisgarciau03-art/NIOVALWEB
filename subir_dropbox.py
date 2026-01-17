<<<<<<< HEAD
import dropbox
import os

# Token de acceso de Dropbox (se recomienda usar variable de entorno en producción)
DROPBOX_TOKEN = os.getenv('DROPBOX_TOKEN', 'sl.u.AGM8NCfrKCxzkubWGfASzJRFOmBZEq2iG56kP6EsLEjJwDC3T9vKaO6JN2EjfbSnEORu7rP7Lo5t2aJH9Mlh83KVHfue78xY9k-rWD4XvuzHWQuXmgpwrNdoIscX45MwWFbZbub5l7w75ImvOJ3i-ER2Mt7zgUPuQ7wJHoomulYMN4YL5SOV_bZMeLUHQSQgcQagSfiQ56Tq28WT9Sa3bjQ7UTgrEf8uA6zMd1x8M70bnDpLhDhS8i2jJOc4-IBoI6SQO7TewHMwwtMq_9d9qx1DgJXluMe5fQtdt0Z8TDKdZsrF8ATAlcFAHkzoxLtJ5OHh0tlKR4LAl1QfpozCeiB8jhlqYF4IB2a1TulZH6BGA-VZt6DbDmPMGfoItfYXcOqJ2BQoc_q3BjBxkljb9Z9jXsEvf1QyraL4dRaPDmtSrXbw5Z0f-fLjLALAL3igYU1cNytKshvcliidpIocyc84lYhnsc7nRcBZuvgTTWdYNSjGgHsXwjfFoKTSMaFq7RIbAerdcVMJ8wDBmexdL21Rsqdnsqf4gXGgMtJBqH3WtRlcBKZ_-xgFpLk7fH3Q9HBitE017C8bN8ysGoIP4BFx0L7YVRaMfH_NmjcUqVAW4f-MRFAL5Vcu0Bp3fZ_fKskbDFFtw7ThL8QUI-PkMsvFwcgGS5hd6oSxf6tT9lwC6Qf8DpuIxUZjOvkGElk1MYsbGPaM0b7aeNIywbw1BdXVKzfJ7eIqElC6_7ZJca5iDhRvkDvZxjIxA7Z7AiqLWWwpHfVR1WySWy7NZUGANksRoRA5cGd51LLIDofKuorNU0JZoA_DsLUFKyr2jbTWAg1SsiuvQpd5SYm9gbCaJ_SeHjiM5REa8-rA0eO1s590-MZ0v_cMbPvVKwVfhBP28QdPWIKGnnVgms8Gj1IvcWuOb2X1eF3Ue3ExdRDXyhgNyr79AxcXOeS6oERBsZwTVm0ZBpOYkBg423RnkHaH4iG2cmTfusclwCx5NvqEZLpfxzbe0gg4uj7XSeo9zCcMG1SUeAVIXVO0F-qxg8o5BSDXHMFVOWGkrgzGYg5Bnv2MTn6QSPihqYlKpAWpETs3Yo1EXB69C8Rby675pxrEr4oY5vuJc5bZS8SEvfxUYB1RHCsGY4qKpY3JKKdNA7Le37C0HfRbRLI2gkRz0qNYEeopvlJWLSEgEOl4q3uE_5SlG9ivja77xzhRlauekBXzyz2-NJicHJ-MGebH2YwR87Vb9GkqNwe4KaqS3xspOjlq1gEM4yYdMHlhbusITv7H-RmIylvkv_iaXFpGQ4B2E_ximE66Nk506ue8Ljwg3hp_eOfYyk9unNrkKq98SXjp1Clj98sUJ6QOFTF64kGo8kAN33pD9Yj230G2OMIj0ppIZWPZ0uQxEiRZEwYbHwc8n98A5PBpmnQZU6vZ7pjnzOQLY6hNEcn_qmO5KxfjaNnyMg')

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
DROPBOX_TOKEN = os.getenv('DROPBOX_TOKEN', 'sl.u.AGM8NCfrKCxzkubWGfASzJRFOmBZEq2iG56kP6EsLEjJwDC3T9vKaO6JN2EjfbSnEORu7rP7Lo5t2aJH9Mlh83KVHfue78xY9k-rWD4XvuzHWQuXmgpwrNdoIscX45MwWFbZbub5l7w75ImvOJ3i-ER2Mt7zgUPuQ7wJHoomulYMN4YL5SOV_bZMeLUHQSQgcQagSfiQ56Tq28WT9Sa3bjQ7UTgrEf8uA6zMd1x8M70bnDpLhDhS8i2jJOc4-IBoI6SQO7TewHMwwtMq_9d9qx1DgJXluMe5fQtdt0Z8TDKdZsrF8ATAlcFAHkzoxLtJ5OHh0tlKR4LAl1QfpozCeiB8jhlqYF4IB2a1TulZH6BGA-VZt6DbDmPMGfoItfYXcOqJ2BQoc_q3BjBxkljb9Z9jXsEvf1QyraL4dRaPDmtSrXbw5Z0f-fLjLALAL3igYU1cNytKshvcliidpIocyc84lYhnsc7nRcBZuvgTTWdYNSjGgHsXwjfFoKTSMaFq7RIbAerdcVMJ8wDBmexdL21Rsqdnsqf4gXGgMtJBqH3WtRlcBKZ_-xgFpLk7fH3Q9HBitE017C8bN8ysGoIP4BFx0L7YVRaMfH_NmjcUqVAW4f-MRFAL5Vcu0Bp3fZ_fKskbDFFtw7ThL8QUI-PkMsvFwcgGS5hd6oSxf6tT9lwC6Qf8DpuIxUZjOvkGElk1MYsbGPaM0b7aeNIywbw1BdXVKzfJ7eIqElC6_7ZJca5iDhRvkDvZxjIxA7Z7AiqLWWwpHfVR1WySWy7NZUGANksRoRA5cGd51LLIDofKuorNU0JZoA_DsLUFKyr2jbTWAg1SsiuvQpd5SYm9gbCaJ_SeHjiM5REa8-rA0eO1s590-MZ0v_cMbPvVKwVfhBP28QdPWIKGnnVgms8Gj1IvcWuOb2X1eF3Ue3ExdRDXyhgNyr79AxcXOeS6oERBsZwTVm0ZBpOYkBg423RnkHaH4iG2cmTfusclwCx5NvqEZLpfxzbe0gg4uj7XSeo9zCcMG1SUeAVIXVO0F-qxg8o5BSDXHMFVOWGkrgzGYg5Bnv2MTn6QSPihqYlKpAWpETs3Yo1EXB69C8Rby675pxrEr4oY5vuJc5bZS8SEvfxUYB1RHCsGY4qKpY3JKKdNA7Le37C0HfRbRLI2gkRz0qNYEeopvlJWLSEgEOl4q3uE_5SlG9ivja77xzhRlauekBXzyz2-NJicHJ-MGebH2YwR87Vb9GkqNwe4KaqS3xspOjlq1gEM4yYdMHlhbusITv7H-RmIylvkv_iaXFpGQ4B2E_ximE66Nk506ue8Ljwg3hp_eOfYyk9unNrkKq98SXjp1Clj98sUJ6QOFTF64kGo8kAN33pD9Yj230G2OMIj0ppIZWPZ0uQxEiRZEwYbHwc8n98A5PBpmnQZU6vZ7pjnzOQLY6hNEcn_qmO5KxfjaNnyMg')

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
