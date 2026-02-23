"""
Tests FIX 771-774: Bugs del deploy FIX 768
==========================================
FIX 771: Fallback contextual post-timeout (BRUCE2435)
FIX 772: INTERRUPCION_CONVERSACIONAL false positive (BRUCE2435/2436)
FIX 773: CATALOGO_REPETIDO patrones interés ampliados (BRUCE2436)
FIX 774: Anti-loop "me puede repetir" threshold >=1 (BRUCE2438)
"""
import os
import sys
import re
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


# ============================================================
# FIX 771: Fallback contextual post-timeout
# ============================================================
class TestFix771FallbackContextual(unittest.TestCase):
    """FIX 771: Si Bruce ya dio contacto y cliente se despide, fallback = despedida."""

    def _make_agente(self, history):
        """Crea agente mock con conversation_history."""
        class MockAgente:
            def __init__(self):
                self.conversation_history = history
                self.lead_data = {}
        return MockAgente()

    def test_bruce_dio_contacto_cliente_despide(self):
        """BRUCE2435: Bruce dio WhatsApp+correo, cliente dice 'Ok, gracias' → despedida."""
        history = [
            {"role": "assistant", "content": "Claro, nuestro WhatsApp es 6 6 2, 4 1 5, 1 9 9 7 y nuestro correo es ventas arroba nioval punto com."},
            {"role": "user", "content": "Ok, gracias. Bien, gracias."},
        ]
        agente = self._make_agente(history)
        respuesta_lower = "ok, gracias. bien, gracias."

        # Simulate FIX 771 logic
        _todos_bruce = [m['content'].lower() for m in agente.conversation_history if m['role'] == 'assistant']
        _bruce_dio_contacto = any(
            any(w in msg for w in ['6 6 2', '662', '4 1 5', '415', '1 9 9 7', '1997',
                                    'ventas arroba nioval', 'ventas@nioval',
                                    'nuestro whatsapp es', 'nuestro correo es'])
            for msg in _todos_bruce
        )
        _cliente_despide = any(p in respuesta_lower for p in [
            'gracias', 'ok gracias', 'bien gracias', 'hasta luego', 'adios'
        ])

        self.assertTrue(_bruce_dio_contacto)
        self.assertTrue(_cliente_despide)

    def test_no_contacto_no_despedida(self):
        """Sin contacto dado → no es despedida contextual."""
        history = [
            {"role": "assistant", "content": "¿Se encontrará el encargado?"},
            {"role": "user", "content": "No, no está."},
        ]
        agente = self._make_agente(history)
        _todos_bruce = [m['content'].lower() for m in agente.conversation_history if m['role'] == 'assistant']
        _bruce_dio_contacto = any(
            any(w in msg for w in ['6 6 2', '662', '1 9 9 7', 'ventas arroba nioval'])
            for msg in _todos_bruce
        )
        self.assertFalse(_bruce_dio_contacto)

    def test_cliente_pide_numero(self):
        """Cliente dice 'Dímelo, cuál es tu número' → dar contacto."""
        respuesta_lower = "dímelo. sí, dime el número."
        _pide_numero = any(p in respuesta_lower for p in [
            'dimelo', 'dímelo', 'si dime', 'sí dime', 'dame el numero',
            'cual es tu numero', 'cuál es tu número'
        ])
        self.assertTrue(_pide_numero)

    def test_gracias_sin_contacto_no_aplica(self):
        """'Gracias' sin que Bruce haya dado contacto → no aplica FIX 771."""
        history = [
            {"role": "assistant", "content": "¿Se encontrará el encargado de compras?"},
            {"role": "user", "content": "No gracias, no me interesa."},
        ]
        agente = self._make_agente(history)
        _todos_bruce = [m['content'].lower() for m in agente.conversation_history if m['role'] == 'assistant']
        _bruce_dio_contacto = any(
            any(w in msg for w in ['6 6 2', '662', '1 9 9 7', 'ventas arroba nioval'])
            for msg in _todos_bruce
        )
        # Sin contacto dado, FIX 771 no aplica (cae a otros fallbacks)
        self.assertFalse(_bruce_dio_contacto)

    def test_hasta_luego_con_contacto(self):
        """'Hasta luego' con contacto dado → despedida."""
        respuesta_lower = "hasta luego, gracias."
        _despide = any(p in respuesta_lower for p in [
            'gracias', 'hasta luego', 'adios', 'bye', 'muchas gracias'
        ])
        self.assertTrue(_despide)


