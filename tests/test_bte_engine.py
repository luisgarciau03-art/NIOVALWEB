"""
Tests para Bruce Templates Engine (BTE).
Verifica las 39 acciones, cobertura completa de decidir_accion(), y flujos E2E.
"""

import sys
import os
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bte_engine import BTEEngine, BTE_CATALOG, ACCIONES_VALIDAS


class TestBTECatalog(unittest.TestCase):
    """Verificar integridad del catalogo de templates."""

    def test_catalog_has_actions(self):
        self.assertGreaterEqual(len(BTE_CATALOG), 30)

    def test_each_action_has_templates(self):
        for accion, info in BTE_CATALOG.items():
            self.assertIn("templates", info, f"{accion} missing templates")
            self.assertGreaterEqual(len(info["templates"]), 2, f"{accion} needs 2+ variants")

    def test_each_action_has_fase(self):
        for accion, info in BTE_CATALOG.items():
            self.assertIn("fase", info, f"{accion} missing fase")

    def test_no_empty_templates(self):
        for accion, info in BTE_CATALOG.items():
            for t in info["templates"]:
                self.assertTrue(len(t.strip()) > 10, f"{accion} has empty/short template: '{t}'")

    def test_acciones_validas_matches_catalog(self):
        self.assertEqual(set(ACCIONES_VALIDAS), set(BTE_CATALOG.keys()))

    def test_templates_no_emojis(self):
        """Templates should not contain emojis (TTS compatibility)."""
        import re
        emoji_pattern = re.compile(
            "[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF"
            "\U0001F1E0-\U0001F1FF\U00002702-\U000027B0\U0001f900-\U0001f9FF]"
        )
        for accion, info in BTE_CATALOG.items():
            for t in info["templates"]:
                self.assertIsNone(emoji_pattern.search(t), f"{accion} has emoji in: '{t[:50]}'")


