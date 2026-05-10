const CELL         = 30;
const WORLD_W      = 100;
const WORLD_H      = 100;
const MAX_HEALTH   = 80;
const SCROLL_SPEED = 600; // px / sec

const API    = 'http://localhost:8000';
const WS_URL = 'ws://localhost:8000/ws';

// ── Canvas ───────────────────────────────────────────────────────────────────

const canvas = document.getElementById('game');
const ctx    = canvas.getContext('2d');

function resize() {
  canvas.width  = window.innerWidth;
  canvas.height = window.innerHeight;
}
window.addEventListener('resize', resize);
resize();

// ── Camera ───────────────────────────────────────────────────────────────────

let camX = 0;
let camY = 0;

function clampCamera() {
  camX = Math.max(0, Math.min(Math.max(0, WORLD_W * CELL - canvas.width),  camX));
  camY = Math.max(0, Math.min(Math.max(0, WORLD_H * CELL - canvas.height), camY));
}

// ── Input ────────────────────────────────────────────────────────────────────

const keys = new Set();

window.addEventListener('keydown', e => {
  if (['ArrowUp', 'ArrowDown', 'ArrowLeft', 'ArrowRight'].includes(e.key)) {
    e.preventDefault();
  }
  keys.add(e.key);
});
window.addEventListener('keyup', e => keys.delete(e.key));

canvas.addEventListener('click', e => {
  const rect = canvas.getBoundingClientRect();
  const wx = Math.floor((e.clientX - rect.left + camX) / CELL);
  const wy = Math.floor((e.clientY - rect.top  + camY) / CELL);
  let hit = null;
  for (const a of agents.values()) {
    if (a.x === wx && a.y === wy) { hit = a.id; break; }
  }
  selectedAgentId = (selectedAgentId === hit) ? null : hit;
  updateAgentPanel(selectedAgentId ? agents.get(selectedAgentId) : null);
});

// ── State ────────────────────────────────────────────────────────────────────

const agents     = new Map();
const deadAgents = new Map();
const food       = new Map();
const rivers     = new Map(); // river_id -> { id, tiles: [[x,y],...], complete }
const groups     = new Map(); // group_id -> { id, home: [x,y]|null, stockpile: int }

let clockState      = 'stopped';
let tickCount       = 0;
let selectedAgentId = null;

function upsertAgent(a) {
  agents.set(a.id, a);
  if (a.id === selectedAgentId) updateAgentPanel(a);
}
function upsertFood(f)  { food.set(f.id, f); }

function upsertRiver(r) {
  rivers.set(r.river_id, { id: r.river_id, tiles: r.tiles.slice(), complete: r.complete });
}

function addRiverTile(riverId, x, y) {
  let river = rivers.get(riverId);
  if (!river) {
    river = { id: riverId, tiles: [], complete: false };
    rivers.set(riverId, river);
  }
  river.tiles.push([x, y]);
}

// ── DOM ───────────────────────────────────────────────────────────────────────

const tickEl         = document.getElementById('tick');
const agentCountEl   = document.getElementById('agent-count');
const foodCountEl    = document.getElementById('food-count');
const groupCountEl   = document.getElementById('group-count');
const statusEl       = document.getElementById('status');
const btnStart       = document.getElementById('btn-start');
const btnPause       = document.getElementById('btn-pause');
const btnStop        = document.getElementById('btn-stop');
const btnStats       = document.getElementById('btn-stats');
const modalOverlay   = document.getElementById('modal-overlay');
const modalBody      = document.getElementById('modal-body');
const agentPanel     = document.getElementById('agent-panel');
const agentPanelBody = document.getElementById('agent-panel-body');

