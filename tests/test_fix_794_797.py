"""
Tests para FIX 794-797: 4 Bugs de Producción (BRUCE2512-2518)
- FIX 794: Número WhatsApp orden incorrecto (P0)
- FIX 795: Re-greeting "que tal" clasificado como QUESTION (P1)
- FIX 796: STT Echo sentence-level dedup (P1)
- FIX 797: CAPTURANDO_CONTACTO + MANAGER_ABSENT/PRESENT/QUESTION (P2)
"""
import sys
import os
import re
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


# ============================================================
# FIX 794: Número WhatsApp orden incorrecto
# ============================================================

class TestFix794NumeroWhatsAppOrden:
    """FIX 794: convertir_numeros_escritos_a_digitos preserva orden de dígitos."""

    def setup_method(self):
        from agente_ventas import convertir_numeros_escritos_a_digitos
        self.convertir = convertir_numeros_escritos_a_digitos

    def _extract_phone(self, texto):
        """Simula la extracción de teléfono como _sync_fsm_to_agent FIX 794."""
        texto_convertido = self.convertir(texto)
        digitos = re.findall(r'\d', texto_convertido)
        if len(digitos) >= 10:
            return ''.join(digitos[:10])
        return ''.join(digitos)

    def test_bruce2512_caso_real(self):
        """BRUCE2512: 'seis seis veintitrés cincuenta y tres dieciocho cero cuatro 23531804'"""
        texto = "Es seis seis veintitrés cincuenta y tres, dieciocho cero cuatro. 23531804."
        result = self._extract_phone(texto)
        assert result == "6623531804", f"Expected 6623531804, got {result}"

    def test_bruce2512_sin_literal(self):
        """Solo palabras numéricas sin dígitos literales."""
        texto = "seis seis veintitrés cincuenta y tres dieciocho cero cuatro"
        result = self._extract_phone(texto)
        assert result == "6623531804", f"Expected 6623531804, got {result}"

    def test_solo_digitos_numericos(self):
        """Solo dígitos numéricos, sin palabras."""
        texto = "6623531804"
        result = self._extract_phone(texto)
        assert result == "6623531804", f"Expected 6623531804, got {result}"

    def test_mixto_inicio_palabras_fin_digitos(self):
        """Palabras al inicio, dígitos al final."""
        texto = "seis seis 23531804"
        result = self._extract_phone(texto)
        assert result == "6623531804", f"Expected 6623531804, got {result}"

    def test_mixto_inicio_digitos_fin_palabras(self):
        """Dígitos al inicio, palabras al final."""
        texto = "66 veintitrés cincuenta y tres dieciocho cero cuatro"
        result = self._extract_phone(texto)
        assert result == "6623531804", f"Expected 6623531804, got {result}"

    def test_numero_con_puntuacion(self):
        """Números con comas y puntos no deben romper orden."""
        texto = "seis, seis, veintitrés, cincuenta y tres, dieciocho, cero, cuatro"
        result = self._extract_phone(texto)
        assert result == "6623531804", f"Expected 6623531804, got {result}"

    def test_numero_simple_palabras(self):
        """Número simple: tres tres uno dos nueve ocho siete seis cinco cuatro."""
        texto = "tres tres uno dos nueve ocho siete seis cinco cuatro"
        result = self._extract_phone(texto)
        assert result == "3312987654", f"Expected 3312987654, got {result}"

    def test_numero_con_prefijo_52(self):
        """Con prefijo país, tomar primeros 10 dígitos."""
        texto = "cincuenta y dos seis seis veintitrés cincuenta y tres dieciocho cero cuatro"
        result = self._extract_phone(texto)
        # 52 + 6623531804 → primeros 10 = 5266235318
        assert len(result) == 10

    def test_no_invierte_orden_bug_original(self):
        """Verificar que el bug original (literal primero) NO ocurre."""
        texto = "Es seis seis veintitrés cincuenta y tres, dieciocho cero cuatro. 23531804."
        result = self._extract_phone(texto)
        # Bug original: 2353180466 (literal "23531804" primero, "seis seis cero" después)
        assert result != "2353180466", f"Bug original sigue presente: {result}"
        assert result == "6623531804"

    def test_bruce2515_caso_real(self):
        """BRUCE2515: verificar que número correcto se extrae."""
        texto = "seis, seis, veintitrés, cincuenta y tres, dieciocho, cero cuatro"
        result = self._extract_phone(texto)
        assert result == "6623531804", f"Expected 6623531804, got {result}"

    def test_convertir_preserva_orden_general(self):
        """convertir_numeros_escritos_a_digitos preserva orden secuencial."""
        texto = "uno dos tres cuatro cinco seis siete ocho nueve cero"
        convertido = self.convertir(texto)
        digitos = re.findall(r'\d', convertido)
        assert ''.join(digitos) == "1234567890"

    def test_dieciocho_se_convierte_correctamente(self):
        """FIX 794: 'dieciocho' → '18', no 'dieci8'."""
        convertido = self.convertir("dieciocho")
        assert "18" in convertido, f"'dieciocho' debe convertir a '18', got '{convertido}'"
        assert "dieci" not in convertido

    def test_dieciseis_se_convierte_correctamente(self):
        """'dieciseis' → '16', no 'dieci6'."""
        convertido = self.convertir("dieciseis")
        assert "16" in convertido

    def test_diecinueve_se_convierte_correctamente(self):
        """'diecinueve' → '19', no 'dieci9'."""
        convertido = self.convertir("diecinueve")
        assert "19" in convertido


