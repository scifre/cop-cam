#!/bin/bash
# Copy processed videos and detections to public folder

set -e  # Exit on error

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "=========================================="
echo "Copying data files to frontend public/"
echo "=========================================="
echo ""

# Change to frontend directory
cd "$SCRIPT_DIR"

# Create directories
mkdir -p public/videos

# Copy videos from processed_data
VIDEO_COUNT=0
if [ -d "$PROJECT_ROOT/processed_data/videos" ]; then
  echo "📹 Copying videos..."
  for video in "$PROJECT_ROOT/processed_data/videos"/*.mp4; do
    if [ -f "$video" ]; then
      cp "$video" public/videos/
      VIDEO_COUNT=$((VIDEO_COUNT + 1))
      echo "  ✓ $(basename "$video")"
    fi
  done
  if [ $VIDEO_COUNT -eq 0 ]; then
    echo "  ⚠ No videos found in processed_data/videos/"
  else
    echo "  ✓ Copied $VIDEO_COUNT videos"
  fi
else
  echo "  ⚠ Warning: processed_data/videos/ directory not found"
fi

# Copy detections.json
if [ -f "$PROJECT_ROOT/processed_data/detections.json" ]; then
  echo ""
  echo "📄 Copying detections.json..."
  cp "$PROJECT_ROOT/processed_data/detections.json" public/
  
  # Validate JSON structure
  python3 << EOF
import json
import sys

try:
    with open('public/detections.json', 'r') as f:
        data = json.load(f)
    
    # Check structure
    if isinstance(data, dict) and 'detections' in data:
        detections = data['detections']
        print(f"  ✓ Found {len(detections)} detections in JSON")
        
        # Validate first few detections
        if len(detections) > 0:
            required_fields = ['timestamp', 'camera_id', 'person_id']
            sample = detections[0]
            missing = [f for f in required_fields if f not in sample]
            if missing:
                print(f"  ⚠ Warning: Missing fields in detections: {missing}")
            else:
                print(f"  ✓ Detection structure validated")
    elif isinstance(data, list):
        print(f"  ✓ Found {len(data)} detections (array format)")
    else:
        print(f"  ⚠ Warning: Unexpected JSON structure")
        sys.exit(1)
except Exception as e:
    print(f"  ✗ Error validating JSON: {e}")
    sys.exit(1)
EOF
else
  echo ""
  echo "  ⚠ Warning: detections.json not found in processed_data/"
fi

# Create cameras.json from metadata
if [ -f "$PROJECT_ROOT/processed_data/detections.json" ]; then
  echo ""
  echo "📷 Creating cameras.json..."
  python3 << EOF
import json
import os

try:
    with open('$PROJECT_ROOT/processed_data/detections.json', 'r') as f:
        data = json.load(f)
    
    cameras = data.get('metadata', {}).get('cameras', {})
    
    if not cameras:
        print("  ⚠ No camera metadata found, using defaults")
        cameras = {
            "CAM_01": {"name": "cp_lab1", "location": {"x": 0.0, "y": 1.0, "z": 0.0}},
            "CAM_02": {"name": "cp_lab2", "location": {"x": 0.866, "y": 0.5, "z": 0.0}},
            "CAM_03": {"name": "vlsi", "location": {"x": 0.866, "y": -0.5, "z": 0.0}},
            "CAM_04": {"name": "iot", "location": {"x": 0.0, "y": -1.0, "z": 0.0}},
            "CAM_05": {"name": "lift", "location": {"x": -0.866, "y": -0.5, "z": 0.0}},
            "CAM_06": {"name": "loby", "location": {"x": -0.866, "y": 0.5, "z": 0.0}},
        }
    
    output = {'cameras': cameras}
    
    with open('public/cameras.json', 'w') as f:
        json.dump(output, f, indent=2)
    
    print(f"  ✓ Created cameras.json with {len(cameras)} cameras")
    for cam_id in sorted(cameras.keys()):
        cam = cameras[cam_id]
        print(f"    - {cam_id}: {cam.get('name', 'N/A')}")
except Exception as e:
    print(f"  ✗ Error creating cameras.json: {e}")
    import traceback
    traceback.print_exc()
EOF
else
  echo ""
  echo "  ⚠ Skipping cameras.json creation (detections.json not found)"
fi

echo ""
echo "=========================================="
echo "✓ Copy complete!"
echo "=========================================="
echo ""
echo "Files in public/:"
ls -lh public/ 2>/dev/null | tail -n +2 || echo "  (empty)"
echo ""
if [ -d "public/videos" ]; then
  echo "Videos in public/videos/:"
  ls -lh public/videos/*.mp4 2>/dev/null | awk '{print "  " $9 " (" $5 ")"}' || echo "  (no videos)"
fi
echo ""

