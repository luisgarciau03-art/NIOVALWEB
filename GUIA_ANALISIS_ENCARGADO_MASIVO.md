# Guía: Análisis Masivo de Manejo del Encargado de Compras

**FIX 404**: Herramienta para detectar automáticamente errores en el manejo del encargado de compras analizando múltiples logs simultáneamente.

---

## 🎯 ¿Qué Detecta?

El script `analizar_encargado_masivo.py` detecta **4 tipos de errores críticos**:

### 1. Ofrece Catálogo Cuando Cliente Dice "No Está"
**Problema**: Cliente dice "no está" / "no se encuentra" pero Bruce inmediatamente ofrece catálogo sin alternativa.

**Ejemplo**:
```
[23:04:48] Cliente: "No, no se encuentra."
[23:04:50] Bruce: "Perfecto. ¿Le envío el catálogo completo?"  ❌ ERROR
```

**Debería decir**:
```
[23:04:50] Bruce: "Entiendo. ¿Le gustaría que le envíe el catálogo por WhatsApp para que lo revise cuando regrese?"  ✅
```

---

### 2. No Responde "¿De Dónde Habla?"
**Problema**: Cliente pregunta de dónde habla pero Bruce NO menciona NIOVAL/empresa.

**Ejemplo**:
```
[23:05:10] Cliente: "¿De dónde me habla?"
[23:05:12] Bruce: "¿Se encontrará el encargado de compras?"  ❌ ERROR
```

**Debería decir**:
```
[23:05:12] Bruce: "Me comunico de la marca NIOVAL para ofrecer información de productos de ferretería. ¿Se encontrará el encargado?"  ✅
```

---

### 3. Insiste en Encargado Cuando Ya Habla Con Él
**Problema**: Cliente dice "con él/ella habla" pero Bruce sigue preguntando por encargado.

**Ejemplo**:
```
[23:06:20] Cliente: "Sí, con ella habla."
[23:06:22] Bruce: "¿Se encontrará la encargada de compras?"  ❌ ERROR
```

**Debería decir**:
```
[23:06:22] Bruce: "Perfecto. Le comento que manejamos productos de ferretería..."  ✅
```

---

### 4. Insiste Después de "No" Simple
**Problema**: Cliente dice "No" simple después de pregunta por encargado, pero Bruce insiste.

**Ejemplo**:
```
[23:07:30] Bruce: "¿Se encontrará el encargado de compras?"
[23:07:32] Cliente: "No."
[23:07:34] Bruce: "¿Me comunica con el encargado?"  ❌ ERROR
```

**Debería decir**:
```
[23:07:34] Bruce: "Entiendo. ¿Le gustaría que le envíe el catálogo por WhatsApp?"  ✅
```

---

## 📝 Formato de Archivo de Logs

El script acepta logs en el siguiente formato:

### Opción 1: Logs con BRUCE ID separados
```
BRUCE1134
[22:54:10] Bruce: "Buenos días..."
[22:54:12] Cliente: "Dígame."
[22:54:15] Bruce: "Me comunico de NIOVAL..."
[22:54:20] Cliente: "No está."
[22:54:22] Bruce: "¿Le envío el catálogo?"

BRUCE1135
[23:05:10] Bruce: "Buenos días..."
[23:05:12] Cliente: "Bueno."
...
```

### Opción 2: Logs de una sola llamada
```
[22:54:10] Bruce: "Buenos días..."
[22:54:12] Cliente: "Dígame."
[22:54:15] Bruce: "Me comunico de NIOVAL..."
...
```

El script automáticamente detecta el formato y procesa correctamente.

---

## 🚀 Cómo Usar

### Paso 1: Tener el archivo de logs

Descarga o copia los logs completos a un archivo `.txt` o `.log`. Por ejemplo:
- `logs_completos.txt`
- `bruce_llamadas.log`
- `analisis_enero_21.txt`

### Paso 2: Ejecutar el script

```bash
python analizar_encargado_masivo.py <ruta_archivo_logs>
```

**Ejemplos**:

```bash
# Archivo en el mismo directorio
python analizar_encargado_masivo.py logs_completos.txt

# Archivo en otra ubicación
python analizar_encargado_masivo.py C:\Users\PC 1\Downloads\logs_bruce.log

# Archivo en carpeta AgenteVentas
python analizar_encargado_masivo.py AgenteVentas\logs_railway\logs_20260121.txt
```

### Paso 3: Revisar resultados

El script genera:

1. **Resumen en consola** con:
   - Total de llamadas analizadas
   - Llamadas con/sin errores
   - Errores por tipo y severidad
   - Detalles de cada error

2. **Archivo JSON** con resultados completos:
   - `analisis_encargado_resultados.json`

---

## 📊 Ejemplo de Salida

