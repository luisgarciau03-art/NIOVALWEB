#!/usr/bin/env python3
"""
Ciclo de Validacion - Orquestador completo zero-llamadas Bruce W.

Ejecuta 4 niveles de validacion en secuencia:

  N1  Rule-based rapido    (~30s,   $0.00)  pre_deploy_check --rapido
  N2  Rule-based completo  (~5min,  $0.00)  pre_deploy_check + OOS 167 escenarios
  N3  GPT Eval produccion  (~15min, ~$1.00) auditoria_profunda --gpt-eval
  N4  Claude Sonnet        (~40min, ~$5.00) auditoria_profunda --agresivo
                                            + validador_v2 --sonnet (OOS)

Reporte unificado: ciclo_validacion_reporte.json + ciclo_validacion_reporte.html

Uso:
    python ciclo_validacion.py                   # Todos los niveles
    python ciclo_validacion.py --nivel 2         # Solo hasta N2 (gratis)
    python ciclo_validacion.py --nivel 3         # Hasta N3 (GPT eval)
    python ciclo_validacion.py --dry-run         # Muestra que correria sin ejecutar
    python ciclo_validacion.py --sin-confirmar   # No pide confirmacion en niveles de pago
    python ciclo_validacion.py --ultimas 20      # Limite N llamadas en auditoria prod
    python ciclo_validacion.py --reporte         # Mostrar ultimo reporte guardado
    python ciclo_validacion.py --nivel 4 --sin-confirmar --ultimas 15
    python ciclo_validacion.py --nivel 4 --vscode-sonnet  # N4 gratis via Claude Code VSCode
"""

import os
import sys
import json
import time
import argparse
import subprocess
from datetime import datetime
from collections import Counter

if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

DIR = os.path.dirname(os.path.abspath(__file__))
REPORTE_JSON          = os.path.join(DIR, 'ciclo_validacion_reporte.json')
REPORTE_HTML          = os.path.join(DIR, 'ciclo_validacion_reporte.html')
AUDIT_JSON            = os.path.join(DIR, 'audit_data', 'ultima_auditoria.json')
OOS_JSON              = os.path.join(DIR, 'validador_v2_reporte.json')
TRANSCRIPCIONES_JSON  = os.path.join(DIR, 'validador_v2_transcripciones.json')
VSCODE_EVAL_INPUT     = os.path.join(DIR, 'audit_data', 'vscode_eval_input.json')
VSCODE_EVAL_OUTPUT    = os.path.join(DIR, 'audit_data', 'vscode_eval_output.json')

# ============================================================
# Colores
# ============================================================
class C:
    OK    = '\033[92m'
    FAIL  = '\033[91m'
    WARN  = '\033[93m'
    BOLD  = '\033[1m'
    CYAN  = '\033[96m'
    DIM   = '\033[2m'
    RESET = '\033[0m'

def ok(msg):   print(f"{C.OK}  [OK]{C.RESET}   {msg}")
def fail(msg): print(f"{C.FAIL}  [FAIL]{C.RESET}  {msg}")
def warn(msg): print(f"{C.WARN}  [WARN]{C.RESET}  {msg}")
def info(msg): print(f"{C.CYAN}  ---{C.RESET}   {msg}")
def titulo(msg):
    print(f"\n{C.BOLD}{'='*65}{C.RESET}")
    print(f"{C.BOLD}  {msg}{C.RESET}")
    print(f"{C.BOLD}{'='*65}{C.RESET}")
def subtitulo(msg):
    print(f"\n{C.CYAN}  {'─'*55}{C.RESET}")
    print(f"{C.CYAN}  {msg}{C.RESET}")
    print(f"{C.CYAN}  {'─'*55}{C.RESET}")

# ============================================================
# Helpers
# ============================================================
def _run(cmd_args, timeout=600, label=""):
    """Ejecuta subprocess, streamos stdout en tiempo real, devuelve (ok, salida, elapsed)."""
    t0 = time.time()
    output_lines = []
    try:
        import os as _os
        _env = _os.environ.copy()
        _env['PYTHONIOENCODING'] = 'utf-8'
        proc = subprocess.Popen(
            [sys.executable] + cmd_args,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            encoding='utf-8',
            errors='replace',
            cwd=DIR,
            env=_env,
        )
        for line in proc.stdout:
            line_s = line.rstrip('\n')
            print(f"    {line_s}")
            output_lines.append(line_s)
        proc.wait(timeout=timeout)
        elapsed = time.time() - t0
        return proc.returncode == 0, '\n'.join(output_lines), elapsed
    except subprocess.TimeoutExpired:
        proc.kill()
        elapsed = time.time() - t0
        warn(f"{label} timeout tras {elapsed:.0f}s")
        return False, '\n'.join(output_lines), elapsed
    except Exception as e:
        elapsed = time.time() - t0
        return False, str(e), elapsed


def _confirmar(prompt_texto):
    """Pide confirmacion al usuario. Retorna True si acepta."""
    try:
        resp = input(f"\n  {C.WARN}{prompt_texto}{C.RESET} [s/N]: ").strip().lower()
        return resp in ('s', 'si', 'y', 'yes')
    except (EOFError, KeyboardInterrupt):
        return False


