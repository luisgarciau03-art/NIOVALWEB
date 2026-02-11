# Plan de Validación FIX 646

## Deploy Status
✅ Commit: b3fab3c
✅ Railway: Auto-deploy completado
✅ Servidor: https://nioval-webhook-server-production.up.railway.app/
✅ Tests: 150/150 passed

---

## Escenarios de Validación

### 1. FIX 646A: GPT Anti-Repetición (CRÍTICO)

**Objetivo:** Verificar que Bruce NO repite preguntas ya respondidas

**Escenario A: Encargado No Está**
```
Bruce: "¿Me comunica con el encargado de compras?"
Cliente: "No, no se encuentra, salió"
Bruce: [DEBE pedir WhatsApp/correo, NO volver a preguntar "¿Se encuentra el encargado?"]
```

**Escenario B: Dato Ya Proporcionado**
```
Bruce: "¿Me puede dar su WhatsApp?"
Cliente: "Sí, 33 1234 5678"
Bruce: [DEBE agradecer y continuar, NO volver a pedir "¿Cuál es su WhatsApp?"]
```

**Escenario C: "Dígame" como Go Ahead**
```
Bruce: "Buenos días, habla Bruce de Nioval"
Cliente: "Dígame"
Bruce: [DEBE continuar con pitch, NO preguntar "¿Me decía?"]
```

**Cómo Validar:**
- Hacer llamada de prueba simulando estos escenarios
- Revisar transcripción en historial-llamadas
- Verificar que Bruce NO genera preguntas repetidas
- Buscar logs con "FIX 646A" para confirmar reglas aplicadas

---

### 2. FIX 646B: "Ya Todo" Despedida Mexicana

**Objetivo:** Verificar que Bruce reconoce "ya todo" como despedida

**Escenario:**
```
Bruce: "Le envío el catálogo por WhatsApp entonces"
Cliente: "Ya todo, gracias"
Bruce: [DEBE despedirse, NO continuar conversación]
```

**Variantes a Probar:**
- "Ya todo"
- "Ya está todo" (normalizado a "ya esta todo" por FIX 631)
- "Ya es todo"

**Cómo Validar:**
- Cliente debe decir una de las variantes después de que se prometió el catálogo
- Bruce debe responder con despedida y colgar
- Verificar en logs que detectó "DESPEDIDA_CLIENTE"

---

### 3. FIX 646C: Email Literal (FALSE POSITIVE)

**Objetivo:** Confirmar que Bruce captura emails literales correctamente

**Nota:** Este NO era un bug real, era un false positive del GPT evaluator. La captura de emails literales ya funcionaba.

**Escenario:**
```
Bruce: "¿Me puede dar su correo?"
Cliente: "ferreterialopez@hotmail.com"
Bruce: [DEBE confirmar y repetir email correctamente]
```

**Cómo Validar:**
- Cliente dicta email con formato completo (nombre@dominio.com)
- Verificar que Bruce captura y repite correctamente
- NO debería haber bugs tipo "DATO_SIN_RESPUESTA"

---

### 4. FIX 646D: Patterns Inmunes (0% Survival)

**Objetivo:** Verificar que EVITAR_LOOP_WHATSAPP y CLIENTE_ACEPTA_CORREO no son invalidados

**Escenario A: Loop WhatsApp Evitado**
```
(Contexto: Bruce ya ofreció WhatsApp hace <30s)
Cliente: "Sí, por WhatsApp"
Bruce: [NO debe ofrecer WhatsApp de nuevo, debe confirmar y proceder]
```

**Escenario B: Cliente Acepta Correo**
```
Bruce: "¿Le parece bien que le envíe el catálogo por correo?"
Cliente: "Sí, por correo está bien"
Bruce: [DEBE pedir correo, pattern NO debe ser invalidado por texto largo]
```

**Cómo Validar:**
- Buscar en logs "EVITAR_LOOP_WHATSAPP" o "CLIENTE_ACEPTA_CORREO"
- Verificar que NO aparezca "INVALIDADO por FIX 601"
- Confirmar que el pattern sobrevivió y se usó

