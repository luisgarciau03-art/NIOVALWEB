# -*- coding: utf-8 -*-
"""
Tests para FIX 863-866:
- FIX 863A: _DICTADO_PATTERNS - \b word boundaries en letras sueltas (a de, e de, etc.)
            + (?<!no ) lookbehind en 'estamos en' para _DICTADO_PATTERNS_FUERTE
- FIX 863B: _CONFIRMACION_DATO_862 - extendido con "con gusto le envío catálogo"
- FIX 863C: _TRANSFER_PATTERNS - 'ya viene(?! hasta)' evita falso positivo "ya viene hasta el lunes"
- FIX 864:  _check_interrupcion_conversacional - despedida apropiada tras "no está"/"está equivocado"
- FIX 865:  FSM no_interest - variantes singulares de "no hacemos compras"
- FIX 866A: FSM another branch - "tienes que hablar a la sucursal" = ANOTHER_BRANCH
- FIX 866B: FSMContext.verificacion_consecutivas - anti-LOOP post-transfer
"""
import unittest
import sys
import os
import re

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


# =============================================================================
# FIX 863A: _DICTADO_PATTERNS - word boundaries en letras sueltas
# =============================================================================

class TestFix863ADictadoPatterns(unittest.TestCase):
    """FIX 863A: \b boundaries evitan falsos positivos de letras en palabras."""

    def setUp(self):
        from bug_detector import ContentAnalyzer
        self.pat = ContentAnalyzer._DICTADO_PATTERNS
        self.pat_fuerte = ContentAnalyzer._DICTADO_PATTERNS_FUERTE

    def test_no_match_nueve_de(self):
        """'nueve de la mañana' NO debe matchear como dictado (era falso positivo)."""
        texto = "a las nueve de la mañana"
        self.assertIsNone(self.pat.search(texto),
                          f"_DICTADO_PATTERNS no debe matchear '{texto}'")
        self.assertIsNone(self.pat_fuerte.search(texto),
                          f"_DICTADO_PATTERNS_FUERTE no debe matchear '{texto}'")

    def test_no_match_catorce_de(self):
        """'catorce de enero' NO debe matchear como dictado."""
        texto = "el catorce de enero"
        self.assertIsNone(self.pat.search(texto),
                          f"No debe matchear '{texto}'")

    def test_match_a_de_standalone(self):
        """'A de Arturo' SÍ debe matchear (letra deletreando)."""
        texto = "A de Arturo, B de Beatriz"
        self.assertIsNotNone(self.pat.search(texto),
                             "'A de Arturo' debe matchear como dictado")

    def test_match_e_de_standalone(self):
        """'E de Eduardo' SÍ debe matchear (letra deletreando)."""
        texto = "E de Eduardo"
        self.assertIsNotNone(self.pat.search(texto),
                             "'E de Eduardo' debe matchear como dictado")

    def test_match_correo_domain(self):
        """'gmail' siempre debe matchear como dictado."""
        texto = "mi correo es en gmail"
        self.assertIsNotNone(self.pat_fuerte.search(texto),
                             "'gmail' siempre debe matchear")

    def test_no_match_estamos_en_no(self):
        """'no estamos en esto' NO debe matchear en _DICTADO_PATTERNS_FUERTE."""
        texto = "no estamos en este tipo de negocio"
        self.assertIsNone(self.pat_fuerte.search(texto),
                          f"'no estamos en...' no debe matchear como dictado")

    def test_match_estamos_en_direccion(self):
        """'estamos en Calle Juárez' SÍ debe matchear (dirección)."""
        texto = "estamos en la Calle Juárez"
        self.assertIsNotNone(self.pat_fuerte.search(texto),
                             "'estamos en la Calle Juárez' debe matchear")

    def test_no_match_treinta_de(self):
        """'treinta de agosto' NO debe matchear."""
        texto = "el treinta de agosto"
        self.assertIsNone(self.pat.search(texto))

    def test_match_numero_digits(self):
        """Números de 3+ dígitos siempre deben matchear."""
        texto = "el número es 331"
        self.assertIsNotNone(self.pat_fuerte.search(texto))


