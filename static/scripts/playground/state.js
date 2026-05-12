export const agents = new Map()
export const food = new Map()

let _tick = 0
let _autoRunning = false
let _activeScenario = null

export const getTick = () => _tick
export const setTick = (t) => { _tick = t }
export const isAutoRunning = () => _autoRunning
export const setAutoRunning = (v) => { _autoRunning = v }
export const getActiveScenario = () => _activeScenario
export const setActiveScenario = (i) => { _activeScenario = i }

export const upsertAgent = (data) => {
  agents.set(data.id, data)
  return data
}

export const upsertFood = (data) => food.set(data.id, data)

export const loadSnapshot = (snapshot) => {
  agents.clear()
  food.clear()
  snapshot.agents.forEach(upsertAgent)
  snapshot.food.forEach(upsertFood)
  setTick(snapshot.tick ?? 0)
  setActiveScenario(snapshot.active_scenario ?? null)
}
