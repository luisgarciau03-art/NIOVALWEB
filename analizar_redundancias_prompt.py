"""
Análisis de Redundancias en system_prompt.txt
Objetivo: Identificar contenido redundante sin perder información funcional
"""

import re
from collections import defaultdict
import sys

# Configurar salida para UTF-8
sys.stdout.reconfigure(encoding='utf-8')

# Leer el archivo completo
with open(r"C:\Users\PC 1\AgenteVentas\prompts\system_prompt.txt", "r", encoding="utf-8") as f:
    lines = f.readlines()

print("=" * 100)
print("ANÁLISIS DE REDUNDANCIAS EN system_prompt.txt")
print(f"Total de líneas: {len(lines)}")
print("=" * 100)

# ===========================
# 1. ANÁLISIS DE FIX DUPLICADOS
# ===========================
print("\n\n### 1. ANÁLISIS DE FIX NUMBERS ###\n")

fix_pattern = re.compile(r'FIX\s+(\d+)', re.IGNORECASE)
fix_occurrences = defaultdict(list)

for i, line in enumerate(lines, 1):
    matches = fix_pattern.findall(line)
    for fix_num in matches:
        fix_occurrences[fix_num].append(i)

# FIX mencionados múltiples veces
duplicated_fixes = {k: v for k, v in fix_occurrences.items() if len(v) > 1}
if duplicated_fixes:
    print(f"FIX mencionados múltiples veces: {len(duplicated_fixes)}")
    for fix_num, line_nums in sorted(duplicated_fixes.items(), key=lambda x: len(x[1]), reverse=True):
        print(f"  FIX {fix_num}: {len(line_nums)} menciones en líneas {line_nums[:5]}{'...' if len(line_nums) > 5 else ''}")

# ===========================
# 2. ANÁLISIS DE FRASES REPETITIVAS
# ===========================
print("\n\n### 2. ANÁLISIS DE FRASES REPETITIVAS ###\n")

# Buscar frases que se repiten textualmente
phrase_occurrences = defaultdict(list)
for i, line in enumerate(lines, 1):
    cleaned = line.strip()
    if len(cleaned) > 30 and not cleaned.startswith("#"):  # Ignorar encabezados
        phrase_occurrences[cleaned].append(i)

repeated_phrases = {k: v for k, v in phrase_occurrences.items() if len(v) > 2}
print(f"Frases repetidas textualmente (>30 chars): {len(repeated_phrases)}")
for phrase, line_nums in sorted(repeated_phrases.items(), key=lambda x: len(x[1]), reverse=True)[:10]:
    if len(line_nums) > 2:
        print(f"  [{len(line_nums)}x] Líneas {line_nums}: {phrase[:80]}...")

# ===========================
# 3. ANÁLISIS DE SECCIONES SIMILARES
# ===========================
print("\n\n### 3. ANÁLISIS DE SECCIONES SIMILARES ###\n")

# Buscar patrones de ejemplo CORRECTO / INCORRECTO
example_sections = []
in_example = False
current_example = {"start": 0, "end": 0, "type": None}

for i, line in enumerate(lines, 1):
    if "CORRECTO:" in line or "INCORRECTO:" in line:
        if not in_example:
            current_example = {"start": i, "lines": []}
            in_example = True
        current_example["lines"].append(i)
    elif in_example and line.strip() == "":
        current_example["end"] = i
        example_sections.append(current_example)
        in_example = False

print(f"Secciones de ejemplos encontradas: {len(example_sections)}")

# ===========================
# 4. ANÁLISIS DE REGLAS PROHIBIDAS DUPLICADAS
# ===========================
print("\n\n### 4. ANÁLISIS DE REGLAS PROHIBIDAS ( NUNCA) ###\n")

prohibited_pattern = re.compile(r'.*NUNCA.*', re.IGNORECASE)
prohibited_rules = []

for i, line in enumerate(lines, 1):
    if prohibited_pattern.search(line):
        prohibited_rules.append((i, line.strip()))

print(f"Total de reglas PROHIBIDAS: {len(prohibited_rules)}")

# Agrupar reglas similares
similar_prohibitions = defaultdict(list)
for line_num, rule in prohibited_rules:
    # Extraer el contenido después de 
    content = re.sub(r'+\s*(NUNCA\s+)?', '', rule).strip()
    key = content[:50]  # Primeros 50 caracteres para agrupar
    similar_prohibitions[key].append((line_num, rule))

