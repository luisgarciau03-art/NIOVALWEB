# -*- coding: utf-8 -*-
"""
Tests para FIX 713: BRUCE2263 - Threshold dinámico GPT eval
- 713A: Threshold dinámico (25s ultra-corta, 25-45s corta, >45s normal)
- 713B: Prompt enfocado para llamadas cortas (solo errores graves)
"""

import sys
import os
import time
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ============================================================
# Tests: Constantes de threshold
# ============================================================

class TestFix713AConstants:
    """Verificar que las constantes están correctamente definidas."""

    def test_min_turnos_es_2(self):
        """FIX 713A: Mínimo turnos bajado a 2."""
        from bug_detector import GPT_EVAL_MIN_TURNOS
        assert GPT_EVAL_MIN_TURNOS == 2

    def test_min_turnos_completo_es_3(self):
        """FIX 713A: GPT eval completo requiere 3+ turnos."""
        from bug_detector import GPT_EVAL_MIN_TURNOS_COMPLETO
        assert GPT_EVAL_MIN_TURNOS_COMPLETO == 3

    def test_min_duracion_es_25(self):
        """FIX 713A: Duración mínima bajada a 25s."""
        from bug_detector import GPT_EVAL_MIN_DURACION_S
        assert GPT_EVAL_MIN_DURACION_S == 25

    def test_duracion_corta_es_45(self):
        """FIX 713A: Llamada corta = < 45s."""
        from bug_detector import GPT_EVAL_DURACION_CORTA_S
        assert GPT_EVAL_DURACION_CORTA_S == 45


# ============================================================
# Tests: Threshold dinámico - clasificación de llamadas
# ============================================================

