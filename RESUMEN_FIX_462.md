# RESUMEN FIX 462: Capturar WhatsApp Cuando Cliente Confirma Numero

## Caso Resuelto

| ID | Error Reportado | Causa Raiz | FIX |
|----|-----------------|------------|-----|
| BRUCE1396 | No detecto numero de WhatsApp + Volvio a preguntar | Cliente confirmo numero pero no se guardo | FIX 462 |

---

## Problema

### Escenario BRUCE1396:
```
Bruce: "Perfecto, lo tengo anotado como 221-442-61-55, es correcto?"
Cliente: "Es correcto."
FIX 295/300: "Bruce dice 'ya lo tengo' pero NO tiene contacto"
Bruce: "Disculpe, me podria proporcionar su numero de WhatsApp?" <- INCORRECTO
```

### Logs del problema:
```
ASSISTANT: Perfecto, lo tengo anotado como 221-442-61-55, es correcto?
USER: Es correcto. Es correcto. Es correcto.

FIX 295/300: FILTRO ACTIVADO - Bruce dice 'ya lo tengo' pero NO tiene contacto
   WhatsApp capturado:
   Bruce iba a decir: "Perfecto, le enviare el catalogo a ese WhatsApp..."
   Respuesta corregida: "Disculpe, me podria proporcionar su numero de WhatsApp?"
```

### Causa Raiz
Cuando Bruce repite un numero para confirmar y el cliente dice "Es correcto":
1. El numero estaba en el historial de Bruce
2. Pero NUNCA se guardo en `lead_data.whatsapp`
3. FIX 295/300 detectaba que GPT queria decir "le enviare el catalogo" pero no habia WhatsApp
4. Entonces forzaba a preguntar el numero de nuevo

---

## Solucion

### FIX 462: Capturar numero del historial cuando cliente confirma

**Logica:**
1. Detectar cuando cliente dice "es correcto", "si", "exacto", etc.
2. Buscar en el historial el ultimo mensaje de Bruce con un numero
3. Extraer el numero y guardarlo como WhatsApp
4. Esto se ejecuta ANTES de FIX 295/300

**Codigo (agente_ventas.py lineas 2833-2877):**
```python
# FIX 462: BRUCE1396 - Capturar numero cuando cliente CONFIRMA
if not filtro_aplicado and not self.lead_data.get("whatsapp"):
    cliente_confirma_numero = any(frase in ultimo_cliente for frase in [
        'es correcto', 'correcto', 'si es', 'asi es', 'eso es',
        'exacto', 'ese es', 'andale', 'aja', 'ok', 'okey'
    ])

    if cliente_confirma_numero:
        for msg in reversed(self.conversation_history[-6:]):
            if msg['role'] == 'assistant':
                patron_numero = re.search(
                    r'(?:anotado como|tengo como|registrado como|es el|numero es)?\s*(\d[\d\s\-\.]+\d)',
                    msg['content'], re.IGNORECASE
                )
                if patron_numero:
                    digitos = re.sub(r'[^\d]', '', patron_numero.group(1))
                    if len(digitos) >= 9 and len(digitos) <= 12:
                        numero_whatsapp = f"+52{digitos}"
                        self.lead_data["whatsapp"] = numero_whatsapp
                        self.lead_data["whatsapp_valido"] = True
                        break
```

---

## Tests

**Archivo:** `test_fix_462.py`

Resultados: 4/4 tests pasados (100%)
- Caso BRUCE1396: OK
- Diferentes formatos numero: OK
- No falsos positivos: OK
- Confirmaciones cliente: OK

---

## Comportamiento Esperado

### Antes (sin FIX 462):
1. Bruce: "lo tengo anotado como 221-442-61-55, es correcto?"
2. Cliente: "Es correcto"
3. FIX 295/300: WhatsApp vacio -> forzar pregunta
4. Bruce: "Disculpe, me podria proporcionar su numero de WhatsApp?"

### Despues (con FIX 462):
1. Bruce: "lo tengo anotado como 221-442-61-55, es correcto?"
2. Cliente: "Es correcto"
3. **FIX 462: Detecta confirmacion -> extrae 221-442-61-55 del historial**
4. **WhatsApp guardado: +522214426155**
5. FIX 295/300: WhatsApp existe -> NO forzar pregunta
6. Bruce: "Perfecto, le enviare el catalogo a ese WhatsApp"

---

## Impacto Esperado

1. **Sin preguntas duplicadas:** Bruce NO vuelve a pedir el WhatsApp cuando ya lo confirmo
2. **Captura correcta:** Numeros confirmados se guardan automaticamente
3. **Mejor experiencia:** Cliente no tiene que repetir el numero

---

## Archivos Modificados

1. `agente_ventas.py` - FIX 462 (lineas 2833-2877)
2. `test_fix_462.py` - Tests de validacion (creado)
3. `RESUMEN_FIX_462.md` - Este documento (creado)
