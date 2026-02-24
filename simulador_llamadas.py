#!/usr/bin/env python3
"""
Simulador de Llamadas Bruce W
==============================
Testea flujos de conversacion sin Twilio/ElevenLabs/Azure.

Modos:
  - Sin OPENAI_API_KEY: Solo FSM + templates (rapido, gratis)
  - Con OPENAI_API_KEY: FSM + GPT real (~$0.01 por escenario)

Uso:
  python simulador_llamadas.py                  # Todos los escenarios
  python simulador_llamadas.py --verbose        # Detalle completo
  python simulador_llamadas.py --escenario 3    # Solo escenario #3
  python simulador_llamadas.py --list           # Listar escenarios
"""

import os
import sys
import io
import time
import argparse
from datetime import datetime

# Fix Windows console encoding (FSM logs use → character)
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Setup path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Env vars dummy si no existen (evitar crash al importar)
for _k in ['ELEVENLABS_API_KEY', 'TWILIO_ACCOUNT_SID', 'TWILIO_AUTH_TOKEN',
           'TWILIO_PHONE_NUMBER']:
    os.environ.setdefault(_k, 'SIM_DUMMY')

from agente_ventas import AgenteVentas, EstadoConversacion
from bug_detector import BugDetector, CallEventTracker

# ============================================================
# ESCENARIOS DE PRUEBA
# ============================================================

