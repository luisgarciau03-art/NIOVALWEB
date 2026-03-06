# -*- coding: utf-8 -*-
"""
Tests para FSM Phase 4: Activación de 5 estados restantes
SALUDO, PITCH, DICTANDO_DATO, OFRECIENDO_CONTACTO, ESPERANDO_TRANSFERENCIA
"""
import unittest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Force active mode for testing
os.environ["FSM_ENABLED"] = "active"
os.environ["FSM_ACTIVE_STATES"] = (
    "despedida,contacto_capturado,buscando_encargado,encargado_presente,"
    "encargado_ausente,capturando_contacto,dictando_dato,ofreciendo_contacto,"
    "esperando_transferencia,saludo,pitch"
)

from fsm_engine import (
    FSMEngine, FSMState, FSMIntent, FSM_ACTIVE_STATES_SET,
    classify_intent, ActionType
)


class TestPhase4ActiveStates(unittest.TestCase):
    """Verificar que los 11 estados están activos."""

    def test_11_estados_activos(self):
        """Phase 4: 11 de 12 estados activos (CONVERSACION_LIBRE excluido)."""
        expected = {
            FSMState.DESPEDIDA, FSMState.CONTACTO_CAPTURADO,
            FSMState.BUSCANDO_ENCARGADO, FSMState.ENCARGADO_PRESENTE,
            FSMState.ENCARGADO_AUSENTE, FSMState.CAPTURANDO_CONTACTO,
            FSMState.DICTANDO_DATO, FSMState.OFRECIENDO_CONTACTO,
            FSMState.ESPERANDO_TRANSFERENCIA, FSMState.SALUDO, FSMState.PITCH,
        }
        self.assertEqual(FSM_ACTIVE_STATES_SET, expected)

    def test_conversacion_libre_no_activa(self):
        """CONVERSACION_LIBRE debe seguir en shadow."""
        self.assertNotIn(FSMState.CONVERSACION_LIBRE, FSM_ACTIVE_STATES_SET)

    def test_deploy_version_phase4(self):
        """FIX 818: Deploy version es dinamico via set_deploy_version."""
        from bug_detector import set_deploy_version, _DEPLOY_VERSION
        self.assertIsInstance(_DEPLOY_VERSION, str)
        self.assertTrue(len(_DEPLOY_VERSION) > 0)


# =============================================================================
# SALUDO: Primera respuesta del cliente
# =============================================================================

class TestSaludoState(unittest.TestCase):
    """SALUDO: Manejar primera respuesta del cliente."""

    def setUp(self):
        self.fsm = FSMEngine()
        self.assertEqual(self.fsm.state, FSMState.SALUDO)

    def test_saludo_confirmation_to_pitch(self):
        """Client 'Sí, dígame' → PITCH."""
        result = self.fsm.process("Sí, dígame")
        self.assertIsNotNone(result)
        self.assertEqual(self.fsm.state, FSMState.PITCH)

    def test_saludo_no_interest_to_despedida(self):
        """Client 'No me interesa' → DESPEDIDA."""
        result = self.fsm.process("No, no me interesa, gracias")
        self.assertIsNotNone(result)
        self.assertEqual(self.fsm.state, FSMState.DESPEDIDA)

    def test_saludo_identity_to_pitch(self):
        """Client '¿Quién habla?' → PITCH (identificación)."""
        result = self.fsm.process("¿Quién habla?")
        self.assertIsNotNone(result)
        self.assertEqual(self.fsm.state, FSMState.PITCH)

    def test_saludo_manager_absent(self):
        """Client 'No está' → ENCARGADO_AUSENTE."""
        result = self.fsm.process("No, no está, salió")
        self.assertIsNotNone(result)
        self.assertEqual(self.fsm.state, FSMState.ENCARGADO_AUSENTE)

    def test_saludo_verification_to_pitch(self):
        """Client '¿Bueno?' → PITCH."""
        result = self.fsm.process("¿Bueno?")
        self.assertIsNotNone(result)
        self.assertEqual(self.fsm.state, FSMState.PITCH)


# =============================================================================
# PITCH: Respuestas al pitch de productos
# =============================================================================

