# -*- coding: utf-8 -*-
"""
Script para probar que el ID BRUCE se guarda en columna Z
"""
import sys
import io

# Fix encoding para Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

from resultados_sheets_adapter import ResultadosSheetsAdapter
from logs_sheets_adapter import LogsSheetsAdapter

print("Inicializando adaptadores...")
resultados = ResultadosSheetsAdapter()
logs = LogsSheetsAdapter()

# Generar nuevo ID BRUCE
bruce_id = logs.generar_nuevo_id_bruce()
print(f"\nID BRUCE generado: {bruce_id}")

print("\nAgregando ejemplo de llamada con ID BRUCE...")

# Simular datos de una llamada
datos_ejemplo = {
    'nombre_negocio': f'Ferretería Ejemplo {bruce_id}',
    'telefono': '+523398765432',
    'ciudad': 'Guadalajara',
    'estado_llamada': 'Dueño',
    'pregunta_1': 'Ferreteria',
    'pregunta_2': 'SI',
    'pregunta_3': 'Crear Pedido Inicial',
    'pregunta_4': 'SI',
    'pregunta_5': 'SI',
    'pregunta_6': 'SI',
    'pregunta_7': 'SI',
    'resultado': 'ACEPTADO',
    'duracion': 180,
    'nivel_interes_clasificado': 'CALIENTE',
    'estado_animo_cliente': 'Positivo',
    'opinion_bruce': f'Llamada de prueba con {bruce_id}',
    'calificacion': 9,
    'bruce_id': bruce_id  # ID BRUCE para columna Z
}

print(f"\nDatos del ejemplo:")
print(f"  Tienda: {datos_ejemplo['nombre_negocio']}")
print(f"  Calificación: {datos_ejemplo['calificacion']}/10")
print(f"  ID BRUCE: {datos_ejemplo['bruce_id']}")

resultado = resultados.guardar_resultado_llamada(datos_ejemplo)

if resultado:
    print("\n========================================")
    print("EXITO: Ejemplo con ID BRUCE agregado")
    print(f"Columna Y debe mostrar: {datos_ejemplo['calificacion']}")
    print(f"Columna Z debe mostrar: {datos_ejemplo['bruce_id']}")
    print("\nRevisa: https://docs.google.com/spreadsheets/d/1U_z1KNqCxSRZVi7wvO2FQH4zIdS_wxuafxj6YHdHEqg/edit#gid=1343998886")
    print("========================================")
else:
    print("\nERROR: No se pudo guardar el ejemplo")
