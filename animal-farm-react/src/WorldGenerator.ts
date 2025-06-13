import { Cell } from './Cell'
import { CellType } from './CellTypes'

export class WorldGenerator {
  private gridSize: number

  constructor(gridSize: number) {
    this.gridSize = gridSize
  }

  generateWorld(): Cell[][] {
    const grid: Cell[][] = []
    for (let x = 0; x < this.gridSize; x++) {
      grid[x] = []
      for (let y = 0; y < this.gridSize; y++) {
        grid[x][y] = new Cell(x, y, CellType.DIRT)
      }
    }

    this.generateWaterBodies(grid)
    this.generateTrees(grid)
    this.setupNeighbors(grid)

    return grid
  }

  private generateWaterBodies(grid: Cell[][]): void {
    const numLakes = Math.floor(this.gridSize / 20) + 2

    for (let i = 0; i < numLakes; i++) {
      const centerX = Math.floor(Math.random() * this.gridSize)
      const centerY = Math.floor(Math.random() * this.gridSize)
      const size = Math.floor(Math.random() * 8) + 3

      this.createWaterBody(grid, centerX, centerY, size)
    }

    this.generateRivers(grid)
  }

  private createWaterBody(
    grid: Cell[][],
    centerX: number,
    centerY: number,
    maxRadius: number
  ): void {
    for (
      let x = Math.max(0, centerX - maxRadius);
      x < Math.min(this.gridSize, centerX + maxRadius);
      x++
    ) {
      for (
        let y = Math.max(0, centerY - maxRadius);
        y < Math.min(this.gridSize, centerY + maxRadius);
        y++
      ) {
        const distance = Math.sqrt((x - centerX) ** 2 + (y - centerY) ** 2)
        const radius = maxRadius * (0.6 + Math.random() * 0.4) // Irregular shape

        if (distance < radius) {
          grid[x][y] = new Cell(x, y, CellType.WATER)
        }
      }
    }
  }

  private generateRivers(grid: Cell[][]): void {
    const waterCells = this.findWaterCells(grid)
    const numRivers = Math.floor(waterCells.length / 10) // Connect some water bodies

    for (let i = 0; i < numRivers; i++) {
      const start = waterCells[Math.floor(Math.random() * waterCells.length)]
      const end = waterCells[Math.floor(Math.random() * waterCells.length)]

      if (start !== end) {
        this.createRiver(grid, start, end)
      }
    }
  }

  private createRiver(grid: Cell[][], start: Cell, end: Cell): void {
    const startPos = start.getPosition()
    const endPos = end.getPosition()
    const steps =
      Math.abs(startPos.x - endPos.x) + Math.abs(startPos.y - endPos.y)

    for (let step = 0; step <= steps; step++) {
      const t = step / steps
      const x = Math.floor(startPos.x + (endPos.x - startPos.x) * t)
      const y = Math.floor(startPos.y + (endPos.y - startPos.y) * t)

      if (x >= 0 && x < this.gridSize && y >= 0 && y < this.gridSize) {
        if (grid[x][y].getType() !== CellType.WATER) {
          grid[x][y] = new Cell(x, y, CellType.WATER)
        }
      }
    }
  }

  private generateTrees(grid: Cell[][]): void {
    for (let x = 0; x < this.gridSize; x++) {
      for (let y = 0; y < this.gridSize; y++) {
        if (grid[x][y].getType() === CellType.DIRT) {
          const treeChance = this.calculateTreeProbability(grid, x, y)

          if (Math.random() < treeChance) {
            grid[x][y] = new Cell(x, y, CellType.TREE)
          }
        }
      }
    }
  }

  private calculateTreeProbability(
    grid: Cell[][],
    x: number,
    y: number
  ): number {
    const waterDistance = this.getDistanceToWater(grid, x, y)

    if (waterDistance === Infinity) return 0.05 // 5% chance far from water
    if (waterDistance < 1) return 0.1 // 10% right next to water
    if (waterDistance < 3) return 0.4 // 40% near water (grove formation)
    if (waterDistance < 6) return 0.2 // 20% moderate distance
    return 0.08 // 8% far from water
  }

  private getDistanceToWater(grid: Cell[][], x: number, y: number): number {
    let minDistance = Infinity
    const searchRadius = 15

    for (let dx = -searchRadius; dx <= searchRadius; dx++) {
      for (let dy = -searchRadius; dy <= searchRadius; dy++) {
        const checkX = x + dx
        const checkY = y + dy

        if (
          checkX >= 0 &&
          checkX < this.gridSize &&
          checkY >= 0 &&
          checkY < this.gridSize
        ) {
          if (grid[checkX][checkY].getType() === CellType.WATER) {
            const distance = Math.sqrt(dx * dx + dy * dy)
            minDistance = Math.min(minDistance, distance)
          }
        }
      }
    }

    return minDistance
  }

  private findWaterCells(grid: Cell[][]): Cell[] {
    const waterCells: Cell[] = []
    for (let x = 0; x < this.gridSize; x++) {
      for (let y = 0; y < this.gridSize; y++) {
        if (grid[x][y].getType() === CellType.WATER) {
          waterCells.push(grid[x][y])
        }
      }
    }
    return waterCells
  }

  private setupNeighbors(grid: Cell[][]): void {
    for (let x = 0; x < this.gridSize; x++) {
      for (let y = 0; y < this.gridSize; y++) {
        const neighbors: Cell[] = []

        // 8-directional neighbors
        for (let dx = -1; dx <= 1; dx++) {
          for (let dy = -1; dy <= 1; dy++) {
            if (dx === 0 && dy === 0) continue // Skip self

            const nx = x + dx
            const ny = y + dy

            if (
              nx >= 0 &&
              nx < this.gridSize &&
              ny >= 0 &&
              ny < this.gridSize
            ) {
              neighbors.push(grid[nx][ny])
            }
          }
        }

        grid[x][y].setNeighbors(neighbors)
      }
    }
  }
}
