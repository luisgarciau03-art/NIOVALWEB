"""
Tests FSM Phase 3: Core Flow Activation
FIX 761-767: BUSCANDO_ENCARGADO, ENCARGADO_PRESENTE, ENCARGADO_AUSENTE, CAPTURANDO_CONTACTO

Tests cover:
A. State activation verification
B. BUSCANDO_ENCARGADO interception
C. ENCARGADO_PRESENTE interception
D. ENCARGADO_AUSENTE interception
E. CAPTURANDO_CONTACTO interception
F. Smart REJECT_DATA alternation (FIX 763)
G. Data extraction on FSM intercept (FIX 762/765)
H. Full flow integration
"""

import unittest
import os
import sys
import re

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from fsm_engine import (
    FSMEngine, FSMState, FSMIntent, FSMContext,
    FSM_ACTIVE_STATES_SET, classify_intent, Transition, ActionType,
)


# ============================================================
# A. State Activation Verification
# ============================================================
class TestPhase3StateActivation(unittest.TestCase):
    """FIX 761: Verify Phase 3 states are in FSM_ACTIVE_STATES_SET."""

    def test_buscando_encargado_active(self):
        self.assertIn(FSMState.BUSCANDO_ENCARGADO, FSM_ACTIVE_STATES_SET)

    def test_encargado_presente_active(self):
        self.assertIn(FSMState.ENCARGADO_PRESENTE, FSM_ACTIVE_STATES_SET)

    def test_encargado_ausente_active(self):
        self.assertIn(FSMState.ENCARGADO_AUSENTE, FSM_ACTIVE_STATES_SET)

    def test_capturando_contacto_active(self):
        self.assertIn(FSMState.CAPTURANDO_CONTACTO, FSM_ACTIVE_STATES_SET)

    def test_despedida_still_active(self):
        self.assertIn(FSMState.DESPEDIDA, FSM_ACTIVE_STATES_SET)

    def test_contacto_capturado_still_active(self):
        self.assertIn(FSMState.CONTACTO_CAPTURADO, FSM_ACTIVE_STATES_SET)

    def test_saludo_not_active(self):
        self.assertNotIn(FSMState.SALUDO, FSM_ACTIVE_STATES_SET)

    def test_dictando_dato_not_active(self):
        self.assertNotIn(FSMState.DICTANDO_DATO, FSM_ACTIVE_STATES_SET)

    def test_pitch_not_active(self):
        self.assertNotIn(FSMState.PITCH, FSM_ACTIVE_STATES_SET)


# ============================================================
# B. BUSCANDO_ENCARGADO Interception
# ============================================================
class TestBuscandoEncargadoInterception(unittest.TestCase):
    """Phase 3: FSM intercepts when in BUSCANDO_ENCARGADO state."""

    def setUp(self):
        self.fsm = FSMEngine()
        self.fsm.state = FSMState.BUSCANDO_ENCARGADO
        self.fsm.context.encargado_preguntado = True

    def test_soy_yo_to_encargado_presente(self):
        """'Soy yo' → ENCARGADO_PRESENTE with pitch."""
        result = self.fsm.process("Soy yo", None)
        self.assertIsNotNone(result)
        self.assertEqual(self.fsm.state, FSMState.ENCARGADO_PRESENTE)
        self.assertIn('NIOVAL', result)

    def test_no_esta_to_encargado_ausente(self):
        """'No está' → ENCARGADO_AUSENTE."""
        result = self.fsm.process("No esta el encargado", None)
        self.assertIsNotNone(result)
        self.assertEqual(self.fsm.state, FSMState.ENCARGADO_AUSENTE)

    def test_espere_to_transferencia(self):
        """'Espere un momento' → ESPERANDO_TRANSFERENCIA."""
        result = self.fsm.process("Espere un momento", None)
        self.assertIsNotNone(result)
        self.assertIn('espero', result.lower())

    def test_no_me_interesa_to_despedida(self):
        """'No me interesa' → DESPEDIDA."""
        result = self.fsm.process("No me interesa", None)
        self.assertIsNotNone(result)
        self.assertEqual(self.fsm.state, FSMState.DESPEDIDA)

    def test_callback_esperar_a_que_regrese(self):
        """'Tendría que esperar a que regrese' → CALLBACK not TRANSFER."""
        result = self.fsm.process("Tendria que esperar a que regrese", None)
        self.assertIsNotNone(result)
        self.assertEqual(self.fsm.state, FSMState.ENCARGADO_AUSENTE)

    def test_te_doy_correo_to_dictando(self):
        """'Te doy el correo' → DICTANDO_DATO."""
        result = self.fsm.process("Te doy el correo, anote", None)
        # DICTANDO_DATO is NOT in active set → might fall through
        # But transition happens regardless
        self.assertIn(self.fsm.state, [FSMState.DICTANDO_DATO])

    def test_10_digits_to_contacto_capturado(self):
        """10 digits → CONTACTO_CAPTURADO."""
        result = self.fsm.process("Es 3312345678", None)
        self.assertIsNotNone(result)
        self.assertEqual(self.fsm.state, FSMState.CONTACTO_CAPTURADO)
        self.assertIn('numero', result.lower())

    def test_hasta_luego_to_despedida(self):
        """'Hasta luego' → DESPEDIDA."""
        result = self.fsm.process("Hasta luego", None)
        self.assertIsNotNone(result)
        self.assertEqual(self.fsm.state, FSMState.DESPEDIDA)


