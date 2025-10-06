import os

import httpx
import psycopg
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

app = FastAPI(title="gateway")
INGEST_URL = os.getenv("INGEST_URL", "http://ingest:8000")
PARSER_URL = os.getenv("PARSER_URL", "http://parser:8000")
INDEXER_URL = os.getenv("INDEXER_URL", "http://indexer:8000")
SEARCH_URL = os.getenv("SEARCH_URL", "http://search:8000")
DSN = os.getenv("POSTGRES_DSN")

@app.get("/health")
def health():
    return {"status":"ok","service":"gateway"}

@app.post("/ingest/upload")
async def proxy_ingest_upload(request: Request):
    form = await request.form()
    files, fields = [], []
    for key, value in form.multi_items():
        if hasattr(value, "filename"):
            files.append(("files", (value.filename, await value.read(), value.content_type)))
        else:
            fields.append((key, str(value)))
    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(f"{INGEST_URL}/ingest/upload", files=files, data=fields)
    return JSONResponse(resp.json(), status_code=resp.status_code)

@app.get("/sources")
def list_sources():
    with psycopg.connect(DSN) as conn, conn.cursor() as cur:
        cur.execute(
          """
          SELECT id, kind, title, created_at, meta
          FROM source
          ORDER BY created_at DESC
          LIMIT 50
          """
        )
        rows = cur.fetchall()
    items = []
    for (id_, kind, title, created_at, meta) in rows:
        items.append({
            "id": str(id_), "kind": kind, "title": title,
            "created_at": created_at.isoformat(), "meta": meta
        })
    return {"items": items}

@app.post("/parser/scan")
async def proxy_parser_scan():
    async with httpx.AsyncClient(timeout=600.0) as client:
        resp = await client.post(f"{PARSER_URL}/parser/scan")
    return JSONResponse(resp.json(), status_code=resp.status_code)

@app.post("/indexer/run")
async def proxy_indexer_run():
    async with httpx.AsyncClient(timeout=600.0) as client:
        resp = await client.post(f"{INDEXER_URL}/indexer/run")
    return JSONResponse(resp.json(), status_code=resp.status_code)

@app.post("/search")
async def proxy_search(request: Request):
    payload = await request.json()
    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(f"{SEARCH_URL}/search", json=payload)
    return JSONResponse(resp.json(), status_code=resp.status_code)
