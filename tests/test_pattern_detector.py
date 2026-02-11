"""
Tests para _detectar_patron_simple_optimizado().

Cada test está basado en un BRUCE#### real de producción.
Markers: @pytest.mark.pattern_detector, @pytest.mark.regression

NOTA: Muchos patrones requieren contexto conversacional (conversation_history)
para funcionar. Los patrones de ENCARGADO necesitan que Bruce haya preguntado
por el encargado primero. Los patrones de CONFIRMACION necesitan conversación activa.
"""

import pytest


# ============================================================
# DESPEDIDA / RECHAZO
# ============================================================

class TestDespedida:
    """Tests para patrones de despedida del cliente."""

    @pytest.mark.pattern_detector
    def test_despedida_fuerte_larga(self, agente_mid_conversation):
        """BRUCE2063: 'Hasta luego, oiga, Hasta luego indra.' → DESPEDIDA_CLIENTE"""
        resultado = agente_mid_conversation._detectar_patron_simple_optimizado("Hasta luego, oiga, Hasta luego indra.")
        assert resultado is not None
        assert resultado["tipo"] in ("DESPEDIDA_CLIENTE", "DESPEDIDA")

    @pytest.mark.pattern_detector
    def test_despedida_simple(self, agente_mid_conversation):
        """Despedida clásica corta."""
        resultado = agente_mid_conversation._detectar_patron_simple_optimizado("Hasta luego")
        assert resultado is not None
        assert resultado["tipo"] in ("DESPEDIDA_CLIENTE", "DESPEDIDA")

    @pytest.mark.pattern_detector
    def test_adios(self, agente_mid_conversation):
        resultado = agente_mid_conversation._detectar_patron_simple_optimizado("Adiós")
        assert resultado is not None
        assert resultado["tipo"] in ("DESPEDIDA_CLIENTE", "DESPEDIDA")

    @pytest.mark.pattern_detector
    def test_que_le_vaya_bien(self, agente_mid_conversation):
        """'Que le vaya bien' puede ir a GPT en ciertos contextos."""
        resultado = agente_mid_conversation._detectar_patron_simple_optimizado("Hasta luego, que le vaya bien")
        assert resultado is not None
        assert resultado["tipo"] in ("DESPEDIDA_CLIENTE", "DESPEDIDA")

    @pytest.mark.pattern_detector
    def test_gracias_buen_dia(self, agente_mid_conversation):
        resultado = agente_mid_conversation._detectar_patron_simple_optimizado("Gracias, buen día")
        assert resultado is not None
        assert resultado["tipo"] in ("DESPEDIDA_CLIENTE", "DESPEDIDA")

    @pytest.mark.pattern_detector
    def test_no_gracias_bye(self, agente_mid_conversation):
        resultado = agente_mid_conversation._detectar_patron_simple_optimizado("No gracias, bye")
        assert resultado is not None
        assert resultado["tipo"] in ("DESPEDIDA_CLIENTE", "DESPEDIDA", "NO_INTERESA_FINAL", "RECHAZO_DEFINITIVO")


class TestRechazoDefinitivo:
    """Tests para rechazo definitivo / no interesado."""

    @pytest.mark.pattern_detector
    def test_no_interesa_fuerte(self, agente_mid_conversation):
        """'No me interesa, gracias' con despedida implícita."""
        resultado = agente_mid_conversation._detectar_patron_simple_optimizado("No, no me interesa, gracias")
        assert resultado is not None
        assert resultado["tipo"] in ("NO_INTERESA_FINAL", "RECHAZO_DEFINITIVO", "DESPEDIDA_CLIENTE")

    @pytest.mark.pattern_detector
    def test_no_gracias_no_interesa(self, agente_mid_conversation):
        resultado = agente_mid_conversation._detectar_patron_simple_optimizado("No gracias, no me interesa")
        assert resultado is not None
        assert resultado["tipo"] in ("NO_INTERESA_FINAL", "RECHAZO_DEFINITIVO", "DESPEDIDA_CLIENTE")

    @pytest.mark.pattern_detector
    def test_no_necesitamos_nada(self, agente_mid_conversation):
        resultado = agente_mid_conversation._detectar_patron_simple_optimizado("No necesitamos nada, gracias")
        assert resultado is not None
        # Puede detectarse como despedida o rechazo
        assert resultado["tipo"] in ("NO_INTERESA_FINAL", "RECHAZO_DEFINITIVO", "DESPEDIDA_CLIENTE")


