# -*- coding: utf-8 -*-
"""
Tests para FIX 850-853:
- FIX 850: NO_INTEREST patterns "ya tengo unos proveedores" (BRUCE2539)
- FIX 851: _DICTADO_PATTERNS_FUERTE sin \bese\b (BRUCE2494)
- FIX 852: Anti-loop alternativa dup en _filtrar_respuesta_post_gpt (BRUCE2522)
- FIX 853: LOOP min length 10→20 (BRUCE2540 "Si, adelante." 13 chars)
"""
import unittest
import sys
import os
import re

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


# =============================================================================
# FIX 850: NO_INTEREST patterns "ya tengo unos proveedores"
# =============================================================================

class TestFix850NoInterestProveedores(unittest.TestCase):
    """FIX 850: BRUCE2539 - 'ya tengo unos proveedores' debe ser NO_INTEREST."""

    def _classify_no_interest(self, texto):
        """Simula la clasificación NO_INTEREST del IntentClassifier."""
        texto_lower = texto.lower().strip()
        # Normalizar acentos
        for a, b in [('á','a'),('é','e'),('í','i'),('ó','o'),('ú','u'),('ü','u')]:
            texto_lower = texto_lower.replace(a, b)
        patterns = [
            'ya tengo proveedor', 'ya tengo proveedores',
            'tengo proveedor de eso', 'tengo mis proveedores',
            # FIX 850: nuevas variantes
            'ya tengo unos proveedores', 'ya tengo varios proveedores',
            'ya tenemos unos proveedores', 'ya tenemos varios proveedores',
            'tenemos nuestros proveedores', 'tenemos nuestros propios proveedores',
            'contamos con proveedores', 'contamos con nuestros proveedores',
            'ya contamos con proveedor', 'ya contamos con proveedores',
            # previas
            'ya tenemos proveedor', 'ya tenemos proveedores',
        ]
        return any(p in texto_lower for p in patterns)

    def test_ya_tengo_unos_proveedores(self):
        """BRUCE2539: 'ya tengo unos proveedores' → NO_INTEREST."""
        self.assertTrue(self._classify_no_interest("Pues, ya tengo unos proveedores"))

    def test_ya_tengo_varios_proveedores(self):
        """'ya tengo varios proveedores' → NO_INTEREST."""
        self.assertTrue(self._classify_no_interest("ya tengo varios proveedores"))

    def test_ya_tenemos_unos_proveedores(self):
        """'ya tenemos unos proveedores' → NO_INTEREST."""
        self.assertTrue(self._classify_no_interest("ya tenemos unos proveedores"))

    def test_tenemos_nuestros_proveedores(self):
        """'tenemos nuestros proveedores' → NO_INTEREST."""
        self.assertTrue(self._classify_no_interest("tenemos nuestros proveedores"))

    def test_contamos_con_proveedores(self):
        """'contamos con proveedores' → NO_INTEREST."""
        self.assertTrue(self._classify_no_interest("contamos con proveedores"))

    def test_ya_contamos_con_proveedores(self):
        """'ya contamos con proveedores' → NO_INTEREST."""
        self.assertTrue(self._classify_no_interest("ya contamos con proveedores"))

    def test_ya_tengo_proveedor_singular(self):
        """FIX 844 anterior sigue funcionando: 'ya tengo proveedor' → NO_INTEREST."""
        self.assertTrue(self._classify_no_interest("ya tengo proveedor"))

    def test_busco_proveedor_not_no_interest(self):
        """'busco un proveedor' NO es NO_INTEREST."""
        self.assertFalse(self._classify_no_interest("busco un proveedor"))

    def test_soy_el_proveedor_not_no_interest(self):
        """'soy el proveedor de X' NO es NO_INTEREST."""
        self.assertFalse(self._classify_no_interest("soy el proveedor de materiales"))

    def test_tenemos_nuestros_propios_proveedores(self):
        """'tenemos nuestros propios proveedores' → NO_INTEREST."""
        self.assertTrue(self._classify_no_interest("tenemos nuestros propios proveedores"))


# =============================================================================
# FIX 851: _DICTADO_PATTERNS_FUERTE sin \bese\b
# =============================================================================

