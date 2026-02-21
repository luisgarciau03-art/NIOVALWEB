"""
tests/test_fsm_integration.py - Tests end-to-end de flujos conversacionales FSM.

Simula conversaciones completas desde SALUDO hasta DESPEDIDA para verificar
que la FSM maneja correctamente los flujos más comunes.
"""
import unittest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Force active mode for tests (FSM intercepta y retorna respuestas)
os.environ["FSM_ENABLED"] = "active"

from fsm_engine import FSMEngine, FSMState, FSMContext


class TestFlowHappyPath(unittest.TestCase):
    """Happy path: saludo → pitch → encargado → contacto → despedida."""

    def setUp(self):
        self.fsm = FSMEngine()

    def test_complete_whatsapp_capture(self):
        """Full flow: greeting → pitch → manager present → whatsapp → dictation → goodbye."""
        # Turno 1: Cliente contesta
        r1 = self.fsm.process("Bueno, sí diga")
        self.assertIsNotNone(r1)
        self.assertEqual(self.fsm.state, FSMState.PITCH)
        self.assertIn("NIOVAL", r1)

        # Turno 2: Cliente acepta, pregunta quién habla
        r2 = self.fsm.process("¿De dónde llama?")
        self.assertIsNotNone(r2)
        self.assertEqual(self.fsm.state, FSMState.PITCH)
        self.assertIn("Bruce", r2)

        # Turno 3: Cliente confirma interés
        r3 = self.fsm.process("Ah ok, sí, yo soy el encargado")
        self.assertIsNotNone(r3)
        self.assertEqual(self.fsm.state, FSMState.ENCARGADO_PRESENTE)
        self.assertTrue(self.fsm.context.encargado_es_interlocutor)

        # Turno 4: Encargado acepta catálogo - "por WhatsApp" = offer_data
        r4 = self.fsm.process("Sí, al WhatsApp, anote")
        self.assertIsNotNone(r4)
        # Should be in DICTANDO_DATO (offer_data → acknowledge)
        self.assertEqual(self.fsm.state, FSMState.DICTANDO_DATO)

        # Turno 5: Cliente dicta número
        r5 = self.fsm.process("3312345678")
        self.assertIsNotNone(r5)
        self.assertEqual(self.fsm.state, FSMState.CONTACTO_CAPTURADO)
        self.assertIn("registrado", r5.lower())

        # Turno 6: Despedida
        r6 = self.fsm.process("Gracias, igualmente")
        self.assertIsNotNone(r6)
        self.assertEqual(self.fsm.state, FSMState.DESPEDIDA)

    def test_email_capture_flow(self):
        """Flow with email capture instead of WhatsApp."""
        self.fsm.process("Sí, dígame")  # → PITCH
        self.fsm.process("Sí, yo soy el encargado")  # → ENCARGADO_PRESENTE
        self.fsm.process("Sí, mándemelo por correo")  # → CAPTURANDO/DICTANDO

        # Client dictates email
        r = self.fsm.process("ventas@ferreteria.com")
        self.assertIsNotNone(r)
        self.assertEqual(self.fsm.state, FSMState.CONTACTO_CAPTURADO)
        self.assertIn("correo", r.lower())


class TestFlowManagerAbsent(unittest.TestCase):
    """Flow when manager is not available."""

    def setUp(self):
        self.fsm = FSMEngine()

    def test_manager_absent_offer_contact(self):
        """Manager absent → ask for contact → client provides WhatsApp."""
        self.fsm.process("Bueno")  # → PITCH
        self.assertEqual(self.fsm.state, FSMState.PITCH)

        r2 = self.fsm.process("No, no está, salió a comer")
        self.assertIsNotNone(r2)
        self.assertEqual(self.fsm.state, FSMState.ENCARGADO_AUSENTE)

        # Client offers contact
        r3 = self.fsm.process("Le paso su WhatsApp, anote")
        self.assertIsNotNone(r3)
        self.assertEqual(self.fsm.state, FSMState.DICTANDO_DATO)

        r4 = self.fsm.process("3387654321")
        self.assertIsNotNone(r4)
        self.assertEqual(self.fsm.state, FSMState.CONTACTO_CAPTURADO)

    def test_manager_absent_reject_all_contacts(self):
        """Manager absent → client rejects all contact methods → offer Bruce's number."""
        self.fsm.process("Sí diga")  # → PITCH
        self.fsm.process("No, no se encuentra")  # → ENCARGADO_AUSENTE

        r3 = self.fsm.process("No, no le puedo dar ningún dato")
        self.assertIsNotNone(r3)
        # reject_data in ENCARGADO_AUSENTE → OFRECIENDO_CONTACTO
        self.assertEqual(self.fsm.state, FSMState.OFRECIENDO_CONTACTO)

    def test_manager_absent_reject_whatsapp(self):
        """Manager absent → reject WhatsApp specifically."""
        self.fsm.process("Sí diga")
        self.fsm.process("No está")
        r = self.fsm.process("No tengo WhatsApp")
        self.assertIsNotNone(r)

    def test_manager_absent_callback(self):
        """Manager absent → callback scheduling."""
        self.fsm.process("Diga")  # → PITCH
        r2 = self.fsm.process("No está, llame más tarde")
        self.assertIsNotNone(r2)
        self.assertEqual(self.fsm.state, FSMState.ENCARGADO_AUSENTE)


