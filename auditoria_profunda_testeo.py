#!/usr/bin/env python3
"""
AUDITORÍA PROFUNDA - FASE DE TESTEO
Análisis completo similar a Auditoría W04 pero para validación de mejoras

Uso:
    python auditoria_profunda_testeo.py --ultimas 200
    python auditoria_profunda_testeo.py --desde "2026-01-24"
"""

import sys
import argparse
from datetime import datetime, timedelta
from resultados_sheets_adapter import ResultadosSheetsAdapter
from collections import Counter, defaultdict
import re

# BASELINE (sistema actual antes de mejoras)
BASELINE_CONVERSION = 5.17
BASELINE_INTERES_BAJO = 57.8


def obtener_llamadas(ultimas=None, desde=None):
    """Obtiene llamadas desde Google Sheets"""
    print(f"\n Obteniendo llamadas de Google Sheets...")

    adapter = ResultadosSheetsAdapter()
    todas_las_filas = adapter.obtener_todas_las_filas()

    if ultimas:
        # Ordenar por timestamp y tomar las últimas N
        filas_ordenadas = sorted(
            todas_las_filas,
            key=lambda x: x.get('timestamp', ''),
            reverse=True
        )
        llamadas = filas_ordenadas[:ultimas]
        print(f" Obtenidas últimas {len(llamadas)} llamadas")
    elif desde:
        # Filtrar por fecha
        fecha_desde = datetime.strptime(desde, "%Y-%m-%d")
        llamadas = [
            f for f in todas_las_filas
            if f.get('timestamp') and datetime.fromisoformat(f['timestamp'].replace('Z', '+00:00')) >= fecha_desde
        ]
        print(f" Obtenidas {len(llamadas)} llamadas desde {desde}")
    else:
        # Últimas 7 días por default
        hace_7_dias = datetime.now() - timedelta(days=7)
        llamadas = [
            f for f in todas_las_filas
            if f.get('timestamp') and datetime.fromisoformat(f['timestamp'].replace('Z', '+00:00')) >= hace_7_dias
        ]
        print(f" Obtenidas {len(llamadas)} llamadas de últimos 7 días")

    return llamadas


