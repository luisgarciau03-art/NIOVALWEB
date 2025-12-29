# -*- coding: utf-8 -*-
"""
Script para descargar todos los audios del cache de Railway a local
"""
import os
import sys
import requests
from dotenv import load_dotenv

# Configurar encoding UTF-8 para Windows
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

load_dotenv()

# URL del servidor en Railway
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "https://nioval-webhook-server-production.up.railway.app")

# Directorio local donde guardar
LOCAL_CACHE_DIR = "audio_cache"

def descargar_audios():
    """Descarga todos los audios del cache de Railway"""

    print("\n" + "=" * 60)
    print("📥 DESCARGANDO AUDIOS DE RAILWAY")
    print("=" * 60 + "\n")

    # Crear directorio si no existe
    if not os.path.exists(LOCAL_CACHE_DIR):
        os.makedirs(LOCAL_CACHE_DIR)
        print(f"📁 Directorio creado: {os.path.abspath(LOCAL_CACHE_DIR)}\n")

    # 1. Listar audios disponibles
    print(f"🔍 Consultando audios disponibles en Railway...")
    try:
        response = requests.get(f"{WEBHOOK_URL}/listar-audios", timeout=10)
        response.raise_for_status()
        data = response.json()

        total = data.get('total', 0)
        archivos = data.get('archivos', [])

        print(f"✅ Encontrados {total} audios en Railway\n")

        if total == 0:
            print("⚠️  No hay audios para descargar")
            return

    except Exception as e:
        print(f"❌ Error al listar audios: {e}")
        return

    # 2. Descargar cada audio
    descargados = 0
    errores = 0

    for i, archivo in enumerate(archivos, 1):
        nombre = archivo['nombre']
        tamano_kb = archivo['tamaño_kb']

        print(f"📥 [{i}/{total}] Descargando: {nombre} ({tamano_kb} KB)")

        try:
            # Descargar archivo
            url_descarga = f"{WEBHOOK_URL}{archivo['url_descarga']}"
            response = requests.get(url_descarga, timeout=30)
            response.raise_for_status()

            # Guardar en disco
            filepath = os.path.join(LOCAL_CACHE_DIR, nombre)
            with open(filepath, 'wb') as f:
                f.write(response.content)

            print(f"   ✅ Guardado en: {filepath}")
            descargados += 1

        except Exception as e:
            print(f"   ❌ Error: {e}")
            errores += 1

        print()

    # 3. Resumen
    print("=" * 60)
    print("📊 RESUMEN DE DESCARGA")
    print("=" * 60)
    print(f"Total disponibles: {total}")
    print(f"✅ Descargados: {descargados}")
    print(f"❌ Errores: {errores}")
    print(f"📁 Ubicación: {os.path.abspath(LOCAL_CACHE_DIR)}")
    print("=" * 60 + "\n")

    if descargados > 0:
        print("✅ Descarga completada. Puedes escuchar los audios en:")
        print(f"   {os.path.abspath(LOCAL_CACHE_DIR)}\n")


if __name__ == "__main__":
    try:
        descargar_audios()
    except KeyboardInterrupt:
        print("\n\n⚠️  Descarga cancelada por el usuario")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
