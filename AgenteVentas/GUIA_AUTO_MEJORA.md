# 🤖 GUÍA COMPLETA - SISTEMA DE AUTO-MEJORA BRUCE W

## 📋 DESCRIPCIÓN

Sistema automático que analiza todas las llamadas de la semana y genera recomendaciones de mejora para el SYSTEM_PROMPT de Bruce W.

**Características principales:**
- ✅ **Análisis automático** cada viernes a las 9:00 AM
- ✅ **KPIs detallados** mostrados en terminal
- ✅ **Requiere autorización manual** antes de aplicar cambios
- ✅ **Genera Excel completo** con desglose de cambios, motivos y KPIs
- ✅ **Selección granular** de qué mejoras aplicar

---

## 🎯 FUNCIONALIDADES

### 1. Análisis Semanal Completo

Cada viernes a las 9:00 AM, el sistema:

1. **Extrae datos de Google Sheets** ("Respuestas de formulario 1")
   - Últimos 7 días de llamadas
   - Todas las columnas (A-X)

2. **Calcula KPIs automáticamente:**
   - Total de llamadas
   - Tasa de conversión (%)
   - WhatsApps capturados
   - Nivel de interés promedio (Alto/Medio/Bajo)
   - Estado de ánimo predominante (Positivo/Neutral/Negativo)
   - Distribución de interés (cuántos Alto, Medio, Bajo)
   - Distribución de estado de ánimo

3. **Analiza con GPT-4o-mini:**
   - Identifica patrones de éxito
   - Detecta áreas de mejora
   - Genera recomendaciones específicas
   - Propone modificaciones al SYSTEM_PROMPT

---

### 2. Presentación en Terminal

El sistema muestra en la terminal:

```
================================================================================
                    📊 ANÁLISIS SEMANAL - BRUCE W
================================================================================

🔢 MÉTRICAS PRINCIPALES:
--------------------------------------------------------------------------------
  📞 Total de llamadas:          45
  ✅ Aprobadas:                  32
  ❌ Negadas:                    13
  📈 Tasa de conversión:         71.11%
  💬 WhatsApps capturados:       32
  ⭐ Nivel de interés promedio:  Alto
  😊 Estado de ánimo predominante: Positivo

📊 DISTRIBUCIÓN DE INTERÉS:
--------------------------------------------------------------------------------
  Alto         28 llamadas ( 62.2%) ██████████████████████████████
  Medio        12 llamadas ( 26.7%) █████████████
  Bajo          5 llamadas ( 11.1%) █████

😊 DISTRIBUCIÓN DE ESTADO DE ÁNIMO:
--------------------------------------------------------------------------------
  Positivo     30 llamadas ( 66.7%) █████████████████████████████████
  Neutral      10 llamadas ( 22.2%) ███████████
  Negativo      5 llamadas ( 11.1%) █████

================================================================================
📋 RESUMEN DEL ANÁLISIS GPT:
================================================================================

La tasa de conversión es buena (71%), pero se identifican oportunidades para
mejorar el manejo de objeciones y aumentar la captura de emails.

================================================================================
🔴 MEJORAS CRÍTICAS (Alta Prioridad):
================================================================================

  [1] Mejorar respuesta a "Ya tengo proveedores" - incrementar énfasis en
      beneficios diferenciadores de NIOVAL

  [2] Fortalecer cierre cuando el cliente dice "Lo voy a pensar" - agregar
      urgencia sutil sobre disponibilidad de stock

================================================================================
🟡 MEJORAS SUGERIDAS (Prioridad Media):
================================================================================

  [3] Agregar confirmación de comprensión después de explicar crédito

  [4] Incluir mención de garantía de calidad antes de preguntar sobre
      pedido muestra

================================================================================
🔧 MODIFICACIONES PROPUESTAS AL SYSTEM_PROMPT:
================================================================================

  [1] Sección: MANEJO DE OBJECIONES - "Ya tengo proveedores"
      Cambio: Agregar "Muchos de nuestros mejores clientes también trabajan
              con otros proveedores. La ventaja es que NIOVAL ofrece..."
      Motivo: Solo 45% de clientes con esta objeción avanzaron

  [2] Sección: FASE 5: CIERRE
      Cambio: Cuando diga "Lo voy a pensar", agregar: "Perfecto, ¿hay algo
              específico que le gustaría evaluar? Le puedo enviar..."
      Motivo: 60% de "lo voy a pensar" no dieron WhatsApp

================================================================================
```

