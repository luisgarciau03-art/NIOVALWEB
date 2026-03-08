"""
Tests FIX 752-755: Production bug audit fixes.

FIX 752: BRUCE2327 - IVR/buzón de voz patterns definitivos (grabe su mensaje, etc.)
FIX 753: BRUCE2322 - Re-engagement check en FIX 712B (¿Bueno? x5 ignorado)
FIX 754: BRUCE2321 - "No, joven," es rechazo cortés, NO continuación
FIX 755: BRUCE2326 - Safety: NO entrar en modo espera si es primer turno
"""
import sys
import os
import re
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ============================================================
# FIX 752: IVR/buzón de voz detection
# ============================================================

class TestFix752BuzonPatterns(unittest.TestCase):
    """FIX 752: Voicemail patterns must be in FRASES_IVR_ALTA_CONFIANZA."""

    def setUp(self):
        from detector_ivr import DetectorIVR
        self.detector = DetectorIVR()

    def test_patterns_exist_in_alta_confianza(self):
        """FIX 752 voicemail patterns must be in FRASES_IVR_ALTA_CONFIANZA."""
        expected = [
            "grabe su mensaje", "grabe tu mensaje", "grabe un mensaje",
            "deje su mensaje", "deje tu mensaje", "deje un mensaje",
            "después del tono", "despues del tono",
            "marque la tecla gato", "tecla gato cuando termine",
        ]
        for pat in expected:
            self.assertIn(pat, self.detector.FRASES_IVR_ALTA_CONFIANZA,
                          f"'{pat}' debe estar en FRASES_IVR_ALTA_CONFIANZA")

    def test_grabe_su_mensaje_detected(self):
        """'Grabe su mensaje' triggers high-confidence IVR."""
        result = self.detector.analizar_respuesta(
            "Gracias. Grabe su mensaje. Marque la tecla gato cuando termine.")
        self.assertTrue(result['es_ivr'])
        self.assertGreaterEqual(result['confianza'], 0.5)

    def test_grabe_tu_mensaje_detected(self):
        """'Grabe tu mensaje' triggers IVR."""
        result = self.detector.analizar_respuesta(
            "Por favor grabe tu mensaje después del tono.")
        self.assertTrue(result['es_ivr'])
        self.assertGreaterEqual(result['confianza'], 0.5)

    def test_deje_su_mensaje_detected(self):
        """'Deje su mensaje' triggers IVR."""
        result = self.detector.analizar_respuesta(
            "Deje su mensaje después del tono.")
        self.assertTrue(result['es_ivr'])
        self.assertGreaterEqual(result['confianza'], 0.5)

    def test_despues_del_tono_detected(self):
        """'después del tono' triggers IVR."""
        result = self.detector.analizar_respuesta(
            "Hable después del tono, gracias.")
        self.assertTrue(result['es_ivr'])
        self.assertGreaterEqual(result['confianza'], 0.5)

    def test_tecla_gato_detected(self):
        """'marque la tecla gato' triggers IVR."""
        result = self.detector.analizar_respuesta(
            "Marque la tecla gato cuando termine de grabar.")
        self.assertTrue(result['es_ivr'])
        self.assertGreaterEqual(result['confianza'], 0.5)

    def test_buzon_completo_colgar(self):
        """Full voicemail message should trigger COLGAR action."""
        result = self.detector.analizar_respuesta(
            "El número que usted marcó no está disponible. "
            "Grabe su mensaje. Marque la tecla gato cuando termine.")
        self.assertTrue(result['es_ivr'])
        # With multiple indicators, should recommend colgar
        self.assertGreaterEqual(result['confianza'], 0.7)

    def test_normal_client_not_ivr(self):
        """Normal client speech should NOT trigger voicemail detection."""
        result = self.detector.analizar_respuesta("Buenas tardes, habla el encargado.")
        self.assertFalse(result['es_ivr'])

    def test_deje_un_mensaje_detected(self):
        """'Deje un mensaje' triggers IVR."""
        result = self.detector.analizar_respuesta(
            "No se encuentra disponible, deje un mensaje.")
        self.assertTrue(result['es_ivr'])
        self.assertGreaterEqual(result['confianza'], 0.5)


# ============================================================
# FIX 753: Re-engagement in FIX 712B
# ============================================================

