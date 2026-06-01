import {
  WORLD_WIDTH,
  WORLD_HEIGHT,
  MUTATION_COLORS,
  MUTATION_PRIORITY,
  NO_MUTATION_COLOR,
} from "./constants.js";
import {
  agents,
  food,
  rivers,
  groups,
  getClockState,
  getSelectedAgentId,
  getTickMs,
  getDayPhase,
  getElevationAt,
  getClouds,
  getEffectivePrecipitationAt,
  getEffectiveTemperatureAt,
} from "./state.js";
import { camera, viewport, scrollCamera } from "./camera.js";

const canvas = document.getElementById("game");
const ctx = canvas.getContext("2d");

const TASK_COLORS = {
  seek_food: "#f1c40f",
  drink: "#3498db",
  sleep: "#9b59b6",
  seek_shelter: "#e67e22",
  find_shelter: "#e67e22",
  flee: "#e74c3c",
  mate: "#e91e63",
  explore: "#95a5a6",
  return_home: "#2ecc71",
};

const drawAgentPath = (agent, renderX, renderY) => {
  if (!agent.path || !agent.path.length) return;

  const taskName = agent.active_task?.name ?? "explore";
  const color = TASK_COLORS[taskName] ?? "#ffffff";
  const half = viewport.cellSize / 2;

  const startX = renderX * viewport.cellSize + half - camera.x;
  const startY = renderY * viewport.cellSize + half - camera.y;

  ctx.save();
  ctx.strokeStyle = color;
  ctx.lineWidth = 1.5;
  ctx.globalAlpha = 0.65;
  ctx.setLineDash([4, 3]);
  ctx.beginPath();
  ctx.moveTo(startX, startY);

  for (const [px, py] of agent.path) {
    ctx.lineTo(
      px * viewport.cellSize + half - camera.x,
      py * viewport.cellSize + half - camera.y,
    );
  }

  ctx.stroke();
  ctx.setLineDash([]);

  const [gx, gy] = agent.path[agent.path.length - 1];
  const goalX = gx * viewport.cellSize + half - camera.x;
  const goalY = gy * viewport.cellSize + half - camera.y;

  ctx.globalAlpha = 0.85;
  ctx.beginPath();
  ctx.arc(goalX, goalY, viewport.cellSize * 0.28, 0, Math.PI * 2);
  ctx.lineWidth = 1.5;
  ctx.stroke();

  const fontSize = Math.max(10, Math.round(viewport.cellSize * 0.55));
  ctx.font = `${fontSize}px Roboto, sans-serif`;
  ctx.textAlign = "center";
  ctx.textBaseline = "bottom";
  ctx.fillStyle = color;
  ctx.fillText(
    taskName.replace(/_/g, " "),
    goalX,
    goalY - viewport.cellSize * 0.35,
  );

  ctx.restore();
};

const agentColor = (agent) => {
  const expressed = agent.mutations ?? [];
  const match = MUTATION_PRIORITY.find((m) => expressed.includes(m));
  return match ? MUTATION_COLORS[match] : NO_MUTATION_COLOR;
};

const isVisible = (screenX, screenY) =>
  screenX > -viewport.cellSize &&
  screenX < canvas.width &&
  screenY > -viewport.cellSize &&
  screenY < canvas.height;

const drawRivers = () => {
  const colStart = Math.floor(camera.x / viewport.cellSize);
  const colEnd = Math.min(
    Math.ceil((camera.x + canvas.width) / viewport.cellSize),
    WORLD_WIDTH,
  );
  const rowStart = Math.floor(camera.y / viewport.cellSize);
  const rowEnd = Math.min(
    Math.ceil((camera.y + canvas.height) / viewport.cellSize),
    WORLD_HEIGHT,
  );

  ctx.fillStyle = "rgba(41, 128, 185, 0.55)";
  for (const river of rivers.values()) {
    for (const [tileX, tileY] of river.tiles) {
      if (
        tileX < colStart ||
        tileX >= colEnd ||
        tileY < rowStart ||
        tileY >= rowEnd
      )
        continue;
      ctx.fillRect(
        tileX * viewport.cellSize - camera.x,
        tileY * viewport.cellSize - camera.y,
        viewport.cellSize,
        viewport.cellSize,
      );
    }
  }
};

