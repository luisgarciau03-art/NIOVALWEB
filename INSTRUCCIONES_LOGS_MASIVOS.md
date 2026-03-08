# Instrucciones: Cómo Pasar Logs Masivos para Análisis

## 📋 Formato Requerido

Para analizar logs masivamente, necesito el archivo en uno de estos formatos:

### Opción 1: Logs de Railway (PREFERIDO)

Descarga los logs directamente de Railway y guárdalos en un archivo `.txt`:

```bash
# Usar el script de descarga
python descargar_logs_railway.py --ultimas 50

# O descargar manualmente desde Railway web
# https://railway.app → Tu proyecto → Deployments → View Logs → Copy All
```

Guarda en: `logs_railway_completos.txt`

### Opción 2: Logs del HTML (API)

Si los logs de Railway están incompletos, puedes usar el endpoint HTML:

```
https://nioval-webhook-server-production.up.railway.app/logs/api?lineas=50000
```

Copia y pega el contenido en un archivo `.txt`

### Opción 3: Logs separados por BRUCE ID

Si tienes múltiples llamadas identificadas, formato así:

```
BRUCE1140
[23:49:00] Bruce: "Buenos días..."
[23:49:02] Cliente: "Bueno."
[23:49:05] Bruce: "Me comunico de..."
[23:49:10] Cliente: "gracias."
[23:49:12] Bruce: "Perfecto, ya lo tengo registrado."  ← ERROR

BRUCE1141
[00:15:00] Bruce: "Buenos días..."
[00:15:02] Cliente: "Dígame."
[00:15:05] Cliente: "No está."
[00:15:07] Bruce: "¿Le envío el catálogo completo?"  ← ERROR

BRUCE1142
...
```

---

## 🚀 Cómo Ejecutar el Análisis

Una vez tengas el archivo:

```bash
# Opción 1: Logs en archivo txt
python analizar_encargado_masivo.py logs_railway_completos.txt

# Opción 2: Logs descargados de API
python analizar_encargado_masivo.py logs_api.txt

# Opción 3: Ruta específica
python analizar_encargado_masivo.py "C:\Users\PC 1\Downloads\logs_bruce_20260121.txt"
```

---

## 📊 Qué Detecta el Análisis

El script automáticamente detecta estos **2 problemas críticos** que mencionas:

### 1. "Ya lo tengo registrado" sin datos
```
Cliente: "gracias."
Bruce: "Perfecto, ya lo tengo registrado."  ← ❌ SIN WhatsApp/Email
```

**Detección**: ERROR_YA_TENGO_SIN_DATOS

### 2. No sabe qué hacer cuando "No está el encargado"
```
Cliente: "No está."
Bruce: "¿Le envío el catálogo completo?"  ← ❌ Sin contexto/alternativa
```

**Detección**: OFRECE_CATALOGO_CUANDO_NO_ESTA

**Plus**: También detecta:
- Cliente pregunta "¿de dónde habla?" → Bruce NO responde
- Cliente dice "con él/ella habla" → Bruce sigue preguntando por encargado
- Cliente dice "No" simple → Bruce insiste

---

## 📁 Archivos Que Genera

El análisis crea:

1. **Salida en consola** con resumen:
   ```
   📞 Llamadas analizadas: 25
      ✅ Sin errores: 18 (72.0%)
      ❌ Con errores: 7 (28.0%)

   🚨 Total de errores detectados: 12
      ERROR_YA_TENGO_SIN_DATOS: 5
      OFRECE_CATALOGO_CUANDO_NO_ESTA: 7
   ```

2. **Archivo JSON** con detalles completos:
   - `analisis_encargado_resultados.json`

---

## 🔍 Ejemplo Completo

```bash
# 1. Descargar logs de Railway
python descargar_logs_railway.py --ultimas 50

# 2. Analizar logs
python analizar_encargado_masivo.py logs_railway/latest_50.txt

# 3. Ver resultados
# - Consola muestra resumen
# - JSON tiene detalles completos

# 4. Revisar errores específicos
cat analisis_encargado_resultados.json | grep -A 10 "ERROR_YA_TENGO_SIN_DATOS"
```

---

## ⚡ Opción Rápida: Pegar Logs Aquí

Si prefieres, puedes copiar y pegar los logs DIRECTAMENTE en este chat:

**Formato esperado**:
```
BRUCE1140
[Logs completos de la llamada...]

BRUCE1141
[Logs completos de la llamada...]
```

Y yo puedo:
1. Guardarlos en un archivo temporal
2. Ejecutar el análisis
3. Mostrarte los errores detectados
4. Sugerir fixes específicos

---

## 📞 Preguntas Frecuentes

**Q: ¿Cuántas llamadas puedo analizar a la vez?**
A: Sin límite. El script puede procesar cientos de llamadas simultáneamente.

**Q: ¿El formato de timestamp es importante?**
A: No. El script detecta estos formatos:
- `[HH:MM:SS]`
- `[YYYY-MM-DD HH:MM:SS]`
- `[DD/MM/YYYY HH:MM:SS]`

**Q: ¿Necesito separar por BRUCE ID?**
A: No. Si no hay BRUCE ID, analiza como una sola llamada o intenta detectar separaciones.

**Q: ¿Puedo analizar logs en inglés u otro idioma?**
A: Actualmente solo detecta patrones en español. Se puede extender fácilmente.

---

## 🎯 Siguiente Paso

**Una vez tengas el archivo de logs**, ejecuta:

```bash
python analizar_encargado_masivo.py <archivo_logs.txt>
```

O **pega los logs directamente aquí** y yo los analizo inmediatamente.