```
====================================================================================================
📊 RESUMEN DEL ANÁLISIS MASIVO - MANEJO DE ENCARGADO DE COMPRAS
====================================================================================================

📞 Llamadas analizadas: 10
   ✅ Sin errores: 6 (60.0%)
   ❌ Con errores: 4 (40.0%)

🚨 Total de errores detectados: 7

📋 Errores por severidad:
   ALTA: 5
   MEDIA: 2

📋 Errores por tipo:
   Ofrece Catalogo Cuando No Esta: 3
   No Responde De Donde Habla: 2
   Insiste Encargado Cuando Ya Habla Con El: 1
   Insiste Despues De No Simple: 1

====================================================================================================
🔍 ERRORES DETALLADOS
====================================================================================================

❌ ERROR 1/7 - OFRECE_CATALOGO_CUANDO_NO_ESTA
   BRUCE ID: BRUCE1134
   Timestamp: 22:54:20
   Severidad: ALTA
   Descripción: Cliente dijo que encargado NO está, pero Bruce ofreció catálogo sin alternativa
   Cliente dijo: "No, no se encuentra."
   Bruce respondió: "Perfecto. ¿Le envío el catálogo completo?"

❌ ERROR 2/7 - NO_RESPONDE_DE_DONDE_HABLA
   BRUCE ID: BRUCE1135
   Timestamp: 23:05:10
   Severidad: ALTA
   Descripción: Cliente preguntó de dónde habla pero Bruce NO mencionó NIOVAL
   Cliente dijo: "¿De dónde me habla?"
   Bruce respondió: "¿Se encontrará el encargado de compras?"

...

====================================================================================================

💾 Resultados guardados en: analisis_encargado_resultados.json

✅ Análisis completado

⚠️  Tasa de error: 40.0%
   🚨 CRÍTICO: Más del 30% de llamadas tienen errores
```

---

## 🔍 Interpretación de Resultados

### Severidad de Errores

- **ALTA**: Error que afecta directamente la experiencia del cliente
  - No responder "¿de dónde habla?"
  - Ofrecer catálogo cuando cliente dijo "no está"
  - Insistir cuando ya habla con encargado

- **MEDIA**: Error que puede causar frustración pero no es crítico
  - Insistir después de "No" simple

### Tasas de Error

- **< 10%**: Excelente - Pocos errores aislados
- **10-30%**: Aceptable pero mejorable
- **30-50%**: Alto - Requiere correcciones urgentes
- **> 50%**: Crítico - Sistema necesita refactorización

---

## 📁 Archivo JSON de Resultados

El archivo `analisis_encargado_resultados.json` contiene:

```json
{
  "llamadas_analizadas": 10,
  "llamadas_con_errores": 4,
  "llamadas_sin_errores": 6,
  "total_errores": 7,
  "errores_por_tipo": {
    "OFRECE_CATALOGO_CUANDO_NO_ESTA": 3,
    "NO_RESPONDE_DE_DONDE_HABLA": 2,
    "INSISTE_ENCARGADO_CUANDO_YA_HABLA_CON_EL": 1,
    "INSISTE_DESPUES_DE_NO_SIMPLE": 1
  },
  "errores_por_severidad": {
    "ALTA": 5,
    "MEDIA": 2
  },
  "errores_detallados": [
    {
      "tipo": "OFRECE_CATALOGO_CUANDO_NO_ESTA",
      "timestamp": "22:54:20",
      "cliente_dijo": "No, no se encuentra.",
      "bruce_respondio": "Perfecto. ¿Le envío el catálogo completo?",
      "bruce_id": "BRUCE1134",
      "severidad": "ALTA",
      "descripcion": "Cliente dijo que encargado NO está, pero Bruce ofreció catálogo sin alternativa"
    },
    ...
  ]
}
```

Puedes usar este JSON para:
- Análisis con herramientas externas (Excel, Python, etc.)
- Tracking de mejoras a lo largo del tiempo
- Reportes automáticos

---

## 🛠️ Personalización

Si quieres agregar nuevos patrones de detección, edita las listas en `analizar_encargado_masivo.py`:

```python
# Agregar nuevo patrón de "no está"
self.patrones_cliente_dice_no_esta = [
    r'no\s+est[aá]',
    r'no\s+se\s+encuentra',
    r'tu_nuevo_patron_aqui'  # ← AGREGAR AQUÍ
]
```

---

## ✅ Casos de Uso

### 1. Análisis Semanal de Producción
```bash
# Descargar logs de Railway de la semana
python descargar_logs_railway.py --semana

# Analizar logs
python analizar_encargado_masivo.py logs_railway/semana_21.txt

# Revisar tasa de error
# Si > 30% → Ajustar prompts o reglas
```

### 2. Validar Fixes Nuevos
```bash
# Antes del FIX
python analizar_encargado_masivo.py logs_antes_fix.txt
# Resultado: 40% error

# Después del FIX
python analizar_encargado_masivo.py logs_despues_fix.txt
# Resultado: 10% error → ✅ FIX funcionó
```

### 3. Comparar Versiones de Prompts
```bash
# Prompt v1
python analizar_encargado_masivo.py logs_prompt_v1.txt

# Prompt v2
python analizar_encargado_masivo.py logs_prompt_v2.txt

# Comparar tasas de error
```

---

## 🔗 Relacionado

- **FIX 400**: Detección mejorada de "no está" y "¿de dónde habla?"
- **FIX 393**: Patrones de encargado no disponible
- **FIX 397**: Detección "No" simple
- **REGLA CRÍTICA 2**: Responder empresa cuando cliente pregunta

---

## 📞 Soporte

Si el script no detecta correctamente un patrón que ves en los logs:

1. Anota el BRUCE ID y el mensaje exacto
2. Revisa si el formato de log coincide con el esperado
3. Agrega el patrón a las listas de detección
4. Reporta para agregar al script principal

---

**Fecha**: 2026-01-21
**Versión**: FIX 404 - Primera versión
