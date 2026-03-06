"""
Tests para FIX 894: Guardrail pre-send + FSM expansion (WHAT_OFFER).

FIX 894A: Guardrail pre-send - 4 checks regex/logica antes de enviar respuesta
FIX 894B: FSM intent WHAT_OFFER con templates dedicados
FIX 894C: Templates pitch_completo_894 y pitch_y_encargado_894
"""
import sys
import os
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fsm_engine import classify_intent, FSMEngine, FSMIntent, FSMState, FSMContext, ActionType
from response_templates import TEMPLATES


# ============================================================
# TEST GROUP 1: FSM Intent Detection - WHAT_OFFER
# ============================================================
class TestFix894WhatOffer(unittest.TestCase):
    """FIX 894: 'que deseaba', 'que ofrece' -> WHAT_OFFER (not generic QUESTION)."""

    def _classify(self, texto, state=FSMState.PITCH):
        ctx = FSMContext()
        return classify_intent(texto, ctx, state)

    def test_que_deseaba(self):
        self.assertEqual(self._classify("que deseaba"), FSMIntent.WHAT_OFFER)

    def test_que_desea(self):
        self.assertEqual(self._classify("que desea"), FSMIntent.WHAT_OFFER)

    def test_que_ofrece(self):
        self.assertEqual(self._classify("que ofrece"), FSMIntent.WHAT_OFFER)

    def test_que_ofrecen(self):
        self.assertEqual(self._classify("que ofrecen"), FSMIntent.WHAT_OFFER)

    def test_que_vende(self):
        self.assertEqual(self._classify("que vende"), FSMIntent.WHAT_OFFER)

    def test_que_venden(self):
        self.assertEqual(self._classify("que venden"), FSMIntent.WHAT_OFFER)

    def test_en_que_se_le_ofrece(self):
        self.assertEqual(self._classify("en que se le ofrece"), FSMIntent.WHAT_OFFER)

    def test_en_que_le_puedo(self):
        self.assertEqual(self._classify("en que le puedo"), FSMIntent.WHAT_OFFER)

    def test_que_me_ofrece(self):
        self.assertEqual(self._classify("que me ofrece"), FSMIntent.WHAT_OFFER)

    def test_que_nos_ofrece(self):
        self.assertEqual(self._classify("que nos ofrece"), FSMIntent.WHAT_OFFER)

    def test_que_producto(self):
        self.assertEqual(self._classify("que producto"), FSMIntent.WHAT_OFFER)

    def test_que_tienen(self):
        self.assertEqual(self._classify("que tienen"), FSMIntent.WHAT_OFFER)

    def test_de_que_se_trata(self):
        self.assertEqual(self._classify("de que se trata"), FSMIntent.WHAT_OFFER)

    def test_para_que_es(self):
        self.assertEqual(self._classify("para que es"), FSMIntent.WHAT_OFFER)

    def test_a_que_se_dedican(self):
        self.assertEqual(self._classify("a que se dedican"), FSMIntent.WHAT_OFFER)


# ============================================================
# TEST GROUP 2: Identity questions still work (IDENTITY intent)
# ============================================================
class TestFix894IdentityStillWorks(unittest.TestCase):
    """FIX 894: Identity questions still classified as IDENTITY (handled by existing FSM)."""

    def _classify(self, texto, state=FSMState.PITCH):
        ctx = FSMContext()
        return classify_intent(texto, ctx, state)

    def test_de_donde_llama(self):
        self.assertEqual(self._classify("de donde llama"), FSMIntent.IDENTITY)

    def test_quien_habla(self):
        self.assertEqual(self._classify("quien habla"), FSMIntent.IDENTITY)

    def test_de_que_parte(self):
        self.assertEqual(self._classify("de que parte"), FSMIntent.IDENTITY)

    def test_de_parte_de_quien(self):
        self.assertEqual(self._classify("de parte de quien"), FSMIntent.IDENTITY)

    def test_con_quien_hablo(self):
        self.assertEqual(self._classify("con quien hablo"), FSMIntent.IDENTITY)

    def test_de_que_empresa(self):
        self.assertEqual(self._classify("de que empresa"), FSMIntent.IDENTITY)


