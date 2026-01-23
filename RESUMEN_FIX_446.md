# RESUMEN FIX 446: Auditoria y Ampliacion de Frases de Deteccion

## Objetivo
Ampliar las listas de deteccion de frases para mejorar la precision en la identificacion de:
1. Encargado disponible / "Yo soy"
2. Encargado no disponible
3. Preferencia de contacto (WhatsApp/correo)

---

## Cambios Implementados

### 1. patrones_encargado_disponible (lineas 386-425)

**Archivo:** `agente_ventas.py`

Ampliada con variantes adicionales:

```python
patrones_encargado_disponible = [
    # Ofreciendo ayuda (existentes)
    '¿en qué le puedo apoyar', '¿en qué le apoyo', etc.

    # FIX 446: Nuevas variantes de ofrecimiento
    '¿qué se le ofrece', '¿qué desea', '¿qué busca',
    'para servirle', 'a sus órdenes', 'a la orden',
    'dígame', 'mande usted', 'servidor', 'servidora', 'presente',

    # FIX 446: Más variantes de "soy yo"
    'yo mero', 'aquí mero', 'acá mero',
    'sí soy', 'sí soy yo',
    'yo soy la dueña', 'yo soy el dueño',
    'yo soy quien', 'yo me encargo', 'yo hago las compras',
    'conmigo', 'con un servidor', 'con una servidora',

    # FIX 446: Confirmando que SÍ está el encargado
    'sí está', 'sí se encuentra',
    'aquí está', 'aquí se encuentra',
    'sí lo tenemos', 'sí la tenemos',
    'ya llegó', 'acaba de llegar', 'ya está aquí'
]
```

### 2. patrones_soy_yo (lineas 563-588)

**Archivo:** `agente_ventas.py`

Ampliada significativamente:

```python
patrones_soy_yo = [
    # Básicos
    'soy yo', 'yo soy', 'sí soy yo', 'sí soy',

    # Encargado/encargada
    'yo soy el encargado', 'soy el encargado',
    'yo soy la encargada', 'soy la encargada',

    # Dueño/dueña
    'yo soy el dueño', 'soy el dueño',
    'yo soy la dueña', 'soy la dueña',

    # Mexicanismos
    'yo mero', 'aquí mero', 'acá mero', 'mero mero',

    # Variantes de "conmigo"
    'conmigo', 'con un servidor', 'con una servidora',
    'a sus órdenes', 'para servirle',

    # Variantes de rol
    'yo me encargo', 'yo hago las compras', 'yo veo eso',
    'yo manejo', 'yo decido', 'yo atiendo', 'yo recibo',

    # "Con él/ella habla"
    'con ella habla', 'con él habla',
    'ella habla', 'él habla',

    # Respuestas afirmativas
    'sí, yo soy', 'sí yo soy',
    'sí, con él', 'sí, con ella'
]
```

### 3. cliente_prefiere_correo (lineas 3108-3123)

**Archivo:** `agente_ventas.py`

Ampliada con variantes adicionales:

```python
cliente_prefiere_correo = [
    # Básicos (existentes)
    'por correo', 'correo electrónico', 'el correo', 'mi correo', 'email',

    # FIX 446: Variantes adicionales
    'al correo', 'a mi correo', 'a su correo',
    'mándalo al correo', 'envíalo al correo',
    'mándamelo al correo', 'mande al correo', 'envíe al correo',
    'por mail', 'al mail', 'mi mail', 'el mail',
    'prefiero correo', 'mejor por correo', 'por correo mejor',
    'mándelo por correo', 'envíelo por correo',
    'le doy el correo', 'le paso el correo',
    'anota el correo', 'apunta el correo'
]
```

### 4. cliente_prefiere_whatsapp (lineas 3125-3143)

**Archivo:** `agente_ventas.py`

Ampliada con variantes adicionales:

```python
cliente_prefiere_whatsapp = [
    # Básicos (existentes)
    'por whatsapp', 'por wasa', 'whatsapp', 'wasa',
    'mi whats', 'mejor whatsapp',

    # FIX 446: Variantes adicionales
    'al whatsapp', 'a mi whatsapp', 'a su whatsapp',
    'mándalo al whatsapp', 'envíalo al whatsapp',
    'mándamelo al whatsapp', 'mande al whatsapp', 'envíe al whatsapp',
    'por whats', 'al whats', 'mi whats', 'el whats',
    'prefiero whatsapp', 'mejor por whatsapp', 'por whatsapp mejor',
    'mándelo por whatsapp', 'envíelo por whatsapp',
    'le doy el whatsapp', 'le paso el whatsapp',
    'anota el whatsapp', 'apunta el whatsapp',
    'manda al wasa', 'envía al wasa',
    'por wasap', 'al wasap', 'por guasa', 'al guasa'
]
```

### 5. respuesta_negativa (expandida en sesion anterior)

Lista de "No está el encargado" ya ampliada con:
- Variantes de ausencia
- Variantes temporales
- Variantes de horario/día
- Ofertas de alternativas

---

## Tests

**Archivo:** `test_fix_446.py`

Resultados: 4/4 tests pasados (100%)
- Encargado disponible: OK
- Soy yo: OK
- Preferencia contacto: OK
- No está encargado: OK

---

## Impacto Esperado

1. **Mejor detección de encargado disponible:** Bruce identificará más variantes de "sí está" o "yo soy"
2. **Respuestas más precisas:** Al detectar preferencia de contacto, Bruce pedirá el dato correcto
3. **Menos errores de contexto:** Detección mejorada reduce respuestas incoherentes

---

## Archivos Modificados

1. `agente_ventas.py` - FIX 446 (4 listas ampliadas)
2. `test_fix_446.py` - Tests de validación (creado)
3. `RESUMEN_FIX_446.md` - Este documento (creado)
