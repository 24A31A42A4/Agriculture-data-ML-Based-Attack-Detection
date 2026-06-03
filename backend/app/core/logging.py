"""
Structured JSON logging for the AgriIoT Security Framework.

Provides a consistent logging setup with JSON formatting for production
and human-readable formatting for development. All security events are
logged with structured fields for audit compliance.
"""

import logging
import json
import sys
from datetime import datetime, timezone
from typing import Any

from app.config import get_settings


class JSONFormatter(logging.Formatter):
    """
    JSON log formatter for structured logging in production.

    Output example:
    {
        "timestamp": "2026-06-03T12:00:00.000Z",
        "level": "WARNING",
        "logger": "app.security.gateway",
        "message": "Replay attack detected",
        "device_id": "sensor-001",
        "correlation_id": "abc-123"
    }
    """

    def format(self, record: logging.LogRecord) -> str:
        log_entry: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Include extra fields passed via `logger.info("msg", extra={...})`
        # Standard LogRecord attributes to exclude from extras
        standard_attrs = {
            "name", "msg", "args", "created", "relativeCreated", "exc_info",
            "exc_text", "stack_info", "lineno", "funcName", "filename",
            "module", "levelname", "levelno", "pathname", "thread",
            "threadName", "process", "processName", "message", "taskName",
        }
        for key, value in record.__dict__.items():
            if key not in standard_attrs and not key.startswith("_"):
                log_entry[key] = value

        # Include exception info if present
        if record.exc_info and record.exc_info[1]:
            log_entry["exception"] = {
                "type": type(record.exc_info[1]).__name__,
                "message": str(record.exc_info[1]),
            }

        return json.dumps(log_entry, default=str)


def setup_logging() -> None:
    """
    Configure application-wide logging.

    - Production (DEBUG=false): JSON-formatted output to stdout.
    - Development (DEBUG=true): Human-readable colored output to stdout.
    """
    settings = get_settings()
    log_level = getattr(logging, settings.log_level.upper(), logging.INFO)

    # Root logger configuration
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Remove existing handlers to avoid duplicates
    root_logger.handlers.clear()

    # Console handler
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(log_level)

    if settings.debug:
        # Human-readable format for development
        formatter = logging.Formatter(
            fmt="%(asctime)s │ %(levelname)-8s │ %(name)-30s │ %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    else:
        # JSON format for production
        formatter = JSONFormatter()

    handler.setFormatter(formatter)
    root_logger.addHandler(handler)

    # Suppress noisy third-party loggers
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(
        logging.INFO if settings.debug else logging.WARNING
    )
    logging.getLogger("asyncpg").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """
    Get a named logger for a specific module.

    Usage:
        from app.core.logging import get_logger
        logger = get_logger(__name__)
        logger.info("Device registered", extra={"device_id": "sensor-001"})
    """
    return logging.getLogger(name)
