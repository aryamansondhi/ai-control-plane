from fastapi import FastAPI
from fastapi.responses import Response
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
from apscheduler.schedulers.background import BackgroundScheduler
from app.relay.run_relay import run_relay
from app.relay.repository import get_dead_letters, get_dead_letter_by_id

app = FastAPI()

scheduler = BackgroundScheduler()
scheduler.add_job(run_relay, "interval", seconds=30)
scheduler.start()

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/metrics")
def metrics():
    return Response(
        generate_latest(),
        media_type=CONTENT_TYPE_LATEST
    )

@app.post("/run-relay")
def trigger_relay():
    run_relay()
    return {"status": "relay executed"}

@app.get("/dead-letters")
def dead_letters():
    return get_dead_letters()

@app.get("/dead-letters/{event_id}")
def dead_letter_by_id(event_id: str):
    result = get_dead_letter_by_id(event_id)
    if not result:
        return {"error": "Not found"}
    return result

@app.on_event("shutdown")
def shutdown_event():
    global scheduler
    scheduler.shutdown()