const drawTerrain = () => {
  const colStart = Math.floor(camera.x / viewport.cellSize);
  const colEnd = Math.min(
    Math.ceil((camera.x + canvas.width) / viewport.cellSize),
    WORLD_WIDTH,
  );
  const rowStart = Math.floor(camera.y / viewport.cellSize);
  const rowEnd = Math.min(
    Math.ceil((camera.y + canvas.height) / viewport.cellSize),
    WORLD_HEIGHT,
  );

  for (let col = colStart; col < colEnd; col++) {
    for (let row = rowStart; row < rowEnd; row++) {
      const elev = getElevationAt(col, row);
      const v = Math.round(5 + elev * 65);
      const hex = v.toString(16).padStart(2, "0");
      ctx.fillStyle = `#${hex}${hex}${hex}`;
      ctx.fillRect(
        col * viewport.cellSize - camera.x,
        row * viewport.cellSize - camera.y,
        viewport.cellSize,
        viewport.cellSize,
      );
    }
  }
};

const drawGrid = () => {
  ctx.strokeStyle = "rgba(255,255,255,0.04)";
  ctx.lineWidth = 0.5;
  ctx.beginPath();

  const colStart = Math.floor(camera.x / viewport.cellSize);
  const colEnd = Math.min(
    Math.ceil((camera.x + canvas.width) / viewport.cellSize),
    WORLD_WIDTH,
  );

  const rowStart = Math.floor(camera.y / viewport.cellSize);
  const rowEnd = Math.min(
    Math.ceil((camera.y + canvas.height) / viewport.cellSize),
    WORLD_HEIGHT,
  );

  for (let col = colStart; col <= colEnd; col++) {
    const x = col * viewport.cellSize - camera.x;
    ctx.moveTo(x, 0);
    ctx.lineTo(x, canvas.height);
  }

  for (let row = rowStart; row <= rowEnd; row++) {
    const y = row * viewport.cellSize - camera.y;
    ctx.moveTo(0, y);
    ctx.lineTo(canvas.width, y);
  }

  ctx.stroke();
};

const drawVision = (agent, visionRadius) => {
  const centerX =
    agent.x * viewport.cellSize + viewport.cellSize / 2 - camera.x;
  const centerY =
    agent.y * viewport.cellSize + viewport.cellSize / 2 - camera.y;
  const pixelRadius = visionRadius * viewport.cellSize;

  ctx.beginPath();
  ctx.moveTo(centerX, centerY - pixelRadius);
  ctx.lineTo(centerX + pixelRadius, centerY);
  ctx.lineTo(centerX, centerY + pixelRadius);
  ctx.lineTo(centerX - pixelRadius, centerY);
  ctx.closePath();
  ctx.fillStyle = "rgba(255,255,255,0.05)";
  ctx.fill();
  ctx.strokeStyle = "rgba(255,255,255,0.35)";
  ctx.lineWidth = 1;
  ctx.setLineDash([6, 4]);
  ctx.stroke();
  ctx.setLineDash([]);
};

const drawRestMemory = (agent) => {
  const entries = agent.memory?.rest;
  if (!entries || entries.length === 0) return;
  const best = entries.reduce((a, b) => (b.added_tick > a.added_tick ? b : a));
  const [rx, ry] = best.pos;
  const screenX = rx * viewport.cellSize - camera.x;
  const screenY = ry * viewport.cellSize - camera.y;
  if (!isVisible(screenX, screenY)) return;
  ctx.fillStyle = "rgba(155, 89, 182, 0.35)";
  ctx.fillRect(screenX, screenY, viewport.cellSize, viewport.cellSize);
  ctx.strokeStyle = "rgba(155, 89, 182, 0.8)";
  ctx.lineWidth = 1;
  ctx.strokeRect(screenX, screenY, viewport.cellSize, viewport.cellSize);
};

const drawFood = (visibleFoodIds) => {
  const colStart = Math.floor(camera.x / viewport.cellSize);
  const colEnd = Math.min(
    Math.ceil((camera.x + canvas.width) / viewport.cellSize),
    WORLD_WIDTH,
  );
  const rowStart = Math.floor(camera.y / viewport.cellSize);
  const rowEnd = Math.min(
    Math.ceil((camera.y + canvas.height) / viewport.cellSize),
    WORLD_HEIGHT,
  );

  for (const foodItem of food.values()) {
    if (
      foodItem.x < colStart ||
      foodItem.x >= colEnd ||
      foodItem.y < rowStart ||
      foodItem.y >= rowEnd
    )
      continue;

    const screenX = foodItem.x * viewport.cellSize - camera.x;
    const screenY = foodItem.y * viewport.cellSize - camera.y;
    const isHighlighted = visibleFoodIds.has(foodItem.id);
    ctx.fillStyle = isHighlighted ? "#f1c40f" : "#27ae60";
    ctx.beginPath();
    ctx.arc(
      screenX + viewport.cellSize / 2,
      screenY + viewport.cellSize / 2,
      isHighlighted ? viewport.cellSize * 0.17 : viewport.cellSize * 0.13,
      0,
      Math.PI * 2,
    );
    ctx.fill();
  }
};

