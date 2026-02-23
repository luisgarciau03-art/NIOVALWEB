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

        # FIX 611: Logging de creación
        print(f" FIX 611: DeepgramTranscriber CREADO para CallSid: {self.call_sid}")

    async def connect(self):
        """Establece conexión con Deepgram"""
        # FIX 611: Logging detallado de inicio de conexión
        print(f" FIX 611: [CONECTANDO] CallSid: {self.call_sid}")

        if not DEEPGRAM_AVAILABLE:
            print(f" FIX 611: [ERROR] Deepgram SDK no disponible - CallSid: {self.call_sid}")
            return False

        if not DEEPGRAM_API_KEY:
            print(f" FIX 611: [ERROR] DEEPGRAM_API_KEY no configurada - CallSid: {self.call_sid}")
            return False

        try:
            # FIX 611: Logging de creación de cliente
            print(f" FIX 611: Creando DeepgramClient - CallSid: {self.call_sid}")
            self.deepgram_client = DeepgramClient(DEEPGRAM_API_KEY)
            print(f" FIX 611: DeepgramClient creado OK - CallSid: {self.call_sid}")

            # FIX 612: Configuración optimizada para llamadas telefónicas
            # Cambio: nova-2-phonecall → nova-2 (phonecall no disponible en plan actual)
            options = LiveOptions(
                model="nova-2",
                language="es",
                encoding="mulaw",
                sample_rate=8000,
                channels=1,
                punctuate=True,
                interim_results=True,
                endpointing=100,
                smart_format=False,
                no_delay=True,
            )

            # FIX 611: Logging de creación de conexión live
            print(f" FIX 611: Creando conexión live.v(1) - CallSid: {self.call_sid}")
            self.dg_connection = self.deepgram_client.listen.live.v("1")
            print(f" FIX 611: Conexión live creada OK - CallSid: {self.call_sid}")

            # Configurar handlers
            print(f" FIX 611: Configurando handlers (Open/Transcript/Error/Close) - CallSid: {self.call_sid}")
            self.dg_connection.on(LiveTranscriptionEvents.Open, self._on_open)
            self.dg_connection.on(LiveTranscriptionEvents.Transcript, self._on_transcript)
            self.dg_connection.on(LiveTranscriptionEvents.Error, self._on_error)
            self.dg_connection.on(LiveTranscriptionEvents.Close, self._on_close)
            print(f" FIX 611: Handlers configurados OK - CallSid: {self.call_sid}")

            # FIX 611: Iniciar conexión con logging detallado
            print(f" FIX 611: Llamando dg_connection.start() - CallSid: {self.call_sid}")
            print(f" FIX 611: Opciones: model={options.model}, language={options.language}, encoding={options.encoding}")

            result = self.dg_connection.start(options)

            # FIX 611: Logging de resultado
            print(f" FIX 611: dg_connection.start() retornó: {result} (type: {type(result)}) - CallSid: {self.call_sid}")

            if result:
                self.is_connected = True
                print(f" FIX 611: [CONECTADO] WebSocket Deepgram ACTIVO - CallSid: {self.call_sid}")
                return True
            else:
                print(f" FIX 611: [ERROR] dg_connection.start() retornó False - CallSid: {self.call_sid}")
                return False

        except Exception as e:
            import traceback
            print(f" FIX 611: [EXCEPCIÓN] Error conectando a Deepgram - CallSid: {self.call_sid}")
            print(f" FIX 611: Tipo: {type(e).__name__}, Mensaje: {e}")
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
                # FIX 610: Loguear cuando NO hay resultado
                print(f" FIX 610: [DEEPGRAM] Callback sin resultado (CallSid: {self.call_sid})")
                return

            # Extraer transcripción
            channel = result.channel
            alternatives = channel.alternatives

            if not alternatives:
                # FIX 610: Loguear cuando NO hay alternativas
                print(f" FIX 610: [DEEPGRAM] Sin alternativas (CallSid: {self.call_sid})")
                return

            transcript = alternatives[0].transcript
            is_final = result.is_final
            speech_final = result.speech_final
            confidence = alternatives[0].confidence if hasattr(alternatives[0], 'confidence') else None

            # FIX 501: Calcular latencia REAL desde el último chunk de audio
            if self.last_audio_chunk_time:
                latency_ms = (datetime.now() - self.last_audio_chunk_time).total_seconds() * 1000
            else:
                latency_ms = (datetime.now() - self.start_time).total_seconds() * 1000

            # FIX 610: LOGUEAR INCLUSO SI TRANSCRIPCIÓN ESTÁ VACÍA
            if not transcript or len(transcript.strip()) == 0:
                conf_str = f"{confidence:.2f}" if confidence else "N/A"
                print(f" FIX 610: [DEEPGRAM VACÍO] is_final={is_final}, speech_final={speech_final}, "
                      f"confidence={conf_str}, latencia={latency_ms:.0f}ms, "
                      f"audio_chunks={self.audio_chunks_received}")
                # FIX 610: Seguir procesando para registrar el evento
                # NO hacer return aquí - queremos ver estos eventos vacíos

            self.transcripts_received += 1

            if is_final:
                self.final_transcripts.append(transcript)
                self.transcript_buffer = ""  # Limpiar buffer al recibir final

                # FIX 610: Logging mejorado para FINAL
                if transcript and len(transcript.strip()) > 0:
                    conf_str_final = f"{confidence:.2f}" if confidence else "N/A"
                    print(f" FIX 212: [FINAL] '{transcript}' (latencia: {latency_ms:.0f}ms, confidence={conf_str_final})")
                else:
                    print(f" FIX 610: [FINAL VACÍO] latencia={latency_ms:.0f}ms, audio_chunks={self.audio_chunks_received}")

                # Llamar callback con transcripción final (incluso si está vacía)
                if self.on_transcript_callback:
                    self.on_transcript_callback(self.call_sid, transcript, True)
            else:
                self.transcript_buffer = transcript

                # FIX 610: Logging mejorado para PARCIAL
                if transcript and len(transcript) > 10:
                    print(f" FIX 212: [PARCIAL] '{transcript}' (latencia: {latency_ms:.0f}ms)")
                elif transcript and len(transcript) > 0:
                    print(f" FIX 610: [PARCIAL CORTO] '{transcript}' ({len(transcript)} chars, latencia: {latency_ms:.0f}ms)")

                # FIX 218: Llamar callback con transcripción parcial para tener datos más rápido
                if self.on_transcript_callback and len(transcript) > 5:
                    self.on_transcript_callback(self.call_sid, transcript, False)

        except Exception as e:
            import traceback
            print(f" FIX 610: Error procesando transcripción: {e}")
            traceback.print_exc()

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
        # FIX 611: Logging detallado de estado antes de enviar
        if not self.is_connected or not self.dg_connection:
            # FIX 611: Loguear SOLO la primera vez que falla (evitar spam)
            if self.audio_chunks_received == 0:
                print(f" FIX 611: [ERROR] NO PUEDO ENVIAR AUDIO - CallSid: {self.call_sid}")
                print(f" FIX 611:   is_connected={self.is_connected}, dg_connection={'EXISTS' if self.dg_connection else 'NULL'}")
            return False

        try:
            self.dg_connection.send(audio_data)
            self.audio_chunks_received += 1

            # FIX 611: Loguear primeros 3 chunks para confirmar que audio fluye
            if self.audio_chunks_received <= 3:
                print(f" FIX 611: [AUDIO ENVIADO] Chunk #{self.audio_chunks_received}, size={len(audio_data)} bytes - CallSid: {self.call_sid}")

            # FIX 501: Registrar timestamp para medir latencia real
            self.last_audio_chunk_time = datetime.now()
            return True
        except Exception as e:
            print(f" FIX 611: [EXCEPCIÓN] Error enviando audio chunk #{self.audio_chunks_received} - CallSid: {self.call_sid}: {e}")
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

    # FIX 536: Método para reconectar después de error
    async def reconnect(self):
        """
        FIX 536: Intenta reconectar a Deepgram después de un error de conexión
        Returns:
            bool: True si reconexión exitosa
        """
        print(f" FIX 536: Intentando reconectar Deepgram para CallSid: {self.call_sid}")

        # Cerrar conexión anterior si existe
        if self.dg_connection:
            try:
                self.dg_connection.finish()
            except:
                pass
            self.dg_connection = None
            self.is_connected = False

        # Esperar un momento antes de reconectar
        await asyncio.sleep(0.5)

        # Intentar reconectar
        try:
            result = await self.connect()
            if result:
                print(f" FIX 536: Reconexión exitosa para CallSid: {self.call_sid}")
                return True
            else:
                print(f" FIX 536: Reconexión fallida para CallSid: {self.call_sid}")
                return False
        except Exception as e:
            print(f" FIX 536: Error en reconexión: {e}")
            return False

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


# FIX 782: Guardar stats del transcriber antes de eliminar para diagnóstico
_transcriber_last_stats = {}


def obtener_last_stats(call_sid):
    """FIX 782: Obtiene stats guardadas del transcriber cerrado."""
    return _transcriber_last_stats.get(call_sid)


def eliminar_transcriber(call_sid):
    """Elimina y cierra el transcriber de una llamada"""
    if call_sid in transcripciones_activas:
        transcriber = transcripciones_activas.pop(call_sid)
        # FIX 782: Guardar stats antes de eliminar para diagnóstico posterior
        try:
            _transcriber_last_stats[call_sid] = transcriber.get_stats()
            # Limitar tamaño del cache de stats
            if len(_transcriber_last_stats) > 50:
                oldest = list(_transcriber_last_stats.keys())[0]
                del _transcriber_last_stats[oldest]
        except Exception:
            pass
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
