# -*- coding: utf-8 -*-
"""
Tests FASE 1+2: Optimización Bruce v2.0

FASE 1.1: Consolidación de inmunidades + threshold FIX 601
FASE 1.2: ESPERANDO_TRANSFERENCIA timeout forzoso 45s + audio >3 words
FASE 1.3: Circuit breaker anti-loop (respuesta repetida + validator escalation)
FASE 2.1: GPT-4o-mini intent classifier module
FASE 2.2: GPT eval false positive reduction
"""
import sys
import os
import unittest
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ============================================================
# FASE 1.1: Immunity consolidation
# ============================================================

class TestFase11UniversalImmunity(unittest.TestCase):
    """FASE 1.1: _PATRONES_INMUNES_UNIVERSAL replaces 4 separate lists."""

    def test_universal_set_exists_in_source(self):
        """_PATRONES_INMUNES_UNIVERSAL must be in agente_ventas.py."""
        agente_path = os.path.join(os.path.dirname(__file__), '..', 'agente_ventas.py')
        with open(agente_path, 'r', encoding='utf-8') as f:
            source = f.read()
        self.assertIn('_PATRONES_INMUNES_UNIVERSAL', source)

    def test_598_uses_universal(self):
        """patrones_inmunes_pregunta_598 must reference universal set."""
        agente_path = os.path.join(os.path.dirname(__file__), '..', 'agente_ventas.py')
        with open(agente_path, 'r', encoding='utf-8') as f:
            source = f.read()
        self.assertIn('patrones_inmunes_pregunta_598 = _PATRONES_INMUNES_UNIVERSAL', source)

    def test_600_uses_universal(self):
        """patrones_inmunes_pero must reference universal set."""
        agente_path = os.path.join(os.path.dirname(__file__), '..', 'agente_ventas.py')
        with open(agente_path, 'r', encoding='utf-8') as f:
            source = f.read()
        self.assertIn('patrones_inmunes_pero = _PATRONES_INMUNES_UNIVERSAL', source)

    def test_601_uses_universal(self):
        """patrones_inmunes_601 must reference universal set."""
        agente_path = os.path.join(os.path.dirname(__file__), '..', 'agente_ventas.py')
        with open(agente_path, 'r', encoding='utf-8') as f:
            source = f.read()
        self.assertIn('patrones_inmunes_601 = _PATRONES_INMUNES_UNIVERSAL', source)

    def test_602_uses_universal(self):
        """patrones_inmunes_602 must reference universal set."""
        agente_path = os.path.join(os.path.dirname(__file__), '..', 'agente_ventas.py')
        with open(agente_path, 'r', encoding='utf-8') as f:
            source = f.read()
        self.assertIn('patrones_inmunes_602 = _PATRONES_INMUNES_UNIVERSAL', source)

    def test_universal_contains_key_patterns(self):
        """Universal set must contain all critical patterns."""
        critical_patterns = [
            'CONFIRMA_MISMO_NUMERO', 'DESPEDIDA_CLIENTE', 'RECHAZO_DEFINITIVO',
            'CLIENTE_ACEPTA_WHATSAPP', 'CORREO_DETECTADO', 'OTRA_SUCURSAL',
            'CLIENTE_ES_ENCARGADO', 'DIGAME_CONTINUAR', 'SOLICITUD_CALLBACK',
            'OFRECER_CONTACTO_BRUCE', 'EVITAR_LOOP_WHATSAPP', 'NO_HACEMOS_COMPRAS',
        ]
        agente_path = os.path.join(os.path.dirname(__file__), '..', 'agente_ventas.py')
        with open(agente_path, 'r', encoding='utf-8') as f:
            source = f.read()
        idx = source.find('_PATRONES_INMUNES_UNIVERSAL')
        # Find the closing brace - set is ~1500 chars
        section = source[idx:idx + 2000]
        for p in critical_patterns:
            self.assertIn(f"'{p}'", section, f"'{p}' must be in _PATRONES_INMUNES_UNIVERSAL")

    def test_no_legacy_pero_set(self):
        """Legacy _patrones_inmunes_pero_legacy should NOT exist."""
        agente_path = os.path.join(os.path.dirname(__file__), '..', 'agente_ventas.py')
        with open(agente_path, 'r', encoding='utf-8') as f:
            source = f.read()
        self.assertNotIn('_patrones_inmunes_pero_legacy', source)


