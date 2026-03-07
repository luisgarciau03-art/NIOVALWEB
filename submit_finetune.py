#!/usr/bin/env python3
"""
FASE 2 - Submit Fine-tuning a OpenAI y monitoreo del job.

Sube los archivos JSONL generados por preparar_dataset_finetune.py
y lanza el job de fine-tuning en OpenAI. Monitorea el progreso
hasta obtener el model ID final.

Uso:
    python submit_finetune.py                                    # Con archivos default
    python submit_finetune.py --train bruce_finetune_train.jsonl --val bruce_finetune_validation.jsonl
    python submit_finetune.py --status ft-xxxx                  # Ver estado de job existente
    python submit_finetune.py --list                             # Listar todos los jobs
    python submit_finetune.py --cancel ft-xxxx                  # Cancelar job
"""

import os
import sys
import json
import time
import argparse

if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

try:
    from openai import OpenAI
except ImportError:
    print("[ERROR] openai no instalado. Ejecuta: pip install openai")
    sys.exit(1)


# Modelo base a fine-tunear
# Si gpt-4.1-mini no soporta FT, usar gpt-4o-mini (equivalente)
BASE_MODELS = [
    "gpt-4.1-mini",
    "gpt-4o-mini",   # Fallback garantizado
]

# Archivo donde guardamos el model ID al terminar
MODEL_ID_FILE = "finetune_model_id.txt"


def get_client():
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("[ERROR] OPENAI_API_KEY no configurada en .env")
        sys.exit(1)
    return OpenAI(api_key=api_key)


def validar_jsonl(filepath):
    """Valida formato del archivo JSONL antes de subir."""
    errores = []
    n_ejemplos = 0

    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            for i, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                    msgs = obj.get('messages', [])
                    if not msgs:
                        errores.append(f"Linea {i}: sin 'messages'")
                        continue
                    roles = [m['role'] for m in msgs]
                    if 'system' not in roles:
                        errores.append(f"Linea {i}: sin mensaje 'system'")
                    if roles[-1] != 'assistant':
                        errores.append(f"Linea {i}: ultimo mensaje no es 'assistant'")
                    n_ejemplos += 1
                except json.JSONDecodeError as e:
                    errores.append(f"Linea {i}: JSON invalido - {e}")
    except FileNotFoundError:
        return 0, [f"Archivo no encontrado: {filepath}"]

    return n_ejemplos, errores


def subir_archivo(client, filepath, purpose="fine-tune"):
    """Sube archivo a OpenAI y retorna file_id."""
    print(f"  Subiendo {os.path.basename(filepath)}...")
    size_mb = os.path.getsize(filepath) / (1024 * 1024)
    print(f"  Tamano: {size_mb:.2f} MB")

    with open(filepath, 'rb') as f:
        response = client.files.create(file=f, purpose=purpose)

    print(f"  File ID: {response.id}")
    return response.id


def crear_job(client, train_file_id, val_file_id, base_model, suffix="bruce"):
    """Crea el job de fine-tuning en OpenAI."""
    print(f"\n  Creando job de fine-tuning...")
    print(f"  Base model: {base_model}")
    print(f"  Suffix: {suffix}")

    kwargs = {
        "training_file": train_file_id,
        "model": base_model,
        "suffix": suffix,
        "hyperparameters": {
            "n_epochs": "auto",  # OpenAI decide el optimo
        }
    }

    if val_file_id:
        kwargs["validation_file"] = val_file_id

    job = client.fine_tuning.jobs.create(**kwargs)
    print(f"  Job ID: {job.id}")
    print(f"  Status: {job.status}")

    # Guardar job ID para referencia
    with open("finetune_job_id.txt", 'w') as f:
        f.write(job.id)
    print(f"  Job ID guardado en: finetune_job_id.txt")

    return job


def monitorear_job(client, job_id, poll_interval=30):
    """Monitorea el progreso del job hasta completarse."""
    print(f"\n  Monitoreando job {job_id}...")
    print(f"  (Actualizando cada {poll_interval}s. Ctrl+C para salir sin cancelar)\n")

    start_time = time.time()
    ultimo_status = None

    try:
        while True:
            job = client.fine_tuning.jobs.retrieve(job_id)
            status = job.status
            elapsed = int(time.time() - start_time)

            if status != ultimo_status:
                print(f"  [{elapsed:4d}s] Status: {status}")
                ultimo_status = status

            # Mostrar eventos recientes
            try:
                events = client.fine_tuning.jobs.list_events(job_id, limit=3)
                for event in reversed(list(events.data)):
                    if event.message and 'Step' in event.message:
                        print(f"  [{elapsed:4d}s] {event.message}")
                        break
            except Exception:
                pass

            if status == 'succeeded':
                model_id = job.fine_tuned_model
                print(f"\n  ✓ FINE-TUNING COMPLETADO")
                print(f"  Model ID: {model_id}")

                # Guardar model ID
                with open(MODEL_ID_FILE, 'w') as f:
                    f.write(model_id)

                print(f"\n  Model ID guardado en: {MODEL_ID_FILE}")
                print(f"\n  SIGUIENTE PASO (Fase 3):")
                print(f"    1. Actualiza Railway env var:")
                print(f"       LLM_MODEL={model_id}")
                print(f"    2. O ejecuta:")
                print(f"       python integrar_finetune.py --model {model_id}")

                return model_id

            elif status in ('failed', 'cancelled'):
                print(f"\n  [!] Job {status}")
                if hasattr(job, 'error') and job.error:
                    print(f"  Error: {job.error}")
                return None

            time.sleep(poll_interval)

    except KeyboardInterrupt:
        print(f"\n  Monitoreo interrumpido. Job continua en OpenAI.")
        print(f"  Para retomar: python submit_finetune.py --status {job_id}")
        return None