class TestFlowTransfer(unittest.TestCase):
    """Flow with call transfer."""

    def setUp(self):
        self.fsm = FSMEngine()

    def test_transfer_to_new_person(self):
        """Transfer → new person answers → pitch → contact."""
        self.fsm.process("Sí, diga")  # → PITCH
        self.fsm.state = FSMState.BUSCANDO_ENCARGADO  # Simular que ya preguntó

        r = self.fsm.process("Espéreme un momento")
        self.assertIsNotNone(r)
        self.assertEqual(self.fsm.state, FSMState.ESPERANDO_TRANSFERENCIA)

        # New person comes on
        r2 = self.fsm.process("Sí, bueno, ¿quién habla?")
        self.assertIsNotNone(r2)
        self.assertEqual(self.fsm.state, FSMState.PITCH)
        self.assertIn("NIOVAL", r2)

    def test_transfer_manager_comes(self):
        """Transfer → manager answers directly."""
        self.fsm.state = FSMState.ESPERANDO_TRANSFERENCIA
        r = self.fsm.process("Sí, yo soy el encargado de compras")
        self.assertIsNotNone(r)
        self.assertEqual(self.fsm.state, FSMState.ENCARGADO_PRESENTE)


class TestFlowRejection(unittest.TestCase):
    """Flow with immediate rejection."""

    def setUp(self):
        self.fsm = FSMEngine()

    def test_immediate_no_interest(self):
        """Client rejects immediately → polite goodbye."""
        self.fsm.process("Sí diga")  # → PITCH
        r = self.fsm.process("No me interesa, gracias")
        self.assertIsNotNone(r)
        self.assertEqual(self.fsm.state, FSMState.DESPEDIDA)

    def test_not_a_store(self):
        """Client says it's not a hardware store → goodbye."""
        self.fsm.process("Bueno")  # → PITCH
        r = self.fsm.process("Aquí es un taller, no ferretería")
        self.assertIsNotNone(r)
        self.assertEqual(self.fsm.state, FSMState.DESPEDIDA)

    def test_no_purchases_here(self):
        """Client says they don't make purchases."""
        self.fsm.process("Dígame")  # → PITCH
        r = self.fsm.process("No hacemos compras aquí")
        self.assertIsNotNone(r)
        self.assertEqual(self.fsm.state, FSMState.DESPEDIDA)

    def test_farewell_at_saludo(self):
        """Client hangs up at greeting."""
        r = self.fsm.process("No gracias, hasta luego")
        self.assertIsNotNone(r)
        self.assertEqual(self.fsm.state, FSMState.DESPEDIDA)


class TestFlowDictation(unittest.TestCase):
    """Detailed dictation flow tests."""

    def setUp(self):
        self.fsm = FSMEngine()
        self.fsm.state = FSMState.CAPTURANDO_CONTACTO

    def test_partial_then_complete_phone(self):
        """Client dictates phone in 2 parts."""
        r1 = self.fsm.process("331 234")
        self.assertIsNotNone(r1)
        self.assertEqual(self.fsm.state, FSMState.DICTANDO_DATO)

        r2 = self.fsm.process("5678")
        self.assertIsNotNone(r2)
        # Stays in DICTANDO_DATO (partial still)
        self.assertEqual(self.fsm.state, FSMState.DICTANDO_DATO)

    def test_complete_phone_immediate(self):
        """Client dictates full 10-digit phone at once."""
        r = self.fsm.process("33 12 34 56 78")
        self.assertIsNotNone(r)
        self.assertEqual(self.fsm.state, FSMState.CONTACTO_CAPTURADO)

    def test_email_with_at_symbol(self):
        """Client provides email with @ symbol."""
        r = self.fsm.process("contacto@gmail.com")
        self.assertIsNotNone(r)
        self.assertEqual(self.fsm.state, FSMState.CONTACTO_CAPTURADO)

    def test_verbal_email(self):
        """Client dictates email verbally."""
        r = self.fsm.process("ventas arroba ferreteria punto com")
        self.assertIsNotNone(r)
        self.assertEqual(self.fsm.state, FSMState.CONTACTO_CAPTURADO)


