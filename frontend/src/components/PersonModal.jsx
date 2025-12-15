import { useState } from 'react'

function PersonModal({ person, onClose }) {
  if (!person) return null
  
  const BACKEND_URL = import.meta.env.VITE_BACKEND_URL || 'http://localhost:8001'
  const personImage = person.person_image || `/api/face-images/${person.person_id || 'default'}`
  const personName = person.person_name || person.person_id || 'Unknown'
  const crime = person.crime || (person.category === 'B' ? 'Criminal Activity' : 'N/A')
  
  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <button className="modal-close" onClick={onClose}>×</button>
        
        <div className="modal-header">
          <div className="modal-image-container">
            <img 
              src={`${BACKEND_URL}${personImage}`}
              alt={personName}
              className="modal-face-image"
              onError={(e) => {
                e.target.src = `data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='200' height='200'%3E%3Crect fill='%234f46e5' width='200' height='200'/%3E%3Ctext x='50%25' y='50%25' font-size='80' fill='white' text-anchor='middle' dominant-baseline='middle'%3E${personName.charAt(0)}%3C/text%3E%3C/svg%3E`
              }}
            />
          </div>
          <div className="modal-title-section">
            <h2 className="modal-name">{personName}</h2>
            <span className={`modal-category ${person.category === 'A' ? 'cat-a' : 'cat-b'}`}>
              {person.category === 'A' ? '👮 Police Officer' : '⚠️ Criminal Suspect'}
            </span>
          </div>
        </div>
        
        <div className="modal-body">
          <div className="modal-info-row">
            <span className="modal-label">Person ID:</span>
            <span className="modal-value">{person.person_id || 'N/A'}</span>
          </div>
          
          {person.category === 'B' && crime !== 'N/A' && (
            <div className="modal-info-row">
              <span className="modal-label">Crime:</span>
              <span className="modal-value crime-value">{crime}</span>
            </div>
          )}
          
          <div className="modal-info-row">
            <span className="modal-label">Camera:</span>
            <span className="modal-value">{person.camera_id || 'N/A'}</span>
          </div>
          
          <div className="modal-info-row">
            <span className="modal-label">Detected At:</span>
            <span className="modal-value">
              {new Date(person.timestamp).toLocaleString()}
            </span>
          </div>
          
          <div className="modal-info-row">
            <span className="modal-label">Location:</span>
            <span className="modal-value">
              {person.coords?.lat?.toFixed(4)}, {person.coords?.lng?.toFixed(4)}
            </span>
          </div>
        </div>
      </div>
    </div>
  )
}

export default PersonModal



