"""
Tests FIX 726-730: 5 nuevos detectores de bugs.

FIX 726: RESPUESTA_FILLER_GPT - GPT genera fillers como respuesta
FIX 727: INTERRUPCION_CONVERSACIONAL - Bruce corta al cliente mientras explica
FIX 728: DESPEDIDA_PREMATURA - Bruce se despide sin capturar contacto
FIX 729: CONTEXTO_IGNORADO (rule-based) - Cliente es decisor, Bruce lo ignora
FIX 730: SALUDO_FALTANTE - Bruce no saluda en primer turno
"""
import sys
import os
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from bug_detector import ContentAnalyzer, BugDetector, CallEventTracker


# ============================================================
# FIX 726: RESPUESTA_FILLER_GPT
# ============================================================

class TestFix726FillerPatterns(unittest.TestCase):
    """FIX 726: Verificar patrones de filler GPT."""

    def test_dejeme_ver(self):
        self.assertTrue(ContentAnalyzer._FILLER_GPT_PATTERNS.search("Déjeme ver"))

    def test_dejame_checar(self):
        self.assertTrue(ContentAnalyzer._FILLER_GPT_PATTERNS.search("déjame checar"))

    def test_dejeme_revisar(self):
        self.assertTrue(ContentAnalyzer._FILLER_GPT_PATTERNS.search("Déjeme revisar"))

    def test_dejame_validarlo(self):
        self.assertTrue(ContentAnalyzer._FILLER_GPT_PATTERNS.search("déjame validarlo"))

    def test_mmm_entiendo(self):
        self.assertTrue(ContentAnalyzer._FILLER_GPT_PATTERNS.search("mmm entiendo"))

    def test_mm_aja(self):
        self.assertTrue(ContentAnalyzer._FILLER_GPT_PATTERNS.search("mm aja"))

    def test_aja_si(self):
        self.assertTrue(ContentAnalyzer._FILLER_GPT_PATTERNS.search("aja si"))

    def test_respuesta_real_no_matchea(self):
        """Respuesta real con 'entiendo' seguida de acción NO debe matchear."""
        self.assertIsNone(ContentAnalyzer._FILLER_GPT_PATTERNS.search(
            "Entiendo, me podría dar su WhatsApp para enviarle el catálogo"
        ))

    def test_dejeme_ver_en_contexto_no_matchea(self):
        """'déjeme ver' dentro de oración larga NO matchea como filler."""
        self.assertIsNone(ContentAnalyzer._FILLER_GPT_PATTERNS.search(
            "Déjeme ver si puedo comunicarlo con el encargado de compras"
        ))


