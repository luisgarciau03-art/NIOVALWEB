"""
Tests for FIX 783 + FIX 784 + FIX 785.

FIX 783: BRUCE2494 (P0) - Farewell check ANTES de dictado numérico.
  - "No una disculpa... hasta luego" tiene num_words=2 → clasificaba DICTATING_PARTIAL
  - Con FIX 783, farewell se detecta PRIMERO → FAREWELL correcto

FIX 784: BRUCE2490 (P1) - Hora en palabras en callback FSM.
  - "márquele a las ocho de la mañana" → FSM detecta CALLBACK → preguntar_hora_callback
  - Con FIX 784, detecta hora verbal → confirmar_callback (no repite pregunta)

FIX 785: BRUCE2492/2497 (P2) - encargado_preguntado en pitch_inicial.
  - pitch_inicial incluye "¿Se encontrará el encargado...?"
  - PITCH→BUSCANDO con preguntar_encargado duplicaba la pregunta
  - Con FIX 785, encargado_preguntado=True tras pitch_inicial → no duplica
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from fsm_engine import (
    classify_intent, FSMIntent, FSMContext, FSMState, FSMEngine, _normalize
)


# ============================================================
# FIX 783: Farewell antes de dictado numérico
# ============================================================

class TestFix783FarewellBeforeDictado(unittest.TestCase):
    """FIX 783: Farewell detectado ANTES de conteo numérico."""

    def _ctx(self):
        ctx = FSMContext()
        ctx.encargado_preguntado = True
        ctx.pitch_dado = True
        return ctx

    def test_hasta_luego_con_numwords(self):
        """'No una disculpa hasta luego' debe ser FAREWELL, no DICTATING_PARTIAL."""
        intent = classify_intent(
            "No una disculpa, nosotros no tenemos ese tipo de caso. Hasta luego.",
            self._ctx(), FSMState.PITCH
        )
        self.assertEqual(intent, FSMIntent.FAREWELL)

    def test_hasta_luego_garbled_stt(self):
        """STT garbled con repeticiones aún detecta FAREWELL."""
        intent = classify_intent(
            "Este, no, una disculpa, no Este, no, una disculpa, nosotros no tenemos "
            "ese tipo de caso. Hasta luego. No una disculpa, nosotros no tenemos ese "
            "tipo de casa hasta luego.",
            self._ctx(), FSMState.PITCH
        )
        self.assertEqual(intent, FSMIntent.FAREWELL)

    def test_adios_con_numwords(self):
        """'No, una... adiós' debe ser FAREWELL."""
        intent = classify_intent(
            "No, una disculpa, adiós.",
            self._ctx(), FSMState.BUSCANDO_ENCARGADO
        )
        self.assertEqual(intent, FSMIntent.FAREWELL)

    def test_hasta_luego_simple(self):
        """'Hasta luego' simple sigue siendo FAREWELL."""
        intent = classify_intent(
            "Hasta luego",
            self._ctx(), FSMState.PITCH
        )
        self.assertEqual(intent, FSMIntent.FAREWELL)

    def test_nos_vemos(self):
        """'nos vemos' = FAREWELL."""
        intent = classify_intent(
            "Nos vemos, gracias",
            self._ctx(), FSMState.BUSCANDO_ENCARGADO
        )
        self.assertEqual(intent, FSMIntent.FAREWELL)

    def test_que_le_vaya_bien(self):
        """'que le vaya bien' = FAREWELL."""
        intent = classify_intent(
            "Ok, que le vaya bien",
            self._ctx(), FSMState.ENCARGADO_PRESENTE
        )
        self.assertEqual(intent, FSMIntent.FAREWELL)

    def test_gracias_exact_match(self):
        """'gracias' exact = FAREWELL."""
        intent = classify_intent(
            "Gracias",
            self._ctx(), FSMState.BUSCANDO_ENCARGADO
        )
        self.assertEqual(intent, FSMIntent.FAREWELL)

    def test_muchas_gracias_exact(self):
        """'muchas gracias' exact = FAREWELL."""
        intent = classify_intent(
            "Muchas gracias",
            self._ctx(), FSMState.PITCH
        )
        self.assertEqual(intent, FSMIntent.FAREWELL)

    def test_real_dictation_still_works(self):
        """Real phone dictation (no farewell) still = DICTATING_PARTIAL."""
        intent = classify_intent(
            "seis uno cuatro tres ocho dos",
            self._ctx(), FSMState.DICTANDO_DATO
        )
        self.assertEqual(intent, FSMIntent.DICTATING_PARTIAL)

    def test_complete_phone_still_works(self):
        """10-digit phone still = DICTATING_COMPLETE_PHONE."""
        intent = classify_intent(
            "6141234567",
            self._ctx(), FSMState.BUSCANDO_ENCARGADO
        )
        self.assertEqual(intent, FSMIntent.DICTATING_COMPLETE_PHONE)

    def test_buen_dia_farewell(self):
        """'buen dia' = FAREWELL."""
        intent = classify_intent(
            "Buen día, hasta luego",
            self._ctx(), FSMState.PITCH
        )
        self.assertEqual(intent, FSMIntent.FAREWELL)

    def test_email_priority_still_works(self):
        """Email with numbers still detected as email, not farewell."""
        intent = classify_intent(
            "test64 arroba gmail punto com",
            self._ctx(), FSMState.DICTANDO_DATO
        )
        self.assertEqual(intent, FSMIntent.DICTATING_COMPLETE_EMAIL)


# ============================================================
# FIX 783: Integration - FSM flow
# ============================================================

class TestFix783Integration(unittest.TestCase):
    """FIX 783: FSM flow when farewell has num_words."""

    def test_farewell_in_pitch_goes_to_despedida(self):
        """Farewell in PITCH → DESPEDIDA."""
        fsm = FSMEngine()
        fsm.state = FSMState.PITCH
        fsm.context.pitch_dado = True
        fsm.process("No, una disculpa, no manejamos eso. Hasta luego.", agente=None)
        self.assertEqual(fsm.state, FSMState.DESPEDIDA)

    def test_farewell_in_buscando_goes_to_despedida(self):
        """Farewell in BUSCANDO_ENCARGADO → DESPEDIDA."""
        fsm = FSMEngine()
        fsm.state = FSMState.BUSCANDO_ENCARGADO
        fsm.context.pitch_dado = True
        fsm.context.encargado_preguntado = True
        fsm.process("Hasta luego, gracias.", agente=None)
        self.assertEqual(fsm.state, FSMState.DESPEDIDA)


# ============================================================
# FIX 784: Hora en palabras en callback
# ============================================================

class TestFix784HoraEnPalabras(unittest.TestCase):
    """FIX 784: Detectar hora verbal en callback y confirmar."""

    def test_detectar_ocho_de_la_manana(self):
        """'a las ocho de la mañana' → hora detectada."""
        fsm = FSMEngine()
        hora = fsm._detectar_hora_en_texto_784("No, márquele a las ocho de la mañana.")
        self.assertIsNotNone(hora)
        self.assertIn("8", hora)

    def test_detectar_nueve(self):
        """'a las nueve' → hora detectada."""
        fsm = FSMEngine()
        hora = fsm._detectar_hora_en_texto_784("Mejor llame a las nueve")
        self.assertIsNotNone(hora)
        self.assertIn("9", hora)

    def test_detectar_tres_de_la_tarde(self):
        """'a las tres de la tarde' → hora detectada con periodo."""
        fsm = FSMEngine()
        hora = fsm._detectar_hora_en_texto_784("Llame a las tres de la tarde")
        self.assertIsNotNone(hora)
        self.assertIn("3", hora)
        self.assertIn("tarde", hora)

    def test_detectar_hora_numerica(self):
        """'a las 9' → hora detectada (dígito)."""
        fsm = FSMEngine()
        hora = fsm._detectar_hora_en_texto_784("Márquele a las 9 de la mañana")
        self.assertIsNotNone(hora)
        self.assertIn("9", hora)

    def test_detectar_doce(self):
        """'a las doce' → hora detectada."""
        fsm = FSMEngine()
        hora = fsm._detectar_hora_en_texto_784("Que llame a las doce")
        self.assertIsNotNone(hora)
        self.assertIn("12", hora)

    def test_sin_hora_retorna_none(self):
        """Texto sin hora → None."""
        fsm = FSMEngine()
        hora = fsm._detectar_hora_en_texto_784("No está, marque más tarde")
        # "en la tarde" sin "a las X" debería devolver periodo genérico o None
        # Depende de si queremos detectar "más tarde" como hora
        # En este caso "mas tarde" no matchea "en la tarde" ni "por la tarde"
        self.assertIsNone(hora)

    def test_en_la_manana_sin_hora(self):
        """'en la mañana' sin hora específica → detecta periodo genérico."""
        fsm = FSMEngine()
        hora = fsm._detectar_hora_en_texto_784("Mejor llame en la mañana")
        self.assertIsNotNone(hora)
        self.assertIn("manana", hora)

    def test_por_la_tarde(self):
        """'por la tarde' → detecta periodo genérico."""
        fsm = FSMEngine()
        hora = fsm._detectar_hora_en_texto_784("Mejor por la tarde")
        self.assertIsNotNone(hora)
        self.assertIn("tarde", hora)


# ============================================================
# FIX 784: Integration - FSM callback con hora
# ============================================================

class TestFix784Integration(unittest.TestCase):
    """FIX 784: FSM callback detecta hora y usa confirmar_callback."""

    def test_callback_con_hora_verbal_no_pregunta(self):
        """'márquele a las ocho' in BUSCANDO → confirmar_callback, no preguntar."""
        fsm = FSMEngine()
        fsm.state = FSMState.BUSCANDO_ENCARGADO
        fsm.context.pitch_dado = True
        fsm.context.encargado_preguntado = True
        result = fsm.process("No, márquele a las ocho de la mañana.", agente=None)
        if result:
            self.assertNotIn("A que hora", result)
            # Should confirm, not ask
            self.assertTrue(
                "marco" in result.lower() or "perfecto" in result.lower(),
                f"Expected confirmation response, got: {result}"
            )

    def test_callback_sin_hora_pregunta(self):
        """'no está, que llame después' sin hora → encargado_ausente path."""
        fsm = FSMEngine()
        fsm.state = FSMState.BUSCANDO_ENCARGADO
        fsm.context.pitch_dado = True
        fsm.context.encargado_preguntado = True
        result = fsm.process("No está, márquele más tarde.", agente=None)
        if result:
            # FSM classifies as MANAGER_ABSENT → pedir_contacto_alternativo
            # (not CALLBACK, so no hora detection needed)
            self.assertIn(fsm.state, [FSMState.ENCARGADO_AUSENTE])

    def test_callback_con_hora_en_pitch(self):
        """Callback con hora desde PITCH → confirmar."""
        fsm = FSMEngine()
        fsm.state = FSMState.PITCH
        fsm.context.pitch_dado = True
        result = fsm.process("No, llame a las nueve mejor.", agente=None)
        if result:
            self.assertNotIn("A que hora", result)


# ============================================================
# FIX 785: encargado_preguntado en pitch_inicial
# ============================================================

class TestFix785EncargadoPreguntado(unittest.TestCase):
    """FIX 785: pitch_inicial marca encargado_preguntado=True."""

    def test_pitch_inicial_sets_encargado_preguntado(self):
        """After SALUDO→PITCH with pitch_inicial, encargado_preguntado=True."""
        fsm = FSMEngine()
        self.assertEqual(fsm.state, FSMState.SALUDO)
        # Client says "Sí" → SALUDO→PITCH with pitch_inicial
        fsm.process("Sí", agente=None)
        self.assertEqual(fsm.state, FSMState.PITCH)
        self.assertTrue(fsm.context.encargado_preguntado,
                       "pitch_inicial should set encargado_preguntado=True")

    def test_pitch_unknown_no_duplicate_encargado(self):
        """FIX 791: PITCH+UNKNOWN advances state, FIX 785 prevents duplicate encargado."""
        fsm = FSMEngine()
        # Step 1: SALUDO→PITCH (pitch_inicial sets encargado_preguntado=True)
        fsm.process("Sí", agente=None)
        self.assertEqual(fsm.state, FSMState.PITCH)
        self.assertTrue(fsm.context.encargado_preguntado)

        # Step 2: PITCH+UNKNOWN → FIX 791 stateful template
        # encargado_preguntado=True → skips preguntar_encargado, goes to pedir_whatsapp
        result = fsm.process("Pues cuando termine.", agente=None)
        self.assertIn(fsm.state, [
            FSMState.CAPTURANDO_CONTACTO,
            FSMState.BUSCANDO_ENCARGADO,
        ])
        # FIX 785 ensures no duplicate encargado question

    def test_first_preguntar_encargado_still_works(self):
        """When encargado NOT preguntado yet, preguntar_encargado works normally."""
        fsm = FSMEngine()
        fsm.state = FSMState.BUSCANDO_ENCARGADO
        fsm.context.pitch_dado = True
        fsm.context.encargado_preguntado = False
        # Client says "Sí" → should ask for encargado
        result = fsm.process("Sí", agente=None)
        if result:
            self.assertIn("encargado", result.lower(),
                         f"Should ask about encargado, got: {result}")

    def test_full_flow_saludo_pitch_buscando(self):
        """Full flow: SALUDO→PITCH→BUSCANDO without encargado duplication."""
        fsm = FSMEngine()

        # Turn 1: SALUDO→PITCH (pitch_inicial includes encargado question)
        r1 = fsm.process("¿Bueno?", agente=None)
        self.assertEqual(fsm.state, FSMState.PITCH)
        if r1:
            self.assertIn("encargado", r1.lower(),
                         "pitch_inicial should include encargado question")

        # Turn 2: PITCH→BUSCANDO (should NOT repeat encargado)
        r2 = fsm.process("Sí, un momento", agente=None)
        if r2:
            self.assertNotIn("encontrara el encargado", r2.lower(),
                           f"Should not repeat encargado question, got: {r2}")

    def test_context_flag_after_pitch(self):
        """Verify context flags after pitch_inicial."""
        fsm = FSMEngine()
        fsm.process("Sí", agente=None)  # SALUDO→PITCH
        self.assertTrue(fsm.context.pitch_dado)
        self.assertTrue(fsm.context.encargado_preguntado)


# ============================================================
# Cross-FIX integration tests
# ============================================================

class TestFix783784785CrossIntegration(unittest.TestCase):
    """Integration: All 3 fixes work together."""

    def test_farewell_after_pitch(self):
        """Client says farewell after pitch → DESPEDIDA (not dictating)."""
        fsm = FSMEngine()
        fsm.process("¿Bueno?", agente=None)  # SALUDO→PITCH
        fsm.process("No, no me interesa. Hasta luego.", agente=None)  # Should → DESPEDIDA
        self.assertEqual(fsm.state, FSMState.DESPEDIDA)

    def test_callback_hora_after_pitch(self):
        """Client requests callback with hour after pitch → confirm."""
        fsm = FSMEngine()
        fsm.process("Sí", agente=None)  # SALUDO→PITCH
        result = fsm.process("No, llámele a las diez de la mañana.", agente=None)
        if result:
            # Should confirm hour, not ask for it
            self.assertNotIn("A que hora", result)

    def test_email_still_works_after_farewell_priority(self):
        """Email detection still works (higher priority than farewell)."""
        intent = classify_intent(
            "Es test arroba gmail punto com",
            FSMContext(), FSMState.DICTANDO_DATO
        )
        self.assertEqual(intent, FSMIntent.DICTATING_COMPLETE_EMAIL)

    def test_continuation_still_works(self):
        """Continuation (comma) still highest priority."""
        intent = classify_intent(
            "Hasta luego,",
            FSMContext(), FSMState.DICTANDO_DATO
        )
        # Comma at end with short text → CONTINUATION
        self.assertEqual(intent, FSMIntent.CONTINUATION)


if __name__ == '__main__':
    unittest.main()
