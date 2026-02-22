"""
Tests FIX 756-757:
- FIX 756: BRUCE2425 - Cliente ofrece dato pero GPT timeout → "me puede repetir" → override aceptar
- FIX 757: Pattern audit 0% survival → ESPERANDO_QUE_ANOTE, TIENDA_CERRADA inmunes
"""

import unittest
import os
import sys
import re

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


# ============================================================
# FIX 756: Oferta de dato en GPT timeout path
# ============================================================

class TestFix756OfertaDatoTimeout(unittest.TestCase):
    """FIX 756: Detectar oferta de dato en FIX 682 GPT timeout fallback."""

    def setUp(self):
        """Load servidor source to verify patterns exist."""
        srv_path = os.path.join(os.path.dirname(__file__), '..', 'servidor_llamadas.py')
        with open(srv_path, 'r', encoding='utf-8') as f:
            self.servidor_source = f.read()

    def test_fix_756_exists_path_a(self):
        """FIX 756 exists in first timeout path (path A)."""
        self.assertIn('FIX 756: BRUCE2425', self.servidor_source)
        self.assertIn("FIX 756: Cliente ofrece correo en timeout", self.servidor_source)

    def test_fix_756_exists_path_b(self):
        """FIX 756 exists in second timeout path (path B)."""
        self.assertIn("FIX 756: Cliente ofrece correo en timeout → aceptar (path B)", self.servidor_source)

    def test_fix_756_patterns_correo(self):
        """FIX 756 detects correo offers in timeout."""
        patterns = [
            'te puedo proporcionar', 'le puedo proporcionar',
            'te paso el correo', 'le paso el correo',
            'te doy el correo', 'le doy el correo',
            'por correo mejor', 'mejor por correo',
        ]
        for p in patterns:
            self.assertIn(p, self.servidor_source, f"Pattern '{p}' missing in FIX 756")

    def test_fix_756_patterns_whatsapp(self):
        """FIX 756 detects WhatsApp offers in timeout."""
        self.assertIn("'whatsapp', 'wats', 'guats'", self.servidor_source)

    def test_fix_756_patterns_generic(self):
        """FIX 756 detects generic data offers in timeout."""
        patterns = [
            'te paso un', 'le paso un',
            'te puedo dar', 'le puedo dar',
            'te puedo pasar', 'le puedo pasar',
            'te puedo mandar', 'le puedo mandar',
        ]
        for p in patterns:
            self.assertIn(p, self.servidor_source, f"Pattern '{p}' missing in FIX 756")

    def test_fix_756_correo_response(self):
        """FIX 756 responds correctly for correo offer."""
        self.assertIn("Claro que sí, dígame el correo por favor.", self.servidor_source)

    def test_fix_756_whatsapp_response(self):
        """FIX 756 responds correctly for WhatsApp offer."""
        self.assertIn("Claro que sí, dígame el número de WhatsApp por favor.", self.servidor_source)

    def test_fix_756_generic_response(self):
        """FIX 756 responds correctly for generic offer."""
        self.assertIn("Claro que sí, dígame por favor.", self.servidor_source)

    def test_fix_756_pattern_matching_bruce2425(self):
        """FIX 756 would match BRUCE2425 exact text."""
        speech = "te puedo, por ¿te puedo proporcionar su correo?"
        speech_lower = speech.lower()
        patterns = [
            'te paso un', 'le paso un', 'si te doy', 'si le doy',
            'te puedo dar', 'le puedo dar', 'te podria dar', 'le podria dar',
            'te puedo pasar', 'le puedo pasar', 'te podria pasar', 'le podria pasar',
            'te puedo proporcionar', 'le puedo proporcionar',
            'por correo mejor', 'mejor por correo', 'te paso el correo',
            'le paso el correo', 'te doy el correo', 'le doy el correo',
            'te paso el numero', 'le paso el numero', 'te doy un numero',
            'le doy un numero', 'te paso mi', 'le paso mi',
            'te puedo mandar', 'le puedo mandar', 'te mando un', 'le mando un'
        ]
        matched = any(p in speech_lower for p in patterns)
        self.assertTrue(matched, f"BRUCE2425 text should match FIX 756: '{speech_lower}'")
        # Should detect correo
        has_correo = any(w in speech_lower for w in ['correo', 'email', 'mail'])
        self.assertTrue(has_correo, "Should detect correo in BRUCE2425 text")

    def test_fix_756_no_false_positive(self):
        """FIX 756 doesn't trigger on non-offer text."""
        speech = "no está el encargado, salió a comer"
        speech_lower = speech.lower()
        patterns = [
            'te paso un', 'le paso un', 'si te doy', 'si le doy',
            'te puedo dar', 'le puedo dar', 'te podria dar', 'le podria dar',
            'te puedo pasar', 'le puedo pasar', 'te podria pasar', 'le podria pasar',
            'te puedo proporcionar', 'le puedo proporcionar',
            'por correo mejor', 'mejor por correo', 'te paso el correo',
        ]
        matched = any(p in speech_lower for p in patterns)
        self.assertFalse(matched, "Non-offer text should NOT match FIX 756")


