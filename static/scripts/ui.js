import {
  UUID_PATTERN,
  API_BASE,
  MUTATION_COLORS,
  MUTATION_PRIORITY,
} from "./constants.js";
import {
  agents,
  plants,
  setClockState,
  getClockState,
  getIsNight,
  getDayNumber,
  snapAgentsToGrid,
  getElevationAt,
  getEffectiveTemperatureAt,
  getEffectivePrecipitationAt,
} from "./state.js";

const agentCountEl = document.getElementById("agent-count");
const plantCountEl = document.getElementById("plant-count");
const tilePanel = document.getElementById("tile-panel");
const tilePanelTitle = document.getElementById("tile-panel-title");
const tilePanelBody = document.getElementById("tile-panel-body");
const statusEl = document.getElementById("status");
const modalOverlay = document.getElementById("modal-overlay");
const modalBody = document.getElementById("modal-body");
const agentPanel = document.getElementById("agent-panel");
const agentPanelTitle = document.getElementById("agent-panel-title");
const agentPanelBody = document.getElementById("agent-panel-body");

const dayNumberEl = document.getElementById("day-number");
const dayIconEl = document.getElementById("day-icon");

export const btnStart = document.getElementById("btn-start");
export const btnPause = document.getElementById("btn-pause");
export const btnStop = document.getElementById("btn-stop");
export const btnStats = document.getElementById("btn-stats");

const formatValue = (value) =>
  value == null ? "—" : Array.isArray(value) ? `[${value}]` : String(value);

const abbreviateId = (value) => {
  if (value == null) return "—";
  const str = String(value);
  return str.length === 36 ? str.slice(0, 8) : str;
};

export const abbreviateField = (value) => {
  if (value == null) return "—";

  if (Array.isArray(value)) {
    return value
      .map((item) =>
        UUID_PATTERN.test(String(item)) ? String(item).slice(0, 8) : item,
      )
      .join(", ");
  }

  if (typeof value === "number" && !Number.isInteger(value)) {
    return value.toFixed(2);
  }

  return UUID_PATTERN.test(String(value)) ? String(value).slice(0, 8) : value;
};

const agentBar = (label, value, color) => {
  const pct = Math.min(100, Math.max(0, value * 100)).toFixed(1);
  return `
    <div class="agent-bar-row">
      <div class="agent-bar-label">${label}<span class="agent-bar-val">${pct}%</span></div>
      <div class="agent-bar-track"><div class="agent-bar-fill" style="width:${pct}%;background:${color}"></div></div>
    </div>`;
};

export const updateAgentPanel = (agent) => {
  if (!agentPanel) return;
  if (!agent) {
    agentPanel.classList.add("hidden");
    return;
  }

  agentPanel.classList.remove("hidden");

  if (agentPanelTitle)
    agentPanelTitle.textContent = `Agent ${abbreviateId(agent.id)}`;

  const g = agent.behavioral_genome ?? {};
  const fmt = (v) => (v != null ? v.toFixed(3) : "—");

  const rows = [
    ["age", agent.age],
    [
      "action",
      agent.active_task ? agent.active_task.name.replace(/_/g, " ") : "—",
    ],
    ["offspring", agent.offspring_count ?? 0],
    ["breakaway", fmt(g.breakaway_threshold)],
  ];

  const infoHtml = rows
    .map(
      ([label, value]) =>
        `<div class="agent-row"><span>${label}</span><span class="val">${value}</span></div>`,
    )
    .join("");

  const barsHtml =
    `<div class="agent-bars">` +
    agentBar("hunger", agent.needs.hunger, "#c0392b") +
    agentBar("thirst", agent.needs.water, "#27a4c0") +
    agentBar("rest", agent.needs.rest, "#5b8dd9") +
    `</div>`;

  agentPanelBody.innerHTML = infoHtml + barsHtml;
};

export const updateDayNightUI = () => {
  if (dayNumberEl) dayNumberEl.textContent = getDayNumber();
  if (dayIconEl) dayIconEl.textContent = getIsNight() ? "🌙" : "☀️";
};

export const syncCounters = () => {
  agentCountEl.textContent = agents.size;
  plantCountEl.textContent = plants.size;
};

