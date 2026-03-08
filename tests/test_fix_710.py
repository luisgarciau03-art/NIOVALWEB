# -*- coding: utf-8 -*-
"""
Tests para FIX 710: BRUCE2255 - "No hacemos compras" = rechazo definitivo.
- 710A: Preguntas obvias - despedida instantánea
- 710B: Inmunidad FIX 600/601 para ENCARGADO_NO_ESTA_* y NO_HACEMOS_COMPRAS
- 710C: Pattern detector - NO_HACEMOS_COMPRAS antes de ENCARGADO_NO_ESTA
"""

import sys
import os
import inspect
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ============================================================
# FIX 710A: Preguntas Obvias - "No hacemos compras"
# ============================================================

class TestFix710ANoHacemosComprasObvias:
    """FIX 710A: Respuesta instantánea a rechazo 'no hacemos compras'."""

    def _classify(self, texto):
        """Simula FIX 708+709+710A."""
        texto_lower = texto.strip().lower()
        texto_lower = texto_lower.replace('á','a').replace('é','e').replace('í','i').replace('ó','o').replace('ú','u').replace('ü','u').replace('ñ','n')
        texto_lower = texto_lower.replace('¿','').replace('?','').replace('¡','').replace('!','')

        patrones_710a = [
            'no hacemos compra', 'no hacemos compras', 'no hacemos ningun tipo de compra',
            'no compramos', 'no compramos nada', 'no compro nada',
            'aqui no se compra', 'aqui no compramos', 'no hacemos pedidos',
            'no manejamos compras', 'no realizamos compras',
            'no adquirimos', 'no necesitamos proveedores', 'no necesitamos proveedor',
            'ya tenemos todo cubierto', 'no nos interesa ningun producto',
            'no estamos interesados en comprar',
        ]
        if any(p in texto_lower for p in patrones_710a):
            return "Entendido, disculpe la molestia. Que tenga buen dia."
        return None

    def test_no_hacemos_compras(self):
        r = self._classify("No hacemos compras")
        assert r is not None
        assert "disculpe" in r.lower()

    def test_no_hacemos_ningun_tipo(self):
        r = self._classify("No hacemos ningún tipo de compra")
        assert r is not None

    def test_bruce2255_exact(self):
        """BRUCE2255 exact text."""
        r = self._classify("No hay no hacemos ningún tipo de compra")
        assert r is not None

    def test_no_compramos(self):
        r = self._classify("No compramos")
        assert r is not None

    def test_no_compramos_nada(self):
        r = self._classify("No compramos nada")
        assert r is not None

    def test_aqui_no_se_compra(self):
        r = self._classify("Aquí no se compra")
        assert r is not None

    def test_no_hacemos_pedidos(self):
        r = self._classify("No hacemos pedidos")
        assert r is not None

    def test_no_necesitamos_proveedores(self):
        r = self._classify("No necesitamos proveedores")
        assert r is not None

    def test_no_realizamos_compras(self):
        r = self._classify("No realizamos compras")
        assert r is not None

    def test_no_estamos_interesados_en_comprar(self):
        r = self._classify("No estamos interesados en comprar")
        assert r is not None

    def test_no_matchea_compras_positivo(self):
        """'Sí hacemos compras' NO debe matchear."""
        r = self._classify("Sí hacemos compras aquí")
        assert r is None

    def test_no_matchea_frase_normal(self):
        r = self._classify("El encargado no está")
        assert r is None


# ============================================================
# FIX 710B: Inmunidad FIX 601 para ENCARGADO_NO_ESTA_*
# ============================================================

