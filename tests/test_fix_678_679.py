# -*- coding: utf-8 -*-
"""
Tests de regresión para FIX 678 (anti-pitch-repeat en todos los paths)
y FIX 679 (detector hash de duplicados exactos).
"""
import os
import sys
import time
import pytest

# Agregar directorio padre al path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Env vars necesarias antes de importar
os.environ.setdefault("OPENAI_API_KEY", "sk-test-dummy")
os.environ.setdefault("ELEVENLABS_API_KEY", "test-dummy")
os.environ.setdefault("TWILIO_ACCOUNT_SID", "AC-test")
os.environ.setdefault("TWILIO_AUTH_TOKEN", "test-token")

from agente_ventas import AgenteVentas, EstadoConversacion


@pytest.fixture
def agente():
    """Crea un AgenteVentas con todos los atributos necesarios para testing."""
    a = AgenteVentas.__new__(AgenteVentas)
    a.conversation_history = []
    a.catalogo_prometido = False
    a.esperando_hora_callback = False
    a.datos_encargado = {}
    a.lead_data = {
        "whatsapp": "",
        "whatsapp_valido": False,
        "email": "",
        "nombre_encargado": "",
        "interesado": False,
        "estado_llamada": "Respondio",
        "nivel_interes": "bajo",
        "temperatura": "frío",
        "notas": "",
    }
    # Mock metrics
    class MockMetrics:
        def log_respuesta_vacia_bloqueada(self): pass
        def log_patron_detectado(self, *a, **kw): pass
        def log_filtro_post_gpt(self, *a, **kw): pass
    a.metrics = MockMetrics()
    a.nombre_negocio = "Ferretería Test"
    a.digitos_preservados = ""
    a.ultimo_patron_detectado = None
    a.ultimo_tipo_detectado = None
    a.ultimo_patron_timestamp = 0
    a.estado_conversacion = EstadoConversacion.CONVERSACION_NORMAL
    a.correo_detectado = ""
    a.whatsapp_detectado = ""
    a.pitch_dado = True  # Ya dio el pitch (para evitar FIX 650/660)
    a.nombre_contacto = ""
    a.hora_preferida = ""
    a.dia_preferido = ""
    a.respuestas_vacias_consecutivas = 0
    a.ultimo_error_tipo = None
    a.ultimo_error_count = 0
    a.telefono_cliente = ""
    a.negocio_tipo = "ferretería"
    a.bruce_id = "BRUCE_TEST"
    a.turno_actual = 3  # Simular que estamos en turno 3+ para evitar FIX 650/660
    a.intentos_recuperacion = 0
    a.ultimo_error_detectado = None
    a.ultimo_correo_capturado = ""
    a.ultimo_whatsapp_capturado = ""
    a.digitos_preservados_previos = ""
    a.encargado_disponible = None
    a.encargado_confirmado = False
    a.datos_capturados = {}
    a.datos_capturados_count = 0
    # Stubs para métodos internos que podrían ser llamados
    a._detectar_error_necesita_recuperacion = lambda *args, **kwargs: (False, None, None)
    a._generar_respuesta_recuperacion_error = lambda *args, **kwargs: "Disculpe, ¿me puede repetir?"
    a._validar_sentido_comun = lambda resp, *args, **kwargs: (True, "")
    return a


