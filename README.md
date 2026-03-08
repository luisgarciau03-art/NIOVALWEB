# 🤖 Sistema de Llamadas Automatizadas - NIOVAL

**Bruce W** - Agente de Ventas Inteligente con IA

Sistema completo de llamadas automatizadas para prospectar clientes del ramo ferretero en México.

---

## 📋 Características Principales

### ✅ **Gestión Completa de Llamadas**
- ✅ Llamadas salientes automáticas con Twilio
- ✅ Conversaciones inteligentes con GPT-4o
- ✅ Voz natural con ElevenLabs
- ✅ Detección automática de interés
- ✅ Captura de WhatsApp y Email
- ✅ Reprogramación automática

### ✅ **Validación de WhatsApp**
- ✅ Validación en tiempo real
- ✅ Múltiples métodos (Twilio, Evolution API, Formato)
- ✅ Sistema de cache para optimización

### ✅ **Google Sheets Integration**
- ✅ Contactos centralizados
- ✅ Registro de llamadas
- ✅ Gestión de leads
- ✅ KPIs automáticos
- ✅ Dashboard en tiempo real

### ✅ **Métricas y KPIs**
- ✅ Tasa de contacto
- ✅ Tasa de conversión
- ✅ Duración promedio de llamadas
- ✅ Leads por temperatura (Frío/Tibio/Caliente)
- ✅ Reportes diarios automáticos

---

## 🏗️ Arquitectura del Sistema

```
┌─────────────────────────────────────────────────────────┐
│              SISTEMA AUTOMATIZADO                       │
│  ┌──────────────────────────────────────────────────┐  │
│  │  sistema_automatizado.py                          │  │
│  │  - Programación de llamadas                       │  │
│  │  - Gestión de reprogramadas                       │  │
│  │  - Reportes y KPIs                                │  │
│  └─────────────┬────────────────────────────────────┘  │
│                │                                         │
│   ┌────────────┴─────────────┬──────────────────────┐  │
│   │                          │                      │  │
│   ▼                          ▼                      ▼  │
│ ┌─────────────┐   ┌──────────────────┐   ┌──────────┐ │
│ │ Bruce W     │   │ Google Sheets    │   │ WhatsApp │ │
│ │ (Agente IA) │◄──┤ Manager          │◄──┤ Validator│ │
│ │             │   │                  │   │          │ │
│ │ - GPT-4o    │   │ - Contactos      │   │ - Twilio │ │
│ │ - ElevenLabs│   │ - Llamadas       │   │ - Evolution│
│ │ - Twilio    │   │ - Leads          │   │ - Formato│ │
│ │             │   │ - KPIs           │   │          │ │
│ └─────────────┘   └──────────────────┘   └──────────┘ │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

---

## 📦 Instalación

### 1. Clonar o descargar el proyecto

```bash
cd C:\Users\PC 1\AgenteVentas
```

### 2. Crear entorno virtual (recomendado)

```bash
python -m venv venv
venv\Scripts\activate  # Windows
```

### 3. Instalar dependencias

```bash
pip install -r requirements.txt
```

### 4. Configurar variables de entorno

Crea un archivo `.env` en la raíz del proyecto:

```env
# ===== OpenAI =====
OPENAI_API_KEY=sk-proj-xxxxx

# ===== ElevenLabs =====
ELEVENLABS_API_KEY=sk_xxxxx
ELEVENLABS_VOICE_ID=xxxxx
ELEVENLABS_AGENT_ID=agent_xxxxx

# ===== Twilio =====
TWILIO_ACCOUNT_SID=ACxxxxx
TWILIO_AUTH_TOKEN=xxxxx
TWILIO_PHONE_NUMBER=+52xxxxx

# ===== Google Sheets =====
GOOGLE_CREDENTIALS_FILE=credentials.json
SPREADSHEET_NAME=NIOVAL - Sistema de Llamadas

# ===== WhatsApp Validator =====
# Opciones: "formato", "twilio", "evolution"
WHATSAPP_VALIDATOR_METHOD=formato

# Evolution API (opcional, para validación real de WhatsApp)
EVOLUTION_API_URL=http://localhost:8080
EVOLUTION_API_KEY=xxxxx

# ===== Configuración de Llamadas =====
LLAMADAS_POR_DIA=100
DELAY_LLAMADAS_SEG=60
HORARIO_INICIO=09:00
HORARIO_FIN=17:00

