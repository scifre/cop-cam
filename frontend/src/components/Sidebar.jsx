function Sidebar({ dets }) {
  const filtered = dets.filter(d => d.detected)
  const BACKEND_URL = import.meta.env.VITE_BACKEND_URL || 'http://localhost:8001'
  
  return (
    <div className="sidebar">
      <h2>Recent Detections</h2>
      <div className="count">Total: {filtered.length}</div>
      <div className="list">
        {filtered.length === 0 ? (
          <div className="empty">No detections yet</div>
        ) : (
          filtered.map((d, i) => {
            const personName = d.person_name || d.person_id || 'Unknown'
            const personImage = d.person_image || `/api/face-images/${d.person_id || 'default'}`
            const crime = d.crime || (d.category === 'B' ? 'Criminal Activity' : 'N/A')
            
            return (
              <div key={i} className={`item ${d.category === 'B' ? 'alert' : ''}`}>
                <div className="item-content">
                  {d.person_id && (
                    <div className="item-image-container">
                      <img 
                        src={`${BACKEND_URL}${personImage}`}
                        alt={personName}
                        className="item-face-image"
                        onError={(e) => {
                          e.target.src = `data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='100' height='100'%3E%3Crect fill='%234f46e5' width='100' height='100'/%3E%3Ctext x='50%25' y='50%25' font-size='40' fill='white' text-anchor='middle' dominant-baseline='middle'%3E${personName.charAt(0)}%3C/text%3E%3C/svg%3E`
                        }}
                      />
                    </div>
                  )}
                  <div className="item-details">
                    <div className="item-header">
                      <span className={`cat ${d.category === 'A' ? 'cat-a' : 'cat-b'}`}>
                        {d.category === 'A' ? '👮 Police' : '⚠️ Criminal'}
                      </span>
                      <span className="cam">{d.camera_id}</span>
                    </div>
                    {d.person_id && (
                      <>
                        <div className="item-name">{personName}</div>
                        {d.category === 'B' && crime !== 'N/A' && (
                          <div className="item-crime">Crime: {crime}</div>
                        )}
                      </>
                    )}
                    <div className="item-time">
                      {new Date(d.timestamp).toLocaleTimeString()}
                    </div>
                    <div className="item-coords">
                      📍 {d.coords.lat.toFixed(4)}, {d.coords.lng.toFixed(4)}
                    </div>
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