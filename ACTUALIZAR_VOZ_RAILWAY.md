# Actualizar Voz en Railway

## Nueva Voz Configurada: Mauricio

**Voice ID:** `94zOad0g7T7K4oa7zhDq`

### Características:
- ✅ **Nombre:** Mauricio - Calm and Conversational
- ✅ **Edad:** Middle-aged (30-45 años) - Más profesional
- ✅ **Género:** Male
- ✅ **Acento:** Latin American neutral
- ✅ **Use Case:** Conversational (diseñado para conversaciones)
- ✅ **Tono:** Calm, gentle (profesional sin ser agresivo)

---

## 🚀 Pasos para Actualizar en Railway

### Opción 1: Desde Railway Dashboard (Recomendado)

1. Ve a: https://railway.app/
2. Selecciona tu proyecto: **nioval-webhook-server**
3. Ve a la pestaña **Variables**
4. Busca: `ELEVENLABS_VOICE_ID`
5. Cambia el valor a: `94zOad0g7T7K4oa7zhDq`
6. Haz clic en **Deploy** o espera el auto-deploy

### Opción 2: Desde Railway CLI

```bash
railway variables set ELEVENLABS_VOICE_ID=94zOad0g7T7K4oa7zhDq
```

---

## ✅ Verificar el Cambio

Después de actualizar:

1. Espera 1-2 minutos que Railway redeploy
2. Haz una llamada de prueba:
   ```bash
   py llamar_produccion.py +523XXXXXXXXXX "Prueba Mauricio"
   ```
3. Escucha la grabación en Twilio Console
4. Verifica que el acento suene más profesional/maduro

---

## 🎙️ Otras Voces Disponibles (si Mauricio no funciona)

### Enrique Mondragón - Elegant and Dynamic
- **Voice ID:** `iDEmt5MnqUotdwCIVplo`
- **Acento:** Mexican (más específico)
- **Estilo:** Más energético y dinámico

### Juan Carlos - Warm and Conversational
- **Voice ID:** `YExhVa4bZONzeingloMX`
- **Acento:** Latin American
- **Estilo:** Cálido y conversacional

Para cambiar, actualiza `ELEVENLABS_VOICE_ID` con el ID correspondiente.