class TestFix851DictadoPatternsFuerte(unittest.TestCase):
    """FIX 851: BRUCE2494 - 'ese tipo de caso' no debe ser detectado como dictado."""

    @classmethod
    def setUpClass(cls):
        from bug_detector import ContentAnalyzer
        cls.patterns_fuerte = ContentAnalyzer._DICTADO_PATTERNS_FUERTE
        cls.patterns_original = ContentAnalyzer._DICTADO_PATTERNS

    def test_ese_tipo_de_caso_no_fuerte(self):
        """BRUCE2494: 'nosotros no tenemos ese tipo de caso' → NO detectado por FUERTE."""
        texto = "nosotros no tenemos ese tipo de caso"
        self.assertFalse(bool(self.patterns_fuerte.search(texto)))

    def test_ese_tipo_de_caso_original_detecta(self):
        """'nosotros no tenemos ese tipo de caso' → SÍ detectado por patrón original (era FP)."""
        texto = "nosotros no tenemos ese tipo de caso"
        # El patrón original tenía \bese\b → detecta "ese"
        self.assertTrue(bool(self.patterns_original.search(texto)))

    def test_numero_real_fuerte(self):
        """'33 12 34 56 78' → SÍ detectado por FUERTE (dígitos separados)."""
        self.assertTrue(bool(self.patterns_fuerte.search("33 12 34 56 78")))

    def test_numero_real_continuo_fuerte(self):
        """'3312345678' → SÍ detectado por FUERTE (10 dígitos continuos)."""
        self.assertTrue(bool(self.patterns_fuerte.search("3312345678")))

    def test_arroba_fuerte(self):
        """'mi correo es compras arroba gmail' → SÍ detectado por FUERTE."""
        self.assertTrue(bool(self.patterns_fuerte.search("mi correo es compras arroba gmail")))

    def test_gmail_fuerte(self):
        """'compras at gmail.com' → SÍ detectado por FUERTE."""
        self.assertTrue(bool(self.patterns_fuerte.search("es compras@gmail.com")))

    def test_mi_numero_es_fuerte(self):
        """'mi número es' → SÍ detectado por FUERTE (frase explícita)."""
        self.assertTrue(bool(self.patterns_fuerte.search("mi número es")))

    def test_ele_fuerte_no_detecta(self):
        """'el ele está en' → NO detectado por FUERTE (letra aislada no cuenta)."""
        self.assertFalse(bool(self.patterns_fuerte.search("el ele esta en la lista")))

    def test_ese_solo_no_fuerte(self):
        """'ese es el número' → NO detectado por FUERTE."""
        self.assertFalse(bool(self.patterns_fuerte.search("ese es el número")))

    def test_no_hora_detectada_fuerte(self):
        """'a las 4:00' → NO detectado por FUERTE (00 < 3 dígitos)."""
        self.assertFalse(bool(self.patterns_fuerte.search("viene a las 4:00")))


class TestFix851CheckDictadoInterrumpido(unittest.TestCase):
    """FIX 851: _check_dictado_interrumpido usa FUERTE → BRUCE2494 no genera bug."""

    @classmethod
    def setUpClass(cls):
        from bug_detector import ContentAnalyzer
        cls.analyzer = ContentAnalyzer

    def test_bruce2494_no_bug(self):
        """BRUCE2494: 'ese tipo de caso' seguido de despedida → NO bug DICTADO_INTERRUMPIDO."""
        conv = [
            ("bruce", "Buen día, soy Bruce de NIOVAL."),
            ("cliente", "Este, no, una disculpa, nosotros no tenemos ese tipo de caso. Hasta luego."),
            ("bruce", "Disculpe la molestia. Que tenga excelente día."),
        ]
        bugs = self.analyzer._check_dictado_interrumpido(conv)
        self.assertEqual(len(bugs), 0, f"Bugs inesperados: {bugs}")

    def test_real_dictado_interrumpido_detectado(self):
        """Dictado real con número seguido de despedida → SÍ bug DICTADO_INTERRUMPIDO."""
        conv = [
            ("bruce", "¿Me puede dar su WhatsApp?"),
            ("cliente", "Sí, es el 3312345678"),
            ("bruce", "Que tenga excelente día."),
        ]
        bugs = self.analyzer._check_dictado_interrumpido(conv)
        tipos = [b['tipo'] for b in bugs]
        self.assertIn("DICTADO_INTERRUMPIDO", tipos)

    def test_correo_dictado_interrumpido(self):
        """'mi correo es compras arroba gmail' seguido de despedida → SÍ bug."""
        conv = [
            ("bruce", "¿Me puede dar su correo?"),
            ("cliente", "mi correo es compras arroba gmail punto com"),
            ("bruce", "Muchas gracias por su tiempo, que tenga buen día."),
        ]
        bugs = self.analyzer._check_dictado_interrumpido(conv)
        tipos = [b['tipo'] for b in bugs]
        self.assertIn("DICTADO_INTERRUMPIDO", tipos)

    def test_no_bug_sin_dictado(self):
        """Texto sin patrones de dictado → NO bug."""
        conv = [
            ("bruce", "¿Se encontrará el encargado?"),
            ("cliente", "No está, viene mañana"),
            ("bruce", "Que tenga excelente día."),
        ]
        bugs = self.analyzer._check_dictado_interrumpido(conv)
        self.assertEqual(len(bugs), 0)


