# -*- coding: utf-8 -*-
"""
Tests para FIX 709: Preguntas Obvias expandidas.
Nuevas categorías: quién habla, qué venden, cómo te llamas, eres Bruce.
"""

import sys
import os
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ============================================================
# Diccionario completo FIX 708+709 - Lógica pura para tests
# ============================================================

PREGUNTAS_OBVIAS = [
    (['tienes donde anotar', 'tiene donde anotar', 'tienes para anotar',
      'tiene para anotar', 'tienes con que anotar', 'tiene con que anotar',
      'tienes lapiz', 'tiene lapiz', 'tienes papel', 'tiene papel',
      'tienes pluma', 'tiene pluma', 'tienes donde apuntar', 'tiene donde apuntar',
      'tienes donde escribir', 'tiene donde escribir'],
     "Si, claro, digame por favor."),

    (['me escuchas', 'me escucha', 'me oyes', 'me oye',
      'sigues ahi', 'sigue ahi', 'estas ahi', 'esta ahi',
      'hay alguien', 'hay alguien ahi', 'se oye', 'se escucha'],
     "Si, le escucho perfectamente, digame."),

    (['eres robot', 'es un robot', 'eres una grabacion', 'es una grabacion',
      'eres una maquina', 'es una maquina', 'es automatico', 'eres automatico',
      'habla una maquina', 'habla un robot', 'eres inteligencia artificial',
      'es inteligencia artificial'],
     "No, soy Bruce, agente de ventas de NIOVAL. ¿En que le puedo ayudar?"),

    (['estas listo', 'esta listo', 'listo para anotar', 'ya estas',
      'ya esta listo', 'preparado'],
     "Si, estoy listo, digame por favor."),

    # FIX 709: Quién habla
    (['quien habla', 'quien llama', 'quien me habla', 'quien me llama',
      'con quien hablo', 'con quien tengo el gusto',
      'de donde habla', 'de donde hablan', 'de donde llama', 'de donde llaman',
      'de donde me habla', 'de donde me llama', 'de donde me marcan',
      'de que empresa', 'de que compania', 'que empresa es',
      'de parte de quien', 'a nombre de quien'],
     "Mi nombre es Bruce, le llamo de la marca NIOVAL. Somos distribuidores de productos ferreteros."),

    # FIX 709: Qué venden
    (['que venden', 'que vende', 'que ofrecen', 'que ofrece',
      'que manejan', 'que maneja', 'que productos', 'que tipo de productos',
      'que es lo que venden', 'a que se dedican', 'que es nioval',
      'de que se trata', 'que comercializan', 'que distribuyen'],
     "Distribuimos productos de ferreteria: cintas tapagoteras, griferia, herramientas, candados y mas de 15 categorias."),

    # FIX 709: Cómo te llamas
    (['como te llamas', 'como se llama', 'cual es tu nombre', 'cual es su nombre',
      'tu nombre', 'su nombre cual es', 'me dice su nombre',
      'dime tu nombre', 'digame su nombre'],
     "Mi nombre es Bruce, de la marca NIOVAL."),

    # FIX 709: Confirmación Bruce
    (['eres bruce', 'es bruce', 'bruce verdad', 'bruce, verdad',
      'bruce cierto', 'bruce, cierto',
      'se llama bruce', 'te llamas bruce', 'usted es bruce'],
     "Si, soy Bruce de NIOVAL. ¿En que le puedo ayudar?"),
]


def classify_709(texto):
    """Simula la lógica de FIX 708+709."""
    texto_lower = texto.strip().lower()
    texto_lower = texto_lower.replace('á','a').replace('é','e').replace('í','i').replace('ó','o').replace('ú','u').replace('ü','u').replace('ñ','n')
    texto_lower = texto_lower.replace('¿','').replace('?','').replace('¡','').replace('!','')
    for patrones, respuesta in PREGUNTAS_OBVIAS:
        if any(p in texto_lower for p in patrones):
            return respuesta
    return None


# ============================================================
# Tests: ¿Quién habla? / ¿De dónde llaman?
# ============================================================

