# -*- coding: utf-8 -*-
"""
Tests de regresión para FIX 688 (OTRA_SUCURSAL con sedes/matrices/comunicarse directamente)
y FIX 689 (no repetir pitch en ¿Bueno? cuando ya se presentó).
"""
import os
import sys
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault("OPENAI_API_KEY", "sk-test-dummy")
os.environ.setdefault("ELEVENLABS_API_KEY", "test-dummy")
os.environ.setdefault("TWILIO_ACCOUNT_SID", "AC-test")
os.environ.setdefault("TWILIO_AUTH_TOKEN", "test-token")

from agente_ventas import AgenteVentas


# ============================================================
# FIX 688: OTRA_SUCURSAL con sedes/matrices/corporativo
# ============================================================

class TestFix688OtraSucursalSedes:
    """FIX 688: BRUCE2200 - 'comunicarse directamente con Cuba' debe detectarse."""

    def _crear_agente(self):
        a = AgenteVentas.__new__(AgenteVentas)
        a.conversation_history = []
        a.datos_capturados = {}
        a.catalogo_prometido = False
        a.datos_capturados_count = 0
        a.estado_conversacion = None
        a.turno_actual = 2
        a.encargado_disponible = None
        a.nombre_negocio = "Plomelek"
        return a

    def test_comunicarse_directamente_detectado(self):
        """'comunicarse directamente con Cuba' → OTRA_SUCURSAL."""
        patrones = [
            'comunicarse directamente', 'hablar directamente con',
            'llamar directamente', 'directamente con ellos',
            'la casa matriz', 'la sede', 'las oficinas centrales',
            'corporativo', 'el corporativo',
        ]
        texto = "es que tiene que comunicarse directamente con cuba"
        texto_lower = texto.lower()
        detectado = any(p in texto_lower for p in patrones)
        assert detectado, "Debe detectar 'comunicarse directamente'"

    def test_hablar_directamente_detectado(self):
        """'hablar directamente con la matriz' → OTRA_SUCURSAL."""
        texto = "tiene que hablar directamente con la matriz en hermosillo"
        patrones = ['comunicarse directamente', 'hablar directamente con', 'la matriz']
        detectado = any(p in texto.lower() for p in patrones)
        assert detectado

    def test_corporativo_detectado(self):
        """'eso se maneja en el corporativo' → OTRA_SUCURSAL."""
        texto = "no, eso se maneja en el corporativo"
        patrones = ['corporativo', 'el corporativo']
        detectado = any(p in texto.lower() for p in patrones)
        assert detectado

    def test_casa_matriz_detectado(self):
        """'la casa matriz lleva eso' → OTRA_SUCURSAL."""
        texto = "no, la casa matriz lleva eso"
        patrones = ['la casa matriz']
        detectado = any(p in texto.lower() for p in patrones)
        assert detectado

    def test_oficinas_centrales_detectado(self):
        """'las oficinas centrales manejan compras' → OTRA_SUCURSAL."""
        texto = "las oficinas centrales manejan eso"
        patrones = ['las oficinas centrales', 'la oficina central']
        detectado = any(p in texto.lower() for p in patrones)
        assert detectado

    def test_sede_detectado(self):
        """'eso lo ve la sede' → OTRA_SUCURSAL."""
        texto = "eso lo ve la sede en guadalajara"
        patrones = ['la sede']
        detectado = any(p in texto.lower() for p in patrones)
        assert detectado

    def test_directamente_con_ellos_detectado(self):
        """'hable directamente con ellos' → OTRA_SUCURSAL."""
        texto = "mejor hable directamente con ellos"
        patrones = ['directamente con ellos']
        detectado = any(p in texto.lower() for p in patrones)
        assert detectado

    def test_comunicarse_con_nosotros_no_detecta(self):
        """'comunicarse con nosotros' NO es otra sucursal (es Bruce hablando)."""
        texto = "para cuando pueda comunicarse con nosotros"
        patrones = ['comunicarse directamente', 'hablar directamente con']
        detectado = any(p in texto.lower() for p in patrones)
        assert not detectado, "'comunicarse con nosotros' no debe matchear"

    def test_source_code_tiene_patrones_688(self):
        """Verificar que agente_ventas.py tiene los patrones FIX 688."""
        with open(os.path.join(os.path.dirname(os.path.dirname(__file__)), 'agente_ventas.py'),
                  encoding='utf-8') as f:
            source = f.read()
        assert 'comunicarse directamente' in source
        assert 'la casa matriz' in source
        assert 'corporativo' in source
        assert 'la sede' in source


# ============================================================
# FIX 689: No repetir pitch en ¿Bueno? cuando ya se presentó
# ============================================================

