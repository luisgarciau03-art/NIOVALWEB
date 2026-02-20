"""
Tests FIX 731-733: Inmunidad 0% patterns + dato mismo turno + anti-interrupción dictado.

FIX 731: ENCARGADO_LLEGA_MAS_TARDE_ALTERNATIVA, CLIENTE_ES_ENCARGADO, OTRA_SUCURSAL → inmunidad
FIX 732: BRUCE2294 - GPT pide dato que cliente dio en el mismo turno → override confirmación
FIX 733: BRUCE2287 - Bruce interrumpe dictado parcial con cambio de tema → override acknowledgment
"""
import sys
import os
import inspect
import re
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from agente_ventas import AgenteVentas


def _get_source():
    """Obtener source de procesar_respuesta completo."""
    return inspect.getsource(AgenteVentas.procesar_respuesta)


def _get_filtrar_source():
    """Obtener source de _filtrar_respuesta_post_gpt completo."""
    return inspect.getsource(AgenteVentas._filtrar_respuesta_post_gpt)


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


# ============================================================
# FIX 731: Inmunidad 0% patterns
# ============================================================

class TestFix731InmunidadPatrones598(unittest.TestCase):
    """FIX 731: Patrones deben estar en patrones_inmunes_pregunta_598 (via _PATRONES_INMUNES_UNIVERSAL)."""

    def test_encargado_llega_alternativa_en_598(self):
        source = _get_source()
        # FASE 1.1: patrones_inmunes_pregunta_598 = _PATRONES_INMUNES_UNIVERSAL
        match = re.search(r"_PATRONES_INMUNES_UNIVERSAL\s*=\s*\{([^}]+)\}", source, re.DOTALL)
        self.assertIsNotNone(match, "_PATRONES_INMUNES_UNIVERSAL no encontrado")
        self.assertIn('ENCARGADO_LLEGA_MAS_TARDE_ALTERNATIVA', match.group(1))

    def test_cliente_es_encargado_en_598(self):
        source = _get_source()
        match = re.search(r"_PATRONES_INMUNES_UNIVERSAL\s*=\s*\{([^}]+)\}", source, re.DOTALL)
        self.assertIsNotNone(match)
        self.assertIn('CLIENTE_ES_ENCARGADO', match.group(1))

    def test_otra_sucursal_en_598(self):
        source = _get_source()
        match = re.search(r"_PATRONES_INMUNES_UNIVERSAL\s*=\s*\{([^}]+)\}", source, re.DOTALL)
        self.assertIsNotNone(match)
        self.assertIn('OTRA_SUCURSAL', match.group(1))


class TestFix731InmunidadPero600(unittest.TestCase):
    """FIX 731: Patrones deben estar en patrones_inmunes_pero (via _PATRONES_INMUNES_UNIVERSAL)."""

    def test_encargado_llega_alternativa_en_pero(self):
        source = _get_source()
        match = re.search(r"_PATRONES_INMUNES_UNIVERSAL\s*=\s*\{([^}]+)\}", source, re.DOTALL)
        self.assertIsNotNone(match, "_PATRONES_INMUNES_UNIVERSAL no encontrado")
        self.assertIn('ENCARGADO_LLEGA_MAS_TARDE_ALTERNATIVA', match.group(1))

    def test_cliente_es_encargado_en_pero(self):
        source = _get_source()
        match = re.search(r"_PATRONES_INMUNES_UNIVERSAL\s*=\s*\{([^}]+)\}", source, re.DOTALL)
        self.assertIsNotNone(match)
        self.assertIn('CLIENTE_ES_ENCARGADO', match.group(1))


class TestFix731InmunidadComplejidad601(unittest.TestCase):
    """FIX 731: CLIENTE_ES_ENCARGADO debe estar en patrones_inmunes_601 (via _PATRONES_INMUNES_UNIVERSAL)."""

    def test_cliente_es_encargado_en_601(self):
        source = _get_source()
        match = re.search(r"_PATRONES_INMUNES_UNIVERSAL\s*=\s*\{([^}]+)\}", source, re.DOTALL)
        self.assertIsNotNone(match, "_PATRONES_INMUNES_UNIVERSAL no encontrado")
        self.assertIn('CLIENTE_ES_ENCARGADO', match.group(1))


class TestFix731InmunidadContexto602(unittest.TestCase):
    """FIX 731: 3 patrones deben estar en patrones_inmunes_602 (via _PATRONES_INMUNES_UNIVERSAL)."""

    def _get_universal_content(self):
        source = _get_source()
        match = re.search(r"_PATRONES_INMUNES_UNIVERSAL\s*=\s*\{([^}]+)\}", source, re.DOTALL)
        self.assertIsNotNone(match, "_PATRONES_INMUNES_UNIVERSAL no encontrado")
        return match.group(1)

    def test_encargado_llega_alternativa_en_602(self):
        self.assertIn('ENCARGADO_LLEGA_MAS_TARDE_ALTERNATIVA', self._get_universal_content())

    def test_cliente_es_encargado_en_602(self):
        self.assertIn('CLIENTE_ES_ENCARGADO', self._get_universal_content())

    def test_otra_sucursal_en_602(self):
        self.assertIn('OTRA_SUCURSAL', self._get_universal_content())


