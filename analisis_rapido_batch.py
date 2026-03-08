#!/usr/bin/env python3
"""
ANÁLISIS RÁPIDO DE BATCH - FASE DE TESTEO
Ejecutar después de cada batch de 50-100 llamadas para validación inmediata

Uso:
    python analisis_rapido_batch.py --batch 50
    python analisis_rapido_batch.py --batch 100
    python analisis_rapido_batch.py --ultimas 50
"""

import sys
import argparse
from datetime import datetime, timedelta
from resultados_sheets_adapter import ResultadosSheetsAdapter
from collections import Counter

# BASELINE (sistema actual antes de mejoras)
BASELINE_CONVERSION = 5.17
BASELINE_INTERES_BAJO = 57.8
BASELINE_DURACION_PROMEDIO = 120  # segundos estimado

# OBJETIVOS FASE DE PRUEBA
OBJETIVO_CONVERSION_MIN = 8.0   # Mínimo aceptable
OBJETIVO_CONVERSION_BUENO = 10.0  # Bueno
OBJETIVO_CONVERSION_EXCELENTE = 12.0  # Excelente

OBJETIVO_INTERES_BAJO_MAX = 35.0  # Máximo aceptable
OBJETIVO_INTERES_BAJO_BUENO = 25.0  # Bueno
OBJETIVO_INTERES_BAJO_EXCELENTE = 20.0  # Excelente


def obtener_ultimas_llamadas(num_llamadas=50):
    """Obtiene las últimas N llamadas desde Google Sheets"""
    print(f"\n Obteniendo últimas {num_llamadas} llamadas de Google Sheets...")

    adapter = ResultadosSheetsAdapter()
    todas_las_filas = adapter.obtener_todas_las_filas()

    # Ordenar por timestamp descendente (más recientes primero)
    filas_ordenadas = sorted(
        todas_las_filas,
        key=lambda x: x.get('timestamp', ''),
        reverse=True
    )

    # Tomar las últimas N
    ultimas = filas_ordenadas[:num_llamadas]

    print(f" Obtenidas {len(ultimas)} llamadas")
    return ultimas


def calcular_metricas(llamadas):
    """Calcula métricas del batch"""
    total = len(llamadas)

    if total == 0:
        return None

    # Contadores
    aprobados = 0
    negados = 0
    transferidos = 0
    no_contesta = 0
    ivr = 0

    interes_bajo = 0
    interes_medio = 0
    interes_alto = 0

    duraciones = []
    resultados = []
    razones_rechazo = []

    for llamada in llamadas:
        resultado = llamada.get('resultado', '').upper()
        interes = llamada.get('interes', '').lower()
        duracion = llamada.get('duracion_llamada', 0)

        resultados.append(resultado)

        # Resultado
        if resultado == 'APROBADO':
            aprobados += 1
        elif resultado == 'NEGADO':
            negados += 1
            # Intentar extraer razón de rechazo
            comentarios = llamada.get('comentarios_adicionales', '').lower()
            if 'no interesa' in comentarios or 'no le interesa' in comentarios:
                razones_rechazo.append('No le interesa')
            elif 'proveedor' in comentarios:
                razones_rechazo.append('Ya tiene proveedor')
            elif 'caro' in comentarios or 'precio' in comentarios:
                razones_rechazo.append('Precio alto')
            else:
                razones_rechazo.append('Otro')
        elif resultado == 'TRANSFERIDO':
            transferidos += 1
        elif resultado == 'NO CONTESTA':
            no_contesta += 1
        elif resultado == 'IVR':
            ivr += 1

        # Interés
        if 'bajo' in interes:
            interes_bajo += 1
        elif 'medio' in interes:
            interes_medio += 1
        elif 'alto' in interes:
            interes_alto += 1

        # Duración
        if duracion and duracion > 0:
            duraciones.append(duracion)

    # Calcular porcentajes
    conversion = (aprobados / total) * 100 if total > 0 else 0
    tasa_interes_bajo = (interes_bajo / total) * 100 if total > 0 else 0
    duracion_promedio = sum(duraciones) / len(duraciones) if duraciones else 0

    # Top razones de rechazo
    contador_razones = Counter(razones_rechazo)
    top_razones = contador_razones.most_common(3)

    return {
        'total': total,
        'aprobados': aprobados,
        'negados': negados,
        'transferidos': transferidos,
        'no_contesta': no_contesta,
        'ivr': ivr,
        'conversion': conversion,
        'interes_bajo': interes_bajo,
        'interes_medio': interes_medio,
        'interes_alto': interes_alto,
        'tasa_interes_bajo': tasa_interes_bajo,
        'duracion_promedio': duracion_promedio,
        'top_razones': top_razones
    }


