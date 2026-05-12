import { connect, post, postJson, fetchScenarios } from './connection.js'
import { startRenderLoop, cellSize, resize } from './renderer.js'
import { isAutoRunning } from './state.js'
import { renderScenarios } from './ui.js'
import { PG_WIDTH, PG_HEIGHT } from './constants.js'

const canvas = document.getElementById('pg-canvas')

canvas.addEventListener('click', async (e) => {
  const rect = canvas.getBoundingClientRect()
  const cs = cellSize()
  const scaleX = canvas.width / rect.width
  const scaleY = canvas.height / rect.height
  const x = Math.floor((e.clientX - rect.left) * scaleX / cs)
  const y = Math.floor((e.clientY - rect.top) * scaleY / cs)
  if (x >= 0 && x < PG_WIDTH && y >= 0 && y < PG_HEIGHT) {
    await postJson('/food/toggle', { x, y })
  }
})

document.getElementById('btn-reset').addEventListener('click', () => post('/reset'))
document.getElementById('btn-step').addEventListener('click', () => post('/step'))

document.getElementById('btn-auto').addEventListener('click', () => {
  if (isAutoRunning()) {
    post('/auto/stop')
  } else {
    const interval = parseFloat(document.getElementById('auto-interval').value ?? '0.5')
    post(`/auto/start?interval=${interval}`)
  }
})

document.getElementById('btn-scatter').addEventListener('click', () => post('/food/scatter?count=5'))
document.getElementById('btn-fill').addEventListener('click', () => post('/food/scatter?count=30'))
document.getElementById('btn-clear-food').addEventListener('click', () => post('/food/clear'))
document.getElementById('btn-heal').addEventListener('click', () => post('/agent/heal'))
document.getElementById('btn-damage').addEventListener('click', () => post('/agent/damage?amount=20'))

const loadScenarios = async () => {
  const { scenarios, error } = await fetchScenarios()
  renderScenarios(scenarios, error, (index) => post(`/scenarios/run?index=${index}`))
}

document.getElementById('btn-refresh-scenarios').addEventListener('click', loadScenarios)

window.addEventListener('resize', resize)
resize()
connect()
loadScenarios()
startRenderLoop()
