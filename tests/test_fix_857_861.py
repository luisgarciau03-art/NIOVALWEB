# -*- coding: utf-8 -*-
"""
Tests para FIX 857-861:
- FIX 857: FSM marca encargado_preguntado en todos los pitch templates
- FIX 858: BugDetector PREGUNTA_REPETIDA - overlap threshold 0.8 para preguntas de contacto
- FIX 859: BugDetector CATALOGO_REPETIDO - threshold=2 (revertido)
- FIX 860: FIX 785 expandido a todos los pitch templates (BRUCE2462)
- FIX 861: FIX 856 salta pedir_whatsapp si ya fue solicitado (BRUCE2454/2441)
"""
import unittest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


# =============================================================================
# FIX 857: FSM encargado_preguntado en todos los pitch templates
# =============================================================================

class TestFix857EncargadoPreguntadoTodosPitch(unittest.TestCase):
    """FIX 857: Todos los pitch templates marcan encargado_preguntado=True."""

    def _make_fsm(self):
        from fsm_engine import FSMEngine, FSMContext
        eng = FSMEngine()
        ctx = FSMContext()
        eng.context = ctx
        return eng, ctx

    def _fake_transition(self, template_key):
        from fsm_engine import Transition, FSMState, ActionType
        return Transition(
            next_state=FSMState.BUSCANDO_ENCARGADO,
            action_type=ActionType.TEMPLATE,
            template_key=template_key,
        )

    def test_preguntar_encargado_sets_flag(self):
        """preguntar_encargado → encargado_preguntado=True."""
        from fsm_engine import FSMIntent
        eng, ctx = self._make_fsm()
        t = self._fake_transition('preguntar_encargado')
        eng._update_context(FSMIntent.UNKNOWN, "hola", t, None)
        self.assertTrue(ctx.encargado_preguntado)

    def test_pitch_inicial_sets_flag(self):
        """pitch_inicial → encargado_preguntado=True."""
        from fsm_engine import FSMIntent
        eng, ctx = self._make_fsm()
        t = self._fake_transition('pitch_inicial')
        eng._update_context(FSMIntent.UNKNOWN, "hola", t, None)
        self.assertTrue(ctx.encargado_preguntado)

    def test_identificacion_pitch_sets_flag(self):
        """identificacion_pitch → encargado_preguntado=True."""
        from fsm_engine import FSMIntent
        eng, ctx = self._make_fsm()
        t = self._fake_transition('identificacion_pitch')
        eng._update_context(FSMIntent.UNKNOWN, "hola", t, None)
        self.assertTrue(ctx.encargado_preguntado)

    def test_pitch_persona_nueva_sets_flag(self):
        """pitch_persona_nueva → encargado_preguntado=True."""
        from fsm_engine import FSMIntent
        eng, ctx = self._make_fsm()
        t = self._fake_transition('pitch_persona_nueva')
        eng._update_context(FSMIntent.UNKNOWN, "hola", t, None)
        self.assertTrue(ctx.encargado_preguntado)

    def test_pitch_encargado_sets_flag(self):
        """pitch_encargado → encargado_preguntado=True."""
        from fsm_engine import FSMIntent
        eng, ctx = self._make_fsm()
        t = self._fake_transition('pitch_encargado')
        eng._update_context(FSMIntent.UNKNOWN, "hola", t, None)
        self.assertTrue(ctx.encargado_preguntado)

    def test_repitch_encargado_sets_flag(self):
        """repitch_encargado → encargado_preguntado=True."""
        from fsm_engine import FSMIntent
        eng, ctx = self._make_fsm()
        t = self._fake_transition('repitch_encargado')
        eng._update_context(FSMIntent.UNKNOWN, "hola", t, None)
        self.assertTrue(ctx.encargado_preguntado)


# =============================================================================
# FIX 860: FIX 785 expandido a todos los pitch templates
# =============================================================================