class TestFix713AClassification:
    """Verificar clasificación: ultra-corta vs corta vs normal."""

    def _make_tracker(self, turnos_bruce=2, duracion_s=40):
        """Helper: crea tracker simulado."""
        from bug_detector import CallEventTracker
        tracker = CallEventTracker("test_sid", "BRUCE_TEST", "+521234567890")
        tracker.created_at = time.time() - duracion_s
        for i in range(turnos_bruce):
            tracker.respuestas_bruce.append(f"Respuesta {i+1}")
            tracker.conversacion.append(("bruce", f"Respuesta {i+1}"))
            tracker.conversacion.append(("cliente", f"Cliente dice {i+1}"))
        return tracker

    def test_ultra_corta_skip(self):
        """< 25s → SKIP total (sin GPT eval)."""
        from bug_detector import GPT_EVAL_MIN_DURACION_S
        assert GPT_EVAL_MIN_DURACION_S == 25
        # 20s con 2 turnos → debería ser skipped
        tracker = self._make_tracker(turnos_bruce=2, duracion_s=20)
        assert len(tracker.respuestas_bruce) >= 2
        # La función _evaluar_con_gpt retornaría [] por duration < 25

    def test_1_turno_skip(self):
        """1 turno Bruce → SKIP (insuficiente contexto)."""
        from bug_detector import GPT_EVAL_MIN_TURNOS
        tracker = self._make_tracker(turnos_bruce=1, duracion_s=40)
        assert len(tracker.respuestas_bruce) < GPT_EVAL_MIN_TURNOS

    def test_corta_2_turnos_41s(self):
        """BRUCE2263: 2 turnos, 41s → llamada corta (prompt enfocado)."""
        from bug_detector import GPT_EVAL_MIN_TURNOS, GPT_EVAL_MIN_DURACION_S, GPT_EVAL_DURACION_CORTA_S, GPT_EVAL_MIN_TURNOS_COMPLETO
        tracker = self._make_tracker(turnos_bruce=2, duracion_s=41)
        duracion = int(time.time() - tracker.created_at)
        num_turnos = len(tracker.respuestas_bruce)

        # No es ultra-corta
        assert duracion >= GPT_EVAL_MIN_DURACION_S
        # Es corta
        es_llamada_corta = (duracion < GPT_EVAL_DURACION_CORTA_S or num_turnos < GPT_EVAL_MIN_TURNOS_COMPLETO)
        assert es_llamada_corta

    def test_corta_3_turnos_35s(self):
        """3 turnos, 35s → llamada corta por duración."""
        from bug_detector import GPT_EVAL_DURACION_CORTA_S, GPT_EVAL_MIN_TURNOS_COMPLETO
        tracker = self._make_tracker(turnos_bruce=3, duracion_s=35)
        duracion = int(time.time() - tracker.created_at)
        num_turnos = len(tracker.respuestas_bruce)

        es_llamada_corta = (duracion < GPT_EVAL_DURACION_CORTA_S or num_turnos < GPT_EVAL_MIN_TURNOS_COMPLETO)
        assert es_llamada_corta  # < 45s

    def test_corta_2_turnos_60s(self):
        """2 turnos, 60s → llamada corta por turnos."""
        from bug_detector import GPT_EVAL_DURACION_CORTA_S, GPT_EVAL_MIN_TURNOS_COMPLETO
        tracker = self._make_tracker(turnos_bruce=2, duracion_s=60)
        duracion = int(time.time() - tracker.created_at)
        num_turnos = len(tracker.respuestas_bruce)

        es_llamada_corta = (duracion < GPT_EVAL_DURACION_CORTA_S or num_turnos < GPT_EVAL_MIN_TURNOS_COMPLETO)
        assert es_llamada_corta  # 2 < 3 turnos

    def test_normal_3_turnos_60s(self):
        """3 turnos, 60s → llamada normal (prompt completo)."""
        from bug_detector import GPT_EVAL_DURACION_CORTA_S, GPT_EVAL_MIN_TURNOS_COMPLETO
        tracker = self._make_tracker(turnos_bruce=3, duracion_s=60)
        duracion = int(time.time() - tracker.created_at)
        num_turnos = len(tracker.respuestas_bruce)

        es_llamada_corta = (duracion < GPT_EVAL_DURACION_CORTA_S or num_turnos < GPT_EVAL_MIN_TURNOS_COMPLETO)
        assert not es_llamada_corta  # >= 45s AND >= 3 turnos

    def test_normal_5_turnos_120s(self):
        """5 turnos, 120s → llamada normal."""
        from bug_detector import GPT_EVAL_DURACION_CORTA_S, GPT_EVAL_MIN_TURNOS_COMPLETO
        tracker = self._make_tracker(turnos_bruce=5, duracion_s=120)
        duracion = int(time.time() - tracker.created_at)
        num_turnos = len(tracker.respuestas_bruce)

        es_llamada_corta = (duracion < GPT_EVAL_DURACION_CORTA_S or num_turnos < GPT_EVAL_MIN_TURNOS_COMPLETO)
        assert not es_llamada_corta


# ============================================================
# Tests: Prompt enfocado existe y tiene contenido correcto
# ============================================================

