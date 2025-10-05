from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.responses import JSONResponse
import os, hashlib, struct, numpy as np
from qdrant_client import QdrantClient

app = FastAPI(title="search")
QDRANT_URL = os.getenv("QDRANT_URL", "http://qdrant:6333")
VECTOR_DIM = int(os.getenv("VECTOR_DIM", "768"))
COLL = "chunks"
client = QdrantClient(url=QDRANT_URL)

class SearchIn(BaseModel):
    query: str
    as_of: str | None = None
    top_k: int = 5

@app.get("/health")
def health():
    return {"status":"ok","service":"search"}

def pseudo_embed(text: str, dim: int) -> np.ndarray:
    h = hashlib.sha256(text.encode("utf-8")).digest()
    seed = struct.unpack("!I", h[:4])[0]
    rng = np.random.default_rng(seed)
    v = rng.standard_normal(dim).astype("float32")
    v /= np.linalg.norm(v) + 1e-9
    return v

@app.post("/search")
def search(payload: SearchIn):
    vec = pseudo_embed(payload.query[:4000], VECTOR_DIM).tolist()
    res = client.search(collection_name=COLL, query_vector=vec, limit=payload.top_k)
    items = []
    for r in res:
        p = r.payload or {}
        items.append({
            "score": r.score,
            "chunk_id": p.get("chunk_id"),
            "source_id": p.get("source_id"),
        })
    return JSONResponse({"count": len(items), "items": items})
