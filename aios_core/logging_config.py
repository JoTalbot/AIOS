"""Structured JSON Logging Configuration for AIOS.

Formats all logs into standard JSON with automatic trace_id, span_id,
agent_id, and constitutional_status fields for production logging aggregation.

Features:
- JSON and human-readable formatting
- Automatic trace/span correlation
- RotatingFileHandler with configurable rotation
- Starlette/ASGI middleware integration
- Context variable injection (agent_id, constitutional_status)
- Log level hierarchy and per-module override
- Sensitive data sanitization
- Log buffering for burst-mode collection
"""

import json
import logging
import sys
import time
from contextvars import ContextVar
from logging.handlers import RotatingFileHandler
from typing import Any

from .tracing import tracer

__all__ = [
    "JSONFormatter",
    "LogMiddleware",
    "setup_logging",
    "logger",
    "set_log_context",
    "clear_log_context",
]

# Context variables for dynamic injection
_ctx_agent_id: ContextVar[str] = ContextVar("agent_id", default="system")
_ctx_constitutional_status: ContextVar[str] = ContextVar(
    "constitutional_status", default="VALID"
)
_ctx_task_id: ContextVar[str] = ContextVar("task_id", default="")

# Sensitive field patterns to sanitize
_SENSITIVE_FIELDS = frozenset(
    {
        "password",
        "token",
        "secret",
        "api_key",
        "auth",
        "credential",
        "private_key",
        "access_key",
    }
)


def set_log_context(
    agent_id: str = "",
    constitutional_status: str = "",
    task_id: str = "",
) -> None:
    """Set context variables that are automatically injected into all log records."""
    if agent_id:
        _ctx_agent_id.set(agent_id)
    if constitutional_status:
        _ctx_constitutional_status.set(constitutional_status)
    if task_id:
        _ctx_task_id.set(task_id)


def clear_log_context() -> None:
    """Reset all log context variables to defaults."""
    _ctx_agent_id.set("system")
    _ctx_constitutional_status.set("VALID")
    _ctx_task_id.set("")


def _sanitize(data: Any) -> Any:
    """Sanitize sensitive fields from data structures."""
    if isinstance(data, dict):
        sanitized = {}
        for key, value in data.items():
            if any(s in key.lower() for s in _SENSITIVE_FIELDS):
                sanitized[key] = "***REDACTED***"
            else:
                sanitized[key] = _sanitize(value)
        return sanitized
    if isinstance(data, list):
        return [_sanitize(item) for item in data]
    return data


class JSONFormatter(logging.Formatter):
    """JSON Formatter for structured production logging.

    Automatically injects trace_id, span_id, agent_id, constitutional_status,
    and task_id from context variables.  Sanitizes sensitive fields.
    """

    def format(self, record: logging.LogRecord) -> str:
        """Format a log record as JSON."""
        current_span = tracer.get_current_span()

        # Build structured data
        log_data: dict[str, Any] = {
            "timestamp": time.time(),
            "iso_time": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "line": record.lineno,
            "trace_id": (
                current_span.trace_id
                if current_span
                else record.__dict__.get("trace_id")
            ),
            "span_id": (
                current_span.span_id if current_span else record.__dict__.get("span_id")
            ),
            "agent_id": _ctx_agent_id.get(),
            "constitutional_status": _ctx_constitutional_status.get(),
            "task_id": _ctx_task_id.get(),
        }

        # Inject extra fields from the record
        extra_fields = {
            k: v
            for k, v in record.__dict__.items()
            if k
            not in {
                "name",
                "msg",
                "args",
                "created",
                "relativeCreated",
                "exc_info",
                "exc_text",
                "stack_info",
                "lineno",
                "module",
                "filename",
                "funcName",
                "levelname",
                "levelno",
                "msecs",
                "thread",
                "threadName",
                "process",
                "processName",
                "trace_id",
                "span_id",
                "agent_id",
                "constitutional_status",
                "task_id",
            }
            and not k.startswith("_")
        }
        if extra_fields:
            log_data["extra"] = _sanitize(extra_fields)

        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_data, ensure_ascii=False)