class TestFlowOtherBranch(unittest.TestCase):
    """Client says it's another branch."""

    def setUp(self):
        self.fsm = FSMEngine()

    def test_otra_sucursal(self):
        """Client says it's a different branch."""
        self.fsm.process("Sí diga")  # → PITCH
        self.fsm.state = FSMState.BUSCANDO_ENCARGADO

        r = self.fsm.process("No, aquí no es, es la otra sucursal")
        self.assertIsNotNone(r)
        self.assertEqual(self.fsm.state, FSMState.DESPEDIDA)


class TestFlowOfferBruceContact(unittest.TestCase):
    """Flow where Bruce offers his own contact."""

    def setUp(self):
        self.fsm = FSMEngine()
        self.fsm.state = FSMState.OFRECIENDO_CONTACTO

    def test_client_accepts_bruce_number(self):
        """Client accepts to take Bruce's number."""
        r = self.fsm.process("Sí, dígame")
        self.assertIsNotNone(r)
        # Should offer to dictate number
        self.assertIn(self.fsm.state, [FSMState.OFRECIENDO_CONTACTO, FSMState.DESPEDIDA])

    def test_client_rejects_bruce_number(self):
        """Client rejects Bruce's number."""
        r = self.fsm.process("No, gracias")
        self.assertIsNotNone(r)
        self.assertEqual(self.fsm.state, FSMState.DESPEDIDA)


class TestFlowContextPreservation(unittest.TestCase):
    """Test that context is preserved across multiple turns."""

    def setUp(self):
        self.fsm = FSMEngine()

    def test_pitch_dado_persists(self):
        """pitch_dado stays True after initial pitch."""
        self.fsm.process("Bueno")  # → PITCH
        self.assertTrue(self.fsm.context.pitch_dado)

        self.fsm.process("¿De dónde llama?")  # identity → stays PITCH
        self.assertTrue(self.fsm.context.pitch_dado)

    def test_turnos_count(self):
        """Turnos increment with each process call."""
        self.fsm.process("Bueno")
        self.assertEqual(self.fsm.context.turnos_bruce, 1)

        self.fsm.process("Sí, yo soy el encargado")
        self.assertEqual(self.fsm.context.turnos_bruce, 2)

        self.fsm.process("Sí claro")
        self.assertEqual(self.fsm.context.turnos_bruce, 3)

    def test_encargado_flag_persists(self):
        """encargado_es_interlocutor persists through flow."""
        self.fsm.process("Diga")  # → PITCH
        self.fsm.process("Yo soy el encargado")  # → ENCARGADO_PRESENTE
        self.assertTrue(self.fsm.context.encargado_es_interlocutor)

        self.fsm.process("Sí, mándame el catálogo")
        self.assertTrue(self.fsm.context.encargado_es_interlocutor)


class TestFlowShadowMode(unittest.TestCase):
    """Test shadow mode behavior."""

    def test_shadow_returns_none(self):
        """Shadow mode should return None (no interception)."""
        import fsm_engine
        original = fsm_engine.FSM_ENABLED
        fsm_engine.FSM_ENABLED = "shadow"
        try:
            fsm_shadow = FSMEngine()
            result = fsm_shadow.process("Bueno")
            self.assertIsNone(result)
            # Shadow mode does NOT update state (returns before update)
        finally:
            fsm_engine.FSM_ENABLED = original

    def test_active_returns_response(self):
        """Active mode should return actual response."""
        # Already in active mode (set at module level)
        fsm_active = FSMEngine()
        result = fsm_active.process("Bueno")
        self.assertIsNotNone(result)
        self.assertIn("NIOVAL", result)


