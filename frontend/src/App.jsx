import { useState, useEffect, useRef, useCallback } from 'react'
import CameraGrid from './components/CameraGrid'
import CameraMap from './components/CameraMap'
import CameraList from './components/CameraList'
import Sidebar from './components/Sidebar'
import VideoModal from './components/VideoModal'
import { loadDetections, loadCameras } from './utils/loadDetections'
import { getDetectionsInRange } from './utils/detectionTrigger'

function App() {
  const [detections, setDetections] = useState([])
  const [cameras, setCameras] = useState({})
  const [currentTime, setCurrentTime] = useState(0)
  const [isPlaying, setIsPlaying] = useState(false)
  const [recentDetections, setRecentDetections] = useState([])
  const [alertCameras, setAlertCameras] = useState(new Set())
  const [videosReady, setVideosReady] = useState(false)
  const [selectedCamera, setSelectedCamera] = useState(null)
  const [viewMode, setViewMode] = useState('grid') // 'grid' or 'map'
  const [modalCamera, setModalCamera] = useState(null) // Camera ID for video modal
  
  const masterVideoRef = useRef(null)
  const allVideoRefs = useRef([])
  
  // Map camera IDs to video filenames
  const videoNameMap = {
    "CAM_01": "cp_lab1",
    "CAM_02": "cp_lab2", 
    "CAM_03": "vlsi",
    "CAM_04": "iot",
    "CAM_05": "lift",
    "CAM_06": "loby"
  }

  // Load data on mount
  useEffect(() => {
    async function loadData() {
      const [dets, cams] = await Promise.all([
        loadDetections(),
        loadCameras()
      ])
      console.log('Loaded cameras:', Object.keys(cams).length, cams)
      console.log('Loaded detections:', dets.length)
      setDetections(dets)
      setCameras(cams)
      
      // Enable buttons after a short delay (videos might still be loading)
      setTimeout(() => {
        setVideosReady(true)
      }, 1000)
    }
    loadData()
  }, [])

  // Track last processed time for detection triggering
  const lastProcessedTimeRef = useRef(0)

  // Initialize detection triggering
  useEffect(() => {
    if (!masterVideoRef.current || detections.length === 0) return

    const video = masterVideoRef.current

    const handleTimeUpdate = () => {
      const currentTime = video.currentTime
      const lastTime = lastProcessedTimeRef.current
      
      // Find detections in this time range, excluding unknown
      const allNewDetections = getDetectionsInRange(detections, lastTime, currentTime)
      const newDetections = allNewDetections.filter(det => {
        const personId = (det.person_id || '').toLowerCase()
        return personId !== 'unknown' && personId !== ''
      })
      
      if (newDetections.length > 0) {
        // Add to recent detections (only known persons)
        setRecentDetections(prev => [...newDetections, ...prev])
        
        // Trigger alerts for cameras with detections
        newDetections.forEach(det => {
          if (det.camera_id) {
            setAlertCameras(prev => new Set(prev).add(det.camera_id))
            // Remove alert after 2 seconds
            setTimeout(() => {
              setAlertCameras(prev => {
                const updated = new Set(prev)
                updated.delete(det.camera_id)
                return updated
              })
            }, 2000)
          }
        })
      }
      
      lastProcessedTimeRef.current = currentTime
      setCurrentTime(currentTime)
    }

    video.addEventListener('timeupdate', handleTimeUpdate)

    return () => {
      video.removeEventListener('timeupdate', handleTimeUpdate)
    }
  }, [detections])

  // Handle play/pause - sync all videos
  const handlePlayPause = useCallback(async () => {
    // Try to find master video if ref isn't set
    if (!masterVideoRef.current) {
      // Look for first video in all refs
      const firstVideo = allVideoRefs.current.find(v => v && v.tagName === 'VIDEO')
      if (firstVideo) {
        masterVideoRef.current = firstVideo
        console.log('Found master video from all refs')
      } else {
        console.warn('Master video not ready, waiting...')
        // Wait a bit and try again
        setTimeout(() => {
          if (masterVideoRef.current) {
            handlePlayPause()
          }
        }, 500)
        return
      }
    }

    try {
      if (isPlaying) {
        // Pause all videos
        masterVideoRef.current.pause()
        allVideoRefs.current.forEach(video => {
          if (video && video !== masterVideoRef.current) {
            video.pause()
          }
        })
        setIsPlaying(false)
      } else {
        // Play all videos
        await masterVideoRef.current.play()
        allVideoRefs.current.forEach(video => {
          if (video && video !== masterVideoRef.current) {
            video.play().catch(err => console.log('Video play error:', err))
          }
        })
        setIsPlaying(true)
      }
    } catch (error) {
      console.error('Play/pause error:', error)
    }
  }, [isPlaying])

  const handleReset = useCallback(() => {
    // Try to find master video if ref isn't set
    if (!masterVideoRef.current) {
      const firstVideo = allVideoRefs.current.find(v => v && v.tagName === 'VIDEO')
      if (firstVideo) {
        masterVideoRef.current = firstVideo
      } else {
        return
      }
    }
    
    // Reset all videos
    masterVideoRef.current.currentTime = 0
    allVideoRefs.current.forEach(video => {
      if (video) {
        video.currentTime = 0
      }
    })
    
    lastProcessedTimeRef.current = 0
    setCurrentTime(0)
    setRecentDetections([])
    setAlertCameras(new Set())
    setIsPlaying(false)
  }, [])

  const setMasterVideoRef = useCallback((videoElement) => {
    if (videoElement) {
      masterVideoRef.current = videoElement
      
      // Set up video event listeners
      const handlePlay = () => setIsPlaying(true)
      const handlePause = () => setIsPlaying(false)
      const handleLoadedMetadata = () => {
        console.log('Master video ready, duration:', videoElement.duration)
        setVideosReady(true)
      }
      
      videoElement.addEventListener('play', handlePlay)
      videoElement.addEventListener('pause', handlePause)
      videoElement.addEventListener('loadedmetadata', handleLoadedMetadata)
      
      // Check if already loaded
      if (videoElement.readyState >= 2) {
        setVideosReady(true)
      }
    }
  }, [])
  
  const registerVideoRef = useCallback((videoElement) => {
    if (videoElement && !allVideoRefs.current.includes(videoElement)) {
      allVideoRefs.current.push(videoElement)
      console.log('Registered video ref, total:', allVideoRefs.current.length)
    }
  }, [])
  
  const handleCameraSelect = useCallback((cameraId) => {
    if (selectedCamera === cameraId) {
      // Deselect if clicking the same camera
      setSelectedCamera(null)
    } else {
      setSelectedCamera(cameraId)
      setViewMode('grid') // Switch to grid view when camera is selected
    }
  }, [selectedCamera])
  
  const handleCameraClick = useCallback((cameraId) => {
    // Open video modal when clicking camera on map
    setModalCamera(cameraId)
  }, [])
  
  const handleClearSelection = useCallback(() => {
    setSelectedCamera(null)
  }, [])
  
  const handleCloseModal = useCallback(() => {
    setModalCamera(null)
  }, [])
  
  const getVideoSrc = useCallback((cameraId) => {
    const baseName = videoNameMap[cameraId]
    return baseName ? `/videos/${baseName}_h264.mp4` : null
  }, [])

  return (
    <div className="app">
      <div className="header">
        <h1>Live Detection Monitor</h1>
        <div className="header-right">
          <div className="header-controls">
            <button 
              className="control-button-small" 
              onClick={handlePlayPause}
              disabled={!videosReady}
            >
              {isPlaying ? '⏸' : '▶'}
            </button>
            <button 
              className="control-button-small" 
              onClick={handleReset}
              disabled={!videosReady}
            >
              ⏮
            </button>
            <div className="time-display-small">
              {Math.floor(currentTime / 60)}:{(Math.floor(currentTime % 60)).toString().padStart(2, '0')}
            </div>
          </div>
          <div className="view-toggle">
            <button 
              className={`view-button ${viewMode === 'grid' ? 'active' : ''}`}
              onClick={() => setViewMode('grid')}
            >
              📹 Grid
            </button>
            <button 
              className={`view-button ${viewMode === 'map' ? 'active' : ''}`}
              onClick={() => setViewMode('map')}
            >
              🗺️ Map
            </button>
          </div>
        </div>
      </div>
      
      {/* Camera List */}
      <CameraList
        cameras={cameras}
        selectedCamera={selectedCamera}
        onCameraSelect={handleCameraSelect}
        alertCameras={alertCameras}
        currentTime={currentTime}
        masterVideoRef={masterVideoRef}
        isPlaying={isPlaying}
      />

      <div className="container">
        {viewMode === 'grid' ? (
          <CameraGrid
            cameras={cameras}
            detections={detections}
            currentTime={currentTime}
            alertCameras={alertCameras}
            selectedCamera={selectedCamera}
            onClearSelection={handleClearSelection}
            onMasterVideoRef={setMasterVideoRef}
            onVideoRef={registerVideoRef}
          />
        ) : (
          <CameraMap
            cameras={cameras}
            selectedCamera={selectedCamera}
            onCameraSelect={handleCameraSelect}
            onCameraClick={handleCameraClick}
            alertCameras={alertCameras}
          />
        )}
        <Sidebar 
          recentDetections={recentDetections}
          totalDetections={detections.length}
          allDetections={detections}
          currentTime={currentTime}
          alertCameras={alertCameras}
        />
      </div>
      
      {/* Video Modal */}
      {modalCamera && cameras[modalCamera] && (
        <VideoModal
          cameraId={modalCamera}
          cameraName={cameras[modalCamera].name}
          videoSrc={getVideoSrc(modalCamera)}
          isOpen={!!modalCamera}
          onClose={handleCloseModal}
          currentTime={currentTime}
          isPlaying={isPlaying}
          onPlayPause={handlePlayPause}
          onReset={handleReset}
        />
      )}
    </div>
  )
}

export default App

