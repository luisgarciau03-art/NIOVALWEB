<<<<<<< HEAD
import dropbox
import os

# Token de acceso de Dropbox (se recomienda usar variable de entorno en producción)
DROPBOX_TOKEN = os.getenv('DROPBOX_TOKEN', 'sl.u.AGMJN_ebl3Wkv8rYT0p1YPgq4b1A8zSxITGlrnATql0TKmnweGDZM587ciWbd9ZZ6ZzEtG8sIBUuMybIh5fcslDjYmwPXGLpDDUrol6zqlnmm63xtqW85lXhyZSqwYSYB5nm9ScHHJ34FuSgVMRKtHIGI-pyFnHtRsD_wZlN996H_WyCLWSXsPivu3AmHnVq_3utGb7b1J_O2K2DeDrIh-YVtMoQDCEHos6TJjQ05IddnWJUepnTZaN9cG75BaJT6aDOACpGpYZOh2W9Mcmi_ry9Ss6CdLU6f-B6MWRymua0tzuTbADMineqO8Or4k_VTofPhpFVyVYvlAPnQve5z1p_UbOQtBAkAZwfGj1Em7c6Jnz1nXSI-EPPItA7lAND-gk1u987K2vwPe_r61dk_yJvnIJJ5cs_8DROXQIbXfBUJhZEgBtz_BTF8siJCDyMU-hmpNUKR1_O2sNIbLjsxC6tpYLFyr43EpqwJh8T6FMQ0HAmqNnZNFsLb_p7OR_MLz6Yt9zeYN8NDctfG7czYmImQxEtAqfBIN4PJtHb-lJ_eFdE2mLZiFpJf9r3ZmPJCBKoSRbFCz1l5DktHYo_ELBkN3ZnHlCNbcJXiS4QzwI_R6UvwRDKXSdvPKUnd-qN-VojJRZLYuCvzHo_zyOaXCH6mIgz-WYIipZRBEjuI3WmQrXIQwLAtQpAqL5fIdHh0Q5TIEqRf8TcRJRJg_ZPPo5qJlgLQ4I7DM6AUSxlfTgJOKEjUSljTEcz8CQJPEsH0qYU6HID7cMFPM31b3eTtShPHZLJlz6GpmEonGwuhT08Hg1VXV0JSE8AtlRApe6ij3mXwIzjNxGMENxPW0kD6GgF749xQLSkn5Sn1UxBERP0-VL1ZHwjL_mj6ArTqhxK2LnjX_4DGUGH7sJutkpaDOSjp5jhVNX3nDLjeSvYg1kP1UjHEcS9TqcCev_fG-R-IC7I_FdYNFsAzftVLzmpbE64T6ReqDXn8ZIdBVqe-d10JW5J9N_jhLLZSuiiPRZ-bGZ3CgGIg3LYbKSkO4g85_bdHf0R6uG2yytnasVvwQYUhDKSx2-GVnDZTj-8dy_F9mutq32kFv0e4WL55Al0trlE-8ZDGOgBySjJhYP6Bll_IuPd2_3nKsCsU5iPfdfcs3KJqdRv6srTz1wbfwUy0Wb6OMu6DIeRMpwCb5rRzs7MVD-IEd2m1Fh-v4d5_laj8pGY87zsDkNbA1ERHt3E4gc_zmHOhxRBuHVkh22V1p-QEPHoqbWvC-KZzggZznPq_qw-dhSVXdC9Jae8nRnLoFSoJlufLZtFAz8WtXE_g5oGNLHjfq8GFlisAIQQI5TeYfgP2meGRxMmk-UQsphrfYWobkptTvaK0jKaF5-GZlgwjPlACY5TF4W7eFEkF3kP1rmZvArQGidL6gbP1jW-GoQemXmK_PwFx-vj0215mXR9ug')

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
DROPBOX_TOKEN = os.getenv('DROPBOX_TOKEN', 'sl.u.AGMJN_ebl3Wkv8rYT0p1YPgq4b1A8zSxITGlrnATql0TKmnweGDZM587ciWbd9ZZ6ZzEtG8sIBUuMybIh5fcslDjYmwPXGLpDDUrol6zqlnmm63xtqW85lXhyZSqwYSYB5nm9ScHHJ34FuSgVMRKtHIGI-pyFnHtRsD_wZlN996H_WyCLWSXsPivu3AmHnVq_3utGb7b1J_O2K2DeDrIh-YVtMoQDCEHos6TJjQ05IddnWJUepnTZaN9cG75BaJT6aDOACpGpYZOh2W9Mcmi_ry9Ss6CdLU6f-B6MWRymua0tzuTbADMineqO8Or4k_VTofPhpFVyVYvlAPnQve5z1p_UbOQtBAkAZwfGj1Em7c6Jnz1nXSI-EPPItA7lAND-gk1u987K2vwPe_r61dk_yJvnIJJ5cs_8DROXQIbXfBUJhZEgBtz_BTF8siJCDyMU-hmpNUKR1_O2sNIbLjsxC6tpYLFyr43EpqwJh8T6FMQ0HAmqNnZNFsLb_p7OR_MLz6Yt9zeYN8NDctfG7czYmImQxEtAqfBIN4PJtHb-lJ_eFdE2mLZiFpJf9r3ZmPJCBKoSRbFCz1l5DktHYo_ELBkN3ZnHlCNbcJXiS4QzwI_R6UvwRDKXSdvPKUnd-qN-VojJRZLYuCvzHo_zyOaXCH6mIgz-WYIipZRBEjuI3WmQrXIQwLAtQpAqL5fIdHh0Q5TIEqRf8TcRJRJg_ZPPo5qJlgLQ4I7DM6AUSxlfTgJOKEjUSljTEcz8CQJPEsH0qYU6HID7cMFPM31b3eTtShPHZLJlz6GpmEonGwuhT08Hg1VXV0JSE8AtlRApe6ij3mXwIzjNxGMENxPW0kD6GgF749xQLSkn5Sn1UxBERP0-VL1ZHwjL_mj6ArTqhxK2LnjX_4DGUGH7sJutkpaDOSjp5jhVNX3nDLjeSvYg1kP1UjHEcS9TqcCev_fG-R-IC7I_FdYNFsAzftVLzmpbE64T6ReqDXn8ZIdBVqe-d10JW5J9N_jhLLZSuiiPRZ-bGZ3CgGIg3LYbKSkO4g85_bdHf0R6uG2yytnasVvwQYUhDKSx2-GVnDZTj-8dy_F9mutq32kFv0e4WL55Al0trlE-8ZDGOgBySjJhYP6Bll_IuPd2_3nKsCsU5iPfdfcs3KJqdRv6srTz1wbfwUy0Wb6OMu6DIeRMpwCb5rRzs7MVD-IEd2m1Fh-v4d5_laj8pGY87zsDkNbA1ERHt3E4gc_zmHOhxRBuHVkh22V1p-QEPHoqbWvC-KZzggZznPq_qw-dhSVXdC9Jae8nRnLoFSoJlufLZtFAz8WtXE_g5oGNLHjfq8GFlisAIQQI5TeYfgP2meGRxMmk-UQsphrfYWobkptTvaK0jKaF5-GZlgwjPlACY5TF4W7eFEkF3kP1rmZvArQGidL6gbP1jW-GoQemXmK_PwFx-vj0215mXR9ug')

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
