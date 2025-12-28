# 🚀 GUÍA DE DESPLIEGUE EN RENDER - Sistema NIOVAL

## ✅ VENTAJAS DE USAR RENDER

- 💰 **$7/mes** (plan Starter) - Más barato que ngrok Personal ($8/mes)
- 🌐 **URL permanente** - No cambia nunca
- ⚡ **Siempre activo** - No necesitas tu PC encendida
- 🔒 **HTTPS automático** - Seguro por defecto
- 📊 **Logs en tiempo real** - Ver qué pasa en cada llamada
- 🔄 **Auto-deploy** - Se actualiza automáticamente desde GitHub

---

## 📋 PRE-REQUISITOS

Antes de empezar:
- ✅ Cuenta de GitHub (gratis): https://github.com/
- ✅ Cuenta de Render (gratis): https://render.com/
- ✅ Credenciales de Twilio configuradas
- ✅ Archivo `bubbly-subject-412101-c969f4a975c5.json` (credenciales Google)

---

## 🎯 PASO 1: PREPARAR REPOSITORIO EN GITHUB (10 minutos)

### 1.1 Crear repositorio en GitHub

1. Ve a: https://github.com/new
2. Nombre del repositorio: `nioval-sistema-llamadas`
3. Visibilidad: **Private** (importante para proteger credenciales)
4. **NO** marques "Add a README file"
5. Haz clic en **Create repository**

### 1.2 Subir código a GitHub

Abre una terminal en `C:\Users\PC 1\AgenteVentas`:

```bash
# Inicializar git (si no está inicializado)
git init

# Agregar archivos (el .gitignore ya excluye .env y credenciales)
git add .

# Crear commit inicial
git commit -m "🚀 Sistema NIOVAL - Despliegue inicial"

# Agregar remote (reemplaza TU_USUARIO con tu usuario de GitHub)
git remote add origin https://github.com/TU_USUARIO/nioval-sistema-llamadas.git

# Subir código
git branch -M main
git push -u origin main
```

**IMPORTANTE:** El archivo `.env` y las credenciales JSON **NO se subirán** (están en `.gitignore`).

---

## 🌐 PASO 2: CREAR WEB SERVICE EN RENDER (5 minutos)

### 2.1 Ir a Render Dashboard

1. Ve a: https://dashboard.render.com/
2. Inicia sesión con tu cuenta
3. Haz clic en **New +** → **Web Service**

### 2.2 Conectar repositorio

1. Haz clic en **Connect a repository**
2. Autoriza a Render para acceder a GitHub (si no lo has hecho)
3. Busca y selecciona: `nioval-sistema-llamadas`
4. Haz clic en **Connect**

### 2.3 Configurar Web Service

| Campo | Valor |
|-------|-------|
| **Name** | `nioval-webhook-server` |
| **Region** | `Oregon (US West)` o el más cercano a México |
| **Branch** | `main` |
| **Root Directory** | (dejar vacío) |
| **Runtime** | `Python 3` |
| **Build Command** | `pip install -r requirements.txt` |
| **Start Command** | `python servidor_llamadas.py` |
| **Instance Type** | **Starter** ($7/month) - Recomendado para producción |

---

## 🔑 PASO 3: CONFIGURAR VARIABLES DE ENTORNO (10 minutos)

### 3.1 Agregar credenciales de Google Sheets

**Opción A - Archivo JSON (Recomendado):**

1. En Render, baja a la sección **Environment**
2. Haz clic en **Add Environment Variable**
3. **Key:** `GOOGLE_APPLICATION_CREDENTIALS_JSON`
4. **Value:** Copia TODO el contenido del archivo `bubbly-subject-412101-c969f4a975c5.json`

   Ejemplo del contenido:
   ```json
   {
     "type": "service_account",
     "project_id": "bubbly-subject-412101",
     "private_key_id": "c969f4a975c5...",
     "private_key": "-----BEGIN PRIVATE KEY-----\n...",
     ...
   }
   ```

**IMPORTANTE:** Copia el JSON completo incluyendo las llaves `{ }`.

### 3.2 Agregar todas las variables de entorno

Agrega estas variables una por una:

