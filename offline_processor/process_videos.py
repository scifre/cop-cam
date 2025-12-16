#!/usr/bin/env python3
"""
Offline CCTV Video Processor
Processes multiple videos sequentially and generates:
1. Annotated output videos
2. Global detection timeline JSON
"""

import warnings
from ultralytics import YOLO
warnings.filterwarnings("ignore", category=FutureWarning)
import cv2
from insightface.app import FaceAnalysis
from deep_sort_realtime.deepsort_tracker import DeepSort
from collections import defaultdict
import torch
import json
import os
from pathlib import Path
import math
import time
import gc

from helper import vector_search

# GPU setup
device = torch.device('cuda:0' if torch.cuda.is_available() else 'cpu')
print(f"Using device: {device}")

# Initialize models (EXACTLY as in test.py)
print("Loading models...")
app = FaceAnalysis(providers=["CUDAExecutionProvider", "CPUExecutionProvider"], 
                  allowed_modules=["detection", "recognition"])
app.prepare(ctx_id=0, det_size=(640, 640))
print("✓ InsightFace loaded")

yolo_model = YOLO("yolov8m.pt").to(device)
print("✓ YOLO loaded")

# Video directory
VIDEO_DIR = "cctv_videos"
OUTPUT_VIDEO_DIR = "processed_data/videos"
OUTPUT_JSON = "processed_data/detections.json"

# Individual video processing output (for single video mode)
INDIVIDUAL_JSON_DIR = "processed_data/individual"
INDIVIDUAL_VIDEO_DIR = "processed_data/videos"

# Ensure output directories exist
os.makedirs(OUTPUT_VIDEO_DIR, exist_ok=True)
os.makedirs(os.path.dirname(OUTPUT_JSON), exist_ok=True)
os.makedirs(INDIVIDUAL_JSON_DIR, exist_ok=True)

# ============================================
# PROCESSING MODE CONFIGURATION
# ============================================
# Set PROCESS_SINGLE_VIDEO to True to process one video at a time
# Set TARGET_CAMERA to the camera ID you want to process (e.g., "CAM_01")
# After processing all videos individually, run merge_results.py to combine them
PROCESS_SINGLE_VIDEO = True  # Change to False to process all videos at once
TARGET_CAMERA = "CAM_01"     # Change this: CAM_01, CAM_02, CAM_03, CAM_04, CAM_05, CAM_06

# ============================================
# PERFORMANCE & STABILITY SETTINGS
# ============================================
# Reduce these values if laptop overheats/shuts down
FRAME_SKIP = 2              # Process every Nth frame (2 = process every 2nd frame, reduces load by 50%)
BATCH_SIZE = 1              # Process frames in batches (keep at 1 for stability)
ENABLE_GPU_CLEANUP = True   # Clear GPU cache periodically (recommended)
CLEANUP_INTERVAL = 50       # Clear GPU cache every N frames
MAX_FRAMES = None           # Limit total frames (None = process all, set to number to limit)
PAUSE_EVERY_N_FRAMES = 100  # Small pause every N frames to prevent overheating (0 = no pause)
PAUSE_DURATION = 0.1        # Pause duration in seconds

# Camera configuration - 6 cameras in a circle
# Positions calculated for 60° spacing starting from top (90°)
# Each camera at radius 1.0, evenly distributed
CAMERA_CONFIG = {
    "CAM_01": {"name": "cp_lab1.mp4", "location": {"x": 0.0, "y": 1.0, "z": 0.0}},      # Top (90°)
    "CAM_02": {"name": "cp_lab2.mp4", "location": {"x": 0.866, "y": 0.5, "z": 0.0}},   # Top-right (30°)
    "CAM_03": {"name": "vlsi.mp4", "location": {"x": 0.866, "y": -0.5, "z": 0.0}},    # Bottom-right (-30°)
    "CAM_04": {"name": "iot.mp4", "location": {"x": 0.0, "y": -1.0, "z": 0.0}},        # Bottom (-90°)
    "CAM_05": {"name": "lift.mp4", "location": {"x": -0.866, "y": -0.5, "z": 0.0}},   # Bottom-left (-150°)
    "CAM_06": {"name": "loby.mp4", "location": {"x": -0.866, "y": 0.5, "z": 0.0}},    # Top-left (150°)
}

