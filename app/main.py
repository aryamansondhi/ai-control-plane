from fastapi import FastAPI
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
from fastapi.responses import Response
from app.relay.run_relay import run_relay

app = FastAPI()

@app.post("/run-relay")
def trigger_relay():
    run_relay()
    return {"status": "relay executed"}

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/metrics")
def metrics():
    return Response(
        generate_latest(),
        media_type=CONTENT_TYPE_LATEST
    )