# ============================================================
# FIX 795: Re-greeting "que tal" clasificado como QUESTION
# ============================================================

class TestFix795GreetingNotQuestion:
    """FIX 795: Saludos como 'que tal' NO deben clasificarse como QUESTION."""

    def setup_method(self):
        from fsm_engine import classify_intent, FSMContext, FSMState, FSMIntent
        self.classify = classify_intent
        self.ctx = FSMContext()
        self.state = FSMState.BUSCANDO_ENCARGADO
        self.QUESTION = FSMIntent.QUESTION

    def _classify(self, texto):
        return self.classify(texto, self.ctx, self.state)

    def test_que_tal_buen_dia_no_es_question(self):
        """'que tal buen dia' es saludo, no pregunta."""
        intent = self._classify("qué tal buen día")
        assert intent != self.QUESTION, f"'que tal buen dia' no debe ser QUESTION, got {intent}"

    def test_que_tal_no_es_question(self):
        """'que tal' solo, es saludo."""
        intent = self._classify("que tal")
        assert intent != self.QUESTION, f"'que tal' no debe ser QUESTION, got {intent}"

    def test_que_onda_no_es_question(self):
        """'que onda' es saludo informal."""
        intent = self._classify("que onda")
        assert intent != self.QUESTION, f"'que onda' no debe ser QUESTION, got {intent}"

    def test_que_hubo_no_es_question(self):
        """'que hubo' es saludo informal."""
        intent = self._classify("que hubo")
        assert intent != self.QUESTION, f"'que hubo' no debe ser QUESTION, got {intent}"

    def test_que_paso_no_es_question(self):
        """'que paso' como saludo."""
        intent = self._classify("que paso")
        assert intent != self.QUESTION, f"'que paso' no debe ser QUESTION, got {intent}"

    def test_que_ofrece_si_es_question(self):
        """'que ofrece' SÍ es pregunta real."""
        intent = self._classify("que ofrece")
        assert intent == self.QUESTION, f"'que ofrece' debe ser QUESTION, got {intent}"

    def test_que_empresa_es_si_es_question(self):
        """'que empresa es' SÍ es pregunta real."""
        intent = self._classify("que empresa es")
        assert intent == self.QUESTION, f"'que empresa es' debe ser QUESTION, got {intent}"

    def test_que_productos_tienen_si_es_question(self):
        """'que productos tienen' SÍ es pregunta real."""
        intent = self._classify("que productos tienen")
        assert intent == self.QUESTION, f"'que productos tienen' debe ser QUESTION, got {intent}"

    def test_cual_es_el_precio_si_es_question(self):
        """'cual es el precio' SÍ es pregunta."""
        intent = self._classify("cual es el precio")
        assert intent == self.QUESTION, f"'cual es el precio' debe ser QUESTION, got {intent}"

    def test_como_funciona_si_es_question(self):
        """'como funciona' SÍ es pregunta."""
        intent = self._classify("como funciona")
        assert intent == self.QUESTION, f"'como funciona' debe ser QUESTION, got {intent}"

    def test_que_tal_con_pregunta_no_es_question(self):
        """'que tal buen dia como esta' - saludo extendido."""
        intent = self._classify("que tal buen dia como esta")
        assert intent != self.QUESTION, f"'que tal buen dia como esta' no debe ser QUESTION, got {intent}"

    def test_pregunta_con_signo_interrogacion(self):
        """Pregunta con ? SÍ debe ser QUESTION (si no es saludo)."""
        intent = self._classify("cuanto cuesta?")
        assert intent == self.QUESTION, f"'cuanto cuesta?' debe ser QUESTION, got {intent}"

    def test_que_tal_con_interrogacion_no_es_question(self):
        """'que tal?' - saludo con ? NO debe ser QUESTION."""
        intent = self._classify("que tal?")
        assert intent != self.QUESTION, f"'que tal?' no debe ser QUESTION, got {intent}"


