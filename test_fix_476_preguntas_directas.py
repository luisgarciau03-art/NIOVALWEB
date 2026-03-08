"""
TEST FIX 476: Validar detección de preguntas directas

OBJETIVO:
- Verificar que el método _detectar_patron_simple_optimizado() detecta las 5 categorías
- Validar que las respuestas son instantáneas (sin llamar a GPT)
"""

import sys
import os

# Agregar path para importar AgenteVentas
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from agente_ventas import AgenteVentas

def test_preguntas_directas():
    """Valida que FIX 476 detecte y responda preguntas directas"""

    print("\n" + "="*60)
    print("TEST FIX 476: PREGUNTAS DIRECTAS")
    print("="*60)

    # Crear instancia de AgenteVentas
    agente = AgenteVentas()

    # Casos de prueba
    casos_prueba = [
        {
            "categoria": "PREGUNTA_UBICACION",
            "entrada": "¿De donde habla?",
            "debe_contener": ["Guadalajara", "Jalisco"]
        },
        {
            "categoria": "PREGUNTA_UBICACION",
            "entrada": "¿Donde estan ubicados?",
            "debe_contener": ["Guadalajara", "Jalisco", "env"]  # "env" captura "envíos" y "envios"
        },
        {
            "categoria": "PREGUNTA_IDENTIDAD",
            "entrada": "¿Quien habla?",
            "debe_contener": ["Bruce", "NIOVAL"]
        },
        {
            "categoria": "PREGUNTA_IDENTIDAD",
            "entrada": "¿De parte de quien?",
            "debe_contener": ["Bruce", "NIOVAL"]
        },
        {
            "categoria": "PREGUNTA_PRODUCTOS",
            "entrada": "¿Que productos manejan?",
            "debe_contener": ["ferret", "cintas", "grif"]  # Prefijos para capturar con/sin tildes
        },
        {
            "categoria": "PREGUNTA_PRODUCTOS",
            "entrada": "¿Que venden?",
            "debe_contener": ["ferret"]  # "ferret" captura "ferretería" y "ferreteria"
        },
        {
            "categoria": "PREGUNTA_MARCAS",
            "entrada": "¿Que marcas manejan?",
            "debe_contener": ["NIOVAL", "marca propia"]
        },
        {
            "categoria": "PREGUNTA_PRECIOS",
            "entrada": "¿Cuanto cuesta?",
            "debe_contener": ["WhatsApp", "cat"]  # "cat" captura "catálogo" y "catalogo"
        },
    ]

    tests_passed = 0
    tests_total = len(casos_prueba)

    for i, caso in enumerate(casos_prueba, 1):
        print(f"\nTEST {i}: {caso['categoria']}")
        print(f"  Entrada: '{caso['entrada']}'")

        # Llamar al detector
        resultado = agente._detectar_patron_simple_optimizado(caso['entrada'])

        # Validar que se detectó
        if not resultado:
            print(f"  FAIL: No se detecto patron")
            continue

        # Validar categoría
        if resultado.get('tipo') != caso['categoria']:
            print(f"  FAIL: Categoria incorrecta (esperado: {caso['categoria']}, obtenido: {resultado.get('tipo')})")
            continue

        # Validar respuesta contiene palabras clave
        respuesta = resultado.get('respuesta', '').lower()
        palabras_encontradas = [
            palabra for palabra in caso['debe_contener']
            if palabra.lower() in respuesta
        ]

        if len(palabras_encontradas) == len(caso['debe_contener']):
            print(f"  PASS: Respuesta correcta")
            print(f"    '{resultado.get('respuesta')[:80]}...'")
            tests_passed += 1
        else:
            print(f"  FAIL: Respuesta no contiene palabras clave esperadas")
            print(f"    Esperadas: {caso['debe_contener']}")
            print(f"    Encontradas: {palabras_encontradas}")
            print(f"    Respuesta: '{respuesta[:80]}...'")

    # Resultado final
    print(f"\n{'='*60}")
    print(f"RESULTADO: {tests_passed}/{tests_total} tests pasados")
    print(f"{'='*60}")

    if tests_passed == tests_total:
        print("EXITO: FIX 476 funciona correctamente")
        return True
    else:
        print("FALLO: FIX 476 necesita revision")
        return False

if __name__ == "__main__":
    success = test_preguntas_directas()
    exit(0 if success else 1)
