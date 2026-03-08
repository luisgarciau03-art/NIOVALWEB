#!/usr/bin/env python3
"""
Runner de 1000 escenarios OOS para Bruce W.
Ejecuta escenarios generados por escenarios_generator.py usando AgenteVentas real.

Flags:
  --gpt-eval        : Evalua cada escenario con GPT-4.1-mini (~$0.03/esc, ~$30 total)
  --vscode-sonnet   : Exporta transcripciones y espera eval de Claude Code VSCode (gratis)
  --limit N         : Solo los primeros N escenarios
  --grupo N         : Solo el grupo G{N}
  --verbose         : Muestra todos los PASS
  --stop-on-fail    : Para al primer FAIL
  --list            : Lista escenarios sin ejecutar
"""
import os
import sys
import time
import json
import argparse
from collections import Counter

DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, DIR)

os.environ.setdefault("PYTHONIOENCODING", "utf-8")

VSCODE_EVAL_INPUT  = os.path.join(DIR, 'audit_data', 'vscode_eval_1000_input.json')
VSCODE_EVAL_OUTPUT = os.path.join(DIR, 'audit_data', 'vscode_eval_1000_output.json')

from escenarios_generator import generate_all


def _evaluar_vscode_sonnet(transcripciones):
    """Exporta transcripciones y espera evaluacion de Claude Code VSCode."""
    os.makedirs(os.path.dirname(VSCODE_EVAL_INPUT), exist_ok=True)

    eval_input = {
        "instrucciones": (
            "Eres auditor de calidad de Bruce W, agente de ventas AI que llama a negocios "
            "para ofrecer el catálogo de Nioval.\n\n"
            "Evalúa cada conversación e identifica bugs reales (ignora FP de simulación de texto).\n\n"
            "TIPOS DE BUG:\n"
            "  LOOP                  - Bruce repite la misma pregunta 3+ veces sin avanzar\n"
            "  DATO_IGNORADO         - Cliente dio número/correo y Bruce no lo usó/confirmó\n"
            "  DATO_NEGADO_REINSISTIDO - Cliente rechazó WA/correo y Bruce vuelve a pedirlo\n"
            "  OFERTA_POST_DESPEDIDA - Bruce se despidió y luego siguió ofreciendo\n"
            "  PREGUNTA_REPETIDA     - Bruce repite la misma pregunta 2 veces seguidas\n"
            "  PITCH_REPETIDO        - Bruce repite el pitch de NIOVAL innecesariamente\n"
            "  GPT_LOGICA_ROTA       - Respuesta incoherente o fuera de contexto\n\n"
            "NOTA: DICTADO_INTERRUMPIDO casi siempre es FP en simulación de texto (sin audio real).\n"
            "NOTA: AREA_EQUIVOCADA puede ser FP si la conversación es corta o ambigua.\n\n"
            "Para cada conversación: lista bugs reales con tipo+detalle, calidad (BUENA/REGULAR/MALA)."
        ),
        "formato_output": {
            "path": VSCODE_EVAL_OUTPUT,
            "estructura": {
                "total": "número total de conversaciones evaluadas (int)",
                "bugs_reales": "total de bugs reales detectados (int)",
                "evaluaciones": [
                    {
                        "id": "OOS-XX-YY",
                        "bugs": [{"tipo": "TIPO_BUG", "detalle": "descripción"}],
                        "calidad": "BUENA | REGULAR | MALA",
                        "nota": "observación opcional"
                    }
                ]
            },
            "nota": "Si no hay bugs reales, bugs=[] y calidad=BUENA o REGULAR"
        },
        "conversaciones": transcripciones,
    }

    with open(VSCODE_EVAL_INPUT, 'w', encoding='utf-8') as f:
        json.dump(eval_input, f, ensure_ascii=False, indent=2)

    print(f"\n{'='*65}")
    print(f"  EVALUACION VSCODE SONNET")
    print(f"{'='*65}")
    print(f"  Transcripciones: {len(transcripciones)} conversaciones")
    print(f"  Input : {VSCODE_EVAL_INPUT}")
    print(f"  Output: {VSCODE_EVAL_OUTPUT}")
    print()
    print(f"  INSTRUCCIONES:")
    print(f"  1. En VSCode, pide a Claude Code:")
    print(f"     \"Evalua las transcripciones en audit_data/vscode_eval_1000_input.json")
    print(f"      siguiendo las instrucciones del archivo, y escribe los resultados")
    print(f"      en audit_data/vscode_eval_1000_output.json\"")
    print(f"  2. Espera que Claude Code termine")
    print(f"  3. Presiona Enter para incorporar resultados")
    print()

    try:
        input("  [Esperando] Presiona Enter cuando Claude Code haya terminado... ")
    except (EOFError, KeyboardInterrupt):
        print("  [SKIP] Evaluacion VSCode saltada")
        return None

    if not os.path.exists(VSCODE_EVAL_OUTPUT):
        print(f"  [WARN] No se encontro {VSCODE_EVAL_OUTPUT}")
        return None

    with open(VSCODE_EVAL_OUTPUT, 'r', encoding='utf-8') as f:
        output_data = json.load(f)

    evaluaciones = output_data.get('evaluaciones', [])
    if not evaluaciones:
        print("  [WARN] vscode_eval_output no tiene 'evaluaciones'")
        return None

    bugs_reales = [b for e in evaluaciones for b in e.get('bugs', [])]
    bug_counter = Counter(b['tipo'] for b in bugs_reales)
    convs_con_bug = [e for e in evaluaciones if e.get('bugs')]

    print(f"\n  [Sonnet] {len(evaluaciones)} evaluadas — {len(convs_con_bug)} con bugs reales")
    if bug_counter:
        print(f"  Bugs por tipo:")
        for bt, cnt in sorted(bug_counter.items(), key=lambda x: -x[1]):
            print(f"    {bt}: {cnt}")

    # Mostrar bugs reales encontrados
    if convs_con_bug:
        print(f"\n  Escenarios con bugs reales:")
        for e in convs_con_bug[:30]:
            print(f"    {e['id']} [{e['calidad']}]")
            for b in e['bugs']:
                print(f"      - {b['tipo']}: {b['detalle']}")

    return {
        "total_evaluadas": len(evaluaciones),
        "convs_con_bug": len(convs_con_bug),
        "bugs_por_tipo": dict(bug_counter),
    }