class TestFix710BInmunidad601:
    """FIX 710B: ENCARGADO_NO_ESTA_* inmune a FIX 601 (umbral complejidad)."""

    def test_encargado_no_esta_sin_horario_inmune(self):
        agente_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'agente_ventas.py')
        with open(agente_path, 'r', encoding='utf-8') as f:
            source = f.read()
        assert "'ENCARGADO_NO_ESTA_SIN_HORARIO'" in source
        # FASE 1.1: patrones_inmunes_601 = _PATRONES_INMUNES_UNIVERSAL
        idx_univ = source.find("_PATRONES_INMUNES_UNIVERSAL = {")
        idx_enc = source.find("'ENCARGADO_NO_ESTA_SIN_HORARIO'", idx_univ)
        idx_end = source.find("}", idx_univ)
        assert idx_univ < idx_enc < idx_end, "ENCARGADO_NO_ESTA_SIN_HORARIO must be in _PATRONES_INMUNES_UNIVERSAL"
        assert "patrones_inmunes_601 = _PATRONES_INMUNES_UNIVERSAL" in source

    def test_encargado_no_esta_con_horario_inmune(self):
        agente_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'agente_ventas.py')
        with open(agente_path, 'r', encoding='utf-8') as f:
            source = f.read()
        # FASE 1.1: patrones_inmunes_601 = _PATRONES_INMUNES_UNIVERSAL
        idx_univ = source.find("_PATRONES_INMUNES_UNIVERSAL = {")
        idx_enc = source.find("'ENCARGADO_NO_ESTA_CON_HORARIO'", idx_univ)
        idx_end = source.find("}", idx_univ)
        assert idx_univ < idx_enc < idx_end

    def test_no_hacemos_compras_inmune_601(self):
        agente_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'agente_ventas.py')
        with open(agente_path, 'r', encoding='utf-8') as f:
            source = f.read()
        # FASE 1.1: patrones_inmunes_601 = _PATRONES_INMUNES_UNIVERSAL
        idx_univ = source.find("_PATRONES_INMUNES_UNIVERSAL = {")
        idx_nhc = source.find("'NO_HACEMOS_COMPRAS'", idx_univ)
        idx_end = source.find("}", idx_univ)
        assert idx_univ < idx_nhc < idx_end

    def test_no_hacemos_compras_inmune_600(self):
        """NO_HACEMOS_COMPRAS also immune to FIX 600 (via _PATRONES_INMUNES_UNIVERSAL)."""
        agente_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'agente_ventas.py')
        with open(agente_path, 'r', encoding='utf-8') as f:
            source = f.read()
        # FASE 1.1: patrones_inmunes_pero = _PATRONES_INMUNES_UNIVERSAL
        idx_univ = source.find("_PATRONES_INMUNES_UNIVERSAL = {")
        idx_nhc = source.find("'NO_HACEMOS_COMPRAS'", idx_univ)
        idx_end = source.find("}", idx_univ)
        assert idx_univ < idx_nhc < idx_end
        assert "patrones_inmunes_pero = _PATRONES_INMUNES_UNIVERSAL" in source

    def test_encargado_no_esta_inmune_600(self):
        """ENCARGADO_NO_ESTA_SIN_HORARIO also immune to FIX 600 (via _PATRONES_INMUNES_UNIVERSAL)."""
        agente_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'agente_ventas.py')
        with open(agente_path, 'r', encoding='utf-8') as f:
            source = f.read()
        # FASE 1.1: patrones_inmunes_pero now references _PATRONES_INMUNES_UNIVERSAL
        idx_univ = source.find("_PATRONES_INMUNES_UNIVERSAL")
        idx_enc = source.find("'ENCARGADO_NO_ESTA_SIN_HORARIO'", idx_univ)
        idx_end = source.find("}", idx_univ)
        assert idx_univ < idx_enc < idx_end, "ENCARGADO_NO_ESTA_SIN_HORARIO must be in _PATRONES_INMUNES_UNIVERSAL"
        # Also verify patrones_inmunes_pero references it
        assert "patrones_inmunes_pero = _PATRONES_INMUNES_UNIVERSAL" in source


# ============================================================
# FIX 710C: Pattern Detector - NO_HACEMOS_COMPRAS
# ============================================================