# ============================================================
# TEST GROUP 3: FSM Transitions - WHAT_OFFER returns template text
# ============================================================
class TestFix894WhatOfferTransitions(unittest.TestCase):
    """FIX 894: WHAT_OFFER in different states returns pitch template text."""

    def _process(self, state, texto="que deseaba"):
        engine = FSMEngine()
        engine.context.state = state
        engine.state = state
        return engine.process(texto)

    def test_saludo_what_offer_returns_pitch(self):
        resp = self._process(FSMState.SALUDO)
        self.assertIsNotNone(resp)
        self.assertIn("NIOVAL", resp)

    def test_pitch_what_offer_returns_encargado(self):
        resp = self._process(FSMState.PITCH)
        self.assertIsNotNone(resp)
        self.assertIn("encargado", resp.lower())

    def test_buscando_encargado_what_offer(self):
        resp = self._process(FSMState.BUSCANDO_ENCARGADO)
        self.assertIsNotNone(resp)
        self.assertIn("encargado", resp.lower())

    def test_encargado_presente_what_offer(self):
        resp = self._process(FSMState.ENCARGADO_PRESENTE)
        self.assertIsNotNone(resp)
        self.assertIn("NIOVAL", resp)

    def test_encargado_ausente_what_offer(self):
        resp = self._process(FSMState.ENCARGADO_AUSENTE)
        self.assertIsNotNone(resp)
        self.assertIn("NIOVAL", resp)

    def test_esperando_transferencia_what_offer(self):
        resp = self._process(FSMState.ESPERANDO_TRANSFERENCIA)
        self.assertIsNotNone(resp)
        self.assertIn("NIOVAL", resp)

    def test_capturando_contacto_what_offer(self):
        resp = self._process(FSMState.CAPTURANDO_CONTACTO)
        self.assertIsNotNone(resp)


# ============================================================
# TEST GROUP 4: Templates exist and have proper content
# ============================================================
class TestFix894Templates(unittest.TestCase):
    """FIX 894: New templates exist and have content."""

    def test_pitch_completo_894_exists(self):
        self.assertIn("pitch_completo_894", TEMPLATES)
        self.assertTrue(len(TEMPLATES["pitch_completo_894"]) > 0)

    def test_pitch_y_encargado_894_exists(self):
        self.assertIn("pitch_y_encargado_894", TEMPLATES)
        self.assertTrue(len(TEMPLATES["pitch_y_encargado_894"]) > 0)

    def test_pitch_completo_894_mentions_nioval(self):
        text = TEMPLATES["pitch_completo_894"][0].lower()
        self.assertIn("nioval", text)

    def test_pitch_y_encargado_894_asks_encargado(self):
        text = TEMPLATES["pitch_y_encargado_894"][0].lower()
        self.assertIn("encargado", text)

    def test_pitch_completo_894_asks_for_action(self):
        text = TEMPLATES["pitch_completo_894"][0].lower()
        self.assertTrue("lista de precios" in text or "catalogo" in text)


