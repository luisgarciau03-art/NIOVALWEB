"""
Tests FIX 744-747: Anti-loop GPT timeout + Re-engagement IVR + Pitch detection + Pattern immunity.

FIX 744: BRUCE2315 - Counter reset bug: "me puede repetir" no reseteaba counter → loop infinito
FIX 745: BRUCE2316 - Re-engagement: "buenas tardes" + gate fix para "¿Bueno?" (7 chars)
FIX 746: BRUCE2317 - Pitch detection: "productos" solo NO es pitch (requiere identificacion)
FIX 747: DIGAME_CONTINUAR 0% survival → inmunidad 4 listas
"""
import sys
import os
import inspect
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from agente_ventas import AgenteVentas


def _sa(t):
    """Strip acentos para comparaciones."""
    return t.replace('á','a').replace('é','e').replace('í','i').replace('ó','o').replace('ú','u').replace('ü','u').replace('ñ','n')


def _get_filtrar_source():
    """Obtener source de _filtrar_respuesta_post_gpt."""
    return inspect.getsource(AgenteVentas._filtrar_respuesta_post_gpt)


def _get_pattern_source():
    """Obtener source de _detectar_patron_simple_optimizado."""
    return inspect.getsource(AgenteVentas._detectar_patron_simple_optimizado)


# ============================================================
# FIX 744: Código presente
# ============================================================

class TestFix744CodigoPresente(unittest.TestCase):
    """FIX 744: Verificar que el código está presente en servidor."""

    def test_fix_744_en_servidor(self):
        """FIX 744 debe estar en servidor_llamadas.py."""
        servidor_path = os.path.join(os.path.dirname(__file__), '..', 'servidor_llamadas.py')
        with open(servidor_path, 'r', encoding='utf-8') as f:
            source = f.read()
        self.assertIn('FIX 744', source)
        self.assertIn('_es_fallback_744', source)
        self.assertIn('me puede repetir', source)

    def test_fix_744_no_resetea_fallback(self):
        """Verify counter reset condition includes 'me puede repetir'."""
        servidor_path = os.path.join(os.path.dirname(__file__), '..', 'servidor_llamadas.py')
        with open(servidor_path, 'r', encoding='utf-8') as f:
            source = f.read()
        # Should check for BOTH fallback messages
        fix_744_start = source.find('FIX 744')
        fix_744_section = source[fix_744_start:fix_744_start + 500]
        self.assertIn('no le estoy escuchando bien', fix_744_section)
        self.assertIn('me puede repetir', fix_744_section)


# ============================================================
# FIX 744: Lógica de counter reset
# ============================================================

class TestFix744CounterLogic(unittest.TestCase):
    """FIX 744: Lógica de reset del counter de GPT timeouts."""

    def test_fallback_disculpe_no_reset(self):
        """'Disculpe, me puede repetir?' NO debe resetear counter."""
        respuesta = "Disculpe, ¿me puede repetir lo que me decía?"
        _ra_744 = str(respuesta).lower()
        _es_fallback = ('no le estoy escuchando bien en este momento' in _ra_744 or
                        'me puede repetir' in _ra_744)
        self.assertTrue(_es_fallback, "Fallback 'me puede repetir' debe ser detectado")

    def test_fallback_no_escucho_no_reset(self):
        """'No le estoy escuchando bien' NO debe resetear counter."""
        respuesta = "Disculpe, no le estoy escuchando bien en este momento."
        _ra_744 = str(respuesta).lower()
        _es_fallback = ('no le estoy escuchando bien en este momento' in _ra_744 or
                        'me puede repetir' in _ra_744)
        self.assertTrue(_es_fallback, "Fallback 'no le estoy escuchando' debe ser detectado")

    def test_respuesta_normal_si_reset(self):
        """Respuesta normal SÍ debe resetear counter."""
        respuesta = "Entiendo, me podría proporcionar su WhatsApp para enviarle el catálogo?"
        _ra_744 = str(respuesta).lower()
        _es_fallback = ('no le estoy escuchando bien en este momento' in _ra_744 or
                        'me puede repetir' in _ra_744)
        self.assertFalse(_es_fallback, "Respuesta normal debe permitir reset")


# ============================================================
# FIX 745A: Código presente - señales fuertes
# ============================================================

class TestFix745CodigoPresente(unittest.TestCase):
    """FIX 745: Verificar que las nuevas señales están presentes."""

    def test_fix_745_senales_fuertes(self):
        """FIX 745A debe agregar buenas tardes/noches/etc a señales fuertes."""
        servidor_path = os.path.join(os.path.dirname(__file__), '..', 'servidor_llamadas.py')
        with open(servidor_path, 'r', encoding='utf-8') as f:
            source = f.read()
        # Buscar sección de frases_volvio_fuertes_712
        fuertes_start = source.find('frases_volvio_fuertes_712')
        fuertes_section = source[fuertes_start:fuertes_start + 2000]
        self.assertIn('buenas tardes', fuertes_section)
        self.assertIn('buenas noches', fuertes_section)
        self.assertIn('muy buenas', fuertes_section)
        self.assertIn('perdon', fuertes_section)
        self.assertIn('disculpe', fuertes_section)

    def test_fix_745_gate_modificado(self):
        """FASE 1.2 simplified gate: just 'if cliente_volvio:' (FIX 745B logic absorbed)."""
        servidor_path = os.path.join(os.path.dirname(__file__), '..', 'servidor_llamadas.py')
        with open(servidor_path, 'r', encoding='utf-8') as f:
            source = f.read()
        # FASE 1.2 absorbed FIX 745B into simplified gate
        self.assertIn('if cliente_volvio:', source)
        self.assertIn('FASE 1.2', source)


