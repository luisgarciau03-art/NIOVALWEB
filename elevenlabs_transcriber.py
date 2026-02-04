# -*- coding: utf-8 -*-
"""
FIX 540: Integración de ElevenLabs Scribe v2 Realtime para transcripción en tiempo real
Reemplaza/complementa Deepgram para mejor precisión en español (~5% WER vs 18%)
Fecha: 2026-02-03

Arquitectura:
1. Twilio envía audio vía WebSocket (MediaStream)
2. Este módulo reenvía el audio a ElevenLabs Scribe
3. ElevenLabs devuelve transcripciones en tiempo real (~150ms latencia)
4. Las transcripciones se pasan al agente de ventas

API Reference: https://elevenlabs.io/docs/api-reference/speech-to-text/v-1-speech-to-text-realtime
"""

import os
import json
import base64
import asyncio
import threading
import websocket
from datetime import datetime
from collections import defaultdict

# Configuración
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")

# WebSocket endpoint para Scribe v2 Realtime
# Formato: ulaw_8000 (mu-law 8kHz - formato de Twilio)
ELEVENLABS_STT_WS_URL = "wss://api.elevenlabs.io/v1/speech-to-text/realtime?audio_format=ulaw_8000"

# Almacenamiento de transcribers activos por CallSid
transcribers_activos = {}
# Callbacks para cuando llega una transcripción
transcripcion_callbacks = {}

# Verificar configuración
ELEVENLABS_STT_AVAILABLE = bool(ELEVENLABS_API_KEY)
if ELEVENLABS_STT_AVAILABLE:
    print(" FIX 540: ElevenLabs Scribe configurado y listo")
    print(f"   API Key: {ELEVENLABS_API_KEY[:10]}...{ELEVENLABS_API_KEY[-4:]}")
else:
    print(" FIX 540: ElevenLabs Scribe no configurado - ELEVENLABS_API_KEY no encontrada")


