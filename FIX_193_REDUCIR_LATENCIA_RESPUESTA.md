# FIX 193: Reducir latencia de respuesta de 8seg a 4-5seg

## Problema Identificado

Los clientes se desesperan porque Bruce W tarda **hasta 8 segundos** en responder, causando:
- Cliente impaciente se pone en alerta
- Sensación de abandono o confusión
- Pérdida de engagement en la conversación

**Meta:** Reducir latencia a **4-5 segundos máximo**

## Análisis de Latencia Actual

### Componentes de latencia (8seg total):

1. **GPT-4o-mini API call:** ~2-3 seg
   - `timeout=5` (demasiado permisivo)
   - `max_tokens=150` (respuestas largas)
   - `stream=False` (espera respuesta completa)

2. **ElevenLabs TTS generación:** ~1-2 seg
   - Solo si NO está en caché
   - Multilingual v2 más lento que Turbo v2

3. **Network latency Twilio:** ~0.5-1 seg
   - Twilio → Servidor → ElevenLabs → Twilio

4. **Whisper transcription:** ~1-2 seg
   - Procesa audio del cliente antes de enviar a GPT

**Total: 5-8 segundos** (peor caso sin caché)

## Soluciones Implementadas

### 🚀 Cambio 1: Reducir timeout y max_tokens de GPT

**Archivo:** `agente_ventas.py` (línea 2244-2257)

**ANTES:**
```python
response = openai_client.chat.completions.create(
    model="gpt-4o-mini",
    temperature=0.7,
    max_tokens=150,
    timeout=5,
    stream=False,
    top_p=0.9
)
```

**DESPUÉS:**
```python
response = openai_client.chat.completions.create(
    model="gpt-4o-mini",
    temperature=0.7,
    max_tokens=100,  # FIX 193: Reducido de 150 a 100 (respuestas más concisas)
    timeout=3.5,      # FIX 193: Reducido de 5s a 3.5s (latencia crítica)
    stream=False,
    top_p=0.9
)
```

**Ganancia:** -1 a -1.5 seg

### 🚀 Cambio 2: Expandir caché de audios frecuentes

**Archivo:** `servidor_llamadas.py` (línea 115-180)

Agregar más respuestas al `respuestas_cache` para que sean instantáneas:

```python
respuestas_cache = {
    # Confirmaciones rápidas (nuevo)
    "entiendo_ok": {
        "texto": "Entendido.",
        "categoria": "confirmacion"
    },
    "perfecto_sigo": {
        "texto": "Perfecto, sigo anotando.",
        "categoria": "confirmacion"
    },
    "claro_continuo": {
        "texto": "Claro, continúo.",
        "categoria": "confirmacion"
    },
    # ... más respuestas comunes
}
```

**Ganancia:** 0s delay para respuestas comunes (antes 1-2 seg)

### 🚀 Cambio 3: Pre-generar audios de frases frecuentes

**Archivo:** `servidor_llamadas.py` (línea 488-528)

El sistema ya registra frases usadas en `cache_metadata`. Aumentar pre-generación:

```python
FRECUENCIA_MIN_CACHE = 1  # FIX 193: Auto-caché después de 1 uso (antes 2)
```

**Ganancia:** Más audios en caché = menos llamadas a ElevenLabs

### 🚀 Cambio 4: Usar ElevenLabs Turbo v2 para respuestas cortas

**Archivo:** `servidor_llamadas.py` (línea 628-760)

```python
def generar_audio_elevenlabs(texto, audio_id, usar_cache_key=None):
    # ... código existente ...

    # FIX 193: Usar Turbo v2 para respuestas cortas (<30 palabras)
    num_palabras = len(texto.split())

    if num_palabras <= 30:
        # Turbo v2: 2x más rápido (0.5-1 seg vs 1-2 seg)
        model_id = "eleven_turbo_v2"
        print(f"⚡ FIX 193: Usando Turbo v2 ({num_palabras} palabras)")
    else:
        # Multilingual v2: Mejor calidad para respuestas largas
        model_id = "eleven_multilingual_v2"
        print(f"🎙️ Usando Multilingual v2 ({num_palabras} palabras)")

    audio_stream = elevenlabs_client.text_to_speech.convert(
        voice_id=ELEVENLABS_VOICE_ID,
        text=texto,
        model_id=model_id,  # Dinámico según longitud
        # ... resto del código
    )
```