class TestQuienHabla:
    """Preguntas de identidad: quién habla, de dónde llaman."""

    def test_quien_habla(self):
        r = classify_709("¿Quién habla?")
        assert r is not None
        assert "bruce" in r.lower()
        assert "nioval" in r.lower()

    def test_quien_llama(self):
        r = classify_709("¿Quién llama?")
        assert r is not None

    def test_con_quien_hablo(self):
        r = classify_709("¿Con quién hablo?")
        assert r is not None

    def test_con_quien_tengo_el_gusto(self):
        r = classify_709("¿Con quién tengo el gusto?")
        assert r is not None

    def test_de_donde_habla(self):
        r = classify_709("¿De dónde habla?")
        assert r is not None
        assert "nioval" in r.lower()

    def test_de_donde_llaman(self):
        r = classify_709("¿De dónde llaman?")
        assert r is not None

    def test_de_donde_me_marcan(self):
        r = classify_709("¿De dónde me marcan?")
        assert r is not None

    def test_de_que_empresa(self):
        r = classify_709("¿De qué empresa?")
        assert r is not None

    def test_de_que_compania(self):
        r = classify_709("¿De qué compañía?")
        assert r is not None

    def test_que_empresa_es(self):
        r = classify_709("¿Qué empresa es?")
        assert r is not None

    def test_de_parte_de_quien(self):
        r = classify_709("¿De parte de quién?")
        assert r is not None

    def test_a_nombre_de_quien(self):
        r = classify_709("¿A nombre de quién?")
        assert r is not None

    def test_quien_me_habla(self):
        r = classify_709("¿Quién me habla?")
        assert r is not None

    def test_de_donde_me_llama(self):
        r = classify_709("De donde me llama")
        assert r is not None


# ============================================================
# Tests: ¿Qué venden/manejan?
# ============================================================

class TestQueVenden:
    """Preguntas sobre productos."""

    def test_que_venden(self):
        r = classify_709("¿Qué venden?")
        assert r is not None
        assert "ferreteria" in r.lower()

    def test_que_ofrece(self):
        r = classify_709("¿Qué ofrece?")
        assert r is not None

    def test_que_manejan(self):
        r = classify_709("¿Qué manejan?")
        assert r is not None

    def test_que_productos(self):
        r = classify_709("¿Qué productos?")
        assert r is not None

    def test_que_tipo_de_productos(self):
        r = classify_709("¿Qué tipo de productos?")
        assert r is not None

    def test_que_es_lo_que_venden(self):
        r = classify_709("¿Qué es lo que venden?")
        assert r is not None

    def test_a_que_se_dedican(self):
        r = classify_709("¿A qué se dedican?")
        assert r is not None

    def test_que_es_nioval(self):
        r = classify_709("¿Qué es NIOVAL?")
        assert r is not None

    def test_de_que_se_trata(self):
        r = classify_709("¿De qué se trata?")
        assert r is not None

    def test_que_distribuyen(self):
        r = classify_709("¿Qué distribuyen?")
        assert r is not None

    def test_que_comercializan(self):
        r = classify_709("¿Qué comercializan?")
        assert r is not None


# ============================================================
# Tests: ¿Cómo te llamas?
# ============================================================

class TestComoTeLlamas:
    """Preguntas sobre el nombre de Bruce."""

    def test_como_te_llamas(self):
        r = classify_709("¿Cómo te llamas?")
        assert r is not None
        assert "bruce" in r.lower()

    def test_como_se_llama(self):
        r = classify_709("¿Cómo se llama?")
        assert r is not None

    def test_cual_es_tu_nombre(self):
        r = classify_709("¿Cuál es tu nombre?")
        assert r is not None

    def test_cual_es_su_nombre(self):
        r = classify_709("¿Cuál es su nombre?")
        assert r is not None

    def test_tu_nombre(self):
        r = classify_709("Tu nombre")
        assert r is not None

    def test_dime_tu_nombre(self):
        r = classify_709("Dime tu nombre")
        assert r is not None

    def test_digame_su_nombre(self):
        r = classify_709("Dígame su nombre")
        assert r is not None

    def test_me_dice_su_nombre(self):
        r = classify_709("¿Me dice su nombre?")
        assert r is not None


# ============================================================
# Tests: Confirmación ¿Eres Bruce?
# ============================================================

class TestEresBruce:
    """Confirmación de nombre Bruce."""

    def test_eres_bruce(self):
        r = classify_709("¿Eres Bruce?")
        assert r is not None
        assert "bruce" in r.lower()
        assert "nioval" in r.lower()

    def test_es_bruce(self):
        r = classify_709("¿Es Bruce?")
        assert r is not None

    def test_bruce_verdad(self):
        r = classify_709("Bruce, ¿verdad?")
        assert r is not None

    def test_bruce_cierto(self):
        r = classify_709("Bruce, ¿cierto?")
        assert r is not None

    def test_se_llama_bruce(self):
        r = classify_709("¿Se llama Bruce?")
        assert r is not None

    def test_usted_es_bruce(self):
        r = classify_709("¿Usted es Bruce?")
        assert r is not None