class TestFix726DetectorFillerGPT(unittest.TestCase):
    """FIX 726: Detector _check_respuesta_filler_gpt."""

    def test_2_fillers_detecta_bug(self):
        """2+ fillers GPT → BUG."""
        respuestas = [
            "Buenos días, me comunico de Nioval",
            "Déjeme ver",
            "Mmm entiendo",
            "Que tenga buen día",
        ]
        conv = [(("bruce", r) if i % 2 == 0 else ("cliente", "Sí")) for i, r in enumerate(respuestas)]
        bugs = ContentAnalyzer._check_respuesta_filler_gpt(respuestas, conv)
        self.assertEqual(len(bugs), 1)
        self.assertEqual(bugs[0]["tipo"], "RESPUESTA_FILLER_GPT")

    def test_4_fillers_critico(self):
        """4+ fillers → CRITICO."""
        respuestas = ["Déjeme ver", "Mmm", "Aja si", "Déjame checar", "Gracias"]
        conv = [("bruce", r) for r in respuestas]
        bugs = ContentAnalyzer._check_respuesta_filler_gpt(respuestas, conv)
        self.assertEqual(len(bugs), 1)
        self.assertEqual(bugs[0]["severidad"], "CRITICO")

    def test_1_filler_no_es_bug(self):
        """1 solo filler no genera bug (puede ser natural)."""
        respuestas = [
            "Buenos días, me comunico de Nioval",
            "Déjeme ver",
            "¿Me podría dar su WhatsApp?",
        ]
        conv = [("bruce", r) for r in respuestas]
        bugs = ContentAnalyzer._check_respuesta_filler_gpt(respuestas, conv)
        self.assertEqual(len(bugs), 0)

    def test_respuestas_normales_no_bug(self):
        """Respuestas normales → sin bug."""
        respuestas = [
            "Buenos días, me comunico de la marca Nioval",
            "Le comento que manejamos productos ferreteros",
            "¿Me podría dar su WhatsApp?",
        ]
        conv = [("bruce", r) for r in respuestas]
        bugs = ContentAnalyzer._check_respuesta_filler_gpt(respuestas, conv)
        self.assertEqual(len(bugs), 0)

    def test_conv_corta_no_crash(self):
        bugs = ContentAnalyzer._check_respuesta_filler_gpt(["Hola"], [("bruce", "Hola")])
        self.assertEqual(len(bugs), 0)

    def test_bruce2274_escenario_real(self):
        """BRUCE2274: 'dejeme checar', 'dejeme ver', 'dejame revisar' repetidos."""
        respuestas = [
            "Buenos días, me comunico de Nioval",
            "Déjeme checar",
            "Déjeme ver",
            "Déjame revisar",
            "Muchas gracias, que tenga buen día",
        ]
        conv = [("bruce", r) for r in respuestas]
        bugs = ContentAnalyzer._check_respuesta_filler_gpt(respuestas, conv)
        self.assertEqual(len(bugs), 1)
        self.assertGreaterEqual(int(bugs[0]["detalle"].split("x")[0].split()[-1]), 3)


# ============================================================
# FIX 727: INTERRUPCION_CONVERSACIONAL
# ============================================================

class TestFix727ClienteExplicandoPatterns(unittest.TestCase):
    """FIX 727: Patrones de cliente explicando."""

    def test_no_esta(self):
        self.assertTrue(ContentAnalyzer._CLIENTE_EXPLICANDO.search("No está ahorita"))

    def test_no_se_encuentra(self):
        self.assertTrue(ContentAnalyzer._CLIENTE_EXPLICANDO.search("No se encuentra el encargado"))

    def test_lo_que_pasa(self):
        self.assertTrue(ContentAnalyzer._CLIENTE_EXPLICANDO.search("Lo que pasa es que salió"))

    def test_no_hacemos(self):
        self.assertTrue(ContentAnalyzer._CLIENTE_EXPLICANDO.search("Nosotros no hacemos compras"))

    def test_tendria_que_marcar(self):
        self.assertTrue(ContentAnalyzer._CLIENTE_EXPLICANDO.search("Tendría que marcar más tarde"))


class TestFix727InterrupcionConversacional(unittest.TestCase):
    """FIX 727: Detector _check_interrupcion_conversacional."""

    def test_interrupcion_bruce_sigue_vendiendo(self):
        """Cliente explicando + Bruce ofrece catálogo → BUG."""
        conv = [
            ("bruce", "¿Se encuentra el encargado de compras?"),
            ("cliente", "No está ahorita, salió a"),
            ("bruce", "Le envío nuestro catálogo de productos ferreteros"),
        ]
        bugs = ContentAnalyzer._check_interrupcion_conversacional(conv)
        self.assertEqual(len(bugs), 1)
        self.assertEqual(bugs[0]["tipo"], "INTERRUPCION_CONVERSACIONAL")

    def test_interrupcion_bruce_se_despide(self):
        """Cliente explicando + Bruce se despide → BUG."""
        conv = [
            ("bruce", "Buenos días"),
            ("cliente", "Mire lo que pasa es que nosotros no manejamos"),
            ("bruce", "Muchas gracias por su tiempo, que tenga buen día"),
        ]
        bugs = ContentAnalyzer._check_interrupcion_conversacional(conv)
        self.assertEqual(len(bugs), 1)

    def test_cliente_termina_idea_no_bug(self):
        """Cliente termina oración completa (con punto) → NO bug."""
        conv = [
            ("bruce", "¿Se encuentra el encargado?"),
            ("cliente", "No está ahorita, viene más tarde."),
            ("bruce", "¿Me podría dar su WhatsApp?"),
        ]
        bugs = ContentAnalyzer._check_interrupcion_conversacional(conv)
        self.assertEqual(len(bugs), 0)

    def test_sin_explicacion_no_bug(self):
        """Cliente no explica → NO bug."""
        conv = [
            ("bruce", "¿Se encuentra el encargado?"),
            ("cliente", "Sí, dígame"),
            ("bruce", "Le comento que manejamos productos ferreteros"),
        ]
        bugs = ContentAnalyzer._check_interrupcion_conversacional(conv)
        self.assertEqual(len(bugs), 0)

    def test_conv_corta_no_crash(self):
        bugs = ContentAnalyzer._check_interrupcion_conversacional([("bruce", "Hola")])
        self.assertEqual(len(bugs), 0)

    def test_bruce2278_escenario_real(self):
        """BRUCE2278: Interrumpió mientras le decían a dónde llamar."""
        conv = [
            ("bruce", "Buenos días, ¿se encuentra el encargado?"),
            ("cliente", "No se encuentra, tendría que marcar"),
            ("bruce", "Le envío nuestro catálogo de productos"),
        ]
        bugs = ContentAnalyzer._check_interrupcion_conversacional(conv)
        self.assertEqual(len(bugs), 1)


