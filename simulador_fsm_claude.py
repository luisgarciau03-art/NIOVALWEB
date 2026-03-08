#!/usr/bin/env python3
"""
Simulador FSM+Claude Log Replay
================================
Replaya conversaciones reales de produccion a traves del FSM+Claude
para detectar bugs, comparar contra produccion, y sugerir fixes.

Modos:
  - Offline (default): Solo FSM + templates, sin LLM calls (~30s, $0)
  - Online: FSM + Claude calls reales (~13 min, ~$0.50)

Uso:
  python simulador_fsm_claude.py                      # Todas, offline
  python simulador_fsm_claude.py --online             # Con Claude
  python simulador_fsm_claude.py --bruce BRUCE2537    # Una llamada
  python simulador_fsm_claude.py --verbose            # Detalle por turno
  python simulador_fsm_claude.py --top-bugs 20        # Top 20 peores
  python simulador_fsm_claude.py -o resultados.json   # Output JSON custom
"""

import os
import sys
import io
import re
import json
import time
import argparse
from collections import Counter, defaultdict
from datetime import datetime

# Fix Windows console encoding
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Setup path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Load .env for API keys
try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env'))
except ImportError:
    pass

# Env vars dummy (evitar crash al importar)
for _k in ['ELEVENLABS_API_KEY', 'TWILIO_ACCOUNT_SID', 'TWILIO_AUTH_TOKEN',
           'TWILIO_PHONE_NUMBER']:
    os.environ.setdefault(_k, 'SIM_DUMMY')

# Force FSM active mode
os.environ['FSM_ENABLED'] = 'active'
os.environ['FSM_ACTIVE_STATES'] = (
    'despedida,contacto_capturado,buscando_encargado,encargado_presente,'
    'encargado_ausente,capturando_contacto,dictando_dato,ofreciendo_contacto,'
    'esperando_transferencia,saludo,pitch'
)

# Import FSM + bug detector
from fsm_engine import FSMEngine, classify_intent, FSMState, FSMIntent, FSMContext
from bug_detector import BugDetector, CallEventTracker


# ============================================================
# LOG PARSER
# ============================================================