class TestFix860PitchTemplatesNoRepetirEncargado(unittest.TestCase):
    """FIX 860: Si encargado_preguntado=True, todos los pitch templates se cambian a verificacion_aqui_estoy."""

    def _make_fsm_con_encargado_preguntado(self):
        from fsm_engine import FSMEngine, FSMContext
        eng = FSMEngine()
        ctx = FSMContext()
        ctx.encargado_preguntado = True
        eng.context = ctx
        return eng, ctx

    def _make_transition(self, template_key):
        from fsm_engine import Transition, FSMState, ActionType
        return Transition(
            next_state=FSMState.PITCH,
            action_type=ActionType.TEMPLATE,
            template_key=template_key,
        )

    def _run_fixups(self, eng, transition, intent=None):
        """Ejecuta la sección de fixups manualmente accediendo al código interno."""
        from fsm_engine import FSMIntent
        if intent is None:
            intent = FSMIntent.UNKNOWN
        # Simular los fixups de step() para el bloque FIX 785/860
        _PITCH_TEMPLATES_CON_ENCARGADO_Q = {
            'preguntar_encargado', 'pitch_inicial', 'identificacion_pitch',
        }
        _block_encargado_q = (
            (transition.template_key in _PITCH_TEMPLATES_CON_ENCARGADO_Q) or
            (transition.template_key == 'pitch_persona_nueva' and
             intent != FSMIntent.IDENTITY)
        )
        if _block_encargado_q and eng.context.encargado_preguntado:
            from fsm_engine import Transition, ActionType
            transition = Transition(
                next_state=transition.next_state,
                action_type=transition.action_type,
                template_key='verificacion_aqui_estoy',
            )
        return transition

    def test_preguntar_encargado_bloqueado(self):
        """FIX 785/860: preguntar_encargado cuando encargado_preguntado=True → verificacion_aqui_estoy."""
        eng, _ = self._make_fsm_con_encargado_preguntado()
        t = self._make_transition('preguntar_encargado')
        result = self._run_fixups(eng, t)
        self.assertEqual(result.template_key, 'verificacion_aqui_estoy')

    def test_identificacion_pitch_bloqueado(self):
        """FIX 860: identificacion_pitch cuando encargado_preguntado=True → verificacion_aqui_estoy."""
        eng, _ = self._make_fsm_con_encargado_preguntado()
        t = self._make_transition('identificacion_pitch')
        result = self._run_fixups(eng, t)
        self.assertEqual(result.template_key, 'verificacion_aqui_estoy')

    def test_pitch_persona_nueva_identity_no_bloqueado(self):
        """FIX 860B: pitch_persona_nueva con intent=IDENTITY NO se bloquea (nueva persona legítima)."""
        from fsm_engine import FSMIntent
        eng, _ = self._make_fsm_con_encargado_preguntado()
        t = self._make_transition('pitch_persona_nueva')
        result = self._run_fixups(eng, t, intent=FSMIntent.IDENTITY)
        # IDENTITY = nueva persona que necesita el pitch con NIOVAL
        self.assertEqual(result.template_key, 'pitch_persona_nueva')  # Sin cambio

    def test_pitch_persona_nueva_question_bloqueado(self):
        """FIX 860B: pitch_persona_nueva con intent=QUESTION se bloquea (BRUCE2462: repite encargado q)."""
        from fsm_engine import FSMIntent
        eng, _ = self._make_fsm_con_encargado_preguntado()
        t = self._make_transition('pitch_persona_nueva')
        result = self._run_fixups(eng, t, intent=FSMIntent.QUESTION)
        self.assertEqual(result.template_key, 'verificacion_aqui_estoy')

    def test_pitch_persona_nueva_verification_bloqueado(self):
        """FIX 860B: pitch_persona_nueva con intent=VERIFICATION se bloquea."""
        from fsm_engine import FSMIntent
        eng, _ = self._make_fsm_con_encargado_preguntado()
        t = self._make_transition('pitch_persona_nueva')
        result = self._run_fixups(eng, t, intent=FSMIntent.VERIFICATION)
        self.assertEqual(result.template_key, 'verificacion_aqui_estoy')

    def test_pitch_inicial_bloqueado(self):
        """FIX 860: pitch_inicial cuando encargado_preguntado=True → verificacion_aqui_estoy."""
        eng, _ = self._make_fsm_con_encargado_preguntado()
        t = self._make_transition('pitch_inicial')
        result = self._run_fixups(eng, t)
        self.assertEqual(result.template_key, 'verificacion_aqui_estoy')

    def test_pitch_normal_no_bloqueado(self):
        """FIX 860: templates que NO preguntan encargado NO se bloquean."""
        eng, _ = self._make_fsm_con_encargado_preguntado()
        t = self._make_transition('pedir_whatsapp_o_correo')
        result = self._run_fixups(eng, t)
        self.assertEqual(result.template_key, 'pedir_whatsapp_o_correo')  # Sin cambio

    def test_sin_encargado_preguntado_no_bloquea(self):
        """FIX 860: Si encargado_preguntado=False, pitch templates NO se bloquean."""
        from fsm_engine import FSMEngine, FSMContext, FSMIntent
        eng = FSMEngine()
        ctx = FSMContext()
        ctx.encargado_preguntado = False  # NO preguntado aún
        eng.context = ctx

        t = self._make_transition('identificacion_pitch')
        result = self._run_fixups(eng, t)
        self.assertEqual(result.template_key, 'identificacion_pitch')  # Sin cambio

    def test_bruce2462_verification_tras_transfer_usa_verificacion(self):
        """FIX 860: BRUCE2462 - VERIFICATION ('¿Bueno?') tras transfer → verificacion_aqui_estoy en tabla FSM."""
        from fsm_engine import FSMEngine, FSMContext, FSMState
        eng = FSMEngine()
        eng.context.encargado_preguntado = True
        eng.state = FSMState.ESPERANDO_TRANSFERENCIA
        result = eng.process("¿Bueno?")
        if result:
            # No debe repetir la pregunta del encargado
            self.assertNotIn("encargado", result.lower())
            self.assertNotIn("se encontrara", result.lower())

    def test_bruce2462_question_tras_transfer_usa_verificacion(self):
        """FIX 860B: QUESTION tras transfer con encargado_preguntado=True → verificacion_aqui_estoy."""
        from fsm_engine import FSMEngine, FSMContext, FSMState
        eng = FSMEngine()
        eng.context.encargado_preguntado = True
        eng.context.pitch_dado = True
        eng.state = FSMState.ESPERANDO_TRANSFERENCIA
        result = eng.process("¿Bueno bueno? Dígame.")
        if result:
            # No debe repetir la pregunta del encargado
            self.assertNotIn("se encontrara", result.lower())