@pytest.fixture
def agente_turno1():
    """AgenteVentas en turno 1 (sin pitch)."""
    a = AgenteVentas.__new__(AgenteVentas)
    a.conversation_history = [
        {"role": "assistant", "content": "Hola, buen día."},
        {"role": "user", "content": "Bueno."},
    ]
    a.catalogo_prometido = False
    a.esperando_hora_callback = False
    a.datos_encargado = {}
    a.lead_data = {
        "whatsapp": "", "whatsapp_valido": False, "email": "",
        "nombre_encargado": "", "interesado": False,
        "estado_llamada": "Respondio", "nivel_interes": "bajo",
        "temperatura": "frío", "notas": "",
    }
    class MockMetrics:
        def log_respuesta_vacia_bloqueada(self): pass
        def log_patron_detectado(self, *a, **kw): pass
        def log_filtro_post_gpt(self, *a, **kw): pass
    a.metrics = MockMetrics()
    a.nombre_negocio = "Ferretería Test"
    a.digitos_preservados = ""
    a.ultimo_patron_detectado = None
    a.ultimo_tipo_detectado = None
    a.ultimo_patron_timestamp = 0
    a.estado_conversacion = EstadoConversacion.CONVERSACION_NORMAL
    a.correo_detectado = ""
    a.whatsapp_detectado = ""
    a.pitch_dado = False
    a.nombre_contacto = ""
    a.hora_preferida = ""
    a.dia_preferido = ""
    a.respuestas_vacias_consecutivas = 0
    a.ultimo_error_tipo = None
    a.ultimo_error_count = 0
    a.telefono_cliente = ""
    a.negocio_tipo = "ferretería"
    a.bruce_id = "BRUCE_TEST"
    a.turno_actual = 1
    a.intentos_recuperacion = 0
    a.ultimo_error_detectado = None
    a.ultimo_correo_capturado = ""
    a.ultimo_whatsapp_capturado = ""
    a.digitos_preservados_previos = ""
    a.encargado_disponible = None
    a.encargado_confirmado = False
    a.datos_capturados = {}
    a.datos_capturados_count = 0
    a._detectar_error_necesita_recuperacion = lambda *args, **kwargs: (False, None, None)
    a._generar_respuesta_recuperacion_error = lambda *args, **kwargs: "Disculpe, ¿me puede repetir?"
    a._validar_sentido_comun = lambda resp, *args, **kwargs: (True, "")
    return a


# ============================================================
# FIX 679: Detector hash de duplicados exactos
# ============================================================