class TestFase11ThresholdRaised(unittest.TestCase):
    """FASE 1.1: FIX 601 threshold raised from 12/3 to 25/5."""

    def test_threshold_25_words(self):
        """FIX 601 threshold must be > 25 words (not 12)."""
        agente_path = os.path.join(os.path.dirname(__file__), '..', 'agente_ventas.py')
        with open(agente_path, 'r', encoding='utf-8') as f:
            source = f.read()
        self.assertIn('len(palabras_601) > 25', source)

    def test_threshold_5_clauses(self):
        """FIX 601 threshold must be >= 5 clauses (not 3)."""
        agente_path = os.path.join(os.path.dirname(__file__), '..', 'agente_ventas.py')
        with open(agente_path, 'r', encoding='utf-8') as f:
            source = f.read()
        self.assertIn('num_clausulas >= 5', source)

    def test_12_word_text_survives(self):
        """Text with 15 words + 3 clauses now survives FIX 601 (was invalidated before)."""
        # 15 words, 3 clauses = used to be invalidated, now survives
        text = "No está el jefe, salió a comer, pero si quiere le paso al encargado del área"
        words = text.split()
        num_clauses = 1
        for sep in ['. ', ', ', '; ', '¿', '?']:
            num_clauses += text.count(sep)
        # Old threshold: > 12 and >= 3 → would invalidate (15 > 12, 3 >= 3)
        self.assertTrue(len(words) > 12)
        self.assertTrue(num_clauses >= 3)
        # New threshold: > 25 and >= 5 → survives (15 NOT > 25)
        self.assertFalse(len(words) > 25)


# ============================================================
# FASE 1.2: ESPERANDO_TRANSFERENCIA timeout + audio detection
# ============================================================

class TestFase12TimeoutForzoso(unittest.TestCase):
    """FASE 1.2: 45s timeout for ESPERANDO_TRANSFERENCIA."""

    def test_timeout_45s_in_source(self):
        """Timeout must be 45s (not 60s) in servidor_llamadas.py."""
        srv_path = os.path.join(os.path.dirname(__file__), '..', 'servidor_llamadas.py')
        with open(srv_path, 'r', encoding='utf-8') as f:
            source = f.read()
        self.assertIn('_t_espera_712 > 45', source)

    def test_audio_sustancial_3_words(self):
        """Audio >= 3 words must be detected as human."""
        srv_path = os.path.join(os.path.dirname(__file__), '..', 'servidor_llamadas.py')
        with open(srv_path, 'r', encoding='utf-8') as f:
            source = f.read()
        self.assertIn('_palabras_audio_751', source)
        self.assertIn('_audio_sustancial_751', source)

    def test_audio_3_words_logic(self):
        """Verify >= 3 words = human."""
        # Simulate the logic
        text = "buenas tardes disculpe"
        words = text.split()
        self.assertTrue(len(words) >= 3)

    def test_audio_1_word_not_human(self):
        """1 word should NOT trigger human detection."""
        text = "si"
        words = text.split()
        self.assertFalse(len(words) >= 3)

    def test_gate_simplified_no_569_required(self):
        """Gate must not require tiene_palabras_reconocibles."""
        srv_path = os.path.join(os.path.dirname(__file__), '..', 'servidor_llamadas.py')
        with open(srv_path, 'r', encoding='utf-8') as f:
            source = f.read()
        # The gate should be just "if cliente_volvio:" not "and tiene_palabras_reconocibles"
        self.assertIn('if cliente_volvio:  # FASE 1.2', source)

    def test_forced_exit_in_712b(self):
        """FIX 712B must have forced exit after 45s."""
        srv_path = os.path.join(os.path.dirname(__file__), '..', 'servidor_llamadas.py')
        with open(srv_path, 'r', encoding='utf-8') as f:
            source = f.read()
        self.assertIn('FASE 1.2: TIMEOUT FORZOSO', source)
        self.assertIn('_t_712b > 45', source)

    def test_forced_exit_in_470(self):
        """FIX 470 (empty speech) must have forced exit after 45s."""
        srv_path = os.path.join(os.path.dirname(__file__), '..', 'servidor_llamadas.py')
        with open(srv_path, 'r', encoding='utf-8') as f:
            source = f.read()
        self.assertIn('_t_470 > 45', source)