class TestPitchState(unittest.TestCase):
    """PITCH: Manejar respuestas al pitch."""

    def setUp(self):
        self.fsm = FSMEngine()
        self.fsm.state = FSMState.PITCH
        self.fsm.context.pitch_dado = True

    def test_pitch_interest_to_buscando(self):
        """Client 'Sí, me interesa' → BUSCANDO_ENCARGADO."""
        result = self.fsm.process("Sí, me interesa")
        self.assertIsNotNone(result)
        self.assertEqual(self.fsm.state, FSMState.BUSCANDO_ENCARGADO)

    def test_pitch_no_interest_to_despedida(self):
        """Client 'No, gracias' → DESPEDIDA."""
        result = self.fsm.process("No gracias, no me interesa")
        self.assertIsNotNone(result)
        self.assertEqual(self.fsm.state, FSMState.DESPEDIDA)

    def test_pitch_manager_present(self):
        """Client 'Soy yo, el encargado' → ENCARGADO_PRESENTE."""
        result = self.fsm.process("Soy yo, dígame")
        self.assertIsNotNone(result)
        self.assertEqual(self.fsm.state, FSMState.ENCARGADO_PRESENTE)

    def test_pitch_transfer(self):
        """Client 'Espere un momento' → ESPERANDO_TRANSFERENCIA."""
        result = self.fsm.process("Espere un momento, se lo paso")
        self.assertIsNotNone(result)
        self.assertIn("espero", result.lower())
        self.assertEqual(self.fsm.state, FSMState.ESPERANDO_TRANSFERENCIA)

    def test_pitch_farewell_to_despedida(self):
        """Client 'Hasta luego' → DESPEDIDA."""
        result = self.fsm.process("Hasta luego, gracias")
        self.assertIsNotNone(result)
        self.assertEqual(self.fsm.state, FSMState.DESPEDIDA)

    def test_pitch_unknown_advances_via_fix791(self):
        """Client text ambiguo → FIX 791 template advances state (no longer stays PITCH)."""
        result = self.fsm.process("Ajá, está bien")
        # FIX 791: PITCH+UNKNOWN → stateful template → advances to BUSCANDO or CAPTURANDO
        self.assertIn(self.fsm.state, [
            FSMState.BUSCANDO_ENCARGADO,
            FSMState.CAPTURANDO_CONTACTO,
        ])


# =============================================================================
# DICTANDO_DATO: Cliente dictando teléfono/email
# =============================================================================

class TestDictandoDatoState(unittest.TestCase):
    """DICTANDO_DATO: Acknowledgments durante dictado."""

    def setUp(self):
        self.fsm = FSMEngine()
        self.fsm.state = FSMState.DICTANDO_DATO

    def test_partial_dictation_stays_ack(self):
        """Dictado parcial '331-876' → stays + ack."""
        result = self.fsm.process("331-876")
        self.assertIsNotNone(result)
        self.assertEqual(self.fsm.state, FSMState.DICTANDO_DATO)

    def test_complete_phone_to_capturado(self):
        """Teléfono completo 10 dígitos → CONTACTO_CAPTURADO."""
        result = self.fsm.process("3313456789")
        self.assertIsNotNone(result)
        self.assertEqual(self.fsm.state, FSMState.CONTACTO_CAPTURADO)

    def test_complete_email_to_capturado(self):
        """Email completo → CONTACTO_CAPTURADO."""
        result = self.fsm.process("juan@gmail.com")
        self.assertIsNotNone(result)
        self.assertEqual(self.fsm.state, FSMState.CONTACTO_CAPTURADO)

    def test_continuation_comma_stays(self):
        """Texto con coma → stays + ack."""
        result = self.fsm.process("tres tres uno,")
        self.assertIsNotNone(result)
        self.assertEqual(self.fsm.state, FSMState.DICTANDO_DATO)

    def test_farewell_to_despedida(self):
        """Client 'Hasta luego' → DESPEDIDA."""
        result = self.fsm.process("Hasta luego")
        self.assertIsNotNone(result)
        self.assertEqual(self.fsm.state, FSMState.DESPEDIDA)

    def test_verification_stays(self):
        """Client '¿Bueno?' → stays."""
        result = self.fsm.process("¿Bueno?")
        self.assertIsNotNone(result)
        self.assertEqual(self.fsm.state, FSMState.DICTANDO_DATO)


# =============================================================================
# OFRECIENDO_CONTACTO: Bruce ofrece su número
# =============================================================================

