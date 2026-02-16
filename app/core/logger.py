import logging
import json
from datetime import datetime
from uuid import UUID


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        log_record = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
        }

        for attr in ["event_id", "trace_id", "attempt", "topic", "error"]:
            value = getattr(record, attr, None)

            if value is not None:
                # Convert UUIDs and other non-serializable types
                if isinstance(value, UUID):
                    value = str(value)

                log_record[attr] = value

        return json.dumps(log_record, default=str)

def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(JsonFormatter())
        logger.addHandler(handler)

    return logger