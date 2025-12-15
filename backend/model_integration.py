import warnings
warnings.filterwarnings("ignore", category=FutureWarning)
import cv2
from insightface.model_zoo import get_model
from deep_sort_realtime.deepsort_tracker import DeepSort
from collections import defaultdict, Counter
from helper import align_faces, get_face_embeddings, batch_vector_search, prepare_deepsort_inputs
import requests
from datetime import datetime

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

with open("poi.txt", "r") as f:
    poi = [line.strip() for line in f.readlines()]

def send_detection(name, score):
    cat = "B" if name in poi else "A"
    
    data = {
        "detected": True,
        "category": cat,
        "camera_id": CURRENT_CAM,
        "timestamp": datetime.now().isoformat(),
        "coords": CAMERA_CONFIG[CURRENT_CAM]
    }
    
    try:
        requests.post(API_URL, json=data)
        print(f"Sent: {name} ({cat}) - Score: {score:.2f}")
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
            
            send_detection(prediction, score if score else 0.0)
            
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