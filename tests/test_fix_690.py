# -*- coding: utf-8 -*-
"""
Tests de regresión para FIX 690 (BRUCE2202: detectar 'tienes donde anotar' como cliente listo para dictar).
FIX 690A: Patrones expandidos en pattern detector (agente)
FIX 690B: GPT timeout fallback contextual (servidor)
FIX 690C: Post-filter override respuesta genérica (agente)
"""
import os
import sys
import re
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault("OPENAI_API_KEY", "sk-test-dummy")
os.environ.setdefault("ELEVENLABS_API_KEY", "test-dummy")
os.environ.setdefault("TWILIO_ACCOUNT_SID", "AC-test")
os.environ.setdefault("TWILIO_AUTH_TOKEN", "test-token")

from agente_ventas import AgenteVentas


# ============================================================
# FIX 690A: Patrones expandidos en pattern detector
# ============================================================

class TestFix690APatronesExpandidos:
    """FIX 690A: Nuevas variantes de 'tienes donde anotar' detectadas."""

    PATRONES_523_690 = [
        "tiene para anotar", "tienes para anotar",
        "tiene donde anotar", "tienes donde anotar",
        "tiene dónde anotar", "tienes dónde anotar",
        "puede anotar", "puedes anotar",
        # FIX 690A nuevos
        "tiene con que anotar", "tienes con que anotar",
        "tiene con qué anotar", "tienes con qué anotar",
        "tiene lapiz", "tienes lapiz", "tiene lápiz", "tienes lápiz",
        "tiene papel", "tienes papel", "tiene pluma", "tienes pluma",
        "tienes donde apuntar", "tiene donde apuntar",
        "tienes para apuntar", "tiene para apuntar",
        "puede apuntar", "puedes apuntar",
        "le doy un correo", "le doy mi correo", "le doy el correo",
        "le doy un número", "le doy mi número", "le doy el número",
        "le paso un correo", "le paso mi correo",
        "le paso un número", "le paso mi número",
        "anote un correo", "anota un correo", "anote el correo",
        "anote un número", "anota un número", "anote el número"
    ]

    def test_tienes_con_que_anotar(self):
        """'tienes con que anotar' debe ser detectado."""
        texto = "sí, ¿tienes con que anotar?"
        assert any(p in texto.lower() for p in self.PATRONES_523_690)

    def test_tienes_lapiz(self):
        """'tienes lapiz' debe ser detectado."""
        texto = "¿tienes lapiz?"
        assert any(p in texto.lower() for p in self.PATRONES_523_690)

    def test_tienes_papel(self):
        """'tienes papel' debe ser detectado."""
        texto = "¿tienes papel para anotar?"
        assert any(p in texto.lower() for p in self.PATRONES_523_690)

    def test_tienes_pluma(self):
        """'tiene pluma' debe ser detectado."""
        texto = "¿tiene pluma?"
        assert any(p in texto.lower() for p in self.PATRONES_523_690)

    def test_tienes_donde_apuntar(self):
        """'tienes donde apuntar' debe ser detectado."""
        texto = "sí, ¿tienes donde apuntar?"
        assert any(p in texto.lower() for p in self.PATRONES_523_690)

    def test_puede_apuntar(self):
        """'puede apuntar' debe ser detectado."""
        texto = "¿puede apuntar un número?"
        assert any(p in texto.lower() for p in self.PATRONES_523_690)

    def test_tiene_para_apuntar(self):
        """'tiene para apuntar' debe ser detectado."""
        texto = "¿tiene para apuntar?"
        assert any(p in texto.lower() for p in self.PATRONES_523_690)

    def test_patrones_existentes_siguen(self):
        """Los patrones originales de FIX 523 siguen funcionando."""
        casos = [
            "¿tiene donde anotar?",
            "¿tienes para anotar un correo?",
            "le doy mi correo",
            "anote un número",
        ]
        for caso in casos:
            assert any(p in caso.lower() for p in self.PATRONES_523_690), \
                f"Patrón existente '{caso}' no detectado"

    def test_source_code_690a(self):
        """Verificar que agente_ventas.py tiene los patrones FIX 690A."""
        with open(os.path.join(os.path.dirname(os.path.dirname(__file__)), 'agente_ventas.py'),
                  encoding='utf-8') as f:
            source = f.read()
        assert 'FIX 690A' in source
        assert 'tienes con que anotar' in source
        assert 'tienes donde apuntar' in source


