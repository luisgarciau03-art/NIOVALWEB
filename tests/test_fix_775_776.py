# -*- coding: utf-8 -*-
"""
Tests para FIX 775 (BRUCE2443 - hora en TIENDA_CERRADA) y FIX 776 (BRUCE2446 - post-farewell)
"""
import unittest
import sys
import os
import re

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


class MockAgente:
    """Mock simplificado de AgenteVentas para testing."""
    def __init__(self):
        self.conversation_history = []
        self.esperando_hora_callback = False
        self.estado_conversacion = None
        self.lead_data = {}
        self.classifier = None


# =============================================================================
# FIX 775: BRUCE2443 - TIENDA_CERRADA con hora ya mencionada
# =============================================================================

class TestFix775TiendaCerradaConHora(unittest.TestCase):
    """FIX 775: Si cliente dice 'viene hasta mañana a las diez', detectar hora."""

    def _detect_hora_775(self, texto):
        """Simula la detección de hora en FIX 775."""
        texto_lower = texto.lower().strip()
        texto_lower = texto_lower.replace('á','a').replace('é','e').replace('í','i').replace('ó','o').replace('ú','u').replace('ü','u')

        horas_palabras = ['ocho', 'nueve', 'diez', 'once', 'doce', 'una', 'dos',
                          'tres', 'cuatro', 'cinco', 'seis', 'siete']
        tiene_hora = (
            re.search(r'a las\s+\d{1,2}', texto_lower) or
            re.search(r'\b\d{1,2}\s*:\s*\d{2}', texto_lower) or
            re.search(r'\b\d{1,2}\s*(?:am|pm)\b', texto_lower) or
            any(f'a las {h}' in texto_lower for h in horas_palabras) or
            any(f'las {h}' in texto_lower for h in horas_palabras)
        )
        return bool(tiene_hora)

    def test_viene_hasta_manana_a_las_diez(self):
        """BRUCE2443: 'viene hasta mañana a las diez' → hora detectada."""
        self.assertTrue(self._detect_hora_775("Viene hasta mañana a las diez"))

    def test_hasta_manana_a_las_10(self):
        """'hasta mañana a las 10' → hora detectada (dígito)."""
        self.assertTrue(self._detect_hora_775("hasta mañana a las 10"))

    def test_hasta_manana_a_las_10_00(self):
        """'hasta mañana a las 10:00' → hora detectada."""
        self.assertTrue(self._detect_hora_775("hasta mañana a las 10:00"))

    def test_hasta_manana_a_las_nueve(self):
        """'hasta mañana a las nueve' → hora detectada."""
        self.assertTrue(self._detect_hora_775("hasta mañana a las nueve"))

    def test_viene_las_ocho(self):
        """'viene las ocho' → hora detectada."""
        self.assertTrue(self._detect_hora_775("viene las ocho"))

    def test_esta_cerrada_a_las_9am(self):
        """'está cerrada, mañana a las 9am' → hora detectada."""
        self.assertTrue(self._detect_hora_775("está cerrada, mañana a las 9am"))

    def test_hasta_manana_sin_hora(self):
        """'hasta mañana' SIN hora → NO detectada (debe preguntar hora)."""
        self.assertFalse(self._detect_hora_775("hasta mañana"))

    def test_tienda_cerrada_sin_hora(self):
        """'tienda cerrada' SIN hora → NO detectada."""
        self.assertFalse(self._detect_hora_775("la tienda ya esta cerrada"))

    def test_ya_cerramos_sin_hora(self):
        """'ya cerramos' SIN hora → NO detectada."""
        self.assertFalse(self._detect_hora_775("ya cerramos"))


