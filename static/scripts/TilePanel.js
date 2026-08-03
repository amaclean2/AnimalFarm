import {
  getElevationAt,
  getEffectiveTemperatureAt,
  getEffectivePrecipitationAt,
} from "./state.js"
import { toCelsius } from "./utils.js"

const tilePanel = document.getElementById("tile-panel")
const tilePanelTitle = document.getElementById("tile-panel-title")
const tilePanelBody = document.getElementById("tile-panel-body")

const PLANT_TYPE_LABELS = {
  fruit_tree: "Fruit Tree",
}

const ELEV_MAX_M = 2000
const toMetres = (fraction) => Math.round(fraction * ELEV_MAX_M)

const tileBar = (label, value, color, text) => {
  const pct = Math.min(100, Math.max(0, value * 100)).toFixed(1)
  const display = text ?? `${pct}%`
  return `
    <div class="agent-bar-row">
      <div class="agent-bar-label">${label}<span class="agent-bar-val">${display}</span></div>
      <div class="agent-bar-track"><div class="agent-bar-fill" style="width:${pct}%;background:${color}"></div></div>
    </div>`
}

export const updateTilePanel = (x, y, plant, isRiver = false) => {
  if (!tilePanel) return

  const typeLabel = isRiver
    ? "River"
    : plant
      ? (PLANT_TYPE_LABELS[plant.plant_type] ?? plant.plant_type)
      : "Bare"
  if (tilePanelTitle)
    tilePanelTitle.textContent = `Tile (${x}, ${y}) — ${typeLabel}`

  const elev = getElevationAt(x, y)
  const temp = getEffectiveTemperatureAt(x, y)
  const precip = getEffectivePrecipitationAt(x, y)

  let barsHtml =
    `<div class="agent-bars">` +
    `<div class="agent-row"><span>elevation</span><span class="val">${toMetres(elev)} m</span></div>` +
    tileBar(
      "temperature",
      temp,
      "#c0392b",
      `${toCelsius(temp).toFixed(1)} °C`,
    ) +
    tileBar("precipitation", precip, "#27a4c0") +
    (plant
      ? tileBar(
          "fruit",
          plant.fruit_count / plant.max_fruit,
          "#27ae60",
          `${Math.floor(plant.fruit_count)}/${plant.max_fruit}`,
        ) +
        `<div class="agent-row"><span>growth rate</span><span class="val">${plant.growth_rate.toFixed(4)}/tick</span></div>`
      : "") +
    `</div>`

  if (tilePanelBody) tilePanelBody.innerHTML = barsHtml
  tilePanel.classList.remove("hidden")
}

export const clearTilePanel = () => {
  if (tilePanel) tilePanel.classList.add("hidden")
}
