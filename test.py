##test

import warnings
from ultralytics import YOLO
warnings.filterwarnings("ignore", category=FutureWarning)
import cv2
from insightface.app import FaceAnalysis
from deep_sort_realtime.deepsort_tracker import DeepSort
from collections import defaultdict, Counter
import torch
from helper import vector_search

device = torch.device('cuda:0' if torch.cuda.is_available() else 'cpu')

#LOADING MODEL 
app = FaceAnalysis(providers=["CUDAExecutionProvider", "CPUExecutionProvider"], allowed_modules=["detection", "recognition"])
app.prepare(ctx_id=0, det_size=(640, 640))

yolo_model = YOLO("yolov8m.pt").to(device)

#LOADING DEEPSORT
tracker = DeepSort(max_age=40, max_cosine_distance=0.6, max_iou_distance=0.8)

#LOADING VIDEO
video_dir = "cctv_videos"
video_name = "loby.mp4"

cap = cv2.VideoCapture(f"{video_dir}/{video_name}")
#cap = cv2.VideoCapture(0)

width  = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
fps    = cap.get(cv2.CAP_PROP_FPS)

fourcc = cv2.VideoWriter_fourcc(*"mp4v")
out = cv2.VideoWriter(f"output_videos/{video_name}", fourcc, fps, (width, height))

prediction_dict = defaultdict(lambda: {
    "name": "unknown",
    "predictions": []
})

with open ("poi.txt", "r") as f:
    poi = [line.strip() for line in f.readlines()]


while cap.isOpened():
    identities = []
    ret, frame = cap.read()
    if not ret:
        break
    clean_frame = frame.copy()
    persons = yolo_model(frame)[0]

    for person in persons.boxes:
        if int(person.cls[0]) == 0:
            x1, y1, x2, y2 = map(int, person.xyxy[0])
            conf = person.conf[0].cpu().numpy()
            #person_frame = frame[y1:y2, x1:x2]
            #identity_results = vector_search(embedding, threshold=0.40)
            identities.append(([x1, y1, x2 - x1, y2 - y1], conf))
    #prepare inputs for deepsort
            
    #update tracker
    tracks = tracker.update_tracks(identities, frame=frame)
    for track in tracks:
        if not track.is_confirmed():
            continue
        track_id = track.track_id
        
        name = prediction_dict[track_id]["name"]
        score = track.get_det_conf()
        
        #print(name, score)
        t, l, b, r = map(int, track.to_tlbr())

        person_center = ((l + r) // 2, (t + b) // 2)


        if name == "unknown":
            person_crop = clean_frame[l:r, t:b]
            if person_crop.size != 0:
                faces = app.get(person_crop)
                if len(faces) != 0:
                    face = faces[0]
                    embedding = face.embedding
                    identity_results = vector_search(embedding, threshold=0.80)
                    name, score = identity_results
                    score = float(score)
                    prediction_dict[track_id]["name"] = name
                    cv2.rectangle(frame, (t, l), (b, r), (255, 0, 0), 2)
                    cv2.putText(frame, f"{name}-{score:.2f}", (t, l - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 2)

        else:
            cv2.rectangle(frame, (t, l), (b, r), (0, 255, 255), 2)
            if score is not None:
                cv2.putText(frame, f"{name}-{score:.2f}", (t, l - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 2)
            else:
                cv2.putText(frame, f"{name}", (t, l - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 2)
    cv2.imshow('Video', frame)
    out.write(frame)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break


cap.release()
out.release()
cv2.destroyAllWindows()