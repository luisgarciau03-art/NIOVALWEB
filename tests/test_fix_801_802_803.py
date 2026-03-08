"""
Tests for FIX 801-803: BRUCE2522 bug fixes.

FIX 801: Missing QUESTION transition for DICTANDO_DATO in FSM.
  - Before: QUESTION in DICTANDO_DATO fell to UNKNOWN → filler loop.
  - After: QUESTION exits DICTANDO_DATO → GPT_NARROW responder_pregunta_producto.

FIX 802: FSM bypasses FIX 759B post-transfer re-introduction.
  - Before: FSM intercepted greeting post-transfer with wrong template.
  - After: FSM checks _post_espera_reintroducir_759 flag first.

FIX 803: Portuguese "continue" → Spanish "prosiga".
  - Before: TTS pronounced "continue" as Portuguese.
  - After: Templates use "prosiga" (unambiguously Spanish).
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from fsm_engine import (
    FSMEngine, FSMState, FSMIntent, FSMContext, ActionType,
    classify_intent,
)
from response_templates import TEMPLATES


# ============================================================
# FIX 801: DICTANDO_DATO + QUESTION → exits dictation
# ============================================================

class TestFix801DictandoDatoQuestion(unittest.TestCase):
    """QUESTION during DICTANDO_DATO must exit dictation, not loop."""

    def setUp(self):
        self.fsm = FSMEngine()

    def test_question_transition_exists(self):
        """DICTANDO_DATO must have a QUESTION transition."""
        transition = self.fsm._lookup(FSMState.DICTANDO_DATO, FSMIntent.QUESTION)
        self.assertIsNotNone(transition, "DICTANDO_DATO missing QUESTION transition")

    def test_question_exits_dictation(self):
        """QUESTION must exit DICTANDO_DATO (not stay in it)."""
        transition = self.fsm._lookup(FSMState.DICTANDO_DATO, FSMIntent.QUESTION)
        self.assertNotEqual(transition.next_state, FSMState.DICTANDO_DATO,
                            "QUESTION should exit DICTANDO_DATO")

    def test_question_uses_gpt_narrow(self):
        """QUESTION should use GPT_NARROW to answer properly."""
        transition = self.fsm._lookup(FSMState.DICTANDO_DATO, FSMIntent.QUESTION)
        self.assertEqual(transition.action_type, ActionType.GPT_NARROW)

    def test_question_goes_to_capturando(self):
        """QUESTION should go to CAPTURANDO_CONTACTO."""
        transition = self.fsm._lookup(FSMState.DICTANDO_DATO, FSMIntent.QUESTION)
        self.assertEqual(transition.next_state, FSMState.CAPTURANDO_CONTACTO)

    def test_que_tipo_productos_classified_as_question(self):
        """'¿Qué tipo de productos manejan?' must be classified as QUESTION."""
        ctx = FSMContext()
        intent = classify_intent("¿Qué tipo de productos manejan?", ctx, FSMState.DICTANDO_DATO)
        self.assertEqual(intent, FSMIntent.QUESTION)

    def test_que_venden_classified_as_question_or_what_offer(self):
        """'¿Qué venden?' must be classified as QUESTION or WHAT_OFFER (FIX 894)."""
        ctx = FSMContext()
        intent = classify_intent("¿Qué venden?", ctx, FSMState.DICTANDO_DATO)
        self.assertIn(intent, (FSMIntent.QUESTION, FSMIntent.WHAT_OFFER))

    def test_dictating_partial_still_works(self):
        """Dictation partial (digits) must still stay in DICTANDO_DATO."""
        transition = self.fsm._lookup(FSMState.DICTANDO_DATO, FSMIntent.DICTATING_PARTIAL)
        self.assertEqual(transition.next_state, FSMState.DICTANDO_DATO)

    def test_unknown_still_stays(self):
        """UNKNOWN must still stay in DICTANDO_DATO (catch-all)."""
        transition = self.fsm._lookup(FSMState.DICTANDO_DATO, FSMIntent.UNKNOWN)
        self.assertEqual(transition.next_state, FSMState.DICTANDO_DATO)

    def test_bruce2522_scenario_no_filler_loop(self):
        """Simulate BRUCE2522: question during dictation must NOT return filler."""
        self.fsm.state = FSMState.DICTANDO_DATO
        # "¿Qué tipo de productos manejan?" should NOT return "Claro, prosiga." etc.
        transition = self.fsm._lookup(FSMState.DICTANDO_DATO, FSMIntent.QUESTION)
        self.assertNotEqual(transition.action_type, ActionType.ACKNOWLEDGE,
                            "QUESTION should not return acknowledgment filler")


# ============================================================
# FIX 802: Post-transfer re-introduction in FSM
# ============================================================

class TestFix802PostTransferReintro(unittest.TestCase):
    """FSM must respect _post_espera_reintroducir_759 flag."""

    def setUp(self):
        self.fsm = FSMEngine()

    def _make_mock_agente(self, flag_value):
        """Create a mock agente with the post-transfer flag."""
        class MockAgente:
            _post_espera_reintroducir_759 = flag_value
        return MockAgente()

    def test_greeting_with_flag_returns_pitch(self):
        """Greeting after transfer must return pitch_persona_nueva."""
        self.fsm.state = FSMState.BUSCANDO_ENCARGADO
        agente = self._make_mock_agente(True)
        result = self.fsm.process("Hola, buen día.", agente)
        self.assertIsNotNone(result)
        self.assertIn("NIOVAL", result)
        self.assertIn("encargado", result.lower())

    def test_flag_consumed_after_greeting(self):
        """Flag must be consumed (set to False) after processing."""
        self.fsm.state = FSMState.BUSCANDO_ENCARGADO
        agente = self._make_mock_agente(True)
        self.fsm.process("Hola, buen día.", agente)
        self.assertFalse(agente._post_espera_reintroducir_759)

    def test_identity_question_not_intercepted(self):
        """'¿Quién habla?' should NOT trigger re-intro (FIX 749A handles it)."""
        self.fsm.state = FSMState.BUSCANDO_ENCARGADO
        agente = self._make_mock_agente(True)
        result = self.fsm.process("¿Quién habla?", agente)
        # Should NOT be pitch_persona_nueva (identity questions handled separately)
        if result:
            # If FSM handled it, it should be identification, not pitch
            self.assertNotIn("productos de ferreteria", result.lower())

    def test_flag_consumed_even_for_identity(self):
        """Flag must be consumed even if identity question (prevent stale flag)."""
        self.fsm.state = FSMState.BUSCANDO_ENCARGADO
        agente = self._make_mock_agente(True)
        self.fsm.process("¿Quién habla?", agente)
        self.assertFalse(agente._post_espera_reintroducir_759)

    def test_no_flag_normal_processing(self):
        """Without flag, FSM processes normally."""
        self.fsm.state = FSMState.BUSCANDO_ENCARGADO
        agente = self._make_mock_agente(False)
        result = self.fsm.process("Hola, buen día.", agente)
        # Should NOT be pitch_persona_nueva (no flag set)
        if result:
            self.assertNotIn("productos de ferreteria", result.lower())

    def test_bueno_triggers_reintro(self):
        """'Bueno' after transfer triggers re-introduction."""
        self.fsm.state = FSMState.CAPTURANDO_CONTACTO
        agente = self._make_mock_agente(True)
        result = self.fsm.process("Bueno", agente)
        self.assertIsNotNone(result)
        self.assertIn("NIOVAL", result)

    def test_digame_triggers_reintro(self):
        """'Dígame' after transfer triggers re-introduction."""
        self.fsm.state = FSMState.CAPTURANDO_CONTACTO
        agente = self._make_mock_agente(True)
        result = self.fsm.process("Dígame", agente)
        self.assertIsNotNone(result)
        self.assertIn("NIOVAL", result)

    def test_fsm_state_reset_to_buscando(self):
        """After re-intro, FSM state should be BUSCANDO_ENCARGADO."""
        self.fsm.state = FSMState.CAPTURANDO_CONTACTO
        agente = self._make_mock_agente(True)
        self.fsm.process("Hola, buen día.", agente)
        self.assertEqual(self.fsm.state, FSMState.BUSCANDO_ENCARGADO)

    def test_context_flags_set(self):
        """After re-intro, pitch_dado and encargado_preguntado must be True."""
        self.fsm.state = FSMState.CAPTURANDO_CONTACTO
        agente = self._make_mock_agente(True)
        self.fsm.process("Hola, buen día.", agente)
        self.assertTrue(self.fsm.context.pitch_dado)
        self.assertTrue(self.fsm.context.encargado_preguntado)


# ============================================================
# FIX 803: "continue" → "prosiga" (Portuguese → Spanish)
# ============================================================

class TestFix803ProsigaNotContinue(unittest.TestCase):
    """Templates must use 'prosiga' instead of 'continue'."""

    def test_aja_si_no_continue(self):
        """aja_si templates must NOT contain 'continue'."""
        for variant in TEMPLATES["aja_si"]:
            self.assertNotIn("continue", variant.lower(),
                             f"Found Portuguese 'continue' in: {variant}")

    def test_aja_si_has_prosiga(self):
        """aja_si templates must contain 'prosiga' as replacement."""
        all_text = " ".join(TEMPLATES["aja_si"]).lower()
        self.assertIn("prosiga", all_text)

    def test_aja_si_count(self):
        """aja_si must have at least 5 variants (FIX 906E: +2 naturales)."""
        self.assertGreaterEqual(len(TEMPLATES["aja_si"]), 5)

    def test_aja_digame_unchanged(self):
        """aja_digame templates should not be affected."""
        self.assertIn("aja_digame", TEMPLATES)
        self.assertTrue(len(TEMPLATES["aja_digame"]) >= 4)

    def test_agente_ack_variants_source(self):
        """Verify _ACK_VARIANTS_769 in agente_ventas.py uses prosiga."""
        agente_path = os.path.join(os.path.dirname(__file__), '..', 'agente_ventas.py')
        with open(agente_path, 'r', encoding='utf-8') as f:
            content = f.read()
        # Must NOT have "continúe" in _ACK_VARIANTS_769
        # Find the block
        start = content.find('_ACK_VARIANTS_769 = [')
        end = content.find(']', start) + 1
        block = content[start:end]
        self.assertNotIn('continúe', block, "Found 'continúe' in _ACK_VARIANTS_769")
        self.assertIn('prosiga', block, "Missing 'prosiga' in _ACK_VARIANTS_769")


# ============================================================
# Integration: Full BRUCE2522 scenario
# ============================================================

class TestBruce2522Scenario(unittest.TestCase):
    """End-to-end test for BRUCE2522 bugs."""

    def setUp(self):
        self.fsm = FSMEngine()

    def test_transfer_then_greeting_then_question(self):
        """Simulate BRUCE2522 full flow:
        1. Transfer → wait
        2. New person greets → re-intro (FIX 802)
        3. Question about products → answer (FIX 801)
        """
        # Step 1: Simulate arriving at CAPTURANDO_CONTACTO (wrong state)
        # after transfer was missed
        self.fsm.state = FSMState.CAPTURANDO_CONTACTO

        # Step 2: New person says "Hola, buen día." with flag set
        class MockAgente:
            _post_espera_reintroducir_759 = True
        agente = MockAgente()

        result = self.fsm.process("Hola, buen día.", agente)
        self.assertIn("NIOVAL", result, "Should re-introduce with pitch")
        self.assertEqual(self.fsm.state, FSMState.BUSCANDO_ENCARGADO)

        # Step 3: Person asks about products
        # After re-intro, they ask "¿Qué tipo de productos manejan?"
        # Intent classifier should detect QUESTION
        ctx = FSMContext()
        intent = classify_intent("¿Qué tipo de productos manejan?", ctx, FSMState.BUSCANDO_ENCARGADO)
        self.assertEqual(intent, FSMIntent.QUESTION)

        # BUSCANDO_ENCARGADO + QUESTION → GPT_NARROW (not filler)
        transition = self.fsm._lookup(FSMState.BUSCANDO_ENCARGADO, FSMIntent.QUESTION)
        self.assertEqual(transition.action_type, ActionType.GPT_NARROW)


if __name__ == '__main__':
    unittest.main()
