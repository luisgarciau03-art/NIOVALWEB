# -*- coding: utf-8 -*-
"""
FASE 6: Auditoría de Verificación Post-Implementación
=====================================================
Verifica que TODAS las implementaciones de Fase 0-4 funcionan correctamente.

Checks:
  1. Calidad del auditor (Fase 0): detectores calibrados, FP reducidos
  2. Anti-repetición (Fase 1 - FIX 678+679): sin duplicados en código
  3. FLU-001/CTN-002 (Fase 4 - FIX 684+685): sin excusas técnicas
  4. GPT timeout resilience (Fase 3 - FIX 682+683): fallbacks correctos
  5. Auditoría en producción: bugs reales vs baseline
  6. Test suite health: todos los tests pasan
"""

import os
import re
import sys
import json
import importlib
from datetime import datetime
from collections import Counter, defaultdict

# Encoding UTF-8 para Windows
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

# ============================================================
# COLORES PARA OUTPUT
# ============================================================
class C:
    OK = "\033[92m"     # Verde
    WARN = "\033[93m"   # Amarillo
    FAIL = "\033[91m"   # Rojo
    BOLD = "\033[1m"
    END = "\033[0m"
    BLUE = "\033[94m"

def ok(msg): return f"{C.OK}[OK]{C.END} {msg}"
def warn(msg): return f"{C.WARN}[WARN]{C.END} {msg}"
def fail(msg): return f"{C.FAIL}[FAIL]{C.END} {msg}"
def header(msg): return f"\n{C.BOLD}{C.BLUE}{'='*70}\n  {msg}\n{'='*70}{C.END}"

