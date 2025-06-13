import { useEffect, useRef } from 'react'

export const World = () => {
  const canvasRef = useRef<HTMLCanvasElement>(null)

  const GRID_SIZE = 100
  const CELL_SIZE = 10
  const CANVAS_SIZE = GRID_SIZE * CELL_SIZE

  const generateCellColor = (x: number, y: number) => {
    const hue = Math.floor(Math.random() * 360)
    const saturation = 40 + ((x + y) % 60)
    const lightness = 30 + ((x * y) % 40)

    return `hsl(${hue}, ${saturation}%, ${lightness}%)`
  }

  const drawGrid = () => {
    const canvas = canvasRef.current
    if (!canvas) return

    const ctx = canvas.getContext('2d')

    ctx!.clearRect(0, 0, CANVAS_SIZE, CANVAS_SIZE)

    for (let x = 0; x < GRID_SIZE; x++) {
      for (let y = 0; y < GRID_SIZE; y++) {
        ctx!.fillStyle = generateCellColor(x, y)
        ctx!.fillRect(x * CELL_SIZE, y * CELL_SIZE, CELL_SIZE, CELL_SIZE)
      }
    }
  }

  useEffect(() => {
    drawGrid()
  }, [])

  return (
    <div className='world'>
      <canvas
        ref={canvasRef}
        width={CANVAS_SIZE}
        height={CANVAS_SIZE}
        className='world-canvas'
        style={{ imageRendering: 'pixelated' }}
      />
    </div>
  )
}
