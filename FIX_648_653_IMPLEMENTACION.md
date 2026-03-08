# Implementación FIX 648-653: 12 Bugs Post FIX 646/647

## Cambios a Realizar

### FIX 648: CLIENTE_HABLA_ULTIMO (2 bugs - CRÍTICO)

**Archivo:** `agente_ventas.py` línea ~8020

**Agregar después de despedidas:**
```python
# FIX 648: BRUCE2112, BRUCE2111 - CLIENTE_HABLA_ULTIMO
# Cliente da cierre natural pero Bruce NO responde → ghostea al cliente
patrones_cierre_natural = [
    "no hay ahorita", "no hay en esta hora", "no hay nadie",
    "tienes que hablar a", "tiene que llamar a", "contacta a",  # OTRA_SUCURSAL
    "habla a la sucursal", "marca a la sucursal",
    "no hay encargado", "no tenemos encargado",
    "solo soy yo", "yo nada mas", "yo solo", "estoy solo", "estoy sola"
]

if any(p in texto_lower for p in patrones_cierre_natural):
    if "otra sucursal" in texto_lower or "habla a" in texto_lower or "tiene que llamar" in texto_lower:
        return {
            "tipo": "DESPEDIDA_NATURAL_CLIENTE_DERIVACION",
            "respuesta": "Perfecto, voy a contactar a esa sucursal entonces. Muchas gracias por su ayuda, que tenga excelente día.",
            "accion": "TERMINAR_LLAMADA"
        }
    return {
        "tipo": "DESPEDIDA_NATURAL_CLIENTE_NO_DISPONIBLE",
        "respuesta": "Perfecto, entonces le marco más tarde cuando esté disponible. Muchas gracias, que tenga buen día.",
        "accion": "TERMINAR_LLAMADA"
    }
```

**Agregar a inmunidad FIX 600/601:**
- patrones_inmunes_pero: agregar 'DESPEDIDA_NATURAL_CLIENTE_DERIVACION', 'DESPEDIDA_NATURAL_CLIENTE_NO_DISPONIBLE'
- patrones_inmunes_601: agregar 'DESPEDIDA_NATURAL_CLIENTE_DERIVACION', 'DESPEDIDA_NATURAL_CLIENTE_NO_DISPONIBLE'

---

### FIX 649: GPT_LOGICA_ROTA Indirecto (3 bugs - ALTO)

**Archivo:** `agente_ventas.py` línea ~9527

**Mejorar regla #2 de FIX 646A:**
```python
2. Si el cliente ya proporcionó un dato (DIRECTA o INDIRECTAMENTE):
   - Directo: "Mi WhatsApp es 3312345678", "El correo es juan@gmail.com"
   - Indirecto: "Llame al 3312345678", "Puede marcar al...", "El número es...",
                "Contacte al...", "Marquen a...", "Te paso el..."
   NO volver a pedirlo. El dato YA está capturado.
   → Agradecer y continuar con el siguiente paso.
```

---

### FIX 650: GPT_FUERA_DE_TEMA (4 bugs - MEDIO)

**Archivo:** `agente_ventas.py` línea ~2100 (post-filter)

**Agregar validación post-GPT:**
```python
# FIX 650: BRUCE2112, BRUCE2106, BRUCE2100, BRUCE2094 - GPT_FUERA_DE_TEMA
# Bruce pregunta por encargado SIN dar pitch de productos primero
if self.turnos_bruce == 1:  # Primer turno de Bruce (después del saludo)
    if ("encargado" in respuesta_lower or "encargada" in respuesta_lower) and \
       not any(p in respuesta_lower for p in ["productos", "ferreteros", "distribuidor", "nioval", "marca"]):
        # Agregar pitch mínimo antes de preguntar por encargado
        pitch_minimo = "Le comento, me comunico de NIOVAL, somos distribuidores de productos ferreteros. "
        respuesta = pitch_minimo + respuesta
        print(f"   FIX 650: Agregado pitch mínimo en turno 1 antes de preguntar por encargado")
```

