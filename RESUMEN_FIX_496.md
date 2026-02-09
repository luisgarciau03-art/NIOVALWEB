# RESUMEN FIX 496: BRUCE1472 - Detectar cliente ofrece correo/WhatsApp

**Fecha**: 2026-01-25
**Problema detectado en**: BRUCE1472

---

## PROBLEMA IDENTIFICADO

### Log de BRUCE1472:
```
[15:54:49] [BRUCE] "Entiendo. ¿Me podría proporcionar el WhatsApp del encargado?"
[15:54:58] [CLIENTE] "está, llega como a las 3. ¿Te puedo pasar el correo?"
[15:55:05] [BRUCE] "Claro, espero."  ← ERROR: No entendió la oferta
[15:55:11] [CLIENTE] "¿Bueno? ¿Por correo?"
```

**Causa raíz**: Cliente OFRECIÓ dar el correo ("¿Te puedo pasar el correo?") pero Bruce no lo detectó y respondió con "Claro, espero." en lugar de aceptar la oferta.

---

## SOLUCIÓN IMPLEMENTADA

### FIX 496: Detección de ofertas de correo/WhatsApp

**Ubicación**: `agente_ventas.py` líneas 5621-5666

**Patrones para CORREO**:
```python
patrones_ofrece_correo = [
    'te puedo pasar el correo', 'le puedo pasar el correo',
    'te paso el correo', 'le paso el correo',
    'te doy el correo', 'le doy el correo',
    'quiere el correo', 'quieres el correo',
    'te mando el correo', 'le mando el correo',
    'anota el correo', 'anote el correo',
    'apunta el correo', 'apunte el correo',
    'tengo el correo', 'aquí tengo el correo',
    'puedo darle el correo', 'puedo darte el correo'
]
→ Respuesta: "Sí, por favor, dígame el correo."
```

**Patrones para WHATSAPP**:
```python
patrones_ofrece_whatsapp = [
    'te puedo pasar el whatsapp', 'le puedo pasar el whatsapp',
    'te paso el whatsapp', 'le paso el whatsapp',
    'te doy el whatsapp', 'le doy el whatsapp',
    'quiere el whatsapp', 'quieres el whatsapp',
    'te mando el whatsapp', 'le mando el whatsapp',
    'anota el whatsapp', 'anote el whatsapp',
    'tengo el whatsapp', 'aquí tengo el whatsapp',
    'te paso el número', 'le paso el número',
    'te doy el número', 'le doy el número'
]
→ Respuesta: "Sí, por favor, dígame el número."
```

---

## NOTA SOBRE BRUCE1471

El loop de 5 repeticiones en BRUCE1471 ocurrió **ANTES** de que FIX 493 fuera desplegado.

### Commits de protección anti-loop:
- `02677c9`: FIX 493 (Parte 1) - Anti-loop básico
- `047ecaf`: FIX 493 (Parte 2) - Parche global
- `21aed77`: FIX 493 (Parte 4) - Auditoría completa

**Estos fixes YA están en el código pero necesitan DEPLOY a Railway.**

---

## ACCIÓN REQUERIDA

```bash
# Desplegar a Railway
cd C:\Users\PC 1\AgenteVentas
git push origin main

# O usar Railway CLI
railway up
```

---

## FIXES ACUMULADOS PENDIENTES DE DEPLOY

| FIX | Descripción | Commit |
|-----|-------------|--------|
| 493 | Anti-loop encargado (5 partes) | 02677c9 - 21aed77 |
| 494 | Protección respuestas incoherentes | 91a127e |
| 495 | Detectar "Por correo" | 494c007 |
| 496 | Cliente OFRECE correo/WhatsApp | 857a2bc |

---

**Generado**: 2026-01-25 16:15
**Autor**: Claude Opus 4.5