const advanceArc = (agent, now) => {
  if (agent.arc && (now - agent.arc.startTime) / agent.arc.duration >= 1) {
    agent.displayX = agent.arc.endX;
    agent.displayY = agent.arc.endY;
    agent.arc = null;
  }

  if (agent.arc) return;

  const tickMs = getTickMs();

  if (agent.posQueue.length) {
    const point = agent.posQueue.shift();
    agent.arc = {
      startX: agent.displayX,
      startY: agent.displayY,
      endX: point.x,
      endY: point.y,
      startTime: now,
      duration: tickMs > 0 ? tickMs : 150,
    };
  }
};

const agentRenderPosition = (agent, now) => {
  if (!agent.arc) return [agent.displayX, agent.displayY];

  const progress = Math.min(
    (now - agent.arc.startTime) / agent.arc.duration,
    1,
  );

  return [
    agent.arc.startX + (agent.arc.endX - agent.arc.startX) * progress,
    agent.arc.startY + (agent.arc.endY - agent.arc.startY) * progress,
  ];
};

const drawLivingAgents = () => {
  const now = performance.now();
  const selectedId = getSelectedAgentId();

  for (const agent of agents.values()) {
    advanceArc(agent, now);
    const [renderX, renderY] = agentRenderPosition(agent, now);
    const screenX = renderX * viewport.cellSize - camera.x;
    const screenY = renderY * viewport.cellSize - camera.y;

    if (!isVisible(screenX, screenY)) continue;

    const centerX = screenX + viewport.cellSize / 2;
    const centerY = screenY + viewport.cellSize / 2;

    if (agent.id === selectedId) {
      drawAgentPath(agent, renderX, renderY);
      ctx.beginPath();
      ctx.arc(centerX, centerY, viewport.cellSize * 0.43, 0, Math.PI * 2);
      ctx.strokeStyle = "rgba(255,255,255,0.8)";
      ctx.lineWidth = 2;
      ctx.stroke();
    }

    ctx.beginPath();
    ctx.arc(centerX, centerY, viewport.cellSize * 0.3, 0, Math.PI * 2);
    ctx.fillStyle = agentColor(agent);
    ctx.fill();
    ctx.strokeStyle = "rgba(255,255,255,0.15)";
    ctx.lineWidth = 1;
    ctx.stroke();

    if (agent.carried_food) {
      const dotX = centerX + viewport.cellSize * 0.18;
      const dotY = centerY - viewport.cellSize * 0.28;
      const dotR = viewport.cellSize * 0.1;
      ctx.beginPath();
      ctx.arc(dotX, dotY, dotR, 0, Math.PI * 2);
      ctx.fillStyle = "#27ae60";
      ctx.fill();
      ctx.strokeStyle = "rgba(255,255,255,0.7)";
      ctx.lineWidth = 1;
      ctx.stroke();
    }
  }
};

const nightOverlayAlpha = (phase) => {
  if (phase < 0.4) return 0;
  if (phase < 0.5) return (phase - 0.4) / 0.1;
  if (phase < 0.9) return 1;
  return 1 - (phase - 0.9) / 0.1;
};

const drawNightOverlay = () => {
  const alpha = nightOverlayAlpha(getDayPhase()) * 0.55;
  if (alpha <= 0) return;
  ctx.fillStyle = `rgba(10, 10, 50, ${alpha.toFixed(3)})`;
  ctx.fillRect(0, 0, canvas.width, canvas.height);
};

const drawPrompt = () => {
  if (agents.size !== 0 || getClockState() !== "stopped") return;

  ctx.textAlign = "center";
  ctx.textBaseline = "middle";
  ctx.fillStyle = "#2a2a2a";
  ctx.font = "14px Roboto, sans-serif";
  ctx.fillText(
    'Press "Start Game" to begin',
    canvas.width / 2,
    canvas.height / 2,
  );
};

let _climateOverlay = 0; // 0=off 1=temperature 2=precipitation

document.addEventListener("keydown", (e) => {
  if (e.key === "c" || e.key === "C") {
    _climateOverlay = (_climateOverlay + 1) % 3;
  }
});

const CLIMATE_OVERLAY_LABELS = ["", "Temperature", "Precipitation"];

