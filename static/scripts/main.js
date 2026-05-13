import { agents, getSelectedAgentId, setSelectedAgentId } from './state.js'
import { camera, viewport, resize, clampCamera } from './camera.js'
import { updateAgentPanel, applyClockState, openStats, btnStart, btnPause, btnStop, btnStats } from './ui.js'
import { connect, post } from './connection.js'
import { startRenderLoop } from './renderer.js'
import { getClockState } from './state.js'

const canvas = document.getElementById('game')

const findAgentAtWorldPos = (worldX, worldY) =>
  [...agents.values()].find((agent) => agent.x === worldX && agent.y === worldY)

const handleCanvasSelect = (screenX, screenY) => {
  const rect = canvas.getBoundingClientRect()
  const worldX = Math.floor((screenX - rect.left + camera.x) / viewport.cellSize)
  const worldY = Math.floor((screenY - rect.top + camera.y) / viewport.cellSize)
  const hitAgent = findAgentAtWorldPos(worldX, worldY)
  const hitId = hitAgent?.id ?? null
  const nextSelection = getSelectedAgentId() === hitId ? null : hitId
  setSelectedAgentId(nextSelection)
  updateAgentPanel(nextSelection ? agents.get(nextSelection) : null)
}

console.log('shy agents')

canvas.addEventListener('click', (event) => {
  handleCanvasSelect(event.clientX, event.clientY)
})

let touchLastX = 0
let touchLastY = 0
let touchMoved = false

canvas.addEventListener('touchstart', (event) => {
  if (event.touches.length !== 1) return
  touchLastX = event.touches[0].clientX
  touchLastY = event.touches[0].clientY
  touchMoved = false
}, { passive: true })

canvas.addEventListener('touchmove', (event) => {
  if (event.touches.length !== 1) return
  camera.x -= event.touches[0].clientX - touchLastX
  camera.y -= event.touches[0].clientY - touchLastY
  clampCamera()
  touchLastX = event.touches[0].clientX
  touchLastY = event.touches[0].clientY
  touchMoved = true
}, { passive: true })

canvas.addEventListener('touchend', (event) => {
  if (touchMoved || event.changedTouches.length !== 1) return
  const touch = event.changedTouches[0]
  handleCanvasSelect(touch.clientX, touch.clientY)
})

btnStart.addEventListener('click', () => post('/start'))

btnPause.addEventListener('click', () => {
  const clockState = getClockState()
  if (clockState === 'running') {
    post('/clock/pause')
    applyClockState('paused')
  } else if (clockState === 'paused') {
    post('/clock/resume')
    applyClockState('running')
  }
})

btnStop.addEventListener('click', () => {
  post('/clock/stop')
  applyClockState('stopped')
})

btnStats.addEventListener('click', openStats)

document.getElementById('hint').textContent = window.matchMedia('(pointer: coarse)').matches
  ? 'Drag to scroll'
  : 'WASD / ↑↓←→ to scroll'

window.addEventListener('resize', resize)
requestAnimationFrame(resize)

connect()
startRenderLoop()
