# -*- coding: utf-8 -*-
"""
Script para analizar una llamada específica de Bruce en detalle
Extrae toda la conversación, errores y métricas de una llamada
"""
import sys
import re
import os
from datetime import datetime

def analizar_llamada(logs, bruce_id):
    """Analiza una llamada específica por ID"""
    print("\n" + "="*70)
    print(f"🔍 ANÁLISIS DETALLADO: BRUCE{bruce_id}")
    print("="*70 + "\n")

    lineas = logs.split('\n')

    # Buscar todas las líneas relacionadas con este BRUCE ID
    lineas_bruce = []
    for i, linea in enumerate(lineas):
        if f"BRUCE{bruce_id}" in linea:
            lineas_bruce.append({
                'numero': i + 1,
                'texto': linea.strip()
            })

    if not lineas_bruce:
        print(f"❌ No se encontró información de BRUCE{bruce_id}")
        return

    print(f"📊 Total de líneas encontradas: {len(lineas_bruce)}\n")

    # Extraer información clave
    print("="*70)
    print("📋 INFORMACIÓN DE LA LLAMADA")
    print("="*70 + "\n")

    # Buscar datos clave
    numero_telefono = None
    nombre_negocio = None
    resultado = None
    duracion = None

    for item in lineas_bruce:
        linea = item['texto']

        # Número de teléfono
        if 'Llamando a' in linea or 'to=' in linea:
            match = re.search(r'\+?52\d{10}', linea)
            if match:
                numero_telefono = match.group(0)

        # Nombre de negocio
        if 'negocio:' in linea.lower():
            match = re.search(r'negocio:\s*([^,\n]+)', linea, re.IGNORECASE)
            if match:
                nombre_negocio = match.group(1).strip()

        # Resultado
        if 'resultado_llamada' in linea.lower():
            match = re.search(r'resultado_llamada["\s:]*([^,\n"]+)', linea, re.IGNORECASE)
            if match:
                resultado = match.group(1).strip()

        # Duración
        if 'duración' in linea.lower() or 'duration' in linea.lower():
            match = re.search(r'(\d+)\s*seg', linea)
            if match:
                duracion = match.group(1)

    if numero_telefono:
        print(f"📞 Teléfono: {numero_telefono}")
    if nombre_negocio:
        print(f"🏪 Negocio: {nombre_negocio}")
    if resultado:
        print(f"📊 Resultado: {resultado}")
    if duracion:
        print(f"⏱️  Duración: {duracion} segundos")

    print("\n")

    # Extraer conversación
    print("="*70)
    print("💬 CONVERSACIÓN COMPLETA")
    print("="*70 + "\n")

    conversacion = []

    for item in lineas_bruce:
        linea = item['texto']

        # Bruce dice
        if 'BRUCE DICE:' in linea or '🤖 BRUCE DICE:' in linea:
            match = re.search(r'BRUCE DICE:\s*"([^"]+)"', linea)
            if match:
                texto = match.group(1)
                conversacion.append(f"🤖 BRUCE: {texto}")

        # Cliente dice
        if 'CLIENTE DICE:' in linea or '👤 CLIENTE DICE:' in linea:
            match = re.search(r'CLIENTE DICE:\s*"([^"]+)"', linea)
            if match:
                texto = match.group(1)
                conversacion.append(f"👤 CLIENTE: {texto}")

    if conversacion:
        for i, mensaje in enumerate(conversacion, 1):
            print(f"{i}. {mensaje}")
    else:
        print("ℹ️  No se encontraron mensajes de conversación en el log")

    print("\n")

    # Detectar errores
    print("="*70)
    print("🚨 ERRORES Y WARNINGS")
    print("="*70 + "\n")

    errores_detectados = []

    patrones_problema = {
        '❌ Error General': r'❌.*',
        '⚠️ Warning': r'⚠️.*',
        '🔄 Reintento': r'Reintentando|intento \d+/\d+',
        '💰 Créditos': r'credits? (remaining|required)',
        '🤖 Error GPT': r'Error en GPT|OpenAI.*error',
        '🎤 Error ElevenLabs': r'Error.*ElevenLabs|ApiError',
        '📞 Error Twilio': r'TwilioException|status_callback_error',
        '⏱️ Timeout': r'timeout|Timeout waiting',
    }

    for nombre, patron in patrones_problema.items():
        matches = []
        for item in lineas_bruce:
            if re.search(patron, item['texto'], re.IGNORECASE):
                matches.append(item)

        if matches:
            errores_detectados.append({
                'tipo': nombre,
                'count': len(matches),
                'items': matches
            })

    if errores_detectados:
        for error in errores_detectados:
            print(f"\n{error['tipo']}: {error['count']} ocurrencias")
            # Mostrar primeras 2
            for item in error['items'][:2]:
                print(f"   Línea {item['numero']}: {item['texto'][:100]}...")
            if len(error['items']) > 2:
                print(f"   ... y {len(error['items']) - 2} más")
    else:
        print("✅ No se detectaron errores en esta llamada")

    print("\n")

    # Detectar fixes activos
    print("="*70)
    print("🔧 FIXES ACTIVOS DETECTADOS")
    print("="*70 + "\n")

    fixes_detectados = set()

    for item in lineas_bruce:
        # Buscar menciones de FIX
        matches = re.findall(r'FIX (\d+[A-Z]?)', item['texto'])
        fixes_detectados.update(matches)

    if fixes_detectados:
        print("Fixes que se activaron en esta llamada:")
        for fix_id in sorted(fixes_detectados):
            # Contar ocurrencias
            count = sum(1 for item in lineas_bruce if f'FIX {fix_id}' in item['texto'])
            print(f"   ✅ FIX {fix_id}: {count} menciones")
    else:
        print("ℹ️  No se detectaron fixes específicos en esta llamada")

    print("\n")

    # Métricas de rendimiento
    print("="*70)
    print("📊 MÉTRICAS DE RENDIMIENTO")
    print("="*70 + "\n")

    # Contar mensajes
    mensajes_bruce = len([c for c in conversacion if c.startswith('🤖')])
    mensajes_cliente = len([c for c in conversacion if c.startswith('👤')])

    print(f"💬 Mensajes de Bruce: {mensajes_bruce}")
    print(f"👤 Mensajes del Cliente: {mensajes_cliente}")

    # Contar palabras de Bruce
    palabras_totales = 0
    for item in lineas_bruce:
        match = re.search(r'BRUCE DICE:\s*"([^"]+)"', item['texto'])
        if match:
            palabras_totales += len(match.group(1).split())

    if mensajes_bruce > 0:
        promedio_palabras = palabras_totales / mensajes_bruce
        print(f"📝 Promedio de palabras por mensaje: {promedio_palabras:.1f}")

        if promedio_palabras > 30:
            print(f"   ⚠️  Mensajes muy largos (objetivo: 15-25 palabras)")
        elif promedio_palabras < 15:
            print(f"   ⚠️  Mensajes muy cortos")
        else:
            print(f"   ✅ Longitud adecuada")

    print("\n")

    # Análisis de resultado
    print("="*70)
    print("🎯 ANÁLISIS DEL RESULTADO")
    print("="*70 + "\n")

    if resultado:
        if "IVR" in resultado or "Buzón" in resultado:
            print("🤖 Resultado: IVR/Contestadora detectada")
            print("   ✅ FIX 202 funcionó correctamente (detectó sistema automatizado)")
        elif "catálogo enviado" in resultado.lower():
            print("✅ Resultado: ÉXITO - Catálogo enviado")
            print("   Cliente aceptó recibir información")
        elif "No contestó" in resultado:
            print("📞 Resultado: No contestó")
            print("   Cliente no respondió a la llamada")
        elif "Ocupado" in resultado or "ocupado" in resultado.lower():
            print("⏳ Resultado: Cliente ocupado")
            print("   Cliente no pudo atender en ese momento")
        elif "Rechazado" in resultado:
            print("❌ Resultado: Rechazado")
            print("   Cliente rechazó la oferta")
        else:
            print(f"ℹ️  Resultado: {resultado}")
    else:
        print("ℹ️  No se encontró resultado registrado")

    print("\n")

    # Guardar análisis en archivo
    carpeta_logs = "C:\\Users\\PC 1\\AgenteVentas\\LOGS"
    os.makedirs(carpeta_logs, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    archivo_analisis = os.path.join(carpeta_logs, f"analisis_BRUCE{bruce_id}_{timestamp}.txt")

    with open(archivo_analisis, 'w', encoding='utf-8') as f:
        f.write(f"ANÁLISIS DETALLADO: BRUCE{bruce_id}\n")
        f.write("="*70 + "\n\n")

        if numero_telefono:
            f.write(f"Teléfono: {numero_telefono}\n")
        if nombre_negocio:
            f.write(f"Negocio: {nombre_negocio}\n")
        if resultado:
            f.write(f"Resultado: {resultado}\n")
        if duracion:
            f.write(f"Duración: {duracion} segundos\n")

        f.write("\n" + "="*70 + "\n")
        f.write("CONVERSACIÓN COMPLETA\n")
        f.write("="*70 + "\n\n")

        for mensaje in conversacion:
            f.write(mensaje + "\n")

        f.write("\n" + "="*70 + "\n")
        f.write("ERRORES Y WARNINGS\n")
        f.write("="*70 + "\n\n")

        for error in errores_detectados:
            f.write(f"{error['tipo']}: {error['count']} ocurrencias\n")
            for item in error['items']:
                f.write(f"   Línea {item['numero']}: {item['texto']}\n")
            f.write("\n")

        f.write("\n" + "="*70 + "\n")
        f.write("TODAS LAS LÍNEAS DEL LOG\n")
        f.write("="*70 + "\n\n")

        for item in lineas_bruce:
            f.write(f"Línea {item['numero']}: {item['texto']}\n")

    print(f"💾 Análisis guardado en: {archivo_analisis}")
    print("\n")

def main():
    print("\n" + "="*70)
    print("🔍 ANALIZADOR DE LLAMADA ESPECÍFICA")
    print("   Sistema BruceW")
    print("="*70)

    # Verificar argumentos
    if len(sys.argv) < 2:
        print("\n❌ Falta el ID de Bruce o archivo de logs")
        print("\nUso:")
        print("   python analizar_llamada_especifica.py <BRUCE_ID>")
        print("   python analizar_llamada_especifica.py <BRUCE_ID> <archivo_logs.txt>")
        print("\nEjemplos:")
        print("   python analizar_llamada_especifica.py 460")
        print("   python analizar_llamada_especifica.py 460 LOGS\\logs_railway_20260113.txt")
        print("\n")
        return

    bruce_id = sys.argv[1].replace("BRUCE", "")

    # Cargar logs
    if len(sys.argv) > 2:
        # Usar archivo especificado
        archivo = sys.argv[2]
        if not os.path.exists(archivo):
            print(f"❌ Archivo no encontrado: {archivo}")
            return

        with open(archivo, 'r', encoding='utf-8', errors='ignore') as f:
            logs = f.read()
    else:
        # Buscar el archivo más reciente en LOGS
        carpeta_logs = "C:\\Users\\PC 1\\AgenteVentas\\LOGS"

        if not os.path.exists(carpeta_logs):
            print(f"❌ Carpeta de logs no existe: {carpeta_logs}")
            print("\n💡 Ejecuta primero: python analizar_logs_railway.py")
            return

        archivos = [f for f in os.listdir(carpeta_logs) if f.startswith('logs_railway_')]

        if not archivos:
            print(f"❌ No hay archivos de logs en: {carpeta_logs}")
            print("\n💡 Ejecuta primero: python analizar_logs_railway.py")
            return

        # Usar el más reciente
        archivo_mas_reciente = max(archivos, key=lambda f: os.path.getctime(os.path.join(carpeta_logs, f)))
        archivo = os.path.join(carpeta_logs, archivo_mas_reciente)

        print(f"\n📂 Usando archivo: {archivo}")

        with open(archivo, 'r', encoding='utf-8', errors='ignore') as f:
            logs = f.read()

    # Analizar
    analizar_llamada(logs, bruce_id)

    print("="*70)
    print("✅ Análisis completado")
    print("="*70 + "\n")

if __name__ == "__main__":
    main()
