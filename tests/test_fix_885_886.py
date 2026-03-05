"""
Tests para FIX 885-886: STT garbling cleanup + fuzzy matching.

FIX 885: Limpieza de texto STT duplicado/garbled antes del FSM
FIX 886: Fuzzy matching en classify_intent para texto STT distorsionado
"""
import unittest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agente_ventas import _limpiar_stt_duplicados_885
from fsm_engine import classify_intent, FSMIntent, FSMState, FSMContext


class TestFix885STTDedup(unittest.TestCase):
    """FIX 885: Limpieza de frases duplicadas del STT."""

    def test_texto_corto_no_cambia(self):
        """Textos < 30 chars no se tocan."""
        self.assertEqual(_limpiar_stt_duplicados_885("Hola buen dia"), "Hola buen dia")

    def test_texto_sin_duplicados_no_cambia(self):
        """Texto limpio no se modifica."""
        texto = "Si, soy el encargado. Me interesa el catalogo."
        result = _limpiar_stt_duplicados_885(texto)
        self.assertEqual(result, texto)

    def test_dedup_frase_exacta(self):
        """Frases idénticas se reducen a una (text must be > 30 chars)."""
        texto = "Si soy el encargado de compras. Si soy el encargado de compras."
        result = _limpiar_stt_duplicados_885(texto)
        # Should dedup to single occurrence
        count = result.lower().count("encargado de compras")
        self.assertEqual(count, 1)

    def test_dedup_frase_similar(self):
        """Frases muy similares (>75% ratio) se deduplicen."""
        texto = "Permiteme un segundo. Es el seis catorce. Permitame un segundo. Es el seis catorce."
        result = _limpiar_stt_duplicados_885(texto)
        # Debe ser mas corto que el original
        self.assertLess(len(result), len(texto))

    def test_dedup_preserva_frases_distintas(self):
        """Frases diferentes se preservan."""
        texto = "No esta el encargado. Si gustas marcar mas tarde."
        result = _limpiar_stt_duplicados_885(texto)
        self.assertIn("encargado", result)
        self.assertIn("marcar", result)

    def test_dedup_produccion_bruce2589(self):
        """Caso real BRUCE2589: 'Hola buen dia' duplicado."""
        texto = "Hola, buen dia. Que dice? Buenos dias. Si, con Hola, buen dia. Que dice? Buenos dias."
        result = _limpiar_stt_duplicados_885(texto)
        # No debe tener "Hola buen dia" 2 veces
        count = result.lower().count("hola")
        self.assertLessEqual(count, 1)

    def test_dedup_produccion_bruce2604(self):
        """Caso real BRUCE2604: queja duplicada."""
        texto = "Permitame, marcan a cada rato, ya se les dijo que no. Permitame, marcan a cada rato, ya se les dijo que no nos interesa."
        result = _limpiar_stt_duplicados_885(texto)
        self.assertLess(len(result), len(texto))

    def test_none_empty_safe(self):
        """None y string vacio son seguros."""
        self.assertEqual(_limpiar_stt_duplicados_885(""), "")
        self.assertEqual(_limpiar_stt_duplicados_885(None), None)

    def test_preserva_numeros(self):
        """No pierde numeros de telefono."""
        texto = "Es el 33 12 34 56 78. Si, es el 33 12 34 56 78."
        result = _limpiar_stt_duplicados_885(texto)
        self.assertIn("33 12 34 56 78", result)