ESCENARIOS = [
    # ----------------------------------------------------------
    # 1. Flujo exitoso completo
    # ----------------------------------------------------------
    {
        "nombre": "Flujo exitoso completo",
        "descripcion": "Saludo -> encargado si -> WhatsApp -> captura -> despedida",
        "contacto": {"nombre_negocio": "Ferreteria Test", "ciudad": "Guadalajara"},
        "turnos": [
            {
                "cliente": "Bueno, buen dia",
                "check_bruce": ["nioval"],
            },
            {
                "cliente": "Si, yo soy el encargado de compras",
                "check_bruce": None,
            },
            {
                "cliente": "Si, me interesa el catalogo por WhatsApp",
                "check_bruce": None,
            },
            {
                "cliente": "Mi WhatsApp es 33 12 34 56 78",
                "check_bruce": None,
            },
        ],
        "bugs_esperados": [],
        "bugs_no_esperados": ["PREGUNTA_IGNORADA"],
    },

    # ----------------------------------------------------------
    # 2. Encargado no esta
    # ----------------------------------------------------------
    {
        "nombre": "Encargado no esta",
        "descripcion": "Saludo -> no esta -> pedir WhatsApp/correo -> captura",
        "contacto": {"nombre_negocio": "Ferreteria Prueba", "ciudad": "Monterrey"},
        "turnos": [
            {
                "cliente": "Bueno",
                "check_bruce": None,
            },
            {
                "cliente": "No, no esta el encargado",
                "check_bruce": None,
            },
            {
                "cliente": "Si, le doy un WhatsApp",
                "check_bruce": None,
            },
            {
                "cliente": "Es 81 23 45 67 89",
                "check_bruce": None,
            },
        ],
        "bugs_esperados": [],
    },

    # ----------------------------------------------------------
    # 3. Pregunta ignorada (FIX 793B)
    # ----------------------------------------------------------
    {
        "nombre": "Pregunta ignorada (FIX 793B)",
        "descripcion": "Cliente pregunta 'quien habla' y Bruce da solo ack",
        "contacto": {"nombre_negocio": "Ferreteria XYZ"},
        "simular_bug": True,
        "turnos_raw": [
            ("bruce", "Me comunico de la marca NIOVAL, manejamos productos ferreteros."),
            ("cliente", "Aja si"),
            ("bruce", "Claro, digame el numero."),
            ("cliente", "Quien habla?"),
            ("bruce", "Si, adelante."),
            ("cliente", "Quien habla?"),
            ("bruce", "Claro, continue."),
        ],
        "bugs_esperados": ["PREGUNTA_IGNORADA"],
    },

    # ----------------------------------------------------------
    # 4. Rechazo inmediato
    # ----------------------------------------------------------
    {
        "nombre": "Rechazo inmediato",
        "descripcion": "Cliente dice 'no me interesa' rapido -> despedida limpia",
        "contacto": {"nombre_negocio": "Tienda ABC"},
        "turnos": [
            {
                "cliente": "Bueno",
                "check_bruce": None,
            },
            {
                "cliente": "No, no me interesa, gracias",
                "check_bruce": None,
            },
        ],
        "bugs_esperados": [],
    },

    # ----------------------------------------------------------
    # 5. Dictado WhatsApp con numero
    # ----------------------------------------------------------
    {
        "nombre": "Dictado WhatsApp",
        "descripcion": "Encargado presente -> ofrece WhatsApp -> dicta numero",
        "contacto": {"nombre_negocio": "Ferreteria Delta"},
        "turnos": [
            {
                "cliente": "Si, buen dia, digame",
                "check_bruce": None,
            },
            {
                "cliente": "Si, yo me encargo de las compras",
                "check_bruce": None,
            },
            {
                "cliente": "Si, le doy mi WhatsApp",
                "check_bruce": None,
            },
            {
                "cliente": "Es el 55 98 76 54 32",
                "check_bruce": None,
            },
        ],
        "bugs_esperados": [],
    },

    # ----------------------------------------------------------
    # 6. Dictado correo electronico
    # ----------------------------------------------------------
    {
        "nombre": "Dictado correo electronico",
        "descripcion": "Encargado da correo en vez de WhatsApp",
        "contacto": {"nombre_negocio": "Herrajes del Norte"},
        "turnos": [
            {
                "cliente": "Bueno, si digame",
                "check_bruce": None,
            },
            {
                "cliente": "Si, yo soy el encargado",
                "check_bruce": None,
            },
            {
                "cliente": "Mejor le doy mi correo",
                "check_bruce": None,
            },
            {
                "cliente": "Es juan arroba gmail punto com",
                "check_bruce": None,
            },
        ],
        "bugs_esperados": [],
    },

    # ----------------------------------------------------------
    # 7. Encargado llega luego (callback)
    # ----------------------------------------------------------
    {
        "nombre": "Callback - encargado llega luego",
        "descripcion": "Encargado no esta -> viene manana -> programar callback",
        "contacto": {"nombre_negocio": "Ferreteria Omega"},
        "turnos": [
            {
                "cliente": "Bueno",
                "check_bruce": None,
            },
            {
                "cliente": "No, ahorita no esta, viene manana",
                "check_bruce": None,
            },
            {
                "cliente": "Por la manana, como a las 9",
                "check_bruce": None,
            },
        ],
        "bugs_esperados": [],
    },

    # ----------------------------------------------------------
    # 8. Pitch repetido (bug detector)
    # ----------------------------------------------------------
    {
        "nombre": "Pitch repetido (deteccion bug)",
        "descripcion": "Bruce repite pitch de NIOVAL 2x -> bug PITCH_REPETIDO",
        "contacto": {"nombre_negocio": "Ferreteria Bug"},
        "simular_bug": True,
        "turnos_raw": [
            ("bruce", "Hola, buen dia. Me comunico de la marca NIOVAL, manejamos productos ferreteros de alta calidad."),
            ("cliente", "Aja, si"),
            ("bruce", "Me comunico de la marca NIOVAL, trabajamos productos ferreteros. Se encontrara el encargado de compras?"),
            ("cliente", "No, no esta"),
            ("bruce", "Entiendo. Me podria dar un WhatsApp?"),
        ],
        "bugs_esperados": ["PITCH_REPETIDO"],
    },
]


# ============================================================
# SIMULADOR
# ============================================================

