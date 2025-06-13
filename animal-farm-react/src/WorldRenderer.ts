import type { Cell } from './Cell'
import { WORLD_CONFIG } from './WorldConfig'
import { calculateVisibleCells } from './WorldUtils'

export class WorldRenderer {
  private canvas: HTMLCanvasElement
  private ctx: CanvasRenderingContext2D
  private world: Cell[][] | null = null

  constructor(canvas: HTMLCanvasElement) {
    this.canvas = canvas

    const ctx = canvas.getContext('2d')

    if (!ctx) {
      throw new Error('Failed to get canvas context')
    }

    this.ctx = ctx
  }

  setWorld(world: Cell[][]): void {
    this.world = world
  }

  render(
    cameraX: number,
    cameraY: number,
    viewportWidth: number,
    viewportHeight: number
  ) {
    this.ctx.clearRect(0, 0, viewportWidth, viewportHeight)

    if (!this.world) {
      this.renderColoredGrid(cameraX, cameraY, viewportWidth, viewportHeight)
      return
    }

    const { startX, endX, startY, endY } = calculateVisibleCells(
      cameraX,
      cameraY,
      viewportWidth,
      viewportHeight,
      WORLD_CONFIG.CELL_SIZE,
      WORLD_CONFIG.GRID_SIZE
    )

    for (let x = startX; x < endX; x++) {
      for (let y = startY; y < endY; y++) {
        const cell = this.world[x][y]
        this.ctx.fillStyle = cell.getColor()
        this.ctx.fillRect(
          x * WORLD_CONFIG.CELL_SIZE - cameraX,
          y * WORLD_CONFIG.CELL_SIZE - cameraY,
          WORLD_CONFIG.CELL_SIZE,
          WORLD_CONFIG.CELL_SIZE
        )
      }
    }
  }

  private renderColoredGrid(
    cameraX: number,
    cameraY: number,
    viewportWidth: number,
    viewportHeight: number
  ) {
    const { startX, endX, startY, endY } = calculateVisibleCells(
      cameraX,
      cameraY,
      viewportWidth,
      viewportHeight,
      WORLD_CONFIG.CELL_SIZE,
      WORLD_CONFIG.GRID_SIZE
    )

    for (let x = startX; x < endX; x++) {
      for (let y = startY; y < endY; y++) {
        const hue = ((x * 7 + y * 13) * 137.5) % 360
        const saturation = 40 + ((x + y) % 60)
        const lightness = 30 + ((x * y) % 40)
        this.ctx.fillStyle = `hsl(${hue}, ${saturation}%, ${lightness}%)`

        this.ctx.fillRect(
          x * WORLD_CONFIG.CELL_SIZE - cameraX,
          y * WORLD_CONFIG.CELL_SIZE - cameraY,
          WORLD_CONFIG.CELL_SIZE,
          WORLD_CONFIG.CELL_SIZE
        )
      }
    }
  }
}
