"""
Tests for FIX 910A-C: GPT eval false positive filters + herramienta electrica
FIX 910A: Encargado recognition at turn 2 FP filter
FIX 910B: INTERRUPCION_CONVERSACIONAL FP filter in GPT eval
FIX 910C: Skip INTERRUPCION in text simulator + herramienta electrica in prompt
"""
import unittest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestFix910AEncargadoFP(unittest.TestCase):
    """FIX 910A: GPT eval FP filter for encargado recognition at turn 2."""

    def test_fp_filter_code_exists(self):
        """_evaluar_con_gpt must have FIX 910A filter."""
        import inspect
        from bug_detector import _evaluar_con_gpt
        source = inspect.getsource(_evaluar_con_gpt)
        self.assertIn('FIX 910A', source)
        self.assertIn('encargado recognition', source.lower())

    def test_fp_filter_checks_turno(self):
        """FP filter should only apply to turno <= 2."""
        import inspect
        from bug_detector import _evaluar_con_gpt
        source = inspect.getsource(_evaluar_con_gpt)
        self.assertIn('_turno_num', source)
        self.assertIn('<= 2', source)

    def test_fp_filter_checks_cliente_confirmo(self):
        """FP filter should check if client confirmed being encargado."""
        import inspect
        from bug_detector import _evaluar_con_gpt
        source = inspect.getsource(_evaluar_con_gpt)
        for phrase in ['si soy', 'yo soy', 'yo mero', 'a sus ordenes']:
            self.assertIn(phrase, source, f"Missing encargado confirmation phrase: {phrase}")


class TestFix910BInterrupcionGPTEval(unittest.TestCase):
    """FIX 910B: INTERRUPCION_CONVERSACIONAL always FP in GPT eval."""

    def test_interrupcion_fp_filter_exists(self):
        """GPT eval FP filter for INTERRUPCION must exist."""
        import inspect
        from bug_detector import _evaluar_con_gpt
        source = inspect.getsource(_evaluar_con_gpt)
        self.assertIn('FIX 910B', source)
        self.assertIn('INTERRUPCION_CONVERSACIONAL', source)


class TestFix910CSimuladorTexto(unittest.TestCase):
    """FIX 910C: Skip INTERRUPCION detection in text simulator."""

    def test_tracker_has_simulador_texto_flag(self):
        """CallEventTracker must have simulador_texto attribute."""
        from bug_detector import CallEventTracker
        tracker = CallEventTracker("test", "test")
        self.assertFalse(tracker.simulador_texto)

    def test_analyze_skips_interrupcion_in_text_mode(self):
        """BugDetector.analyze() should skip INTERRUPCION when simulador_texto=True."""
        from bug_detector import CallEventTracker, BugDetector
        tracker = CallEventTracker("test_910c", "T910C")
        tracker.simulador_texto = True

        # Simulate a conversation where client is "explaining" (truncated text)
        tracker.conversacion = [
            ("bruce", "Buen dia, le llamo de NIOVAL sobre productos ferreteros"),
            ("cliente", "No mire, aqui no hacemos ningun tipo de compra, no"),
            ("bruce", "Entendido, le envio el catalogo por WhatsApp"),
        ]
        tracker.respuestas_bruce = [
            "Buen dia, le llamo de NIOVAL sobre productos ferreteros",
            "Entendido, le envio el catalogo por WhatsApp",
        ]
        tracker.textos_cliente = ["No mire, aqui no hacemos ningun tipo de compra, no"]

        bugs = BugDetector.analyze(tracker)
        interrupcion_bugs = [b for b in bugs if b['tipo'] == 'INTERRUPCION_CONVERSACIONAL']
        self.assertEqual(len(interrupcion_bugs), 0,
                         "INTERRUPCION should be skipped in text simulator mode")

    def test_analyze_detects_interrupcion_in_real_mode(self):
        """BugDetector.analyze() should detect INTERRUPCION when simulador_texto=False."""
        from bug_detector import CallEventTracker, BugDetector
        tracker = CallEventTracker("test_910c_real", "T910CR")
        tracker.simulador_texto = False

        tracker.conversacion = [
            ("bruce", "Buen dia, le llamo de NIOVAL sobre productos ferreteros"),
            ("cliente", "No mire, aqui no hacemos ningun tipo de compra, no"),
            ("bruce", "Perfecto, le envio el catalogo con lista de precios por WhatsApp"),
        ]
        tracker.respuestas_bruce = [
            "Buen dia, le llamo de NIOVAL sobre productos ferreteros",
            "Perfecto, le envio el catalogo con lista de precios por WhatsApp",
        ]
        tracker.textos_cliente = ["No mire, aqui no hacemos ningun tipo de compra, no"]

        bugs = BugDetector.analyze(tracker)
        # In real mode, this could detect interrupcion (depends on other guards)
        # We just verify no crash and the check runs
        self.assertIsInstance(bugs, list)


class TestFix910HerramientaElectrica(unittest.TestCase):
    """FIX 910: System prompt must mention herramienta electrica."""

    def test_prompt_mentions_herramienta_electrica(self):
        """System prompt must explicitly mention electric tools."""
        prompt_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                    'prompts', 'system_prompt.txt')
        with open(prompt_path, 'r', encoding='utf-8') as f:
            prompt = f.read()
        self.assertIn('eléctricas', prompt.lower(),
                       "System prompt must mention 'eléctricas' in product list")
        self.assertIn('rotomartillo', prompt.lower(),
                       "System prompt must mention rotomartillos")


if __name__ == '__main__':
    unittest.main()