class TestFix753ReEngagement712B(unittest.TestCase):
    """FIX 753: Re-engagement detection must exist in 712B path."""

    def _simulate_753_check(self, frase_limpia):
        """Replicate FIX 753 re-engagement logic."""
        _fl = frase_limpia.lower()
        _fl = _fl.replace('á', 'a').replace('é', 'e').replace('í', 'i')
        _fl = _fl.replace('ó', 'o').replace('ú', 'u').replace('ü', 'u').replace('ñ', 'n')
        _fl = _fl.replace('¿', '').replace('?', '').replace('¡', '').replace('!', '')
        _fl = _fl.replace('.', '').replace(',', '')

        _debiles = ['bueno', 'hola', 'si', 'diga', 'digame', 'vuelvo', 'esta bien', 'ok']
        _fuertes = ['aqui estoy', 'ya estoy', 'ya regrese', 'ya volvi', 'oiga', 'oye',
                    'mire', 'me escucha', 'me oye', 'listo', 'fijese', 'encargado',
                    'ferreteria', 'nioval']

        _tiene_fuerte = any(f in _fl for f in _fuertes)
        _tiene_debil = any(f in _fl for f in _debiles)
        _corto = len(_fl) < 25
        return _tiene_fuerte or (_tiene_debil and _corto)

    # --- Strong signals (always re-engage) ---
    def test_fuerte_aqui_estoy(self):
        """'Aquí estoy' = strong re-engagement."""
        self.assertTrue(self._simulate_753_check("Aquí estoy."))

    def test_fuerte_ya_regrese(self):
        """'Ya regresé' = strong re-engagement."""
        self.assertTrue(self._simulate_753_check("Ya regresé"))

    def test_fuerte_oiga(self):
        """'Oiga' = strong re-engagement."""
        self.assertTrue(self._simulate_753_check("Oiga"))

    def test_fuerte_encargado(self):
        """'Soy el encargado' = strong re-engagement."""
        self.assertTrue(self._simulate_753_check("Soy el encargado"))

    def test_fuerte_ferreteria(self):
        """'Ferretería' = strong re-engagement."""
        self.assertTrue(self._simulate_753_check("Ferretería"))

    def test_fuerte_me_escucha(self):
        """'¿Me escucha?' = strong re-engagement."""
        self.assertTrue(self._simulate_753_check("¿Me escucha?"))

    def test_fuerte_nioval(self):
        """'Nioval' = strong re-engagement."""
        self.assertTrue(self._simulate_753_check("Es Nioval verdad"))

    # --- Weak signals (only if short) ---
    def test_debil_bueno_corto(self):
        """'¿Bueno?' short = re-engagement."""
        self.assertTrue(self._simulate_753_check("¿Bueno?"))

    def test_debil_hola_corto(self):
        """'Hola' short = re-engagement."""
        self.assertTrue(self._simulate_753_check("Hola"))

    def test_debil_si_corto(self):
        """'Sí' short = re-engagement."""
        self.assertTrue(self._simulate_753_check("Sí"))

    def test_debil_diga_corto(self):
        """'Diga' short = re-engagement."""
        self.assertTrue(self._simulate_753_check("Diga"))

    def test_debil_digame_corto(self):
        """'Dígame' short = re-engagement."""
        self.assertTrue(self._simulate_753_check("¿Dígame?"))

    def test_debil_bueno_largo_NO(self):
        """Long text with 'bueno' = NOT re-engagement (background noise)."""
        largo = "bueno pues estaba hablando con mi compañero y me dijo que sí pero que necesita"
        self.assertFalse(self._simulate_753_check(largo))

    def test_no_signal_no_reengage(self):
        """Random background noise = NOT re-engagement."""
        self.assertFalse(self._simulate_753_check("la verdad es que no sé qué pasó ahí"))

    def test_code_exists_in_servidor(self):
        """FIX 753 code must exist in servidor_llamadas.py."""
        srv_path = os.path.join(os.path.dirname(__file__), '..', 'servidor_llamadas.py')
        with open(srv_path, 'r', encoding='utf-8') as f:
            src = f.read()
        self.assertIn('FIX 753', src)
        self.assertIn('_fl_753', src)
        self.assertIn('_volvio_753', src)


# ============================================================
# FIX 754: "No, joven" rejection pattern
# ============================================================

