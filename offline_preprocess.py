"""
Offline Preprocessing Script for Cop-Cam Surveillance System

Processes CCTV videos sequentially (one by one) to avoid GPU memory issues.
Saves all detection results to simulation_data/ for later replay.

Output Structure:
- simulation_data/detections/CAM_XX.json - Detection events per camera
- simulation_data/timeline.json - Global timeline of all detections
- simulation_data/criminals.json - Criminal metadata
- simulation_data/embeddings/ - Stable embeddings per identity
- simulation_data/faces/ - Face images
"""

import warnings
warnings.filterwarnings("ignore", category=FutureWarning)

import cv2
import json
import os
import numpy as np
from pathlib import Path
from collections import defaultdict, Counter
from insightface.model_zoo import get_model
from deep_sort_realtime.deepsort_tracker import DeepSort
from helper import align_faces, get_face_embeddings, batch_vector_search, prepare_deepsort_inputs

# Configuration
CCTV_DIR = "cctv"
SIMULATION_DATA_DIR = "simulation_data"
DETECTIONS_DIR = os.path.join(SIMULATION_DATA_DIR, "detections")
EMBEDDINGS_DIR = os.path.join(SIMULATION_DATA_DIR, "embeddings")
FACES_DIR = os.path.join(SIMULATION_DATA_DIR, "faces")

# Camera configuration (matches backend)
CAMERA_CONFIG = {
    "cam_01": {"lat": 20.445, "lng": 82.921, "name": "Main Gate"},
    "cam_02": {"lat": 20.448, "lng": 82.925, "name": "North Wing"},
    "cam_03": {"lat": 20.442, "lng": 82.918, "name": "South Wing"},
    "cam_04": {"lat": 20.446, "lng": 82.923, "name": "East Wing"},
    "cam_05": {"lat": 20.444, "lng": 82.919, "name": "West Parking"},
    "cam_06": {"lat": 20.447, "lng": 82.922, "name": "Roof Access"},
}

# Initialize directories
os.makedirs(DETECTIONS_DIR, exist_ok=True)
os.makedirs(EMBEDDINGS_DIR, exist_ok=True)
os.makedirs(FACES_DIR, exist_ok=True)

# Load POI list
with open("poi.txt", "r") as f:
    poi = [line.strip() for line in f.readlines()]

# Initialize models
print("Loading face detection model...")
detector = get_model(
    name="/home/scifre/.insightface/models/buffalo_s/det_500m.onnx",
    providers=['CUDAExecutionProvider', 'CPUExecutionProvider']
)
detector.prepare(ctx_id=0, input_size=(640, 640))

# Global tracking
person_id_counter = {"A": 1, "B": 1}  # Separate counters for Police (A) and Criminal (B)
name_to_person_id = {}  # Maps name -> person_id
person_metadata = {}  # Stores metadata for each person_id
global_timeline = []  # Global timeline of all detections
all_detections = defaultdict(list)  # Per-camera detections

# Track first seen info for each person
first_seen_info = {}  # person_id -> {camera_id, time, face_image_path}


def get_person_id(name, category):
    """Generate or retrieve person_id for a given name and category."""
    if name in name_to_person_id:
        return name_to_person_id[name]
    
    # Generate new person_id
    prefix = "POLICE" if category == "A" else "CRIM"
    person_id = f"{prefix}_{person_id_counter[category]:03d}"
    person_id_counter[category] += 1
    
    name_to_person_id[name] = person_id
    return person_id


def save_face_image(frame, bbox, person_id, camera_id):
    """Extract and save face image."""
    t, l, b, r = map(int, bbox)
    # Add padding
    padding = 20
    t = max(0, t - padding)
    l = max(0, l - padding)
    b = min(frame.shape[0], b + padding)
    r = min(frame.shape[1], r + padding)
    
    face_crop = frame[t:b, l:r]
    filename = f"{person_id}_{camera_id}.jpg"
    filepath = os.path.join(FACES_DIR, filename)
    cv2.imwrite(filepath, face_crop)
    return filepath


