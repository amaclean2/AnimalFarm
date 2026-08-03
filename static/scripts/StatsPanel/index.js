import { API_BASE } from "../constants.js"
import { agents, getClockState, setSelectedAgentId } from "../state.js"
import { abbreviateField } from "../utils.js"
import { applyClockState } from "../Clock.js"
import { updateAgentPanel } from "../AgentPanel.js"
import { renderGeneChart } from "./GeneChart.js"
import {
  renderPopulationChart,
  initPopulationChartInteraction,
} from "./PopulationChart.js"

const modalOverlay = document.getElementById("modal-overlay")
const modalBody = document.getElementById("modal-body")
const btnStats = document.getElementById("btn-stats")

let pausedForStats = false

export const openStats = async () => {
  applyClockState("paused")
  pausedForStats = true

  const [, data] = await Promise.all([
    fetch(`${API_BASE}/clock/pause`, { method: "POST" }),
    fetch(`${API_BASE}/stats`).then((response) => response.json()),
  ])

  const scalarEntries = Object.entries(data).filter(
    ([, value]) => typeof value !== "object",
  )
  const arrayEntries = Object.entries(data).filter(
    ([key, value]) => Array.isArray(value) && key !== "gene_stats",
  )

  let html = ""

  if (scalarEntries.length) {
    html += `<div class="stats-summary">`
    html += scalarEntries
      .map(
        ([key, value]) => `
        <div class="stats-summary-item">
          <div class="label">${key.replace(/_/g, " ")}</div>
          <div class="value">${value}</div>
        </div>`,
      )
      .join("")
    html += `</div>`
  }

  if (Array.isArray(data.agents) && data.agents.length) {
    html += renderPopulationChart(data.agents, data.tick_count)
  }

  if (Array.isArray(data.gene_stats) && data.gene_stats.length) {
    html += renderGeneChart(data.gene_stats)
  }

  html += arrayEntries
    .map(([key, rawRows]) => {
      if (!rawRows.length) {
        return `<div class="stats-section"><h4>${key.replace(/_/g, " ")}</h4><span class="stats-empty">None</span></div>`
      }

      const rows =
        key === "agents"
          ? [...rawRows].sort((a, b) => b.birth_tick - a.birth_tick)
          : rawRows

      const rawColumns = Object.keys(rows[0]).filter(
        (col) => col !== "x" && col !== "y",
      )
      const columns = [
        ...rawColumns.filter((col) => col === "id"),
        ...rawColumns.filter((col) => col === "age"),
        ...rawColumns.filter((col) => col !== "id" && col !== "age"),
      ]
      const maxAge = columns.includes("age")
        ? Math.max(...rows.map((row) => row.age ?? 0))
        : 0

      const headerRow = columns
        .map((col) => `<th>${col.replace(/_/g, " ")}</th>`)
        .join("")
      const dataRows = rows
        .map((row) => {
          const cells = columns
            .map((col) => {
              if (col === "age") {
                const percentage =
                  maxAge > 0 ? ((row.age ?? 0) / maxAge) * 100 : 0
                return `<td><div class="age-bar"><div style="width:${percentage.toFixed(1)}%"></div></div></td>`
              }
              return `<td>${abbreviateField(row[col])}</td>`
            })
            .join("")
          return key === "agents"
            ? `<tr data-agent-id="${row.id}" data-alive="${row.alive}">${cells}</tr>`
            : `<tr>${cells}</tr>`
        })
        .join("")

      return `
        <div class="stats-section">
          <h4>${key.replace(/_/g, " ")}</h4>
          <table class="stats-table">
            <thead><tr>${headerRow}</tr></thead>
            <tbody>${dataRows}</tbody>
          </table>
        </div>`
    })
    .join("")

  modalBody.innerHTML = html
  modalOverlay.classList.add("open")

  if (Array.isArray(data.agents) && data.agents.length) {
    initPopulationChartInteraction(modalBody, data.agents, data.tick_count)
  }
}

export const closeStats = () => {
  modalOverlay.classList.remove("open")
  if (pausedForStats) {
    fetch(`${API_BASE}/clock/resume`, { method: "POST" })
    applyClockState("running")
    pausedForStats = false
  }
}

btnStats.addEventListener("click", openStats)

document.getElementById("modal-close").addEventListener("click", closeStats)
modalOverlay.addEventListener("click", (event) => {
  if (event.target === modalOverlay) closeStats()
})

modalBody.addEventListener("click", (event) => {
  const row = event.target.closest("tr[data-agent-id]")
  if (!row || row.dataset.alive !== "true") return

  const agent = agents.get(row.dataset.agentId)
  if (!agent) return

  setSelectedAgentId(agent.id)
  updateAgentPanel(agent)
  closeStats()
})