# ============================================================
# ENCARGADO NO ESTÁ (requiere contexto de pregunta por encargado)
# ============================================================

class TestEncargadoNoEsta:
    """Tests para cuando el encargado no está disponible.

    NOTA: Estos patrones requieren que Bruce haya preguntado por el encargado
    en la conversación previa (FIX 493 verifica esto).
    """

    @pytest.fixture
    def agente_pregunto_encargado(self, agente):
        """Agente que ya preguntó por el encargado."""
        agente.conversation_history = [
            {"role": "assistant", "content": "Me comunico de la marca nioval, ¿se encontrará el encargado de compras?"},
        ]
        agente.segunda_parte_saludo_dicha = True
        return agente

    @pytest.mark.pattern_detector
    @pytest.mark.regression
    def test_no_se_encuentra(self, agente_pregunto_encargado):
        """Patrón más común en producción (55 matches)."""
        resultado = agente_pregunto_encargado._detectar_patron_simple_optimizado("No, no se encuentra")
        assert resultado is not None
        assert "ENCARGADO" in resultado["tipo"]

    @pytest.mark.pattern_detector
    def test_no_esta(self, agente_pregunto_encargado):
        resultado = agente_pregunto_encargado._detectar_patron_simple_optimizado("No está")
        assert resultado is not None

    @pytest.mark.pattern_detector
    def test_salio(self, agente_pregunto_encargado):
        resultado = agente_pregunto_encargado._detectar_patron_simple_optimizado("Salió, no está ahorita")
        assert resultado is not None

    @pytest.mark.pattern_detector
    def test_no_esta_con_horario(self, agente_pregunto_encargado):
        """Con horario: 'No está, llega a las 3'."""
        resultado = agente_pregunto_encargado._detectar_patron_simple_optimizado("No está, llega a las 3")
        assert resultado is not None
        assert resultado["tipo"] in ("ENCARGADO_NO_ESTA_CON_HORARIO", "ENCARGADO_LLEGA_MAS_TARDE")

    @pytest.mark.pattern_detector
    def test_llega_mas_tarde(self, agente_pregunto_encargado):
        resultado = agente_pregunto_encargado._detectar_patron_simple_optimizado("Llega más tarde")
        assert resultado is not None
        assert resultado["tipo"] in ("ENCARGADO_LLEGA_MAS_TARDE", "ENCARGADO_NO_ESTA_CON_HORARIO",
                                     "ENCARGADO_NO_ESTA_SIN_HORARIO")

    @pytest.mark.pattern_detector
    def test_todavia_no_llega(self, agente_pregunto_encargado):
        resultado = agente_pregunto_encargado._detectar_patron_simple_optimizado("Todavía no llega")
        assert resultado is not None


# ============================================================
# CLIENTE ES ENCARGADO
# ============================================================

class TestClienteEsEncargado:
    """Tests para cuando el cliente SE IDENTIFICA como encargado."""

    @pytest.mark.pattern_detector
    def test_yo_soy(self, agente):
        resultado = agente._detectar_patron_simple_optimizado("Yo soy")
        assert resultado is not None
        assert resultado["tipo"] == "CLIENTE_ES_ENCARGADO"

    @pytest.mark.pattern_detector
    def test_soy_el_encargado(self, agente):
        resultado = agente._detectar_patron_simple_optimizado("Soy el encargado")
        assert resultado is not None
        assert resultado["tipo"] == "CLIENTE_ES_ENCARGADO"

    @pytest.mark.pattern_detector
    def test_conmigo(self, agente):
        resultado = agente._detectar_patron_simple_optimizado("Conmigo")
        assert resultado is not None
        assert resultado["tipo"] == "CLIENTE_ES_ENCARGADO"

    @pytest.mark.pattern_detector
    def test_yo_mero(self, agente):
        resultado = agente._detectar_patron_simple_optimizado("Yo mero")
        assert resultado is not None
        assert resultado["tipo"] == "CLIENTE_ES_ENCARGADO"

    @pytest.mark.pattern_detector
    def test_soy_la_duena(self, agente):
        resultado = agente._detectar_patron_simple_optimizado("Soy la dueña")
        assert resultado is not None
        assert resultado["tipo"] == "CLIENTE_ES_ENCARGADO"


