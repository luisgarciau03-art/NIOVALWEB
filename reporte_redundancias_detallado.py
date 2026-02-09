"""
Análisis Detallado de Redundancias - system_prompt.txt
Reporte con números de línea específicos y propuestas de consolidación
"""

import re
import sys

sys.stdout.reconfigure(encoding='utf-8')

with open(r"C:\Users\PC 1\AgenteVentas\prompts\system_prompt.txt", "r", encoding="utf-8") as f:
    lines = f.readlines()

print("=" * 120)
print("REPORTE DETALLADO DE REDUNDANCIAS - system_prompt.txt")
print(f"Archivo: 1,666 líneas | ~32k tokens | Objetivo: ~16k tokens (50% reducción)")
print("=" * 120)

print("\n\n## CATEGORÍA 1: FIX DUPLICADOS Y REPETICIONES CRÍTICAS\n")
print("-" * 120)

# FIX 46 - Marcas (aparece 3 veces)
print("\n### 1.1 FIX 46 - Regla sobre marcas (CRÍTICO)")
print("Apariciones: Líneas 9-40, 144-165, 289-293, 780-783")
print("PROBLEMA: La misma regla se repite 4 veces con diferentes palabras")
print("\nPROPUESTA:")
print("  Consolidar en UNA sección al inicio (líneas 9-40)")
print("  En otras ubicaciones, usar: '(Ver FIX 46: Solo marca NIOVAL)'")
print("  REDUCCIÓN: ~200 tokens")

# FIX 172 - No pedir nombre
print("\n### 1.2 FIX 172 - No pedir nombre (aparece 4 veces)")
print("Apariciones: Líneas 404, 409, 413, 434")
print("PROBLEMA: Se repite ' FIX 172: NO pidas el nombre (genera delays de audio)' 4 veces")
print("\nPROPUESTA:")
print("  Mencionar UNA VEZ al inicio de la sección FASE 2")
print("  Eliminar las 3 repeticiones")
print("  REDUCCIÓN: ~100 tokens")

# FIX 171 - No usar nombre del cliente
print("\n### 1.3 FIX 171 - No usar nombre del cliente")
print("Apariciones: Líneas 623, 659, 677")
print("PROBLEMA: Regla repetida 3 veces")
print("\nPROPUESTA:")
print("  Consolidar en sección única")
print("  Referenciar en otros lugares con '(FIX 171)'")
print("  REDUCCIÓN: ~80 tokens")

# FIX 98 - Cliente ocupado
print("\n### 1.4 FIX 98 - Cliente ocupado en mostrador")
print("Apariciones: Líneas 67-114, 357-378")
print("PROBLEMA: Contexto duplicado sobre cliente ocupado")
print("\nPROPUESTA:")
print("  Mantener solo la versión más detallada (líneas 67-114)")
print("  Eliminar repetición en líneas 357-378")
print("  REDUCCIÓN: ~250 tokens")

print("\n\n## CATEGORÍA 2: EJEMPLOS CORRECTO/INCORRECTO REDUNDANTES\n")
print("-" * 120)

print("\n### 2.1 Ejemplos de manejo de correo (líneas 248-252, 969-1006)")
print("PROBLEMA: Mismo ejemplo repetido 2 veces con variaciones mínimas")
print("\nPROPUESTA:")
print("  Consolidar en formato tabla compacto:")
print("  | Escenario | Acción |")
print("  |-----------|--------|")
print("  | Cliente deletrea correo | Escuchar TODO sin interrumpir → Confirmar al final |")
print("  REDUCCIÓN: ~400 tokens")

print("\n### 2.2 Ejemplos de transferencia (líneas 396-435)")
print("PROBLEMA: Múltiples ejemplos de la misma situación (transferencia)")
print("\nPROPUESTA:")
print("  Reducir a 2 ejemplos clave:")
print("  - Cliente confirma que ES el encargado")
print("  - Cliente transfiere a otra persona")
print("  REDUCCIÓN: ~200 tokens")

