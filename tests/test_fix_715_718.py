"""
Tests para FIX 715-718: Nuevos detectores de bugs y ajuste de threshold.

FIX 715: RESPUESTA_FILLER_INCOHERENTE - ElevenLabs TTS falla → "dejeme_ver" filler
FIX 716: AREA_EQUIVOCADA / NO_MANEJA_FERRETERIA - Cliente dice que no es ferretería
FIX 717: Ajuste threshold ultra-short 25s→20s (BRUCE2284: 24s no detectado)
FIX 718: DICTADO_INTERRUMPIDO - Cliente dictando dato, Bruce se despide

Suite: 52 tests
"""
import sys
import os
import unittest
import re

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from bug_detector import (
    CallEventTracker, BugDetector, ContentAnalyzer,
    GPT_EVAL_MIN_DURACION_S, GPT_EVAL_DURACION_CORTA_S,
    GPT_EVAL_MIN_TURNOS, GPT_EVAL_MIN_TURNOS_COMPLETO,
    CRITICO, ALTO, MEDIO
)


# ============================================================
# FIX 715: RESPUESTA_FILLER_INCOHERENTE
# ============================================================
class TestFix715FillerIncoherente(unittest.TestCase):
    """FIX 715: Detectar cuando ElevenLabs TTS falla y se usa filler audio."""

    def _make_tracker(self, filler_count=0):
        t = CallEventTracker("sid_test", "BRUCE_TEST", "+521234567890")
        for _ in range(filler_count):
            t.emit("FILLER_162A", {"respuesta_original": "test response"})
        return t

    def test_filler_counter_initialized_zero(self):
        """Tracker inicia con filler_162a_count = 0."""
        t = CallEventTracker("sid", "BRUCE1", "+52")
        self.assertEqual(t.filler_162a_count, 0)

    def test_filler_event_increments_counter(self):
        """Evento FILLER_162A incrementa el contador."""
        t = CallEventTracker("sid", "BRUCE1", "+52")
        t.emit("FILLER_162A", {})
        self.assertEqual(t.filler_162a_count, 1)
        t.emit("FILLER_162A", {})
        self.assertEqual(t.filler_162a_count, 2)

    def test_filler_1x_detecta_bug(self):
        """1 uso de filler → bug RESPUESTA_FILLER_INCOHERENTE detectado."""
        t = self._make_tracker(filler_count=1)
        t.emit("BRUCE_RESPONDE", {"texto": "Pitch de prueba"})
        t.emit("CLIENTE_DICE", {"texto": "No me interesa"})
        bugs = BugDetector.analyze(t)
        filler_bugs = [b for b in bugs if b["tipo"] == "RESPUESTA_FILLER_INCOHERENTE"]
        self.assertEqual(len(filler_bugs), 1)
        self.assertEqual(filler_bugs[0]["severidad"], ALTO)
        self.assertIn("1x", filler_bugs[0]["detalle"])

    def test_filler_3x_detecta_bug_con_conteo(self):
        """3 usos de filler → bug con conteo correcto."""
        t = self._make_tracker(filler_count=3)
        t.emit("BRUCE_RESPONDE", {"texto": "Pitch de prueba"})
        bugs = BugDetector.analyze(t)
        filler_bugs = [b for b in bugs if b["tipo"] == "RESPUESTA_FILLER_INCOHERENTE"]
        self.assertEqual(len(filler_bugs), 1)
        self.assertIn("3x", filler_bugs[0]["detalle"])

    def test_sin_filler_no_detecta_bug(self):
        """Sin filler → sin bug RESPUESTA_FILLER_INCOHERENTE."""
        t = self._make_tracker(filler_count=0)
        t.emit("BRUCE_RESPONDE", {"texto": "Pitch de prueba"})
        t.emit("CLIENTE_DICE", {"texto": "No me interesa"})
        bugs = BugDetector.analyze(t)
        filler_bugs = [b for b in bugs if b["tipo"] == "RESPUESTA_FILLER_INCOHERENTE"]
        self.assertEqual(len(filler_bugs), 0)

    def test_filler_categoria_tecnico(self):
        """Bug filler tiene categoría 'tecnico'."""
        t = self._make_tracker(filler_count=1)
        bugs = BugDetector.analyze(t)
        filler_bugs = [b for b in bugs if b["tipo"] == "RESPUESTA_FILLER_INCOHERENTE"]
        self.assertEqual(filler_bugs[0]["categoria"], "tecnico")

    def test_filler_detalle_incluye_elevenlabs(self):
        """Detalle del bug menciona ElevenLabs."""
        t = self._make_tracker(filler_count=2)
        bugs = BugDetector.analyze(t)
        filler_bugs = [b for b in bugs if b["tipo"] == "RESPUESTA_FILLER_INCOHERENTE"]
        self.assertIn("ElevenLabs", filler_bugs[0]["detalle"])


