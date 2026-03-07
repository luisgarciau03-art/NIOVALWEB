#!/usr/bin/env python3
"""
FASE 3 - Integrar modelo fine-tuned en Bruce y validar.

Actualiza la configuracion de Bruce para usar el modelo fine-tuned,
genera el system prompt reducido, y valida con el simulador.

Uso:
    python integrar_finetune.py --model ft:gpt-4.1-mini:nioval::abc123
    python integrar_finetune.py --auto          # Leer model ID de finetune_model_id.txt
    python integrar_finetune.py --rollback      # Volver a gpt-4.1-mini original
    python integrar_finetune.py --test-only     # Solo correr simulador sin cambiar nada
"""

import os
import sys
import subprocess
import argparse

if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

MODEL_ID_FILE = "finetune_model_id.txt"
ENV_FILE = ".env"
ORIGINAL_MODEL = "gpt-4.1-mini"

# ============================================================
# System Prompt REDUCIDO para produccion con fine-tuned model
# ~200 lineas vs las 1,900 actuales
# El modelo ya conoce el comportamiento por el fine-tuning
# ============================================================

SYSTEM_PROMPT_REDUCIDO = """############################################################
# BRUCE - AGENTE DE VENTAS NIOVAL (Fine-tuned v1)
############################################################

Eres Bruce, agente de ventas de NIOVAL, marca distribuidora de productos ferreteros.

PRODUCTOS: Cintas tapagoteras, grifería, herramientas manuales y eléctricas
(rotomartillos, taladros, esmeriles, kits profesionales), candados, impermeabilizantes,
adhesivos, selladores, material electrico.

OBJETIVO: Capturar WhatsApp o correo del encargado de compras para enviar catálogo.

############################################################
# FLUJO BASE
############################################################

1. SALUDO: "Buen día/tarde, habla con el encargado de compras?"
2. PITCH (si es encargado): Presentar NIOVAL, pedir WhatsApp para catálogo
3. CAPTURA: Anotar número/correo, confirmar, despedirse
4. ENCARGADO AUSENTE: Pedir WhatsApp/correo del encargado para dejarlo

############################################################
# REGLAS CRITICAS (siempre aplican)
############################################################

TONO: Siempre USTED. Nunca tuteo. Nunca "jefe", "patrón", "chamba".

NO REPETIR: Si ya preguntaste algo, NO vuelvas a preguntar.
NO PEDIR DATO YA DADO: Si ya te dieron WhatsApp/correo, confirma y despídete.
NO INSISTIR en rechazo: Si dice "no me interesa", despídete con respeto.

TRANSFERENCIAS: Cuando dicen "le paso", espera en silencio. No preguntes nada.
ENCARGADO = tú hablas con quien puede comprar (dueño/gerente/decisor).

############################################################
# DATOS CAPTURADOS (inyectados dinámicamente por el sistema)
############################################################

{fsm_context_flags}

############################################################
# RESPUESTAS CORTAS
############################################################

Máximo 2 oraciones por turno. Sé directo y profesional.
""".strip()


def leer_model_id():
    """Lee el model ID del archivo generado por submit_finetune.py."""
    if not os.path.exists(MODEL_ID_FILE):
        print(f"  [!] No se encontro {MODEL_ID_FILE}")
        print(f"      Ejecuta primero: python submit_finetune.py")
        return None
    with open(MODEL_ID_FILE) as f:
        return f.read().strip()


