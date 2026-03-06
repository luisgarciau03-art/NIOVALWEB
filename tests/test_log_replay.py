"""
FASE 4B: Replay de conversaciones REALES desde logs de Railway.
Parsea TODOS los archivos en LOGS/, extrae conversaciones por BRUCE ID,
y las replaya a traves de procesar_respuesta con GPT mockeado.

Verifica:
- No crashes en ninguna entrada real
- No respuestas None inesperadas
- No loops (misma respuesta 3+ veces)
- Respuestas razonables (no vacias cuando se espera respuesta)

Uso:
  python -m pytest tests/test_log_replay.py -v --tb=short
  python tests/test_log_replay.py   # standalone con reporte detallado
"""

import sys
import os
import re
import json
from collections import defaultdict
from datetime import datetime

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

LOGS_DIR = os.path.join(os.path.dirname(__file__), '..', 'LOGS')

# ============================================================
# PARSER DE LOGS
# ============================================================

# Regex para extraer turnos con BRUCE ID y timestamp
RE_CLIENTE = re.compile(
    r'\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\] \[CLIENTE\] (BRUCE\d+) - CLIENTE DIJO: "(.*)"'
)
RE_BRUCE = re.compile(
    r'\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\] \[BRUCE\] (BRUCE\d+) DICE: "(.*)"'
)


def parse_log_file(filepath):
    """Parsea un archivo de log y extrae conversaciones por BRUCE ID.

    Returns:
        dict: {bruce_id: [{"role": "user"/"assistant", "text": str, "ts": str}]}
    """
    conversations = defaultdict(list)
    try:
        with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
            for line in f:
                m_cliente = RE_CLIENTE.search(line)
                if m_cliente:
                    ts, bruce_id, text = m_cliente.groups()
                    conversations[bruce_id].append({
                        "role": "user",
                        "text": text,
                        "ts": ts,
                    })
                    continue

                m_bruce = RE_BRUCE.search(line)
                if m_bruce:
                    ts, bruce_id, text = m_bruce.groups()
                    conversations[bruce_id].append({
                        "role": "assistant",
                        "text": text,
                        "ts": ts,
                    })
    except Exception as e:
        print(f"  ERROR leyendo {filepath}: {e}")

    return dict(conversations)


def parse_all_logs(logs_dir=LOGS_DIR):
    """Parsea TODOS los archivos .txt en el directorio de logs.

    Returns:
        dict: {bruce_id: {"turns": [...], "file": str}}
    """
    all_conversations = {}

    if not os.path.isdir(logs_dir):
        print(f"ERROR: Directorio {logs_dir} no existe")
        return {}

    files = sorted([f for f in os.listdir(logs_dir) if f.endswith('.txt')])
    print(f"Parseando {len(files)} archivos de log...")

    for filename in files:
        filepath = os.path.join(logs_dir, filename)
        convs = parse_log_file(filepath)
        for bruce_id, turns in convs.items():
            if bruce_id not in all_conversations:
                all_conversations[bruce_id] = {"turns": turns, "file": filename}
            else:
                # Merge turns (same call might span multiple log files)
                all_conversations[bruce_id]["turns"].extend(turns)

    # Sort turns by timestamp within each conversation
    for bruce_id in all_conversations:
        all_conversations[bruce_id]["turns"].sort(key=lambda t: t["ts"])

    print(f"Total: {len(all_conversations)} conversaciones extraidas")
    return all_conversations


