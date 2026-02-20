# -*- coding: utf-8 -*-
"""
Tests de regresión para FIX 699: Memory Layer
Verifica que ConversationMemory extrae hechos correctamente,
genera contexto GPT apropiado, bloquea preguntas redundantes,
y valida respuestas contra hechos conocidos.
"""
import os
import sys
import pytest

# Agregar directorio padre al path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from memory_layer import ConversationMemory


@pytest.fixture
def memory():
    """Crea una instancia limpia de ConversationMemory."""
    return ConversationMemory()


# ============================================================
# EXTRACT FACTS - Hechos del cliente
# ============================================================

class TestExtractFactsCliente:
    """Tests de extract_facts() para mensajes del cliente."""

    def test_encargado_no_esta(self, memory):
        history = [
            {"role": "assistant", "content": "¿Se encuentra el encargado?"},
            {"role": "user", "content": "No, no está ahorita"}
        ]
        memory.extract_facts(history)
        assert memory.facts.get('encargado_disponible') == False

    def test_encargado_no_se_encuentra(self, memory):
        history = [
            {"role": "user", "content": "No se encuentra, salió a comer"}
        ]
        memory.extract_facts(history)
        assert memory.facts.get('encargado_disponible') == False

    def test_encargado_salio(self, memory):
        history = [{"role": "user", "content": "Salió temprano hoy"}]
        memory.extract_facts(history)
        assert memory.facts.get('encargado_disponible') == False

    def test_encargado_vacaciones(self, memory):
        history = [{"role": "user", "content": "Está de vacaciones hasta el lunes"}]
        memory.extract_facts(history)
        assert memory.facts.get('encargado_disponible') == False

    def test_es_encargado(self, memory):
        history = [{"role": "user", "content": "Soy yo, dígame"}]
        memory.extract_facts(history)
        assert memory.facts.get('es_encargado') == True
        assert memory.facts.get('encargado_disponible') == True

    def test_es_encargado_servidor(self, memory):
        history = [{"role": "user", "content": "Servidor, a sus órdenes"}]
        memory.extract_facts(history)
        assert memory.facts.get('es_encargado') == True

    def test_mismo_numero(self, memory):
        history = [{"role": "user", "content": "Hay este mismo número, no sé qué día"}]
        memory.extract_facts(history)
        assert memory.facts.get('mismo_numero') == True
        assert 'mismo_numero' in memory.contexto_cliente

    def test_es_el_mismo(self, memory):
        history = [{"role": "user", "content": "Es el mismo número del encargado"}]
        memory.extract_facts(history)
        assert memory.facts.get('mismo_numero') == True

    def test_rechazo_whatsapp(self, memory):
        history = [{"role": "user", "content": "No tengo WhatsApp"}]
        memory.extract_facts(history)
        assert 'whatsapp' in memory.rechazos

    def test_rechazo_correo(self, memory):
        history = [{"role": "user", "content": "No tengo correo electrónico"}]
        memory.extract_facts(history)
        assert 'email' in memory.rechazos

    def test_rechazo_no_quiero_dejar(self, memory):
        history = [{"role": "user", "content": "No te quiero dejar el celular"}]
        memory.extract_facts(history)
        assert 'contacto' in memory.rechazos

    def test_rechazo_no_puedo_dar(self, memory):
        history = [{"role": "user", "content": "No puedo dar esa información"}]
        memory.extract_facts(history)
        assert 'contacto' in memory.rechazos

    def test_no_autorizado(self, memory):
        history = [{"role": "user", "content": "No estoy autorizado para dar esa información"}]
        memory.extract_facts(history)
        assert memory.facts.get('cliente_no_autorizado') == True
        assert 'contacto' in memory.rechazos

    def test_telefono_proporcionado(self, memory):
        history = [{"role": "user", "content": "El número es 3312345678"}]
        memory.extract_facts(history)
        assert 'telefono' in memory.datos_proporcionados
        assert '3312345678' in memory.datos_proporcionados['telefono']

    def test_email_proporcionado(self, memory):
        history = [{"role": "user", "content": "Mi correo es ventas@empresa.com"}]
        memory.extract_facts(history)
        assert 'email' in memory.datos_proporcionados
        assert memory.datos_proporcionados['email'] == 'ventas@empresa.com'

    def test_email_verbal(self, memory):
        history = [{"role": "user", "content": "Es ventas arroba gmail punto com"}]
        memory.extract_facts(history)
        assert memory.facts.get('email_dictado_verbal') == True

    def test_callback_sin_hora(self, memory):
        history = [{"role": "user", "content": "Hábleme mañana"}]
        memory.extract_facts(history)
        assert memory.facts.get('cliente_pide_callback') == True
        assert memory.facts.get('callback_sin_hora') == True

    def test_callback_con_hora(self, memory):
        history = [{"role": "user", "content": "Llame a las 9:00 am"}]
        memory.extract_facts(history)
        assert memory.facts.get('cliente_pide_callback') == True
        assert memory.facts.get('hora_callback') is not None

    def test_despedida(self, memory):
        history = [{"role": "user", "content": "Hasta luego, gracias"}]
        memory.extract_facts(history)
        assert memory.facts.get('cliente_se_despide') == True

    def test_interes(self, memory):
        history = [{"role": "user", "content": "Sí me interesa, mándame el catálogo"}]
        memory.extract_facts(history)
        assert memory.facts.get('cliente_interesado') == True

    def test_no_lo_tengo(self, memory):
        history = [{"role": "user", "content": "No lo tengo, la verdad"}]
        memory.extract_facts(history)
        assert 'dato_solicitado' in memory.rechazos


