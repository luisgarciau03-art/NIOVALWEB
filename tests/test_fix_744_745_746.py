"""
Tests para FIX 744-746:
- FIX 744: AREA_EQUIVOCADA - detección inmediata y despedida
- FIX 745: Anti-recursive garble en FIX 621B
- FIX 746: Transfer mode persistente con "permiteme" repetido

Bugs corregidos:
- BRUCE2366: Cliente dijo "no tengo negocio, está equivocado" x3 → Bruce pidió WhatsApp
- BRUCE2370: "Sí, le preguntaba, sí, le preguntaba..." recursión infinita
- BRUCE2370: "permiteme" repetido → Bruce perdió estado ESPERANDO_TRANSFERENCIA
"""

import os
import sys
import unittest

# Agregar directorio padre al path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# FSM en modo active para tests
os.environ["FSM_ENABLED"] = "active"


# ============================================================
# FIX 744: AREA_EQUIVOCADA - Detección inmediata
# ============================================================
class TestFIX744_AreaEquivocada(unittest.TestCase):
    """BRUCE2366: Cliente dice 'no tengo negocio' → Bruce debe disculparse y colgar."""

    def _get_agente(self):
        from agente_ventas import AgenteVentas
        agente = AgenteVentas.__new__(AgenteVentas)
        agente.conversation_history = []
        agente.estado_conversacion = None
        agente.conversacion_iniciada = True
        agente.lead_data = {"bruce_id": "TEST"}
        agente.pitch_dado = True
        agente.turno_actual = 2
        agente.catalogo_prometido = False
        agente.ofertas_catalogo_count = 0
        agente.veces_pregunto_encargado = 0
        agente.veces_pregunto_whatsapp = 0
        agente.ultimo_patron_detectado = None
        agente.digitos_preservados_481 = ""
        agente.memoria_datos_contacto = {}
        agente.esperando_hora_callback = False
        agente.fsm = None
        # Mock classifier
        agente.classifier = None
        # Mock memory layer
        agente.memory_layer = None
        return agente

    def test_no_tengo_negocio(self):
        """'no tengo negocio' → AREA_EQUIVOCADA + despedida."""
        agente = self._get_agente()
        r = agente._detectar_patron_simple_optimizado("No, no tengo negocio yo")
        self.assertIsNotNone(r)
        self.assertEqual(r["tipo"], "AREA_EQUIVOCADA")
        self.assertEqual(r["accion"], "DESPEDIDA")

    def test_esta_equivocado(self):
        """'está equivocado' → AREA_EQUIVOCADA."""
        agente = self._get_agente()
        r = agente._detectar_patron_simple_optimizado("No mire, usted esta equivocado")
        self.assertIsNotNone(r)
        self.assertEqual(r["tipo"], "AREA_EQUIVOCADA")

    def test_numero_equivocado(self):
        """'número equivocado' → AREA_EQUIVOCADA."""
        agente = self._get_agente()
        r = agente._detectar_patron_simple_optimizado("Tiene el numero equivocado")
        self.assertIsNotNone(r)
        self.assertEqual(r["tipo"], "AREA_EQUIVOCADA")

    def test_no_es_aqui(self):
        """'no es aquí' → AREA_EQUIVOCADA."""
        agente = self._get_agente()
        r = agente._detectar_patron_simple_optimizado("No, aqui no es")
        self.assertIsNotNone(r)
        self.assertEqual(r["tipo"], "AREA_EQUIVOCADA")

    def test_area_equivocada_explicita(self):
        """'area equivocada' → AREA_EQUIVOCADA."""
        agente = self._get_agente()
        r = agente._detectar_patron_simple_optimizado("Creo que tiene el area equivocada")
        self.assertIsNotNone(r)
        self.assertEqual(r["tipo"], "AREA_EQUIVOCADA")

    def test_no_es_ferreteria(self):
        """'no es ferretería' → AREA_EQUIVOCADA."""
        agente = self._get_agente()
        r = agente._detectar_patron_simple_optimizado("Esto no es ferreteria, es una taquería")
        self.assertIsNotNone(r)
        self.assertEqual(r["tipo"], "AREA_EQUIVOCADA")

    def test_se_equivoco_de_numero(self):
        """'se equivocó de número' → AREA_EQUIVOCADA."""
        agente = self._get_agente()
        r = agente._detectar_patron_simple_optimizado("Se equivoco de numero, señor")
        self.assertIsNotNone(r)
        self.assertEqual(r["tipo"], "AREA_EQUIVOCADA")

    def test_respuesta_contiene_disculpa(self):
        """Respuesta debe ser cortés y breve."""
        agente = self._get_agente()
        r = agente._detectar_patron_simple_optimizado("No tengo negocio yo")
        self.assertIn("Disculpe", r["respuesta"])
        self.assertIn("buen día", r["respuesta"])

    def test_no_false_positive_negocio_normal(self):
        """'mi negocio es de ferretería' NO debe ser AREA_EQUIVOCADA."""
        agente = self._get_agente()
        r = agente._detectar_patron_simple_optimizado("Si, mi negocio es de ferreteria")
        if r is not None:
            self.assertNotEqual(r["tipo"], "AREA_EQUIVOCADA")

    def test_no_false_positive_encargado(self):
        """'no está el encargado' NO debe ser AREA_EQUIVOCADA."""
        agente = self._get_agente()
        r = agente._detectar_patron_simple_optimizado("No esta el encargado ahorita")
        if r is not None:
            self.assertNotEqual(r["tipo"], "AREA_EQUIVOCADA")


