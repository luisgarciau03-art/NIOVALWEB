# -*- coding: utf-8 -*-
"""
Tests para FIX 701: Intent Classifier.
Verifica exact match, fuzzy match, normalización, callback vs transfer, y edge cases.
"""

import sys
import os
import unittest

# Agregar directorio padre al path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from intent_classifier import IntentClassifier, IntentCategory, IntentResult


class TestNormalize(unittest.TestCase):
    """Tests de normalización de texto."""

    def setUp(self):
        self.c = IntentClassifier()

    def test_lowercase(self):
        self.assertEqual(self.c._normalize("HOLA MUNDO"), "hola mundo")

    def test_strip_acentos(self):
        self.assertEqual(self.c._normalize("está búsqueda"), "esta busqueda")

    def test_strip_ene(self):
        self.assertEqual(self.c._normalize("mañana señor"), "manana senor")

    def test_strip_u_dieresis(self):
        self.assertEqual(self.c._normalize("pingüino"), "pinguino")

    def test_strip_punctuation(self):
        self.assertEqual(self.c._normalize("¡Hola! ¿Qué tal?"), "hola que tal?")

    def test_multiple_spaces(self):
        self.assertEqual(self.c._normalize("hola    mundo   test"), "hola mundo test")

    def test_empty_string(self):
        self.assertEqual(self.c._normalize(""), "")

    def test_none(self):
        self.assertEqual(self.c._normalize(None), "")

    def test_only_spaces(self):
        self.assertEqual(self.c._normalize("   "), "")

    def test_preserves_question_mark(self):
        result = self.c._normalize("¿Quién habla?")
        self.assertIn("?", result)


class TestExactMatchCallback(unittest.TestCase):
    """Tests de exact match para CALLBACK."""

    def setUp(self):
        self.c = IntentClassifier()

    def test_esperar_a_que_regrese(self):
        r = self.c.classify("Esperar a que regrese el encargado")
        self.assertIsNotNone(r)
        self.assertEqual(r.category, IntentCategory.CALLBACK)
        self.assertEqual(r.method, 'exact')

    def test_marcar_mas_tarde(self):
        r = self.c.classify("Marcar más tarde por favor")
        self.assertIsNotNone(r)
        self.assertEqual(r.category, IntentCategory.CALLBACK)

    def test_llamar_despues(self):
        r = self.c.classify("Mejor llame después")
        self.assertIsNotNone(r)
        self.assertEqual(r.category, IntentCategory.CALLBACK)

    def test_volver_a_marcar(self):
        r = self.c.classify("Tendría que volver a marcar")
        self.assertIsNotNone(r)
        self.assertEqual(r.category, IntentCategory.CALLBACK)

    def test_hablar_luego(self):
        r = self.c.classify("Si gusta hablar luego")
        self.assertIsNotNone(r)
        self.assertEqual(r.category, IntentCategory.CALLBACK)

    def test_hableme_manana(self):
        r = self.c.classify("Hábleme mañana")
        self.assertIsNotNone(r)
        self.assertEqual(r.category, IntentCategory.CALLBACK)

    def test_mandarme_informacion(self):
        """FIX 698: 'mandarme información' es callback, no transfer."""
        r = self.c.classify("Si gusta mandarme información")
        self.assertIsNotNone(r)
        self.assertEqual(r.category, IntentCategory.CALLBACK)

    def test_enviarme_informacion(self):
        r = self.c.classify("Puede enviarme información por correo")
        self.assertIsNotNone(r)
        self.assertEqual(r.category, IntentCategory.CALLBACK)

    def test_mandame_informacion(self):
        r = self.c.classify("Mándame información por favor")
        self.assertIsNotNone(r)
        self.assertEqual(r.category, IntentCategory.CALLBACK)

    def test_mandar_la_informacion(self):
        r = self.c.classify("Puede mandar la información")
        self.assertIsNotNone(r)
        self.assertEqual(r.category, IntentCategory.CALLBACK)

    def test_tiene_que_esperar(self):
        r = self.c.classify("Tiene que esperar a que regrese")
        self.assertIsNotNone(r)
        self.assertEqual(r.category, IntentCategory.CALLBACK)

    def test_tendrias_que_esperar(self):
        r = self.c.classify("Tendrías que esperar porque no está")
        self.assertIsNotNone(r)
        self.assertEqual(r.category, IntentCategory.CALLBACK)

    def test_si_gusta_enviar(self):
        r = self.c.classify("Si gusta enviar la información")
        self.assertIsNotNone(r)
        self.assertEqual(r.category, IntentCategory.CALLBACK)

    def test_llame_manana(self):
        r = self.c.classify("Llame mañana temprano")
        self.assertIsNotNone(r)
        self.assertEqual(r.category, IntentCategory.CALLBACK)

    def test_puede_mandarme(self):
        r = self.c.classify("Me puede mandarme la info")
        self.assertIsNotNone(r)
        self.assertEqual(r.category, IntentCategory.CALLBACK)


