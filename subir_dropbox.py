<<<<<<< HEAD
import dropbox
import os

# Token de acceso de Dropbox (se recomienda usar variable de entorno en producción)
DROPBOX_TOKEN = os.getenv('DROPBOX_TOKEN', 'sl.u.AGSOtnQIzozwViOn1hDfAWmJw7yN2sQKJ1bqOu3ZXhogy5vO0pwoOZeoNhxTKSSSliTjc6WAmlSUqX87p1qxcviPOC3VdWO59jqhsies2W1rV7miv6uixgvKAWlUxMoLgguamuek-8PTD03SDGvMZADvSD02zK3b-obwLsOtF6l36jsDv7_ANraVXv8M6DrK3rVBR1rxiuUMpb72aX9kwr9Z0M4gGEiDYAitIX0PMQqbn4QJZd_kj-UJtsPy_pCWj-Y3w9c9bolJLvVQbXrAIFSGrnLR-rFoW7D-gDDl6Ea7hUbnNj5Rdh43GOaw9oi-qxIyyfcp0KnzMerX2KPX7tyVf9HUfEE85jK_FWIIxoy_aJ_osErYMcV1zpDzRjZ0jqceXt9L2z6ljYlgrhpDLYdtIxE2QufBIg9Jvh-Rjb9tfPg-_gqHHI-t1Uv3O6erYdDhn-HsSF4xlC7-8B9mHXZR6NhK8gbSKr2NiS2MJyKdPSTIhJKD6VSnbn-uwYjhqdA0F_msVbS0ry_wZy03mvryOD9Lsuad5ikWOtfCmAVIkALmEgLI1gXRbOfbmJ4AUkUCkBMvovsV2iU-1xi4uM_igxsr_dg1O8G8q___M-vu6tQcqmgQPYSnqGFJwx-eI4QPaAOcsYIQ_Jhe0tcVeTzYcwwqn3xGHwCeRMoRCIyaVfFTQ4S0iXoDbxotvbU3kkF2BlzC6hgxw20RAQgzlg_DRvkmcNmm9U_8p8lwpnmBQ_W636oIH_bSoffgchcj5-rNCCKZ0qwgxnr_C-iL6He4GHOKvFQwOHnA3EGgMAVDqUD93DLMiESaYIyJm_HQLFa5lgntvwc25E2KLbg93BaqDtgnKZJYIiqUVEMvMnjTc4CxkNXz31V4WP8SFScpdcJxdEgCPkS5vCUT_imAcBkBiCxbBHU6GOJl5OK1MlluVXaYjtiT5gDKJwaAGok9gPn1QhFM_-p39clAYbjyroLPRr4Zs9uPHTzhzKehhRnBez0jHPkwXqC1-e8zSGr5HVFhDt5YFlvBU0r32vvHCKM8iqQI6M5AtpOpI7hmnb1KLt42doWpZGcTNnV5HPNCrdymb6Bc-bDq4hX2U1i71nSa7xKiXNAGa6zR-K38_pt8vljEfbC4PrpwyG6Jpg1ELXknmUI__9iuLfLhD8pE-NgD8_3yPbBkxDpnd-tIGovDcQ65lGgFuoT6VEgWWT11Yt3wSGlnkpCYWMZfI4JEGIRzjqFTWi08teRjus6Uzk2pSBaAR-7p7fbtW7TUxHkYJS8RlB7YyRInpe8e05MhUIX72B-RePleQjdeUHv0ZMGrvcyPkkl5cks76DIli4ggR9sY397IIW3SdKsCyPalru7X7wGfGxKJKjIfBgWVsCts6o3-Nsr8UtjnP4ly_OmYthDmrJVKYt-TOfwN3Q7JYsUmwY88Omqyx8ByZZWsxErJkw')

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
DROPBOX_TOKEN = os.getenv('DROPBOX_TOKEN', 'sl.u.AGSOtnQIzozwViOn1hDfAWmJw7yN2sQKJ1bqOu3ZXhogy5vO0pwoOZeoNhxTKSSSliTjc6WAmlSUqX87p1qxcviPOC3VdWO59jqhsies2W1rV7miv6uixgvKAWlUxMoLgguamuek-8PTD03SDGvMZADvSD02zK3b-obwLsOtF6l36jsDv7_ANraVXv8M6DrK3rVBR1rxiuUMpb72aX9kwr9Z0M4gGEiDYAitIX0PMQqbn4QJZd_kj-UJtsPy_pCWj-Y3w9c9bolJLvVQbXrAIFSGrnLR-rFoW7D-gDDl6Ea7hUbnNj5Rdh43GOaw9oi-qxIyyfcp0KnzMerX2KPX7tyVf9HUfEE85jK_FWIIxoy_aJ_osErYMcV1zpDzRjZ0jqceXt9L2z6ljYlgrhpDLYdtIxE2QufBIg9Jvh-Rjb9tfPg-_gqHHI-t1Uv3O6erYdDhn-HsSF4xlC7-8B9mHXZR6NhK8gbSKr2NiS2MJyKdPSTIhJKD6VSnbn-uwYjhqdA0F_msVbS0ry_wZy03mvryOD9Lsuad5ikWOtfCmAVIkALmEgLI1gXRbOfbmJ4AUkUCkBMvovsV2iU-1xi4uM_igxsr_dg1O8G8q___M-vu6tQcqmgQPYSnqGFJwx-eI4QPaAOcsYIQ_Jhe0tcVeTzYcwwqn3xGHwCeRMoRCIyaVfFTQ4S0iXoDbxotvbU3kkF2BlzC6hgxw20RAQgzlg_DRvkmcNmm9U_8p8lwpnmBQ_W636oIH_bSoffgchcj5-rNCCKZ0qwgxnr_C-iL6He4GHOKvFQwOHnA3EGgMAVDqUD93DLMiESaYIyJm_HQLFa5lgntvwc25E2KLbg93BaqDtgnKZJYIiqUVEMvMnjTc4CxkNXz31V4WP8SFScpdcJxdEgCPkS5vCUT_imAcBkBiCxbBHU6GOJl5OK1MlluVXaYjtiT5gDKJwaAGok9gPn1QhFM_-p39clAYbjyroLPRr4Zs9uPHTzhzKehhRnBez0jHPkwXqC1-e8zSGr5HVFhDt5YFlvBU0r32vvHCKM8iqQI6M5AtpOpI7hmnb1KLt42doWpZGcTNnV5HPNCrdymb6Bc-bDq4hX2U1i71nSa7xKiXNAGa6zR-K38_pt8vljEfbC4PrpwyG6Jpg1ELXknmUI__9iuLfLhD8pE-NgD8_3yPbBkxDpnd-tIGovDcQ65lGgFuoT6VEgWWT11Yt3wSGlnkpCYWMZfI4JEGIRzjqFTWi08teRjus6Uzk2pSBaAR-7p7fbtW7TUxHkYJS8RlB7YyRInpe8e05MhUIX72B-RePleQjdeUHv0ZMGrvcyPkkl5cks76DIli4ggR9sY397IIW3SdKsCyPalru7X7wGfGxKJKjIfBgWVsCts6o3-Nsr8UtjnP4ly_OmYthDmrJVKYt-TOfwN3Q7JYsUmwY88Omqyx8ByZZWsxErJkw')

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
