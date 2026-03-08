"""
Tests FIX 768: Caché Adaptativo para GPT_NARROW
================================================
Verifica normalización, store/lookup, fuzzy matching,
eviction, TTL, persistencia y integración con FSM.
"""
import os
import sys
import json
import unittest
import tempfile
from datetime import datetime, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from fsm_engine import NarrowResponseCache


class TestNormalization(unittest.TestCase):
    """A. Normalización de texto para cache keys."""

    def test_accents_removed(self):
        self.assertEqual(NarrowResponseCache._normalize("¿Dónde están?"), "donde estan")

    def test_punctuation_removed(self):
        self.assertEqual(NarrowResponseCache._normalize("¡Hola! ¿Qué tal?"), "hola que tal")

    def test_spaces_collapsed(self):
        self.assertEqual(NarrowResponseCache._normalize("  hola   mundo  "), "hola mundo")

    def test_uppercase_lowered(self):
        self.assertEqual(NarrowResponseCache._normalize("TIENEN PRODUCTOS"), "tienen productos")

    def test_mixed_normalization(self):
        self.assertEqual(
            NarrowResponseCache._normalize("¿Manejan eléctricos?"),
            "manejan electricos"
        )

    def test_empty_string(self):
        self.assertEqual(NarrowResponseCache._normalize(""), "")

    def test_numbers_preserved(self):
        self.assertEqual(NarrowResponseCache._normalize("tiene 10 productos?"), "tiene 10 productos")


class TestStoreLookup(unittest.TestCase):
    """B. Store + Lookup básico."""

    def setUp(self):
        self.cache = NarrowResponseCache()
        self.cache._cache = {}  # Start fresh
        self.cache.CACHE_FILE = os.path.join(tempfile.gettempdir(), "test_narrow_cache_768.json")

    def test_store_once_lookup_returns_none(self):
        """Store 1x → lookup returns None (count=1 < MIN_HITS=2)."""
        self.cache.store("buscando_encargado", "responder_pregunta_producto",
                         "¿Tienen productos eléctricos?",
                         "Sí, manejamos amplia línea de productos eléctricos.")
        result = self.cache.lookup("buscando_encargado", "responder_pregunta_producto",
                                   "¿Tienen productos eléctricos?")
        self.assertIsNone(result)

    def test_store_once_then_store_again_lookup_returns_cached(self):
        """Store 2x (simulating 2 GPT calls) → lookup on 3rd returns cached."""
        q = "¿Tienen productos eléctricos?"
        resp = "Sí, manejamos amplia línea de productos eléctricos."
        self.cache.store("buscando_encargado", "responder_pregunta_producto", q, resp)
        self.cache.store("buscando_encargado", "responder_pregunta_producto", q, resp)
        # Now count=2, which equals MIN_HITS
        result = self.cache.lookup("buscando_encargado", "responder_pregunta_producto", q)
        self.assertEqual(result, resp)

    def test_store_empty_response_not_cached(self):
        """Store empty response → no cachea."""
        self.cache.store("buscando_encargado", "conversacion_libre", "hola", "")
        self.assertEqual(len(self.cache._cache), 0)

    def test_store_short_response_not_cached(self):
        """Store short response (<5 chars) → no cachea."""
        self.cache.store("buscando_encargado", "conversacion_libre", "hola", "ok")
        self.assertEqual(len(self.cache._cache), 0)

    def test_different_states_different_keys(self):
        """Same question in different states = different cache keys."""
        q = "¿Qué marcas manejan?"
        resp = "Manejamos marcas como Truper, Volteck, Pretul."
        self.cache.store("buscando_encargado", "responder_pregunta_producto", q, resp)
        self.cache.store("buscando_encargado", "responder_pregunta_producto", q, resp)
        self.cache.store("encargado_presente", "responder_pregunta_producto", q, resp)

        # buscando_encargado has count=2 → hit
        result1 = self.cache.lookup("buscando_encargado", "responder_pregunta_producto", q)
        self.assertEqual(result1, resp)

        # encargado_presente has count=1 → miss
        result2 = self.cache.lookup("encargado_presente", "responder_pregunta_producto", q)
        self.assertIsNone(result2)

    def test_different_prompt_keys_different_keys(self):
        """Same question with different prompt_key = different cache keys."""
        q = "¿Tienen productos?"
        resp = "Sí, tenemos de todo."
        self.cache.store("buscando_encargado", "responder_pregunta_producto", q, resp)
        self.cache.store("buscando_encargado", "responder_pregunta_producto", q, resp)

        result1 = self.cache.lookup("buscando_encargado", "responder_pregunta_producto", q)
        self.assertEqual(result1, resp)

        result2 = self.cache.lookup("buscando_encargado", "conversacion_libre", q)
        self.assertIsNone(result2)