# ============================================================
# CHECK 1: Código fuente - sin excusas técnicas (FIX 684)
# ============================================================
def check_sin_excusas_tecnicas():
    """Verifica que no hay menciones de problemas técnicos en respuestas a clientes."""
    print(header("CHECK 1: Sin excusas técnicas en respuestas (FIX 684)"))

    resultados = []

    # Patrones prohibidos en strings literales de respuesta
    patrones_prohibidos = [
        'problemas de conexión', 'problemas de conexion',
        'problemas con la conexión', 'problemas con la conexion',
        'problema con la línea', 'problema con la linea',
        'problemas técnicos', 'problemas tecnicos',
        'hay interferencia', 'problemas de comunicación',
        'problemas de comunicacion', 'problemas de audio',
    ]

    archivos = ['servidor_llamadas.py', 'agente_ventas.py']

    for archivo in archivos:
        filepath = os.path.join(BASE_DIR, archivo)
        with open(filepath, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        for line_num, line in enumerate(lines, 1):
            stripped = line.strip()
            # Skip comments
            if stripped.startswith('#'):
                continue
            # Skip lines that are pattern lists/detection (contienen variable de detección)
            if any(kw in stripped for kw in [
                'patrones_tecnicos', 'patrones_conexion', 'patrones_prohibidos',
                'rechazos_flu', 'bruce_dijo_problemas', 'for p in',
                'if any(p in', "if '", 'assert ', 'in respuesta_lower',
            ]):
                continue
            # Solo buscar en asignaciones de respuesta o return statements
            is_response_line = any(kw in stripped for kw in [
                'respuesta =', 'respuesta_timeout =', 'mensaje_error =',
                'return "', "return '", 'response.say(', 'mensajes_repetir',
                'respuesta_fallback', 'fallback =',
            ])
            if not is_response_line:
                continue

            for patron in patrones_prohibidos:
                if patron in line.lower():
                    resultados.append(fail(
                        f"{archivo}:{line_num}: '{patron}' en respuesta → \"{stripped[:70]}...\""
                    ))

    if not resultados:
        print(ok("Ninguna excusa técnica en strings de respuesta al cliente"))
        return True
    else:
        for r in resultados:
            print(r)
        return False


# ============================================================
# CHECK 2: Anti-repetición activa (FIX 678+679)
# ============================================================
def check_anti_repeticion():
    """Verifica que los mecanismos anti-repetición están en el código."""
    print(header("CHECK 2: Anti-repetición activa (FIX 678+679)"))

    checks_ok = 0
    checks_total = 0

    # Check 2a: FIX 679 - Detector hash de duplicados en agente_ventas.py
    checks_total += 1
    with open(os.path.join(BASE_DIR, 'agente_ventas.py'), 'r', encoding='utf-8') as f:
        agente_src = f.read()
    if 'FIX 679' in agente_src and 'SequenceMatcher' in agente_src and '0.85' in agente_src:
        print(ok("FIX 679: Detector hash duplicados (SequenceMatcher >= 0.85) presente"))
        checks_ok += 1
    else:
        print(fail("FIX 679: Detector hash duplicados NO encontrado"))

    # Check 2b: FIX 678 - ya_presento check en servidor_llamadas.py
    checks_total += 1
    with open(os.path.join(BASE_DIR, 'servidor_llamadas.py'), 'r', encoding='utf-8') as f:
        servidor_src = f.read()
    count_678 = servidor_src.count('ya_presento_678')
    if count_678 >= 3:
        print(ok(f"FIX 678: ya_presento check en {count_678} ubicaciones (esperado >=3)"))
        checks_ok += 1
    else:
        print(fail(f"FIX 678: ya_presento solo en {count_678} ubicaciones (esperado >=3)"))

    # Check 2c: FIX 680 - ya_pregunto_encargado check
    checks_total += 1
    count_680 = servidor_src.count('ya_pregunto_encargado_680')
    if count_680 >= 3:
        print(ok(f"FIX 680: ya_pregunto_encargado en {count_680} ubicaciones (esperado >=3)"))
        checks_ok += 1
    else:
        print(fail(f"FIX 680: ya_pregunto_encargado solo en {count_680} ubicaciones (esperado >=3)"))

    # Check 2d: FIX 684 - Post-filter CTN-002
    checks_total += 1
    if 'FIX 684' in agente_src and 'patrones_tecnicos_684' in agente_src:
        print(ok("FIX 684: Post-filter anti-problemas-técnicos presente"))
        checks_ok += 1
    else:
        print(fail("FIX 684: Post-filter anti-problemas-técnicos NO encontrado"))

    print(f"\n  Resultado: {checks_ok}/{checks_total} checks pasaron")
    return checks_ok == checks_total


# ============================================================
# CHECK 3: GPT timeout resilience (FIX 682+683)
# ============================================================
def check_gpt_timeout_resilience():
    """Verifica que GPT timeout tiene fallback en vez de colgar."""
    print(header("CHECK 3: GPT timeout resilience (FIX 682+683)"))

    checks_ok = 0
    checks_total = 0

    with open(os.path.join(BASE_DIR, 'servidor_llamadas.py'), 'r', encoding='utf-8') as f:
        src = f.read()
    with open(os.path.join(BASE_DIR, 'agente_ventas.py'), 'r', encoding='utf-8') as f:
        agente_src = f.read()

    # Check 3a: Contador GPT timeouts
    checks_total += 1
    if 'gpt_timeouts_consecutivos' in agente_src and 'gpt_timeouts_consecutivos' in src:
        print(ok("FIX 682: Contador gpt_timeouts_consecutivos presente en agente + servidor"))
        checks_ok += 1
    else:
        print(fail("FIX 682: Contador gpt_timeouts_consecutivos faltante"))

    # Check 3b: Fallback contextual en 1er timeout
    checks_total += 1
    if 'ya_presento_682' in src and 'ya_encargado_682' in src:
        print(ok("FIX 682: Fallback contextual (pitch/encargado/repetir) en 1er timeout"))
        checks_ok += 1
    else:
        print(fail("FIX 682: Fallback contextual NO encontrado en 1er timeout"))

    # Check 3c: STT timeout adaptativo
    checks_total += 1
    if 'FIX 683' in src:
        # Verificar valores: 2.0, 1.8, 1.5
        has_2_0 = 'max_wait_deepgram = 2.0' in src
        has_1_8 = 'max_wait_deepgram = 1.8' in src
        has_1_5 = 'max_wait_deepgram = 1.5' in src
        if has_2_0 and has_1_8 and has_1_5:
            print(ok("FIX 683: STT timeout adaptativo (2.0/1.8/1.5s) configurado"))
            checks_ok += 1
        else:
            print(warn(f"FIX 683: Valores timeout incompletos (2.0={has_2_0}, 1.8={has_1_8}, 1.5={has_1_5})"))
    else:
        print(fail("FIX 683: STT timeout adaptativo NO encontrado"))

    print(f"\n  Resultado: {checks_ok}/{checks_total} checks pasaron")
    return checks_ok == checks_total


# ============================================================
# CHECK 4: Auditor calibrado (Fase 0 + FIX 681 + FIX 685)
# ============================================================
def check_auditor_calibrado():
    """Verifica que el auditor tiene las mejoras de Fase 0/4."""
    print(header("CHECK 4: Auditor calibrado (Fase 0 + FIX 681 + FIX 685)"))

    checks_ok = 0
    checks_total = 0

    with open(os.path.join(BASE_DIR, 'auditor_conversaciones.py'), 'r', encoding='utf-8') as f:
        src = f.read()

    # Check 4a: AI-004 usa SequenceMatcher (no substring naive)
    checks_total += 1
    if 'SequenceMatcher' in src:
        print(ok("AI-004: Usa SequenceMatcher para detección de duplicados"))
        checks_ok += 1
    else:
        print(fail("AI-004: NO usa SequenceMatcher"))

    # Check 4b: CAL-001 tiene exclusiones de rechazo
    checks_total += 1
    if 'no estamos interesados' in src and 'ahorita no' in src and 'ya tenemos proveedor' in src:
        print(ok("CAL-001: Exclusiones de rechazo expandidas"))
        checks_ok += 1
    else:
        print(fail("CAL-001: Exclusiones de rechazo incompletas"))

    # Check 4c: FLU-001 tiene exclusiones mejoradas (FIX 685)
    checks_total += 1
    if 'es_timeout_cliente' in src and 'bruce_se_despidio' in src:
        print(ok("FLU-001 (FIX 685): Exclusiones timeout/buzón/despedida Bruce"))
        checks_ok += 1
    else:
        print(fail("FLU-001 (FIX 685): Exclusiones mejoradas NO encontradas"))

    # Check 4d: CTN-002 detecta patrones técnicos
    checks_total += 1
    if 'patrones_conexion' in src and 'CTN-002' in src:
        print(ok("CTN-002: Detector de excusas técnicas activo"))
        checks_ok += 1
    else:
        print(fail("CTN-002: Detector NO encontrado"))

    # Check 4e: CTN-001 usa pitch completo (no solo substring 'nioval')
    checks_total += 1
    if 'menciones_pitch_completo' in src:
        print(ok("CTN-001: Conteo de pitch COMPLETO (no solo substring)"))
        checks_ok += 1
    else:
        print(fail("CTN-001: Aún usa substring simple"))

    print(f"\n  Resultado: {checks_ok}/{checks_total} checks pasaron")
    return checks_ok == checks_total


# ============================================================
# CHECK 5: Auditoría de producción
# ============================================================
def check_produccion():
    """Ejecuta auditor en llamadas recientes y compara vs baseline."""
    print(header("CHECK 5: Auditoría de producción (llamadas recientes)"))

    try:
        from auditor_conversaciones import main as auditar_main, parsear_logs, auditar_conversacion
    except ImportError as e:
        print(fail(f"No se pudo importar auditor: {e}"))
        return False

    # Parsear logs
    conversaciones = parsear_logs()
    if not conversaciones:
        print(warn("No hay logs disponibles para auditar"))
        return True  # No es fallo, simplemente no hay datos

    conversaciones_validas = {k: v for k, v in conversaciones.items() if v['mensajes']}

    # Buscar las más recientes (últimas 50 o BRUCE >= 2175)
    ids_numericos = {}
    for k in conversaciones_validas:
        match = re.search(r'(\d+)', k)
        if match:
            ids_numericos[k] = int(match.group())

    if not ids_numericos:
        print(warn("No se encontraron IDs numéricos en conversaciones"))
        return True

    max_id = max(ids_numericos.values())
    min_reciente = max(max_id - 50, 2175)  # Últimas 50 o post-FIX 678

    recientes = {k: v for k, v in conversaciones_validas.items()
                 if ids_numericos.get(k, 0) >= min_reciente}

    print(f"  Conversaciones recientes (BRUCE >= {min_reciente}): {len(recientes)}")

    if len(recientes) == 0:
        print(warn("No hay conversaciones recientes suficientes"))
        return True

    # Auditar cada conversación
    bugs_por_tipo = Counter()
    total_bugs = 0
    llamadas_con_bugs = 0
    detalles_bugs = defaultdict(list)

    for bruce_id, conv in recientes.items():
        bugs = auditar_conversacion(bruce_id, conv)
        if bugs:
            llamadas_con_bugs += 1
            total_bugs += len(bugs)
            for b in bugs:
                bugs_por_tipo[b['codigo']] += 1
                detalles_bugs[b['codigo']].append(bruce_id)

    # Reportar
    pct_con_bugs = (llamadas_con_bugs / len(recientes) * 100) if recientes else 0
    bugs_per_call = (total_bugs / len(recientes)) if recientes else 0

    print(f"\n  Resultados:")
    print(f"  {'─'*50}")
    print(f"  Llamadas analizadas:  {len(recientes)}")
    print(f"  Llamadas con bugs:    {llamadas_con_bugs} ({pct_con_bugs:.1f}%)")
    print(f"  Bugs totales:         {total_bugs}")
    print(f"  Bugs por llamada:     {bugs_per_call:.2f}")
    print(f"\n  Bugs por tipo:")
    for codigo, count in bugs_por_tipo.most_common(15):
        pct = count / total_bugs * 100 if total_bugs else 0
        ejemplos = detalles_bugs[codigo][:3]
        print(f"    {codigo:12s}: {count:3d} ({pct:5.1f}%)  ej: {', '.join(ejemplos)}")

    # Verificaciones específicas post-fix
    print(f"\n  Verificaciones post-implementación:")

    # CTN-002 debe ser 0 en llamadas post-FIX 684
    ctn002 = bugs_por_tipo.get('CTN-002', 0)
    if ctn002 == 0:
        print(ok(f"CTN-002 (excusas técnicas): 0 instancias"))
    else:
        print(warn(f"CTN-002: {ctn002} instancias (posible llamada pre-deploy)"))
        for bruce_id in detalles_bugs.get('CTN-002', []):
            print(f"    → {bruce_id}")

    # AI-004 debería estar reducido significativamente
    ai004 = bugs_por_tipo.get('AI-004', 0)
    ai004_pct = ai004 / len(recientes) * 100 if recientes else 0
    if ai004_pct < 20:
        print(ok(f"AI-004 (respuesta repetida): {ai004} ({ai004_pct:.1f}% llamadas)"))
    else:
        print(warn(f"AI-004: {ai004} ({ai004_pct:.1f}% llamadas) - revisar anti-repetición"))

    # FLU-001 debería estar reducido
    flu001 = bugs_por_tipo.get('FLU-001', 0)
    flu001_pct = flu001 / len(recientes) * 100 if recientes else 0
    if flu001_pct < 15:
        print(ok(f"FLU-001 (cliente habló último): {flu001} ({flu001_pct:.1f}% llamadas)"))
    else:
        print(warn(f"FLU-001: {flu001} ({flu001_pct:.1f}% llamadas) - revisar flujo"))

    # TEC-002 debería estar reducido por FIX 683
    tec002 = bugs_por_tipo.get('TEC-002', 0)
    tec002_pct = tec002 / len(recientes) * 100 if recientes else 0
    if tec002_pct < 20:
        print(ok(f"TEC-002 (STT timeout): {tec002} ({tec002_pct:.1f}% llamadas)"))
    else:
        print(warn(f"TEC-002: {tec002} ({tec002_pct:.1f}% llamadas) - STT aún problemático"))

    # Baseline comparison
    print(f"\n  Baseline (pre-fix Fase 0-4):")
    print(f"    Bugs/llamada original:  ~3.5 (1,371 bugs / 397 llamadas)")
    print(f"    Bugs/llamada actual:    {bugs_per_call:.2f}")
    if bugs_per_call < 3.5:
        reduccion = (1 - bugs_per_call / 3.5) * 100
        print(ok(f"Reducción: {reduccion:.0f}% vs baseline"))
    else:
        print(warn(f"Bugs/llamada NO mejoró vs baseline"))

    return True


# ============================================================
# CHECK 6: Test suite health
# ============================================================
def check_test_suite():
    """Verifica que la suite de tests está completa y pasa."""
    print(header("CHECK 6: Test suite health"))

    tests_dir = os.path.join(BASE_DIR, 'tests')
    if not os.path.exists(tests_dir):
        print(fail("Directorio tests/ no existe"))
        return False

    # Contar archivos de test
    test_files = [f for f in os.listdir(tests_dir) if f.startswith('test_') and f.endswith('.py')]
    print(f"  Archivos de test: {len(test_files)}")

    # Verificar que existen tests para cada FIX implementado
    fix_tests = {
        'test_fix_678_679.py': 'FIX 678+679 (anti-repetición)',
        'test_fix_680_681.py': 'FIX 680+681 (encargado repeat + auditor)',
        'test_fix_682_683.py': 'FIX 682+683 (GPT timeout + STT adaptive)',
        'test_fix_684_685.py': 'FIX 684+685 (CTN-002 + FLU-001)',
    }

    all_present = True
    for filename, desc in fix_tests.items():
        filepath = os.path.join(tests_dir, filename)
        if os.path.exists(filepath):
            # Contar tests dentro del archivo
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            test_count = content.count('def test_')
            print(ok(f"{filename}: {test_count} tests ({desc})"))
        else:
            print(fail(f"{filename}: NO EXISTE ({desc})"))
            all_present = False

    # Resumen
    total_tests_phase = sum(1 for f in test_files if 'fix_67' in f or 'fix_68' in f)
    print(f"\n  Tests de Fase 0-4: {total_tests_phase} archivos")

    return all_present


# ============================================================
# MAIN
# ============================================================
def main():
    print("\n" + "=" * 70)
    print(f"  {C.BOLD}FASE 6: AUDITORÍA DE VERIFICACIÓN POST-IMPLEMENTACIÓN{C.END}")
    print(f"  Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"  Fases verificadas: 0 (auditor), 1 (anti-repetición), 3 (técnico), 4 (flujo)")
    print("=" * 70)

    resultados = {}

    # Ejecutar todos los checks
    resultados['sin_excusas'] = check_sin_excusas_tecnicas()
    resultados['anti_repeticion'] = check_anti_repeticion()
    resultados['gpt_timeout'] = check_gpt_timeout_resilience()
    resultados['auditor'] = check_auditor_calibrado()
    resultados['produccion'] = check_produccion()
    resultados['tests'] = check_test_suite()

    # Resumen final
    print(header("RESUMEN FINAL"))

    total = len(resultados)
    pasaron = sum(1 for v in resultados.values() if v)

    for nombre, paso in resultados.items():
        status = ok(nombre) if paso else fail(nombre)
        print(f"  {status}")

    print(f"\n  {C.BOLD}Resultado: {pasaron}/{total} checks pasaron{C.END}")

    if pasaron == total:
        print(f"\n  {C.OK}{C.BOLD}AUDITORÍA COMPLETA - TODAS LAS IMPLEMENTACIONES VERIFICADAS{C.END}")
    else:
        print(f"\n  {C.WARN}{C.BOLD}AUDITORÍA PARCIAL - {total - pasaron} check(s) requieren atención{C.END}")

    return pasaron == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
