"""
Tests de regresión para FIX 646 - Bugs detectados 2026-02-11
Análisis de 13 bugs: 69% GPT_LOGICA_ROTA, pattern audit con 0% survival
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


def test_fix_646b_ya_todo_despedida():
    """FIX 646B: BRUCE2080 - "Ya todo" debe detectarse como despedida"""
    from agente_ventas import AgenteVentas

    agente = AgenteVentas()

    # Simular que cliente dice "Ya todo"
    result = agente._detectar_patron_simple_optimizado("Ya todo")

    assert result is not None, "Debe detectar 'Ya todo'"
    assert result["tipo"] == "DESPEDIDA_CLIENTE", f"Debe ser DESPEDIDA_CLIENTE, fue {result['tipo']}"


def test_fix_646b_ya_esta_todo_despedida():
    """FIX 646B: Variante 'Ya está todo' también despedida"""
    from agente_ventas import AgenteVentas

    agente = AgenteVentas()

    result = agente._detectar_patron_simple_optimizado("Ya está todo")

    assert result is not None
    assert result["tipo"] == "DESPEDIDA_CLIENTE"


def test_fix_646b_ya_es_todo_despedida():
    """FIX 646B: Variante 'Ya es todo' también despedida"""
    from agente_ventas import AgenteVentas

    agente = AgenteVentas()

    result = agente._detectar_patron_simple_optimizado("Ya es todo")

    assert result is not None
    assert result["tipo"] == "DESPEDIDA_CLIENTE"


def test_fix_646d_evitar_loop_whatsapp_inmune_601():
    """FIX 646D: EVITAR_LOOP_WHATSAPP debe ser inmune a FIX 601"""
    # Verificar que está en la lista de inmunidad
    from agente_ventas import AgenteVentas
    import re

    # Leer el código fuente para verificar
    with open('agente_ventas.py', 'r', encoding='utf-8') as f:
        code = f.read()

    # FASE 1.1: patrones_inmunes_601 ahora usa _PATRONES_INMUNES_UNIVERSAL
    # Verificar que el set universal contiene los patrones requeridos
    pattern = r"_PATRONES_INMUNES_UNIVERSAL\s*=\s*\{([^}]+)\}"
    match = re.search(pattern, code, re.DOTALL)

    assert match is not None, "Debe existir _PATRONES_INMUNES_UNIVERSAL"

    inmunes = match.group(1)
    assert "'EVITAR_LOOP_WHATSAPP'" in inmunes, "EVITAR_LOOP_WHATSAPP debe estar en inmunes universal"
    assert "'CLIENTE_ACEPTA_CORREO'" in inmunes, "CLIENTE_ACEPTA_CORREO debe estar en inmunes universal"
    # Verificar que 601 usa el set universal
    assert "patrones_inmunes_601 = _PATRONES_INMUNES_UNIVERSAL" in code, "601 debe usar set universal"


def test_fix_646a_reglas_anti_repeticion_en_codigo():
    """FIX 646A: Verificar que reglas anti-repetición están en el código"""
    with open('agente_ventas.py', 'r', encoding='utf-8') as f:
        code = f.read()

    # Buscar FIX 646A
    assert "FIX 646A" in code, "Debe existir FIX 646A en el código"
    assert "REGLAS CRÍTICAS ANTI-REPETICIÓN" in code or "REGLAS CRITICAS ANTI-REPETICION" in code, \
        "Debe tener sección de reglas anti-repetición"
    assert "encargado NO ESTÁ" in code or "encargado NO ESTA" in code, \
        "Debe tener regla sobre encargado no está"
    assert "ya proporcionó un dato" in code or "ya proporciono un dato" in code, \
        "Debe tener regla sobre datos ya proporcionados"


def test_fix_646e_gpt_eval_conteo_turnos():
    """FIX 646E: GPT eval debe tener instrucciones de conteo de turnos"""
    with open('bug_detector.py', 'r', encoding='utf-8') as f:
        code = f.read()

    # Buscar FIX 646E y instrucciones de conteo
    assert "FIX 646E" in code, "Debe existir FIX 646E en bug_detector.py"
    assert "CONTEO DE TURNOS" in code, "Debe tener sección CONTEO DE TURNOS"
    assert "cuenta SOLO los mensajes de Bruce" in code, "Debe instruir contar solo mensajes de Bruce"
    assert "NO cuentes mensajes del CLIENTE" in code, "Debe instruir NO contar mensajes del cliente"


def test_patron_inmune_sobrevive_fix_601():
    """Verificar que patrones inmunes NO son invalidados por FIX 601"""
    from agente_ventas import AgenteVentas

    agente = AgenteVentas()
    # Simular que ya se prometió catálogo (permite despedidas largas)
    agente.catalogo_prometido = True

    # Texto largo complejo que normalmente sería invalidado
    texto = "Ya todo gracias por la información me parece muy bien entonces quedo a la espera del catálogo que me va a enviar"

    # Detectar patrón
    result = agente._detectar_patron_simple_optimizado(texto)

    # Debe detectar DESPEDIDA_CLIENTE
    assert result is not None, "Debe detectar despedida aunque sea texto largo"
    assert result["tipo"] == "DESPEDIDA_CLIENTE", "Debe ser DESPEDIDA_CLIENTE"

    # DESPEDIDA_CLIENTE está en patrones_inmunes_601, no debe ser invalidado


if __name__ == "__main__":
    # Ejecutar tests manualmente
    print("Testing FIX 646 patterns...")

    try:
        test_fix_646b_ya_todo_despedida()
        print("PASS: test_fix_646b_ya_todo_despedida")
    except AssertionError as e:
        print(f"FAIL: test_fix_646b_ya_todo_despedida: {e}")

    try:
        test_fix_646b_ya_esta_todo_despedida()
        print("PASS: test_fix_646b_ya_esta_todo_despedida")
    except AssertionError as e:
        print(f"FAIL: test_fix_646b_ya_esta_todo_despedida: {e}")

    try:
        test_fix_646b_ya_es_todo_despedida()
        print("PASS: test_fix_646b_ya_es_todo_despedida")
    except AssertionError as e:
        print(f"FAIL: test_fix_646b_ya_es_todo_despedida: {e}")

    try:
        test_fix_646d_evitar_loop_whatsapp_inmune_601()
        print("PASS: test_fix_646d_evitar_loop_whatsapp_inmune_601")
    except AssertionError as e:
        print(f"FAIL: test_fix_646d_evitar_loop_whatsapp_inmune_601: {e}")

    try:
        test_fix_646a_reglas_anti_repeticion_en_codigo()
        print("PASS: test_fix_646a_reglas_anti_repeticion_en_codigo")
    except AssertionError as e:
        print(f"FAIL: test_fix_646a_reglas_anti_repeticion_en_codigo: {e}")

    try:
        test_fix_646e_gpt_eval_conteo_turnos()
        print("PASS: test_fix_646e_gpt_eval_conteo_turnos")
    except AssertionError as e:
        print(f"FAIL: test_fix_646e_gpt_eval_conteo_turnos: {e}")

    try:
        test_patron_inmune_sobrevive_fix_601()
        print("PASS: test_patron_inmune_sobrevive_fix_601")
    except AssertionError as e:
        print(f"FAIL: test_patron_inmune_sobrevive_fix_601: {e}")

    print("\nAll FIX 646 tests completed!")
