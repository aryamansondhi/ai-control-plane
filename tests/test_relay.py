import pytest
from unittest.mock import patch, MagicMock, call
from app.relay.run_relay import run_relay


def make_mock_event():
    import uuid
    return (
        "outbox-id-123",
        uuid.uuid4(),
        "market.ticks",
        {"price": 255.82, "volume": 1420615},
        1
    )


class TestRunRelay:
    def test_no_events_does_nothing(self):
        with patch("app.relay.run_relay.claim_pending", return_value=[]):
            with patch("app.relay.run_relay.mark_delivered") as mock_delivered:
                run_relay()
                mock_delivered.assert_not_called()

    def test_successful_publish_marks_delivered(self):
        event = make_mock_event()
        with patch("app.relay.run_relay.claim_pending", return_value=[event]):
            with patch("app.relay.run_relay.publish", return_value=None):
                with patch("app.relay.run_relay.mark_delivered") as mock_delivered:
                    with patch("app.relay.run_relay.mark_failed") as mock_failed:
                        run_relay()
                        mock_delivered.assert_called_once_with(event[0])
                        mock_failed.assert_not_called()

    def test_failed_publish_marks_failed(self):
        event = make_mock_event()
        with patch("app.relay.run_relay.claim_pending", return_value=[event]):
            with patch("app.relay.run_relay.publish", side_effect=Exception("transport error")):
                with patch("app.relay.run_relay.mark_delivered") as mock_delivered:
                    with patch("app.relay.run_relay.mark_failed") as mock_failed:
                        run_relay()
                        mock_failed.assert_called_once()
                        mock_delivered.assert_not_called()

    def test_multiple_events_processed_independently(self):
        events = [make_mock_event(), make_mock_event(), make_mock_event()]
        with patch("app.relay.run_relay.claim_pending", return_value=events):
            with patch("app.relay.run_relay.publish", return_value=None):
                with patch("app.relay.run_relay.mark_delivered") as mock_delivered:
                    run_relay()
                    assert mock_delivered.call_count == 3