# ============================================================
# FIX 715 - Escenarios reales
# ============================================================
class TestFix715EscenariosReales(unittest.TestCase):
    """FIX 715: Escenarios basados en llamadas auditadas."""

    def test_bruce2268_filler_4x(self):
        """BRUCE2268: 4 usos de filler → detectado."""
        t = CallEventTracker("sid_2268", "BRUCE2268", "+528712223299")
        for _ in range(4):
            t.emit("FILLER_162A", {})
        t.emit("BRUCE_RESPONDE", {"texto": "Me comunico de la marca nioval..."})
        t.emit("CLIENTE_DICE", {"texto": "Electronita. Es la economica."})
        bugs = BugDetector.analyze(t)
        filler_bugs = [b for b in bugs if b["tipo"] == "RESPUESTA_FILLER_INCOHERENTE"]
        self.assertEqual(len(filler_bugs), 1)
        self.assertIn("4x", filler_bugs[0]["detalle"])

    def test_bruce2281_filler_1x(self):
        """BRUCE2281: 1 uso de filler → detectado."""
        t = CallEventTracker("sid_2281", "BRUCE2281", "+528717506496")
        t.emit("FILLER_162A", {})
        t.emit("BRUCE_RESPONDE", {"texto": "Me comunico de la marca nioval..."})
        t.emit("CLIENTE_DICE", {"texto": "No, ese en el corporativo de Cemex"})
        t.emit("BRUCE_RESPONDE", {"texto": "Aja, si."})
        bugs = BugDetector.analyze(t)
        filler_bugs = [b for b in bugs if b["tipo"] == "RESPUESTA_FILLER_INCOHERENTE"]
        self.assertEqual(len(filler_bugs), 1)


