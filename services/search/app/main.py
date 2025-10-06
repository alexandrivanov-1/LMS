import hashlib
import os
import re
import struct
from datetime import date
from typing import Any, Dict, List, Optional

import numpy as np
import psycopg
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from psycopg.rows import dict_row
from qdrant_client import QdrantClient

from .graph_build import build_graph, get_subgraph

app = FastAPI(title="search")
QDRANT_URL = os.getenv("QDRANT_URL", "http://qdrant:6333")
VECTOR_DIM = int(os.getenv("VECTOR_DIM", "768"))
COLL = "chunks"
EMBEDDINGS_KIND = os.getenv("INDEXER_EMBEDDINGS", "onnx").lower()
DSN = os.getenv("POSTGRES_DSN")

if EMBEDDINGS_KIND not in {"onnx", "pseudo"}:
    raise RuntimeError("INDEXER_EMBEDDINGS must be either 'onnx' or 'pseudo'")

client = QdrantClient(url=QDRANT_URL)
TOKENIZER = re.compile(r"\w+", re.UNICODE)

try:  # pragma: no cover - optional dependency
    import onnxruntime as ort  # type: ignore
except ImportError:  # pragma: no cover - runtime handled below
    ort = None


def _load_session() -> Optional["ort.InferenceSession"]:
    if EMBEDDINGS_KIND != "onnx":
        return None
    if ort is None:
        raise RuntimeError("onnxruntime must be installed for ONNX embeddings")
    model_path = os.path.join(os.path.dirname(__file__), "models", "hash_normalizer.onnx")
    if not os.path.exists(model_path):
        raise RuntimeError("hash_normalizer.onnx is missing in search service")
    return ort.InferenceSession(model_path, providers=["CPUExecutionProvider"])


SESSION = _load_session()


class SearchIn(BaseModel):
    query: str
    as_of: Optional[str] = None
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
        raise RuntimeError("ONNX session is not initialised")
    features = hashed_features(text)
    if not np.any(features):
        return features
    input_name = SESSION.get_inputs()[0].name
    output = SESSION.run(None, {input_name: features.reshape(1, -1)})[0][0]
    return output.astype("float32")


def embed_query(text: str) -> List[float]:
    truncated = (text or "")[:4000]
    if EMBEDDINGS_KIND == "onnx":
        return onnx_embed(truncated).tolist()
    return pseudo_embed(truncated, VECTOR_DIM).tolist()


def _parse_date(value: Optional[str]) -> Optional[date]:
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid as_of date format") from exc


def _db_conn():
    if not DSN:
        raise RuntimeError("POSTGRES_DSN is required for search service")
    return psycopg.connect(DSN, row_factory=dict_row)


def _compose_norm_ref(row: Dict[str, Any]) -> Optional[str]:
    segments = []
    if row.get("law"):
        segments.append(row["law"])
    if row.get("article"):
        segments.append(f"статья {row['article']}")
    if row.get("part"):
        segments.append(f"часть {row['part']}")
    if row.get("point"):
        segments.append(f"пункт {row['point']}")
    if row.get("subpoint"):
        segments.append(f"подпункт {row['subpoint']}")
    return ", ".join(segments) if segments else None


def _fetch_chunk_metadata(chunk_ids: List[str]) -> Dict[str, Dict[str, Any]]:
    if not chunk_ids:
        return {}
    with _db_conn() as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT c.id::text AS chunk_id,
                   c.page,
                   c.slide,
                   c.timecode,
                   c.valid_from,
                   c.valid_to,
                   c.source_id::text AS source_id,
                   n.id::text AS norm_unit_id,
                   n.law,
                   n.article,
                   n.part,
                   n.point,
                   n.subpoint
            FROM chunk AS c
            LEFT JOIN norm_unit AS n ON c.norm_unit_id = n.id
            WHERE c.id::text = ANY(%s)
            """,
            (chunk_ids,),
        )
        rows = cur.fetchall()
    return {row["chunk_id"]: row for row in rows}


def _within_interval(as_of: Optional[date], start: Optional[str], end: Optional[str]) -> bool:
    if as_of is None:
        return True
    valid_from = _parse_date(start)
    valid_to = _parse_date(end) if end else None
    if valid_from and valid_from > as_of:
        return False
    if valid_to and valid_to < as_of:
        return False
    return True


@app.post("/search")
def search(payload: SearchIn):
    query_vec = embed_query(payload.query)
    results = client.search(
        collection_name=COLL,
        query_vector=query_vec,
        limit=payload.top_k,
        with_payload=True,
    )
    as_of_date = _parse_date(payload.as_of) if payload.as_of else None
    selected = []
    chunk_ids: List[str] = []
    for item in results:
        payload_data = item.payload or {}
        valid_from = payload_data.get("valid_from")
        valid_to = payload_data.get("valid_to")
        if not _within_interval(as_of_date, valid_from, valid_to):
            continue
        chunk_id = payload_data.get("chunk_id") or (str(item.id) if item.id else None)
        if not chunk_id:
            continue
        chunk_ids.append(chunk_id)
        selected.append((item, payload_data, chunk_id))
    meta = _fetch_chunk_metadata(chunk_ids)
    items: List[Dict[str, Any]] = []
    for item, payload_data, chunk_id in selected:
        chunk_meta = meta.get(chunk_id, {})
        norm_ref = _compose_norm_ref(chunk_meta)
        citations = []
        if chunk_meta:
            citations.append(
                {
                    "norm_unit_id": chunk_meta.get("norm_unit_id"),
                    "norm_ref": norm_ref,
                    "chunk": {
                        "chunk_id": chunk_id,
                        "page": chunk_meta.get("page"),
                        "slide": chunk_meta.get("slide"),
                        "timecode": chunk_meta.get("timecode"),
                    },
                }
            )
        items.append(
            {
                "score": item.score,
                "chunk_id": chunk_id,
                "source_id": payload_data.get("source_id") or chunk_meta.get("source_id"),
                "norm_ref": norm_ref,
                "valid_from": payload_data.get("valid_from"),
                "valid_to": payload_data.get("valid_to"),
                "citations": citations,
            }
        )
    return JSONResponse({"count": len(items), "items": items})


@app.post("/graph/rebuild")
def graph_rebuild():
    build_graph()
    return {"status": "ok"}


@app.get("/graph")
def graph(node_id: str = Query(..., description="ID узла"), depth: int = Query(1, ge=1, le=5)):
    data = get_subgraph(node_id, depth)
    if not data["nodes"]:
        raise HTTPException(status_code=404, detail="Node not found")
    return data
