<<<<<<< HEAD
import dropbox
import os

# Token de acceso de Dropbox (se recomienda usar variable de entorno en producción)
DROPBOX_TOKEN = os.getenv('DROPBOX_TOKEN', 'sl.u.AGN4ro-oeoh-ApfGemZPY2n7Qas9Ad9RVScYSf1K50auXY-wW2Bg1YnNgCX8y-fU_rSQwcqbgNapPdSTDLpJ2MfUzjIOntUT7jggFYUvnyjbEwnkebyY6-7PqySnJ172QWXy-fqs7LI1Gt1BD8ZIvXZZwutdrXSCTvUSGz_k6HDG6ur2d6POcBq3PaGgGkqSQXzCkOIkf7catW-aNou4AzaZqGyR71KSMN4YF7vO5V2YludQq1ItuS5yiVhw8x4-VYkOQBgmQjjqmQw6OmIM1W2cMWEu3ysLZOiE98NjjikRTPD1vnxjneMyOWzdDEjweK71vzyXS6zNkfGLg127bXfDHwpYay_IYxGsTb2QyFBWihDpwncWgBwnXlzgI0kt6jjfKzSOUsPGHYf7xq6_KPSdItUhmkcK4Au2-7XG0kSBWMzX-uAM4Edmz35wiU5iX68JMRsp74CwR8VzRmLJCUWJPD2pSvIOXRcRChTan3NTmh_O2QRTngbuS_P2eX2NeXKUNkWCfXUcIC7LvfIXC9AqH2Dzjlk5NmO0q1EQ-UQ7FPHhzYy1n3VlXxZzq6Y5Q54MWDNVb67DZG4wzRpvr2I27b55Bdt0CRB5ebTGrNrhppjG9F7F3rr26-fszTEuJ36Vy3CfVss1v7MVP5uz9vaGC_CuYchKNu6L504uNKZbl8SFCWreM0HXktE8kHIP9dQUuNmLUPmgM2NAn9i4h5dsJ2ZeJP6EVZ3OKosA0BrddQnhhHqlwlIrGRVwR6ut7n7ByiZ7h96M4BtPAzeSxIW0EUM3FxEFz45Kk6BC8sd6RbeQSPgqBrG1jWEa4honcGDHVp39kA7yfHctsBlq8M4WlMOmtSUld-qD8sazgUggFtC1Xp3SE-Sf6CWOL7dS2bl_uQgVtyzEJBDzmokCO491UFYuNb_IGMwfBiKVdKi06dw_uc3Ot2hB2pX3eV8N52ZiB7Q4Lkyr9Wu8e3aqfUUv1CNtkv--I2wGFkaTWZHL7zQmVFfZXFqFJgJxovYfnEJaPQ1HFX1kIBltgDDrxvKSgZ2WmW6ymKyOfkx-69-2MkcK8eJAqPkY1mC8wYV_MpU2EKobEluFitokaEDdNYZGjurIsgSyLvdTQLxKGxZUWFtjzOdncBL3B_F70LGexAJ88AdqaybxaWyisJVs2lSZwKNZf6IrFcsGpHG0QkU1hhKcgWtUwEYv3u9jMjFuPP90bY3pgEI-zb4OWPfNC4B5LxheYLchS17eaRIQpKqeGtGqjAtTyCWcnVWW1EJkawHPmU7Bf4ooapAHozAXju4PGrzSM0qSX8YCbAISJJ4gQPIUKd7QE5OPty_-x0OLTzVFB5uX79GSUkpF-GTrDsQCwNWViGIpxWN0HRLLHCrLlwPio2NpzTXVw32jw5PoLvAwjGL4TAOhcIp2KwhTM7rlDHRgXkYZjjf3eW1jIn274g')

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
DROPBOX_TOKEN = os.getenv('DROPBOX_TOKEN', 'sl.u.AGN4ro-oeoh-ApfGemZPY2n7Qas9Ad9RVScYSf1K50auXY-wW2Bg1YnNgCX8y-fU_rSQwcqbgNapPdSTDLpJ2MfUzjIOntUT7jggFYUvnyjbEwnkebyY6-7PqySnJ172QWXy-fqs7LI1Gt1BD8ZIvXZZwutdrXSCTvUSGz_k6HDG6ur2d6POcBq3PaGgGkqSQXzCkOIkf7catW-aNou4AzaZqGyR71KSMN4YF7vO5V2YludQq1ItuS5yiVhw8x4-VYkOQBgmQjjqmQw6OmIM1W2cMWEu3ysLZOiE98NjjikRTPD1vnxjneMyOWzdDEjweK71vzyXS6zNkfGLg127bXfDHwpYay_IYxGsTb2QyFBWihDpwncWgBwnXlzgI0kt6jjfKzSOUsPGHYf7xq6_KPSdItUhmkcK4Au2-7XG0kSBWMzX-uAM4Edmz35wiU5iX68JMRsp74CwR8VzRmLJCUWJPD2pSvIOXRcRChTan3NTmh_O2QRTngbuS_P2eX2NeXKUNkWCfXUcIC7LvfIXC9AqH2Dzjlk5NmO0q1EQ-UQ7FPHhzYy1n3VlXxZzq6Y5Q54MWDNVb67DZG4wzRpvr2I27b55Bdt0CRB5ebTGrNrhppjG9F7F3rr26-fszTEuJ36Vy3CfVss1v7MVP5uz9vaGC_CuYchKNu6L504uNKZbl8SFCWreM0HXktE8kHIP9dQUuNmLUPmgM2NAn9i4h5dsJ2ZeJP6EVZ3OKosA0BrddQnhhHqlwlIrGRVwR6ut7n7ByiZ7h96M4BtPAzeSxIW0EUM3FxEFz45Kk6BC8sd6RbeQSPgqBrG1jWEa4honcGDHVp39kA7yfHctsBlq8M4WlMOmtSUld-qD8sazgUggFtC1Xp3SE-Sf6CWOL7dS2bl_uQgVtyzEJBDzmokCO491UFYuNb_IGMwfBiKVdKi06dw_uc3Ot2hB2pX3eV8N52ZiB7Q4Lkyr9Wu8e3aqfUUv1CNtkv--I2wGFkaTWZHL7zQmVFfZXFqFJgJxovYfnEJaPQ1HFX1kIBltgDDrxvKSgZ2WmW6ymKyOfkx-69-2MkcK8eJAqPkY1mC8wYV_MpU2EKobEluFitokaEDdNYZGjurIsgSyLvdTQLxKGxZUWFtjzOdncBL3B_F70LGexAJ88AdqaybxaWyisJVs2lSZwKNZf6IrFcsGpHG0QkU1hhKcgWtUwEYv3u9jMjFuPP90bY3pgEI-zb4OWPfNC4B5LxheYLchS17eaRIQpKqeGtGqjAtTyCWcnVWW1EJkawHPmU7Bf4ooapAHozAXju4PGrzSM0qSX8YCbAISJJ4gQPIUKd7QE5OPty_-x0OLTzVFB5uX79GSUkpF-GTrDsQCwNWViGIpxWN0HRLLHCrLlwPio2NpzTXVw32jw5PoLvAwjGL4TAOhcIp2KwhTM7rlDHRgXkYZjjf3eW1jIn274g')

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
