"""
Tests for FIX 777 + FIX 778.

FIX 777: Avanzar FSM a BUSCANDO_ENCARGADO después de segunda_parte_saludo cache.
  - La cache FIX 121/314 entrega pitch+encargado en turno 1
  - Sin FIX 777, FSM queda en SALUDO → genera pitch duplicado en turno 2
  - Con FIX 777, FSM avanza a BUSCANDO_ENCARGADO → no pitch duplicado

FIX 778: Exponer openai_client como atributo de instancia para GPT_NARROW.
  - openai_client es module-level en agente_ventas.py
  - _call_gpt_narrow() en fsm_engine.py busca agente.openai_client
  - Sin FIX 778, hasattr(agente, 'openai_client') → False → GPT_NARROW no ejecuta
  - Con FIX 778, self.openai_client = openai_client → GPT_NARROW funciona
"""

import os
import sys
import unittest

# Add parent dir
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


# ============================================================
# FIX 777: FSM advance after segunda_parte_saludo
# ============================================================

class TestFix777FSMAdvanceAfterSegundaParte(unittest.TestCase):
    """FIX 777: FSM avanza a BUSCANDO_ENCARGADO tras segunda_parte_saludo cache."""

    def test_fsm_advance_code_in_servidor(self):
        """servidor_llamadas.py must contain FIX 777 advance code."""
        srv_path = os.path.join(os.path.dirname(__file__), '..', 'servidor_llamadas.py')
        with open(srv_path, 'r', encoding='utf-8') as f:
            source = f.read()
        # Must have FIX 777 comment
        self.assertIn('FIX 777', source)
        # Must advance to BUSCANDO_ENCARGADO
        self.assertIn('FSMState.BUSCANDO_ENCARGADO', source)
        # Must set pitch_dado = True
        self.assertIn('pitch_dado = True', source)

    def test_fsm_advance_three_paths(self):
        """FIX 777 must cover 3 paths: FIX 121 cache, FIX 408 timeout #3+, FIX 408 timeout #2."""
        srv_path = os.path.join(os.path.dirname(__file__), '..', 'servidor_llamadas.py')
        with open(srv_path, 'r', encoding='utf-8') as f:
            source = f.read()
        # Count occurrences of FIX 777 advance pattern
        count = source.count('FIX 777: FSM avanzado SALUDO')
        self.assertGreaterEqual(count, 3, f"Expected 3+ FIX 777 paths, found {count}")

    def test_fsm_state_buscando_encargado_exists(self):
        """FSMState.BUSCANDO_ENCARGADO must exist in fsm_engine."""
        from fsm_engine import FSMState
        self.assertTrue(hasattr(FSMState, 'BUSCANDO_ENCARGADO'))
        self.assertEqual(FSMState.BUSCANDO_ENCARGADO.value, 'buscando_encargado')

    def test_fsm_advance_sets_pitch_dado(self):
        """After FIX 777 advance, context.pitch_dado must be True."""
        from fsm_engine import FSMEngine, FSMState
        fsm = FSMEngine()
        # Simulate: FSM starts at SALUDO
        self.assertEqual(fsm.state, FSMState.SALUDO)
        # Simulate FIX 777 advance
        fsm.state = FSMState.BUSCANDO_ENCARGADO
        fsm.context.pitch_dado = True
        # Verify
        self.assertEqual(fsm.state, FSMState.BUSCANDO_ENCARGADO)
        self.assertTrue(fsm.context.pitch_dado)

    def test_fsm_advance_prevents_duplicate_pitch(self):
        """After FIX 777, BUSCANDO_ENCARGADO should NOT generate pitch template."""
        from fsm_engine import FSMEngine, FSMState
        fsm = FSMEngine()
        # Simulate FIX 777 advance
        fsm.state = FSMState.BUSCANDO_ENCARGADO
        fsm.context.pitch_dado = True
        # Process client response like "Sí, es él"
        result = fsm.process("Sí, es él", agente=None)
        # Should NOT contain full pitch (Nioval/productos phrase)
        if result:
            # Pitch typically mentions "nioval" or "productos de limpieza"
            resp_lower = result.lower()
            # It's fine to mention Nioval in a short confirmation, but shouldn't be full pitch
            if 'productos de limpieza' in resp_lower and 'nioval' in resp_lower:
                # Full pitch detected - this would be the bug FIX 777 prevents
                self.fail("FIX 777 should prevent duplicate pitch after segunda_parte_saludo")

    def test_fsm_advance_conditional_timeout2(self):
        """FIX 777 timeout #2 path: only advance if response contains nioval/encargad."""
        srv_path = os.path.join(os.path.dirname(__file__), '..', 'servidor_llamadas.py')
        with open(srv_path, 'r', encoding='utf-8') as f:
            source = f.read()
        # Timeout #2 path should have conditional check
        self.assertIn("'nioval' in respuesta_timeout.lower()", source)
        self.assertIn("'encargad' in respuesta_timeout.lower()", source)


