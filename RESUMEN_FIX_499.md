# FIX 499: BRUCE1475 - Email Completo No Procesado

**Fecha**: 2026-01-25
**Estado**: DESPLEGADO EN PRODUCCIÓN

---

## PROBLEMA IDENTIFICADO

### Log de BRUCE1475:
```
[16:36:24] BRUCE: "Perfecto. ¿Cuál es su correo electrónico?"
[16:36:33] CLIENTE: "Rodrigo Rodrigo 0.28 arroba Hotmail punto com."
           → FIX 265: Email parece completo - procesar normalmente
           → FIX 253: Cliente deletreando email (detectado: ['arroba', 'punto', 'hotmail'])
           → FIX 244: CLIENTE HABLANDO PAUSADAMENTE - esperando...
[16:36:40] CLIENTE: (repite el correo)  ← BRUCE NO RESPONDIÓ
[16:36:47] CLIENTE: ""
[16:36:55] CLIENTE: (repite el correo)  ← BRUCE NO RESPONDIÓ
[16:37:02] CLIENTE: (repite el correo)  ← BRUCE NO RESPONDIÓ
[16:37:09-17] CLIENTE: "" "" ""  ← 3 vacíos
[16:37:17] BRUCE: COLGÓ  ← FALSO NEGATIVO
```

### Problema:
- FIX 265 detectó que el email estaba **COMPLETO**
- Pero FIX 253 lo siguió marcando como "deletreando" (incompleto)
- FIX 244 siguió esperando más input
- Cliente repitió el correo **4 veces** sin confirmación
- Después de 3 silencios, Bruce colgó

---

## CAUSA RAÍZ

```
FIX 265:     email_parece_completo = True  ✓
FIX 253:     esta_deletreando_email = True  ← CONFLICTO
             frase_parece_incompleta = True  ← MAL
FIX 244:     esperando que termine...  ← LOOP INFINITO
```

Los FIX estaban en conflicto:
- FIX 265 decía "email completo, procesar"
- FIX 253 decía "tiene arroba/punto/hotmail, esperar más"
- FIX 244 obedecía a FIX 253 y seguía esperando

---

## SOLUCIÓN IMPLEMENTADA

### Nueva bandera: `email_detectado_completo`

```python
# Línea 2334: Inicializar bandera
email_detectado_completo = False

# Línea 2371: Marcar cuando email está completo
if email_parece_completo:
    email_detectado_completo = True

# Línea 2514: FIX 253 ahora respeta la bandera
if esta_deletreando_email and not email_detectado_completo:
    frase_parece_incompleta = True  # Solo si NO está completo
elif esta_deletreando_email and email_detectado_completo:
    print("FIX 499: Email COMPLETO - NO esperar más")
    # NO marcar como incompleto → flujo continúa a GPT
```

---

## FLUJO CORREGIDO

Con FIX 499, BRUCE1475 hubiera funcionado así:

```
[16:36:33] CLIENTE: "Rodrigo 0.28 arroba Hotmail punto com."
           → FIX 265: Email parece completo ✓
           → FIX 499: email_detectado_completo = True
           → FIX 253: NO marca como incompleto (bandera activa)
           → Flujo continúa a _extraer_datos()
           → Email guardado: rodrigo0.28@hotmail.com
[16:36:34] BRUCE: "Perfecto, ya lo tengo anotado. Le llegará el catálogo en las próximas horas."
```

---

## RESUMEN DE FIX 498 + FIX 499

### FIX 498 (commit 66c1d8a):
- Detectar ofertas de correo/WhatsApp durante modo espera
- Detectar verificación de presencia ("Hola, hola")
- Diferenciar silencio (cadena vacía) vs IVR (None)

### FIX 499 (commit 9d2b26c):
- Nueva bandera `email_detectado_completo`
- FIX 253 respeta cuando email ya está completo
- No esperar indefinidamente cuando email está listo

---

## COMMITS

- `66c1d8a`: FIX 498 - Corregir falsos positivos IVR en modo espera
- `9d2b26c`: FIX 499 - Email completo no procesado por conflicto FIX 253/265

---

**Generado**: 2026-01-25 17:15
**Autor**: Claude Opus 4.5
