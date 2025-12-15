import { MapContainer, TileLayer, Marker, Popup, useMap } from 'react-leaflet'
import { useEffect, useRef, useState } from 'react'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'
import PersonModal from './PersonModal'

const blueIcon = L.divIcon({
  className: 'custom-marker',
  html: '<div class="marker blue-marker"></div>',
  iconSize: [20, 20],
  iconAnchor: [10, 10]
})

const redIcon = L.divIcon({
  className: 'custom-marker',
  html: '<div class="marker red-marker"></div>',
  iconSize: [20, 20],
  iconAnchor: [10, 10]
})

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
  const BACKEND_URL = import.meta.env.VITE_BACKEND_URL || 'http://localhost:8001'
  
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
        {dets.filter(d => d.detected).map((d, i) => {
          const personName = d.person_name || d.person_id || 'Unknown'
          const personImage = d.person_image || `/api/face-images/${d.person_id || 'default'}`
          
          return (
            <Marker 
              key={i} 
              position={[d.coords.lat, d.coords.lng]}
              icon={d.category === 'A' ? blueIcon : redIcon}
            >
              <Popup>
                <div className="popup" onClick={() => setSelectedPerson(d)}>
                  {d.person_id && (
                    <div className="popup-image-container">
                      <img 
                        src={`${BACKEND_URL}${personImage}`}
                        alt={personName}
                        className="popup-face-image"
                        onError={(e) => {
                          e.target.src = `data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='80' height='80'%3E%3Crect fill='%234f46e5' width='80' height='80'/%3E%3Ctext x='50%25' y='50%25' font-size='32' fill='white' text-anchor='middle' dominant-baseline='middle'%3E${personName.charAt(0)}%3C/text%3E%3C/svg%3E`
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