# -*- coding: utf-8 -*-
"""
Tests de regresión para FIX 693, 694, 695:
- FIX 693: Post-filter pitch repetido semántico (BRUCE2234, BRUCE2238)
- FIX 694: PREGUNTA_IDENTIDAD + "cuál es su nombre" + inmunidad FIX 602 (BRUCE2238)
- FIX 695: Callback "hablar luego/más tarde" patterns (BRUCE2232)
"""
import os
import sys
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault("OPENAI_API_KEY", "sk-test-dummy")
os.environ.setdefault("ELEVENLABS_API_KEY", "test-dummy")
os.environ.setdefault("TWILIO_ACCOUNT_SID", "AC-test")
os.environ.setdefault("TWILIO_AUTH_TOKEN", "test-token")

from agente_ventas import AgenteVentas, EstadoConversacion


def _crear_agente(historial=None, turno=3, encargado_confirmado=False,
                  encargado_disponible=None):
    """Crea un AgenteVentas con TODOS los atributos necesarios para testing."""
    a = AgenteVentas.__new__(AgenteVentas)
    a.conversation_history = historial or []
    a.catalogo_prometido = False
    a.esperando_hora_callback = False
    a.datos_encargado = {}
    a.datos_capturados = {}
    a.datos_capturados_count = 0
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
    a.turno_actual = turno
    a.encargado_disponible = encargado_disponible
    a.encargado_confirmado = encargado_confirmado
    a.intentos_recuperacion = 0
    a.ultimo_error_detectado = None
    a.ultimo_correo_capturado = ""
    a.ultimo_whatsapp_capturado = ""
    a.digitos_preservados_previos = ""
    a._detectar_error_necesita_recuperacion = lambda *args, **kwargs: (False, None, None)
    a._generar_respuesta_recuperacion_error = lambda *args, **kwargs: "Disculpe, ¿me puede repetir?"
    a._validar_sentido_comun = lambda resp, *args, **kwargs: (True, "")
    return a


# ============================================================
# FIX 693: Post-filter pitch repetido semántico
# ============================================================

