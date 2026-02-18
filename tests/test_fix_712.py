# -*- coding: utf-8 -*-
"""
Tests para FIX 712: BRUCE2266 - Background conversation detection after "Claro, espero"
- 712A: Señales FUERTES vs DÉBILES para re-engagement
- 712B: Ignorar audio de fondo en ESPERANDO_TRANSFERENCIA
"""

import sys
import os
import time
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ============================================================
# Lógica pura FIX 712A para tests
# ============================================================

frases_volvio_fuertes_712 = [
    # Re-engagement explícito
    'aqui estoy', 'ahi estoy', 'ya estoy',
    'ya regrese', 'ya volvi',
    'ya mire', 'ya, mire', 'ya listo', 'ya, listo', 'listo',
    # Dirigiéndose a Bruce
    'oiga', 'oye', 'mire', 'fijese', 'le comento', 'sabe que',
    'me escucha', 'me escuchas', 'me oye', 'me oyes',
    # Preguntas sobre Bruce/empresa
    'quien habla', 'quien llama', 'quien me habla',
    'de donde habla', 'de donde llama', 'de parte de',
    'que marca', 'que vende', 'que venden',
    'estan hablando', 'habla de', 'hablan de',
    # Contenido específico conversación con Bruce
    'ferreteria', 'nioval', 'bruce',
    'encargado', 'encargada', 'compras', 'proveedor',
    'empresa', 'negocio',
    # Estado del encargado
    'no esta', 'no se encuentra', 'salio',
    'no tenemos', 'no manejamos', 'no nos interesa', 'no hacemos compras',
    'no hay encargado', 'no hay nadie',
    # Ofertas de datos
    'anote', 'apunte', 'tome nota', 'tienes donde anotar', 'tiene donde anotar',
    'le doy', 'le paso', 'te doy', 'te paso',
    # Acuerdo/rechazo
    'de acuerdo', 'no gracias',
]

frases_volvio_debiles_712 = [
    'bueno', 'hola', 'si', 'diga', 'digame',
    'vuelvo', 'esta bien', 'ok',
]


def classify_712(texto, tiempo_espera=10):
    """Simula lógica FIX 712A. Retorna True si cliente_volvio, False si audio de fondo."""
    frase_limpia = texto.strip().lower()
    # Normalizar (como FIX 631 + FIX 712A)
    _fl = frase_limpia.replace('á','a').replace('é','e').replace('í','i').replace('ó','o').replace('ú','u').replace('ü','u').replace('ñ','n')
    _fl = _fl.replace('¿','').replace('?','').replace('¡','').replace('!','').replace('.','').replace(',','')

    frases_mas_espera = ['un momento', 'momentito', 'espere', 'tantito', 'un segundo']
    es_mas_espera = any(f in _fl for f in frases_mas_espera)

    tiene_senal_fuerte = any(f in _fl for f in frases_volvio_fuertes_712)
    tiene_senal_debil = any(f in _fl for f in frases_volvio_debiles_712)
    texto_corto_712 = len(_fl) < 25
    timeout_espera_712 = tiempo_espera > 60

    cliente_volvio = (
        tiene_senal_fuerte or
        (tiene_senal_debil and texto_corto_712) or
        timeout_espera_712
    )
    return cliente_volvio


# ============================================================
# Tests: BRUCE2266 exact scenario (audio de fondo)
# ============================================================

class TestFix712ABRUCE2266:
    """BRUCE2266: Cliente hablaba con otra persona tras 'espérame'."""

    def test_bruce2266_ese_es_de_cuanto(self):
        """'Ese es. ¿De cuánto? ¿Por qué? Sí.' = audio de fondo."""
        assert classify_712("Ese es. ¿De cuánto? ¿Por qué? Sí.") == False

    def test_bruce2266_alumbra_watts(self):
        """'y alumbra ciento cincuenta watts...' = audio de fondo."""
        assert classify_712("y alumbra ciento cincuenta watts de este foco") == False

    def test_bruce2266_precio_producto(self):
        """'¿Cuánto cuesta? Deme dos de esos' = audio de fondo."""
        assert classify_712("¿Cuánto cuesta? Deme dos de esos por favor") == False

    def test_bruce2266_dame_esa_caja(self):
        """'Dame esa caja de ahí' = audio de fondo."""
        assert classify_712("dame esa caja de ahí, la grande") == False

    def test_bruce2266_cuanto_sale(self):
        """'¿Cuánto sale? ¿De 100 o de 200?' = audio de fondo."""
        assert classify_712("¿Cuánto sale? ¿De 100 o de 200?") == False


