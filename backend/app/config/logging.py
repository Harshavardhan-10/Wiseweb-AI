"""Structured logging configuration.

Contextual fields (scan_id, website_id, task_id, analyzer, ...) are added by
callers through ``logger.info(..., extra=...)``. No secrets are ever logged.
"""

import json
import logging
import sys
from typing import Any

from app.config.settings import settings


class JsonFormatter(logging.Formatter):
    """Minimal JSON formatter for structured logs."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "ts": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        for key in ("scan_id", "website_id", "task_id", "analyzer",
                    "duration", "status", "error", "category", "rule_id"):
            value = record.__dict__.get(key)
            if value is not None:
                payload[key] = value
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


def configure_logging() -> None:
    root = logging.getLogger()
    root.setLevel(settings.log_level.upper())

    handler: logging.Handler
    if settings.environment == "production":
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(JsonFormatter())
    else:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(
            logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s")
        )

    root.handlers = [handler]

    # Keep noisy third-party loggers at a sane level.
    for noisy in ("httpx", "httpcore", "urllib3", "asyncio", "celery"):
        logging.getLogger(noisy).setLevel(logging.WARNING)