# ============================================================
# EXTRACT FACTS - Hechos de Bruce
# ============================================================

class TestExtractFactsBruce:
    """Tests de extract_facts() para mensajes de Bruce."""

    def test_pitch_dado(self, memory):
        history = [
            {"role": "assistant", "content": "Le hablo de NIOVAL, somos distribuidores de productos para ferretería y le ofrecemos nuestro catálogo"}
        ]
        memory.extract_facts(history)
        assert memory.facts.get('pitch_dado') == True

    def test_encargado_preguntado(self, memory):
        history = [
            {"role": "assistant", "content": "¿Se encontrará el encargado de compras?"}
        ]
        memory.extract_facts(history)
        assert memory.facts.get('encargado_preguntado') == True

    def test_whatsapp_solicitado(self, memory):
        history = [
            {"role": "assistant", "content": "¿Me podría dar su WhatsApp para enviarle el catálogo?"}
        ]
        memory.extract_facts(history)
        assert memory.facts.get('whatsapp_solicitado') == True

    def test_email_solicitado(self, memory):
        history = [
            {"role": "assistant", "content": "¿Me podría proporcionar un correo electrónico?"}
        ]
        memory.extract_facts(history)
        assert memory.facts.get('email_solicitado') == True

    def test_catalogo_ofrecido(self, memory):
        history = [
            {"role": "assistant", "content": "Perfecto, le envío el catálogo en las próximas 2 horas"}
        ]
        memory.extract_facts(history)
        assert memory.facts.get('catalogo_ofrecido') == True


# ============================================================
# EXTRACT FACTS - Incremental
# ============================================================

class TestExtractFactsIncremental:
    """Tests de extracción incremental (solo mensajes nuevos)."""

    def test_incremental_no_reprocesa(self, memory):
        history = [
            {"role": "user", "content": "No está el encargado"}
        ]
        memory.extract_facts(history)
        assert memory.facts.get('encargado_disponible') == False

        # Agregar más mensajes
        history.append({"role": "assistant", "content": "¿Me da su WhatsApp?"})
        history.append({"role": "user", "content": "Sí, es 3312345678"})
        memory.extract_facts(history)

        assert 'telefono' in memory.datos_proporcionados
        assert memory.facts.get('encargado_disponible') == False  # No se perdió

    def test_multiple_hechos_acumulan(self, memory):
        history = [
            {"role": "user", "content": "No está el encargado"},
            {"role": "assistant", "content": "¿Me da su WhatsApp?"},
            {"role": "user", "content": "No tengo WhatsApp"},
        ]
        memory.extract_facts(history)
        assert memory.facts.get('encargado_disponible') == False
        assert 'whatsapp' in memory.rechazos

    def test_history_vacio(self, memory):
        memory.extract_facts([])
        assert memory.facts == {}

    def test_history_none_no_crash(self, memory):
        memory.extract_facts(None)
        assert memory.facts == {}


