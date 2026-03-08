"""
Configuración centralizada del proyecto AgenteVentas
"""

import os
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# === APIs ===
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY", "")
ELEVENLABS_VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID", "pNInz6obpgDQGcFmaJgB")
DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY", "")

# === Twilio ===
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID", "")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN", "")
TWILIO_PHONE_NUMBER = os.getenv("TWILIO_PHONE_NUMBER", "")

# === Google Sheets ===
GOOGLE_CREDENTIALS_FILE = os.getenv(
    "GOOGLE_CREDENTIALS_FILE",
    "C:\\Users\\PC 1\\bubbly-subject-412101-c969f4a975c5.json"
)
SPREADSHEET_URL_CONTACTOS = os.getenv("SPREADSHEET_URL_CONTACTOS", "")
SPREADSHEET_URL_RESULTADOS = os.getenv("SPREADSHEET_URL_RESULTADOS", "")
SPREADSHEET_URL_LOGS = os.getenv("SPREADSHEET_URL_LOGS", "")

# === Modo de ejecución ===
USE_GITHUB_MODELS = os.getenv("USE_GITHUB_MODELS", "false").lower() == "true"
USE_DEEPGRAM = os.getenv("USE_DEEPGRAM", "true").lower() == "true"
DEBUG_MODE = os.getenv("DEBUG_MODE", "false").lower() == "true"

# === Rutas de archivos ===
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROMPTS_DIR = os.path.join(PROJECT_ROOT, "prompts")
AUDIO_CACHE_DIR = os.path.join(PROJECT_ROOT, "audio_cache")

# === Timeouts y límites ===
WHISPER_TIMEOUT = 5  # segundos
ELEVENLABS_TIMEOUT = 10  # segundos
MAX_CALL_DURATION = 300  # 5 minutos
SILENCE_TIMEOUT = 2  # segundos de silencio antes de cortar

# === Información de la empresa ===
EMPRESA_NOMBRE = "NIOVAL"
EMPRESA_TELEFONO = "662 415 1997"
EMPRESA_CIUDAD = "Guadalajara, Jalisco"


def get_openai_client():
    """Retorna cliente OpenAI configurado según el modo"""
    from openai import OpenAI

    if USE_GITHUB_MODELS:
        print("🔧 Modo: GitHub Models (Gratis - Para pruebas)")
        return OpenAI(
            base_url="https://models.inference.ai.azure.com",
            api_key=GITHUB_TOKEN
        )
    else:
        print("🚀 Modo: OpenAI Directo (Producción)")
        return OpenAI(api_key=OPENAI_API_KEY)


def get_elevenlabs_client():
    """Retorna cliente ElevenLabs configurado"""
    from elevenlabs import ElevenLabs
    return ElevenLabs(api_key=ELEVENLABS_API_KEY)


def get_twilio_client():
    """Retorna cliente Twilio configurado"""
    from twilio.rest import Client
    return Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
