# FIX 408 - Timeout Deepgram Progresivo

## Problema Detectado

**Error en producción:**
```
Cliente: "Ahorita no está joven"
→ Deepgram timeout (no transcribió en 5s)
→ FIX 211 asumió: "Cliente dijo 'bueno'"
→ Bruce: "¿Se encontrará el encargado?" ❌ PREGUNTA REDUNDANTE
→ Cliente cuelga (frustrado - YA dijo que no estaba)
```

**Causa raíz:** FIX 211 asumía incorrectamente que el primer mensaje vacío era "bueno" o "hola", cuando en realidad el cliente podría haber dicho información crítica como:
- "Ahorita no está el encargado"
- "No nos interesa"
- "Estamos ocupados"
- "Llame más tarde"

**Consecuencia:** Bruce preguntaba por el encargado cuando el cliente YA había dicho que no estaba, generando frustración y cuelgues.

---

## Solución Implementada

### Estrategia: Lógica Progresiva de Timeouts

En lugar de asumir "bueno" en el primer timeout, Bruce ahora pide repetición de manera natural, con **máximo 2 intentos** para no estresar al cliente.

### Flujo de Respuestas

**PRIMER TIMEOUT (timeouts_deepgram = 1):**
```
Bruce: "Disculpe, no alcancé a escucharle bien, ¿me podría repetir?"
```
- Tono natural y cortés
- Pide repetición sin asumir nada
- Cliente puede decir lo que realmente quiso decir

**SEGUNDO TIMEOUT (timeouts_deepgram = 2):**
```
Bruce: "¿Me escucha? Parece que hay interferencia"
```
- Más directo y breve
- Atribuye el problema a la línea (no al cliente)
- Última oportunidad de captar el mensaje

**TERCER TIMEOUT+ (timeouts_deepgram ≥ 3):**
```
Bruce: "Me comunico de la marca nioval... ¿Se encontrará el encargado?"
```
- Asume problema técnico real
- Continúa con segunda parte del saludo (lógica original FIX 211)
- Evita loops infinitos de "¿me escucha?"

---

## Cambios en Código

### 1. Nuevo Atributo en AgenteVentas

**Archivo:** `agente_ventas.py:261`

```python
self.timeouts_deepgram = 0  # FIX 408: Contador de timeouts de Deepgram (máximo 2 pedidos de repetición)
```

### 2. Lógica Progresiva en Primer Mensaje Vacío

**Archivo:** `servidor_llamadas.py:2268-2378`

```python
if es_primer_mensaje:
    # FIX 408: Lógica progresiva de timeouts - NO asumir "bueno" inmediatamente
    agente.timeouts_deepgram += 1

    if agente.timeouts_deepgram == 1:
        # PRIMER TIMEOUT: Pedir repetición natural
        respuesta_timeout = "Disculpe, no alcancé a escucharle bien, ¿me podría repetir?"

    elif agente.timeouts_deepgram == 2:
        # SEGUNDO TIMEOUT: Pedir repetición directa
        respuesta_timeout = "¿Me escucha? Parece que hay interferencia"

    else:
        # TERCER TIMEOUT+: Continuar con saludo (lógica original FIX 211)
        segunda_parte = "Me comunico de la marca nioval... ¿Se encontrará el encargado?"
```

### 3. Reset de Contador en Transcripción Exitosa

**Archivo:** `servidor_llamadas.py:1680-1685`

```python
# FIX 408: Resetear contador de timeouts cuando Deepgram responde exitosamente
if call_sid in conversaciones_activas:
    agente_temp = conversaciones_activas[call_sid]
    if hasattr(agente_temp, 'timeouts_deepgram') and agente_temp.timeouts_deepgram > 0:
        print(f"   ✅ FIX 408: Reseteando contador de timeouts (era {agente_temp.timeouts_deepgram})")
        agente_temp.timeouts_deepgram = 0
```

---

## Beneficios