# ============================================================
# TEST GROUP 5: Guardrail pre-send
# ============================================================
class TestFix894Guardrail(unittest.TestCase):
    """FIX 894: _guardrail_pre_send checks."""

    def _make_agente(self, lead_data=None, conversation_history=None):
        class MockAgente:
            def __init__(self):
                self.lead_data = lead_data or {}
                self.conversation_history = conversation_history or []
        agente = MockAgente()
        from agente_ventas import AgenteVentas
        agente._guardrail_pre_send = AgenteVentas._guardrail_pre_send.__get__(agente, MockAgente)
        return agente

    # --- CHECK 1: No pedir dato ya capturado ---
    def test_check1_whatsapp_ya_capturado(self):
        agente = self._make_agente(lead_data={"whatsapp": "3312345678"})
        resp = agente._guardrail_pre_send(
            "Me podria proporcionar un numero de WhatsApp?", "si claro"
        )
        self.assertIn("Ya tengo su WhatsApp", resp)

    def test_check1_email_ya_capturado(self):
        agente = self._make_agente(lead_data={"email": "test@mail.com"})
        resp = agente._guardrail_pre_send(
            "Me podria dar su correo electronico para enviarle info?", "ok"
        )
        self.assertIn("Ya tengo su correo", resp)

    def test_check1_sin_dato_no_interviene(self):
        agente = self._make_agente(lead_data={})
        original = "Me podria proporcionar un numero de WhatsApp?"
        resp = agente._guardrail_pre_send(original, "si claro")
        self.assertEqual(resp, original)

    def test_check1_telefono_solo_no_interviene(self):
        agente = self._make_agente(lead_data={"telefono_contacto": "3312345678"})
        original = "Me podria proporcionar un numero de WhatsApp?"
        resp = agente._guardrail_pre_send(original, "ok")
        self.assertEqual(resp, original)

    # --- CHECK 2: No preguntar por encargado cuando cliente enganchado ---
    def test_check2_cliente_enganchado_2_turnos(self):
        history = [
            {"role": "user", "content": "Si claro, digame de que se trata"},
            {"role": "assistant", "content": "Somos distribuidores de NIOVAL..."},
            {"role": "user", "content": "Ah ok, y que productos manejan exactamente"},
            {"role": "assistant", "content": "Manejamos cintas, herramientas..."},
        ]
        agente = self._make_agente(conversation_history=history)
        resp = agente._guardrail_pre_send(
            "Se encontrara el encargado o encargada de compras?", "interesante"
        )
        self.assertNotIn("encargado", resp.lower())
        self.assertIn("productos ferreteros", resp.lower())

    def test_check2_solo_1_turno_no_interviene(self):
        history = [
            {"role": "user", "content": "Bueno, buen dia"},
            {"role": "assistant", "content": "Hola buen dia..."},
        ]
        agente = self._make_agente(conversation_history=history)
        original = "Se encontrara el encargado de compras?"
        resp = agente._guardrail_pre_send(original, "bueno")
        self.assertEqual(resp, original)

    def test_check2_verificaciones_no_cuentan(self):
        history = [
            {"role": "user", "content": "Bueno, bueno?"},
            {"role": "assistant", "content": "Hola..."},
            {"role": "user", "content": "Si bueno, mande"},
            {"role": "assistant", "content": "Le comento..."},
        ]
        agente = self._make_agente(conversation_history=history)
        original = "Se encontrara el encargado de compras?"
        resp = agente._guardrail_pre_send(original, "mande?")
        self.assertEqual(resp, original)

    # --- CHECK 3: No dar "aqui estoy" a pregunta directa ---
    def test_check3_aqui_estoy_sin_pregunta_no_interviene(self):
        agente = self._make_agente()
        original = "Si, aqui estoy. Digame."
        resp = agente._guardrail_pre_send(original, "bueno si")
        self.assertEqual(resp, original)

    # --- CHECK 4: Truncar respuestas largas ante inputs cortos ---
    def test_check4_trunca_respuesta_larga(self):
        agente = self._make_agente()
        long_resp = "Le comento, somos distribuidores de NIOVAL con sede en Guadalajara. " * 4
        resp = agente._guardrail_pre_send(long_resp, "si")
        self.assertLess(len(resp), len(long_resp))

    def test_check4_no_trunca_input_largo(self):
        agente = self._make_agente()
        long_resp = "Le comento, somos distribuidores de NIOVAL con sede en Guadalajara. " * 4
        resp = agente._guardrail_pre_send(
            long_resp, "si claro digame de que se trata su llamada por favor"
        )
        self.assertEqual(resp, long_resp)

    def test_check4_no_trunca_respuesta_corta(self):
        agente = self._make_agente()
        short_resp = "Claro, somos NIOVAL."
        resp = agente._guardrail_pre_send(short_resp, "ok")
        self.assertEqual(resp, short_resp)


