import { Cell } from './Cell'
import { CellType } from './CellTypes'

export class RiverGenerator {
  private gridSize: number
  private elevationMap: number[][] = []

  constructor(gridSize: number) {
    this.gridSize = gridSize
    this.generateElevationMap()
  }

  private generateElevationMap(): void {
    this.elevationMap = []
    for (let x = 0; x < this.gridSize; x++) {
      this.elevationMap[x] = []
      for (let y = 0; y < this.gridSize; y++) {
        // Combine multiple noise layers for more interesting terrain
        const largeScale = this.simpleNoise(x / 20, y / 20) * 0.5
        const mediumScale = this.simpleNoise(x / 10, y / 10) * 0.3
        const smallScale = this.simpleNoise(x / 5, y / 5) * 0.2

        this.elevationMap[x][y] = largeScale + mediumScale + smallScale
      }
    }
  }

  private simpleNoise(x: number, y: number): number {
    const value = Math.sin(x * 12.9898 + y * 78.233) * 43758.5453
    return (value - Math.floor(value)) * 2 - 1 // Range: -1 to 1
  }

  getElevation(x: number, y: number): number {
    if (!this.isValidPosition(x, y)) return 0
    return this.elevationMap[x][y]
  }

  generateRivers(grid: Cell[][]): void {
    const waterBodies = this.findWaterCells(grid)
    const numRivers = Math.floor(this.gridSize / 30) + 1

    for (let i = 0; i < numRivers; i++) {
      const startPoint = this.findHighElevationPoint()
      const destination = this.findNearestWaterBody(waterBodies, startPoint)

      if (destination) {
        this.createNaturalRiver(grid, startPoint, destination)
      }
    }
  }

  findLowElevationPoint(): { x: number; y: number } {
    let bestX = 0,
      bestY = 0,
      lowestElevation = Infinity

    for (let i = 0; i < 20; i++) {
      const x = Math.floor(Math.random() * this.gridSize)
      const y = Math.floor(Math.random() * this.gridSize)

      if (this.elevationMap[x][y] < lowestElevation) {
        lowestElevation = this.elevationMap[x][y]
        bestX = x
        bestY = y
      }
    }

    return { x: bestX, y: bestY }
  }

  private findHighElevationPoint(): { x: number; y: number } {
    let bestX = 0,
      bestY = 0,
      highestElevation = -Infinity

    for (let i = 0; i < 30; i++) {
      const x = Math.floor(Math.random() * this.gridSize)
      const y = Math.floor(Math.random() * this.gridSize)

      if (this.elevationMap[x][y] > highestElevation) {
        highestElevation = this.elevationMap[x][y]
        bestX = x
        bestY = y
      }
    }

    return { x: bestX, y: bestY }
  }

  private findNearestWaterBody(
    waterBodies: Cell[],
    point: { x: number; y: number }
  ): Cell | null {
    if (waterBodies.length === 0) return null

    let nearestWater = waterBodies[0]
    let minDistance = Infinity

    for (const water of waterBodies) {
      const pos = water.getPosition()
      const distance = Math.sqrt(
        (pos.x - point.x) ** 2 + (pos.y - point.y) ** 2
      )

      if (distance < minDistance) {
        minDistance = distance
        nearestWater = water
      }
    }

    return nearestWater
  }

  private createNaturalRiver(
    grid: Cell[][],
    start: { x: number; y: number },
    end: Cell
  ): void {
    const endPos = end.getPosition()
    const riverPath = this.generateRiverPath(start, endPos)

    // Create the main river channel
    for (const point of riverPath) {
      if (this.isValidPosition(point.x, point.y)) {
        grid[point.x][point.y] = new Cell(point.x, point.y, CellType.WATER)

        // Add some width variation
        if (Math.random() < 0.3) {
          this.addRiverWidth(grid, point.x, point.y)
        }
      }
    }

    // Add tributaries
    this.addTributaries(grid, riverPath)
  }

