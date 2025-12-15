from pydantic import BaseModel
from typing import Optional

class Coords(BaseModel):
    lat: float
    lng: float

class DetectionCreate(BaseModel):
    detected: bool
    category: str
    camera_id: str
    timestamp: Optional[str] = None
    coords: Coords

class Detection(DetectionCreate):
    id: int