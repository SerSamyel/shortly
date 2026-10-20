"""Structured JSON logs. Observability (trace ids) is added on top of this later."""

import json
import logging
import sys
from datetime import UTC, datetime

from shortly.config import Settings

_STANDARD = set(logging.makeLogRecord({}).__dict__) | {"message", "asctime"}


class JsonFormatter(logging.Formatter):
    def __init__(self, service: str, environment: str, version: str) -> None:
        super().__init__()
        self.base = {"service": service, "environment": environment, "version": version}

    def format(self, record: logging.LogRecord) -> str:
        data = {
            "ts": datetime.fromtimestamp(record.created, UTC).isoformat(),
            "level": record.levelname.lower(),
            "logger": record.name,
            "message": record.getMessage(),
            **self.base,
        }
        for key, value in record.__dict__.items():
            if key not in _STANDARD and not key.startswith("_"):
                data[key] = value
        if record.exc_info:
            data["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(data, default=str)


def setup_logging(settings: Settings, service: str = "shortly") -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter(service, settings.environment, settings.version))
    root = logging.getLogger()
    root.handlers[:] = [handler]
    root.setLevel(logging.INFO)
    # Access logs would contain client IPs and full paths; we log requests ourselves.
    logging.getLogger("uvicorn.access").disabled = True
    logging.getLogger("aiokafka").setLevel(logging.WARNING)