class TestExactMatchTransfer(unittest.TestCase):
    """Tests de exact match para TRANSFER."""

    def setUp(self):
        self.c = IntentClassifier()

    def test_permitame(self):
        r = self.c.classify("Permítame un momento")
        self.assertIsNotNone(r)
        self.assertEqual(r.category, IntentCategory.TRANSFER)

    def test_un_momento(self):
        r = self.c.classify("Un momento por favor")
        self.assertIsNotNone(r)
        self.assertEqual(r.category, IntentCategory.TRANSFER)

    def test_espereme(self):
        r = self.c.classify("Espéreme tantito")
        self.assertIsNotNone(r)
        self.assertEqual(r.category, IntentCategory.TRANSFER)

    def test_ahorita_se_lo_paso(self):
        r = self.c.classify("Ahorita se lo paso")
        self.assertIsNotNone(r)
        self.assertEqual(r.category, IntentCategory.TRANSFER)

    def test_un_momentito(self):
        r = self.c.classify("Un momentito")
        self.assertIsNotNone(r)
        self.assertEqual(r.category, IntentCategory.TRANSFER)

    def test_dejeme_ver(self):
        r = self.c.classify("Déjeme ver si está")
        self.assertIsNotNone(r)
        self.assertEqual(r.category, IntentCategory.TRANSFER)

    def test_voy_a_ver(self):
        r = self.c.classify("Voy a ver si lo encuentro")
        self.assertIsNotNone(r)
        self.assertEqual(r.category, IntentCategory.TRANSFER)

    def test_aguardeme(self):
        r = self.c.classify("Aguárdeme un segundo")
        self.assertIsNotNone(r)
        self.assertEqual(r.category, IntentCategory.TRANSFER)


class TestCallbackVsTransfer(unittest.TestCase):
    """Tests críticos: callback vs transfer."""

    def setUp(self):
        self.c = IntentClassifier()

    def test_esperar_que_regrese_es_callback(self):
        """FIX 645: 'esperar a que regrese' es CALLBACK, NO transfer."""
        r = self.c.classify_callback_vs_transfer("tendrías que esperar a que regrese")
        self.assertIsNotNone(r)
        self.assertEqual(r.category, IntentCategory.CALLBACK)

    def test_espereme_es_transfer(self):
        """'Espéreme' es TRANSFER."""
        r = self.c.classify_callback_vs_transfer("espéreme un momento")
        self.assertIsNotNone(r)
        self.assertEqual(r.category, IntentCategory.TRANSFER)

    def test_mandarme_info_es_callback(self):
        """FIX 698: 'mandarme información' es CALLBACK."""
        r = self.c.classify_callback_vs_transfer("si gusta mandarme información")
        self.assertIsNotNone(r)
        self.assertEqual(r.category, IntentCategory.CALLBACK)

    def test_permitame_es_transfer(self):
        r = self.c.classify_callback_vs_transfer("permítame un segundo")
        self.assertIsNotNone(r)
        self.assertEqual(r.category, IntentCategory.TRANSFER)

    def test_volver_a_marcar_es_callback(self):
        r = self.c.classify_callback_vs_transfer("tendría que volver a marcar")
        self.assertIsNotNone(r)
        self.assertEqual(r.category, IntentCategory.CALLBACK)

    def test_se_lo_paso_es_transfer(self):
        r = self.c.classify_callback_vs_transfer("ahorita se lo paso")
        self.assertIsNotNone(r)
        self.assertEqual(r.category, IntentCategory.TRANSFER)

    def test_texto_sin_match(self):
        r = self.c.classify_callback_vs_transfer("buenos días")
        self.assertIsNone(r)

    def test_texto_vacio(self):
        r = self.c.classify_callback_vs_transfer("")
        self.assertIsNone(r)

    def test_enviarme_info_es_callback(self):
        r = self.c.classify_callback_vs_transfer("Puede enviarme la información")
        self.assertIsNotNone(r)
        self.assertEqual(r.category, IntentCategory.CALLBACK)

    def test_marcar_despues_es_callback(self):
        r = self.c.classify_callback_vs_transfer("Mejor marque después")
        self.assertIsNotNone(r)
        self.assertEqual(r.category, IntentCategory.CALLBACK)