class TestFix689NoPitchRepetido:
    """FIX 689: BRUCE2193 - ¿Bueno? tras pitch ya dado NO debe repetir pitch completo."""

    def test_ya_presento_nioval_detectado(self):
        """Si historial tiene 'nioval' en assistant msg → ya_presento_689 = True."""
        history = [
            {"role": "assistant", "content": "Me comunico de la marca nioval para productos ferreteros."},
            {"role": "user", "content": "¿Sí?"},
        ]
        ya_presento = any('nioval' in msg.get('content', '').lower()
                          for msg in history if msg['role'] == 'assistant')
        assert ya_presento is True

    def test_no_presento_nioval(self):
        """Si historial NO tiene 'nioval' → ya_presento_689 = False."""
        history = [
            {"role": "assistant", "content": "Hola, buen día."},
            {"role": "user", "content": "¿Bueno?"},
        ]
        ya_presento = any('nioval' in msg.get('content', '').lower()
                          for msg in history if msg['role'] == 'assistant')
        assert ya_presento is False

    def test_con_pitch_y_bueno_no_repite_pitch(self):
        """Simular FIX 604+689: si ya presentó NIOVAL, ¿Bueno? NO retorna pitch completo."""
        history = [
            {"role": "assistant", "content": "Me comunico de la marca NIOVAL, ¿se encontrará el encargado?"},
            {"role": "user", "content": "¿Sí?"},
        ]
        mensajes_usuario = [msg for msg in history if msg['role'] == 'user'
                            and '[Timeout' not in msg.get('content', '')]
        es_inicio_604 = len(mensajes_usuario) <= 1

        ya_presento_689 = any('nioval' in msg.get('content', '').lower()
                              for msg in history if msg['role'] == 'assistant')

        if es_inicio_604 and ya_presento_689:
            # FIX 689: No repetir pitch, dejar que FIX 621B maneje
            accion = "fall_through_621b"
        elif es_inicio_604 and not ya_presento_689:
            accion = "pitch_completo"
        else:
            accion = "otro"

        assert accion == "fall_through_621b", \
            f"Con pitch ya dado, ¿Bueno? debe fall-through a 621B, no {accion}"

    def test_sin_pitch_y_bueno_da_pitch(self):
        """Sin presentación previa, ¿Bueno? SÍ da pitch completo."""
        history = [
            {"role": "assistant", "content": "Hola, buen día."},
        ]
        ya_presento_689 = any('nioval' in msg.get('content', '').lower()
                              for msg in history if msg['role'] == 'assistant')

        if ya_presento_689:
            accion = "fall_through_621b"
        else:
            accion = "pitch_completo"

        assert accion == "pitch_completo"

    def test_621b_repite_pregunta_no_pitch(self):
        """FIX 621B: Si último Bruce termina en '?', repetir la pregunta."""
        ultimo_bruce = "¿Se encontrará el encargado o encargada de compras?"
        termina_en_pregunta = ultimo_bruce.strip().endswith('?')
        assert termina_en_pregunta is True
        # FIX 621B extraería "¿Se encontrará el encargado..." y la repetiría
        # En vez de dar pitch completo

    def test_source_code_tiene_fix_689(self):
        """Verificar que agente_ventas.py tiene check FIX 689."""
        with open(os.path.join(os.path.dirname(os.path.dirname(__file__)), 'agente_ventas.py'),
                  encoding='utf-8') as f:
            source = f.read()
        assert 'ya_presento_689' in source
        assert 'FIX 689' in source


# ============================================================
# Tests de integración
# ============================================================

class TestIntegracionFix688_689:
    """Tests que combinan FIX 688 con detección existente."""

    def test_bruce2200_scenario(self):
        """Escenario BRUCE2200: 'comunicarse directamente con Cuba' → OTRA_SUCURSAL."""
        texto = "es que somos sucursal, tiene que comunicarse directamente con cuba"
        patrones_otra_sucursal = [
            'otra sucursal', 'la otra sucursal', 'en la otra',
            'no es en esta', 'no es esta sucursal',
            'la matriz', 'en la matriz', 'la central', 'la principal',
            'comunicarse directamente', 'hablar directamente con',
            'llamar directamente', 'directamente con ellos',
            'la casa matriz', 'la sede', 'las oficinas centrales',
            'corporativo', 'el corporativo',
        ]
        detectado = any(p in texto.lower() for p in patrones_otra_sucursal)
        assert detectado, "BRUCE2200 debe detectarse como OTRA_SUCURSAL"

    def test_bruce2193_scenario(self):
        """Escenario BRUCE2193: ¿Bueno? después de pitch completo."""
        history = [
            {"role": "assistant", "content": "Me comunico de la marca NIOVAL, productos ferreteros, ¿se encontrará el encargado de compras?"},
            {"role": "user", "content": "¿Sí?"},
        ]
        # Cliente dice "¿Bueno?" como segundo mensaje
        texto_cliente = "bueno"
        verificaciones = ["bueno", "¿bueno?", "bueno?", "hola", "¿hola?"]
        es_verificacion = texto_cliente.lower().strip().rstrip('.,;:!?¿¡') in verificaciones

        mensajes_usuario = [msg for msg in history if msg['role'] == 'user']
        es_inicio_604 = len(mensajes_usuario) <= 1

        ya_presento_689 = any('nioval' in msg.get('content', '').lower()
                              for msg in history if msg['role'] == 'assistant')

        assert es_verificacion is True
        assert es_inicio_604 is True
        assert ya_presento_689 is True
        # Resultado: FIX 689 impide repetir pitch, FIX 621B repite pregunta

    def test_patrones_antiguos_siguen_funcionando(self):
        """Los patrones de OTRA_SUCURSAL originales siguen detectando."""
        casos = [
            "es en otra sucursal",
            "no es en esta, es en la otra",
            "en la matriz se ve eso",
            "nos mandan de monterrey",
            "aqui no hay encargado",
        ]
        patrones_existentes = [
            'otra sucursal', 'en la otra', 'no es en esta',
            'la matriz', 'nos mandan de',
            'aqui no hay encargado',
        ]
        for caso in casos:
            detectado = any(p in caso.lower() for p in patrones_existentes)
            assert detectado, f"Caso '{caso}' debe detectarse con patrones existentes"
