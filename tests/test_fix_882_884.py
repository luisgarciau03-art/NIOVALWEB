"""
Tests para FIX 882-884: Mejoras en classify_intent del FSM.

FIX 882: Callback/manager_absent patterns faltantes
FIX 883: Identity patterns faltantes ("de parte de quién")
FIX 884: "Dígame" en BUSCANDO_ENCARGADO → MANAGER_PRESENT (no INTEREST)
FIX 884B: "Dígame. Fíjese que no." → no INTEREST (contiene negación)
"""
import unittest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fsm_engine import classify_intent, FSMIntent, FSMState, FSMContext


class TestFix882CallbackPatterns(unittest.TestCase):
    """FIX 882: Patterns de callback/manager_absent faltantes."""

    def test_salieron_manager_absent(self):
        """BRUCE2625: 'salieron' debe ser MANAGER_ABSENT."""
        ctx = FSMContext()
        ctx.encargado_preguntado = True
        result = classify_intent("salieron", ctx, FSMState.BUSCANDO_ENCARGADO)
        self.assertEqual(result, FSMIntent.MANAGER_ABSENT)

    def test_si_gustas_marcar_en_una_hora_salieron(self):
        """BRUCE2625: Frase completa con 'salieron' → MANAGER_ABSENT (checked first)."""
        ctx = FSMContext()
        ctx.encargado_preguntado = True
        result = classify_intent("Si gustas marcar en una hora, salieron", ctx, FSMState.BUSCANDO_ENCARGADO)
        self.assertEqual(result, FSMIntent.MANAGER_ABSENT)

    def test_en_una_hora_callback(self):
        """'en una hora' debe ser CALLBACK."""
        ctx = FSMContext()
        result = classify_intent("Llámame en una hora", ctx, FSMState.BUSCANDO_ENCARGADO)
        self.assertEqual(result, FSMIntent.CALLBACK)

    def test_hora_de_comida_manager_absent(self):
        """'hora de comida' debe ser MANAGER_ABSENT."""
        ctx = FSMContext()
        result = classify_intent("Están en su hora de comida", ctx, FSMState.BUSCANDO_ENCARGADO)
        self.assertEqual(result, FSMIntent.MANAGER_ABSENT)

    def test_fueron_a_comer_manager_absent(self):
        ctx = FSMContext()
        result = classify_intent("Fueron a comer", ctx, FSMState.BUSCANDO_ENCARGADO)
        self.assertEqual(result, FSMIntent.MANAGER_ABSENT)

    def test_si_gustas_marcar_callback(self):
        """'si gustas marcar' (tuteo) debe ser CALLBACK."""
        ctx = FSMContext()
        result = classify_intent("Si gustas marcar más tarde", ctx, FSMState.BUSCANDO_ENCARGADO)
        self.assertEqual(result, FSMIntent.CALLBACK)

    def test_si_gustas_llamar_callback(self):
        ctx = FSMContext()
        result = classify_intent("Si gustas llamar después", ctx, FSMState.BUSCANDO_ENCARGADO)
        self.assertEqual(result, FSMIntent.CALLBACK)

    def test_no_se_encuentre_manager_absent(self):
        """BRUCE2630: 'no se encuentre' (subjuntivo) → MANAGER_ABSENT."""
        ctx = FSMContext()
        result = classify_intent("O no se encuentre", ctx, FSMState.BUSCANDO_ENCARGADO)
        self.assertEqual(result, FSMIntent.MANAGER_ABSENT)

    def test_en_un_rato_callback(self):
        ctx = FSMContext()
        result = classify_intent("Llámame en un rato", ctx, FSMState.BUSCANDO_ENCARGADO)
        self.assertEqual(result, FSMIntent.CALLBACK)

    def test_esta_fuera_manager_absent(self):
        ctx = FSMContext()
        result = classify_intent("Está fuera ahorita", ctx, FSMState.BUSCANDO_ENCARGADO)
        self.assertEqual(result, FSMIntent.MANAGER_ABSENT)

    def test_estan_comiendo_manager_absent(self):
        ctx = FSMContext()
        result = classify_intent("Están comiendo", ctx, FSMState.BUSCANDO_ENCARGADO)
        self.assertEqual(result, FSMIntent.MANAGER_ABSENT)


