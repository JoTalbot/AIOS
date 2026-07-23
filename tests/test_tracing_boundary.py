"""tracing boundary test."""
from aios_core.tracing import Tracer

def test(): assert Tracer().stats() is not None