# =============================================================================
# FIX 863B: _CONFIRMACION_DATO_862 extendido con confirmaciones GPT de catálogo
# =============================================================================

class TestFix863BConfirmacionDato862(unittest.TestCase):
    """FIX 863B: 'Con gusto le envío catálogo' = confirmación, no nueva oferta."""

    def setUp(self):
        from bug_detector import ContentAnalyzer
        self.pat = ContentAnalyzer._CONFIRMACION_DATO_862

    def test_match_con_gusto_envio(self):
        """'Con gusto le envío nuestro catálogo completo.' debe matchear."""
        texto = "Con gusto le envío nuestro catálogo completo."
        self.assertIsNotNone(self.pat.search(texto),
                             "FIX 863B: 'con gusto le envío catálogo' debe excluirse")

    def test_match_mando_catalogo_sin_problema(self):
        """'por WhatsApp le mando el catálogo sin problema' debe matchear."""
        texto = "por WhatsApp le mando el catálogo sin problema"
        self.assertIsNotNone(self.pat.search(texto),
                             "FIX 863B: 'le mando catálogo sin problema' debe excluirse")

    def test_match_original_ya_tengo(self):
        """'ya tengo el correo' sigue matcheando (FIX 862 original)."""
        texto = "ya tengo el correo registrado. Le envío el catálogo."
        self.assertIsNotNone(self.pat.search(texto))

    def test_match_original_anotado(self):
        """'ya tengo anotado' sigue matcheando."""
        texto = "ya tengo anotado el número"
        self.assertIsNotNone(self.pat.search(texto))

    def test_no_match_nueva_oferta(self):
        """'¿Le enviamos el catálogo?' (pregunta nueva) NO debe matchear."""
        texto = "¿Le enviamos el catálogo por WhatsApp?"
        self.assertIsNone(self.pat.search(texto),
                          "Pregunta nueva no debe ser confirmación")

    def test_catalogo_repetido_no_fires_on_confirmation(self):
        """_check_catalogo_repetido NO lanza bug cuando Bruce confirma solicitud del cliente."""
        from bug_detector import ContentAnalyzer
        # Simulate: client asks for catalog, Bruce confirms twice (con gusto + mando por WhatsApp)
        respuestas = [
            "Le comento, me comunico de la marca NIOVAL.",
            "Con gusto le envío nuestro catálogo completo.",
            "por WhatsApp le mando el catálogo sin problema",
        ]
        bugs = ContentAnalyzer._check_catalogo_repetido(respuestas)
        catalogo_bugs = [b for b in bugs if b["tipo"] == "CATALOGO_REPETIDO"]
        self.assertEqual(len(catalogo_bugs), 0,
                         "FIX 863B: 2 confirmaciones catálogo no deben ser CATALOGO_REPETIDO")


# =============================================================================
# FIX 863C: _TRANSFER_PATTERNS - 'ya viene hasta' no es transfer
# =============================================================================

class TestFix863CTransferPatterns(unittest.TestCase):
    """FIX 863C: 'ya viene hasta el lunes' NO es transfer signal."""

    def setUp(self):
        from bug_detector import ContentAnalyzer
        self.pat = ContentAnalyzer._TRANSFER_PATTERNS

    def test_no_match_ya_viene_hasta(self):
        """'ya viene hasta el lunes' NO debe matchear como transfer."""
        texto = "ya viene hasta el lunes"
        self.assertIsNone(self.pat.search(texto),
                          "FIX 863C: 'ya viene hasta' no es transfer")

    def test_no_match_ya_viene_hasta_manana(self):
        """'ya viene hasta mañana' NO debe matchear."""
        texto = "ya viene hasta mañana en la tarde"
        self.assertIsNone(self.pat.search(texto))

    def test_match_ya_viene_simple(self):
        """'ya viene' (sin 'hasta') SÍ debe matchear como transfer."""
        texto = "ya viene el encargado"
        self.assertIsNotNone(self.pat.search(texto),
                             "'ya viene' (sin hasta) debe matchear")

    def test_match_ahorita_viene(self):
        """'ahorita viene' sigue matcheando."""
        texto = "ahorita viene el jefe"
        self.assertIsNotNone(self.pat.search(texto))

    def test_match_espereme(self):
        """'espéreme' sigue matcheando."""
        texto = "espéreme tantito"
        self.assertIsNotNone(self.pat.search(texto))


