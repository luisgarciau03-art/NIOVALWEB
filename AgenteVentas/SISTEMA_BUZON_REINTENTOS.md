# 📞 SISTEMA DE BUZÓN CON REINTENTOS (4 INTENTOS)

## 🎯 Objetivo

Cuando un cliente no contesta y entra el buzón de voz, el sistema debe:
1. **Intentos 1-3:** Mover el contacto al final de la lista para reintentar (2 veces mismo día, 2 veces día siguiente)
2. **Intento 4:** Si vuelve a entrar buzón después de 4 intentos, marcar como "TELEFONO INCORRECTO" definitivo

---

## 📋 Flujo de Operación

### Escenario 1: Primer Intento de Buzón

```
📞 Bruce llama a contacto (Fila 5)
   ↓
🔊 Entra buzón de voz
   ↓
👤 Usuario escribe: "buzon"
   ↓
🤖 Bruce detecta: estado_llamada = "Buzon"
   ↓
💾 Sistema guarda en "Respuestas de formulario 1":
   - Columna J: "BUZON"
   - Columna T: "Buzon"
   ↓
📊 Sistema verifica intentos en columna U (LISTA DE CONTACTOS):
   - Intentos actuales: 0
   - Nuevos intentos: 1
   ↓
↩️  Sistema mueve fila 5 al FINAL de LISTA DE CONTACTOS
   - Limpia columna F (estado) para que vuelva a aparecer como pendiente
   - Fila movida de posición 5 → última fila disponible
   ↓
✅ Contacto reagendado para segundo intento
```

### Escenario 2: Segundo Intento de Buzón (después del reintento)

```
📞 Bruce llama nuevamente al contacto (ahora en última fila - después de unos días)
   ↓
🔊 Entra buzón de voz OTRA VEZ
   ↓
👤 Usuario escribe: "buzon"
   ↓
🤖 Bruce detecta: estado_llamada = "Buzon"
   ↓
💾 Sistema guarda en "Respuestas de formulario 1":
   - Columna J: "BUZON"
   - Columna T: "Buzon"
   ↓
📊 Sistema verifica intentos en columna U (LISTA DE CONTACTOS):
   - Intentos actuales: 1 (del primer intento)
   - Nuevos intentos: 2
   ↓
❌ Sistema clasifica como TELEFONO INCORRECTO:
   - Razón: Después de 2 intentos, el número probablemente no es válido
   - Columna F: "TELEFONO INCORRECTO"
   ↓
📋 Sistema mueve fila al final de la lista
   ↓
🛑 Contacto archivado como número no válido
```

---

## 📊 Estructura de Datos

### Google Sheets: "LISTA DE CONTACTOS"

| Columna | Campo | Uso |
|---------|-------|-----|
| **E** | Número de teléfono | Contacto a llamar (formato: 662 108 5297) |
| **F** | Estado de llamada | "Respondio" / "BUZON" / "Telefono Incorrecto" / etc. |
| **T** | Email | Email capturado durante la llamada |
| **U** | Contador de intentos buzón | Contador: 0, 1, 2 (NEW) |

### Google Sheets: "Respuestas de formulario 1"

| Columna | Campo | Valor en caso de Buzón |
|---------|-------|------------------------|
| **J** | Prioridad / Pregunta 7 | "BUZON" |
| **T** | Estado de llamada | "Buzon" |

---

## 🔧 Métodos Implementados

### nioval_sheets_adapter.py

#### 1. `obtener_contador_intentos_buzon(fila: int) -> int`
```python
# Lee columna U para obtener número de intentos (0, 1, 2)
intentos = nioval_adapter.obtener_contador_intentos_buzon(fila=5)
# Retorna: 0 (sin intentos), 1 (primer intento), 2 (segundo intento)
```

#### 2. `marcar_intento_buzon(fila: int) -> int`
```python
# Incrementa contador de intentos en columna U
nuevos_intentos = nioval_adapter.marcar_intento_buzon(fila=5)
# Si tenía 0 → retorna 1
# Si tenía 1 → retorna 2
```

#### 3. `mover_fila_al_final(fila: int)`
```python
# Mueve toda la fila al final de la hoja
# Limpia columna F (estado) para que vuelva a aparecer como pendiente
nioval_adapter.mover_fila_al_final(fila=5)
# Fila 5 ahora está al final de la lista
```

#### 4. `marcar_estado_final(fila: int, estado: str)`
```python
# Marca el estado definitivo en columna F
nioval_adapter.marcar_estado_final(fila=5, estado="BUZON")
# Columna F = "BUZON" (no se volverá a llamar)
```

---

## 🎬 Ejemplo Completo

### Primer Intento

```bash
📞 CONTACTO 1/100
   Negocio: Ferretería El Martillo
   Teléfono: +526621085297
   Ciudad: Hermosillo
==============================================

🎙️ Bruce W: Muy buenas tardes, mi nombre es Bruce W. ¿Me comunica con el encargado de compras del negocio por favor?

👤 Cliente: buzon

[SISTEMA DETECTA BUZÓN]
📝 Estado detectado: Buzón de voz

📊 Analizando llamada...
📝 Guardando resultados en Google Sheets...

   ✅ Formulario guardado correctamente
   📞 Primer intento de buzón detectado
   ↩️  Moviendo contacto al final de la lista para reintentar...
   ✅ Fila movida de 5 → 120 (al final)
   ✅ Contacto reagendado para segundo intento

📊 RESUMEN DE LA CONVERSACIÓN:
📝 Conclusión: BUZON (NEGADO)
```

### Segundo Intento (después de procesar otros contactos)

