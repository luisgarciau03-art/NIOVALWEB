<<<<<<< HEAD
import dropbox
import os

# Token de acceso de Dropbox (se recomienda usar variable de entorno en producción)
DROPBOX_TOKEN = os.getenv('DROPBOX_TOKEN', 'sl.u.AGMxgVIgwLW2Vha10x_I7gqloxeOIV4FH1ehWaWjRVuGU3PMwgOnb2TuiGS6ATRmC1sYRWNbCp2LXjX7MWhyvbHnQF0-DEx8cpyWESnFxenoGnhNhtk96ERaVifB53cBN3yKDaFRZqKPygQNTLPgEeaBLn5jrMUbWB-CTh0pcRlbYg-G_cKezNQlHCBYYPnNtuAA9bD5B_30lAICR3hVywpTuZIKccJJEt9zxAll0AenS9u6H_oATbQUbbYutyawxR9TC4fhAmsKOQGkYIKlbZ7ZOA-J00VZsurM4C5x0IoCyej4vkQb8qkha09hmj0ORLZ2rwLvtJJzUKnIYXk1hZm0H5RdH5Zt3rx13J8z9F1xtnQc1j1foaBC--Awbqvn9WEO20xMei6Cl3C_dDRh2hOWyH-zoUvVATzlS_sxwcrXaAMIqVPG86R6j-y6vZLYINxImhUs4bSUPm1Gps6gW7H8WeGU5JWFqIPilAc6yZZyslaTgz5RtwLOWndBwFRgvPIqyMUNAq297WoVnet9kO85p5BiYZSuFo-pxOn3vwtvoBTPGeWMEANA6rvrUE8QE6qSNc_Xdu7teD4Pavy0zAl-mIFemCC7r4hq665awkdkkwEivKhTNMxvILrBkW6ze8z044tQE0trOtnRKu0umFWPxdW6-2mPcjvLeX0jPcd4x4IqpizBRglb9sraTSEEF14LiEblN-TuwS144bG3NZkEgI6TjVGqvnvZZ-l8yVOAdBLaEPBSJZfBBxe5ncGgewobqKE6kIlKqYHha9KPSSgLymw3oq0rIa41b5vT2fvOS3AlRekgcX0Va9vpdZKPcB9AQdAZ-NXANTG-D0DO_6dKFXv8yAb0_UXo5cF2G1meRLInN3DY4JKY7p7Qc-uCrCz7wgHYDJvpv2HWRJzIoFwKXoogx90y2VRio__BtIyEXIRMgqrxfZZJeRG297I3yPJRgZxaJNNCTyfz2cVI22OyEK9nBgCiQ_JyRVePQKit5gcoNH7TGGPn1kuhuKeO4U52qu_mxciHgKGocor-fLOcUpYz7saQBFPwO5NyggPqCxG4n-k1mhZdiWDEDgrWXzHgkbB-4UI7ROzxoG4dDpEhoq3EmKU4o6S1Sw8mZGMbqmIMKvPFjRrT2CJPdRCyc9hq8SGFNLpspNpWTqQ82Fd9UHnD9-l4auSG7MVOX4Ocev2SyS88yeIXvocAs1iZYBDmL4QIgz6NtDdMINrPrEK22Wpu7SJI69BDjSyi4e6Jtlawzdc-dvrObO11tavs4CK0t7K662_z131-iGI4Zn4aQT4XumDW-cVnuGuP__alqBgQ2LO-L-jT5zU6d9QODN666hBcsP3btzWD4Dof3oOl0DFh3u5nGjRBJtrDkF5qG9OKy1XDGbmEs0nZ9TsFzCQmtUMzwrUhi_u9KoVHY7kbZQ9l9RN5_JpXx0Sle4hOhw')

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
DROPBOX_TOKEN = os.getenv('DROPBOX_TOKEN', 'sl.u.AGMxgVIgwLW2Vha10x_I7gqloxeOIV4FH1ehWaWjRVuGU3PMwgOnb2TuiGS6ATRmC1sYRWNbCp2LXjX7MWhyvbHnQF0-DEx8cpyWESnFxenoGnhNhtk96ERaVifB53cBN3yKDaFRZqKPygQNTLPgEeaBLn5jrMUbWB-CTh0pcRlbYg-G_cKezNQlHCBYYPnNtuAA9bD5B_30lAICR3hVywpTuZIKccJJEt9zxAll0AenS9u6H_oATbQUbbYutyawxR9TC4fhAmsKOQGkYIKlbZ7ZOA-J00VZsurM4C5x0IoCyej4vkQb8qkha09hmj0ORLZ2rwLvtJJzUKnIYXk1hZm0H5RdH5Zt3rx13J8z9F1xtnQc1j1foaBC--Awbqvn9WEO20xMei6Cl3C_dDRh2hOWyH-zoUvVATzlS_sxwcrXaAMIqVPG86R6j-y6vZLYINxImhUs4bSUPm1Gps6gW7H8WeGU5JWFqIPilAc6yZZyslaTgz5RtwLOWndBwFRgvPIqyMUNAq297WoVnet9kO85p5BiYZSuFo-pxOn3vwtvoBTPGeWMEANA6rvrUE8QE6qSNc_Xdu7teD4Pavy0zAl-mIFemCC7r4hq665awkdkkwEivKhTNMxvILrBkW6ze8z044tQE0trOtnRKu0umFWPxdW6-2mPcjvLeX0jPcd4x4IqpizBRglb9sraTSEEF14LiEblN-TuwS144bG3NZkEgI6TjVGqvnvZZ-l8yVOAdBLaEPBSJZfBBxe5ncGgewobqKE6kIlKqYHha9KPSSgLymw3oq0rIa41b5vT2fvOS3AlRekgcX0Va9vpdZKPcB9AQdAZ-NXANTG-D0DO_6dKFXv8yAb0_UXo5cF2G1meRLInN3DY4JKY7p7Qc-uCrCz7wgHYDJvpv2HWRJzIoFwKXoogx90y2VRio__BtIyEXIRMgqrxfZZJeRG297I3yPJRgZxaJNNCTyfz2cVI22OyEK9nBgCiQ_JyRVePQKit5gcoNH7TGGPn1kuhuKeO4U52qu_mxciHgKGocor-fLOcUpYz7saQBFPwO5NyggPqCxG4n-k1mhZdiWDEDgrWXzHgkbB-4UI7ROzxoG4dDpEhoq3EmKU4o6S1Sw8mZGMbqmIMKvPFjRrT2CJPdRCyc9hq8SGFNLpspNpWTqQ82Fd9UHnD9-l4auSG7MVOX4Ocev2SyS88yeIXvocAs1iZYBDmL4QIgz6NtDdMINrPrEK22Wpu7SJI69BDjSyi4e6Jtlawzdc-dvrObO11tavs4CK0t7K662_z131-iGI4Zn4aQT4XumDW-cVnuGuP__alqBgQ2LO-L-jT5zU6d9QODN666hBcsP3btzWD4Dof3oOl0DFh3u5nGjRBJtrDkF5qG9OKy1XDGbmEs0nZ9TsFzCQmtUMzwrUhi_u9KoVHY7kbZQ9l9RN5_JpXx0Sle4hOhw')

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
