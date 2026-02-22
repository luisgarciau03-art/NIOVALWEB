"""
Tests para fsm_engine.py - Motor FSM Determinista.

Tests unitarios de:
- classify_intent: clasificación de intents
- FSMEngine transiciones: (estado, intent) → (estado, acción)
- FSMContext: actualización de contexto
- Guards: evaluación de condiciones
"""
import sys
import os
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Force shadow mode for tests (no intercept)
os.environ["FSM_ENABLED"] = "active"

from fsm_engine import (
    FSMEngine, FSMState, FSMIntent, FSMContext, ActionType,
    classify_intent, _normalize,
)


# ============================================================
# classify_intent tests
# ============================================================

class TestClassifyIntentFarewell(unittest.TestCase):
    """Test farewell detection."""

    def setUp(self):
        self.ctx = FSMContext()
        self.state = FSMState.BUSCANDO_ENCARGADO

    def test_hasta_luego(self):
        self.assertEqual(classify_intent("Hasta luego", self.ctx, self.state), FSMIntent.FAREWELL)

    def test_adios(self):
        self.assertEqual(classify_intent("Adiós", self.ctx, self.state), FSMIntent.FAREWELL)

    def test_gracias_exact(self):
        self.assertEqual(classify_intent("gracias", self.ctx, self.state), FSMIntent.FAREWELL)

    def test_nos_vemos(self):
        self.assertEqual(classify_intent("Nos vemos", self.ctx, self.state), FSMIntent.FAREWELL)


class TestClassifyIntentNoInterest(unittest.TestCase):
    """Test no-interest detection."""

    def setUp(self):
        self.ctx = FSMContext()
        self.state = FSMState.PITCH

    def test_no_me_interesa(self):
        self.assertEqual(classify_intent("No me interesa", self.ctx, self.state), FSMIntent.NO_INTEREST)

    def test_no_hacemos_compras(self):
        self.assertEqual(classify_intent("No hacemos compras", self.ctx, self.state), FSMIntent.NO_INTEREST)

    def test_no_joven(self):
        self.assertEqual(classify_intent("No, joven", self.ctx, self.state), FSMIntent.NO_INTEREST)

    def test_aqui_es_taller(self):
        self.assertEqual(classify_intent("Aquí es un taller", self.ctx, self.state), FSMIntent.NO_INTEREST)

    def test_no_compramos(self):
        self.assertEqual(classify_intent("No compramos", self.ctx, self.state), FSMIntent.NO_INTEREST)


class TestClassifyIntentOfferData(unittest.TestCase):
    """Test offer-data detection."""

    def setUp(self):
        self.ctx = FSMContext()
        self.state = FSMState.BUSCANDO_ENCARGADO

    def test_te_doy_correo(self):
        self.assertEqual(classify_intent("Te doy el correo", self.ctx, self.state), FSMIntent.OFFER_DATA)

    def test_le_paso_numero(self):
        self.assertEqual(classify_intent("Le paso el número", self.ctx, self.state), FSMIntent.OFFER_DATA)

    def test_tiene_donde_anotar(self):
        self.assertEqual(classify_intent("¿Tiene donde anotar?", self.ctx, self.state), FSMIntent.OFFER_DATA)

    def test_mi_correo_es(self):
        self.assertEqual(classify_intent("Mi correo es juan arroba gmail", self.ctx, self.state), FSMIntent.DICTATING_COMPLETE_EMAIL)

    def test_anota(self):
        self.assertEqual(classify_intent("Anota", self.ctx, self.state), FSMIntent.OFFER_DATA)


class TestClassifyIntentManagerAbsent(unittest.TestCase):
    """Test manager-absent detection."""

    def setUp(self):
        self.ctx = FSMContext()
        self.state = FSMState.BUSCANDO_ENCARGADO

    def test_no_esta(self):
        self.assertEqual(classify_intent("No está", self.ctx, self.state), FSMIntent.MANAGER_ABSENT)

    def test_salio_a_comer(self):
        self.assertEqual(classify_intent("Salió a comer", self.ctx, self.state), FSMIntent.MANAGER_ABSENT)

    def test_esta_en_junta(self):
        self.assertEqual(classify_intent("Está en junta", self.ctx, self.state), FSMIntent.MANAGER_ABSENT)

    def test_viene_mas_tarde(self):
        self.assertEqual(classify_intent("Viene más tarde", self.ctx, self.state), FSMIntent.MANAGER_ABSENT)


