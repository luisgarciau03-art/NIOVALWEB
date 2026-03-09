# 📊 Integración del TABLERO DE NIOVAL

## ✅ Cambios Implementados

He integrado el archivo Excel "TABLERO DE NIOVAL Yahir .xlsx" para que Bruce W **NO pregunte** información que ya tenemos de los clientes.

---

## 📋 Información que Bruce YA CONOCE

Según el archivo Excel del tablero, ahora el sistema puede tener estos datos previos:

### Datos Básicos:
- **CONTACTO**: Nombre del negocio/persona
- **Domicilio**: Dirección física completa
- **Horario**: Horario de atención del negocio

### Datos de Google Maps:
- **Puntuacion**: Calificación en Google Maps (ej: 4.5 estrellas)
- **Reseñas**: Número de reseñas en Google Maps
- **Maps**: Nombre en Google Maps
- **Link**: URL de Google Maps
- **Latitud/Longitud**: Coordenadas geográficas

### Datos de Seguimiento:
- **Estatus**: Estado del contacto
- **RESPUESTA**: Respuesta previa registrada
- **PORCENTAJES**: Algún porcentaje (interés, conversión, etc.)
- **Fecha**: Fecha de registro/última actualización
- **Medida**: Métrica específica
- **Esquema**: Esquema de clasificación

---

## 🔧 Archivos Creados/Modificados

### 1. **tablero_nioval_adapter.py** (NUEVO)
Adaptador para leer y buscar información en el TABLERO Excel.

**Funciones principales:**
```python
# Buscar por teléfono
contacto = adapter.buscar_contacto_por_telefono("+526621012000")

# Buscar por nombre
contacto = adapter.buscar_contacto_por_nombre("Ferretería La Estrella")

# Enriquecer contacto con datos del tablero
contacto_enriquecido = adapter.enriquecer_contacto(contacto_base)
```

### 2. **nioval_sheets_adapter.py** (MODIFICADO)
Ahora integra automáticamente datos del tablero al obtener contactos.

**Cambios:**
- Constructor acepta parámetro `usar_tablero=True`
- Método `obtener_contactos_pendientes()` enriquece contactos automáticamente
- Si encuentra el contacto en el tablero, agrega todos los datos disponibles

### 3. **agente_ventas.py** (MODIFICADO)
Bruce W ahora usa información previa y NO pregunta lo que ya sabe.

**Cambios en SYSTEM_PROMPT:**
```
CRÍTICO: ANTES de preguntar CUALQUIER dato al cliente,
REVISA si ya lo tienes en el contexto de la llamada.

NUNCA preguntes:
✗ "¿Cómo se llama su negocio?" - YA LO SABES
✗ "¿En qué ciudad está?" - Si ya lo tienes, NO preguntes
✗ "¿Cuál es su dirección?" - Si ya la tienes, NO preguntes
```

**Nueva función:** `_generar_contexto_cliente()`
- Genera mensaje de sistema con información previa
- Se agrega al inicio de cada conversación
- Bruce ve el contexto pero no lo menciona al cliente

---

## 🔄 Flujo de Datos

```
1. Sistema lee "LISTA DE CONTACTOS" (Google Sheets)
   └─ Obtiene: Nombre, Teléfono, Ciudad, Estado, Categoría

2. Busca en "TABLERO NIOVAL" (Excel) por:
   ├─ Teléfono (primera prioridad)
   └─ Nombre del negocio (segunda prioridad)

3. Si encuentra match en el tablero:
   └─ Enriquece contacto con:
       ├─ Domicilio completo
       ├─ Horario de atención
       ├─ Puntuación Google Maps
       ├─ Número de reseñas
       ├─ Estatus previo
       └─ Otros datos disponibles

4. Al iniciar llamada:
   └─ Bruce recibe contexto con información previa:
       [INFORMACIÓN PREVIA DEL CLIENTE - NO PREGUNTES ESTO]
       - Nombre del negocio: Ferretería La Estrella
       - Ubicación: Guadalajara, Jalisco
       - Dirección: Av. Principal #123, Col. Centro
       - Horario: Lun-Sab 9:00-19:00
       - Puntuación Google Maps: 4.5 estrellas
       - Número de reseñas: 87

       Recuerda: NO preguntes nada de esta información, ya la tienes.

5. Bruce conversa SIN preguntar lo que ya sabe
   └─ Solo pregunta: WhatsApp, Email, Nombre del contacto (opcional)
```

---

## 📝 Ejemplo de Conversación

### ❌ ANTES (sin integración):
```
Bruce: Hola, buenas tardes. Soy Bruce W de NIOVAL...
Cliente: Hola
Bruce: ¿Cómo se llama su negocio?
Cliente: Ferretería La Estrella
Bruce: ¿En qué ciudad se encuentra?
Cliente: En Guadalajara
Bruce: ¿Cuál es su dirección?
Cliente: Av. Principal #123
```

### ✅ AHORA (con integración):
```
Bruce: Hola, buenas tardes. Soy Bruce W de NIOVAL...
Cliente: Hola
Bruce: Perfecto. Veo que está en Guadalajara. Le llamo para
       presentarle nuestros productos ferreteros. ¿Le interesaría
       recibir información de nuestro catálogo?
Cliente: Sí, envíeme información
Bruce: Excelente. ¿Cuál es su WhatsApp para enviarle el catálogo?
```