def ver_status(client, job_id):
    """Muestra el estado actual de un job."""
    job = client.fine_tuning.jobs.retrieve(job_id)
    print(f"\n  Job ID: {job.id}")
    print(f"  Status: {job.status}")
    print(f"  Model base: {job.model}")
    if job.fine_tuned_model:
        print(f"  Model ID: {job.fine_tuned_model}")
        with open(MODEL_ID_FILE, 'w') as f:
            f.write(job.fine_tuned_model)
        print(f"  Guardado en: {MODEL_ID_FILE}")

    # Ultimos eventos
    try:
        events = client.fine_tuning.jobs.list_events(job_id, limit=5)
        print(f"\n  Ultimos eventos:")
        for event in reversed(list(events.data)):
            print(f"    [{event.type}] {event.message}")
    except Exception as e:
        print(f"  (No se pudieron obtener eventos: {e})")


def listar_jobs(client):
    """Lista todos los jobs de fine-tuning."""
    jobs = client.fine_tuning.jobs.list(limit=10)
    print(f"\n  Ultimos jobs de fine-tuning:")
    print(f"  {'Job ID':<35} {'Status':<15} {'Model'}")
    print(f"  {'-'*80}")
    for job in jobs.data:
        model = job.fine_tuned_model or job.model
        print(f"  {job.id:<35} {job.status:<15} {model}")


def submit_finetune(train_path, val_path, base_model=None):
    """Pipeline completo: validar -> subir -> crear job -> monitorear."""
    print("=" * 65)
    print("  FASE 2 - Submit Fine-tuning a OpenAI")
    print("=" * 65)

    client = get_client()

    # Paso 1: Validar archivos
    print(f"\n[1/4] Validando archivos JSONL...")
    n_train, errores_train = validar_jsonl(train_path)
    n_val, errores_val = validar_jsonl(val_path) if val_path else (0, [])

    if errores_train:
        print(f"  [ERROR] {len(errores_train)} errores en training file:")
        for e in errores_train[:5]:
            print(f"    {e}")
        return None

    print(f"  Training: {n_train} ejemplos validos")
    if val_path:
        print(f"  Validation: {n_val} ejemplos validos")

    if n_train < 10:
        print(f"  [!] Muy pocos ejemplos ({n_train}). Minimo recomendado: 50.")
        resp = input("  Continuar de todos modos? (s/N): ").strip().lower()
        if resp != 's':
            return None

    # Paso 2: Determinar modelo base
    print(f"\n[2/4] Verificando modelo base...")

    if not base_model:
        # Intentar gpt-4.1-mini primero, fallback a gpt-4o-mini
        for model in BASE_MODELS:
            try:
                client.models.retrieve(model)
                base_model = model
                print(f"  Usando: {base_model}")
                break
            except Exception:
                print(f"  {model}: no disponible para FT")
        if not base_model:
            print("  [ERROR] Ningun modelo base disponible para fine-tuning")
            return None
    else:
        print(f"  Usando: {base_model}")

    # Paso 3: Subir archivos
    print(f"\n[3/4] Subiendo archivos a OpenAI...")
    train_file_id = subir_archivo(client, train_path)
    val_file_id = subir_archivo(client, val_path) if val_path else None

    # Paso 4: Crear job y monitorear
    print(f"\n[4/4] Creando job de fine-tuning...")
    job = crear_job(client, train_file_id, val_file_id, base_model)

    print(f"\n  Job creado exitosamente.")
    print(f"  Tiempo estimado: 30-120 minutos segun tamano del dataset")

    respuesta = input("\n  Monitorear progreso en tiempo real? (S/n): ").strip().lower()
    if respuesta != 'n':
        return monitorear_job(client, job.id)
    else:
        print(f"\n  Para monitorear despues:")
        print(f"    python submit_finetune.py --status {job.id}")
        return job.id


# ============================================================
# CLI
# ============================================================

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Submit y monitoreo de fine-tuning OpenAI')
    parser.add_argument('--train', default='bruce_finetune_train.jsonl', help='Archivo JSONL de training')
    parser.add_argument('--val', default='bruce_finetune_validation.jsonl', help='Archivo JSONL de validation')
    parser.add_argument('--model', help='Modelo base (default: auto-detect)')
    parser.add_argument('--status', metavar='JOB_ID', help='Ver estado de job existente')
    parser.add_argument('--list', action='store_true', help='Listar todos los jobs')
    parser.add_argument('--cancel', metavar='JOB_ID', help='Cancelar un job')
    parser.add_argument('--monitor', metavar='JOB_ID', help='Monitorear job existente')
    args = parser.parse_args()

    client = get_client()

    if args.list:
        listar_jobs(client)
    elif args.status:
        ver_status(client, args.status)
    elif args.cancel:
        job = client.fine_tuning.jobs.cancel(args.cancel)
        print(f"  Job {args.cancel} cancelado. Status: {job.status}")
    elif args.monitor:
        monitorear_job(client, args.monitor)
    else:
        submit_finetune(args.train, args.val, args.model)