def actualizar_env(model_id):
    """Actualiza LLM_MODEL en el archivo .env."""
    if not os.path.exists(ENV_FILE):
        print(f"  [!] No se encontro {ENV_FILE}")
        return False

    with open(ENV_FILE, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    nueva_linea = f"LLM_MODEL={model_id}\n"
    encontrada = False

    for i, line in enumerate(lines):
        if line.startswith('LLM_MODEL='):
            modelo_anterior = line.strip().split('=', 1)[1]
            lines[i] = nueva_linea
            encontrada = True
            print(f"  Actualizado: {modelo_anterior} -> {model_id}")
            break

    if not encontrada:
        lines.append(nueva_linea)
        print(f"  Agregado: LLM_MODEL={model_id}")

    with open(ENV_FILE, 'w', encoding='utf-8') as f:
        f.writelines(lines)

    return True


def guardar_system_prompt_reducido():
    """Guarda el system prompt reducido."""
    prompt_path = "prompts/system_prompt_finetune.txt"
    os.makedirs("prompts", exist_ok=True)

    with open(prompt_path, 'w', encoding='utf-8') as f:
        f.write(SYSTEM_PROMPT_REDUCIDO)

    print(f"  System prompt reducido guardado: {prompt_path}")
    lineas = SYSTEM_PROMPT_REDUCIDO.count('\n') + 1
    print(f"  Lineas: {lineas} (vs 1,942 actuales = -{1942 - lineas} lineas)")
    return prompt_path


def correr_simulador(label=""):
    """Corre el simulador masivo y retorna el conteo de bugs."""
    print(f"\n  Corriendo simulador masivo{' ('+label+')' if label else ''}...")
    result = subprocess.run(
        [sys.executable, "simulador_masivo.py", "--no-claude", "--quick"],
        capture_output=True, text=True, encoding='utf-8', errors='replace',
        cwd=os.path.dirname(os.path.abspath(__file__))
    )

    output = result.stdout + result.stderr
    bugs_line = [l for l in output.split('\n') if 'BUGS TOTALES' in l]
    pass_line = [l for l in output.split('\n') if 'RESULTADO FINAL' in l]

    bugs = "?"
    tasa = "?"
    if bugs_line:
        bugs = bugs_line[0].strip()
    if pass_line:
        tasa = pass_line[0].strip()

    print(f"  {tasa}")
    print(f"  {bugs}")
    return output


def integrar(model_id, test_only=False, usar_prompt_reducido=False):
    """Pipeline completo de integracion."""
    print("=" * 65)
    print("  FASE 3 - Integracion del modelo fine-tuned")
    print("=" * 65)
    print(f"\n  Modelo: {model_id}")

    if test_only:
        print("\n  [MODO TEST] Solo validando con simulador, sin cambios...")
        correr_simulador("modelo actual")
        return

    # Paso 1: Validar que el model ID tiene formato correcto
    if not model_id.startswith('ft:'):
        print(f"  [!] El model ID no parece un fine-tuned model: {model_id}")
        resp = input("  Continuar de todos modos? (s/N): ").strip().lower()
        if resp != 's':
            return

    # Paso 2: Simulador ANTES (baseline)
    print("\n[1/4] Simulador ANTES del cambio (baseline)...")
    output_antes = correr_simulador("antes")

    # Paso 3: Actualizar .env con nuevo modelo
    print(f"\n[2/4] Actualizando configuracion...")
    if not actualizar_env(model_id):
        print("  [ERROR] No se pudo actualizar .env")
        return

    # Paso 4: Guardar system prompt reducido (opcional)
    if usar_prompt_reducido:
        print(f"\n[3/4] Generando system prompt reducido...")
        prompt_path = guardar_system_prompt_reducido()
        print(f"\n  NOTA: Para usar el prompt reducido en produccion,")
        print(f"  actualiza agente_ventas.py para leer '{prompt_path}'")
        print(f"  en lugar de 'prompts/system_prompt.txt'")
    else:
        print(f"\n[3/4] Manteniendo system prompt actual por ahora...")
        print(f"  (Reducir prompt en siguiente iteracion tras validar comportamiento)")

    # Paso 5: Simulador DESPUES
    print(f"\n[4/4] Simulador DESPUES del cambio...")
    output_despues = correr_simulador("despues")

    print("\n" + "=" * 65)
    print("  FASE 3 COMPLETA")
    print("=" * 65)
    print(f"\n  Modelo activo: {model_id}")
    print(f"\n  SIGUIENTE PASO (Fase 4):")
    print(f"    1. Revisar comparativa de bugs arriba")
    print(f"    2. Si mejora o igual: git commit + push a Railway")
    print(f"    3. Si empeora: python integrar_finetune.py --rollback")
    print(f"\n  Para deployment:")
    print(f"    Actualiza Railway env var LLM_MODEL={model_id}")


def rollback():
    """Vuelve al modelo original gpt-4.1-mini."""
    print(f"\n  Haciendo rollback a {ORIGINAL_MODEL}...")
    if actualizar_env(ORIGINAL_MODEL):
        print(f"  Rollback completado. Modelo activo: {ORIGINAL_MODEL}")


# ============================================================
# CLI
# ============================================================

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Integrar modelo fine-tuned en Bruce')
    parser.add_argument('--model', help='Model ID (ej: ft:gpt-4.1-mini:nioval::abc123)')
    parser.add_argument('--auto', action='store_true', help=f'Leer model ID de {MODEL_ID_FILE}')
    parser.add_argument('--rollback', action='store_true', help='Volver a modelo original')
    parser.add_argument('--test-only', action='store_true', help='Solo correr simulador sin cambiar nada')
    parser.add_argument('--prompt-reducido', action='store_true', help='Generar y activar system prompt reducido')
    args = parser.parse_args()

    if args.rollback:
        rollback()
    elif args.test_only:
        integrar(ORIGINAL_MODEL, test_only=True)
    else:
        model_id = args.model
        if args.auto or not model_id:
            model_id = leer_model_id()
        if not model_id:
            print("  Uso: python integrar_finetune.py --model ft:gpt-4.1-mini:nioval::xxxxx")
            print("  O:   python integrar_finetune.py --auto  (si ya corriste submit_finetune.py)")
            sys.exit(1)
        integrar(model_id, usar_prompt_reducido=args.prompt_reducido)