| Key | Value | Descripción |
|-----|-------|-------------|
| `OPENAI_API_KEY` | `sk-proj-8Vs3N63DO...` | Tu API key de OpenAI |
| `USE_GITHUB_MODELS` | `false` | Usar OpenAI de pago (no GitHub) |
| `ELEVENLABS_API_KEY` | `sk_f4254188a7b46a168...` | API key de ElevenLabs |
| `ELEVENLABS_VOICE_ID` | `vPrtQbTwtAoP87VnQmID` | ID de voz de Bruce W |
| `ELEVENLABS_AGENT_ID` | `agent_9001kdbfxpkwfhbabhyhns37c0h2` | ID del agente Bruce W |
| `TWILIO_ACCOUNT_SID` | `ACddf2b7fafcc4714be7cc3437b905c9dc` | Tu Account SID de Twilio |
| `TWILIO_AUTH_TOKEN` | `d43c85011fd8d331207d881461d32480` | Tu Auth Token de Twilio |
| `TWILIO_PHONE_NUMBER` | `+19377958829` | Tu número de Twilio |
| `PORT` | `5000` | Puerto del servidor (Render lo usa automáticamente) |

**Tips:**
- ✅ Puedes copiar los valores directamente de tu archivo `.env` local
- ✅ No incluyas comillas en los valores
- ✅ Asegúrate de no tener espacios extra al inicio o final

---

## 🚀 PASO 4: DESPLEGAR (5 minutos)

1. Después de agregar todas las variables, haz clic en **Create Web Service**
2. Render comenzará a construir y desplegar tu aplicación
3. Verás logs en tiempo real del despliegue
4. Espera a que aparezca: ✅ **Live**

**Proceso de deploy:**
```
==> Building...
==> Installing dependencies from requirements.txt
==> Starting server...
🚀 SERVIDOR DE LLAMADAS NIOVAL
📞 Endpoints disponibles:
  POST /iniciar-llamada      - Inicia una llamada individual
  POST /llamadas-masivas     - Inicia múltiples llamadas
  GET  /status/<call_sid>    - Estado de una llamada
==> Your service is live 🎉
```

---

## 🌐 PASO 5: OBTENER URL Y CONFIGURAR TWILIO (5 minutos)

### 5.1 Copiar URL de Render

En tu dashboard de Render verás algo como:
```
https://nioval-webhook-server.onrender.com
```

**Copia esta URL completa.**

### 5.2 Actualizar tu `.env` local

Abre `C:\Users\PC 1\AgenteVentas\.env` y actualiza:

```env
WEBHOOK_URL=https://nioval-webhook-server.onrender.com
```

### 5.3 Configurar Webhook en Twilio Console

1. Ve a: https://console.twilio.com/us1/develop/phone-numbers/manage/incoming
2. Haz clic en tu número: `+19377958829`
3. Baja hasta **Voice Configuration**
4. En **A CALL COMES IN**:
   - Selecciona: **Webhook**
   - URL: `https://nioval-webhook-server.onrender.com/webhook-voz`
   - Método: **HTTP POST**
5. Haz clic en **Save configuration**

---

## 🧪 PASO 6: VERIFICAR QUE TODO FUNCIONA (5 minutos)

### 6.1 Verificar que el servidor está activo

Abre en tu navegador:
```
https://nioval-webhook-server.onrender.com/
```

Deberías ver: `OK` o un mensaje del servidor.

### 6.2 Ver logs en tiempo real

En Render Dashboard:
1. Haz clic en tu servicio: `nioval-webhook-server`
2. Ve a la pestaña **Logs**
3. Verás logs en tiempo real de lo que pasa en el servidor

### 6.3 Hacer una llamada de prueba

Desde tu computadora local:

```bash
cd C:\Users\PC 1\AgenteVentas
python sistema_llamadas_nioval.py
```

El sistema:
1. ✅ Leerá contactos de Google Sheets
2. ✅ Llamará vía Twilio
3. ✅ Bruce W conversará con el cliente
4. ✅ Los webhooks llegarán a Render (no a tu PC)
5. ✅ Se guardarán resultados en Google Sheets

**Ver en Render Logs:**
```
📞 Webhook recibido: /webhook-voz
✅ Llamada procesada
💾 Guardando en Google Sheets...
✅ Datos guardados
```

---

## 🔧 MODIFICAR CÓDIGO PARA USAR CREDENCIALES JSON

Necesitas modificar `nioval_sheets_adapter.py` y `resultados_sheets_adapter.py` para que usen las credenciales desde la variable de entorno en lugar del archivo.

### Opción A: Modificar adaptadores (Recomendado)

Agrega este código al inicio del método `_autenticar()` en ambos archivos:

