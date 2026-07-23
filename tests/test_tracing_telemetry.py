"""Tests for tracing, telemetry, and logging infrastructure."""

from aios_core.tracing import Tracer
from aios_core.logging_config import JSONFormatter


def test_tracer_stats():
    t = Tracer()
    s = t.stats()
    assert isinstance(s, dict)


def test_json_formatter():
    fmt = JSONFormatter()
    assert fmt is not None