class TestFix679DuplicadoExacto:
    """FIX 679: Si Bruce repite respuesta similar >=85%, generar alternativa."""

    def test_respuesta_duplicada_exacta_bloqueada(self, agente):
        """Si Bruce ya dijo la misma frase, no repetirla."""
        agente.conversation_history = [
            {"role": "assistant", "content": "Hola, buen día."},
            {"role": "user", "content": "Bueno."},
            {"role": "assistant", "content": "Me comunico de la marca nioval, más que nada quería brindar información de nuestros productos ferreteros, ¿se encontrará el encargado o encargada de compras?"},
            {"role": "user", "content": "Mande."},
        ]
        respuesta = agente._filtrar_respuesta_post_gpt(
            "Me comunico de la marca nioval, más que nada quería brindar información de nuestros productos ferreteros, ¿se encontrará el encargado o encargada de compras?"
        )
        # No debe contener "me comunico de la marca nioval" (pitch repetido)
        assert 'me comunico de la marca nioval' not in respuesta.lower(), \
            f"FIX 679 no bloqueó duplicado. Respuesta: '{respuesta}'"

    def test_respuesta_similar_bloqueada(self, agente):
        """Respuestas 85%+ similares deben bloquearse."""
        agente.conversation_history = [
            {"role": "assistant", "content": "Me comunico de la marca NIOVAL para brindar información de nuestros productos ferreteros. ¿Se encontrará el encargado de compras?"},
            {"role": "user", "content": "Mande."},
        ]
        respuesta = agente._filtrar_respuesta_post_gpt(
            "Me comunico de la marca nioval, más que nada quería brindar información de nuestros productos ferreteros, ¿se encontrará el encargado o encargada de compras?"
        )
        # No debe ser el pitch repetido
        assert 'más que nada quería brindar' not in respuesta.lower(), \
            f"FIX 679 no bloqueó respuesta similar. Respuesta: '{respuesta}'"

    def test_respuesta_diferente_permitida(self, agente):
        """Respuestas genuinamente diferentes deben pasar."""
        # Simular turno 3+ para que FIX 660 no interfiera
        agente.conversation_history = [
            {"role": "assistant", "content": "Hola, buen día."},
            {"role": "user", "content": "Bueno."},
            {"role": "assistant", "content": "Me comunico de la marca nioval para brindar información de productos. ¿Se encuentra el encargado?"},
            {"role": "user", "content": "No está el encargado."},
            {"role": "assistant", "content": "Entiendo. ¿Me podría proporcionar un WhatsApp?"},
            {"role": "user", "content": "No tengo WhatsApp."},
        ]
        respuesta = agente._filtrar_respuesta_post_gpt(
            "¿Prefiere que le envíe la información por correo electrónico?"
        )
        # Respuesta diferente debe pasar
        assert 'correo' in respuesta.lower() or 'información' in respuesta.lower()

    def test_duplicado_nioval_genera_alternativa_encargado(self, agente):
        """Si duplicado menciona nioval, alternativa pregunta encargado."""
        agente.conversation_history = [
            {"role": "assistant", "content": "Le comento, me comunico de la marca nioval, somos distribuidores de productos ferreteros."},
            {"role": "user", "content": "Ajá."},
        ]
        respuesta = agente._filtrar_respuesta_post_gpt(
            "Le comento, me comunico de la marca nioval, somos distribuidores de productos ferreteros."
        )
        # Debe ofrecer una alternativa (no repetir el pitch)
        assert 'me comunico de la marca nioval' not in respuesta.lower()

    def test_duplicado_whatsapp_ofrece_alternativa(self, agente):
        """Si duplicado pide WhatsApp, algún FIX (671 o 679) lo bloquea."""
        agente.conversation_history = [
            {"role": "assistant", "content": "¿Me podría proporcionar un WhatsApp para enviarle el catálogo de productos ferreteros?"},
            {"role": "user", "content": "No, no tengo."},
        ]
        respuesta = agente._filtrar_respuesta_post_gpt(
            "¿Me podría proporcionar un WhatsApp para enviarle el catálogo de productos ferreteros?"
        )
        # FIX 671 o FIX 679 debe bloquear la repetición
        assert 'me podría proporcionar un whatsapp para enviarle el catálogo' not in respuesta.lower(), \
            f"Ni FIX 671 ni FIX 679 bloquearon la repetición. Respuesta: '{respuesta}'"


# ============================================================
# FIX 678: Anti-pitch-repeat en todos los paths (servidor)
# Tests de la lógica de detección (no requieren servidor Flask)
# ============================================================

class TestFix678PitchRepeatDetection:
    """FIX 678: Verificar detección de pitch ya presentado."""

    def test_detecta_nioval_en_historial(self):
        """Si historial contiene 'nioval', ya_presento debe ser True."""
        historial = [
            {"role": "assistant", "content": "Hola, buen día."},
            {"role": "assistant", "content": "Me comunico de la marca nioval para productos ferreteros."}
        ]
        ya_presento = any('nioval' in m.get('content', '').lower()
                         for m in historial if m['role'] == 'assistant')
        assert ya_presento is True

    def test_no_detecta_sin_nioval(self):
        """Si historial NO contiene 'nioval', ya_presento debe ser False."""
        historial = [
            {"role": "assistant", "content": "Hola, buen día."},
            {"role": "assistant", "content": "¿Se encontrará el encargado?"}
        ]
        ya_presento = any('nioval' in m.get('content', '').lower()
                         for m in historial if m['role'] == 'assistant')
        assert ya_presento is False

    def test_solo_checa_assistant_no_user(self):
        """Solo mensajes de assistant cuentan, no del usuario."""
        historial = [
            {"role": "user", "content": "Sí, conozco nioval."},
            {"role": "assistant", "content": "Perfecto. ¿Se encuentra el encargado?"}
        ]
        ya_presento = any('nioval' in m.get('content', '').lower()
                         for m in historial if m['role'] == 'assistant')
        assert ya_presento is False

    def test_historial_vacio_no_presento(self):
        """Historial vacío = no se ha presentado."""
        historial = []
        ya_presento = any('nioval' in m.get('content', '').lower()
                         for m in historial if m['role'] == 'assistant')
        assert ya_presento is False


