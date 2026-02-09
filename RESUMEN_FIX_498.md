# FIX 498: BRUCE1473 - Corregir Modo Espera y Falsos Positivos IVR

**Fecha**: 2026-01-25
**Estado**: DESPLEGADO EN PRODUCCIÓN

---

## PROBLEMA IDENTIFICADO

### Log de BRUCE1473:
```
[16:22:18] CLIENTE: "Salió a comer llega más tarde."
[16:22:18] BRUCE:   "¿Me podría proporcionar el WhatsApp del encargado?"
[16:22:27] CLIENTE: "No, tendrías que esperar a que llegue él."
[16:22:27] BRUCE:   "Claro, espero."         ← ENTRA EN MODO ESPERA
[16:22:32] CLIENTE: "¿O quieres que te pase correo? ¿Te paso correo?"  ← OFERTA!
[16:22:33] BRUCE:   "Claro, espero."         ← BUG: IGNORA LA OFERTA
[16:22:45] CLIENTE: "Hola, hola. ¿Hola?"     ← Verifica si Bruce sigue ahí
[16:22:46] BRUCE:   IVR/CONTESTADORA - COLGANDO  ← FALSO POSITIVO!
```

### Problemas detectados:
1. **Modo espera ignoraba ofertas de correo/WhatsApp**
2. **Cliente verificando presencia era detectado como IVR**
3. **Bruce colgó a un cliente real**

---

## CAUSA RAÍZ

El modo espera (FIX 415) retornaba `None` para silenciarse, pero:
- El servidor interpretaba `None` como "IVR detectado = colgar"
- No había detección de ofertas de contacto durante la espera
- No había detección de verificación de presencia ("Hola, hola")

---

## SOLUCIÓN IMPLEMENTADA

### Parte 1: Detectar ofertas de correo durante espera
```python
patrones_ofrece_correo_espera = [
    'te puedo pasar el correo', 'le puedo pasar el correo',
    'te paso el correo', 'te paso correo', 'te doy el correo',
    'quieres que te pase correo', 'por correo', 'al correo',
    'anota el correo', 'anote el correo'
]
# Si detecta → "Sí, por favor, dígame el correo."
```

### Parte 2: Detectar ofertas de WhatsApp/número durante espera
```python
patrones_ofrece_whatsapp_espera = [
    'te paso el whatsapp', 'te paso el número', 'te doy el número',
    'quiere el número', 'anota el número', 'toma nota', 'ahí le va'
]
# Si detecta → "Sí, por favor, dígame el número."
```

### Parte 3: Detectar verificación de presencia
```python
patrones_verificando_presencia = [
    'hola', '¿hola?', 'bueno', '¿bueno?', '¿sigues ahí?',
    '¿me escucha?', '¿está ahí?', '¿oye?'
]
# Si detecta → "Sí, aquí estoy. Le espero."
```

### Parte 4: Diferenciar silencio vs IVR en servidor
```python
# Antes:
if respuesta_agente is None:  # → Colgar (IVR)

# Después:
if respuesta_agente is None:  # → Colgar (IVR)
elif respuesta_agente == "":  # → Seguir escuchando (modo espera)
```

---

## FLUJO CORREGIDO

Con FIX 498, BRUCE1473 hubiera funcionado así:

```
[16:22:27] BRUCE:   "Claro, espero."
[16:22:32] CLIENTE: "¿Te paso correo?"
           → FIX 498: Detecta oferta de correo
[16:22:33] BRUCE:   "Sí, por favor, dígame el correo."  ← CORRECTO!
           → Continúa conversación normal
```

O si el cliente verifica presencia:
```
[16:22:27] BRUCE:   "Claro, espero."
[16:22:45] CLIENTE: "Hola, hola. ¿Hola?"
           → FIX 498: Detecta verificación de presencia
[16:22:46] BRUCE:   "Sí, aquí estoy. Le espero."  ← CORRECTO!
           → NO cuelga, sigue esperando
```

---

## ARCHIVOS MODIFICADOS

| Archivo | Cambios |
|---------|---------|
| agente_ventas.py | +57 líneas: 3 tipos de detección durante espera |
| servidor_llamadas.py | +16 líneas: Manejo de respuesta vacía |

---

## COMMITS

- `66c1d8a`: FIX 498: BRUCE1473 - Corregir falsos positivos IVR en modo espera

---

## RESUMEN DE MEJORAS

| Escenario | Antes | Después |
|-----------|-------|---------|
| Cliente ofrece correo | "Claro, espero." | "Sí, por favor, dígame el correo." |
| Cliente ofrece número | "Claro, espero." | "Sí, por favor, dígame el número." |
| Cliente dice "Hola?" | CUELGA (IVR falso) | "Sí, aquí estoy. Le espero." |
| Cliente en silencio | Sigue esperando | Sigue esperando |

---

**Generado**: 2026-01-25 16:52
**Autor**: Claude Opus 4.5