class TestFix883IdentityPatterns(unittest.TestCase):
    """FIX 883: 'de parte de quién' y variantes no se detectaban."""

    def test_de_parte_de_quien(self):
        """BRUCE2630/2634: 'de parte de quién' → IDENTITY."""
        ctx = FSMContext()
        result = classify_intent("¿De parte de quién?", ctx, FSMState.BUSCANDO_ENCARGADO)
        self.assertEqual(result, FSMIntent.IDENTITY)

    def test_de_parte_de(self):
        ctx = FSMContext()
        result = classify_intent("De parte de quién, disculpe", ctx, FSMState.PITCH)
        self.assertEqual(result, FSMIntent.IDENTITY)

    def test_quien_eres(self):
        ctx = FSMContext()
        result = classify_intent("¿Quién eres?", ctx, FSMState.BUSCANDO_ENCARGADO)
        self.assertEqual(result, FSMIntent.IDENTITY)

    def test_como_te_llamas(self):
        ctx = FSMContext()
        result = classify_intent("¿Cómo te llamas?", ctx, FSMState.BUSCANDO_ENCARGADO)
        self.assertEqual(result, FSMIntent.IDENTITY)

    def test_quien_me_habla(self):
        ctx = FSMContext()
        result = classify_intent("¿Quién me habla?", ctx, FSMState.BUSCANDO_ENCARGADO)
        self.assertEqual(result, FSMIntent.IDENTITY)

    def test_de_que_marca(self):
        ctx = FSMContext()
        result = classify_intent("¿De qué marca?", ctx, FSMState.PITCH)
        self.assertEqual(result, FSMIntent.IDENTITY)

    def test_de_que_compania(self):
        ctx = FSMContext()
        result = classify_intent("¿De qué compañía?", ctx, FSMState.PITCH)
        self.assertEqual(result, FSMIntent.IDENTITY)

    # Verify existing patterns still work
    def test_de_donde_llama_still_works(self):
        ctx = FSMContext()
        result = classify_intent("¿De dónde llama?", ctx, FSMState.BUSCANDO_ENCARGADO)
        self.assertEqual(result, FSMIntent.IDENTITY)

    def test_quien_habla_still_works(self):
        ctx = FSMContext()
        result = classify_intent("¿Quién habla?", ctx, FSMState.BUSCANDO_ENCARGADO)
        self.assertEqual(result, FSMIntent.IDENTITY)


class TestFix884DigameBuscandoEncargado(unittest.TestCase):
    """FIX 884: 'Dígame' en BUSCANDO_ENCARGADO → MANAGER_PRESENT (no INTEREST)."""

    def test_digame_buscando_encargado_manager_present(self):
        """BRUCE2619: 'Dígame' tras preguntar encargado → MANAGER_PRESENT → da pitch."""
        ctx = FSMContext()
        ctx.encargado_preguntado = True
        result = classify_intent("Dígame.", ctx, FSMState.BUSCANDO_ENCARGADO)
        self.assertEqual(result, FSMIntent.MANAGER_PRESENT)

    def test_si_digame_buscando_encargado_manager_present(self):
        ctx = FSMContext()
        ctx.encargado_preguntado = True
        result = classify_intent("Sí, dígame.", ctx, FSMState.BUSCANDO_ENCARGADO)
        self.assertEqual(result, FSMIntent.MANAGER_PRESENT)

    def test_mande_buscando_encargado_manager_present(self):
        ctx = FSMContext()
        ctx.encargado_preguntado = True
        result = classify_intent("Mande.", ctx, FSMState.BUSCANDO_ENCARGADO)
        self.assertEqual(result, FSMIntent.MANAGER_PRESENT)

    def test_adelante_buscando_encargado_manager_present(self):
        ctx = FSMContext()
        ctx.encargado_preguntado = True
        result = classify_intent("Adelante.", ctx, FSMState.BUSCANDO_ENCARGADO)
        self.assertEqual(result, FSMIntent.MANAGER_PRESENT)

    def test_digame_sin_encargado_preguntado_confirmation(self):
        """Sin encargado_preguntado → sigue siendo CONFIRMATION."""
        ctx = FSMContext()
        ctx.encargado_preguntado = False
        result = classify_intent("Dígame.", ctx, FSMState.BUSCANDO_ENCARGADO)
        self.assertEqual(result, FSMIntent.CONFIRMATION)

    def test_digame_en_otro_estado_confirmation(self):
        """En otro estado → sigue siendo CONFIRMATION."""
        ctx = FSMContext()
        ctx.encargado_preguntado = True
        result = classify_intent("Dígame.", ctx, FSMState.PITCH)
        self.assertEqual(result, FSMIntent.CONFIRMATION)

    def test_digame_en_encargado_presente_confirmation(self):
        """En ENCARGADO_PRESENTE → CONFIRMATION (ya tiene al encargado)."""
        ctx = FSMContext()
        ctx.encargado_preguntado = True
        result = classify_intent("Dígame.", ctx, FSMState.ENCARGADO_PRESENTE)
        self.assertEqual(result, FSMIntent.CONFIRMATION)


