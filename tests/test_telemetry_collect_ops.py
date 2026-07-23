"""Telemetry collect ops."""
from aios_core.telemetry import Telemetry
def test_collect(): t=Telemetry(); t.counter("req",1); assert t.stats() is not None