const drawClimateOverlay = () => {
  if (_climateOverlay === 0) return;

  const colStart = Math.floor(camera.x / viewport.cellSize);
  const colEnd = Math.min(
    Math.ceil((camera.x + canvas.width) / viewport.cellSize),
    WORLD_WIDTH,
  );
  const rowStart = Math.floor(camera.y / viewport.cellSize);
  const rowEnd = Math.min(
    Math.ceil((camera.y + canvas.height) / viewport.cellSize),
    WORLD_HEIGHT,
  );

  for (let col = colStart; col < colEnd; col++) {
    for (let row = rowStart; row < rowEnd; row++) {
      const val =
        _climateOverlay === 1
          ? getEffectiveTemperatureAt(col, row)
          : getEffectivePrecipitationAt(col, row);
      const alpha = (val * 0.65).toFixed(3);
      ctx.fillStyle =
        _climateOverlay === 1
          ? `rgba(231,76,60,${alpha})`
          : `rgba(52,152,219,${alpha})`;
      ctx.fillRect(
        col * viewport.cellSize - camera.x,
        row * viewport.cellSize - camera.y,
        viewport.cellSize,
        viewport.cellSize,
      );
    }
  }

  ctx.font = "bold 13px Roboto, sans-serif";
  ctx.textAlign = "left";
  ctx.textBaseline = "bottom";
  ctx.fillStyle =
    _climateOverlay === 1 ? "rgba(231,76,60,0.9)" : "rgba(52,152,219,0.9)";
  ctx.fillText(CLIMATE_OVERLAY_LABELS[_climateOverlay], 8, canvas.height - 8);
};

const drawClouds = () => {
  const clouds = getClouds();
  if (!clouds.length) return;

  for (const cloud of clouds) {
    const screenX = cloud.cx * viewport.cellSize - camera.x;
    const screenY = cloud.cy * viewport.cellSize - camera.y;
    const screenRadius = cloud.radius * viewport.cellSize;
    const alpha = cloud.strength * 0.32;
    const grad = ctx.createRadialGradient(
      screenX,
      screenY,
      0,
      screenX,
      screenY,
      screenRadius,
    );
    grad.addColorStop(0, `rgba(180,200,230,${alpha.toFixed(3)})`);
    grad.addColorStop(1, "rgba(180,200,230,0)");
    ctx.fillStyle = grad;
    ctx.beginPath();
    ctx.arc(screenX, screenY, screenRadius, 0, Math.PI * 2);
    ctx.fill();
  }
};

let lastFrameTime = 0;
let lastDrawTime = 0;

const drawTimes = [];
const DRAW_SAMPLE = 10;

const recordDrawTime = (ms) => {
  drawTimes.push(ms);
  if (drawTimes.length > DRAW_SAMPLE) drawTimes.shift();
};

const avgDrawTime = () =>
  drawTimes.length === 0
    ? 0
    : drawTimes.reduce((a, b) => a + b, 0) / drawTimes.length;

const autoInterval = () => {
  const avg = avgDrawTime();
  if (avg < 10) return 0;
  if (avg < 20) return 1000 / 30;
  if (avg < 40) return 1000 / 15;
  return 1000 / 10;
};

const frame = (now) => {
  const deltaTime = Math.min((now - lastFrameTime) / 1000, 0.1);
  lastFrameTime = now;

  scrollCamera(deltaTime);

  const interval = autoInterval();
  if (interval > 0 && now - lastDrawTime < interval) {
    requestAnimationFrame(frame);
    return;
  }
  lastDrawTime = now;

  const drawStart = performance.now();

  ctx.fillStyle = "#0a0a0a";
  ctx.fillRect(0, 0, canvas.width, canvas.height);

  const selectedId = getSelectedAgentId();
  const selectedAgent = selectedId ? agents.get(selectedId) : null;
  const visionRadius = selectedAgent
    ? selectedAgent.group_id
      ? Math.round(selectedAgent.vision_range * 1.5)
      : selectedAgent.vision_range
    : 0;

  const visibleFoodIds = new Set();
  if (selectedAgent) {
    for (const foodItem of food.values()) {
      if (
        Math.abs(foodItem.x - selectedAgent.x) +
          Math.abs(foodItem.y - selectedAgent.y) <=
        visionRadius
      ) {
        visibleFoodIds.add(foodItem.id);
      }
    }
  }

  drawTerrain();
  drawClimateOverlay();
  drawGrid();
  drawRivers();

  if (selectedAgent) drawVision(selectedAgent, visionRadius);
  if (selectedAgent) drawRestMemory(selectedAgent);

  drawFood(visibleFoodIds);
  drawLivingAgents();
  drawClouds();
  drawNightOverlay();
  drawPrompt();

  recordDrawTime(performance.now() - drawStart);

  requestAnimationFrame(frame);
};

export const startRenderLoop = () => requestAnimationFrame(frame);
