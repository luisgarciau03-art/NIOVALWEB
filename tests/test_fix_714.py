# -*- coding: utf-8 -*-
"""
Tests para FIX 714: BRUCE2258 - Preservar números dictados en palabras en FIX 481
- 714A: Detectar números en PALABRAS (ochenta, siete, uno) además de dígitos numéricos
- 714B: Threshold reducido de 3 a 2 dígitos para preservar inicio de dictado
"""

import sys
import os
import re
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ============================================================
# Lógica pura FIX 714 para tests (replica la del servidor)
# ============================================================

numeros_palabras_714 = [
    'cero', 'uno', 'dos', 'tres', 'cuatro', 'cinco', 'seis', 'siete', 'ocho', 'nueve',
    'diez', 'once', 'doce', 'trece', 'catorce', 'quince',
    'dieciseis', 'diecisiete', 'dieciocho', 'diecinueve',
    'veinte', 'veintiuno', 'veintidos', 'veintitres', 'veinticuatro', 'veinticinco',
    'treinta', 'cuarenta', 'cincuenta', 'sesenta', 'setenta', 'ochenta', 'noventa',
]

horas_excluir = ['a las', 'las dos', 'las tres', 'las diez', 'las once', 'las doce']


def should_preserve_714(trans):
    """Simula lógica FIX 714: retorna True si transcripción debe preservarse como número."""
    trans_lower = trans.lower() if isinstance(trans, str) else str(trans).lower()

    # Dígitos numéricos
    digitos = re.findall(r'\d', trans_lower)

    # Números en palabras (FIX 714A) - contar por PALABRA del texto, no por item de lista
    _tl = trans_lower.replace('á','a').replace('é','e').replace('í','i').replace('ó','o').replace('ú','u')
    _tl = _tl.replace(',', ' ').replace('.', ' ')
    palabras_texto = _tl.split()
    nums_en_palabras = sum(1 for p in palabras_texto if p in numeros_palabras_714)

    # FIX 714B: threshold 2 (no 3)
    contiene_telefono = (len(digitos) >= 2 or nums_en_palabras >= 2) and not any(h in trans_lower for h in horas_excluir)
    return contiene_telefono


# ============================================================
# Tests: BRUCE2258 exact scenario
# ============================================================

class TestFix714BRUCE2258:
    """BRUCE2258: 'Sí, ochenta y siete, uno.' fue descartado por FIX 455."""

    def test_bruce2258_ochenta_siete_uno(self):
        """'Sí, ochenta y siete, uno.' debe preservarse (2+ números en palabras)."""
        assert should_preserve_714("Sí, ochenta y siete, uno.") == True

    def test_bruce2258_87_uno(self):
        """'87 uno.' debe preservarse (2 dígitos >= threshold 2)."""
        assert should_preserve_714("87 uno.") == True

    def test_bruce2258_si_ochenta(self):
        """'Sí, ochenta y siete, uno.' duplicada también preservada."""
        assert should_preserve_714("Sí, ochenta y siete, uno.") == True


# ============================================================
# Tests: Números en palabras (FIX 714A)
# ============================================================

class TestFix714ANumerosPalabras:
    """FIX 714A: Detectar números dictados en palabras."""

    def test_seis_seis(self):
        """'seis seis' = 2 números en palabras → preservar."""
        assert should_preserve_714("seis seis") == True

    def test_ochenta_y_siete(self):
        """'ochenta y siete' = 2 números → preservar."""
        assert should_preserve_714("ochenta y siete") == True

    def test_treinta_y_tres(self):
        """'treinta y tres' = 2 números → preservar."""
        assert should_preserve_714("treinta y tres") == True

    def test_cero_uno_dos(self):
        """'cero uno dos' = 3 números → preservar."""
        assert should_preserve_714("cero uno dos") == True

    def test_noventa_y_uno(self):
        """'noventa y uno' = 2 números → preservar."""
        assert should_preserve_714("noventa y uno") == True

    def test_solo_un_numero(self):
        """'uno' = 1 número → NO preservar (< 2)."""
        assert should_preserve_714("sí, uno") == False

    def test_sin_numeros(self):
        """'Hola, sí dígame' = 0 números → NO preservar."""
        assert should_preserve_714("Hola, sí dígame") == False

    def test_numeros_con_acento(self):
        """'veintidós' con acento → normaliza y detecta."""
        # 'veintidos' no está en la lista, pero 'veinte' y 'dos' sí
        # Realmente 'veintidós' → 'veintidos' después de normalizar
        # 'veintidos' IS in the list
        assert should_preserve_714("veintidós cuatro") == True

    def test_quince_y_cuarenta(self):
        """'quince cuarenta' = 2 números → preservar."""
        assert should_preserve_714("quince cuarenta") == True


