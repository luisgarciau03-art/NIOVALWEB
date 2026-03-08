"""
FIX 878: FSM identificacion_nioval repetido (>=2x) → pivot a pedir_whatsapp_o_correo.
         BRUCE2551: cliente preguntó "¿Dónde están?" 4x, Bruce respondió "Mi nombre es Bruce..." 3x.

FIX 879: Respuesta larga (>120 chars) ante pedido corto de repetición (≤8 palabras).
         Audit 04/03: "Respuesta muy larga (157 chars) ante pedido de repetición".

FIX 880: Validar número capturado ≠ número propio de Bruce (662 353 1804 = 6623531804).
         BRUCE2551: eco de audio → STT captó número de Bruce como WhatsApp del cliente.
"""
import re
import pytest
from unittest.mock import MagicMock
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# =========================================================
# FIX 878: FSMContext.identity_repetidas + _execute pivot
# =========================================================
class TestFix878IdentityRepetidas:
    """FSM pivot después de 2 identificaciones repetidas."""

    def test_fsmcontext_tiene_identity_repetidas(self):
        """FSMContext inicializa identity_repetidas en 0."""
        from fsm_engine import FSMContext
        ctx = FSMContext()
        assert ctx.identity_repetidas == 0

    def test_primera_identificacion_usa_template_normal(self):
        """Primera vez que FSM usa identificacion_nioval → retorna template normal."""
        from fsm_engine import FSMEngine, FSMContext, Transition, ActionType
        engine = FSMEngine.__new__(FSMEngine)
        engine.context = FSMContext()
        assert engine.context.identity_repetidas == 0

        calls = []
        engine._get_template = lambda k: calls.append(k) or f"TEMPLATE:{k}"

        t = Transition.__new__(Transition)
        t.action_type = ActionType.TEMPLATE
        t.template_key = "identificacion_nioval"

        result = engine._execute(t, "¿De dónde me habla?")
        # Primera vez: identity_repetidas = 1, no pivota aún
        assert engine.context.identity_repetidas == 1
        assert "identificacion_nioval" in calls
        assert "pedir_whatsapp_o_correo" not in calls

    def test_segunda_identificacion_pivota(self):
        """Segunda vez (identity_repetidas == 2) → pivot a pedir_whatsapp_o_correo_breve."""
        from fsm_engine import FSMEngine, FSMContext, Transition, ActionType
        engine = FSMEngine.__new__(FSMEngine)
        engine.context = FSMContext()
        engine.context.identity_repetidas = 1  # Ya ocurrió 1 vez

        calls = []
        engine._get_template = lambda k: calls.append(k) or f"TEMPLATE:{k}"

        t = Transition.__new__(Transition)
        t.action_type = ActionType.TEMPLATE
        t.template_key = "identificacion_nioval"

        result = engine._execute(t, "¿Y dónde se ubican?")
        assert engine.context.identity_repetidas == 2
        # FIX 884/885: Ahora usa template breve para evitar PREGUNTA_REPETIDA
        assert "pedir_whatsapp_o_correo_breve" in calls
        assert result == "TEMPLATE:pedir_whatsapp_o_correo_breve"

    def test_tercera_identificacion_pivota(self):
        """Tercera y subsecuentes → pedir_numero_directo_885."""
        from fsm_engine import FSMEngine, FSMContext, Transition, ActionType
        engine = FSMEngine.__new__(FSMEngine)
        engine.context = FSMContext()
        engine.context.identity_repetidas = 2  # Ya ocurrió 2 veces

        calls = []
        engine._get_template = lambda k: calls.append(k) or f"TEMPLATE:{k}"

        t = Transition.__new__(Transition)
        t.action_type = ActionType.TEMPLATE
        t.template_key = "identificacion_nioval"

        result = engine._execute(t, "¿Dónde se encuentran?")
        assert engine.context.identity_repetidas == 3
        # FIX 885B: 3er+ identity usa template distinto
        assert "pedir_numero_directo_885" in calls

    def test_otros_templates_no_afectados(self):
        """FIX 878 solo intercepta identificacion_nioval, no otros."""
        from fsm_engine import FSMEngine, FSMContext, FSMState, Transition, ActionType
        engine = FSMEngine.__new__(FSMEngine)
        engine.context = FSMContext()
        engine.context.identity_repetidas = 5  # Muy alto
        engine.context.pitch_dado = True        # FIX 919: Evitar que timing guard intercepte pedir_whatsapp
        engine.context.pedir_datos_count = 1    # FIX 922: Avoid captura_minima intercept
        engine.state = FSMState.ENCARGADO_PRESENTE  # FIX 920/922: Need state for guards

        calls = []
        engine._get_template = lambda k: calls.append(k) or f"TEMPLATE:{k}"

        for key in ["identificacion_pitch", "pitch_inicial", "pedir_whatsapp", "despedida_cortes"]:
            calls.clear()
            t = Transition.__new__(Transition)
            t.action_type = ActionType.TEMPLATE
            t.template_key = key
            engine._execute(t, "texto")
            assert key in calls, f"Template '{key}' fue desviado incorrectamente"
            assert "pedir_whatsapp_o_correo" not in calls

    def test_reset_reinicia_contador(self):
        """FSMEngine.reset() reinicia identity_repetidas a 0."""
        from fsm_engine import FSMEngine
        engine = FSMEngine()
        engine.context.identity_repetidas = 5
        engine.reset()
        assert engine.context.identity_repetidas == 0

    def test_template_pedir_whatsapp_o_correo_existe(self):
        """El template pivot existe en TEMPLATES."""
        from response_templates import TEMPLATES
        assert "pedir_whatsapp_o_correo" in TEMPLATES
        texto = TEMPLATES["pedir_whatsapp_o_correo"][0]
        assert "?" in texto  # Debe ser una pregunta

    def test_fix875_y_878_no_interfieren(self):
        """FIX 875 (pitch_encargado) y FIX 878 (identificacion_nioval) coexisten."""
        from fsm_engine import FSMEngine, FSMContext, Transition, ActionType
        engine = FSMEngine.__new__(FSMEngine)
        engine.context = FSMContext()
        engine.context.pitch_dado = True
        engine.context.identity_repetidas = 0

        calls = []
        engine._get_template = lambda k: calls.append(k) or f"TEMPLATE:{k}"

        # FIX 875: pitch_encargado con pitch_dado=True → corto
        t875 = Transition.__new__(Transition)
        t875.action_type = ActionType.TEMPLATE
        t875.template_key = "pitch_encargado"
        engine._execute(t875, "Sí, soy yo")
        assert "pitch_encargado_corto" in calls

        # FIX 878: primera identificacion_nioval → normal (no pivota aún)
        calls.clear()
        t878 = Transition.__new__(Transition)
        t878.action_type = ActionType.TEMPLATE
        t878.template_key = "identificacion_nioval"
        engine._execute(t878, "¿De dónde?")
        assert engine.context.identity_repetidas == 1
        assert "identificacion_nioval" in calls


