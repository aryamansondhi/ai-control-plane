import os
from datetime import datetime, timedelta, timezone

import psycopg
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL: str = os.getenv("DATABASE_URL") or ""
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL is not set in environment")

MAX_ATTEMPTS = 5


def _utcnow():
    return datetime.now(timezone.utc)


def _backoff_seconds(attempt: int) -> int:
    # attempt starts at 1
    # 1 -> 2s, 2 -> 5s, 3 -> 15s, 4 -> 30s, 5 -> 60s
    schedule = [2, 5, 15, 30, 60]
    idx = min(attempt - 1, len(schedule) - 1)
    return schedule[idx]


def claim_pending(limit: int = 10):
    """
    Claim eligible outbox rows for delivery.
    IMPORTANT: We increment delivery_attempts as part of the claim to represent "work started".
    This is critical for correctness if the worker crashes after claiming but before publishing.
    """
    with psycopg.connect(DATABASE_URL) as conn:
        with conn.transaction():
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, event_id, topic, payload_json, delivery_attempts
                    FROM outbox
                    WHERE delivered_at IS NULL
                      AND dead_lettered_at IS NULL
                      AND next_attempt_at <= NOW()
                    ORDER BY created_at
                    LIMIT %s
                    FOR UPDATE SKIP LOCKED
                    """,
                    (limit,),
                )
                rows = cur.fetchall()

                # increment attempts immediately for claimed rows
                for (oid, _event_id, _topic, _payload, _attempts) in rows:
                    cur.execute(
                        """
                        UPDATE outbox
                        SET delivery_attempts = delivery_attempts + 1
                        WHERE id = %s
                        """,
                        (oid,),
                    )

                return rows


def mark_delivered(outbox_id: str):
    with psycopg.connect(DATABASE_URL) as conn:
        with conn.transaction():
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE outbox
                    SET delivered_at = NOW(),
                        last_error = NULL
                    WHERE id = %s
                    """,
                    (outbox_id,),
                )


def mark_failed(outbox_id: str, attempt: int, error: str):
    """
    On failure:
      - if attempt >= MAX_ATTEMPTS: dead-letter
      - else: schedule retry using backoff
    """
    if attempt >= MAX_ATTEMPTS:
        with psycopg.connect(DATABASE_URL) as conn:
            with conn.transaction():
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        UPDATE outbox
                        SET last_error = %s,
                            dead_lettered_at = NOW()
                        WHERE id = %s
                        """,
                        (error[:2000], outbox_id),
                    )
        return

    delay = _backoff_seconds(attempt)
    next_time = _utcnow() + timedelta(seconds=delay)

    with psycopg.connect(DATABASE_URL) as conn:
        with conn.transaction():
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE outbox
                    SET last_error = %s,
                        next_attempt_at = %s
                    WHERE id = %s
                    """,
                    (error[:2000], next_time, outbox_id),
                )

def get_dead_letters():
    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT
                    o.event_id,
                    o.topic,
                    o.delivery_attempts,
                    o.last_error,
                    o.dead_lettered_at,
                    e.event_type,
                    e.entity_id,
                    e.occurred_at
                FROM outbox o
                JOIN events e ON o.event_id = e.event_id
                WHERE o.dead_lettered_at IS NOT NULL
                ORDER BY o.dead_lettered_at DESC
            """)
            rows = cur.fetchall()
            return [
                {
                    "event_id": str(r[0]),
                    "topic": r[1],
                    "delivery_attempts": r[2],
                    "last_error": r[3],
                    "dead_lettered_at": r[4].isoformat(),
                    "event_type": r[5],
                    "entity_id": r[6],
                    "occurred_at": r[7].isoformat(),
                }
                for r in rows
            ]


def get_dead_letter_by_id(event_id: str):
    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT
                    o.event_id,
                    o.topic,
                    o.payload_json,
                    o.delivery_attempts,
                    o.last_error,
                    o.dead_lettered_at,
                    e.event_type,
                    e.entity_id,
                    e.occurred_at,
                    e.trace_id
                FROM outbox o
                JOIN events e ON o.event_id = e.event_id
                WHERE o.dead_lettered_at IS NOT NULL
                AND o.event_id = %s
            """, (event_id,))
            r = cur.fetchone()
            if not r:
                return None
            return {
                "event_id": str(r[0]),
                "topic": r[1],
                "payload": r[2],
                "delivery_attempts": r[3],
                "last_error": r[4],
                "dead_lettered_at": r[5].isoformat(),
                "event_type": r[6],
                "entity_id": r[7],
                "occurred_at": r[8].isoformat(),
                "trace_id": str(r[9]),
            }