# ============================================================
# Tests: Señales FUERTES (siempre exit wait)
# ============================================================

class TestFix712AFuertes:
    """Señales FUERTES = cliente SEGURO hablando con Bruce."""

    def test_fuerte_aqui_estoy(self):
        assert classify_712("aquí estoy") == True

    def test_fuerte_ya_estoy(self):
        assert classify_712("ya estoy aquí") == True

    def test_fuerte_listo(self):
        assert classify_712("listo") == True

    def test_fuerte_ya_listo(self):
        assert classify_712("ya, listo") == True

    def test_fuerte_oiga(self):
        assert classify_712("oiga, ¿sigue ahí?") == True

    def test_fuerte_mire(self):
        assert classify_712("mire, no está el encargado") == True

    def test_fuerte_me_escucha(self):
        assert classify_712("¿me escucha?") == True

    def test_fuerte_quien_habla(self):
        assert classify_712("¿quién habla?") == True

    def test_fuerte_encargado(self):
        assert classify_712("el encargado no se encuentra") == True

    def test_fuerte_no_esta(self):
        assert classify_712("no está, salió a comer") == True

    def test_fuerte_ferreteria(self):
        assert classify_712("ah, ¿es de ferretería?") == True

    def test_fuerte_nioval(self):
        assert classify_712("ah, ¿nioval?") == True

    def test_fuerte_no_hacemos_compras(self):
        assert classify_712("no, aquí no hacemos compras") == True

    def test_fuerte_tienes_donde_anotar(self):
        assert classify_712("tienes donde anotar?") == True

    def test_fuerte_le_paso(self):
        assert classify_712("le paso el número") == True

    def test_fuerte_no_esta_largo(self):
        """Texto largo con señal fuerte = sigue siendo re-engagement."""
        assert classify_712("bueno, mire, no está el encargado, se fue a comer, no sé a qué hora regrese") == True

    def test_fuerte_empresa(self):
        assert classify_712("¿de qué empresa habla?") == True

    def test_fuerte_de_acuerdo(self):
        assert classify_712("de acuerdo, mándeme la información") == True


# ============================================================
# Tests: Señales DÉBILES + texto corto (exit wait)
# ============================================================

class TestFix712ADebilesCroto:
    """Señales DÉBILES con texto CORTO = respuesta dirigida a Bruce."""

    def test_debil_bueno_corto(self):
        """'Bueno' (5 chars) = respuesta corta a Bruce."""
        assert classify_712("bueno") == True

    def test_debil_hola_corto(self):
        """'¿Hola?' (5 chars) = re-engagement."""
        assert classify_712("¿hola?") == True

    def test_debil_si_corto(self):
        """'Sí' (2 chars) = respuesta corta."""
        assert classify_712("sí") == True

    def test_debil_diga_corto(self):
        """'Diga' (4 chars) = respuesta corta."""
        assert classify_712("diga") == True

    def test_debil_digame_corto(self):
        """'Dígame' (6 chars) = respuesta corta."""
        assert classify_712("digame") == True

    def test_debil_bueno_pregunta_corta(self):
        """'¿Bueno? ¿Sí?' (13 chars) = re-engagement corto."""
        assert classify_712("¿bueno? ¿sí?") == True


# ============================================================
# Tests: Señales DÉBILES + texto largo (NO exit wait)
# ============================================================

class TestFix712ADebilesLargo:
    """Señales DÉBILES con texto LARGO = probablemente audio de fondo."""

    def test_debil_si_largo(self):
        """'sí' dentro de texto largo = audio de fondo."""
        assert classify_712("sí, ese de ahí, el que tiene tapa azul") == False

    def test_debil_bueno_largo(self):
        """'bueno' en texto largo sin señales fuertes = audio de fondo."""
        # Note: this text has no strong signals
        assert classify_712("bueno, dame tres de esos y cuatro de aquellos") == False

    def test_debil_hola_largo(self):
        """'hola' en texto largo = audio de fondo."""
        assert classify_712("hola, sí, ¿de cuánto es el tubo? ¿el grande?") == False


# ============================================================
# Tests: Timeout (>60s = exit wait)
# ============================================================

