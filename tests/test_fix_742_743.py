"""
Tests FIX 742-743: Anti-loop exemption dictado/oferta + oferta vs dato.

FIX 742: BRUCE2287+2296 - FIX 671 NO bloquear si cliente dicta datos o ofrece contacto
FIX 743: BRUCE2296 - FIX 732 "te puedo proporcionar correo" = OFERTA, no dato real
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


def _get_filtrar_source():
    """Obtener source de _filtrar_respuesta_post_gpt."""
    return inspect.getsource(AgenteVentas._filtrar_respuesta_post_gpt)


def _crear_agente_catalogo_ofrecido():
    """Agente con catálogo ya ofrecido 1 vez (FIX 671 normalmente bloquearía)."""
    agente = AgenteVentas()
    agente.conversation_history = [
        {"role": "assistant", "content": "Buenos días, me comunico de la marca NIOVAL, somos distribuidores de productos ferreteros."},
        {"role": "user", "content": "Sí, dígame"},
        {"role": "assistant", "content": "Le comento que manejamos más de 500 productos. ¿Le gustaría recibir nuestro catálogo?"},
        {"role": "user", "content": "Sí, me interesa"},
        {"role": "assistant", "content": "¿Me podría proporcionar su número para enviarle el catálogo?"},
        {"role": "user", "content": "Sí claro"},
    ]
    agente.encargado_confirmado = True
    agente.pitch_dado = True
    agente.catalogo_ofrecido = True
    agente.contacto_solicitado = True
    return agente


# ============================================================
# FIX 742: Código presente
# ============================================================

class TestFix742CodigoPresente(unittest.TestCase):
    """FIX 742: Verificar que el código está presente."""

    def test_fix_742_en_filtrar(self):
        source = _get_filtrar_source()
        self.assertIn('FIX 742', source)
        self.assertIn('cliente_dictando_742', source)
        self.assertIn('cliente_ofrece_742', source)


# ============================================================
# FIX 742: Cliente dictando números → NO despedida
# ============================================================

class TestFix742DictandoNumeros(unittest.TestCase):
    """FIX 742: Cliente dictando números → FIX 671 no debe bloquear."""

    def test_digitos_numericos(self):
        """Cliente dictó '8713 880 000' → FIX 671 no debe reemplazar con despedida."""
        agente = _crear_agente_catalogo_ofrecido()
        agente.conversation_history[-1] = {"role": "user", "content": "Es el 8713 880 000"}
        resultado = agente._filtrar_respuesta_post_gpt(
            "Perfecto, ya lo tengo. Le envío el catálogo al número indicado.",
            {}
        )
        resultado_norm = _sa(resultado.lower())
        # FIX 671 NO debe haber reemplazado con despedida
        self.assertNotIn("me comunico despues", resultado_norm,
                         "FIX 671 no debe bloquear cuando cliente dicta números")

    def test_numeros_en_palabras(self):
        """Cliente dictó 'ochenta y siete trece' → FIX 671 no debe bloquear."""
        agente = _crear_agente_catalogo_ofrecido()
        agente.conversation_history[-1] = {"role": "user", "content": "ochenta y siete trece noventa y seis"}
        resultado = agente._filtrar_respuesta_post_gpt(
            "Le envío el catálogo. ¿Algo más que necesite?",
            {}
        )
        resultado_norm = _sa(resultado.lower())
        self.assertNotIn("me comunico despues", resultado_norm,
                         "FIX 671 no debe bloquear cuando cliente dicta números en palabras")

    def test_sin_datos_si_bloquea(self):
        """Cliente NO dicta datos ni ofrece → FIX 671 SÍ debe bloquear."""
        agente = _crear_agente_catalogo_ofrecido()
        agente.conversation_history[-1] = {"role": "user", "content": "ajá, sí"}
        resultado = agente._filtrar_respuesta_post_gpt(
            "Le envío nuestro catálogo de productos ferreteros.",
            {}
        )
        resultado_norm = _sa(resultado.lower())
        self.assertIn("me comunico despues", resultado_norm,
                      "FIX 671 DEBE bloquear cuando cliente no dicta ni ofrece datos")


# ============================================================
# FIX 742: Cliente ofreciendo datos → NO despedida
# ============================================================

class TestFix742OfreciendoDatos(unittest.TestCase):
    """FIX 742: Cliente ofreciendo proporcionar datos → FIX 671 no debe bloquear."""

    def test_te_puedo_proporcionar_correo(self):
        """'Te puedo proporcionar correo' → FIX 671 no debe bloquear."""
        agente = _crear_agente_catalogo_ofrecido()
        agente.conversation_history[-1] = {"role": "user", "content": "te puedo proporcionar correo"}
        resultado = agente._filtrar_respuesta_post_gpt(
            "Perfecto, le envío el catálogo al correo que me indique.",
            {}
        )
        resultado_norm = _sa(resultado.lower())
        self.assertNotIn("me comunico despues", resultado_norm,
                         "FIX 671 no debe bloquear cuando cliente ofrece proporcionar datos")

    def test_le_puedo_dar_un_correo(self):
        """'Le puedo dar un correo' → FIX 671 no debe bloquear."""
        agente = _crear_agente_catalogo_ofrecido()
        agente.conversation_history[-1] = {"role": "user", "content": "le puedo dar un correo"}
        resultado = agente._filtrar_respuesta_post_gpt(
            "Claro, le envío el catálogo al correo.",
            {}
        )
        resultado_norm = _sa(resultado.lower())
        self.assertNotIn("me comunico despues", resultado_norm)

    def test_email_con_arroba(self):
        """Cliente dictó email con 'arroba' → FIX 671 no debe bloquear."""
        agente = _crear_agente_catalogo_ofrecido()
        agente.conversation_history[-1] = {"role": "user", "content": "es ventas arroba empresa punto com"}
        resultado = agente._filtrar_respuesta_post_gpt(
            "Perfecto, le envío el catálogo a ese correo.",
            {}
        )
        resultado_norm = _sa(resultado.lower())
        self.assertNotIn("me comunico despues", resultado_norm)


# ============================================================
# FIX 743: Código presente
# ============================================================

class TestFix743CodigoPresente(unittest.TestCase):
    """FIX 743: Verificar que el código está presente."""

    def test_fix_743_en_filtrar(self):
        source = _get_filtrar_source()
        self.assertIn('FIX 743', source)
        self.assertIn('_ofertas_743', source)
        self.assertIn('es_oferta_743', source)


# ============================================================
# FIX 743: Oferta no se confunde con dato
# ============================================================

class TestFix743OfertaVsDato(unittest.TestCase):
    """FIX 743: 'puedo proporcionar' = oferta, FIX 732 no debe overridear."""

    def test_puedo_proporcionar_correo_no_override(self):
        """'Te puedo proporcionar correo' → FIX 732 NO debe confirmar 'ya lo tengo'."""
        agente = AgenteVentas()
        agente.conversation_history = [
            {"role": "assistant", "content": "Buenos días, marca NIOVAL, productos ferreteros."},
            {"role": "user", "content": "Sí dígame"},
            {"role": "assistant", "content": "Manejamos herramientas y más de 500 productos."},
            {"role": "user", "content": "No se encuentra el encargado"},
            {"role": "assistant", "content": "¿Me podría proporcionar el correo del encargado?"},
            {"role": "user", "content": "Te puedo proporcionar correo"},
        ]
        agente.encargado_confirmado = True
        agente.pitch_dado = True
        # GPT dice "Sí, por favor, dígame" (correcto - pidiendo el correo)
        resultado = agente._filtrar_respuesta_post_gpt(
            "Sí, por favor, dígame el correo.",
            {}
        )
        resultado_norm = _sa(resultado.lower())
        # FIX 732 NO debe haber cambiado a "ya lo tengo anotado"
        self.assertNotIn("ya lo tengo", resultado_norm,
                         "FIX 732 no debe confirmar recepción cuando cliente solo OFRECIÓ dar datos")

    def test_dato_real_si_override(self):
        """'El correo es juan arroba gmail punto com' → FIX 732 SÍ debe confirmar."""
        agente = AgenteVentas()
        agente.conversation_history = [
            {"role": "assistant", "content": "Buenos días, marca NIOVAL, productos ferreteros."},
            {"role": "user", "content": "Sí dígame"},
            {"role": "assistant", "content": "Manejamos herramientas y más de 500 productos."},
            {"role": "user", "content": "Me interesa"},
            {"role": "assistant", "content": "¿Me podría proporcionar su correo?"},
            {"role": "user", "content": "juan arroba gmail punto com"},
        ]
        agente.encargado_confirmado = True
        agente.pitch_dado = True
        # GPT pide correo de nuevo (incorrecto)
        resultado = agente._filtrar_respuesta_post_gpt(
            "¿Me podría proporcionar su correo electrónico?",
            {}
        )
        resultado_norm = _sa(resultado.lower())
        # FIX 732 SÍ debe haber confirmado
        self.assertIn("anotado", resultado_norm,
                      f"FIX 732 debe confirmar recepción cuando cliente DIO el email real, recibido: '{resultado[:80]}'")

    def test_te_paso_un_correo_no_override(self):
        """'Te paso un correo' = oferta, no dato real."""
        agente = AgenteVentas()
        agente.conversation_history = [
            {"role": "assistant", "content": "Buenos días, NIOVAL, productos ferreteros."},
            {"role": "user", "content": "Dígame"},
            {"role": "assistant", "content": "Manejamos herramientas de alta calidad."},
            {"role": "user", "content": "Me interesa"},
            {"role": "assistant", "content": "¿Me podría dar su contacto?"},
            {"role": "user", "content": "Te paso un correo mejor"},
        ]
        agente.encargado_confirmado = True
        agente.pitch_dado = True
        resultado = agente._filtrar_respuesta_post_gpt(
            "Sí, claro, dígame por favor.",
            {}
        )
        resultado_norm = _sa(resultado.lower())
        self.assertNotIn("ya lo tengo", resultado_norm)


if __name__ == "__main__":
    unittest.main()
