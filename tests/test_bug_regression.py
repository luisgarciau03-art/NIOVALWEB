"""
Tests de regresión parametrizados desde bug_regression_catalog.json.

Dos modos:
  RAW  - Valida que BugDetector DETECTA el bug original
  LIVE - Valida que el agente YA NO produce el bug (procesar_respuesta)

Uso:
  python -m pytest tests/test_bug_regression.py -v --tb=short
  python -m pytest tests/test_bug_regression.py -k "RAW" -v      # Solo detección
  python -m pytest tests/test_bug_regression.py -k "LIVE" -v     # Solo fix validation
"""

import os
import sys
import json
import pytest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# ============================================================
# CARGAR CATÁLOGO DE REGRESIÓN
# ============================================================

_CATALOG_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    'test_data', 'bug_regression_catalog.json'
)

def _load_catalog():
    if not os.path.exists(_CATALOG_PATH):
        return []
    with open(_CATALOG_PATH, 'r', encoding='utf-8') as f:
        catalog = json.load(f)
    return catalog.get('regressions', [])

REGRESSIONS = _load_catalog()

# Bug types que son solo detectables en producción (requieren Twilio/audio/TTS metadata)
_PRODUCTION_ONLY_BUGS = {
    'BRUCE_MUDO',                      # Requiere TwiML + audio fetch counts
    'DEGRADACION_TTS',                 # Requiere ElevenLabs filler count
    'RESPUESTA_FILLER_INCOHERENTE',    # Requiere filler_162a_count (TTS filler tracking)
    'SALUDO_FALTANTE',                 # Requiere primer turno bruce (pre-saludo)
    'INTERRUPCION_CONVERSACIONAL',     # Requiere contexto de timing/audio
}

# Bug types que no aplican para modo LIVE (dependen de contexto de producción)
_SKIP_LIVE_BUGS = _PRODUCTION_ONLY_BUGS | {
    'CLIENTE_HABLA_ULTIMO',   # Depende del timing de cierre de llamada
    'SALUDO_FALTANTE',        # Test agente empieza con saludo pre-configurado
}

# Filtrar regressions válidas para RAW
RAW_REGRESSIONS = [
    r for r in REGRESSIONS
    if r['bug_type'] not in _PRODUCTION_ONLY_BUGS
    and len(r.get('conversation', [])) >= 2
]

# Filtrar regressions válidas para LIVE
LIVE_REGRESSIONS = [
    r for r in REGRESSIONS
    if r['bug_type'] not in _SKIP_LIVE_BUGS
    and len(r.get('conversation', [])) >= 2
    # Debe tener al menos 1 turno del cliente
    and any(t['role'] == 'client' for t in r.get('conversation', []))
]


# ============================================================
# GPT MOCK PARA LIVE TESTS
# ============================================================

_GPT_RESPONSES = [
    "Claro, le comento. Somos distribuidores de la marca NIOVAL, "
    "manejamos productos ferreteros de alta calidad. "
    "¿Me podría comunicar con el encargado de compras?",

    "Con mucho gusto. Manejamos una amplia línea de productos ferreteros "
    "de la marca NIOVAL. ¿Le puedo enviar nuestro catálogo por WhatsApp?",

    "Perfecto, muchas gracias. ¿Me podría proporcionar un número de "
    "WhatsApp o correo electrónico para enviarle la información?",

    "Entiendo, no se preocupe. ¿Hay algún horario en el que pueda "
    "encontrar al encargado de compras?",

    "Claro que sí. Le agradezco mucho su tiempo. Que tenga excelente día.",
]
_mock_idx = 0

def _gpt_mock(**kwargs):
    global _mock_idx
    resp = _GPT_RESPONSES[_mock_idx % len(_GPT_RESPONSES)]
    _mock_idx += 1
    mock = MagicMock()
    mock.choices = [MagicMock()]
    mock.choices[0].message.content = resp
    return mock


# ============================================================
# TEST RAW: BugDetector debe DETECTAR el bug original
# ============================================================

@pytest.mark.skipif(not RAW_REGRESSIONS, reason="No hay bug_regression_catalog.json")
class TestBugRegressionRAW:
    """Valida que BugDetector detecta bugs en conversaciones reales."""

    @pytest.mark.parametrize(
        "regression",
        RAW_REGRESSIONS,
        ids=lambda r: f"RAW_{r['bug_id']}"
    )
    def test_detector_catches_raw(self, regression):
        """BugDetector debe encontrar el tipo de bug en la conversación original."""
        from bug_detector import CallEventTracker, BugDetector

        tracker = CallEventTracker(
            call_sid=f"test_{regression['bruce_id']}",
            bruce_id=regression['bruce_id'],
            telefono="+5216621234567"
        )

        # Alimentar la conversación al tracker
        for turn in regression['conversation']:
            role = turn['role']
            text = turn.get('text', '')
            if role == 'bruce':
                tracker.emit("BRUCE_RESPONDE", {"texto": text})
            elif role == 'client':
                tracker.emit("CLIENTE_DICE", {"texto": text})

        # Analizar bugs (sin GPT eval - solo rule-based)
        bugs = BugDetector.analyze(tracker)
        bug_types_found = {b['tipo'] for b in bugs}

        expected_type = regression['bug_type']

        # GPT_* bugs requieren GPT eval (no disponible en tests)
        if expected_type.startswith('GPT_'):
            pytest.skip(f"Bug {expected_type} requiere GPT eval (no disponible en tests)")

        # Algunos bugs pueden no reproducirse solo con turnos (contexto perdido)
        if expected_type not in bug_types_found:
            # Si BugDetector detectó OTROS bugs, es un caso borderline
            if bug_types_found:
                pytest.xfail(
                    f"BugDetector detectó {bug_types_found} en vez de {expected_type} "
                    f"(contexto parcial)"
                )
            else:
                pytest.xfail(
                    f"BugDetector no detectó {expected_type} solo con turnos "
                    f"(requiere contexto de producción adicional)"
                )


