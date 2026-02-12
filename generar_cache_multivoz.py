#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Generador de Cache Multi-Voz para Bruce W Agent
Genera audios pre-cacheados para múltiples voces SIN tocar el cache actual.

Uso:
    python generar_cache_multivoz.py diana_sanchez          # Solo frases base (25)
    python generar_cache_multivoz.py mauricio               # Solo frases base (25)
    python generar_cache_multivoz.py todas                  # Ambas voces, frases base
    python generar_cache_multivoz.py diana_sanchez --full   # COMPLETO desde Railway (1000+)
    python generar_cache_multivoz.py todas --full           # COMPLETO ambas voces
"""

import os
import sys
import json
import time
import hashlib
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

RAILWAY_URL = "https://nioval-webhook-server-production.up.railway.app"

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
# FRASES BASE (pre_generar_audios_cache del servidor)
# ============================================================================

def obtener_frases_base():
    """Retorna las frases base hardcodeadas (25 aprox)."""
    frases_comunes = {
        "error": "Lo siento, hubo un error. Le llamaremos más tarde.",
        "confirmacion_presencia": "Sí, estoy aquí.",
        "pensando_1": "Déjeme ver...",
        "pensando_2": "Mmm, déjeme validarlo...",
        "pensando_3": "Un momento...",
        "pensando_4": "Déjeme revisar...",
        "pensando_5": "Mmm...",
        "pensando_6": "Déjeme checar...",
        "pensando_7": "Permítame un segundo...",
        "pensando_8": "Déjame verificar...",
        "saludo_inicial": "Hola, buen dia",
        "saludo_inicial_encargado": "Hola, buen dia",
        "despedida_1": "Muchas gracias por su tiempo. Que tenga excelente tarde. Hasta pronto.",
        "despedida_2": "Perfecto. En las próximas dos horas le llega el catálogo completo por WhatsApp. Muchas gracias por su tiempo. Que tenga excelente tarde.",
        "despedida_objecion": "Perfecto, comprendo que ya trabajan con un proveedor fijo. Le agradezco mucho su tiempo y por la información. Si en el futuro necesitan comparar precios o buscan un proveedor adicional, con gusto pueden contactarnos. Que tenga excelente día.",
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


def obtener_frases_completas_railway():
    """Descarga TODAS las frases con audio desde Railway (1000+)."""
    import requests

    print(f"Descargando frases completas desde Railway...")
    print(f"URL: {RAILWAY_URL}/exportar-cache-frases\n")

    try:
        resp = requests.get(f"{RAILWAY_URL}/exportar-cache-frases", timeout=60)
        if resp.status_code != 200:
            print(f"Error HTTP {resp.status_code}: {resp.text[:200]}")
            return None

        data = resp.json()
        frases = data.get("frases", {})
        total = data.get("total", 0)

        print(f"Descargadas {total} frases desde Railway")

        # Filtrar frases vacías o muy cortas
        frases_validas = {}
        for key, texto in frases.items():
            if texto and len(texto.strip()) > 2:
                frases_validas[key] = texto.strip()

        print(f"Frases válidas: {len(frases_validas)}")

        # Guardar backup local
        backup_file = Path("frases_cache_railway_export.json")
        with open(backup_file, 'w', encoding='utf-8') as f:
            json.dump(frases_validas, f, indent=2, ensure_ascii=False)
        print(f"Backup guardado en: {backup_file}\n")

        return frases_validas

    except Exception as e:
        print(f"Error descargando frases: {e}")

        # Intentar cargar backup local
        backup_file = Path("frases_cache_railway_export.json")
        if backup_file.exists():
            print(f"Usando backup local: {backup_file}")
            with open(backup_file, 'r', encoding='utf-8') as f:
                return json.load(f)

        return None


def generar_nombre_archivo(key, texto):
    """Genera nombre de archivo normalizado igual que el servidor."""
    text_hash = hashlib.md5(texto.encode()).hexdigest()[:12]
    safe_key = key.replace(" ", "_").replace("/", "_")[:80]
    return f"{safe_key}_{text_hash}.mp3"


def estimar_creditos(frases):
    """Estima caracteres necesarios para generar las frases."""
    total_chars = sum(len(t) for t in frases.values())
    return total_chars


def generar_cache_para_voz(nombre_voz, modo_completo=False):
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

    # Obtener frases
    if modo_completo:
        print(f"MODO COMPLETO: Descargando todas las frases desde Railway...")
        frases = obtener_frases_completas_railway()
        if not frases:
            print("No se pudieron obtener frases de Railway. Usando frases base.")
            frases = obtener_frases_base()
    else:
        frases = obtener_frases_base()

    print(f"\n{'='*80}")
    print(f"GENERANDO CACHE PARA: {voz['nombre']}")
    print(f"Voice ID: {voice_id}")
    print(f"Directorio: {cache_dir}")
    print(f"Total frases: {len(frases)}")
    print(f"Caracteres: {estimar_creditos(frases):,}")
    print(f"Modo: {'COMPLETO (Railway)' if modo_completo else 'BASE (25 frases)'}")
    print(f"{'='*80}\n")

    # Crear directorio
    cache_dir.mkdir(exist_ok=True)

    # Copiar respuestas_cache.json al nuevo directorio
    src_cache = Path("audio_cache/respuestas_cache.json")
    if src_cache.exists():
        import shutil
        shutil.copy2(src_cache, cache_dir / "respuestas_cache.json")
        print(f"Copiado respuestas_cache.json al directorio")

    # Cargar metadata existente (para no regenerar lo que ya existe)
    metadata_file = cache_dir / "metadata.json"
    metadata = {}
    if metadata_file.exists():
        with open(metadata_file, 'r', encoding='utf-8') as f:
            metadata = json.load(f)

    # Contar cuántas ya existen
    ya_existen = sum(1 for k in frases if k in metadata and (cache_dir / metadata[k]).exists())
    por_generar = len(frases) - ya_existen
    chars_por_generar = sum(len(t) for k, t in frases.items()
                           if k not in metadata or not (cache_dir / metadata.get(k, "")).exists())

    print(f"\nYa existen: {ya_existen} audios")
    print(f"Por generar: {por_generar} audios")
    print(f"Caracteres por generar: {chars_por_generar:,}")

    if por_generar == 0:
        print("Todos los audios ya existen. Nada que generar.")
        return True

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
        print(f"\nCreditos disponibles: {chars_restantes:,} caracteres")
        print(f"Caracteres necesarios: {chars_por_generar:,}")
        if chars_por_generar > chars_restantes:
            print(f"ADVERTENCIA: Faltan {chars_por_generar - chars_restantes:,} caracteres!")
            respuesta = input("Continuar de todos modos? (s/n): ").strip().lower()
            if respuesta != 's':
                return False
        else:
            print(f"OK - Suficientes creditos\n")
    except Exception as e:
        print(f"No se pudo verificar creditos: {e}")
        print("Continuando...\n")

    # Generar audios
    generados = 0
    omitidos = 0
    errores = 0
    total = len(frases)
    inicio_total = time.time()

    for idx, (key, texto) in enumerate(frases.items(), 1):
        filename = generar_nombre_archivo(key, texto)

        # Verificar si ya existe
        if key in metadata and (cache_dir / metadata[key]).exists():
            omitidos += 1
            if idx % 100 == 0:
                print(f"  [{idx}/{total}] ... {omitidos} omitidos, {generados} generados")
            continue

        filepath = cache_dir / filename

        try:
            if idx <= 5 or idx % 50 == 0 or idx == total:
                print(f"  [{idx}/{total}] Generando: {key[:50]} ({len(texto)} chars)")

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

            # Rate limiting - pausa cada 10 audios
            if generados % 10 == 0:
                time.sleep(1)

            # Guardar metadata periódicamente (cada 50 audios)
            if generados % 50 == 0:
                with open(metadata_file, 'w', encoding='utf-8') as f:
                    json.dump(metadata, f, indent=2, ensure_ascii=False)
                elapsed = time.time() - inicio_total
                rate = generados / elapsed * 60  # audios por minuto
                remaining = (por_generar - generados) / rate if rate > 0 else 0
                print(f"  >> Progreso: {generados}/{por_generar} ({rate:.0f}/min, ~{remaining:.0f}min restantes)")

        except Exception as e:
            print(f"  ERROR en {key[:40]}: {e}")
            errores += 1
            if errores > 10:
                print("Demasiados errores. Guardando progreso y saliendo.")
                break
            time.sleep(2)  # Pausa extra en error

    # Guardar metadata final
    with open(metadata_file, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)

    # Guardar info de la voz
    info_file = cache_dir / "voz_info.json"
    with open(info_file, 'w', encoding='utf-8') as f:
        json.dump({
            "voice_id": voice_id,
            "nombre": voz["nombre"],
            "generado": datetime.now().isoformat(),
            "total_audios": len(metadata),
            "modelo": "eleven_multilingual_v2"
        }, f, indent=2, ensure_ascii=False)

    elapsed = time.time() - inicio_total

    print(f"\n{'='*80}")
    print(f"RESULTADO PARA: {voz['nombre']}")
    print(f"  Generados: {generados}")
    print(f"  Omitidos (ya existian): {omitidos}")
    print(f"  Errores: {errores}")
    print(f"  Total en cache: {len(metadata)} audios")
    print(f"  Tiempo: {elapsed/60:.1f} minutos")
    print(f"  Directorio: {cache_dir}")
    print(f"{'='*80}\n")

    return True


# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso:")
        print("  python generar_cache_multivoz.py diana_sanchez          # Frases base (25)")
        print("  python generar_cache_multivoz.py mauricio               # Frases base (25)")
        print("  python generar_cache_multivoz.py todas                  # Ambas, base")
        print("  python generar_cache_multivoz.py diana_sanchez --full   # COMPLETO (1000+)")
        print("  python generar_cache_multivoz.py todas --full           # COMPLETO ambas")
        print("\nVoces disponibles:")
        for key, voz in VOCES.items():
            if key != "bruce_w":
                print(f"  {key}: {voz['nombre']} ({voz['voice_id']})")
        sys.exit(1)

    voz_arg = sys.argv[1].lower()
    modo_completo = "--full" in sys.argv

    if modo_completo:
        print("\n*** MODO COMPLETO: Descargara 1000+ frases desde Railway ***\n")

    if voz_arg == "todas":
        for nombre in VOCES:
            if nombre != "bruce_w":
                generar_cache_para_voz(nombre, modo_completo=modo_completo)
    elif voz_arg in VOCES:
        generar_cache_para_voz(voz_arg, modo_completo=modo_completo)
    else:
        print(f"Voz '{voz_arg}' no reconocida.")
        print(f"Opciones: {', '.join(k for k in VOCES if k != 'bruce_w')}, todas")
        sys.exit(1)