class TestFlowEdgeCases(unittest.TestCase):
    """Edge cases from production bugs."""

    def setUp(self):
        self.fsm = FSMEngine()

    def test_esperar_a_que_regrese_is_callback(self):
        """FIX 645: 'esperar a que regrese' = CALLBACK, not TRANSFER."""
        self.fsm.process("Diga")  # → PITCH
        self.fsm.state = FSMState.BUSCANDO_ENCARGADO

        r = self.fsm.process("Tendría que esperar a que regrese")
        self.assertIsNotNone(r)
        # Should go to ENCARGADO_AUSENTE (callback), NOT ESPERANDO_TRANSFERENCIA
        self.assertEqual(self.fsm.state, FSMState.ENCARGADO_AUSENTE)

    def test_empty_text_handled(self):
        """Empty/whitespace text doesn't crash."""
        # Should not raise exception
        try:
            r = self.fsm.process("")
        except Exception as e:
            self.fail(f"process('') raised {e}")

    def test_very_long_text_handled(self):
        """Very long text doesn't crash."""
        long_text = "Sí mire, le comento que " * 50
        try:
            r = self.fsm.process(long_text)
        except Exception as e:
            self.fail(f"process(long_text) raised {e}")

    def test_no_hacemos_compras_immediate_exit(self):
        """FIX 710: 'No hacemos compras' = rejection → goodbye."""
        self.fsm.process("Bueno")
        r = self.fsm.process("No, aquí no hacemos compras")
        self.assertIsNotNone(r)
        self.assertEqual(self.fsm.state, FSMState.DESPEDIDA)

    def test_numbers_in_words_detected(self):
        """FIX 670/714: Numbers dictated as words should be detected."""
        self.fsm.state = FSMState.CAPTURANDO_CONTACTO
        r = self.fsm.process("tres tres uno dos tres cuatro cinco seis siete ocho")
        self.assertIsNotNone(r)
        # Should detect as dictation (complete phone)
        self.assertIn(self.fsm.state, [FSMState.CONTACTO_CAPTURADO, FSMState.DICTANDO_DATO])


class TestFlowMultipleRejections(unittest.TestCase):
    """Test channel rejection flow."""

    def setUp(self):
        self.fsm = FSMEngine()
        self.fsm.state = FSMState.CAPTURANDO_CONTACTO

    def test_reject_whatsapp_ask_correo(self):
        """Client rejects WhatsApp → Bruce asks for email."""
        self.fsm.context.canal_solicitado = "whatsapp"
        r = self.fsm.process("No tengo WhatsApp")
        self.assertIsNotNone(r)
        self.assertIn("whatsapp", self.fsm.context.canales_rechazados)

    def test_reject_correo_ask_telefono(self):
        """Client rejects email → Bruce asks for phone."""
        self.fsm.context.canal_solicitado = "correo"
        self.fsm.context.canales_rechazados = ["whatsapp"]
        r = self.fsm.process("No tengo correo")
        self.assertIsNotNone(r)
        self.assertIn("correo", self.fsm.context.canales_rechazados)


class TestFSMShadowStateTracking(unittest.TestCase):
    """FIX 1: Shadow mode must update state across turns."""

    def test_shadow_updates_state(self):
        """Shadow mode updates state even though it returns None."""
        import fsm_engine
        original = fsm_engine.FSM_ENABLED
        fsm_engine.FSM_ENABLED = "shadow"
        try:
            fsm = FSMEngine()
            fsm.process("Bueno")  # → PITCH (returns None)
            self.assertEqual(fsm.state, FSMState.PITCH)

            fsm.process("No está el encargado")  # → ENCARGADO_AUSENTE
            self.assertEqual(fsm.state, FSMState.ENCARGADO_AUSENTE)
        finally:
            fsm_engine.FSM_ENABLED = original

    def test_shadow_tracks_context(self):
        """Shadow mode updates context (pitch_dado, etc)."""
        import fsm_engine
        original = fsm_engine.FSM_ENABLED
        fsm_engine.FSM_ENABLED = "shadow"
        try:
            fsm = FSMEngine()
            fsm.process("Diga")
            self.assertTrue(fsm.context.pitch_dado)
            self.assertEqual(fsm.context.turnos_bruce, 1)
        finally:
            fsm_engine.FSM_ENABLED = original


class TestContextualNo(unittest.TestCase):
    """FIX 2: Bare 'No' after encargado question = MANAGER_ABSENT."""

    def test_bare_no_after_encargado(self):
        """'No' after asking for encargado → MANAGER_ABSENT."""
        fsm = FSMEngine()
        fsm.process("Sí diga")  # → PITCH
        fsm.state = FSMState.BUSCANDO_ENCARGADO
        fsm.context.encargado_preguntado = True

        r = fsm.process("No")
        self.assertIsNotNone(r)
        self.assertEqual(fsm.state, FSMState.ENCARGADO_AUSENTE)

    def test_no_fijese_after_encargado(self):
        """'No, fíjese' after asking for encargado → MANAGER_ABSENT."""
        fsm = FSMEngine()
        fsm.state = FSMState.BUSCANDO_ENCARGADO
        fsm.context.encargado_preguntado = True

        r = fsm.process("No fíjese")
        self.assertIsNotNone(r)
        self.assertEqual(fsm.state, FSMState.ENCARGADO_AUSENTE)

    def test_bare_no_without_encargado_context(self):
        """'No' without encargado context → NOT MANAGER_ABSENT."""
        from fsm_engine import classify_intent, FSMIntent
        ctx = FSMContext()
        ctx.encargado_preguntado = False
        intent = classify_intent("No", ctx, FSMState.PITCH)
        self.assertNotEqual(intent, FSMIntent.MANAGER_ABSENT)


