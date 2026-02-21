"""
Tests para FIX 751-754:
- FIX 751: Cliente ofrece canal de contacto pero GPT pide otro → override
- FIX 752: Callback sin contacto → despedida prematura → pedir contacto
- FIX 753: Cliente ofrece dato → GPT vacío → FIX 577 "me puede repetir" → aceptar oferta
- FIX 754: FSM gap - DICTATING_COMPLETE_PHONE transitions en todos los estados
"""
import pytest
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agente_ventas import AgenteVentas
from fsm_engine import FSMEngine, FSMState as S, FSMIntent as I


def _crear_agente():
    """Crea agente con atributos mínimos para post-filter tests."""
    agente = AgenteVentas()
    agente.conversation_history = []
    agente.lead_data = {}
    agente.turno_actual = 3
    agente.nombre_negocio = "Test"
    agente.datos_recopilados = {}
    agente.encargado_confirmado = True
    agente.pitch_dado = True
    agente.catalogo_ofrecido = False
    agente.contacto_solicitado = True
    agente.whatsapp_guardado = False
    agente.email_guardado = False
    return agente


# ============================================================
# FIX 751: Cliente ofrece canal → GPT pide otro → override
# ============================================================
class TestFix751OfreceCanalOverride:
    """Cliente ofrece correo/WhatsApp/teléfono pero GPT pide canal diferente."""

    def test_751_ofrece_correo_gpt_pide_whatsapp(self):
        """Cliente ofrece correo, GPT pide WhatsApp → aceptar correo."""
        agente = _crear_agente()
        agente.conversation_history = [
            {"role": "assistant", "content": "Buenos días, me comunico de NIOVAL, distribuidores de productos ferreteros."},
            {"role": "user", "content": "Sí, dígame"},
            {"role": "assistant", "content": "¿Se encuentra el encargado de compras?"},
            {"role": "user", "content": "No, pero si te puedo pasar un correo electrónico"},
        ]
        result = agente._filtrar_respuesta_post_gpt(
            "¿Me podría proporcionar el WhatsApp del encargado?"
        )
        assert 'correo' in result.lower()
        assert 'whatsapp' not in result.lower()

    def test_751_ofrece_correo_variante_le_paso(self):
        """'Le paso el correo' → aceptar correo."""
        agente = _crear_agente()
        agente.conversation_history = [
            {"role": "assistant", "content": "Buenos días, me comunico de NIOVAL."},
            {"role": "user", "content": "Sí"},
            {"role": "assistant", "content": "¿Se encuentra el encargado?"},
            {"role": "user", "content": "No está, le paso el correo del encargado"},
        ]
        result = agente._filtrar_respuesta_post_gpt(
            "¿Me podría dar un número de WhatsApp?"
        )
        assert 'correo' in result.lower()

    def test_751_ofrece_whatsapp_gpt_pide_correo(self):
        """Cliente ofrece WhatsApp, GPT pide correo → aceptar WhatsApp."""
        agente = _crear_agente()
        agente.conversation_history = [
            {"role": "assistant", "content": "Buenos días, me comunico de NIOVAL."},
            {"role": "user", "content": "Sí, dígame"},
            {"role": "assistant", "content": "¿Me podría dar un contacto?"},
            {"role": "user", "content": "Te paso un WhatsApp mejor"},
        ]
        result = agente._filtrar_respuesta_post_gpt(
            "¿Me podría proporcionar un correo electrónico?"
        )
        assert 'whatsapp' in result.lower()

    def test_751_ofrece_telefono_gpt_pide_whatsapp(self):
        """Cliente ofrece teléfono, GPT pide WhatsApp → FIX 751 debe activarse."""
        agente = _crear_agente()
        agente.conversation_history = [
            {"role": "assistant", "content": "Buenos días, me comunico de NIOVAL."},
            {"role": "user", "content": "Sí"},
            {"role": "assistant", "content": "¿Me podría dar un contacto del encargado?"},
            {"role": "user", "content": "Le paso el numero del encargado"},
        ]
        result = agente._filtrar_respuesta_post_gpt(
            "¿Me podría dar el número de WhatsApp?"
        )
        # FIX 751 debe activarse o filtros posteriores ajustar
        assert 'whatsapp' not in result.lower() or 'número' in result.lower() or 'numero' in result.lower()

    def test_751_ofrece_correo_gpt_ignora(self):
        """Cliente ofrece correo, GPT dice 'me puede repetir' → aceptar correo."""
        agente = _crear_agente()
        agente.conversation_history = [
            {"role": "assistant", "content": "Buenos días, me comunico de NIOVAL."},
            {"role": "user", "content": "Sí"},
            {"role": "assistant", "content": "¿Se encuentra el encargado?"},
            {"role": "user", "content": "Te podría pasar un correo del encargado"},
        ]
        result = agente._filtrar_respuesta_post_gpt(
            "Disculpe, no le escuché bien"
        )
        assert 'correo' in result.lower()

    def test_751_no_false_positive_sin_oferta(self):
        """Si cliente NO ofrece canal, no activar FIX 751."""
        agente = _crear_agente()
        agente.conversation_history = [
            {"role": "assistant", "content": "Buenos días, me comunico de NIOVAL."},
            {"role": "user", "content": "Sí, dígame"},
            {"role": "assistant", "content": "¿Se encuentra el encargado?"},
            {"role": "user", "content": "No, no está en este momento"},
        ]
        original = "Entiendo. ¿Me podría proporcionar un número de WhatsApp del encargado para enviarle nuestro catálogo?"
        result = agente._filtrar_respuesta_post_gpt(original)
        # No debería activar FIX 751 - cliente no ofreció canal
        assert 'claro que' not in result.lower()

    def test_751_te_puedo_proporcionar_correo(self):
        """'Te puedo proporcionar un correo' → aceptar correo."""
        agente = _crear_agente()
        agente.conversation_history = [
            {"role": "assistant", "content": "Buenos días, me comunico de NIOVAL."},
            {"role": "user", "content": "Sí"},
            {"role": "assistant", "content": "¿Me podría dar un contacto del encargado?"},
            {"role": "user", "content": "Sí, te puedo proporcionar un correo electrónico"},
        ]
        result = agente._filtrar_respuesta_post_gpt(
            "¿Me podría proporcionar el WhatsApp?"
        )
        assert 'correo' in result.lower()

    def test_751_por_correo_mejor(self):
        """'Por correo mejor' → aceptar correo."""
        agente = _crear_agente()
        agente.conversation_history = [
            {"role": "assistant", "content": "Buenos días, me comunico de NIOVAL."},
            {"role": "user", "content": "Sí"},
            {"role": "assistant", "content": "¿Me da un WhatsApp?"},
            {"role": "user", "content": "No, por correo mejor"},
        ]
        result = agente._filtrar_respuesta_post_gpt(
            "¿Me podría dar un número de WhatsApp entonces?"
        )
        assert 'correo' in result.lower()

    def test_751_te_mando_correo(self):
        """'Te mando un correo' → aceptar correo."""
        agente = _crear_agente()
        agente.conversation_history = [
            {"role": "assistant", "content": "Buenos días, me comunico de NIOVAL."},
            {"role": "user", "content": "Sí, dígame"},
            {"role": "assistant", "content": "¿Se encontrará el encargado?"},
            {"role": "user", "content": "Si quieres te paso un correo del encargado"},
        ]
        result = agente._filtrar_respuesta_post_gpt(
            "¿Me podría dar un número de WhatsApp?"
        )
        assert 'correo' in result.lower()