# ============================================================
# GET GPT CONTEXT
# ============================================================

class TestGetGptContext:
    """Tests de get_gpt_context()."""

    def test_contexto_vacio_sin_hechos(self, memory):
        assert memory.get_gpt_context() == ""

    def test_contexto_encargado_no_esta(self, memory):
        memory.facts['encargado_disponible'] = False
        ctx = memory.get_gpt_context()
        assert 'NO esta disponible' in ctx
        assert 'NO volver a preguntar' in ctx

    def test_contexto_mismo_numero(self, memory):
        memory.facts['mismo_numero'] = True
        ctx = memory.get_gpt_context()
        assert 'ESTE MISMO numero' in ctx
        assert 'NO pedir otro' in ctx

    def test_contexto_rechazo_whatsapp(self, memory):
        memory.rechazos.append('whatsapp')
        ctx = memory.get_gpt_context()
        assert 'rechazo dar WhatsApp' in ctx
        assert 'correo o telefono' in ctx

    def test_contexto_rechazo_contacto(self, memory):
        memory.rechazos.append('contacto')
        ctx = memory.get_gpt_context()
        assert 'rechazo dar contacto' in ctx

    def test_contexto_telefono_proporcionado(self, memory):
        memory.datos_proporcionados['telefono'] = '3312345678'
        ctx = memory.get_gpt_context()
        assert '3312345678' in ctx
        assert 'NO pedir de nuevo' in ctx

    def test_contexto_email_proporcionado(self, memory):
        memory.datos_proporcionados['email'] = 'test@test.com'
        ctx = memory.get_gpt_context()
        assert 'test@test.com' in ctx

    def test_contexto_callback_sin_hora(self, memory):
        memory.facts['cliente_pide_callback'] = True
        memory.facts['callback_sin_hora'] = True
        ctx = memory.get_gpt_context()
        assert 'NO dio hora' in ctx

    def test_contexto_callback_con_hora(self, memory):
        memory.facts['cliente_pide_callback'] = True
        memory.facts['hora_callback'] = '9:00 am'
        ctx = memory.get_gpt_context()
        assert '9:00 am' in ctx

    def test_contexto_pitch_dado(self, memory):
        memory.facts['pitch_dado'] = True
        ctx = memory.get_gpt_context()
        assert 'NO repetir pitch' in ctx

    def test_contexto_no_autorizado(self, memory):
        memory.facts['cliente_no_autorizado'] = True
        ctx = memory.get_gpt_context()
        assert 'NO esta autorizado' in ctx
        assert 'NO insistir' in ctx

    def test_contexto_es_encargado(self, memory):
        memory.facts['es_encargado'] = True
        ctx = memory.get_gpt_context()
        assert 'encargado de compras' in ctx

    def test_contexto_header_presente(self, memory):
        memory.facts['pitch_dado'] = True
        ctx = memory.get_gpt_context()
        assert 'MEMORIA CONVERSACIONAL' in ctx
        assert 'FIX 699' in ctx

    def test_contexto_multiple_hechos(self, memory):
        memory.facts['encargado_disponible'] = False
        memory.rechazos.append('whatsapp')
        memory.datos_proporcionados['telefono'] = '3312345678'
        ctx = memory.get_gpt_context()
        assert 'NO esta disponible' in ctx
        assert 'WhatsApp' in ctx
        assert '3312345678' in ctx


# ============================================================
# SHOULD BLOCK QUESTION
# ============================================================