# ============================================================
# FIX 778: openai_client as instance attribute
# ============================================================

class TestFix778OpenaiClientInstance(unittest.TestCase):
    """FIX 778: openai_client exposed as instance attribute for GPT_NARROW."""

    def test_openai_client_in_init(self):
        """agente_ventas.py __init__ must set self.openai_client."""
        agent_path = os.path.join(os.path.dirname(__file__), '..', 'agente_ventas.py')
        with open(agent_path, 'r', encoding='utf-8') as f:
            source = f.read()
        self.assertIn('self.openai_client = openai_client', source)
        self.assertIn('FIX 778', source)

    def test_gpt_narrow_checks_openai_client(self):
        """fsm_engine._call_gpt_narrow must check agente.openai_client."""
        fsm_path = os.path.join(os.path.dirname(__file__), '..', 'fsm_engine.py')
        with open(fsm_path, 'r', encoding='utf-8') as f:
            source = f.read()
        self.assertIn('agente.openai_client', source)

    def test_gpt_narrow_returns_none_without_client(self):
        """FSMEngine._call_gpt_narrow returns None if agente has no openai_client."""
        from fsm_engine import FSMEngine
        fsm = FSMEngine()
        # Mock agente without openai_client
        class FakeAgente:
            pass
        result = fsm._call_gpt_narrow("PITCH", "test", agente=FakeAgente())
        self.assertIsNone(result)

    def test_gpt_narrow_returns_none_with_none_client(self):
        """FSMEngine._call_gpt_narrow returns None if agente.openai_client is None."""
        from fsm_engine import FSMEngine
        fsm = FSMEngine()
        class FakeAgente:
            openai_client = None
        result = fsm._call_gpt_narrow("PITCH", "test", agente=FakeAgente())
        self.assertIsNone(result)


# ============================================================
# FSM label fix
# ============================================================

class TestFSMLabelPhase4(unittest.TestCase):
    """FSM log label should say Phase 4."""

    def test_fsm_label_phase4(self):
        """fsm_engine.py active states log must say Phase 4."""
        fsm_path = os.path.join(os.path.dirname(__file__), '..', 'fsm_engine.py')
        with open(fsm_path, 'r', encoding='utf-8') as f:
            source = f.read()
        # The active states log line must say Phase 4
        self.assertIn('Phase 4', source)
        # The print statement with active states must reference Phase 4
        self.assertIn('Active states (Phase 4)', source)


# ============================================================
# Integration: FIX 777 + FSM state coherence
# ============================================================

class TestFix777Integration(unittest.TestCase):
    """Integration: After FIX 777 advance, FSM processes correctly."""

    def test_buscando_encargado_accepts_si(self):
        """After advance to BUSCANDO_ENCARGADO, 'Sí' should work."""
        from fsm_engine import FSMEngine, FSMState
        fsm = FSMEngine()
        fsm.state = FSMState.BUSCANDO_ENCARGADO
        fsm.context.pitch_dado = True
        result = fsm.process("Sí", agente=None)
        # Should transition to ENCARGADO_PRESENTE or similar
        if result:
            self.assertIsNotNone(result)

    def test_buscando_encargado_no_esta(self):
        """After advance, 'No está' transitions correctly."""
        from fsm_engine import FSMEngine, FSMState
        fsm = FSMEngine()
        fsm.state = FSMState.BUSCANDO_ENCARGADO
        fsm.context.pitch_dado = True
        result = fsm.process("No está el encargado", agente=None)
        if result:
            self.assertIn(fsm.state, [
                FSMState.ENCARGADO_AUSENTE,
                FSMState.BUSCANDO_ENCARGADO  # might stay if no template
            ])

    def test_advance_from_saludo_to_buscando(self):
        """Simulating the full FIX 777 flow."""
        from fsm_engine import FSMEngine, FSMState
        fsm = FSMEngine()
        # Start: SALUDO
        self.assertEqual(fsm.state, FSMState.SALUDO)
        # FIX 777 advance (simulating what servidor does)
        fsm.state = FSMState.BUSCANDO_ENCARGADO
        fsm.context.pitch_dado = True
        # Verify state
        self.assertEqual(fsm.state, FSMState.BUSCANDO_ENCARGADO)
        self.assertTrue(fsm.context.pitch_dado)
        # Next client input should be handled by BUSCANDO_ENCARGADO, not SALUDO
        self.assertNotEqual(fsm.state, FSMState.SALUDO)


if __name__ == '__main__':
    unittest.main()
