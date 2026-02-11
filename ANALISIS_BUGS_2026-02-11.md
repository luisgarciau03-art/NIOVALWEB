# ANÁLISIS COMPLETO DE BUGS - 2026-02-11

## RESUMEN EJECUTIVO
- **Total bugs detectados:** 13
- **Críticos:** 1 (BRUCE_MUDO)
- **Altos:** 4 (CLIENTE_HABLA_ULTIMO, GPT_RESPUESTA_INCORRECTA x2, GPT_FUERA_DE_TEMA)
- **Medios:** 8 (GPT_LOGICA_ROTA x5, PREGUNTA_REPETIDA, PITCH_REPETIDO, GPT_FUERA_DE_TEMA)

---

## BUG #1 - BRUCE2075: BRUCE_MUDO (CRÍTICO)

### **Descripción:**
TwiML enviado 1x pero audio **NUNCA** fetcheado por Twilio.

### **CallSid:**
`CA6a1929b394f8e55b25fb75c3810c7715`

### **Log Evidence:**
```
FIX 630C: webhook-voz TwiML (784 bytes): ...Play>https://nioval-webhook-server-produ...
[CRITICO] BRUCE_MUDO: TwiML enviado 1x pero audio fetcheado 0x
```

### **Causa Raíz:**
Mismo problema que FIX 630 (BRUCE2064). Twilio no hizo GET request al audio URL después de recibir TwiML 200 OK.

### **Posibles causas:**
1. **Transient Twilio network issue**
2. **ProxyFix (FIX 630A) no funcionó** - URL sigue siendo HTTP en lugar de HTTPS
3. **Audio URL malformada** - Railway truncó la URL en el TwiML
4. **Timeout del lado de Twilio** - Tardó en fetchear y el audio expiró

### **Solución Propuesta - FIX 646:**
**No hay solución de código necesaria**. FIX 630A/B/C ya tiene logging completo.
**Acción:** Monitorear si se repite. Si ocurre >3 veces, contactar soporte Twilio.

---

## BUG #2 - BRUCE2076, BRUCE2081: GPT_LOGICA_ROTA ("Dígame")

### **Conversación BRUCE2076:**
```
1. Cliente: "Dígame."
2. Cliente: "Dígame." (repetido)
3. Bruce: (pitch completo)
4. Bruce: "Sí, le preguntaba, ¿se encontrara el encargado o encargada de compras?"
```

### **Conversación BRUCE2081:**
```
1. Cliente: "Ocho, buenos días."
2. Bruce: (pitch completo con pregunta encargado)
3. Cliente: "Dígame."
4. Bruce: "Sí, le preguntaba, ¿se encontrara el encargado?"
```

### **Causa Raíz:**
**FIX 621B** ya detecta "Dígame" después de pregunta Bruce → repite pregunta.
**PERO** está fallando cuando:
1. Cliente dice "Dígame" **ANTES** de que Bruce termine el pitch completo
2. Bruce interpreta "Dígame" como "no entendí" en lugar de "go ahead"

### **Problema GPT:**
GPT está tratando "Dígame" como **confusión** en lugar de **invitación a continuar**.

### **Solución Propuesta - FIX 646:**
Mejorar FIX 621B para detectar "Dígame" en **cualquier contexto** (no solo después de pregunta):
- Si Bruce ya hizo pitch → NO repetir
- Si "Dígame" es **primer mensaje** cliente → continuar normal (no es confusión)

---

## BUG #3 - BRUCE2078: MÚLTIPLES BUGS

### **Bugs detectados:**
1. ❌ PREGUNTA_REPETIDA: "¿me comunica con el encargado?" 2x
2. ❌ PITCH_REPETIDO: Pitch NIOVAL 2x
3. ❌ GPT_RESPUESTA_INCORRECTA: "No dio info clara sobre productos"
4. ❌ GPT_FUERA_DE_TEMA: "Mencionó problemas técnicos"

### **Conversación:**
```
1. Cliente: "Dígame."
2. Bruce: (pitch completo)
3. Bruce: "Mi nombre es Bruce... ¿Me comunica con el encargado?" ← RE-SALUDO
4. Cliente: "¿De dónde habla, perdón?"
5. Cliente: ""
6. Cliente: "¿Y qué productos ofrece o?"
7. Bruce: "Distribuimos productos... ¿Se encuentra el encargado?" ← 2da vez
8. Cliente: "O checar algún catálogo?"
9. Bruce: "Claro, puedo enviarle el catálogo..."
```

