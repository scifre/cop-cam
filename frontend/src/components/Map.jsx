import { MapContainer, TileLayer, Marker, Popup, useMap } from 'react-leaflet'
import { useEffect, useRef, useState } from 'react'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'
import PersonModal from './PersonModal'

// Create custom icon with photo (Google Maps style)
function createPhotoIcon(imageUrl, category, personName) {
  const isCriminal = category === 'B'
  const borderColor = isCriminal ? '#ef4444' : '#3b82f6'
  const pinColor = isCriminal ? '#dc2626' : '#2563eb'
  const initial = personName.charAt(0).toUpperCase()
  const bgColor = isCriminal ? '#ef4444' : '#3b82f6'
  
  // Create placeholder SVG
  const placeholderSvg = `data:image/svg+xml,${encodeURIComponent(`<svg xmlns="http://www.w3.org/2000/svg" width="60" height="60"><rect fill="${bgColor}" width="60" height="60"/><text x="50%" y="50%" font-size="24" fill="white" text-anchor="middle" dominant-baseline="middle">${initial}</text></svg>`)}`
  
  const pinClass = isCriminal ? '' : 'photo-marker-police-pin'
  const circleClass = isCriminal ? 'photo-marker-criminal' : 'photo-marker-police'
  
  const html = `
    <div class="photo-marker-wrapper">
      <div class="photo-marker-pin ${pinClass}"></div>
      <div class="photo-marker-circle ${circleClass}">
        <img src="${imageUrl}" alt="${personName}" class="photo-marker-image" 
             onerror="this.onerror=null; this.src='${placeholderSvg}';" />
      </div>
    </div>
  `
  
  return L.divIcon({
    className: `photo-marker photo-marker-${category.toLowerCase()}`,
    html: html,
    iconSize: [60, 80],
    iconAnchor: [30, 80],
    popupAnchor: [0, -80]
  })
}

// Camera location marker
function createCameraIcon(hasCriminal) {
  const activeClass = hasCriminal ? 'camera-marker-active' : ''
  const html = `
    <div class="camera-marker-wrapper">
      <div class="camera-marker-pin ${activeClass}"></div>
      <div class="camera-marker-circle ${activeClass}">
        📹
      </div>
    </div>
  `
  
  return L.divIcon({
    className: 'camera-marker',
    html: html,
    iconSize: [45, 65],
    iconAnchor: [22, 65],
    popupAnchor: [0, -65]
  })
}

function AutoZoom({ dets }) {
  const map = useMap()
  const hasZoomed = useRef(false)
  
  useEffect(() => {
    // Only auto-zoom on first detection, then let user control the map
    if (dets.length > 0 && !hasZoomed.current) {
      const bounds = dets.map(d => [d.coords.lat, d.coords.lng])
      if (bounds.length > 0) {
        map.fitBounds(bounds, { padding: [50, 50], maxZoom: 15 })
        hasZoomed.current = true
      }
    }
  }, [dets.length, map])
  
  return null
}

function Map({ dets }) {
  const center = [21.13, 81.77]
  const [selectedPerson, setSelectedPerson] = useState(null)
  const [cameras, setCameras] = useState([])
  const BACKEND_URL = import.meta.env.VITE_BACKEND_URL || 'http://localhost:8001'
  
  // Fetch cameras on mount
  useEffect(() => {
    fetch(`${BACKEND_URL}/cameras`)
      .then(r => r.json())
      .then(data => setCameras(data.cameras || []))
      .catch(err => console.error('Failed to fetch cameras:', err))
  }, [BACKEND_URL])
  
  // Track which cameras have detections (especially criminals)
  const cameraDetections = {}
  dets.filter(d => d.detected).forEach(d => {
    const camId = d.camera_id
    if (!cameraDetections[camId]) {
      cameraDetections[camId] = { hasCriminal: false, hasPolice: false }
    }
    if (d.category === 'B') {
      cameraDetections[camId].hasCriminal = true
    } else {
      cameraDetections[camId].hasPolice = true
    }
  })
  
  return (
    <div className="map-container">
      <MapContainer 
        center={center} 
        zoom={13} 
        style={{ height: '100%', width: '100%' }}
        scrollWheelZoom={true}
        dragging={true}
        touchZoom={true}
        doubleClickZoom={true}
        zoomControl={true}
      >
        <TileLayer
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        />
        <AutoZoom dets={dets} />
        
        {/* Camera location markers */}
        {cameras.map((cam, idx) => {
          const hasCriminal = cameraDetections[cam.id]?.hasCriminal || false
          return (
            <Marker
              key={`cam-${idx}`}
              position={[cam.lat, cam.lng]}
              icon={createCameraIcon(hasCriminal)}
            >
              <Popup>
                <div className="camera-popup">
                  <h3>{cam.name || cam.id}</h3>
                  <p>Camera: {cam.id}</p>
                  {hasCriminal && (
                    <p className="camera-alert">⚠️ Criminal detected here</p>
                  )}
                </div>
              </Popup>
            </Marker>
          )
        })}
        
        {/* Person detection markers with photos */}
        {dets.filter(d => d.detected).map((d, i) => {
          const personName = d.person_name || d.person_id || 'Unknown'
          const personImage = d.person_image || `/api/face-images/${d.person_id || 'default'}`
          const fullImageUrl = personImage.startsWith('http') 
            ? personImage 
            : `${BACKEND_URL}${personImage}`
          
          // Create placeholder if no image
          const placeholderUrl = `data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='60' height='60'%3E%3Crect fill='${d.category === 'B' ? '%23ef4444' : '%233b82f6'}' width='60' height='60'/%3E%3Ctext x='50%25' y='50%25' font-size='24' fill='white' text-anchor='middle' dominant-baseline='middle'%3E${encodeURIComponent(personName.charAt(0))}%3C/text%3E%3C/svg%3E`
          
          return (
            <Marker 
              key={i} 
              position={[d.coords.lat, d.coords.lng]}
              icon={createPhotoIcon(fullImageUrl, d.category, personName)}
            >
              <Popup>
                <div className="popup" onClick={() => setSelectedPerson(d)}>
                  {d.person_id && (
                    <div className="popup-image-container">
                      <img 
                        src={fullImageUrl}
                        alt={personName}
                        className="popup-face-image"
                        onError={(e) => {
                          e.target.src = placeholderUrl
                        }}
                      />
                    </div>
                  )}
                  <h3>{personName}</h3>
                  <p className={d.category === 'A' ? 'cat-a' : 'cat-b'}>
                    {d.category === 'A' ? '👮 Police' : '⚠️ Criminal'}
                  </p>
                  {d.crime && d.category === 'B' && (
                    <p className="popup-crime">Crime: {d.crime}</p>
                  )}
                  <p className="time">{new Date(d.timestamp).toLocaleString()}</p>
                  <p className="popup-click-hint">Click for details →</p>
                </div>
              </Popup>
            </Marker>
          )
        })}
      </MapContainer>
      
      {selectedPerson && (
        <PersonModal 
          person={selectedPerson} 
          onClose={() => setSelectedPerson(null)} 
        />
      )}
    </div>
  )
}

export default Map