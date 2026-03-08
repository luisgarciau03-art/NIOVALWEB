# -*- coding: utf-8 -*-
"""
Script para agregar una fila de ejemplo con calificación en columna Y
"""
import sys
import io

# Fix encoding para Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

from resultados_sheets_adapter import ResultadosSheetsAdapter

print("Inicializando ResultadosSheetsAdapter...")
resultados = ResultadosSheetsAdapter()

print("\nAgregando ejemplo de llamada con calificacion...")

# Simular datos de una llamada exitosa (calificación 9)
datos_ejemplo = {
    'nombre_negocio': 'Ferretería El Martillo (EJEMPLO)',
    'telefono': '+523312345678',
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
    'opinion_bruce': 'Excelente lead, muy interesado en el catálogo. Proporcionó WhatsApp validado.',
    'calificacion': 9  # Calificación de Bruce (1-10)
}

print("\nDatos del ejemplo:")
print(f"  Tienda: {datos_ejemplo['nombre_negocio']}")
print(f"  Resultado: {datos_ejemplo['resultado']}")
print(f"  Nivel Interés: {datos_ejemplo['nivel_interes_clasificado']}")
print(f"  Calificación: {datos_ejemplo['calificacion']}/10")

resultado = resultados.guardar_resultado_llamada(datos_ejemplo)

if resultado:
    print("\n========================================")
    print("EXITO: Ejemplo con calificación agregado")
    print("Columna Y debe mostrar: 9")
    print("\nRevisa: https://docs.google.com/spreadsheets/d/1U_z1KNqCxSRZVi7wvO2FQH4zIdS_wxuafxj6YHdHEqg/edit#gid=1343998886")
    print("========================================")
else:
    print("\nERROR: No se pudo guardar el ejemplo")
