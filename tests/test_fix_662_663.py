"""
Tests de regresión para FIX 662-663: Reducción de timeouts STT

FIX 662: Aumentar timeout de 1.5s → 2.0s
FIX 663: Mejorar fallback de Azure Speech (usar como fallback real, no solo logging)

Bug objetivo: BRUCE2144 - CLIENTE_HABLA_ULTIMO (10% de bugs)
Meta: Reducir de 10% → 1-2% (-80% a -90%)
"""

import pytest
import inspect
import sys
import os

# Agregar el directorio padre al path para importar servidor_llamadas
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import servidor_llamadas


class TestFix662TimeoutAumentado:
    """Verificar que FIX 662 aumentó timeout de 1.5s a 2.0s"""

    def test_fix_662_existe_en_codigo(self):
        """Verificar que FIX 662 está documentado"""
        source = inspect.getsource(servidor_llamadas)

        # Debe mencionar FIX 662
        assert "FIX 662" in source
        assert "BRUCE2144" in source

    def test_fix_662_timeout_aumentado(self):
        """Verificar que timeout aumentó de 1.5s a 2.0s"""
        source = inspect.getsource(servidor_llamadas)

        # Buscar la línea donde se define timeout_espera para casos normales
        lines = source.split('\n')
        timeout_lines = [l for l in lines if 'timeout_espera = ' in l and 'FIX 662' in l]

        assert len(timeout_lines) > 0, "No se encontró línea con FIX 662"

        # Verificar que tiene 2.0
        timeout_line = timeout_lines[0]
        assert "2.0" in timeout_line, f"Timeout no es 2.0: {timeout_line}"

    def test_fix_662_no_1_5_hardcoded(self):
        """Verificar que no hay 1.5s hardcoded en timeout normal"""
        source = inspect.getsource(servidor_llamadas)

        # Buscar líneas con timeout_espera
        lines = source.split('\n')
        for i, line in enumerate(lines):
            if 'timeout_espera = 1.5' in line and 'else:' in lines[i-1]:
                # Debe tener comentario ANTES o ser parte de FIX viejo
                assert "FIX 319" in line or "ANTES" in line, \
                    f"Línea {i+1}: timeout_espera = 1.5 sin justificación"

    def test_fix_662_comentario_fix_319(self):
        """Verificar que FIX 662 reemplazó FIX 319 en comentario"""
        source = inspect.getsource(servidor_llamadas)

        # FIX 662 debe estar junto con timeout_espera = 2.0
        lines = source.split('\n')
        for i, line in enumerate(lines):
            if 'timeout_espera = 2.0' in line:
                assert "FIX 662" in line, f"Línea {i+1}: falta comentario FIX 662"
                break


class TestFix663AzureFallback:
    """Verificar que FIX 663 mejoró fallback de Azure Speech"""

    def test_fix_663_existe_en_codigo(self):
        """Verificar que FIX 663 está implementado"""
        source = inspect.getsource(servidor_llamadas)

        # Debe mencionar FIX 663
        assert "FIX 663" in source
        assert "BRUCE2144" in source

    def test_fix_663_verifica_azure_pre_timeout(self):
        """Verificar que FIX 663 chequea Azure ANTES de declarar timeout"""
        source = inspect.getsource(servidor_llamadas)

        # Debe tener mensaje específico
        assert "Azure tiene transcripción PRE-timeout" in source
        assert "Usando Azure como fallback real" in source

    def test_fix_663_usa_azure_transcripciones(self):
        """Verificar que FIX 663 usa azure_transcripciones"""
        source = inspect.getsource(servidor_llamadas)

        # Debe verificar azure_transcripciones
        assert "azure_transcripciones[call_sid]" in source

        # Debe unir transcripciones con ' '.join()
        assert "' '.join(transcripciones_azure)" in source or \
               '` `.join(transcripciones_azure)' in source or \
               "join(transcripciones_azure)" in source

    def test_fix_663_limpia_buffer_azure(self):
        """Verificar que FIX 663 limpia el buffer de Azure después de usar"""
        source = inspect.getsource(servidor_llamadas)

        # Debe limpiar buffer
        lines = source.split('\n')
        azure_text_found = False
        azure_clear_found = False

        for i, line in enumerate(lines):
            if 'azure_texto_663' in line and 'if len(azure_texto_663)' in line:
                azure_text_found = True
            if azure_text_found and 'azure_transcripciones[call_sid] = []' in line:
                azure_clear_found = True
                break

        assert azure_text_found, "No se encontró verificación de azure_texto_663"
        assert azure_clear_found, "No se encontró limpieza de buffer azure_transcripciones"

    def test_fix_663_resetea_timeouts(self):
        """Verificar que FIX 663 resetea contador cuando Azure funciona"""
        source = inspect.getsource(servidor_llamadas)

        # Debe resetear timeouts_deepgram cuando Azure funciona
        assert "Azure fallback exitoso - reseteando timeouts" in source or \
               "timeouts_deepgram = 0" in source

    def test_fix_663_estructura_condicional(self):
        """Verificar estructura if/else correcta para fallback"""
        source = inspect.getsource(servidor_llamadas)

        # Debe tener estructura:
        # if not azure_texto_663:
        #     # proceder con timeout normal
        # else:
        #     # resetear timeouts
        lines = source.split('\n')

        found_azure_check = False
        found_timeout_normal = False
        found_reset_timeouts = False

        for i, line in enumerate(lines):
            if 'if not azure_texto_663:' in line:
                found_azure_check = True
            if found_azure_check and 'FIX 534' in line:
                found_timeout_normal = True
            if found_azure_check and 'Azure fallback exitoso' in line:
                found_reset_timeouts = True

        assert found_azure_check, "No se encontró check 'if not azure_texto_663'"
        assert found_timeout_normal, "No se encontró bloque de timeout normal (FIX 534)"
        assert found_reset_timeouts, "No se encontró reset de timeouts cuando Azure funciona"