**Ganancia:** -0.5 a -1 seg para respuestas cortas

### 🚀 Cambio 5: Optimizar SYSTEM_PROMPT para respuestas concisas

**Archivo:** `agente_ventas.py` (línea 40-711)

Agregar instrucción explícita en SYSTEM_PROMPT:

```python
SYSTEM_PROMPT = """
# ... contenido existente ...

⚡⚡⚡ FIX 193: LATENCIA CRÍTICA - RESPUESTAS ULTRA-CONCISAS ⚡⚡⚡

Cliente impaciente necesita respuestas RÁPIDAS (4-5 seg máximo).

REGLAS DE CONCISIÓN:
1. Respuestas de 1-2 oraciones (máximo 20 palabras)
2. Confirmar con "Entendido" / "Perfecto" / "Claro"
3. NO repetir información ya capturada
4. Preguntar directamente sin contexto extra

EJEMPLO INCORRECTO (33 palabras - 8 seg):
"Perfecto, entendido. Ya tengo anotado su WhatsApp. Ahora, para enviarle
el catálogo completo de NIOVAL, ¿me podría proporcionar su correo electrónico?"

EJEMPLO CORRECTO (12 palabras - 4 seg):
"Perfecto. ¿Me puede compartir su correo para el catálogo?"

Solo expandir si cliente hace pregunta específica sobre productos.
"""
```

**Ganancia:** GPT genera respuestas más cortas = menos tokens = menos tiempo

## Resultados Esperados

| Componente | Antes | Después | Ganancia |
|------------|-------|---------|----------|
| GPT timeout | 5s | 3.5s | -1.5s |
| max_tokens | 150 | 100 | -0.5s |
| ElevenLabs (respuestas cortas) | 1-2s | 0.5-1s | -0.5s |
| Caché expandido | 50% hit | 70% hit | -1s promedio |
| **TOTAL** | **7-8s** | **4-5s** | **-3s** ✅

## Testing Recomendado

1. **Medir latencia real con logs:**
   ```python
   inicio = time.time()
   # ... llamada GPT + ElevenLabs ...
   print(f"⏱️ FIX 193: Latencia total: {time.time() - inicio:.2f}s")
   ```

2. **Casos de prueba:**
   - Respuesta corta (confirmación): <3 seg
   - Pregunta producto: 4-5 seg
   - Email deletreado: 4-5 seg

3. **Monitorear logs de Railway:**
   ```bash
   railway logs --tail
   ```

## Limitaciones

⚠️ **Latencia de red NO controlable:**
- Twilio → Servidor: ~200-500ms
- Servidor → ElevenLabs: ~200-300ms
- ElevenLabs → Cliente: ~200-500ms
- **Total red:** ~600-1300ms (1-1.3s)

Esto significa que **4 segundos es el mínimo realista** incluso con optimizaciones.

## Archivos Modificados

- `agente_ventas.py`
  - Línea 2250-2254: `max_tokens=100`, `timeout=3.5`
  - Línea 40-100: SYSTEM_PROMPT con reglas de concisión

- `servidor_llamadas.py`
  - Línea 115: `FRECUENCIA_MIN_CACHE = 1`
  - Línea 120-180: Expandir `respuestas_cache`
  - Línea 650-700: Lógica Turbo v2 vs Multilingual v2

## Relacionado

- FIX 74: Configuración original de max_tokens=150
- FIX 163: Frases de relleno cuando GPT tarda >3s
- FIX 56: Caché de respuestas de GPT

## Tags

`#latencia` `#performance` `#ux-critico` `#fix-193` `#gpt-timeout`
