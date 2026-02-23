"""
Tests for FIX 780 + FIX 781 + FIX 782.

FIX 780: Time context guard - "llegan en una hora" no es dictado parcial.
FIX 781: Email check ANTES de dictating check - email con números no es dictado.
FIX 782: Deepgram stats guardadas para diagnóstico post-cierre.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from fsm_engine import classify_intent, FSMIntent, FSMContext, FSMState, FSMEngine


# ============================================================
# FIX 780: Time context guard
# ============================================================

class TestFix780TimeContextGuard(unittest.TestCase):
    """FIX 780: Frases temporales con números no son dictado parcial."""

    def _ctx(self):
        ctx = FSMContext()
        ctx.encargado_preguntado = True
        ctx.pitch_dado = True
        return ctx

    def test_llegan_en_una_hora_not_dictating(self):
        """'Ellos llegan en una hora' should NOT be DICTATING_PARTIAL."""
        intent = classify_intent(
            "Ellos llegan ahorita como en una hora",
            self._ctx(), FSMState.BUSCANDO_ENCARGADO
        )
        self.assertNotEqual(intent, FSMIntent.DICTATING_PARTIAL,
                          "Time phrase should not be classified as dictating")

    def test_como_en_una_hora_not_dictating(self):
        """'como en una hora llegan ellos aquí' should NOT be DICTATING_PARTIAL."""
        intent = classify_intent(
            "como en una hora llegan ellos aquí.",
            self._ctx(), FSMState.BUSCANDO_ENCARGADO
        )
        self.assertNotEqual(intent, FSMIntent.DICTATING_PARTIAL)

    def test_en_un_rato_not_dictating(self):
        """'en un rato' should NOT be DICTATING_PARTIAL."""
        intent = classify_intent(
            "llega en un rato más",
            self._ctx(), FSMState.BUSCANDO_ENCARGADO
        )
        self.assertNotEqual(intent, FSMIntent.DICTATING_PARTIAL)

    def test_en_dos_horas_not_dictating(self):
        """'en dos horas' should NOT be DICTATING_PARTIAL."""
        intent = classify_intent(
            "llega en dos horas",
            self._ctx(), FSMState.BUSCANDO_ENCARGADO
        )
        self.assertNotEqual(intent, FSMIntent.DICTATING_PARTIAL)

    def test_en_la_tarde_not_dictating(self):
        """'viene en la tarde como a las tres' should NOT be DICTATING_PARTIAL."""
        intent = classify_intent(
            "viene en la tarde como a las tres",
            self._ctx(), FSMState.BUSCANDO_ENCARGADO
        )
        self.assertNotEqual(intent, FSMIntent.DICTATING_PARTIAL)

    def test_manana_a_las_nueve_not_dictating(self):
        """'mañana a las nueve' should NOT be DICTATING_PARTIAL in BUSCANDO_ENCARGADO."""
        intent = classify_intent(
            "mañana a las nueve",
            self._ctx(), FSMState.BUSCANDO_ENCARGADO
        )
        self.assertNotEqual(intent, FSMIntent.DICTATING_PARTIAL)

    def test_real_dictation_still_works_buscando(self):
        """Real phone dictation still works in BUSCANDO_ENCARGADO."""
        intent = classify_intent(
            "seis uno cuatro tres ocho dos",
            self._ctx(), FSMState.BUSCANDO_ENCARGADO
        )
        self.assertEqual(intent, FSMIntent.DICTATING_PARTIAL)

    def test_real_dictation_still_works_dictando(self):
        """Real phone dictation in DICTANDO_DATO not affected by time guard."""
        intent = classify_intent(
            "tres tres uno ocho siete seis",
            self._ctx(), FSMState.DICTANDO_DATO
        )
        self.assertEqual(intent, FSMIntent.DICTATING_PARTIAL)

    def test_complete_phone_still_works(self):
        """10-digit phone number still detected as COMPLETE_PHONE."""
        intent = classify_intent(
            "6141234567",
            self._ctx(), FSMState.BUSCANDO_ENCARGADO
        )
        self.assertEqual(intent, FSMIntent.DICTATING_COMPLETE_PHONE)

    def test_time_context_in_dictando_dato_still_dictating(self):
        """In DICTANDO_DATO, 'una hora' with other digits is still dictation."""
        intent = classify_intent(
            "tres tres uno",
            self._ctx(), FSMState.DICTANDO_DATO
        )
        self.assertEqual(intent, FSMIntent.DICTATING_PARTIAL)


# ============================================================
# FIX 781: Email check before dictating
# ============================================================

class TestFix781EmailBeforeDictating(unittest.TestCase):
    """FIX 781: Email detection runs before digit counting."""

    def _ctx(self):
        ctx = FSMContext()
        ctx.encargado_preguntado = True
        ctx.pitch_dado = True
        return ctx

    def test_email_with_numbers_detected(self):
        """'Ferrebillas seis cuatro arroba gmail punto com' = COMPLETE_EMAIL."""
        intent = classify_intent(
            "Ferrebillas seis cuatro arroba gmail punto com",
            self._ctx(), FSMState.DICTANDO_DATO
        )
        self.assertEqual(intent, FSMIntent.DICTATING_COMPLETE_EMAIL)

    def test_email_with_at_symbol(self):
        """'test64@gmail.com' = COMPLETE_EMAIL (not dictating_partial)."""
        intent = classify_intent(
            "test64@gmail.com",
            self._ctx(), FSMState.DICTANDO_DATO
        )
        self.assertEqual(intent, FSMIntent.DICTATING_COMPLETE_EMAIL)

    def test_email_arroba_gmail(self):
        """'arroba gmail' without numbers = COMPLETE_EMAIL."""
        intent = classify_intent(
            "ferrebillas arroba gmail punto com",
            self._ctx(), FSMState.BUSCANDO_ENCARGADO
        )
        self.assertEqual(intent, FSMIntent.DICTATING_COMPLETE_EMAIL)

    def test_email_arroba_hotmail(self):
        """'arroba hotmail' = COMPLETE_EMAIL."""
        intent = classify_intent(
            "juan arroba hotmail punto com",
            self._ctx(), FSMState.DICTANDO_DATO
        )
        self.assertEqual(intent, FSMIntent.DICTATING_COMPLETE_EMAIL)

    def test_email_signal_without_complete(self):
        """'gmail' alone = OFFER_DATA (email signal, not complete)."""
        intent = classify_intent(
            "es de gmail",
            self._ctx(), FSMState.BUSCANDO_ENCARGADO
        )
        self.assertEqual(intent, FSMIntent.OFFER_DATA)

    def test_email_with_digits_and_arroba(self):
        """Email with many digits and arroba still detected."""
        intent = classify_intent(
            "seis cuatro arroba gmail punto com",
            self._ctx(), FSMState.DICTANDO_DATO
        )
        self.assertEqual(intent, FSMIntent.DICTATING_COMPLETE_EMAIL)

    def test_pure_digits_not_email(self):
        """Pure digits without email signals = DICTATING_PARTIAL."""
        intent = classify_intent(
            "seis uno cuatro tres ocho dos",
            self._ctx(), FSMState.DICTANDO_DATO
        )
        self.assertEqual(intent, FSMIntent.DICTATING_PARTIAL)


# ============================================================
# FIX 782: Deepgram stats preservation
# ============================================================

class TestFix782DeepgramStats(unittest.TestCase):
    """FIX 782: Stats preserved after transcriber deletion."""

    def test_deepgram_has_last_stats_function(self):
        """deepgram_transcriber must export obtener_last_stats."""
        dg_path = os.path.join(os.path.dirname(__file__), '..', 'deepgram_transcriber.py')
        with open(dg_path, 'r', encoding='utf-8') as f:
            source = f.read()
        self.assertIn('def obtener_last_stats', source)
        self.assertIn('_transcriber_last_stats', source)
        self.assertIn('FIX 782', source)

    def test_servidor_imports_last_stats(self):
        """servidor_llamadas must import obtener_last_stats."""
        srv_path = os.path.join(os.path.dirname(__file__), '..', 'servidor_llamadas.py')
        with open(srv_path, 'r', encoding='utf-8') as f:
            source = f.read()
        self.assertIn('obtener_last_stats', source)
        self.assertIn('FIX 782', source)

    def test_servidor_diagnostic_uses_last_stats(self):
        """servidor_llamadas diagnostic section uses last stats as fallback."""
        srv_path = os.path.join(os.path.dirname(__file__), '..', 'servidor_llamadas.py')
        with open(srv_path, 'r', encoding='utf-8') as f:
            source = f.read()
        self.assertIn('cerrado (WebSocket', source)
        self.assertIn('nunca inicializado', source)


# ============================================================
# Integration: FSM flow after FIX 780+781
# ============================================================

class TestFix780781Integration(unittest.TestCase):
    """Integration: Full FSM flow correctness."""

    def test_hora_in_buscando_goes_to_callback(self):
        """'llegan en una hora' in BUSCANDO_ENCARGADO should become callback or unknown."""
        fsm = FSMEngine()
        fsm.state = FSMState.BUSCANDO_ENCARGADO
        fsm.context.pitch_dado = True
        fsm.context.encargado_preguntado = True
        result = fsm.process("Ellos llegan ahorita como en una hora", agente=None)
        # Should NOT be in DICTANDO_DATO
        self.assertNotEqual(fsm.state, FSMState.DICTANDO_DATO,
                          "Time phrase should not transition to DICTANDO_DATO")

    def test_email_in_buscando_goes_to_capturado(self):
        """Email dictation in BUSCANDO_ENCARGADO → CONTACTO_CAPTURADO."""
        fsm = FSMEngine()
        fsm.state = FSMState.BUSCANDO_ENCARGADO
        fsm.context.pitch_dado = True
        result = fsm.process("ferrebillas64 arroba gmail punto com", agente=None)
        self.assertEqual(fsm.state, FSMState.CONTACTO_CAPTURADO)

    def test_email_in_dictando_goes_to_capturado(self):
        """Email in DICTANDO_DATO → CONTACTO_CAPTURADO."""
        fsm = FSMEngine()
        fsm.state = FSMState.DICTANDO_DATO
        result = fsm.process("juan arroba hotmail punto com", agente=None)
        self.assertEqual(fsm.state, FSMState.CONTACTO_CAPTURADO)

    def test_digits_in_dictando_stay_dictating(self):
        """Partial digits in DICTANDO_DATO stay in DICTANDO_DATO."""
        fsm = FSMEngine()
        fsm.state = FSMState.DICTANDO_DATO
        result = fsm.process("tres tres uno ocho", agente=None)
        self.assertEqual(fsm.state, FSMState.DICTANDO_DATO)


if __name__ == '__main__':
    unittest.main()
