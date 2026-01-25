"""
Test rápido para verificar que el guardado en Google Sheets funciona
"""

import sys
import io

# Configurar encoding UTF-8 para Windows
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

from resultados_sheets_adapter import ResultadosSheetsAdapter
from datetime import datetime

print("\n" + "=" * 60)
print(" TEST - GUARDADO EN GOOGLE SHEETS")
print("=" * 60 + "\n")

try:
    # Inicializar adapter
    print(" Conectando a Google Sheets...")
    adapter = ResultadosSheetsAdapter()

    # Datos de prueba
    datos_prueba = {
        'nombre_negocio': 'TEST - Ferretería Prueba',
        'estado_llamada': 'Respondio',
        'pregunta_1': 'Entregas Rápidas, Precio Preferente',
        'pregunta_2': 'Sí',
        'pregunta_3': 'Crear Pedido Inicial Sugerido',
        'pregunta_4': 'Sí',
        'pregunta_5': 'Sí',
        'pregunta_6': 'Sí',
        'pregunta_7': 'Pedido',
        'resultado': 'APROBADO',
        'nivel_interes_clasificado': 'Alto',
        'estado_animo_cliente': 'Positivo',
        'opinion_bruce': 'Llamada exitosa, cliente muy receptivo y con interés genuino.',
        'duracion': '3:45'
    }

    print("\n Datos de prueba preparados:")
    print(f"   Negocio: {datos_prueba['nombre_negocio']}")
    print(f"   Resultado: {datos_prueba['resultado']}")
    print(f"   Interés: {datos_prueba['nivel_interes_clasificado']}")

    print("\n Guardando en Google Sheets...")
    exito = adapter.guardar_resultado_llamada(datos_prueba)

    if exito:
        print("\n" + "=" * 60)
        print(" ¡GUARDADO EXITOSO!")
        print("=" * 60)
        print("\n Ve a tu Google Sheets:")
        print("   Spreadsheet: Respuestas de formulario 1")
        print("   Última fila: Debería aparecer 'TEST - Ferretería Prueba'")
        print("\n El sistema de guardado funciona correctamente")
    else:
        print("\n" + "=" * 60)
        print(" ERROR AL GUARDAR")
        print("=" * 60)
        print("\nRevisar:")
        print("  1. Credenciales de Google Sheets")
        print("  2. Permisos del Service Account")
        print("  3. Conexión a internet")

except Exception as e:
    print(f"\n Error: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 60)
