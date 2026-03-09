"""
IMPORTADOR DE CONTACTOS MEJORADO - VERSION OPTIMIZADA PARA BRUCE W

CAMBIOS CRÍTICOS vs versión original:
1. Filtro de calidad: Mínimo 10 reseñas + Calificación >= 3.5 estrellas
2. Solo categorías 100% relevantes (eliminadas: Audio, Seguridad, Empaques, Envíos)
3. Filtro de estado: Solo negocios ABIERTOS
4. Validación de teléfono: Solo contactos con teléfono disponible

IMPACTO ESPERADO:
- Reducción de leads: ~60% (de 2,133 a ~850)
- Aumento de conversión: 5.6% -> 14-18%
- Reducción de interés bajo: 57.8% -> ~25%

Fecha: 2026-01-24
"""

import googlemaps
import pandas as pd
import requests
import time
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import logging
import os
from collections import Counter
import simplekml

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('importador_contactos.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Configurar UTF-8 en Windows
import sys
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')
if sys.stderr.encoding != 'utf-8':
    sys.stderr.reconfigure(encoding='utf-8')

# Importar folium
try:
    import folium
    from folium.plugins import MarkerCluster
    FOLIUM_DISPONIBLE = True
except ImportError:
    FOLIUM_DISPONIBLE = False
    logger.warning("folium no está instalado. Mapas HTML interactivos no estarán disponibles.")

# API Key para Google Maps
API_KEY = "AIzaSyANnZsLqkul5Z8x1PlVsaihlHkpJHqDhJU"
gmaps = googlemaps.Client(key=API_KEY)

# Configuración de Telegram
TELEGRAM_TOKEN = "8404009072:AAGZC4Lb46ELP9-8zrRDWJG61a5F5lHjmSw"
TELEGRAM_CHAT_ID = "5838212022"


def enviar_mensaje_telegram(mensaje):
    """Envía un mensaje a Telegram con las estadísticas."""
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        data = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": mensaje,
            "parse_mode": "HTML"
        }
        response = requests.post(url, data=data, timeout=10)
        if response.status_code == 200:
            logger.info("Notificación enviada a Telegram")
        else:
            logger.warning(f"Error al enviar a Telegram: {response.text}")
    except Exception as e:
        logger.error(f"Error al enviar mensaje a Telegram: {e}")


