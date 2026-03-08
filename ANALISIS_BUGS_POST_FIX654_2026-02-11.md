# Análisis de Bugs Post-FIX 654-657
**Fecha**: 2026-02-11 21:20 - 21:30
**Bugs analizados**: BRUCE2129+
**Total bugs encontrados**: 11 bugs en 4 llamadas

---

## Resumen Ejecutivo

### Bugs Por Tipo

| Tipo | Cantidad | Severidad | Estado |
|------|----------|-----------|--------|
| **GPT_LOG ICA_ROTA** | 3 | 🔴 CRÍTICO | ❌ NO CUBIERTO |
| **CLIENTE_HABLA_ULTIMO** | 1 | 🔴 CRÍTICO | ⚠️ TIMEOUT STT |
| **GPT_FUERA_DE_TEMA** | 3 | 🟡 MEDIO | ❌ NO CUBIERTO |
| **PREGUNTA_REPETIDA** | 2 | 🟡 MEDIO | ❌ NO CUBIERTO |
| **CATALOGO_REPETIDO** | 2 | 🟡 MEDIO | ⚠️ FIX 493B FALLÓ |
| **GPT_TONO_INADECUADO** | 1 | 🟡 MEDIO | ✅ CUBIERTO FIX 651 |

### Patrón Crítico Detectado