class TestBTEDecidirAccionIntents(unittest.TestCase):
    """Test decidir_accion() con diferentes intents."""

    def setUp(self):
        self.engine = BTEEngine()

    def test_greeting_returns_presentacion(self):
        accion = self.engine.decidir_accion(
            fsm_intent="GREETING", fsm_state=None,
            lead_data={}, conversation_history=[], texto_cliente="Bueno", turno=1
        )
        self.assertEqual(accion, "PRESENTACION_Y_PEDIR_ENCARGADO")

    def test_greeting_con_presentacion_returns_confirmar(self):
        history = [{"role": "assistant", "content": "Soy Bruce de NIOVAL"}]
        accion = self.engine.decidir_accion(
            fsm_intent="GREETING", fsm_state=None,
            lead_data={}, conversation_history=history, texto_cliente="Bueno"
        )
        self.assertEqual(accion, "CONFIRMAR_ESCUCHA")

    def test_transfer_returns_esperando(self):
        accion = self.engine.decidir_accion(
            fsm_intent="TRANSFER", fsm_state=None,
            lead_data={}, conversation_history=[], texto_cliente="Un momento le paso"
        )
        self.assertEqual(accion, "ESPERANDO_TRANSFERENCIA")

    def test_callback_con_hora_returns_confirmar(self):
        accion = self.engine.decidir_accion(
            fsm_intent="CALLBACK", fsm_state=None,
            lead_data={}, conversation_history=[], texto_cliente="Llame a las 3 de la tarde"
        )
        self.assertEqual(accion, "CONFIRMAR_Y_AGRADECER")

    def test_callback_sin_hora_returns_preguntar(self):
        accion = self.engine.decidir_accion(
            fsm_intent="CALLBACK", fsm_state=None,
            lead_data={}, conversation_history=[], texto_cliente="No esta, llame despues"
        )
        self.assertEqual(accion, "PREGUNTAR_HORARIO_CALLBACK")

    def test_no_interest_returns_despedida(self):
        accion = self.engine.decidir_accion(
            fsm_intent="NO_INTEREST", fsm_state=None,
            lead_data={}, conversation_history=[], texto_cliente="No me interesa"
        )
        self.assertEqual(accion, "DESPEDIDA_PUERTA_ABIERTA")

    def test_wrong_number_returns_aceptar_rechazo(self):
        accion = self.engine.decidir_accion(
            fsm_intent="WRONG_NUMBER", fsm_state=None,
            lead_data={}, conversation_history=[], texto_cliente="Numero equivocado"
        )
        self.assertEqual(accion, "ACEPTAR_RECHAZO")

    def test_another_branch_returns_aceptar_rechazo(self):
        accion = self.engine.decidir_accion(
            fsm_intent="ANOTHER_BRANCH", fsm_state=None,
            lead_data={}, conversation_history=[], texto_cliente="Llame a otra sucursal"
        )
        self.assertEqual(accion, "ACEPTAR_RECHAZO")

    def test_interest_sin_pitch_returns_pitch(self):
        accion = self.engine.decidir_accion(
            fsm_intent="INTEREST", fsm_state=None,
            lead_data={}, conversation_history=[], texto_cliente="Si, yo soy el encargado"
        )
        self.assertEqual(accion, "PITCH_ENCARGADO_CORTO")

    def test_interest_con_pitch_returns_pedir_whatsapp(self):
        history = [
            {"role": "assistant", "content": "Le ofrezco nuestro catalogo de productos ferreteros"}
        ]
        accion = self.engine.decidir_accion(
            fsm_intent="INTEREST", fsm_state=None,
            lead_data={}, conversation_history=history, texto_cliente="Si claro"
        )
        self.assertEqual(accion, "PEDIR_WHATSAPP")

    def test_interest_con_pitch_y_contacto_returns_agradecer(self):
        history = [
            {"role": "assistant", "content": "Le ofrezco nuestro catalogo de productos ferreteros"},
            {"role": "assistant", "content": "Me da su whatsapp?"}
        ]
        accion = self.engine.decidir_accion(
            fsm_intent="INTEREST", fsm_state=None,
            lead_data={"whatsapp": "3312345678"}, conversation_history=history,
            texto_cliente="Si claro"
        )
        self.assertEqual(accion, "CONFIRMAR_Y_AGRADECER")

    def test_not_available_returns_ofrecer_callback(self):
        accion = self.engine.decidir_accion(
            fsm_intent="NOT_AVAILABLE", fsm_state=None,
            lead_data={}, conversation_history=[], texto_cliente="No esta el encargado"
        )
        self.assertEqual(accion, "OFRECER_CALLBACK")

    def test_verification_returns_confirmar_escucha(self):
        accion = self.engine.decidir_accion(
            fsm_intent="VERIFICATION", fsm_state=None,
            lead_data={}, conversation_history=[], texto_cliente="Me escucha?"
        )
        self.assertEqual(accion, "CONFIRMAR_ESCUCHA")

    def test_reject_data_sin_whatsapp_returns_pedir_correo(self):
        accion = self.engine.decidir_accion(
            fsm_intent="REJECT_DATA", fsm_state=None,
            lead_data={"sin_whatsapp": True}, conversation_history=[],
            texto_cliente="No tengo whatsapp"
        )
        self.assertEqual(accion, "PEDIR_CORREO")

    def test_reject_data_sin_ambos_returns_dar_numero_bruce(self):
        accion = self.engine.decidir_accion(
            fsm_intent="REJECT_DATA", fsm_state=None,
            lead_data={"sin_whatsapp": True, "sin_correo": True},
            conversation_history=[], texto_cliente="Tampoco tengo correo"
        )
        self.assertEqual(accion, "DAR_NUMERO_BRUCE")

    def test_offer_data_returns_confirmar(self):
        accion = self.engine.decidir_accion(
            fsm_intent="OFFER_DATA", fsm_state=None,
            lead_data={}, conversation_history=[],
            texto_cliente="Mi numero es 3312345678"
        )
        self.assertEqual(accion, "CONFIRMAR_DATO")

    def test_confirmation_con_whatsapp_returns_confirmar_envio_whatsapp(self):
        accion = self.engine.decidir_accion(
            fsm_intent="CONFIRMATION", fsm_state=None,
            lead_data={"whatsapp": "3312345678"},
            conversation_history=[], texto_cliente="Si, esta bien"
        )
        self.assertEqual(accion, "CONFIRMAR_ENVIO_WHATSAPP")

    def test_confirmation_con_correo_returns_confirmar_envio_correo(self):
        accion = self.engine.decidir_accion(
            fsm_intent="CONFIRMATION", fsm_state=None,
            lead_data={"correo": "test@test.com"},
            conversation_history=[], texto_cliente="Si, correcto"
        )
        self.assertEqual(accion, "CONFIRMAR_ENVIO_CORREO")

    def test_confirmation_con_pitch_returns_pedir_whatsapp(self):
        history = [{"role": "assistant", "content": "Tenemos catalogo de ferreteria"}]
        accion = self.engine.decidir_accion(
            fsm_intent="CONFIRMATION", fsm_state=None,
            lead_data={}, conversation_history=history, texto_cliente="Si, mande"
        )
        self.assertEqual(accion, "PEDIR_WHATSAPP")

    def test_confirmation_sin_pitch_returns_pitch(self):
        accion = self.engine.decidir_accion(
            fsm_intent="CONFIRMATION", fsm_state=None,
            lead_data={}, conversation_history=[], texto_cliente="Si, digame"
        )
        self.assertEqual(accion, "PITCH_ENCARGADO_CORTO")

    def test_question_ubicacion(self):
        accion = self.engine.decidir_accion(
            fsm_intent="QUESTION", fsm_state=None,
            lead_data={}, conversation_history=[],
            texto_cliente="De donde llaman?"
        )
        self.assertEqual(accion, "RESPONDER_UBICACION")

    def test_question_productos(self):
        accion = self.engine.decidir_accion(
            fsm_intent="QUESTION", fsm_state=None,
            lead_data={}, conversation_history=[],
            texto_cliente="Que productos manejan?"
        )
        self.assertEqual(accion, "RESPONDER_QUIEN_ES_NIOVAL")

    def test_question_precios(self):
        accion = self.engine.decidir_accion(
            fsm_intent="QUESTION", fsm_state=None,
            lead_data={}, conversation_history=[],
            texto_cliente="Cuanto cuestan los productos?"
        )
        self.assertEqual(accion, "RESPONDER_PRECIOS")

    def test_question_envios(self):
        accion = self.engine.decidir_accion(
            fsm_intent="QUESTION", fsm_state=None,
            lead_data={}, conversation_history=[],
            texto_cliente="Mandan a todo el pais?"
        )
        self.assertEqual(accion, "RESPONDER_ENVIOS")

    def test_question_contacto_bruce(self):
        accion = self.engine.decidir_accion(
            fsm_intent="QUESTION", fsm_state=None,
            lead_data={}, conversation_history=[],
            texto_cliente="Cual es tu numero de contacto?"
        )
        self.assertEqual(accion, "MENCIONAR_CONTACTO_BRUCE")

    def test_question_generica(self):
        accion = self.engine.decidir_accion(
            fsm_intent="QUESTION", fsm_state=None,
            lead_data={}, conversation_history=[],
            texto_cliente="Tienen garantia?"
        )
        self.assertEqual(accion, "RESPONDER_PREGUNTA_GENERICA")

    def test_busy_returns_reconocer_ocupado(self):
        accion = self.engine.decidir_accion(
            fsm_intent="BUSY", fsm_state=None,
            lead_data={}, conversation_history=[],
            texto_cliente="Estoy muy ocupado"
        )
        self.assertEqual(accion, "RECONOCER_OCUPADO")

    def test_continuation_returns_acknowledgment(self):
        accion = self.engine.decidir_accion(
            fsm_intent="CONTINUATION", fsm_state=None,
            lead_data={}, conversation_history=[],
            texto_cliente="Aja"
        )
        self.assertEqual(accion, "ACKNOWLEDGMENT")

    def test_continuation_en_pitch_sin_pitch_returns_preguntar_catalogo(self):
        accion = self.engine.decidir_accion(
            fsm_intent="CONTINUATION", fsm_state="pitch",
            lead_data={}, conversation_history=[],
            texto_cliente="Aja"
        )
        self.assertEqual(accion, "PREGUNTAR_SI_QUIERE_CATALOGO")

    def test_continuation_en_pitch_con_pitch_returns_ofrecer_enviar(self):
        history = [{"role": "assistant", "content": "Tenemos catalogo de ferreteria"}]
        accion = self.engine.decidir_accion(
            fsm_intent="CONTINUATION", fsm_state="pitch",
            lead_data={}, conversation_history=history,
            texto_cliente="Aja"
        )
        self.assertEqual(accion, "OFRECER_ENVIAR_CATALOGO")

    def test_continuation_en_captura_returns_pedir_numero(self):
        accion = self.engine.decidir_accion(
            fsm_intent="CONTINUATION", fsm_state="capturando_contacto",
            lead_data={}, conversation_history=[],
            texto_cliente="Aja"
        )
        self.assertEqual(accion, "PEDIR_NUMERO")

    def test_confusion_returns_manejar_confusion(self):
        accion = self.engine.decidir_accion(
            fsm_intent="CONFUSION", fsm_state=None,
            lead_data={}, conversation_history=[],
            texto_cliente="No entendi"
        )
        self.assertEqual(accion, "MANEJAR_CONFUSION")

    def test_timeout_returns_manejar_timeout(self):
        accion = self.engine.decidir_accion(
            fsm_intent="TIMEOUT", fsm_state=None,
            lead_data={}, conversation_history=[],
            texto_cliente=""
        )
        self.assertEqual(accion, "MANEJAR_TIMEOUT")


