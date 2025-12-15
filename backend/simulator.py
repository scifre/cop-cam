from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
from typing import List
import asyncio
import json
from models import Detection, DetectionCreate
from database import db

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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

@app.post("/report-detection")
async def report(data: DetectionCreate):
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
    return {"detections": [d.dict() for d in db.detections]}

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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)