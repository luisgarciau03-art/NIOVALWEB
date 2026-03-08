"""
TEST FIX 475: Validar reducción de timeout Deepgram (1.0s -> 0.3s)

OBJETIVO:
- Verificar que el timeout se redujo de 1.0s a 0.3s
- Confirmar que el cambio está documentado correctamente
"""

import re

def test_timeout_deepgram():
    """Valida que el timeout de Deepgram esté configurado en 0.3s"""

    print("\n" + "="*60)
    print("TEST FIX 475: TIMEOUT DEEPGRAM")
    print("="*60)

    # Leer archivo servidor_llamadas.py
    try:
        with open('servidor_llamadas.py', 'r', encoding='utf-8') as f:
            contenido = f.read()
    except FileNotFoundError:
        print("ERROR: No se encontro servidor_llamadas.py")
        return False

    # Buscar la línea del timeout
    patron_timeout = r'max_espera_final_extra\s*=\s*([\d.]+)'
    match = re.search(patron_timeout, contenido)

    if not match:
        print("ERROR: No se encontro variable max_espera_final_extra")
        return False

    timeout_actual = float(match.group(1))

    print(f"\nTimeout encontrado: {timeout_actual}s")

    # Validaciones
    tests_passed = 0
    tests_total = 3

    # TEST 1: Timeout debe ser 0.3s
    if timeout_actual == 0.3:
        print("  PASS: Timeout configurado en 0.3s")
        tests_passed += 1
    else:
        print(f"  FAIL: Timeout es {timeout_actual}s (esperado: 0.3s)")

    # TEST 2: Debe existir comentario FIX 475
    if 'FIX 475' in contenido:
        print("  PASS: Comentario FIX 475 encontrado")
        tests_passed += 1
    else:
        print("  FAIL: No se encontro comentario FIX 475")

    # TEST 3: Comentario debe mencionar reducción de 1.0s a 0.3s
    patron_comentario = r'(1\.0.*0\.3|reducir.*timeout|AUDITORIA W04)'
    if re.search(patron_comentario, contenido, re.IGNORECASE):
        print("  PASS: Comentario explica la reduccion")
        tests_passed += 1
    else:
        print("  FAIL: Comentario no explica correctamente la reduccion")

    # Resultado final
    print(f"\n{'='*60}")
    print(f"RESULTADO: {tests_passed}/{tests_total} tests pasados")
    print(f"{'='*60}")

    if tests_passed == tests_total:
        print("EXITO: FIX 475 implementado correctamente")
        return True
    else:
        print("FALLO: FIX 475 necesita revision")
        return False

if __name__ == "__main__":
    success = test_timeout_deepgram()
    exit(0 if success else 1)