# ============================================================
# FIX 716: AREA_EQUIVOCADA / NO_MANEJA_FERRETERIA
# ============================================================
class TestFix716AreaEquivocada(unittest.TestCase):
    """FIX 716: Detectar cuando cliente dice que no es ferretería."""

    def test_no_manejo_ferreteria(self):
        """'No manejo nada de ferretería' + Bruce sigue vendiendo → bug."""
        conv = [
            ("bruce", "Me comunico de la marca nioval, productos ferreteros..."),
            ("cliente", "No manejo nada de ferreteria, joven, se lo agradezco bastante"),
            ("bruce", "Me podria proporcionar un numero de WhatsApp?")
        ]
        bugs = ContentAnalyzer._check_area_equivocada(conv)
        self.assertEqual(len(bugs), 1)
        self.assertEqual(bugs[0]["tipo"], "AREA_EQUIVOCADA")
        self.assertEqual(bugs[0]["severidad"], ALTO)

    def test_corporativo_cemex(self):
        """'corporativo de Cemex' + Bruce responde 'aja si' → bug."""
        conv = [
            ("bruce", "Me comunico de la marca nioval..."),
            ("cliente", "No, ese en el corporativo de Cemex, en la ciudad de Monterrey"),
            ("bruce", "Aja, si.")
        ]
        bugs = ContentAnalyzer._check_area_equivocada(conv)
        self.assertEqual(len(bugs), 1)
        self.assertIn("corporativo", bugs[0]["detalle"].lower())

    def test_esto_no_es_ferreteria(self):
        """'Esto no es ferretería' → bug si Bruce sigue."""
        conv = [
            ("bruce", "Se encontrara el encargado de compras?"),
            ("cliente", "Esto no es una ferreteria señor"),
            ("bruce", "Entiendo. Le puedo enviar el catalogo?")
        ]
        bugs = ContentAnalyzer._check_area_equivocada(conv)
        self.assertEqual(len(bugs), 1)

    def test_area_equivocada(self):
        """'Área equivocada' → bug si Bruce sigue."""
        conv = [
            ("bruce", "Se encontrara el encargado?"),
            ("cliente", "No, usted llamo al area equivocada"),
            ("bruce", "Me podria proporcionar un correo electronico?")
        ]
        bugs = ContentAnalyzer._check_area_equivocada(conv)
        self.assertEqual(len(bugs), 1)

    def test_no_vendemos_eso(self):
        """'No vendemos eso' → bug si Bruce sigue."""
        conv = [
            ("bruce", "Productos ferreteros..."),
            ("cliente", "No vendemos eso aqui, somos restaurante"),
            ("bruce", "Le envio el catalogo por WhatsApp?")
        ]
        bugs = ContentAnalyzer._check_area_equivocada(conv)
        self.assertEqual(len(bugs), 1)

    def test_bruce_se_despide_no_bug(self):
        """Si Bruce se despide correctamente después del rechazo → NO es bug."""
        conv = [
            ("bruce", "Me comunico de la marca nioval..."),
            ("cliente", "No manejo nada de ferreteria, joven"),
            ("bruce", "Entendido, muchas gracias por su tiempo, que tenga buen dia.")
        ]
        bugs = ContentAnalyzer._check_area_equivocada(conv)
        self.assertEqual(len(bugs), 0)

    def test_no_es_aqui(self):
        """'Aquí no es' → bug si Bruce continúa vendiendo."""
        conv = [
            ("bruce", "Se encontrara el encargado de compras?"),
            ("cliente", "Aqui no es, marco mal"),
            ("bruce", "Me podria proporcionar su WhatsApp?")
        ]
        bugs = ContentAnalyzer._check_area_equivocada(conv)
        self.assertEqual(len(bugs), 1)

    def test_no_manejamos_eso(self):
        """'No manejamos eso' → bug."""
        conv = [
            ("bruce", "Productos ferreteros de nioval..."),
            ("cliente", "No manejamos eso, somos una clinica"),
            ("bruce", "Le puedo enviar informacion del catalogo?")
        ]
        bugs = ContentAnalyzer._check_area_equivocada(conv)
        self.assertEqual(len(bugs), 1)

    def test_conv_corta_sin_rechazo(self):
        """Conversación normal sin rechazo → sin bug."""
        conv = [
            ("bruce", "Me comunico de la marca nioval..."),
            ("cliente", "Si, digame"),
        ]
        bugs = ContentAnalyzer._check_area_equivocada(conv)
        self.assertEqual(len(bugs), 0)

    def test_conv_vacia(self):
        """Conversación vacía → sin bug."""
        bugs = ContentAnalyzer._check_area_equivocada([])
        self.assertEqual(len(bugs), 0)

    def test_numero_equivocado(self):
        """'Número equivocado' → bug si Bruce sigue."""
        conv = [
            ("bruce", "Me comunico de la marca nioval..."),
            ("cliente", "Tiene el numero equivocado"),
            ("bruce", "Le puedo enviar el catalogo?")
        ]
        bugs = ContentAnalyzer._check_area_equivocada(conv)
        self.assertEqual(len(bugs), 1)


# ============================================================
# FIX 716 - Escenarios reales
# ============================================================
class TestFix716EscenariosReales(unittest.TestCase):
    """FIX 716: Escenarios basados en llamadas auditadas."""

    def test_bruce2284_no_ferreteria(self):
        """BRUCE2284: 'No manejo nada de ferretería' + 'Aja, si' → bug."""
        conv = [
            ("bruce", "Me comunico de la marca nioval, productos ferreteros, Se encontrara el encargado?"),
            ("cliente", "No manejo nada de ferreteria, joven, se lo agradezco bastante"),
            ("bruce", "Aja, si.")
        ]
        bugs = ContentAnalyzer._check_area_equivocada(conv)
        self.assertEqual(len(bugs), 1)
        self.assertEqual(bugs[0]["tipo"], "AREA_EQUIVOCADA")

    def test_bruce2281_corporativo(self):
        """BRUCE2281: 'corporativo de Cemex, Monterrey' + 'Aja, si' → bug."""
        conv = [
            ("bruce", "Me comunico de la marca nioval, productos ferreteros..."),
            ("cliente", "No, ese en el corporativo de Cemex, en la ciudad de Monterrey"),
            ("bruce", "Aja, si.")
        ]
        bugs = ContentAnalyzer._check_area_equivocada(conv)
        self.assertEqual(len(bugs), 1)