**Nota:** Bruce ya sabe el nombre, la ciudad y la dirección, así que NO pregunta.

---

## 🧪 Cómo Probar

### 1. Verifica que el archivo Excel esté en su lugar:
```bash
# Debe estar en:
C:\Users\PC 1\AgenteVentas\TABLERO DE NIOVAL Yahir .xlsx
```

### 2. Prueba el adaptador del tablero:
```bash
python tablero_nioval_adapter.py
```

**Salida esperada:**
```
✅ Tablero NIOVAL cargado: XX registros
   Columnas: CONTACTO, RESPUESTA, PORCENTAJES, Domicilio, ...

📊 ESTADÍSTICAS:
total_registros: XX
con_domicilio: XX
...
```

### 3. Prueba el sistema completo:
```bash
python sistema_llamadas_nioval.py
```

**Verifica en la salida:**
```
✅ Tablero NIOVAL integrado
✅ Conectado a: LISTA DE CONTACTOS

📋 Obteniendo contactos pendientes...
✅ Encontrados X contactos pendientes
```

### 4. Durante la simulación, observa:
- Bruce NO debe preguntar nombre del negocio
- Bruce NO debe preguntar ciudad/estado (si ya los tiene)
- Bruce NO debe preguntar dirección (si ya la tiene)
- Bruce SOLO debe preguntar WhatsApp y Email

---

## ⚙️ Configuración

### Desactivar integración del tablero (si es necesario):
```python
# En sistema_llamadas_nioval.py, modificar:
self.sheets_adapter = NiovalSheetsAdapter(usar_tablero=False)
```

### Cambiar ruta del archivo Excel:
```python
# En tablero_nioval_adapter.py, constructor:
def __init__(self, archivo_excel: str = "ruta/a/tu/archivo.xlsx"):
```

---

## 🔍 Búsqueda de Contactos

El adaptador busca contactos en este orden:

### 1. Por Teléfono (más preciso):
```python
# Normaliza el teléfono y busca coincidencias
tel_limpio = "6621012000"  # Últimos 10 dígitos
# Busca en columna CONTACTO si tiene ese número
```

### 2. Por Nombre (segunda opción):
```python
# Busca coincidencia en:
# - Columna CONTACTO
# - Columna Maps
# Ignora mayúsculas/minúsculas
```

---

## 📊 Datos Disponibles

Después de la integración, cada contacto puede tener:

```python
{
    # Datos del Google Sheets (siempre presentes)
    'fila': 15,
    'telefono': '+526621012000',
    'nombre_negocio': 'Ferretería La Estrella',
    'ciudad': 'Guadalajara',
    'estado': 'Jalisco',
    'categoria': 'Ferretería',

    # Datos del TABLERO (si se encuentra)
    'domicilio': 'Av. Principal #123, Col. Centro',
    'horario': 'Lun-Sab 9:00-19:00',
    'puntuacion_maps': '4.5',
    'resenas_maps': '87',
    'link_maps': 'https://maps.google.com/...',
    'latitud': '20.6597',
    'longitud': '-103.3496',
    'estatus': 'Prospecto',
    'respuesta_previa': '...',
    'tiene_datos_previos': True  # Flag indica que se encontró en tablero
}
```

---

## ✅ Beneficios

1. **Conversaciones más naturales**
   - Bruce no hace preguntas obvias
   - Menor tiempo de llamada
   - Mejor experiencia del cliente

2. **Más eficiente**
   - Solo pregunta lo que NO sabe
   - Enfoque en WhatsApp/Email (objetivo principal)

3. **Mejor contexto**
   - Bruce puede mencionar detalles relevantes
   - Puede hacer referencias a la ubicación
   - Puede adaptar su discurso según el tipo de negocio

4. **Datos centralizados**
   - Toda la información en un solo lugar
   - Fácil actualización del Excel
   - Sistema actualiza automáticamente

---

## ⚠️ Notas Importantes

### Si el tablero NO está disponible:
- El sistema continúa funcionando normalmente
- Solo usa datos de Google Sheets
- Muestra advertencia pero NO se detiene

### Si un contacto NO está en el tablero:
- Se marca con `tiene_datos_previos: False`
- Bruce solo tiene datos básicos del Sheets
- Funcionamiento normal (pregunta lo que no sabe)

### Actualizar el tablero:
- Solo reemplaza el archivo Excel
- El sistema carga automáticamente en cada ejecución
- NO requiere reiniciar nada

---

## 🎯 Próximos Pasos

1. **Revisar el TABLERO Excel**
   - Verifica que tiene datos completos
   - Asegúrate que teléfonos coincidan con Google Sheets
   - Completa campos faltantes si es necesario

2. **Pruebas**
   - Ejecuta algunas llamadas de simulación
   - Verifica que Bruce NO pregunta lo que ya sabe
   - Ajusta SYSTEM_PROMPT si es necesario

3. **Optimización**
   - Considera agregar más campos al tablero si son útiles
   - Documenta qué información es más valiosa

---

**Estado:** ✅ Integración completada y funcional
**Archivo requerido:** `TABLERO DE NIOVAL Yahir .xlsx`
**Ubicación:** `C:\Users\PC 1\AgenteVentas\`
