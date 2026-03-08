# -*- coding: utf-8 -*-
"""
Script para agregar ejemplo CORREGIDO de conversación a la hoja LOGS
Con los nuevos cambios:
- Fecha sin hora (solo YYYY-MM-DD)
- ID secuencial (BRUCE01)
- "CLIENTE" en vez de "N/A" para mensajes del cliente
- Columna F: Nombre de la tienda
- Registros insertados al inicio (nuevos arriba, viejos abajo)
"""
import sys
import io

# Fix encoding para Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

from logs_sheets_adapter import LogsSheetsAdapter

# Inicializar adaptador
print("Inicializando conexion con Google Sheets LOGS...")
logs = LogsSheetsAdapter()

# Generar ID BRUCE para esta conversación
bruce_id = logs.generar_nuevo_id_bruce()
nombre_tienda = "Ferretería El Martillo"

print(f"\nAgregando ejemplo de conversacion completa...")
print(f"ID: {bruce_id}")
print(f"Tienda: {nombre_tienda}\n")

# 1. Saludo inicial de Bruce (desde caché)
logs.registrar_mensaje_bruce(
    bruce_id,
    'Hola, muy buenas tardes. Mi nombre es Bruce W, le llamo de NIOVAL, somos distribuidores especializados en productos ferreteros. ¿Me comunico con el encargado de compras o con el dueño del negocio?',
    desde_cache=True,
    cache_key='saludo_inicial',
    nombre_tienda=nombre_tienda
)
print('OK Registro 1: Saludo inicial')

# 2. Respuesta del cliente (Audio/Cache = "CLIENTE")
logs.registrar_mensaje_cliente(
    bruce_id,
    'Sí, soy el encargado de compras',
    nombre_tienda=nombre_tienda
)
print('OK Registro 2: Cliente responde')

# 3. Respuesta de Bruce (generado con tiempo)
logs.registrar_mensaje_bruce(
    bruce_id,
    'Perfecto, Juan. ¿Me podría proporcionar su número de WhatsApp para enviarle nuestro catálogo completo de productos?',
    desde_cache=False,
    tiempo_generacion=1.35,
    nombre_tienda=nombre_tienda
)
print('OK Registro 3: Bruce pregunta WhatsApp')

# 4. Cliente da número
logs.registrar_mensaje_cliente(
    bruce_id,
    'Sí, es el 33 1234 5678',
    nombre_tienda=nombre_tienda
)
print('OK Registro 4: Cliente da WhatsApp')

# 5. Despedida de Bruce (desde caché)
logs.registrar_mensaje_bruce(
    bruce_id,
    'Perfecto. En las próximas dos horas le llega el catálogo completo por WhatsApp. Muchas gracias por su tiempo. Que tenga excelente tarde.',
    desde_cache=True,
    cache_key='despedida_2',
    nombre_tienda=nombre_tienda
)
print('OK Registro 5: Despedida Bruce')

# 6. Cliente se despide
logs.registrar_mensaje_cliente(
    bruce_id,
    'Gracias, hasta luego',
    nombre_tienda=nombre_tienda
)
print('OK Registro 6: Cliente se despide')

print('\n========================================')
print('EXITO: Ejemplo CORREGIDO agregado al spreadsheet LOGS')
print(f'ID de conversacion: {bruce_id}')
print('Cambios aplicados:')
print('  - Fecha sin hora (solo YYYY-MM-DD)')
print(f'  - ID secuencial: {bruce_id}')
print('  - "CLIENTE" para mensajes del cliente')
print('  - Columna F: Nombre de la tienda')
print('  - Nuevos registros al inicio')
print('\nRevisa: https://docs.google.com/spreadsheets/d/1U_z1KNqCxSRZVi7wvO2FQH4zIdS_wxuafxj6YHdHEqg/edit#gid=1923992617')
print('========================================')
