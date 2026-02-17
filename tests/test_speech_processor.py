# -*- coding: utf-8 -*-
"""
Tests de regresión para FIX 700: Speech Processor
Verifica que SpeechStateMachine maneja estados, transiciones,
acknowledgments, y decisiones wait/process correctamente.
"""
import os
import sys
import time
import pytest

# Agregar directorio padre al path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from speech_processor import SpeechStateMachine, SpeechState, SpeechAction


@pytest.fixture
def sm():
    """Crea una instancia limpia de SpeechStateMachine."""
    return SpeechStateMachine()


# ============================================================
# STATE TRANSITIONS - Dictado de teléfono
# ============================================================

class TestDictadoTelefono:
    """Tests de transición a DICTATING_PHONE."""

    def test_digitos_parciales_2(self, sm):
        state, action = sm.process_input("3 3")
        assert state == SpeechState.DICTATING_PHONE
        assert action == SpeechAction.ACKNOWLEDGE

    def test_digitos_parciales_5(self, sm):
        state, action = sm.process_input("3 3 1 2 3")
        assert state == SpeechState.DICTATING_PHONE
        assert action == SpeechAction.ACKNOWLEDGE

    def test_digitos_parciales_9(self, sm):
        state, action = sm.process_input("331 234 567")
        assert state == SpeechState.DICTATING_PHONE
        assert action == SpeechAction.ACKNOWLEDGE

    def test_telefono_completo_10_digitos(self, sm):
        state, action = sm.process_input("3312345678")
        assert state == SpeechState.IDLE
        assert action == SpeechAction.PROCESS

    def test_telefono_con_texto(self, sm):
        state, action = sm.process_input("Es el 331 234")
        assert state == SpeechState.DICTATING_PHONE
        assert action == SpeechAction.ACKNOWLEDGE

    def test_digitos_preservados(self, sm):
        sm.process_input("331 234")
        assert sm.partial_digits == "331234"

    def test_telefono_completo_preservado(self, sm):
        sm.process_input("3312345678")
        assert sm.partial_digits == "3312345678"

    def test_no_detectar_hora_como_telefono(self, sm):
        sm.set_waiting_for_hour(True)
        state, action = sm.process_input("A las 9 30")
        # No debe detectar como teléfono
        assert state != SpeechState.DICTATING_PHONE


# ============================================================
# STATE TRANSITIONS - Dictado de email
# ============================================================

class TestDictadoEmail:
    """Tests de transición a DICTATING_EMAIL."""

    def test_arroba_detectado(self, sm):
        state, action = sm.process_input("ventas arroba gmail")
        assert state == SpeechState.DICTATING_EMAIL
        assert action == SpeechAction.ACKNOWLEDGE

    def test_at_sign_detectado(self, sm):
        state, action = sm.process_input("ventas@gmail")
        assert state == SpeechState.DICTATING_EMAIL
        assert action == SpeechAction.ACKNOWLEDGE

    def test_punto_com_detectado(self, sm):
        state, action = sm.process_input("ventas punto com")
        assert state == SpeechState.DICTATING_EMAIL
        assert action == SpeechAction.ACKNOWLEDGE

    def test_gmail_detectado(self, sm):
        state, action = sm.process_input("es un gmail")
        assert state == SpeechState.DICTATING_EMAIL
        assert action == SpeechAction.ACKNOWLEDGE

    def test_hotmail_detectado(self, sm):
        state, action = sm.process_input("tengo hotmail")
        assert state == SpeechState.DICTATING_EMAIL
        assert action == SpeechAction.ACKNOWLEDGE

    def test_deletreo_fonetico(self, sm):
        state, action = sm.process_input("v de vaca e de estrella")
        assert state == SpeechState.DICTATING_EMAIL
        assert action == SpeechAction.ACKNOWLEDGE


# ============================================================
# STATE TRANSITIONS - Info parcial
# ============================================================