# ============================================================
# FIX 717: THRESHOLD ULTRA-SHORT 25s → 20s
# ============================================================
class TestFix717Threshold(unittest.TestCase):
    """FIX 717: Verificar que el threshold se bajó a 20s."""

    def test_min_duracion_es_20(self):
        """GPT_EVAL_MIN_DURACION_S debe ser 20 (FIX 717)."""
        self.assertEqual(GPT_EVAL_MIN_DURACION_S, 20)

    def test_llamada_19s_skip(self):
        """19s → SKIP total (debajo del threshold)."""
        self.assertLess(19, GPT_EVAL_MIN_DURACION_S)

    def test_llamada_20s_no_skip(self):
        """20s → NO skip (igual al threshold)."""
        self.assertGreaterEqual(20, GPT_EVAL_MIN_DURACION_S)

    def test_llamada_24s_no_skip(self):
        """24s → NO skip (BRUCE2284 ahora sería evaluada)."""
        self.assertGreaterEqual(24, GPT_EVAL_MIN_DURACION_S)

    def test_duracion_corta_sigue_45(self):
        """GPT_EVAL_DURACION_CORTA_S sigue en 45."""
        self.assertEqual(GPT_EVAL_DURACION_CORTA_S, 45)

    def test_turnos_minimo_sigue_2(self):
        """GPT_EVAL_MIN_TURNOS sigue en 2."""
        self.assertEqual(GPT_EVAL_MIN_TURNOS, 2)

    def test_turnos_completo_sigue_3(self):
        """GPT_EVAL_MIN_TURNOS_COMPLETO sigue en 3."""
        self.assertEqual(GPT_EVAL_MIN_TURNOS_COMPLETO, 3)


# ============================================================
# FIX 717 - Escenario real BRUCE2284
# ============================================================
class TestFix717BRUCE2284(unittest.TestCase):
    """FIX 717: BRUCE2284 (24s) ahora entra en GPT eval enfocado."""

    def test_bruce2284_24s_en_rango(self):
        """BRUCE2284 con 24s ahora es >= GPT_EVAL_MIN_DURACION_S (20)."""
        duracion_bruce2284 = 24
        self.assertGreaterEqual(duracion_bruce2284, GPT_EVAL_MIN_DURACION_S)

    def test_bruce2284_es_llamada_corta(self):
        """BRUCE2284 con 24s y 2 turnos es llamada 'corta' (no completa)."""
        duracion = 24
        turnos = 2
        es_corta = (duracion < GPT_EVAL_DURACION_CORTA_S or turnos < GPT_EVAL_MIN_TURNOS_COMPLETO)
        self.assertTrue(es_corta)

    def test_15s_sigue_skip(self):
        """15s sigue siendo SKIP (debajo de 20s)."""
        self.assertLess(15, GPT_EVAL_MIN_DURACION_S)


