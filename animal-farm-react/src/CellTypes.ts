export const CellType = {
  DIRT: 'dirt',
  WATER: 'water',
  TREE: 'tree',
  GRASS: 'grass'
} as const

export type CellType = (typeof CellType)[keyof typeof CellType]

export interface CellState {
  type: CellType
  resources: number
  fertility: number
  lastHarvested?: number
  growthStage?: number
}

export interface Position {
  x: number
  y: number
}
