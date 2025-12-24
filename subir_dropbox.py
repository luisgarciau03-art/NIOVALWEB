<<<<<<< HEAD
import dropbox
import os

# Token de acceso de Dropbox (se recomienda usar variable de entorno en producción)
DROPBOX_TOKEN = os.getenv('DROPBOX_TOKEN', 'sl.u.AGPjGw3p-lxDv71m-36O_rt03rcy-ECbGbxFdfh03evJV0OgT-ZFiSeaWyxJvbRJKcfD0dY8elLbFEUaNBZcbJpMY-sbX8z6IBPX1U8NgFuF2yLs0zXN7Zh3OGXVFxuc_qiRZi0ORttTSyxtBYUkrrRY7qYAFzzJj_63ZqE8_GRRLJpDabXeGfCUr989XB5HFaiuRI9K4rXCTqt82YbskmnosFy4pzq1Gj1tO0kTLuxqAUEvPPVNUdpjmwp8R1PWLt3eTYfzaPt8ubhgGIt3JqqsJi_NvJKfDPj9oBcWSrAtNVrPoRDOOctCOqz-OxATt_OhLt2mB6vugkaVnwmWeGLazELhwtc3vJ22Wnov807uHBKrWkxRru2bHdN1vXMBQbocNEuYSyaXuiCyLOv9anXS_fKM1ZJItU00hVc3uey5RHuBcyzwCk6vf0IL8wUOR2kdebk3WaT7wEIoIgRPrWV79Tiv39VjSlUu2Qbe_djUhMXgIsH6SRxwwJYGfge6KjxMXznMQFYKBMv8et9GX8B5Ii-XCkx3JVze9A9NuIpJYGeO2mUeTs8E7OZgniBsJ343HqS7BiIJwc5uNfFjfLN2L03xoQa0g_IHnK4dbhJ9C6R03iDH8Kr098aYeq7OOIjJ1GrE1N8wgZPTzouB0hTNQ6CXfRBGVfFGPZ3yjcz_3AkUaPYaFZg9-0Ugvr0mhhOXvqKUGdTzOiIACVeBJtsZ2b5_vCHecuCFKnDxn3FrQAIdnGxhOqQdp1unNeL_JHdlWIuVN-jC3PF16u4CJJkXsYafWv3lR5ZDbB4x_pdsA6XSUP3a7R7v0e-6iGA1IS1jVC_UTo0q95p8t-qs7rosIUnHTQ0CqnYc1eA1YpgwvHIThw1brjyw5A-75UrATEIXDx0xh3tue6F6I52zd5h6aElRSdIfaBaPh7SDuk3ML3xKrj-v6rM_JmgCpoyNB5t-zZTkf3uiDJBb7Ax1PGPrPjg7eomGesxooPmv62Qy9K2DT-w31lXxKMglD1CT7cOsUBMES3vw813yuyoOUomqBf8JGdvdB-Mw0WPMbRPudxlUjyK5jCWSjXBD8bO4vnq_HKVZCLtxZS3BIXLhmCDhOBtlwgy3sRzpQpHAVzYP2DU1I3QNFKphK9Negp-oSEy8pMXVXQyULB3Y1Ztzp_DUBrTx_EyvFEDC8hvtBCs6cer0j_qMv8fM4kg8cmUCZUv9i0S3FmPXfDa0BLqojehIM6E9xSzFPQp0dUQAnJ4RMxaCfQPL8T7iKYUVk-Hc8Q-7FgHAGgG_Ahn44ykGwu6Sl8Uno8K4uy1rG60Q1cX7Jf1D-yqvXGwtwWb21pVYWerhrQKyGGo7CiZD9L2ftvZ44CnWpIxk98bAzx2TNAQVAMKCmkNm1INR_f7gDVfQEfvgnt0t7MZ28kQGof5C4IgUc2m2fLeZU4Cx4VOgoNNVeg')

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
DROPBOX_TOKEN = os.getenv('DROPBOX_TOKEN', 'sl.u.AGPjGw3p-lxDv71m-36O_rt03rcy-ECbGbxFdfh03evJV0OgT-ZFiSeaWyxJvbRJKcfD0dY8elLbFEUaNBZcbJpMY-sbX8z6IBPX1U8NgFuF2yLs0zXN7Zh3OGXVFxuc_qiRZi0ORttTSyxtBYUkrrRY7qYAFzzJj_63ZqE8_GRRLJpDabXeGfCUr989XB5HFaiuRI9K4rXCTqt82YbskmnosFy4pzq1Gj1tO0kTLuxqAUEvPPVNUdpjmwp8R1PWLt3eTYfzaPt8ubhgGIt3JqqsJi_NvJKfDPj9oBcWSrAtNVrPoRDOOctCOqz-OxATt_OhLt2mB6vugkaVnwmWeGLazELhwtc3vJ22Wnov807uHBKrWkxRru2bHdN1vXMBQbocNEuYSyaXuiCyLOv9anXS_fKM1ZJItU00hVc3uey5RHuBcyzwCk6vf0IL8wUOR2kdebk3WaT7wEIoIgRPrWV79Tiv39VjSlUu2Qbe_djUhMXgIsH6SRxwwJYGfge6KjxMXznMQFYKBMv8et9GX8B5Ii-XCkx3JVze9A9NuIpJYGeO2mUeTs8E7OZgniBsJ343HqS7BiIJwc5uNfFjfLN2L03xoQa0g_IHnK4dbhJ9C6R03iDH8Kr098aYeq7OOIjJ1GrE1N8wgZPTzouB0hTNQ6CXfRBGVfFGPZ3yjcz_3AkUaPYaFZg9-0Ugvr0mhhOXvqKUGdTzOiIACVeBJtsZ2b5_vCHecuCFKnDxn3FrQAIdnGxhOqQdp1unNeL_JHdlWIuVN-jC3PF16u4CJJkXsYafWv3lR5ZDbB4x_pdsA6XSUP3a7R7v0e-6iGA1IS1jVC_UTo0q95p8t-qs7rosIUnHTQ0CqnYc1eA1YpgwvHIThw1brjyw5A-75UrATEIXDx0xh3tue6F6I52zd5h6aElRSdIfaBaPh7SDuk3ML3xKrj-v6rM_JmgCpoyNB5t-zZTkf3uiDJBb7Ax1PGPrPjg7eomGesxooPmv62Qy9K2DT-w31lXxKMglD1CT7cOsUBMES3vw813yuyoOUomqBf8JGdvdB-Mw0WPMbRPudxlUjyK5jCWSjXBD8bO4vnq_HKVZCLtxZS3BIXLhmCDhOBtlwgy3sRzpQpHAVzYP2DU1I3QNFKphK9Negp-oSEy8pMXVXQyULB3Y1Ztzp_DUBrTx_EyvFEDC8hvtBCs6cer0j_qMv8fM4kg8cmUCZUv9i0S3FmPXfDa0BLqojehIM6E9xSzFPQp0dUQAnJ4RMxaCfQPL8T7iKYUVk-Hc8Q-7FgHAGgG_Ahn44ykGwu6Sl8Uno8K4uy1rG60Q1cX7Jf1D-yqvXGwtwWb21pVYWerhrQKyGGo7CiZD9L2ftvZ44CnWpIxk98bAzx2TNAQVAMKCmkNm1INR_f7gDVfQEfvgnt0t7MZ28kQGof5C4IgUc2m2fLeZU4Cx4VOgoNNVeg')

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
