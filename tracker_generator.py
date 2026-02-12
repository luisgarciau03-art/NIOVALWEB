"""
Generador dinámico de HTML para Tracker de Bugs & Deploys
Lee tracker_data.json y genera HTML con datos actualizados
"""

import json
import os
from datetime import datetime


def load_tracker_data():
    """Carga datos del archivo JSON persistente."""
    json_path = os.path.join(os.path.dirname(__file__), 'tracker_data.json')

    if not os.path.exists(json_path):
        return None

    with open(json_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_tracker_data(data):
    """Guarda datos al archivo JSON persistente."""
    json_path = os.path.join(os.path.dirname(__file__), 'tracker_data.json')

    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def get_badge_class(bug_type):
    """Retorna clase CSS para badge según tipo de bug."""
    bug_classes = {
        'PREGUNTA_REPETIDA': 'badge-info',
        'CATALOGO_REPETIDO': 'badge-info',
        'CLIENTE_HABLA_ULTIMO': 'badge-info',
        'GPT_LOGICA_ROTA': 'badge-danger',
        'GPT_FUERA_DE_TEMA': 'badge-warning',
        'PITCH_REPETIDO': 'badge-warning',
        'BRUCE_MUDO': 'badge-info',
        'GPT_TONO_INADECUADO': 'badge-warning',
        'GPT_OPORTUNIDAD_PERDIDA': 'badge-warning',
        'GPT_RESPUESTA_INCORRECTA': 'badge-danger',
        'TIMEOUT STT': 'badge-info'
    }
    return bug_classes.get(bug_type, 'badge-info')


def get_impact_class(impact_percent):
    """Retorna clase CSS según impacto."""
    if impact_percent >= 5.0:
        return 'impact-high'
    elif impact_percent >= 2.0:
        return 'impact-medium'
    else:
        return 'impact-low'


def get_impact_category(impact_percent):
    """Retorna categoría de impacto."""
    if impact_percent >= 5.0:
        return 'high'
    elif impact_percent >= 2.0:
        return 'medium'
    else:
        return 'low'


def generate_deploy_row(deploy):
    """Genera HTML para una fila de deploy."""
    impact_class = get_impact_class(deploy['impact_percent'])
    impact_category = get_impact_category(deploy['impact_percent'])
    badge_class = get_badge_class(deploy['bug_type'])

    # Frecuencia total
    frequency_total = deploy.get('frequency_history', {}).get('total', 0)

    html = f'''
                    <tr data-impact="{impact_category}" data-date="{deploy['date']}">
                        <td><strong>{deploy['fix']}</strong></td>
                        <td>{deploy['date']}</td>
                        <td><code>{deploy['commit']}</code></td>
                        <td><span class="badge {badge_class}">{deploy['bug_type']}</span></td>
                        <td>
                            <strong>{deploy['bugs_eliminated']} bugs</strong>
                            <div class="bug-list">{', '.join(deploy['bug_ids'][:5])}</div>
                            <div class="notes">{deploy['notes']}</div>
                            <div class="frequency">📊 Frecuencia total: {frequency_total}x</div>
                        </td>
                        <td class="impact {impact_class}">{deploy['impact_percent']}%</td>
                        <td>{deploy['tests']} (+{deploy['tests_added']})</td>
                        <td><span class="badge badge-success">✅ Deployed</span></td>
                    </tr>'''

    return html


def generate_pending_row(bug):
    """Genera HTML para bugs pendientes."""
    impact_class = get_impact_class(bug['impact_percent'])
    impact_category = get_impact_category(bug['impact_percent'])
    badge_class = get_badge_class(bug['bug_type'])

    # Frecuencia total
    frequency_total = bug.get('frequency_history', {}).get('total', 0)

    # Status badge
    status_badges = {
        'pending_analysis': '<span class="badge badge-warning">⏳ Pendiente</span>',
        'needs_logs': '<span class="badge badge-warning">📋 Necesita logs</span>',
        'monitoring': '<span class="badge badge-info">👁️ Monitoreo</span>'
    }
    status_badge = status_badges.get(bug['status'], '<span class="badge badge-warning">⏳ Pendiente</span>')

    bug_ids_str = ', '.join(bug['bug_ids'][:5]) if bug['bug_ids'] else 'Pendiente identificación'

    html = f'''
                    <tr data-impact="{impact_category}" data-date="2026-02-11">
                        <td><strong>Pendiente</strong></td>
                        <td>-</td>
                        <td>-</td>
                        <td><span class="badge {badge_class}">{bug['bug_type']}</span></td>
                        <td>
                            <strong>{bug['count']} bugs</strong>
                            <div class="bug-list">{bug_ids_str}</div>
                            <div class="notes">{bug['notes']}</div>
                            <div class="frequency">📊 Frecuencia total: {frequency_total}x</div>
                        </td>
                        <td class="impact {impact_class}">{bug['impact_percent']}%</td>
                        <td>-</td>
                        <td>{status_badge}</td>
                    </tr>'''

    return html


def generar_tracker_html():
    """Genera HTML completo del tracker usando datos del JSON."""

    # Cargar datos
    data = load_tracker_data()

    if not data:
        return "<h1>Error</h1><p>No se pudo cargar tracker_data.json</p>", 500

    # Metadata
    metadata = data['metadata']
    total_bugs_eliminated = metadata['total_bugs_base'] - metadata['total_bugs_current']
    reduction_percent = round((total_bugs_eliminated / metadata['total_bugs_base']) * 100, 1)

    # Generar filas de deploys
    deploy_rows = '\n'.join([generate_deploy_row(d) for d in data['deploys']])

    # Generar filas de bugs pendientes
    pending_rows = '\n'.join([generate_pending_row(b) for b in data['pending_bugs']])

    # HTML completo
    html = f'''<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Bruce W - Tracker Bugs & Deploys</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); min-height: 100vh; padding: 20px; }}
        .container {{ max-width: 1400px; margin: 0 auto; background: white; border-radius: 20px; box-shadow: 0 20px 60px rgba(0,0,0,0.3); overflow: hidden; }}
        .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; text-align: center; }}
        .header h1 {{ font-size: 2.5em; margin-bottom: 10px; }}
        .header .subtitle {{ font-size: 1.1em; opacity: 0.9; }}
        .stats-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; padding: 30px; background: #f8f9fa; }}
        .stat-card {{ background: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); text-align: center; }}
        .stat-card .number {{ font-size: 2.5em; font-weight: bold; color: #667eea; margin-bottom: 5px; }}
        .stat-card .label {{ color: #666; font-size: 0.9em; text-transform: uppercase; letter-spacing: 1px; }}
        .content {{ padding: 30px; }}
        .filter-bar {{ display: flex; gap: 15px; margin-bottom: 20px; flex-wrap: wrap; }}
        .filter-btn {{ padding: 10px 20px; border: 2px solid #667eea; background: white; color: #667eea; border-radius: 25px; cursor: pointer; transition: all 0.3s; font-weight: 600; }}
        .filter-btn:hover {{ background: #667eea; color: white; }}
        .filter-btn.active {{ background: #667eea; color: white; }}
        table {{ width: 100%; border-collapse: collapse; background: white; border-radius: 10px; overflow: hidden; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
        thead {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; }}
        th {{ padding: 15px; text-align: left; font-weight: 600; cursor: pointer; user-select: none; }}
        th:hover {{ background: rgba(255,255,255,0.1); }}
        td {{ padding: 15px; border-bottom: 1px solid #eee; }}
        tbody tr:hover {{ background: #f8f9fa; }}
        .badge {{ display: inline-block; padding: 5px 12px; border-radius: 20px; font-size: 0.85em; font-weight: 600; }}
        .badge-success {{ background: #d4edda; color: #155724; }}
        .badge-warning {{ background: #fff3cd; color: #856404; }}
        .badge-info {{ background: #d1ecf1; color: #0c5460; }}
        .badge-danger {{ background: #f8d7da; color: #721c24; }}
        .impact {{ font-weight: bold; }}
        .impact-high {{ color: #28a745; }}
        .impact-medium {{ color: #ffc107; }}
        .impact-low {{ color: #6c757d; }}
        .bug-list {{ font-size: 0.9em; color: #666; margin-top: 5px; }}
        .notes {{ font-style: italic; color: #888; font-size: 0.9em; margin-top: 5px; }}
        .frequency {{ font-size: 0.85em; color: #667eea; margin-top: 5px; font-weight: 600; }}
        .search-box {{ width: 100%; padding: 12px 20px; border: 2px solid #ddd; border-radius: 25px; font-size: 1em; margin-bottom: 20px; transition: border-color 0.3s; }}
        .search-box:focus {{ outline: none; border-color: #667eea; }}
        .footer {{ background: #f8f9fa; padding: 20px; text-align: center; color: #666; font-size: 0.9em; }}
        .last-update {{ background: #fff3cd; padding: 10px 20px; border-radius: 10px; margin-bottom: 20px; text-align: center; color: #856404; }}
        @media (max-width: 768px) {{ .stats-grid {{ grid-template-columns: 1fr; }} table {{ font-size: 0.9em; }} th, td {{ padding: 10px; }} }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🤖 Bruce W - Tracker Bugs & Deploys</h1>
            <div class="subtitle">Sistema de Monitoreo de Correcciones y Deploys (Datos en tiempo real)</div>
        </div>

        <div class="stats-grid">
            <div class="stat-card">
                <div class="number">{metadata['total_deploys']}</div>
                <div class="label">Total Deploys</div>
            </div>
            <div class="stat-card">
                <div class="number">{total_bugs_eliminated}</div>
                <div class="label">Bugs Eliminados</div>
            </div>
            <div class="stat-card">
                <div class="number">{metadata['total_tests']}</div>
                <div class="label">Tests Activos</div>
            </div>
            <div class="stat-card">
                <div class="number">-{reduction_percent}%</div>
                <div class="label">Reducción Bugs</div>
            </div>
        </div>

        <div class="content">
            <div class="last-update">
                🕐 Última actualización: {metadata['last_updated']} | Bugs base: {metadata['total_bugs_base']} → Actuales: {metadata['total_bugs_current']}
            </div>

            <input type="text" class="search-box" id="searchBox" placeholder="🔍 Buscar por FIX, bugs, tipo...">

            <div class="filter-bar">
                <button class="filter-btn active" onclick="filterTable('all')">Todos</button>
                <button class="filter-btn" onclick="filterTable('high')">Impacto Alto</button>
                <button class="filter-btn" onclick="filterTable('medium')">Impacto Medio</button>
                <button class="filter-btn" onclick="filterTable('low')">Impacto Bajo</button>
                <button class="filter-btn" onclick="filterTable('recent')">Últimos 7 días</button>
            </div>

            <table id="deploysTable">
                <thead>
                    <tr>
                        <th onclick="sortTable(0)">FIX ▼</th>
                        <th onclick="sortTable(1)">Fecha</th>
                        <th onclick="sortTable(2)">Commit</th>
                        <th onclick="sortTable(3)">Tipo Bug</th>
                        <th onclick="sortTable(4)">Bugs Eliminados</th>
                        <th onclick="sortTable(5)">Impacto %</th>
                        <th onclick="sortTable(6)">Tests</th>
                        <th onclick="sortTable(7)">Status</th>
                    </tr>
                </thead>
                <tbody>
{deploy_rows}
{pending_rows}
                </tbody>
            </table>
        </div>

        <div class="footer">
            <p><strong>Bruce W - Agente de Ventas AI</strong> | Deploy: Railway | Stack: Python, Twilio, ElevenLabs, Azure Speech, GPT-4o</p>
            <p>Datos cargados desde: tracker_data.json (persistente)</p>
        </div>
    </div>

    <script>
        document.getElementById('searchBox').addEventListener('keyup', function() {{
            const searchValue = this.value.toLowerCase();
            const table = document.getElementById('deploysTable');
            const rows = table.getElementsByTagName('tbody')[0].getElementsByTagName('tr');
            for (let i = 0; i < rows.length; i++) {{
                const row = rows[i];
                const text = row.textContent.toLowerCase();
                if (text.includes(searchValue)) {{
                    row.style.display = '';
                }} else {{
                    row.style.display = 'none';
                }}
            }}
        }});

        function filterTable(filter) {{
            const table = document.getElementById('deploysTable');
            const rows = table.getElementsByTagName('tbody')[0].getElementsByTagName('tr');
            const buttons = document.querySelectorAll('.filter-btn');
            buttons.forEach(btn => btn.classList.remove('active'));
            event.target.classList.add('active');
            for (let i = 0; i < rows.length; i++) {{
                const row = rows[i];
                const impact = row.getAttribute('data-impact');
                const date = row.getAttribute('data-date');
                let show = false;
                if (filter === 'all') {{
                    show = true;
                }} else if (filter === 'high' && impact === 'high') {{
                    show = true;
                }} else if (filter === 'medium' && impact === 'medium') {{
                    show = true;
                }} else if (filter === 'low' && impact === 'low') {{
                    show = true;
                }} else if (filter === 'recent' && date === '2026-02-11') {{
                    show = true;
                }}
                row.style.display = show ? '' : 'none';
            }}
        }}

        let sortDirection = true;
        function sortTable(columnIndex) {{
            const table = document.getElementById('deploysTable');
            const tbody = table.getElementsByTagName('tbody')[0];
            const rows = Array.from(tbody.getElementsByTagName('tr'));
            rows.sort((a, b) => {{
                const aValue = a.getElementsByTagName('td')[columnIndex].textContent;
                const bValue = b.getElementsByTagName('td')[columnIndex].textContent;
                if (sortDirection) {{
                    return aValue.localeCompare(bValue);
                }} else {{
                    return bValue.localeCompare(aValue);
                }}
            }});
            sortDirection = !sortDirection;
            rows.forEach(row => tbody.appendChild(row));
        }}
    </script>
</body>
</html>'''

    return html