# ============================================================
# TEST GROUP 6: No collisions with existing intents
# ============================================================
class TestFix894NoCollisions(unittest.TestCase):
    """FIX 894: WHAT_OFFER no colisiona con intents existentes."""

    def _classify(self, texto, state=FSMState.SALUDO):
        ctx = FSMContext()
        return classify_intent(texto, ctx, state)

    def test_que_tal_buen_dia_not_what_offer(self):
        intent = self._classify("que tal buen dia")
        self.assertNotEqual(intent, FSMIntent.WHAT_OFFER)

    def test_no_me_interesa_not_what_offer(self):
        intent = self._classify("no me interesa")
        self.assertNotEqual(intent, FSMIntent.WHAT_OFFER)

    def test_bueno_not_what_offer(self):
        intent = self._classify("bueno")
        self.assertNotEqual(intent, FSMIntent.WHAT_OFFER)

    def test_si_yo_soy_not_what_offer(self):
        intent = self._classify("si yo soy")
        self.assertNotEqual(intent, FSMIntent.WHAT_OFFER)

    def test_que_precio_tiene_la_cinta(self):
        """Specific product question - could be WHAT_OFFER or QUESTION, but should not crash."""
        intent = self._classify("que precio tiene la cinta")
        self.assertIsNotNone(intent)


# ============================================================
# TEST GROUP 7: FIX 895 - pitch_completo_894 escalation
# ============================================================
class TestFix895PitchEscalation(unittest.TestCase):
    """FIX 895: BRUCE2643/2631 - pitch_completo_894 repeat → escalate."""

    def test_first_what_offer_gives_pitch(self):
        """First WHAT_OFFER gives full pitch."""
        engine = FSMEngine()
        engine.state = FSMState.SALUDO
        engine.context.state = FSMState.SALUDO
        resp = engine.process("que deseaba")
        self.assertIn("NIOVAL", resp)
        self.assertTrue(engine.context.pitch_dado)

    def test_second_what_offer_pivots_to_contact(self):
        """Second WHAT_OFFER (pitch already dado) → pedir contacto."""
        engine = FSMEngine()
        engine.state = FSMState.ENCARGADO_AUSENTE
        engine.context.state = FSMState.ENCARGADO_AUSENTE
        engine.context.pitch_dado = True
        resp = engine.process("que deseaba")
        self.assertNotIn("quince mil", resp.lower())
        self.assertTrue("whatsapp" in resp.lower() or "correo" in resp.lower())

    def test_third_what_offer_offers_bruce_number(self):
        """Third WHAT_OFFER → ofrecer contacto Bruce."""
        engine = FSMEngine()
        engine.state = FSMState.ENCARGADO_AUSENTE
        engine.context.state = FSMState.ENCARGADO_AUSENTE
        engine.context.pitch_dado = True
        engine.context._pitch_894_count = 1
        resp = engine.process("que deseaba")
        self.assertIn("numero", resp.lower())

    def test_fourth_what_offer_farewell(self):
        """Fourth WHAT_OFFER → despedida cortés (all escalation candidates exhausted)."""
        engine = FSMEngine()
        engine.state = FSMState.ENCARGADO_AUSENTE
        engine.context.state = FSMState.ENCARGADO_AUSENTE
        engine.context.pitch_dado = True
        engine.context._pitch_894_count = 2
        # FIX 925: All escalation candidates already used
        engine.context.templates_usados.update([
            "pedir_whatsapp_o_correo", "pedir_whatsapp_o_correo_breve",
            "ofrecer_contacto_bruce",
        ])
        resp = engine.process("que deseaba")
        self.assertIn("gracias", resp.lower())

    def test_pitch_894_sets_pitch_dado(self):
        """pitch_completo_894 must set pitch_dado=True."""
        engine = FSMEngine()
        engine.state = FSMState.SALUDO
        engine.context.state = FSMState.SALUDO
        self.assertFalse(engine.context.pitch_dado)
        engine.process("que deseaba")
        self.assertTrue(engine.context.pitch_dado)

    def test_pitch_y_encargado_894_sets_encargado_preguntado(self):
        """pitch_y_encargado_894 must set encargado_preguntado=True."""
        engine = FSMEngine()
        engine.state = FSMState.PITCH
        engine.context.state = FSMState.PITCH
        self.assertFalse(engine.context.encargado_preguntado)
        engine.process("que deseaba")
        self.assertTrue(engine.context.encargado_preguntado)


if __name__ == '__main__':
    unittest.main()
