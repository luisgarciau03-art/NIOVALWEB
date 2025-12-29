<<<<<<< HEAD
import dropbox
import os

# Token de acceso de Dropbox (se recomienda usar variable de entorno en producción)
DROPBOX_TOKEN = os.getenv('DROPBOX_TOKEN', 'sl.u.AGPAhd1_dIqHz3pTv7Oyn_F5S63nBhNxlXEFAcn_A0G38wTRlpGqB-0xnAYL2wt-7hPq68CVlzLlguOa_hxlytlKdscSpfBlwkrDsuiJ8qjqnLY2KHD5L0HrvGFbHbUzzhrnSTz4ErJF974HvSJii0Luh42sDuRp_gzFS9EwowlQK3RYzsDJP22LwIsWK1K5um9JadUlV24XbiDWWO4_Tbj1GU4WyuyIKaJnQXMp4vKFJzh2WQJVU6heGHj57THU6Y0JZY5AFgJlU_4Jdc_bQ0Jmzi4oJuwm8WVue_R4rJB49ayWjwIdScEBLp-6L0rB6ZRni_aFZaBW-ugDdKsPtNwXEnXgsCAQcKRZQrVsqLJjec7DN1O5ek_sJDZhk5n2fNGeQDSEDTcZ77U-PEIDk1UWKpegoWQ9yWah74F6R0Y4N9gdqvr-lHVnbpXGZk3cZIvyChuCEbueqA1t4AlfulPHFh_u1bZSW2KlUKaJ2x8N72j4CDE4OrPmo_0YcYpIiXTSmYwV6XIK5dbhqEkrsHJH8M2QeTCovMNWQMVNCr88OQwLym9e1BEEuGjtMlIiqEV703T43Wv9JPH_p9lpYWQvrKowIepd_XISvWDZHjmyMn6agjKG98ZWxbl_Z5H5gIAmd0WS4WVGJDuGJYDmSb10WvX7Ghg-JGQ1x_3ZyUTVVI-Wc7o6eFiiXJmS9XH8ZTBfqsWkilR_Y9wrgPOPwBchDJSnYp0gequ86pHzroz_i6q8LMhGexOmaJeilZfvBM8zghXAK8wOqCib2z5z4FPnBbxpsFU52pXoWa6TRuD0YfIopzOInK-WeCLgYupxmE6-sQ6cWT7P8diikg4ZNPGvTd8plG8vBxX9AohBM0PbRnUYnmmTPBo5xhZS-ixVuTl1zRZTEMOkZby_1hjAid2QAmnI96_hwJTmf0wCbSliNRf8BDdvBDeUNxnrQQKPAvI_ITrENu9cu_EbrSGxr7bPEey1YpWRugu5dsjzPZOJvjY2kn6ag_H4w0uAq_9sAWvIm3HbdVXCjevjpfK3vP0cDF9fTaUoasjLetADZlOrH0XXOrRaDxOJ8mv747kqQc9c-e64-koc3ht9a7HlUsg7ZPHQ_IcA1JyNYXbwOoY0aC8-95l8GKGCi67CDKVD2wJirWE5isox1pc8xtM9VaE-u1mTHGKIawjFrRggDfWr7_zYrhMEojRpCzNkxkcJgm4syM7H7kn3IrdUxgcRLm2UME8I2sA0qcIzBW8CMO6iNRZ90lC8rfO6waSO_QP2wNuQMJQMpsruL-PCfFfZRmw7-8rKkSEgZfBkFcHdRjD3m-00eKCGNGATsV3EWza7j_OTqcJK-ny9S4dOSj0iwpcidFVTqWn8A8rsC8KXgDeA3Iru5-sSx7TjbZ53Ho4U4U1WWszqr6vX1zqBk27bN56SJUnTyjGgHTx24FMDXwK_Zw')

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
DROPBOX_TOKEN = os.getenv('DROPBOX_TOKEN', 'sl.u.AGPAhd1_dIqHz3pTv7Oyn_F5S63nBhNxlXEFAcn_A0G38wTRlpGqB-0xnAYL2wt-7hPq68CVlzLlguOa_hxlytlKdscSpfBlwkrDsuiJ8qjqnLY2KHD5L0HrvGFbHbUzzhrnSTz4ErJF974HvSJii0Luh42sDuRp_gzFS9EwowlQK3RYzsDJP22LwIsWK1K5um9JadUlV24XbiDWWO4_Tbj1GU4WyuyIKaJnQXMp4vKFJzh2WQJVU6heGHj57THU6Y0JZY5AFgJlU_4Jdc_bQ0Jmzi4oJuwm8WVue_R4rJB49ayWjwIdScEBLp-6L0rB6ZRni_aFZaBW-ugDdKsPtNwXEnXgsCAQcKRZQrVsqLJjec7DN1O5ek_sJDZhk5n2fNGeQDSEDTcZ77U-PEIDk1UWKpegoWQ9yWah74F6R0Y4N9gdqvr-lHVnbpXGZk3cZIvyChuCEbueqA1t4AlfulPHFh_u1bZSW2KlUKaJ2x8N72j4CDE4OrPmo_0YcYpIiXTSmYwV6XIK5dbhqEkrsHJH8M2QeTCovMNWQMVNCr88OQwLym9e1BEEuGjtMlIiqEV703T43Wv9JPH_p9lpYWQvrKowIepd_XISvWDZHjmyMn6agjKG98ZWxbl_Z5H5gIAmd0WS4WVGJDuGJYDmSb10WvX7Ghg-JGQ1x_3ZyUTVVI-Wc7o6eFiiXJmS9XH8ZTBfqsWkilR_Y9wrgPOPwBchDJSnYp0gequ86pHzroz_i6q8LMhGexOmaJeilZfvBM8zghXAK8wOqCib2z5z4FPnBbxpsFU52pXoWa6TRuD0YfIopzOInK-WeCLgYupxmE6-sQ6cWT7P8diikg4ZNPGvTd8plG8vBxX9AohBM0PbRnUYnmmTPBo5xhZS-ixVuTl1zRZTEMOkZby_1hjAid2QAmnI96_hwJTmf0wCbSliNRf8BDdvBDeUNxnrQQKPAvI_ITrENu9cu_EbrSGxr7bPEey1YpWRugu5dsjzPZOJvjY2kn6ag_H4w0uAq_9sAWvIm3HbdVXCjevjpfK3vP0cDF9fTaUoasjLetADZlOrH0XXOrRaDxOJ8mv747kqQc9c-e64-koc3ht9a7HlUsg7ZPHQ_IcA1JyNYXbwOoY0aC8-95l8GKGCi67CDKVD2wJirWE5isox1pc8xtM9VaE-u1mTHGKIawjFrRggDfWr7_zYrhMEojRpCzNkxkcJgm4syM7H7kn3IrdUxgcRLm2UME8I2sA0qcIzBW8CMO6iNRZ90lC8rfO6waSO_QP2wNuQMJQMpsruL-PCfFfZRmw7-8rKkSEgZfBkFcHdRjD3m-00eKCGNGATsV3EWza7j_OTqcJK-ny9S4dOSj0iwpcidFVTqWn8A8rsC8KXgDeA3Iru5-sSx7TjbZ53Ho4U4U1WWszqr6vX1zqBk27bN56SJUnTyjGgHTx24FMDXwK_Zw')

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
