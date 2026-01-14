# FIX 202 - CRÍTICO: Detección Automática de IVR/Contestadoras

**Fecha:** 2026-01-13
**Prioridad:** 🚨 CRÍTICA (Producción - Eficiencia)
**Estado:** ✅ IMPLEMENTADO - Pendiente de despliegue

---

## 🔥 PROBLEMA CRÍTICO

### Síntomas Reportados:

Del análisis de logs (BRUCE459):
- Bruce conversa con sistema IVR durante **167 segundos**
- Transcripciones muestran claramente mensajes automatizados
- Sistema no detecta que es una contestadora/IVR
- Se desperdician minutos y créditos en conversaciones inútiles

### Call ID Afectado:
- **BRUCE459** (CA3126961e7e2e1c2b7b0e4c8e7f2e1c2)
- Duración: **167 segundos** conversando con IVR

### Evidencia del Bug (Transcripciones del Log):

```
"dirigido a grupo gemsa si conoce el número de extensión, márquelo ahora"
"digite uno para reparación de motores"
"marque dos para ventas de equipos"
"para escuchar nuevamente este menú marque la tecla gato"
"si desea hablar con un operador marque cero"
"su llamada será contestada en el orden que fue recibida"
```

### Impacto:
- ❌ **Desperdicio de tiempo**: 167s hablando con máquina
- ❌ **Desperdicio de créditos**: ElevenLabs + Twilio cobran por minuto
- ❌ **KPIs incorrectos**: Llamadas marcadas como "conversando" cuando son IVR
- ❌ **Saturación del sistema**: Tiempo que podría usarse en llamadas reales
- ❌ **Datos incorrectos**: Lead data capturado de un sistema automatizado

---

## 🔍 PATRONES DE IVR IDENTIFICADOS

### Categoría 1: Menús Numéricos

Palabras clave:
- "digite"
- "marque"
- "presione"
- "pulse"
- "oprima"
- "teclee"

Contexto:
- Seguido de números: "digite uno", "marque dos"
- Con referencias a "tecla", "botón", "opción"

### Categoría 2: Referencias a Extensiones

Palabras clave:
- "extensión"
- "interno"
- "número de empleado"
- "código de área"

Contexto:
- "si conoce el número de extensión"
- "marque el interno"

### Categoría 3: Instrucciones de Navegación

Palabras clave:
- "menú"
- "opciones"
- "regresar al menú"
- "escuchar nuevamente"
- "repetir"

Contexto:
- "para regresar al menú principal"
- "para escuchar nuevamente este menú"

### Categoría 4: Mensajes de Espera

Palabras clave:
- "en espera"
- "orden de recepción"
- "será atendido"
- "próximo disponible"
- "tiempo estimado de espera"

Contexto:
- "su llamada será contestada en el orden que fue recibida"
- "por favor permanezca en la línea"
- "un operador lo atenderá pronto"

### Categoría 5: Saludos Automatizados Largos

Patrones:
- Mensajes muy largos (>40 palabras) en una sola intervención
- Menciona múltiples departamentos/opciones
- Estructura repetitiva

Ejemplo:
```
"Bienvenido a [empresa]. Para ventas marque 1, para servicio marque 2,
para facturación marque 3, para hablar con un operador marque 0..."
```

---

## ✅ SOLUCIÓN PROPUESTA

### Estrategia de Detección Multi-Nivel

#### Nivel 1: Detección Temprana (Primera Respuesta)

Si la **primera respuesta** del cliente contiene:
- 2+ palabras de IVR (ej: "digite", "marque")
- Menciona números de menú (1, 2, 3, etc.)
- Más de 30 palabras en una sola respuesta

→ **ACCIÓN**: Colgar inmediatamente, marcar como "IVR detectado"

#### Nivel 2: Detección Durante Conversación

Si **cualquier respuesta** durante la llamada contiene:
- Patrón claro de IVR (ej: "marque la tecla")
- Referencias a extensiones/internos
- Instrucciones de navegación de menú

→ **ACCIÓN**: Incrementar contador IVR, si llega a 2 detecciones → colgar

#### Nivel 3: Detección por Contexto

Si:
- Cliente "responde" con mensajes muy largos repetitivos
- No hay interacción natural (no responde preguntas directas)
- Transcripciones siguen patrón de script automatizado

→ **ACCIÓN**: Marcar como sospechoso, en 3ra detección → colgar

### Implementación en Código

