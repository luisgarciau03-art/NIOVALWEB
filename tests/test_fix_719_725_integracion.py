"""
Tests de integración FIX 719-725: Replay de conversaciones reales de la auditoría.

Verifica que los nuevos detectores funcionan con datos de producción.
"""
import sys
import os
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from bug_detector import BugDetector, CallEventTracker, ContentAnalyzer


class TestBRUCE2268Degradacion(unittest.TestCase):
    """BRUCE2268: 4x filler → debe detectar DEGRADACION_TTS + RESPUESTA_FILLER_INCOHERENTE."""

    def test_4_fillers_detecta_degradacion(self):
        tracker = CallEventTracker("CA_test_2268", "BRUCE2268", "523312345678")
        tracker.filler_162a_count = 4
        tracker.conversacion = [
            ("bruce", "Buenos días, me comunico de la marca Nioval"),
            ("cliente", "Sí, dígame"),
            ("bruce", "Déjeme ver..."),  # filler
            ("cliente", "¿Bueno?"),
            ("bruce", "Déjeme ver..."),  # filler
            ("cliente", "¿Sigue ahí?"),
            ("bruce", "Déjeme ver..."),  # filler
        ]
        tracker.respuestas_bruce = [t for _, t in tracker.conversacion if _ == "bruce"]
        bugs = BugDetector.analyze(tracker)
        tipos = [b["tipo"] for b in bugs]
        self.assertIn("DEGRADACION_TTS", tipos)
        self.assertIn("RESPUESTA_FILLER_INCOHERENTE", tipos)


class TestBRUCE2281CorporativoNoSkip(unittest.TestCase):
    """BRUCE2281: Cliente dice 'corporativo de Cemex' → FIX 664B NO debe skipear GPT eval."""

    def test_corporativo_no_es_comportamiento_correcto(self):
        from bug_detector import _es_comportamiento_correcto
        conv = [
            ("bruce", "¿Se encuentra el encargado de compras?"),
            ("cliente", "Esto es corporativo de Cemex, no manejamos ferretería"),
            ("bruce", "¿Me podría dar su WhatsApp para enviarle nuestro catálogo?"),
        ]
        result = _es_comportamiento_correcto(conv)
        self.assertFalse(result, "FIX 722: 'corporativo' indica decisor, NO debe skipear GPT eval")


class TestBRUCE2272DictadoEmail(unittest.TestCase):
    """BRUCE2272: Dictado email interrumpido → DICTADO_INTERRUMPIDO."""

    def test_email_dictado_despedida(self):
        conv = [
            ("bruce", "¿Me podría dar su correo?"),
            ("cliente", "Es juan arroba gmail punto com"),
            ("bruce", "Muchas gracias por su tiempo, que tenga buen día"),
        ]
        bugs = ContentAnalyzer._check_dictado_interrumpido(conv)
        self.assertEqual(len(bugs), 1)
        self.assertEqual(bugs[0]["tipo"], "DICTADO_INTERRUMPIDO")

    def test_email_dictado_confirmado_no_bug(self):
        """Si Bruce confirma el dato antes de despedirse → NO bug."""
        conv = [
            ("bruce", "¿Me podría dar su correo?"),
            ("cliente", "Es juan arroba gmail punto com"),
            ("bruce", "Perfecto, ya lo tengo anotado. Que tenga buen día"),
        ]
        bugs = ContentAnalyzer._check_dictado_interrumpido(conv)
        self.assertEqual(len(bugs), 0)


class TestBRUCE2274DictadoTelefono(unittest.TestCase):
    """BRUCE2274: Dictado teléfono interrumpido → DICTADO_INTERRUMPIDO."""

    def test_telefono_dictado_despedida(self):
        conv = [
            ("bruce", "¿Me podría dar su número?"),
            ("cliente", "33 12 34 56 78"),
            ("bruce", "Me comunico después, que tenga buen día"),
        ]
        bugs = ContentAnalyzer._check_dictado_interrumpido(conv)
        self.assertEqual(len(bugs), 1)
        self.assertEqual(bugs[0]["tipo"], "DICTADO_INTERRUMPIDO")


