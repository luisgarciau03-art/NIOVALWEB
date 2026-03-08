# -*- coding: utf-8 -*-
"""
Genera un reporte HTML del estado del cache de Bruce
"""
import requests
import json
import os
import re
import sys
from collections import Counter
from datetime import datetime

if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

RAILWAY_URL = 'https://nioval-webhook-server-production.up.railway.app'
LOGS_DIR = r'C:\Users\PC 1\AgenteVentas\LOGS'

def obtener_cache_railway():
    """Obtiene info del cache de Railway"""
    try:
        response = requests.get(f'{RAILWAY_URL}/info-cache', timeout=30)
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        print(f'Error obteniendo cache: {e}')
    return {}

def analizar_logs_hoy():
    """Analiza logs de hoy"""
    hoy = datetime.now().strftime("%d_%m")
    frases = []

    for archivo in os.listdir(LOGS_DIR):
        if archivo.startswith(hoy) and archivo.endswith('.txt'):
            filepath = os.path.join(LOGS_DIR, archivo)
            try:
                with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                    contenido = f.read()
                    matches = re.findall(r'BRUCE\d+ DICE: "([^"]+)"', contenido)
                    frases.extend(matches)
            except:
                pass

    return Counter(frases)

def generar_html(cache_data, contador_hoy):
    """Genera el HTML del reporte"""

    fecha_hora = datetime.now().strftime('%d/%m/%Y %H:%M')

    # Construir filas de top frases
    filas_top = ""
    for i, frase in enumerate(cache_data.get('top_frases', [])[:15], 1):
        estado = '<span class="badge badge-success">En Cache</span>' if frase.get('en_cache') else '<span class="badge badge-warning">Pendiente</span>'
        texto = frase.get('frase', '')[:60]
        usos = frase.get('usos', 0)
        filas_top += f'''
                    <tr>
                        <td>{i}</td>
                        <td class="text-truncate">{texto}...</td>
                        <td><span class="badge badge-info">{usos}x</span></td>
                        <td>{estado}</td>
                    </tr>'''

    # Construir filas de frases de hoy
    filas_hoy = ""
    for i, (frase, count) in enumerate(contador_hoy.most_common(15), 1):
        texto = frase[:60]
        filas_hoy += f'''
                    <tr>
                        <td>{i}</td>
                        <td class="text-truncate">{texto}...</td>
                        <td><span class="badge badge-info">{count}x</span></td>
                    </tr>'''

    # Construir filas de archivos
    filas_archivos = ""
    for i, archivo in enumerate(cache_data.get('archivos', [])[:10], 1):
        filas_archivos += f'''
                    <tr>
                        <td>{i}</td>
                        <td class="text-truncate">{archivo}</td>
                    </tr>'''

    html = f'''<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Reporte Cache Bruce - {fecha_hora}</title>
    <style>
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            font-family: 'Segoe UI', Tahoma, sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            color: #eee;
            min-height: 100vh;
            padding: 20px;
        }}
        .container {{ max-width: 1200px; margin: 0 auto; }}
        h1 {{
            text-align: center;
            color: #00d4ff;
            margin-bottom: 30px;
            font-size: 2.5em;
            text-shadow: 0 0 20px rgba(0,212,255,0.5);
        }}
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}
        .stat-card {{
            background: rgba(255,255,255,0.1);
            border-radius: 15px;
            padding: 25px;
            text-align: center;
            border: 1px solid rgba(255,255,255,0.1);
            transition: transform 0.3s, box-shadow 0.3s;
        }}
        .stat-card:hover {{
            transform: translateY(-5px);
            box-shadow: 0 10px 30px rgba(0,212,255,0.3);
        }}
        .stat-number {{
            font-size: 3em;
            font-weight: bold;
            color: #00d4ff;
            text-shadow: 0 0 10px rgba(0,212,255,0.5);
        }}
        .stat-label {{
            color: #aaa;
            margin-top: 10px;
            font-size: 0.9em;
            text-transform: uppercase;
            letter-spacing: 1px;
        }}
        .section {{
            background: rgba(255,255,255,0.05);
            border-radius: 15px;
            padding: 25px;
            margin-bottom: 25px;
            border: 1px solid rgba(255,255,255,0.1);
        }}
        .section h2 {{
            color: #00d4ff;
            margin-bottom: 20px;
            padding-bottom: 10px;
            border-bottom: 2px solid rgba(0,212,255,0.3);
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
        }}
        th, td {{
            padding: 12px 15px;
            text-align: left;
            border-bottom: 1px solid rgba(255,255,255,0.1);
        }}
        th {{
            background: rgba(0,212,255,0.2);
            color: #00d4ff;
            font-weight: 600;
        }}
        tr:hover {{ background: rgba(255,255,255,0.05); }}
        .badge {{
            display: inline-block;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 0.8em;
            font-weight: bold;
        }}
        .badge-success {{ background: #00c853; color: #fff; }}
        .badge-warning {{ background: #ff9800; color: #000; }}
        .badge-info {{ background: #00d4ff; color: #000; }}
        .footer {{
            text-align: center;
            color: #666;
            margin-top: 30px;
            padding-top: 20px;
            border-top: 1px solid rgba(255,255,255,0.1);
        }}
        .text-truncate {{
            max-width: 400px;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }}
        .status-ok {{ color: #00c853; }}
        .status-warn {{ color: #ff9800; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>Reporte Cache Bruce</h1>

        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-number">{cache_data.get('audios_en_cache', 0)}</div>
                <div class="stat-label">Audios en Cache</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{cache_data.get('frases_registradas', 0)}</div>
                <div class="stat-label">Frases Registradas</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{cache_data.get('frecuencia_min', 1)}</div>
                <div class="stat-label">Umbral Minimo</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{round(cache_data.get('tamano_mb', 0), 1)}</div>
                <div class="stat-label">Tamano (MB)</div>
            </div>
        </div>

        <div class="section">
            <h2>Top Frases en Cache (Railway)</h2>
            <table>
                <thead>
                    <tr>
                        <th>#</th>
                        <th>Frase</th>
                        <th>Usos</th>
                        <th>Estado</th>
                    </tr>
                </thead>
                <tbody>{filas_top}
                </tbody>
            </table>
        </div>

        <div class="section">
            <h2>Frases Frecuentes Hoy ({datetime.now().strftime('%d/%m')})</h2>
            <table>
                <thead>
                    <tr>
                        <th>#</th>
                        <th>Frase</th>
                        <th>Usos Hoy</th>
                    </tr>
                </thead>
                <tbody>{filas_hoy}
                </tbody>
            </table>
        </div>

        <div class="section">
            <h2>Archivos de Audio Recientes</h2>
            <table>
                <thead>
                    <tr>
                        <th>#</th>
                        <th>Archivo</th>
                    </tr>
                </thead>
                <tbody>{filas_archivos}
                </tbody>
            </table>
        </div>

        <div class="footer">
            <p>Generado automaticamente - {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}</p>
            <p>Bruce W - Sistema de Llamadas Automatizadas</p>
        </div>
    </div>
</body>
</html>'''

    return html

