"""
Tests for FIX 793: Bug detector improvements.

FIX 793A: Remove FIX 664B CASE 4 (skip GPT eval on successful calls).
  - Before: GPT eval skipped when Bruce said "muchas gracias" / "le envio"
  - After: GPT eval always runs, detecting bugs even in successful calls
  - Root cause: BRUCE2512 had incoherent Turn 2 but bug detector skipped eval

FIX 793B: New detector PREGUNTA_IGNORADA.
  - Detects when client asks a direct question and Bruce responds with only
    an acknowledgment (adelante, continue, lo escucho) without answering.
  - Root cause: BRUCE2505 client asked "Quien habla?" 2x, Bruce said "adelante"
"""

import os
import sys
import re
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from bug_detector import ContentAnalyzer


# Helper to build minimal conversation
def _conv(*pairs):
    """Build conversation list from (role, text) pairs."""
    return list(pairs)


# ============================================================
# FIX 793A: _es_comportamiento_correcto no skip llamadas exitosas
# ============================================================

class TestFix793ANoSkipExitosas(unittest.TestCase):
    """FIX 793A: GPT eval must NOT be skipped for successful calls."""

    def test_case4_removed_from_source(self):
        """CASO 4 must be commented out / removed in bug_detector.py."""
        bd_path = os.path.join(os.path.dirname(__file__), '..', 'bug_detector.py')
        with open(bd_path, 'r', encoding='utf-8') as f:
            source = f.read()
        # FIX 793A comment must exist
        self.assertIn('FIX 793A', source)
        # The old active code must NOT exist
        self.assertNotIn("if _tuvo_exito:", source)
        self.assertNotIn("Llamada exitosa (cierre con agradecimiento)", source)

    def test_fix_793a_comment_exists(self):
        """FIX 793A: CASO 4 ELIMINADO comment must exist."""
        bd_path = os.path.join(os.path.dirname(__file__), '..', 'bug_detector.py')
        with open(bd_path, 'r', encoding='utf-8') as f:
            source = f.read()
        self.assertIn('CASO 4 ELIMINADO', source)

    def test_bruce2512_pattern_not_skipped(self):
        """Conversation ending with 'muchas gracias por su tiempo' must NOT be skipped."""
        from bug_detector import _es_comportamiento_correcto
        conv = [
            ("bruce", "Me comunico de la marca nioval. Se encontrara el encargado?"),
            ("cliente", "que tal buen dia"),
            ("bruce", "Hola! Buen dia, aqui andamos listos para ayudarte."),
            ("cliente", "no no esta"),
            ("bruce", "Entiendo. Me podria proporcionar un WhatsApp?"),
            ("cliente", "si, es 6623531804"),
            ("bruce", "Perfecto. Le envio el catalogo. Muchas gracias por su tiempo."),
        ]
        # Must NOT return True (must NOT skip GPT eval)
        result = _es_comportamiento_correcto(conv)
        self.assertFalse(result)

    def test_le_envio_pattern_not_skipped(self):
        """Conversation with 'le envio' must NOT be skipped."""
        from bug_detector import _es_comportamiento_correcto
        conv = [
            ("bruce", "Somos de NIOVAL. Se encontrara el encargado?"),
            ("cliente", "si, digame"),
            ("bruce", "Le envio nuestro catalogo por WhatsApp."),
            ("cliente", "sale"),
            ("bruce", "Excelente dia."),
        ]
        result = _es_comportamiento_correcto(conv)
        self.assertFalse(result)


# ============================================================
# FIX 793B: _check_pregunta_ignorada
# ============================================================