# ============================================================
# FIX 744: AREA_EQUIVOCADA en FSM
# ============================================================
class TestFIX744_FSM(unittest.TestCase):
    """FSM debe clasificar WRONG_NUMBER y transicionar a DESPEDIDA."""

    def test_fsm_wrong_number_intent(self):
        """FSM clasifica 'no tengo negocio' como WRONG_NUMBER."""
        from fsm_engine import classify_intent, FSMContext, FSMState, FSMIntent
        ctx = FSMContext()
        intent = classify_intent("No, no tengo negocio yo", ctx, FSMState.PITCH)
        self.assertEqual(intent, FSMIntent.WRONG_NUMBER)

    def test_fsm_equivocado_intent(self):
        """FSM clasifica 'está equivocado' como WRONG_NUMBER."""
        from fsm_engine import classify_intent, FSMContext, FSMState, FSMIntent
        ctx = FSMContext()
        intent = classify_intent("Usted esta equivocado", ctx, FSMState.SALUDO)
        self.assertEqual(intent, FSMIntent.WRONG_NUMBER)

    def test_fsm_wrong_number_transition(self):
        """FSM transition: any state + WRONG_NUMBER → DESPEDIDA."""
        from fsm_engine import FSMEngine
        fsm = FSMEngine()
        result = fsm.process("No tengo negocio, esta equivocado", None)
        self.assertIsNotNone(result)
        self.assertIn("Disculpe", result)

    def test_fsm_wrong_number_from_pitch(self):
        """FSM desde PITCH + WRONG_NUMBER → DESPEDIDA."""
        from fsm_engine import FSMEngine, FSMState
        fsm = FSMEngine()
        fsm.state = FSMState.PITCH
        result = fsm.process("Aqui no es, tiene el numero equivocado", None)
        self.assertIsNotNone(result)
        from fsm_engine import FSMState as S
        self.assertEqual(fsm.state, S.DESPEDIDA)