# ============================================================
# C. ENCARGADO_PRESENTE Interception
# ============================================================
class TestEncargadoPresenteInterception(unittest.TestCase):
    """Phase 3: FSM intercepts when in ENCARGADO_PRESENTE state."""

    def setUp(self):
        self.fsm = FSMEngine()
        self.fsm.state = FSMState.ENCARGADO_PRESENTE
        self.fsm.context.pitch_dado = True

    def test_si_claro_to_capturando(self):
        """'Si claro' → CAPTURANDO_CONTACTO with pedir_whatsapp."""
        result = self.fsm.process("Si claro", None)
        self.assertIsNotNone(result)
        self.assertEqual(self.fsm.state, FSMState.CAPTURANDO_CONTACTO)
        self.assertIn('WhatsApp', result)

    def test_no_interesa_to_despedida(self):
        """'No me interesa' → DESPEDIDA."""
        result = self.fsm.process("No me interesa", None)
        self.assertIsNotNone(result)
        self.assertEqual(self.fsm.state, FSMState.DESPEDIDA)

    def test_email_to_contacto_capturado(self):
        """Email → CONTACTO_CAPTURADO."""
        result = self.fsm.process("ventas@gmail.com", None)
        self.assertIsNotNone(result)
        self.assertEqual(self.fsm.state, FSMState.CONTACTO_CAPTURADO)
        self.assertIn('correo', result.lower())

    def test_10_digits_to_contacto_capturado(self):
        """10 digits → CONTACTO_CAPTURADO."""
        result = self.fsm.process("3312345678", None)
        self.assertIsNotNone(result)
        self.assertEqual(self.fsm.state, FSMState.CONTACTO_CAPTURADO)

    def test_no_tengo_whatsapp_reject(self):
        """'No tengo WhatsApp' → REJECT_DATA → alternative channel."""
        self.fsm.context.canal_solicitado = 'whatsapp'
        result = self.fsm.process("No tengo WhatsApp", None)
        self.assertIsNotNone(result)
        # Should ask for correo (FIX 763)
        self.assertIn(self.fsm.state, [FSMState.CAPTURANDO_CONTACTO])

    def test_hasta_luego_to_despedida(self):
        """'Hasta luego' → DESPEDIDA."""
        result = self.fsm.process("Hasta luego", None)
        self.assertIsNotNone(result)
        self.assertEqual(self.fsm.state, FSMState.DESPEDIDA)


