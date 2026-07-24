import { WORLD_WIDTH, WORLD_HEIGHT } from "./constants.js";

export const agents = new Map();
export const deadAgents = new Map();
export const plants = new Map();
export const rivers = new Map();

let _elevation = [];
export const setElevation = (data) => {
  _elevation = data ?? [];
};
export const getElevationAt = (x, y) => _elevation[y * WORLD_WIDTH + x] ?? 0.5;

let _temperature = [];
export const setTemperature = (data) => {
  _temperature = data ?? [];
};
export const getTemperatureAt = (x, y) =>
  _temperature[y * WORLD_WIDTH + x] ?? 0.5;

let _precipitation = [];
export const setPrecipitation = (data) => {
  _precipitation = data ?? [];
};
export const getPrecipitationAt = (x, y) =>
  _precipitation[y * WORLD_WIDTH + x] ?? 0.5;

const DIURNAL_AMPLITUDE = 0.1;
const PLANT_SHADE = 0.08;
const PLANT_SHADE_ADJACENT = 0.03;

export const getEffectivePrecipitationAt = (x, y) => getPrecipitationAt(x, y);

const shadeAt = (x, y) => {
  if ([...plants.values()].some((plant) => plant.x === x && plant.y === y))
    return PLANT_SHADE;
  const hasAdjacentPlant = [-1, 0, 1].some((dx) =>
    [-1, 0, 1].some(
      (dy) =>
        (dx !== 0 || dy !== 0) &&
        [...plants.values()].some(
          (plant) => plant.x === x + dx && plant.y === y + dy,
        ),
    ),
  );
  return hasAdjacentPlant ? PLANT_SHADE_ADJACENT : 0;
};

export const getEffectiveTemperatureAt = (x, y) => {
  const base = getTemperatureAt(x, y);
  return Math.max(0, Math.min(1, base + _diurnalOffset - shadeAt(x, y)));
};

let _clockState = "stopped";
let _tickCount = 0;
let _selectedAgentId = null;
let _selectedTile = null;
let _tickMs = 0;
let _isNight = false;
let _dayNumber = 1;
let _dayPhase = 0.0;
let _diurnalOffset = 0.0;

export const getClockState = () => _clockState;
export const getTickCount = () => _tickCount;
export const getSelectedAgentId = () => _selectedAgentId;
export const getSelectedTile = () => _selectedTile;
export const getTickMs = () => _tickMs;
export const getIsNight = () => _isNight;
export const getDayNumber = () => _dayNumber;
export const getDayPhase = () => _dayPhase;

export const setClockState = (state) => {
  _clockState = state;
};
export const setTickCount = (count) => {
  _tickCount = count;
};
export const setSelectedAgentId = (agentId) => {
  _selectedAgentId = agentId;
};
export const setSelectedTile = (tile) => {
  _selectedTile = tile;
};
export const setTickMs = (ms) => {
  _tickMs = ms;
};
export const setIsNight = (v) => {
  _isNight = v;
};
export const setDayNumber = (v) => {
  _dayNumber = v;
};
export const setDayPhase = (v) => {
  _dayPhase = v;
};
export const setDiurnalOffset = (v) => {
  _diurnalOffset = v;
};

export const snapAgentsToGrid = () => {
  for (const agent of agents.values()) {
    agent.posQueue = [];
    agent.arc = null;
    agent.displayX = agent.x;
    agent.displayY = agent.y;
  }
};

export const clearWorld = () => {
  agents.clear();
  deadAgents.clear();
  plants.clear();
  rivers.clear();
  setSelectedAgentId(null);
  setSelectedTile(null);
  _elevation = [];
  _temperature = [];
  _precipitation = [];
};

export const upsertAgent = (agentData) => {
  const existing = agents.get(agentData.id);

  if (!existing) {
    agentData.displayX = agentData.x;
    agentData.displayY = agentData.y;
    agentData.posQueue = [];
    agentData.arc = null;
  } else {
    agentData.displayX = existing.displayX ?? existing.x;
    agentData.displayY = existing.displayY ?? existing.y;
    agentData.posQueue = existing.posQueue ?? [];
    agentData.arc = existing.arc ?? null;

    if (existing.x !== agentData.x || existing.y !== agentData.y) {
      agentData.posQueue.push({ x: agentData.x, y: agentData.y });
      if (agentData.posQueue.length > 3) {
        const snap = agentData.posQueue.shift();
        agentData.displayX = snap.x;
        agentData.displayY = snap.y;
      }
    }
  }

  agents.set(agentData.id, agentData);
  return agentData;
};

export const upsertPlant = (plantData) => {
  plants.set(plantData.id, plantData);
};

export const isRiverTile = (x, y) =>
  [...rivers.values()].some((r) =>
    r.tiles.some(([tx, ty]) => tx === x && ty === y),
  );

export const upsertRiver = (riverData) => {
  rivers.set(riverData.river_id, {
    id: riverData.river_id,
    tiles: riverData.tiles.slice(),
    complete: riverData.complete,
  });
};

export const addRiverTile = (riverId, tileX, tileY) => {
  const existing = rivers.get(riverId);
  const river = existing ?? { id: riverId, tiles: [], complete: false };
  if (!existing) rivers.set(riverId, river);
  river.tiles.push([tileX, tileY]);
};
