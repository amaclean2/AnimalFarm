import { WORLD_WIDTH, WORLD_HEIGHT, MAX_HEALTH, MAX_REST, MUTATION_COLORS, MUTATION_PRIORITY, NO_MUTATION_COLOR } from './constants.js'
import { agents, deadAgents, food, rivers, groups, homes, getClockState, getSelectedAgentId, getTickMs, getDayPhase } from './state.js'
import { camera, viewport, scrollCamera } from './camera.js'

const canvas = document.getElementById('game')
const ctx = canvas.getContext('2d')

const agentColor = (agent) => {
  const expressed = agent.mutations ?? []
  const match = MUTATION_PRIORITY.find(m => expressed.includes(m))
  return match ? MUTATION_COLORS[match] : NO_MUTATION_COLOR
}

const healthColor = (health) => {
  const ratio = health / MAX_HEALTH
  if (ratio > 0.5) return '#2ecc71'
  if (ratio > 0.25) return '#f39c12'
  return '#e74c3c'
}

const isVisible = (screenX, screenY) =>
  screenX > -viewport.cellSize &&
  screenX < canvas.width &&
  screenY > -viewport.cellSize &&
  screenY < canvas.height

const drawRivers = () => {
  ctx.fillStyle = 'rgba(41, 128, 185, 0.55)'
  for (const river of rivers.values()) {
    for (const [tileX, tileY] of river.tiles) {
      const screenX = tileX * viewport.cellSize - camera.x
      const screenY = tileY * viewport.cellSize - camera.y
      if (!isVisible(screenX, screenY)) continue
      ctx.fillRect(screenX, screenY, viewport.cellSize, viewport.cellSize)
    }
  }
}

const drawGrid = () => {
  ctx.strokeStyle = '#1a1a1a'
  ctx.lineWidth = 1
  ctx.beginPath()

  const colStart = Math.floor(camera.x / viewport.cellSize)
  const colEnd = Math.min(Math.ceil((camera.x + canvas.width) / viewport.cellSize), WORLD_WIDTH)
  const rowStart = Math.floor(camera.y / viewport.cellSize)
  const rowEnd = Math.min(Math.ceil((camera.y + canvas.height) / viewport.cellSize), WORLD_HEIGHT)

  for (let col = colStart; col <= colEnd; col++) {
    const x = col * viewport.cellSize - camera.x
    ctx.moveTo(x, 0)
    ctx.lineTo(x, canvas.height)
  }
  for (let row = rowStart; row <= rowEnd; row++) {
    const y = row * viewport.cellSize - camera.y
    ctx.moveTo(0, y)
    ctx.lineTo(canvas.width, y)
  }

  ctx.stroke()
}

const drawVision = (agent, visionRadius) => {
  const centerX = agent.x * viewport.cellSize + viewport.cellSize / 2 - camera.x
  const centerY = agent.y * viewport.cellSize + viewport.cellSize / 2 - camera.y
  const pixelRadius = visionRadius * viewport.cellSize

  ctx.beginPath()
  ctx.moveTo(centerX, centerY - pixelRadius)
  ctx.lineTo(centerX + pixelRadius, centerY)
  ctx.lineTo(centerX, centerY + pixelRadius)
  ctx.lineTo(centerX - pixelRadius, centerY)
  ctx.closePath()
  ctx.fillStyle = 'rgba(255,255,255,0.05)'
  ctx.fill()
  ctx.strokeStyle = 'rgba(255,255,255,0.35)'
  ctx.lineWidth = 1
  ctx.setLineDash([6, 4])
  ctx.stroke()
  ctx.setLineDash([])
}

const drawHomes = () => {
  for (const home of homes.values()) {
    const screenX = home.x * viewport.cellSize - camera.x
    const screenY = home.y * viewport.cellSize - camera.y
    if (!isVisible(screenX, screenY)) continue

    const s = viewport.cellSize
    const wallW = s * 0.55
    const wallH = s * 0.35
    const wallX = screenX + (s - wallW) / 2
    const wallY = screenY + s * 0.52

    // roof
    ctx.beginPath()
    ctx.moveTo(screenX + s * 0.5, screenY + s * 0.2)
    ctx.lineTo(screenX + s * 0.15, screenY + s * 0.52)
    ctx.lineTo(screenX + s * 0.85, screenY + s * 0.52)
    ctx.closePath()
    ctx.fillStyle = 'rgba(180, 100, 40, 0.85)'
    ctx.fill()

    // walls
    ctx.fillStyle = 'rgba(220, 170, 100, 0.85)'
    ctx.fillRect(wallX, wallY, wallW, wallH)
  }
}

