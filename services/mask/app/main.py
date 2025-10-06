import os

from fastapi import FastAPI

app = FastAPI(title=os.getenv("SERVICE_NAME", "service"))

@app.get("/health")
def health():
    return {"status": "ok", "service": os.getenv("SERVICE_NAME", "service")}