const PLANT_TYPE_LABELS = {
  date_palm: "Date Palm",
  wild_plum: "Wild Plum",
  fig_tree: "Fig Tree",
  berry_bush: "Berry Bush",
  bilberry: "Bilberry",
};

const TEMP_MIN_C = -10;
const TEMP_MAX_C = 40;
const toCelsius = (t) => TEMP_MIN_C + t * (TEMP_MAX_C - TEMP_MIN_C);
const ELEV_MAX_M = 2000;
const toMetres = (e) => Math.round(e * ELEV_MAX_M);

const tileBar = (label, value, color, text) => {
  const pct = Math.min(100, Math.max(0, value * 100)).toFixed(1);
  const display = text ?? `${pct}%`;
  return `
    <div class="agent-bar-row">
      <div class="agent-bar-label">${label}<span class="agent-bar-val">${display}</span></div>
      <div class="agent-bar-track"><div class="agent-bar-fill" style="width:${pct}%;background:${color}"></div></div>
    </div>`;
};

export const updateTilePanel = (x, y, plant, isRiver = false) => {
  if (!tilePanel) return;

  const typeLabel = isRiver
    ? "River"
    : plant
      ? (PLANT_TYPE_LABELS[plant.plant_type] ?? plant.plant_type)
      : "Bare";
  if (tilePanelTitle)
    tilePanelTitle.textContent = `Tile (${x}, ${y}) — ${typeLabel}`;

  const elev = getElevationAt(x, y);
  const temp = getEffectiveTemperatureAt(x, y);
  const precip = getEffectivePrecipitationAt(x, y);

  let barsHtml =
    `<div class="agent-bars">` +
    `<div class="agent-row"><span>elevation</span><span class="val">${toMetres(elev)} m</span></div>` +
    tileBar(
      "temperature",
      temp,
      "#c0392b",
      `${toCelsius(temp).toFixed(1)} °C`,
    ) +
    tileBar("precipitation", precip, "#27a4c0") +
    (plant
      ? tileBar(
          "fruit",
          plant.fruit_count / plant.max_fruit,
          "#27ae60",
          `${Math.floor(plant.fruit_count)}/${plant.max_fruit}`,
        ) +
        `<div class="agent-row"><span>growth rate</span><span class="val">${plant.growth_rate.toFixed(4)}/tick</span></div>`
      : "") +
    `</div>`;

  if (tilePanelBody) tilePanelBody.innerHTML = barsHtml;
  tilePanel.classList.remove("hidden");
};

export const clearTilePanel = () => {
  if (tilePanel) tilePanel.classList.add("hidden");
};

const btnNextAgent = document.getElementById("btn-next-agent");

export const applyClockState = (state) => {
  setClockState(state);
  if (state === "paused" || state === "stopped") snapAgentsToGrid();
  btnStart.disabled = state !== "stopped";
  btnPause.disabled = state === "stopped";
  btnStop.disabled = state === "stopped";
  if (btnNextAgent) btnNextAgent.disabled = state === "stopped";
  btnPause.textContent = state === "paused" ? "▶ Resume" : "⏸ Pause";
  statusEl.textContent =
    { stopped: "Stopped", running: "Running", paused: "Paused" }[state] ??
    state;
};

let pausedForStats = false;

