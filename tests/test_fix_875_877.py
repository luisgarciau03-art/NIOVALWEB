"""
FIX 875: INFO_NO_SOLICITADA — pitch_encargado da lista de productos cuando pitch ya fue dado.
         FSM usa pitch_encargado_corto cuando FSMContext.pitch_dado=True.

FIX 876: CATALOGO_POST_CAPTURA — FIX 522 solo bloqueaba preguntas (¿le envío?),
         no statements ('le envío el catálogo'). Ampliado con statements.

FIX 877: PREGUNTA_NOMBRE_INNECESARIA — Bruce dice "Mi nombre es Bruce, le llamo de NIOVAL..."
         con lista de productos DESPUÉS de capturar contacto.
"""
import re
import pytest
from unittest.mock import MagicMock, patch
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# =========================================================
# Helpers
# =========================================================
def _make_history_mixed(*pairs):
    return [{"role": role, "content": content} for role, content in pairs]


# =========================================================
# FIX 875: pitch_encargado_corto
# =========================================================
class TestFix875PitchEncargadoCorto:
    """FSMContext.pitch_dado=True → _execute usa pitch_encargado_corto."""

    def test_template_pitch_encargado_corto_existe(self):
        """El template pitch_encargado_corto debe existir en TEMPLATES."""
        from response_templates import TEMPLATES
        assert "pitch_encargado_corto" in TEMPLATES
        texto = TEMPLATES["pitch_encargado_corto"][0]
        # Debe preguntar por WhatsApp o correo
        assert "whatsapp" in texto.lower() or "correo" in texto.lower()
        # No debe tener lista de productos (diferencia del pitch largo)
        assert "mas de quince" not in texto.lower()
        assert "cintas tapagoteras" not in texto.lower()
        assert "griferia" not in texto.lower()

    def test_template_pitch_encargado_tiene_nioval(self):
        """El template pitch_encargado menciona NIOVAL y productos ferreteros."""
        from response_templates import TEMPLATES
        texto = TEMPLATES["pitch_encargado"][0]
        assert "nioval" in texto.lower() or "ferretero" in texto.lower()

    def test_execute_pitch_encargado_sin_pitch_dado_usa_largo(self):
        """Cuando pitch_dado=False, _execute retorna pitch_encargado normal."""
        from fsm_engine import FSMEngine, FSMContext, Transition, ActionType

        engine = FSMEngine.__new__(FSMEngine)
        engine.context = FSMContext.__new__(FSMContext)
        engine.context.pitch_dado = False

        # Mock de _get_template para rastrear qué key se usa
        calls = []
        def fake_get_template(key):
            calls.append(key)
            return f"TEMPLATE:{key}"

        engine._get_template = fake_get_template

        t = Transition.__new__(Transition)
        t.action_type = ActionType.TEMPLATE
        t.template_key = "pitch_encargado"

        result = engine._execute(t, "Si, soy yo")
        assert calls[0] == "pitch_encargado"

    def test_execute_pitch_encargado_con_pitch_dado_usa_corto(self):
        """Cuando pitch_dado=True, _execute retorna pitch_encargado_corto."""
        from fsm_engine import FSMEngine, FSMContext, Transition, ActionType

        engine = FSMEngine.__new__(FSMEngine)
        engine.context = FSMContext.__new__(FSMContext)
        engine.context.pitch_dado = True

        calls = []
        def fake_get_template(key):
            calls.append(key)
            return f"TEMPLATE:{key}"

        engine._get_template = fake_get_template

        t = Transition.__new__(Transition)
        t.action_type = ActionType.TEMPLATE
        t.template_key = "pitch_encargado"

        result = engine._execute(t, "Si, soy yo")
        assert calls[0] == "pitch_encargado_corto"
        assert result == "TEMPLATE:pitch_encargado_corto"

    def test_execute_otros_templates_no_afectados(self):
        """FIX 875 solo intercepta pitch_encargado, no otros templates."""
        from fsm_engine import FSMEngine, FSMContext, FSMState, Transition, ActionType

        engine = FSMEngine.__new__(FSMEngine)
        engine.context = FSMContext()
        engine.context.pitch_dado = True
        engine.context.pedir_datos_count = 1  # FIX 922: Avoid captura_minima intercept
        engine.state = FSMState.ENCARGADO_PRESENTE  # FIX 920/922: Need state for guards

        calls = []
        def fake_get_template(key):
            calls.append(key)
            return f"TEMPLATE:{key}"

        engine._get_template = fake_get_template

        for key in ["pitch_inicial", "pedir_whatsapp", "despedida_cortes", "confirmar_telefono"]:
            calls.clear()
            t = Transition.__new__(Transition)
            t.action_type = ActionType.TEMPLATE
            t.template_key = key
            engine._execute(t, "texto")
            assert calls[0] == key, f"Template '{key}' fue redirigido incorrectamente"

    def test_pitch_encargado_corto_tiene_pregunta(self):
        """pitch_encargado_corto debe terminar con pregunta (¿?)."""
        from response_templates import TEMPLATES
        texto = TEMPLATES["pitch_encargado_corto"][0]
        assert "?" in texto


