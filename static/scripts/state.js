export const agents = new Map()
export const deadAgents = new Map()
export const food = new Map()
export const rivers = new Map()
export const groups = new Map()

let _clockState = 'stopped'
let _tickCount = 0
let _selectedAgentId = null
let _tickMs = 0

export const getClockState = () => _clockState
export const getTickCount = () => _tickCount
export const getSelectedAgentId = () => _selectedAgentId
export const getTickMs = () => _tickMs

export const setClockState = (state) => { _clockState = state }
export const setTickCount = (count) => { _tickCount = count }
export const setSelectedAgentId = (agentId) => { _selectedAgentId = agentId }
export const setTickMs = (ms) => { _tickMs = ms }

export const clearWorld = () => {
  agents.clear()
  deadAgents.clear()
  food.clear()
  rivers.clear()
  groups.clear()
  setSelectedAgentId(null)
}

export const upsertAgent = (agentData, { mustStop = false } = {}) => {
  const existing = agents.get(agentData.id)

  if (!existing) {
    agentData.displayX = agentData.x
    agentData.displayY = agentData.y
    agentData.posQueue = []
    agentData.arc = null
  } else {
    agentData.displayX = existing.displayX ?? existing.x
    agentData.displayY = existing.displayY ?? existing.y
    agentData.posQueue = existing.posQueue ?? []
    agentData.arc = existing.arc ?? null

    if (existing.x !== agentData.x || existing.y !== agentData.y) {
      agentData.posQueue.push({ x: agentData.x, y: agentData.y, mustStop })
    }
  }

  agents.set(agentData.id, agentData)
  return agentData
}

export const upsertFood = (foodData) => {
  food.set(foodData.id, foodData)
}

export const upsertRiver = (riverData) => {
  rivers.set(riverData.river_id, {
    id: riverData.river_id,
    tiles: riverData.tiles.slice(),
    complete: riverData.complete
  })
}

export const addRiverTile = (riverId, tileX, tileY) => {
  const existing = rivers.get(riverId)
  const river = existing ?? { id: riverId, tiles: [], complete: false }
  if (!existing) rivers.set(riverId, river)
  river.tiles.push([tileX, tileY])
}