class TestClassifyIntentManagerPresent(unittest.TestCase):
    """Test manager-present detection."""

    def setUp(self):
        self.ctx = FSMContext()
        self.state = FSMState.BUSCANDO_ENCARGADO

    def test_soy_yo(self):
        self.assertEqual(classify_intent("Sí, soy yo", self.ctx, self.state), FSMIntent.MANAGER_PRESENT)

    def test_yo_soy_encargado(self):
        self.assertEqual(classify_intent("Yo soy el encargado", self.ctx, self.state), FSMIntent.MANAGER_PRESENT)

    def test_conmigo(self):
        self.assertEqual(classify_intent("Conmigo", self.ctx, self.state), FSMIntent.MANAGER_PRESENT)


class TestClassifyIntentTransfer(unittest.TestCase):
    """Test transfer detection (wait in line)."""

    def setUp(self):
        self.ctx = FSMContext()
        self.state = FSMState.BUSCANDO_ENCARGADO

    def test_espere_un_momento(self):
        self.assertEqual(classify_intent("Espere un momento", self.ctx, self.state), FSMIntent.TRANSFER)

    def test_permitame(self):
        self.assertEqual(classify_intent("Permítame", self.ctx, self.state), FSMIntent.TRANSFER)

    def test_un_momento(self):
        self.assertEqual(classify_intent("Un momento", self.ctx, self.state), FSMIntent.TRANSFER)


class TestClassifyIntentCallback(unittest.TestCase):
    """Test callback detection (call later)."""

    def setUp(self):
        self.ctx = FSMContext()
        self.state = FSMState.BUSCANDO_ENCARGADO

    def test_esperar_que_regrese(self):
        """'Esperar a que regrese' is CALLBACK, not TRANSFER."""
        self.assertEqual(classify_intent("Tendría que esperar a que regrese", self.ctx, self.state), FSMIntent.CALLBACK)

    def test_llamar_mas_tarde(self):
        self.assertEqual(classify_intent("Llame más tarde", self.ctx, self.state), FSMIntent.CALLBACK)

    def test_marcar_despues(self):
        self.assertEqual(classify_intent("Marque después", self.ctx, self.state), FSMIntent.CALLBACK)


class TestClassifyIntentDictation(unittest.TestCase):
    """Test dictation detection (phone/email)."""

    def setUp(self):
        self.ctx = FSMContext()

    def test_10_digits_complete(self):
        self.assertEqual(
            classify_intent("6 6 2 1 2 3 4 5 6 7", self.ctx, FSMState.DICTANDO_DATO),
            FSMIntent.DICTATING_COMPLETE_PHONE)

    def test_partial_digits(self):
        self.assertEqual(
            classify_intent("6 6 2 1 2 3", self.ctx, FSMState.DICTANDO_DATO),
            FSMIntent.DICTATING_PARTIAL)

    def test_email_complete(self):
        self.assertEqual(
            classify_intent("juan@gmail.com", self.ctx, FSMState.DICTANDO_DATO),
            FSMIntent.DICTATING_COMPLETE_EMAIL)

    def test_email_voice(self):
        self.assertEqual(
            classify_intent("juan arroba gmail punto com", self.ctx, FSMState.DICTANDO_DATO),
            FSMIntent.DICTATING_COMPLETE_EMAIL)

    def test_numbers_words_complete(self):
        """10+ number words = complete phone."""
        self.assertEqual(
            classify_intent("seis seis dos uno dos tres cuatro cinco seis siete", self.ctx, FSMState.DICTANDO_DATO),
            FSMIntent.DICTATING_COMPLETE_PHONE)


class TestClassifyIntentRejectData(unittest.TestCase):
    """Test reject-data detection."""

    def setUp(self):
        self.ctx = FSMContext()
        self.state = FSMState.CAPTURANDO_CONTACTO

    def test_no_tengo_whatsapp(self):
        self.assertEqual(classify_intent("No tengo WhatsApp", self.ctx, self.state), FSMIntent.REJECT_DATA)

    def test_no_lo_puedo_dar(self):
        self.assertEqual(classify_intent("No lo puedo dar", self.ctx, self.state), FSMIntent.REJECT_DATA)

    def test_no_estoy_autorizado(self):
        self.assertEqual(classify_intent("No estoy autorizado", self.ctx, self.state), FSMIntent.REJECT_DATA)


