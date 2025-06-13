export const generateCellColor = (x: number, y: number): string => {
  const hue = ((x * 7 + y * 13) * 137.5) % 360
  const saturation = 40 + ((x + y) % 60)
  const lightness = 30 + ((x * y) % 40)

  return `hsl(${hue}, ${saturation}%, ${lightness}%)`
}

export const calculateVisibleCells = (
  cameraX: number,
  cameraY: number,
  viewportWidth: number,
  viewportHeight: number,
  cellSize: number,
  gridSize: number
) => {
  const startX = Math.max(0, Math.floor(cameraX / cellSize))
  const endX = Math.min(
    gridSize,
    Math.ceil((cameraX + viewportWidth) / cellSize)
  )

  const startY = Math.max(0, Math.floor(cameraY / cellSize))
  const endY = Math.min(
    gridSize,
    Math.ceil((cameraY + viewportHeight) / cellSize)
  )

  return { startX, endX, startY, endY }
}