class ElevenLabsTranscriber:
    """
    FIX 540: Clase para manejar transcripción en tiempo real con ElevenLabs Scribe v2
    """

    def __init__(self, call_sid, on_transcript_callback=None):
        """
        Args:
            call_sid: ID de la llamada de Twilio
            on_transcript_callback: Función a llamar cuando llega transcripción
                                   callback(call_sid, texto, is_final)
        """
        self.call_sid = call_sid
        self.on_transcript_callback = on_transcript_callback
        self.ws = None
        self.is_connected = False
        self.transcript_buffer = ""
        self.final_transcripts = []
        self.start_time = datetime.now()
        self.ws_thread = None

        # Métricas
        self.audio_chunks_sent = 0
        self.transcripts_received = 0
        self.last_audio_chunk_time = None
        self.errors_count = 0

        # Control de reconexión
        self.should_reconnect = True
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = 3

    def connect(self):
        """Establece conexión WebSocket con ElevenLabs Scribe"""
        if not ELEVENLABS_STT_AVAILABLE:
            print(f" FIX 540: ElevenLabs API Key no configurada")
            return False

        try:
            print(f" FIX 540: Conectando a ElevenLabs Scribe para CallSid: {self.call_sid}")

            # Headers de autenticación
            headers = {
                "xi-api-key": ELEVENLABS_API_KEY
            }

            # Crear WebSocket con callbacks
            self.ws = websocket.WebSocketApp(
                ELEVENLABS_STT_WS_URL,
                header=headers,
                on_open=self._on_open,
                on_message=self._on_message,
                on_error=self._on_error,
                on_close=self._on_close
            )

            # Ejecutar WebSocket en thread separado
            self.ws_thread = threading.Thread(
                target=self._run_websocket,
                daemon=True
            )
            self.ws_thread.start()

            # Esperar a que se conecte (máximo 5 segundos)
            timeout = 5.0
            wait_interval = 0.1
            waited = 0
            while not self.is_connected and waited < timeout:
                import time
                time.sleep(wait_interval)
                waited += wait_interval

            if self.is_connected:
                print(f" FIX 540: ElevenLabs Scribe conectado para {self.call_sid}")
                return True
            else:
                print(f" FIX 540: Timeout conectando a ElevenLabs Scribe")
                return False

        except Exception as e:
            import traceback
            print(f" FIX 540: Error conectando a ElevenLabs Scribe: {type(e).__name__}: {e}")
            traceback.print_exc()
            return False

    def _run_websocket(self):
        """Ejecuta el WebSocket en loop"""
        try:
            self.ws.run_forever()
        except Exception as e:
            print(f" FIX 540: Error en WebSocket thread: {e}")

    def _on_open(self, ws):
        """Callback cuando se abre la conexión"""
        self.is_connected = True
        self.reconnect_attempts = 0
        print(f" FIX 540: Conexión ElevenLabs Scribe abierta - CallSid: {self.call_sid}")

    def _on_message(self, ws, message):
        """Callback cuando llega un mensaje"""
        try:
            data = json.loads(message)
            message_type = data.get("message_type", "")

            if message_type == "session_started":
                print(f" FIX 540: Sesión iniciada - modelo: {data.get('model_id', 'unknown')}")

            elif message_type == "partial_transcript":
                # Transcripción parcial (interim)
                text = data.get("text", "").strip()
                if text:
                    self.transcript_buffer = text
                    self.transcripts_received += 1

                    # Calcular latencia
                    if self.last_audio_chunk_time:
                        latency_ms = (datetime.now() - self.last_audio_chunk_time).total_seconds() * 1000
                    else:
                        latency_ms = 0

                    if len(text) > 10:
                        print(f" FIX 540: [PARCIAL] '{text}' (latencia: {latency_ms:.0f}ms)")

                    # Llamar callback con transcripción parcial
                    if self.on_transcript_callback and len(text) > 5:
                        self.on_transcript_callback(self.call_sid, text, False)

            elif message_type in ["committed_transcript", "committed_transcript_with_timestamps"]:
                # Transcripción final (committed)
                text = data.get("text", "").strip()
                if text:
                    self.final_transcripts.append(text)
                    self.transcript_buffer = ""
                    self.transcripts_received += 1

                    # Calcular latencia
                    if self.last_audio_chunk_time:
                        latency_ms = (datetime.now() - self.last_audio_chunk_time).total_seconds() * 1000
                    else:
                        latency_ms = 0

                    # Idioma detectado
                    language = data.get("language_code", "unknown")

                    print(f" FIX 540: [FINAL] '{text}' (latencia: {latency_ms:.0f}ms, idioma: {language})")

                    # Llamar callback con transcripción final
                    if self.on_transcript_callback:
                        self.on_transcript_callback(self.call_sid, text, True)

            elif message_type in ["error", "auth_error", "transcriber_error"]:
                error_msg = data.get("error", data.get("message", "Unknown error"))
                print(f" FIX 540: Error de ElevenLabs: {message_type} - {error_msg}")
                self.errors_count += 1

            elif message_type == "quota_exceeded":
                print(f" FIX 540: Cuota de ElevenLabs excedida")
                self.errors_count += 1

        except json.JSONDecodeError as e:
            print(f" FIX 540: Error parseando mensaje: {e}")
        except Exception as e:
            print(f" FIX 540: Error procesando mensaje: {e}")

    def _on_error(self, ws, error):
        """Callback cuando hay error"""
        print(f" FIX 540: Error WebSocket ElevenLabs - CallSid: {self.call_sid}: {error}")
        self.errors_count += 1

    def _on_close(self, ws, close_status_code, close_msg):
        """Callback cuando se cierra la conexión"""
        self.is_connected = False
        print(f" FIX 540: Conexión ElevenLabs cerrada - CallSid: {self.call_sid}")
        print(f"   Status: {close_status_code}, Mensaje: {close_msg}")

        # Intentar reconectar si es necesario
        if self.should_reconnect and self.reconnect_attempts < self.max_reconnect_attempts:
            self.reconnect_attempts += 1
            print(f" FIX 540: Intentando reconexión {self.reconnect_attempts}/{self.max_reconnect_attempts}")
            import time
            time.sleep(0.5)
            self.connect()

    def send_audio(self, audio_data):
        """
        Envía chunk de audio a ElevenLabs Scribe

        Args:
            audio_data: bytes de audio (mulaw 8kHz)
        """
        if not self.is_connected or not self.ws:
            return False

        try:
            # Codificar audio en base64
            audio_base64 = base64.b64encode(audio_data).decode('utf-8')

            # Crear mensaje según especificación de ElevenLabs
            message = {
                "message_type": "input_audio_chunk",
                "audio_base_64": audio_base64,
                "commit": False,  # VAD automático se encarga
                "sample_rate": 8000
            }

            self.ws.send(json.dumps(message))
            self.audio_chunks_sent += 1
            self.last_audio_chunk_time = datetime.now()
            return True

        except Exception as e:
            print(f" FIX 540: Error enviando audio: {e}")
            return False

    def send_audio_base64(self, audio_base64):
        """
        Envía audio ya codificado en base64 (formato de Twilio MediaStream)

        Args:
            audio_base64: string base64 del audio
        """
        try:
            # Crear mensaje según especificación de ElevenLabs
            message = {
                "message_type": "input_audio_chunk",
                "audio_base_64": audio_base64,
                "commit": False,
                "sample_rate": 8000
            }

            if self.is_connected and self.ws:
                self.ws.send(json.dumps(message))
                self.audio_chunks_sent += 1
                self.last_audio_chunk_time = datetime.now()
                return True
            return False

        except Exception as e:
            print(f" FIX 540: Error enviando audio base64: {e}")
            return False

    def commit(self):
        """Fuerza el commit de la transcripción actual"""
        if not self.is_connected or not self.ws:
            return False

        try:
            message = {
                "message_type": "input_audio_chunk",
                "audio_base_64": "",
                "commit": True,
                "sample_rate": 8000
            }
            self.ws.send(json.dumps(message))
            return True
        except Exception as e:
            print(f" FIX 540: Error en commit: {e}")
            return False

    def get_transcript(self):
        """Obtiene la transcripción acumulada"""
        return " ".join(self.final_transcripts)

    def get_latest_transcript(self):
        """Obtiene la última transcripción final o el buffer parcial"""
        if self.final_transcripts:
            return self.final_transcripts[-1]
        return self.transcript_buffer

    def close(self):
        """Cierra la conexión con ElevenLabs"""
        self.should_reconnect = False
        if self.ws:
            try:
                self.ws.close()
                print(f" FIX 540: Conexión ElevenLabs cerrada correctamente - CallSid: {self.call_sid}")
            except Exception as e:
                print(f" FIX 540: Error cerrando conexión: {e}")
        self.is_connected = False

    def get_stats(self):
        """Obtiene estadísticas de la sesión"""
        return {
            "call_sid": self.call_sid,
            "audio_chunks": self.audio_chunks_sent,
            "transcripts": self.transcripts_received,
            "final_transcripts": len(self.final_transcripts),
            "errors": self.errors_count,
            "duration_seconds": (datetime.now() - self.start_time).total_seconds()
        }