def buscar_negocios(categoria, ciudad, reintentos=3):
    """
    Busca negocios con FILTROS MEJORADOS para mejor calidad de leads.

    CAMBIOS vs versión original:
    1. Mínimo 10 reseñas (antes: 5)
    2. Calificación >= 3.5 estrellas (antes: sin filtro)
    3. Solo negocios ABIERTOS (antes: incluía cerrados)
    4. Solo con teléfono disponible (antes: incluía sin teléfono)
    """
    resultados = []
    lugares_ids_vistos = set()
    leads_descartados = {
        'pocas_resenas': 0,
        'baja_calificacion': 0,
        'cerrado': 0,
        'sin_telefono': 0
    }

    logger.info(f"Buscando {categoria} en {ciudad} (FILTROS MEJORADOS)...")

    # Variaciones de búsqueda
    variaciones_busqueda = [
        f"{categoria} en {ciudad}",
        f"{categoria} cerca de {ciudad}",
        f"{categoria} {ciudad}",
    ]

    for variacion in variaciones_busqueda:
        for intento in range(reintentos):
            try:
                lugares_response = gmaps.places(
                    query=variacion,
                    language="es",
                    type="establishment"
                )

                lugares = lugares_response.get('results', [])

                # Obtener todas las páginas disponibles
                paginas_obtenidas = 1
                while 'next_page_token' in lugares_response and paginas_obtenidas < 3:
                    time.sleep(2)

                    try:
                        lugares_response = gmaps.places(
                            page_token=lugares_response['next_page_token']
                        )
                        lugares.extend(lugares_response.get('results', []))
                        paginas_obtenidas += 1
                        logger.info(f"  -> Página {paginas_obtenidas}: Total parcial {len(lugares)} lugares")
                    except Exception as e:
                        logger.warning(f"No se pudo obtener más resultados: {e}")
                        break

                # Procesar resultados con FILTROS MEJORADOS
                for lugar in lugares:
                    place_id = lugar.get('place_id')

                    if place_id in lugares_ids_vistos:
                        continue

                    calificacion = lugar.get("rating")
                    num_resenas = lugar.get("user_ratings_total")

                    # FILTRO 1: Mínimo 10 reseñas (MEJORADO de 5)
                    if not num_resenas or num_resenas < 10:
                        leads_descartados['pocas_resenas'] += 1
                        continue

                    # FILTRO 2: Calificación mínima 3.5 estrellas (NUEVO)
                    if not calificacion or calificacion < 3.5:
                        leads_descartados['baja_calificacion'] += 1
                        continue

                    lugares_ids_vistos.add(place_id)

                    # Obtener detalles adicionales
                    try:
                        detalles = gmaps.place(place_id, language="es")['result']

                        # FILTRO 3: Solo negocios ABIERTOS (NUEVO)
                        abierto_ahora = detalles.get("opening_hours", {}).get("open_now")
                        if abierto_ahora != True:
                            leads_descartados['cerrado'] += 1
                            continue

                        # FILTRO 4: Solo con teléfono disponible (NUEVO)
                        telefono = detalles.get("formatted_phone_number", "")
                        if not telefono or telefono == "No disponible":
                            leads_descartados['sin_telefono'] += 1
                            continue

                        # Clasificar tamaño según reseñas
                        if num_resenas < 200:
                            tamano = "Pequeño"
                        elif num_resenas < 500:
                            tamano = "Mediano"
                        else:
                            tamano = "Grande"

                        negocio = {
                            "Nombre": lugar.get("name"),
                            "Dirección": lugar.get("formatted_address"),
                            "Calificación": calificacion,
                            "Núm. de Reseñas": num_resenas,
                            "Google Maps Link": f"https://www.google.com/maps/place/?q=place_id:{place_id}",
                            "Teléfono": telefono,
                            "Sitio Web": detalles.get("website", "No disponible"),
                            "Horarios": str(detalles.get("opening_hours", {}).get("weekday_text", "No disponible")),
                            "Estado": "Abierto",
                            "Latitud": lugar.get("geometry", {}).get("location", {}).get("lat"),
                            "Longitud": lugar.get("geometry", {}).get("location", {}).get("lng"),
                            "Tamaño": tamano,
                            "Tipo Cliente": "Mayorista/Corporativo" if num_resenas > 300 else "Minorista",
                        }
                        resultados.append(negocio)
                        logger.info(f"  ✓ {lugar.get('name')} - {calificacion}⭐ ({num_resenas} reseñas)")

                        time.sleep(0.3)

                    except Exception as e:
                        logger.warning(f"Error al obtener detalles de {lugar.get('name')}: {e}")
                        continue

                if lugares:
                    break

            except googlemaps.exceptions.ApiError as e:
                logger.error(f"Error en la API de Google (intento {intento + 1}/{reintentos}): {str(e)}")
                if intento < reintentos - 1:
                    time.sleep(2 ** intento)
            except Exception as e:
                logger.error(f"Error inesperado (intento {intento + 1}/{reintentos}): {str(e)}")
                if intento < reintentos - 1:
                    time.sleep(2)

        if variacion != variaciones_busqueda[-1]:
            time.sleep(1)

    # Reporte de filtrado
    total_descartados = sum(leads_descartados.values())
    logger.info(f"\n  Resultados para {categoria}:")
    logger.info(f"    ✓ Aprobados: {len(resultados)}")
    logger.info(f"    ✗ Descartados: {total_descartados}")
    logger.info(f"      - Pocas reseñas (<10): {leads_descartados['pocas_resenas']}")
    logger.info(f"      - Baja calificación (<3.5): {leads_descartados['baja_calificacion']}")
    logger.info(f"      - Cerrado: {leads_descartados['cerrado']}")
    logger.info(f"      - Sin teléfono: {leads_descartados['sin_telefono']}")

    return resultados


