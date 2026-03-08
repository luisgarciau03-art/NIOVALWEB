# FIX 205 - CRÍTICO: Respuestas Rápidas en Interrupciones

**Fecha:** 2026-01-13
**Prioridad:** 🚨 CRÍTICA (Producción - UX)
**Estado:** 🔄 EN DESARROLLO

---

## 🔥 PROBLEMA CRÍTICO

### Reporte del Usuario:

```
"Interrumpen a Bruce y tarda 10seg en responder"
```

### Evidencia del Log:

```
🎵 FIX 162A: Generando audio (intento 1/2)
⚠️ FIX 162A: Error en intento 1/2: ApiError
🔄 FIX 162A: Reintentando en 1 segundo...
🎵 FIX 162A: Generando audio (intento 2/2)
⚠️ FIX 162A: Error en intento 2/2: ApiError
❌ FIX 162A: Error generando audio ElevenLabs después de 2 intentos

'message': 'You have 28 credits remaining, while 178 credits are required'
```

**Análisis:**
- Cliente interrumpe
- Bruce intenta generar mensaje de 25 palabras
- ElevenLabs falla (sin créditos suficientes)
- Reintenta 2 veces → +2 segundos
- Cae a audio de relleno "dejeme_ver"
- **Total: ~10 segundos de espera**

### Impacto:

- ❌ Cliente espera 10s sin respuesta coherente
- ❌ Cliente cuelga frustrado
- ❌ Calificación Bruce: 3/10
- ❌ Mala experiencia en interrupciones
- ❌ Sistema consume créditos en mensajes largos innecesarios

---

## 🔍 CAUSA RAÍZ

### Problema 1: Mensajes Demasiado Largos en Interrupciones

**Lo que pasó:**
```
Cliente: [Interrumpe]
Bruce: [Genera mensaje de 25 palabras]
       "Me comunico de la marca nioval, especializada en productos
        de ferretería como griferías, herramientas y cintas.
        ¿Puedo ayudarle con algo específico o enviarle el catálogo?"
ElevenLabs: [Necesita 178 créditos] → FALLA
```

**Lo que debería pasar:**
```
Cliente: [Interrumpe]
Bruce: [Respuesta corta de 5-10 palabras]
       "Sí, dígame" o "¿En qué le puedo ayudar?"
ElevenLabs: [Necesita ~50 créditos] → ÉXITO rápido
```

### Problema 2: Sin Detección de Contexto de Interrupción

El sistema no detecta que:
- Cliente acaba de interrumpir
- Necesita respuesta INMEDIATA
- Debe usar mensaje ultra-corto
- Debe priorizar velocidad sobre contenido

### Problema 3: Retry en Situaciones de Emergencia

Cuando falla ElevenLabs:
- Reintenta automáticamente (FIX 162A)
- Suma 1-2 segundos adicionales
- En interrupciones, cada segundo cuenta
- Debería fallar rápido y usar caché

---

## ✅ SOLUCIÓN PROPUESTA

### Estrategia de 3 Niveles:

#### Nivel 1: Detección de Interrupciones

```python
def es_interrupcion_cliente(self) -> bool:
    """
    Detecta si el cliente acaba de interrumpir a Bruce

    Returns:
        True si última respuesta del cliente fue durante mensaje de Bruce
    """
    # Verificar si hay menos de 2 segundos entre último mensaje de Bruce
    # y respuesta del cliente

    if len(self.conversation_history) < 2:
        return False

    # Obtener últimos mensajes
    ultimos = self.conversation_history[-3:]

    # Patrón de interrupción:
    # 1. Bruce habló
    # 2. Cliente respondió rápidamente (interrumpió)

    if len(ultimos) >= 2:
        penultimo = ultimos[-2]
        ultimo = ultimos[-1]

        if penultimo['role'] == 'assistant' and ultimo['role'] == 'user':
            # Cliente respondió inmediatamente después de Bruce
            # Probablemente es interrupción

            # Palabras típicas de interrupción
            palabras_interrupcion = [
                "espera", "espere", "pero", "momento", "un segundo",
                "perdón", "perdon", "disculpe", "oiga", "oye"
            ]

            respuesta_lower = ultimo['content'].lower()

            if any(palabra in respuesta_lower for palabra in palabras_interrupcion):
                return True

    return False
```

#### Nivel 2: Respuestas Pre-Cacheadas para Interrupciones

**Crear audios ultra-cortos (5-10 palabras):**