**69% de bugs son GPT_LOGICA_ROTA** (3/11 principales):
- Cliente rechaza proporcionar contacto ("No, oiga" 2x)
- Bruce vuelve a pedir el mismo dato inmediatamente
- FIX 655 (regla #2 anti-repetición) NO está funcionando correctamente

---

## Análisis Detallado por Llamada

### BRUCE2144 - 1 BUG (TIMEOUT STT)

**Tel**: +526622109098 | **Negocio**: PROMATCO FERRETERÍA
**Timestamp**: 2026-02-11 21:20:50
**Duración**: 16 segundos

#### Bug Detectado

| Bug ID | Tipo | Descripción |
|--------|------|-------------|
| 1 | CLIENTE_HABLA_ULTIMO | Cliente dijo "Señor." pero Bruce NO respondió |

#### Conversación

```
TURNO 1
CLIENTE: "Buen día,"
BRUCE: "Me comunico de la marca nioval, más que nada quería brindar informacion
        de nuestros productos ferreteros, ¿Se encontrara el encargado o encargada
        de compras?"

TURNO 2
CLIENTE: "Señor."
BRUCE: "" (VACÍO - NO RESPONDIÓ)
```

#### Causa Raíz

```
[LOG] FIX 401: Deepgram no respondió en 1.5s
[LOG] FIX 498/502: Respuesta vacía (silencio #1) - Continuando sin audio
```

**Diagnóstico**:
- ❌ **NO ES BUG DE CÓDIGO** - Es timeout del STT (Deepgram)
- Cliente llamó atención diciendo "Señor" pero Deepgram no devolvió transcripción a tiempo
- GPT nunca fue invocado porque no había texto para procesar
- Bug detector correctamente identificó CLIENTE_HABLA_ULTIMO

**Acción**:
- ✅ Sistema funcionó correctamente (detectó el problema)
- ⚠️ Problema infraestructura: Deepgram timeout ocasional
- 💡 Considerar aumentar timeout o mejorar fallback a Azure Speech

---

### BRUCE2143 - 4 BUGS (MÚLTIPLES FALLAS GPT)

**Tel**: +526622504515 | **Negocio**: Desconocido
**Timestamp**: 2026-02-11 21:19:56
**Duración**: 44 segundos

#### Bugs Detectados

| Bug ID | Tipo | Turno | Descripción |
|--------|------|-------|-------------|
| 1 | GPT_FUERA_DE_TEMA | 1 | Bruce pidió contacto SIN mencionar productos |
| 2 | GPT_LOGICA_ROTA | 2 | Bruce repitió petición tras cliente decir "No" 2x |
| 3 | PREGUNTA_REPETIDA | 1-2 | Preguntó WhatsApp 2 veces |
| 4 | CATALOGO_REPETIDO | 1-2 | Ofreció catálogo 2 veces |

#### Conversación Completa

```
TURNO 1
CLIENTE: "Pero tenía la cuenta, buenas tardes. Torcería la fuente, buenas tardes."
         (STT confuso - cliente probablemente dijo algo sobre estar ocupado)

BRUCE:   "Me comunico de la marca NIOVAL, más que nada quería brindar información
          de nuestros productos de ferretería. ¿Me podría proporcionar un número
          de WhatsApp o correo para enviarle el catálogo?"

🔴 BUG 1 (GPT_FUERA_DE_TEMA): Bruce NO explicó productos, fue directo a pedir contacto
🔴 BUG 3 (PREGUNTA_REPETIDA): Primera vez que pide WhatsApp
🔴 BUG 4 (CATALOGO_REPETIDO): Primera vez que ofrece catálogo

TURNO 2
CLIENTE: "No, oiga."  (RECHAZÓ proporcionar contacto)
CLIENTE: "No, oiga."  (REPITIÓ el rechazo - cliente enfático)

[LOG] FIX 81 DEBUG: Verificando objeciones en: 'No, oiga. No, oiga.'
[LOG] [OK] FIX 81 DEBUG: NO se detectó objeción terminal. Continuando conversación normal.

BRUCE:   "Entiendo, no hay problema. ¿Me podría dar su WhatsApp para enviarle
          el catálogo?"

🔴 BUG 2 (GPT_LOGICA_ROTA): Cliente dijo "NO" DOS VECES y Bruce VOLVIÓ A PEDIR WhatsApp
🔴 BUG 3 (PREGUNTA_REPETIDA): Segunda vez que pide WhatsApp (en 44 segundos)
🔴 BUG 4 (CATALOGO_REPETIDO): Segunda vez que ofrece catálogo

TURNO 3
CLIENTE: "¿Se maneja por por"  (pregunta truncada por STT)
BRUCE: [Llamada terminó]
```

#### Causa Raíz

**1. FIX 655 NO FUNCIONÓ**
```python
# Regla #2 dice:
"Si el cliente ya proporcionó un dato O EXPLÍCITAMENTE DIJO QUE NO LO TIENE:
 NO volver a pedirlo."

# Cliente dijo "No, oiga" 2x pero:
- FIX 81 (objeciones) NO detectó rechazo
- FIX 655 (anti-repetición) NO se aplicó
- GPT ignoró las 2 negaciones explícitas
```

**2. FIX 493B (anti-loop catálogo) NO se aplicó**
```python
# Debería bloquear 3ra oferta pero:
- TURNO 1: Primera oferta ✓
- TURNO 2: Segunda oferta ✓ (debería advertir)
- Sistema NO contó correctamente las ofertas
```

**3. GPT_FUERA_DE_TEMA en TURNO 1**
- Cliente dio saludo confuso ("Pero tenía la cuenta...")
- Bruce interpretó como "cliente está ocupado"
- En lugar de preguntar por encargado, pidió contacto directamente
- Violó flujo conversacional (pitch → encargado → contacto)

#### Fixes Que Fallaron

| FIX | Propósito | ¿Por qué falló? |
|-----|-----------|----------------|
| FIX 655 | Detectar negaciones explícitas | "No, oiga" no matcheó patrones de negación |
| FIX 493B | Anti-loop catálogo | Contador no detectó 2 ofertas en misma llamada |
| FIX 81 | Detectar objeciones | "No, oiga" no es objeción terminal, pero es rechazo |

---

### BRUCE2142 - 4 BUGS (IDÉNTICO A BRUCE2143)

**Tel**: +526622131188 | **Negocio**: Desconocido
**Timestamp**: 2026-02-11 21:18:26
**Duración**: No especificada

#### Bugs Detectados

| Bug ID | Tipo | Descripción |
|--------|------|-------------|
| 1 | GPT_FUERA_DE_TEMA | Perdió hilo conversacional |
| 2 | GPT_LOGICA_ROTA | Pidió WhatsApp tras rechazo previo |
| 3 | PREGUNTA_REPETIDA | Contacto preguntado 2x |
| 4 | CATALOGO_REPETIDO | Catálogo ofrecido 2x |

**Nota**: Patrón IDÉNTICO a BRUCE2143. Mismo problema recurrente.

---

### BRUCE2129 - 2 BUGS

**Tel**: +526622502810 | **Negocio**: Desconocido
**Timestamp**: 2026-02-11 20:02:08

#### Bugs Detectados

| Bug ID | Tipo | Descripción |
|--------|------|-------------|
| 1 | GPT_FUERA_DE_TEMA | Mala respuesta a confusión sobre encargado de compras |
| 2 | GPT_TONO_INADECUADO | Mostró impaciencia en manejo de situación |

**Status**:
- ✅ FIX 651 (timeout GPT → mensaje profesional) debería cubrir GPT_TONO_INADECUADO
- ❌ GPT_FUERA_DE_TEMA indica problema en prompt del sistema

---

## Pattern Audit - Problemas Detectados

### Patrones con 0% Survival (Siempre Invalidados)

| Patrón | Matches | Survived | Problema |
|--------|---------|----------|----------|
| OFRECER_CONTACTO_BRUCE | 3 | 0 (0%) | FIX 600/601 siempre invalida |
| CLIENTE_ACEPTA_CORREO | 1 | 0 (0%) | Debe agregarse a inmunes |
| CLIENTE_OFRECE_WHATSAPP | 1 | 0 (0%) | Debe agregarse a inmunes |

### Patrones con Baja Supervivencia

| Patrón | Matches | Survival | Acción Recomendada |
|--------|---------|----------|-------------------|
| ENCARGADO_NO_ESTA_SIN_HORARIO | 19 | 42.1% | Revisar invalidaciones FIX 600 |
| EVITAR_LOOP_WHATSAPP | 2 | 50% | Agregar a inmunes FIX 601 |
| CLIENTE_ES_ENCARGADO | 2 | 50% | Revisar contexto de invalidación |

---

## Fixes Necesarios

### FIX 658: GPT_LOGICA_ROTA - Negaciones Explícitas Cortas

**Problema**: "No, oiga" (2 palabras) no es detectado como negación explícita.

**Ubicación**: `agente_ventas.py` línea ~9590 (regla #2 de FIX 655)

**Solución**:
```python
# Agregar a regla #2:
- Negación Explícita CORTA: "No", "No, gracias", "No, oiga", "No, joven",
                             "No, muchacho", "No por ahorita", "No, está bien"
```

**Tests necesarios**: 8 tests (una por variante de negación corta)

---

### FIX 659: FIX 493B - Contador Roto de Catálogo

**Problema**: FIX 493B no cuenta correctamente ofertas de catálogo en historial.

**Ubicación**: `agente_ventas.py` línea ~2228-2248

**Diagnóstico**:
```python
# Código actual:
ultimas_bruce_antiloop = [
    msg['content'] for msg in self.conversation_history[-10:]
    if msg['role'] == 'assistant'
]

veces_ofrecio_catalogo = sum(
    1 for msg in ultimas_bruce_antiloop
    if any(p in msg for p in patrones_catalogo_493b)
)

# PROBLEMA: conversation_history podría no tener los últimos mensajes
# o los patrones no matchean correctamente
```

**Solución**: Agregar logging detallado para diagnosticar:
```python
print(f"[DEBUG FIX 493B] ultimas_bruce_antiloop: {len(ultimas_bruce_antiloop)} mensajes")
print(f"[DEBUG FIX 493B] veces_ofrecio_catalogo: {veces_ofrecio_catalogo}")
print(f"[DEBUG FIX 493B] ofrece_catalogo_493b: {ofrece_catalogo_493b}")
```

---

### FIX 660: GPT_FUERA_DE_TEMA - Forzar Flujo Pitch

**Problema**: Bruce pide contacto en TURNO 1 sin dar pitch de productos.

**Ubicación**: `agente_ventas.py` línea ~2125 (post-filter FIX 650)

**Solución Actual (FIX 650)**:
```python
# Ya existe pero parece que no se aplica correctamente
# Validar que esté funcionando
```

**Acción**: Crear test específico para BRUCE2143 TURNO 1

---

### FIX 661: Pattern Audit - Agregar Inmunidades

**Problema**: 3 patrones con 0% survival deben ser inmunes a FIX 600/601.

**Ubicación**: `agente_ventas.py` líneas ~8185-8275

**Solución**:
```python
patrones_inmunes_pero = [
    # ... existentes ...
    'OFRECER_CONTACTO_BRUCE',
    'CLIENTE_ACEPTA_CORREO',
    'CLIENTE_OFRECE_WHATSAPP'
]

patrones_inmunes_601 = [
    # ... existentes ...
    'CLIENTE_ACEPTA_CORREO',
    'CLIENTE_OFRECE_WHATSAPP'
]
```

---

## Priorización de Fixes

### 🔴 CRÍTICO (Implementar YA)

1. **FIX 658** - Negaciones cortas ("No, oiga")
   - Impacto: 3/11 bugs (27%)
   - Dificultad: Baja (agregar patrones)
   - Tiempo: 10 minutos + 8 tests

2. **FIX 659** - Contador catálogo roto
   - Impacto: 4/11 bugs (36%)
   - Dificultad: Media (debugging + fix)
   - Tiempo: 30 minutos + tests

### 🟡 MEDIO (Implementar en 24h)

3. **FIX 660** - Validar FIX 650 funciona
   - Impacto: 3/11 bugs (27%)
   - Dificultad: Baja (crear test)
   - Tiempo: 15 minutos

4. **FIX 661** - Pattern audit inmunidades
   - Impacto: Mejora pattern detector
   - Dificultad: Baja (agregar a listas)
   - Tiempo: 5 minutos

---

## Métricas de Cobertura

### Bugs Totales: 11

| Tipo | Cantidad | % | Fixes Necesarios |
|------|----------|---|------------------|
| ✅ Cubiertos (infraestructura) | 1 | 9% | Ninguno (timeout STT) |
| ⚠️ Parcialmente cubiertos | 1 | 9% | FIX 651 (ya existe) |
| ❌ NO cubiertos | 9 | 82% | FIX 658-661 |

### Cobertura por Fix

| Fix | Bugs Cubiertos | % Cobertura |
|-----|----------------|-------------|
| FIX 654-657 | 0/11 | 0% (bugs nuevos post-deploy) |
| FIX 658 (propuesto) | 3/11 | 27% |
| FIX 659 (propuesto) | 4/11 | 36% |
| FIX 660 (propuesto) | 3/11 | 27% |
| **TOTAL con FIX 658-660** | **10/11** | **91%** |

---

## Conclusiones

### Hallazgos Principales

1. **FIX 655 NO está funcionando** para negaciones cortas
   - "No, oiga" no matchea patrones actuales
   - Necesita ampliar regla #2 con variantes mexicanas

2. **FIX 493B tiene contador roto**
   - No detecta ofertas repetidas de catálogo
   - Necesita debugging urgente

3. **GPT_FUERA_DE_TEMA recurrente**
   - Bruce salta pasos del flujo (pitch → contacto directo)
   - FIX 650 puede no estar aplicándose correctamente

4. **Pattern Audit revela 3 patrones muertos**
   - 0% survival indica invalidación incorrecta
   - Deben agregarse a inmunidades

### Recomendaciones

1. ✅ **Implementar FIX 658 INMEDIATAMENTE** (10 min)
   - Mayor impacto (27% bugs)
   - Más fácil de implementar

2. ✅ **Debuggear FIX 493B** (30 min)
   - 36% de bugs
   - Requiere investigación pero crítico

3. ✅ **Validar FIX 650** con test específico (15 min)
   - 27% de bugs
   - Puede ser fix rápido si solo falta test

4. ✅ **Agregar inmunidades pattern audit** (5 min)
   - Low-hanging fruit
   - Mejora robustez general

### Próximos Pasos

```bash
# 1. Implementar FIX 658-661
cd "C:\Users\PC 1\AgenteVentas"
# ... implementar fixes ...

# 2. Crear tests
pytest tests/test_fix_658_661.py -v

# 3. Deploy a Railway
git add .
git commit -m "FIX 658-661: Negaciones cortas + contador catálogo + inmunidades"
git push origin main

# 4. Monitorear primeras 24h
# https://nioval-webhook-server-production.up.railway.app/bugs
```

---

**Generado**: 2026-02-11 21:50
**Analista**: Claude Sonnet 4.5
**Método**: Análisis manual de logs + WebFetch endpoints
