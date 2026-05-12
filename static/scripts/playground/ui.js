import { MAX_HEALTH } from './constants.js'
import { agents, getTick, isAutoRunning, getActiveScenario } from './state.js'

const tickEl = document.getElementById('pg-tick')
const statusEl = document.getElementById('pg-status')
const agentInfoEl = document.getElementById('pg-agent-info')
const btnAuto = document.getElementById('btn-auto')
const scenariosEl = document.getElementById('pg-scenarios')
const scenarioStatusEl = document.getElementById('pg-scenario-status')

export const setStatus = (text) => {
  if (statusEl) statusEl.textContent = text
}

export const setTickDisplay = (tick) => {
  if (tickEl) tickEl.textContent = tick
}

export const setAutoButton = (running) => {
  if (!btnAuto) return
  btnAuto.textContent = running ? '⏸ Pause Auto' : '▶ Auto Run'
  btnAuto.classList.toggle('active', running)
}

export const setScenarioStatus = (result, tick) => {
  if (!scenarioStatusEl) return
  if (result === null) {
    scenarioStatusEl.textContent = ''
    scenarioStatusEl.className = ''
    return
  }
  const success = result === 'success'
  scenarioStatusEl.textContent = success
    ? `✓ Complete — tick ${tick}`
    : `✗ Agent died — tick ${tick}`
  scenarioStatusEl.className = success ? 'pg-scenario-pass' : 'pg-scenario-fail'
}

export const renderScenarios = (scenarios, error, onRun) => {
  if (!scenariosEl) return
  if (error) {
    scenariosEl.innerHTML = `<div class="pg-scenario-error">${error}</div>`
    return
  }
  const active = getActiveScenario()
  scenariosEl.innerHTML = scenarios
    .map(({ index, name, description }) => `
      <button class="pg-scenario-btn${index === active ? ' active' : ''}" data-index="${index}" title="${description}">
        <span class="pg-scenario-name">${name}</span>
        ${description ? `<span class="pg-scenario-desc">${description}</span>` : ''}
      </button>`)
    .join('')
  scenariosEl.querySelectorAll('.pg-scenario-btn').forEach((btn) => {
    btn.addEventListener('click', () => onRun(Number(btn.dataset.index)))
  })
}

export const refreshActiveScenario = () => {
  if (!scenariosEl) return
  const active = getActiveScenario()
  scenariosEl.querySelectorAll('.pg-scenario-btn').forEach((btn) => {
    btn.classList.toggle('active', Number(btn.dataset.index) === active)
  })
}

export const updateAgentPanel = () => {
  if (!agentInfoEl) return
  const agent = [...agents.values()][0]
  if (!agent) {
    agentInfoEl.innerHTML = '<div class="pg-row"><span>no agent</span></div>'
    return
  }

  const rows = [
    ['health', `${agent.health} / ${MAX_HEALTH}`],
    ['pos', `${agent.x}, ${agent.y}`],
    ['age', agent.age],
    ['alive', agent.alive ? 'yes' : 'dead'],
    ['direction', agent.direction ? `[${agent.direction}]` : '—'],
    ['last food seen', agent.last_food_seen ? `[${agent.last_food_seen}]` : '—'],
    ['vision', agent.vision_range],
  ]

  const deadBanner = !agent.alive
    ? '<div class="pg-dead-banner">DEAD — click Reset</div>'
    : ''

  agentInfoEl.innerHTML = deadBanner + rows
    .map(([k, v]) => `<div class="pg-row"><span>${k}</span><span class="pg-val">${v}</span></div>`)
    .join('')
}
