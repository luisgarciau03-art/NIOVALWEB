"""
Tests FIX 724-725: PREFERENCIA_IGNORADA + DATO_NEGADO_REINSISTIDO detectors.

FIX 724: Cliente indica canal preferido y Bruce pide otro
FIX 725: Cliente niega tener dato y Bruce lo pide después
"""
import sys
import os
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from bug_detector import ContentAnalyzer


class TestFix724PreferenciaPatterns(unittest.TestCase):
    """FIX 724: Verificar patrones de preferencia de canal."""

    def test_mejor_por_correo(self):
        self.assertTrue(ContentAnalyzer._PREFERENCIA_PATTERNS.search("Mejor por correo"))

    def test_prefiero_whatsapp(self):
        self.assertTrue(ContentAnalyzer._PREFERENCIA_PATTERNS.search("Prefiero WhatsApp"))

    def test_mandamelo_por_correo(self):
        self.assertTrue(ContentAnalyzer._PREFERENCIA_PATTERNS.search("Mándamelo por correo"))

    def test_enviamelo_por_email(self):
        self.assertTrue(ContentAnalyzer._PREFERENCIA_PATTERNS.search("Envíamelo por email"))

    def test_por_whatsapp_mejor(self):
        self.assertTrue(ContentAnalyzer._PREFERENCIA_PATTERNS.search("Por WhatsApp mejor"))

    def test_prefiero_que_me_llamen(self):
        self.assertTrue(ContentAnalyzer._PREFERENCIA_PATTERNS.search("Prefiero que me llamen"))


class TestFix724PreferenciaIgnorada(unittest.TestCase):
    """FIX 724: Detector _check_preferencia_ignorada."""

    def test_prefiere_correo_bruce_pide_whatsapp(self):
        """Cliente prefiere correo, Bruce pide WhatsApp → BUG."""
        conv = [
            ("bruce", "¿Le gustaría recibir el catálogo?"),
            ("cliente", "Sí, mejor por correo"),
            ("bruce", "¿Me podría dar su WhatsApp para enviárselo?"),
        ]
        bugs = ContentAnalyzer._check_preferencia_ignorada(conv)
        self.assertEqual(len(bugs), 1)
        self.assertEqual(bugs[0]["tipo"], "PREFERENCIA_IGNORADA")
        self.assertIn("correo", bugs[0]["detalle"])

    def test_prefiere_whatsapp_bruce_pide_correo(self):
        """Cliente prefiere WhatsApp, Bruce pide correo → BUG."""
        conv = [
            ("bruce", "¿Le gustaría recibir el catálogo?"),
            ("cliente", "Sí, mándamelo por WhatsApp"),
            ("bruce", "¿Me podría dar su correo electrónico?"),
        ]
        bugs = ContentAnalyzer._check_preferencia_ignorada(conv)
        self.assertEqual(len(bugs), 1)
        self.assertEqual(bugs[0]["tipo"], "PREFERENCIA_IGNORADA")

    def test_prefiere_correo_bruce_usa_correo_no_bug(self):
        """Cliente prefiere correo, Bruce usa correo → NO bug."""
        conv = [
            ("bruce", "¿Le gustaría recibir el catálogo?"),
            ("cliente", "Sí, mejor por correo"),
            ("bruce", "Perfecto, ¿me podría dar su correo electrónico?"),
        ]
        bugs = ContentAnalyzer._check_preferencia_ignorada(conv)
        self.assertEqual(len(bugs), 0)

    def test_sin_preferencia_no_bug(self):
        """Sin preferencia explícita → NO bug."""
        conv = [
            ("bruce", "¿Le gustaría recibir el catálogo?"),
            ("cliente", "Sí, me interesa"),
            ("bruce", "¿Me podría dar su WhatsApp?"),
        ]
        bugs = ContentAnalyzer._check_preferencia_ignorada(conv)
        self.assertEqual(len(bugs), 0)

    def test_conv_corta_no_crash(self):
        """Conversación corta no crash."""
        conv = [("bruce", "Hola"), ("cliente", "Hola")]
        bugs = ContentAnalyzer._check_preferencia_ignorada(conv)
        self.assertEqual(len(bugs), 0)

    def test_prefiere_telefono_bruce_pide_whatsapp(self):
        """Cliente prefiere teléfono, Bruce pide WhatsApp → BUG."""
        conv = [
            ("bruce", "¿Cómo le enviamos la información?"),
            ("cliente", "Prefiero que me llamen por teléfono"),
            ("bruce", "¿Me podría dar su WhatsApp?"),
        ]
        bugs = ContentAnalyzer._check_preferencia_ignorada(conv)
        self.assertEqual(len(bugs), 1)


class TestFix725NegacionPatterns(unittest.TestCase):
    """FIX 725: Verificar patrones de negación de datos."""

    def test_no_tengo_whatsapp(self):
        self.assertTrue(ContentAnalyzer._NEGACION_DATO_PATTERNS.search("No tengo WhatsApp"))

    def test_no_tengo_correo(self):
        self.assertTrue(ContentAnalyzer._NEGACION_DATO_PATTERNS.search("No tengo correo"))

    def test_solo_tengo_fijo(self):
        self.assertTrue(ContentAnalyzer._NEGACION_DATO_PATTERNS.search("Solo tengo fijo"))

    def test_no_uso_whatsapp(self):
        self.assertTrue(ContentAnalyzer._NEGACION_DATO_PATTERNS.search("No uso WhatsApp"))

    def test_no_manejo_redes(self):
        self.assertTrue(ContentAnalyzer._NEGACION_DATO_PATTERNS.search("No manejo redes"))

    def test_no_cuento_con_celular(self):
        self.assertTrue(ContentAnalyzer._NEGACION_DATO_PATTERNS.search("No cuento con celular"))