# ============================================================
# OFERTAS DE CONTACTO
# ============================================================

class TestOfertaContacto:
    """Tests para cuando el cliente OFRECE un dato de contacto."""

    @pytest.mark.pattern_detector
    @pytest.mark.regression
    def test_ofrece_contacto_encargado(self, agente_mid_conversation):
        """BRUCE2060: 'te paso su teléfono' → OFRECE_CONTACTO_ENCARGADO (FIX 626B)"""
        resultado = agente_mid_conversation._detectar_patron_simple_optimizado("te paso su teléfono")
        assert resultado is not None
        assert resultado["tipo"] in ("OFRECE_CONTACTO_ENCARGADO", "CLIENTE_OFRECE_NUMERO")

    @pytest.mark.pattern_detector
    @pytest.mark.regression
    def test_ofrece_su_contacto(self, agente_mid_conversation):
        """BRUCE2058: 'te puedo pasar mi teléfono' → CLIENTE_OFRECE_SU_CONTACTO (FIX 625A)"""
        resultado = agente_mid_conversation._detectar_patron_simple_optimizado("te puedo pasar mi teléfono")
        assert resultado is not None
        assert resultado["tipo"] in ("CLIENTE_OFRECE_SU_CONTACTO", "CLIENTE_OFRECE_NUMERO")

    @pytest.mark.pattern_detector
    def test_le_doy_el_correo(self, agente_mid_conversation):
        """'Le doy el correo' puede matchear ACEPTA o OFRECE."""
        resultado = agente_mid_conversation._detectar_patron_simple_optimizado("Le doy el correo")
        assert resultado is not None
        assert resultado["tipo"] in ("CLIENTE_OFRECE_CORREO", "CLIENTE_ACEPTA_CORREO")

    @pytest.mark.pattern_detector
    def test_le_paso_el_whatsapp(self, agente_mid_conversation):
        """'Le paso el WhatsApp' puede matchear ACEPTA o OFRECE."""
        resultado = agente_mid_conversation._detectar_patron_simple_optimizado("Le paso el WhatsApp")
        assert resultado is not None
        assert resultado["tipo"] in ("CLIENTE_OFRECE_WHATSAPP", "CLIENTE_OFRECE_NUMERO",
                                     "OFRECE_CONTACTO_ENCARGADO", "CLIENTE_ACEPTA_WHATSAPP")

    @pytest.mark.pattern_detector
    @pytest.mark.regression
    def test_truncated_offer(self, agente_mid_conversation):
        """BRUCE2062: Oferta truncada 'Quieres que te pase su'."""
        resultado = agente_mid_conversation._detectar_patron_simple_optimizado("Quieres que te pase su")
        # Puede matchear o ir a GPT - lo importante es que NO sea TRANSFERENCIA
        if resultado is not None:
            assert resultado["tipo"] != "TRANSFERENCIA"


# ============================================================
# FALSE POSITIVES - NO debe matchear patrón incorrecto
# ============================================================

