/**
 * Trigger detections based on time range
 */
export function getDetectionsInRange(detections, startTime, endTime) {
  return detections.filter(det => {
    const detTime = typeof det.timestamp === 'number' ? det.timestamp : parseFloat(det.timestamp)
    return detTime >= startTime && detTime < endTime
  })
}

/**
 * Group detections by camera
 */
export function groupDetectionsByCamera(detections) {
  const grouped = {}
  detections.forEach(det => {
    const camId = det.camera_id || det.cameraId
    if (!grouped[camId]) {
      grouped[camId] = []
    }
    grouped[camId].push(det)
  })
  return grouped
}

/**
 * Format timestamp for display
 */
export function formatTime(seconds) {
  const mins = Math.floor(seconds / 60)
  const secs = Math.floor(seconds % 60)
  return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`
}

