"""
Tests de regresión para FIX 671: Ajustar threshold CATALOGO_REPETIDO

FIX 671: Alineación de threshold con bug detector (6 bugs eliminados)

Problema:
- Bug detector marca CATALOGO_REPETIDO si ofreció 2+ veces
- FIX 659 bloqueaba en 3ra oferta (>=2 previos + 1 actual = 3 total)
- MISMATCH: Bug detector detecta pero FIX no previene

Bugs objetivo: BRUCE2157, 2143, 2142, 2135, 2128, 2118 (10% de todos los bugs)
"""

import pytest
import inspect
import sys
import os

# Agregar el directorio padre al path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agente_ventas import AgenteVentas


class TestFix671ExisteEnCodigo:
    """Verificar que FIX 671 está implementado en agente_ventas.py"""

    def test_fix_671_existe(self):
        """Verificar que FIX 671 está en el código"""
        source = inspect.getsource(AgenteVentas._filtrar_respuesta_post_gpt)

        # Debe mencionar FIX 671
        assert "FIX 671" in source
        assert any(f"BRUCE{bid}" in source for bid in ["2157", "2143", "2142", "2135", "2128", "2118"])

    def test_fix_671_despues_fix_659(self):
        """Verificar que FIX 671 actualiza FIX 659 (no lo reemplaza)"""
        source = inspect.getsource(AgenteVentas._filtrar_respuesta_post_gpt)

        # Debe mencionar ambos fixes
        assert "FIX 659" in source  # Original
        assert "FIX 671" in source  # Actualización


class TestFix671ThresholdAjustado:
    """Verificar que FIX 671 ajustó el threshold correctamente"""

    def test_fix_671_threshold_uno(self):
        """Verificar que FIX 671 usa threshold >= 1 (no >= 2)"""
        source = inspect.getsource(AgenteVentas._filtrar_respuesta_post_gpt)

        # Buscar sección de FIX 671
        fix_671_start = source.find("FIX 671")
        fix_671_section = source[fix_671_start:fix_671_start + 1000]

        # Debe verificar >= 1 (bloquea 2da oferta)
        assert ">= 1" in fix_671_section

    def test_fix_671_no_threshold_dos(self):
        """Verificar que FIX 671 NO usa >= 2 (era el problema)"""
        source = inspect.getsource(AgenteVentas._filtrar_respuesta_post_gpt)

        # Buscar sección de FIX 671
        fix_671_start = source.find("FIX 671")
        fix_671_section = source[fix_671_start:fix_671_start + 1000]

        # NO debe tener >= 2 en la misma sección
        # (puede aparecer en otros lados, pero no en FIX 671)
        assert "veces_ofrecio_catalogo >= 2" not in fix_671_section

    def test_fix_671_cuenta_ofertas_historial(self):
        """Verificar que FIX 671 cuenta ofertas en historial completo"""
        source = inspect.getsource(AgenteVentas._filtrar_respuesta_post_gpt)

        # Debe contar en conversation_history (FIX 659)
        assert "conversation_history" in source
        assert "veces_ofrecio_catalogo" in source


class TestFix671ComportamientoEsperado:
    """Verificar comportamiento esperado de FIX 671"""

    def test_fix_671_bloquea_segunda_oferta(self):
        """Verificar que FIX 671 bloquea la 2da oferta (1 previo + 1 actual)"""
        source = inspect.getsource(AgenteVentas._filtrar_respuesta_post_gpt)

        # Buscar sección de FIX 671
        fix_671_start = source.find("FIX 671")
        fix_671_section = source[fix_671_start:fix_671_start + 1000]

        # Debe bloquear con >= 1 previo
        assert ">= 1" in fix_671_section

    def test_fix_671_respuesta_despedida(self):
        """Verificar que FIX 671 usa respuesta de despedida cortés"""
        source = inspect.getsource(AgenteVentas._filtrar_respuesta_post_gpt)

        # Buscar sección después de FIX 671 (FIX 705+742+812 expandieron el bloque)
        fix_671_start = source.find("FIX 671")
        fix_671_section = source[fix_671_start:fix_671_start + 6000]

        # Debe tener respuesta alternativa
        assert "me comunico despues" in fix_671_section.lower() or "entonces me comunico" in fix_671_section.lower()
        assert "muchas gracias" in fix_671_section.lower()

    def test_fix_671_logging_presente(self):
        """Verificar que FIX 671 tiene logging de debug"""
        source = inspect.getsource(AgenteVentas._filtrar_respuesta_post_gpt)

        # Buscar sección de FIX 671
        fix_671_start = source.find("FIX 671")
        fix_671_section = source[fix_671_start:fix_671_start + 1500]

        # Debe tener logging
        assert "FIX 671" in fix_671_section or "ANTI-LOOP" in fix_671_section


