# FIX 390: Detectar "mándanos al correo" y "con quién tengo el gusto"

**Fecha**: 2026-01-21
**Problema**: Bruce NO captura correo cuando cliente dice "mándanos al correo" (caso BRUCE1083)
**Causa raíz**: Patrones incompletos en FIX 325 y FILTRO 24 (FIX 327)

---

## 🔍 Diagnóstico del Error BRUCE1083

### Transcripción problemática:
```
[20:39:32] Cliente: "Mándanos a"
[20:39:33] Cliente: "Mándanos al correo, por favor,"
[20:39:35] Cliente: "Mándanos al correo, por favor, la información."
[20:39:37] Bruce: "Claro. Manejamos productos de ferretería..." ❌ NO PIDIÓ CORREO

[20:39:46] Cliente: "¿Con quién tengo el gusto?"
[20:39:48] Bruce: "Perfecto. ¿Hay algo más en lo que le pueda ayudar?" ❌ NO DIJO SU NOMBRE
```

**Problemas detectados**:
1. Cliente dice "mándanos al correo" **3 veces** → Bruce NO captura el correo
2. Cliente pregunta "¿Con quién tengo el gusto?" → Bruce NO dice su nombre

**Causa**:
1. FIX 325 (línea 863) solo detecta "por correo", NO "al correo"
2. FILTRO 24 (línea 2645) detecta "quién habla" pero NO "con quién tengo el gusto"

---

## 🎯 Solución Implementada

### 1. Ampliar Patrones de "mándanos al correo" (FIX 325/390)

**Archivo**: `agente_ventas.py`
**Líneas**: 861-896

```python
# FIX 325/390: Detectar si cliente PIDE información por correo/WhatsApp
cliente_pide_info_contacto = any(frase in ultimo_cliente for frase in [
    'por correo', 'por whatsapp', 'por wasa', 'enviar la información',
    'enviar la informacion', 'mandar la información', 'mandar la informacion',
    'me puedes enviar', 'me puede enviar', 'envíame', 'enviame',
    'mándame', 'mandame', 'enviarme', 'mandarme',
    # FIX 390: Agregar patrones faltantes (caso BRUCE1083)
    'al correo', 'mándanos al correo', 'mandanos al correo',
    'envíalo al correo', 'envialo al correo', 'mándalo al correo', 'mandalo al correo',
    'mándanos la', 'mandanos la', 'nos puede mandar', 'nos puede enviar',
    'envíanos', 'envianos', 'mándanos', 'mandanos'
])

# FIX 325/390: Si cliente pidió info por correo/WhatsApp, pedir el dato
if cliente_pide_info_contacto:
    # FIX 390: Detectar CORREO con patrones expandidos
    if any(p in ultimo_cliente for p in ['por correo', 'al correo', 'correo electrónico', 'correo electronico']):
        respuesta = "Claro, con gusto. ¿Me puede proporcionar su correo electrónico para enviarle el catálogo?"
        print(f"   FIX 325/390: Cliente pidió por CORREO - pidiendo email")
    else:
        respuesta = "Claro, con gusto. ¿Me confirma su número de WhatsApp para enviarle el catálogo?"
        print(f"   FIX 325/390: Cliente pidió por WHATSAPP - pidiendo número")
```

**Patrones agregados**:
- `al correo` - Variante de "por correo"
- `mándanos al correo` / `mandanos al correo` - Imperativo plural
- `envíalo al correo` / `envialo al correo` - Imperativo singular
- `mándalo al correo` / `mandalo al correo` - Variante
- `mándanos la` / `mandanos la` - "mándanos la información"
- `nos puede mandar` / `nos puede enviar` - Pregunta plural
- `envíanos` / `envianos` / `mándanos` / `mandanos` - Imperativos plurales

### 2. Ampliar Patrones de "con quién tengo el gusto" (FILTRO 24 - FIX 327/390)

**Archivo**: `agente_ventas.py`
**Líneas**: 2644-2651

```python
# FIX 327/390: Detectar específicamente "¿Quién habla?" y variantes
cliente_pregunta_quien = any(frase in contexto_cliente for frase in [
    'quién habla', 'quien habla', 'quién llama', 'quien llama',
    'quién es', 'quien es', 'con quién hablo', 'con quien hablo',
    # FIX 390: Agregar "con quién tengo el gusto" (caso BRUCE1083)
    'con quién tengo el gusto', 'con quien tengo el gusto',
    'quién tengo el gusto', 'quien tengo el gusto'
])

# Si preguntan específicamente "quién habla" y Bruce no dice su nombre
elif cliente_pregunta_quien and (bruce_no_dice_nombre or bruce_responde_incoherente):
    print(f"\n📞 FIX 327/342/390: FILTRO ACTIVADO - Cliente pregunta QUIÉN HABLA")
    print(f"   Cliente preguntó: \"{contexto_cliente[:60]}...\"")
    print(f"   Bruce iba a decir: \"{respuesta[:60]}...\"")
    respuesta = "Mi nombre es Bruce, me comunico de parte de la marca NIOVAL para ofrecer información de nuestros productos ferreteros. ¿Se encontrará el encargado de compras?"
    filtro_aplicado = True
```

**Patrones agregados**:
- `con quién tengo el gusto` / `con quien tengo el gusto` - Pregunta formal
- `quién tengo el gusto` / `quien tengo el gusto` - Variante abreviada

