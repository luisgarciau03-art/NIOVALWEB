# Plan Maestro de Correccion de Bugs - Auditoria Profunda 2026-03-05

## Resumen de Auditoria
- Llamadas auditadas: 653 (historial completo)
- Evaluador: Claude Sonnet 4.6 ultra-agresivo (8 dimensiones)
- Score promedio: ~2.0/10
- Bugs detectados: 24 tipos distintos en 110 llamadas (16.8%)
- Bugs reportados al sistema /bugs: 149

---

## INVENTARIO COMPLETO DE BUGS

### GRUPO A: BUGS ARQUITECTONICOS (requieren cambios en FSM/templates)

#### BUG-01: FLUJO_ROBOTICO (117 llamadas, 17.9%)
- **Severidad**: CRITICO
- **Sintoma**: Bruce SIEMPRE sigue saludo -> pitch generico 15 categorias -> pedir WhatsApp. No adapta flujo.
- **Causa raiz**:
  - FSM tiene transiciones deterministas: SALUDO->PITCH->BUSCANDO_ENCARGADO->CAPTURANDO_CONTACTO
  - Templates de pitch son HARDCODED con lista fija de categorias
  - No hay bifurcaciones segun tipo de negocio o respuesta del cliente
  - response_templates.py: solo 1 variante por template
- **Archivos**: fsm_engine.py (lineas 1170-1352), response_templates.py (lineas 16-67)
- **Solucion propuesta**:
  - Crear multiples variantes de pitch (3-5 por template)
  - Agregar seleccion aleatoria de template
  - Agregar pregunta diagnostica antes del pitch ("Que tipo de negocio manejan?")
  - Personalizar categorias segun nombre del negocio (ferreteria vs taller vs papeleria)

#### BUG-02: FALTA_EMPATIA (101 llamadas, 15.5%)
- **Severidad**: CRITICO
- **Sintoma**: Bruce no reconoce emociones/situacion del cliente. "Entiendo" generico sin reflejo.
- **Causa raiz**:
  - Templates usan "Entiendo" como comodin sin especificar QUE entiende
  - Analisis de sentimiento ocurre DESPUES de responder (demasiado tarde)
  - Narrow prompts no instruyen sobre QUE es empatia
  - No hay deteccion de frustacion/confusion antes de responder
- **Archivos**: response_templates.py (lineas 88-100), agente_ventas.py (linea 11137)
- **Solucion propuesta**:
  - Crear templates con reflejo especifico ("Entiendo que esta ocupado, le marco en otro momento")
  - Mover deteccion de sentimiento ANTES de seleccion de template
  - Agregar variantes empaticas para cada situacion comun

#### BUG-03: TIMING_INCORRECTO (82 llamadas, 12.6%)
- **Severidad**: CRITICO
- **Sintoma**: Bruce pide WhatsApp INMEDIATAMENTE despues de pitch, sin verificar interes real.
- **Causa raiz**:
  - FSM transiciona: PITCH + INTEREST -> CAPTURANDO_CONTACTO (linea 1233)
  - INTEREST es cualquier senal positiva debil ("si", "ok", "claro")
  - No verifica si cliente ENTIENDE la oferta antes de pedir contacto
  - ENCARGADO_PRESENTE + CONFIRMATION -> pedir_whatsapp sin dar pitch primero
- **Archivos**: fsm_engine.py (lineas 1233, 1248-1249)
- **Solucion propuesta**:
  - Agregar estado intermedio: PITCH -> GENERANDO_INTERES -> CAPTURANDO_CONTACTO
  - No pedir contacto hasta que haya al menos 1 senal de interes especifico
  - Verificar que se dio el pitch ANTES de pedir contacto

#### BUG-04: DATO_IGNORADO (69 llamadas, 10.6%)
- **Severidad**: ALTO
- **Sintoma**: Cliente da info (nombre, tipo negocio, "ya nos conocemos") y Bruce la ignora.
- **Causa raiz**:
  - FSMContext.datos_capturados existe PERO NUNCA se llena
  - No hay extraccion de datos mencionados por el cliente
  - Templates no tienen placeholders para datos del cliente
  - lead_data se inicializa de Google Sheets, no se actualiza con datos mencionados
- **Archivos**: fsm_engine.py (linea 280, 1700-1797), agente_ventas.py (lineas 671-707)
- **Solucion propuesta**:
  - Llenar datos_capturados cuando cliente menciona datos
  - Crear funcion _extraer_datos_del_texto() que corra cada turno
  - Verificar datos existentes antes de pedir

#### BUG-05: ESCUCHA_ACTIVA (50 llamadas, 7.7%)
- **Severidad**: ALTO
- **Sintoma**: Bruce responde con templates genericos sin referenciar lo que el cliente dijo.
- **Causa raiz**:
  - Templates son estaticos sin placeholders ({nombre}, {producto_mencionado})
  - Pattern detector retorna respuesta sin enriquecimiento contextual
  - Prompt dinamico menciona lo que cliente dijo pero no instruye reflejo