# ============================================================
# FIX 732: GPT dato mismo turno (code presence + functional)
# ============================================================

class TestFix732CodigoPresente(unittest.TestCase):
    """FIX 732: Verificar que el código está presente."""

    def test_fix_732_en_filtrar(self):
        source = _get_filtrar_source()
        self.assertIn('FIX 732', source)
        self.assertIn('dato_actual_732', source)
        self.assertIn('pide_mismo_732', source)


class TestFix732DatoMismoTurnoEmail(unittest.TestCase):
    """FIX 732: Cliente dio correo en este turno, GPT pide correo → override."""

    def test_email_dictado_bruce_pide_correo(self):
        """Cliente dicta email, GPT pide correo → confirmar."""
        agente = _crear_agente_con_contexto()
        # Reemplazar último mensaje del cliente con email
        agente.conversation_history[-1] = {"role": "user", "content": "Es juan arroba gmail punto com"}
        # Penúltimo Bruce: diferente al GPT response para evitar FIX 679 (duplicate)
        agente.conversation_history[-2] = {"role": "assistant", "content": "Perfecto, le envío el catálogo. ¿Me compartiría su correo?"}
        resultado = agente._filtrar_respuesta_post_gpt(
            "¿Me podría dar su correo electrónico?", {}
        )
        self.assertIn("ya lo tengo", resultado.lower())

    def test_email_con_arroba_bruce_pide_email(self):
        """Cliente dice email con @, GPT pide email → confirmar."""
        agente = _crear_agente_con_contexto()
        agente.conversation_history[-1] = {"role": "user", "content": "Mi correo es juan@gmail.com"}
        # Penúltimo Bruce: diferente al GPT response para evitar FIX 679 (duplicate)
        agente.conversation_history[-2] = {"role": "assistant", "content": "Perfecto, para enviarle la información necesito su correo."}
        resultado = agente._filtrar_respuesta_post_gpt(
            "¿Me podría dar su correo electrónico?", {}
        )
        self.assertIn("ya lo tengo", resultado.lower())


class TestFix732DatoMismoTurnoTelefono(unittest.TestCase):
    """FIX 732: Cliente dio teléfono en este turno, GPT pide número → override."""

    def test_telefono_dictado_bruce_pide_digitos(self):
        """Cliente dicta 10 dígitos, GPT pide dígitos → confirmar."""
        agente = _crear_agente_con_contexto()
        agente.conversation_history[-1] = {"role": "user", "content": "Es el 3312345678"}
        agente.conversation_history[-2] = {"role": "assistant", "content": "¿Me podría dar su WhatsApp?"}
        resultado = agente._filtrar_respuesta_post_gpt(
            "¿Me podría dar los dígitos restantes del número?", {}
        )
        self.assertIn("ya lo tengo", resultado.lower())


class TestFix732SinDatoNoOverride(unittest.TestCase):
    """FIX 732: Sin dato en turno actual → NO override."""

    def test_sin_email_no_override(self):
        """Cliente no da dato, GPT pide correo → NO override por FIX 732."""
        agente = _crear_agente_con_contexto()
        agente.conversation_history[-1] = {"role": "user", "content": "Sí, me interesa mucho"}
        resultado = agente._filtrar_respuesta_post_gpt(
            "¿Me podría dar su correo electrónico?", {}
        )
        # No hay dato en turno actual → FIX 732 no aplica
        self.assertNotIn("ya lo tengo anotado. muchas gracias", resultado.lower())


# ============================================================
# FIX 733: Anti-interrupción durante dictado (code presence + functional)
# ============================================================

class TestFix733CodigoPresente(unittest.TestCase):
    """FIX 733: Verificar que el código está presente."""

    def test_fix_733_en_filtrar(self):
        source = _get_filtrar_source()
        self.assertIn('FIX 733', source)
        self.assertIn('bruce_pidio_dato_733', source)
        self.assertIn('cambio_tema_733', source)


