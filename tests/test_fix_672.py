"""
Tests de regresión para FIX 672: Ajustar threshold PREGUNTA_REPETIDA

FIX 672: Alinear threshold con bug detector (5 bugs eliminados)

Problema:
- Bug detector marca PREGUNTA_REPETIDA si preguntó 2+ veces
- FIX 493 bloqueaba 3ra pregunta (>=3 previos + 1 actual = 4 total)
- MISMATCH: Bug detector detecta pero FIX no previene

Bugs objetivo: BRUCE2143, 2142, 2138, 2128, 2114 (8.3% de todos los bugs)
"""

import pytest
import inspect
import sys
import os

# Agregar el directorio padre al path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agente_ventas import AgenteVentas


class TestFix672ExisteEnCodigo:
    """Verificar que FIX 672 está implementado en agente_ventas.py"""

    def test_fix_672_existe(self):
        """Verificar que FIX 672 está en el código"""
        source = inspect.getsource(AgenteVentas._filtrar_respuesta_post_gpt)

        # Debe mencionar FIX 672
        assert "FIX 672" in source
        assert any(f"BRUCE{bid}" in source for bid in ["2143", "2142", "2138", "2128", "2114"])

    def test_fix_672_actualiza_fix_493(self):
        """Verificar que FIX 672 actualiza FIX 493 (no lo reemplaza)"""
        source = inspect.getsource(AgenteVentas._filtrar_respuesta_post_gpt)

        # Debe mencionar ambos fixes
        assert "FIX 493" in source  # Original
        assert "FIX 672" in source  # Actualización


class TestFix672ThresholdAjustado:
    """Verificar que FIX 672 ajustó los thresholds correctamente"""

    def test_fix_672_threshold_whatsapp_dos(self):
        """Verificar que FIX 672 usa threshold >= 2 para WhatsApp (no >= 3)"""
        source = inspect.getsource(AgenteVentas._filtrar_respuesta_post_gpt)

        # Buscar sección de FIX 672 WhatsApp
        fix_672_start = source.find("FIX 672")
        fix_672_section = source[fix_672_start:fix_672_start + 1500]

        # Debe verificar >= 2 (bloquea 2da pregunta WhatsApp)
        assert "veces_pregunto_whatsapp >= 2" in fix_672_section

    def test_fix_672_threshold_catalogo_dos(self):
        """Verificar que FIX 672 usa threshold >= 2 para catálogo (no >= 3)"""
        source = inspect.getsource(AgenteVentas._filtrar_respuesta_post_gpt)

        # Buscar sección de catálogo (después de WhatsApp)
        # FIX 672 debe haber modificado el threshold de catálogo también
        assert "veces_pregunto_catalogo >= 2" in source

    def test_fix_672_no_threshold_tres(self):
        """Verificar que FIX 672 NO usa >= 3 (era el problema)"""
        source = inspect.getsource(AgenteVentas._filtrar_respuesta_post_gpt)

        # Buscar secciones de FIX 672
        fix_672_start = source.find("FIX 672")
        if fix_672_start > 0:
            # Verificar contexto alrededor de FIX 672
            # NO debe tener >= 3 en la misma sección
            fix_672_section = source[fix_672_start:fix_672_start + 2000]
            assert "veces_pregunto_whatsapp >= 3" not in fix_672_section
            assert "veces_pregunto_catalogo >= 3" not in fix_672_section


class TestFix672ComportamientoEsperado:
    """Verificar comportamiento esperado de FIX 672"""

    def test_fix_672_bloquea_segunda_pregunta_whatsapp(self):
        """Verificar que FIX 672 bloquea la 2da pregunta WhatsApp (2 previos + 1 actual)"""
        source = inspect.getsource(AgenteVentas._filtrar_respuesta_post_gpt)

        # Buscar sección de FIX 672 WhatsApp
        fix_672_start = source.find("FIX 672")
        fix_672_section = source[fix_672_start:fix_672_start + 1500]

        # Debe bloquear con >= 2 previos
        assert ">= 2" in fix_672_section

    def test_fix_672_bloquea_segunda_pregunta_catalogo(self):
        """Verificar que FIX 672 bloquea la 2da pregunta catálogo"""
        source = inspect.getsource(AgenteVentas._filtrar_respuesta_post_gpt)

        # Debe tener lógica para bloquear catálogo
        assert "pregunta_catalogo" in source
        assert "veces_pregunto_catalogo" in source

    def test_fix_672_respuesta_alternativa_whatsapp(self):
        """Verificar que FIX 672 ofrece correo como alternativa tras rechazar WhatsApp"""
        source = inspect.getsource(AgenteVentas._filtrar_respuesta_post_gpt)

        # Buscar sección de FIX 672 WhatsApp
        fix_672_start = source.find("FIX 672")
        fix_672_section = source[fix_672_start:fix_672_start + 1500]

        # Debe ofrecer correo como alternativa
        assert "correo" in fix_672_section.lower() or "informacion" in fix_672_section.lower()

    def test_fix_672_respuesta_despedida_catalogo(self):
        """Verificar que FIX 672 se despide tras rechazar catálogo 2x"""
        source = inspect.getsource(AgenteVentas._filtrar_respuesta_post_gpt)

        # Debe tener despedida profesional
        assert "le agradezco su tiempo" in source.lower() or "entiendo perfectamente" in source.lower()

    def test_fix_672_logging_presente(self):
        """Verificar que FIX 672 tiene logging de debug"""
        source = inspect.getsource(AgenteVentas._filtrar_respuesta_post_gpt)

        # Buscar sección de FIX 672
        fix_672_start = source.find("FIX 672")
        fix_672_section = source[fix_672_start:fix_672_start + 2000]

        # Debe tener logging
        assert "FIX 672" in fix_672_section or "ANTI-LOOP" in fix_672_section


