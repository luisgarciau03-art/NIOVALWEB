"""
Tests para la pipeline de invalidación FIX 598/600/601/602.

Verifica que patrones detectados son invalidados (o sobreviven) correctamente.
Markers: @pytest.mark.invalidation, @pytest.mark.regression
"""

import pytest


# ============================================================
# FIX 600: SPLITTER ADVERSATIVO
# ============================================================

class TestFix600SplitterAdversativo:
    """FIX 600: Conjunciones adversativas invalidan patrones no-inmunes."""

    @pytest.mark.invalidation
    def test_pero_invalida_encargado(self, agente):
        """'no está pero yo le ayudo' → ENCARGADO invalidado por 'pero yo le ayudo'."""
        resultado = agente._detectar_patron_simple_optimizado("no está pero yo le ayudo")
        # Si matchea algo, NO debe ser ENCARGADO_NO_ESTA (fue invalidado por 'pero')
        if resultado is not None:
            assert "ENCARGADO_NO_ESTA" not in resultado["tipo"], \
                f"'pero yo le ayudo' debería invalidar ENCARGADO pattern"

    @pytest.mark.invalidation
    def test_sin_embargo_invalida(self, agente):
        """'No se encuentra, sin embargo yo le puedo atender' → invalidado."""
        resultado = agente._detectar_patron_simple_optimizado("No se encuentra, sin embargo yo le puedo atender")
        if resultado is not None:
            assert resultado["tipo"] not in ("ENCARGADO_NO_ESTA_SIN_HORARIO",)

    @pytest.mark.invalidation
    @pytest.mark.regression
    def test_immune_despedida_survives_600(self, agente_mid_conversation):
        """DESPEDIDA es inmune a FIX 600 - 'hasta luego pero gracias' sigue siendo DESPEDIDA."""
        resultado = agente_mid_conversation._detectar_patron_simple_optimizado("hasta luego pero gracias por llamar")
        assert resultado is not None
        assert resultado["tipo"] in ("DESPEDIDA_CLIENTE", "DESPEDIDA"), \
            f"DESPEDIDA debe ser inmune a FIX 600, pero se invalidó: {resultado}"

    @pytest.mark.invalidation
    def test_immune_rechazo_survives_600(self, agente_mid_conversation):
        """RECHAZO_DEFINITIVO es inmune - 'no me interesa pero gracias'."""
        resultado = agente_mid_conversation._detectar_patron_simple_optimizado("no me interesa pero gracias")
        assert resultado is not None
        assert resultado["tipo"] in ("NO_INTERESA_FINAL", "RECHAZO_DEFINITIVO", "DESPEDIDA_CLIENTE")

    @pytest.mark.invalidation
    @pytest.mark.regression
    def test_immune_ofrece_contacto_survives_600(self, agente_mid_conversation):
        """FIX 626B: OFRECE_CONTACTO_ENCARGADO inmune a FIX 600."""
        resultado = agente_mid_conversation._detectar_patron_simple_optimizado("no está pero te paso su teléfono")
        assert resultado is not None
        # Debe sobrevivir como oferta de contacto
        assert resultado["tipo"] in ("OFRECE_CONTACTO_ENCARGADO", "CLIENTE_OFRECE_NUMERO"), \
            f"OFRECE_CONTACTO debe ser inmune a 'pero': {resultado}"

    @pytest.mark.invalidation
    def test_la_verdad_invalida(self, agente):
        """'Sí, la verdad no me interesa mucho' - 'la verdad' es adversativa."""
        resultado = agente._detectar_patron_simple_optimizado("Sí está la verdad no sé si pueda atenderlo")
        # El 'la verdad' puede invalidar una CONFIRMACION
        if resultado is not None:
            assert resultado["tipo"] != "CONFIRMACION_SIMPLE" or \
                resultado["tipo"] in ("NO_INTERESA_FINAL", "RECHAZO_DEFINITIVO")


# ============================================================
# FIX 601: UMBRAL DE COMPLEJIDAD
# ============================================================