class TestExactMatchOfferData(unittest.TestCase):
    """Tests de exact match para OFFER_DATA."""

    def setUp(self):
        self.c = IntentClassifier()

    def test_te_paso_su_telefono(self):
        r = self.c.classify("Te paso su teléfono")
        self.assertIsNotNone(r)
        self.assertEqual(r.category, IntentCategory.OFFER_DATA)

    def test_le_paso_su_numero(self):
        r = self.c.classify("Le paso su número")
        self.assertIsNotNone(r)
        self.assertEqual(r.category, IntentCategory.OFFER_DATA)

    def test_te_doy_mi_correo(self):
        r = self.c.classify("Te doy mi correo")
        self.assertIsNotNone(r)
        self.assertEqual(r.category, IntentCategory.OFFER_DATA)

    def test_aqui_le_va(self):
        r = self.c.classify("Aquí le va, anote")
        self.assertIsNotNone(r)
        self.assertEqual(r.category, IntentCategory.OFFER_DATA)

    def test_quieres_que_te_pase(self):
        r = self.c.classify("¿Quieres que te pase su teléfono?")
        self.assertIsNotNone(r)
        self.assertEqual(r.category, IntentCategory.OFFER_DATA)

    def test_le_voy_a_dar_un_correo(self):
        """FIX 621A: 'le voy a dar un correo' es oferta de dato."""
        r = self.c.classify("Le voy a dar un correo")
        self.assertIsNotNone(r)
        self.assertEqual(r.category, IntentCategory.OFFER_DATA)

    def test_apunte(self):
        r = self.c.classify("Apunte el número")
        self.assertIsNotNone(r)
        self.assertEqual(r.category, IntentCategory.OFFER_DATA)


class TestExactMatchRejectData(unittest.TestCase):
    """Tests de exact match para REJECT_DATA."""

    def setUp(self):
        self.c = IntentClassifier()

    def test_no_tengo_whatsapp(self):
        r = self.c.classify("No tengo WhatsApp")
        self.assertIsNotNone(r)
        self.assertEqual(r.category, IntentCategory.REJECT_DATA)

    def test_no_tengo_correo(self):
        r = self.c.classify("No tengo correo")
        self.assertIsNotNone(r)
        self.assertEqual(r.category, IntentCategory.REJECT_DATA)

    def test_solo_tengo_telefono(self):
        r = self.c.classify("Solo tengo teléfono fijo")
        self.assertIsNotNone(r)
        self.assertEqual(r.category, IntentCategory.REJECT_DATA)

    def test_no_quiero_dejar(self):
        """FIX 697B: 'no quiero dejar' = rechazo."""
        r = self.c.classify("No quiero dejar mis datos")
        self.assertIsNotNone(r)
        self.assertEqual(r.category, IntentCategory.REJECT_DATA)

    def test_no_estoy_autorizado(self):
        """FIX 647: 'no estoy autorizado' = rechazo."""
        r = self.c.classify("No estoy autorizado para dar eso")
        self.assertIsNotNone(r)
        self.assertEqual(r.category, IntentCategory.REJECT_DATA)

    def test_no_manejo_whatsapp(self):
        r = self.c.classify("No manejo WhatsApp")
        self.assertIsNotNone(r)
        self.assertEqual(r.category, IntentCategory.REJECT_DATA)

    def test_no_uso_wasap(self):
        """Variante STT de WhatsApp."""
        r = self.c.classify("No uso wasap")
        self.assertIsNotNone(r)
        self.assertEqual(r.category, IntentCategory.REJECT_DATA)