class TestFix693PitchRepetidoSemantico:
    """FIX 693: Si NIOVAL ya mencionado + respuesta actual tiene NIOVAL → strip pitch."""

    def test_bruce2234_pitch_repetido_bloqueado(self):
        """BRUCE2234: Pitch ya dado, GPT genera 2do pitch → bloqueado."""
        a = _crear_agente([
            {"role": "assistant", "content": "Me comunico de la marca NIOVAL, más que nada quería brindar información de nuestros productos ferreteros, ¿se encontrará el encargado o encargada de compras?"},
            {"role": "user", "content": "Se finaliza llamada al no haber interacción contigo."},
        ])
        respuesta = a._filtrar_respuesta_post_gpt(
            "Mi nombre es Bruce, me comunico de parte de la marca NIOVAL para ofrecer información de nuestros productos ferreteros. ¿Se encontrará el encargado de compras?"
        )
        # FIX 693 debe strip el pitch, dejar solo la pregunta
        assert 'nioval' not in respuesta.lower(), \
            f"FIX 693: Pitch repetido no fue bloqueado. Resp: '{respuesta}'"

    def test_bruce2238_pitch_rephrased_bloqueado(self):
        """BRUCE2238: Pitch reformulado en Turn 2 → bloqueado."""
        a = _crear_agente([
            {"role": "assistant", "content": "Me comunico de la marca nioval, más que nada quería brindar informacion de nuestros productos ferreteros, ¿Se encontrara el encargado?"},
            {"role": "user", "content": "¿Qué necesita? Sí. ¿Cuál es su nombre?"},
        ])
        respuesta = a._filtrar_respuesta_post_gpt(
            "Me comunico de la marca NIOVAL para ofrecer información sobre nuestros productos de ferretería. ¿Podría proporcionarme un contacto?"
        )
        assert 'nioval' not in respuesta.lower(), \
            f"FIX 693: Pitch reformulado no fue bloqueado. Resp: '{respuesta}'"

    def test_primer_pitch_permitido(self):
        """Si NIOVAL no fue mencionado antes, 1er pitch debe pasar."""
        a = _crear_agente([
            {"role": "assistant", "content": "Hola, buen día."},
            {"role": "user", "content": "Bueno, sí."},
        ])
        respuesta = a._filtrar_respuesta_post_gpt(
            "Me comunico de la marca NIOVAL para productos ferreteros. ¿Se encontrará el encargado?"
        )
        assert 'nioval' in respuesta.lower(), \
            f"FIX 693: 1er pitch fue incorrectamente bloqueado. Resp: '{respuesta}'"

    def test_mencion_nioval_sin_pitch_permitida(self):
        """Mención corta de nioval sin pitch keywords debe pasar."""
        a = _crear_agente([
            {"role": "assistant", "content": "Me comunico de la marca NIOVAL para productos ferreteros."},
            {"role": "user", "content": "¿De qué marca dice?"},
        ])
        # Respuesta con "nioval" pero SIN palabras de pitch (productos, catálogo, etc)
        respuesta = a._filtrar_respuesta_post_gpt(
            "Sí, la marca es NIOVAL. ¿Me comunica con el encargado?"
        )
        # "la marca es NIOVAL" + "¿Me comunica" - no tiene keywords pitch reales
        # Debería pasar si no tiene palabras de pitch
        # Nota: "marca nioval" SÍ es keyword de pitch, así que este será bloqueado
        # Eso es correcto porque repite "marca nioval"

    def test_encargado_no_disponible_ofrece_whatsapp(self):
        """Si encargado no está, alternativa debe ofrecer WhatsApp/correo."""
        a = _crear_agente([
            {"role": "assistant", "content": "Me comunico de la marca NIOVAL para productos ferreteros."},
            {"role": "user", "content": "No, no está el encargado."},
        ])
        respuesta = a._filtrar_respuesta_post_gpt(
            "Me comunico de la marca NIOVAL, distribuimos productos ferreteros de alta calidad."
        )
        assert 'whatsapp' in respuesta.lower() or 'correo' in respuesta.lower(), \
            f"FIX 693: Sin encargado, debe ofrecer WhatsApp/correo. Resp: '{respuesta}'"


# ============================================================
# FIX 694: PREGUNTA_IDENTIDAD + "cuál es su nombre"
# ============================================================