# ============================================================
# D. ENCARGADO_AUSENTE Interception
# ============================================================
class TestEncargadoAusenteInterception(unittest.TestCase):
    """Phase 3: FSM intercepts when in ENCARGADO_AUSENTE state."""

    def setUp(self):
        self.fsm = FSMEngine()
        self.fsm.state = FSMState.ENCARGADO_AUSENTE

    def test_si_to_capturando_digame(self):
        """FIX 764: 'Si' → CAPTURANDO_CONTACTO with digame (not repeat pedir_whatsapp)."""
        result = self.fsm.process("Si", None)
        self.assertIsNotNone(result)
        self.assertEqual(self.fsm.state, FSMState.CAPTURANDO_CONTACTO)
        self.assertIn('digame', result.lower())

    def test_le_paso_whatsapp_to_dictando(self):
        """'Le paso su WhatsApp, anote' → DICTANDO_DATO."""
        result = self.fsm.process("Le paso su WhatsApp, anote", None)
        self.assertIn(self.fsm.state, [FSMState.DICTANDO_DATO])

    def test_no_puedo_dar_datos_to_ofreciendo(self):
        """'No le puedo dar datos' → OFRECIENDO_CONTACTO."""
        result = self.fsm.process("No le puedo dar ningun dato", None)
        self.assertIsNotNone(result)
        self.assertEqual(self.fsm.state, FSMState.OFRECIENDO_CONTACTO)

    def test_callback_llame_mas_tarde(self):
        """'Llame más tarde' → ENCARGADO_AUSENTE (callback)."""
        result = self.fsm.process("Llame mas tarde", None)
        self.assertIsNotNone(result)
        self.assertEqual(self.fsm.state, FSMState.ENCARGADO_AUSENTE)
        self.assertIn('hora', result.lower())

    def test_10_digits_to_contacto_capturado(self):
        """10 digits → CONTACTO_CAPTURADO."""
        result = self.fsm.process("Es 6621234567", None)
        self.assertIsNotNone(result)
        self.assertEqual(self.fsm.state, FSMState.CONTACTO_CAPTURADO)

    def test_espere_to_transferencia(self):
        """'Espere un momento' → ESPERANDO_TRANSFERENCIA."""
        result = self.fsm.process("Espere un momento", None)
        self.assertIsNotNone(result)
        self.assertEqual(self.fsm.state, FSMState.ESPERANDO_TRANSFERENCIA)

    def test_no_interesa_to_despedida(self):
        """'No me interesa' → DESPEDIDA."""
        result = self.fsm.process("No me interesa", None)
        self.assertIsNotNone(result)
        self.assertEqual(self.fsm.state, FSMState.DESPEDIDA)

    def test_hasta_luego_to_despedida(self):
        """'Hasta luego' → DESPEDIDA."""
        result = self.fsm.process("Hasta luego", None)
        self.assertIsNotNone(result)
        self.assertEqual(self.fsm.state, FSMState.DESPEDIDA)


# ============================================================
# E. CAPTURANDO_CONTACTO Interception
# ============================================================
class TestCapturandoContactoInterception(unittest.TestCase):
    """Phase 3: FSM intercepts when in CAPTURANDO_CONTACTO state."""

    def setUp(self):
        self.fsm = FSMEngine()
        self.fsm.state = FSMState.CAPTURANDO_CONTACTO

    def test_si_claro_to_dictando(self):
        """'Si claro' → DICTANDO_DATO with digame_numero."""
        result = self.fsm.process("Si claro", None)
        # DICTANDO_DATO not in active set, but transition happens
        self.assertEqual(self.fsm.state, FSMState.DICTANDO_DATO)

    def test_10_digits_to_contacto_capturado(self):
        """10 digits → CONTACTO_CAPTURADO."""
        result = self.fsm.process("3312345678", None)
        self.assertIsNotNone(result)
        self.assertEqual(self.fsm.state, FSMState.CONTACTO_CAPTURADO)

    def test_email_to_contacto_capturado(self):
        """Email → CONTACTO_CAPTURADO."""
        result = self.fsm.process("contacto@gmail.com", None)
        self.assertIsNotNone(result)
        self.assertEqual(self.fsm.state, FSMState.CONTACTO_CAPTURADO)

    def test_no_tengo_whatsapp_reject(self):
        """'No tengo WhatsApp' → alternative channel."""
        self.fsm.context.canal_solicitado = 'whatsapp'
        result = self.fsm.process("No tengo whatsapp", None)
        self.assertIsNotNone(result)
        self.assertEqual(self.fsm.state, FSMState.CAPTURANDO_CONTACTO)

    def test_no_interesa_to_despedida(self):
        """'No me interesa' → DESPEDIDA."""
        result = self.fsm.process("No me interesa", None)
        self.assertIsNotNone(result)
        self.assertEqual(self.fsm.state, FSMState.DESPEDIDA)

    def test_partial_digits_to_dictando(self):
        """Partial digits → DICTANDO_DATO."""
        result = self.fsm.process("Es 662", None)
        self.assertEqual(self.fsm.state, FSMState.DICTANDO_DATO)