# =========================================================
# FIX 879: Respuesta larga ante repetición corta
# =========================================================
_PIDE_REPETICION_879 = re.compile(
    r'(?:perd[oó]n|mande|c[oó]mo\s+dijo|de\s+d[oó]nde|d[oó]nde\s+(?:est[aá]n?|se\s+ubican?|hablan?|dice)\b|no\s+(?:entend|escu[ij]))',
    re.IGNORECASE
)
_PITCH_LARGO_879 = re.compile(
    r'^(?:mi\s+nombre\s+es|somos\s+de\s+guadalajara|somos\s+distribuidores|le\s+comento|me\s+comunico\s+de)',
    re.IGNORECASE
)

_RESP_PITCH_LARGA = (
    "Mi nombre es Bruce, le llamo de la marca NIOVAL. Somos distribuidores de productos "
    "ferreteros de Guadalajara, Jalisco. Manejamos más de 15 categorías."
)


def _simular_fix879(respuesta, ultimo_msg_cliente):
    """Simula el post-filter FIX 879."""
    if len(respuesta) > 120 and _PITCH_LARGO_879.match(respuesta):
        palabras = len(ultimo_msg_cliente.split())
        if palabras <= 8 and _PIDE_REPETICION_879.search(ultimo_msg_cliente):
            primera = respuesta.split('.')[0].strip() + '.'
            if len(primera) > 80:
                primera = "Somos de Guadalajara, Jalisco."
            respuesta = primera + " ¿Se encuentra el encargado de compras?"
    return respuesta