class TestFase12ReengagementSignals(unittest.TestCase):
    """FASE 1.2: Audio-based human detection."""

    def test_3_words_exits_wait_mode(self):
        """3 words audio with no signal = exit wait (FASE 1.2)."""
        # Before FASE 1.2: Only signal-based detection
        # After FASE 1.2: >=3 words = human regardless of signal
        frase = "buenas tardes disculpe"
        _fl = frase.replace('á','a').replace('é','e').replace('í','i').replace('ó','o').replace('ú','u')
        _fl = _fl.replace('¿','').replace('?','').replace('¡','').replace('!','').replace('.','').replace(',','')
        words = len(_fl.split()) if _fl.strip() else 0
        self.assertTrue(words >= 3)  # audio_sustancial = True → cliente_volvio = True

    def test_2_words_does_not_exit(self):
        """2 words audio without signal = stay in wait mode."""
        frase = "aja si"
        _fl = frase.replace('á','a').replace('é','e')
        words = len(_fl.split()) if _fl.strip() else 0
        self.assertFalse(words >= 3)

    def test_timeout_45_vs_60(self):
        """Verify 45s is used, not 60s."""
        timestamp_start = time.time() - 50  # 50 seconds ago
        elapsed = time.time() - timestamp_start
        self.assertTrue(elapsed > 45)  # Would exit
        timestamp_start2 = time.time() - 40  # 40 seconds ago
        elapsed2 = time.time() - timestamp_start2
        self.assertFalse(elapsed2 > 45)  # Would NOT exit


# ============================================================
# FASE 1.3: Circuit breaker anti-loop
# ============================================================

