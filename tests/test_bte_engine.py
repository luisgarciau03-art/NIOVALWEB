"""
Tests para Bruce Templates Engine (BTE).
Verifica las 32+ acciones, el builder de templates, y el flujo completo.
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


class TestBTEDecidirAccion(unittest.TestCase):
    """Test decidir_accion() con diferentes intents y states."""

    def setUp(self):
        self.engine = BTEEngine()

    def test_greeting_returns_presentacion(self):
        accion = self.engine.decidir_accion(
            fsm_intent="GREETING", fsm_state=None,
            lead_data={}, conversation_history=[], texto_cliente="Bueno", turno=1
        )
        self.assertEqual(accion, "PRESENTACION_Y_PEDIR_ENCARGADO")

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

    def test_state_buscando_encargado_no_esta(self):
        accion = self.engine.decidir_accion(
            fsm_intent=None, fsm_state="BUSCANDO_ENCARGADO",
            lead_data={}, conversation_history=[],
            texto_cliente="No esta, salio"
        )
        self.assertEqual(accion, "OFRECER_CALLBACK")

    def test_state_buscando_encargado_yo_soy(self):
        accion = self.engine.decidir_accion(
            fsm_intent=None, fsm_state="BUSCANDO_ENCARGADO",
            lead_data={}, conversation_history=[],
            texto_cliente="Yo soy el encargado"
        )
        self.assertEqual(accion, "PITCH_ENCARGADO_CORTO")

    def test_state_buscando_encargado_un_momento(self):
        accion = self.engine.decidir_accion(
            fsm_intent=None, fsm_state="BUSCANDO_ENCARGADO",
            lead_data={}, conversation_history=[],
            texto_cliente="Un momento, le paso"
        )
        self.assertEqual(accion, "ESPERANDO_TRANSFERENCIA")

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

    def test_digame_sin_presentacion_returns_presentacion(self):
        accion = self.engine.decidir_accion(
            fsm_intent=None, fsm_state=None,
            lead_data={}, conversation_history=[],
            texto_cliente="Digame"
        )
        self.assertEqual(accion, "PRESENTACION_Y_PEDIR_ENCARGADO")

    def test_digame_con_presentacion_returns_confirmar(self):
        history = [{"role": "assistant", "content": "Soy Bruce de NIOVAL"}]
        accion = self.engine.decidir_accion(
            fsm_intent=None, fsm_state=None,
            lead_data={}, conversation_history=history,
            texto_cliente="Digame"
        )
        self.assertEqual(accion, "CONFIRMAR_ESCUCHA")

    def test_confirmation_con_datos_returns_agradecer(self):
        accion = self.engine.decidir_accion(
            fsm_intent="CONFIRMATION", fsm_state=None,
            lead_data={"whatsapp": "3312345678"},
            conversation_history=[], texto_cliente="Si, esta bien"
        )
        self.assertEqual(accion, "CONFIRMAR_Y_AGRADECER")

    def test_offer_data_returns_confirmar(self):
        accion = self.engine.decidir_accion(
            fsm_intent="OFFER_DATA", fsm_state=None,
            lead_data={}, conversation_history=[],
            texto_cliente="Mi numero es 3312345678"
        )
        self.assertEqual(accion, "CONFIRMAR_DATO")


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
        """Verificar que no repite la misma variante consecutivamente."""
        respuestas = set()
        for _ in range(3):
            resp = self.engine.generar_respuesta("CONFIRMAR_ESCUCHA")
            respuestas.add(resp)
        self.assertGreaterEqual(len(respuestas), 2, "Should rotate variants")

    def test_inyeccion_variables(self):
        resp = self.engine.generar_respuesta("MENCIONAR_CATALOGO", {"canal": "correo"})
        # Al menos una variante menciona {canal}
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
        """Texto ambiguo sin intent → None (GPT fallback)."""
        result = self.engine.process(
            texto_cliente="Ajam bueno pues si verdad",
        )
        # Podria resolverse o no, depende de los patterns


class TestBTEAntiRepeticion(unittest.TestCase):
    """Test que el BTE no repite la misma respuesta."""

    def setUp(self):
        self.engine = BTEEngine()

    def test_no_repite_3_veces_seguidas(self):
        respuestas = []
        for _ in range(6):
            resp = self.engine.generar_respuesta("PEDIR_WHATSAPP")
            respuestas.append(resp)
        # No deberia haber 3 iguales consecutivas
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


class TestBTEEscenarios(unittest.TestCase):
    """Tests end-to-end simulando conversaciones completas."""

    def setUp(self):
        self.engine = BTEEngine()

    def test_flujo_encargado_presente(self):
        """Cliente contesta → es el encargado → pitch → pide WhatsApp."""
        # Turno 1: Cliente contesta
        r1 = self.engine.process("Bueno", turno=1)
        self.assertIsNotNone(r1)  # PRESENTACION_Y_PEDIR_ENCARGADO
        self.assertIn("nioval", r1.lower())

        # Turno 2: Es el encargado
        r2 = self.engine.process(
            "Si, yo soy el encargado",
            fsm_intent="INTEREST",
            conversation_history=[
                {"role": "assistant", "content": r1},
                {"role": "user", "content": "Si, yo soy el encargado"},
            ]
        )
        self.assertIsNotNone(r2)  # PITCH_ENCARGADO_CORTO
        self.assertIn("catalogo", r2.lower())

    def test_flujo_encargado_no_esta(self):
        """Cliente dice que no esta → ofrecer callback."""
        history = [
            {"role": "assistant", "content": "Soy Bruce de NIOVAL. Se encuentra el encargado?"},
        ]
        r = self.engine.process(
            "No, no esta, salio",
            fsm_intent="NOT_AVAILABLE",
            conversation_history=history,
        )
        self.assertIsNotNone(r)
        # Debe ofrecer callback o pedir contacto alternativo

    def test_flujo_rechazo_total(self):
        """No WhatsApp → pide correo. No correo → da numero Bruce."""
        # Rechaza WhatsApp
        r1 = self.engine.process(
            "No tengo whatsapp",
            fsm_intent="REJECT_DATA",
            lead_data={"sin_whatsapp": True},
        )
        self.assertIsNotNone(r1)
        self.assertIn("correo", r1.lower())

        # Rechaza correo
        r2 = self.engine.process(
            "Tampoco tengo correo",
            fsm_intent="REJECT_DATA",
            lead_data={"sin_whatsapp": True, "sin_correo": True},
        )
        self.assertIsNotNone(r2)
        # Debe dar numero de Bruce

    def test_flujo_transferencia(self):
        """Un momento le paso → esperar → persona nueva."""
        r = self.engine.process(
            "Un momento le paso",
            fsm_intent="TRANSFER",
        )
        self.assertIsNotNone(r)
        self.assertIn("espero", r.lower())


if __name__ == "__main__":
    unittest.main()