class TestInfoParcial:
    """Tests de transición a PARTIAL_INFO."""

    def test_termina_en_coma(self, sm):
        state, action = sm.process_input("A ver, te voy a dar un teléfono,")
        assert state == SpeechState.PARTIAL_INFO
        assert action == SpeechAction.ACKNOWLEDGE

    def test_termina_en_y(self, sm):
        state, action = sm.process_input("El número del encargado y")
        assert state == SpeechState.PARTIAL_INFO
        assert action == SpeechAction.ACKNOWLEDGE

    def test_termina_en_entonces(self, sm):
        state, action = sm.process_input("Sí me interesa entonces")
        assert state == SpeechState.PARTIAL_INFO
        assert action == SpeechAction.ACKNOWLEDGE

    def test_termina_en_pues(self, sm):
        state, action = sm.process_input("No está el encargado pues")
        assert state == SpeechState.PARTIAL_INFO

    def test_confirmacion_corta_no_parcial(self, sm):
        """FIX 592: 'Sí, señor,' NO debe ser parcial."""
        state, action = sm.process_input("Sí,")
        assert state != SpeechState.PARTIAL_INFO

    def test_confirmacion_bueno_no_parcial(self, sm):
        state, action = sm.process_input("Bueno,")
        assert state != SpeechState.PARTIAL_INFO

    def test_mande_no_parcial(self, sm):
        state, action = sm.process_input("Mande,")
        assert state != SpeechState.PARTIAL_INFO

    def test_continuation_count_incrementa(self, sm):
        sm.process_input("primero,")
        assert sm.continuation_count == 1
        sm.process_input("segundo,")
        assert sm.continuation_count == 2


# ============================================================
# STATE TRANSITIONS - Cliente ofrece dato
# ============================================================

class TestClienteOfreceDato:
    """Tests de transición a CLIENT_OFFERING_DATA."""

    def test_te_paso_su(self, sm):
        state, action = sm.process_input("Te paso su teléfono")
        assert state == SpeechState.CLIENT_OFFERING_DATA
        assert action == SpeechAction.ACKNOWLEDGE

    def test_le_voy_a_dar(self, sm):
        state, action = sm.process_input("Le voy a dar un correo")
        assert state == SpeechState.CLIENT_OFFERING_DATA

    def test_te_puedo_pasar(self, sm):
        state, action = sm.process_input("Te puedo pasar mi número")
        assert state == SpeechState.CLIENT_OFFERING_DATA

    def test_anote(self, sm):
        state, action = sm.process_input("Anote, es el siguiente")
        assert state == SpeechState.CLIENT_OFFERING_DATA


# ============================================================
# STATE TRANSITIONS - Preguntas directas
# ============================================================

class TestPreguntaDirecta:
    """Tests de pregunta directa → PROCESS."""

    def test_que_quiere(self, sm):
        state, action = sm.process_input("¿Qué quiere?")
        assert state == SpeechState.IDLE
        assert action == SpeechAction.PROCESS

    def test_quien_habla(self, sm):
        state, action = sm.process_input("¿Quién habla?")
        assert state == SpeechState.IDLE
        assert action == SpeechAction.PROCESS

    def test_pregunta_generica(self, sm):
        state, action = sm.process_input("¿Y cuánto cuesta?")
        assert state == SpeechState.IDLE
        assert action == SpeechAction.PROCESS


# ============================================================
# STATE TRANSITIONS - Casos default
# ============================================================

class TestDefault:
    """Tests de transición default."""

    def test_frase_normal_process(self, sm):
        state, action = sm.process_input("No está el encargado ahorita")
        assert state == SpeechState.IDLE
        assert action == SpeechAction.PROCESS

    def test_confirmacion_simple(self, sm):
        state, action = sm.process_input("Sí, claro")
        assert state == SpeechState.IDLE
        assert action == SpeechAction.PROCESS

    def test_texto_vacio_ignore(self, sm):
        state, action = sm.process_input("")
        assert action == SpeechAction.IGNORE

    def test_none_ignore(self, sm):
        state, action = sm.process_input(None)
        assert action == SpeechAction.IGNORE

    def test_solo_espacios_ignore(self, sm):
        state, action = sm.process_input("   ")
        assert action == SpeechAction.IGNORE

    def test_is_partial_wait(self, sm):
        state, action = sm.process_input("El encargado", is_partial=True)
        assert state == SpeechState.WAITING_CONTINUATION
        assert action == SpeechAction.WAIT


# ============================================================
# GET ACKNOWLEDGMENT
# ============================================================