class TestFalsePositives:
    """Tests que verifican que NO se detectan patrones incorrectos."""

    @pytest.mark.pattern_detector
    @pytest.mark.regression
    def test_no_escuche_no_es_correccion(self, agente_mid_conversation):
        """BRUCE2031 FIX 616A: 'no escuché bien' NO es CORRECCION."""
        resultado = agente_mid_conversation._detectar_patron_simple_optimizado("no escuché bien")
        if resultado is not None:
            assert resultado["tipo"] != "CORRECCION", \
                f"'no escuché bien' matcheó CORRECCION (debería ser CONFUSION o None)"

    @pytest.mark.pattern_detector
    @pytest.mark.regression
    def test_te_lo_paso_con_numero_no_transferencia(self, agente_mid_conversation):
        """BRUCE2030 FIX 615A: 'te lo paso, es el 662...' NO es TRANSFERENCIA."""
        resultado = agente_mid_conversation._detectar_patron_simple_optimizado("te lo paso, es el 6621234567")
        if resultado is not None:
            assert resultado["tipo"] != "TRANSFERENCIA", \
                f"'te lo paso + número' matcheó TRANSFERENCIA incorrectamente"

    @pytest.mark.pattern_detector
    @pytest.mark.regression
    def test_negacion_modal_no_transferencia(self, agente_mid_conversation):
        """BRUCE2029 FIX 614: 'no necesitaría esperar' NO debe activar 'Claro, espero'."""
        resultado = agente_mid_conversation._detectar_patron_simple_optimizado("no necesitaría esperar")
        if resultado is not None:
            assert resultado["tipo"] != "TRANSFERENCIA"

    @pytest.mark.pattern_detector
    @pytest.mark.regression
    def test_le_paso_un_telefono_no_transferencia(self, agente_mid_conversation):
        """BRUCE2041 FIX 622A: 'le paso un teléfono' = OFRECE dato, NO transferencia."""
        resultado = agente_mid_conversation._detectar_patron_simple_optimizado("le paso un teléfono")
        if resultado is not None:
            assert resultado["tipo"] != "TRANSFERENCIA", \
                f"'le paso un teléfono' matcheó TRANSFERENCIA (debe ser oferta de dato)"


# ============================================================
# CORREO / EMAIL
# ============================================================

class TestCorreo:
    """Tests para detección de correo electrónico."""

    @pytest.mark.pattern_detector
    @pytest.mark.regression
    def test_arroba_verbal(self, agente_pidiendo_correo):
        """BRUCE2032 FIX 617B: 'juan arroba gmail punto com' → CORREO_DETECTADO."""
        resultado = agente_pidiendo_correo._detectar_patron_simple_optimizado("juan arroba gmail punto com")
        assert resultado is not None
        assert resultado["tipo"] in ("CORREO_DETECTADO", "CLIENTE_DICTA_EMAIL_COMPLETO")

    @pytest.mark.pattern_detector
    def test_email_literal(self, agente_pidiendo_correo):
        """Email con @ literal."""
        resultado = agente_pidiendo_correo._detectar_patron_simple_optimizado("es juan@gmail.com")
        assert resultado is not None
        assert resultado["tipo"] in ("CORREO_DETECTADO", "CLIENTE_DICTA_EMAIL_COMPLETO")

    @pytest.mark.pattern_detector
    def test_ofrece_correo(self, agente_mid_conversation):
        resultado = agente_mid_conversation._detectar_patron_simple_optimizado("Le doy un correo")
        assert resultado is not None
        assert resultado["tipo"] in ("CLIENTE_OFRECE_CORREO",)


# ============================================================
# VERIFICACIÓN DE CONEXIÓN
# ============================================================

class TestVerificacionConexion:
    """Tests para '¿Bueno?' y 'Diga' como verificación de conexión."""

    @pytest.mark.pattern_detector
    def test_bueno_pregunta(self, agente):
        resultado = agente._detectar_patron_simple_optimizado("¿Bueno?")
        assert resultado is not None
        assert resultado["tipo"] in ("VERIFICACION_CONEXION", "VERIFICACION_CONEXION_REPETIR", "SALUDO_INICIAL")

    @pytest.mark.pattern_detector
    @pytest.mark.regression
    def test_diga_after_question(self, agente_mid_conversation):
        """BRUCE2049 FIX 621B: 'Diga' después de pregunta Bruce → repetir pregunta."""
        # Simular que Bruce hizo una pregunta (termina en ?)
        agente_mid_conversation.conversation_history[-1] = {
            "role": "assistant",
            "content": "¿Me podría proporcionar el WhatsApp del encargado?"
        }
        resultado = agente_mid_conversation._detectar_patron_simple_optimizado("Diga")
        assert resultado is not None
        assert resultado["tipo"] in ("VERIFICACION_CONEXION_REPETIR", "VERIFICACION_CONEXION")


