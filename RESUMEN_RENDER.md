# 🚀 RESUMEN RÁPIDO - Despliegue en Render

## ✅ TODO LISTO PARA DESPLEGAR

Tu sistema está **100% preparado** para Render. Todos los archivos necesarios están creados.

---

## 📦 ARCHIVOS PREPARADOS

- ✅ `requirements.txt` - Dependencias de Python
- ✅ `render.yaml` - Configuración de Render
- ✅ `.gitignore` - Protege credenciales y .env
- ✅ `servidor_llamadas.py` - Modificado para puerto dinámico
- ✅ `nioval_sheets_adapter.py` - Soporta credenciales desde env
- ✅ `resultados_sheets_adapter.py` - Soporta credenciales desde env
- ✅ `DESPLIEGUE_RENDER.md` - Guía completa paso a paso

---

## 🎯 PASOS RÁPIDOS (30 minutos total)

### 1. Subir a GitHub (10 min)
```bash
cd "C:\Users\PC 1\AgenteVentas"
git init
git add .
git commit -m "🚀 Sistema NIOVAL - Despliegue inicial"
git remote add origin https://github.com/TU_USUARIO/nioval-sistema-llamadas.git
git push -u origin main
```

### 2. Crear Web Service en Render (5 min)
1. Ve a: https://dashboard.render.com/
2. **New +** → **Web Service**
3. Conecta repositorio: `nioval-sistema-llamadas`
4. Configuración:
   - Name: `nioval-webhook-server`
   - Build: `pip install -r requirements.txt`
   - Start: `python servidor_llamadas.py`
   - Instance: **Starter ($7/month)**

### 3. Configurar Variables de Entorno (10 min)

**Importante:** Agrega `GOOGLE_APPLICATION_CREDENTIALS_JSON` con el contenido completo del archivo `bubbly-subject-412101-c969f4a975c5.json`

Todas las variables:
- `GOOGLE_APPLICATION_CREDENTIALS_JSON` - Contenido del JSON completo
- `OPENAI_API_KEY` - `sk-proj-8Vs3N63DO...`
- `USE_GITHUB_MODELS` - `false`
- `ELEVENLABS_API_KEY` - `sk_f4254188a7b46a168...`
- `ELEVENLABS_VOICE_ID` - `vPrtQbTwtAoP87VnQmID`
- `ELEVENLABS_AGENT_ID` - `agent_9001kdbfxpkwfhbabhyhns37c0h2`
- `TWILIO_ACCOUNT_SID` - `ACddf2b7fafcc4714be7cc3437b905c9dc`
- `TWILIO_AUTH_TOKEN` - `d43c85011fd8d331207d881461d32480`
- `TWILIO_PHONE_NUMBER` - `+19377958829`
- `PORT` - `5000`

### 4. Desplegar (5 min)
1. Haz clic en **Create Web Service**
2. Espera a que aparezca: ✅ **Live**
3. Copia tu URL: `https://nioval-webhook-server.onrender.com`

### 5. Configurar Twilio (3 min)
1. Ve a: https://console.twilio.com/us1/develop/phone-numbers/manage/incoming
2. Selecciona tu número: `+19377958829`
3. En **A CALL COMES IN**:
   - URL: `https://nioval-webhook-server.onrender.com/webhook-voz`
   - Método: **HTTP POST**
4. **Save**

### 6. Actualizar `.env` local (1 min)
```env
WEBHOOK_URL=https://nioval-webhook-server.onrender.com
```

---

## 🧪 PROBAR

```bash
cd "C:\Users\PC 1\AgenteVentas"
python sistema_llamadas_nioval.py
```

Ver logs en Render:
```
Dashboard → nioval-webhook-server → Logs
```

---

## 💰 COSTO MENSUAL

- Render Starter: **$7/mes**
- Twilio (2000 llamadas): ~$220-520/mes
- OpenAI: ~$20/mes
- **TOTAL: ~$247-547/mes**

---

## ✨ VENTAJAS

✅ **$7/mes** - Más barato que ngrok ($8/mes)
✅ **URL permanente** - Nunca cambia
✅ **24/7 activo** - Tu PC puede estar apagada
✅ **Logs en tiempo real** - Ver todo lo que pasa
✅ **Auto-deploy** - Actualiza desde GitHub automáticamente

---

## 📚 DOCUMENTACIÓN COMPLETA

Ver guía detallada paso a paso: [DESPLIEGUE_RENDER.md](DESPLIEGUE_RENDER.md)

---

## 🎉 SIGUIENTE PASO

**Opción 1:** Leer guía completa en [DESPLIEGUE_RENDER.md](DESPLIEGUE_RENDER.md)
**Opción 2:** Seguir los 6 pasos de arriba (30 min)

**¿Listo para desplegar?** 🚀

---

**Estado:** ✅ 100% preparado para Render
**Fecha:** 27 de diciembre 2024
