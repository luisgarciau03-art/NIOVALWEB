# 🚀 GUÍA RÁPIDA - Análisis de Logs BruceW

**Problema:** No tienes Railway CLI instalado
**Solución:** Usa la descarga manual (¡Más fácil!)

---

## ✅ OPCIÓN 1: Descarga Manual (RECOMENDADO)

### Paso 1: Ejecuta el script de descarga manual

```bash
python descargar_logs_web.py
```

**O más fácil:**
```bash
# Busca este archivo y doble clic:
descargar_logs_manual.bat
```

### Paso 2: Sigue las instrucciones en pantalla

El script te guiará:

1. Te dice que vayas a: https://railway.app/dashboard
2. Abres tu proyecto: **nioval-webhook-server**
3. Haces clic en **"Logs"**
4. Seleccionas cuántos logs quieres (1000 líneas o última hora)
5. Copias todo: **Ctrl+A** → **Ctrl+C**
6. El script abre Notepad automáticamente
7. Pegas los logs: **Ctrl+V**
8. Guardas el archivo
9. ¡El script analiza automáticamente!

### Resultado:

```
✅ Logs descargados en: C:\Users\PC 1\AgenteVentas\LOGS\logs_railway_20260114_153000.txt
✅ Análisis completo con errores, warnings y recomendaciones
```

---

## 📊 OPCIÓN 2: Analizar Archivo Existente

Si ya descargaste los logs manualmente:

```bash
python analizar_logs_railway.py LOGS\logs_railway_20260114_153000.txt
```

---

## 🔍 OPCIÓN 3: Analizar Llamada Específica

Si quieres investigar una llamada en particular (ejemplo: BRUCE460):

```bash
python analizar_llamada_especifica.py 460
```

Esto te muestra:
- ✅ Conversación completa (Bruce + Cliente)
- ✅ Errores específicos de esa llamada
- ✅ Qué fixes se activaron (FIX 201, 202, 203, 204)
- ✅ Métricas: palabras por mensaje, duración, etc.
- ✅ Análisis del resultado

---

## 📁 Dónde se Guardan los Logs

Todos los archivos se guardan en:
```
C:\Users\PC 1\AgenteVentas\LOGS\
```

Contenido:
- `logs_railway_20260114_153000.txt` - Logs descargados
- `analisis_BRUCE460_20260114_153500.txt` - Análisis individual
- `README_LOGS.md` - Documentación completa

---

## 🎯 Ejemplo de Uso Completo

### Escenario: Revisar errores del día

```bash
# 1. Descargar logs manualmente
python descargar_logs_web.py

# (Sigues la guía: copias logs de Railway → pegas en Notepad → guardas)

# 2. El análisis se ejecuta automáticamente y muestra:

🔍 ANALIZANDO ERRORES
Total: 5 errores
  • Error API ElevenLabs: 3x
  • Timeout: 2x

🚨 PROBLEMAS CRÍTICOS
🔥 CUOTA_EXCEDIDA: 3 ocurrencias

💰 CRÉDITOS ELEVENLABS
💵 Restantes: 28
   🚨 CRÍTICO: Créditos muy bajos!

💡 RECOMENDACIONES:
   1. ⚠️  URGENTE: Recargar créditos
   2. ✅ FIX 202 detectando IVRs correctamente
```

### Escenario: Investigar llamada específica

```bash
# Usuario reporta: "BRUCE460 repitió algo 3 veces"

python analizar_llamada_especifica.py 460

# Resultado:
💬 CONVERSACIÓN:
1. 🤖 BRUCE: Buenos días...
2. 👤 CLIENTE: Dígame
3. 🤖 BRUCE: Perfecto...
4. 👤 CLIENTE: ...

🚨 ERRORES DETECTADOS:
🔄 Reintento: 3 ocurrencias
   → Línea 245: Reintentando generación de audio...

🔧 FIXES ACTIVOS:
   ✅ FIX 204: 2 menciones (prevenir repeticiones)

📊 MÉTRICAS:
📝 Promedio: 22.5 palabras por mensaje
   ✅ Longitud adecuada
```

---

## ⚡ Atajos Rápidos

### Crear estos archivos .bat para 1 clic:

**`analizar_hoy.bat`**
```batch
@echo off
python descargar_logs_web.py
pause
```

**`revisar_bruce.bat`**
```batch
@echo off
set /p bruce_id="Ingresa ID de BRUCE: "
python analizar_llamada_especifica.py %bruce_id%
pause
```

---

## 🔧 Si Quieres Instalar Railway CLI (Opcional)

```bash
# 1. Instalar Node.js desde: https://nodejs.org/

# 2. Instalar Railway CLI
npm i -g @railway/cli

# 3. Login
railway login

# 4. Vincular proyecto
cd C:\Users\PC 1\AgenteVentas
railway link

# 5. ¡Listo! Ahora funciona automático:
python analizar_logs_railway.py
```

Con CLI instalado, el script descarga automáticamente sin pasos manuales.

---

## 📋 Resumen

| Método | Comandos | Ventajas |
|--------|----------|----------|
| **Manual (Recomendado)** | `python descargar_logs_web.py` | No requiere instalación, 100% guiado |
| **CLI Automático** | `python analizar_logs_railway.py` | 100% automático, pero requiere Railway CLI |
| **Archivo Existente** | `python analizar_logs_railway.py archivo.txt` | Usa logs ya descargados |
| **Llamada Específica** | `python analizar_llamada_especifica.py 460` | Análisis detallado individual |

---

## 💡 Consejos

1. **Ejecuta análisis después de cada batch de llamadas**
   - Detecta problemas temprano
   - Verifica que fixes funcionen

2. **Guarda los logs importantes**
   - Los análisis se guardan en LOGS/
   - Puedes compararlos entre fechas

3. **Revisa las recomendaciones**
   - El script te dice qué arreglar
   - Prioriza según criticidad

4. **Usa análisis individual para debugging**
   - Si ves error repetido, analiza 1 llamada
   - Encuentras causa raíz más rápido

---

**¡Ahora puedes analizar logs fácilmente sin Railway CLI!** 🎉

**Fecha:** 2026-01-14
**Versión:** 1.0
