"""
Genera reporte HTML interactivo de auditoría por lotes.

Uso:
  python scripts/batch_report_html.py                    # Genera HTML
  python scripts/batch_report_html.py --open             # Genera y abre en navegador
"""

import os
import sys
import json
from datetime import datetime

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AUDIT_DATA_DIR = os.path.join(PROJECT_DIR, 'audit_data')
BATCH_HISTORY_PATH = os.path.join(AUDIT_DATA_DIR, 'batch_history.json')
HTML_OUTPUT = os.path.join(AUDIT_DATA_DIR, 'auditoria_bruce.html')

sys.path.insert(0, os.path.join(PROJECT_DIR, 'scripts'))


def load_batch_history():
    if os.path.exists(BATCH_HISTORY_PATH):
        with open(BATCH_HISTORY_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {'batches': [], 'logs_processed': {}}


def _severity_color(sev):
    return {
        'CRITICO': '#dc3545',
        'ALTO': '#fd7e14',
        'MEDIO': '#ffc107',
        'BAJO': '#17a2b8',
    }.get(sev, '#6c757d')


def _bug_rate_class(rate):
    if rate == 0:
        return 'good'
    elif rate <= 20:
        return 'ok'
    elif rate <= 50:
        return 'warn'
    return 'bad'


def _cal_class(cal):
    if cal >= 8:
        return 'good'
    elif cal >= 6:
        return 'ok'
    elif cal > 0:
        return 'warn'
    return 'neutral'


def generate_html(history=None, output_path=None):
    if history is None:
        history = load_batch_history()
    if output_path is None:
        output_path = HTML_OUTPUT

    batches = history.get('batches', [])
    logs_processed = history.get('logs_processed', {})

    # Calcular totales
    total_llamadas = sum(b.get('llamadas', 0) for b in batches)
    total_bugs = sum(b.get('bugs_total', 0) for b in batches)
    avg_cal = 0
    if batches:
        cals = [b.get('calificacion_promedio', 0) for b in batches if b.get('calificacion_promedio', 0) > 0]
        avg_cal = sum(cals) / len(cals) if cals else 0

    # Bug rate global
    bug_rate_global = (total_bugs / total_llamadas * 100) if total_llamadas > 0 else 0

    # Todos los bug types
    all_bug_types = {}
    for b in batches:
        for tipo, count in b.get('bugs_por_tipo', {}).items():
            all_bug_types[tipo] = all_bug_types.get(tipo, 0) + count

    # HTML
    html = f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Bruce W - Auditoria por Lotes</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #0f172a;
            color: #e2e8f0;
            padding: 20px;
        }}
        .container {{ max-width: 1400px; margin: 0 auto; }}

        h1 {{
            font-size: 28px;
            color: #60a5fa;
            margin-bottom: 5px;
        }}
        .subtitle {{
            color: #94a3b8;
            font-size: 14px;
            margin-bottom: 30px;
        }}

        /* KPI Cards */
        .kpi-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 16px;
            margin-bottom: 30px;
        }}
        .kpi-card {{
            background: #1e293b;
            border-radius: 12px;
            padding: 20px;
            border: 1px solid #334155;
        }}
        .kpi-card .label {{
            color: #94a3b8;
            font-size: 13px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}
        .kpi-card .value {{
            font-size: 32px;
            font-weight: 700;
            margin: 8px 0 4px;
        }}
        .kpi-card .detail {{
            font-size: 12px;
            color: #64748b;
        }}
        .kpi-card .value.good {{ color: #34d399; }}
        .kpi-card .value.ok {{ color: #60a5fa; }}
        .kpi-card .value.warn {{ color: #fbbf24; }}
        .kpi-card .value.bad {{ color: #f87171; }}
        .kpi-card .value.neutral {{ color: #94a3b8; }}

        /* Tables */
        .section {{ margin-bottom: 40px; }}
        .section-title {{
            font-size: 18px;
            color: #60a5fa;
            margin-bottom: 12px;
            padding-bottom: 8px;
            border-bottom: 1px solid #334155;
        }}

        table {{
            width: 100%;
            border-collapse: collapse;
            background: #1e293b;
            border-radius: 8px;
            overflow: hidden;
        }}
        th {{
            background: #334155;
            color: #e2e8f0;
            padding: 12px 16px;
            text-align: left;
            font-size: 13px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}
        td {{
            padding: 10px 16px;
            border-bottom: 1px solid #1e293b;
            font-size: 14px;
        }}
        tr:hover {{ background: #262f40; }}
        tr:nth-child(even) {{ background: #1a2332; }}

        .badge {{
            display: inline-block;
            padding: 2px 10px;
            border-radius: 12px;
            font-size: 12px;
            font-weight: 600;
        }}
        .badge-good {{ background: #064e3b; color: #34d399; }}
        .badge-warn {{ background: #78350f; color: #fbbf24; }}
        .badge-bad {{ background: #7f1d1d; color: #f87171; }}
        .badge-info {{ background: #1e3a5f; color: #60a5fa; }}

        .severity {{
            display: inline-block;
            padding: 2px 8px;
            border-radius: 4px;
            font-size: 11px;
            font-weight: 700;
            color: white;
        }}

        /* Bug type chart */
        .bug-bar-container {{
            display: flex;
            align-items: center;
            gap: 10px;
            margin-bottom: 6px;
        }}
        .bug-bar-label {{
            width: 220px;
            font-size: 13px;
            text-align: right;
            color: #cbd5e1;
        }}
        .bug-bar-track {{
            flex: 1;
            height: 22px;
            background: #334155;
            border-radius: 4px;
            overflow: hidden;
        }}
        .bug-bar-fill {{
            height: 100%;
            border-radius: 4px;
            display: flex;
            align-items: center;
            padding-left: 8px;
            font-size: 12px;
            font-weight: 600;
            color: white;
        }}

        /* Trend arrow */
        .trend-up {{ color: #f87171; }}
        .trend-down {{ color: #34d399; }}
        .trend-flat {{ color: #94a3b8; }}

        /* Logs table */
        .logs-summary {{
            display: flex;
            gap: 20px;
            margin-bottom: 15px;
        }}
        .logs-summary .stat {{
            background: #1e293b;
            padding: 10px 20px;
            border-radius: 8px;
            border: 1px solid #334155;
        }}
        .logs-summary .stat .num {{
            font-size: 24px;
            font-weight: 700;
            color: #60a5fa;
        }}

        footer {{
            text-align: center;
            color: #475569;
            font-size: 12px;
            margin-top: 40px;
            padding-top: 20px;
            border-top: 1px solid #1e293b;
        }}

        /* Responsive */
        @media (max-width: 768px) {{
            .kpi-grid {{ grid-template-columns: repeat(2, 1fr); }}
            table {{ font-size: 12px; }}
            th, td {{ padding: 8px; }}
        }}
    </style>
</head>
<body>
<div class="container">
    <h1>Bruce W - Auditoria por Lotes</h1>
    <p class="subtitle">Generado: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | Lotes: {len(batches)} | Logs: {len(logs_processed)}</p>

    <!-- KPI Cards -->
    <div class="kpi-grid">
        <div class="kpi-card">
            <div class="label">Total Lotes</div>
            <div class="value ok">{len(batches)}</div>
            <div class="detail">{total_llamadas} llamadas totales</div>
        </div>
        <div class="kpi-card">
            <div class="label">Bugs Totales</div>
            <div class="value {'good' if total_bugs == 0 else 'bad' if total_bugs > 50 else 'warn'}">{total_bugs}</div>
            <div class="detail">{bug_rate_global:.1f}% bug rate</div>
        </div>
        <div class="kpi-card">
            <div class="label">Calificacion Prom.</div>
            <div class="value {_cal_class(avg_cal)}">{avg_cal:.1f}/10</div>
            <div class="detail">Promedio global</div>
        </div>
        <div class="kpi-card">
            <div class="label">Logs Procesados</div>
            <div class="value ok">{len(logs_processed)}</div>
            <div class="detail">Archivos auditados</div>
        </div>
    </div>
"""

    # ---- TABLA RESUMEN POR LOTE ----
    html += """
    <div class="section">
        <h2 class="section-title">Resumen por Lote</h2>
        <table>
            <thead>
                <tr>
                    <th>Lote</th>
                    <th>Fecha</th>
                    <th>Llamadas</th>
                    <th>BRUCE IDs</th>
                    <th>Bugs</th>
                    <th>Criticos</th>
                    <th>Bug Rate</th>
                    <th>Calif.</th>
                    <th>Conversion</th>
                    <th>Regresion</th>
                    <th>Deploy</th>
                    <th>FIX</th>
                </tr>
            </thead>
            <tbody>
"""
    for batch in batches:
        llamadas = batch.get('llamadas', 0)
        bugs = batch.get('bugs_total', 0)
        crit = batch.get('bugs_criticos', 0)
        bug_rate = (bugs / llamadas * 100) if llamadas > 0 else 0
        cal = batch.get('calificacion_promedio', 0)
        conv = batch.get('conversion_rate', 0)
        reg = batch.get('regression_pass_rate', 0)

        bug_badge = 'badge-good' if bugs == 0 else 'badge-warn' if bugs <= 5 else 'badge-bad'
        cal_class = _cal_class(cal)
        reg_badge = 'badge-good' if reg >= 95 else 'badge-warn' if reg >= 80 else 'badge-bad'

        html += f"""                <tr>
                    <td><strong>#{batch.get('lote', '?')}</strong></td>
                    <td>{batch.get('timestamp', '')[:10]}</td>
                    <td>{llamadas}</td>
                    <td>{len(batch.get('bruce_ids', []))}</td>
                    <td><span class="badge {bug_badge}">{bugs}</span></td>
                    <td>{'<span class="badge badge-bad">'+str(crit)+'</span>' if crit > 0 else '<span class="badge badge-good">0</span>'}</td>
                    <td><span class="badge {'badge-good' if bug_rate < 20 else 'badge-warn' if bug_rate < 50 else 'badge-bad'}">{bug_rate:.1f}%</span></td>
                    <td><span class="badge {'badge-good' if cal >= 8 else 'badge-warn' if cal >= 6 else 'badge-bad' if cal > 0 else 'badge-info'}">{cal:.1f}</span></td>
                    <td>{conv:.1f}%</td>
                    <td><span class="badge {reg_badge}">{reg:.1f}%</span></td>
                    <td style="font-size:12px">{batch.get('version_deploy', '')[:20]}</td>
                    <td style="font-size:12px">{', '.join(batch.get('fix_aplicados', []))[:30]}</td>
                </tr>
"""
    html += """            </tbody>
        </table>
    </div>
"""

    # ---- DISTRIBUCION DE BUGS ----
    if all_bug_types:
        max_count = max(all_bug_types.values()) if all_bug_types else 1
        colors = [
            '#ef4444', '#f97316', '#eab308', '#22c55e', '#06b6d4',
            '#3b82f6', '#8b5cf6', '#ec4899', '#f43f5e', '#14b8a6',
            '#a855f7', '#6366f1', '#84cc16', '#f59e0b', '#10b981',
        ]

        html += """
    <div class="section">
        <h2 class="section-title">Distribucion de Bugs (Todos los Lotes)</h2>
"""
        for i, (tipo, count) in enumerate(sorted(all_bug_types.items(), key=lambda x: -x[1])):
            pct = count / max_count * 100
            color = colors[i % len(colors)]
            html += f"""        <div class="bug-bar-container">
            <div class="bug-bar-label">{tipo}</div>
            <div class="bug-bar-track">
                <div class="bug-bar-fill" style="width:{max(pct, 5)}%; background:{color}">{count}</div>
            </div>
        </div>
"""
        html += "    </div>\n"

    # ---- DETALLE DE BUGS ----
    all_bugs = []
    for batch in batches:
        lote = batch.get('lote', '?')
        for bug in batch.get('bugs_detalle', []):
            bug['_lote'] = lote
            all_bugs.append(bug)
        if not batch.get('bugs_detalle') and batch.get('bugs_por_tipo'):
            for tipo, count in batch['bugs_por_tipo'].items():
                all_bugs.append({
                    '_lote': lote,
                    'bruce_id': '',
                    'tipo': tipo,
                    'severidad': 'MEDIO',
                    'detalle': f'{count} ocurrencia(s)',
                })

    if all_bugs:
        html += """
    <div class="section">
        <h2 class="section-title">Detalle de Bugs</h2>
        <table>
            <thead>
                <tr>
                    <th>Lote</th>
                    <th>Bruce ID</th>
                    <th>Tipo</th>
                    <th>Severidad</th>
                    <th>Detalle</th>
                </tr>
            </thead>
            <tbody>
"""
        # Mostrar últimos 100 bugs
        for bug in all_bugs[-100:]:
            sev = bug.get('severidad', 'MEDIO')
            sev_color = _severity_color(sev)
            html += f"""                <tr>
                    <td>#{bug.get('_lote', '?')}</td>
                    <td>{bug.get('bruce_id', '')}</td>
                    <td><strong>{bug.get('tipo', '')}</strong></td>
                    <td><span class="severity" style="background:{sev_color}">{sev}</span></td>
                    <td style="font-size:12px">{bug.get('detalle', '')[:120]}</td>
                </tr>
"""
        if len(all_bugs) > 100:
            html += f"""                <tr><td colspan="5" style="text-align:center; color:#64748b">... {len(all_bugs)-100} bugs mas (ver Excel para listado completo)</td></tr>
"""
        html += """            </tbody>
        </table>
    </div>
"""

    # ---- LOGS PROCESADOS ----
    html += f"""
    <div class="section">
        <h2 class="section-title">Logs Procesados</h2>
        <div class="logs-summary">
            <div class="stat">
                <div class="num">{len(logs_processed)}</div>
                <div class="label" style="color:#94a3b8; font-size:12px">Procesados</div>
            </div>
        </div>
        <p style="color:#64748b; font-size:13px; margin-bottom:10px">
            Archivos ya auditados (no se vuelven a procesar). Nuevos logs se detectan automaticamente.
        </p>
        <table>
            <thead><tr><th>Archivo</th><th>Lote</th><th>Fecha</th></tr></thead>
            <tbody>
"""
    # Últimos 30 logs
    sorted_logs = sorted(logs_processed.items(), key=lambda x: x[1].get('fecha', ''), reverse=True)
    for log_file, info in sorted_logs[:30]:
        html += f"""                <tr>
                    <td>{log_file}</td>
                    <td>#{info.get('lote', '?')}</td>
                    <td>{info.get('fecha', '')[:19]}</td>
                </tr>
"""
    if len(sorted_logs) > 30:
        html += f"""                <tr><td colspan="3" style="text-align:center; color:#64748b">... {len(sorted_logs)-30} archivos mas</td></tr>
"""
    html += """            </tbody>
        </table>
    </div>
"""

    # ---- WORKFLOW ----
    html += """
    <div class="section">
        <h2 class="section-title">Workflow del Ciclo de Mejora</h2>
        <div style="background:#1e293b; border-radius:12px; padding:20px; border:1px solid #334155;">
            <ol style="color:#cbd5e1; line-height:2; padding-left:20px;">
                <li>Hacer <strong>25 llamadas</strong> de prueba</li>
                <li>Descargar logs: <code style="color:#60a5fa">python auto_descarga_logs.py --una-vez</code></li>
                <li>Ejecutar auditoria: <code style="color:#60a5fa">python scripts/batch_audit.py</code></li>
                <li>Revisar bugs en <strong>este reporte</strong> o en <a href="https://nioval-webhook-server-production.up.railway.app/bugs" style="color:#60a5fa">/bugs</a></li>
                <li>Aplicar FIX para bugs encontrados</li>
                <li>Validar en simulador: <code style="color:#60a5fa">python simulador_llamadas.py</code></li>
                <li>Deploy: <code style="color:#60a5fa">git push</code></li>
                <li>Repetir desde paso 1</li>
            </ol>
        </div>
    </div>
"""

    # Footer
    html += f"""
    <footer>
        Bruce W - Sistema de Auditoria Automatizada | Generado {datetime.now().strftime('%Y-%m-%d %H:%M')}
    </footer>
</div>
</body>
</html>"""

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)

    return output_path


def main():
    import argparse
    parser = argparse.ArgumentParser(description='Bruce W - HTML Report Generator')
    parser.add_argument('--open', action='store_true', help='Abrir en navegador')
    parser.add_argument('--path', type=str, default=HTML_OUTPUT, help='Ruta del HTML')
    args = parser.parse_args()

    history = load_batch_history()
    path = generate_html(history, args.path)

    if path:
        print(f"HTML generado: {path}")
        size = os.path.getsize(path)
        print(f"Tamano: {size:,} bytes")
        print(f"Lotes: {len(history.get('batches', []))}")
        print(f"Logs: {len(history.get('logs_processed', {}))}")

        if args.open:
            import webbrowser
            webbrowser.open(f'file:///{path.replace(chr(92), "/")}')


if __name__ == '__main__':
    main()