class TestFuzzyMatching(unittest.TestCase):
    """C. Fuzzy matching para preguntas similares."""

    def setUp(self):
        self.cache = NarrowResponseCache()
        self.cache._cache = {}
        self.cache.CACHE_FILE = os.path.join(tempfile.gettempdir(), "test_narrow_cache_fuzzy.json")

    def test_fuzzy_hit_similar_question(self):
        """'tienen productos electricos' ~ 'tiene productos electricos' → hit."""
        resp = "Sí, manejamos productos eléctricos."
        # Store original 2x
        self.cache.store("buscando_encargado", "responder_pregunta_producto",
                         "tienen productos electricos", resp)
        self.cache.store("buscando_encargado", "responder_pregunta_producto",
                         "tienen productos electricos", resp)
        # Lookup with similar (not exact)
        result = self.cache.lookup("buscando_encargado", "responder_pregunta_producto",
                                   "tiene productos electricos")
        self.assertEqual(result, resp)

    def test_fuzzy_hit_singular_plural(self):
        """'que marcas manejan' ~ 'que marca manejan' → hit."""
        resp = "Manejamos Truper, Volteck y más."
        self.cache.store("buscando_encargado", "responder_pregunta_producto",
                         "que marcas manejan", resp)
        self.cache.store("buscando_encargado", "responder_pregunta_producto",
                         "que marcas manejan", resp)
        result = self.cache.lookup("buscando_encargado", "responder_pregunta_producto",
                                   "que marca manejan")
        self.assertEqual(result, resp)

    def test_fuzzy_no_match_different_question(self):
        """'donde estan' ≠ 'como estan' → no match."""
        resp = "Estamos en Guadalajara."
        self.cache.store("buscando_encargado", "responder_pregunta_producto",
                         "donde estan", resp)
        self.cache.store("buscando_encargado", "responder_pregunta_producto",
                         "donde estan", resp)
        result = self.cache.lookup("buscando_encargado", "responder_pregunta_producto",
                                   "como estan")
        self.assertIsNone(result)

    def test_fuzzy_increments_existing_count(self):
        """Fuzzy match below threshold → increments count of existing."""
        resp = "Sí, tenemos de todo."
        self.cache.store("buscando_encargado", "responder_pregunta_producto",
                         "tienen productos electricos", resp)
        # count=1 now. Fuzzy lookup increments to 2
        result = self.cache.lookup("buscando_encargado", "responder_pregunta_producto",
                                   "tiene productos electricos")
        self.assertIsNone(result)  # Still below threshold on this call

        # But count was incremented to 2, so next exact lookup should hit
        result2 = self.cache.lookup("buscando_encargado", "responder_pregunta_producto",
                                    "tienen productos electricos")
        self.assertIsNotNone(result2)


class TestEvictionTTL(unittest.TestCase):
    """D. Eviction y TTL."""

    def setUp(self):
        self.cache = NarrowResponseCache()
        self.cache._cache = {}
        self.cache.CACHE_FILE = os.path.join(tempfile.gettempdir(), "test_narrow_cache_evict.json")

    def test_eviction_when_max_exceeded(self):
        """MAX_ENTRIES exceeded → oldest evicted."""
        self.cache.MAX_ENTRIES = 10
        for i in range(15):
            key = f"state::prompt::question{i}"
            self.cache._cache[key] = {
                "question_original": f"question{i}",
                "response": f"response{i}",
                "count": 1,
                "first_seen": datetime.now().isoformat(),
                "last_seen": (datetime.now() - timedelta(hours=15 - i)).isoformat(),
            }
        self.cache._evict()
        self.assertLessEqual(len(self.cache._cache), 10)

    def test_high_count_survives_eviction(self):
        """Entries with high count survive eviction."""
        self.cache.MAX_ENTRIES = 5
        # Add popular entry
        self.cache._cache["state::prompt::popular"] = {
            "question_original": "popular",
            "response": "popular response",
            "count": 100,
            "first_seen": datetime.now().isoformat(),
            "last_seen": datetime.now().isoformat(),
        }
        # Add 8 low-count entries
        for i in range(8):
            self.cache._cache[f"state::prompt::low{i}"] = {
                "question_original": f"low{i}",
                "response": f"low{i}",
                "count": 1,
                "first_seen": datetime.now().isoformat(),
                "last_seen": (datetime.now() - timedelta(hours=i + 1)).isoformat(),
            }
        self.cache._evict()
        self.assertIn("state::prompt::popular", self.cache._cache)

    def test_ttl_expired_cleaned_on_load(self):
        """TTL expired entries cleaned on _load()."""
        expired_data = {
            "state::prompt::old": {
                "question_original": "old question",
                "response": "old response",
                "count": 5,
                "first_seen": (datetime.now() - timedelta(days=60)).isoformat(),
                "last_seen": (datetime.now() - timedelta(days=45)).isoformat(),
            },
            "state::prompt::fresh": {
                "question_original": "fresh question",
                "response": "fresh response",
                "count": 3,
                "first_seen": datetime.now().isoformat(),
                "last_seen": datetime.now().isoformat(),
            },
        }
        tmp_file = os.path.join(tempfile.gettempdir(), "test_ttl_cache.json")
        with open(tmp_file, 'w', encoding='utf-8') as f:
            json.dump(expired_data, f)

        self.cache.CACHE_FILE = tmp_file
        self.cache._load()
        self.assertNotIn("state::prompt::old", self.cache._cache)
        self.assertIn("state::prompt::fresh", self.cache._cache)

        # Cleanup
        if os.path.exists(tmp_file):
            os.remove(tmp_file)


