# FIX 500: BRUCE1476 - Separar OFERTAS de DICTADO

**Fecha**: 2026-01-25
**Estado**: DESPLEGADO EN PRODUCCIÓN

---

## PROBLEMA IDENTIFICADO

### Log de BRUCE1476:
```
[16:52:59] BRUCE: "¿Me podría proporcionar el WhatsApp del encargado?"
[16:53:12] CLIENTE: "Te puedo pasar el correo."
           → FIX 443: CLIENTE OFRECIENDO DATOS - esperar a que termine  ← ERROR!
           → FIX 244: Esperando continuación con timeout de 2.5s...
[16:53:27] CLIENTE: "" (silencio - esperando respuesta)
[16:53:28] BRUCE: "Disculpa, no te escuché bien..."  ← MAL!
[16:53:33] CLIENTE: "Por correo, por correo."
           → FIX 244: Esperando continuación...  ← ERROR OTRA VEZ!
[16:53:51] LLAMADA TERMINADA  ← Cliente frustrado
```

### El Problema:
- FIX 443 detectaba "te puedo pasar el correo" como "ofrecimiento de datos"
- Pero el cliente está **PREGUNTANDO** si quieres el correo, no dándolo
- Bruce esperaba más input en lugar de responder "Sí, dígame"
- Cliente repitió 3 veces sin obtener respuesta

---

## CAUSA RAÍZ

FIX 443 mezclaba dos tipos de frases:

| Tipo | Ejemplo | Acción Correcta |
|------|---------|-----------------|
| **OFERTA** | "Te puedo pasar el correo" | Responder: "Sí, dígame" |
| **DICTADO** | "El correo es juan@gmail.com" | Esperar que termine |

FIX 443 trataba ambos casos igual: **ESPERAR**. Incorrecto.

---

## SOLUCIÓN IMPLEMENTADA

### FIX 500: Separar OFERTAS de DICTADO

**Nuevas categorías:**

1. **OFERTAS** → Respuesta INMEDIATA
```python
frases_oferta_correo = [
    'te puedo pasar el correo', 'le puedo pasar el correo',
    'te paso el correo', 'por correo', 'quieres el correo'...
]
# → "Sí, por favor, dígame el correo."

frases_oferta_whatsapp = [
    'te puedo pasar el whatsapp', 'te paso el número',
    'por whatsapp', 'quieres el número'...
]
# → "Sí, por favor, dígame el número."
```

2. **DICTADO** → Esperar que termine (FIX 443 original)
```python
frases_dictando_datos = [
    'anota', 'apunta', 'ahí le va', 'el correo es',
    'arroba', 'gmail', 'hotmail', 'punto com'...
]
# → Esperar 2.5s para captar todo
```

---

## FLUJO CORREGIDO

Con FIX 500, BRUCE1476 hubiera funcionado así:

```
[16:52:59] BRUCE: "¿Me podría proporcionar el WhatsApp?"
[16:53:12] CLIENTE: "Te puedo pasar el correo."
           → FIX 500: Cliente OFRECE correo - Respuesta INMEDIATA
[16:53:13] BRUCE: "Sí, por favor, dígame el correo."  ← CORRECTO!
[16:53:18] CLIENTE: "rodrigo arroba hotmail punto com"
           → FIX 443: DICTADO detectado - Esperar
[16:53:22] BRUCE: "Perfecto, ya lo tengo anotado."
```

---

## RESUMEN DE CAMBIOS

| Escenario | Antes | Después |
|-----------|-------|---------|
| "Te puedo pasar el correo" | Esperar (bug) | "Sí, dígame el correo" |
| "Por correo" | Esperar (bug) | "Sí, dígame el correo" |
| "Te paso el número" | Esperar (bug) | "Sí, dígame el número" |
| "El correo es juan@..." | Esperar | Esperar (sin cambio) |
| "arroba gmail punto com" | Esperar | Esperar (sin cambio) |

---

## ARCHIVOS MODIFICADOS

| Archivo | Cambios |
|---------|---------|
| servidor_llamadas.py | +70 líneas: FIX 500 con separación OFERTA/DICTADO |

---

## COMMIT

- `32b992d`: FIX 500: BRUCE1476 - Separar OFERTAS de DICTADO en detección de correo/WhatsApp

---

**Generado**: 2026-01-25 17:25
**Autor**: Claude Opus 4.5