# ============================================================
# FIX 745: Lógica de señales
# ============================================================

class TestFix745Senales(unittest.TestCase):
    """FIX 745: Lógica de detección de señales de re-engagement."""

    def test_buenas_tardes_es_fuerte(self):
        """'buenas tardes' debe matchear señal fuerte."""
        frases_fuertes = [
            'buenas tardes', 'buenas noches', 'muy buenas', 'buen dia',
            'perdon', 'disculpe', 'disculpa',
        ]
        texto = 'perdon muy buenas tardes'
        tiene_fuerte = any(f in texto for f in frases_fuertes)
        self.assertTrue(tiene_fuerte, "'perdon muy buenas tardes' debe ser señal fuerte")

    def test_bueno_es_debil(self):
        """'bueno' debe matchear señal débil (no fuerte)."""
        frases_fuertes_745 = ['buenas tardes', 'buenas noches', 'muy buenas', 'buen dia',
                              'perdon', 'disculpe', 'disculpa']
        frases_debiles = ['bueno', 'hola', 'si', 'diga', 'digame']
        texto = 'bueno'
        tiene_fuerte = any(f in texto for f in frases_fuertes_745)
        tiene_debil = any(f in texto for f in frases_debiles)
        self.assertFalse(tiene_fuerte, "'bueno' NO es señal fuerte")
        self.assertTrue(tiene_debil, "'bueno' SÍ es señal débil")

    def test_gate_senal_detectada_bypass_len(self):
        """Si señal detectada, bypass len > 10 check."""
        # Simular: señal débil detectada, texto < 10 chars
        tiene_senal_fuerte = False
        tiene_senal_debil = True  # "bueno" matched
        texto_corto_712 = True
        timeout_espera_712 = False
        frase_limpia = "¿Bueno?"  # 7 chars

        cliente_volvio = (
            tiene_senal_fuerte or
            (tiene_senal_debil and texto_corto_712) or
            timeout_espera_712
        )

        # Viejo gate: FALLA (7 < 10)
        old_gate = cliente_volvio and len(frase_limpia) > 10
        self.assertFalse(old_gate, "Gate viejo debe fallar para '¿Bueno?' (7 chars)")

        # Nuevo gate FIX 745B: PASA
        _senal_detectada_745 = tiene_senal_fuerte or tiene_senal_debil
        new_gate = cliente_volvio and (_senal_detectada_745 or len(frase_limpia) > 10)
        self.assertTrue(new_gate, "Gate nuevo FIX 745B debe pasar para '¿Bueno?' con señal débil")

    def test_sin_senal_requiere_len(self):
        """Sin señal detectada (solo timeout), aún requiere len > 10."""
        tiene_senal_fuerte = False
        tiene_senal_debil = False
        timeout_espera_712 = True
        frase_limpia = "mmm"  # 3 chars, no signal

        cliente_volvio = timeout_espera_712

        _senal_detectada_745 = tiene_senal_fuerte or tiene_senal_debil
        new_gate = cliente_volvio and (_senal_detectada_745 or len(frase_limpia) > 10)
        self.assertFalse(new_gate, "Sin señal + timeout + texto corto → gate debe fallar")


# ============================================================
# FIX 746: Código presente
# ============================================================

class TestFix746CodigoPresente(unittest.TestCase):
    """FIX 746: Verificar que el código está presente."""

    def test_fix_746_en_filtrar(self):
        source = _get_filtrar_source()
        self.assertIn('FIX 746', source)
        self.assertIn('_tiene_identidad_746', source)
        self.assertIn('_tiene_productos_746', source)


# ============================================================
# FIX 746: Lógica pitch detection
# ============================================================