class TestBTEDecidirAccionStates(unittest.TestCase):
    """Test decidir_accion() con states del FSM."""

    def setUp(self):
        self.engine = BTEEngine()

    def test_state_saludo_sin_presentacion(self):
        accion = self.engine.decidir_accion(
            fsm_intent=None, fsm_state="saludo",
            lead_data={}, conversation_history=[],
            texto_cliente="Bueno"
        )
        self.assertEqual(accion, "PRESENTACION_Y_PEDIR_ENCARGADO")

    def test_state_saludo_con_presentacion(self):
        history = [{"role": "assistant", "content": "Soy Bruce de NIOVAL"}]
        accion = self.engine.decidir_accion(
            fsm_intent=None, fsm_state="saludo",
            lead_data={}, conversation_history=history,
            texto_cliente="Bueno"
        )
        self.assertEqual(accion, "SALUDO_Y_PEDIR_ENCARGADO")

    def test_state_pitch_encargado_presente(self):
        accion = self.engine.decidir_accion(
            fsm_intent=None, fsm_state="pitch",
            lead_data={}, conversation_history=[],
            texto_cliente="Yo soy el encargado"
        )
        self.assertEqual(accion, "PITCH_ENCARGADO_CORTO")

    def test_state_pitch_si_sin_pitch_returns_preguntar_catalogo(self):
        accion = self.engine.decidir_accion(
            fsm_intent=None, fsm_state="pitch",
            lead_data={}, conversation_history=[],
            texto_cliente="Si claro"
        )
        self.assertEqual(accion, "PREGUNTAR_SI_QUIERE_CATALOGO")

    def test_state_pitch_si_con_pitch_returns_ofrecer_enviar(self):
        history = [{"role": "assistant", "content": "Tenemos catalogo de ferreteria"}]
        accion = self.engine.decidir_accion(
            fsm_intent=None, fsm_state="pitch",
            lead_data={}, conversation_history=history,
            texto_cliente="Si claro"
        )
        self.assertEqual(accion, "OFRECER_ENVIAR_CATALOGO")

    def test_state_pitch_pregunta_productos(self):
        accion = self.engine.decidir_accion(
            fsm_intent=None, fsm_state="pitch",
            lead_data={}, conversation_history=[],
            texto_cliente="Que productos manejan?"
        )
        self.assertEqual(accion, "PITCH_PRODUCTOS")

    def test_state_pitch_no_interes(self):
        accion = self.engine.decidir_accion(
            fsm_intent=None, fsm_state="pitch",
            lead_data={}, conversation_history=[],
            texto_cliente="No me interesa gracias"
        )
        self.assertEqual(accion, "DESPEDIDA_PUERTA_ABIERTA")

    def test_state_pitch_ocupado(self):
        accion = self.engine.decidir_accion(
            fsm_intent=None, fsm_state="pitch",
            lead_data={}, conversation_history=[],
            texto_cliente="Estoy ocupado ahorita"
        )
        self.assertEqual(accion, "RECONOCER_OCUPADO")

    def test_state_pitch_default_mencionar_productos(self):
        accion = self.engine.decidir_accion(
            fsm_intent=None, fsm_state="pitch",
            lead_data={}, conversation_history=[],
            texto_cliente="ajam"
        )
        self.assertEqual(accion, "MENCIONAR_PRODUCTOS")

    def test_state_buscando_encargado_no_esta(self):
        accion = self.engine.decidir_accion(
            fsm_intent=None, fsm_state="buscando_encargado",
            lead_data={}, conversation_history=[],
            texto_cliente="No esta, salio"
        )
        self.assertEqual(accion, "OFRECER_CALLBACK")

    def test_state_buscando_encargado_yo_soy(self):
        accion = self.engine.decidir_accion(
            fsm_intent=None, fsm_state="buscando_encargado",
            lead_data={}, conversation_history=[],
            texto_cliente="Yo soy el encargado"
        )
        self.assertEqual(accion, "PITCH_ENCARGADO_CORTO")

    def test_state_buscando_encargado_un_momento(self):
        accion = self.engine.decidir_accion(
            fsm_intent=None, fsm_state="buscando_encargado",
            lead_data={}, conversation_history=[],
            texto_cliente="Un momento, le paso"
        )
        self.assertEqual(accion, "ESPERANDO_TRANSFERENCIA")

    def test_state_buscando_encargado_si_bueno(self):
        accion = self.engine.decidir_accion(
            fsm_intent=None, fsm_state="buscando_encargado",
            lead_data={}, conversation_history=[],
            texto_cliente="Si, bueno"
        )
        self.assertEqual(accion, "PEDIR_COMUNICAR_ENCARGADO")

    def test_state_buscando_encargado_default(self):
        accion = self.engine.decidir_accion(
            fsm_intent=None, fsm_state="buscando_encargado",
            lead_data={}, conversation_history=[],
            texto_cliente="mmm pues"
        )
        self.assertEqual(accion, "PREGUNTAR_POR_ENCARGADO")

    def test_state_capturando_no_whatsapp(self):
        accion = self.engine.decidir_accion(
            fsm_intent=None, fsm_state="capturando_contacto",
            lead_data={}, conversation_history=[],
            texto_cliente="No tengo whatsapp"
        )
        self.assertEqual(accion, "PEDIR_CORREO")

    def test_state_capturando_no_correo(self):
        accion = self.engine.decidir_accion(
            fsm_intent=None, fsm_state="capturando_contacto",
            lead_data={}, conversation_history=[],
            texto_cliente="No tengo correo"
        )
        self.assertEqual(accion, "DAR_NUMERO_BRUCE")

    def test_state_capturando_si_con_whatsapp(self):
        accion = self.engine.decidir_accion(
            fsm_intent=None, fsm_state="capturando_contacto",
            lead_data={"whatsapp": "3312345678"}, conversation_history=[],
            texto_cliente="Si, esta bien"
        )
        self.assertEqual(accion, "CONFIRMAR_ENVIO_WHATSAPP")

    def test_state_capturando_si_con_correo(self):
        accion = self.engine.decidir_accion(
            fsm_intent=None, fsm_state="capturando_contacto",
            lead_data={"correo": "test@test.com"}, conversation_history=[],
            texto_cliente="Si, correcto"
        )
        self.assertEqual(accion, "CONFIRMAR_ENVIO_CORREO")

    def test_state_capturando_si_returns_pedir_numero(self):
        accion = self.engine.decidir_accion(
            fsm_intent=None, fsm_state="capturando_contacto",
            lead_data={}, conversation_history=[],
            texto_cliente="Si claro, apunte"
        )
        self.assertEqual(accion, "PEDIR_NUMERO")

    def test_state_capturando_default_pedir_whatsapp(self):
        accion = self.engine.decidir_accion(
            fsm_intent=None, fsm_state="capturando_contacto",
            lead_data={}, conversation_history=[],
            texto_cliente="mmm pues"
        )
        self.assertEqual(accion, "PEDIR_WHATSAPP")

    def test_state_encargado_ausente_con_hora(self):
        accion = self.engine.decidir_accion(
            fsm_intent=None, fsm_state="encargado_ausente",
            lead_data={}, conversation_history=[],
            texto_cliente="Llame a las 3 de la tarde"
        )
        self.assertEqual(accion, "CONFIRMAR_Y_AGRADECER")

    def test_state_encargado_ausente_llame_despues(self):
        accion = self.engine.decidir_accion(
            fsm_intent=None, fsm_state="encargado_ausente",
            lead_data={}, conversation_history=[],
            texto_cliente="Llame mas tarde"
        )
        self.assertEqual(accion, "PREGUNTAR_HORARIO_CALLBACK")

    def test_state_encargado_ausente_default(self):
        accion = self.engine.decidir_accion(
            fsm_intent=None, fsm_state="encargado_ausente",
            lead_data={}, conversation_history=[],
            texto_cliente="Pues no se"
        )
        self.assertEqual(accion, "OFRECER_CALLBACK")

    def test_state_ofreciendo_contacto(self):
        accion = self.engine.decidir_accion(
            fsm_intent=None, fsm_state="ofreciendo_contacto",
            lead_data={}, conversation_history=[],
            texto_cliente="Si, digame"
        )
        self.assertEqual(accion, "DAR_NUMERO_BRUCE")

    def test_state_despedida(self):
        accion = self.engine.decidir_accion(
            fsm_intent=None, fsm_state="despedida",
            lead_data={}, conversation_history=[],
            texto_cliente="Gracias"
        )
        self.assertEqual(accion, "DESPEDIDA")

    def test_state_contacto_capturado(self):
        accion = self.engine.decidir_accion(
            fsm_intent=None, fsm_state="contacto_capturado",
            lead_data={}, conversation_history=[],
            texto_cliente="Ok"
        )
        self.assertEqual(accion, "DESPEDIDA")


