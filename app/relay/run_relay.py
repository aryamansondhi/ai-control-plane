from app.relay.publisher import publish
from app.relay.repository import claim_pending, mark_delivered, mark_failed
from app.core.logger import get_logger

logger = get_logger(__name__)

def run_relay():
    rows = claim_pending(limit=10)

    if not rows:
        print("No eligible outbox events.")
        return

    for (outbox_id, event_id, topic, payload, prev_attempts) in rows:
        attempt = prev_attempts + 1

        try:
            logger.info(
                "Publishing event",
                extra={
                    "event_id": event_id,
                    "attempt": attempt,
                    "topic": topic,
                },
            )

            publish(payload)

            mark_delivered(outbox_id)

            logger.info(
                "Delivered event",
                extra={
                    "event_id": event_id,
                    "attempt": attempt,
                    "topic": topic,
                },
            )

        except Exception as e:
            mark_failed(outbox_id, attempt, str(e))

            logger.error(
                "Publish failed",
                extra={
                    "event_id": event_id,
                    "attempt": attempt,
                    "topic": topic,
                    "error": str(e),
                },
            )

if __name__ == "__main__":
    run_relay()