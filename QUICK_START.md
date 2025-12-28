# 🚀 Guía Rápida - Sistema de Llamadas NIOVAL

## ✅ Pre-requisitos

1. **Archivo de credenciales de Google**
   - Archivo: `bubbly-subject-412101-c969f4a975c5.json`
   - Ubicación: `C:\Users\PC 1\bubbly-subject-412101-c969f4a975c5.json`

2. **Spreadsheet de Google**
   - URL: https://docs.google.com/spreadsheets/d/1wgEentS16hJrcf6YdEnSpEBcp4SCBJ9TkOCZY439jV4/edit
   - Hoja: "LISTA DE CONTACTOS"
   - Compartido con el Service Account

3. **Python 3.8+**

---

## 📦 Instalación Rápida

```bash
# 1. Ir a la carpeta del proyecto
cd C:\Users\PC 1\AgenteVentas

# 2. Instalar dependencias
pip install -r requirements.txt

# 3. Verificar que el archivo de credenciales existe
dir C:\Users\PC 1\bubbly-subject-412101-c969f4a975c5.json
```

---

## 🧪 Prueba Rápida

### 1. Probar Conexión a Google Sheets

```bash
python nioval_sheets_adapter.py
```

**Salida esperada:**
```
✅ Autenticado correctamente con Google Sheets
✅ Spreadsheet abierto: [Nombre del spreadsheet]
✅ Hoja encontrada: LISTA DE CONTACTOS
✅ Conectado a: LISTA DE CONTACTOS

--- ESTADÍSTICAS GENERALES ---
Total contactos: XX
Con número: XX
Llamados: XX
Pendientes: XX
Progreso: XX%
```

Si ves errores:
- Verifica que el archivo `bubbly-subject-412101-c969f4a975c5.json` existe
- Comparte el spreadsheet con el email del Service Account (está dentro del JSON)

---

### 2. Ejecutar Sistema de Llamadas (Modo Simulación)

```bash
python sistema_llamadas_nioval.py
```

**Menú de opciones:**
```
1. Ver estadísticas generales
2. Ejecutar 5 llamadas de prueba  ← EMPIEZA CON ESTA
3. Ejecutar 10 llamadas
4. Ejecutar llamadas masivas (50)
0. Salir
```

**Recomendación:** Empieza con opción **2** (5 llamadas de prueba)

---

## 📊 Estructura del Spreadsheet

### Columnas en "LISTA DE CONTACTOS":

| Columna | Contenido | Descripción |
|---------|-----------|-------------|
| **A** | Nombre negocio | Nombre de la ferretería/negocio |
| **B** | Ciudad | Ubicación |
| **C** | Estado | Estado de México |
| **D** | Categoría | Tipo de negocio |
| **E** | **Número** | **Teléfono (se actualiza con WhatsApp validado)** |
| **F** | **Estado llamada** | **Vacío = Pendiente / Con valor = Ya llamado** |
| ... | *(Otras columnas)* | Columnas intermedias no utilizadas |
| **T** | Email | Se llena automáticamente al capturar |

### ⚠️ IMPORTANTE:

1. **Columna E (Número)**: El sistema lee los números de aquí
2. **Columna F (Estado)**:
   - Si está **VACÍA** → El contacto será llamado
   - Si tiene **CUALQUIER VALOR** → El contacto se omite (ya fue llamado)
   - **NOTA:** Este sistema **NO modifica** la columna F. Solo la verifica para saber qué contactos llamar.
   - La información de resultados de llamadas se registra en otro spreadsheet.

---

## 📱 Formatos de Número Soportados

El sistema normaliza automáticamente estos formatos:

```
✅ 662 101 2000     → +526621012000
✅ 323-112-7516     → +523231127516
✅ 81 1481 9779     → +528114819779
✅ 6621012000       → +526621012000
✅ +526621012000    → +526621012000
✅ 52 662 101 2000  → +526621012000
```

---

## 🔄 Flujo de Operación

### Modo Simulación (actual):

```
1. Sistema lee hoja "LISTA DE CONTACTOS"
2. Filtra contactos donde:
   - Columna E tiene número
   - Columna F está vacía
3. Para cada contacto:
   ├── Normaliza número
   ├── Simula llamada con Bruce W
   ├── Bruce conversa (GPT-4o)
   ├── Detecta WhatsApp/Email automáticamente
   ├── Registra WhatsApp/Email en columnas G/H (si se capturan)
   └── Los resultados de llamadas se guardan en otro spreadsheet
4. Muestra resumen
```

### Registro de Datos:

- **Columna E (Número)**: Se reemplaza con el WhatsApp validado si se captura
- **Columna T (Email)**: Se llena automáticamente si se captura
- **Resultados de llamadas**: Se guardan en otro spreadsheet (separado)

---

## 🧪 Ejemplo de Sesión

