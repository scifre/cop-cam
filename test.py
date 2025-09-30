import warnings

warnings.filterwarnings("ignore", category=FutureWarning)
from facenet_pytorch import InceptionResnetV1
import cv2
import torch
from insightface.app import FaceAnalysis
from insightface.utils import face_align
import torch.nn.functional as F
from deep_sort_realtime.deepsort_tracker import DeepSort
from collections import defaultdict, Counter
import json
from urllib.parse import quote
import subprocess
import numpy as np
from torchvision import transforms
from PIL import Image
import os
import lancedb
import pyarrow as pa
from helper import find_best_match

db = lancedb.connect("face_db")

face_table = db.open_table("face_data")


transform = transforms.Compose([
    transforms.ToTensor(),  # Converts PIL/numpy to tensor and scales to [0,1]
    transforms.Normalize(mean=[0.5, 0.5, 0.5], std=[0.5, 0.5, 0.5])  # Scales to [-1,1]
    ])


app = FaceAnalysis(providers=["CUDAExecutionProvider", "CPUExecutionProvider"])
app.prepare(ctx_id=0, det_size=(640, 640))

model = InceptionResnetV1(pretrained="vggface2").eval().to("cuda")

video_path = "VID_20250915_155804628.mp4"

cap = cv2.VideoCapture(video_path)

while cap.isOpened():
    ret, frame = cap.read()
    if not ret:
        break

    faces = app.get(frame)



    for face in faces:
        box = face.bbox.astype(int)

        aligned_face = face_align.norm_crop(frame, face.kps, image_size=224)
        aligned_face = cv2.resize(aligned_face, (160, 160))
        aligned_face = cv2.cvtColor(aligned_face, cv2.COLOR_BGR2RGB)
        
        face_tensor = transform(aligned_face).unsqueeze(0)

        embedding = model(face_tensor.to("cuda"))
        embedding = F.normalize(embedding, p=2, dim=1).cpu().detach().numpy()

        label, distance = find_best_match(face_table, embedding)

        name, pose = label.split("-")
        if name == "ayush":
            text_color = (0,0, 255)
        else:
            text_color = (0, 255, 0)
        cv2.rectangle(frame, (box[0], box[1]), (box[2], box[3]), text_color, 2)
        cv2.putText(frame, name, (box[0], box[1]-10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, text_color, 2)
    cv2.imshow('Video', frame)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break