class TestPersistence(unittest.TestCase):
    """E. Persistencia a JSON."""

    def setUp(self):
        self.tmp_file = os.path.join(tempfile.gettempdir(), "test_narrow_persist.json")
        self.cache = NarrowResponseCache()
        self.cache._cache = {}
        self.cache.CACHE_FILE = self.tmp_file

    def tearDown(self):
        if os.path.exists(self.tmp_file):
            os.remove(self.tmp_file)

    def test_save_creates_json(self):
        """_save() creates JSON file."""
        self.cache._cache["test::key::hello"] = {
            "question_original": "hello",
            "response": "world",
            "count": 3,
            "first_seen": datetime.now().isoformat(),
            "last_seen": datetime.now().isoformat(),
        }
        self.cache._save()
        self.assertTrue(os.path.exists(self.tmp_file))
        with open(self.tmp_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        self.assertIn("test::key::hello", data)

    def test_load_restores_entries(self):
        """_load() restores entries from JSON."""
        data = {
            "state::prompt::question": {
                "question_original": "question",
                "response": "answer",
                "count": 5,
                "first_seen": datetime.now().isoformat(),
                "last_seen": datetime.now().isoformat(),
            }
        }
        with open(self.tmp_file, 'w', encoding='utf-8') as f:
            json.dump(data, f)
        self.cache._load()
        self.assertIn("state::prompt::question", self.cache._cache)
        self.assertEqual(self.cache._cache["state::prompt::question"]["count"], 5)


class TestStats(unittest.TestCase):
    """F. Stats y utilidades."""

    def setUp(self):
        self.cache = NarrowResponseCache()
        self.cache._cache = {}

    def test_stats_empty(self):
        stats = self.cache.stats()
        self.assertEqual(stats["total_entries"], 0)
        self.assertEqual(stats["promoted"], 0)
        self.assertEqual(stats["total_hits"], 0)

    def test_stats_with_entries(self):
        self.cache._cache["k1"] = {"count": 5, "response": "a"}
        self.cache._cache["k2"] = {"count": 1, "response": "b"}
        self.cache._cache["k3"] = {"count": 3, "response": "c"}
        stats = self.cache.stats()
        self.assertEqual(stats["total_entries"], 3)
        self.assertEqual(stats["promoted"], 2)  # k1(5) + k3(3) >= MIN_HITS=2
        self.assertEqual(stats["total_hits"], 8)  # 5 + 3

    def test_make_key_format(self):
        key = self.cache._make_key("buscando_encargado", "responder_pregunta_producto", "hola")
        self.assertEqual(key, "buscando_encargado::responder_pregunta_producto::hola")

    def test_flush_persists(self):
        tmp_file = os.path.join(tempfile.gettempdir(), "test_flush.json")
        self.cache.CACHE_FILE = tmp_file
        self.cache._cache["test::key::x"] = {
            "question_original": "x",
            "response": "y",
            "count": 1,
            "first_seen": datetime.now().isoformat(),
            "last_seen": datetime.now().isoformat(),
        }
        self.cache.flush()
        self.assertTrue(os.path.exists(tmp_file))
        if os.path.exists(tmp_file):
            os.remove(tmp_file)


class TestIntegration(unittest.TestCase):
    """G. Integración con FSM."""

    def test_narrow_cache_singleton_exists(self):
        """narrow_cache singleton exists in fsm_engine module."""
        from fsm_engine import narrow_cache
        self.assertIsInstance(narrow_cache, NarrowResponseCache)

    def test_fsm_engine_has_cache_in_gpt_narrow(self):
        """_call_gpt_narrow references narrow_cache."""
        import inspect
        from fsm_engine import FSMEngine
        source = inspect.getsource(FSMEngine._call_gpt_narrow)
        self.assertIn('narrow_cache', source)
        self.assertIn('FIX 768', source)

    def test_full_cycle_store_lookup(self):
        """Full cycle: store → store → lookup returns cached."""
        cache = NarrowResponseCache()
        cache._cache = {}
        cache.CACHE_FILE = os.path.join(tempfile.gettempdir(), "test_full_cycle.json")

        q = "¿Dónde están ubicados?"
        resp = "Estamos en Guadalajara, Jalisco."

        # 1st call: GPT would respond, store
        cache.store("buscando_encargado", "responder_pregunta_producto", q, resp)
        self.assertIsNone(cache.lookup("buscando_encargado", "responder_pregunta_producto", q))

        # 2nd call: GPT would respond again, store (count→2)
        cache.store("buscando_encargado", "responder_pregunta_producto", q, resp)

        # 3rd call: cache hit (count >= 2)
        result = cache.lookup("buscando_encargado", "responder_pregunta_producto", q)
        self.assertEqual(result, resp)

        # Cleanup
        tmp = os.path.join(tempfile.gettempdir(), "test_full_cycle.json")
        if os.path.exists(tmp):
            os.remove(tmp)


if __name__ == '__main__':
    unittest.main()
