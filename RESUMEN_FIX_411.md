# RESUMEN FIX 411 - Detección Incorrecta "Permítame" como Transferencia

## Problemas Reportados

### BRUCE1198
```
Error: "Claro, espero." / respuesta incoherente
Error: No pasó su número
```

### BRUCE1199
```
Error: Le preguntaron por su nombre y respuesta incoherente
```

---

## Análisis de Logs

### BRUCE1198 - Conversación Completa

```
1. Bruce: "Hola, buen dia"
2. Cliente: "Buenos días."
3. Cliente: "Sí. ¿Bueno?"
4. Bruce: "Me comunico de la marca nioval..."
5. Cliente: "Mire, ahorita de momento no se encuentran, salieron"
   ✅ FIX 339: Detectó ENCARGADO_NO_ESTA
6. Bruce: "Entiendo, no se preocupe. Si prefiere, puedo llamar en otro momento..."
7. Cliente: "Claro que sí. Sí. ¿Bueno?"
8. Bruce: "Claro. Manejamos productos de ferretería..." ❌ REPITIÓ
   ✅ FIX 204: Detectó repetición y regeneró
9. Cliente: "si gusta marcar ahorita en un en un en 5 minutos"
   ❌ FIX 389: Detectó como "ESPERANDO_TRANSFERENCIA"
10. Bruce: "Claro, espero." ❌ INCOHERENTE (cliente NO pidió esperar)
11. Cliente: "lo atienden, él que está ocupada la la casquera"
    ❌ FIX 389: Detectó NUEVAMENTE como transferencia
12. Bruce: "Claro, espero." ❌ REPITIÓ INCOHERENCIA
13. Cliente: "O si gusta dejarme algún número o algo" ← PIDIÓ NÚMERO
14. Deepgram timeout → Bruce pidió repetir → Cliente colgó
```

**Duración:** 78 segundos
**Calificación Bruce:** 3/10
**Resultado:** Cliente colgó sin datos capturados

---

### BRUCE1199 - Conversación Completa

```
1. Cliente: "Sí, buenos días, dígame."
2. Cliente: "¿Bueno?"
3. Bruce: "Me comunico de la marca nioval..."
4. Cliente: "¿Bueno?"
5. Bruce: "Claro. Manejamos productos de ferretería..."
6. Cliente: "A ver, permítame. ¿Cuánto es tu nombre?" ← PREGUNTA POR NOMBRE
   ❌ FIX 389: Detectó "permítame" como "ESPERANDO_TRANSFERENCIA"
7. Bruce: "Claro, espero." ❌ INCOHERENTE (debía dar su nombre)
8. Cliente colgó (frustrado)
```

**Duración:** 29 segundos
**Calificación Bruce:** 3/10
**Resultado:** Cliente colgó sin datos capturados

---

## Causa Raíz Identificada

### FIX 389/405 - Líneas 431-452 en agente_ventas.py

```python
# Detectar si cliente pide esperar (SOLO si NO es rechazo)
patrones_espera = ['permítame', 'permitame', 'espere', 'espéreme', 'espereme',
                  'un momento', 'un segundito', 'ahorita', 'tantito']

# ...

if tiene_patron_espera and not tiene_negacion and not es_pregunta_directa:
    self.estado_conversacion = EstadoConversacion.ESPERANDO_TRANSFERENCIA
    return
```

### Problema 1: "permítame" es demasiado amplio

El patrón detecta **"permítame"** sin diferenciar contextos:

**❌ Falsos Positivos (NO es transferencia):**
- **"Permítame. ¿Cuál es tu nombre?"** → PREGUNTA por nombre
- **"Permítame. ¿De dónde habla?"** → PREGUNTA por empresa
- **"Si gusta marcar en 5 minutos"** → SOLICITUD de llamar después

**✅ Verdaderos Positivos (SÍ es transferencia):**
- **"Permítame, lo comunico"** → Transferencia real
- **"Permítame verificar"** → Espera (sin pregunta después)
- **"Un momento, por favor"** → Espera

---

### Problema 2: No valida contexto DESPUÉS de "permítame"

**FIX 399** solo valida preguntas directas **dentro del mensaje**, pero NO valida:
1. Preguntas sobre **nombre** ("¿Cuál es tu nombre?", "¿Cómo te llamas?")
2. Solicitudes de **llamar después** ("en 5 minutos", "más tarde", "luego")
3. Solicitudes de **dejar número** ("déjame un número", "dame tu teléfono")

