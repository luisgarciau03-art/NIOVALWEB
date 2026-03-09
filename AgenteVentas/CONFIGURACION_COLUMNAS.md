# 📋 Configuración de Columnas - Sistema NIOVAL

## Hoja: "LISTA DE CONTACTOS"

### 📊 Estructura de Columnas

| Columna | Nombre | Tipo | Descripción |
|---------|--------|------|-------------|
| **A** | Nombre Negocio | Texto | Nombre de la ferretería/negocio |
| **B** | Ciudad | Texto | Ubicación del negocio |
| **C** | Estado | Texto | Estado de México |
| **D** | Categoría | Texto | Tipo de negocio (ej: Ferretería) |
| **E** | **Número** | **Teléfono** | **Lee y escribe** |
| **F** | **Estado Llamada** | **Estado** | **Solo lee** |
| **G-S** | *(Varias)* | Varios | Columnas intermedias no usadas por el sistema |
| **T** | Email | Texto | **Solo escribe** |

---

## 🔄 Operaciones por Columna

### Columna E: Número (Teléfono)
**Operación:** LECTURA y ESCRITURA

#### 📖 Lectura:
- Sistema lee los números de aquí para llamar
- Soporta múltiples formatos:
  ```
  662 101 2000
  323-112-7516
  81 1481 9779
  6621012000
  +526621012000
  ```
- Normaliza automáticamente a formato: `+52XXXXXXXXXX`

#### ✍️ Escritura:
- **SOLO si se captura WhatsApp válido durante la llamada**
- Proceso:
  1. Cliente proporciona su WhatsApp
  2. Sistema valida que el número tenga WhatsApp activo
  3. Si es válido: **REEMPLAZA** el número original con el WhatsApp validado
  4. Si no es válido: **NO modifica** la columna

**Ejemplo:**
```
Antes:  662 101 2000
Durante: Cliente dice "Mi WhatsApp es 3312345678"
Valida:  ✅ +523312345678 tiene WhatsApp activo
Después: +523312345678
```

---

### Columna F: Estado Llamada
**Operación:** SOLO LECTURA

#### 📖 Lectura:
- Sistema verifica si está vacía
- **Vacía** = Contacto pendiente de llamar
- **Con valor** = Ya fue llamado (omitir)

#### ❌ NO Escritura:
- Este sistema **NUNCA** escribe en columna F
- Los resultados de llamadas se guardan en otro spreadsheet

---

### Columna T: Email
**Operación:** SOLO ESCRITURA

#### ✍️ Escritura:
- Si durante la llamada el cliente proporciona su email
- Sistema detecta automáticamente el email en la conversación
- Escribe el email validado en columna T

**Ejemplo de detección:**
```
Cliente: "Mi correo es ventas@ferreteriaelangel.com"
→ Sistema escribe en columna T: ventas@ferreteriaelangel.com
```

---

## 🔍 Validación de WhatsApp

El sistema soporta 3 métodos de validación (configurables en `.env`):

### 1. **Método: "formato"** (Por defecto, gratis)
```env
WHATSAPP_VALIDATOR_METHOD=formato
```
- Solo valida que el formato sea correcto
- NO verifica si tiene WhatsApp activo
- Ideal para testing
- ⚠️ Puede actualizar números que no tienen WhatsApp

### 2. **Método: "twilio"** (Pago, preciso)
```env
WHATSAPP_VALIDATOR_METHOD=twilio
TWILIO_ACCOUNT_SID=ACxxxxx
TWILIO_AUTH_TOKEN=xxxxx
```
- Usa Twilio Lookup API
- Verifica si el número tiene WhatsApp activo
- Costo: ~$0.005 USD por validación
- ✅ Recomendado para producción

### 3. **Método: "evolution"** (Recomendado)
```env
WHATSAPP_VALIDATOR_METHOD=evolution
EVOLUTION_API_URL=http://localhost:8080
EVOLUTION_API_KEY=tu_api_key
```
- Usa Evolution API (WhatsApp Business API)
- Verifica si el número tiene WhatsApp activo
- Más económico que Twilio
- ✅ Mejor opción para producción