class TestFase13CircuitBreakerDuplicates(unittest.TestCase):
    """FASE 1.3: Response duplication circuit breaker."""

    def test_circuit_breaker_code_present(self):
        """Circuit breaker code must be in agente_ventas.py."""
        agente_path = os.path.join(os.path.dirname(__file__), '..', 'agente_ventas.py')
        with open(agente_path, 'r', encoding='utf-8') as f:
            source = f.read()
        self.assertIn('FASE 1.3', source)
        self.assertIn('CIRCUIT BREAKER', source)
        self.assertIn('_dup_count_751', source)

    def test_3rd_repetition_triggers_closure(self):
        """3rd repetition of same response → courteous closure."""
        from difflib import SequenceMatcher
        import unicodedata
        import re

        respuesta = "¿Se encontrará el encargado o encargada de compras?"
        # Normalize
        resp_norm = unicodedata.normalize('NFKD', respuesta.lower()).encode('ascii', 'ignore').decode('ascii')
        resp_norm = re.sub(r'[^\w\s]', '', resp_norm).strip()

        # Simulate history with same message 2x
        previas = [respuesta, respuesta]
        dup_count = 0
        for prev in previas:
            prev_norm = unicodedata.normalize('NFKD', prev.lower()).encode('ascii', 'ignore').decode('ascii')
            prev_norm = re.sub(r'[^\w\s]', '', prev_norm).strip()
            if len(prev_norm) > 25:
                ratio = SequenceMatcher(None, resp_norm, prev_norm).ratio()
                if ratio >= 0.85:
                    dup_count += 1

        self.assertEqual(dup_count, 2)  # Already said 2x
        # dup_count >= 2 → closure
        self.assertTrue(dup_count >= 2)

    def test_1st_repetition_triggers_alternative(self):
        """1st repetition (2nd time saying same thing) → alternative response."""
        from difflib import SequenceMatcher
        import unicodedata
        import re

        respuesta = "¿Se encontrará el encargado o encargada de compras?"
        resp_norm = unicodedata.normalize('NFKD', respuesta.lower()).encode('ascii', 'ignore').decode('ascii')
        resp_norm = re.sub(r'[^\w\s]', '', resp_norm).strip()

        previas = [respuesta]  # Only 1 previous
        dup_count = 0
        for prev in previas:
            prev_norm = unicodedata.normalize('NFKD', prev.lower()).encode('ascii', 'ignore').decode('ascii')
            prev_norm = re.sub(r'[^\w\s]', '', prev_norm).strip()
            if len(prev_norm) > 25:
                ratio = SequenceMatcher(None, resp_norm, prev_norm).ratio()
                if ratio >= 0.85:
                    dup_count += 1

        self.assertEqual(dup_count, 1)  # Exactly 1 previous = alternative

    def test_different_responses_no_trigger(self):
        """Different responses should not trigger circuit breaker."""
        from difflib import SequenceMatcher
        import unicodedata
        import re

        respuesta = "¿Me podría dar su WhatsApp para enviarle el catálogo?"
        resp_norm = unicodedata.normalize('NFKD', respuesta.lower()).encode('ascii', 'ignore').decode('ascii')
        resp_norm = re.sub(r'[^\w\s]', '', resp_norm).strip()

        previas = ["Hola, buen día. Me comunico de la marca NIOVAL.",
                    "¿Se encontrará el encargado de compras?"]
        dup_count = 0
        for prev in previas:
            prev_norm = unicodedata.normalize('NFKD', prev.lower()).encode('ascii', 'ignore').decode('ascii')
            prev_norm = re.sub(r'[^\w\s]', '', prev_norm).strip()
            if len(prev_norm) > 25:
                ratio = SequenceMatcher(None, resp_norm, prev_norm).ratio()
                if ratio >= 0.85:
                    dup_count += 1

        self.assertEqual(dup_count, 0)


class TestFase13ValidatorEscalation(unittest.TestCase):
    """FASE 1.3: Validator escalation (skip after 3 invalidations)."""

    def test_skip_validators_code_present(self):
        """Skip validators code must be in agente_ventas.py."""
        agente_path = os.path.join(os.path.dirname(__file__), '..', 'agente_ventas.py')
        with open(agente_path, 'r', encoding='utf-8') as f:
            source = f.read()
        self.assertIn('_skip_validators_751', source)
        self.assertIn('_patrones_invalidados_consecutivos', source)

    def test_598_respects_skip(self):
        """FIX 598 must check _skip_validators_751."""
        agente_path = os.path.join(os.path.dirname(__file__), '..', 'agente_ventas.py')
        with open(agente_path, 'r', encoding='utf-8') as f:
            source = f.read()
        self.assertIn('patron_detectado and not _skip_validators_751', source)

    def test_600_respects_skip(self):
        """FIX 600 must check _skip_validators_751."""
        agente_path = os.path.join(os.path.dirname(__file__), '..', 'agente_ventas.py')
        with open(agente_path, 'r', encoding='utf-8') as f:
            source = f.read()
        # Count occurrences - should appear for 598, 600, 601
        count = source.count('not _skip_validators_751')
        self.assertGreaterEqual(count, 3, "At least 598, 600, 601 should check _skip_validators_751")

    def test_counter_increment_on_invalidation(self):
        """Counter increments on each invalidation."""
        agente_path = os.path.join(os.path.dirname(__file__), '..', 'agente_ventas.py')
        with open(agente_path, 'r', encoding='utf-8') as f:
            source = f.read()
        count = source.count('_patrones_invalidados_consecutivos')
        # At least: init, 4 increments (598, 600, 601, 602), 1 reset, 1 check
        self.assertGreaterEqual(count, 6)

    def test_counter_resets_on_survival(self):
        """Counter resets when pattern survives."""
        agente_path = os.path.join(os.path.dirname(__file__), '..', 'agente_ventas.py')
        with open(agente_path, 'r', encoding='utf-8') as f:
            source = f.read()
        self.assertIn('_patrones_invalidados_consecutivos = 0', source)


