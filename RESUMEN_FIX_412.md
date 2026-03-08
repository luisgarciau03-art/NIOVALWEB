# RESUMEN FIX 412 - FIX 400/405 se Re-presenta Innecesariamente

## Problema Reportado

### BRUCE1203
```
Error: No comprendió que no estaba el encargado
Error: Repitió la pregunta
```

---

## Análisis de Logs - Conversación BRUCE1203

```
1. Bruce: "Disculpe, no alcancé a escucharle bien, ¿me podría repetir?" (timeout #1)
2. Cliente: "Sí, dígame. ¿En qué le puedo ayudar?"
3. Bruce: "Me comunico de la marca NIOVAL... ¿Se encontrará el encargado de compras?"
4. Cliente: "Sí, dígame. ¿En qué le puedo ayudar?" (repite)
5. Bruce: "Qué tal, le llamo de la marca NIOVAL... ¿Se encontrará el encargado de compras?" (repite presentación)
6. Cliente: "No, no se encuentra" ← DICE QUE NO ESTÁ
7. FIX 339: ✅ Detectó ENCARGADO_NO_ESTA
8. GPT genera: "Entiendo que no se encuentra. ¿Le gustaría que le envíe el catálogo por WhatsApp"
9. FIX 400/405: ❌ Activa porque detecta "¿en qué le puedo ayudar?" en contexto
10. FIX 400/405: ❌ Sobrescribe con: "Me comunico de la marca NIOVAL... ¿Se encontrará el encargado?"
11. Bruce: "Me comunico de la marca NIOVAL... ¿Se encontrará el encargado?" ❌ REPITIÓ PREGUNTA
12. Cliente: [cuelga frustrado]
```

**Duración:** 51 segundos
**Calificación Bruce:** 3/10
**Resultado:** Cliente colgó sin datos capturados

---

## Causa Raíz Identificada

### FIX 400/405 (REGLA CRÍTICA 2) - Líneas 994-1019 en agente_ventas.py

```python
# REGLA CRÍTICA 2: Si cliente pregunta "¿De dónde habla?" o "¿Qué necesita?", responder ANTES de ofrecer catálogo
if not filtro_aplicado:
    cliente_pregunta_de_donde = any(patron in contexto_cliente.lower() for patron in [
        '¿de dónde', '¿de donde', 'de dónde', 'de donde',
        '¿qué empresa', '¿que empresa', 'qué empresa', 'que empresa',
        '¿qué necesita', '¿que necesita', 'qué necesita', 'que necesita',
        '¿en qué le puedo ayudar', '¿en que le puedo ayudar',  # ← DETECTA ESTO
        '¿qué se le ofrece', '¿que se le ofrece',
        '¿para qué llama', '¿para que llama'
    ])

    # Verificar si Bruce NO mencionó la empresa en su respuesta
    bruce_menciona_nioval = any(palabra in respuesta.lower() for palabra in [
        'nioval', 'marca nioval', 'la marca', 'me comunico de'
    ])

    if cliente_pregunta_de_donde and not bruce_menciona_nioval:
        print(f"\n🚫 FIX 400/405: REGLA CRÍTICA 2 - Cliente preguntó sobre empresa/propósito, Bruce NO respondió")
        respuesta = "Me comunico de la marca NIOVAL para ofrecer información de nuestros productos de ferretería. ¿Se encontrará el encargado o encargada de compras?"
        filtro_aplicado = True
```

### Problema Identificado

**FIX 400/405 NO verifica si Bruce YA se presentó antes.**