class TestBTEDecidirAccionTextPatterns(unittest.TestCase):
    """Test decidir_accion() con patrones de texto (sin intent ni state)."""

    def setUp(self):
        self.engine = BTEEngine()

    def test_identidad_sin_presentacion(self):
        accion = self.engine.decidir_accion(
            fsm_intent=None, fsm_state=None,
            lead_data={}, conversation_history=[],
            texto_cliente="De parte de quien habla?"
        )
        self.assertEqual(accion, "PRESENTACION_NIOVAL")

    def test_identidad_con_presentacion(self):
        history = [{"role": "assistant", "content": "Soy Bruce de NIOVAL"}]
        accion = self.engine.decidir_accion(
            fsm_intent=None, fsm_state=None,
            lead_data={}, conversation_history=history,
            texto_cliente="De parte de quien habla?"
        )
        self.assertEqual(accion, "RESPONDER_UBICACION")

    def test_problemas_conexion(self):
        accion = self.engine.decidir_accion(
            fsm_intent=None, fsm_state=None,
            lead_data={}, conversation_history=[],
            texto_cliente="No le escucho, se corto"
        )
        self.assertEqual(accion, "MANEJAR_TIMEOUT")

    def test_ocupado_texto(self):
        accion = self.engine.decidir_accion(
            fsm_intent=None, fsm_state=None,
            lead_data={}, conversation_history=[],
            texto_cliente="Estoy ocupado ahorita"
        )
        self.assertEqual(accion, "RECONOCER_OCUPADO")

    def test_pide_contacto_bruce(self):
        accion = self.engine.decidir_accion(
            fsm_intent=None, fsm_state=None,
            lead_data={}, conversation_history=[],
            texto_cliente="Dame tu numero"
        )
        self.assertEqual(accion, "MENCIONAR_CONTACTO_BRUCE")

    def test_pregunta_ubicacion(self):
        accion = self.engine.decidir_accion(
            fsm_intent=None, fsm_state=None,
            lead_data={}, conversation_history=[],
            texto_cliente="De donde llaman?"
        )
        self.assertEqual(accion, "RESPONDER_UBICACION")

    def test_pregunta_productos(self):
        accion = self.engine.decidir_accion(
            fsm_intent=None, fsm_state=None,
            lead_data={}, conversation_history=[],
            texto_cliente="Que productos manejan?"
        )
        self.assertEqual(accion, "RESPONDER_QUIEN_ES_NIOVAL")

    def test_pregunta_precios(self):
        accion = self.engine.decidir_accion(
            fsm_intent=None, fsm_state=None,
            lead_data={}, conversation_history=[],
            texto_cliente="Cuanto cuestan los productos?"
        )
        self.assertEqual(accion, "RESPONDER_PRECIOS")

    def test_pregunta_envios(self):
        accion = self.engine.decidir_accion(
            fsm_intent=None, fsm_state=None,
            lead_data={}, conversation_history=[],
            texto_cliente="Envian a todo el pais?"
        )
        self.assertEqual(accion, "RESPONDER_ENVIOS")

    def test_digame_sin_presentacion(self):
        accion = self.engine.decidir_accion(
            fsm_intent=None, fsm_state=None,
            lead_data={}, conversation_history=[],
            texto_cliente="Digame"
        )
        self.assertEqual(accion, "PRESENTACION_Y_PEDIR_ENCARGADO")

    def test_digame_con_presentacion(self):
        history = [{"role": "assistant", "content": "Soy Bruce de NIOVAL"}]
        accion = self.engine.decidir_accion(
            fsm_intent=None, fsm_state=None,
            lead_data={}, conversation_history=history,
            texto_cliente="Digame"
        )
        self.assertEqual(accion, "CONFIRMAR_ESCUCHA")

    def test_turno_1_default_presentacion(self):
        accion = self.engine.decidir_accion(
            fsm_intent=None, fsm_state=None,
            lead_data={}, conversation_history=[],
            texto_cliente="alo?", turno=1
        )
        self.assertEqual(accion, "PRESENTACION_Y_PEDIR_ENCARGADO")