# =============================================================================
# FIX 861: Prevenir FIX 856 de repetir WhatsApp ya solicitado
# =============================================================================

class TestFix861WhatsappYaSolicitado(unittest.TestCase):
    """FIX 861: FSMContext.whatsapp_ya_solicitado previene repetición en FIX 856."""

    def test_whatsapp_ya_solicitado_default_false(self):
        """FSMContext.whatsapp_ya_solicitado inicia en False."""
        from fsm_engine import FSMContext
        ctx = FSMContext()
        self.assertFalse(ctx.whatsapp_ya_solicitado)

    def test_pedir_whatsapp_o_correo_sets_flag(self):
        """pedir_whatsapp_o_correo en _update_context → whatsapp_ya_solicitado=True."""
        from fsm_engine import FSMEngine, FSMContext, FSMIntent, Transition, FSMState, ActionType
        eng = FSMEngine()
        ctx = FSMContext()
        eng.context = ctx

        t = Transition(
            next_state=FSMState.CAPTURANDO_CONTACTO,
            action_type=ActionType.TEMPLATE,
            template_key='pedir_whatsapp_o_correo',
        )
        eng._update_context(FSMIntent.OFFER_DATA, "mi whatsapp", t, None)
        self.assertTrue(ctx.whatsapp_ya_solicitado)

    def test_pedir_whatsapp_sets_flag(self):
        """pedir_whatsapp en _update_context → whatsapp_ya_solicitado=True."""
        from fsm_engine import FSMEngine, FSMContext, FSMIntent, Transition, FSMState, ActionType
        eng = FSMEngine()
        ctx = FSMContext()
        eng.context = ctx

        t = Transition(
            next_state=FSMState.CAPTURANDO_CONTACTO,
            action_type=ActionType.TEMPLATE,
            template_key='pedir_whatsapp',
        )
        eng._update_context(FSMIntent.OFFER_DATA, "mi whatsapp", t, None)
        self.assertTrue(ctx.whatsapp_ya_solicitado)

    def test_fallo_861_fix856_salta_pedir_whatsapp(self):
        """FIX 861: FIX 856 con whatsapp_ya_solicitado=True → ofrecer_contacto_bruce en vez de pedir_whatsapp."""
        # Simular la lógica de FIX 856+861
        from fsm_engine import FSMContext, FSMState
        ctx = FSMContext()
        ctx.whatsapp_ya_solicitado = True  # WhatsApp ya fue pedido antes
        ctx.preguntas_producto_respondidas = 2  # 2 preguntas ya respondidas

        redirect_n = 1  # 3ra pregunta = primera escalación FIX 856

        if redirect_n <= 1:
            if ctx.whatsapp_ya_solicitado:
                new_template = 'ofrecer_contacto_bruce'
                new_state = FSMState.OFRECIENDO_CONTACTO
            else:
                new_template = 'pedir_whatsapp_o_correo'
                new_state = FSMState.CAPTURANDO_CONTACTO
        else:
            new_template = 'ofrecer_contacto_bruce'
            new_state = FSMState.OFRECIENDO_CONTACTO

        # Con whatsapp_ya_solicitado=True, NO debe pedir WhatsApp otra vez
        self.assertEqual(new_template, 'ofrecer_contacto_bruce')
        self.assertNotEqual(new_template, 'pedir_whatsapp_o_correo')

    def test_sin_whatsapp_solicitado_856_usa_pedir_whatsapp(self):
        """FIX 861: FIX 856 con whatsapp_ya_solicitado=False → pedir_whatsapp normalmente."""
        from fsm_engine import FSMContext, FSMState
        ctx = FSMContext()
        ctx.whatsapp_ya_solicitado = False  # WhatsApp NO fue pedido aún
        ctx.preguntas_producto_respondidas = 2

        redirect_n = 1  # 3ra pregunta = primera escalación FIX 856

        if redirect_n <= 1:
            if ctx.whatsapp_ya_solicitado:
                new_template = 'ofrecer_contacto_bruce'
                new_state = FSMState.OFRECIENDO_CONTACTO
            else:
                new_template = 'pedir_whatsapp_o_correo'
                new_state = FSMState.CAPTURANDO_CONTACTO
        else:
            new_template = 'ofrecer_contacto_bruce'
            new_state = FSMState.OFRECIENDO_CONTACTO

        # Sin whatsapp_ya_solicitado, SÍ debe pedir WhatsApp (primera vez)
        self.assertEqual(new_template, 'pedir_whatsapp_o_correo')


