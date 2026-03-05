"""
Tests para FIX 888-890: ANOTHER_BRANCH patterns + CONTINUATION vs MANAGER_ABSENT priority + fijese que no.

FIX 888: BRUCE2580 - "ahi te comunican a compras" / "comunicarte a matriz" -> ANOTHER_BRANCH
FIX 889: BRUCE2596 - "No se encuentra en este momento," -> MANAGER_ABSENT (no CONTINUATION)
FIX 890: BRUCE2621 - "Digame. Fijese que no." -> MANAGER_ABSENT
"""
import unittest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fsm_engine import classify_intent, FSMIntent, FSMState, FSMContext


class TestFix888AnotherBranch(unittest.TestCase):
    """FIX 888: ANOTHER_BRANCH patterns faltantes."""

    def test_comunican_a_compras(self):
        """BRUCE2580: 'ahi te comunican a compras' -> TRANSFER (FIX 896 handles this)."""
        ctx = FSMContext()
        result = classify_intent("ahi te comunican a compras", ctx, FSMState.BUSCANDO_ENCARGADO)
        self.assertEqual(result, FSMIntent.TRANSFER)

    def test_comunicarte_a_matriz(self):
        """BRUCE2580: 'si gustas comunicarte a matriz' -> ANOTHER_BRANCH."""
        ctx = FSMContext()
        result = classify_intent("si gustas comunicarte a matriz", ctx, FSMState.BUSCANDO_ENCARGADO)
        self.assertEqual(result, FSMIntent.ANOTHER_BRANCH)

    def test_te_comunican_a(self):
        """'te comunican' matches TRANSFER (FIX 896), which is correct."""
        ctx = FSMContext()
        result = classify_intent("ahi te comunican a la oficina", ctx, FSMState.BUSCANDO_ENCARGADO)
        self.assertEqual(result, FSMIntent.TRANSFER)

    def test_comunicate_a_la_sucursal(self):
        ctx = FSMContext()
        result = classify_intent("comunicate a la sucursal principal", ctx, FSMState.BUSCANDO_ENCARGADO)
        self.assertEqual(result, FSMIntent.ANOTHER_BRANCH)

    def test_habla_a_compras(self):
        ctx = FSMContext()
        result = classify_intent("habla a compras directamente", ctx, FSMState.BUSCANDO_ENCARGADO)
        self.assertEqual(result, FSMIntent.ANOTHER_BRANCH)

    def test_comunicar_a_matriz(self):
        ctx = FSMContext()
        result = classify_intent("tienes que comunicar a matriz", ctx, FSMState.BUSCANDO_ENCARGADO)
        self.assertEqual(result, FSMIntent.ANOTHER_BRANCH)

    # Verify existing patterns still work
    def test_otra_sucursal_still_works(self):
        ctx = FSMContext()
        result = classify_intent("eso es en otra sucursal", ctx, FSMState.BUSCANDO_ENCARGADO)
        self.assertEqual(result, FSMIntent.ANOTHER_BRANCH)

    def test_hablar_a_la_sucursal_still_works(self):
        ctx = FSMContext()
        result = classify_intent("tiene que hablar a la sucursal", ctx, FSMState.BUSCANDO_ENCARGADO)
        self.assertEqual(result, FSMIntent.ANOTHER_BRANCH)

    def test_another_branch_comunicarte_a_matriz(self):
        """ANOTHER_BRANCH: 'comunicarte a matriz' -> ANOTHER_BRANCH (not transfer)."""
        ctx = FSMContext()
        result = classify_intent("si gustas comunicarte a matriz por favor", ctx, FSMState.BUSCANDO_ENCARGADO)
        self.assertEqual(result, FSMIntent.ANOTHER_BRANCH)