```python
RESPUESTAS_RAPIDAS_INTERRUPCION = {
    "general": [
        "Sí, dígame",
        "¿En qué le puedo ayudar?",
        "Perfecto, adelante",
        "Claro, escucho",
        "Dígame"
    ],
    "pregunta": [
        "Sí, ¿qué necesita?",
        "¿Qué desea saber?",
        "Adelante con su pregunta"
    ],
    "objecion": [
        "Entiendo su punto",
        "Claro, lo comprendo",
        "Tiene razón"
    ]
}
```

**Pre-generar cachés:**
```bash
python generar_cache_respuestas_rapidas.py
```

#### Nivel 3: Lógica de Respuesta Rápida

```python
def procesar_respuesta(self, respuesta_cliente: str) -> str:
    """Procesa respuesta con detección de interrupciones"""

    # Agregar al historial
    self.conversation_history.append({
        "role": "user",
        "content": respuesta_cliente
    })

    # FIX 205: Detectar interrupción
    if self.es_interrupcion_cliente():
        print(f"🚨 FIX 205: Interrupción detectada")
        print(f"   Cliente dijo: '{respuesta_cliente}'")
        print(f"   Usando respuesta rápida pre-cacheada...")

        # Seleccionar respuesta rápida apropiada
        if any(q in respuesta_cliente.lower() for q in ["qué", "que", "cómo", "como"]):
            categoria = "pregunta"
        elif any(obj in respuesta_cliente.lower() for obj in ["pero", "no", "espera"]):
            categoria = "objecion"
        else:
            categoria = "general"

        # Usar respuesta pre-cacheada (0s delay)
        import random
        respuesta_rapida = random.choice(RESPUESTAS_RAPIDAS_INTERRUPCION[categoria])

        # Agregar al historial
        self.conversation_history.append({
            "role": "assistant",
            "content": respuesta_rapida
        })

        print(f"✅ FIX 205: Respuesta rápida enviada: '{respuesta_rapida}' (caché, 0s delay)")

        return respuesta_rapida

    # Si no es interrupción, procesar normalmente
    # ... (resto del código existente)
```

---

## 📊 COMPARACIÓN: ANTES vs DESPUÉS

### Escenario: Cliente Interrumpe

**ANTES (10s delay):**
```
Cliente: "Espera, tengo una pregunta"
[Bruce intenta generar 25 palabras]
[ElevenLabs: necesita 178 créditos]
[Intento 1: FALLA → +1s]
[Intento 2: FALLA → +1s]
[Cae a audio relleno "dejeme_ver" → +2s]
Total: ~10 segundos
Cliente: [Cuelga frustrado]
```

**DESPUÉS (<2s delay):**
```
Cliente: "Espera, tengo una pregunta"
[FIX 205: Detecta interrupción]
[Usa respuesta pre-cacheada: "Sí, dígame"]
[Desde caché: 0s delay]
Total: <2 segundos
Cliente: [Continúa conversación]
```

---

## 🎯 BENEFICIOS

### Velocidad:
- ✅ Respuesta en <2s (vs 10s antes)
- ✅ 80% reducción en latencia de interrupciones
- ✅ Cliente no se frustra

### Eficiencia de Créditos:
- ✅ Respuestas cortas: ~50 créditos (vs 178)
- ✅ Pre-cacheadas: 0 créditos
- ✅ Ahorro del 100% en interrupciones

### UX:
- ✅ Bruce responde inmediatamente
- ✅ Conversación fluye naturalmente
- ✅ Cliente siente que lo escuchan

---

## 🔧 IMPLEMENTACIÓN

### Paso 1: Crear Respuestas Rápidas Pre-Cacheadas

```python
# generar_cache_respuestas_rapidas.py

from servidor_llamadas import generar_audio_elevenlabs

RESPUESTAS_RAPIDAS = [
    "Sí, dígame",
    "¿En qué le puedo ayudar?",
    "Perfecto, adelante",
    "Claro, escucho",
    "Dígame",
    "Sí, ¿qué necesita?",
    "¿Qué desea saber?",
    "Adelante con su pregunta",
    "Entiendo su punto",
    "Claro, lo comprendo",
    "Tiene razón"
]

for frase in RESPUESTAS_RAPIDAS:
    cache_key = "_".join(frase.lower().split()[:4])
    print(f"Generando caché: {cache_key}")
    generar_audio_elevenlabs(frase, cache_key, usar_cache_key=cache_key)
    print(f"✅ Caché guardado: {cache_key}")
```

### Paso 2: Modificar `procesar_respuesta()` en agente_ventas.py

```python
# Antes de llamar a GPT, verificar si es interrupción
if self.es_interrupcion_cliente():
    # Usar respuesta rápida pre-cacheada
    return self._respuesta_rapida_interrupcion(respuesta_cliente)

# Si no, procesar normalmente con GPT
# ...
```

