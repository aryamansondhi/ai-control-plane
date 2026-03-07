from fastapi import FastAPI
from fastapi.responses import Response
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
from apscheduler.schedulers.background import BackgroundScheduler
from app.relay.run_relay import run_relay
from app.relay.repository import get_dead_letters, get_dead_letter_by_id, get_event_trace, replay_dead_letter, get_system_health

app = FastAPI()

scheduler = BackgroundScheduler()
scheduler.add_job(run_relay, "interval", seconds=30)
scheduler.start()

@app.get("/health")
def health():
    stats = get_system_health()
    return {
        "status": "ok",
        "scheduler": "running" if scheduler.running else "stopped",
        "pending_events": stats["pending_events"],
        "dead_lettered_events": stats["dead_lettered_events"],
        "delivered_events": stats["delivered_events"],
        "last_delivered_at": stats["last_delivered_at"],
    }

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

@app.get("/events/{event_id}/trace")
def event_trace(event_id: str):
    result = get_event_trace(event_id)
    if not result:
        return {"error": "Event not found"}
    return result

@app.post("/dead-letters/{event_id}/replay")
def replay_dead_letter_endpoint(event_id: str):
    result = replay_dead_letter(event_id)
    if not result:
        return {"error": "Event not found or not dead-lettered"}
    return result

@app.on_event("shutdown")
def shutdown_event():
    global scheduler
    scheduler.shutdown()