---

### FIX 651: GPT_TONO_INADECUADO (2 bugs - MEDIO)

**Archivo:** `servidor_llamadas.py` línea ~3600 (timeout GPT handler)

**Mejorar mensaje de timeout:**
```python
# FIX 651: BRUCE2097, BRUCE2096 - GPT_TONO_INADECUADO
# Timeout GPT → mensaje profesional en lugar de "problemas técnicos"
if timeout_gpt:
    mensaje_profesional = "Disculpe, tengo problemas con la conexión en este momento. ¿Le puedo enviar el catálogo por WhatsApp y lo contacto más tarde para darle mejor información?"
    # Registrar como "problemas técnicos" para bug detector
    agente.call_events.append({
        'timestamp': datetime.now().isoformat(),
        'type': 'TIMEOUT_GPT',
        'details': 'Timeout GPT - mensaje profesional enviado'
    })
    return mensaje_profesional
```

---

### FIX 652: GPT_OPORTUNIDAD_PERDIDA (1 bug - MEDIO)

**Archivo:** `agente_ventas.py` línea ~9527 (agregar a reglas)

**Agregar regla #5:**
```python
5. Si el cliente indica que el encargado NO ESTÁ o NO PUEDE atender,
   SIEMPRE pedir un contacto alternativo (WhatsApp, correo, teléfono directo).
   NO simplemente decir "lo llamo después" y colgar.
   → "¿Me podría dar su WhatsApp para enviarle el catálogo?"
```

---

### FIX 653: GPT_RESPUESTA_INCORRECTA (1 bug - BAJO)

**Archivo:** `agente_ventas.py` línea ~2150 (post-filter)

**Validar formato marca:**
```python
# FIX 653: BRUCE2093 - GPT_RESPUESTA_INCORRECTA
# "nioval" debe ser siempre "NIOVAL" (mayúsculas)
if "nioval" in respuesta_lower:
    # Reemplazar todas las variantes por NIOVAL mayúsculas
    respuesta = re.sub(r'\bnioval\b', 'NIOVAL', respuesta, flags=re.IGNORECASE)
    print(f"   FIX 653: Normalizado 'nioval' → 'NIOVAL'")
```

---

## Tests a Crear

**Archivo:** `tests/test_fix_648_653.py`

- test_fix_648_no_hay_ahorita_cierre
- test_fix_648_otra_sucursal_derivacion
- test_fix_649_llame_al_numero_indirecto
- test_fix_649_puede_marcar_al
- test_fix_650_pitch_minimo_turno_1
- test_fix_651_timeout_mensaje_profesional
- test_fix_652_pedir_contacto_alternativo
- test_fix_653_nioval_mayusculas

Total: 8 tests

---

## Impacto Esperado

| Fix | Bugs Eliminados | % Reducción |
|-----|-----------------|-------------|
| FIX 648 | 2 | 17% |
| FIX 649 | 3 | 25% |
| FIX 650 | 4 | 33% |
| FIX 651 | 2 | 17% |
| FIX 652 | 1 | 8% |
| FIX 653 | 1 | 8% |
| **TOTAL** | **12** | **100%** |

---

## Orden de Implementación

1. FIX 648 (CRÍTICO) - Pattern detector
2. FIX 649 (ALTO) - System prompt
3. FIX 650 (MEDIO) - Post-filter
4. FIX 651 (MEDIO) - Servidor timeout
5. FIX 652 (MEDIO) - System prompt regla #5
6. FIX 653 (BAJO) - Post-filter
7. Tests comprehensivos
8. Commit único + push

---

**Tiempo estimado:** 45-60 minutos
**Archivos modificados:** 2 (agente_ventas.py, servidor_llamadas.py)
**Tests nuevos:** 1 archivo, 8 tests
**Suite completo:** 156 + 8 = 164 tests
