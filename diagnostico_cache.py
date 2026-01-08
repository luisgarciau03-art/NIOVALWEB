# -*- coding: utf-8 -*-
"""
Script de diagnóstico para verificar el estado del caché en Railway
"""
import requests

RAILWAY_URL = "https://nioval-webhook-server-production.up.railway.app"

print("\n" + "=" * 70)
print("DIAGNOSTICO DE CACHE - BRUCE W")
print("=" * 70 + "\n")

# 1. Verificar categorías de respuestas cacheadas
print("1. Verificando categorias de respuestas cacheadas...")
try:
    response = requests.get(f"{RAILWAY_URL}/cache-manager", timeout=10)
    if response.status_code == 200:
        # Buscar cuántas categorías hay en el HTML
        html = response.text
        count = html.count('<div class="cache-card">')
        print(f"   Categorias encontradas: {count}")

        if count == 4:
            print("   PROBLEMA: Solo 4 categorias (deberian ser 9+)")
            print("   - El archivo seed_data/respuestas_cache.json NO se cargo")
        elif count >= 9:
            print("   OK: 9+ categorias cargadas correctamente")
    else:
        print(f"   ERROR: Status {response.status_code}")
except Exception as e:
    print(f"   ERROR: {e}")

print()

# 2. Verificar estadísticas de caché de respuestas
print("2. Verificando estadisticas de cache de respuestas...")
try:
    response = requests.get(f"{RAILWAY_URL}/stats", timeout=10)
    if response.status_code == 200:
        html = response.text

        # Buscar tasa de aciertos
        import re
        match = re.search(r'Tasa de aciertos:.*?(\d+\.\d+)%', html)
        if match:
            hit_rate = float(match.group(1))
            print(f"   Tasa de aciertos del cache: {hit_rate}%")

            if hit_rate < 10:
                print("   PROBLEMA: Tasa muy baja (<10%)")
                print("   - Las respuestas NO se estan cacheando")
            elif hit_rate > 50:
                print("   OK: Cache funcionando bien (>50%)")

        # Buscar audios en caché
        match = re.search(r'Audios en cache:.*?(\d+)', html)
        if match:
            audio_count = int(match.group(1))
            print(f"   Audios pre-generados: {audio_count}")

            if audio_count < 15:
                print("   PROBLEMA: Pocos audios (<15)")
                print("   - Los audios de respuestas NO se pre-generaron")
            else:
                print("   OK: Audios pre-generados correctamente")
    else:
        print(f"   ERROR: Status {response.status_code}")
except Exception as e:
    print(f"   ERROR: {e}")

print()

# 3. Verificar volumen persistente
print("3. Verificando volumen persistente...")
try:
    response = requests.get(f"{RAILWAY_URL}/diagnostico-persistencia", timeout=10)
    if response.status_code == 200:
        result = response.json()
        print(f"   Directorio cache: {result.get('cache_dir')}")
        print(f"   Directorio existe: {result.get('cache_dir_exists')}")
        print(f"   Archivos en cache: {result.get('cache_files_count', 0)}")

        files = result.get('cache_files', [])
        if 'respuestas_cache.json' in files:
            print("   OK: respuestas_cache.json encontrado en Volume")
        else:
            print("   PROBLEMA: respuestas_cache.json NO encontrado")
            print("   - El archivo seed NO se copio al Volume")
    else:
        print(f"   ERROR: Status {response.status_code}")
except Exception as e:
    print(f"   ERROR: {e}")

print()
print("=" * 70)
print("RESUMEN:")
print("Si ves PROBLEMA arriba, el cache NO esta funcionando correctamente")
print("Posibles soluciones:")
print("  1. Verificar que seed_data/respuestas_cache.json este en el repo")
print("  2. Re-deployar Railway para forzar carga del seed")
print("  3. Configurar OPENAI_API_KEY en Railway (para Whisper)")
print("=" * 70 + "\n")
