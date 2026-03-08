# -*- coding: utf-8 -*-
"""
Script para agregar ejemplo de conversación a la hoja LOGS
"""
import sys
import io

# Fix encoding para Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

from logs_sheets_adapter import LogsSheetsAdapter

# Inicializar adaptador
print("Inicializando conexion con Google Sheets LOGS...")
logs = LogsSheetsAdapter()

# Agregar ejemplo de conversación
call_sid_ejemplo = 'CA_EJEMPLO_DEMO_001'

print("\nAgregando ejemplo de conversacion completa...\n")

# 1. Saludo inicial de Bruce (desde caché)
logs.registrar_mensaje_bruce(
    call_sid_ejemplo,
    'Hola, muy buenas tardes. Mi nombre es Bruce W, le llamo de NIOVAL, somos distribuidores especializados en productos ferreteros. ¿Me comunico con el encargado de compras o con el dueño del negocio?',
    desde_cache=True,
    cache_key='saludo_inicial'
)
print('OK Registro 1: Saludo inicial')

# 2. Respuesta del cliente
logs.registrar_mensaje_cliente(
    call_sid_ejemplo,
    'Sí, soy el encargado de compras'
)
print('OK Registro 2: Cliente responde')

# 3. Respuesta de Bruce (generado con tiempo)
logs.registrar_mensaje_bruce(
    call_sid_ejemplo,
    'Perfecto, Juan. ¿Me podría proporcionar su número de WhatsApp para enviarle nuestro catálogo completo de productos?',
    desde_cache=False,
    tiempo_generacion=1.35
)
print('OK Registro 3: Bruce pregunta WhatsApp')

# 4. Cliente da número
logs.registrar_mensaje_cliente(
    call_sid_ejemplo,
    'Sí, es el 33 1234 5678'
)
print('OK Registro 4: Cliente da WhatsApp')

# 5. Despedida de Bruce (desde caché)
logs.registrar_mensaje_bruce(
    call_sid_ejemplo,
    'Perfecto. En las próximas dos horas le llega el catálogo completo por WhatsApp. Muchas gracias por su tiempo. Que tenga excelente tarde.',
    desde_cache=True,
    cache_key='despedida_2'
)
print('OK Registro 5: Despedida Bruce')

# 6. Cliente se despide
logs.registrar_mensaje_cliente(
    call_sid_ejemplo,
    'Gracias, hasta luego'
)
print('OK Registro 6: Cliente se despide')

print('\n========================================')
print('EXITO: Ejemplo completo agregado al spreadsheet LOGS')
print('Revisa: https://docs.google.com/spreadsheets/d/1U_z1KNqCxSRZVi7wvO2FQH4zIdS_wxuafxj6YHdHEqg/edit#gid=1923992617')
print('========================================')