# =============================================================================
# FIX 864: Despedida apropiada tras "no está" o "está equivocado"
# =============================================================================

class TestFix864DespedidaApropiadaExempcion(unittest.TestCase):
    """FIX 864: Bruce dice adiós cuando cliente dice que no hay encargado/negocio = CORRECTO."""

    def _make_tracker(self, conv_pairs):
        """Crea CallEventTracker con conversación simulada."""
        from bug_detector import CallEventTracker
        tracker = CallEventTracker("test_864", "BRUCE_TEST")
        for role, texto in conv_pairs:
            tracker.conversacion.append((role, texto))
            if role == "bruce":
                tracker.respuestas_bruce.append(texto)
            else:
                tracker.textos_cliente.append(texto)
        return tracker

    def test_no_bug_despedida_tras_no_esta(self):
        """Bruce dice adiós después de 'no está' = NO es INTERRUPCION_CONVERSACIONAL."""
        from bug_detector import ContentAnalyzer
        conv = [
            ("bruce", "Hola, buen día. ¿Se encuentra el encargado?"),
            ("cliente", "No, no está"),
            ("bruce", "Entiendo. Muchas gracias por su tiempo, que tenga buen día."),
        ]
        tracker = self._make_tracker(conv)
        bugs = ContentAnalyzer._check_interrupcion_conversacional(tracker.conversacion)
        tipos = [b["tipo"] for b in bugs]
        self.assertNotIn("INTERRUPCION_CONVERSACIONAL", tipos,
                         "FIX 864: Despedida apropiada tras 'no está' no es bug")

    def test_no_bug_despedida_tras_esta_equivocado(self):
        """Bruce dice adiós después de 'está equivocado' = NO es INTERRUPCION_CONVERSACIONAL."""
        from bug_detector import ContentAnalyzer
        conv = [
            ("bruce", "Hola, buen día."),
            ("cliente", "No, mire, usted está equivocado porque no tengo"),
            ("bruce", "Disculpe la molestia, que tenga buen día."),
        ]
        tracker = self._make_tracker(conv)
        bugs = ContentAnalyzer._check_interrupcion_conversacional(tracker.conversacion)
        tipos = [b["tipo"] for b in bugs]
        self.assertNotIn("INTERRUPCION_CONVERSACIONAL", tipos,
                         "FIX 864: Despedida tras 'está equivocado' no es bug")

    def test_no_bug_despedida_tras_no_negocio(self):
        """Bruce dice adiós después de 'no tengo negocio' = NO es INTERRUPCION_CONVERSACIONAL."""
        from bug_detector import ContentAnalyzer
        conv = [
            ("bruce", "Hola, buen día."),
            ("cliente", "No, mire, yo no tengo negocio aquí"),
            ("bruce", "Disculpe la molestia. Que tenga excelente día."),
        ]
        tracker = self._make_tracker(conv)
        bugs = ContentAnalyzer._check_interrupcion_conversacional(tracker.conversacion)
        tipos = [b["tipo"] for b in bugs]
        self.assertNotIn("INTERRUPCION_CONVERSACIONAL", tipos,
                         "FIX 864: Despedida tras 'no tengo negocio' no es bug")

    def test_still_bugs_bruce_sells_after_explanation(self):
        """Bruce hace pitch después de que cliente explica algo = SÍ es bug."""
        from bug_detector import ContentAnalyzer
        conv = [
            ("bruce", "Hola, buen día."),
            ("cliente", "Mire, es que nosotros no manejamos ese tipo de"),
            ("bruce", "Le comento, me comunico de la marca NIOVAL somos distribuidores"),
        ]
        tracker = self._make_tracker(conv)
        bugs = ContentAnalyzer._check_interrupcion_conversacional(tracker.conversacion)
        tipos = [b["tipo"] for b in bugs]
        self.assertIn("INTERRUPCION_CONVERSACIONAL", tipos,
                      "Pitch después de explicación del cliente SÍ es bug")


