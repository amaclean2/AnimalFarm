import { PG_WIDTH, PG_HEIGHT, MAX_HEALTH } from './constants.js'
import { agents, food } from './state.js'

const canvas = document.getElementById('pg-canvas')
const ctx = canvas.getContext('2d')

export const cellSize = () => canvas.width / PG_WIDTH

export const resize = () => {
  const wrap = canvas.parentElement
  const available = Math.min(wrap.clientWidth - 32, wrap.clientHeight - 32)
  const size = Math.max(Math.floor(available / PG_WIDTH) * PG_WIDTH, PG_WIDTH * 20)
  canvas.width = size
  canvas.height = size
}

const healthColor = (health) => {
  const ratio = health / MAX_HEALTH
  if (ratio > 0.5) return '#2ecc71'
  if (ratio > 0.25) return '#f39c12'
  return '#e74c3c'
}

const drawGrid = (cs) => {
  ctx.strokeStyle = '#2a2a2a'
  ctx.lineWidth = 1
  ctx.beginPath()
  for (let col = 0; col <= PG_WIDTH; col++) {
    ctx.moveTo(col * cs, 0)
    ctx.lineTo(col * cs, PG_HEIGHT * cs)
  }
  for (let row = 0; row <= PG_HEIGHT; row++) {
    ctx.moveTo(0, row * cs)
    ctx.lineTo(PG_WIDTH * cs, row * cs)
  }
  ctx.stroke()
}

const drawFood = (cs) => {
  ctx.fillStyle = '#27ae60'
  for (const f of food.values()) {
    ctx.beginPath()
    ctx.arc(f.x * cs + cs / 2, f.y * cs + cs / 2, cs * 0.18, 0, Math.PI * 2)
    ctx.fill()
  }
}

const drawAgents = (cs) => {
  for (const agent of agents.values()) {
    const cx = agent.x * cs + cs / 2
    const cy = agent.y * cs + cs * 0.42

    if (!agent.alive) {
      ctx.beginPath()
      ctx.arc(cx, cy, cs * 0.3, 0, Math.PI * 2)
      ctx.fillStyle = '#444'
      ctx.fill()
      ctx.fillStyle = '#666'
      ctx.font = `bold ${Math.round(cs * 0.25)}px monospace`
      ctx.textAlign = 'center'
      ctx.textBaseline = 'middle'
      ctx.fillText('✕', cx, cy)
      continue
    }

    ctx.beginPath()
    ctx.arc(cx, cy, cs * 0.3, 0, Math.PI * 2)
    ctx.fillStyle = '#3498db'
    ctx.fill()
    ctx.strokeStyle = 'rgba(255,255,255,0.2)'
    ctx.lineWidth = 1
    ctx.stroke()

    if (agent.carrying_food) {
      ctx.beginPath()
      ctx.arc(cx + cs * 0.2, cy - cs * 0.2, cs * 0.1, 0, Math.PI * 2)
      ctx.fillStyle = '#f1c40f'
      ctx.fill()
    }

    const barW = cs * 0.8
    const barX = agent.x * cs + cs * 0.1
    const barY = agent.y * cs + cs * 0.78
    ctx.fillStyle = '#222'
    ctx.fillRect(barX, barY, barW, 3)
    ctx.fillStyle = healthColor(agent.health)
    ctx.fillRect(barX, barY, barW * Math.max(0, agent.health / MAX_HEALTH), 3)
  }
}

export const render = () => {
  const cs = cellSize()
  ctx.fillStyle = '#111'
  ctx.fillRect(0, 0, canvas.width, canvas.height)
  drawGrid(cs)
  drawFood(cs)
  drawAgents(cs)
}

export const startRenderLoop = () => {
  const loop = () => { render(); requestAnimationFrame(loop) }
  requestAnimationFrame(loop)
}