# =========================================================
# FIX 876: Statements de catálogo en FIX 522
# =========================================================
class TestFix876CatalogoStatements:
    """FIX 522/876 detecta tanto preguntas como statements de re-oferta."""

    # Replicar la lógica del post-filter FIX 522/876
    _FRASES_REOFERTA = [
        '¿le gustaría recibirlo', '¿le gustaria recibirlo',
        '¿le envío el catálogo', '¿le envio el catalogo',
        '¿por whatsapp o correo', '¿whatsapp o correo',
        # FIX 876: Statements
        'le envío el catálogo', 'le envio el catalogo',
        'enviarle el catálogo', 'enviarle el catalogo',
        'le mando el catálogo', 'le mando el catalogo',
        'recibir nuestro catálogo', 'recibir nuestro catalogo',
        'le gustaria recibir nuestro catalogo', 'le gustaría recibir nuestro catálogo',
    ]

    def _detecta_reoferta(self, texto):
        texto_lower = texto.lower()
        return any(frase in texto_lower for frase in self._FRASES_REOFERTA)

    @pytest.mark.parametrize("stmt", [
        "Le envío el catálogo en las próximas horas.",
        "Con gusto le envio el catalogo de productos.",
        "Puedo enviarle el catálogo por correo.",
        "Le mando el catálogo ahora mismo.",
        "¿Le gustaría recibir nuestro catálogo?",
        "¿Le envío el catálogo por WhatsApp?",
    ])
    def test_detecta_reoferta(self, stmt):
        assert self._detecta_reoferta(stmt), f"No detectó re-oferta: '{stmt}'"

    @pytest.mark.parametrize("stmt", [
        "Muchas gracias por su tiempo. Que tenga excelente día.",
        "¿Se encontrará el encargado de compras?",
        "Entendido, no se preocupe.",
        "¿Me puede repetir el número?",
    ])
    def test_no_falso_positivo(self, stmt):
        assert not self._detecta_reoferta(stmt), f"Falso positivo: '{stmt}'"

    def test_statement_nuevo_detectado_876(self):
        """Los statements añadidos en FIX 876 (no estaban en original) son detectados."""
        # Estos NO estaban en FIX 522 original (solo había preguntas)
        nuevos_patterns = [
            'le envío el catálogo de productos',
            'le envio el catalogo esta tarde',
            'enviarle el catálogo por whatsapp',
            'le mando el catálogo ahora',
            'recibir nuestro catálogo es gratuito',
        ]
        for stmt in nuevos_patterns:
            assert self._detecta_reoferta(stmt), f"FIX 876 pattern no detectado: '{stmt}'"


# =========================================================
# FIX 877: identificacion_nioval post-captura
# =========================================================
_NOMBRE_BRUCE_877 = re.compile(r'^mi\s+nombre\s+es\s+bruce', re.IGNORECASE)
_PRODUCTOS_877 = re.compile(
    r'\.\s*(Somos distribuidores.*|Manejamos.*|distribuimos.*)',
    re.IGNORECASE | re.DOTALL
)


def _simular_fix877(respuesta, lead_data):
    """Simula exactamente la lógica del post-filter FIX 877."""
    if _NOMBRE_BRUCE_877.match(respuesta):
        contacto_ya = (lead_data.get('whatsapp') or lead_data.get('email')
                       or lead_data.get('telefono_directo'))
        if contacto_ya:
            respuesta = "Le llamo de NIOVAL, distribuidores de ferretería en Guadalajara. Que tenga excelente día."
        else:
            tiene_pregunta = '?' in respuesta
            if not tiene_pregunta:
                respuesta = re.sub(_PRODUCTOS_877, '.', respuesta)
                if not respuesta.rstrip().endswith('?'):
                    respuesta = respuesta.rstrip('.') + ". ¿Se encuentra el encargado de compras?"
    return respuesta