# ============================================================
# FIX 796: STT Echo sentence-level dedup
# ============================================================

class TestFix796SentenceLevelDedup:
    """FIX 796: Deduplicar oraciones con inicio común en STT echo."""

    def _dedup_796(self, speech_result):
        """Simula la lógica de FIX 796."""
        if speech_result and len(speech_result) > 30:
            _sentences = re.split(r'(?<=[.!?])\s+', speech_result)
            _sentences = [s.strip() for s in _sentences if s.strip() and len(s.strip()) > 3]
            if len(_sentences) >= 2:
                _unique = []
                for s in _sentences:
                    _sc = re.sub(r'[.,!?¿¡:;]', '', s).lower().strip()
                    _is_dup = False
                    for idx, u in enumerate(_unique):
                        _uc = re.sub(r'[.,!?¿¡:;]', '', u).lower().strip()
                        if len(_sc) > 10 and len(_uc) > 10 and _sc[:10] == _uc[:10]:
                            if len(s) >= len(u):
                                _unique[idx] = s
                            _is_dup = True
                            break
                    if not _is_dup:
                        _unique.append(s)
                if len(_unique) < len(_sentences):
                    return ' '.join(_unique)
        return speech_result

    def test_echo_numero_duplicado(self):
        """Eco con número: primera versión parcial, segunda completa."""
        texto = "Sí, el número es 6623. Sí, el número es 6623531804."
        result = self._dedup_796(texto)
        assert "6623531804" in result
        assert result.count("Sí, el número") == 1

    def test_echo_encargado(self):
        """Eco de 'no está el encargado' duplicado."""
        texto = "No, no está el encargado. No, no está el encargado ahora."
        result = self._dedup_796(texto)
        assert result.count("no está el encargado") <= 1

    def test_texto_corto_no_dedup(self):
        """Texto < 30 chars NO se procesa."""
        texto = "no no está No, no está."
        result = self._dedup_796(texto)
        assert result == texto  # Sin cambio

    def test_oraciones_diferentes_no_dedup(self):
        """Oraciones diferentes NO se deduplicán."""
        texto = "Hola, buen día. Sí, claro que sí. Me interesa mucho."
        result = self._dedup_796(texto)
        assert result == texto

    def test_echo_saludo_duplicado(self):
        """Echo de saludo duplicado."""
        texto = "Hola, buen día, sí está. Hola, buen día, sí, sí está el encargado."
        result = self._dedup_796(texto)
        assert result.count("Hola") == 1

    def test_tres_oraciones_dos_duplicadas(self):
        """3 oraciones, 2 son eco de la primera."""
        texto = "Sí, aquí estamos para atenderle. Dígame su número. Sí, aquí estamos para atenderle, dígame."
        result = self._dedup_796(texto)
        # La primera y tercera comparten inicio
        assert "Dígame su número" in result

    def test_oracion_unica_sin_cambio(self):
        """Una sola oración larga, sin cambio."""
        texto = "Sí, claro que sí, me interesa mucho su producto de ferretería."
        result = self._dedup_796(texto)
        assert result == texto

    def test_inicio_comun_keep_longer(self):
        """De dos oraciones con inicio común, mantener la más larga."""
        texto = "El teléfono es seis seis. El teléfono es seis seis veintitrés cincuenta y tres."
        result = self._dedup_796(texto)
        assert "veintitrés" in result
        assert result.count("El teléfono") == 1


