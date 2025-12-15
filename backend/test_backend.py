"""
Test Backend for Cop-Cam - Generates simulated detections without video processing.

This backend generates fake detection events for testing the frontend
without requiring video files or GPU processing.
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from typing import List
import asyncio
import random
import os
from dotenv import load_dotenv
from models import Detection, DetectionCreate, Coords
from database import DB
from face_database import face_db

# Load environment variables from .env file
load_dotenv()

# Camera configuration - Coordinates around 21.13° N, 81.77° E
CAMERA_CONFIG = {
    "cam_01": {"lat": 21.13, "lng": 81.77, "name": "Main Gate"},
    "cam_02": {"lat": 21.135, "lng": 81.775, "name": "North Wing"},
    "cam_03": {"lat": 21.125, "lng": 81.765, "name": "South Wing"},
    "cam_04": {"lat": 21.132, "lng": 81.773, "name": "East Wing"},
    "cam_05": {"lat": 21.128, "lng": 81.768, "name": "West Parking"},
    "cam_06": {"lat": 21.133, "lng": 81.772, "name": "Roof Access"},
}

# Test data - simulated criminals and police with details
TEST_CRIMINALS = [
    {
        "name": "Rahul Verma", 
        "person_id": "CRIM_001",
        "crime": "Robbery",
        "image_path": "/api/face-images/CRIM_001.jpg"
    },
    {
        "name": "Vikash Singh", 
        "person_id": "CRIM_002",
        "crime": "Assault",
        "image_path": "/api/face-images/CRIM_002.jpg"
    },
    {
        "name": "Ajay Kumar", 
        "person_id": "CRIM_003",
        "crime": "Theft",
        "image_path": "/api/face-images/CRIM_003.jpg"
    },
]

TEST_POLICE = [
    {
        "name": "Officer Sharma", 
        "person_id": "POLICE_001",
        "crime": "N/A",
        "image_path": "/api/face-images/POLICE_001.jpg"
    },
    {
        "name": "Officer Patel", 
        "person_id": "POLICE_002",
        "crime": "N/A",
        "image_path": "/api/face-images/POLICE_002.jpg"
    },
]

# Initialize face database with test data
def initialize_face_database():
    """Initialize face database with test person data."""
    for criminal in TEST_CRIMINALS:
        face_db.add_person(
            person_id=criminal["person_id"],
            name=criminal["name"],
            category="B",
            image_path=criminal["image_path"],
            crime=criminal["crime"]
        )
    
    for police in TEST_POLICE:
        face_db.add_person(
            person_id=police["person_id"],
            name=police["name"],
            category="A",
            image_path=police["image_path"],
            crime="N/A"
        )

# Initialize on import
initialize_face_database()

class WSManager:
    def __init__(self):
        self.active: List[WebSocket] = []

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.active.append(ws)

    def disconnect(self, ws: WebSocket):
        self.active.remove(ws)

    async def broadcast(self, msg: dict):
        for ws in self.active:
            try:
                await ws.send_json(msg)
            except:
                pass

mgr = WSManager()
db = DB()
is_simulating = False
simulation_task = None

async def generate_test_detections(speed_multiplier: float = 1.0):
    """Generate test detections at regular intervals."""
    global is_simulating
    
    is_simulating = True
    detection_count = 0
    
    # Mix of criminals and police
    all_people = TEST_CRIMINALS + TEST_POLICE
    
    print("=" * 60)
    print("TEST BACKEND: Generating simulated detections...")
    print("=" * 60)
    
    while is_simulating:
        # Random delay between detections (2-8 seconds, adjusted by speed)
        delay = random.uniform(2.0, 8.0) / speed_multiplier
        await asyncio.sleep(delay)
        
        if not is_simulating:
            break
        
        # Randomly select a person
        person = random.choice(all_people)
        category = "B" if person in TEST_CRIMINALS else "A"
        
        # Randomly select a camera
        camera_id = random.choice(list(CAMERA_CONFIG.keys()))
        camera_info = CAMERA_CONFIG[camera_id]
        
        # Get person details from face database
        person_details = face_db.get_person(person["person_id"])
        timestamp = datetime.now().isoformat()
        
        # Update last seen
        if person_details:
            face_db.update_last_seen(person["person_id"], timestamp)
        
        # Create detection with person details
        detection_count += 1
        det_data = {
            "id": detection_count,
            "detected": True,
            "category": category,
            "camera_id": camera_id,
            "timestamp": timestamp,
            "coords": {
                "lat": camera_info["lat"],
                "lng": camera_info["lng"]
            },
            "person_id": person["person_id"],
            "person_name": person["name"],
            "person_image": person.get("image_path", ""),
            "crime": person.get("crime", "Unknown") if category == "B" else "N/A"
        }
        
        det = Detection(
            id=detection_count,
            detected=True,
            category=category,
            camera_id=camera_id,
            timestamp=timestamp,
            coords=Coords(
                lat=camera_info["lat"],
                lng=camera_info["lng"]
            )
        )
        
        # Add to database
        db.add(det)
        
        # Broadcast Category B (criminal) detections with full details
        if category == "B":
            # Include person details in broadcast
            broadcast_data = {
                **det_data,
                "person_id": person["person_id"],
                "person_name": person["name"],
                "person_image": person.get("image_path", ""),
                "crime": person.get("crime", "Unknown")
            }
            await mgr.broadcast(broadcast_data)
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Detected {person['name']} ({person['person_id']}) at {camera_id}")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup - auto-start simulation
    async def delayed_start():
        await asyncio.sleep(2)  # Wait for WebSocket connections
        if not is_simulating:
            print("Auto-starting test simulation...")
            asyncio.create_task(generate_test_detections(speed_multiplier=1.0))
    
    asyncio.create_task(delayed_start())
    
    yield
    
    # Shutdown
    global is_simulating
    is_simulating = False

app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/report-detection")
async def report(data: DetectionCreate):
    """Accept detection reports (for compatibility)."""
    det = Detection(
        id=len(db.detections) + 1,
        detected=data.detected,
        category=data.category,
        camera_id=data.camera_id,
        timestamp=data.timestamp or datetime.now().isoformat(),
        coords=data.coords
    )
    db.add(det)
    
    if data.detected and data.category == "B":
        await mgr.broadcast(det.dict())
    
    return {"status": "ok", "id": det.id}

@app.get("/get-detections")
async def get_all():
    """Get all detections with person details."""
    detections = []
    for d in db.detections:
        det_dict = d.dict()
        # Try to get person details if person_id exists
        if hasattr(d, 'person_id') and d.person_id:
            person = face_db.get_person(d.person_id)
            if person:
                det_dict["person_name"] = person.get("name")
                det_dict["person_image"] = person.get("image_path")
                det_dict["crime"] = person.get("crime")
        detections.append(det_dict)
    return {"detections": detections}

@app.websocket("/ws/detections")
async def ws_endpoint(ws: WebSocket):
    """WebSocket endpoint for real-time detections."""
    await mgr.connect(ws)
    try:
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        mgr.disconnect(ws)

@app.get("/cameras")
async def get_cams():
    """Get camera list."""
    return {
        "cameras": [
            {"id": cam_id, "lat": info["lat"], "lng": info["lng"], "name": info["name"]}
            for cam_id, info in CAMERA_CONFIG.items()
        ]
    }

@app.post("/simulation/start")
async def start_simulation(speed: float = 1.0):
    """Start test simulation."""
    global is_simulating, simulation_task
    
    if is_simulating:
        return {"status": "already_running", "speed": speed}
    
    simulation_task = asyncio.create_task(generate_test_detections(speed_multiplier=speed))
    return {"status": "started", "speed": speed}

@app.post("/simulation/stop")
async def stop_simulation():
    """Stop test simulation."""
    global is_simulating
    is_simulating = False
    return {"status": "stopped"}

@app.get("/simulation/status")
async def simulation_status():
    """Get simulation status."""
    return {
        "mode": "test",
        "simulation_enabled": True,
        "is_running": is_simulating,
        "detections_count": len(db.detections)
    }

@app.get("/test/info")
async def test_info():
    """Get test backend information."""
    return {
        "backend_type": "test",
        "description": "Test backend generating simulated detections",
        "criminals": TEST_CRIMINALS,
        "police": TEST_POLICE,
        "cameras": list(CAMERA_CONFIG.keys())
    }

@app.get("/api/face-images/{person_id}")
async def get_face_image(person_id: str):
    """Serve face images (placeholder for now - returns a data URI)."""
    from fastapi.responses import Response
    import base64
    
    # Get person details
    person = face_db.get_person(person_id)
    if not person:
        return {"error": "Person not found"}
    
    # For now, return a placeholder image data URI
    # In production, you would read the actual image file
    from PIL import Image
    import io
    
    # Create a simple placeholder image with person initial
    img = Image.new('RGB', (200, 200), color=(73, 109, 137))
    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    img_data = buffer.getvalue()
    
    return Response(content=img_data, media_type="image/png")

@app.get("/api/person/{person_id}")
async def get_person_details(person_id: str):
    """Get person details by person_id."""
    person = face_db.get_person(person_id)
    if not person:
        return {"error": "Person not found"}
    return person

@app.get("/api/persons")
async def get_all_persons():
    """Get all persons in database."""
    return {
        "criminals": face_db.get_all_criminals(),
        "police": face_db.get_all_police()
    }

if __name__ == "__main__":
    import uvicorn
    
    # Get port from environment or default to 8001 for test backend
    port = int(os.getenv("TEST_BACKEND_PORT", "8001"))
    
    print("=" * 60)
    print("TEST BACKEND STARTING")
    print("=" * 60)
    print(f"Port: {port}")
    print("This backend generates simulated detections for testing.")
    print("No video files or GPU required.")
    print("=" * 60)
    
    uvicorn.run(app, host="0.0.0.0", port=port)

