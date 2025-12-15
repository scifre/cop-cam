import { useState, useEffect } from 'react'
import Map from './components/Map'
import Sidebar from './components/Sidebar'

// Get backend URL from environment variable
// Vite exposes env variables with VITE_ prefix
const BACKEND_URL = import.meta.env.VITE_BACKEND_URL || 'http://localhost:8000'
const WS_URL = import.meta.env.VITE_WS_URL || 'ws://localhost:8000'

// Log which backend is being used
console.log(`🔗 Connecting to backend: ${BACKEND_URL}`)
console.log(`🔌 WebSocket URL: ${WS_URL}`)

function App() {
  const [dets, setDets] = useState([])
  const [ws, setWs] = useState(null)

  useEffect(() => {
    fetch(`${BACKEND_URL}/get-detections`)
      .then(r => r.json())
      .then(d => setDets(d.detections))

    const socket = new WebSocket(`${WS_URL}/ws/detections`)
    
    socket.onopen = () => console.log('WS Connected')
    
    socket.onmessage = (e) => {
      const data = JSON.parse(e.data)
      setDets(prev => [data, ...prev])
    }
    
    socket.onerror = (e) => console.error('WS Error:', e)
    
    setWs(socket)
    
    return () => socket.close()
  }, [])

  return (
    <div className="app">
      <div className="header">
        <h1>🎯 Live Detection Monitor</h1>
        <div className="legend">
          <span className="badge blue">Police</span>
          <span className="badge red">Criminal</span>
        </div>
      </div>
      <div className="container">
        <Map dets={dets} />
        <Sidebar dets={dets} />
      </div>
    </div>
  )
}

export default App