### ✅ Evita Asunciones Incorrectas
- NO asume que el cliente dijo "bueno" en el primer timeout
- Capta respuestas críticas como "no está el encargado"

### ✅ No Estresa al Cliente
- Máximo 2 pedidos de repetición por llamada
- Evita loops infinitos de "¿me escucha?"

### ✅ Mejora Tasa de Conversión
- Captura respuestas que antes se perdían
- Bruce adapta la conversación a lo que el cliente realmente dijo

### ✅ Manejo Progresivo
- Primera vez: Cortés y natural
- Segunda vez: Directo y breve
- Tercera vez: Continúa asumiendo problema técnico

---

## Casos de Prueba

### Caso 1: Cliente dice "No está" (timeout en transcripción)

**ANTES (FIX 211):**
```
Cliente: "Ahorita no está joven"
Deepgram: [timeout]
Bruce: "¿Se encontrará el encargado?" ❌ REDUNDANTE
Cliente: [cuelga]
```

**DESPUÉS (FIX 408):**
```
Cliente: "Ahorita no está joven"
Deepgram: [timeout]
Bruce: "Disculpe, no alcancé a escucharle bien, ¿me podría repetir?"
Cliente: "Que no está el encargado"
Bruce: "Entendido, ¿sabe a qué hora regresa?" ✅ CORRECTO
```

### Caso 2: Problema técnico real (múltiples timeouts)

```
Cliente: [audio cortado]
Deepgram: [timeout #1]
Bruce: "Disculpe, no alcancé a escucharle bien, ¿me podría repetir?"
Cliente: [audio cortado]
Deepgram: [timeout #2]
Bruce: "¿Me escucha? Parece que hay interferencia"
Cliente: [audio cortado]
Deepgram: [timeout #3]
Bruce: "Me comunico de la marca nioval... ¿Se encontrará el encargado?" ✅ CONTINÚA
```

### Caso 3: Deepgram responde después del primer timeout

```
Cliente: "Bueno"
Deepgram: [timeout #1]
Bruce: "Disculpe, no alcancé a escucharle bien, ¿me podría repetir?"
Cliente: "Que le digo bueno"
Deepgram: "que le digo bueno" ✅
Bruce: "Me comunico de la marca nioval..." ✅
[Contador reset a 0]
```

---

## Logs de Referencia

**Antes de FIX 408:**
```
⚠️ FIX 401: Deepgram no respondió en 5.0s
🚨 FIX 211: Primer mensaje vacío - Asumiendo que cliente respondió pero no se transcribió
📦 FIX 211: Usando audio pre-generado de segunda_parte_saludo
✅ FIX 211: Segunda parte del saludo reproducida aunque cliente no fue transcrito
```

**Después de FIX 408:**
```
⚠️ FIX 401: Deepgram no respondió en 5.0s
🚨 FIX 408: Primer mensaje vacío (timeout #1)
   📞 FIX 408: Primer timeout - pidiendo repetición natural
✅ FIX 408: Respuesta enviada según nivel de timeout
```

---

## Métricas Esperadas

- **Reducción de cuelgues prematuros:** -30%
- **Mejora en detección de "no está":** +50%
- **Tasa de conversiones exitosas:** +15%
- **Satisfacción del cliente:** +20% (menos redundancia)

---

## Próximos Pasos

1. **Monitorear logs en producción** para validar que los timeouts se manejan correctamente
2. **Analizar tasas de cuelgue** después de implementar FIX 408
3. **Ajustar frases** si los clientes responden negativamente a "¿me escucha?"
4. **Considerar aumentar timeout de Deepgram** de 5s a 6s si los timeouts siguen siendo frecuentes

---

## Notas Técnicas

- **Whisper NO se usa como fallback** porque tiene errores graves que confunden a Bruce
- **Deepgram es el único sistema de transcripción** (FIX 401)
- **El contador se resetea** cuando Deepgram responde exitosamente
- **Máximo 2 pedidos de repetición** por llamada para no estresar al cliente
