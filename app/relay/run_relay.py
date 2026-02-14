import json
from app.relay.repository import fetch_pending_events, mark_delivered
from app.relay.publisher import publish


def run_relay():
    events = fetch_pending_events()

    if not events:
        print("No pending events.")
        return

    for event_id, payload, attempts in events:
        try:
            publish(payload)
            mark_delivered(event_id)
            print(f"✅ Delivered {event_id}")
        except Exception as e:
            print(f"❌ Failed {event_id}: {e}")


if __name__ == "__main__":
    run_relay()