def run_all(verbose=False, limit=None, grupo=None, stop_on_fail=False,
            gpt_eval=False, vscode_sonnet=False):
    """Ejecuta todos los escenarios."""
    from agente_ventas import AgenteVentas
    from bug_detector import CallEventTracker, BugDetector

    if gpt_eval:
        from bug_detector import _evaluar_con_gpt

    scenarios = generate_all()

    if grupo is not None:
        gid_str = f"{grupo:02d}"
        scenarios = [s for s in scenarios if s["id"].split("-")[1] == gid_str]

    if limit:
        scenarios = scenarios[:limit]

    total = len(scenarios)
    passed = 0
    failed = 0
    bugs_by_type = {}
    gpt_bugs_by_type = {}
    failed_scenarios = []
    transcripciones = []  # Para vscode_sonnet
    t0 = time.time()

    costo_est = total * 0.03 if gpt_eval else 0

    print(f"\n{'='*65}")
    print(f"  TEST 1000 ESCENARIOS — {total} escenarios")
    if gpt_eval:
        print(f"  GPT Eval: ON (~${costo_est:.0f} USD estimado)")
    if vscode_sonnet:
        print(f"  VSCode Sonnet: ON (gratis, manual)")
    print(f"{'='*65}\n")

    for idx, esc in enumerate(scenarios, 1):
        esc_id = esc["id"]
        nombre = esc["nombre"]
        contacto = esc["contacto"]
        turnos = esc["turnos"]
        bugs_criticos = esc.get("bugs_criticos", [])

        try:
            agente = AgenteVentas(
                contacto_info=contacto,
                sheets_manager=None,
            )

            tracker = CallEventTracker(
                call_sid=f"TEST1K_{esc_id}",
                bruce_id=f"T1K{idx:04d}",
                telefono=contacto.get("telefono", ""),
            )
            tracker.simulador_texto = True

            # Saludo inicial
            saludo = agente.iniciar_conversacion()
            tracker.emit("BRUCE_RESPONDE", {"texto": saludo or ""})

            transcripcion_turnos = [{"rol": "Bruce", "texto": saludo or ""}]
            check_errors = []

            for turno in turnos:
                cliente_msg = turno["cliente"]
                check_not = turno.get("check_not", [])

                tracker.emit("CLIENTE_DICE", {"texto": cliente_msg})
                transcripcion_turnos.append({"rol": "Cliente", "texto": cliente_msg})

                respuesta = agente.procesar_respuesta(cliente_msg)
                if not respuesta:
                    respuesta = ""
                tracker.emit("BRUCE_RESPONDE", {"texto": respuesta})
                transcripcion_turnos.append({"rol": "Bruce", "texto": respuesta})

                if respuesta and check_not:
                    resp_lower = respuesta.lower()
                    for palabra in check_not:
                        if palabra.lower() in resp_lower:
                            check_errors.append(f"'{palabra}' encontrado en respuesta")

            # Rule-based bug detection
            bugs = BugDetector.analyze(tracker) or []
            bug_types = [b["tipo"] for b in bugs]

            # GPT eval
            gpt_bugs = []
            if gpt_eval:
                tracker.created_at = time.time() - 60  # Evitar skip por "ultra-corta"
                try:
                    gpt_bugs = _evaluar_con_gpt(tracker) or []
                    for gb in gpt_bugs:
                        t = gb.get("tipo", "GPT_BUG")
                        gpt_bugs_by_type[t] = gpt_bugs_by_type.get(t, 0) + 1
                except Exception as e:
                    print(f"    [GPT EVAL ERROR] {e}")

            all_bug_types = bug_types + [b.get("tipo") for b in gpt_bugs]

            # Verificar bugs criticos
            critico_found = False
            for bc in bugs_criticos:
                if bc in all_bug_types:
                    critico_found = True
                    check_errors.append(f"Bug critico {bc} detectado")

            is_pass = len(check_errors) == 0 and not critico_found

            # Guardar transcripcion para VSCode Sonnet
            if vscode_sonnet:
                transcripciones.append({
                    "id": esc_id,
                    "nombre": nombre,
                    "contacto": contacto,
                    "turnos": transcripcion_turnos,
                    "bugs_rule": bug_types,
                    "bugs_gpt": [b.get("tipo") for b in gpt_bugs],
                })

            if is_pass:
                passed += 1
                if verbose:
                    print(f"  [{idx}/{total}] {esc_id} {nombre}")
                    gpt_str = f" | GPT: {[b.get('tipo') for b in gpt_bugs]}" if gpt_eval else ""
                    print(f"    [PASS] Rule bugs: {len(bug_types)}{gpt_str}")
            else:
                failed += 1
                failed_scenarios.append({
                    "id": esc_id,
                    "nombre": nombre,
                    "errors": check_errors,
                    "bugs": bug_types,
                    "gpt_bugs": [b.get("tipo") for b in gpt_bugs],
                })
                print(f"  [{idx}/{total}] {esc_id} {nombre}")
                print(f"    [FAIL] {check_errors}")
                if stop_on_fail:
                    print("\n  [STOP] --stop-on-fail activado")
                    break

            for bt in bug_types:
                bugs_by_type[bt] = bugs_by_type.get(bt, 0) + 1

        except Exception as e:
            failed += 1
            failed_scenarios.append({
                "id": esc_id, "nombre": nombre,
                "errors": [f"EXCEPTION: {e}"], "bugs": [], "gpt_bugs": [],
            })
            print(f"  [{idx}/{total}] {esc_id} {nombre}")
            print(f"    [ERROR] {e}")
            if stop_on_fail:
                break

        if idx % 100 == 0 and not verbose:
            elapsed = time.time() - t0
            print(f"  ... {idx}/{total} ({elapsed:.0f}s) — {passed} pass, {failed} fail")

    elapsed = time.time() - t0

    # Resumen
    print(f"\n{'='*65}")
    print(f"  RESULTADO: {passed}/{passed+failed} PASS ({failed} FAIL)")
    print(f"{'='*65}")

    if bugs_by_type:
        print(f"\n  Bugs rule-based por tipo:")
        for bt, cnt in sorted(bugs_by_type.items(), key=lambda x: -x[1]):
            print(f"    {bt}: {cnt}")

    if gpt_bugs_by_type:
        print(f"\n  Bugs GPT eval por tipo:")
        for bt, cnt in sorted(gpt_bugs_by_type.items(), key=lambda x: -x[1]):
            print(f"    {bt}: {cnt}")

    if failed_scenarios:
        print(f"\n  Escenarios fallidos ({len(failed_scenarios)}):")
        for fs in failed_scenarios[:20]:
            print(f"    {fs['id']}: {fs['nombre']}")
            for err in fs['errors'][:3]:
                print(f"      - {err}")
        if len(failed_scenarios) > 20:
            print(f"    ... y {len(failed_scenarios) - 20} mas")

    print(f"\n  Tiempo: {elapsed:.1f}s ({elapsed/60:.1f} min)")
    print(f"  Tasa de exito: {passed/(passed+failed)*100:.1f}%")

    # VSCode Sonnet eval (al final, con todas las transcripciones)
    sonnet_result = None
    if vscode_sonnet and transcripciones:
        sonnet_result = _evaluar_vscode_sonnet(transcripciones)

    # Guardar reporte
    reporte = {
        "fecha": time.strftime("%Y-%m-%d %H:%M:%S"),
        "total": passed + failed,
        "passed": passed,
        "failed": failed,
        "tasa_exito": round(passed / (passed + failed) * 100, 1),
        "bugs_rule_based": bugs_by_type,
        "bugs_gpt_eval": gpt_bugs_by_type,
        "sonnet_eval": sonnet_result,
        "tiempo_s": round(elapsed, 1),
        "fallidos": failed_scenarios,
    }
    reporte_path = os.path.join(DIR, "test_1000_reporte.json")
    with open(reporte_path, "w", encoding="utf-8") as f:
        json.dump(reporte, f, ensure_ascii=False, indent=2)
    print(f"  Reporte: {reporte_path}")

    return failed == 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test 1000 escenarios OOS")
    parser.add_argument("--verbose", "-v", action="store_true")
    parser.add_argument("--limit", "-l", type=int)
    parser.add_argument("--grupo", "-g", type=int)
    parser.add_argument("--stop-on-fail", action="store_true")
    parser.add_argument("--gpt-eval", action="store_true",
                        help="GPT-4.1-mini eval por escenario (~$0.03/esc)")
    parser.add_argument("--vscode-sonnet", action="store_true",
                        help="Exporta transcripciones para evaluacion Claude Code VSCode (gratis)")
    parser.add_argument("--list", action="store_true")
    args = parser.parse_args()

    if args.list:
        scenarios = generate_all()
        if args.grupo:
            gid_str = f"{args.grupo:02d}"
            scenarios = [s for s in scenarios if s["id"].split("-")[1] == gid_str]
        for s in scenarios:
            print(f"  {s['id']}: {s['nombre']} ({len(s['turnos'])} turnos)")
        print(f"\n  Total: {len(scenarios)} escenarios")
        sys.exit(0)

    success = run_all(
        verbose=args.verbose,
        limit=args.limit,
        grupo=args.grupo,
        stop_on_fail=args.stop_on_fail,
        gpt_eval=args.gpt_eval,
        vscode_sonnet=args.vscode_sonnet,
    )
    sys.exit(0 if success else 1)