function updateAgentPanel(a) {
  if (!agentPanel) return;
  if (!a) { agentPanel.classList.add('hidden'); return; }
  agentPanel.classList.remove('hidden');
  const fmt = v => v == null ? '—' : Array.isArray(v) ? `[${v}]` : String(v);
  const abbrev = v => v == null ? '—' : String(v).length === 36 ? String(v).slice(0, 8) : String(v);
  const rows = [
    ['id',             abbrev(a.id)],
    ['x / y',          `${a.x}, ${a.y}`],
    ['health',         `${a.health} / ${MAX_HEALTH}`],
    ['age',            a.age],
    ['vision range',   a.vision_range],
    ['group id',       abbrev(a.group_id)],
    ['carrying food',  a.carrying_food ? 'yes' : 'no'],
    ['direction',      fmt(a.direction)],
    ['last food seen', fmt(a.last_food_seen)],
  ];
  agentPanelBody.innerHTML = rows.map(([k, v]) =>
    `<div class="agent-row"><span>${k}</span><span class="val">${v}</span></div>`
  ).join('');
}

function syncCounters() {
  agentCountEl.textContent  = agents.size;
  foodCountEl.textContent   = food.size;
  groupCountEl.textContent  = groups.size;
}

function setClockState(state) {
  clockState               = state;
  btnStart.disabled        = state !== 'stopped';
  btnPause.disabled        = state === 'stopped';
  btnStop.disabled         = state === 'stopped';
  btnPause.textContent     = state === 'paused' ? '▶ Resume' : '⏸ Pause';
  statusEl.textContent     = { stopped: 'Stopped', running: 'Running', paused: 'Paused' }[state] ?? state;
}

// ── WebSocket ─────────────────────────────────────────────────────────────────

function connect() {
  const ws = new WebSocket(WS_URL);

  ws.onopen  = () => fetchState();
  ws.onerror = () => ws.close();
  ws.onclose = () => {
    statusEl.textContent = 'Disconnected — retrying…';
    setTimeout(connect, 2000);
  };

  ws.onmessage = ({ data }) => {
    const msg = JSON.parse(data);
    switch (msg.event) {
      case 'game_started':
        agents.clear();
        deadAgents.clear();
        food.clear();
        rivers.clear();
        groups.clear();
        selectedAgentId = null;
        updateAgentPanel(null);
        msg.agents.forEach(upsertAgent);
        msg.food.forEach(upsertFood);
        msg.rivers.forEach(upsertRiver);
        setClockState('running');
        break;
      case 'agent_created':
      case 'agent_born':
      case 'agent_picked_up_food':
      case 'agent_moved':   upsertAgent(msg.agent);          break;
      case 'agent_ate':     upsertAgent(msg.agent);
                            food.delete(msg.food_id);        break;
      case 'agent_died':
        deadAgents.set(msg.agent.id, msg.agent);
        agents.delete(msg.agent.id);
        if (selectedAgentId === msg.agent.id) {
          selectedAgentId = null;
          updateAgentPanel(null);
        }
        break;
      case 'group_formed':
        groups.set(msg.group_id, { id: msg.group_id, home: msg.home, stockpile: 0 });
        break;
      case 'group_disbanded':
        groups.delete(msg.group_id);
        break;
      case 'food_deposited':
      case 'food_withdrawn': {
        const g = groups.get(msg.group_id);
        if (g) g.stockpile = msg.stockpile;
        break;
      }
      case 'food_placed':
      case 'food_grew':     upsertFood(msg.food);            break;
      case 'food_removed':  food.delete(msg.food.id);        break;
      case 'food_drowned':  food.delete(msg.food_id);        break;
      case 'river_tile_added':
        addRiverTile(msg.river_id, msg.x, msg.y);
        break;
      case 'river_completed':
        if (rivers.has(msg.river_id)) rivers.get(msg.river_id).complete = true;
        break;
      case 'tick':
        tickCount = msg.tick;
        tickEl.textContent = tickCount;
        break;
    }
    syncCounters();
  };
}

// ── REST ──────────────────────────────────────────────────────────────────────

async function fetchState() {
  const [worldRes, clockRes] = await Promise.all([
    fetch(`${API}/world`),
    fetch(`${API}/clock`),
  ]);
  const worldData = await worldRes.json();
  const clockData = await clockRes.json();

  agents.clear();
  deadAgents.clear();
  food.clear();
  rivers.clear();
  groups.clear();
  worldData.agents.forEach(a => a.alive ? upsertAgent(a) : deadAgents.set(a.id, a));
  worldData.food.forEach(upsertFood);
  worldData.rivers.forEach(upsertRiver);
  (worldData.groups ?? []).forEach(g => groups.set(g.id, g));

  tickCount = clockData.tick_count;
  tickEl.textContent = tickCount || '—';
  setClockState(clockData.state);
  syncCounters();
}

