# 📞 GUÍA DE CONFIGURACIÓN TWILIO - Sistema NIOVAL

## ✅ PRE-REQUISITOS

Antes de empezar, asegúrate de tener:
- ✅ Cuenta de Twilio creada (https://www.twilio.com/try-twilio)
- ✅ Tarjeta de crédito para comprar número mexicano (~$1-2 USD/mes)
- ✅ Sistema NIOVAL funcionando en modo simulación

---

## 📋 PASO 1: OBTENER CREDENCIALES DE TWILIO

### 1.1 Iniciar sesión en Twilio Console
1. Ve a: https://console.twilio.com/
2. Inicia sesión con tu cuenta

### 1.2 Obtener Account SID y Auth Token
1. En el Dashboard principal verás:
   - **Account SID**: ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   - **Auth Token**: (haz clic en "Show" para verlo)

2. **COPIA ESTOS VALORES** - los necesitarás en el `.env`

---

## 📞 PASO 2: COMPRAR NÚMERO MEXICANO

### 2.1 Ir a Phone Numbers
1. En el menú lateral: **Phone Numbers** → **Manage** → **Buy a number**
2. O visita directamente: https://console.twilio.com/us1/develop/phone-numbers/manage/search

### 2.2 Buscar número mexicano
1. **Country**: Selecciona **Mexico (+52)**
2. **Capabilities**: Marca **Voice** ✅
3. **Number contains**: (opcional) puedes buscar un número específico
4. Haz clic en **Search**

### 2.3 Comprar el número
1. Verás una lista de números disponibles
2. Haz clic en **Buy** en el número que te guste
3. Confirma la compra

**Costo aproximado:**
- Número mexicano: ~$1-2 USD/mes
- Llamadas salientes: ~$0.02-0.05 USD/minuto

### 2.4 Copiar el número
- El número aparecerá en formato: **+52 XXX XXX XXXX**
- Cópialo completo (con el +52)

---

## 🔧 PASO 3: CONFIGURAR ARCHIVO `.env`

Abre el archivo `.env` en `C:\Users\PC 1\AgenteVentas\.env` y agrega estas líneas:

```env
# ========================================
# TWILIO CONFIGURATION
# ========================================

# Twilio Account SID (desde Twilio Console)
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# Twilio Auth Token (desde Twilio Console)
TWILIO_AUTH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# Número de teléfono Twilio (formato: +52XXXXXXXXXX)
TWILIO_PHONE_NUMBER=+52XXXXXXXXXX

# URL del webhook para recibir eventos de Twilio
# OPCIÓN 1 - Desarrollo (usando ngrok):
WEBHOOK_URL=https://tu-url-ngrok.ngrok-free.app

# OPCIÓN 2 - Producción (servidor público):
# WEBHOOK_URL=https://tu-servidor.com
```

### Ejemplo real:
```env
TWILIO_ACCOUNT_SID=AC1234567890abcdef1234567890abcd
TWILIO_AUTH_TOKEN=abcdef1234567890abcdef1234567890
TWILIO_PHONE_NUMBER=+523312345678
WEBHOOK_URL=https://abc123.ngrok-free.app
```

---

## 🌐 PASO 4: CONFIGURAR WEBHOOK (Desarrollo con ngrok)

### 4.1 Instalar ngrok
```bash
# Opción 1: Descargar desde https://ngrok.com/download
# Opción 2: Con Chocolatey
choco install ngrok

# Opción 3: Con scoop
scoop install ngrok
```

### 4.2 Crear cuenta en ngrok
1. Ve a: https://dashboard.ngrok.com/signup
2. Crea cuenta gratuita
3. Obtén tu authtoken en: https://dashboard.ngrok.com/get-started/your-authtoken

### 4.3 Configurar authtoken
```bash
ngrok config add-authtoken TU_AUTH_TOKEN_DE_NGROK
```

### 4.4 Iniciar ngrok
```bash
# Abre una terminal SEPARADA y ejecuta:
ngrok http 5000
```

Verás algo como:
```
Forwarding   https://abc123.ngrok-free.app -> http://localhost:5000
```

**IMPORTANTE:**
- ✅ Copia la URL `https://abc123.ngrok-free.app`
- ✅ Agrégala al `.env` como `WEBHOOK_URL`
- ⚠️ Esta URL cambia cada vez que reinicias ngrok (gratis)
- 💡 Con ngrok de pago ($8/mes) puedes tener URL fija

---

## 🔗 PASO 5: CONFIGURAR WEBHOOK EN TWILIO

### 5.1 Ir a configuración del número
1. Ve a: **Phone Numbers** → **Manage** → **Active numbers**
2. Haz clic en tu número comprado
3. Baja hasta la sección **Voice & Fax**

### 5.2 Configurar Voice URL
1. En **A CALL COMES IN**:
   - Selecciona: **Webhook**
   - URL: `https://tu-url-ngrok.ngrok-free.app/webhook-voz`
   - Método: **HTTP POST**

**Ejemplo:**
```
https://abc123.ngrok-free.app/webhook-voz
```

2. Haz clic en **Save configuration** al final de la página

---

## 🧪 PASO 6: PROBAR LA CONFIGURACIÓN

### 6.1 Verificar que todo esté listo

Ejecuta este script de verificación:

```bash
cd C:\Users\PC 1\AgenteVentas
python verificar_twilio.py
```

Si no existe, créalo:

```python
# verificar_twilio.py
import os
from dotenv import load_dotenv
from twilio.rest import Client

load_dotenv()

print("=" * 60)
print("VERIFICACIÓN DE CONFIGURACIÓN TWILIO")
print("=" * 60)

# Verificar variables
account_sid = os.getenv('TWILIO_ACCOUNT_SID')
auth_token = os.getenv('TWILIO_AUTH_TOKEN')
phone_number = os.getenv('TWILIO_PHONE_NUMBER')
webhook_url = os.getenv('WEBHOOK_URL')

print(f"\n✓ TWILIO_ACCOUNT_SID: {account_sid[:8]}... (OK)" if account_sid else "✗ TWILIO_ACCOUNT_SID: NO CONFIGURADO")
print(f"✓ TWILIO_AUTH_TOKEN: {auth_token[:8]}... (OK)" if auth_token else "✗ TWILIO_AUTH_TOKEN: NO CONFIGURADO")
print(f"✓ TWILIO_PHONE_NUMBER: {phone_number}" if phone_number else "✗ TWILIO_PHONE_NUMBER: NO CONFIGURADO")
print(f"✓ WEBHOOK_URL: {webhook_url}" if webhook_url else "✗ WEBHOOK_URL: NO CONFIGURADO")

# Probar conexión
if account_sid and auth_token:
    try:
        client = Client(account_sid, auth_token)

        # Obtener número
        number = client.incoming_phone_numbers.list(phone_number=phone_number, limit=1)

        if number:
            print(f"\n✅ CONEXIÓN EXITOSA")
            print(f"   Número encontrado: {number[0].phone_number}")
            print(f"   Friendly Name: {number[0].friendly_name}")
        else:
            print(f"\n⚠️ Número {phone_number} no encontrado en tu cuenta")

    except Exception as e:
        print(f"\n❌ ERROR DE CONEXIÓN: {e}")
else:
    print("\n⚠️ Completa las variables de entorno primero")

print("\n" + "=" * 60)
```

### 6.2 Iniciar el servidor de webhooks

**Terminal 1 - Servidor de webhooks:**
```bash
cd C:\Users\PC 1\AgenteVentas
python servidor_llamadas.py
```

Deberías ver:
```
🚀 Servidor de webhooks iniciado en http://0.0.0.0:5000
```

**Terminal 2 - ngrok (si estás en desarrollo):**
```bash
ngrok http 5000
```

### 6.3 Hacer una llamada de prueba

**Terminal 3 - Sistema de llamadas:**
```bash
cd C:\Users\PC 1\AgenteVentas
python sistema_llamadas_nioval.py
```

El sistema:
1. ✅ Leerá contactos de Google Sheets
2. ✅ Hará llamada vía Twilio
3. ✅ Bruce W conversará con el cliente
4. ✅ Guardará resultados en ambos spreadsheets

---

## 🎯 PASO 7: MODO DE OPERACIÓN

### Opción A: Desarrollo Local (Recomendado para testing)
```
Terminal 1: python servidor_llamadas.py
Terminal 2: ngrok http 5000
Terminal 3: python sistema_llamadas_nioval.py
```

### Opción B: Servidor Producción (Para uso continuo)
- Despliega `servidor_llamadas.py` en servidor con IP pública
- Usa Render, Railway, Heroku, DigitalOcean, etc.
- Configura `WEBHOOK_URL` con la URL pública
- Ejecuta `sistema_llamadas_nioval.py` desde cualquier lugar

---

## 📊 MONITOREO DE LLAMADAS

### Ver llamadas en Twilio Console
1. Ve a: **Monitor** → **Logs** → **Calls**
2. Verás todas las llamadas realizadas
3. Puedes escuchar grabaciones (si las activas)
4. Ver duración y costo

### Ver transcripciones en el sistema
- Las conversaciones se guardan en `llamadas/` (si está configurado)
- Los resultados en Google Sheets

---

## 💰 COSTOS ESTIMADOS

| Concepto | Costo Aproximado |
|----------|------------------|
| Número mexicano | $1-2 USD/mes |
| Llamadas salientes | $0.02-0.05 USD/minuto |
| OpenAI GPT-4o | $0.01 USD/llamada |
| ElevenLabs TTS | $0.001 USD/llamada |
| **Total por llamada (5 min)** | **$0.11-0.26 USD** |

**Ejemplo:** 100 llamadas/día × 5 min promedio = $11-26 USD/día

---

## 🔧 SOLUCIÓN DE PROBLEMAS

### Error: "Unable to create record: The number is not verified"
**Solución:** Tu cuenta Twilio está en modo Trial
1. Ve a: https://console.twilio.com/
2. Agrega fondos ($20 USD mínimo)
3. Espera activación (10-15 minutos)

### Error: "Webhook URL returned HTTP 404"
**Solución:** El webhook no está accesible
1. Verifica que `servidor_llamadas.py` esté corriendo
2. Verifica que ngrok esté corriendo
3. Verifica que la URL en Twilio Console sea correcta

### Error: "Authentication failed"
**Solución:** Credenciales incorrectas
1. Verifica `TWILIO_ACCOUNT_SID` en `.env`
2. Verifica `TWILIO_AUTH_TOKEN` en `.env`
3. Asegúrate de copiar completos (sin espacios)

### Las llamadas salen pero no se escucha a Bruce
**Solución:** Problema con ElevenLabs
1. Verifica `ELEVENLABS_API_KEY` en `.env`
2. Verifica `ELEVENLABS_AGENT_ID` en `.env`
3. Prueba el agente directamente en ElevenLabs Console

### ngrok da error "command not found"
**Solución:** No está instalado o no está en PATH
1. Descarga desde: https://ngrok.com/download
2. Extrae el archivo
3. Muévelo a una carpeta en tu PATH
4. O ejecuta con ruta completa: `C:\ruta\a\ngrok.exe http 5000`

---

## 📝 CHECKLIST FINAL

Antes de empezar con llamadas reales:

- [ ] ✅ Cuenta Twilio creada y verificada
- [ ] ✅ Número mexicano comprado
- [ ] ✅ `TWILIO_ACCOUNT_SID` en `.env`
- [ ] ✅ `TWILIO_AUTH_TOKEN` en `.env`
- [ ] ✅ `TWILIO_PHONE_NUMBER` en `.env`
- [ ] ✅ ngrok instalado y configurado
- [ ] ✅ `WEBHOOK_URL` en `.env` (URL de ngrok)
- [ ] ✅ Webhook configurado en Twilio Console
- [ ] ✅ `servidor_llamadas.py` corriendo
- [ ] ✅ ngrok corriendo
- [ ] ✅ Prueba con 1 número de prueba EXITOSA
- [ ] ✅ Google Sheets funcionando
- [ ] ✅ Fondos suficientes en Twilio ($20+ USD recomendado)

---

## 🎓 PRÓXIMOS PASOS

1. **Hacer 5-10 llamadas de prueba** con números conocidos
2. **Revisar transcripciones** y ajustar SYSTEM_PROMPT si es necesario
3. **Monitorear costos** en Twilio Console
4. **Escalar gradualmente** a más llamadas por día
5. **Configurar servidor de producción** cuando estés listo

---

## 📞 EJEMPLO DE FLUJO COMPLETO

```bash
# Terminal 1: Servidor de webhooks
cd C:\Users\PC 1\AgenteVentas
python servidor_llamadas.py

# Terminal 2: ngrok
ngrok http 5000

# Copiar URL de ngrok y agregarla al .env como WEBHOOK_URL
# Configurar webhook en Twilio Console

# Terminal 3: Ejecutar sistema
cd C:\Users\PC 1\AgenteVentas
python sistema_llamadas_nioval.py
```

**Resultado esperado:**
```
🚀 Sistema de Llamadas NIOVAL iniciado
✅ Conectado a spreadsheet de contactos
✅ Conectado a spreadsheet de resultados

📋 Obteniendo contactos pendientes...
✅ Encontrados 15 contactos pendientes

📞 Llamada 1/15: Ferretería El Tornillo
   Teléfono: +523312345678

[Bruce W llama y conversa con el cliente]

✅ Llamada completada - Duración: 5:30
💾 Guardando en Google Sheets...
✅ Contacto actualizado en LISTA DE CONTACTOS
✅ Resultado guardado en Respuestas de formulario 1

📞 Llamada 2/15: ...
```

---

## 🎉 ¡LISTO!

Siguiendo esta guía tendrás Twilio completamente configurado y funcionando con tu sistema NIOVAL.

**¿Necesitas ayuda?** Consulta la sección de Solución de Problemas o contacta soporte.

---

**Fecha de creación:** 27 de diciembre 2024
**Sistema:** NIOVAL - Bruce W Sales Agent
**Estado:** ✅ Guía completa lista para uso
