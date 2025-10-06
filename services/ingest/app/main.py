import hashlib
import io
import json
import os
import uuid

import psycopg
from fastapi import FastAPI, File, UploadFile
from fastapi.responses import JSONResponse
from minio import Minio

app = FastAPI(title="ingest")

MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "http://minio:9000")
endpoint = MINIO_ENDPOINT.replace("http://","").replace("https://","")
client = Minio(
    endpoint,
    access_key=os.getenv("MINIO_ACCESS_KEY"),
    secret_key=os.getenv("MINIO_SECRET_KEY"),
    secure=MINIO_ENDPOINT.startswith("https://")
)
BUCKET = os.getenv("MINIO_BUCKET", "sources")
DSN = os.getenv("POSTGRES_DSN")


@app.get("/health")
def health():
    return {"status":"ok","service":"ingest"}


@app.post("/ingest/upload")
async def upload(files: list[UploadFile] = File(...)):
    saved = []
    with psycopg.connect(DSN) as conn:
        with conn.cursor() as cur:
            for f in files:
                data = await f.read()
                sha = hashlib.sha256(data).hexdigest()
                obj = f"{uuid.uuid4()}_{f.filename}"
                ctype = f.content_type or "application/octet-stream"
                client.put_object(BUCKET, obj, io.BytesIO(data), length=len(data), content_type=ctype)
                meta = {
                    "bucket": BUCKET,
                    "object": obj,
                    "size": len(data),
                    "content_type": ctype,
                    "hash_sha256": sha,
                    "status": "uploaded"
                }
                cur.execute(
                  """
                  INSERT INTO source(kind,title,origin_url,license,owner,hash,valid_from,valid_to,meta)
                  VALUES ('file', %s, NULL, NULL, NULL, %s, NULL, NULL, %s)
                  RETURNING id
                  """,
                  (f.filename, sha, json.dumps(meta, ensure_ascii=False)),
                )
                source_id = cur.fetchone()[0]
                saved.append({"source_id": str(source_id), "object": obj, "size": len(data)})
            conn.commit()
    return JSONResponse({"accepted": len(saved), "items": saved})