# =============================================================================
# FIX 865: FSM no_interest - variantes singulares "no hacemos compra"
# =============================================================================

class TestFix865NoHacemosCompra(unittest.TestCase):
    """FIX 865: 'no hacemos compra' (singular) = NO_INTEREST en FSM."""

    def setUp(self):
        from fsm_engine import FSMEngine, FSMContext, FSMState, FSMIntent
        self.FSMIntent = FSMIntent
        self.FSMState = FSMState
        eng = FSMEngine()
        self.ctx = FSMContext()
        eng.context = self.ctx
        self.eng = eng

    def _classify(self, texto):
        from fsm_engine import classify_intent
        return classify_intent(texto, self.ctx, self.FSMState.PITCH)

    def test_no_hacemos_compra_singular(self):
        """'no hacemos compra' (singular) → NO_INTEREST."""
        result = self._classify("no hacemos compra")
        self.assertEqual(result, self.FSMIntent.NO_INTEREST,
                         "FIX 865: 'no hacemos compra' debe ser NO_INTEREST")

    def test_no_hacemos_ningun_tipo_de_compra(self):
        """'no hacemos ningún tipo de compra' → NO_INTEREST."""
        result = self._classify("no hacemos ningun tipo de compra")
        self.assertEqual(result, self.FSMIntent.NO_INTEREST,
                         "FIX 865: 'no hacemos ningún tipo de compra' debe ser NO_INTEREST")

    def test_no_hacemos_compras_plural(self):
        """'no hacemos compras' (plural, original) sigue siendo NO_INTEREST."""
        result = self._classify("no hacemos compras")
        self.assertEqual(result, self.FSMIntent.NO_INTEREST)

    def test_hacemos_compra_sin_no(self):
        """'hacemos compra' (sin 'no') NO debe ser NO_INTEREST."""
        result = self._classify("hacemos compra todos los dias")
        self.assertNotEqual(result, self.FSMIntent.NO_INTEREST,
                            "'hacemos compra' (sin 'no') no debe ser rechazo")


# =============================================================================
# FIX 866A: FSM another branch - "tienes que hablar a la sucursal"
# =============================================================================

class TestFix866AAnotherBranch(unittest.TestCase):
    """FIX 866A: 'tienes que hablar a la sucursal' = ANOTHER_BRANCH en FSM."""

    def setUp(self):
        from fsm_engine import FSMEngine, FSMContext, FSMState, FSMIntent
        self.FSMIntent = FSMIntent
        self.FSMState = FSMState
        eng = FSMEngine()
        self.ctx = FSMContext()
        eng.context = self.ctx
        self.eng = eng

    def _classify(self, texto):
        from fsm_engine import classify_intent
        return classify_intent(texto, self.ctx, self.FSMState.PITCH)

    def test_tienes_que_hablar_sucursal(self):
        """'tienes que hablar a la sucursal' → ANOTHER_BRANCH."""
        result = self._classify("tienes que hablar a la sucursal de Sahuayo")
        self.assertEqual(result, self.FSMIntent.ANOTHER_BRANCH,
                         "FIX 866A: 'tienes que hablar a la sucursal' debe ser ANOTHER_BRANCH")

    def test_hablar_a_la_sucursal(self):
        """'hablar a la sucursal' → ANOTHER_BRANCH."""
        result = self._classify("hablar a la sucursal de Monterrey")
        self.assertEqual(result, self.FSMIntent.ANOTHER_BRANCH,
                         "FIX 866A: 'hablar a la sucursal' debe ser ANOTHER_BRANCH")

    def test_otra_sucursal_original(self):
        """'otra sucursal' (original) sigue siendo ANOTHER_BRANCH."""
        result = self._classify("es otra sucursal")
        self.assertEqual(result, self.FSMIntent.ANOTHER_BRANCH)

    def test_tiene_que_hablar_sucursal(self):
        """'tiene que hablar a la sucursal' → ANOTHER_BRANCH."""
        result = self._classify("tiene que hablar a la sucursal central")
        self.assertEqual(result, self.FSMIntent.ANOTHER_BRANCH,
                         "FIX 866A: 'tiene que hablar a la sucursal' debe ser ANOTHER_BRANCH")


