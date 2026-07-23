"""Tracing full tests."""
from aios_core.tracing import Tracer
def test_tracer_span():
    t = Tracer()
    with t.span("test_op"):
        pass
    assert t.stats() is not None
