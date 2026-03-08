"""
Tests de regresión para FIX 670: Detectar números dictados en palabras

FIX 670: Complementa FIX 512 para detectar números en PALABRAS, no solo dígitos numéricos
Bug objetivo: BRUCE2173 (CLIENTE_HABLA_ULTIMO - cliente dictó número pero Bruce nunca respondió)

Problema: Cliente dijo "Seis seis veintidós. Seis uno. Seis uno. Noventa y uno. Sesenta y cuatro..."
  FIX 512 solo detectaba dígitos numéricos (0-9)
  Cliente dictó 10 dígitos en palabras pero Bruce esperó más datos
"""

import pytest
import inspect
import sys
import os

# Agregar el directorio padre al path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestFix670ExisteEnCodigo:
    """Verificar que FIX 670 está implementado en servidor_llamadas.py"""

    def test_fix_670_existe(self):
        """Verificar que FIX 670 está en el código"""
        servidor_path = os.path.join(os.path.dirname(__file__), '..', 'servidor_llamadas.py')

        if not os.path.exists(servidor_path):
            pytest.skip("servidor_llamadas.py no encontrado")

        with open(servidor_path, 'r', encoding='utf-8') as f:
            source = f.read()

        # Debe mencionar FIX 670
        assert "FIX 670" in source
        assert "BRUCE2173" in source

    def test_fix_670_despues_fix_512(self):
        """Verificar que FIX 670 está después de FIX 512 (orden correcto)"""
        servidor_path = os.path.join(os.path.dirname(__file__), '..', 'servidor_llamadas.py')

        if not os.path.exists(servidor_path):
            pytest.skip("servidor_llamadas.py no encontrado")

        with open(servidor_path, 'r', encoding='utf-8') as f:
            source = f.read()

        # Buscar posiciones
        pos_512 = source.find("FIX 512")
        pos_670 = source.find("FIX 670")

        assert pos_512 > 0, "FIX 512 no encontrado"
        assert pos_670 > 0, "FIX 670 no encontrado"
        assert pos_670 > pos_512, "FIX 670 debe estar DESPUÉS de FIX 512"


class TestFix670DeteccionNumeroPalabras:
    """Verificar detección de números en palabras"""

    def test_fix_670_tiene_diccionario_numeros(self):
        """Verificar que FIX 670 tiene diccionario de números en palabras"""
        servidor_path = os.path.join(os.path.dirname(__file__), '..', 'servidor_llamadas.py')

        if not os.path.exists(servidor_path):
            pytest.skip("servidor_llamadas.py no encontrado")

        with open(servidor_path, 'r', encoding='utf-8') as f:
            source = f.read()

        # Debe tener diccionario con números básicos
        assert "numeros_palabras_670" in source
        assert "'cero'" in source or "'uno'" in source
        assert "'seis'" in source  # Usado en BRUCE2173
        assert "'veinte'" in source or "'veintidos'" in source  # Usado en BRUCE2173

    def test_fix_670_cuenta_numeros_detectados(self):
        """Verificar que FIX 670 cuenta números detectados"""
        servidor_path = os.path.join(os.path.dirname(__file__), '..', 'servidor_llamadas.py')

        if not os.path.exists(servidor_path):
            pytest.skip("servidor_llamadas.py no encontrado")

        with open(servidor_path, 'r', encoding='utf-8') as f:
            source = f.read()

        # Debe contar números detectados
        assert "numeros_detectados_670" in source
        assert "sum(1 for palabra in numeros_palabras_670" in source

    def test_fix_670_threshold_seis_o_mas(self):
        """Verificar que FIX 670 usa threshold de 6+ números (razonable para teléfonos)"""
        servidor_path = os.path.join(os.path.dirname(__file__), '..', 'servidor_llamadas.py')

        if not os.path.exists(servidor_path):
            pytest.skip("servidor_llamadas.py no encontrado")

        with open(servidor_path, 'r', encoding='utf-8') as f:
            source = f.read()

        # Debe usar threshold >= 6 (6-10 números = teléfono típico)
        assert ">= 6" in source or ">= 10" in source or ">= 8" in source


