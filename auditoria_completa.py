# -*- coding: utf-8 -*-
"""
AUDITORIA COMPLETA - FASE DE IMPLEMENTACION
Script maestro que ejecuta todas las auditorias y genera reporte consolidado

Ejecuta:
0. Descarga automatica de logs de todos los deploys del dia (Railway)
1. Auditoria de bugs (logs de Railway)
2. Auditoria de metricas (Google Sheets)
3. Analisis de patrones de mejora

Uso:
    python auditoria_completa.py
    python auditoria_completa.py --solo-bugs      # Solo auditoria de bugs
    python auditoria_completa.py --solo-metricas  # Solo metricas de negocio
    python auditoria_completa.py --ultimas 100    # Ultimas N llamadas
    python auditoria_completa.py --solo-descargar # Solo descarga logs sin auditoria
    python auditoria_completa.py --sin-descargar  # Auditoria sin descargar logs nuevos
    python auditoria_completa.py --fecha 2026-01-28  # Fecha especifica

Autor: Sistema Bruce W - Auditoria Automatizada
Fecha: 2026-01-28
"""

import os
import sys
import re
import json
import subprocess
import argparse
from datetime import datetime
from typing import Dict, List, Optional
from collections import Counter

# Configuracion
REPORTE_DIR = r"C:\Users\PC 1\AgenteVentas\reportes_auditoria"
LOGS_DIR = r"C:\Users\PC 1\AgenteVentas\LOGS"
RAILWAY_PATH = r"C:\Users\PC 1\AppData\Roaming\npm\railway.cmd"
CWD_RAILWAY = r"C:\Users\PC 1\AgenteVentas"

os.makedirs(REPORTE_DIR, exist_ok=True)
os.makedirs(LOGS_DIR, exist_ok=True)


def print_header(titulo: str):
    """Imprime header de seccion"""
    print("\n" + "=" * 80)
    print(f" {titulo}")
    print("=" * 80)


def print_subheader(titulo: str):
    """Imprime subheader"""
    print("\n" + "-" * 60)
    print(f" {titulo}")
    print("-" * 60)


# =========================================================================
# PASO 0: DESCARGA AUTOMATICA DE LOGS DE RAILWAY
# =========================================================================

def obtener_deploys_del_dia(fecha: str = None) -> List[Dict]:
    """Obtiene lista de deploys del dia desde Railway"""
    fecha = fecha or datetime.now().strftime("%Y-%m-%d")

    print(f"\n  Consultando deploys del {fecha}...")

    try:
        resultado = subprocess.run(
            [RAILWAY_PATH, "deployment", "list"],
            capture_output=True,
            timeout=60,
            cwd=CWD_RAILWAY
        )

        output = resultado.stdout.decode('utf-8', errors='replace')

        deploys = []
        for linea in output.split('\n'):
            match = re.search(
                r'([a-f0-9-]{36})\s*\|\s*(SUCCESS|REMOVED|BUILDING|FAILED)\s*\|\s*(\d{4}-\d{2}-\d{2})\s+(\d{2}:\d{2}:\d{2})',
                linea
            )
            if match:
                deploy_id = match.group(1)
                status = match.group(2)
                fecha_deploy = match.group(3)
                hora_deploy = match.group(4)

                if fecha_deploy == fecha:
                    deploys.append({
                        'id': deploy_id,
                        'status': status,
                        'fecha': fecha_deploy,
                        'hora': hora_deploy
                    })

        print(f"  Encontrados {len(deploys)} deploys del {fecha}")
        return deploys

    except subprocess.TimeoutExpired:
        print("  [ERROR] Timeout obteniendo lista de deploys")
        return []
    except Exception as e:
        print(f"  [ERROR] Error obteniendo deploys: {e}")
        return []


