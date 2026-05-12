import { CELL_DESKTOP, CELL_MOBILE, WORLD_WIDTH, WORLD_HEIGHT, SCROLL_SPEED } from './constants.js'

const canvas = document.getElementById('game')
const panel = document.getElementById('panel')
const mobileQuery = window.matchMedia('(max-width: 600px)')

export const camera = { x: 0, y: 0 }
export const viewport = { cellSize: mobileQuery.matches ? CELL_MOBILE : CELL_DESKTOP }

const pressedKeys = new Set()

export const clampCamera = () => {
  camera.x = Math.max(0, Math.min(Math.max(0, WORLD_WIDTH * viewport.cellSize - canvas.width), camera.x))
  camera.y = Math.max(0, Math.min(Math.max(0, WORLD_HEIGHT * viewport.cellSize - canvas.height), camera.y))
}

export const resize = () => {
  viewport.cellSize = mobileQuery.matches ? CELL_MOBILE : CELL_DESKTOP
  const panelBottom = mobileQuery.matches
    ? Math.round(panel.getBoundingClientRect().bottom) + 8
    : 0
  canvas.style.marginTop = panelBottom + 'px'
  canvas.width = window.innerWidth
  canvas.height = window.innerHeight - panelBottom
}

export const scrollCamera = (deltaTime) => {
  if (pressedKeys.has('ArrowLeft') || pressedKeys.has('a')) camera.x -= SCROLL_SPEED * deltaTime
  if (pressedKeys.has('ArrowRight') || pressedKeys.has('d')) camera.x += SCROLL_SPEED * deltaTime
  if (pressedKeys.has('ArrowUp') || pressedKeys.has('w')) camera.y -= SCROLL_SPEED * deltaTime
  if (pressedKeys.has('ArrowDown') || pressedKeys.has('s')) camera.y += SCROLL_SPEED * deltaTime
  clampCamera()
}

window.addEventListener('keydown', (event) => {
  if (['ArrowUp', 'ArrowDown', 'ArrowLeft', 'ArrowRight'].includes(event.key)) {
    event.preventDefault()
  }
  pressedKeys.add(event.key)
})

window.addEventListener('keyup', (event) => pressedKeys.delete(event.key))