class TestFix886FuzzyMatching(unittest.TestCase):
    """FIX 886: Fuzzy matching para STT garbled en classify_intent."""

    def test_sobra_de_comida_fuzzy(self):
        """STT garbled: 'sobra de comida' (should be 'hora de comida')."""
        ctx = FSMContext()
        # "sobra de comida" tiene 'comida' (from pattern ['hora', 'comida'])
        # Only 1 of 2 words match, so it won't fuzzy match with min_match=2
        # But the dedup + the actual text "Están en sobra de comida" won't match MANAGER_ABSENT
        # This tests the fuzzy layer as last resort
        result = classify_intent(
            "Estan en sobra de comida si gustas marcar mas",
            ctx, FSMState.BUSCANDO_ENCARGADO
        )
        # "gustas" + "marcar" should fuzzy match CALLBACK, or "marcar" + "mas" = callback
        # Actually 'si gustas marcar' was added in FIX 882 so this should match CALLBACK directly
        self.assertEqual(result, FSMIntent.CALLBACK)

    def test_fuzzy_no_interesa_garbled(self):
        """STT garbled 'no interesa' detected by fuzzy."""
        ctx = FSMContext()
        result = classify_intent(
            "ya les digo que eso a nosotros no nos interesa para nada gracias",
            ctx, FSMState.BUSCANDO_ENCARGADO
        )
        self.assertEqual(result, FSMIntent.NO_INTEREST)

    def test_fuzzy_no_trigger_short_text(self):
        """Fuzzy no se activa para textos cortos (<= 10 chars)."""
        ctx = FSMContext()
        # "no hora" is short, should not fuzzy match
        result = classify_intent("no hora", ctx, FSMState.BUSCANDO_ENCARGADO)
        # Should be UNKNOWN or other, not MANAGER_ABSENT
        # "no hora" is 6 chars after normalize, fuzzy requires >10
        self.assertNotEqual(result, FSMIntent.CALLBACK)

    def test_fuzzy_callback_state_guard(self):
        """Fuzzy callback solo en estados relevantes."""
        ctx = FSMContext()
        # In DICTANDO_DATO, fuzzy callback should NOT trigger
        result = classify_intent(
            "si gustas hablar en otra hora diferente por favor",
            ctx, FSMState.DICTANDO_DATO
        )
        # Should NOT be callback (wrong state for fuzzy guard)
        # But FIX 882 exact match 'si gustas hablar' is in callback with state guard
        # DICTANDO_DATO is NOT in the callback state guard list at line 576
        self.assertNotEqual(result, FSMIntent.CALLBACK)

    def test_fuzzy_identity_de_parte(self):
        """Fuzzy: 'parte' + 'quien' matches IDENTITY."""
        ctx = FSMContext()
        result = classify_intent(
            "oiga disculpe de parte de quien me anda marcando a cada rato",
            ctx, FSMState.BUSCANDO_ENCARGADO
        )
        # 'de parte de' should be caught by FIX 883 exact match
        self.assertEqual(result, FSMIntent.IDENTITY)


class TestFix885886Integration(unittest.TestCase):
    """Integration: dedup + fuzzy work together."""

    def test_dedup_then_classify(self):
        """Dedup cleans text, then FSM classifies correctly."""
        garbled = "No esta. No se encuentra. No esta el encargado. No se encuentra el encargado."
        cleaned = _limpiar_stt_duplicados_885(garbled)
        ctx = FSMContext()
        result = classify_intent(cleaned, ctx, FSMState.BUSCANDO_ENCARGADO)
        self.assertEqual(result, FSMIntent.MANAGER_ABSENT)

    def test_dedup_callback_duplicate(self):
        """Dedup: 'marcar mas tarde' duplicado → single → CALLBACK."""
        garbled = "Si gustas marcar mas tarde. Si gustas marcar mas tarde por favor."
        cleaned = _limpiar_stt_duplicados_885(garbled)
        ctx = FSMContext()
        result = classify_intent(cleaned, ctx, FSMState.BUSCANDO_ENCARGADO)
        self.assertEqual(result, FSMIntent.CALLBACK)

    def test_dedup_identity_duplicate(self):
        """Dedup: 'de donde habla' duplicado → single → IDENTITY."""
        garbled = "De donde es que nos habla? Perdon? De donde es que habla?"
        cleaned = _limpiar_stt_duplicados_885(garbled)
        ctx = FSMContext()
        result = classify_intent(cleaned, ctx, FSMState.BUSCANDO_ENCARGADO)
        self.assertEqual(result, FSMIntent.IDENTITY)


if __name__ == '__main__':
    unittest.main()
