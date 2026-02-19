"""
Tests FIX 719-720: GPT prompt expansion + regex refinement.

FIX 719: CONTEXTO_IGNORADO y RESPUESTA_INCOHERENTE agregados al prompt completo
FIX 720: Regexes expandidos (_BRUCE_CONFIRMA_DATO, _DICTADO_PATTERNS, _AREA_EQUIVOCADA, _BRUCE_NO_ENTENDIO_RECHAZO)
"""
import re
import sys
import os
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from bug_detector import (
    ContentAnalyzer, _GPT_EVAL_PROMPT, _GPT_EVAL_PROMPT_CORTA
)


class TestFix719PromptExpansion(unittest.TestCase):
    """FIX 719: Verificar que CONTEXTO_IGNORADO y RESPUESTA_INCOHERENTE están en prompt completo."""

    def test_contexto_ignorado_en_prompt_completo(self):
        """CONTEXTO_IGNORADO debe estar en _GPT_EVAL_PROMPT."""
        self.assertIn("CONTEXTO_IGNORADO", _GPT_EVAL_PROMPT)

    def test_respuesta_incoherente_en_prompt_completo(self):
        """RESPUESTA_INCOHERENTE debe estar en _GPT_EVAL_PROMPT."""
        self.assertIn("RESPUESTA_INCOHERENTE", _GPT_EVAL_PROMPT)

    def test_contexto_ignorado_en_prompt_corta(self):
        """CONTEXTO_IGNORADO debe seguir en _GPT_EVAL_PROMPT_CORTA."""
        self.assertIn("CONTEXTO_IGNORADO", _GPT_EVAL_PROMPT_CORTA)

    def test_respuesta_incoherente_en_prompt_corta(self):
        """RESPUESTA_INCOHERENTE debe seguir en _GPT_EVAL_PROMPT_CORTA."""
        self.assertIn("RESPUESTA_INCOHERENTE", _GPT_EVAL_PROMPT_CORTA)

    def test_prompt_completo_tiene_7_tipos(self):
        """_GPT_EVAL_PROMPT debe tener 7 tipos de error."""
        tipos = ['RESPUESTA_INCORRECTA', 'FUERA_DE_TEMA', 'TONO_INADECUADO',
                 'LOGICA_ROTA', 'OPORTUNIDAD_PERDIDA', 'CONTEXTO_IGNORADO',
                 'RESPUESTA_INCOHERENTE']
        for tipo in tipos:
            self.assertIn(tipo, _GPT_EVAL_PROMPT, f"Falta {tipo} en prompt completo")

    def test_prompt_corta_tiene_4_tipos(self):
        """_GPT_EVAL_PROMPT_CORTA debe tener 4 tipos de error."""
        tipos = ['CONTEXTO_IGNORADO', 'RESPUESTA_INCOHERENTE',
                 'LOGICA_ROTA', 'OPORTUNIDAD_PERDIDA']
        for tipo in tipos:
            self.assertIn(tipo, _GPT_EVAL_PROMPT_CORTA, f"Falta {tipo} en prompt corta")

    def test_contexto_ignorado_descripcion_encargado(self):
        """Prompt completo describe señales de encargado/decisor."""
        self.assertIn("encargado", _GPT_EVAL_PROMPT.lower())
        self.assertIn("decisor", _GPT_EVAL_PROMPT.lower())


class TestFix720BruceConfirmaDato(unittest.TestCase):
    """FIX 720: Expansión de _BRUCE_CONFIRMA_DATO."""

    def test_anotado(self):
        self.assertTrue(ContentAnalyzer._BRUCE_CONFIRMA_DATO.search("Anotado, le envío el catálogo"))

    def test_registrado(self):
        self.assertTrue(ContentAnalyzer._BRUCE_CONFIRMA_DATO.search("Registrado, muchas gracias"))

    def test_tome_nota(self):
        self.assertTrue(ContentAnalyzer._BRUCE_CONFIRMA_DATO.search("Tomé nota del número"))

    def test_ya_lo_tengo(self):
        self.assertTrue(ContentAnalyzer._BRUCE_CONFIRMA_DATO.search("Ya lo tengo, perfecto"))

    def test_correcto_lo_tengo(self):
        self.assertTrue(ContentAnalyzer._BRUCE_CONFIRMA_DATO.search("Correcto, ya lo tengo anotado"))

    def test_le_mando(self):
        self.assertTrue(ContentAnalyzer._BRUCE_CONFIRMA_DATO.search("Le mando el catálogo ahora"))

    def test_original_perfecto_lo_tengo(self):
        """Patrones originales siguen funcionando."""
        self.assertTrue(ContentAnalyzer._BRUCE_CONFIRMA_DATO.search("Perfecto, ya lo tengo"))


