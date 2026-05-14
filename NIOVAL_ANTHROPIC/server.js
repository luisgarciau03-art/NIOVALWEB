'use strict';
const express = require('express');
const { spawn, execSync } = require('child_process');
const fs = require('fs');
const path = require('path');
const { v4: uuidv4 } = require('uuid');

const app = express();
const PORT = process.env.PORT || 3000;
// DATA_DIR can be overridden with an env var to point to a persistent volume
const DATA_DIR      = process.env.DATA_DIR || path.join(__dirname, 'data');
const DATA_FILE     = path.join(DATA_DIR, 'activities.json');
const PROJECTS_FILE = path.join(DATA_DIR, 'projects.json');
const REPORTS_DIR   = __dirname;

const DEFAULT_PROJECTS = [
  { id: 'nioval',              name: 'NIOVAL',                    color: '#3b82f6', type: 'main'    },
  { id: 'supratech',           name: 'SUPRATECH',                 color: '#a855f7', type: 'main'    },
  { id: 'fiverr',              name: 'FIVERR',                    color: '#1dbf73', type: 'main'    },
  { id: 'reels-terror',        name: 'Reels de Terror',           color: '#ef4444', type: 'diverse' },
  { id: 'reels-novelas',       name: 'Reels de Novelas',          color: '#ec4899', type: 'diverse' },
  { id: 'reels-juegos-ai',     name: 'Reels juegos AI',           color: '#f59e0b', type: 'diverse' },
  { id: 'bot-reels-automatico',name: 'Bot de Reels AI Automático',color: '#06b6d4', type: 'diverse' },
];

app.use(express.json());
app.use(express.static(path.join(__dirname, 'public')));

// ─── Active script jobs ────────────────────────────────────────────────────
const jobs = new Map(); // jobId -> { status, lines[], process, company, scriptName }

// ─── Persistence ──────────────────────────────────────────────────────────
function loadProjects() {
  try {
    if (!fs.existsSync(PROJECTS_FILE)) return DEFAULT_PROJECTS;
    return JSON.parse(fs.readFileSync(PROJECTS_FILE, 'utf8'));
  } catch { return DEFAULT_PROJECTS; }
}
function saveProjects(list) {
  if (!fs.existsSync(DATA_DIR)) fs.mkdirSync(DATA_DIR, { recursive: true });
  fs.writeFileSync(PROJECTS_FILE, JSON.stringify(list, null, 2), 'utf8');
}

function loadActivities() {
  try {
    if (!fs.existsSync(DATA_FILE)) return [];
    return JSON.parse(fs.readFileSync(DATA_FILE, 'utf8'));
  } catch { return []; }
}

function saveActivities(list) {
  if (!fs.existsSync(DATA_DIR)) fs.mkdirSync(DATA_DIR, { recursive: true });
  fs.writeFileSync(DATA_FILE, JSON.stringify(list, null, 2), 'utf8');
}

// ─── Parser ────────────────────────────────────────────────────────────────
function determinePriority(text) {
  if (/🔴|crítico|crítica|urgente|MÁXIMA|inmediato/i.test(text)) return 'critical';
  if (/🟠|alto|alta|importante|ALTO/i.test(text)) return 'high';
  if (/🟡|medio|media|moderado/i.test(text)) return 'medium';
  if (/🟢|bajo|baja|opcional/i.test(text)) return 'low';
  return 'medium';
}

function normalizeTitle(t) {
  return t.toLowerCase()
    .normalize('NFD').replace(/[̀-ͯ]/g, '')
    .replace(/[^a-z0-9\s]/g, ' ')
    .replace(/\s+/g, ' ').trim();
}

function titleSimilarity(a, b) {
  const wa = new Set(normalizeTitle(a).split(' ').filter(w => w.length > 3));
  const wb = new Set(normalizeTitle(b).split(' ').filter(w => w.length > 3));
  const inter = [...wa].filter(w => wb.has(w)).length;
  const union = new Set([...wa, ...wb]).size;
  return union === 0 ? 0 : inter / union;
}