async function post(path) {
  try { await fetch(`${API}${path}`, { method: 'POST' }); }
  catch (e) { console.error('POST', path, e); }
}

// ── Controls ──────────────────────────────────────────────────────────────────

btnStart.addEventListener('click', () => post('/start'));

btnPause.addEventListener('click', () => {
  if      (clockState === 'running') { post('/clock/pause');  setClockState('paused');  }
  else if (clockState === 'paused')  { post('/clock/resume'); setClockState('running'); }
});

btnStop.addEventListener('click', () => {
  post('/clock/stop');
  setClockState('stopped');
});

// ── Stats modal ───────────────────────────────────────────────────────────────

const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
function abbrevId(val) {
  if (val == null) return '—';
  if (Array.isArray(val)) return val.map(v => UUID_RE.test(String(v)) ? String(v).slice(0, 8) : v).join(', ');
  return UUID_RE.test(String(val)) ? String(val).slice(0, 8) : val;
}

let pausedForStats = false;

async function openStats() {
  if (clockState === 'running') {
    await post('/clock/pause');
    setClockState('paused');
    pausedForStats = true;
  }

  const data = await fetch(`${API}/stats`).then(r => r.json());

  const scalars = Object.entries(data).filter(([, v]) => typeof v !== 'object');
  const arrays  = Object.entries(data).filter(([, v]) => Array.isArray(v));

  let html = '';

  if (scalars.length) {
    html += `<div class="stats-summary">`;
    for (const [key, val] of scalars) {
      html += `<div class="stats-summary-item">
        <div class="label">${key.replace(/_/g, ' ')}</div>
        <div class="value">${val}</div>
      </div>`;
    }
    html += `</div>`;
  }

  for (const [key, rows] of arrays) {
    html += `<div class="stats-section"><h4>${key.replace(/_/g, ' ')}</h4>`;
    if (!rows.length) {
      html += `<span class="stats-empty">None</span>`;
    } else {
      const rawCols = Object.keys(rows[0]).filter(c => c !== 'x' && c !== 'y');
      const cols = [
        ...rawCols.filter(c => c === 'id'),
        ...rawCols.filter(c => c === 'age'),
        ...rawCols.filter(c => c !== 'id' && c !== 'age'),
      ];
      const maxAge = cols.includes('age') ? Math.max(...rows.map(r => r.age ?? 0)) : 0;
      html += `<table class="stats-table"><thead><tr>`;
      for (const col of cols) html += `<th>${col.replace(/_/g, ' ')}</th>`;
      html += `</tr></thead><tbody>`;
      for (const row of rows) {
        html += `<tr>`;
        for (const col of cols) {
          if (col === 'age') {
            const pct = maxAge > 0 ? (row.age ?? 0) / maxAge * 100 : 0;
            html += `<td><div class="age-bar"><div style="width:${pct.toFixed(1)}%"></div></div></td>`;
          } else {
            html += `<td>${abbrevId(row[col])}</td>`;
          }
        }
        html += `</tr>`;
      }
      html += `</tbody></table>`;
    }
    html += `</div>`;
  }

  modalBody.innerHTML = html;
  modalOverlay.classList.add('open');
}

function closeStats() {
  modalOverlay.classList.remove('open');
  if (pausedForStats) {
    post('/clock/resume');
    setClockState('running');
    pausedForStats = false;
  }
}

btnStats.addEventListener('click', openStats);
document.getElementById('modal-close').addEventListener('click', closeStats);
modalOverlay.addEventListener('click', e => { if (e.target === modalOverlay) closeStats(); });

// ── Rendering ─────────────────────────────────────────────────────────────────

const PALETTE = [
  '#e74c3c', '#3498db', '#e67e22', '#2ecc71', '#9b59b6',
  '#1abc9c', '#f0c030', '#e91e63', '#00bcd4', '#8bc34a',
];