# ============================================================
# OTRA SUCURSAL
# ============================================================

class TestOtraSucursal:
    """Tests para detección de 'otra sucursal'."""

    @pytest.mark.pattern_detector
    @pytest.mark.regression
    def test_otra_sucursal(self, agente_mid_conversation):
        """BRUCE2048 FIX 621C: 'esa es la otra sucursal' → OTRA_SUCURSAL."""
        resultado = agente_mid_conversation._detectar_patron_simple_optimizado("esa es la otra sucursal")
        assert resultado is not None
        assert resultado["tipo"] in ("OTRA_SUCURSAL", "OTRA_SUCURSAL_INSISTENCIA")


# ============================================================
# CONFIRMACIÓN / AFIRMACIÓN (requiere contexto de pregunta previa)
# ============================================================

class TestConfirmacion:
    """Tests para confirmación simple del cliente.

    NOTA: Confirmaciones cortas como 'Sí' y 'Ok' pueden ir a GPT
    si no hay un contexto conversacional claro. Aquí testeamos
    con el fixture agente_mid_conversation que ya tiene historial.
    """

    @pytest.mark.pattern_detector
    def test_si(self, agente_mid_conversation):
        resultado = agente_mid_conversation._detectar_patron_simple_optimizado("Sí")
        assert resultado is not None
        assert resultado["tipo"] in ("CONFIRMACION_SIMPLE", "CLIENTE_DICE_SI",
                                     "CLIENTE_ACEPTA_WHATSAPP")

    @pytest.mark.pattern_detector
    def test_claro_acepto(self, agente_mid_conversation):
        """'Claro' como confirmación simple."""
        resultado = agente_mid_conversation._detectar_patron_simple_optimizado("Claro")
        assert resultado is not None

    @pytest.mark.pattern_detector
    def test_ok(self, agente_mid_conversation):
        resultado = agente_mid_conversation._detectar_patron_simple_optimizado("Ok")
        assert resultado is not None


# ============================================================
# TRANSFERENCIA (LEGÍTIMA - requiere contexto)
# ============================================================

class TestTransferencia:
    """Tests para transferencia legítima (cliente va a pasar al encargado).

    NOTA: Transferencia se detecta por servidor (FIX 519), no siempre
    por el pattern detector de agente_ventas.
    """

    @pytest.fixture
    def agente_pregunto_encargado(self, agente):
        """Agente que preguntó por encargado (contexto para transferencia)."""
        agente.conversation_history = [
            {"role": "assistant", "content": "¿Se encontrará el encargado de compras?"},
        ]
        agente.segunda_parte_saludo_dicha = True
        return agente

    @pytest.mark.pattern_detector
    def test_espereme_se_lo_paso(self, agente_pregunto_encargado):
        """Nota: STT produce 'espereme' sin acento, por eso testear sin acento."""
        resultado = agente_pregunto_encargado._detectar_patron_simple_optimizado("Espereme, se lo paso")
        assert resultado is not None
        assert resultado["tipo"] in ("TRANSFERENCIA",)

    @pytest.mark.pattern_detector
    def test_permitame(self, agente_pregunto_encargado):
        resultado = agente_pregunto_encargado._detectar_patron_simple_optimizado("Permítame")
        assert resultado is not None
        assert resultado["tipo"] in ("TRANSFERENCIA",)

    @pytest.mark.pattern_detector
    def test_un_momento_por_favor(self, agente_pregunto_encargado):
        """'Un momento por favor' se maneja por servidor (FIX 519), no pattern detector.
        El detector puede delegarlo a GPT."""
        resultado = agente_pregunto_encargado._detectar_patron_simple_optimizado("Ahorita se lo paso, espereme")
        assert resultado is not None


