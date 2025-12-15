"""
Simulation replay module for Cop-Cam backend.

Loads preprocessed detection data and replays it in real-time via WebSocket.
"""

import os
import json
import asyncio
from typing import List, Dict, Optional
from pathlib import Path
from models import Detection, Coords

SIMULATION_DATA_DIR = "simulation_data"
TIMELINE_FILE = os.path.join(SIMULATION_DATA_DIR, "timeline.json")
DETECTIONS_DIR = os.path.join(SIMULATION_DATA_DIR, "detections")
CRIMINALS_FILE = os.path.join(SIMULATION_DATA_DIR, "criminals.json")

# Camera configuration (must match offline_preprocess.py)
CAMERA_CONFIG = {
    "cam_01": {"lat": 21.13, "lng": 81.77, "name": "Main Gate"},
    "cam_02": {"lat": 21.135, "lng": 81.775, "name": "North Wing"},
    "cam_03": {"lat": 21.125, "lng": 81.765, "name": "South Wing"},
    "cam_04": {"lat": 21.132, "lng": 81.773, "name": "East Wing"},
    "cam_05": {"lat": 21.128, "lng": 81.768, "name": "West Parking"},
    "cam_06": {"lat": 21.133, "lng": 81.772, "name": "Roof Access"},
}


class SimulationReplay:
    """Handles simulation replay from preprocessed data."""
    
    def __init__(self, ws_manager, db):
        self.ws_manager = ws_manager
        self.db = db
        self.timeline: List[Dict] = []
        self.detections_by_camera: Dict[str, List[Dict]] = {}
        self.criminals: Dict[str, Dict] = {}
        self.is_running = False
        self.replay_task: Optional[asyncio.Task] = None
    
    def load_simulation_data(self) -> bool:
        """Load simulation data from disk."""
        try:
            # Load timeline
            if not os.path.exists(TIMELINE_FILE):
                print(f"Warning: Timeline file not found: {TIMELINE_FILE}")
                return False
            
            with open(TIMELINE_FILE, "r") as f:
                self.timeline = json.load(f)
            
            print(f"Loaded {len(self.timeline)} timeline events")
            
            # Load detections per camera
            if os.path.exists(DETECTIONS_DIR):
                for filename in os.listdir(DETECTIONS_DIR):
                    if filename.endswith(".json"):
                        camera_id = filename.replace(".json", "").lower()
                        filepath = os.path.join(DETECTIONS_DIR, filename)
                        with open(filepath, "r") as f:
                            self.detections_by_camera[camera_id] = json.load(f)
                        print(f"Loaded {len(self.detections_by_camera[camera_id])} detections for {camera_id}")
            
            # Load criminals metadata
            if os.path.exists(CRIMINALS_FILE):
                with open(CRIMINALS_FILE, "r") as f:
                    self.criminals = json.load(f)
                print(f"Loaded {len(self.criminals)} criminal records")
            
            return True
        
        except Exception as e:
            print(f"Error loading simulation data: {e}")
            return False
    
    def get_detection_for_timeline_event(self, timeline_event: Dict) -> Optional[Dict]:
        """Get full detection data for a timeline event."""
        camera_id_raw = timeline_event["camera_id"]
        camera_id_lower = camera_id_raw.lower()
        person_id = timeline_event["person_id"]
        global_time = timeline_event["global_time"]
        
        # Try both lowercase and uppercase versions
        camera_id = camera_id_lower
        if camera_id not in self.detections_by_camera:
            # Try uppercase version
            camera_id = camera_id_raw.upper()
            if camera_id not in self.detections_by_camera:
                return None
        
        # Find matching detection (same person_id and closest timestamp)
        best_match = None
        min_time_diff = float('inf')
        
        for det in self.detections_by_camera[camera_id]:
            if det["person_id"] == person_id:
                time_diff = abs(det["timestamp"] - global_time)
                if time_diff < min_time_diff:
                    min_time_diff = time_diff
                    best_match = det
        
        return best_match
    
    async def replay_detections(self, speed_multiplier: float = 1.0):
        """
        Replay detections from timeline in real-time.
        
        Args:
            speed_multiplier: Speed multiplier (1.0 = real-time, 2.0 = 2x speed, etc.)
        """
        if not self.timeline:
            print("No timeline data to replay")
            return
        
        self.is_running = True
        print(f"Starting simulation replay ({speed_multiplier}x speed)...")
        
        previous_time = None
        
        for i, timeline_event in enumerate(self.timeline):
            if not self.is_running:
                break
            
            current_time = timeline_event["global_time"]
            
            # Calculate wait time
            if previous_time is not None:
                wait_time = (current_time - previous_time) / speed_multiplier
                if wait_time > 0:
                    await asyncio.sleep(wait_time)
            
            previous_time = current_time
            
            # Get full detection data
            detection_data = self.get_detection_for_timeline_event(timeline_event)
            
            if detection_data:
                camera_id_raw = detection_data["camera_id"]
                camera_id = camera_id_raw.lower()
                category = detection_data["category"]
                
                # Get camera coordinates
                if camera_id in CAMERA_CONFIG:
                    coords = Coords(
                        lat=CAMERA_CONFIG[camera_id]["lat"],
                        lng=CAMERA_CONFIG[camera_id]["lng"]
                    )
                else:
                    # Fallback coordinates
                    coords = Coords(lat=21.13, lng=81.77)
                
                # Create detection object
                # Format timestamp as ISO string (simulation time)
                from datetime import datetime, timedelta
                base_time = datetime.now()
                sim_timestamp = (base_time + timedelta(seconds=current_time)).isoformat()
                
                det = Detection(
                    id=len(self.db.detections) + 1,
                    detected=True,
                    category=category,
                    camera_id=camera_id,
                    timestamp=sim_timestamp,
                    coords=coords
                )
                
                # Add to database
                self.db.add(det)
                
                # Broadcast Category B (criminal) detections via WebSocket
                if category == "B":
                    await self.ws_manager.broadcast(det.dict())
                    print(f"[{current_time:.2f}s] Detected {detection_data['person_id']} at {camera_id}")
        
        self.is_running = False
        print("Simulation replay complete")
    
    def start_replay(self, speed_multiplier: float = 1.0):
        """Start replay in background task."""
        if self.replay_task and not self.replay_task.done():
            print("Replay already running")
            return
        
        self.replay_task = asyncio.create_task(self.replay_detections(speed_multiplier))
    
    def stop_replay(self):
        """Stop replay."""
        self.is_running = False
        if self.replay_task and not self.replay_task.done():
            self.replay_task.cancel()

