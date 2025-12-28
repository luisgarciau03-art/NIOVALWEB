# 🤖 Sistema de Agente de Ventas NIOVAL

Sistema de llamadas automáticas con IA para ventas B2B de productos ferreteros.

## 🎯 Características

- **GPT-4o**: Conversación inteligente y natural
- **ElevenLabs**: Voz ultra-realista en español
- **Twilio**: Integración con telefonía real
- **Guardado automático**: Leads guardados en Excel
- **Script personalizado**: Flujo de ventas específico para NIOVAL

## 📋 Requisitos Previos

1. **Python 3.9+**
2. **API Keys necesarias**:
   - OpenAI (GPT-4o): https://platform.openai.com/api-keys
   - ElevenLabs: https://elevenlabs.io/app/settings/api-keys
   - Twilio (opcional, para llamadas reales): https://www.twilio.com/console

## 🚀 Instalación

### 1. Instalar dependencias

```powershell
pip install -r requirements.txt
```

### 2. Configurar variables de entorno

Copia `.env.example` a `.env` y completa tus API keys:

```powershell
copy .env.example .env
```

Edita `.env` con tus claves:
```
OPENAI_API_KEY=sk-tu-key-aqui
ELEVENLABS_API_KEY=tu-key-aqui
```

### 3. Obtener Voice ID de ElevenLabs

Para usar una voz en español:

1. Ve a https://elevenlabs.io/app/voice-library
2. Busca voces en **Spanish**
3. Selecciona una voz profesional (ej: "Mateo", "Valentina")
4. Copia el **Voice ID** y actualiza en `.env`

## 💻 Uso

### Modo 1: Demo Interactiva por Consola

Prueba el agente escribiendo respuestas simuladas:

```powershell
python agente_ventas.py
```

**Ejemplo de conversación:**
```
🎙️ Bruce W: Hola, qué tal, muy buenas tardes...
👤 Cliente: Sí, soy yo
🎙️ Bruce W: ¿Con quién tengo el gusto?
👤 Cliente: Juan Pérez
...
```

Escribe `salir` para terminar y guardar el lead.

### Modo 2: Servidor con Llamadas Reales (Twilio)

#### Paso 1: Configurar Twilio

1. Crea cuenta en https://www.twilio.com
2. Obtén un número de teléfono
3. Copia tus credenciales a `.env`

#### Paso 2: Exponer servidor públicamente

Usa **ngrok** para exponer tu servidor local:

```powershell
# Instalar ngrok: https://ngrok.com/download
ngrok http 5000
```

Copia la URL pública (ej: `https://abc123.ngrok.io`)

#### Paso 3: Iniciar servidor

```powershell
python servidor_llamadas.py
```

#### Paso 4: Hacer llamadas

**Llamada individual:**

```powershell
curl -X POST http://localhost:5000/iniciar-llamada `
  -H "Content-Type: application/json" `
  -d '{\"telefono\": \"+52XXXXXXXXXX\", \"nombre_negocio\": \"Ferretería Los Pinos\"}'
```

**Llamadas masivas:**

```powershell
curl -X POST http://localhost:5000/llamadas-masivas `
  -H "Content-Type: application/json" `
  -d '{
    \"lista_telefonos\": [
      {\"telefono\": \"+52XXXXXXXXXX\", \"nombre\": \"Ferretería 1\"},
      {\"telefono\": \"+52YYYYYYYYYY\", \"nombre\": \"Ferretería 2\"}
    ],
    \"delay_segundos\": 30
  }'
```

## 📊 Datos Recopilados

Los leads se guardan automáticamente en `leads_nioval.xlsx` con:

- Nombre del contacto
- Nombre del negocio
- Teléfono / WhatsApp
- Email
- Categorías de interés
- Notas de la conversación
- Fecha y hora
- Nivel de interés

## 🎨 Personalización

### Cambiar el prompt del agente

Edita la variable `SYSTEM_PROMPT` en `agente_ventas.py`

### Ajustar parámetros de voz

En el método `texto_a_voz()`:

```python
voice_settings=VoiceSettings(
    stability=0.50,      # 0-1 (más alto = más estable)
    similarity_boost=0.80,  # 0-1 (qué tan similar a la voz original)
    style=0.35          # 0-1 (exageración del estilo)
)
```

### Cambiar modelo de GPT

En `procesar_respuesta()`:
```python
model="gpt-4o"  # Opciones: "gpt-4o", "gpt-3.5-turbo"
```

## 💰 Costos Estimados

**Por llamada de 3 minutos:**
- GPT-4o: ~$0.02 - $0.05
- ElevenLabs: ~$0.10 - $0.15
- Twilio: ~$0.02 - $0.05 (según país)
- **Total: ~$0.15 - $0.25 por llamada**

**100 llamadas/día:** $15 - $25
**1000 llamadas/mes:** $150 - $250

## 🔧 Solución de Problemas

### Error: "No module named 'openai'"
```powershell
pip install openai
```

### Error: "Invalid API Key"
Verifica que las API keys en `.env` sean correctas

### No se genera audio
Verifica el Voice ID de ElevenLabs en `.env`

### Twilio no conecta
Asegúrate de usar ngrok para exponer tu servidor y configurar la webhook URL en Twilio

## 📝 Próximos Pasos

1. ✅ Prueba el demo por consola
2. ✅ Configura ElevenLabs con voz en español
3. ✅ Realiza llamadas de prueba con Twilio
4. ⬜ Conecta con CRM (HubSpot, Zoho, etc.)
5. ⬜ Agrega análisis de sentimiento
6. ⬜ Dashboard de métricas

## 📞 Soporte

Para dudas o problemas, revisa:
- Documentación OpenAI: https://platform.openai.com/docs
- Documentación ElevenLabs: https://docs.elevenlabs.io
- Documentación Twilio: https://www.twilio.com/docs

---

**Desarrollado para NIOVAL** 🛠️