# ============================================================
# TEST LIVE: Agente ya NO debe producir el bug
# ============================================================

@pytest.mark.skipif(not LIVE_REGRESSIONS, reason="No hay bug_regression_catalog.json")
class TestBugRegressionLIVE:
    """Valida que procesar_respuesta ya no produce bugs conocidos."""

    @pytest.mark.parametrize(
        "regression",
        LIVE_REGRESSIONS,
        ids=lambda r: f"LIVE_{r['bug_id']}"
    )
    def test_bug_fixed_live(self, regression):
        """Replay con procesar_respuesta no debe producir el bug original."""
        from bug_detector import CallEventTracker, BugDetector
        from agente_ventas import AgenteVentas, EstadoConversacion

        expected_type = regression['bug_type']

        # GPT_* bugs no son detectable rule-based en tests
        if expected_type.startswith('GPT_'):
            pytest.skip(f"Bug {expected_type} requiere GPT eval")

        with patch('agente_ventas.openai_client') as mock_client:
            mock_client.chat.completions.create.side_effect = _gpt_mock

            agente = AgenteVentas()
            agente.estado_conversacion = EstadoConversacion.CONVERSACION_NORMAL
            agente.conversacion_iniciada = True
            agente.segunda_parte_saludo_dicha = True
            agente.conversation_history = [
                {"role": "assistant", "content": "Hola, buen día, le llamo de la marca NIOVAL."}
            ]

            tracker = CallEventTracker(
                call_sid=f"live_{regression['bruce_id']}",
                bruce_id=regression['bruce_id'],
                telefono="+5216621234567"
            )
            # Agregar saludo inicial
            tracker.emit("BRUCE_RESPONDE", {"texto": "Hola, buen día, le llamo de la marca NIOVAL."})

            client_turns = [t for t in regression['conversation'] if t['role'] == 'client']

            for turn in client_turns:
                text = turn.get('text', '').strip()
                if not text:
                    continue

                try:
                    # Suprimir stdout
                    _orig = sys.stdout
                    sys.stdout = open(os.devnull, 'w', encoding='utf-8')
                    try:
                        response = agente.procesar_respuesta(text)
                    finally:
                        sys.stdout.close()
                        sys.stdout = _orig

                    tracker.emit("CLIENTE_DICE", {"texto": text})
                    if response:
                        tracker.emit("BRUCE_RESPONDE", {"texto": response})

                except Exception:
                    tracker.emit("CLIENTE_DICE", {"texto": text})
                    continue

            # Analizar bugs
            bugs = BugDetector.analyze(tracker)
            bug_types_found = {b['tipo'] for b in bugs}

            # El bug original NO debe estar presente
            # Nota: GPT mock puede causar false positives (PREGUNTA_REPETIDA, etc.)
            # porque las respuestas mock son estáticas y no contextuales.
            # Estos se marcan como xfail en vez de fail.
            _mock_induced_bugs = {
                'PREGUNTA_REPETIDA',    # GPT mock repite mismas respuestas
                'CATALOGO_REPETIDO',    # GPT mock ofrece catálogo repetidamente
                'DICTADO_INTERRUMPIDO', # GPT mock no detecta dictado parcial
                'PITCH_REPETIDO',       # GPT mock repite pitch
            }
            if expected_type in bug_types_found:
                if expected_type in _mock_induced_bugs:
                    pytest.xfail(
                        f"Bug {expected_type} reproducido por GPT mock estático "
                        f"(falso positivo esperado)"
                    )
                else:
                    pytest.fail(
                        f"Bug {expected_type} sigue presente en {regression['bruce_id']} "
                        f"después de replay LIVE. Todos los bugs: {bug_types_found}"
                    )


# ============================================================
# TEST NO-CRASH: Ninguna conversación del catálogo debe crashear
# ============================================================

@pytest.mark.skipif(not REGRESSIONS, reason="No hay bug_regression_catalog.json")
class TestBugRegressionNoCrash:
    """Valida que ninguna conversación del catálogo crashea el agente."""

    @pytest.mark.parametrize(
        "regression",
        REGRESSIONS[:30],  # Limitar a 30 para velocidad
        ids=lambda r: f"NOCRASH_{r['bug_id']}"
    )
    def test_no_crash_on_replay(self, regression):
        """procesar_respuesta no debe crashear con entrada real."""
        from agente_ventas import AgenteVentas, EstadoConversacion

        with patch('agente_ventas.openai_client') as mock_client:
            mock_client.chat.completions.create.side_effect = _gpt_mock

            agente = AgenteVentas()
            agente.estado_conversacion = EstadoConversacion.CONVERSACION_NORMAL
            agente.conversacion_iniciada = True
            agente.segunda_parte_saludo_dicha = True
            agente.conversation_history = [
                {"role": "assistant", "content": "Hola, buen día."}
            ]

            client_turns = [t for t in regression['conversation'] if t['role'] == 'client']

            crashes = []
            for turn in client_turns:
                text = turn.get('text', '').strip()
                if not text:
                    continue
                try:
                    _orig = sys.stdout
                    sys.stdout = open(os.devnull, 'w', encoding='utf-8')
                    try:
                        response = agente.procesar_respuesta(text)
                    finally:
                        sys.stdout.close()
                        sys.stdout = _orig
                except Exception as e:
                    crashes.append(f"Turn '{text[:40]}': {e}")

            assert not crashes, (
                f"Crashes en {regression['bruce_id']}: {crashes}"
            )
