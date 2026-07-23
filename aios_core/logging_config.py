"""Structured JSON Logging Configuration for AIOS.

Formats all logs into standard JSON with automatic trace_id, span_id,
agent_id, and constitutional_status fields for production logging aggregation.
"""

import json
import logging
import sys
import time
from logging.handlers import RotatingFileHandler
from typing import Optional

from .tracing import tracer


class JSONFormatter(logging.Formatter):
    """JSON Formatter for structured production logging."""

    def format(self, record: logging.LogRecord) -> str:
        current_span = tracer.get_current_span()

        log_data = {
            "timestamp": time.time(),
            "iso_time": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "line": record.lineno,
            "trace_id": (
                current_span.trace_id if current_span else record.__dict__.get("trace_id")
            ),
            "span_id": (current_span.span_id if current_span else record.__dict__.get("span_id")),
            "agent_id": record.__dict__.get("agent_id", "system"),
            "constitutional_status": record.__dict__.get("constitutional_status", "VALID"),
        }

        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_data)


def setup_logging(
    level: str = "INFO", log_file: str = "aios.log", json_format: bool = True
) -> logging.Logger:
    """Configure structured logging for AIOS."""
    logger = logging.getLogger("aios")
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))
    logger.handlers.clear()

    # Formatter selection
    formatter = (
        JSONFormatter()
        if json_format
        else logging.Formatter(
            "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    )

    # Console Handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # File Handler
    file_handler = RotatingFileHandler(log_file, maxBytes=10 * 1024 * 1024, backupCount=5)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger


logger = setup_logging()
