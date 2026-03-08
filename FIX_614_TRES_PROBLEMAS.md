# FIX 614: Tres Problemas Críticos de BRUCE2029

## Problema #1: Negación "NO necesitaría esperar" no detectada
**Línea**: ~2884 en agente_ventas.py  
**Cliente dijo**: "No necesitaría esperar que vuelva."  
**Bruce respondió**: "Claro, espero." (INCORRECTO)

**Causa raíz**:
- Patrón `r'espera'` (línea 2890) detecta "esperar"
- Patrones de negación (línea 2860-2882) son muy específicos: "no gracias", "no está", etc.
- Falta patrón genérico para "NO + verbo + esperar"

**Solución**:
Agregar patrones de negación para verbos modales + esperar:
```python
r'no\s+(?:necesit[aá]|pod[rí]|deber[ií]|quier[oa]|puedes?|puede)[a-z]*\s+esperar',  # "no necesitaría esperar"
r'no\s+(?:necesit[aá]|pod[rí]|deber[ií]|quier[oa])[a-z]*\s+que\s+.*esperar',  # "no necesitaría que esperar"
```

## Problema #2: Repetición idéntica sin contexto
**Cliente**: "¿Necesitas esperar que vuelva?"  
**Bruce**: "Claro, espero." (SEGUNDA VEZ - INCOHERENTE)

**Causa raíz**:
No hay validación de respuestas idénticas consecutivas (anti-loop)

**Solución**:
Antes de generar respuesta, verificar si Bruce ya dijo exactamente lo mismo:
```python
# Verificar últimas 2 respuestas de Bruce
ultimos_bruce = [msg['content'] for msg in self.conversation_history[-4:] if msg['role'] == 'assistant']
if len(ultimos_bruce) >= 2 and ultimos_bruce[-1] == ultimos_bruce[-2]:
    # Bruce repitió EXACTAMENTE - escalar a GPT
    print(f"[EMOJI] FIX 614: Bruce repitió respuesta idéntica - escalar a GPT")
    return None  # Forzar GPT
```

## Problema #3: Pregunta del cliente interpretada como afirmación
**Cliente pregunta**: "¿Necesitas esperar que vuelva?"  
**Bruce**: "Claro, espero." (IGNORA QUE ES PREGUNTA)

**Causa raíz**:
El patrón de espera detecta "esperar" sin validar si es pregunta del cliente

**Solución**:
NO activar "Claro, espero" si el cliente hace una PREGUNTA:
```python
# FIX 614: NO activar espera si cliente hace PREGUNTA con "esperar"
es_pregunta = '¿' in ultimo_cliente or ultimo_cliente.strip().endswith('?')
if (cliente_pide_espera or cliente_pide_espera_contexto) and not tiene_negacion and not es_persona_nueva_estado and not es_pregunta:
```

## Implementación

1. Agregar patrones de negación (línea ~2882)
2. Agregar validación anti-repetición (línea ~2905)
3. Agregar validación de preguntas (línea ~2909)
4. Testear con frase exacta: "No necesitaría esperar que vuelva"
5. Testear con pregunta: "¿Necesitas esperar que vuelva?"