# =============================================================================
# FIX 852: Anti-loop alternativa dup
# =============================================================================

class TestFix852AntiLoopAlternativa(unittest.TestCase):
    """FIX 852: BRUCE2522 - Si la alternativa de FIX 679 se repetiría, usar cierre."""

    def _simular_dup_852(self, respuesta, history_previas):
        """Simula la lógica de FIX 852 dentro de FIX 679."""
        import unicodedata as ud
        # Determinar alternativa de FIX 679
        if 'encargado' in respuesta.lower():
            alt = "¿Me podría proporcionar un WhatsApp o correo para enviarle el catálogo?"
        elif 'nioval' in respuesta.lower():
            alt = "¿Se encontrará el encargado o encargada de compras?"
        elif 'whatsapp' in respuesta.lower():
            alt = "¿Prefiere que le envíe la información por correo electrónico?"
        elif 'catálogo' in respuesta.lower() or 'catalogo' in respuesta.lower():
            alt = "Muchas gracias por su tiempo. Que tenga excelente día."
        else:
            alt = "Disculpe, ¿me podría indicar cómo le puedo apoyar?"

        # Normalizar alt
        alt_norm = ud.normalize('NFKD', alt.lower()).encode('ascii', 'ignore').decode('ascii')
        alt_norm = re.sub(r'[^\w\s]', '', alt_norm).strip()

        # Contar dups del alt en historial previo
        alt_dup = sum(
            1 for p in history_previas
            if re.sub(r'[^\w\s]', '',
                ud.normalize('NFKD', p.lower()).encode('ascii', 'ignore').decode('ascii')
            ).strip() == alt_norm
        )

        if alt_dup >= 2:
            return "Le envío la información por WhatsApp. Muchas gracias por su tiempo, que tenga excelente día."
        return alt

    def test_bruce2522_alt_ya_dicha_2x_cierre(self):
        """BRUCE2522: Alt 'Disculpe...' ya dicha 2x en historial → cierre definitivo."""
        history = [
            "Disculpe, ¿me podría indicar cómo le puedo apoyar?",
            "Disculpe, ¿me podría indicar cómo le puedo apoyar?",
            "Manejamos grifería y herramientas NIOVAL.",
        ]
        respuesta = "Manejamos grifería y herramientas, le podemos ofrecer mucho."
        resultado = self._simular_dup_852(respuesta, history)
        self.assertIn("Muchas gracias", resultado)
        self.assertNotIn("Disculpe", resultado)

    def test_alt_nueva_no_dup_retorna_alt(self):
        """Alt todavía no repetida → retornar alternativa normal."""
        history = [
            "Manejamos grifería y herramientas NIOVAL.",
        ]
        respuesta = "Manejamos grifería y herramientas, le podemos ofrecer mucho."
        resultado = self._simular_dup_852(respuesta, history)
        self.assertIn("Disculpe", resultado)

    def test_alt_dicha_1x_no_cierre(self):
        """Alt dicha solo 1x → retornar alternativa (no cierre)."""
        history = [
            "Disculpe, ¿me podría indicar cómo le puedo apoyar?",
            "Manejamos grifería.",
        ]
        respuesta = "Manejamos grifería, herramientas, candados."
        resultado = self._simular_dup_852(respuesta, history)
        self.assertIn("Disculpe", resultado)