class TestOfreciendoContactoState(unittest.TestCase):
    """OFRECIENDO_CONTACTO: Cliente acepta/rechaza número de Bruce."""

    def setUp(self):
        self.fsm = FSMEngine()
        self.fsm.state = FSMState.OFRECIENDO_CONTACTO

    def test_confirmation_tiene_donde_anotar(self):
        """Client 'Sí' → pregunta 'tiene donde anotar'."""
        result = self.fsm.process("Sí, claro")
        self.assertIsNotNone(result)
        self.assertIn("anotar", result.lower())
        self.assertEqual(self.fsm.state, FSMState.OFRECIENDO_CONTACTO)

    def test_reject_to_despedida(self):
        """Client 'No, gracias' → DESPEDIDA."""
        result = self.fsm.process("No gracias")
        self.assertIsNotNone(result)
        self.assertEqual(self.fsm.state, FSMState.DESPEDIDA)

    def test_unknown_dicta_numero(self):
        """Client texto ambiguo → dictar número de Bruce."""
        self.fsm.context.donde_anotar_preguntado = True
        result = self.fsm.process("Dale, dime")
        self.assertIsNotNone(result)
        self.assertIn("662", result)  # Número de Bruce
        self.assertEqual(self.fsm.state, FSMState.OFRECIENDO_CONTACTO)

    def test_farewell_to_despedida(self):
        """Client 'Adiós' → DESPEDIDA."""
        result = self.fsm.process("Ya, adiós, gracias")
        self.assertIsNotNone(result)
        self.assertEqual(self.fsm.state, FSMState.DESPEDIDA)

    def test_guard_donde_anotar_ya_preguntado(self):
        """Si ya preguntó 'donde anotar' → guard falla → None (fallthrough GPT)."""
        self.fsm.context.donde_anotar_preguntado = True
        result = self.fsm.process("Sí, claro")
        # Guard !donde_anotar_preguntado fails → CONFIRMATION has no match
        # No UNKNOWN fallback for CONFIRMATION intent → returns None (GPT handles)
        self.assertIsNone(result)


# =============================================================================
# ESPERANDO_TRANSFERENCIA: Espera durante transferencia
# =============================================================================

class TestEsperandoTransferenciaState(unittest.TestCase):
    """ESPERANDO_TRANSFERENCIA: Espera silenciosa y detección."""

    def setUp(self):
        self.fsm = FSMEngine()
        self.fsm.state = FSMState.ESPERANDO_TRANSFERENCIA

    def test_new_person_confirmation_to_pitch(self):
        """New person 'Sí, dígame' → PITCH."""
        result = self.fsm.process("Sí, dígame")
        self.assertIsNotNone(result)
        self.assertEqual(self.fsm.state, FSMState.PITCH)

    def test_manager_present(self):
        """Manager 'Soy el encargado' → ENCARGADO_PRESENTE."""
        result = self.fsm.process("Soy yo, el encargado de compras")
        self.assertIsNotNone(result)
        self.assertEqual(self.fsm.state, FSMState.ENCARGADO_PRESENTE)

    def test_farewell_to_despedida(self):
        """'Ya colgaron' → DESPEDIDA."""
        result = self.fsm.process("Ya no hay nadie, hasta luego")
        self.assertIsNotNone(result)
        self.assertEqual(self.fsm.state, FSMState.DESPEDIDA)

    def test_unknown_verificacion_in_transfer(self):
        """FIX 929: UNKNOWN → verificacion_aqui_estoy (no BTE fallback)."""
        result = self.fsm.process("Es Acuario, Acuario de la")
        # FIX 929: UNKNOWN in ESPERANDO_TRANSFERENCIA now returns verificacion template
        self.assertIsNotNone(result)
        self.assertEqual(self.fsm.state, FSMState.ESPERANDO_TRANSFERENCIA)

    def test_offer_data_to_dictando(self):
        """Client ofrece datos → DICTANDO_DATO."""
        result = self.fsm.process("Le paso el correo del jefe")
        self.assertIsNotNone(result)
        self.assertEqual(self.fsm.state, FSMState.DICTANDO_DATO)


# =============================================================================
# Sync mapping validation
# =============================================================================

class TestSyncMapping(unittest.TestCase):
    """Verificar que _FSM_TO_ESTADO cubre los 5 nuevos estados."""

    def test_mapping_saludo(self):
        """SALUDO → ESPERANDO_SALUDO mapping exists."""
        # Read agente_ventas.py and verify mapping
        agente_path = os.path.join(os.path.dirname(__file__), '..', 'agente_ventas.py')
        with open(agente_path, 'r', encoding='utf-8') as f:
            source = f.read()
        self.assertIn('FSMState.SALUDO', source)
        self.assertIn('ESPERANDO_SALUDO', source)

    def test_mapping_pitch(self):
        """PITCH → PRESENTACION mapping exists."""
        agente_path = os.path.join(os.path.dirname(__file__), '..', 'agente_ventas.py')
        with open(agente_path, 'r', encoding='utf-8') as f:
            source = f.read()
        self.assertIn('FSMState.PITCH', source)
        self.assertIn('PRESENTACION', source)

    def test_mapping_ofreciendo_contacto(self):
        """OFRECIENDO_CONTACTO → OFRECIENDO_CONTACTO_BRUCE mapping exists."""
        agente_path = os.path.join(os.path.dirname(__file__), '..', 'agente_ventas.py')
        with open(agente_path, 'r', encoding='utf-8') as f:
            source = f.read()
        self.assertIn('FSMState.OFRECIENDO_CONTACTO', source)
        self.assertIn('OFRECIENDO_CONTACTO_BRUCE', source)


if __name__ == '__main__':
    unittest.main()
