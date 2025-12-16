import { useRef, useEffect, useState } from 'react'

function CameraList({ cameras, selectedCamera, onCameraSelect, alertCameras, currentTime, masterVideoRef, isPlaying }) {
  const cameraIds = Object.keys(cameras)
  const videoRefs = useRef({})
  const [isCollapsed, setIsCollapsed] = useState(false)
  
  // Map camera IDs to video filenames
  const videoNameMap = {
    "CAM_01": "cp_lab1",
    "CAM_02": "cp_lab2", 
    "CAM_03": "vlsi",
    "CAM_04": "iot",
    "CAM_05": "lift",
    "CAM_06": "loby"
  }
  
  // Sync all mini videos with master
  useEffect(() => {
    if (masterVideoRef?.current && currentTime !== undefined && !isCollapsed) {
      Object.values(videoRefs.current).forEach(video => {
        if (video && video !== masterVideoRef.current) {
          if (Math.abs(video.currentTime - currentTime) > 0.1) {
            video.currentTime = currentTime
          }
        }
      })
    }
  }, [currentTime, masterVideoRef, isCollapsed])
  
  // Sync play/pause state
  useEffect(() => {
    if (!isCollapsed) {
      Object.values(videoRefs.current).forEach(video => {
        if (video && video !== masterVideoRef.current) {
          if (isPlaying && video.paused) {
            video.play().catch(() => {})
          } else if (!isPlaying && !video.paused) {
            video.pause()
          }
        }
      })
    }
  }, [isPlaying, masterVideoRef, isCollapsed])
  
  return (
    <div className={`camera-list-section ${isCollapsed ? 'collapsed' : ''}`}>
      <div className="camera-list-header" onClick={() => setIsCollapsed(!isCollapsed)}>
        <div className="camera-list-header-left">
          <span className="camera-list-icon">{isCollapsed ? '▶' : '▼'}</span>
          <h3>Camera Overview</h3>
          <span className="camera-list-count">({cameraIds.length} cameras)</span>
        </div>
        <div className="camera-list-header-right">
          {Array.from(alertCameras).length > 0 && (
            <span className="camera-list-alert-indicator">
              ⚠️ {Array.from(alertCameras).length} Active
            </span>
          )}
        </div>
      </div>
      
      {!isCollapsed && (
        <div className="camera-list-content">
          <div className="camera-list-grid">
            {cameraIds.map(cameraId => {
              const camera = cameras[cameraId]
              const isSelected = selectedCamera === cameraId
              const hasAlert = alertCameras.has(cameraId)
              const baseName = videoNameMap[cameraId]
              const videoSrc = baseName ? `/videos/${baseName}_h264.mp4` : null
              
              return (
                <div
                  key={cameraId}
                  className={`camera-list-item ${isSelected ? 'selected' : ''} ${hasAlert ? 'alert' : ''}`}
                  onClick={() => onCameraSelect(cameraId)}
                >
                  <div className="camera-list-video">
                    {videoSrc ? (
                      <video
                        ref={(el) => {
                          if (el) videoRefs.current[cameraId] = el
                        }}
                        src={videoSrc}
                        muted
                        playsInline
                        preload="auto"
                        style={{ width: '100%', height: '100%', objectFit: 'cover' }}
                      />
                    ) : (
                      <div className="camera-list-placeholder">📹</div>
                    )}
                    <div className="camera-list-overlay">
                      <div className="camera-list-id">{cameraId}</div>
                    </div>
                    {hasAlert && <div className="camera-list-alert-indicator-small">⚠️</div>}
                    {isSelected && <div className="camera-list-check">✓</div>}
                  </div>
                  <div className="camera-list-info">
                    <div className="camera-list-name">{camera.name}</div>
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      )}
    </div>
  )
}

export default CameraList

