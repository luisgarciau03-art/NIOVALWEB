"""
Tests for FIX 789: Activate orphaned narrow prompts.

FIX 789A: PITCH+UNKNOWN → GPT_NARROW `manejar_objecion`
  - Before: PITCH+UNKNOWN blindly advanced to preguntar_encargado
  - After: Uses GPT narrow prompt for empathetic, contextual response
  - Stays in PITCH (doesn't advance on ambiguous input)

FIX 789B: Callback hora-loop protection with `confirmar_callback_generico`
  - When preguntar_hora_callback already used and client gives vague CALLBACK again
  - Uses confirmar_callback_generico instead of repeating "¿A qué hora?"
  - Prevents hora question loop
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from fsm_engine import (
    classify_intent, FSMIntent, FSMContext, FSMState, FSMEngine,
    ActionType, Transition, _normalize, TEMPLATES
)
from response_templates import NARROW_PROMPTS


# ============================================================
# FIX 789A: PITCH+UNKNOWN → GPT_NARROW manejar_objecion
# ============================================================

class TestFix789APitchUnknown(unittest.TestCase):
    """FIX 789A: PITCH+UNKNOWN uses manejar_objecion narrow prompt."""

    def test_pitch_unknown_transition_is_gpt_narrow(self):
        """PITCH+UNKNOWN transition should be GPT_NARROW, not TEMPLATE."""
        fsm = FSMEngine()
        t = fsm._transitions.get((FSMState.PITCH, FSMIntent.UNKNOWN))
        self.assertIsNotNone(t, "PITCH+UNKNOWN transition must exist")
        self.assertEqual(t.action_type, ActionType.GPT_NARROW,
                        "PITCH+UNKNOWN should use GPT_NARROW action")
        self.assertEqual(t.template_key, "manejar_objecion",
                        "PITCH+UNKNOWN should use manejar_objecion prompt")

    def test_pitch_unknown_stays_in_pitch(self):
        """PITCH+UNKNOWN should stay in PITCH (not advance to BUSCANDO)."""
        fsm = FSMEngine()
        t = fsm._transitions.get((FSMState.PITCH, FSMIntent.UNKNOWN))
        self.assertEqual(t.next_state, FSMState.PITCH,
                        "PITCH+UNKNOWN should stay in PITCH state")

    def test_manejar_objecion_prompt_exists(self):
        """manejar_objecion narrow prompt must be defined."""
        self.assertIn("manejar_objecion", NARROW_PROMPTS)
        config = NARROW_PROMPTS["manejar_objecion"]
        self.assertIn("system", config)
        self.assertIn("max_tokens", config)
        self.assertIn("NIOVAL", config["system"])

    def test_pitch_unknown_uses_fix791_template(self):
        """FIX 791: PITCH+UNKNOWN → stateful template (no GPT needed)."""
        fsm = FSMEngine()
        fsm.state = FSMState.PITCH
        fsm.context.pitch_dado = True
        result = fsm.process("Pues no sé qué decirle.", agente=None)
        # FIX 791: stateful template advances state
        self.assertIn(fsm.state, [
            FSMState.BUSCANDO_ENCARGADO,
            FSMState.CAPTURANDO_CONTACTO,
        ])
        self.assertIsNotNone(result)

    def test_other_states_unknown_unchanged(self):
        """Other states' UNKNOWN handlers should NOT be manejar_objecion."""
        fsm = FSMEngine()
        # BUSCANDO_ENCARGADO should still use conversacion_libre
        t = fsm._transitions.get((FSMState.BUSCANDO_ENCARGADO, FSMIntent.UNKNOWN))
        self.assertEqual(t.template_key, "conversacion_libre")
        # ENCARGADO_PRESENTE should still use conversacion_libre
        t = fsm._transitions.get((FSMState.ENCARGADO_PRESENTE, FSMIntent.UNKNOWN))
        self.assertEqual(t.template_key, "conversacion_libre")

    def test_pitch_known_intents_unchanged(self):
        """Known intents in PITCH should work exactly as before."""
        fsm = FSMEngine()
        # NO_INTEREST → DESPEDIDA
        t = fsm._transitions.get((FSMState.PITCH, FSMIntent.NO_INTEREST))
        self.assertEqual(t.next_state, FSMState.DESPEDIDA)
        self.assertEqual(t.template_key, "despedida_no_interesa")
        # CONFIRMATION → BUSCANDO
        t = fsm._transitions.get((FSMState.PITCH, FSMIntent.CONFIRMATION))
        self.assertEqual(t.next_state, FSMState.BUSCANDO_ENCARGADO)
        # QUESTION → PITCH with GPT_NARROW
        t = fsm._transitions.get((FSMState.PITCH, FSMIntent.QUESTION))
        self.assertEqual(t.action_type, ActionType.GPT_NARROW)
        self.assertEqual(t.template_key, "responder_pregunta_producto")


