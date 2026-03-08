# Plan de Validación Post FIX 648-653

## Contexto
- FIX 648-653 deployed: 2026-02-11 ~19:45
- Commit: a9eb6cc
- Bugs pre-fix: 12 (BRUCE2096-BRUCE2112)
- Esperado: Reducción >70% de bugs

---

## Fase 1: Validación Inmediata (30-45 min)

### 1. Llamadas de Prueba (15 min)
```bash
cd "C:\Users\PC 1\AgenteVentas"
python llamadas_masivas_produccion.py --cantidad 25 --delay 10
```

**Tipos de llamadas a probar:**
- 5 llamadas → Encargado NO disponible (testing FIX 652)
- 5 llamadas → Cliente dice "no hay ahorita" (testing FIX 648)
- 5 llamadas → Cliente da número indirectamente "llame al..." (testing FIX 649)
- 5 llamadas → Timeout simulado (testing FIX 651)
- 5 llamadas → Conversaciones normales

### 2. Descarga de Logs Post-Deploy (5 min)
```bash
# Opción 1: Manual desde Railway dashboard
# https://railway.app/project/.../logs

# Opción 2: WebFetch endpoint
# Revisar: https://nioval-webhook-server-production.up.railway.app/logs/api?limit=1000

# Opción 3: Script Python
python -c "
import requests
resp = requests.get('https://nioval-webhook-server-production.up.railway.app/logs/api?limit=1000')
with open('LOGS/post_fix653.txt', 'w', encoding='utf-8') as f:
    f.write(resp.text)
print('Logs guardados en LOGS/post_fix653.txt')
"
```

### 3. Auditoría de Bugs (10 min)

**Script de análisis:**
```python
# analizar_bugs_post_fix653.py
import requests
from datetime import datetime

# Obtener bugs post 20:00 (post-deploy)
bugs_url = "https://nioval-webhook-server-production.up.railway.app/bugs"

# Filtrar bugs con timestamp > 2026-02-11 20:00
# Clasificar por tipo
# Comparar con bugs pre-fix

bugs_post_fix = []
for bug in bugs_response:
    if bug['timestamp'] > '2026-02-11 20:00:00':
        bugs_post_fix.append(bug)

# Métricas
total_bugs_post = len(bugs_post_fix)
tipos = {}
for bug in bugs_post_fix:
    tipo = bug['tipo']
    tipos[tipo] = tipos.get(tipo, 0) + 1

print(f"Total bugs post-FIX 653: {total_bugs_post}")
print(f"Tipos: {tipos}")

# Comparación
bugs_pre_fix = 12
reduccion = (bugs_pre_fix - total_bugs_post) / bugs_pre_fix * 100
print(f"Reducción: {reduccion:.1f}%")
```

### 4. Revisión de Pattern Audit (5 min)
```
https://nioval-webhook-server-production.up.railway.app/pattern-audit
```

**Buscar:**
- DESPEDIDA_NATURAL_CLIENTE_* survival rate (FIX 648)
- Patrones nuevos con 0% survival
- Patrones invalidados frecuentemente

---

## Fase 2: Análisis de Logs (Si bugs persisten - 30 min)

### 1. Extraer Conversaciones Específicas
```bash
cd "C:\Users\PC 1\AgenteVentas"
python analizar_bugs_post_fix646.py  # Modificar para post-fix653
```

**Buscar en logs:**
- Líneas con "FIX 648", "FIX 649", "FIX 650", "FIX 651", "FIX 652", "FIX 653"
- Verificar que los fixes se están activando
- Buscar excepciones/errores en aplicación de fixes

### 2. Tests de Regresión
```bash
pytest tests/test_fix_648_650.py -v
pytest tests/test_fix_651_653.py -v
```

Verificar que todos pasan (184 tests).

### 3. Inspección Manual de Casos Edge
Para cada bug post-fix653:
1. Extraer BRUCE ID
2. Buscar conversación completa en logs
3. Identificar por qué el fix NO se aplicó:
   - ¿Pattern no matcheó?
   - ¿Fix se invalidó por FIX 600/601?
   - ¿Variante no cubierta?
   - ¿Timeout GPT antes del fix?

---

## Fase 3: Decisión (10 min)

### Escenario A: Bugs bajaron >70% ✅
**Acción:** ÉXITO
- Continuar con lotes de 50-100 llamadas
- Monitorear métricas por 24-48h
- Documentar casos exitosos

### Escenario B: Bugs bajaron 30-70% ⚠️
**Acción:** MEJORA PARCIAL
- Identificar 3-5 bugs más frecuentes post-fix
- Analizar por qué los fixes no cubrieron esos casos
- Implementar FIX 654+ para edge cases restantes
- Prioridad: bugs con >10% frecuencia

### Escenario C: Bugs NO bajaron (<30%) 🔴
**Acción:** HOTFIX URGENTE
- Verificar que deploy fue exitoso (revisar Railway dashboard)
- Verificar que código está correcto (git diff a9eb6cc)
- Buscar errores de sintaxis/runtime en logs Railway
- Posible rollback a commit anterior
- Investigación profunda de por qué fixes no funcionan

---

## Métricas Objetivo Post FIX 648-653

| Métrica | Pre-FIX | Objetivo Post-FIX | Estado |
|---------|---------|-------------------|--------|
| Total bugs | 12 | <4 (70% reducción) | ⏳ |
| CLIENTE_HABLA_ULTIMO | 2 (17%) | 0 (100% reducción) | ⏳ |
| GPT_LOGICA_ROTA | 3 (25%) | <1 (>66% reducción) | ⏳ |
| GPT_FUERA_DE_TEMA | 4 (33%) | <2 (>50% reducción) | ⏳ |
| GPT_TONO_INADECUADO | 2 (17%) | 0 (100% reducción) | ⏳ |
| GPT_OPORTUNIDAD_PERDIDA | 1 (8%) | 0 (100% reducción) | ⏳ |
| GPT_RESPUESTA_INCORRECTA | 1 (8%) | 0 (100% reducción) | ⏳ |

---

## Comandos Rápidos

```bash
# 1. Hacer 25 llamadas
cd "C:\Users\PC 1\AgenteVentas"
python llamadas_masivas_produccion.py --cantidad 25

# 2. Ver bugs post-deploy
# Browser: https://nioval-webhook-server-production.up.railway.app/bugs

# 3. Descargar logs
python -c "import requests; open('LOGS/post_fix653.txt','w',encoding='utf-8').write(requests.get('https://nioval-webhook-server-production.up.railway.app/logs/api?limit=1000').text)"

# 4. Analizar bugs
python analizar_bugs_post_fix646.py  # Modificar fechas

# 5. Tests de regresión
pytest tests/ -v --tb=short
```

---

## Siguiente Auditoría
- **Cuándo:** 24h después del deploy (2026-02-12 20:00)
- **Qué:** Análisis de 100-200 llamadas acumuladas
- **Objetivo:** Confirmar estabilidad de los fixes