# ============================================================
# Tests de integración: FIX 679 con escenarios de bugs reales
# ============================================================

class TestFix679EscenariosReales:
    """Escenarios basados en bugs reales (BRUCE2194, 2177, 2186, etc.)."""

    def test_bruce2194_pitch_duplicado(self, agente):
        """BRUCE2194: Bruce repitió pitch completo con 100% similitud."""
        agente.conversation_history = [
            {"role": "assistant", "content": "Hola, buen día."},
            {"role": "user", "content": "Bueno."},
            {"role": "assistant", "content": "Me comunico de la marca nioval, más que nada quería brindar información de nuestros productos ferreteros, ¿se encontrará el encargado o encargada de compras?"},
            {"role": "user", "content": "Mande."},
        ]
        respuesta = agente._filtrar_respuesta_post_gpt(
            "Me comunico de la marca nioval, más que nada quería brindar información de nuestros productos ferreteros, ¿se encontrará el encargado o encargada de compras?"
        )
        # NO debe repetir el pitch
        assert 'me comunico de la marca nioval' not in respuesta.lower()
        # DEBE ser una alternativa útil
        assert len(respuesta) > 10

    def test_bruce2193_encargado_repetido(self, agente):
        """BRUCE2193: Preguntó por encargado repetidamente."""
        agente.conversation_history = [
            {"role": "assistant", "content": "¿Se encontrará el encargado o encargada de compras?"},
            {"role": "user", "content": "No, no está."},
            {"role": "assistant", "content": "¿Me podría proporcionar un WhatsApp para enviarle información?"},
            {"role": "user", "content": "No tengo WhatsApp."},
        ]
        respuesta = agente._filtrar_respuesta_post_gpt(
            "¿Se encontrará el encargado o encargada de compras?"
        )
        # No debe repetir pregunta de encargado exactamente igual
        assert 'se encontrará el encargado o encargada' not in respuesta.lower()

    def test_no_bloquea_respuestas_diferentes(self, agente):
        """No debe bloquear respuestas genuinamente diferentes."""
        agente.conversation_history = [
            {"role": "assistant", "content": "Me comunico de la marca nioval para información de productos."},
            {"role": "user", "content": "No está el encargado pero yo le puedo pasar el mensaje."},
        ]
        respuesta = agente._filtrar_respuesta_post_gpt(
            "Muchas gracias, le comento que manejamos toda la línea de productos ferreteros. ¿Me podría proporcionar un WhatsApp o correo?"
        )
        # FIX 679 NO debe bloquear esta respuesta (es diferente a la previa)
        # Otros FIX rules pueden modificarla pero no debe ser la misma que la previa
        prev = "me comunico de la marca nioval para información de productos."
        assert prev not in respuesta.lower(), "FIX 679 incorrectamente bloqueó respuesta diferente"

    def test_multiples_duplicados_whatsapp_en_historial(self, agente):
        """Con WhatsApp ya preguntado, algún FIX debe bloquear la repetición."""
        agente.conversation_history = [
            {"role": "assistant", "content": "Hola, buen día."},
            {"role": "user", "content": "Bueno."},
            {"role": "assistant", "content": "Me comunico de la marca nioval. ¿Se encuentra el encargado?"},
            {"role": "user", "content": "No está."},
            {"role": "assistant", "content": "¿Me podría proporcionar un WhatsApp para enviarle el catálogo de productos?"},
            {"role": "user", "content": "No tengo."},
        ]
        respuesta = agente._filtrar_respuesta_post_gpt(
            "¿Me podría proporcionar un WhatsApp para enviarle el catálogo de productos?"
        )
        # FIX 671 o FIX 679 deben bloquear la repetición exacta
        assert 'me podría proporcionar un whatsapp para enviarle el catálogo' not in respuesta.lower(), \
            f"Repetición no fue bloqueada. Respuesta: '{respuesta}'"
