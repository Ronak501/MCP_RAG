import json

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

MODEL_NAME = "all-MiniLM-L6-v2"
KNOWLEDGE_PATH = "rag_data/knowledge.json"

model = SentenceTransformer(MODEL_NAME)

with open(KNOWLEDGE_PATH, "r", encoding="utf-8") as f:
    data = json.load(f)

texts = [item["event"] for item in data]
actions = [item["action"] for item in data]

embeddings = model.encode(texts)
embeddings_np = np.array(embeddings, dtype="float32")

index = faiss.IndexFlatL2(embeddings_np.shape[1])
index.add(embeddings_np)


def query_rag(query, return_metadata=False):
    q_emb = model.encode([query])
    q_emb_np = np.array(q_emb, dtype="float32")
    distances, indices = index.search(q_emb_np, k=1)

    best_index = int(indices[0][0])
    best_distance = float(distances[0][0])
    best_action = actions[best_index]
    best_event = texts[best_index]
    similarity = 1.0 / (1.0 + best_distance)

    if return_metadata:
        return {
            "action": best_action,
            "matched_event": best_event,
            "distance": best_distance,
            "similarity": similarity,
        }

    return best_action
