# -*- coding: utf-8 -*-
"""
FIX 212: Integración de Deepgram para transcripción en tiempo real
Reemplaza Whisper para mejor precisión (90%+) y latencia (<100ms)
Actualizado: 2026-01-14

Arquitectura:
1. Twilio envía audio vía WebSocket (MediaStream)
2. Este módulo reenvía el audio a Deepgram
3. Deepgram devuelve transcripciones en tiempo real
4. Las transcripciones se pasan al agente de ventas
"""

import os
import json
import base64
import asyncio
from datetime import datetime
from collections import defaultdict

# Deepgram SDK
try:
    from deepgram import DeepgramClient, LiveTranscriptionEvents, LiveOptions
    DEEPGRAM_AVAILABLE = True
    print(" FIX 212: deepgram-sdk importado correctamente")
except ImportError as e:
    DEEPGRAM_AVAILABLE = False
    print(f" FIX 212: deepgram-sdk no instalado: {e}")
except Exception as e:
    DEEPGRAM_AVAILABLE = False
    print(f" FIX 212: Error importando deepgram-sdk: {type(e).__name__}: {e}")

# Configuración
DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY")

# Almacenamiento de transcripciones activas por CallSid
transcripciones_activas = {}
# Callbacks para cuando llega una transcripción
transcripcion_callbacks = {}