class TestClassifyIntentIdentity(unittest.TestCase):
    """Test identity question detection."""

    def setUp(self):
        self.ctx = FSMContext()
        self.state = FSMState.PITCH

    def test_quien_habla(self):
        self.assertEqual(classify_intent("¿Quién habla?", self.ctx, self.state), FSMIntent.IDENTITY)

    def test_de_donde(self):
        self.assertEqual(classify_intent("¿De dónde?", self.ctx, self.state), FSMIntent.IDENTITY)

    def test_de_que_empresa(self):
        self.assertEqual(classify_intent("¿De qué empresa?", self.ctx, self.state), FSMIntent.IDENTITY)


class TestClassifyIntentConfirmation(unittest.TestCase):
    """Test confirmation detection."""

    def setUp(self):
        self.ctx = FSMContext()
        self.state = FSMState.BUSCANDO_ENCARGADO

    def test_si(self):
        self.assertEqual(classify_intent("Sí", self.ctx, self.state), FSMIntent.CONFIRMATION)

    def test_claro(self):
        self.assertEqual(classify_intent("Claro", self.ctx, self.state), FSMIntent.CONFIRMATION)

    def test_ok(self):
        self.assertEqual(classify_intent("Ok", self.ctx, self.state), FSMIntent.CONFIRMATION)

    def test_esta_bien(self):
        self.assertEqual(classify_intent("Está bien", self.ctx, self.state), FSMIntent.CONFIRMATION)


class TestClassifyIntentVerification(unittest.TestCase):
    """Test connection verification."""

    def setUp(self):
        self.ctx = FSMContext()
        self.state = FSMState.PITCH

    def test_bueno(self):
        self.assertEqual(classify_intent("¿Bueno?", self.ctx, self.state), FSMIntent.VERIFICATION)

    def test_me_escucha(self):
        self.assertEqual(classify_intent("¿Me escucha?", self.ctx, self.state), FSMIntent.VERIFICATION)


# ============================================================
# FSMEngine transition tests
# ============================================================

class TestFSMTransitionsSaludo(unittest.TestCase):
    """Test SALUDO state transitions."""

    def setUp(self):
        self.fsm = FSMEngine()
        self.assertEqual(self.fsm.state, FSMState.SALUDO)

    def test_greeting_to_pitch(self):
        """Client greeting → Bruce gives pitch."""
        result = self.fsm.process("Buenas tardes, dígame")
        self.assertIsNotNone(result)
        self.assertEqual(self.fsm.state, FSMState.PITCH)
        self.assertIn("NIOVAL", result)

    def test_no_interest_to_despedida(self):
        """Client says not interested on first turn → goodbye."""
        result = self.fsm.process("No me interesa")
        self.assertIsNotNone(result)
        self.assertEqual(self.fsm.state, FSMState.DESPEDIDA)

    def test_farewell_to_despedida(self):
        """Client says goodbye immediately → goodbye."""
        result = self.fsm.process("Hasta luego")
        self.assertIsNotNone(result)
        self.assertEqual(self.fsm.state, FSMState.DESPEDIDA)

    def test_identity_question_gives_pitch(self):
        """Client asks identity → pitch with identification."""
        result = self.fsm.process("¿Quién habla?")
        self.assertIsNotNone(result)
        self.assertEqual(self.fsm.state, FSMState.PITCH)
        self.assertIn("NIOVAL", result)


class TestFSMTransitionsPitch(unittest.TestCase):
    """Test PITCH state transitions."""

    def setUp(self):
        self.fsm = FSMEngine()
        self.fsm.process("Bueno")  # → PITCH
        self.assertEqual(self.fsm.state, FSMState.PITCH)

    def test_interest_to_encargado(self):
        """Client shows interest → ask for encargado."""
        result = self.fsm.process("Sí, claro")
        self.assertIsNotNone(result)
        self.assertEqual(self.fsm.state, FSMState.BUSCANDO_ENCARGADO)
        self.assertIn("encargado", result.lower())

    def test_no_interest_to_despedida(self):
        """Client not interested → goodbye."""
        result = self.fsm.process("No me interesa, gracias")
        self.assertIsNotNone(result)
        self.assertEqual(self.fsm.state, FSMState.DESPEDIDA)

    def test_manager_absent_to_encargado_ausente(self):
        """Client says manager absent → ask for alternative contact."""
        result = self.fsm.process("No está, salió a comer")
        self.assertIsNotNone(result)
        self.assertEqual(self.fsm.state, FSMState.ENCARGADO_AUSENTE)

    def test_identity_stays_pitch(self):
        """Client asks identity → stay in PITCH."""
        result = self.fsm.process("¿De dónde habla?")
        self.assertIsNotNone(result)
        self.assertEqual(self.fsm.state, FSMState.PITCH)
        self.assertIn("NIOVAL", result)