class TestFix889ContinuationOverride(unittest.TestCase):
    """FIX 889: MANAGER_ABSENT debe tener prioridad sobre CONTINUATION cuando texto tiene coma."""

    def test_no_se_encuentra_con_coma(self):
        """BRUCE2596: 'No se encuentra en este momento,' -> MANAGER_ABSENT (no CONTINUATION)."""
        ctx = FSMContext()
        result = classify_intent(
            "No se encuentra en este momento,",
            ctx, FSMState.BUSCANDO_ENCARGADO
        )
        self.assertEqual(result, FSMIntent.MANAGER_ABSENT)

    def test_no_esta_con_coma(self):
        """'No esta ahorita,' -> MANAGER_ABSENT."""
        ctx = FSMContext()
        result = classify_intent("No esta ahorita,", ctx, FSMState.BUSCANDO_ENCARGADO)
        self.assertEqual(result, FSMIntent.MANAGER_ABSENT)

    def test_salio_con_coma(self):
        """'Salio a comer,' -> MANAGER_ABSENT."""
        ctx = FSMContext()
        result = classify_intent("Salio a comer,", ctx, FSMState.BUSCANDO_ENCARGADO)
        self.assertEqual(result, FSMIntent.MANAGER_ABSENT)

    def test_hora_de_comida_con_coma(self):
        ctx = FSMContext()
        result = classify_intent("Esta en su hora de comida,", ctx, FSMState.BUSCANDO_ENCARGADO)
        self.assertEqual(result, FSMIntent.MANAGER_ABSENT)

    def test_no_vino_con_coma(self):
        ctx = FSMContext()
        result = classify_intent("No vino hoy,", ctx, FSMState.BUSCANDO_ENCARGADO)
        self.assertEqual(result, FSMIntent.MANAGER_ABSENT)

    def test_no_llego_con_coma(self):
        ctx = FSMContext()
        result = classify_intent("No llego todavia,", ctx, FSMState.BUSCANDO_ENCARGADO)
        self.assertEqual(result, FSMIntent.MANAGER_ABSENT)

    def test_anda_fuera_con_coma(self):
        ctx = FSMContext()
        result = classify_intent("Anda fuera ahorita,", ctx, FSMState.BUSCANDO_ENCARGADO)
        self.assertEqual(result, FSMIntent.MANAGER_ABSENT)

    # Verify CONTINUATION still works for non-manager_absent texts
    def test_continuation_still_works_normal(self):
        """Texto normal con coma sigue siendo CONTINUATION."""
        ctx = FSMContext()
        result = classify_intent("Pues fijese que,", ctx, FSMState.BUSCANDO_ENCARGADO)
        self.assertEqual(result, FSMIntent.CONTINUATION)

    def test_continuation_still_works_bueno(self):
        ctx = FSMContext()
        result = classify_intent("Si bueno pues,", ctx, FSMState.BUSCANDO_ENCARGADO)
        self.assertEqual(result, FSMIntent.CONTINUATION)

    # Verify REJECT_DATA still works with comma
    def test_reject_data_still_works(self):
        """'No tengo WhatsApp,' sigue siendo REJECT_DATA (no CONTINUATION)."""
        ctx = FSMContext()
        result = classify_intent("No tengo WhatsApp,", ctx, FSMState.BUSCANDO_ENCARGADO)
        self.assertEqual(result, FSMIntent.REJECT_DATA)


class TestFix888889NoRegressions(unittest.TestCase):
    """Verify no regressions from FIX 888-889."""

    def test_no_esta_sin_coma(self):
        ctx = FSMContext()
        result = classify_intent("No esta", ctx, FSMState.BUSCANDO_ENCARGADO)
        self.assertEqual(result, FSMIntent.MANAGER_ABSENT)

    def test_soy_yo_still_works(self):
        ctx = FSMContext()
        result = classify_intent("Soy yo", ctx, FSMState.BUSCANDO_ENCARGADO)
        self.assertEqual(result, FSMIntent.MANAGER_PRESENT)

    def test_no_me_interesa_still_works(self):
        ctx = FSMContext()
        result = classify_intent("No me interesa", ctx, FSMState.BUSCANDO_ENCARGADO)
        self.assertEqual(result, FSMIntent.NO_INTEREST)

    def test_si_still_confirmation(self):
        ctx = FSMContext()
        result = classify_intent("Si", ctx, FSMState.BUSCANDO_ENCARGADO)
        self.assertEqual(result, FSMIntent.CONFIRMATION)

    def test_digame_manager_present(self):
        """FIX 884 still works."""
        ctx = FSMContext()
        ctx.encargado_preguntado = True
        result = classify_intent("Digame.", ctx, FSMState.BUSCANDO_ENCARGADO)
        self.assertEqual(result, FSMIntent.MANAGER_PRESENT)


