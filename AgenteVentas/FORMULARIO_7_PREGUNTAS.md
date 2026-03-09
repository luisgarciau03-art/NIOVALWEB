# 📋 Formulario de 7 Preguntas - Integración con Bruce W

**Objetivo:** Bruce W debe hacer estas 7 preguntas de forma SUTIL e INDIRECTA durante la conversación natural, NO como un cuestionario.

---

## 🎯 Principio Fundamental

❌ **NO hacer como cuestionario:**
```
Bruce: "Pregunta 1: ¿Qué requiere de un proveedor?"
Bruce: "Pregunta 2: ¿Toma decisiones de compra?"
```

✅ **Hacer de forma natural y conversacional:**
```
Bruce: "Platíqueme, ¿qué es lo más importante para ustedes al momento de
       elegir un proveedor? ¿La rapidez en entregas, precios competitivos,
       o tal vez líneas de crédito?"
```

---

## 📝 Las 7 Preguntas

### PREGUNTA 0: Estado de Llamada (Automático)
**No se pregunta - El sistema lo detecta automáticamente**

**Opciones:**
- `Respondio` - La llamada fue contestada
- `Buzon` - Entró a buzón de voz
- `Telefono Incorrecto` - Número equivocado/fuera de servicio
- `Colgo` - Cliente colgó durante la conversación

**Captura:** Automática según el resultado de la llamada

---

### PREGUNTA 1: Necesidades del Cliente (Opciones Múltiples)
**Pregunta original del formulario:**
> "¿Algo que requiera tener un proveedor para poderle comprar?"

**Opciones (puede seleccionar varias):**
1. 🚚 **Entregas Rápidas**
2. 💳 **Líneas de Crédito**
3. 📦 **Contra Entrega**
4. 🎁 **Envío Gratis**
5. 💰 **Precio Preferente**
6. ⭐ **Evaluar Calidad**

**Cómo Bruce debe preguntar (SUTIL):**

**Opción A - Después de presentar NIOVAL:**
```
"Platíqueme, ¿qué es lo que más valoran al momento de trabajar con un
proveedor? Por ejemplo, algunos clientes nos buscan por las entregas
rápidas, otros porque ofrecemos líneas de crédito o envíos gratis.
¿Qué sería lo más importante para ustedes?"
```

**Opción B - Si menciona que ya tiene proveedores:**
```
"Perfecto. Y de los proveedores actuales que tiene, ¿qué es lo que
más le gusta de ellos? ¿Las entregas son rápidas, manejan crédito,
o es más por el tema de precios?"
```

**Opción C - Si pregunta sobre condiciones:**
```
"Con gusto le platico nuestras condiciones. ¿Qué le interesa más:
entregas rápidas, crédito, pago contra entrega, o precios competitivos?"
```

**Captura:**
- Si menciona **entregas** → "Entregas Rápidas"
- Si menciona **crédito** → "Líneas de Crédito"
- Si menciona **pago contra entrega / COD** → "Contra Entrega"
- Si menciona **envío gratis / sin costo de envío** → "Envío Gratis"
- Si menciona **precio / costo / económico** → "Precio Preferente"
- Si menciona **calidad / probar / muestra** → "Evaluar Calidad"

**Formato de guardado:** Separado por comas: "Entregas Rápidas, Precio Preferente"

---

### PREGUNTA 2: Toma de Decisiones
**Pregunta original del formulario:**
> "¿Toma usted las decisiones de compra?"

**Opciones:**
- ✅ **Sí**
- ❌ **No**

**Cómo Bruce debe preguntar (SUTIL):**

**Opción A - Si se identifica como dueño:**
```
(Bruce NO pregunta - Asume "Sí" automáticamente)
```

**Opción B - Si no está seguro del rol:**
```
"Perfecto. Y para agilizar el proceso, ¿usted es quien autoriza las
compras o debo hablar con alguien más del equipo?"
```

