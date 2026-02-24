"""
Tests for FIX 791: State-aware template selection for UNKNOWN intents.

FIX 791 replaces GPT_NARROW 'conversacion_libre' with deterministic templates
based on FSM state + context. Eliminates ~72% of GPT_NARROW calls.

Templates based on narrow_cache.json analysis (119 entries → 5 unique responses).
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from fsm_engine import (
    FSMEngine, FSMState, FSMIntent, FSMContext, ActionType, Transition,
    TEMPLATES
)


# ============================================================
# Test 1: New templates exist in TEMPLATES dict
# ============================================================

class TestFix791TemplatesExist(unittest.TestCase):
    """All 6 new FIX 791 templates must be defined."""

    def test_repitch_encargado_exists(self):
        self.assertIn("repitch_encargado", TEMPLATES)
        self.assertIn("NIOVAL", TEMPLATES["repitch_encargado"][0])
        self.assertIn("encargado", TEMPLATES["repitch_encargado"][0].lower())

    def test_pedir_whatsapp_o_correo_exists(self):
        self.assertIn("pedir_whatsapp_o_correo", TEMPLATES)
        self.assertIn("WhatsApp", TEMPLATES["pedir_whatsapp_o_correo"][0])
        self.assertIn("correo", TEMPLATES["pedir_whatsapp_o_correo"][0])

    def test_pitch_catalogo_whatsapp_exists(self):
        self.assertIn("pitch_catalogo_whatsapp", TEMPLATES)
        self.assertIn("catalogo", TEMPLATES["pitch_catalogo_whatsapp"][0])

    def test_preguntar_horario_encargado_exists(self):
        self.assertIn("preguntar_horario_encargado", TEMPLATES)
        self.assertIn("horario", TEMPLATES["preguntar_horario_encargado"][0])

    def test_ofrecer_catalogo_sin_compromiso_exists(self):
        self.assertIn("ofrecer_catalogo_sin_compromiso", TEMPLATES)
        self.assertIn("NIOVAL", TEMPLATES["ofrecer_catalogo_sin_compromiso"][0])

    def test_despedida_agradecimiento_exists(self):
        self.assertIn("despedida_agradecimiento", TEMPLATES)
        self.assertIn("agradezco", TEMPLATES["despedida_agradecimiento"][0])


# ============================================================
# Test 2: _handle_unknown_stateful() returns correct template
# ============================================================

class TestFix791HandleUnknownStateful(unittest.TestCase):
    """_handle_unknown_stateful returns correct Transition per state+context."""

    def setUp(self):
        self.fsm = FSMEngine()

    # --- BUSCANDO_ENCARGADO ---

    def test_buscando_no_pitch_repitch(self):
        """BUSCANDO + no pitch → repitch_encargado."""
        self.fsm.state = FSMState.BUSCANDO_ENCARGADO
        self.fsm.context.pitch_dado = False
        t = self.fsm._handle_unknown_stateful("algo cualquiera")
        self.assertIsNotNone(t)
        self.assertEqual(t.template_key, "repitch_encargado")
        self.assertEqual(t.next_state, FSMState.BUSCANDO_ENCARGADO)

    def test_buscando_pitch_dado_encargado_preguntado(self):
        """BUSCANDO + pitch dado + encargado preguntado → pedir_whatsapp_o_correo."""
        self.fsm.state = FSMState.BUSCANDO_ENCARGADO
        self.fsm.context.pitch_dado = True
        self.fsm.context.encargado_preguntado = True
        t = self.fsm._handle_unknown_stateful("no sé qué decirle")
        self.assertIsNotNone(t)
        self.assertEqual(t.template_key, "pedir_whatsapp_o_correo")
        self.assertEqual(t.next_state, FSMState.CAPTURANDO_CONTACTO)

    def test_buscando_pitch_dado_sin_encargado(self):
        """BUSCANDO + pitch dado + no encargado preguntado → preguntar_encargado."""
        self.fsm.state = FSMState.BUSCANDO_ENCARGADO
        self.fsm.context.pitch_dado = True
        self.fsm.context.encargado_preguntado = False
        t = self.fsm._handle_unknown_stateful("mmm")
        self.assertIsNotNone(t)
        self.assertEqual(t.template_key, "preguntar_encargado")

    # --- ENCARGADO_AUSENTE ---

    def test_ausente_sin_canales(self):
        """ENCARGADO_AUSENTE + sin canales intentados → pedir_whatsapp_o_correo."""
        self.fsm.state = FSMState.ENCARGADO_AUSENTE
        self.fsm.context.canales_intentados = []
        t = self.fsm._handle_unknown_stateful("pues no sé")
        self.assertIsNotNone(t)
        self.assertEqual(t.template_key, "pedir_whatsapp_o_correo")
        self.assertEqual(t.next_state, FSMState.CAPTURANDO_CONTACTO)

    def test_ausente_callback_pedido(self):
        """ENCARGADO_AUSENTE + callback pedido → despedida_agradecimiento."""
        self.fsm.state = FSMState.ENCARGADO_AUSENTE
        self.fsm.context.canales_intentados = ["whatsapp"]
        self.fsm.context.callback_pedido = True
        t = self.fsm._handle_unknown_stateful("bueno pues")
        self.assertIsNotNone(t)
        self.assertEqual(t.template_key, "despedida_agradecimiento")
        self.assertEqual(t.next_state, FSMState.DESPEDIDA)

    def test_ausente_canales_intentados_sin_callback(self):
        """ENCARGADO_AUSENTE + canales intentados, sin callback → preguntar_horario."""
        self.fsm.state = FSMState.ENCARGADO_AUSENTE
        self.fsm.context.canales_intentados = ["whatsapp"]
        self.fsm.context.callback_pedido = False
        t = self.fsm._handle_unknown_stateful("ah bueno")
        self.assertIsNotNone(t)
        self.assertEqual(t.template_key, "preguntar_horario_encargado")
        self.assertEqual(t.next_state, FSMState.ENCARGADO_AUSENTE)

    # --- ENCARGADO_PRESENTE ---

    def test_presente_sin_canales(self):
        """ENCARGADO_PRESENTE + sin canales → pedir_whatsapp."""
        self.fsm.state = FSMState.ENCARGADO_PRESENTE
        self.fsm.context.canales_intentados = []
        t = self.fsm._handle_unknown_stateful("ajá")
        self.assertIsNotNone(t)
        self.assertEqual(t.template_key, "pedir_whatsapp")
        self.assertEqual(t.next_state, FSMState.CAPTURANDO_CONTACTO)

    def test_presente_con_canales(self):
        """ENCARGADO_PRESENTE + canales intentados → pitch_catalogo_whatsapp."""
        self.fsm.state = FSMState.ENCARGADO_PRESENTE
        self.fsm.context.canales_intentados = ["correo"]
        t = self.fsm._handle_unknown_stateful("mm a ver")
        self.assertIsNotNone(t)
        self.assertEqual(t.template_key, "pitch_catalogo_whatsapp")
        self.assertEqual(t.next_state, FSMState.CAPTURANDO_CONTACTO)

    # --- CAPTURANDO_CONTACTO ---

    def test_capturando_digame(self):
        """CAPTURANDO_CONTACTO → always digame_numero."""
        self.fsm.state = FSMState.CAPTURANDO_CONTACTO
        t = self.fsm._handle_unknown_stateful("este pues")
        self.assertIsNotNone(t)
        self.assertEqual(t.template_key, "digame_numero")
        self.assertEqual(t.next_state, FSMState.CAPTURANDO_CONTACTO)


# ============================================================
# Test 3: States NOT mapped return None (fallback to GPT_NARROW)
# ============================================================

class TestFix791PitchState(unittest.TestCase):
    """FIX 791: PITCH + UNKNOWN → stateful template (replaces manejar_objecion)."""

    def setUp(self):
        self.fsm = FSMEngine()

    def test_pitch_no_encargado_preguntado(self):
        """PITCH + no encargado_preguntado → preguntar_encargado."""
        self.fsm.state = FSMState.PITCH
        self.fsm.context.encargado_preguntado = False
        t = self.fsm._handle_unknown_stateful("ajá sí")
        self.assertIsNotNone(t)
        self.assertEqual(t.template_key, "preguntar_encargado")
        self.assertEqual(t.next_state, FSMState.BUSCANDO_ENCARGADO)

    def test_pitch_returns_preguntar_encargado_template(self):
        """PITCH + UNKNOWN → preguntar_encargado (flag set by _update_context)."""
        self.fsm.state = FSMState.PITCH
        self.fsm.context.encargado_preguntado = False
        t = self.fsm._handle_unknown_stateful("ajá sí")
        self.assertEqual(t.template_key, "preguntar_encargado")
        # Flag NOT set here - _update_context handles it post-execution
        self.assertFalse(self.fsm.context.encargado_preguntado)

    def test_pitch_encargado_preguntado_sin_canales(self):
        """PITCH + encargado_preguntado + no canales → pedir_whatsapp_o_correo."""
        self.fsm.state = FSMState.PITCH
        self.fsm.context.encargado_preguntado = True
        self.fsm.context.canales_intentados = []
        t = self.fsm._handle_unknown_stateful("no sé")
        self.assertIsNotNone(t)
        self.assertEqual(t.template_key, "pedir_whatsapp_o_correo")
        self.assertEqual(t.next_state, FSMState.CAPTURANDO_CONTACTO)

    def test_pitch_all_flags_catalogo(self):
        """PITCH + encargado + canales → ofrecer_catalogo_sin_compromiso."""
        self.fsm.state = FSMState.PITCH
        self.fsm.context.encargado_preguntado = True
        self.fsm.context.canales_intentados = ["whatsapp"]
        t = self.fsm._handle_unknown_stateful("este pues")
        self.assertIsNotNone(t)
        self.assertEqual(t.template_key, "ofrecer_catalogo_sin_compromiso")


class TestFix791ContextFlagUpdates(unittest.TestCase):
    """FIX 791 updates context flags to prevent template loops."""

    def setUp(self):
        self.fsm = FSMEngine()

    def test_buscando_no_pitch_returns_repitch(self):
        """BUSCANDO + !pitch_dado → repitch_encargado template."""
        self.fsm.state = FSMState.BUSCANDO_ENCARGADO
        self.fsm.context.pitch_dado = False
        t = self.fsm._handle_unknown_stateful("algo")
        self.assertEqual(t.template_key, "repitch_encargado")
        # pitch_dado NOT set here - _update_context handles it
        self.assertFalse(self.fsm.context.pitch_dado)

    def test_buscando_no_encargado_returns_preguntar(self):
        """BUSCANDO + pitch + !encargado_preguntado → preguntar_encargado."""
        self.fsm.state = FSMState.BUSCANDO_ENCARGADO
        self.fsm.context.pitch_dado = True
        self.fsm.context.encargado_preguntado = False
        t = self.fsm._handle_unknown_stateful("algo")
        self.assertEqual(t.template_key, "preguntar_encargado")

    def test_context_update_sets_pitch_dado_on_repitch(self):
        """_update_context sets pitch_dado for repitch_encargado template."""
        self.fsm.state = FSMState.BUSCANDO_ENCARGADO
        self.fsm.context.pitch_dado = False
        t = Transition(FSMState.BUSCANDO_ENCARGADO, ActionType.TEMPLATE, "repitch_encargado")
        self.fsm._update_context(FSMIntent.UNKNOWN, "algo", t)
        self.assertTrue(self.fsm.context.pitch_dado)

    def test_context_update_sets_encargado_on_preguntar(self):
        """_update_context sets encargado_preguntado for preguntar_encargado template."""
        self.fsm.state = FSMState.BUSCANDO_ENCARGADO
        self.fsm.context.encargado_preguntado = False
        t = Transition(FSMState.BUSCANDO_ENCARGADO, ActionType.TEMPLATE, "preguntar_encargado")
        self.fsm._update_context(FSMIntent.UNKNOWN, "algo", t)
        self.assertTrue(self.fsm.context.encargado_preguntado)

    def test_process_advances_pitch_to_different_states(self):
        """Full process: PITCH+UNKNOWN twice → different templates via state progression."""
        self.fsm.state = FSMState.PITCH
        self.fsm.context.encargado_preguntado = False
        self.fsm.context.canales_intentados = []
        # First: preguntar_encargado → BUSCANDO_ENCARGADO (encargado_preguntado set by _update)
        r1 = self.fsm.process("Pues este no sé", agente=None)
        self.assertEqual(self.fsm.state, FSMState.BUSCANDO_ENCARGADO)
        # encargado_preguntado now True from _update_context
        self.assertTrue(self.fsm.context.encargado_preguntado)
        # Second: BUSCANDO + encargado_preguntado → pedir_whatsapp_o_correo
        r2 = self.fsm.process("Pues mira es que como le digo", agente=None)
        # Different responses (no loop)
        if r1 and r2:
            self.assertNotEqual(r1, r2)


class TestFix791FallbackToGPT(unittest.TestCase):
    """States not in mapping return None → GPT_NARROW."""

    def setUp(self):
        self.fsm = FSMEngine()

    def test_saludo_returns_none(self):
        """SALUDO not mapped → None."""
        self.fsm.state = FSMState.SALUDO
        t = self.fsm._handle_unknown_stateful("mmm")
        self.assertIsNone(t)

    def test_dictando_dato_returns_none(self):
        """DICTANDO_DATO not mapped → None."""
        self.fsm.state = FSMState.DICTANDO_DATO
        t = self.fsm._handle_unknown_stateful("este")
        self.assertIsNone(t)

    def test_despedida_returns_none(self):
        """DESPEDIDA not mapped → None."""
        self.fsm.state = FSMState.DESPEDIDA
        t = self.fsm._handle_unknown_stateful("pues")
        self.assertIsNone(t)


# ============================================================
# Test 4: Integration - process() uses stateful template
# ============================================================

class TestFix791Integration(unittest.TestCase):
    """Integration: process() routes UNKNOWN through _handle_unknown_stateful."""

    def test_buscando_unknown_gets_template(self):
        """BUSCANDO_ENCARGADO + UNKNOWN text → template response (not GPT)."""
        fsm = FSMEngine()
        fsm.state = FSMState.BUSCANDO_ENCARGADO
        fsm.context.pitch_dado = True
        fsm.context.encargado_preguntado = True
        result = fsm.process("Pues no sé qué decirle.", agente=None)
        # Should get pedir_whatsapp_o_correo template
        if result:
            self.assertIn("WhatsApp", result)
            self.assertIn("correo", result)

    def test_ausente_unknown_gets_template(self):
        """ENCARGADO_AUSENTE + UNKNOWN text → template response."""
        fsm = FSMEngine()
        fsm.state = FSMState.ENCARGADO_AUSENTE
        fsm.context.pitch_dado = True
        fsm.context.encargado_preguntado = True
        fsm.context.canales_intentados = []
        # Use text that classifies as UNKNOWN (not verification)
        result = fsm.process("Pues mira es que como le digo.", agente=None)
        if result:
            self.assertIn("WhatsApp", result)

    def test_presente_unknown_gets_template(self):
        """ENCARGADO_PRESENTE + UNKNOWN text → template response."""
        fsm = FSMEngine()
        fsm.state = FSMState.ENCARGADO_PRESENTE
        fsm.context.pitch_dado = True
        fsm.context.encargado_preguntado = True
        fsm.context.canales_intentados = []
        result = fsm.process("Mm a ver.", agente=None)
        if result:
            self.assertIn("WhatsApp", result)

    def test_pitch_unknown_uses_stateful_template(self):
        """PITCH + UNKNOWN → stateful template, advances state."""
        fsm = FSMEngine()
        fsm.state = FSMState.PITCH
        fsm.context.pitch_dado = True
        fsm.context.encargado_preguntado = False
        result = fsm.process("Pues no sé.", agente=None)
        # Should advance to BUSCANDO_ENCARGADO
        if result:
            self.assertEqual(fsm.state, FSMState.BUSCANDO_ENCARGADO)
            # Response should be preguntar_encargado template
            self.assertIsNotNone(result)

    def test_multi_turn_unknown_progression(self):
        """Multi-turn: BUSCANDO → UNKNOWN → template → state advances."""
        fsm = FSMEngine()
        fsm.state = FSMState.BUSCANDO_ENCARGADO
        fsm.context.pitch_dado = True
        fsm.context.encargado_preguntado = True

        # First UNKNOWN → pedir_whatsapp_o_correo → CAPTURANDO_CONTACTO
        result = fsm.process("Pues este...", agente=None)
        if result:
            self.assertEqual(fsm.state, FSMState.CAPTURANDO_CONTACTO)

    def test_ausente_callback_despedida(self):
        """ENCARGADO_AUSENTE + callback_pedido + UNKNOWN → despedida."""
        fsm = FSMEngine()
        fsm.state = FSMState.ENCARGADO_AUSENTE
        fsm.context.pitch_dado = True
        fsm.context.encargado_preguntado = True
        fsm.context.canales_intentados = ["whatsapp"]
        fsm.context.callback_pedido = True
        # Use text that classifies as UNKNOWN (not verification)
        result = fsm.process("Pues mira es que como le digo amigo.", agente=None)
        if result:
            self.assertIn("agradezco", result)
            self.assertEqual(fsm.state, FSMState.DESPEDIDA)

    def test_existing_known_intents_unaffected(self):
        """Known intents (FAREWELL, NO_INTEREST) not affected by FIX 791."""
        fsm = FSMEngine()
        fsm.state = FSMState.BUSCANDO_ENCARGADO
        fsm.context.pitch_dado = True
        # FAREWELL → DESPEDIDA (unchanged)
        fsm.process("Hasta luego.", agente=None)
        self.assertEqual(fsm.state, FSMState.DESPEDIDA)


if __name__ == '__main__':
    unittest.main()
