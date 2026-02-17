# -*- coding: utf-8 -*-
"""
FIX 700: Speech Processor - Máquina de Estados para Control de Speech

Problema: 6+ flags booleanos dispersos (pausa_intencional, cliente_sigue_hablando,
esperando_hora_callback, digitos_acumulados_flag, etc.) controlan el flujo de
speech/pause. Cuando se agrega un flag nuevo, fácilmente contradice otro
(FIX 529 vs FIX 244, FIX 577 vs FIX 620A).

Solución: State machine centralizada con transiciones explícitas.
Cada estado define qué acciones son válidas, eliminando contradicciones.

Arquitectura ADITIVA: Si este módulo falla, el código existente (flags) sigue funcionando.
"""

import re
import time
from enum import Enum


class SpeechState(Enum):
    """Estados posibles del flujo de speech."""
    IDLE = "idle"                          # Esperando input del cliente
    LISTENING = "listening"                # Recibiendo audio activamente
    DICTATING_PHONE = "dictating_phone"    # Cliente dictando teléfono (2-9 dígitos)
    DICTATING_EMAIL = "dictating_email"    # Cliente dictando email (arroba/gmail/etc)
    PARTIAL_INFO = "partial_info"          # Info parcial (termina en coma/conector)
    WAITING_CONTINUATION = "waiting"       # Esperando que cliente termine frase
    CLIENT_OFFERING_DATA = "offering"      # Cliente ofrece dato ("te paso su número")
    PROCESSING = "processing"              # GPT procesando respuesta
    RESPONDING = "responding"              # Bruce hablando (TTS activo)


class SpeechAction(Enum):
    """Acciones que puede tomar el sistema."""
    ACKNOWLEDGE = "acknowledge"    # Enviar "Ajá, sí." (FIX 696)
    WAIT = "wait"                  # Esperar más input (no enviar audio)
    PROCESS = "process"            # Enviar a GPT para procesar
    IGNORE = "ignore"              # Ignorar input (filler/ruido)