class TestFix884BDigameConNegacion(unittest.TestCase):
    """FIX 884B: 'Dígame. Fíjese que no.' NO debe ser INTEREST."""

    def test_digame_fijese_que_no_not_interest(self):
        """BRUCE2621: 'Dígame. Fíjese que no.' contiene negación → no INTEREST."""
        ctx = FSMContext()
        result = classify_intent("Dígame. Fíjese que no.", ctx, FSMState.BUSCANDO_ENCARGADO)
        self.assertNotEqual(result, FSMIntent.INTEREST)

    def test_digame_no_lo_tengo_not_interest(self):
        """'Dígame, no lo tengo' → no INTEREST."""
        ctx = FSMContext()
        result = classify_intent("Dígame, no lo tengo.", ctx, FSMState.BUSCANDO_ENCARGADO)
        self.assertNotEqual(result, FSMIntent.INTEREST)

    def test_digame_no_esta_not_interest(self):
        """'Dígame, no está' → MANAGER_ABSENT (no INTEREST)."""
        ctx = FSMContext()
        result = classify_intent("Dígame, no está.", ctx, FSMState.BUSCANDO_ENCARGADO)
        self.assertEqual(result, FSMIntent.MANAGER_ABSENT)

    def test_digame_solo_still_interest_as_substring(self):
        """'Cuénteme, dígame' (sin negación) → still matches interest patterns."""
        ctx = FSMContext()
        result = classify_intent("Cuénteme más", ctx, FSMState.BUSCANDO_ENCARGADO)
        self.assertEqual(result, FSMIntent.INTEREST)


class TestFix882884NoRegressions(unittest.TestCase):
    """Verify existing patterns still work after FIX 882-884."""

    def test_no_esta_still_manager_absent(self):
        ctx = FSMContext()
        result = classify_intent("No está", ctx, FSMState.BUSCANDO_ENCARGADO)
        self.assertEqual(result, FSMIntent.MANAGER_ABSENT)

    def test_soy_yo_still_manager_present(self):
        ctx = FSMContext()
        result = classify_intent("Soy yo", ctx, FSMState.BUSCANDO_ENCARGADO)
        self.assertEqual(result, FSMIntent.MANAGER_PRESENT)

    def test_no_me_interesa_still_no_interest(self):
        ctx = FSMContext()
        result = classify_intent("No me interesa", ctx, FSMState.BUSCANDO_ENCARGADO)
        self.assertEqual(result, FSMIntent.NO_INTEREST)

    def test_mas_tarde_still_callback(self):
        ctx = FSMContext()
        result = classify_intent("Llame más tarde", ctx, FSMState.BUSCANDO_ENCARGADO)
        self.assertEqual(result, FSMIntent.CALLBACK)

    def test_si_still_confirmation(self):
        ctx = FSMContext()
        result = classify_intent("Sí", ctx, FSMState.BUSCANDO_ENCARGADO)
        self.assertEqual(result, FSMIntent.CONFIRMATION)

    def test_bueno_still_verification(self):
        ctx = FSMContext()
        result = classify_intent("¿Bueno?", ctx, FSMState.BUSCANDO_ENCARGADO)
        self.assertEqual(result, FSMIntent.VERIFICATION)


if __name__ == '__main__':
    unittest.main()
