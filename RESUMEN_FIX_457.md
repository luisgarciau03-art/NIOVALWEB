# RESUMEN FIX 457: No Pedir Número Cuando Cliente Ofrece Correo

## Casos Resueltos

| ID | Error Reportado | Causa Raiz | FIX |
|----|-----------------|------------|-----|
| BRUCE1370 | Le ofrecieron correo no entendió | FIX 311b sobrescribió respuesta correcta de GPT | FIX 457 |

---

## Problema

### Escenario BRUCE1370:
```
Cliente: "No, no se encuentra. Si quiere le doy un correo electrónico."
GPT generó: "Perfecto, ¿le gustaría recibir nuestro catálogo por correo?"
FIX 311b cambió a: "¿Me podría proporcionar el número directo del encargado?"
Bruce: IGNORÓ el ofrecimiento de correo y pidió número
Cliente: "No. Le doy un correo" (confundido, repite)
```

### Logs del problema:
```
📞 FIX 311b: FILTRO ACTIVADO - Encargado no está, pedir número ANTES de catálogo
   Cliente dijo: "no, no se encuentra. si quiere le doy un correo electrónico...."
   Bruce iba a ofrecer catálogo: "Perfecto, ¿le gustaría recibir nuestro catálogo por correo e..."
   Respuesta corregida: "Entiendo. ¿Me podría proporcionar el número directo del encargado?"
```

### Causa Raiz
FIX 311b detecta "no se encuentra" y fuerza a Bruce a pedir número del encargado.
Pero NO consideraba si el cliente está OFRECIENDO dar un dato (correo, número, WhatsApp).

---

## Solución

### FIX 457: Detectar cuando cliente ofrece dato y NO aplicar FIX 311b

**Lógica:** Antes de aplicar FIX 311b, verificar si el cliente está ofreciendo
dar un dato. Si es así, permitir que GPT responda naturalmente aceptando el dato.

### Archivo Modificado

**agente_ventas.py (líneas 3075-3101)**

```python
# FIX 457: BRUCE1370 - NO pedir número si cliente OFRECE dar un correo/número/whatsapp
cliente_ofrece_dato = any(frase in contexto_cliente for frase in [
    'le doy un correo', 'le doy el correo', 'le paso el correo',
    'le doy un numero', 'le doy el numero', 'le paso el numero',
    'si quiere le doy', 'si gusta le doy', 'si desea le doy',
    'le puedo dar un correo', 'le puedo dar el correo',
    'anote el correo', 'tome nota', 'le comparto'
])

if cliente_ofrece_dato:
    print(f"✅ FIX 457: Cliente OFRECE dato - NO aplicar FIX 311b")
    # Bruce usará respuesta de GPT que acepta el dato
elif cliente_dice_no_esta and bruce_ofrece_catalogo and not bruce_ya_pidio_numero:
    # FIX 311b: Forzar pedir número (solo si cliente NO ofrece dato)
    respuesta = "Entiendo. ¿Me podría proporcionar el número directo del encargado?"
```

---

## Tests

**Archivo:** `test_fix_457.py`

Resultados: 3/3 tests pasados (100%)
- Detectar ofrecimiento: OK
- Caso BRUCE1370: OK
- FIX 311b sin ofrecimiento: OK

---

## Comportamiento Esperado

### Antes (sin FIX 457):
1. Cliente: "No se encuentra. Si quiere le doy un correo electrónico."
2. GPT responde: "Perfecto, ¿le gustaría recibir nuestro catálogo por correo?"
3. FIX 311b cambia: "¿Me podría proporcionar el número del encargado?"
4. Bruce pide NÚMERO cuando cliente ofreció CORREO

### Después (con FIX 457):
1. Cliente: "No se encuentra. Si quiere le doy un correo electrónico."
2. GPT responde: "Perfecto, ¿le gustaría recibir nuestro catálogo por correo?"
3. FIX 457 detecta "le doy un correo" → NO aplica FIX 311b
4. Bruce acepta el correo que el cliente ofreció

---

## Impacto Esperado

1. **Bruce acepta datos ofrecidos:** Cuando cliente ofrece correo/número, Bruce lo acepta
2. **FIX 311b sigue funcionando:** Cuando NO hay ofrecimiento, Bruce pide número primero
3. **Conversaciones más naturales:** Bruce no ignora lo que el cliente ofrece

---

## Archivos Modificados

1. `agente_ventas.py` - FIX 457 (detección de ofrecimiento de datos)
2. `test_fix_457.py` - Tests de validación (creado)
3. `RESUMEN_FIX_457.md` - Este documento (creado)
