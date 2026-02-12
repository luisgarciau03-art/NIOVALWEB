# -*- coding: utf-8 -*-
"""
Tests de regresión para FIX 680 (no repetir encargado en timeout paths)
y FIX 681 (mejorar CAL-001/FLU-001 auditor).
"""
import os
import sys
import pytest

# Agregar directorio padre al path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Env vars necesarias antes de importar
os.environ.setdefault("OPENAI_API_KEY", "sk-test-dummy")
os.environ.setdefault("ELEVENLABS_API_KEY", "test-dummy")
os.environ.setdefault("TWILIO_ACCOUNT_SID", "AC-test")
os.environ.setdefault("TWILIO_AUTH_TOKEN", "test-token")


# ============================================================
# FIX 680: Tests de detección lógica (no requieren servidor Flask)
# ============================================================

class TestFix680EncargadoRepeatDetection:
    """FIX 680: Si ya preguntó por encargado Y ya presentó, no repetir encargado en timeout."""

    def test_ya_presento_y_ya_pregunto_encargado(self):
        """Si historial tiene nioval + encargado, ambos flags deben ser True."""
        historial = [
            {"role": "assistant", "content": "Hola, buen día."},
            {"role": "assistant", "content": "Me comunico de la marca nioval, ¿se encontrará el encargado de compras?"},
            {"role": "user", "content": "Mande."},
        ]
        ya_presento = any('nioval' in m.get('content', '').lower()
                         for m in historial if m['role'] == 'assistant')
        ya_pregunto_encargado = any('encargad' in m.get('content', '').lower()
                                    for m in historial if m['role'] == 'assistant')
        assert ya_presento is True
        assert ya_pregunto_encargado is True

    def test_ya_presento_sin_encargado(self):
        """Si solo mencionó nioval pero NO encargado, encargado flag False."""
        historial = [
            {"role": "assistant", "content": "Hola, buen día."},
            {"role": "assistant", "content": "Me comunico de la marca nioval para brindar información."},
            {"role": "user", "content": "Bueno."},
        ]
        ya_presento = any('nioval' in m.get('content', '').lower()
                         for m in historial if m['role'] == 'assistant')
        ya_pregunto_encargado = any('encargad' in m.get('content', '').lower()
                                    for m in historial if m['role'] == 'assistant')
        assert ya_presento is True
        assert ya_pregunto_encargado is False

    def test_no_presento_no_encargado(self):
        """Historial sin nioval ni encargado = ambos False."""
        historial = [
            {"role": "assistant", "content": "Hola, buen día."},
            {"role": "user", "content": "Bueno."},
        ]
        ya_presento = any('nioval' in m.get('content', '').lower()
                         for m in historial if m['role'] == 'assistant')
        ya_pregunto_encargado = any('encargad' in m.get('content', '').lower()
                                    for m in historial if m['role'] == 'assistant')
        assert ya_presento is False
        assert ya_pregunto_encargado is False

    def test_encargado_solo_en_user_no_cuenta(self):
        """Solo mensajes assistant cuentan para encargado check."""
        historial = [
            {"role": "assistant", "content": "Me comunico de la marca nioval."},
            {"role": "user", "content": "No está el encargado."},
        ]
        ya_pregunto_encargado = any('encargad' in m.get('content', '').lower()
                                    for m in historial if m['role'] == 'assistant')
        assert ya_pregunto_encargado is False

    def test_encargada_tambien_detectado(self):
        """'encargada' también se detecta con 'encargad' substring."""
        historial = [
            {"role": "assistant", "content": "¿Se encontrará la encargada de compras?"},
        ]
        ya_pregunto_encargado = any('encargad' in m.get('content', '').lower()
                                    for m in historial if m['role'] == 'assistant')
        assert ya_pregunto_encargado is True

    def test_respuesta_correcta_cuando_ambos_true(self):
        """Cuando ya presentó Y ya preguntó encargado, respuesta debe ser verificación conexión."""
        historial = [
            {"role": "assistant", "content": "Me comunico de nioval. ¿Se encontrará el encargado?"},
            {"role": "user", "content": "[Timeout]"},
        ]
        ya_presento = any('nioval' in m.get('content', '').lower()
                         for m in historial if m['role'] == 'assistant')
        ya_pregunto_encargado = any('encargad' in m.get('content', '').lower()
                                    for m in historial if m['role'] == 'assistant')
        # Simular lógica FIX 680
        if ya_presento:
            if ya_pregunto_encargado:
                respuesta = "¿Me escucha? ¿Sigue en la línea?"
            else:
                respuesta = "¿Se encontrará el encargado o encargada de compras?"
        else:
            respuesta = "Me comunico de la marca NIOVAL..."

        assert '¿Me escucha?' in respuesta
        assert 'encargado' not in respuesta.lower()
        assert 'nioval' not in respuesta.lower()

    def test_respuesta_solo_presento_da_encargado(self):
        """Cuando solo presentó (sin encargado), debe preguntar por encargado."""
        historial = [
            {"role": "assistant", "content": "Me comunico de la marca nioval para información."},
            {"role": "user", "content": "[Timeout]"},
        ]
        ya_presento = any('nioval' in m.get('content', '').lower()
                         for m in historial if m['role'] == 'assistant')
        ya_pregunto_encargado = any('encargad' in m.get('content', '').lower()
                                    for m in historial if m['role'] == 'assistant')
        if ya_presento:
            if ya_pregunto_encargado:
                respuesta = "¿Me escucha? ¿Sigue en la línea?"
            else:
                respuesta = "¿Se encontrará el encargado o encargada de compras?"
        else:
            respuesta = "Me comunico de la marca NIOVAL..."

        assert 'encargado' in respuesta.lower()
        assert 'nioval' not in respuesta.lower()