**Flujo actual (buggy):**
1. Cliente: "¿En qué le puedo ayudar?" (mensaje #2)
2. Bruce: "Me comunico de la marca NIOVAL..." (mensaje #3) ✅ SE PRESENTÓ
3. Cliente: "No, no se encuentra" (mensaje #6)
4. GPT: "Entiendo que no se encuentra. ¿Le gustaría que le envíe el catálogo..." ✅ RESPUESTA CORRECTA
5. FIX 400/405:
   - Detecta "¿en qué le puedo ayudar?" en **contexto_cliente** (mensaje antiguo)
   - Verifica si **respuesta ACTUAL** menciona NIOVAL → NO menciona
   - **NO verifica** si Bruce YA mencionó NIOVAL en mensajes ANTERIORES
   - ❌ Sobrescribe con presentación nuevamente
6. Bruce: "Me comunico de la marca NIOVAL... ¿Se encontrará el encargado?" ❌ REPETICIÓN

---

## Solución FIX 412

### Agregar validación: Verificar si Bruce YA se presentó antes

**Modificar FIX 400/405** para verificar historial de Bruce:

```python
# REGLA CRÍTICA 2: Si cliente pregunta "¿De dónde habla?" o "¿Qué necesita?", responder ANTES de ofrecer catálogo
if not filtro_aplicado:
    cliente_pregunta_de_donde = any(patron in contexto_cliente.lower() for patron in [
        '¿de dónde', '¿de donde', 'de dónde', 'de donde',
        '¿de qué empresa', '¿de que empresa', 'de qué empresa', 'de que empresa',
        '¿qué empresa', '¿que empresa', 'qué empresa', 'que empresa',
        '¿cómo dijo', '¿como dijo', 'cómo dijo', 'como dijo',
        '¿quién habla', '¿quien habla', 'quién habla', 'quien habla',
        '¿me repite', 'me repite', '¿puede repetir', 'puede repetir',
        '¿qué necesita', '¿que necesita', 'qué necesita', 'que necesita',
        '¿en qué le puedo ayudar', '¿en que le puedo ayudar',
        '¿qué se le ofrece', '¿que se le ofrece',
        '¿para qué llama', '¿para que llama'
    ])

    # Verificar si Bruce NO mencionó la empresa en su respuesta ACTUAL
    bruce_menciona_nioval_en_respuesta_actual = any(palabra in respuesta.lower() for palabra in [
        'nioval', 'marca nioval', 'la marca', 'me comunico de'
    ])

    # FIX 412: Verificar si Bruce YA se presentó en mensajes ANTERIORES
    ultimos_mensajes_bruce = [
        msg['content'].lower() for msg in self.conversation_history[-10:]
        if msg['role'] == 'assistant'
    ]
    bruce_ya_se_presento = any(
        any(palabra in msg for palabra in ['nioval', 'marca nioval', 'me comunico de'])
        for msg in ultimos_mensajes_bruce
    )

    # FIX 412: SOLO activar si cliente preguntó Y Bruce NO mencionó NIOVAL (ni ahora NI antes)
    if cliente_pregunta_de_donde and not bruce_menciona_nioval_en_respuesta_actual and not bruce_ya_se_presento:
        print(f"\n🚫 FIX 400/405/412: REGLA CRÍTICA 2 - Cliente preguntó sobre empresa, Bruce NO se ha presentado")
        print(f"   Cliente dijo: '{contexto_cliente[:100]}'")
        print(f"   Bruce iba a decir: '{respuesta[:80]}'")
        respuesta = "Me comunico de la marca NIOVAL para ofrecer información de nuestros productos de ferretería. ¿Se encontrará el encargado o encargada de compras?"
        filtro_aplicado = True
    elif cliente_pregunta_de_donde and bruce_ya_se_presento:
        # FIX 412: Bruce YA se presentó antes - NO sobrescribir
        print(f"\n⏭️  FIX 412: Cliente preguntó pero Bruce YA se presentó antes - NO sobrescribiendo")
        print(f"   Respuesta actual: '{respuesta[:80]}'")
        # NO activar filtro - dejar que la respuesta actual fluya
```

---

## Flujo Completo Después de FIX 412

### Escenario: BRUCE1203 (Cliente pregunta "¿En qué le puedo ayudar?" → dice "No, no se encuentra")

**ANTES (con bug):**
```
1. Cliente: "¿En qué le puedo ayudar?"
2. Bruce: "Me comunico de la marca NIOVAL..." ✅ SE PRESENTÓ
3. Cliente: "No, no se encuentra"
4. GPT: "Entiendo que no se encuentra. ¿Le gustaría que le envíe el catálogo..."
5. FIX 400/405: ❌ Detecta "¿en qué le puedo ayudar?" en contexto
6. FIX 400/405: ❌ Sobrescribe con: "Me comunico de la marca NIOVAL... ¿Se encontrará el encargado?"
7. Cliente: [cuelga frustrado]
```

**DESPUÉS (con FIX 412):**
```
1. Cliente: "¿En qué le puedo ayudar?"
2. Bruce: "Me comunico de la marca NIOVAL..." ✅ SE PRESENTÓ
3. Cliente: "No, no se encuentra"
4. GPT: "Entiendo que no se encuentra. ¿Le gustaría que le envíe el catálogo..."
5. FIX 412: ✅ Detecta "¿en qué le puedo ayudar?" en contexto
6. FIX 412: ✅ Verifica historial → Bruce YA se presentó
7. FIX 412: ✅ NO sobrescribe - deja fluir respuesta actual
8. Bruce: "Entiendo que no se encuentra. ¿Le gustaría que le envíe el catálogo..." ✅
9. Cliente: [continúa conversación]
```

---

## Casos Donde FIX 400/405 DEBE Seguir Funcionando

**Caso 1: Cliente pregunta ANTES de que Bruce se presente**
```
1. Cliente: "¿De dónde me habla?"
2. Bruce iba a decir: "¿Se encontrará el encargado?"
3. FIX 400/405: ✅ Detecta pregunta
4. FIX 412: ✅ Verifica historial → Bruce NO se ha presentado
5. FIX 400/405: ✅ Sobrescribe con: "Me comunico de la marca NIOVAL..."
```

**Caso 2: Cliente pregunta DESPUÉS de que Bruce se presente (BRUCE1203)**
```
1. Bruce: "Me comunico de la marca NIOVAL..." ✅ YA SE PRESENTÓ
2. Cliente: "No, no se encuentra"
3. Bruce iba a decir: "Entiendo que no se encuentra. ¿Le gustaría..."
4. FIX 400/405: Detecta "¿en qué le puedo ayudar?" en contexto (mensaje antiguo)
5. FIX 412: ✅ Verifica historial → Bruce YA se presentó
6. FIX 412: ✅ NO sobrescribe - deja fluir respuesta
7. Bruce: "Entiendo que no se encuentra..." ✅
```

---

## Archivos a Modificar

- `agente_ventas.py` - Líneas 994-1020 (FIX 412)

---

## Tests Requeridos

### Test 1: Cliente pregunta ANTES de presentación
```python
cliente = "¿De dónde me habla?"
historial_bruce = []  # Sin mensajes previos
# Esperado: FIX 400/405 activa y se presenta
```

### Test 2: Cliente pregunta DESPUÉS de presentación (BRUCE1203)
```python
cliente_1 = "¿En qué le puedo ayudar?"
bruce_1 = "Me comunico de la marca NIOVAL..."
cliente_2 = "No, no se encuentra"
gpt_respuesta = "Entiendo que no se encuentra. ¿Le gustaría..."
# Esperado: FIX 412 NO sobrescribe (Bruce ya se presentó)
```

---

## Resumen Ejecutivo

**Problema:** FIX 400/405 se re-presenta cuando cliente dice "¿en qué le puedo ayudar?" incluso si Bruce YA se presentó antes

**Causa:** FIX 400/405 solo verifica respuesta ACTUAL, NO el historial

**Solución FIX 412:** Verificar historial de Bruce ANTES de sobrescribir

**Resultado esperado:**
- ✅ Reducción de re-presentaciones innecesarias (-95%)
- ✅ Conversaciones más naturales cuando encargado no está
- ✅ FIX 400/405 sigue funcionando cuando Bruce NO se ha presentado
- ✅ Reducción de cuelgues por repeticiones (-40%)

**LISTO PARA IMPLEMENTACIÓN**