# ============================================================
# FIX 757: Pattern audit 0% survival → inmunidad
# ============================================================

class TestFix757PatternImmunity(unittest.TestCase):
    """FIX 757: Patterns with 0% survival added to _PATRONES_INMUNES_UNIVERSAL."""

    def setUp(self):
        """Load agente source."""
        agente_path = os.path.join(os.path.dirname(__file__), '..', 'agente_ventas.py')
        with open(agente_path, 'r', encoding='utf-8') as f:
            self.agente_source = f.read()

    def test_esperando_que_anote_immune(self):
        """ESPERANDO_QUE_ANOTE is in _PATRONES_INMUNES_UNIVERSAL."""
        # Find the _PATRONES_INMUNES_UNIVERSAL block
        match = re.search(r'_PATRONES_INMUNES_UNIVERSAL\s*=\s*\{([^}]+)\}', self.agente_source, re.DOTALL)
        self.assertIsNotNone(match, "_PATRONES_INMUNES_UNIVERSAL not found")
        block = match.group(1)
        self.assertIn('ESPERANDO_QUE_ANOTE', block)

    def test_tienda_cerrada_immune(self):
        """TIENDA_CERRADA is in _PATRONES_INMUNES_UNIVERSAL."""
        match = re.search(r'_PATRONES_INMUNES_UNIVERSAL\s*=\s*\{([^}]+)\}', self.agente_source, re.DOTALL)
        self.assertIsNotNone(match)
        block = match.group(1)
        self.assertIn('TIENDA_CERRADA', block)

    def test_otra_sucursal_already_immune(self):
        """OTRA_SUCURSAL was already in _PATRONES_INMUNES_UNIVERSAL."""
        match = re.search(r'_PATRONES_INMUNES_UNIVERSAL\s*=\s*\{([^}]+)\}', self.agente_source, re.DOTALL)
        self.assertIsNotNone(match)
        block = match.group(1)
        self.assertIn('OTRA_SUCURSAL', block)

    def test_fix_757_comment_exists(self):
        """FIX 757 comment exists in source."""
        self.assertIn('FIX 757', self.agente_source)


# ============================================================
# FIX 756: Pattern matching variants
# ============================================================

class TestFix756PatternVariants(unittest.TestCase):
    """FIX 756: Test various client offer phrasings."""

    def setUp(self):
        self.patterns = [
            'te paso un', 'le paso un', 'si te doy', 'si le doy',
            'te puedo dar', 'le puedo dar', 'te podria dar', 'le podria dar',
            'te puedo pasar', 'le puedo pasar', 'te podria pasar', 'le podria pasar',
            'te puedo proporcionar', 'le puedo proporcionar',
            'por correo mejor', 'mejor por correo', 'te paso el correo',
            'le paso el correo', 'te doy el correo', 'le doy el correo',
            'te paso el numero', 'le paso el numero', 'te doy un numero',
            'le doy un numero', 'te paso mi', 'le paso mi',
            'te puedo mandar', 'le puedo mandar', 'te mando un', 'le mando un'
        ]

    def _matches(self, text):
        text_lower = text.lower()
        return any(p in text_lower for p in self.patterns)

    def test_te_puedo_proporcionar_correo(self):
        self.assertTrue(self._matches("¿Te puedo proporcionar su correo?"))

    def test_le_paso_el_correo(self):
        self.assertTrue(self._matches("Le paso el correo del encargado"))

    def test_te_doy_un_numero(self):
        # FIX 631 normalizes accents: número → numero
        self.assertTrue(self._matches("Te doy un numero de WhatsApp"))

    def test_por_correo_mejor(self):
        self.assertTrue(self._matches("Por correo mejor, ¿no?"))

    def test_te_puedo_mandar_info(self):
        self.assertTrue(self._matches("Te puedo mandar la información"))

    def test_le_paso_mi_whatsapp(self):
        self.assertTrue(self._matches("Te paso mi WhatsApp"))

    def test_no_match_simple_question(self):
        self.assertFalse(self._matches("¿Quién habla?"))

    def test_no_match_rejection(self):
        self.assertFalse(self._matches("No gracias, no me interesa"))

    def test_no_match_callback(self):
        self.assertFalse(self._matches("Marque más tarde por favor"))


if __name__ == '__main__':
    unittest.main()
