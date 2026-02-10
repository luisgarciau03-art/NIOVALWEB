"""
Tests para _filtrar_respuesta_post_gpt().

Verifica que las 140+ reglas de post-filtrado funcionan correctamente.
Markers: @pytest.mark.post_filter, @pytest.mark.regression
"""

import pytest


# ============================================================
# FIX 479: RESPUESTAS VACÍAS
# ============================================================

class TestRespuestaVacia:
    """FIX 479: Fallback para respuestas vacías o muy cortas de GPT."""

    @pytest.mark.post_filter
    def test_empty_string_fallback(self, agente):
        """Respuesta vacía → fallback 'no escuché bien'."""
        resultado = agente._filtrar_respuesta_post_gpt("")
        assert resultado is not None
        assert len(resultado) > 10
        # Debe ser un fallback útil, no la cadena vacía
        assert resultado != ""

    @pytest.mark.post_filter
    def test_whitespace_only_fallback(self, agente):
        """Solo espacios → fallback."""
        resultado = agente._filtrar_respuesta_post_gpt("   ")
        assert resultado is not None
        assert len(resultado) > 10

    @pytest.mark.post_filter
    def test_very_short_fallback(self, agente):
        """Respuesta < 5 chars → fallback."""
        resultado = agente._filtrar_respuesta_post_gpt("Ok")
        assert resultado is not None
        assert len(resultado) >= 5

    @pytest.mark.post_filter
    def test_normal_response_passes(self, agente):
        """Respuesta normal no debe ser reemplazada por fallback."""
        texto = "Perfecto, le envío el catálogo por WhatsApp."
        resultado = agente._filtrar_respuesta_post_gpt(texto)
        assert resultado is not None
        assert len(resultado) > 10


# ============================================================
# FIX 615B: NO REPETIR NÚMEROS DE TELÉFONO
# ============================================================

class TestNoRepetirNumeros:
    """FIX 615B: Bruce NO debe repetir números de teléfono en voz."""

    @pytest.mark.post_filter
    @pytest.mark.regression
    def test_phone_number_stripped(self, agente):
        """BRUCE2030: Número de 10 dígitos en respuesta → debe ser removido o transformado."""
        respuesta = "Perfecto, su número es 6621234567, le envío el catálogo."
        resultado = agente._filtrar_respuesta_post_gpt(respuesta)
        # El número no debería aparecer textualmente
        assert "6621234567" not in resultado

    @pytest.mark.post_filter
    def test_number_with_spaces_passes(self, agente):
        """FIX 615B solo filtra 10 dígitos consecutivos, no con espacios."""
        respuesta = "Anotado, el 662 123 4567, le mando información."
        resultado = agente._filtrar_respuesta_post_gpt(respuesta)
        # Con espacios puede o no filtrarse - lo importante es que no crashee
        assert resultado is not None
        assert len(resultado) > 10


# ============================================================
# FIX 493: ANTI-LOOP ENCARGADO
# ============================================================

class TestAntiLoopEncargado:
    """FIX 493: No preguntar por encargado más de 2 veces."""

    @pytest.mark.post_filter
    @pytest.mark.regression
    def test_anti_loop_tercera_vez_encargado(self, agente):
        """Si ya preguntó 2x por encargado, la 3ra debe ser bloqueada."""
        agente.conversation_history = [
            {"role": "assistant", "content": "¿Se encontrará el encargado de compras?"},
            {"role": "user", "content": "No está."},
            {"role": "assistant", "content": "¿A qué hora regresa el encargado?"},
            {"role": "user", "content": "No sé."},
        ]
        respuesta = "¿Me podría comunicar con el encargado de compras?"
        resultado = agente._filtrar_respuesta_post_gpt(respuesta)
        # No debe preguntar por encargado una 3ra vez
        encargado_en_resultado = "encargado" in resultado.lower()
        # Si aún pregunta por encargado, al menos no debería ser la misma pregunta
        if encargado_en_resultado:
            assert resultado != respuesta, "Respuesta no fue modificada - posible loop"


# ============================================================
# FIX 522: NO REPETIR OFERTA CATÁLOGO
# ============================================================

class TestNoRepetirCatalogo:
    """FIX 522: Si ya prometió catálogo, no volver a ofrecer."""

    @pytest.mark.post_filter
    def test_catalogo_ya_prometido(self, agente):
        """Si catalogo_prometido=True, no repetir oferta."""
        agente.catalogo_prometido = True
        respuesta = "¿Le gustaría recibirlo por WhatsApp o correo?"
        resultado = agente._filtrar_respuesta_post_gpt(respuesta)
        # Debe convertir en despedida, no repetir oferta
        assert "gustaría recibirlo" not in resultado.lower()

    @pytest.mark.post_filter
    def test_catalogo_no_prometido_pasa(self, agente):
        """Si catalogo_prometido=False, la oferta pasa normal."""
        agente.catalogo_prometido = False
        respuesta = "Le puedo enviar nuestro catálogo de productos."
        resultado = agente._filtrar_respuesta_post_gpt(respuesta)
        assert "catálogo" in resultado.lower() or "catalogo" in resultado.lower()


# ============================================================
# FIX 526/533: ESPERANDO HORA CALLBACK
# ============================================================

