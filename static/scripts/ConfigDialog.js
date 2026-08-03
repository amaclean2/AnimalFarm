import { API_BASE } from "./constants.js"

const CONFIG_STORAGE_KEY = "animalfarm_config"

const saveConfigToStorage = (values) => {
  localStorage.setItem(CONFIG_STORAGE_KEY, JSON.stringify(values))
}

const loadConfigFromStorage = () => {
  try {
    const raw = localStorage.getItem(CONFIG_STORAGE_KEY)
    return raw ? JSON.parse(raw) : null
  } catch {
    return null
  }
}

const configOverlay = document.getElementById("config-overlay")

const CONFIG_FIELDS = [
  { key: "agent_count", id: "agent-count", parse: parseInt },
  { key: "num_springs", id: "num-springs", parse: parseInt },
  { key: "max_age", id: "max-age", parse: parseInt },
  { key: "adult_drain", id: "adult-drain", parse: parseInt },
  { key: "reproduction_chance", id: "reproduction-chance", parse: parseFloat },
  {
    key: "spontaneous_mutation_rate",
    id: "spontaneous-mutation-rate",
    parse: parseFloat,
  },
]

const syncPair = (rangeEl, numberEl) => {
  rangeEl.addEventListener("input", () => {
    numberEl.value = rangeEl.value
  })
  numberEl.addEventListener("input", () => {
    const clamped = Math.max(
      +rangeEl.min,
      Math.min(+rangeEl.max, +numberEl.value),
    )
    rangeEl.value = clamped
  })
}

let configDefaults = {}

const populateDialog = (values) => {
  CONFIG_FIELDS.forEach(({ id }) => {
    const key = id.replace(/-/g, "_")
    const val = values[key] ?? values[id.replace(/-/g, "_")]
    const numEl = document.getElementById(`cfg-${id}`)
    const rngEl = document.getElementById(`cfg-${id}-range`)
    if (numEl && val !== undefined) numEl.value = val
    if (rngEl && val !== undefined) rngEl.value = val
  })
}

const initSyncPairs = () => {
  CONFIG_FIELDS.forEach(({ id }) => {
    const rng = document.getElementById(`cfg-${id}-range`)
    const num = document.getElementById(`cfg-${id}`)
    if (rng && num) syncPair(rng, num)
  })
}

initSyncPairs()

const populateSavedWorldsDropdown = (worlds) => {
  const select = document.getElementById("cfg-world-id")
  select.innerHTML = '<option value="">— generate random —</option>'

  for (const world of worlds) {
    const opt = document.createElement("option")
    opt.value = world.id
    opt.textContent = world.name
    opt.dataset.config = JSON.stringify(world.config ?? {})
    select.appendChild(opt)
  }
}

const onWorldSelect = () => {
  const select = document.getElementById("cfg-world-id")
  const opt = select.selectedOptions[0]

  if (!opt || !opt.dataset.config) return

  const config = JSON.parse(opt.dataset.config)

  if (config.num_springs !== undefined) {
    document.getElementById("cfg-num-springs").value = config.num_springs
    document.getElementById("cfg-num-springs-range").value = config.num_springs
  }
}

document
  .getElementById("cfg-world-id")
  .addEventListener("change", onWorldSelect)

export const openConfigDialog = async () => {
  const [defaults, savedWorlds] = await Promise.all([
    fetch(`${API_BASE}/config`).then((response) => response.json()),
    fetch(`${API_BASE}/world/saved`).then((response) => response.json()),
  ])

  configDefaults = defaults
  const saved = loadConfigFromStorage()
  populateDialog(saved ? { ...defaults, ...saved } : defaults)
  populateSavedWorldsDropdown(savedWorlds)
  document.getElementById("cfg-world-id").value = ""
  configOverlay.classList.add("open")
}

export const closeConfigDialog = () => {
  configOverlay.classList.remove("open")
}

export const readConfigValues = () => {
  const result = {}
  CONFIG_FIELDS.forEach(({ key, id, parse }) => {
    const el = document.getElementById(`cfg-${id}`)
    if (el) result[key] = parse(el.value)
  })
  saveConfigToStorage(result)
  const worldId = document.getElementById("cfg-world-id")?.value
  if (worldId) result.world_id = worldId
  return result
}

document
  .getElementById("config-close")
  .addEventListener("click", closeConfigDialog)
document
  .getElementById("config-cancel")
  .addEventListener("click", closeConfigDialog)
document
  .getElementById("config-reset")
  .addEventListener("click", () => populateDialog(configDefaults))
configOverlay.addEventListener("click", (event) => {
  if (event.target === configOverlay) closeConfigDialog()
})

// ── Info icon tooltips ────────────────────────────────────────────────────────

const configTooltip = document.createElement("div")
configTooltip.id = "config-tooltip"
document.body.appendChild(configTooltip)

document.querySelectorAll(".info-icon").forEach((icon) => {
  icon.addEventListener("mouseenter", () => {
    const rect = icon.getBoundingClientRect()
    configTooltip.textContent = icon.dataset.tooltip
    // right-align tooltip to the icon so it opens leftward inside the dialog
    configTooltip.style.top = `${rect.bottom + 7}px`
    configTooltip.style.left = `${rect.right - 210}px`
    configTooltip.classList.add("visible")
  })
  icon.addEventListener("mouseleave", () => {
    configTooltip.classList.remove("visible")
  })
})
