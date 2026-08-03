const POPULATION_COLOR = "#2aa7c4"
const DEATH_AGE_COLOR = "#e08a3c"
const DEATH_HARVEST_COLOR = "#8e6fd1"

const CHART_WIDTH = 600
const CHART_HEIGHT = 140
const CHART_PAD = 10

const buildPopulationSeries = (agents, tickCount) => {
  if (!agents.length) return []

  const events = agents.flatMap((agent) =>
    agent.alive
      ? [[Math.max(0, agent.birth_tick), 1]]
      : [
          [Math.max(0, agent.birth_tick), 1],
          [agent.birth_tick + agent.age, -1],
        ],
  )
  events.sort(([tickA], [tickB]) => tickA - tickB)

  const series = []
  let population = 0
  for (const [tick, delta] of events) {
    population += delta
    series.push([tick, population])
  }

  const lastTick = series[series.length - 1][0]
  if (lastTick < tickCount) series.push([tickCount, population])

  return series
}

const buildDeathAgeSeries = (agents) =>
  agents
    .filter((agent) => !agent.alive)
    .map((agent) => [agent.birth_tick + agent.age, agent.age])
    .sort(([tickA], [tickB]) => tickA - tickB)

const buildDeathHarvestSeries = (agents) =>
  agents
    .filter((agent) => !agent.alive)
    .map((agent) => [agent.birth_tick + agent.age, agent.fruits_harvested])
    .sort(([tickA], [tickB]) => tickA - tickB)

const buildScales = (series, tickCount) => {
  const minTick = series[0][0]
  const maxTick = Math.max(tickCount, series[series.length - 1][0])
  const maxValue = Math.max(1, ...series.map(([, value]) => value))

  const xOf = (tick) =>
    CHART_PAD +
    ((tick - minTick) / Math.max(1, maxTick - minTick)) *
      (CHART_WIDTH - CHART_PAD * 2)
  const yOf = (value) =>
    CHART_HEIGHT -
    CHART_PAD -
    (value / maxValue) * (CHART_HEIGHT - CHART_PAD * 2)

  return { minTick, maxTick, maxValue, xOf, yOf }
}

const renderChartView = (view, series, tickCount, color, connect, isActive) => {
  const viewClass = isActive ? "chart-view active-view" : "chart-view"

  if (!series.length) {
    return `<div class="${viewClass}" data-view="${view}"><span class="stats-empty">None yet</span></div>`
  }

  const { minTick, maxTick, maxValue, xOf, yOf } = buildScales(
    series,
    tickCount,
  )

  const linePoints = connect
    ? series
        .map(
          ([tick, value]) => `${xOf(tick).toFixed(1)},${yOf(value).toFixed(1)}`,
        )
        .join(" ")
    : ""

  const markerStride = Math.max(1, Math.floor(series.length / 40))
  const markers = series
    .filter(
      (_, index) => index % markerStride === 0 || index === series.length - 1,
    )
    .map(([tick, value]) => {
      const x = xOf(tick).toFixed(1)
      const y = yOf(value).toFixed(1)
      return `<circle cx="${x}" cy="${y}" r="2.5" fill="${color}" />`
    })
    .join("")

  return `
    <div class="${viewClass}" data-view="${view}">
      <div class="population-chart-row">
        <div class="population-axis-label population-axis-max">${maxValue}</div>
        <div class="population-chart-wrap">
          <svg class="population-chart" viewBox="0 0 ${CHART_WIDTH} ${CHART_HEIGHT}" preserveAspectRatio="none">
            <line class="population-baseline" x1="${CHART_PAD}" y1="${CHART_HEIGHT - CHART_PAD}" x2="${CHART_WIDTH - CHART_PAD}" y2="${CHART_HEIGHT - CHART_PAD}" />
            ${connect ? `<polyline points="${linePoints}" fill="none" stroke="${color}" stroke-width="2" />` : ""}
            ${markers}
            <line class="population-crosshair" x1="0" y1="${CHART_PAD}" x2="0" y2="${CHART_HEIGHT - CHART_PAD}" />
            <circle class="population-hover-dot" r="3.5" fill="${color}" />
          </svg>
          <div class="population-tooltip"></div>
        </div>
        <div class="population-axis-label population-axis-min">0</div>
      </div>
      <div class="population-tick-row">
        <span>tick ${minTick}</span>
        <span>tick ${maxTick}</span>
      </div>
    </div>`
}

