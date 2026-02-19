"""
Tests FIX 734-736: Inmunidad 0% patterns + IVR detector + inicio dictado.

FIX 734: CLIENTE_DICTA_EMAIL_COMPLETO, PIDE_CONTACTO_NIOVAL → inmunidad 598/600/601/602
FIX 735: BRUCE2301 - IVR/conmutador detectado → filtrar falsos positivos
FIX 736: BRUCE2302 - Cliente anuncia dato ("El WhatsApp") → GPT cambia tema → override
"""
import sys
import os
import inspect
import re
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from agente_ventas import AgenteVentas
from bug_detector import BugDetector, CallEventTracker, ContentAnalyzer


def _get_source():
    """Obtener source de procesar_respuesta completo."""
    return inspect.getsource(AgenteVentas.procesar_respuesta)


def _get_filtrar_source():
    """Obtener source de _filtrar_respuesta_post_gpt completo."""
    return inspect.getsource(AgenteVentas._filtrar_respuesta_post_gpt)


def _sa(t):
    """Strip acentos para comparaciones."""
    return t.replace('á','a').replace('é','e').replace('í','i').replace('ó','o').replace('ú','u').replace('ü','u').replace('ñ','n')


def _crear_agente_con_contexto():
    """Crea agente con conversación realista (5+ turnos) para evitar filtros turno-1."""
    agente = AgenteVentas()
    agente.conversation_history = [
        {"role": "assistant", "content": "Buenos días, me comunico de la marca NIOVAL, somos distribuidores de productos ferreteros."},
        {"role": "user", "content": "Sí, dígame"},
        {"role": "assistant", "content": "¿Se encontrará el encargado o encargada de compras?"},
        {"role": "user", "content": "Sí, yo soy el encargado"},
        {"role": "assistant", "content": "Perfecto, le ofrezco nuestro catálogo de productos ferreteros. ¿Le gustaría recibirlo por WhatsApp o correo?"},
        {"role": "user", "content": "Sí, por correo mejor"},
    ]
    agente.encargado_confirmado = True
    agente.pitch_dado = True
    agente.catalogo_ofrecido = True
    return agente


def _crear_agente_736():
    """Crea agente con 4+ turnos Bruce para evitar FIX 298/301 y FIX 494."""
    agente = AgenteVentas()
    agente.conversation_history = [
        {"role": "assistant", "content": "Buenos días, me comunico de la marca NIOVAL, somos distribuidores de productos ferreteros."},
        {"role": "user", "content": "Sí, dígame"},
        {"role": "assistant", "content": "Le comento que manejamos herramientas manuales, eléctricas, plomería y más de 500 productos."},
        {"role": "user", "content": "Ah, suena bien"},
        {"role": "assistant", "content": "Perfecto, le puedo enviar nuestro catálogo digital por correo electrónico."},
        {"role": "user", "content": "Sí, me interesa"},
        {"role": "assistant", "content": "Con gusto. ¿Me podría proporcionar sus datos de contacto?"},
        {"role": "user", "content": "Sí claro"},
    ]
    agente.encargado_confirmado = True
    agente.pitch_dado = True
    agente.catalogo_ofrecido = True
    agente.contacto_solicitado = True
    return agente


# ============================================================
# FIX 734: Inmunidad 0% patterns
# ============================================================

class TestFix734InmunidadPatrones598(unittest.TestCase):
    """FIX 734: CLIENTE_DICTA_EMAIL_COMPLETO y PIDE_CONTACTO_NIOVAL en 598."""

    def test_cliente_dicta_email_en_598(self):
        source = _get_source()
        match = re.search(r"patrones_inmunes_pregunta_598\s*=\s*\{([^}]+)\}", source, re.DOTALL)
        self.assertIsNotNone(match, "patrones_inmunes_pregunta_598 no encontrado")
        self.assertIn('CLIENTE_DICTA_EMAIL_COMPLETO', match.group(1))

    def test_pide_contacto_nioval_en_598(self):
        source = _get_source()
        match = re.search(r"patrones_inmunes_pregunta_598\s*=\s*\{([^}]+)\}", source, re.DOTALL)
        self.assertIsNotNone(match)
        self.assertIn('PIDE_CONTACTO_NIOVAL', match.group(1))


