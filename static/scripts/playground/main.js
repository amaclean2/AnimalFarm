import { connect, post, fetchScenarios } from './connection.js'
import { startRenderLoop, resize } from './renderer.js'
import { isAutoRunning } from './state.js'
import { renderScenarios } from './ui.js'


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