def get_video_files():
    """Get all video files from cctv_videos directory"""
    video_dir = Path(VIDEO_DIR)
    video_files = []
    for cam_id, config in sorted(CAMERA_CONFIG.items()):
        video_path = video_dir / config["name"]
        if video_path.exists():
            video_files.append((cam_id, video_path, config))
        else:
            print(f"⚠ Warning: {video_path} not found, skipping {cam_id}")
    return video_files

def process_video(cam_id, video_path, camera_config):
    """
    Process a single video using EXACT logic from test.py
    Returns: list of detections and output video path
    """
    print(f"\n{'='*60}")
    print(f"Processing {cam_id}: {video_path.name}")
    print(f"{'='*60}")
    
    # Open video
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise ValueError(f"Error: Could not open video file {video_path}")
    
    # Get video properties
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    
    print(f"Resolution: {width}x{height}, FPS: {fps:.2f}, Frames: {total_frames}")
    
    # Initialize tracker (EXACTLY as in test.py)
    tracker = DeepSort(max_age=40, max_cosine_distance=0.6, max_iou_distance=0.8)
    
    # Prediction dict (EXACTLY as in test.py)
    prediction_dict = defaultdict(lambda: {
        "name": "unknown",
        "predictions": []
    })
    
    # Output video writer - Use H.264 codec for browser compatibility
    output_video_path = os.path.join(OUTPUT_VIDEO_DIR, f"{cam_id}.mp4")
    # Try H.264 first (browser-compatible), fallback to mp4v
    fourcc = cv2.VideoWriter_fourcc(*"avc1")  # H.264 codec for browser compatibility
    out = cv2.VideoWriter(output_video_path, fourcc, fps, (width, height))
    
    # If H.264 fails, try mp4v
    if not out.isOpened():
        print("  ⚠ H.264 codec not available, trying mp4v...")
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        out = cv2.VideoWriter(output_video_path, fourcc, fps, (width, height))
    
    # Store all detections for this video
    all_detections = []
    
    frame_id = 0
    processed_frame_count = 0
    
    print(f"\nPerformance settings:")
    print(f"  Frame skip: {FRAME_SKIP} (process every {FRAME_SKIP} frames)")
    if MAX_FRAMES:
        print(f"  Max frames: {MAX_FRAMES}")
    print(f"  GPU cleanup: Every {CLEANUP_INTERVAL} frames" if ENABLE_GPU_CLEANUP else "  GPU cleanup: Disabled")
    if PAUSE_EVERY_N_FRAMES > 0:
        print(f"  Pause: Every {PAUSE_EVERY_N_FRAMES} frames for {PAUSE_DURATION}s")
    print()
    
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break
        
        # Frame skipping to reduce load
        if frame_id % FRAME_SKIP != 0:
            frame_id += 1
            # Still write the frame to output (skip processing, not writing)
            out.write(frame)
            continue
        
        # Limit total frames processed
        if MAX_FRAMES and processed_frame_count >= MAX_FRAMES:
            print(f"\n⚠ Reached MAX_FRAMES limit ({MAX_FRAMES}), stopping processing")
            print(f"   (Video will continue to end, but only first {MAX_FRAMES} frames processed)")
            # Continue writing remaining frames without processing
            while cap.isOpened():
                ret, frame = cap.read()
                if not ret:
                    break
                out.write(frame)
            break
        
        clean_frame = frame.copy()
        timestamp = frame_id / fps if fps > 0 else 0.0
        
        # YOLO detection (EXACTLY as in test.py)
        persons = yolo_model(frame)[0]
        
        identities = []
        for person in persons.boxes:
            if int(person.cls[0]) == 0:  # Class 0 = person
                x1, y1, x2, y2 = map(int, person.xyxy[0])
                conf = person.conf[0].cpu().numpy()
                identities.append(([x1, y1, x2 - x1, y2 - y1], conf))
        
        # Update tracker (EXACTLY as in test.py)
        tracks = tracker.update_tracks(identities, frame=frame)
        
        for track in tracks:
            if not track.is_confirmed():
                continue
            
            track_id = track.track_id
            name = prediction_dict[track_id]["name"]
            score = track.get_det_conf()
            
            # Get bounding box (EXACTLY as in test.py)
            t, l, b, r = map(int, track.to_tlbr())
            
            # Face recognition for unknown persons (EXACTLY as in test.py)
            if name == "unknown":
                person_crop = clean_frame[t:b, l:r]
                if person_crop.size != 0:
                    faces = app.get(person_crop)
                    if len(faces) != 0:
                        face = faces[0]
                        embedding = face.embedding
                        identity_results = vector_search(embedding, threshold=0.80)
                        name, rec_score = identity_results
                        rec_score = float(rec_score)
                        prediction_dict[track_id]["name"] = name
                        
                        # Red box for newly identified (EXACTLY as in test.py)
                        cv2.rectangle(frame, (l, t), (r, b), (255, 0, 0), 2)
                        cv2.putText(frame, f"{name}-{rec_score:.2f}", (l, t - 10), 
                                  cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 2)
                        
                        # Store detection
                        detection = {
                            "timestamp": round(timestamp, 3),
                            "frame_id": frame_id,
                            "camera_id": cam_id,
                            "track_id": track_id,
                            "person_id": name,
                            "bbox": [l, t, r, b],  # [x1, y1, x2, y2]
                            "confidence": round(float(rec_score), 4),
                            "detection_confidence": round(float(score), 4) if score is not None else None
                        }
                        all_detections.append(detection)
            else:
                # Yellow box for already identified (EXACTLY as in test.py)
                cv2.rectangle(frame, (l, t), (r, b), (0, 255, 255), 2)
                if score is not None:
                    cv2.putText(frame, f"{name}-{score:.2f}", (l, t - 10), 
                              cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 2)
                else:
                    cv2.putText(frame, f"{name}", (l, t - 10), 
                              cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 2)
                
                # Store detection for already identified person
                detection = {
                    "timestamp": round(timestamp, 3),
                    "frame_id": frame_id,
                    "camera_id": cam_id,
                    "track_id": track_id,
                    "person_id": name,
                    "bbox": [l, t, r, b],  # [x1, y1, x2, y2]
                    "confidence": None,  # No new recognition score
                    "detection_confidence": round(float(score), 4) if score is not None else None
                }
                all_detections.append(detection)
        
        # Write frame
        out.write(frame)
        frame_id += 1
        processed_frame_count += 1
        
        # Periodic GPU cleanup to prevent memory buildup
        if ENABLE_GPU_CLEANUP and processed_frame_count % CLEANUP_INTERVAL == 0:
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            gc.collect()
        
        # Small pause to prevent overheating
        if PAUSE_EVERY_N_FRAMES > 0 and processed_frame_count % PAUSE_EVERY_N_FRAMES == 0:
            time.sleep(PAUSE_DURATION)
        
        # Progress update
        if processed_frame_count % 50 == 0:  # More frequent updates
            progress = (frame_id / total_frames * 100) if total_frames > 0 else 0
            print(f"  Progress: Frame {frame_id}/{total_frames} ({progress:.1f}%) | Processed: {processed_frame_count} | Detections: {len(all_detections)}")
    
    cap.release()
    out.release()
    
    # Final cleanup
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
    gc.collect()
    
    print(f"\n✓ Completed {cam_id}:")
    print(f"   Total frames: {frame_id}")
    print(f"   Processed frames: {processed_frame_count}")
    print(f"   Detections: {len(all_detections)}")
    print(f"   Output video: {output_video_path}")
    
    return all_detections, output_video_path

