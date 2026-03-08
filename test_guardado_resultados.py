# -*- coding: utf-8 -*-
"""
Script de prueba para verificar que el guardado en Respuestas de formulario 1 funciona
"""

import sys
import codecs

# Configurar encoding UTF-8 para Windows
if sys.platform == 'win32':
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

from resultados_sheets_adapter import ResultadosSheetsAdapter

def test_guardado():
    """Prueba el guardado de un resultado de llamada"""
    print("\n" + "=" * 60)
    print("PRUEBA DE GUARDADO EN RESPUESTAS DE FORMULARIO 1")
    print("=" * 60 + "\n")

    # Inicializar adaptador
    print("1. Inicializando ResultadosSheetsAdapter...")
    resultados_manager = ResultadosSheetsAdapter()
    print(" Adaptador inicializado\n")

    # Datos de prueba
    datos_prueba = {
        'nombre_negocio': 'PRUEBA - Ferretería Test',
        'telefono': '+526621234567',
        'ciudad': 'Guadalajara',
        'estado_llamada': 'Respondio',
        'pregunta_1': 'Grifería, Herramientas',
        'pregunta_2': 'Sí',
        'pregunta_3': 'Crear Pedido Inicial Sugerido',
        'pregunta_4': '',
        'pregunta_5': 'Sí',
        'pregunta_6': 'Tal vez',
        'pregunta_7': 'Hacer pedido',
        'resultado': 'APROBADO',
        'duracion': 120,
        'nivel_interes_clasificado': 'Alto',
        'estado_animo_cliente': 'Positivo',
        'opinion_bruce': 'Cliente muy interesado, respondió todas las preguntas correctamente.',
        'calificacion': 9,
        'bruce_id': 'BRUCE_TEST_001',
        'telefono_completo': '+526621234567',
        'ciudad_estado': 'Guadalajara, Jalisco',
        'whatsapp': '+526621234567'
    }

    print("2. Datos de prueba preparados:")
    print(f"   - Negocio: {datos_prueba['nombre_negocio']}")
    print(f"   - Teléfono: {datos_prueba['telefono']}")
    print(f"   - Resultado: {datos_prueba['resultado']}")
    print(f"   - Calificación: {datos_prueba['calificacion']}/10")
    print()

    # Intentar guardar
    print("3. Guardando en Google Sheets...")
    try:
        exito = resultados_manager.guardar_resultado_llamada(datos_prueba)

        if exito:
            print("\n ¡GUARDADO EXITOSO!")
            print("   Verifica en: https://docs.google.com/spreadsheets/d/1U_z1KNqCxSRZVi7wvO2FQH4zIdS_wxuafxj6YHdHEqg/edit")
            print("   Hoja: Respuestas de formulario 1")
        else:
            print("\n Guardado falló (retornó False)")

    except Exception as e:
        print(f"\n ERROR al guardar: {e}")
        import traceback
        print("\nTraceback completo:")
        print(traceback.format_exc())

    print("\n" + "=" * 60)

if __name__ == "__main__":
    test_guardado()