```bash
C:\Users\PC 1\AgenteVentas> python sistema_llamadas_nioval.py

╔═══════════════════════════════════════════════════════╗
║  SISTEMA DE LLAMADAS NIOVAL                           ║
║  Integrado con Google Sheets                          ║
╚═══════════════════════════════════════════════════════╝

✅ Autenticado correctamente con Google Sheets
✅ Spreadsheet abierto: NIOVAL Contactos
✅ Hoja encontrada: LISTA DE CONTACTOS
✅ Conectado a: LISTA DE CONTACTOS
✅ Validador de WhatsApp: formato

✅ Sistema listo
⏱️  Delay entre llamadas: 5s

📋 OPCIONES:
1. Ver estadísticas generales
2. Ejecutar 5 llamadas de prueba
3. Ejecutar 10 llamadas
4. Ejecutar llamadas masivas (50)
0. Salir

Selecciona una opción: 2

============================================================
📞 INICIANDO LLAMADAS - 2025-01-15 14:30
============================================================

📋 Contactos a llamar: 5

============================================================
📞 LLAMADA 1/5
============================================================

📞 Fila 15: Ferretería La Estrella
   Teléfono: +526621012000

🧪 MODO SIMULACIÓN

🎙️ Bruce: Hola, qué tal, muy buenas tardes. Me comunico de la empresa
NIOVAL con el fin de brindarles información de nuestros productos del
ramo ferretero. ¿Se encuentra el encargado de compras?

👤 Cliente: Sí, soy el encargado

🎙️ Bruce: Perfecto, mucho gusto. El motivo de mi llamada es...

👤 Cliente: Me interesa ver el catálogo

🎙️ Bruce: Excelente! Le puedo enviar el catálogo completo por WhatsApp...

👤 Cliente: Mi WhatsApp es 3312345678

📱 WhatsApp detectado: +523312345678

🎙️ Bruce: Perfecto, entonces anoto el WhatsApp: 33 12 34 56 78...

────────────────────────────────────────────────────────────
📊 RESUMEN DE LA LLAMADA:
   Interesado: ✅ Sí
   📱 WhatsApp: +523312345678
────────────────────────────────────────────────────────────

📱 Validando WhatsApp: +523312345678
✅ WhatsApp validado correctamente
✅ Número actualizado en fila 15 (columna E): +523312345678

⏳ Esperando 5s...

[... continúa con las demás llamadas ...]

============================================================
📊 RESUMEN DE LLAMADAS
============================================================
📞 Total llamadas: 5
✅ Exitosas: 4
📱 WhatsApps capturados: 3
📧 Emails capturados: 1
🔥 Con interés: 3
❄️  Sin interés: 1
❌ Errores: 0

📈 Tasa captura WhatsApp: 75.0%
============================================================
```

---

## 🔧 Configuración Avanzada (Opcional)

### Ajustar delay entre llamadas:

Edita `.env`:
```env
DELAY_LLAMADAS_SEG=10  # 10 segundos entre llamadas
```

### Cambiar método de validación de WhatsApp:

```env
# Opción 1: Solo formato (gratis, actual)
WHATSAPP_VALIDATOR_METHOD=formato

# Opción 2: Twilio (pago, ~$0.005 por consulta)
WHATSAPP_VALIDATOR_METHOD=twilio
TWILIO_ACCOUNT_SID=ACxxxxx
TWILIO_AUTH_TOKEN=xxxxx

# Opción 3: Evolution API (recomendado para producción)
WHATSAPP_VALIDATOR_METHOD=evolution
EVOLUTION_API_URL=http://localhost:8080
EVOLUTION_API_KEY=xxxxx
```

---

## ⚠️ Troubleshooting

### Error: "No se puede conectar a Google Sheets"

**Solución:**
```bash
# 1. Verificar que el archivo existe
dir C:\Users\PC 1\bubbly-subject-412101-c969f4a975c5.json

# 2. Abrir el archivo JSON y copiar el email del Service Account
# Busca la línea: "client_email": "xxxxx@xxxxx.iam.gserviceaccount.com"

# 3. Compartir el spreadsheet con ese email (Editor)
```

### Error: "Hoja 'LISTA DE CONTACTOS' no encontrada"

**Solución:**
- Verifica que la hoja se llama exactamente "LISTA DE CONTACTOS" (con mayúsculas)
- Si tiene otro nombre, edita `nioval_sheets_adapter.py` línea 27

### No se detectan contactos pendientes

**Solución:**
- Verifica que hay números en columna E
- Verifica que columna F está vacía para esos contactos
- Ejecuta prueba: `python nioval_sheets_adapter.py`

---

## 📝 Próximos Pasos

Una vez que confirmes que funciona en modo simulación:

1. **Integrar Twilio para llamadas reales**
   - Configurar credenciales en `.env`
   - Actualizar `sistema_llamadas_nioval.py` para usar Twilio en lugar de simulación

2. **Ajustar SYSTEM_PROMPT**
   - Personalizar script de Bruce según tus necesidades
   - Agregar/quitar productos
   - Modificar objeciones

3. **Producción**
   - Configurar servidor con webhook público
   - Programar llamadas automáticas
   - Monitorear KPIs

---

## 📞 Soporte

Para dudas:
- 📧 Email: soporte@nioval.com
- 📱 WhatsApp: +52 662 415 1997

---

**¡Listo para empezar! 🚀**

Ejecuta: `python sistema_llamadas_nioval.py`