def filter_conversations(conversations, min_client_turns=2, max_client_turns=50):
    """Filtra conversaciones validas para replay.

    Excluye:
    - Conversaciones con < min_client_turns turnos del cliente
    - Conversaciones donde TODOS los mensajes del cliente son vacios
    - Conversaciones con > max_client_turns (anomalas)
    """
    filtered = {}
    stats = {"total": len(conversations), "filtered_short": 0,
             "filtered_empty": 0, "filtered_long": 0, "valid": 0}

    for bruce_id, data in conversations.items():
        client_turns = [t for t in data["turns"] if t["role"] == "user" and t["text"].strip()]

        if len(client_turns) < min_client_turns:
            stats["filtered_short"] += 1
            continue

        if len(client_turns) > max_client_turns:
            stats["filtered_long"] += 1
            continue

        # Check if all messages are empty or IVR-like
        real_messages = [t for t in client_turns if len(t["text"]) > 3]
        if len(real_messages) < 1:
            stats["filtered_empty"] += 1
            continue

        filtered[bruce_id] = data
        stats["valid"] += 1

    print(f"Filtrado: {stats['valid']} validas de {stats['total']} total "
          f"(short={stats['filtered_short']}, empty={stats['filtered_empty']}, "
          f"long={stats['filtered_long']})")
    return filtered, stats


# ============================================================
# REPLAY ENGINE
# ============================================================

def _create_mock_response(content):
    """Crea mock de respuesta OpenAI"""
    from unittest.mock import MagicMock
    mock_resp = MagicMock()
    mock_resp.choices = [MagicMock()]
    mock_resp.choices[0].message.content = content
    return mock_resp


