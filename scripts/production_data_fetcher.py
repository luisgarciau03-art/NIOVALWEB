"""
Descarga datos de todos los endpoints de producción de Bruce W.

Endpoints soportados:
  - /bugs                        → Bugs detectados (últimos 200)
  - /pattern-audit               → Auditoría de patrones (7 días)
  - /diagnostico-narrow-cache    → Cache de respuestas GPT
  - /historial-llamadas          → Historial con calificaciones
  - /stats                       → Estadísticas de cache
  - /diagnostico-persistencia    → Salud de almacenamiento
  - /version                     → Versión actual desplegada
  - /logs/api                    → Logs programáticos

Uso:
  python scripts/production_data_fetcher.py                # Descarga todo
  python scripts/production_data_fetcher.py --endpoint bugs
  python scripts/production_data_fetcher.py --bruce-ids 2515,2516,2518
"""

import os
import sys
import json
import re
import requests
import hashlib
from datetime import datetime

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOGS_DIR = os.path.join(PROJECT_DIR, 'LOGS')
AUDIT_DATA_DIR = os.path.join(PROJECT_DIR, 'audit_data')
HISTORIAL_PATH = os.path.join(AUDIT_DATA_DIR, 'fetch_history.json')

SERVER_URL = "https://nioval-webhook-server-production.up.railway.app"

# Endpoints y sus configuraciones
ENDPOINTS = {
    'bugs': {
        'url': f'{SERVER_URL}/bugs',
        'format': 'html',
        'description': 'Bugs detectados (últimos 200)',
    },
    'pattern-audit': {
        'url': f'{SERVER_URL}/pattern-audit',
        'format': 'html',
        'description': 'Auditoría de patrones (7 días rolling)',
    },
    'diagnostico-narrow-cache': {
        'url': f'{SERVER_URL}/diagnostico-narrow-cache',
        'format': 'html',
        'description': 'Diagnóstico cache GPT narrow',
    },
    'historial-llamadas': {
        'url': f'{SERVER_URL}/historial-llamadas',
        'format': 'html',
        'description': 'Historial de llamadas con calificaciones',
    },
    'stats': {
        'url': f'{SERVER_URL}/stats',
        'format': 'json',
        'description': 'Estadísticas de cache',
    },
    'diagnostico-persistencia': {
        'url': f'{SERVER_URL}/diagnostico-persistencia',
        'format': 'html',
        'description': 'Salud de almacenamiento',
    },
    'version': {
        'url': f'{SERVER_URL}/version',
        'format': 'text',
        'description': 'Versión desplegada actual',
    },
}


def _ensure_dirs():
    os.makedirs(AUDIT_DATA_DIR, exist_ok=True)
    os.makedirs(LOGS_DIR, exist_ok=True)