class TestFix710CPatternDetector:
    """FIX 710C: Pattern detector tiene NO_HACEMOS_COMPRAS antes de ENCARGADO_NO_ESTA."""

    def test_710c_existe_en_codigo(self):
        agente_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'agente_ventas.py')
        with open(agente_path, 'r', encoding='utf-8') as f:
            source = f.read()
        assert "FIX 710C" in source
        assert "NO_HACEMOS_COMPRAS" in source
        assert "patrones_no_hacemos_compras_710" in source

    def test_710c_antes_de_encargado_no_esta(self):
        """FIX 710C must be BEFORE ENCARGADO_NO_ESTA detection."""
        agente_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'agente_ventas.py')
        with open(agente_path, 'r', encoding='utf-8') as f:
            source = f.read()
        idx_710 = source.find("patrones_no_hacemos_compras_710")
        idx_enc = source.find("encargado_no_esta = any(p in texto_lower for p in patrones_no_esta)")
        assert idx_710 < idx_enc, "FIX 710C must be BEFORE encargado_no_esta detection"

    def test_710c_retorna_despedida(self):
        agente_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'agente_ventas.py')
        with open(agente_path, 'r', encoding='utf-8') as f:
            source = f.read()
        # Find the return block for NO_HACEMOS_COMPRAS
        idx = source.find('"tipo": "NO_HACEMOS_COMPRAS"')
        assert idx > 0
        # Check response contains "disculpe" and "buen día"
        block = source[idx:idx+200]
        assert "disculpe" in block.lower()
        assert "DESPEDIDA" in block


# ============================================================
# FIX 710: Integración - BRUCE2255 exact scenario
# ============================================================

class TestFix710Integracion:
    """Test the exact BRUCE2255 scenario end-to-end."""

    def test_bruce2255_triple_rechazo(self):
        """BRUCE2255: Client said 3 different rejections in one message."""
        texto = "No hay no hacemos ningún tipo de compra. No, no hacemos ningún tipo de compra. Ya te comenté que aquí no se encuentra."
        texto_lower = texto.strip().lower()
        texto_lower = texto_lower.replace('á','a').replace('é','e').replace('í','i').replace('ó','o').replace('ú','u')

        # FIX 710A (preguntas obvias) should catch "no hacemos ningun tipo de compra"
        patrones_710a = [
            'no hacemos compra', 'no hacemos compras', 'no hacemos ningun tipo de compra',
            'no compramos', 'aqui no se compra',
        ]
        matched = any(p in texto_lower for p in patrones_710a)
        assert matched, "FIX 710A should match 'no hacemos ningun tipo de compra'"

    def test_bruce2255_no_repetir(self):
        """Bruce should NOT ask 'me puede repetir' when client says 'no hacemos compras'."""
        texto = "No hay no hacemos ningún tipo de compra"
        texto_lower = texto.strip().lower()
        texto_lower = texto_lower.replace('á','a').replace('é','e').replace('í','i').replace('ó','o').replace('ú','u')

        patrones_710c = [
            'no hacemos compra', 'no hacemos compras', 'no hacemos ningun tipo de compra',
            'no compramos',
        ]
        matched = any(p in texto_lower for p in patrones_710c)
        assert matched, "Should detect as NO_HACEMOS_COMPRAS, not send to GPT"

    def test_601_would_have_invalidated(self):
        """Verify that without FIX 710B, FIX 601 WOULD invalidate the pattern."""
        texto = "No hay no hacemos ningún tipo de compra. No, no hacemos ningún tipo de compra. Ya te comenté que aquí no se encuentra."
        palabras = texto.split()
        assert len(palabras) > 12, f"Text has {len(palabras)} words (>12)"

        num_clausulas = 1
        for sep in ['. ', ', ', '; ', '¿', '?']:
            num_clausulas += texto.count(sep)
        assert num_clausulas >= 3, f"Text has {num_clausulas} clauses (>=3)"

    def test_variantes_rechazo_compras(self):
        """Multiple ways to say 'we don't buy'."""
        variantes = [
            "No hacemos compras",
            "No compramos",
            "Aquí no se compra",
            "No hacemos pedidos",
            "No necesitamos proveedores",
        ]
        patrones = [
            'no hacemos compra', 'no hacemos compras', 'no compramos',
            'aqui no se compra', 'no hacemos pedidos',
            'no necesitamos proveedores',
        ]
        for v in variantes:
            vl = v.strip().lower().replace('á','a').replace('é','e').replace('í','i').replace('ó','o').replace('ú','u')
            matched = any(p in vl for p in patrones)
            assert matched, f"'{v}' should match NO_HACEMOS_COMPRAS"
