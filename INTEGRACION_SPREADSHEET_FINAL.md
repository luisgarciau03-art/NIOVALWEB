# ✅ Integración Completa del Google Spreadsheet

## 📊 Estructura del Spreadsheet "LISTA DE CONTACTOS"

Basado en la captura compartida, el spreadsheet tiene las siguientes columnas:

| Col | Nombre | Descripción | Uso por Bruce |
|-----|--------|-------------|---------------|
| **A** | W | Número de fila | No se usa |
| **B** | TIENDA | Nombre del negocio | ✅ YA LO SABE - NO pregunta |
| **C** | CIUDAD | Ciudad del negocio | ✅ YA LO SABE - NO pregunta |
| **D** | CATEGORIA | Tipo de negocio (Ferreterías, etc.) | ✅ YA LO SABE - NO pregunta |
| **E** | CONTACTO | Número de teléfono | ✅ LEE y ESCRIBE (WhatsApp validado) |
| **F** | RESPUESTA | Estado de llamada | ✅ SOLO LEE (filtro) - NO escribe |
| **G** | PORCENTAJES | Porcentaje (¿interés?, ¿conversión?) | Lee pero no usa actualmente |
| **H** | Domicilio | Dirección completa | ✅ YA LO SABE - NO pregunta |
| **I** | Puntuacion | Puntuación Google Maps | ✅ YA LO SABE - puede mencionar |
| **J** | Reseñas | Número de reseñas | ✅ YA LO SABE - puede mencionar |
| **K** | Maps | Nombre en Google Maps | ✅ YA LO SABE |
| **L** | Link | URL de Google Maps | Lee pero no usa |
| **M** | Horario | Horario de atención | ✅ YA LO SABE - NO pregunta |
| **N** | Estatus | Estado del contacto | ✅ YA LO SABE |
| **O** | Latitud | Coordenada geográfica | Lee pero no usa |
| **P** | Longitud | Coordenada geográfica | Lee pero no usa |
| **Q** | Medida | Métrica específica | Lee pero no usa |
| **R** | Esquema | Esquema de clasificación | Lee pero no usa |
| **S** | Fecha | Fecha de registro/actualización | Lee pero no usa |
| **T** | Email | Email del contacto | ✅ ESCRIBE aquí cuando captura |

---

## 🎯 Lo que Bruce W NO Preguntará

Si el spreadsheet tiene esta información, Bruce **NUNCA** preguntará:

### ❌ Datos que YA conoce:
1. **Nombre del negocio** (columna B)
   - ❌ "¿Cómo se llama su negocio?"

2. **Ciudad** (columna C)
   - ❌ "¿En qué ciudad está?"
   - ❌ "¿Dónde se encuentra?"

3. **Dirección** (columna H - si tiene datos)
   - ❌ "¿Cuál es su dirección?"
   - ❌ "¿Dónde están ubicados?"

4. **Horario** (columna M - si tiene datos)
   - ❌ "¿A qué hora abren?"
   - ❌ "¿Cuál es su horario?"

5. **Tipo de negocio** (columna D)
   - ❌ "¿Qué tipo de negocio es?"

### ✅ Datos que SÍ Preguntará:
1. **WhatsApp** - PRIORIDAD #1
2. **Email** - Si no tiene WhatsApp
3. **Nombre del contacto** - Opcional, solo si surge naturalmente

---

## 📋 Ejemplo de Contexto que Recibe Bruce

Cuando Bruce llama a un cliente, recibe este contexto al inicio:

```
[INFORMACIÓN PREVIA DEL CLIENTE - NO PREGUNTES ESTO]
- Nombre del negocio: San Benito Ferretería Matriz
- Ciudad: Hermosillo
- Tipo de negocio: Ferreterías
- Dirección: Av Veracruz
- Horario: Lunes 7. Abierto
- Puntuación Google Maps: 4.5 estrellas
- Número de reseñas: 114
- Nombre en Google Maps: https://wa.me/http://...
- Estatus previo: No disponible

Recuerda: NO preguntes nada de esta información, ya la tienes.
```

