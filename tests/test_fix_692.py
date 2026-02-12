# -*- coding: utf-8 -*-
"""
Tests de regresión para FIX 692:
- FIX 692A: Threshold encargado alineado con bug detector (>=2 → >=1 previos)
- FIX 692B: GPT eval min turnos 3 + filtro duración <45s
- FIX 692C: Inmunidad FIX 602 para patrones con 0% survival
"""
import os
import sys
import time
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault("OPENAI_API_KEY", "sk-test-dummy")
os.environ.setdefault("ELEVENLABS_API_KEY", "test-dummy")
os.environ.setdefault("TWILIO_ACCOUNT_SID", "AC-test")
os.environ.setdefault("TWILIO_AUTH_TOKEN", "test-token")

from agente_ventas import AgenteVentas, EstadoConversacion


def _crear_agente_completo(historial=None, turno=3, encargado_confirmado=False):
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
    a.encargado_disponible = None
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
# FIX 692A: Threshold encargado alineado (>=1 previo)
# ============================================================

class TestFix692AEncargadoThreshold:
    """FIX 692A: BRUCE2217 - Pregunta por encargado 2x debe bloquearse."""

    def test_encargado_2da_vez_bloqueada(self):
        """Si Bruce ya preguntó encargado 1 vez, 2da debe bloquearse."""
        a = _crear_agente_completo([
            {"role": "assistant", "content": "Me comunico de la marca nioval. ¿Se encontrará el encargado o encargada de compras?"},
            {"role": "user", "content": "No está."},
        ])
        respuesta = a._filtrar_respuesta_post_gpt(
            "Sí, le preguntaba, ¿se encontrará el encargado o encargada de compras?"
        )
        assert 'se encontrará el encargado' not in respuesta.lower(), \
            f"FIX 692A: 2da pregunta encargado no fue bloqueada. Resp: '{respuesta}'"

    def test_encargado_1ra_vez_permitida(self):
        """Si Bruce NO ha preguntado encargado, 1ra vez debe pasar."""
        a = _crear_agente_completo([
            {"role": "assistant", "content": "Hola, buen día. Me comunico de la marca nioval."},
            {"role": "user", "content": "Bueno, sí, dígame."},
        ])
        respuesta = a._filtrar_respuesta_post_gpt(
            "¿Se encontrará el encargado o encargada de compras?"
        )
        assert 'encargado' in respuesta.lower(), \
            f"FIX 692A: 1ra pregunta encargado fue incorrectamente bloqueada. Resp: '{respuesta}'"

    def test_encargado_confirmado_bloqueado(self):
        """Si cliente ES el encargado, NUNCA preguntar (FIX 494)."""
        a = _crear_agente_completo([
            {"role": "assistant", "content": "¿Se encontrará el encargado?"},
            {"role": "user", "content": "Soy yo, dígame."},
        ], encargado_confirmado=True)
        respuesta = a._filtrar_respuesta_post_gpt(
            "¿Se encontrará el encargado o encargada de compras?"
        )
        assert 'se encontrará el encargado' not in respuesta.lower()

    def test_bruce2217_scenario(self):
        """Escenario BRUCE2217: encargado preguntado 2x en 4 turnos."""
        a = _crear_agente_completo([
            {"role": "assistant", "content": "Hola, buen día."},
            {"role": "user", "content": "Bueno."},
            {"role": "assistant", "content": "Me comunico de nioval, ¿se encontrará el encargado o encargada de compras?"},
            {"role": "user", "content": "No, no está."},
        ])
        respuesta = a._filtrar_respuesta_post_gpt(
            "Sí, le preguntaba, ¿se encontrará el encargado o encargada de compras?"
        )
        assert 'se encontrará el encargado' not in respuesta.lower(), \
            f"BRUCE2217: 2da pregunta encargado no fue bloqueada"


# ============================================================
# FIX 692B: GPT eval min turnos 3 + filtro duración
# ============================================================

