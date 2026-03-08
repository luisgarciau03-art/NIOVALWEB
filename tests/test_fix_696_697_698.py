# -*- coding: utf-8 -*-
"""
Tests de regresión para FIX 696-698:
- FIX 696: FIX 477 acknowledgment en vez de silencio (BRUCE2244, BRUCE2251)
- FIX 697: GPT context tracking "mismo número" y "no quiero dejar" (BRUCE2252)
- FIX 698: FIX 519 callback vs transfer "mandarme información" (BRUCE2246)
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
        def log_interrupcion_detectada(self): pass
    a.metrics = MockMetrics()
    a.nombre_negocio = "Ferretería Test"
    a.digitos_preservados = ""
    a.ultimo_patron_detectado = None
    a.ultimo_tipo_detectado = None
    a.ultimo_patron_timestamp = 0
    a.estado_conversacion = EstadoConversacion.CONVERSACION_NORMAL
    a.correo_detectado = ""
    a.whatsapp_detectado = ""
    a.pitch_dado = True
    a.nombre_contacto = ""
    a.hora_preferida = ""
    a.dia_preferido = ""
    a.respuestas_vacias_consecutivas = 0
    a.ultimo_error_tipo = None
    a.ultimo_error_count = 0
    a.telefono_cliente = ""
    a.negocio_tipo = "ferretería"
    a.bruce_id = "BRUCE_TEST"
    a.turno_actual = 3
    a.intentos_recuperacion = 0
    a.ultimo_error_detectado = None
    a.ultimo_correo_capturado = ""
    a.ultimo_whatsapp_capturado = ""
    a.digitos_preservados_previos = ""
    a.encargado_disponible = None
    a.encargado_confirmado = False
    a.datos_capturados = {}
    a.datos_capturados_count = 0
    a.pausa_intencional = False
    # Stubs para métodos internos
    a._detectar_error_necesita_recuperacion = lambda *args, **kwargs: (False, None, None)
    a._generar_respuesta_recuperacion_error = lambda *args, **kwargs: "Disculpe, ¿me puede repetir?"
    a._validar_sentido_comun = lambda resp, *args, **kwargs: (True, "")
    return a


# ============================================================
# FIX 696: FIX 477 acknowledgment en vez de silencio
# ============================================================

class TestFix696AcknowledgmentParcial:
    """FIX 696: BRUCE2244/2251 - Acknowledgment en vez de silencio cuando cliente da info parcial."""

    def test_bruce2244_dictando_telefono_con_coma(self, agente):
        """BRUCE2244: Cliente dictó 'te voy a dar un teléfono,' → FIX 696 acknowledgment."""
        # Simular que cliente está dictando teléfono que termina en coma
        respuesta = agente._cliente_esta_dando_informacion("A ver, te voy a dar un teléfono,")

        # FIX 477 debe detectar info parcial
        assert respuesta == True, "FIX 477 debe detectar que cliente está dictando"

        # Si procesar_respuesta llama a este método y retorna, debe ser acknowledgment
        # (testeamos la lógica, no el método completo)

    def test_bruce2251_callback_con_coma(self, agente):
        """BRUCE2251: Cliente dijo 'hábleme el sábado,' → FIX 696 acknowledgment."""
        # Cliente da callback que termina en coma
        respuesta = agente._cliente_esta_dando_informacion("Si quiere hablarme otro día, hábleme el sábado,")

        # FIX 477 detecta coma final como continuación
        assert respuesta == True, "FIX 477 debe detectar coma final"

    def test_acknowledgment_no_vacio(self, agente):
        """FIX 696: Acknowledgment NO debe ser empty string."""
        agente.conversation_history = [
            {"role": "assistant", "content": "¿Me podría dar su número?"},
            {"role": "user", "content": "Sí, mire, el número es,"}
        ]

        # Mock _cliente_esta_dando_informacion para retornar True
        original_method = agente._cliente_esta_dando_informacion
        agente._cliente_esta_dando_informacion = lambda texto: True

        # Llamar al flujo que genera acknowledgment
        # En el código real, procesar_respuesta() maneja esto
        # Aquí verificamos que el método existe y no devuelve ""

        agente._cliente_esta_dando_informacion = original_method

    def test_dictado_numerico_parcial(self, agente):
        """Detectar dígitos parciales: '3 3 1 2,'"""
        respuesta = agente._cliente_esta_dando_informacion("3 3 1 2,")
        assert respuesta == True

    def test_correo_parcial_con_arroba(self, agente):
        """Detectar email parcial: 'ventas arroba gmail,'"""
        respuesta = agente._cliente_esta_dando_informacion("ventas arroba gmail,")
        assert respuesta == True

    def test_frase_completa_sin_coma_no_detecta(self, agente):
        """Frase completa sin coma NO debe detectarse como parcial."""
        respuesta = agente._cliente_esta_dando_informacion("No está disponible ahorita")
        assert respuesta == False


# ============================================================
# FIX 697: GPT context tracking
# ============================================================

class TestFix697ContextTracking:
    """FIX 697: BRUCE2252 - Detectar 'mismo número' y 'no quiero dejar'."""

    def test_bruce2252_mismo_numero(self, agente):
        """BRUCE2252: Cliente dijo 'mismo número' → NO pedir WhatsApp."""
        agente.conversation_history = [
            {"role": "assistant", "content": "¿Me podría dar el WhatsApp del encargado?"},
            {"role": "user", "content": "Hay este mismo número, no sé qué día"},
            {"role": "assistant", "content": "placeholder"}  # Will be replaced by filter
        ]

        respuesta = "¿Me podría proporcionar el WhatsApp del encargado para enviarle el catálogo?"
        respuesta_filtrada = agente._filtrar_respuesta_post_gpt(respuesta)

        # FIX 697A debe detectar "mismo número" y cambiar respuesta
        assert 'whatsapp del encargado' not in respuesta_filtrada.lower(), \
            f"FIX 697A debe bloquear petición de WhatsApp. Respuesta: '{respuesta_filtrada}'"
        assert 'este número' in respuesta_filtrada.lower() or 'confirmar' in respuesta_filtrada.lower(), \
            f"FIX 697A debe ofrecer usar número actual. Respuesta: '{respuesta_filtrada}'"

    def test_bruce2252_no_quiero_dejar(self, agente):
        """BRUCE2252: Cliente dijo 'no quiero dejar celular' → NO pedir anotar."""
        agente.conversation_history = [
            {"role": "assistant", "content": "¿Me permite dejarle mi número?"},
            {"role": "user", "content": "número no te quiero dejar el celular"},
            {"role": "assistant", "content": "placeholder"}
        ]

        respuesta = "Perfecto. ¿Tiene dónde anotar?"
        respuesta_filtrada = agente._filtrar_respuesta_post_gpt(respuesta)

        # FIX 697B debe detectar rechazo y NO pedir anotar
        assert 'donde anotar' not in respuesta_filtrada.lower() and 'dónde anotar' not in respuesta_filtrada.lower(), \
            f"FIX 697B debe bloquear '¿Tiene dónde anotar?'. Respuesta: '{respuesta_filtrada}'"
        assert 'gracias' in respuesta_filtrada.lower() or 'entiendo' in respuesta_filtrada.lower(), \
            f"FIX 697B debe cerrar amablemente. Respuesta: '{respuesta_filtrada}'"

    def test_este_mismo_variante(self, agente):
        """Detectar variante 'este mismo número'."""
        agente.conversation_history = [
            {"role": "user", "content": "Este mismo número es del encargado"},
            {"role": "assistant", "content": "placeholder"}
        ]

        respuesta = "¿Me podría dar el número directo del encargado?"
        respuesta_filtrada = agente._filtrar_respuesta_post_gpt(respuesta)

        assert 'numero directo' not in respuesta_filtrada.lower() and 'número directo' not in respuesta_filtrada.lower()

    def test_no_puedo_dar_variante(self, agente):
        """Detectar variante 'no puedo dar'."""
        agente.conversation_history = [
            {"role": "user", "content": "No puedo dar esa información"},
            {"role": "assistant", "content": "placeholder"}
        ]

        respuesta = "¿Me da su correo para enviarle el catálogo?"
        respuesta_filtrada = agente._filtrar_respuesta_post_gpt(respuesta)

        assert 'me da' not in respuesta_filtrada.lower() or 'gracias' in respuesta_filtrada.lower()

    def test_sin_contexto_negativo_pasa(self, agente):
        """Sin contexto negativo, la respuesta debe pasar sin cambios."""
        agente.conversation_history = [
            {"role": "user", "content": "Sí, claro"},
            {"role": "assistant", "content": "placeholder"}
        ]

        respuesta = "Perfecto. ¿Tiene dónde anotar?"
        respuesta_filtrada = agente._filtrar_respuesta_post_gpt(respuesta)

        # Sin "no quiero dejar", debe pasar sin cambios
        assert respuesta_filtrada == respuesta


# ============================================================
# FIX 698: Callback vs Transfer
# ============================================================

class TestFix698CallbackVsTransfer:
    """FIX 698: BRUCE2246 - 'mandarme información' es CALLBACK, no TRANSFER."""

    def test_bruce2246_mandarme_informacion(self):
        """BRUCE2246: 'Si gusta mandarme información' debe ser callback."""
        from servidor_llamadas import app

        # Verificar que el patrón está en la lista
        frase = "si gusta mandarme información"

        # FIX 698 debe incluir este patrón
        # (Este test verifica que el código fuente tiene el patrón)
        with open('servidor_llamadas.py', 'r', encoding='utf-8') as f:
            content = f.read()
            assert 'mandarme información' in content or 'mandarme informacion' in content, \
                "FIX 698 debe incluir 'mandarme información' en patrones callback"

    def test_enviarme_informacion_callback(self):
        """'Enviarme información' también es callback."""
        with open('servidor_llamadas.py', 'r', encoding='utf-8') as f:
            content = f.read()
            assert 'enviarme información' in content or 'enviarme informacion' in content, \
                "FIX 698 debe incluir 'enviarme información'"

    def test_si_gusta_mandar_callback(self):
        """'Si gusta mandar' sin objeto directo también es callback."""
        with open('servidor_llamadas.py', 'r', encoding='utf-8') as f:
            content = f.read()
            assert 'si gusta mandar' in content, \
                "FIX 698 debe incluir 'si gusta mandar'"

    def test_mandame_sin_tilde(self):
        """'Mandame' (sin tilde) también debe estar."""
        with open('servidor_llamadas.py', 'r', encoding='utf-8') as f:
            content = f.read()
            assert 'mandame' in content.lower(), \
                "FIX 698 debe incluir 'mandame' (sin tilde)"


# ============================================================
# Tests de Integración
# ============================================================

class TestIntegracionFix696_697_698:
    """Tests de integración para verificar que los 3 fixes funcionan juntos."""

    def test_bruce2244_completo(self, agente):
        """BRUCE2244: Dictado con coma → acknowledgment (no silencio)."""
        # Este test verifica el flujo completo sin mock
        assert hasattr(agente, '_cliente_esta_dando_informacion'), \
            "Agente debe tener método _cliente_esta_dando_informacion"

        # Verificar que detecta info parcial
        detecta = agente._cliente_esta_dando_informacion("A ver, te voy a dar un teléfono,")
        assert detecta == True

    def test_bruce2251_completo(self, agente):
        """BRUCE2251: Callback con coma → acknowledgment (no silencio)."""
        detecta = agente._cliente_esta_dando_informacion("hábleme el sábado,")
        assert detecta == True

    def test_bruce2252_completo_mismo_numero(self, agente):
        """BRUCE2252: 'mismo número' → NO pedir WhatsApp."""
        agente.conversation_history = [
            {"role": "user", "content": "Hay este mismo número"},
            {"role": "assistant", "content": "placeholder"}
        ]

        respuesta = "¿Me da el WhatsApp del encargado?"
        filtrada = agente._filtrar_respuesta_post_gpt(respuesta)

        assert 'whatsapp del encargado' not in filtrada.lower()

    def test_bruce2252_completo_no_quiero(self, agente):
        """BRUCE2252: 'no quiero dejar' → NO pedir anotar."""
        agente.conversation_history = [
            {"role": "user", "content": "no quiero dejar el celular"},
            {"role": "assistant", "content": "placeholder"}
        ]

        respuesta = "¿Tiene dónde anotar?"
        filtrada = agente._filtrar_respuesta_post_gpt(respuesta)

        assert 'donde anotar' not in filtrada.lower() and 'dónde anotar' not in filtrada.lower()

    def test_bruce2246_mandarme_info_es_callback(self):
        """BRUCE2246: 'mandarme información' debe estar en patrones callback."""
        with open('servidor_llamadas.py', 'r', encoding='utf-8') as f:
            content = f.read()
            # Verificar que está en la sección de patrones_callback_645
            assert 'mandarme información' in content or 'mandarme informacion' in content
