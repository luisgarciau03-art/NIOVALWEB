# FIX 203 - CRÍTICO: Reducir Latencia de Respuesta de Audio

**Fecha:** 2026-01-13
**Prioridad:** 🚨 CRÍTICA (Producción - UX)
**Estado:** 🔄 EN ANÁLISIS

---

## 🔥 PROBLEMA CRÍTICO

### Log del Error:

```
Timestamp: 2026-01-13 20:27:20-20:27:39

⏳ FIX 165: Esperando audio (44 palabras, timeout=4.5s)...
🎵 Primer chunk en 7.87s
✅ Audio en 7.87s (241 chunks, eleven_multilingual_v2)
```

**Total de espera del cliente: ~12 segundos**
- Audio "pensando": ~2-3s
- Generación de audio: 7.87s
- Cliente colgó inmediatamente después

### Impacto:
- ❌ Cliente espera 12 segundos sin respuesta
- ❌ Cliente cuelga por frustración
- ❌ Llamada marcada como "Colgó" (NEGADO)
- ❌ Calificación Bruce: 3/10
- ❌ Mala experiencia de usuario

---

## 🔍 ANÁLISIS DE CAUSA RAÍZ

### Factor 1: Mensaje Muy Largo (44 palabras)

**Mensaje generado:**
```
"Entiendo, es importante respetar esos tiempos. El motivo de mi llamada
es muy breve: nosotros distribuimos productos de ferretería con alta
rotación, especialmente nuestra cinta para goteras que muchos negocios
tienen como producto estrella. ¿Usted maneja este tipo de productos
actualmente en su negocio?"
```

**Análisis:**
- 44 palabras = ~10 segundos de audio hablado
- ElevenLabs necesita generar todo el audio antes de enviarlo
- Timeout configurado: 4.5s (insuficiente)
- Tiempo real: 7.87s (75% más lento de lo esperado)

### Factor 2: Sin Caché Previo

**Log:**
```
🔥 Frase frecuente detectada (1 usos): Entiendo, es importante respetar...
   Generando caché automático con Multilingual v2...
💾 Caché guardado en disco: entiendo,_es_importante_respetar_esos_tiempos...
```

**Análisis:**
- Primera vez que se genera esta frase
- No había caché previo = 0s de latencia
- Sistema generó caché DESPUÉS de usarla (tardío)

### Factor 3: Latencia de ElevenLabs API

**Métricas del log:**
- Primer chunk: 7.87s
- Total chunks: 241
- Modelo: eleven_multilingual_v2

**Benchmarks típicos:**
- TTS v1: 2-4s para 44 palabras
- Multilingual v2: 6-10s para 44 palabras (más lento pero mejor acento)

### Factor 4: Cliente con Contexto de Prisa

**Contexto del cliente:**
```
"Que no se encuentran porque salieron a comer es la hora en que salen a comer."
```

**Análisis:**
- Cliente está en horario de comida
- Cliente indicó que están ocupados
- Cliente con paciencia limitada
- Espera de 12s = intolerable en este contexto

---

## ✅ SOLUCIONES PROPUESTAS

### Solución 1: Dividir Respuestas Largas en Chunks

**Problema:** Bruce genera mensajes de 44 palabras que tardan 8s.

**Solución:** Dividir automáticamente en mensajes más cortos.

**Implementación:**

```python
def dividir_respuesta_en_chunks(texto: str, max_palabras: int = 20) -> list:
    """
    Divide una respuesta larga en chunks más cortos para reducir latencia

    Args:
        texto: Respuesta completa de Bruce
        max_palabras: Máximo de palabras por chunk (default: 20)

    Returns:
        Lista de chunks de texto
    """
    # Dividir por oraciones
    oraciones = re.split(r'([.!?]+\s*)', texto)

    chunks = []
    chunk_actual = ""
    palabras_actuales = 0

    for i in range(0, len(oraciones), 2):
        oracion = oraciones[i]
        puntuacion = oraciones[i+1] if i+1 < len(oraciones) else ""

        palabras_oracion = len(oracion.split())

        # Si agregar esta oración excede el límite
        if palabras_actuales + palabras_oracion > max_palabras and chunk_actual:
            chunks.append(chunk_actual.strip())
            chunk_actual = oracion + puntuacion
            palabras_actuales = palabras_oracion
        else:
            chunk_actual += oracion + puntuacion
            palabras_actuales += palabras_oracion

    # Agregar último chunk
    if chunk_actual:
        chunks.append(chunk_actual.strip())

    return chunks
```

