"""
Tests FIX 722-723: FIX 664B refinement + DEGRADACION_TTS detector.

FIX 722: Restringir CASO 2 de _es_comportamiento_correcto() para no skipear con decisores
FIX 723: Detector DEGRADACION_TTS para fillers consecutivos
"""
import sys
import os
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from bug_detector import (
    _es_comportamiento_correcto, ContentAnalyzer, CallEventTracker
)


class TestFix722ComportamientoCorrectoDecisor(unittest.TestCase):
    """FIX 722: No skipear GPT eval si cliente menciona rol de decisor."""

    def test_corporativo_no_skipea(self):
        """Cliente dice 'corporativo' → NO skipear GPT eval."""
        conv = [
            ("bruce", "¿Se encuentra el encargado de compras?"),
            ("cliente", "Esto es corporativo de Cemex, no manejamos eso"),
            ("bruce", "¿Me podría dar su WhatsApp?"),
        ]
        result = _es_comportamiento_correcto(conv)
        self.assertFalse(result, "No debe skipear GPT eval cuando cliente menciona 'corporativo'")

    def test_gerente_no_skipea(self):
        """Cliente dice 'gerente' → NO skipear GPT eval."""
        conv = [
            ("bruce", "¿Se encuentra el encargado de compras?"),
            ("cliente", "Soy el gerente, ¿qué necesita?"),
            ("bruce", "¿Me podría dar su WhatsApp para enviarle el catálogo?"),
        ]
        result = _es_comportamiento_correcto(conv)
        self.assertFalse(result)

    def test_dueno_no_skipea(self):
        """Cliente dice 'dueño' → NO skipear GPT eval."""
        conv = [
            ("bruce", "¿Se encuentra el encargado de compras?"),
            ("cliente", "Yo soy el dueño, dígame"),
            ("bruce", "¿Me podría dejar recado con el encargado?"),
        ]
        result = _es_comportamiento_correcto(conv)
        self.assertFalse(result)

    def test_encargado_no_skipea(self):
        """Cliente dice 'encargado' → NO skipear GPT eval."""
        conv = [
            ("bruce", "¿Se encuentra el encargado de compras?"),
            ("cliente", "Yo soy el encargado, ¿qué me ofrece?"),
            ("bruce", "¿Me podría dar el WhatsApp del encargado?"),
        ]
        result = _es_comportamiento_correcto(conv)
        self.assertFalse(result)

    def test_jefe_no_skipea(self):
        """Cliente dice 'jefe' → NO skipear GPT eval."""
        conv = [
            ("bruce", "¿Se encuentra el encargado de compras?"),
            ("cliente", "Yo soy el jefe de la tienda"),
            ("bruce", "¿Me podría dar su WhatsApp?"),
        ]
        result = _es_comportamiento_correcto(conv)
        self.assertFalse(result)

    def test_sin_decisor_puede_skipear(self):
        """Sin palabras de decisor + pregunta no respondida → puede skipear."""
        conv = [
            ("bruce", "¿Se encuentra el encargado de compras?"),
            ("cliente", "No, no está ahorita"),
            ("bruce", "¿Me podría dar el WhatsApp del encargado?"),
        ]
        # Esto PUEDE dar True si cumple CASO 2 original
        # Lo importante es que NO se bloquea por FIX 722
        result = _es_comportamiento_correcto(conv)
        # El resultado depende de la lógica interna, solo verificamos que no crashea
        self.assertIsInstance(result, bool)

    def test_yo_hago_las_compras_no_skipea(self):
        """'Yo hago las compras' → decisor → NO skipear."""
        conv = [
            ("bruce", "¿Se encuentra el encargado de compras?"),
            ("cliente", "Yo hago las compras aquí"),
            ("bruce", "¿Le podría dejar recado al encargado?"),
        ]
        result = _es_comportamiento_correcto(conv)
        self.assertFalse(result)