class HumanFormatter(logging.Formatter):
    """Human-readable formatter with color-like markers for terminal output."""

    COLORS = {
        "DEBUG": "\033[36m",
        "INFO": "\033[32m",
        "WARNING": "\033[33m",
        "ERROR": "\033[31m",
        "CRITICAL": "\033[35m",
    }

    def format(self, record: logging.LogRecord) -> str:
        """Format in readable style."""
        agent = _ctx_agent_id.get()
        task = _ctx_task_id.get()
        prefix = f"[{record.levelname}] {record.name}"
        if agent != "system":
            prefix += f" agent={agent}"
        if task:
            prefix += f" task={task}"
        msg = f"{prefix}: {record.getMessage()}"
        if record.exc_info:
            msg += f"\n{self.formatException(record.exc_info)}"
        return msg


class LogMiddleware:
    """ASGI middleware that injects request metadata into log context.

    Usage::

        app = Starlette(middleware=[LogMiddleware()])
    """

    def __init__(self, app: Any, logger_name: str = "aios"):
        """Initialize LogMiddleware."""
        self.app = app
        self.logger_name = logger_name

    async def __call__(self, scope: dict, receive: Any, send: Any) -> None:
        """Process ASGI request with log context injection."""
        if scope["type"] in ("http", "websocket"):
            path = scope.get("path", "")
            method = scope.get("method", "")
            set_log_context(task_id=f"{method}:{path}")
            logging.getLogger(self.logger_name).info(
                f"Request: {method} {path}",
                extra={"request_path": path, "request_method": method},
            )
        await self.app(scope, receive, send)
        if scope["type"] in ("http", "websocket"):
            clear_log_context()


class BufferedHandler(logging.Handler):
    """Buffered handler that accumulates log records and flushes periodically.

    Useful for burst-mode collection in high-throughput scenarios.
    """

    def __init__(
        self,
        buffer_size: int = 100,
        flush_interval: float = 5.0,
        target: logging.Handler | None = None,
    ):
        """Initialize BufferedHandler."""
        super().__init__()
        self._buffer: list[logging.LogRecord] = []
        self._buffer_size = buffer_size
        self._flush_interval = flush_interval
        self._target = target
        self._last_flush = time.time()

    def emit(self, record: logging.LogRecord) -> None:
        """Buffer the record; flush when buffer is full or interval elapsed."""
        self._buffer.append(record)
        now = time.time()
        if (
            len(self._buffer) >= self._buffer_size
            or (now - self._last_flush) >= self._flush_interval
        ):
            self.flush()

    def flush(self) -> None:
        """Send buffered records to the target handler."""
        if self._target and self._buffer:
            for record in self._buffer:
                self._target.emit(record)
            self._target.flush()
        self._buffer.clear()
        self._last_flush = time.time()


def setup_logging(
    level: str = "INFO",
    log_file: str = "aios.log",
    json_format: bool = True,
    max_bytes: int = 10 * 1024 * 1024,
    backup_count: int = 5,
    buffer_size: int = 0,
    module_levels: dict[str, str] = {},
) -> logging.Logger:
    """Configure structured logging for AIOS.

    Args:
        level: Global log level (DEBUG, INFO, WARNING, ERROR, CRITICAL).
        log_file: Path to the rotating log file.
        json_format: Use JSON formatter if True, human-readable otherwise.
        max_bytes: Maximum log file size before rotation.
        backup_count: Number of backup log files to keep.
        buffer_size: If >0, use a BufferedHandler wrapping the file handler.
        module_levels: Per-module log level overrides (e.g. {"aios_core.storage": "DEBUG"}).
    """
    logger = logging.getLogger("aios")
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))
    logger.handlers.clear()

    # Formatter selection
    formatter = (
        JSONFormatter()
        if json_format
        else HumanFormatter(
            "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    )

    # Console Handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # File Handler (possibly wrapped in BufferedHandler)
    file_handler = RotatingFileHandler(
        log_file, maxBytes=max_bytes, backupCount=backup_count
    )
    file_handler.setFormatter(formatter)

    if buffer_size > 0:
        buffered = BufferedHandler(buffer_size=buffer_size, target=file_handler)
        logger.addHandler(buffered)
    else:
        logger.addHandler(file_handler)

    # Per-module level overrides
    for module_name, module_level in module_levels.items():
        module_logger = logging.getLogger(module_name)
        module_logger.setLevel(getattr(logging, module_level.upper(), logging.INFO))

    return logger


logger = setup_logging()