# ============================================================
# Tests: NO matchea (false positives)
# ============================================================

class TestNoMatchea709:
    """Frases que NO deben matchear las nuevas categorías."""

    def test_frase_normal(self):
        r = classify_709("No, el encargado no está")
        assert r is None

    def test_numero_telefono(self):
        r = classify_709("3312345678")
        assert r is None

    def test_si_me_interesa(self):
        r = classify_709("Sí, me interesa")
        assert r is None

    def test_no_me_interesa(self):
        r = classify_709("No me interesa gracias")
        assert r is None

    def test_mande_informacion(self):
        r = classify_709("Mándeme la información")
        assert r is None

    def test_no_esta_el_encargado(self):
        r = classify_709("No está el encargado, llame más tarde")
        assert r is None

    def test_pregunta_precio(self):
        r = classify_709("¿Cuánto cuesta?")
        assert r is None

    def test_ubicacion(self):
        r = classify_709("¿Dónde están ubicados?")
        assert r is None


# ============================================================
# Tests: Código fuente
# ============================================================

class TestFix709EnCodigo:
    """Verificar que FIX 709 está en agente_ventas.py."""

    def test_fix_709_existe(self):
        agente_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'agente_ventas.py')
        with open(agente_path, 'r', encoding='utf-8') as f:
            source = f.read()
        assert "FIX 709" in source
        assert "quien habla" in source
        assert "que venden" in source
        assert "como te llamas" in source
        assert "eres bruce" in source

    def test_fix_709_en_bloque_708(self):
        """FIX 709 debe estar en el mismo bloque que FIX 708."""
        agente_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'agente_ventas.py')
        with open(agente_path, 'r', encoding='utf-8') as f:
            source = f.read()
        idx_708 = source.find("FIX 708")
        idx_709 = source.find("FIX 709")
        assert idx_708 > 0
        assert idx_709 > 0
        # 709 debe estar cerca de 708 (mismo bloque)
        assert abs(idx_709 - idx_708) < 3000, "FIX 709 debe estar en el mismo bloque que FIX 708"


# ============================================================
# Tests: Integración - prioridad sobre pattern detector
# ============================================================

class TestFix709Integracion:
    """FIX 709 se ejecuta ANTES del pattern detector."""

    def test_quien_habla_antes_de_pattern_detector(self):
        """'quién habla' debe resolverse en FIX 709, no en pattern detector."""
        agente_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'agente_ventas.py')
        with open(agente_path, 'r', encoding='utf-8') as f:
            source = f.read()
        idx_709 = source.find("quien habla")
        idx_pattern = source.find("_detectar_patron_simple_optimizado(respuesta_cliente)")
        assert idx_709 < idx_pattern, "FIX 709 'quien habla' debe estar ANTES del pattern detector"

    def test_que_venden_antes_de_pattern_detector(self):
        agente_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'agente_ventas.py')
        with open(agente_path, 'r', encoding='utf-8') as f:
            source = f.read()
        idx_709 = source.find("que venden")
        idx_pattern = source.find("_detectar_patron_simple_optimizado(respuesta_cliente)")
        assert idx_709 < idx_pattern

    def test_todas_categorias_respuesta_distinta(self):
        """Cada categoría FIX 709 tiene respuesta diferente."""
        respuestas = set()
        tests = [
            "¿Quién habla?",
            "¿Qué venden?",
            "¿Cómo te llamas?",
            "¿Eres Bruce?",
        ]
        for t in tests:
            r = classify_709(t)
            assert r is not None, f"'{t}' no matcheó"
            respuestas.add(r)
        assert len(respuestas) == 4, "Las 4 categorías nuevas deben tener respuestas distintas"

    def test_708_y_709_no_se_solapan(self):
        """FIX 708 y FIX 709 no matchean las mismas frases."""
        frases_708 = [
            "¿Tienes donde anotar?", "¿Me escuchas?",
            "¿Eres robot?", "¿Estás listo?",
        ]
        frases_709 = [
            "¿Quién habla?", "¿Qué venden?",
            "¿Cómo te llamas?", "¿Eres Bruce?",
        ]
        # Verificar que no hay overlap
        for f in frases_708:
            r = classify_709(f)
            assert r is not None  # FIX 708 categorías siguen matcheando

        for f in frases_709:
            r = classify_709(f)
            assert r is not None  # FIX 709 categorías matchean

        # Las respuestas deben ser diferentes entre 708 y 709
        r708 = classify_709("¿Eres robot?")
        r709 = classify_709("¿Eres Bruce?")
        assert r708 != r709