- **Archivos**: response_templates.py (lineas 16-264), agente_ventas.py (linea 10791)
- **Solucion propuesta**:
  - Agregar instrucciones explicitas de reflejo en narrow prompts
  - Crear mecanismo de "context injection" en templates
  - Instruir GPT a mencionar palabras clave del cliente

### GRUPO B: BUGS DE RESPUESTA (requieren cambios en templates/prompts)

#### BUG-06: RESPUESTA_SUBOPTIMA (89 llamadas, 13.6%)
- **Severidad**: ALTO
- **Sintoma**: Bruce responde "correcto" pero habia una respuesta MEJOR.
- **Causa raiz**: Templates son respuestas minimas, no optimizadas para conversion
- **Solucion**: Reescribir templates con enfoque vendedor estrella

#### BUG-07: RESPUESTA_IDEAL (93 llamadas, 14.2%)
- **Severidad**: MEDIO
- **Sintoma**: Cada turno de Bruce podria ser mejor. Claude sugiere alternativas.
- **Causa raiz**: Templates genericos sin adaptacion
- **Solucion**: Crear multiples variantes y mejorar narrow prompts

#### BUG-08: SENTIMIENTO_NEGATIVO (68 llamadas, 10.4%)
- **Severidad**: ALTO
- **Sintoma**: Cliente se frustra durante la llamada y Bruce no lo detecta.
- **Causa raiz**: No hay deteccion de progresion de sentimiento
- **Solucion**: Agregar deteccion de frustracion pre-respuesta

#### BUG-09: RESPUESTA_FILLER_INCOHERENTE (56 llamadas, 8.6%)
- **Severidad**: ALTO
- **Sintoma**: Bruce responde con frases desconectadas ("Claro, digame" cuando no aplica).
- **Causa raiz**: BTE engine usa fillers genericos como fallback
- **Solucion**: Mejorar fillers contextuales en BTE

#### BUG-10: OPORTUNIDAD_PERDIDA (92 llamadas, 14.1%)
- **Severidad**: ALTO
- **Sintoma**: Cliente muestra interes pero Bruce no lo capitaliza.
- **Causa raiz**: FSM no detecta senales sutiles de interes
- **Solucion**: Expandir patrones de INTEREST en classify_intent

### GRUPO C: BUGS DE FLUJO (requieren ajustes en FSM)

#### BUG-11: REDUNDANCIA (28 llamadas, 4.3%)
- **Severidad**: MEDIO
- **Sintoma**: Bruce repite informacion/conceptos ya dichos.
- **Solucion**: Verificar historial antes de repetir template

#### BUG-12: PREGUNTA_REPETIDA (25 Claude + 10 rule-based = 35 total)
- **Severidad**: ALTO
- **Sintoma**: Bruce repite la misma pregunta 2+ veces.
- **Causa raiz**: STT garbled -> UNKNOWN -> FIX 791 asigna mismo template ya dicho
- **Solucion**: En FIX 791, verificar si template ya se dijo

#### BUG-13: MANEJO_OBJECIONES (25 llamadas, 3.8%)
- **Severidad**: MEDIO
- **Sintoma**: Bruce acepta "no" sin ofrecer alternativas.
- **Solucion**: Mejorar narrow prompt de manejar_objecion

#### BUG-14: CAPTURA_DATOS (25 llamadas, 3.8%)
- **Severidad**: ALTO
- **Sintoma**: Bruce no pide datos o los pide mal.
- **Solucion**: Verificar datos faltantes antes de despedirse

#### BUG-15: DESPEDIDA_PREMATURA (23 llamadas, 3.5%)
- **Severidad**: CRITICO
- **Sintoma**: Bruce se despide cuando cliente aun habla o sin capturar datos.
- **Causa raiz**: FSM transiciona a despedida demasiado rapido
- **Solucion**: Agregar guard de "minimo datos capturados" antes de despedida

#### BUG-16: CIERRE (21 llamadas, 3.2%)
- **Severidad**: MEDIO
- **Sintoma**: Despedida generica sin recapitular lo acordado.
- **Solucion**: Template de cierre que confirme siguiente paso

#### BUG-17: LOOP (15 llamadas, 2.3%)
- **Severidad**: ALTO
- **Sintoma**: Bruce entra en ciclo de 3+ turnos repitiendo mismo patron.
- **Solucion**: Contador de repeticiones + escalamiento automatico

#### BUG-18: INTERRUPCION_CONVERSACIONAL (11 llamadas, 1.7%)
- **Severidad**: ALTO
- **Sintoma**: Bruce corta al cliente a mitad de explicacion.
- **Causa raiz**: STT entrega texto parcial, FSM responde inmediatamente
- **Solucion**: Intrinseco a timing STT, mitigacion con detector de interrupciones