# ============================================================
# FIX 797: CAPTURANDO_CONTACTO + MANAGER_ABSENT/PRESENT/QUESTION
# ============================================================

class TestFix797CapturandoContactoTransiciones:
    """FIX 797: Transiciones faltantes en CAPTURANDO_CONTACTO."""

    def setup_method(self):
        from fsm_engine import FSMEngine, FSMState, FSMIntent, ActionType
        self.engine = FSMEngine()
        self.S = FSMState
        self.I = FSMIntent
        self.A = ActionType

    def test_manager_absent_transicion_existe(self):
        """CAPTURANDO_CONTACTO + MANAGER_ABSENT debe tener transición."""
        key = (self.S.CAPTURANDO_CONTACTO, self.I.MANAGER_ABSENT)
        assert key in self.engine._transitions, "Falta transición CAPTURANDO_CONTACTO + MANAGER_ABSENT"

    def test_manager_present_transicion_existe(self):
        """CAPTURANDO_CONTACTO + MANAGER_PRESENT debe tener transición."""
        key = (self.S.CAPTURANDO_CONTACTO, self.I.MANAGER_PRESENT)
        assert key in self.engine._transitions, "Falta transición CAPTURANDO_CONTACTO + MANAGER_PRESENT"

    def test_question_transicion_existe(self):
        """CAPTURANDO_CONTACTO + QUESTION debe tener transición."""
        key = (self.S.CAPTURANDO_CONTACTO, self.I.QUESTION)
        assert key in self.engine._transitions, "Falta transición CAPTURANDO_CONTACTO + QUESTION"

    def test_manager_absent_queda_en_capturando(self):
        """MANAGER_ABSENT en CAPTURANDO_CONTACTO debe quedar en mismo estado."""
        t = self.engine._transitions[(self.S.CAPTURANDO_CONTACTO, self.I.MANAGER_ABSENT)]
        assert t.next_state == self.S.CAPTURANDO_CONTACTO, \
            f"MANAGER_ABSENT debe mantener CAPTURANDO_CONTACTO, got {t.next_state}"

    def test_manager_present_queda_en_capturando(self):
        """MANAGER_PRESENT en CAPTURANDO_CONTACTO debe quedar en mismo estado."""
        t = self.engine._transitions[(self.S.CAPTURANDO_CONTACTO, self.I.MANAGER_PRESENT)]
        assert t.next_state == self.S.CAPTURANDO_CONTACTO, \
            f"MANAGER_PRESENT debe mantener CAPTURANDO_CONTACTO, got {t.next_state}"

    def test_question_queda_en_capturando(self):
        """QUESTION en CAPTURANDO_CONTACTO debe quedar en mismo estado."""
        t = self.engine._transitions[(self.S.CAPTURANDO_CONTACTO, self.I.QUESTION)]
        assert t.next_state == self.S.CAPTURANDO_CONTACTO, \
            f"QUESTION debe mantener CAPTURANDO_CONTACTO, got {t.next_state}"

    def test_manager_absent_template_digame(self):
        """MANAGER_ABSENT → template digame_numero."""
        t = self.engine._transitions[(self.S.CAPTURANDO_CONTACTO, self.I.MANAGER_ABSENT)]
        assert t.template_key == "digame_numero", f"Expected digame_numero, got {t.template_key}"

    def test_manager_present_template_digame(self):
        """MANAGER_PRESENT → template digame_numero."""
        t = self.engine._transitions[(self.S.CAPTURANDO_CONTACTO, self.I.MANAGER_PRESENT)]
        assert t.template_key == "digame_numero", f"Expected digame_numero, got {t.template_key}"

    def test_question_gpt_narrow(self):
        """QUESTION → GPT_NARROW responder_pregunta_producto."""
        t = self.engine._transitions[(self.S.CAPTURANDO_CONTACTO, self.I.QUESTION)]
        assert t.action_type == self.A.GPT_NARROW, f"Expected GPT_NARROW, got {t.action_type}"
        assert t.template_key == "responder_pregunta_producto"

    def test_echo_no_esta_en_capturando_contacto(self):
        """Simular eco STT 'no está' → MANAGER_ABSENT → se queda en CAPTURANDO_CONTACTO."""
        from fsm_engine import classify_intent, FSMContext
        ctx = FSMContext()
        intent = classify_intent("no no está", ctx, self.S.CAPTURANDO_CONTACTO)
        if intent == self.I.MANAGER_ABSENT:
            key = (self.S.CAPTURANDO_CONTACTO, intent)
            assert key in self.engine._transitions
            t = self.engine._transitions[key]
            assert t.next_state == self.S.CAPTURANDO_CONTACTO