def analizar_resultados(llamadas):
    """Análisis detallado de resultados"""
    total = len(llamadas)

    resultados = {
        'APROBADO': 0,
        'NEGADO': 0,
        'TRANSFERIDO': 0,
        'NO CONTESTA': 0,
        'IVR': 0,
        'OTRO': 0
    }

    interes = {
        'BAJO': 0,
        'MEDIO': 0,
        'ALTO': 0,
        'DESCONOCIDO': 0
    }

    estado_animo = {
        'NEUTRAL': 0,
        'POSITIVO': 0,
        'NEGATIVO': 0,
        'APURADO': 0,
        'DESCONOCIDO': 0
    }

    razones_rechazo = []
    categorias_negocio = []
    ciudades = []
    whatsapps_capturados = []
    correos_capturados = []
    duraciones = []

    # Análisis por día
    llamadas_por_dia = defaultdict(int)
    aprobados_por_dia = defaultdict(int)

    for llamada in llamadas:
        # Resultado
        resultado = llamada.get('resultado', 'OTRO').upper()
        resultados[resultado] = resultados.get(resultado, 0) + 1

        # Interés
        nivel_interes = llamada.get('interes', 'DESCONOCIDO').upper()
        if 'BAJO' in nivel_interes:
            interes['BAJO'] += 1
        elif 'MEDIO' in nivel_interes:
            interes['MEDIO'] += 1
        elif 'ALTO' in nivel_interes:
            interes['ALTO'] += 1
        else:
            interes['DESCONOCIDO'] += 1

        # Estado de ánimo
        animo = llamada.get('estado_animo', 'DESCONOCIDO').upper()
        if 'NEUTRAL' in animo:
            estado_animo['NEUTRAL'] += 1
        elif 'POSITIVO' in animo:
            estado_animo['POSITIVO'] += 1
        elif 'NEGATIVO' in animo:
            estado_animo['NEGATIVO'] += 1
        elif 'APURADO' in animo or 'OCUPADO' in animo:
            estado_animo['APURADO'] += 1
        else:
            estado_animo['DESCONOCIDO'] += 1

        # Razones de rechazo (si fue negado)
        if resultado == 'NEGADO':
            comentarios = llamada.get('comentarios_adicionales', '').lower()
            if 'no interesa' in comentarios or 'no le interesa' in comentarios:
                razones_rechazo.append('No le interesa')
            elif 'proveedor' in comentarios or 'ya tengo' in comentarios:
                razones_rechazo.append('Ya tiene proveedor')
            elif 'caro' in comentarios or 'precio' in comentarios:
                razones_rechazo.append('Precio alto')
            elif 'ocupado' in comentarios or 'apurado' in comentarios:
                razones_rechazo.append('Ocupado/No es momento')
            elif 'encargado' in comentarios:
                razones_rechazo.append('Encargado no disponible')
            elif 'cerrado' in comentarios or 'ya no' in comentarios:
                razones_rechazo.append('Negocio cerrado')
            else:
                razones_rechazo.append('Otro/No especificado')

        # WhatsApps y correos
        whatsapp = llamada.get('whatsapp', '')
        if whatsapp and whatsapp != 'No capturado':
            whatsapps_capturados.append(whatsapp)

        correo = llamada.get('correo', '')
        if correo and correo != 'No capturado':
            correos_capturados.append(correo)

        # Categoría de negocio
        categoria = llamada.get('categoria_negocio', 'Desconocido')
        if categoria and categoria != 'Desconocido':
            categorias_negocio.append(categoria)

        # Ciudad
        ciudad = llamada.get('ciudad', 'Desconocido')
        if ciudad and ciudad != 'Desconocido':
            ciudades.append(ciudad)

        # Duración
        duracion = llamada.get('duracion_llamada', 0)
        if duracion and duracion > 0:
            duraciones.append(duracion)

        # Por día
        timestamp = llamada.get('timestamp', '')
        if timestamp:
            try:
                fecha = datetime.fromisoformat(timestamp.replace('Z', '+00:00')).date()
                fecha_str = fecha.strftime('%Y-%m-%d')
                llamadas_por_dia[fecha_str] += 1
                if resultado == 'APROBADO':
                    aprobados_por_dia[fecha_str] += 1
            except:
                pass

    # Calcular métricas
    conversion = (resultados['APROBADO'] / total * 100) if total > 0 else 0
    tasa_interes_bajo = (interes['BAJO'] / total * 100) if total > 0 else 0
    duracion_promedio = sum(duraciones) / len(duraciones) if duraciones else 0

    # Top categorías y razones
    contador_razones = Counter(razones_rechazo)
    contador_categorias = Counter(categorias_negocio)
    contador_ciudades = Counter(ciudades)

    return {
        'total': total,
        'resultados': resultados,
        'interes': interes,
        'estado_animo': estado_animo,
        'conversion': conversion,
        'tasa_interes_bajo': tasa_interes_bajo,
        'duracion_promedio': duracion_promedio,
        'whatsapps': len(whatsapps_capturados),
        'correos': len(correos_capturados),
        'top_razones_rechazo': contador_razones.most_common(5),
        'top_categorias': contador_categorias.most_common(5),
        'top_ciudades': contador_ciudades.most_common(3),
        'llamadas_por_dia': dict(sorted(llamadas_por_dia.items())),
        'aprobados_por_dia': dict(sorted(aprobados_por_dia.items()))
    }


