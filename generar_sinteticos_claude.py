#!/usr/bin/env python3
"""
Generador de conversaciones sinteticas para fine-tuning usando Claude.

Claude actua como cliente (con diferentes personalidades y escenarios)
mientras Bruce responde con el pipeline actual. Genera conversaciones
realistas y diversas para enriquecer el dataset de fine-tuning.

Uso:
    python generar_sinteticos_claude.py              # Generar 50 conversaciones
    python generar_sinteticos_claude.py --n 100      # Generar 100
    python generar_sinteticos_claude.py --preview    # Ver ejemplos sin guardar
    python generar_sinteticos_claude.py --append     # Agregar al JSONL existente
"""

import os
import sys
import json
import random
import argparse
import time

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
    import anthropic
except ImportError:
    print("[ERROR] anthropic no instalado. Ejecuta: pip install anthropic")
    sys.exit(1)

from agente_ventas import AgenteVentas
from bug_detector import CallEventTracker, BugDetector
from preparar_dataset_finetune import (
    SYSTEM_PROMPT_FINETUNE, conv_to_jsonl, detectar_outcome
)

# ============================================================
# Perfiles de cliente para Claude
# ============================================================

PERFILES_CLIENTE = [
    # (nombre_perfil, descripcion_para_claude, probabilidad_exito)
    ("encargado_interesado",
     "Eres el encargado de compras de una ferretería mediana. Contestas el teléfono "
     "con disposición. Te interesa conocer productos nuevos. Cuando te pregunten por "
     "WhatsApp, lo das sin problema. Hablas de manera casual pero profesional.",
     0.9),

    ("encargado_ocupado",
     "Eres el encargado de una ferretería. Estás ocupado pero educado. "
     "Al principio dices que estás en llamada o atendiendo clientes. Eventualmente "
     "das tu WhatsApp para recibir información después. Hablas rápido.",
     0.7),

    ("recepcionista_amable",
     "Eres la recepcionista de una ferretería. El encargado no está, salió a "
     "entregar. Eres amable y ofreces tomar el recado. Das el WhatsApp del encargado "
     "sin problema cuando te lo piden.",
     0.8),

    ("dueno_directo",
     "Eres el dueño de una ferretería pequeña. Contestas tú mismo. Eres directo "
     "y práctico. Preguntas qué venden antes de dar datos. Si el producto te "
     "interesa, das tu WhatsApp de inmediato.",
     0.85),

    ("encargado_ausente_regresar",
     "Contestas el teléfono en una ferretería. El encargado regresa en 2 horas. "
     "No quieres dar el WhatsApp del encargado sin su permiso, pero das el correo "
     "del negocio. Eres amable.",
     0.75),

    ("rechazo_suave",
     "Eres el encargado de compras. Ya tienes proveedor de todo lo que necesitas. "
     "Dices educadamente que por ahora no te interesa pero que llamen en 3 meses. "
     "No das datos de contacto.",
     0.1),

    ("rechazo_con_pregunta",
     "Eres el encargado. Primero preguntas de dónde hablan y qué venden exactamente. "
     "Cuando escuchas los productos (ferretería), dices que ya tienen proveedor fijo "
     "pero que llamen después de diciembre. No das datos.",
     0.15),

    ("transfer_encargado",
     "Contestas el teléfono. Cuando preguntan por el encargado de compras, dices "
     "'un momento le paso' y simulas pasar la llamada. Entonces contestas como si "
     "fueras el encargado y ya escuchas el pitch brevemente dado. Das tu WhatsApp.",
     0.8),

    ("ivr_buzon",
     "Contestas como un sistema automático: 'Gracias por llamar a Ferretería X, "
     "para ventas marque 1, para crédito marque 2...' No entiendes el saludo de "
     "Bruce. Después de confusión, dices 'bueno?' como si fuera persona real.",
     0.5),

    ("encargado_email_preferred",
     "Eres el encargado de compras. Prefieres recibir información por correo "
     "electrónico, no por WhatsApp. Das tu correo profesional cuando te lo piden. "
     "Eres formal y eficiente.",
     0.85),

    ("encargado_pide_numero",
     "Eres el encargado. Estás interesado pero prefieres ser tú quien llame. "
     "Preguntas cuál es el número de Bruce/NIOVAL para llamar tú después. "
     "Finalmente también das tu WhatsApp.",
     0.7),

    ("multiples_preguntas",
     "Eres el encargado. Tienes muchas preguntas antes de dar datos: ¿de dónde "
     "son?, ¿qué marcas manejan?, ¿hacen envíos?, ¿tienen crédito?. Después de "
     "respuestas satisfactorias das tu WhatsApp.",
     0.8),
]