class TestFix754RechazoCortes(unittest.TestCase):
    """FIX 754: Polite rejection ('No, joven,') must NOT be treated as continuation."""

    def _is_rechazo_754(self, texto):
        """Replicate FIX 754 rejection check logic."""
        texto_lower = texto.lower()
        _rechazo_cortes = [
            'no joven', 'no muchacho', 'no señor', 'no senor',
            'no señorita', 'no senorita', 'no mijo', 'no amigo',
            'no gracias joven', 'no gracias muchacho', 'no gracias señor',
        ]
        _tl = re.sub(r'[,.\s]+$', '', texto_lower).replace(',', ' ').strip()
        _tl = re.sub(r'\s+', ' ', _tl)
        return any(r in _tl for r in _rechazo_cortes)

    def test_no_joven_comma(self):
        """'No, joven,' is polite rejection."""
        self.assertTrue(self._is_rechazo_754("No, joven,"))

    def test_no_joven_no_comma(self):
        """'No joven' is polite rejection."""
        self.assertTrue(self._is_rechazo_754("No joven"))

    def test_no_muchacho(self):
        """'No, muchacho' is polite rejection."""
        self.assertTrue(self._is_rechazo_754("No, muchacho"))

    def test_no_senor(self):
        """'No, señor' is polite rejection."""
        self.assertTrue(self._is_rechazo_754("No, señor"))

    def test_no_senor_sin_acento(self):
        """'No, senor' (no accent) is polite rejection."""
        self.assertTrue(self._is_rechazo_754("No, senor"))

    def test_no_senorita(self):
        """'No, señorita' is polite rejection."""
        self.assertTrue(self._is_rechazo_754("No, señorita"))

    def test_no_mijo(self):
        """'No, mijo' is polite rejection."""
        self.assertTrue(self._is_rechazo_754("No, mijo,"))

    def test_no_amigo(self):
        """'No, amigo' is polite rejection."""
        self.assertTrue(self._is_rechazo_754("No, amigo"))

    def test_no_gracias_joven(self):
        """'No, gracias, joven' is polite rejection."""
        self.assertTrue(self._is_rechazo_754("No, gracias, joven"))

    def test_no_gracias_senor(self):
        """'No, gracias, señor' is polite rejection."""
        self.assertTrue(self._is_rechazo_754("No, gracias, señor"))

    def test_si_joven_NOT_rechazo(self):
        """'Sí, joven' is NOT rejection."""
        self.assertFalse(self._is_rechazo_754("Sí, joven"))

    def test_datos_normales_NOT_rechazo(self):
        """Normal data '331 234 5678,' is NOT rejection."""
        self.assertFalse(self._is_rechazo_754("331 234 5678,"))

    def test_email_NOT_rechazo(self):
        """Email 'juan arroba gmail,' is NOT rejection."""
        self.assertFalse(self._is_rechazo_754("juan arroba gmail,"))

    def test_code_exists_in_agente(self):
        """FIX 754 code must exist in agente_ventas.py."""
        agt_path = os.path.join(os.path.dirname(__file__), '..', 'agente_ventas.py')
        with open(agt_path, 'r', encoding='utf-8') as f:
            src = f.read()
        self.assertIn('FIX 754', src)
        self.assertIn('_rechazo_cortes_754', src)

    def test_code_returns_false(self):
        """FIX 754 returns False from _cliente_esta_dando_informacion."""
        agt_path = os.path.join(os.path.dirname(__file__), '..', 'agente_ventas.py')
        with open(agt_path, 'r', encoding='utf-8') as f:
            src = f.read()
        # Must have "return False" after FIX 754 check
        idx = src.find('_rechazo_cortes_754')
        self.assertGreater(idx, 0)
        section = src[idx:idx + 1000]
        self.assertIn('return False', section)


# ============================================================
# FIX 754 Integration: Full _cliente_esta_dando_informacion
# ============================================================

class TestFix754Integration(unittest.TestCase):
    """FIX 754: Test via actual AgenteVentas._cliente_esta_dando_informacion."""

    def setUp(self):
        from agente_ventas import AgenteVentas
        self.agente = AgenteVentas.__new__(AgenteVentas)
        self.agente.conversation_history = []
        self.agente.digitos_acumulados_flag = False
        self.agente.esperando_hora_callback = False
        self.agente.turno_actual = 3
        self.agente.ultimo_dato_recibido = None

    def test_no_joven_returns_false(self):
        """'No, joven,' must return False (not giving info)."""
        result = self.agente._cliente_esta_dando_informacion("No, joven,")
        self.assertFalse(result)

    def test_no_muchacho_comma_returns_false(self):
        """'No, muchacho,' must return False."""
        result = self.agente._cliente_esta_dando_informacion("No, muchacho,")
        self.assertFalse(result)

    def test_no_senor_returns_false(self):
        """'No, señor,' must return False."""
        result = self.agente._cliente_esta_dando_informacion("No, señor,")
        self.assertFalse(result)

    def test_digits_still_detected(self):
        """'331 234 56,' (digits with comma) must still return True."""
        result = self.agente._cliente_esta_dando_informacion("331 234 56,")
        self.assertTrue(result)