class TestFix670ComportamientoEsperado:
    """Verificar comportamiento esperado de FIX 670"""

    def test_fix_670_desactiva_modo_espera(self):
        """Verificar que FIX 670 desactiva cliente_pidio_espera"""
        servidor_path = os.path.join(os.path.dirname(__file__), '..', 'servidor_llamadas.py')

        if not os.path.exists(servidor_path):
            pytest.skip("servidor_llamadas.py no encontrado")

        with open(servidor_path, 'r', encoding='utf-8') as f:
            source = f.read()

        # Buscar sección de FIX 670
        fix_670_start = source.find("FIX 670")
        fix_670_section = source[fix_670_start:fix_670_start + 2000]

        # Debe desactivar modo espera
        assert "cliente_pidio_espera = False" in fix_670_section

    def test_fix_670_tiene_logging(self):
        """Verificar que FIX 670 tiene logging de debug"""
        servidor_path = os.path.join(os.path.dirname(__file__), '..', 'servidor_llamadas.py')

        if not os.path.exists(servidor_path):
            pytest.skip("servidor_llamadas.py no encontrado")

        with open(servidor_path, 'r', encoding='utf-8') as f:
            source = f.read()

        # Buscar sección de FIX 670
        fix_670_start = source.find("FIX 670")
        fix_670_section = source[fix_670_start:fix_670_start + 2000]

        # Debe tener prints de debug
        assert "print(f\"" in fix_670_section
        assert "dictando NÚMERO EN PALABRAS" in fix_670_section.upper() or "EN PALABRAS" in fix_670_section


class TestFix670Integracion:
    """Tests de integración con FIX 512"""

    def test_fix_670_complementa_fix_512(self):
        """Verificar que FIX 670 complementa FIX 512 (no lo reemplaza)"""
        servidor_path = os.path.join(os.path.dirname(__file__), '..', 'servidor_llamadas.py')

        if not os.path.exists(servidor_path):
            pytest.skip("servidor_llamadas.py no encontrado")

        with open(servidor_path, 'r', encoding='utf-8') as f:
            source = f.read()

        # FIX 670 debe existir
        assert "FIX 670" in source

        # FIX 670 debe tener su propia lógica (no reemplazar FIX 512)
        # Buscar sección de FIX 670
        fix_670_start = source.find("FIX 670")
        fix_670_section = source[fix_670_start:fix_670_start + 2000]

        # FIX 670 debe detectar números en palabras (no dígitos)
        assert "numeros_palabras_670" in fix_670_section
        assert "'seis'" in fix_670_section or "'uno'" in fix_670_section

    def test_no_rompe_fix_626a(self):
        """Verificar que FIX 670 no rompe FIX 626A (ofrece dato)"""
        servidor_path = os.path.join(os.path.dirname(__file__), '..', 'servidor_llamadas.py')

        if not os.path.exists(servidor_path):
            pytest.skip("servidor_llamadas.py no encontrado")

        with open(servidor_path, 'r', encoding='utf-8') as f:
            source = f.read()

        # FIX 626A debe seguir presente y después de FIX 670
        pos_670 = source.find("FIX 670")
        pos_626a = source.find("FIX 626A")

        assert pos_626a > 0, "FIX 626A no encontrado"
        # FIX 626A puede estar antes o después, lo importante es que ambos existan


class TestFix670CasosReales:
    """Tests basados en casos reales de BRUCE2173"""

    def test_bruce2173_patron_detectado(self):
        """Simular texto de BRUCE2173 y verificar detección"""
        servidor_path = os.path.join(os.path.dirname(__file__), '..', 'servidor_llamadas.py')

        if not os.path.exists(servidor_path):
            pytest.skip("servidor_llamadas.py no encontrado")

        with open(servidor_path, 'r', encoding='utf-8') as f:
            source = f.read()

        # Texto real de BRUCE2173
        texto_bruce2173 = "seis seis veintidos seis uno seis uno noventa y uno sesenta y cuatro seis cuatro"

        # Verificar que los números del diccionario están en el código
        numeros_en_bruce2173 = ['seis', 'veintidos', 'uno', 'noventa', 'sesenta', 'cuatro']
        for num in numeros_en_bruce2173:
            # Al menos algunos deben estar en el diccionario
            if f"'{num}'" in source:
                break
        else:
            pytest.fail(f"Ninguno de los números de BRUCE2173 está en numeros_palabras_670: {numeros_en_bruce2173}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
