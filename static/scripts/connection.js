import { API_BASE, WS_URL } from "./constants.js";
import {
  agents,
  deadAgents,
  plants,
  rivers,
  upsertAgent,
  upsertPlant,
  upsertRiver,
  addRiverTile,
  clearWorld,
  setTickCount,
  setTickMs,
  getTickMs,
  getSelectedAgentId,
  getSelectedTile,
  setSelectedAgentId,
  setIsNight,
  setDayNumber,
  setDayPhase,
  setDiurnalOffset,
  setElevation,
  setTemperature,
  setPrecipitation,
  setClouds,
  isRiverTile,
} from "./state.js";
import {
  applyClockState,
  updateAgentPanel,
  updateTilePanel,
  syncCounters,
  updateDayNightUI,
} from "./ui.js";

const tickEl = document.getElementById("tick");
const statusEl = document.getElementById("status");

let _lastTickAt = 0;
let _gapSamples = [];
const _GAP_REPORT_INTERVAL = 10;

export const post = async (path, body = null) => {
  try {
    const options = { method: "POST" };
    if (body !== null) {
      options.headers = { "Content-Type": "application/json" };
      options.body = JSON.stringify(body);
    }
    await fetch(`${API_BASE}${path}`, options);
  } catch (error) {
    console.error("POST", path, error);
  }
};

const handleMessage = (rawData) => {
  const message = JSON.parse(rawData);

  switch (message.event) {
    case "game_started":
      clearWorld();
      updateAgentPanel(null);
      message.agents.forEach((agentData) => upsertAgent(agentData));
      message.plants.forEach(upsertPlant);
      message.rivers.forEach(upsertRiver);
      setElevation(message.elevation);
      setTemperature(message.temperature);
      setPrecipitation(message.precipitation);
      setClouds(message.clouds ?? []);
      applyClockState("running");
      break;

    case "agent_created":
    case "agent_born": {
      const agent = upsertAgent(message.agent);
      if (agent.id === getSelectedAgentId()) updateAgentPanel(agent);
      break;
    }

    case "agent_moved":
    case "agent_sleeping": {
      const agent = upsertAgent(message.agent);
      if (agent.id === getSelectedAgentId()) updateAgentPanel(agent);
      break;
    }

    case "agent_ate": {
      const agent = upsertAgent(message.agent);
      if (agent.id === getSelectedAgentId()) updateAgentPanel(agent);
      break;
    }

    case "agent_died":
      deadAgents.set(message.agent.id, message.agent);
      agents.delete(message.agent.id);
      if (getSelectedAgentId() === message.agent.id) {
        setSelectedAgentId(null);
        updateAgentPanel(null);
      }
      break;

    case "plant_placed":
      upsertPlant(message.plant);
      break;

    case "fruit_grew":
      for (const { plant_id, fruit_count } of message.updates) {
        const plant = plants.get(plant_id);
        if (plant) plant.fruit_count = fruit_count;
      }
      break;

    case "fruit_depleted": {
      const plant = plants.get(message.plant_id);
      if (plant) plant.fruit_count = 0;
      break;
    }

    case "river_tile_added":
      addRiverTile(message.river_id, message.x, message.y);
      break;

    case "river_completed":
      if (rivers.has(message.river_id))
        rivers.get(message.river_id).complete = true;
      break;

    case "tick": {
      const now = performance.now();
      const gap = _lastTickAt ? now - _lastTickAt : 0;
      _lastTickAt = now;
      const t0 = performance.now();
      setTickCount(message.tick);
      tickEl.textContent = message.tick;

      if (message.is_night !== undefined) setIsNight(message.is_night);
      if (message.day_number !== undefined) setDayNumber(message.day_number);
      if (message.day_phase !== undefined) setDayPhase(message.day_phase);
      if (message.diurnal_offset !== undefined)
        setDiurnalOffset(message.diurnal_offset);
      if (message.clouds !== undefined) setClouds(message.clouds);
      updateDayNightUI();
      const tile = getSelectedTile();
      if (tile) {
        const plant = [...plants.values()].find(
          ({ x, y }) => x === tile.x && y === tile.y,
        );
        updateTilePanel(
          tile.x,
          tile.y,
          plant ?? null,
          isRiverTile(tile.x, tile.y),
        );
      }
      const handleMs = performance.now() - t0;

      if (gap > 0) {
        _gapSamples.push(gap);
        if (_gapSamples.length >= _GAP_REPORT_INTERVAL) {
          const avgGap =
            _gapSamples.reduce((a, b) => a + b, 0) / _gapSamples.length;
          _gapSamples = [];
          post("/clock/observed-gap", { gap_ms: avgGap });
        }
      }
      break;
    }

    case "game_over":
      applyClockState("stopped");
      statusEl.textContent = "Game Over";
      break;
  }

  syncCounters();
};

export const fetchState = async () => {
  const [worldResponse, clockResponse] = await Promise.all([
    fetch(`${API_BASE}/world`),
    fetch(`${API_BASE}/clock`),
  ]);
  const worldData = await worldResponse.json();
  const clockData = await clockResponse.json();
  agents.clear();
  deadAgents.clear();
  plants.clear();
  rivers.clear();

  worldData.agents.forEach((agentData) =>
    agentData.alive
      ? upsertAgent(agentData)
      : deadAgents.set(agentData.id, agentData),
  );
  (worldData.plants ?? []).forEach(upsertPlant);
  worldData.rivers.forEach(upsertRiver);
  setElevation(worldData.elevation);
  setTemperature(worldData.temperature);
  setPrecipitation(worldData.precipitation);
  setClouds(worldData.clouds ?? []);

  setTickCount(clockData.tick_count);
  tickEl.textContent = clockData.tick_count || "—";
  setTickMs(clockData.interval * 1000);
  setIsNight(clockData.is_night ?? false);
  setDayNumber(clockData.day_number ?? 1);
  setDayPhase(clockData.day_phase ?? 0);
  applyClockState(clockData.state);
  updateDayNightUI();
  syncCounters();
};

export const connect = () => {
  const ws = new WebSocket(WS_URL);

  ws.onopen = () => fetchState();
  ws.onerror = () => ws.close();
  ws.onclose = () => {
    statusEl.textContent = "Disconnected — retrying…";
    setTimeout(connect, 2000);
  };
  ws.onmessage = ({ data }) => handleMessage(data);
};
