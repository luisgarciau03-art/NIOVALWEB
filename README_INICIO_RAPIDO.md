# 🚀 INICIO RÁPIDO - Sistema NIOVAL

**Sistema de llamadas automatizadas con Bruce W**

---

## ⚡ Empezar en 3 Pasos

### 1️⃣ Instalar Dependencias

```bash
pip install -r requirements.txt
```

### 2️⃣ Probar la Integración ⭐ RECOMENDADO

```bash
python test_integracion_completa.py
```

Este script te mostrará:
- ✅ Conexión al Google Spreadsheet
- ✅ Contactos pendientes con toda su información
- ✅ Contexto que Bruce W recibirá antes de llamar
- ✅ Qué preguntará Bruce y qué NO

### 3️⃣ Ejecutar Llamadas de Prueba

```bash
python sistema_llamadas_nioval.py
```

Selecciona opción 2: **Ejecutar 5 llamadas de prueba**

---

## 📚 Documentación Completa

| Archivo | Contenido |
|---------|-----------|
| **[ESTADO_FINAL_SISTEMA.md](ESTADO_FINAL_SISTEMA.md)** | ⭐ Estado actual completo del sistema |
| **[INTEGRACION_SPREADSHEET_FINAL.md](INTEGRACION_SPREADSHEET_FINAL.md)** | Documentación de integración con Spreadsheet |
| **[RESUMEN_FINAL.md](RESUMEN_FINAL.md)** | Pendientes críticos y roadmap |

---

## 🎯 Lo Que Hace el Sistema

### Bruce W YA CONOCE (del Spreadsheet):
- ✅ Nombre del negocio (columna B)
- ✅ Ciudad (columna C)
- ✅ Categoría (columna D)
- ✅ Domicilio (columna H)
- ✅ Horario (columna M)
- ✅ Puntuación Google Maps (columna I)
- ✅ Número de reseñas (columna J)

### Bruce W PREGUNTA:
- ✅ WhatsApp (PRIORIDAD #1) → Valida y actualiza columna E
- ✅ Email (si no tiene WhatsApp) → Escribe en columna T
- ✅ Nombre del contacto (opcional)

### Bruce W NUNCA PREGUNTA:
- ❌ "¿Cómo se llama su negocio?" (ya lo sabe)
- ❌ "¿En qué ciudad está?" (ya lo sabe)
- ❌ "¿Cuál es su dirección?" (ya la sabe)
- ❌ "¿A qué hora abren?" (ya lo sabe)

---

## 📋 Ejemplo de Conversación

### ❌ ANTES (sin integración):
```
Bruce: Hola, buenas tardes, soy Bruce de NIOVAL...
Cliente: Hola
Bruce: ¿Cómo se llama su negocio?
Cliente: San Benito Ferretería
Bruce: ¿En qué ciudad está?
Cliente: Hermosillo
Bruce: ¿Cuál es su dirección?
Cliente: Av Veracruz
Bruce: ¿Cuál es su WhatsApp?
```
**Resultado:** 6 preguntas

### ✅ AHORA (con integración):
```
Bruce: Hola, buenas tardes, soy Bruce de NIOVAL. El motivo
       de mi llamada es presentarle nuestros productos del
       ramo ferretero. ¿Le interesaría recibir información?
Cliente: Sí
Bruce: Excelente. ¿Cuál es su WhatsApp para enviarle el catálogo?
```
**Resultado:** 1 pregunta (la importante)

---

## 🔴 Pendientes Críticos

### 1. Spreadsheet de Resultados (NO CONFIGURADO)
Los resultados de llamadas NO se guardan en ningún lado.

**Acción requerida:**
- Proporcionar URL del spreadsheet de resultados
- Definir estructura de columnas
- Implementar integración

### 2. Twilio (SIMULACIÓN ACTIVA)
Sistema funciona en modo simulación. Para llamadas reales:

**Acción requerida:**
- Obtener credenciales Twilio
- Configurar en `.env`
- Configurar webhook

### 3. Validación Real de WhatsApp (FORMATO SOLAMENTE)
Actualmente solo valida formato, no verifica WhatsApp activo.

**Acción requerida para producción:**
- Configurar Twilio Lookup o Evolution API

---

## 🧪 Scripts de Prueba

| Script | Descripción |
|--------|-------------|
| `test_integracion_completa.py` | ⭐ Test completo - EJECUTAR PRIMERO |
| `ver_estructura_sheets.py` | Ver estructura del spreadsheet |
| `nioval_sheets_adapter.py` | Probar adaptador (ejecutar directamente) |

---

## 📊 Archivos del Sistema

### Archivos Principales:
- `nioval_sheets_adapter.py` - Conexión con Google Spreadsheet
- `agente_ventas.py` - Agente Bruce W con GPT-4o
- `sistema_llamadas_nioval.py` - Sistema de llamadas
- `whatsapp_validator.py` - Validación de WhatsApp

### Configuración:
- `.env.example` - Plantilla de configuración
- `requirements.txt` - Dependencias

### Documentación:
- `ESTADO_FINAL_SISTEMA.md` - ⭐ Estado completo
- `INTEGRACION_SPREADSHEET_FINAL.md` - Integración Spreadsheet
- `RESUMEN_FINAL.md` - Pendientes y roadmap

---

## 💡 Próximo Paso Recomendado

```bash
# Ejecutar test de integración completa
python test_integracion_completa.py
```

Este script te dirá exactamente qué información tiene Bruce y qué NO preguntará.

---

## 📞 ¿Necesitas Ayuda?

1. **Si hay errores de conexión:**
   - Verificar que existe: `C:\Users\PC 1\bubbly-subject-412101-c969f4a975c5.json`
   - Verificar que el Service Account tiene acceso al Spreadsheet
   - Verificar que la hoja se llama "LISTA DE CONTACTOS"

2. **Si quieres configurar llamadas reales:**
   - Ver [RESUMEN_FINAL.md](RESUMEN_FINAL.md) sección "Pendientes Críticos"

3. **Si quieres ajustar comportamiento de Bruce:**
   - Editar `SYSTEM_PROMPT` en [agente_ventas.py](agente_ventas.py)

---

**Estado:** ✅ Sistema completamente integrado y listo para testing
**Próximo paso:** 🧪 Ejecutar `python test_integracion_completa.py`