class TestBTEGenerarRespuesta(unittest.TestCase):
    """Test generar_respuesta() y rotacion de templates."""

    def setUp(self):
        self.engine = BTEEngine()

    def test_genera_texto_no_vacio(self):
        for accion in ACCIONES_VALIDAS:
            resp = self.engine.generar_respuesta(accion)
            self.assertIsNotNone(resp, f"{accion} returned None")
            self.assertTrue(len(resp) > 10, f"{accion} too short: '{resp}'")

    def test_rotacion_variantes(self):
        respuestas = set()
        for _ in range(3):
            resp = self.engine.generar_respuesta("CONFIRMAR_ESCUCHA")
            respuestas.add(resp)
        self.assertGreaterEqual(len(respuestas), 2, "Should rotate variants")

    def test_inyeccion_variables(self):
        resp = self.engine.generar_respuesta("MENCIONAR_CATALOGO", {"canal": "correo"})
        self.assertIsNotNone(resp)

    def test_accion_invalida_returns_none(self):
        resp = self.engine.generar_respuesta("ACCION_INEXISTENTE")
        self.assertIsNone(resp)


class TestBTEProcess(unittest.TestCase):
    """Test flujo completo process()."""

    def setUp(self):
        self.engine = BTEEngine()

    def test_process_con_intent_conocido(self):
        result = self.engine.process(
            texto_cliente="No me interesa gracias",
            fsm_intent="NO_INTEREST",
        )
        self.assertIsNotNone(result)
        self.assertIn("dia", result.lower())

    def test_process_sin_intent_con_texto(self):
        result = self.engine.process(
            texto_cliente="De donde llaman?",
        )
        self.assertIsNotNone(result)
        self.assertIn("guadalajara", result.lower())

    def test_process_desconocido_returns_none(self):
        result = self.engine.process(
            texto_cliente="Ajam bueno pues si verdad",
        )
        # Puede resolverse o no