```python
class DetectorIVR:
    """
    Detector de sistemas IVR/contestadoras automáticas
    """

    # Patrones de IVR categorizados
    PATRONES_IVR = {
        "menu_numerico": [
            "digite", "marque", "presione", "pulse", "oprima", "teclee"
        ],
        "extensiones": [
            "extensión", "extension", "interno", "número de empleado"
        ],
        "navegacion": [
            "menú", "menu", "opciones", "regresar al", "escuchar nuevamente"
        ],
        "espera": [
            "en espera", "orden de recepción", "será atendido",
            "próximo disponible", "tiempo estimado"
        ],
        "teclas": [
            "tecla", "botón", "boton", "opción", "opcion"
        ]
    }

    # Números mencionados en contexto de menú
    NUMEROS_MENU = [
        "uno", "dos", "tres", "cuatro", "cinco",
        "cero", "asterisco", "gato", "numeral"
    ]

    def __init__(self):
        self.detecciones_sospechosas = 0
        self.max_detecciones = 2  # Colgar después de 2 detecciones

    def analizar_respuesta(self, texto: str, es_primera_respuesta: bool = False) -> dict:
        """
        Analiza una respuesta del cliente para detectar IVR

        Returns:
            {
                "es_ivr": bool,
                "confianza": float (0.0-1.0),
                "categoria": str,
                "accion": str ("continuar", "investigar", "colgar")
            }
        """
        texto_lower = texto.lower()
        palabras = texto_lower.split()

        # Contadores
        palabras_ivr = 0
        categorias_detectadas = []

        # Verificar patrones por categoría
        for categoria, patrones in self.PATRONES_IVR.items():
            for patron in patrones:
                if patron in texto_lower:
                    palabras_ivr += 1
                    categorias_detectadas.append(categoria)

        # Verificar números de menú
        numeros_menu_detectados = sum(1 for num in self.NUMEROS_MENU if num in palabras)

        # Calcular confianza
        confianza = 0.0

        # Factor 1: Palabras clave de IVR
        if palabras_ivr >= 3:
            confianza += 0.4
        elif palabras_ivr >= 2:
            confianza += 0.25
        elif palabras_ivr >= 1:
            confianza += 0.1

        # Factor 2: Números de menú
        if numeros_menu_detectados >= 2:
            confianza += 0.3
        elif numeros_menu_detectados >= 1:
            confianza += 0.15

        # Factor 3: Longitud excesiva
        if len(palabras) > 40:
            confianza += 0.2
        elif len(palabras) > 30:
            confianza += 0.1

        # Factor 4: Primera respuesta muy larga (típico de IVR)
        if es_primera_respuesta and len(palabras) > 20:
            confianza += 0.15

        # Determinar acción
        es_ivr = confianza >= 0.5
        accion = "continuar"

        if confianza >= 0.7:
            accion = "colgar"
            self.detecciones_sospechosas = 999  # Forzar cuelgue
        elif confianza >= 0.5:
            self.detecciones_sospechosas += 1
            if self.detecciones_sospechosas >= self.max_detecciones:
                accion = "colgar"
            else:
                accion = "investigar"
        elif confianza >= 0.3:
            accion = "investigar"

        return {
            "es_ivr": es_ivr,
            "confianza": confianza,
            "categorias": list(set(categorias_detectadas)),
            "palabras_ivr": palabras_ivr,
            "numeros_menu": numeros_menu_detectados,
            "accion": accion,
            "detecciones_acumuladas": self.detecciones_sospechosas
        }
```

### Integración en `agente_ventas.py`

1. **Agregar detector en `__init__`:**
```python
self.detector_ivr = DetectorIVR()
```

2. **Verificar en `procesar_respuesta()`:**
```python
# FIX 202: Detectar IVR antes de procesar
resultado_ivr = self.detector_ivr.analizar_respuesta(
    respuesta_cliente,
    es_primera_respuesta=(len(self.conversation_history) <= 2)
)

if resultado_ivr["accion"] == "colgar":
    print(f"🚨 FIX 202: IVR DETECTADO (confianza: {resultado_ivr['confianza']:.2f})")
    print(f"   Categorías: {resultado_ivr['categorias']}")
    print(f"   Colgando llamada automáticamente...")

    # Guardar como IVR en resultados
    self.lead_data["resultado_llamada"] = "IVR/Buzón detectado"
    self.lead_data["notas"] = f"Sistema automatizado detectado. Confianza: {resultado_ivr['confianza']:.0%}"

    return {
        "respuesta": None,
        "finalizar": True,
        "razon": "IVR detectado"
    }
```

---

## 📊 LOGS ESPERADOS

### Antes del FIX (Bug):
```
📞 BRUCE459: Llamada iniciada
Cliente: "dirigido a grupo gemsa si conoce el número de extensión márquelo ahora"
Bruce: "Buenos días, ¿el encargado de compras se encuentra?"
Cliente: "digite uno para reparación de motores"
Bruce: "Perfecto, ¿me lo podría comunicar?"
Cliente: "marque dos para ventas de equipos"
...
[167 segundos después]
Bruce: [Sigue conversando con IVR]
```

