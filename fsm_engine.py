"""
fsm_engine.py - Motor de Estados Finitos Determinista para Bruce W.

Reemplaza GPT-4o free-form como motor de decisión primario.
FSM decide QUÉ hacer -> templates/narrow GPT generan el texto.

Modos (env FSM_ENABLED):
  - "shadow": Loguea decisiones sin interceptar (comparar vs GPT)
  - "active": Intercepta, GPT como fallback
  - "false":  Deshabilitado
"""
import os
import re
import json
import time
import unicodedata
from enum import Enum
from datetime import datetime
from difflib import SequenceMatcher
from dataclasses import dataclass, field
from typing import Optional, Dict, List, Tuple, Any

from response_templates import TEMPLATES, NARROW_PROMPTS
from llm_client import llm_client  # FIX 820: Usar Claude/OpenAI adapter

# ============================================================
# FSM_ENABLED mode
# ============================================================
FSM_ENABLED = os.getenv("FSM_ENABLED", "shadow").lower()


# ============================================================
# FIX 768: Caché adaptativo para respuestas GPT_NARROW
# ============================================================
class NarrowResponseCache:
    """FIX 768: Caché adaptativo que aprende de respuestas GPT_NARROW.

    Primera vez -> GPT responde, se almacena (count=1).
    Segunda vez (count >= MIN_HITS) -> respuesta cacheada (0ms, $0).
    Fuzzy matching para preguntas similares (SequenceMatcher >= 0.85).
    Persiste a JSON para sobrevivir restarts.
    """

    # FIX 831: Persistir en PERSISTENT_DIR (Railway Volume) para sobrevivir deploys
    _PERSISTENT_DIR = os.getenv("PERSISTENT_DIR", os.getenv("CACHE_DIR", "audio_cache"))
    CACHE_FILE = os.path.join(_PERSISTENT_DIR, "narrow_cache.json")
    MAX_ENTRIES = 500
    MIN_HITS = 2
    FUZZY_THRESHOLD = 0.85
    TTL_DAYS = 30

    def __init__(self):
        self._cache: Dict[str, dict] = {}
        self._store_count = 0
        self._load()

    @staticmethod
    def _normalize(texto: str) -> str:
        """Normaliza: lowercase, sin acentos, sin puntuación, espacios colapsados."""
        t = texto.lower().strip()
        t = unicodedata.normalize('NFD', t)
        t = ''.join(c for c in t if unicodedata.category(c) != 'Mn')
        t = re.sub(r'[^\w\s]', '', t)
        t = re.sub(r'\s+', ' ', t).strip()
        return t

    def _make_key(self, state: str, prompt_key: str, texto_norm: str) -> str:
        return f"{state}::{prompt_key}::{texto_norm}"

    def lookup(self, state: str, prompt_key: str, texto: str) -> Optional[str]:
        """Retorna respuesta cacheada si count >= MIN_HITS, None si miss."""
        texto_norm = self._normalize(texto)
        key = self._make_key(state, prompt_key, texto_norm)

        # 1. Exact match
        entry = self._cache.get(key)
        if entry:
            if entry["count"] >= self.MIN_HITS:
                entry["count"] += 1
                entry["last_seen"] = datetime.now().isoformat()
                print(f"  [FIX 768 CACHE HIT] key='{texto_norm[:40]}' count={entry['count']}")
                return entry["response"]
            # Exists but below threshold
            return None

        # 2. Fuzzy match
        prefix = f"{state}::{prompt_key}::"
        for cached_key, cached_entry in self._cache.items():
            if not cached_key.startswith(prefix):
                continue
            cached_text = cached_key[len(prefix):]
            if SequenceMatcher(None, texto_norm, cached_text).ratio() >= self.FUZZY_THRESHOLD:
                if cached_entry["count"] >= self.MIN_HITS:
                    cached_entry["count"] += 1
                    cached_entry["last_seen"] = datetime.now().isoformat()
                    print(f"  [FIX 768 CACHE FUZZY HIT] '{texto_norm[:30]}' ~ '{cached_text[:30]}' count={cached_entry['count']}")
                    return cached_entry["response"]
                # Below threshold but fuzzy matched -> increment existing
                cached_entry["count"] += 1
                cached_entry["last_seen"] = datetime.now().isoformat()
                if cached_entry["count"] >= self.MIN_HITS:
                    print(f"  [FIX 768 CACHE PROMOTED] '{cached_text[:40]}' count={cached_entry['count']}")
                return None

        return None

    def store(self, state: str, prompt_key: str, texto: str, response: str):
        """Almacena respuesta GPT_NARROW. No cachea vacías/cortas."""
        if not response or len(response.strip()) < 5:
            return

        texto_norm = self._normalize(texto)
        key = self._make_key(state, prompt_key, texto_norm)

        if key in self._cache:
            self._cache[key]["count"] += 1
            self._cache[key]["last_seen"] = datetime.now().isoformat()
        else:
            self._cache[key] = {
                "question_original": texto[:100],
                "response": response,
                "count": 1,
                "first_seen": datetime.now().isoformat(),
                "last_seen": datetime.now().isoformat(),
            }

        if len(self._cache) > self.MAX_ENTRIES:
            self._evict()

        self._store_count += 1
        if self._store_count % 5 == 0:
            self._save()

    def _evict(self):
        """Elimina entradas más viejas con count bajo."""
        sorted_entries = sorted(
            self._cache.items(),
            key=lambda x: (x[1]["count"], x[1]["last_seen"])
        )
        to_remove = len(self._cache) - int(self.MAX_ENTRIES * 0.8)
        for key, _ in sorted_entries[:max(to_remove, 1)]:
            del self._cache[key]

    def _load(self):
        try:
            if os.path.exists(self.CACHE_FILE):
                with open(self.CACHE_FILE, 'r', encoding='utf-8') as f:
                    self._cache = json.load(f)
                now = datetime.now()
                expired = []
                for k, v in self._cache.items():
                    try:
                        if (now - datetime.fromisoformat(v["last_seen"])).days > self.TTL_DAYS:
                            expired.append(k)
                    except (KeyError, ValueError):
                        expired.append(k)
                for k in expired:
                    del self._cache[k]
                if self._cache or expired:
                    print(f"  [FIX 768] Cache loaded: {len(self._cache)} entries ({len(expired)} expired) from {self.CACHE_FILE}")
        except Exception as e:
            print(f"  [FIX 768] Error loading cache: {e}")
            self._cache = {}

    def _save(self):
        try:
            with open(self.CACHE_FILE, 'w', encoding='utf-8') as f:
                json.dump(self._cache, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def stats(self) -> dict:
        total = len(self._cache)
        promoted = sum(1 for e in self._cache.values() if e["count"] >= self.MIN_HITS)
        total_hits = sum(e["count"] for e in self._cache.values() if e["count"] >= self.MIN_HITS)
        return {"total_entries": total, "promoted": promoted, "total_hits": total_hits}

    def flush(self):
        self._save()


narrow_cache = NarrowResponseCache()

# ============================================================
# FIX 761: FSM Phase 3 - Core flow activo
# ============================================================
# Comma-separated list of state names que interceptan GPT.
# Phase 2: "despedida,contacto_capturado"
# Phase 3: + buscando_encargado,encargado_presente,encargado_ausente,capturando_contacto
# Phase 4: + dictando_dato,ofreciendo_contacto,esperando_transferencia,saludo,pitch
# Rollback Phase 3: FSM_ACTIVE_STATES=despedida,contacto_capturado,buscando_encargado,encargado_presente,encargado_ausente,capturando_contacto
# Rollback Phase 2: FSM_ACTIVE_STATES=despedida,contacto_capturado
_ACTIVE_RAW = os.getenv("FSM_ACTIVE_STATES", "despedida,contacto_capturado,buscando_encargado,encargado_presente,encargado_ausente,capturando_contacto,dictando_dato,ofreciendo_contacto,esperando_transferencia,saludo,pitch").lower().strip()
FSM_ACTIVE_STATES_SET = set()  # Populated after FSMState defined


# ============================================================
# Estados FSM (12 estados explícitos)
# ============================================================
class FSMState(Enum):
    SALUDO = "saludo"
    PITCH = "pitch"
    BUSCANDO_ENCARGADO = "buscando_encargado"
    ENCARGADO_PRESENTE = "encargado_presente"
    ENCARGADO_AUSENTE = "encargado_ausente"
    ESPERANDO_TRANSFERENCIA = "esperando_transferencia"
    CAPTURANDO_CONTACTO = "capturando_contacto"
    DICTANDO_DATO = "dictando_dato"
    OFRECIENDO_CONTACTO = "ofreciendo_contacto"
    CONTACTO_CAPTURADO = "contacto_capturado"
    DESPEDIDA = "despedida"
    CONVERSACION_LIBRE = "conversacion_libre"


# Populate FSM_ACTIVE_STATES_SET now that FSMState is defined
_state_map = {s.value: s for s in FSMState}
for _name in _ACTIVE_RAW.split(','):
    _name = _name.strip()
    if _name and _name in _state_map:
        FSM_ACTIVE_STATES_SET.add(_state_map[_name])
if FSM_ACTIVE_STATES_SET:
    print(f"  [FSM] Active states (Phase 4): {[s.value for s in FSM_ACTIVE_STATES_SET]}")


# ============================================================
# Tipos de acción
# ============================================================
class ActionType(Enum):
    TEMPLATE = "template"         # Respuesta hardcoded (0ms, $0)
    GPT_NARROW = "gpt_narrow"     # GPT con prompt single-purpose (~500ms)
    ACKNOWLEDGE = "acknowledge"   # Acknowledgment formal con rotación (0ms, $0)
    HANGUP = "hangup"             # Señal para colgar
    NOOP = "noop"                 # Sin respuesta (esperar)


# ============================================================
# Intents reconocidos por FSM
# ============================================================
class FSMIntent(Enum):
    CONFIRMATION = "confirmation"
    INTEREST = "interest"
    NO_INTEREST = "no_interest"
    QUESTION = "question"
    IDENTITY = "identity"
    FAREWELL = "farewell"
    MANAGER_ABSENT = "manager_absent"
    MANAGER_PRESENT = "manager_present"
    TRANSFER = "transfer"
    CALLBACK = "callback"
    OFFER_DATA = "offer_data"
    REJECT_DATA = "reject_data"
    ANOTHER_BRANCH = "another_branch"
    CLOSED = "closed"
    DICTATING_PARTIAL = "dictating_partial"
    DICTATING_COMPLETE_PHONE = "dictating_complete_phone"
    DICTATING_COMPLETE_EMAIL = "dictating_complete_email"
    CONTINUATION = "continuation"
    VERIFICATION = "verification"
    WRONG_NUMBER = "wrong_number"  # FIX 744: Area equivocada / no tengo negocio
    IDENTITY_QUESTION = "identity_question"  # FIX 894: "de donde llama", "quien habla"
    WHAT_OFFER = "what_offer"  # FIX 894: "que deseaba", "que ofrece", "en que se le ofrece"
    UNKNOWN = "unknown"


# ============================================================
# Contexto FSM (reemplaza 40+ flags implícitos)
# ============================================================
@dataclass
class FSMContext:
    pitch_dado: bool = False
    encargado_preguntado: bool = False
    encargado_es_interlocutor: bool = False
    cliente_no_autorizado: bool = False

    canal_solicitado: Optional[str] = None
    canales_rechazados: List[str] = field(default_factory=list)
    canales_intentados: List[str] = field(default_factory=list)
    mismo_numero: bool = False

    datos_capturados: Dict[str, str] = field(default_factory=dict)
    datos_parciales: str = ""

    catalogo_ofrecido: bool = False
    catalogo_prometido: bool = False
    veces_ofrecio_catalogo: int = 0

    callback_pedido: bool = False
    callback_hora: Optional[str] = None
    callback_hora_preguntada: bool = False  # FIX 789B: ya preguntamos hora callback
    callback_confirmaciones: int = 0        # FIX 849: contador de confirmar_callback emitidos

    turnos_bruce: int = 0
    ultimo_template: Optional[str] = None
    preguntas_producto_respondidas: int = 0  # FIX 855: contador preguntas producto en capturando_contacto
    whatsapp_ya_solicitado: bool = False      # FIX 861: track si ya pedimos WhatsApp (evita PREGUNTA_REPETIDA FIX 856)

    tiempo_claro_espero: Optional[float] = None
    donde_anotar_preguntado: bool = False
    ultimo_fue_ofrecer_contacto: bool = False
    verificacion_consecutivas: int = 0  # FIX 866B: contador de verificacion_aqui_estoy consecutivos (anti-LOOP BRUCE2322)
    identity_repetidas: int = 0         # FIX 878: contador de identificacion_nioval consecutivos (anti-loop ubicacion)
    encargado_ausente_veces: int = 0    # FIX 892A: tracker para pedir_contacto_alternativo duplicado
    templates_usados: set = field(default_factory=set)  # FIX 907: templates ya dichos para evitar PREGUNTA_REPETIDA
    template_repeat_count: int = 0     # FIX 910: contador de repeticiones para detectar LOOP
    pedir_datos_count: int = 0         # FIX 909: contador de veces que Bruce pide datos (anti-LOOP)
    confusion_count: int = 0           # FIX 918: contador de turnos confusos del cliente
    ultima_respuesta_bruce: str = ""   # FIX 910: ultima respuesta para dedup
    pitch_turno: int = 0              # FIX 919: turno en que se dio el pitch
    encargado_identificado: bool = False  # FIX 1010: True cuando encargado ya se presentó (no solo "existe")


# ============================================================
# Transición FSM
# ============================================================
@dataclass
class Transition:
    next_state: FSMState
    action_type: ActionType
    template_key: Optional[str] = None
    guards: List[str] = field(default_factory=list)


# ============================================================
# Intent Classifier (rule-based, fast)
# ============================================================

# Números en español para detectar dictado
_NUMS_ESP = {
    'cero', 'uno', 'una', 'dos', 'tres', 'cuatro', 'cinco', 'seis', 'siete',
    'ocho', 'nueve', 'diez', 'once', 'doce', 'trece', 'catorce', 'quince',
    'dieciseis', 'diecisiete', 'dieciocho', 'diecinueve', 'veinte',
    'veintiuno', 'veintidos', 'veintitres', 'veinticuatro', 'veinticinco',
    'veintiseis', 'veintisiete', 'veintiocho', 'veintinueve', 'treinta',
    'cuarenta', 'cincuenta', 'sesenta', 'setenta', 'ochenta', 'noventa',
}


def _normalize(texto: str) -> str:
    """Normaliza texto: lowercase, strip acentos, strip puntuación."""
    t = texto.lower().strip()
    for a, b in [('á', 'a'), ('é', 'e'), ('í', 'i'), ('ó', 'o'), ('ú', 'u'),
                 ('ü', 'u'), ('ñ', 'n')]:
        t = t.replace(a, b)
    t = t.replace('¿', '').replace('?', '').replace('¡', '').replace('!', '')
    t = t.replace('.', '').replace(',', ' ').strip()
    t = re.sub(r'\s+', ' ', t)
    return t


def classify_intent(texto: str, context: FSMContext, state: FSMState) -> FSMIntent:
    """Clasifica intent del cliente con reglas deterministas."""
    tn = _normalize(texto)
    tl = texto.lower().strip()

    # --- Mid-sentence: texto termina en coma = cliente sigue hablando ---
    # FIX 821: REJECT_DATA tiene prioridad sobre CONTINUATION
    # BRUCE2538: "No tengo WhatsApp," -> era CONTINUATION por la coma, debe ser REJECT_DATA
    # FIX 889: MANAGER_ABSENT tiene prioridad sobre CONTINUATION
    # BRUCE2596: "No se encuentra en este momento," -> era CONTINUATION, debe ser MANAGER_ABSENT
    _reject_quick_821 = ['no tengo', 'no puedo', 'tampoco tengo', 'solo tengo',
                          'no manejo', 'no uso', 'no le puedo', 'no te puedo']
    # FIX 926: Expandido con "no hay nadie", "andan fueras", "no nos puede atender"
    _manager_absent_quick_889 = ['no se encuentra', 'no esta', 'salio', 'salieron',
                                  'no vino', 'no llego', 'no viene', 'esta en su hora',
                                  'hora de comida', 'fueron a comer', 'anda fuera', 'andan fuera',
                                  'no hay nadie', 'no hay quien', 'no nos puede atender',
                                  'no puede atender', 'nadie que atienda', 'no atiende']
    if tl.endswith(',') and len(tn) < 40:
        if any(m in tn for m in _manager_absent_quick_889):
            # FIX 930: BRUCE2550 - En SALUDO, "No, no está," con coma = cliente sigue hablando
            # No interrumpir, dejar que termine de hablar (ej: "No, no está, tendría que llamar más tarde")
            if state == FSMState.SALUDO:
                return FSMIntent.CONTINUATION
            pass  # FIX 889: fall through — será clasificado como MANAGER_ABSENT más abajo
        elif not any(r in tn for r in _reject_quick_821):
            return FSMIntent.CONTINUATION
        # else: fall through — será clasificado como REJECT_DATA más abajo

    # --- FIX 783: Despedida ANTES de dictado (BRUCE2494 P0) ---
    # "No una disculpa... hasta luego" tiene num_words=2 ("no","una") -> DICTATING_PARTIAL
    # Farewell debe chequearse ANTES de conteo numérico para evitar malclasificación
    # NOTA: NO incluir "buenas tardes/noches/buen dia" aquí - son saludos ambiguos
    farewell_strong_783 = ['hasta luego', 'adios', 'bye', 'nos vemos', 'que le vaya bien',
                           'hasta pronto',
                           # FIX 994: Despedidas coloquiales mexicanas (que + vaya/este/tenga)
                           # DEBEN estar ANTES del question_markers check ('que' → QUESTION)
                           'que le vaya bonito', 'que este bien', 'que tenga buen dia',
                           'que tenga buenas tardes', 'que tenga buenas noches',
                           'que le vaya muy bien', 'que le vaya bonita', 'que les vaya bien',
                           'con permiso', 'con su permiso',
                           ]
    farewell_weak_783 = ['gracias', 'muchas gracias', 'ok gracias']
    if any(f in tn for f in farewell_strong_783):
        return FSMIntent.FAREWELL
    if any(f == tn for f in farewell_weak_783):  # exact match only
        return FSMIntent.FAREWELL

    # --- FIX 781: Email completo ANTES de dictado (email con números no es dictado parcial) ---
    # BRUCE2472: "Ferrebillas seis cuatro arroba gmail punto com" tiene num_words=4
    # Sin este check, se clasifica como DICTATING_PARTIAL y nunca llega a email detection
    # FIX 939: Requerir sufijo de dominio ("punto com/mx/net") para declarar email COMPLETO
    # Antes: 'arroba' + 'gmail' era suficiente → "arroba gmail" (incompleto) → COMPLETE_EMAIL
    # Después: se requiere también el sufijo para evitar confirmación prematura
    _email_providers_939 = ['gmail', 'hotmail', 'yahoo', 'outlook', 'prodigy']
    _email_suffixes_939 = ['punto com', 'punto net', 'punto mx', 'punto org']
    _has_literal_email_939 = '@' in texto and '.' in (texto.split('@')[-1] if '@' in texto else '')
    _has_voiced_email_939 = (
        'arroba' in tn and
        any(p in tn for p in _email_providers_939) and
        any(s in tn for s in _email_suffixes_939)
    )
    if _has_literal_email_939 or _has_voiced_email_939:
        return FSMIntent.DICTATING_COMPLETE_EMAIL

    # FIX 939B: En DICTANDO_DATO, "punto com/mx/net" = parte final del correo
    # que ya se estaba dictando → clasificar como COMPLETO para confirmar el correo
    _email_final_parts_939 = ['punto com', 'punto net', 'punto mx', 'punto org']
    if state == FSMState.DICTANDO_DATO and any(s in tn for s in _email_final_parts_939):
        return FSMIntent.DICTATING_COMPLETE_EMAIL

    # --- FIX 781: Email parcial ANTES de dictado ---
    email_signals = ['arroba', 'gmail', 'hotmail', 'outlook', 'yahoo', 'punto com', 'punto mx']
    if any(s in tn for s in email_signals):
        return FSMIntent.OFFER_DATA

    # --- Dictado: dígitos numéricos ---
    digits = re.findall(r'\d', texto)
    # FIX 907: Compound number words (veintinueve, treinta, cuarenta) represent 2 digits
    # "tres tres doce treinta cuarenta cero uno veintinueve" = 10 digits, not 8 words
    _COMPOUND_2DIGIT = {
        'diez', 'once', 'doce', 'trece', 'catorce', 'quince',
        'dieciseis', 'diecisiete', 'dieciocho', 'diecinueve', 'veinte',
        'veintiuno', 'veintidos', 'veintitres', 'veinticuatro', 'veinticinco',
        'veintiseis', 'veintisiete', 'veintiocho', 'veintinueve',
        'treinta', 'cuarenta', 'cincuenta', 'sesenta', 'setenta', 'ochenta', 'noventa',
    }
    num_words = 0
    for w in tn.split():
        if w in _COMPOUND_2DIGIT:
            num_words += 2  # These represent 2 digits each
        elif w in _NUMS_ESP:
            num_words += 1  # Single digit words (cero-nueve)

    # FIX 780: Excluir frases con contexto temporal de dictado parcial
    # BRUCE2468: "llegan en una hora" -> "una" × 2 = num_words=2 -> falso DICTATING_PARTIAL
    # Palabras temporales junto a números no son dictado de teléfono
    # FIX 931: Agregado 'las' para "marca a las 4:00" (BRUCE2540)
    _time_context = {'hora', 'horas', 'rato', 'minuto', 'minutos', 'momento', 'dia', 'dias',
                     'semana', 'semanas', 'mes', 'meses', 'tarde', 'manana', 'noche',
                     'las', 'marca', 'marcar', 'llamar', 'llamame', 'marcame'}
    words = set(tn.split())
    has_time_context = bool(words & _time_context)

    # FIX 973: Detectar área code implícita cuando cliente dice "de Guadalajara/CDMX/etc."
    # "El 1754 7880 de Guadalajara" = 8 dígitos + ciudad → 8+2=10 → COMPLETE_PHONE
    _ciudad_area_973 = {
        'guadalajara', 'guad', 'cdmx', 'ciudad de mexico', 'monterrey', 'mty',
        'puebla', 'cancun', 'queretaro', 'leon', 'tijuana', 'hermosillo',
        'culiacan', 'mexicali', 'merida', 'chihuahua', 'saltillo', 'toluca',
        'aqui', 'local', 'este', 'celaya', 'aguascalientes',
    }
    _tiene_ciudad_973 = any(c in tn for c in _ciudad_area_973)
    _effective_digits = len(digits) + num_words + (2 if _tiene_ciudad_973 and len(digits) >= 6 else 0)

    # FIX 1018: "número extensión X" → strip extension digits, validate remaining 10
    # "El 3312190020 extensión 5" = 11 digits raw but phone is just 3312190020 (10)
    _extension_stripped_1018 = False
    if 'extension' in tn or 'ext' in tn.split():
        import re as _re1018
        _tn_no_ext = _re1018.sub(r'\bext(?:ension)?\s*\d+', '', tn).strip()
        _digits_no_ext = _re1018.findall(r'\d', _tn_no_ext)
        if len(_digits_no_ext) >= 10:
            # Valid 10-digit number without extension → treat as complete phone
            print(f"  [FIX 1018] Extension stripped → {len(_digits_no_ext)} dígitos válidos")
            _extension_stripped_1018 = True
            digits = _digits_no_ext  # Use stripped digits for further checks
            _effective_digits = len(_digits_no_ext)

    # OOS-16-19: "Llame al número principal de la empresa + digits" = CALLBACK, not capture
    _callback_num_principal = any(p in tn for p in [
        'numero principal', 'numero de la empresa', 'numero del negocio',
        'llame al numero', 'llame mejor al', 'mejor llame al',
        'llamen al numero', 'marque al numero principal',
    ])

    if _effective_digits >= 10 or len(digits) >= 10:
        # FIX 780: 10+ dígitos con contexto temporal en BUSCANDO_ENCARGADO = callback, no teléfono
        if has_time_context and state == FSMState.BUSCANDO_ENCARGADO:
            pass  # Fall through to callback/other classifiers
        # OOS-16-19: "numero principal de la empresa" + digits = callback request
        elif _callback_num_principal:
            # FIX 1050: In CAPTURANDO_CONTACTO, "numero principal + digits" = client giving contact
            if state in (FSMState.CAPTURANDO_CONTACTO, FSMState.DICTANDO_DATO):
                return FSMIntent.DICTATING_COMPLETE_PHONE
            pass  # Fall through to callback classifiers for other states
        else:
            return FSMIntent.DICTATING_COMPLETE_PHONE
    if len(digits) >= 2 or num_words >= 2:
        # FIX 780+820+823: Con contexto temporal, no es dictado parcial (es info de disponibilidad)
        # FIX 820: Agregado ENCARGADO_AUSENTE (BRUCE2534: "por la tarde a las 4" era dictating_partial)
        # FIX 823: Agregado DICTANDO_DATO (BRUCE2541: "marca a las cuatro" era dictating_partial)
        if has_time_context and state in (FSMState.BUSCANDO_ENCARGADO, FSMState.PITCH,
                                          FSMState.ENCARGADO_PRESENTE, FSMState.ENCARGADO_AUSENTE,
                                          FSMState.DICTANDO_DATO):
            pass  # Fall through to callback/other classifiers
        else:
            # FIX 754+787: Detectar dictado parcial en más estados
            if state in (FSMState.DICTANDO_DATO, FSMState.CAPTURANDO_CONTACTO,
                         FSMState.ENCARGADO_PRESENTE, FSMState.ENCARGADO_AUSENTE,
                         FSMState.BUSCANDO_ENCARGADO, FSMState.PITCH,
                         FSMState.OFRECIENDO_CONTACTO, FSMState.ESPERANDO_TRANSFERENCIA):
                return FSMIntent.DICTATING_PARTIAL

    # --- Despedida ya chequeada arriba por FIX 783 (movida antes de dictado) ---

    # --- FIX 744: Area equivocada / número incorrecto ---
    wrong_number = [
        'esta equivocado', 'estas equivocado', 'usted esta equivocado',
        'numero equivocado', 'se equivoco de numero', 'se equivoco de telefono',
        'no tengo negocio', 'no tenemos negocio', 'yo no tengo negocio',
        'aqui no hay negocio', 'no es aqui', 'aqui no es',
        'area equivocada', 'departamento equivocado',
        'no es conmigo', ' no soy yo', 'no, no soy yo', 'no es mi departamento',
        'marco equivocado', 'llamo equivocado', 'marque equivocado',
        # FIX 994: Casa particular / domicilio privado
        'casa particular', 'domicilio particular', 'numero de casa', 'es mi casa',
        'aqui es casa', 'esto es casa', 'soy particular', 'es residencial',
        # FIX 998: "este no es el número correcto"
        'este no es el numero correcto', 'no es el numero correcto',
        'no es el numero', 'numero incorrecto',
        # FIX 1003: Número personal / domicilio privado (riesgo reputacional)
        'numero personal', 'es un numero personal', 'es numero personal',
        'somos familia', 'es mi familia', 'hablan con un particular',
        'numero domestico', 'linea personal', 'telefono personal',
        'este es un celular personal', 'es celular personal',
        # FIX 908: Giro equivocado - negocio no es ferreteria
        'aqui es un restaurante', 'somos restaurante', 'es un restaurante',
        'aqui es una tienda de', 'somos tienda de abarrotes', 'vendemos abarrotes',
        'puras cosas de abarrotes', 'nada de ferreteria',
        'aqui no vendemos ferreteria', 'no vendemos ferreteria',
        'aqui es una farmacia', 'somos farmacia', 'es una farmacia',
        'aqui es una papeleria', 'somos papeleria', 'es una papeleria',
        'aqui es una carniceria', 'somos carniceria',
        'aqui es una verduleria', 'aqui vendemos comida',
        'no es ferreteria esto', 'esto no es ferreteria',
        'aqui no manejamos nada de eso', 'no es nuestro giro',
        # FIX 1012: Taller mecánico / giro diferente → negocio no aplica
        'somos taller mecanico', 'somos un taller mecanico', 'somos taller',
        'somos un taller', 'somos mecanicos', 'somos un taller de',
        'somos consultorio', 'somos clinica', 'somos salon de belleza',
        'somos peluqueria', 'somos panaderia', 'somos negocio de otro giro',
        'aqui es un taller mecanico', 'esto es un taller',
    ]
    if any(w in tn for w in wrong_number):
        return FSMIntent.WRONG_NUMBER

    # --- No interés / rechazo definitivo ---
    no_interest = [
        'no me interesa', 'no nos interesa', 'no gracias', 'no estamos interesados',
        'no hacemos compras', 'no hacemos compra', 'no hacemos ningun tipo de compra',  # FIX 865: singular + variantes (BRUCE2255)
        'no compramos', 'no ocupamos', 'no necesitamos',
        'no manejamos eso', 'aqui es un taller', 'no es ferreteria',
        'no joven', 'no muchacho', 'no senor', 'no senorita', 'no mijo',
        # FIX 854: "ya tengo proveedores" variantes (sincronizado con IntentClassifier FIX 844/850)
        # BRUCE2539: 'ya tengo unos proveedores' no detectado → Bruce re-preguntaba encargado
        'ya tengo proveedor', 'ya tengo proveedores',
        'ya tengo unos proveedores', 'ya tengo varios proveedores',
        'ya tenemos proveedor', 'ya tenemos proveedores',
        'ya tenemos unos proveedores', 'ya tenemos varios proveedores',
        'tengo mis proveedores', 'tenemos nuestros proveedores',
        'contamos con proveedores', 'ya contamos con proveedor',
        # FIX 938: OOS audit V2 - rechazos firmes no detectados como NO_INTEREST
        'estamos bien', 'estamos bien con lo que tenemos', 'estamos bien surtidos',
        'esta bien como estamos', 'estamos bien asi', 'estamos bien gracias',
        'no muchas gracias', 'no gracias ya', 'no necesito nada',
        'no necesitamos nada', 'no nos hace falta',
        # FIX 969: Slang mexicano hostil/agresivo → NO_INTEREST (FIX 950 también lo captura)
        'dejen de fregar', 'dejame de fregar', 'ya no frieguen', 'no frieguen',
        'dejen de chingar', 'no chinguen', 'dejame en paz', 'dejenos en paz',
        'no quiero nada', 'ya vayanse', 'ya largense',
        # FIX 990: Variantes de no interés
        'no estoy interesado', 'no estoy interesada', 'no estamos interesados en eso',
        'no tenemos interes', 'no hay interes', 'no aplica para nosotros',
        'no aplica', 'no es para nosotros', 'no trabajamos con eso',
        # FIX 997: "no manejo eso" = no aplica para el negocio → NO_INTEREST
        'es que no manejo eso', 'no manejamos eso', 'no es nuestro giro',
        'no aplica en nuestro giro', 'no trabajamos con eso',
        # FIX 992: Peticiones de no llamar más = rechazo definitivo
        'no nos llame', 'ya no nos llame', 'ya no marque', 'no marque mas',
        'no llame mas', 'ya no llame', 'no vuelva a llamar', 'no vuelva a marcar',
        'borrenos de su lista', 'quitenos de su lista', 'borreme de su lista',
        # FIX 993: Ya tienen otro proveedor/distribuidor
        'trabajamos con otro proveedor', 'tenemos otro proveedor',
        'trabajamos con alguien mas', 'ya trabajamos con alguien',
        'tenemos ya distribuidor', 'tenemos distribuidor', 'tenemos proveedor fijo',
        'ya tenemos a alguien', 'ya tenemos quien nos surta',
        # FIX 1000: Rechazos formales/educados que contienen 'no esta' como substring FP
        # IMPORTANTE: Deben estar ANTES del manager_absent check (que matchea 'no esta' en 'no estamos')
        'no estamos en posicion', 'no estamos considerando', 'no consideramos necesario',
        'no es de nuestro interes', 'no es de nuestro interés',
        'estamos satisfechos con nuestros proveedores', 'contamos con todo lo necesario',
        'por el momento contamos con', 'estamos bien cubiertos', 'no necesitamos cambiar',
        # FIX 1047: Encargado no atiende llamadas de vendedores/proveedores → NO_INTEREST
        'no atiende llamadas de vendedores', 'no atiende llamadas de ventas',
        'no atiende a proveedores', 'no atiende proveedores', 'no atiende vendedores',
        'no recibimos vendedores', 'no recibimos llamadas de ventas',
        'no recibimos llamadas de proveedores', 'no atiende a vendedores',
        'el encargado no atiende', 'la encargada no atiende',
        'no tenemos autorizacion para compras', 'no tenemos presupuesto para compras',
    ]
    if any(n in tn for n in no_interest):
        # FIX 1014c: "ya tengo proveedor, en que son mejores?" = competitive inquiry
        # Don't farewell — answer the differentiation question
        _competitiva_1014 = any(q in tn for q in [
            'en que son mejores', 'en que se diferencian', 'en que son diferentes',
            'que ventaja', 'que diferencia', 'como se comparan', 'que los hace',
            'por que deberia', 'que ofrecen de mas', 'en que mejoran',
        ])
        if _competitiva_1014:
            return FSMIntent.QUESTION
        return FSMIntent.NO_INTEREST

    # --- Rechazo de dato específico ---
    # FIX 820: Expandido con patrones de BRUCE2533/2535
    reject_data = [
        'no tengo whatsapp', 'no tengo correo', 'no tengo email',
        'no tengo telefono', 'no tengo celular', 'no tengo fijo',
        'no lo puedo dar', 'no se lo puedo dar', 'no lo podemos pasar',
        'no le puedo dar', 'no le puedo pasar', 'no le podemos dar',
        'solo tengo telefono', 'solo tengo celular', 'no manejo correo',
        'no te lo puedo dar', 'no puedo darte', 'no estoy autorizado',
        'tampoco tengo', 'no cuento con',
        # FIX 820: Patrones faltantes detectados en BRUCE2533/2535
        'no te puedo pasar', 'no puedo proporcionar', 'no le puedo proporcionar',
        'no te puedo proporcionar', 'no uso whatsapp', 'no manejo whatsapp',
        'no tengo de eso', 'no puedo pasar informacion', 'no puedo dar informacion',
        'no te puedo pasar informacion', 'no le puedo pasar informacion',
        # FIX 895: BRUCE2582 - "no me sé el WhatsApp" / "no conozco" no matcheaba
        'no se el whatsapp', 'no me se el whatsapp', 'no se el correo',
        'no me se el correo', 'no se el numero', 'no me se el numero',
        'no conozco el whatsapp', 'no conozco el correo', 'no conozco el numero',
        'no se el dato', 'no me se', 'no lo se', 'no se cual es', 'yo no se',
        # FIX 909: Rechazo indirecto de canal (auditoria Claude: DATO_NEGADO_REINSISTIDO)
        'no tengo datos', 'no tengo datos en el celular', 'no me llegan los whats',
        'no lo uso', 'no lo usamos', 'no usa whatsapp', 'no usa correo',
        'no lo manejo', 'no lo manejamos', 'no usamos whatsapp', 'no usamos correo',
        'es de la vieja escuela', 'no sabe de eso', 'no le sabe a eso',
        'no tiene whatsapp', 'no tiene correo', 'no tiene celular',
        'no tiene de eso', 'el patron no usa', 'el dueno no usa',
        'no reviso correos', 'no revisa correos', 'no checa correos',
        'no checo correos', 'nunca revisa', 'no le llegan',
        'no tenemos internet', 'no hay internet', 'no hay senal',
        # FIX 949: Variantes faltantes detectadas en test_1000_escenarios (22 FAIL)
        'no manejo eso del whatsapp', 'no le se al whatsapp', 'no se usar el whatsapp',
        'whatsapp no', 'correo no', 'correo tampoco', 'tampoco correo',
        'no tengo wats', 'no tengo el wats', 'no tengo el whats',
        'no tenemos whatsapp', 'no tenemos correo', 'no tenemos wats',
        'mejor por otro medio', 'mejor no por whatsapp', 'mejor no por correo',
        'eso del whatsapp no', 'eso del correo no',
        # FIX 994: Políticas de privacidad como rechazo de dato
        'por politicas no podemos', 'por politicas no', 'politicas de privacidad',
        'no podemos por politicas', 'no puedo por politicas',
        # FIX 996: Solo teléfono (rechazo de canales digitales)
        'solo manejo llamadas', 'solo recibo llamadas', 'prefiero por telefono',
        'mejor por telefono', 'solo por telefono', 'nada mas por telefono',
        'prefiero llamadas', 'solo llamadas',
        # FIX 998: No tienen redes / ese tipo de contacto
        'no tenemos redes sociales', 'no tenemos ese tipo de contacto',
        'no le puedo decir el numero', 'no le puedo decir',
        'no tenemos correo corporativo', 'no tenemos pagina',
        # FIX 983: Variantes con artículo 'el' que rompen substring match
        # 'no tengo email' matchea pero 'no tengo el email' NO (artículo intermedio)
        'no tengo el email', 'no tengo el correo', 'no tengo el whatsapp',
        'no tengo el watsapp', 'no tengo el telefono',
        'no hay el correo', 'no hay el email', 'no hay el whatsapp',
        # FIX 988: Rechazo coloquial de datos
        'no se lo doy', 'no se los doy', 'no se lo paso', 'no ando dando datos',
        'no ando dando el numero', 'no doy datos', 'no doy numeros',
        'prefiero no dar ese dato', 'prefiero no dar el numero', 'prefiero no dar',
        'no quiero dar mis datos', 'no quiero dar el numero', 'no quiero dar datos',
        'no quiero proporcionar', 'no voy a dar', 'no te voy a dar',
        'no me gusta dar datos', 'no acostumbramos dar', 'no acostumbramos pasar',
        # FIX 989: Variantes "no sé/recuerdo mi número de WhatsApp"
        'no se mi numero de whatsapp', 'no me se mi numero de whatsapp',
        'no se mi whatsapp', 'no se mi correo', 'no recuerdo mi numero',
        'no me acuerdo del numero', 'no me acuerdo del whatsapp',
        'no me acuerdo del correo', 'no recuerdo el numero',
        'no recuerdo cual es', 'no me recuerdo',
    ]
    if any(r in tn for r in reject_data):
        return FSMIntent.REJECT_DATA

    # --- FIX 897: BRUCE2592 - Cliente pide contacto de BRUCE (contacto invertido) ---
    # "Si gustas dejarme un numero y ya lo proporciono yo" = pide datos de Bruce
    _pide_contacto_bruce_897 = [
        'dejame un numero', 'dejarme un numero', 'dejame tu numero',
        'dejarme tu numero', 'dame tu numero', 'dame tu telefono',
        'pasame tu numero', 'pasame tu telefono', 'pasame tus datos',
        'dame tus datos', 'dejame tus datos', 'me das tu numero',
        'me dejas tu numero', 'me pasas tu numero', 'me pasas tus datos',
        'dejame el numero', 'dame el numero', 'tu numero de telefono',
        'si gustas dejarme', 'dejame un telefono',
        # FIX 1032: "Deje su número y él le llama" / "Me dice su número" → Bruce da su contacto
        'deje su numero', 'deje el numero', 'me da su numero', 'digame su numero',
        'denos su numero', 'me dice su numero', 'me das tu numero de contacto',
        'el le llama', 'el le marca', 'ella le llama', 'ella le marca',
        'para que le marque', 'para que le llame', 'le podemos marcar',
        'le podemos llamar', 'que le marque', 'que le llame',
        'nos puede dar su numero', 'nos da su numero', 'dejenos su numero',
    ]
    if any(p in tn for p in _pide_contacto_bruce_897):
        return FSMIntent.INTEREST  # Triggers ofrecer_contacto_bruce via FSM table

    # FIX 1051: "aqui le paso" = TRANSFER (receptionist transferring call)
    # Must check BEFORE offer_data which also has 'le paso' as substring
    _le_paso_transfer_1051 = any(p in tn for p in [
        'aqui le paso', 'aqui te paso', 'le paso a ', 'le paso con ',
        'te paso a ', 'te paso con ', 'ya le paso', 'ya te paso',
        'le voy a pasar', 'le paso ahora',
    ])
    if _le_paso_transfer_1051:
        return FSMIntent.TRANSFER

    # --- Oferta de dato ---
    offer_data = [
        'te doy', 'le doy', 'te paso', 'le paso', 'te puedo dar',
        'le puedo dar', 'te puedo proporcionar', 'le puedo proporcionar',
        'te puedo pasar', 'anota', 'apunta', 'si gusta anotar',
        'tiene donde anotar', 'yo le doy el correo', 'por correo',
        # FIX 989: "anotemelo"/"apúntelo" = cliente listo para dar dato → OFFER_DATA
        'anotemelo', 'anoteme', 'apuntelo', 'apuntame',
        'te mando', 'le mando', 'mi correo es', 'mi whatsapp es',
        'mi numero es', 'el numero es', 'el correo es',
        'mandelo por whatsapp', 'por whatsapp', 'mandalo por whatsapp',
        'al whatsapp', 'a mi whatsapp', 'a mi correo',
        # FIX 980: Variantes con 'wats' (abreviación informal de WhatsApp)
        # ANTES: 'al wats'/'mandamelo al wats' caía en callback_guard ('mandame' substring)
        # AHORA: offer_data se checa ANTES que callback_guard → OFFER_DATA correcto
        'al wats', 'por wats', 'a mi wats', 'wats porfa', 'al correo esta bien',
        'al correo si', 'al email', 'por email', 'mandamelo al', 'mandamelo por',
        # FIX 987: 'wasap'/'whats' = abreviaciones coloquiales de WhatsApp → OFFER_DATA
        'por wasap', 'al wasap', 'a mi wasap', 'mejor por wasap',
        'por whats', 'al whats', 'wasap porfa', 'whats porfa',
        # FIX 999: 'wa' = abreviación ultra-corta de WhatsApp
        'al wa', 'por wa', 'a mi wa', 'mejor al wa', 'al wa esta bien',
        'mande la lista de precios', 'mande la lista', 'mande los precios',
        # FIX 981: "por el whatsapp/wats" — 'el' intermedio rompe substring match de 'por whatsapp'
        'por el whatsapp', 'por el wats', 'a el whatsapp', 'a el wats',
        'esta bien el whatsapp', 'esta bien el wats', 'esta bien al wats',
        # FIX 983: 'al correo' / 'al email' como canal de preferencia (OFFER_DATA)
        'al correo', 'al email', 'por el correo', 'por el email',
        # FIX 984: 'mandame la info'/'mandamela' caían en callback_guard ('mandame' substring)
        # offer_data se checa ANTES → clasificación correcta como OFFER_DATA
        'mandame la info', 'mandame la informacion', 'mandame la información',
        'mandame el catalogo', 'mandame el catálogo', 'mandame todo',
        'mandame info', 'mandame informacion', 'mandame información',
        'mandame eso', 'mandame algo', 'mandame los datos',
        'mandamela', 'mandamelas', 'mandamelo todo',
        'mande la info', 'mande el catalogo', 'mande el catálogo',
        'mande la informacion', 'mande la información',
        'mande info', 'mande informacion', 'mande todo',
        'enviame la info', 'enviame el catalogo', 'enviame todo',
        'enviame info', 'enviame informacion', 'enviame información',
        'enviame eso', 'enviame los datos',
        'enviale', 'mandele', 'mandele la info', 'mandele el catalogo',
        'si mandame', 'ok mandame', 'mandame eso por favor',
        # FIX 991: "le proporciono" = ofrece dato → OFFER_DATA
        'le proporciono', 'le puedo proporcionar mi', 'le doy mi numero',
        'le doy mi whatsapp', 'le doy mi correo', 'le paso mi whatsapp',
        'le paso mi correo', 'le paso mi numero',
        # FIX 994: "le escribo el correo" / "se lo anoto" = ofrece dato
        'le escribo el correo', 'le anoto mi correo', 'le anoto mi numero',
        'se lo anoto', 'se lo escribo',
        # FIX 995: Tipos específicos de teléfono como dato
        'mi telefono de oficina', 'mi celular es el', 'mi celular es',
        'mi numero de celular', 'mi numero de oficina', 'mi numero fijo',
        'el numero de la tienda', 'el numero del negocio',
        # FIX 1017: "Mándame un WhatsApp primero" = quiere recibirlo en WhatsApp → dar número
        # ANTES: 'mandame' en callback_guard → CALLBACK → "¿A qué hora?"
        # AHORA: offer_data se checa ANTES → OFFER_DATA correcto (cliente da su WA)
        'mandame un whatsapp', 'mandame un wats', 'mandame un wasap',
        'mandame un mensaje', 'mandame un wha', 'mandame al whatsapp primero',
        'primero mandame', 'mandame algo al whatsapp',
    ]
    if any(o in tn for o in offer_data):
        return FSMIntent.OFFER_DATA

    # --- Encargado ausente ---
    manager_absent = [
        'no esta', 'no se encuentra', 'salio', 'esta en junta',
        'no ha llegado', 'viene mas tarde', 'llega mas tarde',
        'no viene hoy', 'esta de vacaciones', 'esta ocupado',
        'esta ocupada', 'esta comiendo', 'salio a comer',
        'no lo veo', 'todavia no llega', 'ya se fue',
        # FIX 882: BRUCE2625 - "salieron" no matcheaba (solo "salio")
        # BRUCE2630 - "no se encuentre" (subjuntivo) no matcheaba
        'salieron', 'no se encuentre', 'anda fuera', 'no vino',
        'hora de comida', 'fueron a comer', 'esta fuera',
        'estan comiendo', 'esta en su hora', 'esta descansando',
        # FIX 926: BRUCE1825 - "no hay nadie" no se detectaba
        'no hay nadie', 'no hay quien', 'nadie que atienda',
        'no nos puede atender', 'no puede atender', 'andan fuera',
        # FIX 991: Variantes "ahorita anda ocupado/en llamada"
        'ahorita anda ocupado', 'ahorita anda ocupada', 'anda ocupado', 'anda ocupada',
        'ahorita esta ocupado', 'ahorita esta ocupada', 'esta en una llamada',
        'anda en una llamada', 'anda en junta', 'anda en reunion',
        'no esta disponible', 'no esta aqui ahorita', 'ahorita no se encuentra',
        # FIX 999: Ausente por cita/evento/reunión externa
        'se fue a una cita', 'fue a un evento', 'esta en una cita',
        'fue a una reunion fuera', 'fue a una cita', 'salio a una cita',
        'esta en un evento', 'fue al banco', 'fue a hacer un tramite',
        # FIX 992: Más variantes de ausencia
        'ahorita nadie', 'nadie ahorita', 'andan de viaje', 'se fue de viaje',
        'se fue de vacaciones', 'salio de viaje', 'esta de viaje',
        # FIX 995: Encargado en otra área o atendiendo
        'esta en la bodega', 'esta en el almacen', 'esta en el piso de venta',
        'esta atendiendo un cliente', 'esta con un cliente', 'esta con visita',
        'esta en caja', 'esta cargando mercancia', 'esta en el patio',
        # FIX 1024: "yo no decido eso" = no es el decisor → redirigir al que decide
        'yo no decido', 'no soy quien decide', 'no tomo esas decisiones',
        'no es mi decision', 'no soy el que decide', 'no decido yo',
        'las compras las hace', 'las compras las decide',
        'no tengo autoridad para', 'no tengo poder de decision',
    ]
    if any(m in tn for m in manager_absent):
        return FSMIntent.MANAGER_ABSENT
    # "No" a secas después de preguntar por encargado = MANAGER_ABSENT contextual
    # FIX 890: BRUCE2621 - "Dígame. Fíjese que no." → "fijese que no" = manager absent
    if tn in ('no', 'no fijese', 'no fijate', 'no senor', 'no senorita',
              'fijese que no', 'fijate que no', 'pues no', 'que no'):
        if context.encargado_preguntado and state == FSMState.BUSCANDO_ENCARGADO:
            return FSMIntent.MANAGER_ABSENT
    # FIX 890: "Dígame. Fíjese que no." combined → check for "fijese que no" in longer text
    if 'fijese que no' in tn or 'fijate que no' in tn:
        if state == FSMState.BUSCANDO_ENCARGADO:
            return FSMIntent.MANAGER_ABSENT

    # --- Encargado presente ("soy yo") ---
    manager_present = [
        'soy yo', 'yo soy', 'si soy', 'yo mero', 'yo soy el encargado',
        'yo soy la encargada', 'si yo soy', 'aqui yo', 'servidor',
        'yo me encargo', 'conmigo', 'a mi',
        # FIX 891: BRUCE2605 - "a la orden" / "a tus ordenes" = encargado presente
        'a la orden', 'a tus ordenes', 'a sus ordenes', 'a tu orden',
        # FIX 987: Variantes coloquiales mexicanas de "soy el encargado"
        # NOTE: 'con el encargado' EXCLUIDO — FP en "le comunico con el encargado" (TRANSFER)
        'aqui ando', 'aqui estoy yo', 'le habla el encargado', 'le habla la encargada',
        'habla el encargado', 'habla la encargada', 'encargado habla',
        # FIX 991: "ando yo aqui" = soy yo el que está (coloquial)
        'ando yo aqui', 'ando aqui yo', 'aqui andamos', 'yo ando aqui',
        # FIX 992: Variantes de "aquí estoy / soy yo el encargado"
        'para servirle', 'para servirles', 'para servir', 'a sus ordenes',
        'ella anda aqui', 'el esta aqui', 'aqui con usted', 'si con el',
        'si con ella', 'le atiende el encargado', 'le atiende la encargada',
        'con el encargado si', 'con la encargada si',
        # FIX 997: "yo manejo eso" = yo soy el que toma decisiones
        'yo manejo eso', 'yo lo manejo', 'yo me encargo de eso',
        # FIX 998: "aqui mando yo" = soy el decisor
        'aqui mando yo', 'yo mando aqui', 'aqui mando yo solo',
        # FIX 999: Propietario/dueño que responde directamente
        'soy el dueno', 'soy la duena', 'soy el propietario', 'soy la propietaria',
        'le habla el propietario', 'le habla la propietaria',
        'el que habla es el dueno', 'el que habla es el propietario',
        'soy el socio', 'soy el gerente', 'soy la gerente',
        # FIX 1000: "con él habla" = soy yo el encargado
        'con el habla', 'con ella habla', 'con el mismo habla',

        # FIX 988: Quién toma decisiones de compra = encargado
        'soy la que compra', 'soy el que compra', 'soy quien compra',
        'yo tomo las decisiones', 'yo decido las compras', 'yo soy quien decide',
        'yo soy la que decide', 'yo me encargo de eso', 'yo compro aqui',
        'yo soy el responsable', 'yo soy la responsable', 'yo soy el dueno',
        'yo soy la duena', 'yo soy el jefe', 'yo soy la jefa',
    ]
    if any(m in tn for m in manager_present):
        # FIX 906: Si también hay callback, priorizar callback
        # Ej: "si soy pero marqueme el lunes" = CALLBACK, no MANAGER_PRESENT
        _has_callback_906 = any(c in tn for c in [
            'marqueme', 'llameme', 'marque el', 'llame el',
            'mas tarde', 'despues', 'luego', 'otro dia',
            'la proxima', 'no puedo ahorita', 'ando ocupado',
            # FIX 1031: 'estoy ocupado' / 'estoy atendiendo' = CALLBACK no MANAGER_PRESENT
            'estoy ocupado', 'estoy muy ocupado', 'estoy bastante ocupado',
            'estoy atendiendo', 'estoy en junta', 'estoy en reunion',
            'estoy trabajando', 'estoy con clientes', 'estoy con un cliente',
            'ahorita no puedo', 'no puedo en este momento', 'no es buen momento',
        ])
        if _has_callback_906:
            return FSMIntent.CALLBACK
        return FSMIntent.MANAGER_PRESENT

    # --- Transfer (espere en línea) ---
    transfer = [
        'espere un momento', 'espereme', 'espera por favor', 'permitame',
        'permiteme', 'un momento', 'un momentito', 'un segundo',
        'dejeme ver', 'le comunico', 'se lo paso', 'se lo comunico',
        'ahorita le paso', 'ahorita se lo comunico',
        # FIX 996: Más variantes de transferencia
        'espere le busco', 'espere le llamo', 'le llamo al encargado',
        'le llamo a la encargada', 'voy por el encargado', 'voy por ella',
        'voy por el', 'ahorita le busco', 'ahorita le llamo',
        # FIX 896: BRUCE2580 - Transfer en 3ra persona
        'te comunican', 'te pasan', 'te transfieren', 'te paso',
        'ahi te comunican', 'ahi te pasan', 'te van a pasar',
        'te van a comunicar', 'lo comunico', 'lo paso',
    ]
    # Guard: NO es callback ("esperar a que regrese")
    # FIX 820: Expandido callback_guard con patrones de BRUCE2535
    callback_guard = [
        'esperar a que', 'esperar que regrese', 'esperar que llegue',
        'esperar que vuelva', 'marcar mas tarde', 'llamar mas tarde',
        'llamar despues', 'marcar despues', 'hablar luego',
        'mandarme', 'enviarme', 'mandame', 'enviame',
        'viene hasta el', 'regresa hasta el', 'llega hasta el',
        'regresa el', 'viene el', 'llega el',
        # FIX 820: BRUCE2535 "esperar ya que regrese"
        'esperar ya que', 'tendrias que esperar', 'tendria que esperar',
        'tienes que esperar', 'tiene que esperar', 'hay que esperar',
        # FIX 906: Callback con dias de la semana
        'marqueme el lunes', 'marqueme el martes', 'marqueme el miercoles',
        'marqueme el jueves', 'marqueme el viernes',
        'llameme el lunes', 'llameme el martes', 'llameme el miercoles',
        'llameme el jueves', 'llameme el viernes',
        'marque el lunes', 'marque el martes', 'marque el miercoles',
        # FIX 938: OOS audit V2 - "marca al rato" / "llama al rato" no detectados
        'marca al rato', 'llama al rato', 'llamame al rato',
        'marqueme al rato', 'marcame al rato', 'llame al rato',
    ]
    # FIX 894: BRUCE2604 - Guard de queja antes de TRANSFER
    # "permítame, márcame a cada rato, ya se les dijo que no" → "permitame" matchea TRANSFER
    # pero el cliente se está QUEJANDO, no transfiriendo
    _complaint_guard_894 = [
        'a cada rato', 'ya se les dijo', 'ya les dije', 'ya se lo dije',
        'no nos interesa', 'no me interesa', 'dejen de llamar', 'dejen de marcar',
        'ya no llamen', 'ya no marquen', 'estan molestando', 'molestando',
        'ya basta', 'ya estuvo', 'ya cansan',
    ]
    _is_complaint_894 = any(c in tn for c in _complaint_guard_894)
    if any(c in tn for c in callback_guard):
        return FSMIntent.CALLBACK
    if any(t in tn for t in transfer):
        # FIX 894: Si hay queja, NO es transfer - es NO_INTEREST
        if _is_complaint_894:
            return FSMIntent.NO_INTEREST
        return FSMIntent.TRANSFER

    # --- Callback ---
    callback = [
        'mas tarde', 'manana', 'otro dia', 'la proxima semana',
        'despues', 'luego', 'vuelva a llamar', 'llame despues',
        'marque despues', 'regrese', 'vuelva', 'cuando llegue',
        'a las', 'en la tarde', 'en la manana', 'por la manana',
        # FIX 902: BRUCE2596 - "si gusta hablar por ahi de las seis"
        'por ahi de las', 'hablar por ahi de', 'gusta hablar',
        'si gusta llamar', 'si gusta marcar',
        # FIX 882: BRUCE2625 - "si gustas marcar en una hora, salieron"
        # "en una hora" no matcheaba (solo "a las"), "si gustas" (tuteo) no matcheaba
        'en una hora', 'en un rato', 'en un momento',
        'si gustas llamar', 'si gustas marcar', 'gustas marcar',
        'si gustas hablar', 'gustas llamar',
        'marcar en una hora', 'llamar en una hora',
        # FIX 990: Variantes coloquiales "ahora no, después"
        'por el momento no', 'no por el momento', 'en este momento no',
        'ahorita no', 'ahorita no puedo', 'ahorita no puedes',
        'no en este momento', 'no por ahora', 'ahora no puedo',
        'en un momento', 'ahorita regresa', 'ahorita llega',
        # FIX 991: Pronunciaciones regionales coloquiales ("horita" / "ora")
        'horita no', 'ora no', 'por ora no', 'horita regresa', 'horita llega',
        # FIX 993: "en camino" = llegará pronto → callback implícito
        'esta en camino', 'viene en camino', 'va en camino', 'anda en camino',
        # FIX 994: "el siguiente lunes/semana" = callback futuro
        'el siguiente lunes', 'el siguiente martes', 'el siguiente miercoles',
        'el siguiente jueves', 'el siguiente viernes', 'la siguiente semana',
        'marque la siguiente', 'llame la siguiente', 'la proxima semana',
        'regresa en dos horas', 'regresa en una hora', 'llega al mediodia',
        'llega a mediodia', 'llega al rato', 'regresa al rato',
        # FIX 996: "mejor llámennos" = callback (ellos llaman)
        'mejor llamamenos', 'mejor llamenos', 'llamamenos',
        'mejor nos llama', 'puede llamarnos', 'vuelva a llamarnos',
        # FIX 997: "el próximo lunes/viernes" / "esta semana no" / "la semana que entra"
        'el proximo lunes', 'el proximo martes', 'el proximo miercoles',
        'el proximo jueves', 'el proximo viernes',
        'marque el proximo', 'llame el proximo',
        'esta semana no', 'esta semana no puedo', 'la semana que entra',
        'la semana entrante', 'la semana siguiente',
        # FIX 998: Callbacks con referencias temporales más específicas
        'a fin de mes', 'a finales del mes', 'a principios del mes',
        'principios del mes que entra', 'finales del mes que entra',
        'mejor marcame a fin', 'a fin del mes',
        # FIX 1000: Callbacks formales/educados
        'podria volver a contactarnos', 'contactenos la proxima',
        'la proxima quincena', 'el siguiente trimestre', 'el proximo trimestre',
        'el siguiente mes', 'a finales de mes', 'la quincena que viene',
        # FIX 998: "quién sabe" = no sabe cuando regresa = callback tentativo
        'quien sabe', 'ni idea', 'no se cuando',
        # FIX 999: Sin presupuesto = callback temporal
        'no tenemos presupuesto', 'sin presupuesto', 'nos quedamos sin presupuesto',
        'no hay presupuesto', 'no hay recursos', 'no hay fondos',
        # FIX 995: "lo voy a pensar" / "consultar con el dueño" = callback tentativo
        'lo voy a pensar', 'lo pensare', 'voy a pensar', 'tengo que pensar',
        'lo comento con', 'voy a consultar', 'tengo que consultar',
        'hay que verlo', 'hay que pensarlo', 'hay que consultarlo',
        'me lo tiene que autorizar', 'tiene que autorizar', 'necesita autorizarlo',
        'lo tengo que consultar', 'lo tenemos que consultar',
        # FIX 1030: "pasado mañana" / "vuélveme a llamar" / "llama mañana" = callback específico
        'pasado manana', 'pasado mañana',
        'vuelveme a llamar', 'vuelvame a llamar', 'vuelve a llamar',
        'llamame manana', 'llama manana', 'llama mañana', 'llamame mañana',
        'marcame manana', 'marca manana', 'marcame mañana',
        'llama otro dia', 'llamame otro dia', 'en otro momento',
        'en unos dias', 'en unos días', 'dentro de unos dias',
        # FIX 1033: "en unos meses" / "en tres meses" / "regresa en N meses" = callback long-term
        'en unos meses', 'en algunos meses', 'en tres meses', 'en dos meses',
        'en un mes', 'dentro de un mes', 'dentro de dos meses', 'dentro de tres meses',
        'regresa en tres meses', 'regresa en dos meses', 'regresa en un mes',
        'en unos meses regresa', 'en unos meses llega', 'en unos meses viene',
        'el siguiente año', 'el proximo año', 'a inicio del año',
        'en unas semanas', 'dentro de unas semanas', 'en dos semanas', 'en tres semanas',
    ]
    if any(c in tn for c in callback):
        if state in (FSMState.BUSCANDO_ENCARGADO, FSMState.ENCARGADO_AUSENTE,
                     FSMState.PITCH, FSMState.ESPERANDO_TRANSFERENCIA,
                     FSMState.ENCARGADO_PRESENTE, FSMState.DICTANDO_DATO,
                     FSMState.CAPTURANDO_CONTACTO):  # FIX 935 + FIX 938
            return FSMIntent.CALLBACK

    # --- Otra sucursal ---
    another = [
        'otra sucursal', 'otro local', 'no es aqui', 'numero equivocado',
        'se equivoco', 'no es esta sucursal', 'otra ubicacion',
        # FIX 866A: BRUCE2111 - "tienes que hablar a la sucursal de Sahuayo" → ANOTHER_BRANCH
        'tienes que hablar a la sucursal', 'tiene que hablar a la sucursal',
        'hablar a la sucursal', 'llamar a la sucursal', 'llame a la sucursal',
        # FIX 904: BRUCE2585 - "el area de compras esta en otro [lado/edificio]"
        'area de compras esta en otro', 'compras esta en otro',
        'compras estan en otro', 'se comunica a una tienda',
        'esta comunicando a una tienda', 'comunicando a una sucursal',
        # FIX 888: BRUCE2580 - "ahí te comunican a compras" / "comunicarte a matríz"
        'comunican a compras', 'te comunican a', 'comunicarte a matri',
        'comunicar a matri', 'comunicate a', 'habla a compras',
        # FIX 993: Área incorrecta dentro de la empresa
        'esto es recursos humanos', 'area de recursos humanos', 'esto es contabilidad',
        'esto es administracion', 'esto es recepcion', 'somos el area de',
        'aqui es el departamento de', 'esto es el area de',
    ]
    if any(a in tn for a in another):
        return FSMIntent.ANOTHER_BRANCH

    # --- Cerrado ---
    closed = ['esta cerrado', 'estamos cerrados', 'ya cerramos', 'no abrimos']
    if any(c in tn for c in closed):
        return FSMIntent.CLOSED

    # --- Pregunta identidad ---
    identity = [
        'quien habla', 'de donde', 'de que empresa', 'de que parte',
        'a donde llama', 'de donde llama', 'con quien hablo',
        # FIX 883: BRUCE2630/2634 - "de parte de quién" no matcheaba
        # Cliente pregunta procedencia → Bruce debe identificarse
        'de parte de', 'de parte de quien', 'quien eres',
        'como te llamas', 'como se llama', 'quien me habla',
        'quien me llama', 'de que compania', 'de que marca',
        # FIX 994: "y usted quién es" = pregunta identidad
        'y usted quien', 'y tu quien', 'y usted de donde', 'y usted que',
        # FIX 1000: "quién le llama" = pregunta identidad
        'quien le llama', 'quien me esta llamando', 'quien llama',
        # FIX 1021: "¿es usted una grabación/robot?" y empresa equivocada
        'es una grabacion', 'es grabacion', 'eres una grabacion',
        'son una grabacion', 'es robot', 'es un robot', 'es un bot',
        'persona real', 'es humano', 'habla con alguien real',
        'es automatizado', 'es inteligencia artificial', 'es una ia',
        'son de herrajes', 'son de ferreteria', 'verdad que son de',
        'son ustedes de', 'es usted de',
    ]
    if any(i in tn for i in identity):
        return FSMIntent.IDENTITY

    # --- Verificación conexión (ANTES de pregunta para que "¿Bueno?" no matchee como QUESTION) ---
    verification = ['bueno', 'me escucha', 'me oye', 'ahi esta', 'aqui esta', 'sigue ahi',
                    'oiga', 'oye']
    if any(v == tn or v in tn for v in verification):
        if len(tn) < 20:
            return FSMIntent.VERIFICATION
    # FIX 837: Fillers cortos - SOLO exact match (no substring)
    # NO incluir 'mmhmm' - en ESPERANDO_TRANSFERENCIA es ruido de fondo (debe ser NOOP)
    _filler_exact_837 = ['mhm', 'mmm', 'aha', 'ajam']
    if tn in _filler_exact_837:
        return FSMIntent.VERIFICATION

    # --- FIX 894: "Que deseaba" / "Que ofrece" → pitch directo ---
    # NOTE: Identity questions (de donde llama, quien habla) already handled by
    # IDENTITY intent at line 632. No need for separate IDENTITY_QUESTION.
    # Estas son preguntas de cortesía que requieren pitch, no GPT_NARROW genérico
    _what_offer_894 = [
        'que deseaba', 'que desea', 'que ofrece', 'que ofrecen',
        'que vende', 'que venden', 'en que se le ofrece', 'en que le puedo',
        'que me ofrece', 'que nos ofrece', 'que producto', 'que tienen',
        'de que se trata', 'para que es', 'a que se dedican',
        # FIX 940: BRUCE2665 - recepcionista "¿En qué podemos ayudarle?"
        # GPT respondía como comprador en vez de dar el pitch de ventas
        'en que podemos ayudarle', 'en que le podemos ayudar',
        'como le podemos ayudar', 'como le puedo ayudar',
        'en que le puedo servir', 'en que le podemos servir',
        'podemos ayudarle', 'puedo ayudarle', 'diga usted',
        # FIX 1013: Solicitud de supervisor → redirigir con pitch (Bruce es el contacto)
        'con su supervisor', 'con el supervisor', 'hablar con el supervisor',
        'hablar con su supervisor', 'comunicarme con su supervisor',
        'quiero hablar con el supervisor', 'supervisor por favor',
        'me puede comunicar con su', 'me puede comunicar con el supervisor',
    ]
    if any(q in tn for q in _what_offer_894):
        return FSMIntent.WHAT_OFFER

    # --- Pregunta general ---
    question_markers = ['que', 'cual', 'como', 'cuando', 'donde', 'cuanto', 'cuantos', 'por que']
    # FIX 795: Saludos que empiezan con "que" NO son preguntas reales
    # "que tal buen dia" -> NO QUESTION (es re-saludo)
    greeting_not_question_795 = ['que tal', 'que onda', 'que hubo', 'que paso']
    if any(tn.startswith(q + ' ') for q in question_markers):
        if not any(tn.startswith(g) for g in greeting_not_question_795):
            return FSMIntent.QUESTION
    if '?' in texto:
        if not any(tn.startswith(g) for g in greeting_not_question_795):
            return FSMIntent.QUESTION

    # --- Confirmación ---
    confirm_exact = [
        'si', 'si claro', 'claro', 'ok', 'esta bien', 'sale', 'va',
        'claro que si', 'por supuesto', 'adelante', 'digame',
        'diga', 'aja', 'como no', 'si digame', 'ok esta bien',
        'si esta bien', 'bueno esta bien', 'ah ok', 'ah bueno',
        # FIX 837: Patterns faltantes que caian como UNKNOWN
        'orale', 'andale', 'correcto', 'exacto', 'asi es',
        'si si', 'si si si', 'ah si', 'ah ok si', 'ah ya',
        'efectivamente', 'mande', 'si mande', 'ya', 'listo',
        'si gracias', 'ok gracias', 'perfecto', 'muy bien',
        # FIX 993: Multi-word confirmations
        'si perfecto', 'si listo', 'si muy bien', 'si adelante', 'si sale',
        'si va', 'si orale', 'si andale', 'si correcto', 'si exacto',
        'ok perfecto', 'ok listo', 'ok sale', 'ok va', 'ok orale',
        'claro perfecto', 'claro que si perfecto',
        # OOS-13-17: Preferencia de número cuando ya se dio → CONFIRMATION
        'use el personal', 'use el del negocio', 'use el de la tienda',
        'el personal por favor', 'mejor el personal', 'el personal mejor',
        'use el personal por favor', 'prefiero el personal',
    ]
    if tn in confirm_exact or any(c == tn for c in confirm_exact):
        # FIX 884 (reemplaza FIX 893): BRUCE2619 - "Dígame" en BUSCANDO_ENCARGADO
        # FIX 893 original: dígame → INTEREST → salta a pedir WhatsApp (INCORRECTO)
        # BRUCE2619: cliente dice "Dígame" queriendo escuchar, no expresar interés
        # Corrección: dígame → MANAGER_PRESENT → da pitch (el que dice "dígame" ES el decisor)
        # Esto evita: (1) re-preguntar encargado (LOOP) y (2) saltar a WhatsApp sin pitch
        _digame_like_884 = {'digame', 'si digame', 'diga', 'mande', 'si mande', 'adelante'}
        if (tn in _digame_like_884 and
                state == FSMState.BUSCANDO_ENCARGADO and
                context.encargado_preguntado):
            return FSMIntent.MANAGER_PRESENT
        return FSMIntent.CONFIRMATION

    # --- Continuación (texto termina en conector) ---
    if tn.endswith(' y') or tn.endswith(' o') or tn.endswith(' pero'):
        return FSMIntent.CONTINUATION

    # --- Preguntas implícitas (FIX 938 MEJ-02) ---
    # Frases afirmativas que funcionan como preguntas sobre productos/empresa
    # No empiezan con question_markers pero requieren respuesta informativa
    implicit_questions = [
        'tienen descuentos', 'tienen descuento', 'manejan descuento',
        'tienen sucursal', 'tienen tienda', 'tienen local',
        'trabajan con credito', 'manejan credito', 'dan credito',
        'manejan herramienta', 'tienen herramienta', 'trabajan herramienta',
        'son distribuidores', 'son mayoristas', 'son fabricantes',
        'de donde son', 'de donde me', 'de que ciudad', 'de donde llaman',
        'cuantos productos', 'cuantas categorias',
        'en que se especializan', 'que tipo de productos',
        # FIX 987: Variantes coloquiales de preguntas sobre productos
        'cuales son sus productos', 'cuales productos', 'que productos tienen',
        'que tienen de productos', 'sus productos', 'que productos manejan',
        # FIX 996: Preguntas de precio implícitas (sin iniciar con question marker)
        'precio de mayoreo', 'precio de distribuidor', 'precio especial',
        'descuento por volumen', 'precio por volumen', 'manejo de precio',
        # FIX 997: Servicios logísticos como preguntas sobre la empresa
        'hacen entregas', 'manejan envios', 'hacen instalacion', 'tienen instalacion',
        'hacen flete', 'manejan flete', 'tienen servicio a domicilio',
        'llegan hasta aca', 'llegan a esta zona', 'hacen envio a',
        'tiempo de entrega', 'el tiempo de entrega', 'los tiempos de entrega',
        'catalogo en papel', 'prefiero catalogo en papel',
        'tienen pagina', 'tienen pagina web', 'tienen catalogo fisico',
        # FIX 1014a: Preguntas de precio (antes en interest → OFFER_DATA/digame_numero incorrecto)
        'cuanto cuesta', 'cuanto sale', 'cuanto vale', 'a cuanto esta',
        'cuanto cuesta el catalogo', 'cuanto cuesta eso', 'cuanto nos sale',
        'cuanto me cuesta', 'cuanto cobran', 'cuantos cuesta',
        # FIX 1014b: Preguntas de productos específicos no capturadas antes
        'tienen tornilleria', 'tiene tornilleria', 'manejan tornilleria',
        'tienen material de construccion', 'manejan material de construccion',
        'tienen candados', 'manejan candados', 'tienen cintas', 'tienen silicones',
        'tienen herramienta electrica', 'manejan herramienta electrica',
        'que productos tienen exactamente', 'que venden exactamente',
        'que venden', 'que manejan', 'cuantos productos tienen',
        'son mayoristas', 'son distribuidores de',
        # FIX 1020: Preguntas de servicio/empresa ignoradas como UNKNOWN
        'aceptan devoluciones', 'devoluciones', 'politica de devolucion',
        'aceptan devolucion', 'hacen devoluciones', 'puedo devolver',
        'tienen rfc', 'dan factura', 'facturan', 'factura electronica',
        'son empresa formal', 'emiten factura', 'tienen facturacion',
        'facturacion', 'requiero factura', 'necesito factura',
        'catalogo fisico', 'catalogo es fisico', 'fisico o digital',
        'el catalogo es fisico', 'catalogo digital', 'tienen catalogo en digital',
        'en cuantos dias', 'cuantos dias llega', 'cuantos dias tarda',
        'en que tiempo llega', 'cuando llega el pedido', 'dias de entrega',
        'cuanto tarda el envio', 'cuanto tarda la entrega',
        # FIX 1034: "¿Cómo consiguió este número?" → GPT explica origen de datos
        'como consiguio este numero', 'como obtuvo este numero', 'de donde saco este numero',
        'como consiguio mi numero', 'de donde consiguio mi numero',
        'quien le dio mi numero', 'como obtuvo mi contacto', 'donde consiguio mi contacto',
        'de donde saco mi numero', 'como tiene mi numero',
        # FIX 1035: "Solo trabajamos con proveedores certificados, ¿tienen eso?" → QUESTION
        'proveedores certificados', 'proveedor certificado', 'certificacion de proveedor',
        'estan certificados', 'tienen certificacion', 'tienen certificado',
        'son proveedores certificados', 'cuentan con certificacion',
        'requieren certificacion', 'requieren estar certificados',
    ]
    if any(q in tn for q in implicit_questions):
        return FSMIntent.QUESTION

    # --- Interés implícito ---
    # FIX 919: Expandido con señales sutiles de interés
    interest = [
        'me interesa', 'si me interesa', 'cuenteme', 'cuentame',
        'a ver', 'que ofrece', 'que ofrecen', 'que tiene', 'que tienen',
        'mandame', 'mandeme', 'enviame', 'envieme', 'pasame',
        'como le hago', 'como funciona', 'que precio', 'que precios',
        'que descuento', 'que promocion',
        # NOTE: 'cuanto cuesta'/'cuanto sale' movidos a implicit_questions (FIX 1014a)
        'suena bien', 'suena interesante', 'esta interesante',
        'si claro', 'por supuesto', 'como no', 'va que va',
        'mandalo', 'mandelo', 'envialo', 'envielo',
        'si por favor', 'si porfavor', 'adelante pues',
        'que marcas', 'que productos', 'que categorias',
        'quiero ver', 'me gustaria ver', 'me gustaria conocer',
        # FIX 990: Interés tentativo/condicional
        'podria ser', 'quizas si', 'tal vez si', 'seria bueno', 'puede ser',
        'pues si podria', 'cabria la posibilidad', 'habria que ver',
        'estaria bien', 'algo asi', 'suena bien eso',
        # FIX 996: Preguntas implícitas de precio sin question marker
        'a cuanto me lo dejan', 'a como me lo dan', 'a cuanto me sale',
        'precio especial', 'tienen precio especial', 'precio por volumen',
        'hacen descuento por volumen', 'manejan precio de mayoreo',
        'precio de mayoreo', 'precio de distribuidor',
        # FIX 996: Canal alternativo social = ofrecer dato (Bruce no usa pero cliente confirma)
        'por mensaje de whatsapp', 'por whatsapp mensaje', 'mensaje de wa',
        # FIX 991: Más expresiones de interés coloquial
        'seria una buena opcion', 'seria buena opcion', 'seria interesante',
        'me gustaria recibir', 'me gustaria conocer', 'me gustaria ver',
        'quiero saber mas', 'quisiera saber mas', 'me gustaria saber',
        'quisiera informacion', 'me interesaria', 'estaria interesado',
        'estaria interesada', 'nos podria interesar', 'podria interesarnos',
        # FIX 998: Interés tentativo / posibilista
        'pues puede que si', 'puede que si', 'quizas podria', 'tal vez podria',
        'pues quizas', 'pues tal vez', 'habria que ver',
        # FIX 1000: Búsqueda activa de nuevos proveedores = interés real
        'estamos considerando cambiar de proveedor', 'estamos buscando nuevos proveedores',
        'nos vendria bien un nuevo proveedor', 'estamos buscando proveedor',
        'queremos cambiar de proveedor', 'estamos evaluando opciones',
        'estamos comparando precios', 'estamos cotizando',
    ]
    # FIX 884B: "digame" removido de interest substring - ya manejado en confirm_exact (FIX 884)
    # BRUCE2621: "Dígame. Fíjese que no." → "digame" substring match → INTEREST → pide WhatsApp
    # Pero cliente está RECHAZANDO. "digame" solo debe ser INTEREST como exact match, no substring.
    interest_substring_guarded = ['digame']
    if any(i in tn for i in interest):
        return FSMIntent.INTEREST
    # "digame" solo como interest si es exact match o no contiene negación
    _negation_884 = ['no', 'fijese que no', 'no tengo', 'no puedo', 'no esta']
    if any(i in tn for i in interest_substring_guarded):
        if not any(n in tn for n in _negation_884):
            return FSMIntent.INTEREST

    # --- FIX 824: "No tengo" corto sin canal = rechazo genérico ---
    # BRUCE2538: "No tengo" (2 palabras) -> UNKNOWN -> FIX 791 pide WhatsApp de nuevo
    # En estados de captura, "no tengo" corto = rechazo de dato
    # FIX 837: Expandido con mas variantes
    _reject_short_824 = ['no tengo', 'tampoco tengo', 'no puedo', 'tampoco', 'no manejo',
                          'solo telefono', 'solo fijo', 'nada mas telefono', 'solo celular',
                          'no uso', 'no cuento con', 'no lo tengo', 'eso no', 'no de eso no',
                          'solo el telefono', 'solo el fijo', 'nomas telefono', 'puro telefono',
                          # FIX 949: Variantes genéricas faltantes
                          'no tenemos de eso', 'no tenemos', 'no le se',
                          'no se usar', 'no lo uso', 'la verdad no uso',
                          'pues no tengo', 'no no']
    if any(tn == r or (tn.startswith(r) and len(tn) < 25) for r in _reject_short_824):
        if state in (FSMState.ENCARGADO_PRESENTE, FSMState.CAPTURANDO_CONTACTO,
                     FSMState.DICTANDO_DATO, FSMState.ENCARGADO_AUSENTE):
            return FSMIntent.REJECT_DATA

    # --- FIX 825: "Buen día/tardes/noches" = saludo recíproco o despedida contextual ---
    # 104 llamadas: cliente dice "Buen día" respondiendo al saludo -> UNKNOWN -> salta a PITCH
    # En SALUDO/PITCH: saludo recíproco -> VERIFICATION (procede normal)
    # En DESPEDIDA/CONTACTO_CAPTURADO: despedida cortés -> FAREWELL
    _saludo_reciproco_825 = ['buen dia', 'buenos dias', 'buenas tardes', 'buenas noches']
    if any(s in tn for s in _saludo_reciproco_825):
        if state in (FSMState.DESPEDIDA, FSMState.CONTACTO_CAPTURADO):
            return FSMIntent.FAREWELL
        return FSMIntent.VERIFICATION

    # --- FIX 829: Patterns adicionales ---
    # "tardes" sola como verificación (32 casos), "que tal" ya en FIX 795
    if tn in ('tardes', 'buenas', 'dias', 'noches'):
        return FSMIntent.VERIFICATION

    # ============================================================
    # FIX 886: Fuzzy matching para texto STT garbled
    # ============================================================
    # Produccion: Azure/Deepgram distorsiona palabras clave.
    # Ejemplo: "sobra de comida" = "hora de comida" garbled por STT.
    # Si llegamos aqui (UNKNOWN), intentar fuzzy match con patterns criticos.
    # Solo se activa para textos > 10 chars (evitar false positives en textos cortos).
    if len(tn) > 10:
        _fuzzy_patterns_886 = [
            # (pattern_words, intent, min_words_match)
            # manager_absent: STT garble "hora"→"sobra", "salió"→"sali", etc.
            (['hora', 'comida'], FSMIntent.MANAGER_ABSENT, 2),
            (['no', 'encuentra'], FSMIntent.MANAGER_ABSENT, 2),
            (['salio', 'comer'], FSMIntent.MANAGER_ABSENT, 2),
            (['esta', 'ocupado'], FSMIntent.MANAGER_ABSENT, 2),
            (['esta', 'ocupada'], FSMIntent.MANAGER_ABSENT, 2),
            (['no', 'llego', 'todavia'], FSMIntent.MANAGER_ABSENT, 2),
            # callback: "gustas marcar" garbled
            (['gusta', 'marcar'], FSMIntent.CALLBACK, 2),
            (['gusta', 'llamar'], FSMIntent.CALLBACK, 2),
            (['llamar', 'hora'], FSMIntent.CALLBACK, 2),
            (['marcar', 'hora'], FSMIntent.CALLBACK, 2),
            # identity: "de parte de" garbled
            (['parte', 'quien'], FSMIntent.IDENTITY, 2),
            (['donde', 'llama'], FSMIntent.IDENTITY, 2),
            # no_interest: "no nos interesa" garbled
            (['no', 'interesa'], FSMIntent.NO_INTEREST, 2),
            (['no', 'necesitamos'], FSMIntent.NO_INTEREST, 2),
        ]
        words_tn = set(tn.split())
        for pattern_words, intent, min_match in _fuzzy_patterns_886:
            matches = sum(1 for pw in pattern_words if pw in words_tn)
            if matches >= min_match:
                # Extra guard: callback/manager_absent solo en estados relevantes
                if intent in (FSMIntent.CALLBACK, FSMIntent.MANAGER_ABSENT):
                    if state not in (FSMState.BUSCANDO_ENCARGADO, FSMState.PITCH,
                                     FSMState.ENCARGADO_AUSENTE, FSMState.ENCARGADO_PRESENTE,
                                     FSMState.ESPERANDO_TRANSFERENCIA):
                        continue
                print(f"  [FIX 886] Fuzzy match: '{tn[:40]}' -> {intent.name} (words: {pattern_words})")
                return intent

    return FSMIntent.UNKNOWN


# ============================================================
# Motor FSM
# ============================================================
class FSMEngine:
    """Motor de Estados Finitos Determinista para Bruce W."""

    def __init__(self):
        self.state = FSMState.SALUDO
        self.context = FSMContext()
        self._transitions = self._build_transitions()

    def reset(self):
        """Reset para nueva llamada."""
        self.state = FSMState.SALUDO
        self.context = FSMContext()

    # ----------------------------------------------------------
    # Punto de entrada principal
    # ----------------------------------------------------------
    def process(self, texto: str, agente=None) -> Optional[str]:
        """
        Procesa input del cliente y retorna respuesta.

        Returns:
            str: Respuesta de Bruce (template o narrow GPT)
            None: FSM no puede manejar -> fallthrough a GPT existente
        """
        if FSM_ENABLED == "false":
            return None

        # FIX 802: BRUCE2522 - Post-transfer re-introduction
        # FSM runs BEFORE FIX 759B in agente_ventas -> flag never consumed
        # Check flag HERE so FSM doesn't intercept with wrong template
        if agente and getattr(agente, '_post_espera_reintroducir_759', False):
            agente._post_espera_reintroducir_759 = False
            _t802 = texto.strip().lower()
            _t802 = _t802.replace('\xe1','a').replace('\xe9','e').replace('\xed','i').replace('\xf3','o').replace('\xfa','u')
            _t802 = _t802.replace('?','').replace('!','').replace('.','').replace(',','').replace('\xbf','').replace('\xa1','')
            _saludos_802 = ['hola', 'bueno', 'buen dia', 'buenas tardes', 'buenas noches', 'que tal', 'digame', 'diga', 'si digame', 'mande']
            _es_saludo_802 = any(s in _t802 for s in _saludos_802)
            _es_identidad_802 = any(q in _t802 for q in ['quien habla', 'quien llama', 'de donde', 'que empresa', 'de parte de'])
            if _es_saludo_802 and not _es_identidad_802:
                # Persona nueva saludando -> re-introducción con pitch
                print(f"\n [FIX 802] FSM: Post-transfer greeting '{texto[:60]}' -> pitch_persona_nueva")
                self.state = FSMState.BUSCANDO_ENCARGADO
                self.context.pitch_dado = True
                self.context.encargado_preguntado = True
                return self._get_template("pitch_persona_nueva")

        # 1. Clasificar intent
        intent = classify_intent(texto, self.context, self.state)
        self._last_intent = intent  # BTE: Exponer para que agente_ventas lo use

        # 1.05 FIX 918: Extraer datos mencionados por el cliente cada turno
        self._extraer_datos_cliente(texto)

        # 1.0 FIX 950: Rechazo hostil / solicitud LFPDPPP (quiten mi número, voy a colgar)
        # Debe ejecutarse ANTES de FIX 920 para no mezclar con frustración normal.
        # Template sin oferta de retomar contacto (art. 16 LFPDPPP — derecho de supresión).
        _texto_lower = texto.lower()
        _hostil_950 = [
            'le voy a colgar', 'voy a colgar', 'les voy a colgar',
            'quiten mi numero', 'borren mi numero', 'eliminen mi numero',
            'no vuelvan a llamar', 'no me vuelvan a llamar', 'no nos vuelvan a llamar',
            'no me vuelvan a marcar', 'no nos vuelvan a marcar',
            'me va a demandar', 'voy a demandar', 'voy a reportar',
            'reportare a profeco', 'voy a reportar a profeco',
            'no quiero que me llamen', 'no quiero que nos llamen',
            'no me llamen mas', 'no nos llamen mas',
            # FIX 969: Slang mexicano hostil/agresivo
            'dejen de fregar', 'dejame de fregar', 'ya no frieguen', 'ya no friegue',
            'no frieguen', 'no me frieguen', 'vayanse a fregar',
            'dejen de chingar', 'no chinguen', 'ya no chinguen',
            'dejame en paz', 'dejenos en paz', 'no nos molesten mas',
            'ya vayanse', 'ya largense', 'no quiero nada',
            # FIX 1003: Acoso / denuncia (riesgo legal y reputacional)
            'esto es acoso', 'es acoso', 'me estan acosando', 'nos estan acosando',
            'esto es hostigamiento', 'es hostigamiento', 'me estan hostigando',
            'nos estan molestando', 'me estan molestando', 'estan molestando',
            'ya no llamen', 'dejen de llamar', 'ya no marquen',
            'voy a denunciar', 'vamos a denunciar', 'lo voy a denunciar',
            'voy a poner una queja', 'voy a poner queja',
        ]
        if any(h in _texto_lower for h in _hostil_950):
            print(f"  [FIX 950] Rechazo hostil/LFPDPPP detectado -> despedida definitiva sin recontacto")
            self.state = FSMState.DESPEDIDA
            return self._get_template("despedida_hostil_950")

        # 1.01 FIX 952: Corrección de número/dato post-captura (CONTACTO_CAPTURADO state)
        # Cliente dice "ese no es el bueno", "me equivoqué", "el correcto es 3312345678"
        if self.state == FSMState.CONTACTO_CAPTURADO:
            _correccion_signals_952 = [
                'ese no es', 'ese no era', 'ese no estaba', 'ese numero no es',
                'el correcto es', 'el bueno es', 'el verdadero es', 'el que es',
                'me equivoque', 'me equivoqué', 'di mal', 'di mal el', 'di el equivocado',
                'le di el equivocado', 'le di mal', 'lo di mal',
                'no era ese', 'era otro', 'era diferente', 'es diferente',
                'es otro numero', 'otro numero es', 'el numero es',
                'corrijo', 'lo corrijo', 'perdón es', 'perdon es', 'disculpe es',
                'en realidad es', 'en realidad el', 'el real es',
                # FIX 968: Variantes que no matcheaban (OOS-50: "el número correcto es")
                'numero correcto', 'número correcto', 'correcto es',
                'el numero correcto', 'el número correcto',
                'numero equivocado', 'numero mal', 'dicte mal',
                'perdon, el', 'perdón, el',  # "Perdón, el número correcto es..."
                'es el correcto', 'ese era', 'ese numero era',
                # FIX 1026: "use el personal / use el del negocio" = preferencia de número
                'use el personal', 'el personal por favor', 'mejor el personal',
                'use el del negocio', 'use el de la tienda', 'el del negocio',
                'prefiero el personal', 'use ese personal',
                # FIX 1029: "No no, el celular es solo X" / "sin extensión" = clarificación
                'el celular es solo', 'el numero es solo', 'sin extension',
                'es sin extension', 'solo es el', 'solo el celular',
                'nada mas el', 'nada mas', 'el correcto es solo',
                'sin la extension', 'numero sin extension',
            ]
            if any(s in _texto_lower for s in _correccion_signals_952):
                import re as _re952
                _numeros_952 = _re952.findall(r'\d[\d\s\-]{6,}\d', texto)
                _numero_limpio_952 = None
                for _n in _numeros_952:
                    _solo_digits = _re952.sub(r'\D', '', _n)
                    if len(_solo_digits) >= 8:
                        _numero_limpio_952 = _solo_digits
                        break
                # FIX 1026: Si no hay número en el texto actual, buscar en historial
                # "Use el personal por favor" → extraer el número marcado como "personal"
                _hist_1026 = getattr(self, 'conversation_history', [])
                if not _numero_limpio_952 and ('personal' in _texto_lower or 'negocio' in _texto_lower):
                    _prefer_personal = 'personal' in _texto_lower
                    for _msg in reversed(_hist_1026[-6:]):
                        if _msg.get('role') != 'user':
                            continue
                        _hist_txt = _msg.get('content', '')
                        _found_pairs = _re952.findall(r'(\w+)\s+es\s+(\d{10})', _hist_txt)
                        for _label, _num in _found_pairs:
                            if _prefer_personal and 'personal' in _label.lower():
                                _numero_limpio_952 = _num
                                break
                            elif not _prefer_personal and any(w in _label.lower() for w in ['negocio', 'tienda', 'empresa']):
                                _numero_limpio_952 = _num
                                break
                        if not _numero_limpio_952:
                            # Fallback: find all 10-digit numbers in history and pick first/last
                            _all_hist_nums = _re952.findall(r'\d{10}', _re952.sub(r'\s', '', _hist_txt))
                            if len(_all_hist_nums) >= 2:
                                _numero_limpio_952 = _all_hist_nums[0] if _prefer_personal else _all_hist_nums[-1]
                        if _numero_limpio_952:
                            break
                if _numero_limpio_952:
                    print(f"  [FIX 952] Corrección post-captura detectada -> actualizando dato a {_numero_limpio_952}")
                    if hasattr(self.context, 'whatsapp') and self.context.whatsapp:
                        self.context.whatsapp = _numero_limpio_952
                    elif hasattr(self.context, 'email') and self.context.email:
                        pass  # email corrections handled by GPT (complex format)
                    # Stay in CONTACTO_CAPTURADO, confirm correction
                    _tmpl_952 = self._get_template("confirmar_correccion_952")
                    return _tmpl_952.replace("{numero}", _numero_limpio_952) if "{numero}" in _tmpl_952 else _tmpl_952

        # 1.02 FIX 953: Acumulación de dígitos parciales en DICTANDO_DATO
        # Cliente da número en múltiples turnos; confirmar cuando acumulado >= 10 dígitos.
        # Sin este fix, el último turno con pocos dígitos queda como DICTATING_PARTIAL
        # y Bruce sigue diciendo "aja" sin confirmar, o cae a GPT con "Si, aqui estoy".
        if self.state == FSMState.DICTANDO_DATO:
            import re as _re953
            if intent == FSMIntent.DICTATING_PARTIAL:
                _nuevos_953 = ''.join(_re953.findall(r'\d', texto))
                # Contar palabras numéricas en español como dígitos adicionales
                _num_words_953 = sum(1 for w in _texto_lower.split() if w in _NUMS_ESP)
                _num_words_953 += sum(2 for w in _texto_lower.split() if w in {
                    'diez','once','doce','trece','catorce','quince','dieciseis','diecisiete',
                    'dieciocho','diecinueve','veinte','treinta','cuarenta','cincuenta',
                    'sesenta','setenta','ochenta','noventa'
                })
                _placeholder_953 = 'X' * max(0, _num_words_953 - len(_nuevos_953))
                _acum_953 = self.context.datos_parciales + _nuevos_953 + _placeholder_953
                self.context.datos_parciales = _acum_953
                print(f"  [FIX 953] Dígitos acumulados: '{_acum_953}' ({len(_acum_953)} dígitos)")
                if len(_acum_953) >= 10:
                    print(f"  [FIX 953] Número completo acumulado ({len(_acum_953)} dígitos) -> DICTATING_COMPLETE_PHONE")
                    intent = FSMIntent.DICTATING_COMPLETE_PHONE
                    self.context.datos_parciales = ""
            elif intent in (FSMIntent.CONFIRMATION, FSMIntent.UNKNOWN, FSMIntent.FAREWELL,
                            FSMIntent.CONTINUATION) \
                    and len(self.context.datos_parciales) >= 8:  # FIX 1008: CONTINUATION también activa fallback
                # Cliente confirmó/terminó con suficientes dígitos acumulados
                _acum_953 = self.context.datos_parciales
                print(f"  [FIX 953] {intent.value} post-parcial con {len(_acum_953)} dígitos -> DICTATING_COMPLETE_PHONE")
                intent = FSMIntent.DICTATING_COMPLETE_PHONE
                self.context.datos_parciales = ""
            elif intent not in (FSMIntent.DICTATING_PARTIAL, FSMIntent.CONTINUATION, FSMIntent.VERIFICATION):
                # Saliendo de DICTANDO_DATO por otra razón — resetear buffer
                if self.context.datos_parciales:
                    print(f"  [FIX 953] Reseteando buffer dígitos parciales (intent={intent.value})")
                    self.context.datos_parciales = ""

        # 1.03 FIX 957: "Ya me llamaron antes" — detectar si hay interés simultáneo
        # Si el cliente menciona llamada previa + interés → no despedida → capturar contacto
        # Si solo menciona llamada previa (sin interés) → FIX 920 lo maneja abajo
        _ya_llamaron_957 = [
            'ya me llamaron', 'ya nos llamaron', 'ya les llamaron', 'ya llamaron antes',
            'ya me hablan', 'ya nos hablan', 'ya han llamado', 'ya nos han llamado',
            'ya me habian llamado', 'ustedes ya llamaron', 'ya llamaron de ahi',
        ]
        _interes_simultaneo_957 = [
            'pero si', 'pero sí', 'pero me interesa', 'pero mandeme', 'pero enviame',
            'ahora si', 'ahora sí', 'esta vez si', 'esta vez sí', 'si me interesa',
            'quiero el catalogo', 'mandeme el catalogo', 'si me manda', 'si me envias',
            'si puedo', 'si le atiendo', 'adelante', 'digame', 'cuénteme', 'cuenteme',
        ]
        if any(s in _texto_lower for s in _ya_llamaron_957):
            if any(i in _texto_lower for i in _interes_simultaneo_957):
                # Cliente dice "ya llamaron pero sí me interesa" → saltar pitch, pedir contacto
                print(f"  [FIX 957] Ya llamaron + interés simultáneo -> saltar pitch, pedir contacto")
                self.context.pitch_dado = True
                self.context.datos_capturados['relacion_previa'] = 'cliente_existente'
                self.state = FSMState.CAPTURANDO_CONTACTO
                return self._get_template("pedir_whatsapp_o_correo")
            # else: cae a FIX 920 para despedida

        # 1.1 FIX 920: Detección de frustración/sentimiento negativo pre-respuesta
        _frustracion_signals = [
            'ya me llamaron', 'ya nos llamaron', 'dejen de llamar', 'otra vez', 'ya no me llamen',
            'estoy ocupado', 'no tengo tiempo', 'estoy en junta', 'ahorita no puedo',
            'no me interesa para nada', 'ya les dije que no',
            # FIX 906: Variaciones reales de queja detectadas en simulador masivo
            'dejenos de llamar', 'dejenos de marcar', 'dejenos de estar llamando',
            'dejen de estar llamando', 'dejen de estar marcando',
            'a cada rato', 'nos tienen hartos', 'me tienen harto',
            'ya no nos llamen', 'ya no nos marquen', 'ya no queremos que nos llamen',
            'ya no le llamen', 'ya no le marquen', 'ya no la molesten', 'ya no lo molesten',
            'ya no le esten llamando', 'ya no le esten marcando',
            'ya basta', 'ya estuvo', 'ya cansan', 'estan molestando',
        ]
        if any(f in _texto_lower for f in _frustracion_signals):
            # Cliente frustrado -> responder con empatía, no con script
            if 'ocupado' in _texto_lower or 'tiempo' in _texto_lower or 'junta' in _texto_lower or 'no puedo' in _texto_lower:
                print(f"  [FIX 920] Frustración detectada: cliente ocupado -> ofrecer rellamar")
                self.state = FSMState.DESPEDIDA
                return self._get_template("despedida_ocupado_920")
            else:
                # FIX 906: Cualquier otra frustración (quejas, hartos, etc.) -> disculparse
                print(f"  [FIX 920/906] Frustración detectada: queja/llamadas repetidas -> disculparse")
                self.state = FSMState.DESPEDIDA
                return self._get_template("despedida_ya_llamaron_920")

        # 1.2 FIX 906: Detección de IVR/buzón por texto (simulador no pasa por detector_ivr)
        _buzon_ivr_signals = [
            'el numero que usted marco', 'numero que marco no existe',
            'ha sido cancelado', 'fuera de servicio', 'no esta disponible',
            'deje su mensaje despues del tono', 'deje su mensaje',
            'la persona que llama no esta disponible',
            'la persona con la que intentas comunicarte',
            'para ventas marque', 'para soporte marque', 'marque uno',
            'bienvenido a empresa', 'menu principal',
            # FIX 1028: 'extension' solo era demasiado amplio → FP con "mi número es X extensión 5"
            # Ahora solo patrones que realmente son IVR (marque/presione extension)
            'marque la extension', 'marque extension', 'presione la extension',
            'presione extension', 'para la extension',
        ]
        if any(b in _texto_lower for b in _buzon_ivr_signals):
            print(f"  [FIX 906] Buzón/IVR detectado por texto -> colgar")
            self.state = FSMState.DESPEDIDA
            return ""  # Silencio = colgar

        # 1.3 FIX 906: Detección de situaciones sensibles (fallecimiento, cierre)
        _situacion_sensible = [
            'fallecio', 'fallecido', 'murio', 'se murio', 'ya no vive',
            'cerramos el negocio', 'ya cerramos', 'cerro la tienda',
            'ya no existe el negocio', 'quebro', 'ya no abrimos',
        ]
        if any(s in _texto_lower for s in _situacion_sensible):
            print(f"  [FIX 906] Situación sensible detectada -> despedida empática")
            self.state = FSMState.DESPEDIDA
            return self._get_template("despedida_sensible_906")

        # 1.04 FIX 958: Despedida prematura sin dato capturado
        # En CAPTURANDO_CONTACTO, NO_INTEREST sin señales negativas claras → GPT_NARROW
        # en vez de despedida. Evita 6 casos de despedida prematura.
        if (intent == FSMIntent.NO_INTEREST and
                self.state == FSMState.CAPTURANDO_CONTACTO and
                not getattr(self.context, 'catalogo_prometido', False)):
            _negativos_958 = [
                'no me interesa', 'no nos interesa', 'no gracias', 'no, gracias',
                'no quiero', 'no queremos', 'no necesito', 'no necesitamos',
                'no por el momento', 'no lo necesito', 'quitenos', 'quiteme',
                'no le interesa', 'no lo necesita',
            ]
            if not any(n in _texto_lower for n in _negativos_958):
                # No hay señal negativa clara → dejar que GPT decida
                print(f"  [FIX 958] NO_INTEREST sin señal negativa en CAPTURANDO_CONTACTO -> GPT_NARROW (anti-despedida-prematura)")
                intent = FSMIntent.UNKNOWN  # GPT_NARROW via UNKNOWN catch-all

        # 1.5. Recovery: DESPEDIDA + CONFIRMATION cuando último fue ofrecer contacto
        if (self.state == FSMState.DESPEDIDA and
                intent == FSMIntent.CONFIRMATION and
                self.context.ultimo_fue_ofrecer_contacto):
            transition = Transition(
                next_state=FSMState.DESPEDIDA,
                action_type=ActionType.TEMPLATE,
                template_key="dictar_numero_bruce",
            )
        # FIX 971: Recovery DESPEDIDA → cliente reabre después de rechazo previo
        # "Espere, mejor mándelo al otro número" / "Sí, mándelo de todos modos"
        elif (self.state == FSMState.DESPEDIDA and
                intent in (FSMIntent.INTEREST, FSMIntent.CONFIRMATION, FSMIntent.UNKNOWN) and
                not any(k in self.context.templates_usados
                        for k in ('confirmar_telefono', 'confirmar_correo', 'confirmar_dato_generico'))):
            _reopen_signals_971 = [
                'espere', 'espera', 'un momento', 'mejor si', 'mejor mandelo',
                'mandelo de todos modos', 'si mandelo', 'mandalo', 'a otro numero',
                'al otro numero', 'otro whatsapp', 'otro correo', 'pensandolo bien',
                'si, mandemelo', 'si envielo', 'si mandame', 'al fin si',
                'de acuerdo', 'okay si', 'ok si',
            ]
            if any(s in _texto_lower for s in _reopen_signals_971):
                print(f"  [FIX 971] Reapertura post-DESPEDIDA detectada: '{texto[:40]}' -> CAPTURANDO_CONTACTO")
                self.state = FSMState.CAPTURANDO_CONTACTO
                transition = Transition(
                    next_state=FSMState.CAPTURANDO_CONTACTO,
                    action_type=ActionType.TEMPLATE,
                    template_key="pedir_whatsapp_o_correo",
                )
            else:
                transition = None
        else:
            transition = None

        # FIX 979: PITCH + VERIFICATION + saludo humano → re-pitch (IVR/conmutador)
        # "Si bueno, digame" después de que Bruce habló con IVR = nuevo humano tomó la llamada
        # Sin este fix: PITCH+VERIFICATION → verificacion_aqui_estoy (ambos dicen "Dígame")
        if (transition is None and
                self.state == FSMState.PITCH and
                intent == FSMIntent.VERIFICATION and
                any(s in _texto_lower for s in [
                    'digame', 'diga', 'si bueno', 'bueno si',
                    'si buenas', 'buenas tardes digame', 'buenas dias digame',
                ])):
            print(f"  [FIX 979] PITCH+VERIFICATION+saludo → re-pitch (nuevo humano en llamada)")
            self.state = FSMState.PITCH
            transition = Transition(FSMState.PITCH, ActionType.TEMPLATE, "pitch_inicial")

        # FIX 763: REJECT_DATA dinámico con alternación de canales
        if (transition is None and
                intent == FSMIntent.REJECT_DATA and
                self.state in (FSMState.CAPTURANDO_CONTACTO,
                               FSMState.ENCARGADO_PRESENTE)):
            transition = self._handle_reject_data_763(texto)

        # 2. Buscar transición (si no fue override)
        if transition is None:
            transition = self._lookup(self.state, intent)

        # 3. Si no hay transición -> escalate a CONVERSACION_LIBRE o fallthrough
        if transition is None:
            # Try UNKNOWN catch-all
            transition = self._lookup(self.state, FSMIntent.UNKNOWN)
            if transition is None:
                if FSM_ENABLED == "shadow":
                    print(f"  [FSM SHADOW] state={self.state.value} intent={intent.value} -> NO TRANSITION (fallthrough)")
                return None

        # FIX 791: Para UNKNOWN, intentar template stateful antes de GPT_NARROW
        if (intent == FSMIntent.UNKNOWN and
                transition.action_type == ActionType.GPT_NARROW):
            stateful = self._handle_unknown_stateful(texto)
            if stateful is not None:
                transition = stateful
                print(f"  [FIX 791] UNKNOWN->template stateful: {stateful.template_key} "
                      f"(estado={self.state.value})")
            # else: fallback a GPT_NARROW original (sin cambio)

        # FIX 938-C: OOS audit V2 - Si ya estamos hablando con el encargado y pide callback,
        # usar template "directo" en vez de "¿A qué hora para encontrar al encargado?"
        if (intent == FSMIntent.CALLBACK and
                transition.template_key == 'preguntar_hora_callback' and
                self.state in (FSMState.ENCARGADO_PRESENTE, FSMState.CAPTURANDO_CONTACTO,
                               FSMState.DICTANDO_DATO)):
            transition = Transition(
                next_state=transition.next_state,
                action_type=transition.action_type,
                template_key='preguntar_hora_callback_directo',
            )
            print(f"  [FIX 938-C] Encargado presente + callback -> preguntar_hora_callback_directo")

        # FIX 784: BRUCE2490 - Si callback y cliente YA mencionó hora, confirmar en vez de preguntar
        if (intent == FSMIntent.CALLBACK and
                transition.template_key == 'preguntar_hora_callback'):
            hora_detectada = self._detectar_hora_en_texto_784(texto)
            # FIX 934: También usar hora pre-guardada de MANAGER_ABSENT previo
            if not hora_detectada and self.context.callback_hora:
                hora_detectada = self.context.callback_hora
                print(f"  [FIX 934] Usando hora pre-guardada: '{hora_detectada}'")
            if hora_detectada:
                # FIX 849: Anti-LOOP confirmar_callback - limitar a 1 confirmar_callback específico
                # + 1 genérico; en el 3ro+ ceder a GPT para romper el loop
                if self.context.callback_confirmaciones >= 2:
                    print(f"  [FIX 849] callback_confirmaciones={self.context.callback_confirmaciones} >= 2 -> fallthrough a GPT (anti-loop)")
                    return None
                elif self.context.callback_confirmaciones == 1:
                    # Ya dimos confirmación específica, dar genérica
                    transition = Transition(
                        next_state=transition.next_state,
                        action_type=transition.action_type,
                        template_key='confirmar_callback_generico',
                    )
                    print(f"  [FIX 849] callback_confirmaciones=1 -> confirmar_callback_generico (anti-loop)")
                else:
                    # Primera confirmación: usar hora específica
                    self.context.callback_hora = hora_detectada
                    transition = Transition(
                        next_state=transition.next_state,
                        action_type=transition.action_type,
                        template_key='confirmar_callback',
                    )
                    print(f"  [FIX 784] Cliente ya mencionó hora: '{hora_detectada}' -> confirmar_callback")
            elif self.context.callback_hora_preguntada:
                # FIX 789B: Ya preguntamos hora y cliente da callback vago ("más tarde")
                # -> confirmar genérico en vez de repetir "¿A qué hora?"
                transition = Transition(
                    next_state=transition.next_state,
                    action_type=transition.action_type,
                    template_key='confirmar_callback_generico',
                )
                print(f"  [FIX 789B] Callback hora ya preguntada -> confirmar_callback_generico (anti-loop)")

        # FIX 839: Anti catálogo repetido - si ya prometimos catálogo, no repetirlo
        # BRUCE2550/2546: despedida_catalogo_prometido después de confirmar_telefono duplica "catálogo"
        if (transition.template_key == 'despedida_catalogo_prometido' and
                self.context.catalogo_prometido):
            transition = Transition(
                next_state=transition.next_state,
                action_type=transition.action_type,
                template_key='despedida_cortes',
            )
            print(f"  [FIX 839] Catálogo ya prometido -> despedida_cortes (sin repetir catálogo)")

        # FIX 892A: BRUCE1975 - pedir_contacto_alternativo duplicado en FSM table
        # PITCH→ENCARGADO_AUSENTE y ESPERANDO_TRANSFERENCIA→ENCARGADO_AUSENTE usan mismo template.
        # En 2da entrada a ENCARGADO_AUSENTE usar template alternativo para evitar PREGUNTA_REPETIDA.
        if (transition.template_key == 'pedir_contacto_alternativo' and
                transition.next_state == FSMState.ENCARGADO_AUSENTE):
            self.context.encargado_ausente_veces += 1
            if self.context.encargado_ausente_veces >= 2:
                print(f"  [FIX 892A] pedir_contacto_alternativo #{self.context.encargado_ausente_veces} → pedir_dato_contacto_892 (anti-PREGUNTA_REPETIDA)")
                transition = Transition(
                    next_state=FSMState.ENCARGADO_AUSENTE,
                    action_type=ActionType.TEMPLATE,
                    template_key='pedir_dato_contacto_892',
                )

        # FIX 897: BRUCE2592 - Contacto invertido (cliente pide datos de BRUCE)
        # INTEREST de _pide_contacto_bruce_897 -> redirigir a ofrecer_contacto_bruce
        if (intent == FSMIntent.INTEREST and
                transition.template_key in ('pedir_whatsapp', 'preguntar_encargado', 'pitch_encargado')):
            _tn_897 = _normalize(texto)
            _pide_bruce_897 = [
                'dejame un numero', 'dejarme un numero', 'dejame tu numero',
                'dame tu numero', 'dame tu telefono', 'pasame tu numero',
                'pasame tus datos', 'dame tus datos', 'me das tu numero',
                'me dejas tu numero', 'me pasas tu numero', 'si gustas dejarme',
            ]
            if any(p in _tn_897 for p in _pide_bruce_897):
                transition = Transition(
                    next_state=FSMState.OFRECIENDO_CONTACTO,
                    action_type=ActionType.TEMPLATE,
                    template_key='ofrecer_contacto_bruce',
                )
                print(f'  [FIX 897] Contacto invertido detectado -> ofrecer_contacto_bruce')

        # FIX 785/860: BRUCE2492/2497/2462 - No repetir pregunta encargado si ya se preguntó
        # FIX 785: solo bloqueaba 'preguntar_encargado'
        # FIX 860: extiende a pitch_inicial + identificacion_pitch
        # FIX 860B: pitch_persona_nueva bloqueado para intents no-IDENTITY (BRUCE2462:
        #   esperando_transferencia+QUESTION → pitch_persona_nueva repite "¿Se encontrará encargado?")
        #   IDENTITY se permite (nueva persona que no ha oído el pitch)
        _PITCH_TEMPLATES_CON_ENCARGADO_Q = {
            'preguntar_encargado', 'pitch_inicial', 'identificacion_pitch',
        }
        _block_encargado_q = (
            (transition.template_key in _PITCH_TEMPLATES_CON_ENCARGADO_Q) or
            (transition.template_key == 'pitch_persona_nueva' and
             intent != FSMIntent.IDENTITY)
        )
        if _block_encargado_q and self.context.encargado_preguntado:
            # Ya preguntamos por encargado -> usar acknowledgment genérico
            _orig_template_860 = transition.template_key
            self.context.verificacion_consecutivas += 1
            # FIX 866B: BRUCE2322 - Anti-LOOP verificacion_aqui_estoy repetida post-transfer
            # Después de 3+ usos consecutivos → ofrecer_contacto_bruce para salir del loop
            if self.context.verificacion_consecutivas >= 3:
                _veri_template = 'ofrecer_contacto_bruce'
                _veri_state = FSMState.OFRECIENDO_CONTACTO
                print(f"  [FIX 866B] verificacion_consecutivas={self.context.verificacion_consecutivas} >= 3 -> ofrecer_contacto_bruce (anti-LOOP)")
            else:
                _veri_template = 'verificacion_aqui_estoy'
                _veri_state = transition.next_state
            transition = Transition(
                next_state=_veri_state,
                action_type=transition.action_type,
                template_key=_veri_template,
            )
            print(f"  [FIX 785/860] Encargado ya preguntado -> no repetir ({_orig_template_860}), usando {_veri_template}")

        # FIX 855+856: BRUCE2522 - Anti-LOOP preguntas de producto repetidas
        # Cliente pregunta "¿Qué tipo de productos manejan?" 10+ veces → GPT genera misma respuesta → LOOP
        # Después de 2 respuestas de producto, redirigir a captura de contacto
        # FIX 856: Escalación progresiva para evitar LOOP + PREGUNTA_REPETIDA
        #   - 3ra pregunta: pedir_whatsapp_o_correo
        #   - 4ta pregunta: ofrecer_contacto_bruce
        #   - 5ta+: despedida_cortes (cliente claramente no coopera)
        # FIX 861: BRUCE2454/2441 - Si WhatsApp ya fue solicitado, saltar directo a ofrecer_contacto_bruce
        if (transition.template_key == 'responder_pregunta_producto' and
                self.context.preguntas_producto_respondidas >= 2):
            # FIX 856: Incrementar aquí porque _update_context no lo verá (template cambia)
            self.context.preguntas_producto_respondidas += 1
            redirect_n = self.context.preguntas_producto_respondidas - 2  # 1=primera, 2=segunda, 3+=tercera+

            if redirect_n <= 1:
                # FIX 861: si WhatsApp ya se pidió, saltar a ofrecer_contacto_bruce (evita PREGUNTA_REPETIDA)
                if self.context.whatsapp_ya_solicitado:
                    new_template = 'ofrecer_contacto_bruce'
                    new_state = FSMState.OFRECIENDO_CONTACTO
                    print(f"  [FIX 861] WhatsApp ya solicitado → saltar pedir_whatsapp → ofrecer_contacto_bruce")
                else:
                    new_template = 'pedir_whatsapp_o_correo'
                    new_state = FSMState.CAPTURANDO_CONTACTO
            elif redirect_n == 2:
                new_template = 'ofrecer_contacto_bruce'
                new_state = FSMState.OFRECIENDO_CONTACTO
            else:
                new_template = 'despedida_cortes'
                new_state = FSMState.DESPEDIDA

            print(f"  [FIX 856] Pregunta producto #{self.context.preguntas_producto_respondidas} → escalation {redirect_n} → {new_template}")
            transition = Transition(
                next_state=new_state,
                action_type=ActionType.TEMPLATE,
                template_key=new_template,
            )

        # 4. Evaluar guards
        if not self._check_guards(transition.guards):
            if FSM_ENABLED == "shadow":
                print(f"  [FSM SHADOW] state={self.state.value} intent={intent.value} -> GUARDS FAILED (fallthrough)")
            return None

        # 4B. FIX 908: Guard de despedida prematura
        # No despedir si: estamos en pitch/buscando_encargado, turnos < 2, y no hay rechazo firme
        if (transition.next_state == FSMState.DESPEDIDA
                and self.state in (FSMState.PITCH, FSMState.BUSCANDO_ENCARGADO, FSMState.ENCARGADO_PRESENTE)
                and self.context.turnos_bruce < 2
                and intent not in (FSMIntent.NO_INTEREST, FSMIntent.FAREWELL, FSMIntent.WRONG_NUMBER,
                                  FSMIntent.ANOTHER_BRANCH, FSMIntent.CLOSED)):
            print(f"  [FIX 908] Guard despedida prematura: turnos={self.context.turnos_bruce} state={self.state.value} -> continuar conversacion")
            # En vez de despedir, intentar ofrecer catalogo
            transition = Transition(
                next_state=self.state,
                action_type=ActionType.TEMPLATE,
                template_key="ofrecer_catalogo_sin_compromiso",
            )

        # 4C. FIX 924: Guard de datos faltantes antes de despedida
        # Si estamos en estados avanzados y no capturamos ningun dato, intentar una ultima vez
        if (transition.next_state == FSMState.DESPEDIDA
                and self.state in (FSMState.ENCARGADO_PRESENTE, FSMState.CAPTURANDO_CONTACTO)
                and intent == FSMIntent.FAREWELL
                and not self.context.whatsapp_ya_solicitado
                and not self.context.catalogo_prometido
                and self.context.turnos_bruce >= 2):
            print(f"  [FIX 924] Guard datos faltantes: encargado presente pero sin datos -> ofrecer catalogo")
            transition = Transition(
                next_state=FSMState.CAPTURANDO_CONTACTO,
                action_type=ActionType.TEMPLATE,
                template_key="ofrecer_catalogo_sin_compromiso",
            )

        # 4D. FIX 1009: No despedir si estamos en PITCH y nunca se intentó capturar contacto
        # (FSM clasifica "Entiendo"/"OK" como FAREWELL antes de que Bruce pida datos)
        if (transition.next_state == FSMState.DESPEDIDA
                and self.state == FSMState.PITCH
                and intent == FSMIntent.FAREWELL
                and not self.context.catalogo_prometido
                and self.context.pedir_datos_count == 0
                and self.context.turnos_bruce >= 2):
            print(f"  [FIX 1009] Despedida prematura en PITCH sin captura intentada "
                  f"(turnos={self.context.turnos_bruce}) -> pedir_whatsapp_o_correo")
            transition = Transition(
                next_state=FSMState.CAPTURANDO_CONTACTO,
                action_type=ActionType.TEMPLATE,
                template_key="pedir_whatsapp_o_correo",
            )

        # 5. Ejecutar acción
        response = self._execute(transition, texto, agente)

        # 6. Actualizar estado y contexto (SIEMPRE, incluyendo shadow mode)
        prev_state = self.state
        self.state = transition.next_state
        self._update_context(intent, texto, transition, agente)

        # 7. Decidir: shadow, phase2 (selective), o full active
        is_state_active = prev_state in FSM_ACTIVE_STATES_SET

        if FSM_ENABLED == "shadow" and not is_state_active:
            # Pure shadow: log only, no intercept
            print(f"  [FSM SHADOW] state={prev_state.value} intent={intent.value} "
                  f"-> next={self.state.value} action={transition.action_type.value} "
                  f"template={transition.template_key} response='{(response or '')[:60]}'")
            return None

        if FSM_ENABLED == "shadow" and is_state_active:
            # Phase 2: state is in active set -> intercept
            # Skip HANGUP/NOOP (let existing code handle closing)
            if transition.action_type in (ActionType.HANGUP, ActionType.NOOP):
                print(f"  [FSM PHASE2] state={prev_state.value} intent={intent.value} "
                      f"-> {transition.action_type.value} (fallthrough - let existing code handle)")
                return None
            if response:
                print(f"  [FSM PHASE2] state={prev_state.value} intent={intent.value} "
                      f"-> next={self.state.value} INTERCEPTING: '{response[:60]}'")
                return response
            # Empty response -> shadow
            print(f"  [FSM SHADOW] state={prev_state.value} (active but empty response)")
            return None

        # Full active mode
        print(f"  [FSM] {prev_state.value} + {intent.value} -> {self.state.value} "
              f"({transition.action_type.value}:{transition.template_key})")

        return response

    # ----------------------------------------------------------
    # FIX 918: Extracción de datos mencionados por el cliente
    # ----------------------------------------------------------
    def _extraer_datos_cliente(self, texto: str):
        """FIX 918: Extrae datos que el cliente menciona y los guarda en datos_capturados.

        Detecta: tipo de negocio, nombre del encargado, relación previa, productos que manejan.
        Estos datos se inyectan en el prompt GPT para que Bruce no los ignore.
        """
        tn = texto.lower().strip()

        # Tipo de negocio
        tipos_negocio = {
            'ferreteria': 'ferretería', 'taller': 'taller', 'papeleria': 'papelería',
            'tienda': 'tienda', 'abarrotes': 'abarrotes', 'refaccionaria': 'refaccionaria',
            'electrica': 'eléctrica', 'plomeria': 'plomería', 'construccion': 'construcción',
            'materiales': 'materiales', 'herreria': 'herrería', 'cerrajeria': 'cerrajería',
            'muebleria': 'mueblería', 'dulceria': 'dulcería', 'farmacia': 'farmacia',
            'restaurante': 'restaurante', 'hotel': 'hotel', 'escuela': 'escuela',
            'fabrica': 'fábrica', 'tlapaleria': 'tlapalería', 'tornilleria': 'tornillería',
        }
        for key, display in tipos_negocio.items():
            if key in tn and 'tipo_negocio' not in self.context.datos_capturados:
                self.context.datos_capturados['tipo_negocio'] = display
                print(f"  [FIX 918] Dato extraído: tipo_negocio={display}")
                break

        # Relación previa con NIOVAL
        relacion_previa = [
            'ya nos conocemos', 'ya les compre', 'ya les compré', 'ya he comprado',
            'ya soy cliente', 'ya nos han llamado', 'ya conozco', 'ya los conozco',
            'ya trabaje con ustedes', 'ya trabajé con ustedes', 'si los conozco',
        ]
        for frase in relacion_previa:
            if frase in tn and 'relacion_previa' not in self.context.datos_capturados:
                self.context.datos_capturados['relacion_previa'] = 'cliente_existente'
                print(f"  [FIX 918] Dato extraído: relacion_previa=cliente_existente")
                break

        # Productos que manejan/buscan
        productos = [
            'herramienta', 'tornillo', 'clavo', 'pintura', 'cable', 'tubo',
            'llave', 'candado', 'cerradura', 'foco', 'lampara', 'lámpara',
            'cinta', 'pegamento', 'soldadura', 'taladro', 'sierra',
        ]
        for prod in productos:
            if prod in tn and 'producto_mencionado' not in self.context.datos_capturados:
                self.context.datos_capturados['producto_mencionado'] = prod
                print(f"  [FIX 918] Dato extraído: producto_mencionado={prod}")
                break

        # Nombre del encargado (cuando dicen "soy [nombre]" o "habla [nombre]")
        import re
        match_nombre = re.search(r'(?:soy|habla|me llamo|mi nombre es)\s+([A-Za-záéíóúñÁÉÍÓÚÑ]{3,})', texto)
        if match_nombre and 'nombre_encargado' not in self.context.datos_capturados:
            nombre = match_nombre.group(1).capitalize()
            # Filtrar palabras que NO son nombres
            _no_nombres = {'el', 'la', 'los', 'las', 'del', 'que', 'con', 'para', 'por', 'encargado', 'encargada', 'dueno', 'dueño'}
            if nombre.lower() not in _no_nombres and len(nombre) >= 3:
                self.context.datos_capturados['nombre_encargado'] = nombre
                print(f"  [FIX 918] Dato extraído: nombre_encargado={nombre}")

        # FIX 959: Detectar preferencia de canal correo/email del cliente
        _correo_prefer_patterns_959 = [
            'al correo', 'por correo', 'al email', 'por email', 'al mail', 'via correo',
            'mandeme al correo', 'enviame al correo', 'correo mejor', 'mejor al correo',
            'prefiero correo', 'prefiero el correo', 'mejor correo', 'correo electronico',
        ]
        if any(p in tn for p in _correo_prefer_patterns_959):
            self.context.datos_capturados['prefiere_correo_959'] = True
            print(f"  [FIX 959] Preferencia correo detectada en texto del cliente")

        # FIX 923: Detectar tono del cliente (informal vs formal)
        _informal_markers = [
            'orale', 'va que va', 'chido', 'simon', 'nel', 'neta', 'mano',
            'compa', 'carnal', 'wey', 'guey', 'nomas', 'pos', 'pues si',
            'arre', 'sale', 'jalo', 'va pues', 'andale', 'hijole',
        ]
        _formal_markers = [
            'por favor', 'disculpe', 'seria tan amable', 'con su permiso',
            'le agradezco', 'buenas tardes', 'buenos dias', 'buenas noches',
            'tenga usted', 'estaria interesado',
        ]
        if 'tono_cliente' not in self.context.datos_capturados:
            if any(m in tn for m in _informal_markers):
                self.context.datos_capturados['tono_cliente'] = 'informal'
                print(f"  [FIX 923] Tono detectado: informal")
            elif any(m in tn for m in _formal_markers):
                self.context.datos_capturados['tono_cliente'] = 'formal'
                print(f"  [FIX 923] Tono detectado: formal")

    # ----------------------------------------------------------
    # FIX 791: Selección stateful de template para UNKNOWN
    # ----------------------------------------------------------
    def _handle_unknown_stateful(self, texto: str) -> Optional[Transition]:
        """FIX 791: Selecciona template basado en estado + contexto para UNKNOWN.

        Reemplaza GPT_NARROW en 90%+ de casos UNKNOWN.
        Retorna Transition con template o None para fallback a GPT_NARROW.
        Actualiza context flags para evitar loops por template repetido.
        FIX 907: Verifica si template ya se dijo para evitar PREGUNTA_REPETIDA.
        FIX 910: Contador de repeticiones para evitar LOOP.
        """
        S = FSMState
        A = ActionType
        ctx = self.context

        def _template_ya_dicho(template_key: str) -> bool:
            """FIX 907: Verifica si este template ya se usó en la conversación."""
            return template_key in ctx.templates_usados

        def _registrar_template(template_key: str):
            """FIX 907/910: Registra template usado y cuenta repeticiones."""
            ctx.templates_usados.add(template_key)
            ctx.template_repeat_count = ctx.template_repeat_count + 1

        def _seleccionar_template(opciones: list) -> Optional[Transition]:
            """FIX 907: Selecciona el primer template NO usado de la lista.
            FIX 910: Si todos usados (>= 3 repeticiones), escalar a GPT o despedida."""
            for next_state, action, tpl in opciones:
                if not _template_ya_dicho(tpl):
                    _registrar_template(tpl)
                    return Transition(next_state, action, tpl)
            # FIX 910: Todos los templates ya se dijeron -> LOOP detectado
            if ctx.template_repeat_count >= 3:
                print(f"  [FIX 910] LOOP detectado: {ctx.template_repeat_count} templates repetidos -> escalar a GPT")
                return None  # Fallback a GPT_NARROW
            # Usar el primero como fallback
            ns, ac, tpl = opciones[0]
            return Transition(ns, ac, tpl)

        # FIX 909: Si ya pidió datos 3+ veces sin éxito, escalar a ofrecer contacto Bruce
        if ctx.pedir_datos_count >= 3:
            print(f"  [FIX 909] LOOP detectado: {ctx.pedir_datos_count} pedidos de datos sin exito -> ofrecer contacto Bruce")
            if not _template_ya_dicho("ofrecer_contacto_bruce"):
                _registrar_template("ofrecer_contacto_bruce")
                return Transition(S.OFRECIENDO_CONTACTO, A.TEMPLATE, "ofrecer_contacto_bruce")
            else:
                return Transition(S.DESPEDIDA, A.TEMPLATE, "despedida_cortes")

        # FIX 918: Detección de confusión - si cliente parece confundido, aclarar
        tn = _normalize(texto)
        # Only exact or near-exact matches to avoid false positives like "como le digo"
        _confusion_918_exact = ['no entiendo', 'no le entendi', 'no entendi',
                                'a que se refiere', 'de que se trata',
                                'no se de que', 'no se de que me habla']
        _confusion_918_substring = ['que quiere decir', 'que quieren decir', 'no comprendo']
        _is_confused = (tn in _confusion_918_exact or
                        any(c in tn for c in _confusion_918_substring) or
                        any(tn.startswith(c) for c in _confusion_918_exact))
        if _is_confused and len(tn) < 30:
            ctx.confusion_count += 1
            if ctx.confusion_count <= 2 and not _template_ya_dicho("aclarar_confusion"):
                _registrar_template("aclarar_confusion")
                print(f"  [FIX 918] Confusion detectada (#{ctx.confusion_count}): '{texto[:40]}' -> aclarar_confusion")
                return Transition(self.state, A.TEMPLATE, "aclarar_confusion")

        # FIX 933: BRUCE2457 - Texto STT incompleto/garbled = cliente sigue hablando
        # "Pero yo le yo le he visto No, es que el yo no me lo" → incompleto (termina en "lo")
        # Heuristic: si el texto es largo (>20 chars), tiene repeticiones STT, y termina sin
        # puntuación ni patrón de cierre → probablemente incompleto, esperar más input
        _ends_incomplete_933 = (
            len(tn) > 20 and
            not any(tn.endswith(p) for p in ('.', '?', '!', 'gracias', 'adios', 'bye')) and
            (tn.count(' yo ') >= 2 or tn.count(' le ') >= 2 or  # STT stutter/repeat
             tn.endswith(' lo') or tn.endswith(' el') or tn.endswith(' la') or
             tn.endswith(' me') or tn.endswith(' le') or tn.endswith(' de') or
             tn.endswith(' que') or tn.endswith(' no') or tn.endswith(' es'))
        )
        if _ends_incomplete_933:
            print(f"  [FIX 933] Texto incompleto detectado: '{texto[:50]}...' -> NOOP (esperar)")
            return Transition(self.state, A.NOOP, None)

        # FIX 921: Rechazo ambiguo - "no" corto en estados tempranos = ambiguo
        # ¿No está el encargado? ¿No le interesa? Aclarar antes de asumir
        _ambiguous_no_921 = ('no', 'no no', 'mmm no', 'pues no')
        if (tn in _ambiguous_no_921
                and self.state in (S.SALUDO, S.PITCH)
                and not ctx.encargado_preguntado
                and not _template_ya_dicho("aclarar_rechazo_ambiguo")):
            _registrar_template("aclarar_rechazo_ambiguo")
            print(f"  [FIX 921] Rechazo ambiguo en {self.state.value}: '{texto}' -> aclarar_rechazo_ambiguo")
            return Transition(self.state, A.TEMPLATE, "aclarar_rechazo_ambiguo")

        if self.state == S.PITCH:
            opciones_pitch = [x for x in [
                (S.BUSCANDO_ENCARGADO, A.TEMPLATE, "preguntar_encargado") if not ctx.encargado_preguntado else None,
                (S.CAPTURANDO_CONTACTO, A.TEMPLATE, "pedir_whatsapp_o_correo") if not ctx.canales_intentados else None,
                (S.CAPTURANDO_CONTACTO, A.TEMPLATE, "ofrecer_catalogo_sin_compromiso"),
            ] if x is not None]
            return _seleccionar_template(opciones_pitch)

        elif self.state == S.BUSCANDO_ENCARGADO:
            opciones = []
            if not ctx.pitch_dado:
                opciones.append((S.BUSCANDO_ENCARGADO, A.TEMPLATE, "repitch_encargado"))
            if ctx.encargado_preguntado:
                opciones.append((S.CAPTURANDO_CONTACTO, A.TEMPLATE, "pedir_whatsapp_o_correo"))
                opciones.append((S.CAPTURANDO_CONTACTO, A.TEMPLATE, "pedir_whatsapp_o_correo_breve"))
            else:
                opciones.append((S.BUSCANDO_ENCARGADO, A.TEMPLATE, "preguntar_encargado"))
            if not opciones:
                opciones.append((S.BUSCANDO_ENCARGADO, A.TEMPLATE, "preguntar_encargado"))
            return _seleccionar_template(opciones)

        elif self.state == S.ENCARGADO_AUSENTE:
            # FIX 938-I: OOS audit V2 - Cliente ofrece dejar recado
            # "Yo le dejo el recado" / "Le aviso" / "Le digo que llamo" → aceptar + pedir WA
            _recado_patterns_938 = [
                'dejo el recado', 'le aviso', 'le digo que llamo',
                'le paso el recado', 'darle razon', 'puedo darle razon',
                'le doy razon', 'yo le aviso', 'le comento',
                'le digo que llamo', 'le menciono',
            ]
            if (any(r in tn for r in _recado_patterns_938) and
                    not _template_ya_dicho("aceptar_recado_pedir_wa")):
                _registrar_template("aceptar_recado_pedir_wa")
                print(f"  [FIX 938-I] Oferta de recado detectada: '{texto[:40]}' -> aceptar_recado_pedir_wa")
                return Transition(S.ENCARGADO_AUSENTE, A.TEMPLATE, "aceptar_recado_pedir_wa")

            if not ctx.canales_intentados:
                if ctx.identity_repetidas >= 2:
                    print(f"  [FIX 891] UNKNOWN en encargado_ausente + identity_repetidas={ctx.identity_repetidas} → pedir_telefono_directo_891")
                    return Transition(S.CAPTURANDO_CONTACTO, A.TEMPLATE, "pedir_telefono_directo_891")
                # FIX 1010: Si encargado ya se identificó, usar template neutro (no callback template)
                _tmpl_885_1010 = (
                    "pedir_numero_directo_885"
                    if not ctx.encargado_identificado
                    else "pedir_whatsapp_o_correo"
                )
                opciones = [
                    (S.CAPTURANDO_CONTACTO, A.TEMPLATE, "pedir_whatsapp_o_correo"),
                    (S.CAPTURANDO_CONTACTO, A.TEMPLATE, "pedir_whatsapp_o_correo_breve"),
                    (S.CAPTURANDO_CONTACTO, A.TEMPLATE, _tmpl_885_1010),
                ]
                return _seleccionar_template(opciones)
            elif ctx.callback_pedido:
                return Transition(S.DESPEDIDA, A.TEMPLATE, "despedida_agradecimiento")
            else:
                opciones = [
                    (S.ENCARGADO_AUSENTE, A.TEMPLATE, "preguntar_horario_encargado"),
                    (S.OFRECIENDO_CONTACTO, A.TEMPLATE, "ofrecer_contacto_bruce"),
                ]
                return _seleccionar_template(opciones)

        elif self.state == S.ENCARGADO_PRESENTE:
            if not ctx.canales_intentados:
                opciones = [
                    (S.CAPTURANDO_CONTACTO, A.TEMPLATE, "pedir_whatsapp"),
                    (S.CAPTURANDO_CONTACTO, A.TEMPLATE, "pedir_whatsapp_o_correo_breve"),
                ]
                return _seleccionar_template(opciones)
            else:
                return Transition(S.CAPTURANDO_CONTACTO, A.TEMPLATE, "pitch_catalogo_whatsapp")

        elif self.state == S.CAPTURANDO_CONTACTO:
            # FIX 970: Si cliente hace pregunta calificadora, dejar que GPT responda
            # (no forzar "digame_numero" cuando el cliente pregunta sobre el producto/servicio)
            _pregunta_calificadora_970 = (
                '?' in texto or
                any(qw in tn for qw in [
                    'cuanto', 'cuantos', 'cuanta', 'cuantas', 'como es', 'como son',
                    'que lineas', 'que productos', 'que categorias', 'que marcas',
                    'manejan', 'tienen', 'dan credito', 'dan descuento', 'descuento',
                    'credito', 'cuanto tarda', 'tiempo de entrega', 'a donde', 'desde donde',
                    'de donde son', 'donde estan', 'tienen sucursal', 'fabricantes',
                    'distribuidores', 'precio', 'precios', 'cuanto cuesta', 'cuanto vale',
                ])
            )
            if _pregunta_calificadora_970:
                print(f"  [FIX 970] CAPTURANDO_CONTACTO pregunta calificadora detectada: '{texto[:50]}' -> GPT_NARROW")
                return None  # Fallback a GPT para responder la pregunta

            # FIX 909: Si ya pidió datos muchas veces, escalar
            if ctx.pedir_datos_count >= 3:
                print(f"  [FIX 909] CAPTURANDO_CONTACTO: {ctx.pedir_datos_count} pedidos -> ofrecer contacto Bruce")
                return Transition(S.OFRECIENDO_CONTACTO, A.TEMPLATE, "ofrecer_contacto_bruce")
            opciones = [
                (S.CAPTURANDO_CONTACTO, A.TEMPLATE, "digame_numero"),
                (S.CAPTURANDO_CONTACTO, A.TEMPLATE, "no_escuche_repetir"),
            ]
            return _seleccionar_template(opciones)

        elif self.state == S.ESPERANDO_TRANSFERENCIA:
            # FIX 911: En espera de transferencia, confirmar presencia
            return Transition(S.ESPERANDO_TRANSFERENCIA, A.TEMPLATE, "verificacion_aqui_estoy")

        elif self.state == S.OFRECIENDO_CONTACTO:
            # FIX 922: Ofrecer dictar numero de Bruce directamente
            if not _template_ya_dicho("dictar_numero_bruce"):
                _registrar_template("dictar_numero_bruce")
                return Transition(S.OFRECIENDO_CONTACTO, A.TEMPLATE, "dictar_numero_bruce")
            return Transition(S.DESPEDIDA, A.TEMPLATE, "despedida_cortes")

        # Estados no mapeados -> None -> fallback a GPT_NARROW existente
        return None

    # ----------------------------------------------------------
    # Tabla de transiciones
    # ----------------------------------------------------------
    def _build_transitions(self) -> Dict[Tuple[FSMState, FSMIntent], Transition]:
        """Construye la tabla de transiciones completa."""
        T = {}

        def add(state, intent, next_state, action, template=None, guards=None):
            T[(state, intent)] = Transition(
                next_state=next_state,
                action_type=action,
                template_key=template,
                guards=guards or [],
            )

        S = FSMState
        I = FSMIntent
        A = ActionType

        # === SALUDO ===
        add(S.SALUDO, I.CONFIRMATION,  S.PITCH, A.TEMPLATE, "pitch_inicial")
        add(S.SALUDO, I.INTEREST,      S.PITCH, A.TEMPLATE, "pitch_inicial")
        add(S.SALUDO, I.VERIFICATION,  S.PITCH, A.TEMPLATE, "pitch_inicial")
        add(S.SALUDO, I.QUESTION,      S.PITCH, A.TEMPLATE, "identificacion_pitch")
        add(S.SALUDO, I.IDENTITY,      S.PITCH, A.TEMPLATE, "identificacion_pitch")
        # FIX 920: Explorar antes de despedida (OPORTUNIDAD_PERDIDA)
        add(S.SALUDO, I.NO_INTEREST,   S.DESPEDIDA, A.TEMPLATE, "despedida_no_interesa")
        add(S.SALUDO, I.FAREWELL,      S.DESPEDIDA, A.TEMPLATE, "despedida_cortes")
        add(S.SALUDO, I.WRONG_NUMBER,  S.DESPEDIDA, A.TEMPLATE, "despedida_area_equivocada")
        add(S.SALUDO, I.OFFER_DATA,    S.DICTANDO_DATO, A.ACKNOWLEDGE, "aja_digame")
        add(S.SALUDO, I.MANAGER_PRESENT, S.ENCARGADO_PRESENTE, A.TEMPLATE, "pitch_encargado")
        add(S.SALUDO, I.MANAGER_ABSENT, S.ENCARGADO_AUSENTE, A.TEMPLATE, "pedir_contacto_alternativo")
        add(S.SALUDO, I.UNKNOWN,       S.PITCH, A.TEMPLATE, "pitch_inicial")
        # FIX 894: New intents - identity question + what_offer
        add(S.SALUDO, I.IDENTITY_QUESTION, S.PITCH, A.TEMPLATE, "identificacion_pitch")
        add(S.SALUDO, I.WHAT_OFFER,        S.PITCH, A.TEMPLATE, "pitch_completo_894")
        # FIX 786: CONTINUATION - cliente sigue hablando, no interrumpir
        add(S.SALUDO, I.CONTINUATION,  S.SALUDO, A.NOOP, None)
        # FIX 1046: SALUDO + TRANSFER → ESPERANDO_TRANSFERENCIA (antes: no entry → GPT da pitch)
        # "Un momento, le transfiero la llamada" en primer turno = cliente pasa a encargado
        add(S.SALUDO, I.TRANSFER, S.ESPERANDO_TRANSFERENCIA, A.TEMPLATE, "claro_espero")

        # === PITCH ===
        # FIX 985: PITCH + CONFIRMATION → ENCARGADO_PRESENTE (no BUSCANDO_ENCARGADO)
        # pitch_inicial siempre termina con "¿Se encontrará el encargado?" →
        # cliente dice "Sí" = manager presente → ir directo a captura contacto.
        # ANTES: BUSCANDO_ENCARGADO + "preguntar_encargado" → pregunta REPETIDA (BRUCE2527)
        add(S.PITCH, I.CONFIRMATION,   S.ENCARGADO_PRESENTE, A.TEMPLATE, "pitch_encargado")
        add(S.PITCH, I.INTEREST,       S.BUSCANDO_ENCARGADO, A.TEMPLATE, "preguntar_encargado")
        add(S.PITCH, I.QUESTION,       S.PITCH, A.GPT_NARROW, "responder_pregunta_producto")
        add(S.PITCH, I.IDENTITY,       S.PITCH, A.TEMPLATE, "identificacion_nioval")
        add(S.PITCH, I.NO_INTEREST,    S.DESPEDIDA, A.TEMPLATE, "despedida_no_interesa")
        add(S.PITCH, I.FAREWELL,       S.DESPEDIDA, A.TEMPLATE, "despedida_cortes")
        add(S.PITCH, I.WRONG_NUMBER,   S.DESPEDIDA, A.TEMPLATE, "despedida_area_equivocada")
        add(S.PITCH, I.MANAGER_ABSENT, S.ENCARGADO_AUSENTE, A.TEMPLATE, "pedir_contacto_alternativo")
        add(S.PITCH, I.MANAGER_PRESENT, S.ENCARGADO_PRESENTE, A.TEMPLATE, "pitch_encargado")
        add(S.PITCH, I.OFFER_DATA,     S.DICTANDO_DATO, A.ACKNOWLEDGE, "aja_digame")
        add(S.PITCH, I.TRANSFER,       S.ESPERANDO_TRANSFERENCIA, A.TEMPLATE, "claro_espero")
        add(S.PITCH, I.CALLBACK,       S.ENCARGADO_AUSENTE, A.TEMPLATE, "preguntar_hora_callback")
        add(S.PITCH, I.ANOTHER_BRANCH, S.DESPEDIDA, A.TEMPLATE, "despedida_otra_sucursal")
        add(S.PITCH, I.CLOSED,         S.DESPEDIDA, A.TEMPLATE, "despedida_cerrado")
        add(S.PITCH, I.VERIFICATION,   S.PITCH, A.TEMPLATE, "verificacion_aqui_estoy")
        add(S.PITCH, I.REJECT_DATA,    S.DESPEDIDA, A.TEMPLATE, "despedida_no_interesa")
        # FIX 754: Cliente dicta teléfono/email completo durante pitch -> capturar
        add(S.PITCH, I.DICTATING_COMPLETE_PHONE, S.CONTACTO_CAPTURADO, A.TEMPLATE, "confirmar_telefono")
        add(S.PITCH, I.DICTATING_COMPLETE_EMAIL, S.CONTACTO_CAPTURADO, A.TEMPLATE, "confirmar_correo")
        add(S.PITCH, I.DICTATING_PARTIAL,        S.DICTANDO_DATO, A.ACKNOWLEDGE, "aja_si")
        # FIX 894: New intents for PITCH
        add(S.PITCH, I.IDENTITY_QUESTION, S.PITCH, A.TEMPLATE, "identificacion_nioval")
        add(S.PITCH, I.WHAT_OFFER,        S.BUSCANDO_ENCARGADO, A.TEMPLATE, "pitch_y_encargado_894")
        # FIX 789A: UNKNOWN durante pitch -> GPT narrow con manejar_objecion
        # (antes: blindly avanzaba a preguntar_encargado)
        add(S.PITCH, I.UNKNOWN,        S.PITCH, A.GPT_NARROW, "manejar_objecion")
        # FIX 786: CONTINUATION - cliente sigue hablando
        add(S.PITCH, I.CONTINUATION,  S.PITCH, A.NOOP, None)

        # === BUSCANDO_ENCARGADO ===
        add(S.BUSCANDO_ENCARGADO, I.CONFIRMATION,    S.BUSCANDO_ENCARGADO, A.TEMPLATE, "preguntar_encargado")
        add(S.BUSCANDO_ENCARGADO, I.MANAGER_PRESENT, S.ENCARGADO_PRESENTE, A.TEMPLATE, "pitch_encargado")
        add(S.BUSCANDO_ENCARGADO, I.MANAGER_ABSENT,  S.ENCARGADO_AUSENTE, A.TEMPLATE, "pedir_contacto_alternativo")
        add(S.BUSCANDO_ENCARGADO, I.TRANSFER,        S.ESPERANDO_TRANSFERENCIA, A.TEMPLATE, "claro_espero")
        add(S.BUSCANDO_ENCARGADO, I.CALLBACK,        S.ENCARGADO_AUSENTE, A.TEMPLATE, "preguntar_hora_callback")
        add(S.BUSCANDO_ENCARGADO, I.OFFER_DATA,      S.DICTANDO_DATO, A.ACKNOWLEDGE, "aja_digame")
        add(S.BUSCANDO_ENCARGADO, I.QUESTION,        S.BUSCANDO_ENCARGADO, A.GPT_NARROW, "responder_pregunta_producto")
        add(S.BUSCANDO_ENCARGADO, I.IDENTITY,        S.BUSCANDO_ENCARGADO, A.TEMPLATE, "identificacion_nioval")
        add(S.BUSCANDO_ENCARGADO, I.NO_INTEREST,     S.DESPEDIDA, A.TEMPLATE, "despedida_no_interesa")
        add(S.BUSCANDO_ENCARGADO, I.FAREWELL,        S.DESPEDIDA, A.TEMPLATE, "despedida_cortes")
        add(S.BUSCANDO_ENCARGADO, I.WRONG_NUMBER,    S.DESPEDIDA, A.TEMPLATE, "despedida_area_equivocada")
        add(S.BUSCANDO_ENCARGADO, I.ANOTHER_BRANCH,  S.DESPEDIDA, A.TEMPLATE, "despedida_otra_sucursal")
        add(S.BUSCANDO_ENCARGADO, I.CLOSED,          S.DESPEDIDA, A.TEMPLATE, "despedida_cerrado")
        # FIX 916: INTEREST en BUSCANDO_ENCARGADO -> dar pitch primero, NO saltar a pedir WhatsApp
        # Antes: saltaba directo a pedir_whatsapp sin generar interes real
        add(S.BUSCANDO_ENCARGADO, I.INTEREST,        S.ENCARGADO_PRESENTE, A.TEMPLATE, "pitch_encargado")
        add(S.BUSCANDO_ENCARGADO, I.VERIFICATION,    S.BUSCANDO_ENCARGADO, A.TEMPLATE, "verificacion_aqui_estoy")
        # FIX 894: New intents for BUSCANDO_ENCARGADO
        add(S.BUSCANDO_ENCARGADO, I.IDENTITY_QUESTION, S.BUSCANDO_ENCARGADO, A.TEMPLATE, "identificacion_nioval")
        add(S.BUSCANDO_ENCARGADO, I.WHAT_OFFER,        S.ENCARGADO_PRESENTE, A.TEMPLATE, "pitch_y_encargado_894")
        add(S.BUSCANDO_ENCARGADO, I.REJECT_DATA,     S.OFRECIENDO_CONTACTO, A.TEMPLATE, "ofrecer_contacto_bruce")
        # FIX 754: Cliente dicta teléfono/email completo buscando encargado -> capturar
        add(S.BUSCANDO_ENCARGADO, I.DICTATING_COMPLETE_PHONE, S.CONTACTO_CAPTURADO, A.TEMPLATE, "confirmar_telefono")
        add(S.BUSCANDO_ENCARGADO, I.DICTATING_COMPLETE_EMAIL, S.CONTACTO_CAPTURADO, A.TEMPLATE, "confirmar_correo")
        add(S.BUSCANDO_ENCARGADO, I.DICTATING_PARTIAL,        S.DICTANDO_DATO, A.ACKNOWLEDGE, "aja_si")
        add(S.BUSCANDO_ENCARGADO, I.UNKNOWN,         S.BUSCANDO_ENCARGADO, A.GPT_NARROW, "conversacion_libre")
        # FIX 786: CONTINUATION - cliente sigue hablando
        add(S.BUSCANDO_ENCARGADO, I.CONTINUATION,  S.BUSCANDO_ENCARGADO, A.NOOP, None)
        # FIX 1046: BUSCANDO_ENCARGADO + TRANSFER → ESPERANDO_TRANSFERENCIA
        add(S.BUSCANDO_ENCARGADO, I.TRANSFER, S.ESPERANDO_TRANSFERENCIA, A.TEMPLATE, "claro_espero")

        # === ENCARGADO_PRESENTE ===
        # FIX 916B: Solo pedir WhatsApp si ya se dio pitch completo
        # Si pitch no se dio, dar pitch primero (evita TIMING_INCORRECTO)
        add(S.ENCARGADO_PRESENTE, I.CONFIRMATION,  S.CAPTURANDO_CONTACTO, A.TEMPLATE, "pedir_whatsapp")
        add(S.ENCARGADO_PRESENTE, I.INTEREST,      S.CAPTURANDO_CONTACTO, A.TEMPLATE, "pedir_whatsapp")
        add(S.ENCARGADO_PRESENTE, I.QUESTION,      S.ENCARGADO_PRESENTE, A.GPT_NARROW, "responder_pregunta_producto")
        add(S.ENCARGADO_PRESENTE, I.OFFER_DATA,    S.DICTANDO_DATO, A.ACKNOWLEDGE, "aja_digame")
        add(S.ENCARGADO_PRESENTE, I.NO_INTEREST,   S.DESPEDIDA, A.TEMPLATE, "despedida_no_interesa")
        add(S.ENCARGADO_PRESENTE, I.FAREWELL,      S.DESPEDIDA, A.TEMPLATE, "despedida_cortes")
        add(S.ENCARGADO_PRESENTE, I.WRONG_NUMBER,  S.DESPEDIDA, A.TEMPLATE, "despedida_area_equivocada")
        # FIX 763: REJECT_DATA ahora es dinámico (ver _handle_reject_data_763)
        # Guard ["whatsapp_rechazado"] removido - atributo no existía en FSMContext
        add(S.ENCARGADO_PRESENTE, I.REJECT_DATA,   S.CAPTURANDO_CONTACTO, A.TEMPLATE, "pedir_alternativa_correo")
        add(S.ENCARGADO_PRESENTE, I.VERIFICATION,  S.ENCARGADO_PRESENTE, A.TEMPLATE, "verificacion_aqui_estoy")
        # FIX 754: Cliente dicta teléfono/email completo estando con encargado -> capturar
        add(S.ENCARGADO_PRESENTE, I.DICTATING_COMPLETE_PHONE, S.CONTACTO_CAPTURADO, A.TEMPLATE, "confirmar_telefono")
        add(S.ENCARGADO_PRESENTE, I.DICTATING_COMPLETE_EMAIL, S.CONTACTO_CAPTURADO, A.TEMPLATE, "confirmar_correo")
        add(S.ENCARGADO_PRESENTE, I.DICTATING_PARTIAL,        S.DICTANDO_DATO, A.ACKNOWLEDGE, "aja_si")
        add(S.ENCARGADO_PRESENTE, I.UNKNOWN,       S.ENCARGADO_PRESENTE, A.GPT_NARROW, "conversacion_libre")
        # FIX 786: CONTINUATION - cliente sigue hablando
        add(S.ENCARGADO_PRESENTE, I.CONTINUATION,  S.ENCARGADO_PRESENTE, A.NOOP, None)
        # FIX 788: Gaps - IDENTITY, ANOTHER_BRANCH, CLOSED, CALLBACK, TRANSFER
        add(S.ENCARGADO_PRESENTE, I.IDENTITY,       S.ENCARGADO_PRESENTE, A.TEMPLATE, "identificacion_nioval")
        add(S.ENCARGADO_PRESENTE, I.ANOTHER_BRANCH, S.DESPEDIDA, A.TEMPLATE, "despedida_otra_sucursal")
        add(S.ENCARGADO_PRESENTE, I.CLOSED,         S.DESPEDIDA, A.TEMPLATE, "despedida_cerrado")
        add(S.ENCARGADO_PRESENTE, I.CALLBACK,       S.ENCARGADO_PRESENTE, A.TEMPLATE, "preguntar_hora_callback")
        add(S.ENCARGADO_PRESENTE, I.TRANSFER,       S.ESPERANDO_TRANSFERENCIA, A.TEMPLATE, "claro_espero")
        # FIX 894: New intents for ENCARGADO_PRESENTE
        add(S.ENCARGADO_PRESENTE, I.IDENTITY_QUESTION, S.ENCARGADO_PRESENTE, A.TEMPLATE, "identificacion_nioval")
        # FIX 1022: WHAT_OFFER en encargado presente = pregunta producto → GPT_NARROW responder
        add(S.ENCARGADO_PRESENTE, I.WHAT_OFFER,        S.ENCARGADO_PRESENTE, A.GPT_NARROW, "responder_pregunta_producto")

        # === ENCARGADO_AUSENTE ===
        add(S.ENCARGADO_AUSENTE, I.OFFER_DATA,     S.DICTANDO_DATO, A.ACKNOWLEDGE, "aja_digame")
        add(S.ENCARGADO_AUSENTE, I.REJECT_DATA,    S.OFRECIENDO_CONTACTO, A.TEMPLATE, "ofrecer_contacto_bruce")
        add(S.ENCARGADO_AUSENTE, I.CALLBACK,       S.ENCARGADO_AUSENTE, A.TEMPLATE, "preguntar_hora_callback")
        # FIX 764: "Sí" tras pedir contacto alternativo = ready to dictate, NO repetir pedir_whatsapp
        add(S.ENCARGADO_AUSENTE, I.CONFIRMATION,   S.CAPTURANDO_CONTACTO, A.TEMPLATE, "digame_numero")
        add(S.ENCARGADO_AUSENTE, I.INTEREST,       S.CAPTURANDO_CONTACTO, A.TEMPLATE, "pedir_whatsapp")
        add(S.ENCARGADO_AUSENTE, I.FAREWELL,       S.DESPEDIDA, A.TEMPLATE, "despedida_cortes")
        add(S.ENCARGADO_AUSENTE, I.NO_INTEREST,    S.DESPEDIDA, A.TEMPLATE, "despedida_no_interesa")
        add(S.ENCARGADO_AUSENTE, I.WRONG_NUMBER,   S.DESPEDIDA, A.TEMPLATE, "despedida_area_equivocada")
        add(S.ENCARGADO_AUSENTE, I.ANOTHER_BRANCH, S.DESPEDIDA, A.TEMPLATE, "despedida_otra_sucursal")
        add(S.ENCARGADO_AUSENTE, I.TRANSFER,       S.ESPERANDO_TRANSFERENCIA, A.TEMPLATE, "claro_espero")
        add(S.ENCARGADO_AUSENTE, I.VERIFICATION,   S.ENCARGADO_AUSENTE, A.TEMPLATE, "verificacion_aqui_estoy")
        add(S.ENCARGADO_AUSENTE, I.QUESTION,       S.ENCARGADO_AUSENTE, A.GPT_NARROW, "responder_pregunta_producto")
        # FIX 754: Cliente dicta teléfono/email completo -> capturar aunque encargado ausente
        add(S.ENCARGADO_AUSENTE, I.DICTATING_COMPLETE_PHONE, S.CONTACTO_CAPTURADO, A.TEMPLATE, "confirmar_telefono")
        add(S.ENCARGADO_AUSENTE, I.DICTATING_COMPLETE_EMAIL, S.CONTACTO_CAPTURADO, A.TEMPLATE, "confirmar_correo")
        add(S.ENCARGADO_AUSENTE, I.DICTATING_PARTIAL,        S.DICTANDO_DATO, A.ACKNOWLEDGE, "aja_si")
        add(S.ENCARGADO_AUSENTE, I.UNKNOWN,        S.ENCARGADO_AUSENTE, A.GPT_NARROW, "conversacion_libre")
        # FIX 786: CONTINUATION - cliente sigue hablando
        add(S.ENCARGADO_AUSENTE, I.CONTINUATION,  S.ENCARGADO_AUSENTE, A.NOOP, None)
        # FIX 926: Cliente repite "no está" en ENCARGADO_AUSENTE -> ofrecer contacto bruce
        add(S.ENCARGADO_AUSENTE, I.MANAGER_ABSENT, S.OFRECIENDO_CONTACTO, A.TEMPLATE, "ofrecer_contacto_bruce")
        # FIX 788: Gaps - IDENTITY, CLOSED
        add(S.ENCARGADO_AUSENTE, I.IDENTITY,      S.ENCARGADO_AUSENTE, A.TEMPLATE, "identificacion_nioval")
        add(S.ENCARGADO_AUSENTE, I.CLOSED,        S.DESPEDIDA, A.TEMPLATE, "despedida_cerrado")
        # FIX 894: New intents for ENCARGADO_AUSENTE
        add(S.ENCARGADO_AUSENTE, I.IDENTITY_QUESTION, S.ENCARGADO_AUSENTE, A.TEMPLATE, "identificacion_nioval")
        add(S.ENCARGADO_AUSENTE, I.WHAT_OFFER,        S.ENCARGADO_AUSENTE, A.TEMPLATE, "pitch_completo_894")

        # === ESPERANDO_TRANSFERENCIA ===
        add(S.ESPERANDO_TRANSFERENCIA, I.CONFIRMATION,    S.PITCH, A.TEMPLATE, "pitch_persona_nueva")
        add(S.ESPERANDO_TRANSFERENCIA, I.IDENTITY,        S.PITCH, A.TEMPLATE, "pitch_persona_nueva")
        add(S.ESPERANDO_TRANSFERENCIA, I.QUESTION,        S.PITCH, A.TEMPLATE, "pitch_persona_nueva")
        add(S.ESPERANDO_TRANSFERENCIA, I.MANAGER_PRESENT, S.ENCARGADO_PRESENTE, A.TEMPLATE, "pitch_encargado")
        add(S.ESPERANDO_TRANSFERENCIA, I.MANAGER_ABSENT,  S.ENCARGADO_AUSENTE, A.TEMPLATE, "pedir_contacto_alternativo")
        add(S.ESPERANDO_TRANSFERENCIA, I.FAREWELL,        S.DESPEDIDA, A.TEMPLATE, "despedida_cortes")
        # FIX 860: BRUCE2462 - VERIFICATION ("¿Bueno?") tras transfer = misma persona volviendo
        # → verificacion_aqui_estoy (no re-pitch con encargado question repetida)
        add(S.ESPERANDO_TRANSFERENCIA, I.VERIFICATION,    S.PITCH, A.TEMPLATE, "verificacion_aqui_estoy")
        add(S.ESPERANDO_TRANSFERENCIA, I.OFFER_DATA,      S.DICTANDO_DATO, A.ACKNOWLEDGE, "aja_digame")
        # FIX 929: BRUCE2576 - UNKNOWN durante espera → silencio (no BTE fallback que re-pregunta encargado)
        add(S.ESPERANDO_TRANSFERENCIA, I.UNKNOWN,         S.ESPERANDO_TRANSFERENCIA, A.TEMPLATE, "verificacion_aqui_estoy")
        # FIX 786: CONTINUATION - cliente sigue hablando durante espera
        add(S.ESPERANDO_TRANSFERENCIA, I.CONTINUATION,   S.ESPERANDO_TRANSFERENCIA, A.NOOP, None)
        # FIX 788: Gaps - NO_INTEREST, CALLBACK, DICTATING_*, WRONG_NUMBER
        add(S.ESPERANDO_TRANSFERENCIA, I.NO_INTEREST,    S.DESPEDIDA, A.TEMPLATE, "despedida_cortes")
        add(S.ESPERANDO_TRANSFERENCIA, I.CALLBACK,       S.ENCARGADO_AUSENTE, A.TEMPLATE, "preguntar_hora_callback")
        add(S.ESPERANDO_TRANSFERENCIA, I.WRONG_NUMBER,   S.DESPEDIDA, A.TEMPLATE, "despedida_area_equivocada")
        add(S.ESPERANDO_TRANSFERENCIA, I.DICTATING_COMPLETE_PHONE, S.CONTACTO_CAPTURADO, A.TEMPLATE, "confirmar_telefono")
        add(S.ESPERANDO_TRANSFERENCIA, I.DICTATING_COMPLETE_EMAIL, S.CONTACTO_CAPTURADO, A.TEMPLATE, "confirmar_correo")
        add(S.ESPERANDO_TRANSFERENCIA, I.DICTATING_PARTIAL,        S.DICTANDO_DATO, A.ACKNOWLEDGE, "aja_si")
        # FIX 894: New intents for ESPERANDO_TRANSFERENCIA
        add(S.ESPERANDO_TRANSFERENCIA, I.IDENTITY_QUESTION, S.PITCH, A.TEMPLATE, "identificacion_pitch")
        add(S.ESPERANDO_TRANSFERENCIA, I.WHAT_OFFER,        S.PITCH, A.TEMPLATE, "pitch_completo_894")

        # === CAPTURANDO_CONTACTO ===
        add(S.CAPTURANDO_CONTACTO, I.OFFER_DATA,              S.DICTANDO_DATO, A.ACKNOWLEDGE, "aja_digame")
        add(S.CAPTURANDO_CONTACTO, I.CONFIRMATION,            S.DICTANDO_DATO, A.TEMPLATE, "digame_numero")
        add(S.CAPTURANDO_CONTACTO, I.DICTATING_PARTIAL,       S.DICTANDO_DATO, A.ACKNOWLEDGE, "aja_si")
        add(S.CAPTURANDO_CONTACTO, I.DICTATING_COMPLETE_PHONE, S.CONTACTO_CAPTURADO, A.TEMPLATE, "confirmar_telefono")
        add(S.CAPTURANDO_CONTACTO, I.DICTATING_COMPLETE_EMAIL, S.CONTACTO_CAPTURADO, A.TEMPLATE, "confirmar_correo")
        add(S.CAPTURANDO_CONTACTO, I.REJECT_DATA,             S.CAPTURANDO_CONTACTO, A.TEMPLATE, "pedir_alternativa_correo")
        add(S.CAPTURANDO_CONTACTO, I.NO_INTEREST,             S.DESPEDIDA, A.TEMPLATE, "despedida_no_interesa")
        add(S.CAPTURANDO_CONTACTO, I.FAREWELL,                S.DESPEDIDA, A.TEMPLATE, "despedida_cortes")
        # FIX 1048: "no tenemos presupuesto" (CALLBACK) in CAPTURANDO_CONTACTO → ask callback time
        add(S.CAPTURANDO_CONTACTO, I.CALLBACK,                S.ENCARGADO_AUSENTE, A.TEMPLATE, "preguntar_hora_callback")
        add(S.CAPTURANDO_CONTACTO, I.VERIFICATION,            S.CAPTURANDO_CONTACTO, A.TEMPLATE, "verificacion_aqui_estoy")
        add(S.CAPTURANDO_CONTACTO, I.UNKNOWN,                 S.CAPTURANDO_CONTACTO, A.GPT_NARROW, "conversacion_libre")
        # FIX 786: CONTINUATION - cliente sigue hablando
        add(S.CAPTURANDO_CONTACTO, I.CONTINUATION,           S.CAPTURANDO_CONTACTO, A.NOOP, None)
        # FIX 788: Gaps - IDENTITY, WRONG_NUMBER
        add(S.CAPTURANDO_CONTACTO, I.IDENTITY,               S.CAPTURANDO_CONTACTO, A.TEMPLATE, "identificacion_nioval")
        add(S.CAPTURANDO_CONTACTO, I.WRONG_NUMBER,           S.DESPEDIDA, A.TEMPLATE, "despedida_area_equivocada")
        # FIX 894: New intents for CAPTURANDO_CONTACTO
        add(S.CAPTURANDO_CONTACTO, I.IDENTITY_QUESTION, S.CAPTURANDO_CONTACTO, A.TEMPLATE, "identificacion_nioval")
        # FIX 1022: WHAT_OFFER en captura = pregunta sobre productos → responder con GPT_NARROW
        # Antes era pitch_completo_894 → FIX 925 lo interceptaba → pedir_whatsapp (INCORRECTO)
        add(S.CAPTURANDO_CONTACTO, I.WHAT_OFFER,        S.CAPTURANDO_CONTACTO, A.GPT_NARROW, "responder_pregunta_producto")
        # FIX 797: En CAPTURANDO_CONTACTO, manejar intents de encargado (eco STT)
        # STT echo "no está" -> MANAGER_ABSENT -> sin transición -> UNKNOWN -> GPT "contacto alternativo"
        add(S.CAPTURANDO_CONTACTO, I.MANAGER_ABSENT,  S.CAPTURANDO_CONTACTO, A.TEMPLATE, "digame_numero")
        add(S.CAPTURANDO_CONTACTO, I.MANAGER_PRESENT, S.CAPTURANDO_CONTACTO, A.TEMPLATE, "digame_numero")
        add(S.CAPTURANDO_CONTACTO, I.QUESTION,        S.CAPTURANDO_CONTACTO, A.GPT_NARROW, "responder_pregunta_producto")
        # FIX 978: INTEREST en CAPTURANDO_CONTACTO = "mándeme el catálogo" → pedir dato directamente
        # Sin esta línea, INTEREST no tenía transición → GPT → "Si, aqui estoy. Digame." (FLUJO_ROBOTICO)
        add(S.CAPTURANDO_CONTACTO, I.INTEREST,       S.DICTANDO_DATO, A.TEMPLATE, "digame_numero")

        # === DICTANDO_DATO ===
        add(S.DICTANDO_DATO, I.DICTATING_PARTIAL,       S.DICTANDO_DATO, A.ACKNOWLEDGE, "aja_si")
        add(S.DICTANDO_DATO, I.DICTATING_COMPLETE_PHONE, S.CONTACTO_CAPTURADO, A.TEMPLATE, "confirmar_telefono")
        add(S.DICTANDO_DATO, I.DICTATING_COMPLETE_EMAIL, S.CONTACTO_CAPTURADO, A.TEMPLATE, "confirmar_correo")
        add(S.DICTANDO_DATO, I.CONTINUATION,             S.DICTANDO_DATO, A.ACKNOWLEDGE, "aja_si")
        add(S.DICTANDO_DATO, I.OFFER_DATA,               S.DICTANDO_DATO, A.ACKNOWLEDGE, "aja_si")
        add(S.DICTANDO_DATO, I.CONFIRMATION,             S.DICTANDO_DATO, A.ACKNOWLEDGE, "aja_si")
        # FIX 936: BRUCE2376 - "permíteme" (TRANSFER) en DICTANDO_DATO → esperar transferencia
        add(S.DICTANDO_DATO, I.TRANSFER,                 S.ESPERANDO_TRANSFERENCIA, A.TEMPLATE, "claro_espero")
        add(S.DICTANDO_DATO, I.FAREWELL,                 S.DESPEDIDA, A.TEMPLATE, "despedida_cortes")
        add(S.DICTANDO_DATO, I.VERIFICATION,             S.DICTANDO_DATO, A.TEMPLATE, "verificacion_aqui_estoy")
        # FIX 820: UNKNOWN durante dictado -> Claude decide (no fillers)
        # ANTES: A.ACKNOWLEDGE "aja_si" -> loop de fillers cuando cliente no dicta
        # FIX 1011: DICTANDO_DATO + UNKNOWN → ACKNOWLEDGE (anti-PREGUNTA_REPETIDA)
        # GPT en este estado generaba preguntas repetidas ("¿Me confirma su correo?")
        # Si el cliente dicta algo ambiguo, asentir y dejar continuar.
        add(S.DICTANDO_DATO, I.UNKNOWN,                  S.DICTANDO_DATO, A.ACKNOWLEDGE, "aja_si")
        # FIX 788: Gaps - NO_INTEREST, REJECT_DATA, IDENTITY
        add(S.DICTANDO_DATO, I.NO_INTEREST,              S.DESPEDIDA, A.TEMPLATE, "despedida_cortes")
        add(S.DICTANDO_DATO, I.REJECT_DATA,              S.OFRECIENDO_CONTACTO, A.TEMPLATE, "ofrecer_contacto_bruce")
        add(S.DICTANDO_DATO, I.IDENTITY,                 S.DICTANDO_DATO, A.TEMPLATE, "identificacion_nioval")
        # FIX 801: BRUCE2522 - QUESTION durante dictado -> responder pregunta y salir de dictado
        # Sin esta transición, QUESTION cae al catch-all UNKNOWN -> filler loop infinito
        add(S.DICTANDO_DATO, I.QUESTION,                 S.CAPTURANDO_CONTACTO, A.GPT_NARROW, "responder_pregunta_producto")

        # === OFRECIENDO_CONTACTO ===
        add(S.OFRECIENDO_CONTACTO, I.CONFIRMATION,  S.OFRECIENDO_CONTACTO, A.TEMPLATE, "tiene_donde_anotar", ["!donde_anotar_preguntado"])
        # FIX 982: INTEREST en OFRECIENDO_CONTACTO = "mandeme el catalogo" = re-abre captura
        # Sin fix: INTEREST → tiene_donde_anotar → Bruce da su propio número (confuso)
        # Con fix: INTEREST → volver a pedir canal de contacto al cliente
        add(S.OFRECIENDO_CONTACTO, I.INTEREST,      S.CAPTURANDO_CONTACTO, A.TEMPLATE, "pedir_whatsapp_o_correo")
        add(S.OFRECIENDO_CONTACTO, I.REJECT_DATA,   S.DESPEDIDA, A.TEMPLATE, "despedida_sin_contacto")
        add(S.OFRECIENDO_CONTACTO, I.NO_INTEREST,   S.DESPEDIDA, A.TEMPLATE, "despedida_sin_contacto")
        add(S.OFRECIENDO_CONTACTO, I.FAREWELL,      S.DESPEDIDA, A.TEMPLATE, "despedida_cortes")
        add(S.OFRECIENDO_CONTACTO, I.UNKNOWN,       S.OFRECIENDO_CONTACTO, A.TEMPLATE, "dictar_numero_bruce")
        # FIX 786: CONTINUATION - cliente sigue hablando
        add(S.OFRECIENDO_CONTACTO, I.CONTINUATION,  S.OFRECIENDO_CONTACTO, A.NOOP, None)
        # FIX 787: Gaps críticos OFRECIENDO_CONTACTO - cliente dicta datos
        add(S.OFRECIENDO_CONTACTO, I.DICTATING_COMPLETE_PHONE, S.CONTACTO_CAPTURADO, A.TEMPLATE, "confirmar_telefono")
        add(S.OFRECIENDO_CONTACTO, I.DICTATING_COMPLETE_EMAIL, S.CONTACTO_CAPTURADO, A.TEMPLATE, "confirmar_correo")
        add(S.OFRECIENDO_CONTACTO, I.DICTATING_PARTIAL,        S.DICTANDO_DATO, A.ACKNOWLEDGE, "aja_si")
        add(S.OFRECIENDO_CONTACTO, I.VERIFICATION,  S.OFRECIENDO_CONTACTO, A.TEMPLATE, "verificacion_aqui_estoy")
        add(S.OFRECIENDO_CONTACTO, I.QUESTION,      S.OFRECIENDO_CONTACTO, A.GPT_NARROW, "responder_pregunta_producto")
        add(S.OFRECIENDO_CONTACTO, I.IDENTITY,      S.OFRECIENDO_CONTACTO, A.TEMPLATE, "identificacion_nioval")
        add(S.OFRECIENDO_CONTACTO, I.OFFER_DATA,    S.DICTANDO_DATO, A.ACKNOWLEDGE, "aja_digame")
        add(S.OFRECIENDO_CONTACTO, I.WRONG_NUMBER,  S.DESPEDIDA, A.TEMPLATE, "despedida_area_equivocada")

        # === CONTACTO_CAPTURADO ===
        # FIX 1049: CONFIRMATION post-captura = cliente da instrucción adicional ("use el personal")
        # Use GPT_NARROW so it can acknowledge the specific instruction before saying goodbye
        add(S.CONTACTO_CAPTURADO, I.CONFIRMATION, S.DESPEDIDA, A.GPT_NARROW, "reconocer_y_despedir")
        add(S.CONTACTO_CAPTURADO, I.FAREWELL,     S.DESPEDIDA, A.TEMPLATE, "despedida_catalogo_prometido")
        add(S.CONTACTO_CAPTURADO, I.UNKNOWN,      S.DESPEDIDA, A.TEMPLATE, "despedida_catalogo_prometido")
        # FIX 839: Cliente repite número después de captura -> despedida corta (ya tenemos el dato)
        add(S.CONTACTO_CAPTURADO, I.DICTATING_COMPLETE_PHONE, S.DESPEDIDA, A.TEMPLATE, "despedida_cortes")
        add(S.CONTACTO_CAPTURADO, I.DICTATING_COMPLETE_EMAIL, S.DESPEDIDA, A.TEMPLATE, "despedida_cortes")
        add(S.CONTACTO_CAPTURADO, I.DICTATING_PARTIAL,        S.DESPEDIDA, A.TEMPLATE, "despedida_cortes")
        # FIX 786: CONTINUATION - cliente sigue hablando
        add(S.CONTACTO_CAPTURADO, I.CONTINUATION, S.CONTACTO_CAPTURADO, A.NOOP, None)
        # FIX 788: Gaps - VERIFICATION, NO_INTEREST
        add(S.CONTACTO_CAPTURADO, I.VERIFICATION, S.CONTACTO_CAPTURADO, A.TEMPLATE, "verificacion_aqui_estoy")
        add(S.CONTACTO_CAPTURADO, I.NO_INTEREST,  S.DESPEDIDA, A.TEMPLATE, "despedida_catalogo_prometido")

        # === DESPEDIDA ===
        add(S.DESPEDIDA, I.UNKNOWN,       S.DESPEDIDA, A.HANGUP, None)
        add(S.DESPEDIDA, I.FAREWELL,      S.DESPEDIDA, A.HANGUP, None)
        add(S.DESPEDIDA, I.CONFIRMATION,  S.DESPEDIDA, A.HANGUP, None)
        # FIX 1038: DESPEDIDA + VERIFICATION → restart pitch (humano llega post-IVR)
        # Antes: "Bueno buenas tardes" en DESPEDIDA → doble despedida (bug OOS-17-06)
        # Ahora: tratarlo como señal de humano presente → pitch (igual que FIX 1016)
        add(S.DESPEDIDA, I.VERIFICATION,  S.PITCH, A.TEMPLATE, "pitch_completo_894")
        add(S.DESPEDIDA, I.OFFER_DATA,    S.DICTANDO_DATO, A.ACKNOWLEDGE, "aja_digame")
        # FIX 839: Cliente sigue dictando después de despedida -> hangup (ya tenemos el dato)
        add(S.DESPEDIDA, I.DICTATING_COMPLETE_PHONE, S.DESPEDIDA, A.HANGUP, None)
        add(S.DESPEDIDA, I.DICTATING_COMPLETE_EMAIL, S.DESPEDIDA, A.HANGUP, None)
        add(S.DESPEDIDA, I.DICTATING_PARTIAL,        S.DESPEDIDA, A.HANGUP, None)
        # FIX 786: CONTINUATION - cliente sigue hablando
        add(S.DESPEDIDA, I.CONTINUATION, S.DESPEDIDA, A.NOOP, None)
        # FIX 788: Gaps - NO_INTEREST, WRONG_NUMBER
        add(S.DESPEDIDA, I.NO_INTEREST,  S.DESPEDIDA, A.HANGUP, None)
        add(S.DESPEDIDA, I.WRONG_NUMBER, S.DESPEDIDA, A.HANGUP, None)
        # FIX 1016: Human greeting after IVR-triggered DESPEDIDA → restart pitch
        # "Para continuar en español marque uno" → DESPEDIDA → human arrives → retomar
        add(S.DESPEDIDA, I.MANAGER_PRESENT,  S.ENCARGADO_PRESENTE, A.TEMPLATE, "pitch_encargado")
        add(S.DESPEDIDA, I.WHAT_OFFER,       S.PITCH, A.TEMPLATE, "pitch_completo_894")
        add(S.DESPEDIDA, I.IDENTITY,         S.PITCH, A.TEMPLATE, "identificacion_pitch")
        add(S.DESPEDIDA, I.INTEREST,         S.PITCH, A.TEMPLATE, "pitch_completo_894")
        # FIX 1031: DESPEDIDA + CALLBACK → confirmar callback (cliente da hora después de despedida)
        # Ej: FSM dice adiós porque "estoy ocupado" → cliente dice "Mejor llámame en una hora"
        add(S.DESPEDIDA, I.CALLBACK,         S.ENCARGADO_AUSENTE, A.TEMPLATE, "preguntar_hora_callback")

        # === CONVERSACION_LIBRE (FIX 790: shadow transitions, sin entry points aún) ===
        # No está en FSM_ACTIVE_STATES - solo shadow logging.
        # Preparado para futura activación cuando se definan entry points.
        add(S.CONVERSACION_LIBRE, I.FAREWELL,      S.DESPEDIDA, A.TEMPLATE, "despedida_cortes")
        add(S.CONVERSACION_LIBRE, I.NO_INTEREST,    S.DESPEDIDA, A.TEMPLATE, "despedida_no_interesa")
        add(S.CONVERSACION_LIBRE, I.VERIFICATION,   S.CONVERSACION_LIBRE, A.TEMPLATE, "verificacion_aqui_estoy")
        add(S.CONVERSACION_LIBRE, I.QUESTION,       S.CONVERSACION_LIBRE, A.GPT_NARROW, "responder_pregunta_producto")
        add(S.CONVERSACION_LIBRE, I.IDENTITY,       S.CONVERSACION_LIBRE, A.TEMPLATE, "identificacion_nioval")
        add(S.CONVERSACION_LIBRE, I.OFFER_DATA,     S.DICTANDO_DATO, A.ACKNOWLEDGE, "aja_digame")
        add(S.CONVERSACION_LIBRE, I.DICTATING_COMPLETE_PHONE, S.CONTACTO_CAPTURADO, A.TEMPLATE, "confirmar_telefono")
        add(S.CONVERSACION_LIBRE, I.DICTATING_COMPLETE_EMAIL, S.CONTACTO_CAPTURADO, A.TEMPLATE, "confirmar_correo")
        add(S.CONVERSACION_LIBRE, I.DICTATING_PARTIAL,        S.DICTANDO_DATO, A.ACKNOWLEDGE, "aja_si")
        add(S.CONVERSACION_LIBRE, I.REJECT_DATA,    S.DESPEDIDA, A.TEMPLATE, "despedida_no_interesa")
        add(S.CONVERSACION_LIBRE, I.WRONG_NUMBER,   S.DESPEDIDA, A.TEMPLATE, "despedida_area_equivocada")
        add(S.CONVERSACION_LIBRE, I.ANOTHER_BRANCH, S.DESPEDIDA, A.TEMPLATE, "despedida_otra_sucursal")
        add(S.CONVERSACION_LIBRE, I.CLOSED,         S.DESPEDIDA, A.TEMPLATE, "despedida_cerrado")
        add(S.CONVERSACION_LIBRE, I.CONTINUATION,   S.CONVERSACION_LIBRE, A.NOOP, None)
        add(S.CONVERSACION_LIBRE, I.CONFIRMATION,   S.CONVERSACION_LIBRE, A.GPT_NARROW, "conversacion_libre")
        add(S.CONVERSACION_LIBRE, I.INTEREST,       S.CAPTURANDO_CONTACTO, A.TEMPLATE, "pedir_whatsapp")
        add(S.CONVERSACION_LIBRE, I.UNKNOWN,        S.CONVERSACION_LIBRE, A.GPT_NARROW, "conversacion_libre")

        return T

    # ----------------------------------------------------------
    # Lookup transición
    # ----------------------------------------------------------
    def _lookup(self, state: FSMState, intent: FSMIntent) -> Optional[Transition]:
        """Busca transición en la tabla."""
        return self._transitions.get((state, intent))

    # ----------------------------------------------------------
    # Evaluar guards
    # ----------------------------------------------------------
    def _check_guards(self, guards: List[str]) -> bool:
        """Evalúa guard conditions contra el contexto."""
        for guard in guards:
            negate = guard.startswith('!')
            attr = guard.lstrip('!')
            val = getattr(self.context, attr, None)
            if val is None:
                # Guard referencia atributo que no existe
                if negate:
                    continue  # !nonexistent = True
                return False
            if negate:
                if val:
                    return False
            else:
                if not val:
                    return False
        return True

    # ----------------------------------------------------------
    # Ejecutar acción
    # ----------------------------------------------------------
    def _execute(self, transition: Transition, texto: str, agente=None) -> Optional[str]:
        """Ejecuta la acción de la transición."""
        if transition.action_type == ActionType.TEMPLATE:
            # FIX 919: No pedir datos si no se ha dado el pitch todavia (TIMING_INCORRECTO)
            # Si transicion va a CAPTURANDO_CONTACTO pero pitch no se dio, dar pitch primero
            _pedir_datos_keys = ('pedir_whatsapp', 'pedir_correo', 'pedir_whatsapp_o_correo',
                                 'pedir_whatsapp_o_correo_breve', 'pedir_contacto_alternativo')
            if (transition.template_key in _pedir_datos_keys
                    and not self.context.pitch_dado
                    and self.context.turnos_bruce < 2):
                print(f"  [FIX 919] TIMING: pitch no dado aun, dar valor antes de pedir datos")
                return self._get_template("pitch_inicial")

            # FIX 920: Explorar antes de despedida - si NO_INTEREST/FAREWELL en estado temprano
            # y no se ha explorado alternativas, ofrecer algo antes de colgar
            # Guard: No interceptar si ya estamos en DESPEDIDA (ya nos estamos despidiendo)
            if (transition.template_key in ('despedida_no_interesa', 'despedida_cortes')
                    and self.state != FSMState.DESPEDIDA
                    and not getattr(self.context, 'pitch_dado', False)
                    and getattr(self.context, 'turnos_bruce', 0) <= 3
                    and "explorar_antes_despedida" not in getattr(self.context, 'templates_usados', set())):
                self.context.templates_usados.add("explorar_antes_despedida")
                print(f"  [FIX 920] Explorar antes de despedida (pitch no dado, turno {self.context.turnos_bruce})")
                return self._get_template("explorar_antes_despedida")

            # FIX 922: Captura mínima pre-despedida - si vamos a despedida con pitch dado pero sin datos
            # Guard: Not in DESPEDIDA already, and only once
            # FIX 939: No pedir datos si cliente dijo area equivocada / no hace compras
            _tn_939 = _normalize(texto) if texto else ''
            _area_equivocada_939 = any(p in _tn_939 for p in [
                'no hacemos compra', 'no compramos', 'no hacemos ningun tipo de compra',
                'no es ferreteria', 'no es aqui', 'aqui no es', 'numero equivocado',
                'se equivoco', 'esta equivocado', 'area equivocada',
            ])
            # FIX 938-D: OOS audit V2 - No pedir datos si cliente expresó rechazo firme
            _rechazo_firme_938 = any(r in _tn_939 for r in [
                'no me interesa', 'no nos interesa', 'no gracias', 'no necesitamos',
                'no necesito nada', 'no nos hace falta', 'estamos bien',
                'no por favor', 'no muchas gracias',
            ])
            if (transition.template_key in ('despedida_no_interesa', 'despedida_cortes')
                    and self.state != FSMState.DESPEDIDA
                    and getattr(self.context, 'pitch_dado', False)
                    and not getattr(self.context, 'datos_capturados', {})
                    and not getattr(self.context, 'catalogo_prometido', False)
                    and getattr(self.context, 'pedir_datos_count', 0) == 0
                    and not _area_equivocada_939
                    and not _rechazo_firme_938
                    and "captura_minima_pre_despedida" not in getattr(self.context, 'templates_usados', set())):
                self.context.templates_usados.add("captura_minima_pre_despedida")
                print(f"  [FIX 922] Captura minima pre-despedida (sin datos capturados)")
                return self._get_template("captura_minima_pre_despedida")

            # FIX 932: BRUCE2528 - dictar_numero_bruce repetido 2+ veces → despedida
            # En OFRECIENDO_CONTACTO, UNKNOWN maps directly to dictar_numero_bruce (not GPT_NARROW)
            # so _handle_unknown_stateful is never called. Manual anti-loop here.
            if transition.template_key == "dictar_numero_bruce":
                _dictar_count = getattr(self.context, '_dictar_numero_count', 0) + 1
                self.context._dictar_numero_count = _dictar_count
                if _dictar_count >= 2:
                    print(f"  [FIX 932] dictar_numero_bruce #{_dictar_count} -> despedida_cortes (anti-LOOP)")
                    return self._get_template("despedida_cortes")

            # FIX 875: pitch_encargado con pitch ya dado → usar versión corta (sin lista de productos)
            # Auditoría 25/02: INFO_NO_SOLICITADA(9x) — Bruce repite descripción de productos
            # cuando el encargado confirma presencia DESPUÉS de que pitch_inicial ya sonó.
            # pitch_dado=True significa que pitch_inicial/pitch_persona_nueva ya fue usado → usar corto.
            if transition.template_key == "pitch_encargado" and self.context.pitch_dado:
                print(f"  [FIX 875] pitch ya dado -> pitch_encargado_corto")
                return self._get_template("pitch_encargado_corto")

            # FIX 895: pitch_completo_894/pitch_y_encargado_894 cuando pitch ya dado → pivot
            # BRUCE2643/2631: WHAT_OFFER en ENCARGADO_AUSENTE repite pitch completo en loop
            # Si pitch ya fue dado, el cliente ya sabe quiénes somos → pedir contacto directamente
            if transition.template_key in ("pitch_completo_894", "pitch_y_encargado_894") and self.context.pitch_dado:
                _pitch_894_count = getattr(self.context, '_pitch_894_count', 0) + 1
                self.context._pitch_894_count = _pitch_894_count
                # FIX 925: Escalar progresivamente sin repetir templates ya dichos
                _candidates_925 = [
                    "pedir_whatsapp_o_correo",
                    "pedir_whatsapp_o_correo_breve",
                    "ofrecer_contacto_bruce",
                    "despedida_cortes",
                ]
                _selected_925 = "despedida_cortes"  # fallback
                for c in _candidates_925:
                    if c not in self.context.templates_usados:
                        _selected_925 = c
                        break
                print(f"  [FIX 925] pitch_completo_894 #{_pitch_894_count} → {_selected_925} (anti-repeticion)")
                return self._get_template(_selected_925)

            # FIX 878: identificacion_nioval repetido → pivot a pedir contacto
            # BRUCE2551: cliente preguntó "¿Dónde están?" 4x, FSM respondió "Mi nombre es Bruce..." 3x.
            # FIX 1023: threshold subido de 2→3: cliente puede hacer 2 preguntas de identidad legítimas
            # ("¿cómo se llama?" + "¿de qué empresa?") antes de pivotar a captura
            if transition.template_key == "identificacion_nioval":
                self.context.identity_repetidas += 1
                if self.context.identity_repetidas >= 3:
                    if self.context.identity_repetidas == 3:
                        print(f"  [FIX 878/1023] identificacion_nioval #{self.context.identity_repetidas} → pivot a pedir_whatsapp_o_correo_breve")
                        # FIX 884: Usar template breve para evitar PREGUNTA_REPETIDA
                        return self._get_template("pedir_whatsapp_o_correo_breve")
                    else:
                        print(f"  [FIX 878/885B/1023] identificacion_nioval #{self.context.identity_repetidas} → pedir_numero_directo_885")
                        # FIX 885B: BRUCE2551/1975 - 4er+ identity → template distinto para evitar PREGUNTA_REPETIDA
                        return self._get_template("pedir_numero_directo_885")

            # FIX 959: Canal ignorado — cliente pide correo, Bruce acepta teléfono
            # Si cliente expresó preferencia por correo/email en últimos 2 turnos del contexto
            # y la FSM está a punto de confirmar un TELÉFONO, redirigir a pedir email.
            if transition.template_key == "confirmar_telefono":
                _correo_pref_ctx_959 = self.context.datos_capturados.get('prefiere_correo_959', False)
                if not _correo_pref_ctx_959:
                    # También revisar datos_parciales context desde _actualizar_prefiere_correo
                    _hist_correo_959 = [
                        'al correo', 'por correo', 'mi correo', 'al email', 'por email',
                        'al mail', 'por mail', 'correo mejor', 'mejor al correo',
                        'mandeme al correo', 'enviame al correo', 'via correo', 'via email',
                    ]
                    _src_959 = texto.lower()  # current turn (_texto_lower no disponible en _execute)
                    _correo_pref_ctx_959 = any(h in _src_959 for h in _hist_correo_959)
                # FIX 972: No redirigir a correo si el cliente AHORA está dando un número de teléfono
                # (el cliente cambió de canal → capturar el número que da, no insistir en correo)
                if _correo_pref_ctx_959:
                    import re as _re972
                    _tiene_digitos_972 = len(_re972.findall(r'\d', texto)) >= 8
                    if _tiene_digitos_972:
                        print(f"  [FIX 972] Cliente prefería correo pero ahora da número -> capturar número")
                        self.context.datos_capturados.pop('prefiere_correo_959', None)
                        _correo_pref_ctx_959 = False  # Capture as phone instead
                    else:
                        print(f"  [FIX 959] confirmar_telefono pero cliente prefiere correo -> pedir correo")
                        self.context.datos_capturados['prefiere_correo_959'] = True
                        self.state = FSMState.DICTANDO_DATO  # Stay in data capture
                        return "Claro, con gusto le envio la informacion al correo. ¿Me podria proporcionar su correo electronico?"

            # FIX 956: Doble despedida cuando cliente dice "gracias" post-confirmación
            # confirmar_telefono/confirmar_correo ya incluye "Muchas gracias". Si el cliente
            # dice "gracias" tras eso, NO emitir otra despedida — solo colgar (NOOP/empty).
            if (transition.template_key == "despedida_catalogo_prometido" and
                    any(k in self.context.templates_usados
                        for k in ('confirmar_telefono', 'confirmar_correo', 'confirmar_dato_generico',
                                  'confirmar_correccion_952'))):
                print(f"  [FIX 956] despedida_catalogo_prometido post-confirmar -> colgar (anti-doble despedida)")
                self.state = FSMState.DESPEDIDA
                return None  # Colgar en silencio

            # FIX 954: "Si, aqui estoy. Digame." en momento incorrecto
            # En CAPTURANDO_CONTACTO/PITCH (pitch ya dado) → pedir contacto, no "aqui estoy"
            # VERIFICATION debería ser checkeo de presencia solo en DICTANDO/BUSCANDO states
            if (transition.template_key == "verificacion_aqui_estoy" and
                    self.state in (FSMState.CAPTURANDO_CONTACTO, FSMState.ENCARGADO_PRESENTE)):
                _veri_954_tmpl = (
                    "pedir_whatsapp_o_correo_breve"
                    if "pedir_whatsapp_o_correo_breve" not in self.context.templates_usados
                    else "pedir_numero_directo_885"
                )
                print(f"  [FIX 954] verificacion_aqui_estoy en {self.state.value} -> {_veri_954_tmpl}")
                return self._get_template(_veri_954_tmpl)

            # FIX 955: "Si, adelante." post-número sin confirmar dato
            # En DICTANDO_DATO, si datos_parciales tiene 8+ dígitos y recibimos "aja_si",
            # hay que intentar confirmar en lugar de solo asentir.
            # (La transición fue DICTATING_PARTIAL → DICTANDO_DATO → aja_si pero el número estaba casi completo)
            if (transition.template_key == "aja_si" and
                    self.state == FSMState.DICTANDO_DATO and
                    len(self.context.datos_parciales) >= 8):
                print(f"  [FIX 955] aja_si con {len(self.context.datos_parciales)} dígitos acumulados -> confirmar_telefono")
                self.state = FSMState.CONTACTO_CAPTURADO
                self.context.datos_parciales = ""
                return self._get_template("confirmar_telefono")

            # FIX 1015: Callback with time already given → acknowledge, don't ask again
            # "Mejor a las 3 de la tarde" → preguntar_hora_callback → asks "¿A qué hora?"
            # Fix: if time is in the text, confirm it directly
            if transition.template_key in ('preguntar_hora_callback', 'preguntar_hora_callback_directo'):
                import re as _re1015
                _hora_1015 = _re1015.search(
                    r'a\s+las?\s+([\w]+(?:\s+(?:de\s+la\s+)?(?:tarde|manana|noche|madrugada))?)',
                    texto, _re1015.IGNORECASE)
                if not _hora_1015:
                    # Try simpler: "las 3", "las tres", "3 pm"
                    _hora_1015 = _re1015.search(
                        r'(?:las?|desde\s+las?)\s+(\d+(?::\d+)?(?:\s*(?:am|pm))?)',
                        texto, _re1015.IGNORECASE)
                if _hora_1015:
                    _hora_str_1015 = _hora_1015.group(1).strip()
                    print(f"  [FIX 1015] Hora ya dada '{_hora_str_1015}' → confirmar sin preguntar")
                    self.state = FSMState.ENCARGADO_AUSENTE
                    return (f"Perfecto, le marco a las {_hora_str_1015}. "
                            f"Muchas gracias por su tiempo, que tenga excelente dia.")

            # FIX 1007: Confirmar correo repitiendo el dato capturado (reduce errores en dictado oral)
            if transition.template_key == 'confirmar_correo':
                import re as _re1007
                _email_match_1007 = _re1007.search(
                    r'[\w._%+\-]+@[\w.\-]+\.[a-zA-Z]{2,}', texto or '')
                if _email_match_1007:
                    _email_1007 = _email_match_1007.group()
                    print(f"  [FIX 1007] Confirmando correo con repeticion: {_email_1007}")
                    self.context.templates_usados.add('confirmar_correo')
                    return (f"Perfecto, le confirmo el correo: {_email_1007}. "
                            f"Le envio el catalogo en breve.")

            return self._get_template(transition.template_key)

        elif transition.action_type == ActionType.ACKNOWLEDGE:
            return self._get_template(transition.template_key or "aja_si")

        elif transition.action_type == ActionType.GPT_NARROW:
            return self._call_gpt_narrow(transition.template_key, texto, agente)

        elif transition.action_type == ActionType.HANGUP:
            return None  # Signal to hang up

        elif transition.action_type == ActionType.NOOP:
            return ""  # Silence

        return None

    # ----------------------------------------------------------
    # Template lookup
    # ----------------------------------------------------------
    def _get_template(self, key: str) -> str:
        """Obtiene template por key. Rota variantes para evitar repetición.
        FIX 907: Registra templates usados para detección de PREGUNTA_REPETIDA.
        FIX 909: Si template ya se usó, intenta variante distinta."""
        templates = TEMPLATES.get(key)
        if not templates:
            return ""

        # FIX 909: Si este template ya se usó y hay variantes, usar otra
        if len(templates) > 1:
            # Intentar variante no usada
            for i, t in enumerate(templates):
                t_key = f"{key}_{i}"
                if t_key not in self.context.templates_usados:
                    response = t
                    self.context.templates_usados.add(t_key)
                    break
            else:
                # Todas usadas, rotar normalmente
                idx = getattr(self, '_template_counter', 0)
                response = templates[idx % len(templates)]
                self._template_counter = idx + 1
        else:
            response = templates[0]

        # FIX 907: Registrar template usado
        self.context.templates_usados.add(key)

        # Variable substitution
        if '{hora}' in response:
            hora = self.context.callback_hora or "mas tarde"
            response = response.replace('{hora}', hora)
        if '{canal_alternativo}' in response:
            alt = self._get_canal_alternativo()
            response = response.replace('{canal_alternativo}', alt)

        return response

    # ----------------------------------------------------------
    # GPT Narrow call
    # ----------------------------------------------------------
    def _call_gpt_narrow(self, prompt_key: str, texto: str, agente=None) -> Optional[str]:
        """FIX 820: Llama a LLM (Claude/OpenAI) con prompt single-purpose."""
        config = NARROW_PROMPTS.get(prompt_key)
        if not config:
            return None

        # FIX 768: Check cache BEFORE calling LLM
        cached = narrow_cache.lookup(self.state.value, prompt_key, texto)
        if cached is not None:
            return cached

        system_prompt = config["system"]

        # Sustituir variables de contexto en prompt
        if '{state}' in system_prompt:
            system_prompt = system_prompt.replace('{state}', self.state.value)
        if '{context_summary}' in system_prompt:
            summary = self._build_context_summary()
            system_prompt = system_prompt.replace('{context_summary}', summary)

        # FIX 820: Agregar contexto FSM al prompt para mejor razonamiento
        fsm_context = self._build_fsm_context_820()
        if fsm_context:
            system_prompt += f"\n\n[CONTEXTO FSM]\n{fsm_context}"

        try:
            # FIX 820: Usar llm_client adapter (Claude o OpenAI según config)
            openai_client = None
            if agente and hasattr(agente, 'openai_client'):
                openai_client = agente.openai_client

            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": texto},
            ]

            # Agregar últimos 4 mensajes de contexto si disponible
            if agente and hasattr(agente, 'conversation_history'):
                history = agente.conversation_history[-4:]
                messages = [{"role": "system", "content": system_prompt}] + history + [
                    {"role": "user", "content": texto}
                ]

            result = llm_client.chat_completion(
                messages=messages,
                openai_client=openai_client,
                temperature=config.get("temperature", 0.5),
                max_tokens=config.get("max_tokens", 80),
                timeout=3.0,
            )

            result = result.strip()

            # FIX 822: Anti-repetición en LLM_NARROW
            # BRUCE2539: Claude repitió "segunda opción" 4 veces en loop
            if agente and hasattr(agente, 'conversation_history'):
                recent_bruce = [m.get('content', '') for m in agente.conversation_history[-6:]
                                if m.get('role') == 'assistant']
                from difflib import SequenceMatcher
                for prev in recent_bruce:
                    if prev and result and SequenceMatcher(None, prev.lower(), result.lower()).ratio() >= 0.75:
                        print(f"  [FSM LLM_NARROW:{prompt_key}] REPETIDO ({SequenceMatcher(None, prev.lower(), result.lower()).ratio():.0%}) -> fallthrough")
                        return None  # Fallthrough a lógica existente del agente

            print(f"  [FSM LLM_NARROW:{prompt_key}] -> '{result[:80]}'")

            # FIX 768: Store in cache AFTER successful response
            narrow_cache.store(self.state.value, prompt_key, texto, result)

            return result

        except Exception as e:
            print(f"  [FSM LLM_NARROW ERROR] {prompt_key}: {e}")
            return None  # Fallthrough a lógica existente

    def _build_fsm_context_820(self) -> str:
        """FIX 820/908: Construye contexto FSM para inyectar en prompts narrow."""
        ctx = self.context
        parts = [f"Estado: {self.state.value}"]
        if ctx.canales_rechazados:
            parts.append(f"Canales rechazados por cliente: {', '.join(ctx.canales_rechazados)}. NO pedir estos canales")
        if ctx.datos_capturados:
            parts.append(f"Datos ya capturados: {ctx.datos_capturados}. NO pedir estos datos de nuevo")
        if ctx.callback_pedido:
            parts.append(f"Callback solicitado: si")
        if ctx.callback_hora:
            parts.append(f"Hora callback: {ctx.callback_hora}")
        if ctx.encargado_es_interlocutor:
            parts.append("El interlocutor ES el encargado de compras")
        if ctx.cliente_no_autorizado:
            parts.append("El cliente NO esta autorizado para dar datos")
        # FIX 908: Contexto adicional para GPT
        if not ctx.pitch_dado:
            parts.append("IMPORTANTE: Aun NO se ha dado el pitch. Explica primero que es NIOVAL antes de pedir datos")
        if ctx.pedir_datos_count >= 2:
            parts.append(f"ATENCION: Ya se pidieron datos {ctx.pedir_datos_count} veces sin exito. Cambiar de tactica o despedirse")
        if ctx.catalogo_prometido:
            parts.append("Ya se prometio enviar catalogo")
        return "\n".join(parts)

    # ----------------------------------------------------------
    # Helpers
    # ----------------------------------------------------------
    def _get_canal_alternativo(self) -> str:
        """Determina canal alternativo basado en rechazos."""
        rechazados = set(self.context.canales_rechazados)
        if 'whatsapp' in rechazados:
            if 'correo' not in rechazados:
                return "correo electronico"
            return "telefono fijo"
        if 'correo' in rechazados:
            return "WhatsApp"
        return "correo electronico o telefono"

    def _build_context_summary(self) -> str:
        """Genera resumen de contexto para GPT narrow."""
        parts = []
        if self.context.pitch_dado:
            parts.append("pitch dado")
        if self.context.encargado_preguntado:
            parts.append("encargado preguntado")
        if self.context.encargado_es_interlocutor:
            parts.append("cliente es encargado")
        if self.context.canales_rechazados:
            parts.append(f"rechazaron: {', '.join(self.context.canales_rechazados)}")
        if self.context.datos_capturados:
            parts.append(f"capturados: {', '.join(self.context.datos_capturados.keys())}")
        if self.context.callback_pedido:
            parts.append("callback pedido")
        return "; ".join(parts) if parts else "inicio de conversacion"

    def _update_context(self, intent: FSMIntent, texto: str,
                        transition: Transition, agente=None):
        """Actualiza contexto FSM tras transición."""
        self.context.turnos_bruce += 1
        self.context.ultimo_template = transition.template_key

        # FIX 866B: Reset verificacion_consecutivas cuando intent no es VERIFICATION
        if intent != FSMIntent.VERIFICATION:
            self.context.verificacion_consecutivas = 0

        # Track pitch dado
        if transition.template_key in ('pitch_inicial', 'pitch_encargado',
                                        'pitch_persona_nueva', 'identificacion_pitch',
                                        'repitch_encargado',  # FIX 791
                                        'pitch_completo_894', 'pitch_y_encargado_894'):  # FIX 895
            self.context.pitch_dado = True

        # Track encargado preguntado
        # FIX 785: BRUCE2492/2497 - pitch_inicial ya incluye "¿Se encontrará el encargado?"
        # FIX 857: Todos los templates de pitch incluyen la pregunta → BRUCE2462/2458/2419
        #   Solo pitch_inicial e identificacion_pitch van a BUSCANDO_ENCARGADO directamente
        #   pitch_persona_nueva, pitch_encargado, repitch_encargado también preguntan
        if transition.template_key in ('preguntar_encargado', 'pitch_inicial',
                                       'identificacion_pitch', 'pitch_persona_nueva',
                                       'pitch_encargado', 'repitch_encargado',
                                       'pitch_y_encargado_894'):  # FIX 895
            self.context.encargado_preguntado = True

        # Track encargado es interlocutor
        if intent == FSMIntent.MANAGER_PRESENT:
            self.context.encargado_es_interlocutor = True
            self.context.encargado_identificado = True  # FIX 1010: encargado ya se presentó

        # FIX 1010: También marcar al transicionar a ENCARGADO_PRESENTE
        if transition.next_state == FSMState.ENCARGADO_PRESENTE:
            self.context.encargado_identificado = True

        # Track canales
        # FIX 838: Incluir pedir_alternativa_* para que canal_solicitado se actualice
        # cuando FIX 763 pide canal alternativo (antes solo trackeaba pedir_whatsapp/pedir_correo)
        if transition.template_key in ('pedir_whatsapp', 'pedir_alternativa_whatsapp'):
            self.context.canal_solicitado = 'whatsapp'
            if 'whatsapp' not in self.context.canales_intentados:
                self.context.canales_intentados.append('whatsapp')
        elif transition.template_key in ('pedir_correo', 'pedir_alternativa_correo'):
            self.context.canal_solicitado = 'correo'
            if 'correo' not in self.context.canales_intentados:
                self.context.canales_intentados.append('correo')
        elif transition.template_key == 'pedir_alternativa_telefono':
            self.context.canal_solicitado = 'telefono'
            if 'telefono' not in self.context.canales_intentados:
                self.context.canales_intentados.append('telefono')

        # FIX 1005: Si canal_solicitado='correo' y cliente dio teléfono → aceptar como WhatsApp
        # Caso: Bruce pide correo, cliente da 10 dígitos → tratar como WhatsApp alternativo
        # (el cliente probablemente prefiere WhatsApp en vez de correo)
        if (intent == FSMIntent.DICTATING_COMPLETE_PHONE and
                self.context.canal_solicitado == 'correo' and
                'correo' not in self.context.canales_rechazados):
            print(f"  [FIX 1005] Cliente dio telefono cuando se pedia correo -> "
                  f"tratar como WhatsApp (canal_solicitado: correo -> whatsapp)")
            self.context.canal_solicitado = 'whatsapp'

        # Track rechazos
        # FIX 838B: Usar 'if' en vez de 'elif' + siempre rechazar canal_solicitado
        # Antes: "Es que no tengo WhatsApp" (mientras Bruce pedia correo) solo rechazaba whatsapp
        # Ahora: rechaza TANTO whatsapp (del texto) como correo (canal_solicitado)
        if intent == FSMIntent.REJECT_DATA:
            tn = _normalize(texto)
            if 'whatsapp' in tn or 'whats' in tn or 'wats' in tn:
                if 'whatsapp' not in self.context.canales_rechazados:
                    self.context.canales_rechazados.append('whatsapp')
            if 'correo' in tn or 'email' in tn:
                if 'correo' not in self.context.canales_rechazados:
                    self.context.canales_rechazados.append('correo')
            if self.context.canal_solicitado:
                c = self.context.canal_solicitado
                if c not in self.context.canales_rechazados:
                    self.context.canales_rechazados.append(c)

        # Track catálogo
        if transition.template_key in ('confirmar_telefono', 'confirmar_correo',
                                        'despedida_catalogo_prometido'):
            self.context.catalogo_prometido = True

        # FIX 789B: Track callback hora preguntada
        if transition.template_key == 'preguntar_hora_callback':
            self.context.callback_hora_preguntada = True

        # FIX 849: Track callback confirmaciones emitidas
        if transition.template_key in ('confirmar_callback', 'confirmar_callback_generico'):
            self.context.callback_confirmaciones += 1

        # FIX 855: Track preguntas de producto respondidas
        if transition.template_key == 'responder_pregunta_producto':
            self.context.preguntas_producto_respondidas += 1

        # FIX 861: Track si ya pedimos WhatsApp (para evitar PREGUNTA_REPETIDA en FIX 856)
        if transition.template_key in ('pedir_whatsapp_o_correo', 'pedir_whatsapp', 'pedir_correo'):
            self.context.whatsapp_ya_solicitado = True

        # FIX 909: Track pedidos de datos para detección de LOOP
        _pedir_datos_templates = (
            'pedir_whatsapp', 'pedir_correo', 'pedir_telefono',
            'pedir_whatsapp_o_correo', 'pedir_whatsapp_o_correo_breve',
            'pedir_alternativa_correo', 'pedir_alternativa_telefono',
            'pedir_alternativa_whatsapp', 'pedir_contacto_alternativo',
            'pedir_numero_directo_885', 'pedir_telefono_directo_891',
            'pedir_dato_contacto_892', 'digame_numero',
        )
        if transition.template_key in _pedir_datos_templates:
            self.context.pedir_datos_count += 1

        # FIX 919: Track turno en que se dio el pitch
        if transition.template_key in ('pitch_inicial', 'pitch_encargado',
                                        'pitch_persona_nueva', 'pitch_completo_894'):
            self.context.pitch_turno = self.context.turnos_bruce

        # Track claro_espero
        if transition.template_key == 'claro_espero':
            self.context.tiempo_claro_espero = time.time()

        # Track donde_anotar
        if transition.template_key == 'tiene_donde_anotar':
            self.context.donde_anotar_preguntado = True

        # Track ofrecer contacto (para recovery DESPEDIDA -> dictar número)
        self.context.ultimo_fue_ofrecer_contacto = (
            transition.template_key in ('ofrecer_contacto_bruce', 'tiene_donde_anotar')
        )

        # Track callback
        if intent == FSMIntent.CALLBACK:
            self.context.callback_pedido = True
            # FIX 784: Extraer hora (dígitos o palabras)
            hora = self._detectar_hora_en_texto_784(texto)
            if hora:
                self.context.callback_hora = hora

        # FIX 934: BRUCE2625 - MANAGER_ABSENT que también contiene info de callback
        # "Si gustas marcar en una hora, salieron" → classified as MANAGER_ABSENT
        # pero la hora de callback está en el texto. Guardarla para uso futuro.
        if intent == FSMIntent.MANAGER_ABSENT:
            hora = self._detectar_hora_en_texto_784(texto)
            if hora:
                self.context.callback_hora = hora
                self.context.callback_pedido = True
                print(f"  [FIX 934] MANAGER_ABSENT con hora callback implícita: {hora}")

    # ----------------------------------------------------------
    # FIX 784: Detectar hora en texto (dígitos + palabras)
    # ----------------------------------------------------------
    _HORAS_PALABRAS_784 = {
        'una': '1', 'dos': '2', 'tres': '3', 'cuatro': '4', 'cinco': '5',
        'seis': '6', 'siete': '7', 'ocho': '8', 'nueve': '9', 'diez': '10',
        'once': '11', 'doce': '12',
    }

    def _detectar_hora_en_texto_784(self, texto: str) -> Optional[str]:
        """FIX 784: Detecta hora en texto, tanto dígitos como palabras.

        Returns: str con la hora (e.g. 'a las 8 de la mañana') o None.
        """
        tn = _normalize(texto)

        # 1. Hora numérica: "a las 8", "a las 9:00"
        hour_match = re.search(r'a las (\d{1,2})', tn)
        if hour_match:
            hora_str = f"a las {hour_match.group(1)}"
            # Agregar periodo si está
            if 'manana' in tn or 'de la manana' in tn:
                hora_str += " de la manana"
            elif 'tarde' in tn:
                hora_str += " de la tarde"
            elif 'noche' in tn:
                hora_str += " de la noche"
            return hora_str

        # 2. Hora en palabras: "a las ocho", "a las nueve de la mañana"
        for palabra, digito in self._HORAS_PALABRAS_784.items():
            pattern = f'a las {palabra}'
            if pattern in tn:
                hora_str = f"a las {digito}"
                if 'manana' in tn or 'de la manana' in tn:
                    hora_str += " de la manana"
                elif 'tarde' in tn:
                    hora_str += " de la tarde"
                elif 'noche' in tn:
                    hora_str += " de la noche"
                return hora_str

        # 3. FIX 934: Tiempos relativos: "en una hora", "en un rato", "en media hora"
        if 'en una hora' in tn:
            return "en una hora"
        if 'en media hora' in tn:
            return "en media hora"
        if 'en un rato' in tn or 'al rato' in tn or 'ahorita no' in tn:
            return "mas tarde"
        if 'mas tarde' in tn or 'mas tardecito' in tn:
            return "mas tarde"

        # 3b. Solo periodo: "en la mañana", "en la tarde" (sin hora específica)
        if 'en la manana' in tn or 'por la manana' in tn:
            return "en la manana"
        if 'en la tarde' in tn or 'por la tarde' in tn:
            return "en la tarde"
        if 'en la noche' in tn or 'por la noche' in tn:
            return "en la noche"

        # FIX 1033: Callbacks long-term ("en unos meses", "en dos semanas", etc.)
        # Devolver la frase como hora para que se use confirmar_callback_generico
        _long_term_patterns = [
            ('en unos meses', 'en unos meses'), ('en algunos meses', 'en algunos meses'),
            ('en tres meses', 'en tres meses'), ('en dos meses', 'en dos meses'),
            ('en un mes', 'en un mes'), ('dentro de un mes', 'en un mes'),
            ('dentro de dos meses', 'en dos meses'), ('dentro de tres meses', 'en tres meses'),
            ('en unas semanas', 'en unas semanas'), ('en dos semanas', 'en dos semanas'),
            ('en tres semanas', 'en tres semanas'), ('dentro de unas semanas', 'en unas semanas'),
            ('pasado manana', 'pasado manana'), ('pasado mañana', 'pasado manana'),
        ]
        for pattern, label in _long_term_patterns:
            if pattern in tn:
                return label

        return None

    # ----------------------------------------------------------
    # FIX 763: REJECT_DATA dinámico
    # ----------------------------------------------------------
    def _handle_reject_data_763(self, texto: str = "") -> Transition:
        """FIX 763: Alternación inteligente de canales cuando cliente rechaza."""
        rechazados = set(self.context.canales_rechazados)
        # Incluir canal actual (será agregado por _update_context después)
        if self.context.canal_solicitado:
            rechazados.add(self.context.canal_solicitado)

        # FIX 834: BRUCE2549 - Pre-parsear canal rechazado del texto ACTUAL
        # _update_context() corre DESPUÉS de esta función, así que canales_rechazados
        # aún no tiene el canal que el cliente ACABA de rechazar en este turno.
        # Parseamos el texto aquí para incluirlo en rechazados ANTES de elegir alternativa.
        if texto:
            tn834 = _normalize(texto)
            # FIX 909: Expanded channel detection from text
            if 'whatsapp' in tn834 or 'whats' in tn834 or 'wats' in tn834:
                rechazados.add('whatsapp')
            if 'correo' in tn834 or 'email' in tn834 or 'mail' in tn834:
                rechazados.add('correo')
            if 'telefono' in tn834 or 'celular' in tn834 or 'numero' in tn834:
                # Solo si es rechazo explícito (no "te doy mi número")
                _reject_words_834 = ['no tengo', 'tampoco', 'no manejo', 'no uso', 'no cuento']
                if any(r in tn834 for r in _reject_words_834):
                    rechazados.add('telefono')
            # FIX 909: Si dice "no tengo datos" o "no me llegan" sin especificar canal,
            # inferir que rechaza el canal que Bruce acaba de pedir
            _generic_reject_909 = ['no tengo datos', 'no me llegan', 'no lo uso',
                                    'no lo usamos', 'no usa', 'no lo manejo', 'no lo manejamos',
                                    'no tiene de eso', 'es de la vieja escuela',
                                    'no reviso correos', 'no revisa correos',
                                    'no checa correos', 'nunca revisa',
                                    'no tenemos internet', 'no hay internet']
            if any(g in tn834 for g in _generic_reject_909):
                # Inferir canal del contexto: que pidio Bruce en ultimo turno
                if self.context.canal_solicitado:
                    rechazados.add(self.context.canal_solicitado)
                    print(f"  [FIX 909] Rechazo generico -> inferido canal={self.context.canal_solicitado}")
                else:
                    # Si no hay canal_solicitado, inferir del ultimo template de Bruce
                    _ult_bruce = ''
                    for _m909 in reversed(getattr(self.context, '_historial_bruce', [])):
                        _ult_bruce = _m909.lower()
                        break
                    if 'whatsapp' in _ult_bruce:
                        rechazados.add('whatsapp')
                    elif 'correo' in _ult_bruce:
                        rechazados.add('correo')
            print(f"  [FIX 834+909] REJECT_DATA: rechazados pre-parse={rechazados} texto='{texto[:60]}'")

        S = FSMState
        A = ActionType

        if 'whatsapp' not in rechazados:
            print(f"  [FIX 763] REJECT_DATA: rechazados={rechazados} -> pedir WhatsApp")
            return Transition(S.CAPTURANDO_CONTACTO, A.TEMPLATE, "pedir_alternativa_whatsapp")
        elif 'correo' not in rechazados:
            print(f"  [FIX 763] REJECT_DATA: rechazados={rechazados} -> pedir correo")
            return Transition(S.CAPTURANDO_CONTACTO, A.TEMPLATE, "pedir_alternativa_correo")
        elif 'telefono' not in rechazados:
            print(f"  [FIX 763] REJECT_DATA: rechazados={rechazados} -> pedir teléfono")
            return Transition(S.CAPTURANDO_CONTACTO, A.TEMPLATE, "pedir_alternativa_telefono")
        else:
            # Todos los canales rechazados -> ofrecer número de Bruce
            print(f"  [FIX 763] REJECT_DATA: TODOS rechazados -> ofrecer contacto Bruce")
            return Transition(S.OFRECIENDO_CONTACTO, A.TEMPLATE, "ofrecer_contacto_bruce")

    # ----------------------------------------------------------
    # State info (para debug/logging)
    # ----------------------------------------------------------
    def get_state_info(self) -> Dict[str, Any]:
        """Retorna info del estado actual para logging."""
        return {
            "state": self.state.value,
            "pitch_dado": self.context.pitch_dado,
            "encargado_preguntado": self.context.encargado_preguntado,
            "canales_rechazados": self.context.canales_rechazados,
            "datos_capturados": list(self.context.datos_capturados.keys()),
            "turnos": self.context.turnos_bruce,
        }