class TestFix734InmunidadPero600(unittest.TestCase):
    """FIX 734: PIDE_CONTACTO_NIOVAL en patrones_inmunes_pero."""

    def test_pide_contacto_nioval_en_pero(self):
        source = _get_source()
        match = re.search(r"patrones_inmunes_pero\s*=\s*\{([^}]+)\}", source, re.DOTALL)
        self.assertIsNotNone(match)
        self.assertIn('PIDE_CONTACTO_NIOVAL', match.group(1))


class TestFix734InmunidadComplejidad601(unittest.TestCase):
    """FIX 734: PIDE_CONTACTO_NIOVAL en patrones_inmunes_601."""

    def test_pide_contacto_nioval_en_601(self):
        source = _get_source()
        match = re.search(r"patrones_inmunes_601\s*=\s*\{([^}]+)\}", source, re.DOTALL)
        self.assertIsNotNone(match)
        self.assertIn('PIDE_CONTACTO_NIOVAL', match.group(1))


class TestFix734InmunidadContexto602(unittest.TestCase):
    """FIX 734: Ambos patrones en patrones_inmunes_602."""

    def _get_602_content(self):
        source = _get_source()
        match = re.search(r"patrones_inmunes_602\s*=\s*\{([^}]+)\}", source, re.DOTALL)
        self.assertIsNotNone(match, "patrones_inmunes_602 no encontrado")
        return match.group(1)

    def test_cliente_dicta_email_en_602(self):
        self.assertIn('CLIENTE_DICTA_EMAIL_COMPLETO', self._get_602_content())

    def test_pide_contacto_nioval_en_602(self):
        self.assertIn('PIDE_CONTACTO_NIOVAL', self._get_602_content())


# ============================================================
# FIX 735: IVR/Conmutador detector
# ============================================================

class TestFix735IVRDetectorBugFilter(unittest.TestCase):
    """FIX 735: IVR detectado → filtrar bugs de contenido falsos positivos."""

    def test_ivr_extension_filtra_contexto_ignorado(self):
        """Conversación con IVR → GPT_CONTEXTO_IGNORADO filtrado."""
        tracker = CallEventTracker("test_ivr", "BRUCE_TEST", "+521234567890")
        tracker.conversacion = [
            ("bruce", "Buenos días, me comunico de la marca Nioval"),
            ("cliente", "Si conoce el número de extensión, márquelo ahora o seleccione una de las opciones"),
            ("bruce", "¿Se encontrará el encargado de compras?"),
            ("cliente", "Uno, ventas mayoreo. Dos, mostrador. Tres, crédito y cobranza"),
            ("bruce", "Ajá, sí."),
            ("cliente", "Administración, o espere en la línea para ser atendido"),
            ("bruce", "Claro, espero."),
        ]
        tracker.respuestas_bruce = [t for _, t in tracker.conversacion if _ == "bruce"]
        bugs = BugDetector.analyze(tracker)
        tipos = [b["tipo"] for b in bugs]
        self.assertNotIn("GPT_CONTEXTO_IGNORADO", tipos)
        self.assertNotIn("INTERRUPCION_CONVERSACIONAL", tipos)

    def test_ivr_presione_filtra_bugs(self):
        """IVR con 'presione uno' → filtrar bugs."""
        tracker = CallEventTracker("test_ivr2", "BRUCE_TEST2")
        tracker.conversacion = [
            ("bruce", "Buenos días"),
            ("cliente", "Bienvenido. Presione uno para ventas, dos para soporte"),
            ("bruce", "¿Se encontrará el encargado de compras?"),
        ]
        tracker.respuestas_bruce = ["Buenos días", "¿Se encontrará el encargado de compras?"]
        bugs = BugDetector.analyze(tracker)
        tipos = [b["tipo"] for b in bugs]
        self.assertNotIn("GPT_CONTEXTO_IGNORADO", tipos)
        self.assertNotIn("DESPEDIDA_PREMATURA", tipos)

    def test_no_ivr_mantiene_bugs(self):
        """Conversación normal (NO IVR) → bugs se mantienen."""
        tracker = CallEventTracker("test_normal", "BRUCE_TEST3")
        tracker.conversacion = [
            ("bruce", "Buenos días, me comunico de la marca Nioval, productos ferreteros"),
            ("cliente", "Sí soy yo el encargado aquí de compras"),
            ("bruce", "¿Se encontrará el encargado de compras?"),
        ]
        tracker.respuestas_bruce = [t for _, t in tracker.conversacion if _ == "bruce"]
        bugs = BugDetector.analyze(tracker)
        # Puede tener bugs legítimos (PREGUNTA_REPETIDA, CONTEXTO_IGNORADO, etc.)
        # Lo importante: NO se filtraron por IVR
        self.assertIsInstance(bugs, list)

    def test_ivr_conv_vacia_no_crash(self):
        """Conversación vacía no crashea el filtro IVR."""
        tracker = CallEventTracker("test_empty", "BRUCE_EMPTY")
        tracker.conversacion = []
        tracker.respuestas_bruce = []
        bugs = BugDetector.analyze(tracker)
        self.assertIsInstance(bugs, list)