class TestFix712ATimeout:
    """Después de 60s desde 'Claro, espero', asumir que volvió."""

    def test_timeout_61s(self):
        """>60s = exit wait even without signals."""
        assert classify_712("algo random sin señales", tiempo_espera=61) == True

    def test_no_timeout_59s(self):
        """<60s = no timeout."""
        assert classify_712("algo random que no matchea nada", tiempo_espera=59) == False

    def test_timeout_120s(self):
        """Way past timeout."""
        assert classify_712("qué tal", tiempo_espera=120) == True


# ============================================================
# Tests: Más espera (stay in wait, handled by FIX 470)
# ============================================================

class TestFix712MasEspera:
    """Frases de 'más espera' se manejan por FIX 470, no por FIX 712."""

    def test_un_momento_no_es_reengagement(self):
        """'Un momento' should NOT trigger re-engagement."""
        # It's mas_espera, handled by FIX 470 separately
        frase = "un momento"
        frase_limpia = frase.strip().lower()
        frases_mas_espera = ['un momento', 'momentito', 'espere', 'tantito', 'un segundo']
        es_mas_espera = any(f in frase_limpia for f in frases_mas_espera)
        assert es_mas_espera


# ============================================================
# Tests: Código en servidor_llamadas.py
# ============================================================

class TestFix712EnCodigo:
    """Verificar FIX 712 en servidor_llamadas.py."""

    def test_712a_existe(self):
        srv_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'servidor_llamadas.py')
        with open(srv_path, 'r', encoding='utf-8') as f:
            source = f.read()
        assert "FIX 712A" in source
        assert "frases_volvio_fuertes_712" in source
        assert "frases_volvio_debiles_712" in source
        assert "tiene_senal_fuerte" in source
        assert "texto_corto_712" in source

    def test_712b_existe(self):
        srv_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'servidor_llamadas.py')
        with open(srv_path, 'r', encoding='utf-8') as f:
            source = f.read()
        assert "FIX 712B" in source
        assert "AUDIO FONDO IGNORADO" in source

    def test_712a_antes_de_712b(self):
        """FIX 712A debe estar ANTES de FIX 712B."""
        srv_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'servidor_llamadas.py')
        with open(srv_path, 'r', encoding='utf-8') as f:
            source = f.read()
        idx_a = source.find("FIX 712A")
        idx_b = source.find("FIX 712B")
        assert idx_a < idx_b

    def test_712b_antes_de_es_pregunta_rapida(self):
        """FIX 712B debe estar ANTES de es_pregunta_rapida (procesamiento normal)."""
        srv_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'servidor_llamadas.py')
        with open(srv_path, 'r', encoding='utf-8') as f:
            source = f.read()
        idx_712b = source.find("FIX 712B")
        idx_preg = source.find("es_pregunta_rapida = (")
        assert idx_712b < idx_preg


# ============================================================
# Tests: Edge cases
# ============================================================

class TestFix712EdgeCases:
    """Edge cases para FIX 712."""

    def test_texto_vacio(self):
        """Texto vacío = no re-engagement."""
        assert classify_712("") == False

    def test_solo_numeros(self):
        """Solo números = probablemente audio de fondo."""
        assert classify_712("ciento cincuenta y dos pesos") == False

    def test_fuerte_con_debil_largo(self):
        """Texto largo con señal fuerte dentro = exit wait."""
        assert classify_712("bueno, sí, ya estoy aquí, disculpe la demora") == True

    def test_pregunta_tecnica(self):
        """Pregunta técnica = audio de fondo."""
        assert classify_712("¿de cuántos watts es esa lámpara?") == False

    def test_instrucciones_trabajador(self):
        """Instrucciones a trabajador = audio de fondo."""
        assert classify_712("ponlo ahí arriba, en la repisa de hasta arriba") == False

    def test_conversacion_precio(self):
        """Negociación de precio con cliente = audio de fondo."""
        assert classify_712("te lo dejo en doscientos si te llevas los dos") == False

    def test_respuesta_corta_si_con_punto(self):
        """'Sí.' (3 chars) = respuesta corta dirigida a Bruce."""
        assert classify_712("sí.") == True

    def test_ya_regrese_largo(self):
        """'Ya regresé, disculpe' = señal fuerte (siempre exit)."""
        assert classify_712("ya regresé, disculpe la tardanza, es que estaba atendiendo") == True
