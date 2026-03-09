# 🚀 RESUMEN RÁPIDO - Configuración Twilio

## 📋 CHECKLIST DE CONFIGURACIÓN (5 pasos)

### ✅ PASO 1: Obtener Credenciales de Twilio (5 minutos)

1. Ve a: https://console.twilio.com/
2. Inicia sesión
3. En el Dashboard, copia:
   - **Account SID**: `ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx`
   - **Auth Token**: (haz clic en "Show")

### ✅ PASO 2: Comprar Número Mexicano (5 minutos)

1. Ve a: https://console.twilio.com/us1/develop/phone-numbers/manage/search
2. Selecciona **Country: Mexico (+52)**
3. Marca **Voice** ✅
4. Haz clic en **Search**
5. Compra un número (~$1-2 USD/mes)
6. Copia el número completo: `+52XXXXXXXXXX`

### ✅ PASO 3: Configurar Variables en `.env` (2 minutos)

Abre el archivo `.env` y reemplaza los valores:

```env
# Pega tus valores reales aquí:
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_PHONE_NUMBER=+52XXXXXXXXXX
```

### ✅ PASO 4: Instalar y Configurar ngrok (10 minutos)

**Opción A - Windows (Chocolatey):**
```bash
choco install ngrok
```

**Opción B - Descarga manual:**
1. Ve a: https://ngrok.com/download
2. Descarga para Windows
3. Extrae el archivo
4. Muévelo a `C:\ngrok\ngrok.exe`

**Configurar authtoken:**
1. Crea cuenta en: https://dashboard.ngrok.com/signup
2. Obtén authtoken: https://dashboard.ngrok.com/get-started/your-authtoken
3. Ejecuta:
```bash
ngrok config add-authtoken TU_AUTH_TOKEN
```

**Iniciar ngrok:**
```bash
ngrok http 5000
```

Verás algo como:
```
Forwarding   https://abc123.ngrok-free.app -> http://localhost:5000
```

**Copiar URL y agregarla al `.env`:**
```env
WEBHOOK_URL=https://abc123.ngrok-free.app
```

### ✅ PASO 5: Configurar Webhook en Twilio (3 minutos)

1. Ve a: https://console.twilio.com/us1/develop/phone-numbers/manage/incoming
2. Haz clic en tu número comprado
3. Baja hasta **Voice & Fax**
4. En **A CALL COMES IN**:
   - Selecciona: **Webhook**
   - URL: `https://tu-url-ngrok.ngrok-free.app/webhook-voz`
   - Método: **HTTP POST**
5. Haz clic en **Save configuration**

---

## 🧪 VERIFICACIÓN (5 minutos)

### 1. Verificar configuración:
```bash
cd C:\Users\PC 1\AgenteVentas
python verificar_twilio.py
```

Deberías ver:
```
✅ Variables de entorno: OK
✅ Conexión con Twilio: OK
✅ Número de teléfono: OK
✅ Saldo suficiente: OK
✅ Dependencias: OK
🎉 SISTEMA LISTO PARA HACER LLAMADAS CON TWILIO
```

### 2. Iniciar servidor de webhooks:
**Terminal 1:**
```bash
cd C:\Users\PC 1\AgenteVentas
python servidor_llamadas.py
```

Deberías ver:
```
🚀 Servidor de webhooks iniciado en http://0.0.0.0:5000
```

### 3. Iniciar ngrok (si no está corriendo):
**Terminal 2:**
```bash
ngrok http 5000
```

### 4. Hacer llamada de prueba:
**Terminal 3:**
```bash
cd C:\Users\PC 1\AgenteVentas
python sistema_llamadas_nioval.py
```

---

## 🎯 FLUJO COMPLETO