### Paso 3: Modificar Retry de ElevenLabs

```python
# En generar_audio_elevenlabs()

# FIX 205: Si es respuesta de interrupción, no reintentar
# Fallar rápido y usar audio de relleno
if palabras < 15 and intento == 1:
    print(f"⚠️ FIX 205: Respuesta corta falló - no reintentar (prioridad velocidad)")
    max_intentos = 1  # Solo 1 intento para respuestas cortas
```

---

## 📋 CACHÉS A PRE-GENERAR

### Categoría: General (Interrupción Neutral)
```
✅ "Sí, dígame"
✅ "Adelante"
✅ "Claro, escucho"
✅ "Dígame"
✅ "Perfecto"
```

### Categoría: Preguntas
```
✅ "¿En qué le puedo ayudar?"
✅ "¿Qué necesita?"
✅ "¿Qué desea saber?"
```

### Categoría: Objeciones
```
✅ "Entiendo"
✅ "Claro, lo comprendo"
✅ "Tiene razón"
```

**Total: 11 audios × ~50 créditos = 550 créditos (una sola vez)**

---

## 🧪 CASOS DE PRUEBA

### Test 1: Interrupción Simple

**Input:**
```
Bruce: "Me comunico de la marca nioval, especializada en..."
Cliente: [Interrumpe] "Espera"
```

**Output Esperado:**
```
🚨 FIX 205: Interrupción detectada
✅ Respuesta rápida: "Sí, dígame" (caché, 0s)
```

### Test 2: Pregunta Durante Presentación

**Input:**
```
Bruce: "Nosotros distribuimos productos de..."
Cliente: [Interrumpe] "¿Qué tipo de productos?"
```

**Output Esperado:**
```
🚨 FIX 205: Interrupción detectada (pregunta)
✅ Respuesta rápida: "¿Qué desea saber?" (caché, 0s)
```

### Test 3: Objeción

**Input:**
```
Bruce: "¿Le gustaría recibir el catálogo?"
Cliente: [Interrumpe] "Pero estoy ocupado"
```

**Output Esperado:**
```
🚨 FIX 205: Interrupción detectada (objeción)
✅ Respuesta rápida: "Entiendo" (caché, 0s)
```

---

## ⚠️ PROBLEMA CRÍTICO: CRÉDITOS

### Del Log:

```
You have 28 credits remaining, while 178 credits are required
```

**Los créditos se están consumiendo muy rápido porque:**

1. **Mensajes muy largos** (25-44 palabras)
   - 25 palabras = 178 créditos
   - 44 palabras = 247 créditos

2. **Sin cachés suficientes**
   - Primeras respuestas no tienen caché
   - Genera audio cada vez

3. **Reintentos consumen doble**
   - Intento 1: consume créditos
   - Intento 2: consume créditos otra vez

### Recomendación:

**Aunque dices que créditos están cargados, se consumen en minutos.**

**Necesitas:**
1. Monitoreo automático (`monitor_creditos_elevenlabs.py`)
2. Alertas cuando < 10,000 créditos
3. Verificar plan: ¿Tiene límite de umbral (threshold)?

---

## 🎯 PLAN DE IMPLEMENTACIÓN

### Fase 1: Respuestas Rápidas (2 horas)

1. Crear `generar_cache_respuestas_rapidas.py`
2. Ejecutar script para pre-generar 11 audios
3. Verificar que cachés existan en `audio_cache/`

### Fase 2: Detección (1 hora)

1. Implementar `es_interrupcion_cliente()`
2. Implementar `_respuesta_rapida_interrupcion()`
3. Integrar en `procesar_respuesta()`

### Fase 3: Optimización Retry (30 min)

1. Modificar FIX 162A para respuestas cortas
2. Solo 1 intento si <15 palabras
3. Fallar rápido para priorizar velocidad

### Fase 4: Testing y Despliegue (30 min)

1. Probar con llamada de prueba
2. Verificar latencia <2s
3. Desplegar a producción

---

## 📊 MÉTRICAS DE ÉXITO

| Métrica | Antes | Después | Mejora |
|---------|-------|---------|--------|
| **Latencia interrupciones** | 10s | <2s | -80% |
| **Créditos por interrupción** | 178 | 0 (caché) | -100% |
| **Tasa de colgadas** | Alta | Baja | -70% |
| **Satisfacción en interrupciones** | Baja | Alta | +++ |

---

**Estado:** 🟡 **DISEÑADO** - Listo para implementar
**Prioridad:** 🔥 **ALTA** - Problema afecta a todas las llamadas con interrupciones
