import { API_BASE, WS_URL } from './constants.js'
import {
  agents, deadAgents, food, rivers, groups,
  upsertAgent, upsertFood, upsertRiver, addRiverTile,
  clearWorld, setTickCount, setTickMs, getSelectedAgentId, setSelectedAgentId,
  setIsNight, setDayNumber, setDayPhase,
} from './state.js'
import { applyClockState, updateAgentPanel, syncCounters, updateDayNightUI } from './ui.js'

const tickEl = document.getElementById('tick')
const statusEl = document.getElementById('status')

export const post = async (path) => {
  try {
    await fetch(`${API_BASE}${path}`, { method: 'POST' })
  } catch (error) {
    console.error('POST', path, error)
  }
}

const handleMessage = (rawData) => {
  const message = JSON.parse(rawData)

  switch (message.event) {
    case 'game_started':
      clearWorld()
      updateAgentPanel(null)
      message.agents.forEach((agentData) => upsertAgent(agentData))
      message.food.forEach(upsertFood)
      message.rivers.forEach(upsertRiver)
      applyClockState('running')
      break

    case 'agent_created':
    case 'agent_born':
    case 'agent_picked_up_food': {
      const agent = upsertAgent(message.agent, { mustStop: true })
      if (agent.id === getSelectedAgentId()) updateAgentPanel(agent)
      break
    }

    case 'agent_moved': {
      const agent = upsertAgent(message.agent)
      if (agent.id === getSelectedAgentId()) updateAgentPanel(agent)
      break
    }

    case 'agent_ate': {
      const agent = upsertAgent(message.agent, { mustStop: true })
      food.delete(message.food_id)
      if (agent.id === getSelectedAgentId()) updateAgentPanel(agent)
      break
    }

    case 'agent_died':
      deadAgents.set(message.agent.id, message.agent)
      agents.delete(message.agent.id)
      if (getSelectedAgentId() === message.agent.id) {
        setSelectedAgentId(null)
        updateAgentPanel(null)
      }
      break

    case 'group_formed':
      groups.set(message.group_id, { id: message.group_id })
      break

    case 'group_disbanded':
      groups.delete(message.group_id)
      break

    case 'food_placed':
    case 'food_grew':
      upsertFood(message.food)
      break

    case 'food_removed':
      food.delete(message.food.id)
      break

    case 'food_drowned':
      food.delete(message.food_id)
      break

    case 'river_tile_added':
      addRiverTile(message.river_id, message.x, message.y)
      break

    case 'river_completed':
      if (rivers.has(message.river_id)) rivers.get(message.river_id).complete = true
      break

    case 'tick':
      setTickCount(message.tick)
      tickEl.textContent = message.tick
      if (message.is_night !== undefined) setIsNight(message.is_night)
      if (message.day_number !== undefined) setDayNumber(message.day_number)
      if (message.day_phase !== undefined) setDayPhase(message.day_phase)
      updateDayNightUI()
      break

    case 'game_over':
      applyClockState('stopped')
      statusEl.textContent = 'Game Over'
      break
  }

  syncCounters()
}

export const fetchState = async () => {
  const [worldResponse, clockResponse] = await Promise.all([
    fetch(`${API_BASE}/world`),
    fetch(`${API_BASE}/clock`)
  ])
  const worldData = await worldResponse.json()
  const clockData = await clockResponse.json()

  agents.clear()
  deadAgents.clear()
  food.clear()
  rivers.clear()
  groups.clear()

  worldData.agents.forEach((agentData) =>
    agentData.alive ? upsertAgent(agentData) : deadAgents.set(agentData.id, agentData)
  )
  worldData.food.forEach(upsertFood)
  worldData.rivers.forEach(upsertRiver)
  ;(worldData.groups ?? []).forEach((group) => groups.set(group.id, group))

  setTickCount(clockData.tick_count)
  tickEl.textContent = clockData.tick_count || '—'
  setTickMs(clockData.interval * 1000)
  setIsNight(clockData.is_night ?? false)
  setDayNumber(clockData.day_number ?? 1)
  setDayPhase(clockData.day_phase ?? 0)
  applyClockState(clockData.state)
  updateDayNightUI()
  syncCounters()
}

export const connect = () => {
  const ws = new WebSocket(WS_URL)

  ws.onopen = () => fetchState()
  ws.onerror = () => ws.close()
  ws.onclose = () => {
    statusEl.textContent = 'Disconnected — retrying…'
    setTimeout(connect, 2000)
  }
  ws.onmessage = ({ data }) => handleMessage(data)
}
