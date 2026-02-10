"""
Fixtures pytest para tests del Agente Bruce W.

Maneja el problema de inicialización a nivel de módulo:
agente_ventas.py crea clientes OpenAI y ElevenLabs al importar.
Se necesitan env vars dummy + mocks ANTES del import.
"""

import os
import sys
import json
import pytest
from unittest.mock import MagicMock, patch


# ============================================================
# SETUP: Env vars dummy ANTES de importar agente_ventas
# ============================================================
os.environ.setdefault("GITHUB_TOKEN", "test-github-token-dummy")
os.environ.setdefault("OPENAI_API_KEY", "test-openai-key-dummy")
os.environ.setdefault("ELEVENLABS_API_KEY", "test-elevenlabs-key-dummy")
os.environ.setdefault("ELEVENLABS_VOICE_ID", "test-voice-id-dummy")
os.environ.setdefault("USE_GITHUB_MODELS", "false")

# Directorio del proyecto
PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_DIR not in sys.path:
    sys.path.insert(0, PROJECT_DIR)


# ============================================================
# Mock de clientes externos ANTES del import
# ============================================================
_mock_openai_client = MagicMock()
_mock_elevenlabs_client = MagicMock()

# Patch a nivel de módulo para evitar conexiones reales
_patches = [
    patch("openai.OpenAI", return_value=_mock_openai_client),
    patch("elevenlabs.ElevenLabs", return_value=_mock_elevenlabs_client),
]

for p in _patches:
    p.start()

# Ahora sí importar agente_ventas (con clientes mockeados)
from agente_ventas import AgenteVentas, EstadoConversacion, EstadoEmail

# Detener patches después del import (ya se crearon los clientes dummy)
for p in _patches:
    p.stop()


# ============================================================
# FIXTURES
# ============================================================

@pytest.fixture
def agente():
    """AgenteVentas limpio sin contacto_info."""
    with patch("openai.OpenAI", return_value=_mock_openai_client), \
         patch("elevenlabs.ElevenLabs", return_value=_mock_elevenlabs_client):
        ag = AgenteVentas()
    ag.conversacion_iniciada = True
    return ag


@pytest.fixture
def agente_con_negocio():
    """AgenteVentas con datos de negocio (simula llamada real)."""
    contacto = {
        "nombre_negocio": "Materiales y Ferretería Test",
        "telefono": "+5216621234567",
        "ciudad": "Hermosillo",
        "fila": 42,
    }
    with patch("openai.OpenAI", return_value=_mock_openai_client), \
         patch("elevenlabs.ElevenLabs", return_value=_mock_elevenlabs_client):
        ag = AgenteVentas(contacto_info=contacto)
    ag.conversacion_iniciada = True
    return ag


@pytest.fixture
def agente_mid_conversation(agente):
    """Agente con historial de 2+ turnos (ya pasó el saludo)."""
    agente.conversation_history = [
        {"role": "assistant", "content": "Me comunico de la marca nioval, ¿se encontrará el encargado de compras?"},
        {"role": "user", "content": "No, no se encuentra ahorita."},
        {"role": "assistant", "content": "Entiendo. ¿Me podría proporcionar el WhatsApp del encargado?"},
    ]
    agente.estado_conversacion = EstadoConversacion.PIDIENDO_WHATSAPP
    agente.segunda_parte_saludo_dicha = True
    return agente


@pytest.fixture
def agente_pidiendo_correo(agente):
    """Agente en estado PIDIENDO_CORREO (ya pidió WhatsApp, no lo tienen)."""
    agente.conversation_history = [
        {"role": "assistant", "content": "¿Me podría proporcionar el WhatsApp del encargado?"},
        {"role": "user", "content": "No, no lo tengo."},
        {"role": "assistant", "content": "¿Me puede dar un correo electrónico?"},
    ]
    agente.estado_conversacion = EstadoConversacion.PIDIENDO_CORREO
    agente.segunda_parte_saludo_dicha = True
    return agente


@pytest.fixture
def agente_esperando_transferencia(agente):
    """Agente en estado ESPERANDO_TRANSFERENCIA (cliente dijo 'espéreme')."""
    agente.conversation_history = [
        {"role": "assistant", "content": "¿Se encontrará el encargado de compras?"},
        {"role": "user", "content": "Sí, espéreme tantito, se lo paso."},
        {"role": "assistant", "content": "Claro, espero."},
    ]
    agente.estado_conversacion = EstadoConversacion.ESPERANDO_TRANSFERENCIA
    agente.esperando_transferencia = True
    agente.segunda_parte_saludo_dicha = True
    return agente


@pytest.fixture
def agente_ofreciendo_contacto(agente):
    """Agente en estado OFRECIENDO_CONTACTO_BRUCE."""
    agente.conversation_history = [
        {"role": "assistant", "content": "¿Me podría proporcionar el WhatsApp del encargado?"},
        {"role": "user", "content": "No lo tengo."},
        {"role": "assistant", "content": "¿Le puedo dejar mi número para que me contacte el encargado?"},
    ]
    agente.estado_conversacion = EstadoConversacion.OFRECIENDO_CONTACTO_BRUCE
    agente.segunda_parte_saludo_dicha = True
    return agente


@pytest.fixture
def agente_dictando_numero(agente):
    """Agente en estado DICTANDO_NUMERO."""
    agente.conversation_history = [
        {"role": "assistant", "content": "¿Me puede dar el número de WhatsApp?"},
        {"role": "user", "content": "Sí, es 662"},
    ]
    agente.estado_conversacion = EstadoConversacion.DICTANDO_NUMERO
    agente.segunda_parte_saludo_dicha = True
    return agente


# ============================================================
# DATOS DE PRODUCCIÓN
# ============================================================

@pytest.fixture(scope="session")
def conversations():
    """Carga conversations.json generado por log_parser."""
    json_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "test_data", "conversations.json"
    )
    if not os.path.exists(json_path):
        pytest.skip("conversations.json no encontrado - ejecutar scripts/log_parser.py primero")
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data["conversations"]


@pytest.fixture(scope="session")
def conversations_with_patterns(conversations):
    """Solo conversaciones que tienen patrones detectados."""
    return {
        k: v for k, v in conversations.items()
        if v.get("patterns_detected")
    }


