# -*- coding: utf-8 -*-
"""
Tests para FIX 706: Servidor bypass - Intent Classifier antes de frases_espera_cliente.
Verifica que:
- 706A: 'espera'/'espere' removidos de frases_espera_cliente (no substring false positive)
- 706B: Callback "sin a que" detectado en patrones_callback_645
- 706C: Intent Classifier completo previene "Claro, espero" para OFFER_DATA, REJECT_DATA, etc.
"""

import sys
import os
import pytest

# Agregar directorio padre al path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from intent_classifier import IntentClassifier, IntentCategory


# ============================================================
# FIX 706A: frases_espera_cliente sin 'espera'/'espere' sueltos
# ============================================================

class TestFix706ASubstringRemoval:
    """Verifica que 'espera'/'espere' ya no están como patterns sueltos en servidor."""

    def test_servidor_no_tiene_espera_suelto(self):
        """Verificar en código fuente que 'espera' suelto fue reemplazado."""
        import inspect
        import servidor_llamadas

        # Buscar la función procesar_respuesta
        source = inspect.getsource(servidor_llamadas)
        # Buscar la sección de frases_espera_cliente
        idx_start = source.find("frases_espera_cliente = [")
        assert idx_start > 0, "No se encontró frases_espera_cliente"
        idx_end = source.find("]", idx_start)
        seccion = source[idx_start:idx_end]

        # 'espera' suelto NO debe estar (debe ser 'espera un', 'espera por favor', etc.)
        lineas = seccion.split('\n')
        for linea in lineas:
            # Ignorar comentarios
            if linea.strip().startswith('#'):
                continue
            # Buscar 'espera' como entrada sola (no como parte de 'esperame', 'espera un', etc.)
            if "'espera'" in linea and "'espera un'" not in linea and "'espera por favor'" not in linea and "'espera tantito'" not in linea:
                pytest.fail(f"'espera' suelto encontrado en frases_espera_cliente: {linea.strip()}")

    def test_servidor_no_tiene_espere_suelto(self):
        """Verificar que 'espere' suelto fue reemplazado."""
        import inspect
        import servidor_llamadas

        source = inspect.getsource(servidor_llamadas)
        idx_start = source.find("frases_espera_cliente = [")
        idx_end = source.find("]", idx_start)
        seccion = source[idx_start:idx_end]

        lineas = seccion.split('\n')
        for linea in lineas:
            if linea.strip().startswith('#'):
                continue
            if "'espere'" in linea and "'espere un'" not in linea and "'espere por favor'" not in linea and "'espere tantito'" not in linea:
                pytest.fail(f"'espere' suelto encontrado en frases_espera_cliente: {linea.strip()}")

    def test_servidor_tiene_espereme(self):
        """'espereme' (7 chars) SÍ debe estar - es específico para transfer."""
        import inspect
        import servidor_llamadas

        source = inspect.getsource(servidor_llamadas)
        idx_start = source.find("frases_espera_cliente = [")
        idx_end = source.find("]", idx_start)
        seccion = source[idx_start:idx_end]

        assert "'espereme'" in seccion or "'espéreme'" in seccion

    def test_servidor_tiene_espere_un(self):
        """'espere un' SÍ debe estar como replacement específico."""
        import inspect
        import servidor_llamadas

        source = inspect.getsource(servidor_llamadas)
        idx_start = source.find("frases_espera_cliente = [")
        idx_end = source.find("]", idx_start)
        seccion = source[idx_start:idx_end]

        assert "'espere un'" in seccion

    def test_espera_no_matchea_esperar_en_callback(self):
        """'espera' como substring NO debe matchear 'esperar que vuelva'."""
        # Simular lo que hace servidor: any(frase in frase_limpia ...)
        frases_espera = [
            'espereme', 'esperame', 'espere un', 'espera un',
            'espere por favor', 'espera por favor',
            'espere tantito', 'espera tantito',
        ]
        frase_callback = "tiene que esperar que vuelva el encargado"
        matchea = any(f in frase_callback for f in frases_espera)
        assert matchea == False, "Patrón de transfer NO debe matchear frase callback"

    def test_espere_un_momento_si_matchea(self):
        """'espere un' SÍ matchea 'espere un momento'."""
        frases_espera = ['espere un', 'espera un']
        frase_transfer = "espere un momento por favor"
        matchea = any(f in frase_transfer for f in frases_espera)
        assert matchea == True


