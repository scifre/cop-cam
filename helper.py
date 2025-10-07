import numpy as np
import torch
import cv2  
from torchvision import transforms
from facenet_pytorch import InceptionResnetV1
from insightface.utils import face_align
import torch.nn.functional as F
import lancedb


device = torch.device('cuda:0' if torch.cuda.is_available() else 'cpu')
model = InceptionResnetV1(pretrained="vggface2").eval().to(device)


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
        return "Uknown-Unknown", distance
    
def get_face_embeddings(aligned_faces):
    """
    Runs FaceNet on all aligned faces in a single batch.
    Returns: numpy array [N, 512] normalized
    """
    if not aligned_faces:
        return np.array([])

    face_tensors = [transform(face) for face in aligned_faces]
    batched_tensor = torch.stack(face_tensors).to(device)

    with torch.no_grad():
        embeddings = model(batched_tensor)
        embeddings = F.normalize(embeddings, p=2, dim=1).cpu().numpy()

    return embeddings

def align_faces(frame, landmarks):
    aligned_faces = []
    for lm in landmarks:
        if lm is None:
            continue
        aligned_face = face_align.norm_crop(frame, lm, image_size=224)
        aligned_face = cv2.resize(aligned_face, (160, 160))
        aligned_face = cv2.cvtColor(aligned_face, cv2.COLOR_BGR2RGB)
        aligned_faces.append(aligned_face)
    return aligned_faces

def batch_vector_search(embeddings, threshold):
    """
    Runs batched similarity search in LanceDB using IVF_FLAT with tuned params.
    Uses cosine distance (lower is better). Returns list of (card_no, similarity).
    Also echoes close matches back into the table with a date suffix (non-Unknown only).
    """

    if embeddings is None or len(embeddings) == 0:
        return []

    # Normalize input shape to (N, 512) numpy
    if isinstance(embeddings, list):
        emb_np = np.asarray(embeddings, dtype=np.float32)
    else:
        emb_np = np.array(embeddings, dtype=np.float32, copy=False)
    if emb_np.ndim == 1:
        emb_np = emb_np.reshape(1, -1)

    # Safety: empty or wrong last dim
    if emb_np.size == 0 or emb_np.shape[-1] != 512:
        print(f"Warning: invalid embeddings array shape: {emb_np.shape}")
        return []

    
    try:
        results = (
            face_table
            .search(emb_np, vector_column_name="embedding")
            .metric("cosine")        
            .select(["label", "_distance"])
            .limit(1)
            .to_list()
        )
    except Exception as e:
        print(f"LanceDB search error: {e}")
        return []

    # Prepare outputs + optional echo-back writes
    identity_results = []
    
    for i, res in enumerate(results):
        label = res.get("label")
        sim = res.get("_distance")

        # Defensive defaults
        if label is None or sim is None:
            identity_results.append(("Unknown", float("inf")))
            continue

        # Decide identity
        if sim < threshold:
            name = label.split("-")[0]
        else:
            name = "Unknown"

        identity_results.append((name, sim))
    return identity_results

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