```bash
📞 CONTACTO 120/120
   Negocio: Ferretería El Martillo  ← MISMO CONTACTO
   Teléfono: +526621085297
   Ciudad: Hermosillo
==============================================

🎙️ Bruce W: Muy buenas tardes, mi nombre es Bruce W. ¿Me comunica con el encargado de compras del negocio por favor?

👤 Cliente: buzon

[SISTEMA DETECTA BUZÓN OTRA VEZ]
📝 Estado detectado: Buzón de voz

📊 Analizando llamada...
📝 Guardando resultados en Google Sheets...

   ✅ Formulario guardado correctamente
   📞 Segundo intento de buzón detectado
   ❌ Número no válido después de 2 intentos
   📋 Clasificando como TELEFONO INCORRECTO
   📋 Moviendo contacto al final de la lista (números no válidos)
   ✅ Contacto archivado al final con estado: TELEFONO INCORRECTO

📊 RESUMEN DE LA CONVERSACIÓN:
📝 Conclusión: BUZON (NEGADO)
```

---

## 🚦 Estados Posibles

| Estado | Descripción | Columna F | ¿Se reintenta? |
|--------|-------------|-----------|----------------|
| **Respondio** | Cliente contestó y conversó | "Respondio" | ❌ No (ya se contactó) |
| **Buzon (intento 1)** | Entró buzón primera vez | "" (vacío) | ✅ Sí → Intento #2 (mismo día) |
| **Buzon (intento 2)** | Entró buzón segunda vez | "" (vacío) | ✅ Sí → Intento #3 (siguiente ronda) |
| **Buzon (intento 3)** | Entró buzón tercera vez | "" (vacío) | ✅ Sí → Intento #4 (último) |
| **Buzon (intento 4)** | Entró buzón cuarta vez | "TELEFONO INCORRECTO" | ❌ No (número no válido) |
| **Telefono Incorrecto** | Número no existe / 4 buzones / equivocado | "TELEFONO INCORRECTO" | ❌ No (número inválido) |
| **Colgo** | Cliente colgó | "Colgo" | ❌ No (no interesado) |
| **No Contesta** | Nadie contestó | "No Contesta" | ❌ No (sin respuesta) |

---

## ✅ Ventajas del Sistema

1. **Optimiza contactos:** No descarta contactos al primer intento de buzón
2. **Persistente:** 4 intentos en 2 días diferentes maximiza probabilidad de contacto
3. **Eficiente:** Mueve al final automáticamente para procesar primero contactos frescos
4. **Evita spam:** Solo reintenta 3 veces, luego clasifica como no válido
5. **Tracking completo:** Guarda cada intento en "Respuestas de formulario 1"
6. **Transparente:** Usuario ve claramente cuántos intentos se hicieron (columna U)
7. **Clasifica inteligentemente:** Después de 4 buzones (2 días), asume número no válido

---

## 📝 Notas Técnicas

### Columna U - Contador de Intentos

- **Valor 0:** Sin intentos de buzón (o vacío)
- **Valor 1:** Primer intento de buzón (se reintentará #2 mismo día)
- **Valor 2:** Segundo intento de buzón (se reintentará #3 siguiente ronda)
- **Valor 3:** Tercer intento de buzón (se reintentará #4 último intento)
- **Valor 4:** Cuarto intento de buzón (clasificado como TELEFONO INCORRECTO definitivo)

### ⚠️ Lógica de Clasificación después de 4 Intentos

**¿Por qué se clasifica como "TELEFONO INCORRECTO" después del cuarto intento?**

**Estrategia de Reintentos:**
1. **Día 1 - Intento 1:** Puede estar ocupado, en reunión
2. **Día 1 - Intento 2:** Segunda oportunidad mismo día (procesar otros contactos primero)
3. **Día 2 - Intento 3:** Reintentar en horario diferente (al día siguiente)
4. **Día 2 - Intento 4:** Último intento. Si OTRA VEZ cae en buzón, el número probablemente:
   - No pertenece a un negocio activo
   - Es un número personal que nunca contesta
   - Está fuera de servicio
   - Es incorrecto desde el inicio

**Resultado:** Después de 4 intentos (2 por día x 2 días), el sistema lo marca como "TELEFONO INCORRECTO" para no seguir desperdiciando tiempo con números que no son válidos para contacto comercial.

### Comportamiento de `mover_fila_al_final()`

1. Lee toda la fila actual
2. Limpia columna F (estado) para que vuelva a estar "pendiente"
3. Agrega la fila al final con `append_row()`
4. Elimina la fila original con `delete_rows()`
5. El contacto aparecerá al final de la lista de contactos pendientes

### Preservación de Datos

Al mover la fila, se preservan TODOS los datos:
- Nombre del negocio
- Ciudad
- Categoría
- Número de teléfono
- Domicilio, puntuación, reseñas, etc.
- **Contador de intentos en columna U** (mantiene el historial)

---

## 🔍 Verificación Manual

Para verificar el sistema funciona correctamente:

1. **Revisar "LISTA DE CONTACTOS":**
   - Después del primer intento: Fila debe estar al FINAL, columna F vacía, columna U = 1
   - Después del segundo intento: Fila permanece donde está, columna F = "BUZON", columna U = 2

2. **Revisar "Respuestas de formulario 1":**
   - Debe haber DOS registros para el mismo contacto
   - Ambos con columna J = "BUZON" y columna T = "Buzon"

---

**Fecha de implementación:** 27/12/2024
**Archivos modificados:**
- `nioval_sheets_adapter.py` (métodos nuevos)
- `agente_ventas.py` (lógica de reintentos)
- `resultados_sheets_adapter.py` (guardado de estado)
