import { useRef, useEffect } from 'react'
import CameraPlayer from './CameraPlayer'

function CameraGrid({ cameras, detections, currentTime, alertCameras, selectedCamera, onClearSelection, onMasterVideoRef, onVideoRef }) {
  const masterVideoRef = useRef(null)
  
  useEffect(() => {
    // Check when master video ref becomes available
    const checkRef = () => {
      if (onMasterVideoRef && masterVideoRef.current) {
        const videoElement = masterVideoRef.current
        // Make sure it's actually a video element
        if (videoElement && (videoElement.tagName === 'VIDEO' || videoElement.nodeName === 'VIDEO')) {
          console.log('Setting master video ref:', videoElement)
          onMasterVideoRef(videoElement)
        }
      }
    }
    
    // Check immediately and after delays
    checkRef()
    const timeout1 = setTimeout(checkRef, 100)
    const timeout2 = setTimeout(checkRef, 500)
    const timeout3 = setTimeout(checkRef, 1000)
    
    return () => {
      clearTimeout(timeout1)
      clearTimeout(timeout2)
      clearTimeout(timeout3)
    }
  }, [onMasterVideoRef, cameras])

  const cameraIds = Object.keys(cameras)
  
  // Filter cameras if one is selected, otherwise show all
  const camerasToShow = selectedCamera 
    ? [selectedCamera].filter(id => cameraIds.includes(id))
    : cameraIds
  
  if (cameraIds.length === 0) {
    return (
      <div className="camera-grid">
        <div style={{ padding: '2rem', textAlign: 'center', color: '#64748b' }}>
          <p>Loading cameras...</p>
          <p style={{ fontSize: '0.9rem', marginTop: '0.5rem' }}>
            If this persists, check browser console for errors
          </p>
        </div>
      </div>
    )
  }

  return (
    <div className="camera-grid">
      {selectedCamera && (
        <div className="selected-camera-header">
          <button 
            className="clear-selection-button"
            onClick={onClearSelection}
          >
            ← Show All Cameras
          </button>
          <span>Viewing: {selectedCamera} - {cameras[selectedCamera]?.name}</span>
        </div>
      )}
      <div className="grid-container">
        {camerasToShow.map((camId, index) => {
          const camera = cameras[camId]
          const cameraDetections = detections.filter(d => d.camera_id === camId)
          const isAlert = alertCameras.has(camId)
          const isMaster = index === 0
          const isSelected = selectedCamera === camId

          return (
            <CameraPlayer
              key={camId}
              ref={isMaster ? masterVideoRef : null}
              cameraId={camId}
              cameraName={camera?.name || camId}
              cameras={cameras}
              isMaster={isMaster}
              detections={cameraDetections}
              currentTime={currentTime}
              isAlert={isAlert}
              isSelected={isSelected}
              onVideoRef={onVideoRef}
            />
          )
        })}
      </div>
    </div>
  )
}

export default CameraGrid