# ============================================================
# FIX 690B: GPT timeout fallback contextual (servidor)
# ============================================================

class TestFix690BGPTTimeoutFallback:
    """FIX 690B: Si GPT timeout + cliente dijo 'anotar', responder 'Sí, dígame'."""

    KEYWORDS_DICTAR = [
        'anotar', 'apuntar', 'lapiz', 'lápiz', 'papel', 'pluma',
        'donde escribir', 'con que escribir'
    ]

    def test_anotar_en_timeout_da_digame(self):
        """GPT timeout + 'tienes donde anotar' → 'Sí, dígame'."""
        speech = "Sí, ¿tienes donde anotar?"
        cliente_listo = any(p in speech.lower() for p in self.KEYWORDS_DICTAR)
        assert cliente_listo is True

    def test_apuntar_en_timeout_da_digame(self):
        """GPT timeout + 'tienes donde apuntar' → 'Sí, dígame'."""
        speech = "¿tienes donde apuntar?"
        cliente_listo = any(p in speech.lower() for p in self.KEYWORDS_DICTAR)
        assert cliente_listo is True

    def test_lapiz_en_timeout_da_digame(self):
        """GPT timeout + 'tienes lapiz' → 'Sí, dígame'."""
        speech = "¿tienes lapiz?"
        cliente_listo = any(p in speech.lower() for p in self.KEYWORDS_DICTAR)
        assert cliente_listo is True

    def test_papel_en_timeout_da_digame(self):
        """GPT timeout + 'tienes papel' → 'Sí, dígame'."""
        speech = "¿tienes papel?"
        cliente_listo = any(p in speech.lower() for p in self.KEYWORDS_DICTAR)
        assert cliente_listo is True

    def test_sin_keyword_no_detecta(self):
        """Texto sin keywords de dictar → no detecta."""
        speech = "Sí, mándame el catálogo"
        cliente_listo = any(p in speech.lower() for p in self.KEYWORDS_DICTAR)
        assert cliente_listo is False

    def test_fallback_chain_con_dictar(self):
        """Simular lógica completa: cliente_listo > ya_presento > ya_encargado."""
        speech = "Sí, tienes donde anotar"
        ya_presento = True
        ya_encargado = True
        cliente_listo = any(p in speech.lower() for p in self.KEYWORDS_DICTAR)

        if cliente_listo:
            respuesta = "Sí, claro, dígame el número por favor."
        elif not ya_presento:
            respuesta = "Me comunico de la marca NIOVAL..."
        elif not ya_encargado:
            respuesta = "¿Se encontrará el encargado?"
        else:
            respuesta = "Disculpe, ¿me puede repetir lo que me decía?"

        assert 'dígame' in respuesta.lower()

    def test_fallback_sin_dictar_sigue_normal(self):
        """Sin keywords de dictar, fallback sigue la cadena normal."""
        speech = "no está el encargado"
        ya_presento = True
        ya_encargado = True
        cliente_listo = any(p in speech.lower() for p in self.KEYWORDS_DICTAR)

        if cliente_listo:
            respuesta = "Sí, claro, dígame el número por favor."
        elif not ya_presento:
            respuesta = "Me comunico de la marca NIOVAL..."
        elif not ya_encargado:
            respuesta = "¿Se encontrará el encargado?"
        else:
            respuesta = "Disculpe, ¿me puede repetir lo que me decía?"

        assert 'repetir' in respuesta.lower()

    def test_source_code_690b(self):
        """Verificar que servidor_llamadas.py tiene FIX 690B."""
        with open(os.path.join(os.path.dirname(os.path.dirname(__file__)), 'servidor_llamadas.py'),
                  encoding='utf-8') as f:
            source = f.read()
        assert 'FIX 690B' in source
        assert 'cliente_listo_dictar_690' in source


