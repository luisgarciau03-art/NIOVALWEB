"""
FIX 633: Pattern Audit - Recopilación de datos de uso de patrones.

Módulo independiente que rastrea:
- Qué patrones matchean (y con qué frecuencia)
- Cuáles son invalidados por FIX 598/600/601/602
- Cuáles sobreviven todos los checks
- Patrones "muertos" (nunca matchean en producción)

Persiste en audio_cache/pattern_audit.json para sobrevivir deploys.
Cada función pública está envuelta en try/except - CERO impacto en path crítico.
"""

import json
import os
import time
import threading
from datetime import datetime
from collections import defaultdict


# ============================================================
# CONFIGURACIÓN
# ============================================================

# FIX 640: Usar CACHE_DIR del env var (consistente con servidor_llamadas.py)
# Railway monta el Volume en /app/audio_cache, en local usa ./audio_cache
_CACHE_DIR = os.getenv("CACHE_DIR", "audio_cache")
# FIX 748: Railway Volume - usar PERSISTENT_DIR para sobrevivir deploys
_PERSISTENT_DIR = os.getenv("PERSISTENT_DIR", _CACHE_DIR)
AUDIT_FILE = os.path.join(_PERSISTENT_DIR, "pattern_audit.json")

# Período de reset automático (7 días en segundos)
RESET_PERIOD = 7 * 24 * 3600

# Lock para thread-safety
_lock = threading.Lock()


# ============================================================
# ESTADO EN MEMORIA
# ============================================================

_audit_data = {
    "started_at": None,       # Timestamp inicio del período
    "matched": {},            # tipo -> count (patrón matcheó regex)
    "invalidated_598": {},    # tipo -> count (invalidado por FIX 598)
    "invalidated_600": {},    # tipo -> count (invalidado por FIX 600)
    "invalidated_601": {},    # tipo -> count (invalidado por FIX 601)
    "invalidated_602": {},    # tipo -> count (invalidado por FIX 602)
    "survived": {},           # tipo -> count (pasó TODOS los checks)
    "last_seen": {},          # tipo -> timestamp último match
    "sample_texts": {},       # tipo -> últimos 3 textos que matchearon
}

_initialized = False
_dirty = False               # True si hay cambios sin persistir
_last_save = 0


# ============================================================
# PERSISTENCIA
# ============================================================

def _load():
    """Carga datos desde disco. Llamar una vez al inicio."""
    global _audit_data, _initialized
    try:
        if os.path.exists(AUDIT_FILE):
            with open(AUDIT_FILE, 'r', encoding='utf-8') as f:
                loaded = json.load(f)
            # Merge con estructura base
            for key in _audit_data:
                if key in loaded:
                    _audit_data[key] = loaded[key]
            # Verificar si necesita reset
            if _audit_data["started_at"]:
                elapsed = time.time() - _audit_data["started_at"]
                if elapsed > RESET_PERIOD:
                    _reset()
        if not _audit_data["started_at"]:
            _audit_data["started_at"] = time.time()
        _initialized = True
    except Exception:
        _audit_data["started_at"] = time.time()
        _initialized = True


def _save():
    """Guarda datos a disco. Máximo cada 60s para no saturar I/O."""
    global _dirty, _last_save
    try:
        now = time.time()
        if not _dirty or (now - _last_save) < 60:
            return
        os.makedirs(os.path.dirname(AUDIT_FILE), exist_ok=True)
        with open(AUDIT_FILE, 'w', encoding='utf-8') as f:
            json.dump(_audit_data, f, ensure_ascii=False, indent=2)
        _dirty = False
        _last_save = now
    except Exception:
        pass


def _reset():
    """Reset de datos para nuevo período de auditoría."""
    global _audit_data
    _audit_data = {
        "started_at": time.time(),
        "matched": {},
        "invalidated_598": {},
        "invalidated_600": {},
        "invalidated_601": {},
        "invalidated_602": {},
        "survived": {},
        "last_seen": {},
        "sample_texts": {},
    }


def _ensure_init():
    """Lazy init - carga datos si no se ha hecho."""
    global _initialized
    if not _initialized:
        _load()


# ============================================================
# API PÚBLICA (todas try/except)
# ============================================================

