"""
Espera a que el job de fine-tuning termine y luego corre ciclo_validacion
con el nuevo modelo.
"""
import os
import sys
import time
import json
import subprocess
from dotenv import load_dotenv
load_dotenv()

DIR = os.path.dirname(os.path.abspath(__file__))
JOB_ID = "ftjob-EWCjI2suqAv3w1LQ6qWmlvlz"

try:
    from openai import OpenAI
    client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
except Exception as e:
    print(f"[ERROR] No se pudo conectar a OpenAI: {e}")
    sys.exit(1)

print(f"[INFO] Monitoreando job: {JOB_ID}")
print("[INFO] Revisando cada 60 segundos...\n")

while True:
    try:
        job = client.fine_tuning.jobs.retrieve(JOB_ID)
        status = job.status
        model_id = job.fine_tuned_model

        print(f"[{time.strftime('%H:%M:%S')}] Status: {status}", flush=True)

        if status == "succeeded" and model_id:
            print(f"\n[OK] Fine-tuning completado!")
            print(f"     Modelo: {model_id}")

            # Guardar model ID
            model_file = os.path.join(DIR, "finetune_model_id.txt")
            with open(model_file, "w") as f:
                f.write(model_id)
            print(f"[OK] Guardado en finetune_model_id.txt")

            # Correr ciclo_validacion con el nuevo modelo
            print(f"\n[INFO] Iniciando ciclo_validacion con nuevo modelo...")
            env = os.environ.copy()
            env["PYTHONIOENCODING"] = "utf-8"
            env["LLM_MODEL"] = model_id

            result = subprocess.run(
                [sys.executable, "ciclo_validacion.py"],
                cwd=DIR,
                env=env,
                encoding="utf-8",
                errors="replace",
            )

            print(f"\n[INFO] ciclo_validacion terminado (exit code: {result.returncode})")
            sys.exit(0)

        elif status in ("failed", "cancelled"):
            print(f"\n[ERROR] Job terminado con status: {status}")
            if job.error:
                print(f"  Error: {job.error}")
            sys.exit(1)

        # Mostrar metricas si hay
        events = client.fine_tuning.jobs.list_events(JOB_ID, limit=3)
        for ev in reversed(list(events)):
            if ev.type == "metrics":
                data = ev.data
                step = data.get("step", "?")
                total = data.get("total_steps", "?")
                loss = data.get("train_loss", "?")
                print(f"         Step {step}/{total} | loss={loss:.3f}" if isinstance(loss, float) else f"         Step {step}/{total}")
                break

    except Exception as e:
        print(f"[WARN] Error consultando API: {e}")

    time.sleep(60)