class SimuladorLlamada:
    """Ejecuta escenarios de prueba contra AgenteVentas + BugDetector."""

    def __init__(self, verbose=False):
        self.verbose = verbose
        self.tiene_openai = bool(os.environ.get('OPENAI_API_KEY', ''))
        self.resultados = []

    def ejecutar_escenario(self, idx, escenario):
        """Ejecuta un escenario y retorna resultado."""
        nombre = escenario["nombre"]
        resultado = {
            "nombre": nombre,
            "idx": idx + 1,
            "turnos": [],
            "bugs_detectados": [],
            "bugs_esperados": escenario.get("bugs_esperados", []),
            "bugs_no_esperados": escenario.get("bugs_no_esperados", []),
            "passed": False,
            "errores": [],
            "tiempo_ms": 0,
        }

        t0 = time.time()

        try:
            if escenario.get("simular_bug"):
                # Modo raw: conversacion pre-armada (para testear bug detector)
                self._ejecutar_raw(escenario, resultado)
            else:
                # Modo normal: usa AgenteVentas.procesar_respuesta()
                self._ejecutar_agente(escenario, resultado)
        except Exception as e:
            resultado["errores"].append(f"EXCEPCION: {e}")

        resultado["tiempo_ms"] = int((time.time() - t0) * 1000)

        # Evaluar pass/fail
        self._evaluar_resultado(resultado)
        self.resultados.append(resultado)
        return resultado

    def _ejecutar_agente(self, escenario, resultado):
        """Ejecuta escenario usando AgenteVentas real."""
        contacto = escenario.get("contacto", {})
        agente = AgenteVentas(contacto_info=contacto)
        saludo = agente.iniciar_conversacion()

        # Setup segunda parte saludo (simula lo que hace servidor)
        agente.conversacion_iniciada = True
        agente.segunda_parte_saludo_dicha = True

        # Agregar pitch al historial (simula turno 1 completo)
        pitch = agente._get_segunda_parte_saludo() if hasattr(agente, '_get_segunda_parte_saludo') else ""
        if pitch:
            agente.conversation_history.append({"role": "assistant", "content": pitch})
            saludo_completo = f"{saludo} {pitch}"
        else:
            saludo_completo = saludo

        resultado["turnos"].append({
            "role": "bruce",
            "texto": saludo_completo,
            "estado": str(agente.estado_conversacion.value),
        })

        for turno in escenario.get("turnos", []):
            cliente_dice = turno["cliente"]

            try:
                respuesta = agente.procesar_respuesta(cliente_dice)
            except Exception as e:
                respuesta = f"[ERROR: {e}]"
                resultado["errores"].append(f"procesar_respuesta error: {e}")

            resultado["turnos"].append({
                "role": "cliente",
                "texto": cliente_dice,
            })
            resultado["turnos"].append({
                "role": "bruce",
                "texto": respuesta or "[VACIO]",
                "estado": str(agente.estado_conversacion.value),
            })

            # Checks por turno
            if turno.get("check_bruce"):
                for keyword in turno["check_bruce"]:
                    if keyword.lower() not in (respuesta or "").lower():
                        resultado["errores"].append(
                            f"Check fallido: '{keyword}' no encontrado en respuesta Bruce"
                        )

        # Bug detection
        self._run_bug_detector(resultado)

    def _ejecutar_raw(self, escenario, resultado):
        """Ejecuta escenario con conversacion pre-armada (no usa AgenteVentas)."""
        for role, texto in escenario["turnos_raw"]:
            resultado["turnos"].append({
                "role": role,
                "texto": texto,
                "estado": "-",
            })

        # Bug detection
        self._run_bug_detector(resultado)

    def _run_bug_detector(self, resultado):
        """Corre bug detector rule-based sobre la conversacion."""
        tracker = CallEventTracker(
            call_sid=f"SIM-{resultado['idx']:03d}",
            bruce_id=f"SIMTEST-{resultado['idx']:03d}",
            telefono="0000000000"
        )

        for turno in resultado["turnos"]:
            role = turno["role"]
            texto = turno["texto"]
            if role == "bruce":
                tracker.conversacion.append(("bruce", texto))
                tracker.respuestas_bruce.append(texto)
            elif role == "cliente":
                tracker.conversacion.append(("cliente", texto))
                tracker.textos_cliente.append(texto)

        try:
            bugs = BugDetector.analyze(tracker)
            resultado["bugs_detectados"] = bugs
        except Exception as e:
            resultado["errores"].append(f"Bug detector error: {e}")

    def _evaluar_resultado(self, resultado):
        """Evalua si el escenario paso o fallo."""
        tipos_detectados = {b["tipo"] for b in resultado["bugs_detectados"]}
        passed = True

        # Verificar bugs esperados esten presentes
        for esperado in resultado["bugs_esperados"]:
            if esperado not in tipos_detectados:
                resultado["errores"].append(
                    f"Bug esperado '{esperado}' NO detectado"
                )
                passed = False

        # Verificar bugs no esperados NO esten presentes
        for no_esperado in resultado.get("bugs_no_esperados", []):
            if no_esperado in tipos_detectados:
                resultado["errores"].append(
                    f"Bug inesperado '{no_esperado}' detectado"
                )
                passed = False

        # Si hay errores de ejecucion, falla
        if resultado["errores"]:
            passed = False

        resultado["passed"] = passed


