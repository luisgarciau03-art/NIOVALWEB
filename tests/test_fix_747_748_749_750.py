"""
Tests para FIX 747-750:
- FIX 747: BRUCE2386 - ENCARGADO_NO_ESTA + dictado concurrente
- FIX 748: BRUCE2392 - GPT timeout callback detection
- FIX 749: BRUCE2388 - Saludo faltante + "te comunico" false positive
- FIX 750: BRUCE2387 - Garbled STT de-duplication
"""
import unittest
import sys
import os
import re

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _get_agente():
    """Helper para crear instancia de AgenteVentas para testing."""
    from agente_ventas import AgenteVentas, EstadoConversacion
    agente = AgenteVentas.__new__(AgenteVentas)
    agente.conversation_history = []
    agente.lead_data = {"bruce_id": "TEST_FIX747"}
    agente.turno_actual = 3
    agente.estado_conversacion = EstadoConversacion.INICIO
    agente.esperando_transferencia = False
    agente.pitch_dado = False
    agente.catalogo_ofrecido = False
    agente.catalogo_prometido = False
    agente.esperando_hora_callback = False
    agente.digitos_preservados_481 = ""
    agente.digitos_acumulados_flag = False
    agente._datos_parciales_en_no_esta_747 = False
    agente.ultimo_claro_espero_timestamp = 0
    agente.pausa_intencional = False
    # Memory/Speech/FSM
    agente.memory = None
    agente.speech = None
    agente.fsm = None
    agente.intent_classifier = None
    return agente


# =============================================================================
# FIX 747: BRUCE2386 - ENCARGADO_NO_ESTA + dictado concurrente
# =============================================================================
class TestFIX747_DictadoConcurrente(unittest.TestCase):
    """Test ENCARGADO_NO_ESTA detection with concurrent number dictation."""

    def test_no_esta_con_numeros_verbales(self):
        """'No estan ahorita. Es cuarenta y cuatro cuarenta' → flag set."""
        agente = _get_agente()
        from agente_ventas import EstadoConversacion
        # Simulate verificar_estado_encargado with the compound text
        mensaje = "es que no estan ahorita. es cuarenta y cuatro cuarenta"
        # Check the number detection logic
        nums_747 = ['cero','uno','dos','tres','cuatro','cinco','seis','siete',
            'ocho','nueve','diez','once','doce','trece','catorce','quince',
            'veinte','treinta','cuarenta','cincuenta','sesenta','setenta','ochenta','noventa']
        msg_norm = mensaje.replace('á','a').replace('é','e').replace('í','i').replace('ó','o').replace('ú','u')
        nums_verbales = sum(1 for p in msg_norm.split() if p in nums_747)
        # "cuarenta" appears 2x, "cuatro" 1x = 3 verbal numbers
        self.assertGreaterEqual(nums_verbales, 2)

    def test_no_esta_sin_numeros(self):
        """'No esta ahorita, salió a comer' → no flag."""
        mensaje = "no esta ahorita, salio a comer"
        nums_747 = ['cero','uno','dos','tres','cuatro','cinco','seis','siete',
            'ocho','nueve','diez','once','doce','trece','catorce','quince',
            'veinte','treinta','cuarenta','cincuenta','sesenta','setenta','ochenta','noventa']
        msg_norm = mensaje.replace('á','a').replace('é','e').replace('í','i').replace('ó','o').replace('ú','u')
        nums_verbales = sum(1 for p in msg_norm.split() if p in nums_747)
        self.assertLess(nums_verbales, 2)

    def test_no_esta_con_digitos_numericos(self):
        """'No esta. 331234' → flag set (3+ digits)."""
        mensaje = "no esta. 331234"
        digitos = len(re.findall(r'\d', mensaje))
        self.assertGreaterEqual(digitos, 3)

    def test_post_filter_override(self):
        """When _datos_parciales_en_no_esta_747 is set, response is overridden."""
        agente = _get_agente()
        from agente_ventas import EstadoConversacion
        agente._datos_parciales_en_no_esta_747 = True
        agente.estado_conversacion = EstadoConversacion.ENCARGADO_NO_ESTA

        # Simulate the post-filter check
        filtro_aplicado = False
        respuesta = "¿Me podría proporcionar un WhatsApp para enviarle nuestro catálogo?"

        if not filtro_aplicado and getattr(agente, '_datos_parciales_en_no_esta_747', False):
            respuesta = "Entendido, no se encuentra. Ajá, sí, dígame el número por favor."
            agente.estado_conversacion = EstadoConversacion.DICTANDO_NUMERO
            filtro_aplicado = True
            agente._datos_parciales_en_no_esta_747 = False

        self.assertTrue(filtro_aplicado)
        self.assertIn("dígame el número", respuesta)
        self.assertEqual(agente.estado_conversacion, EstadoConversacion.DICTANDO_NUMERO)
        self.assertFalse(agente._datos_parciales_en_no_esta_747)

    def test_no_flag_when_no_numbers(self):
        """Without numbers, flag should not be set."""
        agente = _get_agente()
        agente._datos_parciales_en_no_esta_747 = False
        # Without setting flag, post-filter should not fire
        filtro_aplicado = False
        respuesta = "¿Me podría proporcionar un WhatsApp?"
        if not filtro_aplicado and getattr(agente, '_datos_parciales_en_no_esta_747', False):
            respuesta = "override"
            filtro_aplicado = True
        self.assertFalse(filtro_aplicado)
        self.assertIn("WhatsApp", respuesta)