# ============================================================
# FIX 718: DICTADO_INTERRUMPIDO
# ============================================================
class TestFix718DictadoInterrumpido(unittest.TestCase):
    """FIX 718: Detectar cuando Bruce se despide mientras cliente dicta datos."""

    def test_email_dictado_despedida(self):
        """Cliente dicta email con 'arroba' → Bruce se despide → bug."""
        conv = [
            ("bruce", "Digame el correo"),
            ("cliente", "Es proveedores arroba ferrelaguna punto com"),
            ("bruce", "Perfecto, entonces me comunico despues. Muchas gracias por su tiempo.")
        ]
        bugs = ContentAnalyzer._check_dictado_interrumpido(conv)
        self.assertEqual(len(bugs), 1)
        self.assertEqual(bugs[0]["tipo"], "DICTADO_INTERRUMPIDO")
        self.assertEqual(bugs[0]["severidad"], CRITICO)

    def test_email_con_arroba_symbol(self):
        """Cliente dicta email con '@' → Bruce se despide → bug."""
        conv = [
            ("bruce", "Digame su correo"),
            ("cliente", "ventas@ferreteria.com"),
            ("bruce", "Muchas gracias por su tiempo, que tenga excelente dia.")
        ]
        bugs = ContentAnalyzer._check_dictado_interrumpido(conv)
        self.assertEqual(len(bugs), 1)

    def test_guion_bajo_despedida(self):
        """Cliente dicta 'guión bajo' → Bruce se despide → bug."""
        conv = [
            ("bruce", "Cual es su correo?"),
            ("cliente", "Ale guion bajo Po"),
            ("bruce", "Perfecto, entonces me comunico despues. Muchas gracias por su tiempo.")
        ]
        bugs = ContentAnalyzer._check_dictado_interrumpido(conv)
        self.assertEqual(len(bugs), 1)

    def test_gmail_despedida(self):
        """Cliente dice 'gmail' → Bruce se despide → bug."""
        conv = [
            ("bruce", "Digame el correo"),
            ("cliente", "Es juanperez gmail"),
            ("bruce", "Me comunico despues, que tenga buen dia.")
        ]
        bugs = ContentAnalyzer._check_dictado_interrumpido(conv)
        self.assertEqual(len(bugs), 1)

    def test_punto_com_despedida(self):
        """Cliente dice 'punto com' → Bruce se despide → bug."""
        conv = [
            ("bruce", "Digame"),
            ("cliente", "hotmail punto com"),
            ("bruce", "Nos comunicamos despues, gracias.")
        ]
        bugs = ContentAnalyzer._check_dictado_interrumpido(conv)
        self.assertEqual(len(bugs), 1)

    def test_numero_largo_despedida(self):
        """Cliente dicta número largo → Bruce se despide → bug."""
        conv = [
            ("bruce", "Digame el numero"),
            ("cliente", "Es 8712223344"),
            ("bruce", "Muchas gracias por su tiempo, que tenga excelente dia.")
        ]
        bugs = ContentAnalyzer._check_dictado_interrumpido(conv)
        self.assertEqual(len(bugs), 1)

    def test_dictado_con_confirmacion_no_bug(self):
        """Cliente dicta email → Bruce confirma → NO es bug."""
        conv = [
            ("bruce", "Digame el correo"),
            ("cliente", "Es proveedores arroba ferrelaguna punto com"),
            ("bruce", "Perfecto, lo tengo anotado. Proveedores arroba ferrelaguna punto com.")
        ]
        bugs = ContentAnalyzer._check_dictado_interrumpido(conv)
        self.assertEqual(len(bugs), 0)

    def test_sin_dictado_despedida_no_bug(self):
        """Cliente dice algo normal → Bruce se despide → NO es bug."""
        conv = [
            ("bruce", "Se encontrara el encargado?"),
            ("cliente", "No, ya se fue"),
            ("bruce", "Perfecto, entonces me comunico despues. Muchas gracias.")
        ]
        bugs = ContentAnalyzer._check_dictado_interrumpido(conv)
        self.assertEqual(len(bugs), 0)

    def test_conv_corta_no_bug(self):
        """Conversación muy corta → sin bug."""
        conv = [
            ("bruce", "Hola"),
            ("cliente", "Hola"),
        ]
        bugs = ContentAnalyzer._check_dictado_interrumpido(conv)
        self.assertEqual(len(bugs), 0)

    def test_conv_vacia_no_bug(self):
        """Conversación vacía → sin bug."""
        bugs = ContentAnalyzer._check_dictado_interrumpido([])
        self.assertEqual(len(bugs), 0)

    def test_deletreo_letras_despedida(self):
        """Cliente deletrea con 'a de' → Bruce se despide → bug."""
        conv = [
            ("bruce", "Digame el correo"),
            ("cliente", "A de avion, erre, eme"),
            ("bruce", "Me comunico despues. Que tenga excelente dia.")
        ]
        bugs = ContentAnalyzer._check_dictado_interrumpido(conv)
        self.assertEqual(len(bugs), 1)