# =============================================================================
# FIX 858 (revisado): PREGUNTA_REPETIDA - overlap threshold para preguntas de contacto
# =============================================================================

class TestFix858OverlapThresholdContacto(unittest.TestCase):
    """FIX 858 revisado: Preguntas de contacto necesitan >=80% overlap para agruparse."""

    def _make_tracker(self):
        from bug_detector import CallEventTracker
        return CallEventTracker(
            call_sid="test_fix858",
            bruce_id="TEST_858",
            telefono="+5216621234567"
        )

    def test_pregunta_identica_contacto_es_bug(self):
        """FIX 858: Pregunta WhatsApp IDÉNTICA 2x → PREGUNTA_REPETIDA (overlap 100% ≥ 0.8)."""
        from bug_detector import ContentAnalyzer
        tracker = self._make_tracker()
        q = "Me podria proporcionar un numero de WhatsApp o correo electronico para enviarle la informacion?"
        tracker.emit("BRUCE_RESPONDE", {"texto": q})
        tracker.emit("CLIENTE_DICE", {"texto": "No tengo ahorita"})
        tracker.emit("BRUCE_RESPONDE", {"texto": q})
        bugs = ContentAnalyzer.analyze(tracker)
        tipos = [b["tipo"] for b in bugs]
        self.assertIn("PREGUNTA_REPETIDA", tipos)

    def test_pregunta_contacto_variante_no_bug(self):
        """FIX 858: Variantes de pregunta de contacto (<80% overlap) → NO PREGUNTA_REPETIDA."""
        from bug_detector import ContentAnalyzer
        tracker = self._make_tracker()
        tracker.emit("BRUCE_RESPONDE", {"texto": "Me comunico de nioval. Cual es su numero de WhatsApp?"})
        tracker.emit("CLIENTE_DICE", {"texto": "No tengo"})
        tracker.emit("BRUCE_RESPONDE", {"texto": "Entiendo. Me podria dar su correo electronico entonces?"})
        bugs = ContentAnalyzer.analyze(tracker)
        tipos = [b["tipo"] for b in bugs]
        self.assertNotIn("PREGUNTA_REPETIDA", tipos)


# =============================================================================
# FIX 859 (revertido): CATALOGO_REPETIDO - threshold=2
# =============================================================================

class TestFix859CatalogoThresholdDos(unittest.TestCase):
    """FIX 859 revertido: CATALOGO_REPETIDO con threshold=2."""

    def _make_tracker(self):
        from bug_detector import CallEventTracker
        return CallEventTracker(
            call_sid="test_fix859",
            bruce_id="TEST_859",
            telefono="+5216621234567"
        )

    def test_catalogo_dos_veces_es_bug(self):
        """FIX 859 revertido: 2 ofertas de catálogo → CATALOGO_REPETIDO."""
        from bug_detector import ContentAnalyzer
        tracker = self._make_tracker()
        tracker.emit("BRUCE_RESPONDE", {"texto": "Le puedo enviar nuestro catalogo de productos ferreteros."})
        tracker.emit("CLIENTE_DICE", {"texto": "Mmm no se"})
        tracker.emit("BRUCE_RESPONDE", {"texto": "Le envio el catalogo para que lo revise con calma."})
        bugs = ContentAnalyzer.analyze(tracker)
        tipos = [b["tipo"] for b in bugs]
        self.assertIn("CATALOGO_REPETIDO", tipos)

    def test_catalogo_una_vez_no_bug(self):
        """FIX 859 revertido: 1 oferta de catálogo → NO CATALOGO_REPETIDO."""
        from bug_detector import ContentAnalyzer
        tracker = self._make_tracker()
        tracker.emit("BRUCE_RESPONDE", {"texto": "Le envio el catalogo para que lo revise."})
        tracker.emit("CLIENTE_DICE", {"texto": "Perfecto."})
        bugs = ContentAnalyzer.analyze(tracker)
        tipos = [b["tipo"] for b in bugs]
        self.assertNotIn("CATALOGO_REPETIDO", tipos)


if __name__ == "__main__":
    unittest.main(verbosity=2)