def main():
    print("=" * 70)
    print("GENERADOR DE REPORTE HTML - CACHE BRUCE")
    print("=" * 70)
    print()

    # 1. Obtener datos
    print("Obteniendo datos de Railway...")
    cache_data = obtener_cache_railway()

    print("Analizando logs de hoy...")
    contador_hoy = analizar_logs_hoy()

    # 2. Generar HTML
    print("Generando HTML...")
    html = generar_html(cache_data, contador_hoy)

    # 3. Guardar
    output_path = r'C:\Users\PC 1\AgenteVentas\REPORTE_CACHE_28_01.html'
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)

    print()
    print("=" * 70)
    print("REPORTE GENERADO EXITOSAMENTE")
    print("=" * 70)
    print(f"Archivo: {output_path}")
    print()
    print("Resumen:")
    print(f"  - Audios en cache: {cache_data.get('audios_en_cache', 0)}")
    print(f"  - Frases registradas: {cache_data.get('frases_registradas', 0)}")
    print(f"  - Tamano: {cache_data.get('tamano_mb', 0):.1f} MB")
    print(f"  - Umbral minimo: {cache_data.get('frecuencia_min', 1)}")
    print(f"  - Frases analizadas hoy: {sum(contador_hoy.values())}")
    print()

if __name__ == "__main__":
    main()
