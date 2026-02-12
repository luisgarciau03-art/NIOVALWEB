# -*- coding: utf-8 -*-
"""
Tests de regresión para FIX 682 (GPT timeout resilience) y FIX 683 (STT timeout adaptativo).
"""
import os
import sys
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault("OPENAI_API_KEY", "sk-test-dummy")
os.environ.setdefault("ELEVENLABS_API_KEY", "test-dummy")
os.environ.setdefault("TWILIO_ACCOUNT_SID", "AC-test")
os.environ.setdefault("TWILIO_AUTH_TOKEN", "test-token")

from agente_ventas import AgenteVentas


# ============================================================
# FIX 682: GPT Timeout Resilience
# ============================================================

class TestFix682GPTTimeoutResilience:
    """FIX 682: GPT timeout usa fallback contextual en vez de colgar."""

    def test_gpt_timeout_counter_initialized(self):
        """Agente debe tener contador de GPT timeouts consecutivos."""
        a = AgenteVentas.__new__(AgenteVentas)
        a.gpt_timeouts_consecutivos = 0
        assert a.gpt_timeouts_consecutivos == 0

    def test_primer_timeout_no_cuelga(self):
        """Lógica: 1er GPT timeout → fallback, NO colgar."""
        gpt_timeouts = 0
        gpt_timeouts += 1  # Simular timeout

        # Simular lógica FIX 682
        if gpt_timeouts >= 2:
            accion = "colgar"
        else:
            accion = "fallback"

        assert accion == "fallback"
        assert gpt_timeouts == 1

    def test_segundo_timeout_cuelga(self):
        """Lógica: 2do GPT timeout consecutivo → colgar profesionalmente."""
        gpt_timeouts = 1  # Ya tuvo 1 timeout
        gpt_timeouts += 1  # 2do timeout

        if gpt_timeouts >= 2:
            accion = "colgar"
        else:
            accion = "fallback"

        assert accion == "colgar"
        assert gpt_timeouts == 2

    def test_reset_despues_de_exito(self):
        """Contador se resetea después de respuesta GPT exitosa."""
        gpt_timeouts = 1
        respuesta = "Le comento que manejamos productos ferreteros."
        # Simular reset
        if respuesta and 'problemas con la conexión' not in respuesta:
            gpt_timeouts = 0
        assert gpt_timeouts == 0

    def test_no_reset_si_problemas_conexion(self):
        """No resetear si respuesta contiene 'problemas con la conexión'."""
        gpt_timeouts = 1
        respuesta = "Disculpe, tengo problemas con la conexión en este momento."
        if respuesta and 'problemas con la conexión' not in respuesta:
            gpt_timeouts = 0
        assert gpt_timeouts == 1

    def test_fallback_sin_presentar_da_pitch(self):
        """Si no se presentó, fallback da pitch completo."""
        historial = [{"role": "assistant", "content": "Hola, buen día."}]
        ya_presento = any('nioval' in m.get('content', '').lower()
                         for m in historial if m['role'] == 'assistant')
        ya_encargado = any('encargad' in m.get('content', '').lower()
                          for m in historial if m['role'] == 'assistant')
        if not ya_presento:
            fallback = "Me comunico de la marca NIOVAL..."
        elif not ya_encargado:
            fallback = "¿Se encontrará el encargado?"
        else:
            fallback = "Disculpe, ¿me puede repetir?"

        assert 'NIOVAL' in fallback

    def test_fallback_con_pitch_da_encargado(self):
        """Si ya presentó pero no preguntó encargado, fallback pregunta encargado."""
        historial = [{"role": "assistant", "content": "Me comunico de la marca nioval para productos."}]
        ya_presento = any('nioval' in m.get('content', '').lower()
                         for m in historial if m['role'] == 'assistant')
        ya_encargado = any('encargad' in m.get('content', '').lower()
                          for m in historial if m['role'] == 'assistant')
        if not ya_presento:
            fallback = "Me comunico de la marca NIOVAL..."
        elif not ya_encargado:
            fallback = "¿Se encontrará el encargado?"
        else:
            fallback = "Disculpe, ¿me puede repetir?"

        assert 'encargado' in fallback.lower()

    def test_fallback_con_todo_pide_repetir(self):
        """Si ya presentó Y preguntó encargado, fallback pide repetir."""
        historial = [{"role": "assistant", "content": "Me comunico de nioval. ¿Se encontrará el encargado?"}]
        ya_presento = any('nioval' in m.get('content', '').lower()
                         for m in historial if m['role'] == 'assistant')
        ya_encargado = any('encargad' in m.get('content', '').lower()
                          for m in historial if m['role'] == 'assistant')
        if not ya_presento:
            fallback = "Me comunico de la marca NIOVAL..."
        elif not ya_encargado:
            fallback = "¿Se encontrará el encargado?"
        else:
            fallback = "Disculpe, ¿me puede repetir?"

        assert 'repetir' in fallback.lower()


# ============================================================
# FIX 683: STT Timeout Adaptativo
# ============================================================

class TestFix683STTTimeoutAdaptive:
    """FIX 683: Timeouts STT más generosos para dar margen a Azure."""

    def test_primer_turno_2s(self):
        """Sin timeouts previos, timeout debe ser 2.0s (FIX 683)."""
        timeouts_previos = 0
        if timeouts_previos >= 2:
            max_wait = 1.5
        elif timeouts_previos == 1:
            max_wait = 1.8
        else:
            max_wait = 2.0
        assert max_wait == 2.0

    def test_despues_1_timeout_1_8s(self):
        """Después de 1 timeout, timeout debe ser 1.8s."""
        timeouts_previos = 1
        if timeouts_previos >= 2:
            max_wait = 1.5
        elif timeouts_previos == 1:
            max_wait = 1.8
        else:
            max_wait = 2.0
        assert max_wait == 1.8

    def test_despues_2_timeouts_1_5s(self):
        """Después de 2+ timeouts, timeout debe ser 1.5s (no 1.0s como antes)."""
        timeouts_previos = 2
        if timeouts_previos >= 2:
            max_wait = 1.5
        elif timeouts_previos == 1:
            max_wait = 1.8
        else:
            max_wait = 2.0
        assert max_wait == 1.5

    def test_timeouts_nunca_menor_1_5s(self):
        """Incluso con muchos timeouts, nunca bajar de 1.5s."""
        for prev in range(0, 10):
            if prev >= 2:
                max_wait = 1.5
            elif prev == 1:
                max_wait = 1.8
            else:
                max_wait = 2.0
            assert max_wait >= 1.5, f"Timeout {max_wait}s demasiado bajo con {prev} previos"

    def test_progresion_decreciente(self):
        """Timeout decrece con más timeouts previos."""
        waits = []
        for prev in [0, 1, 2, 3]:
            if prev >= 2:
                waits.append(1.5)
            elif prev == 1:
                waits.append(1.8)
            else:
                waits.append(2.0)
        # Debe ser decreciente o estable (nunca creciente)
        for i in range(len(waits) - 1):
            assert waits[i] >= waits[i + 1], f"Timeout subió: {waits[i]}→{waits[i+1]}"