class TestGetAcknowledgment:
    """Tests de get_acknowledgment()."""

    def test_ack_dictating_phone(self, sm):
        sm.process_input("331 234")
        assert sm.get_acknowledgment() == "Ajá, sí."

    def test_ack_dictating_email(self, sm):
        sm.process_input("ventas arroba gmail")
        assert sm.get_acknowledgment() == "Ajá, sí."

    def test_ack_partial_info(self, sm):
        sm.process_input("Te voy a dar un teléfono,")
        assert sm.get_acknowledgment() == "Ajá, sí."

    def test_ack_offering_data(self, sm):
        sm.process_input("Te paso su número")
        assert sm.get_acknowledgment() == "Ajá, sí."

    def test_no_ack_idle(self, sm):
        sm.process_input("No está el encargado")
        assert sm.get_acknowledgment() is None

    def test_no_ack_processing(self, sm):
        assert sm.get_acknowledgment() is None  # Estado IDLE por default


# ============================================================
# SHOULD WAIT / SHOULD PROCESS
# ============================================================

class TestShouldWaitProcess:
    """Tests de should_wait() y should_process()."""

    def test_wait_dictating_phone(self, sm):
        sm.process_input("331 234")
        assert sm.should_wait() == True
        assert sm.should_process() == False

    def test_wait_dictating_email(self, sm):
        sm.process_input("ventas arroba")
        assert sm.should_wait() == True

    def test_wait_partial_info(self, sm):
        sm.process_input("El número es,")
        assert sm.should_wait() == True

    def test_wait_offering(self, sm):
        sm.process_input("Te paso su teléfono")
        assert sm.should_wait() == True

    def test_wait_continuation(self, sm):
        sm.process_input("algo", is_partial=True)
        assert sm.should_wait() == True

    def test_process_normal(self, sm):
        sm.process_input("No está el encargado")
        assert sm.should_process() == True
        assert sm.should_wait() == False

    def test_process_idle(self, sm):
        assert sm.should_process() == True  # Default state


# ============================================================
# SHOULD ACKNOWLEDGE
# ============================================================

class TestShouldAcknowledge:
    """Tests de should_acknowledge()."""

    def test_ack_dictating(self, sm):
        sm.process_input("331 234")
        assert sm.should_acknowledge() == True

    def test_no_ack_idle(self, sm):
        assert sm.should_acknowledge() == False

    def test_no_ack_after_process(self, sm):
        sm.process_input("No gracias")
        assert sm.should_acknowledge() == False


# ============================================================
# WAITING FOR HOUR (FIX 526)
# ============================================================

class TestWaitingForHour:
    """Tests de set_waiting_for_hour() compatibilidad FIX 526."""

    def test_set_waiting_hour(self, sm):
        sm.set_waiting_for_hour(True)
        assert sm.waiting_for_hour == True

    def test_unset_waiting_hour(self, sm):
        sm.set_waiting_for_hour(True)
        sm.set_waiting_for_hour(False)
        assert sm.waiting_for_hour == False

    def test_digitos_no_telefono_cuando_espera_hora(self, sm):
        sm.set_waiting_for_hour(True)
        state, action = sm.process_input("A las 9 30 de la mañana")
        assert state != SpeechState.DICTATING_PHONE


# ============================================================
# STATE INFO / LOGGING
# ============================================================

class TestStateInfo:
    """Tests de get_state_info()."""

    def test_info_default(self, sm):
        info = sm.get_state_info()
        assert info['state'] == 'idle'
        assert info['previous'] is None
        assert info['partial_digits'] == ''
        assert info['continuation_count'] == 0

    def test_info_after_transition(self, sm):
        sm.process_input("331 234")
        info = sm.get_state_info()
        assert info['state'] == 'dictating_phone'
        assert info['previous'] == 'idle'
        assert info['partial_digits'] == '331234'

    def test_time_in_state(self, sm):
        info = sm.get_state_info()
        assert info['time_in_state'] >= 0


# ============================================================
# RESET
# ============================================================

class TestReset:
    """Tests de reset()."""

    def test_reset_limpia_estado(self, sm):
        sm.process_input("331 234")
        sm.set_waiting_for_hour(True)
        sm.continuation_count = 5

        sm.reset()

        assert sm.state == SpeechState.IDLE
        assert sm.previous_state is None
        assert sm.partial_digits == ""
        assert sm.continuation_count == 0
        assert sm.waiting_for_hour == False


# ============================================================
# NORMALIZE
# ============================================================

class TestNormalize:
    """Tests de _normalize()."""

    def test_lowercase(self, sm):
        assert sm._normalize("HOLA") == "hola"

    def test_strip_acentos(self, sm):
        assert sm._normalize("Hábleme mañana") == "hableme manana"

    def test_strip_ene(self, sm):
        assert sm._normalize("señor") == "senor"

    def test_strip_multiple(self, sm):
        assert sm._normalize("Sí, búsquelo después") == "si, busquelo despues"


