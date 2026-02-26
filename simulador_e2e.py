#!/usr/bin/env python3
"""
Simulador End-to-End de llamadas Bruce W.

Simula llamadas completas texto-a-texto pasando por toda la pipeline real:
FSM -> Patterns -> GPT (real) -> Post-filters -> Bug Detector

Sin Twilio, sin ElevenLabs, sin Azure Speech. Solo texto.

Uso:
    python simulador_e2e.py                    # Todos los escenarios
    python simulador_e2e.py --verbose          # Con respuestas completas
    python simulador_e2e.py --scenario 1       # Solo escenario 1
    python simulador_e2e.py --list             # Listar escenarios
"""

import os
import sys
import time
import argparse

# FIX: Windows cp1252 no soporta caracteres Unicode como →
# Reconfigurar stdout/stderr para UTF-8 con fallback a reemplazo
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Asegurar path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Cargar .env antes de imports
from dotenv import load_dotenv
load_dotenv()

from agente_ventas import AgenteVentas
from bug_detector import CallEventTracker, BugDetector


# ============================================================
# Escenarios de test
# ============================================================
ESCENARIOS = [
    {
        "id": 1,
        "nombre": "Canal rechazado: WhatsApp -> correo -> telefono",
        "fix_target": "FIX 834+835",
        "contacto": {"nombre_negocio": "Ferreteria El Clavo", "telefono": "3312345678", "ciudad": "Guadalajara"},
        "turnos": [
            {"cliente": "Bueno, buen dia",
             "check_not": []},
            {"cliente": "Si, yo soy el encargado de compras",
             "check_not": []},
            {"cliente": "No tengo WhatsApp",
             "check_not": ["whatsapp", "WhatsApp"]},
            {"cliente": "Tampoco tengo correo",
             "check_not": ["whatsapp", "WhatsApp", "correo", "email"]},
            {"cliente": "El telefono es 33 12 34 56 78",
             "check_not": []},
        ],
        "bugs_criticos": ["DATO_NEGADO_REINSISTIDO", "LOOP"],
    },
    {
        "id": 2,
        "nombre": "Dato ya capturado: WhatsApp dado, no re-pedir",
        "fix_target": "FIX 836",
        "contacto": {"nombre_negocio": "Tornillos Express", "telefono": "5587654321", "ciudad": "CDMX"},
        "turnos": [
            {"cliente": "Bueno",
             "check_not": []},
            {"cliente": "Si, yo mero, soy el encargado",
             "check_not": []},
            {"cliente": "Si, por WhatsApp esta bien",
             "check_not": []},
            {"cliente": "Es el 55 87 65 43 21",
             "check_not": []},
            {"cliente": "Ok, gracias",
             "check_not": ["whatsapp", "WhatsApp"]},
        ],
        "bugs_criticos": ["GPT_LOGICA_ROTA"],
    },
    {
        "id": 3,
        "nombre": "Confirmaciones variadas: orale, perfecto, correcto",
        "fix_target": "FIX 837",
        "contacto": {"nombre_negocio": "Herramientas del Norte", "telefono": "8112345678", "ciudad": "Monterrey"},
        "turnos": [
            {"cliente": "Bueno, buen dia",
             "check_not": []},
            {"cliente": "Orale",
             "check_not": []},
            {"cliente": "Si, soy yo el encargado",
             "check_not": []},
            {"cliente": "Perfecto, mandalo por WhatsApp",
             "check_not": []},
            {"cliente": "33 45 67 89 01",
             "check_not": []},
        ],
        "bugs_criticos": [],
    },
    {
        "id": 4,
        "nombre": "Flujo exitoso completo (referencia limpia)",
        "fix_target": "Baseline",
        "contacto": {"nombre_negocio": "Ferreteria La Llave", "telefono": "5512345678", "ciudad": "CDMX"},
        "turnos": [
            {"cliente": "Buen dia",
             "check_not": []},
            {"cliente": "Si, yo soy",
             "check_not": []},
            {"cliente": "Claro, al WhatsApp",
             "check_not": []},
            {"cliente": "Es el 55 12 34 56 78",
             "check_not": []},
            {"cliente": "Si, esta bien, gracias",
             "check_not": []},
        ],
        "bugs_criticos": [],
    },
    {
        "id": 5,
        "nombre": "Rechazo total: todos canales -> ofrecer contacto Bruce",
        "fix_target": "FIX 834+835",
        "contacto": {"nombre_negocio": "Cerrajeria Segura", "telefono": "3398765432", "ciudad": "Guadalajara"},
        "turnos": [
            {"cliente": "Bueno",
             "check_not": []},
            {"cliente": "No esta el encargado, salio a comer",
             "check_not": []},
            {"cliente": "No tengo WhatsApp del encargado",
             "check_not": ["whatsapp", "WhatsApp"]},
            {"cliente": "Tampoco tengo correo de el",
             "check_not": ["whatsapp", "WhatsApp", "correo", "email"]},
            {"cliente": "No, solo telefono fijo aqui en el negocio",
             "check_not": []},
        ],
        "bugs_criticos": ["LOOP", "DATO_NEGADO_REINSISTIDO"],
    },
    {
        "id": 6,
        "nombre": "No interes rapido: rechazo en pitch",
        "fix_target": "Baseline",
        "contacto": {"nombre_negocio": "Taller Mecanico Perez", "telefono": "2212345678", "ciudad": "Puebla"},
        "turnos": [
            {"cliente": "Bueno",
             "check_not": []},
            {"cliente": "No gracias, no nos interesa",
             "check_not": []},
        ],
        "bugs_criticos": [],
    },
    {
        "id": 7,
        "nombre": "Encargado ausente con callback",
        "fix_target": "Baseline",
        "contacto": {"nombre_negocio": "Ferreteria El Martillo", "telefono": "4412345678", "ciudad": "Queretaro"},
        "turnos": [
            {"cliente": "Bueno, buen dia",
             "check_not": []},
            {"cliente": "No, no esta, viene mas tarde como a las 4",
             "check_not": []},
            {"cliente": "Si, a las 4 de la tarde",
             "check_not": []},
        ],
        "bugs_criticos": [],
    },
]


