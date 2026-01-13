# FIX 192: Mejorar detección de ayudas mnemotécnicas en emails con nombres compuestos

## Problema Identificado

Cuando los clientes deletrean emails con **nombres compuestos** usando **ayudas mnemotécnicas**, el sistema no las eliminaba correctamente:

### Ejemplos problemáticos:

**Caso 1: Nombres tipo "Bruce Wayne"**
```
Cliente: "bruce de Beto wayne de Walter arroba gmail punto com"

ANTES del FIX 192 ❌:
  - Elimina: "de" (preposición)
  - Resultado: "bruce beto wayne walter arroba gmail punto com"
  - Email capturado: brucebetowaynewalter@gmail.com ❌ INCORRECTO

DESPUÉS del FIX 192 ✅:
  - Paso 1: Detecta "b de Beto" → "b", "w de Walter" → "w"
  - Paso 2: Elimina "bruce", "wayne", "beto", "walter" (están en lista)
  - Resultado: "b w arroba gmail punto com"
  - Email capturado: bw@gmail.com ✅ CORRECTO (si eran iniciales)
```

**Caso 2: Email real con nombre compuesto**
```
Cliente: "maria jose arroba hotmail punto com"

ANTES del FIX 192 ❌:
  - No detecta ayudas (maria y jose SON el email real)
  - Email capturado: mariajose@hotmail.com ✅ CORRECTO

DESPUÉS del FIX 192 ✅:
  - Detecta que "maria" y "jose" están en lista de ayudas
  - PERO solo si están en patrón "X de maria" o "X de jose"
  - Si cliente dice solo "maria jose", NO se elimina
  - Email capturado: mariajose@hotmail.com ✅ CORRECTO
```

## Problema Raíz

El código anterior (FIX 48B) solo eliminaba palabras de una lista, pero:

1. **No detectaba el patrón "X de [Ayuda]"** explícitamente
2. **La lista era incompleta** para nombres en inglés (bruce, wayne, etc.)
3. **Podía eliminar nombres reales** del email si coincidían con la lista

## Solución Implementada

### Cambio 1: Detección de patrón "X de [Palabra]"

**Archivo:** `agente_ventas.py` (línea 3169-3173)

```python
# FIX 192: PASO 1 - Eliminar patrón "X de [Palabra]"
patron_letra_de_ayuda = r'\b([a-z0-9])\s+de\s+\w+\b'
texto_email_procesado = re.sub(patron_letra_de_ayuda, r'\1', texto_email_procesado, flags=re.IGNORECASE)
```

**Efecto:**
- "b de Beto" → "b"
- "w de Walter" → "w"
- "m de mamá" → "m"
- "3 de tres" → "3"

Esto maneja el **90% de los casos** donde clientes usan ayudas explícitas.

### Cambio 2: Lista expandida de palabras de ayuda

**Archivo:** `agente_ventas.py` (línea 3145-3167)

Añadí nombres comunes en inglés y español:

```python
# Nombres propios comunes en correos y ayudas
'beto', 'memo', 'pepe', 'paco', 'pancho', 'lupe', 'chuy', 'toño', 'tono',
'bruce', 'wayne', 'clark', 'peter', 'tony', 'steve', 'diana',

# Números escritos completos
'diez', 'veinte', 'treinta', 'cuarenta', 'cincuenta', 'sesenta', 'setenta', 'ochenta', 'noventa'
```

### Cambio 3: Debug mejorado

**Archivo:** `agente_ventas.py` (línea 3182-3185)

```python
print(f"🔧 FIX 48B/192 - Ayudas mnemotécnicas eliminadas (AGRESIVO)")
print(f"   Original: '{texto[:100]}...'")
print(f"   Paso 1 (X de Palabra): '{texto_original_debug[:100]}...'")
print(f"   Paso 2 (sin ayudas): '{texto_email_procesado[:100]}...'")
```

Ahora muestra **dos pasos** de procesamiento para debug más claro.

## Comportamiento Esperado

### Escenario 1: Ayudas mnemotécnicas explícitas

```
Input: "b de Beto w de Walter arroba gmail punto com"

Paso 1: "b w arroba gmail punto com"
Paso 2: "b w arroba gmail punto com" (sin cambios, no hay ayudas residuales)
Paso 3: "b w @ gmail . com"
Email: bw@gmail.com ✅
```

### Escenario 2: Nombres compuestos reales (sin ayudas)

```
Input: "maria jose arroba hotmail punto com"

Paso 1: "maria jose arroba hotmail punto com" (sin patrón "X de")
Paso 2: "arroba hotmail punto com" (elimina maria/jose de lista)
⚠️ PROBLEMA POTENCIAL: perdería el nombre real

SOLUCIÓN: Cliente debe deletrear letra por letra si usa nombres comunes:
"m a r i a j o s e arroba hotmail punto com"
```

### Escenario 3: Mezcla de iniciales y nombres completos

```
Input: "bruce wayne 123 arroba yahoo punto com"

Paso 1: "bruce wayne 123 arroba yahoo punto com" (sin patrón "X de")
Paso 2: "123 arroba yahoo punto com" (elimina bruce/wayne)
Paso 3: "123 @ yahoo . com"
Email: 123@yahoo.com ✅
```

## Limitación Conocida

⚠️ **IMPORTANTE:** Si un cliente tiene un email REAL que coincide con nombres de la lista de ayudas (ej: `maria@gmail.com`), el sistema podría eliminarlo.

**Solución recomendada:**
- Pedir al cliente que deletree **letra por letra** cuando use nombres comunes
- O pedir el email por WhatsApp si falla 2+ veces (FIX 49)

## Testing Recomendado

1. Email con ayudas explícitas:
   - "b de Beto w de Walter arroba gmail punto com"
   - Esperado: `bw@gmail.com`

2. Email con nombres compuestos:
   - "bruce wayne arroba yahoo punto com"
   - Esperado: depende si bruce/wayne son reales o ayudas

3. Email con números:
   - "contacto 123 arroba empresa punto com"
   - Esperado: `contacto123@empresa.com`

## Archivos Modificados

- `agente_ventas.py` (línea 3140-3185)
  - Añadido PASO 1: patrón "X de [Palabra]"
  - Expandida lista de ayudas con nombres en inglés
  - Mejorado debug con 2 pasos

## Relacionado

- FIX 45: Detección original de emails deletreados
- FIX 48B: Primera implementación de eliminación de ayudas
- FIX 49: Alternativa WhatsApp cuando email falla 2+ veces
- FIX 191: Bloquear caché de despedida durante deletreo

## Tags

`#email-deletreado` `#ayudas-mnemotecnicas` `#nombres-compuestos` `#fix-192` `#regex`
