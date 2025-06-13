import { useEffect, useRef } from 'react'
import { WorldRenderer } from './WorldRenderer'
import { useViewport } from './useViewport'
import { useCameraControls } from './useCameraControls'
import { DebugInfo } from './DebugInfo'
import type { Cell } from './Cell'
import { WorldGenerator } from './WorldGenerator'
import { WORLD_CONFIG } from './WorldConfig'

export const World = () => {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const rendererRef = useRef<WorldRenderer | null>(null)
  const worldRef = useRef<Cell[][] | null>(null)

  const { viewportWidth, viewportHeight } = useViewport()
  const { cameraX, cameraY } = useCameraControls(viewportWidth, viewportHeight)

  useEffect(() => {
    const canvas = canvasRef.current

    if (canvas) {
      rendererRef.current = new WorldRenderer(canvas)

      const generator = new WorldGenerator(WORLD_CONFIG.GRID_SIZE)
      const world = generator.generateWorld()
      worldRef.current = world

      rendererRef.current.setWorld(world)
      canvas.focus()
    }
  }, [])

  useEffect(() => {
    if (rendererRef.current) {
      rendererRef.current.render(
        cameraX,
        cameraY,
        viewportWidth,
        viewportHeight
      )
    }
  }, [cameraX, cameraY, viewportWidth, viewportHeight])

  useEffect(() => {
    if (!worldRef.current) return

    const updateInterval = setInterval(() => {
      const world = worldRef.current!
      const deltaTime = 1000 / 60

      const sampleSize = 10
      for (let i = 0; i < sampleSize; i++) {
        const x = Math.floor(Math.random() * WORLD_CONFIG.GRID_SIZE)
        const y = Math.floor(Math.random() * WORLD_CONFIG.GRID_SIZE)

        world[x][y].update(deltaTime)
      }
    }, 1000)

    return () => clearInterval(updateInterval)
  }, [])

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

      <DebugInfo
        cameraX={cameraX}
        cameraY={cameraY}
        viewportWidth={viewportWidth}
        viewportHeight={viewportHeight}
      />
    </div>
  )
}