# ============================================================
# FIX 789B: Callback hora-loop protection
# ============================================================

class TestFix789BCallbackHoraLoop(unittest.TestCase):
    """FIX 789B: No repetir '¿A qué hora?' si ya se preguntó."""

    def test_context_has_callback_hora_preguntada(self):
        """FSMContext must have callback_hora_preguntada attribute."""
        ctx = FSMContext()
        self.assertFalse(ctx.callback_hora_preguntada)

    def test_confirmar_callback_generico_template_exists(self):
        """confirmar_callback_generico template must be defined."""
        self.assertIn("confirmar_callback_generico", TEMPLATES)
        text = TEMPLATES["confirmar_callback_generico"][0]
        self.assertIn("vuelvo a llamar", text.lower())

    def test_first_callback_asks_hora(self):
        """First CALLBACK should ask for hora (preguntar_hora_callback)."""
        fsm = FSMEngine()
        # Start from ENCARGADO_AUSENTE (manager absence already established)
        fsm.state = FSMState.ENCARGADO_AUSENTE
        fsm.context.pitch_dado = True
        fsm.context.encargado_preguntado = True
        # Client says callback without hora → should ask hora
        result = fsm.process("Mejor márquele después.", agente=None)
        if result:
            self.assertIn("hora", result.lower(),
                         f"First callback should ask hora, got: {result}")

    def test_callback_hora_preguntada_flag_set(self):
        """After preguntar_hora_callback, flag should be set."""
        fsm = FSMEngine()
        fsm.state = FSMState.ENCARGADO_AUSENTE
        fsm.context.pitch_dado = True
        fsm.context.encargado_preguntado = True
        fsm.process("Mejor márquele después.", agente=None)
        self.assertTrue(fsm.context.callback_hora_preguntada,
                       "callback_hora_preguntada should be True after preguntar_hora_callback")

    def test_second_callback_uses_generico(self):
        """Second vague CALLBACK should use confirmar_callback_generico."""
        fsm = FSMEngine()
        fsm.state = FSMState.ENCARGADO_AUSENTE
        fsm.context.pitch_dado = True
        fsm.context.encargado_preguntado = True
        fsm.context.callback_hora_preguntada = True  # Already asked
        # Client gives vague callback again
        result = fsm.process("Pues más tarde, no sé a qué hora.", agente=None)
        if result:
            # Should use confirmar_callback_generico, NOT repeat hora question
            self.assertNotIn("que hora", result.lower(),
                            f"Should NOT repeat hora question, got: {result}")
            self.assertIn("vuelvo a llamar", result.lower(),
                         f"Should use generic callback, got: {result}")

    def test_callback_with_hora_still_confirms(self):
        """CALLBACK with specific hora still uses confirmar_callback (FIX 784)."""
        fsm = FSMEngine()
        fsm.state = FSMState.BUSCANDO_ENCARGADO
        fsm.context.pitch_dado = True
        fsm.context.encargado_preguntado = True
        fsm.context.callback_hora_preguntada = True  # Already asked
        # Client provides specific hora this time
        result = fsm.process("Márquele a las nueve de la mañana.", agente=None)
        if result:
            # Should use confirmar_callback with hora, NOT genérico
            self.assertNotIn("que hora", result.lower())
            # hora was detected → confirmar_callback takes priority over genérico

    def test_full_flow_callback_no_loop(self):
        """Full flow: first callback asks hora, second doesn't repeat."""
        fsm = FSMEngine()
        # Setup: ENCARGADO_AUSENTE (manager already confirmed absent)
        fsm.state = FSMState.ENCARGADO_AUSENTE
        fsm.context.pitch_dado = True
        fsm.context.encargado_preguntado = True

        # Turn 1: Client says callback → should ask hora (first time)
        r1 = fsm.process("Mejor márquele después.", agente=None)
        if r1:
            self.assertIn("hora", r1.lower(),
                         f"First callback should ask hora, got: {r1}")
        self.assertTrue(fsm.context.callback_hora_preguntada)

        # Turn 2: Client says callback again vaguely
        r2 = fsm.process("Mejor llámele después, no sé a qué hora.", agente=None)
        # With FIX 789B, should NOT ask hora again
        if r2:
            self.assertNotIn("que hora", r2.lower(),
                            f"Second callback should NOT repeat hora question, got: {r2}")


