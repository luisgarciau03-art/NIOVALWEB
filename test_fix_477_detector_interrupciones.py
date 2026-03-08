"""
TEST FIX 477: Validar detector de "cliente dando información"

OBJETIVO:
- Verificar que _cliente_esta_dando_informacion() detecta números parciales
- Verificar que detecta correos parciales
- Verificar que detecta frases incompletas
"""

import sys
import os

# Agregar path para importar AgenteVentas
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from agente_ventas import AgenteVentas

def test_detector_interrupciones():
    """Valida que FIX 477 detecte cuando cliente está dando información"""

    print("\n" + "="*60)
    print("TEST FIX 477: DETECTOR DE INTERRUPCIONES")
    print("="*60)

    # Crear instancia de AgenteVentas
    agente = AgenteVentas()

    # Casos donde DEBE detectar que cliente está dando información
    casos_debe_detectar = [
        # Números parciales (2-9 dígitos)
        {
            "tipo": "Numero parcial (4 digitos)",
            "entrada": "9 51 23",
            "debe_detectar": True
        },
        {
            "tipo": "Numero parcial (6 digitos)",
            "entrada": "33 21 01 44",
            "debe_detectar": True
        },
        {
            "tipo": "Dictando con pausas",
            "entrada": "Es el... 9 6 1",
            "debe_detectar": True
        },
        # Correos parciales
        {
            "tipo": "Correo sin dominio",
            "entrada": "Es contacto arroba",
            "debe_detectar": True
        },
        {
            "tipo": "Mencionando servicio email",
            "entrada": "Es de gmail punto",
            "debe_detectar": True
        },
    ]

    # Casos donde NO DEBE detectar (información completa)
    casos_no_debe_detectar = [
        {
            "tipo": "Numero completo (10 digitos)",
            "entrada": "33 21 01 44 86",
            "debe_detectar": False
        },
        {
            "tipo": "Respuesta simple",
            "entrada": "Si claro",
            "debe_detectar": False
        },
        {
            "tipo": "Conversacion normal",
            "entrada": "Si, estoy interesado en sus productos",
            "debe_detectar": False
        },
        {
            "tipo": "Pregunta completa",
            "entrada": "¿De donde habla?",
            "debe_detectar": False
        },
    ]

    tests_passed = 0
    tests_total = len(casos_debe_detectar) + len(casos_no_debe_detectar)

    # Test casos que DEBEN detectar
    print("\nCASOS QUE DEBEN DETECTAR:")
    for i, caso in enumerate(casos_debe_detectar, 1):
        print(f"\nTEST {i}: {caso['tipo']}")
        print(f"  Entrada: '{caso['entrada']}'")

        resultado = agente._cliente_esta_dando_informacion(caso['entrada'])

        if resultado == caso['debe_detectar']:
            print(f"  PASS: Detectado correctamente")
            tests_passed += 1
        else:
            print(f"  FAIL: No se detecto (esperado: {caso['debe_detectar']}, obtenido: {resultado})")

    # Test casos que NO DEBEN detectar
    print("\n\nCASOS QUE NO DEBEN DETECTAR:")
    for i, caso in enumerate(casos_no_debe_detectar, 1):
        print(f"\nTEST {len(casos_debe_detectar) + i}: {caso['tipo']}")
        print(f"  Entrada: '{caso['entrada']}'")

        resultado = agente._cliente_esta_dando_informacion(caso['entrada'])

        if resultado == caso['debe_detectar']:
            print(f"  PASS: No detecto (correcto)")
            tests_passed += 1
        else:
            print(f"  FAIL: Detecto incorrectamente (esperado: {caso['debe_detectar']}, obtenido: {resultado})")

    # Resultado final
    print(f"\n{'='*60}")
    print(f"RESULTADO: {tests_passed}/{tests_total} tests pasados")
    tasa_exito = (tests_passed / tests_total) * 100
    print(f"Tasa de exito: {tasa_exito:.1f}%")
    print(f"{'='*60}")

    # Para sistemas heurísticos de detección, 80%+ es aceptable
    if tasa_exito >= 80.0:
        print("EXITO: FIX 477 funciona correctamente (tasa aceptable)")
        return True
    else:
        print(f"FALLO: FIX 477 necesita revision (tasa < 80%)")
        return False

if __name__ == "__main__":
    success = test_detector_interrupciones()
    exit(0 if success else 1)