class SpeechStateMachine:
    """
    Máquina de estados para control centralizado de speech.
    Reemplaza flags dispersos con transiciones explícitas.
    """

    def __init__(self):
        self.state = SpeechState.IDLE
        self.previous_state = None
        self.partial_digits = ""
        self.partial_email = ""
        self.continuation_count = 0
        self.last_transition_time = time.time()
        self.waiting_for_hour = False

    def reset(self):
        """Reset para nueva llamada."""
        self.state = SpeechState.IDLE
        self.previous_state = None
        self.partial_digits = ""
        self.partial_email = ""
        self.continuation_count = 0
        self.last_transition_time = time.time()
        self.waiting_for_hour = False

    def process_input(self, texto, is_partial=False):
        """
        Procesa input de STT y retorna (nuevo_estado, accion_recomendada).

        Args:
            texto: Transcripción del cliente
            is_partial: True si es transcripción parcial (interim result)

        Returns:
            (SpeechState, SpeechAction): Nuevo estado y acción recomendada
        """
        if not texto or not texto.strip():
            return (self.state, SpeechAction.IGNORE)

        texto_lower = texto.lower().strip()
        texto_norm = self._normalize(texto_lower)

        # --- Transición 1: Detectar dictado de teléfono ---
        digitos = re.findall(r'\d', texto)
        if 2 <= len(digitos) < 10 and not self.waiting_for_hour:
            self._transition(SpeechState.DICTATING_PHONE)
            self.partial_digits = ''.join(digitos)
            return (self.state, SpeechAction.ACKNOWLEDGE)

        # Teléfono completo (10+ dígitos)
        if len(digitos) >= 10:
            self.partial_digits = ''.join(digitos)
            self._transition(SpeechState.IDLE)
            return (self.state, SpeechAction.PROCESS)

        # --- Transición 2: Detectar dictado de email ---
        email_keywords = ['arroba', '@', 'punto com', 'punto mx', 'punto net',
                          'gmail', 'hotmail', 'outlook', 'yahoo']
        deletreo_fonetico = re.search(r'\b[a-z] de [a-z]', texto_lower)
        if any(k in texto_lower for k in email_keywords) or deletreo_fonetico:
            self._transition(SpeechState.DICTATING_EMAIL)
            return (self.state, SpeechAction.ACKNOWLEDGE)

        # --- Transición 3: Info parcial (termina en conector) ---
        texto_stripped = texto.strip()

        # No aplicar a confirmaciones cortas (FIX 592)
        confirmaciones = {
            'si', 'no', 'bueno', 'claro', 'ok', 'aja', 'mhm',
            'si senor', 'no senor', 'si claro', 'bueno si',
            'si digame', 'si mande', 'mande', 'digame',
            'si bueno', 'buenos dias', 'buenas tardes'
        }
        # Normalizar: strip comas internas y trailing para comparar confirmaciones
        texto_limpio = re.sub(r'[,.\s]+$', '', texto_norm).strip()
        texto_limpio_sin_coma = re.sub(r',\s*', ' ', texto_limpio).strip()
        es_confirmacion = texto_limpio in confirmaciones or texto_limpio_sin_coma in confirmaciones

        if not es_confirmacion:
            # Coma final: siempre indica continuación
            if texto_stripped.endswith(','):
                self._transition(SpeechState.PARTIAL_INFO)
                self.continuation_count += 1
                return (self.state, SpeechAction.ACKNOWLEDGE)

            # Conectores como ÚLTIMA PALABRA (no substring)
            # Evita falso positivo: "teléfono" endswith "o" → NO es conector
            conectores_palabra = {'y', 'entonces', 'este', 'pues', 'o', 'pero', 'como', 'porque'}
            conectores_multi = {'o sea', 'es decir'}
            palabras = texto_stripped.split()
            ultima_palabra = palabras[-1].lower().rstrip('.,;:') if palabras else ''

            if ultima_palabra in conectores_palabra:
                self._transition(SpeechState.PARTIAL_INFO)
                self.continuation_count += 1
                return (self.state, SpeechAction.ACKNOWLEDGE)

            for cm in conectores_multi:
                if texto_norm.endswith(cm):
                    self._transition(SpeechState.PARTIAL_INFO)
                    self.continuation_count += 1
                    return (self.state, SpeechAction.ACKNOWLEDGE)

        # --- Transición 4: Cliente ofrece dato ---
        patrones_ofrece = [
            'te paso su', 'le paso su', 'te voy a dar', 'le voy a dar',
            'te puedo pasar', 'le puedo pasar', 'te doy el', 'le doy el',
            'aqui le va', 'ahi le va', 'apunte', 'anote'
        ]
        if any(p in texto_norm for p in patrones_ofrece):
            self._transition(SpeechState.CLIENT_OFFERING_DATA)
            return (self.state, SpeechAction.ACKNOWLEDGE)

        # --- Transición 5: Pregunta directa → responder ---
        preguntas_directas = [
            '?que quiere', '?que se le ofrece', '?de que se trata',
            '?que necesita', '?quien habla', '?de donde llama'
        ]
        if any(p in texto_norm for p in preguntas_directas) or '?' in texto:
            self._transition(SpeechState.IDLE)
            return (self.state, SpeechAction.PROCESS)

        # --- Transición 6: is_partial → esperar ---
        if is_partial:
            self._transition(SpeechState.WAITING_CONTINUATION)
            return (self.state, SpeechAction.WAIT)

        # --- Default: procesar normalmente ---
        self._transition(SpeechState.IDLE)
        return (self.state, SpeechAction.PROCESS)

    def get_acknowledgment(self):
        """
        Retorna acknowledgment apropiado según estado actual.
        Compatible con FIX 696.
        """
        if self.state in (SpeechState.DICTATING_PHONE,
                          SpeechState.DICTATING_EMAIL,
                          SpeechState.PARTIAL_INFO,
                          SpeechState.CLIENT_OFFERING_DATA):
            return "Ajá, sí."
        return None

    def should_wait(self):
        """Retorna True si debemos esperar más input del cliente."""
        return self.state in (
            SpeechState.DICTATING_PHONE,
            SpeechState.DICTATING_EMAIL,
            SpeechState.PARTIAL_INFO,
            SpeechState.WAITING_CONTINUATION,
            SpeechState.CLIENT_OFFERING_DATA
        )

    def should_process(self):
        """Retorna True si debemos enviar a GPT para procesar."""
        return self.state in (SpeechState.IDLE, SpeechState.LISTENING)

    def should_acknowledge(self):
        """Retorna True si debemos enviar acknowledgment corto."""
        return self.state in (
            SpeechState.DICTATING_PHONE,
            SpeechState.DICTATING_EMAIL,
            SpeechState.PARTIAL_INFO,
            SpeechState.CLIENT_OFFERING_DATA
        )

    def set_waiting_for_hour(self, value=True):
        """Marcar que Bruce preguntó por hora (FIX 526 compatible)."""
        self.waiting_for_hour = value

    def get_state_info(self):
        """Retorna info del estado actual para logging."""
        return {
            'state': self.state.value,
            'previous': self.previous_state.value if self.previous_state else None,
            'partial_digits': self.partial_digits,
            'continuation_count': self.continuation_count,
            'waiting_for_hour': self.waiting_for_hour,
            'time_in_state': round(time.time() - self.last_transition_time, 2)
        }

    def _transition(self, new_state):
        """Transición de estado con logging."""
        if new_state != self.state:
            self.previous_state = self.state
            self.state = new_state
            self.last_transition_time = time.time()

    def _normalize(self, texto):
        """Normaliza texto: lowercase + strip acentos."""
        texto = texto.lower().strip()
        for a, b in [('á', 'a'), ('é', 'e'), ('í', 'i'), ('ó', 'o'),
                      ('ú', 'u'), ('ü', 'u'), ('ñ', 'n')]:
            texto = texto.replace(a, b)
        return texto
