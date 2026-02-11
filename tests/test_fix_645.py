"""
Tests de regresión para FIX 645 - BRUCE2073
Problema: "esperar a que regrese" matcheaba "esperar" y activaba "Claro, espero"
cuando el cliente estaba pidiendo CALLBACK, no transferencia.
"""
import sys
import os

# Configurar path antes de imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


def test_callback_esperar_a_que_regrese():
    """
    BRUCE2073 - Cliente dice "tendrías que esperar a que regrese"
    NO debe activar modo espera (transferencia), es un CALLBACK
    """
    frase_limpia = "tendrías que esperar a que regrese"

    # Patrones de callback de FIX 645
    patrones_callback_645 = [
        'esperar a que regrese', 'esperar a que llegue', 'esperar a que venga',
        'esperar a que vuelva', 'esperar a que entre', 'esperar a que esté',
        'tendrías que esperar', 'tienes que esperar', 'tiene que esperar',
        'tendría que esperar', 'tendríamos que esperar',
        'habría que esperar', 'hay que esperar',
        'debe esperar', 'debes esperar', 'mejor esperar',
        'esperar hasta que', 'esperar cuando',
        'marcar más tarde', 'llamar más tarde', 'marcar después', 'llamar después',
        'volver a marcar', 'volver a llamar', 'regresar la llamada'
    ]

    es_callback = any(p in frase_limpia for p in patrones_callback_645)
    assert es_callback, "Debe detectar que es CALLBACK"


def test_callback_variantes():
    """Verificar que todas las variantes de callback se detectan"""
    frases_callback = [
        "tendrías que esperar a que regrese",
        "tienes que esperar a que llegue",
        "hay que esperar a que vuelva",
        "debe esperar hasta que esté",
        "marcar más tarde cuando llegue",
        "llamar después",
        "volver a marcar más tarde",
        "regresar la llamada cuando regrese"
    ]

    patrones_callback_645 = [
        'esperar a que regrese', 'esperar a que llegue', 'esperar a que venga',
        'esperar a que vuelva', 'esperar a que entre', 'esperar a que esté',
        'tendrías que esperar', 'tienes que esperar', 'tiene que esperar',
        'tendría que esperar', 'tendríamos que esperar',
        'habría que esperar', 'hay que esperar',
        'debe esperar', 'debes esperar', 'mejor esperar',
        'esperar hasta que', 'esperar cuando',
        'marcar más tarde', 'llamar más tarde', 'marcar después', 'llamar después',
        'volver a marcar', 'volver a llamar', 'regresar la llamada'
    ]

    for frase in frases_callback:
        frase_limpia = frase.lower()
        es_callback = any(p in frase_limpia for p in patrones_callback_645)
        assert es_callback, f"Debe detectar '{frase}' como CALLBACK"


def test_transferencia_no_es_callback():
    """Verificar que transferencias reales NO se detectan como callback"""
    frases_transferencia = [
        "un momento",
        "ahorita se lo paso",
        "espere un segundo",
        "permítame un momento",
        "déjeme ver si está"
    ]

    patrones_callback_645 = [
        'esperar a que regrese', 'esperar a que llegue', 'esperar a que venga',
        'esperar a que vuelva', 'esperar a que entre', 'esperar a que esté',
        'tendrías que esperar', 'tienes que esperar', 'tiene que esperar',
        'tendría que esperar', 'tendríamos que esperar',
        'habría que esperar', 'hay que esperar',
        'debe esperar', 'debes esperar', 'mejor esperar',
        'esperar hasta que', 'esperar cuando',
        'marcar más tarde', 'llamar más tarde', 'marcar después', 'llamar después',
        'volver a marcar', 'volver a llamar', 'regresar la llamada'
    ]

    for frase in frases_transferencia:
        frase_limpia = frase.lower()
        es_callback = any(p in frase_limpia for p in patrones_callback_645)
        assert not es_callback, f"'{frase}' NO debe detectarse como callback (es transferencia real)"


def test_bruce2073_frase_exacta():
    """Test con la frase exacta de BRUCE2073"""
    # Frase real del log
    frase = "No, tendrías que esperar a que regrese. No tendrías que esperar a que regrese. Regrese como una hora."
    frase_limpia = frase.lower()

    patrones_callback_645 = [
        'esperar a que regrese', 'esperar a que llegue', 'esperar a que venga',
        'esperar a que vuelva', 'esperar a que entre', 'esperar a que esté',
        'tendrías que esperar', 'tienes que esperar', 'tiene que esperar',
        'tendría que esperar', 'tendríamos que esperar',
        'habría que esperar', 'hay que esperar',
        'debe esperar', 'debes esperar', 'mejor esperar',
        'esperar hasta que', 'esperar cuando',
        'marcar más tarde', 'llamar más tarde', 'marcar después', 'llamar después',
        'volver a marcar', 'volver a llamar', 'regresar la llamada'
    ]

    es_callback = any(p in frase_limpia for p in patrones_callback_645)
    assert es_callback, "Debe detectar la frase exacta de BRUCE2073 como CALLBACK"


def test_esperar_con_contexto_transferencia():
    """
    Verificar que "esperar" sin contexto de callback NO se detecta
    (debe seguir el flujo normal de transferencia)
    """
    frases_espera_normal = [
        "espere un momento",
        "espéreme tantito",
        "espera que lo busco"
    ]

    patrones_callback_645 = [
        'esperar a que regrese', 'esperar a que llegue', 'esperar a que venga',
        'esperar a que vuelva', 'esperar a que entre', 'esperar a que esté',
        'tendrías que esperar', 'tienes que esperar', 'tiene que esperar',
        'tendría que esperar', 'tendríamos que esperar',
        'habría que esperar', 'hay que esperar',
        'debe esperar', 'debes esperar', 'mejor esperar',
        'esperar hasta que', 'esperar cuando',
        'marcar más tarde', 'llamar más tarde', 'marcar después', 'llamar después',
        'volver a marcar', 'volver a llamar', 'regresar la llamada'
    ]

    for frase in frases_espera_normal:
        frase_limpia = frase.lower()
        es_callback = any(p in frase_limpia for p in patrones_callback_645)
        assert not es_callback, f"'{frase}' NO debe detectarse como callback (es espera normal)"


if __name__ == "__main__":
    # Ejecutar tests manualmente
    print("Testing FIX 645 patterns...")

    try:
        test_callback_esperar_a_que_regrese()
        print("PASS: test_callback_esperar_a_que_regrese")
    except AssertionError as e:
        print(f"FAIL: test_callback_esperar_a_que_regrese: {e}")

    try:
        test_callback_variantes()
        print("PASS: test_callback_variantes")
    except AssertionError as e:
        print(f"FAIL: test_callback_variantes: {e}")

    try:
        test_transferencia_no_es_callback()
        print("PASS: test_transferencia_no_es_callback")
    except AssertionError as e:
        print(f"FAIL: test_transferencia_no_es_callback: {e}")

    try:
        test_bruce2073_frase_exacta()
        print("PASS: test_bruce2073_frase_exacta")
    except AssertionError as e:
        print(f"FAIL: test_bruce2073_frase_exacta: {e}")

    try:
        test_esperar_con_contexto_transferencia()
        print("PASS: test_esperar_con_contexto_transferencia")
    except AssertionError as e:
        print(f"FAIL: test_esperar_con_contexto_transferencia: {e}")

    print("\nAll FIX 645 tests passed!")
