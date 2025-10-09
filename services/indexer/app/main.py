import hashlib
import os
import struct
import time

import numpy as np
import psycopg
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams

app = FastAPI(title="indexer")
DSN = os.getenv("POSTGRES_DSN")
QDRANT_URL = os.getenv("QDRANT_URL", "http://qdrant:6333")
VECTOR_DIM = int(os.getenv("VECTOR_DIM", "768"))
COLL = "chunks"

client = QdrantClient(url=QDRANT_URL)


@app.get("/health")
def health():
    return {"status": "ok", "service": "indexer"}


def pseudo_embed(text: str, dim: int) -> np.ndarray:
    """Deterministic embedding without external models."""
    h = hashlib.sha256(text.encode("utf-8")).digest()
    seed = struct.unpack("!I", h[:4])[0]
    rng = np.random.default_rng(seed)
    v = rng.standard_normal(dim).astype("float32")
    v /= np.linalg.norm(v) + 1e-9
    return v


def ensure_collection():
    last_error: Exception | None = None
    for _ in range(5):
        try:
            cols = [c.name for c in client.get_collections().collections]
            if COLL not in cols:
                client.recreate_collection(
                    collection_name=COLL,
                    vectors_config=VectorParams(
                        size=VECTOR_DIM, distance=Distance.COSINE
                    ),
                )
            return
        except Exception as exc:  # pragma: no cover - network
            last_error = exc
            time.sleep(2)
    raise last_error or RuntimeError("Unable to ensure Qdrant collection")


@app.post("/indexer/run")
def run(limit: int = 1000):
    ensure_collection()
    points = []
    with psycopg.connect(DSN) as conn, conn.cursor() as cur:
        cur.execute(
            """
          SELECT id, source_id, text
          FROM chunk
          ORDER BY id DESC
          LIMIT %s
          """,
            (limit,),
        )
        for cid, sid, txt in cur.fetchall():
            vec = pseudo_embed((txt or "")[:4000], VECTOR_DIM).tolist()
            payload = {
                "chunk_id": str(cid),
                "source_id": str(sid),
                "valid_from": None,
                "valid_to": None,
            }
            points.append(PointStruct(id=str(cid), vector=vec, payload=payload))
    if points:
        last_error: Exception | None = None
        for _ in range(5):
            try:
                client.upsert(collection_name=COLL, points=points)
                break
            except Exception as exc:  # pragma: no cover - network
                last_error = exc
                time.sleep(2)
        else:
            raise last_error or RuntimeError("Unable to upsert into Qdrant")
    return JSONResponse({"upserted": len(points)})
