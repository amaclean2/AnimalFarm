import { CellType, type CellState, type Position } from './CellTypes'

export class Cell {
  private position: Position
  private state: CellState
  private neighbors: Cell[] = []
  private elevation: number = 0

  constructor(
    x: number,
    y: number,
    type: CellType = CellType.DIRT,
    elevation: number = 0
  ) {
    this.position = { x, y }
    this.elevation = elevation
    this.state = this.initializeState(type)
  }

  private initializeState(type: CellType): CellState {
    const baseState: CellState = {
      type,
      resources: 0,
      fertility: Math.random() * 0.3 + 0.7
    }

    switch (type) {
      case CellType.WATER:
        return {
          ...baseState,
          resources: 100,
          fertility: 1.0
        }

      case CellType.TREE:
        return {
          ...baseState,
          resources: Math.floor(Math.random() * 10) + 5,
          growthStage: Math.floor(Math.random() * 4),
          fertility: baseState.fertility * 1.2
        }
      case CellType.GRASS:
      case CellType.DIRT:
      default:
        return baseState
    }
  }

  getType(): CellType {
    return this.state.type
  }

  getPosition(): Position {
    return this.position
  }

  getElevation(): number {
    return this.elevation
  }

  setElevation(elevation: number): void {
    this.elevation = elevation
  }

  getResources(): number {
    return this.state.resources
  }

  getFertility(): number {
    return this.state.fertility
  }

  getGrowthStage(): number | undefined {
    return this.state.growthStage
  }

  setNeighbors(neighbors: Cell[]): void {
    this.neighbors = neighbors
  }

  getNeighbors(): Cell[] {
    return this.neighbors
  }

  harvestResources(amount: number = 1): number {
    if (this.state.type === CellType.WATER) {
      return Math.min(amount, this.state.resources)
    }

    if (this.state.type === CellType.TREE && this.state.resources > 0) {
      const harvested = Math.min(amount, this.state.resources)
      this.state.resources -= harvested
      this.state.lastHarvested = Date.now()
      return harvested
    }

    return 0
  }

  getDistanceToWater(): number {
    const waterCells = this.findCellsOfType(CellType.WATER, 10)
    if (waterCells.length === 0) return Infinity

    return Math.min(...waterCells.map((cell: Cell) => this.getDistanceTo(cell)))
  }

  private getDistanceTo(other: Cell): number {
    const otherPos = other.getPosition()
    const dx = this.position.x - otherPos.x
    const dy = this.position.y - otherPos.y

    return Math.sqrt(dx ** 2 + dy ** 2)
  }

  private findCellsOfType(type: CellType, maxRadius: number): Cell[] {
    const found: Cell[] = []
    const visited = new Set<string>()
    const queue: Array<{ cell: Cell; distance: number }> = [
      { cell: this, distance: 0 }
    ]

    while (queue.length > 0) {
      const { cell, distance } = queue.shift()!
      const key = `${cell.position.x},${cell.position.y}`

      if (visited.has(key) || distance > maxRadius) continue
      visited.add(key)

      if (cell.getType() === type) {
        found.push(cell)
      }

      cell.neighbors.forEach((neighbor: Cell) => {
        queue.push({ cell: neighbor, distance: distance + 1 })
      })
    }

    return found
  }

  update(deltaTime: number): void {
    switch (this.state.type) {
      case CellType.TREE:
        this.updateTree()
        break
      case CellType.WATER:
        // expand on this later
        break
      case CellType.GRASS:
      case CellType.DIRT:
        this.updateDirt(deltaTime)
        break
    }
  }

  private updateTree(): void {
    const timeSinceHarvest = this.state.lastHarvested
      ? Date.now() - this.state.lastHarvested
      : Infinity

    const regenRate = this.state.fertility * 0.1
    const maxFruit = 20 + (this.state.growthStage || 0) * 5

    if (timeSinceHarvest > 5000 && this.state.resources < maxFruit) {
      this.state.resources = Math.min(
        maxFruit,
        this.state.resources + regenRate
      )
    }
  }

  private updateDirt(deltaTime: number): void {
    const waterDistance = this.getDistanceToWater()
    const treeGrowthChance = this.calculateTreeGrowthProbability(waterDistance)

    if (Math.random() < treeGrowthChance * deltaTime) {
      this.transformToTree()
    }
  }

  private calculateTreeGrowthProbability(waterDistance: number): number {
    if (waterDistance === Infinity) return 0

    if (waterDistance < 1) return 0.0005
    if (waterDistance < 3) return 0.002
    if (waterDistance < 6) return 0.001
    return 0.0002
  }

  private transformToTree(): void {
    this.state.type = CellType.TREE
    this.state.resources = Math.floor(Math.random() * 5) + 2
    this.state.growthStage = 0
    this.state.fertility *= 1.1
  }

  getColor(): string {
    const normalizedElevation = (this.elevation + 1) / 2

    switch (this.state.type) {
      case CellType.WATER: {
        return `hsl(220 80%, ${40 + this.state.fertility * 20}%)`
      }
      case CellType.TREE: {
        const stage = this.state.growthStage || 0
        const resourceEffect = (this.state.resources / 20) * 10
        const elevationEffect = normalizedElevation * 15
        const baseLightness = 25 + stage * 5 + resourceEffect + elevationEffect
        return `hsl(120 ${60 - normalizedElevation * 10}%, ${baseLightness}%)`
      }
      case CellType.DIRT:
      case CellType.GRASS:
      default: {
        const fertility = this.state.fertility

        const elevationLightness = normalizedElevation * 30
        const fertilityEffect = fertility * 20
        const baseLightness = 20 + fertilityEffect + elevationLightness

        const elevationHue = 30 + normalizedElevation * 20
        const saturation =
          (30 + fertility * 40) * (1 - normalizedElevation * 0.3)

        return `hsl(${elevationHue}, ${saturation}%, ${baseLightness}%)`
      }
    }
  }

  getDebugInfo(): string {
    return `${this.state.type} (${this.position.x}, ${this.position.y})
    Resources: ${this.state.resources.toFixed(1)},
    Fertility: ${this.state.fertility.toFixed(2)}
    ${
      this.state.growthStage !== undefined
        ? `Growth: ${this.state.growthStage}`
        : ''
    }
    Water Distance: ${this.getDistanceToWater().toFixed(1)}`
  }
}
