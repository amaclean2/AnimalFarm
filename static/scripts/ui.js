import { MAX_HEALTH, UUID_PATTERN, API_BASE } from './constants.js'
import { agents, food, groups, setClockState, getClockState } from './state.js'

const agentCountEl = document.getElementById('agent-count')
const foodCountEl = document.getElementById('food-count')
const groupCountEl = document.getElementById('group-count')
const statusEl = document.getElementById('status')
const modalOverlay = document.getElementById('modal-overlay')
const modalBody = document.getElementById('modal-body')
const agentPanel = document.getElementById('agent-panel')
const agentPanelBody = document.getElementById('agent-panel-body')

export const btnStart = document.getElementById('btn-start')
export const btnPause = document.getElementById('btn-pause')
export const btnStop = document.getElementById('btn-stop')
export const btnStats = document.getElementById('btn-stats')

const formatValue = (value) =>
  value == null ? '—' : Array.isArray(value) ? `[${value}]` : String(value)

const abbreviateId = (value) => {
  if (value == null) return '—'
  const str = String(value)
  return str.length === 36 ? str.slice(0, 8) : str
}

export const abbreviateField = (value) => {
  if (value == null) return '—'
  if (Array.isArray(value)) {
    return value
      .map((item) => (UUID_PATTERN.test(String(item)) ? String(item).slice(0, 8) : item))
      .join(', ')
  }
  return UUID_PATTERN.test(String(value)) ? String(value).slice(0, 8) : value
}

export const updateAgentPanel = (agent) => {
  if (!agentPanel) return
  if (!agent) {
    agentPanel.classList.add('hidden')
    return
  }

  agentPanel.classList.remove('hidden')

  const rows = [
    ['id', abbreviateId(agent.id)],
    ['x / y', `${agent.x}, ${agent.y}`],
    ['health', `${agent.health} / ${MAX_HEALTH}`],
    ['age', agent.age],
    ['vision range', agent.vision_range],
    ['group id', abbreviateId(agent.group_id)],
    ['carrying food', agent.carrying_food ? 'yes' : 'no'],
    ['direction', formatValue(agent.direction)],
    ['last food seen', formatValue(agent.last_food_seen)]
  ]

  agentPanelBody.innerHTML = rows
    .map(([label, value]) =>
      `<div class="agent-row"><span>${label}</span><span class="val">${value}</span></div>`
    )
    .join('')
}

export const syncCounters = () => {
  agentCountEl.textContent = agents.size
  foodCountEl.textContent = food.size
  groupCountEl.textContent = groups.size
}

export const applyClockState = (state) => {
  setClockState(state)
  btnStart.disabled = state !== 'stopped'
  btnPause.disabled = state === 'stopped'
  btnStop.disabled = state === 'stopped'
  btnPause.textContent = state === 'paused' ? '▶ Resume' : '⏸ Pause'
  statusEl.textContent = { stopped: 'Stopped', running: 'Running', paused: 'Paused' }[state] ?? state
}

let pausedForStats = false

export const openStats = async () => {
  if (getClockState() === 'running') {
    await fetch(`${API_BASE}/clock/pause`, { method: 'POST' })
    applyClockState('paused')
    pausedForStats = true
  }

  const data = await fetch(`${API_BASE}/stats`).then((response) => response.json())

  const scalarEntries = Object.entries(data).filter(([, value]) => typeof value !== 'object')
  const arrayEntries = Object.entries(data).filter(([, value]) => Array.isArray(value))

  let html = ''

  if (scalarEntries.length) {
    html += `<div class="stats-summary">`
    html += scalarEntries
      .map(([key, value]) => `
        <div class="stats-summary-item">
          <div class="label">${key.replace(/_/g, ' ')}</div>
          <div class="value">${value}</div>
        </div>`)
      .join('')
    html += `</div>`
  }

  html += arrayEntries
    .map(([key, rows]) => {
      if (!rows.length) {
        return `<div class="stats-section"><h4>${key.replace(/_/g, ' ')}</h4><span class="stats-empty">None</span></div>`
      }

      const rawColumns = Object.keys(rows[0]).filter((col) => col !== 'x' && col !== 'y')
      const columns = [
        ...rawColumns.filter((col) => col === 'id'),
        ...rawColumns.filter((col) => col === 'age'),
        ...rawColumns.filter((col) => col !== 'id' && col !== 'age')
      ]
      const maxAge = columns.includes('age') ? Math.max(...rows.map((row) => row.age ?? 0)) : 0

      const headerRow = columns.map((col) => `<th>${col.replace(/_/g, ' ')}</th>`).join('')
      const dataRows = rows
        .map((row) => {
          const cells = columns
            .map((col) => {
              if (col === 'age') {
                const percentage = maxAge > 0 ? ((row.age ?? 0) / maxAge) * 100 : 0
                return `<td><div class="age-bar"><div style="width:${percentage.toFixed(1)}%"></div></div></td>`
              }
              return `<td>${abbreviateField(row[col])}</td>`
            })
            .join('')
          return `<tr>${cells}</tr>`
        })
        .join('')

      return `
        <div class="stats-section">
          <h4>${key.replace(/_/g, ' ')}</h4>
          <table class="stats-table">
            <thead><tr>${headerRow}</tr></thead>
            <tbody>${dataRows}</tbody>
          </table>
        </div>`
    })
    .join('')

  modalBody.innerHTML = html
  modalOverlay.classList.add('open')
}

export const closeStats = () => {
  modalOverlay.classList.remove('open')
  if (pausedForStats) {
    fetch(`${API_BASE}/clock/resume`, { method: 'POST' })
    applyClockState('running')
    pausedForStats = false
  }
}

document.getElementById('modal-close').addEventListener('click', closeStats)
modalOverlay.addEventListener('click', (event) => {
  if (event.target === modalOverlay) closeStats()
})