class LogParser:
    """Parsea logs de produccion en LOGS/ para extraer conversaciones."""

    # Regex patterns (probados en audit_masivo_todos.py)
    BRUCE_RE = re.compile(r'\[BRUCE\]\s+(BRUCE\d+)\s+DICE:\s*"(.+?)"', re.DOTALL)
    CLIENTE_RE = re.compile(r'\[CLIENTE\]\s+(BRUCE\d+)\s+-\s+CLIENTE DIJO:\s*"(.+?)"', re.DOTALL)

    # Bug detector header: [BUG_DETECTOR] BRUCEXXXX: N bug(s)
    BUG_HEADER_RE = re.compile(r'\[BUG_DETECTOR\]\s+(BRUCE\d+):')
    # Bug lines (appear AFTER header, without BRUCE ID):
    # [MEDIO] CATALOGO_REPETIDO: ...
    # [GPT ALTO] GPT_LOGICA_ROTA: ...
    BUG_LINE_RE = re.compile(r'^\[(?:GPT\s+)?(CRITICO|ALTO|MEDIO)\]\s+(\w+):\s+(.+?)$', re.MULTILINE)

    # FSM transitions: [FSM PHASE2] state=X intent=Y -> next=Z
    FSM_LINE_RE = re.compile(
        r'\[FSM (?:PHASE\d|SHADOW)\]\s+state=(\w+)\s+intent=(\w+)\s+.*?next=(\w+)'
    )

    @staticmethod
    def parse_all_logs(logs_dir, bruce_filter=None):
        """Parse ALL log files. Optionally filter by BRUCE ID."""
        log_files = sorted([f for f in os.listdir(logs_dir)
                           if f.endswith('.txt') and re.match(r'\d{2}_\d{2}PT', f)])
        print(f"  Archivos de log: {len(log_files)}")

        all_convs = {}

        for lf in log_files:
            filepath = os.path.join(logs_dir, lf)
            date_match = re.match(r'(\d{2}_\d{2})', lf)
            file_date = date_match.group(1) if date_match else 'unknown'

            try:
                with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
                    content = f.read()
            except Exception:
                continue

            # Extract conversation turns
            events = []
            for m in LogParser.BRUCE_RE.finditer(content):
                bruce_id = m.group(1)
                text = m.group(2).strip()
                if text and (not bruce_filter or bruce_id == bruce_filter):
                    events.append((m.start(), bruce_id, 'bruce', text))

            for m in LogParser.CLIENTE_RE.finditer(content):
                bruce_id = m.group(1)
                text = m.group(2).strip()
                if text and len(text) > 1 and (not bruce_filter or bruce_id == bruce_filter):
                    events.append((m.start(), bruce_id, 'cliente', text))

            events.sort(key=lambda x: x[0])

            for _, bruce_id, role, text in events:
                if bruce_id not in all_convs:
                    all_convs[bruce_id] = {
                        'turns': [],
                        'source': lf,
                        'date': file_date,
                        'prod_fsm': [],
                        'prod_bugs': [],
                    }
                all_convs[bruce_id]['turns'].append((role, text))

            # Extract production bugs (context-based: header line has BRUCE ID,
            # bug lines follow WITHOUT BRUCE ID)
            lines = content.split('\n')
            current_bug_bruce = None
            for line in lines:
                # Check for bug header
                hdr = LogParser.BUG_HEADER_RE.search(line)
                if hdr:
                    current_bug_bruce = hdr.group(1)
                    if bruce_filter and current_bug_bruce != bruce_filter:
                        current_bug_bruce = None
                    continue

                # Check for bug line (after header)
                if current_bug_bruce and current_bug_bruce in all_convs:
                    bm = LogParser.BUG_LINE_RE.match(line)
                    if bm:
                        all_convs[current_bug_bruce]['prod_bugs'].append({
                            'severidad': bm.group(1),
                            'tipo': bm.group(2),
                            'detalle': bm.group(3).strip(),
                        })
                        continue

                # Non-bug line resets context (blank or different content)
                if current_bug_bruce and line.strip() and not line.startswith('['):
                    current_bug_bruce = None

            # Extract FSM transitions (context-based: BRUCE ID from nearby lines)
            current_fsm_bruce = None
            for line in lines:
                # Track current BRUCE ID from any line mentioning it
                bid_match = re.search(r'(BRUCE\d+)', line)
                if bid_match:
                    candidate = bid_match.group(1)
                    if candidate in all_convs:
                        current_fsm_bruce = candidate

                # Check for FSM transition line
                if current_fsm_bruce and current_fsm_bruce in all_convs:
                    fm = LogParser.FSM_LINE_RE.search(line)
                    if fm:
                        all_convs[current_fsm_bruce]['prod_fsm'].append({
                            'state': fm.group(1),
                            'intent': fm.group(2),
                            'next': fm.group(3),
                        })

        return all_convs


# ============================================================
# MOCK AGENTE
# ============================================================

class MockAgente:
    """Mock minimo de AgenteVentas para FSM.process(agente=)."""

    def __init__(self):
        self.conversation_history = []
        self.openai_client = None
        self._post_espera_reintroducir_759 = False

    def add_turn(self, role, text):
        """Agrega turno al historial (formato OpenAI)."""
        openai_role = "assistant" if role == "bruce" else "user"
        self.conversation_history.append({"role": openai_role, "content": text})

    def reset(self):
        self.conversation_history = []
        self._post_espera_reintroducir_759 = False


# ============================================================
# FSM REPLAY ENGINE
# ============================================================