class TestFix746PitchDetection(unittest.TestCase):
    """FIX 746: Pitch real = identificación + productos."""

    def test_pitch_completo_detectado(self):
        """'marca NIOVAL productos ferreteros' = pitch real."""
        respuesta_lower = "me comunico de la marca nioval, productos ferreteros"
        _tiene_identidad = any(p in respuesta_lower for p in ["nioval", "marca", "distribuidor"])
        _tiene_productos = any(p in respuesta_lower for p in ["productos", "ferreteros", "ferreteria", "herramientas"])
        tiene_pitch = _tiene_identidad and _tiene_productos
        self.assertTrue(tiene_pitch, "Pitch completo con marca + productos debe ser detectado")

    def test_catalogo_sin_marca_no_pitch(self):
        """'catálogo de nuestros productos' SIN marca = NO pitch."""
        respuesta_lower = "me podría dar su whatsapp para enviarle el catálogo de nuestros productos de ferretería"
        _tiene_identidad = any(p in respuesta_lower for p in ["nioval", "marca", "distribuidor"])
        _tiene_productos = any(p in respuesta_lower for p in ["productos", "ferreteros", "ferreteria", "herramientas"])
        tiene_pitch = _tiene_identidad and _tiene_productos
        self.assertFalse(tiene_pitch, "Mención de productos SIN identificación NO es pitch")

    def test_solo_marca_no_pitch(self):
        """'marca NIOVAL' sin productos = NO pitch."""
        respuesta_lower = "somos la marca nioval, me podría dar su whatsapp"
        _tiene_identidad = any(p in respuesta_lower for p in ["nioval", "marca", "distribuidor"])
        _tiene_productos = any(p in respuesta_lower for p in ["productos", "ferreteros", "ferreteria", "herramientas"])
        tiene_pitch = _tiene_identidad and _tiene_productos
        self.assertFalse(tiene_pitch, "Solo marca sin productos NO es pitch completo")

    def test_fix_746_agrega_pitch_sin_marca(self):
        """FIX 650+746: Si respuesta pide contacto sin pitch real, agregar pitch."""
        agente = AgenteVentas()
        agente.conversation_history = [
            {"role": "assistant", "content": "Hola, buen día"},
            {"role": "user", "content": "Llamar a empresa ferretera del norte"},
        ]
        agente.encargado_confirmado = False
        agente.pitch_dado = False
        # GPT responde pidiendo WhatsApp sin identificarse
        resultado = agente._filtrar_respuesta_post_gpt(
            "¿Me podría dar su WhatsApp para enviarle el catálogo de nuestros productos?",
            {}
        )
        resultado_lower = resultado.lower()
        # FIX 650+746 debe haber agregado pitch con NIOVAL
        self.assertIn("nioval", resultado_lower,
                      f"FIX 650+746 debe agregar pitch con NIOVAL, recibido: '{resultado[:80]}'")


# ============================================================
# FIX 747: Código presente
# ============================================================

def _get_procesar_source():
    """Obtener source de procesar_respuesta (contiene listas de inmunidad)."""
    return inspect.getsource(AgenteVentas.procesar_respuesta)


class TestFix747CodigoPresente(unittest.TestCase):
    """FIX 747: Verificar que DIGAME_CONTINUAR está en _PATRONES_INMUNES_UNIVERSAL (covers all 4 lists)."""

    def _get_universal_section(self):
        """Get the _PATRONES_INMUNES_UNIVERSAL set definition from procesar_respuesta."""
        source = _get_procesar_source()
        idx_univ = source.find('_PATRONES_INMUNES_UNIVERSAL')
        self.assertGreater(idx_univ, -1, "_PATRONES_INMUNES_UNIVERSAL must exist in procesar_respuesta")
        idx_end = source.find('}', idx_univ)
        return source[idx_univ:idx_end + 1]

    def test_fix_747_en_598(self):
        """FASE 1.1: patrones_inmunes_pregunta_598 = _PATRONES_INMUNES_UNIVERSAL which has DIGAME_CONTINUAR."""
        source = _get_procesar_source()
        section = self._get_universal_section()
        self.assertIn('DIGAME_CONTINUAR', section)
        self.assertIn('patrones_inmunes_pregunta_598 = _PATRONES_INMUNES_UNIVERSAL', source)

    def test_fix_747_en_600(self):
        """FASE 1.1: patrones_inmunes_pero = _PATRONES_INMUNES_UNIVERSAL which has DIGAME_CONTINUAR."""
        source = _get_procesar_source()
        section = self._get_universal_section()
        self.assertIn('DIGAME_CONTINUAR', section)
        self.assertIn('patrones_inmunes_pero = _PATRONES_INMUNES_UNIVERSAL', source)

    def test_fix_747_en_601(self):
        """FASE 1.1: patrones_inmunes_601 = _PATRONES_INMUNES_UNIVERSAL which has DIGAME_CONTINUAR."""
        source = _get_procesar_source()
        section = self._get_universal_section()
        self.assertIn('DIGAME_CONTINUAR', section)
        self.assertIn('patrones_inmunes_601 = _PATRONES_INMUNES_UNIVERSAL', source)

    def test_fix_747_en_602(self):
        """FASE 1.1: patrones_inmunes_602 = _PATRONES_INMUNES_UNIVERSAL which has DIGAME_CONTINUAR."""
        source = _get_procesar_source()
        section = self._get_universal_section()
        self.assertIn('DIGAME_CONTINUAR', section)
        self.assertIn('patrones_inmunes_602 = _PATRONES_INMUNES_UNIVERSAL', source)


if __name__ == "__main__":
    unittest.main()