**Opción C - Si ya está hablando con encargado de compras:**
```
"Excelente. ¿Y usted tiene autorización para hacer pedidos directamente
o necesita consultar con el dueño?"
```

**Captura:**
- Si dice que SÍ toma decisiones → "Sí"
- Si dice que NO / tiene que consultar → "No"
- Si es dueño/encargado de compras → "Sí" (automático)

---

### PREGUNTA 3: Pedido Inicial
**Pregunta original del formulario:**
> "Le podemos ayudar con el pedido inicial, manejando el monto que usted diga,
> también contemplando algunos ítems del mismo precio y similar para probar
> qué tal se venden en su punto de venta?"

**Contexto que Bruce debe mencionar ANTES:**
- ✓ Es Producto Potencial para su zona por el ticket
- ✓ Su punto de venta cumple con el perfil
- ✓ No contamos con distribuidor en su zona
- SKU destacado: 5958 (TOP DE VENTA Y BUEN PRECIO)

**Opciones:**
- ✅ **Crear Pedido Inicial Sugerido**
- ❌ **No**

**Cómo Bruce debe preguntar (SUTIL):**

**Opción A - Después de mostrar interés:**
```
"Me da gusto que le interese. Mire, tengo un producto estrella, el SKU 5958,
que es top de venta y tiene muy buen precio. Según lo que veo de su zona,
es un producto muy potencial para ustedes y además aún no tenemos distribuidor
ahí. ¿Le gustaría que le armara un pedido inicial con este y algunos productos
similares para que pruebe cómo se venden en su punto de venta?"
```

**Opción B - Si pregunta cómo empezar:**
```
"Para arrancar, le puedo armar un pedido inicial sugerido con productos que
sabemos que funcionan bien en zonas como la suya. Incluso tenemos un SKU
estrella, el 5958, que es de nuestros tops de venta. ¿Le parece que le prepare
una propuesta con ese y otros productos del mismo rango de precio?"
```

**Captura:**
- Si acepta que le armen un pedido → "Crear Pedido Inicial Sugerido"
- Si dice que no / prefiere ver catálogo → "No"

---

### PREGUNTA 4: Pedido de Muestra
**Pregunta original del formulario:**
> "Pedido Muestra"

**Contexto que Bruce debe mencionar ANTES:**
- Pedido de Muestra de **$1,500**
- ✓ Nosotros cubriríamos el envío
- ✓ Le podemos hacer una sugerencia o recomendación

**Opciones:**
- ✅ **Sí**
- ❌ **No**

**Cómo Bruce debe preguntar (SUTIL):**

**Opción A - Si dice "No" a pedido inicial o muestra duda:**
```
"Sin problema. Si prefiere empezar probando, podemos hacer un pedido de
muestra de solo $1,500 pesos con envío gratis incluido. Así puede probar
la mercancía sin invertir mucho. Le puedo hacer una recomendación de
productos según lo que me platicó. ¿Le parece?"
```

**Opción B - Si menciona "no quiero gastar mucho":**
```
"Perfecto, lo entiendo. Por eso mismo tenemos la opción del pedido de muestra.
Son solo $1,500 pesos, nosotros cubrimos el envío, y le enviamos una selección
de productos que creemos que le van a funcionar. ¿Le gustaría empezar así?"
```

**Opción C - Si ya mostró interés pero quiere ver primero:**
```
"Excelente. Y si gusta, podemos arrancar con un pedido chiquito de muestra,
$1,500 con envío gratis, para que conozca la calidad de nuestros productos.
¿Le interesa?"
```

**Captura:**
- Si acepta pedido de muestra → "Sí"
- Si rechaza / prefiere esperar → "No"

---

### PREGUNTA 5: Compromiso de Fecha
**Pregunta original del formulario:**
> "¿Podemos iniciar esta semana?"

**Contexto:** Pactar Fecha

**Opciones:**
- ✅ **Sí**
- ❌ **No**
- 🤔 **Tal vez**

**Cómo Bruce debe preguntar (SUTIL):**