---

### 3. Sistema de Autorización

Después de mostrar el análisis, el sistema solicita autorización:

```
================================================================================
                       ⚠️ SOLICITUD DE AUTORIZACIÓN
================================================================================

Para autorizar la aplicación de mejoras:
  1. Revisa el análisis anterior
  2. Ingresa los números de las mejoras que deseas aplicar (separados por coma)
     Ejemplo: 1,3,5
  3. Para aplicar TODAS las mejoras, escribe: TODAS
  4. Para CANCELAR, escribe: CANCELAR

  Escribe 'AUTORIZACION' seguido de los números para confirmar
  Formato: AUTORIZACION 1,3,5
================================================================================

👤 Tu respuesta: _
```

**Opciones de respuesta:**

| Entrada | Acción |
|---------|--------|
| `AUTORIZACION TODAS` | Aplica todas las mejoras propuestas |
| `AUTORIZACION 1,3,5` | Aplica solo las mejoras 1, 3 y 5 |
| `CANCELAR` | Cancela el proceso sin aplicar nada |
| Cualquier otra cosa | Cancela automáticamente |

---

### 4. Generación de Excel

El sistema genera un archivo Excel completo con **5 hojas**:

#### 📄 Hoja 1: Resumen Ejecutivo

| MÉTRICA | VALOR |
|---------|-------|
| Período Analizado | Últimos 7 días |
| Fecha de Análisis | 27/12/2024 |
| Total de Llamadas | 45 |
| Llamadas Aprobadas | 32 |
| Llamadas Negadas | 13 |
| Tasa de Conversión (%) | 71.11% |
| WhatsApps Capturados | 32 |
| Nivel de Interés Promedio | Alto |
| Estado de Ánimo Predominante | Positivo |

#### 📄 Hoja 2: Distribución

| CATEGORÍA | CANTIDAD | PORCENTAJE |
|-----------|----------|------------|
| **NIVEL DE INTERÉS** | | |
| Alto | 28 | 62.2% |
| Medio | 12 | 26.7% |
| Bajo | 5 | 11.1% |
| | | |
| **ESTADO DE ÁNIMO** | | |
| Positivo | 30 | 66.7% |
| Neutral | 10 | 22.2% |
| Negativo | 5 | 11.1% |

#### 📄 Hoja 3: Recomendaciones

| TIPO | NÚMERO | RECOMENDACIÓN | ESTADO |
|------|--------|---------------|--------|
| 🔴 CRÍTICA | 1 | Mejorar respuesta a "Ya tengo proveedores"... | ✅ APROBADA |
| 🔴 CRÍTICA | 2 | Fortalecer cierre cuando dice "Lo voy a pensar"... | ✅ APROBADA |
| 🟡 SUGERIDA | 3 | Agregar confirmación de comprensión... | ⏸️ PENDIENTE |
| 🟡 SUGERIDA | 4 | Incluir mención de garantía... | ✅ APROBADA |

#### 📄 Hoja 4: Modificaciones Prompt

| NÚMERO | SECCIÓN | CAMBIO PROPUESTO | MOTIVO | IMPACTO ESPERADO | ESTADO |
|--------|---------|------------------|---------|------------------|--------|
| 1 | MANEJO DE OBJECIONES | Agregar "Muchos de nuestros mejores clientes..." | Solo 45% de clientes con esta objeción avanzaron | Medio | ✅ APROBADA |
| 2 | FASE 5: CIERRE | Cuando diga "Lo voy a pensar", agregar... | 60% de "lo voy a pensar" no dieron WhatsApp | Alto | ✅ APROBADA |

**Colores:**
- 🟢 Verde: Mejoras aprobadas
- ⚪ Blanco: Mejoras pendientes/no autorizadas

#### 📄 Hoja 5: Análisis GPT

Contiene el resumen completo generado por GPT-4o-mini.

---

## 🚀 CÓMO USAR

### Opción 1: Ejecución Programada (Automática)

1. **Iniciar el sistema:**
   ```bash
   # Hacer doble clic en:
   iniciar_auto_mejora.bat

   # O ejecutar en terminal:
   python auto_mejora_scheduler.py
   ```

2. **El sistema esperará** hasta el próximo viernes a las 9:00 AM

