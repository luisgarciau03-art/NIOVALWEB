"""
Tests de regresión para FIX 647: BRUCE2098 - Cliente NO AUTORIZADO

Problema: Cliente dijo "NO ESTABA AUTORIZADO" para dar número del encargado
→ Bruce pidió el número directo en turno 4 (GPT_LOGICA_ROTA)

Solución: Agregar 4ta regla a FIX 646A system prompt:
"Si cliente dice NO AUTORIZADO/NO PUEDE/NO LE PERMITEN dar información → NO insistir"
"""

import pytest
from agente_ventas import AgenteVentas


class TestFix647ClienteNoAutorizado:
    """Verificar que FIX 647 agregó la 4ta regla anti-repetición"""

    def test_fix_647_regla_no_autorizado_en_codigo(self):
        """Verificar que la regla NO AUTORIZADO está presente en el código"""
        import inspect

        # Obtener source code del método procesar_respuesta
        source = inspect.getsource(AgenteVentas.procesar_respuesta)

        # Verificar que existe la 4ta regla
        assert "4." in source, "Debe existir la regla #4 en FIX 646A/647"
        assert "NO ESTÁ AUTORIZADO" in source.upper(), "Debe mencionar NO AUTORIZADO"
        assert "NO PUEDE" in source.upper(), "Debe mencionar NO PUEDE"
        assert "NO LE PERMITEN" in source.upper(), "Debe mencionar NO LE PERMITEN"
        assert "NO insistir" in source, "Debe indicar NO insistir cuando cliente no está autorizado"

        # Verificar que se menciona FIX 647
        assert "FIX 647" in source, "Debe documentar FIX 647: BRUCE2098"
        assert "BRUCE2098" in source, "Debe referenciar el bug BRUCE2098"

    def test_fix_647_integrado_con_fix_646a(self):
        """Verificar que FIX 647 está integrado en el mismo bloque que FIX 646A"""
        import inspect

        source = inspect.getsource(AgenteVentas.procesar_respuesta)

        # Buscar el bloque de reglas_anti_repeticion_646
        assert "reglas_anti_repeticion_646" in source, "Debe existir el dict de reglas"
        assert "[SISTEMA - FIX 646A/647]" in source, "Debe mencionar ambos FIX en el header"

        # Verificar que tiene las 4 reglas
        lines = source.split('\n')
        reglas_section = '\n'.join([l for l in lines if 'REGLAS CRÍTICAS' in l or l.strip().startswith(('1.', '2.', '3.', '4.'))])

        assert "1." in reglas_section, "Debe tener regla #1"
        assert "2." in reglas_section, "Debe tener regla #2"
        assert "3." in reglas_section, "Debe tener regla #3"
        assert "4." in reglas_section, "Debe tener regla #4 (FIX 647)"


class TestFix647ContextoConversacional:
    """Tests de contexto conversacional para NO AUTORIZADO"""

    def test_cliente_no_autorizado_no_deberia_generar_loop(self):
        """Verificar que el sistema tiene la regla para evitar loops cuando cliente no está autorizado"""
        # Este test verifica que la lógica existe, pero el comportamiento real
        # se validará con llamadas de prueba en producción

        from agente_ventas import AgenteVentas
        import inspect

        source = inspect.getsource(AgenteVentas.procesar_respuesta)

        # Verificar que existe protección contra insistir cuando no autorizado
        frases_prohibidas = [
            "NO ESTÁ AUTORIZADO",
            "NO PUEDE",
            "NO LE PERMITEN"
        ]

        # Al menos una de estas frases debe estar en la regla
        tiene_proteccion = any(frase in source.upper() for frase in frases_prohibidas)
        assert tiene_proteccion, "Debe tener protección contra insistir cuando cliente no está autorizado"

    def test_fix_647_sugiere_alternativa(self):
        """Verificar que FIX 647 sugiere alternativa cuando cliente no está autorizado"""
        import inspect

        source = inspect.getsource(AgenteVentas.procesar_respuesta)

        # La regla debe sugerir alternativas
        assert any(palabra in source.lower() for palabra in ["ofrecer", "enviar catálogo", "callback"]), \
            "Debe sugerir alternativa cuando cliente no está autorizado (enviar catálogo/callback)"


class TestFix647DocumentacionYReferencias:
    """Verificar documentación y referencias del fix"""

    def test_fix_647_documenta_bug_original(self):
        """Verificar que FIX 647 documenta el bug BRUCE2098 que lo originó"""
        import inspect

        source = inspect.getsource(AgenteVentas.procesar_respuesta)

        # Debe documentar el bug que se está corrigiendo
        assert "BRUCE2098" in source, "Debe referenciar BRUCE2098 como origen del fix"

    def test_fix_647_mantiene_compatibilidad_fix_646a(self):
        """Verificar que FIX 647 no rompe las 3 reglas originales de FIX 646A"""
        import inspect

        source = inspect.getsource(AgenteVentas.procesar_respuesta)

        # Las 3 reglas originales deben seguir presentes
        reglas_646a = [
            "encargado NO ESTÁ",
            "dato YA está capturado",
            "Dígame"
        ]

        for regla in reglas_646a:
            assert regla in source, f"FIX 647 debe mantener regla original: {regla}"