function cleanCategory(s) {
  return s.replace(/^\d+\.\s*/, '').replace(/^[⚡📈🟢🔴🟠🟡]+\s*/, '').trim();
}

function isJunkTitle(t) {
  return /^(?:Lunes|Martes|Mi[eé]rcoles|Jueves|Viernes|S[áa]bado|Domingo)$/i.test(t) ||
         /^\*+[^*]{1,12}\*+$/.test(t) ||
         t.length < 10;
}

function parseReportFile(filepath, company) {
  let content;
  try { content = fs.readFileSync(filepath, 'utf8'); } catch { return []; }

  const lines = content.split('\n');
  const activities = [];
  let h2 = '', h3 = '';

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];

    // Track headings
    const mh2 = line.match(/^##\s+(.+)/);
    const mh3 = line.match(/^###\s+(.+)/);
    if (mh2) { h2 = mh2[1].trim(); h3 = ''; }
    else if (mh3) { h3 = mh3[1].trim(); }

    // ── Quick Win (### heading or **bold** inline) ──
    const qwHeading = line.match(/^#{1,4}\s+.*?Quick\s+Win\s*[#\d]*\s*[—\-–]\s*(.+)/i);
    const qwBold    = line.match(/^\*\*Quick\s+Win\s*[#\d]*\s*[—\-–]\s*(.+?)\*\*\s*$/i);
    const qwInline  = (!line.startsWith('#') && !line.startsWith('*'))
                        ? line.match(/^Quick\s+Win\s*[#\d]+\s*[—\-–]\s*(.+)/i) : null;

    const qwMatch = qwHeading || qwBold || qwInline;
    if (qwMatch) {
      const title = qwMatch[1].replace(/\*\*/g, '').replace(/\s*\([\d\s\-a-zA-Záéíóú]+\)\s*$/, '').trim();
      if (isJunkTitle(title)) { continue; }

      let descLines = [];
      for (let j = i + 1; j < Math.min(lines.length, i + 30); j++) {
        if (lines[j].match(/^#{1,4}\s+/)) break;
        if (lines[j].match(/Quick\s+Win\s*[#\d]+\s*[—\-–]/i) && j > i + 2) break;
        if (lines[j].match(/^---+$/) && descLines.length > 4) break;
        descLines.push(lines[j]);
      }

      activities.push({
        id: uuidv4(), company,
        title: title.substring(0, 150),
        description: descLines.join('\n').trim(),
        source: path.basename(filepath),
        category: cleanCategory(h2) || 'Quick Win',
        priority: determinePriority(title + descLines.slice(0, 5).join(' ')),
        completed: false,
        createdAt: new Date().toISOString()
      });
      continue;
    }

    // ── ### #N — Title  or  ### QWN — Title (numbered actions) ──
    const numAction = line.match(/^###\s+(?:#\d+|QW\d+)\s*[—\-–]\s*(.+)/i);
    if (numAction) {
      const title = numAction[1].replace(/\*.*?\*/g, '').replace(/\s*\(.*?\)\s*$/, '').trim();
      if (isJunkTitle(title)) continue;

      let descLines = [];
      for (let j = i + 1; j < Math.min(lines.length, i + 20); j++) {
        if (lines[j].match(/^#{1,4}\s+/)) break;
        if (lines[j].match(/^---+$/) && descLines.length > 3) break;
        descLines.push(lines[j]);
      }

      activities.push({
        id: uuidv4(), company,
        title: title.substring(0, 150),
        description: descLines.join('\n').trim(),
        source: path.basename(filepath),
        category: cleanCategory(h2 || h3) || 'Plan de Acción',
        priority: determinePriority(line + descLines.slice(0, 3).join(' ')),
        completed: false,
        createdAt: new Date().toISOString()
      });
      continue;
    }

    // ── ### Oportunidad N — Title ──
    const oppAction = line.match(/^###\s+Oportunidad\s*[#\d]*\s*[—\-–]\s*(.+)/i);
    if (oppAction) {
      const title = oppAction[1].replace(/\*\*/g, '').trim();
      if (isJunkTitle(title)) continue;

      let descLines = [];
      for (let j = i + 1; j < Math.min(lines.length, i + 20); j++) {
        if (lines[j].match(/^#{1,4}\s+/)) break;
        if (lines[j].match(/^---+$/) && descLines.length > 3) break;
        descLines.push(lines[j]);
      }

      activities.push({
        id: uuidv4(), company,
        title: title.substring(0, 150),
        description: descLines.join('\n').trim(),
        source: path.basename(filepath),
        category: cleanCategory(h2) || 'Oportunidades',
        priority: 'medium',
        completed: false,
        createdAt: new Date().toISOString()
      });
      continue;
    }

    // ── Table rows inside PLAN sections ──
    const isPlanCtx = /PLAN|HORIZONTE|IMPLEMENTACI[OÓ]N|ROADMAP|HOJA DE RUTA|MAESTRO/i.test(h2 + h3);
    if (isPlanCtx && line.startsWith('|')) {
      const cols = line.split('|').map(c => c.trim()).filter(Boolean);
      if (cols.length >= 2) {
        const action = cols[0].replace(/^\*+|\*+$/g, '').trim();
        if (
          !action.match(/^[-=\s★☆]+$/) &&
          !action.match(/^(?:Acci[oó]n|Actividad|Action|Paso|Tarea|Item|Qu[eé]|Herramienta|Criterio|Etapa|Herramienta)/i) &&
          !action.match(/^(?:Lunes|Martes|Mi[eé]rcoles|Jueves|Viernes|S[áa]bado|Domingo)$/i) &&
          !isJunkTitle(action)
        ) {
          const detail = cols.slice(1).join(' │ ');
          const ctx = [cleanCategory(h2), cleanCategory(h3)].filter(Boolean).join(' › ');
          activities.push({
            id: uuidv4(), company,
            title: action.substring(0, 150),
            description: `📂 ${ctx}\n\n${detail}`,
            source: path.basename(filepath),
            category: cleanCategory(h3 || h2) || 'Plan de Acción',
            priority: determinePriority(line),
            completed: false,
            createdAt: new Date().toISOString()
          });
        }
      }
    }
  }

  return activities;
}

// ─── Dedup + Merge ─────────────────────────────────────────────────────────
function mergeActivities(existing, incoming) {
  const result = [...existing];

  for (const act of incoming) {
    const dup = result.find(e =>
      e.company === act.company &&
      titleSimilarity(e.title, act.title) >= 0.65
    );

    if (!dup) {
      result.push(act);
    } else {
      // dup exists: if dup is completed keep it; if neither completed keep existing
      // nothing to do in both cases — existing stays
    }
  }
  return result;
}

// ─── Initial parse on startup ─────────────────────────────────────────────
function parseAllReports() {
  const projects = loadProjects();
  const files = fs.readdirSync(REPORTS_DIR).filter(f =>
    f.endsWith('.txt') && f !== 'anthropicapi.txt'
  );

  let all = [];
  for (const f of files) {
    const fp = path.join(REPORTS_DIR, f);
    let company = null;

    if (f.startsWith('nioval'))       company = 'nioval';
    else if (f.startsWith('supratech')) company = 'supratech';
    else if (f.startsWith('fiverr'))    company = 'fiverr';
    else {
      // Match diverse project by ID (hyphens → underscores in filename)
      for (const p of projects) {
        if (p.type === 'main') continue;
        const prefix = p.id.replace(/-/g, '_');
        if (f.startsWith(prefix + '_') || f.startsWith(prefix + '-')) {
          company = p.id;
          break;
        }
      }
    }

    if (!company) continue;
    const parsed = parseReportFile(fp, company);
    all = all.concat(parsed);
  }
  return all;
}

function initActivities() {
  try {
    const existing = loadActivities();
    if (existing.length === 0) {
      console.log('[init] Parsing report files…');
      const parsed = parseAllReports();
      const merged = mergeActivities([], parsed);
      saveActivities(merged);
      console.log(`[init] Saved ${merged.length} activities.`);
    }
  } catch (e) {
    console.error('[init] initActivities error (non-fatal):', e.message);
  }
}

function initProjects() {
  try {
    if (!fs.existsSync(DATA_DIR)) fs.mkdirSync(DATA_DIR, { recursive: true });
    if (!fs.existsSync(PROJECTS_FILE)) {
      saveProjects(DEFAULT_PROJECTS);
      console.log(`[init] Created projects.json with ${DEFAULT_PROJECTS.length} default projects.`);
    }
  } catch (e) {
    console.error('[init] initProjects error (non-fatal):', e.message);
  }
}

// Global handlers so a single bad request never kills the process
process.on('uncaughtException',  err => console.error('[uncaughtException]',  err));
process.on('unhandledRejection', err => console.error('[unhandledRejection]', err));

initProjects();
initActivities();

// ─── API endpoints ────────────────────────────────────────────────────────

// GET /api/activities
app.get('/api/activities', (req, res) => {
  res.json(loadActivities());
});

// PATCH /api/activities/:id  { completed: bool }
app.patch('/api/activities/:id', (req, res) => {
  const list = loadActivities();
  const idx = list.findIndex(a => a.id === req.params.id);
  if (idx === -1) return res.status(404).json({ error: 'not found' });
  const patch = { ...req.body };
  if (patch.completed === true && !list[idx].completed) {
    patch.completedAt = new Date().toISOString();
  } else if (patch.completed === false) {
    patch.completedAt = null;
  }
  list[idx] = { ...list[idx], ...patch };
  saveActivities(list);
  res.json(list[idx]);
});

// POST /api/parse-reports  — re-scan all txt files and merge
app.post('/api/parse-reports', (req, res) => {
  const existing = loadActivities();
  const parsed   = parseAllReports();
  const merged   = mergeActivities(existing, parsed);
  const added    = merged.length - existing.length;
  saveActivities(merged);
  res.json({ total: merged.length, added });
});

// POST /api/run-script  { script: 'nioval_analista_marketing.py', args?: string[] }
app.post('/api/run-script', (req, res) => {
  const { script, args } = req.body;
  if (!script) return res.status(400).json({ error: 'script required' });

  const allowed = [
    'nioval_analista_marketing.py',
    'nioval_analista_ventas.py',
    'supratech_analista.py',
    'analista_proyectos_anexos.py',
    'fiverr_asesor.py',
  ];
  if (!allowed.includes(script)) return res.status(400).json({ error: 'script not allowed' });

  const scriptPath = path.join(REPORTS_DIR, script);
  if (!fs.existsSync(scriptPath)) return res.status(404).json({ error: 'script not found' });

  const jobId = uuidv4();
  const pythonCmd = process.platform === 'win32' ? 'python' : 'python3';

  // Optional extra args (e.g. project ID for analista_proyectos_anexos.py)
  const extraArgs = Array.isArray(args) ? args.map(String) : [];

  const proc = spawn(pythonCmd, [scriptPath, ...extraArgs], {
    cwd: REPORTS_DIR,
    env: { ...process.env },
    shell: false
  });

  jobs.set(jobId, {
    status: 'running',
    lines: [],
    process: proc,
    script,
    startedAt: new Date().toISOString()
  });

  const job = jobs.get(jobId);

  const onData = (chunk) => {
    const text = chunk.toString();
    text.split('\n').forEach(l => {
      if (l) job.lines.push({ t: Date.now(), text: l });
    });
  };

  proc.stdout.on('data', onData);
  proc.stderr.on('data', onData);

  proc.on('error', (err) => {
    job.status   = 'error';
    job.exitCode = -1;
    job.finishedAt = new Date().toISOString();
    const isNotFound = err.code === 'ENOENT';
    job.lines.push({ t: Date.now(), text: `ERROR: ${err.message}` });
    if (isNotFound) {
      job.lines.push({ t: Date.now(), text: '⚠ Python no está disponible en este servidor.' });
      job.lines.push({ t: Date.now(), text: '→ Los scripts de análisis deben ejecutarse LOCALMENTE (npm run dev en tu máquina).' });
      job.lines.push({ t: Date.now(), text: '→ Requieren Python + paquetes (requests, bs4) + Claude Code CLI instalados.' });
    }
  });

  proc.on('close', (code) => {
    job.status = code === 0 ? 'done' : 'error';
    job.exitCode = code;
    job.finishedAt = new Date().toISOString();

    // Auto-merge new activities after script completes
    try {
      const existing = loadActivities();
      const parsed   = parseAllReports();
      const merged   = mergeActivities(existing, parsed);
      const added    = merged.length - existing.length;
      if (added > 0) saveActivities(merged);
      job.newActivities = added;
    } catch (e) {
      job.mergeError = e.message;
    }

    // Auto-commit new .txt report files to git
    try {
      const txtFiles = fs.readdirSync(REPORTS_DIR)
        .filter(f => f.endsWith('.txt') && f !== 'anthropicapi.txt');
      if (txtFiles.length > 0) {
        const fileArgs = txtFiles.map(f => `"${f}"`).join(' ');
        execSync(`git add ${fileArgs}`, { cwd: REPORTS_DIR, stdio: 'pipe' });
        execSync(
          `git commit -m "Auto: reporte de ${script} [${new Date().toISOString().substring(0, 10)}]"`,
          { cwd: REPORTS_DIR, stdio: 'pipe' }
        );
        job.autoCommit = 'committed';
      }
    } catch (e) {
      // Nothing new to commit, or git not available — non-fatal
      job.autoCommit = 'skipped: ' + e.message.split('\n')[0];
    }
  });

  res.json({ jobId });
});

// GET /api/script-output/:jobId  — SSE stream
app.get('/api/script-output/:jobId', (req, res) => {
  const { jobId } = req.params;

  res.setHeader('Content-Type', 'text/event-stream');
  res.setHeader('Cache-Control', 'no-cache');
  res.setHeader('Connection', 'keep-alive');
  res.setHeader('X-Accel-Buffering', 'no');
  res.flushHeaders();

  const send = (ev, data) => {
    res.write(`event: ${ev}\ndata: ${JSON.stringify(data)}\n\n`);
  };

  const job = jobs.get(jobId);
  if (!job) { send('error', { msg: 'job not found' }); res.end(); return; }

  let cursor = 0;

  // Replay any lines already buffered
  const flush = () => {
    while (cursor < job.lines.length) {
      send('line', { text: job.lines[cursor].text });
      cursor++;
    }
    if (job.status === 'done' || job.status === 'error') {
      send('done', {
        exitCode: job.exitCode,
        newActivities: job.newActivities || 0
      });
      clearInterval(timer);
      res.end();
    }
  };

  const timer = setInterval(flush, 200);

  req.on('close', () => clearInterval(timer));
});

// GET /api/jobs  — list recent jobs
app.get('/api/jobs', (_req, res) => {
  const list = [...jobs.entries()].map(([id, j]) => ({
    id,
    script: j.script,
    status: j.status,
    startedAt: j.startedAt,
    finishedAt: j.finishedAt,
    newActivities: j.newActivities
  }));
  res.json(list.reverse());
});

// ─── Projects CRUD ────────────────────────────────────────────────────────

app.get('/api/projects', (_req, res) => res.json(loadProjects()));

app.post('/api/projects', (req, res) => {
  const { name, color } = req.body;
  if (!name || !name.trim()) return res.status(400).json({ error: 'name required' });
  const projects = loadProjects();
  const id = name.trim().toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '')
               .replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '');
  if (projects.find(p => p.id === id)) return res.status(409).json({ error: 'already exists' });
  const p = { id, name: name.trim(), color: color || '#6b7280', type: 'diverse' };
  projects.push(p);
  saveProjects(projects);
  res.json(p);
});

app.delete('/api/projects/:id', (req, res) => {
  const projects = loadProjects();
  const target = projects.find(p => p.id === req.params.id);
  if (!target) return res.status(404).json({ error: 'not found' });
  if (target.type === 'main') return res.status(403).json({ error: 'cannot delete main project' });
  saveProjects(projects.filter(p => p.id !== req.params.id));
  res.json({ ok: true });
});

// POST /api/activities — create manual activity (diverse projects)
app.post('/api/activities', (req, res) => {
  const { company, title, category, priority, description, assignees, dueDate, estimatedTime } = req.body;
  if (!title || !company) return res.status(400).json({ error: 'title and company required' });
  const list = loadActivities();
  const act = {
    id: uuidv4(), company,
    title: String(title).substring(0, 200),
    description: description || '',
    category: category || 'General',
    priority: priority || 'medium',
    completed: false,
    blocked: false,
    blockedReason: '',
    assignees: assignees || '',
    estimatedTime: estimatedTime || '',
    timeSpent: '',
    dueDate: dueDate || null,
    source: 'manual',
    createdAt: new Date().toISOString()
  };
  list.push(act);
  saveActivities(list);
  res.json(act);
});

// DELETE /api/activities/:id
app.delete('/api/activities/:id', (req, res) => {
  const list = loadActivities();
  const idx = list.findIndex(a => a.id === req.params.id);
  if (idx === -1) return res.status(404).json({ error: 'not found' });
  list.splice(idx, 1);
  saveActivities(list);
  res.json({ ok: true });
});

// POST /api/verify-progress — AI analysis of completed tasks vs reports
app.post('/api/verify-progress', async (req, res) => {
  const { company } = req.body;
  if (!company) return res.status(400).json({ error: 'company required' });

  const apiKey = process.env.ANTHROPIC_API_KEY;
  if (!apiKey) return res.status(500).json({ error: 'ANTHROPIC_API_KEY no configurada' });

  const all      = loadActivities().filter(a => a.company === company);
  const completed = all.filter(a => a.completed);
  const pending   = all.filter(a => !a.completed && !a.blocked);
  const blocked   = all.filter(a => a.blocked && !a.completed);

  // Read .txt report files for context (meeting notes / previous analyses)
  let reportsText = '';
  try {
    const reportFiles = fs.readdirSync(REPORTS_DIR)
      .filter(f => f.endsWith('.txt') && f !== 'anthropicapi.txt')
      .filter(f => f.includes(company));
    reportsText = reportFiles.map(f => {
      try {
        const content = fs.readFileSync(path.join(REPORTS_DIR, f), 'utf8');
        return `\n\n--- REPORTE: ${f} ---\n${content.substring(0, 5000)}`;
      } catch { return ''; }
    }).join('');
  } catch { reportsText = ''; }

  const fmt = list => list.length
    ? list.map(a => {
        const date = a.completedAt ? ` [completada ${a.completedAt.substring(0,10)}]` : '';
        return `  • [${(a.priority||'medium').toUpperCase()}] ${a.title} (${a.category||'General'})${date}`;
      }).join('\n')
    : '  (ninguna)';

  const companyName = company === 'nioval' ? 'NIOVAL'
    : company === 'supratech' ? 'SUPRATECH' : company.toUpperCase();

  const userPrompt = `Eres un consultor estratégico analizando el progreso real de ${companyName} versus su plan de acción.

## ESTADO ACTUAL DEL PLAN DE ACCIÓN

**Tareas completadas (${completed.length}):**
${fmt(completed)}

**Tareas pendientes (${pending.length}):**
${fmt(pending)}

**Tareas bloqueadas (${blocked.length}):**
${blocked.length ? blocked.map(a => `  • ${a.title} — ${a.blockedReason || 'sin razón especificada'}`).join('\n') : '  (ninguna)'}

## CONTEXTO: REPORTES Y REUNIONES ANTERIORES
${reportsText || '(sin reportes disponibles)'}

---

Proporciona un análisis estructurado con las siguientes secciones:

## 1. VERIFICACIÓN DE AVANCES
¿Las tareas marcadas como completadas corresponden coherentemente con lo planeado en los reportes? ¿Hay avances que se ven incompletos o que necesitan validación adicional?

## 2. PROGRESO REAL vs ESPERADO
Evalúa el ritmo de avance. ¿Está el proyecto al día, adelantado o atrasado respecto al plan?

## 3. PUNTOS DE ATENCIÓN
Las 3 situaciones más críticas que necesitan atención inmediata (pendientes de alta prioridad, bloqueos, riesgos).

## 4. RECOMENDACIONES PARA ESTA SEMANA
4-5 acciones concretas y específicas para los próximos 7 días, en orden de prioridad.

## 5. PRÓXIMOS HITOS
3 resultados clave que deben lograrse en los próximos 14-30 días para que el proyecto esté en buen camino.

Sé directo, honesto y accionable. Máximo 700 palabras. Responde en español.`;

  try {
    const response = await fetch('https://api.anthropic.com/v1/messages', {
      method: 'POST',
      headers: {
        'x-api-key': apiKey,
        'anthropic-version': '2023-06-01',
        'content-type': 'application/json',
      },
      body: JSON.stringify({
        model: 'claude-sonnet-4-6',
        max_tokens: 2048,
        messages: [{ role: 'user', content: userPrompt }],
      }),
    });

    if (!response.ok) {
      const errText = await response.text();
      return res.status(500).json({ error: `Error API Anthropic ${response.status}: ${errText.substring(0,200)}` });
    }

    const data = await response.json();
    const total = all.length;
    res.json({
      analysis: data.content[0].text,
      stats: {
        total,
        completed: completed.length,
        pending: pending.length,
        blocked: blocked.length,
        completionRate: total ? Math.round((completed.length / total) * 100) : 0,
      },
    });
  } catch (e) {
    res.status(500).json({ error: 'Error al conectar con Anthropic: ' + e.message });
  }
});

// GET /api/reports/:company — lista reportes .txt de un proyecto
app.get('/api/reports/:company', (req, res) => {
  const { company } = req.params;
  try {
    const files = fs.readdirSync(REPORTS_DIR)
      .filter(f => f.endsWith('.txt') && f !== 'anthropicapi.txt' && f.startsWith(company + '_reporte'))
      .sort().reverse();
    res.json(files);
  } catch { res.json([]); }
});

// GET /api/report-content?file=filename — contenido de un reporte
app.get('/api/report-content', (req, res) => {
  const { file } = req.query;
  if (!file || file.includes('..') || !file.endsWith('.txt'))
    return res.status(400).json({ error: 'archivo inválido' });
  const fp = path.join(REPORTS_DIR, file);
  if (!fs.existsSync(fp)) return res.status(404).json({ error: 'no encontrado' });
  try { res.json({ content: fs.readFileSync(fp, 'utf8') }); }
  catch (e) { res.status(500).json({ error: e.message }); }
});

// ─── Start ────────────────────────────────────────────────────────────────
app.listen(PORT, () => {
  console.log(`Dashboard running on http://localhost:${PORT}`);
});