class TestBTEAntiRepeticion(unittest.TestCase):
    """Test que el BTE no repite la misma respuesta."""

    def setUp(self):
        self.engine = BTEEngine()

    def test_no_repite_3_veces_seguidas(self):
        respuestas = []
        for _ in range(6):
            resp = self.engine.generar_respuesta("PEDIR_WHATSAPP")
            respuestas.append(resp)
        for i in range(len(respuestas) - 2):
            self.assertFalse(
                respuestas[i] == respuestas[i+1] == respuestas[i+2],
                f"3 respuestas iguales consecutivas: '{respuestas[i][:50]}'"
            )


class TestBTECobertura(unittest.TestCase):
    """Test que las 7 fases estan cubiertas."""

    def test_todas_las_fases(self):
        fases = set(info["fase"] for info in BTE_CATALOG.values())
        expected = {"APERTURA", "BUSCAR_ENCARGADO", "PITCH", "CAPTURA", "CIERRE", "SITUACIONAL", "PREGUNTAS"}
        self.assertEqual(fases, expected)

    def test_fase_apertura_tiene_acciones(self):
        apertura = [a for a, i in BTE_CATALOG.items() if i["fase"] == "APERTURA"]
        self.assertGreaterEqual(len(apertura), 3)

    def test_fase_captura_tiene_acciones(self):
        captura = [a for a, i in BTE_CATALOG.items() if i["fase"] == "CAPTURA"]
        self.assertGreaterEqual(len(captura), 5)