# ============================================================
# SALUDO INICIAL
# ============================================================

class TestSaludo:
    """Tests para saludo inicial del cliente."""

    @pytest.mark.pattern_detector
    def test_bueno(self, agente):
        resultado = agente._detectar_patron_simple_optimizado("Bueno")
        assert resultado is not None
        assert resultado["tipo"] in ("SALUDO_INICIAL", "VERIFICACION_CONEXION")

    @pytest.mark.pattern_detector
    def test_hola(self, agente):
        resultado = agente._detectar_patron_simple_optimizado("Hola")
        assert resultado is not None

    @pytest.mark.pattern_detector
    def test_buenas_tardes(self, agente):
        resultado = agente._detectar_patron_simple_optimizado("Buenas tardes")
        assert resultado is not None


# ============================================================
# CONNECTOR CHECK (FIX 579)
# ============================================================

class TestConnectorCheck:
    """FIX 579: Texto que termina en conector → dejar a GPT."""

    @pytest.mark.pattern_detector
    def test_termina_en_y(self, agente):
        """Texto incompleto terminado en 'y' → None (GPT)."""
        resultado = agente._detectar_patron_simple_optimizado("Sí, el encargado y")
        assert resultado is None, "Texto terminado en 'y' debería ir a GPT"

    @pytest.mark.pattern_detector
    def test_termina_en_pero(self, agente):
        resultado = agente._detectar_patron_simple_optimizado("Sí está pero")
        assert resultado is None, "Texto terminado en 'pero' debería ir a GPT"

    @pytest.mark.pattern_detector
    def test_termina_en_puntos_suspensivos(self, agente):
        resultado = agente._detectar_patron_simple_optimizado("Pues mire...")
        assert resultado is None, "Texto terminado en '...' debería ir a GPT"


# ============================================================
# NÚMERO / WHATSAPP
# ============================================================

class TestNumero:
    """Tests para dictado de números de teléfono."""

    @pytest.mark.pattern_detector
    def test_confirma_mismo_numero(self, agente_mid_conversation):
        """Cliente confirma que el WhatsApp es el mismo número de la llamada."""
        resultado = agente_mid_conversation._detectar_patron_simple_optimizado("Es el mismo")
        assert resultado is not None
        # Puede ser CONFIRMA_MISMO_NUMERO u OFRECE_WHATSAPP
        assert resultado["tipo"] in ("CONFIRMA_MISMO_NUMERO", "CLIENTE_OFRECE_WHATSAPP",
                                     "CLIENTE_ACEPTA_WHATSAPP")

    @pytest.mark.pattern_detector
    def test_no_tiene_whatsapp(self, agente_mid_conversation):
        resultado = agente_mid_conversation._detectar_patron_simple_optimizado("No tengo WhatsApp")
        assert resultado is not None
        assert resultado["tipo"] in ("CLIENTE_NO_TIENE_WHATSAPP",)

    @pytest.mark.pattern_detector
    def test_acepta_dar_whatsapp(self, agente_mid_conversation):
        """'Sí, es este mismo número' cuando Bruce pidió WhatsApp."""
        resultado = agente_mid_conversation._detectar_patron_simple_optimizado("Sí, es este mismo")
        assert resultado is not None


# ============================================================
# REGRESO DE ESPERA
# ============================================================

class TestRegresoEspera:
    """Tests para cuando cliente vuelve después de una espera/transferencia."""

    @pytest.mark.pattern_detector
    def test_bueno_tras_espera(self, agente_esperando_transferencia):
        """Tras transferencia, '¿Bueno?' = regresó."""
        resultado = agente_esperando_transferencia._detectar_patron_simple_optimizado("¿Bueno?")
        assert resultado is not None


# ============================================================
# PREGUNTA IDENTIDAD / UBICACIÓN
# ============================================================