**Código actual (líneas 446-455):**
```python
preguntas_directas = [
    '¿de dónde', '¿de donde', 'de dónde', 'de donde',
    '¿quién habla', '¿quien habla', 'quién habla', 'quien habla',
    # ... (NO incluye preguntas sobre NOMBRE)
]

es_pregunta_directa = any(preg in mensaje_lower for preg in preguntas_directas)

# Verificar que NO sea negación Y NO sea pregunta directa
if not any(neg in mensaje_lower for neg in ['no está', 'no esta']) and not es_pregunta_directa:
    self.estado_conversacion = EstadoConversacion.ESPERANDO_TRANSFERENCIA
```

---

## Solución FIX 411

### Cambio 1: Expandir detección de preguntas que NO son transferencia

**Agregar patrones de pregunta por nombre:**
```python
preguntas_directas = [
    # Existentes
    '¿de dónde', '¿de donde', 'de dónde', 'de donde',
    '¿quién habla', '¿quien habla', 'quién habla', 'quien habla',

    # FIX 411: Preguntas por NOMBRE (caso BRUCE1199)
    '¿cuál es tu nombre', '¿cual es tu nombre', 'cuál es tu nombre', 'cual es tu nombre',
    '¿cómo te llamas', '¿como te llamas', 'cómo te llamas', 'como te llamas',
    '¿cuánto es tu nombre', '¿cuanto es tu nombre',  # Deepgram a veces transcribe "cuál" como "cuánto"
    '¿tu nombre', 'tu nombre',
    '¿su nombre', 'su nombre',
]
```

### Cambio 2: Detectar solicitudes de "llamar después"

**Agregar patrones de NO transferencia:**
```python
# FIX 411: Solicitudes de llamar después (caso BRUCE1198)
solicita_llamar_despues = [
    'marcar en', 'llamar en',  # "Si gusta marcar en 5 minutos"
    'marcar más tarde', 'llamar más tarde',
    'marcar después', 'llamar después',
    'marcar luego', 'llamar luego',
    'en 5 minutos', 'en un rato',
    'más tarde', 'más tardecito',
]

es_solicitud_llamar_despues = any(patron in mensaje_lower for patron in solicita_llamar_despues)

if es_solicitud_llamar_despues:
    print(f"📊 FIX 411: Cliente pide LLAMAR DESPUÉS (no transferencia)")
    print(f"   Mensaje: '{mensaje_cliente}' - GPT debe agendar o despedirse")
    # NO activar ESPERANDO_TRANSFERENCIA
    return  # Dejar que GPT maneje
```

### Cambio 3: Detectar solicitudes de número de Bruce

**Agregar patrones de solicitud de contacto:**
```python
# FIX 411: Cliente pide número/contacto de Bruce (caso BRUCE1198)
pide_numero_bruce = [
    'déjame un número', 'dejame un numero',
    'déjame algún número', 'dejame algun numero',
    'dame un número', 'dame un numero',
    'tu número', 'su número',
    'tu teléfono', 'su telefono',
    'tu whatsapp', 'su whatsapp',
    'dejarme número', 'dejarme numero',
]

cliente_pide_numero = any(patron in mensaje_lower for patron in pide_numero_bruce)

if cliente_pide_numero:
    print(f"📊 FIX 411: Cliente PIDE NÚMERO de Bruce")
    print(f"   Mensaje: '{mensaje_cliente}' - GPT debe dar WhatsApp 33 1234 5678")
    # NO activar ESPERANDO_TRANSFERENCIA
    return  # Dejar que GPT maneje
```

---

## Implementación Completa FIX 411

### Ubicación: agente_ventas.py, líneas 429-456

**ANTES (buggy):**
```python
else:
    # Detectar si cliente pide esperar (SOLO si NO es rechazo)
    patrones_espera = ['permítame', 'permitame', 'espere', 'espéreme', 'espereme',
                      'un momento', 'un segundito', 'ahorita', 'tantito']

    tiene_patron_espera = any(patron in mensaje_lower for patron in patrones_espera)

    if tiene_patron_espera:
        # FIX 399: Verificar que NO sea pregunta directa
        preguntas_directas = [
            '¿de dónde', '¿de donde', 'de dónde', 'de donde',
            '¿quién habla', '¿quien habla', 'quién habla', 'quien habla',
            # ... (NO incluye preguntas sobre NOMBRE)
        ]

        es_pregunta_directa = any(preg in mensaje_lower for preg in preguntas_directas)

        # Verificar que NO sea negación Y NO sea pregunta directa
        if not any(neg in mensaje_lower for neg in ['no está', 'no esta']) and not es_pregunta_directa:
            self.estado_conversacion = EstadoConversacion.ESPERANDO_TRANSFERENCIA
            return
```