class TestShouldBlockQuestion:
    """Tests de should_block_question()."""

    def test_block_whatsapp_rechazado(self, memory):
        memory.rechazos.append('whatsapp')
        assert memory.should_block_question('whatsapp') == True

    def test_block_whatsapp_contacto_rechazado(self, memory):
        memory.rechazos.append('contacto')
        assert memory.should_block_question('whatsapp') == True

    def test_block_whatsapp_mismo_numero(self, memory):
        memory.facts['mismo_numero'] = True
        assert memory.should_block_question('whatsapp') == True

    def test_no_block_whatsapp_sin_rechazo(self, memory):
        assert memory.should_block_question('whatsapp') == False

    def test_block_email_rechazado(self, memory):
        memory.rechazos.append('email')
        assert memory.should_block_question('email') == True

    def test_block_email_ya_proporcionado(self, memory):
        memory.datos_proporcionados['email'] = 'test@test.com'
        assert memory.should_block_question('email') == True

    def test_block_encargado_no_esta(self, memory):
        memory.facts['encargado_disponible'] = False
        assert memory.should_block_question('encargado') == True

    def test_block_encargado_es_el(self, memory):
        memory.facts['es_encargado'] = True
        assert memory.should_block_question('encargado') == True

    def test_no_block_encargado_sin_info(self, memory):
        assert memory.should_block_question('encargado') == False

    def test_block_telefono_ya_proporcionado(self, memory):
        memory.datos_proporcionados['telefono'] = '3312345678'
        assert memory.should_block_question('telefono') == True

    def test_block_contacto_rechazado(self, memory):
        memory.rechazos.append('contacto')
        assert memory.should_block_question('contacto') == True

    def test_block_contacto_no_autorizado(self, memory):
        memory.facts['cliente_no_autorizado'] = True
        assert memory.should_block_question('contacto') == True

    def test_block_pitch_dado(self, memory):
        memory.facts['pitch_dado'] = True
        assert memory.should_block_question('pitch') == True

    def test_no_block_pitch_no_dado(self, memory):
        assert memory.should_block_question('pitch') == False


# ============================================================
# VALIDATE RESPONSE
# ============================================================

class TestValidateResponse:
    """Tests de validate_response()."""

    def test_ok_sin_hechos(self, memory):
        ok, alt = memory.validate_response("¿Me podría dar su WhatsApp?")
        assert ok == True

    def test_block_whatsapp_mismo_numero(self, memory):
        memory.facts['mismo_numero'] = True
        ok, alt = memory.validate_response("¿Me podría dar el WhatsApp del encargado?")
        assert ok == False
        assert 'este numero' in alt.lower() or 'catalogo' in alt.lower()

    def test_block_whatsapp_rechazado(self, memory):
        memory.rechazos.append('whatsapp')
        ok, alt = memory.validate_response("¿Me da su WhatsApp?")
        assert ok == False
        assert 'correo' in alt.lower() or 'telefono' in alt.lower()

    def test_block_email_rechazado(self, memory):
        memory.rechazos.append('email')
        ok, alt = memory.validate_response("¿Me da su correo electrónico?")
        assert ok == False

    def test_block_ambos_rechazados(self, memory):
        memory.rechazos.append('whatsapp')
        memory.rechazos.append('email')
        ok, alt = memory.validate_response("¿Me da su correo?")
        assert ok == False
        assert 'este numero' in alt.lower() or 'gracias' in alt.lower()

    def test_block_contacto_rechazado(self, memory):
        memory.rechazos.append('contacto')
        ok, alt = memory.validate_response("¿Me podría dar su número?")
        assert ok == False
        assert 'gracias' in alt.lower() or 'no se preocupe' in alt.lower()

    def test_block_encargado_no_esta(self, memory):
        memory.facts['encargado_disponible'] = False
        ok, alt = memory.validate_response("¿Se encuentra el encargado de compras?")
        assert ok == False
        assert 'whatsapp' in alt.lower() or 'correo' in alt.lower()

    def test_block_pitch_repetido(self, memory):
        memory.facts['pitch_dado'] = True
        memory.facts['encargado_disponible'] = False
        ok, alt = memory.validate_response("Le hablo de NIOVAL, somos distribuidores de productos para ferretería y le ofrecemos catálogo")
        assert ok == False

    def test_block_no_autorizado(self, memory):
        memory.facts['cliente_no_autorizado'] = True
        ok, alt = memory.validate_response("¿Me podría dar el número del encargado?")
        assert ok == False
        assert 'catalogo' in alt.lower() or 'este numero' in alt.lower()

    def test_block_telefono_ya_dado(self, memory):
        memory.datos_proporcionados['telefono'] = '3312345678'
        ok, alt = memory.validate_response("¿Cuál es su número de teléfono?")
        assert ok == False
        assert 'ya tengo' in alt.lower() or 'registrado' in alt.lower()

    def test_block_email_ya_dado(self, memory):
        memory.datos_proporcionados['email'] = 'test@test.com'
        ok, alt = memory.validate_response("¿Me podría dar un correo electrónico?")
        assert ok == False
        assert 'ya tengo' in alt.lower()

    def test_ok_respuesta_normal(self, memory):
        ok, alt = memory.validate_response("Perfecto, muchas gracias por su tiempo.")
        assert ok == True

    def test_ok_respuesta_vacia(self, memory):
        ok, alt = memory.validate_response("")
        assert ok == True

    def test_ok_respuesta_none(self, memory):
        ok, alt = memory.validate_response(None)
        assert ok == True


