# Auditoría Post FIX 646/647 - 2026-02-11

## Resumen Ejecutivo

**Período:** 2026-02-11 12:00 PM (FIX 646) → 2026-02-11 19:30 PM
**Duración:** 7.5 horas
**Total Bugs Detectados:** 12
**Estado:** ⚠️ **CRÍTICO** - 100% de bugs son POST-FIX 646

---

## 📊 Métricas Generales

| Métrica | Valor | Objetivo | Estado |
|---------|-------|----------|--------|
| **Bugs totales** | 12 | <5 | 🔴 CRÍTICO |
| **GPT_LOGICA_ROTA** | 3 (25%) | <10% | 🟡 MEJORÓ vs 69% |
| **CLIENTE_HABLA_ULTIMO** | 2 (17%) | 0% | 🔴 NUEVO |
| **GPT_FUERA_DE_TEMA** | 4 (33%) | <15% | 🔴 ALTO |
| **Bugs HIGH severity** | 7 (58%) | <20% | 🔴 CRÍTICO |

**Conclusión:** FIX 646 REDUJO GPT_LOGICA_ROTA de 69% → 25% ✅ pero aparecieron **bugs nuevos** ⚠️

---

## 🔴 Bugs Críticos (HIGH Severity)

### 1. CLIENTE_HABLA_ULTIMO (2 bugs)

**BRUCE2112** (19:02:35)
```
CLIENTE: "No, no hay ahorita, en esta hora no hay"
BRUCE: [SILENCIO - NO RESPONDIÓ]
```

**BRUCE2111** (18:58:39)
```
CLIENTE: "tienes que hablar a la sucursal de Sahuayo"
BRUCE: [SILENCIO - NO RESPONDIÓ]
```

**Causa Raíz:**
- Cliente da información útil (encargado NO ESTÁ / OTRA SUCURSAL)
- Bruce detecta esto pero NO genera respuesta de despedida o cierre apropiado
- La llamada queda colgada sin cierre

**Impacto:** MUY ALTO - Cliente queda con mala experiencia (Bruce "ghosteó")

---

### 2. GPT_LOGICA_ROTA (3 bugs - 25% vs 69% antes)

**BRUCE2106** (18:52:20)
```
Turno 3: Cliente mencionó contacto
Turno 4: Bruce pidió el contacto DE NUEVO
```

**BRUCE2104** (18:48:49)
```
Turno 1: Cliente dio número de teléfono
Turno 2: Bruce pidió el número DE NUEVO
```

**BRUCE2098** (18:40:47) - ✅ **YA SOLUCIONADO CON FIX 647**
```
Cliente: "No estoy autorizado"
Bruce: "¿Me puede dar el número?" [turno 4]
```

**Análisis:**
- FIX 646A regla #2 dice: "dato ya proporcionado → NO pedir de nuevo"
- ¿Por qué sigue pasando?
  - Posible: GPT no está detectando que el dato fue proporcionado
  - Posible: El dato se proporcionó de forma indirecta ("llame al 3312345678")
  - Posible: Timeout GPT → respuesta vacía → fallback genérico

---

## 🟡 Bugs Moderados (MEDIUM Severity)

### 3. GPT_FUERA_DE_TEMA (4 bugs - 33%)

**BRUCE2112** (19:02:36)
```
Turno 1: Bruce no dio información relevante sobre productos ferreteros
```

**BRUCE2106** (18:52:20)
```
Turno 3: No entendió respuesta del cliente, pidió información duplicada
```

**BRUCE2100** (18:44:05)
```
Turno 2: Continuó oferta después de que cliente dijo que NO
```

**BRUCE2094** (18:34:13)
```
Turno 1: No dio información ferretera antes de preguntar por encargado
```

**Causa Raíz:**
- Problema de PROMPT: Bruce debe dar pitch de productos ANTES de pedir encargado
- FIX 646A solo cubre anti-repetición, NO cubre ORDEN del flujo conversacional

---

### 4. GPT_TONO_INADECUADO (2 bugs - 17%)

**BRUCE2097** (18:38:06) y **BRUCE2096** (18:36:58)
```
Bruce mencionó "problemas técnicos" sin profesionalismo
```

