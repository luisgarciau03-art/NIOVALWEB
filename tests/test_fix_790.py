"""
Tests for FIX 790: CONVERSACION_LIBRE shadow transitions.

CONVERSACION_LIBRE is the only state that had 0 transitions.
FIX 790 adds 17 transitions for all intents (shadow-only, not in FSM_ACTIVE_STATES).
Prepared for future activation when entry points are defined.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from fsm_engine import (
    FSMIntent, FSMState, FSMEngine, ActionType
)


class TestFix790ConversacionLibreTransitions(unittest.TestCase):
    """FIX 790: CONVERSACION_LIBRE has shadow transitions for all key intents."""

    def setUp(self):
        self.fsm = FSMEngine()

    def test_conversacion_libre_has_transitions(self):
        """CONVERSACION_LIBRE should have transitions defined."""
        cl_transitions = [
            (s, i) for (s, i) in self.fsm._transitions
            if s == FSMState.CONVERSACION_LIBRE
        ]
        self.assertGreaterEqual(len(cl_transitions), 15,
                               f"Expected 15+ transitions, got {len(cl_transitions)}")

    def test_farewell_to_despedida(self):
        """CONVERSACION_LIBRE + FAREWELL → DESPEDIDA."""
        t = self.fsm._transitions.get((FSMState.CONVERSACION_LIBRE, FSMIntent.FAREWELL))
        self.assertIsNotNone(t)
        self.assertEqual(t.next_state, FSMState.DESPEDIDA)
        self.assertEqual(t.template_key, "despedida_cortes")

    def test_no_interest_to_despedida(self):
        """CONVERSACION_LIBRE + NO_INTEREST → DESPEDIDA."""
        t = self.fsm._transitions.get((FSMState.CONVERSACION_LIBRE, FSMIntent.NO_INTEREST))
        self.assertIsNotNone(t)
        self.assertEqual(t.next_state, FSMState.DESPEDIDA)

    def test_verification_stays(self):
        """CONVERSACION_LIBRE + VERIFICATION → stays."""
        t = self.fsm._transitions.get((FSMState.CONVERSACION_LIBRE, FSMIntent.VERIFICATION))
        self.assertIsNotNone(t)
        self.assertEqual(t.next_state, FSMState.CONVERSACION_LIBRE)
        self.assertEqual(t.template_key, "verificacion_aqui_estoy")

    def test_question_gpt_narrow(self):
        """CONVERSACION_LIBRE + QUESTION → GPT_NARROW."""
        t = self.fsm._transitions.get((FSMState.CONVERSACION_LIBRE, FSMIntent.QUESTION))
        self.assertIsNotNone(t)
        self.assertEqual(t.action_type, ActionType.GPT_NARROW)
        self.assertEqual(t.template_key, "responder_pregunta_producto")

    def test_identity_stays(self):
        """CONVERSACION_LIBRE + IDENTITY → stays with identificacion."""
        t = self.fsm._transitions.get((FSMState.CONVERSACION_LIBRE, FSMIntent.IDENTITY))
        self.assertIsNotNone(t)
        self.assertEqual(t.template_key, "identificacion_nioval")

    def test_offer_data_to_dictando(self):
        """CONVERSACION_LIBRE + OFFER_DATA → DICTANDO_DATO."""
        t = self.fsm._transitions.get((FSMState.CONVERSACION_LIBRE, FSMIntent.OFFER_DATA))
        self.assertIsNotNone(t)
        self.assertEqual(t.next_state, FSMState.DICTANDO_DATO)

    def test_dictating_complete_phone(self):
        """CONVERSACION_LIBRE + DICTATING_COMPLETE_PHONE → CONTACTO_CAPTURADO."""
        t = self.fsm._transitions.get((FSMState.CONVERSACION_LIBRE, FSMIntent.DICTATING_COMPLETE_PHONE))
        self.assertIsNotNone(t)
        self.assertEqual(t.next_state, FSMState.CONTACTO_CAPTURADO)
        self.assertEqual(t.template_key, "confirmar_telefono")

    def test_dictating_complete_email(self):
        """CONVERSACION_LIBRE + DICTATING_COMPLETE_EMAIL → CONTACTO_CAPTURADO."""
        t = self.fsm._transitions.get((FSMState.CONVERSACION_LIBRE, FSMIntent.DICTATING_COMPLETE_EMAIL))
        self.assertIsNotNone(t)
        self.assertEqual(t.next_state, FSMState.CONTACTO_CAPTURADO)

    def test_dictating_partial(self):
        """CONVERSACION_LIBRE + DICTATING_PARTIAL → DICTANDO_DATO."""
        t = self.fsm._transitions.get((FSMState.CONVERSACION_LIBRE, FSMIntent.DICTATING_PARTIAL))
        self.assertIsNotNone(t)
        self.assertEqual(t.next_state, FSMState.DICTANDO_DATO)

    def test_continuation_noop(self):
        """CONVERSACION_LIBRE + CONTINUATION → NOOP (stay)."""
        t = self.fsm._transitions.get((FSMState.CONVERSACION_LIBRE, FSMIntent.CONTINUATION))
        self.assertIsNotNone(t)
        self.assertEqual(t.action_type, ActionType.NOOP)
        self.assertEqual(t.next_state, FSMState.CONVERSACION_LIBRE)

    def test_unknown_gpt_narrow(self):
        """CONVERSACION_LIBRE + UNKNOWN → GPT_NARROW conversacion_libre."""
        t = self.fsm._transitions.get((FSMState.CONVERSACION_LIBRE, FSMIntent.UNKNOWN))
        self.assertIsNotNone(t)
        self.assertEqual(t.action_type, ActionType.GPT_NARROW)
        self.assertEqual(t.template_key, "conversacion_libre")

    def test_interest_to_capturando(self):
        """CONVERSACION_LIBRE + INTEREST → CAPTURANDO_CONTACTO."""
        t = self.fsm._transitions.get((FSMState.CONVERSACION_LIBRE, FSMIntent.INTEREST))
        self.assertIsNotNone(t)
        self.assertEqual(t.next_state, FSMState.CAPTURANDO_CONTACTO)

    def test_wrong_number_to_despedida(self):
        """CONVERSACION_LIBRE + WRONG_NUMBER → DESPEDIDA."""
        t = self.fsm._transitions.get((FSMState.CONVERSACION_LIBRE, FSMIntent.WRONG_NUMBER))
        self.assertIsNotNone(t)
        self.assertEqual(t.next_state, FSMState.DESPEDIDA)

    def test_another_branch_to_despedida(self):
        """CONVERSACION_LIBRE + ANOTHER_BRANCH → DESPEDIDA."""
        t = self.fsm._transitions.get((FSMState.CONVERSACION_LIBRE, FSMIntent.ANOTHER_BRANCH))
        self.assertIsNotNone(t)
        self.assertEqual(t.next_state, FSMState.DESPEDIDA)

    def test_closed_to_despedida(self):
        """CONVERSACION_LIBRE + CLOSED → DESPEDIDA."""
        t = self.fsm._transitions.get((FSMState.CONVERSACION_LIBRE, FSMIntent.CLOSED))
        self.assertIsNotNone(t)
        self.assertEqual(t.next_state, FSMState.DESPEDIDA)

    def test_not_in_active_states(self):
        """CONVERSACION_LIBRE should NOT be in FSM_ACTIVE_STATES (shadow only)."""
        from fsm_engine import FSM_ACTIVE_STATES_SET
        self.assertNotIn(FSMState.CONVERSACION_LIBRE, FSM_ACTIVE_STATES_SET,
                        "CONVERSACION_LIBRE should remain shadow-only")


class TestFix790AllStatesHaveTransitions(unittest.TestCase):
    """Verify all 12 states now have at least 1 transition."""

    def test_all_states_have_transitions(self):
        """Every FSMState should have at least 1 transition defined."""
        fsm = FSMEngine()
        for state in FSMState:
            state_transitions = [
                (s, i) for (s, i) in fsm._transitions if s == state
            ]
            self.assertGreater(len(state_transitions), 0,
                              f"State {state.value} has 0 transitions!")


if __name__ == '__main__':
    unittest.main()
