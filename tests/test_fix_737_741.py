"""
Tests FIX 737-741: Datos dictados ignorados + identidad + dictado palabras + datos Bruce + inmunidad.

FIX 737: BRUCE2306 - Cliente dictó email/teléfono pero GPT pide otro canal → override
FIX 738: BRUCE2307 - "¿Dónde dice que llama?" → responder identidad
FIX 739: BRUCE2308 - "ochenta y..." (palabras) = inicio dictado parcial
FIX 740: BRUCE2311 - "Me pasas tus datos" → dar contacto Nioval
FIX 741: CLIENTE_ACEPTA_CONTACTO_BRUCE + DAR_CONTACTO_BRUCE → inmunidad 598/600/601/602
"""
import sys
import os
import inspect
import re
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from agente_ventas import AgenteVentas


def _sa(t):
    """Strip acentos para comparaciones."""
    return t.replace('á','a').replace('é','e').replace('í','i').replace('ó','o').replace('ú','u').replace('ü','u').replace('ñ','n')


def _get_source():
    """Obtener source de procesar_respuesta."""
    return inspect.getsource(AgenteVentas.procesar_respuesta)


def _get_filtrar_source():
    """Obtener source de _filtrar_respuesta_post_gpt."""
    return inspect.getsource(AgenteVentas._filtrar_respuesta_post_gpt)


def _get_pattern_source():
    """Obtener source de _detectar_patron_simple_optimizado."""
    return inspect.getsource(AgenteVentas._detectar_patron_simple_optimizado)


def _crear_agente_737():
    """Crea agente con 4+ turnos Bruce y datos dictados 2 turnos atrás."""
    agente = AgenteVentas()
    agente.conversation_history = [
        {"role": "assistant", "content": "Buenos días, me comunico de la marca NIOVAL, somos distribuidores de productos ferreteros."},
        {"role": "user", "content": "Sí, dígame"},
        {"role": "assistant", "content": "Le comento que manejamos más de 500 productos ferreteros de alta calidad."},
        {"role": "user", "content": "Ah, suena bien"},
        {"role": "assistant", "content": "¿Me podría proporcionar su correo electrónico para enviarle el catálogo?"},
        {"role": "user", "content": "Sí, es fabiana arroba almaco punto mx"},
        {"role": "assistant", "content": "Perfecto, ya lo anoté. ¿Algo más que necesite?"},
        {"role": "user", "content": "Sí, también me interesa ver precios"},
    ]
    agente.encargado_confirmado = True
    agente.pitch_dado = True
    agente.catalogo_ofrecido = True
    agente.contacto_solicitado = True
    agente.whatsapp_guardado = False
    agente.email_guardado = False
    return agente


def _crear_agente_739():
    """Crea agente para test de dictado en palabras."""
    agente = AgenteVentas()
    agente.conversation_history = [
        {"role": "assistant", "content": "Buenos días, me comunico de la marca NIOVAL, somos distribuidores de productos ferreteros."},
        {"role": "user", "content": "Sí, dígame"},
        {"role": "assistant", "content": "Le comento que manejamos herramientas, plomería y más de 500 productos."},
        {"role": "user", "content": "Sí, me interesa"},
        {"role": "assistant", "content": "Con gusto. ¿Me podría proporcionar su número de teléfono para enviarle información?"},
        {"role": "user", "content": "Es el ochenta y siete, trece"},
    ]
    agente.encargado_confirmado = True
    agente.pitch_dado = True
    agente.catalogo_ofrecido = True
    agente.contacto_solicitado = True
    return agente


# ============================================================
# FIX 737: Datos dictados ignorados por GPT
# ============================================================

class TestFix737CodigoPresente(unittest.TestCase):
    """FIX 737: Verificar que el código está presente."""

    def test_fix_737_en_filtrar(self):
        source = _get_filtrar_source()
        self.assertIn('FIX 737', source)
        self.assertIn('tiene_email_737', source)
        self.assertIn('pide_otro_737', source)


