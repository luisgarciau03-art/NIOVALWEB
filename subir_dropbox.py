<<<<<<< HEAD
import dropbox
import os

# Token de acceso de Dropbox (se recomienda usar variable de entorno en producción)
DROPBOX_TOKEN = os.getenv('DROPBOX_TOKEN', 'sl.u.AGNZ8CJz2Rj2c7P4vzzHpcCj-_pO6MCM_GiHKttoqKr5uSBTQEr-otZB7MTJsSAQEblQe3cXsJXxKuhwsk9zTR8OQdnJ-FGTcQ6XhD2LNusNSLJQ3PcQwtuseEgRkG412hCITbxHbd0wvy7RkjenGtqWPQXJYTBKOpQ6Hii8XY0xWAfpHC64QcqQ4n2TZwWNPRCxIDRJFeZZ3xe-fD-ZoZ-vzaRSRsdGXcoqhyWoccJoLvIBs-nvuHYPv7bB0RLVHzejdu5tcovE8hGllV_bbkbDHh_iiF4DI9qyyuWfhzvkw-QAgxJ_9KkEHstxFCLQ5rFVZBhEIprbOPUoTYJSrtI1Hg01MgmWpZn4a-5N1z95hxuU8xW2rOczDYRdxvAElB6ujSxKoB-hfRQDs617X2RZ4MFmXhtyzq36DG_JLt5ya13aG4XIkx8Jzcq42n95cSy7GhtYUyXlVw5O4_dZkVSGBAEG93_2snb2Eo_0UkEhX8fYv7mOL9dBFnt1E3fXcW-tMbqBWKaJs7tGd_fy3dg3XCJcuIszqMOxMa7LySLHlHCSUdfECG2vOZka94YWyBuRAG_sJ73sTUIOVvf1xxnLZCrKQtlyWIf57yja63Zf-UlOw0dXqQvyqe6sVfAl16qTTOk9bsSgSNMZ_h6niU7bN_EkcfakSAS5Lk4TQU5n-IEr9svCQrah6D3jRwSaTKFXlZtOIfIvV-7g39L-Qb42_WsRy2L_pR29jq7-0tZZvVFN3Hzy9uGJRHvwUKIkyG6yLZIBwMXRVSVvQT3MK7u9jM0cWuyVgFVsKj-aXaICHMdfnSK96ZcSjh7ejJ99KSXRSJTxVzW8KQ_nC-tRSZnvLUVDdRHEoGCpaDiIDQTwku9s9LCwWM7BVvJbA5M8vBON2OLWDKFcQYyLzKUkAJca1gb3i1mJcu0g0NBwnj2Nfw4Vt0y_2m43He3P_v6NItdDPHdBb9Bb0aM_N9ru4LXff0_dvnFD5_ez7ni8EsWpPVCR1IlE4p5USvYtpp1_TOnFIDhatTLIpzrbrafkYDHVlMH7epZ-FGFGsU-xLOWdsFuOsT19gJCQq57K19FPoxrr-yjIZ01N-pIoH9nq14x1zTmH4JJ5u7jzpAvLIPCLtwEJmkOYfgtLoEvsv2A7kpUFKc7Z679-4mXjgeR9O-m0euk750jxsKn5qviNhFs_Weryn0ftDpl_r5YT7AmE_XrauN66FQH7xAup7XocrhHBNKSDsfk1CY0zXJWZZ2Dg_yalxq8zsVr71N6bWR9yjVmQihp9J_aUje1loNw2yXsfSLOL47AILqIWgMQtkXklb3-rdFpN_RAxr2i4bmgcfjkPg8RhHxOsKP1KJJ8fXfVjEQC71ilJF_conlnCSPHrTTYY8DYDyhTaNgxkHBBbS04VycNtaehajkZv75ULR8U722L_WO8q_hjPrQnHaEg-OQ')

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
DROPBOX_TOKEN = os.getenv('DROPBOX_TOKEN', 'sl.u.AGNZ8CJz2Rj2c7P4vzzHpcCj-_pO6MCM_GiHKttoqKr5uSBTQEr-otZB7MTJsSAQEblQe3cXsJXxKuhwsk9zTR8OQdnJ-FGTcQ6XhD2LNusNSLJQ3PcQwtuseEgRkG412hCITbxHbd0wvy7RkjenGtqWPQXJYTBKOpQ6Hii8XY0xWAfpHC64QcqQ4n2TZwWNPRCxIDRJFeZZ3xe-fD-ZoZ-vzaRSRsdGXcoqhyWoccJoLvIBs-nvuHYPv7bB0RLVHzejdu5tcovE8hGllV_bbkbDHh_iiF4DI9qyyuWfhzvkw-QAgxJ_9KkEHstxFCLQ5rFVZBhEIprbOPUoTYJSrtI1Hg01MgmWpZn4a-5N1z95hxuU8xW2rOczDYRdxvAElB6ujSxKoB-hfRQDs617X2RZ4MFmXhtyzq36DG_JLt5ya13aG4XIkx8Jzcq42n95cSy7GhtYUyXlVw5O4_dZkVSGBAEG93_2snb2Eo_0UkEhX8fYv7mOL9dBFnt1E3fXcW-tMbqBWKaJs7tGd_fy3dg3XCJcuIszqMOxMa7LySLHlHCSUdfECG2vOZka94YWyBuRAG_sJ73sTUIOVvf1xxnLZCrKQtlyWIf57yja63Zf-UlOw0dXqQvyqe6sVfAl16qTTOk9bsSgSNMZ_h6niU7bN_EkcfakSAS5Lk4TQU5n-IEr9svCQrah6D3jRwSaTKFXlZtOIfIvV-7g39L-Qb42_WsRy2L_pR29jq7-0tZZvVFN3Hzy9uGJRHvwUKIkyG6yLZIBwMXRVSVvQT3MK7u9jM0cWuyVgFVsKj-aXaICHMdfnSK96ZcSjh7ejJ99KSXRSJTxVzW8KQ_nC-tRSZnvLUVDdRHEoGCpaDiIDQTwku9s9LCwWM7BVvJbA5M8vBON2OLWDKFcQYyLzKUkAJca1gb3i1mJcu0g0NBwnj2Nfw4Vt0y_2m43He3P_v6NItdDPHdBb9Bb0aM_N9ru4LXff0_dvnFD5_ez7ni8EsWpPVCR1IlE4p5USvYtpp1_TOnFIDhatTLIpzrbrafkYDHVlMH7epZ-FGFGsU-xLOWdsFuOsT19gJCQq57K19FPoxrr-yjIZ01N-pIoH9nq14x1zTmH4JJ5u7jzpAvLIPCLtwEJmkOYfgtLoEvsv2A7kpUFKc7Z679-4mXjgeR9O-m0euk750jxsKn5qviNhFs_Weryn0ftDpl_r5YT7AmE_XrauN66FQH7xAup7XocrhHBNKSDsfk1CY0zXJWZZ2Dg_yalxq8zsVr71N6bWR9yjVmQihp9J_aUje1loNw2yXsfSLOL47AILqIWgMQtkXklb3-rdFpN_RAxr2i4bmgcfjkPg8RhHxOsKP1KJJ8fXfVjEQC71ilJF_conlnCSPHrTTYY8DYDyhTaNgxkHBBbS04VycNtaehajkZv75ULR8U722L_WO8q_hjPrQnHaEg-OQ')

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
