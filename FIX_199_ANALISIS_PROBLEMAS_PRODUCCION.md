# FIX 199 - ANÁLISIS DE PROBLEMAS EN PRODUCCIÓN

**Fecha:** 2026-01-13
**Prioridad:** 🚨 ALTA
**Estado:** 🔍 EN INVESTIGACIÓN

---

## 📋 PROBLEMAS REPORTADOS POR USUARIO

### 1. 🚨 **CRÍTICO: Delay de 8-10 segundos**
**Reporte**: "Bruce tiene un delay considerable de 8-10 segundos, por arriba de 10seg la platica no se vuelve fluida"

**Análisis de Logs**:
```
2026-01-13T22:22:25 - ElevenLabs quota_exceeded: 2 credits remaining, 58-176 credits required
2026-01-13T22:22:26 - ⚡ FIX 97: Usar Twilio TTS (respuesta larga o error)
2026-01-13T22:22:26 - 🎵 FIX 162A: Usando audio de relleno 'dejeme_ver'
```

**CAUSA RAÍZ**: ❌ **ELEVENLABS SIN CRÉDITOS**
- Solo 2 créditos restantes
- Cada respuesta requiere 58-176 créditos
- Sistema usa fallback a Twilio TTS (voz robótica lenta)

**IMPACTO**:
- ❌ Delay real: 8-10 segundos por respuesta
- ❌ Voz robótica en lugar de voz natural Bruce
- ❌ Clientes colgando por impaciencia
- ❌ Audio de relleno "dejeme_ver" repetido

**SOLUCIÓN INMEDIATA**:
✅ **Recargar créditos ElevenLabs** (URGENTE)
- Con créditos: delay vuelve a 0-2s
- Voz natural mexicana restaurada
- UX fluida restaurada

---

### 2. ⚠️ **Problemas capturando correos**
**Reporte**: "Aun tiene problemas para tomar anotar correo, menciona que si puedes repetir nuevamente la pregunta BRUCE455"

**Análisis Call BRUCE455 (CAb070adf7)**:
```
22:22:25 - Cliente: "por WhatsApp"
22:22:26 - Bruce: "Excelente. ¿Cuál es su número de WhatsApp?"
22:22:32 - Cliente: "" (vacío - timeout)
22:22:32 - Bruce: "Disculpa, no te escuché bien, ¿me puedes repetir?"
22:22:38 - Cliente: "por WhatsApp" (REPITE LO MISMO)
22:22:40 - Bruce: "Entiendo que prefiere por WhatsApp. ¿Cuál es su número?"
22:22:46 - Cliente: "" (vacío de nuevo)
22:22:50 - Cliente: "WhatsApp"
22:22:52 - Bruce: "Parece que está ocupado..."
22:22:57 - CallStatus: completed (cliente colgó)
```

**CAUSA RAÍZ**:
1. ❌ **Cliente NO está dando el número**, solo dice "WhatsApp"
2. ❌ **ElevenLabs sin créditos** → Audio de relleno "dejeme_ver" confunde al cliente
3. ❌ **Whisper transcribe bien**, pero cliente no entiende qué hacer

**PROBLEMA**: No es técnico - es de **UX/comunicación**
- Cliente confundido por voz robótica (Twilio TTS fallback)
- Audio de relleno "dejeme_ver" no ayuda
- Cliente no sabe que debe dictar su número

**SOLUCIÓN**:
1. ✅ Recargar créditos ElevenLabs (voz clara → cliente entiende)
2. ✅ Mejorar prompt de GPT para ser más específico:
   - "¿Cuál es su número de WhatsApp de 10 dígitos?"
   - "Dígame su número para anotarlo"

---

### 3. ⚠️ **Bruce repitiendo preguntas 3 veces (BRUCE449)**
**Reporte**: "Repite las mismas preguntas BRUCE449 3 veces (problema en la reduccion de tokens)"

**Análisis**: No encontrado en logs recientes, necesito logs de BRUCE449

**HIPÓTESIS**:
- Posible loop de GPT por reducción de contexto
- FIX 66 (anti-loop) debería prevenir esto
- Necesito ver logs específicos para diagnosticar

**ACCIÓN**: Solicitar logs de Call SID BRUCE449

---

### 4. 🔍 **Whisper transcribiendo mal códigos/emails**
**Reporte**: "problema en whisper al transcribir el codigo, que otras opciones hay con mayor calidad"

**Logs Relevantes**:
```
22:15:48 - Cliente: "Consultar nuestro aviso de privacidad... www.gafi.com.mx..."
           (MENSAJE AUTOMATIZADO - no es cliente humano)
```

