# ⚠️ Aclaración sobre TABLERO vs SPREADSHEET

## 📊 Situación Actual

### Archivo Excel: "TABLERO DE NIOVAL Yahir .xlsx"
- **Propósito:** Solo una MUESTRA/EXPORTACIÓN
- **NO es la fuente de verdad**
- **NO se debe leer directamente**

### Google Spreadsheet: "LISTA DE CONTACTOS"
- **URL:** https://docs.google.com/spreadsheets/d/1wgEentS16hJrcf6YdEnSpEBcp4SCBJ9TkOCZY439jV4/edit
- **Es la FUENTE DE VERDAD**
- **Se actualiza en tiempo real**
- **Bruce trabaja directamente con esto**

---

## 🔧 Cambios Realizados

### Archivos Removidos/No Usados:
- ❌ `tablero_nioval_adapter.py` - Ya NO se usa
- ❌ Excel "TABLERO DE NIOVAL Yahir .xlsx" - Solo referencia

### Sistema Actualizado:
- ✅ `nioval_sheets_adapter.py` - Lee SOLO del Google Spreadsheet
- ✅ Removida integración con Excel
- ✅ Sistema simplificado

---

## ❓ Información Pendiente

Para completar la integración de datos previos del cliente, necesito saber:

### 1. ¿Qué columnas tiene el Google Spreadsheet "LISTA DE CONTACTOS"?

**Columnas conocidas (A-F):**
- A: Nombre negocio
- B: Ciudad
- C: Estado
- D: Categoría
- E: Número
- F: Estado llamada

**¿Hay más columnas con información como:**
- Domicilio/Dirección completa?
- Horario de atención?
- Puntuación Google Maps?
- Número de reseñas?
- Link de Google Maps?
- Estatus/Respuesta previa?

### 2. Si sí tiene esas columnas, ¿en qué letras están?

Ejemplo:
```
G: ¿?
H: ¿?
I: ¿?
...
T: Email (ya sabemos que T es email)
```

---

## 🎯 Próximos Pasos

### Opción 1: Si el Spreadsheet tiene columnas adicionales con datos
1. Identific ar qué columnas tienen qué información
2. Modificar `nioval_sheets_adapter.py` para leer esas columnas
3. Actualizar `agente_ventas.py` para usar esos datos
4. Bruce NO preguntará lo que ya está en el Spreadsheet

### Opción 2: Si el Spreadsheet SOLO tiene columnas A-F
1. Bruce solo tendrá: Nombre, Ciudad, Estado, Categoría
2. NO preguntará eso
3. SÍ preguntará: WhatsApp, Email

---

## 🧪 Script para Ver Estructura

He creado un script para ver todas las columnas del Spreadsheet:

```bash
python ver_estructura_sheets.py
```

Este script mostrará:
- Todas las columnas y sus encabezados
- Ejemplo de datos de la primera fila
- Te ayudará a identificar qué información ya tenemos

---

## ✅ Estado Actual del Sistema

**Integración Excel:** ❌ Removida (era innecesaria)
**Integración Spreadsheet:** ✅ Funcional (columnas A-F)
**Datos previos del cliente:** ⏸️ Pendiente de confirmar qué columnas usar

**Próximo paso:** Ejecutar `ver_estructura_sheets.py` para ver todas las columnas disponibles en el Google Spreadsheet.
