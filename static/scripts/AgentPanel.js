import { INVENTORY_CAPACITY } from "./constants.js"
import { abbreviateId, toCelsius } from "./utils.js"
import { getEffectiveTemperatureAt } from "./state.js"

const agentPanel = document.getElementById("agent-panel")
const agentPanelTitle = document.getElementById("agent-panel-title")
const agentPanelBody = document.getElementById("agent-panel-body")

const agentBar = (label, value, color, text) => {
  const pct = Math.min(100, Math.max(0, value * 100)).toFixed(1)
  const display = text ?? `${pct}%`
  return `
    <div class="agent-bar-row">
      <div class="agent-bar-label">${label}<span class="agent-bar-val">${display}</span></div>
      <div class="agent-bar-track"><div class="agent-bar-fill" style="width:${pct}%;background:${color}"></div></div>
    </div>`
}

export const updateAgentPanel = (agent) => {
  if (!agentPanel) return
  if (!agent) {
    agentPanel.classList.add("hidden")
    return
  }

  agentPanel.classList.remove("hidden")

  if (agentPanelTitle)
    agentPanelTitle.textContent = `Agent ${abbreviateId(agent.id)}`

  const genome = agent.behavioral_genome ?? {}
  const fmt = (value) => (value != null ? value.toFixed(3) : "—")

  const temperature = getEffectiveTemperatureAt(agent.x, agent.y)

  const rows = [
    ["age", agent.age],
    [
      "action",
      agent.active_task ? agent.active_task.name.replace(/_/g, " ") : "—",
    ],
    ["breakaway", fmt(genome.breakaway_threshold)],
    ["hunger drain", `${agent.needs.hunger_drain_rate.toFixed(4)}/tick`],
    ["harvested", agent.fruits_harvested],
    ["tile temp", `${toCelsius(temperature).toFixed(1)} °C`],
  ]

  const infoHtml = rows
    .map(
      ([label, value]) =>
        `<div class="agent-row"><span>${label}</span><span class="val">${value}</span></div>`,
    )
    .join("")

  const carrying = agent.inventory?.items ?? {}
  const carriedTotal = Object.values(carrying).reduce(
    (total, quantity) => total + quantity,
    0,
  )
  const carriedText =
    Object.entries(carrying)
      .map(([kind, quantity]) => `${quantity} ${kind}`)
      .join(", ") || "empty"

  const barsHtml =
    `<div class="agent-bars">` +
    agentBar("hunger", agent.needs.hunger, "#c0392b") +
    agentBar("thirst", agent.needs.water, "#27a4c0") +
    agentBar("rest", agent.needs.rest, "#5b8dd9") +
    agentBar(
      "carrying",
      carriedTotal / INVENTORY_CAPACITY,
      "#e67e22",
      carriedText,
    ) +
    `</div>`

  agentPanelBody.innerHTML = infoHtml + barsHtml
}