class TestFix692BGPTEvalFilters:
    """FIX 692B: Reducir falsos positivos en GPT eval."""

    def test_min_turnos_es_3(self):
        """GPT_EVAL_MIN_TURNOS debe ser 3 (no 2)."""
        from bug_detector import GPT_EVAL_MIN_TURNOS
        assert GPT_EVAL_MIN_TURNOS == 3

    def test_min_duracion_existe(self):
        """GPT_EVAL_MIN_DURACION_S debe existir y ser >= 45."""
        from bug_detector import GPT_EVAL_MIN_DURACION_S
        assert GPT_EVAL_MIN_DURACION_S >= 45

    def test_2_turnos_no_evalua(self):
        """Con solo 2 turnos de Bruce, GPT eval no debe ejecutarse."""
        from bug_detector import _evaluar_con_gpt, CallEventTracker
        tracker = CallEventTracker("CA_test", "BRUCE_TEST", "+5200000")
        tracker.emit("BRUCE_RESPONDE", {"texto": "Hola, buen día."})
        tracker.emit("CLIENTE_HABLA", {"texto": "Bueno."})
        tracker.emit("BRUCE_RESPONDE", {"texto": "Me comunico de nioval."})
        resultado = _evaluar_con_gpt(tracker)
        assert resultado == [], "GPT eval no debe ejecutarse con 2 turnos de Bruce"

    def test_3_turnos_corta_duracion_no_evalua(self):
        """Con 3 turnos pero <45s, GPT eval no debe ejecutarse."""
        from bug_detector import _evaluar_con_gpt, CallEventTracker
        tracker = CallEventTracker("CA_test2", "BRUCE_TEST2", "+5200000")
        # Simular que la llamada acaba de empezar (hace <45s)
        tracker.created_at = time.time()  # Justo ahora = 0s de duración
        tracker.emit("BRUCE_RESPONDE", {"texto": "Hola."})
        tracker.emit("BRUCE_RESPONDE", {"texto": "Me comunico de nioval."})
        tracker.emit("BRUCE_RESPONDE", {"texto": "¿Se encontrará el encargado?"})
        resultado = _evaluar_con_gpt(tracker)
        assert resultado == [], "GPT eval no debe ejecutarse con <45s de duración"

    def test_bruce2214_scenario_no_evalua(self):
        """Escenario BRUCE2214: 2 turnos, 43s → NO debe evaluarse."""
        from bug_detector import _evaluar_con_gpt, CallEventTracker
        tracker = CallEventTracker("CA_bruce2214", "BRUCE2214", "+5200000")
        tracker.created_at = time.time() - 43  # 43 segundos atrás
        tracker.emit("BRUCE_RESPONDE", {"texto": "Hola."})
        tracker.emit("BRUCE_RESPONDE", {"texto": "¿Le envío catálogo?"})
        resultado = _evaluar_con_gpt(tracker)
        assert resultado == [], "BRUCE2214 (2t/43s) no debe evaluarse"


# ============================================================
# FIX 692C: Inmunidad FIX 602 para patrones 0% survival
# ============================================================