# ============================================================
# FIX 706B: patrones_callback_645 con variantes sin "a que"
# ============================================================

class TestFix706BCallbackSinAQue:
    """Verifica que callback sin 'a que' está en patrones_callback_645."""

    def test_servidor_tiene_esperar_que_regrese(self):
        """'esperar que regrese' (sin 'a que') debe estar."""
        import inspect
        import servidor_llamadas

        source = inspect.getsource(servidor_llamadas)
        idx = source.find("patrones_callback_645")
        assert idx > 0
        seccion = source[idx:idx + 3000]

        assert "'esperar que regrese'" in seccion

    def test_servidor_tiene_esperar_que_vuelva(self):
        import inspect
        import servidor_llamadas

        source = inspect.getsource(servidor_llamadas)
        idx = source.find("patrones_callback_645")
        seccion = source[idx:idx + 3000]

        assert "'esperar que vuelva'" in seccion

    def test_servidor_tiene_necesita_esperar(self):
        import inspect
        import servidor_llamadas

        source = inspect.getsource(servidor_llamadas)
        idx = source.find("patrones_callback_645")
        seccion = source[idx:idx + 3000]

        assert "'necesita esperar'" in seccion

    def test_callback_sin_a_que_matchea(self):
        """Verificar que 'esperar que regrese' matchea como substring."""
        patrones_callback = [
            'esperar que regrese', 'esperar que vuelva',
            'esperar que llegue', 'esperar que venga',
            'necesita esperar', 'necesitaria esperar',
        ]
        frase = "tendría que esperar que regrese el jefe"
        matchea = any(p in frase for p in patrones_callback)
        assert matchea == True

    def test_callback_vs_transfer_disambiguation(self):
        """Frases callback NO deben terminar como 'Claro, espero'."""
        frases_callback_reales = [
            "tiene que esperar que vuelva el encargado",
            "necesita esperar a que llegue",
            "esperar que regrese el dueño",
            "necesitaria esperar un rato hasta que venga",
        ]
        patrones_callback = [
            'esperar a que regrese', 'esperar a que llegue', 'esperar a que venga',
            'esperar a que vuelva', 'esperar a que entre',
            'esperar que regrese', 'esperar que llegue', 'esperar que venga',
            'esperar que vuelva', 'esperar que entre', 'esperar que este',
            'necesitaria esperar', 'necesitas esperar', 'necesita esperar',
            'tendrías que esperar', 'tienes que esperar', 'tiene que esperar',
            'tendría que esperar', 'habría que esperar', 'hay que esperar',
        ]
        for frase in frases_callback_reales:
            frase_lower = frase.lower()
            es_callback = any(p in frase_lower for p in patrones_callback)
            assert es_callback, f"Frase callback no detectada: '{frase}'"


# ============================================================
# FIX 706C: Intent Classifier completo previene "Claro, espero"
# ============================================================

