# INSTRUCCIONES PARA EJECUTAR TESTS - AUDITORÍA W04

**Fecha de creación**: 24 de enero 2026
**Objetivo**: Validar implementaciones de FIX 475-482 antes de deploy a producción

---

## 📋 TESTS DISPONIBLES

Se crearon 5 scripts de test individuales más 1 script maestro:

### Tests Individuales (Críticos)

1. **`test_fix_475_timeout_deepgram.py`** - FIX 475
   - Valida reducción de timeout Deepgram (1.0s → 0.3s)
   - Verifica comentarios explicativos
   - **Duración**: ~2 segundos

2. **`test_fix_476_preguntas_directas.py`** - FIX 476
   - Valida detección de 5 categorías de preguntas
   - Prueba 8 casos reales
   - **Duración**: ~5 segundos

3. **`test_fix_477_detector_interrupciones.py`** - FIX 477
   - Valida detector de "cliente dando información"
   - Prueba números parciales, correos parciales, frases incompletas
   - **Duración**: ~5 segundos

4. **`test_fix_479_480_481_recuperacion.py`** - FIX 479+480+481
   - Valida bloqueo de respuestas vacías (FIX 479)
   - Valida detección de repeticiones (FIX 480)
   - Valida recuperación de errores (FIX 481)
   - **Duración**: ~8 segundos

5. **`test_fix_482_metricas.py`** - FIX 482 (Opcional)
   - Valida sistema de métricas e instrumentación
   - Prueba timing, calidad, interacciones
   - **Duración**: ~6 segundos

### Script Maestro

6. **`ejecutar_todos_los_tests.py`** - Suite Completa
   - Ejecuta todos los tests anteriores
   - Genera reporte consolidado
   - Identifica tests críticos fallidos
   - **Duración**: ~30 segundos

---

## 🚀 OPCIÓN 1: EJECUTAR TODOS LOS TESTS (RECOMENDADO)

Esta es la forma más rápida y simple:

```bash
cd AgenteVentas
python ejecutar_todos_los_tests.py
```

**Salida esperada**:
```
======================================================================
SUITE COMPLETA DE TESTS - AUDITORIA W04
Fecha: 2026-01-24 XX:XX:XX
======================================================================

======================================================================
EJECUTANDO: test_fix_475_timeout_deepgram.py
======================================================================
...
[Output de cada test]
...

======================================================================
REPORTE FINAL DE TESTS
======================================================================

FIX 475: Timeout Deepgram:
  Estado: PASS
  Criticidad: CRITICO

FIX 476: Preguntas Directas:
  Estado: PASS
  Criticidad: CRITICO

[...]

======================================================================
RESUMEN
======================================================================
Tests ejecutados: 5
Tests pasados: 5
Tests fallidos: 0
Tasa de exito: 100.0%

======================================================================
EXITO: TODOS LOS TESTS PASARON
Sistema listo para testing en produccion
======================================================================
```

---

## 🔍 OPCIÓN 2: EJECUTAR TESTS INDIVIDUALES

Si prefieres ejecutar tests uno por uno:

### Test 1: FIX 475 (Timeout Deepgram)
```bash
python test_fix_475_timeout_deepgram.py
```

**Salida esperada**:
```
============================================================
TEST FIX 475: TIMEOUT DEEPGRAM
============================================================

Timeout encontrado: 0.3s
  PASS: Timeout configurado en 0.3s
  PASS: Comentario FIX 475 encontrado
  PASS: Comentario explica la reduccion

============================================================
RESULTADO: 3/3 tests pasados
============================================================
EXITO: FIX 475 implementado correctamente
```

### Test 2: FIX 476 (Preguntas Directas)
```bash
python test_fix_476_preguntas_directas.py
```

**Salida esperada**:
```
============================================================
TEST FIX 476: PREGUNTAS DIRECTAS
============================================================

TEST 1: PREGUNTA_UBICACION
  Entrada: '¿De donde habla?'
  PASS: Respuesta correcta
    'Estamos ubicados en Guadalajara, Jalisco, pero hacemos envíos...'

[... 7 tests más ...]

============================================================
RESULTADO: 8/8 tests pasados
============================================================
EXITO: FIX 476 funciona correctamente
```

### Test 3: FIX 477 (Detector Interrupciones)
```bash
python test_fix_477_detector_interrupciones.py
```

### Test 4: FIX 479+480+481 (Recuperación)
```bash
python test_fix_479_480_481_recuperacion.py
```

### Test 5: FIX 482 (Métricas)
```bash
python test_fix_482_metricas.py
```

---

## ⚠️ QUÉ HACER SI UN TEST FALLA

### Si FALLA un test CRÍTICO (FIX 475, 476, 477, 479-481):

1. **Leer el mensaje de error detalladamente**
   ```
   FAIL: Categoria incorrecta (esperado: PREGUNTA_UBICACION, obtenido: None)
   ```