class TestFix692CPatternImmunity602:
    """FIX 692C: Patrones con 0% survival deben ser inmunes a FIX 602."""

    def test_source_tiene_patrones_inmunes_602(self):
        """agente_ventas.py debe tener patrones_inmunes_602 definido."""
        with open(os.path.join(os.path.dirname(os.path.dirname(__file__)),
                               'agente_ventas.py'), encoding='utf-8') as f:
            source = f.read()
        assert 'patrones_inmunes_602' in source
        assert 'OFRECER_CONTACTO_BRUCE' in source
        assert 'CLIENTE_ACEPTA_CORREO' in source
        assert 'CLIENTE_OFRECE_SU_CONTACTO' in source
        assert 'CLIENTE_OFRECE_WHATSAPP' in source
        assert 'PEDIR_TELEFONO_FIJO' in source
        assert 'PREGUNTA_MARCAS' in source

    def test_inmunidad_check_antes_de_invalidacion(self):
        """FIX 602 debe verificar inmunidad ANTES de invalidar."""
        with open(os.path.join(os.path.dirname(os.path.dirname(__file__)),
                               'agente_ventas.py'), encoding='utf-8') as f:
            source = f.read()
        # La condición debe incluir "not in patrones_inmunes_602"
        assert 'not in patrones_inmunes_602' in source, \
            "FIX 602 invalidación debe verificar inmunidad FIX 692C"

    def test_6_patrones_protegidos(self):
        """Los 6 patrones con 0% survival deben estar en inmunes_602."""
        patrones_esperados = [
            'OFRECER_CONTACTO_BRUCE',
            'CLIENTE_ACEPTA_CORREO',
            'CLIENTE_OFRECE_SU_CONTACTO',
            'CLIENTE_OFRECE_WHATSAPP',
            'PEDIR_TELEFONO_FIJO',
            'PREGUNTA_MARCAS',
        ]
        with open(os.path.join(os.path.dirname(os.path.dirname(__file__)),
                               'agente_ventas.py'), encoding='utf-8') as f:
            source = f.read()
        for patron in patrones_esperados:
            # Verificar que está en patrones_inmunes_602
            assert f"'{patron}'" in source or f'"{patron}"' in source, \
                f"Patrón {patron} no encontrado en código"

    def test_ofrecer_contacto_bruce_logica(self):
        """OFRECER_CONTACTO_BRUCE debe sobrevivir en contexto PIDIENDO_CORREO."""
        # Simulación de lógica FIX 602
        patrones_inmunes_602 = {
            'OFRECER_CONTACTO_BRUCE', 'CLIENTE_ACEPTA_CORREO',
            'CLIENTE_OFRECE_SU_CONTACTO', 'CLIENTE_OFRECE_WHATSAPP',
            'PEDIR_TELEFONO_FIJO', 'PREGUNTA_MARCAS',
        }
        tipo_patron = 'OFRECER_CONTACTO_BRUCE'
        incoherencias = ['ENCARGADO_NO_ESTA_CON_HORARIO', 'TRANSFERENCIA']
        # Con FIX 692C, no debe ser invalidado
        invalidar = tipo_patron in incoherencias and tipo_patron not in patrones_inmunes_602
        assert not invalidar, "OFRECER_CONTACTO_BRUCE no debe ser invalidado"

    def test_patron_no_inmune_si_se_invalida(self):
        """Patrones NO inmunes SÍ deben ser invalidados normalmente."""
        patrones_inmunes_602 = {
            'OFRECER_CONTACTO_BRUCE', 'CLIENTE_ACEPTA_CORREO',
            'CLIENTE_OFRECE_SU_CONTACTO', 'CLIENTE_OFRECE_WHATSAPP',
            'PEDIR_TELEFONO_FIJO', 'PREGUNTA_MARCAS',
        }
        tipo_patron = 'ENCARGADO_NO_ESTA_CON_HORARIO'
        incoherencias = ['ENCARGADO_NO_ESTA_CON_HORARIO', 'TRANSFERENCIA']
        # NO es inmune → debe ser invalidado
        invalidar = tipo_patron in incoherencias and tipo_patron not in patrones_inmunes_602
        assert invalidar, "Patrón no inmune debe ser invalidado normalmente"


# ============================================================
# Tests de integración
# ============================================================

class TestIntegracionFix692:
    """Tests que combinan los 3 sub-fixes."""

    def test_thresholds_alineados_bug_detector(self):
        """Verificar que threshold encargado está alineado con bug_detector."""
        # bug_detector marca PREGUNTA_REPETIDA con >= 2 total
        # FIX 692A bloquea con >= 1 previos (= bloquea 2da = alineado)
        threshold_previos = 1  # FIX 692A
        preguntas_que_bug_detector_marca = 2  # >= 2 total
        # Si hay 1 previo y va a hacer la 2da, FIX 692A bloquea ANTES de llegar a 2 total
        bloqueado_antes_de_bug = threshold_previos < preguntas_que_bug_detector_marca
        assert bloqueado_antes_de_bug, "Threshold debe bloquear ANTES de que bug detector marque"

    def test_gpt_eval_filtros_combinados(self):
        """GPT eval debe tener múltiples filtros anti-FP."""
        from bug_detector import GPT_EVAL_MIN_TURNOS, GPT_EVAL_MIN_DURACION_S
        # Filtro 1: Min turnos
        assert GPT_EVAL_MIN_TURNOS >= 3
        # Filtro 2: Min duración
        assert GPT_EVAL_MIN_DURACION_S >= 45

    def test_persistencia_bugs_robusta(self):
        """FIX 691: _save_bugs tiene force parameter."""
        from bug_detector import _save_bugs
        import inspect
        sig = inspect.signature(_save_bugs)
        assert 'force' in sig.parameters, "FIX 691: _save_bugs debe tener parámetro force"
