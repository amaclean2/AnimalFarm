export const WORLD_WIDTH = 100
export const WORLD_HEIGHT = 100
export const CELL_DESKTOP = 30
export const CELL_MOBILE = 15
export const MAX_HEALTH = 200
export const MAX_REST = 200
export const SCROLL_SPEED = 600
export const API_BASE = ''

export const WS_URL = `${location.protocol === 'https:' ? 'wss' : 'ws'}://${location.host}/ws`

export const COLOR_PALETTE = [
  '#e74c3c', '#3498db', '#e67e22', '#2ecc71', '#9b59b6',
  '#1abc9c', '#f0c030', '#e91e63', '#00bcd4', '#8bc34a'
]

export const MUTATION_COLORS = {
  keen_sight:       '#3498db',
  poor_sight:       '#7f8c8d',
  slow_metabolism:  '#2ecc71',
  fast_metabolism:  '#e74c3c',
  light_sleeper:    '#f39c12',
  heavy_sleeper:    '#9b59b6',
  night_owl:        '#1abc9c',
}

export const MUTATION_PRIORITY = [
  'fast_metabolism', 'slow_metabolism',
  'keen_sight', 'poor_sight',
  'night_owl', 'light_sleeper', 'heavy_sleeper',
]

export const NO_MUTATION_COLOR = '#d4b896'

export const UUID_PATTERN = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i