def save_embedding(person_id, embedding):
    """Save stable embedding for a person."""
    filepath = os.path.join(EMBEDDINGS_DIR, f"{person_id}.npy")
    np.save(filepath, embedding)


def process_video(video_path, camera_id, global_start_time=0.0):
    """
    Process a single video file.
    
    Args:
        video_path: Path to video file
        camera_id: Camera identifier (e.g., "cam_01")
        global_start_time: Global timestamp offset for this video
    
    Returns:
        Last global timestamp in this video
    """
    print(f"\nProcessing {video_path} for {camera_id}...")
    
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"Error: Could not open {video_path}")
        return global_start_time
    
    fps = cap.get(cv2.CAP_PROP_FPS)
    if fps <= 0:
        fps = 30.0  # Default FPS
    
    frame_count = 0
    prediction_dict = defaultdict(list)  # track_id -> list of predictions
    track_embeddings = {}  # track_id -> latest embedding
    track_bboxes = {}  # track_id -> latest bbox
    tracker = DeepSort(max_age=20, max_cosine_distance=0.6, max_iou_distance=0.8)
    
    camera_detections = []
    
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break
        
        # Calculate global timestamp
        global_time = global_start_time + (frame_count / fps)
        
        # Detect faces
        boxes, landmarks = detector.detect(frame)
        
        # Align faces
        aligned_faces = align_faces(frame, landmarks)
        
        # Generate embeddings
        embeddings = get_face_embeddings(aligned_faces)
        
        # Perform vector search
        identity_results = batch_vector_search(embeddings, threshold=0.40)
        
        # Prepare inputs for deepsort
        identities = prepare_deepsort_inputs(boxes, identity_results)
        
        # Update tracker
        tracks = tracker.update_tracks(identities, frame=frame)
        
        for track in tracks:
            if not track.is_confirmed():
                continue
            
            name = track.det_class
            score = track.get_det_conf()
            track_id = track.track_id
            t, l, b, r = map(int, track.to_tlbr())
            bbox = [t, l, b, r]
            
            # Store prediction
            prediction_dict[track_id].append(name)
            
            # Store latest embedding and bbox for this track
            if len(embeddings) > 0 and len(identity_results) > 0:
                # Find corresponding embedding (simplified - assumes order matches)
                track_idx = min(len(embeddings) - 1, len(prediction_dict[track_id]) - 1)
                if track_idx >= 0:
                    track_embeddings[track_id] = embeddings[track_idx]
                    track_bboxes[track_id] = bbox
            
            # After 10-frame stabilization, create detection
            if len(prediction_dict[track_id]) >= 10:
                counter = Counter(prediction_dict[track_id])
                prediction = counter.most_common(1)[0][0]
                
                # Determine category
                category = "B" if prediction in poi else "A"
                
                # Get or create person_id
                person_id = get_person_id(prediction, category)
                
                # Track first seen info
                if person_id not in first_seen_info:
                    face_image_path = save_face_image(frame, bbox, person_id, camera_id)
                    # Store relative path
                    face_image_rel_path = os.path.join("faces", os.path.basename(face_image_path))
                    first_seen_info[person_id] = {
                        "camera_id": camera_id,
                        "time": global_time,
                        "face_image_path": face_image_rel_path
                    }
                    
                    # Save embedding if available
                    if track_id in track_embeddings:
                        save_embedding(person_id, track_embeddings[track_id])
                
                # Create detection event
                detection = {
                    "person_id": person_id,
                    "category": category,
                    "camera_id": camera_id,
                    "timestamp": global_time,
                    "frame_id": frame_count,
                    "bbox": bbox,
                    "confidence": float(score) if score is not None else 0.0,
                    "face_image_path": first_seen_info[person_id]["face_image_path"]
                }
                
                camera_detections.append(detection)
                
                # Add to global timeline
                global_timeline.append({
                    "global_time": global_time,
                    "camera_id": camera_id,
                    "person_id": person_id
                })
            
            # Keep only last 10 predictions
            prediction_dict[track_id] = prediction_dict[track_id][-10:]
        
        frame_count += 1
        
        if frame_count % 100 == 0:
            print(f"  Processed {frame_count} frames...")
    
    cap.release()
    
    # Save detections for this camera
    detections_file = os.path.join(DETECTIONS_DIR, f"{camera_id.upper()}.json")
    with open(detections_file, "w") as f:
        json.dump(camera_detections, f, indent=2)
    
    print(f"  Saved {len(camera_detections)} detections to {detections_file}")
    
    # Return last timestamp
    last_time = global_start_time + (frame_count / fps) if frame_count > 0 else global_start_time
    return last_time