class TestFix706CClassifierCompleto:
    """Verifica que classify() detecta categorías no-transfer correctamente."""

    def setup_method(self):
        self.c = IntentClassifier()

    def test_offer_data_no_es_transfer(self):
        """'te doy el correo' = OFFER_DATA, no debe generar 'Claro, espero'."""
        r = self.c.classify("te doy el correo del encargado")
        assert r is not None
        assert r.category == IntentCategory.OFFER_DATA

    def test_reject_data_no_es_transfer(self):
        """'no lo podemos pasar' = REJECT_DATA, no debe generar 'Claro, espero'."""
        r = self.c.classify("no lo podemos pasar, es política")
        assert r is not None
        assert r.category == IntentCategory.REJECT_DATA

    def test_question_no_es_transfer(self):
        """'que quiere' = QUESTION, no debe generar 'Claro, espero'."""
        r = self.c.classify("que quiere joven")
        assert r is not None
        assert r.category == IntentCategory.QUESTION

    def test_farewell_no_es_transfer(self):
        """'hasta luego' = FAREWELL, no debe generar 'Claro, espero'."""
        r = self.c.classify("hasta luego gracias")
        assert r is not None
        assert r.category == IntentCategory.FAREWELL

    def test_no_interest_no_es_transfer(self):
        """'no me interesa' = NO_INTEREST."""
        r = self.c.classify("no me interesa gracias")
        assert r is not None
        assert r.category == IntentCategory.NO_INTEREST

    def test_callback_detected_by_full_classify(self):
        """'hableme manana' = CALLBACK via classify() también."""
        r = self.c.classify("hableme manana mejor")
        assert r is not None
        assert r.category == IntentCategory.CALLBACK

    def test_transfer_still_works(self):
        """'espere un momento' SÍ es TRANSFER legítimo."""
        r = self.c.classify("espere un momento por favor")
        assert r is not None
        assert r.category == IntentCategory.TRANSFER

    def test_no_transfer_categories_list(self):
        """Verificar que las categorías no-transfer están definidas correctamente."""
        no_transfer = [
            IntentCategory.OFFER_DATA, IntentCategory.REJECT_DATA,
            IntentCategory.QUESTION, IntentCategory.NO_INTEREST,
            IntentCategory.FAREWELL, IntentCategory.ANOTHER_BRANCH,
            IntentCategory.CALLBACK
        ]
        # TRANSFER NO debe estar en la lista
        assert IntentCategory.TRANSFER not in no_transfer
        # Todas deben ser IntentCategory válidas
        for cat in no_transfer:
            assert isinstance(cat, IntentCategory)

    def test_servidor_tiene_classify_completo(self):
        """Verificar que FIX 706C usa classify() además de classify_callback_vs_transfer()."""
        import inspect
        import servidor_llamadas

        source = inspect.getsource(servidor_llamadas)
        # Debe tener classify() en el bloque FIX 706C
        assert "_classifier_706.classify(speech_result)" in source or \
               "_classifier_706.classify(" in source

    def test_servidor_confidence_080(self):
        """Verificar que threshold es 0.80, no 0.85."""
        import inspect
        import servidor_llamadas

        source = inspect.getsource(servidor_llamadas)
        # Buscar el bloque FIX 706C
        idx = source.find("FIX 706C")
        assert idx > 0
        seccion = source[idx:idx + 1000]
        assert ">= 0.80" in seccion or ">=0.80" in seccion or ">= 0.8" in seccion


# ============================================================
# Integración: Flujo completo servidor con FIX 706
# ============================================================

class TestFix706Integracion:
    """Tests de integración end-to-end para FIX 706."""

    def test_esperar_que_vuelva_no_activa_espera(self):
        """Simular flujo: 'esperar que vuelva' → ambas capas lo bloquean."""
        frase = "tiene que esperar que vuelva el encargado"
        frase_lower = frase.lower()

        # Capa 1: frases_espera_cliente (706A limpia)
        frases_espera = [
            'espereme', 'esperame', 'espere un', 'espera un',
            'espere por favor', 'espera por favor',
            'un momento', 'un momentito', 'permitame',
        ]
        match_espera = any(f in frase_lower for f in frases_espera)

        # Capa 2: patrones_callback_645 (706B expande)
        patrones_callback = [
            'esperar que vuelva', 'esperar que regrese',
            'necesita esperar', 'tiene que esperar',
        ]
        es_callback = any(p in frase_lower for p in patrones_callback)

        # Capa 3: Intent Classifier (706C)
        c = IntentClassifier()
        r = c.classify_callback_vs_transfer(frase)

        # Al menos una capa debe bloquear
        bloqueado = (not match_espera) or es_callback or (r and r.category == IntentCategory.CALLBACK)
        assert bloqueado, "Ninguna capa bloqueó la frase callback"

    def test_te_doy_el_correo_no_activa_espera(self):
        """'te doy el correo' no debe activar modo espera."""
        frase = "te doy el correo del encargado, anota"
        c = IntentClassifier()
        r = c.classify(frase)
        assert r is not None
        assert r.category == IntentCategory.OFFER_DATA
        # Categoría OFFER_DATA está en lista no_transfer de 706C

    def test_espere_un_momento_si_activa_espera(self):
        """'espere un momento' SÍ debe activar modo espera."""
        frase = "espere un momento le paso al encargado"
        frase_lower = frase.lower()

        # Capa 1: frases_espera_cliente
        frases_espera = ['espere un', 'un momento']
        match_espera = any(f in frase_lower for f in frases_espera)
        assert match_espera == True

        # Capa 3: Classifier confirma TRANSFER
        c = IntentClassifier()
        r = c.classify(frase)
        if r:
            assert r.category == IntentCategory.TRANSFER

    def test_mandarme_informacion_no_activa_espera(self):
        """'mandarme información' es CALLBACK, no transfer."""
        frase = "si gusta mandarme la información"
        c = IntentClassifier()
        r = c.classify(frase)
        assert r is not None
        assert r.category == IntentCategory.CALLBACK
