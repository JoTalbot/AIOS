"""Distributed Tracing for AIOS"""

import uuid
from typing import Dict, Optional
from contextlib import contextmanager


class Tracer:
    """Simple distributed tracer."""

    def __init__(self):
        self.spans: Dict[str, Dict] = {}

    @contextmanager
    def start_span(self, name: str, parent: Optional[str] = None):
        span_id = str(uuid.uuid4())[:16]
        self.spans[span_id] = {
            "name": name,
            "parent": parent,
            "start": __import__("time").time()
        }
        try:
            yield span_id
        finally:
            self.spans[span_id]["end"] = __import__("time").time()
            self.spans[span_id]["duration"] = self.spans[span_id]["end"] - self.spans[span_id]["start"]

    def get_trace(self, span_id: str) -> Dict:
        return self.spans.get(span_id, {})

    def stats(self) -> dict:
        return {"active_spans": len(self.spans)}


tracer = Tracer()