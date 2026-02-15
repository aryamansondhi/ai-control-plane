from app.relay.publisher import publish
from app.relay.repository import claim_pending, mark_delivered, mark_failed


def run_relay():
    rows = claim_pending(limit=10)

    if not rows:
        print("No eligible outbox events.")
        return

    for (outbox_id, event_id, topic, payload, prev_attempts) in rows:
        # attempts were incremented during claim, so current attempt is prev_attempts + 1
        attempt = prev_attempts + 1

        try:
            publish(payload)
            mark_delivered(outbox_id)
            print(f"✅ Delivered {event_id} (attempt {attempt})")
        except Exception as e:
            mark_failed(outbox_id, attempt, str(e))
            print(f"❌ Failed {event_id} (attempt {attempt}): {e}")


if __name__ == "__main__":
    run_relay()