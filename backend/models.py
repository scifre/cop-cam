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
    person_id: Optional[str] = None
    person_name: Optional[str] = None
    person_image: Optional[str] = None
    crime: Optional[str] = None

class Detection(DetectionCreate):
    id: int