class TestFix890FijeseQueNo(unittest.TestCase):
    """FIX 890: BRUCE2621 - 'fijese que no' / 'fijate que no' -> MANAGER_ABSENT."""

    def test_fijese_que_no_standalone(self):
        """'Fijese que no' alone -> MANAGER_ABSENT when encargado_preguntado."""
        ctx = FSMContext()
        ctx.encargado_preguntado = True
        result = classify_intent("Fijese que no.", ctx, FSMState.BUSCANDO_ENCARGADO)
        self.assertEqual(result, FSMIntent.MANAGER_ABSENT)

    def test_fijate_que_no_standalone(self):
        ctx = FSMContext()
        ctx.encargado_preguntado = True
        result = classify_intent("Fijate que no.", ctx, FSMState.BUSCANDO_ENCARGADO)
        self.assertEqual(result, FSMIntent.MANAGER_ABSENT)

    def test_fijese_que_no_in_longer_text(self):
        """'fijese que no' in longer sentence -> MANAGER_ABSENT."""
        ctx = FSMContext()
        result = classify_intent("Pues fijese que no esta ahorita", ctx, FSMState.BUSCANDO_ENCARGADO)
        self.assertEqual(result, FSMIntent.MANAGER_ABSENT)

    def test_fijate_que_no_in_longer_text(self):
        ctx = FSMContext()
        result = classify_intent("Fijate que no vino hoy", ctx, FSMState.BUSCANDO_ENCARGADO)
        self.assertEqual(result, FSMIntent.MANAGER_ABSENT)

    def test_fijese_que_no_sin_encargado_preguntado(self):
        """'fijese que no' in longer text works even without encargado_preguntado."""
        ctx = FSMContext()
        ctx.encargado_preguntado = False
        result = classify_intent("Pues fijese que no se encuentra", ctx, FSMState.BUSCANDO_ENCARGADO)
        self.assertEqual(result, FSMIntent.MANAGER_ABSENT)

    def test_no_standalone_with_encargado_preguntado(self):
        """'no' alone with encargado_preguntado -> MANAGER_ABSENT."""
        ctx = FSMContext()
        ctx.encargado_preguntado = True
        result = classify_intent("No", ctx, FSMState.BUSCANDO_ENCARGADO)
        self.assertEqual(result, FSMIntent.MANAGER_ABSENT)

    def test_pues_no_with_encargado_preguntado(self):
        ctx = FSMContext()
        ctx.encargado_preguntado = True
        result = classify_intent("Pues no", ctx, FSMState.BUSCANDO_ENCARGADO)
        self.assertEqual(result, FSMIntent.MANAGER_ABSENT)

    def test_no_fijese_with_encargado_preguntado(self):
        """'no fijese' with encargado_preguntado -> MANAGER_ABSENT."""
        ctx = FSMContext()
        ctx.encargado_preguntado = True
        result = classify_intent("No fijese", ctx, FSMState.BUSCANDO_ENCARGADO)
        self.assertEqual(result, FSMIntent.MANAGER_ABSENT)

    # Verify no regressions - "fijese que" without "no" should NOT be manager_absent
    def test_fijese_que_si_not_manager_absent(self):
        """'Fijese que si' should NOT be MANAGER_ABSENT."""
        ctx = FSMContext()
        ctx.encargado_preguntado = True
        result = classify_intent("Fijese que si", ctx, FSMState.BUSCANDO_ENCARGADO)
        self.assertNotEqual(result, FSMIntent.MANAGER_ABSENT)


if __name__ == '__main__':
    unittest.main()