2. **Revisar el código correspondiente**
   - El test indica el archivo y método que falló
   - Ejemplo: Si falla FIX 476, revisar `agente_ventas.py:5313-5420`

3. **NO DEPLOY A PRODUCCIÓN** hasta corregir el fallo

4. **Reportar el error**:
   - Copiar output completo del test
   - Agregar a issue de GitHub o documento de tracking

### Si FALLA un test OPCIONAL (FIX 482):

1. **Revisar si es crítico para tu caso de uso**
   - FIX 482 (métricas) es importante para análisis pero no bloquea funcionalidad

2. **Se puede proceder con precaución** si tests críticos pasan

3. **Agendar corrección** para próxima iteración

---

## 📊 INTERPRETACIÓN DE RESULTADOS

### ✅ Resultado Ideal
```
Tests ejecutados: 5
Tests pasados: 5
Tests fallidos: 0
Tasa de exito: 100.0%

EXITO: TODOS LOS TESTS PASARON
```
**Acción**: Proceder con testing en producción

---

### ⚠️ Resultado Aceptable
```
Tests ejecutados: 5
Tests pasados: 4
Tests fallidos: 1
Tasa de exito: 80.0%

PARCIAL: Tests criticos OK, algunos opcionales fallaron
```
**Acción**: Proceder con precaución, monitorear métricas

---

### ❌ Resultado Bloqueante
```
Tests ejecutados: 5
Tests pasados: 3
Tests fallidos: 2

ATENCION: TESTS CRITICOS FALLIDOS
  - FIX 476: Preguntas Directas
  - FIX 477: Detector Interrupciones
```
**Acción**: NO DEPLOY, corregir tests críticos primero

---

## 🐛 TROUBLESHOOTING

### Error: "ModuleNotFoundError: No module named 'agente_ventas'"

**Solución**:
```bash
# Asegúrate de estar en el directorio correcto
cd AgenteVentas
python test_fix_476_preguntas_directas.py
```

### Error: "UnicodeEncodeError: 'charmap' codec can't encode..."

**Solución**: Este es un error de Windows con emojis (ya conocido).
Los tests **NO usan emojis en prints**, así que no deberías ver este error.

Si ocurre, ejecuta:
```bash
python -X utf8 test_fix_476_preguntas_directas.py
```

### Error: "ImportError: cannot import name 'MetricsLogger'"

**Causa**: `agente_ventas.py` no se ha guardado correctamente con los cambios.

**Solución**:
1. Verificar que `agente_ventas.py` tiene la clase `MetricsLogger` en línea 22
2. Reiniciar Python si usas REPL
3. Verificar que no hay errores de sintaxis en `agente_ventas.py`

---

## 📝 DESPUÉS DE EJECUTAR TESTS

### Si todos los tests PASAN:

1. **Documentar resultados**:
   ```bash
   # El script maestro genera automáticamente:
   reporte_tests_YYYYMMDD_HHMMSS.txt
   ```

2. **Proceder con Fase 2**: Testing en producción
   - Llamada de prueba end-to-end
   - Validar métricas se imprimen
   - Confirmar latencias reducidas

3. **Commit cambios**:
   ```bash
   git add .
   git commit -m "feat: implementar FIX 475-482 (AUDITORIA W04)

   - FIX 475: Reducir timeout Deepgram 1.0s -> 0.3s
   - FIX 476: Detector preguntas directas (5 categorias)
   - FIX 477: Prevenir interrupciones durante dictado
   - FIX 479: Validacion respuestas vacias
   - FIX 480: Deteccion repeticiones cliente
   - FIX 481: Sistema recuperacion errores
   - FIX 482: Instrumentacion metricas completas

   Todos los tests unitarios: PASS (100%)
   "
   ```

### Si algún test FALLA:

1. **NO commit** hasta corregir
2. **Revisar código** del FIX específico
3. **Re-ejecutar test** después de corrección
4. **Documentar** qué se cambió y por qué

---

## 📞 SIGUIENTE PASO: TESTING EN PRODUCCIÓN

Una vez que **todos los tests unitarios pasen**, proceder con:

```bash
# Llamada de prueba a número test
python llamar_produccion.py --test
```

Ver instrucciones detalladas en `RESUMEN_IMPLEMENTACIONES_AUDITORIA_W04.md`

---

## ✅ CHECKLIST FINAL

Antes de deploy a producción, verificar:

- [ ] Script maestro ejecutado: `python ejecutar_todos_los_tests.py`
- [ ] Todos los tests críticos: PASS
- [ ] Reporte de tests guardado
- [ ] Código committed con mensaje descriptivo
- [ ] Llamada de prueba ejecutada exitosamente
- [ ] Métricas FIX 482 se imprimen al final de llamada
- [ ] Latencias reducidas verificadas (<5s promedio)
- [ ] Deploy gradual planificado (10% → 50% → 100%)

---

**Generado**: 2026-01-24
**Versión**: 1.0
**Contacto**: Ver RESUMEN_IMPLEMENTACIONES_AUDITORIA_W04.md para detalles
