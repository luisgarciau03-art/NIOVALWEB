"""
Tests FIX 749-750: FIX 569 gate punctuation fix + GPT eval false positive.

FIX 749A: BRUCE2322+2326 - palabras_espanol_569 missing greeting words + punctuation stripping
FIX 749B: BRUCE2322+2326 - Strong signals bypass FIX 569 gate entirely
FIX 750: BRUCE2321 - "Sí, bueno?" is connection check, NOT interest (GPT eval false positive)
"""
import sys
import os
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ============================================================
# FIX 749A: Punctuation stripping in FIX 569
# ============================================================

class TestFix749APunctuationStripping(unittest.TestCase):
    """FIX 749A: Strip punctuation before word matching."""

    def _strip_punct(self, word):
        """Replica the FIX 749A punctuation strip logic."""
        _punct_749 = '¿?¡!.,;:()'
        return word.strip(_punct_749)

    def test_bueno_question_mark(self):
        """'¿bueno?' → 'bueno' after strip."""
        self.assertEqual(self._strip_punct('¿bueno?'), 'bueno')

    def test_bueno_period(self):
        """'bueno.' → 'bueno' after strip."""
        self.assertEqual(self._strip_punct('bueno.'), 'bueno')

    def test_nombre_question(self):
        """'¿nombre?' → 'nombre' after strip."""
        self.assertEqual(self._strip_punct('¿nombre?'), 'nombre')

    def test_para_period(self):
        """'para.' → 'para' after strip."""
        self.assertEqual(self._strip_punct('para.'), 'para')

    def test_tardes_period(self):
        """'tardes.' → 'tardes' after strip."""
        self.assertEqual(self._strip_punct('tardes.'), 'tardes')

    def test_permiteme_period(self):
        """'permiteme.' → 'permiteme' after strip."""
        self.assertEqual(self._strip_punct('permiteme.'), 'permiteme')

    def test_clean_word_unchanged(self):
        """'hola' (no punct) stays 'hola'."""
        self.assertEqual(self._strip_punct('hola'), 'hola')


# ============================================================
# FIX 749A: New words in palabras_espanol_569
# ============================================================

class TestFix749ANewWords(unittest.TestCase):
    """FIX 749A: Verify new greeting/apology words in set."""

    def test_palabras_en_servidor(self):
        """FIX 749A words must be in servidor_llamadas.py."""
        servidor_path = os.path.join(os.path.dirname(__file__), '..', 'servidor_llamadas.py')
        with open(servidor_path, 'r', encoding='utf-8') as f:
            source = f.read()
        idx = source.find('palabras_espanol_569')
        section = source[idx:idx + 800]
        # FIX 749A new words
        for word in ['buenas', 'tardes', 'noches', 'perdon', 'disculpe', 'disculpa',
                     'nombre', 'digame', 'permiteme', 'para', 'dia', 'buen', 'buenos']:
            self.assertIn(f"'{word}'", section,
                          f"'{word}' debe estar en palabras_espanol_569")

    def test_punct_strip_en_servidor(self):
        """FIX 749A punctuation strip must be in servidor."""
        servidor_path = os.path.join(os.path.dirname(__file__), '..', 'servidor_llamadas.py')
        with open(servidor_path, 'r', encoding='utf-8') as f:
            source = f.read()
        self.assertIn('_punct_749', source)
        self.assertIn('.strip(_punct_749)', source)


# ============================================================
# FIX 749A: Word matching with punctuation
# ============================================================

class TestFix749AWordMatching(unittest.TestCase):
    """FIX 749A: Verify word matching works with punctuation."""

    def _check_reconocible(self, frase_limpia):
        """Replica FIX 569 + 749A logic."""
        palabras_espanol_569 = {'hola', 'bueno', 'buenas', 'buenos', 'buen', 'si', 'sí', 'no',
            'que', 'qué', 'como', 'cómo', 'quien', 'quién', 'donde', 'dónde',
            'esta', 'está', 'aqui', 'aquí', 'mande', 'diga', 'oiga', 'por', 'favor', 'gracias',
            'espere', 'momento', 'listo', 'ya', 'voy', 'estoy', 'el', 'la',
            'encargado', 'ferreteria', 'ferretería', 'marca', 'empresa', 'negocio', 'interesa',
            'tardes', 'noches', 'dias', 'perdon', 'perdón', 'disculpe', 'disculpa', 'nombre',
            'digame', 'permiteme', 'para', 'dia'}
        _punct_749 = '¿?¡!.,;:()'
        palabras = [w.strip(_punct_749) for w in frase_limpia.lower().split()]
        return any(p in palabras_espanol_569 for p in palabras) if palabras else False

    def test_bueno_question(self):
        """'¿bueno?' now matches (FIX 749A strips punct)."""
        self.assertTrue(self._check_reconocible('¿bueno?'))

    def test_bueno_period(self):
        """'bueno.' now matches."""
        self.assertTrue(self._check_reconocible('bueno.'))

    def test_buenas_tardes_period(self):
        """'buenas tardes.' now matches."""
        self.assertTrue(self._check_reconocible('buenas tardes.'))

    def test_buenas_tardes_permíteme(self):
        """'buenas tardes Buenas tardes. Permíteme.' now matches."""
        self.assertTrue(self._check_reconocible('buenas tardes buenas tardes. permiteme.'))

    def test_nombre_question(self):
        """'¿nombre?' now matches."""
        self.assertTrue(self._check_reconocible('¿nombre?'))

    def test_para_period(self):
        """'para.' now matches."""
        self.assertTrue(self._check_reconocible('para.'))

    def test_perdon_buenas_tardes(self):
        """'perdón, muy buenas tardes.' matches."""
        self.assertTrue(self._check_reconocible('perdón, muy buenas tardes.'))


