"""
Tests para FIX 902-905: Correcciones de produccion 2026-03-05 (post-deploy).

FIX 902: Callback time expandido ("si gusta hablar por ahi de las seis")
FIX 903: GPT eval false positive - orden temporal + "Digame" != encargado
FIX 904: ANOTHER_BRANCH expandido ("area de compras esta en otro")
FIX 905: Buzon de voz expandido ("la persona con la que intentas comunicarte")
"""

import sys
import os
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fsm_engine import (
    classify_intent, FSMIntent, FSMContext, FSMState,
)


# ============================================================
# FIX 902: Callback time expandido
# ============================================================

class TestFix902CallbackExpanded(unittest.TestCase):
    """BRUCE2596: 'si gusta hablar por ahi de las seis' no detectado como CALLBACK."""

    def test_si_gusta_hablar_por_ahi_de_las(self):
        ctx = FSMContext()
        intent = classify_intent("Si gusta hablar por ahi de las seis de la tarde.",
                                 ctx, FSMState.BUSCANDO_ENCARGADO)
        self.assertEqual(intent, FSMIntent.CALLBACK)

    def test_por_ahi_de_las_nueve(self):
        ctx = FSMContext()
        intent = classify_intent("Por ahi de las nueve.", ctx, FSMState.BUSCANDO_ENCARGADO)
        self.assertEqual(intent, FSMIntent.CALLBACK)

    def test_gusta_hablar_manana(self):
        ctx = FSMContext()
        intent = classify_intent("Si gusta hablar manana.", ctx, FSMState.BUSCANDO_ENCARGADO)
        self.assertEqual(intent, FSMIntent.CALLBACK)

    def test_si_gusta_llamar_mas_tarde(self):
        ctx = FSMContext()
        intent = classify_intent("Si gusta llamar mas tarde.", ctx, FSMState.BUSCANDO_ENCARGADO)
        self.assertEqual(intent, FSMIntent.CALLBACK)

    def test_existing_callback_a_las_still_works(self):
        """Existing 'a las' pattern still works."""
        ctx = FSMContext()
        intent = classify_intent("Llame a las tres.", ctx, FSMState.BUSCANDO_ENCARGADO)
        self.assertEqual(intent, FSMIntent.CALLBACK)


# ============================================================
# FIX 903: GPT eval false positive
# ============================================================

class TestFix903GPTEvalFalsePositive(unittest.TestCase):
    """BRUCE2594/2596: GPT eval false positives por orden temporal y Digame."""

    def test_gpt_eval_prompt_has_temporal_order_fix(self):
        """Verificar que el prompt GPT tiene FIX 903 sobre orden temporal."""
        from bug_detector import _GPT_EVAL_PROMPT
        self.assertIn('FIX 903', _GPT_EVAL_PROMPT)
        self.assertIn('ORDEN TEMPORAL', _GPT_EVAL_PROMPT)

    def test_gpt_eval_prompt_digame_not_encargado(self):
        """Verificar que el prompt GPT aclara que Digame != encargado."""
        from bug_detector import _GPT_EVAL_PROMPT
        self.assertIn('Digame', _GPT_EVAL_PROMPT)
        self.assertIn('NO es identificarse como encargado', _GPT_EVAL_PROMPT)

    def test_ivr_prefilter_has_voicemail(self):
        """FIX 905: Pre-filtro IVR incluye buzon de voz."""
        import bug_detector
        source = open(bug_detector.__file__, 'r', encoding='utf-8').read()
        self.assertIn('la persona con la que intent', source)


# ============================================================
# FIX 904: ANOTHER_BRANCH expandido
# ============================================================

class TestFix904AnotherBranchExpanded(unittest.TestCase):
    """BRUCE2585: 'el area de compras esta en otro' no detectado."""

    def test_area_compras_en_otro(self):
        ctx = FSMContext()
        intent = classify_intent("El area de compras esta en otro edificio.",
                                 ctx, FSMState.BUSCANDO_ENCARGADO)
        self.assertEqual(intent, FSMIntent.ANOTHER_BRANCH)

    def test_compras_esta_en_otro_lado(self):
        ctx = FSMContext()
        intent = classify_intent("Compras esta en otro lado.", ctx, FSMState.BUSCANDO_ENCARGADO)
        self.assertEqual(intent, FSMIntent.ANOTHER_BRANCH)

    def test_se_comunica_a_una_tienda(self):
        ctx = FSMContext()
        intent = classify_intent("Se comunica a una tienda, el area de compras esta en otro.",
                                 ctx, FSMState.BUSCANDO_ENCARGADO)
        self.assertEqual(intent, FSMIntent.ANOTHER_BRANCH)

    def test_esta_comunicando_a_una_tienda(self):
        ctx = FSMContext()
        intent = classify_intent("Se esta comunicando a una tienda.",
                                 ctx, FSMState.BUSCANDO_ENCARGADO)
        self.assertEqual(intent, FSMIntent.ANOTHER_BRANCH)

    def test_existing_otra_sucursal_still_works(self):
        ctx = FSMContext()
        intent = classify_intent("No es aqui, es otra sucursal.",
                                 ctx, FSMState.BUSCANDO_ENCARGADO)
        # "no es aqui" matches WRONG_NUMBER before ANOTHER_BRANCH - both are valid redirects
        self.assertIn(intent, (FSMIntent.ANOTHER_BRANCH, FSMIntent.WRONG_NUMBER))


# ============================================================
# FIX 905: Buzon de voz expandido
# ============================================================

class TestFix905VoicemailExpanded(unittest.TestCase):
    """BRUCE2584: 'La persona con la que intentas comunicarte' no detectado como buzon."""

    def test_detector_ivr_has_persona_pattern(self):
        from detector_ivr import DetectorIVR
        d = DetectorIVR()
        result = d.analizar_respuesta(
            "La persona con la que intentas comunicarte no esta disponible.",
            es_primera_respuesta=True,
        )
        self.assertTrue(result['es_ivr'])

    def test_detector_ivr_graba_tu_mensaje(self):
        from detector_ivr import DetectorIVR
        d = DetectorIVR()
        result = d.analizar_respuesta(
            "Graba tu mensaje despues del tono.",
            es_primera_respuesta=True,
        )
        self.assertTrue(result['es_ivr'])

    def test_detector_ivr_puedes_colgar(self):
        from detector_ivr import DetectorIVR
        d = DetectorIVR()
        result = d.analizar_respuesta(
            "Puedes colgar cuando hayas terminado de grabarlo.",
            es_primera_respuesta=True,
        )
        self.assertTrue(result['es_ivr'])

    def test_detector_ivr_existing_grabe_su_mensaje_still_works(self):
        from detector_ivr import DetectorIVR
        d = DetectorIVR()
        result = d.analizar_respuesta(
            "Grabe su mensaje despues del tono.",
            es_primera_respuesta=True,
        )
        self.assertTrue(result['es_ivr'])


if __name__ == "__main__":
    unittest.main()