# ============================================================
# FIX 728: DESPEDIDA_PREMATURA
# ============================================================

class TestFix728DespedidaPrematura(unittest.TestCase):
    """FIX 728: Detector _check_despedida_prematura."""

    def test_cliente_interesado_bruce_se_despide(self):
        """Cliente muestra interés, Bruce se despide sin contacto → BUG."""
        conv = [
            ("bruce", "Manejamos productos ferreteros de la marca Nioval"),
            ("cliente", "Sí, me interesa, envíame información"),
            ("bruce", "Muchas gracias por su tiempo, que tenga buen día"),
        ]
        respuestas = [c[1] for c in conv if c[0] == "bruce"]
        bugs = ContentAnalyzer._check_despedida_prematura(conv, respuestas)
        self.assertEqual(len(bugs), 1)
        self.assertEqual(bugs[0]["tipo"], "DESPEDIDA_PREMATURA")

    def test_contacto_capturado_no_bug(self):
        """Bruce capturó contacto antes de despedirse → NO bug."""
        conv = [
            ("bruce", "¿Me podría dar su WhatsApp?"),
            ("cliente", "Sí, es 3312345678"),
            ("bruce", "Perfecto, ya lo tengo anotado. Que tenga buen día"),
        ]
        respuestas = [c[1] for c in conv if c[0] == "bruce"]
        bugs = ContentAnalyzer._check_despedida_prematura(conv, respuestas)
        self.assertEqual(len(bugs), 0)

    def test_cliente_no_interesado_no_bug(self):
        """Cliente no mostró interés → despedida es normal, NO bug."""
        conv = [
            ("bruce", "Manejamos productos ferreteros"),
            ("cliente", "No me interesa, gracias"),
            ("bruce", "Que tenga buen día"),
        ]
        respuestas = [c[1] for c in conv if c[0] == "bruce"]
        bugs = ContentAnalyzer._check_despedida_prematura(conv, respuestas)
        self.assertEqual(len(bugs), 0)

    def test_tienes_donde_anotar_despedida(self):
        """'Tienes donde anotar' = interés claro, despedida = BUG."""
        conv = [
            ("bruce", "¿Se encuentra el encargado?"),
            ("cliente", "Sí, tienes donde anotar"),
            ("bruce", "Gracias por su tiempo, que tenga excelente día"),
        ]
        respuestas = [c[1] for c in conv if c[0] == "bruce"]
        bugs = ContentAnalyzer._check_despedida_prematura(conv, respuestas)
        self.assertEqual(len(bugs), 1)

    def test_conv_corta_no_crash(self):
        bugs = ContentAnalyzer._check_despedida_prematura(
            [("bruce", "Hola")], ["Hola"]
        )
        self.assertEqual(len(bugs), 0)


