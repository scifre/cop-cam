function Sidebar({ dets }) {
  const filtered = dets.filter(d => d.detected)
  
  return (
    <div className="sidebar">
      <h2>Recent Detections</h2>
      <div className="count">Total: {filtered.length}</div>
      <div className="list">
        {filtered.length === 0 ? (
          <div className="empty">No detections yet</div>
        ) : (
          filtered.map((d, i) => (
            <div key={i} className={`item ${d.category === 'B' ? 'alert' : ''}`}>
              <div className="item-header">
                <span className={`cat ${d.category === 'A' ? 'cat-a' : 'cat-b'}`}>
                  {d.category === 'A' ? '👮 Police' : '⚠️ Criminal'}
                </span>
                <span className="cam">{d.camera_id}</span>
              </div>
              <div className="item-time">
                {new Date(d.timestamp).toLocaleTimeString()}
              </div>
              <div className="item-coords">
                📍 {d.coords.lat.toFixed(4)}, {d.coords.lng.toFixed(4)}
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  )
}

export default Sidebar