# ============================================================
# FIX 718 - Escenarios reales
# ============================================================
class TestFix718EscenariosReales(unittest.TestCase):
    """FIX 718: Escenarios basados en llamadas auditadas."""

    def test_bruce2272_email_sin_respuesta(self):
        """BRUCE2272: Cliente dictó email, Bruce no respondió (DATO_SIN_RESPUESTA cubre,
        pero si hubiera respondido con despedida sería DICTADO_INTERRUMPIDO)."""
        conv = [
            ("bruce", "Si, por favor, digame el correo."),
            ("cliente", "Es proveedores arroba CR Laguna punto com"),
            # Bruce no respondió → DATO_SIN_RESPUESTA cubre esto
            # Pero si hubiera respondido con despedida:
        ]
        # Sin respuesta Bruce, _check_dictado_interrumpido no aplica (no hay "bruce" después)
        bugs = ContentAnalyzer._check_dictado_interrumpido(conv)
        self.assertEqual(len(bugs), 0)

    def test_bruce2274_email_cortado(self):
        """BRUCE2274: Cliente dictando 'Ale guion_bajo Po' → Bruce se despidió."""
        conv = [
            ("bruce", "Perfecto. Cual es su correo electronico?"),
            ("cliente", "Es Ale guion bajo Po."),
            ("bruce", "Perfecto, entonces me comunico despues. Muchas gracias por su tiempo, que tenga excelente dia.")
        ]
        bugs = ContentAnalyzer._check_dictado_interrumpido(conv)
        self.assertEqual(len(bugs), 1)
        self.assertEqual(bugs[0]["tipo"], "DICTADO_INTERRUMPIDO")
        self.assertEqual(bugs[0]["severidad"], CRITICO)


# ============================================================
# FIX 715 - Verificación en código
# ============================================================
class TestFix715EnCodigo(unittest.TestCase):
    """Verificar que FIX 715 está implementado en el código."""

    def test_tracker_tiene_filler_counter(self):
        """CallEventTracker tiene atributo filler_162a_count."""
        t = CallEventTracker("sid", "BRUCE", "+52")
        self.assertTrue(hasattr(t, 'filler_162a_count'))

    def test_tracker_acepta_evento_filler(self):
        """CallEventTracker procesa evento FILLER_162A sin error."""
        t = CallEventTracker("sid", "BRUCE", "+52")
        t.emit("FILLER_162A", {"respuesta_original": "test"})
        self.assertEqual(t.filler_162a_count, 1)

    def test_emit_event_servidor(self):
        """Verificar que servidor_llamadas.py tiene emit_event para FILLER_162A."""
        servidor_path = os.path.join(os.path.dirname(__file__), '..', 'servidor_llamadas.py')
        with open(servidor_path, 'r', encoding='utf-8') as f:
            contenido = f.read()
        self.assertIn('emit_event(call_sid, "FILLER_162A"', contenido)


# ============================================================
# FIX 716 - Verificación en código
# ============================================================
class TestFix716EnCodigo(unittest.TestCase):
    """Verificar que FIX 716 está implementado en el código."""

    def test_patterns_existen(self):
        """_AREA_EQUIVOCADA_PATTERNS existe y tiene patterns."""
        self.assertTrue(hasattr(ContentAnalyzer, '_AREA_EQUIVOCADA_PATTERNS'))
        self.assertGreater(len(ContentAnalyzer._AREA_EQUIVOCADA_PATTERNS), 10)

    def test_method_existe(self):
        """_check_area_equivocada existe como método."""
        self.assertTrue(hasattr(ContentAnalyzer, '_check_area_equivocada'))

    def test_en_bug_detector(self):
        """FIX 716 llamado desde BugDetector.analyze."""
        import inspect
        source = inspect.getsource(BugDetector.analyze)
        self.assertIn('_check_area_equivocada', source)


# ============================================================
# FIX 718 - Verificación en código
# ============================================================
class TestFix718EnCodigo(unittest.TestCase):
    """Verificar que FIX 718 está implementado en el código."""

    def test_dictado_patterns_existen(self):
        """_DICTADO_PATTERNS existe como regex."""
        self.assertTrue(hasattr(ContentAnalyzer, '_DICTADO_PATTERNS'))

    def test_bruce_despedida_existe(self):
        """_BRUCE_DESPEDIDA existe como regex."""
        self.assertTrue(hasattr(ContentAnalyzer, '_BRUCE_DESPEDIDA'))

    def test_method_existe(self):
        """_check_dictado_interrumpido existe como método."""
        self.assertTrue(hasattr(ContentAnalyzer, '_check_dictado_interrumpido'))

    def test_en_bug_detector(self):
        """FIX 718 llamado desde BugDetector.analyze."""
        import inspect
        source = inspect.getsource(BugDetector.analyze)
        self.assertIn('_check_dictado_interrumpido', source)


if __name__ == '__main__':
    unittest.main()
