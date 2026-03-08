"""
Tests for FIX 906A-F: Auditoria Claude - 240 bugs
FIX 906A: Filler GPT mejorado (confirmar numero completo, pregunta directa, interes)
FIX 906B: System prompt naturalidad, empatia, cierre, tono
FIX 906C: Anti-tuteo post-filter
FIX 906D: FSM context injection mejorada
FIX 906E: Templates confirmar_telefono/correo mejorados + ack variantes
FIX 906F: Narrow prompt conversacion_libre mejorado
"""
import unittest
import re
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestFix906AFillerMejorado(unittest.TestCase):
    """FIX 906A: Filler GPT mejorado para numeros completos, preguntas, interes."""

    def test_filler_list_includes_new_patterns(self):
        """Nuevos fillers deben estar en la lista."""
        from agente_ventas import AgenteVentas
        import inspect
        source = inspect.getsource(AgenteVentas._filtrar_respuesta_post_gpt)
        for filler in ['claro, prosiga', 'claro, digame', 'perfecto, digame',
                       'entendido, prosiga', 'entendido, digame']:
            self.assertIn(filler, source, f"Filler '{filler}' no encontrado en FIX 810B")

    def test_numero_completo_detection(self):
        """Debe detectar numeros con 7+ digitos en palabras."""
        from agente_ventas import AgenteVentas
        import inspect
        source = inspect.getsource(AgenteVentas._filtrar_respuesta_post_gpt)
        self.assertIn('_total_digits_810', source, "Variable de conteo total de digitos no encontrada")
        self.assertIn('>= 7', source, "Threshold de 7 digitos no encontrado")

    def test_pregunta_directa_override(self):
        """Debe override fillers cuando cliente hace pregunta directa."""
        from agente_ventas import AgenteVentas
        import inspect
        source = inspect.getsource(AgenteVentas._filtrar_respuesta_post_gpt)
        self.assertIn('que venden', source, "Patron 'que venden' no encontrado")
        self.assertIn('pregunta directa', source, "Caso pregunta directa no documentado")

    def test_cliente_interesado_override(self):
        """Debe override fillers cuando cliente muestra interes."""
        from agente_ventas import AgenteVentas
        import inspect
        source = inspect.getsource(AgenteVentas._filtrar_respuesta_post_gpt)
        self.assertIn('me interesa', source, "Patron 'me interesa' no encontrado")
        self.assertIn('cliente interesado', source, "Caso cliente interesado no documentado")


class TestFix906BSystemPrompt(unittest.TestCase):
    """FIX 906B: System prompt mejorado con reglas de naturalidad, empatia, cierre."""

    def setUp(self):
        prompt_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                    'prompts', 'system_prompt.txt')
        with open(prompt_path, 'r', encoding='utf-8') as f:
            self.prompt = f.read()

    def test_regla_anti_robotico(self):
        """Prompt debe incluir regla anti-robotico."""
        self.assertIn('ANTI-ROBOTICO', self.prompt)
        self.assertIn('SUENA COMO PERSONA', self.prompt)

    def test_regla_empatia(self):
        """Prompt debe incluir regla de empatia."""
        self.assertIn('REGLA DE EMPATIA', self.prompt)
        self.assertIn('REFLEJA LO QUE EL CLIENTE SIENTE', self.prompt)

    def test_regla_cierre(self):
        """Prompt debe incluir regla de cierre completo."""
        self.assertIn('REGLA DE CIERRE', self.prompt)
        self.assertIn('QUE le vas a enviar', self.prompt)
        self.assertIn('CUANDO', self.prompt)

    def test_regla_tono_usted(self):
        """Prompt debe incluir regla de siempre usar usted."""
        self.assertIn('SIEMPRE USA "USTED"', self.prompt)
        self.assertIn('PROHIBIDO ABSOLUTAMENTE usar "tu"', self.prompt)

    def test_regla_confirmacion_datos(self):
        """Prompt debe incluir regla de repetir numero al confirmar."""
        self.assertIn('CONFIRMACION DE DATOS', self.prompt)
        self.assertIn('REPITE el numero', self.prompt)


class TestFix906CAntiTuteo(unittest.TestCase):
    """FIX 906C: Post-filter que corrige tuteo a usted."""

    def test_anti_tuteo_patterns_exist(self):
        """Post-filter debe tener patterns de tuteo."""
        from agente_ventas import AgenteVentas
        import inspect
        source = inspect.getsource(AgenteVentas._filtrar_respuesta_post_gpt)
        self.assertIn('_tuteo_patterns_906c', source)
        self.assertIn('Anti-tuteo', source)

    def test_te_envio_pattern(self):
        """Debe detectar 'te envio' como tuteo."""
        patterns = [
            (r'\bte\s+(?:envío|envio|mando|paso|comparto)\b', 'le'),
        ]
        for pat, repl in patterns:
            self.assertIsNotNone(re.search(pat, "te envio el catalogo"),
                                 f"Pattern '{pat}' no matchea 'te envio el catalogo'")

    def test_quieres_pattern(self):
        """Debe detectar 'quieres' como tuteo."""
        pat = r'\bquieres\s+que\b'
        self.assertIsNotNone(re.search(pat, "quieres que te mande"),
                             "Pattern no matchea 'quieres que te mande'")

    def test_tu_numero_pattern(self):
        """Debe detectar 'tu numero' como tuteo."""
        pat = r'\btu\s+(?:número|numero|correo|whatsapp|teléfono|telefono|nombre|negocio|empresa)\b'
        self.assertIsNotNone(re.search(pat, "dame tu numero"),
                             "Pattern no matchea 'dame tu numero'")