def exportar_a_google_sheets(datos, categoria, worksheet, ciudad_busqueda):
    """Exporta los datos obtenidos a la hoja de Google Sheets."""
    try:
        fecha_actual = datetime.now().strftime("%d/%m/%Y")
        num_semana = datetime.now().isocalendar()[1]

        for dato in datos:
            dato["NUM SEMANA"] = num_semana
            dato["Categoría"] = categoria
            dato["Fecha"] = fecha_actual
            dato["Ciudad"] = ciudad_busqueda

        df = pd.DataFrame(datos)

        columnas = [
            "NUM SEMANA", "Nombre", "Ciudad", "Categoría", "Teléfono",
            "", "", "Dirección", "Calificación", "Núm. de Reseñas",
            "Google Maps Link", "Sitio Web", "Horarios", "Estado",
            "Latitud", "Longitud", "Tamaño", "Tipo Cliente", "Fecha"
        ]

        df[""] = ""
        df = df[columnas]

        datos_actuales = worksheet.get_all_values()

        if len(datos_actuales) == 0:
            todas_filas = [df.columns.values.tolist()] + df.values.tolist()
            worksheet.update('A1', todas_filas)
            logger.info(f"'{categoria}' exportado con encabezados ({len(df)} registros)")
        else:
            nombres_existentes = set()
            for fila in datos_actuales[1:]:
                if len(fila) > 7:
                    nombres_existentes.add(f"{fila[1]}|{fila[7]}")

            nuevos_registros = []
            duplicados = 0

            for _, row in df.iterrows():
                key = f"{row['Nombre']}|{row['Dirección']}"
                if key not in nombres_existentes:
                    nuevos_registros.append(row.tolist())
                else:
                    duplicados += 1

            if nuevos_registros:
                ultima_fila = len(datos_actuales) + 1
                worksheet.append_rows(nuevos_registros, value_input_option='USER_ENTERED')
                logger.info(f"'{categoria}': {len(nuevos_registros)} nuevos agregados, {duplicados} duplicados omitidos")
            else:
                logger.info(f"'{categoria}': Todos los registros ya existían ({duplicados} duplicados)")

    except Exception as e:
        logger.error(f"Error al exportar '{categoria}' a Google Sheets: {e}")


def crear_respaldo_csv(datos, categoria, directorio="respaldos_importador"):
    """Crea un respaldo en formato CSV de los datos obtenidos."""
    try:
        if not os.path.exists(directorio):
            os.makedirs(directorio)

        fecha = datetime.now().strftime("%Y%m%d_%H%M%S")
        archivo = os.path.join(directorio, f"{categoria}_{fecha}.csv")

        df = pd.DataFrame(datos)
        df.to_csv(archivo, index=False, encoding='utf-8-sig')
        logger.info(f"Respaldo CSV creado: {archivo}")

    except Exception as e:
        logger.error(f"Error al crear respaldo CSV: {e}")


def exportar_a_kml(todos_resultados, archivo="contactos_importador.kml"):
    """Exporta todos los resultados a UN SOLO archivo KML para importar en Google MyMaps."""
    try:
        kml = simplekml.Kml()

        ciudad_nombre = "Negocios Importador"
        if todos_resultados:
            primera_direccion = todos_resultados[0].get('Dirección', '')
            if ', ' in primera_direccion:
                ciudad_nombre = f"Contactos en {primera_direccion.split(',')[-2].strip()}"

        kml.document.name = ciudad_nombre

        colores_categoria = {
            'Ferreterías': 'ff0000ff',
            'Grifería': 'ff00ff00',
            'Distribuidoras Ferreterías': 'ff00ffff',
            'Materiales de Construcción': 'ff808000',
            'Herramientas Industriales': 'ff008080',
            'Suministros Eléctricos': 'ff80ff80',
            'Plomería y Sanitarios': 'ff8080ff',
            'Pintura y Acabados': 'ffff80ff'
        }

        categorias_dict = {}
        for negocio in todos_resultados:
            categoria = negocio.get('Categoría', 'Sin categoría')
            if categoria not in categorias_dict:
                categorias_dict[categoria] = []
            categorias_dict[categoria].append(negocio)

        for categoria, negocios in categorias_dict.items():
            fol = kml.newfolder(name=f"{categoria} ({len(negocios)})")
            color_hex = colores_categoria.get(categoria, 'ff808080')

            for negocio in negocios:
                lat = negocio.get('Latitud')
                lon = negocio.get('Longitud')

                if lat and lon:
                    descripcion = f"""
                    <b>Categoría:</b> {categoria}<br>
                    <b>Calificación:</b> {negocio.get('Calificación', 'N/A')}⭐<br>
                    <b>Reseñas:</b> {negocio.get('Núm. de Reseñas', 'N/A')}<br>
                    <b>Dirección:</b> {negocio.get('Dirección', 'N/A')}<br>
                    <b>Teléfono:</b> {negocio.get('Teléfono', 'No disponible')}<br>
                    <b>Sitio Web:</b> {negocio.get('Sitio Web', 'No disponible')}<br>
                    <b>Tamaño:</b> {negocio.get('Tamaño', 'N/A')}<br>
                    <b>Tipo Cliente:</b> {negocio.get('Tipo Cliente', 'N/A')}<br>
                    <b>Estado:</b> {negocio.get('Estado', 'Desconocido')}<br>
                    <a href="{negocio.get('Google Maps Link', '#')}">Ver en Google Maps</a>
                    """

                    pnt = fol.newpoint(
                        name=negocio.get('Nombre', 'Sin nombre'),
                        coords=[(lon, lat)]
                    )
                    pnt.description = descripcion
                    pnt.style.iconstyle.color = color_hex
                    pnt.style.iconstyle.scale = 1.2

        kml.save(archivo)
        logger.info(f"Archivo KML creado: {archivo}")
        logger.info(f"  -> Categorías: {len(categorias_dict)}")
        logger.info(f"  -> Total contactos: {len(todos_resultados)}")

    except Exception as e:
        logger.error(f"Error al crear archivo KML: {e}")


