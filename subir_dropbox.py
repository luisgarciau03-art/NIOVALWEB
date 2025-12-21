<<<<<<< HEAD
import dropbox
import os

# Token de acceso de Dropbox (se recomienda usar variable de entorno en producción)
DROPBOX_TOKEN = os.getenv('DROPBOX_TOKEN', 'sl.u.AGL8huTiudZoneA8VyVPyh51iU9B3VEYkGjCR_PbbLAVhkTQOZc-naBmYHsj8XcAudQoEL8FNNyKYUiVuFJAkIIIVvRK31X9Ll6OJs3j13Ei0WzHpP1SdvlRCOyETo8-SQbTUpPK7lff9SDoBOKI4P0hvqY2PHyiKEvJsto819A5l6c5rSBLIkn6sSNVhYPjHosyDE_aiyjTUdfvumM4djqw2QPeegfLuTI7H06_--4hKOnF7kf0o420N4Y4-hH4GX7PM8nIH84Pd4kQ99kgNi9JklKr7RUM5sbcEge7q_XaK7xd1tPiN1CfXWpV5auN2XLztia2ynVWoVVXCnjyO0w-ZqB-E_08x0O5tRM_SzOk-2QV7Tqik19S8b37OCfDmopUgPODAck7YpWgVKmDzrySNc8kMxvKzKXzsSMVhTBq-gSc6Dl8ExsSCcWV8XPFa42jJMCNA1emNw0-UoSjCpNpmyX1cHXe3Gt3T_lOQsMUyZEfCVR3F1gXDS84fXtZlujvdX7JZMVKXnlLmjv8EPJys1UhIolzQtMiHBsJLdU7zv92jiuBit_DezC28n717c08rn4Kd13sr0GJT5OoZUkgwOf2cgxbTJ6dw4nnP6dt2Fyb4XKqsw8-mfy2szONsSImNVaAFRs3dbLiFXt8kHsydezSXWSFbaEU1IxU3uOtO9oTIfOiFhLYWhs_ba4spQL4p3b9q8Mi1sJmFHPsAkLNkr1xlbp1j3ljN_pQPQk8YBFrL9oLdMT3JUu95HkcKqU_ZiPxdc_Qu_rm4IgbiUaFW81vk28UifD7LNdWuJaGlAgUeuCvChmZFn3XRPcEF5MurdIyBSno44_2yM9u_rQoqo9nAocMCjYcu7XOqE6mR4EXe8CyuxL1tPj8qRz60RB0Qu1J6PnGhYmm17fYhiwV2O822Wxm1uAVVg-1hminuM7zsewQRMV4w9Hd8s-OJcj6cDZrOOs0R071DSK5qPZxPFXOXrUGDTQug4ivDddr_I5fTGhRemonBJBfznsdKj4dxNV41_zFGHqImhp-Nl-hm9vXYwS1oO2JgLa_DaZZEQq0khDi6mRWIRoykwVNU3NHladNbQNuNLsELcSqU6X1S2jmvAO4hajd63yGkngZIPgbrDjLI1m8q839ZK6R19yMQjaiSEKYh2nGRMpIR9Wt9j4GnfrUe-s7-x3EVa4HVRFNf_9PIiGKS9HvYHs0mVhvLsKTPOphJ0YGqgmYOYJFpdecrwi9zTcW5JGl4FBkjwGEzrB1DkjgkeKY3uxtH3bUjD-y-sYYS5uRiUm_yAXZgsuvxlX5xTJlhF4Uz8xKyeGfmKMxddZDiJ-CDwbE3j2g8MT_kfrS1eYZYVoLi5sndWU5v4R5TDI7xjRnQ6fguEn0Xv8nSEr7d_eX2A89E44IiqW4R1S3wa-9i4cAwtR8MRziYop7nSdNBk1zUiVNEg')

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
DROPBOX_TOKEN = os.getenv('DROPBOX_TOKEN', 'sl.u.AGL8huTiudZoneA8VyVPyh51iU9B3VEYkGjCR_PbbLAVhkTQOZc-naBmYHsj8XcAudQoEL8FNNyKYUiVuFJAkIIIVvRK31X9Ll6OJs3j13Ei0WzHpP1SdvlRCOyETo8-SQbTUpPK7lff9SDoBOKI4P0hvqY2PHyiKEvJsto819A5l6c5rSBLIkn6sSNVhYPjHosyDE_aiyjTUdfvumM4djqw2QPeegfLuTI7H06_--4hKOnF7kf0o420N4Y4-hH4GX7PM8nIH84Pd4kQ99kgNi9JklKr7RUM5sbcEge7q_XaK7xd1tPiN1CfXWpV5auN2XLztia2ynVWoVVXCnjyO0w-ZqB-E_08x0O5tRM_SzOk-2QV7Tqik19S8b37OCfDmopUgPODAck7YpWgVKmDzrySNc8kMxvKzKXzsSMVhTBq-gSc6Dl8ExsSCcWV8XPFa42jJMCNA1emNw0-UoSjCpNpmyX1cHXe3Gt3T_lOQsMUyZEfCVR3F1gXDS84fXtZlujvdX7JZMVKXnlLmjv8EPJys1UhIolzQtMiHBsJLdU7zv92jiuBit_DezC28n717c08rn4Kd13sr0GJT5OoZUkgwOf2cgxbTJ6dw4nnP6dt2Fyb4XKqsw8-mfy2szONsSImNVaAFRs3dbLiFXt8kHsydezSXWSFbaEU1IxU3uOtO9oTIfOiFhLYWhs_ba4spQL4p3b9q8Mi1sJmFHPsAkLNkr1xlbp1j3ljN_pQPQk8YBFrL9oLdMT3JUu95HkcKqU_ZiPxdc_Qu_rm4IgbiUaFW81vk28UifD7LNdWuJaGlAgUeuCvChmZFn3XRPcEF5MurdIyBSno44_2yM9u_rQoqo9nAocMCjYcu7XOqE6mR4EXe8CyuxL1tPj8qRz60RB0Qu1J6PnGhYmm17fYhiwV2O822Wxm1uAVVg-1hminuM7zsewQRMV4w9Hd8s-OJcj6cDZrOOs0R071DSK5qPZxPFXOXrUGDTQug4ivDddr_I5fTGhRemonBJBfznsdKj4dxNV41_zFGHqImhp-Nl-hm9vXYwS1oO2JgLa_DaZZEQq0khDi6mRWIRoykwVNU3NHladNbQNuNLsELcSqU6X1S2jmvAO4hajd63yGkngZIPgbrDjLI1m8q839ZK6R19yMQjaiSEKYh2nGRMpIR9Wt9j4GnfrUe-s7-x3EVa4HVRFNf_9PIiGKS9HvYHs0mVhvLsKTPOphJ0YGqgmYOYJFpdecrwi9zTcW5JGl4FBkjwGEzrB1DkjgkeKY3uxtH3bUjD-y-sYYS5uRiUm_yAXZgsuvxlX5xTJlhF4Uz8xKyeGfmKMxddZDiJ-CDwbE3j2g8MT_kfrS1eYZYVoLi5sndWU5v4R5TDI7xjRnQ6fguEn0Xv8nSEr7d_eX2A89E44IiqW4R1S3wa-9i4cAwtR8MRziYop7nSdNBk1zUiVNEg')

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