class TestFix879RespuestaLargaRepeticion:
    """FIX 879: pitch largo + cliente pide repetición corta → respuesta concisa."""

    @pytest.mark.parametrize("msg", [
        "¿Perdón?",
        "¿De dónde me habla?",
        "¿Dónde están?",
        "¿Dónde se ubican?",
        "¿Cómo dijo?",
        "Perdón, ¿de dónde?",
        "Mande?",
        "No entendí",
        "¿Dónde hablan?",
    ])
    def test_detecta_pide_repeticion(self, msg):
        assert _PIDE_REPETICION_879.search(msg), f"No detectó repetición: '{msg}'"

    @pytest.mark.parametrize("msg", [
        "Sí, yo soy el encargado",
        "No tenemos WhatsApp",
        "Mándame el catálogo",
        "Cuánto cuestan las cintas?",
        "No me interesa",
    ])
    def test_no_falso_positivo_repeticion(self, msg):
        assert not _PIDE_REPETICION_879.search(msg), f"Falso positivo: '{msg}'"

    def test_activa_con_pitch_largo_y_repeticion_corta(self):
        """Pitch >120 chars + cliente ≤8 palabras + keyword → respuesta concisa."""
        result = _simular_fix879(_RESP_PITCH_LARGA, "¿Perdón?")
        assert len(result) < 120
        assert "¿Se encuentra el encargado" in result

    def test_no_activa_con_respuesta_corta(self):
        """Si Bruce ya responde corto, no modificar."""
        resp_corta = "Somos de Guadalajara."
        result = _simular_fix879(resp_corta, "¿Perdón?")
        assert result == resp_corta

    def test_no_activa_con_cliente_largo(self):
        """Si cliente dice más de 8 palabras, no es una repetición simple."""
        msg_largo = "Oiga, ¿de dónde me habla y cuáles son sus productos en especial?"
        result = _simular_fix879(_RESP_PITCH_LARGA, msg_largo)
        # No se activa porque el mensaje es largo
        assert result == _RESP_PITCH_LARGA

    def test_no_activa_sin_keyword_repeticion(self):
        """Sin keyword de repetición → no modificar aunque respuesta sea larga."""
        result = _simular_fix879(_RESP_PITCH_LARGA, "¿Qué productos tienen?")
        assert result == _RESP_PITCH_LARGA

    def test_primera_oracion_usada_si_corta(self):
        """Usa primera oración del pitch si es ≤80 chars."""
        resp = "Somos de Guadalajara. Manejamos más de 15 categorías de productos ferreteros."
        result = _simular_fix879(resp, "¿Perdón?")
        # resp es <120 chars, no se activa
        assert result == resp

    def test_fallback_si_primera_oracion_muy_larga(self):
        """Si primera oración >80 chars → usar fallback 'Somos de Guadalajara, Jalisco.'"""
        resp_sin_punto_corto = (
            "Mi nombre es Bruce y le llamo desde NIOVAL distribuidores ferreteros en Guadalajara Jalisco. "
            "Tenemos más de 15 categorías disponibles."
        )
        result = _simular_fix879(resp_sin_punto_corto, "¿Perdón?")
        assert "Guadalajara" in result
        assert "¿Se encuentra el encargado" in result


# =========================================================
# FIX 880: Número propio de Bruce detectado
# =========================================================
_NUMERO_PROPIO_BRUCE_880 = "6623531804"


