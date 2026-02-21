# FSM Determinista Bruce W - Plan de Fases

## Problema
Despues de 750+ fixes, Bruce mantiene ~80% tasa de bugs (4/5 llamadas). La causa raiz es arquitectural: GPT-4o recibe un system prompt masivo con 750+ reglas y genera respuestas libres que 10+ post-filters intentan corregir. Cada fix tapa UN caso pero GPT genera casos nuevos (whack-a-mole).

## Solucion
Separar DECISION (determinista, FSM) de GENERACION (GPT solo como redactor). La FSM decide QUE hacer, GPT solo genera texto natural cuando se necesita.

## Archivos FSM
| Archivo | Proposito |
|---------|-----------|
| `fsm_engine.py` | Motor FSM: 12 estados, 80+ transiciones, intent classifier, guards |
| `response_templates.py` | 35 templates espanol mexicano + 6 narrow prompts GPT |
| `tests/test_fsm_engine.py` | 81 tests unitarios (transiciones, intents, guards) |
| `tests/test_fsm_integration.py` | 31 tests end-to-end (flujos conversacionales) |
| `agente_ventas.py` | +15 lineas: interceptor FSM en `procesar_respuesta()` (~linea 9014) |

## Feature Flag
```
FSM_ENABLED = os.getenv("FSM_ENABLED", "shadow")
```
- `"shadow"`: Loguea decisiones `[FSM SHADOW]` sin interceptar (comparar vs GPT)
- `"active"`: FSM intercepta, GPT como fallback si FSM retorna None
- `"false"`: FSM deshabilitado completamente

Cambiar en Railway: Variables de entorno > `FSM_ENABLED` > valor deseado

## 12 Estados FSM
```
SALUDO                  -> Llamada inicia, esperando respuesta
PITCH                   -> Bruce da pitch de productos NIOVAL
BUSCANDO_ENCARGADO      -> Pregunto por encargado de compras
ENCARGADO_PRESENTE      -> Encargado confirmado en linea
ENCARGADO_AUSENTE       -> Encargado no disponible
ESPERANDO_TRANSFERENCIA -> Cliente transfiriendo llamada
CAPTURANDO_CONTACTO     -> Pidiendo WhatsApp/correo/telefono
DICTANDO_DATO           -> Cliente dictando numero/email (NO interrumpir)
OFRECIENDO_CONTACTO     -> Bruce ofrece dejar SU numero
CONTACTO_CAPTURADO      -> Dato capturado exitosamente
DESPEDIDA               -> Cerrando conversacion
CONVERSACION_LIBRE      -> Caso complejo -> GPT narrow fallback
```

## 4 Tipos de Accion
1. **TEMPLATE** (0ms, $0): Respuesta hardcoded del banco de templates
2. **GPT_NARROW** (~500ms, ~$0.001): GPT con prompt de 2-3 lineas, single-purpose
3. **ACKNOWLEDGE** (0ms, $0): "Aja, si." o "Aja, si. Digame."
4. **HANGUP/NOOP** (0ms, $0): Senal para colgar o no hacer nada

## 6 Narrow Prompts GPT
| Prompt | Cuando | max_tokens |
|--------|--------|------------|
| responder_pregunta_producto | Cliente pregunta sobre productos/precios | 80 |
| generar_despedida | Despedida personalizada | 40 |
| manejar_objecion | Cliente tiene duda/objecion | 80 |
| confirmar_dato_dictado | Confirmar dato capturado | 60 |
| conversacion_libre | FSM no puede manejar | 100 |
| personalizar_template | Variacion menor de template | 80 |

---

## FASES DE IMPLEMENTACION

### FASE 1: Infraestructura + Shadow Mode - COMPLETADA
- **Commit**: `733fbbe` (2026-02-20)
- **Que se hizo**:
  - Creado `fsm_engine.py` con FSMEngine completo
  - Creado `response_templates.py` con 35 templates + 6 prompts
  - Integrado en `agente_ventas.py` (interceptor + init)
  - 112 tests nuevos (81 unitarios + 31 integracion)
  - Suite total: 1770 tests pasando
- **Estado**: FSM loguea `[FSM SHADOW]` en Railway pero NO intercepta
- **Siguiente paso**: Desplegar a Railway, hacer 5-10 llamadas, revisar logs shadow