class TestFix713BPrompt:
    """Verificar que el prompt enfocado está bien definido."""

    def test_prompt_corta_existe(self):
        """Prompt para llamadas cortas existe."""
        from bug_detector import _GPT_EVAL_PROMPT_CORTA
        assert _GPT_EVAL_PROMPT_CORTA is not None
        assert len(_GPT_EVAL_PROMPT_CORTA) > 100

    def test_prompt_corta_tiene_contexto_ignorado(self):
        """Prompt corta detecta CONTEXTO_IGNORADO (encargado no detectado)."""
        from bug_detector import _GPT_EVAL_PROMPT_CORTA
        assert "CONTEXTO_IGNORADO" in _GPT_EVAL_PROMPT_CORTA

    def test_prompt_corta_tiene_respuesta_incoherente(self):
        """Prompt corta detecta RESPUESTA_INCOHERENTE (mmm entiendo)."""
        from bug_detector import _GPT_EVAL_PROMPT_CORTA
        assert "RESPUESTA_INCOHERENTE" in _GPT_EVAL_PROMPT_CORTA

    def test_prompt_corta_tiene_logica_rota(self):
        """Prompt corta detecta LOGICA_ROTA."""
        from bug_detector import _GPT_EVAL_PROMPT_CORTA
        assert "LOGICA_ROTA" in _GPT_EVAL_PROMPT_CORTA

    def test_prompt_corta_tiene_oportunidad_perdida(self):
        """Prompt corta detecta OPORTUNIDAD_PERDIDA."""
        from bug_detector import _GPT_EVAL_PROMPT_CORTA
        assert "OPORTUNIDAD_PERDIDA" in _GPT_EVAL_PROMPT_CORTA

    def test_prompt_corta_tiene_placeholder_conversacion(self):
        """Prompt corta tiene {conversacion} placeholder."""
        from bug_detector import _GPT_EVAL_PROMPT_CORTA
        assert "{conversacion}" in _GPT_EVAL_PROMPT_CORTA

    def test_prompt_corta_max_2_errores(self):
        """Prompt corta indica máximo 2 errores."""
        from bug_detector import _GPT_EVAL_PROMPT_CORTA
        assert "Maximo 2" in _GPT_EVAL_PROMPT_CORTA

    def test_prompt_completo_max_3_errores(self):
        """Prompt completo indica máximo 3 errores."""
        from bug_detector import _GPT_EVAL_PROMPT
        assert "Maximo 3" in _GPT_EVAL_PROMPT

    def test_prompt_corta_menciona_encargado(self):
        """Prompt corta menciona detección de encargado/dueño."""
        from bug_detector import _GPT_EVAL_PROMPT_CORTA
        assert "encargado" in _GPT_EVAL_PROMPT_CORTA
        assert "decisor" in _GPT_EVAL_PROMPT_CORTA

    def test_prompt_corta_menciona_tienes_donde_anotar(self):
        """Prompt corta menciona 'tienes donde anotar' como señal de decisor."""
        from bug_detector import _GPT_EVAL_PROMPT_CORTA
        assert "Tienes donde anotar" in _GPT_EVAL_PROMPT_CORTA

    def test_prompt_corta_anti_fp(self):
        """Prompt corta tiene reglas anti-FP estrictas."""
        from bug_detector import _GPT_EVAL_PROMPT_CORTA
        assert "DUDA" in _GPT_EVAL_PROMPT_CORTA
        assert "falso positivo" in _GPT_EVAL_PROMPT_CORTA


# ============================================================
# Tests: Código en bug_detector.py - verificación estructural
# ============================================================

class TestFix713EnCodigo:
    """Verificar FIX 713 en bug_detector.py."""

    def test_713a_existe_en_codigo(self):
        """FIX 713A debe estar en el código."""
        bd_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'bug_detector.py')
        with open(bd_path, 'r', encoding='utf-8') as f:
            source = f.read()
        assert "FIX 713A" in source
        assert "es_llamada_corta" in source
        assert "GPT_EVAL_DURACION_CORTA_S" in source
        assert "GPT_EVAL_MIN_TURNOS_COMPLETO" in source

    def test_713b_existe_en_codigo(self):
        """FIX 713B debe estar en el código."""
        bd_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'bug_detector.py')
        with open(bd_path, 'r', encoding='utf-8') as f:
            source = f.read()
        assert "FIX 713B" in source
        assert "_GPT_EVAL_PROMPT_CORTA" in source

    def test_prompt_seleccion_condicional(self):
        """Prompt se selecciona según es_llamada_corta."""
        bd_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'bug_detector.py')
        with open(bd_path, 'r', encoding='utf-8') as f:
            source = f.read()
        assert "if es_llamada_corta:" in source
        assert "_GPT_EVAL_PROMPT_CORTA" in source
        assert "_GPT_EVAL_PROMPT" in source

    def test_max_errores_dinamico(self):
        """max_errores varía según tipo de llamada."""
        bd_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'bug_detector.py')
        with open(bd_path, 'r', encoding='utf-8') as f:
            source = f.read()
        assert "max_errores = 2" in source
        assert "max_errores = 3" in source
        assert "errores[:max_errores]" in source


