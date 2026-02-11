# SESIÓN 2026-02-08: FIX 614 - Análisis y Corrección BRUCE2029

## PROBLEMA REPORTADO
Usuario reportó dos llamadas problemáticas:
- **BRUCE2029**: ✅ Analizada y corregida
  - Bruce no entendió "salió a comer"
  - Entró en modo espera sin necesidad
  - Respuestas y preguntas incoherentes
- **BRUCE2028**: ❌ No existe en logs (solo BRUCE2029 disponible)

## ANÁLISIS BRUCE2029 (73 segundos, resultado: Nulo)

### Conversación Completa
1. **[02:08:32]** Cliente: "¿Qué tal? Buen día."  
   Bruce: "Me comunico de la marca nioval, más que nada quería brindar informacion de nuestros productos ferreteros, ¿Se encontrara el encargado o encargada de compras?"

2. **[02:08:43]** Cliente: "Sí, no, bueno,"  
   **[02:08:44]** Bruce: "Disculpe, ¿me puede repetir eso último?" (FIX 577: fallback)

3. **[02:08:52]** Cliente: "Sí, no, bueno, no, no es cierto, salió a comer."  
   **[02:08:54]** Bruce: "Disculpe, tiene razón. ¿Me confirma el WhatsApp del encargado para enviarle el catálogo?"  
   ✅ **CORRECTO**: Patrón "salió a comer" SÍ se detectó, Bruce pidió WhatsApp (apropiado)

4. **[02:09:06]** Cliente: "No, un estrés para No necesitaría esperar que vuelva."  
   **[02:09:08]** Bruce: "Claro, espero."  
   ❌ **PROBLEMA #1**: Negación "NO necesitaría esperar" NO fue detectada

5. **[02:09:12]** Cliente: "¿Necesitas esperar que vuelva?"  
   **[02:09:14]** Bruce: "Claro, espero."  
   ❌ **PROBLEMA #2**: Pregunta interpretada como afirmación
   ❌ **PROBLEMA #3**: Bruce repitió respuesta idéntica (loop)

6. **[02:09:20-02:09:40]** Múltiples silencios → Cuelgan

## DIAGNÓSTICO TÉCNICO

### Problema #1: Negación "NO necesitaría esperar" no detectada
**Línea**: ~2884 en agente_ventas.py  
**Causa**: Patrón `r'espera'` detectaba "esperar" pero patrones de negación no capturaban "NO + verbo modal + esperar"  
**Patrón faltante**: "no necesitaría/podría/debería/quisiera esperar"

### Problema #2: Pregunta interpretada como afirmación
**Causa**: El patrón de espera detecta "esperar" sin validar si es pregunta del cliente  
**Faltante**: Validación de "¿" o "?" en texto del cliente

### Problema #3: Repetición idéntica sin contexto
**Causa**: No había validación anti-repetición de respuestas idénticas  
**Faltante**: Verificar últimos 2 mensajes de Bruce antes de generar respuesta

## SOLUCIÓN IMPLEMENTADA: FIX 614

### 1. Nuevos patrones de negación (línea ~2883)
```python
# FIX 614: BRUCE2029 - Detectar "NO + verbo modal + esperar"
r'no\s+(?:necesit|pod|deber|quier|puedes?|puede)[a-záéíóúüñ]*\s+esperar',
r'no\s+(?:necesit|pod|deber|quier)[a-záéíóúüñ]*\s+que\s+.*esperar',
```

**Casos cubiertos**:
- ✅ "No necesitaría esperar"
- ✅ "No podría esperar"
- ✅ "No debería esperar"
- ✅ "No quisiera esperar"

**IMPORTANTE**: Usar `[a-záéíóúüñ]*` en lugar de `[a-z]*` para capturar acentos en español

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

## TESTS REALIZADOS

✅ **Test #1**: "No necesitaría esperar que vuelva." → NO activa "Claro, espero"  
✅ **Test #2**: "¿Necesitas esperar que vuelva?" → NO activa "Claro, espero"  
✅ **Test #3**: "No podría esperar." → NO activa "Claro, espero"  
✅ **Test #4**: "Espérame un momento." → SÍ activa "Claro, espero" (válido)  
✅ **Test #5**: "Permítame un segundo." → SÍ activa "Claro, espero" (válido)  

**Resultado**: 5/5 tests PASS

## ARCHIVOS MODIFICADOS

1. **agente_ventas.py** (5 secciones):
   - Línea ~2883: Nuevos patrones de negación
   - Línea ~2912: Validación de preguntas
   - Línea ~2915: Validación anti-repetición
   - Línea ~2920: Condición actualizada
   - Línea ~2926: Logging mejorado

2. **Nuevos archivos**:
   - `test_fix_614.py` (5 tests unitarios)
   - `RESUMEN_FIX_614.md` (resumen ejecutivo)
   - `FIX_614_TRES_PROBLEMAS.md` (análisis detallado)
   - `analisis_bruce2029.txt` (análisis de llamada)

3. **Actualizado**:
   - `MEMORY.md` (FIX 614 + 3 lecciones aprendidas)

## DEPLOY

- **Commit**: c0979b9
- **Mensaje**: "FIX 614: BRUCE2029 - Detección de negaciones y preguntas en 'Claro, espero'"
- **Branch**: main
- **Push**: ✅ Exitoso a Railway
- **Auto-deploy**: En progreso

## IMPACTO ESPERADO

✅ **Reduce falsos positivos** en "Claro, espero"  
✅ **Elimina loops** de respuestas idénticas  
✅ **Mejora detección** de negaciones contextuales  
✅ **Respeta preguntas** del cliente  

## MONITOREO POST-DEPLOY

1. Buscar en logs: `FIX 614.1` (cliente hace pregunta)
2. Buscar en logs: `FIX 614.2` (loop detectado)
3. Validar que "No necesitaría esperar" NO active "Claro, espero"
4. Validar que preguntas con "¿" NO activen "Claro, espero"

## PRÓXIMOS PASOS

1. ✅ Commit y push (completado)
2. ✅ Actualizar MEMORY.md (completado)
3. ⏳ Esperar deploy de Railway (~2-3 min)
4. 🔍 Hacer llamada de prueba y revisar logs
5. 📊 Monitorear próximas 10 llamadas para validar FIX 614

## NOTAS

- **BRUCE2028** NO existe en logs (solo BRUCE2029 disponible)
- Azure Speech Services funcionando correctamente como STT primario
- Deepgram como fallback secundario
- Todos los tests pasaron antes de deploy