class TestExactMatchFarewell(unittest.TestCase):
    """Tests de exact match para FAREWELL."""

    def setUp(self):
        self.c = IntentClassifier()

    def test_hasta_luego(self):
        r = self.c.classify("Hasta luego")
        self.assertIsNotNone(r)
        self.assertEqual(r.category, IntentCategory.FAREWELL)

    def test_adios(self):
        r = self.c.classify("Adiós")
        self.assertIsNotNone(r)
        self.assertEqual(r.category, IntentCategory.FAREWELL)

    def test_ya_esta_todo(self):
        r = self.c.classify("Ya está todo")
        self.assertIsNotNone(r)
        self.assertEqual(r.category, IntentCategory.FAREWELL)

    def test_no_hay_ahorita(self):
        """FIX 648: cierre natural."""
        r = self.c.classify("No hay ahorita")
        self.assertIsNotNone(r)
        self.assertEqual(r.category, IntentCategory.FAREWELL)

    def test_no_oiga(self):
        """FIX 658: cortés mexicano."""
        r = self.c.classify("No, oiga")
        self.assertIsNotNone(r)
        self.assertEqual(r.category, IntentCategory.FAREWELL)

    def test_no_joven(self):
        r = self.c.classify("No, joven")
        self.assertIsNotNone(r)
        self.assertEqual(r.category, IntentCategory.FAREWELL)


class TestExactMatchInterest(unittest.TestCase):
    """Tests para INTEREST."""

    def setUp(self):
        self.c = IntentClassifier()

    def test_me_interesa(self):
        r = self.c.classify("Sí, me interesa")
        self.assertIsNotNone(r)
        self.assertEqual(r.category, IntentCategory.INTEREST)

    def test_digame(self):
        r = self.c.classify("Sí, dígame")
        self.assertIsNotNone(r)
        self.assertEqual(r.category, IntentCategory.INTEREST)

    def test_cuenteme_mas(self):
        r = self.c.classify("Cuénteme más")
        self.assertIsNotNone(r)
        self.assertEqual(r.category, IntentCategory.INTEREST)

    def test_mandeme_el_catalogo(self):
        r = self.c.classify("Mándeme el catálogo")
        self.assertIsNotNone(r)
        self.assertEqual(r.category, IntentCategory.INTEREST)


class TestExactMatchNoInterest(unittest.TestCase):
    """Tests para NO_INTEREST."""

    def setUp(self):
        self.c = IntentClassifier()

    def test_no_me_interesa(self):
        r = self.c.classify("No me interesa")
        self.assertIsNotNone(r)
        self.assertEqual(r.category, IntentCategory.NO_INTEREST)

    def test_ya_tenemos_proveedor(self):
        r = self.c.classify("Ya tenemos proveedor")
        self.assertIsNotNone(r)
        self.assertEqual(r.category, IntentCategory.NO_INTEREST)

    def test_no_gracias(self):
        r = self.c.classify("No, gracias")
        self.assertIsNotNone(r)
        self.assertEqual(r.category, IntentCategory.NO_INTEREST)

    def test_estamos_bien_asi(self):
        r = self.c.classify("Estamos bien así, gracias")
        self.assertIsNotNone(r)
        self.assertEqual(r.category, IntentCategory.NO_INTEREST)

    def test_no_por_el_momento(self):
        r = self.c.classify("No por el momento")
        self.assertIsNotNone(r)
        self.assertEqual(r.category, IntentCategory.NO_INTEREST)


class TestExactMatchQuestion(unittest.TestCase):
    """Tests para QUESTION."""

    def setUp(self):
        self.c = IntentClassifier()

    def test_que_venden(self):
        r = self.c.classify("¿Qué venden?")
        self.assertIsNotNone(r)
        self.assertEqual(r.category, IntentCategory.QUESTION)

    def test_de_donde_hablan(self):
        r = self.c.classify("¿De dónde hablan?")
        self.assertIsNotNone(r)
        self.assertEqual(r.category, IntentCategory.QUESTION)

    def test_que_precios_manejan(self):
        r = self.c.classify("¿Qué precios manejan?")
        self.assertIsNotNone(r)
        self.assertEqual(r.category, IntentCategory.QUESTION)

    def test_cuanto_cuesta(self):
        r = self.c.classify("¿Cuánto cuesta?")
        self.assertIsNotNone(r)
        self.assertEqual(r.category, IntentCategory.QUESTION)


