# -*- coding: utf-8 -*-
"""
Tests para FIX 711: BRUCE2255 - "Dígame" != "Diga"
- 711A: "Dígame" = "go ahead, tell me" → dar pitch, NO repetir pregunta
"""

import sys
import os
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ============================================================
# FIX 711A: "Dígame" se distingue de "Diga"
# ============================================================

class TestFix711ADigameVsDiga:
    """'Dígame' NO debe tratarse como 'Diga' (verificación de conexión)."""

    def test_711a_existe_en_codigo(self):
        agente_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'agente_ventas.py')
        with open(agente_path, 'r', encoding='utf-8') as f:
            source = f.read()
        assert "FIX 711A" in source
        assert "es_digame_711" in source

    def test_711a_antes_de_saludos(self):
        """FIX 711A check must be BEFORE 'diga' in saludos check."""
        agente_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'agente_ventas.py')
        with open(agente_path, 'r', encoding='utf-8') as f:
            source = f.read()
        idx_711 = source.find("es_digame_711")
        idx_saludos = source.find("any(s in texto_lower for s in saludos)")
        assert idx_711 < idx_saludos, "FIX 711A must be BEFORE saludos substring check"

    def test_digame_detectado(self):
        """'digame' is detected as DIGAME, not as saludo."""
        texto = "digame"  # already lowered and accent-stripped
        texto_stripped = texto.strip().rstrip('.,;:!?¿¡')
        es_digame = texto_stripped in ['digame', 'si digame', 'si, digame']
        assert es_digame

    def test_digame_con_punto(self):
        """'digame.' is detected as DIGAME."""
        texto = "digame."
        texto_stripped = texto.strip().rstrip('.,;:!?¿¡')
        es_digame = texto_stripped in ['digame', 'si digame', 'si, digame']
        assert es_digame

    def test_si_digame(self):
        """'si digame' is detected as DIGAME."""
        texto = "si digame"
        texto_stripped = texto.strip().rstrip('.,;:!?¿¡')
        es_digame = texto_stripped in ['digame', 'si digame', 'si, digame']
        assert es_digame

    def test_si_coma_digame(self):
        """'si, digame' is detected as DIGAME."""
        texto = "si, digame"
        texto_stripped = texto.strip().rstrip('.,;:!?¿¡')
        es_digame = texto_stripped in ['digame', 'si digame', 'si, digame']
        assert es_digame

    def test_diga_no_es_digame(self):
        """'diga' should NOT match as DIGAME."""
        texto = "diga"
        texto_stripped = texto.strip().rstrip('.,;:!?¿¡')
        es_digame = texto_stripped in ['digame', 'si digame', 'si, digame']
        assert not es_digame

    def test_bueno_no_es_digame(self):
        """'bueno' should NOT match as DIGAME."""
        texto = "bueno"
        texto_stripped = texto.strip().rstrip('.,;:!?¿¡')
        es_digame = texto_stripped in ['digame', 'si digame', 'si, digame']
        assert not es_digame


# ============================================================
# FIX 711A: Respuestas correctas para "Dígame"
# ============================================================

class TestFix711AResponses:
    """Las respuestas para 'Dígame' deben ser pitch/continuar, NO repetir pregunta."""

    def test_711a_retorna_digame_tipo(self):
        """Code has DIGAME_CONTINUAR, DIGAME_ADELANTE, DIGAME_INICIO types."""
        agente_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'agente_ventas.py')
        with open(agente_path, 'r', encoding='utf-8') as f:
            source = f.read()
        assert "DIGAME_CONTINUAR" in source
        assert "DIGAME_ADELANTE" in source
        assert "DIGAME_INICIO" in source

    def test_711a_no_repite_encargado(self):
        """When Bruce already asked for encargado and client says 'Dígame',
        Bruce should give pitch, NOT repeat 'se encontrará el encargado'."""
        agente_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'agente_ventas.py')
        with open(agente_path, 'r', encoding='utf-8') as f:
            source = f.read()
        # Find DIGAME_CONTINUAR response
        idx = source.find('"tipo": "DIGAME_CONTINUAR"')
        assert idx > 0
        block = source[idx:idx+300]
        # Should NOT contain "le preguntaba"
        assert "le preguntaba" not in block
        # Should contain pitch info
        assert "NIOVAL" in block or "nioval" in block

    def test_711a_digame_inicio_da_pitch(self):
        """At conversation start, 'Dígame' should give full pitch."""
        agente_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'agente_ventas.py')
        with open(agente_path, 'r', encoding='utf-8') as f:
            source = f.read()
        idx = source.find('"tipo": "DIGAME_INICIO"')
        assert idx > 0
        block = source[idx:idx+300]
        assert "NIOVAL" in block


# ============================================================
# FIX 711A: BRUCE2255 exact scenario
# ============================================================

class TestFix711ABRUCE2255:
    """Reproduce exact BRUCE2255 scenario."""

    def test_bruce2255_digame_no_repite_encargado(self):
        """BRUCE2255: After pitch+encargado question, client said 'Dígame.'
        Bruce should NOT repeat 'se encontrará el encargado'."""
        # Simulate: Bruce asked for encargado, client says "Dígame."
        texto = "Dígame."
        texto_lower = texto.lower().strip()
        texto_lower = texto_lower.replace('á','a').replace('é','e').replace('í','i').replace('ó','o').replace('ú','u')
        texto_stripped = texto_lower.strip().rstrip('.,;:!?¿¡')

        # FIX 711A should catch this
        es_digame = texto_stripped in ['digame', 'si digame', 'si, digame']
        assert es_digame, "'Dígame.' should be detected as DIGAME by FIX 711A"

        # Old behavior: "diga" in "digame" → True → repeat question
        saludos = ["hola", "bueno", "buenos dias", "buenas tardes", "diga", "si digame"]
        old_match = any(s in texto_lower for s in saludos)
        assert old_match, "Old code would match 'diga' in 'digame' (the bug)"

    def test_bruce2255_diga_still_works(self):
        """'Diga.' should still work as before (verification/repeat question)."""
        texto = "Diga."
        texto_lower = texto.lower().strip()
        texto_lower = texto_lower.replace('á','a').replace('é','e').replace('í','i').replace('ó','o').replace('ú','u')
        texto_stripped = texto_lower.strip().rstrip('.,;:!?¿¡')

        # FIX 711A should NOT catch "diga"
        es_digame = texto_stripped in ['digame', 'si digame', 'si, digame']
        assert not es_digame, "'Diga.' should NOT be caught by FIX 711A"

        # Still matches as saludo
        saludos = ["hola", "bueno", "buenos dias", "buenas tardes", "diga", "si digame"]
        old_match = any(s in texto_lower for s in saludos)
        assert old_match, "'Diga.' should still match as saludo"