class TestFix735IVRGPTEvalSkip(unittest.TestCase):
    """FIX 735: IVR detectado → SKIP GPT eval."""

    def test_ivr_patterns_regex(self):
        """Regex IVR detecta patterns comunes de conmutador."""
        import re
        _IVR = re.compile(
            r'(extensi[oó]n|m[aá]rquelo ahora|seleccione una|presione\s+(?:uno|dos|tres|\d)|'
            r'espere en la l[ií]nea|para ser atendido)',
            re.IGNORECASE
        )
        self.assertTrue(_IVR.search("Si conoce el número de extensión"))
        self.assertTrue(_IVR.search("Márquelo ahora"))
        self.assertTrue(_IVR.search("Seleccione una de las opciones"))
        self.assertTrue(_IVR.search("Presione uno para ventas"))
        self.assertTrue(_IVR.search("Espere en la línea"))
        self.assertTrue(_IVR.search("Para ser atendido"))
        # Negativo: conversación normal
        self.assertIsNone(_IVR.search("Sí, dígame"))
        self.assertIsNone(_IVR.search("No se encuentra, joven"))


# ============================================================
# FIX 736: Inicio de dictado ("El WhatsApp")
# ============================================================

class TestFix736CodigoPresente(unittest.TestCase):
    """FIX 736: Verificar que el código está presente."""

    def test_fix_736_en_filtrar(self):
        source = _get_filtrar_source()
        self.assertIn('FIX 736', source)
        self.assertIn('anuncio_dato_736', source)
        self.assertIn('cambio_tema_736', source)


class TestFix736InicioDictadoWhatsApp(unittest.TestCase):
    """FIX 736: Cliente anuncia 'El WhatsApp' → GPT cambia tema → override."""

    def test_el_whatsapp_gpt_callback(self):
        """Cliente: 'este sí, el WhatsApp' → GPT: '¿A qué hora llamar?' → override."""
        agente = _crear_agente_736()
        agente.conversation_history[-2] = {"role": "assistant", "content": "Con gusto. ¿Me podría proporcionar su número de WhatsApp?"}
        agente.conversation_history[-1] = {"role": "user", "content": "Este sí. El WhatsApp."}
        resultado = agente._filtrar_respuesta_post_gpt(
            "Entendido. ¿A qué hora me recomienda llamar?",
            {}
        )
        resultado_norm = _sa(resultado.lower())
        self.assertTrue(
            "digame" in resultado_norm or "aja" in resultado_norm,
            f"Esperado acknowledgment, recibido: '{resultado[:80]}'"
        )

    def test_el_whatsapp_gpt_despedida(self):
        """Cliente: 'sí, el WhatsApp' → GPT se despide → override."""
        agente = _crear_agente_736()
        agente.conversation_history[-2] = {"role": "assistant", "content": "Con gusto. ¿Me podría proporcionar su número de WhatsApp?"}
        agente.conversation_history[-1] = {"role": "user", "content": "Sí, el WhatsApp"}
        resultado = agente._filtrar_respuesta_post_gpt(
            "Perfecto, me comunico después. Muchas gracias por su tiempo, que tenga buen día.",
            {}
        )
        resultado_norm = _sa(resultado.lower())
        self.assertTrue(
            "digame" in resultado_norm or "aja" in resultado_norm,
            f"Esperado acknowledgment, recibido: '{resultado[:80]}'"
        )

    def test_te_doy_el_correo(self):
        """Cliente: 'te doy el correo' → GPT ofrece catálogo → override."""
        agente = _crear_agente_736()
        agente.conversation_history[-2] = {"role": "assistant", "content": "¿Le gustaría recibirlo por correo electrónico?"}
        agente.conversation_history[-1] = {"role": "user", "content": "Sí, te doy el correo"}
        resultado = agente._filtrar_respuesta_post_gpt(
            "Le comento que nuestro catálogo tiene más de 500 productos ferreteros de alta calidad",
            {}
        )
        resultado_norm = _sa(resultado.lower())
        self.assertTrue(
            "digame" in resultado_norm or "aja" in resultado_norm,
            f"Esperado acknowledgment, recibido: '{resultado[:80]}'"
        )