**Opción A - Después de aceptar pedido:**
```
"Perfecto, entonces le preparo el pedido. ¿Le parece bien que lo procesemos
esta misma semana para que le llegue pronto?"
```

**Opción B - Si mostró interés fuerte:**
```
"Excelente. ¿Qué le parece si arrancamos esta semana? Así le llega su pedido
a más tardar la próxima semana."
```

**Opción C - Si dice "después veo":**
```
"Entiendo. Nada más para ir avanzando, ¿cree que podríamos cerrar algo esta
semana o prefiere que le hable la próxima?"
```

**Captura:**
- Si confirma esta semana → "Sí"
- Si dice que no puede esta semana → "No"
- Si dice "tal vez" / "lo veo" / "no estoy seguro" → "Tal vez"

---

### PREGUNTA 6: Método de Pago TDC
**Pregunta original del formulario:**
> "¿Le parece si podemos cerrar el pedido con envío gratis y nosotros le
> realizamos un mapeo de un top de venta en su zona?"

**Contexto que Bruce debe mencionar ANTES:**
- Métodos de pago con **TDC** (Tarjeta de Crédito)
- Financiamiento aprox de **30/50 días** dependiendo de su tarjeta
- ✓ La comisión nosotros la cubrimos **100%**

**Opciones:**
- ✅ **Sí**
- ❌ **No**
- 🤔 **Tal vez**

**Cómo Bruce debe preguntar (SUTIL):**

**Opción A - Después de confirmar pedido:**
```
"Perfecto. Y mire, una ventaja que tenemos es que aceptamos pago con tarjeta
de crédito sin comisión para usted. La comisión la cubrimos nosotros al 100%.
Eso le da un financiamiento de 30 a 50 días según su tarjeta. ¿Le parece si
cerramos el pedido con envío gratis y además le preparo un mapeo de los
productos top de venta en su zona?"
```

**Opción B - Si menciona flujo de efectivo:**
```
"Perfecto, entiendo. Por eso aceptamos tarjeta de crédito, sin comisión para
usted. Así tiene 30 o 50 días para pagar dependiendo de su tarjeta, mientras
ya está vendiendo el producto. ¿Le sirve esa opción?"
```

**Captura:**
- Si acepta TDC / cierre con mapeo → "Sí"
- Si rechaza / prefiere otro método → "No"
- Si dice "lo veo" / "tal vez" → "Tal vez"

---

### PREGUNTA 7: Conclusión (Siguiente Paso)
**Pregunta original del formulario:**
> "¿Cuál es el siguiente paso con este contacto?"

**Opciones:**
1. 📦 **Pedido** - Cliente va a hacer un pedido
2. 📋 **Revisara el Catalogo** - Cliente va a revisar el catálogo
3. 📧 **Correo** - Cliente prefiere recibir información por correo
4. 📅 **Avance (Fecha Pactada)** - Se pactó una fecha específica de seguimiento
5. ⏳ **Continuacion (Cliente Esperando Alguna Situacion)** - Cliente está esperando algo (presupuesto, consultar con alguien, etc.)
6. ❌ **Nulo** - No hay seguimiento / Cliente no interesado
7. 📞 **Colgo** - Cliente colgó durante la conversación

**Cómo Bruce debe determinarlo (AUTOMÁTICO - NO PREGUNTA):**

Esta pregunta NO se hace explícitamente. Bruce determina la conclusión según cómo terminó la conversación:

**Mapeo automático:**

- Si cliente **aceptó hacer pedido** (Pregunta 3, 4, 5 o 6 = Sí) → `"Pedido"`

- Si cliente dijo **"voy a revisar el catálogo"** → `"Revisara el Catalogo"`

- Si cliente pidió **información por correo** → `"Correo"`

- Si se pactó **fecha específica** de seguimiento (Pregunta 5 con fecha) → `"Avance (Fecha Pactada)"`

