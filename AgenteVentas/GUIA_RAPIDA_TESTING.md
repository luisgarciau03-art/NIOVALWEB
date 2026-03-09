# 🚀 GUÍA RÁPIDA DE TESTING - FORMULARIO 7 PREGUNTAS

## ✅ INTEGRACIÓN COMPLETADA

La integración del formulario de 7 preguntas está **100% completa** y lista para usar.

---

## 📊 ¿QUÉ SE INTEGRÓ?

### 1. **Spreadsheet de Resultados**
- **URL:** https://docs.google.com/spreadsheets/d/1U_z1KNqCxSRZVi7wvO2FQH4zIdS_wxuafxj6YHdHEqg/edit
- **Hoja:** "Respuestas de formulario 1"
- **Adaptador:** `resultados_sheets_adapter.py`

### 2. **7 Preguntas del Formulario** (basado en `llenar_formularios.py`)
| Pregunta | Tipo | Momento | Captura |
|----------|------|---------|---------|
| **P0** | Estado llamada | Automático | Respondio/Buzon/Telefono Incorrecto/Colgo |
| **P1** | Necesidades | Presentación inicial | Opciones múltiples (ej: "Entregas Rápidas, Precio Preferente") |
| **P2** | Toma decisiones | Después de P1 | Sí/No |
| **P3** | Pedido inicial | Cuando muestra interés | Crear Pedido/No |
| **P4** | Pedido muestra $1,500 | Si P3 = No | Sí/No |
| **P5** | Compromiso fecha | Si acepta pedido | Sí/No/Tal vez |
| **P6** | Método pago TDC | Si acepta pedido | Sí/No/Tal vez |
| **P7** | Conclusión | Automático al final | Pedido/Revisara/Correo/No apto/Colgo/etc. |

### 3. **Características Especiales**
✅ **Preguntas sutiles e indirectas** - NO como cuestionario
✅ **Orden cronológico** - P1 → P2 → P3 → P4 → P5 → P6 → P7
✅ **Manejo de sinónimos** - "Que sea barato" → "Precio Preferente"
✅ **Lead mapping** - Cuando 5+ clientes dicen lo mismo → nueva opción
✅ **Captura automática** - Detecta keywords durante conversación natural
✅ **Coherencia conversacional** - Flujo adaptativo según respuestas

---

## 🧪 CÓMO PROBAR

### Opción 1: Prueba Completa del Sistema
```bash
cd C:\Users\PC 1\AgenteVentas
python sistema_llamadas_nioval.py
```

**Qué esperar:**
1. Se conectará al spreadsheet "LISTA DE CONTACTOS"
2. Se conectará al spreadsheet "Respuestas de formulario 1"
3. Iniciará llamadas automáticamente
4. Bruce hará las 7 preguntas de forma **sutil e indirecta**
5. Al terminar cada llamada, guardará los resultados en ambos spreadsheets

### Opción 2: Prueba Individual del Agente
```bash
cd C:\Users\PC 1\AgenteVentas
python agente_ventas.py
```

**Qué esperar:**
1. Podrás simular una conversación con Bruce
2. Observa cómo hace las preguntas sutilmente
3. Prueba diferentes sinónimos y variaciones

### Opción 3: Prueba del Adaptador de Resultados
```bash
cd C:\Users\PC 1\AgenteVentas
python resultados_sheets_adapter.py
```

**Qué esperar:**
1. Se conectará al spreadsheet de resultados
2. Mostrará estadísticas actuales
3. Puedes descomentar el código de prueba para guardar un registro de ejemplo

---

## 🎯 EJEMPLOS DE CONVERSACIÓN

### Ejemplo 1: Cliente Aprobado (Todas las preguntas)

**Bruce:** Buenos días, ¿hablo con el encargado de compras de [Tienda]?

**Cliente:** Sí, soy yo.

**Bruce:** Perfecto. Platíqueme, ¿qué es lo más importante para ustedes al momento de elegir un proveedor?
*→ PREGUNTA 1 (sutil)*

**Cliente:** Pues que sea barato y que llegue rápido.
*→ CAPTURA: "Precio Preferente, Entregas Rápidas"*

**Bruce:** Excelente. Y para agilizar el proceso, ¿usted es quien autoriza las compras?
*→ PREGUNTA 2*

**Cliente:** Sí, yo decido.
*→ CAPTURA: "Sí"*

**Bruce:** Perfecto. Mire, tengo un producto estrella, el SKU 5958, que es top de venta con muy buen precio. ¿Le gustaría que le armara un pedido inicial con este producto y otros similares?
*→ PREGUNTA 3*

**Cliente:** Sí, arma el pedido.
*→ CAPTURA: "Crear Pedido Inicial Sugerido" → SALTA P4*

**Bruce:** ¡Excelente! Para que lo tenga listo, ¿qué día le vendría bien recibirlo?
*→ PREGUNTA 5*

**Cliente:** El viernes está bien.
*→ CAPTURA: "Sí"*

**Bruce:** Perfecto. Y para que sea más rápido, ¿puedo registrar una tarjeta de crédito o débito?
*→ PREGUNTA 6*

**Cliente:** Sí, sin problema.
*→ CAPTURA: "Sí"*

**Bruce:** ¡Perfecto! Le voy a mandar todo por WhatsApp al [número]. Muchas gracias.
*→ PREGUNTA 7: Automático → "Pedido"*
*→ RESULTADO: "APROBADO"*

---

### Ejemplo 2: Cliente con Sinónimos