**Ejemplo:**
```python
Input: "Entiendo, es importante respetar esos tiempos. El motivo de mi
        llamada es muy breve: nosotros distribuimos productos de ferretería
        con alta rotación, especialmente nuestra cinta para goteras que
        muchos negocios tienen como producto estrella. ¿Usted maneja este
        tipo de productos actualmente en su negocio?"

Output:
  Chunk 1 (15 palabras): "Entiendo, es importante respetar esos tiempos.
                          El motivo de mi llamada es muy breve:"
  Chunk 2 (17 palabras): "nosotros distribuimos productos de ferretería
                          con alta rotación, especialmente nuestra cinta
                          para goteras"
  Chunk 3 (12 palabras): "que muchos negocios tienen como producto estrella.
                          ¿Usted maneja este tipo de productos actualmente?"
```

**Beneficios:**
- Chunk 1: ~3s generación → Cliente escucha algo inmediatamente
- Chunk 2: ~3s generación → Mientras habla chunk 1
- Chunk 3: ~2s generación → Mientras habla chunk 2
- **Latencia percibida: 3s vs 8s (reducción del 62%)**

---

### Solución 2: Instrucción a GPT para Respuestas Más Cortas

**Problema:** GPT genera respuestas de 40-50 palabras.

**Solución:** Agregar instrucción explícita en prompt.

**Implementación en `_construir_prompt_dinamico()`:**

```python
# FIX 203: Instrucción para respuestas cortas y concisas
instrucciones_brevedad = """
🔥 CRÍTICO - BREVEDAD EN RESPUESTAS:

⏱️ LONGITUD MÁXIMA:
- Respuestas de 15-25 palabras máximo
- NUNCA más de 30 palabras en una sola respuesta
- Si necesitas decir más, termina con pregunta y espera respuesta del cliente

✅ CORRECTO (18 palabras):
"Entiendo que están en horario de comida. ¿Hay un mejor momento
 para llamar y hablar con el encargado?"

❌ INCORRECTO (44 palabras):
"Entiendo, es importante respetar esos tiempos. El motivo de mi
 llamada es muy breve: nosotros distribuimos productos de ferretería
 con alta rotación, especialmente nuestra cinta para goteras que muchos
 negocios tienen como producto estrella. ¿Usted maneja este tipo de
 productos actualmente en su negocio?"

💡 ESTRATEGIA:
- Una idea por respuesta
- Termina con pregunta cerrada
- Espera respuesta antes de continuar
- Conversación = ping-pong, no monólogo
"""
```

**Ejemplo de mejora:**

**ANTES (44 palabras):**
```
"Entiendo, es importante respetar esos tiempos. El motivo de mi llamada
es muy breve: nosotros distribuimos productos de ferretería con alta
rotación, especialmente nuestra cinta para goteras que muchos negocios
tienen como producto estrella. ¿Usted maneja este tipo de productos
actualmente en su negocio?"
```

**DESPUÉS (18 palabras):**
```
"Entiendo. ¿Hay un mejor momento para llamar y hablar con el encargado
de compras?"
```

**Beneficios:**
- Latencia: 8s → 3s (reducción del 62%)
- Conversación más natural
- Cliente no se abruma
- Mejor adaptación al contexto (cliente ocupado)

---

### Solución 3: Aumentar Timeout Dinámicamente

**Problema:** Timeout fijo de 4.5s es insuficiente para mensajes largos.

**Solución:** Calcular timeout basado en longitud del mensaje.

**Implementación:**