```
┌─────────────────────────────────────────────────────────────┐
│                  1. SISTEMA DE LLAMADAS                     │
│          (sistema_llamadas_nioval.py)                       │
│   - Lee contactos de Google Sheets                         │
│   - Inicia llamada vía Twilio                              │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│                      2. TWILIO                              │
│   - Recibe instrucción de llamar                           │
│   - Llama al número del cliente                            │
│   - Conecta con ElevenLabs                                 │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│                   3. ELEVENLABS                             │
│   - Bruce W conversa con el cliente                        │
│   - Hace las 7 preguntas de forma sutil                    │
│   - Captura WhatsApp, Email, etc.                          │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│                 4. SERVIDOR DE WEBHOOKS                     │
│            (servidor_llamadas.py + ngrok)                   │
│   - Recibe eventos de la llamada                           │
│   - Procesa transcripción                                  │
│   - Extrae datos capturados                                │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│                  5. GOOGLE SHEETS                           │
│   - Actualiza "LISTA DE CONTACTOS" (columna E, T)         │
│   - Guarda "Respuestas de formulario 1" (7 preguntas)     │
└─────────────────────────────────────────────────────────────┘
```

---

## 💰 COSTOS

| Item | Costo |
|------|-------|
| Número mexicano | ~$1-2 USD/mes |
| Llamada saliente | ~$0.02-0.05 USD/minuto |
| OpenAI GPT-4o | ~$0.01 USD/llamada |
| ElevenLabs | ~$0.001 USD/llamada |
| **Total por llamada (5 min)** | **~$0.11-0.26 USD** |

**Ejemplo:**
- 10 llamadas/día × 5 min promedio = $1.10-2.60 USD/día
- 100 llamadas/día × 5 min promedio = $11-26 USD/día

**Recomendación:** Agregar $20-50 USD a Twilio para empezar.

---

## 🔧 SOLUCIÓN RÁPIDA DE PROBLEMAS

### Error: "Unable to create record: The number is not verified"
```
Tu cuenta está en modo Trial.
Solución: Agrega fondos ($20 USD mínimo) en https://console.twilio.com/billing
```

### Error: "Webhook URL returned HTTP 404"
```
El webhook no está accesible.
Solución:
1. Verifica que servidor_llamadas.py esté corriendo
2. Verifica que ngrok esté corriendo
3. Verifica que la URL en Twilio Console sea correcta
```

### Error: "Authentication failed"
```
Credenciales incorrectas.
Solución: Revisa TWILIO_ACCOUNT_SID y TWILIO_AUTH_TOKEN en .env
```

### ngrok: "command not found"
```
ngrok no está instalado.
Solución:
1. Instala con: choco install ngrok
2. O descarga desde: https://ngrok.com/download
```

---

## 📝 COMANDOS ÚTILES

### Verificar configuración:
```bash
python verificar_twilio.py
```

### Iniciar sistema completo:
```bash
# Terminal 1
python servidor_llamadas.py

# Terminal 2
ngrok http 5000

# Terminal 3
python sistema_llamadas_nioval.py
```

### Ver logs de Twilio:
https://console.twilio.com/us1/monitor/logs/calls

### Ver saldo:
https://console.twilio.com/billing

---

## 📚 DOCUMENTACIÓN COMPLETA

Para guía detallada, ver: [CONFIGURACION_TWILIO.md](CONFIGURACION_TWILIO.md)

---

## ✅ CHECKLIST FINAL

Antes de hacer llamadas reales:

- [ ] Cuenta Twilio creada
- [ ] Número mexicano comprado
- [ ] Variables en `.env` configuradas
- [ ] ngrok instalado y corriendo
- [ ] Webhook configurado en Twilio Console
- [ ] `servidor_llamadas.py` corriendo
- [ ] `verificar_twilio.py` ejecutado exitosamente
- [ ] Fondos suficientes en Twilio ($20+ USD)
- [ ] Google Sheets funcionando
- [ ] Prueba con 1 número de prueba exitosa

---

**Tiempo total estimado:** ~30-40 minutos
**Estado:** ✅ Listo para configurar

🎉 **¡Sigue estos pasos y tendrás Twilio funcionando!**