# ============================================================
# REPORTE
# ============================================================

def imprimir_reporte(resultados, verbose=False):
    """Imprime reporte formateado."""
    modo = "GPT REAL" if os.environ.get('OPENAI_API_KEY', '') else "TEMPLATE (sin OPENAI_API_KEY)"
    total = len(resultados)
    passed = sum(1 for r in resultados if r["passed"])
    failed = total - passed

    print()
    print("=" * 60)
    print("  SIMULADOR DE LLAMADAS BRUCE W")
    print(f"  Modo: {modo}")
    print(f"  Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    print()

    for r in resultados:
        idx = r["idx"]
        nombre = r["nombre"]
        status = "PASS" if r["passed"] else "FAIL"
        icon = "[OK]" if r["passed"] else "[FAIL]"
        tiempo = r["tiempo_ms"]

        print(f"  [{idx}/{total}] {nombre}")

        if verbose:
            # Mostrar cada turno
            turno_num = 0
            for t in r["turnos"]:
                if t["role"] == "cliente":
                    turno_num += 1
                    print(f"    T{turno_num} Cliente: \"{t['texto'][:80]}\"")
                elif t["role"] == "bruce":
                    estado = t.get("estado", "")
                    estado_str = f" [{estado}]" if estado and estado != "-" else ""
                    print(f"       Bruce:   \"{t['texto'][:80]}\"{estado_str}")
            print()

        # Bugs detectados
        bugs = r["bugs_detectados"]
        if bugs:
            tipos_str = ", ".join(f"{b['tipo']}({b['severidad']})" for b in bugs)
            print(f"    Bugs: {tipos_str}")

        # Errores
        for err in r["errores"]:
            print(f"    ERROR: {err}")

        print(f"    {icon} {status} ({tiempo}ms)")
        print()

    # Resumen
    print("=" * 60)
    if failed == 0:
        print(f"  RESULTADO: {passed}/{total} PASS")
    else:
        print(f"  RESULTADO: {passed}/{total} PASS, {failed} FAIL")
    print("=" * 60)
    print()


# ============================================================
# MAIN
# ============================================================

def main():
    parser = argparse.ArgumentParser(description="Simulador de llamadas Bruce W")
    parser.add_argument("--verbose", "-v", action="store_true", help="Mostrar detalle completo")
    parser.add_argument("--escenario", "-e", type=int, help="Ejecutar solo escenario N")
    parser.add_argument("--list", "-l", action="store_true", help="Listar escenarios disponibles")
    args = parser.parse_args()

    if args.list:
        print("\nEscenarios disponibles:")
        for i, e in enumerate(ESCENARIOS):
            bug_str = f" -> espera: {', '.join(e.get('bugs_esperados', []))}" if e.get('bugs_esperados') else ""
            print(f"  {i+1}. {e['nombre']}: {e['descripcion']}{bug_str}")
        print()
        return

    sim = SimuladorLlamada(verbose=args.verbose)

    if args.escenario:
        idx = args.escenario - 1
        if 0 <= idx < len(ESCENARIOS):
            sim.ejecutar_escenario(idx, ESCENARIOS[idx])
        else:
            print(f"Error: escenario {args.escenario} no existe (hay {len(ESCENARIOS)})")
            sys.exit(1)
    else:
        for i, escenario in enumerate(ESCENARIOS):
            sim.ejecutar_escenario(i, escenario)

    imprimir_reporte(sim.resultados, verbose=args.verbose)

    # Exit code
    failed = sum(1 for r in sim.resultados if not r["passed"])
    sys.exit(1 if failed > 0 else 0)


if __name__ == "__main__":
    main()
