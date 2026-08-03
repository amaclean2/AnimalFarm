import { API_BASE } from "./constants.js"
import {
  getClockState,
  setClockState,
  setTickMs,
  snapAgentsToGrid,
} from "./state.js"

const btnStart = document.getElementById("btn-start")
const btnPause = document.getElementById("btn-pause")
const btnStop = document.getElementById("btn-stop")
const btnNextAgent = document.getElementById("btn-next-agent")
const statusEl = document.getElementById("status")

export const applyClockState = (state) => {
  setClockState(state)
  if (state === "paused" || state === "stopped") snapAgentsToGrid()
  btnStart.disabled = state !== "stopped"
  btnPause.disabled = state === "stopped"
  btnStop.disabled = state === "stopped"
  if (btnNextAgent) btnNextAgent.disabled = state === "stopped"
  btnPause.textContent = state === "paused" ? "▶ Resume" : "⏸ Pause"
  statusEl.textContent =
    { stopped: "Stopped", running: "Running", paused: "Paused" }[state] ?? state
}

const togglePause = () => {
  const clockState = getClockState()
  if (clockState === "running") {
    fetch(`${API_BASE}/clock/pause`, { method: "POST" })
    applyClockState("paused")
  } else if (clockState === "paused") {
    fetch(`${API_BASE}/clock/resume`, { method: "POST" })
    applyClockState("running")
  }
}

btnPause.addEventListener("click", togglePause)

btnStop.addEventListener("click", () => {
  fetch(`${API_BASE}/clock/stop`, { method: "POST" })
  applyClockState("stopped")
})

document.addEventListener("keydown", (event) => {
  if (event.key === "p" || event.key === "P") togglePause()
})

const speedSlider = document.getElementById("speed-slider")
const speedVal = document.getElementById("speed-val")

const sliderToInterval = (step) =>
  parseFloat((2.0 * Math.pow(0.025, (step - 1) / 9)).toFixed(3))

const formatInterval = (interval) =>
  interval < 1 ? `${Math.round(interval * 1000)}ms` : `${interval.toFixed(1)}s`

speedVal.textContent = formatInterval(
  sliderToInterval(parseInt(speedSlider.value, 10)),
)

speedSlider.addEventListener("input", () => {
  const interval = sliderToInterval(parseInt(speedSlider.value, 10))
  speedVal.textContent = formatInterval(interval)
  setTickMs(interval * 1000)
  fetch(`${API_BASE}/clock/speed`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ interval }),
  })
})
