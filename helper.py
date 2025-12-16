import numpy as np
import torch
import cv2  
from torchvision import transforms
from insightface.model_zoo import get_model
from insightface.utils import face_align
import torch.nn.functional as F
import lancedb


device = torch.device('cuda:0' if torch.cuda.is_available() else 'cpu')

# Note: This model is only used in get_face_embeddings() function
# test.py uses FaceAnalysis directly, so this model may not be needed
# If you need to use get_face_embeddings(), ensure InsightFace model is downloaded first
import os
model_path = os.path.expanduser("~/.insightface/models/buffalo_l/w600k_r50.onnx")

# Initialize model only if path exists, otherwise set to None
# InsightFace will auto-download models when using FaceAnalysis
if os.path.exists(model_path):
    model = get_model(name=model_path, providers=['CUDAExecutionProvider', 'CPUExecutionProvider'])
else:
    model = None  # Model not available - use FaceAnalysis instead for embeddings


db = lancedb.connect("face_db")
face_table = db.open_table("face_data")

transform = transforms.Compose([
    transforms.ToTensor(),  # Converts PIL/numpy to tensor and scales to [0,1]
    transforms.Normalize(mean=[0.5, 0.5, 0.5], std=[0.5, 0.5, 0.5])  # Scales to [-1,1]
    ])

def find_best_match(face_table, face_embedding, threshold=0.4):
    face_embedding = np.asarray(face_embedding).flatten()
    result = face_table.search(face_embedding, vector_column_name="embedding").metric("cosine").limit(1).to_list()[0]
    label = result.get("label")
    distance = result.get("_distance")

    if distance <threshold:
        return label, distance
    else:
        return "Unknown-Unknown", distance
    
def get_face_embeddings(aligned_faces):
    """
    aligned_faces: list of 112x112 BGR numpy images
    returns: [N, 512] normalized
    Note: This function requires model to be initialized. 
    If model is None, use FaceAnalysis.get() instead (as done in test.py)
    """
    if model is None:
        raise ValueError("Model not initialized. Use FaceAnalysis for embeddings instead.")
    if len(aligned_faces) == 0:
        return np.empty((0, 512))

    embeddings = model.get(aligned_faces)  # ✅ correct
    embeddings = embeddings / np.linalg.norm(embeddings, axis=1, keepdims=True)

    return embeddings

def align_faces(frame, landmarks):
    aligned_faces = []
    for lm in landmarks:
        if lm is None:
            continue
        aligned_face = face_align.norm_crop(frame, lm, image_size=112)
        aligned_face = cv2.cvtColor(aligned_face, cv2.COLOR_BGR2RGB)
        aligned_faces.append(aligned_face)
    return aligned_faces

def vector_search(embedding, threshold):
    if embedding is None:
        return ("Unknown", float("inf"))

    emb = np.asarray(embedding, dtype=np.float32)
    if emb.ndim != 1 or emb.shape[0] != 512:
        print(f"Invalid embedding shape: {emb.shape}")
        return ("Unknown", float("inf"))

    try:
        res = (
            face_table
            .search(emb, vector_column_name="embedding")
            .metric("cosine")
            .select(["label", "_distance"])
            .limit(1)
            .to_list()
        )
    except Exception as e:
        print(f"LanceDB search error: {e}")
        return ("Unknown", float("inf"))

    if not res:
        return ("Unknown", float("inf"))

    label = res[0]["label"]
    dist = res[0]["_distance"]

    if label is None or dist is None or dist >= threshold:
        return ("unknown", dist)

    return (label, dist)

def prepare_deepsort_inputs(face_bboxes, identity_results):
    """
    Prepares input list for DeepSORT tracker.
    Returns: list of (bbox, score, card_no)
    """
    identities = []
    for (x1, y1, x2, y2, conf), (card_no, score) in zip(face_bboxes, identity_results):
        w, h = x2 - x1, y2 - y1
        identities.append(([x1, y1, w, h], score, card_no))
    return identities