### **Causa Raíz:**
**RE-SALUDO** en turno 3 → GPT perdió contexto → repitió pitch.

**Posible trigger:**
- Cliente dijo "" (vacío) en turno 5
- FIX 577 fallback generó RE-SALUDO en lugar de continuar conversación

### **Solución Propuesta - FIX 646:**
FIX 577 (fallback GPT vacío) NO debe generar RE-SALUDO si:
- Ya hizo pitch inicial (<30s antes)
- Cliente ya respondió algo (turnos > 2)

---

## BUG #4 - BRUCE2079, BRUCE2081: GPT_LOGICA_ROTA (Repite pregunta encargado)

### **BRUCE2079:**
```
1. Cliente: "Buenos días."
2. Bruce: (pitch + pregunta encargado)
3. Cliente: "No se encuentra."
4. Bruce: "¿Me podría proporcionar el WhatsApp del encargado?"
5. Cliente: ""
6. Cliente: "No."
7. Bruce: "Claro. ¿Se encontrará el encargado...?" ← REPITE
```

### **BRUCE2081:**
```
3. Cliente: "Dígame."
4. Bruce: "¿Se encontrara el encargado?"
5. Cliente: "No está Ángel... encargado de vacaciones..."
6. Bruce: "Entendido. ¿Me podría proporcionar un número de WhatsApp...?" ← OK
```

### **Causa Raíz:**
**FIX 493 (anti-loop encargado)** NO está funcionando.

**FIX 493 debería:**
- Detectar que Bruce ya preguntó por encargado 1+ veces
- NO permitir preguntar 2da vez si cliente dijo "No está/No se encuentra"

### **Problema:**
FIX 493 solo previene en **post-filter**, pero GPT ya genera la pregunta.

### **Solución Propuesta - FIX 646:**
Agregar en **system prompt** de GPT:
```
REGLA CRÍTICA: Si el cliente ya indicó que el encargado NO ESTÁ (no se encuentra,
salió, está de vacaciones, no está disponible), NO volver a preguntar por el encargado.
Proceder a pedir WhatsApp/correo del encargado o agendar callback.
```

---

## BUG #5 - BRUCE2080: CLIENTE_HABLA_ULTIMO ("Ya todo")

### **Conversación:**
```
1. Cliente: "Órale."
2. Bruce: "Perfecto. Le llamo para ofrecerle nuestro catálogo... ¿Le gustaría recibirlo por WhatsApp o correo?"
3. Cliente: "" (vacío)
4. Cliente: "" (vacío)
5. Cliente: "" (vacío)
6. Cliente: "Ya todo"
← Bruce NUNCA respondió
```

### **Causa Raíz:**
"Ya todo" NO está en ningún pattern detector.
GPT no entendió "Ya todo" = despedida/rechazo.

### **¿Es un bug real?**
**SÍ** - Bruce debió responder algo tipo:
- "Entendido, muchas gracias. Que tenga buen día."
- "Perfecto, cualquier cosa estamos a la orden."

### **Solución Propuesta - FIX 646:**
Agregar a `patrones_despedida` o `patrones_rechazo`:
```python
'ya todo', 'ya está todo', 'ya es todo'
```

---

## BUG #6 - BRUCE2086: GPT_FUERA_DE_TEMA ("problemas técnicos")

### **Conversación:**
```
1. Cliente: "Avenida, Afrodita, Aferreria Abascal."
2. Bruce: "¿Bueno? Buenos días. Me comunico de NIOVAL... ¿Se encontrará el encargado?"
3. Cliente: "Administración dos. Sucursal Morelos, Le agradecemos su preferencia."
```

### **GPT Eval:**
> "Bruce mencionó problemas técnicos en turno 3"

### **Análisis:**
**FALSE POSITIVE** - Solo hay 3 turnos, Bruce habló 1 vez (turno 2).
NO hay turno 3 de Bruce. El turno 3 es del CLIENTE.

### **Causa Raíz:**
GPT eval está contando mal los turnos o confundiendo roles.

### **Solución Propuesta - FIX 646:**
Mejorar FIX 641 (prompt GPT eval) para ser más explícito:
```
Al analizar, cuenta SOLO los mensajes de Bruce (rol: assistant).
Turno 1 de Bruce = primer mensaje de Bruce
Turno 2 de Bruce = segundo mensaje de Bruce
NO cuentes mensajes del cliente.
```

---

## BUG #7 - BRUCE2087: GPT_LOGICA_ROTA (No captura correo)