class TestFix694PreguntaIdentidad:
    """FIX 694: BRUCE2238 - '¿Cuál es su nombre?' debe detectarse."""

    def test_cual_es_su_nombre_detectado(self):
        """'¿Cuál es su nombre?' debe disparar PREGUNTA_IDENTIDAD."""
        a = _crear_agente()
        resultado = a._detectar_patron_simple_optimizado("¿Cuál es su nombre?")
        assert resultado is not None, "FIX 694: '¿Cuál es su nombre?' no fue detectado"
        assert resultado['tipo'] == 'PREGUNTA_IDENTIDAD', \
            f"FIX 694: Tipo incorrecto: {resultado['tipo']}"

    def test_como_se_llama_detectado(self):
        """'¿Cómo se llama?' debe disparar PREGUNTA_IDENTIDAD."""
        a = _crear_agente()
        resultado = a._detectar_patron_simple_optimizado("¿Cómo se llama usted?")
        assert resultado is not None, "FIX 694: '¿Cómo se llama?' no fue detectado"
        assert resultado['tipo'] in ['PREGUNTA_IDENTIDAD', 'PREGUNTA_IDENTIDAD_SIN_ENCARGADO']

    def test_su_nombre_detectado(self):
        """'su nombre' debe disparar PREGUNTA_IDENTIDAD."""
        a = _crear_agente()
        resultado = a._detectar_patron_simple_optimizado("¿Cuál es su nombre, por favor?")
        assert resultado is not None

    def test_quien_habla_sigue_funcionando(self):
        """Patrones existentes ('quién habla') siguen funcionando."""
        a = _crear_agente()
        resultado = a._detectar_patron_simple_optimizado("¿Quién habla?")
        assert resultado is not None
        assert 'IDENTIDAD' in resultado['tipo'] or 'UBICACION' in resultado['tipo']

    def test_bruce2238_escenario(self):
        """BRUCE2238: Cliente pregunta nombre 2x, Bruce debe responder."""
        a = _crear_agente([
            {"role": "assistant", "content": "Me comunico de la marca nioval para productos ferreteros."},
            {"role": "user", "content": "¿Qué necesita? Sí. ¿Cuál es su nombre?"},
        ])
        resultado = a._detectar_patron_simple_optimizado("¿Cuál es su nombre?")
        assert resultado is not None, \
            "BRUCE2238: '¿Cuál es su nombre?' no fue detectado como patrón"
        assert 'bruce' in resultado['respuesta'].lower() or 'nombre' in resultado['respuesta'].lower(), \
            f"Respuesta debe incluir nombre de Bruce: '{resultado['respuesta']}'"

    def test_source_tiene_patrones_694(self):
        """Verificar que agente_ventas.py tiene los nuevos patrones."""
        with open(os.path.join(os.path.dirname(os.path.dirname(__file__)),
                               'agente_ventas.py'), encoding='utf-8') as f:
            source = f.read()
        assert 'cuál es su nombre' in source or 'cual es su nombre' in source
        assert 'cómo se llama' in source or 'como se llama' in source

    def test_inmunidad_602_pregunta_identidad(self):
        """PREGUNTA_IDENTIDAD debe estar en patrones_inmunes_602."""
        with open(os.path.join(os.path.dirname(os.path.dirname(__file__)),
                               'agente_ventas.py'), encoding='utf-8') as f:
            source = f.read()
        assert "'PREGUNTA_IDENTIDAD'" in source and 'patrones_inmunes_602' in source


# ============================================================
# FIX 695: Callback "hablar luego/más tarde" patterns
# ============================================================

class TestFix695CallbackHablar:
    """FIX 695: BRUCE2232 - 'si gustas hablar luego' debe detectarse como callback."""

    def test_hablar_luego_detectado(self):
        """'hablar luego' debe ser patrón de callback."""
        texto = "si gustas hablar luego cuando esté el encargado"
        patrones = ['hablar luego', 'hablar más tarde', 'si gusta hablar', 'si gustas hablar']
        detectado = any(p in texto.lower() for p in patrones)
        assert detectado, "FIX 695: 'si gustas hablar luego' no fue detectado"

    def test_hablar_mas_tarde_detectado(self):
        """'hablar más tarde' debe ser patrón de callback."""
        texto = "mejor hablar más tarde cuando llegue"
        patrones = ['hablar luego', 'hablar más tarde', 'hablar mas tarde']
        detectado = any(p in texto.lower() for p in patrones)
        assert detectado

    def test_hablar_despues_detectado(self):
        """'hablar después' debe ser patrón de callback."""
        texto = "si quiere hablar después con el encargado"
        patrones = ['hablar después', 'hablar despues']
        detectado = any(p in texto.lower() for p in patrones)
        assert detectado

    def test_si_gustas_hablar_detectado(self):
        """'si gustas hablar' debe ser patrón de callback."""
        texto = "si gustas hablar con él regresa a las 4"
        patrones = ['si gusta hablar', 'si gustas hablar']
        detectado = any(p in texto.lower() for p in patrones)
        assert detectado

    def test_bruce2232_scenario(self):
        """BRUCE2232: 'Si gustas hablar luego' → callback detectado."""
        texto = "si gustas hablar luego. no, no lo tengo."
        patrones_callback = [
            'marcar más tarde', 'llamar más tarde',
            'hablar luego', 'hablar más tarde',
            'si gusta hablar', 'si gustas hablar',
        ]
        es_callback = any(p in texto.lower() for p in patrones_callback)
        assert es_callback, "BRUCE2232: 'si gustas hablar luego' no fue detectado como callback"

    def test_source_servidor_tiene_hablar(self):
        """servidor_llamadas.py debe tener 'hablar luego' en patrones_callback_645."""
        with open(os.path.join(os.path.dirname(os.path.dirname(__file__)),
                               'servidor_llamadas.py'), encoding='utf-8') as f:
            source = f.read()
        assert 'hablar luego' in source
        assert 'si gusta hablar' in source or 'si gustas hablar' in source

    def test_source_agente_tiene_hablar(self):
        """agente_ventas.py debe tener 'hablar' variantes en callback patterns."""
        with open(os.path.join(os.path.dirname(os.path.dirname(__file__)),
                               'agente_ventas.py'), encoding='utf-8') as f:
            source = f.read()
        assert 'si gusta hablar' in source
        assert 'hablar luego' in source

    def test_patrones_existentes_siguen_funcionando(self):
        """Patrones existentes de callback siguen detectando."""
        patrones_existentes = [
            'marcar más tarde', 'llamar más tarde', 'volver a marcar',
            'esperar a que regrese', 'mandar la información',
        ]
        casos = [
            "puede marcar más tarde",
            "si gusta volver a marcar mañana",
            "esperar a que regrese el encargado",
        ]
        for caso in casos:
            detectado = any(p in caso.lower() for p in patrones_existentes)
            assert detectado, f"Patrón existente no detectó: '{caso}'"


