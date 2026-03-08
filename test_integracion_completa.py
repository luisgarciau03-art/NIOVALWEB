"""
Script de prueba para verificar la integración completa del sistema
Muestra cómo Bruce W ve la información de los clientes
"""

from nioval_sheets_adapter import NiovalSheetsAdapter
from agente_ventas import AgenteVentas
from whatsapp_validator import WhatsAppValidator
import os
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

print("\n" + "=" * 80)
print(" TEST DE INTEGRACIÓN COMPLETA - SISTEMA NIOVAL")
print("=" * 80)

try:
    # 1. Conectar a Google Sheets
    print("\n Paso 1: Conectando a Google Spreadsheet...")
    print("-" * 80)
    adapter = NiovalSheetsAdapter()

    # 2. Obtener estadísticas
    print("\n Paso 2: Estadísticas generales...")
    print("-" * 80)
    stats = adapter.obtener_estadisticas()
    print(f"Total de contactos: {stats.get('total_contactos', 0)}")
    print(f"Con número de teléfono: {stats.get('con_numero', 0)}")
    print(f"Ya llamados (columna F llena): {stats.get('llamados', 0)}")
    print(f"Pendientes de llamar: {stats.get('pendientes', 0)}")
    print(f"Progreso: {stats.get('porcentaje_completado', 0)}%")

    # 3. Obtener contactos pendientes
    print("\n Paso 3: Obteniendo contactos pendientes (primeros 2)...")
    print("-" * 80)
    contactos = adapter.obtener_contactos_pendientes(limite=2)

    if not contactos:
        print(" No hay contactos pendientes")
        print("\nPosibles razones:")
        print("  - Todos los contactos ya tienen valor en columna F")
        print("  - No hay números en columna E")
        print("  - La hoja está vacía")
    else:
        print(f" {len(contactos)} contactos pendientes encontrados\n")

        # 4. Mostrar información completa de cada contacto
        for idx, contacto in enumerate(contactos, 1):
            print("=" * 80)
            print(f"CONTACTO #{idx} - FILA {contacto['fila']}")
            print("=" * 80)

            print("\n INFORMACIÓN BÁSICA:")
            print(f"  Teléfono original: {contacto.get('numero_raw', 'N/A')}")
            print(f"  Teléfono normalizado: {contacto.get('telefono', 'N/A')}")

            print("\n DATOS DEL NEGOCIO (Spreadsheet):")
            print(f"  Nombre (col B): {contacto.get('nombre_negocio', 'N/A')}")
            print(f"  Ciudad (col C): {contacto.get('ciudad', 'N/A')}")
            print(f"  Categoría (col D): {contacto.get('categoria', 'N/A')}")
            print(f"  Domicilio (col H): {contacto.get('domicilio', 'N/A')}")
            print(f"  Horario (col M): {contacto.get('horario', 'N/A')}")

            print("\n DATOS DE GOOGLE MAPS:")
            print(f"  Puntuación (col I): {contacto.get('puntuacion', 'N/A')}")
            print(f"  Reseñas (col J): {contacto.get('resenas', 'N/A')}")
            print(f"  Nombre Maps (col K): {contacto.get('maps', 'N/A')}")
            print(f"  Link Maps (col L): {contacto.get('link', 'N/A')[:50]}..." if contacto.get('link') else "  Link Maps (col L): N/A")

            print("\n OTROS DATOS:")
            print(f"  Estatus (col N): {contacto.get('estatus', 'N/A')}")
            print(f"  Porcentajes (col G): {contacto.get('porcentajes', 'N/A')}")
            print(f"  Latitud (col O): {contacto.get('latitud', 'N/A')}")
            print(f"  Longitud (col P): {contacto.get('longitud', 'N/A')}")
            print(f"  Fecha (col S): {contacto.get('fecha', 'N/A')}")

            # 5. Simular cómo Bruce verá este contacto
            print("\n" + "=" * 80)
            print(" CONTEXTO QUE BRUCE W RECIBIRÁ AL LLAMAR:")
            print("=" * 80)

            # Crear agente temporal para generar contexto
            # Configurar validador según variable de entorno
            whatsapp_method = os.getenv("WHATSAPP_VALIDATOR_METHOD", "formato")

            if whatsapp_method == "formato":
                whatsapp_validator = WhatsAppValidator(method="formato")
            elif whatsapp_method == "twilio":
                whatsapp_validator = WhatsAppValidator(
                    method="twilio",
                    twilio_sid=os.getenv("TWILIO_ACCOUNT_SID"),
                    twilio_token=os.getenv("TWILIO_AUTH_TOKEN")
                )
            elif whatsapp_method == "evolution":
                whatsapp_validator = WhatsAppValidator(
                    method="evolution",
                    evolution_url=os.getenv("EVOLUTION_API_URL"),
                    evolution_key=os.getenv("EVOLUTION_API_KEY"),
                    evolution_instance=os.getenv("EVOLUTION_INSTANCE_NAME", "nioval")
                )
            else:
                whatsapp_validator = None

            agente = AgenteVentas(
                contacto_info=contacto,
                whatsapp_validator=whatsapp_validator
            )

            contexto = agente._generar_contexto_cliente()

            if contexto:
                print(contexto)

                print("\n" + "=" * 80)
                print(" LO QUE ESTO SIGNIFICA:")
                print("=" * 80)

                datos_conocidos = []
                datos_que_preguntar = []

                if contacto.get('nombre_negocio'):
                    datos_conocidos.append(" Nombre del negocio")
                else:
                    datos_que_preguntar.append(" Nombre del negocio")

                if contacto.get('ciudad'):
                    datos_conocidos.append(" Ciudad")
                else:
                    datos_que_preguntar.append(" Ciudad")

                if contacto.get('domicilio'):
                    datos_conocidos.append(" Dirección completa")
                else:
                    datos_que_preguntar.append(" Dirección")

                if contacto.get('horario'):
                    datos_conocidos.append(" Horario de atención")
                else:
                    datos_que_preguntar.append(" Horario")

                # Lo que SIEMPRE pregunta
                datos_que_preguntar.append(" WhatsApp (PRIORIDAD #1)")
                datos_que_preguntar.append(" Email (si no tiene WhatsApp)")
                datos_que_preguntar.append(" Nombre del contacto (opcional)")

                print("\n🟢 BRUCE YA CONOCE:")
                for dato in datos_conocidos:
                    print(f"  {dato}")

                print("\n BRUCE VA A PREGUNTAR:")
                for dato in datos_que_preguntar:
                    print(f"  {dato}")

            else:
                print(" No hay información previa disponible")
                print("Bruce preguntará toda la información necesaria")

            print("\n")

    print("=" * 80)
    print(" TEST DE INTEGRACIÓN COMPLETADO")
    print("=" * 80)

    print("\n PRÓXIMOS PASOS:")
    print("  1. Verificar que la información mostrada es correcta")
    print("  2. Confirmar que Bruce NO preguntará lo que ya sabe")
    print("  3. Ejecutar sistema_llamadas_nioval.py para probar llamadas")
    print("\n")

except Exception as e:
    print(f"\n Error durante el test: {e}")
    import traceback
    traceback.print_exc()

    print("\n POSIBLES SOLUCIONES:")
    print("  1. Verificar que existe: C:\\Users\\PC 1\\bubbly-subject-412101-c969f4a975c5.json")
    print("  2. Verificar que el Service Account tiene acceso al Spreadsheet")
    print("  3. Verificar que la hoja se llama 'LISTA DE CONTACTOS'")
    print("  4. Ejecutar: pip install gspread google-auth python-dotenv")
    print("\n")