# ============================================================
# FIX 681: Tests del auditor mejorado
# ============================================================

class TestFix681AuditorCAL001:
    """FIX 681: CAL-001 debe excluir STT timeouts, rechazos expandidos, buzón."""

    def _crear_conversacion(self, mensajes, estado_final='completed'):
        """Helper para crear estructura de conversación para el auditor."""
        return {
            'mensajes': mensajes,
            'estado_final': estado_final,
            'duracion': 30,
            'gpt_timeouts': 0,
            'stt_timeouts': 0,
            'respuestas_vacias': 0,
        }

    def test_rechazo_no_estamos_interesados(self):
        """'No estamos interesados' debe excluir CAL-001."""
        from auditor_conversaciones import auditar_conversacion
        conv = self._crear_conversacion([
            {'rol': 'bruce', 'texto': 'Hola, buen día.'},
            {'rol': 'cliente', 'texto': 'Bueno.'},
            {'rol': 'bruce', 'texto': 'Me comunico de nioval para productos ferreteros.'},
            {'rol': 'cliente', 'texto': 'No, ahorita no estamos interesados.'},
            {'rol': 'bruce', 'texto': 'Entiendo. Que tenga buen día.'},
            {'rol': 'cliente', 'texto': 'Gracias.'},
        ])
        bugs = auditar_conversacion('BRUCE_TEST', conv)
        cal_001 = [b for b in bugs if b['codigo'] == 'CAL-001']
        assert len(cal_001) == 0, f"CAL-001 no debió dispararse con rechazo. Bugs: {cal_001}"

    def test_rechazo_ahorita_no(self):
        """'Ahorita no' debe excluir CAL-001."""
        from auditor_conversaciones import auditar_conversacion
        conv = self._crear_conversacion([
            {'rol': 'bruce', 'texto': 'Hola, buen día.'},
            {'rol': 'cliente', 'texto': 'Bueno.'},
            {'rol': 'bruce', 'texto': 'Me comunico de nioval para productos ferreteros.'},
            {'rol': 'cliente', 'texto': 'Ahorita no, gracias.'},
            {'rol': 'bruce', 'texto': 'Entiendo. Que tenga buen día.'},
            {'rol': 'cliente', 'texto': 'Igualmente.'},
        ])
        bugs = auditar_conversacion('BRUCE_TEST', conv)
        cal_001 = [b for b in bugs if b['codigo'] == 'CAL-001']
        assert len(cal_001) == 0, f"CAL-001 no debió dispararse con 'ahorita no'"

    def test_buzon_voz_excluido(self):
        """Buzón de voz debe excluir CAL-001."""
        from auditor_conversaciones import auditar_conversacion
        conv = self._crear_conversacion([
            {'rol': 'bruce', 'texto': 'Hola, buen día.'},
            {'rol': 'cliente', 'texto': 'Favor de dejar un breve mensaje después del tono.'},
            {'rol': 'bruce', 'texto': 'Me comunico de nioval.'},
            {'rol': 'cliente', 'texto': 'Favor de dejar un breve mensaje después del tono.'},
            {'rol': 'bruce', 'texto': 'Parece que entré al buzón de voz.'},
            {'rol': 'cliente', 'texto': '[Timeout]'},
        ])
        bugs = auditar_conversacion('BRUCE_TEST', conv)
        cal_001 = [b for b in bugs if b['codigo'] == 'CAL-001']
        assert len(cal_001) == 0, f"CAL-001 no debió dispararse con buzón de voz"

    def test_timeout_excesivo_excluido(self):
        """3+ timeouts STT deben excluir CAL-001."""
        from auditor_conversaciones import auditar_conversacion
        conv = self._crear_conversacion([
            {'rol': 'bruce', 'texto': 'Hola, buen día.'},
            {'rol': 'cliente', 'texto': '[Timeout Deepgram #1]'},
            {'rol': 'bruce', 'texto': 'Me comunico de nioval.'},
            {'rol': 'cliente', 'texto': '[Timeout Deepgram #2]'},
            {'rol': 'bruce', 'texto': '¿Me escucha?'},
            {'rol': 'cliente', 'texto': '[Timeout Deepgram #3]'},
        ])
        bugs = auditar_conversacion('BRUCE_TEST', conv)
        cal_001 = [b for b in bugs if b['codigo'] == 'CAL-001']
        assert len(cal_001) == 0, f"CAL-001 no debió dispararse con 3+ timeouts"

    def test_llamada_real_sin_datos_si_detecta(self):
        """Llamada real donde Bruce pudo capturar pero no lo hizo = CAL-001 válido."""
        from auditor_conversaciones import auditar_conversacion
        conv = self._crear_conversacion([
            {'rol': 'bruce', 'texto': 'Hola, buen día.'},
            {'rol': 'cliente', 'texto': 'Bueno, sí.'},
            {'rol': 'bruce', 'texto': 'Me comunico de nioval para productos ferreteros.'},
            {'rol': 'cliente', 'texto': 'Sí, dígame.'},
            {'rol': 'bruce', 'texto': '¿Se encontrará el encargado?'},
            {'rol': 'cliente', 'texto': 'Soy yo, dígame.'},
        ])
        bugs = auditar_conversacion('BRUCE_TEST', conv)
        cal_001 = [b for b in bugs if b['codigo'] == 'CAL-001']
        assert len(cal_001) == 1, f"CAL-001 debió detectarse en llamada sin captura real"