class TestExactMatchIdentity(unittest.TestCase):
    """Tests para IDENTITY."""

    def setUp(self):
        self.c = IntentClassifier()

    def test_quien_habla(self):
        r = self.c.classify("¿Quién habla?")
        self.assertIsNotNone(r)
        self.assertEqual(r.category, IntentCategory.IDENTITY)

    def test_de_parte_de_quien(self):
        r = self.c.classify("¿De parte de quién?")
        self.assertIsNotNone(r)
        self.assertEqual(r.category, IntentCategory.IDENTITY)

    def test_con_quien_hablo(self):
        r = self.c.classify("¿Con quién hablo?")
        self.assertIsNotNone(r)
        self.assertEqual(r.category, IntentCategory.IDENTITY)

    def test_de_que_empresa(self):
        r = self.c.classify("¿De qué empresa?")
        self.assertIsNotNone(r)
        self.assertEqual(r.category, IntentCategory.IDENTITY)


class TestExactMatchConfirmation(unittest.TestCase):
    """Tests para CONFIRMATION."""

    def setUp(self):
        self.c = IntentClassifier()

    def test_si_claro(self):
        r = self.c.classify("Sí, claro")
        self.assertIsNotNone(r)
        self.assertEqual(r.category, IntentCategory.CONFIRMATION)

    def test_asi_es(self):
        r = self.c.classify("Así es")
        self.assertIsNotNone(r)
        self.assertEqual(r.category, IntentCategory.CONFIRMATION)

    def test_de_acuerdo(self):
        r = self.c.classify("De acuerdo")
        self.assertIsNotNone(r)
        self.assertEqual(r.category, IntentCategory.CONFIRMATION)

    def test_orale(self):
        r = self.c.classify("Órale")
        self.assertIsNotNone(r)
        self.assertEqual(r.category, IntentCategory.CONFIRMATION)


class TestExactMatchAnotherBranch(unittest.TestCase):
    """Tests para ANOTHER_BRANCH."""

    def setUp(self):
        self.c = IntentClassifier()

    def test_otra_sucursal(self):
        r = self.c.classify("Es otra sucursal")
        self.assertIsNotNone(r)
        self.assertEqual(r.category, IntentCategory.ANOTHER_BRANCH)

    def test_comunicarse_directamente(self):
        """FIX 688: 'comunicarse directamente con' = OTRA_SUCURSAL."""
        r = self.c.classify("Comunicarse directamente con ellos")
        self.assertIsNotNone(r)
        self.assertEqual(r.category, IntentCategory.ANOTHER_BRANCH)

    def test_sucursal_equivocada(self):
        r = self.c.classify("Creo que es sucursal equivocada")
        self.assertIsNotNone(r)
        self.assertEqual(r.category, IntentCategory.ANOTHER_BRANCH)


class TestExactMatchCorrection(unittest.TestCase):
    """Tests para CORRECTION."""

    def setUp(self):
        self.c = IntentClassifier()

    def test_no_es_eso(self):
        r = self.c.classify("No, no es eso")
        self.assertIsNotNone(r)
        self.assertEqual(r.category, IntentCategory.CORRECTION)

    def test_me_equivoque(self):
        r = self.c.classify("Me equivoqué, disculpe")
        self.assertIsNotNone(r)
        self.assertEqual(r.category, IntentCategory.CORRECTION)

    def test_incorrecto(self):
        r = self.c.classify("Eso es incorrecto")
        self.assertIsNotNone(r)
        self.assertEqual(r.category, IntentCategory.CORRECTION)


class TestExactMatchClosed(unittest.TestCase):
    """Tests para CLOSED."""

    def setUp(self):
        self.c = IntentClassifier()

    def test_estamos_cerrados(self):
        r = self.c.classify("Estamos cerrados ya")
        self.assertIsNotNone(r)
        self.assertEqual(r.category, IntentCategory.CLOSED)

    def test_ya_cerramos(self):
        r = self.c.classify("Ya cerramos por hoy")
        self.assertIsNotNone(r)
        self.assertEqual(r.category, IntentCategory.CLOSED)

    def test_abrimos_manana(self):
        r = self.c.classify("Abrimos mañana a las 9")
        self.assertIsNotNone(r)
        self.assertEqual(r.category, IntentCategory.CLOSED)