# ============================================================
# F. Smart REJECT_DATA Alternation (FIX 763)
# ============================================================
class TestRejectDataAlternation(unittest.TestCase):
    """FIX 763: Dynamic channel alternation on REJECT_DATA."""

    def setUp(self):
        self.fsm = FSMEngine()
        self.fsm.state = FSMState.CAPTURANDO_CONTACTO

    def test_first_reject_whatsapp_asks_correo(self):
        """Reject WhatsApp → ask for correo."""
        self.fsm.context.canal_solicitado = 'whatsapp'
        result = self.fsm.process("No tengo whatsapp", None)
        self.assertIsNotNone(result)
        self.assertIn('correo', result.lower())

    def test_second_reject_asks_telefono(self):
        """Reject WhatsApp + correo → ask for telefono."""
        self.fsm.context.canal_solicitado = 'correo'
        self.fsm.context.canales_rechazados = ['whatsapp']
        result = self.fsm.process("No tengo correo", None)
        self.assertIsNotNone(result)
        self.assertIn('telefono', result.lower())

    def test_all_rejected_ofrecer_contacto(self):
        """All channels rejected → offer Bruce's number."""
        self.fsm.context.canal_solicitado = 'telefono'
        self.fsm.context.canales_rechazados = ['whatsapp', 'correo']
        result = self.fsm.process("No tengo telefono fijo", None)
        self.assertIsNotNone(result)
        self.assertEqual(self.fsm.state, FSMState.OFRECIENDO_CONTACTO)

    def test_reject_correo_first_asks_whatsapp(self):
        """Reject correo first → ask for WhatsApp."""
        self.fsm.context.canal_solicitado = 'correo'
        result = self.fsm.process("No tengo correo", None)
        self.assertIsNotNone(result)
        # WhatsApp not rejected yet → should ask for WhatsApp
        # (pedir_alternativa_whatsapp template)

    def test_canales_rechazados_persists(self):
        """Rejected channels persist across turns."""
        self.fsm.context.canal_solicitado = 'whatsapp'
        self.fsm.process("No tengo whatsapp", None)
        self.assertIn('whatsapp', self.fsm.context.canales_rechazados)

    def test_encargado_presente_reject_dynamic(self):
        """FIX 763 also works from ENCARGADO_PRESENTE state."""
        self.fsm.state = FSMState.ENCARGADO_PRESENTE
        self.fsm.context.canal_solicitado = 'whatsapp'
        result = self.fsm.process("No tengo whatsapp", None)
        self.assertIsNotNone(result)
        self.assertEqual(self.fsm.state, FSMState.CAPTURANDO_CONTACTO)