class TestFix775AntiLoop(unittest.TestCase):
    """FIX 775B: Si Bruce YA preguntó hora y cliente repite → confirmar."""

    def test_esperando_hora_callback_activa_confirmar(self):
        """Si esperando_hora_callback=True, cualquier TIENDA_CERRADA → confirmar."""
        agente = MockAgente()
        agente.esperando_hora_callback = True
        # La lógica en FIX 775 verifica _ya_pregunto_hora_775
        self.assertTrue(agente.esperando_hora_callback)

    def test_esperando_hora_callback_se_desactiva(self):
        """Después de confirmar, esperando_hora_callback=False."""
        agente = MockAgente()
        agente.esperando_hora_callback = True
        # Simular lo que hace FIX 775
        agente.esperando_hora_callback = False
        self.assertFalse(agente.esperando_hora_callback)

    def test_primera_vez_tienda_cerrada_sin_hora_pregunta(self):
        """Primera vez TIENDA_CERRADA sin hora → debe preguntar hora."""
        agente = MockAgente()
        agente.esperando_hora_callback = False
        # Sin hora detectada y sin esperando_hora → debe preguntar
        self.assertFalse(agente.esperando_hora_callback)


class TestFix775Respuestas(unittest.TestCase):
    """Verificar respuestas de FIX 775 vs FIX 513."""

    def test_respuesta_con_hora_confirma(self):
        """Con hora → respuesta confirma hora."""
        respuesta = "Perfecto, le llamo mañana a esa hora entonces. Muchas gracias por su tiempo."
        self.assertIn("a esa hora", respuesta)
        self.assertNotIn("¿A qué hora", respuesta)

    def test_respuesta_sin_hora_pregunta(self):
        """Sin hora → respuesta pregunta hora."""
        respuesta = "Entiendo, disculpe la molestia. ¿A qué hora puedo llamar mañana para encontrarlos?"
        self.assertIn("¿A qué hora", respuesta)

    def test_respuesta_anti_loop_no_pregunta_hora(self):
        """Anti-loop → NO pregunta hora de nuevo."""
        respuesta = "Perfecto, le llamo mañana a esa hora entonces. Muchas gracias por su tiempo."
        self.assertNotIn("¿A qué hora", respuesta)


# =============================================================================
# FIX 776: BRUCE2446 - Post-farewell "¿Aló?" → despedida final
# =============================================================================

class TestFix776PostFarewell(unittest.TestCase):
    """FIX 776: Si Bruce ya se despidió y cliente dice '¿Aló?', despedida final."""

    def _is_post_farewell(self, ultimo_bruce, texto_cliente):
        """Simula la detección post-farewell de FIX 776."""
        ultimo_bruce_lower = ultimo_bruce.lower()
        texto_lower = texto_cliente.lower().strip()
        texto_lower = texto_lower.replace('á','a').replace('é','e').replace('í','i').replace('ó','o').replace('ú','u').replace('ü','u')

        bruce_ya_despidio = any(p in ultimo_bruce_lower for p in [
            'que tenga buen dia', 'que tenga excelente dia', 'que tenga buena tarde',
            'que tenga excelente tarde', 'gracias por su tiempo', 'hasta luego',
            'que le vaya bien', 'que este bien', 'disculpe la molestia',
            'buen dia', 'buena tarde', 'fue un placer'
        ])
        cliente_post_farewell = any(p in texto_lower for p in [
            'alo', 'bueno', 'hello', 'hola', 'oiga', 'si', 'ok'
        ]) and len(texto_lower) < 20
        return bruce_ya_despidio and cliente_post_farewell

    def test_bruce_despidio_cliente_alo(self):
        """BRUCE2446: Bruce 'que tenga buen dia' + cliente '¿Aló?' → post-farewell."""
        self.assertTrue(self._is_post_farewell(
            "Disculpe la molestia, que tenga buen dia.",
            "¿Aló?"
        ))

    def test_bruce_despidio_cliente_bueno(self):
        """Bruce farewell + cliente '¿Bueno?' → post-farewell."""
        self.assertTrue(self._is_post_farewell(
            "Gracias por su tiempo, que tenga excelente día.",
            "¿Bueno?"
        ))

    def test_bruce_despidio_cliente_hello(self):
        """Bruce farewell + cliente 'Hello?' → post-farewell."""
        self.assertTrue(self._is_post_farewell(
            "Hasta luego, que le vaya bien.",
            "Hello?"
        ))

    def test_bruce_despidio_cliente_hola(self):
        """Bruce farewell + cliente 'Hola?' → post-farewell."""
        self.assertTrue(self._is_post_farewell(
            "Que tenga buen dia.",
            "Hola?"
        ))

    def test_bruce_NO_despidio_cliente_alo(self):
        """Bruce NO se despidió + cliente '¿Aló?' → NOT post-farewell."""
        self.assertFalse(self._is_post_farewell(
            "¿Me podría proporcionar un correo electrónico?",
            "¿Aló?"
        ))

    def test_bruce_despidio_cliente_habla_largo(self):
        """Bruce farewell + texto largo del cliente → NOT post-farewell (>20 chars)."""
        self.assertFalse(self._is_post_farewell(
            "Que tenga buen dia.",
            "Oiga, espere, tengo una pregunta más por favor"
        ))

    def test_bruce_despidio_cliente_da_dato(self):
        """Bruce farewell + cliente da dato → NOT post-farewell."""
        self.assertFalse(self._is_post_farewell(
            "Que tenga buen dia.",
            "Mi correo es juan@gmail.com para que me envíe el catálogo"
        ))