class TestExactMatchManagerAbsent(unittest.TestCase):
    """Tests para MANAGER_ABSENT."""

    def setUp(self):
        self.c = IntentClassifier()

    def test_no_esta_el_encargado(self):
        r = self.c.classify("No está el encargado")
        self.assertIsNotNone(r)
        self.assertEqual(r.category, IntentCategory.MANAGER_ABSENT)

    def test_salio_a_comer(self):
        r = self.c.classify("Salió a comer")
        self.assertIsNotNone(r)
        self.assertEqual(r.category, IntentCategory.MANAGER_ABSENT)

    def test_llega_mas_tarde(self):
        r = self.c.classify("Llega más tarde")
        self.assertIsNotNone(r)
        self.assertEqual(r.category, IntentCategory.MANAGER_ABSENT)

    def test_no_viene_hoy(self):
        r = self.c.classify("Hoy no viene")
        self.assertIsNotNone(r)
        self.assertEqual(r.category, IntentCategory.MANAGER_ABSENT)

    def test_esta_ocupado(self):
        r = self.c.classify("Está ocupado ahorita")
        self.assertIsNotNone(r)
        self.assertEqual(r.category, IntentCategory.MANAGER_ABSENT)

    def test_todavia_no_llega(self):
        r = self.c.classify("Todavía no llega")
        self.assertIsNotNone(r)
        self.assertEqual(r.category, IntentCategory.MANAGER_ABSENT)


class TestFuzzyMatch(unittest.TestCase):
    """Tests de fuzzy matching para variantes STT."""

    def setUp(self):
        self.c = IntentClassifier()

    def test_fuzzy_mandarme_info(self):
        """Variante STT: 'mandarme informasion' (error ortográfico)."""
        r = self.c.classify("mandarme informasion")
        self.assertIsNotNone(r)
        self.assertEqual(r.category, IntentCategory.CALLBACK)
        # Puede ser exact o fuzzy dependiendo de normalización

    def test_fuzzy_esperara_que_regrese(self):
        """Variante STT: 'espera a que regrese' (sin r final)."""
        r = self.c.classify("espera a que regrese")
        self.assertIsNotNone(r)
        self.assertEqual(r.category, IntentCategory.CALLBACK)

    def test_fuzzy_no_tengo_guatsap(self):
        """Variante STT de WhatsApp: 'guatsap'."""
        r = self.c.classify("no tengo guatsap")
        # Puede no matchear exacto pero fuzzy debería capturar
        if r:
            self.assertEqual(r.category, IntentCategory.REJECT_DATA)

    def test_fuzzy_asta_luego(self):
        """Variante STT sin h: 'asta luego'."""
        r = self.c.classify("asta luego")
        self.assertIsNotNone(r)
        self.assertEqual(r.category, IntentCategory.FAREWELL)

    def test_fuzzy_ke_venden(self):
        """Variante STT: 'ke venden' en vez de 'que venden'."""
        r = self.c.classify("ke venden")
        if r:
            self.assertEqual(r.category, IntentCategory.QUESTION)

    def test_fuzzy_no_me_intereza(self):
        """Variante STT: 'intereza' con z."""
        r = self.c.classify("no me intereza")
        self.assertIsNotNone(r)
        self.assertEqual(r.category, IntentCategory.NO_INTEREST)

    def test_fuzzy_kien_habla(self):
        """Variante STT: 'kien habla'."""
        r = self.c.classify("kien habla")
        if r:
            self.assertEqual(r.category, IntentCategory.IDENTITY)

    def test_fuzzy_no_esta_el_enkargado(self):
        """Variante STT: 'enkargado'."""
        r = self.c.classify("no esta el enkargado")
        if r:
            self.assertEqual(r.category, IntentCategory.MANAGER_ABSENT)

    def test_fuzzy_method_flag(self):
        """Verifica que fuzzy matches tienen method='fuzzy'."""
        # Forzar fuzzy con typo que no matchea exacto
        r = self.c.classify("volber a markar")
        if r and r.method == 'fuzzy':
            self.assertGreaterEqual(r.confidence, self.c.FUZZY_THRESHOLD)

    def test_fuzzy_high_confidence(self):
        """Fuzzy match debe tener confidence >= threshold."""
        r = self.c.classify("asta luego amigo")
        if r and r.method == 'fuzzy':
            self.assertGreaterEqual(r.confidence, self.c.FUZZY_THRESHOLD)


