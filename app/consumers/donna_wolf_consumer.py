import psycopg
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL: str = os.getenv("DATABASE_URL") or ""
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL is not set in environment")


def get_latest_market_event(symbol: str) -> dict | None:
    """
    Reads the most recently delivered market event for a given symbol
    from the Control Plane event store.

    This replaces Donna's direct yfinance call with a reliable,
    traceable, structured event consumption pattern.
    """
    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT
                    e.event_id,
                    e.trace_id,
                    e.entity_id,
                    e.occurred_at,
                    e.payload_json,
                    o.delivered_at
                FROM events e
                JOIN outbox o ON e.event_id = o.event_id
                WHERE e.entity_id = %s
                AND e.event_type = 'MARKET_TICK_INGESTED'
                AND o.delivered_at IS NOT NULL
                ORDER BY o.delivered_at DESC
                LIMIT 1
            """, (symbol,))
            row = cur.fetchone()
            if not row:
                return None
            return {
                "event_id": str(row[0]),
                "trace_id": str(row[1]),
                "symbol": row[2],
                "occurred_at": row[3].isoformat(),
                "price": row[4]["price"],
                "volume": row[4]["volume"],
                "currency": row[4]["currency"],
                "delivered_at": row[5].isoformat(),
            }


def get_portfolio_snapshot(symbols: list[str]) -> list[dict]:
    """
    Returns the latest delivered market event for each symbol.
    Donna's Wolf calls this instead of hitting yfinance directly.
    """
    results = []
    for symbol in symbols:
        event = get_latest_market_event(symbol)
        if event:
            results.append(event)
    return results


if __name__ == "__main__":
    snapshot = get_portfolio_snapshot(["AAPL"])
    for item in snapshot:
        print(f"{item['symbol']}: ${item['price']} — trace_id: {item['trace_id']}")