import { WORLD_WIDTH } from "./constants.js";

export const agents = new Map();
export const deadAgents = new Map();
export const food = new Map();
export const rivers = new Map();
export const groups = new Map();

let _elevation = [];
export const setElevation = (data) => {
  _elevation = data ?? [];
};
export const getElevationAt = (x, y) => _elevation[y * WORLD_WIDTH + x] ?? 0.5;

let _clockState = "stopped";
let _tickCount = 0;
let _selectedAgentId = null;
let _tickMs = 0;
let _isNight = false;
let _dayNumber = 1;
let _dayPhase = 0.0;
let _maxHunger = 80;
let _maxRest = 80;
let _maxWater = 80;

export const getClockState = () => _clockState;
export const getTickCount = () => _tickCount;
export const getSelectedAgentId = () => _selectedAgentId;
export const getTickMs = () => _tickMs;
export const getIsNight = () => _isNight;
export const getDayNumber = () => _dayNumber;
export const getDayPhase = () => _dayPhase;
export const getMaxHunger = () => _maxHunger;
export const getMaxRest = () => _maxRest;
export const getMaxWater = () => _maxWater;

export const setClockState = (state) => {
  _clockState = state;
};
export const setTickCount = (count) => {
  _tickCount = count;
};
export const setSelectedAgentId = (agentId) => {
  _selectedAgentId = agentId;
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
export const setMaxHunger = (v) => {
  _maxHunger = v;
};
export const setMaxRest = (v) => {
  _maxRest = v;
};
export const setMaxWater = (v) => {
  _maxWater = v;
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
  food.clear();
  rivers.clear();
  groups.clear();
  setSelectedAgentId(null);
  _elevation = [];
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

export const upsertFood = (foodData) => {
  food.set(foodData.id, foodData);
};

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