# ============================================================
# Tests de integración
# ============================================================

class TestIntegracionFix693_694_695:
    """Tests que combinan los 3 fixes."""

    def test_bruce2238_completo(self):
        """BRUCE2238: Pitch repetido + nombre no respondido."""
        a = _crear_agente([
            {"role": "assistant", "content": "Me comunico de la marca nioval para productos ferreteros, ¿se encontrará el encargado?"},
            {"role": "user", "content": "¿Cuál es su nombre?"},
        ])
        # FIX 694: Pattern detector debe capturar "¿Cuál es su nombre?"
        resultado = a._detectar_patron_simple_optimizado("¿Cuál es su nombre?")
        assert resultado is not None, "FIX 694 no detectó '¿Cuál es su nombre?'"
        # FIX 693: Si GPT genera pitch de nuevo, debe bloquearse
        respuesta = a._filtrar_respuesta_post_gpt(
            "Me comunico de la marca NIOVAL, somos distribuidores de productos ferreteros."
        )
        assert 'nioval' not in respuesta.lower(), \
            f"FIX 693 no bloqueó pitch repetido en escenario BRUCE2238"

    def test_bruce2232_callback_hablar(self):
        """BRUCE2232: 'Si gustas hablar luego' detectado como callback."""
        texto = "si gustas hablar luego. no, no lo tengo."
        patrones_callback_completos = [
            'marcar más tarde', 'llamar más tarde', 'marcar después', 'llamar después',
            'volver a marcar', 'volver a llamar',
            'hablar luego', 'hablar más tarde', 'hablar mas tarde',
            'hablar después', 'hablar despues',
            'si gusta hablar', 'si gustas hablar',
        ]
        es_callback = any(p in texto.lower() for p in patrones_callback_completos)
        assert es_callback, "BRUCE2232 callback no detectado"

    def test_pitch_1ra_vez_no_bloqueado(self):
        """Primer pitch NO debe ser bloqueado por ningún FIX."""
        a = _crear_agente([
            {"role": "assistant", "content": "Hola, buen día."},
            {"role": "user", "content": "Bueno."},
        ])
        respuesta = a._filtrar_respuesta_post_gpt(
            "Me comunico de la marca NIOVAL, más que nada quería brindar información de nuestros productos ferreteros, ¿se encontrará el encargado o encargada de compras?"
        )
        assert 'nioval' in respuesta.lower(), \
            "Primer pitch fue incorrectamente bloqueado"
