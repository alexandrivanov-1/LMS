import os

import httpx
import psycopg
from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse

app = FastAPI(title="gateway")
INGEST_URL = os.getenv("INGEST_URL", "http://ingest:8000")
PARSER_URL = os.getenv("PARSER_URL", "http://parser:8000")
INDEXER_URL = os.getenv("INDEXER_URL", "http://indexer:8000")
SEARCH_URL = os.getenv("SEARCH_URL", "http://search:8000")
MASK_URL = os.getenv("MASK_URL", "http://mask:8000")
DSN = os.getenv("POSTGRES_DSN")


@app.get("/health")
def health():
    return {"status": "ok", "service": "gateway"}


@app.post("/ingest/upload")
async def proxy_ingest_upload(request: Request):
    form = await request.form()
    files, fields = [], []
    for key, value in form.multi_items():
        if hasattr(value, "filename"):
            files.append(
                ("files", (value.filename, await value.read(), value.content_type))
            )
        else:
            fields.append((key, str(value)))
    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(
            f"{INGEST_URL}/ingest/upload", files=files, data=fields
        )
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
    for id_, kind, title, created_at, meta in rows:
        items.append(
            {
                "id": str(id_),
                "kind": kind,
                "title": title,
                "created_at": created_at.isoformat(),
                "meta": meta,
            }
        )
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


async def _proxy_mask(method: str, path: str, request: Request):
    async with httpx.AsyncClient(timeout=60.0) as client:
        if method == "get":
            resp = await client.get(
                f"{MASK_URL}{path}", params=dict(request.query_params)
            )
        elif method in {"post", "patch"}:
            body = await request.json()
            resp = await client.request(method, f"{MASK_URL}{path}", json=body)
        elif method == "delete":
            resp = await client.delete(f"{MASK_URL}{path}")
        else:  # pragma: no cover - defensive
            raise ValueError(f"Unsupported method {method}")
    if not resp.content:
        return Response(status_code=resp.status_code)
    return JSONResponse(resp.json(), status_code=resp.status_code)


@app.get("/atoms")
async def gateway_atoms(request: Request):
    return await _proxy_mask("get", "/atoms", request)


@app.post("/atoms")
async def gateway_atoms_create(request: Request):
    return await _proxy_mask("post", "/atoms", request)


@app.patch("/atoms/{atom_id}")
async def gateway_atoms_update(atom_id: str, request: Request):
    return await _proxy_mask("patch", f"/atoms/{atom_id}", request)


@app.delete("/atoms/{atom_id}")
async def gateway_atoms_delete(atom_id: str, request: Request):
    return await _proxy_mask("delete", f"/atoms/{atom_id}", request)


@app.get("/contexts")
async def gateway_contexts(request: Request):
    return await _proxy_mask("get", "/contexts", request)


@app.post("/contexts")
async def gateway_contexts_create(request: Request):
    return await _proxy_mask("post", "/contexts", request)


@app.patch("/contexts/{context_id}")
async def gateway_contexts_update(context_id: str, request: Request):
    return await _proxy_mask("patch", f"/contexts/{context_id}", request)


@app.delete("/contexts/{context_id}")
async def gateway_contexts_delete(context_id: str, request: Request):
    return await _proxy_mask("delete", f"/contexts/{context_id}", request)


@app.get("/graph")
async def gateway_graph(node_id: str, depth: int = 1):
    async with httpx.AsyncClient(timeout=180.0) as client:
        await client.post(f"{SEARCH_URL}/graph/rebuild")
        resp = await client.get(
            f"{SEARCH_URL}/graph", params={"node_id": node_id, "depth": depth}
        )
    return JSONResponse(resp.json(), status_code=resp.status_code)
