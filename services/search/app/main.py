import hashlib
import time
import os
import struct

import numpy as np
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from pydantic import BaseModel
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
    return {"status": "ok", "service": "search"}


def pseudo_embed(text: str, dim: int) -> np.ndarray:
    h = hashlib.sha256(text.encode("utf-8")).digest()
    seed = struct.unpack("!I", h[:4])[0]
    rng = np.random.default_rng(seed)
    v = rng.standard_normal(dim).astype("float32")
    v /= np.linalg.norm(v) + 1e-9
    return v


@app.post("/search")
def search(payload: SearchIn):
    try:
        vec = pseudo_embed(payload.query[:4000], VECTOR_DIM).tolist()
        last_error: Exception | None = None
        for _ in range(10):
            try:
                res = client.search(
                    collection_name=COLL,
                    query_vector=vec,
                    limit=payload.top_k,
                )
                break
            except Exception as exc:  # pragma: no cover - network
                last_error = exc
                time.sleep(2)
        else:
            raise last_error or RuntimeError("Search backend unavailable")
        items = []
        for r in res:
            p = r.payload or {}
            items.append(
                {
                    "score": r.score,
                    "chunk_id": p.get("chunk_id"),
                    "source_id": p.get("source_id"),
                }
            )
        return JSONResponse({"count": len(items), "items": items})
    except Exception as exc:  # pragma: no cover - safety net
        return JSONResponse({"count": 0, "items": [], "warning": str(exc)})