const drawFood = (visibleFoodIds) => {
  for (const foodItem of food.values()) {
    const screenX = foodItem.x * viewport.cellSize - camera.x
    const screenY = foodItem.y * viewport.cellSize - camera.y
    if (!isVisible(screenX, screenY)) continue

    const isHighlighted = visibleFoodIds.has(foodItem.id)
    ctx.fillStyle = isHighlighted ? '#f1c40f' : '#27ae60'
    ctx.beginPath()
    ctx.arc(
      screenX + viewport.cellSize / 2,
      screenY + viewport.cellSize / 2,
      isHighlighted ? viewport.cellSize * 0.17 : viewport.cellSize * 0.13,
      0,
      Math.PI * 2
    )
    ctx.fill()
  }
}

const advanceArc = (agent, now) => {
  if (agent.arc && (now - agent.arc.startTime) / agent.arc.duration >= 1) {
    agent.displayX = agent.arc.endX
    agent.displayY = agent.arc.endY
    agent.arc = null
  }

  if (agent.arc) return

  const tickMs = getTickMs()

  if (agent.posQueue.length >= 2 && !agent.posQueue[0].mustStop) {
    const point1 = agent.posQueue.shift()
    const point2 = agent.posQueue.shift()
    agent.arc = {
      startX: agent.displayX, startY: agent.displayY,
      midX: point1.x,         midY: point1.y,
      endX: point2.x,         endY: point2.y,
      startTime: now,
      duration: tickMs > 0 ? 2 * tickMs : 300,
      curved: true
    }
  } else if (agent.posQueue.length >= 1) {
    const point = agent.posQueue.shift()
    agent.arc = {
      startX: agent.displayX, startY: agent.displayY,
      endX: point.x,          endY: point.y,
      startTime: now,
      duration: tickMs > 0 ? tickMs : 150,
      curved: false
    }
  }
}

const agentRenderPosition = (agent, now) => {
  if (!agent.arc) return [agent.displayX, agent.displayY]

  const progress = Math.min((now - agent.arc.startTime) / agent.arc.duration, 1)

  if (agent.arc.curved) {
    const complement = 1 - progress
    return [
      complement * complement * agent.arc.startX + 2 * complement * progress * agent.arc.midX + progress * progress * agent.arc.endX,
      complement * complement * agent.arc.startY + 2 * complement * progress * agent.arc.midY + progress * progress * agent.arc.endY
    ]
  }

  return [
    agent.arc.startX + (agent.arc.endX - agent.arc.startX) * progress,
    agent.arc.startY + (agent.arc.endY - agent.arc.startY) * progress
  ]
}

const drawDeadAgents = () => {
  for (const agent of deadAgents.values()) {
    if (!agent) continue
    const screenX = agent.x * viewport.cellSize - camera.x
    const screenY = agent.y * viewport.cellSize - camera.y
    if (!isVisible(screenX, screenY)) continue

    ctx.beginPath()
    ctx.arc(screenX + viewport.cellSize / 2, screenY + viewport.cellSize / 2, viewport.cellSize * 0.3, 0, Math.PI * 2)
    ctx.fillStyle = '#444'
    ctx.fill()
    ctx.strokeStyle = 'rgba(255,255,255,0.05)'
    ctx.lineWidth = 1
    ctx.stroke()
  }
}