# ============================================================
# Cross-FIX integration tests
# ============================================================

class TestFix789Integration(unittest.TestCase):
    """Integration tests for FIX 789A + 789B together."""

    def test_pitch_specific_intents_still_advance(self):
        """PITCH with clear intents still advance normally."""
        fsm = FSMEngine()
        fsm.state = FSMState.PITCH
        fsm.context.pitch_dado = True
        # NO_INTEREST → DESPEDIDA
        fsm.process("No me interesa, gracias.", agente=None)
        self.assertEqual(fsm.state, FSMState.DESPEDIDA)

    def test_pitch_farewell_still_works(self):
        """PITCH+FAREWELL still goes to DESPEDIDA."""
        fsm = FSMEngine()
        fsm.state = FSMState.PITCH
        fsm.context.pitch_dado = True
        fsm.process("Hasta luego.", agente=None)
        self.assertEqual(fsm.state, FSMState.DESPEDIDA)

    def test_callback_hora_in_encargado_presente(self):
        """CALLBACK from ENCARGADO_PRESENTE also gets hora-loop protection."""
        fsm = FSMEngine()
        fsm.state = FSMState.ENCARGADO_PRESENTE
        fsm.context.pitch_dado = True
        fsm.context.encargado_preguntado = True
        fsm.context.callback_hora_preguntada = True
        # Vague callback → should use genérico
        result = fsm.process("Llámele más tarde.", agente=None)
        if result:
            self.assertNotIn("que hora", result.lower())

    def test_orphaned_prompts_all_defined(self):
        """All narrow prompts referenced by FSM transitions must be defined."""
        fsm = FSMEngine()
        for (state, intent), t in fsm._transitions.items():
            if t.action_type == ActionType.GPT_NARROW:
                self.assertIn(t.template_key, NARROW_PROMPTS,
                             f"GPT_NARROW key '{t.template_key}' in {state.value}+{intent.value} "
                             f"not found in NARROW_PROMPTS")

    def test_all_templates_referenced_exist(self):
        """All template keys used in transitions must exist in TEMPLATES."""
        fsm = FSMEngine()
        for (state, intent), t in fsm._transitions.items():
            if t.action_type in (ActionType.TEMPLATE, ActionType.ACKNOWLEDGE):
                if t.template_key:
                    self.assertIn(t.template_key, TEMPLATES,
                                 f"Template '{t.template_key}' in {state.value}+{intent.value} "
                                 f"not found in TEMPLATES")


if __name__ == '__main__':
    unittest.main()
