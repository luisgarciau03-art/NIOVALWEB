#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para importar el caché sugerido del análisis del LOG
al sistema de respuestas de Bruce
"""

import json
import os

# Directorio de caché
CACHE_DIR = "audio_cache"

# Cargar caché sugerido del análisis
with open('cache_sugerido_del_log.json', 'r', encoding='utf-8') as f:
    cache_sugerido = json.load(f)

# Crear directorio si no existe
if not os.path.exists(CACHE_DIR):
    os.makedirs(CACHE_DIR)
    print(f" Directorio creado: {CACHE_DIR}")

# Cargar caché existente (si existe)
cache_file = os.path.join(CACHE_DIR, "respuestas_cache.json")
if os.path.exists(cache_file):
    with open(cache_file, 'r', encoding='utf-8') as f:
        cache_existente = json.load(f)
    print(f" Caché existente cargado: {len(cache_existente)} categorías")
else:
    cache_existente = {}
    print(" No hay caché existente, creando nuevo")

# Merge: agregar solo las categorías nuevas
categorias_agregadas = 0
categorias_actualizadas = 0

for categoria, datos in cache_sugerido.items():
    if categoria in cache_existente:
        # Actualizar patrones (merge)
        patrones_existentes = set(cache_existente[categoria]["patrones"])
        patrones_nuevos = set(datos["patrones"])
        patrones_merged = list(patrones_existentes | patrones_nuevos)

        cache_existente[categoria]["patrones"] = patrones_merged
        categorias_actualizadas += 1
        print(f" Actualizada: {categoria} ({len(patrones_merged)} patrones)")
    else:
        # Agregar nueva categoría
        cache_existente[categoria] = datos
        categorias_agregadas += 1
        print(f" Agregada: {categoria} ({len(datos['patrones'])} patrones)")

# Guardar caché actualizado
with open(cache_file, 'w', encoding='utf-8') as f:
    json.dump(cache_existente, f, ensure_ascii=False, indent=2)

print("\n" + "="*80)
print("IMPORTACIÓN COMPLETADA")
print("="*80)
print(f" Categorías agregadas: {categorias_agregadas}")
print(f" Categorías actualizadas: {categorias_actualizadas}")
print(f" Total de categorías: {len(cache_existente)}")
print(f" Archivo guardado: {cache_file}")
print("\n El caché estará disponible en Railway después del próximo deploy")
print("   Accede al panel en: /cache-manager")
