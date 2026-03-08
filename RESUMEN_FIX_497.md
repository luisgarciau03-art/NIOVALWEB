# FIX 497: SISTEMA DE DETECCIÓN SEMÁNTICA ROBUSTO

**Fecha**: 2026-01-25
**Estado**: DESPLEGADO EN PRODUCCIÓN

---

## PROBLEMA IDENTIFICADO (70% de fallos)

1. **No detecta encargado** con variaciones regionales
2. **No detecta ofertas de contacto** (correo/WhatsApp)

### Ejemplos de Fallos:
```
Querétaro: "No está"                    → Bruce no entendía
CDMX:      "Jefe, disculpe aún no llega" → Bruce no entendía
Norte:     "El patrón anda pa fuera"     → Bruce no entendía
```

---

## SOLUCIÓN IMPLEMENTADA

### 4 CAPAS DE DETECCIÓN SEMÁNTICA:

---

### CAPA 1: ENCARGADO NO ESTÁ (50+ patrones)

**Regiones cubiertas:**
| Región | Ejemplos |
|--------|----------|
| Querétaro/Bajío | "no está", "no se encuentra", "salió" |
| CDMX | "jefe disculpe", "aún no llega", "ahorita no" |
| Norte (MTY, Chihuahua) | "no anda aquí", "anda pa fuera" |
| Bajío (GDL, León) | "el mero mero salió", "no anda" |
| General | "ocupado", "en junta", "fue a comer" |

**Sinónimos de "encargado" detectados:**
- Formales: gerente, director, administrador, responsable
- Informales: jefe, patrón, dueño, el mero mero
- Títulos: licenciado, ingeniero, contador

---

### CAPA 2: CLIENTE ES EL ENCARGADO (40+ patrones)

```
"Yo soy"           → Detectado
"Soy yo"           → Detectado
"Yo mero"          → Detectado
"Con él habla"     → Detectado
"A sus órdenes"    → Detectado
"Servidor"         → Detectado
"Sí lo soy"        → Detectado
"Así es"           → Detectado
"Mande"            → Detectado (CDMX)
"Simón"            → Detectado (Norte)
"Órale"            → Detectado (General)
```

---

### CAPA 3: CLIENTE ACEPTA CONTACTO (30+ patrones c/u)

**Correo:**
```
"Por correo"          → Detectado
"Al mail"             → Detectado
"Mándalo al correo"   → Detectado
"Mejor por correo"    → Detectado
```

**WhatsApp:**
```
"Por whatsapp"        → Detectado
"Al wasa"             → Detectado
"A este número"       → Detectado
"Por el wa"           → Detectado
```

---

### CAPA 4: CLIENTE OFRECE CONTACTO (40+ patrones c/u)

**Frases detectadas:**
```
"¿Te puedo pasar el correo?"     → "Sí, por favor, dígame el correo."
"Le doy el número"               → "Sí, por favor, dígame el número."
"Anote"                          → "Sí, por favor, dígame el número."
"Aquí está el correo"            → Detectado
"Es arroba gmail"                → Detectado (dictando)
"Toma nota"                      → Detectado
"Ahí le va"                      → Detectado
```

---

## ESTADÍSTICAS DE PATRONES

| Categoría | Patrones | Antes | Después |
|-----------|----------|-------|---------|
| Encargado NO está | 50+ | 11 | 50+ |
| Cliente ES encargado | 40+ | ~10 | 40+ |
| Acepta correo | 30+ | 12 | 30+ |
| Acepta WhatsApp | 30+ | 12 | 30+ |
| Ofrece correo | 25+ | 17 | 25+ |
| Ofrece WhatsApp | 40+ | 17 | 40+ |
| **TOTAL** | **215+** | ~79 | **215+** |

---

## MEJORA ESPERADA

```
ANTES:
- Detección limitada a frases exactas
- Solo español neutro
- 70% de fallos por variaciones regionales

DESPUÉS:
- Detección semántica por categorías
- Cobertura: CDMX, Norte, Bajío, Querétaro, general
- Reducción esperada: 60-70% de estos fallos
```

---

## PRÓXIMOS PASOS RECOMENDADOS

1. **Monitorear logs** de próximas 20-30 llamadas
2. **Identificar patrones no cubiertos** que aparezcan
3. **Agregar nuevos patrones** según se detecten

---

## CÓMO AGREGAR NUEVOS PATRONES

Si detectas un patrón no cubierto, agrégalo a la lista correspondiente en `agente_ventas.py`:

```python
# Línea ~5568: patrones_no_esta (encargado no está)
# Línea ~5653: patrones_acepta_correo
# Línea ~5683: patrones_acepta_whatsapp
# Línea ~5717: patrones_ofrece_correo
# Línea ~5749: patrones_ofrece_whatsapp
# Línea ~5804: patrones_soy_encargado
```

---

**Generado**: 2026-01-25 16:35
**Autor**: Claude Opus 4.5
**Commit**: 67a8234