class TestBruce2068Regression:
    """FIX 639: Regresion BRUCE2068 - email no detectado, Bruce mudo."""

    @pytest.mark.regression
    def test_email_completo_con_literal_y_arroba(self, agente_pidiendo_correo):
        """BRUCE2068: Texto con 'arroba' verbal Y email literal → CLIENTE_DICTA_EMAIL_COMPLETO."""
        texto = "Por correo, si quieres. Ulloa cero tres arroba q de uva cero tres arroba Gmail punto com. Es Luis García U. De uva03@gmail.com."
        resultado = agente_pidiendo_correo._detectar_patron_simple_optimizado(texto)
        assert resultado is not None
        assert resultado["tipo"] == "CLIENTE_DICTA_EMAIL_COMPLETO"

    @pytest.mark.regression
    def test_email_literal_preferido_sobre_procesado(self, agente_pidiendo_correo):
        """FIX 639B: Si texto tiene email literal (con @), preferirlo sobre procesado."""
        texto = "Ulloa cero tres arroba q de uva cero tres arroba Gmail punto com. Es Luis García U. De uva03@gmail.com."
        agente_pidiendo_correo._detectar_patron_simple_optimizado(texto)
        email = agente_pidiendo_correo.lead_data.get("email", "")
        assert email == "uva03@gmail.com", f"Esperaba 'uva03@gmail.com' pero obtuve '{email}'"

    @pytest.mark.regression
    def test_email_solo_arroba_verbal(self, agente_pidiendo_correo):
        """Email dictado solo con 'arroba' (sin literal) debe procesarse correctamente."""
        texto = "es ventas arroba gmail punto com"
        resultado = agente_pidiendo_correo._detectar_patron_simple_optimizado(texto)
        assert resultado is not None
        assert resultado["tipo"] == "CLIENTE_DICTA_EMAIL_COMPLETO"
        email = agente_pidiendo_correo.lead_data.get("email", "")
        assert "@" in email
        assert "gmail" in email

    @pytest.mark.regression
    def test_fix_322_no_destruye_con_lead_data_email(self, agente):
        """FIX 639C: Si lead_data tiene email, FIX 322 NO debe reemplazar la respuesta."""
        # Contexto: Bruce pidio correo, cliente lo dio, lead_data ya tiene el email
        agente.conversation_history = [
            {"role": "assistant", "content": "Me comunico de la marca nioval, productos ferreteros. Se encontrara el encargado?"},
            {"role": "user", "content": "No esta, pero le doy el correo"},
            {"role": "assistant", "content": "Si, digame el correo por favor."},
            {"role": "user", "content": "Es uva03 arroba gmail punto com"},
        ]
        agente.lead_data["email"] = "uva03@gmail.com"
        agente.segunda_parte_saludo_dicha = True
        respuesta = "Perfecto, ya lo tengo anotado. Le llegará el catálogo en las próximas horas."
        resultado = agente._filtrar_respuesta_post_gpt(respuesta)
        # No debe contener el pitch de presentación (FIX 322 reemplazaba con pitch)
        assert "se encontrará" not in resultado.lower(), f"FIX 322 destruyó la respuesta: '{resultado[:80]}'"


class TestPreguntaIdentidad:
    """Tests para cuando el cliente pregunta quién llama o de dónde."""

    @pytest.mark.pattern_detector
    def test_quien_habla(self, agente):
        resultado = agente._detectar_patron_simple_optimizado("¿Quién habla?")
        assert resultado is not None
        assert resultado["tipo"] in ("PREGUNTA_IDENTIDAD",)

    @pytest.mark.pattern_detector
    def test_de_donde_llama(self, agente):
        resultado = agente._detectar_patron_simple_optimizado("¿De dónde me llama?")
        assert resultado is not None
        assert resultado["tipo"] in ("PREGUNTA_IDENTIDAD", "PREGUNTA_UBICACION")

    @pytest.mark.pattern_detector
    def test_que_empresa(self, agente):
        resultado = agente._detectar_patron_simple_optimizado("¿De qué empresa?")
        assert resultado is not None
        assert resultado["tipo"] in ("PREGUNTA_IDENTIDAD",)
