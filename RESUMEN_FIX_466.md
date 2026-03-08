# RESUMEN FIX 466: Permitir Presentacion Cuando Cliente Pregunta De Donde Llaman

## Caso Resuelto

| ID | Error Reportado | Causa Raiz | FIX |
|----|-----------------|------------|-----|
| BRUCE1405 | No comprende pregunta de donde hablaba, colgo | FIX 228 detecto repeticion y cambio a "Si, digame" | FIX 466 |

---

## Problema

### Escenario BRUCE1405:
```
Cliente: "Buenas tardes. ¿De donde me habla la esposa?"
Bruce: (Ya se habia presentado antes)
GPT genero: "Me comunico de la marca nioval, queria ofrecer informacion..."
FIX 228/236/240: Patron detectado - 'me\s+comunico\s+de\s+(la\s+)?marca\s+nioval'
                 Respuesta corregida: "Si, digame."  <- INCORRECTO
Cliente: "¿Mande? No le escuche bien. ¿De donde me dijo que me hablaba?"
```

### Causa Raiz
FIX 228/236/240 detecta cuando Bruce repite su presentacion ("me comunico de la marca nioval")
y lo cambia a "Si, digame" para evitar repeticiones.

PERO cuando el cliente pregunta "¿De donde me habla?", la presentacion ES la respuesta correcta.
El cliente QUIERE saber de donde llaman.

---

## Solucion

### FIX 466: Detectar preguntas sobre origen de llamada

**Logica:** Antes de aplicar el filtro de repeticion, verificar si el cliente
esta preguntando DE DONDE llaman. En ese caso, la presentacion es la respuesta correcta.

**Codigo (agente_ventas.py lineas 2230-2249):**
```python
# FIX 466: BRUCE1405 - NO filtrar si cliente pregunta DE DONDE LLAMAN
cliente_pregunta_origen = any(frase in ultimo_cliente_para_466 for frase in [
    'de dónde', 'de donde', 'quién habla', 'quien habla',
    'quién llama', 'quien llama', 'quién es', 'quien es',
    'de qué empresa', 'de que empresa', 'de qué compañía', 'de que compania',
    'de parte de quién', 'de parte de quien', 'con quién hablo', 'con quien hablo'
])

if cliente_pregunta_origen:
    print(f"FIX 466: Cliente pregunta DE DONDE LLAMAN - presentacion ES la respuesta correcta")
    break  # Salir del for sin aplicar filtro
```

---

## Tests

**Archivo:** `test_fix_466.py`

Resultados: 4/4 tests pasados (100%)
- Caso BRUCE1405: OK
- Preguntas sobre origen: OK (9 variantes)
- Preguntas NO origen: OK (7 casos sin falsos positivos)
- Simulacion filtro: OK

---

## Comportamiento Esperado

### Antes (sin FIX 466):
1. Cliente: "¿De donde me habla?"
2. GPT: "Me comunico de la marca nioval..."
3. FIX 228: Detecta repeticion -> cambia a "Si, digame"
4. Bruce: "Si, digame." (INCORRECTO - no responde la pregunta)
5. Cliente confundido, cuelga

### Despues (con FIX 466):
1. Cliente: "¿De donde me habla?"
2. GPT: "Me comunico de la marca nioval..."
3. FIX 228: Detecta patron de repeticion
4. **FIX 466: Detecta pregunta de origen -> NO aplicar filtro**
5. Bruce: "Me comunico de la marca nioval..." (CORRECTO)
6. Cliente obtiene la informacion solicitada

---

## Impacto Esperado

1. **Respuestas correctas:** Bruce se presenta cuando le preguntan de donde llama
2. **Menos llamadas perdidas:** Cliente no cuelga por confusion
3. **Filtro sigue funcionando:** Repeticiones NO solicitadas SI se filtran

---

## Frases Detectadas Como Pregunta de Origen

| Frase | Ejemplo |
|-------|---------|
| de donde | "¿De donde me habla?" |
| quien habla | "¿Quien habla?" |
| quien llama | "¿Quien llama?" |
| quien es | "¿Quien es?" |
| de que empresa | "¿De que empresa llama?" |
| de que compania | "¿De que compania es?" |
| de parte de quien | "¿De parte de quien?" |
| con quien hablo | "¿Con quien hablo?" |

---

## Archivos Modificados

1. `agente_ventas.py` - FIX 466 (lineas 2230-2249)
2. `test_fix_466.py` - Tests de validacion (creado)
3. `RESUMEN_FIX_466.md` - Este documento (creado)
