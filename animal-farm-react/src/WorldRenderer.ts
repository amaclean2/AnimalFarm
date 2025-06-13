import { WORLD_CONFIG } from './WorldConfig'
import { calculateVisibleCells, generateCellColor } from './WorldUtils'

export class WorldRenderer {
  private canvas: HTMLCanvasElement
  private ctx: CanvasRenderingContext2D

  constructor(canvas: HTMLCanvasElement) {
    this.canvas = canvas

    const ctx = canvas.getContext('2d')

    if (!ctx) {
      throw new Error('Failed to get canvas context')
    }

    this.ctx = ctx
  }

  render(
    cameraX: number,
    cameraY: number,
    viewportWidth: number,
    viewportHeight: number
  ) {
    this.ctx.clearRect(0, 0, viewportWidth, viewportHeight)

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
        this.ctx.fillStyle = generateCellColor(x, y)
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