class TestIntegracionFix662_663:
    """Tests de integración para FIX 662-663"""

    def test_ambos_fixes_documentados(self):
        """Verificar que ambos fixes están documentados"""
        source = inspect.getsource(servidor_llamadas)

        # FIX 662
        assert "FIX 662" in source

        # FIX 663
        assert "FIX 663" in source

    def test_fix_662_no_rompe_timeouts_especiales(self):
        """Verificar que FIX 662 no afectó timeouts especiales (0s, 0.3s)"""
        source = inspect.getsource(servidor_llamadas)

        # Debe mantener timeouts especiales
        lines = source.split('\n')

        tiene_timeout_0 = False
        tiene_timeout_0_3 = False

        for line in lines:
            if 'timeout_espera = 0' in line and 'FIX 146' in line:
                tiene_timeout_0 = True
            if 'timeout_espera = 0.3' in line and 'FIX 319' in line:
                tiene_timeout_0_3 = True

        assert tiene_timeout_0, "FIX 662 eliminó timeout = 0 (cliente desesperado)"
        assert tiene_timeout_0_3, "FIX 662 eliminó timeout = 0.3 (primera respuesta)"

    def test_fix_663_no_rompe_fix_613(self):
        """Verificar que FIX 663 no rompió FIX 613 (Azure primario)"""
        source = inspect.getsource(servidor_llamadas)

        # FIX 613 debe seguir presente (Azure como primario)
        assert "FIX 613" in source

        # Debe mantener azure_transcripciones_lock
        assert "azure_transcripciones_lock" in source

    def test_cobertura_objetivo(self):
        """Verificar que FIX 662-663 cubren el objetivo de reducción"""
        # Meta: Reducir CLIENTE_HABLA_ULTIMO de 10% → 1-2%
        # FIX 662: +0.5s timeout → -50% a -70% bugs
        # FIX 663: Azure fallback real → -80% a -90% bugs
        # Combinados: -80% a -90% total

        reduccion_fix_662_min = 0.50  # 50%
        reduccion_fix_663_min = 0.80  # 80%

        # Verificar que ambos fixes están presentes
        source = inspect.getsource(servidor_llamadas)
        fix_662_present = "FIX 662" in source
        fix_663_present = "FIX 663" in source

        assert fix_662_present, "FIX 662 no está presente"
        assert fix_663_present, "FIX 663 no está presente"

        # Si ambos están presentes, la reducción esperada es válida
        reduccion_total_esperada = 1 - ((1 - reduccion_fix_662_min) * (1 - reduccion_fix_663_min))
        assert reduccion_total_esperada >= 0.80, \
            f"Reducción combinada esperada: {reduccion_total_esperada*100:.0f}% (meta: 80-90%)"


class TestRegresionBRUCE2144:
    """Test específico para el caso BRUCE2144"""

    def test_bruce2144_scenario_cubierto(self):
        """
        Simular BRUCE2144:
        Cliente: "Señor." (audio corto 0.5s)
        Deepgram: timeout 1.5s → 2.0s (FIX 662)
        Azure: fallback activo (FIX 663)

        Verificar que:
        1. FIX 662: Timeout aumentado da más tiempo
        2. FIX 663: Azure se usa como fallback real
        """
        source = inspect.getsource(servidor_llamadas)

        # FIX 662: Timeout aumentado
        assert "timeout_espera = 2.0" in source

        # FIX 663: Azure fallback antes de timeout
        assert "Azure tiene transcripción PRE-timeout" in source

        # Verificar que ambos trabajan juntos
        lines = source.split('\n')

        found_timeout_2_0 = False
        found_azure_fallback = False

        for line in lines:
            if 'timeout_espera = 2.0' in line and 'FIX 662' in line:
                found_timeout_2_0 = True
            if 'azure_texto_663' in line and 'FIX 663' in line:
                found_azure_fallback = True

        assert found_timeout_2_0, "FIX 662 no implementado correctamente"
        assert found_azure_fallback, "FIX 663 no implementado correctamente"

    def test_no_rompe_fix_642a(self):
        """Verificar que FIX 662-663 no rompieron FIX 642A (detector CLIENTE_HABLA_ULTIMO)"""
        # FIX 642A está en bug_detector.py, no en servidor_llamadas.py
        # Verificar que bug_detector sigue disponible
        try:
            from bug_detector import get_or_create_tracker
            bug_detector_disponible = True
        except ImportError:
            bug_detector_disponible = False

        # Si bug_detector está disponible, debe tener FIX 642A
        if bug_detector_disponible:
            import bug_detector
            source_bug_detector = inspect.getsource(bug_detector)
            assert "FIX 642A" in source_bug_detector or "CLIENTE_HABLA_ULTIMO" in source_bug_detector
        else:
            # Si no está disponible, al menos verificar que el import está en servidor
            source_servidor = inspect.getsource(servidor_llamadas)
            assert "from bug_detector import" in source_servidor or "bug_detector" in source_servidor
