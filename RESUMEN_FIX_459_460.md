# RESUMEN FIX 459/460: Errores de BRUCE1381

## Casos Resueltos

| ID | Error Reportado | Causa Raiz | FIX |
|----|-----------------|------------|-----|
| BRUCE1381 | Le pregunta 2 veces por el encargado | FIX 298/301 no verificaba si ya preguntó | FIX 459 |
| BRUCE1381 | Respuesta incoherente "Claro, espero" | FIX 170 confundió "llame después" con transferencia | FIX 460 |

---

## Problema 1: Doble Pregunta por Encargado

### Escenario BRUCE1381:
```
21:36:05 Bruce: "¿Se encontrará el encargado o encargada de compras?"
21:36:16 Cliente: "Este, mire, por el momento no se"
21:36:18 Bruce: "Claro. ¿Se encontrará el encargado o encargada...?" ← PREGUNTA 2 VECES
```

### Logs del problema:
```
🚨 FIX 298/301: CRÍTICO - Bruce asume cosas
   Mensajes de Bruce: 2 (< 4)
   Bruce iba a decir: 'Entiendo que está ocupado. ¿Le gustaría que le envíe el catá...'
   Respuesta corregida: "Claro. ¿Se encontrará el encargado..."
```

### Causa Raíz
FIX 298/301 detecta que Bruce tiene < 4 mensajes y GPT "asume cosas", entonces fuerza la pregunta por el encargado SIN verificar si Bruce YA la hizo.

### Solución: FIX 459

**Lógica:** Antes de forzar pregunta por encargado, verificar si Bruce ya lo preguntó en los últimos 4 mensajes.

**Código (agente_ventas.py líneas 1449-1479):**
```python
# FIX 459: BRUCE1381 - Verificar si Bruce YA preguntó por el encargado
historial_bruce_459 = ' '.join([
    msg['content'].lower() for msg in self.conversation_history[-4:]
    if msg['role'] == 'assistant'
])
bruce_ya_pregunto_encargado = any(frase in historial_bruce_459 for frase in [
    'encargado de compras', 'encargada de compras',
    '¿se encontrará el encargado', '¿se encuentra el encargado'
])

if bruce_ya_pregunto_encargado:
    print(f"   ✅ FIX 459: Bruce YA preguntó por encargado - NO volver a preguntar")
    # Usar respuesta contextual o de GPT
```

---

## Problema 2: "Claro, espero" Incoherente

### Escenario BRUCE1381:
```
21:36:47 Cliente: "...le está hablando el mostrador...puede marcar en otro"
21:36:47 Bruce: "Claro, espero." ← INCOHERENTE (no es transferencia)
```

### Logs del problema:
```
📞 FIX 170: Cliente va a PASAR al encargado AHORA
   Patrón detectado: 'ahorita'
✅ FIX 170: Bruce esperará (timeout extendido a 20s)
```

### Causa Raíz
FIX 170 detectó "ahorita" en "no se la maneja ahorita" y asumió transferencia. Pero el cliente estaba diciendo que debe LLAMAR DESPUÉS, no que iba a transferir.

### Solución: FIX 460

**Lógica:** Antes de activar transferencia, verificar si el cliente sugiere "llamar después".

**Código (agente_ventas.py líneas 5037-5053):**
```python
# FIX 460: BRUCE1381 - Detectar si cliente dice LLAMAR DESPUÉS vs TRANSFERIR AHORA
cliente_dice_llamar_despues = any(frase in respuesta_lower for frase in [
    'puede marcar', 'llame después', 'marcar en otro', 'llamar en otro',
    'vuelva a llamar', 'otro momento', 'más tarde',
    'el mostrador', 'nada más atendemos', 'no se la maneja'
])

if cliente_dice_llamar_despues:
    print(f"📅 FIX 460: Cliente sugiere LLAMAR DESPUÉS - NO es transferencia")
    # NO activar transferencia - dejar que GPT maneje con despedida apropiada
```

---

## Tests

**Archivo:** `test_fix_459_460.py`

Resultados: 4/4 tests pasados (100%)
- FIX 459: No doble pregunta: OK
- FIX 459: Caso BRUCE1381: OK
- FIX 460: Llamar después vs Transferir: OK
- FIX 460: Caso BRUCE1381: OK

---

## Comportamiento Esperado

### Antes (sin FIX 459/460):
1. Bruce: "¿Se encontrará el encargado?" (primera vez)
2. Cliente: "Por el momento no se..."
3. FIX 298/301 cambia respuesta → Bruce pregunta OTRA VEZ por encargado
4. Cliente: "...puede marcar en otro momento"
5. FIX 170 detecta "ahorita" → Bruce: "Claro, espero" (incorrecto)

### Después (con FIX 459/460):
1. Bruce: "¿Se encontrará el encargado?" (primera vez)
2. Cliente: "Por el momento no se..."
3. **FIX 459: Detecta que Bruce ya preguntó → NO repite pregunta**
4. Bruce: "Entiendo. ¿A qué hora puedo llamar?" (contextual)
5. Cliente: "...puede marcar en otro momento"
6. **FIX 460: Detecta "llamar después" → NO activa transferencia**
7. Bruce usa respuesta de despedida apropiada

---

## Impacto Esperado

1. **Sin preguntas duplicadas:** Bruce no repite "¿Se encontrará el encargado?"
2. **Respuestas coherentes:** "Claro, espero" solo cuando hay transferencia real
3. **Mejor detección de contexto:** Distingue "llamar después" de "transferir ahora"

---

## Archivos Modificados

1. `agente_ventas.py` - FIX 459 (líneas 1449-1479) + FIX 460 (líneas 5037-5053)
2. `test_fix_459_460.py` - Tests de validación (creado)
3. `RESUMEN_FIX_459_460.md` - Este documento (creado)