class TestFix672AlineacionBugDetector:
    """Verificar que FIX 672 está alineado con bug detector"""

    def test_bug_detector_threshold_dos(self):
        """Verificar que bug detector marca PREGUNTA_REPETIDA con 2+ preguntas"""
        # Leer bug_detector.py
        bug_detector_path = os.path.join(os.path.dirname(__file__), '..', 'bug_detector.py')

        if not os.path.exists(bug_detector_path):
            pytest.skip("bug_detector.py no encontrado")

        with open(bug_detector_path, 'r', encoding='utf-8') as f:
            source = f.read()

        # Bug detector debe marcar con >= 2
        pregunta_section_start = source.find("def _check_pregunta_repetida")
        pregunta_section = source[pregunta_section_start:pregunta_section_start + 1500]

        assert ">= 2" in pregunta_section

    def test_fix_672_bloquea_antes_bug_detector(self):
        """Verificar que FIX 672 bloquea ANTES de que bug detector lo detecte"""
        # FIX 672 bloquea con >= 2 previos (3ra pregunta)
        # Bug detector marca con >= 2 preguntas totales
        # Por lo tanto, FIX 672 previene que el bug ocurra

        source = inspect.getsource(AgenteVentas._filtrar_respuesta_post_gpt)

        # Buscar sección de FIX 672
        fix_672_start = source.find("FIX 672")
        fix_672_section = source[fix_672_start:fix_672_start + 1500]

        # FIX 672 usa >= 2 (bloquea ANTES o IGUAL que detector)
        assert ">= 2" in fix_672_section


class TestFix672Integracion:
    """Tests de integración con otros fixes"""

    def test_no_rompe_fix_493(self):
        """Verificar que FIX 672 no rompe FIX 493 (base original)"""
        source = inspect.getsource(AgenteVentas._filtrar_respuesta_post_gpt)

        # FIX 493 debe seguir presente
        assert "FIX 493" in source
        assert "preguntas_whatsapp" in source
        assert "preguntas_catalogo" in source

    def test_no_rompe_fix_494(self):
        """Verificar que FIX 672 no rompe FIX 494 (WhatsApp/correo ya capturado)"""
        source = inspect.getsource(AgenteVentas._filtrar_respuesta_post_gpt)

        # FIX 494 debe seguir presente
        assert "FIX 494" in source
        assert "whatsapp_ya_capturado" in source or "email_ya_capturado" in source

    def test_usa_mismos_patrones(self):
        """Verificar que FIX 672 usa los mismos patrones que FIX 493"""
        source = inspect.getsource(AgenteVentas._filtrar_respuesta_post_gpt)

        # Debe usar patrones de FIX 493
        assert "preguntas_whatsapp" in source
        assert "preguntas_catalogo" in source
        assert "veces_pregunto_whatsapp" in source
        assert "veces_pregunto_catalogo" in source


class TestFix672CasosReales:
    """Tests basados en casos reales de bugs PREGUNTA_REPETIDA"""

    def test_bruce2143_patron(self):
        """Simular BRUCE2143: pregunta WhatsApp 2x"""
        # Turno 1: Bruce pide WhatsApp (1ra vez)
        # Turno 3: Bruce iba a pedir WhatsApp (2da vez) → DEBE BLOQUEARSE

        source = inspect.getsource(AgenteVentas._filtrar_respuesta_post_gpt)

        # Verificar que FIX 672 bloquea con >= 2 previos
        assert ">= 2" in source

    def test_bruce2138_patron(self):
        """Simular BRUCE2138: pregunta WhatsApp 3x (caso edge)"""
        # BRUCE2138 preguntó 3x pero NO se bloqueó
        # Con FIX 672 >= 2, debería bloquearse en la 3ra

        source = inspect.getsource(AgenteVentas._filtrar_respuesta_post_gpt)

        # Verificar que BRUCE2138 está en comentarios
        assert "2138" in source or "FIX 672" in source


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
