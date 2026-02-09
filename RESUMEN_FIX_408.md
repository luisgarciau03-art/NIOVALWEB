# RESUMEN FIX 408 - Timeout Deepgram Progresivo

## ❌ Problema
Cliente dijo: **"Ahorita no está joven"**
Deepgram: [timeout]
Bruce asumió: "Cliente dijo 'bueno'"
Bruce preguntó: **"¿Se encontrará el encargado?"** ← REDUNDANTE
Cliente: **[colgó]**

## ✅ Solución
Lógica progresiva de timeouts - **máximo 2 pedidos de repetición**:

1. **Primer timeout:** "Disculpe, no alcancé a escucharle bien, ¿me podría repetir?"
2. **Segundo timeout:** "¿Me escucha? Parece que hay interferencia"
3. **Tercer timeout+:** Continuar con saludo (asumir problema técnico)

## 📁 Archivos Modificados
- `agente_ventas.py:261` - Nuevo atributo `timeouts_deepgram`
- `servidor_llamadas.py:2268-2378` - Lógica progresiva FIX 408
- `servidor_llamadas.py:1680-1685` - Reset de contador

## 📊 Beneficios
- ✅ Evita asunciones incorrectas
- ✅ No estresa al cliente (máximo 2 repeticiones)
- ✅ Captura respuestas críticas ("no está")
- ✅ Mejora tasa de conversión (+15% esperado)

## 🔍 Logs
**Antes:**
```
🚨 FIX 211: Primer mensaje vacío - Asumiendo que cliente respondió
```

**Después:**
```
🚨 FIX 408: Primer mensaje vacío (timeout #1)
   📞 FIX 408: Primer timeout - pidiendo repetición natural
```

## ⚠️ Importante
- **Whisper NO se usa** (errores graves que confunden a Bruce)
- **Deepgram único sistema** de transcripción
- **Contador se resetea** cuando Deepgram responde exitosamente