def _load_history():
    """Carga historial de fetchs previos."""
    if os.path.exists(HISTORIAL_PATH):
        with open(HISTORIAL_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {'fetches': [], 'processed_logs': [], 'processed_bruce_ids': []}


def _save_history(history):
    with open(HISTORIAL_PATH, 'w', encoding='utf-8') as f:
        json.dump(history, f, ensure_ascii=False, indent=2)


def fetch_endpoint(name, config, timeout=30):
    """Descarga datos de un endpoint."""
    url = config['url']
    fmt = config['format']
    try:
        headers = {'Accept': 'application/json'} if fmt == 'json' else {}
        resp = requests.get(url, headers=headers, timeout=timeout)
        resp.raise_for_status()

        if fmt == 'json':
            return {'status': 'ok', 'data': resp.json(), 'format': 'json'}
        else:
            return {'status': 'ok', 'data': resp.text, 'format': fmt}
    except requests.exceptions.RequestException as e:
        return {'status': 'error', 'error': str(e), 'format': fmt}


def fetch_bugs_json():
    """Descarga bugs en formato JSON parseable desde el HTML."""
    result = fetch_endpoint('bugs', ENDPOINTS['bugs'])
    if result['status'] != 'ok':
        return result

    html = result['data']
    bugs = []

    # Parsear tabla HTML de bugs
    # Patrón: cada fila tiene bruce_id, tipo, severidad, detalle
    rows = re.findall(
        r'<tr[^>]*>.*?<td[^>]*>(BRUCE\d+)</td>'
        r'.*?<td[^>]*>(\w+)</td>'
        r'.*?<td[^>]*>(CRITICO|ALTO|MEDIO|BAJO)</td>'
        r'.*?<td[^>]*>(.*?)</td>',
        html, re.DOTALL
    )
    for bruce_id, tipo, severidad, detalle in rows:
        detalle_clean = re.sub(r'<[^>]+>', '', detalle).strip()
        bugs.append({
            'bruce_id': bruce_id,
            'tipo': tipo,
            'severidad': severidad,
            'detalle': detalle_clean,
        })

    # Alternativa: buscar datos JSON embebidos
    if not bugs:
        json_match = re.search(r'var\s+bugsData\s*=\s*(\[.*?\]);', html, re.DOTALL)
        if json_match:
            try:
                bugs = json.loads(json_match.group(1))
            except json.JSONDecodeError:
                pass

    # Otra alternativa: parsear bloques de texto
    if not bugs:
        blocks = re.findall(
            r'(BRUCE\d+).*?(PREGUNTA_REPETIDA|CATALOGO_REPETIDO|PITCH_REPETIDO|'
            r'BRUCE_MUDO|CLIENTE_HABLA_ULTIMO|SALUDO_FALTANTE|NUMERO_INCORRECTO|'
            r'DESPEDIDA_PREMATURA|RESPUESTA_FILLER_INCOHERENTE|DEGRADACION_TTS|'
            r'INTERRUPCION_CONVERSACIONAL|DICTADO_INTERRUMPIDO|AREA_EQUIVOCADA|'
            r'GPT_LOGICA_ROTA|GPT_CONTEXTO_IGNORADO|GPT_RESPUESTA_INCOHERENTE|'
            r'GPT_OPORTUNIDAD_PERDIDA|DATO_NEGADO_REINSISTIDO|PREFERENCIA_IGNORADA|'
            r'TRANSFER_IGNORADA).*?(CRITICO|ALTO|MEDIO|BAJO)?',
            html
        )
        for bruce_id, tipo, sev in blocks:
            bugs.append({
                'bruce_id': bruce_id,
                'tipo': tipo,
                'severidad': sev or 'MEDIO',
                'detalle': '',
            })

    return {'status': 'ok', 'data': bugs, 'format': 'json', 'count': len(bugs)}


def fetch_logs_for_bruce(bruce_id, timeout=30):
    """Descarga logs de un BRUCE ID específico via /logs/api."""
    bruce_num = re.sub(r'\D', '', str(bruce_id))
    url = f"{SERVER_URL}/logs/api?bruce_id={bruce_num}&formato=json"
    try:
        resp = requests.get(url, timeout=timeout)
        resp.raise_for_status()
        data = resp.json()
        return {'status': 'ok', 'data': data}
    except Exception as e:
        return {'status': 'error', 'error': str(e)}


def download_new_logs(history=None):
    """Descarga logs nuevos que no están en el historial.

    Retorna lista de archivos nuevos descargados.
    """
    if history is None:
        history = _load_history()

    processed = set(history.get('processed_logs', []))
    new_files = []

    # Verificar logs existentes en el directorio
    existing_files = set()
    if os.path.isdir(LOGS_DIR):
        for f in os.listdir(LOGS_DIR):
            if f.endswith('.txt'):
                existing_files.add(f)

    # Descargar logs via API
    hoy = datetime.now()
    prefijo = hoy.strftime("%d_%m")

    # Encontrar siguiente número de parte
    max_part = 0
    for f in existing_files:
        m = re.match(rf'{prefijo}PT(\d+)\.txt', f)
        if m:
            max_part = max(max_part, int(m.group(1)))

    # Descargar últimos logs desde API
    url = f"{SERVER_URL}/logs/api?limite=10000&formato=texto"
    try:
        resp = requests.get(url, timeout=60)
        resp.raise_for_status()
        content = resp.text

        if len(content.strip()) > 100:
            # Limpiar HTML que contamina los logs
            content = re.sub(r'<[^>]+>', '\n', content)
            content = re.sub(r'\n{3,}', '\n\n', content)

            # Calcular hash para evitar duplicados
            content_hash = hashlib.md5(content[:5000].encode()).hexdigest()[:12]

            # Verificar si ya tenemos este contenido
            if content_hash not in processed:
                next_part = max_part + 1
                filename = f"{prefijo}PT{next_part}.txt"
                filepath = os.path.join(LOGS_DIR, filename)

                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(content)

                new_files.append(filename)
                history.setdefault('processed_logs', []).append(content_hash)
                print(f"  [+] Descargado: {filename} ({len(content)} chars)")
    except Exception as e:
        print(f"  [!] Error descargando logs: {e}")

    return new_files


def get_unprocessed_logs(history=None):
    """Retorna lista de archivos de log que no han sido procesados."""
    if history is None:
        history = _load_history()

    processed = set(history.get('processed_logs', []))
    unprocessed = []

    if os.path.isdir(LOGS_DIR):
        for f in sorted(os.listdir(LOGS_DIR)):
            if f.endswith('.txt') and f not in processed:
                unprocessed.append(f)

    return unprocessed


def mark_logs_processed(filenames, history=None):
    """Marca archivos de log como procesados."""
    if history is None:
        history = _load_history()

    processed = set(history.get('processed_logs', []))
    for f in filenames:
        processed.add(f)
    history['processed_logs'] = sorted(processed)
    _save_history(history)


def fetch_all(endpoints=None):
    """Descarga datos de todos los endpoints.

    Returns:
        dict con resultados por endpoint
    """
    _ensure_dirs()

    if endpoints is None:
        endpoints = list(ENDPOINTS.keys())

    results = {}
    timestamp = datetime.now().isoformat()

    for name in endpoints:
        if name not in ENDPOINTS:
            print(f"  [!] Endpoint desconocido: {name}")
            continue

        config = ENDPOINTS[name]
        print(f"  Descargando {name}... ", end='', flush=True)
        result = fetch_endpoint(name, config)

        if result['status'] == 'ok':
            # Guardar snapshot
            snapshot_dir = os.path.join(AUDIT_DATA_DIR, 'snapshots')
            os.makedirs(snapshot_dir, exist_ok=True)
            ts = datetime.now().strftime('%Y%m%d_%H%M%S')
            ext = 'json' if result['format'] == 'json' else 'html'
            snapshot_file = os.path.join(snapshot_dir, f"{name}_{ts}.{ext}")

            with open(snapshot_file, 'w', encoding='utf-8') as f:
                if result['format'] == 'json':
                    json.dump(result['data'], f, ensure_ascii=False, indent=2)
                else:
                    f.write(result['data'])

            data_size = len(json.dumps(result['data'])) if result['format'] == 'json' else len(result['data'])
            print(f"OK ({data_size} chars)")
        else:
            print(f"ERROR: {result.get('error', 'unknown')}")

        results[name] = result

    # Intentar parsear bugs como JSON
    bugs_result = fetch_bugs_json()
    results['bugs_parsed'] = bugs_result

    # Guardar historial
    history = _load_history()
    history['fetches'].append({
        'timestamp': timestamp,
        'endpoints': endpoints,
        'results': {k: v['status'] for k, v in results.items()},
    })
    # Mantener solo últimos 100 fetches
    history['fetches'] = history['fetches'][-100:]
    _save_history(history)

    return results


def get_production_summary(results=None):
    """Genera resumen del estado de producción desde los datos descargados.

    Returns:
        dict con métricas clave
    """
    if results is None:
        results = fetch_all()

    summary = {
        'timestamp': datetime.now().isoformat(),
        'version': None,
        'bugs': {'total': 0, 'by_type': {}, 'by_severity': {}, 'bruce_ids': []},
        'endpoints_status': {},
    }

    # Versión
    ver = results.get('version', {})
    if ver.get('status') == 'ok':
        summary['version'] = ver['data'][:200] if isinstance(ver['data'], str) else str(ver['data'])[:200]

    # Bugs parseados
    bugs_parsed = results.get('bugs_parsed', {})
    if bugs_parsed.get('status') == 'ok' and isinstance(bugs_parsed.get('data'), list):
        bugs = bugs_parsed['data']
        summary['bugs']['total'] = len(bugs)
        for b in bugs:
            tipo = b.get('tipo', 'UNKNOWN')
            sev = b.get('severidad', 'MEDIO')
            bid = b.get('bruce_id', '')
            summary['bugs']['by_type'][tipo] = summary['bugs']['by_type'].get(tipo, 0) + 1
            summary['bugs']['by_severity'][sev] = summary['bugs']['by_severity'].get(sev, 0) + 1
            if bid and bid not in summary['bugs']['bruce_ids']:
                summary['bugs']['bruce_ids'].append(bid)

    # Estado de endpoints
    for name, result in results.items():
        if name == 'bugs_parsed':
            continue
        summary['endpoints_status'][name] = result.get('status', 'unknown')

    return summary


# ============================================================
# CLI
# ============================================================

def main():
    import argparse
    parser = argparse.ArgumentParser(description='Bruce W - Production Data Fetcher')
    parser.add_argument('--endpoint', type=str, help='Descargar solo un endpoint')
    parser.add_argument('--bruce-ids', type=str, help='Descargar logs de BRUCE IDs (comma-separated)')
    parser.add_argument('--download-logs', action='store_true', help='Descargar logs nuevos')
    parser.add_argument('--summary', action='store_true', help='Mostrar resumen de producción')
    parser.add_argument('--unprocessed', action='store_true', help='Listar logs no procesados')
    args = parser.parse_args()

    _ensure_dirs()

    if args.unprocessed:
        logs = get_unprocessed_logs()
        print(f"\nLogs no procesados: {len(logs)}")
        for f in logs[:20]:
            print(f"  {f}")
        if len(logs) > 20:
            print(f"  ... y {len(logs)-20} más")
        return

    if args.bruce_ids:
        ids = [x.strip() for x in args.bruce_ids.split(',')]
        for bid in ids:
            print(f"\nDescargando logs de BRUCE{bid}...")
            result = fetch_logs_for_bruce(bid)
            if result['status'] == 'ok':
                data = result['data']
                if isinstance(data, dict) and data.get('logs'):
                    logs_text = '\n'.join(data['logs']) if isinstance(data['logs'], list) else str(data['logs'])
                    filename = f"bruce_{bid}_audit.txt"
                    filepath = os.path.join(LOGS_DIR, filename)
                    with open(filepath, 'w', encoding='utf-8') as f:
                        f.write(logs_text)
                    print(f"  Guardado: {filepath} ({len(logs_text)} chars)")
                else:
                    print(f"  Sin logs disponibles para BRUCE{bid}")
            else:
                print(f"  Error: {result.get('error')}")
        return

    if args.download_logs:
        print("\nDescargando logs nuevos...")
        new_files = download_new_logs()
        if new_files:
            print(f"\n{len(new_files)} archivo(s) nuevo(s) descargado(s)")
        else:
            print("\nNo hay logs nuevos")
        return

    # Default: fetch all endpoints
    endpoints = [args.endpoint] if args.endpoint else None
    print(f"\n{'='*50}")
    print(f"  PRODUCTION DATA FETCHER")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*50}\n")

    results = fetch_all(endpoints)

    if args.summary or not args.endpoint:
        summary = get_production_summary(results)
        print(f"\n--- RESUMEN ---")
        print(f"  Versión: {summary['version'][:80] if summary['version'] else 'N/A'}")
        print(f"  Bugs totales: {summary['bugs']['total']}")
        if summary['bugs']['by_type']:
            print(f"  Por tipo:")
            for tipo, count in sorted(summary['bugs']['by_type'].items(), key=lambda x: -x[1]):
                print(f"    {tipo}: {count}")
        if summary['bugs']['by_severity']:
            print(f"  Por severidad:")
            for sev, count in sorted(summary['bugs']['by_severity'].items()):
                print(f"    {sev}: {count}")
        print(f"  Endpoints: {summary['endpoints_status']}")

    # Guardar resumen
    summary_path = os.path.join(AUDIT_DATA_DIR, 'latest_summary.json')
    with open(summary_path, 'w', encoding='utf-8') as f:
        json.dump(summary if 'summary' in dir() else get_production_summary(results),
                  f, ensure_ascii=False, indent=2)
    print(f"\n  Resumen guardado: {summary_path}")


if __name__ == '__main__':
    main()