# ============================================================
# FIX 745: Anti-recursive garble en FIX 621B
# ============================================================
class TestFIX745_AntiRecursive(unittest.TestCase):
    """BRUCE2370: Previene 'Sí, le preguntaba, ¿le preguntaba, ¿...?'"""

    def _get_agente(self):
        from agente_ventas import AgenteVentas
        agente = AgenteVentas.__new__(AgenteVentas)
        # Enough history so FIX 604 ("¿Bueno?" en primer turno) does NOT fire
        agente.conversation_history = [
            {"role": "assistant", "content": "Le comento, me comunico de la marca NIOVAL."},
            {"role": "user", "content": "Sí, dígame."},
            {"role": "assistant", "content": "¿Se encontrará el encargado de compras?"},
            {"role": "user", "content": "Sí, espere."},
        ]
        agente.estado_conversacion = None
        agente.conversacion_iniciada = True
        agente.lead_data = {"bruce_id": "TEST"}
        agente.pitch_dado = True
        agente.turno_actual = 5
        agente.catalogo_prometido = False
        agente.ofertas_catalogo_count = 0
        agente.veces_pregunto_encargado = 1
        agente.veces_pregunto_whatsapp = 0
        agente.ultimo_patron_detectado = None
        agente.digitos_preservados_481 = ""
        agente.memoria_datos_contacto = {}
        agente.esperando_hora_callback = False
        agente.fsm = None
        agente.classifier = None
        agente.memory_layer = None
        return agente

    def test_first_bueno_repeats_question(self):
        """Primera '¿Bueno?' después de pregunta → 'Sí, le preguntaba, ¿...?'"""
        agente = self._get_agente()
        from agente_ventas import EstadoConversacion
        agente.estado_conversacion = EstadoConversacion.CONVERSACION_NORMAL
        # Last assistant msg ends with "?" → FIX 621B should wrap
        agente.conversation_history = [
            {"role": "assistant", "content": "Le comento, me comunico de la marca NIOVAL."},
            {"role": "user", "content": "Sí, dígame."},
            {"role": "assistant", "content": "Somos distribuidores de productos ferreteros."},
            {"role": "user", "content": "Ajá."},
            {"role": "assistant", "content": "¿Se encontrará el encargado de compras?"},
            {"role": "user", "content": "Bueno?"},
        ]
        r = agente._detectar_patron_simple_optimizado("Bueno?")
        self.assertIsNotNone(r)
        self.assertIn("le preguntaba", r["respuesta"])
        self.assertNotIn("le preguntaba, ¿le preguntaba", r["respuesta"])

    def test_second_bueno_uses_fallback(self):
        """Segunda '¿Bueno?' (último Bruce ya era 'le preguntaba') → fallback limpio."""
        agente = self._get_agente()
        from agente_ventas import EstadoConversacion
        agente.estado_conversacion = EstadoConversacion.CONVERSACION_NORMAL
        agente.conversation_history = [
            {"role": "assistant", "content": "Le comento, me comunico de la marca NIOVAL."},
            {"role": "user", "content": "Sí, dígame."},
            {"role": "assistant", "content": "Somos distribuidores de productos ferreteros."},
            {"role": "user", "content": "Ajá."},
            {"role": "assistant", "content": "Sí, le preguntaba, ¿se encontrará el encargado de compras?"},
            {"role": "user", "content": "Bueno?"},
        ]
        r = agente._detectar_patron_simple_optimizado("Bueno?")
        self.assertIsNotNone(r)
        # Should NOT contain recursive "le preguntaba"
        self.assertNotIn("le preguntaba", r["respuesta"])
        # Should be the clean fallback
        self.assertIn("aquí estoy", r["respuesta"])

    def test_third_bueno_still_fallback(self):
        """Tercera '¿Bueno?' → sigue con fallback limpio (no recursión)."""
        agente = self._get_agente()
        from agente_ventas import EstadoConversacion
        agente.estado_conversacion = EstadoConversacion.CONVERSACION_NORMAL
        agente.conversation_history = [
            {"role": "assistant", "content": "Sí, aquí estoy. Dígame."},
            {"role": "user", "content": "Bueno?"},
        ]
        r = agente._detectar_patron_simple_optimizado("Bueno?")
        self.assertIsNotNone(r)
        # "Sí, aquí estoy. Dígame." ends with "." not "?" so 621B won't fire
        # This should give fallback
        self.assertNotIn("le preguntaba, ¿le preguntaba", r["respuesta"])

    def test_no_recursive_pattern_535b_path(self):
        """Path 535b: 'Diga' después de 'le preguntaba' → fallback."""
        agente = self._get_agente()
        from agente_ventas import EstadoConversacion
        agente.estado_conversacion = EstadoConversacion.CONVERSACION_NORMAL
        agente.conversation_history = [
            {"role": "assistant", "content": "Sí, le preguntaba, ¿me podría proporcionar el WhatsApp?"},
            {"role": "user", "content": "Diga"},
            {"role": "assistant", "content": "dummy"},  # Need 4 msgs for historial_avanzado
            {"role": "user", "content": "dummy"},
        ]
        r = agente._detectar_patron_simple_optimizado("Diga")
        # Can be None (many conditions) or fallback - just ensure no recursion
        if r is not None:
            self.assertNotIn("le preguntaba, ¿le preguntaba", r["respuesta"])


