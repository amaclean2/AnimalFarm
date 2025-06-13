import { useEffect, useState } from 'react'

export const useViewport = () => {
  const [viewportWidth, setViewportWidth] = useState(window.innerWidth)
  const [viewportHeight, setViewportHeight] = useState(window.innerHeight)

  useEffect(() => {
    const handleResize = () => {
      setViewportWidth(window.innerWidth)
      setViewportHeight(window.innerHeight)
    }

    window.addEventListener('resize', handleResize)

    return () => window.removeEventListener('resize', handleResize)
  }, [])

  return { viewportWidth, viewportHeight }
}