# ===== Webhook URL (para Twilio) =====
WEBHOOK_URL=https://tu-servidor.com
```

---

## 🚀 Uso del Sistema

### Opción 1: Llamadas Interactivas (Testing)

```bash
python agente_ventas.py
```

Esto inicia una conversación de prueba en consola donde puedes simular respuestas del cliente.

### Opción 2: Sistema Automatizado

```bash
python sistema_automatizado.py
```

**Menú de opciones:**

1. **Ejecutar llamadas ahora (manual)** - Inicia llamadas inmediatamente
2. **Programar llamadas automáticas** - Modo continuo 24/7
3. **Generar reporte del día** - Ver estadísticas
4. **Ver resumen general** - Métricas globales
5. **Ejecutar 1 llamada de prueba** - Testing

### Opción 3: Servidor de Webhooks (Producción)

```bash
python servidor_llamadas.py
```

Inicia el servidor Flask que maneja webhooks de Twilio.

**Endpoints disponibles:**
- `POST /iniciar-llamada` - Inicia llamada individual
- `POST /llamadas-masivas` - Llamadas en lote
- `POST /webhook-voz` - Webhook de Twilio
- `GET /status/<call_sid>` - Estado de llamada

---

## 📊 Google Sheets - Estructura

El sistema crea automáticamente las siguientes hojas:

### 1. **Contactos**
Almacena todos los clientes potenciales.

| Campo | Descripción |
|-------|-------------|
| ID | Identificador único |
| Nombre Negocio | Nombre de la ferretería/negocio |
| Teléfono | Teléfono de contacto |
| WhatsApp | Número de WhatsApp validado |
| WhatsApp Válido | Sí/No |
| Email | Correo electrónico |
| Ciudad | Ubicación |
| Prioridad | 1-5 (5 = máxima) |
| Estado Contacto | Pendiente/Contactado/No interesado |

### 2. **Llamadas**
Registro de todas las llamadas realizadas.

| Campo | Descripción |
|-------|-------------|
| ID Llamada | Identificador |
| ID Contacto | Referencia al contacto |
| Fecha Llamada | Timestamp |
| Duración (seg) | Segundos de llamada |
| Estado | contestada/no_contesta/ocupado/reprogramada |
| WhatsApp Capturado | Número obtenido |
| Email Capturado | Email obtenido |
| Nivel Interés | Bajo/Medio/Alto |
| Objeciones | Objeciones detectadas |

### 3. **Leads**
Clientes con interés confirmado.

| Campo | Descripción |
|-------|-------------|
| ID Lead | Identificador |
| Nombre Contacto | Persona de contacto |
| Temperatura | Frío/Tibio/Caliente |
| Productos Interés | Productos mencionados |
| Siguiente Paso | Acción de seguimiento |
| Estado Lead | Nuevo/Contactado/Negociación/Cerrado |

### 4. **KPIs Diarios**
Métricas automáticas por día.

| Métrica | Descripción |
|---------|-------------|
| Llamadas Realizadas | Total del día |
| Tasa Contacto (%) | % de llamadas contestadas |
| Tasa Conversión (%) | % de leads generados |
| WhatsApps Capturados | Cantidad |
| Leads Generados | Por temperatura |

### 5. **Reprogramadas**
Llamadas pendientes de reprogramación.

---

## 🔧 Configuración Detallada

### Google Sheets

1. Ir a [Google Cloud Console](https://console.cloud.google.com/)
2. Crear nuevo proyecto
3. Habilitar Google Sheets API y Google Drive API
4. Crear credenciales (Service Account)
5. Descargar archivo JSON de credenciales
6. Guardar como `credentials.json` en la raíz
7. Compartir tu Google Sheet con el email del Service Account

### Twilio

1. Crear cuenta en [Twilio](https://www.twilio.com/)
2. Comprar número telefónico mexicano (+52)
3. Configurar webhook URL en el número
4. Copiar Account SID y Auth Token al `.env`

### ElevenLabs

1. Crear cuenta en [ElevenLabs](https://elevenlabs.io/)
2. Crear/elegir voz para Bruce W
3. Copiar API Key y Voice ID al `.env`

---

## 📱 Validación de WhatsApp

El sistema soporta 3 métodos de validación:

### 1. **Por Formato** (Gratis, por defecto)
```env
WHATSAPP_VALIDATOR_METHOD=formato
```
- Solo valida formato del número
- No verifica si está activo
- Ideal para testing

### 2. **Twilio Lookup** (Pago, preciso)
```env
WHATSAPP_VALIDATOR_METHOD=twilio
```
- Valida si el número existe
- Verifica operador
- Costo: ~$0.005 USD por consulta

### 3. **Evolution API** (Recomendado para producción)
```env
WHATSAPP_VALIDATOR_METHOD=evolution
EVOLUTION_API_URL=http://localhost:8080
EVOLUTION_API_KEY=tu_api_key
```
- Valida si tiene WhatsApp activo
- Requiere servidor Evolution API
- Más preciso y económico

---

## 📈 Métricas y KPIs

### KPIs Automáticos Calculados:

1. **Tasa de Contacto**
   ```
   (Llamadas Contestadas / Llamadas Realizadas) × 100
   ```

2. **Tasa de Conversión**
   ```
   (Leads Generados / Llamadas Contestadas) × 100
   ```

3. **Duración Promedio**
   ```
   Duración Total / Llamadas Contestadas
   ```

4. **Efectividad por Hora**
   - Detecta la hora con mayor tasa de contacto

5. **Distribución de Leads**
   - Frío: Sin interés inmediato
   - Tibio: Interés moderado, seguimiento
   - Caliente: Alta probabilidad de cierre

---

## 🔄 Flujo de Trabajo Automático

### Modo Continuo (24/7)

```bash
python sistema_automatizado.py
# Seleccionar opción 2
```

El sistema ejecutará:

1. **9:00 AM** - Inicia llamadas del día
2. **Cada hora** - Actualiza KPIs
3. **Cada 4 horas** - Revisa reprogramadas
4. **17:00 PM** - Finaliza llamadas
5. **Continuo** - Monitorea webhooks de Twilio

### Reprogramación Automática

Cuando un cliente dice:
- "Llámame después"
- "No tengo tiempo ahora"
- "No contesta"

El sistema:
1. Detecta la reprogramación
2. Sugiere fecha/hora
3. Registra en hoja "Reprogramadas"
4. Programa llamada automática

---

## 🧪 Testing

### Modo Simulación (Sin Twilio)

```python
# En sistema_automatizado.py
sistema = SistemaAutomatizado()
sistema.realizar_llamada(contacto)  # Simula llamada sin Twilio
```

### Testing de Componentes

```bash
# Test Google Sheets
python google_sheets_manager.py