- Si cliente dijo **"lo consulto"** / **"lo veo"** / **"después te confirmo"** → `"Continuacion (Cliente Esperando Alguna Situacion)"`

- Si cliente **rechazó todo** o **no está interesado** → `"Nulo"`

- Si cliente **colgó durante la conversación** → `"Colgo"`

**Captura:** Automática según el flujo de la conversación

---

## 🔄 Flujo de las Preguntas

### Flujo Normal (Cliente Interesado):

```
PREGUNTA 0: [Automático] → Respondio

PREGUNTA 1: (Durante presentación inicial)
Bruce: "¿Qué es lo más importante para ustedes: entregas rápidas,
        crédito, o precios competitivos?"
Cliente: "Pues principalmente el precio y entregas rápidas"
→ Captura: "Precio Preferente, Entregas Rápidas"

PREGUNTA 2: (Si no está claro su rol)
Bruce: "¿Usted es quien autoriza las compras?"
Cliente: "Sí, yo soy el dueño"
→ Captura: "Sí"

PREGUNTA 3: (Después de mostrar interés)
Bruce: "Tengo un producto estrella, el SKU 5958, muy solicitado en
        su zona. ¿Le armo un pedido inicial con ese y productos
        similares para que pruebe?"
Cliente: "Sí, pero no muy grande"
→ Captura: "Crear Pedido Inicial Sugerido"

PREGUNTA 4: (Como alternativa o refuerzo)
Bruce: "Perfecto. Podemos empezar con un pedido de muestra de $1,500
        con envío gratis. ¿Le parece?"
Cliente: "Sí, eso suena bien"
→ Captura: "Sí"

PREGUNTA 5: (Pactar fecha)
Bruce: "¿Le parece que lo procesemos esta semana?"
Cliente: "Sí, esta semana está bien"
→ Captura: "Sí"

PREGUNTA 6: (Ofrecer TDC)
Bruce: "Aceptamos tarjeta de crédito sin comisión, le da 30-50 días
        para pagar. ¿Le parece si cerramos con envío gratis y un
        mapeo de productos top de su zona?"
Cliente: "Sí, perfecto"
→ Captura: "Sí"

PREGUNTA 7: [Automático basado en flujo]
→ Captura: "Pedido"
```

### Flujo Alternativo (Cliente con Dudas):

```
PREGUNTA 1: "Precio Preferente, Evaluar Calidad"
PREGUNTA 2: "Sí"
PREGUNTA 3: "No" (prefiere ver primero)
PREGUNTA 4: "Tal vez" (no está seguro)
PREGUNTA 5: "No" (no puede esta semana)
PREGUNTA 6: "Tal vez"
PREGUNTA 7: "Revisara el Catalogo"
```

### Flujo Rechazo (Cliente No Interesado):

```
PREGUNTA 1: (No responde claramente / "no necesito nada")
PREGUNTA 2: "Sí"
PREGUNTA 3: "No"
PREGUNTA 4: "No"
PREGUNTA 5: "No"
PREGUNTA 6: "No"
PREGUNTA 7: "Nulo"
```

---

## 📊 Guardado en Spreadsheet

Las respuestas se guardan en el spreadsheet de resultados:

**URL:** https://docs.google.com/spreadsheets/d/1U_z1KNqCxSRZVi7wvO2FQH4zIdS_wxuafxj6YHdHEqg/edit
**Hoja:** "Respuestas de formulario 1"

**Mapeo de columnas:**
- **Columna A:** Fecha/Hora
- **Columna B:** TIENDA (nombre del negocio)
- **Columna C:** Pregunta 1 (opciones separadas por coma)
- **Columna D:** Pregunta 2 (Sí/No)
- **Columna E:** Pregunta 3 (Crear Pedido/No)
- **Columna G:** Pregunta 4 (Sí/No)
- **Columna H:** Pregunta 5 (Sí/No/Tal vez)
- **Columna I:** Pregunta 6 (Sí/No/Tal vez)
- **Columna J:** Pregunta 7 o Prioridad
- **Columna S:** Resultado (APROBADO/NEGADO)
- **Columna T:** Estado de llamada (Respondio/Buzon/etc.)