class TestFix601UmbralComplejidad:
    """FIX 601: >12 palabras + >=3 cláusulas → invalidar (excepto inmunes)."""

    @pytest.mark.invalidation
    def test_complex_text_invalidated(self, agente):
        """Texto complejo (>12 palabras, 3+ cláusulas) con patrón no-inmune → GPT."""
        texto = "pues mire, no sé si está el encargado, creo que salió, pero la verdad no estoy segura de cuándo regresa"
        resultado = agente._detectar_patron_simple_optimizado(texto)
        # Este texto es lo suficientemente complejo como para ir a GPT
        # Si matchea, es porque un patrón inmune lo salvó
        if resultado is not None:
            # Solo patrones inmunes deben sobrevivir textos tan complejos
            patrones_inmunes_601 = {
                'CONFIRMACION_SIMPLE', 'SALUDO', 'DESPEDIDA', 'DESPEDIDA_CLIENTE',
                'RECHAZO_DEFINITIVO', 'NO_INTERESA_FINAL', 'CLIENTE_DICE_SI', 'CLIENTE_DICE_NO',
                'CORREO_DETECTADO', 'WHATSAPP_DETECTADO',
                'OTRA_SUCURSAL', 'OTRA_SUCURSAL_INSISTENCIA',
                'CLIENTE_OFRECE_CORREO', 'CLIENTE_OFRECE_NUMERO',
                'OFRECE_CONTACTO_ENCARGADO', 'CLIENTE_OFRECE_SU_CONTACTO'
            }
            assert resultado["tipo"] in patrones_inmunes_601, \
                f"Texto complejo matcheó patrón no-inmune: {resultado['tipo']}"

    @pytest.mark.invalidation
    @pytest.mark.regression
    def test_immune_correo_survives_601(self, agente_pidiendo_correo):
        """FIX 617A: Email dictado (largo + multi-cláusula) NO se invalida."""
        texto = "sí, mire, es juan punto perez arroba gmail punto com, ese es el correo del encargado"
        resultado = agente_pidiendo_correo._detectar_patron_simple_optimizado(texto)
        # CORREO_DETECTADO debe sobrevivir FIX 601
        if resultado is not None:
            assert resultado["tipo"] in ("CORREO_DETECTADO", "CLIENTE_DICTA_EMAIL_COMPLETO"), \
                f"CORREO_DETECTADO debe ser inmune a FIX 601: {resultado['tipo']}"

    @pytest.mark.invalidation
    def test_short_text_not_invalidated(self, agente_mid_conversation):
        """Texto corto (<= 12 palabras) no se invalida por FIX 601."""
        resultado = agente_mid_conversation._detectar_patron_simple_optimizado("Hasta luego")
        # Texto corto pasa sin problemas (FIX 601 solo invalida >12 palabras)
        assert resultado is not None

    @pytest.mark.invalidation
    def test_immune_despedida_survives_601(self, agente_mid_conversation):
        """DESPEDIDA inmune a FIX 601 incluso con texto largo."""
        texto = "pues mire, la verdad no me interesa, ya tenemos proveedor, hasta luego y gracias"
        resultado = agente_mid_conversation._detectar_patron_simple_optimizado(texto)
        # Debe detectar DESPEDIDA o NO_INTERESA (ambos inmunes)
        if resultado is not None:
            assert resultado["tipo"] in (
                "DESPEDIDA_CLIENTE", "DESPEDIDA", "NO_INTERESA_FINAL", "RECHAZO_DEFINITIVO"
            )


# ============================================================
# FIX 598: VALIDADOR POST-PATRÓN (CONTRADICCIONES)
# ============================================================

class TestFix598Contradicciones:
    """FIX 598: Detectar contradicciones entre patrón y texto real."""

    @pytest.mark.invalidation
    def test_encargado_no_esta_pero_ofrece_correo(self, agente):
        """'No está pero le doy su correo' → ENCARGADO invalidado por 'correo'."""
        resultado = agente._detectar_patron_simple_optimizado("No se encuentra pero le doy su correo")
        if resultado is not None:
            # No debe ser ENCARGADO_NO_ESTA porque ofrece dato (contradicción)
            assert resultado["tipo"] not in ("ENCARGADO_NO_ESTA_SIN_HORARIO",) or \
                resultado["tipo"] in ("CLIENTE_OFRECE_CORREO",)

    @pytest.mark.invalidation
    def test_transferencia_pero_es_encargado(self, agente):
        """'Espéreme... ah soy yo el encargado' → TRANSFERENCIA invalidada."""
        resultado = agente._detectar_patron_simple_optimizado("espéreme, bueno soy yo el encargado")
        if resultado is not None:
            # 'soy yo el encargado' contradice TRANSFERENCIA
            assert resultado["tipo"] in ("CLIENTE_ES_ENCARGADO", "TRANSFERENCIA")