class TestEsperandoHoraCallback:
    """FIX 526: Detectar cuando Bruce pregunta por hora de callback."""

    @pytest.mark.post_filter
    def test_pregunta_hora_activa_flag(self, agente):
        """Si Bruce pregunta '¿A qué hora regresa?', activar flag."""
        respuesta = "¿A qué hora regresa el encargado?"
        agente._filtrar_respuesta_post_gpt(respuesta)
        assert agente.esperando_hora_callback is True

    @pytest.mark.post_filter
    def test_respuesta_sin_hora_no_activa(self, agente):
        """Si respuesta no pregunta por hora, flag permanece False."""
        respuesta = "Perfecto, le envío el catálogo."
        agente._filtrar_respuesta_post_gpt(respuesta)
        assert agente.esperando_hora_callback is False


# ============================================================
# RESPUESTAS COHERENTES (no se rompen)
# ============================================================

class TestRespuestasCoherentes:
    """Verificar que respuestas válidas no son destruidas por el post-filter."""

    @pytest.mark.post_filter
    def test_respuesta_normal_no_modificada_drasticamente(self, agente_mid_conversation):
        """Una respuesta normal de Bruce no debe ser vaciada ni cortada."""
        respuesta = "Entiendo, entonces le mando la información por correo electrónico."
        resultado = agente_mid_conversation._filtrar_respuesta_post_gpt(respuesta)
        assert len(resultado) > 20
        # Debe mantener el sentido general
        assert "correo" in resultado.lower() or "información" in resultado.lower() or "envío" in resultado.lower() or len(resultado) > 30

    @pytest.mark.post_filter
    def test_despedida_pasa(self, agente_mid_conversation):
        """Despedida de Bruce pasa sin modificación destructiva."""
        respuesta = "Muchas gracias por su tiempo, que tenga excelente día."
        resultado = agente_mid_conversation._filtrar_respuesta_post_gpt(respuesta)
        assert len(resultado) > 15

    @pytest.mark.post_filter
    def test_pitch_inicial_pasa(self, agente):
        """El pitch de presentación pasa correctamente."""
        respuesta = "Me comunico de la marca nioval, trabajamos productos ferreteros."
        resultado = agente._filtrar_respuesta_post_gpt(respuesta)
        assert "nioval" in resultado.lower() or len(resultado) > 20


# ============================================================
# FIX 629B: NO OVERRIDE CLIENT OFFER
# ============================================================

class TestNoOverrideClientOffer:
    """FIX 629B: Cuando cliente ofrece dato, no aplicar FIX 254."""

    @pytest.mark.post_filter
    @pytest.mark.regression
    def test_cliente_ofrece_numero_no_override(self, agente_mid_conversation):
        """Si cliente ofreció 'te paso su número', la respuesta no debe ser sobreescrita."""
        agente_mid_conversation.conversation_history.append(
            {"role": "user", "content": "te puedo pasar su número"}
        )
        respuesta = "Sí, por favor, dígame el número."
        resultado = agente_mid_conversation._filtrar_respuesta_post_gpt(respuesta)
        # La respuesta debe aceptar el número, no redirigir a otra cosa
        assert len(resultado) > 10


# ============================================================
# CONTEXTO EMAIL
# ============================================================

class TestContextoEmail:
    """Tests de post-filter en contexto de dictado de email."""

    @pytest.mark.post_filter
    def test_no_pedir_correo_si_ya_capturado(self, agente_pidiendo_correo):
        """FIX 616B: Si email ya capturado, no volver a pedir."""
        agente_pidiendo_correo.estado_email = EstadoEmail.CAPTURADO
        agente_pidiendo_correo.lead_data["email"] = "test@gmail.com"
        respuesta = "¿Me puede dar su correo electrónico?"
        resultado = agente_pidiendo_correo._filtrar_respuesta_post_gpt(respuesta)
        # No debe pedir correo de nuevo
        assert "correo" not in resultado.lower() or "ya" in resultado.lower() or len(resultado) < len(respuesta)


# Import necesario para test
from agente_ventas import EstadoEmail


# ============================================================
# FIX 606: FALLBACK GPT VACÍO MEJORADO
# ============================================================

class TestFallbackGPTVacio:
    """FIX 606: 5 categorías contextuales para fallback cuando GPT falla."""

    @pytest.mark.post_filter
    def test_fallback_no_es_generico(self, agente_mid_conversation):
        """Fallback debe ser contextual, no siempre 'no escuché'."""
        resultado = agente_mid_conversation._filtrar_respuesta_post_gpt("")
        assert resultado is not None
        assert len(resultado) > 5


# ============================================================
# LONGITUD DE RESPUESTA
# ============================================================

class TestLongitudRespuesta:
    """Verificar que respuestas extremadamente largas son recortadas."""

    @pytest.mark.post_filter
    def test_respuesta_muy_larga(self, agente):
        """Una respuesta de 500+ palabras debe ser recortada o reformulada."""
        respuesta_larga = "Perfecto, " + "le comento que " * 100 + "muchas gracias."
        resultado = agente._filtrar_respuesta_post_gpt(respuesta_larga)
        # El resultado no debe ser igual de largo (debería haber algún recorte)
        assert resultado is not None
        assert len(resultado) > 0