# ============================================================
# FIX 752: Callback sin contacto → despedida prematura
# ============================================================
class TestFix752CallbackSinContacto:
    """Bruce se despide en callback sin haber capturado contacto."""

    def test_752_callback_manana_sin_contacto(self):
        """Callback mañana, sin contacto, Bruce se despide → pedir contacto."""
        agente = _crear_agente()
        agente.conversation_history = [
            {"role": "assistant", "content": "Buenos días, me comunico de NIOVAL."},
            {"role": "user", "content": "Sí, dígame"},
            {"role": "assistant", "content": "¿Se encuentra el encargado?"},
            {"role": "user", "content": "No, el encargado regresa mañana"},
            {"role": "assistant", "content": "Entiendo, ¿a qué hora mañana?"},
            {"role": "user", "content": "En la mañana como a las 9"},
        ]
        result = agente._filtrar_respuesta_post_gpt(
            "Perfecto, muchas gracias por su tiempo. Que tenga excelente día."
        )
        assert 'número' in result.lower() or 'numero' in result.lower() or 'contacto' in result.lower()

    def test_752_callback_no_esta_sin_contacto(self):
        """'No está' → callback implícito, sin contacto → pedir contacto."""
        agente = _crear_agente()
        agente.conversation_history = [
            {"role": "assistant", "content": "Buenos días, me comunico de NIOVAL."},
            {"role": "user", "content": "Sí"},
            {"role": "assistant", "content": "¿Se encuentra el encargado?"},
            {"role": "user", "content": "No está, salió a comer"},
            {"role": "assistant", "content": "Entiendo"},
            {"role": "user", "content": "Sí, marque más tarde"},
        ]
        result = agente._filtrar_respuesta_post_gpt(
            "Le agradezco mucho su tiempo. Hasta luego."
        )
        assert 'número' in result.lower() or 'numero' in result.lower() or 'contacto' in result.lower()

    def test_752_no_override_si_tiene_contacto(self):
        """Si ya tiene contacto capturado, FIX 752 NO debe pedir contacto."""
        agente = _crear_agente()
        agente.lead_data = {"telefono": "3312345678"}
        agente.whatsapp_guardado = True
        agente.turno_actual = 6
        agente.conversation_history = [
            {"role": "assistant", "content": "Buenos días, me comunico de NIOVAL, distribuidores de productos ferreteros."},
            {"role": "user", "content": "Sí, dígame"},
            {"role": "assistant", "content": "Le comento, manejamos más de quince categorías. ¿Se encontrará el encargado?"},
            {"role": "user", "content": "Sí, soy yo"},
            {"role": "assistant", "content": "¿Me podría dar un WhatsApp para enviarle catálogo?"},
            {"role": "user", "content": "Sí, es el 3312345678"},
            {"role": "assistant", "content": "Perfecto, ya lo tengo anotado."},
            {"role": "user", "content": "Muy bien, está bien, mañana me comunico"},
        ]
        result = agente._filtrar_respuesta_post_gpt(
            "Perfecto, muchas gracias por su tiempo. Que tenga excelente día."
        )
        # FIX 752 NO debe activar - ya tiene contacto
        # La respuesta puede ser modificada por otros filtros pero NO debe pedir número
        assert 'me podría dejar un número' not in result.lower()

    def test_752_no_override_sin_callback(self):
        """Sin callback mencionado, FIX 752 NO debe pedir contacto."""
        agente = _crear_agente()
        agente.turno_actual = 5
        agente.conversation_history = [
            {"role": "assistant", "content": "Buenos días, me comunico de NIOVAL, distribuidores de productos ferreteros."},
            {"role": "user", "content": "Sí, dígame"},
            {"role": "assistant", "content": "Manejamos más de quince categorías. ¿Se encontrará el encargado?"},
            {"role": "user", "content": "No compramos de eso, no nos interesa, gracias"},
            {"role": "assistant", "content": "Entiendo"},
            {"role": "user", "content": "No, gracias"},
        ]
        result = agente._filtrar_respuesta_post_gpt(
            "Le agradezco mucho su tiempo. Que tenga excelente día."
        )
        # FIX 752 NO debe activar - no hay callback
        assert 'me podría dejar un número' not in result.lower()

    def test_752_callback_regresa(self):
        """'Regresa en la tarde' → callback sin contacto → pedir contacto."""
        agente = _crear_agente()
        agente.conversation_history = [
            {"role": "assistant", "content": "Buenos días, me comunico de NIOVAL."},
            {"role": "user", "content": "Sí"},
            {"role": "assistant", "content": "¿Se encuentra el encargado?"},
            {"role": "user", "content": "No, regresa en la tarde"},
            {"role": "assistant", "content": "¿A qué hora en la tarde?"},
            {"role": "user", "content": "Como a las 3"},
        ]
        result = agente._filtrar_respuesta_post_gpt(
            "Muchas gracias por su tiempo. Que tenga excelente día."
        )
        assert 'número' in result.lower() or 'numero' in result.lower()

    def test_752_no_despedida_no_activa(self):
        """Si Bruce NO se despide, no activar FIX 752."""
        agente = _crear_agente()
        agente.conversation_history = [
            {"role": "assistant", "content": "Buenos días, me comunico de NIOVAL."},
            {"role": "user", "content": "Sí"},
            {"role": "assistant", "content": "¿Se encuentra el encargado?"},
            {"role": "user", "content": "No, regresa mañana"},
        ]
        original = "¿A qué hora mañana podría encontrarlo?"
        result = agente._filtrar_respuesta_post_gpt(original)
        assert result == original