# ============================================================
# FIX 729: CONTEXTO_IGNORADO (rule-based)
# ============================================================

class TestFix729ClienteDecisorPatterns(unittest.TestCase):
    """FIX 729: Patrones de cliente como decisor."""

    def test_yo_soy_el_encargado(self):
        self.assertTrue(ContentAnalyzer._CLIENTE_ES_DECISOR.search("Yo soy el encargado"))

    def test_yo_soy_el_dueno(self):
        self.assertTrue(ContentAnalyzer._CLIENTE_ES_DECISOR.search("Yo soy el dueño"))

    def test_yo_hago_las_compras(self):
        self.assertTrue(ContentAnalyzer._CLIENTE_ES_DECISOR.search("Yo hago las compras aquí"))

    def test_yo_me_encargo(self):
        self.assertTrue(ContentAnalyzer._CLIENTE_ES_DECISOR.search("Yo me encargo de las compras"))

    def test_tienes_donde_anotar(self):
        self.assertTrue(ContentAnalyzer._CLIENTE_ES_DECISOR.search("¿Tienes donde anotar?"))

    def test_yo_soy_la_gerente(self):
        self.assertTrue(ContentAnalyzer._CLIENTE_ES_DECISOR.search("Yo soy la gerente"))

    def test_conmigo_es(self):
        self.assertTrue(ContentAnalyzer._CLIENTE_ES_DECISOR.search("Conmigo es, dígame"))


class TestFix729BruceIgnoraDecisor(unittest.TestCase):
    """FIX 729: Patrones de Bruce ignorando al decisor."""

    def test_cuando_regrese_el_encargado(self):
        self.assertTrue(ContentAnalyzer._BRUCE_IGNORA_DECISOR.search(
            "Cuando regrese el encargado le dejo recado"
        ))

    def test_le_dejo_recado(self):
        self.assertTrue(ContentAnalyzer._BRUCE_IGNORA_DECISOR.search("Le dejo recado"))

    def test_cuando_llegue_el_jefe(self):
        self.assertTrue(ContentAnalyzer._BRUCE_IGNORA_DECISOR.search(
            "Cuando llegue el jefe le paso la información"
        ))


class TestFix729ContextoIgnorado(unittest.TestCase):
    """FIX 729: Detector _check_contexto_ignorado."""

    def test_encargado_ignorado(self):
        """Cliente dice ser encargado, Bruce ofrece dejar recado → BUG."""
        conv = [
            ("bruce", "¿Se encuentra el encargado de compras?"),
            ("cliente", "Yo soy el encargado, dígame"),
            ("bruce", "Cuando regrese el encargado le dejo recado"),
        ]
        bugs = ContentAnalyzer._check_contexto_ignorado(conv)
        self.assertEqual(len(bugs), 1)
        self.assertEqual(bugs[0]["tipo"], "CONTEXTO_IGNORADO")
        self.assertEqual(bugs[0]["severidad"], "CRITICO")

    def test_dueno_ignorado(self):
        """Cliente dice ser dueño, Bruce ofrece dejar recado → BUG."""
        conv = [
            ("bruce", "¿Se encuentra el encargado?"),
            ("cliente", "Yo soy el dueño de la tienda"),
            ("bruce", "Le dejo recado con el encargado"),
        ]
        bugs = ContentAnalyzer._check_contexto_ignorado(conv)
        self.assertEqual(len(bugs), 1)

    def test_encargado_atendido_correctamente(self):
        """Cliente es encargado, Bruce lo atiende → NO bug."""
        conv = [
            ("bruce", "¿Se encuentra el encargado de compras?"),
            ("cliente", "Yo soy el encargado, dígame"),
            ("bruce", "Perfecto, le comento que manejamos productos ferreteros"),
        ]
        bugs = ContentAnalyzer._check_contexto_ignorado(conv)
        self.assertEqual(len(bugs), 0)

    def test_bruce2263_escenario_real(self):
        """BRUCE2263: No detectó al encargado."""
        conv = [
            ("bruce", "Buenos días, ¿se encuentra el encargado de compras?"),
            ("cliente", "Yo me encargo de las compras aquí"),
            ("bruce", "Cuando regrese el encargado le dejo recado del catálogo"),
        ]
        bugs = ContentAnalyzer._check_contexto_ignorado(conv)
        self.assertEqual(len(bugs), 1)

    def test_conv_corta_no_crash(self):
        bugs = ContentAnalyzer._check_contexto_ignorado([("bruce", "Hola")])
        self.assertEqual(len(bugs), 0)