**DESPUÉS (FIX 411):**
```python
else:
    # Detectar si cliente pide esperar (SOLO si NO es rechazo)
    patrones_espera = ['permítame', 'permitame', 'espere', 'espéreme', 'espereme',
                      'un momento', 'un segundito', 'ahorita', 'tantito']

    tiene_patron_espera = any(patron in mensaje_lower for patron in patrones_espera)

    if tiene_patron_espera:
        # FIX 411: Verificar que NO sea solicitud de llamar después
        solicita_llamar_despues = [
            'marcar en', 'llamar en',  # "Si gusta marcar en 5 minutos"
            'marcar más tarde', 'llamar más tarde',
            'marcar después', 'llamar después',
            'marcar luego', 'llamar luego',
            'en 5 minutos', 'en un rato', 'en unos minutos',
            'más tarde', 'más tardecito', 'al rato',
        ]

        es_solicitud_llamar_despues = any(patron in mensaje_lower for patron in solicita_llamar_despues)

        if es_solicitud_llamar_despues:
            print(f"📊 FIX 411: Cliente pide LLAMAR DESPUÉS (no transferencia)")
            print(f"   Mensaje: '{mensaje_cliente}' - GPT debe agendar o despedirse")
            # NO activar ESPERANDO_TRANSFERENCIA
            return  # Dejar que GPT maneje

        # FIX 411: Verificar que NO sea solicitud de número de Bruce
        pide_numero_bruce = [
            'déjame un número', 'dejame un numero',
            'déjame algún número', 'dejame algun numero',
            'dame un número', 'dame un numero',
            'tu número', 'su número',
            'tu teléfono', 'su telefono',
            'tu whatsapp', 'su whatsapp',
            'dejarme número', 'dejarme numero',
            'dejarme algún', 'dejarme algun',
        ]

        cliente_pide_numero = any(patron in mensaje_lower for patron in pide_numero_bruce)

        if cliente_pide_numero:
            print(f"📊 FIX 411: Cliente PIDE NÚMERO de Bruce")
            print(f"   Mensaje: '{mensaje_cliente}' - GPT debe dar WhatsApp")
            # NO activar ESPERANDO_TRANSFERENCIA
            return  # Dejar que GPT maneje

        # FIX 411: Expandir preguntas directas (incluir NOMBRE)
        preguntas_directas = [
            '¿de dónde', '¿de donde', 'de dónde', 'de donde',
            '¿quién habla', '¿quien habla', 'quién habla', 'quien habla',
            '¿quién es', '¿quien es', 'quién es', 'quien es',
            '¿de qué empresa', '¿de que empresa',
            '¿qué empresa', '¿que empresa',
            # FIX 411: Preguntas por NOMBRE (caso BRUCE1199)
            '¿cuál es tu nombre', '¿cual es tu nombre', 'cuál es tu nombre', 'cual es tu nombre',
            '¿cómo te llamas', '¿como te llamas', 'cómo te llamas', 'como te llamas',
            '¿cuánto es tu nombre', '¿cuanto es tu nombre',  # Deepgram transcribe "cuál" como "cuánto"
            '¿tu nombre', 'tu nombre',
            '¿su nombre', 'su nombre',
            '¿cómo se llama', '¿como se llama',
            '¿cuál es su nombre', '¿cual es su nombre',
        ]

        es_pregunta_directa = any(preg in mensaje_lower for preg in preguntas_directas)

        if es_pregunta_directa:
            print(f"📊 FIX 411: 'Permítame' detectado pero es PREGUNTA DIRECTA - NO es transferencia")
            print(f"   Mensaje: '{mensaje_cliente}' - GPT debe responder la pregunta")
            # NO activar ESPERANDO_TRANSFERENCIA
            return  # Dejar que GPT maneje

        # Verificar que NO sea negación ("no está ahorita")
        if not any(neg in mensaje_lower for neg in ['no está', 'no esta', 'no se encuentra']):
            self.estado_conversacion = EstadoConversacion.ESPERANDO_TRANSFERENCIA
            print(f"📊 FIX 339/399/405/411: Estado → ESPERANDO_TRANSFERENCIA")
            return
```

