# RESUMEN FIX 461: Corregir Duplicación de Mensajes de Usuario

## Caso Resuelto

| ID | Error Reportado | Causa Raiz | FIX |
|----|-----------------|------------|-----|
| BRUCE1381 | Mensajes de usuario duplicados en historial | servidor_llamadas.py agregaba mensaje Y procesar_respuesta() también | FIX 461 |

---

## Problema

### Descubierto en Auditoría de Contexto:
```
📝 FIX 68: Últimos 2 mensajes en historial:
   USER: Este, mire, por el momento no se
   USER: Este, mire, por el momento no se  ← DUPLICADO
```

### Causa Raíz

En el caso de **interrupción durante la segunda parte del saludo**:

1. `servidor_llamadas.py` línea 2798: Agregaba mensaje del usuario al historial
2. `procesar_respuesta()` se llamaba porque `respuesta_desde_cache` era None
3. `agente_ventas.py` línea 4314: `procesar_respuesta()` agregaba el MISMO mensaje OTRA VEZ

**Flujo problemático:**
```
bruce_ya_dijo_segunda_parte = True  (línea 2787)
    ↓
usa_segunda_parte_saludo = False    (línea 2795)
    ↓
agente.conversation_history.append({...})  (línea 2798) ← PRIMERA ADICIÓN
    ↓
if not respuesta_desde_cache:  ← Es True (no hay caché)
    ↓
agente.procesar_respuesta(speech_result)  (línea 2841)
    ↓
self.conversation_history.append({...})  (línea 4314) ← SEGUNDA ADICIÓN (DUPLICADO)
```

---

## Solución

### FIX 461: Remover adición duplicada

**Archivo:** `servidor_llamadas.py` líneas 2797-2805

**Cambio:** Comentar/remover la adición del mensaje que causaba duplicación

```python
# FIX 461: BRUCE1381 - NO agregar mensaje aquí
# procesar_respuesta() ya lo agrega en agente_ventas.py línea 4314
# Agregar aquí causaba DUPLICACIÓN del mensaje del usuario
# REMOVIDO:
# agente.conversation_history.append({
#     "role": "user",
#     "content": speech_result
# })
```

---

## Por qué el caso de caché NO tiene duplicación

En el caso de caché (primera respuesta):
1. `bruce_ya_dijo_segunda_parte = False`
2. `respuesta_desde_cache` se asigna
3. `servidor_llamadas.py` línea 2810: Agrega mensaje de usuario
4. `servidor_llamadas.py` línea 2816: Agrega respuesta de caché
5. `if not respuesta_desde_cache:` es **False** → `procesar_respuesta()` NO se llama
6. **Sin duplicación**

---

## Tests

**Archivo:** `test_fix_461.py`

Resultados: 3/3 tests pasados (100%)
- No duplicación mensajes: OK
- Caso BRUCE1381 interrupción: OK
- Flujo caché no afectado: OK

---

## Impacto Esperado

1. **Sin mensajes duplicados:** El historial de conversación tendrá mensajes únicos
2. **GPT recibe contexto limpio:** Sin repeticiones que confundan al modelo
3. **Logs de FIX 68 correctos:** Ya no mostrarán mensajes duplicados

---

## Archivos Modificados

1. `servidor_llamadas.py` - FIX 461 (líneas 2797-2805) - Remover adición duplicada
2. `test_fix_461.py` - Tests de validación (creado)
3. `RESUMEN_FIX_461.md` - Este documento (creado)