# Test WhatsApp Validator
python whatsapp_validator.py
```

---

## 📝 Agregar Contactos

### Opción 1: Manualmente en Google Sheets

1. Abrir el spreadsheet
2. Ir a hoja "Contactos"
3. Agregar fila con:
   - Nombre Negocio
   - Teléfono (+52XXXXXXXXXX)
   - Ciudad
   - Prioridad (1-5)

### Opción 2: Desde Python

```python
from google_sheets_manager import GoogleSheetsManager

manager = GoogleSheetsManager()

# Agregar contacto individual
manager.agregar_contacto(
    nombre_negocio="Ferretería La Estrella",
    telefono="+523312345678",
    ciudad="Guadalajara",
    prioridad=5
)

# Agregar múltiples contactos
contactos = [
    {
        'nombre_negocio': 'Tlapalería González',
        'telefono': '+523398765432',
        'ciudad': 'Zapopan',
        'prioridad': 4
    },
    # ... más contactos
]

manager.agregar_contactos_masivo(contactos)
```

### Opción 3: Importar desde CSV/Excel

```python
import pandas as pd

# Leer CSV
df = pd.read_csv('contactos.csv')

# Convertir a lista de diccionarios
contactos = df.to_dict('records')

# Agregar masivamente
manager.agregar_contactos_masivo(contactos)
```

---

## 🛠️ Mantenimiento

### Actualizar KPIs Manualmente

```python
from google_sheets_manager import GoogleSheetsManager

manager = GoogleSheetsManager()
manager.actualizar_kpis_diarios()
```

### Ver Reportes

```python
# KPIs últimos 7 días
kpis = manager.obtener_kpis_ultimos_dias(dias=7)

# Resumen general
resumen = manager.obtener_resumen_general()
print(resumen)
```

### Limpiar Llamadas Antiguas

```python
# Implementar lógica de limpieza si es necesario
# Por ahora todas las llamadas se mantienen en el histórico
```

---

## ⚠️ Troubleshooting

### Error: "No se puede conectar a Google Sheets"
- Verifica que `credentials.json` esté en la raíz
- Comparte el Sheet con el email del Service Account
- Revisa que las APIs estén habilitadas

### Error: "Twilio authentication failed"
- Verifica Account SID y Auth Token en `.env`
- Confirma que el número esté activo
- Revisa saldo de la cuenta

### Error: "WhatsApp validation timeout"
- Si usas Evolution API, verifica que el servidor esté corriendo
- Intenta cambiar a método "formato" temporalmente
- Revisa configuración de Evolution API

### Las llamadas no se programan
- Verifica formato de HORARIO_INICIO y HORARIO_FIN
- Confirma que el sistema esté en modo continuo
- Revisa que haya contactos pendientes

---

## 📞 Soporte y Contacto

Para dudas o problemas:

- 📧 Email: soporte@nioval.com
- 📱 WhatsApp: +52 662 415 1997
- 🌐 Sitio web: www.nioval.com

---

## 📄 Licencia

Copyright © 2025 NIOVAL
Todos los derechos reservados.

---

## 🔮 Próximas Mejoras

- [ ] Integración con CRM (HubSpot/Salesforce)
- [ ] Análisis de sentimientos en llamadas
- [ ] Envío automático de catálogos por WhatsApp
- [ ] Dashboard web en tiempo real
- [ ] Reportes PDF automáticos por email
- [ ] Integración con WhatsApp Business API
- [ ] A/B Testing de scripts de ventas
- [ ] Predicción de mejor hora para llamar (ML)

---

**¡Éxito con las ventas! 🚀**
