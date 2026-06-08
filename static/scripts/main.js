import {
  agents,
  plants,
  getSelectedAgentId,
  setSelectedAgentId,
  getSelectedTile,
  setSelectedTile,
  isRiverTile
} from './state.js'
import {
  camera,
  viewport,
  resize,
  clampCamera,
  centerOnWorld
} from './camera.js'
import {
  updateAgentPanel,
  updateTilePanel,
  clearTilePanel,
  applyClockState,
  openStats,
  openConfigDialog,
  closeConfigDialog,
  readConfigValues,
  btnStart,
  btnPause,
  btnStop,
  btnStats
} from './ui.js'
import { connect, post } from './connection.js'
import { startRenderLoop } from './renderer.js'
import { getClockState, setTickMs } from './state.js'

const canvas = document.getElementById('game')

console.log('hi')

const findAgentAtWorldPos = (worldX, worldY) =>
  [...agents.values()].find((agent) => agent.x === worldX && agent.y === worldY)

const findPlantAtWorldPos = (worldX, worldY) =>
  [...plants.values()].find((p) => p.x === worldX && p.y === worldY)

const handleCanvasSelect = (screenX, screenY) => {
  const rect = canvas.getBoundingClientRect()
  const worldX = Math.floor(
    (screenX - rect.left + camera.x) / viewport.cellSize
  )
  const worldY = Math.floor((screenY - rect.top + camera.y) / viewport.cellSize)
  const hitAgent = findAgentAtWorldPos(worldX, worldY)
  const hitId = hitAgent?.id ?? null
  const nextSelection = getSelectedAgentId() === hitId ? null : hitId

  setSelectedAgentId(nextSelection)
  updateAgentPanel(nextSelection ? agents.get(nextSelection) : null)

  if (nextSelection) {
    setSelectedTile(null)
    clearTilePanel()
  } else {
    const prevTile = getSelectedTile()
    const sameEmpty = prevTile && prevTile.x === worldX && prevTile.y === worldY
    if (sameEmpty) {
      setSelectedTile(null)
      clearTilePanel()
    } else {
      setSelectedAgentId(null)
      updateAgentPanel(null)
      setSelectedTile({ x: worldX, y: worldY })
      updateTilePanel(
        worldX,
        worldY,
        findPlantAtWorldPos(worldX, worldY),
        isRiverTile(worldX, worldY)
      )
    }
  }
}

canvas.addEventListener('click', (event) => {
  handleCanvasSelect(event.clientX, event.clientY)
})

let touchLastX = 0
let touchLastY = 0
let touchMoved = false

canvas.addEventListener(
  'touchstart',
  (event) => {
    if (event.touches.length !== 1) return
    touchLastX = event.touches[0].clientX
    touchLastY = event.touches[0].clientY
    touchMoved = false
  },
  { passive: true }
)

canvas.addEventListener(
  'touchmove',
  (event) => {
    if (event.touches.length !== 1) return
    camera.x -= event.touches[0].clientX - touchLastX
    camera.y -= event.touches[0].clientY - touchLastY
    clampCamera()
    touchLastX = event.touches[0].clientX
    touchLastY = event.touches[0].clientY
    touchMoved = true
  },
  { passive: true }
)

canvas.addEventListener('touchend', (event) => {
  if (touchMoved || event.changedTouches.length !== 1) return
  const touch = event.changedTouches[0]
  handleCanvasSelect(touch.clientX, touch.clientY)
})

btnStart.addEventListener('click', openConfigDialog)

document.getElementById('config-start-btn').addEventListener('click', () => {
  closeConfigDialog()
  post('/start', readConfigValues())
})

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

const btnNextAgent = document.getElementById('btn-next-agent')
let agentCursor = 0

const jumpToNextAgent = () => {
  const living = [...agents.values()]
  if (!living.length) return
  agentCursor = agentCursor % living.length
  const agent = living[agentCursor]
  agentCursor = (agentCursor + 1) % living.length
  setSelectedAgentId(agent.id)
  updateAgentPanel(agent)
  centerOnWorld(agent.x, agent.y)
}

btnNextAgent.addEventListener('click', jumpToNextAgent)

const speedSlider = document.getElementById('speed-slider')
const speedVal = document.getElementById('speed-val')

const sliderToInterval = (s) =>
  parseFloat((2.0 * Math.pow(0.025, (s - 1) / 9)).toFixed(3))

const formatInterval = (interval) =>
  interval < 1 ? `${Math.round(interval * 1000)}ms` : `${interval.toFixed(1)}s`

speedVal.textContent = formatInterval(
  sliderToInterval(parseInt(speedSlider.value, 10))
)

speedSlider.addEventListener('input', () => {
  const interval = sliderToInterval(parseInt(speedSlider.value, 10))
  speedVal.textContent = formatInterval(interval)
  setTickMs(interval * 1000)
  post('/clock/speed', { interval })
})

document.getElementById('hint').textContent = window.matchMedia(
  '(pointer: coarse)'
).matches
  ? 'Drag to scroll · Pinch to zoom'
  : 'WASD / ↑↓←→ to scroll · C: climate overlay'

window.addEventListener('resize', resize)
requestAnimationFrame(resize)

connect()
startRenderLoop()