---

## Flujo Completo Después de FIX 411

### Escenario 1: BRUCE1199 (Pregunta por nombre)

```
1. Cliente: "A ver, permítame. ¿Cuánto es tu nombre?"
2. FIX 411: Detecta "permítame" + "tu nombre"
3. FIX 411: Identifica como PREGUNTA DIRECTA (no transferencia)
4. GPT responde: "Mi nombre es Bruce, de la marca NIOVAL. ¿Le gustaría recibir..."
5. ✅ Conversación continúa naturalmente
```

### Escenario 2: BRUCE1198 (Llamar después)

```
1. Cliente: "Si gusta marcar en 5 minutos"
2. FIX 411: Detecta "marcar en" (solicitud de llamar después)
3. FIX 411: NO activa ESPERANDO_TRANSFERENCIA
4. GPT responde: "Perfecto, le llamo en 5 minutos. ¿Me confirma el número?"
5. ✅ Bruce agenda llamada correctamente
```

### Escenario 3: BRUCE1198 (Pide número)

```
1. Cliente: "O si gusta dejarme algún número o algo"
2. FIX 411: Detecta "dejarme número" (pide contacto de Bruce)
3. FIX 411: NO activa ESPERANDO_TRANSFERENCIA
4. GPT responde: "Claro, mi WhatsApp es 33 1234 5678. ¿Le envío el catálogo?"
5. ✅ Bruce proporciona su número
```

### Escenario 4: Transferencia REAL (debe seguir funcionando)

```
1. Cliente: "Permítame, lo comunico con el encargado"
2. FIX 411: Detecta "permítame" pero NO hay pregunta directa NI solicitud
3. FIX 411: Activa ESPERANDO_TRANSFERENCIA ✅
4. Bruce: "Claro, espero."
5. ✅ Funcionalidad de transferencia preservada
```

---

## Archivos Modificados

- `agente_ventas.py` - Líneas 429-456 (FIX 411)

---

## Tests Requeridos

### Test 1: Pregunta por nombre
```python
cliente = "A ver, permítame. ¿Cuál es tu nombre?"
# Esperado: NO activar ESPERANDO_TRANSFERENCIA
# Esperado: GPT responde con nombre
```

### Test 2: Llamar después
```python
cliente = "Si gusta marcar en 5 minutos"
# Esperado: NO activar ESPERANDO_TRANSFERENCIA
# Esperado: GPT agenda llamada
```

### Test 3: Pide número de Bruce
```python
cliente = "O si gusta dejarme algún número"
# Esperado: NO activar ESPERANDO_TRANSFERENCIA
# Esperado: GPT da WhatsApp
```

### Test 4: Transferencia REAL (no romper)
```python
cliente = "Permítame, lo comunico"
# Esperado: SÍ activar ESPERANDO_TRANSFERENCIA
# Esperado: Bruce dice "Claro, espero."
```

---

## Resumen Ejecutivo

**Problema:** FIX 389/405 detecta "permítame" como transferencia sin validar contexto

**3 casos de falsos positivos identificados:**
1. **Pregunta por nombre** - "Permítame. ¿Cuál es tu nombre?" (BRUCE1199)
2. **Solicitud de llamar después** - "Si gusta marcar en 5 minutos" (BRUCE1198)
3. **Solicitud de número de Bruce** - "Déjame algún número" (BRUCE1198)

**Solución FIX 411:**
1. Expandir preguntas directas (incluir NOMBRE)
2. Detectar solicitudes de llamar después
3. Detectar solicitudes de número de Bruce
4. NO activar transferencia en estos 3 casos

**Resultado esperado:**
- ✅ Reducción de respuestas incoherentes "Claro, espero." en -90%
- ✅ Bruce responde preguntas sobre su nombre correctamente
- ✅ Bruce agenda llamadas cuando cliente pide llamar después
- ✅ Bruce proporciona su WhatsApp cuando cliente lo solicita
- ✅ Transferencias REALES siguen funcionando

**LISTO PARA IMPLEMENTACIÓN**
