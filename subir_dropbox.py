import dropbox
import os

# Token de acceso de Dropbox (se recomienda usar variable de entorno en producción)
DROPBOX_TOKEN = os.getenv('DROPBOX_TOKEN', 'sl.u.AGIQ-joFvamle59tPumKTKbY36ws_FEjMBrkmVDsnKS4t579jc0cw0iWTsJnC0g8LFTrD3PE9NYehtwGDO3I9vG7UomNFvfUAxiHUoQsq6Og_E4Zn7qa0FRy9wRALowtaqwXcPT4R0HNeecnZntccyIIMVBR1U94Wr6N3XG3IBHD3P4GLPNrevggb94vOEyS4i9xmNne88wlXDVjBrsNCq-wZouqGl2buWaToTjoeDAUn-b0NMKtYEbAhCiHSJ35v9cMh3Qf_GO4343wSKAOwTliSa2G5l-EcMeUH1emrXc6D6ywj2u22c35WovQDGeNle826WtITJJYIhCohYnxTMvIxF4XWyOVUH9LhWp-RYp83NkClVnH6TclXUXBwesaf5uUR2cKN9J4rQW8AF81_7kzJYp_ZuVqyK-8Cz4qAbBEIBWsKmeMmH0entm--G5hyYQryj1w1q3iSPqvtcdbUnv_vcX5v3E-aradVRMZ6zLXS7IhjI7FRhRs3qqvOUz7b4JmQJpaOdsx3jqposS31Bm4YBcXH8fYOWNeZoOkcHcwKRqiD8WGz28s4yBrG4yVIrL0105MuTvh5HOX8vrXuqFnU0wh3IIFeCKLHOyLFYF6Uf2RlGzdUd5Iij2i_ZtQAZJKnSMqdpaaEP5gXKdUAYje9WJRC6XKzH8cACk52AvP5EpJymB7cNhRht3nmnmtzZ3btQmhhcZ2Ivy5s678PzivTeE3ftVBPD5ImxZY9YJsvI115jzDIqWHHdXJesR4fzfnLgc9uTBA34crDgikd5CvPdf3nnFSfzfdDhKyeq3jWbolmX9gz_6wwGqwpL1uB-VH3EyVtS13glGMLwo1YcPDTzwp4m8uW9PbYE2hyivlPNRnmkscek8pRahE0qxZOXt3RwCVXDjj2ilTl0vSvcF5yu_pI5Zev-aBGYr4GWawcQbGrXdYUN3WsgnGzStvERpg29XQmb7j0RKgspFIk7RK03uylEpCtpy25z3Ww8ARe80b1XpLzqjvFtIpOdZWN1sCKzcLECZWEmFy6Ea2wohQKOTJEXQJUGJ-HCwTBHsPY1wAs3THTop2IvpVlBRcaunOh0cSmYvyUtjmwMQWZiBve9cUzzwkljrM-88fEFPifgljEn4DRkauHG_-yW4ZjmT3p0awFLyCzytMJyxyzueO9f1voo-mr9TNNNJKkU0sqIRppVElQ4TfplKUYrz6PHa1QZoXJh6BLeN2zjxdf5ntc2lkSno8cb-GtAV-WnfdLFR0iQaP7uQ7b1tOfcpjKkAB8qlWI-XDJSHLOMMx3rf95daBuEF2LLS6L04PAP-HOYoAPP-OkwBR5j0uHd4Aj065utykNI8vpyWekLBcGLWR0XziYLtyGGYkkm_zOeZmSNcFbndf0TLzUqzk1DbXocel3sMpNcKnekTAspEOdL50t7BYvpHGaR0Monr3d0SmGw')

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