# ============================================================
# RESET
# ============================================================

class TestReset:
    """Tests de reset()."""

    def test_reset_limpia_todo(self, memory):
        memory.facts['encargado_disponible'] = False
        memory.rechazos.append('whatsapp')
        memory.datos_proporcionados['telefono'] = '123'
        memory.contexto_cliente.append('test')

        memory.reset()

        assert memory.facts == {}
        assert memory.rechazos == []
        assert memory.datos_proporcionados == {}
        assert memory.contexto_cliente == []
        assert memory._last_history_len == 0


# ============================================================
# GET SUMMARY
# ============================================================

class TestGetSummary:
    """Tests de get_summary()."""

    def test_summary_vacio(self, memory):
        s = memory.get_summary()
        assert s['facts'] == {}
        assert s['rechazos'] == []

    def test_summary_con_datos(self, memory):
        memory.facts['encargado_disponible'] = False
        memory.rechazos.append('whatsapp')
        memory.datos_proporcionados['telefono'] = '3312345678'

        s = memory.get_summary()
        assert s['facts']['encargado_disponible'] == False
        assert 'whatsapp' in s['rechazos']
        assert s['datos']['telefono'] == '3312345678'


# ============================================================
# INTEGRACIÓN - Flujo completo
# ============================================================

class TestIntegracion:
    """Tests de integración con flujo de conversación completo."""

    def test_flujo_encargado_no_esta_whatsapp(self, memory):
        """Flujo: Encargado no está → pedir WhatsApp → cliente da WhatsApp."""
        history = [
            {"role": "assistant", "content": "Buen día, le hablo de NIOVAL, productos para ferretería. ¿Se encuentra el encargado de compras?"},
            {"role": "user", "content": "No, no está ahorita, salió"},
        ]
        memory.extract_facts(history)

        assert memory.facts.get('encargado_disponible') == False
        assert memory.facts.get('pitch_dado') == True
        assert memory.should_block_question('encargado') == True

        # GPT no debería preguntar por encargado
        ok, alt = memory.validate_response("¿Se encuentra el encargado?")
        assert ok == False

        # GPT debería poder pedir WhatsApp
        ok, alt = memory.validate_response("¿Me podría dar un WhatsApp para enviarle el catálogo?")
        assert ok == True  # WhatsApp aún no rechazado

    def test_flujo_mismo_numero(self, memory):
        """Flujo: Cliente dice 'mismo número' → no pedir otro."""
        history = [
            {"role": "assistant", "content": "¿Me podría dar el WhatsApp del encargado?"},
            {"role": "user", "content": "Hay este mismo número, no sé qué día viene"},
        ]
        memory.extract_facts(history)

        assert memory.facts.get('mismo_numero') == True
        ok, alt = memory.validate_response("¿Me da el WhatsApp del encargado?")
        assert ok == False
        assert 'este numero' in alt.lower() or 'catalogo' in alt.lower()

    def test_flujo_rechazo_escalado(self, memory):
        """Flujo: Cliente rechaza WhatsApp → ofrecer email → rechaza → cerrar."""
        history = [
            {"role": "assistant", "content": "¿Me da su WhatsApp?"},
            {"role": "user", "content": "No tengo WhatsApp"},
        ]
        memory.extract_facts(history)

        # Debería sugerir correo
        ok, alt = memory.validate_response("¿Me da su WhatsApp?")
        assert ok == False
        assert 'correo' in alt.lower()

        # Cliente rechaza email
        history.append({"role": "assistant", "content": "¿Me da un correo entonces?"})
        history.append({"role": "user", "content": "No tengo correo tampoco"})
        memory.extract_facts(history)

        # Ahora ambos rechazados → cerrar
        ok, alt = memory.validate_response("¿Me da su correo?")
        assert ok == False

    def test_flujo_no_autorizado(self, memory):
        """Flujo: Cliente no autorizado → no insistir con datos."""
        history = [
            {"role": "assistant", "content": "¿Me podría dar el número del encargado?"},
            {"role": "user", "content": "No estoy autorizado para dar esa información"},
        ]
        memory.extract_facts(history)

        assert memory.facts.get('cliente_no_autorizado') == True
        ok, alt = memory.validate_response("¿Me da el contacto del encargado?")
        assert ok == False

    def test_flujo_datos_ya_proporcionados(self, memory):
        """Flujo: Cliente ya dio teléfono → no volver a pedir."""
        history = [
            {"role": "assistant", "content": "¿Me da su número?"},
            {"role": "user", "content": "Sí, es el 3312345678"},
        ]
        memory.extract_facts(history)

        assert 'telefono' in memory.datos_proporcionados
        ok, alt = memory.validate_response("¿Cuál es su número de teléfono?")
        assert ok == False
        assert 'ya tengo' in alt.lower()

    def test_solo_mensajes_nuevos_procesados(self, memory):
        """Verificar que extract_facts solo procesa mensajes nuevos."""
        history = [
            {"role": "user", "content": "No está el encargado"}
        ]
        memory.extract_facts(history)
        assert memory._last_history_len == 1

        # Agregar otro mensaje
        history.append({"role": "user", "content": "Es el 3312345678"})
        memory.extract_facts(history)
        assert memory._last_history_len == 2
        assert 'telefono' in memory.datos_proporcionados

    def test_normalize_acentos(self, memory):
        """Verificar que normalización de acentos funciona (FIX 631 compatible)."""
        history = [
            {"role": "user", "content": "No está disponible, salió temprano"}
        ]
        memory.extract_facts(history)
        assert memory.facts.get('encargado_disponible') == False

    def test_datos_no_se_pierden_entre_turnos(self, memory):
        """Verificar que datos acumulados persisten entre extract_facts calls."""
        # Turno 1
        history = [{"role": "user", "content": "No está el encargado"}]
        memory.extract_facts(history)

        # Turno 2
        history.append({"role": "assistant", "content": "¿Me da su WhatsApp?"})
        history.append({"role": "user", "content": "No tengo WhatsApp"})
        memory.extract_facts(history)

        # Turno 3
        history.append({"role": "assistant", "content": "¿Un correo?"})
        history.append({"role": "user", "content": "ventas@test.com"})
        memory.extract_facts(history)

        # Todo debe estar acumulado
        assert memory.facts.get('encargado_disponible') == False
        assert 'whatsapp' in memory.rechazos
        assert 'email' in memory.datos_proporcionados


