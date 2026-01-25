# PLAN DE TESTEO - IMPORTADOR MEJORADO
**Fecha inicio**: 2026-01-24
**Objetivo**: Validar que IMPORTADOR_CONTACTOS_MEJORADO.py mejora conversión de 5.17% a 10%+

---

## 🎯 OBJETIVOS DEL TESTEO

### Métricas Objetivo
```
CONVERSIÓN:
- Mínimo aceptable: >= 8.0% (mejora 55% vs 5.17%)
- Bueno: >= 10.0% (mejora 93% vs 5.17%)
- Excelente: >= 12.0% (mejora 132% vs 5.17%)

INTERÉS BAJO:
- Máximo aceptable: <= 35% (reducción 40% vs 57.8%)
- Bueno: <= 25% (reducción 57% vs 57.8%)
- Excelente: <= 20% (reducción 65% vs 57.8%)

CALIDAD DE LEADS:
- Leads irrelevantes: < 5% (era ~33%)
- Negocios cerrados: < 3% (nuevo filtro)
- Errores técnicos: < 2%
```

---

## 📋 FASES DEL TESTEO

### FASE 1: Batch Inicial (200 llamadas)
**Duración**: 1-2 días
**Objetivo**: Validación básica del importador

```bash
# Paso 1: Generar leads con importador mejorado
cd C:\Users\PC 1
python IMPORTADOR_CONTACTOS_MEJORADO.py
# Input: Guadalajara
# Generar 250 leads (margen de 50 para NO CONTESTA/IVR)

# Paso 2: Ejecutar campaña
cd AgenteVentas
python sistema_llamadas_nioval.py --limite 200

# Paso 3: Auditoría profunda
python auditoria_profunda_testeo.py --ultimas 200
```

**Criterios de decisión**:
```python
if conversion >= 10.0 and interes_bajo <= 30.0:
    DECISION = "✅ CONTINUAR A FASE 2"
elif conversion >= 8.0:
    DECISION = "⚠️ REVISAR 10 llamadas + CONTINUAR"
else:
    DECISION = "❌ DETENER - Investigar problema"
```

---

### FASE 2: Validación Ampliada (300 llamadas adicionales = 500 totales)
**Duración**: 2-3 días
**Objetivo**: Confirmar estabilidad de métricas

```bash
# Paso 1: Generar más leads si es necesario
cd C:\Users\PC 1
python IMPORTADOR_CONTACTOS_MEJORADO.py

# Paso 2: Ejecutar campaña
cd AgenteVentas
python sistema_llamadas_nioval.py --limite 300

# Paso 3: Auditoría profunda de TODAS las 500 llamadas
python auditoria_profunda_testeo.py --ultimas 500
```

**Criterios de decisión**:
```python
if conversion >= 10.0 and estable_por_3_dias:
    DECISION = "✅ PASAR A PRODUCCIÓN CONTROLADA"
elif conversion >= 8.0:
    DECISION = "⚠️ CONTINUAR TESTEO (más 200 llamadas)"
else:
    DECISION = "❌ REVISAR ESTRATEGIA"
```

---

### FASE 3: Producción Controlada (1000 llamadas/semana)
**Duración**: 2 semanas
**Objetivo**: Estabilizar sistema antes de escalar

```bash
# Semana 1: 500 llamadas
python sistema_llamadas_nioval.py --limite 100  # 5 días × 100 llamadas

# Auditoría al final de semana
python auditoria_profunda_testeo.py --ultimas 500

# Semana 2: 750 llamadas
python sistema_llamadas_nioval.py --limite 150  # 5 días × 150 llamadas

# Auditoría final
python auditoria_profunda_testeo.py --ultimas 750
```

**Criterios de éxito**:
```
✅ Conversión promedio >= 10% durante 2 semanas
✅ Interés Bajo promedio <= 30%
✅ Sin errores técnicos críticos
✅ Sistema estable (sin crashes)
```

---

### FASE 4: Producción Completa
**A partir de**: Después de validar Fase 3
**Volumen**: 1500-2000 llamadas/semana

```bash
# Cambiar a monitoreo semanal automático
python auto_mejora_bruce.py  # Cada domingo

# Auditorías profundas solo si:
# - Conversión cae < 8%
# - Interés Bajo sube > 35%
# - Errores técnicos > 2%
```

---

## 🔍 HERRAMIENTAS DE AUDITORÍA

### 1. Auditoría Profunda (después de cada fase)
```bash
python auditoria_profunda_testeo.py --ultimas 200
python auditoria_profunda_testeo.py --desde "2026-01-24"
```

**Tiempo**: 10-15 min (automático)
**Output**: Reporte completo con 9 secciones + decisión

---

### 2. Auditoría Rápida (opcional, entre batches)
```bash
python analisis_rapido_batch.py --batch 50
python analisis_rapido_batch.py --ultimas 100
```

**Tiempo**: 2-3 min (automático)
**Output**: Métricas principales + decisión (CONTINUAR/REVISAR/DETENER)

---

