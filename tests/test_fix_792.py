"""
Tests for FIX 792: Template fallback before GPT full.

FIX 792 adds a safety net in procesar_respuesta() that returns template
responses based on estado_conversacion BEFORE the expensive GPT full call.
This catches cases where FSM returned None (error, guard failure, etc.)
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from agente_ventas import AgenteVentas, EstadoConversacion


def _make_agente():
    """Create AgenteVentas with minimal init (no API keys needed)."""
    agente = AgenteVentas()
    agente.conversacion_iniciada = True
    agente.segunda_parte_saludo_dicha = True
    agente.conversation_history = [
        {"role": "assistant", "content": "Hola, buen dia. Le llamo de NIOVAL."}
    ]
    return agente


# ============================================================
# Test 1: Each estado returns correct template
# ============================================================

class TestFix792Templates(unittest.TestCase):
    """_try_narrow_prompt_792 returns correct template per estado."""

    def setUp(self):
        self.agente = _make_agente()

    def test_encargado_no_esta(self):
        """ENCARGADO_NO_ESTA → pedir WhatsApp/correo."""
        self.agente.estado_conversacion = EstadoConversacion.ENCARGADO_NO_ESTA
        result = self.agente._try_narrow_prompt_792("no está")
        self.assertIsNotNone(result)
        self.assertIn("WhatsApp", result)
        self.assertIn("correo", result)

    def test_contacto_capturado(self):
        """CONTACTO_CAPTURADO → confirmar envio + despedida."""
        self.agente.estado_conversacion = EstadoConversacion.CONTACTO_CAPTURADO
        result = self.agente._try_narrow_prompt_792("listo")
        self.assertIsNotNone(result)
        self.assertIn("catalogo", result)
        self.assertIn("2 horas", result)

    def test_dictando_numero(self):
        """DICTANDO_NUMERO → acknowledgment silencioso."""
        self.agente.estado_conversacion = EstadoConversacion.DICTANDO_NUMERO
        result = self.agente._try_narrow_prompt_792("33 12 34")
        self.assertIsNotNone(result)
        self.assertIn("Aja", result)

    def test_dictando_correo(self):
        """DICTANDO_CORREO → acknowledgment silencioso."""
        self.agente.estado_conversacion = EstadoConversacion.DICTANDO_CORREO
        result = self.agente._try_narrow_prompt_792("arroba gmail")
        self.assertIsNotNone(result)
        self.assertIn("Aja", result)

    def test_despedida(self):
        """DESPEDIDA → agradecimiento."""
        self.agente.estado_conversacion = EstadoConversacion.DESPEDIDA
        result = self.agente._try_narrow_prompt_792("hasta luego")
        self.assertIsNotNone(result)
        self.assertIn("agradezco", result)

    def test_pidiendo_whatsapp(self):
        """PIDIENDO_WHATSAPP → pedir numero."""
        self.agente.estado_conversacion = EstadoConversacion.PIDIENDO_WHATSAPP
        result = self.agente._try_narrow_prompt_792("si le doy mi whats")
        self.assertIsNotNone(result)
        self.assertIn("WhatsApp", result)

    def test_pidiendo_correo(self):
        """PIDIENDO_CORREO → pedir correo."""
        self.agente.estado_conversacion = EstadoConversacion.PIDIENDO_CORREO
        result = self.agente._try_narrow_prompt_792("si le doy mi correo")
        self.assertIsNotNone(result)
        self.assertIn("correo", result)

    def test_presentacion(self):
        """PRESENTACION → re-pitch con encargado."""
        self.agente.estado_conversacion = EstadoConversacion.PRESENTACION
        result = self.agente._try_narrow_prompt_792("ajá")
        self.assertIsNotNone(result)
        self.assertIn("NIOVAL", result)
        self.assertIn("encargado", result)

    def test_buscando_encargado(self):
        """BUSCANDO_ENCARGADO → preguntar encargado."""
        self.agente.estado_conversacion = EstadoConversacion.BUSCANDO_ENCARGADO
        result = self.agente._try_narrow_prompt_792("pues no sé")
        self.assertIsNotNone(result)
        self.assertIn("encargado", result.lower())


# ============================================================
# Test 2: Unmapped estados return None
# ============================================================

class TestFix792Fallthrough(unittest.TestCase):
    """Unmapped estados return None → GPT full fallback."""

    def setUp(self):
        self.agente = _make_agente()

    def test_inicio_returns_none(self):
        """INICIO → None (GPT full)."""
        self.agente.estado_conversacion = EstadoConversacion.INICIO
        result = self.agente._try_narrow_prompt_792("hola")
        self.assertIsNone(result)

    def test_conversacion_normal_returns_none(self):
        """CONVERSACION_NORMAL → None (GPT full)."""
        self.agente.estado_conversacion = EstadoConversacion.CONVERSACION_NORMAL
        result = self.agente._try_narrow_prompt_792("pues mire")
        self.assertIsNone(result)

    def test_esperando_transferencia_returns_none(self):
        """ESPERANDO_TRANSFERENCIA → None (GPT full)."""
        self.agente.estado_conversacion = EstadoConversacion.ESPERANDO_TRANSFERENCIA
        result = self.agente._try_narrow_prompt_792("un momento")
        self.assertIsNone(result)

    def test_ofreciendo_contacto_returns_none(self):
        """OFRECIENDO_CONTACTO_BRUCE → None (GPT full)."""
        self.agente.estado_conversacion = EstadoConversacion.OFRECIENDO_CONTACTO_BRUCE
        result = self.agente._try_narrow_prompt_792("ajá")
        self.assertIsNone(result)


# ============================================================
# Test 3: Method exists and code integration
# ============================================================

class TestFix792CodeExists(unittest.TestCase):
    """FIX 792 code must exist in agente_ventas.py."""

    def test_method_exists(self):
        """AgenteVentas must have _try_narrow_prompt_792 method."""
        self.assertTrue(hasattr(AgenteVentas, '_try_narrow_prompt_792'))

    def test_fix_792_in_source(self):
        """FIX 792 comment must appear in agente_ventas.py."""
        agent_path = os.path.join(os.path.dirname(__file__), '..', 'agente_ventas.py')
        with open(agent_path, 'r', encoding='utf-8') as f:
            source = f.read()
        self.assertIn('FIX 792', source)
        self.assertIn('_try_narrow_prompt_792', source)

    def test_fix_792_before_gpt_call(self):
        """FIX 792 call must appear BEFORE the GPT full call in procesar_respuesta."""
        agent_path = os.path.join(os.path.dirname(__file__), '..', 'agente_ventas.py')
        with open(agent_path, 'r', encoding='utf-8') as f:
            source = f.read()
        # FIX 792 call point
        pos_792 = source.find('_try_narrow_prompt_792(respuesta_cliente)')
        # GPT full call (FIX 819: ahora usa llm_client adapter)
        pos_gpt = source.find('llm_client.chat_completion(')
        if pos_gpt < 0:
            pos_gpt = source.find('openai_client.chat.completions.create')
        self.assertGreater(pos_792, 0, "FIX 792 call not found")
        self.assertGreater(pos_gpt, 0, "GPT full call not found")
        self.assertLess(pos_792, pos_gpt,
                        "FIX 792 must appear BEFORE GPT full call")


if __name__ == '__main__':
    unittest.main()
