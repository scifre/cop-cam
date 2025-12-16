import { validateDetections, validateCameras } from './validateData'

/**
 * Load detections from JSON file
 */
export async function loadDetections() {
  try {
    const response = await fetch('/detections.json')
    if (!response.ok) {
      console.warn(`Failed to load detections: ${response.statusText}`)
      return []
    }
    const data = await response.json()
    
    // Handle both direct array and object with detections property
    const detections = Array.isArray(data) ? data : (data.detections || [])
    
    // Validate structure
    const validation = validateDetections(detections)
    if (!validation.valid) {
      console.error('Invalid detections format:', validation.errors)
      return []
    }
    if (validation.warnings.length > 0) {
      console.warn('Detection warnings:', validation.warnings.slice(0, 5))
    }
    
    // Validate and filter detections
    const validDetections = detections.filter(det => {
      return det && 
             typeof det.timestamp === 'number' && 
             det.camera_id && 
             det.person_id !== undefined
    })
    
    // Sort by timestamp
    validDetections.sort((a, b) => a.timestamp - b.timestamp)
    
    console.log(`✓ Loaded ${validDetections.length} detections (${validation.count} total)`)
    return validDetections
  } catch (error) {
    console.error('Error loading detections:', error)
    return []
  }
}

/**
 * Load camera configuration
 */
export async function loadCameras() {
  try {
    const response = await fetch('/cameras.json')
    if (!response.ok) {
      console.warn('cameras.json not found, using defaults')
      return getDefaultCameras()
    }
    const data = await response.json()
    const cameras = data.cameras || data || getDefaultCameras()
    
    // Validate camera structure
    const validation = validateCameras(cameras)
    if (!validation.valid) {
      console.warn('Camera validation warnings:', validation.missing)
      // Merge with defaults for missing cameras
      const defaults = getDefaultCameras()
      const merged = { ...defaults, ...cameras }
      return merged
    }
    
    console.log(`✓ Loaded ${validation.count} cameras`)
    return cameras
  } catch (error) {
    console.warn('Error loading cameras.json, using defaults:', error)
    return getDefaultCameras()
  }
}

function getDefaultCameras() {
  return {
    CAM_01: { name: "cp_lab1", location: { x: 0.0, y: 1.0, z: 0.0 } },
    CAM_02: { name: "cp_lab2", location: { x: 0.866, y: 0.5, z: 0.0 } },
    CAM_03: { name: "vlsi", location: { x: 0.866, y: -0.5, z: 0.0 } },
    CAM_04: { name: "iot", location: { x: 0.0, y: -1.0, z: 0.0 } },
    CAM_05: { name: "lift", location: { x: -0.866, y: -0.5, z: 0.0 } },
    CAM_06: { name: "loby", location: { x: -0.866, y: 0.5, z: 0.0 } },
  }
}