# =============================================================================
# FIX 853: LOOP min length 10→20
# =============================================================================

class TestFix853LoopMinLength(unittest.TestCase):
    """FIX 853: BRUCE2540 - "Si, adelante." (13 chars) no debe detectar LOOP."""

    @classmethod
    def setUpClass(cls):
        from bug_detector import CallEventTracker, BugDetector
        cls.CallEventTracker = CallEventTracker
        cls.BugDetector = BugDetector

    def _make_tracker_with_resps(self, resps):
        """Crea un tracker con respuestas de Bruce dadas."""
        tracker = self.CallEventTracker.__new__(self.CallEventTracker)
        tracker.respuestas_bruce = resps
        tracker.conversacion = []
        tracker.duracion_total_s = 60
        # Atributos requeridos por BugDetector.analyze
        tracker.twiml_count = 1
        tracker.audio_fetch_count = 1
        tracker.cliente_dijo_bueno = 0
        tracker.errores_stt = 0
        tracker.turnos_sin_respuesta = 0
        tracker.tts_errors = 0
        tracker.gpt_errors = 0
        return tracker

    def test_si_adelante_13chars_no_loop(self):
        """'Si, adelante.' (13 chars) repetida 3x → NO es LOOP con FIX 853 (len > 20)."""
        # "Si, adelante." → len = 13 ≤ 20 → NO debe generar LOOP
        tracker = self._make_tracker_with_resps(["Si, adelante.", "Si, adelante.", "Si, adelante."])
        bugs = self.BugDetector.analyze(tracker)
        loop_bugs = [b for b in bugs if b['tipo'] == 'LOOP']
        self.assertEqual(len(loop_bugs), 0, f"FIX 853: 'Si, adelante.' no debe ser LOOP: {loop_bugs}")

    def test_ack_corto_14chars_no_loop(self):
        """Ack de 14 chars repetido 3x → NO es LOOP."""
        ack = "Sí, adelante."  # 14 chars
        tracker = self._make_tracker_with_resps([ack, ack, ack])
        bugs = self.BugDetector.analyze(tracker)
        loop_bugs = [b for b in bugs if b['tipo'] == 'LOOP']
        self.assertEqual(len(loop_bugs), 0)

    def test_respuesta_larga_loop_detectado(self):
        """Respuesta >20 chars repetida 3x → SÍ es LOOP."""
        resp = "Manejamos grifería, herramientas y más de 15 categorías de productos ferreteros."
        tracker = self._make_tracker_with_resps([resp, resp, resp])
        bugs = self.BugDetector.analyze(tracker)
        loop_bugs = [b for b in bugs if b['tipo'] == 'LOOP']
        self.assertGreater(len(loop_bugs), 0, "Respuesta larga repetida 3x debe ser LOOP")

    def test_respuesta_21chars_loop_detectado(self):
        """Respuesta exactamente 21 chars repetida 3x → SÍ es LOOP."""
        resp = "A" * 21  # 21 chars > 20
        tracker = self._make_tracker_with_resps([resp, resp, resp])
        bugs = self.BugDetector.analyze(tracker)
        loop_bugs = [b for b in bugs if b['tipo'] == 'LOOP']
        self.assertGreater(len(loop_bugs), 0)

    def test_respuesta_20chars_no_loop(self):
        """Respuesta exactamente 20 chars repetida 3x → NO es LOOP (len > 20, no >=)."""
        resp = "A" * 20  # 20 chars, no > 20
        tracker = self._make_tracker_with_resps([resp, resp, resp])
        bugs = self.BugDetector.analyze(tracker)
        loop_bugs = [b for b in bugs if b['tipo'] == 'LOOP']
        self.assertEqual(len(loop_bugs), 0)

    def test_solo_2_repeticiones_no_loop(self):
        """Respuesta larga repetida solo 2x → NO es LOOP (requiere 3+)."""
        resp = "Manejamos grifería y herramientas de ferretería."
        tracker = self._make_tracker_with_resps([resp, resp])
        bugs = self.BugDetector.analyze(tracker)
        loop_bugs = [b for b in bugs if b['tipo'] == 'LOOP']
        self.assertEqual(len(loop_bugs), 0)


if __name__ == '__main__':
    unittest.main()
