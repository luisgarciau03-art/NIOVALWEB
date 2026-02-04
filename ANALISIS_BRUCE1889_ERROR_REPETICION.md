# ANÁLISIS BRUCE1889 - ERROR DE REPETICIÓN Y NO DETECCIÓN DE CORREO

**Fecha:** 2026-02-04 19:12:03
**CallSid:** CA9050ecb88cbd6e78b09360db281bd98d
**Duración:** 47 segundos
**Resultado:** NEGADO (Cliente colgó)
**Problema:** Bruce repitió 3 veces "Sí, por favor, dígame el correo" y NO detectó el dictado completo del correo

---

## 1. CONVERSACIÓN COMPLETA (CLIENTE vs BRUCE)

### Turno 1
**CLIENTE:** "¿Qué tal? Buenas tardes. Dígame."
**BRUCE:** "Me comunico de la marca nioval, más que nada quería brindar informacion de nuestros productos ferreteros, ¿Se encontrara el encargado o encargada de compras?"

### Turno 2
**CLIENTE:** "¿Qué tal? Buenas tardes. Dígame. Muy bien, y yo te doy el correo. Muy bien, yo le doy el correo."
**BRUCE:** "Sí, por favor, dígame el correo." **(REPETICIÓN #1)**

### Turno 3
**CLIENTE:** "¿Qué tal? Buenas tardes. Dígame. Muy bien, yo te doy el correo. Si me gusta, no tardo. ¿Qué tal? Buenas tardes. Dígame. Muy bien, yo te doy el correo. Si gusta, no tardó. Si es, eh, espérame tantito."
**BRUCE:** "Sí, por favor, dígame el correo." **(REPETICIÓN #2)**

### Turno 4
**CLIENTE:** "¿Qué tal? Buenas tardes. Dígame. Muy bien, yo te doy el correo. Si gusta, no tardó. Si es, eh, espérame tantito. ¿Qué tal? Buenas tardes. Dígame. Muy bien, yo te doy el correo. Si gusta, no tardó. Sí, es, eh, espérame tantito. Sí, mira, es Martín Compras. Sí, mire, es Martín Compras."
**BRUCE:** "Sí, por favor, dígame el correo." **(REPETICIÓN #3)**

### Turno 5 - DICTADO DEL CORREO (NO DETECTADO)
**CLIENTE:** "¿Qué tal? Buenas tardes. Dígame. Muy bien, yo te doy el correo. Si gusta, no tardó. Sí, es, eh, espérame tantito. Sí, mira, es Martín Compras. **Martín Compras arroba--**"

**Transcripciones Deepgram:**
- PARCIAL: 'Martín Compras arroba el grupo Walmart.'
- PARCIAL: 'Martín Compras arroba el grupo Walmart.'
- **FINAL: 'Martín Compras arroba Grupo Balmar.'**

**BRUCE:** "Sí, por favor, dígame el correo." **(REPETICIÓN #4 - después del dictado)**

### Turno 6
**CLIENTE:** "" (Timeout - cliente colgó frustrado)
**BRUCE:** "Disculpa, no te escuché bien, ¿me puedes repetir?"

**Cliente cuelga**

---

## 2. MOMENTO EXACTO DE LAS 3 REPETICIONES

### REPETICIÓN #1 (Línea 172, 19:12:22)
```
[2026-02-04 19:12:22] [BRUCE] BRUCE1889 DICE: "Sí, por favor, dígame el correo."
```
**Contexto:** Cliente dijo "Muy bien, yo le doy el correo"
**FIX:** FIX 491: PATRÓN DETECTADO (CLIENTE_OFRECE_CORREO)
**Estado:** Apropiado (cliente ofrece dar correo)

### REPETICIÓN #2 (Línea 261, 19:12:30)
```
[2026-02-04 19:12:30] [BRUCE] BRUCE1889 DICE: "Sí, por favor, dígame el correo."
```
**Contexto:** Cliente dijo "espérame tantito" (pidiendo esperar)
**FIX:** FIX 491: PATRÓN DETECTADO (CLIENTE_OFRECE_CORREO)
**Estado:** INAPROPIADO - Cliente pidió esperar, no ofreció dar correo

### REPETICIÓN #3 (Línea 379, 19:12:36)
```
[2026-02-04 19:12:36] [BRUCE] BRUCE1889 DICE: "Sí, por favor, dígame el correo."
```
**Contexto:** Cliente dijo "Sí, mira, es Martín Compras" (preparándose para dictar)
**FIX:** FIX 491: PATRÓN DETECTADO (CLIENTE_OFRECE_CORREO)
**Estado:** INAPROPIADO - Cliente está empezando a dictar, no ofreció dar correo

### REPETICIÓN #4 (Línea 514, 19:12:42) - DESPUÉS DEL DICTADO
```
[2026-02-04 19:12:42] [BRUCE] BRUCE1889 DICE: "Sí, por favor, dígame el correo."
```
**Contexto:** Cliente YA dictó "Martín Compras arroba Grupo Balmar"
**FIX:** FIX 491: PATRÓN DETECTADO (CLIENTE_OFRECE_CORREO)
**Estado:** CRÍTICO - Cliente YA dictó el correo, Bruce no lo procesó

---

## 3. DICTADO DE CORREO QUE NO DETECTÓ

### Línea 484 (19:12:41)
```
[2026-02-04 19:12:41] [CLIENTE] BRUCE1889 - CLIENTE DIJO:
"¿Qué tal? Buenas tardes. Dígame. Muy bien, yo te doy el correo.
Si gusta, no tardó. Sí, es, eh, espérame tantito. Sí, mira, es Martín Compras.
Martín Compras arroba--"
```

### Transcripciones Deepgram detectadas (Líneas 485-510):
```
 FIX 212: [PARCIAL] 'Martín Compras arroba el grupo Walmart.'
 FIX 212: [PARCIAL] 'Martín Compras arroba el grupo Walmart.'
 FIX 212: [FINAL] 'Martín Compras arroba Grupo Balmar.'
```

### Lo que debió capturar:
**Email dictado:** martincompras@grupobalmar.com (o similar)
**Email detectado:** NINGUNO (FIX 496 siguió activándose como si no hubiera dictado)

---

## 4. LOGS RELEVANTES QUE MUESTRAN EL PROBLEMA

### A) FIX 491 disparándose incorrectamente 4 veces

**Línea 168 (19:12:22) - APROPIADO**
```
[EMOJI] FIX 491: PATRÓN DETECTADO (CLIENTE_OFRECE_CORREO)
- Latencia ~0.05s vs 3.5s GPT (reducción 98%)
```

**Línea 257 (19:12:30) - INAPROPIADO**
```
[OK] FIX 496: Cliente OFRECE dar CORREO: '¿Qué tal? Buenas tardes. Dígame. Muy bien, yo te d'
[EMOJI] FIX 491: PATRÓN DETECTADO (CLIENTE_OFRECE_CORREO)
```
**Problema:** Cliente dijo "espérame tantito" - NO está ofreciendo dar correo

**Línea 377 (19:12:36) - INAPROPIADO**
```
[EMOJI] FIX 491: PATRÓN DETECTADO (CLIENTE_OFRECE_CORREO)
```
**Problema:** Cliente dijo "Sí, mira, es Martín Compras" - está DICTANDO, no ofreciendo

**Línea 517 (19:12:42) - CRÍTICO**
```
[OK] FIX 496: Cliente OFRECE dar CORREO: '¿Qué tal? Buenas tardes. Dígame. Muy bien, yo te d'
[EMOJI] FIX 491: PATRÓN DETECTADO (CLIENTE_OFRECE_CORREO)
```
**Problema:** Cliente YA dictó "Martín Compras arroba Grupo Balmar" - NO está ofreciendo, YA lo dio

### B) FIX 455 descartando el dictado del correo (Línea 505-506)

```
 FIX 455: Limpiando 2 transcripciones acumuladas ANTES de enviar audio
   Contenido descartado: [
     'Martín Compras arroba el grupo Walmart.',
     'Martín Compras arroba Grupo Balmar.'
   ]
```

**CRÍTICO:** El sistema DESCARTÓ las transcripciones que contenían el correo dictado

### C) FIX 499 y FIX 504 intentando procesar (Líneas 492-493)

```
    FIX 499: Email COMPLETO detectado - NO esperar más, procesar ahora
    FIX 504: Dictado detectado PERO email ya completo - procesar ahora
```

**Estado:** Detectó que había email completo pero NO lo procesó correctamente

### D) FIX 265 confirmando email completo (Línea 488)

```
    FIX 265: Email parece completo - procesar normalmente
```

### E) FIX 547 detectando modo captura (Líneas 503-507)

```
 FIX 547: Cliente está DANDO número - '¿Qué tal? Buenas tardes. Dígame.
 Muy bien, yo te doy el correo. Si gusta, no tar...'
    Activando modo captura, DESACTIVANDO oferta de contacto Bruce
```

**Problema:** Activó modo captura pero luego descartó el contenido capturado

### F) Resultado final - Email no capturado (Línea 625)

```
   Email capturado:
[WARN] No se capturó WhatsApp ni referencia - no se actualiza columna E
```

---

## 5. CAUSA RAÍZ DEL ERROR

### PROBLEMA #1: FIX 491 (CLIENTE_OFRECE_CORREO) tiene lógica defectuosa

**Comportamiento actual:**
- Se dispara cuando detecta frases como "yo te doy el correo" en CUALQUIER parte del contexto
- No diferencia entre:
  - Cliente OFRECIENDO dar correo (apropiado)
  - Cliente DICTANDO correo (inapropiado - debe escuchar)
  - Cliente ESPERANDO para dictar (inapropiado - debe confirmar "claro, espero")

**Evidencia:**
- Línea 156-157: Detecta "yo te doy el correo" y activa FIX 496
- Línea 256-257: Se repite cuando cliente pide "espérame tantito"
- Línea 377: Se repite cuando cliente dice "Sí, mira, es Martín Compras"
- Línea 516-517: Se repite DESPUÉS de que cliente dictó completo

**Código problemático (hipótesis):**
```python
if "correo" in cliente_dijo and ("doy" in cliente_dijo or "dar" in cliente_dijo):
    return "Sí, por favor, dígame el correo."
```

### PROBLEMA #2: FIX 455 descarta transcripciones críticas

**Comportamiento actual:**
- FIX 455 limpia transcripciones acumuladas ANTES de enviar audio
- Descartó EXACTAMENTE las transcripciones que contenían el email dictado

**Evidencia (Líneas 505-506):**
```
 FIX 455: Limpiando 2 transcripciones acumuladas ANTES de enviar audio
   Contenido descartado: [
     'Martín Compras arroba el grupo Walmart.',
     'Martín Compras arroba Grupo Balmar.'
   ]
```

**Problema:**
- El sistema detectó correctamente el email en las transcripciones PARCIALES y FINAL
- Pero FIX 455 los descartó antes de procesarlos con GPT
- Resultado: GPT nunca vio el email dictado

### PROBLEMA #3: FIX 496/497/499 detectan email pero no capturan

**Evidencia:**
- Línea 492: "FIX 499: Email COMPLETO detectado - NO esperar más, procesar ahora"
- Línea 493: "FIX 504: Dictado detectado PERO email ya completo - procesar ahora"
- Línea 625: "Email capturado: " (vacío)

**Problema:**
- Los FIX de detección funcionaron correctamente
- Pero el flujo de captura y guardado falló
- Posiblemente porque FIX 491 sobrescribió la respuesta antes de capturar

### PROBLEMA #4: FIX 248 concatena con duplicados de saludo

**Evidencia (Líneas 228, 352):**
```
FIX 248: Concatenando 2 partes únicas:
'¿Qué tal? Buenas tardes. Dígame. Muy bien, yo te doy el correo. Si me gusta, no tardo.
¿Qué tal? Buenas tardes. Dígame. Muy bien, yo te doy el correo. Si gusta, no tardó.
Si es, eh, espérame tantito.'
```

**Problema:**
- El saludo "¿Qué tal? Buenas tardes. Dígame." se repite múltiples veces
- Esto contamina el contexto y confunde la detección de patrones
- FIX 248 intenta eliminar duplicados pero no funciona correctamente

---

## 6. CADENA DE FALLAS

```
1. Cliente: "Muy bien, yo te doy el correo"
   └─> FIX 496 detecta oferta de correo ✓
   └─> FIX 491 responde "Sí, por favor, dígame el correo" ✓ APROPIADO

2. Cliente: "espérame tantito"
   └─> FIX 248 concatena con contexto previo
   └─> Contexto incluye "yo te doy el correo" de antes
   └─> FIX 496 se dispara NUEVAMENTE (falso positivo) ✗
   └─> FIX 491 repite "Sí, por favor, dígame el correo" ✗ INAPROPIADO

3. Cliente: "Sí, mira, es Martín Compras"
   └─> FIX 248 concatena con contexto previo OTRA VEZ
   └─> Contexto sigue incluyendo "yo te doy el correo"
   └─> FIX 496 se dispara TERCERA VEZ (falso positivo) ✗
   └─> FIX 491 repite "Sí, por favor, dígame el correo" ✗ INAPROPIADO

4. Cliente: "Martín Compras arroba Grupo Balmar"
   └─> Deepgram detecta correctamente el email ✓
   └─> FIX 499: Email COMPLETO detectado ✓
   └─> FIX 504: Dictado detectado ✓
   └─> FIX 547: Activando modo captura ✓
   └─> Pero... FIX 496 se dispara CUARTA VEZ (contexto antiguo) ✗
   └─> FIX 455 DESCARTA las transcripciones con el email ✗ CRÍTICO
   └─> FIX 491 repite "Sí, por favor, dígame el correo" ✗ CRÍTICO
   └─> Email nunca llega a GPT para procesar ✗
   └─> Email NO se captura ✗

5. Cliente: (cuelga frustrado)
```

---

## 7. RESUMEN EJECUTIVO

### Problema Principal
Bruce repitió 4 veces "Sí, por favor, dígame el correo" debido a que:
1. FIX 496/491 se disparan cada vez que ven "correo" en el contexto acumulado
2. No diferencian entre OFRECER correo vs DICTANDO correo vs ESPERANDO para dictar

### Problema Crítico
El email "Martín Compras arroba Grupo Balmar" fue:
1. Correctamente detectado por Deepgram ✓
2. Correctamente identificado por FIX 499, 504, 265 ✓
3. Pero DESCARTADO por FIX 455 antes de procesarse ✗
4. Y nunca llegó a GPT para extracción ✗

### Impacto
- Cliente colgó frustrado después de 47 segundos
- Email válido perdido
- Experiencia de usuario muy negativa
- Bruce autoevaluación: 3/10

---

## 8. SOLUCIONES REQUERIDAS

### SOLUCIÓN #1: Rediseñar FIX 496/491 con estados

```python
# Estado del flujo de correo
email_flow_state = None  # 'offered' -> 'waiting' -> 'dictating' -> 'captured'

# Solo disparar si cliente OFRECE por primera vez
if email_flow_state is None and cliente_ofrece_correo():
    email_flow_state = 'offered'
    return "Sí, por favor, dígame el correo."

# Si está dictando, NO interrumpir
elif email_flow_state == 'dictating':
    # Dejar que GPT procese el dictado
    return None

# Si pide esperar, confirmar
elif "espera" in cliente_dijo and email_flow_state == 'offered':
    email_flow_state = 'waiting'
    return "Claro, espero."
```

### SOLUCIÓN #2: Proteger FIX 455 de descartar emails

```python
# NO descartar transcripciones que contengan emails
if tiene_email(transcripcion) or tiene_dictado_activo(transcripcion):
    # Preservar para procesamiento
    preservar_transcripcion(transcripcion)
else:
    # Descartar solo ruido
    descartar_transcripcion(transcripcion)
```

### SOLUCIÓN #3: Mejorar FIX 248 para eliminar saludos repetidos

```python
# Detectar y eliminar saludos duplicados del contexto
contexto_limpio = eliminar_saludos_duplicados(contexto_acumulado)
```

### SOLUCIÓN #4: Priorizar FIX 499/504 sobre FIX 491

```python
# Si email completo detectado, NO disparar CLIENTE_OFRECE_CORREO
if email_completo_detectado():
    # Procesar email inmediatamente
    procesar_y_capturar_email()
    return None  # NO responder con "dígame el correo"
```

---

## 9. PRIORIDAD DE FIXES

1. **CRÍTICO:** FIX 455 descartando emails dictados
2. **CRÍTICO:** FIX 496/491 disparándose con contexto antiguo
3. **ALTA:** FIX 248 acumulando saludos duplicados
4. **MEDIA:** Falta de estados en flujo de captura de correo

---

**Análisis completado:** 2026-02-04
**Archivo fuente:** logs_bruce1889.txt
**ID BRUCE:** BRUCE1889
**CallSid:** CA9050ecb88cbd6e78b09360db281bd98d