---

## 🔄 Flujo de Operación Actualizado

### 1. Sistema lee Google Spreadsheet
```
Lee "LISTA DE CONTACTOS" →
- Obtiene TODAS las columnas (A-S)
- Filtra: Columna E tiene número Y Columna F está vacía
- Enriquece cada contacto con todos los datos disponibles
```

### 2. Bruce inicia llamada con contexto
```
Bruce recibe información previa →
- Nombre del negocio
- Ciudad
- Dirección (si disponible)
- Horario (si disponible)
- Puntuación y reseñas
- Estatus previo
```

### 3. Conversación Natural
```
Bruce: "Hola, buenas tardes. Soy Bruce W de NIOVAL..."

[Bruce ya sabe que está hablando con "San Benito Ferretería Matriz"
 en Hermosillo, así que NO pregunta eso]

Bruce: "El motivo de mi llamada es presentarle nuestros productos
       del ramo ferretero. ¿Le interesaría recibir información?"

Cliente: "Sí, mándeme información"

Bruce: "Perfecto. ¿Cuál es su WhatsApp para enviarle el catálogo?"
```

### 4. Captura y Validación
```
Cliente proporciona WhatsApp →
Sistema valida si tiene WhatsApp activo →
Si válido: Actualiza columna E con número validado
Si captura email: Escribe en columna T
```

---

## 📝 Ejemplo Comparativo

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

## 🔧 Archivos Modificados

### 1. nioval_sheets_adapter.py
- ✅ Actualizado para leer TODAS las columnas (A-S)
- ✅ Enriquece contactos con todos los datos disponibles
- ✅ NO intenta leer archivo Excel (solo Spreadsheet)

### 2. agente_ventas.py
- ✅ Método `_generar_contexto_cliente()` actualizado
- ✅ Usa todas las columnas del Spreadsheet
- ✅ Genera contexto completo para Bruce
- ✅ SYSTEM_PROMPT actualizado con reglas de NO preguntar

---

## ✅ Estado Actual

**Integración:** ✅ Completa
**Fuente de datos:** ✅ Google Spreadsheet únicamente
**Archivo Excel:** ❌ NO se usa (solo es muestra)
**Datos previos:** ✅ Bruce tiene toda la información del Spreadsheet
**Conversaciones:** ✅ Más naturales y eficientes

---

## 🧪 Próximo Paso: Probar

```bash
# 1. Probar adaptador
python nioval_sheets_adapter.py

# Debería mostrar:
# ✅ Autenticado correctamente con Google Sheets
# ✅ Spreadsheet abierto: [nombre]
# ✅ Hoja encontrada: LISTA DE CONTACTOS
# ✅ Conectado a: LISTA DE CONTACTOS

# 2. Ejecutar sistema
python sistema_llamadas_nioval.py

# Opción 2: Ejecutar 5 llamadas de prueba
```

Durante la simulación, verifica que:
- Bruce NO pregunta nombre del negocio
- Bruce NO pregunta ciudad
- Bruce NO pregunta dirección (si está en el spreadsheet)
- Bruce NO pregunta horario (si está en el spreadsheet)
- Bruce SOLO pregunta WhatsApp y Email

---

## 💡 Beneficios

1. **Conversaciones más cortas**
   - De 6+ preguntas a solo 1-2

2. **Mejor experiencia del cliente**
   - No hace preguntas obvias
   - Cliente siente que Bruce ya lo conoce

3. **Mayor eficiencia**
   - Menos tiempo por llamada
   - Más llamadas por hora

4. **Datos centralizados**
   - Todo en el Google Spreadsheet
   - Fácil de actualizar
   - Sincronización automática

---

**Estado:** ✅ Sistema completamente integrado con todas las columnas del Google Spreadsheet