3. **Cuando llegue el viernes a las 9:00 AM:**
   - El sistema se ejecutará automáticamente
   - Mostrará el análisis en terminal
   - Solicitará autorización

4. **Responder con:**
   ```
   AUTORIZACION 1,2,4
   ```
   O:
   ```
   AUTORIZACION TODAS
   ```

5. **El sistema generará el Excel y guardará todo en el historial**

---

### Opción 2: Ejecución Inmediata (Testing)

Para probar sin esperar al viernes:

```bash
# Hacer doble clic en:
test_auto_mejora.bat

# O ejecutar en terminal:
python auto_mejora_scheduler.py --test
```

Esto ejecutará el análisis **inmediatamente** con los datos actuales.

---

## 📊 INTERPRETACIÓN DE RESULTADOS

### KPIs Críticos

| KPI | Bueno | Regular | Malo |
|-----|-------|---------|------|
| **Tasa de Conversión** | >70% | 50-70% | <50% |
| **Nivel de Interés** | Alto | Medio | Bajo |
| **Estado de Ánimo** | Positivo >60% | Neutral >50% | Negativo >30% |
| **WhatsApps Capturados** | >80% de aprobados | 60-80% | <60% |

### Tipos de Mejoras

**🔴 CRÍTICAS** (Alta Prioridad):
- Problemas que afectan >30% de llamadas
- Patrones de rechazo repetitivos
- Objeciones mal manejadas
- **Recomendación:** Aplicar siempre

**🟡 SUGERIDAS** (Prioridad Media):
- Optimizaciones incrementales
- Mejoras de flujo conversacional
- Ajustes de tono/estilo
- **Recomendación:** Evaluar caso por caso

---

## 🔧 APLICAR CAMBIOS AL CÓDIGO

**IMPORTANTE:** El sistema **NO modifica automáticamente** el archivo `agente_ventas.py`.

Los cambios aprobados se documentan en:
1. ✅ `historial_mejoras_bruce.json` - Registro completo
2. ✅ Excel generado - Desglose visual

**Para aplicar manualmente:**

1. **Abrir el Excel generado**
2. **Ir a la hoja "4. Modificaciones Prompt"**
3. **Ver las filas marcadas como "✅ APROBADA"**
4. **Editar `agente_ventas.py`:**
   - Buscar la sección indicada en columna "SECCIÓN"
   - Aplicar el cambio descrito en "CAMBIO PROPUESTO"
   - Guardar archivo

5. **Probar las llamadas**
6. **Si funcionan bien, hacer commit:**
   ```bash
   git add agente_ventas.py
   git commit -m "✨ Mejoras semana del DD/MM/YYYY - Tasa conversión: XX%"
   git push
   ```

---

## 📁 ARCHIVOS GENERADOS

### Durante la ejecución:

1. **`analisis_bruce_YYYYMMDD_HHMMSS.xlsx`**
   - Excel con análisis completo
   - 5 hojas con todos los KPIs
   - Formato visual con colores

2. **`historial_mejoras_bruce.json`**
   - Historial acumulativo de todos los análisis
   - Incluye:
     - Fecha de análisis
     - KPIs de la semana
     - Mejoras propuestas
     - Mejoras autorizadas
     - Estado de aplicación

**Ejemplo de historial:**
```json
[
  {
    "fecha": "2024-12-27",
    "stats": {
      "total_llamadas": 45,
      "tasa_conversion": 71.11,
      "interes_promedio": "Alto",
      "animo_predominante": "Positivo"
    },
    "analisis": {
      "resumen": "Buena tasa de conversión...",
      "mejoras_criticas": ["..."],
      "mejoras_sugeridas": ["..."]
    },
    "autorizado": true,
    "mejoras_seleccionadas": [1, 2, 4],
    "archivo_excel": "analisis_bruce_20241227_090015.xlsx"
  }
]
```

---

## ⚙️ CONFIGURACIÓN

### Cambiar día/hora de ejecución

Editar [auto_mejora_scheduler.py](C:\Users\PC 1\AgenteVentas\auto_mejora_scheduler.py):

```python
# Línea ~460
schedule.every().friday.at("09:00").do(ejecutar_analisis_programado)

# Cambiar a:
schedule.every().monday.at("14:00").do(ejecutar_analisis_programado)  # Lunes 2pm
schedule.every().wednesday.at("08:30").do(ejecutar_analisis_programado)  # Miércoles 8:30am
```

### Cambiar período de análisis