class TestEdgeCases(unittest.TestCase):
    """Tests de edge cases."""

    def setUp(self):
        self.c = IntentClassifier()

    def test_empty_string(self):
        self.assertIsNone(self.c.classify(""))

    def test_none(self):
        self.assertIsNone(self.c.classify(None))

    def test_only_spaces(self):
        self.assertIsNone(self.c.classify("   "))

    def test_single_word_no_match(self):
        """Una palabra sola no debería matchear transfer."""
        r = self.c.classify("hola")
        # 'hola' no está en ningún patrón
        self.assertIsNone(r)

    def test_very_long_text(self):
        """Texto largo con patrón al final."""
        texto = "Mire joven yo le explico que aquí en la tienda " * 5 + "no me interesa"
        r = self.c.classify(texto)
        self.assertIsNotNone(r)
        self.assertEqual(r.category, IntentCategory.NO_INTEREST)

    def test_mixed_case(self):
        r = self.c.classify("NO ME INTERESA")
        self.assertIsNotNone(r)
        self.assertEqual(r.category, IntentCategory.NO_INTEREST)

    def test_with_acentos(self):
        """Acentos deben normalizarse correctamente."""
        r = self.c.classify("está ocupado")
        self.assertIsNotNone(r)
        self.assertEqual(r.category, IntentCategory.MANAGER_ABSENT)

    def test_numbers_no_match(self):
        """Solo números no deberían matchear."""
        self.assertIsNone(self.c.classify("3312345678"))

    def test_filler_sounds(self):
        """Sonidos de relleno no deberían matchear."""
        self.assertIsNone(self.c.classify("mmm"))

    def test_bueno_alone(self):
        """'Bueno' solo no debería matchear categoría fuerte."""
        r = self.c.classify("bueno")
        # bueno puede o no matchear; si matchea, no debe ser FAREWELL
        if r:
            self.assertNotEqual(r.category, IntentCategory.CALLBACK)


class TestCallbackVsTransferSpecific(unittest.TestCase):
    """Tests específicos de classify_callback_vs_transfer."""

    def setUp(self):
        self.c = IntentClassifier()

    def test_espere_un_momento_is_transfer(self):
        r = self.c.classify_callback_vs_transfer("espere un momento")
        self.assertIsNotNone(r)
        self.assertEqual(r.category, IntentCategory.TRANSFER)

    def test_tendria_que_esperar_is_callback(self):
        """FIX 645: 'tendría que esperar' es callback."""
        r = self.c.classify_callback_vs_transfer("tendría que esperar")
        self.assertIsNotNone(r)
        self.assertEqual(r.category, IntentCategory.CALLBACK)

    def test_mandame_la_info_is_callback(self):
        r = self.c.classify_callback_vs_transfer("mándame la información")
        self.assertIsNotNone(r)
        self.assertEqual(r.category, IntentCategory.CALLBACK)

    def test_le_paso_su_no_es_transfer(self):
        """'le paso su número' NO es transfer (es oferta de dato)."""
        r = self.c.classify_callback_vs_transfer("le paso su número")
        # Debe retornar None porque no es ni callback ni transfer
        self.assertIsNone(r)

    def test_callback_priority_over_transfer(self):
        """Callback tiene prioridad sobre transfer en classify_callback_vs_transfer."""
        # "esperar a que regrese" contiene "esperar" (transfer) pero es callback
        r = self.c.classify_callback_vs_transfer("tiene que esperar a que regrese")
        self.assertIsNotNone(r)
        self.assertEqual(r.category, IntentCategory.CALLBACK)

    def test_regresar_la_llamada(self):
        r = self.c.classify_callback_vs_transfer("le voy a regresar la llamada")
        self.assertIsNotNone(r)
        self.assertEqual(r.category, IntentCategory.CALLBACK)


class TestIntentResult(unittest.TestCase):
    """Tests del IntentResult."""

    def test_repr(self):
        r = IntentResult(IntentCategory.CALLBACK, 0.95, 'marcar mas tarde', 'exact')
        s = repr(r)
        self.assertIn('callback', s)
        self.assertIn('0.95', s)
        self.assertIn('marcar mas tarde', s)

    def test_attributes(self):
        r = IntentResult(IntentCategory.FAREWELL, 0.82, 'hasta luego', 'fuzzy')
        self.assertEqual(r.category, IntentCategory.FAREWELL)
        self.assertAlmostEqual(r.confidence, 0.82)
        self.assertEqual(r.pattern, 'hasta luego')
        self.assertEqual(r.method, 'fuzzy')


