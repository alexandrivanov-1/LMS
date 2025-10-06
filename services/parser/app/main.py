import json
import os

import httpx
import psycopg
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from minio import Minio

app = FastAPI(title="parser")

DSN = os.getenv("POSTGRES_DSN")
TIKA_URL = os.getenv("TIKA_URL", "http://tika:9998")
MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "http://minio:9000")
endpoint = MINIO_ENDPOINT.replace("http://","").replace("https://","")
minio = Minio(
    endpoint,
    access_key=os.getenv("MINIO_ACCESS_KEY"),
    secret_key=os.getenv("MINIO_SECRET_KEY"),
    secure=MINIO_ENDPOINT.startswith("https://")
)
BUCKET = os.getenv("MINIO_BUCKET", "sources")

@app.get("/health")
def health():
    return {"status":"ok","service":"parser"}

def _split(text, size=1000, overlap=100):
    res, i, n = [], 0, len(text)
    while i < n:
        res.append(text[i:i+size])
        i += size - overlap
    return res

@app.post("/parser/scan")
async def scan(limit: int = 5):
    processed = 0
    with psycopg.connect(DSN) as conn:
        conn.autocommit = False
        with conn.cursor() as cur:
            cur.execute(
              """
              SELECT id, meta
              FROM source
              WHERE (meta->>'status') = 'uploaded'
              ORDER BY created_at DESC
              LIMIT %s
              """,
              (limit,),
            )
            rows = cur.fetchall()
            for (sid, meta) in rows:
                obj = meta["object"]
                data = minio.get_object(BUCKET, obj).read()
                async with httpx.AsyncClient(timeout=120.0) as client:
                    r = await client.put(f"{TIKA_URL}/tika", content=data, headers={"Accept": "text/plain"})
                    r.raise_for_status()
                    text = r.text
                parts = _split(text, 1000, 100)
                for p in parts:
                    if not p.strip():
                        continue
                    cur.execute(
                      """
                      INSERT INTO chunk(source_id, norm_unit_id, page, paragraph, slide, timecode, text)
                      VALUES (%s, NULL, NULL, NULL, NULL, NULL, %s)
                      """,
                      (sid, p),
                    )
                new_meta = dict(meta)
                new_meta["status"] = "parsed"
                cur.execute("UPDATE source SET meta=%s WHERE id=%s", (json.dumps(new_meta, ensure_ascii=False), sid))
                processed += 1
            conn.commit()
    return JSONResponse({"processed": processed})
