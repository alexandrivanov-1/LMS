import contextlib
import json
import os
import httpx
import psycopg
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from minio import Minio
from minio.error import S3Error

app = FastAPI(title="parser")

DSN = os.getenv("POSTGRES_DSN")
TIKA_URL = os.getenv("TIKA_URL", "http://tika:9998")
MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "http://minio:9000")
endpoint = MINIO_ENDPOINT.replace("http://", "").replace("https://", "")
minio = Minio(
    endpoint,
    access_key=os.getenv("MINIO_ACCESS_KEY"),
    secret_key=os.getenv("MINIO_SECRET_KEY"),
    secure=MINIO_ENDPOINT.startswith("https://"),
)
BUCKET = os.getenv("MINIO_BUCKET", "sources")


@app.get("/health")
def health():
    return {"status": "ok", "service": "parser"}


def _split(text: str, size: int = 1000, overlap: int = 100) -> list[str]:
    res: list[str] = []
    step = max(size - overlap, 1)
    i = 0
    while i < len(text):
        res.append(text[i : i + size])
        i += step
    return res


def _close_response(response: object) -> None:
    for attr in ("close", "release_conn"):
        with contextlib.suppress(AttributeError):
            getattr(response, attr)()


def _read_object(client: Minio, bucket: str, object_name: str) -> bytes:
    response = None
    try:
        response = client.get_object(bucket, object_name)
        try:
            return response.read()
        except S3Error as exc:
            raise RuntimeError(
                f"Ошибка чтения объекта {bucket}/{object_name}: {exc.code}"
            ) from exc
        except Exception:
            raise
    except S3Error as exc:
        raise RuntimeError(
            f"Не удалось получить объект {bucket}/{object_name}: {exc.code}"
        ) from exc
    finally:
        if response is not None:
            _close_response(response)


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
            for sid, meta in rows:
                obj = meta["object"]
                data = _read_object(minio, BUCKET, obj)
                async with httpx.AsyncClient(timeout=120.0) as client:
                    r = await client.put(
                        f"{TIKA_URL}/tika",
                        content=data,
                        headers={"Accept": "text/plain"},
                    )
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
                cur.execute(
                    "UPDATE source SET meta=%s WHERE id=%s",
                    (json.dumps(new_meta, ensure_ascii=False), sid),
                )
                processed += 1
            conn.commit()
    return JSONResponse({"processed": processed})