class FSMReplayEngine:
    """Replaya conversaciones de produccion a traves del FSM."""

    def __init__(self, online_mode=False, verbose=False):
        self.online = online_mode
        self.verbose = verbose

    def replay(self, bruce_id, data):
        """Replaya una conversacion completa por el FSM.

        Returns dict con intent_classifications, fsm_transitions,
        responses, bugs_replay, bugs_prod, etc.
        """
        fsm = FSMEngine()
        mock = MockAgente()
        turns = data['turns']

        result = {
            'bruce_id': bruce_id,
            'source': data.get('source', ''),
            'date': data.get('date', ''),
            'turns_total': len(turns),
            'client_turns': 0,
            'fsm_final_state': 'saludo',
            'intent_classifications': [],
            'fsm_transitions': [],
            'responses': [],
            'bugs_replay': [],
            'bugs_prod': data.get('prod_bugs', []),
            'prod_fsm': data.get('prod_fsm', []),
            'llm_calls': 0,
            'errors': [],
        }

        # FIX 827: Build replay_conv correctly
        # - Production bruce turns go to mock history only (context for GPT_NARROW)
        # - replay_conv gets: initial bruce saludo, then client+bruce pairs
        # - Each client turn gets exactly ONE bruce response (FSM or prod fallback)
        # - Client turns included for complete bug analysis
        replay_conv = []
        client_turn_idx = 0
        first_bruce_added = False
        fsm_states_visited = []

        for i, (role, text) in enumerate(turns):
            if role == 'bruce':
                mock.add_turn('bruce', text)
                # FIX 827: Only add the FIRST bruce turn (saludo) directly
                # Subsequent bruce turns are added as FSM/prod response after client processing
                if not first_bruce_added:
                    replay_conv.append(('bruce', text))
                    first_bruce_added = True
            elif role == 'cliente':
                result['client_turns'] += 1
                mock.add_turn('cliente', text)
                # FIX 827: Add client turn to replay_conv for complete analysis
                replay_conv.append(('cliente', text))

                state_before = fsm.state.value

                # 1. Classify intent (always fast, deterministic)
                try:
                    intent = classify_intent(text, fsm.context, fsm.state)
                except Exception as e:
                    intent = FSMIntent.UNKNOWN
                    result['errors'].append(f"classify error T{client_turn_idx}: {e}")

                result['intent_classifications'].append({
                    'text': text[:100],
                    'intent': intent.value,
                    'state_before': state_before,
                })

                # 2. Process through FSM
                fsm_response = None
                try:
                    fsm_response = fsm.process(text, agente=mock)
                except Exception as e:
                    result['errors'].append(f"FSM error T{client_turn_idx}: {e}")

                state_after = fsm.state.value
                intercepted = fsm_response is not None
                fsm_states_visited.append(state_after)

                result['fsm_transitions'].append({
                    'state_before': state_before,
                    'intent': intent.value,
                    'state_after': state_after,
                    'intercepted': intercepted,
                    'response': (fsm_response[:80] if fsm_response else None),
                })

                # 3. Find production Bruce response (next bruce turn after this)
                prod_response = None
                for j in range(i + 1, len(turns)):
                    if turns[j][0] == 'bruce':
                        prod_response = turns[j][1]
                        break

                result['responses'].append({
                    'client': text[:100],
                    'fsm_response': (fsm_response[:100] if fsm_response else None),
                    'prod_response': (prod_response[:100] if prod_response else None),
                    'intercepted': intercepted,
                })

                # 4. Add exactly ONE bruce response to replay conversation
                # FIX 827: Prefer FSM response; fall back to prod; never double-add
                response = fsm_response or prod_response
                if response:
                    replay_conv.append(('bruce', response))

                client_turn_idx += 1

                if self.verbose:
                    flag = "FSM" if intercepted else "PROD"
                    resp_show = (fsm_response or prod_response or "")[:60]
                    print(f"    T{client_turn_idx} [{state_before}] {intent.value} -> [{state_after}] ({flag}) {resp_show}")

        result['fsm_final_state'] = fsm.state.value

        # 5. Run bug detector on replayed conversation
        # FIX 828: Pass FSM states for better tracker initialization
        result['bugs_replay'] = self._detect_bugs(bruce_id, replay_conv, fsm_states_visited)

        return result

    def _detect_bugs(self, bruce_id, replay_conv, fsm_states=None):
        """Corre BugDetector sobre la conversacion replay.
        FIX 828: Mejor inicializacion del tracker para reducir falsos positivos.
        """
        tracker = CallEventTracker(
            call_sid=f"CA_fsm_replay_{bruce_id}",
            bruce_id=bruce_id,
            telefono=""
        )

        # FIX 828: Estimar duracion real por numero de turnos (avg 15s/turno)
        n_bruce = sum(1 for r, _ in replay_conv if r == 'bruce')
        n_client = sum(1 for r, _ in replay_conv if r == 'cliente')
        estimated_duration = max(30, (n_bruce + n_client) * 12)  # ~12s por turno
        tracker.created_at = time.time() - estimated_duration

        for role, text in replay_conv:
            if role == 'bruce':
                tracker.conversacion.append(('bruce', text))
                tracker.respuestas_bruce.append(text)
            else:
                tracker.conversacion.append(('cliente', text))
                tracker.textos_cliente.append(text)

        tracker.turnos = n_bruce
        tracker.twiml_count = n_bruce + 2  # +2 for connection overhead
        tracker.audio_fetch_count = n_bruce

        # FIX 828: Marcar saludo/pitch basado en estados FSM visitados
        if fsm_states:
            for st in fsm_states:
                if st == 'pitch':
                    if hasattr(tracker, 'pitch_dado'):
                        tracker.pitch_dado = True
                if st == 'saludo':
                    if hasattr(tracker, 'saludo_dado'):
                        tracker.saludo_dado = True

        try:
            bugs = BugDetector.analyze(tracker)
            return bugs
        except Exception as e:
            return [{"tipo": "DETECTOR_ERROR", "severidad": "CRITICO", "detalle": str(e)}]


