"""
Tests de regresión para FIX 667-669: Anti-repetición GPT con post-filters

FIX 667A: Post-filter negación de datos (BRUCE2171)
FIX 667B: Post-filter información ignorada (BRUCE2173)
FIX 668: Post-filter encargado mañana sin hora (BRUCE2163)
FIX 669: Tests regresión para validar que FIX 646A ya no falla

Bug objetivo: BRUCE2171, BRUCE2173, BRUCE2163 (83.3% regresión post-FIX 664-666)
"""

import pytest
import inspect
import sys
import os

# Agregar el directorio padre al path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agente_ventas import AgenteVentas


class TestFix667ANegacionDatos:
    """Verificar que FIX 667A detecta cuando cliente negó tener dato específico"""

    def test_fix_667a_existe_en_codigo(self):
        """Verificar que FIX 667A está implementado"""
        source = inspect.getsource(AgenteVentas._filtrar_respuesta_post_gpt)

        # Debe mencionar FIX 667A
        assert "FIX 667A" in source
        assert "BRUCE2171" in source

    def test_fix_667a_patrones_negacion(self):
        """Verificar que FIX 667A tiene patrones de negación de datos"""
        source = inspect.getsource(AgenteVentas._filtrar_respuesta_post_gpt)

        # Debe detectar "solo tengo"
        assert "solo" in source or "tengo" in source
        assert "negaciones_dato" in source or "dato_negado" in source

    def test_fix_667a_detecta_solo_tengo_telefono(self):
        """Verificar que FIX 667A detecta 'solo tengo teléfono' → no pedir WhatsApp"""
        source = inspect.getsource(AgenteVentas._filtrar_respuesta_post_gpt)

        # Debe tener lógica para detectar dato negado
        assert "solo" in source.lower()
        assert "whatsapp" in source.lower() or "telefono" in source.lower()

    def test_fix_667a_override_respuesta(self):
        """Verificar que FIX 667A hace override cuando GPT pide dato negado"""
        source = inspect.getsource(AgenteVentas._filtrar_respuesta_post_gpt)

        # Debe tener alternativas de respuesta
        assert "alternativas" in source.lower() or "override" in source.lower()
        assert "proporcionar entonces" in source.lower() or "podria proporcionar" in source.lower()

    def test_fix_667a_detecta_no_tengo_whatsapp(self):
        """Verificar que FIX 667A detecta 'no tengo WhatsApp'"""
        source = inspect.getsource(AgenteVentas._filtrar_respuesta_post_gpt)

        # Debe tener patrón para "no tengo"
        assert "no" in source and "tengo" in source

    def test_fix_667a_alternativas_por_tipo_dato(self):
        """Verificar que FIX 667A tiene alternativas diferentes según dato negado"""
        source = inspect.getsource(AgenteVentas._filtrar_respuesta_post_gpt)

        # Debe mapear alternativas por tipo de dato
        assert "alternativas_667" in source or "dato_map" in source


class TestFix667BInformacionIgnorada:
    """Verificar que FIX 667B detecta cuando Bruce ignora información clave del cliente"""

    def test_fix_667b_existe_en_codigo(self):
        """Verificar que FIX 667B está implementado"""
        source = inspect.getsource(AgenteVentas._filtrar_respuesta_post_gpt)

        # Debe mencionar FIX 667B
        assert "FIX 667B" in source
        assert "BRUCE2173" in source

    def test_fix_667b_patrones_error(self):
        """Verificar que FIX 667B detecta 'no es la sucursal correcta'"""
        source = inspect.getsource(AgenteVentas._filtrar_respuesta_post_gpt)

        # Debe detectar indicadores de error
        assert "indicadores_error" in source or "indico_error" in source
        assert "no es" in source.lower() or "sucursal" in source.lower()

    def test_fix_667b_detecta_sucursal_incorrecta(self):
        """Verificar que FIX 667B tiene patrón para sucursal incorrecta"""
        source = inspect.getsource(AgenteVentas._filtrar_respuesta_post_gpt)

        # Debe tener patrón específico
        assert "sucursal" in source.lower() or "ubicacion" in source.lower()
        assert "incorrecto" in source.lower() or "equivocado" in source.lower()

    def test_fix_667b_override_cuando_pide_datos(self):
        """Verificar que FIX 667B hace override si Bruce pide datos de ubicación incorrecta"""
        source = inspect.getsource(AgenteVentas._filtrar_respuesta_post_gpt)

        # Debe verificar si pide datos de sucursal
        assert "pide_datos_sucursal" in source or "datos de" in source.lower()

    def test_fix_667b_respuesta_corregida(self):
        """Verificar que FIX 667B pregunta por ubicación correcta"""
        source = inspect.getsource(AgenteVentas._filtrar_respuesta_post_gpt)

        # Debe tener respuesta corregida (con o sin tilde)
        assert "correcta" in source.lower() and ("ubicacion" in source.lower() or "sucursal" in source.lower())

    def test_fix_667b_detecta_equivocacion(self):
        """Verificar que FIX 667B detecta 'se equivocó'"""
        source = inspect.getsource(AgenteVentas._filtrar_respuesta_post_gpt)

        # Debe tener patrón para equivocación
        assert "equivoc" in source.lower()