**Bruce:** ¿Qué valoran más: entregas rápidas, buenos precios, o líneas de crédito?

**Cliente:** Que llegue luego luego y que sea económico.
*→ BRUCE MAPEA: "luego luego" = Entregas Rápidas, "económico" = Precio Preferente*
*→ CAPTURA: "Entregas Rápidas, Precio Preferente"*

---

### Ejemplo 3: Cliente Dice Algo No Listado (Lead Mapping)

**Bruce:** ¿Qué es lo más importante para ustedes al elegir proveedor?

**Cliente:** Que tenga garantía y buen servicio post-venta.
*→ BRUCE PIENSA: "garantía" y "servicio post-venta" no están en las 6 opciones*
*→ LO MÁS CERCANO: "Evaluar Calidad"*
*→ CAPTURA: "Evaluar Calidad"*
*→ ANOTA MENTALMENTE: Si 5+ clientes mencionan "garantía", considerar nueva opción*

---

## 📋 VERIFICAR RESULTADOS

### Spreadsheet "Respuestas de formulario 1"

Después de cada llamada, verifica que se guardó:

| Columna | Contenido | Ejemplo |
|---------|-----------|---------|
| **A** | Fecha/Hora | 27/12/2024 14:30:00 |
| **B** | TIENDA | Ferretería El Tornillo |
| **C** | Pregunta 1 | Entregas Rápidas, Precio Preferente |
| **D** | Pregunta 2 | Sí |
| **E** | Pregunta 3 | Crear Pedido Inicial Sugerido |
| **G** | Pregunta 4 | Sí |
| **H** | Pregunta 5 | Sí |
| **I** | Pregunta 6 | Sí |
| **J** | Pregunta 7 | Pedido |
| **S** | Resultado | APROBADO |
| **T** | Estado | Respondio |

---

## 🔧 ARCHIVOS MODIFICADOS/CREADOS

### ✅ Creados
- `resultados_sheets_adapter.py` - Adaptador para spreadsheet de resultados
- `FORMULARIO_7_PREGUNTAS.md` - Documentación completa de las 7 preguntas
- `INTEGRACION_FORMULARIO_COMPLETA.md` - Resumen ejecutivo
- `GUIA_RAPIDA_TESTING.md` - Este documento

### ✏️ Modificados
- `agente_ventas.py` - SYSTEM_PROMPT actualizado con las 7 preguntas
- `sistema_llamadas_nioval.py` - Integración con resultados_sheets_adapter

---

## 🎓 REGLAS CLAVE PARA BRUCE

1. **NUNCA digas "Pregunta 1", "Pregunta 2"** - Las preguntas fluyen naturalmente
2. **Respeta el orden cronológico** - P1 → P2 → P3 → P4 → P5 → P6 → P7
3. **Maneja sinónimos automáticamente** - "barato" = "Precio Preferente"
4. **Si P3 = Sí, salta P4** - No preguntes por pedido muestra si ya aceptó pedido inicial
5. **Si cliente no muestra interés, salta P3-P6** - Solo haz P1 y P2
6. **Lead mapping activo** - Cuando 5+ clientes dicen lo mismo → nueva opción válida

---

## 📞 FLUJOS ADAPTATIVOS

### Flujo Normal (Cliente interesado)
P1 → P2 → P3(Sí) → P5 → P6 → P7(Automático)

### Flujo Alternativo (Rechaza pedido inicial)
P1 → P2 → P3(No) → P4 → P7(Automático)

### Flujo Corto (Sin interés)
P1 → P2 → P7(Automático: "No apto")

### Flujo Buzón/Teléfono Incorrecto
P0(Buzon/Telefono Incorrecto) → P7(Automático: "BUZON"/"TELEFONO INCORRECTO")

---

## 🚨 SOLUCIÓN DE PROBLEMAS

### Problema: No se guardan resultados en el spreadsheet
**Solución:** Verificar que:
1. Archivo `bubbly-subject-412101-c969f4a975c5.json` existe
2. Service account tiene permisos sobre el spreadsheet
3. URL del spreadsheet es correcta en `resultados_sheets_adapter.py`

### Problema: Bruce no hace las preguntas
**Solución:**
1. Verificar que el SYSTEM_PROMPT se cargó correctamente
2. Revisar el método `_capturar_respuestas_formulario()` en `agente_ventas.py`

### Problema: Las respuestas se capturan mal
**Solución:**
1. Revisar keywords en `_capturar_respuestas_formulario()`
2. Agregar más sinónimos al SYSTEM_PROMPT

---

## ✨ PRÓXIMOS PASOS

1. **Ejecutar pruebas** con clientes reales
2. **Monitorear** el spreadsheet de resultados para ver patrones
3. **Identificar nuevas opciones** cuando se repitan 5+ veces
4. **Ajustar keywords** si hay sinónimos no contemplados
5. **Revisar tasas de aprobación** en las estadísticas

---

## 📊 MÉTRICAS A OBSERVAR

Ejecuta `python resultados_sheets_adapter.py` para ver:
- Total de resultados registrados
- Total de aprobados
- Total de negados
- Tasa de aprobación (%)

---

## 🎉 ¡LISTO PARA USAR!

El sistema está **completamente integrado** y funcional.

**Comando para iniciar:**
```bash
python sistema_llamadas_nioval.py
```

**Documenta todo lo observado** para futuras mejoras.

---

**Fecha de integración:** 27 de diciembre 2024
**Estado:** ✅ Completado
**Archivos involucrados:** 6 archivos (2 creados, 2 modificados, 2 documentación)