def evaluar_metricas(metricas):
    """Evalúa si las métricas son buenas y retorna decisión"""
    conversion = metricas['conversion']
    interes_bajo = metricas['tasa_interes_bajo']

    # Evaluación de conversión
    if conversion >= OBJETIVO_CONVERSION_EXCELENTE:
        eval_conversion = 'EXCELENTE'
        emoji_conv = '🎉'
    elif conversion >= OBJETIVO_CONVERSION_BUENO:
        eval_conversion = 'BUENO'
        emoji_conv = '✅'
    elif conversion >= OBJETIVO_CONVERSION_MIN:
        eval_conversion = 'ACEPTABLE'
        emoji_conv = '⚠️'
    else:
        eval_conversion = 'INSUFICIENTE'
        emoji_conv = '❌'

    # Evaluación de interés bajo
    if interes_bajo <= OBJETIVO_INTERES_BAJO_EXCELENTE:
        eval_interes = 'EXCELENTE'
        emoji_int = '🎉'
    elif interes_bajo <= OBJETIVO_INTERES_BAJO_BUENO:
        eval_interes = 'BUENO'
        emoji_int = '✅'
    elif interes_bajo <= OBJETIVO_INTERES_BAJO_MAX:
        eval_interes = 'ACEPTABLE'
        emoji_int = '⚠️'
    else:
        eval_interes = 'MALO'
        emoji_int = '❌'

    # Decisión global
    if conversion >= OBJETIVO_CONVERSION_BUENO and interes_bajo <= OBJETIVO_INTERES_BAJO_BUENO:
        decision = 'CONTINUAR'
        emoji_decision = '🚀'
        mensaje = 'Batch exitoso - Escalar al siguiente nivel'
    elif conversion >= OBJETIVO_CONVERSION_MIN and interes_bajo <= OBJETIVO_INTERES_BAJO_MAX:
        decision = 'REVISAR'
        emoji_decision = '🔍'
        mensaje = 'Mejora vs baseline pero no alcanza objetivo - Revisar 5-10 llamadas'
    else:
        decision = 'DETENER'
        emoji_decision = '🛑'
        mensaje = 'No alcanza mínimos - Investigar problema antes de continuar'

    return {
        'eval_conversion': eval_conversion,
        'emoji_conv': emoji_conv,
        'eval_interes': eval_interes,
        'emoji_int': emoji_int,
        'decision': decision,
        'emoji_decision': emoji_decision,
        'mensaje': mensaje
    }