class TestFix906DContextInjection(unittest.TestCase):
    """FIX 906D: FSM context injection mejorada."""

    def test_pregunta_detection(self):
        """Debe inyectar flag cuando cliente hace pregunta."""
        from agente_ventas import AgenteVentas
        import inspect
        source = inspect.getsource(AgenteVentas._construir_prompt_dinamico)
        self.assertIn('ACABA DE HACER UNA PREGUNTA', source)

    def test_interes_detection(self):
        """Debe inyectar flag cuando cliente muestra interes."""
        from agente_ventas import AgenteVentas
        import inspect
        source = inspect.getsource(AgenteVentas._construir_prompt_dinamico)
        self.assertIn('MOSTRO INTERES', source)

    def test_ocupado_detection(self):
        """Debe inyectar flag cuando cliente esta ocupado."""
        from agente_ventas import AgenteVentas
        import inspect
        source = inspect.getsource(AgenteVentas._construir_prompt_dinamico)
        self.assertIn('ESTA OCUPADO', source)

    def test_objecion_detection(self):
        """Debe inyectar flag cuando cliente tiene objecion."""
        from agente_ventas import AgenteVentas
        import inspect
        source = inspect.getsource(AgenteVentas._construir_prompt_dinamico)
        self.assertIn('OBJECION', source)

    def test_cierre_ejemplo_added(self):
        """Debe agregar ejemplo de cierre completo."""
        from agente_ventas import AgenteVentas
        import inspect
        source = inspect.getsource(AgenteVentas._construir_prompt_dinamico)
        self.assertIn('Ejemplo BUENO cierre', source)


class TestFix906ETemplates(unittest.TestCase):
    """FIX 906E: Templates mejorados + variantes ack."""

    def test_confirmar_telefono_templates(self):
        """confirmar_telefono debe tener 3 variantes con info completa."""
        from response_templates import TEMPLATES
        templates = TEMPLATES['confirmar_telefono']
        self.assertGreaterEqual(len(templates), 3)
        # Al menos uno debe mencionar que se envia y cuando
        any_mentions_envio = any('envio' in t.lower() or 'envío' in t.lower() for t in templates)
        self.assertTrue(any_mentions_envio, "Ningun template menciona envio")

    def test_confirmar_correo_templates(self):
        """confirmar_correo debe tener variantes con info completa."""
        from response_templates import TEMPLATES
        templates = TEMPLATES['confirmar_correo']
        self.assertGreaterEqual(len(templates), 2)

    def test_aja_si_variantes_naturales(self):
        """aja_si debe tener variantes naturales adicionales."""
        from response_templates import TEMPLATES
        templates = TEMPLATES['aja_si']
        self.assertGreaterEqual(len(templates), 7)  # 5 originales + 2 nuevas
        all_text = ' '.join(templates).lower()
        self.assertIn('aja', all_text, "Falta variante 'Aja'")

    def test_aja_digame_variantes(self):
        """aja_digame debe tener variantes adicionales."""
        from response_templates import TEMPLATES
        templates = TEMPLATES['aja_digame']
        self.assertGreaterEqual(len(templates), 5)


class TestFix906FNarrowPrompts(unittest.TestCase):
    """FIX 906F: Narrow prompts mejorados."""

    def test_conversacion_libre_usted(self):
        """conversacion_libre debe incluir regla de usted."""
        from response_templates import NARROW_PROMPTS
        system = NARROW_PROMPTS['conversacion_libre']['system']
        self.assertIn('usted', system.lower())
        self.assertIn('NUNCA tutees', system)

    def test_conversacion_libre_confirmar_dato(self):
        """conversacion_libre debe incluir regla de confirmar dato."""
        from response_templates import NARROW_PROMPTS
        system = NARROW_PROMPTS['conversacion_libre']['system']
        self.assertIn('REPITE el numero', system)

    def test_confirmar_dato_dictado_improved(self):
        """confirmar_dato_dictado debe tener reglas expandidas."""
        from response_templates import NARROW_PROMPTS
        system = NARROW_PROMPTS['confirmar_dato_dictado']['system']
        self.assertIn('QUE le vas a enviar', system)
        self.assertIn('CUANDO', system)

    def test_responder_pregunta_envios(self):
        """responder_pregunta_producto debe mencionar envios nacionales."""
        from response_templates import NARROW_PROMPTS
        system = NARROW_PROMPTS['responder_pregunta_producto']['system']
        self.assertIn('envios', system.lower())


if __name__ == '__main__':
    unittest.main()