### FASE 2: Estados Deterministas - PENDIENTE
- **Que hacer**:
  - Cambiar `FSM_ENABLED=active` en Railway
  - Activar FSM SOLO para estados 100% deterministas:
    - `SALUDO` -> siempre da pitch
    - `DESPEDIDA` -> siempre despedida cortes
    - `DICTANDO_DATO` -> siempre acknowledge o confirmar
    - `ESPERANDO_TRANSFERENCIA` -> siempre "Claro, espero" o re-pitch
  - Los demas estados siguen usando GPT existente (FSM retorna None)
- **Como implementar**:
  - Agregar flag `FSM_ACTIVE_STATES` en fsm_engine.py
  - Solo interceptar si `self.state in FSM_ACTIVE_STATES`
  - Si estado no esta en lista, retornar None (fallthrough a GPT)
- **Entregable**: ~30% de turnos manejados por FSM, 0ms latencia en esos turnos
- **Validacion**: 10-20 llamadas, verificar que turnos FSM son correctos

### FASE 3: Core Flow - PENDIENTE
- **Que hacer**:
  - Agregar a `FSM_ACTIVE_STATES`:
    - `BUSCANDO_ENCARGADO` -> pregunta/responde sobre encargado
    - `ENCARGADO_AUSENTE` -> pide contacto alternativo
    - `CAPTURANDO_CONTACTO` -> pide WhatsApp/correo/telefono
    - `ENCARGADO_PRESENTE` -> da pitch al encargado
  - Cubre el happy path completo (35-40% de llamadas)
- **Entregable**: ~60% de turnos manejados por FSM
- **Validacion**: 20-30 llamadas, comparar tasa de bugs vs baseline

### FASE 4: Full FSM - PENDIENTE
- **Que hacer**:
  - Activar TODOS los estados
  - `OFRECIENDO_CONTACTO` -> ofrece numero de Bruce
  - `CONTACTO_CAPTURADO` -> confirma y despide
  - `CONVERSACION_LIBRE` -> GPT narrow (NO GPT full)
  - GPT solo se usa via narrow prompts (max 100 tokens, prompt de 2-3 lineas)
- **Entregable**: ~80%+ de turnos manejados por FSM, ~20% GPT narrow
- **Impacto esperado**:
  - Latencia: 0ms (template) vs 3500ms (GPT actual)
  - Costo: ~$0.004/llamada vs ~$0.02 actual (-80%)
  - Bugs "GPT repite pregunta": ~0% vs 69% actual
  - Bugs "ignora rechazo": ~0% vs ~15% actual

---

## INTEGRACION EN agente_ventas.py

Punto de insercion: `procesar_respuesta()` linea ~9014

```python
# === FSM Engine como primer respondedor ===
if hasattr(self, 'fsm') and self.fsm:
    try:
        fsm_result = self.fsm.process(respuesta_cliente, self)
        if fsm_result is not None:
            self.conversation_history.append({
                "role": "assistant",
                "content": fsm_result
            })
            self.turno_actual += 1
            return fsm_result
    except Exception as e:
        print(f"  [FSM ERROR] {e} - fallthrough a logica existente")
# === Si FSM no maneja, continua logica existente ===
```

Init en `__init__()` linea ~504:
```python
self.fsm = None
try:
    from fsm_engine import FSMEngine, FSM_ENABLED
    if FSM_ENABLED != "false":
        self.fsm = FSMEngine()
        print(f"  [FSM] Inicializado en modo: {FSM_ENABLED}")
except ImportError:
    pass
```

## ROLLBACK
Si algo falla en produccion:
1. Railway > Variables > `FSM_ENABLED` = `false`
2. Re-deploy (o esperar auto-deploy)
3. FSM se desactiva completamente, Bruce vuelve a GPT puro

## NOTAS TECNICAS
- FSM NO modifica: servidor_llamadas.py, intent_classifier.py, memory_layer.py, speech_processor.py
- FSM es aditiva: si retorna None, la logica existente maneja todo
- El intent classifier de FSM es independiente del intent_classifier.py existente
- Los templates NO tienen acentos (compatibilidad FIX 631 normalizacion)
- `classify_intent()` normaliza texto: lowercase, sin acentos, sin puntuacion
- Guards permiten condiciones como "!whatsapp_rechazado" o "pitch_dado"