# ============================================================
# FIX 730: SALUDO_FALTANTE
# ============================================================

class TestFix730SaludoFaltante(unittest.TestCase):
    """FIX 730: Detector _check_saludo_faltante."""

    def test_sin_saludo(self):
        """Primer turno sin saludo → BUG."""
        respuestas = ["Le comento que manejamos productos ferreteros"]
        bugs = ContentAnalyzer._check_saludo_faltante(respuestas)
        self.assertEqual(len(bugs), 1)
        self.assertEqual(bugs[0]["tipo"], "SALUDO_FALTANTE")

    def test_con_buenos_dias(self):
        """'Buenos días' → NO bug."""
        respuestas = ["Buenos días, me comunico de la marca Nioval"]
        bugs = ContentAnalyzer._check_saludo_faltante(respuestas)
        self.assertEqual(len(bugs), 0)

    def test_con_buen_dia(self):
        """'Buen día' → NO bug."""
        respuestas = ["Buen día, le llamo de Nioval"]
        bugs = ContentAnalyzer._check_saludo_faltante(respuestas)
        self.assertEqual(len(bugs), 0)

    def test_con_buenas_tardes(self):
        """'Buenas tardes' → NO bug."""
        respuestas = ["Buenas tardes, me comunico de la marca Nioval"]
        bugs = ContentAnalyzer._check_saludo_faltante(respuestas)
        self.assertEqual(len(bugs), 0)

    def test_con_me_comunico_de(self):
        """'Me comunico de' es forma de saludo → NO bug."""
        respuestas = ["Me comunico de la marca Nioval"]
        bugs = ContentAnalyzer._check_saludo_faltante(respuestas)
        self.assertEqual(len(bugs), 0)

    def test_vacio_no_crash(self):
        bugs = ContentAnalyzer._check_saludo_faltante([])
        self.assertEqual(len(bugs), 0)

    def test_respuesta_vacia_no_crash(self):
        bugs = ContentAnalyzer._check_saludo_faltante([""])
        self.assertEqual(len(bugs), 0)


# ============================================================
# INTEGRACION: Verificar en BugDetector.analyze()
# ============================================================

class TestFix726a730EnAnalyze(unittest.TestCase):
    """Verificar que los 5 detectores aparecen en BugDetector.analyze()."""

    def test_filler_gpt_en_analyze(self):
        tracker = CallEventTracker("test", "BRUCE_TEST")
        tracker.respuestas_bruce = [
            "Buenos días, me comunico de Nioval",
            "Déjeme ver", "Mmm entiendo", "Que tenga buen día",
        ]
        tracker.conversacion = [("bruce", r) for r in tracker.respuestas_bruce]
        bugs = BugDetector.analyze(tracker)
        tipos = [b["tipo"] for b in bugs]
        self.assertIn("RESPUESTA_FILLER_GPT", tipos)

    def test_contexto_ignorado_en_analyze(self):
        tracker = CallEventTracker("test", "BRUCE_TEST")
        tracker.conversacion = [
            ("bruce", "Buenos días, ¿se encuentra el encargado?"),
            ("cliente", "Yo soy el encargado"),
            ("bruce", "Cuando regrese el encargado le dejo recado"),
        ]
        tracker.respuestas_bruce = ["Buenos días, ¿se encuentra el encargado?", "Cuando regrese el encargado le dejo recado"]
        bugs = BugDetector.analyze(tracker)
        tipos = [b["tipo"] for b in bugs]
        self.assertIn("CONTEXTO_IGNORADO", tipos)

    def test_saludo_faltante_en_analyze(self):
        tracker = CallEventTracker("test", "BRUCE_TEST")
        tracker.respuestas_bruce = ["Le comento que manejamos productos", "Que tenga buen día"]
        tracker.conversacion = [
            ("bruce", "Le comento que manejamos productos"),
            ("cliente", "No gracias"),
            ("bruce", "Que tenga buen día"),
        ]
        bugs = BugDetector.analyze(tracker)
        tipos = [b["tipo"] for b in bugs]
        self.assertIn("SALUDO_FALTANTE", tipos)

    def test_despedida_prematura_en_analyze(self):
        tracker = CallEventTracker("test", "BRUCE_TEST")
        tracker.conversacion = [
            ("bruce", "Buenos días, me comunico de Nioval"),
            ("cliente", "Sí, me interesa, envíame información"),
            ("bruce", "Gracias por su tiempo, que tenga buen día"),
        ]
        tracker.respuestas_bruce = [c[1] for c in tracker.conversacion if c[0] == "bruce"]
        bugs = BugDetector.analyze(tracker)
        tipos = [b["tipo"] for b in bugs]
        self.assertIn("DESPEDIDA_PREMATURA", tipos)


