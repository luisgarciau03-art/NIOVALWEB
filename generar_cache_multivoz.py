#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Generador de Cache Multi-Voz para Bruce W Agent
Genera audios pre-cacheados para múltiples voces SIN tocar el cache actual.

Uso:
    python generar_cache_multivoz.py diana_sanchez
    python generar_cache_multivoz.py mauricio
    python generar_cache_multivoz.py todas
"""

import os
import sys
import json
import time
import hashlib
import tempfile
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# ============================================================================
# CONFIGURACIÓN DE VOCES
# ============================================================================

VOCES = {
    "bruce_w": {
        "voice_id": "7uSWXMmzGnsyxZwYFfmK",
        "nombre": "Bruce W - Masculina Original",
        "cache_dir": "audio_cache"  # Directorio actual - NO TOCAR
    },
    "diana_sanchez": {
        "voice_id": "FIhWHKTvfI9sX1beLEJ8",
        "nombre": "Diana Sanchez - Femenina",
        "cache_dir": "audio_cache_diana_sanchez"
    },
    "mauricio": {
        "voice_id": "94zOad0g7T7K4oa7zhDq",
        "nombre": "Mauricio - Masculina",
        "cache_dir": "audio_cache_mauricio"
    }
}

# ============================================================================
# FRASES A GENERAR (mismas que pre_generar_audios_cache en servidor)
# ============================================================================

def obtener_frases_a_generar():
    """Retorna todas las frases que necesitan cache de audio."""

    frases_comunes = {
        # Frases de sistema
        "error": "Lo siento, hubo un error. Le llamaremos más tarde.",
        "confirmacion_presencia": "Sí, estoy aquí.",

        # Frases de "pensando"
        "pensando_1": "Déjeme ver...",
        "pensando_2": "Mmm, déjeme validarlo...",
        "pensando_3": "Un momento...",
        "pensando_4": "Déjeme revisar...",
        "pensando_5": "Mmm...",
        "pensando_6": "Déjeme checar...",
        "pensando_7": "Permítame un segundo...",
        "pensando_8": "Déjame verificar...",

        # Saludos
        "saludo_inicial": "Hola, buen dia",
        "saludo_inicial_encargado": "Hola, buen dia",

        # Despedidas
        "despedida_1": "Muchas gracias por su tiempo. Que tenga excelente tarde. Hasta pronto.",
        "despedida_2": "Perfecto. En las próximas dos horas le llega el catálogo completo por WhatsApp. Muchas gracias por su tiempo. Que tenga excelente tarde.",
        "despedida_objecion": "Perfecto, comprendo que ya trabajan con un proveedor fijo. Le agradezco mucho su tiempo y por la información. Si en el futuro necesitan comparar precios o buscan un proveedor adicional, con gusto pueden contactarnos. Que tenga excelente día.",

        # Segunda parte del saludo
        "segunda_parte_saludo": "Me comunico de la marca nioval, más que nada quería brindar informacion de nuestros productos ferreteros, ¿Se encontrara el encargado o encargada de compras?",
    }

    # Cargar respuestas_cache.json
    cache_file = Path("audio_cache/respuestas_cache.json")
    if cache_file.exists():
        with open(cache_file, 'r', encoding='utf-8') as f:
            respuestas_cache = json.load(f)
        for categoria, datos in respuestas_cache.items():
            cache_key = f"respuesta_cache_{categoria}"
            frases_comunes[cache_key] = datos["respuesta"]

    return frases_comunes


def generar_nombre_archivo(key, texto):
    """Genera nombre de archivo normalizado igual que el servidor."""
    # Hash de 12 chars del texto completo
    text_hash = hashlib.md5(texto.encode()).hexdigest()[:12]
    # Normalizar key
    safe_key = key.replace(" ", "_").replace("/", "_")[:80]
    return f"{safe_key}_{text_hash}.mp3"


def generar_cache_para_voz(nombre_voz):
    """Genera todo el cache de audios para una voz específica."""

    if nombre_voz not in VOCES:
        print(f"Voz '{nombre_voz}' no encontrada. Disponibles: {list(VOCES.keys())}")
        return False

    if nombre_voz == "bruce_w":
        print("La voz 'bruce_w' ya tiene cache en audio_cache/. No se regenera.")
        return False

    voz = VOCES[nombre_voz]
    voice_id = voz["voice_id"]
    cache_dir = Path(voz["cache_dir"])

    print(f"\n{'='*80}")
    print(f"GENERANDO CACHE PARA: {voz['nombre']}")
    print(f"Voice ID: {voice_id}")
    print(f"Directorio: {cache_dir}")
    print(f"{'='*80}\n")

    # Crear directorio
    cache_dir.mkdir(exist_ok=True)

    # Copiar respuestas_cache.json al nuevo directorio
    src_cache = Path("audio_cache/respuestas_cache.json")
    if src_cache.exists():
        import shutil
        shutil.copy2(src_cache, cache_dir / "respuestas_cache.json")
        print(f"Copiado respuestas_cache.json al directorio")

    # Obtener frases
    frases = obtener_frases_a_generar()

    # Cargar metadata existente (para no regenerar lo que ya existe)
    metadata_file = cache_dir / "metadata.json"
    metadata = {}
    if metadata_file.exists():
        with open(metadata_file, 'r', encoding='utf-8') as f:
            metadata = json.load(f)

    # Inicializar ElevenLabs
    api_key = os.getenv("ELEVENLABS_API_KEY")
    if not api_key:
        print("ELEVENLABS_API_KEY no encontrada en .env")
        return False

    from elevenlabs.client import ElevenLabs
    from elevenlabs import VoiceSettings

    client = ElevenLabs(api_key=api_key)
    voice_settings = VoiceSettings(
        stability=0.65,
        similarity_boost=0.80,
        style=0.20,
        use_speaker_boost=True
    )

    # Verificar créditos
    try:
        user = client.user.get()
        chars_restantes = user.subscription.character_limit - user.subscription.character_count
        chars_necesarios = sum(len(t) for t in frases.values())
        print(f"Créditos disponibles: {chars_restantes:,} caracteres")
        print(f"Caracteres necesarios: {chars_necesarios:,}")

        if chars_necesarios > chars_restantes:
            print(f"NO hay suficientes créditos! Faltan {chars_necesarios - chars_restantes:,}")
            return False
        print(f"OK - Suficientes créditos\n")
    except Exception as e:
        print(f"No se pudo verificar créditos: {e}")
        print("Continuando de todos modos...\n")

    # Generar audios
    generados = 0
    omitidos = 0
    errores = 0
    total = len(frases)

    for idx, (key, texto) in enumerate(frases.items(), 1):
        filename = generar_nombre_archivo(key, texto)
        filepath = cache_dir / filename

        # Verificar si ya existe
        if key in metadata and (cache_dir / metadata[key]).exists():
            print(f"  [{idx}/{total}] Omitido (ya existe): {key}")
            omitidos += 1
            continue

        try:
            print(f"  [{idx}/{total}] Generando: {key} ({len(texto)} chars)")

            audio_generator = client.text_to_speech.convert(
                text=texto,
                voice_id=voice_id,
                model_id="eleven_multilingual_v2",
                output_format="mp3_44100_128",
                voice_settings=voice_settings,
                optimize_streaming_latency=4
            )

            audio_data = b"".join(audio_generator)

            with open(filepath, 'wb') as f:
                f.write(audio_data)

            metadata[key] = filename
            generados += 1

            # Rate limiting
            if idx % 10 == 0:
                print(f"  ... Pausa de 1s (rate limit) ...")
                time.sleep(1)

        except Exception as e:
            print(f"  ERROR en {key}: {e}")
            errores += 1

    # Guardar metadata
    with open(metadata_file, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)

    # Guardar info de la voz
    info_file = cache_dir / "voz_info.json"
    with open(info_file, 'w', encoding='utf-8') as f:
        json.dump({
            "voice_id": voice_id,
            "nombre": voz["nombre"],
            "generado": datetime.now().isoformat(),
            "total_audios": generados + omitidos,
            "modelo": "eleven_multilingual_v2"
        }, f, indent=2, ensure_ascii=False)

    print(f"\n{'='*80}")
    print(f"RESULTADO PARA: {voz['nombre']}")
    print(f"  Generados: {generados}")
    print(f"  Omitidos (ya existían): {omitidos}")
    print(f"  Errores: {errores}")
    print(f"  Total en cache: {len(metadata)} audios")
    print(f"  Directorio: {cache_dir}")
    print(f"{'='*80}\n")

    return True


# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso:")
        print("  python generar_cache_multivoz.py diana_sanchez")
        print("  python generar_cache_multivoz.py mauricio")
        print("  python generar_cache_multivoz.py todas")
        print("\nVoces disponibles:")
        for key, voz in VOCES.items():
            if key != "bruce_w":
                print(f"  {key}: {voz['nombre']} ({voz['voice_id']})")
        sys.exit(1)

    voz_arg = sys.argv[1].lower()

    if voz_arg == "todas":
        for nombre in VOCES:
            if nombre != "bruce_w":
                generar_cache_para_voz(nombre)
    elif voz_arg in VOCES:
        generar_cache_para_voz(voz_arg)
    else:
        print(f"Voz '{voz_arg}' no reconocida.")
        print(f"Opciones: {', '.join(k for k in VOCES if k != 'bruce_w')}, todas")
        sys.exit(1)