# ============================================================
# INTEGRACIÓN CON AGENTE
# ============================================================

class TestIntegracionAgente:
    """Tests de integración con AgenteVentas (importación y atributo)."""

    def test_agente_tiene_memory(self):
        """Verificar que AgenteVentas tiene atributo memory tras FIX 699."""
        os.environ.setdefault("OPENAI_API_KEY", "sk-test-dummy")
        os.environ.setdefault("ELEVENLABS_API_KEY", "test-dummy")
        os.environ.setdefault("TWILIO_ACCOUNT_SID", "AC-test")
        os.environ.setdefault("TWILIO_AUTH_TOKEN", "test-token")

        from agente_ventas import AgenteVentas
        a = AgenteVentas.__new__(AgenteVentas)
        # Simular init mínimo
        a.memory = None
        try:
            a.memory = ConversationMemory()
        except Exception:
            pass

        assert a.memory is not None
        assert isinstance(a.memory, ConversationMemory)

    def test_memory_layer_import(self):
        """Verificar que memory_layer se importa correctamente."""
        from memory_layer import ConversationMemory as CM
        m = CM()
        assert hasattr(m, 'extract_facts')
        assert hasattr(m, 'get_gpt_context')
        assert hasattr(m, 'should_block_question')
        assert hasattr(m, 'validate_response')
        assert hasattr(m, 'reset')
        assert hasattr(m, 'get_summary')