---

## 📝 Flujo Completo de Operaciones

### 1. Antes de la llamada:
```
┌─────────────────────────────────────┐
│ LECTURA de "LISTA DE CONTACTOS"     │
├─────────────────────────────────────┤
│ • Lee columna E: Obtiene números    │
│ • Lee columna F: Verifica que esté  │
│   vacía (filtro de pendientes)      │
└─────────────────────────────────────┘
```

### 2. Durante la llamada:
```
┌─────────────────────────────────────┐
│ Bruce W conversa con el cliente     │
├─────────────────────────────────────┤
│ Cliente: "Mi WhatsApp es XXX"       │
│ → Sistema extrae: +52XXXXXXXXXX     │
│                                     │
│ Cliente: "Mi email es XXX@YYY.com"  │
│ → Sistema extrae: XXX@YYY.com       │
└─────────────────────────────────────┘
```

### 3. Después de la llamada:
```
┌─────────────────────────────────────────────┐
│ VALIDACIÓN Y ESCRITURA                      │
├─────────────────────────────────────────────┤
│ 1. Valida WhatsApp capturado                │
│    ├─ ✅ Tiene WhatsApp activo:             │
│    │   → ESCRIBE en columna E (reemplaza)   │
│    └─ ❌ No tiene WhatsApp:                 │
│        → NO modifica columna E              │
│                                             │
│ 2. Registra Email                           │
│    └─ ESCRIBE en columna T                  │
│                                             │
│ 3. Resultados de llamada                    │
│    └─ ESCRIBE en otro spreadsheet           │
└─────────────────────────────────────────────┘
```

---

## ⚙️ Configuración Recomendada

### Para Testing (sin costos):
```env
WHATSAPP_VALIDATOR_METHOD=formato
DELAY_LLAMADAS_SEG=5
```

### Para Producción (con validación real):
```env
WHATSAPP_VALIDATOR_METHOD=evolution
EVOLUTION_API_URL=http://localhost:8080
EVOLUTION_API_KEY=tu_api_key
DELAY_LLAMADAS_SEG=60
```

---

## ✅ Checklist de Verificación

Antes de ejecutar el sistema, verifica:

- [ ] Columna E tiene números de teléfono
- [ ] Columna F está vacía para contactos pendientes
- [ ] Archivo de credenciales Google existe: `bubbly-subject-412101-c969f4a975c5.json`
- [ ] Spreadsheet compartido con Service Account
- [ ] Hoja "LISTA DE CONTACTOS" existe
- [ ] Método de validación configurado en `.env`
- [ ] Si usas Evolution/Twilio: credenciales configuradas

---

## 🎯 Resumen Visual

```
COLUMNAS DE "LISTA DE CONTACTOS"
═════════════════════════════════════════════════════════════

 A    B       C      D          E           F        ...    T
┌───┬──────┬──────┬─────┬──────────────┬─────────┬─────┬───────┐
│NOM│CIUDAD│ESTADO│CAT  │   NÚMERO     │ ESTADO  │ ... │ EMAIL │
│BRE│      │      │     │              │ LLAMADA │     │       │
├───┼──────┼──────┼─────┼──────────────┼─────────┼─────┼───────┤
│   │      │      │     │              │         │     │       │
│ ✓ │  ✓   │  ✓   │  ✓  │  📖 LEE      │ 📖 LEE  │     │✍️ ESC │
│   │      │      │     │  ✍️ ESCRIBE  │ ❌ NO   │     │       │
│   │      │      │     │  (WhatsApp   │ ESCRIBE │     │       │
│   │      │      │     │   validado)  │         │     │       │
└───┴──────┴──────┴─────┴──────────────┴─────────┴─────┴───────┘

📖 = LECTURA
✍️ = ESCRITURA
❌ = NO MODIFICA
```

---

**Última actualización:** 2025-01-XX
**Versión del sistema:** 1.0.0