# ============================================================
# Tests de integración: Verificar no regresiones
# ============================================================

class TestFix794797NoRegresiones:
    """Verificar que los fixes no rompen funcionalidad existente."""

    def test_question_real_sigue_funcionando(self):
        """Preguntas reales siguen clasificándose como QUESTION."""
        from fsm_engine import classify_intent, FSMContext, FSMState, FSMIntent
        ctx = FSMContext()
        preguntas = [
            "que productos manejan",
            "cual es el precio",
            "como puedo hacer un pedido",
            "donde estan ubicados",
            "cuanto cuesta el envio",
        ]
        for p in preguntas:
            intent = classify_intent(p, ctx, FSMState.BUSCANDO_ENCARGADO)
            assert intent == FSMIntent.QUESTION, f"'{p}' debe ser QUESTION, got {intent}"

    def test_capturando_contacto_transiciones_previas(self):
        """Transiciones existentes en CAPTURANDO_CONTACTO siguen funcionando."""
        from fsm_engine import FSMEngine, FSMState, FSMIntent
        engine = FSMEngine()
        intents_previos = [
            FSMIntent.OFFER_DATA,
            FSMIntent.CONFIRMATION,
            FSMIntent.DICTATING_PARTIAL,
            FSMIntent.DICTATING_COMPLETE_PHONE,
            FSMIntent.DICTATING_COMPLETE_EMAIL,
            FSMIntent.REJECT_DATA,
            FSMIntent.NO_INTEREST,
            FSMIntent.FAREWELL,
            FSMIntent.VERIFICATION,
            FSMIntent.UNKNOWN,
            FSMIntent.CONTINUATION,
            FSMIntent.IDENTITY,
            FSMIntent.WRONG_NUMBER,
        ]
        for intent in intents_previos:
            key = (FSMState.CAPTURANDO_CONTACTO, intent)
            assert key in engine._transitions, f"Falta transición previa: CAPTURANDO_CONTACTO + {intent}"

    def test_convertir_numeros_no_rompe_texto_normal(self):
        """convertir_numeros_escritos_a_digitos no modifica texto sin números."""
        from agente_ventas import convertir_numeros_escritos_a_digitos
        texto = "hola buen día, sí claro"
        resultado = convertir_numeros_escritos_a_digitos(texto)
        assert "hola" in resultado.lower()


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