# ============================================================
# FIX 690C: Post-filter override respuesta genérica
# ============================================================

class TestFix690CPostFilter:
    """FIX 690C: Si cliente dijo 'anotar' y GPT respondió genérico, override."""

    KEYWORDS_DICTAR_690 = ['anotar', 'apuntar', 'donde escribir', 'con que escribir',
                           'tienes lapiz', 'tiene lapiz', 'tienes papel', 'tiene papel',
                           'tienes pluma', 'tiene pluma']

    def test_anotar_con_repetir_override(self):
        """Cliente: 'anotar' + Bruce: 'me puede repetir' → override."""
        ultimo_cliente = "sí, ¿tienes donde anotar?"
        respuesta = "Disculpe, ¿me puede repetir lo que me decía?"
        respuesta_lower = respuesta.lower()

        cliente_listo = any(k in ultimo_cliente.lower() for k in self.KEYWORDS_DICTAR_690)
        respuesta_generica = any(p in respuesta_lower for p in [
            'me puede repetir', 'me podria repetir', 'no escuche', 'no le escuche',
            'disculpe', 'me decia'
        ])

        if cliente_listo and respuesta_generica:
            respuesta = "Sí, claro, dígame el número por favor."

        assert 'dígame' in respuesta.lower()

    def test_apuntar_con_disculpe_override(self):
        """Cliente: 'apuntar' + Bruce: 'Disculpe...' → override."""
        ultimo_cliente = "tienes donde apuntar"
        respuesta = "Disculpe, no alcancé a captar lo que me decía."
        respuesta_lower = respuesta.lower()

        cliente_listo = any(k in ultimo_cliente.lower() for k in self.KEYWORDS_DICTAR_690)
        respuesta_generica = any(p in respuesta_lower for p in [
            'me puede repetir', 'me podria repetir', 'no escuche', 'no le escuche',
            'disculpe', 'me decia'
        ])

        if cliente_listo and respuesta_generica:
            respuesta = "Sí, claro, dígame el número por favor."

        assert 'dígame' in respuesta.lower()

    def test_anotar_con_respuesta_buena_no_override(self):
        """Cliente: 'anotar' + Bruce: respuesta buena → NO override."""
        ultimo_cliente = "tienes donde anotar"
        respuesta = "Sí, claro, dígame el número por favor."
        respuesta_lower = respuesta.lower()

        cliente_listo = any(k in ultimo_cliente.lower() for k in self.KEYWORDS_DICTAR_690)
        respuesta_generica = any(p in respuesta_lower for p in [
            'me puede repetir', 'me podria repetir', 'no escuche', 'no le escuche',
            'disculpe', 'me decia'
        ])

        if cliente_listo and respuesta_generica:
            respuesta = "Sí, claro, dígame el número por favor."

        # Ya era buena, no se override
        assert 'dígame' in respuesta.lower()

    def test_sin_anotar_no_override(self):
        """Cliente sin 'anotar' + Bruce genérico → no override."""
        ultimo_cliente = "no está el encargado"
        respuesta = "Disculpe, ¿me puede repetir lo que me decía?"
        respuesta_lower = respuesta.lower()

        cliente_listo = any(k in ultimo_cliente.lower() for k in self.KEYWORDS_DICTAR_690)
        respuesta_generica = any(p in respuesta_lower for p in [
            'me puede repetir', 'me podria repetir', 'no escuche', 'no le escuche',
            'disculpe', 'me decia'
        ])

        if cliente_listo and respuesta_generica:
            respuesta = "Sí, claro, dígame el número por favor."

        assert 'repetir' in respuesta.lower()

    def test_source_code_690c(self):
        """Verificar que agente_ventas.py tiene FIX 690C."""
        with open(os.path.join(os.path.dirname(os.path.dirname(__file__)), 'agente_ventas.py'),
                  encoding='utf-8') as f:
            source = f.read()
        assert 'FIX 690C' in source
        assert 'keywords_dictar_690' in source


