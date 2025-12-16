import { useRef, useEffect, useImperativeHandle, forwardRef, useState } from 'react'

const CameraPlayer = forwardRef(({ cameraId, cameraName, cameras, isMaster, detections, currentTime, isAlert, isSelected, onVideoRef }, ref) => {
  const videoRef = useRef(null)
  const [videoError, setVideoError] = useState(false)
  const [videoSrc, setVideoSrc] = useState(null)
  
  // Register video ref with parent
  useEffect(() => {
    if (videoRef.current && onVideoRef) {
      onVideoRef(videoRef.current)
    }
  }, [onVideoRef, videoSrc])

  // Map camera IDs to video filenames (try H.264 versions first)
  const videoNameMap = {
    "CAM_01": "cp_lab1",
    "CAM_02": "cp_lab2", 
    "CAM_03": "vlsi",
    "CAM_04": "iot",
    "CAM_05": "lift",
    "CAM_06": "loby"
  }
  
  // Set initial video source - try H.264 version first, fallback to original
  useEffect(() => {
    const baseName = videoNameMap[cameraId]
    if (baseName) {
      // Try H.264 version first
      setVideoSrc(`/videos/${baseName}_h264.mp4`)
      console.log(`[${cameraId}] Loading video: /videos/${baseName}_h264.mp4`)
    } else {
      setVideoSrc(`/videos/${cameraId}.mp4`)
      console.log(`[${cameraId}] Loading video: /videos/${cameraId}.mp4`)
    }
  }, [cameraId])

  // Expose video ref to parent if master
  useImperativeHandle(ref, () => videoRef.current, [])
  
  // Notify parent when video element is ready (for master)
  useEffect(() => {
    if (isMaster && videoRef.current && ref) {
      // Update ref when video is ready
      if (typeof ref === 'function') {
        ref(videoRef.current)
      } else if (ref && 'current' in ref) {
        ref.current = videoRef.current
      }
    }
  }, [isMaster, videoSrc, videoRef.current])

  // Sync video time to master
  useEffect(() => {
    if (!isMaster && videoRef.current && currentTime !== undefined) {
      const video = videoRef.current
      // Sync time if difference is significant
      if (Math.abs(video.currentTime - currentTime) > 0.1) {
        video.currentTime = currentTime
      }
    }
  }, [currentTime, isMaster])
  
  // Sync will be handled by App.jsx via play/pause calls

  const handleVideoError = (e) => {
    const video = e.target
    if (!video) return
    
    const currentSrc = video.src || video.currentSrc || ''
    const error = video.error
    
    // Only handle real errors (error.code !== 0 means no error)
    // error.code values: 0=no error, 1=aborted, 2=network, 3=decode, 4=not supported
    if (error && error.code !== 0) {
      console.error(`[${cameraId}] Video error (code ${error.code}):`, currentSrc, error.message)
      
      // Try fallback to original name if H.264 version failed
      const baseName = videoNameMap[cameraId]
      if (baseName && currentSrc.includes('_h264')) {
        // Try original name
        console.log(`[${cameraId}] Trying fallback to original: /videos/${baseName}.mp4`)
        setTimeout(() => {
          setVideoSrc(`/videos/${baseName}.mp4`)
          setVideoError(false)
        }, 100)
        return
      } else if (baseName && currentSrc.includes(baseName) && !currentSrc.includes('CAM_')) {
        // Try CAM_XX format
        const fallback = `/videos/${cameraId}.mp4`
        console.log(`[${cameraId}] Trying fallback: ${fallback}`)
        setTimeout(() => {
          setVideoSrc(fallback)
          setVideoError(false)
        }, 100)
        return
      }
      
      setVideoError(true)
    }
    // If error.code === 0 or error is null, it's not a real error - ignore
  }
  
  const handleVideoLoaded = () => {
    console.log(`[${cameraId}] Video loaded successfully:`, videoRef.current?.src)
    setVideoError(false)
  }
  
  const handleVideoCanPlay = () => {
    console.log(`[${cameraId}] Video can play, duration:`, videoRef.current?.duration)
    setVideoError(false)
    
    // Notify parent that master video is ready
    if (isMaster && videoRef.current && ref) {
      if (typeof ref === 'function') {
        ref(videoRef.current)
      } else if (ref && 'current' in ref) {
        ref.current = videoRef.current
      }
    }
  }

  if (!videoSrc) {
    return (
      <div className="camera-player-wrapper">
        <div className="camera-label">{cameraId}</div>
        <div style={{ padding: '2rem', textAlign: 'center', color: '#64748b' }}>
          Loading video...
        </div>
      </div>
    )
  }

  return (
    <div className={`camera-player-wrapper ${isAlert ? 'alert' : ''} ${isSelected ? 'selected' : ''}`}>
      <div className="camera-label">{cameraId}</div>
      {videoError ? (
        <div style={{ 
          padding: '2rem', 
          textAlign: 'center', 
          color: '#ef4444', 
          background: '#fee',
          borderRadius: '4px'
        }}>
          Video not found: {videoNameMap[cameraId] ? `${videoNameMap[cameraId]}_h264.mp4` : `${cameraId}.mp4`}
        </div>
      ) : (
        <video
          ref={videoRef}
          src={videoSrc}
          muted
          playsInline
          preload="auto"
          controls={false}
          style={{ width: '100%', height: 'auto', display: 'block' }}
          onError={handleVideoError}
          onLoadedData={handleVideoLoaded}
          onCanPlay={handleVideoCanPlay}
          onLoadedMetadata={() => {
            console.log(`[${cameraId}] Video metadata loaded, ready:`, videoRef.current?.readyState)
          }}
        />
      )}
    </div>
  )
})

CameraPlayer.displayName = 'CameraPlayer'

export default CameraPlayer