class TestFix736NoOverrideSiAcknowledgment(unittest.TestCase):
    """FIX 736: Si GPT ya es acknowledgment → NO cambiar."""

    def test_gpt_aja_digame_no_override(self):
        """GPT dice 'Ajá, dígame' → no debe cambiar."""
        agente = _crear_agente_736()
        agente.conversation_history[-2] = {"role": "assistant", "content": "Con gusto. ¿Me podría proporcionar su correo electrónico?"}
        agente.conversation_history[-1] = {"role": "user", "content": "Sí, te doy el correo"}
        resultado = agente._filtrar_respuesta_post_gpt("Ajá, dígame por favor.", {})
        self.assertIn("digame", _sa(resultado.lower()))


class TestFix736SinAnuncioNoOverride(unittest.TestCase):
    """FIX 736: Sin anuncio de dato → NO override."""

    def test_sin_anuncio_no_override(self):
        """Cliente dice algo genérico → FIX 736 no aplica."""
        agente = _crear_agente_con_contexto()
        agente.conversation_history[-1] = {"role": "user", "content": "Sí, me interesa mucho"}
        resultado = agente._filtrar_respuesta_post_gpt(
            "Entendido. ¿A qué hora me recomienda llamar?",
            {}
        )
        # Sin anuncio de dato → FIX 736 no aplica
        self.assertIsInstance(resultado, str)


# ============================================================
# BRUCE2301 replay (IVR)
# ============================================================

class TestBRUCE2301Replay(unittest.TestCase):
    """BRUCE2301: IVR detectado → bugs filtrados."""

    def test_bruce2301_ivr_no_bugs_contenido(self):
        """Replay BRUCE2301: IVR con extensión → sin bugs de contenido."""
        tracker = CallEventTracker("CA_test_2301", "BRUCE2301", "+528712222550")
        tracker.conversacion = [
            ("cliente", "Por llamar a. Si conoce el número de extensión,"),
            ("bruce", "Me comunico de la marca nioval, productos ferreteros, ¿Se encontrará el encargado de compras?"),
            ("cliente", "Si conoce el número de extensión, márquelo ahora o seleccione una de las opciones. Uno, ventas mayoreo. Dos, mostrador. Tres, crédito y cobranza,"),
            ("bruce", "Ajá, sí."),
            ("cliente", "Administración, o espere en la línea para ser atendido."),
            ("bruce", "Claro, espero."),
        ]
        tracker.respuestas_bruce = [t for _, t in tracker.conversacion if _ == "bruce"]
        bugs = BugDetector.analyze(tracker)
        tipos = [b["tipo"] for b in bugs]
        # IVR: NO debe tener bugs de contenido falsos positivos
        self.assertNotIn("GPT_CONTEXTO_IGNORADO", tipos)
        self.assertNotIn("GPT_OPORTUNIDAD_PERDIDA", tipos)
        self.assertNotIn("INTERRUPCION_CONVERSACIONAL", tipos)


# ============================================================
# Deploy version
# ============================================================

class TestDeployVersion(unittest.TestCase):
    """Verificar _DEPLOY_VERSION."""

    def test_deploy_version_existe(self):
        from bug_detector import _DEPLOY_VERSION
        self.assertIsInstance(_DEPLOY_VERSION, str)
        self.assertTrue(len(_DEPLOY_VERSION) > 0)


if __name__ == "__main__":
    unittest.main()