function agentColor(id) {
  let hash = 0;
  for (const c of id) hash = (hash * 31 + c.charCodeAt(0)) >>> 0;
  return PALETTE[hash % PALETTE.length];
}

function healthColor(health) {
  const r = health / MAX_HEALTH;
  if (r > 0.5)  return '#2ecc71';
  if (r > 0.25) return '#f39c12';
  return '#e74c3c';
}

function drawRivers() {
  ctx.fillStyle = 'rgba(41, 128, 185, 0.55)';
  for (const river of rivers.values()) {
    for (const [x, y] of river.tiles) {
      const sx = x * CELL - camX;
      const sy = y * CELL - camY;
      if (!isVisible(sx, sy)) continue;
      ctx.fillRect(sx, sy, CELL, CELL);
    }
  }
}

function drawGrid() {
  ctx.strokeStyle = '#1a1a1a';
  ctx.lineWidth   = 1;
  ctx.beginPath();

  const c0 = Math.floor(camX / CELL);
  const c1 = Math.min(Math.ceil((camX + canvas.width)  / CELL), WORLD_W);
  const r0 = Math.floor(camY / CELL);
  const r1 = Math.min(Math.ceil((camY + canvas.height) / CELL), WORLD_H);

  for (let c = c0; c <= c1; c++) {
    const x = c * CELL - camX;
    ctx.moveTo(x, 0);
    ctx.lineTo(x, canvas.height);
  }
  for (let r = r0; r <= r1; r++) {
    const y = r * CELL - camY;
    ctx.moveTo(0, y);
    ctx.lineTo(canvas.width, y);
  }
  ctx.stroke();
}

function isVisible(sx, sy) {
  return sx > -CELL && sx < canvas.width && sy > -CELL && sy < canvas.height;
}

function drawStockpiles() {
  for (const g of groups.values()) {
    if (!g.home) continue;
    const sx = g.home[0] * CELL - camX;
    const sy = g.home[1] * CELL - camY;
    if (!isVisible(sx, sy)) continue;

    const cx = sx + CELL / 2;
    const cy = sy + CELL / 2;
    const half = 7;

    ctx.fillStyle   = g.stockpile > 0 ? 'rgba(232, 180, 80, 0.85)' : 'rgba(80, 80, 80, 0.6)';
    ctx.strokeStyle = g.stockpile > 0 ? '#f1c40f' : '#444';
    ctx.lineWidth   = 1.5;
    ctx.beginPath();
    ctx.rect(cx - half, cy - half, half * 2, half * 2);
    ctx.fill();
    ctx.stroke();

    ctx.fillStyle    = g.stockpile > 0 ? '#111' : '#666';
    ctx.font         = 'bold 9px Roboto, sans-serif';
    ctx.textAlign    = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText(g.stockpile, cx, cy);
  }
}

// visionFoods is a Set of food IDs visible to the selected agent (may be empty)
function drawVision(a, r) {
  const cx = a.x * CELL + CELL / 2 - camX;
  const cy = a.y * CELL + CELL / 2 - camY;
  const pr = r * CELL;

  ctx.beginPath();
  ctx.moveTo(cx,      cy - pr);
  ctx.lineTo(cx + pr, cy     );
  ctx.lineTo(cx,      cy + pr);
  ctx.lineTo(cx - pr, cy     );
  ctx.closePath();
  ctx.fillStyle   = 'rgba(255,255,255,0.05)';
  ctx.fill();
  ctx.strokeStyle = 'rgba(255,255,255,0.35)';
  ctx.lineWidth   = 1;
  ctx.setLineDash([6, 4]);
  ctx.stroke();
  ctx.setLineDash([]);
}

function drawFood(visionFoods) {
  for (const f of food.values()) {
    const sx = f.x * CELL - camX;
    const sy = f.y * CELL - camY;
    if (!isVisible(sx, sy)) continue;

    const lit = visionFoods.has(f.id);
    ctx.fillStyle = lit ? '#f1c40f' : '#27ae60';
    ctx.beginPath();
    ctx.arc(sx + CELL / 2, sy + CELL / 2, lit ? 5 : 4, 0, Math.PI * 2);
    ctx.fill();
  }
}

