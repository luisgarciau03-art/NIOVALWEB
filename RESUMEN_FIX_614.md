# FIX 614: BRUCE2029 - Tres Problemas Críticos de Detección

## Fecha
2026-02-08

## Problema Raíz
Análisis de llamada BRUCE2029 reveló tres problemas críticos:

### Problema #1: Negación "NO necesitaría esperar" no detectada
**Cliente dijo**: "No necesitaría esperar que vuelva."  
**Bruce respondió**: "Claro, espero." (INCORRECTO)

**Causa**: Patrón `r'espera'` detectaba "esperar" pero patrones de negación no capturaban "NO + verbo modal + esperar"

### Problema #2: Repetición idéntica sin contexto
**Cliente**: "¿Necesitas esperar que vuelva?"  
**Bruce**: "Claro, espero." (SEGUNDA VEZ - loop)

**Causa**: No había validación anti-repetición de respuestas idénticas

### Problema #3: Pregunta interpretada como afirmación
**Cliente pregunta**: "¿Necesitas esperar que vuelva?"  
**Bruce**: "Claro, espero." (ignora que es pregunta)

**Causa**: Patrón de espera no validaba si cliente hacía PREGUNTA

## Implementación

### 1. Nuevos patrones de negación (línea ~2883)
```python
# FIX 614: BRUCE2029 - Detectar "NO + verbo modal + esperar"
r'no\s+(?:necesit|pod|deber|quier|puedes?|puede)[a-záéíóúüñ]*\s+esperar',
r'no\s+(?:necesit|pod|deber|quier)[a-záéíóúüñ]*\s+que\s+.*esperar',
```

**Casos cubiertos**:
- "No necesitaría esperar"
- "No podría esperar"
- "No debería esperar"  
- "No quisiera esperar"

### 2. Validación de preguntas (línea ~2912)
```python
# FIX 614: BRUCE2029 - NO activar si cliente hace PREGUNTA
es_pregunta = '¿' in ultimo_cliente or ultimo_cliente.strip().endswith('?')
```

### 3. Validación anti-repetición (línea ~2915)
```python
# FIX 614: BRUCE2029 - NO activar si Bruce ya dijo "Claro, espero" (anti-loop)
ultimos_bruce_614 = [
    msg['content'].lower() for msg in self.conversation_history[-4:]
    if msg['role'] == 'assistant'
]
bruce_ya_dijo_espero_614 = any('claro, espero' in msg or 'claro espero' in msg for msg in ultimos_bruce_614[-2:])
```

### 4. Condición actualizada (línea ~2920)
```python
if (cliente_pide_espera or cliente_pide_espera_contexto) and not tiene_negacion and not es_persona_nueva_estado and not es_pregunta and not bruce_ya_dijo_espero_614:
    respuesta = "Claro, espero."
```

### 5. Logging mejorado (línea ~2926)
```python
elif cliente_pide_espera and es_pregunta:
    print(f"\n[EMOJI] FIX 614.1: NO activar espera - Cliente hace PREGUNTA: '{ultimo_cliente}'")
elif cliente_pide_espera and bruce_ya_dijo_espero_614:
    print(f"\n[EMOJI] FIX 614.2: NO activar espera - Bruce YA dijo 'Claro, espero' - evitar loop")
```

## Tests
✅ Test 1: "No necesitaría esperar que vuelva." → NO activa "Claro, espero"  
✅ Test 2: "¿Necesitas esperar que vuelva?" → NO activa "Claro, espero"  
✅ Test 3: "No podría esperar." → NO activa "Claro, espero"  
✅ Test 4: "Espérame un momento." → SÍ activa "Claro, espero"  
✅ Test 5: "Permítame un segundo." → SÍ activa "Claro, espero"  

**Resultado**: 5/5 tests PASS

## Archivos Modificados
- `agente_ventas.py` (líneas ~2883, ~2912, ~2915, ~2920, ~2926)
- `test_fix_614.py` (nuevo archivo de tests)
- `FIX_614_TRES_PROBLEMAS.md` (documentación)
- `analisis_bruce2029.txt` (análisis de llamada)

## Impacto
- ✅ Reduce falsos positivos en "Claro, espero"
- ✅ Elimina loops de respuestas idénticas
- ✅ Mejora detección de negaciones contextuales
- ✅ Respeta preguntas del cliente

## Próximos Pasos
1. Deploy a Railway
2. Monitorear logs para validar FIX 614.1 y FIX 614.2
3. Actualizar MEMORY.md con FIX 614