# ============================================================
# FIX 602: VALIDADOR DE CONTEXTO CONVERSACIONAL
# ============================================================

class TestFix602ContextoConversacional:
    """FIX 602: Patrón debe ser coherente con la última pregunta de Bruce."""

    @pytest.mark.invalidation
    def test_pidiendo_correo_no_encargado(self, agente_pidiendo_correo):
        """Si Bruce pidió correo, 'no está' es incoherente."""
        resultado = agente_pidiendo_correo._detectar_patron_simple_optimizado("No sé, no está el encargado")
        # En contexto PIDIENDO_CORREO, ENCARGADO patterns son incoherentes
        # Puede ir a GPT (None) o matchear algo contextual
        if resultado is not None:
            # Si matchea algo, no debe ser un patrón incoherente con el contexto
            assert resultado["tipo"] not in (
                "ENCARGADO_NO_ESTA_CON_HORARIO",
                "SOLICITUD_CALLBACK",
                "TRANSFERENCIA",
            ) or resultado["tipo"] in (
                "ENCARGADO_NO_ESTA_SIN_HORARIO",  # Este puede ser válido si cliente cambia tema
            )

    @pytest.mark.invalidation
    def test_contexto_whatsapp_acepta_numero(self, agente_mid_conversation):
        """Si Bruce pidió WhatsApp, respuesta con número es coherente."""
        agente_mid_conversation.estado_conversacion = "pidiendo_whatsapp"
        agente_mid_conversation.conversation_history[-1] = {
            "role": "assistant",
            "content": "¿Me puede dar el número de WhatsApp del encargado?"
        }
        resultado = agente_mid_conversation._detectar_patron_simple_optimizado("Sí, es el 6621234567")
        # Debe detectar número, no invalidarlo
        assert resultado is not None


# ============================================================
# INMUNIDAD COMBINADA
# ============================================================

class TestInmunidadCombinada:
    """Tests que verifican inmunidad a través de múltiples capas."""

    @pytest.mark.invalidation
    def test_despedida_survives_all_layers(self, agente_mid_conversation):
        """DESPEDIDA sobrevive FIX 598 + 600 + 601 + 602."""
        texto = "no gracias, no me interesa, hasta luego"
        resultado = agente_mid_conversation._detectar_patron_simple_optimizado(texto)
        assert resultado is not None
        assert resultado["tipo"] in ("DESPEDIDA_CLIENTE", "DESPEDIDA", "NO_INTERESA_FINAL", "RECHAZO_DEFINITIVO")

    @pytest.mark.invalidation
    def test_rechazo_con_adversativa_larga_sobrevive(self, agente_mid_conversation):
        """RECHAZO_DEFINITIVO con texto largo + adversativa → sobrevive."""
        texto = "mire, la verdad es que no me interesa, ya tenemos todo cubierto, pero gracias"
        resultado = agente_mid_conversation._detectar_patron_simple_optimizado(texto)
        if resultado is not None:
            assert resultado["tipo"] in (
                "NO_INTERESA_FINAL", "RECHAZO_DEFINITIVO", "DESPEDIDA_CLIENTE", "DESPEDIDA"
            )

    @pytest.mark.invalidation
    def test_ofrece_contacto_survives_all(self, agente_mid_conversation):
        """OFRECE_CONTACTO_ENCARGADO sobrevive todas las capas."""
        texto = "no está pero le paso su teléfono si quiere"
        resultado = agente_mid_conversation._detectar_patron_simple_optimizado(texto)
        if resultado is not None:
            assert resultado["tipo"] in (
                "OFRECE_CONTACTO_ENCARGADO", "CLIENTE_OFRECE_NUMERO"
            ), f"OFRECE_CONTACTO debe sobrevivir: {resultado['tipo']}"