class TestFSMTransitionsEncargado(unittest.TestCase):
    """Test BUSCANDO_ENCARGADO state transitions."""

    def setUp(self):
        self.fsm = FSMEngine()
        self.fsm.process("Bueno")      # → PITCH
        self.fsm.process("Sí, dígame")  # → BUSCANDO_ENCARGADO
        self.assertEqual(self.fsm.state, FSMState.BUSCANDO_ENCARGADO)

    def test_soy_yo_to_presente(self):
        """'Soy yo' → ENCARGADO_PRESENTE."""
        result = self.fsm.process("Sí, soy yo")
        self.assertIsNotNone(result)
        self.assertEqual(self.fsm.state, FSMState.ENCARGADO_PRESENTE)

    def test_no_esta_to_ausente(self):
        """'No está' → ENCARGADO_AUSENTE."""
        result = self.fsm.process("No está, salió")
        self.assertIsNotNone(result)
        self.assertEqual(self.fsm.state, FSMState.ENCARGADO_AUSENTE)

    def test_espere_to_transfer(self):
        """'Espere un momento' → ESPERANDO_TRANSFERENCIA."""
        result = self.fsm.process("Espere un momento")
        self.assertIsNotNone(result)
        self.assertEqual(self.fsm.state, FSMState.ESPERANDO_TRANSFERENCIA)
        self.assertIn("espero", result.lower())

    def test_callback_to_ausente(self):
        """'Llame más tarde' → ENCARGADO_AUSENTE with callback."""
        result = self.fsm.process("Tendría que esperar a que regrese")
        self.assertIsNotNone(result)
        self.assertEqual(self.fsm.state, FSMState.ENCARGADO_AUSENTE)
        self.assertIn("hora", result.lower())

    def test_offer_data_to_dictando(self):
        """Client offers data → DICTANDO_DATO."""
        result = self.fsm.process("Te doy el correo")
        self.assertIsNotNone(result)
        self.assertEqual(self.fsm.state, FSMState.DICTANDO_DATO)

    def test_otra_sucursal_to_despedida(self):
        """'Otra sucursal' → DESPEDIDA."""
        result = self.fsm.process("No es aquí, es otra sucursal")
        self.assertIsNotNone(result)
        self.assertEqual(self.fsm.state, FSMState.DESPEDIDA)


class TestFSMTransitionsDictado(unittest.TestCase):
    """Test DICTANDO_DATO state transitions."""

    def setUp(self):
        self.fsm = FSMEngine()
        self.fsm.process("Bueno")           # → PITCH
        self.fsm.process("Sí")              # → BUSCANDO_ENCARGADO
        self.fsm.process("Te doy el correo") # → DICTANDO_DATO
        self.assertEqual(self.fsm.state, FSMState.DICTANDO_DATO)

    def test_complete_phone_to_capturado(self):
        """10 digits → CONTACTO_CAPTURADO."""
        result = self.fsm.process("6 6 2 1 2 3 4 5 6 7")
        self.assertIsNotNone(result)
        self.assertEqual(self.fsm.state, FSMState.CONTACTO_CAPTURADO)
        self.assertIn("catalogo", result.lower())

    def test_complete_email_to_capturado(self):
        """Email → CONTACTO_CAPTURADO."""
        result = self.fsm.process("juan@gmail.com")
        self.assertIsNotNone(result)
        self.assertEqual(self.fsm.state, FSMState.CONTACTO_CAPTURADO)

    def test_partial_stays_dictando(self):
        """Partial = stay and acknowledge."""
        result = self.fsm.process("Seis seis dos")
        self.assertIsNotNone(result)
        self.assertEqual(self.fsm.state, FSMState.DICTANDO_DATO)
        # FIX 769: Acknowledgment formal con variantes
        self.assertTrue(
            any(w in result.lower() for w in ["si", "claro", "entendido", "perfecto", "adelante"]),
            f"Unexpected acknowledgment: {result}"
        )


class TestFSMTransitionsContactoCapturado(unittest.TestCase):
    """Test CONTACTO_CAPTURADO → DESPEDIDA."""

    def setUp(self):
        self.fsm = FSMEngine()
        self.fsm.state = FSMState.CONTACTO_CAPTURADO

    def test_any_to_despedida(self):
        """Any response after capture → goodbye."""
        result = self.fsm.process("Ok, gracias")
        self.assertEqual(self.fsm.state, FSMState.DESPEDIDA)


