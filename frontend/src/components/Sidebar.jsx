import { useEffect, useState } from 'react'
import { formatTime } from '../utils/detectionTrigger'

// Map person IDs to photo paths
const personPhotos = {
  'ayush': '/new_photos/ayush/ayush-5.jpg',
  'kanika': '/new_photos/kanika/kanika-5.jpg',

}

function Sidebar({ recentDetections, totalDetections, allDetections, currentTime, alertCameras }) {
  const [displayedDetections, setDisplayedDetections] = useState([])
  const [showMode, setShowMode] = useState('recent') // 'recent' or 'all'
  const [alertedPersons, setAlertedPersons] = useState(new Set())

  useEffect(() => {
    // Filter out unknown detections
    const filterUnknown = (dets) => {
      return dets.filter(det => {
        const personId = (det.person_id || '').toLowerCase()
        return personId !== 'unknown' && personId !== ''
      })
    }
    
    if (showMode === 'recent') {
      // Show most recent triggered detections (last 20), excluding unknown
      const recent = filterUnknown(recentDetections)
        .sort((a, b) => {
          const timeA = typeof a.timestamp === 'number' ? a.timestamp : parseFloat(a.timestamp)
          const timeB = typeof b.timestamp === 'number' ? b.timestamp : parseFloat(b.timestamp)
          return timeB - timeA
        })
        .slice(0, 20)
      
      setDisplayedDetections(recent)
    } else {
      // Show all detections, sorted by timestamp, excluding unknown
      const all = filterUnknown(allDetections || [])
        .sort((a, b) => {
          const timeA = typeof a.timestamp === 'number' ? a.timestamp : parseFloat(a.timestamp)
          const timeB = typeof b.timestamp === 'number' ? b.timestamp : parseFloat(b.timestamp)
          return timeB - timeA
        })
        .slice(0, 50) // Limit to 50 for performance
      
      setDisplayedDetections(all)
    }
  }, [recentDetections, allDetections, showMode])
  
  // Track alerted persons (excluding unknown)
  useEffect(() => {
    const persons = new Set()
    recentDetections.forEach(det => {
      const personId = (det.person_id || '').toLowerCase()
      if (personId && personId !== 'unknown' && personId !== '') {
        persons.add(personId)
      }
    })
    setAlertedPersons(persons)
  }, [recentDetections])

  // Get unique alerted persons with photos
  const alertedPersonsList = Array.from(alertedPersons).filter(p => personPhotos[p])
  
  // Calculate known detections count
  const knownDetectionsCount = (allDetections || []).filter(det => {
    const personId = (det.person_id || '').toLowerCase()
    return personId !== 'unknown' && personId !== ''
  }).length
  
  return (
    <div className="sidebar">
      <h2>Detections</h2>
      <div className="count">Total: {knownDetectionsCount} (Known Persons)</div>
      
      {/* Alerted Persons Section */}
      {alertedPersonsList.length > 0 && (
        <div className="alerted-persons-section">
          <h3 className="alerted-persons-title">⚠️ Active Alerts</h3>
          <div className="alerted-persons-list">
            {alertedPersonsList.map(personId => {
              const photoPath = personPhotos[personId]
              return (
                <div key={personId} className="alerted-person-card">
                  <img 
                    src={photoPath} 
                    alt={personId}
                    className="alerted-person-photo"
                    onError={(e) => {
                      e.target.style.display = 'none'
                    }}
                  />
                  <div className="alerted-person-name">
                    {personId.charAt(0).toUpperCase() + personId.slice(1)}
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      )}
      
      <div className="sidebar-controls">
        <button 
          className={`sidebar-button ${showMode === 'recent' ? 'active' : ''}`}
          onClick={() => setShowMode('recent')}
        >
          Recent ({displayedDetections.length})
        </button>
        <button 
          className={`sidebar-button ${showMode === 'all' ? 'active' : ''}`}
          onClick={() => setShowMode('all')}
        >
          All ({knownDetectionsCount})
        </button>
      </div>
      {currentTime > 0 && (
        <div className="current-time-indicator">
          Video Time: {formatTime(currentTime)}
        </div>
      )}
      <div className="list">
        {displayedDetections.length === 0 ? (
          <div className="empty">
            {showMode === 'recent' 
              ? 'No detections triggered yet. Play video to see detections.'
              : 'No detections found.'}
          </div>
        ) : (
          displayedDetections.map((det, i) => {
            const personId = det.person_id || 'unknown'
            const personIdLower = personId.toLowerCase()
            const cameraId = det.camera_id || 'N/A'
            const timestamp = typeof det.timestamp === 'number' ? det.timestamp : parseFloat(det.timestamp)
            const isUnknown = personIdLower === 'unknown'
            const isAlert = !isUnknown
            const isPast = currentTime >= timestamp
            const personPhoto = personPhotos[personIdLower]

            return (
              <div key={i} className={`item ${isAlert ? 'alert' : ''} ${isPast ? 'past' : ''}`}>
                <div className="item-content">
                  {personPhoto && (
                    <div className="item-image-container">
                      <img 
                        src={personPhoto} 
                        alt={personId}
                        className="item-face-image"
                        onError={(e) => {
                          e.target.style.display = 'none'
                        }}
                      />
                    </div>
                  )}
                  <div className="item-details">
                    <div className="item-header">
                      <span className={`cat ${isAlert ? 'cat-a' : 'cat-b'}`}>
                        {isAlert ? '👮 Known' : '⚠️ Unknown'}
                      </span>
                      <span className="cam">{cameraId}</span>
                    </div>
                    <div className="item-name">{personId}</div>
                    <div className="item-time">
                      {formatTime(timestamp)}
                      {isPast && <span className="time-indicator">✓</span>}
                    </div>
                    {det.confidence && (
                      <div className="item-coords">
                        Confidence: {(det.confidence * 100).toFixed(1)}%
                      </div>
                    )}
                  </div>
                </div>
              </div>
            )
          })
        )}
      </div>
    </div>
  )
}

export default Sidebar