def descargar_logs_deploy(deploy: Dict, fecha_corta: str, num_lineas: int = 5000) -> Optional[str]:
    """Descarga logs de un deploy especifico"""
    deploy_id = deploy['id']
    hora = deploy['hora'].replace(':', '-')

    nombre_archivo = f"{fecha_corta}_{hora}_{deploy_id[:8]}.txt"
    ruta_archivo = os.path.join(LOGS_DIR, nombre_archivo)

    if os.path.exists(ruta_archivo):
        size = os.path.getsize(ruta_archivo)
        if size > 1000:  # Solo skip si tiene contenido
            print(f"    [SKIP] {nombre_archivo} ya existe ({size//1024}KB)")
            return ruta_archivo

    print(f"    Descargando {nombre_archivo}...")

    try:
        resultado = subprocess.run(
            [RAILWAY_PATH, "logs", deploy_id, "-n", str(num_lineas)],
            capture_output=True,
            timeout=180,
            cwd=CWD_RAILWAY
        )

        logs = resultado.stdout.decode('utf-8', errors='replace')

        with open(ruta_archivo, 'w', encoding='utf-8') as f:
            f.write(f"# Deploy: {deploy_id}\n")
            f.write(f"# Fecha: {deploy['fecha']} {deploy['hora']}\n")
            f.write(f"# Status: {deploy['status']}\n")
            f.write(f"# Descargado: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"{'='*60}\n\n")
            f.write(logs)

        lineas = len(logs.split('\n'))
        print(f"    [OK] {lineas} lineas guardadas")
        return ruta_archivo

    except subprocess.TimeoutExpired:
        print(f"    [ERROR] Timeout descargando {deploy_id[:8]}")
        return None
    except Exception as e:
        print(f"    [ERROR] Error: {e}")
        return None


def descargar_logs_del_dia(fecha: str = None) -> Dict:
    """Descarga automaticamente todos los logs del dia desde Railway"""
    print_header("0. DESCARGA AUTOMATICA DE LOGS (Railway)")

    fecha = fecha or datetime.now().strftime("%Y-%m-%d")
    fecha_corta = datetime.strptime(fecha, "%Y-%m-%d").strftime("%d_%m")

    deploys = obtener_deploys_del_dia(fecha)

    if not deploys:
        print("\n  [WARN] No se encontraron deploys para descargar")
        return {'exito': True, 'archivos': 0, 'deploys': 0}

    archivos_descargados = []
    bruce_ids_total = set()

    for deploy in deploys:
        archivo = descargar_logs_deploy(deploy, fecha_corta)
        if archivo:
            archivos_descargados.append(archivo)

            # Contar BRUCE IDs en el archivo
            try:
                with open(archivo, 'r', encoding='utf-8', errors='replace') as f:
                    contenido = f.read()
                    bruce_ids = set(re.findall(r'BRUCE(\d+)', contenido))
                    bruce_ids_total.update(bruce_ids)
            except:
                pass

    print(f"\n  RESUMEN DESCARGA:")
    print(f"    Deploys del dia: {len(deploys)}")
    print(f"    Archivos descargados: {len(archivos_descargados)}")
    print(f"    BRUCE IDs encontrados: {len(bruce_ids_total)}")

    if bruce_ids_total:
        ids_ordenados = sorted([int(x) for x in bruce_ids_total])
        print(f"    Rango: BRUCE{ids_ordenados[0]} - BRUCE{ids_ordenados[-1]}")

    return {
        'exito': True,
        'archivos': len(archivos_descargados),
        'deploys': len(deploys),
        'bruce_ids': len(bruce_ids_total),
        'fecha': fecha
    }


def ejecutar_auditoria_bugs(forzar: bool = False) -> Dict:
    """Ejecuta auditoria de bugs en logs"""
    print_header("1. AUDITORIA DE BUGS (Logs Railway)")

    try:
        from auditoria_diaria_bugs import AuditoriaDiariaBugs

        auditoria = AuditoriaDiariaBugs()
        resultado = auditoria.ejecutar_auditoria(forzar=forzar)

        return {
            'exito': True,
            'archivos_analizados': resultado.get('archivos_analizados', 0),
            'bugs_detectados': resultado.get('bugs_detectados', 0),
            'bugs': resultado.get('bugs', [])
        }
    except ImportError as e:
        print(f"  Error importando modulo: {e}")
        return {'exito': False, 'error': str(e)}
    except Exception as e:
        print(f"  Error ejecutando auditoria: {e}")
        return {'exito': False, 'error': str(e)}


def ejecutar_auditoria_metricas(ultimas: int = None) -> Dict:
    """Ejecuta auditoria de metricas de negocio usando auto_mejora_bruce"""
    print_header("2. AUDITORIA DE METRICAS (Google Sheets)")

    try:
        from auto_mejora_bruce import AutoMejoraBruce

        auto_mejora = AutoMejoraBruce()
        stats = auto_mejora._obtener_estadisticas_semana()

        if not stats:
            print("  No hay datos suficientes")
            return {'exito': True, 'total': 0}

        total = stats.get('total_llamadas', 0)
        aprobados = stats.get('aprobados', 0)
        conversion = stats.get('tasa_conversion', 0)
        whatsapps = stats.get('whatsapps_capturados', 0)

        # Calcular interes bajo
        niveles = stats.get('niveles_interes', [])
        interes_bajo_count = sum(1 for n in niveles if 'bajo' in n.lower())
        interes_bajo_pct = (interes_bajo_count / total * 100) if total > 0 else 0

        print(f"\n  METRICAS PRINCIPALES:")
        print(f"    Total llamadas: {total}")
        print(f"    Aprobadas: {aprobados}")
        print(f"    Tasa conversion: {conversion:.2f}%")
        print(f"    WhatsApps capturados: {whatsapps}")
        print(f"    Interes bajo: {interes_bajo_pct:.1f}%")
        print(f"    Interes promedio: {stats.get('interes_promedio', 'N/A')}")
        print(f"    Animo predominante: {stats.get('animo_predominante', 'N/A')}")

        return {
            'exito': True,
            'total': total,
            'aprobados': aprobados,
            'conversion': conversion,
            'whatsapps': whatsapps,
            'interes_bajo_pct': interes_bajo_pct,
            'interes_promedio': stats.get('interes_promedio', 'N/A'),
            'animo_predominante': stats.get('animo_predominante', 'N/A')
        }

    except ImportError as e:
        print(f"  Error importando modulo: {e}")
        return {'exito': False, 'error': str(e)}
    except Exception as e:
        print(f"  Error ejecutando auditoria: {e}")
        return {'exito': False, 'error': str(e)}


def ejecutar_analisis_patrones() -> Dict:
    """Ejecuta analisis de patrones de mejora"""
    print_header("3. ANALISIS DE PATRONES (Auto-Mejora)")

    try:
        from auto_mejora_bruce import AutoMejoraBruce

        auto_mejora = AutoMejoraBruce()

        # Obtener estadisticas sin el analisis GPT (que es interactivo)
        print("  Obteniendo estadisticas de la semana...")
        stats = auto_mejora._obtener_estadisticas_semana()

        if not stats:
            print("  No hay datos suficientes")
            return {'exito': True, 'datos': None}

        print(f"\n  ESTADISTICAS SEMANALES:")
        print(f"    Total llamadas: {stats.get('total_llamadas', 0)}")
        print(f"    Tasa conversion: {stats.get('tasa_conversion', 0):.2f}%")
        print(f"    WhatsApps: {stats.get('whatsapps_capturados', 0)}")
        print(f"    Interes promedio: {stats.get('interes_promedio', 'N/A')}")
        print(f"    Animo predominante: {stats.get('animo_predominante', 'N/A')}")

        return {
            'exito': True,
            'stats': stats
        }

    except ImportError as e:
        print(f"  Error importando modulo: {e}")
        return {'exito': False, 'error': str(e)}
    except Exception as e:
        print(f"  Error ejecutando analisis: {e}")
        return {'exito': False, 'error': str(e)}


def generar_reporte_consolidado(resultados: Dict) -> str:
    """Genera reporte consolidado en JSON"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    reporte_file = os.path.join(REPORTE_DIR, f"auditoria_completa_{timestamp}.json")

    reporte = {
        'fecha': datetime.now().isoformat(),
        'tipo': 'AUDITORIA_COMPLETA',
        'resultados': resultados
    }

    with open(reporte_file, 'w', encoding='utf-8') as f:
        json.dump(reporte, f, indent=2, ensure_ascii=False)

    return reporte_file


def imprimir_resumen_ejecutivo(resultados: Dict):
    """Imprime resumen ejecutivo de la auditoria"""
    print_header("RESUMEN EJECUTIVO")

    # Bugs
    bugs = resultados.get('bugs', {})
    if bugs.get('exito'):
        bugs_count = bugs.get('bugs_detectados', 0)
        emoji = '[CRITICO]' if bugs_count > 10 else '[ALERTA]' if bugs_count > 0 else '[OK]'
        print(f"\n  {emoji} BUGS TECNICOS: {bugs_count} detectados")
        if bugs_count > 0:
            # Agrupar por tipo
            from collections import Counter
            tipos = Counter([b.get('tipo', 'OTRO') for b in bugs.get('bugs', [])])
            for tipo, count in tipos.most_common(3):
                print(f"      - {tipo}: {count}")

        # Metricas avanzadas de logs
        metricas_bugs = bugs.get('metricas', {})
        if metricas_bugs:
            # Latencia
            latencias = metricas_bugs.get('latencias', [])
            if latencias:
                lat_prom = sum(latencias) / len(latencias)
                emoji_lat = '[OK]' if lat_prom <= 2.5 else '[ALERTA]' if lat_prom <= 4 else '[CRITICO]'
                print(f"\n  {emoji_lat} LATENCIA PROMEDIO: {lat_prom:.2f}s")

            # IVR vs Humanos
            ivr = metricas_bugs.get('ivr_count', 0)
            humanos = metricas_bugs.get('humanos_count', 0)
            if ivr + humanos > 0:
                tasa_ivr = (ivr / (ivr + humanos) * 100)
                emoji_ivr = '[OK]' if tasa_ivr <= 20 else '[ALERTA]' if tasa_ivr <= 35 else '[CRITICO]'
                print(f"\n  {emoji_ivr} TASA IVR: {tasa_ivr:.1f}% ({ivr} de {ivr+humanos})")

            # Llamadas abandonadas
            abandonadas = metricas_bugs.get('abandonadas', 0)
            if abandonadas > 0:
                print(f"\n  [ALERTA] LLAMADAS ABANDONADAS: {abandonadas}")

            # Clientes frustrados
            frustrados = metricas_bugs.get('frustrados', 0)
            if frustrados > 0:
                print(f"\n  [ALERTA] CLIENTES FRUSTRADOS: {frustrados}")

    else:
        print(f"\n  [!]  BUGS TECNICOS: Error en auditoria - {bugs.get('error', 'desconocido')}")

    # Metricas
    metricas = resultados.get('metricas', {})
    if metricas.get('exito') and metricas.get('total', 0) > 0:
        conversion = metricas.get('conversion', 0)
        emoji = '[OK]' if conversion >= 10 else '[ALERTA]' if conversion >= 5 else '[CRITICO]'
        print(f"\n  {emoji} CONVERSION: {conversion:.2f}%")
        print(f"      Total llamadas: {metricas.get('total', 0)}")
        print(f"      Aprobadas: {metricas.get('aprobados', 0)}")
        print(f"      WhatsApps: {metricas.get('whatsapps', 0)}")

        interes_bajo = metricas.get('interes_bajo_pct', 0)
        emoji2 = '[OK]' if interes_bajo <= 30 else '[ALERTA]' if interes_bajo <= 50 else '[CRITICO]'
        print(f"\n  {emoji2} INTERES BAJO: {interes_bajo:.1f}%")
    else:
        print(f"\n  [!]  METRICAS: Sin datos o error")

    # Patrones
    patrones = resultados.get('patrones', {})
    if patrones.get('exito') and patrones.get('stats'):
        stats = patrones['stats']
        print(f"\n  [STATS] PATRONES SEMANALES:")
        print(f"      Llamadas semana: {stats.get('total_llamadas', 0)}")
        print(f"      Interes promedio: {stats.get('interes_promedio', 'N/A')}")

    # Recomendaciones
    print_subheader("RECOMENDACIONES")

    recomendaciones = []

    if bugs.get('exito') and bugs.get('bugs_detectados', 0) > 5:
        recomendaciones.append("- Revisar bugs criticos en logs (timeouts, errores API)")

    # Recomendaciones basadas en metricas avanzadas
    metricas_bugs = bugs.get('metricas', {}) if bugs.get('exito') else {}
    if metricas_bugs:
        latencias = metricas_bugs.get('latencias', [])
        if latencias and (sum(latencias) / len(latencias)) > 3.5:
            recomendaciones.append("- Latencia muy alta (>3.5s) - Revisar ElevenLabs/Deepgram")

        ivr = metricas_bugs.get('ivr_count', 0)
        humanos = metricas_bugs.get('humanos_count', 0)
        if ivr + humanos > 0 and (ivr / (ivr + humanos) * 100) > 30:
            recomendaciones.append("- Tasa IVR alta (>30%) - Mejorar deteccion o calidad de leads")

        if metricas_bugs.get('abandonadas', 0) > 3:
            recomendaciones.append("- Llamadas abandonadas - Revisar saludo inicial")

        if metricas_bugs.get('frustrados', 0) > 0:
            recomendaciones.append("- Clientes frustrados detectados - Revisar conversaciones")

    if metricas.get('exito'):
        if metricas.get('conversion', 0) < 5:
            recomendaciones.append("- Conversion muy baja (<5%) - Revisar script de apertura")
        if metricas.get('interes_bajo_pct', 0) > 50:
            recomendaciones.append("- Interes bajo alto (>50%) - Mejorar propuesta de valor")

    if not recomendaciones:
        recomendaciones.append("- Sistema funcionando dentro de parametros normales")

    for rec in recomendaciones:
        print(f"  {rec}")


def main():
    parser = argparse.ArgumentParser(description='Auditoria completa - Fase de implementacion')
    parser.add_argument('--solo-bugs', action='store_true',
                       help='Solo ejecutar auditoria de bugs')
    parser.add_argument('--solo-metricas', action='store_true',
                       help='Solo ejecutar auditoria de metricas')
    parser.add_argument('--solo-descargar', action='store_true',
                       help='Solo descargar logs, sin auditoria')
    parser.add_argument('--sin-descargar', action='store_true',
                       help='Ejecutar auditoria sin descargar logs nuevos')
    parser.add_argument('--fecha', type=str, default=None,
                       help='Fecha a auditar (YYYY-MM-DD), por defecto hoy')
    parser.add_argument('--ultimas', type=int,
                       help='Analizar ultimas N llamadas')
    parser.add_argument('--forzar', action='store_true',
                       help='Forzar re-analisis de logs')

    args = parser.parse_args()

    fecha = args.fecha or datetime.now().strftime("%Y-%m-%d")

    print("\n" + "#" * 80)
    print(" " * 20 + "AUDITORIA COMPLETA - BRUCE W")
    print(" " * 15 + f"Fecha auditoria: {fecha}")
    print(" " * 15 + f"Ejecutado: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("#" * 80)

    resultados = {}

    # 0. Descarga automatica de logs (si no se indica --sin-descargar)
    if not args.sin_descargar:
        resultados['descarga'] = descargar_logs_del_dia(fecha=fecha)

        if args.solo_descargar:
            print("\n" + "=" * 80)
            print(" DESCARGA COMPLETADA (--solo-descargar)")
            print("=" * 80)
            return 0

    # 1. Auditoria de bugs
    if not args.solo_metricas:
        resultados['bugs'] = ejecutar_auditoria_bugs(forzar=args.forzar)

    # 2. Auditoria de metricas
    if not args.solo_bugs:
        resultados['metricas'] = ejecutar_auditoria_metricas(ultimas=args.ultimas)

    # 3. Analisis de patrones (solo si se ejecutan ambas)
    if not args.solo_bugs and not args.solo_metricas:
        resultados['patrones'] = ejecutar_analisis_patrones()

    # Generar reporte
    reporte_file = generar_reporte_consolidado(resultados)

    # Imprimir resumen ejecutivo
    imprimir_resumen_ejecutivo(resultados)

    print("\n" + "=" * 80)
    print(" AUDITORIA COMPLETADA")
    print("=" * 80)
    print(f"\n  Reporte guardado: {reporte_file}")

    # Determinar exit code
    bugs_count = resultados.get('bugs', {}).get('bugs_detectados', 0)
    conversion = resultados.get('metricas', {}).get('conversion', 100)

    if bugs_count > 20 or conversion < 3:
        print("\n  [!]  ATENCION: Se detectaron problemas criticos")
        return 2
    elif bugs_count > 5 or conversion < 5:
        print("\n  [i]  Se detectaron algunos problemas a revisar")
        return 1
    else:
        print("\n  [OK] Sistema funcionando correctamente")
        return 0


if __name__ == '__main__':
    sys.exit(main())
