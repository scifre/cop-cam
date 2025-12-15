from typing import List
from models import Detection

class DB:
    def __init__(self):
        self.detections: List[Detection] = []
    
    def add(self, det: Detection):
        self.detections.append(det)
    
    def get_all(self):
        return self.detections

db = DB()