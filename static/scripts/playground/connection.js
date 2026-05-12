import { API_BASE, WS_URL } from './constants.js'
import { agents, food, upsertAgent, upsertFood, loadSnapshot, setTick, setAutoRunning } from './state.js'
import { updateAgentPanel, setStatus, setTickDisplay, setAutoButton, refreshActiveScenario, setScenarioStatus } from './ui.js'

const handleMessage = (rawData) => {
  const msg = JSON.parse(rawData)

  switch (msg.event) {
    case 'pg_reset':
      loadSnapshot(msg)
      setTickDisplay(msg.tick ?? 0)
      updateAgentPanel()
      refreshActiveScenario()
      setScenarioStatus(null, 0)
      break

    case 'agent_moved':
    case 'agent_ate':
    case 'agent_picked_up_food':
    case 'agent_born':
      upsertAgent(msg.agent)
      updateAgentPanel()
      break

    case 'agent_died':
      upsertAgent({ ...msg.agent, alive: false })
      updateAgentPanel()
      break

    case 'food_placed':
    case 'food_grew':
      upsertFood(msg.food)
      break

    case 'food_removed':
      food.delete(msg.food.id)
      break

    case 'tick':
      setTick(msg.tick)
      setTickDisplay(msg.tick)
      updateAgentPanel()
      break

    case 'pg_auto':
      setAutoRunning(msg.running)
      setAutoButton(msg.running)
      break

    case 'pg_scenario_complete':
      setScenarioStatus(msg.result, msg.tick)
      break
  }
}

export const fetchScenarios = async () => {
  try {
    const res = await fetch(`${API_BASE}/scenarios`)
    return await res.json()
  } catch (e) {
    return { scenarios: [], error: String(e) }
  }
}

export const post = async (path) => {
  try {
    await fetch(`${API_BASE}${path}`, { method: 'POST' })
  } catch (e) {
    console.error('POST', path, e)
  }
}

export const postJson = async (path, body) => {
  try {
    await fetch(`${API_BASE}${path}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    })
  } catch (e) {
    console.error('POST', path, e)
  }
}

export const connect = () => {
  const ws = new WebSocket(WS_URL)
  ws.onopen = () => setStatus('Connected')
  ws.onerror = () => ws.close()
  ws.onclose = () => {
    setStatus('Disconnected — retrying…')
    setTimeout(connect, 2000)
  }
  ws.onmessage = ({ data }) => handleMessage(data)
}