function drawAgents() {
  for (const a of deadAgents.values()) {
    if (!a) continue;
    const sx = a.x * CELL - camX;
    const sy = a.y * CELL - camY;
    if (!isVisible(sx, sy)) continue;

    ctx.beginPath();
    ctx.arc(sx + 15, sy + 11, 9, 0, Math.PI * 2);
    ctx.fillStyle   = '#444';
    ctx.fill();
    ctx.strokeStyle = 'rgba(255,255,255,0.05)';
    ctx.lineWidth   = 1;
    ctx.stroke();
  }

  for (const a of agents.values()) {
    const sx = a.x * CELL - camX;
    const sy = a.y * CELL - camY;
    if (!isVisible(sx, sy)) continue;

    const cx = sx + 15;
    const cy = sy + 11;

    if (a.id === selectedAgentId) {
      ctx.beginPath();
      ctx.arc(cx, cy, 13, 0, Math.PI * 2);
      ctx.strokeStyle = 'rgba(255,255,255,0.8)';
      ctx.lineWidth   = 2;
      ctx.stroke();
    }

    ctx.beginPath();
    ctx.arc(cx, cy, 9, 0, Math.PI * 2);
    ctx.fillStyle   = agentColor(a.id);
    ctx.fill();
    ctx.strokeStyle = 'rgba(255,255,255,0.15)';
    ctx.lineWidth   = 1;
    ctx.stroke();

    if (a.carrying_food) {
      ctx.beginPath();
      ctx.arc(cx + 6, cy - 6, 3, 0, Math.PI * 2);
      ctx.fillStyle = '#f1c40f';
      ctx.fill();
    }

    const barW = 24;
    const barX = sx + 3;
    const barY = sy + 22;
    ctx.fillStyle = '#222';
    ctx.fillRect(barX, barY, barW, 3);
    ctx.fillStyle = healthColor(a.health);
    ctx.fillRect(barX, barY, Math.min(barW * (a.health / MAX_HEALTH), barW), 3);
  }
}

function drawPrompt() {
  if (agents.size === 0 && clockState === 'stopped') {
    ctx.textAlign    = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillStyle    = '#2a2a2a';
    ctx.font         = '14px Roboto, sans-serif';
    ctx.fillText('Press "Start Game" to begin', canvas.width / 2, canvas.height / 2);
  }
}

// ── Game loop ─────────────────────────────────────────────────────────────────

let lastTime = 0;

function frame(now) {
  const dt = Math.min((now - lastTime) / 1000, 0.1);
  lastTime = now;

  if (keys.has('ArrowLeft')  || keys.has('a')) camX -= SCROLL_SPEED * dt;
  if (keys.has('ArrowRight') || keys.has('d')) camX += SCROLL_SPEED * dt;
  if (keys.has('ArrowUp')    || keys.has('w')) camY -= SCROLL_SPEED * dt;
  if (keys.has('ArrowDown')  || keys.has('s')) camY += SCROLL_SPEED * dt;
  clampCamera();

  ctx.fillStyle = '#111111';
  ctx.fillRect(0, 0, canvas.width, canvas.height);

  const visionAgent = selectedAgentId ? agents.get(selectedAgentId) : null;
  const visionR     = visionAgent
    ? (visionAgent.group_id ? Math.round(visionAgent.vision_range * 1.5) : visionAgent.vision_range)
    : 0;
  const visionFoods = new Set();
  if (visionAgent) {
    for (const f of food.values()) {
      if (Math.abs(f.x - visionAgent.x) + Math.abs(f.y - visionAgent.y) <= visionR) {
        visionFoods.add(f.id);
      }
    }
  }

  drawGrid();
  drawRivers();
  drawStockpiles();
  if (visionAgent) drawVision(visionAgent, visionR);
  drawFood(visionFoods);
  drawAgents();
  drawPrompt();

  requestAnimationFrame(frame);
}

// ── Boot ──────────────────────────────────────────────────────────────────────

connect();
requestAnimationFrame(frame);