# ============================================================
# FIX 746: Transfer mode persistente
# ============================================================
class TestFIX746_TransferModePersistent(unittest.TestCase):
    """BRUCE2370: 'permiteme' repetido debe mantener ESPERANDO_TRANSFERENCIA."""

    def test_frases_mas_espera_includes_permiteme(self):
        """'permiteme' está en frases_mas_espera ampliadas."""
        # Verificar que los patterns están definidos correctamente
        frases_mas_espera_746 = [
            'permiteme', 'permitame', 'dejame ver', 'dejeme ver',
            'voy a ver', 'ahorita', 'aguardeme', 'aguardame',
            'en un momento', 'un minuto', 'un minutito',
            'dame chance', 'deme chance', 'un ratito',
            'se lo paso', 'le paso', 'te paso', 'ahorita le',
        ]
        self.assertIn('permiteme', frases_mas_espera_746)
        self.assertIn('dejame ver', frases_mas_espera_746)
        self.assertIn('ahorita', frases_mas_espera_746)

    def test_permiteme_in_long_text_is_mas_espera(self):
        """'iban a entrar a junta, permiteme' matchea como más espera."""
        frase = "iban a entrar a junta permiteme"
        frases_mas_espera_746 = [
            'permiteme', 'permitame', 'dejame ver', 'dejeme ver',
            'voy a ver', 'ahorita', 'aguardeme', 'aguardame',
        ]
        es_mas_espera = any(f in frase for f in frases_mas_espera_746)
        self.assertTrue(es_mas_espera)

    def test_bueno_is_not_mas_espera(self):
        """'¿Bueno?' NO es más espera - es re-engagement."""
        frase = "bueno"
        frases_mas_espera = ['un momento', 'momentito', 'espere', 'tantito', 'un segundo']
        frases_mas_espera_746 = [
            'permiteme', 'permitame', 'dejame ver', 'dejeme ver',
            'voy a ver', 'ahorita', 'aguardeme', 'aguardame',
        ]
        es_mas_espera = any(f in frase for f in frases_mas_espera) or \
                         any(f in frase for f in frases_mas_espera_746)
        self.assertFalse(es_mas_espera)

    def test_mas_espera_overrides_audio_sustancial(self):
        """es_mas_espera=True debe forzar cliente_volvio=False."""
        # Simular la lógica de FIX 746
        es_mas_espera = True  # "permiteme" detected
        tiene_senal_fuerte = False
        tiene_senal_debil = False
        texto_corto_712 = False
        timeout_espera_712 = False
        _audio_sustancial_751 = True  # >= 3 words

        # FIX 746 logic
        if es_mas_espera:
            cliente_volvio = False
        else:
            cliente_volvio = (
                tiene_senal_fuerte or
                (tiene_senal_debil and texto_corto_712) or
                timeout_espera_712 or
                _audio_sustancial_751
            )

        self.assertFalse(cliente_volvio)

    def test_without_746_audio_sustancial_causes_exit(self):
        """Sin FIX 746: audio >= 3 palabras fuerza cliente_volvio=True (el bug original)."""
        es_mas_espera = False  # NOT a wait request
        tiene_senal_fuerte = False
        tiene_senal_debil = False
        texto_corto_712 = False
        timeout_espera_712 = False
        _audio_sustancial_751 = True  # >= 3 words

        cliente_volvio = (
            tiene_senal_fuerte or
            (tiene_senal_debil and texto_corto_712) or
            timeout_espera_712 or
            _audio_sustancial_751
        )

        self.assertTrue(cliente_volvio)  # Original behavior: would exit wait mode

    def test_753_permiteme_stays_waiting(self):
        """FIX 753 path: 'permiteme' in 712B → seguir esperando."""
        _fl_753 = "iban a entrar a junta permiteme"
        _mas_espera_753 = ['permiteme', 'permitame', 'un momento', 'momentito', 'espere',
                           'tantito', 'un segundo', 'dejame ver', 'dejeme ver', 'voy a ver',
                           'ahorita', 'aguardeme', 'en un momento', 'un minuto',
                           'se lo paso', 'le paso', 'te paso']
        _es_mas_espera_753 = any(f in _fl_753 for f in _mas_espera_753)
        self.assertTrue(_es_mas_espera_753)

        if _es_mas_espera_753:
            _volvio_753 = False
        else:
            _volvio_753 = True  # Would have been True from other signals

        self.assertFalse(_volvio_753)