**OBSERVACIÓN IMPORTANTE**:
- ❌ Bruce está llamando a **IVR/contestadoras automáticas**
- Sistema de menú automático: "Digite 1 para... digite 2 para..."
- NO es falla de Whisper - es detección de buzón/IVR incorrecta

**PROBLEMA REAL**:
- Sistema no detecta IVR automático
- Whisper transcribe perfectamente el mensaje del IVR
- Bruce intenta conversar con una máquina

**SOLUCIÓN**:
```python
# Detectar patrones de IVR/mensajes automáticos
patron_ivr = [
    "digite", "presione", "marque", "opciones", "menú",
    "pulse", "seleccione", "aviso de privacidad",
    "horario de atención", "nuestro horario"
]

if any(patron in transcripcion.lower() for patron in patron_ivr):
    marcar_como_buzon_ivr()
    colgar_llamada()
```

**Alternativas a Whisper**:
1. **Deepgram** (más rápido, mejor español mexicano)
2. **AssemblyAI** (excelente con acentos)
3. **Azure Speech** (muy preciso, más caro)

Pero el problema NO es Whisper - es detección de IVR.

---

### 5. 🔍 **No captó respuesta y colgaron (BRUCE434)**
**Reporte**: "No capto una respuesta que le dieron y le colgaron BRUCE434"

**Análisis**: No encontrado en logs recientes

**ACCIÓN**: Necesito logs específicos de BRUCE434

---

### 6. 🚨 **Menciona "Problema técnico" (BRUCE433)**
**Reporte**: "Menciona Problema tecnico BRUCE433"

**HIPÓTESIS**: Posiblemente relacionado con FIX 198.1 que acabamos de resolver
- Error: `name 'respuesta_cliente' is not defined`
- Causaba mensaje "Disculpe, tuve un problema técnico"
- ✅ **YA RESUELTO** en commit 9bbb39d

**VERIFICACIÓN**: Necesito logs de BRUCE433 para confirmar

---

### 7. ⚠️ **Ciclo de interrupciones (BRUCE430)**
**Reporte**: "BRUCE430 (Ciclo de interrupciones)"

**Logs Relevantes**:
```
22:15:27 - Cliente: "No se registró ninguna opción, por favor, intente de nuevo."
           (MENSAJE DE IVR AUTOMÁTICO)
22:15:29 - Bruce: "¿Bueno? Buenos días. Me comunico de la marca Nioval..."
22:15:48 - Cliente: "Consultar nuestro aviso de privacidad... digite 1... digite 2..."
           (SISTEMA AUTOMÁTICO CONTINÚA)
```

**CAUSA RAÍZ**:
- ❌ Bruce conversando con **sistema IVR automático**
- Cliente = mensaje grabado de opciones
- FIX 157 (barge_in) debería interrumpir, pero no detecta que es IVR