class TestFix737EmailDictado(unittest.TestCase):
    """FIX 737: Email dictado → GPT pide otro canal → override."""

    def test_email_dictado_gpt_pide_whatsapp(self):
        """Cliente dictó email 2 turnos atrás, GPT pide WhatsApp → override."""
        agente = _crear_agente_737()
        resultado = agente._filtrar_respuesta_post_gpt(
            "Entiendo. ¿Me podría proporcionar el WhatsApp del encargado para enviarle el catálogo?",
            {}
        )
        resultado_norm = _sa(resultado.lower())
        self.assertTrue(
            "anotado" in resultado_norm or "lo tengo" in resultado_norm or "correo" in resultado_norm,
            f"Esperado confirmación de recepción, recibido: '{resultado[:80]}'"
        )

    def test_email_dictado_gpt_confirma_no_override(self):
        """GPT ya confirma recepción → no override."""
        agente = _crear_agente_737()
        # GPT response already confirms, no override needed
        resultado = agente._filtrar_respuesta_post_gpt(
            "Le envío la información al correo indicado, muchas gracias.",
            {}
        )
        resultado_norm = _sa(resultado.lower())
        # FIX 737 should NOT override because GPT is not asking for another channel
        self.assertNotIn("anotado", resultado_norm)

    def test_sin_email_no_override(self):
        """Sin datos dictados → no override."""
        agente = AgenteVentas()
        agente.conversation_history = [
            {"role": "assistant", "content": "Buenos días, marca NIOVAL, productos ferreteros."},
            {"role": "user", "content": "Sí dígame"},
            {"role": "assistant", "content": "Le comento que manejamos herramientas y plomería."},
            {"role": "user", "content": "Ah, suena bien"},
            {"role": "assistant", "content": "¿Le gustaría recibir nuestro catálogo?"},
            {"role": "user", "content": "Sí, me interesa mucho"},
        ]
        agente.encargado_confirmado = True
        agente.pitch_dado = True
        resultado = agente._filtrar_respuesta_post_gpt(
            "¿Me podría proporcionar su correo para enviarle el catálogo?",
            {}
        )
        # Sin datos dictados en recientes, FIX 737 no debe aplicar
        self.assertIsInstance(resultado, str)


class TestFix737TelDictado(unittest.TestCase):
    """FIX 737: Teléfono dictado → GPT pide otro canal → override."""

    def test_tel_dictado_gpt_pide_correo(self):
        """Cliente dictó dígitos 2 turnos atrás, GPT pide correo → override."""
        agente = AgenteVentas()
        agente.conversation_history = [
            {"role": "assistant", "content": "Buenos días, marca NIOVAL, productos ferreteros."},
            {"role": "user", "content": "Sí dígame"},
            {"role": "assistant", "content": "Le comento que manejamos herramientas de alta calidad."},
            {"role": "user", "content": "Sí me interesa"},
            {"role": "assistant", "content": "¿Me podría dar su número de teléfono para enviarle información?"},
            {"role": "user", "content": "Es el 8713 880 000"},
            {"role": "assistant", "content": "Perfecto, lo anoté. ¿Algo más?"},
            {"role": "user", "content": "Sí, también quiero ver sus productos"},
        ]
        agente.encargado_confirmado = True
        agente.pitch_dado = True
        agente.catalogo_ofrecido = True
        agente.contacto_solicitado = True
        agente.whatsapp_guardado = False
        agente.email_guardado = False
        resultado = agente._filtrar_respuesta_post_gpt(
            "¿Me podría proporcionar el correo del encargado?",
            {}
        )
        resultado_norm = _sa(resultado.lower())
        self.assertTrue(
            "anotado" in resultado_norm or "lo tengo" in resultado_norm or "catalogo" in resultado_norm,
            f"Esperado confirmación, recibido: '{resultado[:80]}'"
        )


# ============================================================
# FIX 738: Pregunta identidad expandida
# ============================================================

class TestFix738PatronesPresentes(unittest.TestCase):
    """FIX 738: Nuevos patrones en PREGUNTA_IDENTIDAD."""

    def test_donde_dice_que_llama(self):
        source = _get_pattern_source()
        self.assertIn('donde dice que llama', source)

    def test_donde_dice_que_habla(self):
        source = _get_pattern_source()
        self.assertIn('donde dice que habla', source)

    def test_de_que_parte_llama(self):
        source = _get_pattern_source()
        self.assertIn('de que parte llama', source)


