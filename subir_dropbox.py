<<<<<<< HEAD
import dropbox
import os

# Token de acceso de Dropbox (se recomienda usar variable de entorno en producción)
DROPBOX_TOKEN = os.getenv('DROPBOX_TOKEN', 'sl.u.AGQedX7-tumPFUhyJKC2UpD0TVrlQeWoa6IHVLYj5oMHI_T6iyoD-nCXSmgOtjfjRScN4HomEKcviMzq8tlW1pxEmw8aUiAcnHfkuzXnK7NuaAei-Gr-oYdOllJsAkE5UleesDkH-f5WfwVMVoU-bVL8kWPUc8DZZ5cq0EL2dWD_0AIfJO4MlAGv1kkH47FwSLNJDfVAUwEFQHzTqysviCC6puk-X4zSKkRtzkzI4-QjSYDEko-0MBLJyQbjjxdGQrhUlC2xERLAkOCU5A4q5hbzCmtj24YpqVA1HRnKeTZZFVzc_TVE_MxWJdt6OPCr3E4x5EWthankRvzMStChIzs99aOtjG-9k6Ee3bZ2mHc64yt1Nmeg2Kqlc5NSEKzGTxM8nwKj2DvgAlXlMSRjNm7LdxPZ2DzALyfw6_smyXcs-FDu3iQ6_XyJx55DkqElIpK2dM76hkFNaV3x04-NOgWOaFSvK25agTMqL7cvUfAg2gOrAYJ1OzpRXs2oJ8qB6lWRsnGosm4Qs3OywGHKovZ1O4L_mA9LZBAItLd5tmqe3bhZg8B-5IjVG-P7x77bIS9ZsUndSik14FdUIy5uoBWkCZFexEgtUpoUR5guu4K6yOMeIRoK-qSIrP4Pg5EfYBSzf5zRd-vRzgiG3XHQCW86f_lKtHUUDIsNLoCIw16MsqqGJcYw2GvDBPN6TvnK2MYgLAzCsVxP4WDjHj4sfACJeD9QDzex1HYIa10Q4i6oLjANgIiJqN6myElai3NBIm_1S3KgSNuoMlQ2pA2S36MRO8cDrNlbUKeUu9uouNIWgNzuUZXbVLWY5MhyYZrteSXWX6wWhBW3uDK0LTYdtbugRzK9W8PHtC2vhR02Md14Jal2qzfM2B5sXQjRNNiA3HWusiLgVStPJ_q6Sbtd5ksmcvx5uciquQHRfJcRwRmupnUYWt27bQ88LFELLy_1DAJ7CaBQ4Emwi2uiJeS3JjXydIDTw1WNEtVBDf7qNNCZpYk5JB9oExl2HY-iV2PB4U8KjgpViorzVQwtzEJuJFHidMeeOs9TIFBuVkaHNEqivk2iHd21jX9CjGmUCIv5vdD4_9ThGGr_vQW4CqCWLrCC8Qeg3ojszExlAzY6RTUau51YzTkn1-TNVLQqsKx_013oV7UJ0JKYt6MNv8HsHR6m8_R4dmckgSQiNYPjEIA2I0V4CNBnFBAeLQJHdqM0S9kGvVEZBV60YwNebPxF1VPtdsyhbEp1Ug9X6enASuMvyiu8iIiFAD5xOccybFtLjKAsRUD2_nO50OvUWWMGt6xSKdVR4mlFP38Ecf6cnbkGBTuDGeg9x6vvSP7BUyE9y0Smuj89VcH1Q08iaqc54EpUOkIsGLgVqjEVcKTEZivnwIw_Ob_4rklNxzoX4D5wlBKx0_UP4pwAGjkCBK_mAkvfX3cJF_Pez1S66GXrUietMA')

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
DROPBOX_TOKEN = os.getenv('DROPBOX_TOKEN', 'sl.u.AGQedX7-tumPFUhyJKC2UpD0TVrlQeWoa6IHVLYj5oMHI_T6iyoD-nCXSmgOtjfjRScN4HomEKcviMzq8tlW1pxEmw8aUiAcnHfkuzXnK7NuaAei-Gr-oYdOllJsAkE5UleesDkH-f5WfwVMVoU-bVL8kWPUc8DZZ5cq0EL2dWD_0AIfJO4MlAGv1kkH47FwSLNJDfVAUwEFQHzTqysviCC6puk-X4zSKkRtzkzI4-QjSYDEko-0MBLJyQbjjxdGQrhUlC2xERLAkOCU5A4q5hbzCmtj24YpqVA1HRnKeTZZFVzc_TVE_MxWJdt6OPCr3E4x5EWthankRvzMStChIzs99aOtjG-9k6Ee3bZ2mHc64yt1Nmeg2Kqlc5NSEKzGTxM8nwKj2DvgAlXlMSRjNm7LdxPZ2DzALyfw6_smyXcs-FDu3iQ6_XyJx55DkqElIpK2dM76hkFNaV3x04-NOgWOaFSvK25agTMqL7cvUfAg2gOrAYJ1OzpRXs2oJ8qB6lWRsnGosm4Qs3OywGHKovZ1O4L_mA9LZBAItLd5tmqe3bhZg8B-5IjVG-P7x77bIS9ZsUndSik14FdUIy5uoBWkCZFexEgtUpoUR5guu4K6yOMeIRoK-qSIrP4Pg5EfYBSzf5zRd-vRzgiG3XHQCW86f_lKtHUUDIsNLoCIw16MsqqGJcYw2GvDBPN6TvnK2MYgLAzCsVxP4WDjHj4sfACJeD9QDzex1HYIa10Q4i6oLjANgIiJqN6myElai3NBIm_1S3KgSNuoMlQ2pA2S36MRO8cDrNlbUKeUu9uouNIWgNzuUZXbVLWY5MhyYZrteSXWX6wWhBW3uDK0LTYdtbugRzK9W8PHtC2vhR02Md14Jal2qzfM2B5sXQjRNNiA3HWusiLgVStPJ_q6Sbtd5ksmcvx5uciquQHRfJcRwRmupnUYWt27bQ88LFELLy_1DAJ7CaBQ4Emwi2uiJeS3JjXydIDTw1WNEtVBDf7qNNCZpYk5JB9oExl2HY-iV2PB4U8KjgpViorzVQwtzEJuJFHidMeeOs9TIFBuVkaHNEqivk2iHd21jX9CjGmUCIv5vdD4_9ThGGr_vQW4CqCWLrCC8Qeg3ojszExlAzY6RTUau51YzTkn1-TNVLQqsKx_013oV7UJ0JKYt6MNv8HsHR6m8_R4dmckgSQiNYPjEIA2I0V4CNBnFBAeLQJHdqM0S9kGvVEZBV60YwNebPxF1VPtdsyhbEp1Ug9X6enASuMvyiu8iIiFAD5xOccybFtLjKAsRUD2_nO50OvUWWMGt6xSKdVR4mlFP38Ecf6cnbkGBTuDGeg9x6vvSP7BUyE9y0Smuj89VcH1Q08iaqc54EpUOkIsGLgVqjEVcKTEZivnwIw_Ob_4rklNxzoX4D5wlBKx0_UP4pwAGjkCBK_mAkvfX3cJF_Pez1S66GXrUietMA')

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
