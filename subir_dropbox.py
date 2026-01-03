<<<<<<< HEAD
import dropbox
import os

# Token de acceso de Dropbox (se recomienda usar variable de entorno en producción)
DROPBOX_TOKEN = os.getenv('DROPBOX_TOKEN', 'sl.u.AGM2F4B6sqJ6TH9jnrJSh7YzGqgEykrxmyhJb2-E1338Zk1FtC30y0SAIO2TYvk4HlxTjLhgi1HnXGjWVpaG7EQYGSxVSAXxrPcaBK8HLIZhrOK2XovblfOXLIyb00csJ3khI10zuRNwjUaj0ErFVWxIOpvg1Q73QkcQmbEj5t3yAQ5NmxXdU2ZguDN_j0jPivCySBvu7u1cVRD455sYDkQ4ufu-dvuJj7At5oKwtuxSrB8ySeaxaQfbukYSv-9gHZ2YHZtlDkhuHS_Ec5126Qr_OhoAZ_HFSeKaj4jUDSHsTU2c4k-giDpibkjasWgPbzGwsakaEVa3uzQyZNy5ZsqNyjq1xhGWLC0GhwDvG80sq6nYN5krWrnFwpdw_78B9qjvn1ff6j-D1kJ9xysawruroUHYLPEMjl0qOy3_e_74VKjL101B-QHtcsodek5PVYsa7JXR4x9WRqqvHt-_Dw6Kv_2MapWAALnXpc2APXQqSydG2R6bw-fJkEi7YIjTsFwv6WtXx7BYHa1FvSQ7HS2CGK7VVgNVlb03qWFKB3o6s3DO1q2TN3fNyFF_ypsMMwqU7cfyjSREfN857Y0p9SACQn3kKv401IRXncWdxE1Bm66g3DBADeI3OPHErZr6RgvHUTT0XZIqlSLY1scaMr_Q25IjmLfMrHwpHa4FBa6tqjAohcrxDatTFK5-VyJzl4m9jOFzZaE-YeE-Sf2GYJ_sXMI-hJPQPiClKdw0tHhDgVKr3AQ5rcuhnfkEePjL-aWuB2xIigIdVdinSXOg6PDBHsQKWjQn_8kBRgRRw1IDEOClnRn-2GT375G81aun632QuwlPiklMZ34KA2ZPATcPVUySysue5V6haUVcbv9JRKpoN7A5yu-KpXJUMX_837UppdjrDA_wVwqWFSQ9si-b4AyC7o2uUVZaeI3eNNcutw2w2m0PXEkYwi0lLjjN5dGHHDUpdEApWgvvDm00D1eFtE-ATssg-koZvRgVQ_FtJidICxoZ554wb0W7_fAIN0Pq3_wHAkpxqeVNWFKHncvqDgUG9mVk16JyQFCDzwQOeEDsYsTl8iL7C8b48g3YDCb4FKhuN8PFA7jimFxnIvS3sVec1EXV7Im30136XZIgl2lFfb0CuQ82Grj_YdHmIwyeu0ed44KutlxRVhAIM0UsJ_AL-uhSj4nROkowqfj-e2ECFHtC7Ty6SKaXsPTxVydEsWlbDMC7ww6oqv8oyHfJGzC1yaykYJj2QII3rHHW27M7B8ILl04JdkdjGYFmV9w3g2x4ZR6q9Nflzj95qeajCg-mnPzfxin4pi5c7vUcLuH9bjM9jGNh3PKZyZ8kXxPIxQL-6oVKLZvYybiJ8-YO8Q1wYlFWEuC2HY0DlhjKO3gvEQ0mk8aZSfFoVB2dyRmDsGpDTAO83jw2x0VmZZn1WhHfz7FcjYSHuH3C55kPkQ')

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
DROPBOX_TOKEN = os.getenv('DROPBOX_TOKEN', 'sl.u.AGM2F4B6sqJ6TH9jnrJSh7YzGqgEykrxmyhJb2-E1338Zk1FtC30y0SAIO2TYvk4HlxTjLhgi1HnXGjWVpaG7EQYGSxVSAXxrPcaBK8HLIZhrOK2XovblfOXLIyb00csJ3khI10zuRNwjUaj0ErFVWxIOpvg1Q73QkcQmbEj5t3yAQ5NmxXdU2ZguDN_j0jPivCySBvu7u1cVRD455sYDkQ4ufu-dvuJj7At5oKwtuxSrB8ySeaxaQfbukYSv-9gHZ2YHZtlDkhuHS_Ec5126Qr_OhoAZ_HFSeKaj4jUDSHsTU2c4k-giDpibkjasWgPbzGwsakaEVa3uzQyZNy5ZsqNyjq1xhGWLC0GhwDvG80sq6nYN5krWrnFwpdw_78B9qjvn1ff6j-D1kJ9xysawruroUHYLPEMjl0qOy3_e_74VKjL101B-QHtcsodek5PVYsa7JXR4x9WRqqvHt-_Dw6Kv_2MapWAALnXpc2APXQqSydG2R6bw-fJkEi7YIjTsFwv6WtXx7BYHa1FvSQ7HS2CGK7VVgNVlb03qWFKB3o6s3DO1q2TN3fNyFF_ypsMMwqU7cfyjSREfN857Y0p9SACQn3kKv401IRXncWdxE1Bm66g3DBADeI3OPHErZr6RgvHUTT0XZIqlSLY1scaMr_Q25IjmLfMrHwpHa4FBa6tqjAohcrxDatTFK5-VyJzl4m9jOFzZaE-YeE-Sf2GYJ_sXMI-hJPQPiClKdw0tHhDgVKr3AQ5rcuhnfkEePjL-aWuB2xIigIdVdinSXOg6PDBHsQKWjQn_8kBRgRRw1IDEOClnRn-2GT375G81aun632QuwlPiklMZ34KA2ZPATcPVUySysue5V6haUVcbv9JRKpoN7A5yu-KpXJUMX_837UppdjrDA_wVwqWFSQ9si-b4AyC7o2uUVZaeI3eNNcutw2w2m0PXEkYwi0lLjjN5dGHHDUpdEApWgvvDm00D1eFtE-ATssg-koZvRgVQ_FtJidICxoZ554wb0W7_fAIN0Pq3_wHAkpxqeVNWFKHncvqDgUG9mVk16JyQFCDzwQOeEDsYsTl8iL7C8b48g3YDCb4FKhuN8PFA7jimFxnIvS3sVec1EXV7Im30136XZIgl2lFfb0CuQ82Grj_YdHmIwyeu0ed44KutlxRVhAIM0UsJ_AL-uhSj4nROkowqfj-e2ECFHtC7Ty6SKaXsPTxVydEsWlbDMC7ww6oqv8oyHfJGzC1yaykYJj2QII3rHHW27M7B8ILl04JdkdjGYFmV9w3g2x4ZR6q9Nflzj95qeajCg-mnPzfxin4pi5c7vUcLuH9bjM9jGNh3PKZyZ8kXxPIxQL-6oVKLZvYybiJ8-YO8Q1wYlFWEuC2HY0DlhjKO3gvEQ0mk8aZSfFoVB2dyRmDsGpDTAO83jw2x0VmZZn1WhHfz7FcjYSHuH3C55kPkQ')

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