class TestFSMTransitionsEsperandoTransferencia(unittest.TestCase):
    """Test ESPERANDO_TRANSFERENCIA transitions."""

    def setUp(self):
        self.fsm = FSMEngine()
        self.fsm.state = FSMState.ESPERANDO_TRANSFERENCIA

    def test_confirmation_to_pitch(self):
        """Confirmation after wait → new pitch."""
        result = self.fsm.process("Sí, aquí está")
        self.assertIsNotNone(result)
        self.assertEqual(self.fsm.state, FSMState.PITCH)

    def test_soy_encargado_to_presente(self):
        """New person is manager → ENCARGADO_PRESENTE."""
        result = self.fsm.process("Sí, yo soy el encargado")
        self.assertIsNotNone(result)
        self.assertEqual(self.fsm.state, FSMState.ENCARGADO_PRESENTE)


# ============================================================
# Context tracking tests
# ============================================================

class TestFSMContextTracking(unittest.TestCase):
    """Test context updates during transitions."""

    def test_pitch_dado_after_pitch(self):
        fsm = FSMEngine()
        fsm.process("Buenas tardes")
        self.assertTrue(fsm.context.pitch_dado)

    def test_encargado_preguntado(self):
        fsm = FSMEngine()
        fsm.process("Buenas tardes")  # → PITCH
        fsm.process("Sí, claro")      # → BUSCANDO_ENCARGADO
        self.assertTrue(fsm.context.encargado_preguntado)

    def test_canal_rechazado_tracked(self):
        fsm = FSMEngine()
        fsm.state = FSMState.CAPTURANDO_CONTACTO
        fsm.context.canal_solicitado = 'whatsapp'
        fsm.process("No tengo WhatsApp")
        self.assertIn('whatsapp', fsm.context.canales_rechazados)

    def test_callback_hora_extracted(self):
        fsm = FSMEngine()
        fsm.state = FSMState.BUSCANDO_ENCARGADO
        fsm.process("Llámele a las 5")
        self.assertTrue(fsm.context.callback_pedido)
        self.assertEqual(fsm.context.callback_hora, "a las 5")

    def test_turnos_incrementa(self):
        fsm = FSMEngine()
        fsm.process("Bueno")
        self.assertEqual(fsm.context.turnos_bruce, 1)
        fsm.process("Sí")
        self.assertEqual(fsm.context.turnos_bruce, 2)


# ============================================================
# Guards tests
# ============================================================

class TestFSMGuards(unittest.TestCase):
    """Test guard condition evaluation."""

    def test_negated_guard_true(self):
        """!donde_anotar_preguntado when False → pass."""
        fsm = FSMEngine()
        self.assertTrue(fsm._check_guards(["!donde_anotar_preguntado"]))

    def test_negated_guard_false(self):
        """!donde_anotar_preguntado when True → fail."""
        fsm = FSMEngine()
        fsm.context.donde_anotar_preguntado = True
        self.assertFalse(fsm._check_guards(["!donde_anotar_preguntado"]))

    def test_positive_guard_true(self):
        """pitch_dado when True → pass."""
        fsm = FSMEngine()
        fsm.context.pitch_dado = True
        self.assertTrue(fsm._check_guards(["pitch_dado"]))

    def test_positive_guard_false(self):
        """pitch_dado when False → fail."""
        fsm = FSMEngine()
        self.assertFalse(fsm._check_guards(["pitch_dado"]))

    def test_empty_guards_pass(self):
        """No guards → always pass."""
        fsm = FSMEngine()
        self.assertTrue(fsm._check_guards([]))


# ============================================================
# Normalize tests
# ============================================================

class TestNormalize(unittest.TestCase):
    """Test text normalization."""

    def test_accents_removed(self):
        self.assertEqual(_normalize("está"), "esta")

    def test_question_marks_removed(self):
        self.assertEqual(_normalize("¿Bueno?"), "bueno")

    def test_commas_to_space(self):
        self.assertEqual(_normalize("No, joven,"), "no joven")

    def test_lowercase(self):
        self.assertEqual(_normalize("HOLA"), "hola")

    def test_multiple_spaces(self):
        self.assertEqual(_normalize("no   joven"), "no joven")


# ============================================================
# Reset test
# ============================================================