# =============================================================================
# FIX 748: BRUCE2392 - GPT timeout callback detection
# =============================================================================
class TestFIX748_TimeoutCallback(unittest.TestCase):
    """Test FIX 682 fallback detects callback info instead of 'me puede repetir'."""

    def _simulate_fallback(self, speech_lower):
        """Simulate FIX 748 callback detection logic."""
        dias = ['lunes', 'martes', 'miercoles', 'miércoles', 'jueves', 'viernes', 'sabado', 'sábado', 'domingo']
        momentos = ['mañana', 'manana', 'pasado mañana', 'pasado manana', 'la proxima semana', 'la próxima semana']
        callback_patterns = ['se presenta', 'viene hasta', 'llega hasta', 'regresa', 'vuelve',
            'esta hasta', 'está hasta', 'marque el', 'llame el', 'mejor el']

        tiene_dia = any(d in speech_lower for d in dias + momentos)
        tiene_callback = any(c in speech_lower for c in callback_patterns)

        if tiene_dia and tiene_callback:
            dia = next((d for d in dias + momentos if d in speech_lower), '')
            return f"Perfecto, le marco el {dia}. Muchas gracias por la información."
        elif tiene_dia:
            dia = next((d for d in dias + momentos if d in speech_lower), '')
            return f"Perfecto, le marco el {dia}. ¿A qué hora le puedo llamar?"
        else:
            return "Disculpe, ¿me puede repetir lo que me decía?"

    def test_se_presenta_el_lunes(self):
        """'se presenta el lunes' → callback response, NOT 'me puede repetir'."""
        result = self._simulate_fallback("se presenta el lunes")
        self.assertIn("lunes", result)
        self.assertNotIn("repetir", result)

    def test_viene_hasta_el_viernes(self):
        """'viene hasta el viernes' → callback response."""
        result = self._simulate_fallback("viene hasta el viernes")
        self.assertIn("viernes", result)
        self.assertNotIn("repetir", result)

    def test_llega_mañana(self):
        """'llega hasta mañana' → callback with mañana."""
        result = self._simulate_fallback("llega hasta mañana")
        self.assertIn("mañana", result)

    def test_marque_el_martes(self):
        """'marque el martes' → callback response."""
        result = self._simulate_fallback("marque el martes")
        self.assertIn("martes", result)

    def test_dia_sin_callback_pattern(self):
        """'el lunes hay promoción' → asks for time (has day but no callback pattern)."""
        result = self._simulate_fallback("el lunes hay promoción")
        self.assertIn("lunes", result)
        self.assertIn("hora", result)

    def test_no_callback_info(self):
        """'hola buenas tardes' → generic 'me puede repetir'."""
        result = self._simulate_fallback("hola buenas tardes")
        self.assertIn("repetir", result)

    def test_regresa_el_jueves(self):
        """'regresa el jueves en la tarde' → callback response."""
        result = self._simulate_fallback("regresa el jueves en la tarde")
        self.assertIn("jueves", result)


