#!/usr/bin/env python3
"""
Script to process face images from new_photos/ directory and add them to the face database.
This uses the same InsightFace method as test.py for consistency.
"""

import os
import cv2
import numpy as np
from insightface.app import FaceAnalysis
import lancedb
from pathlib import Path

# Initialize InsightFace (same as test.py)
print("Loading InsightFace model...")
app = FaceAnalysis(providers=["CUDAExecutionProvider", "CPUExecutionProvider"], 
                  allowed_modules=["detection", "recognition"])
app.prepare(ctx_id=0, det_size=(640, 640))
print("✓ InsightFace loaded")

# Connect to database
print("Connecting to face database...")
db = lancedb.connect("face_db")
face_table = db.open_table("face_data")
print("✓ Database connected")

def process_image(image_path, person_name, image_name):
    """
    Process a single image and return embedding with label.
    Returns (label, embedding) or None if face not detected.
    """
    img = cv2.imread(str(image_path))
    if img is None:
        print(f"  ⚠ Could not read image: {image_path}")
        return None
    
    # Detect faces
    faces = app.get(img)
    if len(faces) == 0:
        print(f"  ⚠ No face detected in: {image_path}")
        return None
    
    # Use first face found
    face = faces[0]
    embedding = face.embedding  # 512-dimensional embedding from InsightFace
    
    # Use person name as label (e.g., "ayush", "kanika")
    # Multiple images of the same person will have the same label
    # This allows the system to match any image of that person
    label = person_name
    
    return (label, embedding)

def process_directory(new_photos_dir="new_photos"):
    """
    Process all images in new_photos/ directory structure.
    Expected structure: new_photos/person_name/image_files
    """
    new_photos_path = Path(new_photos_dir)
    
    if not new_photos_path.exists():
        print(f"Error: Directory '{new_photos_dir}' not found!")
        return
    
    print(f"\nProcessing images from '{new_photos_dir}/'...")
    print("=" * 60)
    
    total_processed = 0
    total_added = 0
    total_failed = 0
    
    # Process each person's directory
    for person_dir in sorted(new_photos_path.iterdir()):
        if not person_dir.is_dir():
            continue
        
        person_name = person_dir.name
        print(f"\nProcessing: {person_name}/")
        
        # Get all image files
        image_files = []
        for ext in ['*.jpg', '*.jpeg', '*.png', '*.JPG', '*.JPEG', '*.PNG']:
            image_files.extend(person_dir.glob(ext))
        
        if len(image_files) == 0:
            print(f"  ⚠ No images found in {person_name}/")
            continue
        
        embeddings_to_add = []
        
        for image_path in sorted(image_files):
            total_processed += 1
            print(f"  Processing: {image_path.name}...", end=" ")
            
            result = process_image(image_path, person_name, image_path.name)
            
            if result is None:
                total_failed += 1
                continue
            
            label, embedding = result
            embeddings_to_add.append({
                "label": label,
                "embedding": np.asarray(embedding, dtype=np.float32).flatten()
            })
            print("✓")
        
        # Add all embeddings for this person to database
        if embeddings_to_add:
            try:
                face_table.add(embeddings_to_add)
                total_added += len(embeddings_to_add)
                print(f"  ✓ Added {len(embeddings_to_add)} embeddings to database")
            except Exception as e:
                print(f"  ✗ Error adding to database: {e}")
                total_failed += len(embeddings_to_add)
    
    print("\n" + "=" * 60)
    print("Summary:")
    print(f"  Total images processed: {total_processed}")
    print(f"  Successfully added: {total_added}")
    print(f"  Failed: {total_failed}")
    
    # Show current database size
    try:
        df = face_table.to_pandas()
        print(f"\n  Current database size: {len(df)} embeddings")
        print(f"  Unique labels: {df['label'].nunique()}")
    except Exception as e:
        print(f"\n  Could not query database: {e}")

if __name__ == "__main__":
    print("=" * 60)
    print("Face Database Population Script")
    print("=" * 60)
    
    process_directory("new_photos")
    
    print("\n✓ Done!")
    print("\nYou can now run test.py to use the updated face database.")

