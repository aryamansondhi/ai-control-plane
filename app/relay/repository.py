import psycopg
import os
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")


def fetch_pending_events(limit=10):
    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT event_id, payload_json, delivery_attempts
                FROM outbox
                WHERE delivered_at IS NULL
                ORDER BY created_at
                LIMIT %s
                FOR UPDATE SKIP LOCKED
            """, (limit,))
            return cur.fetchall()


def mark_delivered(event_id):
    with psycopg.connect(DATABASE_URL) as conn:
        with conn.transaction():
            with conn.cursor() as cur:
                cur.execute("""
                    UPDATE outbox
                    SET delivered_at = %s,
                        delivery_attempts = delivery_attempts + 1
                    WHERE event_id = %s
                """, (datetime.utcnow(), event_id))