def process_single_video(cam_id):
    """
    Process a single video and save individual results
    """
    print("="*60)
    print(f"PROCESSING SINGLE VIDEO: {cam_id}")
    print("="*60)
    
    if cam_id not in CAMERA_CONFIG:
        print(f"❌ Error: {cam_id} not found in CAMERA_CONFIG")
        print(f"Available cameras: {list(CAMERA_CONFIG.keys())}")
        return False
    
    camera_config = CAMERA_CONFIG[cam_id]
    video_path = Path(VIDEO_DIR) / camera_config["name"]
    
    if not video_path.exists():
        print(f"❌ Error: Video file not found: {video_path}")
        return False
    
    try:
        # Process the video
        detections, output_path = process_video(cam_id, video_path, camera_config)
        
        # Create individual output structure
        camera_metadata = {
            "video_file": camera_config["name"],
            "output_video": f"videos/{cam_id}.mp4",
            "location": camera_config["location"]
        }
        
        individual_data = {
            "camera_id": cam_id,
            "metadata": {
                "total_detections": len(detections),
                "camera": camera_metadata
            },
            "detections": detections
        }
        
        # Save individual JSON
        individual_json_path = os.path.join(INDIVIDUAL_JSON_DIR, f"{cam_id}.json")
        with open(individual_json_path, 'w') as f:
            json.dump(individual_data, f, indent=2)
        
        print(f"\n{'='*60}")
        print(f"✓ SINGLE VIDEO PROCESSING COMPLETE")
        print(f"{'='*60}")
        print(f"Camera: {cam_id}")
        print(f"Detections: {len(detections)}")
        print(f"Output video: {output_path}")
        print(f"Output JSON: {individual_json_path}")
        
        # Count by person
        person_counts = defaultdict(int)
        for det in detections:
            person_counts[det["person_id"]] += 1
        
        print(f"\nDetections by person:")
        for person, count in sorted(person_counts.items()):
            print(f"  {person}: {count}")
        
        print(f"\n{'='*60}")
        print("NEXT STEPS:")
        print(f"1. Change TARGET_CAMERA to next camera (e.g., 'CAM_02')")
        print(f"2. Run this script again")
        print(f"3. After processing all videos, run merge_results.py")
        print(f"{'='*60}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error processing {cam_id}: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Main processing function"""
    print("="*60)
    print("OFFLINE CCTV VIDEO PROCESSOR")
    print("="*60)
    
    # Single video processing mode
    if PROCESS_SINGLE_VIDEO:
        print(f"\n🔧 SINGLE VIDEO MODE")
        print(f"Target Camera: {TARGET_CAMERA}")
        print(f"\nTo process all videos:")
        print(f"  1. Process {TARGET_CAMERA} (current)")
        print(f"  2. Change TARGET_CAMERA to next camera")
        print(f"  3. Repeat until all cameras processed")
        print(f"  4. Run merge_results.py to combine results")
        print()
        
        success = process_single_video(TARGET_CAMERA)
        if success:
            print(f"\n✅ Successfully processed {TARGET_CAMERA}")
        else:
            print(f"\n❌ Failed to process {TARGET_CAMERA}")
        return
    
    # Batch processing mode (original behavior)
    print(f"\n🔧 BATCH PROCESSING MODE")
    print(f"Processing all videos sequentially...")
    
    # Get all video files
    video_files = get_video_files()
    
    if not video_files:
        print("❌ No video files found!")
        return
    
    print(f"\nFound {len(video_files)} videos to process")
    
    # Process all videos sequentially
    all_detections = []
    camera_metadata = {}
    
    for cam_id, video_path, camera_config in video_files:
        try:
            detections, output_path = process_video(cam_id, video_path, camera_config)
            all_detections.extend(detections)
            
            # Store camera metadata
            camera_metadata[cam_id] = {
                "video_file": camera_config["name"],
                "output_video": f"videos/{cam_id}.mp4",
                "location": camera_config["location"]
            }
        except Exception as e:
            print(f"❌ Error processing {cam_id}: {e}")
            import traceback
            traceback.print_exc()
            continue
    
    # Sort all detections globally by timestamp
    all_detections.sort(key=lambda x: (x["timestamp"], x["camera_id"], x["frame_id"]))
    
    # Create final output structure
    output_data = {
        "metadata": {
            "total_detections": len(all_detections),
            "total_cameras": len(camera_metadata),
            "cameras": camera_metadata
        },
        "detections": all_detections
    }
    
    # Save JSON
    print(f"\n{'='*60}")
    print(f"Saving results to {OUTPUT_JSON}")
    print(f"{'='*60}")
    
    with open(OUTPUT_JSON, 'w') as f:
        json.dump(output_data, f, indent=2)
    
    print(f"✓ Saved {len(all_detections)} detections from {len(camera_metadata)} cameras")
    print(f"✓ Output videos saved to {OUTPUT_VIDEO_DIR}/")
    print(f"✓ Detection timeline saved to {OUTPUT_JSON}")
    
    # Print summary
    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")
    print(f"Total detections: {len(all_detections)}")
    
    # Count by person
    person_counts = defaultdict(int)
    for det in all_detections:
        person_counts[det["person_id"]] += 1
    
    print(f"\nDetections by person:")
    for person, count in sorted(person_counts.items()):
        print(f"  {person}: {count}")
    
    print(f"\n{'='*60}")
    print("PROCESSING COMPLETE")
    print(f"{'='*60}")

if __name__ == "__main__":
    main()