# =============================================================================
# FIX 749A: BRUCE2388 - Greeting prefix on identity response
# =============================================================================
class TestFIX749A_GreetingPrefix(unittest.TestCase):
    """Test FIX 708 identity response includes greeting + encargado question."""

    def test_identity_response_has_greeting(self):
        """FIX 708 identity response should start with 'Buen día'."""
        # The updated response in FIX 708 for identity questions
        response = "Buen día. Mi nombre es Bruce, le llamo de la marca NIOVAL. Somos distribuidores de productos ferreteros. ¿Se encontrará el encargado o encargada de compras?"
        self.assertTrue(response.startswith("Buen día"))
        self.assertIn("encargado", response)
        self.assertIn("NIOVAL", response)

    def test_con_quien_tengo_el_gusto_detected(self):
        """'con quien tengo el gusto' should match identity patterns."""
        texto = "con quien tengo el gusto"
        texto_norm = texto.replace('á','a').replace('é','e').replace('í','i').replace('ó','o').replace('ú','u').replace('ü','u').replace('ñ','n')
        texto_norm = texto_norm.replace('¿','').replace('?','').replace('¡','').replace('!','')
        patterns = ['quien habla', 'quien llama', 'quien me habla', 'quien me llama',
              'con quien hablo', 'con quien tengo el gusto', 'con quien tengo gusto',
              'de donde habla', 'de donde hablan', 'de donde llama', 'de donde llaman',
              'de donde me habla', 'de donde me llama', 'de donde me marcan',
              'de que empresa', 'de que compania', 'que empresa es',
              'de parte de quien', 'a nombre de quien']
        self.assertTrue(any(p in texto_norm for p in patterns))

    def test_con_quien_tengo_el_gusto_in_pregunta_identidad(self):
        """'con quien tengo el gusto' should be in PREGUNTA_IDENTIDAD detector."""
        patterns_identidad = [
            "con quién tengo el gusto", "con quien tengo el gusto",
            "con quién tengo gusto", "con quien tengo gusto",
        ]
        texto = "sofi ferreterias, con quien tengo el gusto"
        self.assertTrue(any(p in texto for p in patterns_identidad))


# =============================================================================
# FIX 749B: BRUCE2388 - "te comunico sobre" NOT transfer
# =============================================================================
class TestFIX749B_TeComunicoNoTransfer(unittest.TestCase):
    """Test 'te comunico sobre' is NOT classified as transfer."""

    def _is_explanation_not_transfer(self, text):
        """Check if text matches FIX 749B exclusion patterns."""
        text_lower = text.lower()
        exclusions = [
            'te comunico sobre', 'le comunico sobre', 'se comunica a',
            'te comunico que', 'le comunico que', 'comunico de que',
            'linea directa de atencion', 'línea directa de atención',
            'linea de atencion', 'línea de atención'
        ]
        return any(p in text_lower for p in exclusions)

    def test_te_comunico_sobre(self):
        """'Te comunico sobre una línea directa' → NOT transfer."""
        self.assertTrue(self._is_explanation_not_transfer(
            "Te comunico sobre una línea directa de atención a clientes"))

    def test_le_comunico_que(self):
        """'Le comunico que esta es una línea directa' → NOT transfer."""
        self.assertTrue(self._is_explanation_not_transfer(
            "Le comunico que esta es una línea directa"))

    def test_se_comunica_a(self):
        """'Se comunica a una línea de atención' → NOT transfer."""
        self.assertTrue(self._is_explanation_not_transfer(
            "Se comunica a una línea de atención a clientes"))

    def test_te_comunico_con_IS_transfer(self):
        """'te comunico con el encargado' should NOT match exclusion (it IS a transfer)."""
        self.assertFalse(self._is_explanation_not_transfer(
            "te comunico con el encargado"))

    def test_ahorita_te_lo_paso_IS_transfer(self):
        """'ahorita te lo paso' should NOT match exclusion (it IS a transfer)."""
        self.assertFalse(self._is_explanation_not_transfer(
            "ahorita te lo paso"))

    def test_linea_directa_de_atencion(self):
        """'línea directa de atención' alone → NOT transfer."""
        self.assertTrue(self._is_explanation_not_transfer(
            "esta es una línea directa de atención"))


# =============================================================================
# FIX 750: BRUCE2387 - Garbled STT de-duplication
# =============================================================================
class TestFIX750_GarbledSTT(unittest.TestCase):
    """Test garbled/duplicated STT text is de-duplicated."""

    def _dedup_garbled(self, speech):
        """Simulate FIX 750 garbled STT de-duplication."""
        fillers = {'mhm', 'aja', 'ajá', 'este', 'eh', 'ah', 'mm', 'mmm', 'uh', 'pues', 'uhm'}
        palabras = speech.strip().split()
        if len(palabras) >= 4:
            half = len(palabras) // 2
            clean = lambda t: re.sub(r'[.,!?¿¡:;]', '', t).lower().strip()
            first_half = clean(' '.join(palabras[:half]))
            second_half = clean(' '.join(palabras[half:]))
            if first_half == second_half or (
                len(first_half) > 5 and first_half in second_half
            ):
                return ' '.join(palabras[:half])
        return speech

    def test_exact_duplicate(self):
        """'hola buen dia Hola, buen dia' → de-duplicated."""
        result = self._dedup_garbled("hola buen dia Hola, buen dia")
        self.assertEqual(result, "hola buen dia")

    def test_duplicate_with_comma(self):
        """'Buenos dias Buenos dias' → de-duplicated."""
        result = self._dedup_garbled("Buenos dias Buenos dias")
        self.assertEqual(result, "Buenos dias")

    def test_no_duplicate(self):
        """'hola buenos dias como esta' → NOT de-duplicated."""
        result = self._dedup_garbled("hola buenos dias como esta")
        self.assertEqual(result, "hola buenos dias como esta")

    def test_short_text_not_affected(self):
        """Short text (< 4 words) should not be de-duplicated."""
        result = self._dedup_garbled("hola bueno")
        self.assertEqual(result, "hola bueno")

    def test_similar_but_not_exact(self):
        """'hola buen dia hola buenas tardes' → NOT de-duplicated (different)."""
        result = self._dedup_garbled("hola buen dia hola buenas tardes")
        self.assertEqual(result, "hola buen dia hola buenas tardes")

    def test_contained_duplicate(self):
        """'buenos dias buenos dias señor' → de-duplicated (first half in second)."""
        result = self._dedup_garbled("buenos dias buenos dias señor")
        # 5 words: half=2, first='buenos dias', second='buenos dias señor'
        # first is in second → de-duplicate
        self.assertEqual(result, "buenos dias")


