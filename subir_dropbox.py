<<<<<<< HEAD
import dropbox
import os

# Token de acceso de Dropbox (se recomienda usar variable de entorno en producción)
DROPBOX_TOKEN = os.getenv('DROPBOX_TOKEN', 'sl.u.AGODHgYh0wkani-0rtnJ0BAHLze3rMCU5LXP7tqg-eeGDoTwA0tob_mQuUArO-BlDzbMkjTfP2Z_Nv02hk4qF4CyCCcuvvnknpbjKRj7GuSvHqozm44eOlUxEdKDW6lwTu_-URQ2gQnmMwyOmTbIIh2S4uura4h7G_NNIrvu54ZD9pPU5CPHmVPaGgUAmsmA9CcAMZsrV-2nMS4am52ayVpA2gAlqD2FzCZRmApafeIrUH6BgF31mmC2GoY9Ml0Hxs_g0VOTpd-DabO5EbGuTkv_stwAQhnD77HULyveFr9EsIaF0gxRPtBd3lmZNNmX-5tk-lFrlynik9qZbDRrIEp3Kcb93t3fayriutwcIgvoKYvM9WbwTJKEeTZF2j2LRk_V1K7UjNGf8E1oVsFyhh-e2r2nmAnBSFRYJWvpUaIHTrZco-LZFbG-EN5uxhSou38de7DEHcnO4Ttbxwyj5ZO7LlUbswogGx0P29azASzOQwtJu-sPG-BoCCqwHIccPmBCTD8zjup3mJCqLItY09s9ZXVXQfMUyHatlQPg7Wx2bPsuocMd4a9SbQUbw2FJDaCb5a-94HL9H0UaycdXCPj6aK8TPqbEI7ZCdC1QIm8aIqgjqCXXN0eSvAQaV5SZHA-BJeQy4ZbX6BKk1qfUctlgZ3-dH4UHBCtdze_bUbi0S48HW6WhZnqnc0Jg12_aKTGpzpvO7y9g2lcKifO_UQzocDKSaQ9txy5NTNFMt3QN7_vefHFrmt1lJuE9XC764SdMIPWnE70LpFblxPevUK7vCQOzRJQxPU2S6zpwB6eElVQsYZHfpJ57xH8BOFgn3Z6vB0Vq7bBiEwoivrDmbqWpeP2nrPRkAgEH8-IVbXr5KlsBUwzF9xeVi5MfBF1SAxrMJasXqm1_3I0t7AGpIx-ITpwaweVmHNopKYkOIlPG-oPNLkENiDfl_ve_CDQxZ4UBTY48VRmaezibjwIAQEXBa9bDQqzd7v2uw7bdXzGZB2Dpfx_q9bBhV6xR-3h4ZVclRT_OhndJALSpQAAob-qNT-Fsy_BxXbNqQ3axSakxB9cq9GKgfoF-qPAcGS6wKru8wS-iDKSyJGDP1XCSpqwatR68uolXh5m7-beULPhqX7xQ2a7VB_i8TpSSenkAFr5A50fVb2cw7tZtWo2eexLftHFLTSz1I62vYB-zATXrFtv4SS8s_Ixpb3cZAFjTAE8M3unF7D1JjRGB7z-OH1Q66pWYF05U_0R8PNspjkmsoHH-TgdJ_dIHbYmYJHXsiIv35sA2bF3pBmrzA2s0YqceCep1c1kOzsR5blAtM6AFBFJldVbY8JS_Pm2Pxmbx7FN4I8TArhFiQCRMJthtQLlEU-l1Z3SzvLxvG8q6Uj0SuOslG8IF5P2XV4B5zxUKb3t0YdUrgzTIW0DbJ6tS_-rKJD8oBBrBf1fZQkYjk76BXQ')

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
DROPBOX_TOKEN = os.getenv('DROPBOX_TOKEN', 'sl.u.AGODHgYh0wkani-0rtnJ0BAHLze3rMCU5LXP7tqg-eeGDoTwA0tob_mQuUArO-BlDzbMkjTfP2Z_Nv02hk4qF4CyCCcuvvnknpbjKRj7GuSvHqozm44eOlUxEdKDW6lwTu_-URQ2gQnmMwyOmTbIIh2S4uura4h7G_NNIrvu54ZD9pPU5CPHmVPaGgUAmsmA9CcAMZsrV-2nMS4am52ayVpA2gAlqD2FzCZRmApafeIrUH6BgF31mmC2GoY9Ml0Hxs_g0VOTpd-DabO5EbGuTkv_stwAQhnD77HULyveFr9EsIaF0gxRPtBd3lmZNNmX-5tk-lFrlynik9qZbDRrIEp3Kcb93t3fayriutwcIgvoKYvM9WbwTJKEeTZF2j2LRk_V1K7UjNGf8E1oVsFyhh-e2r2nmAnBSFRYJWvpUaIHTrZco-LZFbG-EN5uxhSou38de7DEHcnO4Ttbxwyj5ZO7LlUbswogGx0P29azASzOQwtJu-sPG-BoCCqwHIccPmBCTD8zjup3mJCqLItY09s9ZXVXQfMUyHatlQPg7Wx2bPsuocMd4a9SbQUbw2FJDaCb5a-94HL9H0UaycdXCPj6aK8TPqbEI7ZCdC1QIm8aIqgjqCXXN0eSvAQaV5SZHA-BJeQy4ZbX6BKk1qfUctlgZ3-dH4UHBCtdze_bUbi0S48HW6WhZnqnc0Jg12_aKTGpzpvO7y9g2lcKifO_UQzocDKSaQ9txy5NTNFMt3QN7_vefHFrmt1lJuE9XC764SdMIPWnE70LpFblxPevUK7vCQOzRJQxPU2S6zpwB6eElVQsYZHfpJ57xH8BOFgn3Z6vB0Vq7bBiEwoivrDmbqWpeP2nrPRkAgEH8-IVbXr5KlsBUwzF9xeVi5MfBF1SAxrMJasXqm1_3I0t7AGpIx-ITpwaweVmHNopKYkOIlPG-oPNLkENiDfl_ve_CDQxZ4UBTY48VRmaezibjwIAQEXBa9bDQqzd7v2uw7bdXzGZB2Dpfx_q9bBhV6xR-3h4ZVclRT_OhndJALSpQAAob-qNT-Fsy_BxXbNqQ3axSakxB9cq9GKgfoF-qPAcGS6wKru8wS-iDKSyJGDP1XCSpqwatR68uolXh5m7-beULPhqX7xQ2a7VB_i8TpSSenkAFr5A50fVb2cw7tZtWo2eexLftHFLTSz1I62vYB-zATXrFtv4SS8s_Ixpb3cZAFjTAE8M3unF7D1JjRGB7z-OH1Q66pWYF05U_0R8PNspjkmsoHH-TgdJ_dIHbYmYJHXsiIv35sA2bF3pBmrzA2s0YqceCep1c1kOzsR5blAtM6AFBFJldVbY8JS_Pm2Pxmbx7FN4I8TArhFiQCRMJthtQLlEU-l1Z3SzvLxvG8q6Uj0SuOslG8IF5P2XV4B5zxUKb3t0YdUrgzTIW0DbJ6tS_-rKJD8oBBrBf1fZQkYjk76BXQ')

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
