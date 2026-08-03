import { agents, plants, getIsNight, getDayNumber } from "./state.js"

const agentCountEl = document.getElementById("agent-count")
const plantCountEl = document.getElementById("plant-count")
const dayNumberEl = document.getElementById("day-number")
const dayIconEl = document.getElementById("day-icon")

export const btnStart = document.getElementById("btn-start")

const panelEl = document.getElementById("panel")
const panelToggle = document.getElementById("panel-toggle")
const panelToggleIcon = panelToggle.querySelector("span")

panelToggle.addEventListener("click", () => {
  const collapsed = panelEl.classList.toggle("collapsed")
  panelToggleIcon.textContent = collapsed ? "☰" : "✕"
})

export const updateDayNightUI = () => {
  if (dayNumberEl) dayNumberEl.textContent = getDayNumber()
  if (dayIconEl) dayIconEl.textContent = getIsNight() ? "🌙" : "☀️"
}

export const syncCounters = () => {
  agentCountEl.textContent = agents.size
  plantCountEl.textContent = plants.size
}

const btnFullscreen = document.getElementById("btn-fullscreen")
btnFullscreen.addEventListener("click", () => {
  if (!document.fullscreenElement) {
    document.documentElement.requestFullscreen()
  } else {
    document.exitFullscreen()
  }
})
document.addEventListener("fullscreenchange", () => {
  btnFullscreen.textContent = document.fullscreenElement
    ? "⛶ Exit Fullscreen"
    : "⛶ Fullscreen"
})