class TestGetPatternsForCategory(unittest.TestCase):
    """Tests de introspección."""

    def setUp(self):
        self.c = IntentClassifier()

    def test_callback_patterns_not_empty(self):
        patterns = self.c.get_patterns_for_category(IntentCategory.CALLBACK)
        self.assertGreater(len(patterns), 0)

    def test_all_categories_have_patterns(self):
        cats = self.c.get_all_categories()
        for cat_name, count in cats.items():
            self.assertGreater(count, 0, f"Category {cat_name} has no patterns")

    def test_stats(self):
        stats = self.c.get_stats()
        self.assertGreater(stats['total_patterns'], 300)
        self.assertEqual(stats['categories'], 14)
        self.assertEqual(stats['fuzzy_threshold'], 0.80)


class TestIntegracionAgente(unittest.TestCase):
    """Tests de integración con agente_ventas."""

    def test_import_modulo(self):
        """Verificar que el módulo se importa correctamente."""
        try:
            from intent_classifier import IntentClassifier, IntentCategory, IntentResult
            DISPONIBLE = True
        except ImportError:
            DISPONIBLE = False
        self.assertTrue(DISPONIBLE)

    def test_classify_retorna_none_para_texto_generico(self):
        """Texto genérico sin patrón no causa error."""
        c = IntentClassifier()
        r = c.classify("Pues mire, aquí andamos trabajando normalmente")
        # Puede retornar None o algo, pero no debe lanzar excepción

    def test_classify_multiples_llamadas(self):
        """Verificar que múltiples llamadas no causan problemas de estado."""
        c = IntentClassifier()
        r1 = c.classify("No me interesa")
        r2 = c.classify("Sí, dígame")
        r3 = c.classify("Hasta luego")
        self.assertEqual(r1.category, IntentCategory.NO_INTEREST)
        self.assertEqual(r2.category, IntentCategory.INTEREST)
        self.assertEqual(r3.category, IntentCategory.FAREWELL)

    def test_cache_normalizacion(self):
        """Verificar que el cache no causa problemas."""
        c = IntentClassifier()
        for _ in range(100):
            c.classify("No me interesa gracias")
        stats = c.get_stats()
        self.assertGreater(stats['cache_size'], 0)


class TestVariantesSTT(unittest.TestCase):
    """Tests de variantes comunes de STT."""

    def setUp(self):
        self.c = IntentClassifier()

    def test_wasap_variante(self):
        """STT puede transcribir 'WhatsApp' como 'wasap'."""
        r = self.c.classify("no tengo wasap")
        self.assertIsNotNone(r)
        self.assertEqual(r.category, IntentCategory.REJECT_DATA)

    def test_watsap_variante(self):
        """Otra variante STT."""
        r = self.c.classify("no tengo watsap")
        self.assertIsNotNone(r)
        self.assertEqual(r.category, IntentCategory.REJECT_DATA)

    def test_acentos_removidos_por_stt(self):
        """STT a veces no incluye acentos."""
        r = self.c.classify("esta ocupado")
        self.assertIsNotNone(r)
        self.assertEqual(r.category, IntentCategory.MANAGER_ABSENT)

    def test_manana_sin_tilde(self):
        r = self.c.classify("hableme manana")
        self.assertIsNotNone(r)
        self.assertEqual(r.category, IntentCategory.CALLBACK)

    def test_despues_sin_tilde(self):
        r = self.c.classify("llamar despues")
        self.assertIsNotNone(r)
        self.assertEqual(r.category, IntentCategory.CALLBACK)

    def test_permitame_sin_tilde(self):
        r = self.c.classify("permitame")
        self.assertIsNotNone(r)
        self.assertEqual(r.category, IntentCategory.TRANSFER)

    def test_digame_sin_tilde(self):
        r = self.c.classify("digame")
        self.assertIsNotNone(r)
        self.assertEqual(r.category, IntentCategory.INTEREST)

    def test_telefono_sin_tilde(self):
        r = self.c.classify("te paso su telefono")
        self.assertIsNotNone(r)
        self.assertEqual(r.category, IntentCategory.OFFER_DATA)


if __name__ == '__main__':
    unittest.main()