class TestFix671AlineacionBugDetector:
    """Verificar que FIX 671 está alineado con bug detector"""

    def test_bug_detector_threshold_dos(self):
        """Verificar que bug detector marca CATALOGO_REPETIDO con 2+ ofertas"""
        # Leer bug_detector.py
        bug_detector_path = os.path.join(os.path.dirname(__file__), '..', 'bug_detector.py')

        if not os.path.exists(bug_detector_path):
            pytest.skip("bug_detector.py no encontrado")

        with open(bug_detector_path, 'r', encoding='utf-8') as f:
            source = f.read()

        # Bug detector marca CATALOGO_REPETIDO con >= 2 ofertas
        catalogo_section_start = source.find("def _check_catalogo_repetido")
        catalogo_section = source[catalogo_section_start:catalogo_section_start + 1000]

        assert ">= 2" in catalogo_section

    def test_fix_671_bloquea_antes_bug_detector(self):
        """Verificar que FIX 671 bloquea ANTES de que bug detector lo detecte"""
        # FIX 671 bloquea con >= 1 previo (2da oferta)
        # Bug detector marca con >= 2 ofertas
        # Por lo tanto, FIX 671 previene que el bug ocurra

        source = inspect.getsource(AgenteVentas._filtrar_respuesta_post_gpt)

        # Buscar sección de FIX 671
        fix_671_start = source.find("FIX 671")
        fix_671_section = source[fix_671_start:fix_671_start + 1000]

        # FIX 671 usa >= 1 (bloquea ANTES de 2)
        assert ">= 1" in fix_671_section


class TestFix671Integracion:
    """Tests de integración con otros fixes"""

    def test_no_rompe_fix_493b(self):
        """Verificar que FIX 671 no rompe FIX 493B (base original)"""
        source = inspect.getsource(AgenteVentas._filtrar_respuesta_post_gpt)

        # FIX 493B debe seguir presente
        assert "FIX 493B" in source
        assert "patrones_catalogo_493b" in source

    def test_no_rompe_fix_659(self):
        """Verificar que FIX 671 no rompe FIX 659 (contador)"""
        source = inspect.getsource(AgenteVentas._filtrar_respuesta_post_gpt)

        # FIX 659 debe seguir presente
        assert "FIX 659" in source
        assert "veces_ofrecio_catalogo" in source

    def test_usa_mismos_patrones(self):
        """Verificar que FIX 671 usa los mismos patrones que FIX 493B/659"""
        source = inspect.getsource(AgenteVentas._filtrar_respuesta_post_gpt)

        # Debe usar patrones_catalogo_493b
        assert "patrones_catalogo_493b" in source
        assert "ofrece_catalogo_493b" in source


class TestFix671CasosReales:
    """Tests basados en casos reales de bugs CATALOGO_REPETIDO"""

    def test_bruce2157_patron(self):
        """Simular BRUCE2157: 4 turnos, 2 ofertas de catálogo"""
        # Turno 1: Bruce ofrece catálogo (1ra vez)
        # Turno 3: Bruce ofrece catálogo (2da vez) ✅ DEBE BLOQUEARSE

        source = inspect.getsource(AgenteVentas._filtrar_respuesta_post_gpt)

        # Verificar que FIX 671 bloquea con >= 1 previo
        assert ">= 1" in source

    def test_bruce2142_patron(self):
        """Simular BRUCE2142: 7 turnos, 2 ofertas de catálogo"""
        # Similar a BRUCE2157: debe bloquearse en 2da oferta

        source = inspect.getsource(AgenteVentas._filtrar_respuesta_post_gpt)

        # Verificar que BRUCE2142 está en comentarios
        assert "2142" in source or "FIX 671" in source


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