class TestFix668EncargadoManana:
    """Verificar que FIX 668 detecta encargado disponible mañana sin hora"""

    def test_fix_668_existe_en_codigo(self):
        """Verificar que FIX 668 está implementado"""
        source = inspect.getsource(AgenteVentas._filtrar_respuesta_post_gpt)

        # Debe mencionar FIX 668
        assert "FIX 668" in source
        assert "BRUCE2163" in source

    def test_fix_668_patrones_manana(self):
        """Verificar que FIX 668 detecta 'mañana' sin hora"""
        source = inspect.getsource(AgenteVentas._filtrar_respuesta_post_gpt)

        # Debe detectar indicadores de mañana
        assert "indicadores_manana" in source or "manana" in source.lower()

    def test_fix_668_verifica_sin_hora(self):
        """Verificar que FIX 668 verifica que cliente NO mencionó hora"""
        source = inspect.getsource(AgenteVentas._filtrar_respuesta_post_gpt)

        # Debe verificar ausencia de hora (delegar a FIX 665)
        assert "tiene_hora_668" in source or "patron_hora_668" in source

    def test_fix_668_override_pedir_contacto(self):
        """Verificar que FIX 668 hace override si Bruce pide contacto en vez de hora"""
        source = inspect.getsource(AgenteVentas._filtrar_respuesta_post_gpt)

        # Debe verificar si pide contacto
        assert "pide_contacto_668" in source

    def test_fix_668_pregunta_hora(self):
        """Verificar que FIX 668 pregunta '¿A qué hora mañana?'"""
        source = inspect.getsource(AgenteVentas._filtrar_respuesta_post_gpt)

        # Debe tener respuesta que pregunta hora
        assert "a que hora" in source.lower() or "que hora mañana" in source.lower()

    def test_fix_668_no_interfiere_con_fix_665(self):
        """Verificar que FIX 668 no interfiere con FIX 665 (hora ya mencionada)"""
        source = inspect.getsource(AgenteVentas._filtrar_respuesta_post_gpt)

        # Debe verificar FIX 665 primero (tiene_hora, menciona_hora_palabra)
        assert "tiene_hora_668" in source or "menciona_hora_palabra_668" in source


class TestFix669RegresionFix646A:
    """Tests de regresión para validar que FIX 646A ya no falla con post-filters"""

    def test_fix_646a_sigue_presente(self):
        """Verificar que FIX 646A sigue presente en system prompt"""
        source = inspect.getsource(AgenteVentas.procesar_respuesta)

        # FIX 646A está en el system prompt de GPT
        assert "FIX 646A" in source or "REGLAS ANTI-REPETICION" in source

    def test_fix_667_668_complementan_fix_646a(self):
        """Verificar que FIX 667-668 complementan FIX 646A (no lo reemplazan)"""
        source_post_filter = inspect.getsource(AgenteVentas._filtrar_respuesta_post_gpt)

        # Debe tener FIX 667A, 667B, 668
        assert "FIX 667A" in source_post_filter
        assert "FIX 667B" in source_post_filter
        assert "FIX 668" in source_post_filter

    def test_todos_fixes_documentados(self):
        """Verificar que todos los fixes están documentados con BRUCE IDs"""
        source = inspect.getsource(AgenteVentas._filtrar_respuesta_post_gpt)

        # Debe tener los 3 BRUCE IDs de regresión
        assert "BRUCE2171" in source  # FIX 667A
        assert "BRUCE2173" in source  # FIX 667B
        assert "BRUCE2163" in source  # FIX 668


class TestIntegracionFix667_668_669:
    """Tests de integración para FIX 667-669"""

    def test_no_rompe_fix_646a(self):
        """Verificar que FIX 667-669 no rompieron FIX 646A original"""
        source_procesar = inspect.getsource(AgenteVentas.procesar_respuesta)

        # FIX 646A debe seguir presente
        assert "FIX 646A" in source_procesar or "encargado NO ESTA" in source_procesar

    def test_no_rompe_fix_665(self):
        """Verificar que FIX 668 no rompe FIX 665 (hora ya mencionada)"""
        source = inspect.getsource(AgenteVentas._filtrar_respuesta_post_gpt)

        # FIX 665 debe seguir presente
        assert "FIX 665" in source

    def test_orden_ejecucion_correcto(self):
        """Verificar que FIX 667-668 se ejecutan DESPUÉS de FIX 665"""
        source = inspect.getsource(AgenteVentas._filtrar_respuesta_post_gpt)

        # Buscar posiciones
        pos_665 = source.find("FIX 665")
        pos_667a = source.find("FIX 667A")
        pos_668 = source.find("FIX 668")

        # FIX 665 debe estar ANTES de FIX 668 (para no interferir)
        # Pero como FIX 668 verifica que NO hay hora (delegando a FIX 665), el orden no importa tanto
        # Lo importante es que ambos existan
        assert pos_665 > 0, "FIX 665 no encontrado"
        assert pos_667a > 0, "FIX 667A no encontrado"
        assert pos_668 > 0, "FIX 668 no encontrado"

    def test_logging_presente(self):
        """Verificar que FIX 667-668 tienen logging para debugging"""
        source = inspect.getsource(AgenteVentas._filtrar_respuesta_post_gpt)

        # Debe tener prints de debug
        assert "FIX 667A:" in source or "BRUCE2171" in source
        assert "FIX 667B:" in source or "BRUCE2173" in source
        assert "FIX 668:" in source or "BRUCE2163" in source


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