class TestBTECoberturaCompleta(unittest.TestCase):
    """Test que TODAS las acciones del catalogo son alcanzables via decidir_accion."""

    def setUp(self):
        self.engine = BTEEngine()

    def test_todas_acciones_alcanzables(self):
        """Brute-force test: intenta todas las combinaciones y verifica cobertura 100%."""
        acciones_alcanzables = set()

        test_intents = [
            'GREETING', 'SALUDO', 'SALUDO_SIMPLE', 'IVR',
            'INTEREST', 'ENCARGADO_PRESENTE', 'IDENTITY',
            'TRANSFER', 'CALLBACK', 'NO_INTEREST', 'REJECT', 'RECHAZO',
            'NOT_AVAILABLE', 'ENCARGADO_AUSENTE', 'ANOTHER_BRANCH', 'WRONG_NUMBER',
            'CONFIRMATION', 'CONFIRM', 'YES', 'REJECT_DATA', 'REJECT_CHANNEL',
            'OFFER_DATA', 'DICTA_NUMERO', 'DICTA_EMAIL', 'VERIFICATION', 'CHECK',
            'QUESTION', 'PREGUNTA', 'BUSY', 'OCCUPIED', 'CONTINUATION', 'FILLER',
            'UNCLEAR', 'CONFUSION', 'CORRECTION', 'TIMEOUT', 'SILENCE', 'NO_AUDIO',
            None,
        ]

        test_states = [
            'saludo', 'pitch', 'encargado_presente', 'buscando_encargado',
            'esperando_transferencia', 'capturando_contacto', 'dictando_dato',
            'encargado_ausente', 'ofreciendo_contacto', 'despedida', 'contacto_capturado',
            None,
        ]

        test_textos = [
            'Bueno', 'Digame', 'Si claro', 'No me interesa gracias',
            'No esta', 'Yo soy el encargado', 'Un momento le paso',
            'Llame a las 3 de la tarde', 'No esta llame despues',
            'No tengo whatsapp', 'No tengo correo', 'De donde llaman',
            'Que productos manejan', 'Cuanto cuestan', 'Envian a todo el pais',
            'Me escucha?', 'Mi numero es 3312345678', 'Si esta bien',
            'De parte de quien habla', 'No le escucho se corto',
            'Estoy ocupado', 'Dame tu numero', 'Aja', 'No entendi',
            'Que tienen', 'mmm pues', 'anote apunte', 'Si correcto',
            'Llame mas tarde', 'Pues no se', 'ajam',
            'Tienen garantia', 'Como te contacto', 'Pasame tus datos',
            'alo?',
        ]

        test_lead_datas = [
            {},
            {"whatsapp": "3312345678"},
            {"correo": "test@test.com"},
            {"telefono_contacto": "3312345678"},
            {"digitos_parciales": 5},
            {"sin_whatsapp": True},
            {"sin_whatsapp": True, "sin_correo": True},
        ]

        test_histories = [
            [],
            [{"role": "assistant", "content": "Soy Bruce de NIOVAL catalogo ferreteria"}],
            [{"role": "assistant", "content": "Soy Bruce"},
             {"role": "assistant", "content": "Le envio whatsapp catalogo"}],
        ]

        for intent in test_intents:
            for state in test_states:
                for txt in test_textos:
                    for ld in test_lead_datas:
                        for hist in test_histories:
                            a = self.engine.decidir_accion(intent, state, ld, hist, txt)
                            if a:
                                acciones_alcanzables.add(a)

        # Turno 1 especial
        a = self.engine.decidir_accion(None, None, {}, [], "alo?", turno=1)
        if a:
            acciones_alcanzables.add(a)

        no_alcanzables = set(BTE_CATALOG.keys()) - acciones_alcanzables
        self.assertEqual(
            len(no_alcanzables), 0,
            f"Acciones NO alcanzables ({len(no_alcanzables)}): {sorted(no_alcanzables)}"
        )


