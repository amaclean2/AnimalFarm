const listEl = document.getElementById('test-list')
const summaryEl = document.getElementById('summary')
const btnRunAll = document.getElementById('btn-run-all')

let tests = []
let running = false

const ICONS = {
  pending: '<span class="test-status status-pending">○</span>',
  running: '<span class="test-status status-running">◉</span>',
  pass:    '<span class="test-status status-pass">✓</span>',
  fail:    '<span class="test-status status-fail">✗</span>',
}

function rowId(index) {
  return `test-row-${index}`
}

function renderRow(test, state = 'pending', result = null) {
  const ticks = result?.ticks != null
    ? `tick ${result.ticks} / ${test.max_ticks}`
    : `max ${test.max_ticks} ticks`
  const tickClass = result?.ticks != null ? 'has-ticks' : ''
  const failure = result && !result.passed && result.failure_message
    ? `<div class="test-failure">✗ ${result.failure_message}</div>`
    : ''
  const stateClass = state === 'running' ? 'running' : state === 'pass' ? 'passed' : state === 'fail' ? 'failed' : ''

  return `
    <div id="${rowId(test.index)}" class="test-row ${stateClass}">
      ${ICONS[state]}
      <span class="test-name">${test.name}</span>
      <div class="test-meta">
        <span class="test-ticks ${tickClass}">${ticks}</span>
        <button class="btn-run-one" data-index="${test.index}" ${running ? 'disabled' : ''}>Run</button>
      </div>
      ${test.description ? `<div class="test-desc">${test.description}</div>` : ''}
      ${failure}
    </div>`
}

function updateSummary(results) {
  if (!results) {
    summaryEl.textContent = `${tests.length} tests`
    summaryEl.className = ''
    return
  }
  const passed = results.filter(r => r.passed).length
  const failed = results.length - passed
  summaryEl.className = 'has-results'
  summaryEl.innerHTML = `
    <span class="pass">${passed} passed</span>
    ${failed > 0 ? ` · <span class="fail">${failed} failed</span>` : ''}
    · ${results.length} total
  `
}

function renderAll(states = {}, results = {}) {
  listEl.innerHTML = tests.map(t => {
    const state = states[t.index] ?? 'pending'
    return renderRow(t, state, results[t.index] ?? null)
  }).join('')

  listEl.querySelectorAll('.btn-run-one').forEach(btn => {
    btn.addEventListener('click', () => runOne(Number(btn.dataset.index)))
  })
}

function setRunning(isRunning) {
  running = isRunning
  btnRunAll.disabled = isRunning
}

async function runAll() {
  if (running) return
  setRunning(true)

  const states = Object.fromEntries(tests.map(t => [t.index, 'pending']))
  const results = {}

  for (const t of tests) {
    states[t.index] = 'running'
    renderAll(states, results)

    try {
      const res = await fetch(`/tests/run/${t.index}`, { method: 'POST' })
      const data = await res.json()
      results[t.index] = data
      states[t.index] = data.passed ? 'pass' : 'fail'
    } catch {
      states[t.index] = 'fail'
    }
    renderAll(states, results)
  }

  updateSummary(Object.values(results))
  setRunning(false)
}

async function runOne(index) {
  if (running) return
  setRunning(true)

  const states = Object.fromEntries(tests.map(t => [t.index, 'pending']))
  const results = {}
  states[index] = 'running'
  renderAll(states, results)

  try {
    const res = await fetch(`/tests/run/${index}`, { method: 'POST' })
    const data = await res.json()
    results[index] = data
    states[index] = data.passed ? 'pass' : 'fail'
  } catch {
    states[index] = 'fail'
  }

  renderAll(states, results)
  updateSummary(null)
  setRunning(false)
}

async function init() {
  const res = await fetch('/tests')
  const data = await res.json()
  if (data.error) {
    listEl.innerHTML = `<div style="color:#c62828;padding:16px;font-size:13px;">${data.error}</div>`
    return
  }
  tests = data.tests
  updateSummary(null)
  renderAll()
}

btnRunAll.addEventListener('click', runAll)
init()
