# FIX 191: Bloquear caché de despedida cuando cliente está deletreando email

## Problema Identificado

**Timestamp del log: 23:24:16 (12 Ene 2026)**

Bruce interrumpía al cliente cuando este estaba deletreando el correo electrónico:

```
Cliente: "I m de mamá n de niño de Pablo Rd Rodrigo"
Cliente: "Tito arroba"
Bruce: "Perfecto, ya lo tengo anotado. Le llegará el catálogo..." ❌ INTERRUMPE
```

### Causa Raíz

El caché automático en `servidor_llamadas.py` (línea 671-678) se activaba ANTES de que GPT pudiera procesar las instrucciones del sistema sobre email incompleto.

**Flujo defectuoso:**
1. Cliente dice "Tito arroba" (fragmento de email)
2. Sistema detecta email incompleto ✅
3. Añade instrucciones a GPT para pedir el resto ✅
4. **PERO** el caché devuelve "Perfecto, ya lo tengo anotado..." ANTES de que GPT procese ❌
5. Bruce termina llamada prematuramente sin capturar el email completo ❌

## Solución Implementada

### Cambio 1: Bloquear caché de despedidas de cierre

**Archivo:** `servidor_llamadas.py` (línea 671-691)

```python
# FIX 191: NUNCA usar caché si el texto contiene despedidas de cierre
palabras_cierre = ["perfecto ya lo tengo anotado", "perfecto, ya lo tengo anotado",
                  "le llegará el catálogo", "muchas gracias por su tiempo"]

es_despedida_cierre = any(palabra in texto_lower for palabra in palabras_cierre)

if es_despedida_cierre:
    print(f"🚫 FIX 191: Bloqueando caché de despedida - cliente aún puede estar hablando")
    # NO usar caché - dejar que GPT decida si es momento de despedirse
else:
    # Código normal de búsqueda en caché
```

**Efecto:** El caché de "Perfecto, ya lo tengo anotado..." ya NO se usará automáticamente. Solo GPT decide cuándo despedirse, considerando el contexto completo.

### Cambio 2: Instrucciones mejoradas a GPT

**Archivo:** `agente_ventas.py` (línea 3346-3371)

Mensaje del sistema mejorado cuando detecta email incompleto:

```
🚫🚫🚫 FIX 191: PROHIBIDO DECIR "PERFECTO, YA LO TENGO ANOTADO"
El cliente AÚN está hablando. NO lo interrumpas con despedidas.

ACCIÓN REQUERIDA:
1. Pide al cliente que CONTINÚE con el resto del correo
2. Di algo como: "Perfecto, excelente. Por favor, adelante con el correo."

❌ NO HACER:
- NO digas "ya lo tengo anotado" (NO lo tienes completo)
- NO te despidas (el cliente sigue hablando)

✅ HACER:
- Escucha pacientemente cada letra
- Deja que el cliente termine de deletrear
- Solo cuando tengas el correo COMPLETO, ahí sí confirma
```

## Comportamiento Esperado

### Antes del FIX 191 ❌

```
Cliente: "Te paso un correo"
Bruce: "Perfecto, excelente. Por favor, adelante con el correo."
Cliente: "m de mamá"
Bruce: "Entiendo, ¿me podría proporcionar el correo electrónico..."
Cliente: "Tito arroba"
Bruce: "Perfecto, ya lo tengo anotado. Le llegará..." ❌ INTERRUMPE SIN EMAIL
```

### Después del FIX 191 ✅

```
Cliente: "Te paso un correo"
Bruce: "Perfecto, excelente. Por favor, adelante con el correo."
Cliente: "m de mamá"
Bruce: "Entiendo, ¿me podría proporcionar el correo electrónico..."
Cliente: "Tito arroba"
Bruce: "Perfecto, adelante" ✅ ESPERA MÁS INFO
Cliente: "gmail.com"
Bruce: "Perfecto, ya lo tengo anotado: tito@gmail.com" ✅ AHORA SÍ SE DESPIDE
```

## Testing Recomendado

1. Llamar y deletrear un email muy lentamente
2. Decir solo "arroba" y pausar
3. Verificar que Bruce NO se despida prematuramente
4. Completar el email y verificar que ahora sí se despide

## Archivos Modificados

- `servidor_llamadas.py` (línea 671-691)
- `agente_ventas.py` (línea 3346-3371)

## Tags

`#audio-cache` `#deletreo-email` `#interrupcion` `#despedida-prematura` `#fix-191`