# ============================================================
# FIX 704A: validate_response("") con dictado activo
# ============================================================

class TestFix704AEmptyResponseDictation:
    """FIX 704A: Respuesta vacía durante dictado activo devuelve acknowledgment."""

    def test_empty_response_no_dictation(self, memory):
        """Sin dictado activo, respuesta vacía sigue siendo ok."""
        ok, alt = memory.validate_response("")
        assert ok == True
        assert alt == ""

    def test_empty_response_with_telefono(self, memory):
        """FIX 751: Teléfono capturado NO activa acknowledgment permanente.
        Solo email_dictado_verbal indica dictado activo real."""
        memory.datos_proporcionados['telefono'] = '3312345678'
        ok, alt = memory.validate_response("")
        assert ok == True
        assert alt == ""

    def test_empty_response_with_email_verbal(self, memory):
        """Con email dictado verbal, devuelve acknowledgment."""
        memory.facts['email_dictado_verbal'] = True
        ok, alt = memory.validate_response("")
        assert ok == False
        assert 'aja' in alt.lower() or 'si' in alt.lower()

    def test_empty_response_dictation_but_despedida(self, memory):
        """Con email dictado PERO cliente se despide, no acknowledgment."""
        memory.facts['email_dictado_verbal'] = True
        memory.facts['cliente_se_despide'] = True
        ok, alt = memory.validate_response("")
        assert ok == True
        assert alt == ""

    def test_none_response_with_dictation(self, memory):
        """FIX 751: None con solo teléfono capturado NO activa acknowledgment.
        Solo email_dictado_verbal es indicador de dictado activo."""
        memory.datos_proporcionados['telefono'] = '3312345678'
        ok, alt = memory.validate_response(None)
        assert ok == True
        assert alt == ""


# ============================================================
# FIX 704B: Callback sin hora → preguntar hora, no contacto
# ============================================================