### 3. Análisis Manual (si auditoría detecta problemas)
```bash
# Descargar logs de Railway
python descargar_logs_railway.py --hours 24

# Buscar casos específicos
grep "NEGADO" logs_railway_recent.txt | tail -10
grep "Interés: Bajo" logs_railway_recent.txt | tail -10

# Analizar llamada específica
python analizar_llamada_especifica.py BRUCE1450
```

---

## 📊 DASHBOARD DE MONITOREO

### Métricas a Monitorear Diariamente (Fase 1-3)

```
DÍA A DÍA:
┌─────────────────────────────────────────────────┐
│ CONVERSIÓN:     10.5% ✅ (+5.3% vs baseline)   │
│ INTERÉS BAJO:   24.2% ✅ (-33.6% vs baseline)  │
│ WHATSAPPS:      21 de 200 llamadas             │
│ ERRORES TÉC:    1.0% ✅                        │
│ LEADS IRRELEVANTES: 2.5% ✅                    │
│ NEGOCIOS CERRADOS: 1.0% ✅                     │
└─────────────────────────────────────────────────┘

DECISIÓN: ✅ CONTINUAR - Métricas superan objetivo
```

---

## 🚨 TRIGGERS DE ALERTA

### Detener inmediatamente si:
```python
if conversion_batch < 5.0:  # Peor que baseline
    ALERTA("❌ IMPORTADOR EMPEORÓ RESULTADOS")

if errores_consecutivos >= 5:
    ALERTA("❌ BUG CRÍTICO EN SISTEMA")

if crashes_por_hora >= 2:
    ALERTA("❌ INESTABILIDAD DEL SISTEMA")

if tasa_irrelevantes > 10.0:  # Filtro no funciona
    ALERTA("❌ IMPORTADOR NO FILTRA CORRECTAMENTE")
```

### Revisar inmediatamente si:
```python
if conversion_batch < 8.0:
    REVISAR("⚠️ No alcanza mínimo - Revisar 10 llamadas NEGADAS")

if interes_bajo > 40.0:
    REVISAR("⚠️ Interés bajo muy alto - Revisar calidad leads")

if duracion_promedio < 40:
    REVISAR("⚠️ Clientes cuelgan rápido - Revisar saludo")
```

---

## 📅 CALENDARIO ESTIMADO

```
SEMANA 1 (Ene 24-31):
├─ Lun 24: Generar 250 leads + Batch 1 (100 llamadas)
├─ Mar 25: Batch 2 (100 llamadas) + Auditoría 200 llamadas ✅
├─ Decisión: CONTINUAR o DETENER
├─ Mie 26: Batch 3 (150 llamadas)
├─ Jue 27: Batch 4 (150 llamadas)
├─ Vie 28: Auditoría 500 llamadas totales ✅
└─ Decisión: PRODUCCIÓN CONTROLADA o MÁS TESTEO

SEMANA 2 (Feb 1-7):
├─ Lun-Vie: 100 llamadas/día (500 semana)
└─ Dom: Auditoría semanal ✅

SEMANA 3 (Feb 8-14):
├─ Lun-Vie: 150 llamadas/día (750 semana)
└─ Dom: Auditoría semanal + Decisión FINAL ✅

SEMANA 4+ (Feb 15+):
└─ PRODUCCIÓN COMPLETA (1500-2000/semana)
```

---

## ✅ CRITERIOS DE ÉXITO FINAL

Para declarar IMPORTADOR_CONTACTOS_MEJORADO.py como **EXITOSO**:

```
1. ✅ Conversión >= 10% (vs 5.17% baseline) - SOSTENIDA por 2 semanas
2. ✅ Interés Bajo <= 30% (vs 57.8% baseline) - SOSTENIDA por 2 semanas
3. ✅ Leads irrelevantes < 5% (vs ~33% antes)
4. ✅ Negocios cerrados < 3%
5. ✅ Sin errores técnicos críticos (< 2%)
6. ✅ Sistema estable (sin crashes)
7. ✅ Mismos WhatsApps con ~60% menos llamadas
```

**Si se cumplen 6/7 criterios** → ÉXITO ✅
**Si se cumplen 4-5/7 criterios** → ÉXITO PARCIAL ⚠️ (requiere ajustes)
**Si se cumplen < 4/7 criterios** → FALLÓ ❌ (revisar estrategia)

---

## 📝 NOTAS IMPORTANTES

1. **NO ejecutar más de 200 llamadas sin auditoría profunda** en Fase 1-2
2. **DETENER inmediatamente** si conversión < 5% (peor que baseline)
3. **Respaldar logs de Railway** después de cada batch importante
4. **Documentar cualquier cambio** al código durante testeo
5. **NO cambiar múltiples variables** simultáneamente (solo importador)

---

**Última actualización**: 2026-01-24 23:50
**Autor**: Claude Sonnet 4.5
**Relacionado con**:
- IMPORTADOR_CONTACTOS_MEJORADO.py
- auditoria_profunda_testeo.py
- analisis_rapido_batch.py
- RESUMEN_EJECUTIVO_FINAL_2026-01-24.md