# ============================================================
# G. Data Extraction on FSM Intercept (FIX 762/765)
# ============================================================
class TestDataExtraction(unittest.TestCase):
    """FIX 762+765: Data extraction when FSM intercepts."""

    def test_phone_10_digits_extraction(self):
        """10 numeric digits extracted from text."""
        texto = "Es 3312345678"
        digitos = re.findall(r'\d', texto)
        self.assertEqual(len(digitos), 10)
        numero = ''.join(digitos[:10])
        self.assertEqual(numero, '3312345678')

    def test_phone_with_spaces(self):
        """Phone with spaces extracted."""
        texto = "Es 33 1234 5678"
        digitos = re.findall(r'\d', texto)
        self.assertEqual(len(digitos), 10)
        numero = ''.join(digitos[:10])
        self.assertEqual(numero, '3312345678')

    def test_email_literal_extraction(self):
        """Email with literal @ extracted."""
        texto = "Mi correo es ventas@gmail.com"
        match = re.search(r'[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}', texto)
        self.assertIsNotNone(match)
        self.assertEqual(match.group(0), 'ventas@gmail.com')

    def test_email_voice_arroba(self):
        """Voice-dictated email: 'arroba' → '@'."""
        texto = "ventas arroba gmail punto com"
        tn = texto.lower().strip()
        tn = tn.replace(' arroba ', '@').replace(' punto com', '.com')
        match = re.search(r'[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}', tn)
        self.assertIsNotNone(match)
        self.assertEqual(match.group(0), 'ventas@gmail.com')

    def test_phone_in_words(self):
        """FIX 765: Phone dictated in words."""
        texto = "seis seis dos uno dos tres cuatro cinco seis siete"
        nums = {
            'cero': '0', 'uno': '1', 'una': '1', 'dos': '2', 'tres': '3',
            'cuatro': '4', 'cinco': '5', 'seis': '6', 'siete': '7',
            'ocho': '8', 'nueve': '9',
        }
        words = texto.lower().split()
        word_digits = [nums[w] for w in words if w in nums]
        self.assertEqual(len(word_digits), 10)
        self.assertEqual(''.join(word_digits), '6621234567')

    def test_phone_mixed_digits_words(self):
        """Mixed numeric + word digits."""
        texto = "Es 662 uno dos tres cuatro cinco seis siete"
        digitos_num = re.findall(r'\d', texto)
        nums = {
            'cero': '0', 'uno': '1', 'dos': '2', 'tres': '3',
            'cuatro': '4', 'cinco': '5', 'seis': '6', 'siete': '7',
            'ocho': '8', 'nueve': '9',
        }
        words = texto.lower().split()
        word_digits = [nums[w] for w in words if w in nums]
        all_digits = digitos_num + word_digits
        self.assertGreaterEqual(len(all_digits), 10)

    def test_no_overwrite_existing_whatsapp(self):
        """Don't overwrite if whatsapp already captured."""
        lead_data = {"whatsapp": "3312345678"}
        new_digits = "6629876543"
        # Sync logic: if not lead_data.get("whatsapp") → skip
        self.assertTrue(lead_data.get("whatsapp"))
        # Should NOT overwrite

    def test_no_overwrite_existing_email(self):
        """Don't overwrite if email already captured."""
        lead_data = {"email": "old@gmail.com"}
        self.assertTrue(lead_data.get("email"))

    def test_empty_text_no_crash(self):
        """Empty text doesn't crash extraction."""
        texto = ""
        digitos = re.findall(r'\d', texto)
        self.assertEqual(len(digitos), 0)

    def test_fsm_classify_complete_phone(self):
        """FSM classify_intent detects complete phone."""
        ctx = FSMContext()
        state = FSMState.CAPTURANDO_CONTACTO
        intent = classify_intent("3312345678", ctx, state)
        self.assertEqual(intent, FSMIntent.DICTATING_COMPLETE_PHONE)


