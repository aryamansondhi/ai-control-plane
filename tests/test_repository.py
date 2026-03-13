import pytest
from unittest.mock import patch, MagicMock
from app.relay.repository import mark_delivered, mark_failed, get_dead_letters, get_event_trace


def make_mock_conn():
    mock_cursor = MagicMock()
    mock_conn = MagicMock()
    mock_conn.__enter__ = lambda s: s
    mock_conn.__exit__ = MagicMock(return_value=False)
    mock_conn.transaction.return_value.__enter__ = lambda s: s
    mock_conn.transaction.return_value.__exit__ = MagicMock(return_value=False)
    mock_conn.cursor.return_value.__enter__ = lambda s: mock_cursor
    mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
    return mock_conn, mock_cursor


class TestMarkDelivered:
    def test_executes_update(self):
        mock_conn, mock_cursor = make_mock_conn()
        with patch("app.relay.repository.psycopg.connect", return_value=mock_conn):
            mark_delivered("some-outbox-id")
            assert mock_cursor.execute.called


class TestMarkFailed:
    def test_schedules_retry_below_max(self):
        mock_conn, mock_cursor = make_mock_conn()
        with patch("app.relay.repository.psycopg.connect", return_value=mock_conn):
            mark_failed("some-outbox-id", attempt=2, error="timeout")
            assert mock_cursor.execute.called

    def test_dead_letters_at_max_attempts(self):
        mock_conn, mock_cursor = make_mock_conn()
        with patch("app.relay.repository.psycopg.connect", return_value=mock_conn):
            mark_failed("some-outbox-id", attempt=5, error="timeout")
            call_args = mock_cursor.execute.call_args[0][0]
            assert "dead_lettered_at" in call_args


class TestGetDeadLetters:
    def test_returns_empty_list_when_none(self):
        mock_conn, mock_cursor = make_mock_conn()
        mock_cursor.fetchall.return_value = []
        with patch("app.relay.repository.psycopg.connect", return_value=mock_conn):
            result = get_dead_letters()
            assert result == []

    def test_returns_formatted_list(self):
        from datetime import datetime, timezone
        import uuid
        mock_conn, mock_cursor = make_mock_conn()
        mock_cursor.fetchall.return_value = [(
            uuid.uuid4(),
            "market.ticks",
            5,
            "Simulated publish failure",
            datetime(2026, 3, 1, tzinfo=timezone.utc),
            "MARKET_TICK_INGESTED",
            "AAPL",
            datetime(2026, 3, 1, tzinfo=timezone.utc),
        )]
        with patch("app.relay.repository.psycopg.connect", return_value=mock_conn):
            result = get_dead_letters()
            assert len(result) == 1
            assert result[0]["topic"] == "market.ticks"
            assert result[0]["entity_id"] == "AAPL"
            assert result[0]["delivery_attempts"] == 5


class TestGetEventTrace:
    def test_returns_none_when_event_not_found(self):
        mock_conn, mock_cursor = make_mock_conn()
        mock_cursor.fetchone.return_value = None
        with patch("app.relay.repository.psycopg.connect", return_value=mock_conn):
            result = get_event_trace("nonexistent-id")
            assert result is None