class TestBRUCE2284AreaEquivocada(unittest.TestCase):
    """BRUCE2284: Área equivocada con 24s → debe detectar con threshold 20s."""

    def test_area_equivocada_bruce_insiste(self):
        conv = [
            ("bruce", "Buenos días, me comunico de Nioval, productos ferreteros"),
            ("cliente", "No, aquí no es ferretería, se equivocó de número"),
            ("bruce", "¿Me podría dar el WhatsApp del encargado?"),
        ]
        bugs = ContentAnalyzer._check_area_equivocada(conv)
        self.assertEqual(len(bugs), 1)
        self.assertEqual(bugs[0]["tipo"], "AREA_EQUIVOCADA")


class TestBRUCE2255Timeout(unittest.TestCase):
    """BRUCE2255: GPT timeout + 'no hacemos compras' → area equivocada."""

    def test_no_hacemos_compras_detectado(self):
        """FIX 720: 'no hacemos compras' ahora está en _AREA_EQUIVOCADA_PATTERNS."""
        conv = [
            ("bruce", "Buenos días, me comunico de la marca Nioval"),
            ("cliente", "No hacemos ningún tipo de compra. Ya te comenté"),
            ("bruce", "Entiendo, ¿me podría dar su WhatsApp?"),
        ]
        bugs = ContentAnalyzer._check_area_equivocada(conv)
        self.assertEqual(len(bugs), 1)
        self.assertEqual(bugs[0]["tipo"], "AREA_EQUIVOCADA")


class TestTransferIgnoradaReal(unittest.TestCase):
    """Escenarios reales de transfer ignorada."""

    def test_le_paso_al_encargado_bruce_sigue(self):
        conv = [
            ("bruce", "Buenos días, ¿se encuentra el encargado de compras?"),
            ("cliente", "Sí, espéreme, le paso"),
            ("bruce", "Le comento que nuestro catálogo tiene más de 500 productos"),
        ]
        bugs = ContentAnalyzer._check_transfer_ignorada(conv)
        self.assertEqual(len(bugs), 1)


class TestPreferenciaIgnoradaReal(unittest.TestCase):
    """Escenarios reales de preferencia ignorada."""

    def test_prefiere_correo_bruce_pide_whatsapp(self):
        conv = [
            ("bruce", "¿Le gustaría que le envíe nuestro catálogo?"),
            ("cliente", "Sí, mándamelo por correo mejor"),
            ("bruce", "Perfecto, ¿me podría dar su WhatsApp?"),
        ]
        bugs = ContentAnalyzer._check_preferencia_ignorada(conv)
        self.assertEqual(len(bugs), 1)


class TestDatoNegadoReal(unittest.TestCase):
    """Escenarios reales de dato negado y reinsistido."""

    def test_no_tiene_whatsapp_bruce_reinsiste(self):
        conv = [
            ("bruce", "¿Me podría dar su WhatsApp?"),
            ("cliente", "No tengo WhatsApp, solo tengo fijo"),
            ("bruce", "¿No tiene algún WhatsApp al que le pueda enviar la información?"),
        ]
        bugs = ContentAnalyzer._check_dato_negado_reinsistido(conv)
        self.assertEqual(len(bugs), 1)
        self.assertEqual(bugs[0]["tipo"], "DATO_NEGADO_REINSISTIDO")


class TestNuevosDetectoresNoCrash(unittest.TestCase):
    """Todos los nuevos detectores no crashean con edge cases."""

    def test_conv_vacia_todos(self):
        conv = []
        self.assertEqual(ContentAnalyzer._check_transfer_ignorada(conv), [])
        self.assertEqual(ContentAnalyzer._check_preferencia_ignorada(conv), [])
        self.assertEqual(ContentAnalyzer._check_dato_negado_reinsistido(conv), [])

    def test_conv_un_turno(self):
        conv = [("bruce", "Hola")]
        self.assertEqual(ContentAnalyzer._check_transfer_ignorada(conv), [])
        self.assertEqual(ContentAnalyzer._check_preferencia_ignorada(conv), [])
        self.assertEqual(ContentAnalyzer._check_dato_negado_reinsistido(conv), [])

    def test_tracker_degradacion_sin_fillers(self):
        tracker = CallEventTracker("test", "TEST")
        self.assertEqual(ContentAnalyzer._check_degradacion_servicio(tracker), [])


if __name__ == "__main__":
    unittest.main()