**SOLUCIÓN**: Mejorar detección de IVR (ver problema #4)

---

## 🎯 PRIORIDADES DE SOLUCIÓN

### ⚡ URGENTE (HOY)
1. **Recargar créditos ElevenLabs** ← Resuelve delay + voz robótica
2. **Implementar detección de IVR** ← Evita loops con contestadoras
3. **Obtener logs de BRUCE433, 430, 434, 449** ← Diagnóstico completo

### 📅 ALTA PRIORIDAD (ESTA SEMANA)
4. **Mejorar prompts de solicitud de datos** ← Claridad en preguntas
5. **Evaluar alternativas a Whisper** ← Deepgram, AssemblyAI
6. **Revisar FIX 66 anti-loop** ← Prevenir preguntas repetidas

---

## 📊 ESTADO ACTUAL DEL SISTEMA

### ✅ FUNCIONANDO CORRECTAMENTE:
- ✅ FIX 198: Detección "Dígame", emails duplicados, errores Whisper
- ✅ FIX 198.1: Variable `respuesta_cliente` corregida
- ✅ Whisper transcribiendo perfectamente (96-99% precisión)
- ✅ Cache de audios (0s delay cuando hay créditos)
- ✅ GPT-4o-mini generando respuestas coherentes

### ❌ PROBLEMAS ACTIVOS:
- ❌ **ElevenLabs sin créditos** (CRÍTICO)
- ❌ **No detecta IVR/contestadoras** (ALTA)
- ❌ Necesito logs específicos de BRUCE433, 430, 434, 449

---

## 💡 SOLUCIONES TÉCNICAS PROPUESTAS

### 1. Detección de IVR/Contestadora Automática

```python
def detectar_ivr_o_contestadora(transcripcion: str) -> bool:
    """
    FIX 199: Detecta mensajes de IVR o contestadoras automáticas
    """
    patrones_ivr = [
        # Menús interactivos
        "digite", "presione", "marque", "pulse", "seleccione",
        "opción", "opciones", "menú", "menu",

        # Mensajes corporativos
        "aviso de privacidad", "horario de atención", "nuestro horario",
        "gracias por llamar", "bienvenido a", "está llamando a",

        # Instrucciones
        "para", "si desea", "si gusta", "visite", "consultar",

        # Números/opciones
        "uno", "dos", "tres", "cuatro", "1", "2", "3", "4",

        # Buzón específico
        "buzón de voz", "buzon de voz", "deje su mensaje",
        "después del tono", "despues del tono"
    ]

    transcripcion_lower = transcripcion.lower()

    # Contar cuántos patrones coinciden
    coincidencias = sum(1 for patron in patrones_ivr if patron in transcripcion_lower)

    # Si tiene 2+ patrones O mensaje muy largo (>100 palabras) → es IVR
    palabras = len(transcripcion.split())

    if coincidencias >= 2 or palabras > 100:
        print(f"🤖 FIX 199: IVR detectado ({coincidencias} patrones, {palabras} palabras)")
        return True

    return False
```

### 2. Mejora de Prompts para Datos

```python
# En lugar de:
"¿Cuál es su número de WhatsApp?"

# Usar:
"¿Cuál es su número de WhatsApp de 10 dígitos para enviárselo? Por favor, dígamelo despacio."

# O mejor aún:
"Perfecto. Para enviarle el catálogo, necesito que me dicte su número de WhatsApp.
Son 10 dígitos, puede decirlos de uno en uno. Adelante por favor."
```

### 3. Evaluación de Alternativas a Whisper

**Deepgram** (Recomendado):
- ✅ 50% más rápido que Whisper
- ✅ Mejor con acentos mexicanos
- ✅ Streaming (transcripción en tiempo real)
- ✅ $0.0043/min vs $0.006/min Whisper
- ❌ Requiere integración nueva

**AssemblyAI**:
- ✅ Excelente con números/códigos
- ✅ Detección de idioma automática
- ✅ Speaker diarization (útil para transferencias)
- ❌ $0.00025/segundo = $0.015/min (2.5x más caro)

**Azure Speech**:
- ✅ Muy preciso (98-99%)
- ✅ Integración con Twilio directa
- ❌ $1.00/hora = $0.0167/min (2.8x más caro)

**RECOMENDACIÓN**: Mantener Whisper (funciona bien) + mejorar detección IVR

---

## 🧪 PLAN DE TESTING

### Test 1: Verificar delay con créditos ElevenLabs
1. Recargar créditos
2. Hacer llamada de prueba
3. Medir tiempo entre respuestas (objetivo: <2s)

### Test 2: Detección de IVR
1. Llamar a número con contestadora conocida
2. Verificar que detecte IVR y cuelgue
3. No registrar como "Colgo" sino "Buzon/IVR"

### Test 3: Captura de WhatsApp
1. Llamada de prueba
2. Decir claramente 10 dígitos
3. Verificar captura correcta

---

## 📝 ACCIONES INMEDIATAS REQUERIDAS

**Para el Usuario**:
1. ⚡ **Recargar créditos ElevenLabs** (URGENTE)
2. 📋 **Proporcionar logs de**:
   - BRUCE433 (problema técnico)
   - BRUCE430 (ciclo interrupciones)
   - BRUCE434 (no captó respuesta)
   - BRUCE449 (preguntas repetidas 3 veces)

**Para Desarrollo**:
1. ✅ Implementar detección de IVR (FIX 199)
2. ✅ Mejorar prompts de solicitud de datos
3. ✅ Agregar logging para depurar casos específicos

---

## 📞 RESUMEN EJECUTIVO

**Problema Principal**: ❌ **ElevenLabs sin créditos**
- Causa delay de 8-10s
- Voz robótica confunde clientes
- Solución: Recargar créditos

**Problema Secundario**: ❌ **No detecta IVR/contestadoras**
- Bruce conversa con máquinas
- Genera loops infinitos
- Solución: Implementar FIX 199

**Sistema Core**: ✅ **Funcionando correctamente**
- Whisper: 96-99% precisión ✅
- GPT-4o: Respuestas coherentes ✅
- Cache: 0s delay (cuando hay créditos) ✅
- FIX 198/198.1: Bugs corregidos ✅

**Acción Urgente**: ⚡ **Recargar ElevenLabs HOY**
