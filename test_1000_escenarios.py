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
import io
import time
import json
import argparse
from collections import Counter

DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, DIR)

os.environ["PYTHONIOENCODING"] = "utf-8"
# Fix Windows cp1252 stdout encoding for unicode characters (e.g. →)
if hasattr(sys.stdout, 'buffer'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'buffer'):
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

VSCODE_EVAL_INPUT  = os.path.join(DIR, 'audit_data', 'vscode_eval_1000_input.json')
VSCODE_EVAL_OUTPUT = os.path.join(DIR, 'audit_data', 'vscode_eval_1000_output.json')

from escenarios_generator import generate_all


def _evaluar_vscode_sonnet(transcripciones):
    """Exporta transcripciones y espera evaluacion de Claude Code VSCode.

    Usa los mismos criterios que auditoria_profunda.py (_EVAL_AGRESIVO_PROMPT):
    - 8 dimensiones de score (1-10)
    - 20+ tipos de bug con severidad CRITICO/ALTO/MEDIO
    - capa_pipeline, que_debio_decir, patron_repetitivo, sentimiento_cliente_progresion
    - Score < 6.0 = bug de calidad automatico
    """
    os.makedirs(os.path.dirname(VSCODE_EVAL_INPUT), exist_ok=True)

    instrucciones = """\
Eres un AUDITOR IMPLACABLE de calidad para llamadas de ventas telefonicas.
Tu estandar de referencia es un VENDEDOR ESTRELLA humano con 15 anos de experiencia en ventas B2B en Mexico.
CUALQUIER desviacion de ese estandar es un problema.

Bruce es un agente AI que vende productos ferreteros de la marca NIOVAL por telefono. Su pipeline tiene varias capas:
- FSM (maquina de estados): decide transiciones y selecciona templates pre-escritos
- GPT Narrow: prompts especializados enviados a GPT-4.1-mini para respuestas dinamicas
- BTE (Bruce Talk Engine): genera fillers/acknowledgments cuando FSM no tiene respuesta
- Cache: respuestas GPT cacheadas para frases frecuentes
- Post-filtros: reglas que modifican la respuesta final

NOTA: Estas son simulaciones texto-a-texto (sin audio real). Ignora falsos positivos de:
- DICTADO_INTERRUMPIDO (no hay audio)
- AREA_EQUIVOCADA en conversaciones cortas o ambiguas

ESCALA DE CALIFICACION (MUY ESTRICTA):
- 10: PERFECTO. Imposible mejorar.
- 8-9: MUY BUENO. Solo detalles menores.
- 6-7: ACEPTABLE. Funciona pero con areas de mejora.
- 4-5: DEFICIENTE. Errores notables que afectan la conversion.
- 2-3: MALO. El cliente percibe que algo esta mal.
- 1: DESASTROSO. Pierde completamente al cliente.

EVALUA en 8 DIMENSIONES (1-10 cada una):
1. naturalidad: Bruce suena como humano mexicano profesional o como robot
2. efectividad_ventas: avanza la venta de forma estrategica
3. manejo_objeciones: maneja rechazos, dudas o resistencia
4. captura_datos: eficiente pidiendo WhatsApp/correo/telefono
5. cierre: termina la llamada de forma profesional
6. escucha_activa: demuestra que escucho lo que dijo el cliente
7. adaptabilidad: se adapta al estilo/ritmo del cliente
8. fluidez_conversacional: la conversacion fluye naturalmente

TIPOS DE PROBLEMA (busca TODOS agresivamente):
Calidad conversacional:
- RESPUESTA_SUBOPTIMA: respondio "correcto" pero habia una respuesta MEJOR
- SENTIMIENTO_NEGATIVO: el cliente se frustro, confundio o molesto
- OPORTUNIDAD_PERDIDA: cliente mostro interes pero Bruce no lo capitalizo
- FLUJO_ROBOTICO: siguio patron predecible sin adaptarse
- TIMING_INCORRECTO: dijo algo correcto en el MOMENTO equivocado
- FALTA_EMPATIA: no reconocio emocion o situacion del cliente
- REDUNDANCIA: repitio informacion/conceptos/frases que ya dijo
- RESPUESTA_IDEAL: para cada turno, indica si fue la respuesta optima

Bugs tecnicos conocidos:
- PREGUNTA_REPETIDA: repite la MISMA pregunta 2+ veces
- PITCH_REPETIDO: repite el pitch/oferta de productos 2+ veces
- LOOP: ciclo de 3+ turnos repitiendo el mismo patron
- DATO_IGNORADO: cliente dio un dato pero Bruce lo ignoro
- DATO_NEGADO_REINSISTIDO: cliente dijo que NO tiene WA/correo y Bruce vuelve a pedirlo
- DESPEDIDA_PREMATURA: se despidio cuando el cliente aun estaba hablando/interesado
- RESPUESTA_FILLER_INCOHERENTE: respondio con algo sin sentido (posible BTE malo)
- TRANSFER_IGNORADA: cliente pidio hablar con alguien mas y Bruce lo ignoro
- GPT_LOGICA_ROTA: respuesta de GPT contradice el contexto
- TEMPLATE_INADECUADO: FSM selecciono template que no corresponde al contexto
- CACHE_DESACTUALIZADO: respuesta cacheada que no refleja el estado actual

REGLAS ULTRA-ESTRICTAS:
- score_total = promedio de las 8 dimensiones
- BUSCA PROBLEMAS ACTIVAMENTE. Si no encuentras al menos 2, estas siendo demasiado suave
- Un score de 5 significa "mediocre". Un 7 es "aceptable". Solo un 9+ es "bueno"
- Severidad CRITICO: afecta directamente la conversion
- Severidad ALTO: el cliente lo nota y afecta su percepcion de profesionalismo
- Severidad MEDIO: mejorable, un vendedor estrella no lo haria asi
- Score < 6.0 automaticamente es un problema de calidad
- Maximo 10 problemas por conversacion
- Para cada problema indica la capa_pipeline: fsm_template|gpt_narrow|bte|cache|post_filtro|desconocido

Para cada conversacion en "conversaciones", produce una evaluacion con el formato indicado en formato_output."""

    eval_input = {
        "instrucciones": instrucciones,
        "formato_output": {
            "path": VSCODE_EVAL_OUTPUT,
            "estructura": {
                "total": "numero total de conversaciones evaluadas (int)",
                "score_promedio": "promedio de score_total de todas las conversaciones (float)",
                "convs_bajo_umbral": "numero de conversaciones con score_total < 6.0 (int)",
                "bugs_criticos_total": "total de problemas con severidad CRITICO (int)",
                "evaluaciones": [
                    {
                        "id": "OOS-XX-YY",
                        "nombre": "nombre del escenario",
                        "scores": {
                            "naturalidad": "N (1-10)",
                            "efectividad_ventas": "N (1-10)",
                            "manejo_objeciones": "N (1-10)",
                            "captura_datos": "N (1-10)",
                            "cierre": "N (1-10)",
                            "escucha_activa": "N (1-10)",
                            "adaptabilidad": "N (1-10)",
                            "fluidez_conversacional": "N (1-10)"
                        },
                        "score_total": "N (promedio 8 dimensiones, float)",
                        "problemas": [
                            {
                                "tipo": "TIPO_PROBLEMA",
                                "turno": "N (numero de turno donde ocurre)",
                                "severidad": "CRITICO | ALTO | MEDIO",
                                "detalle": "descripcion del problema",
                                "que_dijo_bruce": "texto exacto de Bruce",
                                "que_debio_decir": "lo que diria el vendedor estrella",
                                "capa_pipeline": "fsm_template|gpt_narrow|bte|cache|post_filtro|desconocido"
                            }
                        ],
                        "patron_repetitivo": "si Bruce usa la misma estructura/frase en multiples turnos, describelo",
                        "sentimiento_cliente_progresion": "como evoluciono la actitud del cliente (positivo/neutro/negativo)",
                        "resumen": "2-3 frases evaluando la conversacion con honestidad brutal"
                    }
                ]
            },
            "nota": "Evalua TODAS las conversaciones del array 'conversaciones'. Score < 6.0 = problema de calidad."
        },
        "conversaciones": transcripciones,
    }

    with open(VSCODE_EVAL_INPUT, 'w', encoding='utf-8') as f:
        json.dump(eval_input, f, ensure_ascii=False, indent=2)

    print(f"\n{'='*65}")
    print(f"  EVALUACION VSCODE SONNET (Auditoria Profunda)")
    print(f"{'='*65}")
    print(f"  Transcripciones: {len(transcripciones)} conversaciones")
    print(f"  Criterios: 8 dimensiones | 20+ tipos de bug | severidad CRITICO/ALTO/MEDIO")
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

    # Procesar resultados con criterios de auditoria_profunda
    todos_problemas = [p for e in evaluaciones for p in e.get('problemas', [])]
    bug_counter = Counter(p['tipo'] for p in todos_problemas)
    by_sev = Counter(p.get('severidad', 'MEDIO') for p in todos_problemas)

    scores_totales = [e['score_total'] for e in evaluaciones if isinstance(e.get('score_total'), (int, float))]
    score_prom = sum(scores_totales) / len(scores_totales) if scores_totales else 0
    bajo_umbral = [e for e in evaluaciones if isinstance(e.get('score_total'), (int, float)) and e['score_total'] < 6.0]

    convs_criticas = [e for e in evaluaciones if any(
        p.get('severidad') == 'CRITICO' for p in e.get('problemas', [])
    )]

    print(f"\n  [Sonnet] {len(evaluaciones)} evaluadas")
    print(f"  Score promedio: {score_prom:.1f}/10")
    print(f"  Bajo umbral (<6.0): {len(bajo_umbral)} conversaciones")
    print(f"  Problemas: {len(todos_problemas)} total | CRITICO:{by_sev.get('CRITICO',0)} ALTO:{by_sev.get('ALTO',0)} MEDIO:{by_sev.get('MEDIO',0)}")

    if bug_counter:
        print(f"\n  Problemas por tipo:")
        for bt, cnt in sorted(bug_counter.items(), key=lambda x: -x[1]):
            print(f"    {bt}: {cnt}")

    # Scores por dimension
    dims = ['naturalidad','efectividad_ventas','manejo_objeciones','captura_datos',
            'cierre','escucha_activa','adaptabilidad','fluidez_conversacional']
    scores_dim = {d: [] for d in dims}
    for e in evaluaciones:
        for d in dims:
            v = e.get('scores', {}).get(d)
            if isinstance(v, (int, float)):
                scores_dim[d].append(v)
    print(f"\n  Scores por dimension:")
    for d in dims:
        vals = scores_dim[d]
        avg = sum(vals)/len(vals) if vals else 0
        print(f"    {d:<28s}: {avg:.1f}")

    # Mostrar conversaciones criticas
    if convs_criticas:
        print(f"\n  Conversaciones con problemas CRITICOS ({len(convs_criticas)}):")
        for e in convs_criticas[:20]:
            print(f"    {e['id']} score={e.get('score_total','?')} — {e.get('resumen','')[:80]}")
            for p in e.get('problemas', []):
                if p.get('severidad') == 'CRITICO':
                    print(f"      !!! {p['tipo']}: {p.get('detalle','')[:80]}")
                    if p.get('que_debio_decir'):
                        print(f"          -> Estrella: \"{p['que_debio_decir'][:70]}\"")

    # Bajo umbral
    if bajo_umbral:
        print(f"\n  Conversaciones bajo umbral score<6 ({len(bajo_umbral)}):")
        for e in sorted(bajo_umbral, key=lambda x: x.get('score_total', 10))[:10]:
            print(f"    {e['id']} score={e.get('score_total','?')} — {e.get('resumen','')[:80]}")

    return {
        "total_evaluadas": len(evaluaciones),
        "score_promedio": round(score_prom, 2),
        "bajo_umbral": len(bajo_umbral),
        "bugs_criticos": by_sev.get('CRITICO', 0),
        "bugs_altos": by_sev.get('ALTO', 0),
        "bugs_medios": by_sev.get('MEDIO', 0),
        "bugs_por_tipo": dict(bug_counter),
        "scores_dimension": {d: round(sum(v)/len(v), 1) if (v := scores_dim[d]) else 0 for d in dims},
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