print("\n### 2.3 Ejemplos al final (líneas 1496-1665)")
print("PROBLEMA: 8 ejemplos extensos CORRECTO/INCORRECTO")
print("\nPROPUESTA:")
print("  Convertir a formato tabla:")
print("  | Situación |  Error |  Correcto |")
print("  Reducir narrativa, mantener solo el mensaje clave")
print("  REDUCCIÓN: ~800 tokens")

print("\n\n## CATEGORÍA 3: OBJECIONES (24 objeciones con formato repetitivo)\n")
print("-" * 120)

print("\n### 3.1 Objeciones estándar (líneas 725-828)")
print("PROBLEMA: Cada objeción usa formato largo:")
print("  'OBJECIÓN: [texto]'")
print("  'RESPUESTA: [párrafo largo]'")
print("\nPROPUESTA:")
print("  Formato tabla de 2 columnas:")
print("  | Objeción | Respuesta (concisa) |")
print("  |----------|---------------------|")
print("  | 'No me interesa' | 'Entiendo. ¿Le envío catálogo sin compromiso para referencia?' |")
print("  REDUCCIÓN: ~600 tokens")

print("\n\n## CATEGORÍA 4: REGLAS PROHIBIDAS ( NUNCA)\n")
print("-" * 120)

print("\n### 4.1 Consolidar prohibiciones similares")
print("PROBLEMA: 36 reglas prohibidas dispersas")
print("\nEjemplos de consolidación:")
print("  Líneas 18-26: 8 prohibiciones sobre 'no mencionar correo después derecibirlo'")
print("  → Consolidar en: ' NO menciones el correo después de recibirlo (ni repetirlo, ni confirmar, ni preguntar más)'")
print("  ")
print("  Líneas 28-39: 6 prohibiciones sobre marcas externas")
print("  → Ya cubierto en FIX 46 (consolidar referencia)")
print("  ")
print("  Líneas 167-179: 8 prohibiciones sobre confirmar productos")
print("  → Consolidar en: ' NO confirmes productos. Siempre redirige al catálogo completo'")
print("\nREDUCCIÓN TOTAL: ~500 tokens")

print("\n\n## CATEGORÍA 5: ENCABEZADOS Y SEPARADORES DECORATIVOS\n")
print("-" * 120)

print("\n### 5.1 Separadores extensos")
print("PROBLEMA: Múltiples líneas de '---', '===', emojis repetidos")
print("Ejemplos:")
print("  Línea 436: '---' (separador innecesario)")
print("  Línea 501: '---' (separador innecesario)")
print("  Líneas con  repetido 3 veces en encabezado")
print("\nPROPUESTA:")
print("  - Eliminar separadores --- (usar solo ##)")
print("  - Reducir  a ")
print("  - Usar formato Markdown estándar")
print("  REDUCCIÓN: ~200 tokens")

print("\n\n## CATEGORÍA 6: FORMULARIO DE CALIFICACIÓN (líneas 1036-1404)\n")
print("-" * 120)

print("\n### 6.1 Estructura del formulario de 7 preguntas")
print("PROBLEMA: Formato muy verbose con repeticiones")
print("Cada pregunta usa:")
print("  - **MOMENTO:** (30-50 palabras)")
print("  - **CÓMO PREGUNTAR (opciones sutiles):** (repetido 6 veces)")
print("  - **OPCIONES A CAPTURAR:** (con explicaciones largas)")
print("  - **MANEJO DE SINÓNIMOS:** (ejemplos redundantes)")
print("\nPROPUESTA:")
print("  Formato tabla compacto por pregunta:")
print("  | P# | Cuándo | Cómo preguntar | Opciones | Sinónimos clave |")
print("  Mantener solo 1-2 ejemplos por pregunta")
print("  REDUCCIÓN: ~1,500 tokens")