def analizar_patrones_especificos(llamadas):
    """Análisis de patrones específicos para fase de testeo"""
    print("\n Analizando patrones específicos...")

    # 1. ¿Mejoraron las categorías de negocio?
    categorias_irrelevantes = ['Audio', 'Seguridad', 'Empaques', 'Envíos']
    negocios_irrelevantes = 0
    negocios_cerrados = 0
    negocios_sin_telefono = 0

    for llamada in llamadas:
        categoria = llamada.get('categoria_negocio', '')
        if any(irr in categoria for irr in categorias_irrelevantes):
            negocios_irrelevantes += 1

        comentarios = llamada.get('comentarios_adicionales', '').lower()
        if 'cerrado' in comentarios or 'ya no existe' in comentarios:
            negocios_cerrados += 1

        if llamada.get('resultado') == 'NO CONTESTA':
            negocios_sin_telefono += 1

    # 2. ¿Contacto incorrecto sigue siendo problema?
    contacto_incorrecto = 0
    for llamada in llamadas:
        comentarios = llamada.get('comentarios_adicionales', '').lower()
        if any(palabra in comentarios for palabra in ['mostrador', 'recepción', 'no es el encargado', 'no soy el encargado']):
            contacto_incorrecto += 1

    # 3. ¿Errores técnicos?
    errores_tecnicos = 0
    for llamada in llamadas:
        comentarios = llamada.get('comentarios_adicionales', '').lower()
        if any(palabra in comentarios for palabra in ['error', 'timeout', 'crash', 'no funcionó', 'fallo']):
            errores_tecnicos += 1

    total = len(llamadas)
    return {
        'negocios_irrelevantes': negocios_irrelevantes,
        'tasa_irrelevantes': (negocios_irrelevantes / total * 100) if total > 0 else 0,
        'negocios_cerrados': negocios_cerrados,
        'tasa_cerrados': (negocios_cerrados / total * 100) if total > 0 else 0,
        'contacto_incorrecto': contacto_incorrecto,
        'tasa_contacto_incorrecto': (contacto_incorrecto / total * 100) if total > 0 else 0,
        'errores_tecnicos': errores_tecnicos,
        'tasa_errores': (errores_tecnicos / total * 100) if total > 0 else 0
    }


