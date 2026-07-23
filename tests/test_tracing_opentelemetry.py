"""Tests for tracing and OpenTelemetry integration."""

from aios_core.tracing import Tracer
from aios_core.telemetry import TelemetryCollector


def test_tracer_init():
    t = Tracer()
    assert t is not None


def test_telemetry_collector_init():
    tc = TelemetryCollector()
    assert tc is not None
