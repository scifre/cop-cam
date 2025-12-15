"""
Face Images Database Management

Manages storage and retrieval of face images and person metadata.
"""

import json
import os
from typing import Dict, Optional
from pathlib import Path

FACE_DB_DIR = "face_images_db"
FACE_IMAGES_DIR = os.path.join(FACE_DB_DIR, "images")
FACE_DB_FILE = os.path.join(FACE_DB_DIR, "face_database.json")

# Initialize directories
os.makedirs(FACE_IMAGES_DIR, exist_ok=True)


class FaceDatabase:
    """Manages face images and person metadata."""
    
    def __init__(self):
        self.db_file = FACE_DB_FILE
        self.images_dir = FACE_IMAGES_DIR
        self.load_database()
    
    def load_database(self):
        """Load database from JSON file."""
        if os.path.exists(self.db_file):
            with open(self.db_file, 'r') as f:
                self.database = json.load(f)
        else:
            self.database = {}
            self.save_database()
    
    def save_database(self):
        """Save database to JSON file."""
        with open(self.db_file, 'w') as f:
            json.dump(self.database, f, indent=2)
    
    def add_person(self, person_id: str, name: str, category: str, 
                   image_path: str, crime: str = "Unknown", 
                   additional_info: Optional[Dict] = None):
        """Add or update person in database."""
        self.database[person_id] = {
            "person_id": person_id,
            "name": name,
            "category": category,
            "image_path": image_path,
            "crime": crime,
            "additional_info": additional_info or {},
            "first_seen": None,
            "last_seen": None
        }
        self.save_database()
    
    def get_person(self, person_id: str) -> Optional[Dict]:
        """Get person details by person_id."""
        return self.database.get(person_id)
    
    def update_last_seen(self, person_id: str, timestamp: str):
        """Update last seen timestamp."""
        if person_id in self.database:
            if not self.database[person_id].get("first_seen"):
                self.database[person_id]["first_seen"] = timestamp
            self.database[person_id]["last_seen"] = timestamp
            self.save_database()
    
    def get_all_criminals(self) -> Dict:
        """Get all criminals."""
        return {pid: data for pid, data in self.database.items() 
                if data.get("category") == "B"}
    
    def get_all_police(self) -> Dict:
        """Get all police."""
        return {pid: data for pid, data in self.database.items() 
                if data.get("category") == "A"}


# Global instance
face_db = FaceDatabase()