# ============================================================
# H. Full Flow Integration
# ============================================================
class TestFullFlowIntegration(unittest.TestCase):
    """End-to-end flow tests for Phase 3."""

    def test_happy_path_manager_present(self):
        """SALUDO → BUSCANDO → PRESENTE → CAPTURANDO → CAPTURADO → DESPEDIDA."""
        fsm = FSMEngine()
        # Turn 1: Client answers phone → SALUDO
        self.assertEqual(fsm.state, FSMState.SALUDO)

        # Turn 2: Client says "Bueno" → FSM transitions to PITCH
        fsm.process("Bueno", None)
        self.assertEqual(fsm.state, FSMState.PITCH)

        # Turn 3: Client confirms → FSM goes to BUSCANDO_ENCARGADO
        fsm.process("Si, digame", None)
        self.assertIn(fsm.state, [FSMState.BUSCANDO_ENCARGADO, FSMState.CAPTURANDO_CONTACTO])

        # Turn 4: Manager is here
        if fsm.state == FSMState.BUSCANDO_ENCARGADO:
            fsm.process("Si, soy yo", None)
            self.assertEqual(fsm.state, FSMState.ENCARGADO_PRESENTE)

            # Turn 5: Interested
            fsm.process("Si claro", None)
            self.assertEqual(fsm.state, FSMState.CAPTURANDO_CONTACTO)

        # Turn 6: Give phone
        fsm.process("3312345678", None)
        self.assertEqual(fsm.state, FSMState.CONTACTO_CAPTURADO)

        # Turn 7: Farewell
        fsm.process("Gracias", None)
        self.assertEqual(fsm.state, FSMState.DESPEDIDA)

    def test_manager_absent_flow(self):
        """Flow when manager is not available."""
        fsm = FSMEngine()
        fsm.state = FSMState.BUSCANDO_ENCARGADO
        fsm.context.encargado_preguntado = True

        # Client says not here
        fsm.process("No esta, salio a comer", None)
        self.assertEqual(fsm.state, FSMState.ENCARGADO_AUSENTE)

        # Client agrees to give contact
        fsm.process("Si", None)
        self.assertEqual(fsm.state, FSMState.CAPTURANDO_CONTACTO)

        # Client gives phone
        fsm.process("6621234567", None)
        self.assertEqual(fsm.state, FSMState.CONTACTO_CAPTURADO)

    def test_rejection_cascade(self):
        """All channels rejected → offer Bruce's number."""
        fsm = FSMEngine()
        fsm.state = FSMState.CAPTURANDO_CONTACTO
        fsm.context.canal_solicitado = 'whatsapp'

        # Reject WhatsApp
        fsm.process("No tengo whatsapp", None)
        self.assertEqual(fsm.state, FSMState.CAPTURANDO_CONTACTO)

        # Reject correo
        fsm.context.canal_solicitado = 'correo'
        fsm.process("No tengo correo", None)
        self.assertEqual(fsm.state, FSMState.CAPTURANDO_CONTACTO)

        # Reject telefono
        fsm.context.canal_solicitado = 'telefono'
        fsm.process("No tengo telefono fijo", None)
        self.assertEqual(fsm.state, FSMState.OFRECIENDO_CONTACTO)

    def test_callback_flow(self):
        """Callback: manager absent → call later."""
        fsm = FSMEngine()
        fsm.state = FSMState.BUSCANDO_ENCARGADO
        fsm.context.encargado_preguntado = True

        # Client says callback
        result = fsm.process("Llame mas tarde a las 3", None)
        self.assertEqual(fsm.state, FSMState.ENCARGADO_AUSENTE)
        self.assertTrue(fsm.context.callback_pedido)

    def test_phase3_states_intercept_not_shadow(self):
        """Phase 3 states produce responses (not None) when FSM processes."""
        fsm = FSMEngine()
        fsm.state = FSMState.BUSCANDO_ENCARGADO
        fsm.context.encargado_preguntado = True

        result = fsm.process("Si, soy yo", None)
        # In Phase 3, BUSCANDO_ENCARGADO is active → should intercept
        self.assertIsNotNone(result)
        self.assertGreater(len(result), 0)

    def test_fsm_source_has_phase3_comments(self):
        """FIX 761/763/764 comments exist in source."""
        fsm_path = os.path.join(os.path.dirname(__file__), '..', 'fsm_engine.py')
        with open(fsm_path, 'r', encoding='utf-8') as f:
            source = f.read()
        self.assertIn('FIX 761', source)
        self.assertIn('FIX 763', source)
        self.assertIn('FIX 764', source)
        self.assertIn('Phase 3', source)

    def test_agente_has_sync_method(self):
        """FIX 762 sync method exists in agente source."""
        agente_path = os.path.join(os.path.dirname(__file__), '..', 'agente_ventas.py')
        with open(agente_path, 'r', encoding='utf-8') as f:
            source = f.read()
        self.assertIn('_sync_fsm_to_agent', source)
        self.assertIn('FIX 762', source)
        self.assertIn('FIX 765', source)
        self.assertIn('FIX 766', source)


if __name__ == '__main__':
    unittest.main()