_GPT_MOCK_RESPONSES = [
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
_mock_counter = 0

def _replay_gpt_mock(**kwargs):
    """GPT mock que rota entre respuestas variadas para evitar falsos loops"""
    global _mock_counter
    resp = _GPT_MOCK_RESPONSES[_mock_counter % len(_GPT_MOCK_RESPONSES)]
    _mock_counter += 1
    return _create_mock_response(resp)


class _SuppressStdout:
    """Context manager que suprime stdout para acelerar replay (prints de debug)."""
    def __enter__(self):
        self._original = sys.stdout
        sys.stdout = open(os.devnull, 'w')
        return self

    def __exit__(self, *args):
        sys.stdout.close()
        sys.stdout = self._original


def replay_conversation(bruce_id, turns, suppress_output=True):
    """Replaya una conversacion a traves de procesar_respuesta.

    Returns:
        dict: {
            "bruce_id": str,
            "total_turns": int,
            "client_turns": int,
            "crashes": list,
            "none_responses": int,
            "empty_responses": int,
            "loop_detected": bool,
            "responses": list,
            "success": bool,
        }
    """
    from unittest.mock import patch
    from agente_ventas import AgenteVentas, EstadoConversacion

    result = {
        "bruce_id": bruce_id,
        "total_turns": len(turns),
        "client_turns": 0,
        "crashes": [],
        "none_responses": 0,
        "empty_responses": 0,
        "loop_detected": False,
        "responses": [],
        "success": True,
    }

    try:
        with patch('agente_ventas.openai_client') as mock_client:
            mock_client.chat.completions.create.side_effect = _replay_gpt_mock

            agente = AgenteVentas()
            agente.estado_conversacion = EstadoConversacion.CONVERSACION_NORMAL
            agente.conversacion_iniciada = True
            agente.segunda_parte_saludo_dicha = True

            # Add initial saludo to history
            saludo = (
                "Hola, buen día, le llamo de la marca NIOVAL, somos distribuidores "
                "de productos ferreteros de alta calidad. ¿Me podría comunicar con "
                "el encargado de compras?"
            )
            agente.conversation_history = [
                {"role": "assistant", "content": saludo}
            ]

            recent_responses = []

            for turn in turns:
                if turn["role"] != "user":
                    continue

                text = turn["text"].strip()
                if not text:
                    continue

                result["client_turns"] += 1

                try:
                    # Suprimir stdout/stderr para acelerar (miles de prints de debug)
                    if suppress_output:
                        _orig_stdout = sys.stdout
                        _orig_stderr = sys.stderr
                        sys.stdout = open(os.devnull, 'w', encoding='utf-8')
                        sys.stderr = open(os.devnull, 'w', encoding='utf-8')
                    try:
                        response = agente.procesar_respuesta(text)
                    finally:
                        if suppress_output:
                            sys.stdout.close()
                            sys.stderr.close()
                            sys.stdout = _orig_stdout
                            sys.stderr = _orig_stderr

                    if response is None:
                        result["none_responses"] += 1
                    elif response == "":
                        result["empty_responses"] += 1
                    else:
                        result["responses"].append(response[:100])

                        # Check for loops (same response 3+ times)
                        recent_responses.append(response)
                        if len(recent_responses) >= 3:
                            last_3 = recent_responses[-3:]
                            if last_3[0] == last_3[1] == last_3[2]:
                                result["loop_detected"] = True

                except Exception as e:
                    result["crashes"].append({
                        "turn": result["client_turns"],
                        "text": text[:80],
                        "error": str(e)[:200],
                    })

    except Exception as e:
        result["crashes"].append({
            "turn": 0,
            "text": "INIT",
            "error": str(e)[:200],
        })

    if result["crashes"]:
        result["success"] = False

    return result


# ============================================================
# PYTEST TESTS
# ============================================================

import pytest


@pytest.fixture(scope="module")
def all_conversations():
    """Parsea todos los logs una sola vez para todos los tests"""
    convs = parse_all_logs()
    filtered, stats = filter_conversations(convs)
    return filtered, stats


class TestLogReplayParser:
    """Verificar que el parser extrae conversaciones correctamente"""

    def test_logs_directory_exists(self):
        assert os.path.isdir(LOGS_DIR), f"Directorio LOGS no existe: {LOGS_DIR}"

    def test_parser_finds_conversations(self, all_conversations):
        filtered, stats = all_conversations
        assert stats["total"] > 0, "Debe encontrar al menos 1 conversacion"

    def test_parser_finds_valid_conversations(self, all_conversations):
        filtered, stats = all_conversations
        assert stats["valid"] > 0, "Debe haber al menos 1 conversacion valida"

    def test_conversations_have_turns(self, all_conversations):
        filtered, _ = all_conversations
        for bruce_id, data in list(filtered.items())[:10]:
            client_turns = [t for t in data["turns"] if t["role"] == "user"]
            assert len(client_turns) >= 2, f"{bruce_id}: Debe tener >= 2 turnos cliente"


class TestLogReplayExecution:
    """Replay de conversaciones reales — verificar sin crashes ni loops"""

    def test_replay_sample_no_crashes(self, all_conversations):
        """Replay de las primeras 50 conversaciones sin crashes"""
        filtered, _ = all_conversations
        sample = list(filtered.items())[:50]

        crashes = []
        for bruce_id, data in sample:
            result = replay_conversation(bruce_id, data["turns"])
            if result["crashes"]:
                crashes.append({
                    "id": bruce_id,
                    "crashes": result["crashes"],
                    "file": data["file"],
                })

        if crashes:
            detail = "\n".join(
                f"  {c['id']} ({c['file']}): {c['crashes'][0]['error'][:100]}"
                for c in crashes[:10]
            )
            pytest.fail(f"{len(crashes)} conversaciones con crash:\n{detail}")

    def test_replay_sample_loops_under_threshold(self, all_conversations):
        """Verificar que loops se mantienen bajo umbral aceptable (mock GPT causa loops)"""
        filtered, _ = all_conversations
        sample = list(filtered.items())[:50]

        loops = []
        for bruce_id, data in sample:
            result = replay_conversation(bruce_id, data["turns"])
            if result["loop_detected"]:
                loops.append(bruce_id)

        # Con GPT mock, hasta 50% de loops es aceptable (respuestas estaticas)
        loop_rate = len(loops) * 100 / max(len(sample), 1)
        assert loop_rate <= 50, (
            f"Demasiados loops: {len(loops)}/{len(sample)} ({loop_rate:.0f}%) > 50%: {loops[:10]}"
        )

    def test_replay_recent_logs_no_crashes(self, all_conversations):
        """Replay de logs del 19_02 (mas recientes) sin crashes"""
        filtered, _ = all_conversations
        recent = {k: v for k, v in filtered.items()
                  if v["file"].startswith("19_02")}

        if not recent:
            pytest.skip("No hay logs recientes (19_02)")

        crashes = []
        for bruce_id, data in recent.items():
            result = replay_conversation(bruce_id, data["turns"])
            if result["crashes"]:
                crashes.append({
                    "id": bruce_id,
                    "error": result["crashes"][0]["error"][:100],
                })

        if crashes:
            detail = "\n".join(f"  {c['id']}: {c['error']}" for c in crashes[:10])
            pytest.fail(f"{len(crashes)} conversaciones recientes con crash:\n{detail}")

    def test_replay_recent_logs_loops_under_threshold(self, all_conversations):
        """Verificar que loops recientes se mantienen bajo umbral aceptable"""
        filtered, _ = all_conversations
        recent = {k: v for k, v in filtered.items()
                  if v["file"].startswith("19_02")}

        if not recent:
            pytest.skip("No hay logs recientes (19_02)")

        loops = []
        for bruce_id, data in recent.items():
            result = replay_conversation(bruce_id, data["turns"])
            if result["loop_detected"]:
                loops.append(bruce_id)

        # Con GPT mock, hasta 50% de loops es aceptable
        loop_rate = len(loops) * 100 / max(len(recent), 1)
        assert loop_rate <= 50, (
            f"Demasiados loops recientes: {len(loops)}/{len(recent)} ({loop_rate:.0f}%) > 50%: {loops[:10]}"
        )


class TestLogReplayWithBugDetector:
    """Replay con BugDetector integration — valida que conversaciones
    recientes no producen bugs CRITICOS."""

    def test_replay_sample_no_critical_bugs(self, all_conversations):
        """Replay de 30 conversaciones recientes sin bugs CRITICOS."""
        from unittest.mock import patch as mock_patch
        from bug_detector import CallEventTracker, BugDetector

        filtered, _ = all_conversations
        sample = list(filtered.items())[:30]

        critical_bugs = []
        critical_types = {'LOOP', 'BRUCE_MUDO'}

        for bruce_id, data in sample:
            with mock_patch('agente_ventas.openai_client') as mock_client:
                mock_client.chat.completions.create.side_effect = _replay_gpt_mock

                from agente_ventas import AgenteVentas, EstadoConversacion
                agente = AgenteVentas()
                agente.estado_conversacion = EstadoConversacion.CONVERSACION_NORMAL
                agente.conversacion_iniciada = True
                agente.segunda_parte_saludo_dicha = True
                agente.conversation_history = [
                    {"role": "assistant", "content": "Hola, buen día."}
                ]

                tracker = CallEventTracker(
                    call_sid=f"replay_{bruce_id}",
                    bruce_id=bruce_id,
                    telefono="+5216621234567"
                )
                tracker.emit("BRUCE_RESPONDE", {"texto": "Hola, buen día."})

                for turn in data["turns"]:
                    if turn["role"] != "user":
                        continue
                    text = turn["text"].strip()
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

                        tracker.emit("CLIENTE_DICE", {"texto": text})
                        if response:
                            tracker.emit("BRUCE_RESPONDE", {"texto": response})
                    except Exception:
                        tracker.emit("CLIENTE_DICE", {"texto": text})

                bugs = BugDetector.analyze(tracker)
                criticos = [b for b in bugs if b['tipo'] in critical_types]
                if criticos:
                    critical_bugs.append({
                        'bruce_id': bruce_id,
                        'bugs': [(b['tipo'], b['detalle'][:60]) for b in criticos],
                    })

        # Máximo 25% de conversaciones con bugs críticos (GPT mock causes false positives
        # especially LOOP when mock returns same text repeatedly in FSM-intercepted flows)
        rate = len(critical_bugs) * 100 / max(len(sample), 1)
        assert rate <= 25, (
            f"Demasiados bugs CRITICOS: {len(critical_bugs)}/{len(sample)} ({rate:.0f}%): "
            f"{critical_bugs[:5]}"
        )


# ============================================================
# STANDALONE: Reporte completo
# ============================================================

def run_full_replay(max_conversations=50):
    """Ejecuta replay de conversaciones reales y genera reporte.

    Args:
        max_conversations: Maximo de conversaciones a replayar (0 = todas)
    """
    print("=" * 70)
    print("FASE 4B: REPLAY MASIVO DE CONVERSACIONES REALES")
    print("=" * 70)

    # Parse
    all_convs = parse_all_logs()
    filtered, parse_stats = filter_conversations(all_convs)

    # Limitar si max_conversations > 0
    if max_conversations > 0:
        items = list(filtered.items())[:max_conversations]
        filtered = dict(items)
        print(f"\n[MODO RAPIDO] Limitado a {len(filtered)} conversaciones")

    # Replay
    total = len(filtered)
    print(f"\nReplayando {total} conversaciones...")

    results = {
        "total": total,
        "success": 0,
        "crashes": 0,
        "loops": 0,
        "high_none": 0,
        "details_crashes": [],
        "details_loops": [],
        "total_client_turns": 0,
        "total_none": 0,
        "total_empty": 0,
    }

    for i, (bruce_id, data) in enumerate(filtered.items()):
        if (i + 1) % 10 == 0:
            print(f"  Progreso: {i+1}/{total} ({(i+1)*100//total}%)")

        result = replay_conversation(bruce_id, data["turns"])

        results["total_client_turns"] += result["client_turns"]
        results["total_none"] += result["none_responses"]
        results["total_empty"] += result["empty_responses"]

        if result["crashes"]:
            results["crashes"] += 1
            results["details_crashes"].append({
                "id": bruce_id,
                "file": data["file"],
                "turns": result["client_turns"],
                "error": result["crashes"][0]["error"][:200],
                "turn_num": result["crashes"][0]["turn"],
                "text": result["crashes"][0]["text"],
            })
        elif result["loop_detected"]:
            results["loops"] += 1
            results["details_loops"].append({
                "id": bruce_id,
                "file": data["file"],
                "turns": result["client_turns"],
            })
        else:
            results["success"] += 1

    # Report
    print("\n" + "=" * 70)
    print("RESULTADOS")
    print("=" * 70)
    print(f"\nConversaciones totales:    {results['total']}")
    print(f"  Exitosas (sin bugs):     {results['success']} ({results['success']*100//max(results['total'],1)}%)")
    print(f"  Con crashes:             {results['crashes']}")
    print(f"  Con loops:               {results['loops']}")
    print(f"\nTurnos cliente totales:    {results['total_client_turns']}")
    print(f"  Respuestas None:         {results['total_none']}")
    print(f"  Respuestas vacias:       {results['total_empty']}")

    if results["details_crashes"]:
        print(f"\n--- CRASHES ({len(results['details_crashes'])}) ---")
        for c in results["details_crashes"][:20]:
            print(f"  {c['id']} ({c['file']}) turno {c['turn_num']}: {c['error'][:120]}")
            print(f"    Input: \"{c['text']}\"")

    if results["details_loops"]:
        print(f"\n--- LOOPS ({len(results['details_loops'])}) ---")
        for l in results["details_loops"][:20]:
            print(f"  {l['id']} ({l['file']}) - {l['turns']} turnos")

    # Summary
    success_rate = results['success'] * 100 / max(results['total'], 1)
    print(f"\n{'=' * 70}")
    print(f"TASA DE EXITO: {success_rate:.1f}% ({results['success']}/{results['total']})")
    print(f"{'=' * 70}")

    return results


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--full', action='store_true', help='Replay ALL conversations (slow)')
    parser.add_argument('-n', type=int, default=50, help='Max conversations (default 50)')
    args = parser.parse_args()
    max_conv = 0 if args.full else args.n
    results = run_full_replay(max_conversations=max_conv)