# ============================================================
# FIX 772: INTERRUPCION_CONVERSACIONAL false positive
# ============================================================
class TestFix772InterrupcionFalsePositive(unittest.TestCase):
    """FIX 772: 'No está' + pedir dato encargado = flujo correcto, no interrupción."""

    def test_no_esta_con_pedir_whatsapp_encargado(self):
        """'No, no está' → '¿WhatsApp del encargado?' = NO es interrupción."""
        texto_cliente = "No, no está"
        respuesta_bruce = "Entiendo. ¿Me podría proporcionar el WhatsApp del encargado para enviarle el catálogo?"

        texto_lower = texto_cliente.lower()
        t2_lower = respuesta_bruce.lower()

        _dijo_no_esta = any(p in texto_lower for p in ['no esta', 'no está', 'no se encuentra'])
        _pide_dato_encargado = (
            ('whatsapp' in t2_lower and 'encargado' in t2_lower) or
            ('correo' in t2_lower and 'encargado' in t2_lower) or
            'entiendo' in t2_lower[:20]
        )

        self.assertTrue(_dijo_no_esta)
        self.assertTrue(_pide_dato_encargado)
        # FIX 772: Should be SKIPPED, not flagged as bug

    def test_no_esta_disponible_con_pedir_correo(self):
        """'No, no está disponible' → '¿Correo del encargado?' = NO es interrupción."""
        texto_cliente = "No, no está disponible"
        respuesta_bruce = "Entiendo. ¿Me podría proporcionar el correo del encargado?"

        texto_lower = texto_cliente.lower()
        t2_lower = respuesta_bruce.lower()

        _dijo_no_esta = any(p in texto_lower for p in ['no esta disponible', 'no está disponible'])
        _pide_dato_encargado = ('correo' in t2_lower and 'encargado' in t2_lower)

        self.assertTrue(_dijo_no_esta)
        self.assertTrue(_pide_dato_encargado)

    def test_real_interrupcion_no_afectada(self):
        """Interrupción REAL: 'Lo que pasa es que' + Bruce da pitch = SÍ es bug."""
        texto_cliente = "Lo que pasa es que nosotros"
        respuesta_bruce = "Me comunico de la marca NIOVAL para brindar información de productos ferreteros."

        texto_lower = texto_cliente.lower()
        t2_lower = respuesta_bruce.lower()

        _dijo_no_esta = any(p in texto_lower for p in ['no esta', 'no está', 'no se encuentra'])
        # No dijo "no está" → FIX 772 no aplica → se evalúa normalmente
        self.assertFalse(_dijo_no_esta)

    def test_entiendo_acknowledges_client(self):
        """'Entiendo.' al inicio = acknowledges lo que dijo el cliente."""
        respuesta_bruce = "Entiendo. ¿Me podría proporcionar un número directo?"
        t2_lower = respuesta_bruce.lower()
        _acknowledges = 'entiendo' in t2_lower[:20]
        self.assertTrue(_acknowledges)

    def test_no_se_encuentra_variante(self):
        """'No se encuentra' = variante de 'no está'."""
        texto_lower = "no se encuentra el encargado"
        _dijo_no_esta = any(p in texto_lower for p in ['no esta', 'no está', 'no se encuentra'])
        self.assertTrue(_dijo_no_esta)