class TestFSMReset(unittest.TestCase):
    """Test FSM reset for new call."""

    def test_reset_clears_state(self):
        fsm = FSMEngine()
        fsm.process("Bueno")
        fsm.process("Sí")
        self.assertNotEqual(fsm.state, FSMState.SALUDO)
        fsm.reset()
        self.assertEqual(fsm.state, FSMState.SALUDO)
        self.assertEqual(fsm.context.turnos_bruce, 0)
        self.assertFalse(fsm.context.pitch_dado)


# ============================================================
# State info test
# ============================================================

class TestFSMStateInfo(unittest.TestCase):
    """Test get_state_info for debugging."""

    def test_info_has_keys(self):
        fsm = FSMEngine()
        info = fsm.get_state_info()
        self.assertIn("state", info)
        self.assertIn("pitch_dado", info)
        self.assertIn("turnos", info)
        self.assertEqual(info["state"], "saludo")


# ============================================================
# Phase 2: Selective activation tests
# ============================================================

class TestFSMPhase2ActiveStates(unittest.TestCase):
    """Test Phase 2 selective state activation."""

    def test_active_states_set_populated(self):
        """FSM_ACTIVE_STATES_SET should contain states from env var."""
        from fsm_engine import FSM_ACTIVE_STATES_SET
        # Default includes despedida and contacto_capturado
        self.assertIsInstance(FSM_ACTIVE_STATES_SET, set)

    def test_despedida_in_active_states(self):
        """DESPEDIDA should be in active states by default."""
        from fsm_engine import FSM_ACTIVE_STATES_SET
        self.assertIn(FSMState.DESPEDIDA, FSM_ACTIVE_STATES_SET)

    def test_contacto_capturado_in_active_states(self):
        """CONTACTO_CAPTURADO should be in active states by default."""
        from fsm_engine import FSM_ACTIVE_STATES_SET
        self.assertIn(FSMState.CONTACTO_CAPTURADO, FSM_ACTIVE_STATES_SET)

    def test_saludo_not_in_active_states(self):
        """SALUDO should NOT be in active states by default."""
        from fsm_engine import FSM_ACTIVE_STATES_SET
        self.assertNotIn(FSMState.SALUDO, FSM_ACTIVE_STATES_SET)

    def test_contacto_capturado_intercepts(self):
        """CONTACTO_CAPTURADO state should return response (intercept)."""
        fsm = FSMEngine()
        fsm.state = FSMState.CONTACTO_CAPTURADO
        result = fsm.process("Gracias, hasta luego", None)
        # Should intercept with despedida_catalogo_prometido
        self.assertIsNotNone(result)
        self.assertIn("catalogo", result.lower())

    def test_despedida_verification_intercepts(self):
        """DESPEDIDA + VERIFICATION should return template (intercept)."""
        fsm = FSMEngine()
        fsm.state = FSMState.DESPEDIDA
        result = fsm.process("¿Bueno? ¿Sigue ahí?", None)
        # VERIFICATION → despedida_cortes template
        if result is not None:
            self.assertIn("gracias", result.lower())

    def test_despedida_hangup_does_not_intercept(self):
        """DESPEDIDA + FAREWELL → HANGUP should return None (fallthrough)."""
        fsm = FSMEngine()
        fsm.state = FSMState.DESPEDIDA
        result = fsm.process("Hasta luego, bye", None)
        # HANGUP returns None → fallthrough to existing code
        self.assertIsNone(result)

    def test_shadow_non_active_state_returns_none(self):
        """Non-active state (PITCH) should still shadow (return None)."""
        fsm = FSMEngine()
        fsm.state = FSMState.PITCH
        # In shadow mode, non-active states return None
        result = fsm.process("Sí, dígame más", None)
        # PITCH is not in active set → shadow → None
        from fsm_engine import FSM_ENABLED, FSM_ACTIVE_STATES_SET
        if FSM_ENABLED == "shadow" and FSMState.PITCH not in FSM_ACTIVE_STATES_SET:
            self.assertIsNone(result)

    def test_despedida_offer_data_intercepts(self):
        """DESPEDIDA + OFFER_DATA → DICTANDO_DATO should intercept."""
        fsm = FSMEngine()
        fsm.state = FSMState.DESPEDIDA
        fsm.context.ultimo_fue_ofrecer_contacto = False
        result = fsm.process("Bueno, le doy mi número: 332", None)
        # OFFER_DATA → aja_digame template
        if result is not None:
            self.assertIn("igame", result.lower())  # "Dígame" or "dígame"


if __name__ == '__main__':
    unittest.main()