# ============================================================
# FIX 749B: Strong signal bypasses FIX 569
# ============================================================

class TestFix749BStrongSignalBypass(unittest.TestCase):
    """FIX 749B: Strong signals bypass tiene_palabras_reconocibles check."""

    def test_gate_code_present(self):
        """FIX 749B gate condition must be in servidor."""
        servidor_path = os.path.join(os.path.dirname(__file__), '..', 'servidor_llamadas.py')
        with open(servidor_path, 'r', encoding='utf-8') as f:
            source = f.read()
        self.assertIn('FIX 749B', source)
        self.assertIn('tiene_senal_fuerte or', source)

    def test_strong_signal_bypasses_569(self):
        """Strong signal + tiene_palabras=False → gate PASSES."""
        tiene_senal_fuerte = True
        tiene_senal_debil = False
        cliente_volvio = True
        tiene_palabras_reconocibles = False  # Would have blocked before FIX 749B
        frase_limpia = "buenas tardes."

        # FIX 749B gate
        _senal_detectada_745 = tiene_senal_fuerte or tiene_senal_debil
        gate = cliente_volvio and (tiene_senal_fuerte or ((_senal_detectada_745 or len(frase_limpia) > 10) and tiene_palabras_reconocibles))
        self.assertTrue(gate, "Strong signal must bypass FIX 569 gate")

    def test_weak_signal_still_needs_569(self):
        """Weak signal + tiene_palabras=False → gate FAILS."""
        tiene_senal_fuerte = False
        tiene_senal_debil = True
        cliente_volvio = True
        tiene_palabras_reconocibles = False
        frase_limpia = "¿bueno?"

        _senal_detectada_745 = tiene_senal_fuerte or tiene_senal_debil
        gate = cliente_volvio and (tiene_senal_fuerte or ((_senal_detectada_745 or len(frase_limpia) > 10) and tiene_palabras_reconocibles))
        self.assertFalse(gate, "Weak signal without reconocible words should fail (but 749A fixes the words)")

    def test_weak_signal_with_749a_fix(self):
        """Weak signal + tiene_palabras=True (749A fix) → gate PASSES."""
        tiene_senal_fuerte = False
        tiene_senal_debil = True
        cliente_volvio = True
        tiene_palabras_reconocibles = True  # Now True thanks to FIX 749A punct strip
        frase_limpia = "¿bueno?"

        _senal_detectada_745 = tiene_senal_fuerte or tiene_senal_debil
        gate = cliente_volvio and (tiene_senal_fuerte or ((_senal_detectada_745 or len(frase_limpia) > 10) and tiene_palabras_reconocibles))
        self.assertTrue(gate, "Weak signal + reconocible (749A) must pass gate")

    def test_no_signal_timeout_still_needs_len(self):
        """No signal (timeout only) + short text → gate FAILS."""
        tiene_senal_fuerte = False
        tiene_senal_debil = False
        cliente_volvio = True  # via timeout
        tiene_palabras_reconocibles = True
        frase_limpia = "mmm"

        _senal_detectada_745 = tiene_senal_fuerte or tiene_senal_debil
        gate = cliente_volvio and (tiene_senal_fuerte or ((_senal_detectada_745 or len(frase_limpia) > 10) and tiene_palabras_reconocibles))
        self.assertFalse(gate, "No signal + short text must fail even with reconocible")


# ============================================================
# FIX 749: Integration - BRUCE2322 scenario
# ============================================================