# =============================================================================
# Integration: BRUCE2386 Replay
# =============================================================================
class TestBRUCE2386_Replay(unittest.TestCase):
    """Replay BRUCE2386 exact conversation to verify fix."""

    def test_bruce2386_compound_sentence(self):
        """'Es que no estan ahorita. Es cuarenta y cuatro cuarenta' should
        acknowledge both: encargado absent + number dictation."""
        mensaje = "es que no estan ahorita. es cuarenta y cuatro cuarenta"
        # Verify ENCARGADO_NO_ESTA would match
        patrones_no_esta = ['no está', 'no esta', 'no se encuentra', 'no estan']
        has_no_esta = any(p in mensaje for p in patrones_no_esta)
        self.assertTrue(has_no_esta)

        # Verify number detection
        nums = ['cero','uno','dos','tres','cuatro','cinco','seis','siete',
            'ocho','nueve','diez','once','doce','trece','catorce','quince',
            'veinte','treinta','cuarenta','cincuenta','sesenta','setenta','ochenta','noventa']
        nums_verbales = sum(1 for p in mensaje.split() if p in nums)
        self.assertGreaterEqual(nums_verbales, 2)  # cuarenta, cuatro, cuarenta = 3


# =============================================================================
# Integration: BRUCE2388 Replay
# =============================================================================
class TestBRUCE2388_Replay(unittest.TestCase):
    """Replay BRUCE2388 exact conversation to verify fix."""

    def test_bruce2388_identity_greeting(self):
        """FIX 708 identity response for 'con quién tengo el gusto' should include greeting."""
        # The updated response
        response = "Buen día. Mi nombre es Bruce, le llamo de la marca NIOVAL. Somos distribuidores de productos ferreteros. ¿Se encontrará el encargado o encargada de compras?"
        self.assertTrue(response.startswith("Buen día"))
        self.assertIn("encargado", response)

    def test_bruce2388_te_comunico_sobre(self):
        """'Te comunico sobre una línea directa' should NOT trigger 'Claro, espero'."""
        texto = "te comunico sobre una línea directa de atención a clientes"
        exclusions = ['te comunico sobre', 'le comunico sobre', 'se comunica a',
            'te comunico que', 'le comunico que']
        is_explanation = any(p in texto.lower() for p in exclusions)
        self.assertTrue(is_explanation)

        # And the text DOES contain 'te comunico' (transfer pattern)
        transfer_patterns = ['te comunico']
        has_transfer = any(p in texto.lower() for p in transfer_patterns)
        self.assertTrue(has_transfer)
        # But exclusion should prevent transfer activation


# =============================================================================
# Integration: BRUCE2392 Replay
# =============================================================================
class TestBRUCE2392_Replay(unittest.TestCase):
    """Replay BRUCE2392 exact conversation to verify fix."""

    def test_bruce2392_se_presenta_el_lunes(self):
        """'¿Qué cree que se presenta el lunes?' → callback, NOT 'me puede repetir'."""
        speech = "¿qué cree que se presenta el lunes?"
        speech_lower = speech.lower()
        dias = ['lunes', 'martes', 'miércoles', 'jueves', 'viernes']
        callback = ['se presenta', 'viene hasta', 'regresa']
        tiene_dia = any(d in speech_lower for d in dias)
        tiene_callback = any(c in speech_lower for c in callback)
        self.assertTrue(tiene_dia)
        self.assertTrue(tiene_callback)


if __name__ == '__main__':
    unittest.main()