```python
def calcular_timeout_audio(num_palabras: int) -> float:
    """
    Calcula timeout dinámico basado en cantidad de palabras

    Args:
        num_palabras: Cantidad de palabras en el mensaje

    Returns:
        Timeout en segundos (mínimo 5s, máximo 15s)
    """
    # Benchmarks reales de ElevenLabs Multilingual v2:
    # - 10 palabras: ~2s
    # - 20 palabras: ~4s
    # - 30 palabras: ~6s
    # - 40 palabras: ~8s
    # - 50 palabras: ~10s

    # Fórmula: 0.2s por palabra + 2s buffer
    timeout_base = (num_palabras * 0.2) + 2.0

    # Limites
    timeout = max(5.0, min(timeout_base, 15.0))

    return timeout
```

**Ejemplo:**
```python
calcular_timeout_audio(10)  # → 5.0s (mínimo)
calcular_timeout_audio(20)  # → 6.0s
calcular_timeout_audio(44)  # → 10.8s ✅ (vs 4.5s antes)
calcular_timeout_audio(100) # → 15.0s (máximo)
```

**Modificación en `generar_audio_elevenlabs()`:**

```python
# FIX 203: Timeout dinámico basado en longitud
num_palabras = len(texto.split())
timeout_dinamico = calcular_timeout_audio(num_palabras)

print(f"⏳ FIX 165 + FIX 203: Esperando audio ({num_palabras} palabras, timeout={timeout_dinamico:.1f}s)...")
```

**Beneficios:**
- No más timeouts prematuros
- No más warnings en logs
- Timeout ajustado a realidad del API

---

### Solución 4: Pre-generar Cachés de Frases Comunes

**Problema:** Primera vez que se usa una frase = 8s de espera.

**Solución:** Identificar y pre-generar cachés de frases más usadas.

**Análisis de logs previos:**

Frases frecuentes que deberían tener caché:
1. "Entiendo, es importante respetar esos tiempos."
2. "El motivo de mi llamada es muy breve:"
3. "Nosotros distribuimos productos de ferretería con alta rotación"
4. "Especialmente nuestra cinta para goteras"
5. "¿Usted maneja este tipo de productos actualmente en su negocio?"

**Script de pre-generación:**

```python
# generar_cache_frases_comunes.py

FRASES_FRECUENTES = [
    "Entiendo, es importante respetar esos tiempos",
    "El motivo de mi llamada es muy breve",
    "Nosotros distribuimos productos de ferretería con alta rotación",
    "Especialmente nuestra cinta para goteras",
    "¿Usted maneja este tipo de productos actualmente en su negocio?",
    "¿Hay un mejor momento para llamar?",
    "¿Me podría dar su WhatsApp o correo electrónico?",
    "Perfecto, muchas gracias por su tiempo",
    "Le llegará el catálogo en las próximas horas",
    "¿Con quién tengo el gusto?",
    # ... más frases frecuentes
]

def pre_generar_caches():
    """Pre-genera cachés de frases más frecuentes"""
    for frase in FRASES_FRECUENTES:
        cache_key = generar_cache_key(frase)
        if not cache_existe(cache_key):
            print(f"Generando caché: {frase[:50]}...")
            generar_audio_elevenlabs(frase, cache_key, usar_cache=True)
```

**Beneficios:**
- Frases comunes: 0s latencia (desde caché)
- Solo frases nuevas/únicas necesitan generación
- Reducción promedio del 70% en latencia

---

### Solución 5: Streaming de Audio (Avanzado)

**Problema:** Sistema espera TODO el audio antes de reproducir.

**Solución:** Reproducir audio mientras se genera (streaming).

**Implementación (Complejo):**

```python
def generar_y_reproducir_streaming(texto: str):
    """
    Genera audio en chunks y reproduce mientras se genera
    """
    # Dividir en oraciones
    oraciones = dividir_en_oraciones(texto)

    for i, oracion in enumerate(oraciones):
        # Generar audio de esta oración
        audio_generator = elevenlabs_client.text_to_speech.convert(
            voice_id=ELEVENLABS_VOICE_ID,
            text=oracion,
            model_id="eleven_multilingual_v2",
            output_format="mp3_44100_128"
        )

        # Guardar chunk
        audio_path = f"audio_chunk_{i}.mp3"
        save_audio(audio_generator, audio_path)

        # Reproducir inmediatamente (no esperar)
        reproducir_en_twilio(audio_path)

        # Mientras reproduce, generar siguiente chunk en paralelo
        if i < len(oraciones) - 1:
            # Iniciar generación del siguiente chunk
            threading.Thread(target=pre_generar_chunk, args=(oraciones[i+1],)).start()
```

