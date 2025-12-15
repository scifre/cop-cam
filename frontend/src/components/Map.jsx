import { MapContainer, TileLayer, Marker, Popup, useMap } from 'react-leaflet'
import { useEffect, useRef } from 'react'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'

const blueIcon = L.divIcon({
  className: 'custom-marker',
  html: '<div class="marker blue-marker"></div>',
  iconSize: [20, 20],
  iconAnchor: [10, 10]
})

const redIcon = L.divIcon({
  className: 'custom-marker',
  html: '<div class="marker red-marker pulse"></div>',
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
        {dets.filter(d => d.detected).map((d, i) => (
          <Marker 
            key={i} 
            position={[d.coords.lat, d.coords.lng]}
            icon={d.category === 'A' ? blueIcon : redIcon}
          >
            <Popup>
              <div className="popup">
                <h3>{d.camera_id}</h3>
                <p className={d.category === 'A' ? 'cat-a' : 'cat-b'}>
                  {d.category === 'A' ? '👮 Police' : '⚠️ Criminal'}
                </p>
                <p className="time">{new Date(d.timestamp).toLocaleString()}</p>
              </div>
            </Popup>
          </Marker>
        ))}
      </MapContainer>
    </div>
  )
}

export default Map