"""Distributed Tracing Engine for AIOS Executive Layer.

Supports W3C Trace Context headers (traceparent: 00-traceid-spanid-flags),
nested spans, trace context propagation across EventBus, agents, and HTTP API.
"""

import threading
import time
import uuid
from contextlib import contextmanager
from typing import Any, Dict, List, Optional, Tuple

_current_trace_context = threading.local()


class Span:
    """An OpenTelemetry-compatible tracing span."""

    def __init__(
        self,
        name: str,
        trace_id: str,
        span_id: str,
        parent_id: str | None = None,
        attributes: dict[str, Any] | None = None,
    ):
        self.name = name
        self.trace_id = trace_id
        self.span_id = span_id
        self.parent_id = parent_id
        self.attributes: dict[str, Any] = attributes or {}
        self.events: List[dict[str, Any]] = []
        self.start_time = time.time()
        self.end_time: float | None = None
        self.status = "OK"
        self.error_message: str | None = None

    def set_attribute(self, key: str, value: Any) -> None:
        """Execute set attribute."""
        self.attributes[key] = value

    def add_event(self, name: str, attributes: dict[str, Any] | None = None) -> None:
        """Execute add event."""
        self.events.append({"name": name, "attributes": attributes or {}, "timestamp": time.time()})

    def set_status_error(self, message: str) -> None:
        """Execute set status error."""
        self.status = "ERROR"
        self.error_message = message

    def finish(self) -> None:
        """Execute finish."""
        if self.end_time is None:
            self.end_time = time.time()

    @property
    def duration_ms(self) -> float:
        """Execute duration ms."""
        end = self.end_time or time.time()
        return round((end - self.start_time) * 1000.0, 3)

    def to_w3c_header(self) -> str:
        """Format as standard W3C traceparent header string: 00-{trace_id}-{span_id}-01."""
        return f"00-{self.trace_id}-{self.span_id}-01"


class Tracer:
    """Thread-safe Distributed Tracer with W3C propagation."""

    def __init__(self):
        self.active_spans: Dict[str, Span] = {}
        self.finished_spans: List[Span] = []

    def generate_trace_id(self) -> str:
        """Execute generate trace id."""
        return uuid.uuid4().hex

    def generate_span_id(self) -> str:
        """Execute generate span id."""
        return uuid.uuid4().hex[:16]

    def parse_w3c_header(self, traceparent: str) -> Tuple[str | None, str | None]:
        """Parse W3C traceparent header: 00-{trace_id}-{span_id}-{flags}."""
        parts = traceparent.split("-")
        if len(parts) >= 3 and parts[0] == "00":
            return parts[1], parts[2]
        return None, None

    @contextmanager
    def start_span(
        self,
        name: str,
        parent_traceparent: str | None = None,
        attributes: dict[str, Any] | None = None,
    ):
        """Start a new contextual span."""
        parent_trace_id, parent_span_id = None, None
        if parent_traceparent:
            parent_trace_id, parent_span_id = self.parse_w3c_header(parent_traceparent)

        # Retrieve thread local active span if available
        current_active: Optional[Span] = getattr(_current_trace_context, "active_span", None)

        if parent_trace_id:
            trace_id = parent_trace_id
            parent_id = parent_span_id
        elif current_active:
            trace_id = current_active.trace_id
            parent_id = current_active.span_id
        else:
            trace_id = self.generate_trace_id()
            parent_id = None

        span_id = self.generate_span_id()
        span = Span(
            name=name,
            trace_id=trace_id,
            span_id=span_id,
            parent_id=parent_id,
            attributes=attributes,
        )

        self.active_spans[span_id] = span
        previous_span = getattr(_current_trace_context, "active_span", None)
        _current_trace_context.active_span = span

        try:
            yield span
        except Exception as exc:
            span.set_status_error(str(exc))
            raise
        finally:
            span.finish()
            self.active_spans.pop(span_id, None)
            self.finished_spans.append(span)
            if len(self.finished_spans) > 2000:
                self.finished_spans = self.finished_spans[-2000:]
            _current_trace_context.active_span = previous_span

    def get_current_span(self) -> Optional[Span]:
        """Execute get current span."""
        return getattr(_current_trace_context, "active_span", None)

    def stats(self) -> dict[str, Any]:
        """Return statistics dict."""
        return {
            "active_spans": len(self.active_spans),
            "finished_spans": len(self.finished_spans),
        }


from typing import Tuple

__all__ = ["Span", "Tracer"]

tracer = Tracer()
