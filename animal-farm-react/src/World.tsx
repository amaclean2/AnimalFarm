import { useEffect, useRef } from 'react'
import { WorldRenderer } from './WorldRenderer'
import { useViewport } from './useViewport'
import { useCameraControls } from './useCameraControls'
import { DebugInfo } from './DebugInfo'

export const World = () => {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const rendererRef = useRef<WorldRenderer | null>(null)

  const { viewportWidth, viewportHeight } = useViewport()
  const { cameraX, cameraY } = useCameraControls(viewportWidth, viewportHeight)

  useEffect(() => {
    const canvas = canvasRef.current
    if (canvas) {
      rendererRef.current = new WorldRenderer(canvas)
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