# ============================================================
# Simulador
# ============================================================
class SimuladorE2E:
    def __init__(self, verbose=False):
        self.verbose = verbose
        self.resultados = []

    def run_scenario(self, escenario):
        """Ejecuta un escenario completo y retorna resultado."""
        eid = escenario["id"]
        nombre = escenario["nombre"]
        fix_target = escenario["fix_target"]

        print(f"\n  [{eid}/{len(ESCENARIOS)}] {nombre}")
        print(f"    Target: {fix_target}")

        t0 = time.time()

        # 1. Crear agente real
        agente = AgenteVentas(
            contacto_info=escenario["contacto"],
            sheets_manager=None,
            resultados_manager=None,
            whatsapp_validator=None,
        )

        # 2. Crear tracker para bug detection
        tracker = CallEventTracker(
            call_sid=f"SIM_E2E_{eid}",
            bruce_id=f"SIM{eid:04d}",
            telefono=escenario["contacto"].get("telefono", ""),
        )

        # 3. Saludo inicial de Bruce
        try:
            saludo = agente.iniciar_conversacion()
            tracker.emit("BRUCE_RESPONDE", {"texto": saludo})
            if self.verbose:
                print(f"    Bruce: {saludo}")
        except Exception as e:
            print(f"    [ERROR] iniciar_conversacion: {e}")
            saludo = ""

        # 4. Loop de turnos
        errores_check = []
        for i, turno in enumerate(escenario["turnos"]):
            cliente_msg = turno["cliente"]
            tracker.emit("CLIENTE_DICE", {"texto": cliente_msg})

            if self.verbose:
                print(f"    Cliente [{i+1}]: {cliente_msg}")

            try:
                respuesta = agente.procesar_respuesta(cliente_msg)
                if not respuesta:
                    respuesta = ""
            except Exception as e:
                respuesta = f"[ERROR: {e}]"
                print(f"    [ERROR] procesar_respuesta turno {i+1}: {e}")

            tracker.emit("BRUCE_RESPONDE", {"texto": respuesta})

            if self.verbose:
                print(f"    Bruce [{i+1}]: {respuesta}")

            # Validar check_not (palabras que NO deben aparecer en la respuesta)
            for palabra in turno.get("check_not", []):
                if palabra.lower() in respuesta.lower():
                    error_msg = f"Turno {i+1}: Bruce dijo '{palabra}' (NO deberia)"
                    errores_check.append(error_msg)
                    if self.verbose:
                        print(f"    ** CHECK FAIL: {error_msg}")

        # 5. Analizar bugs
        duracion = time.time() - t0
        bugs = BugDetector.analyze(tracker)

        # 6. Filtrar bugs criticos que NO deberian aparecer
        bugs_criticos_encontrados = []
        for bug in bugs:
            if bug["tipo"] in escenario.get("bugs_criticos", []):
                bugs_criticos_encontrados.append(bug)

        # 7. Determinar PASS/FAIL
        passed = len(errores_check) == 0 and len(bugs_criticos_encontrados) == 0

        # 8. Mostrar resultado
        bugs_str = ", ".join(f"{b['tipo']}({b['severidad']})" for b in bugs) if bugs else "ninguno"
        status = "PASS" if passed else "FAIL"

        if not self.verbose:
            print(f"    Bugs: {bugs_str}")

        if errores_check:
            for err in errores_check:
                print(f"    ** {err}")

        if bugs_criticos_encontrados:
            for bc in bugs_criticos_encontrados:
                print(f"    ** BUG CRITICO: {bc['tipo']} - {bc['detalle'][:80]}")

        print(f"    [{status}] ({duracion:.1f}s)")

        resultado = {
            "id": eid,
            "nombre": nombre,
            "passed": passed,
            "bugs": bugs,
            "bugs_criticos": bugs_criticos_encontrados,
            "errores_check": errores_check,
            "duracion": duracion,
        }
        self.resultados.append(resultado)
        return resultado

    def run_all(self, scenario_id=None):
        """Ejecuta todos los escenarios (o uno especifico)."""
        print("=" * 60)
        print("  SIMULADOR E2E - Bruce W (GPT real, sin Twilio)")
        print("=" * 60)

        escenarios = ESCENARIOS
        if scenario_id:
            escenarios = [e for e in ESCENARIOS if e["id"] == scenario_id]
            if not escenarios:
                print(f"  Escenario {scenario_id} no encontrado")
                return

        for esc in escenarios:
            self.run_scenario(esc)

        # Resumen
        total = len(self.resultados)
        passed = sum(1 for r in self.resultados if r["passed"])
        failed = total - passed

        print("\n" + "=" * 60)
        print(f"  RESULTADO: {passed}/{total} PASS" + (f", {failed} FAIL" if failed else ""))
        print("=" * 60)

        # Bug summary
        all_bugs = []
        for r in self.resultados:
            all_bugs.extend(r["bugs"])

        if all_bugs:
            from collections import Counter
            bug_counts = Counter(b["tipo"] for b in all_bugs)
            print(f"\n  Bugs totales: {len(all_bugs)}")
            for tipo, count in bug_counts.most_common():
                print(f"    {tipo}: {count}")

        # Costo estimado
        total_duracion = sum(r["duracion"] for r in self.resultados)
        print(f"\n  Tiempo total: {total_duracion:.1f}s")
        print(f"  Costo estimado: ~${len(escenarios) * 0.01:.2f} USD (GPT-4.1-mini)")

        return failed == 0


def main():
    parser = argparse.ArgumentParser(description="Simulador E2E Bruce W")
    parser.add_argument("--verbose", "-v", action="store_true", help="Mostrar respuestas completas")
    parser.add_argument("--scenario", "-s", type=int, help="Ejecutar solo escenario N")
    parser.add_argument("--list", "-l", action="store_true", help="Listar escenarios")
    args = parser.parse_args()

    if args.list:
        print("Escenarios disponibles:")
        for e in ESCENARIOS:
            print(f"  [{e['id']}] {e['nombre']} ({e['fix_target']})")
        return

    sim = SimuladorE2E(verbose=args.verbose)
    success = sim.run_all(scenario_id=args.scenario)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