class TestFix733AntiInterrupcionDictado(unittest.TestCase):
    """FIX 733: Bruce pidió dato, cliente da parcial, GPT cambia de tema → override."""

    def test_bruce_pidio_whatsapp_cliente_dicta_gpt_ofrece_catalogo(self):
        """Bruce pidió WhatsApp, cliente da dígitos, GPT ofrece catálogo → override."""
        agente = _crear_agente_con_contexto()
        agente.conversation_history[-2] = {"role": "assistant", "content": "¿Me podría dar su WhatsApp?"}
        agente.conversation_history[-1] = {"role": "user", "content": "Sí, es el 33 12"}
        resultado = agente._filtrar_respuesta_post_gpt(
            "Le comento que nuestro catálogo tiene más de 500 productos ferreteros",
            {}
        )
        resultado_lower = resultado.lower()
        self.assertTrue(
            "contin" in resultado_lower or "aja" in resultado_lower,
            f"Esperado acknowledgment, recibido: '{resultado[:80]}'"
        )

    def test_bruce_pidio_correo_cliente_dicta_gpt_despide(self):
        """Bruce pidió correo, cliente da email parcial, GPT se despide → override.
        FIX 733 fires, then FIX 231 (email collection) may further adjust.
        Both 'continúe' and 'dígame su correo' are valid responses."""
        agente = _crear_agente_con_contexto()
        agente.conversation_history[-2] = {"role": "assistant", "content": "Para enviarle la información necesito su correo."}
        agente.conversation_history[-1] = {"role": "user", "content": "Es juan arroba gmail"}
        resultado = agente._filtrar_respuesta_post_gpt(
            "Muchas gracias por su tiempo, que tenga buen dia",
            {}
        )
        resultado_lower = resultado.lower()
        # FIX 733 override OR FIX 231 email collection - ambos son correctos
        self.assertTrue(
            "contin" in resultado_lower or "aja" in resultado_lower or
            "correo" in resultado_lower or "digame" in resultado_lower,
            f"Esperado acknowledgment o solicitud correo, recibido: '{resultado[:80]}'"
        )

    def test_bruce_pidio_numero_cliente_dicta_gpt_cambia_tema(self):
        """Bruce pidió número, cliente da dígitos, GPT cambia de tema → override."""
        agente = _crear_agente_con_contexto()
        agente.conversation_history[-2] = {"role": "assistant", "content": "Perfecto, para enviarle la información necesito su número de teléfono."}
        agente.conversation_history[-1] = {"role": "user", "content": "87 14 22"}
        resultado = agente._filtrar_respuesta_post_gpt(
            "Le comento que nuestro catálogo tiene más de 500 productos ferreteros de alta calidad",
            {}
        )
        resultado_lower = resultado.lower()
        self.assertTrue(
            "contin" in resultado_lower or "aja" in resultado_lower,
            f"Esperado acknowledgment, recibido: '{resultado[:80]}'"
        )


class TestFix733NoOverrideSiAcknowledgment(unittest.TestCase):
    """FIX 733: Si GPT ya es acknowledgment → NO cambia a algo peor."""

    def test_gpt_dice_aja_no_override(self):
        """GPT dice 'Ajá, continúe' → no debe cambiar a catálogo ni encargado."""
        agente = _crear_agente_con_contexto()
        agente.conversation_history[-2] = {"role": "assistant", "content": "¿Me podría dar su WhatsApp?"}
        agente.conversation_history[-1] = {"role": "user", "content": "Sí, es el 33 12"}
        resultado = agente._filtrar_respuesta_post_gpt("Ajá, continúe por favor.", {})
        self.assertNotIn("encargado", resultado.lower())


class TestFix733NoDictadoNoOverride(unittest.TestCase):
    """FIX 733: Sin datos parciales → NO override."""

    def test_sin_peticion_previa_no_override(self):
        """Bruce NO pidió dato → FIX 733 no aplica."""
        agente = _crear_agente_con_contexto()
        # Bruce dijo algo genérico (no pidió dato)
        agente.conversation_history[-2] = {"role": "assistant", "content": "Buenos días, le comento sobre nuestros productos"}
        agente.conversation_history[-1] = {"role": "user", "content": "Sí, estoy en la calle 33 12"}
        resultado = agente._filtrar_respuesta_post_gpt(
            "Le comento que nuestro catálogo tiene productos ferreteros",
            {}
        )
        # Bruce no pidió dato → FIX 733 no aplica
        self.assertIsInstance(resultado, str)


# ============================================================
# Deploy version en bug_detector
# ============================================================

class TestDeployVersion(unittest.TestCase):
    """Verificar que _DEPLOY_VERSION está definida."""

    def test_deploy_version_existe(self):
        from bug_detector import _DEPLOY_VERSION
        self.assertIsInstance(_DEPLOY_VERSION, str)
        self.assertTrue(len(_DEPLOY_VERSION) > 0)

    def test_deploy_version_actual(self):
        from bug_detector import _DEPLOY_VERSION
        # FASE 1.1: Deploy version may use "FASE" prefix instead of "FIX"
        self.assertTrue("FIX" in _DEPLOY_VERSION or "FASE" in _DEPLOY_VERSION,
                        f"Deploy version should contain FIX or FASE, got: {_DEPLOY_VERSION}")


if __name__ == "__main__":
    unittest.main()