---

## 🎯 Reglas Importantes para Bruce

### ✅ SIEMPRE:
1. Hacer las preguntas de forma **NATURAL y CONVERSACIONAL**
2. **NO** decir "Pregunta 1", "Pregunta 2", etc.
3. Adaptar el lenguaje según la respuesta del cliente
4. Si el cliente ya dio la información, **NO volver a preguntar**
5. Dejar que las respuestas surjan naturalmente en la conversación

### ❌ NUNCA:
1. Hacer las 7 preguntas en secuencia como cuestionario
2. Forzar todas las preguntas si el cliente no está interesado
3. Preguntar algo que el cliente ya respondió
4. Usar lenguaje robotizado o de formulario

### 🔄 Flujo Adaptativo:
- Si cliente dice **NO** en Pregunta 3 → Ofrecer Pregunta 4 (Muestra)
- Si cliente dice **NO** en Pregunta 4 → NO insistir con más preguntas de pedido
- Si cliente **cuelga** en cualquier momento → Marcar "Colgo" y terminar
- Si cliente **muestra interés** → Avanzar con todas las preguntas sutilmente

---

## 📝 Ejemplo de Conversación Completa

```
[PREGUNTA 0: Automático - Respondio]

Bruce: "Hola, buenas tardes. Soy Bruce W de NIOVAL, distribuidores de
       productos ferreteros. ¿Me comunico con el encargado de compras?"
Cliente: "Sí, soy yo"

Bruce: "Perfecto. El motivo de mi llamada es presentarle nuestros productos.
       Platíqueme, ¿qué es lo que más valoran al elegir un proveedor?"
[PREGUNTA 1]
Cliente: "Pues principalmente buenos precios y que las entregas sean rápidas"
→ Captura: "Precio Preferente, Entregas Rápidas"

Bruce: "Entiendo perfectamente. Y para agilizar, ¿usted es quien autoriza
       las compras o consulta con alguien más?"
[PREGUNTA 2]
Cliente: "No, yo soy el dueño, yo autorizo"
→ Captura: "Sí"

Bruce: "Excelente. Mire, tenemos un producto estrella, el SKU 5958, que es
       top de venta con muy buen precio. En su zona veo que tiene potencial
       y aún no tenemos distribuidor. ¿Le gustaría que le armara un pedido
       inicial con ese producto y otros similares para que pruebe qué tal
       se venden?"
[PREGUNTA 3]
Cliente: "Mmm... suena bien pero no quiero algo muy grande todavía"
→ Captura: "Crear Pedido Inicial Sugerido"

Bruce: "Perfecto, sin problema. Podemos iniciar con un pedido de muestra de
       solo $1,500 pesos, nosotros cubrimos el envío. Así prueba la mercancía
       sin invertir mucho. ¿Le parece?"
[PREGUNTA 4]
Cliente: "Ah ok, eso sí suena bien"
→ Captura: "Sí"

Bruce: "Excelente. ¿Le parece si lo procesamos esta semana para que le llegue
       pronto?"
[PREGUNTA 5]
Cliente: "Sí, esta semana está bien"
→ Captura: "Sí"

Bruce: "Perfecto. Y una ventaja es que aceptamos tarjeta de crédito sin
       comisión, la cubrimos nosotros. Eso le da 30 o 50 días para pagar.
       ¿Le parece si cerramos con envío gratis y le preparo un mapeo de
       productos top de su zona?"
[PREGUNTA 6]
Cliente: "Sí, perfecto"
→ Captura: "Sí"

Bruce: "Excelente. Nada más necesito su WhatsApp para enviarle la confirmación
       del pedido y el catálogo completo..."

[PREGUNTA 7: Automático - "Pedido"]
```

---

**Siguiente paso:** Integrar estas preguntas en el SYSTEM_PROMPT de Bruce W
