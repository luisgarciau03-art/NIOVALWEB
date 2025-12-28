<<<<<<< HEAD
import dropbox
import os

# Token de acceso de Dropbox (se recomienda usar variable de entorno en producción)
DROPBOX_TOKEN = os.getenv('DROPBOX_TOKEN', 'sl.u.AGMo2aQmDJj6_d7FdGE2usLuTNvKt1xjLFnRCog1yV5iA6B5l_qxeKdvEg0GLFYJAKcUG_1NklS1XqOvoa8LxzDNHy9XawYb-hjmrCg2IDjQXVhX34hg039P9U_oxornoqAD9okEbUe-W_zLtyKkw8pTE1FjytvMETknE3gfrxmGvD_1lHIOF8IogB1nbnoU5w9APzKQujJIeLgi6r7j29cPUI3FY9PQbOr0pUpESZLZgd2zNj6gN0lIORHKoEKywjaXK10FYC9kejiNN-uHuOnDBIMpGDTAEETjhHQXkmxXpY12HXnWwLIl5oKX1OLISQPgko48xjWyuUC6EQ9iVOze48rUSbLtuS6LBLYc_HC-FiqxPlB8TxaS7exqJ5Hj9K74Bpeo8OdV8Gt76n9IpW5QvJDIdrcJQvhc21hjZmyDAG3bmbh-SVFojQRT0ikcABzHMJUrftHHVRrSPq8kW1QpDDXcj6nAlEgmY34_kLljxp9AEZgrfAcFioc2u1GozSdt1ZjP_mwpV47E-q6s8yMOOQqgNxxWuZShUbKR_vjMJCN8jf7U9toBq0FxF0VQwcdIDV5GCdCWdWCZGwyyFNQGA_TRErUkTP3Lth8Zm4J9wdcjU90VQMBlzufy5f5iugeDJvQgB03q1UdloBu9VwxZS8cGpuht2GDPIFlzkdDtau5yRbNh9xIjZoea8mDFqkflgfX2mftr38EBB1VQ0_ikSmGhMGvnpoOlWZULkhltidCRiKBs8RSV9mUp6AE9_jzqg3XYzvXGrFAop4IegnT34xWa6waU8HZ1U1xyG6k83h4yc0C0AGzZk3S3DC3kScUbAmqrA5kducCw3zv35EtuBy_y9JbSrtaJ2CAyKJw-f7-LFFp1xhGT2OmSuL-uvVTbZR_Opjthdb797-BFo3uxJssf6G5oh_7kdAI9v4G86u6nV4YyvMB_A0Tuw7CJFTtKjR7PW9-gl-GAYut-vN-f8FZPS5nQ6uGyZt0RvByPU7Bd-IpIH7vZsRWn7DTsSloaZvBmPvAHAE7T7oKGIEhrIS9EM7lweT_tVp7THKP82E0YxCsd-G4f2RlZ78zO-n2rsT-5QVPAWV1NRtrY9EXB06NSomMOxSOcAzWgNyFvIa6206l5VUoZc5vX7FbIGHNueYUkfm08YPYGVLpbtO_kmJ380wmfXaJ_QHVYDVIdauO2yNJzqBVQU1n4esH8OK8YATmzGDiBwmmsybGfWF2Sr81WRUoCH1dUzmtDeRJ6Gxu7cUjNLjRZFlNJawvn4V_ljoh3ObEIoIrysKu5PJ43ySfuoaoBENFb-MoaYLiDDBIjXirTuDiemObfXPbgsI0mA3cBNPdsvpPkZMGg9AVHNaZUcMYW-u_RmnfkJpgeL8W9K8l7wnIl3Jmdww31_RcPAJIJOUSW0uuYmu0gKES9mjRzGMnyRq-SETxmk_Chpw')

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
DROPBOX_TOKEN = os.getenv('DROPBOX_TOKEN', 'sl.u.AGMo2aQmDJj6_d7FdGE2usLuTNvKt1xjLFnRCog1yV5iA6B5l_qxeKdvEg0GLFYJAKcUG_1NklS1XqOvoa8LxzDNHy9XawYb-hjmrCg2IDjQXVhX34hg039P9U_oxornoqAD9okEbUe-W_zLtyKkw8pTE1FjytvMETknE3gfrxmGvD_1lHIOF8IogB1nbnoU5w9APzKQujJIeLgi6r7j29cPUI3FY9PQbOr0pUpESZLZgd2zNj6gN0lIORHKoEKywjaXK10FYC9kejiNN-uHuOnDBIMpGDTAEETjhHQXkmxXpY12HXnWwLIl5oKX1OLISQPgko48xjWyuUC6EQ9iVOze48rUSbLtuS6LBLYc_HC-FiqxPlB8TxaS7exqJ5Hj9K74Bpeo8OdV8Gt76n9IpW5QvJDIdrcJQvhc21hjZmyDAG3bmbh-SVFojQRT0ikcABzHMJUrftHHVRrSPq8kW1QpDDXcj6nAlEgmY34_kLljxp9AEZgrfAcFioc2u1GozSdt1ZjP_mwpV47E-q6s8yMOOQqgNxxWuZShUbKR_vjMJCN8jf7U9toBq0FxF0VQwcdIDV5GCdCWdWCZGwyyFNQGA_TRErUkTP3Lth8Zm4J9wdcjU90VQMBlzufy5f5iugeDJvQgB03q1UdloBu9VwxZS8cGpuht2GDPIFlzkdDtau5yRbNh9xIjZoea8mDFqkflgfX2mftr38EBB1VQ0_ikSmGhMGvnpoOlWZULkhltidCRiKBs8RSV9mUp6AE9_jzqg3XYzvXGrFAop4IegnT34xWa6waU8HZ1U1xyG6k83h4yc0C0AGzZk3S3DC3kScUbAmqrA5kducCw3zv35EtuBy_y9JbSrtaJ2CAyKJw-f7-LFFp1xhGT2OmSuL-uvVTbZR_Opjthdb797-BFo3uxJssf6G5oh_7kdAI9v4G86u6nV4YyvMB_A0Tuw7CJFTtKjR7PW9-gl-GAYut-vN-f8FZPS5nQ6uGyZt0RvByPU7Bd-IpIH7vZsRWn7DTsSloaZvBmPvAHAE7T7oKGIEhrIS9EM7lweT_tVp7THKP82E0YxCsd-G4f2RlZ78zO-n2rsT-5QVPAWV1NRtrY9EXB06NSomMOxSOcAzWgNyFvIa6206l5VUoZc5vX7FbIGHNueYUkfm08YPYGVLpbtO_kmJ380wmfXaJ_QHVYDVIdauO2yNJzqBVQU1n4esH8OK8YATmzGDiBwmmsybGfWF2Sr81WRUoCH1dUzmtDeRJ6Gxu7cUjNLjRZFlNJawvn4V_ljoh3ObEIoIrysKu5PJ43ySfuoaoBENFb-MoaYLiDDBIjXirTuDiemObfXPbgsI0mA3cBNPdsvpPkZMGg9AVHNaZUcMYW-u_RmnfkJpgeL8W9K8l7wnIl3Jmdww31_RcPAJIJOUSW0uuYmu0gKES9mjRzGMnyRq-SETxmk_Chpw')

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