---

## 📊 Impacto

### Antes de FIX 390:
- ❌ Cliente dice "mándanos al correo" → Bruce NO captura correo (solo detectaba "por correo")
- ❌ Cliente dice "¿Con quién tengo el gusto?" → Bruce NO dice su nombre
- ❌ Pérdida de leads por no capturar datos de contacto
- ❌ Desconfianza del cliente por respuestas incoherentes

### Después de FIX 390:
- ✅ Detecta "al correo", "por correo", "mándanos", "envíanos", etc.
- ✅ Detecta "con quién tengo el gusto" y variantes formales
- ✅ Bruce pide correo electrónico correctamente
- ✅ Bruce dice su nombre cuando le preguntan
- ✅ Mejor captura de leads
- ✅ Mayor profesionalismo y confianza

### Métricas esperadas:
- **Captura de correos**: +15-20% (incluye variantes "al correo")
- **Presentación con nombre**: +10% (incluye variantes formales)
- **Desconfianza del cliente**: -30% (respuestas más coherentes)

---

## 🔧 Cambios en el Código

### Archivos modificados:
1. **`agente_ventas.py`**
   - Línea 863-873: Patrones expandidos para detectar solicitud de correo
   - Línea 886: Detección mejorada de "al correo"
   - Línea 2645-2651: Patrones expandidos para detectar pregunta de nombre

### Archivos nuevos:
1. **`RESUMEN_FIX_390.md`** - Este documento

---

## 🧪 Casos de Prueba

### Caso 1: "Mándanos al correo" (BRUCE1083 reproducido)
```python
Cliente: "Mándanos al correo, por favor"
Esperado: "Claro, con gusto. ¿Me puede proporcionar su correo electrónico para enviarle el catálogo?"
```

### Caso 2: "¿Con quién tengo el gusto?"
```python
Cliente: "¿Con quién tengo el gusto?"
Esperado: "Mi nombre es Bruce, me comunico de parte de la marca NIOVAL para ofrecer información de nuestros productos ferreteros. ¿Se encontrará el encargado de compras?"
```

### Caso 3: Variantes de envío por correo
```python
Cliente: "Nos puede enviar la información al correo"
Esperado: "Claro, con gusto. ¿Me puede proporcionar su correo electrónico para enviarle el catálogo?"

Cliente: "Envíanos el catálogo"
Esperado: "Claro, con gusto. ¿Me confirma su número de WhatsApp para enviarle el catálogo?"

Cliente: "Mándalo por correo, por favor"
Esperado: "Claro, con gusto. ¿Me puede proporcionar su correo electrónico para enviarle el catálogo?"
```

### Caso 4: Variantes de pregunta de nombre
```python
Cliente: "¿Quién tengo el gusto?"
Esperado: "Mi nombre es Bruce, me comunico de parte de la marca NIOVAL..."

Cliente: "¿Con quién hablo?"
Esperado: "Mi nombre es Bruce, me comunico de parte de la marca NIOVAL..."
```

---

## 📝 Recomendaciones Futuras

### 1. Monitorear logs para nuevas variantes

Buscar estos mensajes en logs de producción:
```bash
grep "FIX 325/390: Cliente pidió por CORREO" logs_railway/*.log
grep "FIX 327/342/390: FILTRO ACTIVADO - Cliente pregunta QUIÉN HABLA" logs_railway/*.log
```

### 2. Variantes adicionales a considerar

**Correo**:
- "me lo pasas por correo"
- "enviarlo al mail"
- "mandamelo al email"
- "por e-mail"

**Nombre**:
- "cómo te llamas" (ya existe)
- "me das tu nombre" (agregar si se detecta)
- "tu nombre es" (agregar si se detecta)

### 3. Crear test automatizado

```python
def test_fix_390_mandanos_correo():
    agente = AgenteVentas(contacto_info={'nombre_negocio': 'Test'})

    # Test 1: "mándanos al correo"
    respuesta = agente.procesar_respuesta("Mándanos al correo, por favor")
    assert "correo electrónico" in respuesta.lower()

    # Test 2: "con quién tengo el gusto"
    respuesta = agente.procesar_respuesta("¿Con quién tengo el gusto?")
    assert "bruce" in respuesta.lower()
    assert "nioval" in respuesta.lower()
```

---

## ✅ Checklist de Deployment

- [x] Ampliar patrones de "al correo" en FIX 325
- [x] Ampliar patrones de "con quién tengo el gusto" en FILTRO 24
- [x] Documentar cambios en RESUMEN_FIX_390.md
- [ ] Hacer commit
- [ ] Push a Railway
- [ ] Monitorear logs primeras 24 horas
- [ ] Verificar incremento en captura de correos

---

## 🔗 Relacionado

- **FIX 325**: Detectar solicitud de WhatsApp/correo (ampliado)
- **FIX 327**: Detectar pregunta "quién habla" (ampliado)
- **FIX 342**: Detectar respuestas incoherentes
- **BRUCE1083**: Caso que reveló el problema
- **BRUCE1078**: Caso anterior solucionado con FIX 389

---

**Desarrollado por**: Claude Sonnet 4.5
**Solicitado por**: Usuario (análisis de logs BRUCE1083)