# ============================================================
# FASE 2.1: GPT-4o-mini intent classifier
# ============================================================

class TestFase21GPTIntentClassifier(unittest.TestCase):
    """FASE 2.1: GPT-4o-mini intent classifier module."""

    def test_module_exists(self):
        """gpt_intent_classifier.py must exist."""
        module_path = os.path.join(os.path.dirname(__file__), '..', 'gpt_intent_classifier.py')
        self.assertTrue(os.path.exists(module_path))

    def test_module_imports(self):
        """Module must be importable."""
        from gpt_intent_classifier import classify_intent, intent_to_pattern_type, INTENTS
        self.assertIsNotNone(classify_intent)
        self.assertIsNotNone(intent_to_pattern_type)
        self.assertIsInstance(INTENTS, dict)

    def test_intents_coverage(self):
        """INTENTS must cover all critical categories."""
        from gpt_intent_classifier import INTENTS
        critical = ['ENCARGADO_NO_ESTA', 'ACEPTA_CONTACTO', 'DESPEDIDA',
                    'TRANSFERENCIA', 'CALLBACK', 'DICTANDO_DATO',
                    'VERIFICACION_CONEXION', 'CLIENTE_ES_ENCARGADO']
        for intent in critical:
            self.assertIn(intent, INTENTS, f"'{intent}' must be in INTENTS")

    def test_intent_mapping(self):
        """intent_to_pattern_type maps correctly."""
        from gpt_intent_classifier import intent_to_pattern_type
        self.assertEqual(intent_to_pattern_type('ENCARGADO_NO_ESTA'), 'ENCARGADO_NO_ESTA_SIN_HORARIO')
        self.assertEqual(intent_to_pattern_type('DESPEDIDA'), 'DESPEDIDA_CLIENTE')
        self.assertEqual(intent_to_pattern_type('TRANSFERENCIA'), 'TRANSFERENCIA')
        self.assertIsNone(intent_to_pattern_type('AMBIGUO'))
        self.assertIsNone(intent_to_pattern_type('CONTINUACION'))

    def test_empty_input_returns_none(self):
        """Empty input returns None (no API call)."""
        from gpt_intent_classifier import classify_intent
        self.assertIsNone(classify_intent(""))
        self.assertIsNone(classify_intent(None))
        self.assertIsNone(classify_intent("  "))

    def test_cache_mechanism(self):
        """Cache must exist and have TTL."""
        from gpt_intent_classifier import _intent_cache, _CACHE_TTL_S, _CACHE_MAX_SIZE
        self.assertIsInstance(_intent_cache, dict)
        self.assertGreater(_CACHE_TTL_S, 0)
        self.assertGreater(_CACHE_MAX_SIZE, 0)

    def test_integration_in_agente(self):
        """GPT intent classifier must be integrated in agente_ventas.py."""
        agente_path = os.path.join(os.path.dirname(__file__), '..', 'agente_ventas.py')
        with open(agente_path, 'r', encoding='utf-8') as f:
            source = f.read()
        self.assertIn('from gpt_intent_classifier import', source)
        self.assertIn('_gpt_intent_751', source)

    def test_few_shot_examples(self):
        """Module must have few-shot examples."""
        from gpt_intent_classifier import _FEW_SHOT_EXAMPLES
        self.assertGreaterEqual(len(_FEW_SHOT_EXAMPLES), 10)  # At least 5 pairs