print(f"\nReglas prohibidas agrupadas por similitud:")
for key, rules in sorted(similar_prohibitions.items(), key=lambda x: len(x[1]), reverse=True)[:10]:
    if len(rules) > 2:
        print(f"  [{len(rules)}x] Similar a: {key}...")
        for ln, r in rules[:3]:
            print(f"    L{ln}: {r[:70]}...")

# ===========================
# 5. ANÁLISIS DE DESPEDIDAS Y RESPUESTAS TIPO
# ===========================
print("\n\n### 5. ANÁLISIS DE DESPEDIDAS Y RESPUESTAS TIPO ###\n")

despedida_pattern = re.compile(r'(Muchas gracias|excelente día|Hasta pronto|Que tenga)', re.IGNORECASE)
despedidas = []

for i, line in enumerate(lines, 1):
    if despedida_pattern.search(line):
        despedidas.append((i, line.strip()))

print(f"Líneas con despedidas/saludos: {len(despedidas)}")

# ===========================
# 6. ANÁLISIS DE OBJECIONES DUPLICADAS
# ===========================
print("\n\n### 6. ANÁLISIS DE OBJECIONES ###\n")

objecion_pattern = re.compile(r'OBJECIÓN:', re.IGNORECASE)
objeciones = []

for i, line in enumerate(lines, 1):
    if objecion_pattern.search(line):
        objeciones.append((i, line.strip()))

print(f"Total de objeciones definidas: {len(objeciones)}")

# ===========================
# 7. ESTIMACIÓN DE TOKENS
# ===========================
print("\n\n### 7. ESTIMACIÓN DE TOKENS ###\n")

total_chars = sum(len(line) for line in lines)
estimated_tokens = total_chars // 4  # Aproximación: 1 token ≈ 4 caracteres

print(f"Total de caracteres: {total_chars:,}")
print(f"Tokens estimados (aprox): {estimated_tokens:,}")
print(f"Objetivo de reducción (45%): ~{int(estimated_tokens * 0.45):,} tokens a eliminar")
print(f"Objetivo final: ~{int(estimated_tokens * 0.55):,} tokens")

# ===========================
# 8. RECOMENDACIONES
# ===========================
print("\n\n" + "=" * 100)
print("### RECOMENDACIONES DE COMPACTACIÓN ###")
print("=" * 100)

print("""
OPORTUNIDADES PRINCIPALES:

1. CONSOLIDAR FIX DUPLICADOS
   - Varios FIX se mencionan múltiples veces en diferentes secciones
   - Crear una sección única de "REGLAS CRÍTICAS DE FIX" al inicio
   - Referenciar en contexto con formato compacto: (ver FIX 223)

2. COMPACTAR EJEMPLOS CORRECTO/INCORRECTO
   - Muchos ejemplos se pueden reducir a formato tabla
   - Usar bullets en lugar de diálogos completos
   - Mantener solo ejemplos únicos, eliminar variaciones redundantes

3. CONSOLIDAR REGLAS PROHIBIDAS ( NUNCA)
   - Agrupar todas las prohibiciones similares en una sola línea
   - Ejemplo: En lugar de 5 líneas de " NO digas X", usar: " NO digas: X, Y, Z"

4. COMPACTAR OBJECIONES
   - Convertir formato largo a tabla de 2 columnas: Objeción | Respuesta
   - Eliminar ejemplos repetitivos de manejo

5. ELIMINAR ENCABEZADOS Y SEPARADORES DECORATIVOS
   - Usar ## en lugar de líneas de ===
   - Reducir emojis y decoraciones visuales

6. CONSOLIDAR DESPEDIDAS
   - Una sola sección con variaciones, no repetir en cada escenario

7. COMPACTAR PRONUNCIACIÓN
   - Usar lista compacta en lugar de múltiples ejemplos

IMPACTO ESTIMADO:
- Reducción esperada: 40-50% (12k-16k tokens eliminados)
- Tokens objetivo final: ~16k-20k tokens
- Conservar: 100% del contenido funcional único
""")

print("\n" + "=" * 100)
print("FIN DEL ANÁLISIS")
print("=" * 100)