# Funciones de utilidad para usar desde servidor_llamadas.py

def crear_transcriber(call_sid, on_transcript_callback=None):
    """
    Crea un nuevo transcriber para una llamada

    Args:
        call_sid: ID de la llamada
        on_transcript_callback: Función callback(call_sid, texto, is_final)

    Returns:
        ElevenLabsTranscriber o None si falla
    """
    if call_sid in transcribers_activos:
        print(f" FIX 540: Ya existe transcriber ElevenLabs para CallSid: {call_sid}")
        return transcribers_activos[call_sid]

    transcriber = ElevenLabsTranscriber(call_sid, on_transcript_callback)
    transcribers_activos[call_sid] = transcriber

    if on_transcript_callback:
        transcripcion_callbacks[call_sid] = on_transcript_callback

    return transcriber


def obtener_transcriber(call_sid):
    """Obtiene el transcriber activo para una llamada"""
    return transcribers_activos.get(call_sid)


def eliminar_transcriber(call_sid):
    """Elimina y cierra el transcriber de una llamada"""
    if call_sid in transcribers_activos:
        transcriber = transcribers_activos.pop(call_sid)
        transcriber.close()
        if call_sid in transcripcion_callbacks:
            del transcripcion_callbacks[call_sid]
        return transcriber
    return None


def verificar_configuracion():
    """Verifica que ElevenLabs Scribe esté configurado correctamente"""
    errores = []

    if not ELEVENLABS_API_KEY:
        errores.append("ELEVENLABS_API_KEY no configurada")

    if errores:
        print(f" FIX 540: Errores de configuración ElevenLabs Scribe:")
        for error in errores:
            print(f"   - {error}")
        return False

    return True


# Verificar configuración al importar
if __name__ != "__main__":
    print("\n FIX 540: Inicializando módulo ElevenLabs Scribe...")
    verificar_configuracion()