# ============================================================
# FIX 755: First-turn safety guard
# ============================================================

class TestFix755FirstTurnSafety(unittest.TestCase):
    """FIX 755: No ESPERANDO_TRANSFERENCIA on first turn."""

    def _simulate_755_check(self, conversation_history, cliente_pidio_espera):
        """Replicate FIX 755 safety logic."""
        _user_msgs = sum(1 for m in conversation_history if m.get('role') == 'user')
        if cliente_pidio_espera and _user_msgs < 1:
            return False  # Override: don't enter wait mode
        return cliente_pidio_espera

    def test_first_turn_blocks_espera(self):
        """First turn (0 user msgs) must block ESPERANDO_TRANSFERENCIA."""
        history = []  # No user messages yet
        result = self._simulate_755_check(history, True)
        self.assertFalse(result)

    def test_second_turn_allows_espera(self):
        """Second turn (1+ user msgs) should allow ESPERANDO_TRANSFERENCIA."""
        history = [{'role': 'user', 'content': 'Buenas tardes'}]
        result = self._simulate_755_check(history, True)
        self.assertTrue(result)

    def test_no_espera_always_false(self):
        """No espera request returns False regardless of turn."""
        history = []
        result = self._simulate_755_check(history, False)
        self.assertFalse(result)

    def test_multiple_turns_allows_espera(self):
        """Multiple turns should allow ESPERANDO_TRANSFERENCIA."""
        history = [
            {'role': 'user', 'content': 'Buenas tardes'},
            {'role': 'assistant', 'content': 'Hola, buenas tardes...'},
            {'role': 'user', 'content': 'Permítame un momento'},
        ]
        result = self._simulate_755_check(history, True)
        self.assertTrue(result)

    def test_code_exists_in_servidor(self):
        """FIX 755 code must exist in servidor_llamadas.py."""
        srv_path = os.path.join(os.path.dirname(__file__), '..', 'servidor_llamadas.py')
        with open(srv_path, 'r', encoding='utf-8') as f:
            src = f.read()
        self.assertIn('FIX 755', src)
        self.assertIn('_user_msgs_755', src)

    def test_assistant_msgs_not_counted(self):
        """Only user messages should be counted, not assistant."""
        history = [
            {'role': 'assistant', 'content': 'Saludo...'},
            {'role': 'assistant', 'content': 'Pitch...'},
        ]
        result = self._simulate_755_check(history, True)
        self.assertFalse(result)  # 0 user msgs = block espera


# ============================================================
# Integration: All FIX 752-755 code presence
# ============================================================

class TestFix752755CodePresence(unittest.TestCase):
    """Verify all FIX 752-755 are present in source files."""

    def test_fix_752_in_detector_ivr(self):
        """FIX 752 must be in detector_ivr.py."""
        path = os.path.join(os.path.dirname(__file__), '..', 'detector_ivr.py')
        with open(path, 'r', encoding='utf-8') as f:
            src = f.read()
        self.assertIn('FIX 752', src)
        self.assertIn('grabe su mensaje', src)
        self.assertIn('tecla gato', src)

    def test_fix_753_in_servidor(self):
        """FIX 753 must be in servidor_llamadas.py."""
        path = os.path.join(os.path.dirname(__file__), '..', 'servidor_llamadas.py')
        with open(path, 'r', encoding='utf-8') as f:
            src = f.read()
        self.assertIn('FIX 753', src)
        self.assertIn('_debiles_753', src)
        self.assertIn('_fuertes_753', src)

    def test_fix_754_in_agente(self):
        """FIX 754 must be in agente_ventas.py."""
        path = os.path.join(os.path.dirname(__file__), '..', 'agente_ventas.py')
        with open(path, 'r', encoding='utf-8') as f:
            src = f.read()
        self.assertIn('FIX 754', src)
        self.assertIn('no joven', src)
        self.assertIn('no muchacho', src)

    def test_fix_755_in_servidor(self):
        """FIX 755 must be in servidor_llamadas.py."""
        path = os.path.join(os.path.dirname(__file__), '..', 'servidor_llamadas.py')
        with open(path, 'r', encoding='utf-8') as f:
            src = f.read()
        self.assertIn('FIX 755', src)
        self.assertIn('_user_msgs_755', src)


if __name__ == '__main__':
    unittest.main()