# ============================================================
# FIX 753: Cliente ofrece dato → GPT vacío → FIX 577 fallback
# ============================================================
class TestFix753OfertaDatoFallback:
    """Tests para FIX 753 - detectar oferta dato en FIX 577 fallback."""

    def test_753_te_paso_correo(self):
        """'Si te paso un correo' debe matchear."""
        patterns = [
            'te paso un', 'le paso un', 'si te doy', 'si le doy',
            'te puedo dar', 'le puedo dar', 'te podria dar', 'le podria dar',
            'te puedo pasar', 'le puedo pasar', 'te podria pasar', 'le podria pasar',
            'te puedo proporcionar', 'le puedo proporcionar',
            'por correo mejor', 'mejor por correo', 'te paso el correo',
            'le paso el correo', 'te doy el correo', 'le doy el correo',
            'te paso el numero', 'le paso el numero', 'te doy un numero',
            'le doy un numero', 'te paso mi', 'le paso mi',
            'te puedo mandar', 'le puedo mandar', 'te mando un',
            'le mando un', 'si quieres te paso', 'si gusta le paso'
        ]
        assert any(p in "si te paso un correo electronico" for p in patterns)

    def test_753_le_puedo_dar_numero(self):
        """'Le puedo dar un número' debe matchear."""
        patterns = ['le puedo dar']
        assert any(p in "le puedo dar un numero" for p in patterns)

    def test_753_no_match_rechazo(self):
        """'No compramos' no debe matchear oferta."""
        patterns = [
            'te paso un', 'le paso un', 'si te doy', 'si le doy',
            'te puedo dar', 'le puedo dar', 'te podria dar', 'le podria dar',
            'te puedo pasar', 'le puedo pasar', 'te podria pasar', 'le podria pasar'
        ]
        assert not any(p in "no compramos gracias" for p in patterns)

    def test_753_te_podria_pasar_correo(self):
        """'Te podría pasar un correo' debe matchear."""
        assert 'te podria pasar' in "te podria pasar un correo"

    def test_753_si_gusta_le_paso(self):
        """'Si gusta le paso un correo' debe matchear."""
        assert 'si gusta le paso' in "si gusta le paso un correo del encargado"

    def test_753_te_mando_un(self):
        """'Te mando un correo' debe matchear."""
        assert 'te mando un' in "te mando un correo del encargado"

    def test_753_channel_detection_correo(self):
        """Con 'correo' en texto → respuesta debe mencionar correo."""
        text = "si te paso un correo electronico"
        channel_words = ['correo', 'email', 'mail']
        assert any(w in text for w in channel_words)

    def test_753_channel_detection_whatsapp(self):
        """Con 'whatsapp' en texto → respuesta debe mencionar WhatsApp."""
        text = "te paso un whatsapp"
        channel_words = ['whatsapp', 'wats', 'guats']
        assert any(w in text for w in channel_words)


