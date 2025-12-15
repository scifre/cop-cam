from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from datetime import datetime
from typing import List
import asyncio
import json
import os
from dotenv import load_dotenv
from models import Detection, DetectionCreate
from database import db
from simulation import SimulationReplay
from face_database import face_db

# Load environment variables from .env file
load_dotenv()

# Check for simulation mode
SIMULATION_MODE = os.getenv("SIMULATION_MODE", "false").lower() == "true"

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

# Initialize simulation replay if in simulation mode
simulation_replay = None
if SIMULATION_MODE:
    simulation_replay = SimulationReplay(mgr, db)
    if simulation_replay.load_simulation_data():
        print("=" * 60)
        print("SIMULATION MODE ENABLED")
        print("=" * 60)
        print("Backend will replay preprocessed detections.")
        print("No GPU required - all processing was done offline.")
        print("=" * 60)
    else:
        print("Warning: Simulation mode enabled but data not found.")
        print("Run offline_preprocess.py first to generate simulation data.")
        simulation_replay = None
else:
    print("Live mode: Backend ready to receive real-time detections.")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    if SIMULATION_MODE and simulation_replay:
        # Start replay in background after a short delay
        async def delayed_start():
            await asyncio.sleep(3)  # Wait for WebSocket connections
            if simulation_replay:
                print("Auto-starting simulation replay...")
                simulation_replay.start_replay(speed_multiplier=1.0)
        
        asyncio.create_task(delayed_start())
    
    yield
    # Shutdown
    if SIMULATION_MODE and simulation_replay:
        simulation_replay.stop_replay()

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
    timestamp = data.timestamp or datetime.now().isoformat()
    
    # Create detection
    det = Detection(
        id=len(db.detections) + 1,
        detected=data.detected,
        category=data.category,
        camera_id=data.camera_id,
        timestamp=timestamp,
        coords=data.coords,
        person_id=data.person_id,
        person_name=data.person_name,
        person_image=data.person_image,
        crime=data.crime
    )
    db.add(det)
    
    # Update face database if person_id provided
    if data.person_id:
        # Update last seen timestamp
        person = face_db.get_person(data.person_id)
        if person:
            face_db.update_last_seen(data.person_id, timestamp)
        elif data.person_name:
            # Create new person entry if doesn't exist
            face_db.add_person(
                person_id=data.person_id,
                name=data.person_name,
                category=data.category,
                image_path=data.person_image or "",
                crime=data.crime or "Unknown"
            )
    
    # Broadcast Category B (criminal) detections with person details
    if data.detected and data.category == "B":
        det_dict = det.dict()
        # Ensure person details are included
        if data.person_id:
            person = face_db.get_person(data.person_id)
            if person:
                det_dict["person_name"] = person.get("name")
                det_dict["person_image"] = person.get("image_path")
                det_dict["crime"] = person.get("crime")
        await mgr.broadcast(det_dict)
    
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
    await mgr.connect(ws)
    try:
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        mgr.disconnect(ws)

@app.get("/cameras")
async def get_cams():
    return {
        "cameras": [
            {"id": "cam_01", "lat": 21.13, "lng": 81.77, "name": "Main Gate"},
            {"id": "cam_02", "lat": 21.135, "lng": 81.775, "name": "North Wing"},
            {"id": "cam_03", "lat": 21.125, "lng": 81.765, "name": "South Wing"},
            {"id": "cam_04", "lat": 21.132, "lng": 81.773, "name": "East Wing"},
            {"id": "cam_05", "lat": 21.128, "lng": 81.768, "name": "West Parking"},
            {"id": "cam_06", "lat": 21.133, "lng": 81.772, "name": "Roof Access"},
        ]
    }

@app.post("/simulation/start")
async def start_simulation(speed: float = 1.0):
    """Start simulation replay (only available in SIMULATION_MODE)."""
    if not SIMULATION_MODE or simulation_replay is None:
        return {"error": "Simulation mode not enabled or data not loaded"}
    
    simulation_replay.start_replay(speed_multiplier=speed)
    return {"status": "started", "speed": speed}

@app.post("/simulation/stop")
async def stop_simulation():
    """Stop simulation replay."""
    if not SIMULATION_MODE or simulation_replay is None:
        return {"error": "Simulation mode not enabled"}
    
    simulation_replay.stop_replay()
    return {"status": "stopped"}

@app.get("/simulation/status")
async def simulation_status():
    """Get simulation status."""
    if not SIMULATION_MODE:
        return {"mode": "live", "simulation_enabled": False}
    
    return {
        "mode": "simulation",
        "simulation_enabled": True,
        "data_loaded": simulation_replay is not None,
        "is_running": simulation_replay.is_running if simulation_replay else False,
        "timeline_events": len(simulation_replay.timeline) if simulation_replay else 0
    }

@app.get("/api/face-images/{person_id}")
async def get_face_image(person_id: str):
    """Serve face images."""
    from fastapi.responses import FileResponse, Response
    import os
    
    # Get person details
    person = face_db.get_person(person_id)
    if not person:
        return {"error": "Person not found"}
    
    image_path = person.get("image_path", "")
    
    # If image_path is relative, try to resolve it
    if image_path and not image_path.startswith("/"):
        # Check if it's in face_images_db/images
        full_path = os.path.join(face_db.images_dir, os.path.basename(image_path))
        if os.path.exists(full_path):
            return FileResponse(full_path, media_type="image/jpeg")
        
        # Check simulation_data/faces
        sim_faces_path = os.path.join("simulation_data", "faces", os.path.basename(image_path))
        if os.path.exists(sim_faces_path):
            return FileResponse(sim_faces_path, media_type="image/jpeg")
    
    # Fallback: return placeholder image
    from PIL import Image
    import io
    
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
    
    # Get port from environment or default to 8000
    port = int(os.getenv("BACKEND_PORT", "8000"))
    host = os.getenv("BACKEND_HOST", "0.0.0.0")
    
    uvicorn.run(app, host=host, port=port)