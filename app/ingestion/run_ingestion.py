import uuid
import json
import yfinance as yf
import psycopg
from datetime import datetime, timezone
from dotenv import load_dotenv
import os

load_dotenv()

from typing import Final

DATABASE_URL: Final[str] = os.getenv("DATABASE_URL") or ""

if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL is not set in environment")

def fetch_market_data(symbol: str):
    ticker = yf.Ticker(symbol)
    data = ticker.history(period="1d", interval="1m")

    if data.empty:
        raise ValueError("No market data returned")

    latest = data.iloc[-1]
    timestamp = data.index[-1]

    if hasattr(timestamp, "to_pydatetime"):
        dt = timestamp.to_pydatetime()
    else:
        dt = datetime.utcnow()

    dt = dt.replace(tzinfo=timezone.utc)

    return {
        "symbol": symbol,
        "price": float(latest["Close"]),
        "volume": int(latest["Volume"]),
        "currency": "USD",
        "occurred_at": dt.isoformat()
    }

def run_ingestion(symbol: str):
    raw_data = fetch_market_data(symbol)

    event_id = uuid.uuid4()
    trace_id = uuid.uuid4()

    canonical_event = {
        "event_id": str(event_id),
        "event_type": "MARKET_TICK_INGESTED",
        "source": "yfinance",
        "entity_id": raw_data["symbol"],
        "entity_type": "equity",
        "occurred_at": raw_data["occurred_at"],
        "schema_version": 1,
        "trace_id": str(trace_id),
        "payload": {
            "price": raw_data["price"],
            "volume": raw_data["volume"],
            "currency": raw_data["currency"]
        }
    }

    with psycopg.connect(DATABASE_URL) as conn:
        with conn.transaction():
            with conn.cursor() as cur:

                # 1️⃣ Insert raw payload
                cur.execute("""
                    INSERT INTO raw_payloads (source, payload_json)
                    VALUES (%s, %s)
                """, (
                    canonical_event["source"],
                    json.dumps(raw_data)
                ))

                # 2️⃣ Insert canonical event
                cur.execute("""
                    INSERT INTO events (
                        event_id,
                        event_type,
                        source,
                        entity_id,
                        entity_type,
                        occurred_at,
                        schema_version,
                        trace_id,
                        payload_json
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    canonical_event["event_id"],
                    canonical_event["event_type"],
                    canonical_event["source"],
                    canonical_event["entity_id"],
                    canonical_event["entity_type"],
                    datetime.fromisoformat(raw_data["occurred_at"]),
                    canonical_event["schema_version"],
                    canonical_event["trace_id"],
                    json.dumps(canonical_event["payload"])
                ))

                # 3️⃣ Insert outbox record
                cur.execute("""
                    INSERT INTO outbox (event_id, topic, payload_json)
                    VALUES (%s, %s, %s)
                """, (
                    canonical_event["event_id"],
                    "market.ticks",
                    json.dumps(canonical_event)
                ))

    print("✅ Ingestion successful")
    print(f"Event ID: {event_id}")
    print(f"Trace ID: {trace_id}")


if __name__ == "__main__":
    run_ingestion("AAPL")