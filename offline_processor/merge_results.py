#!/usr/bin/env python3
"""
Merge individual video processing results into final detections.json
Run this after processing all videos individually
"""

import json
import os
from pathlib import Path
from collections import defaultdict

# Configuration
INDIVIDUAL_JSON_DIR = "processed_data/individual"
OUTPUT_JSON = "processed_data/detections.json"
VIDEO_DIR = "processed_data/videos"

# Camera configuration (must match process_videos.py)
CAMERA_CONFIG = {
    "CAM_01": {"name": "cp_lab1.mp4", "location": {"x": 0.0, "y": 1.0, "z": 0.0}},
    "CAM_02": {"name": "cp_lab2.mp4", "location": {"x": 0.866, "y": 0.5, "z": 0.0}},
    "CAM_03": {"name": "vlsi.mp4", "location": {"x": 0.866, "y": -0.5, "z": 0.0}},
    "CAM_04": {"name": "iot.mp4", "location": {"x": 0.0, "y": -1.0, "z": 0.0}},
    "CAM_05": {"name": "lift.mp4", "location": {"x": -0.866, "y": -0.5, "z": 0.0}},
    "CAM_06": {"name": "loby.mp4", "location": {"x": -0.866, "y": 0.5, "z": 0.0}},
}

def find_individual_results():
    """Find all individual JSON files"""
    individual_dir = Path(INDIVIDUAL_JSON_DIR)
    if not individual_dir.exists():
        print(f"❌ Directory not found: {INDIVIDUAL_JSON_DIR}")
        return []
    
    json_files = list(individual_dir.glob("CAM_*.json"))
    return sorted(json_files)

def load_individual_result(json_path):
    """Load a single individual result file"""
    try:
        with open(json_path, 'r') as f:
            data = json.load(f)
        return data
    except Exception as e:
        print(f"❌ Error loading {json_path}: {e}")
        return None

def merge_results():
    """Merge all individual results into final output"""
    print("="*60)
    print("MERGING INDIVIDUAL VIDEO RESULTS")
    print("="*60)
    print()
    
    # Find all individual JSON files
    json_files = find_individual_results()
    
    if not json_files:
        print("❌ No individual result files found!")
        print(f"   Expected files in: {INDIVIDUAL_JSON_DIR}/")
        print(f"   Format: CAM_01.json, CAM_02.json, etc.")
        return False
    
    print(f"Found {len(json_files)} individual result files:")
    for jf in json_files:
        print(f"  ✓ {jf.name}")
    print()
    
    # Load all results
    all_detections = []
    camera_metadata = {}
    processed_cameras = set()
    
    for json_file in json_files:
        cam_id = json_file.stem  # e.g., "CAM_01" from "CAM_01.json"
        
        print(f"Loading {cam_id}...")
        data = load_individual_result(json_file)
        
        if data is None:
            print(f"  ⚠ Skipping {cam_id}")
                    continue
        
        # Extract detections
        detections = data.get("detections", [])
        if not detections:
            print(f"  ⚠ No detections found in {cam_id}")
                continue
            
        all_detections.extend(detections)
        processed_cameras.add(cam_id)
        
        # Extract camera metadata
        camera_info = data.get("metadata", {}).get("camera", {})
        if not camera_info and cam_id in CAMERA_CONFIG:
            # Fallback to config
            camera_info = {
                "video_file": CAMERA_CONFIG[cam_id]["name"],
                "output_video": f"videos/{cam_id}.mp4",
                "location": CAMERA_CONFIG[cam_id]["location"]
            }
        
        camera_metadata[cam_id] = camera_info
        
        print(f"  ✓ Loaded {len(detections)} detections")
    
    if not all_detections:
        print("\n❌ No detections found in any files!")
        return False
    
    # Check for missing cameras
    expected_cameras = set(CAMERA_CONFIG.keys())
    missing_cameras = expected_cameras - processed_cameras
    
    if missing_cameras:
        print(f"\n⚠ Warning: Missing cameras: {sorted(missing_cameras)}")
        print(f"   Processed: {sorted(processed_cameras)}")
        response = input("   Continue anyway? (y/n): ")
        if response.lower() != 'y':
            print("   Aborted.")
            return False
    
    # Sort all detections globally by timestamp
    print(f"\nSorting {len(all_detections)} detections...")
    all_detections.sort(key=lambda x: (x.get("timestamp", 0), x.get("camera_id", ""), x.get("frame_id", 0)))
    
    # Create final output structure
    output_data = {
        "metadata": {
        "total_detections": len(all_detections),
            "total_cameras": len(camera_metadata),
            "cameras": camera_metadata
        },
        "detections": all_detections
    }
    
    # Ensure output directory exists
    os.makedirs(os.path.dirname(OUTPUT_JSON), exist_ok=True)
    
    # Save merged JSON
    print(f"\n{'='*60}")
    print(f"Saving merged results to {OUTPUT_JSON}")
    print(f"{'='*60}")
    
    with open(OUTPUT_JSON, 'w') as f:
        json.dump(output_data, f, indent=2)
    
    print(f"✓ Saved {len(all_detections)} detections from {len(camera_metadata)} cameras")
    print(f"✓ Merged detection timeline saved to {OUTPUT_JSON}")
    
    # Print summary
    print(f"\n{'='*60}")
    print("MERGE SUMMARY")
    print(f"{'='*60}")
    print(f"Total detections: {len(all_detections)}")
    print(f"Cameras processed: {len(processed_cameras)}")
    
    # Count by person
    person_counts = defaultdict(int)
    for det in all_detections:
        person_id = det.get("person_id", "unknown")
        person_counts[person_id] += 1
    
    print(f"\nDetections by person:")
    for person, count in sorted(person_counts.items()):
        print(f"  {person}: {count}")
    
    # Count by camera
    camera_counts = defaultdict(int)
    for det in all_detections:
        camera_id = det.get("camera_id", "unknown")
        camera_counts[camera_id] += 1
    
    print(f"\nDetections by camera:")
    for camera, count in sorted(camera_counts.items()):
        print(f"  {camera}: {count}")
    
    print(f"\n{'='*60}")
    print("MERGE COMPLETE")
    print(f"{'='*60}")
    print(f"\nNext steps:")
    print(f"  1. Verify {OUTPUT_JSON}")
    print(f"  2. Run frontend/copy-data.sh to copy to frontend")
    print(f"  3. Start frontend: cd frontend && npm run dev")
    
    return True

if __name__ == "__main__":
    success = merge_results()
    exit(0 if success else 1)