def imprimir_reporte(metricas, evaluacion):
    """Imprime reporte visual del batch"""
    print("\n" + "="*80)
    print(" REPORTE RÁPIDO DE BATCH - FASE DE TESTEO")
    print("="*80)

    # Métricas principales
    print("\n METRICAS PRINCIPALES:")
    print("-"*80)

    # Conversión
    delta_conv = metricas['conversion'] - BASELINE_CONVERSION
    signo_conv = '+' if delta_conv > 0 else ''
    print(f"\n  {evaluacion['emoji_conv']} Conversión: {metricas['conversion']:.1f}% ({signo_conv}{delta_conv:.1f}% vs baseline {BASELINE_CONVERSION}%)")
    print(f"     Evaluación: {evaluacion['eval_conversion']}")
    print(f"     WhatsApps: {metricas['aprobados']} de {metricas['total']} llamadas")

    # Interés Bajo
    delta_int = metricas['tasa_interes_bajo'] - BASELINE_INTERES_BAJO
    signo_int = '+' if delta_int > 0 else ''
    print(f"\n  {evaluacion['emoji_int']} Interés Bajo: {metricas['tasa_interes_bajo']:.1f}% ({signo_int}{delta_int:.1f}% vs baseline {BASELINE_INTERES_BAJO}%)")
    print(f"     Evaluación: {evaluacion['eval_interes']}")

    # Distribución de resultados
    print("\n DISTRIBUCION DE RESULTADOS:")
    print("-"*80)
    print(f"  APROBADO:     {metricas['aprobados']:3d} ({metricas['aprobados']/metricas['total']*100:5.1f}%)")
    print(f"  NEGADO:       {metricas['negados']:3d} ({metricas['negados']/metricas['total']*100:5.1f}%)")
    print(f"  TRANSFERIDO:  {metricas['transferidos']:3d} ({metricas['transferidos']/metricas['total']*100:5.1f}%)")
    print(f"  NO CONTESTA:  {metricas['no_contesta']:3d} ({metricas['no_contesta']/metricas['total']*100:5.1f}%)")
    print(f"  IVR:          {metricas['ivr']:3d} ({metricas['ivr']/metricas['total']*100:5.1f}%)")

    # Nivel de interés
    print("\n NIVEL DE INTERES:")
    print("-"*80)
    print(f"  BAJO:   {metricas['interes_bajo']:3d} ({metricas['tasa_interes_bajo']:5.1f}%)")
    print(f"  MEDIO:  {metricas['interes_medio']:3d} ({metricas['interes_medio']/metricas['total']*100:5.1f}%)")
    print(f"  ALTO:   {metricas['interes_alto']:3d} ({metricas['interes_alto']/metricas['total']*100:5.1f}%)")

    # Duración promedio
    if metricas['duracion_promedio'] > 0:
        print(f"\n DURACION PROMEDIO: {metricas['duracion_promedio']:.0f} segundos")

    # Top razones de rechazo
    if metricas['top_razones']:
        print("\n TOP RAZONES DE RECHAZO:")
        print("-"*80)
        for razon, count in metricas['top_razones']:
            print(f"  {razon}: {count}")

    # Decisión
    print("\n" + "="*80)
    print(f" {evaluacion['emoji_decision']} DECISION: {evaluacion['decision']}")
    print("="*80)
    print(f"\n  {evaluacion['mensaje']}")
    print("\n" + "="*80)

    # Siguientes pasos
    print("\n SIGUIENTES PASOS:")
    print("-"*80)
    if evaluacion['decision'] == 'CONTINUAR':
        print("  1. ✅ Batch exitoso - Métricas superan objetivo")
        print("  2. 🚀 Escalar al siguiente batch (50-100 llamadas más)")
        print("  3. 📊 Mantener monitoreo de estabilidad")
    elif evaluacion['decision'] == 'REVISAR':
        print("  1. ⚠️ Mejora parcial vs baseline")
        print("  2. 🔍 Revisar manualmente 5-10 llamadas NEGADAS")
        print("  3. 🎯 Identificar patrón de rechazo")
        print("  4. 🔧 Ajustar si es necesario, luego continuar")
    else:  # DETENER
        print("  1. ❌ Métricas por debajo del mínimo aceptable")
        print("  2. 🛑 NO ejecutar más batches hasta investigar")
        print("  3. 🔍 Revisar:")
        print("     - ¿El importador generó leads de calidad?")
        print("     - ¿Hubo errores técnicos en las llamadas?")
        print("     - ¿Algún cambio en el script de Bruce?")
        print("  4. 🔧 Corregir problema antes de continuar")

    print("\n")


def main():
    parser = argparse.ArgumentParser(description='Análisis rápido de batch para fase de testeo')
    parser.add_argument('--batch', type=int, help='Número de llamadas del batch (ej: 50, 100)')
    parser.add_argument('--ultimas', type=int, help='Analizar las últimas N llamadas')

    args = parser.parse_args()

    # Determinar cuántas llamadas analizar
    if args.batch:
        num_llamadas = args.batch
    elif args.ultimas:
        num_llamadas = args.ultimas
    else:
        num_llamadas = 50  # Default

    try:
        # Obtener datos
        llamadas = obtener_ultimas_llamadas(num_llamadas)

        if not llamadas:
            print("\n ❌ ERROR: No se encontraron llamadas")
            return 1

        # Calcular métricas
        metricas = calcular_metricas(llamadas)

        if not metricas:
            print("\n ❌ ERROR: No se pudieron calcular métricas")
            return 1

        # Evaluar
        evaluacion = evaluar_metricas(metricas)

        # Imprimir reporte
        imprimir_reporte(metricas, evaluacion)

        # Return code según decisión
        if evaluacion['decision'] == 'CONTINUAR':
            return 0  # Success
        elif evaluacion['decision'] == 'REVISAR':
            return 2  # Warning
        else:  # DETENER
            return 3  # Error

    except Exception as e:
        print(f"\n ❌ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
