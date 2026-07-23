"""Tracing span ops."""
from aios_core.tracing import Tracer
def test_span(): t=Tracer(); t.start_span("op"); t.end_span(); assert t.stats() is not None