export const renderPopulationChart = (agents, tickCount) => {
  const populationSeries = buildPopulationSeries(agents, tickCount)
  if (populationSeries.length < 2) return ""

  const deathAgeSeries = buildDeathAgeSeries(agents)
  const deathHarvestSeries = buildDeathHarvestSeries(agents)

  return `
    <div class="stats-section population-section">
      <div class="population-section-header">
        <h4>Population</h4>
        <div class="chart-toggle">
          <button type="button" class="chart-toggle-btn active" data-view="population">population</button>
          <button type="button" class="chart-toggle-btn" data-view="death-age">death age</button>
          <button type="button" class="chart-toggle-btn" data-view="death-harvest">harvested</button>
        </div>
      </div>
      <div class="chart-view-stack">
        ${renderChartView("population", populationSeries, tickCount, POPULATION_COLOR, true, true)}
        ${renderChartView("death-age", deathAgeSeries, tickCount, DEATH_AGE_COLOR, false, false)}
        ${renderChartView("death-harvest", deathHarvestSeries, tickCount, DEATH_HARVEST_COLOR, false, false)}
      </div>
    </div>`
}

const initChartViewInteraction = (view, series, tickCount) => {
  const wrap = view.querySelector(".population-chart-wrap")
  if (!wrap || series.length < 1) return

  const { minTick, maxTick, xOf, yOf } = buildScales(series, tickCount)
  const svg = wrap.querySelector(".population-chart")
  const crosshair = wrap.querySelector(".population-crosshair")
  const hoverDot = wrap.querySelector(".population-hover-dot")
  const tooltip = wrap.querySelector(".population-tooltip")

  const nearestPoint = (tick) =>
    series.reduce((closest, point) =>
      Math.abs(point[0] - tick) < Math.abs(closest[0] - tick) ? point : closest,
    )

  const showAt = (clientX) => {
    const rect = svg.getBoundingClientRect()
    const svgX = ((clientX - rect.left) / rect.width) * CHART_WIDTH
    const tickAtCursor = minTick + (svgX / CHART_WIDTH) * (maxTick - minTick)
    const [tick, value] = nearestPoint(tickAtCursor)
    const x = xOf(tick)
    const y = yOf(value)

    crosshair.setAttribute("x1", x)
    crosshair.setAttribute("x2", x)
    hoverDot.setAttribute("cx", x)
    hoverDot.setAttribute("cy", y)

    tooltip.textContent = value
    tooltip.style.left = `${(x / CHART_WIDTH) * 100}%`
    tooltip.style.top = `${(y / CHART_HEIGHT) * 100}%`

    wrap.classList.add("hovering")
  }

  svg.addEventListener("mousemove", (event) => showAt(event.clientX))
  svg.addEventListener("mouseleave", () => wrap.classList.remove("hovering"))
}

export const initPopulationChartInteraction = (
  container,
  agents,
  tickCount,
) => {
  const section = container.querySelector(".population-section")
  if (!section) return

  const seriesByView = {
    population: buildPopulationSeries(agents, tickCount),
    "death-age": buildDeathAgeSeries(agents),
    "death-harvest": buildDeathHarvestSeries(agents),
  }

  section.querySelectorAll(".chart-view").forEach((view) => {
    initChartViewInteraction(view, seriesByView[view.dataset.view], tickCount)
  })

  const toggleButtons = section.querySelectorAll(".chart-toggle-btn")
  const views = section.querySelectorAll(".chart-view")

  toggleButtons.forEach((button) => {
    button.addEventListener("click", () => {
      toggleButtons.forEach((btn) =>
        btn.classList.toggle("active", btn === button),
      )
      views.forEach((view) =>
        view.classList.toggle(
          "active-view",
          view.dataset.view === button.dataset.view,
        ),
      )
    })
  })
}
