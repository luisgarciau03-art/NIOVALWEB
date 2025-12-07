import dropbox
import os

# Token de acceso de Dropbox (se recomienda usar variable de entorno en producción)
DROPBOX_TOKEN = os.getenv('DROPBOX_TOKEN', 'sl.u.AGIkNsqUprrt4LJ0u0xcjH-B-jFuLVRcTKtzLNC42et_1aO3YiOB8kQceWQX9wVxW8bL7hRb7CQAGDjhcq8i5Q8k0r0GEaC43sJCg_yzO6REaX1zwLKQF_AMWmZJe04ehWJLOyai2c6tSTF6tgB_Y3I2lPDn4lwRmkhDAj0b57D75skF9AInvS7n9IyGV3uwFSFbal4G-mYT0Qsq2v0pa8auTsF5pEYkK-9xAY1awENEqWVhb3vlkL1ros46yQPweuzhLZxZfP3sqneTr7PWFFkseiWkIAmTmGGpzBBgH1CUDkysDn4Kb1M3RaGwrGbD_uyuAMEjydzkqkl9t3dS5m9ClKT9tbFGrH3olVhX2s6L2S7iA0I1XwfBFCa9cRdKk2FghzwVukXLEgopJ1kddErX3WWY-m-Ylhy4BzdRu97TS_n-AaZWVhe-Zi-ZvLLRjIZi-Uo2nK40GR1qzPTapL3t6gF08jWeHIrRWMdCB63LiCtLpYIzbDHEBmliBQXXl9zwTNlSqn1m0BEdJDhvVnndrvhDnpr2yo328Kl-u1Eka1XrnbJHYGmW4wniFGtm4L8vK8eQhLh70-4beqQqQHppHTRc3Eid2XZxcNyrn07wZbSd5z72ISM53ZZFd-gkzPOSuim0i40xjieLE0tDhau6vztWc-1nfx1EVuwjiPcKrM5ZuUxv18-oxTAeNVmKjN30jPk2ClB_JjwCTH3PfXhVyq8QDecZ5LvZ9ebINc1IFN66I8DJHozdxGvAHtM2UNU7lzhXaO-mOPgpGVkZaI4Bk5DO6NHvrOjx8tkLAYG_EUsUQWAK7RIgMxqA9gceIyUSP-8NEji3z91Y7hsxNmsoOoz09baZyWEl1SL5Bj9zCCrB150yi5GiyhfNM9udesuMo0eTvPTMpxljHbm69ZPWNopKtzR8BXWroqwdatsweua5Jk7JuwZSaMpe3ZximYVfjClx72IQ_tFgBOuakEjGgiY4Ix16RukJa87-E8BmqY6TFzE8qmzLigLmxpUbDYQo6U6rZ0Cuh61qnxQwZmGuHOVocF9VsTu9Wx9jHcmTUTORUKOiU7lNytdWiDxWbXnYeKDUCW9hNInEBeZAUAcD02QrOjpqLMGo1JzrW0Dr0qw7uLX9cMSB7_3vNsgkowC0r_i0V9zcw1XYyyru28MxOXKIQvt1js94IU3xANT2VQGPRi5-eBHsiWLJMwH-dupn8t1Y8Fm-Vm0TjjYIeEjJ7sqZ-nQ25eEbdvKhp5DQG5JBZZJ9uUsPLGJ_YqEnzB9E2cYetVFIkBv7G0bqhrVzvf9SM0gnGbCi8nevZL-47Z8eEEwPMZi-0MpyXQejKu36nY9imhxpxd-X6LrlHIq1pofW4cLjpqX05mAAV0uRCrIiN-NOQ_A6pTEOx5qMd26hclqjgN9L1ZHcZro2IP9vnvj3cCA00eyOzHzILRlJKg')

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