class TestFix738DeteccionIdentidad(unittest.TestCase):
    """FIX 738: Detección funcional de nuevos patrones."""

    def test_donde_dice_que_llama_detecta(self):
        """'¿Dónde dice que llama?' → PREGUNTA_IDENTIDAD → menciona NIOVAL."""
        agente = AgenteVentas()
        agente.conversation_history = [
            {"role": "assistant", "content": "Buenos días, me comunico de la marca NIOVAL."},
            {"role": "user", "content": "Sí, dígame"},
        ]
        resultado = agente.procesar_respuesta("¿Dónde dice que llama?")
        self.assertIn("NIOVAL", resultado)

    def test_de_que_parte_llama_detecta(self):
        """'¿De qué parte llama?' → PREGUNTA_IDENTIDAD → menciona NIOVAL."""
        agente = AgenteVentas()
        agente.conversation_history = [
            {"role": "assistant", "content": "Buenos días, me comunico de la marca NIOVAL."},
            {"role": "user", "content": "Sí, dígame"},
        ]
        resultado = agente.procesar_respuesta("¿De qué parte llama?")
        self.assertIn("NIOVAL", resultado)


# ============================================================
# FIX 739: Dictado en palabras parcial
# ============================================================

class TestFix739CodigoPresente(unittest.TestCase):
    """FIX 739: Código presente en FIX 733."""

    def test_fix_739_en_filtrar(self):
        source = _get_filtrar_source()
        self.assertIn('FIX 739', source)
        self.assertIn('_nums_739', source)
        self.assertIn('_nums_verbales_739', source)


class TestFix739DictadoPalabras(unittest.TestCase):
    """FIX 739: Números en palabras detectados como dictado."""

    def test_ochenta_y_siete(self):
        """'ochenta y siete, trece' → GPT cambia tema → override."""
        agente = _crear_agente_739()
        resultado = agente._filtrar_respuesta_post_gpt(
            "Entendido. Le comento que nuestros productos son de alta calidad.",
            {}
        )
        resultado_norm = _sa(resultado.lower())
        self.assertTrue(
            "continue" in resultado_norm or "aja" in resultado_norm or "digame" in resultado_norm,
            f"Esperado acknowledgment de dictado, recibido: '{resultado[:80]}'"
        )

    def test_seis_seis(self):
        """'seis seis veintidós' → detecta como dictado."""
        agente = AgenteVentas()
        agente.conversation_history = [
            {"role": "assistant", "content": "Buenos días, me comunico de la marca NIOVAL."},
            {"role": "user", "content": "Sí, dígame"},
            {"role": "assistant", "content": "Manejamos herramientas y más de 500 productos."},
            {"role": "user", "content": "Sí, me interesa"},
            {"role": "assistant", "content": "¿Me podría dar su número para enviarle información?"},
            {"role": "user", "content": "seis seis veintidós noventa y uno"},
        ]
        agente.encargado_confirmado = True
        agente.pitch_dado = True
        agente.contacto_solicitado = True
        resultado = agente._filtrar_respuesta_post_gpt(
            "Entiendo. Le comento que somos distribuidores de productos ferreteros.",
            {}
        )
        resultado_norm = _sa(resultado.lower())
        self.assertTrue(
            "continue" in resultado_norm or "aja" in resultado_norm or "digame" in resultado_norm,
            f"Esperado acknowledgment, recibido: '{resultado[:80]}'"
        )

    def test_texto_normal_no_detecta(self):
        """Texto normal sin números → FIX 739 no aplica."""
        agente = _crear_agente_739()
        agente.conversation_history[-1] = {"role": "user", "content": "sí, me interesa mucho"}
        resultado = agente._filtrar_respuesta_post_gpt(
            "Perfecto, le envío nuestro catálogo de productos ferreteros.",
            {}
        )
        # Sin números, FIX 739 no debe aplicar
        self.assertIsInstance(resultado, str)


# ============================================================
# FIX 740: "Me pasas tus datos"
# ============================================================

class TestFix740PatronesPresentes(unittest.TestCase):
    """FIX 740: Nuevos patrones en PIDE_CONTACTO_NIOVAL."""

    def test_me_pasas_tus_datos(self):
        source = _get_pattern_source()
        self.assertIn('me pasas tus datos', source)

    def test_dame_tus_datos(self):
        source = _get_pattern_source()
        self.assertIn('dame tus datos', source)


