import { useEffect, useRef, useState } from 'react'

export const World = () => {
  const canvasRef = useRef<HTMLCanvasElement>(null)

  const GRID_SIZE = 100
  const CELL_SIZE = 30
  const WORLD_SIZE = GRID_SIZE * CELL_SIZE
  const SCROLL_SPEED = 100

  const [cameraX, setCameraX] = useState(0)
  const [cameraY, setCameraY] = useState(0)

  const [viewportWidth, setViewportWidth] = useState(window.innerWidth)
  const [viewportHeight, setViewportHeight] = useState(window.innerHeight)

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
    if (!ctx) return

    ctx.clearRect(0, 0, viewportWidth, viewportHeight)

    const startX = Math.max(0, Math.floor(cameraX / CELL_SIZE))
    const endX = Math.min(
      GRID_SIZE,
      Math.ceil((cameraX + viewportWidth) / CELL_SIZE)
    )

    const startY = Math.max(0, Math.floor(cameraY / CELL_SIZE))
    const endY = Math.min(
      GRID_SIZE,
      Math.ceil((cameraY + viewportHeight) / CELL_SIZE)
    )

    for (let x = startX; x < endX; x++) {
      for (let y = startY; y < endY; y++) {
        ctx.fillStyle = generateCellColor(x, y)
        ctx.fillRect(
          x * CELL_SIZE - cameraX,
          y * CELL_SIZE - cameraY,
          CELL_SIZE,
          CELL_SIZE
        )
      }
    }
  }

  useEffect(() => {
    const handleResize = () => {
      setViewportWidth(window.innerWidth)
      setViewportHeight(window.innerHeight)
    }

    window.addEventListener('resize', handleResize)

    const canvas = canvasRef.current
    if (canvas) canvas.focus()

    return () => window.removeEventListener('resize', handleResize)
  }, [])

  useEffect(() => {
    drawGrid()
  }, [cameraX, cameraY])

  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      switch (event.key) {
        case 'ArrowUp':
          event.preventDefault()
          setCameraY((prev) => Math.max(0, prev - SCROLL_SPEED))
          break
        case 'ArrowDown':
          event.preventDefault()
          setCameraY((prev) =>
            Math.min(WORLD_SIZE - viewportHeight, prev + SCROLL_SPEED)
          )
          break
        case 'ArrowLeft':
          event.preventDefault()
          setCameraX((prev) => Math.max(0, prev - SCROLL_SPEED))
          break
        case 'ArrowRight':
          event.preventDefault()
          setCameraX((prev) =>
            Math.min(WORLD_SIZE - viewportWidth, prev + SCROLL_SPEED)
          )
          break
        default:
          return
      }
    }

    window.addEventListener('keydown', handleKeyDown)

    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [viewportWidth, viewportHeight])

  return (
    <div
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        width: '100vw',
        height: '100vh',
        overflow: 'hidden',
        backgroundColor: '#000'
      }}
      className='world'
    >
      <canvas
        ref={canvasRef}
        width={viewportWidth}
        height={viewportHeight}
        tabIndex={0}
        style={{
          imageRendering: 'pixelated',
          display: 'block',
          outline: 'none'
        }}
        className='world-canvas'
      />

      <div
        style={{
          position: 'absolute',
          top: 10,
          left: 10,
          color: '#fff',
          fontFamily: 'monospace',
          fontSize: '14px',
          backgroundColor: 'rgba(0, 0, 0, 0.5)',
          padding: '5px',
          borderRadius: '5px'
        }}
      >
        Camera: ({cameraX}, {cameraY})<br />
        Viewport: {viewportWidth} x {viewportHeight}
      </div>
    </div>
  )
}