export const openStats = async () => {
  if (getClockState() === "running") {
    await fetch(`${API_BASE}/clock/pause`, { method: "POST" });
    applyClockState("paused");
    pausedForStats = true;
  }

  const data = await fetch(`${API_BASE}/stats`).then((response) =>
    response.json(),
  );

  const scalarEntries = Object.entries(data).filter(
    ([, value]) => typeof value !== "object",
  );
  const arrayEntries = Object.entries(data).filter(([, value]) =>
    Array.isArray(value),
  );

  let html = "";

  if (scalarEntries.length) {
    html += `<div class="stats-summary">`;
    html += scalarEntries
      .map(
        ([key, value]) => `
        <div class="stats-summary-item">
          <div class="label">${key.replace(/_/g, " ")}</div>
          <div class="value">${value}</div>
        </div>`,
      )
      .join("");
    html += `</div>`;
  }

  const mutationCounts = data.mutation_counts ?? {};
  const maxMutCount = Math.max(1, ...Object.values(mutationCounts));
  const allMutations = [
    ...MUTATION_PRIORITY,
    ...Object.keys(mutationCounts).filter(
      (m) => !MUTATION_PRIORITY.includes(m),
    ),
  ];

  html += `<div class="stats-section"><h4>Mutations</h4><div class="mutation-histogram">`;
  html += allMutations
    .map((m) => {
      const count = mutationCounts[m] ?? 0;
      const pct = ((count / maxMutCount) * 100).toFixed(1);
      const color = MUTATION_COLORS[m] ?? "#666";
      return `
      <div class="mutation-row">
        <span class="mut-label">${m.replace(/_/g, " ")}</span>
        <div class="mut-track"><div class="mut-fill" style="width:${pct}%;background:${color}"></div></div>
        <span class="mut-count">${count}</span>
      </div>`;
    })
    .join("");
  html += `</div></div>`;

  html += arrayEntries
    .map(([key, rows]) => {
      if (!rows.length) {
        return `<div class="stats-section"><h4>${key.replace(/_/g, " ")}</h4><span class="stats-empty">None</span></div>`;
      }

      const rawColumns = Object.keys(rows[0]).filter(
        (col) => col !== "x" && col !== "y",
      );
      const columns = [
        ...rawColumns.filter((col) => col === "id"),
        ...rawColumns.filter((col) => col === "age"),
        ...rawColumns.filter((col) => col !== "id" && col !== "age"),
      ];
      const maxAge = columns.includes("age")
        ? Math.max(...rows.map((row) => row.age ?? 0))
        : 0;

      const headerRow = columns
        .map((col) => `<th>${col.replace(/_/g, " ")}</th>`)
        .join("");
      const dataRows = rows
        .map((row) => {
          const cells = columns
            .map((col) => {
              if (col === "age") {
                const percentage =
                  maxAge > 0 ? ((row.age ?? 0) / maxAge) * 100 : 0;
                return `<td><div class="age-bar"><div style="width:${percentage.toFixed(1)}%"></div></div></td>`;
              }
              return `<td>${abbreviateField(row[col])}</td>`;
            })
            .join("");
          return `<tr>${cells}</tr>`;
        })
        .join("");

      return `
        <div class="stats-section">
          <h4>${key.replace(/_/g, " ")}</h4>
          <table class="stats-table">
            <thead><tr>${headerRow}</tr></thead>
            <tbody>${dataRows}</tbody>
          </table>
        </div>`;
    })
    .join("");

  modalBody.innerHTML = html;
  modalOverlay.classList.add("open");
};

export const closeStats = () => {
  modalOverlay.classList.remove("open");
  if (pausedForStats) {
    fetch(`${API_BASE}/clock/resume`, { method: "POST" });
    applyClockState("running");
    pausedForStats = false;
  }
};

// ── Config dialog ────────────────────────────────────────────────────────────

const CONFIG_STORAGE_KEY = "animalfarm_config";

const saveConfigToStorage = (values) => {
  localStorage.setItem(CONFIG_STORAGE_KEY, JSON.stringify(values));
};