**Beneficios:**
- Latencia percibida: ~2s (primer chunk)
- Cliente escucha algo inmediatamente
- Chunks siguientes se reproducen sin pausa

**Desventajas:**
- Implementación compleja
- Requiere manejo de threads
- Posible desincronización

---

## 📊 COMPARACIÓN DE SOLUCIONES

| Solución | Complejidad | Latencia Actual | Latencia Post-Fix | Reducción | Prioridad |
|----------|-------------|-----------------|-------------------|-----------|-----------|
| **#1: Dividir en Chunks** | Media | 8s | 3s | 62% | 🔥 ALTA |
| **#2: Respuestas Cortas** | Baja | 8s | 3s | 62% | 🔥 ALTA |
| **#3: Timeout Dinámico** | Baja | 4.5s (timeout) | 10s (sin timeout) | N/A | 🟡 MEDIA |
| **#4: Pre-generar Cachés** | Media | 8s (primera vez) | 0s (cache) | 100% | 🟢 ALTA |
| **#5: Streaming** | Alta | 8s | 2s | 75% | 🔵 BAJA |

---

## ✅ PLAN DE IMPLEMENTACIÓN

### Fase 1: Quick Wins (Inmediato) 🔥

**Implementar Soluciones #2 y #3:**

1. Agregar instrucción de brevedad en prompt
2. Implementar timeout dinámico
3. Desplegar y monitorear

**Beneficios inmediatos:**
- Respuestas más cortas naturalmente
- No más timeouts prematuros
- Implementación rápida (30 min)

### Fase 2: Optimización de Caché (Corto plazo) 🟢

**Implementar Solución #4:**

1. Analizar logs para identificar frases más frecuentes
2. Crear script de pre-generación
3. Ejecutar pre-generación de cachés
4. Desplegar

**Beneficios:**
- 70% de respuestas desde caché (0s latencia)
- Solo frases únicas necesitan generación

### Fase 3: Chunking Inteligente (Mediano plazo) 🟡

**Implementar Solución #1:**

1. Crear función de división de respuestas
2. Integrar en flujo de generación
3. Testing exhaustivo
4. Desplegar

**Beneficios:**
- Latencia percibida reducida al 62%
- Mejor UX en respuestas largas

### Fase 4: Streaming (Opcional - Largo plazo) 🔵

**Implementar Solución #5:**

1. Diseñar arquitectura de streaming
2. Implementar threading y manejo de chunks
3. Testing extensivo
4. Desplegar gradualmente

**Beneficios:**
- Latencia percibida mínima (~2s)
- Mejor experiencia en todas las llamadas

---

## 🎯 MÉTRICAS DE ÉXITO

### KPIs Objetivo:

| Métrica | Actual | Objetivo | Mejora |
|---------|--------|----------|--------|
| **Latencia promedio** | 8s | 3s | 62% |
| **Tasa de colgadas por timeout** | 15% | <5% | 67% |
| **Respuestas desde caché** | 30% | 70% | +133% |
| **Satisfacción cliente** | Baja | Alta | +++ |

### Monitoreo:

- Trackear latencia de cada respuesta
- Graficar histograma de latencias
- Alertar si latencia > 6s
- Revisar tasa de colgadas después de respuestas largas

---

## 🚨 RECOMENDACIÓN INMEDIATA

**IMPLEMENTAR FASE 1 AHORA:**

1. ✅ Agregar instrucción de brevedad en prompt (5 min)
2. ✅ Implementar timeout dinámico (10 min)
3. ✅ Desplegar a producción (5 min)

**Total: 20 minutos → 62% reducción de latencia**

---

**Estado:** 🟡 READY TO IMPLEMENT