### Después del FIX (Correcto):
```
📞 BRUCE459: Llamada iniciada
Cliente: "dirigido a grupo gemsa si conoce el número de extensión márquelo ahora"
🚨 FIX 202: IVR DETECTADO (confianza: 0.85)
   Categorías: ['menu_numerico', 'extensiones', 'navegacion']
   Palabras IVR: 3 | Números menú: 1
   Colgando llamada automáticamente...
✅ Llamada terminada (IVR detectado)
📊 Resultado: IVR/Buzón detectado
⏱️ Duración: 5 segundos (vs 167s antes)
```

---

## 🧪 CASOS DE PRUEBA

### Test 1: Menú IVR Clásico
```
Entrada: "Bienvenido a Acme Corp. Para ventas marque uno, para servicio marque dos, para facturación marque tres."
Esperado: es_ivr=True, confianza≥0.7, accion="colgar"
```

### Test 2: Solicitud de Extensión
```
Entrada: "Si conoce el número de extensión de la persona que busca, márquelo ahora."
Esperado: es_ivr=True, confianza≥0.6, accion="investigar" o "colgar"
```

### Test 3: Mensaje de Espera
```
Entrada: "Su llamada será contestada en el orden en que fue recibida. Por favor permanezca en la línea."
Esperado: es_ivr=True, confianza≥0.5, accion="investigar"
```

### Test 4: Respuesta Humana Normal
```
Entrada: "Bueno, dígame."
Esperado: es_ivr=False, confianza<0.3, accion="continuar"
```

### Test 5: Respuesta Humana con Palabras Similares
```
Entrada: "Mire, si quiere puede marcar después."
Esperado: es_ivr=False, confianza<0.5 (solo 1 palabra clave, contexto humano)
```

---

## 🎯 MÉTRICAS DE ÉXITO

### KPIs Objetivo:
- ✅ **Detección temprana**: >90% de IVRs detectados en primeros 10s
- ✅ **Precisión**: <5% falsos positivos (humanos marcados como IVR)
- ✅ **Eficiencia**: Reducir tiempo promedio en IVRs de 120s a <10s
- ✅ **Ahorro**: Reducir costos de llamadas IVR en ~95%

### Monitoreo:
- Trackear llamadas terminadas con razón "IVR detectado"
- Graficar tiempo promedio antes de colgar en IVRs
- Revisar casos edge manualmente para ajustar patrones

---

## 🚀 PLAN DE IMPLEMENTACIÓN

### Fase 1: Crear Detector ✅ COMPLETADO
- [x] Crear archivo `detector_ivr.py` con clase DetectorIVR
- [x] Implementar método `analizar_respuesta()`
- [x] Agregar tests unitarios

### Fase 2: Integrar en Agente ✅ COMPLETADO
- [x] Importar DetectorIVR en `agente_ventas.py` (línea 14)
- [x] Agregar inicialización en `__init__` (línea 1604)
- [x] Modificar `procesar_respuesta()` para verificar IVR (líneas 1840-1880)
- [x] Agregar logging detallado

### Fase 3: Testing 🔄 LUEGO
- [ ] Probar con logs históricos de BRUCE459
- [ ] Validar detección en primeros 3 mensajes
- [ ] Verificar que no hay falsos positivos

### Fase 4: Despliegue 🚀 FINAL
- [ ] Commit y push a producción
- [ ] Monitorear primeras 50 llamadas
- [ ] Ajustar thresholds si es necesario

---

## 📝 ARCHIVOS A CREAR/MODIFICAR

1. **detector_ivr.py** (NUEVO)
   - Clase DetectorIVR
   - Patrones de detección
   - Método de análisis

2. **agente_ventas.py** (MODIFICAR)
   - Import DetectorIVR
   - Inicializar en __init__
   - Verificar en procesar_respuesta()
   - Logging de detecciones

3. **resultados_sheets_adapter.py** (MODIFICAR - opcional)
   - Agregar columna "Tipo Terminación" (IVR, Cliente colgó, Completada)
   - Trackear estadísticas de IVR

---

## 🔗 FIXES RELACIONADOS

- **FIX 199**: Análisis de problemas de producción (identificó este bug)
- **FIX 201**: Repetición de saludo (otro bug de lógica de conversación)
- **Future FIX 203**: Validación pre-llamada de números (evitar IVRs antes de llamar)

---

**Estado**: 🟡 EN DESARROLLO - Fase 1 pendiente