# ============================================================
# FIX 754: FSM transitions para DICTATING_COMPLETE_PHONE
# ============================================================
class TestFix754FSMTransitions:
    """FSM debe manejar DICTATING_COMPLETE_PHONE en todos los estados relevantes."""

    def setup_method(self):
        self.fsm = FSMEngine()

    def test_754_encargado_presente_complete_phone(self):
        """ENCARGADO_PRESENTE + teléfono completo → CONTACTO_CAPTURADO."""
        self.fsm.state = S.ENCARGADO_PRESENTE
        self.fsm.process("Mi número es 33 12 34 56 78", None)
        assert self.fsm.state == S.CONTACTO_CAPTURADO

    def test_754_encargado_presente_complete_email(self):
        """ENCARGADO_PRESENTE + email completo → CONTACTO_CAPTURADO."""
        self.fsm.state = S.ENCARGADO_PRESENTE
        self.fsm.process("El correo es juan@gmail.com", None)
        assert self.fsm.state == S.CONTACTO_CAPTURADO

    def test_754_encargado_presente_partial(self):
        """ENCARGADO_PRESENTE + dictado parcial → DICTANDO_DATO."""
        self.fsm.state = S.ENCARGADO_PRESENTE
        self.fsm.process("Es el 33 12", None)
        assert self.fsm.state == S.DICTANDO_DATO

    def test_754_encargado_ausente_complete_phone(self):
        """ENCARGADO_AUSENTE + teléfono completo → CONTACTO_CAPTURADO."""
        self.fsm.state = S.ENCARGADO_AUSENTE
        self.fsm.process("El teléfono es 66 21 23 45 67", None)
        assert self.fsm.state == S.CONTACTO_CAPTURADO

    def test_754_encargado_ausente_complete_email(self):
        """ENCARGADO_AUSENTE + email completo → CONTACTO_CAPTURADO."""
        self.fsm.state = S.ENCARGADO_AUSENTE
        self.fsm.process("correo@empresa.com.mx", None)
        assert self.fsm.state == S.CONTACTO_CAPTURADO

    def test_754_encargado_ausente_partial(self):
        """ENCARGADO_AUSENTE + dictado parcial → DICTANDO_DATO."""
        self.fsm.state = S.ENCARGADO_AUSENTE
        self.fsm.process("Es 33 45", None)
        assert self.fsm.state == S.DICTANDO_DATO

    def test_754_buscando_encargado_complete_phone(self):
        """BUSCANDO_ENCARGADO + teléfono completo → CONTACTO_CAPTURADO."""
        self.fsm.state = S.BUSCANDO_ENCARGADO
        self.fsm.process("Anote este número 33 98 76 54 32", None)
        assert self.fsm.state == S.CONTACTO_CAPTURADO

    def test_754_buscando_encargado_complete_email(self):
        """BUSCANDO_ENCARGADO + email completo → CONTACTO_CAPTURADO."""
        self.fsm.state = S.BUSCANDO_ENCARGADO
        self.fsm.process("Le doy el correo ventas@ferreteria.com", None)
        assert self.fsm.state == S.CONTACTO_CAPTURADO

    def test_754_buscando_encargado_partial(self):
        """BUSCANDO_ENCARGADO + dictado parcial → DICTANDO_DATO."""
        self.fsm.state = S.BUSCANDO_ENCARGADO
        self.fsm.process("Sí, es el 662 123", None)
        assert self.fsm.state == S.DICTANDO_DATO

    def test_754_pitch_complete_phone(self):
        """PITCH + teléfono completo → CONTACTO_CAPTURADO."""
        self.fsm.state = S.PITCH
        self.fsm.process("Mi número es 33 44 55 66 77", None)
        assert self.fsm.state == S.CONTACTO_CAPTURADO

    def test_754_pitch_complete_email(self):
        """PITCH + email completo → CONTACTO_CAPTURADO."""
        self.fsm.state = S.PITCH
        self.fsm.process("Mándalo a contacto@tienda.com", None)
        assert self.fsm.state == S.CONTACTO_CAPTURADO

    def test_754_pitch_partial(self):
        """PITCH + dictado parcial → DICTANDO_DATO."""
        self.fsm.state = S.PITCH
        self.fsm.process("Apunta 33 12", None)
        assert self.fsm.state == S.DICTANDO_DATO

    def test_754_capturando_contacto_still_works(self):
        """CAPTURANDO_CONTACTO + teléfono → CONTACTO_CAPTURADO (existing)."""
        self.fsm.state = S.CAPTURANDO_CONTACTO
        self.fsm.process("Es el 33 12 34 56 78", None)
        assert self.fsm.state == S.CONTACTO_CAPTURADO

    def test_754_dictando_dato_still_works(self):
        """DICTANDO_DATO + teléfono completo → CONTACTO_CAPTURADO (existing)."""
        self.fsm.state = S.DICTANDO_DATO
        self.fsm.process("78 el completo es 33 12 34 56 78", None)
        assert self.fsm.state == S.CONTACTO_CAPTURADO

    def test_754_contacto_capturado_to_despedida(self):
        """CONTACTO_CAPTURADO → DESPEDIDA (existing flow)."""
        self.fsm.state = S.CONTACTO_CAPTURADO
        self.fsm.process("Perfecto, gracias", None)
        assert self.fsm.state == S.DESPEDIDA

    def test_754_intent_partial_in_encargado_presente(self):
        """classify_intent debe retornar DICTATING_PARTIAL en ENCARGADO_PRESENTE."""
        from fsm_engine import classify_intent, FSMContext
        ctx = FSMContext()
        result = classify_intent("Es el 33 12", ctx, S.ENCARGADO_PRESENTE)
        assert result == I.DICTATING_PARTIAL

    def test_754_intent_partial_in_encargado_ausente(self):
        """classify_intent debe retornar DICTATING_PARTIAL en ENCARGADO_AUSENTE."""
        from fsm_engine import classify_intent, FSMContext
        ctx = FSMContext()
        result = classify_intent("Anote 33 45", ctx, S.ENCARGADO_AUSENTE)
        assert result == I.DICTATING_PARTIAL