def get_event_trace(event_id: str):
    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            # Get canonical event
            cur.execute("""
                SELECT
                    event_id,
                    event_type,
                    source,
                    entity_id,
                    entity_type,
                    occurred_at,
                    ingested_at,
                    schema_version,
                    trace_id,
                    payload_json
                FROM events
                WHERE event_id = %s
            """, (event_id,))
            event = cur.fetchone()
            if not event:
                return None

            # Get raw payload
            cur.execute("""
                SELECT id, source, fetched_at, payload_json
                FROM raw_payloads
                WHERE source = %s
                ORDER BY fetched_at ASC
                LIMIT 1
            """, (event[2],))
            raw = cur.fetchone()

            # Get outbox lifecycle
            cur.execute("""
                SELECT
                    id,
                    topic,
                    delivery_attempts,
                    next_attempt_at,
                    delivered_at,
                    dead_lettered_at,
                    last_error,
                    created_at
                FROM outbox
                WHERE event_id = %s
            """, (event_id,))
            outbox = cur.fetchone()

            if not outbox:
                return {
                    "event_id": str(event[0]),
                    "trace_id": str(event[8]),
                    "final_state": "NO_OUTBOX_RECORD",
                    "event": {
                        "event_type": event[1],
                        "source": event[2],
                        "entity_id": event[3],
                        "entity_type": event[4],
                        "occurred_at": event[5].isoformat(),
                        "ingested_at": event[6].isoformat(),
                        "schema_version": event[7],
                        "payload": event[9],
                    },
                    "outbox": None,
                }

            # Determine final state
            if outbox[4]:
                state = "DELIVERED"
            elif outbox[5]:
                state = "DEAD_LETTERED"
            else:
                state = "PENDING"

            return {
                "event_id": str(event[0]),
                "trace_id": str(event[8]),
                "final_state": state,
                "event": {
                    "event_type": event[1],
                    "source": event[2],
                    "entity_id": event[3],
                    "entity_type": event[4],
                    "occurred_at": event[5].isoformat(),
                    "ingested_at": event[6].isoformat(),
                    "schema_version": event[7],
                    "payload": event[9],
                },
                "outbox": {
                    "topic": outbox[1],
                    "delivery_attempts": outbox[2],
                    "next_attempt_at": outbox[3].isoformat() if outbox[3] else None,
                    "delivered_at": outbox[4].isoformat() if outbox[4] else None,
                    "dead_lettered_at": outbox[5].isoformat() if outbox[5] else None,
                    "last_error": outbox[6],
                    "created_at": outbox[7].isoformat(),
                },
            }

def replay_dead_letter(event_id: str):
    with psycopg.connect(DATABASE_URL) as conn:
        with conn.transaction():
            with conn.cursor() as cur:
                # Confirm it's actually dead-lettered
                cur.execute("""
                    SELECT id FROM outbox
                    WHERE event_id = %s
                    AND dead_lettered_at IS NOT NULL
                """, (event_id,))
                row = cur.fetchone()
                if not row:
                    return None

                # Reset outbox record for redelivery
                cur.execute("""
                    UPDATE outbox
                    SET dead_lettered_at = NULL,
                        delivered_at = NULL,
                        delivery_attempts = 0,
                        next_attempt_at = NOW(),
                        last_error = NULL
                    WHERE event_id = %s
                """, (event_id,))
                return {"event_id": event_id, "status": "requeued"}

def get_system_health():
    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT
                    COUNT(*) FILTER (WHERE delivered_at IS NOT NULL) AS delivered,
                    COUNT(*) FILTER (WHERE dead_lettered_at IS NOT NULL) AS dead_lettered,
                    COUNT(*) FILTER (
                        WHERE delivered_at IS NULL
                        AND dead_lettered_at IS NULL
                    ) AS pending,
                    MAX(delivered_at) AS last_delivered_at
                FROM outbox
            """)
            row = cur.fetchone()
            if not row:
                return {
                    "delivered_events": 0,
                    "dead_lettered_events": 0,
                    "pending_events": 0,
                    "last_delivered_at": None,
                }
            return {
                "delivered_events": row[0],
                "dead_lettered_events": row[1],
                "pending_events": row[2],
                "last_delivered_at": row[3].isoformat() if row[3] else None,
            }