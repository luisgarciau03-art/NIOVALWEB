# -*- coding: utf-8 -*-
"""
Tests de regresión para FIX 684 (CTN-002: eliminar menciones problemas técnicos)
y FIX 685 (FLU-001: mejorar exclusiones auditor).
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


# ============================================================
# FIX 684: Post-filter CTN-002 en agente_ventas
# ============================================================

@pytest.fixture
def agente():
    """Crea AgenteVentas para testing FIX 684."""
    a = AgenteVentas.__new__(AgenteVentas)
    a.conversation_history = [
        {"role": "assistant", "content": "Hola, buen día."},
        {"role": "user", "content": "Bueno."},
        {"role": "assistant", "content": "Me comunico de la marca nioval para productos ferreteros. ¿Se encontrará el encargado?"},
        {"role": "user", "content": "Mande."},
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
    a._detectar_error_necesita_recuperacion = lambda *args, **kwargs: (False, None, None)
    a._generar_respuesta_recuperacion_error = lambda *args, **kwargs: "Disculpe, ¿me puede repetir?"
    a._validar_sentido_comun = lambda resp, *args, **kwargs: (True, "")
    return a


class TestFix684PostFilterCTN002:
    """FIX 684: Post-filter bloquea menciones de problemas técnicos en respuesta GPT."""

    def test_bloquea_problemas_conexion(self, agente):
        """GPT dice 'problemas de conexión' → debe reemplazarse."""
        respuesta = agente._filtrar_respuesta_post_gpt(
            "Parece que tenemos problemas de conexión. ¿Le llamo más tarde?"
        )
        assert 'problemas de conexión' not in respuesta.lower()
        assert 'problemas de conexion' not in respuesta.lower()

    def test_bloquea_problemas_tecnicos(self, agente):
        """GPT dice 'problemas técnicos' → debe reemplazarse."""
        respuesta = agente._filtrar_respuesta_post_gpt(
            "Disculpe, tenemos problemas técnicos en este momento."
        )
        assert 'problemas técnicos' not in respuesta.lower()

    def test_bloquea_problemas_audio(self, agente):
        """GPT dice 'problemas de audio' → debe reemplazarse."""
        respuesta = agente._filtrar_respuesta_post_gpt(
            "Perdón, tuve problemas de audio. ¿Puede repetir?"
        )
        assert 'problemas de audio' not in respuesta.lower()

    def test_bloquea_interferencia(self, agente):
        """GPT dice 'hay interferencia' → debe reemplazarse."""
        respuesta = agente._filtrar_respuesta_post_gpt(
            "Parece que hay interferencia en la línea, le marco después."
        )
        assert 'hay interferencia' not in respuesta.lower()

    def test_bloquea_problemas_comunicacion(self, agente):
        """GPT dice 'problemas de comunicación' → debe reemplazarse."""
        respuesta = agente._filtrar_respuesta_post_gpt(
            "Tenemos problemas de comunicación. ¿Le envío info por WhatsApp?"
        )
        assert 'problemas de comunicación' not in respuesta.lower()

    def test_reemplazo_con_llamar_ofrece_callback(self, agente):
        """Si menciona llamar/marco → ofrece callback sin excusa técnica."""
        respuesta = agente._filtrar_respuesta_post_gpt(
            "Tenemos problemas de conexión, le marco después."
        )
        assert 'escuchando' in respuesta.lower() or 'llamar' in respuesta.lower() or 'llame' in respuesta.lower()

    def test_reemplazo_con_whatsapp_ofrece_catalogo(self, agente):
        """Si menciona WhatsApp → ofrece catálogo sin excusa técnica."""
        respuesta = agente._filtrar_respuesta_post_gpt(
            "Problemas de conexión. ¿Le envío el catálogo por WhatsApp?"
        )
        assert 'catálogo' in respuesta.lower() or 'catalogo' in respuesta.lower()

    def test_reemplazo_generico_pide_repetir(self, agente):
        """Sin contexto específico → pide repetir sin excusa técnica."""
        respuesta = agente._filtrar_respuesta_post_gpt(
            "Hay problemas técnicos, disculpe."
        )
        assert 'repetir' in respuesta.lower() or 'escuché' in respuesta.lower() or 'escuche' in respuesta.lower()

    def test_no_bloquea_respuesta_sin_tecnicos(self, agente):
        """Respuestas sin menciones técnicas NO deben bloquearse."""
        respuesta = agente._filtrar_respuesta_post_gpt(
            "Perfecto, le envío el catálogo de productos ferreteros por WhatsApp."
        )
        assert 'catálogo' in respuesta.lower() or 'catalogo' in respuesta.lower()

    def test_no_bloquea_no_le_escuche(self, agente):
        """'No le escuché bien' (sin mencionar problemas) NO debe bloquearse."""
        respuesta = agente._filtrar_respuesta_post_gpt(
            "Disculpe, no le escuché bien. ¿Me puede repetir?"
        )
        assert 'repetir' in respuesta.lower()


# ============================================================
# FIX 684: Verificar strings en servidor_llamadas.py
# ============================================================

class TestFix684ServidorStrings:
    """FIX 684: Verificar que servidor_llamadas.py NO contiene 'problemas de conexión'."""

    def test_no_problemas_conexion_en_servidor(self):
        """servidor_llamadas.py NO debe tener 'problemas con la conexión' en mensajes de Bruce."""
        import re
        with open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                               'servidor_llamadas.py'), 'r', encoding='utf-8') as f:
            contenido = f.read()
        # Buscar en strings literales (entre comillas)
        # Permitimos en comentarios pero no en strings que se dicen al cliente
        mensajes_bruce = re.findall(r'mensaje_error\s*=\s*"([^"]*)"', contenido)
        for msg in mensajes_bruce:
            assert 'problemas con la conexión' not in msg.lower(), \
                f"FIX 684: Encontrada mención 'problemas con la conexión' en: '{msg[:60]}'"
            assert 'problemas de conexión' not in msg.lower(), \
                f"FIX 684: Encontrada mención 'problemas de conexión' en: '{msg[:60]}'"

    def test_no_problemas_audio_en_mensajes_repetir(self):
        """mensajes_repetir NO debe tener 'problemas de audio' en strings literales."""
        import re
        with open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                               'servidor_llamadas.py'), 'r', encoding='utf-8') as f:
            contenido = f.read()
        # Buscar solo en strings literales (entre comillas), no en comentarios
        strings_literales = re.findall(r'"([^"]*problemas de audio[^"]*)"', contenido)
        assert len(strings_literales) == 0, \
            f"FIX 684: Aún existe 'problemas de audio' en string literal: {strings_literales}"


# ============================================================
# FIX 684: Verificar strings en agente_ventas.py
# ============================================================

class TestFix684AgenteStrings:
    """FIX 684: Verificar que agente_ventas.py NO contiene excusas técnicas en respuestas."""

    def test_no_problemas_conexion_en_agente(self):
        """agente_ventas.py NO debe tener 'problemas de conexión' en return statements."""
        import re
        with open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                               'agente_ventas.py'), 'r', encoding='utf-8') as f:
            contenido = f.read()
        # Buscar en return "..." y respuesta = "..."
        returns = re.findall(r'return\s+"([^"]*)"', contenido)
        asignaciones = re.findall(r'respuesta\s*=\s*"([^"]*)"', contenido)
        for msg in returns + asignaciones:
            assert 'problemas de conexión' not in msg.lower(), \
                f"FIX 684: 'problemas de conexión' en: '{msg[:60]}'"
            assert 'problemas de comunicación' not in msg.lower(), \
                f"FIX 684: 'problemas de comunicación' en: '{msg[:60]}'"


# ============================================================
# FIX 685: Mejorar exclusiones FLU-001
# ============================================================

class TestFix685FLU001Exclusions:
    """FIX 685: FLU-001 exclusiones mejoradas."""

    def _crear_conversacion(self, mensajes, estado_final='completed'):
        return {
            'mensajes': mensajes,
            'estado_final': estado_final,
            'duracion': 30,
            'gpt_timeouts': 0,
            'stt_timeouts': 0,
            'respuestas_vacias': 0,
        }

    def test_timeout_cliente_no_es_flu001(self):
        """Si último msg cliente es '[Timeout]', no es FLU-001."""
        from auditor_conversaciones import auditar_conversacion
        conv = self._crear_conversacion([
            {'rol': 'bruce', 'texto': 'Hola, buen día.'},
            {'rol': 'cliente', 'texto': 'Bueno.'},
            {'rol': 'bruce', 'texto': 'Me comunico de nioval para productos.'},
            {'rol': 'cliente', 'texto': '[Timeout Deepgram #1]'},
        ])
        bugs = auditar_conversacion('BRUCE_TEST', conv)
        flu = [b for b in bugs if b['codigo'] == 'FLU-001']
        assert len(flu) == 0, f"FLU-001 no debió dispararse con timeout. Bugs: {flu}"

    def test_buzon_cliente_no_es_flu001(self):
        """Si último msg cliente menciona buzón, no es FLU-001."""
        from auditor_conversaciones import auditar_conversacion
        conv = self._crear_conversacion([
            {'rol': 'bruce', 'texto': 'Hola, buen día.'},
            {'rol': 'cliente', 'texto': 'Favor de dejar un breve mensaje después del tono.'},
        ])
        bugs = auditar_conversacion('BRUCE_TEST', conv)
        flu = [b for b in bugs if b['codigo'] == 'FLU-001']
        assert len(flu) == 0, f"FLU-001 no debió dispararse con buzón. Bugs: {flu}"

    def test_despedida_buen_dia_no_es_flu001(self):
        """'Buen día' como despedida no es FLU-001."""
        from auditor_conversaciones import auditar_conversacion
        conv = self._crear_conversacion([
            {'rol': 'bruce', 'texto': 'Muchas gracias. Que tenga excelente día.'},
            {'rol': 'cliente', 'texto': 'Buen día.'},
        ])
        bugs = auditar_conversacion('BRUCE_TEST', conv)
        flu = [b for b in bugs if b['codigo'] == 'FLU-001']
        assert len(flu) == 0, f"FLU-001 no debió dispararse con 'Buen día'. Bugs: {flu}"

    def test_despedida_bendiciones_no_es_flu001(self):
        """'Bendiciones' como despedida no es FLU-001."""
        from auditor_conversaciones import auditar_conversacion
        conv = self._crear_conversacion([
            {'rol': 'bruce', 'texto': 'Muchas gracias por su tiempo.'},
            {'rol': 'cliente', 'texto': 'Bendiciones.'},
        ])
        bugs = auditar_conversacion('BRUCE_TEST', conv)
        flu = [b for b in bugs if b['codigo'] == 'FLU-001']
        assert len(flu) == 0, f"FLU-001 no debió dispararse con 'Bendiciones'"

    def test_bruce_se_despidio_antes_no_es_flu001(self):
        """Si Bruce se despidió antes del último msg cliente, no es FLU-001."""
        from auditor_conversaciones import auditar_conversacion
        conv = self._crear_conversacion([
            {'rol': 'bruce', 'texto': 'Hola, buen día.'},
            {'rol': 'cliente', 'texto': 'Bueno.'},
            {'rol': 'bruce', 'texto': 'Que tenga excelente día, le marco después.'},
            {'rol': 'cliente', 'texto': 'Sí, está bien.'},
        ])
        bugs = auditar_conversacion('BRUCE_TEST', conv)
        flu = [b for b in bugs if b['codigo'] == 'FLU-001']
        assert len(flu) == 0, f"FLU-001 no debió dispararse cuando Bruce ya se despidió"

    def test_bruce_problemas_escuchar_no_es_flu001(self):
        """Si Bruce dijo 'no le estoy escuchando bien', no es FLU-001."""
        from auditor_conversaciones import auditar_conversacion
        conv = self._crear_conversacion([
            {'rol': 'bruce', 'texto': 'Disculpe, no le estoy escuchando bien. ¿Prefiere que le llame en otro momento?'},
            {'rol': 'cliente', 'texto': 'Sí, está bien, llámame después.'},
        ])
        bugs = auditar_conversacion('BRUCE_TEST', conv)
        flu = [b for b in bugs if b['codigo'] == 'FLU-001']
        assert len(flu) == 0, f"FLU-001 no debió dispararse con 'no le estoy escuchando bien'"

    def test_rechazo_no_ocupo_nada_no_es_flu001(self):
        """'No ocupo nada' como rechazo no es FLU-001."""
        from auditor_conversaciones import auditar_conversacion
        conv = self._crear_conversacion([
            {'rol': 'bruce', 'texto': 'Me comunico de nioval para productos ferreteros.'},
            {'rol': 'cliente', 'texto': 'No ocupo nada, gracias.'},
        ])
        bugs = auditar_conversacion('BRUCE_TEST', conv)
        flu = [b for b in bugs if b['codigo'] == 'FLU-001']
        assert len(flu) == 0, f"FLU-001 no debió dispararse con rechazo 'no ocupo nada'"

    def test_real_flu001_si_detecta(self):
        """Si cliente da info y Bruce no responde, SÍ es FLU-001."""
        from auditor_conversaciones import auditar_conversacion
        conv = self._crear_conversacion([
            {'rol': 'bruce', 'texto': 'Hola, buen día.'},
            {'rol': 'cliente', 'texto': 'Bueno.'},
            {'rol': 'bruce', 'texto': '¿Me puede dar un número de WhatsApp?'},
            {'rol': 'cliente', 'texto': 'Mi número es tres tres uno dos tres cuatro.'},
        ])
        bugs = auditar_conversacion('BRUCE_TEST', conv)
        flu = [b for b in bugs if b['codigo'] == 'FLU-001']
        assert len(flu) == 1, f"FLU-001 debió detectarse. Bugs: {[b['codigo'] for b in bugs]}"


# ============================================================
# FIX 685: CTN-002 en auditor (verificar que ya no detecta nuevos mensajes)
# ============================================================

class TestFix685CTN002Auditor:
    """FIX 685: CTN-002 ya no debe detectarse con nuevos mensajes FIX 684."""

    def _crear_conversacion(self, mensajes, estado_final='completed'):
        return {
            'mensajes': mensajes,
            'estado_final': estado_final,
            'duracion': 30,
            'gpt_timeouts': 0,
            'stt_timeouts': 0,
            'respuestas_vacias': 0,
        }

    def test_no_le_escucho_bien_no_es_ctn002(self):
        """'No le estoy escuchando bien' NO debe disparar CTN-002."""
        from auditor_conversaciones import auditar_conversacion
        conv = self._crear_conversacion([
            {'rol': 'bruce', 'texto': 'Hola, buen día.'},
            {'rol': 'cliente', 'texto': 'Bueno.'},
            {'rol': 'bruce', 'texto': 'Disculpe, no le estoy escuchando bien. ¿Prefiere que le llame en otro momento?'},
            {'rol': 'cliente', 'texto': 'Sí, está bien.'},
            {'rol': 'bruce', 'texto': 'Perfecto, le marco más tarde. Que tenga buen día.'},
        ])
        bugs = auditar_conversacion('BRUCE_TEST', conv)
        ctn = [b for b in bugs if b['codigo'] == 'CTN-002']
        assert len(ctn) == 0, f"CTN-002 no debió dispararse con 'no le estoy escuchando bien'. Bugs: {ctn}"

    def test_no_le_escuche_bien_no_es_ctn002(self):
        """'No le escuché bien' NO debe disparar CTN-002."""
        from auditor_conversaciones import auditar_conversacion
        conv = self._crear_conversacion([
            {'rol': 'bruce', 'texto': 'Hola, buen día.'},
            {'rol': 'cliente', 'texto': 'Bueno.'},
            {'rol': 'bruce', 'texto': 'Disculpe, no le escuché bien. ¿Me puede repetir?'},
            {'rol': 'cliente', 'texto': 'Sí, le decía que no está el encargado.'},
            {'rol': 'bruce', 'texto': 'Entiendo. ¿Me podría proporcionar un WhatsApp?'},
        ])
        bugs = auditar_conversacion('BRUCE_TEST', conv)
        ctn = [b for b in bugs if b['codigo'] == 'CTN-002']
        assert len(ctn) == 0, f"CTN-002 no debió dispararse con 'no le escuché bien'. Bugs: {ctn}"

    def test_viejo_problemas_conexion_si_detecta(self):
        """Si aún hubiera 'problemas de conexión', CTN-002 SÍ lo detecta (validar auditor funciona)."""
        from auditor_conversaciones import auditar_conversacion
        conv = self._crear_conversacion([
            {'rol': 'bruce', 'texto': 'Hola, buen día.'},
            {'rol': 'cliente', 'texto': 'Bueno.'},
            {'rol': 'bruce', 'texto': 'Parece que tenemos problemas de conexión. Le marco después.'},
            {'rol': 'cliente', 'texto': 'Está bien.'},
        ])
        bugs = auditar_conversacion('BRUCE_TEST', conv)
        ctn = [b for b in bugs if b['codigo'] == 'CTN-002']
        assert len(ctn) == 1, f"CTN-002 debió detectarse con 'problemas de conexión'. Bugs: {[b['codigo'] for b in bugs]}"