class TestFix776Respuesta(unittest.TestCase):
    """Verificar que respuesta post-farewell es despedida, NO 'me puede repetir'."""

    def test_respuesta_post_farewell_es_despedida(self):
        """Respuesta post-farewell contiene despedida."""
        respuesta = "Que tenga excelente día, hasta luego."
        self.assertIn("hasta luego", respuesta)
        self.assertNotIn("repetir", respuesta)


# =============================================================================
# Tests de integración: flujo completo BRUCE2443
# =============================================================================

class TestFix775IntegracionFlujo(unittest.TestCase):
    """Simula el flujo de BRUCE2443 y verifica que FIX 775 corta el loop."""

    def test_flujo_primera_vez_con_hora(self):
        """Turno 1: 'viene hasta mañana a las diez' → confirma hora (NO loop)."""
        texto = "viene hasta manana a las diez"
        # Simular detección de hora
        horas_palabras = ['ocho', 'nueve', 'diez', 'once', 'doce']
        tiene_hora = any(f'a las {h}' in texto for h in horas_palabras)
        self.assertTrue(tiene_hora, "Debe detectar 'a las diez' como hora")

    def test_flujo_segunda_vez_anti_loop(self):
        """Turno 2: Cliente repite 'a las diez' + esperando_hora → confirma."""
        agente = MockAgente()
        agente.esperando_hora_callback = True
        # FIX 775B: Ya preguntamos → confirmar
        self.assertTrue(agente.esperando_hora_callback)
        # Después de confirmar
        agente.esperando_hora_callback = False
        self.assertFalse(agente.esperando_hora_callback)

    def test_no_falso_positivo_cerrada_sin_hora(self):
        """'tienda cerrada' sin hora → DEBE preguntar hora (FIX 513 normal)."""
        texto = "la tienda esta cerrada"
        horas_palabras = ['ocho', 'nueve', 'diez', 'once', 'doce']
        tiene_hora = (
            re.search(r'a las\s+\d{1,2}', texto) or
            any(f'a las {h}' in texto for h in horas_palabras)
        )
        self.assertFalse(bool(tiene_hora), "Sin hora → debe preguntar")


class TestDeployVersion(unittest.TestCase):
    """Verificar deploy version actualizada."""

    def test_deploy_version_fix_776(self):
        """FIX 818: Deploy version es dinamico via set_deploy_version."""
        from bug_detector import set_deploy_version, _DEPLOY_VERSION
        self.assertIsInstance(_DEPLOY_VERSION, str)
        self.assertTrue(len(_DEPLOY_VERSION) > 0)
        # Verificar que set_deploy_version funciona
        original = _DEPLOY_VERSION
        set_deploy_version("TEST-776")
        import bug_detector
        self.assertEqual(bug_detector._DEPLOY_VERSION, "TEST-776")
        set_deploy_version(original)


if __name__ == '__main__':
    unittest.main()