# ============================================================
# BUG COMPARATOR
# ============================================================

class BugComparator:
    """Compara bugs del replay vs produccion."""

    @staticmethod
    def compare(bugs_replay, bugs_prod):
        replay_types = Counter(b['tipo'] for b in bugs_replay)
        prod_types = Counter(b['tipo'] for b in bugs_prod)

        replay_set = set(replay_types.keys())
        prod_set = set(prod_types.keys())

        fixed = prod_set - replay_set
        new = replay_set - prod_set
        common = replay_set & prod_set

        n_replay = len(bugs_replay)
        n_prod = len(bugs_prod)
        delta = n_replay - n_prod

        if n_replay == 0 and n_prod == 0:
            verdict = 'PASS'
        elif delta < 0:
            verdict = 'IMPROVED'
        elif delta > 0:
            verdict = 'REGRESSED'
        else:
            verdict = 'UNCHANGED'

        return {
            'replay_count': n_replay,
            'prod_count': n_prod,
            'delta': delta,
            'fixed': sorted(fixed),
            'new': sorted(new),
            'common': sorted(common),
            'verdict': verdict,
        }


# ============================================================
# FIX SUGGESTION ENGINE
# ============================================================

class FixSuggestionEngine:
    """Analiza resultados agregados para generar sugerencias de fix."""

    def analyze(self, all_results):
        """Retorna lista de sugerencias priorizadas."""
        suggestions = []

        # 1. Intent misclassifications vs produccion
        suggestions.extend(self._find_intent_mismatches(all_results))

        # 2. UNKNOWN intents frecuentes (missing patterns)
        suggestions.extend(self._find_missing_patterns(all_results))

        # 3. Bug-generating transitions
        suggestions.extend(self._find_bug_transitions(all_results))

        # Sort by priority then count
        priority_order = {'P0': 0, 'P1': 1, 'P2': 2}
        suggestions.sort(key=lambda s: (priority_order.get(s['priority'], 9), -s['count']))

        return suggestions

    def _find_intent_mismatches(self, all_results):
        """Encuentra donde classify_intent difiere del log de produccion."""
        mismatches = defaultdict(list)

        for r in all_results:
            prod_fsm = r.get('prod_fsm', [])
            replay_intents = r.get('intent_classifications', [])

            # Comparar por indice (imperfecto pero util)
            for i, ri in enumerate(replay_intents):
                if i < len(prod_fsm):
                    prod_intent = prod_fsm[i].get('intent', '')
                    if ri['intent'] != prod_intent and prod_intent:
                        key = (ri['intent'], prod_intent)
                        mismatches[key].append({
                            'bruce_id': r['bruce_id'],
                            'text': ri['text'],
                            'state': ri['state_before'],
                        })

        suggestions = []
        for (replay_intent, prod_intent), cases in mismatches.items():
            if len(cases) >= 2:
                suggestions.append({
                    'priority': 'P1' if len(cases) >= 5 else 'P2',
                    'type': 'fix_intent',
                    'description': f"Intent mismatch: replay={replay_intent} vs prod={prod_intent} ({len(cases)} cases)",
                    'affected_calls': list(set(c['bruce_id'] for c in cases))[:10],
                    'count': len(cases),
                    'examples': [c['text'] for c in cases[:5]],
                })

        return suggestions

    def _find_missing_patterns(self, all_results):
        """Encuentra textos clasificados UNKNOWN que aparecen frecuentemente."""
        unknowns_by_state = defaultdict(list)

        for r in all_results:
            for ic in r.get('intent_classifications', []):
                if ic['intent'] == 'unknown':
                    unknowns_by_state[ic['state_before']].append({
                        'text': ic['text'],
                        'bruce_id': r['bruce_id'],
                    })

        suggestions = []
        for state, items in unknowns_by_state.items():
            if len(items) >= 3:
                # Agrupar textos similares por palabras clave
                clusters = self._cluster_by_keywords(items)
                for keyword, cluster_items in clusters.items():
                    if len(cluster_items) >= 3:
                        suggestions.append({
                            'priority': 'P0' if len(cluster_items) >= 10 else 'P1',
                            'type': 'add_pattern',
                            'description': f"UNKNOWN en {state}: '{keyword}' ({len(cluster_items)} cases)",
                            'affected_calls': list(set(c['bruce_id'] for c in cluster_items))[:10],
                            'count': len(cluster_items),
                            'examples': [c['text'] for c in cluster_items[:5]],
                        })

        return suggestions

    def _cluster_by_keywords(self, items):
        """Agrupa items por palabras clave frecuentes."""
        word_freq = Counter()
        word_items = defaultdict(list)

        stopwords = {'si', 'no', 'el', 'la', 'de', 'que', 'en', 'un', 'es', 'y', 'a',
                     'por', 'para', 'con', 'los', 'las', 'del', 'al', 'se', 'lo', 'le',
                     'me', 'su', 'ya', 'mas', 'pero', 'como', 'este', 'o', 'una'}

        for item in items:
            words = set(item['text'].lower().split()) - stopwords
            for w in words:
                if len(w) > 3:
                    word_freq[w] += 1
                    word_items[w].append(item)

        # Solo clusters con 3+ items
        return {w: word_items[w] for w, c in word_freq.items() if c >= 3}

    def _find_bug_transitions(self, all_results):
        """Encuentra transiciones FSM que correlacionan con bugs."""
        transition_bugs = defaultdict(lambda: {'bugs': [], 'calls': set()})

        for r in all_results:
            if not r.get('bugs_replay'):
                continue

            transitions = r.get('fsm_transitions', [])
            bug_types = [b['tipo'] for b in r['bugs_replay']]

            # Atribuir bugs a la ultima transicion (simplificado)
            for t in transitions:
                key = f"{t['state_before']}+{t['intent']}->{t['state_after']}"
                for bt in bug_types:
                    transition_bugs[key]['bugs'].append(bt)
                    transition_bugs[key]['calls'].add(r['bruce_id'])

        suggestions = []
        for trans_key, data in transition_bugs.items():
            n_calls = len(data['calls'])
            if n_calls >= 5:
                top_bugs = Counter(data['bugs']).most_common(3)
                suggestions.append({
                    'priority': 'P0' if n_calls >= 15 else 'P1',
                    'type': 'change_transition',
                    'description': f"Transicion {trans_key}: {n_calls} llamadas con bugs (top: {', '.join(f'{b}({c})' for b,c in top_bugs)})",
                    'affected_calls': sorted(list(data['calls']))[:10],
                    'count': n_calls,
                    'examples': [],
                })

        return suggestions

    def generate_auto_scenarios(self, all_results, top_n=10):
        """Genera escenarios para simulador_llamadas.py desde peores llamadas."""
        # Ordenar por bugs replay (descendente)
        with_bugs = [r for r in all_results if r.get('bugs_replay')]
        worst = sorted(with_bugs, key=lambda r: len(r['bugs_replay']), reverse=True)[:top_n]

        scenarios = []
        for r in worst:
            # Reconstruir turnos_raw desde el resultado
            turns_raw = []
            original_turns = []
            # Necesitamos los turnos originales - los guardamos en el resultado
            for resp in r.get('responses', []):
                turns_raw.append(("cliente", resp['client']))
                if resp.get('prod_response'):
                    turns_raw.append(("bruce", resp['prod_response']))

            scenario = {
                "nombre": f"Log replay: {r['bruce_id']}",
                "descripcion": f"Auto-generado desde {r.get('source', 'unknown')} - {len(r['bugs_replay'])} bugs",
                "simular_bug": True,
                "turnos_raw": turns_raw,
                "bugs_esperados": list(set(b['tipo'] for b in r['bugs_replay'])),
            }
            scenarios.append(scenario)

        return scenarios