class TestFix793BPreguntaIgnorada(unittest.TestCase):
    """FIX 793B: Detect when client asks question and Bruce gives only ack."""

    def test_quien_habla_adelante(self):
        """Client: 'Quien habla?' Bruce: 'adelante' → PREGUNTA_IGNORADA."""
        conv = _conv(
            ("bruce", "Me comunico de la marca NIOVAL."),
            ("cliente", "Aja"),
            ("bruce", "Claro, digame el numero."),
            ("cliente", "¿Quién habla?"),
            ("bruce", "Si, adelante."),
        )
        bugs = ContentAnalyzer._check_pregunta_ignorada(conv)
        self.assertEqual(len(bugs), 1)
        self.assertEqual(bugs[0]["tipo"], "PREGUNTA_IGNORADA")

    def test_quien_habla_twice_alto(self):
        """Client asks 'Quien habla?' 2x → severity ALTO."""
        conv = _conv(
            ("bruce", "Somos de NIOVAL."),
            ("cliente", "¿Quién habla?"),
            ("bruce", "Claro, continue."),
            ("cliente", "¿Quién habla?"),
            ("bruce", "Si, adelante."),
        )
        bugs = ContentAnalyzer._check_pregunta_ignorada(conv)
        self.assertEqual(len(bugs), 1)
        self.assertEqual(bugs[0]["severidad"], "ALTO")
        self.assertIn("2x", bugs[0]["detalle"])

    def test_de_donde_llama_continue(self):
        """Client: 'De donde llama?' Bruce: 'continue' → bug."""
        conv = _conv(
            ("bruce", "Buenos dias."),
            ("cliente", "Hola"),
            ("bruce", "Digame."),
            ("cliente", "¿De dónde llama?"),
            ("bruce", "Claro, continue."),
        )
        bugs = ContentAnalyzer._check_pregunta_ignorada(conv)
        self.assertEqual(len(bugs), 1)

    def test_a_quien_busca_perfecto_adelante(self):
        """Client: 'A quien busca?' Bruce: 'Perfecto, adelante.' → bug."""
        conv = _conv(
            ("bruce", "Me comunico de NIOVAL."),
            ("cliente", "Si"),
            ("bruce", "Digame."),
            ("cliente", "¿A quién busca?"),
            ("bruce", "Perfecto, adelante."),
        )
        bugs = ContentAnalyzer._check_pregunta_ignorada(conv)
        self.assertEqual(len(bugs), 1)

    def test_que_ofrece_lo_escucho(self):
        """Client: 'Que ofrece?' Bruce: 'lo escucho' → bug."""
        conv = _conv(
            ("bruce", "Me comunico de NIOVAL."),
            ("cliente", "Ajá"),
            ("bruce", "Digame."),
            ("cliente", "¿Qué ofrece?"),
            ("bruce", "Si, lo escucho."),
        )
        bugs = ContentAnalyzer._check_pregunta_ignorada(conv)
        self.assertEqual(len(bugs), 1)

    def test_bruce_answers_properly_no_bug(self):
        """Client: 'Quien habla?' Bruce: 'Le hablo de NIOVAL' → NO bug."""
        conv = _conv(
            ("bruce", "Buenos dias."),
            ("cliente", "Hola"),
            ("bruce", "Digame."),
            ("cliente", "¿Quién habla?"),
            ("bruce", "Le hablo de la marca NIOVAL, manejamos productos ferreteros."),
        )
        bugs = ContentAnalyzer._check_pregunta_ignorada(conv)
        self.assertEqual(len(bugs), 0)

    def test_non_question_no_bug(self):
        """Client says statement (no question) → NO bug even with ack."""
        conv = _conv(
            ("bruce", "Buenos dias."),
            ("cliente", "Hola"),
            ("bruce", "Digame."),
            ("cliente", "No me interesa."),
            ("bruce", "Claro, adelante."),
        )
        bugs = ContentAnalyzer._check_pregunta_ignorada(conv)
        self.assertEqual(len(bugs), 0)

    def test_too_short_conv_no_bug(self):
        """Conversation too short (< 4 turns) → no check."""
        conv = _conv(
            ("bruce", "Hola"),
            ("cliente", "¿Quién habla?"),
            ("bruce", "Adelante."),
        )
        bugs = ContentAnalyzer._check_pregunta_ignorada(conv)
        self.assertEqual(len(bugs), 0)

    def test_single_question_medio(self):
        """Single ignored question → severity MEDIO."""
        conv = _conv(
            ("bruce", "Me comunico de NIOVAL."),
            ("cliente", "Ajá"),
            ("bruce", "Digame el numero."),
            ("cliente", "¿De qué empresa habla?"),
            ("bruce", "Claro, continue."),
        )
        bugs = ContentAnalyzer._check_pregunta_ignorada(conv)
        self.assertEqual(len(bugs), 1)
        self.assertEqual(bugs[0]["severidad"], "MEDIO")


# ============================================================
# FIX 793B: Regex patterns
# ============================================================

