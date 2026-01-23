# RESUMEN FIX 464: Responder Correctamente a Preguntas Sobre Productos

## Caso Resuelto

| ID | Error Reportado | Causa Raiz | FIX |
|----|-----------------|------------|-----|
| BRUCE1390 | No comprendio "Que es lo que vende?" | FIX 444 cambio respuesta de GPT a "Si, digame" | FIX 464 |

---

## Problema

### Escenario BRUCE1390:
```
Cliente: "Es en 3 pesos. Que mercancia vende, disculpa?"
GPT genero: "Manejamos productos de ferreteria como griferias, cintas y herramientas..."
FIX 444: Cliente hace PREGUNTA - no decir 'adelante con el dato'
Respuesta corregida: "Si, digame."  <- INCORRECTO
```

### Causa Raiz
FIX 444 detecta cualquier pregunta con `?` y cambia la respuesta a "Si, digame".
Pero esto es incorrecto cuando el cliente pregunta especificamente que productos vende.

GPT habia generado la respuesta correcta explicando los productos, pero FIX 444
la cambio a "Si, digame" porque detecto un signo de interrogacion.

---

## Solucion

### FIX 464: Detectar preguntas sobre productos

**Logica:** Antes de cambiar a "Si, digame", verificar si el cliente esta
preguntando que vende/que productos tiene. En ese caso, dejar la respuesta de GPT.

**Codigo (agente_ventas.py lineas 2425-2442):**
```python
# FIX 464: BRUCE1390 - Detectar si cliente pregunta QUE VENDE
cliente_pregunta_que_vende = any(frase in ultimo_cliente_lower for frase in [
    'que vende', 'que mercancia', 'que productos', 'que manejan',
    'que es lo que vende', 'a que se dedica', 'de que se trata', 'que ofrece'
])

if cliente_pregunta_que_vende:
    # FIX 464: NO cambiar la respuesta de GPT - dejar que explique los productos
    print(f"   FIX 464: Cliente pregunta QUE VENDE - dejando respuesta de GPT")
    filtro_aplicado = False  # Cancelar el filtro
    break
```

---

## Tests

**Archivo:** `test_fix_464.py`

Resultados: 3/3 tests pasados (100%)
- Caso BRUCE1390: OK
- Preguntas sobre productos: OK
- Preguntas genericas: OK

---

## Comportamiento Esperado

### Antes (sin FIX 464):
1. Cliente: "Que mercancia vende?"
2. GPT: "Manejamos productos de ferreteria como griferias..."
3. FIX 444: Detecta `?` -> cambia a "Si, digame"
4. Bruce: "Si, digame." (INCORRECTO)

### Despues (con FIX 464):
1. Cliente: "Que mercancia vende?"
2. GPT: "Manejamos productos de ferreteria como griferias..."
3. FIX 464: Detecta "que mercancia" -> NO cambiar respuesta
4. Bruce: "Manejamos productos de ferreteria..." (CORRECTO)

---

## Impacto Esperado

1. **Respuestas correctas:** Bruce explica productos cuando el cliente pregunta
2. **FIX 444 sigue funcionando:** Preguntas genericas SI cambian a "Si, digame"
3. **Mejor experiencia:** Clientes obtienen informacion que solicitan

---

## Archivos Modificados

1. `agente_ventas.py` - FIX 464 (lineas 2425-2442)
2. `test_fix_464.py` - Tests de validacion (creado)
3. `RESUMEN_FIX_464.md` - Este documento (creado)