class DeepgramTranscriber:
    """
    FIX 212: Clase para manejar transcripción en tiempo real con Deepgram
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
        self.deepgram_client = None
        self.dg_connection = None
        self.is_connected = False
        self.transcript_buffer = ""
        self.final_transcripts = []
        self.start_time = datetime.now()

        # Métricas
        self.audio_chunks_received = 0
        self.transcripts_received = 0
        self.total_latency_ms = 0
        # FIX 501: Timestamp del último chunk de audio para medir latencia real
        self.last_audio_chunk_time = None

    async def connect(self):
        """Establece conexión con Deepgram"""
        if not DEEPGRAM_AVAILABLE:
            print(f" FIX 212: Deepgram SDK no disponible")
            return False

        if not DEEPGRAM_API_KEY:
            print(f" FIX 212: DEEPGRAM_API_KEY no configurada")
            return False

        try:
            self.deepgram_client = DeepgramClient(DEEPGRAM_API_KEY)

            # FIX 222/401/501: Configuración OPTIMIZADA para baja latencia
            # FIX 501: BRUCE1476 - Optimizaciones adicionales para reducir delay
            options = LiveOptions(
                model="nova-2",  # Modelo más preciso para español
                language="es-419",  # Español Latinoamérica
                encoding="mulaw",  # Formato de audio de Twilio
                sample_rate=8000,  # Frecuencia de Twilio
                channels=1,
                punctuate=True,  # Agregar puntuación
                interim_results=True,  # Resultados parciales para baja latencia
                # FIX 501: Ajustes para menor latencia en llamadas telefónicas
                endpointing=150,  # Reducido de 200ms a 150ms (más agresivo)
                smart_format=True,  # Formato inteligente
                # FIX 501: Nuevos parámetros para optimizar latencia
                no_delay=True,  # Procesar audio inmediatamente sin buffering
                # FIX 222: REMOVIDOS parámetros que pueden causar HTTP 400:
                # - utterance_end_ms (puede no estar soportado)
                # - vad_events (puede no estar soportado)
                # - filler_words (puede no estar soportado para es-419)
                # - numerals (puede no estar soportado para es-419)
            )

            # Crear conexión de streaming
            self.dg_connection = self.deepgram_client.listen.live.v("1")

            # Configurar handlers
            self.dg_connection.on(LiveTranscriptionEvents.Open, self._on_open)
            self.dg_connection.on(LiveTranscriptionEvents.Transcript, self._on_transcript)
            self.dg_connection.on(LiveTranscriptionEvents.Error, self._on_error)
            self.dg_connection.on(LiveTranscriptionEvents.Close, self._on_close)

            # FIX 222: Iniciar conexión con mejor manejo de errores
            print(f" FIX 222: Iniciando conexión Deepgram...")
            print(f"   Opciones: model={options.model}, language={options.language}, encoding={options.encoding}")

            result = self.dg_connection.start(options)
            if result:
                self.is_connected = True
                print(f" FIX 212: Deepgram conectado para CallSid: {self.call_sid}")
                return True
            else:
                print(f" FIX 222: Deepgram.start() retornó False")
                return False

        except Exception as e:
            import traceback
            print(f" FIX 222: Error conectando a Deepgram: {type(e).__name__}: {e}")
            traceback.print_exc()
            return False

    def _on_open(self, *args, **kwargs):
        """Callback cuando se abre la conexión"""
        print(f"🟢 FIX 212: Conexión Deepgram abierta - CallSid: {self.call_sid}")

    def _on_transcript(self, *args, **kwargs):
        """Callback cuando llega una transcripción"""
        try:
            # El resultado viene en kwargs o args dependiendo de la versión
            result = kwargs.get('result') or (args[1] if len(args) > 1 else None)

            if not result:
                return

            # Extraer transcripción
            channel = result.channel
            alternatives = channel.alternatives

            if not alternatives:
                return

            transcript = alternatives[0].transcript
            is_final = result.is_final
            speech_final = result.speech_final

            if not transcript:
                return

            self.transcripts_received += 1

            # FIX 501: Calcular latencia REAL desde el último chunk de audio
            # Antes: medía desde start_time (engañoso, podía mostrar 44s)
            # Ahora: mide desde el último audio enviado (latencia real de Deepgram)
            if self.last_audio_chunk_time:
                latency_ms = (datetime.now() - self.last_audio_chunk_time).total_seconds() * 1000
            else:
                latency_ms = (datetime.now() - self.start_time).total_seconds() * 1000

            if is_final:
                self.final_transcripts.append(transcript)
                self.transcript_buffer = ""  # Limpiar buffer al recibir final
                print(f" FIX 212: [FINAL] '{transcript}' (latencia: {latency_ms:.0f}ms)")

                # Llamar callback con transcripción final
                if self.on_transcript_callback:
                    self.on_transcript_callback(self.call_sid, transcript, True)
            else:
                self.transcript_buffer = transcript
                # FIX 218: Solo loguear parciales largos para reducir spam
                if len(transcript) > 10:
                    print(f" FIX 212: [PARCIAL] '{transcript}'")

                # FIX 218: Llamar callback con transcripción parcial para tener datos más rápido
                if self.on_transcript_callback and len(transcript) > 5:
                    self.on_transcript_callback(self.call_sid, transcript, False)

        except Exception as e:
            print(f" FIX 212: Error procesando transcripción: {e}")

    def _on_error(self, *args, **kwargs):
        """Callback cuando hay error"""
        error = kwargs.get('error') or (args[1] if len(args) > 1 else "Unknown")
        print(f" FIX 212: Error Deepgram - CallSid: {self.call_sid}: {error}")

    def _on_close(self, *args, **kwargs):
        """Callback cuando se cierra la conexión"""
        print(f" FIX 212: Conexión Deepgram cerrada - CallSid: {self.call_sid}")
        self.is_connected = False

    def send_audio(self, audio_data):
        """
        Envía chunk de audio a Deepgram

        Args:
            audio_data: bytes de audio (mulaw 8kHz)
        """
        if not self.is_connected or not self.dg_connection:
            return False

        try:
            self.dg_connection.send(audio_data)
            self.audio_chunks_received += 1
            # FIX 501: Registrar timestamp para medir latencia real
            self.last_audio_chunk_time = datetime.now()
            return True
        except Exception as e:
            print(f" FIX 212: Error enviando audio: {e}")
            return False

    def send_audio_base64(self, audio_base64):
        """
        Envía audio codificado en base64 (formato de Twilio MediaStream)

        Args:
            audio_base64: string base64 del audio
        """
        try:
            audio_bytes = base64.b64decode(audio_base64)
            return self.send_audio(audio_bytes)
        except Exception as e:
            print(f" FIX 212: Error decodificando audio base64: {e}")
            return False

    def get_transcript(self):
        """Obtiene la transcripción acumulada"""
        return " ".join(self.final_transcripts)

    def get_latest_transcript(self):
        """Obtiene la última transcripción final o el buffer parcial"""
        if self.final_transcripts:
            return self.final_transcripts[-1]
        return self.transcript_buffer

    async def close(self):
        """Cierra la conexión con Deepgram"""
        if self.dg_connection and self.is_connected:
            try:
                self.dg_connection.finish()
                print(f" FIX 212: Conexión Deepgram cerrada correctamente - CallSid: {self.call_sid}")
            except Exception as e:
                print(f" FIX 212: Error cerrando conexión Deepgram: {e}")
        self.is_connected = False

    def get_stats(self):
        """Obtiene estadísticas de la sesión"""
        return {
            "call_sid": self.call_sid,
            "audio_chunks": self.audio_chunks_received,
            "transcripts": self.transcripts_received,
            "final_transcripts": len(self.final_transcripts),
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
        DeepgramTranscriber o None si falla
    """
    if call_sid in transcripciones_activas:
        print(f" FIX 212: Ya existe transcriber para CallSid: {call_sid}")
        return transcripciones_activas[call_sid]

    transcriber = DeepgramTranscriber(call_sid, on_transcript_callback)
    transcripciones_activas[call_sid] = transcriber

    if on_transcript_callback:
        transcripcion_callbacks[call_sid] = on_transcript_callback

    return transcriber


def obtener_transcriber(call_sid):
    """Obtiene el transcriber activo para una llamada"""
    return transcripciones_activas.get(call_sid)


def eliminar_transcriber(call_sid):
    """Elimina y cierra el transcriber de una llamada"""
    if call_sid in transcripciones_activas:
        transcriber = transcripciones_activas.pop(call_sid)
        if call_sid in transcripcion_callbacks:
            del transcripcion_callbacks[call_sid]
        return transcriber
    return None


def verificar_configuracion():
    """Verifica que Deepgram esté configurado correctamente"""
    errores = []

    if not DEEPGRAM_AVAILABLE:
        errores.append("deepgram-sdk no instalado")

    if not DEEPGRAM_API_KEY:
        errores.append("DEEPGRAM_API_KEY no configurada")

    if errores:
        print(f" FIX 212: Errores de configuración Deepgram:")
        for error in errores:
            print(f"   - {error}")
        return False

    print(f" FIX 212: Deepgram configurado correctamente")
    print(f"   API Key: {DEEPGRAM_API_KEY[:10]}...{DEEPGRAM_API_KEY[-4:]}")
    return True


# Verificar configuración al importar
if __name__ != "__main__":
    print("\n FIX 212: Inicializando módulo Deepgram...")
    verificar_configuracion()