def generar_estadisticas(todos_resultados):
    """Genera un resumen estadístico de todos los resultados."""
    try:
        if not todos_resultados:
            return

        df = pd.DataFrame(todos_resultados)

        logger.info("\n" + "="*60)
        logger.info("ESTADÍSTICAS GENERALES (FILTROS MEJORADOS)")
        logger.info("="*60)
        logger.info(f"Total de negocios APROBADOS: {len(df)}")

        calificaciones_numericas = df[df['Calificación'] != 'N/A']['Calificación']
        if len(calificaciones_numericas) > 0:
            logger.info(f"Calificación promedio: {calificaciones_numericas.mean():.2f}⭐ (mínimo 3.5)")

        logger.info(f"Total de reseñas: {df['Núm. de Reseñas'].sum():,}")
        logger.info(f"Reseñas promedio por negocio: {df['Núm. de Reseñas'].mean():.0f} (mínimo 10)")

        logger.info("\nDistribución por tamaño:")
        tamanos = df['Tamaño'].value_counts()
        for tamano, count in tamanos.items():
            logger.info(f"  {tamano}: {count} ({count/len(df)*100:.1f}%)")

        logger.info("\nDistribución por tipo de cliente:")
        tipos = df['Tipo Cliente'].value_counts()
        for tipo, count in tipos.items():
            logger.info(f"  {tipo}: {count} ({count/len(df)*100:.1f}%)")

        logger.info("\nDistribución por categoría:")
        categorias = df['Categoría'].value_counts()
        for categoria, count in categorias.items():
            logger.info(f"  {categoria}: {count} negocios")

        logger.info("\nTop 5 negocios por reseñas:")
        top5 = df.nlargest(5, 'Núm. de Reseñas')
        for idx, row in top5.iterrows():
            logger.info(f"  {row['Nombre']} - {row['Calificación']}⭐ ({row['Núm. de Reseñas']} reseñas)")

        logger.info("\nCobertura:")
        con_web = len(df[df['Sitio Web'] != 'No disponible'])
        logger.info(f"  Con sitio web: {con_web} ({con_web/len(df)*100:.1f}%)")
        logger.info(f"  Con teléfono: {len(df)} (100% - filtro aplicado)")
        logger.info(f"  Estado Abierto: {len(df)} (100% - filtro aplicado)")

        logger.info("="*60 + "\n")

    except Exception as e:
        logger.error(f"Error al generar estadísticas: {e}")


