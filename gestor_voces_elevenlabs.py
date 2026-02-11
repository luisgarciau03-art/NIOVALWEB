#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gestor de Voces ElevenLabs con Respaldos
Permite cambiar la voz de Bruce y crear respaldos para volver atrás
"""

import os
import json
import shutil
from datetime import datetime
from pathlib import Path
from elevenlabs.client import ElevenLabs
from elevenlabs import VoiceSettings
import time

# ============================================================================
# CONFIGURACIÓN
# ============================================================================

AUDIO_CACHE_DIR = Path("audio_cache")
BACKUPS_DIR = Path("audio_cache_backups")
CACHE_AUDIOS_FILE = AUDIO_CACHE_DIR / "cache_audios.json"
CACHE_FRASES_FILE = AUDIO_CACHE_DIR / "cache_frases_frecuentes.json"

# Voces disponibles en ElevenLabs
VOCES_DISPONIBLES = {
    "bruce_masculino": {
        "voice_id": "7uSWXMmzGnsyxZwYFfmK",
        "nombre": "Bruce - Voz Masculina Original",
        "descripcion": "Voz masculina profesional mexicana"
    },
    "domi_femenino": {
        "voice_id": "AZnzlk1XvdvUeBnXmlld",
        "nombre": "Domi - Voz Femenina",
        "descripcion": "Voz femenina profesional y amigable"
    },
    "jessica_femenino": {
        "voice_id": "cgSgspJ2msm6clMCkdW9",
        "nombre": "Jessica - Voz Femenina Profesional",
        "descripcion": "Voz femenina clara y profesional"
    },
    "matilda_femenino": {
        "voice_id": "XrExE9yKIg1WjnnlVkGX",
        "nombre": "Matilda - Voz Femenina Cálida",
        "descripcion": "Voz femenina cálida y amigable"
    }
}

# ============================================================================
# FUNCIONES DE RESPALDO
# ============================================================================

def crear_respaldo(nombre_respaldo=None):
    """
    Crea un respaldo completo del cache de audios actual

    Args:
        nombre_respaldo: Nombre del respaldo (default: timestamp)

    Returns:
        Path al directorio del respaldo
    """
    if nombre_respaldo is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        nombre_respaldo = f"backup_{timestamp}"

    # Crear directorio de respaldos si no existe
    BACKUPS_DIR.mkdir(exist_ok=True)

    # Path del respaldo
    backup_path = BACKUPS_DIR / nombre_respaldo

    if backup_path.exists():
        print(f"⚠️  El respaldo '{nombre_respaldo}' ya existe. Sobrescribiendo...")
        shutil.rmtree(backup_path)

    # Copiar todo el directorio audio_cache
    print(f"📦 Creando respaldo en: {backup_path}")
    shutil.copytree(AUDIO_CACHE_DIR, backup_path)

    # Guardar metadata del respaldo
    metadata = {
        "fecha_creacion": datetime.now().isoformat(),
        "nombre": nombre_respaldo,
        "archivos_respaldados": len(list(backup_path.glob("*.mp3"))),
        "tamano_mb": sum(f.stat().st_size for f in backup_path.glob("*.mp3")) / (1024 * 1024)
    }

    # Intentar detectar la voz del respaldo
    if CACHE_AUDIOS_FILE.exists():
        try:
            with open(CACHE_AUDIOS_FILE, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)
                if "voice_id" in cache_data:
                    metadata["voice_id"] = cache_data["voice_id"]
                    # Buscar nombre de la voz
                    for key, voz in VOCES_DISPONIBLES.items():
                        if voz["voice_id"] == metadata["voice_id"]:
                            metadata["voz_nombre"] = voz["nombre"]
                            break
        except:
            pass

    with open(backup_path / "metadata.json", 'w', encoding='utf-8') as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)

    print(f"✅ Respaldo creado exitosamente:")
    print(f"   - Archivos: {metadata['archivos_respaldados']} MP3")
    print(f"   - Tamaño: {metadata['tamano_mb']:.2f} MB")
    if "voz_nombre" in metadata:
        print(f"   - Voz: {metadata['voz_nombre']}")

    return backup_path


def listar_respaldos():
    """Lista todos los respaldos disponibles"""
    if not BACKUPS_DIR.exists() or not list(BACKUPS_DIR.iterdir()):
        print("📭 No hay respaldos disponibles")
        return []

    respaldos = []
    print("\n" + "="*80)
    print("📦 RESPALDOS DISPONIBLES")
    print("="*80)

    for backup_dir in sorted(BACKUPS_DIR.iterdir(), reverse=True):
        if not backup_dir.is_dir():
            continue

        metadata_file = backup_dir / "metadata.json"
        if metadata_file.exists():
            with open(metadata_file, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
        else:
            # Metadata básica si no existe archivo
            metadata = {
                "nombre": backup_dir.name,
                "archivos_respaldados": len(list(backup_dir.glob("*.mp3"))),
                "tamano_mb": sum(f.stat().st_size for f in backup_dir.glob("*.mp3")) / (1024 * 1024)
            }

        respaldos.append((backup_dir, metadata))

        print(f"\n{len(respaldos)}. {metadata['nombre']}")
        if "fecha_creacion" in metadata:
            fecha = datetime.fromisoformat(metadata["fecha_creacion"])
            print(f"   Fecha: {fecha.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"   Archivos: {metadata['archivos_respaldados']} MP3")
        print(f"   Tamaño: {metadata['tamano_mb']:.2f} MB")
        if "voz_nombre" in metadata:
            print(f"   Voz: {metadata['voz_nombre']}")

    print("="*80 + "\n")
    return respaldos


def restaurar_respaldo(nombre_respaldo):
    """
    Restaura un respaldo al cache actual

    Args:
        nombre_respaldo: Nombre del respaldo a restaurar
    """
    backup_path = BACKUPS_DIR / nombre_respaldo

    if not backup_path.exists():
        print(f"❌ El respaldo '{nombre_respaldo}' no existe")
        return False

    # Crear respaldo del estado actual antes de restaurar
    print("📦 Creando respaldo del estado actual antes de restaurar...")
    crear_respaldo(f"auto_backup_antes_restaurar_{datetime.now().strftime('%Y%m%d_%H%M%S')}")

    # Limpiar cache actual
    print(f"🧹 Limpiando cache actual...")
    if AUDIO_CACHE_DIR.exists():
        shutil.rmtree(AUDIO_CACHE_DIR)

    # Restaurar desde respaldo
    print(f"♻️  Restaurando respaldo '{nombre_respaldo}'...")
    shutil.copytree(backup_path, AUDIO_CACHE_DIR)

    # Leer metadata del respaldo
    metadata_file = backup_path / "metadata.json"
    if metadata_file.exists():
        with open(metadata_file, 'r', encoding='utf-8') as f:
            metadata = json.load(f)

        print(f"✅ Respaldo restaurado exitosamente:")
        print(f"   - Archivos: {metadata['archivos_respaldados']} MP3")
        print(f"   - Tamaño: {metadata['tamano_mb']:.2f} MB")
        if "voz_nombre" in metadata:
            print(f"   - Voz: {metadata['voz_nombre']}")
    else:
        print(f"✅ Respaldo restaurado exitosamente")

    return True


# ============================================================================
# FUNCIONES DE REGENERACIÓN
# ============================================================================

def listar_voces():
    """Lista todas las voces disponibles"""
    print("\n" + "="*80)
    print("🎙️  VOCES DISPONIBLES EN ELEVENLABS")
    print("="*80)

    for idx, (key, voz) in enumerate(VOCES_DISPONIBLES.items(), 1):
        print(f"\n{idx}. {voz['nombre']}")
        print(f"   ID: {voz['voice_id']}")
        print(f"   Descripción: {voz['descripcion']}")

    print("="*80 + "\n")


def regenerar_cache_con_nueva_voz(voice_id, crear_backup=True):
    """
    Regenera todo el cache de audios con una nueva voz

    Args:
        voice_id: ID de la voz de ElevenLabs
        crear_backup: Si True, crea respaldo antes de regenerar

    Returns:
        Número de audios regenerados
    """
    # Crear respaldo del cache actual
    if crear_backup:
        print("📦 Creando respaldo del cache actual...")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        crear_respaldo(f"backup_antes_cambio_voz_{timestamp}")

    # Cargar frases del cache
    if not CACHE_AUDIOS_FILE.exists():
        print(f"❌ No se encontró el archivo {CACHE_AUDIOS_FILE}")
        return 0

    with open(CACHE_AUDIOS_FILE, 'r', encoding='utf-8') as f:
        cache_audios = json.load(f)

    frases = cache_audios.get("audios", {})

    if not frases:
        print("❌ No hay frases en el cache para regenerar")
        return 0

    print(f"\n🔄 Regenerando {len(frases)} audios con nueva voz...")
    print(f"   Voice ID: {voice_id}")

    # Buscar nombre de la voz
    voz_nombre = "Desconocida"
    for key, voz in VOCES_DISPONIBLES.items():
        if voz["voice_id"] == voice_id:
            voz_nombre = voz["nombre"]
            break
    print(f"   Voz: {voz_nombre}\n")

    # Inicializar cliente ElevenLabs
    elevenlabs_api_key = os.getenv("ELEVENLABS_API_KEY")
    if not elevenlabs_api_key:
        print("❌ No se encontró ELEVENLABS_API_KEY en variables de entorno")
        return 0

    client = ElevenLabs(api_key=elevenlabs_api_key)

    # Configuración de voz
    voice_settings = VoiceSettings(
        stability=0.65,
        similarity_boost=0.80,
        style=0.20,
        use_speaker_boost=True
    )

    # Regenerar cada audio
    regenerados = 0
    errores = 0

    for idx, (texto, info) in enumerate(frases.items(), 1):
        try:
            print(f"[{idx}/{len(frases)}] Regenerando: {texto[:60]}{'...' if len(texto) > 60 else ''}")

            # Generar audio con nueva voz
            audio_generator = client.text_to_speech.convert(
                text=texto,
                voice_id=voice_id,
                model_id="eleven_multilingual_v2",
                voice_settings=voice_settings,
                optimize_streaming_latency=4
            )

            # Recolectar chunks
            audio_data = b"".join(audio_generator)

            # Guardar audio
            audio_path = AUDIO_CACHE_DIR / info["filename"]
            with open(audio_path, 'wb') as f:
                f.write(audio_data)

            regenerados += 1

            # Rate limiting (evitar sobrepasar límites de API)
            if idx % 10 == 0:
                time.sleep(1)

        except Exception as e:
            print(f"   ❌ Error: {str(e)}")
            errores += 1

    # Actualizar metadata del cache
    cache_audios["voice_id"] = voice_id
    cache_audios["ultima_actualizacion"] = datetime.now().isoformat()
    cache_audios["voz_nombre"] = voz_nombre

    with open(CACHE_AUDIOS_FILE, 'w', encoding='utf-8') as f:
        json.dump(cache_audios, f, indent=2, ensure_ascii=False)

    print(f"\n{'='*80}")
    print(f"✅ Regeneración completada:")
    print(f"   - Audios regenerados: {regenerados}")
    if errores > 0:
        print(f"   - Errores: {errores}")
    print(f"   - Nueva voz: {voz_nombre}")
    print(f"{'='*80}\n")

    return regenerados


# ============================================================================
# INTERFAZ DE LÍNEA DE COMANDOS
# ============================================================================

def menu_principal():
    """Menú interactivo principal"""
    while True:
        print("\n" + "="*80)
        print("🎙️  GESTOR DE VOCES ELEVENLABS - BRUCE W")
        print("="*80)
        print("\n1. Listar voces disponibles")
        print("2. Ver respaldos existentes")
        print("3. Crear respaldo del cache actual")
        print("4. Regenerar cache con nueva voz")
        print("5. Restaurar respaldo")
        print("6. Salir")
        print("\n" + "="*80)

        opcion = input("\nSelecciona una opción (1-6): ").strip()

        if opcion == "1":
            listar_voces()

        elif opcion == "2":
            listar_respaldos()

        elif opcion == "3":
            nombre = input("\nNombre del respaldo (Enter para auto): ").strip()
            if not nombre:
                nombre = None
            crear_respaldo(nombre)

        elif opcion == "4":
            listar_voces()
            voice_key = input("\nSelecciona la voz (bruce_masculino/domi_femenino/jessica_femenino/matilda_femenino): ").strip()

            if voice_key not in VOCES_DISPONIBLES:
                print("❌ Voz no válida")
                continue

            voice_id = VOCES_DISPONIBLES[voice_key]["voice_id"]
            confirmar = input(f"\n⚠️  ¿Confirmas regenerar TODO el cache con {VOCES_DISPONIBLES[voice_key]['nombre']}? (si/no): ").strip().lower()

            if confirmar == "si":
                regenerar_cache_con_nueva_voz(voice_id, crear_backup=True)
            else:
                print("❌ Operación cancelada")

        elif opcion == "5":
            respaldos = listar_respaldos()
            if not respaldos:
                continue

            idx = input("\nNúmero del respaldo a restaurar (0 para cancelar): ").strip()
            try:
                idx = int(idx)
                if idx == 0:
                    print("❌ Operación cancelada")
                    continue

                if 1 <= idx <= len(respaldos):
                    backup_path, metadata = respaldos[idx - 1]
                    confirmar = input(f"\n⚠️  ¿Confirmas restaurar '{metadata['nombre']}'? (si/no): ").strip().lower()

                    if confirmar == "si":
                        restaurar_respaldo(metadata["nombre"])
                    else:
                        print("❌ Operación cancelada")
                else:
                    print("❌ Número inválido")
            except ValueError:
                print("❌ Entrada inválida")

        elif opcion == "6":
            print("\n👋 ¡Hasta luego!")
            break

        else:
            print("❌ Opción no válida")


if __name__ == "__main__":
    menu_principal()