def imprimir_reporte_completo(analisis, patrones):
    """Imprime reporte completo de auditoría profunda"""
    print("\n" + "="*100)
    print(" AUDITORIA PROFUNDA - FASE DE TESTEO")
    print("="*100)

    # SECCIÓN 1: RESUMEN EJECUTIVO
    print("\n 1. RESUMEN EJECUTIVO")
    print("-"*100)

    delta_conv = analisis['conversion'] - BASELINE_CONVERSION
    delta_int = analisis['tasa_interes_bajo'] - BASELINE_INTERES_BAJO

    print(f"\n  Total llamadas analizadas: {analisis['total']}")
    print(f"  WhatsApps capturados: {analisis['whatsapps']}")
    print(f"  Correos capturados: {analisis['correos']}")
    print(f"  Duración promedio: {analisis['duracion_promedio']:.0f} segundos")

    # Conversión
    signo_conv = '+' if delta_conv > 0 else ''
    emoji_conv = '✅' if delta_conv > 0 else '❌'
    print(f"\n  {emoji_conv} CONVERSIÓN: {analisis['conversion']:.2f}%")
    print(f"     Baseline: {BASELINE_CONVERSION}%")
    print(f"     Diferencia: {signo_conv}{delta_conv:.2f}%")
    if delta_conv > 0:
        mejora_pct = (delta_conv / BASELINE_CONVERSION * 100)
        print(f"     Mejora: {mejora_pct:.1f}%")

    # Interés Bajo
    signo_int = '+' if delta_int > 0 else ''
    emoji_int = '✅' if delta_int < 0 else '❌'
    print(f"\n  {emoji_int} INTERÉS BAJO: {analisis['tasa_interes_bajo']:.2f}%")
    print(f"     Baseline: {BASELINE_INTERES_BAJO}%")
    print(f"     Diferencia: {signo_int}{delta_int:.2f}%")
    if delta_int < 0:
        reduccion_pct = abs(delta_int / BASELINE_INTERES_BAJO * 100)
        print(f"     Reducción: {reduccion_pct:.1f}%")

    # SECCIÓN 2: DISTRIBUCIÓN DE RESULTADOS
    print("\n 2. DISTRIBUCION DE RESULTADOS")
    print("-"*100)
    for resultado, count in sorted(analisis['resultados'].items(), key=lambda x: x[1], reverse=True):
        pct = (count / analisis['total'] * 100) if analisis['total'] > 0 else 0
        print(f"  {resultado:15s}: {count:4d} ({pct:5.1f}%)")

    # SECCIÓN 3: NIVEL DE INTERÉS
    print("\n 3. NIVEL DE INTERES")
    print("-"*100)
    for nivel, count in sorted(analisis['interes'].items(), key=lambda x: x[1], reverse=True):
        pct = (count / analisis['total'] * 100) if analisis['total'] > 0 else 0
        print(f"  {nivel:15s}: {count:4d} ({pct:5.1f}%)")

    # SECCIÓN 4: ESTADO DE ÁNIMO
    print("\n 4. ESTADO DE ANIMO DEL CLIENTE")
    print("-"*100)
    for animo, count in sorted(analisis['estado_animo'].items(), key=lambda x: x[1], reverse=True):
        pct = (count / analisis['total'] * 100) if analisis['total'] > 0 else 0
        print(f"  {animo:15s}: {count:4d} ({pct:5.1f}%)")

    # SECCIÓN 5: TOP RAZONES DE RECHAZO
    print("\n 5. TOP RAZONES DE RECHAZO (llamadas NEGADAS)")
    print("-"*100)
    for razon, count in analisis['top_razones_rechazo']:
        print(f"  {razon}: {count}")

    # SECCIÓN 6: ANÁLISIS DE PATRONES (ESPECÍFICO PARA TESTEO)
    print("\n 6. ANALISIS DE PATRONES - VALIDACION DE MEJORAS")
    print("-"*100)

    print(f"\n  CALIDAD DE LEADS (vs problema identificado):")
    print(f"    Negocios irrelevantes: {patrones['negocios_irrelevantes']} ({patrones['tasa_irrelevantes']:.1f}%)")
    print(f"    Objetivo: <5% (era 33% con categorías Audio/Seguridad/Empaques/Envíos)")
    emoji1 = '✅' if patrones['tasa_irrelevantes'] < 5.0 else '❌'
    print(f"    {emoji1} {'MEJORÓ' if patrones['tasa_irrelevantes'] < 5.0 else 'AÚN ALTO'}")

    print(f"\n  NEGOCIOS CERRADOS:")
    print(f"    Detectados: {patrones['negocios_cerrados']} ({patrones['tasa_cerrados']:.1f}%)")
    print(f"    Objetivo: <3% (filtro 'OPEN' del importador)")
    emoji2 = '✅' if patrones['tasa_cerrados'] < 3.0 else '⚠️'
    print(f"    {emoji2} {'OK' if patrones['tasa_cerrados'] < 3.0 else 'REVISAR FILTRO'}")

    print(f"\n  CONTACTO INCORRECTO (mostrador/ventas):")
    print(f"    Detectados: {patrones['contacto_incorrecto']} ({patrones['tasa_contacto_incorrecto']:.1f}%)")
    print(f"    Nota: Este problema NO se puede resolver con filtros (Google Maps no distingue)")
    print(f"    Esperado: ~70-75% (sin cambios)")

    print(f"\n  ERRORES TECNICOS:")
    print(f"    Detectados: {patrones['errores_tecnicos']} ({patrones['tasa_errores']:.1f}%)")
    print(f"    Objetivo: <2%")
    emoji3 = '✅' if patrones['tasa_errores'] < 2.0 else '❌'
    print(f"    {emoji3} {'OK' if patrones['tasa_errores'] < 2.0 else 'INVESTIGAR'}")

    # SECCIÓN 7: TOP CATEGORÍAS
    print("\n 7. TOP CATEGORIAS DE NEGOCIO")
    print("-"*100)
    for categoria, count in analisis['top_categorias']:
        print(f"  {categoria}: {count}")

    # SECCIÓN 8: TENDENCIA POR DÍA
    if analisis['llamadas_por_dia']:
        print("\n 8. TENDENCIA POR DIA")
        print("-"*100)
        print(f"  {'Fecha':<12} {'Llamadas':>10} {'Aprobados':>10} {'Conversión':>12}")
        print("  " + "-"*46)
        for fecha in sorted(analisis['llamadas_por_dia'].keys()):
            llamadas_dia = analisis['llamadas_por_dia'][fecha]
            aprobados_dia = analisis['aprobados_por_dia'].get(fecha, 0)
            conv_dia = (aprobados_dia / llamadas_dia * 100) if llamadas_dia > 0 else 0
            print(f"  {fecha:<12} {llamadas_dia:>10} {aprobados_dia:>10} {conv_dia:>11.1f}%")

    # SECCIÓN 9: EVALUACIÓN GLOBAL
    print("\n" + "="*100)
    print(" 9. EVALUACION GLOBAL - DECISION")
    print("="*100)

    # Criterios de evaluación
    criterios_cumplidos = 0
    total_criterios = 5

    print("\n  CRITERIOS DE EXITO:")

    # 1. Conversión >= 10%
    if analisis['conversion'] >= 10.0:
        print(f"  ✅ Conversión >= 10%: {analisis['conversion']:.1f}%")
        criterios_cumplidos += 1
    elif analisis['conversion'] >= 8.0:
        print(f"  ⚠️ Conversión >= 8%: {analisis['conversion']:.1f}% (aceptable pero mejorable)")
        criterios_cumplidos += 0.5
    else:
        print(f"  ❌ Conversión < 8%: {analisis['conversion']:.1f}% (insuficiente)")

    # 2. Interés Bajo <= 30%
    if analisis['tasa_interes_bajo'] <= 25.0:
        print(f"  ✅ Interés Bajo <= 25%: {analisis['tasa_interes_bajo']:.1f}%")
        criterios_cumplidos += 1
    elif analisis['tasa_interes_bajo'] <= 35.0:
        print(f"  ⚠️ Interés Bajo <= 35%: {analisis['tasa_interes_bajo']:.1f}% (aceptable)")
        criterios_cumplidos += 0.5
    else:
        print(f"  ❌ Interés Bajo > 35%: {analisis['tasa_interes_bajo']:.1f}% (alto)")

    # 3. Leads irrelevantes < 5%
    if patrones['tasa_irrelevantes'] < 5.0:
        print(f"  ✅ Leads irrelevantes < 5%: {patrones['tasa_irrelevantes']:.1f}%")
        criterios_cumplidos += 1
    else:
        print(f"  ❌ Leads irrelevantes >= 5%: {patrones['tasa_irrelevantes']:.1f}%")

    # 4. Negocios cerrados < 3%
    if patrones['tasa_cerrados'] < 3.0:
        print(f"  ✅ Negocios cerrados < 3%: {patrones['tasa_cerrados']:.1f}%")
        criterios_cumplidos += 1
    else:
        print(f"  ⚠️ Negocios cerrados >= 3%: {patrones['tasa_cerrados']:.1f}%")
        criterios_cumplidos += 0.5

    # 5. Errores técnicos < 2%
    if patrones['tasa_errores'] < 2.0:
        print(f"  ✅ Errores técnicos < 2%: {patrones['tasa_errores']:.1f}%")
        criterios_cumplidos += 1
    else:
        print(f"  ❌ Errores técnicos >= 2%: {patrones['tasa_errores']:.1f}%")

    # Decisión final
    pct_cumplimiento = (criterios_cumplidos / total_criterios * 100)

    print(f"\n  CUMPLIMIENTO: {criterios_cumplidos}/{total_criterios} criterios ({pct_cumplimiento:.0f}%)")

    if pct_cumplimiento >= 80:
        decision = 'PASAR A PRODUCCION'
        emoji = '🎉'
        mensaje = 'Mejoras validadas exitosamente - Sistema listo para producción completa'
    elif pct_cumplimiento >= 60:
        decision = 'CONTINUAR TESTEO'
        emoji = '✅'
        mensaje = 'Mejoras positivas pero requiere más validación - Continuar con más batches'
    elif pct_cumplimiento >= 40:
        decision = 'AJUSTAR Y RE-TESTEAR'
        emoji = '⚠️'
        mensaje = 'Mejoras parciales - Hacer ajustes y volver a testear'
    else:
        decision = 'REVISAR ESTRATEGIA'
        emoji = '❌'
        mensaje = 'Mejoras insuficientes - Revisar importador y estrategia'

    print(f"\n  {emoji} DECISION: {decision}")
    print(f"  {mensaje}")

    print("\n" + "="*100)


def main():
    parser = argparse.ArgumentParser(description='Auditoría profunda para fase de testeo')
    parser.add_argument('--ultimas', type=int, help='Analizar las últimas N llamadas')
    parser.add_argument('--desde', type=str, help='Analizar desde fecha (YYYY-MM-DD)')

    args = parser.parse_args()

    try:
        # Obtener llamadas
        llamadas = obtener_llamadas(ultimas=args.ultimas, desde=args.desde)

        if not llamadas:
            print("\n ❌ ERROR: No se encontraron llamadas")
            return 1

        # Análisis general
        analisis = analizar_resultados(llamadas)

        # Análisis de patrones específicos
        patrones = analizar_patrones_especificos(llamadas)

        # Imprimir reporte
        imprimir_reporte_completo(analisis, patrones)

        return 0

    except Exception as e:
        print(f"\n ❌ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