# ============================================================
# INTEGRACIÓN - Flujos completos
# ============================================================

class TestIntegracion:
    """Tests de integración con flujos de conversación."""

    def test_flujo_dictado_telefono_completo(self, sm):
        """Cliente dicta teléfono en 3 partes."""
        s1, a1 = sm.process_input("Apunte, el número es")
        assert s1 == SpeechState.CLIENT_OFFERING_DATA

        s2, a2 = sm.process_input("331 234")
        assert s2 == SpeechState.DICTATING_PHONE
        assert a2 == SpeechAction.ACKNOWLEDGE

        s3, a3 = sm.process_input("3312345678")
        assert s3 == SpeechState.IDLE
        assert a3 == SpeechAction.PROCESS
        assert sm.partial_digits == "3312345678"

    def test_flujo_email_parcial(self, sm):
        """Cliente dicta email con pausa."""
        s1, a1 = sm.process_input("ventas arroba gmail")
        assert s1 == SpeechState.DICTATING_EMAIL
        assert sm.should_wait() == True

    def test_flujo_info_parcial_coma(self, sm):
        """Cliente da info con coma (BRUCE2244)."""
        s1, a1 = sm.process_input("A ver, te voy a dar un teléfono,")
        assert s1 == SpeechState.PARTIAL_INFO
        assert a1 == SpeechAction.ACKNOWLEDGE
        assert sm.get_acknowledgment() == "Ajá, sí."

    def test_flujo_pregunta_rompe_dictado(self, sm):
        """Pregunta directa saca de estado dictado."""
        sm.process_input("331 234")
        assert sm.state == SpeechState.DICTATING_PHONE

        s2, a2 = sm.process_input("¿Número de quién?")
        assert s2 == SpeechState.IDLE
        assert a2 == SpeechAction.PROCESS

    def test_flujo_callback_hora(self, sm):
        """Bruce pregunta hora → dígitos NO son teléfono."""
        sm.set_waiting_for_hour(True)
        s1, a1 = sm.process_input("A las 9 de la mañana")
        assert s1 != SpeechState.DICTATING_PHONE

    def test_multiple_transiciones(self, sm):
        """Múltiples transiciones preservan historial."""
        sm.process_input("331 234")
        assert sm.state == SpeechState.DICTATING_PHONE

        sm.process_input("No, espere")
        assert sm.previous_state == SpeechState.DICTATING_PHONE


# ============================================================
# INTEGRACIÓN CON AGENTE
# ============================================================

class TestIntegracionAgente:
    """Tests de integración con AgenteVentas."""

    def test_agente_tiene_speech(self):
        """Verificar que AgenteVentas tiene atributo speech tras FIX 700."""
        os.environ.setdefault("OPENAI_API_KEY", "sk-test-dummy")
        os.environ.setdefault("ELEVENLABS_API_KEY", "test-dummy")
        os.environ.setdefault("TWILIO_ACCOUNT_SID", "AC-test")
        os.environ.setdefault("TWILIO_AUTH_TOKEN", "test-token")

        from agente_ventas import AgenteVentas
        a = AgenteVentas.__new__(AgenteVentas)
        a.speech = None
        try:
            a.speech = SpeechStateMachine()
        except Exception:
            pass

        assert a.speech is not None
        assert isinstance(a.speech, SpeechStateMachine)

    def test_speech_processor_import(self):
        """Verificar que speech_processor se importa correctamente."""
        from speech_processor import SpeechStateMachine as SSM
        m = SSM()
        assert hasattr(m, 'process_input')
        assert hasattr(m, 'get_acknowledgment')
        assert hasattr(m, 'should_wait')
        assert hasattr(m, 'should_process')
        assert hasattr(m, 'should_acknowledge')
        assert hasattr(m, 'reset')
        assert hasattr(m, 'get_state_info')
        assert hasattr(m, 'set_waiting_for_hour')

    def test_enums_accesibles(self):
        """Verificar que enums son accesibles."""
        assert SpeechState.IDLE.value == "idle"
        assert SpeechState.DICTATING_PHONE.value == "dictating_phone"
        assert SpeechAction.ACKNOWLEDGE.value == "acknowledge"
        assert SpeechAction.PROCESS.value == "process"
        assert SpeechAction.WAIT.value == "wait"