def build_criminals_metadata():
    """Build criminals.json from first_seen_info and person_metadata."""
    criminals = {}
    
    for person_id, info in first_seen_info.items():
        if person_id.startswith("CRIM"):
            # Extract name from person_id mapping
            name = None
            for n, pid in name_to_person_id.items():
                if pid == person_id:
                    name = n
                    break
            
            criminals[person_id] = {
                "name": name or "Unknown",
                "crime": "Unknown",  # Could be extended with additional metadata
                "first_seen_camera": info["camera_id"],
                "first_seen_time": info["time"],
                "face_image": info["face_image_path"]
            }
    
    return criminals


def main():
    """Main preprocessing function."""
    print("=" * 60)
    print("Cop-Cam Offline Preprocessing")
    print("=" * 60)
    
    # Find all video files in CCTV directory
    video_files = []
    if os.path.exists(CCTV_DIR):
        for filename in sorted(os.listdir(CCTV_DIR)):
            if filename.lower().endswith(('.mp4', '.avi', '.mov', '.mkv', '.flv')):
                video_files.append(os.path.join(CCTV_DIR, filename))
    
    if not video_files:
        print(f"Error: No video files found in {CCTV_DIR}/")
        print("Please place CCTV video files in the cctv/ directory.")
        return
    
    print(f"\nFound {len(video_files)} video file(s) to process")
    
    # Process videos sequentially
    global_time = 0.0
    camera_idx = 0
    
    for video_path in video_files:
        # Assign camera ID (cycle through available cameras)
        camera_ids = sorted(CAMERA_CONFIG.keys())
        camera_id = camera_ids[camera_idx % len(camera_ids)]
        camera_idx += 1
        
        # Process video
        global_time = process_video(video_path, camera_id, global_time)
    
    # Build criminals metadata
    criminals = build_criminals_metadata()
    
    # Save timeline (sort by global_time)
    global_timeline.sort(key=lambda x: x["global_time"])
    timeline_file = os.path.join(SIMULATION_DATA_DIR, "timeline.json")
    with open(timeline_file, "w") as f:
        json.dump(global_timeline, f, indent=2)
    print(f"\nSaved {len(global_timeline)} timeline events to {timeline_file}")
    
    # Save criminals metadata
    criminals_file = os.path.join(SIMULATION_DATA_DIR, "criminals.json")
    with open(criminals_file, "w") as f:
        json.dump(criminals, f, indent=2)
    print(f"Saved {len(criminals)} criminal records to {criminals_file}")
    
    print("\n" + "=" * 60)
    print("Preprocessing complete!")
    print("=" * 60)
    print(f"\nOutput directory: {SIMULATION_DATA_DIR}/")
    print(f"  - Detections: {DETECTIONS_DIR}/")
    print(f"  - Timeline: {timeline_file}")
    print(f"  - Criminals: {criminals_file}")
    print(f"  - Embeddings: {EMBEDDINGS_DIR}/")
    print(f"  - Face images: {FACES_DIR}/")


if __name__ == "__main__":
    main()

