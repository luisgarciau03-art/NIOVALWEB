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
    _reject_quick_821 = ['no tengo', 'no puedo', 'tampoco tengo', 'solo tengo',
                          'no manejo', 'no uso', 'no le puedo', 'no te puedo']
    if tl.endswith(',') and len(tn) < 40:
        if not any(r in tn for r in _reject_quick_821):
            return FSMIntent.CONTINUATION
        # else: fall through — será clasificado como REJECT_DATA más abajo

    # --- FIX 783: Despedida ANTES de dictado (BRUCE2494 P0) ---
    # "No una disculpa... hasta luego" tiene num_words=2 ("no","una") -> DICTATING_PARTIAL
    # Farewell debe chequearse ANTES de conteo numérico para evitar malclasificación
    # NOTA: NO incluir "buenas tardes/noches/buen dia" aquí - son saludos ambiguos
    farewell_strong_783 = ['hasta luego', 'adios', 'bye', 'nos vemos', 'que le vaya bien',
                           'hasta pronto']
    farewell_weak_783 = ['gracias', 'muchas gracias', 'ok gracias']
    if any(f in tn for f in farewell_strong_783):
        return FSMIntent.FAREWELL
    if any(f == tn for f in farewell_weak_783):  # exact match only
        return FSMIntent.FAREWELL

    # --- FIX 781: Email completo ANTES de dictado (email con números no es dictado parcial) ---
    # BRUCE2472: "Ferrebillas seis cuatro arroba gmail punto com" tiene num_words=4
    # Sin este check, se clasifica como DICTATING_PARTIAL y nunca llega a email detection
    if '@' in texto or ('arroba' in tn and ('punto' in tn or 'gmail' in tn or 'hotmail' in tn)):
        return FSMIntent.DICTATING_COMPLETE_EMAIL

    # --- FIX 781: Email parcial ANTES de dictado ---
    email_signals = ['arroba', 'gmail', 'hotmail', 'outlook', 'yahoo', 'punto com', 'punto mx']
    if any(s in tn for s in email_signals):
        return FSMIntent.OFFER_DATA

    # --- Dictado: dígitos numéricos ---
    digits = re.findall(r'\d', texto)
    num_words = sum(1 for w in tn.split() if w in _NUMS_ESP)

    # FIX 780: Excluir frases con contexto temporal de dictado parcial
    # BRUCE2468: "llegan en una hora" -> "una" × 2 = num_words=2 -> falso DICTATING_PARTIAL
    # Palabras temporales junto a números no son dictado de teléfono
    _time_context = {'hora', 'horas', 'rato', 'minuto', 'minutos', 'momento', 'dia', 'dias',
                     'semana', 'semanas', 'mes', 'meses', 'tarde', 'manana', 'noche'}
    words = set(tn.split())
    has_time_context = bool(words & _time_context)

    if len(digits) >= 10 or (len(digits) + num_words) >= 10:
        # FIX 780: 10+ dígitos con contexto temporal en BUSCANDO_ENCARGADO = callback, no teléfono
        if has_time_context and state == FSMState.BUSCANDO_ENCARGADO:
            pass  # Fall through to callback/other classifiers
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
        'marco equivocado', 'llamo equivocado',
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
    ]
    if any(n in tn for n in no_interest):
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
    ]
    if any(r in tn for r in reject_data):
        return FSMIntent.REJECT_DATA

    # --- Oferta de dato ---
    offer_data = [
        'te doy', 'le doy', 'te paso', 'le paso', 'te puedo dar',
        'le puedo dar', 'te puedo proporcionar', 'le puedo proporcionar',
        'te puedo pasar', 'anota', 'apunta', 'si gusta anotar',
        'tiene donde anotar', 'yo le doy el correo', 'por correo',
        'te mando', 'le mando', 'mi correo es', 'mi whatsapp es',
        'mi numero es', 'el numero es', 'el correo es',
        'mandelo por whatsapp', 'por whatsapp', 'mandalo por whatsapp',
        'al whatsapp', 'a mi whatsapp', 'a mi correo',
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
    ]
    if any(m in tn for m in manager_absent):
        return FSMIntent.MANAGER_ABSENT
    # "No" a secas después de preguntar por encargado = MANAGER_ABSENT contextual
    if tn in ('no', 'no fijese', 'no fijate', 'no senor', 'no senorita'):
        if context.encargado_preguntado and state == FSMState.BUSCANDO_ENCARGADO:
            return FSMIntent.MANAGER_ABSENT

    # --- Encargado presente ("soy yo") ---
    manager_present = [
        'soy yo', 'yo soy', 'si soy', 'yo mero', 'yo soy el encargado',
        'yo soy la encargada', 'si yo soy', 'aqui yo', 'servidor',
        'yo me encargo', 'conmigo', 'a mi',
    ]
    if any(m in tn for m in manager_present):
        return FSMIntent.MANAGER_PRESENT

    # --- Transfer (espere en línea) ---
    transfer = [
        'espere un momento', 'espereme', 'espera por favor', 'permitame',
        'permiteme', 'un momento', 'un momentito', 'un segundo',
        'dejeme ver', 'le comunico', 'se lo paso', 'se lo comunico',
        'ahorita le paso', 'ahorita se lo comunico',
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
    ]
    if any(c in tn for c in callback_guard):
        return FSMIntent.CALLBACK
    if any(t in tn for t in transfer):
        return FSMIntent.TRANSFER

    # --- Callback ---
    callback = [
        'mas tarde', 'manana', 'otro dia', 'la proxima semana',
        'despues', 'luego', 'vuelva a llamar', 'llame despues',
        'marque despues', 'regrese', 'vuelva', 'cuando llegue',
        'a las', 'en la tarde', 'en la manana', 'por la manana',
    ]
    if any(c in tn for c in callback):
        if state in (FSMState.BUSCANDO_ENCARGADO, FSMState.ENCARGADO_AUSENTE,
                     FSMState.PITCH, FSMState.ESPERANDO_TRANSFERENCIA,
                     FSMState.ENCARGADO_PRESENTE):
            return FSMIntent.CALLBACK

    # --- Otra sucursal ---
    another = [
        'otra sucursal', 'otro local', 'no es aqui', 'numero equivocado',
        'se equivoco', 'no es esta sucursal', 'otra ubicacion',
        # FIX 866A: BRUCE2111 - "tienes que hablar a la sucursal de Sahuayo" → ANOTHER_BRANCH
        'tienes que hablar a la sucursal', 'tiene que hablar a la sucursal',
        'hablar a la sucursal', 'llamar a la sucursal', 'llame a la sucursal',
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

    # --- Pregunta general ---
    question_markers = ['que', 'cual', 'como', 'cuando', 'donde', 'cuanto', 'por que']
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
    ]
    if tn in confirm_exact or any(c == tn for c in confirm_exact):
        return FSMIntent.CONFIRMATION

    # --- Continuación (texto termina en conector) ---
    if tn.endswith(' y') or tn.endswith(' o') or tn.endswith(' pero'):
        return FSMIntent.CONTINUATION

    # --- Interés implícito ---
    interest = [
        'me interesa', 'si me interesa', 'digame', 'cuenteme',
        'a ver', 'que ofrece', 'que tiene',
    ]
    if any(i in tn for i in interest):
        return FSMIntent.INTEREST

    # --- FIX 824: "No tengo" corto sin canal = rechazo genérico ---
    # BRUCE2538: "No tengo" (2 palabras) -> UNKNOWN -> FIX 791 pide WhatsApp de nuevo
    # En estados de captura, "no tengo" corto = rechazo de dato
    # FIX 837: Expandido con mas variantes
    _reject_short_824 = ['no tengo', 'tampoco tengo', 'no puedo', 'tampoco', 'no manejo',
                          'solo telefono', 'solo fijo', 'nada mas telefono', 'solo celular',
                          'no uso', 'no cuento con', 'no lo tengo', 'eso no', 'no de eso no',
                          'solo el telefono', 'solo el fijo', 'nomas telefono', 'puro telefono']
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

        # 1.5. Recovery: DESPEDIDA + CONFIRMATION cuando último fue ofrecer contacto
        if (self.state == FSMState.DESPEDIDA and
                intent == FSMIntent.CONFIRMATION and
                self.context.ultimo_fue_ofrecer_contacto):
            transition = Transition(
                next_state=FSMState.DESPEDIDA,
                action_type=ActionType.TEMPLATE,
                template_key="dictar_numero_bruce",
            )
        else:
            transition = None

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

        # FIX 784: BRUCE2490 - Si callback y cliente YA mencionó hora, confirmar en vez de preguntar
        if (intent == FSMIntent.CALLBACK and
                transition.template_key == 'preguntar_hora_callback'):
            hora_detectada = self._detectar_hora_en_texto_784(texto)
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
    # FIX 791: Selección stateful de template para UNKNOWN
    # ----------------------------------------------------------
    def _handle_unknown_stateful(self, texto: str) -> Optional[Transition]:
        """FIX 791: Selecciona template basado en estado + contexto para UNKNOWN.

        Reemplaza GPT_NARROW en 90%+ de casos UNKNOWN.
        Retorna Transition con template o None para fallback a GPT_NARROW.
        Actualiza context flags para evitar loops por template repetido.
        """
        S = FSMState
        A = ActionType
        ctx = self.context

        if self.state == S.PITCH:
            # PITCH+UNKNOWN: cliente responde vago al pitch
            # Flags se actualizan via _update_context() existente (lines 1204-1213)
            if not ctx.encargado_preguntado:
                return Transition(S.BUSCANDO_ENCARGADO, A.TEMPLATE, "preguntar_encargado")
            elif not ctx.canales_intentados:
                return Transition(S.CAPTURANDO_CONTACTO, A.TEMPLATE, "pedir_whatsapp_o_correo")
            else:
                return Transition(S.CAPTURANDO_CONTACTO, A.TEMPLATE, "ofrecer_catalogo_sin_compromiso")

        elif self.state == S.BUSCANDO_ENCARGADO:
            # Flags se actualizan via _update_context() existente
            if not ctx.pitch_dado:
                return Transition(S.BUSCANDO_ENCARGADO, A.TEMPLATE, "repitch_encargado")
            elif ctx.encargado_preguntado:
                return Transition(S.CAPTURANDO_CONTACTO, A.TEMPLATE, "pedir_whatsapp_o_correo")
            else:
                return Transition(S.BUSCANDO_ENCARGADO, A.TEMPLATE, "preguntar_encargado")

        elif self.state == S.ENCARGADO_AUSENTE:
            if not ctx.canales_intentados:
                return Transition(S.CAPTURANDO_CONTACTO, A.TEMPLATE, "pedir_whatsapp_o_correo")
            elif ctx.callback_pedido:
                return Transition(S.DESPEDIDA, A.TEMPLATE, "despedida_agradecimiento")
            else:
                return Transition(S.ENCARGADO_AUSENTE, A.TEMPLATE, "preguntar_horario_encargado")

        elif self.state == S.ENCARGADO_PRESENTE:
            if not ctx.canales_intentados:
                return Transition(S.CAPTURANDO_CONTACTO, A.TEMPLATE, "pedir_whatsapp")
            else:
                return Transition(S.CAPTURANDO_CONTACTO, A.TEMPLATE, "pitch_catalogo_whatsapp")

        elif self.state == S.CAPTURANDO_CONTACTO:
            return Transition(S.CAPTURANDO_CONTACTO, A.TEMPLATE, "digame_numero")

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
        add(S.SALUDO, I.NO_INTEREST,   S.DESPEDIDA, A.TEMPLATE, "despedida_cortes")
        add(S.SALUDO, I.FAREWELL,      S.DESPEDIDA, A.TEMPLATE, "despedida_cortes")
        add(S.SALUDO, I.WRONG_NUMBER,  S.DESPEDIDA, A.TEMPLATE, "despedida_area_equivocada")
        add(S.SALUDO, I.OFFER_DATA,    S.DICTANDO_DATO, A.ACKNOWLEDGE, "aja_digame")
        add(S.SALUDO, I.MANAGER_PRESENT, S.ENCARGADO_PRESENTE, A.TEMPLATE, "pitch_encargado")
        add(S.SALUDO, I.MANAGER_ABSENT, S.ENCARGADO_AUSENTE, A.TEMPLATE, "pedir_contacto_alternativo")
        add(S.SALUDO, I.UNKNOWN,       S.PITCH, A.TEMPLATE, "pitch_inicial")
        # FIX 786: CONTINUATION - cliente sigue hablando, no interrumpir
        add(S.SALUDO, I.CONTINUATION,  S.SALUDO, A.NOOP, None)

        # === PITCH ===
        add(S.PITCH, I.CONFIRMATION,   S.BUSCANDO_ENCARGADO, A.TEMPLATE, "preguntar_encargado")
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
        add(S.BUSCANDO_ENCARGADO, I.INTEREST,        S.CAPTURANDO_CONTACTO, A.TEMPLATE, "pedir_whatsapp")
        add(S.BUSCANDO_ENCARGADO, I.VERIFICATION,    S.BUSCANDO_ENCARGADO, A.TEMPLATE, "verificacion_aqui_estoy")
        add(S.BUSCANDO_ENCARGADO, I.REJECT_DATA,     S.OFRECIENDO_CONTACTO, A.TEMPLATE, "ofrecer_contacto_bruce")
        # FIX 754: Cliente dicta teléfono/email completo buscando encargado -> capturar
        add(S.BUSCANDO_ENCARGADO, I.DICTATING_COMPLETE_PHONE, S.CONTACTO_CAPTURADO, A.TEMPLATE, "confirmar_telefono")
        add(S.BUSCANDO_ENCARGADO, I.DICTATING_COMPLETE_EMAIL, S.CONTACTO_CAPTURADO, A.TEMPLATE, "confirmar_correo")
        add(S.BUSCANDO_ENCARGADO, I.DICTATING_PARTIAL,        S.DICTANDO_DATO, A.ACKNOWLEDGE, "aja_si")
        add(S.BUSCANDO_ENCARGADO, I.UNKNOWN,         S.BUSCANDO_ENCARGADO, A.GPT_NARROW, "conversacion_libre")
        # FIX 786: CONTINUATION - cliente sigue hablando
        add(S.BUSCANDO_ENCARGADO, I.CONTINUATION,  S.BUSCANDO_ENCARGADO, A.NOOP, None)

        # === ENCARGADO_PRESENTE ===
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
        # FIX 788: Gaps - IDENTITY, CLOSED
        add(S.ENCARGADO_AUSENTE, I.IDENTITY,      S.ENCARGADO_AUSENTE, A.TEMPLATE, "identificacion_nioval")
        add(S.ENCARGADO_AUSENTE, I.CLOSED,        S.DESPEDIDA, A.TEMPLATE, "despedida_cerrado")

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
        add(S.ESPERANDO_TRANSFERENCIA, I.UNKNOWN,         S.ESPERANDO_TRANSFERENCIA, A.NOOP, None)
        # FIX 786: CONTINUATION - cliente sigue hablando durante espera
        add(S.ESPERANDO_TRANSFERENCIA, I.CONTINUATION,   S.ESPERANDO_TRANSFERENCIA, A.NOOP, None)
        # FIX 788: Gaps - NO_INTEREST, CALLBACK, DICTATING_*, WRONG_NUMBER
        add(S.ESPERANDO_TRANSFERENCIA, I.NO_INTEREST,    S.DESPEDIDA, A.TEMPLATE, "despedida_cortes")
        add(S.ESPERANDO_TRANSFERENCIA, I.CALLBACK,       S.ENCARGADO_AUSENTE, A.TEMPLATE, "preguntar_hora_callback")
        add(S.ESPERANDO_TRANSFERENCIA, I.WRONG_NUMBER,   S.DESPEDIDA, A.TEMPLATE, "despedida_area_equivocada")
        add(S.ESPERANDO_TRANSFERENCIA, I.DICTATING_COMPLETE_PHONE, S.CONTACTO_CAPTURADO, A.TEMPLATE, "confirmar_telefono")
        add(S.ESPERANDO_TRANSFERENCIA, I.DICTATING_COMPLETE_EMAIL, S.CONTACTO_CAPTURADO, A.TEMPLATE, "confirmar_correo")
        add(S.ESPERANDO_TRANSFERENCIA, I.DICTATING_PARTIAL,        S.DICTANDO_DATO, A.ACKNOWLEDGE, "aja_si")

        # === CAPTURANDO_CONTACTO ===
        add(S.CAPTURANDO_CONTACTO, I.OFFER_DATA,              S.DICTANDO_DATO, A.ACKNOWLEDGE, "aja_digame")
        add(S.CAPTURANDO_CONTACTO, I.CONFIRMATION,            S.DICTANDO_DATO, A.TEMPLATE, "digame_numero")
        add(S.CAPTURANDO_CONTACTO, I.DICTATING_PARTIAL,       S.DICTANDO_DATO, A.ACKNOWLEDGE, "aja_si")
        add(S.CAPTURANDO_CONTACTO, I.DICTATING_COMPLETE_PHONE, S.CONTACTO_CAPTURADO, A.TEMPLATE, "confirmar_telefono")
        add(S.CAPTURANDO_CONTACTO, I.DICTATING_COMPLETE_EMAIL, S.CONTACTO_CAPTURADO, A.TEMPLATE, "confirmar_correo")
        add(S.CAPTURANDO_CONTACTO, I.REJECT_DATA,             S.CAPTURANDO_CONTACTO, A.TEMPLATE, "pedir_alternativa_correo")
        add(S.CAPTURANDO_CONTACTO, I.NO_INTEREST,             S.DESPEDIDA, A.TEMPLATE, "despedida_no_interesa")
        add(S.CAPTURANDO_CONTACTO, I.FAREWELL,                S.DESPEDIDA, A.TEMPLATE, "despedida_cortes")
        add(S.CAPTURANDO_CONTACTO, I.VERIFICATION,            S.CAPTURANDO_CONTACTO, A.TEMPLATE, "verificacion_aqui_estoy")
        add(S.CAPTURANDO_CONTACTO, I.UNKNOWN,                 S.CAPTURANDO_CONTACTO, A.GPT_NARROW, "conversacion_libre")
        # FIX 786: CONTINUATION - cliente sigue hablando
        add(S.CAPTURANDO_CONTACTO, I.CONTINUATION,           S.CAPTURANDO_CONTACTO, A.NOOP, None)
        # FIX 788: Gaps - IDENTITY, WRONG_NUMBER
        add(S.CAPTURANDO_CONTACTO, I.IDENTITY,               S.CAPTURANDO_CONTACTO, A.TEMPLATE, "identificacion_nioval")
        add(S.CAPTURANDO_CONTACTO, I.WRONG_NUMBER,           S.DESPEDIDA, A.TEMPLATE, "despedida_area_equivocada")
        # FIX 797: En CAPTURANDO_CONTACTO, manejar intents de encargado (eco STT)
        # STT echo "no está" -> MANAGER_ABSENT -> sin transición -> UNKNOWN -> GPT "contacto alternativo"
        add(S.CAPTURANDO_CONTACTO, I.MANAGER_ABSENT,  S.CAPTURANDO_CONTACTO, A.TEMPLATE, "digame_numero")
        add(S.CAPTURANDO_CONTACTO, I.MANAGER_PRESENT, S.CAPTURANDO_CONTACTO, A.TEMPLATE, "digame_numero")
        add(S.CAPTURANDO_CONTACTO, I.QUESTION,        S.CAPTURANDO_CONTACTO, A.GPT_NARROW, "responder_pregunta_producto")

        # === DICTANDO_DATO ===
        add(S.DICTANDO_DATO, I.DICTATING_PARTIAL,       S.DICTANDO_DATO, A.ACKNOWLEDGE, "aja_si")
        add(S.DICTANDO_DATO, I.DICTATING_COMPLETE_PHONE, S.CONTACTO_CAPTURADO, A.TEMPLATE, "confirmar_telefono")
        add(S.DICTANDO_DATO, I.DICTATING_COMPLETE_EMAIL, S.CONTACTO_CAPTURADO, A.TEMPLATE, "confirmar_correo")
        add(S.DICTANDO_DATO, I.CONTINUATION,             S.DICTANDO_DATO, A.ACKNOWLEDGE, "aja_si")
        add(S.DICTANDO_DATO, I.OFFER_DATA,               S.DICTANDO_DATO, A.ACKNOWLEDGE, "aja_si")
        add(S.DICTANDO_DATO, I.CONFIRMATION,             S.DICTANDO_DATO, A.ACKNOWLEDGE, "aja_si")
        add(S.DICTANDO_DATO, I.FAREWELL,                 S.DESPEDIDA, A.TEMPLATE, "despedida_cortes")
        add(S.DICTANDO_DATO, I.VERIFICATION,             S.DICTANDO_DATO, A.TEMPLATE, "verificacion_aqui_estoy")
        # FIX 820: UNKNOWN durante dictado -> Claude decide (no fillers)
        # ANTES: A.ACKNOWLEDGE "aja_si" -> loop de fillers cuando cliente no dicta
        add(S.DICTANDO_DATO, I.UNKNOWN,                  S.DICTANDO_DATO, A.GPT_NARROW, "conversacion_libre")
        # FIX 788: Gaps - NO_INTEREST, REJECT_DATA, IDENTITY
        add(S.DICTANDO_DATO, I.NO_INTEREST,              S.DESPEDIDA, A.TEMPLATE, "despedida_cortes")
        add(S.DICTANDO_DATO, I.REJECT_DATA,              S.OFRECIENDO_CONTACTO, A.TEMPLATE, "ofrecer_contacto_bruce")
        add(S.DICTANDO_DATO, I.IDENTITY,                 S.DICTANDO_DATO, A.TEMPLATE, "identificacion_nioval")
        # FIX 801: BRUCE2522 - QUESTION durante dictado -> responder pregunta y salir de dictado
        # Sin esta transición, QUESTION cae al catch-all UNKNOWN -> filler loop infinito
        add(S.DICTANDO_DATO, I.QUESTION,                 S.CAPTURANDO_CONTACTO, A.GPT_NARROW, "responder_pregunta_producto")

        # === OFRECIENDO_CONTACTO ===
        add(S.OFRECIENDO_CONTACTO, I.CONFIRMATION,  S.OFRECIENDO_CONTACTO, A.TEMPLATE, "tiene_donde_anotar", ["!donde_anotar_preguntado"])
        add(S.OFRECIENDO_CONTACTO, I.INTEREST,      S.OFRECIENDO_CONTACTO, A.TEMPLATE, "tiene_donde_anotar", ["!donde_anotar_preguntado"])
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
        add(S.CONTACTO_CAPTURADO, I.CONFIRMATION, S.DESPEDIDA, A.TEMPLATE, "despedida_catalogo_prometido")
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
        add(S.DESPEDIDA, I.VERIFICATION,  S.DESPEDIDA, A.TEMPLATE, "despedida_cortes")
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
            # FIX 875: pitch_encargado con pitch ya dado → usar versión corta (sin lista de productos)
            # Auditoría 25/02: INFO_NO_SOLICITADA(9x) — Bruce repite descripción de productos
            # cuando el encargado confirma presencia DESPUÉS de que pitch_inicial ya sonó.
            # pitch_dado=True significa que pitch_inicial/pitch_persona_nueva ya fue usado → usar corto.
            if transition.template_key == "pitch_encargado" and self.context.pitch_dado:
                print(f"  [FIX 875] pitch ya dado -> pitch_encargado_corto")
                return self._get_template("pitch_encargado_corto")

            # FIX 878: identificacion_nioval repetido → pivot a pedir contacto
            # BRUCE2551: cliente preguntó "¿Dónde están?" 4x, FSM respondió "Mi nombre es Bruce..." 3x.
            # Si identity_repetidas >= 2, pivotar a pedir_whatsapp_o_correo para avanzar la conv.
            if transition.template_key == "identificacion_nioval":
                self.context.identity_repetidas += 1
                if self.context.identity_repetidas >= 2:
                    print(f"  [FIX 878] identificacion_nioval #{self.context.identity_repetidas} → pivot a pedir_whatsapp_o_correo")
                    # FIX 884: Usar template breve para evitar PREGUNTA_REPETIDA
                    # pedir_whatsapp_o_correo breve tiene palabras distintas al primer pedido.
                    return self._get_template("pedir_whatsapp_o_correo_breve")

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
        """Obtiene template por key. Rota variantes para evitar repetición."""
        templates = TEMPLATES.get(key)
        if not templates:
            return ""
        # FIX 769: Rotar variantes si hay más de una
        if len(templates) > 1:
            idx = getattr(self, '_template_counter', 0)
            response = templates[idx % len(templates)]
            self._template_counter = idx + 1
        else:
            response = templates[0]

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
        """FIX 820: Construye contexto FSM para inyectar en prompts narrow."""
        ctx = self.context
        parts = [f"Estado: {self.state.value}"]
        if ctx.canales_rechazados:
            parts.append(f"Canales rechazados por cliente: {', '.join(ctx.canales_rechazados)}")
        if ctx.datos_capturados:
            parts.append(f"Datos ya capturados: {ctx.datos_capturados}")
        if ctx.callback_pedido:
            parts.append(f"Callback solicitado: si")
        if ctx.callback_hora:
            parts.append(f"Hora callback: {ctx.callback_hora}")
        if ctx.encargado_es_interlocutor:
            parts.append("El interlocutor ES el encargado de compras")
        if ctx.cliente_no_autorizado:
            parts.append("El cliente NO esta autorizado para dar datos")
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
                                        'repitch_encargado'):  # FIX 791
            self.context.pitch_dado = True

        # Track encargado preguntado
        # FIX 785: BRUCE2492/2497 - pitch_inicial ya incluye "¿Se encontrará el encargado?"
        # FIX 857: Todos los templates de pitch incluyen la pregunta → BRUCE2462/2458/2419
        #   Solo pitch_inicial e identificacion_pitch van a BUSCANDO_ENCARGADO directamente
        #   pitch_persona_nueva, pitch_encargado, repitch_encargado también preguntan
        if transition.template_key in ('preguntar_encargado', 'pitch_inicial',
                                       'identificacion_pitch', 'pitch_persona_nueva',
                                       'pitch_encargado', 'repitch_encargado'):
            self.context.encargado_preguntado = True

        # Track encargado es interlocutor
        if intent == FSMIntent.MANAGER_PRESENT:
            self.context.encargado_es_interlocutor = True

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

        # Track rechazos
        # FIX 838B: Usar 'if' en vez de 'elif' + siempre rechazar canal_solicitado
        # Antes: "Es que no tengo WhatsApp" (mientras Bruce pedia correo) solo rechazaba whatsapp
        # Ahora: rechaza TANTO whatsapp (del texto) como correo (canal_solicitado)
        if intent == FSMIntent.REJECT_DATA:
            tn = _normalize(texto)
            if 'whatsapp' in tn:
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

        # 3. Solo periodo: "en la mañana", "en la tarde" (sin hora específica)
        if 'en la manana' in tn or 'por la manana' in tn:
            return "en la manana"
        if 'en la tarde' in tn or 'por la tarde' in tn:
            return "en la tarde"

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
            if 'whatsapp' in tn834:
                rechazados.add('whatsapp')
            if 'correo' in tn834 or 'email' in tn834 or 'mail' in tn834:
                rechazados.add('correo')
            if 'telefono' in tn834 or 'celular' in tn834 or 'numero' in tn834:
                # Solo si es rechazo explícito (no "te doy mi número")
                _reject_words_834 = ['no tengo', 'tampoco', 'no manejo', 'no uso', 'no cuento']
                if any(r in tn834 for r in _reject_words_834):
                    rechazados.add('telefono')
            print(f"  [FIX 834] REJECT_DATA: rechazados pre-parse={rechazados} texto='{texto[:60]}'")

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
