/**
 * Validate data format compatibility
 */
export function validateDetections(detections) {
  if (!Array.isArray(detections)) {
    return { valid: false, error: 'Detections must be an array' }
  }

  const errors = []
  const warnings = []

  detections.forEach((det, index) => {
    // Required fields
    if (!det.camera_id) {
      errors.push(`Detection ${index}: missing camera_id`)
    }
    if (det.person_id === undefined) {
      errors.push(`Detection ${index}: missing person_id`)
    }
    if (typeof det.timestamp !== 'number') {
      errors.push(`Detection ${index}: timestamp must be a number`)
    }
    if (!Array.isArray(det.bbox) || det.bbox.length !== 4) {
      warnings.push(`Detection ${index}: bbox should be [x1, y1, x2, y2]`)
    }
  })

  return {
    valid: errors.length === 0,
    errors,
    warnings,
    count: detections.length
  }
}

export function validateCameras(cameras) {
  if (!cameras || typeof cameras !== 'object') {
    return { valid: false, error: 'Cameras must be an object' }
  }

  const cameraIds = Object.keys(cameras)
  const expectedCams = ['CAM_01', 'CAM_02', 'CAM_03', 'CAM_04', 'CAM_05', 'CAM_06']
  const missing = expectedCams.filter(id => !cameraIds.includes(id))
  const extra = cameraIds.filter(id => !expectedCams.includes(id))

  return {
    valid: missing.length === 0,
    missing,
    extra,
    count: cameraIds.length
  }
}