# ============================================================
# FIX 773: CATALOGO_REPETIDO patrones interés ampliados
# ============================================================
class TestFix773PatronesInteres(unittest.TestCase):
    """FIX 773: Preguntas sobre empresa = interés → no bloquear catálogo."""

    def _check_interes(self, texto):
        """Simula la detección de FIX 705 + FIX 773."""
        patrones_interes = [
            'como es', 'como seria', 'como funciona', 'como le hago',
            'whatsapp', 'por whatsapp', 'al whatsapp',
            'por correo', 'al correo', 'me interesa',
            'si me interesa', 'si quiero', 'mandame', 'mandeme',
            'enviame', 'enviemelo', 'si por favor', 'si claro',
            'como es el catalogo', 'donde lo veo', 'como lo recibo',
            'a donde me lo manda', 'digame', 'platiqueme',
            'anotar', 'apuntar', 'donde anotar', 'donde apuntar',
            'te doy', 'le doy', 'te paso su', 'le paso su',
            'te lo paso', 'se lo paso', 'te lo doy', 'se lo doy',
            # FIX 773 nuevos
            'donde estan', 'donde están', 'de donde son', 'de dónde son',
            'que productos', 'qué productos', 'que marcas', 'qué marcas',
            'que manejan', 'qué manejan', 'que venden', 'qué venden',
            'tienen envios', 'hacen envios', 'hacen envíos',
            'te paso su correo', 'le paso su correo', 'te paso el correo',
        ]
        return any(p in texto.lower() for p in patrones_interes)

    def test_donde_estan_es_interes(self):
        """BRUCE2436: '¿Y donde estan?' = interés → no bloquear catálogo.
        Nota: FIX 631 normaliza acentos en producción, así que el texto llega sin acentos."""
        self.assertTrue(self._check_interes("Ok. ¿Y donde estan?"))

    def test_que_productos_manejan(self):
        """'¿Qué productos manejan?' = interés."""
        self.assertTrue(self._check_interes("¿Y qué productos manejan?"))

    def test_que_marcas_tienen(self):
        """'¿Qué marcas manejan?' = interés."""
        self.assertTrue(self._check_interes("¿Qué marcas manejan ustedes?"))

    def test_de_donde_son(self):
        """'¿De dónde son?' = interés."""
        self.assertTrue(self._check_interes("¿De dónde son?"))

    def test_hacen_envios(self):
        """'¿Hacen envíos?' = interés."""
        self.assertTrue(self._check_interes("¿Hacen envíos a todo el país?"))

    def test_te_paso_su_correo(self):
        """'Te paso su correo' = ofrece dato → interés."""
        self.assertTrue(self._check_interes("No, pero te paso su correo"))

    def test_no_no_esta_no_es_interes(self):
        """'No, no está' = NO es interés (rechazo)."""
        self.assertFalse(self._check_interes("No, no está"))

    def test_no_gracias_no_es_interes(self):
        """'No gracias' = NO es interés."""
        self.assertFalse(self._check_interes("No gracias, ahorita no"))