```python
def _autenticar(self):
    """Autentica con Google usando las credenciales"""
    try:
        # Intenta obtener credenciales desde variable de entorno (Render)
        import json
        credentials_json = os.getenv('GOOGLE_APPLICATION_CREDENTIALS_JSON')

        if credentials_json:
            # Estamos en Render, usar credenciales desde env
            credentials_dict = json.loads(credentials_json)
            creds = Credentials.from_service_account_info(
                credentials_dict,
                scopes=self.scopes
            )
        else:
            # Estamos en local, usar archivo
            creds = Credentials.from_service_account_file(
                self.credentials_file,
                scopes=self.scopes
            )

        client = gspread.authorize(creds)
        print("✅ Autenticado correctamente")
        return client
    except Exception as e:
        print(f"❌ Error al autenticar: {e}")
        raise
```

**¿Quieres que modifique los archivos automáticamente?**

---

## 📊 PASO 7: MONITOREO Y MANTENIMIENTO

### Ver logs en tiempo real
```
Render Dashboard → nioval-webhook-server → Logs
```

### Reiniciar servicio (si es necesario)
```
Render Dashboard → nioval-webhook-server → Manual Deploy → Deploy latest commit
```

### Ver métricas
```
Render Dashboard → nioval-webhook-server → Metrics
```

### Actualizar código

Cada vez que hagas cambios:
```bash
git add .
git commit -m "Descripción de cambios"
git push
```

Render **detectará automáticamente** el push y desplegará la nueva versión.

---

## 💰 COSTOS

| Concepto | Costo |
|----------|-------|
| **Render Starter** | **$7/mes** |
| Twilio (2000 llamadas × 5 min) | ~$220-520/mes |
| OpenAI GPT-4 | ~$20/mes |
| **TOTAL** | **~$247-547/mes** |

---

## 🎯 VENTAJAS vs ngrok

| Aspecto | Render ($7/mes) | ngrok ($8/mes) |
|---------|----------------|----------------|
| Precio | $7/mes | $8/mes |
| URL permanente | ✅ | ✅ |
| PC encendida | ❌ No necesaria | ✅ Necesaria |
| Uptime | 99.9% | Depende de tu PC |
| Logs | ✅ Dashboard | ❌ |
| Auto-deploy | ✅ | ❌ |
| Para 2000 llamadas/mes | ✅ Ideal | ❌ No recomendado |

---

## 🔧 SOLUCIÓN DE PROBLEMAS

### Error: "Application failed to respond"
**Solución:** Verifica que el puerto sea dinámico en `servidor_llamadas.py`:
```python
port = int(os.getenv("PORT", 5000))
```

### Error: "Module not found"
**Solución:** Verifica que `requirements.txt` incluya todas las dependencias:
```bash
pip freeze > requirements.txt
```

### Error: Google Sheets authentication failed
**Solución:** Verifica que la variable `GOOGLE_APPLICATION_CREDENTIALS_JSON` contenga el JSON completo.

### Logs no aparecen
**Solución:**
1. Ve a Render Dashboard
2. Haz clic en tu servicio
3. Pestaña **Logs**
4. Selecciona "Live" en el dropdown

---

## ✅ CHECKLIST FINAL

Antes de declarar todo listo:

- [ ] ✅ Código subido a GitHub
- [ ] ✅ Web Service creado en Render
- [ ] ✅ Todas las variables de entorno configuradas
- [ ] ✅ Servicio desplegado y **Live**
- [ ] ✅ URL copiada y agregada al `.env` local
- [ ] ✅ Webhook configurado en Twilio Console
- [ ] ✅ Prueba de llamada exitosa
- [ ] ✅ Logs de Render muestran datos guardándose
- [ ] ✅ Google Sheets se actualiza correctamente

---

## 🎉 ¡LISTO!

Tu sistema NIOVAL está desplegado en Render y funcionando 24/7.

**URL permanente:** `https://nioval-webhook-server.onrender.com`

**Para hacer llamadas:**
```bash
python sistema_llamadas_nioval.py
```

Los webhooks llegarán automáticamente a Render, no necesitas tu PC encendida.

---

## 📞 PRÓXIMOS PASOS

1. **Hacer 5-10 llamadas de prueba** y revisar logs en Render
2. **Verificar que se guarden correctamente** en Google Sheets
3. **Monitorear costos** en Twilio Console
4. **Escalar gradualmente** a más llamadas

---

**Fecha:** 27 de diciembre 2024
**Sistema:** NIOVAL - Bruce W Sales Agent
**Deploy:** ✅ Listo para Render