const drawLivingAgents = () => {
  const now = performance.now()
  const selectedId = getSelectedAgentId()

  for (const agent of agents.values()) {
    advanceArc(agent, now)
    const [renderX, renderY] = agentRenderPosition(agent, now)
    const screenX = renderX * viewport.cellSize - camera.x
    const screenY = renderY * viewport.cellSize - camera.y
    if (!isVisible(screenX, screenY)) continue

    const centerX = screenX + viewport.cellSize / 2
    const centerY = screenY + viewport.cellSize * 0.37

    if (agent.id === selectedId) {
      ctx.beginPath()
      ctx.arc(centerX, centerY, viewport.cellSize * 0.43, 0, Math.PI * 2)
      ctx.strokeStyle = 'rgba(255,255,255,0.8)'
      ctx.lineWidth = 2
      ctx.stroke()
    }

    ctx.beginPath()
    ctx.arc(centerX, centerY, viewport.cellSize * 0.3, 0, Math.PI * 2)
    ctx.fillStyle = agentColor(agent)
    ctx.fill()
    ctx.strokeStyle = 'rgba(255,255,255,0.15)'
    ctx.lineWidth = 1
    ctx.stroke()

    if (agent.carried_food) {
      const dotX = centerX + viewport.cellSize * 0.18
      const dotY = centerY - viewport.cellSize * 0.28
      const dotR = viewport.cellSize * 0.1
      ctx.beginPath()
      ctx.arc(dotX, dotY, dotR, 0, Math.PI * 2)
      ctx.fillStyle = '#27ae60'
      ctx.fill()
      ctx.strokeStyle = 'rgba(255,255,255,0.7)'
      ctx.lineWidth = 1
      ctx.stroke()
    }

    const barWidth = viewport.cellSize * 0.8
    const barX = screenX + viewport.cellSize * 0.1
    const barY = screenY + viewport.cellSize * 0.73

    ctx.fillStyle = '#222'
    ctx.fillRect(barX, barY, barWidth, 3)
    ctx.fillStyle = healthColor(agent.health)
    ctx.fillRect(barX, barY, Math.min(barWidth * (agent.health / MAX_HEALTH), barWidth), 3)

    ctx.fillStyle = '#222'
    ctx.fillRect(barX, barY + 5, barWidth, 3)
    ctx.fillStyle = '#5b8dd9'
    ctx.fillRect(barX, barY + 5, barWidth * Math.max(0, agent.rest / MAX_REST), 3)
  }
}

const nightOverlayAlpha = (phase) => {
  if (phase < 0.4) return 0
  if (phase < 0.5) return (phase - 0.4) / 0.1
  if (phase < 0.9) return 1
  return 1 - (phase - 0.9) / 0.1
}

const drawNightOverlay = () => {
  const alpha = nightOverlayAlpha(getDayPhase()) * 0.55
  if (alpha <= 0) return
  ctx.fillStyle = `rgba(10, 10, 50, ${alpha.toFixed(3)})`
  ctx.fillRect(0, 0, canvas.width, canvas.height)
}

const drawPrompt = () => {
  if (agents.size !== 0 || getClockState() !== 'stopped') return

  ctx.textAlign = 'center'
  ctx.textBaseline = 'middle'
  ctx.fillStyle = '#2a2a2a'
  ctx.font = '14px Roboto, sans-serif'
  ctx.fillText('Press "Start Game" to begin', canvas.width / 2, canvas.height / 2)
}

let lastFrameTime = 0

const frame = (now) => {
  const deltaTime = Math.min((now - lastFrameTime) / 1000, 0.1)
  lastFrameTime = now

  scrollCamera(deltaTime)

  ctx.fillStyle = '#111111'
  ctx.fillRect(0, 0, canvas.width, canvas.height)

  const selectedId = getSelectedAgentId()
  const selectedAgent = selectedId ? agents.get(selectedId) : null
  const visionRadius = selectedAgent
    ? selectedAgent.group_id
      ? Math.round(selectedAgent.vision_range * 1.5)
      : selectedAgent.vision_range
    : 0

  const visibleFoodIds = new Set()
  if (selectedAgent) {
    for (const foodItem of food.values()) {
      if (Math.abs(foodItem.x - selectedAgent.x) + Math.abs(foodItem.y - selectedAgent.y) <= visionRadius) {
        visibleFoodIds.add(foodItem.id)
      }
    }
  }

  drawGrid()
  drawRivers()
  drawHomes()
  if (selectedAgent) drawVision(selectedAgent, visionRadius)
  drawDeadAgents()
  drawFood(visibleFoodIds)
  drawLivingAgents()
  drawNightOverlay()
  drawPrompt()

  requestAnimationFrame(frame)
}

export const startRenderLoop = () => requestAnimationFrame(frame)