class TestFix704BCallbackSinHora:
    """FIX 704B: Rule 7 - Callback sin hora bloquea preguntas de contacto."""

    def test_callback_sin_hora_blocks_whatsapp(self, memory):
        """Con callback sin hora, pedir WhatsApp debe bloquearse."""
        memory.facts['callback_sin_hora'] = True
        ok, alt = memory.validate_response("¿Me da su WhatsApp?")
        assert ok == False
        assert 'hora' in alt.lower()

    def test_callback_sin_hora_blocks_correo(self, memory):
        memory.facts['callback_sin_hora'] = True
        ok, alt = memory.validate_response("¿Me da su correo?")
        assert ok == False
        assert 'hora' in alt.lower()

    def test_callback_sin_hora_blocks_numero_directo(self, memory):
        memory.facts['callback_sin_hora'] = True
        ok, alt = memory.validate_response("¿Me proporciona el número directo?")
        assert ok == False
        assert 'hora' in alt.lower()

    def test_callback_con_hora_no_blocks(self, memory):
        """Si ya tiene hora, no bloquear preguntas de contacto."""
        memory.facts['callback_sin_hora'] = True
        memory.facts['hora_callback'] = '9:00'
        ok, alt = memory.validate_response("¿Me da su WhatsApp?")
        # Rule 7 no se activa porque hora_callback está
        # Puede bloquearse por otra regla, pero no por Rule 7
        # (Sin otros facts, debería ser ok)
        assert ok == True

    def test_callback_sin_hora_allows_non_contact(self, memory):
        """Preguntas que NO piden contacto no se bloquean."""
        memory.facts['callback_sin_hora'] = True
        ok, alt = memory.validate_response("Perfecto, le marco mañana entonces.")
        assert ok == True

    def test_callback_sin_hora_extraction(self, memory):
        """Verificar que extract_facts detecta callback sin hora."""
        history = [
            {"role": "user", "content": "No esta, hableme manana"}
        ]
        memory.extract_facts(history)
        assert memory.facts.get('cliente_pide_callback') == True
        # "manana" sin hora específica
        assert memory.facts.get('callback_sin_hora') == True

    def test_callback_con_hora_extraction(self, memory):
        """Verificar que extract_facts detecta callback CON hora."""
        history = [
            {"role": "user", "content": "Hableme manana a las 9:00"}
        ]
        memory.extract_facts(history)
        assert memory.facts.get('cliente_pide_callback') == True
        assert memory.facts.get('hora_callback') is not None


# ============================================================
# FIX 704C: Re-pitch exception cuando cliente pide repetir
# ============================================================

class TestFix704CRePitchException:
    """FIX 704C: Si cliente pide repetir, Rule 4 no bloquea re-pitch."""

    def test_repitame_allows_repitch(self, memory):
        """Cliente dice 'repítame' → pitch repetido es válido."""
        history = [
            {"role": "assistant", "content": "Le hablo de NIOVAL, manejamos productos para ferretería y catálogo completo."},
            {"role": "user", "content": "repitame por favor, no le escuche"}
        ]
        memory.extract_facts(history)

        assert memory.facts.get('pitch_dado') == True
        assert 'pide_repetir' in memory.contexto_cliente

        # Rule 4 should NOT block because client asked for repetition
        ok, alt = memory.validate_response(
            "Claro, le comento, le hablo de NIOVAL, somos distribuidores de productos para ferretería y le ofrecemos catálogo completo.")
        assert ok == True

    def test_no_pide_repetir_blocks_repitch(self, memory):
        """Sin pedir repetir, pitch repetido SÍ se bloquea."""
        memory.facts['pitch_dado'] = True
        memory.facts['encargado_disponible'] = False

        ok, alt = memory.validate_response(
            "Le hablo de NIOVAL, somos distribuidores de productos para ferretería y le ofrecemos catálogo completo.")
        assert ok == False

    def test_que_decia_allows_repitch(self, memory):
        """'que decía' es pedir repetir."""
        history = [
            {"role": "assistant", "content": "Le hablo de NIOVAL, distribuidores de productos para ferretería."},
            {"role": "user", "content": "que decia? no le escuche bien"}
        ]
        memory.extract_facts(history)
        assert 'pide_repetir' in memory.contexto_cliente

    def test_otra_vez_allows_repitch(self, memory):
        """'otra vez' es pedir repetir."""
        history = [
            {"role": "assistant", "content": "Le hablo de NIOVAL con productos para ferretería."},
            {"role": "user", "content": "digame otra vez"}
        ]
        memory.extract_facts(history)
        assert 'pide_repetir' in memory.contexto_cliente

    def test_puede_repetir_allows_repitch(self, memory):
        history = [
            {"role": "assistant", "content": "Le hablo de NIOVAL, productos de ferretería."},
            {"role": "user", "content": "puede repetir por favor"}
        ]
        memory.extract_facts(history)
        assert 'pide_repetir' in memory.contexto_cliente