#### BUG-19: ADAPTABILIDAD (11 llamadas, 1.7%)
- **Severidad**: MEDIO
- **Sintoma**: Bruce formal con cliente informal o viceversa.
- **Solucion**: Detectar tono del cliente y adaptar

#### BUG-20: PITCH_REPETIDO (3 llamadas, 0.5%)
- **Severidad**: MEDIO
- **Sintoma**: Bruce repite el pitch de productos 2+ veces.
- **Solucion**: Flag pitch_dado en FSM (ya existe parcialmente)

---

## PLAN DE CORRECCION POR FASES

### FASE 1: Quick Wins (alto impacto, baja complejidad)
**Tiempo estimado: 1 sesion**

| FIX | Bug | Que hacer | Impacto |
|-----|-----|-----------|---------|
| FIX 907 | PREGUNTA_REPETIDA (#12) | En FIX 791 UNKNOWN->template: verificar si template ya se dijo, si si -> escalar | 35 llamadas |
| FIX 908 | DESPEDIDA_PREMATURA (#15) | Guard: no despedir si no hay datos capturados ni minimo 3 turnos | 23 llamadas |
| FIX 909 | REDUNDANCIA (#11) | Verificar en historial si concepto ya se dijo antes de repetir | 28 llamadas |
| FIX 910 | LOOP (#17) | Contador de templates repetidos, escalar despues de 2x | 15 llamadas |

### FASE 2: Templates y Prompts (impacto medio, complejidad media)
**Tiempo estimado: 1-2 sesiones**

| FIX | Bug | Que hacer | Impacto |
|-----|-----|-----------|---------|
| FIX 911 | FALTA_EMPATIA (#2) | Crear variantes empaticas de templates + reflejo especifico | 101 llamadas |
| FIX 912 | RESPUESTA_FILLER (#9) | Mejorar fillers BTE con contexto conversacional | 56 llamadas |
| FIX 913 | MANEJO_OBJECIONES (#13) | Mejorar narrow prompt con tecnicas de reencuadre | 25 llamadas |
| FIX 914 | CIERRE (#16) | Template de cierre que recapitule accion siguiente | 21 llamadas |
| FIX 915 | ESCUCHA_ACTIVA (#5) | Instrucciones de reflejo en narrow prompts + GPT | 50 llamadas |

### FASE 3: FSM y Flujo (alto impacto, alta complejidad)
**Tiempo estimado: 2-3 sesiones**

| FIX | Bug | Que hacer | Impacto |
|-----|-----|-----------|---------|
| FIX 916 | TIMING_INCORRECTO (#3) | Estado intermedio entre PITCH y CAPTURANDO_CONTACTO | 82 llamadas |
| FIX 917 | FLUJO_ROBOTICO (#1) | Multiples variantes de pitch + seleccion aleatoria | 117 llamadas |
| FIX 918 | DATO_IGNORADO (#4) | Llenar datos_capturados cada turno + verificar antes de pedir | 69 llamadas |
| FIX 919 | OPORTUNIDAD_PERDIDA (#10) | Expandir INTEREST patterns para senales sutiles | 92 llamadas |
| FIX 920 | SENTIMIENTO_NEGATIVO (#8) | Deteccion de frustracion pre-respuesta | 68 llamadas |

### FASE 4: Optimizacion (bajo impacto, complejidad variable)
**Tiempo estimado: 1 sesion**

| FIX | Bug | Que hacer | Impacto |
|-----|-----|-----------|---------|
| FIX 921 | RESPUESTA_SUBOPTIMA (#6) | Reescribir templates con enfoque vendedor estrella | 89 llamadas |
| FIX 922 | RESPUESTA_IDEAL (#7) | Multiples variantes por template | 93 llamadas |
| FIX 923 | ADAPTABILIDAD (#19) | Detectar tono informal/formal del cliente | 11 llamadas |
| FIX 924 | CAPTURA_DATOS (#14) | Verificar datos faltantes antes de despedir | 25 llamadas |

---

## FASE 5: TESTEO (validacion)

1. Replay de las 653 llamadas con FSM actualizado (rule-based, 30s)
2. Claude Sonnet ultra-agresivo en muestra de 50 llamadas (~$5 USD)
3. Simulador E2E con escenarios especificos para cada FIX
4. Comparar scores antes (2.0/10) vs despues
5. Verificar 0 regresiones en bugs ya corregidos

## METRICAS DE EXITO

| Metrica | Antes | Objetivo |
|---------|-------|----------|
| Score Claude promedio | 2.0/10 | >= 5.0/10 |
| FLUJO_ROBOTICO | 117 (17.9%) | < 30 (5%) |
| FALTA_EMPATIA | 101 (15.5%) | < 20 (3%) |
| TIMING_INCORRECTO | 82 (12.6%) | < 15 (2%) |
| Llamadas con bugs | 110 (16.8%) | < 30 (5%) |
| Bugs totales | 24 tipos | < 10 tipos activos |