class TestCallbackVieneHasta(unittest.TestCase):
    """FIX 3: 'viene hasta el [día]' = CALLBACK."""

    def test_viene_hasta_el_lunes(self):
        """'viene hasta el lunes' → CALLBACK."""
        from fsm_engine import classify_intent, FSMIntent
        ctx = FSMContext()
        intent = classify_intent("viene hasta el lunes", ctx, FSMState.BUSCANDO_ENCARGADO)
        self.assertEqual(intent, FSMIntent.CALLBACK)

    def test_regresa_el_martes(self):
        """'regresa el martes' → CALLBACK."""
        from fsm_engine import classify_intent, FSMIntent
        ctx = FSMContext()
        intent = classify_intent("regresa el martes", ctx, FSMState.BUSCANDO_ENCARGADO)
        self.assertEqual(intent, FSMIntent.CALLBACK)

    def test_llega_hasta_el_miercoles(self):
        """'llega hasta el miércoles' → CALLBACK."""
        from fsm_engine import classify_intent, FSMIntent
        ctx = FSMContext()
        intent = classify_intent("llega hasta el miércoles", ctx, FSMState.BUSCANDO_ENCARGADO)
        self.assertEqual(intent, FSMIntent.CALLBACK)


class TestMidSentenceDetection(unittest.TestCase):
    """FIX 4: Text ending in comma = CONTINUATION (mid-sentence)."""

    def test_comma_ending_short(self):
        """Short text ending in comma → CONTINUATION."""
        from fsm_engine import classify_intent, FSMIntent
        ctx = FSMContext()
        intent = classify_intent("No, no se encuentra,", ctx, FSMState.BUSCANDO_ENCARGADO)
        self.assertEqual(intent, FSMIntent.CONTINUATION)

    def test_comma_ending_dictation(self):
        """Dictation mid-sentence with comma."""
        from fsm_engine import classify_intent, FSMIntent
        ctx = FSMContext()
        intent = classify_intent("331 234,", ctx, FSMState.DICTANDO_DATO)
        self.assertEqual(intent, FSMIntent.CONTINUATION)

    def test_no_comma_processes_normally(self):
        """Without comma, normal classification."""
        from fsm_engine import classify_intent, FSMIntent
        ctx = FSMContext()
        intent = classify_intent("No, no se encuentra", ctx, FSMState.BUSCANDO_ENCARGADO)
        self.assertEqual(intent, FSMIntent.MANAGER_ABSENT)


class TestDespedidaRecovery(unittest.TestCase):
    """FIX 5: Recovery from DESPEDIDA when client accepts Bruce's number."""

    def test_confirmation_after_ofrecer_contacto(self):
        """Client says 'ok' after Bruce offered number → dictar número."""
        fsm = FSMEngine()
        fsm.state = FSMState.DESPEDIDA
        fsm.context.ultimo_fue_ofrecer_contacto = True

        r = fsm.process("Ok, está bien")
        self.assertIsNotNone(r)
        self.assertIn("662", r)  # Bruce's number

    def test_confirmation_without_ofrecer_goes_hangup(self):
        """Normal DESPEDIDA + confirmation → HANGUP (no recovery)."""
        fsm = FSMEngine()
        fsm.state = FSMState.DESPEDIDA
        fsm.context.ultimo_fue_ofrecer_contacto = False

        r = fsm.process("Ok")
        # HANGUP returns None
        self.assertIsNone(r)

    def test_offer_data_from_despedida(self):
        """Client offers data from DESPEDIDA → DICTANDO_DATO."""
        fsm = FSMEngine()
        fsm.state = FSMState.DESPEDIDA

        r = fsm.process("Le paso mi número, anote")
        self.assertIsNotNone(r)
        self.assertEqual(fsm.state, FSMState.DICTANDO_DATO)


if __name__ == '__main__':
    unittest.main()