  private generateRiverPath(
    start: { x: number; y: number },
    end: { x: number; y: number }
  ): { x: number; y: number }[] {
    const path = []
    const current = { ...start }
    const target = { ...end }

    let noiseOffset = Math.random() * 1000
    const bendStrength = 0.3 + Math.random() * 0.4

    while (
      Math.abs(current.x - target.x) > 1 ||
      Math.abs(current.y - target.y) > 1
    ) {
      path.push({ ...current })

      // Basic direction toward target
      const dx = target.x - current.x
      const dy = target.y - current.y
      const distance = Math.sqrt(dx * dx + dy * dy)

      if (distance === 0) break

      // Normalize direction
      const dirX = dx / distance
      const dirY = dy / distance

      // Add elevation-based flow
      const { x: elevationDirX, y: elevationDirY } = this.getElevationGradient(
        current.x,
        current.y
      )

      // Add noise for natural meandering
      const noiseValue = this.simpleNoise(noiseOffset, 0)
      const perpendicularX = -dirY * noiseValue * bendStrength
      const perpendicularY = dirX * noiseValue * bendStrength

      // Combine all forces
      const finalDirX = dirX * 0.6 + elevationDirX * 0.3 + perpendicularX
      const finalDirY = dirY * 0.6 + elevationDirY * 0.3 + perpendicularY

      // Move to next position
      current.x +=
        Math.sign(finalDirX) * (Math.random() < Math.abs(finalDirX) ? 1 : 0)
      current.y +=
        Math.sign(finalDirY) * (Math.random() < Math.abs(finalDirY) ? 1 : 0)

      // Keep within bounds
      current.x = Math.max(0, Math.min(this.gridSize - 1, current.x))
      current.y = Math.max(0, Math.min(this.gridSize - 1, current.y))

      noiseOffset += 0.1

      // Safety check
      if (path.length > this.gridSize * 2) break
    }

    path.push(target)
    return path
  }

  private getElevationGradient(x: number, y: number): { x: number; y: number } {
    if (!this.isValidPosition(x, y)) return { x: 0, y: 0 }

    const currentElevation = this.elevationMap[x][y]

    let gradientX = 0,
      gradientY = 0

    if (x > 0) gradientX += currentElevation - this.elevationMap[x - 1][y]
    if (x < this.gridSize - 1)
      gradientX += currentElevation - this.elevationMap[x + 1][y]
    if (y > 0) gradientY += currentElevation - this.elevationMap[x][y - 1]
    if (y < this.gridSize - 1)
      gradientY += currentElevation - this.elevationMap[x][y + 1]

    const magnitude = Math.sqrt(gradientX * gradientX + gradientY * gradientY)
    if (magnitude > 0) {
      gradientX /= magnitude
      gradientY /= magnitude
    }

    return { x: gradientX, y: gradientY }
  }

  private addRiverWidth(grid: Cell[][], x: number, y: number): void {
    const directions = [
      [-1, 0],
      [1, 0],
      [0, -1],
      [0, 1],
      [-1, -1],
      [-1, 1],
      [1, -1],
      [1, 1]
    ]

    for (const [dx, dy] of directions) {
      const newX = x + dx
      const newY = y + dy

      if (this.isValidPosition(newX, newY) && Math.random() < 0.6) {
        if (grid[newX][newY].getType() !== CellType.WATER) {
          const elevation = this.elevationMap[newX][newY]
          grid[newX][newY] = new Cell(newX, newY, CellType.WATER, elevation)
        }
      }
    }
  }

  private addTributaries(
    grid: Cell[][],
    mainRiver: { x: number; y: number }[]
  ): void {
    const numTributaries = Math.floor(mainRiver.length / 20)

    for (let i = 0; i < numTributaries; i++) {
      const connectionPoint =
        mainRiver[Math.floor(Math.random() * mainRiver.length)]
      const tributaryStart = this.findNearbyHighPoint(connectionPoint)

      if (tributaryStart) {
        const tributaryPath = this.generateRiverPath(
          tributaryStart,
          connectionPoint
        )

        for (let j = 0; j < tributaryPath.length; j += 2) {
          const point = tributaryPath[j]
          if (this.isValidPosition(point.x, point.y)) {
            const elevation = this.elevationMap[point.x][point.y]
            grid[point.x][point.y] = new Cell(
              point.x,
              point.y,
              CellType.WATER,
              elevation
            )
          }
        }
      }
    }
  }

  private findNearbyHighPoint(center: {
    x: number
    y: number
  }): { x: number; y: number } | null {
    const searchRadius = 10
    let bestPoint = null
    let highestElevation = this.elevationMap[center.x][center.y]

    for (let dx = -searchRadius; dx <= searchRadius; dx++) {
      for (let dy = -searchRadius; dy <= searchRadius; dy++) {
        const x = center.x + dx
        const y = center.y + dy

        if (this.isValidPosition(x, y)) {
          if (this.elevationMap[x][y] > highestElevation) {
            highestElevation = this.elevationMap[x][y]
            bestPoint = { x, y }
          }
        }
      }
    }

    return bestPoint
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

  private isValidPosition(x: number, y: number): boolean {
    return x >= 0 && x < this.gridSize && y >= 0 && y < this.gridSize
  }
}