const loadConfigFromStorage = () => {
  try {
    const raw = localStorage.getItem(CONFIG_STORAGE_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
};

const configOverlay = document.getElementById("config-overlay");

const CONFIG_FIELDS = [
  { key: "agent_count", id: "agent-count", parse: parseInt },
  { key: "num_springs", id: "num-springs", parse: parseInt },
  { key: "max_age", id: "max-age", parse: parseInt },
  { key: "adult_drain", id: "adult-drain", parse: parseInt },
  { key: "reproduction_chance", id: "reproduction-chance", parse: parseFloat },
  {
    key: "spontaneous_mutation_rate",
    id: "spontaneous-mutation-rate",
    parse: parseFloat,
  },
];

const syncPair = (rangeEl, numberEl) => {
  rangeEl.addEventListener("input", () => {
    numberEl.value = rangeEl.value;
  });
  numberEl.addEventListener("input", () => {
    const v = Math.max(+rangeEl.min, Math.min(+rangeEl.max, +numberEl.value));
    rangeEl.value = v;
  });
};

let configDefaults = {};

const populateDialog = (values) => {
  CONFIG_FIELDS.forEach(({ id }) => {
    const key = id.replace(/-/g, "_");
    const val = values[key] ?? values[id.replace(/-/g, "_")];
    const numEl = document.getElementById(`cfg-${id}`);
    const rngEl = document.getElementById(`cfg-${id}-range`);
    if (numEl && val !== undefined) numEl.value = val;
    if (rngEl && val !== undefined) rngEl.value = val;
  });
};

const initSyncPairs = () => {
  CONFIG_FIELDS.forEach(({ id }) => {
    const rng = document.getElementById(`cfg-${id}-range`);
    const num = document.getElementById(`cfg-${id}`);
    if (rng && num) syncPair(rng, num);
  });
};

initSyncPairs();

const populateSavedWorldsDropdown = (worlds) => {
  const select = document.getElementById("cfg-world-id");
  select.innerHTML = '<option value="">— generate random —</option>';

  for (const w of worlds) {
    const opt = document.createElement("option");
    opt.value = w.id;
    opt.textContent = w.name;
    opt.dataset.config = JSON.stringify(w.config ?? {});
    select.appendChild(opt);
  }
};

const onWorldSelect = () => {
  const select = document.getElementById("cfg-world-id");
  const opt = select.selectedOptions[0];

  if (!opt || !opt.dataset.config) return;

  const config = JSON.parse(opt.dataset.config);

  if (config.num_springs !== undefined) {
    document.getElementById("cfg-num-springs").value = config.num_springs;
    document.getElementById("cfg-num-springs-range").value = config.num_springs;
  }
};

document
  .getElementById("cfg-world-id")
  .addEventListener("change", onWorldSelect);

export const openConfigDialog = async () => {
  const [defaults, savedWorlds] = await Promise.all([
    fetch(`${API_BASE}/config`).then((r) => r.json()),
    fetch(`${API_BASE}/world/saved`).then((r) => r.json()),
  ]);

  configDefaults = defaults;
  const saved = loadConfigFromStorage();
  populateDialog(saved ? { ...defaults, ...saved } : defaults);
  populateSavedWorldsDropdown(savedWorlds);
  document.getElementById("cfg-world-id").value = "";
  configOverlay.classList.add("open");
};

export const closeConfigDialog = () => {
  configOverlay.classList.remove("open");
};

export const readConfigValues = () => {
  const result = {};
  CONFIG_FIELDS.forEach(({ key, id, parse }) => {
    const el = document.getElementById(`cfg-${id}`);
    if (el) result[key] = parse(el.value);
  });
  saveConfigToStorage(result);
  const worldId = document.getElementById("cfg-world-id")?.value;
  if (worldId) result.world_id = worldId;
  return result;
};

document
  .getElementById("config-close")
  .addEventListener("click", closeConfigDialog);
document
  .getElementById("config-cancel")
  .addEventListener("click", closeConfigDialog);
document
  .getElementById("config-reset")
  .addEventListener("click", () => populateDialog(configDefaults));
configOverlay.addEventListener("click", (event) => {
  if (event.target === configOverlay) closeConfigDialog();
});

document.getElementById("modal-close").addEventListener("click", closeStats);
modalOverlay.addEventListener("click", (event) => {
  if (event.target === modalOverlay) closeStats();
});

const btnFullscreen = document.getElementById("btn-fullscreen");
btnFullscreen.addEventListener("click", () => {
  if (!document.fullscreenElement) {
    document.documentElement.requestFullscreen();
  } else {
    document.exitFullscreen();
  }
});
document.addEventListener("fullscreenchange", () => {
  btnFullscreen.textContent = document.fullscreenElement
    ? "⛶ Exit Fullscreen"
    : "⛶ Fullscreen";
});

// ── Info icon tooltips ────────────────────────────────────────────────────────

const configTooltip = document.createElement("div");
configTooltip.id = "config-tooltip";
document.body.appendChild(configTooltip);

document.querySelectorAll(".info-icon").forEach((icon) => {
  icon.addEventListener("mouseenter", () => {
    const rect = icon.getBoundingClientRect();
    configTooltip.textContent = icon.dataset.tooltip;
    // right-align tooltip to the icon so it opens leftward inside the dialog
    configTooltip.style.top = `${rect.bottom + 7}px`;
    configTooltip.style.left = `${rect.right - 210}px`;
    configTooltip.classList.add("visible");
  });
  icon.addEventListener("mouseleave", () => {
    configTooltip.classList.remove("visible");
  });
});