Editar [auto_mejora_bruce.py](C:\Users\PC 1\AgenteVentas\auto_mejora_bruce.py):

```python
# Línea 97
hace_7_dias = datetime.now() - timedelta(days=7)

# Cambiar a:
hace_14_dias = datetime.now() - timedelta(days=14)  # Últimos 14 días
hace_30_dias = datetime.now() - timedelta(days=30)  # Último mes
```

---

## 🐛 SOLUCIÓN DE PROBLEMAS

### Error: "No hay datos suficientes para analizar"

**Causa:** Menos de 1 llamada en los últimos 7 días

**Solución:**
- Esperar a tener más llamadas
- O reducir período de análisis (ver Configuración)

---

### Error: "Error al obtener estadísticas"

**Causa:** No se puede conectar a Google Sheets

**Solución:**
1. Verificar credenciales en `bubbly-subject-412101-c969f4a975c5.json`
2. Verificar acceso del Service Account al spreadsheet
3. Verificar conexión a internet

---

### Excel no se genera

**Causa:** Faltan dependencias

**Solución:**
```bash
pip install pandas openpyxl
```

---

### Sistema no se ejecuta el viernes

**Causa:** El script no está corriendo continuamente

**Solución:**
- Dejar la terminal abierta con `iniciar_auto_mejora.bat` corriendo
- O usar Windows Task Scheduler para iniciarlo automáticamente

---

## 📈 EJEMPLO DE FLUJO COMPLETO

### Viernes 9:00 AM - Ejecución Automática

```
🔔🔔🔔🔔🔔🔔🔔🔔🔔🔔🔔🔔🔔🔔🔔🔔🔔🔔🔔🔔
              ⏰ ANÁLISIS SEMANAL PROGRAMADO
           Fecha: 27/12/2024 09:00:15
🔔🔔🔔🔔🔔🔔🔔🔔🔔🔔🔔🔔🔔🔔🔔🔔🔔🔔🔔🔔

📊 Analizando llamadas de los últimos 7 días...

[... Muestra KPIs y análisis ...]

================================================================================
                       ⚠️ SOLICITUD DE AUTORIZACIÓN
================================================================================

👤 Tu respuesta: AUTORIZACION 1,2,4

✅ Autorización recibida para mejoras: [1, 2, 4]

📄 Generando reporte Excel final con cambios aprobados...

✅ Excel generado: analisis_bruce_20241227_090032.xlsx

🔧 Aplicando mejoras autorizadas...

✅ Se aplicarán 3 modificaciones al SYSTEM_PROMPT:
  1. MANEJO DE OBJECIONES: Mejorar respuesta a "Ya tengo proveedores"
  2. FASE 5: CIERRE: Fortalecer cierre cuando dice "Lo voy a pensar"
  3. FASE 3: CALIFICACIÓN: Agregar confirmación de comprensión

================================================================================
✅ PROCESO COMPLETADO
================================================================================

📊 Reporte Excel: analisis_bruce_20241227_090032.xlsx
💾 Historial actualizado: historial_mejoras_bruce.json
🔧 Modificaciones aprobadas: 3

⚠️ IMPORTANTE: Las modificaciones están documentadas en el historial.
   Para aplicarlas al código, revisa el archivo Excel y actualiza
   manualmente el SYSTEM_PROMPT en agente_ventas.py

================================================================================
```

---

## 🎯 MEJORES PRÁCTICAS

1. **Revisar siempre el Excel antes de autorizar**
2. **No aplicar todas las mejoras a la vez** - mejor hacerlo gradualmente
3. **Probar con 5-10 llamadas** después de cada cambio
4. **Comparar tasas de conversión** antes y después
5. **Mantener backup** del `agente_ventas.py` original
6. **Documentar resultados** en el commit de git

---

## 📞 PRÓXIMOS PASOS

1. ✅ **Probar el sistema inmediatamente:**
   ```bash
   python auto_mejora_scheduler.py --test
   ```

2. ✅ **Dejar corriendo para el viernes:**
   ```bash
   iniciar_auto_mejora.bat
   ```

3. ✅ **Hacer al menos 10-15 llamadas esta semana** para tener datos

4. ✅ **El viernes a las 9:00 AM:**
   - Revisar análisis
   - Autorizar mejoras específicas
   - Aplicar cambios al código

---

**Estado:** ✅ Sistema listo para usar
**Fecha:** 27 de diciembre 2024