def _simular_fix880(lead_data, respuesta="Perfecto, ya tengo el numero registrado."):
    """Simula el post-filter FIX 880."""
    activado = False
    for campo in ("whatsapp", "telefono_directo", "telefono"):
        val = str(lead_data.get(campo) or "")
        digitos = re.sub(r'[^\d]', '', val)
        if digitos.endswith(_NUMERO_PROPIO_BRUCE_880):
            lead_data.pop(campo, None)
            activado = True
            break
    if activado:
        respuesta = "Disculpe, ese numero no lo capte bien. ¿Me lo puede repetir por favor?"
    return respuesta, lead_data


class TestFix880NumeroPropiosBruce:
    """FIX 880: número propio de Bruce en lead_data → eliminar y re-preguntar."""

    def test_detecta_numero_bruce_en_whatsapp(self):
        """Si whatsapp == número de Bruce → lo elimina."""
        lead = {"whatsapp": "+526623531804"}
        resp, lead = _simular_fix880(lead)
        assert "whatsapp" not in lead
        assert "repetir" in resp.lower()

    def test_detecta_numero_bruce_sin_prefijo(self):
        """Número sin +52 también detectado."""
        lead = {"whatsapp": "6623531804"}
        resp, lead = _simular_fix880(lead)
        assert "whatsapp" not in lead

    def test_detecta_numero_bruce_en_telefono_directo(self):
        """Detecta en telefono_directo también."""
        lead = {"telefono_directo": "6623531804"}
        resp, lead = _simular_fix880(lead)
        assert "telefono_directo" not in lead

    def test_detecta_numero_bruce_en_telefono(self):
        """Detecta en campo 'telefono'."""
        lead = {"telefono": "+526623531804"}
        resp, lead = _simular_fix880(lead)
        assert "telefono" not in lead

    def test_no_afecta_numero_cliente_diferente(self):
        """Número legítimo del cliente no se toca."""
        lead = {"whatsapp": "+523312345678"}
        resp_orig = "Perfecto, ya tengo el numero registrado."
        resp, lead = _simular_fix880(lead, resp_orig)
        assert lead.get("whatsapp") == "+523312345678"
        assert resp == resp_orig

    def test_no_afecta_sin_numero_capturado(self):
        """Lead sin número no activa FIX 880."""
        lead = {}
        resp_orig = "Perfecto, ya tengo el numero registrado."
        resp, lead = _simular_fix880(lead, resp_orig)
        assert resp == resp_orig

    def test_numero_bruce_parcial_no_detectado(self):
        """Número que contiene solo parte del número de Bruce no dispara FIX 880."""
        lead = {"whatsapp": "+526623531"}  # Solo 9 dígitos, no termina en 6623531804
        resp_orig = "Perfecto."
        resp, lead = _simular_fix880(lead, resp_orig)
        # 6623531 no termina en 6623531804 (la cadena 6623531 < 6623531804)
        assert lead.get("whatsapp") == "+526623531"

    def test_numero_bruce_con_prefijo_pais_detectado(self):
        """Número con +52 completo (526623531804 = 12 dígitos) detectado."""
        lead = {"whatsapp": "526623531804"}
        resp, lead = _simular_fix880(lead)
        assert "whatsapp" not in lead

    def test_otros_campos_intactos_cuando_activa(self):
        """Cuando FIX 880 activa, otros campos de lead_data no se tocan."""
        lead = {
            "whatsapp": "6623531804",
            "nombre_negocio": "Ferretería Test",
            "ciudad": "Guadalajara",
        }
        resp, lead = _simular_fix880(lead)
        assert "whatsapp" not in lead
        assert lead.get("nombre_negocio") == "Ferretería Test"
        assert lead.get("ciudad") == "Guadalajara"

    def test_respuesta_re_pregunta_numero(self):
        """La respuesta override pide repetir el número."""
        lead = {"whatsapp": "+526623531804"}
        resp, _ = _simular_fix880(lead)
        assert "repetir" in resp.lower() or "repita" in resp.lower()
        assert "?" in resp
