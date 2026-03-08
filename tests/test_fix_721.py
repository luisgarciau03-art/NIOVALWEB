"""
Tests FIX 721: TRANSFER_IGNORADA detector.

Detecta cuando cliente pide esperar/transferir y Bruce sigue vendiendo.
"""
import sys
import os
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from bug_detector import ContentAnalyzer


class TestFix721TransferPatterns(unittest.TestCase):
    """Verificar que los patrones de transfer se detectan."""

    def test_espereme(self):
        self.assertTrue(ContentAnalyzer._TRANSFER_PATTERNS.search("Espéreme tantito"))

    def test_le_paso(self):
        self.assertTrue(ContentAnalyzer._TRANSFER_PATTERNS.search("Le paso al encargado"))

    def test_le_comunico(self):
        self.assertTrue(ContentAnalyzer._TRANSFER_PATTERNS.search("Le comunico con el gerente"))

    def test_se_lo_paso(self):
        self.assertTrue(ContentAnalyzer._TRANSFER_PATTERNS.search("Se lo paso, un momento"))

    def test_ahorita_viene(self):
        self.assertTrue(ContentAnalyzer._TRANSFER_PATTERNS.search("Ahorita viene el encargado"))

    def test_dejeme_pasar(self):
        self.assertTrue(ContentAnalyzer._TRANSFER_PATTERNS.search("Déjeme pasarle la llamada"))

    def test_espere_un_momento(self):
        self.assertTrue(ContentAnalyzer._TRANSFER_PATTERNS.search("Espere un momento por favor"))

    def test_le_transfiero(self):
        self.assertTrue(ContentAnalyzer._TRANSFER_PATTERNS.search("Le transfiero la llamada"))


class TestFix721BruceEsperaCorrectamente(unittest.TestCase):
    """Verificar que respuestas correctas de Bruce no generan bug."""

    def test_claro_espero(self):
        self.assertTrue(ContentAnalyzer._BRUCE_ESPERA_CORRECTO.search("Claro, espero con gusto"))

    def test_si_espero(self):
        self.assertTrue(ContentAnalyzer._BRUCE_ESPERA_CORRECTO.search("Sí, espero"))

    def test_adelante(self):
        self.assertTrue(ContentAnalyzer._BRUCE_ESPERA_CORRECTO.search("Adelante"))

    def test_por_supuesto_espero(self):
        self.assertTrue(ContentAnalyzer._BRUCE_ESPERA_CORRECTO.search("Por supuesto, espero"))


class TestFix721DetectorTransferIgnorada(unittest.TestCase):
    """Tests del detector _check_transfer_ignorada."""

    def test_transfer_ignorada_bruce_sigue_vendiendo(self):
        """Si cliente pide transferir y Bruce sigue vendiendo → BUG."""
        conv = [
            ("bruce", "Buenos días, me comunico de Nioval"),
            ("cliente", "Espéreme, le paso al encargado"),
            ("bruce", "Le ofrecemos nuestro catálogo de productos ferreteros"),
        ]
        bugs = ContentAnalyzer._check_transfer_ignorada(conv)
        self.assertEqual(len(bugs), 1)
        self.assertEqual(bugs[0]["tipo"], "TRANSFER_IGNORADA")

    def test_transfer_correcta_bruce_espera(self):
        """Si cliente pide transferir y Bruce espera → NO bug."""
        conv = [
            ("bruce", "Buenos días, me comunico de Nioval"),
            ("cliente", "Le paso al encargado"),
            ("bruce", "Claro, espero con gusto"),
        ]
        bugs = ContentAnalyzer._check_transfer_ignorada(conv)
        self.assertEqual(len(bugs), 0)

    def test_no_transfer_normal(self):
        """Conversación normal sin transfer → NO bug."""
        conv = [
            ("bruce", "Buenos días, me comunico de Nioval"),
            ("cliente", "Sí, dígame"),
            ("bruce", "Le comento que trabajamos productos ferreteros"),
        ]
        bugs = ContentAnalyzer._check_transfer_ignorada(conv)
        self.assertEqual(len(bugs), 0)

    def test_transfer_dejeme_comunicar(self):
        """Déjeme comunicarle + Bruce sigue → BUG."""
        conv = [
            ("bruce", "Buenos días, ¿se encuentra el encargado?"),
            ("cliente", "Déjeme comunicarlo, un momento"),
            ("bruce", "Le comento que nuestro catálogo tiene muchos productos"),
        ]
        bugs = ContentAnalyzer._check_transfer_ignorada(conv)
        self.assertEqual(len(bugs), 1)

    def test_transfer_adelante_no_bug(self):
        """Bruce dice adelante → NO bug."""
        conv = [
            ("bruce", "Buenos días"),
            ("cliente", "Espere un momento, le paso"),
            ("bruce", "Adelante"),
        ]
        bugs = ContentAnalyzer._check_transfer_ignorada(conv)
        self.assertEqual(len(bugs), 0)

    def test_conv_corta_no_crash(self):
        """Conversación de 1 turno no crash."""
        conv = [("bruce", "Hola")]
        bugs = ContentAnalyzer._check_transfer_ignorada(conv)
        self.assertEqual(len(bugs), 0)

    def test_conv_vacia_no_crash(self):
        """Conversación vacía no crash."""
        bugs = ContentAnalyzer._check_transfer_ignorada([])
        self.assertEqual(len(bugs), 0)


if __name__ == "__main__":
    unittest.main()