# ============================================================
# ESCENARIOS REALES
# ============================================================

class TestEscenariosReales(unittest.TestCase):
    """Replay de llamadas reales de la auditoría."""

    def test_bruce2268_fillers_repetidos(self):
        """BRUCE2268: 'dejame ver' repetido constantemente."""
        tracker = CallEventTracker("test", "BRUCE2268")
        tracker.respuestas_bruce = [
            "Buenos días, me comunico de la marca Nioval",
            "Déjeme ver",
            "Déjame ver",
            "Déjeme ver",
            "Que tenga buen día",
        ]
        tracker.conversacion = [("bruce", r) for r in tracker.respuestas_bruce]
        bugs = BugDetector.analyze(tracker)
        tipos = [b["tipo"] for b in bugs]
        self.assertIn("RESPUESTA_FILLER_GPT", tipos)

    def test_bruce2263_encargado_no_detectado(self):
        """BRUCE2263: Cliente es encargado, Bruce lo ignora."""
        tracker = CallEventTracker("test", "BRUCE2263")
        tracker.conversacion = [
            ("bruce", "Buenos días, ¿se encuentra el encargado de compras?"),
            ("cliente", "Yo me encargo de las compras aquí"),
            ("bruce", "Cuando regrese el encargado le dejo recado del catálogo"),
        ]
        tracker.respuestas_bruce = [c[1] for c in tracker.conversacion if c[0] == "bruce"]
        bugs = BugDetector.analyze(tracker)
        tipos = [b["tipo"] for b in bugs]
        self.assertIn("CONTEXTO_IGNORADO", tipos)


class TestNuevosDetectoresNoCrash(unittest.TestCase):
    """Edge cases: verificar que nada crashea."""

    def test_todos_con_conv_vacia(self):
        self.assertEqual(ContentAnalyzer._check_respuesta_filler_gpt([], []), [])
        self.assertEqual(ContentAnalyzer._check_interrupcion_conversacional([]), [])
        self.assertEqual(ContentAnalyzer._check_despedida_prematura([], []), [])
        self.assertEqual(ContentAnalyzer._check_contexto_ignorado([]), [])
        self.assertEqual(ContentAnalyzer._check_saludo_faltante([]), [])

    def test_todos_con_un_turno(self):
        conv = [("bruce", "Hola")]
        resp = ["Hola"]
        self.assertEqual(ContentAnalyzer._check_respuesta_filler_gpt(resp, conv), [])
        self.assertEqual(ContentAnalyzer._check_interrupcion_conversacional(conv), [])
        self.assertEqual(ContentAnalyzer._check_despedida_prematura(conv, resp), [])
        self.assertEqual(ContentAnalyzer._check_contexto_ignorado(conv), [])
        # saludo_faltante SÍ puede reportar con 1 turno
        self.assertIsInstance(ContentAnalyzer._check_saludo_faltante(resp), list)


if __name__ == "__main__":
    unittest.main()