# ============================================================
# Tests: Dígitos parciales (FIX 714B)
# ============================================================

class TestFix714BDigitosParciales:
    """FIX 714B: Threshold reducido de 3 a 2 dígitos."""

    def test_87_es_suficiente(self):
        """'87' = 2 dígitos → preservar (antes necesitaba 3)."""
        assert should_preserve_714("87") == True

    def test_87_uno(self):
        """'87 uno.' = 2 dígitos numéricos → preservar."""
        assert should_preserve_714("87 uno.") == True

    def test_33_digitos(self):
        """'33' = 2 dígitos → preservar."""
        assert should_preserve_714("33") == True

    def test_1_digito_no_preserva(self):
        """'8' = 1 dígito → NO preservar (< 2)."""
        assert should_preserve_714("sí, 8") == False

    def test_871_preserva(self):
        """'871' = 3 dígitos → preservar."""
        assert should_preserve_714("871") == True

    def test_6621_preserva(self):
        """'6621' = 4 dígitos → preservar."""
        assert should_preserve_714("6621") == True


# ============================================================
# Tests: Exclusión de horas
# ============================================================

class TestFix714Horas:
    """Horas como 'a las 2' no deben confundirse con teléfonos."""

    def test_a_las_dos_no_preserva(self):
        """'a las 2:30' → hora, no teléfono."""
        # 'a las' está en exclusión, pero '2' y '30' = 2 dígitos
        # Sin embargo 'a las' excluye
        assert should_preserve_714("a las 2:30") == False

    def test_las_tres_no_preserva(self):
        """'las tres de la tarde' → hora."""
        assert should_preserve_714("las tres de la tarde") == False

    def test_numero_sin_hora(self):
        """'el 33 y el 12' → números, no horas."""
        assert should_preserve_714("el 33 y el 12") == True


# ============================================================
# Tests: Verificación en código
# ============================================================

class TestFix714EnCodigo:
    """Verificar FIX 714 existe en servidor_llamadas.py."""

    def test_714a_existe(self):
        srv_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'servidor_llamadas.py')
        with open(srv_path, 'r', encoding='utf-8') as f:
            source = f.read()
        assert "FIX 714A" in source
        assert "numeros_palabras_714" in source
        assert "nums_en_palabras_714" in source

    def test_714b_existe(self):
        srv_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'servidor_llamadas.py')
        with open(srv_path, 'r', encoding='utf-8') as f:
            source = f.read()
        assert "FIX 714B" in source
        # Threshold reducido
        assert "len(digitos) >= 2" in source

    def test_714a_en_623a(self):
        """FIX 714A debe estar también en FIX 623A (almacenar dígitos)."""
        srv_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'servidor_llamadas.py')
        with open(srv_path, 'r', encoding='utf-8') as f:
            source = f.read()
        # FIX 623A debe convertir números en palabras a dígitos
        assert "_numeros_conv_714" in source


# ============================================================
# Tests: Edge cases
# ============================================================

class TestFix714EdgeCases:
    """Edge cases para FIX 714."""

    def test_mezcla_digitos_y_palabras(self):
        """'87 uno' = 2 dígitos numéricos + 1 palabra → preservar."""
        assert should_preserve_714("87 uno") == True

    def test_solo_si(self):
        """'Sí' no tiene números → NO preservar."""
        assert should_preserve_714("Sí") == False

    def test_texto_largo_con_numero(self):
        """'dame un momento, el ochenta y siete' → 2 números → preservar."""
        assert should_preserve_714("dame un momento, el ochenta y siete") == True

    def test_cuatro_cero_dos(self):
        """Dictado típico: 'cuatro cero dos' = 3 números → preservar."""
        assert should_preserve_714("cuatro cero dos") == True

    def test_numero_mixto_33_veinte(self):
        """'33 veinte' = 2 dígitos + 1 palabra = preservar."""
        assert should_preserve_714("33 veinte") == True

    def test_vacio(self):
        """String vacío → no preservar."""
        assert should_preserve_714("") == False