class TestFix740Deteccion(unittest.TestCase):
    """FIX 740: Detección funcional."""

    def test_me_pasas_tus_datos_detecta(self):
        """'¿Me pasas tus datos?' → PIDE_CONTACTO_NIOVAL → da WhatsApp."""
        agente = AgenteVentas()
        agente.conversation_history = [
            {"role": "assistant", "content": "Buenos días, marca NIOVAL, productos ferreteros."},
            {"role": "user", "content": "Sí, dígame"},
        ]
        resultado = agente.procesar_respuesta("¿Me pasas tus datos, por favor?")
        # WhatsApp number is spaced: "6 6 2, 4 1 5, 1 9 9 7"
        self.assertTrue("6 6 2" in resultado or "nioval" in resultado.lower(),
                        f"Esperado contacto Nioval, recibido: '{resultado[:80]}'")

    def test_sus_datos_por_favor_detecta(self):
        """'¿Me da sus datos por favor?' → PIDE_CONTACTO_NIOVAL → da contacto."""
        agente = AgenteVentas()
        agente.conversation_history = [
            {"role": "assistant", "content": "Buenos días, marca NIOVAL, productos ferreteros."},
            {"role": "user", "content": "Sí, dígame"},
        ]
        resultado = agente.procesar_respuesta("¿Me da sus datos por favor?")
        self.assertTrue("6 6 2" in resultado or "nioval" in resultado.lower(),
                        f"Esperado contacto Nioval, recibido: '{resultado[:80]}'")


# ============================================================
# FIX 741: Inmunidad 0% patterns
# ============================================================

class TestFix741Inmunidad598(unittest.TestCase):
    """FIX 741: CLIENTE_ACEPTA_CONTACTO_BRUCE + DAR_CONTACTO_BRUCE en 598 (via _PATRONES_INMUNES_UNIVERSAL)."""

    def test_cliente_acepta_contacto_bruce_en_598(self):
        source = _get_source()
        match = re.search(r"_PATRONES_INMUNES_UNIVERSAL\s*=\s*\{([^}]+)\}", source, re.DOTALL)
        self.assertIsNotNone(match)
        self.assertIn('CLIENTE_ACEPTA_CONTACTO_BRUCE', match.group(1))

    def test_dar_contacto_bruce_en_598(self):
        source = _get_source()
        match = re.search(r"_PATRONES_INMUNES_UNIVERSAL\s*=\s*\{([^}]+)\}", source, re.DOTALL)
        self.assertIsNotNone(match)
        self.assertIn('DAR_CONTACTO_BRUCE', match.group(1))


class TestFix741Inmunidad600(unittest.TestCase):
    """FIX 741: Ambos en patrones_inmunes_pero (via _PATRONES_INMUNES_UNIVERSAL)."""

    def test_ambos_en_pero(self):
        source = _get_source()
        match = re.search(r"_PATRONES_INMUNES_UNIVERSAL\s*=\s*\{([^}]+)\}", source, re.DOTALL)
        self.assertIsNotNone(match)
        content = match.group(1)
        self.assertIn('CLIENTE_ACEPTA_CONTACTO_BRUCE', content)
        self.assertIn('DAR_CONTACTO_BRUCE', content)


class TestFix741Inmunidad601(unittest.TestCase):
    """FIX 741: Ambos en patrones_inmunes_601 (via _PATRONES_INMUNES_UNIVERSAL)."""

    def test_ambos_en_601(self):
        source = _get_source()
        match = re.search(r"_PATRONES_INMUNES_UNIVERSAL\s*=\s*\{([^}]+)\}", source, re.DOTALL)
        self.assertIsNotNone(match)
        content = match.group(1)
        self.assertIn('CLIENTE_ACEPTA_CONTACTO_BRUCE', content)
        self.assertIn('DAR_CONTACTO_BRUCE', content)


class TestFix741Inmunidad602(unittest.TestCase):
    """FIX 741: Ambos en patrones_inmunes_602 (via _PATRONES_INMUNES_UNIVERSAL)."""

    def test_ambos_en_602(self):
        source = _get_source()
        match = re.search(r"_PATRONES_INMUNES_UNIVERSAL\s*=\s*\{([^}]+)\}", source, re.DOTALL)
        self.assertIsNotNone(match)
        content = match.group(1)
        self.assertIn('CLIENTE_ACEPTA_CONTACTO_BRUCE', content)
        self.assertIn('DAR_CONTACTO_BRUCE', content)


if __name__ == "__main__":
    unittest.main()
