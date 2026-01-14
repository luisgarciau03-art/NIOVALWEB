<<<<<<< HEAD
import dropbox
import os

# Token de acceso de Dropbox (se recomienda usar variable de entorno en producción)
DROPBOX_TOKEN = os.getenv('DROPBOX_TOKEN', 'sl.u.AGNUKMLMg15h9321mPAMMX1EO0c8ih7Nr1i2_0bI5h47lvkVBGvaD4qUBDZRmDQschpLzC_HKduJJa7QdlshkYx9SwbBXP69FrR3VcTxmi0YljWxyJwCjO9j_LXJFM5RGe-L0lN8B4Wc7XUOzpHT7GtJ8QA-R6nWfvbOOi76TcUmztLrcjjbtKx8GIYf6KTvERTD_cUTroapjTmBt5lbs8oPtSZh9rzAHDVHy5LNOatwAvU8DXMJsGknqP2dUkDf1DF9J4GsZ1Z_CLXBnHvOMMfUVT38zX-5_ZKMCkH6HB3f6pLF4UFsBT_AYcd-66xERLpx8JwmA9vDYyIwk-Rpr5l79rvZL1C83R3NBaYMSJvuIkYQwI6M4VQN1BGpECkemt6xbzL8gppsNRrSt8nmJJXD-a8kseU8ippq7RsebMIbAwfmqDc4a2pqera2qjY2XxHuVCbFFsEhrztgwx1PuRP65HKS0DR8P4P0lMP-3dnWoqJOVLnHKumf7quixx5T3zkrJc8pV-jVmmB21XaQwho8QbUoI1iyW_TH8ryQyuJNaW2g5KXUxwMd1WY7KAwbbU5521PTAN7UmcRh6wHjOI_uO0CdJi1_dIW9_i_D3PwTKG60HJd29FnDYU2NQNOg4nvaA1bJVGJiOLNcBLtWVIl_tMfsLxUsjAzPjmjhrY9kwmmppt5j5Vbdb_D_sh_77oIpXPLaJDSHU8Cn5T0Lv48H4qukGMBPJLDmWQaz4eOtKm1pGfXZApqMGgZaIiIOuylmDZNxlRfvt-Fun4t6W7ycaAwemYR8Z5qXOqZd3N9HbwY-vGknO2gOXtE98BoGw4wdk7PlELew7EtWbk8n0w1hugkh2UXLNpJJ_mMIMH4rZpDs2qisXnui6Hum6y3PKj7flcoD9NWKV5dquPBNpzPvkGQAwZ8v0vlerQ1ny0uDSp2FoZlj0uWvAtNjyQhFx8CKnGLMRg4woRU5ndYD-rmAouPyzprFQf6yQ_Q73eI2kyHEnIbT2QpdHVbBPjWBuTj-mU_t8AofJ7M6sCNiCq1nSUV4rp9Eam_lZyMwHnT5De7OClPq4OP6TWcqnDbGqF83buHy-NyUPhMwrgo4EahXQlSBdsjUHbX69wDiwug-GUvfXTE3bUDpPKFgJnPC7XHfIrVYL7dyvcEfSKDoK50RP0iaUW1M9Cd-e1W6yJxNppr_qYGh17_hh81tH4JrDqOee5_fnaPe2jvt4Dsz3zGrwt9puyN-HiXsEdb3Fx5aadttH3UEN1sclo_qgoiZJwg18WUMKAshiN0uqH780YrUA37s4byvbSgHf3LPu7bjvdx88G9mZN0cZNPic41Gjdrb-M6maVlaoKRk21FHwIZChCWB9-TjShzRFcOSCQUOGd8RlfHQX822WvDZUgHHB3T3jQs45D4NOwetHBynWu1A9kvgtory2eNalpMItYz_Mg')

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
DROPBOX_TOKEN = os.getenv('DROPBOX_TOKEN', 'sl.u.AGNUKMLMg15h9321mPAMMX1EO0c8ih7Nr1i2_0bI5h47lvkVBGvaD4qUBDZRmDQschpLzC_HKduJJa7QdlshkYx9SwbBXP69FrR3VcTxmi0YljWxyJwCjO9j_LXJFM5RGe-L0lN8B4Wc7XUOzpHT7GtJ8QA-R6nWfvbOOi76TcUmztLrcjjbtKx8GIYf6KTvERTD_cUTroapjTmBt5lbs8oPtSZh9rzAHDVHy5LNOatwAvU8DXMJsGknqP2dUkDf1DF9J4GsZ1Z_CLXBnHvOMMfUVT38zX-5_ZKMCkH6HB3f6pLF4UFsBT_AYcd-66xERLpx8JwmA9vDYyIwk-Rpr5l79rvZL1C83R3NBaYMSJvuIkYQwI6M4VQN1BGpECkemt6xbzL8gppsNRrSt8nmJJXD-a8kseU8ippq7RsebMIbAwfmqDc4a2pqera2qjY2XxHuVCbFFsEhrztgwx1PuRP65HKS0DR8P4P0lMP-3dnWoqJOVLnHKumf7quixx5T3zkrJc8pV-jVmmB21XaQwho8QbUoI1iyW_TH8ryQyuJNaW2g5KXUxwMd1WY7KAwbbU5521PTAN7UmcRh6wHjOI_uO0CdJi1_dIW9_i_D3PwTKG60HJd29FnDYU2NQNOg4nvaA1bJVGJiOLNcBLtWVIl_tMfsLxUsjAzPjmjhrY9kwmmppt5j5Vbdb_D_sh_77oIpXPLaJDSHU8Cn5T0Lv48H4qukGMBPJLDmWQaz4eOtKm1pGfXZApqMGgZaIiIOuylmDZNxlRfvt-Fun4t6W7ycaAwemYR8Z5qXOqZd3N9HbwY-vGknO2gOXtE98BoGw4wdk7PlELew7EtWbk8n0w1hugkh2UXLNpJJ_mMIMH4rZpDs2qisXnui6Hum6y3PKj7flcoD9NWKV5dquPBNpzPvkGQAwZ8v0vlerQ1ny0uDSp2FoZlj0uWvAtNjyQhFx8CKnGLMRg4woRU5ndYD-rmAouPyzprFQf6yQ_Q73eI2kyHEnIbT2QpdHVbBPjWBuTj-mU_t8AofJ7M6sCNiCq1nSUV4rp9Eam_lZyMwHnT5De7OClPq4OP6TWcqnDbGqF83buHy-NyUPhMwrgo4EahXQlSBdsjUHbX69wDiwug-GUvfXTE3bUDpPKFgJnPC7XHfIrVYL7dyvcEfSKDoK50RP0iaUW1M9Cd-e1W6yJxNppr_qYGh17_hh81tH4JrDqOee5_fnaPe2jvt4Dsz3zGrwt9puyN-HiXsEdb3Fx5aadttH3UEN1sclo_qgoiZJwg18WUMKAshiN0uqH780YrUA37s4byvbSgHf3LPu7bjvdx88G9mZN0cZNPic41Gjdrb-M6maVlaoKRk21FHwIZChCWB9-TjShzRFcOSCQUOGd8RlfHQX822WvDZUgHHB3T3jQs45D4NOwetHBynWu1A9kvgtory2eNalpMItYz_Mg')

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
