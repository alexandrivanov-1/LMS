import hashlib
import os
import re
import struct
from datetime import date
from typing import Any, Optional

import numpy as np
import psycopg
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams

try:
    import onnxruntime as ort
except ImportError:  # pragma: no cover - handled at runtime
    ort = None

from pathlib import Path


app = FastAPI(title="indexer")
DSN = os.getenv("POSTGRES_DSN")
QDRANT_URL = os.getenv("QDRANT_URL", "http://qdrant:6333")
VECTOR_DIM = int(os.getenv("VECTOR_DIM", "768"))
EMBEDDINGS_KIND = os.getenv("INDEXER_EMBEDDINGS", "onnx").lower()
COLL = "chunks"

if EMBEDDINGS_KIND not in {"onnx", "pseudo"}:
    raise RuntimeError("INDEXER_EMBEDDINGS must be either 'onnx' or 'pseudo'")

if EMBEDDINGS_KIND == "onnx" and VECTOR_DIM != 768:
    raise RuntimeError("ONNX embeddings require VECTOR_DIM to be 768")

client = QdrantClient(url=QDRANT_URL)

TOKENIZER = re.compile(r"\w+", re.UNICODE)


def _load_onnx_session() -> Optional["ort.InferenceSession"]:
    if EMBEDDINGS_KIND != "onnx":
        return None
    if ort is None:
        raise RuntimeError("onnxruntime is required for ONNX embeddings")
    model_path = Path(__file__).resolve().parent / "models" / "hash_normalizer.onnx"
    if not model_path.exists():
        raise RuntimeError(f"ONNX model not found: {model_path}")
    return ort.InferenceSession(str(model_path), providers=["CPUExecutionProvider"])


SESSION = _load_onnx_session()


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


def hashed_features(text: str) -> np.ndarray:
    vec = np.zeros(VECTOR_DIM, dtype="float32")
    if not text:
        return vec
    for token in TOKENIZER.findall(text.lower()):
        digest = hashlib.sha1(token.encode("utf-8")).digest()
        index = int.from_bytes(digest[:4], "big") % VECTOR_DIM
        sign = 1.0 if digest[4] < 128 else -1.0
        weight = 1.0 + int.from_bytes(digest[5:7], "big") / 65535.0
        vec[index] += sign * weight
    return vec


def onnx_embed(text: str) -> np.ndarray:
    if SESSION is None:
        raise RuntimeError("ONNX session is not initialized")
    features = hashed_features(text)
    if not np.any(features):
        return features
    input_name = SESSION.get_inputs()[0].name
    output = SESSION.run(None, {input_name: features.reshape(1, -1)})[0][0]
    return output.astype("float32")


def embed_text(text: str) -> np.ndarray:
    truncated = (text or "")[:4000]
    if EMBEDDINGS_KIND == "onnx":
        return onnx_embed(truncated)
    return pseudo_embed(truncated, VECTOR_DIM)


def _first_not_none(*values: Any) -> Any:
    for value in values:
        if value is not None:
            return value
    return None


def _date_to_iso(value: Optional[Any]) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, date):
        return value.isoformat()
    if hasattr(value, "date"):
        return value.date().isoformat()
    return str(value)


def _compose_norm_ref(
    law: Optional[str],
    article: Optional[str],
    part: Optional[str],
    point: Optional[str],
    subpoint: Optional[str],
) -> Optional[str]:
    if not any([law, article, part, point, subpoint]):
        return None
    segments = []
    if law:
        segments.append(law)
    if article:
        segments.append(f"статья {article}")
    if part:
        segments.append(f"часть {part}")
    if point:
        segments.append(f"пункт {point}")
    if subpoint:
        segments.append(f"подпункт {subpoint}")
    return ", ".join(segments)


def ensure_collection():
    cols = [c.name for c in client.get_collections().collections]
    if COLL not in cols:
        client.recreate_collection(
            collection_name=COLL,
            vectors_config=VectorParams(size=VECTOR_DIM, distance=Distance.COSINE),
        )


@app.post("/indexer/run")
def run(limit: int = 1000):
    ensure_collection()
    points = []
    with psycopg.connect(DSN) as conn, conn.cursor() as cur:
        cur.execute(
            """
          SELECT
            c.id,
            c.source_id,
            c.text,
            c.page,
            c.slide,
            c.timecode,
            c.valid_from AS chunk_valid_from,
            c.valid_to AS chunk_valid_to,
            s.valid_from AS source_valid_from,
            s.valid_to AS source_valid_to,
            n.valid_from AS norm_valid_from,
            n.valid_to AS norm_valid_to,
            n.law,
            n.article,
            n.part,
            n.point,
            n.subpoint
          FROM chunk AS c
          LEFT JOIN source AS s ON c.source_id = s.id
          LEFT JOIN norm_unit AS n ON c.norm_unit_id = n.id
          ORDER BY c.id DESC
          LIMIT %s
          """,
            (limit,),
        )
        for row in cur.fetchall():
            (
                cid,
                sid,
                txt,
                page,
                slide,
                timecode,
                chunk_valid_from,
                chunk_valid_to,
                source_valid_from,
                source_valid_to,
                norm_valid_from,
                norm_valid_to,
                law,
                article,
                part,
                point,
                subpoint,
            ) = row

            vec = embed_text(txt).tolist()

            valid_from = _first_not_none(chunk_valid_from, norm_valid_from, source_valid_from)
            valid_to = _first_not_none(chunk_valid_to, norm_valid_to, source_valid_to)

            payload = {
                "chunk_id": str(cid),
                "source_id": str(sid) if sid else None,
                "norm_ref": _compose_norm_ref(law, article, part, point, subpoint),
                "page": page,
                "slide": slide,
                "timecode": timecode,
                "valid_from": _date_to_iso(valid_from),
                "valid_to": _date_to_iso(valid_to),
            }

            points.append(PointStruct(id=str(cid), vector=vec, payload=payload))
    if points:
        client.upsert(collection_name=COLL, points=points)
    return JSONResponse({"upserted": len(points)})