NEGOCIOS_SINTETICOS = [
    "Ferretería El Clavo Dorado",
    "Materiales y Herramientas San José",
    "Ferretería Industrial del Norte",
    "Distribuidora Herrera e Hijos",
    "Ferreconstrucciones del Valle",
    "Tornillería y Herramientas La Paz",
    "Ferretería Centro Histórico",
    "Materiales de Construcción Rápidos",
    "Herramientas y Más del Occidente",
    "Ferretería La Paloma",
    "Distribuidora Técnica Monterrey",
    "Ferretería El Maestro",
    "Suministros Industriales Jalisco",
    "Ferretería y Materiales Zárate",
    "Constructor Plus Guadalajara",
]

SYSTEM_CLAUDE_CLIENTE = """Eres un cliente en una llamada telefónica a tu negocio (ferretería/materiales de construcción).
Recibes una llamada de Bruce, un agente de ventas de NIOVAL (marca de productos ferreteros).

PERFIL: {perfil}

INSTRUCCIONES:
- Responde como lo haría una persona real en una llamada de negocios en México
- Habla de manera natural, con el vocabulario típico de un ferretero mexicano
- Tus respuestas deben ser cortas (1-2 oraciones máximo, como en una llamada real)
- Puedes usar expresiones como: "Bueno?", "Digame", "Ahorita está ocupado", "Sale pues", "Sí señor"
- NO seas robot. Varía tu manera de hablar
- Si el agente hace algo incorrecto (pregunta algo que ya respondiste), reacciona con ligera impaciencia
- El nombre de tu negocio es: {negocio}

Responde SOLO con el texto que diría el cliente, sin explicaciones ni notas."""


# ============================================================
# Generador de conversaciones con Claude como cliente
# ============================================================

def generar_conversacion_claude(client_anthropic, agente, perfil_info, negocio):
    """
    Genera una conversacion completa donde:
    - Bruce: pipeline actual de AgenteVentas
    - Cliente: Claude simulando el perfil dado
    """
    perfil_nombre, perfil_desc, _ = perfil_info

    system_cliente = SYSTEM_CLAUDE_CLIENTE.format(
        perfil=perfil_desc,
        negocio=negocio
    )

    import uuid
    turns = []
    historial_claude = []
    _sid = f"SIM_{uuid.uuid4().hex[:8]}"
    _bid = f"CLAUDE_{uuid.uuid4().hex[:6].upper()}"
    tracker = CallEventTracker(call_sid=_sid, bruce_id=_bid)
    tracker.simulador_texto = True

    _farewell = [
        'gracias por su tiempo', 'que tenga buen dia', 'que tenga excelente',
        'hasta luego', 'hasta pronto', 'fue un gusto', 'muchas gracias',
    ]

    try:
        # Saludo inicial de Bruce
        saludo = agente.iniciar_conversacion()
        if saludo:
            turns.append({'role': 'bruce', 'text': saludo})
            tracker.emit("BRUCE_RESPONDE", {"texto": saludo})
            historial_claude.append({"role": "user", "content": saludo})

        # Hasta 8 turnos
        for _ in range(8):
            # Cliente responde (Claude)
            response = client_anthropic.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=80,
                system=system_cliente,
                messages=historial_claude,
            )
            texto_cliente = response.content[0].text.strip()
            if not texto_cliente:
                break

            turns.append({'role': 'cliente', 'text': texto_cliente})
            tracker.emit("CLIENTE_DICE", {"texto": texto_cliente})
            historial_claude.append({"role": "assistant", "content": texto_cliente})

            # Bruce responde (pipeline actual)
            respuesta_bruce = agente.procesar_respuesta(texto_cliente)
            if not respuesta_bruce:
                break

            turns.append({'role': 'bruce', 'text': respuesta_bruce})
            tracker.emit("BRUCE_RESPONDE", {"texto": respuesta_bruce})
            historial_claude.append({"role": "user", "content": respuesta_bruce})

            # Fin de llamada
            if any(p in respuesta_bruce.lower() for p in _farewell):
                break

        return turns, tracker

    except Exception as e:
        return None, None


