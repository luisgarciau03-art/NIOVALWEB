# -*- coding: utf-8 -*-
"""
Tests para FIX 708: Preguntas Obvias - Respuestas instantáneas.
Bruce siempre tiene donde anotar, siempre escucha, no es robot.
"""

import sys
import os
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ============================================================
# Diccionario de preguntas obvias - Lógica pura
# ============================================================

# Reproducir la lógica de FIX 708 para tests independientes
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
]


def classify_708(texto):
    """Simula la lógica de FIX 708."""
    texto_lower = texto.strip().lower()
    texto_lower = texto_lower.replace('á','a').replace('é','e').replace('í','i').replace('ó','o').replace('ú','u').replace('ü','u').replace('ñ','n')
    texto_lower = texto_lower.replace('¿','').replace('?','').replace('¡','').replace('!','')
    for patrones, respuesta in PREGUNTAS_OBVIAS:
        if any(p in texto_lower for p in patrones):
            return respuesta
    return None


# ============================================================
# Tests: Cliente ofrece dictar dato
# ============================================================

class TestPreguntasAnotar:
    """Preguntas sobre si Bruce tiene donde anotar."""

    def test_tienes_donde_anotar(self):
        r = classify_708("¿Tienes donde anotar?")
        assert r is not None
        assert "digame" in r.lower()

    def test_tiene_donde_anotar(self):
        r = classify_708("¿Tiene donde anotar?")
        assert r is not None

    def test_tienes_para_anotar(self):
        r = classify_708("Tienes para anotar")
        assert r is not None

    def test_tienes_lapiz(self):
        r = classify_708("¿Tienes lápiz?")
        assert r is not None

    def test_tiene_papel(self):
        r = classify_708("¿Tiene papel?")
        assert r is not None

    def test_tienes_pluma(self):
        r = classify_708("¿Tienes pluma?")
        assert r is not None

    def test_tienes_con_que_anotar(self):
        r = classify_708("¿Tienes con qué anotar?")
        assert r is not None

    def test_tienes_donde_apuntar(self):
        r = classify_708("¿Tienes donde apuntar?")
        assert r is not None

    def test_tienes_donde_escribir(self):
        r = classify_708("Tiene donde escribir?")
        assert r is not None

    def test_frase_compuesta_anotar(self):
        """'No está, tienes donde anotar?' también matchea."""
        r = classify_708("No está el encargado, tienes donde anotar?")
        assert r is not None


# ============================================================
# Tests: Verificación de conexión
# ============================================================

class TestVerificacionConexion:
    """Preguntas sobre si Bruce escucha/está ahí."""

    def test_me_escuchas(self):
        r = classify_708("¿Me escuchas?")
        assert r is not None
        assert "escucho" in r.lower()

    def test_me_escucha(self):
        r = classify_708("¿Me escucha?")
        assert r is not None

    def test_me_oyes(self):
        r = classify_708("¿Me oyes?")
        assert r is not None

    def test_sigues_ahi(self):
        r = classify_708("¿Sigues ahí?")
        assert r is not None

    def test_estas_ahi(self):
        r = classify_708("¿Estás ahí?")
        assert r is not None

    def test_hay_alguien(self):
        r = classify_708("¿Hay alguien?")
        assert r is not None

    def test_se_oye(self):
        r = classify_708("¿Se oye?")
        assert r is not None


# ============================================================
# Tests: ¿Eres robot?
# ============================================================

class TestEresRobot:
    """Preguntas sobre si Bruce es robot/grabación."""

    def test_eres_robot(self):
        r = classify_708("¿Eres robot?")
        assert r is not None
        assert "bruce" in r.lower()

    def test_es_un_robot(self):
        r = classify_708("¿Es un robot?")
        assert r is not None

    def test_eres_grabacion(self):
        r = classify_708("¿Eres una grabación?")
        assert r is not None
        assert "bruce" in r.lower()

    def test_es_automatico(self):
        r = classify_708("¿Es automático?")
        assert r is not None

    def test_habla_una_maquina(self):
        r = classify_708("Habla una máquina")
        assert r is not None

    def test_eres_inteligencia_artificial(self):
        r = classify_708("¿Eres inteligencia artificial?")
        assert r is not None


# ============================================================
# Tests: ¿Estás listo?
# ============================================================

class TestEstasListo:
    """Preguntas sobre si Bruce está listo."""

    def test_estas_listo(self):
        r = classify_708("¿Estás listo?")
        assert r is not None
        assert "listo" in r.lower()

    def test_esta_listo(self):
        r = classify_708("¿Está listo?")
        assert r is not None

    def test_listo_para_anotar(self):
        r = classify_708("¿Listo para anotar?")
        assert r is not None

    def test_ya_estas(self):
        r = classify_708("¿Ya estás?")
        assert r is not None


# ============================================================
# Tests: NO matchea (false positives)
# ============================================================

class TestNoMatchea:
    """Frases que NO deben matchear preguntas obvias."""

    def test_frase_normal(self):
        r = classify_708("No, el encargado no está")
        assert r is None

    def test_pregunta_normal(self):
        r = classify_708("¿Qué marca maneja?")
        assert r is None

    def test_numero(self):
        r = classify_708("3312345678")
        assert r is None

    def test_despedida(self):
        r = classify_708("Hasta luego, gracias")
        assert r is None

    def test_si_me_interesa(self):
        r = classify_708("Sí me interesa, dígame")
        assert r is None

    def test_no_me_interesa(self):
        r = classify_708("No me interesa gracias")
        assert r is None


# ============================================================
# Tests: Código fuente
# ============================================================

class TestFix708EnCodigo:
    """Verificar que FIX 708 está en agente_ventas.py."""

    def test_fix_708_existe(self):
        agente_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'agente_ventas.py')
        with open(agente_path, 'r', encoding='utf-8') as f:
            source = f.read()
        assert "FIX 708" in source
        assert "preguntas_obvias_708" in source

    def test_fix_708_antes_de_patron_detector(self):
        """FIX 708 debe estar ANTES de _detectar_patron_simple_optimizado."""
        agente_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'agente_ventas.py')
        with open(agente_path, 'r', encoding='utf-8') as f:
            source = f.read()
        idx_708 = source.find("preguntas_obvias_708")
        idx_491 = source.find("_detectar_patron_simple_optimizado(respuesta_cliente)")
        assert idx_708 < idx_491, "FIX 708 debe ejecutarse ANTES del pattern detector"