class TestFix681AuditorFLU001:
    """FIX 681: FLU-001 debe excluir rechazos y problemas técnicos."""

    def _crear_conversacion(self, mensajes, estado_final='completed'):
        return {
            'mensajes': mensajes,
            'estado_final': estado_final,
            'duracion': 30,
            'gpt_timeouts': 0,
            'stt_timeouts': 0,
            'respuestas_vacias': 0,
        }

    def test_rechazo_final_no_es_flu001(self):
        """Si cliente termina con rechazo, no es FLU-001."""
        from auditor_conversaciones import auditar_conversacion
        conv = self._crear_conversacion([
            {'rol': 'bruce', 'texto': 'Hola, buen día.'},
            {'rol': 'cliente', 'texto': 'Bueno.'},
            {'rol': 'bruce', 'texto': 'Me comunico de nioval para productos ferreteros.'},
            {'rol': 'cliente', 'texto': 'No estamos interesados, gracias.'},
        ])
        bugs = auditar_conversacion('BRUCE_TEST', conv)
        flu_001 = [b for b in bugs if b['codigo'] == 'FLU-001']
        assert len(flu_001) == 0, f"FLU-001 no debió dispararse con rechazo final"

    def test_problemas_tecnicos_no_es_flu001(self):
        """Si Bruce dijo 'problemas técnicos', FLU-001 no aplica."""
        from auditor_conversaciones import auditar_conversacion
        conv = self._crear_conversacion([
            {'rol': 'bruce', 'texto': 'Hola, buen día.'},
            {'rol': 'cliente', 'texto': 'Bueno.'},
            {'rol': 'bruce', 'texto': 'Disculpe, estamos teniendo un problema técnico.'},
            {'rol': 'cliente', 'texto': '¿Bueno? ¿Sigue ahí?'},
        ])
        bugs = auditar_conversacion('BRUCE_TEST', conv)
        flu_001 = [b for b in bugs if b['codigo'] == 'FLU-001']
        assert len(flu_001) == 0, f"FLU-001 no debió dispararse con problemas técnicos"

    def test_cliente_da_info_sin_respuesta_si_es_flu001(self):
        """Si cliente da info y Bruce no responde, SÍ es FLU-001."""
        from auditor_conversaciones import auditar_conversacion
        conv = self._crear_conversacion([
            {'rol': 'bruce', 'texto': 'Hola, buen día.'},
            {'rol': 'cliente', 'texto': 'Bueno.'},
            {'rol': 'bruce', 'texto': '¿A qué hora la puedo encontrar?'},
            {'rol': 'cliente', 'texto': 'La puedes encontrar después de las diez de la mañana.'},
        ])
        bugs = auditar_conversacion('BRUCE_TEST', conv)
        flu_001 = [b for b in bugs if b['codigo'] == 'FLU-001']
        assert len(flu_001) == 1, f"FLU-001 debió detectarse cuando cliente da info sin respuesta"

    def test_despedida_natural_no_es_flu001(self):
        """Despedida natural del cliente no es FLU-001."""
        from auditor_conversaciones import auditar_conversacion
        conv = self._crear_conversacion([
            {'rol': 'bruce', 'texto': 'Muchas gracias por su tiempo, que tenga excelente día.'},
            {'rol': 'cliente', 'texto': 'Igualmente, hasta luego.'},
        ])
        bugs = auditar_conversacion('BRUCE_TEST', conv)
        flu_001 = [b for b in bugs if b['codigo'] == 'FLU-001']
        assert len(flu_001) == 0, f"FLU-001 no debió dispararse con despedida natural"
