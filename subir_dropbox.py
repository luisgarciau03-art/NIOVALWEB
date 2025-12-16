<<<<<<< HEAD
import dropbox
import os

# Token de acceso de Dropbox (se recomienda usar variable de entorno en producción)
DROPBOX_TOKEN = os.getenv('DROPBOX_TOKEN', 'sl.u.AGJMpaSSvHdRss-_uszDt2lbbZ9uxJYVZiukGy-X2xlYonbEHdp8An26Bh_U_CRW3pp_sv1IHYnxDWpNh9plbGOT2j8KtWmbJI3OUKTqnE1uMMAmoMmNuMOwucLxk2TvNJnnZlRvg-78_ujeSElJF4t7E_PaDUOpf3HtVPi0CLHVJlcQCjTNf6K0znDVR5Qim3KWsMG63Y_pf57f4HD1Uh0F_qwzdvuRTOJyD_iQ-xeGFKosLDDoPT7uxf6QTR7dQUzKS2o-MB5FjpmaHlASvC4JGQvMp1vZIV4lADq3jmAAtHczzoJIHP6TAe6K_XKwMDhb1nBlPnx001EJYK594gaUTv1fq7xzMxep9gjYf0MCwJFVbFoDGQhly1JX2QuE7j7DNiq6-U6wydTiZCtksX_BGOaaiDpZGwopgyfWTCxcIx1q3j0GWpnTAG2y7jali0lOBf4a0thNStRHONqrpWhvtlLHubJGqGEBU6mGoy56zGMyoJYx26Ou412_LLJAgQt0JjuEv2wDK8LE8yF3eH8qhmUntPXEs1OinbY6EYC5DASJdhVmNZA2a2Op3nfIaOaV2rfkuYgXngsqk1iIWh36os5sZVQYTL-2hNMCtKRMNa-i3QQGHbXIZkvAQhs9fnFRYELP2LuSQ1EzTOxCvt-Owusv2ivUWOnI1NOgCXynj8FPtjBG25QO4SEJAjcNVIXcrMmPQiUWxPIWZickIQf66ypmFXn3gr6Ydw7Vc7vqYgQVLzKf5LRbrngAK9Y7BFJCDZkTqtfb-EMFyP9id_scz0RqXH7il5V7KXh_FTPNwWFxDZkftnK27f5S6eUi-FVHvO37_BgEH6Mp62mXB7Mbq8ADBmjgKlOk8DZbKkH8jk0K8qGmQlOT1NZgdKz29S5RbT2JLWIk7YNYygBi1g1snjBVaL6LzBFzDj78AxUAOHjF_5_aDYYxt6m5L_FfP8JWZ_CTZotIIi9EaKgoo3SA4bA4aCrnqDhqqcz9djI5sS6uFCc4C23cXs25xiYBejOl8kpF_qQXqCrNjZK4iC3a9BIlZ6noeewdcWoybCqzoYa0aHroISqk_8VtwBMCkseqwYKOdor20wiL3JNcB9cES6HnjF1Ngw2SjsD_sa9ILg7ytGfAATvmbTFJpWav8En6wBGzLUQ3_chSUwveRpAHPyvBeyVOeEvt5AkpDHqp16fyAj9KwDNx6moHz6SWgR9yTqStpSoX4vhbtUfaTYUZp1BORgUPCgEkxXEm3a3VnBzfbi5HzZ04F3KJI4NY3nUhdoaf7GD9fCCNL4PBmKPBLCVfge7g-q3gsIkDu12v8ZCvCfYGl0bzaQD0num4KG54n4slakYYMk_H5Y_DLZGpfnNK_Geayqa9JssUFpZG9RbxsDf3j-RrYGAcvmOBrHVHIOOB0nwwJ-T9R5FN-ZYmWD7iZvMd_UCmg_1HmAnFBw')

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
DROPBOX_TOKEN = os.getenv('DROPBOX_TOKEN', 'sl.u.AGJMpaSSvHdRss-_uszDt2lbbZ9uxJYVZiukGy-X2xlYonbEHdp8An26Bh_U_CRW3pp_sv1IHYnxDWpNh9plbGOT2j8KtWmbJI3OUKTqnE1uMMAmoMmNuMOwucLxk2TvNJnnZlRvg-78_ujeSElJF4t7E_PaDUOpf3HtVPi0CLHVJlcQCjTNf6K0znDVR5Qim3KWsMG63Y_pf57f4HD1Uh0F_qwzdvuRTOJyD_iQ-xeGFKosLDDoPT7uxf6QTR7dQUzKS2o-MB5FjpmaHlASvC4JGQvMp1vZIV4lADq3jmAAtHczzoJIHP6TAe6K_XKwMDhb1nBlPnx001EJYK594gaUTv1fq7xzMxep9gjYf0MCwJFVbFoDGQhly1JX2QuE7j7DNiq6-U6wydTiZCtksX_BGOaaiDpZGwopgyfWTCxcIx1q3j0GWpnTAG2y7jali0lOBf4a0thNStRHONqrpWhvtlLHubJGqGEBU6mGoy56zGMyoJYx26Ou412_LLJAgQt0JjuEv2wDK8LE8yF3eH8qhmUntPXEs1OinbY6EYC5DASJdhVmNZA2a2Op3nfIaOaV2rfkuYgXngsqk1iIWh36os5sZVQYTL-2hNMCtKRMNa-i3QQGHbXIZkvAQhs9fnFRYELP2LuSQ1EzTOxCvt-Owusv2ivUWOnI1NOgCXynj8FPtjBG25QO4SEJAjcNVIXcrMmPQiUWxPIWZickIQf66ypmFXn3gr6Ydw7Vc7vqYgQVLzKf5LRbrngAK9Y7BFJCDZkTqtfb-EMFyP9id_scz0RqXH7il5V7KXh_FTPNwWFxDZkftnK27f5S6eUi-FVHvO37_BgEH6Mp62mXB7Mbq8ADBmjgKlOk8DZbKkH8jk0K8qGmQlOT1NZgdKz29S5RbT2JLWIk7YNYygBi1g1snjBVaL6LzBFzDj78AxUAOHjF_5_aDYYxt6m5L_FfP8JWZ_CTZotIIi9EaKgoo3SA4bA4aCrnqDhqqcz9djI5sS6uFCc4C23cXs25xiYBejOl8kpF_qQXqCrNjZK4iC3a9BIlZ6noeewdcWoybCqzoYa0aHroISqk_8VtwBMCkseqwYKOdor20wiL3JNcB9cES6HnjF1Ngw2SjsD_sa9ILg7ytGfAATvmbTFJpWav8En6wBGzLUQ3_chSUwveRpAHPyvBeyVOeEvt5AkpDHqp16fyAj9KwDNx6moHz6SWgR9yTqStpSoX4vhbtUfaTYUZp1BORgUPCgEkxXEm3a3VnBzfbi5HzZ04F3KJI4NY3nUhdoaf7GD9fCCNL4PBmKPBLCVfge7g-q3gsIkDu12v8ZCvCfYGl0bzaQD0num4KG54n4slakYYMk_H5Y_DLZGpfnNK_Geayqa9JssUFpZG9RbxsDf3j-RrYGAcvmOBrHVHIOOB0nwwJ-T9R5FN-ZYmWD7iZvMd_UCmg_1HmAnFBw')

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