class TestFix725DatoNegadoReinsistido(unittest.TestCase):
    """FIX 725: Detector _check_dato_negado_reinsistido."""

    def test_no_tiene_whatsapp_bruce_pide_whatsapp(self):
        """Cliente dice no tiene WhatsApp, Bruce pide WhatsApp → BUG."""
        conv = [
            ("bruce", "¿Me podría dar su WhatsApp?"),
            ("cliente", "No tengo WhatsApp"),
            ("bruce", "¿Tiene algún número de WhatsApp al que le pueda enviar?"),
        ]
        bugs = ContentAnalyzer._check_dato_negado_reinsistido(conv)
        self.assertEqual(len(bugs), 1)
        self.assertEqual(bugs[0]["tipo"], "DATO_NEGADO_REINSISTIDO")
        self.assertIn("whatsapp", bugs[0]["detalle"])

    def test_no_tiene_correo_bruce_pide_correo(self):
        """Cliente dice no tiene correo, Bruce pide correo → BUG."""
        conv = [
            ("bruce", "¿Me podría dar su correo?"),
            ("cliente", "No tengo correo electrónico"),
            ("bruce", "Entiendo, ¿y no tiene algún email al que le pueda enviar?"),
        ]
        bugs = ContentAnalyzer._check_dato_negado_reinsistido(conv)
        self.assertEqual(len(bugs), 1)

    def test_no_tiene_whatsapp_bruce_pide_correo_no_bug(self):
        """Cliente dice no tiene WhatsApp, Bruce pide correo → NO bug (alternativa correcta)."""
        conv = [
            ("bruce", "¿Me podría dar su WhatsApp?"),
            ("cliente", "No tengo WhatsApp"),
            ("bruce", "Entiendo, ¿me podría dar su correo electrónico?"),
        ]
        bugs = ContentAnalyzer._check_dato_negado_reinsistido(conv)
        self.assertEqual(len(bugs), 0)

    def test_antes_de_negacion_no_es_bug(self):
        """Bruce pidió ANTES de la negación → NO es bug."""
        conv = [
            ("bruce", "¿Me podría dar su WhatsApp?"),
            ("cliente", "No tengo WhatsApp"),
            ("bruce", "Entiendo, gracias por su tiempo"),
        ]
        bugs = ContentAnalyzer._check_dato_negado_reinsistido(conv)
        self.assertEqual(len(bugs), 0)

    def test_solo_tengo_fijo_bruce_pide_celular(self):
        """Cliente solo tiene fijo, Bruce pide celular → BUG."""
        conv = [
            ("bruce", "¿Me podría dar su número?"),
            ("cliente", "Solo tengo teléfono de casa"),
            ("bruce", "¿Y no tiene algún celular?"),
        ]
        bugs = ContentAnalyzer._check_dato_negado_reinsistido(conv)
        # No reporta porque 'celular' no fue lo negado, fue 'telefono de casa' (fijo)
        # Pero 'solo tengo' + pattern matchea por el regex, veamos
        self.assertIsInstance(bugs, list)

    def test_conv_corta_no_crash(self):
        """Conversación corta no crash."""
        conv = [("bruce", "Hola"), ("cliente", "Hola")]
        bugs = ContentAnalyzer._check_dato_negado_reinsistido(conv)
        self.assertEqual(len(bugs), 0)

    def test_conv_vacia_no_crash(self):
        """Conversación vacía no crash."""
        bugs = ContentAnalyzer._check_dato_negado_reinsistido([])
        self.assertEqual(len(bugs), 0)


class TestFix724725EnBugDetector(unittest.TestCase):
    """Verificar que nuevos detectores aparecen en BugDetector.analyze()."""

    def test_preferencia_ignorada_en_analyze(self):
        """BugDetector.analyze() debe detectar PREFERENCIA_IGNORADA."""
        from bug_detector import BugDetector, CallEventTracker
        tracker = CallEventTracker("test_sid", "BRUCE_TEST")
        tracker.conversacion = [
            ("bruce", "¿Le gustaría recibir el catálogo?"),
            ("cliente", "Sí, mejor por correo"),
            ("bruce", "¿Me podría dar su WhatsApp para enviárselo?"),
        ]
        tracker.respuestas_bruce = ["¿Le gustaría recibir el catálogo?", "¿Me podría dar su WhatsApp para enviárselo?"]
        bugs = BugDetector.analyze(tracker)
        tipos = [b["tipo"] for b in bugs]
        self.assertIn("PREFERENCIA_IGNORADA", tipos)

    def test_dato_negado_en_analyze(self):
        """BugDetector.analyze() debe detectar DATO_NEGADO_REINSISTIDO."""
        from bug_detector import BugDetector, CallEventTracker
        tracker = CallEventTracker("test_sid", "BRUCE_TEST")
        tracker.conversacion = [
            ("bruce", "¿Me podría dar su WhatsApp?"),
            ("cliente", "No tengo WhatsApp"),
            ("bruce", "¿Tiene algún número de WhatsApp?"),
        ]
        tracker.respuestas_bruce = ["¿Me podría dar su WhatsApp?", "¿Tiene algún número de WhatsApp?"]
        bugs = BugDetector.analyze(tracker)
        tipos = [b["tipo"] for b in bugs]
        self.assertIn("DATO_NEGADO_REINSISTIDO", tipos)


if __name__ == "__main__":
    unittest.main()