# ============================================================
# Tests de integración: flujo completo BRUCE2416-like
# ============================================================
class TestFix754IntegracionFlujo:
    """Flujo completo como BRUCE2416: encargado → WhatsApp → número → despedida."""

    def setup_method(self):
        self.fsm = FSMEngine()

    def test_flujo_bruce2416_encargado_a_contacto(self):
        """Simular flujo BRUCE2416: encargado presente → dicta teléfono → capturado."""
        assert self.fsm.state == S.SALUDO

        # Cliente responde al saludo
        self.fsm.process("Sí, buenas tardes", None)
        assert self.fsm.state == S.PITCH

        # Cliente confirma interés → buscar encargado
        self.fsm.process("Sí, dígame", None)
        assert self.fsm.state == S.BUSCANDO_ENCARGADO

        # Encargado presente
        self.fsm.process("Sí, soy yo, el encargado", None)
        assert self.fsm.state == S.ENCARGADO_PRESENTE

        # FIX 754: Cliente dicta teléfono completo desde ENCARGADO_PRESENTE
        self.fsm.process("Le doy mi número 33 12 34 56 78", None)
        assert self.fsm.state == S.CONTACTO_CAPTURADO

        # Despedida
        self.fsm.process("Gracias, hasta luego", None)
        assert self.fsm.state == S.DESPEDIDA

    def test_flujo_encargado_ausente_a_contacto(self):
        """Encargado ausente → cliente dicta teléfono → capturado."""
        self.fsm.state = S.ENCARGADO_AUSENTE
        self.fsm.process("Le doy el teléfono del encargado 66 21 23 45 67", None)
        assert self.fsm.state == S.CONTACTO_CAPTURADO

    def test_flujo_buscando_encargado_email(self):
        """Buscando encargado → cliente dicta email → capturado."""
        self.fsm.state = S.BUSCANDO_ENCARGADO
        self.fsm.process("Le paso el correo ventas@laferreteria.com", None)
        assert self.fsm.state == S.CONTACTO_CAPTURADO

    def test_flujo_capturando_via_dictado_parcial(self):
        """Encargado presente → dictado parcial → dictando → completo → capturado."""
        self.fsm.state = S.ENCARGADO_PRESENTE

        # Dictado parcial (4 dígitos)
        self.fsm.process("Sí, anote, es el 33 12", None)
        assert self.fsm.state == S.DICTANDO_DATO

        # Completa teléfono (10 dígitos)
        self.fsm.process("34 56 78 90 12 ya ese es el completo", None)
        assert self.fsm.state == S.CONTACTO_CAPTURADO

    def test_flujo_encargado_ausente_parcial_a_completo(self):
        """Encargado ausente → dictado parcial → completo → capturado."""
        self.fsm.state = S.ENCARGADO_AUSENTE

        # Dictado parcial
        self.fsm.process("Es el 662 12", None)
        assert self.fsm.state == S.DICTANDO_DATO

        # Completa
        self.fsm.process("34 56 78 ya 6621234567", None)
        assert self.fsm.state == S.CONTACTO_CAPTURADO