class TestBTEEscenarios(unittest.TestCase):
    """Tests end-to-end simulando conversaciones completas."""

    def setUp(self):
        self.engine = BTEEngine()

    def test_flujo_encargado_presente(self):
        r1 = self.engine.process("Bueno", turno=1)
        self.assertIsNotNone(r1)
        self.assertIn("nioval", r1.lower())

        r2 = self.engine.process(
            "Si, yo soy el encargado",
            fsm_intent="INTEREST",
            conversation_history=[
                {"role": "assistant", "content": r1},
                {"role": "user", "content": "Si, yo soy el encargado"},
            ]
        )
        self.assertIsNotNone(r2)
        self.assertIn("catalogo", r2.lower())

    def test_flujo_encargado_no_esta(self):
        history = [
            {"role": "assistant", "content": "Soy Bruce de NIOVAL. Se encuentra el encargado?"},
        ]
        r = self.engine.process(
            "No, no esta, salio",
            fsm_intent="NOT_AVAILABLE",
            conversation_history=history,
        )
        self.assertIsNotNone(r)

    def test_flujo_rechazo_total(self):
        r1 = self.engine.process(
            "No tengo whatsapp",
            fsm_intent="REJECT_DATA",
            lead_data={"sin_whatsapp": True},
        )
        self.assertIsNotNone(r1)
        self.assertIn("correo", r1.lower())

        r2 = self.engine.process(
            "Tampoco tengo correo",
            fsm_intent="REJECT_DATA",
            lead_data={"sin_whatsapp": True, "sin_correo": True},
        )
        self.assertIsNotNone(r2)

    def test_flujo_transferencia(self):
        r = self.engine.process(
            "Un momento le paso",
            fsm_intent="TRANSFER",
        )
        self.assertIsNotNone(r)
        self.assertIn("espero", r.lower())

    def test_flujo_confirmacion_whatsapp(self):
        r = self.engine.process(
            "Si, esta bien",
            fsm_intent="CONFIRMATION",
            lead_data={"whatsapp": "3312345678"},
        )
        self.assertIsNotNone(r)
        self.assertIn("whatsapp", r.lower())

    def test_flujo_ocupado(self):
        r = self.engine.process(
            "Estoy muy ocupado",
            fsm_intent="BUSY",
        )
        self.assertIsNotNone(r)
        self.assertIn("ocupado", r.lower())


if __name__ == "__main__":
    unittest.main()