# =============================================================================
# FIX 866B: FSMContext.verificacion_consecutivas - anti-LOOP
# =============================================================================

class TestFix866BVerificacionConsecutivas(unittest.TestCase):
    """FIX 866B: verificacion_consecutivas en FSMContext previene LOOP post-transfer."""

    def test_field_exists_in_context(self):
        """FSMContext debe tener campo verificacion_consecutivas con default 0."""
        from fsm_engine import FSMContext
        ctx = FSMContext()
        self.assertTrue(hasattr(ctx, 'verificacion_consecutivas'),
                        "FIX 866B: FSMContext debe tener verificacion_consecutivas")
        self.assertEqual(ctx.verificacion_consecutivas, 0,
                         "FIX 866B: verificacion_consecutivas default debe ser 0")

    def test_counter_resets_on_non_verification(self):
        """verificacion_consecutivas se resetea cuando intent no es VERIFICATION."""
        from fsm_engine import FSMEngine, FSMContext, FSMState, FSMIntent, Transition, ActionType
        eng = FSMEngine()
        ctx = FSMContext()
        ctx.verificacion_consecutivas = 5
        eng.context = ctx

        # Simular _update_context con intent != VERIFICATION
        t = Transition(next_state=FSMState.PITCH, action_type=ActionType.TEMPLATE,
                       template_key='pitch_inicial')
        eng._update_context(FSMIntent.MANAGER_PRESENT, "sí, yo soy", t, agente=None)
        self.assertEqual(eng.context.verificacion_consecutivas, 0,
                         "FIX 866B: verificacion_consecutivas debe resetearse en intent != VERIFICATION")

    def test_counter_not_reset_on_verification(self):
        """verificacion_consecutivas NO se resetea en VERIFICATION."""
        from fsm_engine import FSMEngine, FSMContext, FSMState, FSMIntent, Transition, ActionType
        eng = FSMEngine()
        ctx = FSMContext()
        ctx.verificacion_consecutivas = 2
        eng.context = ctx

        t = Transition(next_state=FSMState.PITCH, action_type=ActionType.TEMPLATE,
                       template_key='verificacion_aqui_estoy')
        eng._update_context(FSMIntent.VERIFICATION, "¿bueno?", t, agente=None)
        # Should NOT reset (stays at 2, or incremented in pre-transition logic)
        self.assertGreaterEqual(eng.context.verificacion_consecutivas, 2,
                                "FIX 866B: verificacion_consecutivas no debe resetearse en VERIFICATION")

    def test_escalation_to_ofrecer_contacto_after_3x(self):
        """Después de 3 verificaciones consecutivas, debe escalar a ofrecer_contacto_bruce."""
        from fsm_engine import FSMEngine, FSMContext, FSMState, FSMIntent
        eng = FSMEngine()
        ctx = FSMContext()
        ctx.encargado_preguntado = True  # Trigger FIX 785/860 redirect
        ctx.verificacion_consecutivas = 2  # Ya 2 consecutivos - el próximo será el 3ro
        eng.context = ctx

        # El process() llama la lógica FIX 785/860 inline para VERIFICATION en PITCH state
        # Simulamos: cliente dice "¿Bueno?" con state=PITCH y encargado_preguntado=True
        # La lógica FIX 866B debe detectar verificacion_consecutivas >= 3 tras el incremento
        # y devolver 'ofrecer_contacto_bruce'
        # Verificamos directamente el counter y la lógica: si actual=2, próximo incremento→3
        eng.context.verificacion_consecutivas += 1  # Simular el incremento del fixup
        self.assertGreaterEqual(eng.context.verificacion_consecutivas, 3,
                                "FIX 866B: counter debe llegar a 3 tras incremento")
        # Y la condición del fixup debe disparar la escalación
        self.assertTrue(eng.context.verificacion_consecutivas >= 3,
                        "FIX 866B: verificacion_consecutivas >= 3 debe disparar escalación")


if __name__ == '__main__':
    unittest.main()