class TestFix877IdentificacionNioval:
    """FIX 877: identificacion_nioval recortada post-captura."""

    _RESP_TIPICA = (
        "Mi nombre es Bruce, le llamo de la marca NIOVAL. Somos distribuidores de productos "
        "ferreteros de Guadalajara, Jalisco."
    )

    def test_post_captura_whatsapp_da_version_compacta(self):
        """Si WhatsApp ya capturado → respuesta compacta sin lista de productos."""
        lead = {"whatsapp": "3312345678"}
        result = _simular_fix877(self._RESP_TIPICA, lead)
        assert "Le llamo de NIOVAL" in result
        assert "Somos distribuidores de productos ferreteros" not in result
        assert "Mi nombre es Bruce" not in result

    def test_post_captura_email_da_version_compacta(self):
        """Si email ya capturado → versión compacta."""
        lead = {"email": "cliente@empresa.com"}
        result = _simular_fix877(self._RESP_TIPICA, lead)
        assert "NIOVAL" in result
        assert "Mi nombre es Bruce" not in result

    def test_post_captura_telefono_da_version_compacta(self):
        """Si telefono_directo ya capturado → versión compacta."""
        lead = {"telefono_directo": "3312345678"}
        result = _simular_fix877(self._RESP_TIPICA, lead)
        assert "NIOVAL" in result
        assert "Mi nombre es Bruce" not in result

    def test_sin_contacto_sin_pregunta_agrega_pivot(self):
        """Sin contacto capturado Y sin '?' → quitar lista y añadir pivot encargado."""
        lead = {}
        result = _simular_fix877(self._RESP_TIPICA, lead)
        assert "Mi nombre es Bruce" in result  # Keeps intro
        assert "Somos distribuidores de productos ferreteros" not in result  # Removes product list
        assert "¿Se encuentra el encargado de compras?" in result  # Adds pivot

    def test_sin_contacto_con_pregunta_no_modifica(self):
        """Si ya tiene pregunta → FIX 877 no altera el segundo branch."""
        lead = {}
        resp_con_pregunta = "Mi nombre es Bruce, le llamo de NIOVAL. ¿Se encuentra el encargado?"
        result = _simular_fix877(resp_con_pregunta, lead)
        # Ya tiene pregunta → no se modifica por el segundo branch
        assert result == resp_con_pregunta

    def test_respuesta_sin_mi_nombre_es_no_afectada(self):
        """Respuestas que no empiezan con 'Mi nombre es Bruce' no se tocan."""
        lead = {"whatsapp": "3312345678"}
        resps = [
            "Hola, soy Bruce de NIOVAL.",
            "Bruce, agente de ventas de NIOVAL.",
            "¿Le envío el catálogo?",
            "Entendido.",
        ]
        for resp in resps:
            result = _simular_fix877(resp, lead)
            assert result == resp, f"FIX 877 modificó respuesta que no debía: '{resp}'"

    def test_regex_detecta_variantes_inicio(self):
        """El regex detecta variantes de capitalización."""
        variantes = [
            "Mi nombre es Bruce, soy de NIOVAL.",
            "mi nombre es bruce, le llamo de...",
            "MI NOMBRE ES BRUCE, LE LLAMO...",
        ]
        for v in variantes:
            assert _NOMBRE_BRUCE_877.match(v), f"No matcheó: '{v}'"

    def test_regex_no_detecta_mitad_de_oracion(self):
        """El regex solo matchea al inicio (^), no en mitad de oración."""
        resp = "Hola. Mi nombre es Bruce, le llamo de NIOVAL."
        assert not _NOMBRE_BRUCE_877.match(resp)

    def test_version_compacta_tiene_despedida(self):
        """La versión compacta post-captura incluye despedida."""
        lead = {"whatsapp": "3312345678"}
        result = _simular_fix877(self._RESP_TIPICA, lead)
        assert "excelente día" in result or "excelente dia" in result.lower()

    def test_sin_contacto_ninguno_no_da_compacta(self):
        """Con lead_data vacío → NO da versión compacta (esa es solo post-captura)."""
        lead = {}
        result = _simular_fix877(self._RESP_TIPICA, lead)
        # El resultado debe contener la intro de Bruce
        assert "Mi nombre es Bruce" in result


# =========================================================
# Regresión: FIX 875 no rompe otros templates
# =========================================================
class TestFix875Regresion:
    """Verificar que FIX 875 no afecta plantillas fuera de pitch_encargado."""

    def test_pitch_inicial_no_afectado(self):
        """pitch_inicial siempre usa su template normal."""
        from fsm_engine import FSMEngine, FSMContext, Transition, ActionType

        engine = FSMEngine.__new__(FSMEngine)
        engine.context = FSMContext.__new__(FSMContext)
        engine.context.pitch_dado = True  # Incluso con pitch_dado True

        calls = []
        engine._get_template = lambda k: calls.append(k) or f"T:{k}"

        t = Transition.__new__(Transition)
        t.action_type = ActionType.TEMPLATE
        t.template_key = "pitch_inicial"

        engine._execute(t, "Bueno")
        assert "pitch_inicial" in calls
        assert "pitch_encargado_corto" not in calls

    def test_pitch_persona_nueva_no_afectado(self):
        """pitch_persona_nueva no usa corto (solo pitch_encargado)."""
        from fsm_engine import FSMEngine, FSMContext, Transition, ActionType

        engine = FSMEngine.__new__(FSMEngine)
        engine.context = FSMContext.__new__(FSMContext)
        engine.context.pitch_dado = True

        calls = []
        engine._get_template = lambda k: calls.append(k) or f"T:{k}"

        t = Transition.__new__(Transition)
        t.action_type = ActionType.TEMPLATE
        t.template_key = "pitch_persona_nueva"

        engine._execute(t, "texto")
        assert "pitch_persona_nueva" in calls
        assert "pitch_encargado_corto" not in calls