**Causa Raíz:**
- Timeout GPT → mensaje de error genérico al cliente
- FIX 643 registra "problemas técnicos" en tracker pero NO mejora el mensaje

---

## 📋 Pattern Audit - Hallazgos Críticos

### Patterns con 0% Survival (Candidatos FIX 601 Inmunidad)

| Pattern | Matches | Survivors | Rate | Acción Requerida |
|---------|---------|-----------|------|------------------|
| **OFRECER_CONTACTO_BRUCE** | 2 | 0 | 0.0% | 🔴 **ELIMINAR O INMUNIZAR** |
| CLIENTE_ACEPTA_CORREO | 1 | 0 | 0.0% | ✅ **YA INMUNE (FIX 646D)** |
| EVITAR_LOOP_WHATSAPP | 1 | 0 | 0.0% | ✅ **YA INMUNE (FIX 646D)** |

### Pattern con Bajo Survival (42.9%)

| Pattern | Matches | Survivors | Rate | Observación |
|---------|---------|-----------|------|-------------|
| **ENCARGADO_NO_ESTA_SIN_HORARIO** | 14 | 6 | **42.9%** | 🟡 8 de 14 invalidados - investigar |

**Recomendación:**
- OFRECER_CONTACTO_BRUCE tiene 2 matches, 0 survival → muy malo
- Revisar por qué este pattern se activa pero luego se invalida
- ¿Es por FIX 600 (splitter adversativo)? ¿FIX 601 (complejidad)?

---

## 🎯 Recomendaciones de Fixes

### FIX 648 (CRÍTICO): CLIENTE_HABLA_ULTIMO - Cierre Apropiado

**Problema:** Cliente dice algo útil (encargado NO ESTÁ, OTRA SUCURSAL) → Bruce NO responde

**Solución Propuesta:**
1. Detectar en pattern detector casos donde cliente da cierre natural:
   - "No hay ahorita"
   - "Tienes que hablar a otra sucursal"
   - "No está disponible"
2. Generar respuesta de cierre apropiada:
   - "Perfecto, entonces le marco más tarde. Muchas gracias."
   - "Entendido, voy a contactar a esa sucursal. Que tenga buen día."
3. NO dejar la llamada colgada sin respuesta

**Archivos:**
- `agente_ventas.py` línea ~7500-8000 (pattern detector)
- `servidor_llamadas.py` línea ~4000-4500 (despedida_final handler)

---

### FIX 649 (ALTO): GPT_LOGICA_ROTA - Detección Indirecta de Datos

**Problema:** Cliente dice "llame al 33-1234-5678" → Bruce pide número DE NUEVO

**Causa Raíz:** FIX 646A regla #2 asume dato fue proporcionado DIRECTAMENTE
- ✅ "Mi WhatsApp es 3312345678" → detectado
- ❌ "Llame al 3312345678" → NO detectado (indirecto)
- ❌ "Puede marcar al 33-1234-5678" → NO detectado (indirecto)

**Solución Propuesta:**
Mejorar FIX 646A regla #2 para cubrir formas indirectas:

```python
# REGLA 2 MEJORADA:
"Si el cliente ya proporcionó un dato (DIRECTA o INDIRECTAMENTE):
   - Directo: 'Mi WhatsApp es 3312345678'
   - Indirecto: 'Llame al 3312345678', 'Puede marcar al...', 'El número es...'
 NO volver a pedirlo. El dato YA está capturado."
```

---

### FIX 650 (MEDIO): OFRECER_CONTACTO_BRUCE - 0% Survival

**Problema:** Pattern OFRECER_CONTACTO_BRUCE tiene 2 matches, 0 survivors

**Investigación Requerida:**
1. Revisar logs donde este pattern se activó
2. Verificar qué FIX lo invalidó (600? 601? 602?)
3. Decidir:
   - ¿Agregar a patrones_inmunes_601?
   - ¿Eliminar pattern (false positive)?
   - ¿Mejorar pattern (muy amplio)?

---

### FIX 651 (MEDIO): GPT_FUERA_DE_TEMA - Orden Conversacional

