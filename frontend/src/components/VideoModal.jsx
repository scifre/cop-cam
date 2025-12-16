import { useEffect, useRef } from 'react'

function VideoModal({ cameraId, cameraName, videoSrc, isOpen, onClose, currentTime, isPlaying, onPlayPause, onReset }) {
  const videoRef = useRef(null)
  
  useEffect(() => {
    if (isOpen && videoRef.current && currentTime !== undefined) {
      // Sync video time
      if (Math.abs(videoRef.current.currentTime - currentTime) > 0.1) {
        videoRef.current.currentTime = currentTime
      }
    }
  }, [isOpen, currentTime])
  
  useEffect(() => {
    if (isOpen && videoRef.current) {
      // Sync play/pause
      if (isPlaying && videoRef.current.paused) {
        videoRef.current.play().catch(() => {})
      } else if (!isPlaying && !videoRef.current.paused) {
        videoRef.current.pause()
      }
    }
  }, [isOpen, isPlaying])
  
  if (!isOpen) return null
  
  return (
    <div className="video-modal-overlay" onClick={onClose}>
      <div className="video-modal-content" onClick={(e) => e.stopPropagation()}>
        <div className="video-modal-header">
          <h3>{cameraId} - {cameraName}</h3>
          <button className="video-modal-close" onClick={onClose}>×</button>
        </div>
        <div className="video-modal-video">
          <video
            ref={videoRef}
            src={videoSrc}
            muted
            playsInline
            controls
            style={{ width: '100%', height: 'auto', maxHeight: '70vh' }}
          />
        </div>
        <div className="video-modal-controls">
          <button className="control-button" onClick={onPlayPause}>
            {isPlaying ? '⏸ Pause' : '▶ Play'}
          </button>
          <button className="control-button" onClick={onReset}>
            ⏮ Reset
          </button>
        </div>
      </div>
    </div>
  )
}

export default VideoModal