class TestFix749IntegrationBRUCE2322(unittest.TestCase):
    """FIX 749: Full scenario simulation for BRUCE2322."""

    def _simulate_712a_749(self, speech_result):
        """Simulate FIX 712A + 749A + 749B gate logic."""
        frase_limpia = speech_result.strip().lower()

        # FIX 712A normalize
        _fl_712 = frase_limpia
        for a, b in [('á','a'),('é','e'),('í','i'),('ó','o'),('ú','u'),('ü','u'),('ñ','n')]:
            _fl_712 = _fl_712.replace(a, b)
        for c in '¿?¡!.,;:()':
            _fl_712 = _fl_712.replace(c, '')
        _fl_712 = _fl_712.strip()

        frases_fuertes = ['buenas tardes', 'buenas noches', 'muy buenas', 'buen dia',
                          'perdon', 'disculpe', 'disculpa',
                          'encargado', 'ferreteria', 'nioval', 'no esta', 'oiga', 'mire',
                          'anote', 'apunte']
        frases_debiles = ['bueno', 'hola', 'si', 'diga', 'digame']

        tiene_senal_fuerte = any(f in _fl_712 for f in frases_fuertes)
        tiene_senal_debil = any(f in _fl_712 for f in frases_debiles)
        texto_corto_712 = len(_fl_712) < 25
        tiene_senal_debil = tiene_senal_debil and texto_corto_712

        cliente_volvio = tiene_senal_fuerte or tiene_senal_debil

        # FIX 569 + 749A
        palabras_espanol_569 = {'hola', 'bueno', 'buenas', 'buenos', 'buen', 'si', 'sí', 'no',
            'tardes', 'noches', 'dias', 'perdon', 'disculpe', 'disculpa', 'nombre',
            'digame', 'permiteme', 'para', 'dia', 'mande', 'diga', 'oiga',
            'encargado', 'ferreteria', 'marca', 'empresa', 'negocio', 'interesa',
            'esta', 'aqui', 'que', 'como', 'donde', 'por', 'favor', 'gracias',
            'espere', 'momento', 'listo', 'ya', 'voy', 'estoy', 'el', 'la'}
        _punct_749 = '¿?¡!.,;:()'
        palabras = [w.strip(_punct_749) for w in frase_limpia.split()]
        tiene_palabras = any(p in palabras_espanol_569 for p in palabras) if palabras else False

        # FIX 749B gate
        _senal_detectada_745 = tiene_senal_fuerte or tiene_senal_debil
        gate_passes = cliente_volvio and (tiene_senal_fuerte or ((_senal_detectada_745 or len(frase_limpia) > 10) and tiene_palabras))

        return gate_passes

    def test_buenas_tardes_period(self):
        """BRUCE2322/2326: 'Buenas tardes.' must exit wait mode."""
        self.assertTrue(self._simulate_712a_749('Buenas tardes.'))

    def test_bueno_question(self):
        """BRUCE2322: '¿Bueno?' must exit wait mode."""
        self.assertTrue(self._simulate_712a_749('¿Bueno?'))

    def test_bueno_period(self):
        """BRUCE2322: 'Bueno.' must exit wait mode."""
        self.assertTrue(self._simulate_712a_749('Bueno.'))

    def test_nombre_question(self):
        """BRUCE2322: '¿Nombre?' must NOT exit (not in signal lists)."""
        self.assertFalse(self._simulate_712a_749('¿Nombre?'))

    def test_perdon_buenas_tardes(self):
        """BRUCE2316: 'Perdón, muy buenas tardes.' must exit wait mode."""
        self.assertTrue(self._simulate_712a_749('Perdón, muy buenas tardes.'))

    def test_buenas_tardes_permiteme(self):
        """'buenas tardes Buenas tardes. Permíteme.' must exit."""
        self.assertTrue(self._simulate_712a_749('buenas tardes Buenas tardes. Permíteme.'))


# ============================================================
# FIX 750: GPT eval false positive
# ============================================================

class TestFix750GPTEvalFalsePositive(unittest.TestCase):
    """FIX 750: 'Sí, bueno?' recognized as connection check in GPT eval."""

    def test_fix_750_in_focused_prompt(self):
        """FIX 750 must be in focused prompt (short calls)."""
        import bug_detector
        # Get the focused prompt source
        import inspect
        source = inspect.getsource(bug_detector)
        # Find OPORTUNIDAD_PERDIDA in focused prompt section
        idx_focused = source.find('OPORTUNIDAD_PERDIDA: Cliente mostró interés claro')
        section = source[idx_focused:idx_focused + 500]
        self.assertIn('FIX 750', section)
        self.assertIn('bueno', section.lower())

    def test_fix_750_in_full_prompt(self):
        """FIX 750 must be in full prompt (normal calls)."""
        import bug_detector
        import inspect
        source = inspect.getsource(bug_detector)
        idx_full = source.find('OPORTUNIDAD_PERDIDA: Cliente dijo explicitamente')
        section = source[idx_full:idx_full + 500]
        self.assertIn('FIX 750', section)
        self.assertIn('bueno', section.lower())


if __name__ == "__main__":
    unittest.main()
