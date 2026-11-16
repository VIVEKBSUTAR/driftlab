"""Structured application logs without request bodies, cookies, or query strings."""

import json
import logging
from datetime import datetime, timezone


class JsonFormatter(logging.Formatter):
    def format(self, record):
        item = {
            "time": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        for name in ("request_id", "run_id", "method", "path", "status", "duration_ms"):
            value = getattr(record, name, None)
            if value is not None:
                item[name] = value
        if record.exc_info:
            item["exception"] = self.formatException(record.exc_info)
        return json.dumps(item, ensure_ascii=False)


def configure_logging():
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers[:] = [handler]
    root.setLevel(logging.INFO)