if __name__ == "__main__":
    # Configurar credenciales de Google Sheets
    try:
        scopes = ['https://www.googleapis.com/auth/spreadsheets']
        creds = Credentials.from_service_account_file('bubbly-subject-412101-c969f4a975c5.json', scopes=scopes)
        client = gspread.authorize(creds)

        spreadsheet_id = "1wgEentS16hJrcf6YdEnSpEBcp4SCBJ9TkOCZY439jV4"
        spreadsheet = client.open_by_key(spreadsheet_id)

        try:
            worksheet = spreadsheet.worksheet("LISTA DE CONTACTOS")
        except:
            worksheet = spreadsheet.sheet1
            logger.warning(f"No se encontró la hoja 'LISTA DE CONTACTOS', usando: {worksheet.title}")

        logger.info(f"Usando spreadsheet: {spreadsheet.url}")
        logger.info(f"Hoja activa: {worksheet.title}")

    except FileNotFoundError:
        logger.error("Error: No se encontró el archivo 'bubbly-subject-412101-c969f4a975c5.json'.")
        exit(1)
    except Exception as e:
        logger.error(f"Error al configurar Google Sheets: {e}")
        exit(1)

    # Solicitar ciudad al usuario
    print("\n" + "="*60)
    print("IMPORTADOR DE CONTACTOS - VERSION MEJORADA PARA BRUCE W")
    print("="*60)
    print("\nFILTROS APLICADOS:")
    print("  - Mínimo 10 reseñas (antes: 5)")
    print("  - Calificación >= 3.5 estrellas (antes: sin filtro)")
    print("  - Solo negocios ABIERTOS (antes: incluía cerrados)")
    print("  - Solo con teléfono (antes: incluía sin teléfono)")
    print("\nRESULTADO ESPERADO:")
    print("  - ~60% menos leads, pero MUCHO mejor calidad")
    print("  - Conversión estimada: 14-18% (vs 5.6% actual)")
    print("="*60)

    ciudad = input("\n¿En qué ciudad deseas buscar? (ejemplo: Guadalajara, CDMX, Monterrey): ").strip()

    if not ciudad:
        logger.error("No se ingresó ninguna ciudad. Usando 'Guadalajara' por defecto.")
        ciudad = "Guadalajara"

    logger.info(f"\nCiudad seleccionada: {ciudad}")
    logger.info("Iniciando búsqueda con FILTROS MEJORADOS...")

    # CATEGORÍAS MEJORADAS: Solo 100% relevantes para ferreterías
    categorias = [
        "Ferreterías",
        "Grifería",
        "Distribuidoras Ferreterías",
        "Materiales de Construcción",
        "Herramientas Industriales",
        "Suministros Eléctricos",
        "Plomería y Sanitarios",
        "Pintura y Acabados"
    ]

    todos_resultados = []
    inicio_ejecucion = time.time()

    logger.info(f"\nIniciando búsqueda en {len(categorias)} categorías en {ciudad}...\n")

    for idx, categoria in enumerate(categorias, 1):
        logger.info(f"\n[{idx}/{len(categorias)}] Procesando: {categoria}")
        logger.info("-" * 60)

        resultados = buscar_negocios(categoria, ciudad)

        if resultados:
            todos_resultados.extend(resultados)
            crear_respaldo_csv(resultados, categoria)
            exportar_a_google_sheets(resultados, categoria, worksheet, ciudad)
        else:
            logger.warning(f"No se encontraron resultados para {categoria} en {ciudad}")

        time.sleep(2)

    # Generar estadísticas finales
    generar_estadisticas(todos_resultados)

    # Exportar a Google MyMaps (KML)
    logger.info("\nGenerando archivos de mapas...")
    nombre_archivo_kml = f"contactos_{ciudad.replace(' ', '_').lower()}_MEJORADO.kml"
    exportar_a_kml(todos_resultados, nombre_archivo_kml)

    tiempo_total = time.time() - inicio_ejecucion
    logger.info("\n" + "="*60)
    logger.info("Tiempo total de ejecución: {:.2f} minutos".format(tiempo_total/60))
    logger.info("Todos los datos han sido guardados en: {}".format(spreadsheet.url))
    logger.info("Respaldos CSV guardados en: ./respaldos_importador/")
    logger.info(f"Archivo KML para MyMaps: {nombre_archivo_kml}")
    logger.info("Log completo guardado en: importador_contactos.log")
    logger.info("="*60)

    # Enviar notificación a Telegram
    try:
        total_agregado = len(todos_resultados)

        desglose_categorias = {}
        for negocio in todos_resultados:
            categoria = negocio.get('Categoría', 'Sin categoría')
            desglose_categorias[categoria] = desglose_categorias.get(categoria, 0) + 1

        mensaje = f"""<b>IMPORTADOR MEJORADO - Búsqueda Completada</b>

<b>Ciudad:</b> {ciudad}
<b>Total encontrado:</b> {total_agregado} contactos (FILTROS APLICADOS)
<b>Tiempo:</b> {tiempo_total/60:.2f} minutos

<b>FILTROS APLICADOS:</b>
  Min 10 reseñas + Cal >= 3.5
  Solo ABIERTOS + Con teléfono

<b>Desglose por categoría:</b>
"""

        for categoria, cantidad in sorted(desglose_categorias.items()):
            mensaje += f"  {categoria}: {cantidad}\n"

        mensaje += f"\n<a href=\"{spreadsheet.url}\">Ver Spreadsheet</a>\n"

        enviar_mensaje_telegram(mensaje)
    except Exception as e:
        logger.error(f"Error al preparar mensaje de Telegram: {e}")