def validar_conversacion(turns, tracker):
    """Valida que la conversacion sea util para fine-tuning."""
    if not turns or len(turns) < 3:
        return False, "muy_corta"

    # Sin bugs rule-based
    try:
        bugs = BugDetector.analyze(tracker)
        rule_bugs = [b for b in bugs if 'GPT' not in b.get('tipo', '')]
        if rule_bugs:
            tipos = [b['tipo'] for b in rule_bugs]
            return False, f"bugs:{','.join(tipos)}"
    except Exception:
        pass

    # Outcome claro
    conv_fake = {'turns': turns, 'whatsapp_capturado': None, 'email_capturado': None}
    outcome = detectar_outcome(conv_fake)
    if outcome == 'incompleto':
        return False, "sin_outcome"

    return True, outcome


# ============================================================
# Pipeline principal
# ============================================================

def generar_dataset_claude(n_objetivo=50, output_file="bruce_sinteticos_claude.jsonl",
                            preview=False, append=False):
    """Genera n_objetivo conversaciones sinteticas con Claude como cliente."""

    print("=" * 65)
    print("  Generador de Sinteticos con Claude como Cliente")
    print("=" * 65)

    # Verificar API key
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("\n  [ERROR] ANTHROPIC_API_KEY no configurada en .env")
        sys.exit(1)

    client_anthropic = anthropic.Anthropic(api_key=api_key)
    agente = AgenteVentas()

    print(f"\n  Objetivo: {n_objetivo} conversaciones")
    print(f"  Cliente simulado por: claude-haiku-4-5-20251001")
    print(f"  Bruce simulado por: pipeline actual (gpt-4.1-mini)")
    print(f"  Output: {output_file}")

    ejemplos = []
    intentos = 0
    rechazadas = 0
    stats_outcome = {}
    stats_perfil = {}

    max_intentos = n_objetivo * 3  # Margen para rechazos

    print(f"\n  Generando conversaciones...")
    print(f"  {'#':>4} {'Perfil':<25} {'Outcome':<22} {'Turnos':>6} {'Status'}")
    print(f"  {'-'*70}")

    while len(ejemplos) < n_objetivo and intentos < max_intentos:
        intentos += 1

        # Seleccionar perfil y negocio aleatorio
        perfil = random.choice(PERFILES_CLIENTE)
        negocio = random.choice(NEGOCIOS_SINTETICOS)
        perfil_nombre = perfil[0]

        # Generar conversacion
        turns, tracker = generar_conversacion_claude(
            client_anthropic, agente, perfil, negocio
        )

        if not turns:
            rechazadas += 1
            continue

        # Validar
        es_valida, resultado = validar_conversacion(turns, tracker)

        n = len(turns)
        status = "OK" if es_valida else f"SKIP({resultado})"
        print(f"  {len(ejemplos)+1:>4} {perfil_nombre:<25} {resultado:<22} {n:>6} {status}")

        if not es_valida:
            rechazadas += 1
            continue

        # Convertir a JSONL
        conv_fake = {'turns': turns}
        ejemplo = conv_to_jsonl(conv_fake, SYSTEM_PROMPT_FINETUNE)
        if not ejemplo:
            rechazadas += 1
            continue

        ejemplo['_meta'] = {
            'bruce_id': f"CLAUDE_{intentos:04d}",
            'outcome': resultado,
            'negocio': negocio,
            'perfil': perfil_nombre,
            'n_turns': n,
            'sintetico': True,
            'fuente': 'claude',
        }

        ejemplos.append(ejemplo)
        stats_outcome[resultado] = stats_outcome.get(resultado, 0) + 1
        stats_perfil[perfil_nombre] = stats_perfil.get(perfil_nombre, 0) + 1

        # Rate limiting suave
        time.sleep(0.3)

    print(f"\n  {'='*70}")
    print(f"  Generados: {len(ejemplos)} / {n_objetivo}")
    print(f"  Rechazados: {rechazadas} | Intentos: {intentos}")
    print(f"\n  Por outcome:")
    for k, v in sorted(stats_outcome.items(), key=lambda x: -x[1]):
        print(f"    {k}: {v}")
    print(f"\n  Por perfil:")
    for k, v in sorted(stats_perfil.items(), key=lambda x: -x[1]):
        print(f"    {k}: {v}")

    if preview:
        print(f"\n  [PREVIEW] Primer ejemplo:")
        if ejemplos:
            msgs = ejemplos[0]['messages']
            for m in msgs[:8]:
                label = {"system": "SYS", "user": "CLI", "assistant": "BRUCE"}[m['role']]
                txt = m['content'][:100] + ('...' if len(m['content']) > 100 else '')
                print(f"    [{label}] {txt}")
        return

    # Guardar
    mode = 'a' if append else 'w'
    with open(output_file, mode, encoding='utf-8') as f:
        for ej in ejemplos:
            clean = {k: v for k, v in ej.items() if k != '_meta'}
            f.write(json.dumps(clean, ensure_ascii=False) + '\n')

    accion = "Agregados a" if append else "Guardados en"
    print(f"\n  {accion}: {output_file}")

    # Costo estimado
    tokens_aprox = sum(
        sum(len(m['content']) for m in ej['messages'])
        for ej in ejemplos
    ) // 4

    # claude-haiku: $0.25/1M input + $1.25/1M output
    costo_claude = (tokens_aprox * 0.00000025) * 2  # aprox input+output
    # gpt-4.1-mini: $0.15/1M input
    costo_gpt = tokens_aprox * 0.00000015
    print(f"  Tokens aprox: {tokens_aprox:,}")
    print(f"  Costo estimado: ~${costo_claude + costo_gpt:.3f} USD")

    print(f"\n  Para agregar al dataset principal:")
    print(f"    python preparar_dataset_finetune.py --output bruce_finetune")
    print(f"    (los sinteticos de Claude se agregan automaticamente)")

    return output_file


# ============================================================
# CLI
# ============================================================

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Generar conversaciones sinteticas con Claude como cliente'
    )
    parser.add_argument('--n', type=int, default=50,
                        help='Numero de conversaciones a generar (default: 50)')
    parser.add_argument('--output', default='bruce_sinteticos_claude.jsonl',
                        help='Archivo de salida JSONL')
    parser.add_argument('--preview', action='store_true',
                        help='Mostrar ejemplos sin guardar')
    parser.add_argument('--append', action='store_true',
                        help='Agregar al archivo existente en vez de reemplazar')
    parser.add_argument('--seed', type=int, default=42)
    args = parser.parse_args()

    random.seed(args.seed)
    generar_dataset_claude(
        n_objetivo=args.n,
        output_file=args.output,
        preview=args.preview,
        append=args.append,
    )