def track_pattern_match(tipo: str, texto: str = ""):
    """Registra que un patrón matcheó (antes de validaciones)."""
    try:
        _ensure_init()
        with _lock:
            _audit_data["matched"][tipo] = _audit_data["matched"].get(tipo, 0) + 1
            _audit_data["last_seen"][tipo] = time.time()
            # Guardar últimos 3 textos de ejemplo
            if tipo not in _audit_data["sample_texts"]:
                _audit_data["sample_texts"][tipo] = []
            samples = _audit_data["sample_texts"][tipo]
            if len(texto) > 5 and texto[:80] not in samples:
                samples.append(texto[:80])
                if len(samples) > 3:
                    samples.pop(0)
            global _dirty
            _dirty = True
        _save()
    except Exception:
        pass


def track_pattern_invalidation(tipo: str, by_fix: str):
    """Registra que un patrón fue invalidado por un FIX específico."""
    try:
        _ensure_init()
        with _lock:
            key = f"invalidated_{by_fix}"
            if key in _audit_data:
                _audit_data[key][tipo] = _audit_data[key].get(tipo, 0) + 1
            global _dirty
            _dirty = True
        _save()
    except Exception:
        pass


def track_pattern_survived(tipo: str):
    """Registra que un patrón sobrevivió TODOS los checks."""
    try:
        _ensure_init()
        with _lock:
            _audit_data["survived"][tipo] = _audit_data["survived"].get(tipo, 0) + 1
            global _dirty
            _dirty = True
        _save()
    except Exception:
        pass


def force_save():
    """Fuerza guardado inmediato (para shutdown graceful)."""
    try:
        global _dirty, _last_save
        _dirty = True
        _last_save = 0
        _save()
    except Exception:
        pass


# ============================================================
# REPORTE
# ============================================================

def get_audit_report() -> dict:
    """Genera reporte de auditoría de patrones."""
    try:
        _ensure_init()
        with _lock:
            matched = dict(_audit_data.get("matched", {}))
            survived = dict(_audit_data.get("survived", {}))
            inv_598 = dict(_audit_data.get("invalidated_598", {}))
            inv_600 = dict(_audit_data.get("invalidated_600", {}))
            inv_601 = dict(_audit_data.get("invalidated_601", {}))
            inv_602 = dict(_audit_data.get("invalidated_602", {}))
            last_seen = dict(_audit_data.get("last_seen", {}))
            samples = dict(_audit_data.get("sample_texts", {}))
            started_at = _audit_data.get("started_at", time.time())

        # Calcular métricas
        all_types = set(matched.keys()) | set(survived.keys())
        elapsed_hours = max(1, (time.time() - started_at) / 3600)

        report = {
            "period_start": datetime.fromtimestamp(started_at).strftime("%Y-%m-%d %H:%M"),
            "elapsed_hours": round(elapsed_hours, 1),
            "total_patterns_seen": len(all_types),
            "total_matches": sum(matched.values()),
            "total_survived": sum(survived.values()),
            "patterns": {}
        }

        for tipo in sorted(all_types):
            m = matched.get(tipo, 0)
            s = survived.get(tipo, 0)
            total_inv = (
                inv_598.get(tipo, 0) +
                inv_600.get(tipo, 0) +
                inv_601.get(tipo, 0) +
                inv_602.get(tipo, 0)
            )
            survival_rate = round(s / m * 100, 1) if m > 0 else 0

            report["patterns"][tipo] = {
                "matched": m,
                "survived": s,
                "invalidated": {
                    "598": inv_598.get(tipo, 0),
                    "600": inv_600.get(tipo, 0),
                    "601": inv_601.get(tipo, 0),
                    "602": inv_602.get(tipo, 0),
                    "total": total_inv
                },
                "survival_rate": survival_rate,
                "last_seen": datetime.fromtimestamp(last_seen[tipo]).strftime("%m-%d %H:%M") if tipo in last_seen else "never",
                "samples": samples.get(tipo, [])
            }

        # Clasificaciones
        report["dead_patterns"] = [
            t for t in all_types if matched.get(t, 0) == 0
        ]
        report["always_invalidated"] = [
            t for t in all_types
            if matched.get(t, 0) >= 3 and survived.get(t, 0) == 0
        ]
        report["rarely_used"] = [
            t for t in all_types
            if 0 < matched.get(t, 0) < 5
        ]
        report["most_used"] = sorted(
            all_types, key=lambda t: matched.get(t, 0), reverse=True
        )[:10]

        return report

    except Exception as e:
        return {"error": str(e)}


# ============================================================
# DASHBOARD HTML
# ============================================================

