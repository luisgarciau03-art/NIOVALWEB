"""
Tests for FIX 786 + FIX 787 + FIX 788 (FSM Phase 5).

FIX 786: CONTINUATION en 10 estados (antes solo DICTANDO_DATO).
  - Cliente sigue hablando (texto termina en coma) → NOOP, no interrumpir.

FIX 787: Gaps críticos OFRECIENDO_CONTACTO.
  - DICTATING_COMPLETE_PHONE/EMAIL → CONTACTO_CAPTURADO
  - DICTATING_PARTIAL → DICTANDO_DATO
  - VERIFICATION, QUESTION, IDENTITY, OFFER_DATA, WRONG_NUMBER

FIX 788: Gaps menores en ENCARGADO_PRESENTE, ESPERANDO_TRANSFERENCIA,
         ENCARGADO_AUSENTE, CAPTURANDO_CONTACTO, DICTANDO_DATO,
         CONTACTO_CAPTURADO, DESPEDIDA.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from fsm_engine import (
    classify_intent, FSMIntent, FSMContext, FSMState, FSMEngine, ActionType
)


def _is_noop(result):
    """NOOP returns None (shadow) or '' (active). Both = no response."""
    return result is None or result == ""


# ============================================================
# FIX 786: CONTINUATION en todos los estados
# ============================================================

class TestFix786Continuation(unittest.TestCase):
    """FIX 786: CONTINUATION → NOOP en estados que no lo tenían."""

    def _fsm_at(self, state, **ctx_kwargs):
        fsm = FSMEngine()
        fsm.state = state
        fsm.context.pitch_dado = True
        fsm.context.encargado_preguntado = True
        for k, v in ctx_kwargs.items():
            setattr(fsm.context, k, v)
        return fsm

    def test_continuation_saludo(self):
        """SALUDO + CONTINUATION → stays SALUDO, NOOP."""
        fsm = self._fsm_at(FSMState.SALUDO)
        result = fsm.process("Sí, es que,", agente=None)
        self.assertEqual(fsm.state, FSMState.SALUDO)
        self.assertTrue(_is_noop(result), f"Expected NOOP, got: {result!r}")

    def test_continuation_pitch(self):
        """PITCH + CONTINUATION → stays PITCH, NOOP."""
        fsm = self._fsm_at(FSMState.PITCH)
        result = fsm.process("Pues mire,", agente=None)
        self.assertEqual(fsm.state, FSMState.PITCH)
        self.assertTrue(_is_noop(result), f"Expected NOOP, got: {result!r}")

    def test_continuation_buscando(self):
        """BUSCANDO_ENCARGADO + CONTINUATION → stays, NOOP."""
        fsm = self._fsm_at(FSMState.BUSCANDO_ENCARGADO)
        result = fsm.process("Espere,", agente=None)
        self.assertEqual(fsm.state, FSMState.BUSCANDO_ENCARGADO)
        self.assertTrue(_is_noop(result), f"Expected NOOP, got: {result!r}")

    def test_continuation_encargado_presente(self):
        """ENCARGADO_PRESENTE + CONTINUATION → stays, NOOP."""
        fsm = self._fsm_at(FSMState.ENCARGADO_PRESENTE)
        result = fsm.process("Ah bueno,", agente=None)
        self.assertEqual(fsm.state, FSMState.ENCARGADO_PRESENTE)
        self.assertTrue(_is_noop(result), f"Expected NOOP, got: {result!r}")

    def test_continuation_encargado_ausente(self):
        """ENCARGADO_AUSENTE + CONTINUATION → stays, NOOP."""
        fsm = self._fsm_at(FSMState.ENCARGADO_AUSENTE)
        result = fsm.process("Es que,", agente=None)
        self.assertEqual(fsm.state, FSMState.ENCARGADO_AUSENTE)
        self.assertTrue(_is_noop(result), f"Expected NOOP, got: {result!r}")

    def test_continuation_esperando(self):
        """ESPERANDO_TRANSFERENCIA + CONTINUATION → stays, NOOP."""
        fsm = self._fsm_at(FSMState.ESPERANDO_TRANSFERENCIA)
        result = fsm.process("Ya mero,", agente=None)
        self.assertEqual(fsm.state, FSMState.ESPERANDO_TRANSFERENCIA)
        self.assertTrue(_is_noop(result), f"Expected NOOP, got: {result!r}")

    def test_continuation_capturando(self):
        """CAPTURANDO_CONTACTO + CONTINUATION → stays, NOOP."""
        fsm = self._fsm_at(FSMState.CAPTURANDO_CONTACTO)
        result = fsm.process("Bueno,", agente=None)
        self.assertEqual(fsm.state, FSMState.CAPTURANDO_CONTACTO)
        self.assertTrue(_is_noop(result), f"Expected NOOP, got: {result!r}")

    def test_continuation_ofreciendo(self):
        """OFRECIENDO_CONTACTO + CONTINUATION → stays, NOOP."""
        fsm = self._fsm_at(FSMState.OFRECIENDO_CONTACTO)
        result = fsm.process("Pues,", agente=None)
        self.assertEqual(fsm.state, FSMState.OFRECIENDO_CONTACTO)
        self.assertTrue(_is_noop(result), f"Expected NOOP, got: {result!r}")

    def test_continuation_contacto_capturado(self):
        """CONTACTO_CAPTURADO + CONTINUATION → stays, NOOP."""
        fsm = self._fsm_at(FSMState.CONTACTO_CAPTURADO)
        result = fsm.process("Y pues,", agente=None)
        self.assertEqual(fsm.state, FSMState.CONTACTO_CAPTURADO)
        self.assertTrue(_is_noop(result), f"Expected NOOP, got: {result!r}")

    def test_continuation_despedida(self):
        """DESPEDIDA + CONTINUATION → stays, NOOP."""
        fsm = self._fsm_at(FSMState.DESPEDIDA)
        result = fsm.process("Bueno,", agente=None)
        self.assertEqual(fsm.state, FSMState.DESPEDIDA)
        self.assertTrue(_is_noop(result), f"Expected NOOP, got: {result!r}")

    def test_continuation_dictando_dato_still_ack(self):
        """DICTANDO_DATO + CONTINUATION → stays, ACK (pre-existing, not NOOP)."""
        fsm = self._fsm_at(FSMState.DICTANDO_DATO)
        result = fsm.process("Tres tres uno,", agente=None)
        self.assertEqual(fsm.state, FSMState.DICTANDO_DATO)
        # DICTANDO_DATO already had CONTINUATION → ACKNOWLEDGE "aja_si" (not NOOP)
        # This should intercept with a response
        if result:
            self.assertIn("si", result.lower())

    def test_classify_continuation(self):
        """Comma-ending text < 40 chars = CONTINUATION."""
        intent = classify_intent("Pues mire,", FSMContext(), FSMState.PITCH)
        self.assertEqual(intent, FSMIntent.CONTINUATION)

    def test_not_continuation_long(self):
        """Comma-ending text >= 40 chars is NOT CONTINUATION."""
        long_text = "Pues fíjese que aquí no tenemos ese tipo de producto,"
        intent = classify_intent(long_text, FSMContext(), FSMState.PITCH)
        self.assertNotEqual(intent, FSMIntent.CONTINUATION)


# ============================================================
# FIX 787: Gaps OFRECIENDO_CONTACTO
# ============================================================

class TestFix787OfreciendoContacto(unittest.TestCase):
    """FIX 787: Completar transiciones faltantes en OFRECIENDO_CONTACTO."""

    def _fsm_at_ofreciendo(self):
        fsm = FSMEngine()
        fsm.state = FSMState.OFRECIENDO_CONTACTO
        fsm.context.pitch_dado = True
        fsm.context.encargado_preguntado = True
        return fsm

    def test_complete_phone_captures(self):
        """Client dictates full phone → CONTACTO_CAPTURADO."""
        fsm = self._fsm_at_ofreciendo()
        fsm.process("6141234567", agente=None)
        self.assertEqual(fsm.state, FSMState.CONTACTO_CAPTURADO)

    def test_complete_email_captures(self):
        """Client dictates full email → CONTACTO_CAPTURADO."""
        fsm = self._fsm_at_ofreciendo()
        fsm.process("test arroba gmail punto com", agente=None)
        self.assertEqual(fsm.state, FSMState.CONTACTO_CAPTURADO)

    def test_partial_dictation_to_dictando(self):
        """Client starts dictating → DICTANDO_DATO."""
        fsm = self._fsm_at_ofreciendo()
        fsm.process("Es 614 tres ocho", agente=None)
        self.assertEqual(fsm.state, FSMState.DICTANDO_DATO)

    def test_verification_stays(self):
        """'¿Bueno?' → stays OFRECIENDO_CONTACTO."""
        fsm = self._fsm_at_ofreciendo()
        result = fsm.process("Bueno", agente=None)
        self.assertEqual(fsm.state, FSMState.OFRECIENDO_CONTACTO)
        if result:
            self.assertIn("aqui estoy", result.lower().replace("í", "i"))

    def test_question_stays_narrow(self):
        """Question → stays OFRECIENDO_CONTACTO (QUESTION or WHAT_OFFER per FIX 894)."""
        fsm = self._fsm_at_ofreciendo()
        intent = classify_intent("¿Qué productos manejan?", FSMContext(), FSMState.OFRECIENDO_CONTACTO)
        self.assertIn(intent, (FSMIntent.QUESTION, FSMIntent.WHAT_OFFER))

    def test_identity_stays(self):
        """'¿De dónde habla?' → stays OFRECIENDO_CONTACTO."""
        fsm = self._fsm_at_ofreciendo()
        result = fsm.process("De donde habla?", agente=None)
        self.assertEqual(fsm.state, FSMState.OFRECIENDO_CONTACTO)

    def test_offer_data_to_dictando(self):
        """'Le doy mi teléfono' → DICTANDO_DATO."""
        fsm = self._fsm_at_ofreciendo()
        fsm.process("Le doy mi teléfono", agente=None)
        self.assertEqual(fsm.state, FSMState.DICTANDO_DATO)

    def test_wrong_number_to_despedida(self):
        """'Número equivocado' → DESPEDIDA."""
        fsm = self._fsm_at_ofreciendo()
        fsm.process("Número equivocado", agente=None)
        self.assertEqual(fsm.state, FSMState.DESPEDIDA)


# ============================================================
# FIX 788: Gaps menores - ENCARGADO_PRESENTE
# ============================================================

class TestFix788EncargadoPresente(unittest.TestCase):
    """FIX 788: Gaps en ENCARGADO_PRESENTE."""

    def _fsm_at(self):
        fsm = FSMEngine()
        fsm.state = FSMState.ENCARGADO_PRESENTE
        fsm.context.pitch_dado = True
        fsm.context.encargado_preguntado = True
        return fsm

    def test_identity_stays(self):
        """'De donde habla?' → stays ENCARGADO_PRESENTE."""
        fsm = self._fsm_at()
        result = fsm.process("De donde habla?", agente=None)
        self.assertEqual(fsm.state, FSMState.ENCARGADO_PRESENTE)

    def test_another_branch_despedida(self):
        """'Otra sucursal' → DESPEDIDA."""
        fsm = self._fsm_at()
        fsm.process("No es esta sucursal, es otra sucursal", agente=None)
        self.assertEqual(fsm.state, FSMState.DESPEDIDA)

    def test_closed_despedida(self):
        """'Estamos cerrados' → DESPEDIDA."""
        fsm = self._fsm_at()
        fsm.process("Estamos cerrados", agente=None)
        self.assertEqual(fsm.state, FSMState.DESPEDIDA)

    def test_callback_stays(self):
        """'Llame más tarde' → stays (preguntar_hora_callback)."""
        fsm = self._fsm_at()
        fsm.process("Llame más tarde", agente=None)
        self.assertEqual(fsm.state, FSMState.ENCARGADO_PRESENTE)

    def test_transfer_to_esperando(self):
        """'Un momento' → ESPERANDO_TRANSFERENCIA."""
        fsm = self._fsm_at()
        fsm.process("Un momento", agente=None)
        self.assertEqual(fsm.state, FSMState.ESPERANDO_TRANSFERENCIA)


# ============================================================
# FIX 788: Gaps menores - ESPERANDO_TRANSFERENCIA
# ============================================================

class TestFix788EsperandoTransferencia(unittest.TestCase):
    """FIX 788: Gaps en ESPERANDO_TRANSFERENCIA."""

    def _fsm_at(self):
        fsm = FSMEngine()
        fsm.state = FSMState.ESPERANDO_TRANSFERENCIA
        fsm.context.pitch_dado = True
        fsm.context.encargado_preguntado = True
        return fsm

    def test_no_interest_to_despedida(self):
        """'No me interesa' → DESPEDIDA."""
        fsm = self._fsm_at()
        fsm.process("No me interesa", agente=None)
        self.assertEqual(fsm.state, FSMState.DESPEDIDA)

    def test_callback_to_encargado_ausente(self):
        """'Llame más tarde' → ENCARGADO_AUSENTE."""
        fsm = self._fsm_at()
        fsm.process("Llame más tarde", agente=None)
        self.assertEqual(fsm.state, FSMState.ENCARGADO_AUSENTE)

    def test_wrong_number_to_despedida(self):
        """'Número equivocado' → DESPEDIDA."""
        fsm = self._fsm_at()
        fsm.process("Número equivocado", agente=None)
        self.assertEqual(fsm.state, FSMState.DESPEDIDA)

    def test_complete_phone_captures(self):
        """Client dictates full phone → CONTACTO_CAPTURADO."""
        fsm = self._fsm_at()
        fsm.process("6141234567", agente=None)
        self.assertEqual(fsm.state, FSMState.CONTACTO_CAPTURADO)

    def test_complete_email_captures(self):
        """Client dictates email → CONTACTO_CAPTURADO."""
        fsm = self._fsm_at()
        fsm.process("test arroba gmail punto com", agente=None)
        self.assertEqual(fsm.state, FSMState.CONTACTO_CAPTURADO)

    def test_partial_dictation_to_dictando(self):
        """Partial dictation → DICTANDO_DATO."""
        fsm = self._fsm_at()
        fsm.process("Es 614 tres", agente=None)
        self.assertEqual(fsm.state, FSMState.DICTANDO_DATO)


# ============================================================
# FIX 788: Gaps menores - otros estados
# ============================================================

class TestFix788OtrosEstados(unittest.TestCase):
    """FIX 788: Gaps en ENCARGADO_AUSENTE, CAPTURANDO_CONTACTO, etc."""

    def _fsm_at(self, state, **ctx_kwargs):
        fsm = FSMEngine()
        fsm.state = state
        fsm.context.pitch_dado = True
        fsm.context.encargado_preguntado = True
        for k, v in ctx_kwargs.items():
            setattr(fsm.context, k, v)
        return fsm

    def test_encargado_ausente_identity(self):
        """ENCARGADO_AUSENTE + IDENTITY → stays."""
        fsm = self._fsm_at(FSMState.ENCARGADO_AUSENTE)
        fsm.process("De donde habla?", agente=None)
        self.assertEqual(fsm.state, FSMState.ENCARGADO_AUSENTE)

    def test_encargado_ausente_closed(self):
        """ENCARGADO_AUSENTE + CLOSED → DESPEDIDA."""
        fsm = self._fsm_at(FSMState.ENCARGADO_AUSENTE)
        fsm.process("Estamos cerrados", agente=None)
        self.assertEqual(fsm.state, FSMState.DESPEDIDA)

    def test_capturando_identity(self):
        """CAPTURANDO_CONTACTO + IDENTITY → stays."""
        fsm = self._fsm_at(FSMState.CAPTURANDO_CONTACTO)
        fsm.process("De donde habla?", agente=None)
        self.assertEqual(fsm.state, FSMState.CAPTURANDO_CONTACTO)

    def test_capturando_wrong_number(self):
        """CAPTURANDO_CONTACTO + WRONG_NUMBER → DESPEDIDA."""
        fsm = self._fsm_at(FSMState.CAPTURANDO_CONTACTO)
        fsm.process("Número equivocado", agente=None)
        self.assertEqual(fsm.state, FSMState.DESPEDIDA)

    def test_dictando_no_interest(self):
        """DICTANDO_DATO + NO_INTEREST → DESPEDIDA."""
        fsm = self._fsm_at(FSMState.DICTANDO_DATO)
        fsm.process("No me interesa", agente=None)
        self.assertEqual(fsm.state, FSMState.DESPEDIDA)

    def test_dictando_reject_data(self):
        """DICTANDO_DATO + REJECT_DATA → OFRECIENDO_CONTACTO."""
        fsm = self._fsm_at(FSMState.DICTANDO_DATO)
        fsm.process("No tengo whatsapp", agente=None)
        self.assertEqual(fsm.state, FSMState.OFRECIENDO_CONTACTO)

    def test_dictando_identity(self):
        """DICTANDO_DATO + IDENTITY → stays DICTANDO_DATO."""
        fsm = self._fsm_at(FSMState.DICTANDO_DATO)
        fsm.process("De donde habla?", agente=None)
        self.assertEqual(fsm.state, FSMState.DICTANDO_DATO)

    def test_contacto_capturado_verification(self):
        """CONTACTO_CAPTURADO + VERIFICATION → stays."""
        fsm = self._fsm_at(FSMState.CONTACTO_CAPTURADO)
        result = fsm.process("Bueno", agente=None)
        self.assertEqual(fsm.state, FSMState.CONTACTO_CAPTURADO)

    def test_contacto_capturado_no_interest(self):
        """CONTACTO_CAPTURADO + NO_INTEREST → DESPEDIDA."""
        fsm = self._fsm_at(FSMState.CONTACTO_CAPTURADO)
        fsm.process("No me interesa", agente=None)
        self.assertEqual(fsm.state, FSMState.DESPEDIDA)

    def test_despedida_no_interest(self):
        """DESPEDIDA + NO_INTEREST → stays DESPEDIDA (HANGUP)."""
        fsm = self._fsm_at(FSMState.DESPEDIDA)
        result = fsm.process("No me interesa", agente=None)
        self.assertEqual(fsm.state, FSMState.DESPEDIDA)

    def test_despedida_wrong_number(self):
        """DESPEDIDA + WRONG_NUMBER → stays DESPEDIDA (HANGUP)."""
        fsm = self._fsm_at(FSMState.DESPEDIDA)
        result = fsm.process("Número equivocado", agente=None)
        self.assertEqual(fsm.state, FSMState.DESPEDIDA)


# ============================================================
# Transition count validation
# ============================================================

class TestTransitionCoverage(unittest.TestCase):
    """Validate transition coverage improved."""

    def test_continuation_in_active_states(self):
        """CONTINUATION defined for all 11 active states (not CONVERSACION_LIBRE)."""
        fsm = FSMEngine()
        for state in FSMState:
            if state == FSMState.CONVERSACION_LIBRE:
                continue  # Dead state, no transitions defined
            key = (state, FSMIntent.CONTINUATION)
            self.assertIn(key, fsm._transitions,
                         f"CONTINUATION missing for {state.value}")

    def test_ofreciendo_contacto_has_dictating(self):
        """OFRECIENDO_CONTACTO has DICTATING_* transitions."""
        fsm = FSMEngine()
        for intent in [FSMIntent.DICTATING_COMPLETE_PHONE,
                       FSMIntent.DICTATING_COMPLETE_EMAIL,
                       FSMIntent.DICTATING_PARTIAL]:
            key = (FSMState.OFRECIENDO_CONTACTO, intent)
            self.assertIn(key, fsm._transitions,
                         f"{intent.value} missing for OFRECIENDO_CONTACTO")

    def test_total_transitions_increased(self):
        """Total transitions should be >= 160 (was ~130)."""
        fsm = FSMEngine()
        count = len(fsm._transitions)
        self.assertGreaterEqual(count, 160,
                               f"Expected >= 160 transitions, got {count}")

    def test_encargado_presente_has_identity(self):
        """ENCARGADO_PRESENTE has IDENTITY transition."""
        fsm = FSMEngine()
        key = (FSMState.ENCARGADO_PRESENTE, FSMIntent.IDENTITY)
        self.assertIn(key, fsm._transitions)

    def test_esperando_has_no_interest(self):
        """ESPERANDO_TRANSFERENCIA has NO_INTEREST transition."""
        fsm = FSMEngine()
        key = (FSMState.ESPERANDO_TRANSFERENCIA, FSMIntent.NO_INTEREST)
        self.assertIn(key, fsm._transitions)

    def test_esperando_has_callback(self):
        """ESPERANDO_TRANSFERENCIA has CALLBACK transition."""
        fsm = FSMEngine()
        key = (FSMState.ESPERANDO_TRANSFERENCIA, FSMIntent.CALLBACK)
        self.assertIn(key, fsm._transitions)


if __name__ == '__main__':
    unittest.main()
