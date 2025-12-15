import warnings
warnings.filterwarnings("ignore", category=FutureWarning)
import cv2
import os
from insightface.model_zoo import get_model
from deep_sort_realtime.deepsort_tracker import DeepSort
from collections import defaultdict, Counter
from helper import align_faces, get_face_embeddings, batch_vector_search, prepare_deepsort_inputs
import requests
from datetime import datetime
import sys

# Add backend directory to path to import face_database
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from face_database import face_db

API_URL = "http://localhost:8000/report-detection"

CAMERA_CONFIG = {
    "cam_01": {"lat": 21.13, "lng": 81.77},
    "cam_02": {"lat": 21.135, "lng": 81.775},
}

CURRENT_CAM = "cam_01"

detector = get_model(
    name="/home/scifre/.insightface/models/buffalo_s/det_500m.onnx",
    providers=['CUDAExecutionProvider', 'CPUExecutionProvider']
)
detector.prepare(ctx_id=0, input_size=(640, 640))
tracker = DeepSort(max_age=20, max_cosine_distance=0.6, max_iou_distance=0.8)

video_path = "video_4.mp4"
cap = cv2.VideoCapture(video_path)
prediction_dict = defaultdict(list)
track_frames = defaultdict(list)  # Store frames for each track_id

with open("poi.txt", "r") as f:
    poi = [line.strip() for line in f.readlines()]

def save_face_image(frame, bbox, person_id, camera_id):
    """Extract and save face image."""
    t, l, b, r = map(int, bbox)
    # Add padding
    padding = 20
    t = max(0, t - padding)
    l = max(0, l - padding)
    b = min(frame.shape[0], b + padding)
    r = min(frame.shape[1], r + padding)
    
    face_crop = frame[t:b, l:r]
    filename = f"{person_id}_{camera_id}.jpg"
    filepath = os.path.join(face_db.images_dir, filename)
    cv2.imwrite(filepath, face_crop)
    
    # Return relative path for API
    return f"/api/face-images/{person_id}"

def get_person_id(name, category):
    """Generate or retrieve person_id for a given name."""
    # Check if person already exists in database
    for person_id, person_data in face_db.database.items():
        if person_data.get("name") == name and person_data.get("category") == category:
            return person_id
    
    # Generate new person_id
    import random
    prefix = "POLICE" if category == "A" else "CRIM"
    # Use a simple counter based on existing entries
    existing_ids = [pid for pid in face_db.database.keys() if pid.startswith(prefix)]
    num = len(existing_ids) + 1
    person_id = f"{prefix}_{num:03d}"
    
    return person_id

def send_detection(name, score, frame, bbox, track_id):
    cat = "B" if name in poi else "A"
    timestamp = datetime.now().isoformat()
    
    # Get or create person_id
    person_id = get_person_id(name, category=cat)
    
    # Save face image if not already saved for this person
    person = face_db.get_person(person_id)
    image_path = ""
    
    if not person:
        # Save face image and create person entry
        image_path = save_face_image(frame, bbox, person_id, CURRENT_CAM)
        crime = "Unknown" if cat == "B" else "N/A"
        face_db.add_person(
            person_id=person_id,
            name=name,
            category=cat,
            image_path=image_path,
            crime=crime
        )
    else:
        image_path = person.get("image_path", "")
    
    # Update last seen
    face_db.update_last_seen(person_id, timestamp)
    
    data = {
        "detected": True,
        "category": cat,
        "camera_id": CURRENT_CAM,
        "timestamp": timestamp,
        "coords": CAMERA_CONFIG[CURRENT_CAM],
        "person_id": person_id,
        "person_name": name,
        "person_image": image_path,
        "crime": face_db.get_person(person_id).get("crime") if cat == "B" else "N/A"
    }
    
    try:
        requests.post(API_URL, json=data)
        print(f"Sent: {name} ({cat}) - Score: {score:.2f} - Person ID: {person_id}")
    except Exception as e:
        print(f"API Error: {e}")

while cap.isOpened():
    ret, frame = cap.read()
    if not ret:
        break
    
    boxes, landmarks = detector.detect(frame)
    aligned_faces = align_faces(frame, landmarks)
    embeddings = get_face_embeddings(aligned_faces)
    identity_results = batch_vector_search(embeddings, threshold=0.40)
    identities = prepare_deepsort_inputs(boxes, identity_results)
    tracks = tracker.update_tracks(identities, frame=frame)
    
    for track in tracks:
        if not track.is_confirmed():
            continue
        
        name = track.det_class
        score = track.get_det_conf()
        track_id = track.track_id
        t, l, b, r = map(int, track.to_tlbr())
        
        prediction_dict[track_id].append(name)
        
        if len(prediction_dict[track_id]) >= 10:
            counter = Counter(prediction_dict[track_id])
            prediction = counter.most_common(1)[0][0]
            
            # Store frame for this track (for face image extraction)
            track_frames[track_id] = frame
            
            send_detection(prediction, score if score else 0.0, frame, [t, l, b, r], track_id)
            
            cv2.rectangle(frame, (t, l), (b, r), (0, 255, 0), 2)
            if score is not None:
                cv2.putText(frame, f"{prediction}-{score:.2f}", (t, l - 10),
                          cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
            else:
                cv2.putText(frame, f"{prediction}", (t, l - 10),
                          cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
        
        prediction_dict[track_id] = prediction_dict[track_id][-10:]
    
    cv2.imshow('Video', frame)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()