### **Conversación:**
```
2. Cliente: "Sí. ¿En qué podemos ayudarle? Vamos a ayudarle."
3. Bruce: "Me comunico de NIOVAL... ¿Se encuentra el encargado de compras disponible?"
4. Cliente: "Quiere mandarle información al correo electrónico de Ferretería La Fuente... ferreterialafuente@hotmail.com"
5. Bruce: "Entendido. ¿Me podría proporcionar el correo electrónico de Ferretería La Fuente?" ← NO CAPTURÓ
6. Cliente: "Arroba Hotmail punto com. El correo de ferreterialafuente@hotmail.com."
7. Bruce: "Perfecto, ya lo tengo anotado."
```

### **Causa Raíz:**
Cliente dictó correo COMPLETO en turno 4:
`"ferreterialafuente@hotmail.com"`

**PERO** Bruce NO lo capturó → preguntó de nuevo.

**Problema:**
1. Pattern detector NO detectó email (FIX 617B solo convierte "arroba" → "@")
2. GPT NO capturó email en `lead_data["email"]`
3. FIX 616B (pre-check FIX 500) NO detectó que email ya fue dado

### **Solución Propuesta - FIX 646:**
Mejorar FIX 617B para detectar emails con formato literal:
```python
# Detectar emails literales (sin "arroba" verbal)
email_regex_literal = r'\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b'
if re.search(email_regex_literal, texto_cliente):
    # Capturar y almacenar
```

---

## BUG #8 - BRUCE2074: GPT_RESPUESTA_INCORRECTA (Menor)

### **Descripción:**
"Bruce mencionó 'nioval' en lugar de 'NIOVAL' con mayúsculas"

### **Análisis:**
**Bug cosmético** - No afecta funcionalidad.

### **Solución:**
No prioritario. Si se quiere fix:
- Agregar a system prompt: "SIEMPRE escribe 'NIOVAL' en mayúsculas"
- Post-filter: `respuesta.replace('nioval', 'NIOVAL')`

---

## PATTERN AUDIT - PROBLEMAS DETECTADOS

### **1. EVITAR_LOOP_WHATSAPP: 0% survival**
- 1 match, 0 survivals
- Siempre invalidado por FIX 600/601
- **Acción:** Agregar a `patrones_inmunes_pero` y `patrones_inmunes_601`

### **2. CLIENTE_ACEPTA_CORREO: 0% survival**
- 1 match, 0 survivals
- Siempre invalidado
- **Acción:** Revisar diseño del patrón o agregar a inmunes

### **3. ENCARGADO_NO_ESTA_SIN_HORARIO: 30% survival**
- 10 matches, solo 3 survivals (70% invalidado)
- **Más usado pero más invalidado**
- **Acción:** Considerar agregar a `patrones_inmunes_601` (umbral complejidad)

---

## PRIORIDADES DE FIX 646

### **Prioridad 1: GPT_LOGICA_ROTA (5 casos similares)**
**Problema:** Bruce repite preguntas sobre encargado/correo cuando cliente ya respondió.

**Solución:**
1. Mejorar system prompt con reglas explícitas
2. Fortalecer FIX 493 (anti-loop encargado)
3. Mejorar captura de datos (email literal)

### **Prioridad 2: "Ya todo" y "Dígame"**
**Problema:** Patrones mexicanos no reconocidos.

**Solución:**
1. Agregar "ya todo" a despedidas
2. Mejorar FIX 621B para "Dígame" en cualquier contexto

### **Prioridad 3: Patterns con 0% survival**
**Problema:** EVITAR_LOOP_WHATSAPP y CLIENTE_ACEPTA_CORREO siempre invalidados.

**Solución:**
Agregar a listas de inmunidad.

### **Prioridad 4: GPT Eval false positives**
**Problema:** BRUCE2086 - GPT eval cuenta mal los turnos.

**Solución:**
Mejorar FIX 641 prompt con instrucciones explícitas de conteo.

---

## MÉTRICAS DE BUGS

| Tipo de Bug | Cantidad | % del Total |
|-------------|----------|-------------|
| GPT_LOGICA_ROTA | 5 | 38% |
| GPT_FUERA_DE_TEMA | 2 | 15% |
| GPT_RESPUESTA_INCORRECTA | 2 | 15% |
| CLIENTE_HABLA_ULTIMO | 1 | 8% |
| BRUCE_MUDO | 1 | 8% |
| PREGUNTA_REPETIDA | 1 | 8% |
| PITCH_REPETIDO | 1 | 8% |

**Conclusión:** 69% de bugs son problemas de **lógica conversacional de GPT**.