class TestFix793BRegexPatterns(unittest.TestCase):
    """FIX 793B: Regex patterns for question detection and ack detection."""

    def test_pregunta_directa_patterns(self):
        """_PREGUNTA_DIRECTA_CLIENTE must match key question patterns."""
        regex = ContentAnalyzer._PREGUNTA_DIRECTA_CLIENTE
        should_match = [
            "¿Quién habla?",
            "Quien habla?",
            "¿De dónde llama?",
            "De donde llama?",
            "¿Qué empresa es?",
            "¿A quién busca?",
            "¿De qué marca habla?",
            "¿Quién llama?",
            "¿Qué ofrece?",
            "¿Qué vende?",
        ]
        for pattern in should_match:
            self.assertIsNotNone(regex.search(pattern), f"Should match: '{pattern}'")

    def test_pregunta_directa_no_match(self):
        """Non-question patterns must NOT match."""
        regex = ContentAnalyzer._PREGUNTA_DIRECTA_CLIENTE
        should_not_match = [
            "No me interesa",
            "Sí, adelante",
            "¿Bueno?",
            "Dígame",
            "No está",
        ]
        for pattern in should_not_match:
            self.assertIsNone(regex.search(pattern), f"Should NOT match: '{pattern}'")

    def test_bruce_ack_puro_patterns(self):
        """_BRUCE_ACK_PURO_793 must match pure acknowledgment responses."""
        regex = ContentAnalyzer._BRUCE_ACK_PURO_793
        should_match = [
            "Si, adelante.",
            "Claro, continue.",
            "Perfecto, adelante.",
            "Entendido, continue.",
            "Adelante.",
            "Continue.",
            "Lo escucho.",
            "Claro, si.",
            "Aja",
        ]
        for pattern in should_match:
            self.assertIsNotNone(regex.search(pattern), f"Should match: '{pattern}'")

    def test_bruce_ack_real_answer_no_match(self):
        """Real answers must NOT match ack pattern."""
        regex = ContentAnalyzer._BRUCE_ACK_PURO_793
        should_not_match = [
            "Le hablo de la marca NIOVAL.",
            "Somos distribuidores de productos ferreteros.",
            "Entiendo. Me podria dar su WhatsApp?",
            "Claro, le comento que somos de NIOVAL.",
        ]
        for pattern in should_not_match:
            self.assertIsNone(regex.search(pattern), f"Should NOT match: '{pattern}'")


# ============================================================
# FIX 793B: BRUCE2505 reproduction
# ============================================================

class TestFix793BBRUCE2505(unittest.TestCase):
    """FIX 793B: Reproduce BRUCE2505 scenario."""

    def test_bruce2505_pattern(self):
        """BRUCE2505: Client asks 'Quien habla?' 2x, Bruce says 'adelante' → caught."""
        conv = _conv(
            ("bruce", "Me comunico de la marca nioval."),
            ("cliente", "Buen dia, permitame un momento."),
            ("bruce", "Claro, espero."),
            ("cliente", "No, no se encuentra."),
            ("bruce", "Entiendo. Me podria proporcionar un WhatsApp?"),
            ("cliente", "365. Bueno,"),
            ("bruce", "Si, adelante."),
            ("cliente", "¿Bueno?"),
            ("bruce", "Si, adelante."),
            ("cliente", "365."),
            ("bruce", "Claro, continue."),
            ("cliente", "Porque si Cualquier Perdon."),
            ("bruce", "Si, lo escucho."),
            ("cliente", "¿Perdón? ¿Bueno? ¿Bueno, sí, dígame?"),
            ("bruce", "Entendido, continue."),
            ("cliente", "Sí, dígame. ¿A quién busca?"),
            ("bruce", "Perfecto, adelante."),
            ("cliente", "¿Quién habla?"),
            ("bruce", "Si, adelante."),
            ("cliente", "¿Quién habla?"),
            ("bruce", "Claro, continue."),
        )
        bugs = ContentAnalyzer._check_pregunta_ignorada(conv)
        self.assertGreaterEqual(len(bugs), 1)
        self.assertEqual(bugs[0]["tipo"], "PREGUNTA_IGNORADA")
        self.assertEqual(bugs[0]["severidad"], "ALTO")


# ============================================================
# FIX 793: Code integration
# ============================================================

class TestFix793Integration(unittest.TestCase):
    """FIX 793: Code must exist in bug_detector.py."""

    def test_fix_793_in_source(self):
        """FIX 793A and FIX 793B must appear in bug_detector.py."""
        bd_path = os.path.join(os.path.dirname(__file__), '..', 'bug_detector.py')
        with open(bd_path, 'r', encoding='utf-8') as f:
            source = f.read()
        self.assertIn('FIX 793A', source)
        self.assertIn('FIX 793B', source)
        self.assertIn('_check_pregunta_ignorada', source)
        self.assertIn('PREGUNTA_IGNORADA', source)

    def test_pregunta_ignorada_in_pipeline(self):
        """_check_pregunta_ignorada must be called in detect_bugs pipeline."""
        bd_path = os.path.join(os.path.dirname(__file__), '..', 'bug_detector.py')
        with open(bd_path, 'r', encoding='utf-8') as f:
            source = f.read()
        # Must be called in the pipeline
        self.assertIn('_check_pregunta_ignorada(tracker.conversacion)', source)

    def test_method_exists(self):
        """ContentAnalyzer must have _check_pregunta_ignorada method."""
        self.assertTrue(hasattr(ContentAnalyzer, '_check_pregunta_ignorada'))

    def test_regex_attributes_exist(self):
        """ContentAnalyzer must have FIX 793B regex attributes."""
        self.assertTrue(hasattr(ContentAnalyzer, '_PREGUNTA_DIRECTA_CLIENTE'))
        self.assertTrue(hasattr(ContentAnalyzer, '_BRUCE_ACK_PURO_793'))


if __name__ == '__main__':
    unittest.main()
