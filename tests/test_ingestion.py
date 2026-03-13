import pytest
from unittest.mock import patch, MagicMock
from app.ingestion.run_ingestion import fetch_market_data, ingest_symbol


def mock_yfinance_ticker(symbol):
    import pandas as pd
    from datetime import datetime, timezone

    mock_data = pd.DataFrame(
        {"Close": [255.82], "Volume": [1420615]},
        index=pd.DatetimeIndex([datetime(2026, 3, 1, 15, 59, tzinfo=timezone.utc)])
    )
    mock_ticker = MagicMock()
    mock_ticker.history.return_value = mock_data
    return mock_ticker

class TestFetchMarketData:
    def test_returns_expected_fields(self):
        with patch("app.ingestion.run_ingestion.yf.Ticker", side_effect=mock_yfinance_ticker):
            result = fetch_market_data("AAPL")
            assert result["symbol"] == "AAPL"
            assert result["price"] == 255.82
            assert result["volume"] == 1420615
            assert result["currency"] == "USD"
            assert "occurred_at" in result

    def test_raises_on_empty_data(self):
        import pandas as pd
        mock_ticker = MagicMock()
        mock_ticker.history.return_value = pd.DataFrame()
        with patch("app.ingestion.run_ingestion.yf.Ticker", return_value=mock_ticker):
            with pytest.raises(ValueError, match="No market data returned"):
                fetch_market_data("INVALID")

class TestIngestSymbol:
    def test_returns_event_id_and_trace_id(self):
        with patch("app.ingestion.run_ingestion.yf.Ticker", side_effect=mock_yfinance_ticker):
            with patch("app.ingestion.run_ingestion.psycopg.connect") as mock_conn:
                mock_conn.return_value.__enter__ = lambda s: s
                mock_conn.return_value.__exit__ = MagicMock(return_value=False)
                mock_conn.return_value.transaction = MagicMock()
                mock_conn.return_value.transaction.return_value.__enter__ = lambda s: s
                mock_conn.return_value.transaction.return_value.__exit__ = MagicMock(return_value=False)
                mock_cursor = MagicMock()
                mock_conn.return_value.cursor.return_value.__enter__ = lambda s: mock_cursor
                mock_conn.return_value.cursor.return_value.__exit__ = MagicMock(return_value=False)

                result = ingest_symbol("AAPL")
                assert "event_id" in result
                assert "trace_id" in result
                assert result["symbol"] == "AAPL"