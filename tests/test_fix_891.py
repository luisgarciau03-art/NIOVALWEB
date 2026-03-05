"""
Tests para FIX 891: "a la orden" / "a tus ordenes" -> MANAGER_PRESENT.

FIX 891: BRUCE2605 - "Si, a la orden" classified as UNKNOWN instead of MANAGER_PRESENT.
"""
import unittest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fsm_engine import classify_intent, FSMIntent, FSMState, FSMContext


class TestFix891ALaOrden(unittest.TestCase):
    """FIX 891: BRUCE2605 - 'a la orden' -> MANAGER_PRESENT."""

    def test_a_la_orden(self):
        ctx = FSMContext()
        result = classify_intent("A la orden", ctx, FSMState.BUSCANDO_ENCARGADO)
        self.assertEqual(result, FSMIntent.MANAGER_PRESENT)

    def test_si_a_la_orden(self):
        """BRUCE2605: 'Si, a la orden.' -> MANAGER_PRESENT."""
        ctx = FSMContext()
        result = classify_intent("Si, a la orden.", ctx, FSMState.BUSCANDO_ENCARGADO)
        self.assertEqual(result, FSMIntent.MANAGER_PRESENT)

    def test_a_tus_ordenes(self):
        ctx = FSMContext()
        result = classify_intent("A tus ordenes", ctx, FSMState.BUSCANDO_ENCARGADO)
        self.assertEqual(result, FSMIntent.MANAGER_PRESENT)

    def test_a_sus_ordenes(self):
        ctx = FSMContext()
        result = classify_intent("A sus ordenes", ctx, FSMState.BUSCANDO_ENCARGADO)
        self.assertEqual(result, FSMIntent.MANAGER_PRESENT)

    def test_a_tu_orden(self):
        ctx = FSMContext()
        result = classify_intent("A tu orden", ctx, FSMState.BUSCANDO_ENCARGADO)
        self.assertEqual(result, FSMIntent.MANAGER_PRESENT)

    def test_a_la_orden_digame(self):
        ctx = FSMContext()
        result = classify_intent("A la orden, digame", ctx, FSMState.BUSCANDO_ENCARGADO)
        self.assertEqual(result, FSMIntent.MANAGER_PRESENT)

    def test_si_a_la_orden_en_que_puedo_ayudar(self):
        ctx = FSMContext()
        result = classify_intent("Si a la orden en que le puedo ayudar", ctx, FSMState.BUSCANDO_ENCARGADO)
        self.assertEqual(result, FSMIntent.MANAGER_PRESENT)

    # Verify no regressions
    def test_soy_yo_still_works(self):
        ctx = FSMContext()
        result = classify_intent("Soy yo", ctx, FSMState.BUSCANDO_ENCARGADO)
        self.assertEqual(result, FSMIntent.MANAGER_PRESENT)

    def test_servidor_still_works(self):
        ctx = FSMContext()
        result = classify_intent("Servidor", ctx, FSMState.BUSCANDO_ENCARGADO)
        self.assertEqual(result, FSMIntent.MANAGER_PRESENT)

    def test_yo_mero_still_works(self):
        ctx = FSMContext()
        result = classify_intent("Yo mero", ctx, FSMState.BUSCANDO_ENCARGADO)
        self.assertEqual(result, FSMIntent.MANAGER_PRESENT)


if __name__ == '__main__':
    unittest.main()