---

### 5. FIX 646E: GPT Eval Conteo Turnos

**Objetivo:** Verificar que GPT eval NO genera false positives en conteo de turnos

**Qué Monitorear:**
- En /bugs, buscar bugs con categoría "GPT_EVAL"
- Verificar que NO haya reportes tipo "Bruce mencionó X en turno N" cuando turno N es del CLIENTE
- El prompt ahora tiene instrucciones explícitas de contar solo mensajes de Bruce

**Cómo Validar:**
- Esperar a que se acumulen ~20-30 llamadas nuevas post-deploy
- Revisar /bugs para ver si hay nuevos GPT_EVAL false positives
- Comparar con bugs BRUCE2086 (turno 3 era cliente, no Bruce)

---

## Métodos de Validación

### Opción 1: Llamadas de Prueba Manuales

**Script:**
```bash
cd "C:\Users\PC 1\AgenteVentas"
py llamar_produccion.py +52XXXXXXXXXX "Ferretería Prueba FIX646"
```

**Ventajas:**
- Control total del escenario
- Validación inmediata
- Puede simular casos específicos

**Desventajas:**
- Requiere números de prueba reales
- Twilio cobra por minuto
- No captura casos edge reales del campo

---

### Opción 2: Monitoreo Pasivo de Logs

**URL:** https://nioval-webhook-server-production.up.railway.app/historial-llamadas

**Qué Buscar:**
1. **Llamadas con "GPT_LOGICA_ROTA" ANTES de FIX 646:**
   - IDs: BRUCE2076, BRUCE2079, BRUCE2081, BRUCE2087, BRUCE2091
   - Timestamp: 2026-02-11 antes de deploy

2. **Llamadas DESPUÉS de FIX 646:**
   - Timestamp: 2026-02-11 después de 12:00 PM (hora del deploy)
   - Buscar si hay nuevos "GPT_LOGICA_ROTA"
   - Comparar frecuencia: 69% antes → debería bajar a ~20-30%

**Ventajas:**
- Captura comportamiento real en producción
- No cuesta llamadas de prueba
- Identifica edge cases no anticipados

**Desventajas:**
- Requiere esperar 12-24 horas para suficientes llamadas
- Menos control sobre escenarios específicos

---

## Criterios de Éxito

### FIX 646A: ✅ SI
- 0 bugs nuevos tipo "Bruce repitió pregunta encargado"
- 0 bugs tipo "Bruce repitió solicitud de dato ya proporcionado"
- "Dígame" primer mensaje NO genera "¿Me decía?"

### FIX 646B: ✅ SI
- "Ya todo" / "Ya está todo" / "Ya es todo" detectados como DESPEDIDA_CLIENTE
- Bruce se despide inmediatamente sin continuar conversación

### FIX 646D: ✅ SI
- EVITAR_LOOP_WHATSAPP y CLIENTE_ACEPTA_CORREO NO aparecen como invalidados
- Pattern Audit muestra survival rate > 0% (antes era 0%)

### FIX 646E: ✅ SI
- 0 bugs GPT_EVAL nuevos con conteo de turnos incorrecto
- Bugs tipo BRUCE2086 NO se repiten

---

## Recomendación

**Opción Híbrida (RECOMENDADA):**
1. **Ahora (15 min):** 2-3 llamadas de prueba rápidas para FIX 646A y 646B
2. **Después (24h):** Monitoreo pasivo de logs para validar FIX 646D y 646E

**Números de Prueba:**
- Si tienes números de prueba: úsalos para escenarios A, B, C de FIX 646A
- Si prefieres esperar: los logs naturales validarán todo en 24-48 horas

---

## Siguiente Paso

¿Quieres que haga llamadas de prueba ahora o prefieres esperar a que se acumulen logs naturales?

Si eliges llamadas de prueba, necesito:
- 1-2 números de teléfono de prueba (pueden ser tuyos o de colaboradores)
- Confirmación de que está OK gastar ~5-10 minutos de Twilio (~$0.50-1.00 USD)
