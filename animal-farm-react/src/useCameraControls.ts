import { useEffect, useState } from 'react'
import { WORLD_CONFIG } from './WorldConfig'

export const useCameraControls = (
  viewportWidth: number,
  viewportHeight: number
) => {
  const [cameraX, setCameraX] = useState(0)
  const [cameraY, setCameraY] = useState(0)

  const keysPressed = new Set<string>()

  useEffect(() => {
    let animationId: number

    const animate = () => {
      let deltaX = 0
      let deltaY = 0

      if (keysPressed.has('ArrowUp')) deltaY -= WORLD_CONFIG.SCROLL_SPEED
      if (keysPressed.has('ArrowDown')) deltaY += WORLD_CONFIG.SCROLL_SPEED
      if (keysPressed.has('ArrowLeft')) deltaX -= WORLD_CONFIG.SCROLL_SPEED
      if (keysPressed.has('ArrowRight')) deltaX += WORLD_CONFIG.SCROLL_SPEED

      if (deltaX !== 0 || deltaY !== 0) {
        setCameraX((prev) =>
          Math.max(
            0,
            Math.min(WORLD_CONFIG.WORLD_SIZE - viewportWidth, prev + deltaX)
          )
        )

        setCameraY((prev) =>
          Math.max(
            0,
            Math.min(WORLD_CONFIG.WORLD_SIZE - viewportHeight, prev + deltaY)
          )
        )
      }

      animationId = requestAnimationFrame(animate)
    }

    animationId = requestAnimationFrame(animate)

    return () => cancelAnimationFrame(animationId)
  }, [viewportWidth, viewportHeight])

  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if (
        ['ArrowUp', 'ArrowDown', 'ArrowLeft', 'ArrowRight'].includes(event.key)
      ) {
        event.preventDefault()
        keysPressed.add(event.key)
      }
    }

    const handleKeyUp = (event: KeyboardEvent) => {
      if (
        ['ArrowUp', 'ArrowDown', 'ArrowLeft', 'ArrowRight'].includes(event.key)
      ) {
        event.preventDefault()
        keysPressed.delete(event.key)
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    window.addEventListener('keyup', handleKeyUp)

    return () => {
      window.removeEventListener('keydown', handleKeyDown)
      window.removeEventListener('keyup', handleKeyUp)
    }
  }, [])

  return { cameraX, cameraY }
}
