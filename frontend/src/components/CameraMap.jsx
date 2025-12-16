import { MapContainer, TileLayer, Marker, Popup, useMap, Tooltip } from 'react-leaflet'
import { useEffect, useRef } from 'react'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'

// Fix for default marker icons in react-leaflet
delete L.Icon.Default.prototype._getIconUrl
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon-2x.png',
  iconUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon.png',
  shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-shadow.png',
})

// Professional camera markers - blue dots for normal, red for alerts
const createCameraIcon = (isActive = false, hasAlert = false) => {
  const color = hasAlert ? '#ef4444' : (isActive ? '#4f46e5' : '#64748b')
  const size = isActive ? 16 : 12
  const borderSize = isActive ? 3 : 2
  
  return L.divIcon({
    className: 'custom-camera-marker',
    html: `<div class="camera-marker-dot" style="
      width: ${size}px;
      height: ${size}px;
      background: ${color};
      border: ${borderSize}px solid white;
      border-radius: 50%;
      box-shadow: 0 2px 8px rgba(0,0,0,0.3);
    "></div>`,
    iconSize: [size + borderSize * 2, size + borderSize * 2],
    iconAnchor: [(size + borderSize * 2) / 2, (size + borderSize * 2) / 2]
  })
}

function AutoZoom({ cameras }) {
  const map = useMap()
  const hasZoomed = useRef(false)
  
  useEffect(() => {
    if (Object.keys(cameras).length > 0 && !hasZoomed.current) {
      // Convert camera locations to lat/lng
      // Assuming cameras are in a circle, convert to approximate lat/lng
      // Using a base location (you can adjust this)
      const baseLat = 21.13
      const baseLng = 81.77
      const scale = 0.01 // Scale factor for converting normalized coords to lat/lng
      
      const bounds = Object.values(cameras).map(cam => {
        const lat = baseLat + (cam.location.y * scale)
        const lng = baseLng + (cam.location.x * scale)
        return [lat, lng]
      })
      
      if (bounds.length > 0) {
        map.fitBounds(bounds, { padding: [50, 50], maxZoom: 16 })
        hasZoomed.current = true
      }
    }
  }, [Object.keys(cameras).length, map, cameras])
  
  return null
}

function CameraMap({ cameras, selectedCamera, onCameraSelect, alertCameras, onCameraClick }) {
  // Base location (adjust to your actual location)
  const center = [21.13, 81.77]
  const scale = 0.01 // Scale for converting normalized coords
  
  // Convert camera locations to lat/lng
  const getCameraPosition = (camera) => {
    const baseLat = 21.13
    const baseLng = 81.77
    return [
      baseLat + (camera.location.y * scale),
      baseLng + (camera.location.x * scale)
    ]
  }
  
  return (
    <div className="camera-map-container">
      <MapContainer 
        center={center} 
        zoom={14} 
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
        <AutoZoom cameras={cameras} />
        {Object.entries(cameras).map(([cameraId, camera]) => {
          const position = getCameraPosition(camera)
          const isSelected = selectedCamera === cameraId
          const hasAlert = alertCameras.has(cameraId)
          
          return (
            <Marker
              key={cameraId}
              position={position}
              icon={createCameraIcon(isSelected, hasAlert)}
              eventHandlers={{
                click: () => {
                  if (onCameraClick) {
                    onCameraClick(cameraId)
                  } else {
                    onCameraSelect(cameraId)
                  }
                }
              }}
            >
              <Tooltip permanent direction="top" offset={[0, -10]}>
                <span className={`map-camera-label ${hasAlert ? 'alert' : ''} ${isSelected ? 'selected' : ''}`}>
                  {cameraId}
                </span>
              </Tooltip>
              <Popup>
                <div className="camera-popup">
                  <h3>{cameraId}</h3>
                  <p>{camera.name}</p>
                  {hasAlert && <p className="popup-alert">⚠️ Alert Active</p>}
                  <button 
                    className="popup-view-button"
                    onClick={() => {
                      if (onCameraClick) {
                        onCameraClick(cameraId)
                      } else {
                        onCameraSelect(cameraId)
                      }
                    }}
                  >
                    View Video →
                  </button>
                </div>
              </Popup>
            </Marker>
          )
        })}
      </MapContainer>
    </div>
  )
}

export default CameraMap

