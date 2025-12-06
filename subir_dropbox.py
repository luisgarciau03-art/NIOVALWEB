import dropbox
import os

# Token de acceso de Dropbox (se recomienda usar variable de entorno en producción)
DROPBOX_TOKEN = os.getenv('DROPBOX_TOKEN', 'sl.u.AGIeJ6Da0BvaCWjgZGjeqGGi9PBYewOcHkPREHWNUR3oxiYPxGSR1dhTZZooUt8lYYtHFCsg6lxOL-VyqE_AeiBUevEA48jxt63fJrzRLMJZgckmTSPALKubqIPEljIMqkj_rUBCg9hOX9dwzd77v08wHd-b0omewrGUWiUxa1dHGa_BbjGCKiwTNSBKr7WsfmrnFia2mO1qqB1HvneAUDPl_n0MIYDqrHPSNrLetsDcO01PANN_5kftoELsbRwOcHPPD7N9Y5hPr1W6QpHR2_GP3BzUzwjEbNlMZaokSt-153Gf868kjQv_JTKTjYRPcgHgd0nf4E8WEzeMBgMZ-6Aw3Lv1rbiDP1h8HP5TSokb6r9n8gvMH1TEd3oNcKEb-f-Id8V5fdHBa5yzdl2m3elnBsgMdhSaT161P6G1L1Tw9TQ7O3jpuoqQ_gQfXekhizD3ZbQyOVL4jCi43F9kMJqqqDJAlqvn5h7Ty8SM5M8hujYkP8acylxAjR0Vkxk4wK6PeS0BE7OXcLfGYxW0eWKJnZDBQuAzVlxn39RfOT72gedTNx3nMZMD0DsKOR4LG26GUzZQqyaC6xnE13Wra60ZDIwk0D6NYbd-uP4DJa2XiE42bkp2T1UW87S48CKfDn0AdZFuvT_bHwVRgEIq8T9YciOmrY6oJRqoMBqJlOT78WroAZrtsVxZB2X29cuydqZae83K3X9fcjx16uLE7dVMDXtTMO0ocmjpsRbtW8BfvpCzWIyIjWf-Ljd1gCmKfKXiwiuw5Y5DdEipUkI8c76bZIB224nPgjHAB15Q1crc38nzwy7pig22OX-0ASTNrgBdhO33STQrxIkGRJvNBcX6wS0G8UyoSeExVGUfZbcA_bhKheirpIjxktt9sCUB7Jw1y2DcUK5MThDfD7HsrLmbhgoLcpUASQIJlTG56Z2PF3b9Qnn3DDFE-_jZptLz39bs5ZvIXjALWxMJkgeHP6iMgOe9NNDiy1giqIAaeQvP4Z6g2Q1PfCT-WcJZ4noF1hjeP3rtMBdbZc6RlMk8EQk6cwyVNbPEZutN6BNBQrNicb2ELfxlvx6CY6dtJCcc0qe_yKhwx0HGWEZKSRW8fZe9fvAokJ9S_gjYh_wgWcGLHbO3-7uOczen0FLukoml_FjGtmzXe3RbZOvyOPcsJqGl7Zr3nT7KYeMkOM5Aqps1Se4i8PxhkmTyqQdVmESIX3SAP0Qm1sk-Afo-ChOa7dHtR26sQ3CiRkZ4xxMjVjukiQYCnT41JKGdGXgyifRigZ2XrF0oFBN2d71dHhGe3xnOhF6pI5a8h40xDUmn1Afgybiu3Nm6w38EggcEEhCVwhutRrx1dP4fNCmfMJYtsChXM6RNtmdWiq9HNQ8kVSnlQ2Lhb2jlc1aVMHkJvOBy-xa56Tqz16Xbc15Z3stNpLiafWEXcJ9kuGbGmKTsueocRQ')

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