class TestFix722CasosCasoUnoNoAfectado(unittest.TestCase):
    """FIX 722: CASO 1 (verificación conexión) NO debe afectarse."""

    def test_bueno_pregunta_sigue_funcionando(self):
        """CASO 1: Cliente dice '¿bueno?' → skip SIGUE funcionando."""
        conv = [
            ("bruce", "¿Me podría dar su WhatsApp para enviarle el catálogo?"),
            ("cliente", "¿bueno?"),
            ("bruce", "¿Me podría dar su WhatsApp para enviarle el catálogo?"),
        ]
        result = _es_comportamiento_correcto(conv)
        self.assertTrue(result, "CASO 1 debe seguir funcionando sin cambios")

    def test_ivr_sigue_funcionando(self):
        """CASO 3: IVR → skip SIGUE funcionando."""
        conv = [
            ("bruce", "Buenos días"),
            ("cliente", "Para ventas marque 1"),
            ("bruce", "Parece ser un sistema automatizado"),
        ]
        result = _es_comportamiento_correcto(conv)
        self.assertTrue(result, "CASO 3 debe seguir funcionando sin cambios")


class TestFix723DegradacionTTS(unittest.TestCase):
    """FIX 723: Detector DEGRADACION_TTS."""

    def test_2_fillers_es_degradacion(self):
        """2+ fillers = DEGRADACION_TTS."""
        tracker = CallEventTracker("test_sid", "BRUCE_TEST")
        tracker.filler_162a_count = 2
        bugs = ContentAnalyzer._check_degradacion_servicio(tracker)
        self.assertEqual(len(bugs), 1)
        self.assertEqual(bugs[0]["tipo"], "DEGRADACION_TTS")
        self.assertEqual(bugs[0]["severidad"], "CRITICO")

    def test_4_fillers_es_degradacion(self):
        """4 fillers = DEGRADACION_TTS."""
        tracker = CallEventTracker("test_sid", "BRUCE_TEST")
        tracker.filler_162a_count = 4
        bugs = ContentAnalyzer._check_degradacion_servicio(tracker)
        self.assertEqual(len(bugs), 1)
        self.assertIn("4x", bugs[0]["detalle"])

    def test_1_filler_no_es_degradacion(self):
        """1 filler = no degradación (ya cubierto por RESPUESTA_FILLER_INCOHERENTE)."""
        tracker = CallEventTracker("test_sid", "BRUCE_TEST")
        tracker.filler_162a_count = 1
        bugs = ContentAnalyzer._check_degradacion_servicio(tracker)
        self.assertEqual(len(bugs), 0)

    def test_0_fillers_sin_bug(self):
        """0 fillers = sin bug."""
        tracker = CallEventTracker("test_sid", "BRUCE_TEST")
        tracker.filler_162a_count = 0
        bugs = ContentAnalyzer._check_degradacion_servicio(tracker)
        self.assertEqual(len(bugs), 0)


class TestFix723EnBugDetector(unittest.TestCase):
    """FIX 723: Verificar que DEGRADACION_TTS aparece en BugDetector.analyze()."""

    def test_degradacion_en_analyze(self):
        """BugDetector.analyze() debe detectar DEGRADACION_TTS con 2+ fillers."""
        from bug_detector import BugDetector
        tracker = CallEventTracker("test_sid", "BRUCE_TEST")
        tracker.filler_162a_count = 3
        tracker.conversacion = [
            ("bruce", "Buenos días"),
            ("cliente", "Hola"),
        ]
        tracker.respuestas_bruce = ["Buenos días"]
        bugs = BugDetector.analyze(tracker)
        tipos = [b["tipo"] for b in bugs]
        self.assertIn("DEGRADACION_TTS", tipos)
        # También debe tener RESPUESTA_FILLER_INCOHERENTE (FIX 715)
        self.assertIn("RESPUESTA_FILLER_INCOHERENTE", tipos)


if __name__ == "__main__":
    unittest.main()