def generar_audit_html() -> str:
    """Genera HTML para el endpoint /pattern-audit."""
    report = get_audit_report()

    if "error" in report:
        return f"<h1>Error</h1><p>{report['error']}</p>"

    # Resumen
    resumen = f"""
    <div class="resumen">
        <b>Periodo:</b> {report['period_start']} ({report['elapsed_hours']}h)<br>
        <b>Patrones vistos:</b> {report['total_patterns_seen']}<br>
        <b>Total matches:</b> {report['total_matches']}<br>
        <b>Total survived:</b> {report['total_survived']}<br>
        <b>Dead patterns:</b> {len(report.get('dead_patterns', []))}<br>
        <b>Always invalidated:</b> {len(report.get('always_invalidated', []))}<br>
    </div>
    """

    # Alertas
    alertas = ""
    if report.get("always_invalidated"):
        alertas += "<div class='alerta'><b>SIEMPRE INVALIDADOS</b> (matchean pero nunca sobreviven):<br>"
        for t in report["always_invalidated"]:
            p = report["patterns"].get(t, {})
            alertas += f"  - {t}: {p.get('matched', 0)} matches, 0 survived "
            inv = p.get("invalidated", {})
            alertas += f"(598:{inv.get('598',0)} 600:{inv.get('600',0)} 601:{inv.get('601',0)} 602:{inv.get('602',0)})<br>"
        alertas += "</div>"

    # Tabla principal
    rows = []
    patterns = report.get("patterns", {})
    # Ordenar por matches descendente
    sorted_patterns = sorted(patterns.items(), key=lambda x: x[1].get("matched", 0), reverse=True)

    for tipo, data in sorted_patterns:
        m = data.get("matched", 0)
        s = data.get("survived", 0)
        rate = data.get("survival_rate", 0)
        inv = data.get("invalidated", {})
        last = data.get("last_seen", "")
        samples = data.get("samples", [])

        # Color por survival rate
        if m == 0:
            color = "#666"
        elif rate == 0:
            color = "#ff4444"
        elif rate < 50:
            color = "#ffaa00"
        else:
            color = "#44ff44"

        samples_html = "<br>".join(f"<small>'{s}'</small>" for s in samples[:2])

        rows.append(f"""
        <tr>
            <td><b>{tipo}</b></td>
            <td>{m}</td>
            <td>{s}</td>
            <td style="color:{color};font-weight:bold">{rate}%</td>
            <td>{inv.get('598',0)}</td>
            <td>{inv.get('600',0)}</td>
            <td>{inv.get('601',0)}</td>
            <td>{inv.get('602',0)}</td>
            <td>{last}</td>
            <td>{samples_html}</td>
        </tr>""")

    tabla = f"""
    <table border="1" cellpadding="6" cellspacing="0" style="border-collapse:collapse;width:100%;font-size:13px">
        <tr style="background:#333;color:white">
            <th>Patron</th><th>Match</th><th>Surv</th><th>Rate</th>
            <th>598</th><th>600</th><th>601</th><th>602</th>
            <th>Last</th><th>Samples</th>
        </tr>
        {''.join(rows) if rows else '<tr><td colspan="10">Sin datos aún. Esperar llamadas.</td></tr>'}
    </table>
    """

    return f"""<!DOCTYPE html>
<html><head>
<meta charset="utf-8">
<title>Bruce W - Pattern Audit</title>
<style>
    body {{ font-family: monospace; margin: 20px; background: #1a1a1a; color: #eee; }}
    h1 {{ color: #44aaff; }}
    table {{ background: #222; }}
    tr:nth-child(even) {{ background: #2a2a2a; }}
    th {{ text-align: left; }}
    a {{ color: #44aaff; }}
    .resumen {{ background: #333; padding: 10px; border-radius: 5px; margin: 10px 0; }}
    .alerta {{ background: #442222; padding: 10px; border-radius: 5px; margin: 10px 0; border-left: 4px solid #ff4444; }}
    small {{ color: #999; }}
</style>
</head><body>
<h1>Pattern Audit - Bruce W</h1>
<p><a href="/historial-llamadas">Historial</a> | <a href="/bugs">Bugs</a> | <a href="/pattern-audit">Audit</a></p>
{resumen}
{alertas}
{tabla}
<p style="color:#666;margin-top:20px">
    Match = regex matcheó | Surv = sobrevivió FIX 598+600+601+602 | Rate = Surv/Match %<br>
    Dead = 0 matches | Always Inv = matchea pero nunca sobrevive (candidato a eliminar)<br>
    Datos se resetean cada 7 días automáticamente.
</p>
</body></html>"""
