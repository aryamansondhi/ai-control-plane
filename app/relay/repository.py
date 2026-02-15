import os
from datetime import datetime, timedelta, timezone

import psycopg
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

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