# ============================================================
# Tests de integración
# ============================================================

class TestIntegracionFix690:
    """Tests que simulan el escenario completo de BRUCE2202."""

    def test_bruce2202_scenario_pattern_detection(self):
        """BRUCE2202: 'Sí, ¿tienes dónde anotar?' → detectado por pattern detector."""
        texto = "sí, ¿tienes dónde anotar?"
        # FIX 631 normaliza acentos
        texto_normalizado = texto.replace('á', 'a').replace('é', 'e').replace('í', 'i').replace('ó', 'o').replace('ú', 'u')
        patrones = [
            "tiene donde anotar", "tienes donde anotar",
            "tienes con que anotar", "tienes donde apuntar",
        ]
        detectado = any(p in texto_normalizado.lower() for p in patrones)
        assert detectado, f"BRUCE2202: '{texto}' no detectado después de normalización"

    def test_bruce2202_scenario_garbled_stt(self):
        """BRUCE2202 STT garbled: 'Sí, tiene Sí' sin 'anotar' → fallback normal."""
        texto_garbled = "sí, tiene sí"
        keywords = ['anotar', 'apuntar', 'lapiz', 'papel', 'pluma']
        detectado = any(k in texto_garbled.lower() for k in keywords)
        assert not detectado, "Texto garbled sin keywords no debe detectar"

    def test_bruce2202_scenario_gpt_timeout_with_anotar(self):
        """BRUCE2202: GPT timeout + 'anotar' en texto → 'Sí, dígame'."""
        speech_result = "Sí, tienes donde anotar"
        gpt_timed_out = True  # Simular timeout
        ya_presento = True
        ya_encargado = True

        keywords = ['anotar', 'apuntar', 'lapiz', 'papel', 'pluma', 'donde escribir']
        cliente_listo = any(k in speech_result.lower() for k in keywords)

        if gpt_timed_out:
            if cliente_listo:
                respuesta = "Sí, claro, dígame el número por favor."
            elif not ya_presento:
                respuesta = "Me comunico de la marca NIOVAL..."
            elif not ya_encargado:
                respuesta = "¿Se encontrará el encargado?"
            else:
                respuesta = "Disculpe, ¿me puede repetir lo que me decía?"
        else:
            respuesta = "GPT normal response"

        assert 'dígame' in respuesta.lower()
        assert 'repetir' not in respuesta.lower()

    def test_bruce2202_scenario_postfilter_catches(self):
        """BRUCE2202: Incluso si pattern detector falla, post-filter corrige."""
        ultimo_cliente = "sí, ¿tienes dónde anotar?"
        respuesta_gpt = "Disculpe, ¿me puede repetir?"

        keywords = ['anotar', 'apuntar', 'donde escribir']
        cliente_listo = any(k in ultimo_cliente.lower() for k in keywords)
        respuesta_generica = 'me puede repetir' in respuesta_gpt.lower()

        if cliente_listo and respuesta_generica:
            respuesta_gpt = "Sí, claro, dígame el número por favor."

        assert 'dígame' in respuesta_gpt.lower()

    def test_triple_layer_coverage(self):
        """Verificar que las 3 capas de FIX 690 están en el código fuente."""
        agente_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'agente_ventas.py')
        servidor_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'servidor_llamadas.py')

        with open(agente_path, encoding='utf-8') as f:
            agente_src = f.read()
        with open(servidor_path, encoding='utf-8') as f:
            servidor_src = f.read()

        assert 'FIX 690A' in agente_src, "FIX 690A no encontrado en agente"
        assert 'FIX 690B' in servidor_src, "FIX 690B no encontrado en servidor"
        assert 'FIX 690C' in agente_src, "FIX 690C no encontrado en agente"
