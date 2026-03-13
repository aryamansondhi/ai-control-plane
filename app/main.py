from fastapi import FastAPI
from fastapi.responses import Response, HTMLResponse
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
from apscheduler.schedulers.background import BackgroundScheduler
from app.relay.run_relay import run_relay
from app.relay.repository import get_dead_letters, get_dead_letter_by_id, get_event_trace, replay_dead_letter, get_system_health
from app.ingestion.run_ingestion import run_ingestion

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

@app.get("/dashboard", response_class=HTMLResponse)
def dashboard():
    stats = get_system_health()
    dead_letters = get_dead_letters()

    dead_letter_rows = ""
    for dl in dead_letters:
        dead_letter_rows += f"""
        <tr>
            <td>{dl['event_id'][:8]}...</td>
            <td>{dl['entity_id']}</td>
            <td>{dl['delivery_attempts']}</td>
            <td>{dl['last_error']}</td>
            <td>{dl['dead_lettered_at']}</td>
        </tr>
        """

    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>AI Control Plane</title>
        <meta http-equiv="refresh" content="30">
        <style>
            body {{ font-family: monospace; background: #0a0a0a; color: #00d4ff; padding: 40px; }}
            h1 {{ color: #ff6b35; }}
            h2 {{ color: #00d4ff; border-bottom: 1px solid #333; padding-bottom: 8px; }}
            .grid {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 20px; margin: 30px 0; }}
            .card {{ background: #111; border: 1px solid #222; border-radius: 8px; padding: 20px; }}
            .card .value {{ font-size: 2em; font-weight: bold; color: #ff6b35; }}
            .card .label {{ font-size: 0.85em; color: #666; margin-top: 4px; }}
            .status {{ display: inline-block; padding: 4px 12px; border-radius: 4px; font-size: 0.85em; }}
            .running {{ background: #0a2a0a; color: #00ff88; border: 1px solid #00ff88; }}
            .stopped {{ background: #2a0a0a; color: #ff4444; border: 1px solid #ff4444; }}
            table {{ width: 100%; border-collapse: collapse; margin-top: 16px; }}
            th {{ text-align: left; padding: 10px; border-bottom: 1px solid #333; color: #666; font-size: 0.85em; }}
            td {{ padding: 10px; border-bottom: 1px solid #1a1a1a; font-size: 0.85em; color: #aaa; }}
            .footer {{ margin-top: 40px; color: #333; font-size: 0.75em; }}
        </style>
    </head>
    <body>
        <h1>AI Control Plane</h1>
        <p>Scheduler: <span class="status {'running' if scheduler.running else 'stopped'}">
            {'● RUNNING' if scheduler.running else '● STOPPED'}
        </span></p>

        <div class="grid">
            <div class="card">
                <div class="value">{stats['delivered_events']}</div>
                <div class="label">Delivered</div>
            </div>
            <div class="card">
                <div class="value">{stats['pending_events']}</div>
                <div class="label">Pending</div>
            </div>
            <div class="card">
                <div class="value">{stats['dead_lettered_events']}</div>
                <div class="label">Dead Lettered</div>
            </div>
            <div class="card">
                <div class="value" style="font-size: 0.9em;">{stats['last_delivered_at'] or 'N/A'}</div>
                <div class="label">Last Delivered</div>
            </div>
        </div>

        <h2>Dead Letters</h2>
        <table>
            <thead>
                <tr>
                    <th>Event ID</th>
                    <th>Symbol</th>
                    <th>Attempts</th>
                    <th>Last Error</th>
                    <th>Dead Lettered At</th>
                </tr>
            </thead>
            <tbody>
                {dead_letter_rows if dead_letter_rows else '<tr><td colspan="5" style="color:#333">No dead letters</td></tr>'}
            </tbody>
        </table>

        <div class="footer">Auto-refreshes every 30 seconds · AI Control Plane</div>
    </body>
    </html>
    """

@app.post("/ingest")
def ingest(symbols: list[str]):
    results = run_ingestion(symbols)
    return {"ingested": results}

@app.on_event("shutdown")
def shutdown_event():
    global scheduler
    scheduler.shutdown()