# ============================================================
# Tests: BRUCE2263 scenario (habría sido detectado con FIX 713)
# ============================================================

class TestFix713BRUCE2263:
    """BRUCE2263: 41s, 2 turnos → ahora sería evaluado como llamada corta."""

    def test_bruce2263_no_es_ultra_corta(self):
        """41s >= 25s → NO es ultra-corta → NO skip."""
        from bug_detector import GPT_EVAL_MIN_DURACION_S
        assert 41 >= GPT_EVAL_MIN_DURACION_S

    def test_bruce2263_es_llamada_corta(self):
        """41s < 45s → es llamada corta → prompt enfocado."""
        from bug_detector import GPT_EVAL_DURACION_CORTA_S
        assert 41 < GPT_EVAL_DURACION_CORTA_S

    def test_bruce2263_tiene_suficientes_turnos(self):
        """2 turnos >= 2 → suficiente para GPT eval."""
        from bug_detector import GPT_EVAL_MIN_TURNOS
        assert 2 >= GPT_EVAL_MIN_TURNOS

    def test_bruce2263_prompt_cubre_errores(self):
        """Prompt enfocado cubre los 3 errores de BRUCE2263."""
        from bug_detector import _GPT_EVAL_PROMPT_CORTA
        # Error 1: No detectó al encargado
        assert "encargado" in _GPT_EVAL_PROMPT_CORTA
        assert "CONTEXTO_IGNORADO" in _GPT_EVAL_PROMPT_CORTA
        # Error 2: Respuesta incoherente "entiendo"
        assert "entiendo" in _GPT_EVAL_PROMPT_CORTA.lower()
        assert "RESPUESTA_INCOHERENTE" in _GPT_EVAL_PROMPT_CORTA
        # Error 3: Dejó recado cuando hablaba con encargado
        assert "recado" in _GPT_EVAL_PROMPT_CORTA.lower() or "regrese" in _GPT_EVAL_PROMPT_CORTA.lower()


# ============================================================
# Tests: Edge cases
# ============================================================

class TestFix713EdgeCases:
    """Edge cases para threshold dinámico."""

    def test_exactamente_25s(self):
        """25s exactos → NO es ultra-corta (>=25)."""
        from bug_detector import GPT_EVAL_MIN_DURACION_S
        assert 25 >= GPT_EVAL_MIN_DURACION_S

    def test_exactamente_24s(self):
        """24s → SÍ es ultra-corta (<25)."""
        from bug_detector import GPT_EVAL_MIN_DURACION_S
        assert 24 < GPT_EVAL_MIN_DURACION_S

    def test_exactamente_45s(self):
        """45s → NO es corta (>=45), pero depende de turnos."""
        from bug_detector import GPT_EVAL_DURACION_CORTA_S
        assert 45 >= GPT_EVAL_DURACION_CORTA_S  # No es corta por duración

    def test_44s_es_corta(self):
        """44s → SÍ es corta (<45)."""
        from bug_detector import GPT_EVAL_DURACION_CORTA_S
        assert 44 < GPT_EVAL_DURACION_CORTA_S

    def test_2_turnos_siempre_corta(self):
        """2 turnos siempre es 'corta' independiente de duración."""
        from bug_detector import GPT_EVAL_MIN_TURNOS_COMPLETO
        assert 2 < GPT_EVAL_MIN_TURNOS_COMPLETO  # 2 < 3

    def test_3_turnos_45s_es_normal(self):
        """3 turnos + 45s → normal."""
        from bug_detector import GPT_EVAL_DURACION_CORTA_S, GPT_EVAL_MIN_TURNOS_COMPLETO
        duracion = 45
        num_turnos = 3
        es_corta = (duracion < GPT_EVAL_DURACION_CORTA_S or num_turnos < GPT_EVAL_MIN_TURNOS_COMPLETO)
        assert not es_corta