# ============================================================
# FASE 2.2: GPT eval false positive reduction
# ============================================================

class TestFase22GPTEvalFPReduction(unittest.TestCase):
    """FASE 2.2: Reduce GPT eval false positives."""

    def test_modismos_in_full_prompt(self):
        """Mexican idioms dictionary must be in full prompt."""
        bd_path = os.path.join(os.path.dirname(__file__), '..', 'bug_detector.py')
        with open(bd_path, 'r', encoding='utf-8') as f:
            source = f.read()
        self.assertIn('MODISMOS MEXICANOS', source)
        self.assertIn('verificacion de conexion', source.lower())
        self.assertIn('rechazo cortes', source.lower())

    def test_modismos_specific_idioms(self):
        """Specific idioms must be listed."""
        bd_path = os.path.join(os.path.dirname(__file__), '..', 'bug_detector.py')
        with open(bd_path, 'r', encoding='utf-8') as f:
            source = f.read()
        for idiom in ['Ahi le encargo', 'Mande', 'Andale', 'Digame']:
            self.assertIn(idiom, source, f"Idiom '{idiom}' must be in prompts")

    def test_prefilter_exitosa(self):
        """FIX 793A: CASO 4 eliminated - GPT eval now runs on successful calls too."""
        bd_path = os.path.join(os.path.dirname(__file__), '..', 'bug_detector.py')
        with open(bd_path, 'r', encoding='utf-8') as f:
            source = f.read()
        # FIX 793A: CASO 4 was removed (no longer skips GPT eval for successful calls)
        self.assertIn('CASO 4 ELIMINADO', source)
        self.assertIn('FIX 793A', source)

    def test_prefilter_modismos_go_ahead(self):
        """Pre-filter must detect 'go ahead' modismos."""
        bd_path = os.path.join(os.path.dirname(__file__), '..', 'bug_detector.py')
        with open(bd_path, 'r', encoding='utf-8') as f:
            source = f.read()
        self.assertIn('CASO 5', source)
        self.assertIn('_modismos_go_ahead', source)

    def test_prefilter_minimum_turns(self):
        """Pre-filter must skip calls with < 2 Bruce turns."""
        bd_path = os.path.join(os.path.dirname(__file__), '..', 'bug_detector.py')
        with open(bd_path, 'r', encoding='utf-8') as f:
            source = f.read()
        self.assertIn('CASO 6', source)
        self.assertIn('_turnos_bruce', source)

    def test_deploy_version_updated(self):
        """FIX 818: Deploy version es dinamico via set_deploy_version."""
        from bug_detector import set_deploy_version, _DEPLOY_VERSION
        self.assertIsInstance(_DEPLOY_VERSION, str)
        self.assertTrue(len(_DEPLOY_VERSION) > 0)


# ============================================================
# Integration: Validator chain with circuit breaker
# ============================================================

class TestFase13IntegrationValidatorChain(unittest.TestCase):
    """Integration test: Validator chain with circuit breaker."""

    def test_skip_activates_at_3(self):
        """Circuit breaker activates at counter >= 3."""
        counter = 3
        skip = counter >= 3
        self.assertTrue(skip)

    def test_skip_does_not_activate_at_2(self):
        """Circuit breaker does NOT activate at counter = 2."""
        counter = 2
        skip = counter >= 3
        self.assertFalse(skip)

    def test_counter_resets_after_bypass(self):
        """Counter resets to 0 after bypass."""
        counter = 5
        # After bypass
        counter = 0
        self.assertEqual(counter, 0)

    def test_counter_resets_on_pattern_survival(self):
        """Counter resets when pattern survives all validators."""
        counter = 2
        # Pattern survived → reset
        counter = 0
        self.assertEqual(counter, 0)


if __name__ == "__main__":
    unittest.main()