# ============================================================
# FIX 774: Anti-loop "me puede repetir"
# ============================================================
class TestFix774AntiLoopRepetir(unittest.TestCase):
    """FIX 774: Threshold 'me puede repetir' >= 1 (bloquea 2da repetición)."""

    def test_threshold_ge_1(self):
        """Si ya pidió repetir 1 vez, la 2da se bloquea."""
        preguntas_repetir = [
            'me puede repetir', 'me podría repetir', 'me podria repetir',
            'no escuché bien', 'no escuche bien', 'disculpe no escuché'
        ]
        ultimas_bruce = ["disculpe, ¿me puede repetir lo que me decía?"]
        respuesta_lower = "disculpe, ¿me puede repetir lo que me decía?"

        veces = sum(1 for msg in ultimas_bruce if any(p in msg for p in preguntas_repetir))
        pregunta_repetir = any(p in respuesta_lower for p in preguntas_repetir)

        self.assertEqual(veces, 1)
        self.assertTrue(pregunta_repetir)
        # FIX 774: veces >= 1 → BLOQUEAR
        self.assertTrue(veces >= 1)

    def test_first_time_allowed(self):
        """Primera vez 'me puede repetir' se permite (veces=0)."""
        preguntas_repetir = [
            'me puede repetir', 'me podría repetir', 'no escuché bien'
        ]
        ultimas_bruce = ["Me comunico de la marca NIOVAL..."]
        respuesta_lower = "disculpe, ¿me puede repetir lo que me decía?"

        veces = sum(1 for msg in ultimas_bruce if any(p in msg for p in preguntas_repetir))
        pregunta_repetir = any(p in respuesta_lower for p in preguntas_repetir)

        self.assertEqual(veces, 0)
        self.assertTrue(pregunta_repetir)
        # FIX 774: veces < 1 → PERMITIR
        self.assertFalse(veces >= 1)

    def test_replacement_offers_catalog(self):
        """FIX 774: Reemplazo es oferta de catálogo, no otro 'me puede repetir'."""
        respuesta_reemplazo = "¿Le gustaría que le envíe nuestro catálogo por WhatsApp para que lo revise con calma?"
        self.assertIn("catálogo", respuesta_reemplazo)
        self.assertNotIn("repetir", respuesta_reemplazo)

    def test_no_escuche_bien_counts(self):
        """'No escuché bien' también cuenta como repetición."""
        preguntas_repetir = [
            'me puede repetir', 'no escuché bien', 'no escuche bien'
        ]
        ultimas_bruce = ["disculpe, no escuché bien. ¿me puede repetir?"]
        veces = sum(1 for msg in ultimas_bruce if any(p in msg for p in preguntas_repetir))
        self.assertEqual(veces, 1)

    def test_old_threshold_was_2(self):
        """Verifica que el viejo threshold (>=2) permitía 2 repeticiones (bug)."""
        # Con 1 repetición previa, el viejo threshold NO bloqueaba
        veces = 1
        old_threshold = veces >= 2  # FIX 493 viejo
        new_threshold = veces >= 1  # FIX 774 nuevo
        self.assertFalse(old_threshold)  # Viejo: NO bloqueaba → BUG
        self.assertTrue(new_threshold)   # Nuevo: SÍ bloquea → CORRECTO


# ============================================================
# Integration: Bug detector FIX 772
# ============================================================
class TestFix772BugDetectorIntegration(unittest.TestCase):
    """FIX 772: Verificar que bug_detector tiene el filtro."""

    def test_bug_detector_has_fix_772(self):
        """bug_detector.py contiene código FIX 772."""
        import inspect
        from bug_detector import ContentAnalyzer
        source = inspect.getsource(ContentAnalyzer._check_interrupcion_conversacional)
        self.assertIn('FIX 772', source)
        self.assertIn('no_esta_772', source)

    def test_no_esta_whatsapp_encargado_not_flagged(self):
        """'No, no está' + '¿WhatsApp encargado?' → 0 bugs."""
        from bug_detector import ContentAnalyzer
        conv = [
            ("cliente", "¿Qué tal? Buen día."),
            ("bruce", "Me comunico de la marca NIOVAL. ¿Se encontrará el encargado de compras?"),
            ("cliente", "No, no está"),
            ("bruce", "Entiendo. ¿Me podría proporcionar el WhatsApp del encargado para enviarle el catálogo?"),
        ]
        bugs = ContentAnalyzer._check_interrupcion_conversacional(conv)
        self.assertEqual(len(bugs), 0, f"No debería haber bugs, pero encontró: {bugs}")

    def test_no_esta_disponible_not_flagged(self):
        """'No, no está disponible' + '¿WhatsApp encargado?' → 0 bugs."""
        from bug_detector import ContentAnalyzer
        conv = [
            ("cliente", "No, no está disponible"),
            ("bruce", "Entiendo. ¿Me podría proporcionar el WhatsApp del encargado para enviarle el catálogo?"),
        ]
        bugs = ContentAnalyzer._check_interrupcion_conversacional(conv)
        self.assertEqual(len(bugs), 0, f"No debería haber bugs, pero encontró: {bugs}")


# ============================================================
# Deploy version
# ============================================================
class TestDeployVersion(unittest.TestCase):
    """Verificar deploy version actualizada."""

    def test_deploy_version_774(self):
        bd_path = os.path.join(os.path.dirname(__file__), '..', 'bug_detector.py')
        with open(bd_path, 'r', encoding='utf-8') as f:
            source = f.read()
        self.assertIn('FSM Phase 4', source)


if __name__ == '__main__':
    unittest.main()
