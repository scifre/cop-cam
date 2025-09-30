import numpy as np

def find_best_match(face_table, face_embedding, threshold=0.6):
    face_embedding = np.asarray(face_embedding).flatten()
    result = face_table.search(face_embedding, vector_column_name="embedding").metric("cosine").limit(1).to_list()[0]
    label = result.get("label")
    distance = result.get("_distance")

    if distance <threshold:
        return label, distance
    else:
        return "Uknown-Unknown", distance