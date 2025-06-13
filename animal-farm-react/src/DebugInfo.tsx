interface DebugInfoProps {
  cameraX: number
  cameraY: number
  viewportWidth: number
  viewportHeight: number
}

export const DebugInfo = ({
  cameraX,
  cameraY,
  viewportWidth,
  viewportHeight
}: DebugInfoProps) => (
  <div
    style={{
      position: 'absolute',
      top: 10,
      left: 10,
      padding: '5px',
      borderRadius: '5px',
      backgroundColor: 'rgba(0, 0, 0, 0.5)',
      color: '#FFF',
      fontSize: '14px',
      fontFamily: 'monospace'
    }}
  >
    Camera: ({cameraX}, {cameraY})<br />
    Viewport: {viewportWidth} x {viewportHeight}
  </div>
)