class TestFix720DictadoPatterns(unittest.TestCase):
    """FIX 720: Expansión de _DICTADO_PATTERNS con WhatsApp, nombre, dirección."""

    def test_mi_whatsapp_es(self):
        self.assertTrue(ContentAnalyzer._DICTADO_PATTERNS.search("Mi WhatsApp es 3312345678"))

    def test_mi_numero_es(self):
        self.assertTrue(ContentAnalyzer._DICTADO_PATTERNS.search("Mi número es 3312345678"))

    def test_mi_celular_es(self):
        self.assertTrue(ContentAnalyzer._DICTADO_PATTERNS.search("Mi celular es 33 1234 5678"))

    def test_mi_correo_es(self):
        self.assertTrue(ContentAnalyzer._DICTADO_PATTERNS.search("Mi correo es juan@gmail.com"))

    def test_me_llamo(self):
        self.assertTrue(ContentAnalyzer._DICTADO_PATTERNS.search("Me llamo Juan Pérez"))

    def test_la_direccion_es(self):
        self.assertTrue(ContentAnalyzer._DICTADO_PATTERNS.search("La dirección es Av. Juárez 123"))

    def test_original_arroba(self):
        """Patrones originales siguen funcionando."""
        self.assertTrue(ContentAnalyzer._DICTADO_PATTERNS.search("juan arroba gmail punto com"))


class TestFix720AreaEquivocadaPatterns(unittest.TestCase):
    """FIX 720: Expansión de _AREA_EQUIVOCADA_PATTERNS."""

    def test_no_es_conmigo(self):
        texto = "no es conmigo, yo no manejo eso"
        texto_norm = texto.lower().replace('á', 'a').replace('é', 'e').replace('í', 'i').replace('ó', 'o').replace('ú', 'u')
        self.assertTrue(any(p in texto_norm for p in ContentAnalyzer._AREA_EQUIVOCADA_PATTERNS))

    def test_no_soy_yo(self):
        texto = "no soy yo el que ve eso"
        texto_norm = texto.lower()
        self.assertTrue(any(p in texto_norm for p in ContentAnalyzer._AREA_EQUIVOCADA_PATTERNS))

    def test_no_hacemos_compras(self):
        texto = "aquí no hacemos compras"
        texto_norm = texto.lower().replace('í', 'i')
        self.assertTrue(any(p in texto_norm for p in ContentAnalyzer._AREA_EQUIVOCADA_PATTERNS))

    def test_no_hacemos_ningun_tipo(self):
        texto = "No hacemos ningún tipo de compra"
        texto_norm = texto.lower().replace('ú', 'u')
        self.assertTrue(any(p in texto_norm for p in ContentAnalyzer._AREA_EQUIVOCADA_PATTERNS))

    def test_original_area_equivocada(self):
        """Patrones originales siguen funcionando."""
        texto = "es area equivocada"
        texto_norm = texto.lower()
        self.assertTrue(any(p in texto_norm for p in ContentAnalyzer._AREA_EQUIVOCADA_PATTERNS))


class TestFix720BruceNoEntendioRechazo(unittest.TestCase):
    """FIX 720: Expansión de _BRUCE_NO_ENTENDIO_RECHAZO."""

    def test_le_ofrecemos(self):
        self.assertTrue(ContentAnalyzer._BRUCE_NO_ENTENDIO_RECHAZO.search("Le ofrecemos productos de ferretería"))

    def test_nuestro_catalogo(self):
        self.assertTrue(ContentAnalyzer._BRUCE_NO_ENTENDIO_RECHAZO.search("Nuestro catálogo tiene variedad"))

    def test_le_interesaria(self):
        self.assertTrue(ContentAnalyzer._BRUCE_NO_ENTENDIO_RECHAZO.search("¿Le interesaría ver nuestro catálogo?"))

    def test_que_le_parece(self):
        self.assertTrue(ContentAnalyzer._BRUCE_NO_ENTENDIO_RECHAZO.search("¿Qué le parece si le envío información?"))

    def test_original_whatsapp(self):
        """Patrones originales siguen funcionando."""
        self.assertTrue(ContentAnalyzer._BRUCE_NO_ENTENDIO_RECHAZO.search("¿Me puede dar su WhatsApp?"))


if __name__ == "__main__":
    unittest.main()