**Problema:** Bruce pregunta por encargado SIN dar pitch de productos primero

**Análisis:**
- FIX 646A cubre anti-repetición, NO cubre ORDEN del flujo
- Necesitamos validar que Bruce NO pregunte por encargado en turno 1
- Debe dar pitch mínimo: "Somos distribuidores de productos ferreteros..."

**Solución Propuesta:**
Post-filter que verifica:
```python
if turno == 1 and "encargado de compras" in respuesta_gpt:
    if "distribuidores" not in respuesta_gpt and "productos" not in respuesta_gpt:
        # Override: agregar pitch antes de preguntar
        respuesta = f"{PITCH_MINIMO} {respuesta_gpt}"
```

---

### FIX 652 (BAJO): GPT_TONO_INADECUADO - Mensaje Error Profesional

**Problema:** Timeout GPT → "Tengo problemas técnicos" (poco profesional)

**Solución:**
Mejorar mensaje de fallback cuando hay timeout GPT:

**Actual:**
```
"Disculpe, tengo problemas técnicos. Voy a terminar la llamada."
```

**Propuesto:**
```
"Disculpe, tengo problemas con la conexión en este momento.
¿Le puedo enviar el catálogo por WhatsApp y lo contacto más tarde?"
```

---

## 📈 Métricas de Éxito FIX 646/647

### ✅ Logros

1. **GPT_LOGICA_ROTA reducido:** 69% → 25% (⬇️ 44 puntos porcentuales)
2. **FIX 647 implementado en 6h:** Edge case BRUCE2098 detectado y solucionado rápidamente
3. **156 tests passed:** Suite de regresión completa mantiene estabilidad

### ⚠️ Challenges

1. **Bugs nuevos aparecieron:** CLIENTE_HABLA_ULTIMO (2), GPT_FUERA_DE_TEMA (4)
2. **GPT_LOGICA_ROTA no eliminado:** 3 bugs persisten (formas indirectas de datos)
3. **Pattern survival bajo:** ENCARGADO_NO_ESTA_SIN_HORARIO solo 42.9%

---

## 🔄 Plan de Acción

### Inmediato (HOY)

1. ✅ **FIX 648:** CLIENTE_HABLA_ULTIMO cierre apropiado
2. ✅ **FIX 649:** GPT_LOGICA_ROTA detección indirecta de datos
3. ⏳ **Investigar:** OFRECER_CONTACTO_BRUCE 0% survival

### Corto Plazo (24-48h)

4. ⏳ **FIX 650:** Decidir sobre OFRECER_CONTACTO_BRUCE
5. ⏳ **FIX 651:** GPT_FUERA_DE_TEMA orden conversacional
6. ⏳ **FIX 652:** Mensaje error profesional

### Monitoreo Continuo

- Esperar 50-100 llamadas más con FIX 648/649 deployed
- Comparar % GPT_LOGICA_ROTA: 25% → objetivo <10%
- Validar que CLIENTE_HABLA_ULTIMO baje a 0%

---

## 📝 Conclusiones

### Positivo ✅

- FIX 646/647 **SÍ FUNCIONÓ** para casos cubiertos (69% → 25%)
- Velocidad de respuesta excelente (FIX 647 en 6h post-deploy)
- Tests de regresión previenen regressions

### A Mejorar ⚠️

- **Edge cases siguen apareciendo:** formas indirectas de proporcionar datos
- **Bugs nuevos emergieron:** CLIENTE_HABLA_ULTIMO, GPT_FUERA_DE_TEMA
- **Pattern audit indica problemas:** 3 patterns con 0% o <50% survival

### Próximo Paso Recomendado

Implementar **FIX 648 + FIX 649** hoy mismo para atacar los 2 bugs más críticos:
1. CLIENTE_HABLA_ULTIMO (17% de bugs)
2. GPT_LOGICA_ROTA formas indirectas (25% de bugs)

Si ambos se eliminan → reducción potencial de **42% de bugs actuales**

---

**Fecha Auditoría:** 2026-02-11 19:30 PM
**Auditor:** Claude Sonnet 4.5
**Siguiente Revisión:** 2026-02-12 12:00 PM (después de FIX 648/649)