# ============================================================
# REPORT GENERATOR
# ============================================================

class ReportGenerator:
    """Genera reporte en consola y JSON."""

    def __init__(self, verbose=False):
        self.verbose = verbose

    def print_header(self, mode, n_calls, n_files):
        print("\n" + "=" * 60)
        print(f"  SIMULADOR FSM+CLAUDE LOG REPLAY")
        print(f"  Modo: {'ONLINE (Claude)' if mode == 'online' else 'OFFLINE (templates)'}")
        print(f"  Logs: {n_calls} llamadas | {n_files} archivos")
        print(f"  Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 60 + "\n")

    def print_call_result(self, idx, total, result, comparison):
        bruce = result['bruce_id']
        turns = result['client_turns']
        final = result['fsm_final_state']
        n_replay = comparison['replay_count']
        n_prod = comparison['prod_count']
        verdict = comparison['verdict']
        delta = comparison['delta']

        # Intent accuracy
        n_intents = len(result['intent_classifications'])
        n_intercepted = sum(1 for t in result['fsm_transitions'] if t['intercepted'])

        # Verdict icon
        if verdict == 'PASS':
            icon = '[OK] PASS'
        elif verdict == 'IMPROVED':
            icon = f'[OK] IMPROVED ({delta} bugs)'
        elif verdict == 'REGRESSED':
            icon = f'[FAIL] REGRESSED (+{delta} bugs)'
        else:
            icon = f'[--] UNCHANGED ({n_replay} bugs)'

        print(f"  [{idx}/{total}] {bruce}: {turns} turnos, final={final}")
        print(f"    FSM intercepto: {n_intercepted}/{n_intents} turnos | "
              f"Bugs: {n_replay} replay vs {n_prod} prod")

        if comparison['new']:
            print(f"    NUEVOS: {', '.join(comparison['new'])}")
        if comparison['fixed']:
            print(f"    ARREGLADOS: {', '.join(comparison['fixed'])}")

        print(f"    {icon}")

        if result.get('errors'):
            for err in result['errors'][:3]:
                print(f"    [ERROR] {err}")

        print()

    def print_summary(self, all_results, all_comparisons, suggestions, elapsed_s):
        total = len(all_results)
        verdicts = Counter(c['verdict'] for c in all_comparisons)

        total_bugs_replay = sum(c['replay_count'] for c in all_comparisons)
        total_bugs_prod = sum(c['prod_count'] for c in all_comparisons)

        # Intent stats
        total_intents = sum(len(r['intent_classifications']) for r in all_results)
        total_intercepted = sum(
            sum(1 for t in r['fsm_transitions'] if t['intercepted'])
            for r in all_results
        )

        # Intent distribution
        intent_counter = Counter()
        for r in all_results:
            for ic in r['intent_classifications']:
                intent_counter[ic['intent']] += 1

        # Top bug types in replay
        bug_counter = Counter()
        for r in all_results:
            for b in r.get('bugs_replay', []):
                bug_counter[b['tipo']] += 1

        print("\n" + "=" * 60)
        print("  RESUMEN")
        print("=" * 60)
        print(f"  Total: {total} llamadas en {elapsed_s:.1f}s")
        print(f"  PASS: {verdicts.get('PASS', 0)} ({verdicts.get('PASS', 0)*100/max(total,1):.0f}%) | "
              f"IMPROVED: {verdicts.get('IMPROVED', 0)} ({verdicts.get('IMPROVED', 0)*100/max(total,1):.0f}%) | "
              f"UNCHANGED: {verdicts.get('UNCHANGED', 0)} ({verdicts.get('UNCHANGED', 0)*100/max(total,1):.0f}%) | "
              f"REGRESSED: {verdicts.get('REGRESSED', 0)} ({verdicts.get('REGRESSED', 0)*100/max(total,1):.0f}%)")
        print(f"  Bugs: {total_bugs_replay} replay vs {total_bugs_prod} produccion (delta: {total_bugs_replay - total_bugs_prod:+d})")
        print(f"  FSM intercepto: {total_intercepted}/{total_intents} turnos ({total_intercepted*100/max(total_intents,1):.1f}%)")

        print(f"\n  --- Top intents clasificados ---")
        for intent, count in intent_counter.most_common(10):
            print(f"    {intent:30s} {count:5d} ({count*100/max(total_intents,1):.1f}%)")

        if bug_counter:
            print(f"\n  --- Top bugs en replay ---")
            for bug_type, count in bug_counter.most_common(15):
                print(f"    {bug_type:35s} {count:5d}")

        if suggestions:
            print(f"\n  --- Sugerencias de fix ({len(suggestions)}) ---")
            for i, s in enumerate(suggestions[:15], 1):
                print(f"    [{s['priority']}] {s['type']}: {s['description']}")
                if s.get('examples'):
                    for ex in s['examples'][:2]:
                        print(f"         Ej: \"{ex[:70]}\"")
                if s.get('affected_calls'):
                    print(f"         Llamadas: {', '.join(s['affected_calls'][:5])}")

        print("\n" + "=" * 60)

    def save_json(self, filepath, all_results, all_comparisons, suggestions, auto_scenarios, elapsed_s):
        """Guarda resultados completos en JSON."""
        total = len(all_results)
        verdicts = Counter(c['verdict'] for c in all_comparisons)

        output = {
            "metadata": {
                "date": datetime.now().isoformat(),
                "total_calls": total,
                "elapsed_s": round(elapsed_s, 1),
            },
            "summary": {
                "pass": verdicts.get('PASS', 0),
                "improved": verdicts.get('IMPROVED', 0),
                "unchanged": verdicts.get('UNCHANGED', 0),
                "regressed": verdicts.get('REGRESSED', 0),
                "total_bugs_replay": sum(c['replay_count'] for c in all_comparisons),
                "total_bugs_prod": sum(c['prod_count'] for c in all_comparisons),
            },
            "calls": {},
            "fix_suggestions": suggestions,
            "auto_scenarios_count": len(auto_scenarios),
        }

        # Per-call results (compact)
        for r, c in zip(all_results, all_comparisons):
            output["calls"][r['bruce_id']] = {
                'source': r.get('source', ''),
                'client_turns': r['client_turns'],
                'final_state': r['fsm_final_state'],
                'bugs_replay': [b['tipo'] for b in r.get('bugs_replay', [])],
                'bugs_prod': [b['tipo'] for b in r.get('bugs_prod', [])],
                'verdict': c['verdict'],
                'delta': c['delta'],
                'intents': [ic['intent'] for ic in r.get('intent_classifications', [])],
                'errors': r.get('errors', []),
            }

        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(output, f, ensure_ascii=False, indent=2)
            print(f"\n  Resultados guardados en: {filepath}")
        except Exception as e:
            print(f"\n  Error guardando JSON: {e}")

        return output


# ============================================================
# MAIN
# ============================================================

def main():
    parser = argparse.ArgumentParser(description="Simulador FSM+Claude Log Replay")
    parser.add_argument("--online", action="store_true",
                        help="Incluir Claude calls para GPT_NARROW (default: offline)")
    parser.add_argument("--bruce", type=str,
                        help="Replay solo una llamada (ej: BRUCE2537)")
    parser.add_argument("--verbose", "-v", action="store_true",
                        help="Mostrar detalle por turno")
    parser.add_argument("--output", "-o", type=str, default="fsm_replay_results.json",
                        help="Archivo JSON de output (default: fsm_replay_results.json)")
    parser.add_argument("--top-bugs", type=int, default=10,
                        help="Numero de peores llamadas para auto-scenarios (default: 10)")
    parser.add_argument("--min-turns", type=int, default=3,
                        help="Minimo de turnos para incluir llamada (default: 3)")
    args = parser.parse_args()

    online_mode = args.online

    # Check API keys for online mode
    if online_mode:
        has_anthropic = bool(os.environ.get('ANTHROPIC_API_KEY'))
        has_openai = bool(os.environ.get('OPENAI_API_KEY'))
        if not has_anthropic and not has_openai:
            print("  WARNING: No API key found, switching to offline mode")
            online_mode = False

    # 1. Parse logs
    logs_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'LOGS')
    if not os.path.exists(logs_dir):
        print(f"  ERROR: Directorio LOGS no encontrado: {logs_dir}")
        sys.exit(1)

    print("  Parseando logs...")
    all_convs = LogParser.parse_all_logs(logs_dir, bruce_filter=args.bruce)
    print(f"  Conversaciones encontradas: {len(all_convs)}")

    # Filter by minimum turns
    valid_convs = {}
    for bid, data in all_convs.items():
        n_turns = len(data['turns'])
        has_both = (any(r == 'bruce' for r, _ in data['turns']) and
                    any(r == 'cliente' for r, _ in data['turns']))
        if n_turns >= args.min_turns and has_both:
            valid_convs[bid] = data

    print(f"  Conversaciones validas (>={args.min_turns} turnos): {len(valid_convs)}")

    if not valid_convs:
        print("  No hay conversaciones para procesar.")
        sys.exit(0)

    # Sort by BRUCE ID (numeric)
    sorted_ids = sorted(valid_convs.keys(),
                        key=lambda x: int(re.search(r'\d+', x).group()) if re.search(r'\d+', x) else 0)

    # 2. Initialize components
    engine = FSMReplayEngine(online_mode=online_mode, verbose=args.verbose)
    report = ReportGenerator(verbose=args.verbose)
    suggestion_engine = FixSuggestionEngine()

    report.print_header(
        mode='online' if online_mode else 'offline',
        n_calls=len(valid_convs),
        n_files=len(set(d['source'] for d in valid_convs.values())),
    )

    # 3. Replay all conversations
    t0 = time.time()
    all_results = []
    all_comparisons = []

    for idx, bruce_id in enumerate(sorted_ids, 1):
        data = valid_convs[bruce_id]

        # Suppress FSM print output unless verbose
        if not args.verbose:
            old_stdout = sys.stdout
            sys.stdout = io.StringIO()

        try:
            result = engine.replay(bruce_id, data)
        except Exception as e:
            result = {
                'bruce_id': bruce_id,
                'client_turns': 0,
                'fsm_final_state': 'error',
                'intent_classifications': [],
                'fsm_transitions': [],
                'responses': [],
                'bugs_replay': [],
                'bugs_prod': data.get('prod_bugs', []),
                'errors': [str(e)],
            }

        if not args.verbose:
            sys.stdout = old_stdout

        comparison = BugComparator.compare(
            result.get('bugs_replay', []),
            result.get('bugs_prod', []),
        )

        all_results.append(result)
        all_comparisons.append(comparison)

        # Print progress
        report.print_call_result(idx, len(sorted_ids), result, comparison)

    elapsed = time.time() - t0

    # 4. Generate fix suggestions
    suggestions = suggestion_engine.analyze(all_results)

    # 5. Generate auto scenarios
    auto_scenarios = suggestion_engine.generate_auto_scenarios(all_results, top_n=args.top_bugs)

    # 6. Print summary
    report.print_summary(all_results, all_comparisons, suggestions, elapsed)

    # 7. Save JSON
    output_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), args.output)
    report.save_json(output_path, all_results, all_comparisons, suggestions, auto_scenarios, elapsed)

    # 8. Save auto scenarios
    if auto_scenarios:
        scenarios_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                       'fsm_auto_scenarios.json')
        try:
            with open(scenarios_path, 'w', encoding='utf-8') as f:
                json.dump(auto_scenarios, f, ensure_ascii=False, indent=2)
            print(f"  Auto-scenarios ({len(auto_scenarios)}) guardados en: {scenarios_path}")
        except Exception as e:
            print(f"  Error guardando auto-scenarios: {e}")

    # Return exit code
    n_regressed = sum(1 for c in all_comparisons if c['verdict'] == 'REGRESSED')
    sys.exit(1 if n_regressed > len(all_results) * 0.1 else 0)  # Fail if >10% regressed


if __name__ == "__main__":
    main()
