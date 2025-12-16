<<<<<<< HEAD
import dropbox
import os

# Token de acceso de Dropbox (se recomienda usar variable de entorno en producción)
DROPBOX_TOKEN = os.getenv('DROPBOX_TOKEN', 'sl.u.AGL68kXyz_KvIZE9nQRMlQ9sJ8ebCrBzPxBeqfxErc1hoNiFBPtptZpfjhWATykqRR_VUK5mHQv71XNHczYizFZTHSRgUwxSSYO2Gv0dhuckP4SonKDMxMA4_3XMZA_pLotXb3LX9-608PjYrOaA_WgvteUpgT1SXGzpnsRkr7qx0O_7Wz2ItmgN3ONTIY14TtcQRHecGOdJgRZlmS3o6pdGGwPi3apfJ4mFRroE7iwRwVUXaNZ8Ftr3VjQQoieuiQzhEoQyQeYJdE8UbT3uqhJrBu6pYaoQCoFwsRYEpZMRU2gfuDmU6ZhDDlLFW383XnESeClNhNg_vhdC3ydcH4Gz3ejRlwBg2dzLMcNEJD_raWbGFk1gLKklDY0ywIZ2Ka7FyKyQZtXUJ4APxXiHt1Lwk6q92LlEa7nI7XmauGV9wJp2g2attBpkK5axB82PFjvR4ohr4d3CrJw25urKHjLIQ_xRmdY5SKlqIkIgrbce9rjBv_ts6TAMegS_5aUAZqPQCBQbQIIRiFcfceKgTL2SDusyZ1QxwnDD5cINI0p7P5hFWLfk-8stvDuwQEKXbQDkOdOtKUbK1wo1vqZt1vMhTCvRluxx_is4cSNVL3euCTtKrF5YiZpraNZBpaJwjcl-0-7DCskc2xbx4Dq4onrAYjoGDlkiDw7SZGKwRUqSLu1hfThwIs4oBxyYe4Gr7CvReB3XDZMkKZOh0RZKRmBuxx-Zly6hkOmnP4PNHDHS5O6Y3EWyIDoHuL0V7OzLs3hby_09XUvf7iD8NyZw8zqr7NLHB34zHf4DLv329NwSe7Ogndh3k_-b1_YlbarPhNrsAXCXVoXNE6iQBX3sRBtVAZAHJMr_ZT43kyu7UhZZY-KaZh0SyGeYf2HwCxEchZHnAMmXR3FeJRWqAfJvTgPIiQAjoPC-jcap3tX9EVwuYE9SGu0OQTHhWdzj2uJfzXp6MuQ9xP-vT9DOlsMSIyAMPyN01GReGB3W0YzqPmBqs0_XoUEw6ehnCVENaBcaxQAlwAtIgI6UbDMuJSEjzGsQMmj6VMh6Rk-VjGSP3dQlHLVD-owEmknSTEY_v33ivgv1RDjfA9CtRk-wqxorQzt55f3ZbRMaTqjN8SsblYOrMgV5okeS8riiP0fMkIc9q59Gl1MbLvNP7qj-m60VsvXfrQ7CaSssiQ4w0ysBt1rYxGIQOdJTqR083IdSD61xgexPHibsYUDZukUSeqs2UcJ_SjBEiHXI9Cc6EJHQIFTr0hWyCFlsg4FT5LS5Dy8svF3yco6_1zYFh732VuPDMEsjn4qjWW__hKpi5akeXki6gMQ4vaWeMv94NXXHX7feCrNY0U9YwAY15HNcjE9DDS92lD9_7N5X0fHgjqaQZ3TP5bY8pMrvl5U9eW_MdyZx8rDKYMU_pGGxEAIVHKaYa2W61lc0AMUITGTZ4KTOsdGUjw')

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
DROPBOX_TOKEN = os.getenv('DROPBOX_TOKEN', 'sl.u.AGL68kXyz_KvIZE9nQRMlQ9sJ8ebCrBzPxBeqfxErc1hoNiFBPtptZpfjhWATykqRR_VUK5mHQv71XNHczYizFZTHSRgUwxSSYO2Gv0dhuckP4SonKDMxMA4_3XMZA_pLotXb3LX9-608PjYrOaA_WgvteUpgT1SXGzpnsRkr7qx0O_7Wz2ItmgN3ONTIY14TtcQRHecGOdJgRZlmS3o6pdGGwPi3apfJ4mFRroE7iwRwVUXaNZ8Ftr3VjQQoieuiQzhEoQyQeYJdE8UbT3uqhJrBu6pYaoQCoFwsRYEpZMRU2gfuDmU6ZhDDlLFW383XnESeClNhNg_vhdC3ydcH4Gz3ejRlwBg2dzLMcNEJD_raWbGFk1gLKklDY0ywIZ2Ka7FyKyQZtXUJ4APxXiHt1Lwk6q92LlEa7nI7XmauGV9wJp2g2attBpkK5axB82PFjvR4ohr4d3CrJw25urKHjLIQ_xRmdY5SKlqIkIgrbce9rjBv_ts6TAMegS_5aUAZqPQCBQbQIIRiFcfceKgTL2SDusyZ1QxwnDD5cINI0p7P5hFWLfk-8stvDuwQEKXbQDkOdOtKUbK1wo1vqZt1vMhTCvRluxx_is4cSNVL3euCTtKrF5YiZpraNZBpaJwjcl-0-7DCskc2xbx4Dq4onrAYjoGDlkiDw7SZGKwRUqSLu1hfThwIs4oBxyYe4Gr7CvReB3XDZMkKZOh0RZKRmBuxx-Zly6hkOmnP4PNHDHS5O6Y3EWyIDoHuL0V7OzLs3hby_09XUvf7iD8NyZw8zqr7NLHB34zHf4DLv329NwSe7Ogndh3k_-b1_YlbarPhNrsAXCXVoXNE6iQBX3sRBtVAZAHJMr_ZT43kyu7UhZZY-KaZh0SyGeYf2HwCxEchZHnAMmXR3FeJRWqAfJvTgPIiQAjoPC-jcap3tX9EVwuYE9SGu0OQTHhWdzj2uJfzXp6MuQ9xP-vT9DOlsMSIyAMPyN01GReGB3W0YzqPmBqs0_XoUEw6ehnCVENaBcaxQAlwAtIgI6UbDMuJSEjzGsQMmj6VMh6Rk-VjGSP3dQlHLVD-owEmknSTEY_v33ivgv1RDjfA9CtRk-wqxorQzt55f3ZbRMaTqjN8SsblYOrMgV5okeS8riiP0fMkIc9q59Gl1MbLvNP7qj-m60VsvXfrQ7CaSssiQ4w0ysBt1rYxGIQOdJTqR083IdSD61xgexPHibsYUDZukUSeqs2UcJ_SjBEiHXI9Cc6EJHQIFTr0hWyCFlsg4FT5LS5Dy8svF3yco6_1zYFh732VuPDMEsjn4qjWW__hKpi5akeXki6gMQ4vaWeMv94NXXHX7feCrNY0U9YwAY15HNcjE9DDS92lD9_7N5X0fHgjqaQZ3TP5bY8pMrvl5U9eW_MdyZx8rDKYMU_pGGxEAIVHKaYa2W61lc0AMUITGTZ4KTOsdGUjw')

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