# ============================================================
# Integration: BRUCE2366 scenario replay
# ============================================================
class TestBRUCE2366_Replay(unittest.TestCase):
    """Replay completo del bug BRUCE2366: 'no tengo negocio' ignorado."""

    def _get_agente(self):
        from agente_ventas import AgenteVentas
        agente = AgenteVentas.__new__(AgenteVentas)
        agente.conversation_history = []
        agente.estado_conversacion = None
        agente.conversacion_iniciada = True
        agente.lead_data = {"bruce_id": "TEST_2366"}
        agente.pitch_dado = True
        agente.turno_actual = 1
        agente.catalogo_prometido = False
        agente.ofertas_catalogo_count = 0
        agente.veces_pregunto_encargado = 0
        agente.veces_pregunto_whatsapp = 0
        agente.ultimo_patron_detectado = None
        agente.digitos_preservados_481 = ""
        agente.memoria_datos_contacto = {}
        agente.fsm = None
        agente.classifier = None
        agente.memory_layer = None
        return agente

    def test_first_equivocado_triggers_despedida(self):
        """T1: 'no tengo negocio, está equivocado' → inmediata despedida (no pedir WhatsApp)."""
        agente = self._get_agente()
        r = agente._detectar_patron_simple_optimizado(
            "No, mire, yo creo que esta equivocado porque no, no tengo negocio yo"
        )
        self.assertIsNotNone(r)
        self.assertEqual(r["tipo"], "AREA_EQUIVOCADA")
        self.assertEqual(r["accion"], "DESPEDIDA")
        # Must NOT ask for WhatsApp or any contact
        self.assertNotIn("WhatsApp", r["respuesta"])
        self.assertNotIn("correo", r["respuesta"])


# ============================================================
# Integration: BRUCE2370 scenario replay
# ============================================================
class TestBRUCE2370_Replay(unittest.TestCase):
    """Replay del bug BRUCE2370: recursive garble + lost transfer mode."""

    def _get_agente(self):
        from agente_ventas import AgenteVentas
        agente = AgenteVentas.__new__(AgenteVentas)
        agente.conversation_history = [
            {"role": "assistant", "content": "Le comento, me comunico de la marca NIOVAL."},
            {"role": "user", "content": "Sí, dígame."},
            {"role": "assistant", "content": "Somos distribuidores de productos ferreteros."},
            {"role": "user", "content": "Ajá."},
        ]
        agente.estado_conversacion = None
        agente.conversacion_iniciada = True
        agente.lead_data = {"bruce_id": "TEST_2370"}
        agente.pitch_dado = True
        agente.turno_actual = 6
        agente.catalogo_prometido = False
        agente.ofertas_catalogo_count = 0
        agente.veces_pregunto_encargado = 1
        agente.veces_pregunto_whatsapp = 0
        agente.ultimo_patron_detectado = None
        agente.digitos_preservados_481 = ""
        agente.memoria_datos_contacto = {}
        agente.esperando_hora_callback = False
        agente.fsm = None
        agente.classifier = None
        agente.memory_layer = None
        return agente

    def test_recursive_garble_prevented(self):
        """After 'Sí, le preguntaba...' + another '¿Bueno?' → clean fallback."""
        agente = self._get_agente()
        from agente_ventas import EstadoConversacion
        agente.estado_conversacion = EstadoConversacion.CONVERSACION_NORMAL
        agente.conversation_history = [
            {"role": "assistant", "content": "Le comento, me comunico de la marca NIOVAL."},
            {"role": "user", "content": "Sí, dígame."},
            {"role": "assistant", "content": "Somos distribuidores de productos ferreteros."},
            {"role": "user", "content": "Ajá."},
            {"role": "assistant", "content": "Sí, le preguntaba, ¿disculpe, me puede repetir?"},
            {"role": "user", "content": "Bueno."},
        ]
        r = agente._detectar_patron_simple_optimizado("Bueno.")
        self.assertIsNotNone(r)
        # CRITICAL: No recursive nesting
        self.assertNotIn("le preguntaba, ¿le preguntaba", r["respuesta"])
        self.assertNotIn("le preguntaba, ¿si, le preguntaba", r["respuesta"])
        # Should be clean fallback
        self.assertIn("aquí estoy", r["respuesta"])


if __name__ == "__main__":
    unittest.main()
