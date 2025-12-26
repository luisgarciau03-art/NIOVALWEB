<<<<<<< HEAD
import dropbox
import os

# Token de acceso de Dropbox (se recomienda usar variable de entorno en producción)
DROPBOX_TOKEN = os.getenv('DROPBOX_TOKEN', 'sl.u.AGPpxtruZmc_2RhK9cgvg7WBoWpuc_0mlzGjhGxNmHvvo01XSe1ef5akRLiivI6OiwJ8DKJYsvnkamtTHTsb-EkRUYF3MbMwLrjg389VNCvHrYzAg8vojrdA_vyA_ur8vYbUc78cgW-ajlJIKjFF_vUQuAqGwI9b9Hpv5-Vs_qM_RqG6W5PSCSZd5dC1mKTzZFaiAX0TggPMwwG1rS26iFjsTNniqDa2W8pgdse55r_gAvlJE9s_aXK0HIMGfnjwbC2CpBb-ht7G43hMTLsfpuSEi1WbmmbWHyfLcRC04uyIhr3PTC5g4dtpJD7D5xlc6BaX2lntHbvD1Wt6lyGPRZWfN7tpfjqevREg8Z5_32LDXHov7GoxM--nn1mLR5xa9Xz0EVgL5Rkn6SpWufWLAaW0mqUKsbO-EjlEgW4d0ua_-zaP1R78aQCCt5KW9TYartJtYFstVysSMylSP7v7VCxxAQFhl4oK4uxr1zwFxwXSpz9EB0Diz4F09dwDn8-R6wccvQJKlf9375fNnuTBDrgYT40JjpVc80qSIh9KVBF0hC7FRaP2ePnxKh_GHpExpOfDFhTxpBoiEZ-KyllxaBwOnV_w1b_K6b0kcCbN84h7-G7_Cekc6Fy7qUh-_vtoIrfPIlmK2cNnt_lK1sogPs5kdgNQE5AN9ZmLRfKClif5q1-nGThY12K-fH7Dn7O5Bx-oahU8hO4oMTvC7gXcqUWbqAQyNu84-Kej31sVYdTeztvSc5mI0z00Ue5OXGcCEkf_qPbJXfe86ydV3miCTRJ3jkrzvQ3oaO6roNx-X6cBzcm_9PAP8wgyPCfTGKONWcIC3L1b92q0PeRllVdEGsI70FF5fjp1EjHI6KaWxhoJfFql4o7ilju_yq-lZ49FYPc6Y1tb00-s2v_q4XhzooCLVqOwn9skvl8oyryt2zwwvpyThLBTllpnQwuoiBjGyKl_5sSDtm9Bx0bq_9zPhK-6mfwjR-l82AJrNTj5MZwxXTR2em8d7Lw2MDx-gSAwV_Ouef0rfX5R3xfdg2NEfDoWffZSGrlBAGxRxPOqaggxE5nc3W1GhJQ9edvYGcyzvlHRzfWEbVM0dgeHri7DImykQwhuTuRueoIkpU1iWaN_SeEEz0J-vi5C5XgeGFj-gfOby-CtGERYBmKvOl2rjlgKuOONkuQB16qti0xdf8N-78K26DQzvnSB5p0u77jEpBJnGypnUu_CTsgMsQuibLFPXbIR7gqA3XMbODms3Xk4Ij0ILK1VV_pdOQ_OvkTB1LAKSuYwdn7rWLdY8pyDdFpDDPVCfx1bdZ7b3boMVvHGlOCOmh204TImPUmRDInd1Qw-3VDZBW-d80vw5QTxTPeJqYe6MlTXZn-311kV8sTqwK4SyNCPf3RPLWcdCifTSW-MRtCljKjXAzSQI809zWwe93C77DIHarv7nwFdeyNFqw')

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
DROPBOX_TOKEN = os.getenv('DROPBOX_TOKEN', 'sl.u.AGPpxtruZmc_2RhK9cgvg7WBoWpuc_0mlzGjhGxNmHvvo01XSe1ef5akRLiivI6OiwJ8DKJYsvnkamtTHTsb-EkRUYF3MbMwLrjg389VNCvHrYzAg8vojrdA_vyA_ur8vYbUc78cgW-ajlJIKjFF_vUQuAqGwI9b9Hpv5-Vs_qM_RqG6W5PSCSZd5dC1mKTzZFaiAX0TggPMwwG1rS26iFjsTNniqDa2W8pgdse55r_gAvlJE9s_aXK0HIMGfnjwbC2CpBb-ht7G43hMTLsfpuSEi1WbmmbWHyfLcRC04uyIhr3PTC5g4dtpJD7D5xlc6BaX2lntHbvD1Wt6lyGPRZWfN7tpfjqevREg8Z5_32LDXHov7GoxM--nn1mLR5xa9Xz0EVgL5Rkn6SpWufWLAaW0mqUKsbO-EjlEgW4d0ua_-zaP1R78aQCCt5KW9TYartJtYFstVysSMylSP7v7VCxxAQFhl4oK4uxr1zwFxwXSpz9EB0Diz4F09dwDn8-R6wccvQJKlf9375fNnuTBDrgYT40JjpVc80qSIh9KVBF0hC7FRaP2ePnxKh_GHpExpOfDFhTxpBoiEZ-KyllxaBwOnV_w1b_K6b0kcCbN84h7-G7_Cekc6Fy7qUh-_vtoIrfPIlmK2cNnt_lK1sogPs5kdgNQE5AN9ZmLRfKClif5q1-nGThY12K-fH7Dn7O5Bx-oahU8hO4oMTvC7gXcqUWbqAQyNu84-Kej31sVYdTeztvSc5mI0z00Ue5OXGcCEkf_qPbJXfe86ydV3miCTRJ3jkrzvQ3oaO6roNx-X6cBzcm_9PAP8wgyPCfTGKONWcIC3L1b92q0PeRllVdEGsI70FF5fjp1EjHI6KaWxhoJfFql4o7ilju_yq-lZ49FYPc6Y1tb00-s2v_q4XhzooCLVqOwn9skvl8oyryt2zwwvpyThLBTllpnQwuoiBjGyKl_5sSDtm9Bx0bq_9zPhK-6mfwjR-l82AJrNTj5MZwxXTR2em8d7Lw2MDx-gSAwV_Ouef0rfX5R3xfdg2NEfDoWffZSGrlBAGxRxPOqaggxE5nc3W1GhJQ9edvYGcyzvlHRzfWEbVM0dgeHri7DImykQwhuTuRueoIkpU1iWaN_SeEEz0J-vi5C5XgeGFj-gfOby-CtGERYBmKvOl2rjlgKuOONkuQB16qti0xdf8N-78K26DQzvnSB5p0u77jEpBJnGypnUu_CTsgMsQuibLFPXbIR7gqA3XMbODms3Xk4Ij0ILK1VV_pdOQ_OvkTB1LAKSuYwdn7rWLdY8pyDdFpDDPVCfx1bdZ7b3boMVvHGlOCOmh204TImPUmRDInd1Qw-3VDZBW-d80vw5QTxTPeJqYe6MlTXZn-311kV8sTqwK4SyNCPf3RPLWcdCifTSW-MRtCljKjXAzSQI809zWwe93C77DIHarv7nwFdeyNFqw')

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