def _leer_json(path):
    """Lee un JSON, devuelve None si no existe."""
    if os.path.exists(path):
        try:
            with open(path, encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return None
    return None


def evaluar_con_vscode(transcripciones_path=None):
    """
    Modo VSCode Sonnet: exporta transcripciones a audit_data/vscode_eval_input.json,
    espera que el usuario pida a Claude Code (VSCode) que las evalúe y escriba
    audit_data/vscode_eval_output.json, luego lee y devuelve los resultados.

    Retorna dict compatible con fase3_sonnet_audit, o None si se salta.
    """
    tp = transcripciones_path or TRANSCRIPCIONES_JSON
    transcripciones = _leer_json(tp)
    if not transcripciones:
        warn(f"No hay transcripciones en {tp} — salta evaluacion VSCode")
        return None

    os.makedirs(os.path.dirname(VSCODE_EVAL_INPUT), exist_ok=True)

    # Construir input JSON con instrucciones y conversaciones
    eval_input = {
        "instrucciones": (
            "Eres auditor de calidad de Bruce W, un agente de ventas AI que llama a negocios "
            "para ofrecer el catálogo de Nioval. Evalúa cada conversación e identifica bugs.\n\n"
            "TIPOS DE BUG a detectar:\n"
            "  LOOP              - Bruce hace la misma pregunta 3+ veces sin avanzar\n"
            "  DATO_IGNORADO     - El cliente dio un número/correo y Bruce no lo usa/confirma\n"
            "  OFERTA_POST_DESPEDIDA - Bruce se despidió pero luego siguió ofreciendo\n"
            "  PREGUNTA_REPETIDA - Bruce repite la misma pregunta 2 veces seguidas\n"
            "  DATO_NEGADO_REINSISTIDO - Cliente rechazó WhatsApp/correo y Bruce vuelve a pedirlo\n"
            "  GPT_LOGICA_ROTA   - Respuesta incoherente, mezcla idiomas, contradice lo dicho\n\n"
            "Para cada conversación escribe tu evaluación en el output_path indicado."
        ),
        "formato_output": {
            "path": VSCODE_EVAL_OUTPUT,
            "estructura": {
                "total": "número total de conversaciones evaluadas (int)",
                "evaluaciones": [
                    {
                        "id": "OOS-XX-YY (del campo id de la conversacion)",
                        "bugs": [
                            {"tipo": "TIPO_BUG", "detalle": "descripción breve del problema"}
                        ],
                        "calidad": "BUENA | REGULAR | MALA",
                        "nota": "observación opcional"
                    }
                ]
            },
            "nota": "Si no hay bugs en una conversacion, bugs debe ser [] y calidad BUENA o REGULAR"
        },
        "conversaciones": transcripciones,
    }

    with open(VSCODE_EVAL_INPUT, 'w', encoding='utf-8') as f:
        json.dump(eval_input, f, ensure_ascii=False, indent=2)

    titulo("PASO MANUAL — Evaluacion VSCode Sonnet (gratis)")
    info(f"Transcripciones listas: {len(transcripciones)} conversaciones OOS")
    info(f"Input : {VSCODE_EVAL_INPUT}")
    info(f"Output: {VSCODE_EVAL_OUTPUT}")
    print()
    print(f"  {C.BOLD}INSTRUCCIONES:{C.RESET}")
    print(f"  1. En VSCode, pide a Claude Code:")
    print(f"     \"Evalúa las transcripciones en audit_data/vscode_eval_input.json")
    print(f"      siguiendo las instrucciones del archivo, y escribe los resultados")
    print(f"      en audit_data/vscode_eval_output.json\"")
    print(f"  2. Espera que Claude Code termine de evaluar todas las conversaciones")
    print(f"  3. Vuelve aquí y presiona Enter para incorporar los resultados al reporte")
    print()

    try:
        input(f"  {C.WARN}[Esperando] Presiona Enter cuando Claude Code haya terminado...{C.RESET} ")
    except (EOFError, KeyboardInterrupt):
        warn("Evaluacion VSCode saltada por usuario (Ctrl+C / EOF)")
        return None

    output_data = _leer_json(VSCODE_EVAL_OUTPUT)
    if not output_data:
        warn(f"No se encontro {VSCODE_EVAL_OUTPUT} — continuando sin evaluacion Sonnet")
        return None

    evaluaciones = output_data.get('evaluaciones', [])
    if not evaluaciones:
        warn("vscode_eval_output.json no tiene 'evaluaciones' — revisa el formato")
        return None

    convs_con_bug = [e for e in evaluaciones if e.get('bugs')]
    bug_counter = Counter(b['tipo'] for e in evaluaciones for b in e.get('bugs', []))
    tasa = round(len(convs_con_bug) / max(len(evaluaciones), 1), 4)

    ok(f"VSCode Sonnet: {len(evaluaciones)} evaluadas, {len(convs_con_bug)} con bugs, tasa {tasa:.1%}")

    return {
        "total_auditadas": len(evaluaciones),
        "convs_con_bug":   len(convs_con_bug),
        "tasa_bugs":       tasa,
        "bugs_por_tipo":   dict(bug_counter),
        "escenarios_con_bug": [
            {
                "id":      e.get("id", "?"),
                "calidad": e.get("calidad", ""),
                "nota":    e.get("nota", ""),
                "bugs":    e.get("bugs", []),
            }
            for e in convs_con_bug
        ],
    }


def _modelo_activo():
    """Detecta el modelo LLM activo desde .env."""
    from dotenv import load_dotenv
    load_dotenv()
    return os.environ.get('LLM_MODEL', 'gpt-4.1-mini')


# ============================================================
# Nivel 1 — Rule-based rapido
# ============================================================
def ejecutar_n1(dry_run=False):
    subtitulo("NIVEL 1 — Rule-based rapido  (~30s, $0.00)")
    info("pre_deploy_check.py --rapido")
    info("Cobertura: replay 10 logs recientes + banco_regresion 112 patrones")

    if dry_run:
        warn("[DRY-RUN] Saltando ejecucion")
        return {'status': 'DRY_RUN', 'pass': True, 'elapsed': 0}

    exito, salida, elapsed = _run(['pre_deploy_check.py', '--rapido'], timeout=120, label="N1")

    regresiones = 0
    for line in salida.splitlines():
        if 'Regresiones:' in line:
            try:
                regresiones = int(line.split('Regresiones:')[1].strip())
            except Exception:
                pass

    resultado = {
        'status': 'PASS' if exito else 'FAIL',
        'pass': exito,
        'regresiones': regresiones,
        'elapsed': round(elapsed, 1),
    }

    if exito:
        ok(f"N1 PASS — {regresiones} regresiones ({elapsed:.0f}s)")
    else:
        fail(f"N1 FAIL — {regresiones} regresiones detectadas")

    return resultado


# ============================================================
# Nivel 2 — Rule-based completo + OOS 167 escenarios
# ============================================================
def ejecutar_n2(dry_run=False):
    subtitulo("NIVEL 2 — Rule-based completo  (~5min, $0.00)")
    info("pre_deploy_check.py  (replay + banco)")
    info("validador_v2.py --fase 2  (167 escenarios OOS)")
    info("Cobertura: 10 logs reales + 167 OOS (Grupos 1-17) + 112 banco_regresion")

    if dry_run:
        warn("[DRY-RUN] Saltando ejecucion")
        return {'status': 'DRY_RUN', 'pass': True, 'elapsed': 0}

    t0 = time.time()

    # 2a: pre_deploy_check completo
    info("  2a: pre_deploy_check.py (replay + OOS interno + banco)...")
    exito_pdc, salida_pdc, el_pdc = _run(['pre_deploy_check.py'], timeout=360, label="N2-PDC")

    # 2b: validador_v2 fase 2 (OOS 167)
    info("  2b: validador_v2.py --fase 2 (OOS 167 escenarios)...")
    exito_oos, salida_oos, el_oos = _run(['validador_v2.py', '--fase', '2'], timeout=360, label="N2-OOS")

    elapsed = time.time() - t0

    # Leer reporte OOS
    oos_data = _leer_json(OOS_JSON) or {}
    oos_fase2 = oos_data.get('fase2_oos_150', {})
    oos_bugs = oos_fase2.get('bugs_totales', '?')
    oos_tasa = oos_fase2.get('tasa_bugs', '?')
    oos_total = oos_fase2.get('total_convs', '?')

    exito = exito_pdc and exito_oos
    resultado = {
        'status': 'PASS' if exito else 'FAIL',
        'pass': exito,
        'pdc_pass': exito_pdc,
        'oos_pass': exito_oos,
        'oos_total': oos_total,
        'oos_bugs': oos_bugs,
        'oos_tasa_bugs': oos_tasa,
        'elapsed': round(elapsed, 1),
        'oos_reporte': oos_fase2,
    }

    if exito:
        ok(f"N2 PASS — OOS: {oos_bugs} bugs en {oos_total} escenarios ({elapsed:.0f}s)")
    else:
        fail(f"N2 FAIL — PDC:{exito_pdc} OOS:{exito_oos} — {oos_bugs} bugs OOS")

    return resultado


# ============================================================
# Nivel 3 — GPT Eval sobre produccion
# ============================================================
def ejecutar_n3(ultimas_n=30, dry_run=False, sin_confirmar=False):
    costo_est = ultimas_n * 0.03
    subtitulo(f"NIVEL 3 — GPT Eval produccion  (~15min, ~${costo_est:.2f})")
    info(f"auditoria_profunda.py --gpt-eval --ultimas {ultimas_n} --sin-descargar")
    info(f"Cobertura: {ultimas_n} llamadas reales con GPT-4.1-mini eval por llamada")
    info(f"Costo estimado: ~${costo_est:.2f} USD (GPT-4.1-mini, {ultimas_n} llamadas)")

    if dry_run:
        warn("[DRY-RUN] Saltando ejecucion")
        return {'status': 'DRY_RUN', 'pass': True, 'elapsed': 0, 'costo_real': 0}

    if not sin_confirmar:
        if not _confirmar(f"Ejecutar N3 GPT Eval (~${costo_est:.2f})?"):
            warn("N3 saltado por usuario")
            return {'status': 'SKIP', 'pass': True, 'elapsed': 0, 'costo_real': 0}

    t0 = time.time()
    exito, salida, elapsed = _run([
        'auditoria_profunda.py',
        '--gpt-eval',
        '--ultimas', str(ultimas_n),
        '--sin-descargar',
    ], timeout=900, label="N3")

    # Leer reporte auditoria
    audit_data = _leer_json(AUDIT_JSON) or {}
    analisis = audit_data.get('analisis', {})

    bugs_gpt = 0
    for line in salida.splitlines():
        if 'GPT_' in line and ('bugs' in line.lower() or ':' in line):
            pass  # GPT bugs are within the bug_counter

    # Contar bugs GPT del analisis
    bug_counter = analisis.get('bug_counter', {})
    bugs_gpt = sum(v for k, v in bug_counter.items() if k.startswith('GPT_'))
    total_llamadas = analisis.get('total', 0)
    tasa_bugs = analisis.get('tasa_bugs', 0)

    resultado = {
        'status': 'PASS' if exito else 'FAIL',
        'pass': exito,
        'llamadas': total_llamadas,
        'bugs_gpt': bugs_gpt,
        'bug_counter': bug_counter,
        'tasa_bugs': tasa_bugs,
        'elapsed': round(elapsed, 1),
        'costo_real': round(total_llamadas * 0.03, 2),
    }

    if exito:
        ok(f"N3 PASS — {total_llamadas} llamadas, {bugs_gpt} bugs GPT, tasa {tasa_bugs:.1f}% ({elapsed:.0f}s)")
    else:
        fail(f"N3 FAIL — {total_llamadas} llamadas procesadas, {bugs_gpt} bugs GPT")

    return resultado


# ============================================================
# Nivel 4 — Claude Sonnet: produccion + OOS
# ============================================================
def ejecutar_n4(ultimas_n=30, dry_run=False, sin_confirmar=False, vscode_sonnet=False):
    if vscode_sonnet:
        costo_prod  = ultimas_n * 0.03   # Solo GPT eval, no Sonnet API
        costo_oos   = 0.0                # VSCode Claude Code es gratis
        costo_total = costo_prod
        subtitulo(f"NIVEL 4 — VSCode Sonnet  (~30min, ~${costo_total:.2f})")
        info(f"4a: auditoria_profunda.py --gpt-eval --ultimas {ultimas_n}  (~${costo_prod:.2f})")
        info(f"4b: validador_v2.py --exportar-transcripciones + Claude Code eval (GRATIS)")
        info(f"Costo estimado total: ~${costo_total:.2f} USD (sin Anthropic API)")
    else:
        costo_prod  = ultimas_n * 0.15
        costo_oos   = 0.35               # ~17 batches × $0.02
        costo_total = costo_prod + costo_oos
        subtitulo(f"NIVEL 4 — Claude Sonnet completo  (~40min, ~${costo_total:.2f})")
        info(f"4a: auditoria_profunda.py --agresivo --ultimas {ultimas_n}  (~${costo_prod:.2f})")
        info(f"4b: validador_v2.py --fase 2 --sonnet                        (~${costo_oos:.2f})")
        info(f"Costo estimado total: ~${costo_total:.2f} USD (Claude Sonnet 4.6)")

    if dry_run:
        warn("[DRY-RUN] Saltando ejecucion")
        return {'status': 'DRY_RUN', 'pass': True, 'elapsed': 0, 'costo_real': 0}

    if not sin_confirmar and not vscode_sonnet:
        if not _confirmar(f"Ejecutar N4 Claude Sonnet (~${costo_total:.2f})?"):
            warn("N4 saltado por usuario")
            return {'status': 'SKIP', 'pass': True, 'elapsed': 0, 'costo_real': 0}

    t0 = time.time()

    # 4a: auditoria produccion
    if vscode_sonnet:
        info(f"  4a: auditoria_profunda.py --gpt-eval --sin-descargar ({ultimas_n} llamadas)...")
        exito_prod, salida_prod, el_prod = _run([
            'auditoria_profunda.py',
            '--gpt-eval',
            '--ultimas', str(ultimas_n),
            '--sin-descargar',
        ], timeout=900, label="N4a")
    else:
        info("  4a: auditoria_profunda.py --agresivo --gpt-eval --sin-descargar --exportar...")
        exito_prod, salida_prod, el_prod = _run([
            'auditoria_profunda.py',
            '--agresivo',
            '--gpt-eval',
            '--ultimas', str(ultimas_n),
            '--sin-descargar',
            '--exportar',
        ], timeout=2400, label="N4a")

    # 4b: OOS 167 escenarios con Sonnet o VSCode
    fase3_vscode = None
    if vscode_sonnet:
        info("  4b: validador_v2.py --fase 2 --exportar-transcripciones...")
        exito_oos, salida_oos, el_oos = _run([
            'validador_v2.py',
            '--fase', '2',
            '--exportar-transcripciones',
        ], timeout=360, label="N4b")
        # Pausa interactiva para evaluación VSCode
        fase3_vscode = evaluar_con_vscode(TRANSCRIPCIONES_JSON)
        exito_oos = True  # La eval manual no bloquea el pipeline
    else:
        info("  4b: validador_v2.py --fase 2 --sonnet (OOS 167 escenarios)...")
        exito_oos, salida_oos, el_oos = _run([
            'validador_v2.py',
            '--fase', '2',
            '--sonnet',
        ], timeout=1800, label="N4b")

    elapsed = time.time() - t0

    # Leer reportes
    audit_data = _leer_json(AUDIT_JSON) or {}
    analisis   = audit_data.get('analisis', {})

    # Scores produccion (solo cuando --agresivo corre Sonnet en prod)
    scores_prom = analisis.get('scores_promedio', {}) if not vscode_sonnet else {}
    score_total = sum(scores_prom.values()) / len(scores_prom) if scores_prom else 0

    bug_counter_prod = analisis.get('bug_counter', {})
    total_llamadas   = analisis.get('total', 0)
    tasa_bugs_prod   = analisis.get('tasa_bugs', 0)

    # Bugs OOS Sonnet/VSCode
    if vscode_sonnet and fase3_vscode:
        sonnet_bugs_oos  = fase3_vscode.get('convs_con_bug', 0)
        sonnet_tasa_oos  = fase3_vscode.get('tasa_bugs', 0)
        sonnet_total_oos = fase3_vscode.get('total_auditadas', 0)
        sonnet_bugs_tipo = fase3_vscode.get('bugs_por_tipo', {})
    else:
        oos_data = _leer_json(OOS_JSON) or {}
        fase3    = oos_data.get('fase3_sonnet_audit', {})
        sonnet_bugs_oos  = fase3.get('bugs_totales', 0)
        sonnet_tasa_oos  = fase3.get('tasa_bugs', 0)
        sonnet_total_oos = fase3.get('total_auditadas', 0)
        sonnet_bugs_tipo = fase3.get('bugs_por_tipo', {})

    exito = exito_prod and exito_oos
    costo_real = round(total_llamadas * (0.03 if vscode_sonnet else 0.15) + (0 if vscode_sonnet else costo_oos), 2)

    resultado = {
        'status': 'PASS' if exito else 'FAIL',
        'pass': exito,
        'modo': 'vscode_sonnet' if vscode_sonnet else 'api_sonnet',
        'prod': {
            'llamadas':           total_llamadas,
            'tasa_bugs':          tasa_bugs_prod,
            'bug_counter':        bug_counter_prod,
            'score_promedio':     round(score_total, 2),
            'scores_por_dimension': scores_prom,
        },
        'oos_sonnet': {
            'total':          sonnet_total_oos,
            'bugs':           sonnet_bugs_oos,
            'tasa_bugs':      sonnet_tasa_oos,
            'bugs_por_tipo':  sonnet_bugs_tipo,
        },
        'elapsed':    round(elapsed, 1),
        'costo_real': costo_real,
    }

    if exito:
        modo_str = "VSCode" if vscode_sonnet else "Sonnet"
        ok(f"N4 PASS ({modo_str}) — OOS: {sonnet_bugs_oos} bugs / {sonnet_total_oos} convs ({elapsed:.0f}s)")
    else:
        fail(f"N4 FAIL — Prod:{exito_prod} OOS:{exito_oos}")

    return resultado


# ============================================================
# Reporte unificado
# ============================================================
def _veredicto(niveles):
    """Calcula veredicto final del ciclo."""
    estados = {k: v.get('status', 'SKIP') for k, v in niveles.items()}

    if any(v == 'FAIL' for v in estados.values()):
        bugs_criticos = []
        for k, v in niveles.items():
            if v.get('status') == 'FAIL':
                bugs_criticos.append(k)
        return 'DEPLOY_BLOQUEADO', bugs_criticos

    # Si N3 o N4 corrieron y tienen bugs significativos → revision
    n3 = niveles.get('n3', {})
    n4 = niveles.get('n4', {})
    bugs_gpt = n3.get('bugs_gpt', 0) if n3.get('status') == 'PASS' else 0
    score = n4.get('prod', {}).get('score_promedio', 10) if n4.get('status') == 'PASS' else 10
    sonnet_oos_bugs = n4.get('oos_sonnet', {}).get('bugs', 0) if n4.get('status') == 'PASS' else 0

    if bugs_gpt >= 5 or score < 5.0 or sonnet_oos_bugs >= 5:
        return 'REVISION_REQUERIDA', []

    return 'DEPLOY_OK', []


def generar_reporte_json(niveles, modelo, elapsed_total):
    """Guarda reporte unificado JSON."""
    veredicto, problemas = _veredicto(niveles)
    reporte = {
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'modelo': modelo,
        'elapsed_total': round(elapsed_total, 1),
        'veredicto': veredicto,
        'problemas': problemas,
        'niveles': niveles,
    }
    with open(REPORTE_JSON, 'w', encoding='utf-8') as f:
        json.dump(reporte, f, ensure_ascii=False, indent=2)
    return reporte


def generar_reporte_html(reporte):
    """Genera reporte HTML con tabla de resultados."""
    ts = reporte['timestamp']
    modelo = reporte['modelo']
    veredicto = reporte['veredicto']
    elapsed = reporte['elapsed_total']
    niveles = reporte['niveles']

    color_veredicto = {
        'DEPLOY_OK':          '#28a745',
        'REVISION_REQUERIDA': '#ffc107',
        'DEPLOY_BLOQUEADO':   '#dc3545',
    }.get(veredicto, '#6c757d')

    # Filas niveles
    filas_niveles = ""
    nivel_info = {
        'n1': ('N1 Rule-based rapido',   '$0.00',  '~30s'),
        'n2': ('N2 Rule-based completo', '$0.00',  '~5min'),
        'n3': ('N3 GPT Eval prod',       '~$1.00', '~15min'),
        'n4': ('N4 Claude Sonnet',       '~$5.00', '~40min'),
    }
    for clave, (nombre, costo, tiempo) in nivel_info.items():
        niv = niveles.get(clave, {})
        status = niv.get('status', 'SKIP')
        elapsed_n = niv.get('elapsed', 0)
        status_color = {'PASS': '#28a745', 'FAIL': '#dc3545', 'SKIP': '#6c757d', 'DRY_RUN': '#adb5bd'}.get(status, '#6c757d')

        # Detalles por nivel
        detalles = ""
        if clave == 'n1':
            reg = niv.get('regresiones', 0)
            detalles = f"Regresiones: {reg}"
        elif clave == 'n2':
            detalles = f"OOS: {niv.get('oos_bugs','?')} bugs en {niv.get('oos_total','?')} escenarios"
        elif clave == 'n3':
            tasa_n3h = niv.get('tasa_bugs', 0)
            detalles = f"Llamadas: {niv.get('llamadas','?')}, Bugs GPT: {niv.get('bugs_gpt','?')}, Tasa: {tasa_n3h:.1f}%" if isinstance(tasa_n3h, float) else f"Bugs GPT: {niv.get('bugs_gpt','?')}"
        elif clave == 'n4':
            prod = niv.get('prod', {})
            oos_s = niv.get('oos_sonnet', {})
            detalles = (f"Score prod: {prod.get('score_promedio','?')}/10 | "
                        f"Bugs OOS Sonnet: {oos_s.get('bugs','?')}")

        filas_niveles += f"""
        <tr>
          <td><strong>{nombre}</strong></td>
          <td>{costo}</td>
          <td>{tiempo}</td>
          <td style="color:{status_color}; font-weight:bold">{status}</td>
          <td>{elapsed_n:.0f}s</td>
          <td>{detalles}</td>
        </tr>"""

    # Top bugs N3/N4
    bug_rows = ""
    all_bugs = Counter()
    for clave in ('n3', 'n4'):
        niv = niveles.get(clave, {})
        for btype, cnt in (niv.get('bug_counter') or {}).items():
            all_bugs[btype] += cnt
        for btype, cnt in (niv.get('prod', {}).get('bug_counter') or {}).items():
            all_bugs[btype] += cnt
    if all_bugs:
        for btype, cnt in all_bugs.most_common(10):
            sev_color = '#dc3545' if 'GPT_' in btype else '#ffc107'
            bug_rows += f"<tr><td style='color:{sev_color}'>{btype}</td><td>{cnt}</td></tr>"

    # Scores Sonnet
    scores_rows = ""
    n4_data = niveles.get('n4', {})
    scores = n4_data.get('prod', {}).get('scores_por_dimension', {})
    if scores:
        for dim, val in sorted(scores.items()):
            bar_w = int(val * 10)
            bar_color = '#28a745' if val >= 7 else ('#ffc107' if val >= 4 else '#dc3545')
            alerta = " ⚠" if val < 5 else ""
            scores_rows += f"""
            <tr>
              <td>{dim}{alerta}</td>
              <td>
                <div style="background:#e9ecef;border-radius:4px;height:18px;width:200px">
                  <div style="background:{bar_color};width:{bar_w}%;height:100%;border-radius:4px"></div>
                </div>
              </td>
              <td>{val:.1f}/10</td>
            </tr>"""

    html = f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Ciclo Validacion Bruce W — {ts[:10]}</title>
<style>
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background:#f8f9fa; margin:0; padding:20px; color:#212529 }}
  .container {{ max-width:960px; margin:0 auto; background:#fff; border-radius:8px; padding:30px; box-shadow:0 2px 8px rgba(0,0,0,.1) }}
  h1 {{ font-size:1.5rem; margin-bottom:4px }}
  .meta {{ color:#6c757d; font-size:.9rem; margin-bottom:24px }}
  .veredicto {{ display:inline-block; padding:8px 24px; border-radius:6px; color:#fff; font-weight:bold; font-size:1.1rem; margin-bottom:24px; background:{color_veredicto} }}
  table {{ width:100%; border-collapse:collapse; margin-bottom:24px }}
  th {{ background:#343a40; color:#fff; padding:8px 12px; text-align:left; font-size:.85rem }}
  td {{ padding:8px 12px; border-bottom:1px solid #dee2e6; font-size:.85rem }}
  tr:hover td {{ background:#f8f9fa }}
  h2 {{ font-size:1.1rem; margin:24px 0 8px; border-left:4px solid #007bff; padding-left:10px }}
  .badge {{ padding:2px 8px; border-radius:10px; font-size:.75rem; font-weight:bold }}
  .pass {{ background:#d4edda; color:#155724 }}
  .fail {{ background:#f8d7da; color:#721c24 }}
  .skip {{ background:#e2e3e5; color:#383d41 }}
</style>
</head>
<body>
<div class="container">
  <h1>Ciclo de Validacion Bruce W</h1>
  <div class="meta">Fecha: {ts} | Modelo: {modelo} | Tiempo total: {elapsed:.0f}s</div>
  <div class="veredicto">{veredicto}</div>

  <h2>Resumen por nivel</h2>
  <table>
    <thead>
      <tr><th>Nivel</th><th>Costo</th><th>Tiempo ref.</th><th>Status</th><th>Tiempo real</th><th>Detalles</th></tr>
    </thead>
    <tbody>
      {filas_niveles}
    </tbody>
  </table>

  {"<h2>Top bugs detectados (GPT Eval + Sonnet prod)</h2><table><thead><tr><th>Tipo de bug</th><th>Ocurrencias</th></tr></thead><tbody>" + bug_rows + "</tbody></table>" if bug_rows else ""}

  {"<h2>Scores de calidad Claude Sonnet (produccion)</h2><table><thead><tr><th>Dimension</th><th>Barra</th><th>Score</th></tr></thead><tbody>" + scores_rows + "</tbody></table>" if scores_rows else ""}

  <div style="color:#6c757d;font-size:.8rem;margin-top:24px">
    Generado por ciclo_validacion.py — Bruce W AI Sales Agent
  </div>
</div>
</body>
</html>"""

    with open(REPORTE_HTML, 'w', encoding='utf-8') as f:
        f.write(html)


def imprimir_resumen_final(reporte):
    """Imprime resumen ejecutivo en consola."""
    veredicto = reporte['veredicto']
    elapsed   = reporte['elapsed_total']
    niveles   = reporte['niveles']

    titulo("RESUMEN FINAL — Ciclo de Validacion")
    print(f"  Fecha   : {reporte['timestamp']}")
    print(f"  Modelo  : {reporte['modelo']}")
    print(f"  Tiempo  : {elapsed:.0f}s ({elapsed/60:.1f} min)")
    print()

    color_v = C.OK if veredicto == 'DEPLOY_OK' else (C.WARN if veredicto == 'REVISION_REQUERIDA' else C.FAIL)
    print(f"  Veredicto: {color_v}{C.BOLD}{veredicto}{C.RESET}")
    print()

    # Tabla de niveles
    print(f"  {'NIVEL':<30} {'STATUS':<10} {'TIEMPO':>8}  DETALLE")
    print(f"  {'─'*70}")

    nivel_nombres = {
        'n1': 'N1 Rule-based rapido',
        'n2': 'N2 Rule-based completo',
        'n3': 'N3 GPT Eval produccion',
        'n4': 'N4 Claude Sonnet',
    }
    for clave, nombre in nivel_nombres.items():
        niv = niveles.get(clave)
        if niv is None:
            continue
        status = niv.get('status', 'SKIP')
        elapsed_n = niv.get('elapsed', 0)
        status_str = f"{C.OK}PASS{C.RESET}" if status == 'PASS' else (
            f"{C.FAIL}FAIL{C.RESET}" if status == 'FAIL' else
            f"{C.WARN}SKIP{C.RESET}" if status == 'SKIP' else
            f"{C.DIM}DRY {C.RESET}"
        )
        # Detalle
        if clave == 'n1':
            det = f"{niv.get('regresiones',0)} regresiones"
        elif clave == 'n2':
            det = f"OOS: {niv.get('oos_bugs','?')} bugs / {niv.get('oos_total','?')} escenarios"
        elif clave == 'n3':
            # tasa_bugs viene de auditoria_profunda ya como porcentaje (ej. 3.3 = 3.3%)
            tasa_n3 = niv.get('tasa_bugs', 0)
            det = f"GPT bugs: {niv.get('bugs_gpt','?')} | tasa: {tasa_n3:.1f}%" if isinstance(tasa_n3, float) else f"GPT bugs: {niv.get('bugs_gpt','?')}"
        elif clave == 'n4':
            prod  = niv.get('prod', {})
            oos_s = niv.get('oos_sonnet', {})
            det = f"Score: {prod.get('score_promedio','?')}/10 | OOS Sonnet bugs: {oos_s.get('bugs','?')}"
        else:
            det = ""
        print(f"  {nombre:<30} {status_str:<10} {elapsed_n:>6.0f}s  {det}")

    # Top bugs agregados
    all_bugs = Counter()
    for clave in ('n3', 'n4'):
        niv = niveles.get(clave, {})
        for btype, cnt in (niv.get('bug_counter') or {}).items():
            all_bugs[btype] += cnt
        for btype, cnt in (niv.get('prod', {}).get('bug_counter') or {}).items():
            all_bugs[btype] += cnt
    if all_bugs:
        print(f"\n  TOP BUGS (GPT Eval + Sonnet produccion):")
        for btype, cnt in all_bugs.most_common(8):
            print(f"    {btype:<38} {cnt:3d}")

    # Scores Sonnet
    n4_d = niveles.get('n4', {})
    scores = n4_d.get('prod', {}).get('scores_por_dimension', {})
    if scores:
        print(f"\n  SCORES CALIDAD Claude Sonnet (produccion):")
        for dim, val in sorted(scores.items()):
            bar = '█' * int(val) + '░' * (10 - int(val))
            alerta = f" {C.FAIL}<<<{C.RESET}" if val < 5 else ""
            print(f"    {dim:<32} {val:.1f}/10  {bar}{alerta}")

    print(f"\n  Reporte JSON : ciclo_validacion_reporte.json")
    if os.path.exists(REPORTE_HTML):
        print(f"  Reporte HTML : ciclo_validacion_reporte.html")

    # Acciones sugeridas
    _imprimir_acciones_sugeridas(niveles, veredicto)

    print(f"\n{'='*65}\n")


def _imprimir_acciones_sugeridas(niveles, veredicto):
    """Imprime acciones recomendadas basadas en resultados."""
    acciones = []

    n1 = niveles.get('n1', {})
    n2 = niveles.get('n2', {})
    n3 = niveles.get('n3', {})
    n4 = niveles.get('n4', {})

    if n1.get('status') == 'FAIL':
        reg = n1.get('regresiones', 0)
        acciones.append(f"[CRITICO] {reg} regresiones en replay → revisar FSM/templates antes de deploy")

    if n2.get('status') == 'FAIL':
        bugs_oos = n2.get('oos_bugs', 0)
        acciones.append(f"[CRITICO] {bugs_oos} bugs OOS → revisar patrones FSM + Grupo donde falla")

    if n3.get('status') == 'PASS':
        bugs_gpt = n3.get('bugs_gpt', 0)
        all_bugs = Counter(n3.get('bug_counter', {}))
        top = all_bugs.most_common(3)
        if bugs_gpt >= 3:
            acciones.append(f"[ATENCION] {bugs_gpt} bugs GPT Eval → top: {', '.join(t for t,_ in top)}")

    if n4.get('status') == 'PASS':
        score = n4.get('prod', {}).get('score_promedio', 10)
        scores_dim = n4.get('prod', {}).get('scores_por_dimension', {})
        dims_bajas = [(d, v) for d, v in scores_dim.items() if v < 5]
        if dims_bajas:
            for d, v in sorted(dims_bajas, key=lambda x: x[1]):
                acciones.append(f"[MEJORA] Dimension '{d}' score {v:.1f}/10 < 5 → revisar prompt/template")
        oos_bugs = n4.get('oos_sonnet', {}).get('bugs', 0)
        if oos_bugs >= 3:
            for btype, cnt in Counter(n4.get('oos_sonnet', {}).get('bugs_por_tipo', {})).most_common(3):
                acciones.append(f"[MEJORA] Sonnet OOS detecta {btype} ({cnt}x) → agregar escenario banco_regresion")

    if not acciones:
        if veredicto == 'DEPLOY_OK':
            acciones.append("[OK] Todo limpio — listo para deploy a Railway")
        else:
            acciones.append("[INFO] Revisar reporte HTML para detalles completos")

    print(f"\n  ACCIONES SUGERIDAS:")
    for a in acciones:
        color = C.FAIL if 'CRITICO' in a else (C.WARN if 'ATENCION' in a else C.CYAN)
        print(f"  {color}{a}{C.RESET}")


# ============================================================
# Main
# ============================================================
def main():
    parser = argparse.ArgumentParser(description='Ciclo de Validacion zero-llamadas Bruce W')
    parser.add_argument('--nivel', type=int, choices=[1, 2, 3, 4], default=4,
                        help='Ejecutar hasta nivel N (default: 4 = completo)')
    parser.add_argument('--dry-run', action='store_true',
                        help='Mostrar que correria sin ejecutar')
    parser.add_argument('--sin-confirmar', action='store_true',
                        help='No pedir confirmacion para niveles de pago (N3, N4)')
    parser.add_argument('--ultimas', type=int, default=30,
                        help='N llamadas de produccion para N3/N4 (default: 30)')
    parser.add_argument('--reporte', action='store_true',
                        help='Mostrar ultimo reporte guardado')
    parser.add_argument('--vscode-sonnet', action='store_true',
                        help='N4: usa Claude Code (VSCode) para eval OOS en lugar de Anthropic API (gratis)')
    args = parser.parse_args()

    # ---- Solo mostrar reporte ----
    if args.reporte:
        data = _leer_json(REPORTE_JSON)
        if data:
            print(json.dumps(data, ensure_ascii=False, indent=2))
        else:
            print("No hay reporte previo. Ejecuta sin --reporte primero.")
        return

    # ---- Encabezado ----
    titulo("CICLO DE VALIDACION — Bruce W Zero-Llamadas")
    modelo = _modelo_activo()
    print(f"  Modelo activo : {modelo}")
    print(f"  Nivel maximo  : N{args.nivel}")
    print(f"  Llamadas prod : {args.ultimas} (N3/N4)")
    print(f"  Dry-run       : {'SI' if args.dry_run else 'NO'}")
    if args.vscode_sonnet:
        print(f"  {C.OK}Modo N4       : VSCode Sonnet (GRATIS — sin Anthropic API){C.RESET}")
    print()

    # Estimado de costo total
    costo_est = 0
    if args.nivel >= 3:
        costo_est += args.ultimas * 0.03
    if args.nivel >= 4:
        if args.vscode_sonnet:
            costo_est += args.ultimas * 0.03   # Solo GPT eval, VSCode gratis
        else:
            costo_est += args.ultimas * 0.15 + 0.35
    print(f"  Costo estimado: ${costo_est:.2f} USD")
    if args.dry_run:
        print(f"  {C.WARN}[DRY-RUN]{C.RESET} Los niveles se muestran pero NO se ejecutan")

    t_inicio = time.time()
    niveles  = {}

    # ---- Ejecutar niveles ----
    niveles['n1'] = ejecutar_n1(dry_run=args.dry_run)

    if args.nivel >= 2:
        niveles['n2'] = ejecutar_n2(dry_run=args.dry_run)

    if args.nivel >= 3:
        niveles['n3'] = ejecutar_n3(
            ultimas_n=args.ultimas,
            dry_run=args.dry_run,
            sin_confirmar=args.sin_confirmar,
        )

    if args.nivel >= 4:
        niveles['n4'] = ejecutar_n4(
            ultimas_n=args.ultimas,
            dry_run=args.dry_run,
            sin_confirmar=args.sin_confirmar,
            vscode_sonnet=args.vscode_sonnet,
        )

    elapsed_total = time.time() - t_inicio

    # ---- Reporte ----
    reporte = generar_reporte_json(niveles, modelo, elapsed_total)
    try:
        generar_reporte_html(reporte)
    except Exception as e:
        warn(f"HTML no generado: {e}")

    imprimir_resumen_final(reporte)

    # Exit code
    veredicto = reporte['veredicto']
    sys.exit(0 if veredicto in ('DEPLOY_OK', 'REVISION_REQUERIDA') else 1)


if __name__ == '__main__':
    main()