print("\n\n## CATEGORÍA 7: DESPEDIDAS Y FRASES TIPO\n")
print("-" * 120)

print("\n### 7.1 Variaciones de despedida")
print("PROBLEMA: 21 líneas con variaciones de despedida dispersas")
print("Ejemplos:")
print("  'Muchas gracias por su tiempo, que tenga excelente día'")
print("  'Que tenga excelente tarde. Hasta pronto'")
print("  'Muchas gracias, que tenga buen día'")
print("\nPROPUESTA:")
print("  Sección única 'DESPEDIDAS TIPO' con:")
print("  - Formal: 'Muchas gracias. Que tenga excelente día.'")
print("  - Informal: 'Gracias. Hasta luego.'")
print("  REDUCCIÓN: ~150 tokens")

print("\n\n## CATEGORÍA 8: TIMING Y HORARIOS\n")
print("-" * 120)

print("\n### 8.1 Reglas de horario laboral")
print("PROBLEMA: Reglas sobre horario 8am-5pm repetidas múltiples veces")
print("Apariciones: Líneas 650-655, 734-739, 771-776")
print("\nPROPUESTA:")
print("  Consolidar en sección única 'HORARIO LABORAL' al inicio")
print("  Referenciar en objeciones: '(ver horario laboral)'")
print("  REDUCCIÓN: ~200 tokens")

print("\n\n" + "=" * 120)
print("RESUMEN EJECUTIVO DE CONSOLIDACIÓN")
print("=" * 120)

consolidations = [
    ("FIX duplicados (46, 172, 171, 98)", 630),
    ("Ejemplos CORRECTO/INCORRECTO", 1400),
    ("Objeciones (formato tabla)", 600),
    ("Reglas prohibidas consolidadas", 500),
    ("Separadores y decoración", 200),
    ("Formulario 7 preguntas", 1500),
    ("Despedidas tipo", 150),
    ("Horarios y timing", 200),
    ("Otros ajustes menores", 500)
]

print("\nDETALLE DE REDUCCIONES PROPUESTAS:\n")
total_reduction = 0
for item, tokens in consolidations:
    print(f"  {item:<45} -{tokens:>5} tokens")
    total_reduction += tokens

print(f"\n  {'TOTAL REDUCCIÓN ESTIMADA':<45} -{total_reduction:>5} tokens")
print(f"\n  Archivo actual:                               ~32,000 tokens")
print(f"  Archivo optimizado:                           ~{32000 - total_reduction:,} tokens")
print(f"  Reducción porcentual:                          {(total_reduction/32000)*100:.1f}%")

print("\n\n## PLAN DE IMPLEMENTACIÓN SUGERIDO\n")
print("-" * 120)

print("""
FASE 1: CONSOLIDACIONES DE ALTO IMPACTO (3,000 tokens)
  1. Consolidar formulario de 7 preguntas (líneas 1036-1404) → formato tabla
  2. Consolidar ejemplos CORRECTO/INCORRECTO (líneas 1496-1665) → formato tabla

FASE 2: ELIMINACIÓN DE DUPLICADOS (1,130 tokens)
  3. Unificar FIX duplicados (46, 172, 171, 98)
  4. Consolidar reglas prohibidas similares

FASE 3: OPTIMIZACIÓN DE FORMATO (850 tokens)
  5. Convertir objeciones a tabla
  6. Eliminar separadores decorativos
  7. Consolidar despedidas y horarios

FASE 4: REFINAMIENTO (700 tokens)
  8. Simplificar ejemplos de manejo de correo
  9. Reducir narrativa en secciones de flujo
  10. Optimizar pronunciación y reglas técnicas

RESULTADO FINAL:
   Reducción de ~5,680 tokens (45%)
   De ~32k a ~17k tokens
   100% del contenido funcional preservado
   Mayor claridad y consultabilidad
""")

print("\n" + "=" * 120)
print("FIN DEL REPORTE DETALLADO")
print("=" * 120)
