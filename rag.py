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


def query_rag(query):
    q_emb = model.encode([query])
    q_emb_np = np.array(q_emb, dtype="float32")
    _, indices = index.search(q_emb_np, k=1)
    return actions[indices[0][0]]
